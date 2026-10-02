# Báo cáo kết quả Nấc 3b — Lệnh tuỳ biến `dot4` và bộ tích luỹ

## 1. Tóm tắt kết quả

Nấc 3b mở rộng giao diện đồng xử lý PCPI của PicoRV32 với lệnh tính tích vô hướng 4 phần tử 8-bit `dot4` (`custom-0`, `funct7 = 0000000`, `funct3 = 011`), kết hợp thanh ghi tích luỹ 32-bit `acc`.

Kết quả đo đạc trên ma trận kích thước N = 16, kiểu dữ liệu I8 (4 096 phép nhân-cộng):
- **CPM thuần nhân ma trận**: **14,58 chu kỳ/MAC** (59 719 chu kỳ / 4 096 MACs), nhanh hơn **2,64×** so với cấu hình H2 tốt nhất.
- **CPM tính cả chi phí chuyển vị ma trận B**: **16,76 chu kỳ/MAC** ((59 719 + 8 931) / 4 096 MACs), nhanh hơn **2,30×** so với H2.
- **Mục tiêu đề bài**: Cả hai con số (14,58 và 16,76) đều **vượt mốc yêu cầu ≤ 19,25 chu kỳ/MAC** (bằng ½ CPM của cấu hình H2 = 38,51 chu kỳ/MAC).
- **Tính đúng đắn**: Tổng kiểm `chk = 0x08EA34EA` trùng khớp 100% với lời giải tham chiếu Python (`tools/gen_data.py --n 16 --dtype I8 --seed 2026`) và trùng khớp kết quả phần cứng H2.

---

## 2. Bảng so sánh hiệu năng các cấu hình (N = 16, I8)

| Cấu hình | Mô tả kiến trúc / phần cứng | Số chu kỳ nhân (N=16) | Chi phí chuyển vị | Tổng chu kỳ | CPM thuần | CPM toàn bộ | Tăng tốc so với H2 |
|---|---|---|---|---|---|---|---|
| **H0** | CPU `rv32i` thuần (nhân phần mềm) | 2 462 485 | 0 | 2 462 485 | 601,19 | 601,19 | 0,06× (chậm 15,6×) |
| **H1** | CPU có bộ nhân phần cứng tuần tự (`ENABLE_MUL=1`) | 296 996 | 0 | 296 996 | 72,51 | 72,51 | 0,53× (chậm 1,88×) |
| **H2** | CPU có bộ nhân nhanh DSP (`ENABLE_FAST_MUL=1`) | 157 733 | 0 | 157 733 | 38,51 | 38,51 | 1,00× (mốc cơ sở) |
| **P3a** | Lệnh tuỳ biến `mac` qua PCPI (1 MAC/lệnh, 32×32) | 221 312 | 0 | 221 312 | 54,03 | 54,03 | 0,71× (chậm hơn H2) |
| **P3b** | Lệnh tuỳ biến `dot4` qua PCPI (4 MAC/lệnh, 4× 8×8) | **59 719** | **8 931** | **68 650** | **14,58** | **16,76** | **2,64× (thuần) / 2,30× (toàn bộ)** |

### Nhận xét về chi phí chuyển vị:
- Lệnh `dot4` yêu cầu các phần tử của vector cột trong ma trận B phải nằm liên tiếp trong bộ nhớ để CPU đọc ra 4 byte bằng đúng 1 lệnh nạp 32-bit (`lw`).
- Hàm chuyển vị `transpose_b` tốn 8 931 chu kỳ CPU. Khi tính toàn bộ chi phí tiền xử lý này vào bài toán, CPM đạt **16,76**, vẫn thấp hơn đáng kể so với ngưỡng trần 19,25 mà đề bài đặt ra.

---

## 3. Tiêu hao tài nguyên phần cứng và định thời

Tổng hợp và đặt - đi dây trên chip FPGA Gowin GW2AR-LV18QN88C6/I5 (Tang Nano 20K):

| Thành phần | Bài 1 (Baseline SoC) | Nấc 3b (`soc_top` + `pcpi_dot4`) | Chênh lệch |
|---|---|---|---|
| **LUT4** | 2 180 | 2 796 | +616 (+28,3 %) |
| **FF (Flip-Flop)** | 628 | 660 | +32 |
| **DSP** | 0 | **5** | +5 |
| **Fmax** | 134,93 MHz | 113,49 MHz | Đạt định thời xung 27 MHz |

