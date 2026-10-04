#ifndef RTOS_H
#define RTOS_H

#include <stdint.h>
#include <stdbool.h>

#define RTOS_MAX_PRIORITIES 32
#define RTOS_IDLE_PRIORITY   0
#define RTOS_MAX_TASKS      16

typedef enum {
    TASK_READY = 0,
    TASK_RUNNING,
    TASK_BLOCKED,
    TASK_SUSPENDED
} task_state_t;

/* Cấu trúc mô tả tác vụ (TCB)
 * CHÚ Ý: Trường sp BẮT BUỘC ở offset 0 để PendSV truy cập trực tiếp bằng một lệnh LDR/STR.
 */
typedef struct tcb {
    uint32_t        *sp;          /* [Offset 0] Đỉnh ngăn xếp hiện tại (PSP) */
    task_state_t     state;       /* Trạng thái tác vụ */
    uint8_t          priority;    /* Mức ưu tiên tĩnh: 0 (thấp nhất) đến 31 (cao nhất) */
    uint32_t         delay_ticks; /* Số nhịp tick còn chờ trễ hoặc timeout */
    uint32_t        *stack_base;  /* Địa chỉ đáy ngăn xếp để kiểm tra tràn */
    uint32_t         stack_size;  /* Kích thước ngăn xếp (tính bằng word) */
    const char      *name;        /* Tên tác vụ để nhận diện và giám sát */
    void            *waiting_on;  /* Đối tượng hàng đợi đang chờ (nếu có) */
    bool             timed_out;   /* Đánh dấu kết quả chờ bị hết hạn */
    struct tcb      *next;        /* Con trỏ liên kết danh sách */
} tcb_t;

/* Cấu trúc hàng đợi tĩnh (Queue) */
typedef struct {
    uint8_t         *buffer;      /* Vùng nhớ tĩnh cấp phát trước */
    uint32_t         item_size;   /* Kích thước một phần tử (byte) */
    uint32_t         max_items;   /* Dung lượng tối đa phần tử */
    uint32_t         head;        /* Chỉ số ghi phần tử tiếp theo */
    uint32_t         tail;        /* Chỉ số đọc phần tử tiếp theo */
    uint32_t         count;       /* Số phần tử hiện có trong hàng đợi */
    tcb_t           *waiting_send;/* Tác vụ đang chờ gửi khi hàng đợi đầy */
    tcb_t           *waiting_recv;/* Tác vụ đang chờ nhận khi hàng đợi rỗng */
} rtos_queue_t;

/* Khởi tạo nhân */
void rtos_init(void);

/* Tạo tác vụ mới */
bool rtos_task_create(tcb_t *tcb, const char *name, void (*entry)(void *), void *arg,
                      uint8_t priority, uint32_t *stack, uint32_t stack_size);

/* Khởi động bộ lập lịch */
void rtos_start(void);

/* Trễ tác vụ một khoảng thời gian (tính bằng mili-giây / tick) */
void rtos_delay_ms(uint32_t ms);

/* Chủ động nhường CPU cho tác vụ khác */
void rtos_yield(void);

/* Xử lý nhịp thời gian hệ thống (gọi từ SysTick hoặc bộ giả lập) */
void rtos_tick(void);

/* Khởi tạo hàng đợi tĩnh */
void rtos_queue_init(rtos_queue_t *q, void *buffer, uint32_t item_size, uint32_t max_items);

/* Gửi tin nhắn vào hàng đợi (timeout_ticks = 0: không chờ, 0xFFFFFFFF: chờ vô tận) */
bool rtos_queue_send(rtos_queue_t *q, const void *item, uint32_t timeout_ticks);

/* Nhận tin nhắn từ hàng đợi (timeout_ticks = 0: không chờ, 0xFFFFFFFF: chờ vô tận) */
bool rtos_queue_receive(rtos_queue_t *q, void *item, uint32_t timeout_ticks);

/* Các hàm tra cứu và kiểm thử bộ lập lịch */
tcb_t *rtos_get_current_task(void);
tcb_t *rtos_pick_next_task(void);
uint32_t rtos_get_ready_map(void);

/* Quản lý vùng găng */
void rtos_enter_critical(void);
void rtos_exit_critical(void);

/* Quản lý và giám sát ngăn xếp */
#define RTOS_STACK_PAINT_PATTERN 0xA5A5A5A5UL

/* Trả về số word chưa chạm tới tính từ đáy ngăn xếp (watermark) */
uint32_t rtos_task_get_stack_watermark(const tcb_t *tcb);

/* Trả về số word đã sử dụng tối đa */
uint32_t rtos_task_get_stack_used_words(const tcb_t *tcb);

#endif /* RTOS_H */
