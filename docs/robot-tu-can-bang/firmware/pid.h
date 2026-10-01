#ifndef PID_H_
#define PID_H_

typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float prev_error;
    float integral_max;
    float out_max;
} pid_controller_t;

/* Khởi tạo thông số bộ điều khiển PID */
void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float integral_max, float out_max);

/* Cập nhật tính toán PID với sai số và khoảng thời gian dt */
float pid_calculate(pid_controller_t *pid, float setpoint, float current_val, float dt);

/* Xoá bộ tích phân khi dừng động cơ hoặc chuyển trạng thái */
void pid_reset(pid_controller_t *pid);

#endif /* PID_H_ */
