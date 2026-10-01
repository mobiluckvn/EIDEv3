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
static float s_angle_gyro = 0.0f;

/* Quản lý nút nhấn phi chặn */
static bool s_prev_btn_state = true;
static uint32_t s_last_btn_time = 0;

/* Quản lý còi phi chặn theo bản tham chiếu app_balance.c */
static uint32_t s_buzzer_off_time = 0;
static bool s_sensor_error = false;
static bool s_sensor_error_muted = false;
static uint32_t s_last_calib_ms = 0;
static uint32_t s_last_beep_time = 0;
static uint8_t s_beep_count = 0;
static uint32_t s_beep_interval = 0;
static bool s_is_error_nga = false;

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

    /* Khởi tạo bộ lọc bù theo bản tham chiếu: alpha = 0.9996, dt = 4 ms */
    filter_init(&s_filter, 0.9996f, CONTROL_LOOP_DT);

    /* Khởi tạo PID theo bản tham chiếu (Kp=12.0, Ki=0.4, Kd=10.0) */
    pid_init();

    /* Ban đầu ở trạng thái dừng chờ bấm nút D12 (STATE_CHO_NUT trong bản tham chiếu) */
    s_state = STATE_STOPPED;
    s_sensor_error = false;
    s_last_calib_ms = 0;
    s_last_measured_pitch = 0.0f;
    s_last_beep_time = 0;
    s_beep_count = 0;
    s_is_error_nga = false;
    mpu6050_calib_reset();

    /* Tiếng bíp 100 ms ngay khi bật nguồn (app_balance.c:38) */
    buzzer_on_ms(100);
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
                pid_reset();
                buzzer_on_ms(100);
            } else if (s_state == STATE_CALIBRATING) {
                /* Bấm nút khi đang hiệu chuẩn -> Huỷ và quay lại dừng (app_balance.c:79-83) */
                s_state = STATE_STOPPED;
                buzzer_on_ms(100);
            } else if (s_state == STATE_STOPPED) {
                /* Bấm nút khi đang dừng -> Bắt đầu hiệu chỉnh con quay (STATE_HIEU_CHINH theo bản tham chiếu) */
                s_state = STATE_CALIBRATING;
                mpu6050_calib_reset();
                s_last_calib_ms = now;
                s_last_beep_time = now;
                s_beep_count = 1;
                buzzer_on_ms(100);
            } else if (s_state == STATE_FALLEN) {
                /* Bấm nút khi ngã -> Quay về trạng thái dừng chờ (FR-03, app_balance.c:169-173) */
                s_state = STATE_STOPPED;
                motor_stop();
                pid_reset();
                buzzer_on_ms(100);
                s_is_error_nga = false;
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
        /* Tiếng bíp 100 ms mỗi 500 ms (tối đa 5 tiếng) trong lúc hiệu chỉnh (app_balance.c:85-89) */
        if (now - s_last_beep_time >= 500 && s_beep_count < 5) {
            buzzer_on_ms(100);
            s_last_beep_time = now;
            s_beep_count++;
        }

        /* Giãn cách 3 ms mỗi mẫu: 500 mẫu = 1500 ms = 1,5 s theo §8.8 (phi chặn) */
        if (now - s_last_calib_ms >= 3) {
            s_last_calib_ms = now;
            bool done = false;
            if (!mpu6050_calib_step(&done)) {
                /* Cảm biến lỗi: chuyển sang STOPPED và kích hoạt mã bíp cảnh báo lỗi */
                fsm_notify_sensor_error();
            } else if (done) {
                motor_stop();
                pid_reset();
                if (s_diag_mode) {
                    /* Vào chế độ chẩn đoán Bài 1 kiểm dấu góc (§13.4 Mục 4) */
                    s_state = STATE_DIAG_ANGLE;
                    buzzer_on_ms(200);
                } else {
                    /* Tự hiệu chuẩn thành công -> chuyển sang READY (app_balance.c:93-96: bíp 100 ms) */
                    s_state = STATE_READY;
                    buzzer_on_ms(100);
                    s_last_beep_time = now;
                    s_beep_count = 1;
                }
            }
        }
    } else if (s_state == STATE_READY) {
        /* Tiếng bíp thứ 2 sau 150 ms để báo sẵn sàng (app_balance.c:108-112) */
        if (now - s_last_beep_time >= 150 && s_beep_count < 2) {
            buzzer_on_ms(100);
            s_last_beep_time = now;
            s_beep_count++;
        }
    } else if (s_state == STATE_FALLEN) {
        /* Báo lỗi ngã: 3 tiếng bíp ngắn 50 ms dồn dập rồi nghỉ 600 ms lặp lại (app_balance.c:156-167) */
        if (s_is_error_nga) {
            if (now - s_last_beep_time >= s_beep_interval) {
                buzzer_on_ms(50);
                s_last_beep_time = now;
                s_beep_count++;
                if (s_beep_count < 3) {
                    s_beep_interval = 100;
                } else {
                    s_beep_interval = 600;
                    s_beep_count = 0;
                }
            }
        }
    }
}

