/**
 * @file rtos_core.c
 * @brief Hiện thực bộ lập lịch nhân RTOS tiền định với độ phức tạp O(1)
 *        dựa trên bitmap và lệnh đếm số 0 dẫn đầu (CLZ) trên Cortex-M4.
 */

#include "rtos_types.h"
#include "stm32f469xx.h"
#include "core_cm4.h"

/* Con trỏ tác vụ đang chạy */
volatile rtos_tcb_t *rtos_current_tcb = NULL;

/* Bảng tra cứu tác vụ theo mức ưu tiên (0 .. 31) */
static rtos_tcb_t *task_table[RTOS_MAX_PRIORITIES];

/* Bitmap biểu diễn các tác vụ đang ở trạng thái READY */
static volatile uint32_t ready_bitmap = 0;

/* Biến đếm nhịp hệ thống (SysTick counter) */
static volatile uint32_t system_ticks = 0;

/* TCB và vùng stack cho tác vụ rảnh (Idle task) */
static rtos_tcb_t idle_tcb;
static uint32_t idle_stack[RTOS_IDLE_STACK_WORDS];

/**
 * @brief Hàm thực thi của tác vụ rảnh (Idle Task).
 *        Chạy khi không có tác vụ người dùng nào ở trạng thái READY.
 */
static void rtos_idle_task_entry(void *arg)
{
    (void)arg;
    while (1) {
        __WFI(); /* Chờ ngắt để tiết kiệm năng lượng tiêu thụ */
    }
}

/**
 * @brief Khởi tạo nhân RTOS, xóa bảng tác vụ và khởi tạo tác vụ Idle.
 */
void rtos_init(void)
{
    ready_bitmap = 0;
    system_ticks = 0;
    rtos_current_tcb = NULL;

    for (uint32_t i = 0; i < RTOS_MAX_PRIORITIES; i++) {
        task_table[i] = NULL;
    }

    /* Tạo tác vụ Idle ở mức ưu tiên thấp nhất (31) */
    rtos_task_create(
        &idle_tcb,
        "IdleTask",
        rtos_idle_task_entry,
        NULL,
        RTOS_IDLE_PRIORITY,
        idle_stack,
        RTOS_IDLE_STACK_WORDS
    );
}

/**
 * @brief Tạo tác vụ mới và đưa vào danh sách sẵn sàng chạy.
 */
rtos_status_t rtos_task_create(
    rtos_tcb_t *tcb,
    const char *name,
    rtos_task_func_t entry,
    void *arg,
    uint32_t priority,
    uint32_t *stack,
    uint32_t stack_size_words
)
{
    if ((tcb == NULL) || (entry == NULL) || (stack == NULL)) {
        return RTOS_ERR_PARAM;
    }

    if (priority >= RTOS_MAX_PRIORITIES) {
        return RTOS_ERR_PARAM;
    }

    /* Kiểm tra xem mức ưu tiên này đã có tác vụ nào đăng ký chưa */
    if (task_table[priority] != NULL) {
        return RTOS_ERR_NOMEM;
    }

    /* Điền thông tin vào khối điều khiển tác vụ TCB */
    tcb->stack_base = stack;
    tcb->stack_size_words = stack_size_words;
    tcb->priority = priority;
    tcb->state = RTOS_TASK_STATE_READY;
    tcb->sleep_ticks = 0;
    tcb->entry = entry;
    tcb->arg = arg;
    tcb->name = name;
    tcb->next_blocked = NULL;

    /* Khởi tạo khung stack ban đầu */
    uint32_t *stack_top = stack + stack_size_words;
    tcb->sp = rtos_port_stack_init(entry, arg, stack_top);

    /* Đăng ký tác vụ vào bảng quản lý */
    task_table[priority] = tcb;

    /* Bật bit sẵn sàng trong bitmap O(1): bit 31 tương ứng ưu tiên 0 */
    uint32_t primask = __get_PRIMASK();
    __disable_irq();
    ready_bitmap |= (1UL << (31U - priority));
    __set_PRIMASK(primask);

    return RTOS_OK;
}

/**
 * @brief Hàm điều phối tác vụ O(1), được gọi bởi ngắt PendSV.
 *        Tìm tác vụ có mức ưu tiên cao nhất đang READY bằng lệnh phần cứng CLZ.
 */
void rtos_core_switch_context(void)
{
    if (ready_bitmap != 0) {
        /* Đếm số số 0 ở đầu để tìm mức ưu tiên cao nhất trong O(1) */
        uint32_t highest_prio = (uint32_t)__CLZ(ready_bitmap);
        if (highest_prio < RTOS_MAX_PRIORITIES) {
            rtos_current_tcb = task_table[highest_prio];
            rtos_current_tcb->state = RTOS_TASK_STATE_RUNNING;
        }
    }
}

/**
 * @brief Khởi động bộ lập lịch RTOS và chuyển quyền điều khiển cho tác vụ đầu tiên.
 */
void rtos_start(void)
{
    rtos_core_switch_context();
    rtos_port_start_first_task();
}

/**
 * @brief Tự nguyện nhường quyền CPU cho tác vụ khác.
 */
void rtos_yield(void)
{
    rtos_port_trigger_pendsv();
}

/**
 * @brief Tạm dừng tác vụ hiện tại trong khoảng thời gian xác định (ms).
 */
void rtos_delay_ms(uint32_t ms)
{
    if (ms == 0) {
        rtos_yield();
        return;
    }

    uint32_t primask = __get_PRIMASK();
    __disable_irq();

    if (rtos_current_tcb != NULL) {
        rtos_current_tcb->sleep_ticks = ms;
        rtos_current_tcb->state = RTOS_TASK_STATE_BLOCKED;

        /* Xóa cờ READY trong bitmap */
        ready_bitmap &= ~(1UL << (31U - rtos_current_tcb->priority));
    }

    __set_PRIMASK(primask);

    /* Kích hoạt chuyển ngữ cảnh sang tác vụ khác */
    rtos_port_trigger_pendsv();
}

/**
 * @brief Trình xử lý nhịp SysTick từ rtos_port, cập nhật trạng thái ngủ của các tác vụ.
 */
void rtos_core_tick_handler(void)
{
    system_ticks++;
    bool need_reschedule = false;

    for (uint32_t i = 0; i < RTOS_MAX_PRIORITIES; i++) {
        rtos_tcb_t *tcb = task_table[i];
        if ((tcb != NULL) && (tcb->state == RTOS_TASK_STATE_BLOCKED)) {
            if (tcb->sleep_ticks > 0) {
                tcb->sleep_ticks--;
                if (tcb->sleep_ticks == 0) {
                    /* Tác vụ đã hết thời gian chờ, đưa về trạng thái READY */
                    tcb->state = RTOS_TASK_STATE_READY;
                    ready_bitmap |= (1UL << (31U - tcb->priority));

                    /* Nếu tác vụ thức dậy có mức ưu tiên cao hơn tác vụ hiện tại */
                    if ((rtos_current_tcb == NULL) || (tcb->priority < rtos_current_tcb->priority)) {
                        need_reschedule = true;
                    }
                }
            }
        }
    }

    if (need_reschedule) {
        rtos_port_trigger_pendsv();
    }
}

/**
 * @brief Lấy số nhịp tick tích lũy từ lúc khởi động.
 */
uint32_t rtos_get_tick_count(void)
{
    return system_ticks;
}

/**
 * @brief Lấy con trỏ TCB của tác vụ hiện thời.
 */
rtos_tcb_t *rtos_get_current_task(void)
{
    return (rtos_tcb_t *)rtos_current_tcb;
}
