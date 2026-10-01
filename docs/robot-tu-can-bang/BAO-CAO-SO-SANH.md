# Robot hai bánh tự đứng — Agent làm được gì, chỗ nào vẫn cần người, mất bao lâu, tốn bao nhiêu

*Phiên ngày 01/10/2026. Robot đứng được lúc kết phiên.*

Báo cáo này so việc Agent của EIDE làm phần mềm giúp robot đứng, với việc một đội người làm
tay cùng đề bài — đủ bốn khâu: phân tích, thiết kế, viết mã, kiểm thử.

Nó không phải bài quảng cáo. Trong phiên này Agent sai nhiều lần, và những chỗ sai nói về giá
trị của nó rõ hơn những chỗ đúng.

---

## 1 · Đề bài khó ở đâu

Phụ lục B.1 của tập tài liệu phần cứng ghi rõ đã **bỏ hẳn** phần chương trình mẫu: vòng điều
khiển, bộ lọc góc, cách chốt điểm thăng bằng, PID. Phần còn lại **chỉ có điều kiện bắt buộc về
phần cứng** — chân nào nối đâu, thanh ghi nào đặt gì, nhịp bao nhiêu, và một bảng kê những
cách viết bị cấm.

Nên không có lời giải để chép. Thêm ba thứ làm bài này khó hơn vẻ ngoài:

- **Vi điều khiển 8 bit, 2 KB SRAM.** §12.7 cấm số thực và phép chia trong ngắt 50 kHz.
- **Ba dấu cộng trừ không đo riêng được.** §11.5 Bảng 33 có ba dấu — dấu của cảm biến `s`, dấu
  do cách lắp động cơ `k`, dấu của đầu ra điều khiển `u`. Khi robot đứng yên thì **chỉ nhân ba
  dấu lại mới đo được**, từng dấu riêng thì không. Đọc mã bao nhiêu cũng không tách ra; phải
  dựng robot lên mới biết.
- **Ba con số phải đo trên từng bo một**: điểm cân bằng của cảm biến gia tốc, độ lệch tĩnh của
  cảm biến góc, hệ số cầu chia đo pin. Không bo nào giống bo nào.

---

## 2 · Số đo của phiên

| | |
|---|---|
| Firmware | **1 820 dòng C**, 10 mô-đun, cho ATmega328P |
| Ảnh nhị phân | **13 056 B** Flash / 32 KB · **634 B** SRAM / 2 KB |
| ISR 50 kHz | **35 lệnh · 0 lời gọi hàm · 0 số thực · 0 phép chia** — đúng điều §12.7 cấm |
| Sổ ghi việc | **16 666 dòng**, kiểm được là chưa ai sửa dòng nào |
| Lời gọi công cụ | **1 108** (1 019 chạy được · 89 báo lỗi) · **45 công cụ** khác nhau |
| Lần sửa có ghi | **249**, mỗi lần gỡ lại được |
| Lời gọi mô hình | **1 415**, tất cả `gemini-3.8-flash`, không một lời gọi nào khác |
| Token | vào **292,48 triệu** (trong đó **273,80** đọc lại từ đệm) · ra **0,86 triệu** |
| Bảng điều kiện bắt buộc | **109 mục** dựng từ tài liệu, đối chiếu lại sau mỗi lần sửa |

Hàm ngắt dùng bộ đếm pha số nguyên 32 bit. Đây là điều kiện khó nhất trong tài liệu, và nó
**kiểm được bằng cách dịch ngược tệp ảnh ra lệnh máy** — không phải tin lời ai.

---

## 3 · So với người làm tay

Tách làm hai loại việc, vì Agent mạnh yếu rất khác nhau giữa chúng.

### 3.1 · Việc tay chân — Agent nhanh hơn nhiều

| Việc | Người làm tay | Agent |
|---|---|---|
| Đọc tập tài liệu, lập bản đồ chân | nửa ngày tra chéo | trong một lượt |
| Dò 109 điều kiện rải khắp 13 chương | dễ sót, không ai kê đủ | **bảng 109 mục**, đối chiếu lại mỗi lần sửa |
| Tra thanh ghi TWI, Timer2, ADC của ATmega328P | tra tài liệu từng thanh ghi | viết đúng, có ghi chỗ lấy |
| Ghi lại ai sửa gì vì sao | hiếm khi làm nổi | **249 lần sửa**, gỡ lại được |
| Dịch mã, nạp, đọc ngược so từng byte | làm tay, dễ bỏ bước | **32 lần nạp, 32 lần đọc ngược**, tự làm |
| Viết tài liệu vận hành và bản sửa lỗi tài liệu | thường bỏ qua | viết kèm, khớp với mã |

