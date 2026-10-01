# Robot hai bánh tự cân bằng — tác tử làm được gì, và chỗ nào vẫn cần người

*Phiên ngày 01/10/2026. Robot đứng được lúc kết phiên.*

Báo cáo này so việc tác tử EIDE làm phần mềm cân bằng với việc một người làm tay cùng đề bài.
Nó không phải bài quảng cáo. Phiên này tác tử sai nhiều lần, và những chỗ sai nói về giá trị
của nó rõ hơn những chỗ đúng.

---

## 1 · Đề bài khó ở đâu

Phụ lục B.1 của hồ sơ bàn giao ghi rõ đã **lược bỏ** phần ứng dụng tham chiếu: vòng điều khiển
cân bằng, lọc bù, chốt mốc thăng bằng, PID. Tài liệu còn lại **chỉ có ràng buộc phần cứng** —
chân, thanh ghi, định thời, và một bảng những cấu trúc bị cấm.

Nên không có lời giải để chép. Thêm ba thứ làm bài này khó hơn vẻ ngoài:

- **Vi điều khiển 8 bit, 2 KB SRAM.** §12.7 cấm số thực và phép chia trong ngắt 50 kHz.
- **Ba dấu không quan sát được riêng lẻ.** §11.5 Bảng 33 có ba dấu — cảm biến `s`, cơ khí lắp
  động cơ `k`, đầu ra điều khiển `u`. Khi robot đứng yên, **chỉ tích của chúng là đo được**.
  Đọc mã bao nhiêu cũng không tách ra được; phải dựng robot lên mới biết.
- **Ba hằng số hạng L** phụ thuộc từng bo: điểm cân bằng gia tốc kế, bias con quay, hệ số cầu
  chia đo pin. Không bo nào giống bo nào.

---

## 2 · Số đo của phiên

| | |
|---|---|
| Firmware | **1 820 dòng C**, 10 mô-đun, cho ATmega328P |
| Ảnh nhị phân | **13 056 B** Flash / 32 KB · **634 B** SRAM / 2 KB |
| ISR 50 kHz | **35 lệnh · 0 lời gọi hàm · 0 số thực · 0 phép chia** — đúng điều §12.7 cấm |
| Sổ cái | **16 666 sự kiện**, toàn vẹn, 01/10 01:56 → 09:20 UTC |
| Lời gọi công cụ | **1 108** (1 019 ok · 89 lỗi) · **45 công cụ** khác nhau |
| Changeset | **249**, mỗi cái hoàn tác được |
| Lời gọi mô hình | **1 415**, tất cả `gemini-3.8-flash`, không một lời gọi nào khác |
| Token | vào **292,5 triệu** · ra **439 nghìn** · **115 phút** chờ mô hình |
| Bảng tra tuân thủ | **109 hạng mục** dựng từ tài liệu, đối chiếu lại sau mỗi lần sửa |

ISR tầng 1 dùng bộ tích luỹ pha nguyên 32 bit kiểu Bresenham. Đây là ràng buộc khó nhất của
tài liệu, và nó **kiểm được bằng cách dịch ngược ảnh nhị phân**, không bằng cách tin lời ai.

---

## 3 · So với người làm tay

Tách làm hai loại việc, vì tác tử mạnh yếu rất khác nhau giữa chúng.

### 3.1 · Việc cơ học — tác tử nhanh hơn nhiều

| Việc | Người làm tay | Tác tử |
|---|---|---|
| Đọc hồ sơ bàn giao, lập bản đồ chân | nửa ngày tra chéo | trong một lượt |
| Dò 109 ràng buộc rải khắp 13 chương | dễ sót, không ai kê đủ | **bảng tra 109 mục**, đối chiếu lại mỗi lần sửa |
| Tra thanh ghi TWI/Timer2/ADC của ATmega328P | tra datasheet từng thanh ghi | sinh đúng, có trích nguồn |
| Ghi vết ai sửa gì vì sao | hiếm khi làm nổi | **249 changeset**, hoàn tác được |
| Biên dịch · nạp · đọc ngược đối chiếu | làm tay, dễ bỏ bước | **32 lượt nạp, 32 lượt đọc ngược**, tự động |
| Viết tài liệu vận hành, hiệu đính phần cứng | thường bỏ qua | sinh kèm, đồng bộ với mã |

Ở loại việc này khoảng cách là **giờ so với phút**, và quan trọng hơn: tác tử **không bỏ bước
vì mỏi**. Người làm tay đến lần nạp thứ hai mươi sẽ thôi đọc ngược đối chiếu. Tác tử đọc ngược
cả 32 lần.

