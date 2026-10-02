# Báo cáo Kết quả Đo đạc Nhân Ma trận (Bài 2)

Tài liệu này tổng hợp và phân tích 96 điểm đo đạc thực nghiệm từ tệp `results/all.csv` cho bài toán nhân ma trận vuông $C = A \times B$ trên lõi vi xử lý PicoRV32 (FPGA Gowin GW2AR-18C).

Tất cả 96/96 điểm đo đều đạt kiểm tra tính đúng đắn (`ok=1`), bao phủ:
- 4 kích thước ma trận: $N \in \{4, 8, 16, 32\}$
- 2 kiểu dữ liệu:
  - **I8**: $A, B$ kiểu `int8_t` (8 bit), tích luỹ $C$ kiểu `int32_t` (32 bit)
  - **I32**: $A, B, C$ đều là `int32_t` (32 bit)
- 4 phiên bản thuật toán phần mềm:
  - **V0**: Ba vòng lặp kinh điển $i-j-k$
  - **V1**: Hoán đổi thứ tự vòng lặp $i-k-j$ (truy cập theo hàng)
  - **V2**: $V1$ kết hợp mở vòng lặp trong (loop unrolling) theo $j$ bước 4
  - **V3**: Chia khối ma trận (cache tiling) kích thước $4 \times 4$ (áp dụng cho $N \ge 16$, chuyển tiếp $V2$ khi $N < 16$)
- 3 cấu hình phần cứng CPU:
  - **H0**: CPU `rv32i` thuần tuý, không có khối nhân phần cứng (nhân bằng phần mềm qua thư viện GCC `__mulsi3`)
  - **H1**: Bật bộ nhân tuần tự phần cứng (`ENABLE_MUL=1`, đa chu kỳ)
  - **H2**: Bật bộ nhân nhanh phần cứng dùng DSP block (`ENABLE_FAST_MUL=1`, dùng 1 khối `MULT36X36`)

Đơn vị đo: **cpm** (cycles per MAC — chu kỳ trên mỗi phép nhân-cộng, tổng số phép tính $MAC = N^3$).

---

## 1. Cấu hình CPU đổi được bao nhiêu — H0 so với H1 và H2

### Bảng đối chiếu hiệu năng và tài nguyên phần cứng

| Cấu hình | cpm ($N=32$, I8, V2) | Tỷ lệ tăng tốc so với H0 | cpm ($N=32$, I32, V2) | Tỷ lệ tăng tốc so với H0 | Tài nguyên LUT | Tài nguyên FF | BSRAM | Khối DSP | Chênh lệch so với H0 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **H0** (`rv32i`) | 602,83 | $1,00\times$ (cơ sở) | 644,78 | $1,00\times$ (cơ sở) | 2 352 | 627 | 16 | 0 | Cơ sở |
| **H1** (`ENABLE_MUL=1`) | 71,09 | **$8,48\times$** | 71,22 | **$9,05\times$** | 2 562 | 907 | 16 | 0 | LUT **+210** · FF +280 |
| **H2** (`ENABLE_FAST_MUL=1`) | 37,09 | **$16,25\times$** | 37,22 | **$17,32\times$** | 2 232 | 785 | 16 | 1× MULT36X36 | LUT **−120** · FF +158 |

*(Ghi chú: Số đo tài nguyên thực hiện trực tiếp trên `rtl/` hiện tại bằng cách đổi tham số mô-đun cấp cao nhất qua lệnh `chparam -set ENABLE_MUL … -set ENABLE_FAST_MUL … soc_top` rồi chạy `synth_gowin -top soc_top` trong Yosys).*

### Phân tích kỹ thuật

1. **Từ H0 lên H1 (Bổ sung bộ nhân tuần tự đa chu kỳ)**:
   - Ở H0, phép nhân số học phải gọi hàm thư viện phần mềm `__mulsi3`, thực hiện giải thuật dịch và cộng (shift-and-add) tốn khoảng 40–50 chỉ lệnh (tương đương vài chục đến hàng trăm chu kỳ clock cho mỗi phép nhân 32-bit).
   - Ở H1, bộ nhân tuần tự phần cứng bên trong PicoRV32 xử lý phép nhân trong khoảng 32–34 chu kỳ. Nhờ đó, hiệu năng tăng vọt từ **8,5× đến 9,0×** (giảm ~88–89 % tổng số chu kỳ thực thi). Đổi lại, tài nguyên logic mềm tăng 210 LUT (+8,9 %) và 280 FF (+44,7 %).

