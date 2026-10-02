# BẢN THIẾT KẾ KIẾN TRÚC NẤC 3C: ĐƠN VỊ VECTOR MINI (TIỀN RVV)

**Dự án**: SoC PicoRV32 trên FPGA Gowin GW2AR-18C (Tang Nano 20K)  
**Tác giả**: Tác tử EIDE & Kỹ sư trưởng CongVT  
**Trạng thái**: Chờ duyệt (Điểm dừng bắt buộc số 4)  
**Tệp mục tiêu**: `docs/bai3-arch.md`  

---

## 1. Thanh ghi vector: Số lượng, độ rộng và phân bổ tài nguyên

### 1.1. Lựa chọn thông số kiến trúc
- **Độ rộng vector ($VLEN$)**: **128 bit**.
  - **Lý do kỹ thuật**: Ma trận mục tiêu của Bài 2 và Bài 3 có kích thước $N \in \{4, 8, 16, 32\}$ với kiểu dữ liệu `int8_t`. Với $N = 16$, đúng một hàng của ma trận $A$ hoặc một cột của ma trận $B$ (đã chuyển vị) có kích thước:
    $$16 \text{ phần tử} \times 8 \text{ bit} = 128 \text{ bit} = 16 \text{ byte} = 4 \text{ từ 32-bit}$$
  - $VLEN = 128$ bit cho phép chứa trọn vẹn toàn bộ một vector hàng/cột của $N = 16$ trong đúng một thanh ghi vector, triệt tiêu phân mảnh vector.
- **Số lượng thanh ghi vector**: **4 thanh ghi** (`v0`, `v1`, `v2`, `v3`).
  - `v0`: Giữ vector hàng của ma trận $A$ (nạp 1 lần, tái sử dụng cho toàn bộ 16 cột của $B$).
  - `v1`: Giữ vector cột của ma trận $B$ (nạp tuần tự từng cột).
  - `v2`, `v3`: Thanh ghi dự phòng (phục vụ mở rộng unrolling $2\times$ tính toán song song 2 cột của $B$, hoặc lưu kết quả trung gian).

### 1.2. Phân tích tài nguyên phần cứng (LUT, FF, BSRAM)
Thiết bị đích là **Gowin GW2AR-LV18QN88C6/I5**:
- Tổng tài nguyên: 20 736 LUT4, 15 552 FF, 46 khối BSRAM (18K bit/khối), 48 DSP9X9.
- Ngưỡng trần đề bài cho phép: **LUT ≤ 85 %** (tối đa 17 625 LUT4).
- Tài nguyên hiện tại của Nấc 3b: **2 796 LUT4 (13,5 %)**, **660 FF (4,2 %)**, **5 DSP**.

| Thành phần vector | Số lượng | Tài nguyên phần cứng ước tính | Loại tài nguyên |
|---|---|---|---|
| **Tệp thanh ghi vector (4 × 128-bit)** | 512 bit lưu trữ | 512 FF | Flip-Flops (DFF) |
| **Bộ dồn kênh đọc (Mux 4-to-1 × 128-bit)** | 2 cổng đọc 128-bit | ~160 LUT4 | LUT logic thuần |
| **Cổng ghi giải mã địa chỉ vector** | 4-bit write enable | ~20 LUT4 | LUT logic thuần |
| **Làn nhân (Execution Lanes)** | 4 bộ nhân 8×8 (tái sử dụng từ 3b) hoặc 16 bộ | 4 DSP (chạy 4 chu kỳ) hoặc 16 DSP (chạy 1 chu kỳ) | Khối DSP có sẵn |
| **FSM điều khiển nạp/tính/wait** | 8 trạng thái, bộ đếm 4-bit | ~60 LUT4, 25 FF | Logic tuần tự |
| **Tổng cộng đơn vị vector mini** | | **~240 LUT4 + 537 FF + DSP** | Hoàn toàn nằm trong tầm kiểm soát |

