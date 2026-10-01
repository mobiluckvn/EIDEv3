# Phần mềm robot hai bánh tự cân bằng — hồ sơ phiên làm việc

Anh Công giao: *đọc tài liệu robot trong thư mục `docs/robot`, tạo dự án, phân tích và thiết
kế phần mềm giúp robot đứng cân bằng, có quy trình vận hành (bật nguồn → báo hiệu → bấm nút →
tự đứng); làm theo thứ tự phân tích · thiết kế · code · mô phỏng; ghi log đầy đủ kể cả lời gọi
LLM.*

Toàn bộ việc do tác tử làm qua giao diện EIDE thật. Thư mục này giữ **dấu vết**, không giữ bản
kể lại.

**Robot đã đứng được** (01/10/2026). Đọc trước:
[**BAO-CAO-SO-SANH.md**](BAO-CAO-SO-SANH.md) — tác tử làm được gì, sai ở đâu, và vì sao robot
chỉ đứng sau khi có một bản đã chạy được làm mốc đối chứng.

| Thư mục | Nội dung |
|---|---|
| [`firmware/`](firmware/) | **1 820 dòng C** cho ATmega328P, 10 mô-đun, kèm `mach.elf` · `mach.hex` đã nạp |
| [`sim/`](sim/) | mô phỏng và hai bài kiểm — **biên dịch chính mã firmware**, không chép lại |
| [`ncc/`](ncc/) | gói V1 của nhà cung cấp — firmware người viết, **mốc đối chứng đã đứng được** |
| [`BANG-TRA-TUAN-THU.md`](BANG-TRA-TUAN-THU.md) | 109 hạng mục ràng buộc dựng từ tài liệu |
| [`QUY-TRINH-NAP-VA-VAN-HANH.md`](QUY-TRINH-NAP-VA-VAN-HANH.md) | tài liệu cho người cầm bo mạch |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | **16 666 sự kiện** sổ cái · **249 changeset** · transcript |
| [`nhat-ky-llm/`](nhat-ky-llm/) | **1 415 lời gọi mô hình**, nguyên văn trả về và lượt gửi mới |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký **65 bước** + **65 ảnh** chụp cửa sổ EIDE ở từng mốc |

Dựng lại phiên: `.venv/bin/python tools/phien_robot_phan_mem.py`

## Vì sao bài này khó hơn vẻ ngoài

Phụ lục B.1 của hồ sơ bàn giao ghi rõ đã **lược bỏ** phần ứng dụng tham chiếu: vòng điều khiển
cân bằng, lọc bù, chốt mốc thăng bằng, PID. Tài liệu chỉ còn **ràng buộc phần cứng**. Tác tử
không có lời giải để chép — nó phải tự thiết kế vòng điều khiển *bên trong* những ràng buộc ấy.

## Kết quả

Kiến trúc chốt: **ba tầng** — ngắt Timer2 50 kHz sinh xung bước · ngắt Timer0 4 ms chạy lọc bù
và PID · vòng nền quét nút và còi. Chọn từ ba phương án so bằng số, người duyệt qua cổng
`G-DESIGN`.

| Số đo | |
|---|---|
| Flash · SRAM | **5 708 B** / 32 KB · **87 B** / 2 KB |
| ISR 50 kHz | **35 lệnh, 0 lời gọi hàm, 0 số thực, 0 phép chia** — đúng điều tài liệu cấm |
| Mô phỏng | **7/7 tiêu chí**, nêu trước khi chạy |

ISR tầng 1 dùng bộ tích luỹ pha nguyên 32 bit (kiểu Bresenham). Đây là ràng buộc khó nhất của
tài liệu — *"phép chia hoặc số thực trong ISR 50 kHz"* nằm trong bảng cấm — và kiểm được bằng
cách dịch ngược tệp ảnh, không bằng cách tin lời.

## Bốn chỗ phải chất vấn mới ra

Phiên này không trôi một mạch. Bốn lần phải dừng lại và bắt sửa:

