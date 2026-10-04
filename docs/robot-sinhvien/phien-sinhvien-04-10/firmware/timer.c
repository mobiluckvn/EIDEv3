#include "config.h"

static volatile uint32_t g_millis_count = 0;
static volatile uint32_t g_timer2_ticks = 0;

void timer_init(void) {
    g_timer2_ticks = 0;
    /* Timer0: CTC, prescaler 64, ngat 1 ms */
    TCCR0A = (1 << WGM01);
    TCCR0B = (1 << CS01) | (1 << CS00);
    OCR0A = 249;
    TIMSK0 = (1 << OCIE0A);

    /* Timer2: CTC, prescaler 8, ngat 50 kHz */
    TCCR2A = (1 << WGM21);
    TCCR2B = (1 << CS21);
    OCR2A = 39;
    TIMSK2 = (1 << OCIE2A);
}

uint32_t millis(void) {
    uint32_t m;
    uint8_t sreg = SREG;
    cli();
    m = g_millis_count;
    SREG = sreg;
    return m;
}

uint32_t micros(void) {
    uint32_t m;
    uint8_t t;
    uint8_t sreg = SREG;
    cli();
    m = g_millis_count;
    t = TCNT0;
    /* Neu co co ngat COMPA dang cho ma TCNT0 da reset ve 0 */
    if ((TIFR0 & (1 << OCF0A)) && (t < 249)) {
        m++;
    }
    SREG = sreg;
    return (m * 1000UL) + ((uint32_t)t * 4UL);
}

void delay_ms(uint16_t ms) {
    uint32_t start = millis();
    while ((uint16_t)(millis() - start) < ms) {
        /* cho */
    }
}

uint32_t timer_get_step_ticks(void) {
    uint32_t t;
    uint8_t sreg = SREG;
    cli();
    t = g_timer2_ticks;
    SREG = sreg;
    return t;
}

ISR(TIMER0_COMPA_vect) {
    g_millis_count++;
}

ISR(TIMER2_COMPA_vect) {
    /* NT-A: Dao chan D13 (PB5) de do bang may hien song */
    PINB = (1 << PIN_TEST_D13);
    g_timer2_ticks++;
    motor_step_isr();
}
