#include "drv_buzzer.h"
#include <avr/io.h>

static uint32_t beep_start_time = 0;
static uint32_t beep_duration = 0;
static bool is_beeping = false;

void buzzer_init(void) {
    // ref: ds-atme-gpio-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.85-100
    DDRB |= (1 << DDB2);
    // ref: ds-atme-gpio-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.85-100
    PORTB &= ~(1 << PORTB2);
    is_beeping = false;
}

void buzzer_beep_async(uint32_t current_time_ms, uint32_t duration_ms) {
    if (duration_ms > 0) {
        beep_start_time = current_time_ms;
        beep_duration = duration_ms;
        is_beeping = true;
        // ref: ds-atme-gpio-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.85-100
        PORTB |= (1 << PORTB2);
    } else {
        buzzer_stop();
    }
}

void buzzer_update(uint32_t current_time_ms) {
    if (is_beeping) {
        if ((current_time_ms - beep_start_time) >= beep_duration) {
            buzzer_stop();
        }
    }
}

void buzzer_stop(void) {
    is_beeping = false;
    // ref: ds-atme-gpio-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.85-100
    PORTB &= ~(1 << PORTB2);
}
