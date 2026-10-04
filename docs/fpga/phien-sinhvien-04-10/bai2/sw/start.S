/* start.S
 * Khoi tao moi truong bare-metal cho PicoRV32 Bai 2:
 * 1. Thiet lap con tro ngan xep sp o dinh BRAM
 * 2. Xoa phan vung .bss ve 0
 * 3. Chuyen dieu khien vao main()
 */

.section .init, "ax"
.global _start
.type _start, @function

_start:
    /* 1. Thiet lap stack pointer tai dinh BRAM */
    la sp, _stack_top

    /* 2. Xoa phan doan .bss */
    la a0, _sbss
    la a1, _ebss
clear_bss_loop:
    bge a0, a1, clear_bss_done
    sw zero, 0(a0)
    addi a0, a0, 4
    j clear_bss_loop

clear_bss_done:
    /* 3. Goi chuong trinh C */
    call main

    /* Dung chuong trinh neu main thoat */
hang:
    j hang

.size _start, . - _start
