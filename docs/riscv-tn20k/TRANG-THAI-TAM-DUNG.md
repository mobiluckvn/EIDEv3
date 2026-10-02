# Trạng thái — hết ngày 02/10/2026

Viết để mai mở lại mà không phải dò sổ cái. Nói ba thứ: **đang ở đâu**, **làm gì tiếp**, và
**chỗ nào dễ hiểu sai**.

---

## 1 · Đề án FPGA: phần làm được mà không cần phần cứng đã XONG

Đặc tả nay gồm **hai bài** — Bài 3 ra khỏi phạm vi ngày 02/10/2026.

| | Trạng thái |
|---|---|
| **Bài 1** · SoC in "Hello" qua UART | **xong** phần mô phỏng |
| **Bài 2** · nhân ma trận, đo số chu kỳ | **xong** — 96/96 ô, mọi ô `ok=1`, đủ ba sản phẩm đề bài nêu |
| ~~Bài 3~~ · lệnh tuỳ biến và vector | ngoài phạm vi — [`bai3/NGOAI-PHAM-VI.md`](bai3/NGOAI-PHAM-VI.md) |

**Việc duy nhất còn lại của cả đề án cần kit thật**: đối chiếu số mô phỏng với số đo trên bo,
đề bài đòi chênh ≤ 1 %. Kit đã đặt mua, đang chờ về.

### Bài 2 — ba con số đáng nhớ

```
tăng tốc        602,83 → 71,09 → 37,09 cpm        (H2 nhanh hơn H0 16,25×)
tài nguyên      H0 2.352 LUT · H1 2.562 · H2 2.232    ← H2 NHANH NHẤT mà ÍT LUT NHẤT
kiểu dữ liệu    I32 so I8 ở H1/H2: tỷ lệ 1,002–1,035  ← gần như không tốn thêm gì
```

Con số giữa ngược trực giác: H2 có thêm một khối nhân mà nhỏ đi 120 ô LUT. Đã chạy lại hai lần,
lặp đúng; bảng chi tiết cho thấy H2 ít LUT1 hơn 99 ô và ít ô dồn kênh hơn. Đó là kết quả **trên
thiết kế này**, không phải quy luật chung.

Sản phẩm: [`bai2/KET-QUA.md`](bai2/KET-QUA.md) · `bai2/all.csv` · `bai2/cpm.png` ·
`tools/{gen_data,quet_bai2,plot,parse_log}.py`.

### Khi kit về thì làm gì — theo thứ tự

1. **Kiểm bo trước khi nạp.** Hai chỗ đã ghi sẵn trong
   [`bai1/DANH-GIA-NAP-BO-THAT.md`](bai1/DANH-GIA-NAP-BO-THAT.md): thêm `BANK_VCCIO=3.3` cho
   giống bản tham chiếu Sipeed, và LED tích cực thấp nên phần mềm ghi `1` để bật là đảo.
2. **Nạp Bài 1**, xem UART có ra `Hello from PicoRV32` không.
3. **Chạy lại 24 lượt của Bài 2 trên bo**, bắt bản ghi UART, rồi
   `python tools/parse_log.py <bản ghi...> --out results/board.csv`.
   `parse_log.py` viết sẵn cho đúng việc này, và đã thử trên ba bản ghi khó: thiếu dòng
   `CONFIG` thì **nói ra** chứ không điền `?`; rác lúc đồng bộ baud được đếm và báo; dòng
   `ok=0` vẫn vào CSV.
4. **So `board.csv` với `all.csv`**, chênh ≤ 1 % là đạt.

Lưu ý cặp ISA: **H0 dịch bằng `rv32i`, H1 và H2 bằng `rv32im`**. Ghép lệch thì EIDE cảnh báo
(DEV-320), nhưng biết trước đỡ một lượt.

---

## 2 · Giao diện: bảy việc anh Công nêu đã làm hết

