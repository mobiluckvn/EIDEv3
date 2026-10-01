#ifndef DRV_STEPPER_H
#define DRV_STEPPER_H

#include <stdint.h>

void stepper_init(void);
void stepper_set_speed(int16_t left, int16_t right);

#endif // DRV_STEPPER_H