Ở loại việc này khoảng cách là **giờ so với phút**, và quan trọng hơn: Agent **không bỏ bước vì
mỏi**. Người làm tay đến lần nạp thứ hai mươi sẽ thôi đọc ngược để so. Agent đọc ngược cả 32
lần.

### 3.2 · Việc phải tự xét — Agent báo xong trong khi đang sai

Đây là phần phải nói thẳng. Trong phiên này Agent sai những chỗ sau, **mỗi chỗ đều kèm một báo
cáo tự nhận là đã xong**:

| Agent làm gì | Vì sao sai | Ai bắt được |
|---|---|---|
| Tắt động cơ bằng chân `ENABLE = HIGH` ở bốn trạng thái | chính nó đã đọc ra "EN kéo xuống GND" ở lượt trước | người chất vấn |
| Chạy thử trên máy báo **6/6 đạt** khi đã đảo dấu khâu P | không về được điểm cân bằng thì biến đo giữ `0.0`, mà `0 ≤ 2,0 s` nên bị tính là đạt | sửa hỏng mã rồi đo lại |
| `"dat": true` **viết cứng** trong `printf` | chương trình in kết luận bất kể số đo | đọc mã |
| Bỏ yêu cầu FR-01 "đèn nháy" mà không báo ai | lý do kỹ thuật đúng, nhưng kho ghi một đằng mã làm một nẻo | đối chiếu bản ghi yêu cầu với mã |
| Báo "nạp xong, đã kiểm, 0 byte lệch" | nạp **sai tệp**; `avrdude` so với đúng cái tệp nó được đưa, nên vẫn báo đã kiểm | mở cổng nối tiếp đọc xem bo chạy gì |
| Ba bộ kiểm liên tiếp **chép logic sang tệp kiểm** | báo đạt bất kể mã sản phẩm đúng hay sai | sửa hỏng mã sản phẩm rồi chạy lại bộ kiểm |
| Đoán ra chip MPU-6500 từ một con số `0x72`, rồi đặt thanh ghi không có tác dụng mà vẫn báo OK | một con số lạ chưa đủ để kết luận lại về phần cứng | đọc lại thanh ghi |
| Khẳng định còi là loại cần cấp xung | §10.1 ghi rõ "không cần PWM" | tra tài liệu |

Điểm chung của tám dòng trên: **không dòng nào do Agent tự tìm ra.** Tất cả đều do một phép đo
do người thiết kế, hoặc do người đọc mã rồi hỏi lại.

Và một chi tiết đáng ghi hơn cả: ba lần liên tiếp Agent viết bộ kiểm cho đúng chỗ nó vừa sửa,
và cả ba lần bộ kiểm chỉ **chép lại logic** sang tệp kiểm rồi so logic với chính nó. Lần cuối,
sau khi bị bắt viết lại cho bộ kiểm **dùng thẳng mã sản phẩm**, sáu phép sửa hỏng đều làm bộ
kiểm báo lỗi đúng lúc phải báo. **Agent biết cách làm đúng. Nhưng mặc định của nó vẫn là làm
sai.**

---

## 4 · Chỗ quyết định: robot chỉ đứng sau khi có một bản chạy được để so

Đây là kết luận quan trọng nhất của phiên.

Bốn lần cắm bo đầu, anh Công lần lượt báo: *robot không làm gì, hai bánh khoá cứng* → *một
tiếng bíp rồi bánh trái quay ngược* → *lực rất yếu, ngã về trước* → *đã có chuyển động nhưng
gằn và xoay lùi*. Mỗi lần nhìn như vậy trả lời đúng **một** câu hỏi, và không lượng đọc mã nào
thay được — vì ba dấu của Bảng 33 chỉ đo được khi nhân chúng lại.

Lần thứ năm vẫn ngã ngửa. Lúc đó chỗ bị nghi là hệ số PID, và cả Agent lẫn tôi đều từng nghi
nó.

Rồi anh Công đưa vào gói **V1 của nhà cung cấp** — phần mềm người viết, đã đứng được trên chính
loại phần cứng này. Nạp V1: **robot đứng rất tốt**. Một lần nạp đó chốt được thứ mà năm lần
trước không chốt nổi: phần cứng, jack động cơ, cảm biến, nguồn **đều tốt** — nên lỗi còn lại
nằm trong phần mềm.

