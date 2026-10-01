# Việc anh Công đã nêu, chưa làm

Ghi ngay lúc được nêu, để không rơi khi đang dở việc khác. Làm xong thì xoá khỏi đây và ghi
một mục DEV.

## 1 · Công thức LaTeX chưa dựng trên MÀN HÌNH CHAT

*Nêu ngày 01/10/2026, giữa phiên robot.*

> "Latex chưa render ở màn hình chat bạn nhé."

DEV-317 đã sửa phần **tài liệu xuất ra** — docx, pdf, pptx, xlsx đổi `$…$`, `$$…$$` và rào
` ```math ` sang ký hiệu toán. Nhưng đó là `xuat_ban.py` phía Python.

**Console là đường khác**: nó dựng bằng `Views/Markdown.swift` trong app Swift. Phần công thức
chưa hề được nối vào đó — tức cùng một câu tác tử viết ra sẽ đẹp trong tệp Word mà vẫn là
`\frac{a}{b}` trên màn hình.

Cần: cổng công thức trong bộ dựng Markdown của Swift, dùng lại đúng bảng 90 ký hiệu và cùng
luật tách tiền/công thức của `cong_thuc_nguoi_doc()` — hai bên phải cho **cùng một kết quả**,
và phải có ca kiểm so hai bên trên cùng một tập mẫu (cùng cách `so_do.py` và `SoDo.swift`
đang bị ràng).

## 2 · Rà soát TOÀN BỘ ký hiệu Markdown trên màn hình

*Nêu ngày 01/10/2026, ngay sau mục 1.*

> "Markdown chưa render ** cần phải review đảm bảo render toàn bộ các ký hiệu của Markdown."

Dấu `**` đang lọt ra màn hình — tức bộ dựng Markdown của Console bỏ sót ít nhất một trường
hợp. Không chỉ vá đúng chỗ ấy: phải **rà hết** bảng ký hiệu và có ca kiểm cho từng cái.

Tối thiểu phải phủ: `**đậm**` · `*nghiêng*` · `` `mã` `` · ```` ```khối mã``` ```` ·
`# tiêu đề` sáu mức · `- gạch đầu dòng` lồng nhau · `1. đánh số` · `> trích dẫn` nhiều dòng ·
`| bảng |` · `[liên kết](đích)` · `---` · `~~gạch ngang~~` · chữ lồng kiểu (`**a *b* c**`).

Bài học đã có sẵn trong `tach_chu()` của `xuat_ban.py`: một `finditer` phẳng cho cả ba kiểu
làm `*Đề tài: **Phát triển…** · Vũ Trí Công*` in ra giấy thành `*Đề tài: Phát triển…`. Bộ dựng
Swift rất có thể vướng đúng loại ấy.

**Không con số nào bắt được chuyện này** — phải nhìn màn hình. Bộ quét giao diện đã có ô "lời
tác tử đã được DỰNG thành chữ, không còn dấu Markdown thô trên màn"; ô ấy đang xanh, nên việc
đầu tiên là tìm xem nó xanh nhờ cơ chế nào.
