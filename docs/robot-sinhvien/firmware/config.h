#ifndef CONFIG_H
#define CONFIG_H

#include <stdint.h>
#ifndef EIDE_SIM
#include <avr/io.h>
#endif

/* =========================================================================
 * BẢNG 15: CÁC THAM SỐ THỰC NGHIỆM ĐÃ KIỂM CHỨNG TRÊN BO THẬT
 * ========================================================================= */
#define FACT_SO_BU_GIA_TOC          92
#define FACT_ACCEL_MIN              -8200
#define FACT_ACCEL_MAX              8200
#define FACT_RAD_TO_DEG             57.29578f
#define FACT_GYRO_PITCH_COEFF       0.000031f
#define FACT_GYRO_YAW_COEFF         0.0000003f
#define FACT_FILTER_GYRO            0.9996f
#define FACT_FILTER_ACCEL           0.0004f
#define FACT_PID_KP                 12.0f
#define FACT_PID_KI                 0.4f
#define FACT_PID_KD                 10.0f
#define FACT_BRAKE_THRESHOLD        10.0f
#define FACT_BRAKE_COEFF            0.015f
#define FACT_INTEGRAL_CLAMP_MIN     -400.0f
#define FACT_INTEGRAL_CLAMP_MAX     400.0f
#define FACT_DEADZONE_MIN           -5.0f
#define FACT_DEADZONE_MAX           5.0f
#define FACT_AUTO_BALANCE_STEP      0.002f
#define FACT_BALANCE_ANGLE_MIN      -0.5f
#define FACT_BALANCE_ANGLE_MAX      0.5f
#define FACT_FALL_ANGLE             30.0f
#define FACT_LOW_BATT_THRESHOLD     420
#define FACT_BATT_INTERVAL_MS       500
#define FACT_GYRO_SCALE             131.0f
#define FACT_ACCEL_SCALE            8192.0f
#define FACT_DT_SEC                 0.004f

/* =========================================================================
 * BẢNG 16: GIÁ TRỊ CẤU HÌNH THANH GHI VI ĐIỀU KHIỂN
 * ========================================================================= */
#define FACT_OCR0A_VAL              249     /* Timer0 nhịp 1 ms ở prescaler 64 */
#define FACT_OCR2A_VAL              39      /* Timer2 nhịp ngắt 50 kHz ở prescaler 8 */
#define FACT_TWBR_VAL               12      /* TWI/I2C nhịp 400 kHz */
#define FACT_UART_BAUD              9600    /* Cổng nối tiếp 9600 baud */

/* =========================================================================
 * BẢNG 1.3: GÁN CHÂN PHẦN CỨNG (ARDUINO NANO / ATMEGA328P)
 * ========================================================================= */
/* 1. Động cơ bước Trái & Phải (PORTD) */
#define PIN_DIR_RIGHT               4       /* PD4 / D4: Chọn chiều quay bánh phải */
#define PIN_STEP_RIGHT              5       /* PD5 / D5: Phát xung bước bánh phải */
#define PIN_DIR_LEFT                6       /* PD6 / D6: Chọn chiều quay bánh trái */
#define PIN_STEP_LEFT               7       /* PD7 / D7: Phát xung bước bánh trái */

/* Mức logic chiều tiến theo Bảng 3.3 của tài liệu đặc tả:
 * - Bánh trái: chiều TIẾN là mức THẤP (0), chiều LÙI là mức CAO (1)
 * - Bánh phải: chiều TIẾN là mức CAO (1), chiều LÙI là mức THẤP (0)
 */
#define DIR_LEFT_FORWARD            0       /* Bảng 3.3: Chiều tiến bánh trái là mức THẤP (0) */
#define DIR_RIGHT_FORWARD           1       /* Bảng 3.3: Chiều tiến bánh phải là mức CAO (1) */

#define PORT_STEP_DIR               PORTD
#define DDR_STEP_DIR                DDRD
#define BIT_DIR_RIGHT               4
#define BIT_STEP_RIGHT              5
#define BIT_DIR_LEFT                6
#define BIT_STEP_LEFT               7

/* 2. Còi báo hiệu (PORTB) */
#define PIN_BUZZER                  10      /* PB2 / D10: Còi chip báo hiệu */
#define PORT_BUZZER                 PORTB
#define DDR_BUZZER                  DDRB
#define BIT_BUZZER                  2

/* 3. Nút bấm (PORTB) - có kéo lên nội bộ */
#define PIN_BUTTON                  12      /* PB4 / D12: Nút bấm điều khiển */
#define PIN_IN_BUTTON               PINB
#define PORT_BUTTON                 PORTB
#define DDR_BUTTON                  DDRB
#define BIT_BUTTON                  4

/* 4. Chân đo thời gian chạy của hàm ngắt (dùng cho máy hiện sóng) */
#define PIN_DEBUG_ISR               13      /* PB5 / D13: Đo thời gian chạy ISR */
#define PORT_DEBUG_ISR              PORTB
#define DDR_DEBUG_ISR               DDRB
#define BIT_DEBUG_ISR               5

/* 5. Chân đo điện áp pin qua cầu chia */
#define PIN_BATTERY_ADC             0       /* PC0 / Chân A0 */

#endif /* CONFIG_H */