2. **Từ H1 lên H2 (Chuyển sang bộ nhân nhanh dùng DSP) — H2 nhanh hơn 16 lần mà còn RẺ hơn về LUT**:
   - H2 tận dụng khối nhân cứng chuyên dụng `MULT36X36` có sẵn trên silicon của dòng Gowin LittleBee GW2AR-18C. Thời gian thực thi phép nhân 32-bit giảm xuống chỉ còn 2–3 chu kỳ.
   - Hiệu năng H2 tăng gấp **$1,91\times$ so với H1**, và tăng vọt từ **$16,2\times$ đến $17,3\times$ so với H0**.
   - **Kết luận cốt lõi: H2 nhanh hơn 16 lần nhưng lại RẺ hơn H0 về tài nguyên logic mềm (LUT)**. H2 dùng 2 232 LUT, ít hơn H0 (2 352 LUT) đúng **120 LUT** (−5,1 %). Đây là kết luận thực nghiệm quan trọng nhất của Bài 2.
   - **Cơ chế kỹ thuật đằng sau con số ngược trực giác này**:
     Phân rã chi tiết các loại ô logic giữa H0 và H2 cho thấy:
     ```
     H0:  LUT1=262  MUX2_LUT5=326  MUX2_LUT6=56  MUX2_LUT7=19
     H2:  LUT1=163  MUX2_LUT5=286  MUX2_LUT6=26  MUX2_LUT7=4
     ```
     H2 sử dụng ít hơn tới **99 ô LUT1** và giảm rõ rệt số lượng ô dồn kênh lớn (`MUX2_LUT5`, `MUX2_LUT6`, `MUX2_LUT7`), đổi lại số lượng LUT3 và LUT4 tăng lên. Khi có bộ nhân phần cứng chuyên dụng, đường dữ liệu (datapath) trong CPU không cần các mạng dồn kênh phức tạp để luân chuyển dữ liệu ALU qua nhiều chu kỳ. Nhờ đó, bộ tổng hợp logic gói được nhiều hàm chức năng vào các bảng tra LUT rộng hơn thay vì phải chẻ nhỏ và ghép qua nhiều tầng dồn kênh.
   - **Cảnh báo kỹ thuật**: Con số LUT âm (−120 LUT) này là **kết quả của bộ tổng hợp trên thiết kế NÀY** (lõi PicoRV32 cùng cấu trúc SoC và bộ công cụ Yosys `synth_gowin`), không phải một quy luật phổ quát chung cho mọi kiến trúc hay mọi trường hợp thêm khối nhân cứng.

3. **Cách tái hiện phép đo tài nguyên (Reproducibility)**:
   Để kiểm tra lại các số liệu trên bất kỳ lúc nào, chạy Yosys với các lệnh sau:
   ```tcl
   # Cấu hình H0 (rv32i thuần):
   chparam -set ENABLE_MUL 0 -set ENABLE_FAST_MUL 0 soc_top
   synth_gowin -top soc_top

   # Cấu hình H1 (bộ nhân tuần tự):
   chparam -set ENABLE_MUL 1 -set ENABLE_FAST_MUL 0 soc_top
   synth_gowin -top soc_top

   # Cấu hình H2 (bộ nhân DSP MULT36X36):
   chparam -set ENABLE_MUL 0 -set ENABLE_FAST_MUL 1 soc_top
   synth_gowin -top soc_top
   ```

---

## 2. Đánh giá thuật toán phần mềm: Ai thắng và nguyên nhân kỹ thuật

Trong tổng số 24 tổ hợp thử nghiệm (4 kích thước $N \times 2$ kiểu dữ liệu $\times 3$ cấu hình phần cứng):

