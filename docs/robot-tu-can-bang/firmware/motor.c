#include "motor.h"
#include "config.h"
#ifndef EIDE_SIM
#include <avr/io.h>
#include <util/atomic.h>
#else
#define ATOMIC_BLOCK(type)
#define ATOMIC_RESTORESTATE
extern uint8_t PORTD;
extern uint8_t DDRD;
#endif
#include <stdlib.h>
#include <math.h>

static volatile bool s_motor_active = false;
static volatile int16_t s_target_thr_l = 0;
static volatile int16_t s_target_thr_r = 0;

/* Các biến trạng thái nội bộ chạy trong ISR ngắt Timer2 50 kHz */
static uint16_t s_count_l = 0;
static uint16_t s_count_r = 0;
static uint16_t s_active_thr_l = 0;
static uint16_t s_active_thr_r = 0;
static uint8_t s_cur_dir_l = DIR_FORWARD_LEFT;
static uint8_t s_cur_dir_r = DIR_FORWARD_RIGHT;
static uint8_t s_next_dir_l = DIR_FORWARD_LEFT;
static uint8_t s_next_dir_r = DIR_FORWARD_RIGHT;

void motor_init(void) {
    /* Cấu hình các chân điều khiển động cơ bước là OUTPUT */
    MOTOR_L_STEP_DDR |= (1 << MOTOR_L_STEP_PIN);
    MOTOR_L_DIR_DDR  |= (1 << MOTOR_L_DIR_PIN);
    MOTOR_R_STEP_DDR |= (1 << MOTOR_R_STEP_PIN);
    MOTOR_R_DIR_DDR  |= (1 << MOTOR_R_DIR_PIN);

    motor_stop();
}

int16_t motor_speed_to_throttle(float speed_hz) {
    float abs_spd = fabsf(speed_hz);
    if (abs_spd < 10.0f) {
        return 0; /* Xử lý tường minh: đứng im (§7.6, Bảng 40) */
    }
    /* Theo §7.6: chu kỳ = (|thr| + 1) * 20 µs => |thr| = (50000 / f) - 1 */
    float thr_val = (50000.0f / abs_spd) - 1.0f;
    int16_t thr = (int16_t)(thr_val + 0.5f);
    if (thr < 1) {
        thr = 1; /* Tốc độ tối đa thiết kế: 25.000 xung/s = 1,571 m/s (Bảng 18) */
    } else if (thr > 2000) {
        thr = 2000; /* Vận tốc cực chậm sát điểm thăng bằng: 25 xung/s */
    }
    return (speed_hz >= 0.0f) ? thr : -thr;
}

int16_t motor_calc_throttle_from_pid(float out) {
    if (out > 0.0f) {
        float out_nl = 405.0f - (5500.0f / (out + 9.0f));
        return (int16_t)(400.0f - out_nl);
    } else if (out < 0.0f) {
        float out_nl = -405.0f - (5500.0f / (out - 9.0f));
        return (int16_t)(-400.0f - out_nl);
    }
    return 0;
}

void motor_set_throttle(int16_t throttle_left, int16_t throttle_right) {
    /* Yêu cầu 6 (§7.7, Bảng 43): Truy cập nguyên tử với biến 16 bit chia sẻ */
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        s_target_thr_l = throttle_left;
        s_target_thr_r = throttle_right;
    }
}

void motor_set_speed(int16_t speed_left, int16_t speed_right) {
    motor_set_throttle(motor_speed_to_throttle((float)speed_left),
                       motor_speed_to_throttle((float)speed_right));
}

void motor_stop(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        s_motor_active = false;
        s_target_thr_l = 0;
        s_target_thr_r = 0;
    }
    /* Hạ chân STEP ngay lập tức */
    MOTOR_L_STEP_PORT &= ~(1 << MOTOR_L_STEP_PIN);
    MOTOR_R_STEP_PORT &= ~(1 << MOTOR_R_STEP_PIN);
}

void motor_enable(void) {
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        s_motor_active = true;
    }
}

int16_t motor_get_throttle_l(void) {
    int16_t val;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        val = s_target_thr_l;
    }
    return val;
}

int16_t motor_get_throttle_r(void) {
    int16_t val;
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        val = s_target_thr_r;
    }
    return val;
}

