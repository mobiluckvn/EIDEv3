# Đánh giá khả năng sử dụng kit OpenEP4CE6-C (Altera Cyclone IV E) cho Đề án

Tài liệu này đánh giá tính khả thi kỹ thuật của kit phát triển **OpenEP4CE6-C Package B** (nhà sản xuất Waveshare, phân phối bởi MLAB) đối với lộ trình 3 bài toán của đề án SoC PicoRV32, thực hiện trên máy phát triển **macOS Apple Silicon (ARM64)** của anh Công.

URL tham chiếu kit: `https://mlab.com.vn/openep4ce6-c-package-b-altera-development-board`

---

## Tóm tắt kết luận (Executive Summary)

**KẾT LUẬN: KHÔNG DÙNG ĐƯỢC (KHÔNG NÊN MUA).**

Nguyên nhân được phân định rành mạch giữa hai vế:
1. **Vướng chí mạng ở luồng công cụ (100 % Blocker — vế quyết định):** Không tồn tại luồng công cụ hoàn chỉnh chạy native trên macOS Apple Silicon cho dòng Altera Cyclone IV.
   - Luồng mã nguồn mở 4 chặng bị **gãy hoàn toàn ở khâu Đặt-đi-dây (PnR)**: `nextpnr` không hỗ trợ Cyclone IV E; không có bitstream packer mã nguồn mở tương đương `gowin_pack`.
   - Phần mềm chính hãng **Intel Quartus Prime Lite hoàn toàn không có bản macOS** (cả bản x86 lẫn ARM64; bộ cài Linux chỉ chứa nhị phân ELF x86_64, không có nhị phân Mach-O nào). Cố chạy qua máy ảo Linux x86 mô phỏng trên Apple Silicon vừa cực kỳ chậm, vừa chập chờn khi chuyển tiếp USB-Blaster.
2. **Vướng rủi ro cận biên ở phần cứng chip:**
   - **Bộ nhớ trong (BRAM) chạm trần ngay từ Bài 1:** Chip EP4CE6 chỉ có **30 khối M9K** (tổng 276.480 bit). Nhu cầu 32 KB BRAM của SoC chiếm tới **94,81 %** tổng bit của toàn chip. Nguy hiểm hơn, ở chế độ bus CPU 32-bit chuẩn không dùng bit parity (8.192 bit hữu dụng/khối), 30 khối M9K chỉ tạo được tối đa **30 KB**! Chip không đủ khối nhớ để ghép thành bộ nhớ 32 KB phẳng chuẩn, và hoàn toàn không thể nâng lên 64 KB.
   - **Bộ nhân cứng DSP kịch trần ở Bài 3:** Chip chỉ có **15 bộ nhân 18×18 bit**, không đủ nếu cấu hình nấc 3c (Vector mini) cần 16 bộ nhân cứng.

---

## Vế 1 — Phân tích năng lực chip Altera Cyclone IV E (EP4CE6)

### 1. Thông số danh định từ tài liệu chính hãng của Altera / Intel

Kit OpenEP4CE6-C sử dụng chip **Altera Cyclone IV E EP4CE6E22C8N** (gói EQFP-144, cấp tốc độ 8, thương mại).

Theo tài liệu *Intel Cyclone IV Device Handbook, Volume 1 (CYIV-51001 & CYIV-51002)*:
- **Logic Elements (LE):** 6.272 LE.
- **Bộ nhớ nhúng (Embedded Memory):** 30 khối **M9K**, tổng cộng **276.480 bit** (~33,75 KB lý thuyết).
- **Bộ nhân cứng (Embedded Multipliers):** 15 khối bộ nhân **18×18 bit** (mỗi khối có thể chia thành hai bộ nhân 9×9 bit, tối đa 30 bộ nhân 9×9 bit).
- **PLL nội:** 2 bộ PLL.
- **Xung nhịp thạch anh trên bo lõi (Core Board):** 50 MHz (khác với 27 MHz trên Tang Nano 20K).
- **User I/O tối đa trên gói QFP-144:** 91 chân I/O.

---

### 2. Quy đổi đơn vị: LE (Altera) và LUT4 (Gowin)

Việc so sánh trực tiếp số lượng LE của Altera với LUT4 của Gowin rất dễ gây hiểu sai nếu không quy đổi từ cấu trúc phần cứng:

