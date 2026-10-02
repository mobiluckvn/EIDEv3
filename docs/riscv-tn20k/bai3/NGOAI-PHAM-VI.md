# Bài 3 — ngoài phạm vi từ 02/10/2026

Thư mục này **không còn là việc phải làm**. Anh Công đưa Bài 3 ra khỏi đặc tả ngày 02/10/2026.
Đặc tả nay gồm hai bài: Bài 1 (SoC in "Hello" qua UART) và Bài 2 (nhân ma trận, đo số chu kỳ).

Giữ lại vì ba lý do, không phải vì tiếc công: đây là **số đo thật** và xoá đi thì không dựng
lại được; nó trả lời được một câu mà hai bài còn lại không trả lời; và nấc cuối để lại một
kết quả âm có giá trị hơn phần lớn kết quả dương.

---

## Đã đo được gì

Mọi con số dưới đây đều kèm tổng kiểm trùng đáp án do `tools/gen_data.py` tính độc lập bằng
Python (`--n 16 --dtype I8 --seed 2026` → `0x08EA34EA`). Nên chúng nói về **phép tính đúng**,
không chỉ về tốc độ.

| Cấu hình | chu kỳ mỗi phép nhân-cộng | so với phần mềm thuần |
|---|---|---|
| H0 · phần mềm thuần, không bộ nhân | 601,19 | 1× |
| H1 · bộ nhân tuần tự | 72,51 | 8,3× |
| H2 · bộ nhân nhanh dùng DSP | 38,51 | 15,6× |
| P3a · lệnh `mac` vô hướng | 54,03 | 11,1× |
| P3b · lệnh `dot4` (4 × int8 mỗi lệnh) | 14,58 | 41× |
| P3b · sau tối ưu con trỏ, thuần phần mềm | 12,93 | 46× |
| **P3c · đơn vị vector mini** | **3,84** | **157×** |

Mốc đề bài cho 3b là ≤ 19,25 (một nửa cpm của H2). Đạt 14,58. Tính cả chi phí chuyển vị ma
trận B — việc mà H2 không phải làm — thì 16,76, **vẫn dưới mốc**.

Giá tài nguyên của 3b, đo bằng `hdl.synth` và `hdl.pnr`:

| | Bài 1 | nấc 3b | thêm |
|---|---|---|---|
| LUT4 | 2 180 | 2 796 | +616 |
| DSP | 0 | 5 | +5 |
| Fmax | 134,93 MHz | 113,49 MHz | vẫn thừa 4,2 lần so với xung 27 MHz |

Năm khối DSP, không phải bốn: bốn MULT9X9 cho `dot4`, và một MULT36X36 cho lệnh `mac` của
nấc 3a vẫn còn trong mô-đun.

---

## Vì sao nấc 3c không về đích

Nấc 3c **đúng về chức năng mà không vừa chip**. Hai điều ấy khác nhau, và chúng được trả lời
bởi hai công cụ khác nhau.

Phần mềm chạy đúng từ đầu đến cuối: `cpm=3.84`, `chk=0x08EA34EA`, `ok=1`. Bộ kiểm đơn vị bắt
**7 trên 7** phép phá mã, kể cả hai lỗi giao thức mà chỉ đồng hồ canh bắt được. Mô phỏng
không hề báo gì bất thường.

Nhưng tổng hợp lên chip không về đích. Biểu hiện đầu tiên chỉ là **chậm**: 5 giây thành hơn 30
phút, rồi chạm hạn và trượt. Tôi đoán sai hai lần — lần đầu nghĩ do bộ dồn kênh đọc tệp thanh
ghi vector (chốt toán hạng vào `opa`/`opb` rồi vẫn chậm), lần sau nghĩ do phép làm phẳng toàn
mạch. Nguyên nhân thật chỉ lộ ra khi **tổng hợp riêng mô-đun bộ nhớ**:

```
Module bram: replaced 819152 cells with 5635760 new cells
  262144  DFFE          ◀── cả 32 KB thành flip-flop
  786384  $_MUX_
Extracted 2474345 AND gates ... 262516 inputs
```