| | Việc | Nguyên nhân thật |
|---|---|---|
| 1 | công thức LaTeX ở chat | *"chưa hề nối vào"* **sai** — đã nối. Lỗi thật: hai bảng ký hiệu lệch **41 mục**, và Swift đổi `\sum` thành `Σ` thay vì `∑` |
| 2 | dấu `**` lọt ra màn | phần lời Agent **đã đúng**; lỗi ở **lời người gõ** — đi một đường khác, cố ý để chữ trơn |
| 3 | bản chụp cắt ở 3 000 ký tự | đúng. Nay 20 000, và khi còn cắt thì ghi bản đủ ra tệp |
| 4 | cảnh báo dồn đống | đúng — 10 chỗ thêm, 1 chỗ xoá, và chỗ xoá chỉ chạy khi đổi dự án |
| 5 | bảng Markdown dựng sai | bốn lỗi. Việc duy nhất chẩn đoán trúng hoàn toàn |
| 6 | màn hình Thiết kế trắng | A5.10 cây mô-đun · A5.11 tài nguyên · A5.12 bản đồ địa chỉ · A5.13 bitstream |
| 7 | kết quả bộ kiểm chip không hiện | A8.0 — tab Mô phỏng đọc một khoá khác với khoá `hdl.sim` ghi vào |

**Bốn việc cuối cùng một hình dạng**, và nó là mẫu lặp đi lặp lại trong dự án này: *cơ chế có
sẵn, đường dẫn tới nó đứt*. Không phải thiếu tính năng — là thiếu một dòng nối.

Trước 02/10 **cả giao diện chưa từng có một ca kiểm nào**. Nay **40 ca Swift**, và 13 trong số
đó đỏ khi trả lại mã cũ.

---

## 3 · Việc còn lại, theo thứ tự đáng làm

### a. Tác tử xác minh con có hạn 10 lời gọi, quá chặt

Mục 6 của [`VIEC-CHO-LAM.md`](../md/VIEC-CHO-LAM.md). Nó cày hết hạn vào `ledger.query` rồi
trả `chua_du_du_kien` mà chưa kịp nộp báo cáo — nên lời xác minh biến mất đúng lúc cần nó nhất.

Hai chỗ sửa: nới hạn (hoặc tính riêng ngân sách *đọc bằng chứng* với ngân sách *làm việc*), và
**buộc nộp báo cáo khi còn 2 lời gọi** kèm ghi rõ phần nào chưa kiểm được. Một báo cáo thiếu có
nói rõ chỗ thiếu thì dùng được; `chua_du_du_kien` thì không dùng được gì.

### b. Agent không có công cụ chạy một tệp Python

Tìm ra trong phiên này, và nó đắt hơn vẻ ngoài. Agent viết được `gen_data.py`, `plot.py`,
`parse_log.py` — nhưng **không tự chạy được chúng**. Nên nó không kiểm được chính công cụ nó vừa
sửa, và một lần đã báo *"đã xác minh thành công"* cho một tệp đang vỡ `NameError`.

Lời báo ấy **đúng về mô phỏng** mà sai về công cụ: nó xác minh qua **sản phẩm** đã sinh ra từ
trước, không qua công cụ. Tôi cũng mắc đúng lỗi ấy — tôi cũng chỉ chạy mô phỏng.

> Sửa công cụ nào thì phải **chạy lại chính công cụ ấy**, không phải chạy thứ nó đã sinh ra lần
> trước. Và cách chắc chắn nhất là **xoá sản phẩm đi trước khi chạy**.

### c. `tool.install` để lại thẻ duyệt treo

Mỗi lần gọi lại mở một thẻ **mới**, nên một việc cài có thể để lại hàng chục thẻ — thẻ được
duyệt sang lượt sau, mà Agent thử lại trong cùng lượt.

### d. Dọn lại cấu trúc thư mục FPGA