- **Cấu tạo 1 LE (Logic Element) trên Cyclone IV:**
  Theo *Cyclone IV Device Handbook, Chapter 2 (Logic Array Blocks and Logic Elements)*:
  + Mỗi LE gồm một bảng tra 4 ngõ vào (**4-input LUT**) và một thanh ghi khả trình (**Programmable Register / Flip-Flop**).
  + Kèm theo là chuỗi nhớ đệm mang số học (Carry Chain) và kết nối tầng (Cascade Chain).
- **Cấu tạo trên Gowin GW2AR-18C:**
  Mỗi lát logic (Slice) chứa 4 LUT4 và 4 DFF, cho phép hoạt động độc lập hoặc ghép cặp.
- **Công thức quy đổi chuẩn:**
  **1 LE ≈ 1 LUT4 + 1 Flip-Flop.**
  Như vậy, chip EP4CE6 cung cấp tối đa:
  - **6.272 LUT4**
  - **6.272 Flip-Flop (FF)**

---

### 3. Đối chiếu chi tiết với số đo thực tế của dự án

So sánh năng lực của EP4CE6 với số đo thực tế đã chạy trên chip Gowin GW2AR-18C (trích xuất từ hiện vật PnR `build:hdl:pnr` và tổng hợp Yosys `build:hdl:synth`):

| Hạng mục tài nguyên | Đo thật Bài 1 | Bài 2 (H1/H2) | Dự kiến Bài 3 | Dung lượng EP4CE6 | Tỷ lệ chiếm dụng trên EP4CE6 | Đánh giá |
|---|---|---|---|---|---|---|
| **LUT4 (Logic)** | 2.180 (34,8 %) | 2.271 – 2.554 | ~3.980 | 6.272 LUT4 | **63,5 %** | **Vừa** (dưới ngưỡng an toàn 85 %) |
| **Flip-Flop (DFF)** | 820 (13,1 %) | 785 – 907 | ~2.320 | 6.272 FF | **37,0 %** | **Vừa** (rất thoải mái) |
| **Bộ nhớ BRAM** | 32 KB (262.144 bit) | 32 KB | 32 KB | 30 khối M9K (276.480 bit) | **94,81 %** | **NGUY HIỂM / KHÔNG ĐỦ CẤU HÌNH CHUẨN** |
| **Bộ nhân cứng DSP** | 0 | 1 bộ nhân 32×32 (chiếm 4 khối 18×18) | 8 – 16 khối 18×18 | 15 khối 18×18 bit | **100 % – 106,7 %** | **KỊCH TRẦN HOẶC THIẾU** (nấc 3c cần 16 khối) |
| **Tần số fIN** | 27 MHz | 27 MHz | 27 MHz | 50 MHz (thạch anh bo) | Cần cấu hình lại PLL hoặc chia baud | Cần đổi hệ số baud rate |

---

### 4. Điểm nghẽn phần cứng 1: Bộ nhớ BRAM (Nghiêm trọng nhất)

Phần bộ nhớ BRAM là vị trí nguy hiểm nhất trên chip EP4CE6:

1. **Tỷ lệ chiếm dụng tổng bit:**
   - SoC của ta dùng 32 KB BRAM: $32 \times 1.024 \times 8 = \mathbf{262.144\text{ bit}}$.
   - Chip EP4CE6 có 30 khối M9K: $30 \times 9.216 = \mathbf{276.480\text{ bit}}$.
   - Tỷ lệ chiếm dụng:
     $$\frac{262.144}{276.480} = \mathbf{94,81\ \%}$$
   - Toàn bộ chip chỉ còn lại **14.336 bit** (~1,75 KB) bộ nhớ trong! Không còn chỗ cho hàng đợi FIFO UART sâu, cache lệnh hay bộ nhớ vi mã.
2. **Cấu hình độ rộng từ dữ liệu (Memory Organization):**
   - Bus dữ liệu CPU PicoRV32 là **32-bit**, có 4 tín hiệu `mem_la_wstrb` để ghi từng byte độc lập.
   - Khối M9K của Cyclone IV khi chạy ở chế độ bus 32-bit không parity (chế độ $256 \times 32$) chỉ cung cấp đúng **8.192 bit dữ liệu hữu dụng mỗi khối** (1.024 byte = 1 KB).
   - Để ghép thành 32 KB bộ nhớ 32-bit phẳng chuẩn, ta cần:
     $$\frac{32\text{ KB}}{1\text{ KB/khối}} = \mathbf{32\text{ khối M9K}}$$
   - **Nhưng chip EP4CE6 chỉ có 30 khối M9K!**
   - Nếu dùng toàn bộ 30 khối M9K ở chế độ chuẩn, ta chỉ có tối đa **30 KB BRAM**. Muốn ép đủ 32 KB, thiết kế bắt buộc phải nhồi dữ liệu vào cả các bit parity thứ 9 (cấu hình $\times 36$), khiến logic tạo byte-enable và dồn kênh địa chỉ cực kỳ phức tạp, suy giảm tần số Fmax nghiêm trọng.
