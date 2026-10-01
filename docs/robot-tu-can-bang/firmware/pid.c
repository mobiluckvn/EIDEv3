#include "pid.h"

/* Các hệ số PID kiểm chứng thực nghiệm từ bản tham chiếu đã chạy tốt trên bo */
static float pid_p_gain = 12.0f;
static float pid_i_gain = 0.4f;
static float pid_d_gain = 10.0f;

static float pid_i_mem = 0.0f;
static float pid_last_d_error = 0.0f;
static float self_balance_setpoint = 0.0f;
static float pid_output = 0.0f;

void pid_init(void) {
    pid_i_mem = 0.0f;
    pid_last_d_error = 0.0f;
    self_balance_setpoint = 0.0f;
    pid_output = 0.0f;
}

void pid_set_tunings(float kp, float ki, float kd) {
    pid_p_gain = kp;
    pid_i_gain = ki;
    pid_d_gain = kd;
}

float pid_compute(float angle, float pid_setpoint, bool is_running) {
    float pid_error_temp = angle - self_balance_setpoint - pid_setpoint;

    /* Khâu hãm (brake damping): khi ngõ ra lớn thì hãm lại để chống vọt lố */
    if (pid_output > 10.0f || pid_output < -10.0f) {
        pid_error_temp += pid_output * 0.015f;
    }

    /* Khâu tích phân có giới hạn kẹp chống bão hoà (anti-windup) */
    pid_i_mem += pid_i_gain * pid_error_temp;
    if (pid_i_mem > 400.0f) pid_i_mem = 400.0f;
    if (pid_i_mem < -400.0f) pid_i_mem = -400.0f;

    /* Khâu đạo hàm tính theo sai số (error-derivative) */
    pid_output = pid_p_gain * pid_error_temp 
               + pid_i_mem 
               + pid_d_gain * (pid_error_temp - pid_last_d_error);

    /* Giới hạn ngõ ra */
    if (pid_output > 400.0f) pid_output = 400.0f;
    if (pid_output < -400.0f) pid_output = -400.0f;

    pid_last_d_error = pid_error_temp;

    /* Vùng chết (deadband) chống rung lắc khi đứng yên */
    if (pid_output < 5.0f && pid_output > -5.0f) {
        pid_output = 0.0f;
    }

    /* Tự học điểm cân bằng tĩnh theo V1 (V1 dòng 367-368: self_balance_pid_setpoint +=/- 0.002) */
    if (pid_setpoint == 0.0f) {
        if (pid_output < 0.0f) self_balance_setpoint += 0.002f;
        if (pid_output > 0.0f) self_balance_setpoint -= 0.002f;
    }

    /* Điều kiện dừng / ngã đổ: triệt tiêu ngõ ra và bộ nhớ tích phân */
    if (!is_running || angle > 30.0f || angle < -30.0f) {
        pid_output = 0.0f;
        pid_i_mem = 0.0f;
        self_balance_setpoint = 0.0f;
    }

    return pid_output;
}

void pid_reset(void) {
    pid_output = 0.0f;
    pid_i_mem = 0.0f;
    self_balance_setpoint = 0.0f;
    pid_last_d_error = 0.0f;
}

float pid_get_self_balance_setpoint(void) {
    return self_balance_setpoint;
}
