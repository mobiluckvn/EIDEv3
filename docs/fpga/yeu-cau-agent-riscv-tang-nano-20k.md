# ĐẶC TẢ BÀI TOÁN CHO TÁC TỬ (AGENT)
## Lõi RISC‑V trên Sipeed Tang Nano 20K: từ "Hello" đến nhân ma trận

- Phiên bản: 1.1, ngày 01/10/2026. So với v1.0: bổ sung môi trường macOS và mô tả chi tiết từng bài.
- Người giao việc: CongVT
- Người thực hiện: tác tử (agent) chạy trên máy macOS

---

## PHẦN A. BỐI CẢNH VÀ CÁCH LÀM VIỆC

### A1. Bối cảnh
CongVT muốn tiến dần tới việc đưa phép nhân ma trận (lõi tính toán của mô hình AI) xuống phần cứng FPGA. Bước đầu dùng một kit giá rẻ, Sipeed Tang Nano 20K (chip Gowin GW2AR‑18), với hai mục tiêu:

1. Biến FPGA thành một CPU RISC‑V nhỏ chạy được chương trình C.
2. Đo chính xác chi phí nhân ma trận trên CPU đó, gọi là **đường cơ sở (baseline)**.

Việc thêm phần cứng chuyên dụng để giảm chi phí ấy từng là mục tiêu thứ ba, và đã được đưa ra khỏi phạm vi ngày 02/10/2026 — xem PHẦN I.

### A2. Kết quả cuối cùng mong muốn
- Một kho mã (repository) Git chạy lại được toàn bộ từ đầu trên macOS bằng vài lệnh `make`.
- Một bảng số liệu so sánh **số chu kỳ trên mỗi phép nhân‑cộng (cycles/MAC)** giữa các cấu hình CPU: không có bộ nhân, bộ nhân tuần tự, bộ nhân nhanh dùng DSP.
- Số liệu đo trên **mô phỏng** và trên **kit thật** khớp nhau.

### A3. Quy tắc bắt buộc cho tác tử
1. **Mọi thông số phần cứng phải có nguồn.** Không đoán chân, tần số, tên thiết bị. Mục nào đánh dấu **[XÁC MINH]** là giá trị ban đầu, phải đối chiếu với Sipeed wiki, sơ đồ nguyên lý hoặc tài liệu Gowin, và ghi link.
2. **Mô phỏng trước, nạp sau.** Bài nào chưa qua tiêu chí nghiệm thu mô phỏng thì không nạp lên kit.
3. **Không tự mua hàng, không tự cài phần mềm cần quyền quản trị** khi chưa được CongVT đồng ý.
4. **Mỗi kết quả đều có kiểm chứng tự động.** Testbench phải tự kiểm tra và in `PASS`/`FAIL`. Không dựa vào việc người xem dạng sóng.
5. Giữ nguyên giấy phép (license) của mã nguồn mở. Ghi phiên bản/commit đã dùng vào `docs/third_party.md`.
6. Báo cáo bằng tiếng Việt. Thuật ngữ tiếng Anh giữ nguyên thì giải thích tiếng Việt ở lần đầu xuất hiện.
7. Gặp **điểm dừng bắt buộc** (Phần F) thì dừng, gửi báo cáo, chờ trả lời.

---

## PHẦN B. MÔI TRƯỜNG LÀM VIỆC (macOS)

### B1. Máy chủ
- macOS. Tác tử phải ghi lại phiên bản macOS và kiến trúc chip (Apple Silicon `arm64` hay Intel `x86_64`) vào `docs/env.md`.

### B2. Công cụ

