#include "control.h"
#include "config.h"
#include "motor.h"
#include <math.h>

static control_state_t g_state;

void control_init(void) {
    control_reset();
}

void control_reset(void) {
    g_state.angle_pitch = 0.0f;
    g_state.angle_pitch_accel = 0.0f;
    g_state.balance_target = 0.0f;
    g_state.pid_integral = 0.0f;
    g_state.last_output = 0.0f;
    g_state.motor_output_l = 0;
    g_state.motor_output_r = 0;
    g_state.is_balancing = false;
    g_state.is_fallen = false;
}

const control_state_t* control_get_state(void) {
    return &g_state;
}

void control_update_4ms(const mpu6050_raw_t *raw) {
    /* =====================================================================
     * 1. TÍNH GÓC NGHIÊNG TỪ GIA TỐC (THEO BẢNG 3.2: TRỤC TRƯỚC SAU LÀ ACCEL_Z)
     * ===================================================================== */
    int32_t accel_raw = (int32_t)raw->accel_z + FACT_SO_BU_GIA_TOC;

    if (accel_raw < FACT_ACCEL_MIN) {
        accel_raw = FACT_ACCEL_MIN;
    }
    if (accel_raw > FACT_ACCEL_MAX) {
        accel_raw = FACT_ACCEL_MAX;
    }

    float sin_val = (float)accel_raw / FACT_ACCEL_SCALE;
    if (sin_val < -1.0f) {
        sin_val = -1.0f;
    }
    if (sin_val > 1.0f) {
        sin_val = 1.0f;
    }
    float angle_accel = asinf(sin_val) * FACT_RAD_TO_DEG;
    g_state.angle_pitch_accel = angle_accel;

    /* =====================================================================
     * 2. TÍNH TỐC ĐỘ GÓC VÀ CẬP NHẬT GÓC CHẠY (THEO BẢNG 3.2: NGHIÊNG = GYRO_Y, XOAY = GYRO_X)
     * ===================================================================== */
    float gyro_pitch = (float)raw->gyro_y;
    float gyro_yaw   = (float)raw->gyro_x;

    g_state.angle_pitch += gyro_pitch * FACT_GYRO_PITCH_COEFF;
    g_state.angle_pitch -= gyro_yaw * FACT_GYRO_YAW_COEFF;

    /* =====================================================================
     * 3. BỘ LỌC BÙ (COMPLEMENTARY FILTER)
     * ===================================================================== */
    g_state.angle_pitch = g_state.angle_pitch * FACT_FILTER_GYRO + angle_accel * FACT_FILTER_ACCEL;

    /* =====================================================================
     * 4. KIỂM TRA NGƯỠNG ĐỔ
     * ===================================================================== */
    if (g_state.angle_pitch > FACT_FALL_ANGLE || g_state.angle_pitch < -FACT_FALL_ANGLE) {
        g_state.is_fallen = true;
        g_state.is_balancing = false;
        g_state.motor_output_l = 0;
        g_state.motor_output_r = 0;
        motor_stop();
        return;
    }

    /* =====================================================================
     * 5. KIỂM TRA ĐIỀU KIỆN BẬT GIỮ CÂN BẰNG
     * ===================================================================== */
    if (!g_state.is_balancing) {
        if (g_state.angle_pitch >= FACT_BALANCE_ANGLE_MIN && g_state.angle_pitch <= FACT_BALANCE_ANGLE_MAX) {
            g_state.is_balancing = true;
            g_state.is_fallen = false;
            g_state.pid_integral = 0.0f;
            g_state.last_output = 0.0f;
            motor_enable(true);
        } else {
            motor_stop();
            return;
        }
    }

    /* =====================================================================
     * 6. BỘ ĐIỀU KHIỂN PID VÀ PHẦN HÃM
     * ===================================================================== */
    float error = g_state.angle_pitch - g_state.balance_target;

    /* Phần hãm: Nếu đầu ra trước vượt ngưỡng thì cộng thêm phần hãm vào sai số */
    if (g_state.last_output > FACT_BRAKE_THRESHOLD) {
        error += g_state.last_output * FACT_BRAKE_COEFF;
    } else if (g_state.last_output < -FACT_BRAKE_THRESHOLD) {
        error += g_state.last_output * FACT_BRAKE_COEFF;
    }

    /* Khâu tỉ lệ P */
    float p_term = error * FACT_PID_KP;

    /* Khâu tích lũy I */
    g_state.pid_integral += error * FACT_PID_KI;
    if (g_state.pid_integral > FACT_INTEGRAL_CLAMP_MAX) {
        g_state.pid_integral = FACT_INTEGRAL_CLAMP_MAX;
    }
    if (g_state.pid_integral < FACT_INTEGRAL_CLAMP_MIN) {
        g_state.pid_integral = FACT_INTEGRAL_CLAMP_MIN;
    }

    /* Khâu vi phân D: Dựa trên tốc độ góc quy đổi từ con quay hồi chuyển */
    float d_term = (gyro_pitch / FACT_GYRO_SCALE) * FACT_PID_KD;

    /* Tổng hợp đầu ra điều khiển */
    float output = p_term + g_state.pid_integral + d_term;

    /* =====================================================================
     * 7. VÙNG CHẾT (DEADZONE)
     * ===================================================================== */
    if (output >= FACT_DEADZONE_MIN && output <= FACT_DEADZONE_MAX) {
        output = 0.0f;
    }

    /* =====================================================================
     * 8. BƯỚC TỰ HỌC ĐIỂM CÂN BẰNG
     * ===================================================================== */
    if (output > 0.0f) {
        g_state.balance_target -= FACT_AUTO_BALANCE_STEP;
    } else if (output < 0.0f) {
        g_state.balance_target += FACT_AUTO_BALANCE_STEP;
    }

    /* Lưu đầu ra cho vòng kế tiếp */
    g_state.last_output = output;

    /* =====================================================================
     * 9. TRUYỀN TỐC ĐỘ XUỐNG TẦNG 1 (ĐỘNG CƠ)
     * ===================================================================== */
    g_state.motor_output_l = (int16_t)output;
    g_state.motor_output_r = (int16_t)output;
    motor_set_speeds(g_state.motor_output_l, g_state.motor_output_r);
}
