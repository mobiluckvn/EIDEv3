/* Khoi dong PicoRV32 cho Bai 3: thiet lap sp, xoa BSS va goi main */
    .section .init, "ax"
    .global _start
    .type _start, @function

_start:
    /* 1. Thiet lap con tro ngan xep sp tu nhan linker script __stack_top */
    la sp, __stack_top

    /* 2. Xoa vung nho .bss */
    la a0, _sbss
    la a1, _ebss
    bge a0, a1, .L_bss_done

.L_bss_loop:
    sw zero, 0(a0)
    addi a0, a0, 4
    blt a0, a1, .L_bss_loop

.L_bss_done:
    /* 3. Goi ham main */
    call main

    /* 4. Vong lap vo han neu main thoat */
.L_hang:
    j .L_hang

    .size _start, . - _start