| Vai trò | Công cụ | Cách cài gợi ý | Ghi chú |
|---|---|---|---|
| Tổng hợp, đặt‑đi dây, đóng gói bitstream (luồng chính) | Yosys (`synth_gowin`), nextpnr‑himbaechel, Apicula (`gowin_pack`) | Bộ **oss‑cad‑suite** bản darwin (arm64 hoặc x64) | Chạy hoàn toàn bằng dòng lệnh, phù hợp tự động hoá |
| Nạp bitstream | openFPGALoader | có trong oss‑cad‑suite hoặc Homebrew | Board: `tangnano20k` [XÁC MINH] |
| Luồng đối chiếu | Gowin EDA **Education** bản macOS (miễn phí, không cần license) | Tải từ gowinsemi.com (cần tài khoản) | Dùng để đối chiếu timing/tài nguyên và làm dự phòng. Bản cũ có thể cần script sửa liên kết thư viện của cộng đồng |
| Mô phỏng nhanh, đo chu kỳ | **Verilator** | Homebrew hoặc oss‑cad‑suite | Bắt buộc cho Bài 2 |
| Mô phỏng testbench nhỏ | Icarus Verilog + GTKWave | oss‑cad‑suite | Cho unit test |
| Mô phỏng VHDL | GHDL | chỉ khi chọn NEORV32 | Phải kiểm tra chạy được trên kiến trúc máy |
| Biên dịch phần mềm RISC‑V | GCC bare‑metal: `riscv64-unknown-elf-gcc` (Homebrew tap riscv) hoặc `riscv-none-elf-gcc` (xPack) | | Cờ: `-march=rv32i_zicsr` hoặc `rv32im_zicsr`, `-mabi=ilp32` |
| Kiểm chứng số liệu | Python 3 + NumPy (+ matplotlib để vẽ biểu đồ) | `venv` + pip | Mô hình chuẩn (golden model) |
| Terminal nối tiếp | `picocom` hoặc `screen` | Homebrew | Đọc UART từ kit |

### B3. Kiểm tra môi trường sớm (bắt buộc ở G1)
1. `make check-env`: in phiên bản mọi công cụ.
2. **Blinky toolchain mở:** tổng hợp ví dụ nháy LED cho Tang Nano 20K đến tận file `.fs`. Chưa cần kit.
3. **BRAM hai cổng:** tổng hợp và đặt‑đi dây một module RAM hai cổng tối giản (đọc/ghi độc lập trên hai cổng) bằng toolchain mở.
   - Nếu lỗi (ví dụ thiếu primitive DPB/DPX9), ghi lại thông báo lỗi và thử lại bằng Gowin EDA.
4. **Tổng hợp thử PicoRV32 trần** (không SoC) để biết tài nguyên lõi chiếm.

---

## PHẦN C. CẤU TRÚC KHO MÃ VÀ QUY ƯỚC

```
riscv-tn20k/
├── README.md              # cách chạy lại toàn bộ
├── Makefile               # điều phối, gọi Makefile con
├── docs/
│   ├── hardware-facts.md  # G0: thông số đã xác minh + nguồn
│   ├── env.md             # G1: môi trường
│   ├── decisions.md       # các quyết định thiết kế + lý do
│   ├── third_party.md     # lõi/thư viện bên ngoài + license + commit
│   └── troubleshooting.md
├── constraints/tangnano20k.cst
├── third_party/picorv32/  # git submodule
├── rtl/                   # mã HDL chung (uart_tx, bram, soc_top…)
├── bai1/  bai2/           # mỗi bài: rtl/ sw/ sim/ results/
└── tools/                 # gen_data.py, parse_log.py, plot.py
```

### Các lệnh `make` chuẩn (mỗi bài đều có)

| Lệnh | Việc làm |
|---|---|
| `make sw` | Biên dịch C → `.elf` → `.hex` (để nạp sẵn vào BRAM) |
| `make sim` | Mô phỏng, in `PASS`/`FAIL` |
| `make bitstream` | Yosys → nextpnr → gowin_pack → `.fs`, kèm báo cáo tài nguyên |
| `make load` | Nạp `.fs` vào SRAM của kit (mất khi tắt nguồn) |
| `make flash` | Nạp vào flash (giữ khi tắt nguồn) |
| `make term` | Mở terminal nối tiếp đúng cổng, đúng baud |

---

## PHẦN D. CÁC GIAI ĐOẠN VÀ BÀI TẬP

### G0. Thu thập thông tin

**Mục tiêu:** có bảng thông số đã xác minh trước khi viết dòng HDL đầu tiên.

**Bảng cần lập** (`docs/hardware-facts.md`, mỗi dòng có link nguồn):

