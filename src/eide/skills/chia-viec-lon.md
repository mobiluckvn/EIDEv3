# chia-viec-lon
tu_khoa: việc lớn, chia nhỏ, nhiều bước, nhiều lần, kế hoạch, plan, gộp, hợp nhất, tài liệu dài, nhiều phần, làm tiếp
khi_nao: Việc không xong trong một lượt — viết một tài liệu dài, dựng nhiều khối firmware, khảo sát nhiều nguồn.

## Việc lớn thì CHIA, đừng cố làm hết trong một lượt

Một lượt có trần lời gọi và trần thời gian. Cố làm một tài liệu 10 chương trong một lượt thì
thứ anh nhận được là ba chương đầu tử tế và bảy chương viết vội — mà nhìn vào thì cả mười
chương trông giống nhau.

    plan.enter   → khoá mọi công cụ GHI, chỉ còn đọc và nghĩ
    plan.exit    → nộp 2–20 bước cho người duyệt (cổng G-SCOPE nếu là việc lớn)
    ... mỗi bước một (hoặc vài) lượt ...
    plan.step_done(so, hien_vat)   → sau TỪNG bước, không để dồn
    plan.merge(ra=…)               → gộp các phần thành một sản phẩm

## Mỗi bước phải để lại một HIỆN VẬT MỞ RA XEM ĐƯỢC

`plan.step_done` kiểm điều đó bằng mã: đường dẫn tệp có thật · mã hiện vật trong kho · mã
changeset. Một câu kể lại việc mình vừa làm (*"tôi đã viết xong chương 1"*) bị từ chối —
`E6004`. Dấu tích "xong" kiểu ấy chỉ nói rằng **bạn tin là** nó xong.

Nên khi chia bước, hãy chia sao cho mỗi bước **đẻ ra một tệp**. Bước "suy nghĩ về kiến trúc"
không để lại gì; bước "viết `tai-lieu/2-kien-truc.md`" thì có.

## Quyết ngay lúc lập kế hoạch: MỘT tệp hay MỖI BƯỚC MỘT TỆP

Hai kiểu đều dùng được, nhưng chúng khác nhau ở chỗ quan trọng, và chọn nhầm thì chỉ lộ ra ở
cuối — lúc sửa đã đắt:

| | Mỗi bước một tệp rồi gộp | Mọi bước viết dồn một tệp |
|---|---|---|
| Hỏng một bước | làm lại **riêng bước ấy** | làm lại **cả nhóm** dùng chung tệp |
| Bước cuối | `plan.merge` ráp lại, có mục lục, ghi rõ nguồn từng phần | không có gì để gộp — tệp ấy **đã là** bản hợp nhất |
| Hợp với | tài liệu nhiều chương, firmware nhiều mô-đun | một tệp ngắn viết dần |

`plan.exit` nhìn `hien_vat` của các bước và **cảnh báo ngay** nếu nhiều bước khai cùng một
tệp. Đọc cảnh báo ấy rồi quyết, đừng bỏ qua: nó nói trước điều mà `plan.merge` sẽ nói sau,
và nói sau thì việc đã làm xong hết rồi.

## Kế hoạch sống qua nhiều lượt và qua cả khởi động lại

Kế hoạch đã duyệt nằm trong `<pending>` **mỗi lượt**, kèm bước nào xong bước nào chưa. Nó là
hiện vật trên đĩa, nên tắt app mở lại vẫn còn — người dùng gõ *"làm tiếp"* là đi tiếp đúng
bước, không phải duyệt lại.

Vào `plan.enter` khi đang có kế hoạch đã duyệt dở dang thì kế hoạch cũ **được cất lại**, không
mất. Nói cho người dùng biết nó được cất ở đâu.

## Gộp là GHÉP, không phải viết lại

`plan.merge` ráp các phần theo **đúng thứ tự bước**, sinh mục lục, hạ cấp tiêu đề cho khớp thứ
bậc, ghi rõ từng phần lấy từ tệp nào, và **kê ra phần nào không gộp được** ngay trong tài liệu
— không giấu vào kết quả lời gọi.

Nó **không** làm mạch lạc hộ, không thống nhất thuật ngữ hộ. Chỗ trùng lặp hay lệch thuật ngữ
giữa các phần thì sửa bằng `fs.edit` sau đó — khi ấy diff hiện đúng chỗ bạn sửa, còn một công
cụ vừa ghép vừa viết lại thì người duyệt không phân biệt được đâu là bản gốc.

Còn bước chưa xong mà gọi gộp thì bị từ chối (`E6005`): gộp lúc mới làm một nửa ra một tài
liệu **thiếu mà trông như đủ**.

Cần bản Word / PowerPoint / PDF thì `doc.render` từ tệp hợp nhất ấy.
