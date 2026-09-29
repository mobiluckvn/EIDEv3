# trinh-bay-bang-hinh
tu_khoa: sơ đồ, mermaid, vẽ, hình, luồng, kiến trúc, sequence, tuần tự, slide, tài liệu, docx, pptx, pdf, excel, báo cáo, xuất file
khi_nao: Giải thích một CẤU TRÚC hay một TRÌNH TỰ; hoặc người dùng cần một tệp gửi đi, in ra, nộp.

## Viết ```mermaid là VẼ, không phải dán mã

Khối ```mermaid trong câu trả lời **được vẽ thành hình** trên Console, kèm nút *Xem mã* để
người dùng đọc nguyên văn hoặc chép đi. Và `doc.render` vẽ nó thành **ảnh** trong tệp Word ·
PowerPoint · PDF · Excel.

Nên khi cần cho thấy một cấu trúc hay một trình tự, **vẽ**. Đừng vẽ bằng ký tự ASCII, đừng kể
bằng văn xuôi ba đoạn thứ một hình nói xong trong ba giây.

**Người dùng bảo "vẽ cho dễ hiểu" thì hình phải hiện TRONG LỜI ĐÁP**, không chỉ nằm trong tệp
xuất ra. Đo được 29/09/2026 qua giao diện thật: xin *"vẽ sơ đồ cho dễ hiểu, xong xuất ra
PowerPoint"* — tác tử viết sơ đồ vào tệp `.md`, xuất slide có hình đúng, và **Console không có
hình nào**. Người dùng phải mở tệp mới thấy thứ họ vừa xin được xem. Viết cả hai chỗ: khối
```mermaid trong câu trả lời, và cùng khối ấy trong nguồn tài liệu.

| Muốn cho thấy | Viết |
|---|---|
| Ai gọi ai, theo thứ tự nào, chờ đáp ra sao | ```mermaid + `sequenceDiagram` |
| Khối nào nối với khối nào, dữ liệu chảy đường nào | ```mermaid + `graph TB` (hoặc `LR`) |

## Hai kiểu vẽ được, và chỉ hai

`sequenceDiagram` và `graph`/`flowchart`. Kiểu khác (`classDiagram`, `stateDiagram`, `gantt`,
`erDiagram`, `pie`) **chưa vẽ được**: giao diện hiện mã kèm một câu nói rõ là chưa vẽ được.
Biết trước điều đó thì diễn đạt lại bằng hai kiểu trên còn hơn để người dùng nhận một khối mã.

Cú pháp nhận được: `actor`/`participant … as …` · `autonumber` · `->>` `-->>` · `loop`/`alt`/
`opt`/`par` + `end` · `Note over A,B:` · `A["nhãn"]` `A(("nhãn"))` `A{"nhãn"}` · `A -->|nhãn| B`
· `subgraph … end` · `<br/>` để xuống dòng trong nhãn.

## Sơ đồ KHÔNG thay cho hiện vật

Một hình là cách **trình bày**. Cấu trúc mạch vẫn phải ghi bằng `ckm.module_set` mỗi khối một
lần, và hình lấy từ `diagram.render` — do mã sinh nên luôn khớp bản đồ hiện tại. Vẽ tay một
sơ đồ rồi coi như đã ghi xong cấu trúc là mất toàn bộ khả năng truy vết.

## Sửa một sơ đồ: sửa NGUỒN rồi render lại

Sơ đồ trong tài liệu là ảnh dựng ra từ khối ```mermaid trong tệp `.md`. Muốn đổi thì `fs.edit`
tệp nguồn rồi gọi lại `doc.render` — **đừng sửa trong Word**. Nguồn nằm trong sổ cái nên xem
được diff và hoàn tác được; tệp render ra là thứ dựng lại được trong hai giây.

## Bốn định dạng, và chỗ mỗi cái nói KHÔNG

| Định dạng | Hợp với | Nói KHÔNG khi |
|---|---|---|
| `docx` | tài liệu để đọc và sửa tiếp | — |
| `pdf` | bản gửi đi, in ra | máy chưa có LibreOffice |
| `pptx` | trình bày — **mỗi tiêu đề một slide** | — |
| `xlsx` | số liệu để lọc, sắp xếp, tính | nguồn **không có bảng Markdown** nào |

Lời từ chối của `doc.render` (`E2013`) là **có chủ ý**, không phải sự cố: đọc rồi sửa nguồn
hoặc đổi định dạng, đừng gọi lại y nguyên. Nguồn không có bảng mà muốn Excel thì thêm một bảng
thật vào nguồn — và **nói với người dùng là đã thêm**, đừng để họ tự phát hiện tệp của mình đổi.

## Xong thì đọc lại con số

`doc.render` mở lại chính tệp vừa tạo và đếm: bao nhiêu đoạn · bao nhiêu slide · bao nhiêu
trang · bao nhiêu hình. Báo con số ấy cho người dùng. Đừng báo "đã xuất xong" —
*`ok` nói về lời gọi, không nói về kết quả.*
