#include <stdint.h>
#include <stddef.h>
#include "custom_insn.h"

/* Bộ nhớ và dữ liệu ma trận kiểm thử n=16, I8 */
#include "../../data_16_I8.h"

#define UART_TX_REG     (*(volatile uint32_t *)0x10000000)
#define UART_STATUS_REG (*(volatile uint32_t *)0x10000004)
#define LED_REG         (*(volatile uint32_t *)0x20000000)

static acc_t mat_c[MATRIX_N * MATRIX_N];
static elem_t mat_b_trans[MATRIX_N * MATRIX_N] __attribute__((aligned(4)));

/* Freestanding memcpy va memset */
void *memcpy(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) *d++ = *s++;
    return dest;
}

void *memset(void *s, int c, size_t n) {
    uint8_t *p = (uint8_t *)s;
    while (n--) *p++ = (uint8_t)c;
    return s;
}

/* UART TX */
static void uart_putc(char c) {
    while (UART_STATUS_REG & 1) {}
    UART_TX_REG = (uint32_t)(uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) uart_putc(*s++);
}

/* Chia nguyên 64-bit tự lập */
static uint64_t divmod64(uint64_t n, uint64_t d, uint64_t *r) {
    if (d == 0) {
        if (r) *r = 0;
        return 0;
    }
    uint64_t q = 0;
    uint64_t rem = 0;
    for (int i = 63; i >= 0; i--) {
        rem = (rem << 1) | ((n >> i) & 1ULL);
        if (rem >= d) {
            rem -= d;
            q |= (1ULL << i);
        }
    }
    if (r) *r = rem;
    return q;
}

static void uart_put_u64(uint64_t val) {
    char buf[21];
    int idx = 0;
    if (val == 0) {
        uart_putc('0');
        return;
    }
    while (val > 0) {
        uint64_t rem = 0;
        val = divmod64(val, 10ULL, &rem);
        buf[idx++] = (char)('0' + (uint32_t)rem);
    }
    while (idx > 0) uart_putc(buf[--idx]);
}

static void uart_put_hex32(uint32_t val) {
    const char hex_chars[] = "0123456789ABCDEF";
    for (int i = 7; i >= 0; i--) {
        uint8_t nibble = (val >> (i * 4)) & 0x0F;
        uart_putc(hex_chars[nibble]);
    }
}

/* Đọc bộ đếm chu kỳ 64-bit */
static inline uint64_t get_cycle64(void) {
    uint32_t hi0, hi1, lo;
    do {
        __asm__ volatile ("rdcycleh %0" : "=r"(hi0));
        __asm__ volatile ("rdcycle %0" : "=r"(lo));
        __asm__ volatile ("rdcycleh %0" : "=r"(hi1));
    } while (hi0 != hi1);
    return ((uint64_t)hi0 << 32) | lo;
}

static uint64_t measure_rdcycle_overhead(void) {
    uint64_t min_ov = (uint64_t)-1;
    for (int i = 0; i < 5; i++) {
        uint64_t t0 = get_cycle64();
        uint64_t t1 = get_cycle64();
        uint64_t diff = (t1 >= t0) ? (t1 - t0) : 0;
        if (diff < min_ov) min_ov = diff;
    }
    return min_ov;
}

/* Tính tổng kiểm trọng số: sum((i*N + j + 1) * C[i][j]) */
static uint32_t compute_checksum(int n, const acc_t *c) {
    uint32_t chk = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            uint32_t weight = (uint32_t)(i * n + j + 1);
            chk += (uint32_t)c[i * n + j] * weight;
        }
    }
    return chk;
}

/* Chuyển vị ma trận B: b_t[j][k] = b[k][j] bằng cộng con trỏ thuần tuý */
void transpose_b(int n, const elem_t *b, elem_t *b_t) {
    const elem_t *b_ptr = b;
    for (int k = 0; k < n; k++) {
        elem_t *b_t_col = b_t + k;
        for (int j = 0; j < n; j++) {
            *b_t_col = *b_ptr++;
            b_t_col += n;
        }
    }
}

