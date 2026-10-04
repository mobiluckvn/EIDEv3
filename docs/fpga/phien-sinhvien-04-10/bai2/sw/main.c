/* bai2/sw/main.c
 * Chuong trinh do hieu nang nhan ma tran tren PicoRV32 (Tang Nano 20K)
 * Do 32 o: 4 kich thuoc N in {4, 8, 16, 32} x 2 kieu {I32, I8} x 4 cach cai dat {V0..V3}
 * In ket qua tung o ngay khi do xong qua UART 115200 baud
 */

#include <stdint.h>
#include "golden_checksums.h"

#define REG_UART_DATA   (*(volatile uint32_t *)0x10000000)
#define REG_UART_STATUS (*(volatile uint32_t *)0x10000004)
#define REG_LED         (*(volatile uint32_t *)0x20000000)

#ifndef HW_TAG
#define HW_TAG "H0"
#endif

#define MAX_N 32
#define MAX_ELEMENTS (MAX_N * MAX_N)

/* Vung dem tai su dung cho bon ma tran (tong 16 KB: mat_a 4 KB, mat_b 4 KB, mat_c 4 KB, mat_b_trans 4 KB) */
static int32_t mat_a[MAX_ELEMENTS];
static int32_t mat_b[MAX_ELEMENTS];
static int32_t mat_c[MAX_ELEMENTS];
static int32_t mat_b_trans[MAX_ELEMENTS];

static inline uint64_t read_cycle(void) {
    uint32_t high0, low, high1;
    do {
        __asm__ volatile ("rdcycleh %0" : "=r"(high0));
        __asm__ volatile ("rdcycle  %0" : "=r"(low));
        __asm__ volatile ("rdcycleh %0" : "=r"(high1));
    } while (high0 != high1);
    return (((uint64_t)high0) << 32) | low;
}

__attribute__((optimize("no-tree-loop-distribute-patterns")))
void *memset(void *s, int c, unsigned int n) {
    unsigned char *p = (unsigned char *)s;
    while (n--) {
        *p++ = (unsigned char)c;
    }
    return s;
}

void uart_putc(char c) {
    while (REG_UART_STATUS & 1) {
    }
    REG_UART_DATA = (uint32_t)(uint8_t)c;
}

void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

void print_u64(uint64_t val) {
    char buf[24];
    int idx = 0;
    if (val == 0) {
        uart_putc('0');
        return;
    }
    while (val > 0) {
        uint64_t q = 0;
        uint64_t r = 0;
        for (int i = 63; i >= 0; i--) {
            r = (r << 1) | ((val >> i) & 1);
            if (r >= 10) {
                r -= 10;
                q |= (1ULL << i);
            }
        }
        buf[idx++] = '0' + (char)r;
        val = q;
    }
    while (idx > 0) {
        uart_putc(buf[--idx]);
    }
}

__attribute__((optimize("no-tree-loop-distribute-patterns")))
void *memcpy(void *dest, const void *src, unsigned int n) {
    char *d = (char *)dest;
    const char *s = (const char *)src;
    while (n--) *d++ = *s++;
    return dest;
}

void print_hex32(uint32_t val) {
    static const char hex_chars[] = "0123456789abcdef";
    uart_puts("0x");
    for (int i = 7; i >= 0; i--) {
        uart_putc(hex_chars[(val >> (i * 4)) & 0xf]);
    }
}

/* Khoi tao du lieu ma tran theo quy luat xac dinh de doi chieu */
static void init_matrices_i32(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            mat_a[i * n + j] = ((i + j) % 7) + 1;
            mat_b[i * n + j] = ((i * 3 + j) % 11) - 5;
            mat_c[i * n + j] = 0;
        }
    }
}

static void init_matrices_i8(int n) {
    int8_t *a8 = (int8_t *)mat_a;
    int8_t *b8 = (int8_t *)mat_b;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            a8[i * n + j] = (int8_t)(((i + j) % 7) + 1);
            b8[i * n + j] = (int8_t)(((i * 3 + j) % 11) - 5);
            mat_c[i * n + j] = 0;
        }
    }
}

/* 4 cach cai dat cho I32 */
static void matmul_i32_v0(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            for (int k = 0; k < n; k++) {
                sum += mat_a[i * n + k] * mat_b[k * n + j];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

static void matmul_i32_v1(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            mat_c[i * n + j] = 0;
        }
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            int32_t a_ik = mat_a[i * n + k];
            for (int j = 0; j < n; j++) {
                mat_c[i * n + j] += a_ik * mat_b[k * n + j];
            }
        }
    }
}