| # | Thông số | Giá trị ban đầu [XÁC MINH] |
|---|---|---|
| 1 | Mã chip, chuỗi device cho nextpnr/gowin_pack và cho Gowin EDA | GW2AR‑LV18QN88C8/I7; family GW2A‑18C |
| 2 | LUT4, flip‑flop | ~20.736 LUT4, ~15.552 FF |
| 3 | BSRAM: số khối, dung lượng mỗi khối, tổng KB | cần tra (dự kiến ~46 khối × 18 Kbit) |
| 4 | Số khối DSP / bộ nhân cứng | cần tra |
| 5 | Thạch anh và chân clock | 27 MHz, chân cần tra |
| 6 | 6 chân LED, mức tích cực (thường tích cực thấp) | cần tra |
| 7 | Chân nút S1, S2 | cần tra |
| 8 | Chân UART TX/RX nối tới chip cầu USB (BL616) | cần tra |
| 9 | Tên cổng serial trên macOS khi cắm kit (thường là `/dev/tty.usbserial-*`, có thể có 2 cổng) | cần tra |
| 10 | Chân đa chức năng (dual‑purpose) cần cấu hình riêng | cần tra |
| 11 | PLL: tần số ra hợp lệ từ 27 MHz | cần tra |
| 12 | Dự án mẫu chính thức của Sipeed (LED, UART, RISC‑V) | link |

**Nghiệm thu:** đủ 12 dòng, có nguồn. Chân clock và UART lấy từ nguồn chính thức. File `constraints/tangnano20k.cst` chỉ chứa chân đã xác minh.

---

### G1. Dựng môi trường
Làm đủ Phần B. **Nghiệm thu:** 4 kiểm tra ở mục B3 có kết quả rõ ràng, ghi vào `docs/env.md`.

**Quyết định lõi:** mặc định **PicoRV32** (Verilog), vì:
- Nhỏ.
- Có bộ đếm chu kỳ (`rdcycle`).

NEORV32 (VHDL) chỉ dùng khi CongVT yêu cầu.

---

### BÀI 1. SoC tối thiểu in "Hello" qua UART

**Bài toán:** xây một hệ thống trên chip (SoC) gồm CPU PicoRV32, bộ nhớ BRAM và cổng UART. Chương trình C chạy trên CPU in chuỗi ký tự ra máy tính qua cáp USB‑C.

**Đặc tả phần cứng:**

1. **CPU:** PicoRV32 với các tham số:
   - `ENABLE_COUNTERS=1`, `ENABLE_COUNTERS64=1`
   - `ENABLE_MUL=0`, `ENABLE_DIV=0`, `ENABLE_PCPI=0`
   - `COMPRESSED_ISA=0`
   - `PROGADDR_RESET=0x0000_0000`, `STACKADDR` = đỉnh BRAM
2. **Bộ nhớ:** BRAM một khối dùng chung lệnh và dữ liệu.
   - Kích thước mục tiêu 32 KB; giảm xuống 16 KB nếu BSRAM không đủ.
   - Nạp sẵn chương trình lúc tổng hợp bằng `$readmemh`.
   - Hỗ trợ ghi từng byte theo `mem_wstrb`.
3. **Bản đồ địa chỉ:**

   | Địa chỉ | Thiết bị | Truy cập |
   |---|---|---|
   | `0x0000_0000` – đỉnh BRAM | BRAM | đọc/ghi |
   | `0x1000_0000` | UART_TX: ghi 1 byte để gửi | ghi |
   | `0x1000_0004` | UART_STATUS: bit 0 = 1 nghĩa là đang bận gửi | đọc |
   | `0x2000_0000` | LED: 6 bit thấp | ghi |

   Địa chỉ không hợp lệ: trả `mem_ready` để CPU không treo, đọc ra 0.
4. **UART TX:** 115200 baud, 8N1, mức nghỉ = 1.
   - Bộ chia từ 27 MHz: 27.000.000 / 115.200 ≈ 234,375. Dùng 234, sai số ≈ +0,16%, chấp nhận được.
   - Tham số hoá bộ chia theo tần số clock để dùng lại khi đổi PLL.
