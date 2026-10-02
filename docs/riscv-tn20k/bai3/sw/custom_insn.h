#ifndef BAI3_CUSTOM_INSN_H
#define BAI3_CUSTOM_INSN_H

#include <stdint.h>

/*
 * Các chỉ thị lệnh tuỳ biến vùng custom-0 (opcode = 0x0B, funct7 = 0x00)
 * Định dạng R: .insn r opcode, funct3, funct7, rd, rs1, rs2
 */

/* funct3 = 000: acc.clr (acc <- 0) */
static inline void custom_acc_clr(void) {
    __asm__ volatile (".insn r 0x0B, 0, 0, x0, x0, x0");
}

/* funct3 = 001: mac rs1, rs2 (acc <- acc + rs1 * rs2) */
static inline void custom_mac(int32_t rs1, int32_t rs2) {
    __asm__ volatile (".insn r 0x0B, 1, 0, x0, %0, %1" : : "r"(rs1), "r"(rs2));
}

/* funct3 = 010: acc.rd rd (rd <- acc) */
static inline int32_t custom_acc_rd(void) {
    int32_t res;
    __asm__ volatile (".insn r 0x0B, 2, 0, %0, x0, x0" : "=r"(res));
    return res;
}

#endif /* BAI3_CUSTOM_INSN_H */
