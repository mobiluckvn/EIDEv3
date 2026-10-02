# Đánh giá năng lực phần cứng Sipeed Tang Nano 20K cho Đề án


> **Ghi chú 02/10/2026.** Bài 3 đã được đưa ra khỏi phạm vi đề án. Những phần dưới đây nói về
> Bài 3 **chỉ còn giá trị tham khảo**, không còn là yêu cầu. Bản phân tích giữ nguyên như lúc
> nộp — xem [`bai3/NGOAI-PHAM-VI.md`](../bai3/NGOAI-PHAM-VI.md) để biết đã đo được gì và vì sao
> dừng.
>
> Số thật của phạm vi hai bài, đo ngày 02/10/2026: **LUT4 2 211/20 736 = 10,7 %**,
> BSRAM 16/46, Fmax 106,01 MHz trên yêu cầu 27 MHz.

Tài liệu này phân tích và đánh giá năng lực phần cứng của kit **Sipeed Tang Nano 20K** (chip **Gowin GW2AR-LV18QN88C8/I7**) nhằm trả lời câu hỏi: *Kit này có đủ sức chạy hết chương trình của đề án (Bài 1, Bài 2, Bài 3) hay không?*

Mọi con số trong tài liệu đều có sở cứ xác thực từ ba nguồn:
1. **Số đo thực tế trên silicon**: trích xuất từ hiện vật PnR (`build:hdl:pnr`) và tổng hợp Yosys (`build:hdl:synth`) trong kho dự án.
2. **Thông số chip nhà sản xuất**: trích từ `docs/hardware-facts.md` và Gowin GW2A Series Data Sheet (DS226).
3. **Số tính toán**: kèm công thức toán học tường minh để người đọc tự kiểm chứng.

---

## Phần 1 — Hiện trạng sử dụng tài nguyên (Bài 1)

Bài 1 đã hoàn thành thiết kế SoC tối thiểu gồm: CPU PicoRV32 (RV32I, không FPU/bộ nhân cứng), bộ nhớ BRAM 32 KB, khối UART TX và bộ điều khiển 6 LED.

Kết quả đo đạc thực tế sau khâu đặt và đi dây (Place & Route) trên silicon chip GW2AR-LV18QN88C8/I7:

| Tài nguyên | Đang dùng (PnR thật) | Dung lượng chip | Tỷ lệ sử dụng | Sở cứ trích xuất |
|---|---|---|---|---|
| **LUT4** | 2.180 | 20.736 | **10,51 %** | Hiện vật `build:hdl:pnr` (v5) / Datasheet DS226 |
| **Flip-Flop (DFF)** | 820 | 15.552 | **5,27 %** | Hiện vật `build:hdl:pnr` (v5) / Datasheet DS226 |
| **BSRAM** | 16 khối (32 KB) | 46 khối (103,5 KB) | **34,78 %** | Hiện vật `build:hdl:pnr` (v5) / Datasheet DS226 |
| **DSP (MULT18X18)** | 0 | 48 khối | **0,00 %** | Hiện vật `build:hdl:pnr` (v5) / Datasheet DS226 |
| **Chân IOB (User I/O)** | 9 | 384 (on-chip) | **2,34 %** | Hiện vật `build:hdl:pnr` (v5) / `tangnano20k.cst` |

- **Tần số hoạt động tối đa (Fmax)**: đạt **134,93 MHz** (xung nhịp hệ thống chạy ở 27 MHz, thặng dư định thời slack rất lớn).
- **Nhận xét**: Cấu hình Bài 1 mới chỉ chiếm hơn 10 % logic và hoàn toàn chưa dùng khối DSP nào.

---

## Phần 2 — Bài 2 cần thêm gì (Nhân ma trận N×N)

Bài 2 thực hiện nhân hai ma trận vuông $A \times B = C$ với kích thước $N \times N$, hỗ trợ $N$ từ 4 đến 32 trên hai kiểu dữ liệu:
- **I8**: số nguyên 8-bit có dấu (`int8_t`, 1 byte/phần tử).
- **I32**: số nguyên 32-bit có dấu (`int32_t`, 4 byte/phần tử).

### 1. Phân tích bộ nhớ BRAM

