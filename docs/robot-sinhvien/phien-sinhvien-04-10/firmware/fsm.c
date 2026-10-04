#include "config.h"

static robot_state_t g_state = STATE_BOOT;
static uint32_t g_last_loop_time = 0;
static uint32_t g_last_batt_time = 0;
static uint16_t g_battery_raw = 0;
static int16_t g_last_az = 0;
static int16_t g_last_pulse_l = 0;
static int16_t g_last_pulse_r = 0;
static uint8_t g_telem_div = 0;
static uint16_t g_loop_overrun_count = 0;
static uint16_t g_timing_i2c = 0;
static uint16_t g_timing_filter = 0;
static uint16_t g_timing_ctrl = 0;
static uint16_t g_timing_total = 0;
static uint8_t g_timing_report_div = 0;

static const char* state_to_str(robot_state_t st) {
    switch (st) {
        case STATE_BOOT: return "BOOT";
        case STATE_CALIBRATE: return "CALIB";
        case STATE_WAIT_BALANCE: return "WAIT";
        case STATE_RUNNING: return "RUN";
        case STATE_FALLEN: return "FALL";
        case STATE_LOW_BATT: return "LOWBATT";
        case STATE_SELF_TEST: return "USB_TEST";
        case STATE_ERROR: return "ERR";
        default: return "UNKNOWN";
    }
}

static void adc_init(void) {
    /* Bang 3.4: ADMUX bat REFS0, ADCSRA bat ADEN, ADSC, ADPS2..0 */
    ADMUX = (1 << REFS0) | (ADC_PIN_BATT & 0x07);
    ADCSRA = (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1) | (1 << ADPS0);
}

static uint16_t adc_read(void) {
    ADCSRA |= (1 << ADSC);
    while (ADCSRA & (1 << ADSC));
    return ADC;
}

void fsm_init(bool self_test_requested) {
    adc_init();
    if (self_test_requested) {
        g_state = STATE_SELF_TEST;
    } else {
        g_state = STATE_CALIBRATE;
    }
    g_last_loop_time = millis();
    g_last_batt_time = millis();
    g_last_az = 0;
    g_last_pulse_l = 0;
    g_last_pulse_r = 0;
    g_telem_div = 0;
    g_loop_overrun_count = 0;
    g_timing_i2c = 0;
    g_timing_filter = 0;
    g_timing_ctrl = 0;
    g_timing_total = 0;
    g_timing_report_div = 0;
}

robot_state_t fsm_get_state(void) {
    return g_state;
}

void fsm_update(void) {
    uint32_t now = millis();

    /* Nguoi dung co the chu dong nhan nut PB4 de vao che do chay thu USB khong pin */
    if (!(BUTTON_PIN & (1 << PIN_BUTTON))) {
        g_state = STATE_SELF_TEST;
        motor_enable(false);
    }

    /* Do pin moi 500 ms theo bang 3.3. Giu nguyen nguong 420 cho duong chay that */
    if (now - g_last_batt_time >= 500) {
        g_last_batt_time = now;
        g_battery_raw = adc_read();
        if (g_battery_raw < 420 && g_state != STATE_BOOT && g_state != STATE_SELF_TEST) {
            g_state = STATE_LOW_BATT;
            motor_enable(false);
        }
    }

    /* Vong tinh 4 ms theo muc 3.3 va NT-B */
    if (now - g_last_loop_time >= 4) {
        if (now - g_last_loop_time > 40) {
            g_last_loop_time = now;
            g_loop_overrun_count++;
        } else {
            g_last_loop_time += 4;
        }

        /* Dao chan A1 moi vong de do bang may hien song theo NT-B */
        TEST_A1_PORT ^= (1 << PIN_TEST_A1);

        uint32_t t0 = micros();

        int16_t az, gx, gy;
        if (!mpu6050_read_raw(&az, &gx, &gy)) {
            g_state = STATE_ERROR;
            motor_enable(false);
            return;
        }
        uint32_t t1 = micros();

        float accel_angle = filter_calc_accel_angle(az);
        float current_angle = filter_update(accel_angle, gx, gy);
        g_last_az = az;
        uint32_t t2 = micros();

        switch (g_state) {
            case STATE_BOOT:
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                break;

            case STATE_CALIBRATE:
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                mpu6050_calibrate();
                g_state = STATE_WAIT_BALANCE;
                break;

            case STATE_WAIT_BALANCE:
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                if (current_angle >= -ANGLE_WINDOW_BALANCE && current_angle <= ANGLE_WINDOW_BALANCE) {
                    pid_reset();
                    motor_enable(true);
                    g_state = STATE_RUNNING;
                }
                break;

            case STATE_RUNNING:
                if (current_angle > ANGLE_LIMIT_FALLEN || current_angle < -ANGLE_LIMIT_FALLEN) {
                    motor_enable(false);
                    g_last_pulse_l = 0;
                    g_last_pulse_r = 0;
                    g_state = STATE_FALLEN;
                } else {
                    float out = pid_calculate(current_angle);
                    int16_t pulse = motor_calc_pulse(out);
                    g_last_pulse_l = pulse;
                    g_last_pulse_r = pulse;
                    motor_set_target(pulse, pulse);
                }
                break;

            case STATE_FALLEN:
                motor_enable(false);
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                if (current_angle >= -ANGLE_WINDOW_BALANCE && current_angle <= ANGLE_WINDOW_BALANCE) {
                    pid_reset();
                    motor_enable(true);
                    g_state = STATE_RUNNING;
                }
                break;

            case STATE_LOW_BATT:
                motor_enable(false);
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                break;

            case STATE_SELF_TEST:
                /* Che do chay thu qua USB khong pin: tu choi phat xung dong co */
                motor_enable(false);
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                break;

            case STATE_ERROR:
                motor_enable(false);
                g_last_pulse_l = 0;
                g_last_pulse_r = 0;
                break;
        }
        uint32_t t3 = micros();

        g_timing_i2c = (uint16_t)(t1 - t0);
        g_timing_filter = (uint16_t)(t2 - t1);
        g_timing_ctrl = (uint16_t)(t3 - t2);
        g_timing_total = (uint16_t)(t3 - t0);

        if (g_timing_total > 4000) {
            g_loop_overrun_count++;
        }

        /* Phat telemetry moi 100 ms (dung 25 chu ky vong tinh 4 ms): muc 3.10 va NT-UART */
        g_telem_div++;
        if (g_telem_div >= 25) {
            g_telem_div = 0;
            uart_send_telemetry(state_to_str(g_state), current_angle, g_last_az, g_last_pulse_l, g_last_pulse_r, uart_get_dropped_lines(), g_loop_overrun_count);
            g_timing_report_div++;
        }

        /* Dinh ky 1 giay (10 lan telemetry) bao cao thoi gian tung chang: gui o tick 12 lech pha (48 ms sau telemetry) de khong tranh dem */
        if (g_telem_div == 12 && g_timing_report_div >= 10) {
            g_timing_report_div = 0;
            uart_send_timing(g_timing_i2c, g_timing_filter, g_timing_ctrl, g_timing_total);
        }
    }
}
