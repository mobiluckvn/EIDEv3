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
static bool s_sensor_error = false;
static bool s_sensor_error_muted = false;
static uint32_t s_last_calib_ms = 0;

/* Quản lý chế độ tự kiểm dấu (§13.4) */
static bool s_diag_mode = false;
static uint32_t s_diag_motor_start = 0;
static volatile float s_last_measured_pitch = 0.0f;

static void buzzer_on_ms(uint16_t duration_ms) {
    BUZZER_PORT |= (1 << BUZZER_PIN);
    s_buzzer_off_time = timer_get_ms() + duration_ms;
}

void fsm_enable_diagnostics(void) {
    s_diag_mode = true;
}

void fsm_notify_sensor_error(void) {
    s_sensor_error = true;
    s_state = STATE_STOPPED;
    motor_stop();
}

bool fsm_has_sensor_error(void) {
    return s_sensor_error;
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

    /* Khởi tạo PID theo thang tốc độ throttle mới (§7.6, Bảng 18: max 25.000 xung/s):
     * Kp = 180.0, Ki = 10.0, Kd = 6.0, MaxI = 1250.0, MaxOut = 25000.0 */
    pid_init(&s_pid, 180.0f, 10.0f, 6.0f, 1250.0f, 25000.0f);

    s_state = STATE_INIT;
    s_sensor_error = false;
    s_last_calib_ms = 0;
    s_last_measured_pitch = 0.0f;
    mpu6050_calib_reset();
}

robot_state_t fsm_get_state(void) {
    return s_state;
}

float fsm_get_pitch(void) {
    return s_last_measured_pitch;
}

