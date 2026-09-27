#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/wdt.h>
#include <stdint.h>
#include <stdbool.h>

#include "control.h"

/**
 * @file firmware.ino
 * @brief Chương trình điều khiển robot hai bánh tự cân bằng MOBILUCK.
 * Bo mạch: BLKLab_Balancing_Robot_Shield_v1 (ATmega328P @ 16 MHz).
 *
 * Cấu hình thanh ghi từ Fact tài liệu MOBILUCK-HW-v1.1:
 * - Timer2 CTC OCR2A=39, chia 8 (nhịp 20 µs)
 * - Timer1 chạy tự do chia 1 (đo thời gian)
 * - TWI 400 kHz: TWSR=0, TWBR=12
 * - USART0 9600 baud: UBRR0=207, U2X0=1
 * - ADC0: AVcc tham chiếu, ADCSRA prescaler 128
 */

/* Địa chỉ và thanh ghi MPU6050 */
#define MPU6050_ADDR        0x68
#define MPU6050_SMPLRT_DIV  0x19
#define MPU6050_CONFIG      0x1A
#define MPU6050_GYRO_CONFIG 0x1B
#define MPU6050_ACCEL_CONFIG 0x1C
#define MPU6050_PWR_MGMT_1  0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B

/* Định nghĩa chân trên các Port AVR */
#define PORTD_DIR1_PIN      PD4  /* D4: Hướng quay bánh phải */
#define PORTD_STEP1_PIN     PD5  /* D5: Xung bước bánh phải */
#define PORTD_DIR2_PIN      PD6  /* D6: Hướng quay bánh trái */
#define PORTD_STEP2_PIN     PD7  /* D7: Xung bước bánh trái */
#define PORTD_SONAR_TRIG    PD3  /* D3: Kích siêu âm */
#define PORTD_SONAR_ECHO    PD2  /* D2: Vọng siêu âm (INT0) */

#define PORTB_BUZZER_PIN    PB2  /* D10: Còi chip */
#define PORTB_WS2812_PIN    PB3  /* D11: LED RGB WS2812 */
#define PORTB_BUTTON_PIN    PB4  /* D12: Nút bấm */
#define PORTB_PROBE_ISR     PB5  /* D13: Điểm đo thời gian tầng 1 */

#define PORTC_ADC_BAT       PC0  /* A0: Giám sát điện áp pin */
#define PORTC_PROBE_PID     PC1  /* A1: Điểm đo thời gian tầng 2 */

/* Biến dùng chung giữa ISR và vòng chính */
static volatile motor_step_cmd_t g_step_cmd;
static volatile uint16_t g_step_cnt_left = 0;
static volatile uint16_t g_step_cnt_right = 0;

static control_state_t g_ctrl_state;
static pid_config_t g_pid_cfg;

/* Giao tiếp TWI phần cứng tối giản */
static void twi_init(void)
{
    TWSR = 0x00;  /* Fact f-d3ccbea5f6: TWPS = 0 */
    TWBR = 12;    /* Fact f-2c1c9c3d92: 400 kHz ở 16 MHz */
    TWCR = 0x04;  /* Fact f-9b233a7946: TWEN */
}

static uint8_t twi_start(uint8_t address)
{
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));
    TWDR = address;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));
    return (TWSR & 0xF8);
}

static void twi_stop(void)
{
    TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
}

static void twi_write(uint8_t data)
{
    TWDR = data;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));
}

static uint8_t twi_read_ack(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWEA);
    while (!(TWCR & (1 << TWINT)));
    return TWDR;
}

static uint8_t twi_read_nack(void)
{
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));
    return TWDR;
}

static void mpu6050_write_reg(uint8_t reg, uint8_t val)
{
    twi_start((MPU6050_ADDR << 1) | 0);
    twi_write(reg);
    twi_write(val);
    twi_stop();
}

static bool mpu6050_read_block14(int16_t *acc_x, int16_t *acc_z, int16_t *gyro_y)
{
    uint8_t raw[14];
    if (twi_start((MPU6050_ADDR << 1) | 0) != 0x18 && (TWSR & 0xF8) != 0x18) {
        twi_stop();
        return false;
    }
    twi_write(MPU6050_ACCEL_XOUT_H);

    if (twi_start((MPU6050_ADDR << 1) | 1) != 0x40 && (TWSR & 0xF8) != 0x40) {
        twi_stop();
        return false;
    }

    for (uint8_t i = 0; i < 13; i++) {
        raw[i] = twi_read_ack();
    }
    raw[13] = twi_read_nack();
    twi_stop();

    *acc_x  = (int16_t)((raw[0] << 8) | raw[1]);
    *acc_z  = (int16_t)((raw[4] << 8) | raw[5]);
    *gyro_y = (int16_t)((raw[10] << 8) | raw[11]);
    return true;
}