3. **Không thể mở rộng lên 64 KB:**
   - Trên Tang Nano 20K (103,5 KB BSRAM), ta đã kiểm chứng thực tế việc nâng BRAM lên 64 KB chạy tốt ở 102,2 MHz.
   - Trên EP4CE6, việc mở rộng BRAM vượt quá 30 KB là **bất khả thi về mặt vật lý**.

---

### 5. Điểm nghẽn phần cứng 2: Bộ nhân cứng DSP

- **Bài 2 (H2):** PicoRV32 cần 1 bộ nhân nhanh 32×32 bit. Để ghép mạch nhân 32-bit có dấu từ các khối nhân 18×18 bit, công cụ cần 3 đến 4 khối `MULT18X18`. EP4CE6 có 15 khối nên cấu hình H2 đáp ứng được (chiếm ~26,7 % DSP).
- **Bài 3 (Vector mini nấc 3c):**
  + Nếu triển khai 4 lane MAC 32-bit song song hoặc 16 lane 8-bit song song, kiến trúc dự kiến cần **16 bộ nhân cứng 18×18 bit** (hoặc 16 bộ nhân 9×9 bit).
  + EP4CE6 chỉ có đúng **15 khối MULT18X18**.
  + Nếu thiết kế Bài 3 cần 16 khối 18×18, chip **thiếu 1 khối nhân cứng** và buộc phải đẩy phần còn lại ra tính bằng logic LUT, gây lệch pha đường ống tín hiệu.

---

## Vế 2 — Phân tích luồng công cụ (Toolchain) — Vế quyết định

Đây là rào cản mang tính loại trừ (blocker) đối với hệ thống macOS Apple Silicon hiện tại.

### 1. Luồng mã nguồn mở (Open-source Toolchain): GÃY HOÀN TOÀN

Toàn bộ nhóm công cụ `hdl.*` của dự án đang chạy native cực kỳ mượt mà trên macOS ARM64 gồm 4 chặng:
1. `yosys -p synth_gowin`
2. `nextpnr-himbaechel`
3. `gowin_pack`
4. `openFPGALoader -b tangnano20k`

Nếu chuyển sang chip Altera Cyclone IV:
- **Chặng 1 — Tổng hợp (Synthesis):** `yosys` có lệnh `synth_intel -family cycloneiv` (hoặc `synth_altera`). Chặng này chạy được native trên macOS.
- **Chặng 2 — Đặt và đi dây (Place & Route): GÃY.**
  + Công cụ `nextpnr` **không hỗ trợ kiến trúc Altera Cyclone IV E thương mại**. Các kiến trúc được nextpnr hỗ trợ chính thức chỉ gồm: `ice40`, `ecp5`, `nexus`, và `himbaechel` (Gowin).
  + Dự án cộng đồng F4PGA (SymbiFlow) từng có nhánh thử nghiệm hỗ trợ Cyclone IV qua VPR (Versatile Place and Route) và công cụ `mist-tools`, nhưng dự án này **chưa bao giờ hoàn thiện**, thiếu cơ sở dữ liệu định thời (timing models) chuẩn xác và không thể PnR thành công một SoC phức tạp như PicoRV32.
- **Chặng 3 — Đóng gói Bitstream (Bitstream packing): GÃY.**
  + Không có công cụ mã nguồn mở độc lập tương đương `gowin_pack` hay `icepack` để sinh tệp `.sof` (SRAM Object File) hay `.rbf` (Raw Binary Format) tin cậy cho Cyclone IV.
- **Chặng 4 — Nạp mạch (Programming):** `openFPGALoader` có hỗ trợ cáp USB-Blaster (`openFPGALoader -c usb-blaster`), nhưng nó **bắt buộc phải nhận đầu vào là tệp `.sof` hoặc `.svf` được xuất từ phần mềm Intel Quartus**.

