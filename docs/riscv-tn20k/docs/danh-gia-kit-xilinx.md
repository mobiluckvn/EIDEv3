# Đánh giá khả năng sử dụng kit Digilent Arty A7-100T và Basys 3 (Xilinx Artix-7) cho Đề án


> **Ghi chú 02/10/2026.** Bản đánh giá này viết khi đề án còn **ba** bài. Bài 3 đã ra khỏi
> phạm vi, nên nhu cầu tài nguyên thật **thấp hơn** mọi con số dưới đây — phạm vi hai bài đo
> được **2 211 LUT4** (10,7 % trên Tang Nano 20K), không phải ~3 980. Kết luận về hai kit
> Xilinx **không đổi**: vướng vẫn nằm ở hai chặng giữa của luồng công cụ trên macOS, không ở
> dung lượng chip. Bản phân tích giữ nguyên như lúc nộp.

Tài liệu này đánh giá tính khả thi kỹ thuật của hai kit phát triển FPGA dùng chip **Xilinx Artix-7**:
1. **Digilent Arty A7-100T** (chip `XC7A100T-1CSG324C`)
2. **Digilent Basys 3** (chip `XC7A35T-1CPG236C`)

Mục tiêu đối chiếu: phục vụ lộ trình 3 bài toán của đề án SoC PicoRV32 (Bài 1: SoC in "Hello", Bài 2: Nhân ma trận I8/I32 đo chu kỳ, Bài 3: Lệnh tuỳ biến & Mini-Vector), chạy trên máy phát triển **macOS Apple Silicon (ARM64)** của anh Công.

Thứ tự đánh giá tuân thủ quy tắc rút ra từ bài EP4CE6: **Vế công cụ xét trước (rẻ hơn, dứt khoát hơn), Vế chip xét sau**.

---

## Tóm tắt kết luận (Executive Summary)

1. **Vế chip & phần cứng bo mạch (RẤT TỐT — VƯỢT TRỘI):**
   - **Tài nguyên chip:** Cả XC7A35T (Basys 3) và XC7A100T (Arty A7) đều **thừa sức** đáp ứng cả 3 bài toán. SoC của ta (kể cả Bài 3) chỉ chiếm ~**19,2 % LUT** trên bản 35T và chỉ ~**6,3 % LUT** trên bản 100T. Dung lượng BRAM của chip nhỏ nhất (35T) là **225 KB** (gấp 7 lần nhu cầu 32 KB), cho phép mở rộng lên 64 KB hay 128 KB phẳng hoàn toàn tự nhiên.
   - **Cầu USB–UART:** **CẢ HAI BO ĐỀU CÓ SẴN CẦU USB–UART TÍCH HỢP** (dùng chip FTDI FT2232HQ kênh đôi: Kênh A làm JTAG nạp bitstream, Kênh B làm UART nối thẳng vào chân TX/RX của FPGA). Cắm một sợi cáp micro-USB vào máy Mac là vừa nạp được vừa thấy chuỗi in "Hello" ở 115200 baud, không cần mua thêm mạch nạp hay module USB-to-UART rời.

2. **Vế luồng công cụ (RÀO CẢN QUYẾT ĐỊNH TRÊN macOS APPLE SILICON):**
   - **Chặng 1 (Tổng hợp) & Chặng 4 (Nạp):** Đã có sẵn và chạy native mượt mà (`yosys` có `synth_xilinx`; `openFPGALoader` nhận diện và nạp trực tiếp cả hai bo `arty_a7_100t` và `basys3`).
   - **Chặng 2 (Đặt-đi-dây) & Chặng 3 (Đóng gói bitstream):**
     + **Phần mềm chính hãng Vivado:** **HOÀN TOÀN KHÔNG CÓ BẢN CHO macOS** (kể cả x86 lẫn ARM64; mục tải về của AMD/Xilinx chỉ phát hành gói cho Windows 64-bit và Linux x86_64). Chạy Vivado qua giả lập máy ảo Linux x86 trên Apple Silicon là một trải nghiệm cực kỳ nặng nề (bộ cài > 50 GB, chạy giả lập x86 qua QEMU rất chậm).
     + **Luồng mã nguồn mở (Project X-Ray / F4PGA / nextpnr-xilinx):** Có tồn tại về mặt dự án (dự án **Project X-Ray** giải mã bitstream, **F4PGA/VPR** hoặc **nextpnr-xilinx/himbaechel** làm PnR, **xc7frames2bit** đóng gói bitstream). Tuy nhiên, **chưa có gói nhị phân dựng sẵn (turn-key) cho macOS Apple Silicon**. Gói `oss-cad-suite` chính thức **không đóng gói** `nextpnr` cho Xilinx do cơ sở dữ liệu định tuyến (`prjxray-db`) quá đồ sộ. Để chạy trên macOS ARM64, bắt buộc phải tự tải mã nguồn, tự biên dịch các công cụ C++ và dựng database chip bằng tay với độ phức tạp bảo trì rất cao.