Đối chiếu từng con số của V1 với phần mềm của Agent tìm ra **bảy** chỗ lệch:

| | phần mềm của Agent | V1 (đã đứng được) |
|---|---|---|
| Số chỉnh chuẩn gia tốc | `− (−535)` = **+535** | **+92**, phép cộng |
| Chiều DIR bánh trái (D6) | thr>0 → CAO | thr>0 → **THẤP** |
| Chiều DIR bánh phải (D4) | thr>0 → THẤP | thr>0 → **CAO** |
| Bước tự chỉnh điểm thăng bằng | 0,0015 | **0,002** |
| Bù độ trôi khi xoay | không có | **`−gyro_x × 0,0000003`** |
| Khoảng góc để bắt đầu giữ cân bằng | 2,0° (bị `control.c` ghi đè) | **0,5°** |
| Ngắt động cơ khi pin yếu | chưa có | **ADC A0 < 420** |

Chỗ nặng nhất là số chỉnh chuẩn: **535 thay vì 92**, tức điểm cân bằng sai **3,1 độ**. Robot
đuổi một thế đứng mà nó không giữ được, nên nó vọt qua rồi ngã. Đó đúng là "phản ứng rất mạnh
rồi ngã ngay" mà anh Công thấy.

Còn hệ số PID — chỗ ai cũng nghĩ tới trước — thì **V1 dùng đúng `12 / 0,4 / 10`, y hệt con số
Agent vẫn để**. Nó chưa bao giờ là nguyên nhân. Không có bản chạy được để so thì cả ba bên đã
cùng nhau hạ hệ số PID và đi sai hướng thêm vài lần cắm bo nữa.

Sau khi sửa bảy con số, phần mềm của Agent **đứng rất tốt**.

---

## 5 · Thời gian và tiền: đo được bên này, ước lượng bên kia

Hai cột dưới đây **không cùng loại số**, nên nói trước cho rõ: cột Agent là **đo được** từ sổ
ghi việc và nhật ký mô hình; cột người là **ước lượng** theo phương pháp PERT, kiểm chéo bằng
COCOMO. Trộn hai loại vào một bảng mà không nói thì bảng đó nói sai.

### 5.1 · Phiên Agent — những con số đo được

| | |
|---|---|
| Thời gian từ đầu tới cuối | **7,4 giờ** (01/10, 08:56 → 16:19) — dưới một ngày làm việc |
| Số lượt người gõ | **116** |
| Lời gọi mô hình | **1 415**, tất cả `gemini-3.8-flash` |
| Token vào mới · đọc lại từ đệm · ra | **18,69 triệu** · **273,80 triệu** · **0,86 triệu** |
| Thời gian chờ mô hình | **115 phút** trong 7,4 giờ đó |
| Lời gọi công cụ | **1 108** (1 019 chạy được · 89 báo lỗi) |
| Lần sửa có ghi | **249**, mỗi lần gỡ lại được |

Phần lớn token là **đọc lại từ đệm** — 93,6 % — vì mỗi lượt gửi lại cả đoạn hội thoại đã có.
Token loại này rẻ hơn nhiều, nên nó đổi hẳn con số tiền.

Kho không lưu bảng giá, nên tiền trình bày dưới dạng **công thức kèm tham số**, thay đơn giá
thật trong hoá đơn vào là có số cuối:

| Kịch bản đơn giá (USD / triệu token) | Vào mới | Đệm | Ra | **Tiền cả phiên** |
|---|---|---|---|---|
| A — mức thấp | 0,075 | 0,019 | 0,30 | **≈ 6,9 USD · 172 nghìn đồng** |
| **B — mức giữa** | 0,15 | 0,0375 | 0,60 | **≈ 13,6 USD · 340 nghìn đồng** |
| C — mức cao | 0,30 | 0,075 | 2,50 | **≈ 28,3 USD · 707 nghìn đồng** |

*(quy đổi 25 000 đồng/USD, cùng tỉ giá đã dùng cho phiên viết hệ điều hành để hai việc so được
với nhau)*

### 5.2 · Nếu người làm tay — ước lượng từng việc

Đủ bốn khâu: phân tích, thiết kế, viết mã, kiểm thử. Mỗi dòng có ba mức — nhanh nhất, thường
gặp, chậm nhất — rồi lấy theo PERT: `(nhanh + 4 × thường + chậm) / 6`.

