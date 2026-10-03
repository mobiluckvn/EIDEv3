# Phiên sinh viên — vòng kín từ tài liệu yêu cầu tới bo thật

**Phiên CHƯA XONG.** Đã chạy 23 trong 32 bước. Phần còn lại cần cắm bo, dự kiến chiều
03/10/2026. Thư mục này giữ dấu vết tới thời điểm chốt, không giữ bản kể lại.

Khác hai phiên robot trước ở ba chỗ, và cả ba đều là chủ ý:

1. **Đầu vào là tài liệu yêu cầu phần mềm**, không phải hồ sơ bàn giao phần cứng. Tài liệu đó
   đã cho sẵn đủ 28 tham số đã chạy được trên bo thật. Nên phiên này không đo "tác tử có tự
   nghĩ ra được tham số không" — câu đó đã trả lời ở phiên 01/10 và trả lời là **không**. Nó đo
   câu khác: *cho một đặc tả đủ số, tác tử có đi hết vòng mà không tự bỏ bước nào không.*

2. **Dự án dựng trống.** Không chép firmware cũ sang. Chép thì tác tử đọc ra đáp án và phiên
   này không đo được gì ngoài khả năng chép tệp.

3. **Người ra lệnh đóng vai sinh viên mới học nhúng**, không đóng vai người đã biết đáp án.

Mọi lượt đi qua giao diện EIDE thật. Ảnh từng mốc do chính app vẽ ra cửa sổ của nó, không dùng
`screencapture`.

Dựng lại: `PHIEN_NOI_HAN=1 .venv/bin/python tools/phien_sinhvien_robot.py --giai-doan 1`

## Số đo tới bước 23

| | |
|---|---|
| Bước đã chạy | **23 / 32** |
| Mã nguồn tác tử viết | **679 dòng**, 8 tệp |
| Bộ đo | **272 dòng**, dịch thẳng mã sản phẩm |
| Ảnh nhị phân | **9 382 B** Flash / 32 KB · **471 B** SRAM / 2 KB |
| ISR 50 kHz | **64 lệnh · 0 lời gọi hàm · 0 phép chia · 0 số thực** — đo trên `.elf`, không đọc đặc tả |
| Lời gọi công cụ | **394** (368 chạy được · **26 bị chặn hoặc lỗi**) |
| Lời gọi mô hình | **512** |
| Sổ cái | **6 391 dòng** |
| Changeset | **70**, mỗi lần gỡ lại được |
| Ảnh cửa sổ EIDE | **23** |
| Độ nhạy bộ đo | **0/4 → 5/5** phép phá bị bắt |

## Bảy lượt sửa, và chỗ đo ra chúng

Kịch bản ban đầu 18 bước chạy một chiều. Thực tế thành 32, vì **mỗi lần mở mã hoặc mở sổ cái ra
đối chiếu lại bắt được một chỗ phải quay lại**. Bảy bước thêm vào đều ghi rõ trong
`tools/phien_sinhvien_robot.py` lý do nó sinh ra.

| # | Chỗ sai | Phép đo nào bắt được | Ai bắt |
|---|---|---|---|
| 1 | Tài liệu không nói trục nào là trục nghiêng, trục nào là trục xoay | đọc `mpu6050.c` rồi tra lại tài liệu | **tác tử tự nêu** |
| 2 | Câu chốt phương án không nhắc tên phương án nào | cổng `E5009` chặn `store.option_choose` | cổng |
| 3 | Ghi hằng số chưa truy vết được nguồn | lớp cấp quyền `E4001` chặn `fs.write` | cổng |
| 4 | Khai "0 lệnh call trong hàm ngắt" khi chưa có tệp nào được dịch | đếm lời gọi của lượt: chỉ có `doc.read` ×5 | người |
| 5 | Chân D2/D3 thay D6/D7 · thiếu còi D10 và nút D12 · chiếm chân đo D13 làm đèn | đọc `config.h` đối chiếu Bảng 1.3 | người |
| 6 | Dùng sai **cả ba trục** cảm biến so với Bảng 3.2 | đọc `control.cpp` đối chiếu Bảng 3.2 | người |
| 7 | Bốn phép phá đều sống sót; rồi vá xong thì **chỉnh sai mốc** | đọc `sim/` và tự chạy lại bốn phép phá | người + tác tử |

Hai điều đáng ghi hơn cả bảy dòng trên.

**Dòng 1 là chỗ tác tử làm tốt hơn tài liệu.** Ở lượt thứ ba tôi hỏi *"có con số nào bạn cần mà
tài liệu KHÔNG ghi không?"*. Nó chỉ ra tài liệu viết "trục trước sau" và "trục xoay" mà không
nói đó là byte nào trong 14 byte đọc về. Tra lại `mpu6050.c` thì đúng là thiếu. Tài liệu lên
bản 1.1, thêm mục 3.2. **Nó không tự chế ra ánh xạ trục rồi đi tiếp** — đúng chỗ phiên 01/10 đã
sai khi tự nhớ hằng số phần cứng.

**Dòng 6 là chỗ nặng nhất, và nó cùng một dạng với dòng 5.** Bảng 3.2 là bảng do chính tác tử
đòi thêm, và ở lượt sau nó đọc lại đúng từng dòng. Rồi lúc viết mã nó dùng bộ trục khác. Có
bảng đúng trong tay, đọc lại đúng, vẫn viết theo thói quen. Hai lần trong một phiên.

## Chỗ sâu nhất: bài kiểm nhạy mà chỉnh sai mốc

