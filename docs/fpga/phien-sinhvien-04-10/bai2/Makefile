# bai2/Makefile
# Bien dich firmware va tong hop bitstream cho 3 cau hinh H0, H1, H2

CROSS   ?= riscv64-unknown-elf-
CC      := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
SIZE    := $(CROSS)size

DEVICE  := GW2AR-LV18QN88C8/I7
FAMILY  := GW2A-18C
CST     := ../constraints/tangnano20k.cst

CFLAGS_BASE := -mabi=ilp32 -O2 -nostdlib -fno-builtin -fno-tree-loop-distribute-patterns -Wall -Wextra -Isw
CFLAGS_H0   := -march=rv32i_zicsr $(CFLAGS_BASE) -DHW_TAG=\"H0\"
CFLAGS_H1   := -march=rv32im_zicsr $(CFLAGS_BASE) -DHW_TAG=\"H1\"
CFLAGS_H2   := -march=rv32im_zicsr $(CFLAGS_BASE) -DHW_TAG=\"H2\"

RTL_COMMON := ../bai1/rtl/reset_gen.v \
              ../bai1/rtl/bus_interconnect.v \
              ../bai1/rtl/bram_mem.v \
              ../bai1/rtl/uart_tx.v \
              ../bai1/rtl/gpio_led.v \
              ../tai-lieu/picorv32.v

RTL_SRCS := rtl/soc_top.v $(RTL_COMMON)

SIM_SRCS := sim/tb_soc.v \
            ../bai1/sim/uart_rx_model.v \
            $(RTL_SRCS)

BUILD_DIR := build

.PHONY: all sw-h0 sw-h1 sw-h2 sim-h0 sim-h1 sim-h2 synth-h0 pnr-h0 bitstream-h0 synth-h1 pnr-h1 bitstream-h1 synth-h2 pnr-h2 bitstream-h2 clean verify header check-hex-h0 check-hex-h1 check-hex-h2

all: sw-h0 sw-h1 sw-h2

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# ----------------- SINH TONG KIEM CHUAN PYTHON -----------------
header: sw/golden_checksums.h

sw/golden_checksums.h: tools/golden_model.py
	python3 tools/golden_model.py --gen-header sw/golden_checksums.h

# ----------------- BIEN DICH FIRMWARE -----------------
sw-h0: $(BUILD_DIR) sw/golden_checksums.h
	rm -f firmware.hex ../firmware.hex
	$(CC) $(CFLAGS_H0) -T sw/linker.ld sw/start.S sw/main.c -o $(BUILD_DIR)/firmware_h0.elf -lgcc
	@echo "=== KICH THUOC PHAN VUNG H0 (rv32i) ==="
	$(SIZE) $(BUILD_DIR)/firmware_h0.elf
	$(OBJCOPY) -O binary $(BUILD_DIR)/firmware_h0.elf $(BUILD_DIR)/firmware_h0.bin
	python3 tools/elf2hex.py $(BUILD_DIR)/firmware_h0.bin $(BUILD_DIR)/firmware_h0.hex 8192
	cp $(BUILD_DIR)/firmware_h0.hex firmware.hex
	cp $(BUILD_DIR)/firmware_h0.hex ../firmware.hex
	@echo "H0" > $(BUILD_DIR)/firmware.tag

check-hex-h0: sw-h0
	@test -s firmware.hex || { echo "[LOI CHOT CHAN] firmware.hex khong ton tai hoac rong!"; exit 1; }
	@cmp -s firmware.hex $(BUILD_DIR)/firmware_h0.hex || { echo "[LOI CHOT CHAN] firmware.hex khong khop voi firmware_h0.hex!"; exit 1; }
	@cmp -s ../firmware.hex $(BUILD_DIR)/firmware_h0.hex || { echo "[LOI CHOT CHAN] ../firmware.hex khong khop voi firmware_h0.hex!"; exit 1; }
	@grep -q "^H0$$" $(BUILD_DIR)/firmware.tag || { echo "[LOI CHOT CHAN] Nhan phan cung khong phai H0!"; exit 1; }

sw-h1: $(BUILD_DIR) sw/golden_checksums.h
	rm -f firmware.hex ../firmware.hex
	$(CC) $(CFLAGS_H1) -T sw/linker.ld sw/start.S sw/main.c -o $(BUILD_DIR)/firmware_h1.elf -lgcc
	@echo "=== KICH THUOC PHAN VUNG H1 (rv32im) ==="
	$(SIZE) $(BUILD_DIR)/firmware_h1.elf
	$(OBJCOPY) -O binary $(BUILD_DIR)/firmware_h1.elf $(BUILD_DIR)/firmware_h1.bin
	python3 tools/elf2hex.py $(BUILD_DIR)/firmware_h1.bin $(BUILD_DIR)/firmware_h1.hex 8192
	cp $(BUILD_DIR)/firmware_h1.hex firmware.hex
	cp $(BUILD_DIR)/firmware_h1.hex ../firmware.hex
	@echo "H1" > $(BUILD_DIR)/firmware.tag

check-hex-h1: sw-h1
	@test -s firmware.hex || { echo "[LOI CHOT CHAN] firmware.hex khong ton tai hoac rong!"; exit 1; }
	@cmp -s firmware.hex $(BUILD_DIR)/firmware_h1.hex || { echo "[LOI CHOT CHAN] firmware.hex khong khop voi firmware_h1.hex!"; exit 1; }
	@cmp -s ../firmware.hex $(BUILD_DIR)/firmware_h1.hex || { echo "[LOI CHOT CHAN] ../firmware.hex khong khop voi firmware_h1.hex!"; exit 1; }
	@grep -q "^H1$$" $(BUILD_DIR)/firmware.tag || { echo "[LOI CHOT CHAN] Nhan phan cung khong phai H1!"; exit 1; }

