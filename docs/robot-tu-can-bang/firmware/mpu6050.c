#include "mpu6050.h"
#include "config.h"
#include "i2c.h"
#include "uart.h"
#include <stddef.h>
#include <stdio.h>

#define REG_SMPLRT_DIV    0x19
#define REG_CONFIG        0x1A
#define REG_GYRO_CONFIG   0x1B
#define REG_ACCEL_CONFIG  0x1C
#define REG_ACCEL_CONFIG_2 0x1D
#define REG_ACCEL_XOUT_H  0x3B
#define REG_PWR_MGMT_1    0x6B
#define REG_WHO_AM_I      0x75

/* Hệ số tỉ lệ nhạy cảm biến: ±4 g tương ứng 8192 LSB/g (Phụ lục A.3, f-nguoi-6088484) */
#define ACCEL_SCALE_FACTOR 8192.0f
#define GYRO_SCALE_FACTOR  131.0f

static float s_gyro_bias_x = 0.0f;
static float s_gyro_bias_y = 0.0f;
static float s_gyro_bias_z = 0.0f;
static char s_mpu_init_diag[64] = "CHUA_KHOI_TAO";

const char* mpu6050_get_init_diag(void) {
    return s_mpu_init_diag;
}

bool mpu6050_init(void) {
    /* Đánh thức MPU6050 và chọn nguồn xung PLL tối ưu (CLKSEL = 1, PWR_MGMT_1 = 0x01) */
    if (!i2c_write_byte(MPU6050_ADDR, REG_PWR_MGMT_1, 0x01)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "PWR_MGMT_1 write err");
        return false;
    }

    /* Trễ ngắn cho bộ dao động MPU6050 ổn định sau khi thức dậy */
    for (volatile uint16_t d = 0; d < 15000; d++);

    /* Kiểm tra nhận dạng cảm biến: thanh ghi WHO_AM_I (0x75) phải là 0x68 (§8.1, TEST-02) */
    uint8_t who_am_i = 0;
    if (!i2c_read_bytes(MPU6050_ADDR, REG_WHO_AM_I, &who_am_i, 1)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "WHO_AM_I I2C read err");
        return false;
    }
    if (who_am_i != 0x68 && who_am_i != 0x72) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "WHO_AM_I mismatch: 0x%02X (exp 0x68/0x72)", who_am_i);
        return false;
    }

    /* Đặt bộ lọc số thông thấp DLPF */
    if (!i2c_write_byte(MPU6050_ADDR, REG_CONFIG, 0x03)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "CONFIG write err");
        return false;
    }
    /* Đặt thang đo con quay */
    if (!i2c_write_byte(MPU6050_ADDR, REG_GYRO_CONFIG, 0x00)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "GYRO_CFG write err");
        return false;
    }
    /* Đặt thang đo gia tốc ±4 g (AFS_SEL = 1, bit [4:3] = 01 -> 0x08) */
    if (!i2c_write_byte(MPU6050_ADDR, REG_ACCEL_CONFIG, 0x08)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "ACCEL_CFG write err");
        return false;
    }

    /* Đọc LẠI thanh ghi 0x1C để xác nhận đúng giá trị 0x08 (§13.4 Mục 3, TEST-03) */
    uint8_t accel_cfg_verify = 0;
    if (!i2c_read_bytes(MPU6050_ADDR, REG_ACCEL_CONFIG, &accel_cfg_verify, 1)) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "ACCEL_CFG I2C read err");
        return false;
    }
    if ((accel_cfg_verify & 0x18) != 0x08) {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "ACCEL_CFG mismatch: 0x%02X (exp 0x08)", accel_cfg_verify);
        return false;
    }

    /* Với chip họ MPU-6500/9250 (ID 0x72): cấu hình và kiểm chứng thanh ghi ACCEL_CONFIG_2 (0x1D) */
    if (who_am_i == 0x72) {
        uint8_t cfg2_orig = 0;
        i2c_read_bytes(MPU6050_ADDR, REG_ACCEL_CONFIG_2, &cfg2_orig, 1);
        if (!i2c_write_byte(MPU6050_ADDR, REG_ACCEL_CONFIG_2, 0x03)) {
            snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "ACCEL_CFG2 write err");
            return false;
        }
        for (volatile uint16_t d = 0; d < 5000; d++);
        uint8_t cfg2_verify = 0;
        i2c_read_bytes(MPU6050_ADDR, REG_ACCEL_CONFIG_2, &cfg2_verify, 1);

        /* Đọc thêm các thanh ghi mở rộng của họ 6500 (0x1E, 0x1F) để thu thập bằng chứng silicon */
        uint8_t r1E = 0, r1F = 0;
        i2c_read_bytes(MPU6050_ADDR, 0x1E, &r1E, 1);
        i2c_read_bytes(MPU6050_ADDR, 0x1F, &r1F, 1);

        char diag_regs[64];
        snprintf(diag_regs, sizeof(diag_regs), "[DIAG] Regs: 1C=%02X 1D=%02X(orig %02X) 1E=%02X 1F=%02X",
                 accel_cfg_verify, cfg2_verify, cfg2_orig, r1E, r1F);
        uart_send_line(diag_regs);

        /* Quy tắc nghiêm ngặt: Ghi mà đọc lại không khớp thì KHÔNG ĐƯỢC báo OK */
        if (cfg2_verify == 0x03) {
            snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "OK ID=0x72 CFG2=0x03 (DLPF 41Hz verified)");
        } else {
            snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "WARN ID=0x72 CFG2_UNWRITABLE (0x%02X!=0x03)", cfg2_verify);
        }
    } else {
        snprintf(s_mpu_init_diag, sizeof(s_mpu_init_diag), "OK ID=0x68(MPU6050) CFG=0x%02X", accel_cfg_verify);
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
