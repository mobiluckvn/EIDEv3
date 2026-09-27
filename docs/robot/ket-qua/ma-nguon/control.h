#ifndef FIRMWARE_CONTROL_H_
#define FIRMWARE_CONTROL_H_

#include <stdint.h>
#include <stdbool.h>

/**
 * @file control.h
 * @brief Logic điều khiển thuần túy cho robot 2 bánh tự cân bằng MOBILUCK.
 * Không phụ thuộc phần cứng vi điều khiển, không include avr/io.h.
 * Dùng số nguyên (fixed-point) cho đường chạy nhanh.
 */

/* Hằng số hiệu chuẩn gia tốc kế từ tài liệu (Fact f-3a843e07a6 và f-66ea36381e) */
#define IMU_ACCEL_OFFSET_LSB        102   /* Điểm cân bằng cơ khí (LSB) */
#define IMU_ACCEL_SCALE_LSB         8192  /* Độ nhạy gia tốc kế ở dải ±4 g */

/* Cấu trúc tham số cấu hình bộ điều khiển PID */
typedef struct {
    int32_t kp;           /* Hệ số tỉ lệ P (tỉ lệ 1/1000) */
    int32_t ki;           /* Hệ số tích phân I (tỉ lệ 1/1000) */
    int32_t kd;           /* Hệ số vi phân D (tỉ lệ 1/1000) */
    int32_t target_mdeg;  /* Điểm đặt góc cân bằng (millidegree) */
    int32_t max_integral; /* Giới hạn chống bão hòa tích phân */
    int32_t max_output;   /* Giới hạn đầu ra PID */
} pid_config_t;

/* Cấu trúc trạng thái bộ lọc góc và vòng điều khiển */
typedef struct {
    int32_t angle_pitch_mdeg; /* Góc nghiêng pitch ước lượng (millidegree) */
    int32_t gyro_pitch_rate;  /* Vận tốc góc pitch (mdeg/s) */
    int32_t integral_accum;   /* Bộ tích phân sai số góc */
    int32_t last_error;       /* Sai số góc vòng trước */
} control_state_t;

/* Kết quả điều khiển xung động cơ cấp cho ISR tầng 1 */
typedef struct {
    uint16_t period_ticks_left;  /* Số nhịp 20 µs giữa hai xung bánh trái (0 = dừng) */
    uint16_t period_ticks_right; /* Số nhịp 20 µs giữa hai xung bánh phải (0 = dừng) */
    bool dir_left;               /* Mức logic chân DIR bánh trái */
    bool dir_right;              /* Mức logic chân DIR bánh phải */
    bool enabled;                /* Trạng thái phát xung (false = dừng) */
} motor_step_cmd_t;

#ifdef __cplusplus
extern "C" {
#endif

/* Khởi tạo trạng thái bộ điều khiển */
void control_init(control_state_t *state);

/* Cập nhật góc bằng bộ lọc bù từ dữ liệu thô IMU (chạy chu kỳ dt_ms) */
void control_update_imu(control_state_t *state,
                        int16_t raw_acc_x,
                        int16_t raw_acc_z,
                        int16_t raw_gyro_y,
                        int16_t gyro_bias_y,
                        int16_t gyro_scale_lsb_per_dps,
                        uint16_t dt_ms);

/* Tính toán PID giữ thăng bằng từ góc ước lượng */
int16_t control_calc_pid(control_state_t *state,
                         const pid_config_t *cfg,
                         uint16_t dt_ms);

/* Quy đổi throttle sang chu kỳ xung bước (số nhịp 20 µs) và mức DIR theo Mục 7.6 */
void control_throttle_to_steps(int16_t throttle_left,
                               int16_t throttle_right,
                               motor_step_cmd_t *cmd);

#ifdef __cplusplus
}
#endif

#endif /* FIRMWARE_CONTROL_H_ */
