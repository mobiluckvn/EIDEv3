# Môi trường làm việc (macOS)

Tài liệu ghi lại cấu hình máy chủ và hiện trạng công cụ trên máy phát triển cho dự án RISC-V trên Sipeed Tang Nano 20K.

## 1. Thông tin máy chủ
- **Hệ điều hành:** macOS (Darwin)
- **Kiến trúc chip:** `arm64` (Apple Silicon — đường dẫn Homebrew `/opt/homebrew/`)

## 2. Kết quả kiểm tra công cụ qua EIDE (`env.check`)

### A. Nhóm công cụ FPGA Gowin (`fpga-gowin`)
Được kiểm tra trực tiếp qua `env.check(isa="fpga-gowin")`:
- Tổng số công cụ quét: 9
- Đã có: 9 / Thiếu: 0

| Công cụ | Trạng thái | Phiên bản đọc được | Đường dẫn thực tế | Mục đích sử dụng |
|---|---|---|---|---|
| `yosys` | **ĐÃ CÓ** | `Yosys 0.69+post` | `/opt/homebrew/bin/yosys` | Tổng hợp Verilog (`synth_gowin`) |
| `nextpnr-himbaechel` | **ĐÃ CÓ** | nextpnr trong oss-cad-suite | `/Users/congvt/.eide/cong-cu/oss-cad-suite/bin/nextpnr-himbaechel` | Đặt-đi dây cho chip Gowin GW2A-18C |
| `gowin_pack` | **ĐÃ CÓ** | Apicula trong oss-cad-suite | `/Users/congvt/.eide/cong-cu/oss-cad-suite/bin/gowin_pack` | Đóng gói bitstream `.fs` |
| `openFPGALoader` | **ĐÃ CÓ** | `v1.1.1` | `/Users/congvt/.eide/cong-cu/oss-cad-suite/bin/openFPGALoader` | Nạp bitstream vào SRAM / Flash của kit |
| `verilator` | **ĐÃ CÓ** | `5.052` | `/opt/homebrew/bin/verilator` | Mô phỏng nhanh, đo số chu kỳ (Bài 2, Bài 3) |
| `iverilog` | **ĐÃ CÓ** | có sẵn | `/opt/homebrew/bin/iverilog` | Mô phỏng testbench nhỏ, kiểm từng khối |
| `gtkwave` | **ĐÃ CÓ** | có sẵn trong gói | `/Users/congvt/.eide/cong-cu/oss-cad-suite/bin/gtkwave` | Xem dạng sóng tín hiệu |
| `cc` | **ĐÃ CÓ** | `Apple clang version 21.0.0` | `/usr/bin/cc` | Biên dịch mô phỏng C máy chủ |
| `git` | **ĐÃ CÓ** | `git version 2.55.0` | `/opt/homebrew/bin/git` | Quản lý phiên bản mã nguồn |

### B. Chuỗi công cụ RISC-V Bare-metal (`rv32i`, `rv32im`, `rv32imac`)
Được kiểm tra trực tiếp qua `env.check(isa="rv32i")`:
- Tổng số công cụ: 5 / Đã có: 5 / Thiếu: 0
- Trạng thái biên dịch: `bien_dich_duoc: true`

| Công cụ | Trạng thái | Phiên bản đọc được | Đường dẫn thực tế | Ghi chú |
|---|---|---|---|---|
| `riscv64-unknown-elf-gcc` | **ĐÃ CÓ** | `14.2.0 (g04696df09)` | `/opt/homebrew/bin/riscv64-unknown-elf-gcc` | Hỗ trợ cờ `-march=rv32i_zicsr`, `-mabi=ilp32` |
| `riscv64-unknown-elf-objcopy` | **ĐÃ CÓ** | `GNU objcopy 2.43.1` | `/opt/homebrew/bin/riscv64-unknown-elf-objcopy` | Tự động sinh hex `$readmemh` (1 từ 32-bit/dòng) |
| `riscv64-unknown-elf-size` | **ĐÃ CÓ** | `GNU size 2.43.1` | `/opt/homebrew/bin/riscv64-unknown-elf-size` | Kiểm tra kích thước phân vùng BRAM |
| `cc` | **ĐÃ CÓ** | `Apple clang version 21.0.0` | `/usr/bin/cc` | Trình biên dịch C máy chủ |
| `git` | **ĐÃ CÓ** | `2.55.0` | `/opt/homebrew/bin/git` | Quản lý mã nguồn |

---

## 3. Điểm dừng số 2 (Phần F) & Công cụ chưa cài

1. **Gowin EDA Education bản macOS:** Hiện chưa có. Cần tải từ trang chủ `gowinsemi.com` (yêu cầu đăng ký tài khoản). Tác tử không tự tải khi chưa có sự đồng ý của anh Công.
2. **Quyền quản trị (`sudo`):** Các công cụ trong nhóm `fpga-gowin` và toolchain RISC-V đều đã được bố trí trong Homebrew (`/opt/homebrew`) và thư mục người dùng (`~/.eide/cong-cu/`), do đó **không cần quyền quản trị** để chạy luồng mã nguồn mở.

## Gowin EDA Education cho macOS — đã có, chưa cài

*01/10/2026. Điểm dừng số 2 của đề bài đã được anh Công gỡ: anh ấy tự tạo tài khoản và đăng
nhập, rồi cho phép tải.*

| | |
|---|---|
| Tệp | `~/Downloads/Gowin_V1.9.11.03Education_macOS.dmg` |
| Kích thước | **686 639 001 byte** (655 MB) — khớp từng byte với con số máy chủ báo |
| Định dạng | ảnh đĩa macOS (nén bzip2) |
| Bản | **V1.9.11.03 Education** — bản miễn phí, không cần license, đúng bản đề bài nêu |

**Chưa cài.** Việc cài là của Agent, không ai cài hộ.

### Một chỗ dễ trượt khi tìm tệp này

Trang tải của Gowin chỉ có **hai** mục: *Software for Windows* và *Software for Linux*. Nhìn
qua thì tưởng không có bản macOS. Nhưng **ba bản macOS nằm trong mục "Software for Linux"**:

- Gowin V1.9.12.04 (macOS)
- Gowin V1.9.12 (macOS) TUV Certified
- **Gowin V1.9.11.03 Education (macOS)** ← bản đã tải

Ai chỉ đọc tên hai mục rồi kết luận "Gowin không có bản macOS" sẽ kết luận sai. Đây đúng loại
chỗ phải mở ra xem chứ không đọc nhãn.