Đơn vị vector cần một cổng thứ hai vào bộ nhớ. Thêm cổng ấy làm **suy luận khối nhớ cứng
(BSRAM) đứt hoàn toàn**: cả 32 KB — 262 144 bit — bị dựng thành thanh ghi, trên một chip
GW2AR-18 chỉ có 15 552 flip-flop. **Vượt 17 lần.** Thiết kế không bao giờ nạp được, và
`yosys-abc` cày 30 phút để tối ưu một mạng 2,47 triệu cổng cho một mạch vô vọng.

Nguyên nhân nằm ở **cấu trúc**, không ở số cổng: bản hai cổng đặt cả hai cổng trong cùng một
khối `always @(posedge clk)`, mỗi cổng vừa đọc vừa ghi với cho phép ghi theo từng byte, trên
cùng một mảng. Gowin BSRAM không có nguyên thuỷ nào như thế. Bản một cổng suy luận ra
32 × RAM16SDP4 + 16 × SP = 16 khối BSRAM, và tổng hợp cả SoC xong trong 4,6 giây.

Đáng chú ý là chính đặc tả Bài 3 đã đặt đúng câu hỏi này — mục kiến trúc, điểm (3): *"luồng
công cụ: toolchain mở hay Gowin EDA, theo kết quả kiểm tra BRAM hai cổng ở G1"*. Câu hỏi đặt
đúng mà chưa ai trả lời trước khi viết RTL. **Nếu sau này quay lại, phép kiểm BRAM hai cổng
phải là việc đầu tiên — trước cả bản thiết kế kiến trúc.** Và phải kiểm bằng cách đọc bảng
đếm ô, không phải bằng việc mô phỏng chạy đúng.

---

## Trạng thái mã nguồn

`rtl/bram.v` và `rtl/soc_top.v` của dự án **đã trả về bản một cổng, không còn phụ thuộc
`bai3/`**, và đã chứng minh lại:

```
tổng hợp   4,6 giây    LUT4 2 211/20 736 = 10,7 %   BSRAM 16/46
đặt-đi-dây 20,0 giây   Fmax 106,01 MHz, cần 27
Bài 1      nhận đúng "Hello from PicoRV32" hai lần, PASS
Bài 2      H0 618,04 · H1 83,40 · H2 49,40 — trùng đúng đường cơ sở cũ
```

Mã của Bài 3 trong thư mục này **không còn được dựng cùng dự án**. Nó đọc được, chạy lại được
nếu nối tay, nhưng không nằm trong đường dựng nào.

---

## Tệp trong thư mục này

| | |
|---|---|
| `KET-QUA-3A.md` | nấc 3a — lệnh `mac` vô hướng, kiểm chứng luồng PCPI |
| `KET-QUA-3B.md` | nấc 3b — lệnh `dot4`, đạt mốc đề bài |
| `rtl/pcpi_mac.v` | khối nấc 3a |
| `rtl/pcpi_dot4.v` | khối nấc 3b — 4 bộ nhân 8×8 có dấu, cây cộng |
| `rtl/pcpi_vmini.v` | khối nấc 3c — 4 thanh ghi vector 128 bit, FSM nạp qua cổng B |
| `sim/tb_pcpi_dot4.v` | bộ kiểm 3b — độ nhạy 7/7 |
| `sim/tb_pcpi_vmini.v` | bộ kiểm 3c — độ nhạy 7/7, có đồng hồ canh đã chứng minh nổ được |
| `sw/` | `custom_insn.h`, `main.c`, `start.S`, `linker.ld` |
| `../docs/bai3-arch.md` | bản thiết kế kiến trúc nấc 3c, đã được duyệt ở điểm dừng bắt buộc |
| `../tai-lieu/do-nhay-dot4.py` | bản đo độ nhạy bộ kiểm 3b |
| `../tai-lieu/do-nhay-vmini.py` | bản đo độ nhạy bộ kiểm 3c |