Hệ thống cần lưu trữ ba ma trận: ma trận nguồn $A$, ma trận nguồn $B$, và ma trận kết quả $C$.

**Công thức tính dung lượng dữ liệu ba ma trận:**
$$S_{data} = 3 \times N^2 \times S_{type} \text{ (byte)}$$
Trong đó:
- $S_{type} = 1$ byte đối với kiểu I8.
- $S_{type} = 4$ byte đối với kiểu I32.

BRAM hiện tại của SoC được cấu hình là **32 KB** = 32.768 byte.
Ước lượng vùng nhớ dành cho chương trình thực thi (mã máy firmware, runtime C, vùng ngăn xếp Stack, vùng dữ liệu BSS): $S_{prog} \approx 4\text{ KB}$ = 4.096 byte.
Dung lượng BRAM khả dụng cho ma trận:
$$S_{avail} = 32.768 - 4.096 = 28.672 \text{ byte} \approx 28 \text{ KB}$$

**Bảng tính toán dung lượng cho các kích thước N:**

| N | Kiểu dữ liệu | Dung lượng ma trận $S_{data}$ | Tổng RAM cần ($S_{data} + S_{prog}$) | Tình trạng với BRAM 32 KB |
|---|---|---|---|---|
| **4** | I8 | $3 \times 4^2 \times 1 = 48$ byte | ~4,1 KB | **Vừa** (12,8 %) |
| **4** | I32 | $3 \times 4^2 \times 4 = 192$ byte | ~4,3 KB | **Vừa** (13,4 %) |
| **8** | I8 | $3 \times 8^2 \times 1 = 192$ byte | ~4,3 KB | **Vừa** (13,4 %) |
| **8** | I32 | $3 \times 8^2 \times 4 = 768$ byte | ~4,8 KB | **Vừa** (15,0 %) |
| **16** | I8 | $3 \times 16^2 \times 1 = 768$ byte | ~4,8 KB | **Vừa** (15,0 %) |
| **16** | I32 | $3 \times 16^2 \times 4 = 3.072$ byte (3 KB) | ~7,1 KB | **Vừa** (22,2 %) |
| **32** | I8 | $3 \times 32^2 \times 1 = 3.072$ byte (3 KB) | ~7,1 KB | **Vừa** (22,2 %) |
| **32** | I32 | $3 \times 32^2 \times 4 = 12.288$ byte (12 KB) | ~16,3 KB | **Vừa** (50,9 %) |
| *48 (mở rộng)* | I32 | $3 \times 48^2 \times 4 = 27.648$ byte (27 KB) | ~31,7 KB | **Mép trần** (99,1 %) |
| *64 (mở rộng)* | I32 | $3 \times 64^2 \times 4 = 49.152$ byte (48 KB) | ~53,2 KB | **KHÔNG VỪA** (> 100 %) |

**Kết luận về bộ nhớ:**
- Trong phạm vi đề bài yêu cầu ($N \le 32$): **Tất cả các trường hợp I8 và I32 đều vừa vặn hoàn toàn** trong BRAM 32 KB (kịch bản nặng nhất $N=32$, I32 chỉ chiếm khoảng 50,9 % BRAM).
- Nếu mở rộng lên $N = 64$ với kiểu I32, dung lượng 48 KB dữ liệu sẽ vượt quá BRAM 32 KB hiện tại. Khi đó phải bỏ hoặc nâng BRAM SoC lên 64 KB (chip có 103,5 KB BSRAM nên hoàn toàn nâng được lên 64 KB).

---

### 2. Đo đạc tài nguyên cho ba cấu hình CPU (H0, H1, H2)

Để có số đo thực tế chính xác mà không phải phỏng đoán, chúng tôi đã tiến hành tổng hợp bằng công cụ Yosys (`synth_gowin`) trên cùng mô-đun `soc_top` cho từng cấu hình:

1. **H0 (Bản hiện tại)**: CPU RV32I thuần, không bộ nhân phần cứng (`ENABLE_MUL=0`, `ENABLE_FAST_MUL=0`). Phép nhân thực hiện bằng hàm phần mềm gcc (`__mulsi3`).
2. **H1 (Bộ nhân tuần tự bằng LUT logic)**: Bật `ENABLE_MUL=1`, `ENABLE_FAST_MUL=0`. PicoRV32 tích hợp bộ nhân dịch-cộng tuần tự (multi-cycle) hoàn toàn bằng logic LUT.
3. **H2 (Bộ nhân nhanh sử dụng DSP)**: Bật `ENABLE_MUL=0`, `ENABLE_FAST_MUL=1`. PicoRV32 sinh mạch nhân phần cứng ánh xạ vào khối DSP nhúng của Gowin.