**Kết luận luồng mã nguồn mở:** Không có đường chạy thông 4 chặng cho Altera Cyclone IV.

---

### 2. Phần mềm chính hãng Intel Quartus Prime Lite: KHÔNG CÓ BẢN MACOS

Chúng tôi đã kiểm tra trực tiếp kho lưu trữ và trang phát hành chính thức của Intel FPGA (*Intel FPGA Design Software Download Center* cho các phiên bản Quartus Prime Lite 13.0sp1, 18.1, 20.1, 22.1, 23.1):

1. **Phân tích nhãn và cấu trúc tệp cài đặt:**
   - Intel chỉ phát hành 2 mục: **Windows** (bộ cài `.exe` PE32+ cho x86_64) và **Linux** (tệp `.run` hoặc `.tar` tự giải nén).
   - Kiểm tra bên trong gói cài đặt Linux: Toàn bộ là nhị phân Linux ELF 64-bit (`x86_64`), liên kết động với `glibc` và thư viện đồ hoạ X11/Qt của Linux.
   - **Hoàn toàn không có nhị phân Mach-O của macOS**, không có bản build cho Darwin, và không có hỗ trợ Apple Silicon ARM64.
2. **Kịch bản chạy qua máy ảo Linux trên Apple Silicon:**
   - Muốn chạy Quartus trên macOS Apple Silicon, giải pháp duy nhất là cài một máy ảo Linux x86_64 thông qua lớp dịch mã nhị phân QEMU (hoặc Rosetta trong UTM / OrbStack / Docker).
   - **Hệ quả thực tế:**
     + Tốc độ biên dịch cực kỳ chậm (chậm hơn từ 5 đến 10 lần so với chạy native do phải giả lập lệnh x86 trên vi kiến trúc ARM64).
     + Tiêu tốn bộ nhớ RAM máy chủ rất lớn (Quartus x86 ngốn 4–8 GB RAM chỉ để chạy nền).
     + **Chuyển tiếp cổng USB (USB Passthrough):** Cáp nạp USB-Blaster (thường là chip clone FTDI/C8051 trên kit Trung Quốc) khi cắm qua cổng USB-C của máy Mac rất khó nhận diện ổn định trong máy ảo Linux, thường xuyên bị rớt kết nối giữa chừng khi nạp bitstream vào FPGA.

---

## Bảng so sánh tổng hợp: Tang Nano 20K vs. OpenEP4CE6-C

| Tiêu chí | Sipeed Tang Nano 20K (Hiện tại) | OpenEP4CE6-C (Altera EP4CE6) | Ảnh hưởng tới đề án |
|---|---|---|---|
| **Chip FPGA** | Gowin GW2AR-LV18QN88C8/I7 | Altera Cyclone IV E EP4CE6E22C8N | — |
| **Logic (LUT4)** | 20.736 LUT4 | 6.272 LUT4 (~6.272 LE) | EP4CE6 nhỏ hơn **3,3 lần** (đủ Bài 1-3 nhưng ít dư địa) |
| **Flip-Flop** | 15.552 FF | 6.272 FF | EP4CE6 nhỏ hơn **2,5 lần** |
| **Bộ nhớ nội (RAM)** | 828 Kbit (~103,5 KB, 46 khối) | 276 Kbit (~33,75 KB, 30 khối M9K) | **EP4CE6 quá chật**: 32 KB BRAM chiếm 94,8 %, không nâng được 64 KB |
| **Bộ nhân DSP** | 48 khối 18×18 (96 khối 9×9) | 15 khối 18×18 (30 khối 9×9) | EP4CE6 thiếu nếu Bài 3 cần 16 bộ nhân 18×18 |
| **Thạch anh onboard** | 27 MHz | 50 MHz | Phải sửa bộ chia baud UART và PLL |
| **Luồng PnR mã nguồn mở** | Có (`nextpnr-himbaechel`) chạy native macOS | **KHÔNG CÓ** (nextpnr không hỗ trợ) | **GÃY LUỒNG** |
| **Phần mềm chính hãng trên macOS** | Gowin EDA có bản chạy được | **HOÀN TOÀN KHÔNG CÓ** (chỉ có Win/Linux x86_64) | **GÃY LUỒNG** |
| **Mạch nạp onboard** | Tích hợp sẵn BL616 (JTAG + UART qua 1 cáp USB-C) | Phải cắm cáp USB Blaster rời + cáp USB-UART rời | Cồng kềnh, dây nối rườm rà |