3. **Khuyến nghị lựa chọn:**
   - Nếu anh Công **bắt buộc luồng làm việc 100 % native, 1-click mượt mà trên macOS Apple Silicon** như hiện tại với Tang Nano 20K: **Cả hai kit này đều chưa thể dùng ngay lập tức** bằng công cụ có sẵn trong `oss-cad-suite`, trừ khi chấp nhận bỏ công dựng luồng toolchain mã nguồn mở từ source hoặc dựng một máy chủ build Linux từ xa (remote server).
   - Nếu chọn trong 2 kit (khi đã có giải pháp chạy Vivado hoặc dựng xong toolchain): **Nên chọn Digilent Arty A7-100T**. Arty A7-100T có 256 MB RAM DDR3L, cổng 100M Ethernet PHY, tài nguyên gấp 3 lần Basys 3, cực kỳ lý tưởng để phát triển SoC RISC-V chạy Linux hoặc mở rộng sau này; trong khi Basys 3 chủ yếu thiết kế cho bài tập logic nhập môn (nhiều switch, led 7 thanh nhưng không có RAM ngoài).

---

## Vế 1 — Phân tích luồng công cụ (Toolchain)

Đây là vế quyết định tính khả thi trong môi trường làm việc macOS Apple Silicon (ARM64).

### 1. Hiện trạng 4 chặng công cụ trên máy của ta

| Chặng | Công cụ | Trạng thái trên macOS Apple Silicon | Chi tiết kỹ thuật |
|---|---|---|---|
| **1 · Tổng hợp** | `yosys` | **SẴN SÀNG (Native ARM64)** | Đã tích hợp sẵn lệnh `synth_xilinx` (chuyển đổi Verilog thành LUT6, MUXF7/MUXF8, CARRY4, DSP48E1, RAMB36E1). |
| **2 · Đặt-đi-dây (PnR)** | `nextpnr` / `VPR` | **CHƯA CÓ TRONG BẢN CÀI** | `oss-cad-suite` không có nhị phân `nextpnr-xilinx` dựng sẵn. Cần xem xét luồng F4PGA hoặc tự dựng từ nguồn. |
| **3 · Bitstream** | `prjxray` / `fasm` | **CHƯA CÓ TRONG BẢN CÀI** | Cần công cụ chuyển đổi FASM sang `.bit` (`fasm2frames` và `xc7frames2bit`). |
| **4 · Nạp bo** | `openFPGALoader` | **SẴN SÀNG (Native ARM64)** | Đã hỗ trợ sẵn cờ bo: `-b arty_a7_100t` và `-b basys3` qua giao tiếp FTDI JTAG. |

---

### 2. Dự án mã nguồn mở cho Xilinx 7-Series: Có tồn tại thật không?

Câu trả lời là: **CÓ TỒN TẠI THẬT, nhưng tình trạng triển khai trên macOS ARM64 có rào cản lớn.**

#### A. Dự án nền tảng: Project X-Ray (prjxray)
- **Tổ chức duy trì:** F4PGA (trước đây là SymbiFlow thuộc Linux Foundation / Google hỗ trợ).
- **Mục tiêu:** Dịch ngược định dạng bitstream của dòng Xilinx 7-Series (Artix-7, Kintex-7, Zynq-7000).
- **Trạng thái:** Bản cơ sở dữ liệu `prjxray-db` đã hoàn chỉnh cho các chip phổ thông gồm `xc7a35t` và `xc7a100t`. Dự án vẫn được lưu trữ và cập nhật trên GitHub (`f4pga/prjxray`).

