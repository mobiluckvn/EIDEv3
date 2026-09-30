# Phần phân tích và thiết kế hiện lên tab — ảnh chụp làm sở cứ

Anh Công theo dõi phiên dựng RTOS và nói: *"việc phân tích và thiết kế của Agent khá okay
nhưng nội dung đó chưa được show ở tab bên cạnh"*.

Đo lại trên chính dự án ấy (`du-lieu/rtos-ptit`) trước khi sửa:

| Bề mặt | Trước |
|---|---|
| A2 Yêu cầu & Giải pháp | A2.1 rỗng · A2.3 · A2.4 — **không có kế hoạch** |
| A5 Thiết kế | A5.4 rỗng · A5.2 rỗng — **rỗng hoàn toàn** |
| A7 Mã nguồn | A7.1 · build — **không có tài liệu phân tích** |

Tác tử vừa so ba phương án kiến trúc, chốt một cái qua cổng G-DESIGN, chia việc thành 6 bước
qua 12 phiên bản kế hoạch, và viết một tài liệu phân tích mã. Không thứ nào trong số đó mở ra
xem được từ tab.

## Ảnh trong thư mục này

Chụp bằng chính app (app tự vẽ cửa sổ ra PNG), trên bản sao dự án RTOS.

| Tệp | Cái nó chứng minh |
|---|---|
| `A2-ke-hoach-va-ADR.png` | Khối **A2.5 Kế hoạch chia việc** đã có; và cột *Ai quyết* của A2.4 nay đọc **"Tác tử đề xuất · anh duyệt qua cổng G-DESIGN"** thay vì mỗi chữ "Tác tử" |
| `A2.5-ke-hoach-day-du.png` | Trọn khối kế hoạch: mục tiêu · **giả định** · ô hổ phách **"Tác tử tuyên bố KHÔNG làm trong lần này"** · 6 bước kèm công cụ và hiện vật |
| `A5-kien-truc-phan-mem.png` | Khối **A5.6 Kiến trúc phần mềm** với **sơ đồ mô-đun vẽ thành hình** — 6 khối, 5 nối, nhóm theo thư mục, cạnh đọc từ `#include` thật |
| `A7-phan-tich-ma.png` | Khối **A7.2 Phân tích mã trước khi sửa** đọc thẳng nội dung tệp `.md` lên tab |

## Vì sao tách khỏi `ket-qua-giao-dien/`

Bộ quét 124 ô chạy trên `du-lieu/stm32f469-freertos` — dự án ấy có REQ nên ô *"có khối cho
người sửa trực tiếp"* mới đo được. Dự án RTOS không có REQ nào, nên chạy bộ quét ở đó sẽ ra
123/124 vì một lý do thuộc về **dự án**, không thuộc về sản phẩm. Trộn hai thứ vào một bảng là
nói sai về sản phẩm, nên ảnh chứng cho các khối mới để riêng ở đây.