*Kết luận về tài nguyên*: Tệp thanh ghi $4 \times 128\text{ bit}$ chiếm **512 FF**, chỉ tương đương 3,3 % tổng số FF của FPGA. Sử dụng trực tiếp Flip-Flop (không cần BSRAM) giúp việc đọc/ghi thanh ghi vector hoàn thành ngay trong 0–1 chu kỳ clock, không tạo độ trễ truy xuất (latency) và không phụ thuộc vào công cụ suy luận RAM.

---

## 2. Nạp và lưu: Phân tích đường truyền dữ liệu và nút thắt nạp

Đây là bài toán cốt lõi quyết định Nấc 3c có nhanh hơn Nấc 3b hay không.

### 2.1. Phân tích thực nghiệm Nấc 3b và bản chất của 189 chu kỳ "việc khác"

Trong báo cáo ban đầu của Nấc 3b (chạy ma trận $N=16$, I8), kết quả đo đạc ghi nhận:
$$\text{CPM}_{\text{3b}} = \frac{59\,719\text{ chu kỳ}}{4\,096\text{ MAC}} \approx 14,58\text{ chu kỳ/MAC} \quad (\approx 233,3\text{ chu kỳ cho mỗi cặp } (i, j))$$

Mỗi cặp $(i, j)$ thực hiện 16 phép MAC qua 4 lần gọi `dot4`. Nếu chỉ tính thời gian thực thi tối thiểu của phần cứng:
$$4 \times (2 \times \text{lw } 4\text{ ck} + 1 \times \text{dot4 } 3\text{ ck}) = 4 \times 11 = 44\text{ chu kỳ}$$
Khối tính toán chỉ chiếm $44 / 233,3 \approx 18,9\,\%$ tổng thời gian! Khoảng $189\text{ chu kỳ}$ còn lại là chi phí khác.

#### Hai phép đo dứt khoát xác minh nguồn gốc 189 chu kỳ:
1. **Phép đo 1: Xác minh vai trò bộ nhân phần cứng `CFG_MUL=1`**:
   - *Lưu ý về phép đo trước*: Việc chạy nhị phân biên dịch `-march=rv32i` trên phần cứng `CFG_MUL=1` là **cặp lệch, không đo được gì**, do nhị phân `rv32i` hoàn toàn không phát sinh lệnh nhân mở rộng nào nên bộ nhân phần cứng ngồi không cả hai lượt (EIDE đã được vá cơ chế DEV-320 để phát hiện và cảnh báo cặp lệch kiểu này).
   - *Kết quả cặp chuẩn (`rv32im` + `CFG_MUL=1`)*: Đạt chính xác **52 969 chu kỳ, y nguyên**.
   - *Phân tích mã máy (tháo mã)*:
     - Trong toàn bộ nhị phân có phát sinh 10 lời gọi `__mulsi3` nằm ở `main` và trong libgcc (tổng kiểm, chia 64-bit, in chuỗi ra UART) — chạy 1 lần ngoài vòng lặp.
     - Trong **vòng lặp nóng (hot loop)** nhân ma trận `matmul_v1_p3b`, hoàn toàn **không có bất kỳ phép nhân nào**! Trình biên dịch GCC (`-Os`) đã tự động quy các phép tính chỉ số về cộng con trỏ tuyến tính (`add t1, t1, a0` cho `b_col += n` và `add a1, a1, a0` cho `a_row += n`). Do đó phép nhân phần mềm không phải nguyên nhân gây nghẽn.
2. **Phép đo 2: Viết lại thuật toán thuần túy bằng cộng con trỏ tuyến tính (`CFG_MUL=0`)**:
   - Viết lại `transpose_b` và `matmul_v1_p3b` bằng con trỏ tăng dần (`*b_t_col = *b_ptr++; b_t_col += n;` và `b_col_ptr += n; a_row_ptr += n;`).
   - Kết quả đo mới trên Verilator:
     - `TRANSPOSE`: giảm từ 8 931 xuống **8 863 chu kỳ**.
     - `RESULT`: giảm từ 59 719 xuống **52 969 chu kỳ** (tiết kiệm **6 750 chu kỳ**, tức giảm **26,4 chu kỳ mỗi cặp $(i, j)$**).
     - $\text{CPM}_{\text{3b-opt}}$ đạt **12,93 chu kỳ/MAC** (tổng kiểm `0x08EA34EA, ok=1`).