#### B. Công cụ Đặt-đi-dây (PnR): VPR và nextpnr-xilinx
1. **Luồng F4PGA chuẩn (dùng VPR):**
   - F4PGA sử dụng VPR (Versatile Place and Route) để PnR cho Xilinx 7-Series.
   - Định dạng đầu ra là tệp FASM (FPGA Assembly).
   - **Rào cản:** Bộ cài F4PGA chính thức qua Conda/Mamba **chỉ phát hành nhị phân cho Linux x86_64** (không có bản dựng cho macOS hay ARM64).
2. **Luồng nextpnr (`nextpnr-xilinx` / `himbaechel`):**
   - Cộng đồng YosysHQ đã phát triển kiến trúc `himbaechel` (kiến trúc dùng chung để hỗ trợ nhiều họ FPGA mới, trong đó có backend `uarch/xilinx` hoặc nhánh `nextpnr-xilinx` thử nghiệm của tác giả `gatecat`).
   - `nextpnr` có khả năng đọc cơ sở dữ liệu BBA (Binary Blob Architecture) sinh ra từ `prjxray-db`.
   - **Vì sao `oss-cad-suite` không đóng gói sẵn `nextpnr-xilinx`?**
     Vì cơ sở dữ liệu routing graph của Artix-7 cực kỳ khổng lồ. Tệp chipdb cho XC7A100T nén lại có thể nặng hàng GB bộ nhớ, thời gian dựng chipdb mất nhiều giờ và tiêu tốn hàng chục GB RAM. Do đó, đội ngũ YosysHQ chưa đưa Xilinx 7-Series vào danh sách nhị phân dựng sẵn hàng ngày của `oss-cad-suite`.

#### C. Công cụ đóng gói bitstream mã nguồn mở
- **Công cụ:** `xc7frames2bit` (nằm trong bộ mã nguồn `prjxray-tools` viết bằng C++) kết hợp với `fasm2frame` (viết bằng Python).
- **Nguyên lý hoạt động:** Nhận tệp `.fasm` từ PnR, tra bảng đối chiếu bit của `prjxray`, sinh ra các khung cấu hình (frames), sau đó chèn header chuẩn của Xilinx để xuất ra tệp nhị phân `.bit`. Tệp `.bit` này tương thích 100 % với chuẩn nạp của chip Xilinx.

#### D. Khả năng chạy trên macOS Apple Silicon (ARM64)
- **Bản dựng sẵn (pre-built binary):** **KHÔNG CÓ.** Cả F4PGA lẫn YosysHQ đều chưa cung cấp một gói đóng sẵn cho macOS ARM64 cho họ Xilinx 7.
- **Nếu tự biên dịch từ mã nguồn (Build from source):**
  + Có thể tự biên dịch `prjxray-tools` (C++14, CMake) và `nextpnr` với backend Xilinx trên macOS ARM64 bằng Clang/Apple Clang.
  + **Độ nặng và phức tạp:** Cần cài đặt Boost, Eigen3, Python3, tự clone repo `prjxray-db` (~1-2 GB dữ liệu git), chạy script sinh chipdb BBA cho `xc7a35t` hoặc `xc7a100t`. Quá trình sinh BBA tốn rất nhiều RAM (khuyến nghị máy có ≥ 16–32 GB RAM) và dễ gặp lỗi không tương thích giữa các phiên bản commit.

---

### 3. Phần mềm chính hãng AMD / Xilinx Vivado có bản macOS không?

- **Kết quả rà soát trang tải chính thức của Xilinx (Vivado ML Standard Edition):**
  + Các hệ điều hành được hỗ trợ chính thức:
    * **Windows:** Windows 10/11 64-bit.
    * **Linux:** Red Hat Enterprise Workstation / CentOS 7/8/9, Ubuntu 18.04/20.04/22.04 LTS, SUSE Linux Enterprise 15 (tất cả đều là kiến trúc **x86_64**).
  + **Mục macOS:** **HOÀN TOÀN KHÔNG CÓ.** Không có bản cài native cho macOS (cả thời kỳ Intel x86 trước đây lẫn Apple Silicon hiện nay).
