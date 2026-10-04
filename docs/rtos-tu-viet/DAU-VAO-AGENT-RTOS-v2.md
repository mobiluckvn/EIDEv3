# Giao việc: tự viết một hệ điều hành thời gian thực, bỏ FreeRTOS

Chào bạn. Mình là sinh viên đang làm đồ án về lập trình nhúng. Việc này mình nhờ bạn làm cùng
mình từ đầu tới cuối: **viết lấy một hệ điều hành thời gian thực nhỏ, rồi thay FreeRTOS trong
một dự án đang chạy được bằng nó.**

Mình viết tài liệu này cho bạn thực hiện, nên mình cố gắng nói rõ **mình cần gì** và **cái gì
đã chắc chắn** — còn **làm thế nào** thì phần lớn là việc của bạn.

---

## 1 · Mình ở đâu trong việc này

Mình là sinh viên, không phải người đã làm nhúng nhiều năm. Nói thẳng để bạn khỏi phải đoán:

- Mình **đọc hiểu được** mã C, sơ đồ chân, và tài liệu chip khi có người chỉ chỗ.
- Mình **chưa từng** viết bộ lập lịch, chưa từng viết chuyển ngữ cảnh bằng hợp ngữ, và chưa
  từng gỡ lỗi màn hình DSI.
- Mình **không đủ trình để soát từng dòng mã của bạn**. Nên thứ mình dựa vào là **số đo** và
  **chỗ bạn trích dẫn**, không phải cảm giác mã trông có đúng không.
- Mình **cắm bo và nhìn bo hộ bạn**. Bạn bảo mình nhìn gì thì mình nhìn và nói lại đúng điều
  mình thấy. Mình không tự suy ra nguyên nhân.

Vì vậy mình cần bạn làm một điều suốt cả việc: **mỗi lần bạn nói một việc đã xong, kèm theo
phép đo nào chứng minh điều đó, và chỗ lấy số.** Câu "đã biên dịch xong" không giúp mình; câu
"ảnh ra 259 488 byte, trong đó có đủ 15 tệp, đây là danh sách" thì giúp.

---

## 2 · Đề bài

Có một dự án **đang chạy được** trên kit STM32F469I-DISCO: màn hình DSI 800×480, cảm ứng điện
dung, sáu việc chạy song song, dùng **FreeRTOS v10**.

Việc của bạn: **bỏ hẳn FreeRTOS, viết lấy nhân thời gian thực của mình, và dự án phải chạy
đúng như trước.**

Đây không phải bài tập viết thêm tính năng. Nó là bài tập **thay một thứ đang chạy bằng một thứ
mình tự làm, mà không được làm hỏng thứ đang chạy** — nên phép đo quan trọng hơn mã.

### Vì sao mình chọn việc này

Vì nó có một mốc so sánh **không thể tranh luận**: bản cũ chạy được, nên bản mới chạy sai là
thấy ngay. Và vì nhân thời gian thực là chỗ **sai một chút là treo hẳn**, không sai nhẹ.

---

## 3 · Phần cứng — số ở đây mình đã tra, bạn dùng được luôn

Mình tra những con số này từ dự án đang chạy và từ linker script, không phải nhớ lại. Chỗ nào
mình **không chắc** thì mình ghi rõ là không chắc.

| | giá trị | mình lấy ở đâu |
|---|---|---|
| Vi điều khiển | STM32F469NI, lõi Cortex-M4F | nhãn trên chip và tên linker script |
| Flash | **2 048 KB** tại `0x08000000` | `stm32f469ni.ld` mục `MEMORY` |
| RAM nội | **320 KB** tại `0x20000000` | `stm32f469ni.ld` mục `MEMORY` |
| Đỉnh ngăn xếp ban đầu | `ORIGIN(RAM) + LENGTH(RAM)` | `stm32f469ni.ld` dòng `_estack` |
| Nguồn xung nhịp ngoài | HSE | mã cấu hình xung nhịp |
| Xung nhịp hệ thống | **180 MHz** | PLL cấu hình như dưới |
| PLL chính | `PLLM = 8` · `PLLN = 360` · `PLLP = ÷2` · `PLLQ = 7` · `PLLR = 6` | thanh ghi `RCC->PLLCFGR` trong mã đang chạy |
| Màn hình | DSI 800×480, IC điều khiển **OTM8009A** | chuỗi hiện trên màn bản cũ |
| Cảm ứng | điện dung, IC **FT6206**, giao tiếp I2C | mã driver cảm ứng |
| Nút bấm người dùng | **PA0** | mã quét nút |
| SDRAM dùng làm bộ đệm khung | có, bản cũ dùng | mã khởi tạo giao diện |

