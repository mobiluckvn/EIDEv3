#ifndef MOTOR_H_
#define MOTOR_H_

#include <stdint.h>
#include <stdbool.h>

/* Khởi tạo chân I/O điều khiển driver động cơ bước A4988 */
void motor_init(void);

/* Cài đặt tốc độ bước cho hai bánh xe (xung/giây) */
void motor_set_speed(int16_t speed_left, int16_t speed_right);

/* Dừng hoàn toàn việc phát xung bước (Chân EN nối cứng GND nên dừng bằng cách tắt xung STEP) */
void motor_stop(void);

/* Bật cho phép phát xung bước */
void motor_enable(void);

/* Hàm thực thi trong ISR ngắt Timer2 50 kHz (Tầng 1) */
void motor_isr_step(void);

#endif /* MOTOR_H_ */