static uint16_t adc0_read(void)
{
    ADCSRA |= (1 << ADSC);
    while (ADCSRA & (1 << ADSC));
    return ADC;
}

/* ISR Tầng 1: Timer2 phát xung bước động cơ nhịp 20 µs (50 kHz) */
ISR(TIMER2_COMPA_vect)
{
    PORTB |= (1 << PORTB_PROBE_ISR); /* Dựng Probe D13 */

    /* Hạ xung STEP lần trước */
    PORTD &= ~((1 << PORTD_STEP1_PIN) | (1 << PORTD_STEP2_PIN));

    if (g_step_cmd.enabled) {
        if (g_step_cmd.dir_left) {
            PORTD |= (1 << PORTD_DIR2_PIN);
        } else {
            PORTD &= ~(1 << PORTD_DIR2_PIN);
        }

        if (g_step_cmd.period_ticks_left > 0) {
            g_step_cnt_left++;
            if (g_step_cnt_left >= g_step_cmd.period_ticks_left) {
                PORTD |= (1 << PORTD_STEP2_PIN);
                g_step_cnt_left = 0;
            }
        }

        if (g_step_cmd.dir_right) {
            PORTD |= (1 << PORTD_DIR1_PIN);
        } else {
            PORTD &= ~(1 << PORTD_DIR1_PIN);
        }

        if (g_step_cmd.period_ticks_right > 0) {
            g_step_cnt_right++;
            if (g_step_cnt_right >= g_step_cmd.period_ticks_right) {
                PORTD |= (1 << PORTD_STEP1_PIN);
                g_step_cnt_right = 0;
            }
        }
    }

    PORTB &= ~(1 << PORTB_PROBE_ISR); /* Hạ Probe D13 */
}

/* ISR Bộ lập lịch: Nhịp 1 ms từ Timer0 CTC (mục 12.5 & Phụ lục A.2) */
static volatile uint32_t g_system_tick_ms = 0;

ISR(TIMER0_COMPA_vect)
{
    g_system_tick_ms++;
}

static uint32_t g_last_ctrl_ms = 0;
static uint32_t g_last_bg_ms = 0;