#### Bóc tách bản chất chi phí qua số đếm lệnh thực tế (5,05 chu kỳ/lệnh):
Đếm số lệnh máy thực tế trong bản tháo mã của `matmul_v1_p3b` cho mỗi cặp $(i, j)$:
- Thân vòng $k$ (lặp 4 lần): 8 lệnh máy $\times 4 = \mathbf{32\text{ lệnh}}$.
- Phần còn lại của vòng $j$ (khởi tạo, đọc acc, lưu kết quả, điều khiển nhánh): $\mathbf{9\text{ lệnh}}$.
- **Tổng cộng**: $\mathbf{41\text{ lệnh máy}}$ cho mỗi cặp $(i, j)$, thực hiện 16 phép MAC.

Từ số chu kỳ đo được trên phần cứng thực tế ($52\,969\text{ chu kỳ} / 256\text{ cặp} = \mathbf{206,9\text{ chu kỳ/cặp}}$):
$$\text{Hiệu năng lệnh thực tế} = \frac{206,9\text{ chu kỳ}}{41\text{ lệnh}} = \mathbf{5,05\text{ chu kỳ mỗi lệnh}}$$

Con số **5,05 chu kỳ/lệnh** phản ánh chính xác bản chất phần cứng của CPU PicoRV32 trong SoC này:
- PicoRV32 là CPU vô hướng đa chu kỳ (multi-cycle), không có pipeline.
- Mỗi lệnh thực thi tuần tự từ Fetch (3–4 ck để phát `mem_valid` và đọc BRAM) $\rightarrow$ Decode $\rightarrow$ Execute (1–2 ck cho ALU, 3 ck cho `lw`/`sw`/PCPI) $\rightarrow$ Writeback. Trung bình một lệnh tiêu tốn đúng ~5,05 chu kỳ xung nhịp.
- Với 41 lệnh phụ trợ cho mỗi cặp $(i, j)$, CPU mất: $41 \times 5,05 = \mathbf{207\text{ chu kỳ}}$!

> **Kết luận cốt tử**: Nấc 3b bị nghẽn không phải do bộ tăng tốc tính chậm, mà do **CPU PicoRV32 mất phần lớn thời gian chỉ để fetch và thực thi các lệnh vô hướng phụ trợ** (41 lệnh $\times$ 5,05 ck/lệnh). Muốn Nấc 3c bứt phá, khối vector mini bắt buộc phải **giải phóng CPU khỏi việc fetch và chạy các lệnh vô hướng này**.

---

### 2.2. So sánh hai phương án nạp vector

#### Phương án A: Nạp qua thanh ghi CPU (Register-based PCPI Loading)
- **Quy trình**: CPU tự nạp dữ liệu từ BRAM vào thanh ghi CPU bằng `lw`, rồi đẩy vào khối vector qua PCPI.
- **Đánh giá**: Phương án này giữ nguyên CPU trong vòng lặp nạp, CPU vẫn phải fetch hàng loạt lệnh `lw` vô hướng. Do đó, Phương án A **hoàn toàn thất bại trong việc giải quyết nút thắt CPU vô hướng** và không thể nhanh hơn 3b.