void fsm_update_control_4ms(void) {
    mpu6050_raw_data_t raw;
    if (!mpu6050_read_raw(&raw)) {
        return;
    }

    /* Thuật toán tính góc theo bản tham chiếu drv_imu.c:46-61:
     * - Trừ offset cơ khí ACCEL_BALANCE_OFFSET = -535
     * - Kẹp dải ±8200 LSB (đúng 1 g ở thang đo ±4 g)
     * - Tính góc gia tốc bằng asinf() một trục
     * - Tích phân con quay với hệ số 0.000031
     * - Trộn lọc bù: 0.9996 con quay + 0.0004 gia tốc
     */
    int32_t accel_z = (int32_t)raw.accel_z - ACCEL_BALANCE_OFFSET;
    if (accel_z > 8200) accel_z = 8200;
    if (accel_z < -8200) accel_z = -8200;

    float angle_acc = asinf((float)accel_z / 8200.0f) * RAD_TO_DEG_FACTOR;
    float gyro_y_corrected = (float)(raw.gyro_y - mpu6050_get_gyro_bias_y_raw());

    float pitch;
    if (s_state == STATE_STOPPED || s_state == STATE_CALIBRATING) {
        /* Khi chưa hiệu chuẩn hoặc đang hiệu chuẩn: chốt góc bằng góc gia tốc tĩnh */
        s_angle_gyro = angle_acc;
        pitch = angle_acc;
    } else {
        s_angle_gyro += gyro_y_corrected * 0.000031f;
        s_angle_gyro = s_angle_gyro * 0.9996f + angle_acc * 0.0004f;
        pitch = s_angle_gyro;
    }
    s_last_measured_pitch = pitch;

    switch (s_state) {
        case STATE_DIAG_ANGLE:
            motor_stop();
            break;

        case STATE_DIAG_MOTOR:
            /* Giữ lệnh chạy tới trong Bài 2 */
            break;

        case STATE_READY:
            /* Tự động kích hoạt khi đi qua điểm thăng bằng: cửa sổ ±0,5° theo bản tham chiếu (app_balance.c:116) */
            if (pitch > -0.5f && pitch < 0.5f) {
                s_state = STATE_BALANCING;
                pid_reset();
                motor_enable();
            }
            break;

        case STATE_BALANCING:
            /* Kiểm tra điều kiện ngã xe: vượt quá ±30° theo bản tham chiếu (app_balance.c:133) */
            if (pitch > 30.0f || pitch < -30.0f) {
                s_state = STATE_FALLEN;
                motor_stop();
                pid_compute(pitch, 0.0f, false);
                s_is_error_nga = true;
                s_last_beep_time = timer_get_ms();
                s_beep_count = 1;
                s_beep_interval = 100;
                buzzer_on_ms(50); /* Bíp mở đầu chuỗi báo ngã */
            } else {
                /* Tính toán PID ngõ ra theo bản tham chiếu */
                float out = pid_compute(pitch, 0.0f, true);
                /* Gọi hàm throttle phi tuyến dùng chung (bỏ trùng lặp với control.c) */
                int16_t motor = motor_calc_throttle_from_pid(out);
                motor_set_throttle(motor, motor);
            }
            break;

        case STATE_FALLEN:
        case STATE_STOPPED:
        default:
            motor_stop();
            break;
    }
}
