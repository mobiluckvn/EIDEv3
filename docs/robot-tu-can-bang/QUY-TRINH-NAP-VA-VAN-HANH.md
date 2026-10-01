# QUY TRÌNH NẠP FIRMWARE VÀ VẬN HÀNH ROBOT TỰ CÂN BẰNG MOBILUCK

Tài liệu hướng dẫn thao tác thực địa cho kỹ sư phần cứng và người vận hành bo mạch điều khiển robot 2 bánh tự cân bằng MOBILUCK (ATmega328P @ 16 MHz).

---

## 1. Chuẩn bị trước khi cắm mạch

Trước khi kết nối bất kỳ nguồn điện hoặc cáp nạp nào vào bo mạch, bắt buộc thực hiện kiểm tra an toàn:

1. **Kiểm tra cơ khí và dây nối:**
   - Đảm bảo 2 động cơ bước được bắt chặt vào khung gầm, bánh xe cao su lắp đồng trục và không bị kẹt cơ khí.
   - Cáp động cơ bước (4 dây mỗi động cơ) cắm đúng thứ tự vào đầu ra của 2 driver A4988.
   - Mô-đun cảm biến MPU6050 lắp cố định chắc chắn gần trọng tâm robot, hướng trục X/Y đúng chiều tiến/lùi.
2. **Kiểm tra nguồn điện:**
   - Nguồn cấp động cơ (Pin LiPo 3S 11,1 V - 12,6 V hoặc nguồn bàn DC có giới hạn dòng): Đảm bảo đúng cực tính (+ / -), kiểm tra thông mạch GND giữa tầng vi điều khiển và tầng công suất động cơ.
   - Đặt giới hạn dòng trên bộ nguồn DC ở mức 1,5 A trong lần thử đầu tiên để chống chập cháy.
3. **Lưu ý phần cứng đặc biệt:**
   - **Chân EN của 2 driver A4988 đã nối cứng xuống GND trên bo mạch.** Khi cấp nguồn động cơ, driver luôn ở chế độ giữ mô-men (holding torque). Việc dừng động cơ hoàn toàn do phần mềm ngắt phát xung STEP, không thể ngắt nguồn công suất qua phần mềm.

---

## 2. Các bước nạp firmware theo đúng thứ tự

Thực hiện nạp chương trình vào ATmega328P qua cổng nạp ISP hoặc cổng nạp nạp USB-UART (Bootloader Arduino Nano):

1. **Bước 1: Ngắt nguồn công suất động cơ:**
   - Rút giắc pin/nguồn động cơ trước khi cắm cáp nạp USB vào bo mạch để tránh dòng trả ngược gây hỏng cổng USB máy tính.
2. **Bước 2: Kết nối cáp nạp:**
   - Cắm cáp USB (Mini-USB/Micro-USB) từ máy tính vào cổng nạp của bo mạch ATmega328P.
   - Đèn LED nguồn 5 V (PWR) trên bo vi điều khiển sáng liên tục.
3. **Bước 3: Biên dịch và nạp bản dựng:**
   - Bản nạp nhị phân nằm tại đường dẫn: `.eide/build/mach.elf` (Flash: 5.710 B, SRAM: 87 B).
   - Sử dụng công cụ `avrdude` hoặc giao diện EIDE để nạp vi điều khiển:
     ```bash
     avrdude -v -patmega328p -carduino -P /dev/ttyUSB0 -b 115200 -D -U flash:w:.eide/build/mach.elf:e
     ```
   - Quan sát quá trình ghi Flash và xác thực (verification) đạt 100% không có lỗi timeout.
4. **Bước 4: Ngắt cáp nạp hoặc chuyển sang cổng giám sát Serial:**
   - Sau khi nạp hoàn tất, ngắt cáp nạp hoặc giữ cáp nếu muốn xem log UART (115.200 bps).

---

## 3. Trình tự khởi động và vận hành sau khi bật nguồn

Sau khi nạp xong, quy trình cấp nguồn và vận hành robot diễn ra theo 4 giai đoạn cụ thể:

### Giai đoạn 1: Bật nguồn và Tự hiệu chuẩn MPU6050 (FR-01, FR-02)
- **Hành động:** Đặt robot **nằm yên hoàn toàn trên mặt phẳng** (không cầm trên tay, không rung lắc), sau đó bật công tắc nguồn pin.
- **Tín hiệu quan sát:**
  - Còi chip D10 phát **1 tiếng bíp ngắn (50 ms)** báo hiệu hệ thống đã khởi động và bước vào trạng thái tự hiệu chuẩn (`STATE_CALIBRATING`).
  - Vi điều khiển tự động thu thập 500 mẫu dữ liệu tĩnh từ cảm biến MPU6050 trong khoảng 1 đến 2 giây để khử trôi con quay (gyro bias).

### Giai đoạn 2: Sẵn sàng kích hoạt (STATE_READY)
- **Tín hiệu quan sát:**
  - Khi hiệu chuẩn 500 mẫu thành công, còi D10 phát **1 tiếng bíp dài hơn (200 ms)** báo hiệu robot đã sẵn sàng.
  - Lúc này động cơ vẫn đứng yên (tần số xung STEP = 0 bước/s).

### Giai đoạn 3: Dựng robot để kích hoạt tự cân bằng (FR-04)
- **Hành động:** Dùng tay cầm nhẹ khung thân trên, dựng robot đứng thẳng dần lên.
- **Tín hiệu quan sát:**
  - Khi góc nghiêng thân robot đi qua vùng lân cận điểm cân bằng (trong phạm vi $\pm 2^\circ$), hệ thống **tự động chuyển sang trạng thái cân bằng (`STATE_BALANCING`)**.
  - Động cơ bước hai bánh xe lập tức phát xung điều khiển tiến/lùi để ghìm thân robot thăng bằng. Lúc này buông nhẹ tay để robot tự hành.