void setup()
{
    /* BƯỚC 1: Đọc và xóa thanh ghi MCUSR, tắt Watchdog */
    MCUSR = 0;
    wdt_disable();

    /* BƯỚC 2: Cấu hình hướng chân GPIO */
    DDRD |= (1 << PORTD_DIR1_PIN) | (1 << PORTD_STEP1_PIN) |
            (1 << PORTD_DIR2_PIN) | (1 << PORTD_STEP2_PIN) |
            (1 << PORTD_SONAR_TRIG);
    DDRD &= ~(1 << PORTD_SONAR_ECHO);

    DDRB |= (1 << PORTB_BUZZER_PIN) | (1 << PORTB_WS2812_PIN) |
            (1 << PORTB_PROBE_ISR);
    DDRB &= ~(1 << PORTB_BUTTON_PIN);
    PORTB |= (1 << PORTB_BUTTON_PIN);

    DDRC |= (1 << PORTC_PROBE_PID);
    DDRC &= ~(1 << PORTC_ADC_BAT);

    /* BƯỚC 3: Mức logic ban đầu */
    PORTD &= ~((1 << PORTD_STEP1_PIN) | (1 << PORTD_STEP2_PIN) |
               (1 << PORTD_SONAR_TRIG));
    PORTB &= ~((1 << PORTB_BUZZER_PIN) | (1 << PORTB_PROBE_ISR));
    PORTC &= ~(1 << PORTC_PROBE_PID);

    /* BƯỚC 4: Khởi tạo USART0 (9600 baud, 16 MHz) */
    UBRR0H = 0;
    UBRR0L = 207;   /* Fact f-426e02b2b9 */
    UCSR0A = 0x02;  /* Fact f-48a6cf7f20: U2X0 = 1 */
    UCSR0B = 0x98;  /* Fact f-5a08b5e7e8: TXEN0 | RXEN0 | RXCIE0 */
    UCSR0C = 0x06;  /* Fact f-ed28b1e49c: 8N1 */

    /* BƯỚC 5: Khởi tạo Timer1 chạy tự do chia 1 */
    TCCR1A = 0x00;
    TCCR1B = 0x01;  /* Fact f-fba4a24240: CS10 = 1 */

    /* BƯỚC 5b: Khởi tạo Timer0 (nhịp 1 ms bộ lập lịch, mục 12.5 & Phụ lục A.2) */
    TCCR0A = 0x02;  /* Fact f-4111f50961: CTC (WGM01) */
    TCCR0B = 0x03;  /* Fact f-1bbd11fcfc: Prescaler 64 (CS01 | CS00) */
    OCR0A  = 0xF9;  /* Fact f-24f57c499c: 249 ticks (chu kỳ 1 ms tại 16 MHz) */
    TIMSK0 = 0x02;  /* Phụ lục A.2: OCIE0A cho phép ngắt Compare Match A */

    /* BƯỚC 6: Khởi tạo ADC kênh 0 */
    ADMUX  = 0x40;  /* Fact f-1129754268: AVcc, kênh ADC0 */
    ADCSRA = 0x87;  /* Fact f-a82813b202: ADEN, chia 128 */

    /* BƯỚC 7: Khởi tạo TWI 400 kHz (TWCR=0x04) */
    twi_init();

    /* BƯỚC 8: Khởi tạo cảm biến MPU6050 */
    mpu6050_write_reg(MPU6050_PWR_MGMT_1, 0x00);
    mpu6050_write_reg(MPU6050_CONFIG, 0x03);
    mpu6050_write_reg(MPU6050_GYRO_CONFIG, 0x00);
    mpu6050_write_reg(MPU6050_ACCEL_CONFIG, 0x08);

    /* BƯỚC 9: Khởi tạo logic điều khiển */
    control_init(&g_ctrl_state);
    g_pid_cfg.kp = 18000;
    g_pid_cfg.ki = 0;
    g_pid_cfg.kd = 1200;
    g_pid_cfg.target_mdeg = 0;
    g_pid_cfg.max_integral = 5000;
    g_pid_cfg.max_output = 400;

    /* BƯỚC 10: Khởi tạo Timer2 (nhịp 20 µs phát xung bước) */
    TCCR2A = 0x02;  /* Fact f-ddd7b94864: CTC */
    TCCR2B = 0x02;  /* Fact f-0dd6246676: Chia 8 */
    OCR2A  = 39;    /* Fact f-a37df53dac: Chu kỳ 20 µs */
    TIMSK2 = 0x02;  /* Fact f-c4aa5d66a5: OCIE2A */

    /* BƯỚC 11: Cho phép ngắt toàn cục */
    sei();
}

void loop()
{
    uint32_t now = g_system_tick_ms;

    /* TẦNG 2: Vòng điều khiển chu kỳ 4 ms */
    if (now - g_last_ctrl_ms >= 4) {
        g_last_ctrl_ms = now;
        PORTC |= (1 << PORTC_PROBE_PID);

        int16_t raw_ax = 0, raw_az = 0, raw_gy = 0;
        if (mpu6050_read_block14(&raw_ax, &raw_az, &raw_gy)) {
            control_update_imu(&g_ctrl_state, raw_ax, raw_az, raw_gy, 0, 131, 4);

            int16_t throttle = control_calc_pid(&g_ctrl_state, &g_pid_cfg, 4);

            if (g_ctrl_state.angle_pitch_mdeg > 35000 || g_ctrl_state.angle_pitch_mdeg < -35000) {
                throttle = 0;
            }

            motor_step_cmd_t cmd;
            control_throttle_to_steps(throttle, throttle, &cmd);
            g_step_cmd.period_ticks_left  = cmd.period_ticks_left;
            g_step_cmd.period_ticks_right = cmd.period_ticks_right;
            g_step_cmd.dir_left           = cmd.dir_left;
            g_step_cmd.dir_right          = cmd.dir_right;
            g_step_cmd.enabled            = cmd.enabled;
        }

        PORTC &= ~(1 << PORTC_PROBE_PID);
    }

    /* TẦNG 3: Tác vụ nền (100 ms) */
    if (now - g_last_bg_ms >= 100) {
        g_last_bg_ms = now;
        volatile uint16_t bat_adc = adc0_read();
        (void)bat_adc;
    }
}
