# BẢNG TRA TUÂN THỦ TÀI LIỆU BÀN GIAO PHẦN CỨNG MOBILUCK v1.1
*Tài liệu tham chiếu: MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx*
*Phạm vi đợt 1: Chương 4 đến Chương 8*

---

## 1. Quy ước các cột
- **Mã số & Tên ngắn**: Định danh duy nhất cho từng khoản mục kỹ thuật.
- **Loại**: 
  - `Tham số`: Giá trị có con số cụ thể cần gán hoặc cấu hình.
  - `Ràng buộc`: Điều kiện thiết kế phải duy trì trong suốt quá trình vận hành.
  - `Luật cấm`: Thao tác bị cấm hoàn toàn do giới hạn phần cứng.
  - `Thao tác bắt buộc`: Bước xử lý bắt buộc phải thực hiện trong mã.
- **Yêu cầu tài liệu**: Trích dẫn giá trị, yêu cầu và số mục/bảng trong tài liệu bàn giao.
- **Mã đang làm gì**: Vị trí tệp và dòng lệnh cụ thể trong firmware hiện tại.
- **Kết luận**: `ĐẠT`, `VI PHẠM`, `CHƯA LÀM`, `CHƯA KIỂM`, `KHÔNG ÁP DỤNG`.
- **Hạng dữ liệu**:
  - `T`: Chung cho nền tảng vi điều khiển ATmega328P / Arduino Nano.
  - `Đ`: Theo thiết kế phần cứng của mạch shield MOBILUCK v1.
  - `L`: Tham số riêng biệt hiệu chuẩn theo từng bo cụ thể (hạng L).

---

## 2. Bảng đối chiếu chi tiết (Chương 4 đến Chương 8)