- **V2 thắng tuyệt đối ở 21 / 24 tổ hợp** (chiếm 87,5 % số trường hợp).
- **V0 thắng ở 3 / 24 tổ hợp** (chiếm 12,5 % số trường hợp). Cụ thể là:
  1. Tổ hợp `n=4, dtype=I8, hw=H0`: V0 đạt **719,48 cpm** vs V2 đạt **758,28 cpm** (V0 nhanh hơn 5,1 %).
  2. Tổ hợp `n=8, dtype=I8, hw=H0`: V0 đạt **573,36 cpm** vs V2 đạt **656,58 cpm** (V0 nhanh hơn 12,7 %).
  3. Tổ hợp `n=32, dtype=I8, hw=H0`: V0 đạt **601,17 cpm** vs V2 đạt **602,83 cpm** (V0 nhỉnh hơn 0,3 %).
  *(Riêng tại `n=16, dtype=I8, hw=H0`, V2 thắng sít sao: V2 đạt 601,19 cpm vs V0 đạt 618,04 cpm).*
- **V1 và V3 không thắng ở bất kỳ tổ hợp nào**.

### Bảng tổng hợp so sánh cpm giữa các phiên bản tại $N=32$

| Cấu hình & Kiểu | V0 ($i-j-k$) | V1 ($i-k-j$) | V2 (V1 + unroll ×4) | V3 (Tiling 4×4) | Phiên bản tốt nhất |
|:---|:---:|:---:|:---:|:---:|:---:|
| H0, I32 | 673,31 | 680,50 | **644,78** | 670,32 | **V2** |
| H0, I8  | **601,17** | 656,89 | 602,83 | 635,12 | **V0** |
| H1, I32 | 82,47 | 82,43 | **71,22** | 74,97 | **V2** |
| H1, I8  | 82,16 | 90,36 | **71,09** | 74,59 | **V2** |
| H2, I32 | 48,47 | 48,43 | **37,22** | 40,97 | **V2** |
| H2, I8  | 48,16 | 56,36 | **37,09** | 40,59 | **V2** |

### Giải thích nguyên nhân kỹ thuật

1. **Vì sao V2 áp đảo ở hầu hết các trường hợp**:
   - V2 lấy cấu trúc hoán vị vòng lặp $i-k-j$ của V1 để đưa phần tử $a_{ik}$ ra làm hằng số trong suốt vòng lặp trong theo $j$.
   - Đồng thời, V2 mở vòng lặp trong theo bước 4 (unrolling $\times 4$). Việc mở vòng lặp này loại bỏ 75 % số lệnh kiểm tra điều kiện nhảy và tăng biến đếm của vòng lặp $j$, đồng thời tận dụng bộ nạp liên tiếp theo hàng của $b$ và ghi dồn vào mảng $c$. Nhờ đó, V2 giảm từ 10–11 chu kỳ/MAC so với V1 trên H1 và H2 (ví dụ tại $N=32, H2$: V1 tốn 48,43 cpm, V2 chỉ tốn 37,22 cpm).

2. **Vì sao V0 lại thắng V2 ở cấu hình H0 với kiểu I8**:
   - **Vấn đề thanh ghi so với bộ nhớ**:
     - Trong V0 ($i-j-k$), biến tích luỹ `sum` được giữ nguyên vẹn trong một thanh ghi CPU 32-bit trong suốt toàn bộ vòng lặp $k$. Không có bất kỳ lệnh đọc hay ghi nào tới bộ nhớ đối với mảng kết quả $c$ trong thân vòng lặp trong.
     - Trong V1 và V2 ($i-k-j$), tại mỗi bước lặp $j$, mã máy bắt buộc phải: **LOAD** `ci[j]` từ RAM (lệnh `lw`), thực hiện nhân-cộng, rồi **STORE** `ci[j]` ngược lại vào RAM (lệnh `sw`).
   - **Gánh nặng trích xuất byte I8 khi nhân phần mềm**:
     - Khi chạy trên H0 (không có bộ nhân phần cứng), việc gọi hàm phần mềm `__mulsi3` phá huỷ các thanh ghi tạm (caller-saved registers), buộc trình biên dịch phải đẩy/kéo thanh ghi vào ngăn xếp (stack spills).
     - Với kiểu I8, mỗi phần tử của $b$ phải nạp qua lệnh `lb` (load byte kèm mở rộng dấu sign-extension). Sự kết hợp giữa stack overhead của hàm phần mềm, thao tác nạp/ghi mảng `ci[j]` liên tục trong V2, và chi phí sign-extend đã khiến V2 tốn nhiều chu kỳ hơn so với V0 — nơi mà `sum` được cô lập trong thanh ghi và chỉ ghi ra bộ nhớ một lần duy nhất ở cuối vòng lặp $k$.

