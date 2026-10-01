#include "matmul.h"

/* V0: Ba vòng lặp i-j-k cơ bản */
void matmul_v0(int n, const elem_t *a, const elem_t *b, acc_t *c) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            acc_t sum = 0;
            for (int k = 0; k < n; k++) {
                sum += (acc_t)a[i * n + k] * (acc_t)b[k * n + j];
            }
            c[i * n + j] = sum;
        }
    }
}

/* V1: Thứ tự i-k-j, duyệt B theo hàng, ghi dồn c[i][j] */
void matmul_v1(int n, const elem_t *a, const elem_t *b, acc_t *c) {
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

/* V2: V1 + mở vòng lặp trong theo j bước 4 (loop unrolling x4) */
void matmul_v2(int n, const elem_t *a, const elem_t *b, acc_t *c) {
    for (int i = 0; i < n; i++) {
        acc_t *ci = &c[i * n];
        for (int j = 0; j < n; j += 4) {
            ci[j]     = 0;
            ci[j + 1] = 0;
            ci[j + 2] = 0;
            ci[j + 3] = 0;
        }
        for (int k = 0; k < n; k++) {
            acc_t a_ik = (acc_t)a[i * n + k];
            const elem_t *bk = &b[k * n];
            for (int j = 0; j < n; j += 4) {
                ci[j]     += a_ik * (acc_t)bk[j];
                ci[j + 1] += a_ik * (acc_t)bk[j + 1];
                ci[j + 2] += a_ik * (acc_t)bk[j + 2];
                ci[j + 3] += a_ik * (acc_t)bk[j + 3];
            }
        }
    }
}

/* V3: Chia khối (tiling) 4x4, chỉ áp dụng cho N >= 16 */
#define TILE_BS 4

void matmul_v3(int n, const elem_t *a, const elem_t *b, acc_t *c) {
    if (n < 16) {
        /* Đề bài quy định V3 chỉ áp dụng cho N >= 16; khi N < 16 chuyển tiếp sang V2 */
        matmul_v2(n, a, b, c);
        return;
    }

    for (int idx = 0; idx < n * n; idx++) {
        c[idx] = 0;
    }

    for (int ii = 0; ii < n; ii += TILE_BS) {
        for (int kk = 0; kk < n; kk += TILE_BS) {
            for (int jj = 0; jj < n; jj += TILE_BS) {
                for (int i = ii; i < ii + TILE_BS; i++) {
                    acc_t *ci = &c[i * n];
                    for (int k = kk; k < kk + TILE_BS; k++) {
                        acc_t a_ik = (acc_t)a[i * n + k];
                        const elem_t *bk = &b[k * n];
                        for (int j = jj; j < jj + TILE_BS; j += 4) {
                            ci[j]     += a_ik * (acc_t)bk[j];
                            ci[j + 1] += a_ik * (acc_t)bk[j + 1];
                            ci[j + 2] += a_ik * (acc_t)bk[j + 2];
                            ci[j + 3] += a_ik * (acc_t)bk[j + 3];
                        }
                    }
                }
            }
        }
    }
}