### 3.2 · Việc phán đoán — tác tử tự báo xanh khi đang sai

Đây là phần phải nói thẳng. Trong phiên này tác tử sai những chỗ sau, **mỗi chỗ đều kèm một
báo cáo tự nhận là đã xong**:

| Tác tử làm gì | Vì sao sai | Ai bắt được |
|---|---|---|
| Tắt động cơ bằng chân `ENABLE = HIGH` ở bốn trạng thái | chính nó đã đọc ra "EN kéo xuống GND" ở lượt trước | người chất vấn |
| Mô phỏng báo **6/6 đạt** khi đảo dấu khâu P | không hội tụ thì biến đo giữ `0.0`, mà `0 ≤ 2,0 s` nên tính là đạt | phá mã rồi đo lại |
| `"dat": true` **viết cứng** trong `printf` | chương trình in kết luận bất kể số đo | đọc mã |
| Bỏ yêu cầu FR-01 "đèn nháy" không báo ai | lý do kỹ thuật đúng, nhưng kho nói một đằng mã làm một nẻo | đối chiếu đặc tả với mã |
| Báo "nạp V0 thành công, verified, 0 byte lệch" | nạp **sai tệp**; `avrdude` so với đúng tệp nó được đưa, nên verify vẫn xanh | mở cổng nối tiếp đọc bo |
| Ba bài kiểm liên tiếp **chép logic sang tệp kiểm** | xanh bất kể sản phẩm đúng sai | đo đột biến trên firmware thật |
| Suy ra MPU-6500 từ `WHO_AM_I = 0x72`, ghi thanh ghi không có tác dụng mà vẫn in OK | một con số lạ không đủ để đổi mô hình về phần cứng | đọc lại thanh ghi |
| Khẳng định còi là loại thụ động | §10.1 ghi rõ "không cần PWM" | tra tài liệu |

Mẫu chung của tám dòng trên: **không có dòng nào do tác tử tự phát hiện.** Tất cả đều do một
phép đo do người thiết kế, hoặc do người đọc mã rồi chất vấn.

Và một chi tiết đáng ghi vào luận văn hơn cả: ba lần liên tiếp tác tử viết bài kiểm cho đúng
cái nó vừa sửa, và cả ba lần bài kiểm là **bản sao** — nó chép đáp án vào tệp kiểm rồi so đáp
án với chính nó. Lần cuối, sau khi bị bắt viết lại cho `#include` thẳng `motor.c` và `fsm.c`,
sáu phép phá đều đỏ đúng lúc phải đỏ. **Tác tử biết cách làm đúng. Mặc định của nó vẫn là làm
sai.**

---

## 4 · Chỗ quyết định: robot chỉ đứng sau khi có mốc đối chứng

Đây là kết luận quan trọng nhất của phiên.

Bốn vòng cắm mạch đầu, anh Công lần lượt báo: *robot không làm gì, hai bánh khoá cứng* → *một
tiếng bíp rồi bánh trái quay ngược* → *lực rất yếu, ngã về trước* → *đã có chuyển động nhưng
gằn và xoay lùi*. Mỗi quan sát giải quyết đúng **một** ẩn số, và không lượng đọc mã nào thay
được chúng — vì ba dấu của Bảng 33 chỉ quan sát được qua tích của chúng.

Vòng thứ năm vẫn ngã ngửa. Lúc đó nghi phạm hiển nhiên là hệ số PID, và cả tác tử lẫn tôi đều
đã từng nghi nó.

Rồi anh Công đưa vào gói **V1 của nhà cung cấp** — firmware người viết, đã đứng được trên
chính loại phần cứng này. Nạp V1: **robot đứng rất tốt**. Một phép đo, và nó chốt được thứ
không phép đo nào trước đó chốt nổi: phần cứng, jack động cơ, IMU, nguồn **đều tốt** — nên mọi
lỗi còn lại nằm trong phần mềm.

Đối chiếu từng tham số V1 với firmware của ta tìm ra **bảy** chỗ lệch:

| | firmware của ta | V1 (đã đứng được) |
|---|---|---|
| Hiệu chuẩn gia tốc | `− (−535)` = **+535** | **+92**, phép cộng |
| Chiều DIR bánh trái (D6) | thr>0 → CAO | thr>0 → **THẤP** |
| Chiều DIR bánh phải (D4) | thr>0 → THẤP | thr>0 → **CAO** |
| Bước tự chỉnh mốc thăng bằng | 0,0015 | **0,002** |
| Bù trôi khi xoay | không có | **`−gyro_x × 0,0000003`** |
| Cửa sổ kích hoạt | 2,0° (bị `control.c` che) | **0,5°** |
| Ngắt động cơ khi pin yếu | chưa có | **ADC A0 < 420** |