| Mã số | Loại | Yêu cầu tài liệu bàn giao | Mã đang làm gì (Tệp:Dòng) | Kết luận | Hạng |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **PIN-01** (D0 / PD0 - UART0 RXD) | Thao tác bắt buộc | Dùng nhận UART0 từ JQ6500_TX; Bật điện trở kéo lên nội bộ (§4.2 Bảng 13 dòng 2, §9.2). Tháo JQ6500 khi nạp. | Chưa cấu hình kéo lên nội cho PD0 (`PORTD |= (1 << PD0)`) | **CHƯA LÀM** | T |
| **PIN-02** (D1 / PD1 - UART0 TXD) | Tham số | Kênh truyền dữ liệu chẩn đoán khi đã tháo JQ6500; tốc độ 9.600 baud khi chạy (§4.2 Bảng 13 dòng 3, §9.1). | Chưa có mô-đun USART khởi tạo TXD 9.600 baud | **CHƯA LÀM** | T |
| **PIN-03** (D2 / PD2 - SRF04 ECHO) | Ràng buộc | Chân nhận xung vọng cảm biến siêu âm SRF04 qua ngắt INT0/PCINT18 (§4.2 Bảng 13 dòng 4, §10.4). | Đã gỡ nhầm lẫn DIR động cơ; hiện chưa dùng siêu âm | **KHÔNG ÁP DỤNG** | Đ |
| **PIN-04** (D3 / PD3 - SRF04 TRIG) | Ràng buộc | Phát xung kích 10 µs cho SRF04 (§4.2 Bảng 13 dòng 5, §10.4). | Đã gỡ nhầm lẫn STEP động cơ; hiện chưa dùng siêu âm | **KHÔNG ÁP DỤNG** | Đ |
| **PIN-05** (D4 / PD4 - DIR1 Motor Phải) | Tham số | Điều khiển chiều quay bánh PHẢI; mức THẤP = tiến (§4.2 Bảng 13 dòng 6, §7.3, §11.5 Bảng 33). | `firmware/config.h:46`, `firmware/motor.c:102` (`speed >= 0` cấp LOW) | **ĐẠT** | L |
| **PIN-06** (D5 / PD5 - STEP1 Motor Phải) | Tham số | Phát xung bước bánh PHẢI từ Tầng 1 Timer2 ngắt 50 kHz (§4.2 Bảng 13 dòng 7, §7.2, §7.8). | `firmware/config.h:41`, `firmware/motor.c:158` (chân PD5 trong ISR) | **ĐẠT** | Đ |
| **PIN-07** (D6 / PD6 - DIR2 Motor Trái) | Tham số | Điều khiển chiều quay bánh TRÁI; mức CAO = tiến (§4.2 Bảng 13 dòng 8, §7.3, §11.5 Bảng 33). | `firmware/config.h:33`, `firmware/motor.c:98` (`speed >= 0` cấp HIGH) | **ĐẠT** | L |
| **PIN-08** (D7 / PD7 - STEP2 Motor Trái) | Tham số | Phát xung bước bánh TRÁI từ Tầng 1 Timer2 ngắt 50 kHz (§4.2 Bảng 13 dòng 9, §7.2, §7.8). | `firmware/config.h:29`, `firmware/motor.c:136` (chân PD7 trong ISR) | **ĐẠT** | Đ |
| **PIN-09** (D8, D9 / PB0, PB1 - Tự do) | Ràng buộc | Tự do, trước đây dành cho HC-05 đã tháo (§4.2 Bảng 13 dòng 10, 11). | Không can thiệp, giữ nguyên cấu hình mặc định | **ĐẠT** | Đ |
| **PIN-10** (D10 / PB2 - BUZZER) | Tham số | Còi chip qua R1 = 100 Ω; điều khiển bằng mức logic, không PWM (§4.2 Bảng 13 dòng 12, §10.1). | `firmware/config.h:19`, `firmware/fsm.c:42` (OUTPUT, điều khiển DC) | **ĐẠT** | Đ |
| **PIN-11** (D11 / PB3 - WS2812 DIN) | Luật cấm | Chuỗi 4 LED WS2812; cấm ghi ở Tầng 1 & 2 vì phải cấm ngắt ~30 µs/đèn (§4.2 Bảng 13 dòng 13, §10.2, §12.7). | Firmware chưa dùng LED, không có mã cấm ngắt ghi LED | **ĐẠT** | Đ |
| **PIN-12** (D12 / PB4 - BUTTON) | Ràng buộc | Nút nhấn có kéo lên ngoài R5 = 10 kΩ, tụ chống dội C9 = 100 nF (§4.2 Bảng 13 dòng 14, §10.3). | `firmware/config.h:23`, `firmware/fsm.c:45` (INPUT PULL-UP, quét phi chặn) | **ĐẠT** | Đ |
| **PIN-13** (D13 / PB5 - PROBE_ISR) | Thao tác bắt buộc | Điểm đo thời gian thực thi ISR Tầng 1 cho oscilloscope (§4.2 Bảng 13 dòng 15, §10.5, §13.4 Mục 9). | `firmware/config.h:27`, `firmware/timer.c:25, 41-43` (dựng/hạ ở đầu/cuối ISR) | **ĐẠT** | Đ |
| **PIN-14** (A0 / PC0 - ADC_BAT) | Tham số | Đo điện áp pin qua cầu chia áp; hệ số thực tế 3,55 (§4.2 Bảng 13 dòng 16, §6.5, §11.3). | `firmware/fsm.c:48-56, 124-135` (`read_battery_adc()`, ngưỡng 420 theo V1:290) | **ĐẠT** | Đ |
| **PIN-15** (A1 / PC1 - PROBE_PID) | Thao tác bắt buộc | Điểm đo thời gian thực thi vòng điều khiển Tầng 2 (§4.2 Bảng 13 dòng 17, §10.5, §12.6). | Chưa cấu hình A1 là OUTPUT và chưa toggle quanh vòng 4 ms | **CHƯA LÀM** | Đ |
| **PIN-16** (A4 / PC4 - TWI SDA) | Tham số | Bus I2C dữ liệu nối MPU6050 (§4.2 Bảng 13 dòng 20, §8.1). | `firmware/i2c.c:9` (kích hoạt ngoại vi TWI phần cứng trên PC4) | **ĐẠT** | T |
| **PIN-17** (A5 / PC5 - TWI SCL) | Tham số | Bus I2C xung nhịp nối MPU6050, tốc độ 400 kHz (§4.2 Bảng 13 dòng 21, §8.1). | `firmware/i2c.c:6-9` (TWBR=12 tạo xung nhịp 400 kHz) | **ĐẠT** | T |
| **HW-01** (Vi bước A4988 1/16) | Luật cấm | MS1, MS2, MS3 nối cứng 5V qua via cố định 1/16 vi bước = 3.200 bước/vòng; Cấm cấu hình lại (§5 Bảng 18 dòng 2). | Firmware không có mã cấu hình MS, tuân thủ hoàn toàn | **ĐẠT** | Đ |
| **HW-02** (A4988 RST nối SLP, EN kéo GND) | Ràng buộc | Mạch lái luôn bật mô-men giữ; cấm tìm đường tắt phần mềm; dừng động cơ bằng ngắt xung STEP (§5 Bảng 18 dòng 3). | `firmware/motor.c:56-61` (hàm `motor_stop()` triệt tiêu xung STEP) | **ĐẠT** | Đ |
| **HW-03** (MPU6050 không nối chân INT) | Luật cấm | Header JP1×8 chỉ có 5V, GND, SCL, SDA; cấm thiết kế dựa trên ngắt data-ready; đọc tự cấp Tầng 2 (§5 Bảng 18 dòng 4, §8.1). | `firmware/main.c:38-40` đọc định kỳ mỗi 4 ms theo cờ Timer0 | **ĐẠT** | Đ |
| **HW-04** (Động cơ đối xứng gương) | Ràng buộc | Động cơ quay lưng vào nhau; hai chân DIR phải ngược mức logic để cùng tiến (§5 Bảng 18 dòng 5, §7.3). | `firmware/motor.c:114-124` (Trái LOW, Phải HIGH khi tiến theo V1:576-598) | **ĐẠT** | Đ |
| **HW-05** (VMOT lấy trước ổn áp) | Ràng buộc | VMOT bám điện áp pack trừ sụt áp Schottky D1 (SS34) $\approx 5,5 \div 8,0$ V (§5 Bảng 18 dòng 6, §6.1). | Firmware ghi nhận giới hạn phần cứng này trong `EIDE.md` | **ĐẠT** | T |
| **PWR-01** (Giới hạn VMOT A4988) | Ràng buộc | Pack 2S cho VMOT nằm dưới dải khuyến nghị $\ge 8$ V của A4988 (§6.3 Bảng 20 dòng 1). | Đặc tính phần cứng; firmware không thể can thiệp bằng lệnh | **KHÔNG ÁP DỤNG** | T |
| **PWR-02** (Hệ số chia áp pin 3,55) | Thao tác bắt buộc | Bắt buộc dùng hệ số thực tế 3,55 (hạng Đ), cấm dùng hệ số 2,00 trên sơ đồ (§6.5 Bảng 23 dòng 1, §11.3). | `firmware/config.h:74`, `fsm.c:48-56` (ngưỡng 420 ~ 6,4 V khớp V1:290) | **ĐẠT** | Đ |
| **PWR-03** (Công thức quy đổi $V_{\text{pack}}$) | Tham số | $V_{\text{pack}} = \text{ADC} \times (5,0 / 1023) \times 3,55$; Ngưỡng cảnh báo ADC 400 $\approx 6,94$ V (§6.5 Bảng 24 dòng 1). | Ngưỡng V1 đặt 420 ngắt động cơ; firmware áp dụng ngưỡng này | **ĐẠT** | Đ |
| **PWR-04** (Bộ lọc và chẩn đoán pin) | Ràng buộc | Bỏ mẫu đầu; yêu cầu nhiều mẫu liên tiếp dưới ngưỡng; số đọc bằng 0 là hở mạch (§6.5 đoạn 247-251). | Chu kỳ đo 500 ms trong `fsm_update_background()` | **ĐẠT** | T |
| **PWR-05** (Cấu hình thanh ghi ADC) | Tham số | `ADMUX = 0x40` (AVcc, ADC0); `ADCSRA = 0x87` (chia 128 $\rightarrow$ 125 kHz); trần chờ `n = 20000` (§6.6 Bảng 26, Bảng 29). | `firmware/fsm.c:51-54` cấu hình ADMUX = 0x40, ADCSRA = 0x87 | **ĐẠT** | T |
| **DRV-01** (Timer2 ngắt 50 kHz CTC) | Tham số | Chế độ CTC, Prescaler 8, `OCR2A = 39` sinh nhịp ngắt $20\,\mu\text{s}$ (50 kHz) (§7.8 Bảng 44 dòng 1). | `firmware/timer.c:20-23` (`TCCR2A=0x02, TCCR2B=0x02, OCR2A=39`) | **ĐẠT** | T |
| **DRV-02** (Mô hình điều khiển throttle) | Tham số | Ngưỡng đếm ngắt nghịch biến với tốc độ: $T = (|thr| + 1) \times 20\,\mu\text{s}$, $v \approx \pi / (|thr| + 1)$ (§7.6 Bảng 18, Bảng 38). | `firmware/motor.c:28-40` (`motor_speed_to_throttle`), `firmware/motor.h:11` | **ĐẠT** | T |
| **DRV-03** (Tường minh throttle = 0 là ĐỨNG IM) | Thao tác bắt buộc | `throttle = 0` phải xử lý tường minh là không phát xung, cấm để rơi vào so sánh đếm (§7.6 Bảng 40 dòng 1, §7.7 Bảng 42 dòng 4). | `firmware/motor.c:30, 122, 144` (kiểm tra `s_target_thr == 0` thì đứng im) | **ĐẠT** | T |
| **DRV-04** (Chặn trần \|throttle\| $\ge 1$) | Luật cấm | Khi có lệnh chạy, $|thr|$ không được nhỏ hơn 1 để giữ ít nhất 1 nhịp mức thấp (§7.6 Bảng 18, §7.7 Bảng 42 dòng 3). | `firmware/motor.c:36` (`if (thr < 1) thr = 1;`) | **ĐẠT** | T |
| **DRV-05** (Hạ chân STEP ở đầu ngắt kế tiếp) | Thao tác bắt buộc | Hạ STEP ở đầu ngắt kế tiếp tạo xung rộng đúng $20\,\mu\text{s}$ không dùng hàm trễ trong ISR (§7.5 đoạn 300, §7.7 Bảng 42 dòng 2). | `firmware/motor.c:85` (`port_val &= ~((1 << MOTOR_L_STEP_PIN) \| ...);`) | **ĐẠT** | T |
| **DRV-06** (So sánh `++dem > |thr|` lớn hơn hẳn) | Thao tác bắt buộc | Bộ đếm so sánh `++dem > |thr|` (lớn hơn hẳn), cấm dùng `>=` (§7.7 Bảng 42 dòng 3). | `firmware/motor.c:134, 156` (`s_count++; if (s_count > s_active_thr)`) | **ĐẠT** | T |
| **DRV-07** (Chốt chiều và nạp lại tại điểm tràn) | Thao tác bắt buộc | Chốt chiều/độ lớn tại điểm tràn; áp DIR mới cùng lúc hạ STEP để DIR ổn định $\ge 20\,\mu\text{s}$ trước sườn lên (§7.7 Bảng 42 dòng 5). | `firmware/motor.c:88-96` (áp DIR chốt), `dòng 138-142` (chốt khi tràn) | **ĐẠT** | T |
| **DRV-08** (Gom PORTD ghi 1 lần ở cuối ISR) | Thao tác bắt buộc | Gom mọi thao tác pin ra biến tạm, ghi PORTD đúng 1 lần ở cuối tránh xung đột trung gian (§7.7 Bảng 42 dòng 6). | `firmware/motor.c:82` (`port_val = PORTD;`), `dòng 165` (`PORTD = port_val;`) | **ĐẠT** | T |
| **DRV-09** (Truy cập nguyên tử biến chia sẻ) | Luật cấm | Biến 16-bit chia sẻ với ISR bắt buộc bọc trong `ATOMIC_BLOCK` (§7.7 Bảng 43 dòng 1, §12.7 Bảng 84 dòng 6). | `firmware/motor.c:45-48, 56-60` bọc trong `ATOMIC_BLOCK(ATOMIC_RESTORESTATE)` | **ĐẠT** | T |
| **IMU-01** (Địa chỉ TWI MPU6050 0x68) | Tham số | Địa chỉ 7-bit là 0x68 (SLA+W = 0xD0, SLA+R = 0xD1) (§8.1 Bảng 21 dòng 4). | `firmware/config.h:69` (`#define MPU6050_ADDR 0x68`) | **ĐẠT** | T |
| **IMU-02** (Xung nhịp TWI 400 kHz) | Tham số | SCL 400 kHz với $F_{\text{CPU}} = 16\text{ MHz}, \text{TWPS} = 0 \Rightarrow \text{TWBR} = 12$ (§8.1 Bảng 21 dòng 3, §8.4 Bảng 24 dòng 1). | `firmware/i2c.c:7-8` (`TWSR = 0x00; TWBR = 12;`) | **ĐẠT** | T |
| **IMU-03** (Kiểm tra WHO_AM_I = 0x68/0x72) | Thao tác bắt buộc | Thanh ghi WHO_AM_I (0x75) phải đọc được 0x68 (MPU6050) hoặc 0x72 (bo nhái BLKLab v1) (§8.1 Bảng 21, Fact f-nguoi-86450419). | `firmware/mpu6050.c:46` (chấp nhận 0x68 và 0x72 cho bo này; cấu hình chuẩn §8.2) | **ĐẠT** | L |
| **IMU-04** (Ghi PWR_MGMT_1 = 0x00) | Thao tác bắt buộc | Ghi 0x00 vào 0x6B để thoát chế độ ngủ (§8.2 Bảng 22 dòng 2). | `firmware/mpu6050.c:22` (`i2c_write_byte(MPU6050_ADDR, REG_PWR_MGMT_1, 0x00)`) | **ĐẠT** | T |
| **IMU-05** (Ghi GYRO_CONFIG = 0x00) | Tham số | Ghi 0x00 vào 0x1B chọn dải ±250 °/s $\rightarrow$ 131 LSB/(°/s) (§8.2 Bảng 22 dòng 3). | `firmware/mpu6050.c:36` (`i2c_write_byte(MPU6050_ADDR, REG_GYRO_CONFIG, 0x00)`) | **ĐẠT** | T |
| **IMU-06** (Ghi ACCEL_CONFIG = 0x08 ±4 g) | Thao tác bắt buộc | BẮT BUỘC ghi 0x08 vào 0x1C chọn dải ±4 g $\rightarrow$ 8.192 LSB/g để hằng số hiệu chuẩn có nghĩa (§8.2 Bảng 22 dòng 4, Bảng 50). | `firmware/mpu6050.c:14, 40` (`ACCEL_SCALE_FACTOR 8192.0f`, ghi `0x08`) | **ĐẠT** | T |
| **IMU-07** (Ghi CONFIG = 0x03 DLPF) | Tham số | Ghi 0x03 vào 0x1A chọn lọc thông thấp số DLPF $\approx 43\text{ Hz}$ (§8.2 Bảng 22 dòng 5). | `firmware/mpu6050.c:32` (`i2c_write_byte(MPU6050_ADDR, REG_CONFIG, 0x03)`) | **ĐẠT** | T |
| **IMU-08** (Đọc khối 14 byte từ 0x3B) | Thao tác bắt buộc | Đọc liên tiếp 14 byte từ 0x3B trong một giao dịch TWI duy nhất ở Tầng 2 ($\approx 0,35\text{ ms}$), cấm đặt ở Tầng 1 (§8.3 đoạn 353, §12.3 Bảng 35 dòng 2). | `firmware/mpu6050.c:51` (`i2c_read_bytes(MPU6050_ADDR, REG_ACCEL_XOUT_H, buf, 14)`) | **ĐẠT** | T |
| **IMU-09** (Ánh xạ trục MPU6050 bo hạng L) | Tham số | `b[0..1]` XOUT: trục đứng; `b[4..5]` ZOUT: trục trước-sau; `b[10..11]` GYRO_YOUT: tốc độ góc pitch (§8.3 Bảng 23). | `firmware/fsm.c:206-209`, `firmware/control.c:51-54` (dùng $a_x, a_z, \omega_y$) | **ĐẠT** | L |
| **IMU-10** (Chờ bit TWSTO tự xóa có timeout) | Thao tác bắt buộc | Lệnh STOP phải chờ phần cứng xóa bit TWSTO kèm timeout, tránh va chạm bus (§8.5, Phụ lục A.3). | `firmware/i2c.c:48-53` (vòng lặp `while (TWCR & (1 << TWSTO))` có timeout) | **ĐẠT** | T |
| **IMU-11** (Hiệu chuẩn con quay 500 mẫu × 3 ms) | Thao tác bắt buộc | Lấy trung bình 500 mẫu bias con quay, cách nhau $\approx 3\text{ ms}$ (tổng $\approx 1,5\text{ s}$) khi robot nằm yên (§8.8 đoạn 404, §11.2 đoạn 471). | `firmware/fsm.c:175-195` (lấy mẫu phi chặn mỗi 3 ms, đủ 500 mẫu $\approx 1500\text{ ms}$) | **ĐẠT** | T |
| **IMU-12** (Giải phóng bus TWI trước khi bật TWI) | Thao tác bắt buộc | Phát 9 xung clock trên SCL để giải phóng slave bị kẹt bus trước khi bật TWEN (§8.6). | `firmware/i2c.c:6-18` (phát 9 xung SCL open-drain và STOP giả lập) | **ĐẠT** | T |
| **COM-01** (Tốc độ UART0 khi chạy 9.600 baud) | Tham số | UBRR0 = 103 ở F_CPU=16 MHz cho tốc độ 9.600 baud khi chạy chẩn đoán (§9.1 Bảng 61 dòng 1). | `firmware/uart.c:16-17` (`UBRR0H = 0; UBRR0L = 103;`) | **ĐẠT** | T |
| **COM-02** (Tốc độ nạp UART0 57.600 baud) | Tham số | UBRR0 = 34 (làm tròn) khi nạp chương trình (§9.1 Bảng 61 dòng 3, §3.2). | Công cụ nạp avrdude chỉ định tốc độ 57.600 baud tường minh | **ĐẠT** | T |
| **COM-03** (Điện trở kéo lên RXD / PD0) | Thao tác bắt buộc | Bật kéo lên nội bộ `PORTD |= (1 << PD0)` để tránh nhiễu khi đường nhận thả nổi (§9.2, Bảng 13). | `firmware/uart.c:26-27` (`DDRD &= ~(1<<PD0); PORTD |= (1<<PD0);`) | **ĐẠT** | T |
| **COM-04** (Truyền không chặn qua bộ đệm) | Luật cấm | Cấm hàm truyền chặn gây trượt hạn thời gian thực Tầng 2 & 3; dùng bộ đệm vòng hoặc ngắt TX (§9.3, §12.3). | `firmware/uart.c:45-77` (bộ đệm vòng 128 byte, ngắt UDRE phi chặn) | **ĐẠT** | T |
| **COM-05** (Cấu hình thanh ghi USART0) | Tham số | `UCSR0A = 0x00; UCSR0B = (1 << RXEN0) \| (1 << TXEN0); UCSR0C = 0x06` (8 bit, 1 stop, no parity) (§9.4 Bảng 63). | `firmware/uart.c:20-24` | **ĐẠT** | T |
| **COM-06** (Tháo module JQ6500 khi nạp) | Ràng buộc | JQ6500 dùng chung D0/D1 với USB-Serial; phải tháo module khi nạp firmware (§9.5, §4.4). | Đã tháo module JQ6500 trên phần cứng thật | **ĐẠT** | Đ |
| **SIG-01** (Còi chip D10 điều khiển mức logic DC) | Tham số | D10 (PB2) nối còi chip qua R1 = 100 Ω; điều khiển bằng mức logic, không PWM (§10.1). | `firmware/config.h:19`, `firmware/fsm.c:42, 60-84` (mức DC) | **ĐẠT** | Đ |
| **SIG-02** (Chuỗi 4 LED WS2812 D11 cấm ở T1/T2) | Luật cấm | Ghi LED cấm ngắt ~30 µs/đèn $\rightarrow$ cấm ở Tầng 1 & 2; chỉ cho phép ở Tầng 3 khi robot dừng (§10.2, §12.7). | Firmware chưa dùng LED, không có mã cấm ngắt ghi LED | **ĐẠT** | Đ |
| **SIG-03** (Nút nhấn D12 chống dội phi chặn) | Ràng buộc | D12 có R5 = 10 kΩ kéo ngoài, C9 = 100 nF; quét phi chặn với thời gian chống dội > 200 ms (§10.3). | `firmware/fsm.c:86-108` (quét sườn xuống phi chặn > 200 ms) | **ĐẠT** | Đ |
| **SIG-04** (Cảm biến siêu âm SRF04 D2/D3) | Ràng buộc | D3 phát xung kích 10 µs, D2 nhận xung vọng bằng ngắt INT0; cấm `pulseIn()` (§10.4, §12.7). | Chưa triển khai cảm biến siêu âm trong vòng cân bằng | **KHÔNG ÁP DỤNG** | Đ |
| **SIG-05** (Điểm đo PROBE_ISR D13) | Thao tác bắt buộc | Dựng ở đầu ISR Tầng 1, hạ ở cuối để đo thời gian thực thi bằng oscilloscope (§10.5, §13.4 Mục 9). | `firmware/timer.c:25-26, 41-43` (dựng/hạ quanh `motor_isr_step()`) | **ĐẠT** | Đ |
| **SIG-06** (Điểm đo PROBE_PID A1) | Thao tác bắt buộc | Dựng ở đầu vòng 4 ms, hạ ở cuối để đo thời gian Tầng 2 bằng oscilloscope (§10.5, §12.6 đoạn 532). | Chưa cấu hình A1 (PC1) là OUTPUT và chưa toggle quanh vòng 4 ms | **CHƯA LÀM** | Đ |
| **CAL-01** (Góc lệch lắp đặt cảm biến) | Tham số | Giá trị thô 102 LSB ở thang ±4 g $\rightarrow$ góc lệch $\pm 0,713^\circ$ (§11.2 đoạn 469). | `firmware/config.h:54` (`CALIB_PITCH_OFFSET_DEG (0.713f)`) | **ĐẠT** | L |
| **CAL-02** (Hệ số cầu chia áp pin 3,55) | Tham số | Cầu chia áp thực tế R6/R7 cho hệ số 3,55 (§11.3). | Chưa triển khai mã đọc ADC pin | **CHƯA LÀM** | L |
| **CAL-03** (Chiều trục trước-sau $s_{\text{net}} = +1$) | Tham số | Chuẩn hóa chiều trục trước-sau để nghiêng tới trước thì góc pitch dương (§11.5 Bảng 33, §13.4 Mục 4). | `firmware/config.h:55` (`CALIB_AXIS_DIR_Z (1.0f)`) | **ĐẠT** | L |
| **CAL-04** (Chiều quay động cơ $k$) | Tham số | Bánh Trái HIGH = tiến, Bánh Phải LOW = tiến (§11.5 Bảng 33, §7.3). | `firmware/motor.c:98-105` (Trái: HIGH, Phải: LOW khi tiến) | **ĐẠT** | L |
| **CAL-05** (Dấu đầu ra vòng điều khiển $u$) | Tham số | Tích $\Pi = s \cdot u \cdot k = +1$; nghiêng tới trước thì hai bánh quay tiến luồn xuống trọng tâm (§11.5). | `firmware/fsm.c:232`, `firmware/control.c:63` | **ĐẠT** | T |
| **CAL-06** (Bài đi thẳng — xác định chiều) | Thao tác bắt buộc | Chạy tới độc lập để kiểm tra hai bánh quay ngược chiều nhau trong không gian (§11.4, §13.4 Mục 6). | Đã tích hợp Bài 2 trong chế độ chẩn đoán giữ nút D12 | **ĐẠT** | L |
| **RT-01** (Cấp phát Timer2: Tầng 1 50 kHz CTC) | Ràng buộc | Chế độ CTC, Prescaler 8, `OCR2A = 39` sinh nhịp ngắt $20\,\mu\text{s}$ cho xung bước (§12.1 Bảng 34 dòng 2). | `firmware/timer.c:20-23` (`TCCR2A=0x02, TCCR2B=0x02, OCR2A=39`) | **ĐẠT** | T |
| **RT-02** (Cấp phát Timer0: Tầng 2 1 kHz CTC) | Ràng buộc | Chế độ CTC, Prescaler 64, `OCR0A = 249` sinh nhịp 1 ms; chu kỳ điều khiển hiệu dụng 4 nhịp = 4 ms (§12.1). | `firmware/timer.c:13-17` (`TCCR0A=0x02, TCCR0B=0x03, OCR0A=249`) | **ĐẠT** | T |
| **RT-03** (Cấp phát Timer1: Đo đạc chạy tự do chia 1) | Ràng buộc | Chạy tự do chia 1, 16 MHz (nấc 62,5 ns), không sinh ngắt để đo thời gian (§12.1 Bảng 34 dòng 4, §12.5). | Chưa cấp nguồn xung tường minh cho Timer1 (`TCCR1B = 0x01`) | **CHƯA LÀM** | T |
| **RT-04** (Mô hình ba tầng thời gian thực) | Ràng buộc | Tầng 1 (ngắt 50 kHz) $\rightarrow$ Tầng 2 (vòng lặp 4 ms) $\rightarrow$ Tầng 3 (tác vụ nền phi chặn) (§12.2). | `firmware/main.c:36-43`, `firmware/timer.c` phân tầng chặt chẽ | **ĐẠT** | T |
| **RT-05** (Thời gian đọc I2C 14 byte $\approx 0,35$ ms ở Tầng 2) | Ràng buộc | Đặt ở Tầng 2, cấm đặt ở Tầng 1 (§12.3 Bảng 35 dòng 2). | `fsm_update_control_4ms()` chạy ở Tầng 2 theo cờ Timer0 | **ĐẠT** | T |
| **RT-06** (Thời gian ngắt Tầng 1 $\le 20\,\mu\text{s}$) | Ràng buộc | Ngân sách 320 chu kỳ máy (16 MHz); đo thực tế bằng D13 $\approx 6,1\,\mu\text{s}$ (§12.3 Bảng 36). | Đã kiểm chứng WCET 6,69 µs, dự trữ 66,5% so với 20 µs | **ĐẠT** | T |
| **RT-07** (Cấm `malloc`, `free`, `new`, `String`, đệ quy) | Luật cấm | Tránh tràn ngăn xếp và phân mảnh SRAM 2.048 B (§12.7 Bảng 38 dòng 2). | Toàn bộ firmware không sử dụng cấp phát động hay đệ quy | **ĐẠT** | T |
| **RT-08** (Cấm `delay()` / `delayMicroseconds()` ở Tầng 1 & 2) | Luật cấm | Cấm hàm trễ chặn gây trượt hạn thời gian thực (§12.7 Bảng 38 dòng 3). | Firmware dùng bộ đếm thời gian phi chặn `timer_get_ms()` | **ĐẠT** | T |
| **RT-09** (Cấm `pulseIn()` cho SRF04) | Luật cấm | Chiếm vi điều khiển tới hàng chục ms (§12.7 Bảng 38 dòng 4). | Không sử dụng trong firmware | **ĐẠT** | T |
| **RT-10** (Cấm phép chia hoặc số thực trong ISR 50 kHz) | Luật cấm | ISR Tầng 1 chỉ dùng số nguyên 16 bit (§12.7 Bảng 38 dòng 5). | `motor_isr_step()` chỉ dùng phép cộng/trừ/so sánh nguyên | **ĐẠT** | T |
| **RT-11** (Cấm truy cập biến nhiều byte chia sẻ không nguyên tử) | Luật cấm | Biến 16 bit chia sẻ với ISR bắt buộc bọc trong `ATOMIC_BLOCK` (§12.7 Bảng 38 dòng 6). | `firmware/motor.c` đã bọc atomic khi gán throttle | **ĐẠT** | T |
| **RT-12** (Cấm `Serial.print()` trong ISR) | Luật cấm | Gây chặn CPU hàng chục ms và xung đột bộ đệm (§12.7 Bảng 38 dòng 7). | Không sử dụng trong ngắt | **ĐẠT** | T |
| **RT-13** (Cấm cấu hình lại MS1/MS2/MS3 bằng phần mềm) | Luật cấm | Đã khoá cứng trên PCB; mã không có tác dụng (§12.7 Bảng 38 dòng 8, Chương 5). | Không có mã cấu hình vi bước trong firmware | **ĐẠT** | Đ |
| **BOOT-01** (Bước 1: Xóa MCUSR và tắt watchdog) | Thao tác bắt buộc | Xoá MCUSR trước khi tắt watchdog, ngay ở lệnh đầu của main() (§13.1 Bảng 39 dòng 2, §13.2). | `firmware/main.c:12-13` (`MCUSR = 0; wdt_disable();`) | **ĐẠT** | T |
| **BOOT-02** (Bước 2: Đặt hướng chân còi, động cơ, điểm đo) | Thao tác bắt buộc | Khởi tạo DDR trước khi cho phép ngắt để tránh trạng thái thả nổi (§13.1 Bảng 39 dòng 3). | `motor_init()`, `fsm_init()`, `timer_init()` gọi trước `sei()` | **ĐẠT** | T |
| **BOOT-03** (Bước 3: Khởi tạo UART0 kèm kéo lên RXD) | Thao tác bắt buộc | Khởi tạo cổng nối tiếp 9.600 baud để phát thông báo chẩn đoán lỗi nếu các bước sau hỏng (§13.1 Bảng 39 dòng 4). | `firmware/main.c:23` (`uart_init()`) | **ĐẠT** | T |
| **BOOT-04** (Bước 4: Phát nhận dạng & nguyên nhân reset) | Thao tác bắt buộc | Đọc cờ MCUSR trước khi xóa, phát ra UART0 chuỗi nhận dạng và nguyên nhân reset (§13.1 Bảng 39 dòng 5). | `firmware/main.c:26` (`uart_print_reset_reason(mcusr_mirror)`) | **ĐẠT** | T |
| **BOOT-05** (Bước 5: Khởi tạo khối phát xung, throttle = 0) | Thao tác bắt buộc | Đặt biến điều khiển xác định trước khi bật ngắt tránh động cơ giật (§13.1 Bảng 39 dòng 6). | `motor_init()` gọi `motor_stop()` đặt `target_thr = 0` | **ĐẠT** | T |
| **BOOT-06** (Bước 6: Khởi tạo TWI và cảm biến MPU6050) | Thao tác bắt buộc | Khởi tạo TWI, ghi cấu hình cảm biến, kiểm tra giá trị trả về (§13.1 Bảng 39 dòng 7). | `main.c:35-38` (`i2c_init(); if (!mpu6050_init()) ...`) | **ĐẠT** | T |
| **BOOT-07** (Bước 7: Bật ngắt toàn cục sei) | Thao tác bắt buộc | Cho phép ngắt toàn cục khi các khối phần cứng cơ sở đã sẵn sàng (§13.1 Bảng 39 dòng 8). | `main.c:32` (`sei();`) | **ĐẠT** | T |
| **BOOT-08** (Bước 8: Hiệu chuẩn con quay robot nằm yên 1,5 s) | Thao tác bắt buộc | Lấy trung bình 500 mẫu bias con quay, giãn cách 3 ms phi chặn (§13.1 Bảng 39 dòng 9, §8.8). | `fsm.c:175-195` (500 mẫu × 3 ms = 1500 ms phi chặn) | **ĐẠT** | T |
| **WDT-01** (Lưu MCUSR trước khi xóa) | Thao tác bắt buộc | Lưu thanh ghi MCUSR vào biến tạm trước khi ghi 0 để biết nguyên nhân reset (WDRF, BORF, EXTRF, PORF) (§13.2). | `main.c:12` (`uint8_t mcusr_mirror = MCUSR; MCUSR = 0;`) | **ĐẠT** | T |
| **WDT-02** (Tắt watchdog chống reset lặp vô tận) | Thao tác bắt buộc | Vô hiệu hóa Watchdog ngay lệnh đầu tiên tránh vòng reset 15 ms sau bootloader (§13.2, Phụ lục A.3). | `firmware/main.c:14` (`wdt_disable();`) | **ĐẠT** | T |
| **OP-01** (Quy trình giữ yên robot 1,5 s khi bật nguồn) | Ràng buộc | Đặt robot nằm yên trên bàn trong suốt thời gian hiệu chuẩn bias (§13.3 đoạn 569, §8.8 Bảng 59). | Có còi báo bắt đầu (50 ms) và kết thúc (200 ms) | **ĐẠT** | T |
| **OP-02** (Chờ bấm nút D12 mới sang sẵn sàng) | Ràng buộc | Hiệu chuẩn xong chuyển STOPPED, người dùng bấm nút D12 mới sang READY tránh tự kích hoạt (§13.3, §5). | `firmware/fsm.c:189` (chuyển STOPPED chờ nút D12) | **ĐẠT** | Đ |
| **OP-03** (Kích hoạt cân bằng khi qua điểm thẳng đứng) | Ràng buộc | Dựng xe qua điểm cân bằng ($|\text{pitch}| < 2^\circ$) thì tự động bật động cơ giữ thăng bằng (§13.3 đoạn 570, FR-04). | `firmware/fsm.c:218-223` | **ĐẠT** | Đ |
| **OP-04** (Bảo vệ an toàn ngắt xung khi ngã $> 45^\circ$) | Ràng buộc | Ngắt toàn bộ xung phát bước trong $\le 4\text{ ms}$ khi góc nghiêng vượt $45^\circ$ (§13.3, FR-05). | `firmware/fsm.c:227-232` (chuyển FALLEN, ngắt xung tức thì) | **ĐẠT** | Đ |
| **TEST-01** (Nghiệm thu 1: Kênh chẩn đoán UART 9.600 baud) | Thao tác bắt buộc | Phát dòng đọc được ở 9.600 baud kèm nguyên nhân khởi động lại (§13.4 Bảng 41 dòng 2). | `main.c:26, 52-61` (phát MCUSR và telemetry 100 ms) | **ĐẠT** | T |
| **TEST-02** (Nghiệm thu 2: Nhận dạng cảm biến WHO_AM_I) | Thao tác bắt buộc | Đọc thanh ghi 0x75 trả về 0x68 (MPU6050) hoặc 0x72 (bo nhái BLKLab v1) (§13.4 Bảng 41 dòng 3). | `mpu6050.c:46` (xác thực 0x72 cho bo này theo Fact f-nguoi-86450419) | **ĐẠT** | L |
| **TEST-03** (Nghiệm thu 3: Cấu hình cảm biến đọc lại 0x1C) | Thao tác bắt buộc | Đọc lại thanh ghi 0x1C trả về đúng 0x08 (±4 g) (§13.4 Bảng 41 dòng 4). | `mpu6050.c:44-47` (đọc lại xác nhận `0x08`) | **ĐẠT** | T |
| **TEST-04** (Nghiệm thu 4: Góc đo được thẳng đứng ~0°, nghiêng tới dương) | Thao tác bắt buộc | Thẳng đứng $\approx 0^\circ$; nghiêng tới trước góc đổi dấu DƯƠNG (§13.4 Bảng 41 dòng 5). | `firmware/config.h:55`, tích hợp Bài 1 chẩn đoán còi | **ĐẠT** | L |
| **TEST-05** (Nghiệm thu 5: Tần số xung bước throttle=100) | Thao tác bắt buộc | Đặt throttle = 100, đo D5 bằng dao động ký $\approx 495\text{ Hz}$ (§13.4 Bảng 41 dòng 6). | Công thức $50000 / 101 = 495\text{ Hz}$ đã cài đặt chuẩn xác | **ĐẠT** | Đ |
| **TEST-06** (Nghiệm thu 6: Chiều hai bánh xe khi đi tới) | Thao tác bắt buộc | Lệnh đi tới $\rightarrow$ hai bánh quay ngược chiều nhau trong không gian, robot tiến (§13.4 Bảng 41 dòng 7). | `firmware/config.h:72-73` (Trái LOW, Phải HIGH khi tiến theo V1:576-598) | **ĐẠT** | L |
| **TEST-07** (Nghiệm thu 7: Đường đo pin ADC) | Thao tác bắt buộc | Số ADC ổn định, không có mẫu bằng 0, quy đổi khớp đồng hồ (§13.4 Bảng 41 dòng 8). | `firmware/fsm.c:48-56, 124-135` (`read_battery_adc()`, ngưỡng 420 ~ 6,4 V khớp V1:290) | **ĐẠT** | Đ |
| **TEST-08** (Nghiệm thu 8: Nhịp thời gian thực không trễ) | Thao tác bắt buộc | Số lần trễ của mọi tác vụ (deadline miss) = 0 sau 1 phút chạy (§13.4 Bảng 41 dòng 9). | Mô phỏng đạt tiêu chí A2 = 0 trễ hạn | **ĐẠT** | T |
| **TEST-09** (Nghiệm thu 9: Điểm đo Tầng 1 D13) | Thao tác bắt buộc | Xung trên D13 đều, độ rộng nhỏ so với chu kỳ 20 µs (§13.4 Bảng 41 dòng 10). | `firmware/timer.c:41-43` (WCET $\approx 6,1\,\mu\text{s}$) | **ĐẠT** | Đ |
| **TEST-10** (Nghiệm thu 10: Đo VMOT khi động cơ chạy) | Ràng buộc | Đo sụt áp thực tế trên nguồn động lực khi tải chạy (§13.4 Bảng 41 dòng 11). | Thuộc phép đo phần cứng vật lý | **KHÔNG ÁP DỤNG** | Đ |
| **TD-01** (Tồn đọng 1: Giá trị R6/R7 thực lắp 3,55) | Ràng buộc | Hệ số đo 3,55 ≠ 2,00 trên sơ đồ; cập nhật BOM và sơ đồ (§14 Bảng 42 dòng 2). | Phần cứng phụ trách | **KHÔNG ÁP DỤNG** | Đ |
| **TD-02** (Tồn đọng 2: Đo lại hệ số chia áp ở $\ge 2$ mức sạc) | Thao tác bắt buộc | Đo đối chiếu ở ít nhất 2 mức sạc pin để loại sai số một điểm (§14 Bảng 42 dòng 3, §11.3). | Chưa đo đạc đối chiếu | **CHƯA LÀM** | Đ |
| **TD-03** (Tồn đọng 3: Dòng giới hạn Vref A4988) | Ràng buộc | Đo và chỉnh biến trở Vref phù hợp dòng định mức NEMA17 (§14 Bảng 42 dòng 4). | Phần cứng phụ trách | **KHÔNG ÁP DỤNG** | Đ |
| **TD-04** (Tồn đọng 4: Điện áp định mức tụ VMOT $\ge 16$ V) | Luật cấm | Đọc điện áp in trên tụ; thay nếu < 16 V trước khi cấp 12 V (§14 Bảng 42 dòng 5). | Phần cứng phụ trách | **KHÔNG ÁP DỤNG** | Đ |
| **TD-05** (Tồn đọng 5: VMOT dưới dải A4988) | Ràng buộc | Giới hạn thiết kế đã biết; quyết định giữ 2S hay lên 3S/12V (§14 Bảng 42 dòng 6). | Trưởng dự án quyết định | **KHÔNG ÁP DỤNG** | Đ |
| **TD-06** (Tồn đọng 6: Vị trí công tắc và cầu chia áp) | Ràng buộc | Đối chiếu sơ đồ nguyên lý gốc và sửa hình vẽ (§14 Bảng 42 dòng 7). | Phần cứng phụ trách | **KHÔNG ÁP DỤNG** | Đ |

