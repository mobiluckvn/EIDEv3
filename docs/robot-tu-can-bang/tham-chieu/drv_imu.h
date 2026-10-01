#ifndef DRV_IMU_H
#define DRV_IMU_H

#include <stdint.h>
#include <stdbool.h>

void imu_init(void);
bool imu_update(void);
void imu_calibrate_begin(void);
bool imu_calibrate_busy(void);
void imu_calibrate_commit(void);
float imu_get_tilt_angle(void);

#endif // DRV_IMU_H