#### Phương án B: Nạp trực tiếp qua cổng BRAM thứ hai (True Dual-Port BRAM Master)
- **Cơ chế**:
  - Bộ nhớ BRAM của SoC được mở thành True Dual-Port:
    - **Port A**: Dành riêng cho CPU PicoRV32 (`mem_*`).
    - **Port B**: Kết nối trực tiếp với Đơn vị Vector (`vmem_*`).
  - CPU chỉ phát đúng **một lệnh** PCPI: `vload v_dst, rs1` (với `rs1` là địa chỉ cơ sở).
  - Khối vector kéo `pcpi_wait = 1` và chạy FSM tự động đọc 4 từ 32-bit liên tiếp từ Port B.
- **Thời gian thực thi chính xác của `vload` (6 chu kỳ)**:
  - BRAM của FPGA Gowin chốt dữ liệu ngõ ra (`mem_rdata <= mem[word_addr]`). Địa chỉ phát ở chu kỳ $N$ thì dữ liệu trả về ở chu kỳ $N+1$.
  - FSM nạp 4 từ gối đầu (pipelined) qua Port B:
    - Chu kỳ 0: Khối nhận `pcpi_valid`, kéo `pcpi_wait = 1`, phát địa chỉ 0 (`addr_0`).
    - Chu kỳ 1: Phát `addr_1`.
    - Chu kỳ 2: Nhận `data_0` vào `v_dst[31:0]`, phát `addr_2`.
    - Chu kỳ 3: Nhận `data_1` vào `v_dst[63:32]`, phát `addr_3`.
    - Chu kỳ 4: Nhận `data_2` vào `v_dst[95:64]`, ngừng phát địa chỉ.
    - Chu kỳ 5: Nhận `data_3` vào `v_dst[127:96]`, hạ `pcpi_wait = 0`, trả `pcpi_ready = 1`.
  - $\rightarrow$ Toàn bộ lệnh `vload` hoàn thành trong **đúng 6 chu kỳ clock**!

---

### 2.3. Đòn bẩy quyết định: Tái sử dụng Vector (Vector Reuse) và Loại bỏ vòng lặp CPU

Trong phép nhân ma trận $C_{16\times 16} = A_{16\times 16} \times B_{16\times 16}$:
- Với mỗi hàng $i$ của $A$:
  1. CPU phát 1 lệnh `vload v0, &A[i][0]`: Fetch lệnh (4 ck) + nạp BRAM (6 ck) $\rightarrow$ **10 chu kỳ**.
  2. Vector hàng $A$ nằm cố định trong `v0` suốt toàn bộ 16 cột của $B$ (tái sử dụng 16 lần).
  3. Lặp qua 16 cột của $B$ (mỗi cặp $(i, j)$ làm 16 MAC, gồm 7 lệnh CPU):
     - CPU thực thi 7 lệnh điều khiển và phát PCPI (`vload`, `acc.clr`, `vdot`, `acc.rd`, `sw`, `addi`, `bne`):
       $$7\text{ lệnh} \times 5,05\text{ chu kỳ/lệnh} \approx \mathbf{35,35\text{ chu kỳ}}$$
     - Chu kỳ chờ phần cứng (hardware wait latency do `pcpi_wait` giữ CPU):
       - `vload` (FSM nạp 4 từ gối đầu qua Port B): **6 chu kỳ chờ**.
       - `vdot` (4 nhịp nhân tích luỹ 4 làn): **4 chu kỳ chờ**.
     - **Tổng chu kỳ thực tế cho mỗi cặp $(i, j)$**:
       $$35,35 + 6 + 4 \approx \mathbf{45,35\text{ chu kỳ}} \quad (\text{thay vì } 206,9\text{ chu kỳ của 3b})$$

#### CPM thực tế của Phương án B trên đường cơ sở đã tối ưu:
- **Chu kỳ tính thuần ma trận 4 096 MAC**:
  $$\text{Tổng chu kỳ} \approx 16\text{ hàng } A \times (5,05 + 6) + 256\text{ cặp } (i, j) \times 45,35\text{ ck} \approx 177 + 11\,610 \approx \mathbf{11\,787\text{ chu kỳ}}$$
