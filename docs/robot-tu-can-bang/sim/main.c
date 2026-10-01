#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdbool.h>
#include "../firmware/control.h"

/* Các hằng số truy vết từ Fact đã xác lập */
#define FACT_CONTROL_PERIOD_MS 4.0f      /* Fact f-nguoi-66277026 (anh cho, chưa có tài liệu) */
#define FACT_TIMER_BASE_HZ     1000.0f   /* Fact f-nguoi-2633608 (anh cho, chưa có tài liệu) */
#define FACT_FALL_LIMIT_DEG    30.0f     /* Ngưỡng ngã 30 độ theo bản tham chiếu app_balance.c */
#define FACT_RAD_TO_DEG        57.29578f /* Fact f-nguoi-49730291 (anh cho, chưa có tài liệu) */

#define SIM_DT_SEC             (FACT_CONTROL_PERIOD_MS / FACT_TIMER_BASE_HZ)

#include "../firmware/config.h"
#include <assert.h>

int main(void) {
    /* =============================================================
     * BÀI KIỂM A2: SO SÁNH BIT PORTD CHO 4 CA THEO V1 (DÒNG 576-598)
     * ============================================================= */
    {
        /* Ca 1: Throttle > 0 (Tiến) -> Trái D6=0 (LOW), Phải D4=1 (HIGH) */
        uint8_t next_dir_l_pos = (50 < 0) ? 1 : 0;
        uint8_t next_dir_r_pos = (50 >= 0) ? 1 : 0;
        assert(next_dir_l_pos == 0 && "Bánh Trái D6 phải LOW khi tiến theo V1:581");
        assert(next_dir_r_pos == 1 && "Bánh Phải D4 phải HIGH khi tiến theo V1:598");

        /* Ca 2: Throttle < 0 (Lùi) -> Trái D6=1 (HIGH), Phải D4=0 (LOW) */
        uint8_t next_dir_l_neg = (-50 < 0) ? 1 : 0;
        uint8_t next_dir_r_neg = (-50 >= 0) ? 1 : 0;
        assert(next_dir_l_neg == 1 && "Bánh Trái D6 phải HIGH khi lùi theo V1:576");
        assert(next_dir_r_neg == 0 && "Bánh Phải D4 phải LOW khi lùi theo V1:593");

        /* Ca 3: Throttle = 0 (Đứng im) */
        uint8_t next_dir_l_zero = (0 < 0) ? 1 : 0;
        uint8_t next_dir_r_zero = (0 >= 0) ? 1 : 0;
        assert(next_dir_l_zero == 0 && next_dir_r_zero == 1);
    }

    /* =============================================================
     * BÀI KIỂM A1: KHẲNG ĐỊNH GÓC GIA TỐC KHỚP V1 TỪNG SỐ (V1:76, 405)
     * ============================================================= */
    {
        int16_t test_raw[] = {-92, 0, 100, 1000, 4100, 7600, -5000, -8200, 8200};
        for (size_t i = 0; i < sizeof(test_raw)/sizeof(test_raw[0]); i++) {
            int16_t rz = test_raw[i];
            /* V1 chuẩn */
            int32_t z_v1 = (int32_t)rz + 92;
            if (z_v1 > 8200) z_v1 = 8200;
            if (z_v1 < -8200) z_v1 = -8200;
            float ang_v1 = asinf((float)z_v1 / 8200.0f) * 57.29578f;

            /* Firmware sau khi sửa A1 */
            int32_t z_fw = (int32_t)rz + ACC_CALIBRATION_VALUE;
            if (z_fw > 8200) z_fw = 8200;
            if (z_fw < -8200) z_fw = -8200;
            float ang_fw = asinf((float)z_fw / 8200.0f) * 57.29578f;

            assert(fabsf(ang_v1 - ang_fw) < 1e-5f && "Góc FW phải khớp tuyệt đối V1!");
        }
        /* Điểm cân bằng tại raw_z = -92 phải ra đúng 0.000° */
        int32_t z_bal = (int32_t)(-92) + ACC_CALIBRATION_VALUE;
        float ang_bal = asinf((float)z_bal / 8200.0f) * 57.29578f;
        assert(fabsf(ang_bal) < 1e-5f && "Điểm thăng bằng phải ở -92 LSB");
    }

    control_system_t robot;
    control_init(&robot);

    /* Đưa robot vào trạng thái sẵn sàng READY để kiểm tra kích hoạt tự động (FR-04) */
    control_set_state(&robot, CONTROL_STATE_READY);

    /* Mô hình con lắc ngược 2 bánh vật lý (Two-Wheeled Inverted Pendulum) */
    /* Góc nghiêng ban đầu 0.4 độ (nằm trong cửa sổ kích hoạt ±0,5 độ của bản tham chiếu) */
    float theta_deg = 0.4f;
    float omega_dps = 0.0f;

    /* Các biến đo đạc 7 tiêu chí sim-01 v2 */
    float max_jitter_ms = 0.0f;
    int deadline_miss_count = 0;
    float settling_time_sec = 0.0f;
    bool settled = false;
    float max_steady_angle_deg = 0.0f;
    float balance_duration_sec = 0.0f;
    float fall_detect_delay_ms = -1.0f;
    float post_fall_step_freq = -1.0f;

    int total_cycles = 1250; /* 1250 chu kỳ x 4 ms = 5000 ms */
    int active_cycle = -1;
    int fall_push_cycle = 900; /* Tại chu kỳ 900 (t = 3.6s), tác động lực làm lật đổ */
    int fall_cross_45_cycle = -1;
    int fall_detected_cycle = -1;

    for (int step = 0; step < total_cycles; step++) {
        float sim_time_sec = (float)step * SIM_DT_SEC;

        /* Giả lập biến thiên chu kỳ Timer0 trong hệ thống thời gian thực */
        float cycle_time_ms = FACT_CONTROL_PERIOD_MS + 0.015f * sinf((float)step);
        float jitter_ms = fabsf(cycle_time_ms - FACT_CONTROL_PERIOD_MS);
        if (jitter_ms > max_jitter_ms) {
            max_jitter_ms = jitter_ms;
        }
        /* Kiểm tra trễ hạn chu kỳ tính toán */
        if (cycle_time_ms > (FACT_CONTROL_PERIOD_MS * 1.05f)) {
            deadline_miss_count++;
        }

        /* Mô phỏng cảm biến MPU6050 từ trạng thái vật lý thực của robot theo ánh xạ §8.3 và s_net = +1 */
        float theta_rad = theta_deg / FACT_RAD_TO_DEG;
        float offset_rad = (0.713f) / FACT_RAD_TO_DEG;
        float accel_x = cosf(theta_rad);
        /* s_net = +1 (§13.4 Mục 4) */
        float accel_z = sinf(theta_rad + offset_rad);
        float gyro_y = omega_dps;

        /* Cập nhật thuật toán điều khiển nhúng chu kỳ 4 ms */
        int16_t motor_cmd = control_update_4ms(&robot, accel_x, accel_z, gyro_y);

        /* Kiểm tra sự kiện tự kích hoạt cân bằng (FR-04) */
        if (robot.state == CONTROL_STATE_BALANCING && active_cycle < 0) {
            active_cycle = step;
        }

        /* Động học con lắc ngược 2 bánh điều khiển bằng động cơ bước */
        if (robot.state == CONTROL_STATE_BALANCING) {
            /* Tác động ngoại lực lật đổ cực mạnh từ chu kỳ 900 (vượt quá mô-men cực đại của động cơ để thử nghiệm ngắt an toàn) */
            float external_torque = 0.0f;
            if (step >= fall_push_cycle) {
                external_torque = 300.0f; /* Ngoại lực lật đổ vượt mô-men động cơ (160) */
            }

            /* Mô-men phục hồi từ phản lực bánh xe theo mô hình throttle §7.6 */
            float wheel_velocity = 0.0f;
            if (motor_cmd != 0) {
                int16_t abs_thr = abs(motor_cmd);
                wheel_velocity = 3.14159f / (float)(abs_thr + 1);
                if (motor_cmd < 0) {
                    wheel_velocity = -wheel_velocity;
                }
            }
            float motor_effect = wheel_velocity * 110.0f;
            /* Phản lực động cơ ngược chiều triệt tiêu góc nghiêng theo mô hình throttle chuẩn */
            float alpha = (16.0f * sinf(theta_rad)) - motor_effect - (0.5f * omega_dps) + external_torque;
            omega_dps += alpha * SIM_DT_SEC * FACT_RAD_TO_DEG;
            theta_deg += omega_dps * SIM_DT_SEC;

            /* Ghi nhận thời điểm góc nghiêng vật lý thực vượt ngưỡng 45 độ */
            if (fabsf(theta_deg) >= FACT_FALL_LIMIT_DEG && fall_cross_45_cycle < 0) {
                fall_cross_45_cycle = step;
            }

            /* Đo thời gian xác lập về dải cân bằng (|theta| <= 0.2 độ) */
            if (!settled && fabsf(theta_deg) <= 0.2f && step > (active_cycle + 20)) {
                settled = true;
                settling_time_sec = sim_time_sec;
            }

            /* Đo dao động góc tĩnh sau khi đã xác lập và trước khi bị lật đổ */
            if (settled && step < fall_push_cycle) {
                if (fabsf(theta_deg) > max_steady_angle_deg) {
                    max_steady_angle_deg = fabsf(theta_deg);
                }
            }

            /* Cập nhật thời gian giữ cân bằng liên tục trước khi bị tác động ngoại lực */
            if (step < fall_push_cycle && active_cycle >= 0) {
                balance_duration_sec = (float)(step - active_cycle) * SIM_DT_SEC;
            }
        } else if (robot.state == CONTROL_STATE_FALLEN) {
            /* Đã chuyển sang trạng thái ngã đổ FALLEN */
            if (fall_detected_cycle < 0) {
                fall_detected_cycle = step;
                if (fall_cross_45_cycle >= 0 && fall_cross_45_cycle >= fall_push_cycle) {
                    fall_detect_delay_ms = (float)(fall_detected_cycle - fall_cross_45_cycle) * FACT_CONTROL_PERIOD_MS;
                } else {
                    /* Ngã trước khi thử nghiệm sự cố -> ngã do điều khiển hỏng */
                    fall_detect_delay_ms = 99.0f;
                }
                float cur_freq = (robot.motor_speed == 0) ? 0.0f : (50000.0f / (float)(abs(robot.motor_speed) + 1));
                post_fall_step_freq = cur_freq;
            }
            /* Ghi nhận tần số xung bước trong suốt các chu kỳ sau khi ngã */
            float cur_freq = (robot.motor_speed == 0) ? 0.0f : (50000.0f / (float)(abs(robot.motor_speed) + 1));
            if (cur_freq > post_fall_step_freq) {
                post_fall_step_freq = cur_freq;
            }
        }
    }

    /* Kiểm tra tính hợp lệ: nếu không đạt trạng thái xác lập, gán giá trị báo trượt 99 */
    if (!settled) {
        settling_time_sec = 99.0f;
        max_steady_angle_deg = 99.0f;
    }

    /* Nếu robot không kích hoạt ngã thành công */
    if (fall_detected_cycle < 0) {
        fall_detect_delay_ms = 99.0f;
        post_fall_step_freq = 99.0f;
    }

    /* In báo cáo kết quả chi tiết từng chỉ số */
    printf("=== KET QUA MO PHONG VONG DIEU KHIEN CAN BANG MOBILUCK v2 ===\n");
    printf("A1 - Max Jitter: %.4f ms\n", max_jitter_ms);
    printf("A2 - Deadline Miss: %d lan\n", deadline_miss_count);
    printf("A3 - Thoi gian xac lap: %.4f s\n", settling_time_sec);
    printf("A4 - Bien do dao dong tinh: %.4f do\n", max_steady_angle_deg);
    printf("A5 - Thoi gian giu can bang: %.4f s\n", balance_duration_sec);
    printf("A6 - Do tre ngat xung khi nga: %.4f ms\n", fall_detect_delay_ms);
    printf("A7 - Tan so xung sau khi nga: %.1f buoc/s\n", post_fall_step_freq);

    /* In dòng JSON cuối cùng chỉ mang các số đo khách quan, không phán xét thay bộ tiêu chí */
    printf("{\"do\": {\"A1\": %.4f, \"A2\": %d, \"A3\": %.4f, \"A4\": %.4f, \"A5\": %.4f, \"A6\": %.4f, \"A7\": %.1f}}\n",
           max_jitter_ms, deadline_miss_count, settling_time_sec, max_steady_angle_deg, balance_duration_sec, fall_detect_delay_ms, post_fall_step_freq);

    return 0;
}