**Chỗ mình không chắc, bạn tự xác định rồi ghi lại:**

- Giao tiếp I2C với IC cảm ứng ở bản cũ **không dùng ngoại vi I2C của chip** mà tự lắc chân.
  Mình không biết tần số bao nhiêu là đúng ở 180 MHz, cũng không biết nên đổi sang ngoại vi
  I2C thật hay giữ cách lắc chân. Bạn quyết, và nói lý do.
- Mình **không biết** ngăn xếp mỗi tác vụ cần bao nhiêu. Bản cũ đặt một con số, nhưng mình
  không biết con số ấy có dư hay có thiếu. Bạn tự chọn, và **đo** chứ đừng đoán.

---

## 4 · Nhân thời gian thực — mình cần những gì

Mình nêu **yêu cầu**, không nêu cách làm. Bạn thấy cách khác tốt hơn thì làm, nhưng phải nói ra.

### 4.1 · Lập lịch

- **Tiền định theo mức ưu tiên** — tác vụ ưu tiên cao hơn mà sẵn sàng thì phải chiếm CPU ngay,
  không chờ tác vụ đang chạy nhường.
- Có **đủ 32 mức ưu tiên**, trong đó mức thấp nhất dành cho tác vụ rỗi.
- Chịu được **tối thiểu 16 tác vụ**.
- Nhịp hệ thống **1 000 Hz** (một nhịp mỗi mili-giây).

### 4.2 · Chuyển ngữ cảnh

Đây là chỗ mình biết là khó nhất và mình không kiểm được bằng mắt, nên mình nêu rõ ràng buộc:

- Chuyển ngữ cảnh phải xảy ra trong ngắt **PendSV**, không xảy ra trong `SysTick`.
- Lõi này **có bộ xử lý số thực**. Khung ngăn xếp khi có dùng số thực **khác** khung thường, và
  giá trị `EXC_RETURN` cũng khác. Nếu bạn làm sai chỗ này thì nó chạy đúng cho tới khi một tác
  vụ nào đó dùng số thực, rồi treo — nên bạn phải xử lý cả hai khung, và **nói cho mình biết
  bạn phân biệt chúng bằng cách nào**.
- Tác vụ chạy ở **Thread mode dùng con trỏ ngăn xếp tiến trình (PSP)**; nhân và ngắt dùng con
  trỏ ngăn xếp chính (MSP).
- Khi dựng ngăn xếp cho một tác vụ mới, thanh ghi trạng thái ban đầu phải có **bit Thumb** bật.

### 4.3 · Truyền tin giữa các tác vụ

- Một kiểu **hàng đợi** là đủ, nhưng phải có:
  - **cấp phát tĩnh** — không cấp phát động ở đâu trong nhân. Mình muốn biết trước lúc dịch là
    nó tốn bao nhiêu RAM.
  - **chờ có thời hạn** — gửi và nhận đều phải nêu được "chờ tối đa bao nhiêu nhịp", và phải
    phân biệt được *nhận được* với *hết thời hạn*.
- Một tác vụ đang chờ hàng đợi thì **không được chiếm CPU**.

### 4.4 · Trễ

- `trễ bao nhiêu mili-giây` — và trong lúc trễ thì tác vụ **không chiếm CPU**.
- Mình cần bạn chú ý một chỗ: trong dự án có những đoạn khởi tạo phần cứng **có ràng buộc thời
  gian cứng**, mà chúng đang gọi hàm trễ của thư viện phần cứng. Nếu hàm trễ ấy nhường CPU thì
  đoạn khởi tạo bị chen ngang. Mình nêu ra để bạn cân nhắc, **không phải để bạn chữa theo cách
  mình nghĩ** — bạn tự quyết.

