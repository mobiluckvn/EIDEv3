/* start.S
 * Khởi tạo môi trường bare-metal cho PicoRV32:
 * 1. Khởi tạo con trỏ ngăn xếp sp = đỉnh BRAM (32 KB = 0x00008000) (anh cho, chưa có tài liệu)
 * 2. Xoá sạch phân vùng .bss về 0
 * 3. Chuyển điều khiển vào main()
 */

.section .init, "ax"
.global _start
.type _start, @function

_start:
    /* 1. Thiết lập stack pointer tại đỉnh 32 KB BRAM */
    la sp, _stack_top

    /* 2. Xoá phân đoạn .bss */
    la a0, _sbss
    la a1, _ebss
clear_bss_loop:
    bge a0, a1, clear_bss_done
    sw zero, 0(a0)
    addi a0, a0, 4
    j clear_bss_loop

clear_bss_done:
    /* 3. Gọi chương trình C */
    call main

    /* Vòng lặp dừng nếu main kết thúc */
hang:
    j hang

.size _start, . - _start
