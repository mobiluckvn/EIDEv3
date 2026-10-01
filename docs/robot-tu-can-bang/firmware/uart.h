#ifndef UART_H_
#define UART_H_

#include <stdint.h>
#include <stdbool.h>
#include "fsm.h"

/* Khởi tạo UART0 9.600 baud (UBRR0 = 103 @ 16 MHz, 8-N-1) kèm kéo lên nội bộ RXD (§9.1, §9.2) */
void uart_init(void);

/* Truyền một chuỗi không chặn qua bộ đệm vòng; nếu đệm đầy thì bỏ dòng và tăng biến đếm (§9.3) */
bool uart_send_line(const char *str);

/* Phát giải mã nguyên nhân khởi động lại từ thanh ghi MCUSR (§13.2 Bảng 40, BOOT-04) */
void uart_print_reset_reason(uint8_t mcusr_val);

/* Phát dòng chẩn đoán ngắn gọn (< 45 ký tự) định kỳ 100 ms đọc được bằng mắt */
void uart_send_diag_telemetry(robot_state_t state, float pitch, int16_t z_raw, int16_t thr_l, int16_t thr_r, uint16_t miss, uint16_t dropped);

/* Lấy số dòng chẩn đoán bị bỏ do đầy bộ đệm */
uint16_t uart_get_dropped_lines(void);

#endif /* UART_H_ */
