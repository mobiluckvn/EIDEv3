# Hồ sơ tác tử — dự án `stm32f469-freertos`

Toàn bộ **đầu ra nội bộ** của tác tử trong dự án này. Dự án gốc sống ở `du-lieu/`, mà thư mục
ấy bị gitignore (nơi tác tử dựng dự án, và bộ kịch bản phiên sẽ `rmtree` nó khi chạy không kèm
`--giu-du-an`). Đây là bản chụp để hồ sơ không mất.

| tệp | là gì |
|---|---|
| `ledger.jsonl` | **sổ cái** — mọi lời gọi công cụ, mọi thẻ cổng, mọi quyết định của người, theo thứ tự, có chuỗi hash. Đây là bằng chứng gốc: mọi con số trong DEV log đều đếm được lại từ đây. |
| `changesets.jsonl` | từng thay đổi tác tử làm, kèm lớp giải thích sáu trường (N8) và hoàn tác được (N9). |
| `EIDE.md` | bộ nhớ dài hạn của dự án — thứ tác tử đọc mỗi lượt. |
| `sessions/` | transcript từng phiên. |

## Đếm lại được

```sh
# số lời gọi công cụ
grep -c '"kind": "tool_use"' ledger.jsonl
# công cụ nào được gọi nhiều nhất
grep -o '"tool": "[a-z_.]*"' ledger.jsonl | sort | uniq -c | sort -rn | head
# các thẻ cổng và ai quyết
grep '"kind": "gate"' ledger.jsonl | head
```

Nhật ký người đọc được, kèm ảnh cửa sổ EIDE từng bước, nằm ở `../ket-qua/`.