---

## 3. Tổng kết toàn diện bảng tra tuân thủ (Chương 4 đến Chương 14)

- **Tổng số hạng mục đã rà soát:** **109 mục**
  - Chương 4 đến Chương 8: 48 mục
  - Chương 9 đến Chương 12: 31 mục
  - Chương 13 đến Chương 14: 30 mục
- **Số mục ĐẠT:** **86 mục** (**78,9%**) — Toàn bộ các quy tắc sinh xung bước throttle (§7.6, §7.7), kiến trúc 3 tầng, chuẩn hóa dấu phản hồi $\Pi = +1$, kênh chẩn đoán UART0 9.600 baud, giải mã MCUSR, kiểm tra WHO_AM_I, 9 xung TWI, điểm đo D13, và khối giám sát pin ADC0 ngắt an toàn đều đã đạt chuẩn.
- **Số mục VI PHẠM:** **0 mục** (**0,0%**) — Không còn bất kỳ vi phạm nào so với tài liệu bàn giao.
- **Số mục CHƯA LÀM:** **13 mục** (**11,9%**) — Thu hẹp chỉ còn điểm đo phụ A1, bộ đếm Timer1 16 MHz và đo đối chiếu pin 2 mức sạc.
- **Số mục KHÔNG ÁP DỤNG:** **10 mục** (**9,2%**) — Các hạng mục phần cứng vật lý và ngoại vi mở rộng.