/* Hàm chạy trong ISR Timer2 ngắt 50 kHz (Tầng 1) tuân thủ nghiêm ngặt §7.7 (Bảng 19) */
void motor_isr_step(void) {
    /* Yêu cầu 5: Gom mọi thao tác vào một biến tạm, ghi PORTD một lần ở cuối */
    uint8_t port_val = PORTD;

    /* Yêu cầu 1: Hạ chân STEP ở đầu lần ngắt kế tiếp (xung STEP rộng đúng 20 µs) */
    port_val &= ~((1 << MOTOR_L_STEP_PIN) | (1 << MOTOR_R_STEP_PIN));

    /* Áp mức DIR hiện thời: Bánh Trái D6, Bánh Phải D4 theo đúng V1 dòng 576-581 và 593-598:
     * - Trái: throttle < 0 -> D6 = 1 (HIGH); throttle >= 0 -> D6 = 0 (LOW) (V1:576-581)
     * - Phải: throttle < 0 -> D4 = 0 (LOW);  throttle >= 0 -> D4 = 1 (HIGH) (V1:593-598)
     */
    if (s_cur_dir_l) {
        port_val |= (1 << MOTOR_L_DIR_PIN);  /* D6 = 1 (thấp hơn 0 / lùi) */
    } else {
        port_val &= ~(1 << MOTOR_L_DIR_PIN); /* D6 = 0 (lớn hơn hoặc bằng 0 / tiến) */
    }

    if (s_cur_dir_r) {
        port_val |= (1 << MOTOR_R_DIR_PIN);  /* D4 = 1 (lớn hơn hoặc bằng 0 / tiến) */
    } else {
        port_val &= ~(1 << MOTOR_R_DIR_PIN); /* D4 = 0 (thấp hơn 0 / lùi) */
    }

    if (!s_motor_active) {
        s_count_l = 0;
        s_count_r = 0;
        s_active_thr_l = 0;
        s_active_thr_r = 0;
        PORTD = port_val;
        return;
    }

    /* -------------------------------------------------------------
     * XỬ LÝ ĐỘNG CƠ TRÁI (MOTOR L)
     * ------------------------------------------------------------- */
    /* Yêu cầu 3: throttle = 0 xử lý tường minh là đứng im */
    if (s_target_thr_l == 0) {
        s_count_l = 0;
        s_active_thr_l = 0;
    } else {
        if (s_active_thr_l == 0) {
            s_active_thr_l = (uint16_t)abs(s_target_thr_l);
            s_next_dir_l = (s_target_thr_l >= 0) ? DIR_FORWARD_LEFT : !DIR_FORWARD_LEFT;
            s_cur_dir_l = s_next_dir_l;
            s_count_l = 0;
        }

        /* Yêu cầu 2: So sánh ++dem > |thr| (lớn hơn hẳn) */
        s_count_l++;
        if (s_count_l > s_active_thr_l) {
            port_val |= (1 << MOTOR_L_STEP_PIN);
            s_count_l = 0;

            /* Yêu cầu 4: Chốt chiều và độ lớn cùng lúc tại điểm nạp lại bộ đếm */
            s_active_thr_l = (uint16_t)abs(s_target_thr_l);
            s_next_dir_l = (s_target_thr_l >= 0) ? DIR_FORWARD_LEFT : !DIR_FORWARD_LEFT;
            s_cur_dir_l = s_next_dir_l;
        }
    }

    /* -------------------------------------------------------------
     * XỬ LÝ ĐỘNG CƠ PHẢI (MOTOR R)
     * ------------------------------------------------------------- */
    /* Yêu cầu 3: throttle = 0 xử lý tường minh là đứng im */
    if (s_target_thr_r == 0) {
        s_count_r = 0;
        s_active_thr_r = 0;
    } else {
        if (s_active_thr_r == 0) {
            s_active_thr_r = (uint16_t)abs(s_target_thr_r);
            s_next_dir_r = (s_target_thr_r >= 0) ? DIR_FORWARD_RIGHT : !DIR_FORWARD_RIGHT;
            s_cur_dir_r = s_next_dir_r;
            s_count_r = 0;
        }

        /* Yêu cầu 2: So sánh ++dem > |thr| (lớn hơn hẳn) */
        s_count_r++;
        if (s_count_r > s_active_thr_r) {
            port_val |= (1 << MOTOR_R_STEP_PIN);
            s_count_r = 0;

            /* Yêu cầu 4: Chốt chiều và độ lớn cùng lúc tại điểm nạp lại bộ đếm */
            s_active_thr_r = (uint16_t)abs(s_target_thr_r);
            s_next_dir_r = (s_target_thr_r >= 0) ? DIR_FORWARD_RIGHT : !DIR_FORWARD_RIGHT;
            s_cur_dir_r = s_next_dir_r;
        }
    }

    /* Yêu cầu 5: Ghi PORTD một lần duy nhất ở cuối */
    PORTD = port_val;
}
