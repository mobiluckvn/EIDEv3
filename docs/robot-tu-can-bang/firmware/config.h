#ifndef CONFIG_H_
#define CONFIG_H_

#include <avr/io.h>

/* =========================================================================
 * CẤU HÌNH HỆ THỐNG VÀ PHẦN CỨNG MOBILUCK (ATmega328P @ 16 MHz)
 * ========================================================================= */

#define F_CPU 16000000UL /* 16 MHz (anh cho, chưa có tài liệu) */

/* Tần số và chu kỳ các tầng thời gian thực (NFR-01, ADR-01) */
#define TIMER2_FREQ_HZ       50000UL   /* Tầng 1: Ngắt phát xung bước 50 kHz (anh cho, chưa có tài liệu) */
#define TIMER0_TICK_HZ       1000UL    /* Tầng 2: Timer0 ngắt 1 kHz (anh cho, chưa có tài liệu) */
#define CONTROL_LOOP_MS      4         /* Tầng 2: Chu kỳ vòng cân bằng 4 ms (anh cho, chưa có tài liệu) */
#define CONTROL_LOOP_DT      ((float)CONTROL_LOOP_MS / (float)TIMER0_TICK_HZ)

/* Chân ngoại vi giao tiếp người dùng và điểm đo kiểm (§13.4) */
#define BUZZER_PIN           PB2       /* D10 (PB2): Còi chip báo hiệu trạng thái (FR-01) */
#define BUZZER_DDR           DDRB
#define BUZZER_PORT          PORTB

#define BUTTON_PIN           PB4       /* D12 (PB4): Nút nhấn chuyển trạng thái (FR-03) */
#define BUTTON_DDR           DDRB
#define BUTTON_PINREG        PINB
#define BUTTON_PORT          PORTB

#define PROBE_ISR_PIN        PB5       /* D13 (PB5): Điểm đo thời gian thực thi ISR Tầng 1 (Bảng 13, §13.4) */
#define PROBE_ISR_DDR        DDRB
#define PROBE_ISR_PORT       PORTB

/* Chân điều khiển Driver A4988 Động cơ Trái (Motor L) theo Bảng 13 (STEP2 = D7, DIR2 = D6) */
#define MOTOR_L_STEP_PIN     PD7       /* D7 (PD7): Xung STEP động cơ trái (STEP2) */
#define MOTOR_L_STEP_DDR     DDRD
#define MOTOR_L_STEP_PORT    PORTD

#define MOTOR_L_DIR_PIN      PD6       /* D6 (PD6): Hướng DIR động cơ trái (DIR2) */
#define MOTOR_L_DIR_DDR      DDRD
#define MOTOR_L_DIR_PORT     PORTD

/* Chân điều khiển Driver A4988 Động cơ Phải (Motor R) theo Bảng 13 (STEP1 = D5, DIR1 = D4) */
#define MOTOR_R_STEP_PIN     PD5       /* D5 (PD5): Xung STEP động cơ phải (STEP1) */
#define MOTOR_R_STEP_DDR     DDRD
#define MOTOR_R_STEP_PORT    PORTD

#define MOTOR_R_DIR_PIN      PD4       /* D4 (PD4): Hướng DIR động cơ phải (DIR1) */
#define MOTOR_R_DIR_DDR      DDRD
#define MOTOR_R_DIR_PORT     PORTD

/* =========================================================================
 * THAM SỐ HIỆU CHUẨN BO HẠNG L (Tài liệu bàn giao §11)
 * ========================================================================= */
#define CALIB_ACCEL_ZERO_RAW   102       /* Giá trị thô gia tốc tại điểm cân bằng (LSB, ±4 g) (§11.2) */
#define CALIB_PITCH_OFFSET_DEG (0.713f)  /* Góc lệch lắp đặt cảm biến [°] (§11.2) */
#define CALIB_AXIS_DIR_Z       (1.0f)    /* Chiều trục trước-sau s_net = +1 (nghiêng tới -> pitch > 0) (§13.4 Mục 4) */

/* Mức logic chân DIR khi đi tới theo Fact f-nguoi-34069670 (quan sát trực tiếp trên bo của anh Công) */
#define DIR_FORWARD_LEFT       1         /* Bánh TRÁI: mức CAO (HIGH) = tiến */
#define DIR_FORWARD_RIGHT      0         /* Bánh PHẢI: mức THẤP (LOW) = tiến */

/* GHI CHÚ PHẦN CỨNG ĐẶC BIỆT:
 * Chân EN của 2 driver A4988 nối cứng GND trên mạch bo mạch.
 * Dừng động cơ bắt buộc thực hiện bằng cách ngắt phát xung STEP (EIDE.md).
 */

/* Cấu hình an toàn và góc nghiêng theo bản tham chiếu app_balance.c */
#define ANGLE_FALL_LIMIT_DEG 30.0f     /* Ngưỡng ngã robot: ngắt xung bước khi vượt ±30 độ (app_balance.c:133) */
#define ANGLE_ACTIVE_DEG     0.5f      /* Cửa sổ kích hoạt cân bằng: ±0,5 độ (app_balance.c:116) */
#define ACCEL_BALANCE_OFFSET (-535)    /* Offset cơ khí trục Z gia tốc theo bản tham chiếu (drv_imu.c:9) */

/* Cấu hình MPU6050 */
#define MPU6050_ADDR         0x68      /* Địa chỉ I2C mặc định MPU6050 */
#define I2C_TIMEOUT_CYCLES   1000      /* Vòng lặp timeout chống treo TWI (anh cho, chưa có tài liệu) */

/* Cấu hình hiệu chuẩn (FR-02) */
#define CALIB_SAMPLES        500       /* Số mẫu đo offset tĩnh MPU6050 (anh cho, chưa có tài liệu) */

#endif /* CONFIG_H_ */
