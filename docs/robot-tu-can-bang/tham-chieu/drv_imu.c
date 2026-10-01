#include "drv_imu.h"
#include "drv_i2c.h"
#include <math.h>

// ref: ds-031, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.40-45
// ref: ds-032, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.29-31

#define MPU6050_ADDR 0x68
#define ACCEL_BALANCE_OFFSET (-535)

typedef enum {
    STATE_INIT_PWR_START,
    STATE_INIT_PWR_WAIT,
    STATE_INIT_GYRO_START,
    STATE_INIT_GYRO_WAIT,
    STATE_INIT_ACCEL_START,
    STATE_INIT_ACCEL_WAIT,
    STATE_INIT_CONFIG_START,
    STATE_INIT_CONFIG_WAIT,
    STATE_READ_REG_START,
    STATE_READ_REG_WAIT,
    STATE_READ_DATA_START,
    STATE_READ_DATA_WAIT
} imu_state_t;

static imu_state_t current_state = STATE_INIT_PWR_START;
static uint8_t tx_buf[2];
static uint8_t rx_buf[14];

static float angle_gyro = 0.0f;
static float angle_acc = 0.0f;
static bool is_calibrating = false;
static uint16_t calib_count = 0;
static int32_t gyro_y_sum = 0;
static int16_t gyro_y_offset = 0;

void imu_init(void) {
    i2c_init();
    current_state = STATE_INIT_PWR_START;
}

static void process_data(const uint8_t *data) {
    int16_t accel_z_raw = (int16_t)((data[8] << 8) | data[9]);
    int16_t gyro_y_raw = (int16_t)((data[10] << 8) | data[11]);

    int32_t accel_z = accel_z_raw - ACCEL_BALANCE_OFFSET;
    if (accel_z > 8200) accel_z = 8200;
    if (accel_z < -8200) accel_z = -8200;

    angle_acc = asin((float)accel_z / 8200.0f) * 57.296f;

    if (is_calibrating) {
        if (calib_count < 500) {
            gyro_y_sum += gyro_y_raw;
            calib_count++;
        }
    } else {
        float gyro_y_corrected = (float)(gyro_y_raw - gyro_y_offset);
        angle_gyro += gyro_y_corrected * 0.000031f;
        angle_gyro = angle_gyro * 0.9996f + angle_acc * 0.0004f;
    }
}

bool imu_update(void) {
    i2c_status_t status = i2c_get_status();

    switch (current_state) {
        case STATE_INIT_PWR_START:
            // ref: ds-031, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.40-45
            tx_buf[0] = 0x6B; tx_buf[1] = 0x00;
            if (i2c_write_async(MPU6050_ADDR, tx_buf, 2)) {
                current_state = STATE_INIT_PWR_WAIT;
            }
            break;
        case STATE_INIT_PWR_WAIT:
            if (status == I2C_SUCCESS) current_state = STATE_INIT_GYRO_START;
            else if (status == I2C_ERROR) current_state = STATE_INIT_PWR_START;
            break;
            
        case STATE_INIT_GYRO_START:
            // ref: ds-032, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.29-31
            tx_buf[0] = 0x1B; tx_buf[1] = 0x00;
            if (i2c_write_async(MPU6050_ADDR, tx_buf, 2)) {
                current_state = STATE_INIT_GYRO_WAIT;
            }
            break;
        case STATE_INIT_GYRO_WAIT:
            if (status == I2C_SUCCESS) current_state = STATE_INIT_ACCEL_START;
            else if (status == I2C_ERROR) current_state = STATE_INIT_GYRO_START;
            break;
            
        case STATE_INIT_ACCEL_START:
            // ref: ds-032, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.29-31
            tx_buf[0] = 0x1C; tx_buf[1] = 0x08;
            if (i2c_write_async(MPU6050_ADDR, tx_buf, 2)) {
                current_state = STATE_INIT_ACCEL_WAIT;
            }
            break;
        case STATE_INIT_ACCEL_WAIT:
            if (status == I2C_SUCCESS) current_state = STATE_INIT_CONFIG_START;
            else if (status == I2C_ERROR) current_state = STATE_INIT_ACCEL_START;
            break;
            
        case STATE_INIT_CONFIG_START:
            // ref: ds-031, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.40-45
            tx_buf[0] = 0x1A; tx_buf[1] = 0x03;
            if (i2c_write_async(MPU6050_ADDR, tx_buf, 2)) {
                current_state = STATE_INIT_CONFIG_WAIT;
            }
            break;
        case STATE_INIT_CONFIG_WAIT:
            if (status == I2C_SUCCESS) current_state = STATE_READ_REG_START;
            else if (status == I2C_ERROR) current_state = STATE_INIT_CONFIG_START;
            break;
            
        case STATE_READ_REG_START:
            // ref: ds-032, MPU-6000/MPU-6050 Register Map rev. 4.2, tr.29-31
            tx_buf[0] = 0x3B;
            if (i2c_write_async(MPU6050_ADDR, tx_buf, 1)) {
                current_state = STATE_READ_REG_WAIT;
            }
            break;
        case STATE_READ_REG_WAIT:
            if (status == I2C_SUCCESS) current_state = STATE_READ_DATA_START;
            else if (status == I2C_ERROR) current_state = STATE_READ_REG_START;
            break;
            
        case STATE_READ_DATA_START:
            if (i2c_read_async(MPU6050_ADDR, rx_buf, 14)) {
                current_state = STATE_READ_DATA_WAIT;
            }
            break;
        case STATE_READ_DATA_WAIT:
            if (status == I2C_SUCCESS) {
                current_state = STATE_READ_REG_START;
                process_data(rx_buf);
                return true;
            } else if (status == I2C_ERROR) {
                current_state = STATE_READ_REG_START;
            }
            break;
    }
    return false;
}

void imu_calibrate_begin(void) {
    is_calibrating = true;
    calib_count = 0;
    gyro_y_sum = 0;
}

bool imu_calibrate_busy(void) {
    return is_calibrating && (calib_count < 500);
}

void imu_calibrate_commit(void) {
    if (calib_count > 0) {
        gyro_y_offset = (int16_t)(gyro_y_sum / calib_count);
    }
    is_calibrating = false;
    angle_gyro = angle_acc;
}

float imu_get_tilt_angle(void) {
    return angle_gyro;
}
