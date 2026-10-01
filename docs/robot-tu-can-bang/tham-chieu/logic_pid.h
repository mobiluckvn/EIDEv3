#ifndef LOGIC_PID_H
#define LOGIC_PID_H

#include <stdbool.h>

void  pid_set_tunings(float kp, float ki, float kd);
float pid_compute(float angle, float pid_setpoint, bool is_running);

#endif // LOGIC_PID_H