**Bảng đối chiếu số đo tổng hợp thực tế:**

| Cấu hình | LUT (Yosys) | Chênh lệch LUT | Flip-Flop | Chênh lệch FF | Khối DSP | BSRAM |
|---|---|---|---|---|---|---|
| **H0 (Gốc)** | 2.239 | Gốc | 628 | Gốc | 0 | 16 |
| **H1 (`ENABLE_MUL=1`)** | 2.554 | **+315 LUT** (+14,1 %) | 907 | **+279 FF** (+44,4 %) | **0** | 16 |
| **H2 (`ENABLE_FAST_MUL=1`)** | 2.271 | **+32 LUT** (+1,4 %) | 785 | **+157 FF** (+25,0 %) | **1 MULT36X36** (4 khối MULT18X18) | 16 |

**Phân tích kết quả đo:**
- **Cấu hình H1**: Tốn thêm 315 LUT và 279 FF để dựng bộ nhân tuần tự 32-bit. Không tốn khối DSP nào.
- **Cấu hình H2**: Bộ nhân nhanh tận dụng khối DSP cứng, chỉ tiêu tốn thêm 32 LUT (logic giao tiếp điều khiển) và 157 FF cho đường ống tín hiệu, đồng thời sử dụng 1 khối nhân `MULT36X36` của Gowin (tương đương 4 khối `MULT18X18`, chiếm 4 / 48 = 8,33 % năng lực DSP của chip).

---

## Phần 3 — Bài 3 cần thêm gì (Tăng tốc phần cứng)

Bài 3 phát triển các bộ tăng tốc tính toán theo ba cấp độ (nối qua giao diện đồng xử lý PCPI hoặc bus nội):

### Cấp độ 1: MAC vô hướng (Multiply-Accumulate 32-bit)
- **Chức năng**: Tính $Acc \leftarrow Acc + (A \times B)$ trong 1–2 chu kỳ.
- **Cơ sở ước lượng**: Tương đương mạch H2 (1 bộ nhân phần cứng 32-bit) cộng thêm 1 bộ tích luỹ (bộ cộng 64-bit hoặc 32-bit với thanh ghi lưu trữ và logic phát hiện tràn).
- **Tài nguyên ước lượng**:
  + DSP: 4 khối `MULT18X18` (hoặc 1 khối `MULTALU36X18` tích hợp sẵn bộ cộng trong khối DSP Gowin).
  + LUT: thêm khoảng 60 – 100 LUT (giải mã lệnh tuỳ biến trên PCPI và dồn kênh).
  + Flip-Flop: thêm khoảng 100 – 160 FF.

### Cấp độ 2: Lệnh `dot4` (Bốn bộ nhân 8×8 song song)
- **Chức năng**: Tính tích vô hướng của hai vector 4 phần tử 8-bit:
  $$Result = (a_0 \times b_0) + (a_1 \times b_1) + (a_2 \times b_2) + (a_3 \times b_3)$$
- **Cơ sở ước lượng**:
  + Khối DSP Gowin GW2A-18C cho phép cấu hình mỗi khối DSP thành hai bộ nhân 9×9 bit độc lập (tổng cộng chip có tới 96 bộ nhân 9×9 bit).
  + Bốn phép nhân 8×8 bit chỉ cần **2 khối MULT18X18** (4 bộ nhân 9×9 bit).
  + Cây cộng 3 tầng (adder tree) gom kết quả 16-bit: tốn khoảng 80–120 LUT.
  + Giao tiếp opcode tuỳ biến PCPI: ~50 LUT.
- **Tài nguyên ước lượng**:
  + DSP: 2 khối `MULT18X18` (4,17 % DSP chip).
  + LUT: thêm khoảng 150 – 250 LUT.
  + Flip-Flop: thêm khoảng 80 – 120 FF.