| Việc | Vai | Nhanh | Thường | Chậm | **Ngày công** |
|---|---|---|---|---|---|
| Đọc 13 chương tài liệu phần cứng, lập bản đồ chân | Senior | 1 | 2 | 4 | **2,17** |
| Dựng bảng 109 điều kiện bắt buộc, đối chiếu được | Mid | 1 | 2 | 4 | **2,17** |
| Thiết kế: ba cách dựng, so bằng số, chốt cấu trúc ba tầng | Senior | 1 | 2 | 4 | **2,17** |
| Thiết kế máy trạng thái vận hành và các bước bấm nút | Mid | 0,5 | 1 | 2 | **1,08** |
| Hàm ngắt 50 kHz: 0 số thực, 0 phép chia | Senior | 1 | 3 | **8** | **3,50** |
| Driver I2C, MPU6050, lọc góc | Mid | 1 | 2 | 4 | **2,17** |
| PID và mô hình throttle phi tuyến | Senior | 1 | 2 | 5 | **2,33** |
| Máy trạng thái, nút, còi, đo pin bằng ADC | Mid | 1 | 2 | 3 | **2,00** |
| Chương trình chạy thử trên máy và bộ mức đo | Mid | 1 | 2 | 4 | **2,17** |
| **Gỡ lỗi trên bo: ba dấu Bảng 33 và ba hằng số theo từng bo** | Senior | 2 | 5 | **12** | **5,67** |
| Kênh chẩn đoán UART, đo bằng máy hiện sóng | Mid | 0,5 | 1 | 3 | **1,25** |
| Bộ kiểm đơn vị và đo độ nhạy bộ kiểm | QA | 1 | 2 | 4 | **2,17** |
| Tài liệu: yêu cầu, thiết kế, vận hành, hiệu đính phần cứng | Mid | 1 | 2 | 4 | **2,17** |
| **TỔNG** | | **13** | **28** | **61** | **31,0 ngày công** |

Hai dòng có mức chậm nhất **gấp bốn đến sáu lần** mức nhanh nhất, và đó là hai chỗ rủi ro thật:

- **Hàm ngắt 50 kHz** (1 → 8). Tài liệu cấm số thực và phép chia trong hàm ngắt này. Ai chưa
  từng viết bộ tích luỹ pha nguyên thì sẽ mất vài vòng thử.
- **Gỡ lỗi trên bo** (2 → 12). Đây là dòng đáng chú ý nhất, và trong phiên thật nó **đã rơi về
  phía mức chậm**: mười vòng cắm bo, và vẫn chưa xong tới khi có một bản chạy được để so sánh.

Độ lệch chuẩn PERT **±2,6 ngày**:

| Mức tin | Khoảng |
|---|---|
| ~68 % | **28 – 34 ngày công** |
| ~95 % | **26 – 36 ngày công** |

### 5.3 · Cần mấy người, và bao lâu theo lịch

| Vai | Ngày công | Phần |
|---|---|---|
| Kỹ sư nhúng **Senior** | **15,8** | 51 % |
| Kỹ sư nhúng **Mid** | 13,0 | 42 % |
| **QA** nhúng | 2,2 | 7 % |
| Quản lý dự án (20 % thời lượng) | 6,2 | — |

Đội ít nhất: **1 Senior + 1 Mid + QA một phần + quản lý 20 %**.

**Thời gian theo lịch khoảng 4 tuần.** Senior là chỗ không chia việc được: 15,8 ngày công của
người này phải làm nối tiếp nhau — đọc tài liệu rồi mới thiết kế được, thiết kế rồi mới viết
hàm ngắt được, có mã rồi mới gỡ lỗi trên bo được. Thêm người thứ ba **không rút ngắn** phần
này.

### 5.4 · Tiền nhân sự

Đơn giá tính theo lương tháng thị trường Việt Nam (triệu đồng), chia 21 ngày làm việc, nhân
**1,4** cho bảo hiểm, chỗ ngồi, thiết bị và chi phí quản lý:

| Vai | Thấp | Giữa | Cao |
|---|---|---|---|
| Senior nhúng | 40 | 55 | 70 |
| Mid nhúng | 20 | 27 | 35 |
| QA nhúng | 15 | 20 | 25 |
| Quản lý dự án | 35 | 50 | 65 |

