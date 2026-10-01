#ifndef PID_H_
#define PID_H_

#include <stdbool.h>

/* Khởi tạo bộ điều khiển PID theo bản tham chiếu */
void pid_init(void);

/* Cài đặt hệ số Kp, Ki, Kd */
void pid_set_tunings(float kp, float ki, float kd);

/* Tính toán ngõ ra PID theo góc nghiêng, điểm đặt và trạng thái vận hành */
float pid_compute(float angle, float pid_setpoint, bool is_running);

/* Reset bộ nhớ tích phân và điểm cân bằng tự học */
void pid_reset(void);

/* Lấy điểm cân bằng tự học hiện tại */
float pid_get_self_balance_setpoint(void);

#endif /* PID_H_ */