/*
 * Nhân ma trận nấc 3b dùng lệnh dot4 qua PCPI:
 * B đã được chuyển vị trước thành b_t để mỗi cột là một vector hàng liên tiếp.
 * Toàn bộ duyệt mảng bằng cộng con trỏ để không phụ thuộc phép nhân chỉ số.
 */
void matmul_v1_p3b(int n, const elem_t *a, const elem_t *b_t, acc_t *c) {
    const elem_t *a_row_ptr = a;
    acc_t *c_row_ptr = c;
    for (int i = 0; i < n; i++) {
        const uint32_t *a_row = (const uint32_t *)a_row_ptr;
        const elem_t *b_col_ptr = b_t;
        for (int j = 0; j < n; j++) {
            const uint32_t *b_col = (const uint32_t *)b_col_ptr;
            custom_acc_clr();
            for (int k = 0; k < n; k += 4) {
                uint32_t a_val = a_row[k / 4];
                uint32_t b_val = b_col[k / 4];
                custom_dot4(a_val, b_val);
            }
            c_row_ptr[j] = custom_acc_rd();
            b_col_ptr += n;
        }
        a_row_ptr += n;
        c_row_ptr += n;
    }
}

int main(void) {
    LED_REG = 0x01;
    uart_puts("=== BAI 3: CUSTOM INSTRUCTION BENCHMARK (P3b - dot4) ===\r\n");

    uint64_t overhead = measure_rdcycle_overhead();

    // 1. Đo riêng chi phí chuyển vị ma trận B (chạy 3 lần lấy min)
    uint64_t min_trans_cycles = (uint64_t)-1;
    for (int run = 0; run < 3; run++) {
        uint64_t t0 = get_cycle64();
        transpose_b(MATRIX_N, (const elem_t *)mat_b, mat_b_trans);
        uint64_t t1 = get_cycle64();

        uint64_t diff = (t1 >= t0) ? (t1 - t0) : 0;
        if (diff > overhead) diff -= overhead;
        else diff = 0;

        if (diff < min_trans_cycles) min_trans_cycles = diff;
    }

    uart_puts("TRANSPOSE,n=");
    uart_put_u64((uint64_t)MATRIX_N);
    uart_puts(",cycles=");
    uart_put_u64(min_trans_cycles);
    uart_puts("\r\n");

    // 2. Đo nhân ma trận P3b với B đã chuyển vị (chạy 3 lần lấy min)
    uint64_t min_cycles = (uint64_t)-1;
    for (int run = 0; run < 3; run++) {
        uint64_t t0 = get_cycle64();
        matmul_v1_p3b(MATRIX_N, (const elem_t *)mat_a, mat_b_trans, mat_c);
        uint64_t t1 = get_cycle64();

        uint64_t diff = (t1 >= t0) ? (t1 - t0) : 0;
        if (diff > overhead) diff -= overhead;
        else diff = 0;

        if (diff < min_cycles) min_cycles = diff;
    }

    uint32_t chk = compute_checksum(MATRIX_N, mat_c);
    int ok = (chk == CHECKSUM_REF) ? 1 : 0;
    uint32_t macs = (uint32_t)MATRIX_N * MATRIX_N * MATRIX_N;

    uint64_t rem = 0;
    uint64_t cpm_int = divmod64(min_cycles, (uint64_t)macs, &rem);
    uint64_t cpm_frac = divmod64(rem * 100ULL, (uint64_t)macs, NULL);

    uart_puts("RESULT,n=");
    uart_put_u64((uint64_t)MATRIX_N);
    uart_puts(",dtype=I8,ver=V1,hw=P3b,cycles=");
    uart_put_u64(min_cycles);
    uart_puts(",macs=");
    uart_put_u64((uint64_t)macs);
    uart_puts(",cpm=");
    uart_put_u64(cpm_int);
    uart_putc('.');
    if (cpm_frac < 10) uart_putc('0');
    uart_put_u64(cpm_frac);
    uart_puts(",chk=0x");
    uart_put_hex32(chk);
    uart_puts(",ok=");
    uart_putc((char)('0' + ok));
    uart_puts("\r\n");

    uart_puts("=== BENCHMARK COMPLETED ===\r\n");
    uart_puts("DONE\r\n");

    LED_REG = 0x3F;
    while (1) {}
    return 0;
}
