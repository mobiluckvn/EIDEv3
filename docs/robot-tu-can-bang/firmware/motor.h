#ifndef MOTOR_H_
#define MOTOR_H_

#include <stdint.h>
#include <stdbool.h>

/* Khởi tạo chân I/O điều khiển driver động cơ bước A4988 */
void motor_init(void);

/* Cài đặt tốc độ bước cho hai bánh xe qua đại lượng throttle theo §7.6 (|thr| >= 1, 0 = đứng im) */
void motor_set_throttle(int16_t throttle_left, int16_t throttle_right);

/* Chuyển đổi tốc độ/tần số xung mong muốn (xung/giây) sang throttle theo §7.6 */
int16_t motor_speed_to_throttle(float speed_hz);

/* Cài đặt tốc độ bước cho hai bánh xe (hàm tương thích gọi throttle) */
void motor_set_speed(int16_t speed_left, int16_t speed_right);

/* Dừng hoàn toàn việc phát xung bước (Chân EN nối cứng GND nên dừng bằng cách tắt xung STEP) */
void motor_stop(void);

/* Bật cho phép phát xung bước */
void motor_enable(void);

/* Hàm thực thi trong ISR ngắt Timer2 50 kHz (Tầng 1) */
void motor_isr_step(void);

/* Ánh xạ phi tuyến từ đầu ra PID sang giá trị throttle (app_balance.c:141-149) */
int16_t motor_calc_throttle_from_pid(float out);

/* Đọc lệnh throttle hiện tại của hai bánh xe */
int16_t motor_get_throttle_l(void);
int16_t motor_get_throttle_r(void);

#endif /* MOTOR_H_ */
