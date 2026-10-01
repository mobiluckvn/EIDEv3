#include "motor.h"
#include "config.h"
#include <stdlib.h>

static volatile bool s_motor_active = false;
static volatile int16_t s_speed_left = 0;
static volatile int16_t s_speed_right = 0;

static uint32_t s_accum_left = 0;
static uint32_t s_accum_right = 0;

void motor_init(void) {
    /* Cấu hình các chân điều khiển động cơ bước là OUTPUT */
    MOTOR_L_STEP_DDR |= (1 << MOTOR_L_STEP_PIN);
    MOTOR_L_DIR_DDR  |= (1 << MOTOR_L_DIR_PIN);
    MOTOR_R_STEP_DDR |= (1 << MOTOR_R_STEP_PIN);
    MOTOR_R_DIR_DDR  |= (1 << MOTOR_R_DIR_PIN);

    motor_stop();
}

void motor_set_speed(int16_t speed_left, int16_t speed_right) {
    s_speed_left = speed_left;
    s_speed_right = speed_right;

    /* Cập nhật hướng quay DIR */
    if (speed_left >= 0) {
        MOTOR_L_DIR_PORT |= (1 << MOTOR_L_DIR_PIN);
    } else {
        MOTOR_L_DIR_PORT &= ~(1 << MOTOR_L_DIR_PIN);
    }

    if (speed_right >= 0) {
        MOTOR_R_DIR_PORT |= (1 << MOTOR_R_DIR_PIN);
    } else {
        MOTOR_R_DIR_PORT &= ~(1 << MOTOR_R_DIR_PIN);
    }
}

void motor_stop(void) {
    s_motor_active = false;
    s_speed_left = 0;
    s_speed_right = 0;
    s_accum_left = 0;
    s_accum_right = 0;

    /* Kéo xung STEP xuống mức thấp để ngừng kích hoạt bước */
    /* Lưu ý: Chân EN nối cứng GND nên dừng động cơ bằng cách ngắt xung STEP */
    MOTOR_L_STEP_PORT &= ~(1 << MOTOR_L_STEP_PIN);
    MOTOR_R_STEP_PORT &= ~(1 << MOTOR_R_STEP_PIN);
}

void motor_enable(void) {
    s_motor_active = true;
}

/* Hàm chạy trong ISR Timer2 ngắt 50 kHz (Tầng 1) */
void motor_isr_step(void) {
    if (!s_motor_active) {
        MOTOR_L_STEP_PORT &= ~(1 << MOTOR_L_STEP_PIN);
        MOTOR_R_STEP_PORT &= ~(1 << MOTOR_R_STEP_PIN);
        return;
    }

    /* Thuật toán DDA tích luỹ bước động cơ trái */
    uint16_t mag_l = (uint16_t)abs(s_speed_left);
    s_accum_left += mag_l;
    if (s_accum_left >= TIMER2_FREQ_HZ) {
        s_accum_left -= TIMER2_FREQ_HZ;
        MOTOR_L_STEP_PORT |= (1 << MOTOR_L_STEP_PIN);
    } else {
        MOTOR_L_STEP_PORT &= ~(1 << MOTOR_L_STEP_PIN);
    }

    /* Thuật toán DDA tích luỹ bước động cơ phải */
    uint16_t mag_r = (uint16_t)abs(s_speed_right);
    s_accum_right += mag_r;
    if (s_accum_right >= TIMER2_FREQ_HZ) {
        s_accum_right -= TIMER2_FREQ_HZ;
        MOTOR_R_STEP_PORT |= (1 << MOTOR_R_STEP_PIN);
    } else {
        MOTOR_R_STEP_PORT &= ~(1 << MOTOR_R_STEP_PIN);
    }
}