- **Thử nghiệm chạy qua máy ảo trên Apple Silicon:**
  + Vì Vivado là mã x86_64 độc quyền, nếu chạy trên macOS Apple Silicon, máy ảo (như UTM, Parallels) bắt buộc phải dùng lớp giả lập kiến trúc CPU (QEMU TCG x86_64 emulation).
  + Bộ cài đặt Vivado ML nặng từ **50 GB đến trên 100 GB**. Quá trình giả lập CPU x86_64 để chạy bộ cài và chạy thuật toán PnR của Vivado sẽ **chậm hơn hàng chục lần**, thường xuyên gặp lỗi tràn bộ nhớ hoặc treo tiến trình.

---

## Vế 2 — Phân tích năng lực chip Artix-7 (XC7A35T & XC7A100T)

Phần cứng là điểm sáng tuyệt đối của cả hai kit: không có bất kỳ điểm nghẽn nào về mặt tài nguyên logic, thanh ghi, BRAM hay DSP.

### 1. Bảng đối chiếu thông số phần cứng

Dữ liệu trích xuất từ tài liệu chính hãng Xilinx (*7 Series FPGAs Overview — DS180* và *Artix-7 FPGAs Data Sheet — DS181*):

| Hạng mục phần cứng | Nhu cầu SoC của ta (Bài 1 + Bài 3) | Digilent Basys 3 (XC7A35T-1CPG236C) | Tỷ lệ dùng (Basys 3) | Digilent Arty A7-100T (XC7A100T-1CSG324C) | Tỷ lệ dùng (Arty A7-100T) |
|---|---|---|---|---|---|
| **Logic Cells** | — | 33.280 | — | 101.440 | — |
| **LUT (6 ngõ vào - LUT6)** | ~**4.000** (Bài 1: 2.180, B3: +1.800) | **20.800 LUT6** | **19,2 %** | **63.400 LUT6** | **6,3 %** |
| **Flip-Flop (FF)** | ~**2.320** (Bài 1: 820, B3: +1.500) | **41.600 FF** | **5,5 %** | **126.800 FF** | **1,8 %** |
| **Block RAM (BRAM)** | **32 KB** (hoặc 64 KB mở rộng) | **1.800 Kb** (50 khối 36 Kb = 225 KB) | **14,2 %** (dùng 32 KB) | **4.860 Kb** (135 khối 36 Kb = 607,5 KB) | **5,3 %** (dùng 32 KB) |
| **Khối DSP (DSP48E1)** | **8 – 16 bộ nhân** (Bài 2: 1, B3: 8–16) | **90 lát DSP48E1** (nhân 25×18) | **8,9 % – 17,8 %** | **240 lát DSP48E1** (nhân 25×18) | **3,3 % – 6,7 %** |
| **Bộ quản lý xung (CMT)** | Cần 1 PLL / MMCM | 5 khối CMT (mỗi khối gồm 1 MMCM + 1 PLL) | 20 % | 6 khối CMT (mỗi khối gồm 1 MMCM + 1 PLL) | 16,7 % |

### 2. Nhận xét về độ thoải mái tài nguyên
- **Logic & Flip-Flop:** Cả hai chip đều có LUT6 (kiến trúc 6 ngõ vào có thể tách đôi thành 2 LUT5 dùng chung ngõ vào), hiệu suất nén logic cao hơn nhiều so với LUT4 của Gowin hay Cyclone IV. SoC của ta chỉ chiếm dưới 20 % trên XC7A35T và dưới 7 % trên XC7A100T.
- **Bộ nhớ BRAM:**
  + Trên Cyclone IV EP4CE6, BRAM bị thiếu và nghẽn cấu hình nghiêm trọng (chỉ có 30 khối M9K).
  + Ngược lại, trên XC7A35T, chip có tới **50 khối RAMB36E1** (tổng 225 KB). Mỗi khối 36 Kb có thể hoạt động độc lập như hai khối 18 Kb với độ rộng bus dữ liệu lên tới 36-bit (32-bit data + 4 parity), hỗ trợ ghi từng byte (`byte-write enable`) trực tiếp từ phần cứng. Để tạo 32 KB BRAM 32-bit, ta chỉ cần **8 khối RAMB36E1** (chiếm 16 % số khối BRAM của chip 35T và 5,9 % của chip 100T).