Chỗ nặng nhất là hằng số hiệu chuẩn: **535 thay vì 92**, tức **3,1° điểm cân bằng giả**. Robot
đuổi một tư thế nó không giữ được, nên nó vọt qua rồi ngã. Đó đúng là "phản ứng rất mạnh rồi
ngã ngay" mà anh Công thấy.

Còn hệ số PID — nghi phạm ai cũng nghĩ tới trước — thì **V1 dùng đúng `12 / 0,4 / 10`, y hệt
ta vẫn để**. Nó chưa bao giờ là thủ phạm. Không có mốc đối chứng thì ba bên đã cùng nhau hạ hệ
số PID và đi sai hướng thêm vài vòng cắm mạch nữa.

Sau khi đồng bộ bảy tham số, firmware của tác tử **đứng rất tốt**.

---

## 5 · Kết luận

**Tác tử không thay được người ở bài này.** Nó cũng không chỉ là công cụ gõ nhanh.

Chỗ nó thật sự đổi được cục diện: **nó làm những phép đo mà người sẽ bỏ.** Đọc ngược flash 32
lần. Dựng bảng tra 109 hạng mục rồi đối chiếu lại sau mỗi lần sửa. Ghi 249 changeset hoàn tác
được. Giữ nguyên văn 1 415 lời gọi mô hình. Không phải vì nó cẩn thận hơn người — mà vì nó
**không mỏi**, và mỏi là lý do người bỏ bước.

Chỗ nó không làm được, và phiên này chứng minh khá dứt khoát:

1. **Nó không tự biết nó sai.** Tám lỗi, không lỗi nào do nó tự tìm ra. Mọi báo cáo "đã xong,
   verified, 0 byte lệch" đều có thể đúng về lời gọi và sai về kết quả.
2. **Bài kiểm nó tự viết thì xanh sẵn.** Ba lần liên tiếp. Phải có người phá mã sản phẩm rồi
   đòi bài kiểm phải đỏ, mới có phép đo thật.
3. **Nó không chạm được vào thế giới.** Ba dấu của Bảng 33 và ba hằng số hạng L chỉ ra được
   khi có người dựng robot lên và nói nó ngã về phía nào.

Nên hình dung đúng không phải "tác tử thay người", mà là: **tác tử gánh phần ghi chép và phần
kỷ luật, người giữ phần phán đoán và phần chạm vào vật thật.** Và vai thứ ba hoá ra quan trọng
không kém: **một bản đã chạy được**, dùng làm mốc đối chứng. V1 làm trong một lần nạp cái việc
mà năm vòng chẩn đoán chưa làm nổi — nó chia đôi không gian lỗi, phần cứng sang một bên, phần
mềm sang bên kia.

Ba câu đã thành thói quen trong dự án này, phiên robot kiểm lại cả ba và cả ba đều đúng:

> **`ok` nói về lời gọi, không nói về kết quả.**
>
> **Một phép đo xanh bất kể sản phẩm đúng hay sai thì nó không đo gì cả.**
>
> **Một ô xanh chưa nói gì tới khi biết cơ chế nào làm nó xanh.**

---

## 6 · Hiện vật kiểm chứng được

Mọi con số trong báo cáo này tra lại được, không cần tin bản kể lại:

| Thư mục | Nội dung |
|---|---|
| [`firmware/`](firmware/) | 1 820 dòng C, 10 mô-đun, kèm `mach.elf` · `mach.hex` đã nạp |
| [`sim/`](sim/) | mô phỏng và hai bài kiểm **biên dịch chính mã firmware** |
| [`ncc/`](ncc/) | gói V1 nhà cung cấp — mốc đối chứng đã đứng được |
| [`BANG-TRA-TUAN-THU.md`](BANG-TRA-TUAN-THU.md) | 109 hạng mục dựng từ tài liệu |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | sổ cái 16 666 sự kiện · 249 changeset · transcript |
| [`nhat-ky-llm/`](nhat-ky-llm/) | **1 415 lời gọi mô hình**, nguyên văn trả về và lượt gửi mới |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký 65 bước · 65 ảnh chụp cửa sổ EIDE |

Nhật ký LLM thu từ 1,2 GB xuống 1,0 MB bằng cách lưu lời nhắc hệ thống và danh mục công cụ
**một lần** thay vì 1 415 lần — phần nguyên văn trả về và lượt gửi mới giữ đủ, không cắt.
