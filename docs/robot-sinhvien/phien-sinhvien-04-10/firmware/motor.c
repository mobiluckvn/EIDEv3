#include "config.h"

static volatile bool g_motor_enabled = false;
static volatile int16_t g_target_pulse_l = 0;
static volatile int16_t g_target_pulse_r = 0;

static uint16_t g_step_count_l = 0;
static uint16_t g_step_count_r = 0;
static uint16_t g_current_period_l = 0;
static uint16_t g_current_period_r = 0;

void motor_init(void) {
    /* Bang 3.1 buoc 3: Dat 4 chan dong co lam chan ra, ha hai chan xung ve 0 */
    MOTOR_DDR |= (1 << PIN_DIR_L) | (1 << PIN_DIR_R) | (1 << PIN_STEP_L) | (1 << PIN_STEP_R);
    MOTOR_PORT &= ~((1 << PIN_STEP_L) | (1 << PIN_STEP_R));
    g_motor_enabled = false;
}

void motor_enable(bool en) {
    g_motor_enabled = en;
}

void motor_set_target(int16_t pulse_l, int16_t pulse_r) {
    g_target_pulse_l = pulse_l;
    g_target_pulse_r = pulse_r;
}

int16_t motor_calc_pulse(float output) {
    if (output > 0.0f) {
        float out_nl = 405.0f - (5500.0f / (output + 9.0f));
        float p = 400.0f - out_nl;
        if (p < MOTOR_PULSE_MIN) {
            p = MOTOR_PULSE_MIN;
        } else if (p > MOTOR_PULSE_MAX) {
            p = MOTOR_PULSE_MAX;
        }
        return (int16_t)(p + 0.5f);
    } else if (output < 0.0f) {
        float out_nl = -405.0f - (5500.0f / (output - 9.0f));
        float p = -400.0f - out_nl;
        if (p > -MOTOR_PULSE_MIN) {
            p = -MOTOR_PULSE_MIN;
        } else if (p < -MOTOR_PULSE_MAX) {
            p = -MOTOR_PULSE_MAX;
        }
        return (int16_t)(p - 0.5f);
    }
    return 0;
}

void motor_step_isr(void) {
    /* Dieu kien 1: Doc thanh ghi cong vao mot bien tam */
    uint8_t port_val = MOTOR_PORT;

    /* Dieu kien 2: Ha hai chan xung xuong muc thap ngay o dau ham */
    port_val &= ~((1 << PIN_STEP_L) | (1 << PIN_STEP_R));

    /* Dieu kien 6: Khi co cho phep chay dang tat thi dat bien ve 0 va thoat */
    if (!g_motor_enabled) {
        g_step_count_l = 0;
        g_step_count_r = 0;
        g_current_period_l = 0;
        g_current_period_r = 0;
        MOTOR_PORT = port_val;
        return;
    }

    /* Xu ly banh trai */
    if (g_target_pulse_l == 0) {
        g_step_count_l = 0;
        g_current_period_l = 0;
    } else {
        if (g_current_period_l == 0) {
            g_current_period_l = (g_target_pulse_l > 0) ? g_target_pulse_l : -g_target_pulse_l;
            if (g_target_pulse_l >= 0) {
                port_val &= ~(1 << PIN_DIR_L); /* Bang A.2: Tien = muc 0 */
            } else {
                port_val |= (1 << PIN_DIR_L);
            }
            g_step_count_l = 0;
        }
        g_step_count_l++;
        if (g_step_count_l > g_current_period_l) {
            port_val |= (1 << PIN_STEP_L);
            g_step_count_l = 0;
            g_current_period_l = (g_target_pulse_l > 0) ? g_target_pulse_l : -g_target_pulse_l;
            if (g_target_pulse_l >= 0) {
                port_val &= ~(1 << PIN_DIR_L);
            } else {
                port_val |= (1 << PIN_DIR_L);
            }
        }
    }

    /* Xu ly banh phai */
    if (g_target_pulse_r == 0) {
        g_step_count_r = 0;
        g_current_period_r = 0;
    } else {
        if (g_current_period_r == 0) {
            g_current_period_r = (g_target_pulse_r > 0) ? g_target_pulse_r : -g_target_pulse_r;
            if (g_target_pulse_r >= 0) {
                port_val |= (1 << PIN_DIR_R); /* Bang A.2: Tien = muc 1 */
            } else {
                port_val &= ~(1 << PIN_DIR_R);
            }
            g_step_count_r = 0;
        }
        g_step_count_r++;
        if (g_step_count_r > g_current_period_r) {
            port_val |= (1 << PIN_STEP_R);
            g_step_count_r = 0;
            g_current_period_r = (g_target_pulse_r > 0) ? g_target_pulse_r : -g_target_pulse_r;
            if (g_target_pulse_r >= 0) {
                port_val |= (1 << PIN_DIR_R);
            } else {
                port_val &= ~(1 << PIN_DIR_R);
            }
        }
    }

    /* Ghi bien tam ra cong dung mot lan duy nhat */
    MOTOR_PORT = port_val;
}
