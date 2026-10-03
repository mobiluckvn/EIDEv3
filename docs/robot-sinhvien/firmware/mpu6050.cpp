#include "mpu6050.h"
#include "config.h"
#include <Arduino.h>
#include <Wire.h>

static void mpu6050_write_byte(uint8_t reg, uint8_t val) {
    Wire.beginTransmission(MPU6050_I2C_ADDR);
    Wire.write(reg);
    Wire.write(val);
    Wire.endTransmission();
}

bool mpu6050_init(void) {
    Wire.begin();
    TWBR = FACT_TWBR_VAL; /* Bảng 16: TWBR = 12 để đạt tốc độ TWI 400 kHz */

    /* Đánh thức MPU-6050 (thoát chế độ ngủ) */
    mpu6050_write_byte(MPU6050_REG_PWR_MGMT_1, 0x00);
    delay(10);

    /* Cấu hình bộ lọc số thông thấp DLPF (42 Hz) */
    mpu6050_write_byte(MPU6050_REG_CONFIG, 0x03);

    /* Cấu hình Gyro: thang đo +-250 deg/s (ứng với FACT_GYRO_SCALE = 131) */
    mpu6050_write_byte(MPU6050_REG_GYRO_CONFIG, 0x00);

    /* Cấu hình Accel: thang đo +-4 g (ứng với FACT_ACCEL_SCALE = 8192) */
    mpu6050_write_byte(MPU6050_REG_ACCEL_CONFIG, 0x08);

    /* Kiểm tra cảm biến có phản hồi */
    Wire.beginTransmission(MPU6050_I2C_ADDR);
    Wire.write(MPU6050_REG_WHO_AM_I);
    if (Wire.endTransmission() != 0) {
        return false;
    }

    Wire.requestFrom((uint8_t)MPU6050_I2C_ADDR, (uint8_t)1);
    if (Wire.available()) {
        uint8_t who = Wire.read();
        return (who == 0x68 || who == 0x70 || who == 0x72);
    }

    return false;
}

bool mpu6050_read_raw(mpu6050_raw_t *raw) {
    Wire.beginTransmission(MPU6050_I2C_ADDR);
    Wire.write(MPU6050_REG_ACCEL_XOUT_H);
    if (Wire.endTransmission() != 0) {
        return false;
    }

    Wire.requestFrom((uint8_t)MPU6050_I2C_ADDR, (uint8_t)14);
    if (Wire.available() < 14) {
        return false;
    }

    raw->accel_x = ((int16_t)Wire.read() << 8) | Wire.read();
    raw->accel_y = ((int16_t)Wire.read() << 8) | Wire.read();
    raw->accel_z = ((int16_t)Wire.read() << 8) | Wire.read();
    (void)(((int16_t)Wire.read() << 8) | Wire.read()); /* Bỏ qua nhiệt độ */
    raw->gyro_x  = ((int16_t)Wire.read() << 8) | Wire.read();
    raw->gyro_y  = ((int16_t)Wire.read() << 8) | Wire.read();
    raw->gyro_z  = ((int16_t)Wire.read() << 8) | Wire.read();

    return true;
}
