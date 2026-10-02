#include <stdint.h>
#include <stddef.h>
#include "custom_insn.h"

/* Bộ nhớ và dữ liệu ma trận kiểm thử n=4, I8 */
#include "../../data_4_I8.h"

#define UART_TX_REG     (*(volatile uint32_t *)0x10000000)
#define UART_STATUS_REG (*(volatile uint32_t *)0x10000004)
#define LED_REG         (*(volatile uint32_t *)0x20000000)

static acc_t mat_c[MATRIX_N * MATRIX_N];

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

/* Hàm nhân ma trận V1 phần mềm gốc (đối chứng) */
void matmul_v1_sw(int n, const elem_t *a, const elem_t *b, acc_t *c) {
    for (int i = 0; i < n; i++) {
        acc_t *ci = &c[i * n];
        for (int j = 0; j < n; j++) {
            ci[j] = 0;
        }
        for (int k = 0; k < n; k++) {
            acc_t a_ik = (acc_t)a[i * n + k];
            const elem_t *bk = &b[k * n];
            for (int j = 0; j < n; j++) {
                ci[j] += a_ik * (acc_t)bk[j];
            }
        }
    }
}

/*
 * Hàm nhân ma trận V1 dùng tăng tốc MAC nấc 3a qua PCPI:
 * acc.clr xoá thanh ghi tích luỹ phần cứng
 * mac rs1, rs2 cộng dồn tích a[i][k] * b[k][j]
 * acc.rd ghi kết quả ra C[i][j]
 */
void matmul_v1_p3a(int n, const elem_t *a, const elem_t *b, acc_t *c) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            custom_acc_clr();
            for (int k = 0; k < n; k++) {
                custom_mac((int32_t)a[i * n + k], (int32_t)b[k * n + j]);
            }
            c[i * n + j] = custom_acc_rd();
        }
    }
}

typedef void (*matmul_fn_t)(int n, const elem_t *a, const elem_t *b, acc_t *c);

static void run_benchmark(const char *ver_name, const char *hw_name, matmul_fn_t fn, uint64_t overhead) {
    uint64_t min_cycles = (uint64_t)-1;

    for (int run = 0; run < 3; run++) {
        uint64_t t0 = get_cycle64();
        fn(MATRIX_N, (const elem_t *)mat_a, (const elem_t *)mat_b, mat_c);
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
    uart_puts(",dtype=I8,ver=");
    uart_puts(ver_name);
    uart_puts(",hw=");
    uart_puts(hw_name);
    uart_puts(",cycles=");
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
}

int main(void) {
    LED_REG = 0x01;
    uart_puts("=== BAI 3: CUSTOM INSTRUCTION BENCHMARK (P3a) ===\r\n");

    uint64_t overhead = measure_rdcycle_overhead();

    /* Đo phiên bản V1 gốc (phần mềm thuần) để đối chiếu */
    run_benchmark("V1_SW", "H0", matmul_v1_sw, overhead);

    /* Đo phiên bản V1 dùng tăng tốc MAC nấc 3a */
    run_benchmark("V1", "P3a", matmul_v1_p3a, overhead);

    uart_puts("=== BENCHMARK COMPLETED ===\r\n");
    uart_puts("DONE\r\n");

    LED_REG = 0x3F;
    while (1) {}
    return 0;
}
