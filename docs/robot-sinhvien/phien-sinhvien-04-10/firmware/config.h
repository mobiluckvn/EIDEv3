#ifndef CONFIG_H_
#define CONFIG_H_

#include <stdint.h>
#include <stdbool.h>
#ifndef EIDE_SIM
#include <avr/io.h>
#include <avr/interrupt.h>
#endif

/* Cac chan vao/ra tren vi dieu khien */
#define PIN_DIR_L      PD6
#define PIN_DIR_R      PD4
#define PIN_STEP_L     PD7
#define PIN_STEP_R     PD5

#define MOTOR_PORT     PORTD
#define MOTOR_DDR      DDRD

#define PIN_BUZZER     PB2
#define BUZZER_PORT    PORTB
#define BUZZER_DDR     DDRB

#define PIN_BUTTON     PB4
#define BUTTON_PIN     PINB
#define BUTTON_PORT    PORTB
#define BUTTON_DDR     DDRB

#define PIN_TEST_D13   PB5
#define TEST_D13_PORT  PORTB
#define TEST_D13_DDR   DDRB

#define PIN_TEST_A1    PC1
#define TEST_A1_PORT   PORTC
#define TEST_A1_DDR    DDRC

#define PIN_TEST_A2    PC2
#define TEST_A2_PORT   PORTC
#define TEST_A2_DDR    DDRC

#define ADC_PIN_BATT   0

/* Tham so tinh goc theo muc 2.2 va Bang A.1 (anh cho, chua co tai lieu) */
#define ACCEL_OFFSET_Z            92
#define ACCEL_CLIP_MIN            -8200
#define ACCEL_CLIP_MAX            8200
#define RAD_TO_DEG                57.29578f

#define GYRO_PITCH_COEFF          0.000031f
#define GYRO_YAW_COEFF            0.0000003f
#define FILTER_WEIGHT_GYRO        0.9996f
#define FILTER_WEIGHT_ACCEL       0.0004f

/* Bang A.2: Chieu tien dong co (anh cho, chua co tai lieu) */
#define DIR_LEFT_FWD_LEVEL        0
#define DIR_RIGHT_FWD_LEVEL       1

/* Tham so dieu khien theo Muc E (anh cho, chua co tai lieu) */
#define PID_KP                    12.0f
#define PID_KI                    0.4f
#define PID_KD                    10.0f
#define PID_INTEGRAL_LIMIT        400.0f
#define PID_OUTPUT_LIMIT          400.0f
#define PID_FEEDBACK_THRESHOLD    10.0f
#define PID_FEEDBACK_GAIN         0.015f
#define PID_LEARN_STEP            0.002f

#define ANGLE_LIMIT_FALLEN        30.0f
#define ANGLE_WINDOW_BALANCE      0.5f

#define MOTOR_PULSE_MIN           1
#define MOTOR_PULSE_MAX           2000

/* Nguyen mau ham cac mo-dun */
void timer_init(void);
uint32_t millis(void);
uint32_t micros(void);
uint32_t timer_get_step_ticks(void);
void delay_ms(uint16_t ms);

void uart_init(void);
void uart_putc(char c);
void uart_puts(const char *s);
void uart_put_int(int32_t n);
void uart_send_line(const char *s);
uint16_t uart_get_dropped_lines(void);
void uart_send_telemetry(const char *state_name, float angle, int16_t az, int16_t pulse_l, int16_t pulse_r, uint16_t dropped_lines, uint16_t overrun_count);
void uart_send_timing(uint16_t t_i2c, uint16_t t_filter, uint16_t t_ctrl, uint16_t t_total);

void i2c_init(void);
bool i2c_start(uint8_t addr);
bool i2c_write(uint8_t data);
uint8_t i2c_read_ack(void);
uint8_t i2c_read_nack(void);
void i2c_stop(void);

bool mpu6050_init(void);
void mpu6050_calibrate(void);
bool mpu6050_read_raw(int16_t *az, int16_t *gx, int16_t *gy);

void filter_init(void);
float filter_calc_accel_angle(int16_t raw_az);
float filter_update(float accel_angle, int16_t raw_gx, int16_t raw_gy);
float filter_get_angle(void);

void pid_init(void);
void pid_reset(void);
float pid_calculate(float current_angle);
float pid_get_target_angle(void);

void motor_init(void);
void motor_step_isr(void);
void motor_set_target(int16_t pulse_l, int16_t pulse_r);
void motor_enable(bool en);
int16_t motor_calc_pulse(float output);

typedef enum {
    STATE_BOOT = 0,
    STATE_CALIBRATE,
    STATE_WAIT_BALANCE,
    STATE_RUNNING,
    STATE_FALLEN,
    STATE_LOW_BATT,
    STATE_SELF_TEST,
    STATE_ERROR
} robot_state_t;

void fsm_init(bool self_test_requested);
void fsm_update(void);
robot_state_t fsm_get_state(void);

#endif
