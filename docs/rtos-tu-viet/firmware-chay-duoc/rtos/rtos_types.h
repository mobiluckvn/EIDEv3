/**
 * @file rtos_types.h
 * @brief Định nghĩa kiểu dữ liệu, cấu trúc TCB và giao diện nhân RTOS tiền định
 *        cho vi điều khiển ARM Cortex-M4F (STM32F469).
 */

#ifndef RTOS_TYPES_H
#define RTOS_TYPES_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================================================================= */
/* Cấu hình cơ bản của nhân RTOS (anh cho, chưa có tài liệu)                 */
/* ========================================================================= */

#define RTOS_MAX_PRIORITIES         32U   /* 32 mức ưu tiên (0: cao nhất, 31: idle) */
#define RTOS_MAX_TASKS              16U   /* Số lượng tác vụ tối đa */
#define RTOS_TICK_RATE_HZ           1000U /* Tần số nhịp SysTick 1000 Hz (chu kỳ 1 ms) */
#define RTOS_IDLE_PRIORITY          (RTOS_MAX_PRIORITIES - 1U) /* Ưu tiên 31 cho Idle task */

#define RTOS_DEFAULT_STACK_WORDS    256U  /* Stack mặc định 256 words = 1024 bytes */
#define RTOS_IDLE_STACK_WORDS       128U  /* Stack cho tác vụ Idle 128 words = 512 bytes */

/* Hằng số thanh ghi kiến trúc ARM Cortex-M4 */
#define RTOS_INITIAL_XPSR           0x01000000UL /* Thumb bit (bit 24) = 1 */
#define RTOS_EXC_RETURN_THREAD_PSP  0xFFFFFFFDUL /* Trở về Thread mode dùng PSP (khung chuẩn) */
#define RTOS_EXC_RETURN_THREAD_FPU  0xFFFFFFEDUL /* Trở về Thread mode dùng PSP (khung mở rộng FPU) */

/* ========================================================================= */
/* Trạng thái tác vụ và mã lỗi                                               */
/* ========================================================================= */

typedef enum {
    RTOS_TASK_STATE_INACTIVE = 0, /* Tác vụ chưa được tạo hoặc đã dừng */
    RTOS_TASK_STATE_READY,        /* Tác vụ sẵn sàng chạy trong hàng đợi ưu tiên */
    RTOS_TASK_STATE_RUNNING,      /* Tác vụ đang được CPU thực thi */
    RTOS_TASK_STATE_BLOCKED,      /* Tác vụ đang ngủ hoặc chờ tài nguyên IPC */
    RTOS_TASK_STATE_SUSPENDED     /* Tác vụ tạm ngưng thủ công */
} rtos_task_state_t;

typedef enum {
    RTOS_OK          =  0, /* Thành công */
    RTOS_ERR_PARAM   = -1, /* Tham số truyền vào không hợp lệ */
    RTOS_ERR_NOMEM   = -2, /* Vượt quá số lượng tác vụ cho phép */
    RTOS_ERR_FULL    = -3, /* Hàng đợi đã đầy */
    RTOS_ERR_EMPTY   = -4, /* Hàng đợi đang rỗng */
    RTOS_ERR_TIMEOUT = -5, /* Hết thời gian chờ */
    RTOS_ERR_STATE   = -6  /* Trạng thái nhân hoặc tác vụ không phù hợp */
} rtos_status_t;

/* Con trỏ hàm tác vụ */
typedef void (*rtos_task_func_t)(void *arg);

/* ========================================================================= */
/* Khung ngữ cảnh thanh ghi Cortex-M4F                                      */
/* ========================================================================= */

/* Khung do phần mềm (PendSV) lưu/khôi phục: r4-r11 và mã EXC_RETURN */
typedef struct {
    uint32_t r4;
    uint32_t r5;
    uint32_t r6;
    uint32_t r7;
    uint32_t r8;
    uint32_t r9;
    uint32_t r10;
    uint32_t r11;
    uint32_t exc_return;
} rtos_sw_frame_t;

