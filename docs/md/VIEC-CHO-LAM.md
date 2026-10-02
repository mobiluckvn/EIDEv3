# Việc anh Công đã nêu, chưa làm

Ghi ngay lúc được nêu, để không rơi khi đang dở việc khác. Làm xong thì xoá khỏi đây và ghi
một mục DEV.

## 1 · Công thức LaTeX chưa dựng trên MÀN HÌNH CHAT

*Nêu ngày 01/10/2026, giữa phiên robot.*

> "Latex chưa render ở màn hình chat bạn nhé."

DEV-317 đã sửa phần **tài liệu xuất ra** — docx, pdf, pptx, xlsx đổi `$…$`, `$$…$$` và rào
` ```math ` sang ký hiệu toán. Nhưng đó là `xuat_ban.py` phía Python.

**Console là đường khác**: nó dựng bằng `ui/EIDEApp/Sources/EIDE/Views/Markdown.swift` trong app Swift. Phần công thức
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

## 5 · Bảng Markdown dựng sai trên màn hình

*Nêu ngày 01/10/2026, giữa phiên FPGA.*

> "Lưu việc render markdown bảng nữa nhé mình thấy bị lỗi đấy."

Đã tra `ui/EIDEApp/Sources/EIDE/Views/Markdown.swift`. Bảng **có** được nhận ra và **có** bộ
dựng riêng (`BangMd`), nên đây không phải chuyện thiếu tính năng — là bốn lỗi cụ thể trong đó.
Xếp theo mức dễ thấy trên màn hình:

### 5.1 · Hàng lệch cột, vì không ai đối chiếu số ô với tiêu đề

`BangMd` vẽ từng hàng bằng `ForEach(Array(h.enumerated()))` — tức nó đi theo **số ô của hàng
đó**, không theo số cột của tiêu đề. Hàng nào thiếu ô thì vẽ thiếu cột, hàng nào thừa ô thì vẽ
tràn ra ngoài tiêu đề. Không có khâu nào san cho bằng.

Đây gần như chắc chắn là cái anh Công thấy, và nó đi cùng lỗi 5.2 bên dưới.

### 5.2 · `oCua` cắt theo mọi dấu `|`, kể cả dấu nằm trong mã hoặc đã thoát

```swift
return t.components(separatedBy: "|").map { ... }
```

Một ô chứa `` `a|b` `` hoặc `\|` bị cắt thành hai ô. Hàng ấy thừa ô, và hậu quả hiện ra đúng
dưới dạng lỗi 5.1: hàng lệch khỏi tiêu đề. Cần bỏ qua dấu `|` nằm trong dấu nháy ngược và dấu
`\|` đã thoát.

### 5.3 · Bề rộng cột tính theo số ký tự của MÃ NGUỒN, không theo chữ hiện ra

```swift
let dai = max(cot[j].count, hang.prefix(20).map { $0[j].count }.max() ?? 0)
return min(max(CGFloat(dai) * 6.2 + 14, 70), tran)
```

Ô `**ĐẠT**` dài 7 ký tự trong mã mà chỉ hiện 3 chữ. Nên cột nào nhiều chữ đậm hoặc nhiều
`` `mã` `` sẽ được cấp bề rộng cho cả dấu Markdown mà người đọc không thấy — cột rộng vô cớ,
và cột bên cạnh bị ép hẹp theo. Phải đếm **sau khi** chạy `inline()`, không đếm trước.

### 5.4 · Chỉ đo 20 hàng đầu

`hang.prefix(20)`. Bảng dài hơn 20 hàng, mà hàng thứ 21 có ô dài hơn, thì cột không được nới —
ô ấy phải tự ngắt dòng, nên bảng trông vỡ hàng ở đúng chỗ không ai ngờ. Bảng tuân thủ của dự án
robot có **109 hàng**, nên đây không phải trường hợp hiếm.

### Thêm: trần 170 px khi bảng có từ 4 cột

`tran = cot.count >= 4 ? 170 : ...` — 170 px khoảng 27 ký tự. Các bảng so sánh trong báo cáo
thường có 4–6 cột với ô dài hơn thế nhiều, nên chúng bị ép xuống cột rất hẹp rồi ngắt dòng
liên tục. Không mất chữ, nhưng đọc rất khó. Cần tính lại theo bề rộng khung thật thay vì ba con
số ghi cứng.

### Cách đo

**Không con số nào bắt được bốn lỗi này** — phải nhìn ảnh. Nhưng có thể dựng ca kiểm cho phần
**tách**, là phần sai đầu tiên: cho `tach()` một bảng có ô chứa `|` trong mã, một bảng có hàng
thiếu ô, một bảng có hàng thừa ô, rồi khẳng định mọi hàng ra đúng số ô bằng tiêu đề. Phần bề
rộng thì cần ảnh, và `BangMd` đã có một chú thích nói đúng chuyện ấy từ 28/09.

## 6 · Tác tử xác minh con có hạn 10 lời gọi, quá chặt

*02/10/2026.*

Lượt chốt toán hạng nấc 3c, Agent gọi tác tử xác minh con. Nó **cày hết 10 lời gọi vào
`ledger.query` và `fs.read` rồi trả về `chua_du_du_kien`** mà chưa kịp nộp báo cáo đúng lược
đồ. Nên lời xác minh biến mất đúng lúc cần nó nhất — lúc có một kết quả trượt phải đối soát.

Hai chỗ nên sửa:

- **Nới hạn** cho tác tử xác minh, hoặc tính riêng: lời gọi để *đọc bằng chứng* không nên tiêu
  cùng một ngân sách với lời gọi để *làm việc*.
- **Nộp báo cáo trước khi hết hạn.** Khi còn 2 lời gọi, buộc nó nộp những gì đã có kèm ghi rõ
  phần nào chưa kiểm được — một báo cáo thiếu có nói rõ chỗ thiếu thì dùng được, còn
  `chua_du_du_kien` thì không dùng được gì.

## 7 · Cổng duyệt nổ giữa lượt làm mất phần còn lại của lời giao việc

*02/10/2026.*

Lượt 55 của phiên FPGA: thẻ cổng `G-QUAL` hiện ra, người dùng bấm Duyệt, và Agent báo lại:

> *"nội dung chỉ thị chi tiết của anh ở lượt trước (sau đoạn 'Việc lượt này: mở đường để quét
> được N và k…') đã bị ngắt quãng do cơ chế kích hoạt cổng an toàn"*

Nên nó phải hỏi lại toàn bộ đề bài. Một lượt mất trắng, và nếu người dùng không đọc kỹ thì sẽ
tưởng Agent lười hoặc hiểu sai.

Đây **cùng một loại lỗi** với lỗi hộp thư ngày 01/10/2026 (`inbox.jsonl` không được dọn nên app
phát lại lời giao việc cũ nhất, mất bốn lượt để tìm ra): **lời giao việc không tới được Agent
nguyên vẹn, mà biểu hiện ra lại giống như Agent làm sai.**

> Trước khi hỏi *"vì sao nó làm sai"*, hỏi *"nó có nhận được đề bài không"*.

Cần: khi cổng nổ, **giữ nguyên lời giao việc** và phát lại đầy đủ sau khi cổng được duyệt —
cổng là chuyện của luồng điều khiển, không được xén dữ liệu vào.
