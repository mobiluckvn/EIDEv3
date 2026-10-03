#include "motor.h"
#include "config.h"
#ifndef EIDE_SIM
#include <Arduino.h>
#include <avr/interrupt.h>
#endif

static volatile uint16_t step_rate_l = 0;
static volatile uint16_t step_rate_r = 0;
static volatile uint16_t accum_l = 0;
static volatile uint16_t accum_r = 0;
static volatile uint8_t motor_is_enabled = 0;

void motor_init(void) {
    /* Đặt các chân STEP và DIR là đầu ra */
    DDR_STEP_DIR |= (1 << BIT_DIR_LEFT) | (1 << BIT_STEP_LEFT) |
                    (1 << BIT_DIR_RIGHT) | (1 << BIT_STEP_RIGHT);

    /* Mức khởi đầu LOW cho các chân motor */
    PORT_STEP_DIR &= ~((1 << BIT_DIR_LEFT) | (1 << BIT_STEP_LEFT) |
                       (1 << BIT_DIR_RIGHT) | (1 << BIT_STEP_RIGHT));

    /* Đặt chân D13 (PB5) là đầu ra đo thời gian thực thi ISR cho máy hiện sóng (Bảng 1.3) */
    DDR_DEBUG_ISR |= (1 << BIT_DEBUG_ISR);
    PORT_DEBUG_ISR &= ~(1 << BIT_DEBUG_ISR);

    /* Cấu hình Timer2 theo Bảng 16:
     * - Chế độ CTC (Clear Timer on Compare Match): WGM21 = 1
     * - Bộ chia tần 8: CS21 = 1
     * - OCR2A = FACT_OCR2A_VAL
     */
    TCCR2A = (1 << WGM21);
    TCCR2B = (1 << CS21);
    OCR2A  = FACT_OCR2A_VAL;
    TCNT2  = 0;

    /* Bật ngắt so sánh Timer2 Output Compare A */
    TIMSK2 |= (1 << OCIE2A);
}

void motor_enable(bool en) {
    motor_is_enabled = en ? 1 : 0;
    if (!en) {
        step_rate_l = 0;
        step_rate_r = 0;
        accum_l = 0;
        accum_r = 0;
        PORT_STEP_DIR &= ~((1 << BIT_STEP_LEFT) | (1 << BIT_STEP_RIGHT));
    }
}

void motor_stop(void) {
    motor_enable(false);
}

void motor_set_speeds(int16_t speed_left, int16_t speed_right) {
    /* Đặt hướng quay theo Bảng 3.3 và lấy giá trị tuyệt đối làm tốc độ bước tích lũy */
    if (speed_left >= 0) {
        if (DIR_LEFT_FORWARD) {
            PORT_STEP_DIR |= (1 << BIT_DIR_LEFT);
        } else {
            PORT_STEP_DIR &= ~(1 << BIT_DIR_LEFT);
        }
        step_rate_l = (uint16_t)speed_left;
    } else {
        if (DIR_LEFT_FORWARD) {
            PORT_STEP_DIR &= ~(1 << BIT_DIR_LEFT);
        } else {
            PORT_STEP_DIR |= (1 << BIT_DIR_LEFT);
        }
        step_rate_l = (uint16_t)(-speed_left);
    }

    if (speed_right >= 0) {
        if (DIR_RIGHT_FORWARD) {
            PORT_STEP_DIR |= (1 << BIT_DIR_RIGHT);
        } else {
            PORT_STEP_DIR &= ~(1 << BIT_DIR_RIGHT);
        }
        step_rate_r = (uint16_t)speed_right;
    } else {
        if (DIR_RIGHT_FORWARD) {
            PORT_STEP_DIR &= ~(1 << BIT_DIR_RIGHT);
        } else {
            PORT_STEP_DIR |= (1 << BIT_DIR_RIGHT);
        }
        step_rate_r = (uint16_t)(-speed_right);
    }
}

/* =========================================================================
 * TẦNG 1: ISR TIMER2
 * Ràng buộc nghiêm ngặt:
 * 1. Tuyệt đối KHÔNG dùng số thực.
 * 2. Tuyệt đối KHÔNG dùng phép chia.
 * 3. Tuyệt đối KHÔNG gọi hàm ngoài.
 * 4. Chân D13 đo thời gian chạy của ISR cho máy hiện sóng (Bảng 1.3).
 * ========================================================================= */
ISR(TIMER2_COMPA_vect) {
    /* Kéo chân D13 lên HIGH khi bắt đầu thực thi ISR để máy hiện sóng đo thời gian */
    PORT_DEBUG_ISR |= (1 << BIT_DEBUG_ISR);

    if (motor_is_enabled) {
        /* Động cơ trái: Tích lũy bước số nguyên */
        accum_l += step_rate_l;
        if (accum_l >= 5000) {
            accum_l -= 5000;
            PORT_STEP_DIR |= (1 << BIT_STEP_LEFT);
            asm volatile("nop\n\tnop\n\tnop\n\tnop\n\t");
            PORT_STEP_DIR &= ~(1 << BIT_STEP_LEFT);
        }

        /* Động cơ phải: Tích lũy bước số nguyên */
        accum_r += step_rate_r;
        if (accum_r >= 5000) {
            accum_r -= 5000;
            PORT_STEP_DIR |= (1 << BIT_STEP_RIGHT);
            asm volatile("nop\n\tnop\n\tnop\n\tnop\n\t");
            PORT_STEP_DIR &= ~(1 << BIT_STEP_RIGHT);
        }
    }

    /* Kéo chân D13 xuống LOW khi kết thúc ISR */
    PORT_DEBUG_ISR &= ~(1 << BIT_DEBUG_ISR);
}
