#include "app_balance.h"
#include "drv_imu.h"
#include "logic_pid.h"
#include "drv_stepper.h"
#include "drv_buzzer.h"
#include "drv_button.h"

#define CALIB_TIMEOUT_MS 10000
#define IMU_PUMP_LIMIT 20000

typedef enum {
    STATE_CHO_NUT,
    STATE_HIEU_CHINH,
    STATE_SAN_SANG,
    STATE_CAN_BANG,
    STATE_NGA
} app_state_t;

static app_state_t current_state = STATE_CHO_NUT;
static uint32_t now_ms = 0;
static uint32_t state_start_time = 0;
static uint32_t last_beep_time = 0;
static uint8_t beep_count = 0;
static uint32_t beep_interval = 0;
static bool is_error_nga = false;
static uint8_t missed_samples = 0;

extern void i2c_tick(void);

void app_init(void) {
    imu_init();
    stepper_init();
    buzzer_init();
    button_init();
    
    now_ms = 0;
    current_state = STATE_CHO_NUT;
    buzzer_beep_async(now_ms, 100);
}

void app_step(void) {
    now_ms += 4;
    i2c_tick();

    uint16_t pump_count = 0;
    bool sample_ready = false;
    while (pump_count < IMU_PUMP_LIMIT) {
        if (imu_update()) {
            sample_ready = true;
            break;
        }
        pump_count++;
    }

    if (sample_ready) {
        missed_samples = 0;
    } else {
        if (missed_samples < 255) {
            missed_samples++;
        }
    }

    buzzer_update(now_ms);
    button_event_t btn = button_get_event(now_ms);

    switch (current_state) {
        case STATE_CHO_NUT:
            if (btn == BUTTON_EVENT_PRESSED) {
                current_state = STATE_HIEU_CHINH;
                state_start_time = now_ms;
                imu_calibrate_begin();
                beep_count = 1;
                last_beep_time = now_ms;
                buzzer_beep_async(now_ms, 100);
            }
            break;

        case STATE_HIEU_CHINH:
            if (btn == BUTTON_EVENT_PRESSED) {
                current_state = STATE_CHO_NUT;
                buzzer_beep_async(now_ms, 100);
                break;
            }

            if (now_ms - last_beep_time >= 500 && beep_count < 5) {
                buzzer_beep_async(now_ms, 100);
                last_beep_time = now_ms;
                beep_count++;
            }

            if (!imu_calibrate_busy()) {
                imu_calibrate_commit();
                current_state = STATE_SAN_SANG;
                buzzer_beep_async(now_ms, 100);
                last_beep_time = now_ms;
                beep_count = 1;
            } else if (now_ms - state_start_time > CALIB_TIMEOUT_MS) {
                current_state = STATE_NGA;
                is_error_nga = true;
                last_beep_time = now_ms;
                beep_count = 1;
                beep_interval = 100;
                buzzer_beep_async(now_ms, 50);
            }
            break;

        case STATE_SAN_SANG:
            if (now_ms - last_beep_time >= 150 && beep_count < 2) {
                buzzer_beep_async(now_ms, 100);
                last_beep_time = now_ms;
                beep_count++;
            }

            if (sample_ready) {
                float angle = imu_get_tilt_angle();
                if (angle > -0.5f && angle < 0.5f) {
                    current_state = STATE_CAN_BANG;
                }
            }
            break;

        case STATE_CAN_BANG:
            if (missed_samples >= 10) {
                stepper_set_speed(0, 0);
                pid_compute(0.0f, 0.0f, false);
                current_state = STATE_NGA;
                is_error_nga = false;
                break;
            }

            if (sample_ready) {
                float angle = imu_get_tilt_angle();
                if (angle > 30.0f || angle < -30.0f) {
                    stepper_set_speed(0, 0);
                    pid_compute(angle, 0.0f, false);
                    current_state = STATE_NGA;
                    is_error_nga = false;
                } else {
                    float out = pid_compute(angle, 0.0f, true);
                    int16_t motor = 0;
                    if (out > 0.0f) {
                        out = 405.0f - (5500.0f / (out + 9.0f));
                        motor = (int16_t)(400.0f - out);
                    } else if (out < 0.0f) {
                        out = -405.0f - (5500.0f / (out - 9.0f));
                        motor = (int16_t)(-400.0f - out);
                    } else {
                        motor = 0;
                    }
                    stepper_set_speed(motor, motor);
                }
            }
            break;

        case STATE_NGA:
            if (is_error_nga) {
                if (now_ms - last_beep_time >= beep_interval) {
                    buzzer_beep_async(now_ms, 50);
                    last_beep_time = now_ms;
                    beep_count++;
                    if (beep_count < 3) {
                        beep_interval = 100;
                    } else {
                        beep_interval = 600;
                        beep_count = 0;
                    }
                }
            }
            if (btn == BUTTON_EVENT_PRESSED) {
                current_state = STATE_CHO_NUT;
                buzzer_beep_async(now_ms, 100);
                is_error_nga = false;
            }
            break;
    }
}

void app_tick(void) {
    app_step();
}
