#include <Arduino.h>
#include <avr/interrupt.h>
#include "config.h"
#include "mpu6050.h"
#include "motor.h"
#include "control.h"

/* Biến đếm nhịp 1 ms từ Timer0 để tạo chu kỳ 4 ms cho Tầng 2 */
static volatile uint8_t g_timer0_ms = 0;
static volatile uint8_t g_flag_4ms = 0;

/* Quản lý còi không chặn (non-blocking) theo Bảng 2.4 */
static uint32_t g_buzzer_off_time = 0;

static void buzzer_on(uint16_t duration_ms) {
    PORT_BUZZER |= (1 << BIT_BUZZER);
    g_buzzer_off_time = millis() + duration_ms;
}

static void buzzer_update(void) {
    if (g_buzzer_off_time > 0 && millis() >= g_buzzer_off_time) {
        PORT_BUZZER &= ~(1 << BIT_BUZZER);
        g_buzzer_off_time = 0;
    }
}

/* Ngắt so sánh Timer0 Compare Match A theo Bảng 16 */
ISR(TIMER0_COMPA_vect) {
    g_timer0_ms++;
    if (g_timer0_ms >= 4) {
        g_timer0_ms = 0;
        g_flag_4ms = 1;
    }
}

void setup() {
    /* =====================================================================
     * THỨ TỰ KHỞI TẠO PHẦN CỨNG (BẢNG 13 & BẢNG 1.3)
     * ===================================================================== */

    /* 1. Cấu hình còi D10 (PB2 - Ra) và nút bấm D12 (PB4 - Vào kéo lên) */
    DDR_BUZZER |= (1 << BIT_BUZZER);
    PORT_BUZZER &= ~(1 << BIT_BUZZER);

    DDR_BUTTON &= ~(1 << BIT_BUTTON);
    PORT_BUTTON |= (1 << BIT_BUTTON);   /* Bật điện trở kéo lên nội bộ */

    /* 2. Đặt cổng nối tiếp ở 9600 baud (Bảng 13 dòng 6, Bảng 15) */
    Serial.begin(FACT_UART_BAUD);
    Serial.println(F("[ROBOT] Khoi dong he thong..."));

    /* 3. Cấu hình Timer0 ngắt 1 ms với OCR0A = 249 (Bảng 16 dòng 4) */
    OCR0A = FACT_OCR0A_VAL;
    TIMSK0 |= (1 << OCIE0A);

    /* 4. Khởi tạo giao tiếp I2C và cảm biến MPU-6050 */
    if (!mpu6050_init()) {
        Serial.println(F("[LOI] Khong tim thay cam bien MPU-6050!"));
        /* Còi báo lỗi lặp lại nếu không đọc được cảm biến (Bảng 2.4) */
        while (1) {
            PORT_BUZZER |= (1 << BIT_BUZZER);
            delay(80);
            PORT_BUZZER &= ~(1 << BIT_BUZZER);
            delay(200);
        }
    }
    Serial.println(F("[ROBOT] MPU-6050 da ket noi thanh cong (I2C nhan)."));

    /* 5. Khởi tạo hệ thống động cơ bước và Timer2 ngắt 50 kHz (kèm D13 đo xung) */
    motor_init();
    Serial.println(F("[ROBOT] Timer2 50 kHz da kich hoat."));

    /* 6. Khởi tạo bộ điều khiển */
    control_init();

    /* Bật ngắt toàn cục */
    sei();

    /* YC-01 & Bảng 2.4 dòng 2: Báo 1 tiếng còi 100 ms ngay khi bật nguồn thành công */
    buzzer_on(100);
    Serial.println(F("[ROBOT] He thong san sang! Dang dung cho nut bam D12."));
}

