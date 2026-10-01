#include "config.h"
#include "timer.h"
#include "i2c.h"
#include "mpu6050.h"
#include "motor.h"
#include "fsm.h"
#include "uart.h"
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <stdio.h>

int main(void) {
    /* WDT-01 & BOOT-01: Đọc lưu cờ reset MCUSR và vô hiệu hoá Watchdog ngay lệnh đầu tiên (§13.2, Phụ lục A.3) */
    uint8_t mcusr_mirror = MCUSR;
    MCUSR = 0;
    wdt_disable();

    /* BOOT-02: Khởi tạo chân I/O điều khiển động cơ bước A4988 và đặt hướng chân */
    motor_init();

    /* Khởi tạo máy trạng thái và chân nút nhấn/còi */
    fsm_init();

    /* BOOT-03 & COM-01..05: Khởi tạo UART0 9.600 baud và kéo lên nội bộ RXD */
    uart_init();

    /* BOOT-04 & TEST-01: Phát nhận dạng và giải mã nguyên nhân reset từ MCUSR */
    uart_print_reset_reason(mcusr_mirror);

    /* Nếu người dùng GIỮ nút nhấn D12 lúc bật nguồn: kích hoạt chế độ tự kiểm dấu (§13.4) */
    if ((BUTTON_PINREG & (1 << BUTTON_PIN)) == 0) {
        fsm_enable_diagnostics();
    }

    /* Khởi tạo hệ thống Timer0 và Timer2 */
    timer_init();

    /* BOOT-07: Cho phép ngắt toàn cục khi các khối phần cứng cơ sở đã sẵn sàng */
    sei();

    /* BOOT-06: Khởi tạo giao tiếp I2C phần cứng TWI có 9 xung giải phóng bus (§8.6, IMU-12) */
    i2c_init();

    /* Khởi tạo cảm biến con quay quán tính MPU6050 (kiểm tra WHO_AM_I và đọc lại 0x1C) */
    char mpu_diag_msg[80];
    if (!mpu6050_init()) {
        snprintf(mpu_diag_msg, sizeof(mpu_diag_msg), "[ERR] MPU6050: %s", mpu6050_get_init_diag());
        uart_send_line(mpu_diag_msg);
        fsm_notify_sensor_error();
    } else {
        snprintf(mpu_diag_msg, sizeof(mpu_diag_msg), "[INFO] MPU6050: %s", mpu6050_get_init_diag());
        uart_send_line(mpu_diag_msg);
    }

    uint32_t last_telemetry_ms = 0;

    /* Vòng lặp chính kết hợp Tầng 2 và Tầng 3 */
    while (1) {
        /* Tầng 2: Vòng lặp điều khiển thời gian thực chu kỳ xác định 4 ms */
        if (timer_check_control_flag()) {
            fsm_update_control_4ms();
        }

        /* Tầng 3: Tác vụ nền phi chặn (nút bấm, còi, kiểm tra trạng thái) */
        fsm_update_background();

        /* Tầng 3: Phát dòng chẩn đoán ngắn gọn qua UART0 mỗi 100 ms đọc được bằng mắt (§9.3, TEST-01) */
        uint32_t now = timer_get_ms();
        if (now - last_telemetry_ms >= 100) {
            last_telemetry_ms = now;
            uart_send_diag_telemetry(fsm_get_state(),
                                     fsm_get_pitch(),
                                     motor_get_throttle_l(),
                                     motor_get_throttle_r(),
                                     timer_get_deadline_miss(),
                                     uart_get_dropped_lines());
        }

        /* LƯU Ý BẢO MẬT THỜI GIAN THỰC (NFR-02):
         * - Không sử dụng hàm trễ gây chặn CPU.
         * - Không truyền chuỗi LED WS2812 khi hệ thống đang vận hành cân bằng.
         */
    }

    return 0;
}
