#include "pid.h"

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float integral_max, float out_max) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->integral_max = integral_max;
    pid->out_max = out_max;
}

float pid_calculate(pid_controller_t *pid, float setpoint, float current_val, float dt) {
    float error = setpoint - current_val;

    /* Thành phần vi phân */
    float derivative = 0.0f;
    if (dt > 0.0f) {
        derivative = (error - pid->prev_error) / dt;
    }
    pid->prev_error = error;

    /* Thành phần tích phân có kẹp giới hạn chống windup */
    pid->integral += error * dt;
    if (pid->integral > pid->integral_max) {
        pid->integral = pid->integral_max;
    } else if (pid->integral < -pid->integral_max) {
        pid->integral = -pid->integral_max;
    }

    /* Tính đầu ra */
    float output = (pid->kp * error) + (pid->ki * pid->integral) + (pid->kd * derivative);

    /* Kẹp giới hạn đầu ra bão hòa */
    if (output > pid->out_max) {
        output = pid->out_max;
    } else if (output < -pid->out_max) {
        output = -pid->out_max;
    }

    return output;
}

void pid_reset(pid_controller_t *pid) {
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
}