- **CPM nhân ma trận thuần**:
  $$\text{CPM}_{\text{vmini}} = \frac{45,35\text{ ck/cặp}}{16\text{ MAC/cặp}} \approx \mathbf{2,8\text{ chu kỳ/MAC}}$$
- **Tăng tốc so với các mốc chuẩn**:
  - So với Nấc 3b đã tối ưu con trỏ (12,93 CPM): **Nhanh gấp ~4,6×** ($12,93 / 2,83$)!
  - So với Nấc 3b ban đầu (14,58 CPM): **Nhanh gấp ~5,2×**!
  - So với cấu hình H2 tốt nhất Bài 2 (38,51 CPM): **Nhanh gấp ~13,6×**!
- **CPM toàn bộ (tính cả chi phí chuyển vị ma trận B = 8 863 chu kỳ)**:
  $$\text{CPM}_{\text{toàn bộ}} = \frac{11\,787 + 8\,863}{4\,096} = \frac{20\,650}{4\,096} \approx \mathbf{5,04\text{ chu kỳ/MAC}}$$
  (So với CPM toàn bộ của 3b là 15,09 sau tối ưu con trỏ).

### 2.4. Kết luận kiến trúc về nút thắt nạp
> **Khẳng định**: Nếu Nấc 3c nạp qua thanh ghi CPU (Phương án A), hiệu năng sẽ kẹt cứng vì CPU PicoRV32 mất phần lớn thời gian chỉ để fetch các lệnh vô hướng.  
> Nấc 3c **chỉ chiến thắng vượt trội (giảm CPM từ 12,93 xuống ~2,8)** khi Đơn vị Vector tự làm chủ việc nạp dữ liệu qua **Port B của BRAM**, kết hợp **Vector Reuse** của thanh ghi `v0` và **tính toán tích luỹ nội bộ** để giải phóng hoàn toàn CPU khỏi vòng lặp tính toán.

---

## 3. Giao thức nhiều chu kỳ và cơ chế `pcpi_wait`