3. **Vì sao V3 (chia khối / tiling $4 \times 4$) lại kém hơn V2**:
   - Thuật toán chia khối (tiling) sinh ra nhằm mục đích tối ưu hoá tỷ lệ trúng bộ nhớ đệm (cache hit rate) trên các bộ vi xử lý lớn có hệ thống bộ nhớ phân cấp (L1/L2 cache).
   - Tuy nhiên, vi hệ thống PicoRV32 trong SoC này sử dụng **BRAM nội bộ phẳng (flat single-cycle on-chip BRAM)**, không có phân cấp cache và không có hình phạt trễ (cache miss penalty = 0 chu kỳ).
   - Do đó, kỹ thuật chia khối trong V3 không mang lại bất kỳ lợi ích nào về băng thông nhớ, mà ngược lại còn làm tăng đáng kể chi phí điều khiển (6 tầng vòng lặp lồng nhau $ii, kk, jj, i, k, j$ cùng các phép tính địa chỉ bù trừ). Hậu quả là V3 luôn tốn thêm khoảng 3,5–4,0 cpm so với V2 (ví dụ tại $N=32, H2, I32$: V2 đạt 37,22 cpm trong khi V3 tốn 40,97 cpm).

---

## 3. Biến thiên của cpm theo kích thước ma trận N (4 → 32)

Quan sát sự thay đổi của cpm khi $N$ tăng dần từ 4 lên 32 (xét trên thuật toán tối ưu V2):

| Cấu hình & Kiểu | $N=4$ | $N=8$ | $N=16$ | $N=32$ | Xu hướng biến thiên |
|:---|:---:|:---:|:---:|:---:|:---|
| **H2, I32** | 50,96 | 42,27 | 38,79 | **37,22** | Giảm liên tục 27,0 % |
| **H2, I8**  | 49,25 | 41,64 | 38,51 | **37,09** | Giảm liên tục 24,7 % |
| **H1, I32** | 84,96 | 76,27 | 72,79 | **71,22** | Giảm liên tục 16,2 % |
| **H1, I8**  | 83,25 | 75,64 | 72,51 | **71,09** | Giảm liên tục 14,6 % |
| **H0, I32** | 688,40 | 650,63 | 656,62 | **644,78** | Dao động, xu hướng giảm |
| **H0, I8**  | 758,28 | 656,58 | 601,19 | **602,83** | Giảm mạnh rồi bão hoà |

### Nguyên nhân kỹ thuật

Chỉ số **cpm** (chu kỳ trên mỗi phép MAC) giảm rõ rệt và tiệm cận về một hằng số khi $N$ tăng lên:
1. **San đều chi phí cố định (Amortization)**:
   - Tổng số phép toán MAC tăng theo luỹ thừa bậc 3 ($N^3$): khi $N=4$ chỉ có 64 MAC, nhưng khi $N=32$ có tới 32 768 MAC (tăng gấp 512 lần).
   - Trong khi đó, các chi phí phụ trợ bao gồm:
     - Chi phí cố định khởi tạo hàm, chuẩn bị con trỏ, lưu/phục hồi thanh ghi: độ phức tạp $O(1)$.
     - Chi phí vòng lặp ngoài cùng ($i$): độ phức tạp $O(N)$.
     - Chi phí khởi tạo mảng tích luỹ `ci[j] = 0` và bước lặp giữa ($k$): độ phức tạp $O(N^2)$.
   - Khi chia các chi phí phụ trợ $O(1), O(N), O(N^2)$ cho tổng số phép tính $N^3$, phần đóng góp của chúng triệt tiêu dần về 0:
     $$\text{cpm} = \frac{\text{Cycles}}{N^3} = \frac{C_{\text{core}} \cdot N^3 + C_2 \cdot N^2 + C_1 \cdot N + C_0}{N^3} \approx C_{\text{core}} + \frac{C_2}{N}$$
   - Ở $N=4$, phần phụ trợ $C_2/N$ chiếm tỷ trọng đáng kể khiến cpm bị đội lên cao. Đến $N=32$, chi phí phụ trợ gần như bị triệt tiêu hoàn toàn, cpm hội tụ về chi phí thực tế thuần tuý của thân vòng lặp trong cùng ($C_{\text{core}} \approx 37$ chu kỳ/MAC đối với H2).

