CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

CFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
         -O0 -g3 -Wall -Wextra -ffunction-sections -fdata-sections -nostdlib \
         -I. -Ifree_rtos/include -Ifree_rtos/portable/GCC/ARM_CM4F -Ivendor -I../tham-chieu-lcd

LDFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
          -T stm32f469ni.ld -nostdlib -Wl,--gc-sections -Wl,-Map=firmware.map

SRCS = startup.c \
       libc_stub.c \
       main.c \
       ui.c \
       touch.c \
       free_rtos/tasks.c \
       free_rtos/list.c \
       free_rtos/queue.c \
       free_rtos/portable/GCC/ARM_CM4F/port.c \
       free_rtos/portable/MemMang/heap_4.c \
       vendor/stm32f4xx_hal_dsi.c \
       vendor/stm32f4xx_hal_ltdc.c \
       vendor/stm32f4xx_hal_dma2d.c \
       vendor/stm32f4xx_hal_sdram.c \
       vendor/stm32f4xx_ll_fmc.c \
       ../tham-chieu-lcd/stm32469i_discovery.c \
       ../tham-chieu-lcd/stm32469i_discovery_lcd.c \
       ../tham-chieu-lcd/stm32469i_discovery_sdram.c \
       ../tham-chieu-lcd/otm8009a.c \
       ../tham-chieu-lcd/otm8009a_reg.c \
       ../tham-chieu-lcd/font12.c \
       ../tham-chieu-lcd/font16.c \
       ../tham-chieu-lcd/font20.c \
       ../tham-chieu-lcd/font24.c \
       ../tham-chieu-lcd/logo_ptit.c

OBJS = $(patsubst %.c,build_objs/%.o,$(notdir $(SRCS)))
VPATH = . free_rtos free_rtos/portable/GCC/ARM_CM4F free_rtos/portable/MemMang vendor ../tham-chieu-lcd

all: build_objs firmware.bin

build_objs:
	mkdir -p build_objs

firmware.elf: $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@
	$(SIZE) $@

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

build_objs/%.o: %.c | build_objs
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf build_objs firmware.elf firmware.bin firmware.map