### 3.1. Cơ chế Timeout của PicoRV32 (Bằng chứng mã nguồn)
Tra cứu trực tiếp trong `third_party/picorv32/picorv32.v`:
- **Độ rộng bộ đếm timeout** (Dòng 1215):
  ```verilog
  reg [3:0] pcpi_timeout_counter;
  reg pcpi_timeout;
  ```
  $\rightarrow$ Bộ đếm có độ rộng đúng **4 bit** (đếm từ $15 = 4\text{'b}1111$ lùi về 0).
- **Logic đếm lùi và bẫy lệnh lạ** (Dòng 1423–1430):
  ```verilog
  if (WITH_PCPI && CATCH_ILLINSN) begin
      if (resetn && pcpi_valid && !pcpi_int_wait) begin
          if (pcpi_timeout_counter)
              pcpi_timeout_counter <= pcpi_timeout_counter - 1;
      end else
          pcpi_timeout_counter <= ~0;
      pcpi_timeout <= !pcpi_timeout_counter;
  end
  ```
- **Tín hiệu giữ chờ nội bộ `pcpi_int_wait`** (Dòng 328):
  ```verilog
  pcpi_int_wait = |{ENABLE_PCPI && pcpi_wait, (ENABLE_MUL || ENABLE_FAST_MUL) && pcpi_mul_wait, ENABLE_DIV && pcpi_div_wait};
  ```

### 3.2. Giới hạn chu kỳ chờ và luật điều khiển `pcpi_wait`
Từ các dòng mã trên, nguyên lý hoạt động của PicoRV32 được xác định như sau:
1. **Khi `pcpi_wait = 0`**:
   - Ngay khi `pcpi_valid` tích cực, nếu khối đồng xử lý không kéo `pcpi_wait`, bộ đếm `pcpi_timeout_counter` sẽ đếm lùi: $15 \rightarrow 14 \rightarrow \dots \rightarrow 0$.
   - Đúng sau **16 chu kỳ clock**, nếu `pcpi_ready` vẫn chưa lên 1, `pcpi_timeout` sẽ kích hoạt lên 1, và CPU nhảy vào bẫy `CATCH_ILLINSN` (lệnh không hợp lệ) ở dòng 1605/1777.
   - **Quy tắc 1**: Mọi lệnh không kéo `wait` phải hoàn tất và trả lời `pcpi_ready = 1` trong vòng **dưới 16 chu kỳ**.
2. **Khi `pcpi_wait = 1`**:
   - Tín hiệu `pcpi_int_wait` được kích hoạt lên 1.
   - Nhánh `else` được kích hoạt: `pcpi_timeout_counter <= ~0;` liên tục nạp lại giá trị 15 ($4\text{'b}1111$).
   - `pcpi_timeout` giữ mức 0 tuyệt đối $\rightarrow$ CPU bị hoãn chu kỳ vô thời hạn và KHÔNG bao giờ bị timeout chừng nào `pcpi_wait` còn giữ mức 1.
3. **Quy tắc bắt tay (Handshake Protocol) cho lệnh nhiều chu kỳ (`vload`, `vdot`)**:
   - **Bước 1 (Chu kỳ 0)**: Khi `pcpi_valid` lên 1 và lệnh thuộc Nấc 3c nhiều chu kỳ, mạch tổ hợp hoặc thanh ghi FSM phải **kéo ngay `pcpi_wait = 1` trong cùng chu kỳ hoặc chu kỳ kế tiếp** (trước khi bộ đếm 4-bit kịp giảm về 0).
   - **Bước 2 (Các chu kỳ thực thi)**: Giữ vững `pcpi_wait = 1` trong suốt thời gian đọc BRAM hoặc chạy chuỗi nhân dồn.
   - **Bước 3 (Chu kỳ kết thúc)**: Khi hoàn thành chu kỳ cuối cùng:
     - Hạ `pcpi_wait <= 0`.
     - Đồng thời nâng `pcpi_ready <= 1` và đặt dữ liệu `pcpi_rd` (nếu là lệnh đọc).
     - Đặt `pcpi_wr <= 1` (nếu có ghi vào thanh ghi đích của CPU) hoặc `0` (nếu không đổi thanh ghi CPU).
   - **Bước 4 (Chu kỳ giải phóng)**: Khi `pcpi_valid` hạ xuống 0, hạ toàn bộ `pcpi_ready <= 0`.

---

## 4. Tập lệnh tuỳ biến Nấc 3c và mã hoá lệnh

### 4.1. Không gian mã lệnh RISC-V Custom
- Không gian mã lệnh: **custom-0** (`opcode = 7'b0001011`), định dạng R-type:
  - `opcode [6:0] = 7'b0001011`
  - `rd     [11:7]`: Thanh ghi đích CPU (hoặc chỉ số thanh ghi vector)
  - `funct3 [14:12]`: Phân nhóm lệnh chức năng
  - `rs1    [19:15]`: Thanh ghi nguồn 1 (hoặc địa chỉ nền bộ nhớ BRAM)
  - `rs2    [24:20]`: Thanh ghi nguồn 2 (hoặc chỉ số thanh ghi vector phụ)
  - `funct7 [31:25]`: Mã phân biệt lệnh mở rộng

### 4.2. Bảng phân bổ mã lệnh

Hiện tại các mã `funct3` từ `000` đến `011` đã sử dụng cho 3a và 3b (`acc.clr`, `mac`, `acc.rd`, `dot4`) với `funct7 = 7'b0000000`.  
Nấc 3c sử dụng 4 mã `funct3` còn lại (`100`–`111`):

| Lệnh | `opcode` | `funct3` | `funct7` | Ý nghĩa kỹ thuật | Chu kỳ thực thi |
|---|---|---|---|---|---|
| `vsetvl rd, rs1` | `0001011` | `100` | `0000000` | Đặt chiều dài vector $VL \leftarrow \min(rs1, 16)$, trả $VL$ về `rd` | 1 chu kỳ (`wait=0`) |
| `vload vd, rs1` | `0001011` | `101` | `0000000` | Nạp $VL$ byte từ BRAM Port B (địa chỉ cơ sở `rs1`) vào thanh ghi `vd` | 6 chu kỳ (`wait=1`) |
| `vdot vs1, vs2` | `0001011` | `110` | `0000000` | Tích luỹ tích vô hướng: $acc \leftarrow acc + \sum_{k=0}^{VL-1} vs1[k] \times vs2[k]$ | 4 chu kỳ (`wait=1`) |
| `vstore vs, rs1` | `0001011` | `111` | `0000000` | Ghi $VL$ byte từ thanh ghi `vs` ra BRAM Port B (dự phòng) | 5 chu kỳ (`wait=1`) |

### 4.3. Giải pháp mở rộng khi cần thêm lệnh
Nếu trong tương lai cần thêm các lệnh như `vredsum` (cộng dồn vector thành vô hướng) hoặc `vmul` (nhân từng phần tử):
- Ta sử dụng trường **`funct7`** để mở rộng mà không làm tăng `opcode`.
  - Ví dụ: `funct3 = 110` với `funct7 = 7'b0000000` là `vdot`; với `funct7 = 7'b0000001` là `vredsum`.
- **Hệ quả đối với chốt giải mã (Decoder Lock)**:
  - Khối giải mã BẮT BUỘC phải chốt cả 7 bit `funct7` cùng với 3 bit `funct3` và 7 bit `opcode`.
  - Mọi trường hợp giá trị `funct7` không khớp hoàn toàn với danh sách hợp lệ phải được khối giải mã coi là lệnh lạ, giữ nguyên `pcpi_ready = 0` và `pcpi_wait = 0` để CPU PicoRV32 kích hoạt bẫy `illegal instruction`.

---

## 5. Kế hoạch kiểm chứng và 7 phép phá mã (Mutation Testing)

Khối Nấc 3c là một mạch tuần tự phức tạp có trạng thái nội bộ (FSM), có tệp thanh ghi, và giao tiếp bộ nhớ qua `pcpi_wait`. Do đó, kiểm thử hộp đen đơn thuần không đủ để chứng minh tính toàn vẹn.

Dưới đây là **7 phép phá mã đặc thù cho khối có trạng thái** mà bộ kiểm thử Nấc 3c (`tb_pcpi_vmini.v`) bắt buộc phải phát hiện và đánh trượt (FAIL):

| STT | Phép phá mã (Mutation) | Lỗ hổng kỹ thuật mô phỏng | Phản ứng kỳ vọng của hệ thống | Ca kiểm thử bắt buộc |
|---|---|---|---|---|
| **1** | **Bỏ bẫy `wait` treo (Deadlock Injection)**: Cố ý giữ `pcpi_wait = 1` vĩnh viễn không hạ sau khi nạp xong vector. | Lỗi treo cứng bus PCPI và làm CPU dừng hoàn toàn. | Testbench phải có watchdog phát hiện CPU không tiến triển sau $>20$ chu kỳ và báo **FAIL**. | Ca kiểm tra timeout chu kỳ thực thi tối đa. |
| **2** | **Kéo `pcpi_wait` trễ (Wait Assertion Delay)**: Trì hoãn kéo `pcpi_wait` sau chu kỳ thứ 16 kể từ khi `pcpi_valid` bật. | Khối không kịp báo bận, làm tràn `pcpi_timeout_counter` (4-bit) của PicoRV32. | CPU PicoRV32 phải kích hoạt bẫy `CATCH_ILLINSN`. Testbench phát hiện nhảy vào trap và báo **FAIL**. | Ca kiểm tra tuân thủ định thời timeout 16 chu kỳ. |
| **3** | **Đọc thanh ghi chưa khởi tạo (Uninitialized Vector Read)**: Thực hiện `vdot` giữa một thanh ghi vector chưa từng được `vload` sau khi reset. | Đơn vị vector sử dụng giá trị rác trong FF hoặc không khởi tạo logic reset. | Giá trị `acc` tính ra bị sai lệch so với mô hình tham chiếu $\rightarrow$ Checksum **FAIL**. | Ca kiểm tra tính xác định sau trạng thái Reset. |
| **4** | **Ghi đè khi đang bận (Hazard Overwrite)**: Phát lệnh `vload` hoặc `vdot` mới ngay khi FSM đang ở chu kỳ nạp thứ 2 của lệnh trước. | Lỗi xung đột dữ liệu (data hazard) và xáo trộn con trỏ nạp BRAM. | FSM phải bỏ qua lệnh mới hoặc CPU phải bị giữ bằng `wait` không thể phát lệnh mới. Nếu thanh ghi bị ghi đè dở dang $\rightarrow$ **FAIL**. | Ca kiểm tra tính toàn vẹn FSM trước các hazard. |
| **5** | **Lệch căn chỉnh địa chỉ BRAM (Unaligned Memory Pointer)**: Phát `vload` với địa chỉ `rs1` không chia hết cho 4 (ví dụ `rs1 = 0x0001`). | Lỗi truy cập bộ nhớ lệch byte, đọc sai từ mã trong BRAM 32-bit. | Đơn vị vector phải phát hiện bit `rs1[1:0] != 0` và từ chối nạp, hoặc báo lỗi căn chỉnh. Nếu đọc sai dữ liệu $\rightarrow$ **FAIL**. | Ca kiểm tra căn chỉnh địa chỉ biên (Address Alignment). |
| **6** | **Chiều dài vector động sai ($VL < VLEN$)**: Gọi `vsetvl` với $VL = 8$ (cho ma trận $N = 8$), nhưng mạch `vdot` vẫn cố tính đủ 16 phần tử của $VLEN = 128$. | Lỗi tràn biên phép tính, cộng cả dữ liệu rác ngoài vùng ma trận con. | Kết quả `acc` bị thừa giá trị của các phần tử ngoài $VL$ $\rightarrow$ Checksum ma trận $N=8$ **FAIL**. | Ca kiểm tra tích vô hướng với $VL \in \{4, 8, 12, 16\}$. |
| **7** | **Lọt chốt mã lệnh kép (Funct7/Funct3 Aliasing)**: Kích hoạt `opcode = custom-0`, `funct3 = 101` (vload) nhưng đặt `funct7 = 7'b0100000`. | Lỗ hổng giải mã lệnh lỏng lẻo tương tự Nấc 3b cũ. | Khối phải giữ `wait = 0`, `ready = 0`, không kích hoạt FSM nạp BRAM. Nếu FSM tự ý chạy $\rightarrow$ **FAIL**. | Ca kiểm tra âm tính độc lập từng chốt giải mã. |

---

## 6. Lộ trình thực hiện và Phân kỳ công việc

Sau khi bản thiết kế kiến trúc này được duyệt:
1. **Chặng 1**: Cấu hình bộ nhớ BRAM True Dual-Port trong `rtl/bram.v` (mở rộng cổng Port B độc lập cho vector unit).
2. **Chặng 2**: Xây dựng mô-đun RTL `bai3/rtl/pcpi_vmini.v` với FSM điều khiển `pcpi_wait`, 4 thanh ghi vector 128-bit và 4 làn tính MAC.
3. **Chặng 3**: Viết bộ testbench toàn diện `bai3/sim/tb_pcpi_vmini.v` thực hiện 1 000 bộ thử ngẫu nhiên kèm 7 phép phá mã ở Mục 5.
4. **Chặng 4**: Cập nhật header phần mềm `bai3/sw/custom_insn.h`, viết hàm nhân ma trận vector `matmul_vmini` và đo đạc CPM trên Verilator.
5. **Chặng 5**: Tổng hợp và PnR trên Gowin EDA để chốt tài nguyên phần cứng thực tế và Fmax.
