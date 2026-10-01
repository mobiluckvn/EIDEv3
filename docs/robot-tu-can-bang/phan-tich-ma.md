# Phân tích mã trước khi sửa

**Sẽ đổi gì:** 1. Thêm mô-đun uart.h và uart.c truyền không chặn 9600 baud kèm ring buffer và giải mã MCUSR; 2. Thêm kiểm tra WHO_AM_I=0x68 và đọc lại 0x1C=0x08 trong mpu6050.c; 3. Thêm 9 xung clock giải phóng bus TWI trong i2c.c; 4. Phát dòng chẩn đoán 100ms trong main.c/fsm.c.

**Vì sao:** Triển khai nhóm ưu tiên 1: kênh chẩn đoán UART0, xác thực WHO_AM_I, đọc lại 0x1C và giải phóng TWI

## Tệp trong phạm vi

| Tệp | Dòng | Ký hiệu | Phụ thuộc |
|---|---|---|---|
| `firmware/i2c.c` | 112 | `i2c_init`, `i2c_wait_twint`, `i2c_start`, `i2c_stop`, `i2c_write`, `i2c_read_ack`, `i2c_read_nack`, `i2c_write_byte` …+1 | `avr/io.h`, `config.h`, `i2c.h` |
| `firmware/mpu6050.c` | 132 | `mpu6050_init`, `mpu6050_read_raw`, `mpu6050_calib_reset`, `mpu6050_calib_step`, `mpu6050_calibrate_gyro`, `mpu6050_read_scaled` | `config.h`, `i2c.h`, `mpu6050.h`, `stddef.h` |
| `firmware/main.c` | 57 | `main` | `avr/interrupt.h`, `avr/wdt.h`, `config.h`, `fsm.h`, `i2c.h` |
| `firmware/fsm.c` | 253 | `buzzer_on_ms`, `fsm_enable_diagnostics`, `fsm_notify_sensor_error`, `fsm_has_sensor_error`, `fsm_init`, `fsm_get_state`, `fsm_update_background`, `fsm_update_control_4ms` | `config.h`, `filter.h`, `fsm.h`, `math.h`, `motor.h` |

## Ai đang dùng — chỗ phải xem lại sau khi sửa

* `i2c_init` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_read_ack` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_read_bytes` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_read_nack` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_start` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_stop` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_write` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `i2c_write_byte` (trong `firmware/i2c.c`) → `firmware/i2c.h`
* `mpu6050_calib_reset` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `mpu6050_calib_step` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `mpu6050_calibrate_gyro` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `mpu6050_init` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `mpu6050_read_raw` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `mpu6050_read_scaled` (trong `firmware/mpu6050.c`) → `firmware/mpu6050.h`
* `main` (trong `firmware/main.c`) → `sim/main.c`
* `fsm_enable_diagnostics` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_get_state` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_has_sensor_error` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_init` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_notify_sensor_error` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_update_background` (trong `firmware/fsm.c`) → `firmware/fsm.h`
* `fsm_update_control_4ms` (trong `firmware/fsm.c`) → `firmware/fsm.h`

## Giới hạn của phép dò này

Đây là dò **tên ký hiệu trong văn bản**, không phải đồ thị gọi hàm. Nó có thể kêu thừa (tên trùng nằm trong chú thích hay chuỗi) nhưng không bỏ sót chỗ gọi thẳng. Gọi gián tiếp qua con trỏ hàm, macro nối chuỗi, hay phản chiếu thì nó **không thấy** — chỗ nào nghi thì đọc bằng mắt.

## Nhận định của tác tử con `code-analyst`

*Tầng tin cậy: **DONG** · kết luận: `chua_du_du_kien`. Phần trên là DỮ KIỆN do mã quét; phần này là ĐỌC HIỂU — hai thứ khác nhau.*

*(không có tóm tắt)*
