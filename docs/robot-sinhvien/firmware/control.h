#ifndef CONTROL_H
#define CONTROL_H

#include <stdint.h>
#include <stdbool.h>
#include "mpu6050.h"

typedef struct {
    float angle_pitch;          /* Góc nghiêng hiện tại */
    float angle_pitch_accel;    /* Góc tính từ gia tốc */
    float balance_target;       /* Điểm cân bằng tự học */
    float pid_integral;         /* Phần tích lũy sai số */
    float last_output;          /* Đầu ra vòng trước */
    int16_t motor_output_l;     /* Lệnh tốc độ cho động cơ trái */
    int16_t motor_output_r;     /* Lệnh tốc độ cho động cơ phải */
    bool is_balancing;          /* Đang trong trạng thái cân bằng */
    bool is_fallen;             /* Đã bị đổ */
} control_state_t;

void control_init(void);
void control_update_4ms(const mpu6050_raw_t *raw);
const control_state_t* control_get_state(void);
void control_reset(void);

#endif /* CONTROL_H */