void fsm_update_background(void) {
    uint32_t now = timer_get_ms();

    /* Quản lý còi: nếu có lỗi cảm biến, phát mã bíp cảnh báo riêng biệt (nếu chưa bấm nút tắt còi) */
    if (s_sensor_error) {
        if (s_sensor_error_muted) {
            BUZZER_PORT &= ~(1 << BUZZER_PIN); /* Đã bấm tắt còi: im tiếng hoàn toàn */
        } else {
            uint16_t phase = (uint16_t)(now % 1000);
            if ((phase < 80) || (phase >= 160 && phase < 240) || (phase >= 320 && phase < 400)) {
                BUZZER_PORT |= (1 << BUZZER_PIN);
            } else {
                BUZZER_PORT &= ~(1 << BUZZER_PIN);
            }
        }
    } else if (s_state == STATE_DIAG_ANGLE) {
        /* Chế độ kiểm tra dấu góc (§13.4 Mục 4): còi kêu theo dấu góc */
        if (s_buzzer_off_time > 0 && now < s_buzzer_off_time) {
            BUZZER_PORT |= (1 << BUZZER_PIN);
        } else {
            s_buzzer_off_time = 0;
            if (fabsf(s_last_measured_pitch) < 2.0f) {
                /* Đứng thẳng: Còi IM LẶNG */
                BUZZER_PORT &= ~(1 << BUZZER_PIN);
            } else if (s_last_measured_pitch >= 3.0f) {
                /* Nghiêng về TRƯỚC (dấu dương): Còi bíp CHẬM (chu kỳ 600 ms) */
                uint16_t ph = (uint16_t)(now % 600);
                if (ph < 80) {
                    BUZZER_PORT |= (1 << BUZZER_PIN);
                } else {
                    BUZZER_PORT &= ~(1 << BUZZER_PIN);
                }
            } else if (s_last_measured_pitch <= -3.0f) {
                /* Nghiêng ra SAU (dấu âm): Còi bíp NHANH (chu kỳ 200 ms) */
                uint16_t ph = (uint16_t)(now % 200);
                if (ph < 60) {
                    BUZZER_PORT |= (1 << BUZZER_PIN);
                } else {
                    BUZZER_PORT &= ~(1 << BUZZER_PIN);
                }
            } else {
                BUZZER_PORT &= ~(1 << BUZZER_PIN);
            }
        }
    } else {
        /* Tự động tắt còi phi chặn khi hết thời gian */
        if (s_buzzer_off_time > 0 && now >= s_buzzer_off_time) {
            BUZZER_PORT &= ~(1 << BUZZER_PIN);
            s_buzzer_off_time = 0;
        }
    }

    /* Đọc nút nhấn D12 chống rung phi chặn */
    bool current_btn = (BUTTON_PINREG & (1 << BUTTON_PIN)) ? true : false;
    if (s_prev_btn_state && !current_btn) {
        /* Bắt sườn xuống nút bấm */
        if (now - s_last_btn_time > 200) {
            s_last_btn_time = now;
            /* Xử lý bấm nút trong chế độ chẩn đoán */
            if (s_state == STATE_DIAG_ANGLE) {
                /* Bấm nút ở Bài 1 -> Phát tiếng còi dài 600 ms phân cách và chuyển sang Bài 2 (§13.4 Mục 6) */
                s_state = STATE_DIAG_MOTOR;
                buzzer_on_ms(600); /* Tiếng còi dài 600 ms để phân biệt đang ở bài nào */
                motor_enable();
                motor_set_throttle(100, 100); /* Chạy tới chậm trong 3 giây (v ≈ 0,031 m/s) */
                s_diag_motor_start = now;
            } else if (s_sensor_error) {
                /* Bấm nút D12 khi đang báo lỗi: TẮT CÒI NGAY LẬP TỨC nhưng vẫn giữ cờ lỗi và log chữ */
                s_sensor_error_muted = true;
                BUZZER_PORT &= ~(1 << BUZZER_PIN);
            } else if (s_state == STATE_BALANCING || s_state == STATE_READY) {
                /* Bấm nút khi đang chạy hoặc sẵn sàng -> Dừng hẳn (FR-03) */
                s_state = STATE_STOPPED;
                motor_stop();
                pid_reset(&s_pid);
                buzzer_on_ms(100);
            } else if (s_state == STATE_STOPPED || s_state == STATE_FALLEN) {
                /* Bấm nút khi đang dừng/ngã/hiệu chuẩn xong -> Đưa về sẵn sàng (FR-03) */
                s_state = STATE_READY;
                motor_stop();
                pid_reset(&s_pid);
                buzzer_on_ms(50);
            }
        }
    }
    s_prev_btn_state = current_btn;

    /* Xử lý thời gian kết thúc Bài 2 trong chế độ chẩn đoán (§13.4 Mục 6) */
    if (s_state == STATE_DIAG_MOTOR) {
        if (now - s_diag_motor_start >= 3000) {
            /* Hết 3 giây chạy tới: dừng động cơ và chuyển về STOPPED */
            motor_stop();
            s_state = STATE_STOPPED;
            s_diag_mode = false;
            buzzer_on_ms(200); /* Bíp báo kết thúc toàn bộ kiểm tra */
        }
    }

    /* Xử lý khởi tạo và hiệu chuẩn ở trạng thái INIT / CALIBRATING phi chặn (§8.8, §12.7) */
    if (s_state == STATE_INIT) {
        buzzer_on_ms(50); /* Báo hiệu đang khởi động (FR-01) */
        s_state = STATE_CALIBRATING;
        mpu6050_calib_reset();
        s_last_calib_ms = now;
    } else if (s_state == STATE_CALIBRATING) {
        /* Giãn cách 3 ms mỗi mẫu: 500 mẫu = 1500 ms = 1,5 s theo §8.8 (phi chặn) */
        if (now - s_last_calib_ms >= 3) {
            s_last_calib_ms = now;
            bool done = false;
            if (!mpu6050_calib_step(&done)) {
                /* Cảm biến lỗi: chuyển sang STOPPED và kích hoạt mã bíp cảnh báo lỗi */
                fsm_notify_sensor_error();
            } else if (done) {
                motor_stop();
                pid_reset(&s_pid);
                if (s_diag_mode) {
                    /* Vào chế độ chẩn đoán Bài 1 kiểm dấu góc (§13.4 Mục 4) */
                    s_state = STATE_DIAG_ANGLE;
                    buzzer_on_ms(200);
                } else {
                    /* Tự hiệu chuẩn thành công -> chuyển sang STOPPED CHỜ BẤM NÚT */
                    s_state = STATE_STOPPED;
                    buzzer_on_ms(200);
                }
            }
        }
    }
}

void fsm_update_control_4ms(void) {
    mpu6050_data_t imu;
    if (!mpu6050_read_scaled(&imu)) {
        return;
    }

    /* Tính góc nghiêng pitch từ gia tốc kế theo ánh xạ §8.3 (X đứng, Z trước-sau) và tham số §11 */
    float forward_accel_z = CALIB_AXIS_DIR_Z * imu.accel_z_g; /* s = -1 cho bo hạng L (§11.5) */
    float accel_pitch = (atan2f(forward_accel_z, imu.accel_x_g) * RAD_TO_DEG_FACTOR) - CALIB_PITCH_OFFSET_DEG;

    /* Cập nhật bộ lọc bù với tốc độ con quay trục Y nhân hệ số s = -1 (§11.5) */
    float gyro_pitch_rate = CALIB_AXIS_DIR_Z * imu.gyro_y_dps;
    float pitch = filter_update(&s_filter, accel_pitch, gyro_pitch_rate);
    s_last_measured_pitch = pitch;

    switch (s_state) {
        case STATE_DIAG_ANGLE:
            motor_stop();
            break;

        case STATE_DIAG_MOTOR:
            /* Giữ lệnh chạy tới trong Bài 2 */
            break;

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
                /* Tính toán PID cân bằng với dấu đầu ra u phù hợp (§11.5) */
                float speed_out = -pid_calculate(&s_pid, 0.0f, pitch, CONTROL_LOOP_DT);
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
