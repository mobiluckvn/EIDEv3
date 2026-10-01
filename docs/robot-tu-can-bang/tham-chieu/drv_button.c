#include "drv_button.h"
#include <avr/io.h>

static uint8_t button_state_debounced = 1; // 1 = released, 0 = pressed
static uint8_t button_state_raw_prev = 1;
static uint32_t debounce_start_time = 0;
static uint8_t last_reported_state = 1;

void button_init(void) {
    // ref: ds-atme-gpio-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.85-100
    DDRB &= ~(1 << 4);  // Configure PB4 as input
    PORTB |= (1 << 4);  // Enable internal pull-up on PB4
}

button_event_t button_get_event(uint32_t current_time_ms) {
    uint8_t raw_state = (PINB & (1 << 4)) ? 1 : 0;
    
    if (raw_state != button_state_raw_prev) {
        debounce_start_time = current_time_ms;
        button_state_raw_prev = raw_state;
    }
    
    if ((current_time_ms - debounce_start_time) >= 20) {
        if (raw_state != button_state_debounced) {
            button_state_debounced = raw_state;
        }
    }
    
    if (button_state_debounced != last_reported_state) {
        last_reported_state = button_state_debounced;
        if (button_state_debounced == 0) {
            return BUTTON_EVENT_PRESSED;
        } else {
            return BUTTON_EVENT_RELEASED;
        }
    }
    
    return BUTTON_EVENT_NONE;
}
