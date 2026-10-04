#include "config.h"
#include <math.h>

static float g_angle = 0.0f;

void filter_init(void) {
    g_angle = 0.0f;
}

float filter_calc_accel_angle(int16_t raw_az) {
    /* Cong thuc muc 2.2 va Bang A.1 (anh cho, chua co tai lieu) */
    int32_t val = (int32_t)raw_az + ACCEL_OFFSET_Z;
    if (val > ACCEL_CLIP_MAX) {
        val = ACCEL_CLIP_MAX;
    } else if (val < ACCEL_CLIP_MIN) {
        val = ACCEL_CLIP_MIN;
    }

    float ratio = (float)val / (float)ACCEL_CLIP_MAX;
    return asinf(ratio) * RAD_TO_DEG;
}

float filter_update(float accel_angle, int16_t raw_gx, int16_t raw_gy) {
    /* Cong don toc do goc va tron theo bang 3.3 */
    g_angle -= (float)raw_gx * GYRO_YAW_COEFF;
    g_angle += (float)raw_gy * GYRO_PITCH_COEFF;
    g_angle = (FILTER_WEIGHT_GYRO * g_angle) + (FILTER_WEIGHT_ACCEL * accel_angle);
    return g_angle;
}

float filter_get_angle(void) {
    return g_angle;
}
