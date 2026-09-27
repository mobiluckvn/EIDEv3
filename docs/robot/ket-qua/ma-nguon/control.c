#include "control.h"

/**
 * @file control.c
 * @brief Hiện thực logic điều khiển cân bằng thuần túy.
 * Không chứa mã phụ thuộc phần cứng, không include avr/io.h.
 */

void control_init(control_state_t *state)
{
    if (!state) return;
    state->angle_pitch_mdeg = 0;
    state->gyro_pitch_rate  = 0;
    state->integral_accum   = 0;
    state->last_error       = 0;
}

void control_update_imu(control_state_t *state,
                        int16_t raw_acc_x,
                        int16_t raw_acc_z,
                        int16_t raw_gyro_y,
                        int16_t gyro_bias_y,
                        int16_t gyro_scale_lsb_per_dps,
                        uint16_t dt_ms)
{
    if (!state || dt_ms == 0) return;
    (void)raw_acc_x;

    /* Ánh xạ trục và chiều theo mục 8.3 và Bảng 32:
     * Trục trước–sau là trục Z, chiều s = -1 (đảo dấu Z).
     */
    int32_t acc_z_fwd = -(int32_t)raw_acc_z;

    /* Trừ độ lệch lắp đặt cân bằng (102 LSB theo mục 11.2) */
    int32_t acc_z_corr = acc_z_fwd - (int32_t)IMU_ACCEL_OFFSET_LSB;

    /* Tính góc nghiêng từ gia tốc kế ở vùng góc nhỏ:
     * theta_rad ≈ acc_z_corr / 8192.
     * Đổi ra millidegree: theta_mdeg ≈ acc_z_corr * 57296 / 8192 = acc_z_corr * 7162 / 1024
     */
    int32_t angle_acc_mdeg = (acc_z_corr * 7162) / 1024;

    /* Tính tốc độ góc pitch từ gyro Y (mdeg/s) */
    int32_t gyro_rate_raw = (int32_t)raw_gyro_y - (int32_t)gyro_bias_y;
    int32_t rate_mdeg_s = 0;
    if (gyro_scale_lsb_per_dps > 0) {
        rate_mdeg_s = (gyro_rate_raw * 1000) / (int32_t)gyro_scale_lsb_per_dps;
    }
    state->gyro_pitch_rate = rate_mdeg_s;

    /* Tích phân con quay góc */
    int32_t delta_angle_gyro = (rate_mdeg_s * (int32_t)dt_ms) / 1000;
    int32_t angle_pred = state->angle_pitch_mdeg + delta_angle_gyro;

    /* Lọc bù: 98% góc dự đoán từ gyro + 2% góc từ gia tốc kế */
    state->angle_pitch_mdeg = (angle_pred * 980 + angle_acc_mdeg * 20) / 1000;
}

int16_t control_calc_pid(control_state_t *state,
                         const pid_config_t *cfg,
                         uint16_t dt_ms)
{
    if (!state || !cfg || dt_ms == 0) return 0;

    /* Sai số góc so với điểm đặt cân bằng (mdeg) */
    int32_t error = state->angle_pitch_mdeg - cfg->target_mdeg;

    /* Khâu tỉ lệ P */
    int32_t p_term = (cfg->kp * error) / 1000;

    /* Khâu tích phân I kèm giới hạn chống bão hòa tích phân */
    state->integral_accum += (error * (int32_t)dt_ms) / 1000;
    if (state->integral_accum > cfg->max_integral) {
        state->integral_accum = cfg->max_integral;
    } else if (state->integral_accum < -cfg->max_integral) {
        state->integral_accum = -cfg->max_integral;
    }
    int32_t i_term = (cfg->ki * state->integral_accum) / 1000;

    /* Khâu vi phân D: dùng trực tiếp tốc độ góc đo từ con quay */
    int32_t d_term = (cfg->kd * state->gyro_pitch_rate) / 1000;

    /* Tổng hợp đầu ra điều khiển */
    int32_t output = p_term + i_term + d_term;

    /* Bão hòa đầu ra */
    if (output > cfg->max_output) {
        output = cfg->max_output;
    } else if (output < -cfg->max_output) {
        output = -cfg->max_output;
    }

    state->last_error = error;
    return (int16_t)output;
}

void control_throttle_to_steps(int16_t throttle_left,
                               int16_t throttle_right,
                               motor_step_cmd_t *cmd)
{
    if (!cmd) return;

    /* Bánh trái:
     * Theo mục 7.6: throttle = 0 là ĐỨNG IM (period_ticks = 0).
     * Khi chạy: period_ticks = |throttle| + 1 nhịp (mỗi nhịp 20 µs).
     * Theo mục 11.4 & Bảng 32: DIR đi tới là HIGH (true), lùi là LOW (false).
     */
    if (throttle_left == 0) {
        cmd->period_ticks_left = 0;
        cmd->dir_left = false;
    } else {
        int16_t abs_th = (throttle_left > 0) ? throttle_left : -throttle_left;
        cmd->period_ticks_left = (uint16_t)(abs_th + 1);
        cmd->dir_left = (throttle_left > 0) ? true : false;
    }

    /* Bánh phải:
     * Theo mục 7.6: throttle = 0 là ĐỨNG IM (period_ticks = 0).
     * Khi chạy: period_ticks = |throttle| + 1 nhịp (mỗi nhịp 20 µs).
     * Theo mục 11.4 & Bảng 32: DIR đi tới là LOW (false), lùi là HIGH (true).
     */
    if (throttle_right == 0) {
        cmd->period_ticks_right = 0;
        cmd->dir_right = false;
    } else {
        int16_t abs_th = (throttle_right > 0) ? throttle_right : -throttle_right;
        cmd->period_ticks_right = (uint16_t)(abs_th + 1);
        cmd->dir_right = (throttle_right > 0) ? false : true;
    }

    cmd->enabled = (cmd->period_ticks_left > 0 || cmd->period_ticks_right > 0);
}
