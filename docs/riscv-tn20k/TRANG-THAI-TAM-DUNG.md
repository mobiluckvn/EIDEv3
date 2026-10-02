# Trạng thái tạm dừng — 02/10/2026

Anh Công dừng phiên để tối làm tiếp. Bản này ghi **đang ở đâu, làm gì tiếp, và chỗ nào dễ
hiểu sai** — viết để đọc lại sau vài giờ mà không phải dò lại sổ cái.

---

## 1 · Phạm vi đã đổi

Đề án nay gồm **hai bài**, Bài 3 đã ra khỏi yêu cầu (02/10/2026):

| | |
|---|---|
| **Bài 1** · SoC in "Hello" qua UART | mô phỏng **xong** |
| **Bài 2** · nhân ma trận, đo số chu kỳ | **12/96 ô**, đang làm |
| ~~Bài 3~~ | ngoài phạm vi — [`bai3/NGOAI-PHAM-VI.md`](bai3/NGOAI-PHAM-VI.md) |

Kit **đã đặt mua, đang chờ về**. Mọi con số hiện có là số mô phỏng.

---

## 2 · Bài 2 đang ở đâu — 12 trên 96 ô

Đề bài đòi 96 ô: **4 giá trị N** (4, 8, 16, 32) × **2 kiểu** (I8, I32) × **4 cách viết**
(V0–V3) × **3 cấu hình CPU** (H0, H1, H2).

Một lượt mô phỏng cho **4 ô** (phần mềm chạy cả bốn cách viết rồi in bốn dòng `RESULT`), nên
96 ô = **24 lượt**. Đã có 3 lượt → 12 ô.

Mười hai ô đã đo, tất cả ở N=16 I8, tổng kiểm `0x08EA34EA` khớp đáp án Python độc lập:

| | V0 i-j-k | V1 i-k-j | **V2** mở vòng ×4 | V3 chia khối |
|---|---|---|---|---|
| **H0** `rv32i`, nhân bằng phần mềm | 618,04 | 656,04 | **601,19** | 632,85 |
| **H1** `ENABLE_MUL`, nhân bằng LUT | 83,40 | 92,79 | **72,51** | 75,61 |
| **H2** `ENABLE_FAST_MUL`, nhân bằng DSP | 49,40 | 58,79 | **38,51** | 41,60 |

Mình đã **tự chạy lại cả 12 ô hôm nay** sau khi bỏ Bài 3 và trả `rtl/` về bản một cổng — ra
đúng từng con số. Nên việc bỏ Bài 3 không xê dịch gì.

Còn thiếu: **N ∈ {4, 8, 32}** và **toàn bộ kiểu I32** → 21 lượt nữa.

---

## 3 · Việc tiếp theo, theo thứ tự

### Việc 1 — mở đường quét N và kiểu dữ liệu ⬅️ ĐANG DỞ

`bai2/sw/main.c` **ghim cứng** `#include "../../data_16_I8.h"`, nên không đổi N hay kiểu từ
ngoài được. Cần:

- Đổi thành một tên cố định `#include "../../data_matrix.h"`.
- `tools/gen_data.py` sinh được đúng tệp ấy, và tệp ấy khai **cả ba** thứ: `MATRIX_N`,
  `CHECKSUM_REF`, và **`DTYPE_STR`**.
- Giữ các tệp `data_<N>_<kiểu>.h` hiện có, đừng xoá.

`DTYPE_STR` là chỗ dễ bỏ sót: hiện nó mặc định `"I8"` trong `main.c`, nên chạy I32 sẽ ghi
**sai kiểu** vào dòng `RESULT` — cùng loại lỗi với nhãn `hw` đã vá ở việc dưới.

> **Việc này đã giao ba lượt và chưa làm được lần nào**, vì thẻ cổng `G-QUAL` nổ giữa lượt và
> tác tử mất phần sau của đề bài. Nguyên nhân đã tìm ra và đã vá (DEV-323, DEV-324) — xem mục
> 5. **Lượt tới giao lại là làm được.** Nhớ khởi động lại app để nạp chỗ vá.

### Việc 2 — quét 21 lượt còn lại

Với mỗi cặp (N, kiểu) trong 8 cặp: sinh `data_matrix.h`, dịch, rồi chạy 3 cấu hình CPU.

Lưu ý thời gian: N=16 H0 mất ~10 s mô phỏng. N=32 nhiều gấp 8 lần phép tính nên ~85–120 s.
Cả đợt ước chừng **15–25 phút**.

Lưu ý ISA: **H0 phải dịch bằng `rv32i`, H1 và H2 bằng `rv32im`.** Ghép lệch thì EIDE nay tự
cảnh báo (DEV-320), nhưng biết trước thì đỡ một lượt.

Lưu ý dung lượng: N=32 với I32 là ca sát trần BRAM 32 KB. Bản phân tích năng lực kit nói
N ≤ 32 cho I32 — nên đây là ô cần nhìn kỹ, không phải ô chạy cho đủ.

### Việc 3 — `parse_log.py` → `results/all.csv`

