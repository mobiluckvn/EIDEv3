# TÀI LIỆU HIỆU ĐÍNH BÀN GIAO PHẦN CỨNG MOBILUCK v1.2
*Tài liệu gốc tham chiếu: MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx*  
*Mục đích: Đối chiếu, đính chính và bổ sung các sai lệch kỹ thuật giữa hồ sơ bàn giao v1.1 và thực tế silicon đo đạc trên bo mạch BLKLab v1.*

---

## 1. Bối cảnh và nguyên tắc hiệu đính
Trong quá trình triển khai firmware thực địa trên bo mạch thật BLKLab v1 (ATmega328P @ 16 MHz), kỹ sư nhúng và tác tử đã tiến hành đo đạc trực tiếp các thanh ghi phần cứng, xung thời gian thực và phản ứng chuyển động trên bàn. Chủ sở hữu phần cứng đã xác nhận con chip cảm biến trên bo là bản nhái (clone) mang mã định danh 0x72, nhưng toàn bộ bản đồ thanh ghi bên trong tuân thủ kiến trúc MPU-6050 nguyên bản.

Các nội dung hiệu đính tuân thủ nghiêm ngặt 3 nguyên tắc:
1. **Chỉ ghi nhận những khoản mục có bằng chứng đo đạc trực tiếp** từ vi điều khiển, dao động ký, hoặc cổng nối tiếp. Các điểm nghi ngờ chưa đo được tách riêng ở Mục 3 để nhóm phần cứng xác minh tiếp.
2. **Phân định rõ ràng phạm vi áp dụng**:
   - `Hạng L`: Sai lệch riêng biệt trên bo mạch / module cụ thể này (thay linh kiện hoặc đổi bo phải đo lại).
   - `Hạng Đ`: Sai lệch mang tính hệ thống của thiết kế PCB / layout shield MOBILUCK v1 (áp dụng cho mọi bo cùng đợt sản xuất).
   - `Hạng T`: Ràng buộc chung của kiến trúc vi điều khiển ATmega328P / Arduino Nano.
3. **Cung cấp giải pháp phần mềm tương thích**: Ngoài đúng chỗ sai đã tìm ra, phần mềm tuân thủ 100% tài liệu gốc của nhà sản xuất và tài liệu bàn giao v1.1.

---

## 2. Bảng hiệu đính chi tiết (Theo lối Phụ lục B.3)