/* Khung do phần cứng Cortex-M4 tự động lưu vào stack khi nhảy vào ngắt */
typedef struct {
    uint32_t r0;
    uint32_t r1;
    uint32_t r2;
    uint32_t r3;
    uint32_t r12;
    uint32_t lr;
    uint32_t pc;
    uint32_t xpsr;
} rtos_hw_frame_t;

/* ========================================================================= */
/* Khối điều khiển tác vụ (Task Control Block - TCB)                         */
/* ========================================================================= */

typedef struct rtos_tcb {
    volatile uint32_t *sp;           /* Con trỏ đỉnh stack hiện tại */
    uint32_t *stack_base;           /* Địa chỉ đáy stack để kiểm tra tràn */
    uint32_t stack_size_words;      /* Kích thước stack (tính theo word 32-bit) */
    uint32_t priority;              /* Mức ưu tiên: 0 (cao nhất) .. 31 (thấp nhất) */
    rtos_task_state_t state;        /* Trạng thái hiện tại của tác vụ */
    volatile uint32_t sleep_ticks;  /* Số nhịp tick còn phải chờ */
    rtos_task_func_t entry;         /* Địa chỉ hàm tác vụ */
    void *arg;                      /* Đối số truyền vào hàm */
    const char *name;               /* Tên mô tả tác vụ */
    struct rtos_tcb *next_blocked;  /* Danh sách liên kết tác vụ chờ */
} rtos_tcb_t;

/* ========================================================================= */
/* Cấu trúc hàng đợi IPC tĩnh (Queue)                                        */
/* ========================================================================= */

typedef struct {
    uint8_t *buffer;                /* Vùng nhớ tĩnh lưu dữ liệu hàng đợi */
    uint32_t item_size;             /* Kích thước mỗi phần tử (bytes) */
    uint32_t capacity;              /* Sức chứa tối đa (số lượng phần tử) */
    volatile uint32_t count;        /* Số phần tử đang có trong hàng đợi */
    uint32_t head;                  /* Vị trí đọc phần tử ra */
    uint32_t tail;                  /* Vị trí ghi phần tử vào */
    rtos_tcb_t *waiting_send;       /* Tác vụ đang đợi để gửi */
    rtos_tcb_t *waiting_recv;       /* Tác vụ đang đợi để nhận */
} rtos_queue_t;

/* ========================================================================= */
/* Khai báo giao diện API của nhân RTOS                                      */
/* ========================================================================= */

/* Khởi tạo hệ thống và quản lý tác vụ */
void rtos_init(void);

rtos_status_t rtos_task_create(
    rtos_tcb_t *tcb,
    const char *name,
    rtos_task_func_t entry,
    void *arg,
    uint32_t priority,
    uint32_t *stack,
    uint32_t stack_size_words
);

void rtos_start(void);
void rtos_yield(void);
void rtos_delay_ms(uint32_t ms);
uint32_t rtos_get_tick_count(void);
rtos_tcb_t *rtos_get_current_task(void);

/* Tầng phụ thuộc phần cứng (Port) */
uint32_t *rtos_port_stack_init(
    rtos_task_func_t entry,
    void *arg,
    uint32_t *stack_top
);

void rtos_port_start_first_task(void);
void rtos_port_trigger_pendsv(void);

/* Giao diện hàng đợi tĩnh IPC */
rtos_status_t rtos_queue_init(
    rtos_queue_t *q,
    void *buffer,
    uint32_t item_size,
    uint32_t capacity
);

rtos_status_t rtos_queue_send(
    rtos_queue_t *q,
    const void *item,
    uint32_t timeout_ticks
);

rtos_status_t rtos_queue_receive(
    rtos_queue_t *q,
    void *item,
    uint32_t timeout_ticks
);

#ifdef __cplusplus
}
#endif

#endif /* RTOS_TYPES_H */
