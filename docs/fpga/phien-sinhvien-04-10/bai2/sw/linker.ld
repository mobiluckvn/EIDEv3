/* bai2/sw/linker.ld
 * Bo cuc bo nho cho Bai 2 tren BRAM Tang Nano 20K
 * Dung luong BRAM: 32 KB
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

    .stack (NOLOAD) : {
        . = ALIGN(16);
        _stack_bottom = .;
        . = ORIGIN(BRAM) + LENGTH(BRAM);
        _stack_top = .;
        __stack = .;
    } > BRAM
}