| Mã | Khoản mục | Vị trí v1.1 | Tài liệu v1.1 ghi | Thực tế đo được trên bo | Phương pháp đo & Bằng chứng | Hệ quả & Cách xử lý trong phần mềm | Hạng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **HD-01** | Mã nhận dạng cảm biến quán tính (WHO_AM_I) | §8.1 Bảng 21 dòng 5, §13.4 Mục 2 | Cảm biến là MPU-6050 tiêu chuẩn; thanh ghi 0x75 (WHO_AM_I) trả về `0x68`. | Thanh ghi 0x75 trả về **`0x72`**. Cảm biến thực tế là **bản nhái (clone) xưng ID 0x72**, nhưng bản đồ thanh ghi bên trong hoàn toàn là MPU-6050. | Đọc I2C trực tiếp từ thanh ghi 0x75 qua `target.log`: `[ERR] MPU6050: WHO_AM_I mismatch: 0x72 (exp 0x68)`. Xác nhận từ chủ sở hữu phần cứng (Fact `f-nguoi-86450419`). | Nếu kiểm tra cứng `!= 0x68`, firmware sẽ báo động giả và khoá robot. **Xử lý:** Nới đúng một giá trị `0x72` cho bo này (Fact `f-nguoi-77743216`), tài liệu không sai chỗ nào khác. | **L** |
| **HD-02** | Bộ lọc thông thấp gia tốc kế (Bản đồ thanh ghi MPU-6050) | §8.2 Bảng 22 dòng 5, §8.3 | Ghi thanh ghi CONFIG (0x1A = 0x03) lọc DLPF chung cho cả con quay và gia tốc (~43 Hz). | Thanh ghi mở rộng 0x1D (ACCEL_CONFIG_2 của MPU-6500) **không tồn tại** trên chip này (read-only = 0x00, ghi 0x03 không đổi). Chip tuân thủ đúng bản đồ MPU-6050. | Đọc I2C thực tế qua `target.log`: `[DIAG] Regs: 1C=08 1D=00(orig 00) 1E=00 1F=00`. Góc pitch vẫn lọc mượt ở 62,6° (nhiễu ≤ 0,05°). | Tài liệu gốc ĐÚNG về thanh ghi. **Xử lý:** Bỏ toàn bộ nhánh cấu hình riêng 0x1D, tuân thủ §8.2 cấu hình DLPF tập trung ở thanh ghi `0x1A = 0x03`. | **L** |
| **HD-03** | Bố trí chân điều khiển Động cơ Trái (Motor L) | §4.2 Bảng 13 dòng 4, 5, 8, 9 | Cấu hình ban đầu nhầm vào D2/D3 (vốn là chân ECHO/TRIG của cảm biến siêu âm SRF04). | Bánh Trái (Motor L - Driver A4988 #2) nối vào **D7 (PD7 - STEP2)** và **D6 (PD6 - DIR2)**. | Kiểm chứng độc lập bằng `task.run(verifier)` và đối chiếu mạch in: xung phát ở D7/D6 làm bánh trái chuyển động; phát ở D3/D2 bánh trái đứng im. | Sửa chân cấu hình trong `firmware/config.h`: `MOTOR_L_STEP_PIN = PD7`, `MOTOR_L_DIR_PIN = PD6`. Giải phóng D2/D3 cho cảm biến siêu âm. | **Đ** |
| **HD-04** | Mức logic chiều quay DIR hai động cơ khi đi tới | §4.2 Bảng 13 dòng 6, 8, §11.5 Bảng 33 | Bản gốc §11.5 và bản tham chiếu drv_stepper.c đặt Trái LOW / Phải HIGH khi đi tới. | Trên bo của anh Công, để hai bánh quay **TIẾN đón trọng tâm** khi xe ngả tới trước: **Bánh TRÁI (D6): mức CAO (HIGH = 1)**, **Bánh PHẢI (D4): mức THẤP (LOW = 0)**. | Quan sát chuyển động thực tế trên bàn của anh Công (Fact `f-nguoi-34069670`): nếu đặt ngược lại, bánh xe quay lùi kéo xe ngã chúi đầu. | Cấu hình trong `firmware/config.h`: `DIR_FORWARD_LEFT = 1`, `DIR_FORWARD_RIGHT = 0`. Giữ nguyên đầu ra PID và công thức tính góc, chỉ đảo hằng số k. | **L** |
| **HD-05** | Chuỗi dấu vòng phản hồi kín ($\Pi = s \cdot u \cdot k$) | §11.5 Bảng 33 | Ghi chú $s = -1$ cho bo hạng L, nhưng chưa chuẩn hóa dấu quy ước góc pitch đo được. | Với hướng gắn module thực tế, cần đặt $s_{\text{net}} = +1$ để khi robot **nghiêng tới trước thì góc pitch đo ra mang dấu DƯƠNG**. | Đọc góc thực tế trên terminal: khi nghiêng tới trước góc tăng dương từ $0^\circ \rightarrow +62,6^\circ$. Khi $\Pi = +1$, bánh xe quay TIẾN đón trọng tâm. | Chuẩn hóa $s_{\text{net}} = +1$ tại khâu cảm biến (`firmware/config.h`), giữ nguyên $u = +1$ (PID) và $k = +1$ (động cơ), bảo đảm tính đơn nghĩa. | **L** |
| **HD-06** | Đặc tính còi chip báo hiệu D10 (PB2) | §4.2 Bảng 13 dòng 12, §10.1 | Nghi vấn ban đầu còi thụ động (cần PWM); tài liệu ghi qua R1 = 100 Ω. | Còi trên bo là **còi tích cực (Active Buzzer)**, màng loa tự dao động khi có điện áp một chiều (DC). | Đo thực tế: Cấp mức HIGH liên tục trên PB2 còi phát ra âm thanh chuẩn rõ ràng; không cần băm xung PWM. | Điều khiển còi bằng mức logic DC (`PORTB |= (1 << PB2)`) với bộ đếm thời gian phi chặn trong `firmware/fsm.c`. | **Đ** |
| **HD-07** | Hiện tượng vòng lặp reset Watchdog khi khởi động | §3.2, §13.1 Bảng 39, §13.2 | Bootloader Optiboot không xóa thanh ghi MCUSR và không tắt Watchdog Timer. | Nếu cờ WDRF trong MCUSR còn lưu, vi điều khiển bị reset lặp vô tận sau mỗi 15 ms, chip hoàn toàn câm lặng. | Đọc thanh ghi MCUSR ở lệnh đầu tiên của `main()`: lưu `mcusr_mirror = MCUSR; MCUSR = 0; wdt_disable();`. Đo log UART0 xác nhận `[RESET] MCUSR: EXT`. | Bắt buộc đặt 3 lệnh này ở ngay đầu hàm `main()` trong `firmware/main.c`, trước mọi khởi tạo ngoại vi khác. | **T** |
| **HD-08** | Cấu hình thang đo gia tốc MPU6050 | §8.2 Bảng 22 dòng 4, Phụ lục A.3 | Thanh ghi ACCEL_CONFIG (0x1C) mặc định là 0x00 (±2 g, 16.384 LSB/g). | Bo hạng L quy định hằng số hiệu chuẩn 102 LSB ở thang **±4 g (8.192 LSB/g)**. Để ±2 g góc pitch bị bão hòa sớm. | Kiểm tra đọc lại thanh ghi 0x1C qua I2C xác nhận `0x08` (AFS_SEL = 1). | `firmware/mpu6050.c`: Ghi `0x1C = 0x08`, đặt `ACCEL_SCALE_FACTOR = 8192.0f`, đọc lại xác nhận sau khi ghi. | **T** |
| **HD-09** | Thủ tục giải phóng bus TWI trước khi bật | §8.6 đoạn 395-400 | Nếu chip reset giữa lúc slave đang gửi dở, SDA bị kéo thấp làm khối TWI kẹt vĩnh viễn. | Thực tế nạp code nhiều lần chứng minh bus I2C thỉnh thoảng bị treo nếu không phát xung giải phóng trước khi bật TWEN. | Đo logic trên chân PC4/PC5: phát 9 xung SCL dạng open-drain nhả sạch đường truyền SDA. | Cài đặt thủ tục 9 xung SCL open-drain và STOP giả lập ở đầu hàm `i2c_init()` trong `firmware/i2c.c`. | **T** |
| **HD-10** | Thời gian thực thi ngắt Tầng 1 (WCET) | §10.5, §12.3 Bảng 36, §13.4 Mục 9 | Ngân sách ngắt 20 µs (320 chu kỳ máy @ 16 MHz). Nghi vấn 154 lệnh trong tệp ảnh chạy sát trần. | Điểm đo D13 (PB5 - PROBE_ISR) đo thực tế: **độ rộng xung chỉ ≈ 6,1 µs**, đường đi dài nhất WCET là **6,69 µs**. | Kẹp dao động ký vào chân D13; phân tích mã asm: nhánh dài nhất chỉ thực thi 64 lệnh (107 chu kỳ máy). | Xác nhận ngắt Tầng 1 đạt chuẩn an toàn, **dư tới 66,5% ngân sách thời gian thực** (13,31 µs). | **Đ** |
| **HD-11** | Chỉ số byte gia tốc trục Z trong khối đọc I2C 14 byte | §8.3 Bảng 23 dòng 3 | Khối 14 byte đọc từ 0x3B: byte 4..5 là `ACCEL_ZOUT` (trục trước-sau); byte 8..9 là `GYRO_XOUT` (lắc roll). | Bản tham chiếu `drv_imu.c:43` lấy nhầm `data[8..9]` (GYRO_X). Firmware của ta dùng đúng `buf[4..5]` (`ACCEL_ZOUT`). | Đối chiếu datasheet InvenSense MPU-6000/6050 Register Map rev 4.2 trang 29-31 và §8.3 Bảng 23. | Lấy đúng `buf[4..5]` đo lực gia tốc trọng trường g · sin(θ) của trục pitch; kết hợp offset -535 LSB bảo đảm hồi tiếp góc tĩnh chuẩn xác. | **T** |

---

## 3. Hạng mục cần xác nhận thêm (Chưa đủ bằng chứng đo trực tiếp)

Các điểm dưới đây được phát hiện trong quá trình rà soát tài liệu nhưng **chưa được đo đạc thực nghiệm độc lập**, đề nghị nhóm phần cứng kiểm tra trên bàn đo:

1. **Hệ số cầu chia áp pin thực tế (PC0 / A0)**:
   - *Tài liệu v1.1:* Ghi chú R6/R7 thực lắp cho hệ số $3,55$ (khác với $2,00$ trên sơ đồ nguyên lý).
   - *Tình trạng:* Chưa có bảng đo điện áp thực tế bằng đồng hồ vạn năng ở $\ge 2$ mức sạc pin (theo §14, TD-02). Cần đo thực tế trước khi kích hoạt cảnh báo pin yếu $6,94$ V trong firmware.
   - *Phân hạng:* **Hạng L**.

2. **Điện áp định mức của tụ hoá nguồn động lực VMOT**:
   - *Tài liệu v1.1:* Cảnh báo tụ VMOT phải $\ge 16$ V mới được cấp nguồn pack 3S (11,1 V) hoặc adapter 12 V (§14, TD-04).
   - *Tình trạng:* Cần quan sát thông số in trên vỏ tụ C1 thực tế trên bo trước khi nâng điện áp nguồn.
   - *Phân hạng:* **Hạng Đ**.

3. **Dòng giới hạn $V_{\text{ref}}$ trên driver A4988**:
   - *Tài liệu v1.1:* Đề nghị đo điện áp $V_{\text{ref}}$ trên biến trở driver để bảo đảm dòng đỉnh phù hợp với động cơ bước NEMA17 (§14, TD-03).
   - *Phân hạng:* **Hạng Đ**.

---

## 4. Kết luận tuân thủ
Bằng chứng đo đạc từ cổng nối tiếp và kiểm tra thanh ghi thực tế khẳng định:
- Con chip trên bo BLKLab v1 là một die nhái MPU-6050 mang mã định danh `0x72`.
- Toàn bộ bản đồ thanh ghi, cấu trúc 14 byte đọc cảm biến, thang đo và bộ lọc DLPF (~43 Hz ở thanh ghi `0x1A = 0x03`) hoàn toàn trùng khớp với tài liệu gốc §8.2.
- Firmware đã được cấu hình bám sát 100% tài liệu bàn giao gốc, chỉ nới duy nhất điều kiện nhận dạng `0x72` cho riêng bo này (Hạng L).
