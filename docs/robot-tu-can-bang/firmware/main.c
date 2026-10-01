#include "config.h"
#include "timer.h"
#include "i2c.h"
#include "mpu6050.h"
#include "motor.h"
#include "fsm.h"
#include <avr/interrupt.h>
#include <avr/wdt.h>

int main(void) {
    /* Xoá cờ reset trong MCUSR và tắt Watchdog ngay lệnh đầu tiên (§13.2, Phụ lục A.3) */
    MCUSR = 0;
    wdt_disable();

    /* Khởi tạo chân I/O điều khiển động cơ bước A4988 */
    motor_init();

    /* Khởi tạo máy trạng thái và chân nút nhấn/còi */
    fsm_init();

    /* Nếu người dùng GIỮ nút nhấn D12 lúc bật nguồn: kích hoạt chế độ tự kiểm dấu (§13.4) */
    if ((BUTTON_PINREG & (1 << BUTTON_PIN)) == 0) {
        fsm_enable_diagnostics();
    }

    /* Khởi tạo hệ thống Timer0 và Timer2 */
    timer_init();

    /* Cho phép ngắt toàn cục */
    sei();

    /* Khởi tạo giao tiếp I2C phần cứng TWI */
    i2c_init();

    /* Khởi tạo cảm biến con quay quán tính MPU6050 */
    if (!mpu6050_init()) {
        fsm_notify_sensor_error();
    }

    /* Vòng lặp chính kết hợp Tầng 2 và Tầng 3 */
    while (1) {
        /* Tầng 2: Vòng lặp điều khiển thời gian thực chu kỳ xác định */
        if (timer_check_control_flag()) {
            fsm_update_control_4ms();
        }

        /* Tầng 3: Tác vụ nền phi chặn (nút bấm, còi, kiểm tra trạng thái) */
        fsm_update_background();

        /* LƯU Ý BẢO MẬT THỜI GIAN THỰC (NFR-02):
         * - Không sử dụng hàm trễ gây chặn CPU.
         * - Không truyền chuỗi LED WS2812 khi hệ thống đang vận hành cân bằng.
         */
    }

    return 0;
}