### Cấp độ 3: Đơn vị Vector mini (4–8 thanh ghi vector 128-bit)
- **Chức năng**: Tập thanh ghi vector chuyên dụng (Vector Register File - VRF) gồm 4 đến 8 thanh ghi dài 128-bit, đi kèm ALU vector xử lý song song các kiểu dữ liệu I8 (16 lane) hoặc I32 (4 lane).
- **Cơ sở ước lượng**:
  + **Tập thanh ghi VRF**: $8 \times 128\text{ bit} = 1.024\text{ bit}$. Nếu cài đặt bằng Flip-Flop thông thường, tốn đúng 1.024 FF (6,58 % dung lượng FF của chip). Nếu cài đặt bằng Gowin Shadow RAM (RAM16SDP4), chỉ tốn 16 ô nhớ phân tán và vài chục LUT.
  + **ALU Vector**: 4 lane 32-bit MAC song song cần 16 khối `MULT18X18` (hoặc 16 lane 8-bit cần 8 khối `MULT18X18`).
  + **Bộ điều khiển Vector**: Logic giải mã, sinh địa chỉ vector load/store theo stride, điều khiển vòng lặp vector: ước tính khoảng 800 – 1.500 LUT.
- **Tài nguyên ước lượng**:
  + DSP: 8 – 16 khối `MULT18X18` (16,6 % – 33,3 % DSP chip).
  + LUT: thêm khoảng 1.000 – 1.800 LUT (4,8 % – 8,7 % chip).
  + Flip-Flop: thêm khoảng 1.200 – 1.500 FF (7,7 % – 9,6 % chip).

---

## Phần 4 — Đánh giá giới hạn: Chỗ nào chạm trần trước?

Tổng hợp mức tiêu thụ tài nguyên dự kiến khi thực hiện toàn bộ Bài 3 (kịch bản cấu hình tối đa gồm SoC + Vector Mini 8 thanh ghi + 4 MAC song song):

| Loại tài nguyên | Bài 1 (PnR thật) | Dự kiến thêm (Bài 2 + Bài 3) | Tổng tích luỹ | Dung lượng chip | Tỷ lệ sử dụng | Hạn định mức |
|---|---|---|---|---|---|---|
| **LUT4** | 2.180 | +1.800 | **~3.980** | 20.736 | **19,2 %** | $\le$ 85 % (17.625) |
| **Flip-Flop** | 820 | +1.500 | **~2.320** | 15.552 | **14,9 %** | 100 % |
| **Khối DSP** | 0 | +16 | **16** | 48 | **33,3 %** | 100 % |
| **Chân I/O** | 9 | 0 | **9** | Đủ chân header | Rất thấp | 100 % |
| **BSRAM (32 KB BRAM)** | 16 | 0 | **16** | 46 khối (103,5 KB) | **34,78 %** | 100 % |

### Đánh giá 5 loại tài nguyên:

1. **LUT4 (Logic)**: Đề bài yêu cầu ngưỡng an toàn $\le 85\ \%$ (tương đương tối đa 17.625 LUT). Khi tích hợp toàn bộ đơn vị vector mini, SoC chỉ chiếm khoảng 19,2 % LUT. **Còn trống hơn 13.600 LUT** trước khi chạm trần 85 %. Logic hoàn toàn thoải mái.
2. **Flip-Flop**: Mức chiếm dụng tối đa chỉ ~15 %, thặng dư trên 13.000 FF.
3. **DSP**: Kể cả khi triển khai 4 bộ MAC 32-bit song song cho vector mini, hệ thống chỉ dùng 16 / 48 khối DSP (33,3 %).
4. **Chân I/O**: Giao tiếp giữ nguyên qua UART và LED hiện tại nên không phát sinh chân ngoài.
5. **BSRAM (Bộ nhớ SRAM nội)**:
   - Hiện tại SoC chỉ gán 32 KB (16 khối BSRAM).
   - Với kích thước bài toán $N \le 32$, BRAM 32 KB đáp ứng tốt cả I8 và I32 (chiếm tối đa 50,9 %).
   - **Tuy nhiên**, nếu bài toán mở rộng lên $N \ge 64$ với I32 (cần 48 KB dữ liệu ma trận + chương trình), BRAM 32 KB sẽ bị tràn ngay lập tức. Mặc dù chip GW2A-18C có 46 khối BSRAM (103,5 KB) cho phép ta mở rộng BRAM SoC lên 64 KB (32 khối), nhưng 103,5 KB là trần cứng tuyệt đối của toàn bộ chip.

