#define EIDE_SIM 1

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
#include <assert.h>

/* =========================================================================
 * GIẢ LẬP PHẦN CỨNG AVR CHO MÁY CHỦ LINUX / MACOS
 * ========================================================================= */
volatile uint8_t sim_DDRB  = 0;
volatile uint8_t sim_PORTB = 0;
volatile uint8_t sim_PINB  = 0xFF;

uint8_t PORTD = 0;
uint8_t DDRD  = 0;
uint8_t PORTC = 0;
uint8_t DDRC  = 0;
uint8_t PINC  = 0xFF;
uint8_t PIND  = 0xFF;

uint8_t ADMUX  = 0;
uint8_t ADCSRA = 0;
uint16_t ADC   = 1023;

#define REFS0 6
#define ADEN  7
#define ADSC  6
#define ADPS2 2
#define ADPS1 1
#define ADPS0 0

uint8_t TWBR = 0;
uint8_t TWSR = 0;
uint8_t TWCR = 0;
uint8_t TWDR = 0;

#define cli()
#define sei()
#define _BV(bit) (1 << (bit))
#define abs(x) ((x) < 0 ? -(x) : (x))

/* Giả lập bộ đếm thời gian hệ thống millis */
static uint32_t s_mock_ms = 1000;
uint32_t timer_get_ms(void) {
    return s_mock_ms;
}

/* Giả lập cờ Timer 4 ms */
static bool s_mock_control_flag = false;
bool timer_check_control_flag(void) {
    if (s_mock_control_flag) {
        s_mock_control_flag = false;
        return true;
    }
    return false;
}
uint16_t timer_get_deadline_miss(void) {
    return 0;
}

/* Mock I2C và MPU6050 */
#include "../firmware/mpu6050.h"

static mpu6050_raw_data_t s_mock_raw = {0, 0, 0, 0, 0, 0};
static int16_t s_mock_gyro_bias_x = 0;
static int16_t s_mock_gyro_bias_y = 0;

bool mpu6050_read_raw(mpu6050_raw_data_t *raw) {
    *raw = s_mock_raw;
    return true;
}
int16_t mpu6050_get_gyro_bias_x_raw(void) {
    return s_mock_gyro_bias_x;
}
int16_t mpu6050_get_gyro_bias_y_raw(void) {
    return s_mock_gyro_bias_y;
}
bool mpu6050_calib_step(bool *out_done) {
    *out_done = true;
    return true;
}
void mpu6050_calib_reset(void) {}

/* Mock UART */
bool uart_send_line(const char *str) {
    (void)str;
    return true;
}

/* =========================================================================
 * INCLUDE TRỰC TIẾP MÃ SẢN PHẨM THẬT TRONG FIRMWARE/
 * ========================================================================= */
#include "../firmware/motor.c"
#include "../firmware/pid.c"
#include "../firmware/filter.c"
#include "../firmware/fsm.c"

/* Hàm tính góc V1 chuẩn dùng làm đối chứng tuyệt đối */
static float v1_calc_angle_ref(int16_t raw_z) {
    int32_t z = (int32_t)raw_z + 92; /* V1:405, V1:76 */
    if (z > 8200) z = 8200;
    if (z < -8200) z = -8200;
    return asinf((float)z / 8200.0f) * 57.29578f;
}

int main(void) {
    printf("=== TEST KIEM CHUNG THUC NGHIEM A1 VA A2 TRUC TIEP TREN FIRMWARE ===\n");

    /* =====================================================================
     * PHẦN 1: BÀI KIỂM A2 — SO SÁNH BIT PORTD KHI GỌI MOTOR_ISR_STEP() THẬT
     * ===================================================================== */
    printf("\n[BAI KIEM A2] Goi truc tiep motor_set_throttle() va motor_isr_step() that:\n");
    motor_init();
    motor_enable();

    /* Ca 1: Lệnh TIẾN (throttle = +50 cho cả 2 bánh) */
    motor_set_throttle(50, 50);
    motor_isr_step();
    motor_isr_step();

    uint8_t d6_val = (PORTD & (1 << MOTOR_L_DIR_PIN)) ? 1 : 0;
    uint8_t d4_val = (PORTD & (1 << MOTOR_R_DIR_PIN)) ? 1 : 0;
    printf("  Ca 1 (Tien thr=+50): D6(Trai)=%d (exp 0), D4(Phai)=%d (exp 1) -> ", d6_val, d4_val);
    assert(d6_val == 0 && "Banh Trai D6 phai bang 0 (LOW) khi tien theo V1:581");
    assert(d4_val == 1 && "Banh Phai D4 phai bang 1 (HIGH) khi tien theo V1:598");
    printf("PASS\n");

    /* Ca 2: Lệnh LÙI (throttle = -50 cho cả 2 bánh) */
    motor_set_throttle(-50, -50);
    for (int i = 0; i < 60; i++) {
        motor_isr_step();
    }
    d6_val = (PORTD & (1 << MOTOR_L_DIR_PIN)) ? 1 : 0;
    d4_val = (PORTD & (1 << MOTOR_R_DIR_PIN)) ? 1 : 0;
    printf("  Ca 2 (Lui thr=-50):  D6(Trai)=%d (exp 1), D4(Phai)=%d (exp 0) -> ", d6_val, d4_val);
    assert(d6_val == 1 && "Banh Trai D6 phai bang 1 (HIGH) khi lui theo V1:576");
    assert(d4_val == 0 && "Banh Phai D4 phai bang 0 (LOW) khi lui theo V1:593");
    printf("PASS\n");

    /* =====================================================================
     * PHẦN 2: BÀI KIỂM A1 — GỌI TRỰC TIẾP FSM_UPDATE_CONTROL_4MS() THẬT
     * ===================================================================== */
    printf("\n[BAI KIEM A1] Goi truc tiep fsm_update_control_4ms() that de kiem tra goc:\n");
    fsm_init();
    s_state = STATE_STOPPED;

    int16_t test_cases[] = {-92, 0, 100, 1000, 4100, 7600, -5000, -8200, 8200};
    int n_cases = sizeof(test_cases) / sizeof(test_cases[0]);

    for (int i = 0; i < n_cases; i++) {
        int16_t rz = test_cases[i];
        s_mock_raw.accel_z = rz;
        s_mock_raw.gyro_x  = 0;
        s_mock_raw.gyro_y  = 0;

        /* Gọi hàm thật của firmware */
        fsm_update_control_4ms();
        float fw_pitch = fsm_get_pitch();
        float v1_pitch = v1_calc_angle_ref(rz);
        float diff = fabsf(fw_pitch - v1_pitch);

        printf("  raw_z = %6d | V1: %8.4f deg | FW that: %8.4f deg | diff: %.6f -> ",
               rz, v1_pitch, fw_pitch, diff);
        assert(diff < 1e-4f && "Goc tinh tu fsm_update_control_4ms() phai khop tuyet doi voi V1!");
        printf("PASS\n");
    }

    /* Khẳng định điểm cân bằng cơ khí: tại raw_z = -92, fsm_get_pitch() phải bằng đúng 0.0000 deg */
    s_mock_raw.accel_z = -92;
    fsm_update_control_4ms();
    assert(fabsf(fsm_get_pitch()) < 1e-5f && "Diem can bang phai o dung raw_z = -92 LSB");
    printf("  Diem can bang tai raw_z = -92 LSB -> pitch = %.4f deg -> PASS\n", fsm_get_pitch());

    printf("\n>>> TAT CA BAI KIEM TRA A1 VA A2 GOC DA DAT 100%% VOI FIRMWARE THAT! <<<\n");
    return 0;
}
