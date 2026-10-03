# Môi trường phát triển và kiểm tra công cụ

**Thời điểm kiểm tra:** 03/10/2026  
**Hệ điều hành:** macOS (Apple Silicon / Darwin)

## 1. Danh sách công cụ & phiên bản đo được

| Vai trò | Tên lệnh | Đường dẫn | Phiên bản |
|---|---|---|---|
| C/C++ máy chủ | `cc` | `/usr/bin/cc` | Apple clang 21.0.0 (clang-2100.0.123.102) |
| Quản lý phiên bản | `git` | `/opt/homebrew/bin/git` | 2.55.0 |
| Trình biên dịch RISC-V | `riscv64-unknown-elf-gcc` | `/opt/homebrew/bin/riscv64-unknown-elf-gcc` | 14.2.0 (g04696df09) |
| Kích thước tệp ELF | `riscv64-unknown-elf-size` | `/opt/homebrew/bin/riscv64-unknown-elf-size` | GNU size 2.43.1 |
| Trích xuất nhị phân | `riscv64-unknown-elf-objcopy` | `/opt/homebrew/bin/riscv64-unknown-elf-objcopy` | GNU objcopy 2.43.1 |
| Tổng hợp Verilog FPGA | `yosys` | `/opt/homebrew/bin/yosys` | 0.69+post (git 143eb14f) |
| Đặt và đi dây Gowin | `nextpnr-himbaechel` | `~/.eide/cong-cu/oss-cad-suite/bin/nextpnr-himbaechel` | Hỗ trợ thiết bị GW2AR-LV18QN88C8/I7 |
| Soát lỗi HDL | `verilator` | `/opt/homebrew/bin/verilator` | 5.052 2026-09-05 |
| Mô phỏng Verilog | `iverilog` | `/opt/homebrew/bin/iverilog` | Đã kiểm tra qua `hdl.sim` (trả về PASS) |

---

## 2. Kết quả tổng hợp mạch mẫu Blinky

- **Thiết kế:** `rtl/blinky.v`, bộ chia tần số từ thạch anh 27 MHz đảo 6 LED mỗi 0,5 giây.
- **Ràng buộc chân:** `constraints/tangnano20k.cst` (CLK chân 4, S1 chân 88, LED chân 15–20).
- **Kết quả PnR (nextpnr-himbaechel):**
  - **Fmax:** 315,16 MHz (ĐẠT mục tiêu 27 MHz).
  - **Tài nguyên silicon:**
    - LUT4: 79 / 20 736 (0,38 %)
    - DFF: 31 / 15 552 (0,20 %)
    - ALU: 54 / 15 552 (0,35 %)
    - IOB: 8 / 384 (2,08 %)

---

## 3. Kết quả tổng hợp thử lõi PicoRV32 trần

- **Mã nguồn:** `picorv32.v` (từ repo Claire Wolf / YosysHQ).
- **Công cụ:** `synth_gowin -top picorv32` (Yosys).
- **Tài nguyên ước tính:**
  - **LUT:** 1 951 ô (~9,4 % tổng số LUT của GW2AR-18C).
  - **Flip-Flop (FF):** 573 ô (~3,7 % tổng số FF).
  - **RAM16SDP4:** 32 ô (register file phân tán).
- **Đánh giá:** Lõi PicoRV32 chiếm dưới 10 % tài nguyên của chip, hoàn toàn đủ diện tích để tích hợp BRAM, UART và các khối tăng tốc sau này.
