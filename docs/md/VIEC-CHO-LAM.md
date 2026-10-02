# Việc anh Công đã nêu, chưa làm

Ghi ngay lúc được nêu, để không rơi khi đang dở việc khác. Làm xong thì xoá khỏi đây và ghi
một mục DEV.

## 1–5 · ĐÃ LÀM HẾT ngày 02/10/2026 — xem DEV-325

Năm việc về giao diện anh Công nêu ngày 01/10/2026 đã xong. Ghi lại **ngắn** ở đây vì chi tiết
nằm trong DEV-325; nhưng phải ghi lại một điều: **ba trong năm mục chẩn đoán sai nguyên nhân**,
và chỉ biết khi có chỗ đứng để đo.

| | Việc | Thực tế tìm ra |
|---|---|---|
| 1 | công thức LaTeX chưa dựng ở chat | *"chưa hề được nối vào"* là **sai** — đã nối từ trước. Lỗi thật: hai bảng ký hiệu **lệch 41 mục**, và `\sum` ở Swift ra `Σ` thay vì `∑` |
| 2 | `**` lọt ra màn, rà hết ký hiệu | phần lớn **đã hoạt động**. 11 trên 17 ca kiểm mới xanh ngay với mã cũ |
| 3 | bản chụp cắt ở 3 000 ký tự | đúng. Nâng lên 20 000 và khi còn cắt thì ghi bản đủ ra tệp |
| 4 | cảnh báo dồn đống | đúng, và đúng cả chẩn đoán 10 chỗ thêm / 1 chỗ xoá |
| 5 | bảng dựng sai | đúng cả bốn lỗi. Đây là mục duy nhất chẩn đoán trúng hoàn toàn |

**Thứ đáng giá nhất không phải năm bản vá, mà là mục tiêu kiểm cho giao diện.** Trước 02/10
`Package.swift` chỉ có một `executableTarget` — **không một ca kiểm nào** cho toàn bộ giao diện,
nên cả năm mục trên đều kết thúc bằng câu *"không con số nào bắt được, phải nhìn màn hình"*.
Câu ấy đúng với bề rộng cột và màu sắc, nhưng **sai với phần tách khối, tách ô, đổi ký hiệu** —
những phần ấy là hàm thuần. Nay có 31 ca kiểm Swift, và 13 trong số đó đỏ khi trả lại mã cũ.

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

## 7 · ~~Cổng duyệt làm mất lời giao việc~~ — ĐÃ VÁ. Và tôi sai hai lần trước khi tìm ra

*02/10/2026. Giữ cả hai lần sai, vì đường đi tới câu trả lời đáng ghi hơn câu trả lời.*

**Hiện tượng.** Ba lượt liền, thẻ cổng `G-QUAL` hiện ra, người dùng bấm Duyệt, rồi Agent báo
rằng lời giao việc đã bị cắt và xin gửi lại đề bài.

**Lần sai thứ nhất — tôi tin ngay.** Ghi vào đây rằng cổng xén dữ liệu, rồi commit.

**Lần sai thứ hai — tôi tra sổ cái và kết luận Agent kể sai.** Lời giao việc còn nguyên 770 ký
tự trong `.eide/ledger.jsonl`, đủ cả đầu lẫn đuôi. Tôi viết lại mục này nói rằng Agent dựng ra
một lời giải thích, và ghi thêm một bài học về việc đừng tin lời kể của tác tử. Commit lần nữa.

**Nguyên nhân thật.** `ledger.query` cắt **mọi** sự kiện ở `chu[:220]` và **không nói gì**:

```python
ra.append({... "tom_tat": chu[:220]})
```

Tôi tra **tệp** sổ cái nên thấy đủ 770 ký tự. Agent đọc **qua `ledger.query`** nên chỉ thấy 220
ký tự đầu. **Cả hai đều báo đúng về thứ mình nhìn thấy.** Chỗ hỏng là công cụ cắt mà không nói,
nên không bên nào biết hai bên đang xem hai thứ khác nhau — và tôi đã dùng cái thấy của mình để
bác cái thấy của nó.

**Đã vá hai chỗ:**

- **DEV-324** — `ledger.query` nâng bản tóm lên 1 200 ký tự, và khi còn cắt thì đánh dấu
  `da_cat` kèm `do_dai_that`, cộng một lời nhắc chỉ đường đọc đủ. Cắt thì phải nói.
- **DEV-323** — nhánh duyệt cổng chặn một lời gọi công cụ nay phát lời nhắc. Thiếu nó, mô hình
  thấy `E4003` *"DỪNG LẠI"* rồi ngay sau là kết quả của chính công cụ ấy, không ai giải thích.
  Chỗ này là lỗi thật, độc lập với chỗ trên.

**Bài học, và nó không phải bài học tôi tưởng.** Lần viết trước tôi rút ra *"đừng tin lời kể
của tác tử"*. Nhưng lần này lời kể của nó **đúng về hiện tượng** và chỉ sai về cơ chế — còn
tôi thì sai về cả hiện tượng. Bài học đúng là:

> Khi hai bên báo hai điều trái nhau, câu hỏi đầu tiên không phải *"ai sai"* mà là **"hai bên
> có đang xem cùng một thứ không"**. Ở đây không: một bên đọc tệp, một bên đọc qua một công cụ
> cắt chuỗi trong im lặng.