| Kịch bản | Tiền phát triển | Kèm quản lý | Quy đổi |
|---|---|---|---|
| Thấp | 61,7 triệu | **≈ 76 triệu** | ≈ 3 050 USD |
| **Giữa** | **84,3 triệu** | **≈ 105 triệu** | ≈ 4 200 USD |
| Cao | 107,8 triệu | **≈ 135 triệu** | ≈ 5 390 USD |

### 5.5 · Kiểm chéo bằng COCOMO — và vì sao nó ra cao hơn

COCOMO cơ bản trên **1,820 KSLOC** phần mềm giao ra:

| Chế độ | Người-tháng | Ngày công | Tháng lịch |
|---|---|---|---|
| Organic | 4,50 | **94,5** | 4,4 |
| Embedded | 7,39 | **155,1** | 4,7 |

COCOMO cho **95 – 155 ngày công**, tức **gấp 3 đến 5 lần** con số PERT (31). Chênh lệch đó có
lý do, và nói ra thì có ích hơn là chọn con số mình thích:

- COCOMO tính **trọn vòng đời công nghiệp**: bản ghi yêu cầu chính thức, rà soát chéo, kiểm thử
  cả hệ thống, tài liệu giao hàng, bảo trì đầu kỳ. Phần lớn những thứ ấy không nằm trong phạm
  vi việc này.
- Nó được chuẩn trên **dự án lớn**, và được biết là **ước lượng thừa cho dự án rất nhỏ** — dưới
  2 KSLOC thì phần hệ số cố định lấn át.
- Robot dùng lại driver và thư viện có sẵn; COCOMO tính theo số dòng giao ra, không trừ phần
  dùng lại.

Nên lấy **PERT làm số chính**, và đọc COCOMO như **mức trần**: nếu đội chưa từng viết hàm ngắt
ở mức thanh ghi trên AVR, con số thật sẽ trôi về phía 60 – 90 ngày hơn là 31.

### 5.6 · Đặt hai cột cạnh nhau

| | Người làm tay (ước lượng) | Phiên Agent (đo được) |
|---|---|---|
| Thời gian | **31,0 ngày công ±2,6** · khoảng **4 tuần** lịch | **7,4 giờ**, một buổi |
| Nhân lực | 1 Senior + 1 Mid + QA + quản lý | **1 người** + Agent |
| Tiền | **≈ 105 triệu đồng** (mức giữa) | **≈ 340 nghìn đồng** tiền mô hình |
| Có phần mềm đứng được không | có | **có** |
| Bảng 109 điều kiện bắt buộc | mất thêm 2,2 ngày công | sinh kèm |
| Ghi vết từng lần sửa, gỡ lại được | thường không làm nổi | **249 lần sửa**, đều gỡ lại được |
| Nguyên văn từng lời gọi mô hình | — | **1 415 lời gọi**, giữ đủ |

Nói gọn: **31 ngày công của một đội so với 7,4 giờ của một người**, và **105 triệu so với 340
nghìn** — chênh khoảng **300 lần về tiền** và **30 lần về giờ công**.

### 5.7 · Bốn điều hai cột trên KHÔNG chứng minh

Phải nói ra, nếu không bảng trên sẽ bị đọc quá tay.

1. **Người vẫn nằm trên đường quyết định, và không rút ngắn được phần đó.** Cả mười vòng cắm bo
   đều cần anh Công dựng robot lên rồi nói nó ngã về phía nào. Agent không chạm được vào robot.
   Bảy giờ rưỡi ấy **không phải bảy giờ rưỡi của riêng Agent** — phần lớn là chờ người thử.
2. **Bước cuối dùng một bản đã chạy được để so sánh.** Nếu không có nó thì phiên này còn kéo
   dài, vì chỗ ai cũng nghĩ tới trước là hệ số PID — mà PID lại không có lỗi gì. Dòng *gỡ lỗi trên
   bo* trong bảng PERT (2 → 12 ngày) đã tính cả hai trường hợp: có bản để so và không có.
3. **340 nghìn đồng không phải toàn bộ chi phí.** Chưa tính giờ của anh Công, chưa tính phần
   cứng, chưa tính thời gian dựng EIDE.
4. **Tám chỗ Agent báo xong trong khi đang sai đều cần một phép đo do người thiết kế mới bắt
   được.** Thời gian rà soát đó nằm **trong** 7,4 giờ, không phải thêm vào — nhưng nó cần một
   người biết phải đo cái gì. Giao cho người không biết nghi chỗ nào thì tám chỗ ấy sẽ lọt, và
   robot sẽ không đứng.