Chưa có. Bộ đọc phải lấy nhãn `hw` từ **dòng `CONFIG`**, không phải từ dòng `RESULT` — xem
mục 4.

### Việc 4 — `plot.py`, biểu đồ cpm

Chưa có. Đề bài đòi biểu đồ so các cấu hình.

---

## 4 · Đã vá hôm nay trong dự án

**Nhãn `hw` sai ở mọi dòng `RESULT`.** Phần mềm viết cứng `hw=H2`, nên 8 trong 12 ô mang nhãn
sai mà không gì báo động. Phần mềm **không có cách nào biết đúng** — cấu hình CPU là thuộc
tính của bản dựng phần cứng, quyết định bởi `CFG_MUL`/`CFG_FAST_MUL` lúc tổng hợp.

Nay `bai2/sim/tb_bai2.v` in `CONFIG,hw=H0|H1|H2` suy từ chính macro của nó, và `main.c` in
`hw=?`. **Phía biết thì khai, phía không biết thì nói thẳng là không biết.** Đã kiểm cả ba
cấu hình ra đúng.

**`rtl/` trả về bản một cổng.** `bram.v` bỏ cổng B, `soc_top.v` bỏ phụ thuộc `bai3/`,
`ENABLE_PCPI` mặc định 0. Chứng minh lại:

```
tổng hợp   4,6 giây (từ hơn 1 800)   LUT4 2 211/20 736 = 10,7 %   BSRAM 16/46
đặt-đi-dây 20,0 giây                 Fmax 106,01 MHz, cần 27
Bài 1      nhận đúng "Hello from PicoRV32" hai lần, PASS
```

---

## 5 · Đã vá hôm nay trong EIDE — bốn chỗ

| | Chỗ vá | Vì sao |
|---|---|---|
| **DEV-320** | `build.compile` đếm lệnh mở rộng **có thật** trong mã máy; `hdl.sim` tự đối chiếu với cấu hình | Agent so hai cấu hình CPU bằng một mã máy không có lệnh nhân nào; hai lượt ra số bằng nhau và con số ấy bị đọc thành kết luận |
| **DEV-321** | hết hạn thì diệt **cả nhóm** tiến trình | một `yosys-abc` mồ côi cày 49 phút sau khi lượt của nó đã trượt, giành CPU của lượt sau |
| **DEV-323** | duyệt cổng chặn lời gọi công cụ thì **phải phát lời nhắc** | thiếu nó, mô hình thấy `E4003` *"DỪNG LẠI"* rồi ngay sau là kết quả của chính công cụ ấy |
| **DEV-324** | `ledger.query` nâng bản tóm lên 1 200 ký tự và **nói ra khi còn cắt** | cắt ở 220 ký tự trong im lặng, làm tác tử đọc lại lời giao việc chỉ thấy một phần ba |

Bộ kiểm EIDE: 1538 → **1549**, tất cả xanh.

**Chỗ đáng đọc nhất trong bốn chỗ trên không phải mã, mà là cách tìm ra DEV-324.** Tác tử báo
rằng lời giao việc bị cắt. Tôi tra **tệp** sổ cái, thấy đủ 770 ký tự, kết luận nó kể sai, và
ghi kết luận ấy vào tài liệu. Nhưng nó đọc **qua `ledger.query`**, và công cụ ấy cắt ở 220 ký
tự. Cả hai đều báo đúng về thứ mình nhìn thấy.

> Khi hai bên báo hai điều trái nhau, câu hỏi đầu tiên không phải *"ai sai"* mà là **"hai bên
> có đang xem cùng một thứ không"**.

---

## 6 · Hai điều về cách làm việc với Agent, dùng cho mọi việc sau

**Giao một việc mỗi lượt.** Ba lượt liền tác tử đọc tài liệu rồi kết lượt mà không ghi gì.
Không phải hết ngân sách — hạn 220 lời gọi, nó dùng 13–17. Đề dài có bảng và sáu mục thì nó
đọc rồi dừng; **đề một câu một việc thì nó làm ngay.** Tám lượt ngắn liên tiếp sau đó đều ra
sản phẩm.

**Một phép phá mã không giết được mã có hai nghĩa:** bộ kiểm yếu, **hoặc phép phá rỗng.** Đo
độ nhạy bộ kiểm 3c lần đầu ra 2/7; ba trong năm phép "lọt" là lỗi của chính phép phá tôi viết
— một phép không tạo ra treo thật, một phép chuỗi tìm không khớp, một phép nhắm vào chốt luôn
đúng. Sửa lại thì 7/7. Phải phân biệt trước khi kết luận, nếu không ta đi vá một bộ kiểm không
hỏng.

---

## 7 · Mở lại phiên thế nào

```
cd /Users/congvt/Documents/EIDE_v3
EIDE_TRAN_GIAY_LUOT=3600 EIDE_TRAN_LOI_GOI_LUOT=220 \
  .venv/bin/python -c "..."     # xem tools/phien_fpga.py
```

Nhật ký phiên: `docs/riscv-tn20k/nhat-ky-phien/NHAT-KY.md` (57 bước).
Ảnh màn hình từng bước: `docs/riscv-tn20k/nhat-ky-phien/anh/`.