static void matmul_i32_v2(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            int k = 0;
            for (; k <= n - 4; k += 4) {
                sum += mat_a[i * n + k] * mat_b[k * n + j];
                sum += mat_a[i * n + k + 1] * mat_b[(k + 1) * n + j];
                sum += mat_a[i * n + k + 2] * mat_b[(k + 2) * n + j];
                sum += mat_a[i * n + k + 3] * mat_b[(k + 3) * n + j];
            }
            for (; k < n; k++) {
                sum += mat_a[i * n + k] * mat_b[k * n + j];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

static void transpose_i32(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            mat_b_trans[j * n + i] = mat_b[i * n + j];
        }
    }
}

static void matmul_i32_v3_core(int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            for (int k = 0; k < n; k++) {
                sum += mat_a[i * n + k] * mat_b_trans[j * n + k];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

/* 4 cach cai dat cho I8 */
static void matmul_i8_v0(int n) {
    const int8_t *a8 = (const int8_t *)mat_a;
    const int8_t *b8 = (const int8_t *)mat_b;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            for (int k = 0; k < n; k++) {
                sum += (int32_t)a8[i * n + k] * (int32_t)b8[k * n + j];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

static void matmul_i8_v1(int n) {
    const int8_t *a8 = (const int8_t *)mat_a;
    const int8_t *b8 = (const int8_t *)mat_b;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            mat_c[i * n + j] = 0;
        }
    }
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            int32_t a_ik = (int32_t)a8[i * n + k];
            for (int j = 0; j < n; j++) {
                mat_c[i * n + j] += a_ik * (int32_t)b8[k * n + j];
            }
        }
    }
}

static void matmul_i8_v2(int n) {
    const int8_t *a8 = (const int8_t *)mat_a;
    const int8_t *b8 = (const int8_t *)mat_b;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            int k = 0;
            for (; k <= n - 4; k += 4) {
                sum += (int32_t)a8[i * n + k] * (int32_t)b8[k * n + j];
                sum += (int32_t)a8[i * n + k + 1] * (int32_t)b8[(k + 1) * n + j];
                sum += (int32_t)a8[i * n + k + 2] * (int32_t)b8[(k + 2) * n + j];
                sum += (int32_t)a8[i * n + k + 3] * (int32_t)b8[(k + 3) * n + j];
            }
            for (; k < n; k++) {
                sum += (int32_t)a8[i * n + k] * (int32_t)b8[k * n + j];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

static void transpose_i8(int n) {
    const int8_t *b8 = (const int8_t *)mat_b;
    int8_t *b8_trans = (int8_t *)mat_b_trans;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            b8_trans[j * n + i] = b8[i * n + j];
        }
    }
}

static void matmul_i8_v3_core(int n) {
    const int8_t *a8 = (const int8_t *)mat_a;
    const int8_t *b8_trans = (const int8_t *)mat_b_trans;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            for (int k = 0; k < n; k++) {
                sum += (int32_t)a8[i * n + k] * (int32_t)b8_trans[j * n + k];
            }
            mat_c[i * n + j] = sum;
        }
    }
}

/* Tinh checksum 32-bit de kiem tra tinh dung dan */
static uint32_t calc_checksum(int n) {
    uint32_t chk = 0;
    for (int i = 0; i < n * n; i++) {
        chk = (chk * 31) + (uint32_t)mat_c[i];
    }
    return chk;
}

