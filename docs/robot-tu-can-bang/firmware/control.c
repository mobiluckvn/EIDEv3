#include "control.h"
#include "config.h"
#include "motor.h"
#include <math.h>

#define RAD_TO_DEG_FACTOR    57.29578f /* Fact f-nguoi-49730291 (anh cho, chưa có tài liệu) */

void control_init(control_system_t *cs) {
    cs->state = CONTROL_STATE_INIT;
    cs->current_pitch = 0.0f;
    cs->motor_speed = 0;
    cs->motor_enabled = false;
    cs->fall_triggered = false;
    filter_init(&cs->filter, 0.9996f, CONTROL_LOOP_DT);
    pid_init();
}

void control_reset(control_system_t *cs) {
    cs->motor_speed = 0;
    cs->motor_enabled = false;
    pid_reset();
}

void control_set_state(control_system_t *cs, control_state_t new_state) {
    cs->state = new_state;
    if (new_state == CONTROL_STATE_READY || new_state == CONTROL_STATE_STOPPED || new_state == CONTROL_STATE_FALLEN) {
        control_reset(cs);
    }
}

int16_t control_update_4ms(control_system_t *cs, float accel_x_g, float accel_z_g, float gyro_y_dps) {
    /* Tính góc nghiêng pitch từ gia tốc kế theo ánh xạ §8.3 (X đứng, Z trước-sau) và s_net = +1 (§13.4 Mục 4) */
    float forward_accel_z = (1.0f) * accel_z_g; /* s_net = +1 (nghiêng tới -> pitch > 0) */
    float accel_pitch = (atan2f(forward_accel_z, accel_x_g) * RAD_TO_DEG_FACTOR) - (0.713f);

    /* Cập nhật bộ lọc bù kết hợp con quay quán tính nhân s_net = +1 */
    float gyro_pitch_rate = (1.0f) * gyro_y_dps;
    float pitch = filter_update(&cs->filter, accel_pitch, gyro_pitch_rate);
    cs->current_pitch = pitch;

    switch (cs->state) {
        case CONTROL_STATE_READY:
            /* Tự động kích hoạt khi qua vị trí cân bằng: cửa sổ ±0,5° theo bản tham chiếu */
            if (pitch > -0.5f && pitch < 0.5f) {
                cs->state = CONTROL_STATE_BALANCING;
                control_reset(cs);
                cs->motor_enabled = true;
            }
            cs->motor_speed = 0;
            break;

        case CONTROL_STATE_BALANCING:
            /* Phát hiện ngã đổ vượt 30 độ theo bản tham chiếu */
            if (pitch > 30.0f || pitch < -30.0f) {
                cs->state = CONTROL_STATE_FALLEN;
                cs->fall_triggered = true;
                control_reset(cs);
            } else {
                /* Tính toán PID cân bằng và chuyển sang throttle phi tuyến qua hàm dùng chung */
                float out = pid_compute(pitch, 0.0f, true);
                cs->motor_speed = motor_calc_throttle_from_pid(out);
            }
            break;

        case CONTROL_STATE_FALLEN:
        case CONTROL_STATE_STOPPED:
        default:
            control_reset(cs);
            break;
    }

    return cs->motor_speed;
}