### 4.5 · Những thứ mình KHÔNG đòi

Nói ra để bạn khỏi làm thừa:

- Không cần cấp phát bộ nhớ động.
- Không cần mutex, semaphore, event group, timer mềm — trừ khi dự án cần mới làm.
- Không cần hỗ trợ nhiều lõi.
- Không cần tương thích API của FreeRTOS. Bạn đặt tên hàm theo ý bạn.

---

## 5 · Sáu việc phải chạy song song

Dự án cũ có sáu việc. Bản mới phải có đủ sáu, **hành vi nhìn thấy được phải giống**.

| việc | nó làm gì | mốc thời gian |
|---|---|---|
| 1 | nháy một đèn | **chu kỳ 1 000 ms** |
| 2 | nháy một đèn khác | **chu kỳ 400 ms** |
| 3 | quét nút bấm PA0, chống rung | **quét mỗi 30 ms** |
| 4 | một đèn nữa, chỉ nháy khi **nhận được tin qua hàng đợi** | chờ có thời hạn |
| 5 | theo dõi và báo trạng thái hệ thống | chu kỳ mình để bạn chọn |
| 6 | màn hình DSI và cảm ứng | xem dưới |

Về **thứ tự ưu tiên** giữa sáu việc: mình **không chốt**. Bạn tự xếp, nhưng phải nói lý do, và
phải nghĩ tới chuyện việc quét nút chạy mỗi 30 ms có thể chen vào giữa việc khác.

Việc thứ 6 cần:
- khởi tạo SDRAM và màn hình, vẽ được giao diện;
- đọc được điểm chạm trên màn hình;
- nút bấm vật lý **và** chạm màn hình đều đổi được trang hiển thị.

### 5.1 · Giao diện: ba màn hình, bấm nút thì sang trang

Thêm 04/10/2026. Nhân chạy được rồi nên mình nói rõ phần nhìn thấy.

Mình cần **đúng giao diện của bản cũ**, vì nó là thứ mình đem đi báo cáo. Ba màn hình, chuyển
qua lại bằng **chạm nút trên màn hình** hoặc **nút bấm PA0**.

#### Màn hình 1 — Giới thiệu (nền trắng)

| vị trí | nội dung | màu |
|---|---|---|
| giữa, y = 30 | `HOC VIEN CONG NGHE BUU CHINH VIEN THONG` | đỏ |
| giữa, y = 55 | `KHOA KY THUAT DIEN TU 1` | đỏ |
| x = 300, y = 130 | `DE AN TOT NGHIEP` | xanh đậm |
| x = 300, y = 160 | `HE THONG TAC TU EIDE v3` | xanh đậm |
| x = 300, y = 210 | `DT: PHAT TRIEN PHAN MEM NHUNG` | đen |
| x = 300, y = 240 | `CO UNG DUNG TRI TUE NHAN TAO(AI)` | đen |
| x = 300, y = 280 | `Hoc vien  : Vu Tri Cong` | đen |
| x = 300, y = 310 | `GVHD      : TS. Nguyen Trung Hieu` | đen |
| bên trái | **logo PTIT** | ảnh |

Hai nút ở hàng dưới, cùng `y = 400`, cùng `240 × 50`:

| nút | x | màu nền | nhãn | bấm vào thì |
|---|---|---|---|---|
| 1 | 140 | xanh dương | `Chi tiet` | sang màn hình 2 |
| 2 | 420 | xanh lá | `Hello` | sang màn hình 3 |

#### Màn hình 2 — Chi tiết (nền xanh đậm)

Tiêu đề giữa, y = 25, màu vàng: `=== TINH NANG HE THONG EIDE v3 ===`

Ba mục, tiêu đề mục màu trắng, các dòng con màu lam nhạt:

```
1. He dieu hanh thoi gian thuc TU VIET da tac vu:      (y = 75)
   - Task 1: LED1 nhay chu ky 1000 ms                  (y = 100)
   - Task 2: LED2 nhay chu ky 400 ms                   (y = 125)
   - Task 3: Quet nut bam PA0, chong rung 30 ms        (y = 150)

2. Phan cung STM32F469NIH6 Cortex-M4F:                 (y = 185)
   - Man hinh DSI 800x480 IC OTM8009A                  (y = 210)
   - Bo nho mo rong SDRAM FMC (FrameBuffer)            (y = 235)
   - Cam ung dien dung FocalTech FT6206 qua I2C        (y = 260)

3. Nhan tu viet, khong dung FreeRTOS:                  (y = 295)
   - Lap lich tien dinh 32 muc, chuyen ngu canh PendSV (y = 320)
   - Hang doi tinh co thoi han, 0 ky hieu FreeRTOS     (y = 345)
```

**Mục 1 và mục 3 mình đã sửa chữ so với bản cũ**, vì bản cũ viết *FreeRTOS v10* và *Blink 4
LEDs* — nay nhân là của bạn và các tác vụ khác đi. Nếu bạn thấy nên ghi khác thì **đề xuất**,
đừng tự đổi.

Một nút `Tro ve` ở `x = 280, y = 400`, `240 × 50` → về màn hình 1.

#### Màn hình 3 — Hello (nền tối)

| vị trí | nội dung |
|---|---|
| giữa, y = 150 | `Xin chao` |
| giữa, y = 210 | `Chao mung ban den voi He thong EIDE v3!` |
| giữa, y = 260 | `Bo mach STM32F469I-DISCO san sang phuc vu` |

Một nút `Tro ve` cùng toạ độ như màn hình 2 → về màn hình 1.

#### Hai điều về cách làm

- **Logo PTIT lấy lại được.** Nó là ảnh, không phải logic, nên cùng loại với thư viện của ST:
  bạn lấy `logo_ptit.h` của bản cũ dùng luôn. Nhớ kê nó vào cột *lấy từ ngoài*, đừng đếm vào
  số dòng bạn tự viết.
- **Chạm màn hình và nút PA0 phải cho cùng kết quả.** Nút PA0 thì mình nghĩ nên là *sang trang
  kế tiếp theo vòng*, còn chạm thì theo đúng nút được chạm. Bạn thấy hợp lý thì làm thế; thấy
  khác thì nói.

Mình không nêu phông chữ và màu chính xác theo tên hằng số — bạn tự chọn trong thư viện, miễn
đọc được và tương phản.

---

---

## 6 · Đạt nghĩa là gì — danh mục nghiệm thu

Mỗi dòng dưới đây bạn phải báo **đạt hay chưa, kèm số đo và chỗ lấy số**. Dòng nào cần mắt mình
thì ghi rõ là cần mình, mình sẽ nhìn bo và nói lại.

| # | điều kiện | ai đo |
|---|---|---|
| 1 | **Không còn một ký hiệu nào của FreeRTOS** trong ảnh đã dịch | bạn — đọc bảng ký hiệu của ảnh, không phải grep mã nguồn |
| 2 | Ảnh dịch ra **không lớn hơn bản FreeRTOS cũ** (bản cũ khoảng 263 KB) | bạn — đo bằng công cụ đọc kích thước phân vùng |
| 3 | **Không tệp nào mình trông đợi bị thiếu khỏi ảnh một cách im lặng** — xem 6.2 | bạn — đối chiếu cây nguồn với thứ thật sự được dịch |
| 3b | **Xung nhịp hệ thống thật đạt 180 MHz** — đọc `RCC_CFGR` xem nguồn có phải PLL, và **đo nhịp thật** chứ đừng tin giá trị nạp vào SysTick | bạn — đọc thanh ghi trên chip |
| 4 | Hai đèn nháy **đúng chu kỳ 1 000 ms và 400 ms** | bạn đo nếu đo được; nếu không thì mình nhìn |
| 5 | Nút bấm PA0 **đổi trang**, và không bị rung nút | mình nhìn |
| 6 | **Màn hình sáng và vẽ đúng giao diện** | mình nhìn |
| 7 | **Chạm màn hình đổi trang** | mình nhìn |
| 8 | Đèn của việc thứ 4 **chỉ nháy khi có tin**, không nháy tự do | mình nhìn |
| 9 | Chạy **liên tục 10 phút không treo** | bạn — nêu cách bạn chứng minh là không treo |
| 10 | **Rút điện cắm lại thì chạy lại được**, không cần nạp lại | mình làm, mình nhìn |