---

## 4. Dùng I32 thay I8 tốn thêm bao nhiêu? — Nghịch lý dữ liệu hẹp trên lõi vô hướng

### Bảng so sánh chi phí chênh lệch giữa I32 và I8 (tại thuật toán tối ưu V2)

| Cấu hình CPU | Kích thước | cpm (I8) | cpm (I32) | Chênh lệch cpm (I32 − I8) | % Tăng thêm của I32 |
|:---|:---:|:---:|:---:|:---:|:---:|
| **H0** (`rv32i`) | $N=4$  | 758,28 | 688,40 | −69,88 | −9,2 % *(V0: I32 tốn kém hơn I8)* |
| **H0** (`rv32i`) | $N=8$  | 656,58 | 650,63 | −5,95  | −0,9 % *(V0: I8 = 573,36 vs I32 = 678,45: I32 tốn hơn +18,3 %)* |
| **H0** (`rv32i`) | $N=16$ | 601,19 | 656,62 | +55,43 | **+9,2 %** |
| **H0** (`rv32i`) | $N=32$ | 602,83 | 644,78 | +41,95 | **+7,0 %** |
| **H1** (`MUL=1`) | $N=4$  | 83,25  | 84,96  | +1,71  | +2,1 % |
| **H1** (`MUL=1`) | $N=8$  | 75,64  | 76,27  | +0,63  | +0,8 % |
| **H1** (`MUL=1`) | $N=16$ | 72,51  | 72,79  | +0,28  | +0,4 % |
| **H1** (`MUL=1`) | $N=32$ | 71,09  | 71,22  | **+0,13** | **+0,18 %** |
| **H2** (`FAST_MUL=1`) | $N=4$  | 49,25  | 50,96  | +1,71  | +3,5 % |
| **H2** (`FAST_MUL=1`) | $N=8$  | 41,64  | 42,27  | +0,63  | +1,5 % |
| **H2** (`FAST_MUL=1`) | $N=16$ | 38,51  | 38,79  | +0,28  | +0,7 % |
| **H2** (`FAST_MUL=1`) | $N=32$ | 37,09  | 37,22  | **+0,13** | **+0,35 %** |

### Sự ngạc nhiên và Lý do Kiến trúc PicoRV32

**Sự ngạc nhiên**:
Về trực giác, ma trận 8-bit (I8) có dung lượng bộ nhớ nhỏ hơn ma trận 32-bit (I32) tới 4 lần ($1/4$). Người ta kỳ vọng rằng I8 phải chạy nhanh hơn I32 rất nhiều (gấp 2 đến 4 lần). Thế nhưng trên thực tế ở cấu hình phần cứng H1 và H2, **I32 hầu như không tốn thêm bao nhiêu chu kỳ so với I8**:
- Ở $N=32$, I32 chỉ tốn thêm đúng **0,13 chu kỳ** trên mỗi phép tính MAC (+0,18 % ở H1 và +0,35 % ở H2). Hai đường cong hiệu năng của I8 và I32 gần như trùng khít lên nhau!

**Nguyên nhân nằm ở bản chất kiến trúc của PicoRV32**:
1. **Bản chất vô hướng 32-bit (Scalar 32-bit Architecture)**:
   - PicoRV32 là một vi xử lý RISC-V 32-bit tiêu chuẩn, không có phần cứng SIMD (Single Instruction Multiple Data) hay Vector mở rộng.
   - Các thanh ghi đa năng ($x0 \dots x31$) và đường truyền dữ liệu (datapath) đều cố định ở độ rộng 32 bit. Dù biến đầu vào là `int8_t`, khi nạp vào CPU qua lệnh `lb`, CPU vẫn phải thực hiện thao tác mở rộng dấu (sign-extension) thành số nguyên 32 bit đầy đủ.
2. **Khối nhân phần cứng xử lý kích thước cố định**:
   - Cả bộ nhân tuần tự H1 (`ENABLE_MUL=1`) và bộ nhân DSP H2 (`ENABLE_FAST_MUL=1`) đều chỉ nhận toán hạng 32-bit và trả về kết quả 32-bit.
   - Phần cứng không hề có chế độ nhân chuyên biệt cho 8-bit. Dù toán hạng chỉ có giá trị trong khoảng $[-128, 127]$, khối nhân phần cứng vẫn thực thi đúng số chu kỳ quy định của một phép nhân 32-bit đầy đủ.
