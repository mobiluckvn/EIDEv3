#include "control.h"
#include <math.h>

#define RAD_TO_DEG_FACTOR    57.29578f /* Fact f-nguoi-49730291 (anh cho, chưa có tài liệu) */
#define ANGLE_FALL_LIMIT_DEG 45.0f     /* Fact f-nguoi-39884580 (anh cho, chưa có tài liệu) */
#define ANGLE_ACTIVE_DEG     2.0f      /* FR-04 (anh cho, chưa có tài liệu) */
#define CONTROL_PERIOD_MS    4.0f      /* Fact f-nguoi-66277026 (anh cho, chưa có tài liệu) */
#define TIMER_BASE_HZ        1000.0f   /* Fact f-nguoi-2633608 (anh cho, chưa có tài liệu) */
#define CONTROL_LOOP_DT      (CONTROL_PERIOD_MS / TIMER_BASE_HZ)

void control_init(control_system_t *cs) {
    cs->state = CONTROL_STATE_INIT;
    cs->current_pitch = 0.0f;
    cs->motor_speed = 0;
    cs->motor_enabled = false;
    cs->fall_triggered = false;
    filter_init(&cs->filter, 0.98f, CONTROL_LOOP_DT);
    pid_init(&cs->pid, 15.0f, 0.8f, 0.5f, 100.0f, 2000.0f);
}

void control_reset(control_system_t *cs) {
    cs->motor_speed = 0;
    cs->motor_enabled = false;
    pid_reset(&cs->pid);
}

void control_set_state(control_system_t *cs, control_state_t new_state) {
    cs->state = new_state;
    if (new_state == CONTROL_STATE_READY || new_state == CONTROL_STATE_STOPPED || new_state == CONTROL_STATE_FALLEN) {
        control_reset(cs);
    }
}

int16_t control_update_4ms(control_system_t *cs, float accel_x_g, float accel_z_g, float gyro_y_dps) {
    /* Tính góc nghiêng pitch từ gia tốc kế */
    float accel_pitch = atan2f(-accel_x_g, accel_z_g) * RAD_TO_DEG_FACTOR;

    /* Cập nhật bộ lọc bù kết hợp con quay quán tính */
    float pitch = filter_update(&cs->filter, accel_pitch, gyro_y_dps);
    cs->current_pitch = pitch;

    switch (cs->state) {
        case CONTROL_STATE_READY:
            /* Tự động kích hoạt khi qua vị trí cân bằng (FR-04) */
            if (fabsf(pitch) < ANGLE_ACTIVE_DEG) {
                cs->state = CONTROL_STATE_BALANCING;
                control_reset(cs);
                cs->motor_enabled = true;
            }
            cs->motor_speed = 0;
            break;

        case CONTROL_STATE_BALANCING:
            /* Phát hiện ngã đổ vượt 45 độ (FR-05) */
            if (fabsf(pitch) > ANGLE_FALL_LIMIT_DEG) {
                cs->state = CONTROL_STATE_FALLEN;
                cs->fall_triggered = true;
                control_reset(cs);
            } else {
                /* Tính toán PID cân bằng góc nghiêng */
                float speed_out = pid_calculate(&cs->pid, 0.0f, pitch, CONTROL_LOOP_DT);
                cs->motor_speed = (int16_t)speed_out;
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
