#ifndef MOCK_AVR_IO_H
#define MOCK_AVR_IO_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

extern volatile uint8_t PORTD;
extern volatile uint8_t DDRD;
extern volatile uint8_t PINB;
extern volatile uint8_t PORTB;
extern volatile uint8_t DDRB;
extern volatile uint8_t TCCR2A;
extern volatile uint8_t TCCR2B;
extern volatile uint8_t OCR2A;
extern volatile uint8_t TCNT2;
extern volatile uint8_t TIMSK2;

#define WGM21  1
#define CS21   1
#define OCIE2A 1

#ifdef __cplusplus
}
#endif

#endif /* MOCK_AVR_IO_H */