sw-h2: $(BUILD_DIR) sw/golden_checksums.h
	rm -f firmware.hex ../firmware.hex
	$(CC) $(CFLAGS_H2) -T sw/linker.ld sw/start.S sw/main.c -o $(BUILD_DIR)/firmware_h2.elf -lgcc
	@echo "=== KICH THUOC PHAN VUNG H2 (rv32im) ==="
	$(SIZE) $(BUILD_DIR)/firmware_h2.elf
	$(OBJCOPY) -O binary $(BUILD_DIR)/firmware_h2.elf $(BUILD_DIR)/firmware_h2.bin
	python3 tools/elf2hex.py $(BUILD_DIR)/firmware_h2.bin $(BUILD_DIR)/firmware_h2.hex 8192
	cp $(BUILD_DIR)/firmware_h2.hex firmware.hex
	cp $(BUILD_DIR)/firmware_h2.hex ../firmware.hex
	@echo "H2" > $(BUILD_DIR)/firmware.tag

check-hex-h2: sw-h2
	@test -s firmware.hex || { echo "[LOI CHOT CHAN] firmware.hex khong ton tai hoac rong!"; exit 1; }
	@cmp -s firmware.hex $(BUILD_DIR)/firmware_h2.hex || { echo "[LOI CHOT CHAN] firmware.hex khong khop voi firmware_h2.hex!"; exit 1; }
	@cmp -s ../firmware.hex $(BUILD_DIR)/firmware_h2.hex || { echo "[LOI CHOT CHAN] ../firmware.hex khong khop voi firmware_h2.hex!"; exit 1; }
	@grep -q "^H2$$" $(BUILD_DIR)/firmware.tag || { echo "[LOI CHOT CHAN] Nhan phan cung khong phai H2!"; exit 1; }

# ----------------- MO PHONG -----------------
sim-h0: check-hex-h0
	iverilog -g2012 -I.. -o $(BUILD_DIR)/sim_h0.vvp -P soc_top.ENABLE_MUL=0 -P soc_top.ENABLE_FAST_MUL=0 -P tb_soc.HEX_FILE=firmware.hex $(SIM_SRCS)
	vvp $(BUILD_DIR)/sim_h0.vvp

sim-h1: check-hex-h1
	iverilog -g2012 -I.. -o $(BUILD_DIR)/sim_h1.vvp -P soc_top.ENABLE_MUL=1 -P soc_top.ENABLE_FAST_MUL=0 -P tb_soc.HEX_FILE=firmware.hex $(SIM_SRCS)
	vvp $(BUILD_DIR)/sim_h1.vvp

sim-h2: check-hex-h2
	iverilog -g2012 -I.. -o $(BUILD_DIR)/sim_h2.vvp -P soc_top.ENABLE_MUL=1 -P soc_top.ENABLE_FAST_MUL=1 -P tb_soc.HEX_FILE=firmware.hex $(SIM_SRCS)
	vvp $(BUILD_DIR)/sim_h2.vvp

# ----------------- DOI CHIEU LOG VOI MO HINH CHUAN -----------------
verify:
	python3 tools/golden_model.py --verify $(LOG)

# ----------------- TONG HOP & DONG GOI BITSTREAM H0 -----------------
synth-h0: check-hex-h0
	yosys -p "read_verilog -sv -I.. $(RTL_SRCS); chparam -set ENABLE_MUL 0 -set ENABLE_FAST_MUL 0 soc_top; synth_gowin -top soc_top -json $(BUILD_DIR)/soc_h0.json"

pnr-h0: synth-h0
	nextpnr-himbaechel --json $(BUILD_DIR)/soc_h0.json --write $(BUILD_DIR)/soc_h0_pnr.json --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST)

bitstream-h0: pnr-h0
	gowin_pack -d $(FAMILY) -o $(BUILD_DIR)/bai2_h0.fs $(BUILD_DIR)/soc_h0_pnr.json

# ----------------- TONG HOP & DONG GOI BITSTREAM H1 -----------------
synth-h1: check-hex-h1
	yosys -p "read_verilog -sv -I.. $(RTL_SRCS); chparam -set ENABLE_MUL 1 -set ENABLE_FAST_MUL 0 soc_top; synth_gowin -top soc_top -json $(BUILD_DIR)/soc_h1.json"

pnr-h1: synth-h1
	nextpnr-himbaechel --json $(BUILD_DIR)/soc_h1.json --write $(BUILD_DIR)/soc_h1_pnr.json --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST)

bitstream-h1: pnr-h1
	gowin_pack -d $(FAMILY) -o $(BUILD_DIR)/bai2_h1.fs $(BUILD_DIR)/soc_h1_pnr.json

# ----------------- TONG HOP & DONG GOI BITSTREAM H2 -----------------
synth-h2: check-hex-h2
	yosys -p "read_verilog -sv -I.. $(RTL_SRCS); chparam -set ENABLE_MUL 1 -set ENABLE_FAST_MUL 1 soc_top; synth_gowin -top soc_top -json $(BUILD_DIR)/soc_h2.json"

pnr-h2: synth-h2
	nextpnr-himbaechel --json $(BUILD_DIR)/soc_h2.json --write $(BUILD_DIR)/soc_h2_pnr.json --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST)

bitstream-h2: pnr-h2
	gowin_pack -d $(FAMILY) -o $(BUILD_DIR)/bai2_h2.fs $(BUILD_DIR)/soc_h2_pnr.json

clean:
	rm -rf $(BUILD_DIR) sw/golden_checksums.h
