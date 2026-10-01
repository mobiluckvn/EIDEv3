#include "mpu6050.h"
#include "config.h"
#include "i2c.h"
#include <stddef.h>

#define REG_SMPLRT_DIV    0x19
#define REG_CONFIG        0x1A
#define REG_GYRO_CONFIG   0x1B
#define REG_ACCEL_CONFIG  0x1C
#define REG_ACCEL_XOUT_H  0x3B
#define REG_PWR_MGMT_1    0x6B

/* Hệ số tỉ lệ nhạy cảm biến: ±4 g tương ứng 8192 LSB/g (Phụ lục A.3) */
#define ACCEL_SCALE_FACTOR 8192.0f
#define GYRO_SCALE_FACTOR  131.0f

static float s_gyro_bias_x = 0.0f;
static float s_gyro_bias_y = 0.0f;
static float s_gyro_bias_z = 0.0f;

bool mpu6050_init(void) {
    /* Đánh thức MPU6050 bằng cách xoá bit SLEEP trong thanh ghi PWR_MGMT_1 */
    if (!i2c_write_byte(MPU6050_ADDR, REG_PWR_MGMT_1, 0x00)) {
        return false;
    }
    /* Đặt bộ lọc số thông thấp DLPF */
    if (!i2c_write_byte(MPU6050_ADDR, REG_CONFIG, 0x03)) {
        return false;
    }
    /* Đặt thang đo con quay */
    if (!i2c_write_byte(MPU6050_ADDR, REG_GYRO_CONFIG, 0x00)) {
        return false;
    }
    /* Đặt thang đo gia tốc ±4 g (AFS_SEL = 1, bit [4:3] = 01 -> 0x08) */
    if (!i2c_write_byte(MPU6050_ADDR, REG_ACCEL_CONFIG, 0x08)) {
        return false;
    }
    return true;
}

bool mpu6050_read_raw(mpu6050_raw_data_t *raw) {
    uint8_t buf[14];
    if (!i2c_read_bytes(MPU6050_ADDR, REG_ACCEL_XOUT_H, buf, 14)) {
        return false;
    }

    raw->accel_x = (int16_t)((buf[0] << 8) | buf[1]);
    raw->accel_y = (int16_t)((buf[2] << 8) | buf[3]);
    raw->accel_z = (int16_t)((buf[4] << 8) | buf[5]);
    raw->gyro_x  = (int16_t)((buf[8] << 8) | buf[9]);
    raw->gyro_y  = (int16_t)((buf[10] << 8) | buf[11]);
    raw->gyro_z  = (int16_t)((buf[12] << 8) | buf[13]);

    return true;
}

static int32_t s_calib_sum_gx = 0;
static int32_t s_calib_sum_gy = 0;
static int32_t s_calib_sum_gz = 0;
static uint16_t s_calib_count = 0;

void mpu6050_calib_reset(void) {
    s_calib_sum_gx = 0;
    s_calib_sum_gy = 0;
    s_calib_sum_gz = 0;
    s_calib_count = 0;
}

bool mpu6050_calib_step(bool *out_done) {
    if (out_done == NULL) {
        return false;
    }
    *out_done = false;

    mpu6050_raw_data_t raw;
    if (!mpu6050_read_raw(&raw)) {
        return false;
    }

    s_calib_sum_gx += raw.gyro_x;
    s_calib_sum_gy += raw.gyro_y;
    s_calib_sum_gz += raw.gyro_z;
    s_calib_count++;

    if (s_calib_count >= CALIB_SAMPLES) {
        s_gyro_bias_x = (float)s_calib_sum_gx / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);
        s_gyro_bias_y = (float)s_calib_sum_gy / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);
        s_gyro_bias_z = (float)s_calib_sum_gz / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);
        *out_done = true;
    }

    return true;
}

bool mpu6050_calibrate_gyro(void) {
    int32_t sum_gx = 0;
    int32_t sum_gy = 0;
    int32_t sum_gz = 0;
    mpu6050_raw_data_t raw;

    for (uint16_t i = 0; i < CALIB_SAMPLES; i++) {
        if (!mpu6050_read_raw(&raw)) {
            return false;
        }
        sum_gx += raw.gyro_x;
        sum_gy += raw.gyro_y;
        sum_gz += raw.gyro_z;
    }

    s_gyro_bias_x = (float)sum_gx / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);
    s_gyro_bias_y = (float)sum_gy / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);
    s_gyro_bias_z = (float)sum_gz / ((float)CALIB_SAMPLES * GYRO_SCALE_FACTOR);

    return true;
}

bool mpu6050_read_scaled(mpu6050_data_t *data) {
    mpu6050_raw_data_t raw;
    if (!mpu6050_read_raw(&raw)) {
        return false;
    }

    data->accel_x_g = (float)raw.accel_x / ACCEL_SCALE_FACTOR;
    data->accel_y_g = (float)raw.accel_y / ACCEL_SCALE_FACTOR;
    data->accel_z_g = (float)raw.accel_z / ACCEL_SCALE_FACTOR;

    data->gyro_x_dps = ((float)raw.gyro_x / GYRO_SCALE_FACTOR) - s_gyro_bias_x;
    data->gyro_y_dps = ((float)raw.gyro_y / GYRO_SCALE_FACTOR) - s_gyro_bias_y;
    data->gyro_z_dps = ((float)raw.gyro_z / GYRO_SCALE_FACTOR) - s_gyro_bias_z;

    return true;
}
