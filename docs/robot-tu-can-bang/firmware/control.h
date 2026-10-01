#ifndef CONTROL_H_
#define CONTROL_H_

#include <stdint.h>
#include <stdbool.h>
#include "filter.h"
#include "pid.h"

/* Các trạng thái hoạt động của hệ thống điều khiển */
typedef enum {
    CONTROL_STATE_INIT = 0,
    CONTROL_STATE_CALIBRATING,
    CONTROL_STATE_READY,
    CONTROL_STATE_BALANCING,
    CONTROL_STATE_FALLEN,
    CONTROL_STATE_STOPPED
} control_state_t;

typedef struct {
    control_state_t state;
    comp_filter_t filter;
    float current_pitch;
    int16_t motor_speed;
    bool motor_enabled;
    bool fall_triggered;
} control_system_t;

/* Khởi tạo hệ thống điều khiển với bộ lọc và thông số PID */
void control_init(control_system_t *cs);

/* Reset trạng thái tích phân PID và tốc độ motor */
void control_reset(control_system_t *cs);

/* Chuyển trạng thái hoạt động */
void control_set_state(control_system_t *cs, control_state_t new_state);

/* Thực thi bước tính toán chu kỳ 4 ms (Tầng 2) */
int16_t control_update_4ms(control_system_t *cs, float accel_x_g, float accel_z_g, float gyro_y_dps);

#endif /* CONTROL_H_ */