int main(void) {
#ifdef SIM
    static const int n_list[] = {4};
    static const int n_count = 1;
#else
    static const int n_list[] = {4, 8, 16, 32};
    static const int n_count = 4;
#endif
    uint64_t overhead = 0;
    uint32_t led_val = 0;

    /* Do overhead cua phep doc read_cycle */
    for (int i = 0; i < 5; i++) {
        uint64_t t0 = read_cycle();
        uint64_t t1 = read_cycle();
        uint64_t diff = t1 - t0;
        if (i == 0 || diff < overhead) {
            overhead = diff;
        }
    }

    uart_puts("START_BENCHMARK_BAI2\r\n");

    /* Chay cac o: N x 2 kieu du lieu x 4 cach cai dat */
    for (int ni = 0; ni < n_count; ni++) {
        int n = n_list[ni];
        uint64_t macs = (uint64_t)n * (uint64_t)n * (uint64_t)n;

        for (int dtype = 0; dtype < 2; dtype++) {
            const char *dtype_str = (dtype == 0) ? "I32" : "I8";

            for (int ver = 0; ver < 4; ver++) {
                /* Dao LED sau moi o de bao hieu he thong dang chay binh thuong */
                led_val ^= 1;
                REG_LED = led_val;

                uint64_t min_cycles = (uint64_t)-1;
                uint64_t min_trans_cycles = 0;
                uint32_t chk = 0;

                /* Lap 3 lan do de lay gia tri nho nhat tranh nhieu */
                for (int rep = 0; rep < 3; rep++) {
                    if (dtype == 0) {
                        init_matrices_i32(n);
                    } else {
                        init_matrices_i8(n);
                    }

                    if (ver == 3) {
                        uint64_t t_tr0 = read_cycle();
                        if (dtype == 0) {
                            transpose_i32(n);
                        } else {
                            transpose_i8(n);
                        }
                        uint64_t t_tr1 = read_cycle();
                        uint64_t d_tr = (t_tr1 > t_tr0) ? (t_tr1 - t_tr0) : 0;
                        if (d_tr > overhead) d_tr -= overhead;
                        if (rep == 0 || d_tr < min_trans_cycles) {
                            min_trans_cycles = d_tr;
                        }
                    }

                    uint64_t t_start = read_cycle();
                    if (dtype == 0) {
                        if (ver == 0) matmul_i32_v0(n);
                        else if (ver == 1) matmul_i32_v1(n);
                        else if (ver == 2) matmul_i32_v2(n);
                        else matmul_i32_v3_core(n);
                    } else {
                        if (ver == 0) matmul_i8_v0(n);
                        else if (ver == 1) matmul_i8_v1(n);
                        else if (ver == 2) matmul_i8_v2(n);
                        else matmul_i8_v3_core(n);
                    }
                    uint64_t t_end = read_cycle();

                    uint64_t diff = (t_end > t_start) ? (t_end - t_start) : 0;
                    if (diff > overhead) {
                        diff -= overhead;
                    }
                    if (diff < min_cycles) {
                        min_cycles = diff;
                    }
                }

                chk = calc_checksum(n);
                uint32_t golden_chk = get_golden_checksum(n, dtype);
                int is_ok = (chk == golden_chk) ? 1 : 0;
                /* Tinh CPM bang phep dich bit vi N in {4, 8, 16, 32} => macs = N^3 la luy thua cua 2:
                 * N=4  => macs=64    (2^6)  => dich phai 6 bit
                 * N=8  => macs=512   (2^9)  => dich phai 9 bit
                 * N=16 => macs=4096  (2^12) => dich phai 12 bit
                 * N=32 => macs=32768 (2^15) => dich phai 15 bit
                 * Khong dung toan tu chia '/' de tranh sinh lenh div/divu khi march=rv32im ma ENABLE_DIV=0 (ADR-03) */
                int shift_macs = (n == 4) ? 6 : ((n == 8) ? 9 : ((n == 16) ? 12 : 15));
                uint64_t cpm = min_cycles >> shift_macs;

                /* In dong ket qua ngay lap tuc cho tung o */
                uart_puts("RESULT,n=");
                print_u64((uint64_t)n);
                uart_puts(",dtype=");
                uart_puts(dtype_str);
                uart_puts(",ver=V");
                print_u64((uint64_t)ver);
                uart_puts(",hw=");
                uart_puts(HW_TAG);
                uart_puts(",cycles=");
                print_u64(min_cycles);
                uart_puts(",macs=");
                print_u64(macs);
                uart_puts(",cpm=");
                print_u64(cpm);
                uart_puts(",chk=");
                print_hex32(chk);
                uart_puts(",ok=");
                uart_putc(is_ok ? '1' : '0');
                if (ver == 3) {
                    uart_puts(",trans_cyc=");
                    print_u64(min_trans_cycles);
                }
                uart_puts("\r\n");
            }
        }
    }

    uart_puts("DONE_BENCHMARK_BAI2\r\n");

    /* Hoan thanh: bat tat ca LED bao thanh cong */
    REG_LED = 0;

    while (1) {
        /* Dung chuong trinh */
    }

    return 0;
}
