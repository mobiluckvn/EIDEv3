#include "drv_stepper.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdbool.h>

volatile int16_t target_speed_left = 0;
volatile int16_t target_speed_right = 0;

static uint16_t counter_left = 0;
static uint16_t counter_right = 0;
static uint16_t current_thr_left = 0;
static uint16_t current_thr_right = 0;
static bool is_stopped_left = true;
static bool is_stopped_right = true;

void stepper_init(void) {
    // Configure DIR and STEP pins for both motors as output
    DDRD |= (1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7);
    PORTD &= ~((1 << PD4) | (1 << PD5) | (1 << PD6) | (1 << PD7));

    // ref: ds-atme-timer2-01, ATmega48A-PA-88A-PA-168A-PA-328-P-DS-DS40002061B.pdf, tr.155,165-166
    TCCR2A = 0; 
    TCCR2B = 0;
    TCCR2B |= (1 << CS21);      // Prescaler 8
    OCR2A  = 39;                // 20 us interrupt period
    TCCR2A |= (1 << WGM21);     // CTC mode
    TIMSK2 |= (1 << OCIE2A);    // Enable Compare Match A interrupt
}

void stepper_set_speed(int16_t left, int16_t right) {
    cli();
    target_speed_left = left;
    target_speed_right = right;
    sei();
}

ISR(TIMER2_COMPA_vect) {
    // --- Left Motor ---
    counter_left++;
    if (counter_left > current_thr_left) {
        counter_left = 0;
        int16_t target = target_speed_left;
        if (target == 0) {
            is_stopped_left = true;
            current_thr_left = 0;
        } else {
            is_stopped_left = false;
            if (target < 0) {
                PORTD |= (1 << PD6); // DIR = 1
                current_thr_left = (uint16_t)(-target);
            } else {
                PORTD &= ~(1 << PD6); // DIR = 0
                current_thr_left = (uint16_t)(target);
            }
        }
    }

    if (!is_stopped_left) {
        if (counter_left == 1) {
            PORTD |= (1 << PD7); // STEP HIGH
        } else if (counter_left == 2 || counter_left == 0) {
            PORTD &= ~(1 << PD7); // STEP LOW
        }
    } else {
        PORTD &= ~(1 << PD7); // Ensure STEP is LOW when stopped
    }

    // --- Right Motor ---
    counter_right++;
    if (counter_right > current_thr_right) {
        counter_right = 0;
        int16_t target = target_speed_right;
        if (target == 0) {
            is_stopped_right = true;
            current_thr_right = 0;
        } else {
            is_stopped_right = false;
            if (target < 0) {
                PORTD &= ~(1 << PD4); // DIR = 0
                current_thr_right = (uint16_t)(-target);
            } else {
                PORTD |= (1 << PD4); // DIR = 1
                current_thr_right = (uint16_t)(target);
            }
        }
    }

    if (!is_stopped_right) {
        if (counter_right == 1) {
            PORTD |= (1 << PD5); // STEP HIGH
        } else if (counter_right == 2 || counter_right == 0) {
            PORTD &= ~(1 << PD5); // STEP LOW
        }
    } else {
        PORTD &= ~(1 << PD5); // Ensure STEP is LOW when stopped
    }
}