[`DE-XUAT-CAU-TRUC-FPGA.md`](../md/DE-XUAT-CAU-TRUC-FPGA.md) việc 5. Rào cản đã hết (Bài 3 ra
khỏi phạm vi, không còn việc dở giữa chặng). Vẫn nên làm bằng **một changeset riêng không kèm
việc gì khác** — một changeset chỉ đổi đường dẫn thì đọc lại được, còn vừa đổi đường dẫn vừa
đổi mã thì không ai tách ra được nữa.

### e. Năm trong mười hai dòng bảng thông số còn trỏ vào trang tra cứu

Chưa phải tài liệu cụ thể, nên chưa coi là xong.

---

## 4 · Mười chỗ vá EIDE trong phiên này

| | |
|---|---|
| DEV-320 | mã máy và cấu hình CPU phải khớp — `build.compile` đếm lệnh **có thật**, `hdl.sim` đối chiếu |
| DEV-321 | hết hạn thì diệt **cả nhóm** tiến trình, không chỉ con trực tiếp |
| DEV-322 | bỏ Bài 3 khỏi đặc tả, và giữ lại kết quả âm |
| DEV-323 | duyệt cổng xong **phải nói ra** |
| DEV-324 | `ledger.query` cắt 220 ký tự trong im lặng |
| DEV-325 | năm việc giao diện, và mục tiêu kiểm cho Swift |
| DEV-326 | A8.0 hiện kết quả bộ kiểm HDL |
| DEV-327 | A5.10 cây mô-đun, đọc từ Verilog thật |
| DEV-328 | luật công thức giữa dòng lệch hai bên |
| DEV-329 | câu của **người** cũng phải qua bộ dựng Markdown |

Bộ kiểm: Python **1 575** · Swift **40**. Cả hai xanh.

---

## 5 · Ba điều về cách làm việc, dùng cho mọi phiên sau

**Giao một việc mỗi lượt.** Ba lượt liền Agent đọc tài liệu rồi kết lượt mà không ghi gì —
không phải hết ngân sách (hạn 220 lời gọi, nó dùng 13–17). Đề dài có bảng và sáu mục thì nó đọc
rồi dừng; **đề một câu một việc thì nó làm ngay**.

**Khi hai bên báo hai điều trái nhau, câu hỏi đầu tiên không phải "ai sai".** Agent báo lời giao
việc bị cắt; tôi tra **tệp** sổ cái thấy đủ 770 ký tự và kết luận nó kể sai — rồi ghi kết luận
ấy vào tài liệu. Nguyên nhân thật: nó đọc **qua `ledger.query`**, và công cụ ấy cắt ở 220 ký tự
trong im lặng. **Cả hai đều báo đúng về thứ mình nhìn thấy.** Câu hỏi đúng là *"hai bên có đang
xem cùng một thứ không"*.

**Tôi kiểm thứ làm việc, rồi kết luận cho việc đã được làm.** Ba lần trong cùng một ngày: khối
A8.0, khối A5.10, và chỗ chọn bộ dựng Markdown — cả ba bộ ca kiểm đều **xanh khi đường dẫn
đứt**. Hai thứ ấy cách nhau một đường dẫn, và đường dẫn là chỗ hay đứt nhất. Nay mỗi khối có
một ca đi qua đúng đường người dùng đi.

---

## 6 · Mở lại phiên

```bash
cd /Users/congvt/Documents/EIDE_v3
.venv/bin/python -m pytest -q                 # 1 575 ca
cd ui/EIDEApp && swift test                   # 40 ca
```

Phiên FPGA với Agent — xem `tools/phien_fpga.py`; nhớ đặt
`EIDE_TRAN_GIAY_LUOT=3600 EIDE_TRAN_LOI_GOI_LUOT=220`, vì mặc định 300 giây / 40 lời gọi là
quá chặt cho việc HDL.

Nhật ký phiên: [`nhat-ky-phien/NHAT-KY.md`](nhat-ky-phien/NHAT-KY.md) · ảnh từng bước ở
`nhat-ky-phien/anh/`.
