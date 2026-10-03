#ifndef MOTOR_H
#define MOTOR_H

#include <stdint.h>
#include <stdbool.h>

void motor_init(void);
void motor_set_speeds(int16_t speed_left, int16_t speed_right);
void motor_enable(bool en);
void motor_stop(void);

#endif /* MOTOR_H */
