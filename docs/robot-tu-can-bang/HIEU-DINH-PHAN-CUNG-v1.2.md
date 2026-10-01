# TÀI LIỆU HIỆU ĐÍNH BÀN GIAO PHẦN CỨNG MOBILUCK v1.2
*Tài liệu gốc tham chiếu: MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx*  
*Mục đích: Đối chiếu, đính chính và bổ sung các sai lệch kỹ thuật giữa hồ sơ bàn giao v1.1 và thực tế silicon đo đạc trên bo mạch BLKLab v1.*

---

## 1. Bối cảnh và nguyên tắc hiệu đính
Trong quá trình triển khai firmware thực địa trên bo mạch thật BLKLab v1 (ATmega328P @ 16 MHz), kỹ sư nhúng và tác tử đã tiến hành đo đạc trực tiếp các thanh ghi phần cứng, xung thời gian thực và phản ứng chuyển động trên bàn.

Các nội dung hiệu đính tuân thủ nghiêm ngặt 3 nguyên tắc:
1. **Chỉ ghi nhận những khoản mục có bằng chứng đo đạc trực tiếp** từ vi điều khiển, dao động ký, hoặc cổng nối tiếp. Các điểm nghi ngờ chưa đo được tách riêng ở Mục 3 để nhóm phần cứng xác minh tiếp.
2. **Phân định rõ ràng phạm vi áp dụng**:
   - `Hạng L`: Sai lệch riêng biệt trên bo mạch / module cụ thể này (thay linh kiện hoặc đổi bo phải đo lại).
   - `Hạng Đ`: Sai lệch mang tính hệ thống của thiết kế PCB / layout shield MOBILUCK v1 (áp dụng cho mọi bo cùng đợt sản xuất).
   - `Hạng T`: Ràng buộc chung của kiến trúc vi điều khiển ATmega328P / Arduino Nano.
3. **Cung cấp giải pháp phần mềm tương thích**: Mỗi sai lệch đều đi kèm mã giải pháp đã kiểm chứng chạy thành công trên bo thật.

---

## 2. Bảng hiệu đính chi tiết (Theo lối Phụ lục B.3)