- **Bộ nhân DSP48E1:**
  + Mỗi khối DSP48E1 chứa một bộ nhân 25×18 bit kèm bộ cộng/tích luỹ 48-bit và thanh ghi đường ống (pipelined).
  + Nhu cầu 16 bộ nhân song song của Bài 3 nấc 3c chỉ chiếm 16 / 90 (17,8 %) trên Basys 3 và 16 / 240 (6,7 %) trên Arty A7.

---

## Vế 3 — Trang bị ngoại vi trên bo mạch & Cầu USB–UART

Đề bài đặt câu hỏi then chốt: **Hai bo có sẵn cầu USB–nối tiếp để in chuỗi 'Hello' ra máy tính không, hay chỉ có JTAG?**

### 1. Cơ chế giao tiếp USB trên hai kit của Digilent

Theo sơ đồ nguyên lý và tài liệu *Reference Manual* của Digilent:
- Cả **Digilent Arty A7** và **Digilent Basys 3** đều sử dụng chip chuyển đổi giao tiếp **FTDI FT2232HQ** (Dual High-Speed USB to Multipurpose UART/FIFO IC).
- Chip FT2232HQ cung cấp **2 kênh độc lập** qua duy nhất một cổng cắm cáp micro-USB:
  1. **Kênh A (Channel A — chế độ JTAG / MPSSE):** Nối thẳng vào 4 chân JTAG (`TCK`, `TMS`, `TDI`, `TDO`) của FPGA Artix-7. Kênh này dùng cho mạch nạp bitstream qua `openFPGALoader` hoặc Xilinx Hardware Server.
  2. **Kênh B (Channel B — chế độ Virtual COM Port / UART):** Nối thẳng vào 2 chân I/O chuyên dụng của FPGA (chân `TXD` và `RXD`).
- **Kết quả thực tế khi cắm vào máy Mac:**
  + Hệ điều hành macOS tự nhận diện driver FTDI có sẵn trong nhân macOS (AppleUSBFTDI).
  + Máy sẽ xuất hiện thiết bị nối tiếp dạng `/dev/cu.usbserial-XXXX1` (cổng UART) và giao diện JTAG.
  + Chương trình SoC Bài 1 khi gửi ký tự ra UART TX ở baudrate 115200 sẽ **hiển thị trực tiếp trên máy tính** thông qua bất kỳ trình terminal nào (`screen`, `minicom`, `tio`, hoặc script Python), **hoàn toàn không cần mạch chuyển đổi USB-to-TTL ngoài**.

### 2. So sánh ngoại vi giữa Arty A7-100T và Basys 3

| Tiêu chí | Digilent Basys 3 | Digilent Arty A7-100T | Nhận xét ứng dụng |
|---|---|---|---|
| **Chip FPGA** | Artix-7 XC7A35T | Artix-7 XC7A100T | Arty mạnh gấp ~3 lần về logic và BRAM. |
| **Bộ nhớ ngoài** | **Không có RAM ngoài** | **256 MB DDR3L (16-bit bus)** | Arty chạy được hệ điều hành Linux RISC-V hoàn chỉnh; Basys 3 chỉ chạy code trong BRAM nội. |
| **Giao tiếp mạng** | Không có | **10/100 Mbps Ethernet PHY** | Arty làm được các ứng dụng mạng, IoT, Web server. |
| **Cổng Pmod / Mở rộng** | 4 cổng Pmod tiêu chuẩn | 4 cổng Pmod + Header Arduino Uno R3 | Arty gắn được trực tiếp các shield Arduino. |
| **Ngoại vi nhập môn** | 16 Switch gạt, 16 LED đơn, 5 nút bấm, 4 LED 7 thanh, cổng VGA 12-bit | 4 Switch gạt, 4 LED đơn, 4 LED RGB, 4 nút bấm | Basys 3 tối ưu cho môn học Thiết kế Logic / Đồ án cơ sở ở trường đại học. |
| **Cổng USB Host** | Có (USB HID cho chuột/phím qua PIC24) | Không có sẵn USB Host | Basys 3 cắm được bàn phím/chuột cơ bản. |
| **Mức giá thị trường** | ~$165 – $190 | ~$280 – $320 | Arty đắt hơn nhưng giá trị sử dụng lâu dài cao hơn nhiều. |

