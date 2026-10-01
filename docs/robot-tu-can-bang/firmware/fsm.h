#ifndef FSM_H_
#define FSM_H_

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    STATE_INIT = 0,
    STATE_CALIBRATING,
    STATE_READY,
    STATE_BALANCING,
    STATE_FALLEN,
    STATE_STOPPED,
    STATE_DIAG_ANGLE, /* Chế độ kiểm dấu góc: còi bíp theo chiều nghiêng (Mục 4) */
    STATE_DIAG_MOTOR  /* Chế độ kiểm chiều động cơ: chạy tới 3 giây ở throttle chậm (Mục 6) */
} robot_state_t;

/* Kích hoạt chế độ chẩn đoán tự kiểm dấu khi giữ nút D12 lúc bật nguồn */
void fsm_enable_diagnostics(void);

/* Khởi tạo máy trạng thái và các chân ngoại vi nút bấm/còi */
void fsm_init(void);

/* Cập nhật tác vụ nền Tầng 3: quét nút nhấn D12, quản lý còi D10 */
void fsm_update_background(void);

/* Cập nhật vòng lặp điều khiển Tầng 2 (chu kỳ 4 ms) */
void fsm_update_control_4ms(void);

/* Lấy trạng thái hiện tại của robot */
robot_state_t fsm_get_state(void);

/* Lấy góc nghiêng pitch đo được gần nhất */
float fsm_get_pitch(void);

/* Lấy giá trị thô gia tốc trục trước-sau (ZOUT) gần nhất */
int16_t fsm_get_accel_z_raw(void);

/* Báo lỗi cảm biến quán tính (MPU6050) và kích hoạt mã bíp cảnh báo */
void fsm_notify_sensor_error(void);

/* Kiểm tra xem hệ thống có đang ở trạng thái lỗi cảm biến không */
bool fsm_has_sensor_error(void);

#endif /* FSM_H_ */
