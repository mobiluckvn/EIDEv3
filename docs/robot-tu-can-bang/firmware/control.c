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
    /* Khởi tạo PID theo thang tốc độ throttle max 25.000 xung/s (§7.6, Bảng 18) */
    pid_init(&cs->pid, 180.0f, 10.0f, 6.0f, 1250.0f, 25000.0f);
}

static int16_t speed_to_throttle_internal(float speed_hz) {
    float abs_spd = fabsf(speed_hz);
    if (abs_spd < 10.0f) {
        return 0; /* Xử lý tường minh: đứng im (§7.6) */
    }
    float thr_val = (50000.0f / abs_spd) - 1.0f;
    int16_t thr = (int16_t)(thr_val + 0.5f);
    if (thr < 1) {
        thr = 1;
    } else if (thr > 2000) {
        thr = 2000;
    }
    return (speed_hz >= 0.0f) ? thr : -thr;
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
    /* Tính góc nghiêng pitch từ gia tốc kế theo ánh xạ §8.3 (X đứng, Z trước-sau) và tham số §11 */
    float forward_accel_z = (-1.0f) * accel_z_g; /* s = -1 cho bo hạng L (§11.5) */
    float accel_pitch = (atan2f(forward_accel_z, accel_x_g) * RAD_TO_DEG_FACTOR) - (-0.713f);

    /* Cập nhật bộ lọc bù kết hợp con quay quán tính nhân s = -1 (§11.5) */
    float gyro_pitch_rate = (-1.0f) * gyro_y_dps;
    float pitch = filter_update(&cs->filter, accel_pitch, gyro_pitch_rate);
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
                /* Tính toán PID cân bằng góc nghiêng và đổi sang throttle (§7.6, §11.5) */
                float speed_out = -pid_calculate(&cs->pid, 0.0f, pitch, CONTROL_LOOP_DT);
                cs->motor_speed = speed_to_throttle_internal(speed_out);
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
