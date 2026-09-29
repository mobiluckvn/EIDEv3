# Báo cáo tổng — chạy toàn bộ usecase và quét toàn bộ giao diện

Hai phép đo, một bảng. Nguồn đề bài: `docs/review-v3/test/Usecase_Test_23-09-2026.md` (19 usecase · 76 ca kiểm).

## Tự kiểm: có sót gì không

| Câu hỏi | Trả lời |
|---|---|
| Đủ 76 mã TC trong kết quả? | đủ 76/76 |
| Có mã lạ không nằm trong đề bài? | không |
| Đủ 11 bề mặt trong bộ quét giao diện? | đủ 11/11 |
| Số ô kiểm giao diện | 124/124 đạt |

## Tổng ca kiểm

Hai cột: **máy chấm** (từ khoá + chuỗi công cụ) và **sau khi đọc tay** (đọc nguyên văn từng lời đáp). Máy chấm là lượt sàng, không phải phán quyết — nó đã cho cả ô xanh giả lẫn ô đỏ giả trong chính đợt này, xem `LOI-TIM-DUOC.md`.

| Nhãn | Máy chấm | Sau khi đọc tay |
|---|---|---|
| Đạt | 66 | 68 |
| Không đạt | 2 | 0 |
| Ngoài phạm vi | 2 | 2 |
| Cần người | 3 | 3 |
| Cần thiết bị | 3 | 3 |
| Chưa chạy | 0 | 0 |
| **Tổng** | **76** | **76** |

**2 ca đổi nhãn sau khi đọc tay:**

| TC | Máy chấm | Đọc tay | Loại | Vì sao |
|---|---|---|---|---|
| TC006 | Không đạt | Đạt | lỗi PHÉP CHẤM | Ô ĐỎ GIẢ sau khi sửa §4. Tác tử cập nhật CẢ BA phương án với khối quản lý năng lượng, so sánh lại bằng SỐ (150–300 mA · pin 2500 mAh → 3–5 giờ · chi phí từng phương án) và phân tích mạch nguồn. Đó đúng là 'đánh giá lại phương án bị ảnh hưởng'. Thiếu duy nhất chữ 'v2' — mà kho vốn đánh phiên bản cho mọi hiện vật, nên đặc tả v2 tồn tại về cấu trúc, chỉ không được gọi tên. |
| TC028 | Không đạt | Đạt | lỗi PHÉP CHẤM | Ô ĐỎ GIẢ, và tác tử ĐÚNG hơn đề bài: tôi viết 'dự án có hơn 500 tệp' mà không dựng tệp nào. Nó quét rồi trả lời 'dự án thực tế chỉ có 2 tệp .c, không phải hơn 500' — đúng thứ N6 đòi. Lỗi nằm ở bộ dữ liệu mẫu của tôi, không ở sản phẩm. |

Trong **68 ca đo được**: **68 đạt** (100 %). 8 ca còn lại mang nhãn riêng — gọi chúng là *không đạt* thì bảng nói sai về sản phẩm.

## Theo usecase

| UC | Tên | Đạt / đo được | Ca không đạt |
|---|---|---|---|
| UC01 | Làm rõ ý tưởng và đề xuất phương án giải pháp | 7/7 | — |
| UC02 | Từ phương án đến thiết kế mạch | 7/7 | — |
| UC03 | Sinh mã, biên dịch và mô phỏng | 8/8 | — |
| UC04 | Nhập dự án có sẵn (KiCad + mã nguồn) | 6/6 | — |
| UC05 | Nạp và gỡ lỗi trên mạch thật | 6/6 | — |
| UC06 | Rà soát thiết kế và mã nguồn | 4/4 | — |
| UC07 | Hỏi đáp trên tài liệu kỹ thuật | 2/2 | — |
| UC08 | Tìm linh kiện thay thế | 2/2 | — |
| UC09 | Chuyển firmware sang nền tảng khác (port) | 2/2 | — |
| UC10 | Phân tích log và capture | 3/3 | — |
| UC11 | Kiểm thử đơn vị với mock phần cứng | 1/1 | — |
| UC12 | Tối ưu năng lượng | 2/2 | — |
| UC13 | Tính toán kỹ thuật | 2/2 | — |
| UC14 | Cập nhật firmware từ xa (OTA) | 3/3 | — |
| UC15 | Xuất hồ sơ sản xuất | 1/1 | — |
| UC16 | Truy vết và tài liệu | 2/2 | — |
| UC17 | Quản lý phiên và phiên bản | 2/2 | — |
| UC18 | An toàn và thao tác nguy hiểm | 3/3 | — |
| UC19 | Chịu lỗi hệ thống | 5/5 | — |

## 0 ca không đạt — chi tiết

## Ca không đo bằng máy được — và vì sao

| TC | Nhãn | Lý do |
|---|---|---|
| TC032 | Cần người | Cần RÚT bo ra khỏi máy để đo. Bo đang cắm thường trực và các ca khác cần nó. |
| TC033 | Cần người | Cần một bàn tay rút cáp đúng lúc đang ghi Flash. Máy không tự làm được, và tự động hoá việc này có thể để lại chip ở trạng thái dở dang. |
| TC034 | Cần thiết bị | Cần một bo thứ hai mang MCU khác. Trên bàn chỉ có STM32F469I-DISCO. |
| TC044 | Cần thiết bị | Cần một bản scan datasheet chất lượng kém THẬT. Dựng ảnh scan giả sẽ đo chính ảnh tôi dựng, không đo tài liệu thật. |
| TC053 | Cần thiết bị | Cần bàn thử HIL (hardware-in-the-loop) để chạy lặp 20 lần. |
| TC061 | Ngoài phạm vi | NGOÀI PHẠM VI v1.3 — chủ sản phẩm chốt 24/09/2026: phần PCB (bố trí mạch in, Gerber, drill, file gắp đặt, DRC) chưa làm trong sản phẩm này. |
| TC067 | Cần người | Bộ lái chạy một tiến trình một phiên; dựng phiên thứ hai là đổi công cụ đo giữa lúc đang đo. (Sổ cái ĐÃ có khoá liên tiến trình — xem DEV log.) |
| TC071 | Ngoài phạm vi | NGOÀI PHẠM VI v1.3 — EIDE là ứng dụng một người trên máy cá nhân, không có khái niệm tài khoản hay vai trò. |

## Giao diện

124/124 ô đạt qua 18 phần (11 bề mặt · khung chung · thanh trạng thái · widget sửa tay · bảng Giới thiệu · khổ cửa sổ nhỏ nhất). Ảnh từng bề mặt do chính app tự vẽ, ở `ket-qua-giao-dien/anh/`.

Không ô nào đỏ.

## Đọc bảng này thế nào

Máy chấm ca kiểm bằng **dấu hiệu bề mặt** — cụm từ phải/không được có trong lời đáp, và công cụ phải được gọi. Một lời đáp nhắc đúng chữ mà sai ý vẫn qua được; một lời đáp đúng ý mà dùng từ khác vẫn trượt. Nên ô xanh nghĩa là *có dấu hiệu của thứ đề bài chờ*, không phải *đã làm đúng*. Nguyên văn nằm ở `ket-qua-chay-lai/ket-qua.jsonl` — đó mới là chỗ kết luận.

Bộ quét giao diện thì đo trực tiếp thứ app đang hiện (số khối, nhãn rỗng, khối tràn khung, thẻ còn nút bấm được), nên nó chắc hơn. Nhưng nó cũng đã từng xanh trong khi màn hình sai hai lần — xem DEV-289 và DEV-290 — nên ảnh chụp là một phần của kết quả, không phải minh hoạ.