### 6.1b · Vì sao mình thêm điều kiện 3b về xung nhịp

Thêm 04/10/2026, sau khi mất một lượt nạp vì thiếu nó.

Mục 3 mình đã cho sẵn hằng số PLL, nên mình **tưởng** chuyện xung nhịp là xong. Nhưng cho một
hằng số không làm nó được cài. Bản nạp đầu tiên chạy ở **HSI 16 MHz** — thạch anh ngoài chưa
từng được bật (`HSEON = False`) — trong khi SysTick nạp 179 999 tức tính cho 180 MHz. Hậu quả
là **mọi mốc thời gian chậm đúng 11,25 lần**, và màn hình tối vì định thời DSI tính theo 180 MHz.

Chỗ nguy là nó **không báo lỗi gì**: không fault, không treo, mọi thanh ghi trông hợp lý. Một
hệ chậm 11 lần nhìn giống một hệ không chạy.

Và đáng chú ý: nhịp nạp vào SysTick **đúng** (179 999 cho 1 000 Hz ở 180 MHz). Nên đọc giá trị
ấy rồi kết luận *nhịp 1 000 Hz* là sai — nó chỉ nói *nhịp sẽ là 1 000 Hz NẾU xung nhịp là 180
MHz*. Đo nhịp thật thì ra 91 Hz. **Giá trị cấu hình không phải phép đo.**

### 6.2 · Điều kiện số 3 mình viết sai, và đây là bản sửa

Sửa 04/10/2026, sau khi thấy hậu quả.

Bản đầu mình viết *"mọi tệp mã nguồn của dự án đều vào được ảnh"*. Câu ấy **tự nó khuyến
khích làm sai**: một tệp rỗng thì không vào được ảnh, nên cách dễ nhất để đạt là **viết thêm
mã vào tệp rỗng cho nó có gì đó**. Và chuyện ấy đã xảy ra thật — có một tệp trong dự án mang
chú thích *"tệp này chứa mã thực thi để đảm bảo mọi tệp mã nguồn đều được biên dịch vào ảnh
(Điều kiện số 3)"*. Mã viết ra để tiêu chí đạt, không vì sản phẩm cần.

Lỗi ở mình. Điều mình **thật sự** muốn canh là chuyện khác: ở một phiên trước của chính việc
này, có lượt báo *biên dịch xong* với ảnh 1 416 byte vì đầu vào bị thu hẹp dần cho tới khi
dịch qua — **driver màn hình, giao diện và cảm ứng đều rơi ra ngoài mà không ai được báo**.

Nên điều kiện số 3 đọc lại như sau:

- **Nêu trước** danh sách tệp bạn trông đợi có trong ảnh, và vì sao mỗi tệp cần có.
- Sau khi dịch, **đối chiếu** danh sách ấy với thứ thật sự vào ảnh.
- Tệp nào thiếu thì **nói ra kèm lý do** — thiếu có thể là đúng, im lặng thì không bao giờ
  đúng.
- **Một tệp không có việc gì để làm thì xoá đi**, đừng viết thêm mã cho nó đạt điều kiện.
  Mình thà nhận một dự án ít tệp hơn mà tệp nào cũng có lý do tồn tại.

### 6.1 · Hai chỗ mình muốn bạn cẩn thận với chính phép đo

Mình đã bị hai chuyện này cắn ở việc trước nên nói trước:

- **Một ảnh dịch ra nhỏ bất thường không phải là tin tốt.** Nếu bạn thu hẹp đầu vào cho tới khi
  dịch qua được rồi báo "xong", thì lời báo ấy đúng về **lời gọi** mà sai về **việc**. Nên điều
  kiện số 3 ở trên tồn tại: mình cần biết tệp nào **không** vào ảnh.