### Giải trình chi tiết 5 khối DSP:
Mô-đun `pcpi_dot4.v` tích hợp đồng thời năng lực tính toán của Nấc 3a và Nấc 3b:
1. **4× MULT9X9**: Phục vụ trực tiếp cho lệnh `dot4` (thực hiện 4 phép nhân 8-bit có dấu đồng thời trong 1 chu kỳ).
2. **1× MULT36X36**: Phục vụ lệnh `mac` 32-bit của Nấc 3a (vẫn giữ lại trong mô-đun để tương thích ngược với các chương trình dùng lệnh `mac`).

---

## 4. Kiểm chứng và độ nhạy bộ kiểm (Mutation Testing)

Bộ kiểm đơn vị `bai3/sim/tb_pcpi_dot4.v` được thiết kế lại nhằm khắc phục hoàn toàn lỗ hổng giải mã (lọt lệnh sai `funct7`). 

### Các ca kiểm thử âm tính độc lập từng chốt (Single-Fault Negative Tests):
- **Chốt 1 (Opcode sai)**: opcode = `7'b0110011` (lệnh chuẩn), `funct7 = 7'b0000000`, `funct3 = 3'b011`. Khối giữ nguyên `ready = 0`, `wait = 0`, `wr = 0`.
- **Chốt 2 (Funct7 sai)**: opcode = `7'b0001011` (custom-0), `funct7 = 7'b0000001` và `7'b0100000`, `funct3 = 3'b011`. Khối không phản hồi (`ready = 0`).
- **Chốt 3 (Funct3 không hỗ trợ)**: opcode = `7'b0001011`, `funct7 = 7'b0000000`, `funct3` thử lần lượt `100`, `101`, `110`, `111`. Khối im lặng.
- **Kiểm tra tính toàn vẹn của thanh ghi `acc`**: Sau toàn bộ các xung phát lệnh âm tính, giá trị thanh ghi `acc` được đối chiếu và xác nhận không bị xáo trộn.

### Kết quả thử nghiệm 7 phép phá mã (Fault Injection):

| STT | Phép phá mã (Mutation) | Kỳ vọng | Kết quả bộ kiểm | Trạng thái |
|---|---|---|---|---|
| 1 | Bỏ `signed` ở toán hạng A (`wire [7:0] a0..a3`) | Bắt sai lệch phép nhân số âm | **FAIL** (27 lỗi mismatch) | **ĐẠT (Bắt)** |
| 2 | Bỏ mở rộng dấu ở cây cộng (`zero-extend` thay vì `sign-extend`) | Bắt sai lệch tràn/dấu cộng dồn | **FAIL** (27 lỗi mismatch) | **ĐẠT (Bắt)** |
| 3 | Lệch làn nhân (`a0 * b1` thay vì `a0 * b0`) | Bắt lỗi ghép sai làn vector | **FAIL** (25 lỗi mismatch) | **ĐẠT (Bắt)** |
| 4 | Mất cộng dồn tích luỹ (`acc <= dot4_sum`) | Bắt lỗi không lưu vết `acc` | **FAIL** (25 lỗi mismatch) | **ĐẠT (Bắt)** |
| 5 | **Bỏ chốt `funct7`** (lỗ hổng cũ) | Bắt kích hoạt nhầm lệnh lạ | **FAIL** (3 lỗi: ready sai và làm bẩn acc) | **ĐẠT (Bắt)** |
| 6 | Đổi `funct3` của dot4 sang `3'b100` | Bắt lỗi giải mã mã hàm | **FAIL** (1 237 lỗi ready) | **ĐẠT (Bắt)** |
| 7 | Mất một làn tính toán (`prod3 = 0`) | Bắt thiếu hụt phần tử vector | **FAIL** (30 lỗi mismatch) | **ĐẠT (Bắt)** |

**Độ nhạy bộ kiểm sau khi vá**: **7 / 7 phép phá đều bị phát hiện ngay lập tức (100 %)**.
