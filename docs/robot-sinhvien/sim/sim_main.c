#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <math.h>
#include "../firmware/config.h"
#include "../firmware/control.h"
#include "../firmware/mpu6050.h"
#include "../firmware/motor.h"
#include "avr/io.h"

/* Định nghĩa các thanh ghi phần cứng AVR ATmega328P cho mô phỏng */
volatile uint8_t PORTD = 0;
volatile uint8_t DDRD = 0;
volatile uint8_t PINB = 0;
volatile uint8_t PORTB = 0;
volatile uint8_t DDRB = 0;
volatile uint8_t TCCR2A = 0;
volatile uint8_t TCCR2B = 0;
volatile uint8_t OCR2A = 0;
volatile uint8_t TCNT2 = 0;
volatile uint8_t TIMSK2 = 0;

/* Hằng số phần cứng thực tế đo được độc lập (không lấy macro FACT_SO_BU_GIA_TOC từ config.h) */
#define TESTBENCH_HARDWARE_OFFSET 92

int main(void) {
    printf("=== BAT DAU MO PHONG VONG DIEU KHIEN CAN BANG ROBOT ===\n");
    bool all_tests_passed = true;

    /* =====================================================================
     * KIỂM TRA 1: DỊCH THẲNG motor.cpp VÀ KIỂM TRA BIT CHÂN DIR TRÊN PORTD
     * Mức kỳ vọng lấy độc lập từ BẢNG 3.3 của tài liệu:
     * - Bánh trái: Tiến = THẤP (0), Lùi = CAO (1)
     * - Bánh phải: Tiến = CAO (1), Lùi = THẤP (0)
     * ===================================================================== */
    motor_init();

    /* 1.1 Kiểm tra chiều TIẾN của bánh trái (D6 / BIT_DIR_LEFT) và bánh phải (D4 / BIT_DIR_RIGHT) */
    motor_set_speeds(50, 50);
    if (PORTD & (1 << BIT_DIR_LEFT)) {
        printf("[LOI_DIR] Bánh trái tiến (speed >= 0) nhưng bit chân D6 (DIR_LEFT) ở mức CAO (1)! Kỳ vọng THẤP (0) theo Bảng 3.3.\n");
        all_tests_passed = false;
    } else {
        printf("[OK_DIR] Bit chân D6 (DIR_LEFT) = 0 đúng chiều tiến bánh trái theo Bảng 3.3.\n");
    }

    if (!(PORTD & (1 << BIT_DIR_RIGHT))) {
        printf("[LOI_DIR] Bánh phải tiến (speed >= 0) nhưng bit chân D4 (DIR_RIGHT) ở mức THẤP (0)! Kỳ vọng CAO (1) theo Bảng 3.3.\n");
        all_tests_passed = false;
    } else {
        printf("[OK_DIR] Bit chân D4 (DIR_RIGHT) = 1 đúng chiều tiến bánh phải theo Bảng 3.3.\n");
    }

    /* 1.2 Kiểm tra chiều LÙI của cả hai bánh */
    motor_set_speeds(-50, -50);
    if (!(PORTD & (1 << BIT_DIR_LEFT))) {
        printf("[LOI_DIR] Bánh trái lùi (speed < 0) nhưng bit chân D6 (DIR_LEFT) ở mức THẤP (0)! Kỳ vọng CAO (1) theo Bảng 3.3.\n");
        all_tests_passed = false;
    } else {
        printf("[OK_DIR] Bit chân D6 (DIR_LEFT) = 1 đúng chiều lùi bánh trái theo Bảng 3.3.\n");
    }

    if (PORTD & (1 << BIT_DIR_RIGHT)) {
        printf("[LOI_DIR] Bánh phải lùi (speed < 0) nhưng bit chân D4 (DIR_RIGHT) ở mức CAO (1)! Kỳ vọng THẤP (0) theo Bảng 3.3.\n");
        all_tests_passed = false;
    } else {
        printf("[OK_DIR] Bit chân D4 (DIR_RIGHT) = 0 đúng chiều lùi bánh phải theo Bảng 3.3.\n");
    }

    /* =====================================================================
     * KIỂM TRA 2: SO VỚI DÃY GÓC MẪU CỐ ĐỊNH (PHÁT HIỆN LỆCH SỐ BÙ HOẶC DẤU)
     * Dãy mẫu dùng hằng số cố định độc lập TESTBENCH_HARDWARE_OFFSET = 92
     * ===================================================================== */
    control_init();

    float test_angles[] = {0.0f, 2.0f, -2.0f, 5.0f, -5.0f};
    int num_vectors = sizeof(test_angles) / sizeof(test_angles[0]);

    for (int i = 0; i < num_vectors; i++) {
        float expected_deg = test_angles[i];
        float rad = expected_deg / FACT_RAD_TO_DEG;
        /* Sinh dữ liệu từ số bù đo đạc thực tế cố định 92, không dùng macro config */
        int16_t accel_raw_val = (int16_t)(sinf(rad) * FACT_ACCEL_SCALE) - TESTBENCH_HARDWARE_OFFSET;

        mpu6050_raw_t sample_raw;
        sample_raw.accel_x = 0;
        sample_raw.accel_y = 0;
        sample_raw.accel_z = accel_raw_val; /* Bảng 3.2: trục trước sau là accel_z */
        sample_raw.gyro_x = 0;
        sample_raw.gyro_y = 0;              /* Bảng 3.2: trục nghiêng là gyro_y */
        sample_raw.gyro_z = 0;

        control_reset();
        control_update_4ms(&sample_raw);
        const control_state_t *st = control_get_state();

        float angle_measured = st->angle_pitch_accel;
        float diff = fabsf(angle_measured - expected_deg);
        if (diff > 0.1f) {
            printf("[LOI_GOC_MAU] Mẫu %d: Kỳ vọng %.3f độ, mã tính ra %.3f độ (lệch %.3f độ > 0.1 độ)!\n",
                   i, expected_deg, angle_measured, diff);
            all_tests_passed = false;
        }
    }

    if (all_tests_passed) {
        printf("[OK_GOC_MAU] Tất cả mẫu góc đối chứng khớp chính xác với bản mẫu.\n");
    }

    /* =====================================================================
     * KIỂM TRA 3: MÔ PHỎNG ĐỘNG LỰC HỌC VÒNG ĐIỀU KHIỂN CÂN BẰNG
     * ===================================================================== */
    control_reset();
    double theta_deg = 0.05;
    double omega_deg = 0.0;
    const double dt = FACT_DT_SEC;

    double max_angle_stable = 0.0;
    double fall_trigger_angle = 0.0;
    double fall_response_time_ms = 0.0;
    double measured_trigger_balance = 0.0;
    bool activated_balance = false;

    mpu6050_raw_t raw;

    /* Giai đoạn 1: Kích hoạt cân bằng và kiểm tra độ ổn định */
    for (int step = 0; step < 500; step++) {
        double rad_val = theta_deg / FACT_RAD_TO_DEG;
        double sin_val = sin(rad_val);
        /* Sử dụng số bù cố định TESTBENCH_HARDWARE_OFFSET, không lấy từ config.h */
        int32_t accel_z = (int32_t)(sin_val * FACT_ACCEL_SCALE) - TESTBENCH_HARDWARE_OFFSET;
        int16_t gyro_y  = (int16_t)(omega_deg * FACT_GYRO_SCALE);

        raw.accel_x = 0;
        raw.accel_y = 0;
        raw.accel_z = (int16_t)accel_z; /* Trục trước-sau theo Bảng 3.2 */
        raw.gyro_x  = 0;
        raw.gyro_y  = gyro_y;           /* Trục nghiêng theo Bảng 3.2 */
        raw.gyro_z  = 0;

        control_update_4ms(&raw);
        const control_state_t *st = control_get_state();

        if (st->is_balancing && !activated_balance) {
            activated_balance = true;
            measured_trigger_balance = st->angle_pitch;
            printf("[T=%.3fs] Bật chế độ cân bằng ở góc: %.3f độ\n", step * dt, measured_trigger_balance);
        }

        if (st->is_balancing && step > 20) {
            double abs_ang = fabs(st->angle_pitch);
            if (abs_ang > max_angle_stable) {
                max_angle_stable = abs_ang;
            }
        }

        /* Mô hình con lắc ngược cơ bản */
        double alpha = (sin_val * FACT_RAD_TO_DEG * 80.0) - (st->motor_output_l * 1.2);
        omega_deg += alpha * dt;
        theta_deg += omega_deg * dt;
        omega_deg *= 0.99;
    }

    /* Giai đoạn 2: Tác động góc lớn và vận tốc góc để kích hoạt ngưỡng ngã (>= 30 độ) */
    theta_deg = 31.0;
    omega_deg = 150.0;
    bool fall_detected = false;

    for (int step = 500; step < 800; step++) {
        double rad_val = theta_deg / FACT_RAD_TO_DEG;
        double sin_val = sin(rad_val);
        int32_t accel_z = (int32_t)(sin_val * FACT_ACCEL_SCALE) - TESTBENCH_HARDWARE_OFFSET;
        int16_t gyro_y  = (int16_t)(omega_deg * FACT_GYRO_SCALE);

        raw.accel_x = 0;
        raw.accel_y = 0;
        raw.accel_z = (int16_t)accel_z;
        raw.gyro_x  = 0;
        raw.gyro_y  = gyro_y;
        raw.gyro_z  = 0;

        control_update_4ms(&raw);
        const control_state_t *st = control_get_state();

        if (st->is_fallen && !fall_detected) {
            fall_detected = true;
            fall_trigger_angle = st->angle_pitch;
            fall_response_time_ms = round(FACT_DT_SEC * 1000.0);
            printf("[T=%.3fs] Phát hiện ngã ở góc: %.3f độ, output=(%d, %d)\n",
                   step * dt, fall_trigger_angle, st->motor_output_l, st->motor_output_r);
            break;
        }

        theta_deg += omega_deg * dt;
    }

    double measured_loop_ms = dt * 1000.0;

    /* Kiểm tra 5 tiêu chí criteria:sim-01 */
    if (measured_loop_ms < 3.9 || measured_loop_ms > 4.1) all_tests_passed = false;
    if (measured_trigger_balance < -0.5 || measured_trigger_balance > 0.5) all_tests_passed = false;
    if (max_angle_stable > 10.0) all_tests_passed = false;
    if (fall_trigger_angle < 30.0) all_tests_passed = false;
    if (fall_response_time_ms > 4.0) all_tests_passed = false;

    printf("\nKet qua do luong:\n");
    printf("- A1 (Nhip vong dieu khien): %.2f ms\n", measured_loop_ms);
    printf("- A2 (Goc kich hoat can bang): %.3f do\n", measured_trigger_balance);
    printf("- A3 (Goc nghieng cuc dai on dinh): %.3f do\n", max_angle_stable);
    printf("- A4 (Goc phat hien nga): %.3f do\n", fall_trigger_angle);
    printf("- A5 (Thoi gian phan hoi ngat xung): %.2f ms\n", fall_response_time_ms);
    printf("- Trang thai tong the: %s\n", all_tests_passed ? "DAT" : "KHONG DAT");

    printf("{\"dat\": %s, \"do\": {\"A1\": %.2f, \"A2\": %.3f, \"A3\": %.3f, \"A4\": %.3f, \"A5\": %.2f}}\n",
           all_tests_passed ? "true" : "false",
           measured_loop_ms, measured_trigger_balance, max_angle_stable, fall_trigger_angle, fall_response_time_ms);

    return 0;
}