---

## 6 · Kết luận

**Agent không thay được người ở bài này.** Nó cũng không chỉ là công cụ gõ mã nhanh.

Chỗ nó thật sự đổi được cục diện: **nó làm những phép đo mà người sẽ bỏ.** Đọc ngược chip 32
lần. Dựng bảng 109 điều kiện rồi đối chiếu lại sau mỗi lần sửa. Ghi 249 lần sửa đều gỡ lại
được. Giữ nguyên văn 1 415 lời gọi mô hình. Không phải vì nó cẩn thận hơn người, mà vì nó
**không mỏi** — và mỏi là lý do người bỏ bước.

Và nó rẻ hơn rất nhiều ở phần làm được: **340 nghìn đồng trong 7,4 giờ**, so với ước lượng
**105 triệu đồng trong 4 tuần** nếu một đội làm tay cả bốn khâu.

Chỗ nó không làm được, và phiên này cho thấy khá rõ:

1. **Nó không tự biết nó sai.** Tám lỗi, không lỗi nào do nó tự tìm ra. Mọi câu "đã xong, đã
   kiểm, 0 byte lệch" đều có thể đúng về lời gọi và sai về kết quả.
2. **Bộ kiểm nó tự viết thì báo đạt sẵn.** Ba lần liên tiếp. Phải có người sửa hỏng mã sản phẩm
   rồi đòi bộ kiểm phải báo lỗi, mới có phép đo thật.
3. **Nó không chạm được vào thế giới.** Ba dấu của Bảng 33 và ba con số đo theo từng bo chỉ ra
   được khi có người dựng robot lên và nói nó ngã về phía nào.

Nên hình dung đúng không phải "Agent thay người", mà là: **Agent gánh phần ghi chép và phần làm
đủ bước, người giữ phần phán đoán và phần chạm vào vật thật.** Và có một vai thứ ba cũng quan
trọng: **một bản đã chạy được, dùng để so.** V1 làm trong một lần nạp cái việc mà năm lần cắm
bo trước không làm nổi — nó chia đôi chỗ cần tìm lỗi: phần cứng sang một bên, phần mềm sang bên
kia.

Và về mặt tiền, điều này có nghĩa là: con số 340 nghìn đồng **chỉ đúng khi có người biết phải
nghi chỗ nào**. Giao cùng việc đó cho người không biết đặt phép đo thì tám chỗ sai sẽ lọt hết,
và robot sẽ không đứng — lúc ấy 340 nghìn đồng mua được một phần mềm trông như đã xong.

Ba câu đã thành thói quen trong dự án này, phiên robot kiểm lại cả ba và cả ba đều đúng:

> **Câu "chạy được" chỉ nói về lời gọi, không nói về kết quả.**
>
> **Một phép đo báo đạt bất kể sản phẩm đúng hay sai thì nó không đo gì cả.**
>
> **Một kết quả đạt chưa nói gì tới khi biết cơ chế nào làm nó đạt.**

---

## 7 · Những tệp để kiểm lại

Mọi con số trong báo cáo này tra lại được, không cần tin bản kể lại:

| Thư mục | Nội dung |
|---|---|
| [`firmware/`](firmware/) | 1 820 dòng C, 10 mô-đun, kèm `mach.elf` và `mach.hex` đã nạp |
| [`sim/`](sim/) | chương trình chạy thử và hai bộ kiểm **dùng thẳng mã sản phẩm** |
| [`ncc/`](ncc/) | gói V1 của nhà cung cấp — bản đã đứng được, dùng để so |
| [`BANG-TRA-TUAN-THU.md`](BANG-TRA-TUAN-THU.md) | 109 điều kiện bắt buộc dựng từ tài liệu |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | sổ ghi việc 16 666 dòng · 249 lần sửa · bản ghi từng phiên |
| [`nhat-ky-llm/`](nhat-ky-llm/) | **1 415 lời gọi mô hình**, giữ nguyên văn phần trả về và lượt gửi mới |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký 65 bước · 65 ảnh chụp cửa sổ EIDE |

Nhật ký mô hình thu từ 1,2 GB xuống 1,0 MB bằng cách lưu lời nhắc hệ thống và danh sách công cụ
**một lần** thay vì 1 415 lần. Phần trả về và lượt gửi mới giữ đủ, không cắt.
