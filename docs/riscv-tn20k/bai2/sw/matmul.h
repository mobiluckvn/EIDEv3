#ifndef BAI2_MATMUL_H
#define BAI2_MATMUL_H

#include <stdint.h>

#include "../../data_matrix.h"

typedef void (*matmul_fn_t)(int n, const elem_t *a, const elem_t *b, acc_t *c);

/* Bốn phiên bản nhân ma trận cùng chữ ký */
void matmul_v0(int n, const elem_t *a, const elem_t *b, acc_t *c);
void matmul_v1(int n, const elem_t *a, const elem_t *b, acc_t *c);
void matmul_v2(int n, const elem_t *a, const elem_t *b, acc_t *c);
void matmul_v3(int n, const elem_t *a, const elem_t *b, acc_t *c);

#endif /* BAI2_MATMUL_H */
