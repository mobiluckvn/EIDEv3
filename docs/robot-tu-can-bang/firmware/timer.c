#include "timer.h"
#include "config.h"
#include <avr/interrupt.h>

static volatile uint32_t s_system_ms = 0;
static volatile bool s_flag_control_4ms = false;
static volatile uint8_t s_tick_counter_4ms = 0;

/* Khai báo hàm ngắt tầng 1 sinh xung bước từ mô-đun motor */
extern void motor_isr_step(void);

void timer_init(void) {
    /* Cấu hình Timer0: Chế độ CTC, Prescaler 64, ngắt chu kỳ 1 ms */
    TCCR0A = (1 << WGM01);              /* CTC mode */
    TCCR0B = (1 << CS01) | (1 << CS00); /* Prescaler 64 */
    OCR0A  = 249;
    TIMSK0 |= (1 << OCIE0A);            /* Bật ngắt so sánh kênh A */

    /* Cấu hình Timer2: Chế độ CTC, Prescaler 8, ngắt 50 kHz */
    TCCR2A = (1 << WGM21);              /* CTC mode */
    TCCR2B = (1 << CS21);               /* Prescaler 8 */
    OCR2A  = 39;
    TIMSK2 |= (1 << OCIE2A);            /* Bật ngắt so sánh kênh A */
    /* Cấu hình chân điểm đo PROBE_ISR D13 (PB5) là OUTPUT, ban đầu LOW */
    PROBE_ISR_DDR |= (1 << PROBE_ISR_PIN);
    PROBE_ISR_PORT &= ~(1 << PROBE_ISR_PIN);
}

/* Ngắt Timer0: 1 ms hệ thống, đánh cờ kích hoạt Tầng 2 mỗi chu kỳ điều khiển */
ISR(TIMER0_COMPA_vect) {
    s_system_ms++;
    s_tick_counter_4ms++;
    if (s_tick_counter_4ms >= CONTROL_LOOP_MS) {
        s_tick_counter_4ms = 0;
        s_flag_control_4ms = true;
    }
}

/* Ngắt Timer2: Tầng 1 sinh xung bước kèm điểm đo PROBE_ISR D13 (§13.4, Mục 9) */
ISR(TIMER2_COMPA_vect) {
    PROBE_ISR_PORT |= (1 << PROBE_ISR_PIN);  /* Dựng xung PROBE_ISR D13 ở đầu ISR (sbi) */
    motor_isr_step();
    PROBE_ISR_PORT &= ~(1 << PROBE_ISR_PIN); /* Hạ xung PROBE_ISR D13 ở cuối ISR (cbi) */
}

uint32_t timer_get_ms(void) {
    uint32_t ms;
    uint8_t sreg = SREG;
    cli(); /* Cấm ngắt ngắn gọn vài chu kỳ lệnh asm */
    ms = s_system_ms;
    SREG = sreg;
    return ms;
}

bool timer_check_control_flag(void) {
    if (s_flag_control_4ms) {
        s_flag_control_4ms = false;
        return true;
    }
    return false;
}
