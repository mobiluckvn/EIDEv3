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
    STATE_STOPPED
} robot_state_t;

/* Khởi tạo máy trạng thái và các chân ngoại vi nút bấm/còi */
void fsm_init(void);

/* Cập nhật tác vụ nền Tầng 3: quét nút nhấn D12, quản lý còi D10 */
void fsm_update_background(void);

/* Cập nhật vòng lặp điều khiển Tầng 2 (chu kỳ 4 ms) */
void fsm_update_control_4ms(void);

/* Lấy trạng thái hiện tại của robot */
robot_state_t fsm_get_state(void);

#endif /* FSM_H_ */
