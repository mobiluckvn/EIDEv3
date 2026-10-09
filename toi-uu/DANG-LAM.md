# ĐANG LÀM — chiến dịch tối ưu tác tử

> Tệp này trả lời đúng một câu: **mở phiên mới thì làm gì tiếp.**
> Đọc nó TRƯỚC khi mở `KE-HOACH-SUA-VA-KIEM-THU.md`.

## Trạng thái — 10/10/2026

| | |
|---|---|
| Việc xong | **33/106** (DEV-330 → DEV-362) |
| **Giai đoạn 1** | **32/32 — ĐÓNG** |
| P0 | **29/30** · còn đúng **#34 M5-04** |
| P1 | 2/54 · P2 1/20 · P3 0/2 |
| Bộ kiểm | **2 125 xanh**, 1 skip, 0 đỏ |
| Công cụ | **135** (125 thấy mặc định · 73 `core` · 10 sau cờ) |
| Cờ | **13**, cả 13 TẮT |
| `kiem_tai_lieu` | 0 chỗ LỆCH CHẮC CHẮN |
| `main` | gộp xong `toi-uu/M4-13`, đã push |
| Việc dở | **không có** — việc #27 đã cất trọn, cây làm việc sạch |

## Làm gì tiếp

**#34 M5-04 — trích bảng có cấu trúc từ PDF datasheet.** P0 · L, và là **việc P0 cuối cùng**
trong cả 106 việc.

**Cần hỏi anh Công trước khi bắt đầu:** nó đòi một phụ thuộc mới (`pdfplumber` hoặc tương
đương), và N-10 của chính dự án bắt phải hỏi chủ sản phẩm trước khi cài thêm phụ thuộc. Đừng
tự cài.

Sau #34 thì hết P0. Mọi việc còn lại là **P1 trở xuống** (52 · 19 · 2), và anh Công chưa yêu
cầu mở chúng — nên đó là chỗ phải **hỏi** chứ không phải chỗ tự đi tiếp.

## Cách làm — đọc lại mỗi lần, đừng làm theo thói quen

§3.1 của kế hoạch, mười bước. Ba chỗ đã trả giá nhiều lần:

1. **Nhánh trước, không sửa trên `main`.** `git switch -c toi-uu/<Mx-yy>`.
2. **Viết ca kiểm TRƯỚC**, và xác nhận nó ĐỎ **vì đúng lý do** — không phải đỏ vì `ImportError`.
3. **Xoá `__pycache__` trước MỖI lần phá.** Một phép phá dài bằng mã gốc giữ nguyên số byte,
   nên `.pyc` cũ còn hiệu lực và phép đo chạy mã **khác** mã trong tệp.
4. **Tập phép phá dựng từ `git diff`, không từ ký ức** — và **đọc lại sau mỗi lần sửa mã**:
   việc #27 có một phép phá im lặng trượt vì chuỗi cũ không còn trong tệp (báo `[?]`, không
   báo LỌT). Khuôn: `toi-uu/pha_lai-khuon.py`.

## Bài học mạnh nhất tới giờ — và nó vừa lặp lần thứ BẢY

Bảy việc liên tiếp (M5-03 · M5-07 · M5-13 · M5-17 · M5-01 · M2-09 · **M4-13**) có chỗ LỌT nằm
trong **tập ca kiểm**, không nằm trong mã sản phẩm. Hình dạng của nó:

* hai vế của một phép chia **tình cờ bằng nhau** trong bản mẫu (4 thanh ghi / 4 trường);
* một tập chỉ có **một** phần tử, nên phép gộp nhóm hỏng vẫn ra kết quả đúng;
* hình dạng dữ liệu **đã đúng sẵn**, nên phép sửa hình dạng không đổi gì;
* ca kiểm **không chạm tới dòng** nó tưởng đang canh — việc #27: hàm đối chứng của
  `ham_tra_hang` mở đầu bằng `add.w`, nên một phép kiểm hỏng cũng loại nó, và ca kiểm xanh mà
  không phân biệt được *"đúng hai lệnh"* với *"từ hai lệnh trở lên"*.

Cách chữa, dùng được ngay:

* bản mẫu cho một phép **chia** hay một phép **cắt** phải có ít nhất **hai phần tử KHÁC nhau**;
* đặt một `assert` **trước** chỗ phá/monkeypatch, chứng minh ca kiểm **tới được** dòng ấy;
* khẳng định trên **đúng dòng**, không trên cả khối;
* hai lớp phòng độc lập thì phải có một phép phá **GỘP** — tháo riêng từng lớp không nói gì;
* một lần **TREO** phải biến thành ĐỎ, không được làm script phá chết theo.

## Và một hình dạng thứ hai, cũng đã lặp

**Kế hoạch tự nó sai, và chỉ phép đo chỉ ra.** Việc #27: luật dò ISR mà kế hoạch ghi sẵn
(*"có ký hiệu mạnh `<X>_Handler` ở địa chỉ khác"*) bắt được **0 ca**, vì GNU ld tự ưu tiên
định nghĩa mạnh trước alias yếu. Trước đó: M4-11 sai hai lần, M5-05/M5-07 có ca kiểm xanh vì
lý do sai. Nên **không nhận luật của kế hoạch làm chân lý** — dựng ca tái hiện bằng công cụ
thật trước, rồi mới viết mã theo cái đo được.

Và một hình dạng thứ ba, mới ở việc #27: **phép phá VÔ HIỆU**. Chín chỗ LỌT ở vòng đầu chia ba
loại — sáu lỗ thật trong ca kiểm, **hai phép phá không đổi được hành vi nào** (bit Thumb ở ô 0
vì con trỏ ngăn xếp luôn căn 8 byte; mốc địa chỉ 0 trùng mốc dùng để bỏ ô trống), và **một cửa
mã CHẾT** đã xoá. "LỌT" không tự động nghĩa là "thiếu ca kiểm" — phải mở từng cái ra xem.

## Số đo của chính đợt này, để lần sau không phải đo lại

* **"Phá lại thì đỏ" lượt đầu, mười việc gần nhất:** 7/9 · 18/20 · 17/24 · 22/27 · 15/20 ·
  7/13 · 15/22 · 18/22 · 34/36 · **20/29**. Lượt chốt: tất cả 100 %.
* **Công cụ đã dùng thật: 118/135** — đo 10/10/2026 trên **77 tệp sổ cái, 201 774 bản ghi**.
  Con số cũ *115/134* sai vì **phép lọc**: `glob('**/ledger*.jsonl')` không vào thư mục ẩn, nên
  nó thấy **6 trên 73** sổ cái. Quét bằng `os.walk`. Lọc sai mà trả rỗng thì rẻ; lọc sai mà
  trả một con số **hợp lý** thì đắt.