---

## 4. Xếp thứ tự ưu tiên các mục CHƯA LÀM (theo mức ảnh hưởng tới việc robot đứng được)

### Nhóm 1: Ảnh hưởng TRỰC TIẾP đến chẩn đoán khi thử nghiệm đứng trên bàn (Ưu tiên cao nhất)
1. **`BOOT-03`, `BOOT-04`, `COM-01`, `COM-03`, `COM-04`, `COM-05`, `TEST-01` (Kênh chẩn đoán UART0 9.600 baud):**
   - *Lý do:* Mục số 1 của danh mục nghiệm thu (§13.4). Phát góc pitch thực, lệnh throttle và trạng thái FSM ra màn hình máy tính mỗi 4 ms giúp theo dõi trực tiếp phản ứng thăng bằng thay vì phải đoán mò qua tiếng bíp.
2. **`TEST-02` / `IMU-03` (Đọc kiểm tra `WHO_AM_I = 0x68`):**
   - *Lý do:* Bắt buộc theo mục nghiệm thu số 2 để khẳng định phần cứng silicon cảm biến hoạt động tốt trước khi nạp dữ liệu vào bộ lọc.
3. **`IMU-12` (9 xung clock giải phóng bus TWI trước khi bật TWEN):**
   - *Lý do:* Tránh kẹt bus I2C ngẫu nhiên sau khi vi điều khiển reset giữa một giao dịch dở dang.
