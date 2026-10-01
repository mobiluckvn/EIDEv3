/* Khởi động PicoRV32 cho Bài 2: thiết lập sp, xoá BSS và gọi main */
    .section .init, "ax"
    .global _start
    .type _start, @function

_start:
    /* 1. Thiết lập con trỏ ngăn xếp sp từ nhãn linker script __stack_top */
    la sp, __stack_top

    /* 2. Xoá vùng nhớ .bss */
    la a0, _sbss
    la a1, _ebss
    bge a0, a1, .L_bss_done

.L_bss_loop:
    sw zero, 0(a0)
    addi a0, a0, 4
    blt a0, a1, .L_bss_loop

.L_bss_done:
    /* 3. Gọi hàm main */
    call main

    /* 4. Vòng lặp vô hạn nếu main thoát */
.L_hang:
    j .L_hang

    .size _start, . - _start