Sau khi vá, bộ đo bắt được cả bốn phép phá. Nhưng đọc kỹ thông báo lỗi thì nó khẳng định **chân
D6 phải ở mức CAO khi tiến**, trong khi Bảng 3.3 ghi **mức THẤP**. Mã sản phẩm cũng đặt mức CAO.
Nên bài kiểm đi khẳng định cái sai là đúng.

> Một bài kiểm không nhạy thì chỉ là không đo được gì.
> Một bài kiểm nhạy mà chỉnh sai mốc thì nó **chủ động bảo vệ cái lỗi** — ai sửa mã cho khớp
> tài liệu sẽ thấy nó báo đỏ, rồi tưởng mình vừa làm hỏng.

Nguyên nhân: bài kiểm được viết bằng cách đọc mã rồi ghi lại mã đang làm gì. Làm thế thì nó chỉ
xác nhận lại chính mã. Sau khi sửa, hai hằng số chiều tiến được đưa ra `config.h` kèm trích chỗ
lấy, và mốc kỳ vọng của bài kiểm lấy từ Bảng 3.3 chứ không từ hành vi của mã.

## Phép đo độ nhạy, làm KHÔNG qua tác tử

Tự dịch bằng `cc`, tự phá bằng `sed`, tự chạy:

```
cc -I sim -o /tmp/s sim/sim_main.c sim/control.c sim/mock_motor.c -lm
```

| Trạng thái mã | `"dat"` |
|---|---|
| nguyên trạng | `true` |
| số bù 92 → 535 | `false` |
| chiều trái 0 → 1 | `false` |
| chiều phải 1 → 0 | `false` |
| cộng → trừ | `false` |
| **đổi lại sai trục `accel_z` → `accel_y`** | `false` |
| khôi phục | `true` |

Phép cuối không có trong Bảng 4.2 — tôi tự thêm, và nó bắt đúng cái lỗi vừa suýt lọt ở dòng 6.

`dat` được tính từ `all_tests_passed`, bị hạ bởi 10 phép kiểm khác nhau, **không viết cứng trong
`printf`** như phiên 01/10.

## 26 lời gọi bị chặn — không lời nào là lỗi hệ thống

| Mã | Chặn vì | Đúng hay sai |
|---|---|---|
| `E4001` | Ghi hằng số chưa truy vết được nguồn · chưa có tệp mã để dịch | **chặn đúng** |
| `E5009` | Khai người quyết mà câu trích không nhắc phương án nào | **chặn đúng** |
| `E2003` | Rút bản đồ chân từ tệp `.docx` như thể nó là header của bo | **chặn đúng** |
| `E8002` | Đăng ký chip và gán chân trước khi có Fact chân | **chặn đúng** |
| `E5007` | Bộ kiểm chứng không đọc được cấu trúc nhị phân tệp Word | hạn chế thật, tác tử nói ra |

Lời chặn `E4001` nguyên văn: *"Trong nội dung sắp ghi có hằng số kỹ thuật chưa truy vết được tới
nguồn nào... Đừng bỏ con số đi, cũng đừng tìm đường vòng để lách."*

## Một luật tác tử tự ghi vào kho sau khi bị bắt

`EIDE.md` dòng 26 của dự án, changeset `cs-0019`:

> *Chưa đo được bằng công cụ thật thì nói thẳng là chưa đo được; tuyệt đối không đưa con số suy
> diễn lý thuyết dưới dạng kết quả đã đo.*

Nó biến một lần bị bắt thành ràng buộc cho các lượt sau, không phải một lời xin lỗi rồi quên.

## Những tệp để kiểm lại

| Thư mục | Nội dung |
|---|---|
| [`firmware/`](firmware/) | 679 dòng, 8 tệp, cho ATmega328P |
| [`sim/`](sim/) | bộ đo — `#include` thẳng `control.cpp` và `motor.cpp`, chỉ mock thanh ghi AVR |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký 23 bước · 23 ảnh cửa sổ EIDE · `buoc.jsonl` để so hai lần chạy bằng mã |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | sổ cái 6 391 dòng · 70 changeset · `EIDE.md` |
| [`nhat-ky-llm/`](nhat-ky-llm/) | **512 lời gọi mô hình**, nguyên văn |
| [`YEU-CAU-...docx`](YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx) | tài liệu đầu vào, bản 1.1 |

Nhật ký mô hình thu từ **79 MB xuống 2,5 MB** bằng `tools/thu_gon_nhat_ky_llm.py`: lưu lời nhắc
hệ thống và danh sách công cụ **một lần**, và mỗi lượt chỉ giữ phần gửi mới. Không cắt nội dung
— dựng lại cả 512 lời gọi rồi so với bản thô cho **0 lời gọi lệch**:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0,'tools')
from thu_gon_nhat_ky_llm import doc_lai
import pathlib
print(sum(1 for _ in doc_lai(pathlib.Path('docs/robot-sinhvien/nhat-ky-llm'))))"
```

## Còn lại gì

| Giai đoạn | Bước | Cần người |
|---|---|---|
| 5 — bo thật | 24–29 | **có** — ba chỗ dừng chờ người quan sát robot |
| 6 — chốt | 30–32 | không |

Ba dấu của vòng điều khiển và ba hằng số theo từng bo **chỉ đo được khi có người dựng robot
lên**. Tài liệu đã cho sẵn cả ba dấu đúng, nên kỳ vọng ít vòng cắm bo hơn mười vòng của phiên
01/10 — nhưng không kỳ vọng một vòng.