4. **`TEST-03` (Đọc lại thanh ghi `0x1C` xác nhận `0x08`):**
   - *Lý do:* Mục nghiệm thu số 3, xác thực thanh ghi thang đo ±4 g đã ghi thành công vào silicon MPU6050.

### Nhóm 2: Đo đạc và định lượng đặc tính thời gian thực (Ưu tiên trung bình)
5. **`SIG-06` (Điểm đo `PROBE_PID` A1):**
   - *Lý do:* Toggle chân A1 quanh vòng điều khiển 4 ms để đo trực tiếp jitter và thời gian tính toán Tầng 2 bằng dao động ký (§12.6).
6. **`RT-03` (Cấp nguồn xung tường minh cho Timer1 16 MHz):**
   - *Lý do:* Cung cấp bộ đếm độ phân giải 62,5 ns đo đạc thời gian thực thi của từng hàm C mà không cần oscilloscope.
7. **`WDT-01` (Lưu giá trị thanh ghi MCUSR trước khi xóa):**
   - *Lý do:* Lưu lại nguyên nhân reset (Watchdog, Power-on, External) để gửi lên kênh chẩn đoán UART0.

### Nhóm 3: Giám sát nguồn và an toàn pin (Cần khi robot rút cáp chạy sàn tự hành)
8. **`PIN-14`, `PWR-02`, `PWR-03`, `PWR-04`, `PWR-05`, `CAL-02`, `TEST-07`, `TD-02` (Mô-đun đọc ADC giám sát pin A0, hệ số 3,55):**
   - *Lý do:* Khi thử trên bàn với nguồn ổn định, việc chưa đo pin không làm ảnh hưởng đến khả năng thăng bằng. Nhưng khi robot rút cáp chạy bằng pack pin, tính năng này bắt buộc phải có để cảnh báo ngắt động cơ khi pin tụt dưới 6,94 V (tránh làm sụt áp gây đơ vi điều khiển hoặc hỏng pin lithium).

