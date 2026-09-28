CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
SIZE = arm-none-eabi-size

CFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
         -O0 -g3 -Wall -Wextra -ffunction-sections -fdata-sections -nostdlib \
         -I. -Ifree_rtos/include -Ifree_rtos/portable/GCC/ARM_CM4F

LDFLAGS = -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard \
          -T stm32f469ni.ld -nostdlib -Wl,--gc-sections -Wl,-Map=firmware.map

SRCS = startup.c \
       libc_stub.c \
       main.c \
       free_rtos/tasks.c \
       free_rtos/list.c \
       free_rtos/queue.c \
       free_rtos/portable/GCC/ARM_CM4F/port.c \
       free_rtos/portable/MemMang/heap_4.c

OBJS = $(SRCS:.c=.o)

all: firmware.bin

firmware.elf: $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@
	$(SIZE) $@

firmware.bin: firmware.elf
	$(OBJCOPY) -O binary $< $@

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) firmware.elf firmware.bin firmware.map
