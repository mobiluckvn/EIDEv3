/* bai2/sw/golden_checksums.h
 * Mo hinh chuan doc lap tinh tong kiem 32-bit cho phep nhan ma tran.
 * Tinh truc tiep tu cong thuc toan hoc doc lap, khong dung chung bo dem voi V0..V3.
 */

#ifndef GOLDEN_CHECKSUMS_H
#define GOLDEN_CHECKSUMS_H

#include <stdint.h>

/* Tinh toan doc lap ket qua chuan cua ma tran C va checksum tuong ung
 * Quy luat du lieu vao va 4 tong kiem chuan theo muc 5.3b tai-lieu/DAU-VAO-AGENT-FPGA-v2.md (tang NGUOI):
 * A[i, k] = ((i + k) % 7) + 1
 * B[k, j] = ((k * 3 + j) % 11) - 5
 */
static inline uint32_t get_golden_checksum(int n, int dtype) {
    (void)dtype;
    uint32_t chk = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            int32_t sum = 0;
            for (int k = 0; k < n; k++) {
                int32_t a_ik = ((i + k) % 7) + 1;
                int32_t b_kj = ((k * 3 + j) % 11) - 5;
                sum += a_ik * b_kj;
            }
            chk = (chk * 31) + (uint32_t)sum;
        }
    }
    return chk;
}

#endif /* GOLDEN_CHECKSUMS_H */
