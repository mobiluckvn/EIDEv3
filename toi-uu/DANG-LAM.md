# ĐANG LÀM — chiến dịch tối ưu tác tử

> Tệp này trả lời đúng một câu: **mở phiên mới thì làm gì tiếp.**
> Đọc nó TRƯỚC khi mở `KE-HOACH-SUA-VA-KIEM-THU.md`.

## Trạng thái — 10/10/2026

| | |
|---|---|
| Việc xong | **34/106** (DEV-330 → DEV-363) |
| **P0** | **30/30 — HẾT ưu tiên cao nhất** |
| Giai đoạn 1 | 32/32 — đóng |
| P1 | 3/54 · P2 1/20 · P3 0/2 |
| Bộ kiểm | **2 160 xanh**, 1 skip, 0 đỏ |
| Công cụ | **135** (125 thấy mặc định · 73 `core` · 10 sau cờ) |
| Cờ | **14**, cả 14 TẮT |
| Phụ thuộc tuỳ chọn | `pdfplumber>=0.11`, nhóm `[pdf]` — anh Công duyệt cài 10/10/2026 |
| `kiem_tai_lieu` | 0 chỗ LỆCH CHẮC CHẮN |
| Việc dở | **không có** — việc #34 đã cất trọn |

## Làm gì tiếp — chỗ này phải HỎI, không tự đi

**Hết P0.** Còn 72 việc, **tất cả P1 trở xuống**: 51 P1 · 19 P2 · 2 P3. Anh Công đặt mốc báo
cáo ở *"hoàn thiện hết các nội dung ưu tiên cao nhất"* — mốc ấy đã tới, nên đừng mở P1 mà
chưa hỏi.

Nếu được mở tiếp, ba việc đáng làm trước và lý do:

* **#85 M5-21 — bộ eval vàng** (P1 · M). Nó là tiêu chí **CHƯA ĐẠT** của #34, và chính kế
  hoạch khuyên làm sớm: *"không có thước đo thì không biết một việc có làm hệ thống khá hơn"*.
  Nó cũng là thứ duy nhất nói được vế **recall** của cờ `pdf_bang`.
* **#35 M1-05 — ngân sách và lượt buộc nộp cho tác tử con** (P1 · M). Tác tử con hiện không
  có trần nào.
* **#39 M1-20 — bảng chỉ số từ sổ cái** (P1 · M). Kế hoạch cũng khuyên làm sớm.

**Và một việc KHÔNG phải mã:** repo chưa có **một datasheet PDF nào**. 21 tệp PDF thật đều là
bài báo và báo cáo, nên vế recall của #34 không đo được ở đây. Một datasheet thật (ATmega328P
hoặc STM32F469) đặt vào `tests/du-lieu-chung/` sẽ mở được phép đo ấy — nhưng tải tệp về là
một việc đi ra ngoài, nên phải hỏi anh Công trước.

## Cách làm — đọc lại mỗi lần, đừng làm theo thói quen

§3.1 của kế hoạch, mười bước. Bốn chỗ đã trả giá nhiều lần:

1. **Nhánh trước, không sửa trên `main`.** `git switch -c toi-uu/<Mx-yy>`.
2. **Viết ca kiểm TRƯỚC**, và xác nhận nó ĐỎ **vì đúng lý do** — không phải đỏ vì `ImportError`.
3. **Xoá `__pycache__` trước MỖI lần phá.** Một phép phá dài bằng mã gốc giữ nguyên số byte,
   nên `.pyc` cũ còn hiệu lực và phép đo chạy mã **khác** mã trong tệp.
4. **Tập phép phá dựng từ `git diff`, không từ ký ức** — và **đọc lại sau mỗi lần sửa mã**.
   Lưu ý kỹ thuật: tệp mới chưa vào chỉ mục thì **không hiện trong `git diff`** — `git add -N`
   trước khi đọc diff, không thì cả một module mới sẽ không có phép phá nào.
   Khuôn: `toi-uu/pha_lai-khuon.py`.

## Bài học mạnh nhất tới giờ — và nó vừa lặp lần thứ TÁM

Tám việc liên tiếp (M5-03 · M5-07 · M5-13 · M5-17 · M5-01 · M2-09 · M4-13 · **M5-04**) có chỗ
LỌT nằm trong **tập ca kiểm**, không nằm trong mã sản phẩm. Hình dạng của nó:

