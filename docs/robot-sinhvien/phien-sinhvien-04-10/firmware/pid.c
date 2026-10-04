#include "config.h"
#include <math.h>

static float g_target_angle = 0.0f;
static float g_integral = 0.0f;
static float g_last_error = 0.0f;
static float g_last_output = 0.0f;

void pid_init(void) {
    g_target_angle = 0.0f;
    g_integral = 0.0f;
    g_last_error = 0.0f;
    g_last_output = 0.0f;
}

void pid_reset(void) {
    g_integral = 0.0f;
    g_last_error = 0.0f;
    g_last_output = 0.0f;
}

float pid_calculate(float current_angle) {
    /* Muc E.1 (anh cho, chua co tai lieu): Triet tieu khi nga */
    if (fabsf(current_angle) > ANGLE_LIMIT_FALLEN) {
        g_integral = 0.0f;
        g_last_output = 0.0f;
        return 0.0f;
    }

    float error = current_angle - g_target_angle;

    /* Muc E.1: Phan hoi ngo ra vao sai so khi |ngo ra| > 10 */
    if (fabsf(g_last_output) > PID_FEEDBACK_THRESHOLD) {
        error += g_last_output * PID_FEEDBACK_GAIN;
    }

    /* Khau ti le (P) */
    float p_term = PID_KP * error;

    /* Khau tich phan (I) va kep tich phan */
    g_integral += PID_KI * error;
    if (g_integral > PID_INTEGRAL_LIMIT) {
        g_integral = PID_INTEGRAL_LIMIT;
    } else if (g_integral < -PID_INTEGRAL_LIMIT) {
        g_integral = -PID_INTEGRAL_LIMIT;
    }

    /* Khau vi phan (D) */
    float d_term = PID_KD * (error - g_last_error);
    g_last_error = error;

    /* Tong ngo ra */
    float output = p_term + g_integral + d_term;

    /* Kep ngo ra trong khoang [-400, 400] */
    if (output > PID_OUTPUT_LIMIT) {
        output = PID_OUTPUT_LIMIT;
    } else if (output < -PID_OUTPUT_LIMIT) {
        output = -PID_OUTPUT_LIMIT;
    }

    /* Muc E.1: Tu hoc diem can bang */
    if (output < 0.0f) {
        g_target_angle += PID_LEARN_STEP;
    } else if (output > 0.0f) {
        g_target_angle -= PID_LEARN_STEP;
    }

    g_last_output = output;
    return output;
}

float pid_get_target_angle(void) {
    return g_target_angle;
}
