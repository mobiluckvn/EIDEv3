# DEV-333 — Gói app cũ hơn mã nguồn, và 16 câu trả lời mất đuôi trong im lặng

Ngày 03/10/2026. Phát hiện giữa phiên sinh viên FPGA, khi đang kiểm câu trả lời của tác
tử về số bitstream cần dựng cho Bài 2.

## Chuyện gì đã xảy ra

Tôi đọc `NHAT-KY.md` và thấy câu trả lời của tác tử dừng giữa một công thức:

```
Tổng số ô đo là:
$$\mathbf{4} \ (N) \times \mathbf{2} \ (\text{dtype}) \times \mathbf{4} \ (\text{ver}) \times \mathbf
```

Kết luận đầu tiên của tôi: *tác tử không trả lời câu hỏi về số bitstream.* Kết luận ấy
**sai**. Nó trả lời đầy đủ — ở đoạn nhật ký không có.

## Đo ở bốn chỗ trên cùng một câu

| Chỗ đo | Độ dài câu trả lời bước 30 |
|---|---|
| Mô hình sinh ra — `.eide/llm/*.jsonl`, `finish_reason=STOP`, `out=2077` token | **6 057** ký tự |
| Bản ghi phiên của app — `.eide/sessions/ses-0016/transcript.jsonl` | **6 057** ký tự |
| Chuỗi app đưa ra cho bộ đo — sự kiện `anh_chup` | **3 000** ký tự |
| `NHAT-KY.md` | 3 063 ký tự |

Đúng 3 000 ở cả 120 ảnh chụp của phiên. Lời của mô hình không bị cắt; chỗ mất nằm giữa
bản ghi của app và bộ đo.

## Nguyên nhân gốc

Mã nguồn Swift hiện tại để trần ở 20 000 ký tự, **dán dấu `⟨CẮT Ở … — bản đủ N ký tự ở
…⟩` vào chính chuỗi**, và ghi bản đủ ra tệp. Cả ba thứ đó vào từ DEV-325 ngày 02/10 và
`ThongBaoTests` đã xanh từ hôm ấy.

Nhưng:

```
ui/EIDEApp/.build/debug/EIDE                  dựng 02/10 21:40   ← swift build cập nhật
ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE       dựng 30/09 22:45   ← chỉ dong-goi.sh cập nhật
```

Phiên chạy `EIDE.app/Contents/MacOS/EIDE`. `swift build` không cập nhật tệp đó —
`dong-goi.sh` mới cập nhật, và nó không được chạy lại sau ngày 30/09. Bốn commit vào `ui/`
chưa bao giờ tới chỗ đo: `d45c64d`, `DEV-325`, `DEV-328`, `DEV-329`.

Bản 30/09 cắt bằng `String(cuoi.prefix(3000))`, **không dấu, không bản đủ, không khai độ
dài thật**. Nên mất mà không có cách nào biết là đã mất.

## Thiệt hại

16 trong 30 câu trả lời của phiên bị cắt, tổng **23 396 ký tự** không vào nhật ký. Nặng
nhất: +4 076 ký tự ở một câu. Nhật ký là sở cứ để viết báo cáo, nên đây là 16 chỗ mà báo
cáo sẽ nói thiếu về việc tác tử đã làm.

Và một thiệt hại không đo bằng ký tự: tôi đã dùng nhật ký ấy để **kết luận sai về tác
tử**. Phần bị mất của câu bước 28 chứa đúng mục `## 4. Cả phiên này cần dựng bao nhiêu
bitstream? Vì sao đúng con số đó?` — tức là chính câu tôi bảo nó không trả lời.

## Vá

1. **Dựng lại gói** bằng `ui/EIDEApp/dong-goi.sh`. Kiểm bằng hành vi, không bằng
   `strings`: `swift test --filter ThongBao` → 6 phép kiểm xanh.

2. **Chốt trước khi mở app** — `doi_chieu_app_voi_nguon()` trong `tools/phien_robot.py`,
   gọi ở đầu `mo_app()` của cả bốn phiên. Nếu có tệp `.swift` nào mới hơn gói thì phiên
   **dừng**, nêu tên tệp và cách chữa. Phép kiểm này không hỏi "mã có đúng không" mà hỏi
   *"thứ tôi sắp đo có phải là mã tôi vừa sửa không"*.

3. **Chốt trong `hoi()`** — so `loi_tac_tu_do_dai` (app khai độ dài thật) với độ dài chuỗi
   nhận được. Thiếu thì lấy lại bản đủ từ `transcript.jsonl` và dán một dòng ghi rõ đã
   lấy lại; không lấy được thì ghi thẳng vào nhật ký rằng **phần này thiếu đuôi, đừng kết
   luận tác tử không nói điều gì chỉ vì không thấy nó ở đây**.

4. **Vá lại nhật ký đã hỏng** — `tools/va_nhat_ky_bi_cat.py`. Khớp theo 300 ký tự đầu
   (đuôi là thứ đã mất nên không dùng để khớp được), kiểm không có chỗ nào khớp nhiều hơn
   một lời gốc (0 chỗ nhập nhằng), và dán dấu vào từng chỗ vá.

5. **Phép kiểm trên sở cứ thật** —
   `test_nhat_ky_fpga_khong_con_cau_nao_bi_cat_am_tham` đọc chính
   `du-lieu/ket-qua/fpga-sinhvien/NHAT-KY.md` và đòi không câu nào dài đúng 3 000 ký tự.
   Chạy lại phiên bằng gói cũ thì con số ấy hiện ra lại ở đây.

`tests/test_bo_do_phien.py` — 9 phép kiểm, đã thử độ nhạy: đẩy mốc một tệp Swift lên mới
hơn gói thì chốt kêu và nêu đúng tên tệp; gói mới hơn thì chốt im (một chốt lúc nào cũng
kêu sẽ bị tắt); thiếu gói thì nói là thiếu. Toàn bộ: **1 593 phép kiểm xanh**.

## Thuộc họ nào

Cùng họ với bốn lỗi khác của hai ngày này, và đây là lần thứ năm:

| Lần | Thứ nói một đằng | Thực tế |
|---|---|---|
| `PULL_MODE=UP` | có trong tệp CST | chân vẫn thả nổi |
| `"openfpgaloader"` | có trong danh sách công cụ | nhánh ấy chưa chạy lần nào, nổ `NameError` |
| mốc nạp sau mốc dựng | phép so của tôi ĐẠT | bo đang chạy bitstream khác, từ flash |
| `control.c` | có trong dự án, mô phỏng 7/7 | mã chết, firmware không gọi |
| **gói app** | `swift test` xanh, mã đã sửa | **đo bằng bản dựng 3 ngày trước** |

Bài học viết thẳng vào chú thích hàm chốt: **một phép kiểm xanh trên mã nguồn không nói
gì về bản nhị phân mà bộ đo đang chạy.** Phải có một chỗ nối hai thứ đó lại, và chỗ nối
ấy phải tự kêu.