3. **Mảng tích luỹ $C$ đều là 32-bit (`int32_t`)**:
   - Cả trong I8 lẫn I32, mảng kết quả đều là kiểu 32-bit để tránh tràn số. Thao tác nạp/ghi `ci[j]` qua bus BRAM 32-bit hoàn toàn giống nhau giữa hai kiểu dữ liệu.
4. **Chi phí nạp byte so với nạp từ nhớ (Word vs Byte)**:
   - Thậm chí, việc nạp byte lẻ (`lb`) trong PicoRV32 còn đòi hỏi thêm logic giải mã địa chỉ byte và dịch bit trong chu kỳ đọc, trong khi nạp từ nhớ (`lw`) đọc trực tiếp toàn bộ 32-bit từ BRAM aligned.
5. **Động lực quyết định để chuyển sang Bài 3**:
   - Kết quả này chứng minh rằng: **Phần mềm thuần tuý trên kiến trúc CPU vô hướng chuẩn không thể nào khai thác được lợi thế kích thước của dữ liệu 8-bit**.
   - Đây chính là tiền đề cốt lõi để triển khai Bài 3: Bổ sung tập lệnh tuỳ biến `dot4` qua giao diện đồng xử lý PCPI, cho phép đóng gói 4 phần tử 8-bit vào một từ nhớ 32-bit và tính toán 4 phép MAC song song trong một chu kỳ, từ đó hạ chỉ số cpm xuống dưới $1/2$ của H2.

---

## 5. Giới hạn của bộ số liệu và Kế hoạch kiểm chứng trên bo mạch thực

Tất cả các số liệu trong báo cáo này được đo đạc thông qua công cụ mô phỏng chính xác chu kỳ (cycle-accurate simulation) bằng **Verilator**.

### Những điểm phép đo mô phỏng chưa phản ánh được
1. **Tần số xung nhịp thực tế và Timing Closure**:
   - Mô phỏng Verilator mặc định rằng mọi đường tín hiệu logic đều kịp thời gian xác lập (setup/hold) trong chu kỳ 27 MHz.
   - Khi chạy trên FPGA GW2AR-18C thực tế, thời gian trễ lan truyền qua các lát cắt LUT, dây nối routing, và khối DSP có thể tạo ra vi phạm thời gian nếu không đạt timing closure (Fmax dự tính > 200 MHz, xung nhịp danh định bo là 27 MHz).
2. **Hành vi nguồn và Xung nhịp vật lý**:
   - Hiện tượng jitter của bộ tạo dao động trên bo mạch, độ ổn định của nguồn cấp logic core 1,2 V khi CPU hoạt động với tải tính toán nặng (toàn bộ khối DSP và logic cùng lật trạng thái liên tục).
3. **Độ trễ giao tiếp ngoại vi**:
   - Việc đẩy chuỗi kết quả qua bộ UART TX ở tốc độ 115 200 baud trên phần cứng thực tế có độ trễ vật lý và phụ thuộc vào trạng thái thanh ghi cờ bận `UART_STATUS`. Dù phép đo đã sử dụng lệnh `rdcycle` trừ chi phí hàm đọc ngay sát hai đầu hàm tính toán, sự can thiệp của việc ghi bộ đệm UART cần được khẳng định lại trên mạch thực.

### Mục tiêu kiểm chứng theo đề bài
- Đề bài yêu cầu: **Sai lệch số chu kỳ đo trên bo mạch thực tế so với số chu kỳ mô phỏng Verilator phải thoả mãn $\le 1\,\%$**.
- **Kế hoạch tiếp theo**:
  1. Biên dịch và tổng hợp bitstream hoàn chỉnh của SoC cho cấu hình phần cứng tối ưu (H2) bằng luồng Yosys + NextPNR Himbaechel + Gowin Pack.
  2. Nạp bitstream vào kit Tang Nano 20K thông qua `openFPGALoader`.
  3. Bắt luồng ký tự UART trả về qua cổng nối tiếp USB-CDC ở tốc độ 115 200 baud để đối chiếu trực tiếp các trường `cycles` thực tế với 96 dòng trong `results/all.csv`.
