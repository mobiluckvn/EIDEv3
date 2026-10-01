#ifndef MPU6050_H_
#define MPU6050_H_

#include <stdint.h>
#include <stdbool.h>

typedef struct {
    int16_t accel_x;
    int16_t accel_y;
    int16_t accel_z;
    int16_t gyro_x;
    int16_t gyro_y;
    int16_t gyro_z;
} mpu6050_raw_data_t;

typedef struct {
    float accel_x_g;
    float accel_y_g;
    float accel_z_g;
    float gyro_x_dps;
    float gyro_y_dps;
    float gyro_z_dps;
} mpu6050_data_t;

/* Khởi tạo cảm biến MPU6050 qua I2C */
bool mpu6050_init(void);

/* Lấy chuỗi chẩn đoán kết quả khởi tạo MPU6050 (Bảng 86) */
const char* mpu6050_get_init_diag(void);

/* Đọc toàn bộ 6 trục cảm biến thô */
bool mpu6050_read_raw(mpu6050_raw_data_t *raw);

/* Quy trình tự động hiệu chuẩn offset tĩnh con quay (FR-02) */
bool mpu6050_calibrate_gyro(void);

/* Khởi tạo quy trình hiệu chuẩn phi chặn */
void mpu6050_calib_reset(void);

/* Thực hiện lấy 1 mẫu hiệu chuẩn phi chặn, trả về true khi thành công và gán *out_done = true khi đủ 500 mẫu */
bool mpu6050_calib_step(bool *out_done);

/* Đọc dữ liệu đã trừ offset hiệu chuẩn và đổi sang đơn vị vật lý */
bool mpu6050_read_scaled(mpu6050_data_t *data);

/* Lấy giá trị bias con quay trục Y dạng thô (LSB) */
int16_t mpu6050_get_gyro_bias_y_raw(void);

#endif /* MPU6050_H_ */
