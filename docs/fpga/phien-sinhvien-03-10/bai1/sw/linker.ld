/* linker.ld
 * Bố cục bộ nhớ cho PicoRV32 trên Tang Nano 20K
 * BRAM 32 KB bắt đầu từ địa chỉ 0x00000000 (anh cho, chưa có tài liệu)
 */

OUTPUT_ARCH(riscv)
ENTRY(_start)

MEMORY
{
    BRAM (rwx) : ORIGIN = 0x00000000, LENGTH = 32K
}

SECTIONS
{
    .text : {
        . = ALIGN(4);
        *(.init)
        *(.text)
        *(.text.*)
        . = ALIGN(4);
        _etext = .;
    } > BRAM

    .rodata : {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata.*)
        *(.srodata)
        *(.srodata.*)
        . = ALIGN(4);
    } > BRAM

    .data : {
        . = ALIGN(4);
        *(.data)
        *(.data.*)
        *(.sdata)
        *(.sdata.*)
        . = ALIGN(4);
        _edata = .;
    } > BRAM

    .bss : {
        . = ALIGN(4);
        _sbss = .;
        *(.bss)
        *(.bss.*)
        *(.sbss)
        *(.sbss.*)
        *(COMMON)
        . = ALIGN(4);
        _ebss = .;
    } > BRAM

    /* Đỉnh ngăn xếp ở cuối bộ nhớ BRAM 32 KB */
    _stack_top = ORIGIN(BRAM) + LENGTH(BRAM);
}
