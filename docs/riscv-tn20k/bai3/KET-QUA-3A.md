# Bài 3 nấc 3a — khối MAC qua giao diện PCPI

*02/10/2026. Khối chạy đúng trong testbench đơn vị. Bộ kiểm có hai lỗ, đã tìm ra.*

## Giao thức PCPI: Agent đọc, và đọc đúng

Đề bài bắt xác minh ba điểm từ README của PicoRV32, và dặn **đừng đoán**. Agent báo cáo kèm số
dòng; tôi kiểm lại từng chỗ và **cả ba đều đúng**:

| Điểm | Agent nói | Kiểm lại |
|---|---|---|
| (b) Hạn trả lời | 16 chu kỳ, rồi CPU báo lệnh không hợp lệ | README dòng 480 ✓ · `pcpi_timeout_counter` 4 bit ở `picorv32.v:1215`, nạp `~0` rồi đếm lùi ✓ |
| (a) Phối hợp với bộ nhân nội bộ | `pcpi_wait`/`pcpi_ready` gộp bằng **OR**; khối ngoài chỉ được tích cực khi giải mã đúng opcode của mình | `picorv32.v:328–329`, đúng nguyên văn ✓ |
| (c) Giữ CPU chờ | bằng `pcpi_wait` | ✓ |

Điểm (a) là chỗ nguy hiểm nhất và Agent nêu đúng hệ quả: **nếu khối ngoài tích cực `ready` sai
lúc, nó cướp lệnh của bộ nhân nội bộ.** Lỗi ấy chỉ hiện khi bật PCPI *cùng với* `ENABLE_MUL` —
tức đúng cấu hình khó nhất của Bài 3.

## Testbench đơn vị: PASS, 1 200 bộ giá trị

Có cả hai giá trị biên **−128** và **127** mà đề bài nêu đích danh. Có ca kiểm "bỏ qua lệnh
không thuộc custom-0".

## Nhưng bộ kiểm có hai lỗ, tìm ra bằng cách phá mã sản phẩm

| Phá gì trong `pcpi_mac.v` | Bộ kiểm |
|---|---|
| không cộng dồn (`acc = tích` thay vì `acc + tích`) | **đỏ** ✓ |
| `acc.clr` không xoá | **đỏ** ✓ |
| bỏ dấu — nhân không dấu thay vì có dấu | *xanh — nhưng xem ghi chú* |
| **nhận MỌI opcode** (cướp lệnh của CPU) | **xanh — LỖ THẬT** |
| **bỏ kiểm `funct7`** | **xanh — LỖ THẬT** |

### Hai lỗ thật, và chúng che nhau

Testbench chỉ có **một** ca âm tính, và lệnh dùng cho ca ấy sai **cả** opcode **lẫn** `funct7`.
Nên khi phá một trong hai phép kiểm, phép kiểm còn lại vẫn chặn — không phép kiểm nào được đo
riêng.

Đây đúng loại hai lớp canh chồng nhau mà dự án đã gặp ở `hdl.py`. Cách chữa cũng giống: thêm
**hai** ca âm tính, mỗi ca chỉ sai **một** thứ.

Lỗ này đắt vì hậu quả của nó là cướp lệnh bộ nhân nội bộ — thứ chỉ vỡ ở cấu hình H1/H2 cộng
PCPI, tức đúng chỗ Bài 3 cần đo.

### Còn phép phá "bỏ dấu" thì không phải lỗ

Với hai toán hạng 32 bit, **32 bit thấp của tích giống hệt nhau** dù hiểu là có dấu hay không
dấu — đó là tính chất của bù hai, không phải chỗ hở của bộ kiểm. Phép phá ấy **không giết được**,
và ghi lại đây để không ai đi viết thêm ca kiểm cho một thứ không phân biệt được.

Dấu chỉ quan trọng khi mở rộng lên quá 32 bit — tức ở nấc 3b, nơi bốn tích 8×8 được cộng vào
một thanh ghi rộng hơn. Ca kiểm dấu phải đặt ở đó.
