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

## 3 · Bản chụp giao diện cắt lời tác tử ở 3 000 ký tự

*Thấy ngày 01/10/2026, phiên robot.*

`UITestChannel.anhChup()` dùng `String(cuoi.prefix(3000))` cho `loi_tac_tu_cuoi`. Câu trả lời
dài hơn bị cắt giữa chừng, nên **nhật ký phiên chép thiếu** — hai lần trong phiên robot: danh
mục an toàn và phần thiết kế phép đo dấu đều mất phần đuôi.

Nhật ký là sở cứ. Một sở cứ cắt mất đoạn cuối thì chỗ bị cắt luôn là chỗ không ai biết là đã
mất. Nâng trần, hoặc ghi ra tệp riêng khi vượt trần và để lại đường dẫn.

## 4 · Cảnh báo dồn đống trên màn hình chat, không có cách nào bỏ đi

*Nêu ngày 01/10/2026, cuối phiên robot.*

> "Màn hình chat Agent quá nhiều cảnh báo cần ẩn nó đi hoặc xoá đi nếu đã clear nhé."

Đã tra, lỗi rõ ràng chứ không phải cảm giác:

| | |
|---|---|
| `notices.append` | **10 chỗ** — `EIDEApp.swift` 4, `AppState.swift` 6 |
| `notices.removeAll` | **1 chỗ duy nhất**, `AppState.swift:172` — và chỗ ấy là `doiDuAn()` |

Nghĩa là trong suốt một phiên, `state.notices` **chỉ tăng**. Cách duy nhất để nó rỗng lại là
**đổi sang dự án khác** — điều không ai làm giữa lúc đang chạy việc. `ThongBaoView`
(`ConsoleView.swift:214`) cũng **không có nút tắt**, nên một cảnh báo đã đọc rồi vẫn nằm đó
tới hết phiên.

Chúng được vẽ sau transcript trong cùng cột (`ConsoleView.swift:77`), nên càng dồn thì càng
đẩy hội thoại lên. Lại không có khâu gộp trùng: cùng một cảnh báo nổ mười lần thì hiện mười
thẻ.

Cần: nút tắt từng thẻ · tự hết sau một khoảng với mức `info` · gộp cái trùng kèm số lần ·
và `clear` của Console phải xoá luôn `notices`, vì anh Công hiểu `clear` là dọn cả màn.

**Và một điểm mù phải sửa cùng lúc.** `UITestChannel.swift:489` chỉ xuất
`notices.suffix(5)`. Nên dù có dồn một trăm thẻ, bộ quét giao diện vẫn chỉ thấy năm — nó
**không thể** phát hiện chuyện dồn đống, mãi mãi. Đúng loại lỗi mà dự án này gặp đi gặp lại:
cơ chế đo có sẵn, nhưng bị bịt đúng chỗ cần thấy. Xuất thêm `tổng số` bên cạnh năm thẻ cuối,
rồi mới đặt được ngưỡng cho nó.