5. **Clock và reset:** chạy thẳng 27 MHz (chưa dùng PLL). Reset gồm power‑on‑reset (giữ reset ~16 chu kỳ đầu) và nút S1.
6. **LED:** do phần mềm điều khiển, để nhìn biết CPU đang chạy.

**Đặc tả phần mềm (`bai1/sw/`):**
- `start.S`: đặt `sp`, xoá `.bss`, gọi `main`.
- `linker.ld`: đặt `.text`, `.data`, `.bss` trong BRAM.
- `main.c`: vòng lặp vô hạn, mỗi ~1 giây (đo bằng `rdcycle`, 27.000.000 chu kỳ) làm hai việc:
  - In `Hello from PicoRV32 on Tang Nano 20K, cycle=<số>\r\n`.
  - Đảo trạng thái một LED.
- Script chuyển `.elf` → `.hex` đúng định dạng `$readmemh` (từ 32‑bit, little‑endian).

**Mô phỏng (`bai1/sim/`):**
- Testbench chạy toàn SoC. Có một **bộ thu UART mô hình** trong testbench để giải mã từng byte theo đúng baud.
- Để mô phỏng nhanh, cho phép biên dịch phần mềm với hằng "1 giây" nhỏ hơn qua `-DSIM`.
- Testbench in `PASS` khi nhận đúng chuỗi `Hello from PicoRV32` ít nhất 2 lần; ngược lại `FAIL` sau giới hạn thời gian.

**Sản phẩm bàn giao:** mã nguồn; `make sim` ra PASS; `make bitstream` ra `.fs`; báo cáo tài nguyên (LUT/FF/BSRAM) và Fmax.

**Nghiệm thu:**
- Mô phỏng PASS.
- Fmax ≥ 27 MHz.
- Không có cảnh báo latch/multi‑driven.
- Trên kit (sau G4): terminal hiện chuỗi lặp lại, LED nháy. Sau `make flash` và cấp lại nguồn vẫn chạy.

---

### BÀI 2. Nhân ma trận bằng C, đo số chu kỳ

**Bài toán:** tính C = A × B cho ma trận vuông N×N trên CPU của Bài 1. Đo chính xác số chu kỳ máy cho từng cách cài đặt và từng cấu hình CPU, để biết **cấu hình CPU nào đổi được gì**, và đổi bao nhiêu.

**Tham số thử nghiệm:**
- N ∈ {4, 8, 16, 32}. Tác tử tính dung lượng: 3 ma trận × N² × kích thước phần tử phải vừa BRAM cùng với chương trình. N nào không vừa thì ghi rõ và bỏ.
- Hai kiểu dữ liệu:
  - `I32`: A, B, C đều `int32_t`.
  - `I8`: A, B là `int8_t`, C là `int32_t` (cộng dồn). Đây là kiểu của mô hình AI lượng tử hoá (quantized).

**Bốn cách cài đặt (mỗi cách một hàm, cùng chữ ký):**

| Mã | Mô tả |
|---|---|
| V0 | Ba vòng lặp i‑j‑k cơ bản |
| V1 | Thứ tự i‑k‑j (đọc B theo hàng, liên tục hơn) |
| V2 | V1 + mở vòng lặp trong (loop unrolling) ×4 |
| V3 | Chia khối (tiling) 4×4 hoặc 8×8; chỉ áp dụng N ≥ 16 |

**Ba cấu hình phần cứng:**

| Mã | Tham số PicoRV32 | Cờ GCC |
|---|---|---|
| H0 | RV32I (không nhân cứng, nhân bằng `libgcc`) | `-march=rv32i_zicsr` |
| H1 | `ENABLE_MUL=1` | `-march=rv32im_zicsr` |
| H2 | `ENABLE_FAST_MUL=1` (dùng DSP) | `-march=rv32im_zicsr` |

Mọi bản biên dịch dùng `-O2`, ghi cờ vào báo cáo.

**Dữ liệu và kiểm chứng:**
- `tools/gen_data.py --n N --dtype I8|I32 --seed 2026` sinh A, B ngẫu nhiên. Giá trị I8 trong [−128, 127]; giá trị I32 trong [−1000, 1000] để không tràn số. Xuất `data_N_dtype.h`.
- Script tính C bằng NumPy và một **tổng kiểm (checksum)** cố định, ví dụ tổng có trọng số `Σ C[i][j]·(i·N+j+1) mod 2³²`, rồi ghi vào header làm đáp án.

