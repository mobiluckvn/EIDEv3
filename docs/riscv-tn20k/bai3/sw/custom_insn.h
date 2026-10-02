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

/* funct3 = 011: dot4 rs1, rs2 (acc <- acc + dot4(rs1, rs2)) */
static inline void custom_dot4(uint32_t rs1, uint32_t rs2) {
    __asm__ volatile (".insn r 0x0B, 3, 0, x0, %0, %1" : : "r"(rs1), "r"(rs2));
}

/* funct3 = 100: vsetvl rd, rs1 (VL <= min(rs1, 16), rd <= VL) */
#define custom_vsetvl(avl) ({ \
    uint32_t __vl; \
    __asm__ volatile (".insn r 0x0B, 4, 0, %0, %1, x0" : "=r"(__vl) : "r"(avl)); \
    __vl; \
})

/* funct3 = 101: vload vd, rs1 (nạp VL byte từ BRAM Port B) */
#define custom_vload(vd, addr) \
    __asm__ volatile (".insn r 0x0B, 5, 0, x" #vd ", %0, x0" \
                      : : "r"(addr) : "memory")

/* funct3 = 110: vdot vs1, vs2 (tích luỹ tích vô hướng vector) */
#define custom_vdot(vs1, vs2) \
    __asm__ volatile (".insn r 0x0B, 6, 0, x0, x" #vs1 ", x" #vs2)

/* funct3 = 111: vstore vs, rs1 (ghi VL byte ra BRAM Port B) */
#define custom_vstore(vs, addr) \
    __asm__ volatile (".insn r 0x0B, 7, 0, x0, %0, x" #vs \
                      : : "r"(addr) : "memory")

#endif /* BAI3_CUSTOM_INSN_H */