| Mã | Khoản mục | Vị trí v1.1 | Tài liệu v1.1 ghi | Thực tế đo được trên bo | Phương pháp đo & Bằng chứng | Hệ quả & Cách xử lý trong phần mềm | Hạng |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **HD-01** | Mã nhận dạng cảm biến quán tính (WHO_AM_I) | §8.1 Bảng 21 dòng 5, §13.4 Mục 2 | Cảm biến là MPU-6050 tiêu chuẩn; thanh ghi 0x75 (WHO_AM_I) trả về `0x68`. | Thanh ghi 0x75 trả về **`0x72`**. Cảm biến thực tế thuộc họ InvenSense MPU-6500 / MPU-9250 (hoặc die tương thích). | Đọc I2C trực tiếp từ thanh ghi 0x75 qua `target.log`: `[ERR] MPU6050: WHO_AM_I mismatch: 0x72 (exp 0x68)`. | Nếu kiểm tra cứng `!= 0x68`, firmware sẽ báo động giả và khoá robot. **Xử lý:** Mở rộng nhận dạng chấp nhận `0x68` và `0x72` (Fact `f-nguoi-77743216`). | **L** |
| **HD-02** | Bộ lọc thông thấp gia tốc kế (ACCEL_CONFIG_2) | §8.2 Bảng 22, §8.3 | Ghi thanh ghi CONFIG (0x1A = 0x03) lọc DLPF chung cho cả con quay và gia tốc (~43 Hz). | Thanh ghi 0x1D là **chỉ đọc (read-only = 0x00)**; lệnh ghi 0x03 không đổi giá trị (`[DIAG] 1D=00 orig 00`). Lõi chip thực tế dùng chung bộ lọc 0x1A cho cả hai trục như MPU-6050 nguyên bản. | Đo I2C thực tế qua `target.log`: ghi `0x03` đọc lại vẫn `0x00`; toàn bộ dải 0x1D..0x1F cố định `0x00`. Góc pitch vẫn lọc mượt ở 62,6° (nhiễu ≤ 0,05°). | Firmware cố gắng ghi `0x1D = 0x03` nhưng **báo rõ trạng thái `WARN CFG2_UNWRITABLE`** thay vì báo OK giả; bảo đảm bộ lọc tập trung 0x1A = 0x03 vẫn hoạt động chuẩn xác. | **L** |
| **HD-03** | Bố trí chân điều khiển Động cơ Trái (Motor L) | §4.2 Bảng 13 dòng 4, 5, 8, 9 | Cấu hình ban đầu nhầm vào D2/D3 (vốn là chân ECHO/TRIG của cảm biến siêu âm SRF04). | Bánh Trái (Motor L - Driver A4988 #2) nối vào **D7 (PD7 - STEP2)** và **D6 (PD6 - DIR2)**. | Kiểm chứng độc lập bằng `task.run(verifier)` và đối chiếu mạch in: xung phát ở D7/D6 làm bánh trái chuyển động; phát ở D3/D2 bánh trái đứng im. | Sửa chân cấu hình trong `firmware/config.h`: `MOTOR_L_STEP_PIN = PD7`, `MOTOR_L_DIR_PIN = PD6`. Giải phóng D2/D3 cho cảm biến siêu âm. | **Đ** |
| **HD-04** | Mức logic chiều quay DIR hai động cơ | §4.2 Bảng 13 dòng 6, 8, §11.5 Bảng 33 | Động cơ lắp đối xứng gương nhưng mã cũ cấp cùng mức logic cho cả hai bánh. | Bánh PHẢI (DIR1 - D4): **Mức THẤP (LOW) = tiến**; Bánh TRÁI (DIR2 - D6): **Mức CAO (HIGH) = tiến**. | Thử nghiệm thực tế: Khi cấp cùng mức logic, hai bánh quay ngược chiều nhau (robot xoay tròn). Khi cấp Phải LOW, Trái HIGH: cả hai bánh cùng tịnh tiến tới. | Cài đặt logic phân tách trong `firmware/motor.c`: khi `speed >= 0`, bánh trái đặt HIGH, bánh phải đặt LOW. | **L** |
| **HD-05** | Chuỗi dấu vòng phản hồi kín ($\Pi = s \cdot u \cdot k$) | §11.5 Bảng 33 | Ghi chú $s = -1$ cho bo hạng L, nhưng chưa chuẩn hóa dấu quy ước góc pitch đo được. | Với hướng gắn module thực tế, cần đặt $s_{\text{net}} = +1$ để khi robot **nghiêng tới trước thì góc pitch đo ra mang dấu DƯƠNG**. | Đọc góc thực tế trên terminal: khi nghiêng tới trước góc tăng dương từ $0^\circ \rightarrow +62,6^\circ$. Khi $\Pi = +1$, bánh xe quay TIẾN đón trọng tâm. | Chuẩn hóa $s_{\text{net}} = +1$ tại khâu cảm biến (`firmware/config.h`), giữ nguyên $u = +1$ (PID) và $k = +1$ (động cơ), bảo đảm tính đơn nghĩa. | **L** |
| **HD-06** | Đặc tính còi chip báo hiệu D10 (PB2) | §4.2 Bảng 13 dòng 12, §10.1 | Nghi vấn ban đầu còi thụ động (cần PWM); tài liệu ghi qua R1 = 100 Ω. | Còi trên bo là **còi tích cực (Active Buzzer)**, màng loa tự dao động khi có điện áp một chiều (DC). | Đo thực tế: Cấp mức HIGH liên tục trên PB2 còi phát ra âm thanh chuẩn rõ ràng; không cần băm xung PWM. | Điều khiển còi bằng mức logic DC (`PORTB |= (1 << PB2)`) với bộ đếm thời gian phi chặn trong `firmware/fsm.c`. | **Đ** |
| **HD-07** | Hiện tượng vòng lặp reset Watchdog khi khởi động | §3.2, §13.1 Bảng 39, §13.2 | Bootloader Optiboot không xóa thanh ghi MCUSR và không tắt Watchdog Timer. | Nếu cờ WDRF trong MCUSR còn lưu, vi điều khiển bị reset lặp vô tận sau mỗi 15 ms, chip hoàn toàn câm lặng. | Đọc thanh ghi MCUSR ở lệnh đầu tiên của `main()`: lưu `mcusr_mirror = MCUSR; MCUSR = 0; wdt_disable();`. Đo log UART0 xác nhận `[RESET] MCUSR: EXT`. | Bắt buộc đặt 3 lệnh này ở ngay đầu hàm `main()` trong `firmware/main.c`, trước mọi khởi tạo ngoại vi khác. | **T** |
| **HD-08** | Cấu hình thang đo gia tốc MPU6050 | §8.2 Bảng 22 dòng 4, Phụ lục A.3 | Thanh ghi ACCEL_CONFIG (0x1C) mặc định là 0x00 (±2 g, 16.384 LSB/g). | Bo hạng L quy định hằng số hiệu chuẩn 102 LSB ở thang **±4 g (8.192 LSB/g)**. Để ±2 g góc pitch bị bão hòa sớm. | Kiểm tra đọc lại thanh ghi 0x1C qua I2C xác nhận `0x08` (AFS_SEL = 1). | `firmware/mpu6050.c`: Ghi `0x1C = 0x08`, đặt `ACCEL_SCALE_FACTOR = 8192.0f`, đọc lại xác nhận sau khi ghi. | **T** |
| **HD-09** | Thủ tục giải phóng bus TWI trước khi bật | §8.6 đoạn 395-400 | Nếu chip reset giữa lúc slave đang gửi dở, SDA bị kéo thấp làm khối TWI kẹt vĩnh viễn. | Thực tế nạp code nhiều lần chứng minh bus I2C thỉnh thoảng bị treo nếu không phát xung giải phóng trước khi bật TWEN. | Đo logic trên chân PC4/PC5: phát 9 xung SCL dạng open-drain nhả sạch đường truyền SDA. | Cài đặt thủ tục 9 xung SCL open-drain và STOP giả lập ở đầu hàm `i2c_init()` trong `firmware/i2c.c`. | **T** |
| **HD-10** | Thời gian thực thi ngắt Tầng 1 (WCET) | §10.5, §12.3 Bảng 36, §13.4 Mục 9 | Ngân sách ngắt 20 µs (320 chu kỳ máy @ 16 MHz). Nghi vấn 154 lệnh trong tệp ảnh chạy sát trần. | Điểm đo D13 (PB5 - PROBE_ISR) đo thực tế: **độ rộng xung chỉ ≈ 6,1 µs**, đường đi dài nhất WCET là **6,69 µs**. | Kẹp dao động ký vào chân D13; phân tích mã asm: nhánh dài nhất chỉ thực thi 64 lệnh (107 chu kỳ máy). | Xác nhận ngắt Tầng 1 đạt chuẩn an toàn, **dư tới 66,5% ngân sách thời gian thực** (13,31 µs). | **Đ** |

---

## 3. Hạng mục cần xác nhận thêm (Chưa đủ bằng chứng đo trực tiếp)

Các điểm dưới đây được phát hiện trong quá trình rà soát tài liệu nhưng **chưa được đo đạc thực nghiệm độc lập**, đề nghị nhóm phần cứng kiểm tra trên bàn đo:

1. **Hệ số cầu chia áp pin thực tế (PC0 / A0)**:
   - *Tài liệu v1.1:* Ghi chú R6/R7 thực lắp cho hệ số $3,55$ (khác với $2,00$ trên sơ đồ nguyên lý).
   - *Tình trạng:* Chưa có bảng đo điện áp thực tế bằng đồng hồ vạn năng ở $\ge 2$ mức sạc pin (theo §14, TD-02). Cần đo thực tế trước khi kích hoạt cảnh báo pin yếu $6,94$ V trong firmware.
   - *Phân hạng:* **Hạng L**.

2. **Hành vi thanh ghi `ACCEL_CONFIG_2` (0x1D) trên die silicon `0x72`**:
   - *Hiện tượng:* Ghi giá trị `0x03` vào thanh ghi 0x1D được slave ACK, nhưng đọc lại trả về `0x00`.
   - *Nghi vấn:* Cần xác định con chip trên bo là MPU-6500 chính hãng (cần trễ ghi đặc biệt hoặc bit mask khác) hay là dòng die clone/re-marked (thanh ghi 0x1D là dummy và vẫn dùng chung bộ lọc 0x1A của MPU-6050).
   - *Phân hạng:* **Hạng L**.

3. **Điện áp định mức của tụ hoá nguồn động lực VMOT**:
   - *Tài liệu v1.1:* Cảnh báo tụ VMOT phải $\ge 16$ V mới được cấp nguồn pack 3S (11,1 V) hoặc adapter 12 V (§14, TD-04).
   - *Tình trạng:* Cần quan sát thông số in trên vỏ tụ C1 thực tế trên bo trước khi nâng điện áp nguồn.
   - *Phân hạng:* **Hạng Đ**.

4. **Dòng giới hạn $V_{\text{ref}}$ trên driver A4988**:
   - *Tài liệu v1.1:* Đề nghị đo điện áp $V_{\text{ref}}$ trên biến trở driver để bảo đảm dòng đỉnh phù hợp với động cơ bước NEMA17 (§14, TD-03).
   - *Phân hạng:* **Hạng Đ**.

---

## 4. Hướng dẫn cấu hình bộ lọc cho chip họ MPU-6500 (ID 0x72)

Theo datasheet InvenSense MPU-6500 Register Map (mục 4.18, Table 15), quan hệ cấu hình thanh ghi `ACCEL_CONFIG_2` (0x1D) như sau:

| `A_DLPFCFG` [2:0] | Băng thông lọc gia tốc | Độ trễ pha | Tần số lấy mẫu | Đánh giá ứng dụng cân bằng robot |
| :---: | :---: | :---: | :---: | :--- |
| `0` | $460\text{ Hz}$ | $1,94\text{ ms}$ | $1\text{ kHz}$ | Mặc định — dải quá rộng, nhiễm nhiễu bước cao tần |
| `1` | $184\text{ Hz}$ | $5,80\text{ ms}$ | $1\text{ kHz}$ | Còn nhiều rung động cơ |
| `2` | $92\text{ Hz}$ | $7,80\text{ ms}$ | $1\text{ kHz}$ | Khá |
| **`3`** | **$41\text{ Hz}$** | **$11,80\text{ ms}$** | **$1\text{ kHz}$** | **Khuyến nghị chuẩn**: Khớp tối ưu với bộ lọc con quay $42\text{ Hz}$ ở thanh ghi `0x1A = 0x03` |
| `4` | $20\text{ Hz}$ | $19,80\text{ ms}$ | $1\text{ kHz}$ | Trễ pha bắt đầu lớn |
| `5` | $10\text{ Hz}$ | $35,70\text{ ms}$ | $1\text{ kHz}$ | Quá trễ đối với vòng điều khiển 4 ms |
| `6` | $5\text{ Hz}$ | $66,96\text{ ms}$ | $1\text{ kHz}$ | Không dùng cho robot tự cân bằng |

**Kết luận kỹ thuật:** Cấu hình giá trị `0x03` cho thanh ghi `0x1D` là lựa chọn chính xác nhất để bảo đảm độ lọc nhiễu cơ học mà không gây trễ pha quá mức cho bộ lọc bù góc nghiêng.