void loop() {
    static uint32_t last_batt_check_ms = 0;
    static uint32_t last_button_scan_ms = 0;
    static uint8_t button_prev_state = 1;
    static uint32_t button_press_start = 0;
    static bool low_battery_detected = false;
    static bool fallen_reported = false;

    /* Cập nhật tắt còi không chặn */
    buzzer_update();

    /* =====================================================================
     * TẦNG 2: VÒNG LẶP CHU KỲ 4 ms (THEO CỜ TIMER0)
     * ===================================================================== */
    if (g_flag_4ms) {
        g_flag_4ms = 0;

        if (!low_battery_detected) {
            mpu6050_raw_t imu_raw;
            if (mpu6050_read_raw(&imu_raw)) {
                control_update_4ms(&imu_raw);
            }
        }
    }

    /* =====================================================================
     * TẦNG 3: TÁC VỤ NỀN (QUÉT NÚT BẤM, ĐO PIN, BÁO CÒI VÀ TRUYỀN NỐI TIẾP)
     * ===================================================================== */
    uint32_t now = millis();

    /* 1. Quét nút bấm D12 (YC-03) mỗi 10 ms */
    if (now - last_button_scan_ms >= 10) {
        last_button_scan_ms = now;
        uint8_t btn_pin = (PIN_IN_BUTTON & (1 << BIT_BUTTON)) ? 1 : 0;

        if (button_prev_state == 1 && btn_pin == 0) {
            /* Nút vừa được nhấn xuống */
            button_press_start = now;
        } else if (button_prev_state == 0 && btn_pin == 1) {
            /* Nút vừa được nhả ra */
            uint32_t press_duration = now - button_press_start;
            if (press_duration >= 30 && press_duration < 2000) {
                /* Bấm nhả nhanh (YC-03, Bảng 9 dòng 6 & Bảng 23 dòng 6): đổi trạng thái */
                const control_state_t *st = control_get_state();
                if (st->is_balancing) {
                    /* Đang chạy -> Dừng */
                    motor_stop();
                    control_reset();
                    buzzer_on(100);
                    Serial.println(F("[NUT] Nhan nut: Chuyen sang DUNG"));
                } else {
                    /* Đang dừng -> Bật sẵn sàng cân bằng */
                    control_reset();
                    buzzer_on(100);
                    Serial.println(F("[NUT] Nhan nut: Chuyen sang SAN SANG"));
                }
            }
        }
        button_prev_state = btn_pin;
    }

    /* 2. Giám sát trạng thái ngã đổ (YC-05 & Bảng 2.4 dòng 5) */
    const control_state_t *st = control_get_state();
    if (st->is_fallen) {
        if (!fallen_reported) {
            fallen_reported = true;
            buzzer_on(200);
            Serial.println(F("[CANH BAO] Robot da do qua 30 do! Tat xung dong co."));
        }
    } else {
        fallen_reported = false;
    }

    /* 3. Đo pin định kỳ theo FACT_BATT_INTERVAL_MS (YC-06 & Bảng 15 dòng 21) */
    if (now - last_batt_check_ms >= FACT_BATT_INTERVAL_MS) {
        last_batt_check_ms = now;

        /* Đọc điện áp pin từ chân A0 qua cầu chia */
        int batt_raw = analogRead(PIN_BATTERY_ADC);

        /* Kiểm tra ngưỡng pin yếu (Bảng 15 dòng 20: FACT_LOW_BATT_THRESHOLD = 420) */
        if (batt_raw < FACT_LOW_BATT_THRESHOLD) {
            low_battery_detected = true;
            motor_stop();
            buzzer_on(300);
            Serial.print(F("[CANH BAO] Pin yeu (< 420): "));
            Serial.println(batt_raw);
        } else {
            /* In trạng thái nối tiếp định kỳ (YC-07) */
            Serial.print(F("[INFO] Goc: "));
            Serial.print(st->angle_pitch);
            Serial.print(F(" | Can bang: "));
            Serial.print(st->is_balancing ? F("BAT") : F("TAT"));
            Serial.print(F(" | Pin: "));
            Serial.println(batt_raw);
        }
    }
}
