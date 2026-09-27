# explain-for-humans
tu_khoa: explain, giải thích, hiện vật, sáu trường, ghi
khi_nao: Ghi bất kỳ hiện vật nào — mọi lời gọi công cụ có `explain`.

## Sáu trường, và câu mà mỗi trường trả lời

| Trường | Người đọc đang hỏi |
|---|---|
| `summary` | Cái này là gì, một câu? |
| `why` | Vì sao lại thế, chứ không phải cách khác? |
| `sources` | Dựa vào đâu? (Fact, tài liệu + trang, lời người dùng) |
| `diff_prev` | Khác bản trước ở chỗ nào? |
| `next` | Giờ tới lượt ai làm gì? |
| `confidence` | Tin được tới đâu, và vì sao chỉ tới đó? |

## Viết cho ai

Cho chính người dùng đọc sau sáu tháng, khi họ đã quên hết. Không viết cho máy chấm điểm.

- `why` **không** được là "vì người dùng yêu cầu" — đó là ai yêu cầu, không phải vì sao.
- `sources` rỗng nghĩa là con số trong hiện vật này không truy vết được. Nếu thật sự không
  có nguồn thì nói ra trong `confidence`, đừng để trống rồi đi tiếp.
- `diff_prev` ở bản đầu tiên viết "bản đầu tiên" — đừng bịa một thay đổi.
