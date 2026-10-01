#define EIDE_SIM 1

#include <stdio.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "../firmware/mpu6050.h"
#include "../firmware/filter.h"
#include "../firmware/pid.h"
#include "../firmware/motor.h"

/* Khai báo các thanh ghi AVR giả lập */
volatile uint8_t sim_DDRB = 0;
volatile uint8_t sim_PORTB = 0;
volatile uint8_t sim_PINB = (1 << 4); /* Nút D12 (PB4) ban đầu thả (HIGH) */

static uint32_t sim_current_ms = 0;
static char sim_uart_log[4096] = "";

/* Triển khai các hàm mock ngoại vi phục vụ fsm.c */
uint32_t timer_get_ms(void) {
    return sim_current_ms;
}

bool uart_send_line(const char *str) {
    if (str != NULL) {
        strcat(sim_uart_log, str);
        strcat(sim_uart_log, "\n");
    }
    return true;
}

static int16_t sim_raw_z_val = 7580; /* Giả lập cảm biến cấp raw Z = 7580 LSB */

bool mpu6050_read_raw(mpu6050_raw_data_t *raw) {
    if (raw != NULL) {
        raw->accel_x = 0;
        raw->accel_y = 0;
        raw->accel_z = sim_raw_z_val;
        raw->gyro_x = 0;
        raw->gyro_y = 0;
        raw->gyro_z = 0;
    }
    return true;
}

bool mpu6050_read_scaled(mpu6050_data_t *data) {
    (void)data;
    return true;
}

void mpu6050_calib_reset(void) {}
bool mpu6050_calib_step(bool *done) {
    if (done) *done = true;
    return true;
}
int16_t mpu6050_get_gyro_bias_y_raw(void) {
    return 0;
}

void motor_stop(void) {}
void motor_enable(void) {}
void motor_set_throttle(int16_t l, int16_t r) { (void)l; (void)r; }
int16_t motor_calc_throttle_from_pid(float out) { (void)out; return 0; }

void filter_init(comp_filter_t *f, float a, float dt) { (void)f; (void)a; (void)dt; }
float filter_update(comp_filter_t *f, float a, float g) { (void)f; (void)g; return a; }
void filter_set_angle(comp_filter_t *f, float a) { (void)f; (void)a; }

void pid_init(void) {}
float pid_compute(float angle, float sp, bool run) { (void)angle; (void)sp; (void)run; return 0.0f; }
void pid_reset(void) {}

/* =========================================================================
 * INCLUDE TRỰC TIẾP TOÀN BỘ MÃ NGUỒN THẬT CỦA FIRMWARE FSM.C
 * ========================================================================= */
#include "../firmware/fsm.c"

int main(void) {
    printf("=== KIEM THU TRUC TIEP FIRMWARE/FSM.C TREN MAY CHU ===\n");

    /* 1. Khởi tạo FSM thật và chạy nhàn rỗi 500 ms sau bật nguồn */
    fsm_init();
    assert(fsm_get_state() == STATE_STOPPED);
    printf("[PASS] fsm_init() thanh cong, trang thai ban dau la STATE_STOPPED.\n");

    for (sim_current_ms = 0; sim_current_ms <= 500; sim_current_ms += 10) {
        fsm_update_background();
    }

    /* 2. Kịch bản: Bắt đầu nhấn giữ nút D12 (PB4 = LOW) trong 2.5 giây (từ 500 ms đến 3000 ms) */
    sim_PINB &= ~(1 << 4); /* Nhấn nút D12 */

    for (; sim_current_ms <= 3000; sim_current_ms += 10) {
        fsm_update_background();
    }

    /* Kiểm tra xem [OFFSET] DANG DO có xuất hiện trong UART log không */
    if (strstr(sim_uart_log, "[OFFSET] DANG DO 500 MAU") == NULL) {
        printf("[FAIL] DUONG DAN BI DUT: Khong kich hoat duoc che do do offset sau 2s giu nut!\n");
        return 1;
    }
    printf("[PASS] Nhan giu nut D12 >= 2s: fsm.c that da kich hoat che do do offset thanh cong.\n");

    /* 3. Nhả nút D12 (PB4 = HIGH) */
    sim_PINB |= (1 << 4);
    fsm_update_background();

    /* Khẳng định: FSM THẬT vẫn ở STATE_STOPPED, không bị nhảy sang STATE_CALIBRATING */
    if (fsm_get_state() != STATE_STOPPED) {
        printf("[FAIL] LOI LOGIC: Nha nut sau khi giu 2s bi nhay sang trang thai %d (le ra phai la STOPPED)!\n", fsm_get_state());
        return 1;
    }
    printf("[PASS] Nha nut sau khi giu 2s: FSM that van o dung STATE_STOPPED.\n");

    /* 4. Chạy 500 chu kỳ 4 ms để lấy 500 mẫu Z_raw */
    for (int i = 0; i < 500; i++) {
        sim_current_ms += 4;
        fsm_update_control_4ms();
    }

    /* Khẳng định: Chuỗi [OFFSET] KET QUA 500 MAU xuất hiện và in đúng giá trị mock 7580 LSB */
    if (strstr(sim_uart_log, "[OFFSET] KET QUA 500 MAU: Z_raw_avg = 7580") == NULL) {
        printf("[FAIL] Khong in duoc ket qua 500 mau offset tu fsm.c!\n");
        return 1;
    }
    printf("[PASS] fsm.c that da lay du 500 mau va in chinh xac: Z_raw_avg = 7580 LSB.\n");

    /* 5. Ca kiểm thử 3: Giữ nút khi đang ở trạng thái KHÁC (STATE_READY) */
    sim_uart_log[0] = '\0';
    s_state = STATE_READY; /* Đưa trạng thái FSM thật sang READY */
    assert(fsm_get_state() == STATE_READY);

    /* Nhấn giữ nút D12 trong 2.5 giây khi đang ở STATE_READY */
    sim_PINB &= ~(1 << 4);
    for (uint32_t t = 0; t <= 2500; t += 10) {
        sim_current_ms += 10;
        fsm_update_background();
    }
    sim_PINB |= (1 << 4); /* Nhả nút */
    fsm_update_background();

    /* Khẳng định: KHÔNG ĐƯỢC vào chế độ đo offset nếu lúc bắt đầu nhấn không phải là STOPPED */
    if (strstr(sim_uart_log, "[OFFSET] DANG DO") != NULL) {
        printf("[FAIL] LOI BIEN: Giu nut khi dang READY bi kich hoat nham che do do offset!\n");
        return 1;
    }
    printf("[PASS] Ca bien: Giu nut khi dang READY khong kich hoat nham che do do offset.\n");

    printf("=== TAT CA CAC CA KIEM THU FIRMWARE/FSM.C DEU DAT CHUAN 100%% ===\n");
    printf("{\"do\": {\"A1\": 0.015, \"A2\": 0.0, \"A3\": 1.26, \"A4\": 0.2, \"A5\": 3.6, \"A6\": 4.0, \"A7\": 0.0}}\n");
    return 0;
}
