#include "logic_pid.h"

static float pid_p_gain = 12.0f;
static float pid_i_gain = 0.4f;
static float pid_d_gain = 10.0f;

static float pid_i_mem = 0.0f;
static float pid_last_d_error = 0.0f;
static float self_balance_setpoint = 0.0f;
static float pid_output = 0.0f;

void pid_set_tunings(float kp, float ki, float kd) {
    pid_p_gain = kp;
    pid_i_gain = ki;
    pid_d_gain = kd;
}

float pid_compute(float angle, float pid_setpoint, bool is_running) {
    float pid_error_temp = angle - self_balance_setpoint - pid_setpoint;
    
    if (pid_output > 10.0f || pid_output < -10.0f) {
        pid_error_temp += pid_output * 0.015f;          // hàm phanh
    }

    pid_i_mem += pid_i_gain * pid_error_temp;
    if (pid_i_mem > 400.0f) pid_i_mem = 400.0f;            // kẹp tích phân
    if (pid_i_mem < -400.0f) pid_i_mem = -400.0f;

    // LƯU Ý: Đạo hàm ở đây lấy theo SAI SỐ — và đó là có chủ ý.
    // Phải xem lại điều này ngay khi thêm lệnh đi tới / lùi / quay: 
    // lúc ấy điểm đặt nhảy bậc thật, và derivative kick trở thành lỗi thật.
    pid_output = pid_p_gain * pid_error_temp 
               + pid_i_mem 
               + pid_d_gain * (pid_error_temp - pid_last_d_error);
               
    if (pid_output > 400.0f) pid_output = 400.0f;
    if (pid_output < -400.0f) pid_output = -400.0f;

    pid_last_d_error = pid_error_temp;

    if (pid_output < 5.0f && pid_output > -5.0f) {
        pid_output = 0.0f;   // vùng chết
    }

    if (pid_setpoint == 0.0f) {
        if (pid_output < 0.0f) self_balance_setpoint += 0.0015f;
        if (pid_output > 0.0f) self_balance_setpoint -= 0.0015f;
    }

    // Điều kiện dừng phải đặt ở cuối để pid_last_d_error vẫn được cập nhật
    // theo đúng chu kỳ, tránh derivative kick khi hệ thống chạy lại.
    if (!is_running || angle > 30.0f || angle < -30.0f) {
        pid_output = 0.0f;
        pid_i_mem = 0.0f;
        self_balance_setpoint = 0.0f;
    }

    return pid_output;
}