---

## Đối chiếu tổng hợp: Tang Nano 20K vs Altera EP4CE6 vs Xilinx Artix-7

| Hạng mục | Sipeed Tang Nano 20K (Hiện tại) | Waveshare EP4CE6 (Đã loại) | Xilinx Artix-7 (Basys 3 / Arty A7) |
|---|---|---|---|
| **Hãng chip** | Gowin Semiconductor | Altera (Intel PSG) | Xilinx (AMD) |
| **Chạy native trên macOS ARM64** | **100 % mượt mà (Turn-key)** | **KHÔNG** (Quartus & nextpnr đều gãy) | **CHƯA TURN-KEY** (Vivado không có macOS, F4PGA/nextpnr phải tự build từ source) |
| **Mạch nạp bitstream** | `openFPGALoader` (BL616) | USB-Blaster (chập chờn) | `openFPGALoader` (FT2232HQ rất chuẩn xác) |
| **Cầu USB-UART trên bo** | Có sẵn | Không có sẵn | **Có sẵn (FTDI Channel B)** |
| **Năng lực BRAM cho SoC** | 103,5 KB (đủ Bài 1, 2, 3) | 33,75 KB (chạm trần, gãy ở 32 KB) | **225 KB – 607,5 KB (dư dả tuyệt đối)** |
| **Khối nhân cứng DSP** | 1 bộ MULT36X36 (ghép được) | 15 khối 18×18 (thiếu ở nấc 3c) | **90 – 240 khối DSP48E1 (rất mạnh)** |

---

## Kết luận & Khuyến nghị

1. **Kit nào dùng được?**
   - **Về mặt nguyên lý phần cứng:** Cả **Basys 3** và **Arty A7-100T** đều dùng được rất tốt cho đề án. Chúng vượt trội hơn hẳn Tang Nano 20K và loại bỏ hoàn toàn các điểm nghẽn bộ nhớ của Cyclone IV EP4CE6.
   - **Về mặt công cụ trên macOS Apple Silicon:** Cả hai kit **chưa thể dùng theo dạng "cắm là chạy" (out-of-the-box)** với bộ công cụ `oss-cad-suite` hiện có trên máy, do thiếu nhị phân PnR (`nextpnr-xilinx`) và phần mềm chính hãng Vivado không hỗ trợ macOS.
   - **Điều kiện để dùng được kit Xilinx:**
     + **Cách 1 (Khuyên dùng nếu có máy phụ):** Dùng một máy tính x86_64 chạy Ubuntu/Debian hoặc Windows cài Vivado WebPACK chính hãng (hoặc máy ảo x86 trên server nội bộ) để tổng hợp và xuất file `.bit`, sau đó chuyển file `.bit` sang Mac dùng `openFPGALoader` nạp thẳng vào bo.
     + **Cách 2 (Luồng mã nguồn mở tự dựng):** Dành thời gian tự biên dịch `prjxray`, `fasm`, và `nextpnr` với cờ kiến trúc Xilinx native trên macOS ARM64.

2. **Nếu cả hai dùng được thì nên chọn kit nào?**
   - **LỰA CHỌN TỐI ƯU: Digilent Arty A7-100T.**
   - **Lý do:**
     1. **Đầu tư dài hạn:** Arty A7-100T sở hữu chip **XC7A100T** (gấp 3 lần logic và BRAM so với Basys 3). Với 256 MB DDR3L RAM và 100M Ethernet, bo mạch này đủ sức chạy các vi xử lý RISC-V 64-bit (RocketChip, CVA6) cài Linux nhúng (Buildroot/Yocto), trong khi Basys 3 hoàn toàn không có RAM ngoài.
     2. **Định hướng kiến trúc:** Basys 3 có giá chỉ rẻ hơn một chút nhưng trang bị quá nhiều linh kiện phục vụ bài tập thí nghiệm sinh viên (16 switch, led 7 thanh, VGA điện trở) – những thứ không cần thiết cho đề án SoC vi xử lý của anh Công.