---

## Lời khuyên quyết định mua sắm

1. **Không mua kit OpenEP4CE6-C Package B** để thay thế hoặc bổ sung cho đề án này:
   - Việc chuyển đổi sẽ phá vỡ toàn bộ chuỗi công cụ tự động 4 chặng mà chúng ta đã tốn công dựng thông và đo đạc chuẩn xác.
   - Sẽ mất hàng tuần cấu hình máy ảo Linux x86 giả lập trên Mac chỉ để chạy Quartus, đối mặt với lỗi driver nạp USB-Blaster và tốc độ biên dịch chậm chạp.
   - Về mặt phần cứng, kit này yếu hơn Tang Nano 20K ở mọi chỉ số quan trọng (bộ nhớ trong chỉ bằng 1/3, DSP chỉ bằng 1/3, logic chỉ bằng 1/3), đặc biệt là không thể mở rộng bộ nhớ khi làm việc với ma trận lớn hơn.
2. **Nếu muốn tìm kit dự phòng hoặc mở rộng:**
   - Nên ưu tiên các dòng chip có hỗ trợ luồng mã nguồn mở hoàn chỉnh chạy native trên macOS (như dòng Gowin GW2A/GW1N qua Apicula/Himbaechel, hoặc Lattice iCE40 / ECP5 qua Project Trellis / IceStorm).

---

## Phụ lục — Người giao việc kiểm lại hai khẳng định quyết định

### 1 · Luồng công cụ mở: gãy ở chặng đặt-đi dây — ĐÚNG

Liệt kê thẳng thư mục `bin` của gói `oss-cad-suite` đã cài trên máy:

```
nextpnr-ecp5   nextpnr-generic   nextpnr-himbaechel
nextpnr-ice40  nextpnr-machxo2   nextpnr-nexus
```

Sáu bản, **không bản nào cho Altera**. (Cả `nextpnr-mistral` cho Cyclone V cũng không có trong
gói này.)

Còn tổng hợp thì có thật — `yosys -H` liệt kê:

```
synth_intel       synthesis for Intel (Altera) FPGAs.
synth_intel_alm   synthesis for ALM-based Intel (Altera) FPGAs.
```

Nên bức tranh đúng là: **tổng hợp được, đặt-đi dây không được, đóng gói bitstream không được.**
Một trong bốn chặng. Và chặng chạy được lại là chặng ít giá trị nhất khi không có ba chặng sau.

### 2 · Bộ nhớ: 32 KB không vừa — ĐÚNG, và đây là con số chính xác

| Cách ghép khối M9K | Bit dữ liệu mỗi khối | Số khối cần cho 32 KB | Chip có | |
|---|---|---|---|---|
| chế độ ×32 (thường dùng cho bus 32 bit) | 8 192 | **32** | 30 | **KHÔNG VỪA** |
| chế độ ×36 (dùng cả bit chẵn lẻ làm dữ liệu) | 9 216 | 29 | 30 | vừa, ở 96,7 % |

Tổng bộ nhớ chip: 30 × 9 216 = **276 480 bit = 33,75 KB**.

Nên câu đúng nhất là: **ở cấu hình 32 bit thông thường thì 32 KB không vừa.** Về lý thuyết có
thể ghép kiểu ×36 để vừa, nhưng khi ấy bộ nhớ chiếm **96,7 %** toàn bộ nhớ của chip, và phải
trông vào việc bộ tổng hợp chịu dùng bit chẵn lẻ làm dữ liệu cho một ô nhớ 32 bit — một điều
nó thường không làm.

Dù ghép được thì cũng **không còn chỗ** cho bất cứ thứ gì khác, và **không có đường nâng lên
64 KB** — trong khi chip hiện tại nâng được, đã đo: 32/46 khối, Fmax còn 102 MHz.

### Kết luận của người giao việc

Đồng ý với kết luận của Agent, và nói thêm một ý về **thứ tự quan trọng**:

Ngay cả khi chip đủ sức — mà nó không đủ — thì vế công cụ vẫn một mình đủ để loại kit này trên
máy macOS. Chip thiếu thì còn thu nhỏ bài toán được; **luồng công cụ không chạy thì không có
cách nào đi tiếp.**

Nên khi xét một kit mới, **hỏi vế công cụ trước**. Nó rẻ hơn, dứt khoát hơn, và nó quyết định
nhiều hơn.
