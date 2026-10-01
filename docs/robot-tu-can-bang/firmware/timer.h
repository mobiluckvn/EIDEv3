#ifndef TIMER_H_
#define TIMER_H_

#include <stdint.h>
#include <stdbool.h>

/* Khởi tạo Timer0 (1 kHz CTC) và Timer2 (50 kHz CTC) */
void timer_init(void);

/* Trả về số ms hệ thống từ khi khởi động */
uint32_t timer_get_ms(void);

/* Kiểm tra và xoá cờ chu kỳ vòng cân bằng 4 ms (Tầng 2) */
bool timer_check_control_flag(void);

/* Lấy số lần trễ hạn chu kỳ điều khiển Tầng 2 */
uint16_t timer_get_deadline_miss(void);

#endif /* TIMER_H_ */
