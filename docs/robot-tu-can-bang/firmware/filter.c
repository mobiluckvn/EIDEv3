#include "filter.h"

void filter_init(comp_filter_t *f, float alpha, float dt) {
    f->angle     = 0.0f;
    f->gyro_rate = 0.0f;
    f->alpha     = alpha;
    f->dt        = dt;
}

float filter_update(comp_filter_t *f, float accel_angle, float gyro_rate) {
    f->gyro_rate = gyro_rate;
    /* Tích hợp con quay và bù lại bằng góc đo từ gia tốc kế */
    f->angle = f->alpha * (f->angle + gyro_rate * f->dt) + (1.0f - f->alpha) * accel_angle;
    return f->angle;
}

void filter_set_angle(comp_filter_t *f, float angle) {
    f->angle = angle;
}