- **Mốc đọc phải sau mốc nạp.** Nếu bạn nạp rồi đọc trạng thái bo, phải tự so hai mốc thời gian
  ấy trước khi kết luận. Đọc trước khi nạp thì bạn đang đo **bản cũ**, và số sẽ trông hợp lý.

---

## 7 · Cách mình muốn làm việc với bạn

### 7.1 · Mình giao một việc mỗi lượt

Mình học được chuyện này ở việc trước: đưa cả tài liệu dài rồi nói "làm đi" thì bạn đọc rồi
dừng. Nên mình sẽ gõ từng câu ngắn, mỗi câu một việc. Bạn cứ làm việc được giao trong lượt, báo
lại, rồi mình giao tiếp.

### 7.2 · Bắt buộc dừng lại hỏi mình, sáu chỗ

1. Trước khi **nạp bất cứ thứ gì** lên bo.
2. Khi bạn muốn **lệch khỏi tài liệu này** — kể cả lệch đúng.
3. Khi bạn phát hiện **tài liệu này sai hoặc thiếu**. Mình viết nó, nên mình cũng sai được.
4. Khi bạn cần mình **cắm mạch, nhìn bo, hoặc bấm nút**.
5. Khi một quyết định làm **đổi chính thứ đang được đo**.
6. Khi bạn nhận ra **mình đã báo một việc xong mà thực ra chưa xong**. Chỗ này mình để riêng vì
   nó là chỗ khó nói nhất, và nó đáng giá nhất.

### 7.3 · Mỗi lượt kết lại năm dòng

1. Đã làm gì.
2. Bỏ gì và vì sao.
3. Giả định đang dùng.
4. Hoàn tác được tới đâu.
5. Hết bao nhiêu.

### 7.4 · Tầng tin được

Khi bạn đưa một con số, nói rõ nó ở tầng nào:

- **NGƯỜI** — mình đo hoặc mình nhìn thấy.
- **VÀNG** — bạn đo bằng công cụ, có hiện vật.
- **ĐỒNG** — bạn ước lượng, suy ra, hoặc nhớ.

Con số tầng ĐỒNG mình vẫn dùng, nhưng mình cần biết nó là ĐỒNG. Ở việc trước có một con số bạn
tự khai ĐỒNG rồi sau nâng lên có số đo — làm đúng như vậy là đủ.

### 7.5 · Bộ kiểm phải đo được sản phẩm

Nếu bạn viết bài kiểm, mình cần biết **bài kiểm ấy có đo gì không**. Hai chỗ mình nghe nói hay
sập, bạn tự tránh:

- **Tệp kiểm chép lại logic** của mã sản phẩm thay vì dịch thẳng mã sản phẩm vào.
- **Mốc so sánh lấy từ đầu ra của chính mã** — thì nó bảo vệ cả cái lỗi.

Và sau khi bài kiểm xanh, mình muốn bạn **tự phá mã sản phẩm rồi chạy lại** để xem bài kiểm có
kêu. Ca nào không kêu thì nói rõ ra — đó là chỗ nó không bảo vệ được, và nói ra thì đáng tin hơn
một bảng toàn màu xanh.

---

## 8 · Thứ mình cần nhận cuối cùng

| | |
|---|---|
| mã nguồn | nhân, driver, linker script, startup — chạy được |
| ảnh đã nạp | tệp nhị phân đúng bản đang chạy trên bo |
| bảng nghiệm thu | 10 dòng ở mục 6, mỗi dòng có số đo và chỗ lấy |
| các quyết định | mỗi chỗ bạn lệch khỏi tài liệu này, kèm lý do và mặt dở |
| chỗ chưa xong | thật thà, kể cả chỗ bạn đã báo xong rồi phát hiện chưa |
| chỗ bảng nghiệm thu **không chứng minh được** | dù nó xanh hết |

Dòng cuối mình để riêng. Một bảng nghiệm thu xanh toàn bộ là đúng loại kết quả dễ bị tin quá
mức, nên mình cần bạn tự nói ra giới hạn của nó.
