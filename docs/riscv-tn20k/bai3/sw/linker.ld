/* Linker script cho PicoRV32 SoC tren Tang Nano 20K (BRAM 32 KB) - Bai 3 */
ENTRY(_start)

MEMORY
{
    BRAM (rwx) : ORIGIN = 0x00000000, LENGTH = 32K
}

SECTIONS
{
    . = 0x00000000;

    .init : {
        KEEP(*(.init))
        KEEP(*(.init.*))
    } > BRAM

    .text : {
        . = ALIGN(4);
        *(.text)
        *(.text.*)
    } > BRAM

    .rodata : {
        . = ALIGN(4);
        *(.rodata)
        *(.rodata.*)
        *(.srodata)
        *(.srodata.*)
    } > BRAM

    .data : {
        . = ALIGN(4);
        _sdata = .;
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

    /* Đỉnh ngăn xếp nằm ở cuối vùng BRAM 32 KB (0x00008000) */
    . = ALIGN(16);
    __stack_top = ORIGIN(BRAM) + LENGTH(BRAM);
}