### Giai đoạn 4: Dừng khẩn cấp bằng nút bấm D12 (FR-03)
- **Hành động:** Khi robot đang cân bằng hoặc sẵn sàng, bấm nút nhấn D12 một lần.
- **Tín hiệu quan sát:**
  - Hệ thống chuyển ngay sang trạng thái dừng (`STATE_STOPPED`), ngắt toàn bộ xung phát bước, còi kêu 1 tiếng bíp 100 ms.
  - Muốn đưa robot trở lại trạng thái sẵn sàng: Đặt robot thăng bằng và bấm nút D12 thêm một lần nữa (còi kêu 50 ms báo về `STATE_READY`).

---

## 4. Dấu hiệu chạy đúng, dấu hiệu sai và cách xử lý

| Hiện tượng quan sát | Đánh giá | Nguyên nhân | Cách xử lý |
|:---|:---:|:---|:---|
| Bật nguồn $\rightarrow$ 1 bíp ngắn $\rightarrow$ yên lặng 1,5 s $\rightarrow$ 1 bíp dài $\rightarrow$ dựng thẳng tự cân bằng | **ĐÚNG** | Hệ thống khởi động, hiệu chuẩn và vòng PID điều khiển phản hồi âm chuẩn xác. | Tiếp tục vận hành bình thường. |
| Bật nguồn kêu 1 bíp ngắn nhưng không bao giờ kêu bíp dài sẵn sàng | **SAI** | Lỗi giao tiếp I2C với MPU6050 (đứt dây SDA/SCL, lỏng giắc hoặc cảm biến mất nguồn). | Tắt nguồn; kiểm tra điện áp 3,3 V/5 V cấp cho MPU6050; cắm chặt cáp I2C tại chân A4/A5; kiểm tra điện trở kéo lên pull-up trên bus I2C. |
| Dựng robot thẳng đứng nhưng 2 bánh xe phóng vọt về một phía và ngã ngay | **SAI** | Ngược chiều quay động cơ bước hoặc đảo chiều trục cảm biến (phản hồi dương). | Đảo ngược 2 dây của 1 cuộn pha động cơ bước trên giắc A4988, hoặc đổi logic chân DIR (D2, D4) trong `config.h`. |
| Robot đứng được nhưng rung giật biên độ lớn, dao động tăng dần | **SAI** | Hệ số khuếch đại $K_p$ hoặc $K_d$ quá lớn, hoặc cảm biến bị rung động cơ khí truyền vào. | Lắp thêm đệm cao su giảm chấn cho mô-đun MPU6050; hạ hệ số $K_p$ trong `firmware/pid.c` từ 15,0 xuống 12,0. |
| Robot bị nghiêng lệch cố định về một phía (drift từ từ về trước hoặc sau) | **SAI** | Điểm cân bằng cơ khí lệch so với góc 0 độ của IMU (trọng tâm không trùng mặt phẳng cảm biến). | Hiệu chỉnh bù góc nghiêng tĩnh (setpoint offset) trong hàm tính toán PID khoảng $\pm 0,5^\circ$ đến $\pm 1,5^\circ$. |
| Robot ngã vượt $45^\circ$, còi kêu 1 tiếng dài (300 ms) và bánh xe ngừng quay | **ĐÚNG** | Cơ chế ngắt an toàn chống lật đổ FR-05 hoạt động chuẩn xác trong vòng $\le 4\text{ ms}$. | Nâng robot dựng lại điểm thăng bằng và bấm nút D12 để reset về trạng thái `STATE_READY`. |

---

## 5. Những điều PHẢI TUYỆT ĐỐI TRÁNH

1. **KHÔNG ĐƯỢC rung lắc hoặc di chuyển robot trong 2 giây đầu sau khi bật nguồn:**
   - Trong thời gian vi điều khiển lấy 500 mẫu tĩnh, bất kỳ chuyển động nào cũng sẽ làm sai lệch giá trị gyro bias, dẫn đến việc ước lượng góc nghiêng bị trôi liên tục khiến robot không thể cân bằng.
2. **KHÔNG ĐƯỢC dùng tay quay cưỡng bức bánh xe khi đang có nguồn cấp động cơ:**
   - Chân EN driver A4988 nối cứng GND, động cơ bước luôn có dòng điện giữ mô-men. Cố tình xoay bánh xe bằng tay sẽ sinh sức phản điện động lớn làm cháy driver A4988 hoặc làm mòn bánh răng giảm tốc.
3. **KHÔNG ĐƯỢC thêm hàm trễ chặn CPU (`_delay_ms`) hoặc nạp mã điều khiển LED WS2812:**
   - Hệ thống vận hành kiến trúc thời gian thực 3 tầng: ngắt Timer2 50 kHz (phát xung bước) và ngắt Timer0 chu kỳ 4 ms (tính toán góc & PID).
   - Bất kỳ đoạn mã nào chặn CPU quá 0,2 ms (như giao thức truyền chuỗi LED WS2812 cấm ngắt) sẽ làm trễ hạn ngắt, gây vỡ nhịp bước và làm robot sụp đổ tức thì (vi phạm NFR-01, NFR-02).
4. **KHÔNG ĐƯỢC để bánh xe quay tự do trên không khi chưa đặt xuống mặt sàn:**
   - Khi không có tải trọng và phản lực mặt sàn, vòng điều khiển PID sẽ tích phân sai số tăng dần dẫn đến tốc độ bánh xe vọt lên mức tối đa.
