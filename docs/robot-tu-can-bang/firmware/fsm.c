#include "fsm.h"
#include "config.h"
#include "timer.h"
#include "mpu6050.h"
#include "filter.h"
#include "pid.h"
#include "motor.h"
#include <math.h>

#define RAD_TO_DEG_FACTOR 57.29578f /* (anh cho, chưa có tài liệu) */

static robot_state_t s_state = STATE_INIT;
static comp_filter_t s_filter;
static pid_controller_t s_pid;

/* Quản lý nút nhấn phi chặn */
static bool s_prev_btn_state = true;
static uint32_t s_last_btn_time = 0;

/* Quản lý còi phi chặn */
static uint32_t s_buzzer_off_time = 0;

static void buzzer_on_ms(uint16_t duration_ms) {
    BUZZER_PORT |= (1 << BUZZER_PIN);
    s_buzzer_off_time = timer_get_ms() + duration_ms;
}

void fsm_init(void) {
    /* Cấu hình chân Buzzer D10 là OUTPUT, ban đầu tắt */
    BUZZER_DDR |= (1 << BUZZER_PIN);
    BUZZER_PORT &= ~(1 << BUZZER_PIN);

    /* Cấu hình chân Button D12 là INPUT có điện trở kéo lên PULL-UP */
    BUTTON_DDR &= ~(1 << BUTTON_PIN);
    BUTTON_PORT |= (1 << BUTTON_PIN);

    /* Khởi tạo bộ lọc bù: alpha = 0.98, dt = 4 ms */
    filter_init(&s_filter, 0.98f, CONTROL_LOOP_DT);

    /* Khởi tạo PID: Kp = 15.0, Ki = 0.8, Kd = 0.5, MaxI = 100.0, MaxOut = 2000.0 */
    pid_init(&s_pid, 15.0f, 0.8f, 0.5f, 100.0f, 2000.0f);

    s_state = STATE_INIT;
}

robot_state_t fsm_get_state(void) {
    return s_state;
}

void fsm_update_background(void) {
    uint32_t now = timer_get_ms();

    /* Tự động tắt còi phi chặn khi hết thời gian */
    if (s_buzzer_off_time > 0 && now >= s_buzzer_off_time) {
        BUZZER_PORT &= ~(1 << BUZZER_PIN);
        s_buzzer_off_time = 0;
    }

    /* Đọc nút nhấn D12 chống rung phi chặn */
    bool current_btn = (BUTTON_PINREG & (1 << BUTTON_PIN)) ? true : false;
    if (s_prev_btn_state && !current_btn) {
        /* Bắt sườn xuống nút bấm */
        if (now - s_last_btn_time > 200) {
            s_last_btn_time = now;
            /* Xử lý bấm nút (FR-03) */
            if (s_state == STATE_BALANCING || s_state == STATE_READY) {
                /* Bấm nút khi đang chạy hoặc sẵn sàng -> Dừng hẳn (FR-03) */
                s_state = STATE_STOPPED;
                motor_stop();
                pid_reset(&s_pid);
                buzzer_on_ms(100);
            } else if (s_state == STATE_STOPPED || s_state == STATE_FALLEN) {
                /* Bấm nút khi đang dừng/ngã -> Đưa về sẵn sàng (FR-03) */
                s_state = STATE_READY;
                motor_stop();
                pid_reset(&s_pid);
                buzzer_on_ms(50);
            }
        }
    }
    s_prev_btn_state = current_btn;

    /* Xử lý khởi tạo và hiệu chuẩn ở trạng thái INIT */
    if (s_state == STATE_INIT) {
        buzzer_on_ms(50); /* Báo hiệu đang khởi động (FR-01) */
        s_state = STATE_CALIBRATING;
        if (mpu6050_calibrate_gyro()) {
            /* Tự hiệu chuẩn thành công (FR-02) -> chuyển sang READY */
            s_state = STATE_READY;
            buzzer_on_ms(200); /* Còi kêu báo sẵn sàng (FR-01) */
        } else {
            /* Cảm biến lỗi */
            s_state = STATE_STOPPED;
        }
    }
}

void fsm_update_control_4ms(void) {
    mpu6050_data_t imu;
    if (!mpu6050_read_scaled(&imu)) {
        return;
    }

    /* Tính góc nghiêng pitch từ gia tốc kế */
    float accel_pitch = atan2f(-imu.accel_x_g, imu.accel_z_g) * RAD_TO_DEG_FACTOR;

    /* Cập nhật bộ lọc bù với tốc độ con quay trục Y */
    float pitch = filter_update(&s_filter, accel_pitch, imu.gyro_y_dps);

    switch (s_state) {
        case STATE_READY:
            /* Tự động kích hoạt khi đi qua điểm thăng bằng (FR-04) */
            if (fabsf(pitch) < (float)ANGLE_ACTIVE_DEG) {
                s_state = STATE_BALANCING;
                pid_reset(&s_pid);
                motor_enable();
            }
            break;

        case STATE_BALANCING:
            /* Kiểm tra điều kiện ngã xe (FR-05) */
            if (fabsf(pitch) > (float)ANGLE_FALL_LIMIT_DEG) {
                s_state = STATE_FALLEN;
                motor_stop();
                pid_reset(&s_pid);
                buzzer_on_ms(300); /* Còi báo ngã */
            } else {
                /* Tính toán PID cân bằng */
                float speed_out = pid_calculate(&s_pid, 0.0f, pitch, CONTROL_LOOP_DT);
                int16_t motor_spd = (int16_t)speed_out;
                motor_set_speed(motor_spd, motor_spd);
            }
            break;

        case STATE_FALLEN:
        case STATE_STOPPED:
        default:
            motor_stop();
            break;
    }
}