* hai vế của một phép chia **tình cờ bằng nhau** trong bản mẫu (4 thanh ghi / 4 trường);
* một tập chỉ có **một** phần tử, nên phép gộp nhóm hỏng vẫn ra kết quả đúng;
* hình dạng dữ liệu **đã đúng sẵn**, nên phép sửa hình dạng không đổi gì;
* ca kiểm **không chạm tới dòng** nó tưởng đang canh.

Việc #34 cho dạng mạnh nhất của nó: **hai BẢNG SỐ trùng nhau ở mọi khoá**. `vdd.abs_max` bằng
`vdd.max`; `PHAM_VI_GOC["ta"]` bằng `PHAM_VI_HOP_LY["ta.max"]`; `PHAM_VI_GOC` phủ đúng những
gốc mà `PHAM_VI_HOP_LY` phủ. Trên dữ liệu trùng như thế, ba phép phá tháo **ba luật thứ tự
khác nhau** đều cho **cùng một con số** — ba luật ấy đang được một sự tình cờ bảo vệ, không
được ca kiểm nào bảo vệ. Chữa bằng một ca dựng **bảng riêng** để ba luật phân biệt được nhau.

Cách chữa, dùng được ngay:

* bản mẫu cho một phép **chia** hay một phép **cắt** phải có ít nhất **hai phần tử KHÁC nhau**;
* **bảng tra** thì phải dựng bảng riêng trong ca kiểm, đừng dựa vào bảng thật — bảng thật hay
  trùng nhau, và trùng nhau là cách một luật sống sót mà không ai canh;
* đặt một `assert` **trước** chỗ phá/monkeypatch, chứng minh ca kiểm **tới được** dòng ấy;
* cẩn thận với `except Exception` trong mã sản phẩm: nó **nuốt luôn `AssertionError`** của ca
  kiểm, nên một ca dựng trên "hàm này nổ thì tôi biết" sẽ xanh mà không đo gì (#34, ca cờ TẮT);
* hai lớp phòng độc lập thì phải có một phép phá **GỘP** — tháo riêng từng lớp không nói gì;
* một lần **TREO** phải biến thành ĐỎ, không được làm script phá chết theo.

## Hình dạng thứ hai: kế hoạch tự nó sai

Việc #34 làm hai lần nữa: (1) kế hoạch coi `_tu_hang_bang` đã chạy được trên bảng datasheet —
đo ra là **không khớp nổi một hàng nào**; (2) kế hoạch chỉ nói `abs_max`, bỏ sót cột Min của
bảng ấy. Trước đó: #27 (luật dò ISR bắt 0 ca), M4-11 (sai hai lần), M5-05/M5-07 (ca kiểm xanh
vì lý do sai). Nên **không nhận luật của kế hoạch làm chân lý** — dựng ca tái hiện bằng công
cụ thật trước, rồi mới viết mã theo cái đo được.

## Hình dạng thứ ba: con số tự nhớ

Việc #34: tôi đặt biên dưới của `i2c.pullup` ở **10 Ω** theo thói quen *"pull-up I2C thường
1–10 kΩ"*. Một ca kiểm **có từ trước** bác ngay: ô bảng ghi `4R7` — **4,7 Ω**, một giá trị
điện trở có thật. Phanh độ lớn chỉ được chặn thứ **không thể**, không chặn thứ hiếm. Đây đúng
là lỗi N1 nói tới, và nó xảy ra ở lượt thứ ba của chiến dịch này.

## Số đo của chính đợt này, để lần sau không phải đo lại

* **"Phá lại thì đỏ" lượt đầu, mười một việc gần nhất:** 7/9 · 18/20 · 17/24 · 22/27 · 15/20 ·
  7/13 · 15/22 · 18/22 · 34/36 · 20/29 · **17/29**. Lượt chốt: tất cả 100 %.
* **Công cụ đã dùng thật: 118/135** — đo 10/10/2026 trên **77 tệp sổ cái, 201 774 bản ghi**.
  Con số cũ *115/134* sai vì **phép lọc**: `glob('**/ledger*.jsonl')` không vào thư mục ẩn, nên
  nó thấy **6 trên 73** sổ cái. Quét bằng `os.walk`.
* **Cờ `pdf_bang` trên 21 PDF thật (293 trang):** hàng bảng 0 → **109** · Fact **18 → 18** ·
  **0/109** nhận bừa là bảng thông số · thời gian nạp **×4,3–4,7**.