**Đo chu kỳ:**
- Đọc bộ đếm 64‑bit (`rdcycle`/`rdcycleh`) ngay trước và sau lời gọi hàm.
- Trừ đi chi phí của chính phép đọc bộ đếm. Đo riêng bằng hai lần đọc liền nhau.
- Mỗi phép đo chạy 3 lần, lấy giá trị nhỏ nhất.

**Định dạng in qua UART (một dòng mỗi kết quả, để máy đọc được):**
```
RESULT,n=16,dtype=I8,ver=V1,hw=H2,cycles=123456,macs=4096,cpm=30.14,chk=0x1A2B3C4D,ok=1
```
- `cpm` = cycles/MAC; số MAC = N³.
- `ok=1` khi checksum khớp đáp án.

**Mô phỏng:**
- Dùng **Verilator** cho đo chu kỳ, vì Icarus quá chậm với H0, N=32.
- Testbench thu dòng UART, ghi ra `results/sim.log`.
- `tools/parse_log.py` chuyển log thành `results/bai2.csv` với các cột: n, dtype, ver, hw, cycles, macs, cpm, ok, source (`sim`/`board`).
- `tools/plot.py` vẽ cpm theo N cho từng cấu hình.

**Nghiệm thu:**
- 100% dòng `ok=1`.
- Số chu kỳ sim và board chênh ≤ 1%. Hệ BRAM là đồng bộ và xác định, nên hai con số phải gần như trùng. Nếu lệch, tác tử phải tìm nguyên nhân.
- Báo cáo nêu mức tăng tốc H1/H0, H2/H0, và cách cài đặt tốt nhất.

---

## PHẦN E. MUA KIT, NẠP VÀ CHẠY THẬT (G4)

### E1. Lập phương án mua: tác tử KHÔNG tự đặt hàng
- Kit: **Sipeed Tang Nano 20K**. Tham khảo đầu tiên: https://hshop.vn/sipeed-tang-nano-20k-gowin-gw2ar-18-fpga-development-board (đã thấy giá ~890.000đ, từng hết hàng).
- Kiểm tra thêm ít nhất 2 nơi: cửa hàng trong nước khác và cửa hàng chính hãng Sipeed trên AliExpress.
- Lập bảng: nơi bán, giá, phí ship, thời gian giao, bản có hàn sẵn header hay không, tình trạng hàng.
- Phụ kiện:
  - Cáp USB‑C **có truyền dữ liệu**.
  - Bộ chuyển USB‑UART rời (CH340/CP2102, tuỳ chọn, dự phòng).
  - Breadboard và dây cắm (tuỳ chọn).
- **Gửi bảng cho CongVT duyệt.**

Lưu ý: G0 → Bài 2 (phần mô phỏng) không cần kit, có thể làm song song trong lúc chờ hàng.

### E2. Kiểm tra khi nhận kit (trên macOS)
1. Cắm kit. Chạy `ls /dev/tty.*` và `openFPGALoader --detect` [XÁC MINH cú pháp]. Ghi lại tên cổng serial và kết quả nhận chip vào `docs/env.md`.
2. Nạp blinky từ G1 bằng `make load`. Xác nhận LED nháy.
3. Mở `make term`. Xác nhận cổng serial mở được.

### E3. Thứ tự chạy test

| Bước | Việc | Điều kiện qua |
|---|---|---|
| 1 | Blinky | LED nháy |
| 2 | Bài 1, nạp SRAM | Thấy `Hello…` |
| 3 | Bài 1, nạp flash, cấp lại nguồn | Vẫn chạy |
| 4 | Bài 2: H0, H1, H2 | `ok=1`, lệch sim ≤ 1% |

Các bước cần người thao tác vật lý (cắm cáp, nhấn reset, nhìn LED): tác tử ghi rõ "CẦN NGƯỜI" và hướng dẫn từng thao tác cho CongVT.