> **Kết luận điểm nghẽn**: **BSRAM là loại tài nguyên eo hẹp nhất và sẽ chạm trần đầu tiên** khi tăng kích thước bài toán hoặc dữ liệu ma trận, trong khi logic LUT và bộ nhân cứng DSP còn rất dư dả.

---

## Kết luận

**Kit Sipeed Tang Nano 20K hoàn toàn đủ sức chạy hết toàn bộ chương trình của đề án (từ Bài 1, Bài 2 đến Bài 3) với điều kiện kích thước ma trận $N \le 32$ đối với kiểu dữ liệu I32 (hoặc $N \le 48$ nếu tinh giản stack/code) do giới hạn dung lượng bộ nhớ BSRAM nội của chip.**

---

## Phụ lục — Kiểm lại bằng phép đo độc lập (anh Công yêu cầu)

*Người giao việc chạy lại các phép đo trong tài liệu này, không tin bảng đã viết.*

### Ba cấu hình CPU: tái lập ĐÚNG từng con số

Tổng hợp lại `soc_top` với từng tham số, đọc bảng thống kê của Yosys:

| Cấu hình | LUT | FF | DSP | Chênh so với H0 |
|---|---|---|---|---|
| H0 hiện tại | 2 239 | 628 | không | — |
| H1 `ENABLE_MUL=1` | 2 554 | 907 | không | **+315 LUT · +279 FF** |
| H2 `ENABLE_FAST_MUL=1` | 2 271 | 785 | **1× MULT36X36** | **+32 LUT · +157 FF** |

Khớp từng số với bảng ở Phần 2. Đây là **đo thật**, không phải ước lượng.

Con số đáng chú ý: H2 chỉ tốn thêm **32 LUT** mà có bộ nhân một chu kỳ, vì nó đẩy phép nhân
xuống khối DSP cứng. H1 làm bộ nhân bằng LUT nên tốn gấp mười lần logic.

### Nâng BRAM: đo được tới 64 KB, KHÔNG đo được quá đó

| BRAM đặt | BSRAM dùng | Fmax |
|---|---|---|
| 32 KB | 16/46 (35 %) | 134,93 MHz |
| **64 KB** | **32/46 (70 %)** | **102,2 MHz** |
| 96 KB | 16/46 | 130,55 MHz |
| 128 KB | 32/46 | 79,43 MHz |

**Hai dòng cuối là số vô lý và không được dùng.** 96 KB không thể dùng ít khối hơn 64 KB. Lý do:
độ rộng địa chỉ trong `soc_top` cố định, nên phần nhớ vượt dải địa chỉ bị khâu tổng hợp cắt bỏ —
phép đo đang đo một thiết kế khác với thiết kế mình nghĩ.

Ghi lại cả chỗ phép đo hỏng, vì một bảng chỉ có hai dòng đẹp sẽ khiến người sau tin rằng 128 KB
đã được kiểm.

**Kết luận đo được:**
- Nâng BRAM lên **64 KB chạy được**, chiếm 70 % BSRAM, Fmax còn **102 MHz** — vẫn dư gần bốn
  lần so với 27 MHz cần chạy. Nên khẳng định "nâng được lên 64 KB" ở Phần 4 là **có sở cứ**.
- Trần 103,5 KB của chip là con số **datasheet**, chưa ai đo. Muốn đo thì phải nới cả độ rộng
  địa chỉ trong `soc_top`, không chỉ đổi `WORDS`.

### Một chỗ bản đánh giá nói hơi quá

Phần 4 kết luận *"BSRAM là loại tài nguyên eo hẹp nhất và sẽ chạm trần đầu tiên"*. Đúng khi suy
rộng ra N ≥ 64, nhưng **trong phạm vi đề bài đặt ra** (N ≤ 32) thì BSRAM chỉ dùng 35 %, và
không loại tài nguyên nào chạm gần trần. Câu đúng hơn: *trong phạm vi đề bài, không có chỗ nào
chật; BSRAM là chỗ sẽ chật trước nếu mở rộng bài toán.*
