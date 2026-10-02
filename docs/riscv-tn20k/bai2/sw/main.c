#include <stdint.h>
#include <stddef.h>
#include "matmul.h"

/* Hiện thực memcpy và memset freestanding cho GCC -nostdlib */
void *memcpy(void *dest, const void *src, size_t n) {
    uint8_t *d = (uint8_t *)dest;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) {
        *d++ = *s++;
    }
    return dest;
}

void *memset(void *s, int c, size_t n) {
    uint8_t *p = (uint8_t *)s;
    while (n--) {
        *p++ = (uint8_t)c;
    }
    return s;
}

/* Dữ liệu kiểm thử ma trận A, B và CHECKSUM_REF */
#include "../../data_matrix.h"

#define UART_TX_REG     (*(volatile uint32_t *)0x10000000)
#define UART_STATUS_REG (*(volatile uint32_t *)0x10000004)
#define LED_REG         (*(volatile uint32_t *)0x20000000)

#ifndef HW_CONFIG
#define HW_CONFIG "?"
#endif

#ifndef DTYPE_STR
#define DTYPE_STR "?"
#endif

/* Bộ đệm ma trận kết quả C */
static acc_t mat_c[MATRIX_N * MATRIX_N];

/* UART cơ bản */
static void uart_putc(char c) {
    while (UART_STATUS_REG & 1) {
        /* Chờ bit bận của UART TX hạ xuống */
    }
    UART_TX_REG = (uint32_t)(uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

/* Thuật toán chia nguyên 64-bit tự lập (không dùng chia phần cứng / libgcc) */
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

/* In số nguyên không dấu 64-bit qua UART */
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
    while (idx > 0) {
        uart_putc(buf[--idx]);
    }
}

/* In số hex 32-bit định dạng 8 ký tự viết hoa */
static void uart_put_hex32(uint32_t val) {
    const char hex_chars[] = "0123456789ABCDEF";
    for (int i = 7; i >= 0; i--) {
        uint8_t nibble = (val >> (i * 4)) & 0x0F;
        uart_putc(hex_chars[nibble]);
    }
}

/* Đọc bộ đếm 64-bit rdcycle/rdcycleh chống rollover */
static inline uint64_t get_cycle64(void) {
    uint32_t hi0, hi1, lo;
    do {
        __asm__ volatile ("rdcycleh %0" : "=r"(hi0));
        __asm__ volatile ("rdcycle %0" : "=r"(lo));
        __asm__ volatile ("rdcycleh %0" : "=r"(hi1));
    } while (hi0 != hi1);
    return ((uint64_t)hi0 << 32) | lo;
}

/* Đo chi phí overhead của 2 lần đọc get_cycle64 liền nhau */
static uint64_t measure_rdcycle_overhead(void) {
    uint64_t min_ov = (uint64_t)-1;
    for (int i = 0; i < 5; i++) {
        uint64_t t0 = get_cycle64();
        uint64_t t1 = get_cycle64();
        uint64_t diff = (t1 >= t0) ? (t1 - t0) : 0;
        if (diff < min_ov) {
            min_ov = diff;
        }
    }
    return min_ov;
}

/* Tính tổng kiểm có trọng số: sum((i*N + j + 1) * C[i][j]) mod 2^32 */
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

/* Đo và in kết quả cho 1 phiên bản hàm nhân ma trận */
static void run_benchmark(const char *ver_name, matmul_fn_t fn, uint64_t overhead) {
    uint64_t min_cycles = (uint64_t)-1;

    /* Mỗi phép đo chạy 3 lần, lấy giá trị nhỏ nhất */
    for (int run = 0; run < 3; run++) {
        uint64_t t0 = get_cycle64();
        fn(MATRIX_N, (const elem_t *)mat_a, (const elem_t *)mat_b, mat_c);
        uint64_t t1 = get_cycle64();

        uint64_t diff = (t1 >= t0) ? (t1 - t0) : 0;
        if (diff > overhead) {
            diff -= overhead;
        } else {
            diff = 0;
        }

        if (diff < min_cycles) {
            min_cycles = diff;
        }
    }

    uint32_t chk = compute_checksum(MATRIX_N, mat_c);
    int ok = (chk == CHECKSUM_REF) ? 1 : 0;
    uint32_t macs = (uint32_t)MATRIX_N * MATRIX_N * MATRIX_N;

    /* Tính cpm = cycles / macs với 2 chữ số thập phân bằng chia nguyên sau khi đo */
    uint64_t rem = 0;
    uint64_t cpm_int = divmod64(min_cycles, (uint64_t)macs, &rem);
    uint64_t cpm_frac = divmod64(rem * 100ULL, (uint64_t)macs, NULL);

    /* In đúng chuẩn đề bài:
       RESULT,n=16,dtype=I8,ver=V1,hw=H2,cycles=123456,macs=4096,cpm=30.14,chk=0x1A2B3C4D,ok=1 */
    uart_puts("RESULT,n=");
    uart_put_u64((uint64_t)MATRIX_N);
    uart_puts(",dtype=");
    uart_puts(DTYPE_STR);
    uart_puts(",ver=");
    uart_puts(ver_name);
    uart_puts(",hw=");
    uart_puts(HW_CONFIG);
    uart_puts(",cycles=");
    uart_put_u64(min_cycles);
    uart_puts(",macs=");
    uart_put_u64((uint64_t)macs);
    uart_puts(",cpm=");
    uart_put_u64(cpm_int);
    uart_putc('.');
    if (cpm_frac < 10) {
        uart_putc('0');
    }
    uart_put_u64(cpm_frac);
    uart_puts(",chk=0x");
    uart_put_hex32(chk);
    uart_puts(",ok=");
    uart_putc((char)('0' + ok));
    uart_puts("\r\n");
}

int main(void) {
    /* Đèn LED báo hiệu khởi động */
    LED_REG = 0x01;

    uart_puts("=== BAI 2: MATRIX MULTIPLICATION BENCHMARK ===\r\n");

    uint64_t overhead = measure_rdcycle_overhead();

    run_benchmark("V0", matmul_v0, overhead);
    run_benchmark("V1", matmul_v1, overhead);
    run_benchmark("V2", matmul_v2, overhead);

    /* V3 chỉ áp dụng khi N >= 16; nếu N < 16 có thể chạy để kiểm tra hoặc chỉ khi N >= 16 */
#if MATRIX_N >= 16
    run_benchmark("V3", matmul_v3, overhead);
#else
    /* Khi N < 16, đề bài nêu V3 chỉ áp dụng N >= 16. Ta vẫn có thể đo nếu muốn hoặc ghi chú */
    run_benchmark("V3", matmul_v3, overhead);
#endif

    uart_puts("=== BENCHMARK COMPLETED ===\r\n");
    uart_puts("DONE\r\n");

    /* Hoàn tất thành công: bật toàn bộ LED */
    LED_REG = 0x3F;

    while (1) {
        /* Chờ */
    }

    return 0;
}