**1 · `ENABLE = HIGH` cho một chân nối cứng xuống đất.** Máy trạng thái bản đầu tắt động cơ
bằng chân ENABLE ở bốn trạng thái. Nhưng chính tác tử ở lượt đầu đã đọc ra *"EN kéo xuống GND
— mạch lái luôn hoạt động"*. Thiết kế dựa vào một cái chân phần cứng không cho điều khiển. Sửa
thành: ngừng phát xung `STEP`, động cơ **giữ mô-men khoá trục**, dòng tĩnh 1,6–2,0 A, và muốn
thả trơn trục thì phải tắt công tắc cơ khí.

**2 · Mô phỏng xanh cả khi vòng điều khiển bị phá.** Đảo dấu khâu P — robot chắc chắn không
đứng được — mà mô phỏng vẫn báo `dat: true`, 6/6 đạt. Vì khi không hội tụ, biến đo giữ giá trị
khởi tạo `0.0`, và `0 ≤ 2,0 s` nên tính là đạt.

> *Một phép đo xanh bất kể sản phẩm đúng hay sai thì nó không đo gì cả.*

Sửa: thêm **A5 — phải đứng vững liên tục ≥ 3,0 s** trước khi có ngoại lực (tiêu chí *khẳng
định*, thứ còn thiếu); thay `0.0` bằng **`99.0`** để "không chạy" không đội lốt "xuất sắc"; A6
chỉ tính khi ngã **do ngoại lực thử nghiệm**, tự ngã sớm thì trượt. Cổng **`G-QUAL`** nổ đúng
lúc: đổi tiêu chí sau khi đã có kết quả là việc người phải duyệt.

**3 · `"dat": true` viết cứng trong `printf`.** Chương trình mô phỏng in kết luận "đạt" bất kể
số đo. Phán quyết thật do `sim.run` tính từ ngưỡng nên EIDE không bị lừa — nhưng ai chạy tay
nhị phân thì bị. Nay chương trình **chỉ in số đo**, nơi duy nhất phán xử là bộ tiêu chí.

**4 · Yêu cầu "đèn nháy" bị bỏ mà không ai được báo.** FR-01 có chữ đèn nháy, máy trạng thái
ghi rõ 0,5 Hz / 1 Hz / 5 Hz cho từng trạng thái — mà firmware **không một dòng nào** điều khiển
LED. Lý do kỹ thuật đúng: giao thức WS2812 cấm ngắt quá lâu, sẽ làm trượt hạn ISR 50 kHz. Nhưng
kho vẫn nói một đằng, mã làm một nẻo.

Đã tra cả hai chân còn lại: **D13 là `PROBE_ISR`**, **A1 là `PROBE_PID`** — hai điểm đo dao
động ký, và điểm đo tầng 1 là mục 9 của danh mục nghiệm thu. Lấy chúng làm đèn là phá mất phép
đo. Nên chốt: **không có đèn**, FR-01 hạ xuống bản 2 chỉ dùng còi, và ghi thành **`ADR-02`** để
người sau biết đây là *quyết định*, không phải *bỏ quên*.

## Ba phép phá, ba lần đỏ

Sau khi sửa, tự kiểm lại bằng tay trên nhị phân:

| Phá gì | Số đo | Kết |
|---|---|---|
| đảo dấu khâu P | A3 = A4 = A6 = **99** · A5 = **1,536 s** (< 3,0) | trượt |
| ngưỡng ngã 45° → 400° | A6 = A7 = **99** | trượt |
| khôi phục | A1 0,015 · A3 1,408 · A4 0,199 · A5 **3,596** · A6 4,0 · A7 0,0 | đạt 7/7 |

## Điều mô phỏng KHÔNG chứng minh được

Tác tử tự kê ra, và đây là phần quan trọng nhất trước khi cắm mạch: độ trễ bus I2C thật và
nhiễu đường SDA/SCL **không mô phỏng được** — dữ liệu cảm biến trong mô phỏng đến từ mô hình
toán, không đi qua dây và thanh ghi TWI. Bù bằng cách đo xung thật trên chân SCL/SDA bằng máy
phân tích logic khi chạy trên bo.

Mô phỏng chỉ nói thuật toán **tự nhất quán và ổn định trên mô hình**. Nó không nói robot sẽ
đứng.