### E4. Xử lý sự cố (ghi vào `docs/troubleshooting.md`)
- Không thấy chữ: sai cổng (thử cổng serial thứ hai của BL616), sai baud, đảo TX/RX trong `.cst`, mức nghỉ UART sai.
- Ký tự rác: sai bộ chia baud so với tần số clock thực.
- Nạp được nhưng không chạy: reset bị giữ; chân dual‑purpose chưa cấu hình; `.hex` không được nạp vào BRAM (kiểm tra đường dẫn `$readmemh` và log Yosys).
- openFPGALoader không thấy kit: thử cáp khác, kiểm tra quyền USB/libusb trên macOS.

---

## PHẦN F. ĐIỂM DỪNG BẮT BUỘC (tác tử phải hỏi CongVT)
1. Sau G0, nếu thông số nào không xác minh được từ nguồn chính thức.
2. Trước khi cài phần mềm cần quyền quản trị hoặc tải bản Gowin EDA cần tài khoản.
3. Trước khi đặt mua kit (E1).
4. Khi LUT > 85% hoặc không đạt timing sau 2 lần tối ưu.
5. Khi bước tiếp theo cần thao tác vật lý trên kit.

---

## PHẦN G. MẪU BÁO CÁO SAU MỖI BÀI

```
Bài: …            Ngày: …           Commit: …
Máy: macOS …, arm64/x86_64
Luồng công cụ: oss-cad-suite <ngày bản> / Gowin EDA <phiên bản>
Cấu hình lõi: …   Tần số: … MHz
Tài nguyên: LUT …/…  FF …/…  BSRAM …/…  DSP …/…  Fmax … MHz
Mô phỏng: PASS/FAIL — ghi chú
Trên kit: PASS/FAIL/CHƯA CÓ KIT — ghi chú
Số liệu chính: (bảng ngắn hoặc link CSV)
Vấn đề còn mở / cần CongVT quyết định: …
Nguồn đã dùng: …
```

---

## PHẦN H. ĐÁNH GIÁ KHẢ THI (để tác tử biết chỗ cần cẩn thận)

| Hạng mục | Khả thi | Rủi ro cần theo dõi |
|---|---|---|
| Công cụ trên macOS | Cao | Toolchain mở (Apicula) hỗ trợ Tang Nano 20K; Gowin EDA Education có bản macOS |
| Bài 1 | Rất cao | Chủ yếu là đúng chân UART/clock |
| Bài 2 | Cao | Thời gian mô phỏng: phải dùng Verilator |

---

## PHẦN I. LỊCH SỬ THAY ĐỔI ĐẶC TẢ

### 02/10/2026 — bỏ BÀI 3 (lệnh tuỳ biến và đơn vị vector mini)

CongVT quyết định đưa Bài 3 ra khỏi phạm vi. Đặc tả nay gồm **hai bài**: Bài 1 (SoC in
"Hello" qua UART) và Bài 2 (nhân ma trận, đo số chu kỳ).

Phần việc đã làm được giữ trong `docs/riscv-tn20k/bai3/`, đánh dấu **ngoài phạm vi**. Giữ
lại vì đó là số đo thật, xoá đi thì không dựng lại được, và vì nó trả lời được một câu mà
Bài 2 không trả lời: tăng tốc bằng phần cứng chuyên dụng đổi được bao nhiêu.

Chặng cuối của Bài 3 cũng để lại một kết quả đáng giữ. Nấc 3c **đúng về chức năng** — tổng
kiểm khớp đáp án độc lập, cpm 3,84 — nhưng **không vừa chip**, và nguyên nhân chỉ lộ ra khi
tổng hợp riêng `bram.v`: thêm cổng thứ hai làm **suy luận BSRAM đứt hoàn toàn**, cả 32 KB bị
dựng thành 262 144 flip-flop trên một chip chỉ có 15 552. Vượt 17 lần.

Điều ấy nói rằng điểm (3) trong phần kiến trúc của Bài 3 cũ — *"luồng công cụ: toolchain mở
hay Gowin EDA, theo kết quả kiểm tra BRAM hai cổng ở G1"* — là một câu hỏi đặt đúng mà chưa
ai trả lời trước khi viết RTL. Nếu sau này quay lại bài này, **phép kiểm BRAM hai cổng phải
là việc đầu tiên**, trước cả bản thiết kế kiến trúc.
