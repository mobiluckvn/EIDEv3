# bai1/Makefile
# Điều phối build firmware, sim, synth, pnr, bitstream cho Bài 1

CROSS   ?= riscv64-unknown-elf-
CC      := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
SIZE    := $(CROSS)size

DEVICE  := GW2AR-LV18QN88C8/I7
FAMILY  := GW2A-18C
CST     := ../constraints/tangnano20k.cst

RTL_SRCS := rtl/soc_top.v \
            rtl/reset_gen.v \
            rtl/bus_interconnect.v \
            rtl/bram_mem.v \
            rtl/uart_tx.v \
            rtl/gpio_led.v \
            ../tai-lieu/picorv32.v

SIM_SRCS := sim/tb_soc.v \
            sim/uart_rx_model.v \
            $(RTL_SRCS)

CFLAGS := -march=rv32i_zicsr -mabi=ilp32 -O2 -nostdlib -Wall -Wextra

BUILD_DIR := build

.PHONY: all sw sw-sim sim synth pnr bitstream load flash clean

all: sim

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# 1. Firmware cho mô phỏng (-DSIM)
sw-sim: $(BUILD_DIR)
	$(CC) $(CFLAGS) -DSIM -T sw/linker.ld sw/start.S sw/main.c -o $(BUILD_DIR)/firmware_sim.elf
	$(SIZE) $(BUILD_DIR)/firmware_sim.elf
	$(OBJCOPY) -O binary $(BUILD_DIR)/firmware_sim.elf $(BUILD_DIR)/firmware_sim.bin
	python3 tools/elf2hex.py $(BUILD_DIR)/firmware_sim.bin firmware.hex 8192

# 2. Firmware cho bo thật (1 giây thật)
sw: $(BUILD_DIR)
	$(CC) $(CFLAGS) -T sw/linker.ld sw/start.S sw/main.c -o $(BUILD_DIR)/firmware.elf
	$(SIZE) $(BUILD_DIR)/firmware.elf
	$(OBJCOPY) -O binary $(BUILD_DIR)/firmware.elf $(BUILD_DIR)/firmware.bin
	python3 tools/elf2hex.py $(BUILD_DIR)/firmware.bin $(BUILD_DIR)/firmware.hex 8192
	cp $(BUILD_DIR)/firmware.hex firmware.hex

# 3. Mô phỏng testbench iverilog
sim: sw-sim
	iverilog -g2012 -o $(BUILD_DIR)/sim.vvp $(SIM_SRCS)
	vvp $(BUILD_DIR)/sim.vvp

# 4. Tổng hợp Yosys
synth: sw $(BUILD_DIR)
	yosys -p "read_verilog -sv $(RTL_SRCS); synth_gowin -top soc_top -json $(BUILD_DIR)/soc_top.json"

# 5. Đặt-đi dây NextPNR
pnr: synth
	nextpnr-himbaechel --json $(BUILD_DIR)/soc_top.json \
	                   --write $(BUILD_DIR)/soc_top_pnr.json \
	                   --device $(DEVICE) \
	                   --vopt family=$(FAMILY) \
	                   --vopt cst=$(CST)

# 6. Đóng gói bitstream .fs
bitstream: pnr
	gowin_pack -d $(FAMILY) -o $(BUILD_DIR)/bai1.fs $(BUILD_DIR)/soc_top_pnr.json
	@echo "Bitstream hoàn tất: $(BUILD_DIR)/bai1.fs"

# 7. Nạp SRAM kit (G-FLASH cổng an toàn cần duyệt)
load:
	openFPGALoader -b tangnano20k $(BUILD_DIR)/bai1.fs

# 8. Nạp Flash kit
flash:
	openFPGALoader -b tangnano20k -f $(BUILD_DIR)/bai1.fs

clean:
	rm -rf $(BUILD_DIR) firmware.hex
