#include "rtos.h"

#ifndef RTOS_WEAK
#define RTOS_WEAK
#endif

#if defined(UNIT_TEST) || !defined(__arm__)
#include <string.h>
volatile uint32_t mock_scb_icsr = 0;
#define SCB_ICSR_REG mock_scb_icsr
#else
#include "stm32f4xx.h"
#define SCB_ICSR_REG (*(volatile uint32_t *)0xE000ED04UL)
static void *rtos_memcpy(void *dst, const void *src, uint32_t n) {
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) {
        *d++ = *s++;
    }
    return dst;
}
#define memcpy rtos_memcpy
#endif

#define SCB_ICSR_PENDSVSET_BIT (1UL << 28)

tcb_t *current_tcb = 0;
tcb_t *ready_table[RTOS_MAX_PRIORITIES];
uint32_t ready_map = 0;
static tcb_t *task_list = 0;
static uint32_t critical_nesting = 0;

RTOS_WEAK void rtos_enter_critical(void) {
#if defined(__arm__)
    __disable_irq();
#endif
    critical_nesting++;
}

RTOS_WEAK void rtos_exit_critical(void) {
    if (critical_nesting > 0) {
        critical_nesting--;
#if defined(__arm__)
        if (critical_nesting == 0) {
            __enable_irq();
        }
#endif
    }
}

uint32_t rtos_first_switch = 1;

#define RTOS_IDLE_STACK_WORDS 128
static uint32_t rtos_idle_stack[RTOS_IDLE_STACK_WORDS];
static tcb_t rtos_idle_tcb;

static void rtos_idle_task(void *arg) {
    (void)arg;
    while (1) {
#if defined(__arm__)
        __WFI();
#else
        break;
#endif
    }
}

RTOS_WEAK void rtos_init(void) {
    current_tcb = 0;
    ready_map = 0;
    task_list = 0;
    critical_nesting = 0;
    rtos_first_switch = 1;
    for (uint32_t i = 0; i < RTOS_MAX_PRIORITIES; i++) {
        ready_table[i] = 0;
    }
    rtos_task_create(&rtos_idle_tcb, "Idle", rtos_idle_task, 0,
                     RTOS_IDLE_PRIORITY, rtos_idle_stack, RTOS_IDLE_STACK_WORDS);
}

RTOS_WEAK tcb_t *rtos_get_current_task(void) {
    return current_tcb;
}

RTOS_WEAK uint32_t rtos_get_ready_map(void) {
    return ready_map;
}

RTOS_WEAK tcb_t *rtos_pick_next_task(void) {
    if (ready_map == 0) {
        return 0;
    }
    /* Đếm số bit 0 từ MSB để tìm mức ưu tiên cao nhất trong ready_map */
    uint32_t lz = (uint32_t)__builtin_clz(ready_map);
    uint32_t highest_prio = (RTOS_MAX_PRIORITIES - 1) - lz;
    return ready_table[highest_prio];
}

RTOS_WEAK void rtos_yield(void) {
    SCB_ICSR_REG = SCB_ICSR_PENDSVSET_BIT;
#if defined(__arm__)
    __asm__ volatile ("dsb \n isb" ::: "memory");
#else
    tcb_t *next = rtos_pick_next_task();
    if (next != 0) {
        current_tcb = next;
    }
#endif
}

RTOS_WEAK bool rtos_task_create(tcb_t *tcb, const char *name, void (*entry)(void *), void *arg,
                                uint8_t priority, uint32_t *stack, uint32_t stack_size) {
    if (!tcb || !entry || !stack || stack_size < RTOS_MAX_PRIORITIES || priority >= RTOS_MAX_PRIORITIES) {
        return false;
    }

    tcb->name = name;
    tcb->priority = priority;
    (void)arg;
    tcb->state = TASK_READY;
    tcb->delay_ticks = 0;
    tcb->stack_base = stack;
    tcb->stack_size = stack_size;
    tcb->waiting_on = 0;
    tcb->timed_out = false;

    /* Sơn ngăn xếp để theo dõi mức nước sử dụng tối đa */
    for (uint32_t i = 0; i < stack_size; i++) {
        stack[i] = RTOS_STACK_PAINT_PATTERN;
    }

    /* Khởi tạo con trỏ ngăn xếp đỉnh */
    uint32_t *sp = &stack[stack_size];
    sp = (uint32_t *)((uintptr_t)sp & ~(uintptr_t)7);

    /* Khung phần cứng tự động pop khi thoát exception: */
    *(--sp) = (1UL << 24);                /* xPSR: bit 24 (Thumb) */
    *(--sp) = (uint32_t)(uintptr_t)entry; /* PC */
    *(--sp) = 0;                          /* LR */
    *(--sp) = 0;                          /* R12 */
    *(--sp) = 0;                          /* R3 */
    *(--sp) = 0;                          /* R2 */
    *(--sp) = 0;                          /* R1 */
    *(--sp) = (uint32_t)(uintptr_t)arg;   /* R0 */

    /* Khung phần mềm PendSV lưu: EXC_RETURN, R11 - R4 */
    *(--sp) = 0xFFFFFFFDU;                /* EXC_RETURN */
    *(--sp) = 0;                          /* R11 */
    *(--sp) = 0;                          /* R10 */
    *(--sp) = 0;                          /* R9 */
    *(--sp) = 0;                          /* R8 */
    *(--sp) = 0;                          /* R7 */
    *(--sp) = 0;                          /* R6 */
    *(--sp) = 0;                          /* R5 */
    *(--sp) = 0;                          /* R4 */

    tcb->sp = sp;

    rtos_enter_critical();

    ready_table[priority] = tcb;
    ready_map |= (1UL << priority);

    tcb->next = task_list;
    task_list = tcb;

    if (current_tcb == 0) {
        current_tcb = tcb;
    } else {
        /* Tiền định: nếu tác vụ mới có mức ưu tiên cao hơn tác vụ hiện tại */
        if (priority > current_tcb->priority) {
            current_tcb = tcb;
        }
    }

    rtos_exit_critical();
    return true;
}

RTOS_WEAK void rtos_delay_ms(uint32_t ms) {
    if (ms == 0) {
        rtos_yield();
        return;
    }

    rtos_enter_critical();
    if (current_tcb != 0) {
        ready_map &= ~(1UL << current_tcb->priority);
        current_tcb->state = TASK_BLOCKED;
        current_tcb->delay_ticks = ms;
    }
    rtos_exit_critical();

    rtos_yield();
}

RTOS_WEAK void rtos_tick(void) {
    rtos_enter_critical();

    tcb_t *curr = task_list;
    bool need_resched = false;

    while (curr) {
        if (curr->state == TASK_BLOCKED && curr->delay_ticks > 0) {
            curr->delay_ticks--;
            if (curr->delay_ticks == 0) {
                if (curr->waiting_on != 0) {
                    curr->timed_out = true;
                    curr->waiting_on = 0;
                }
                curr->state = TASK_READY;
                ready_table[curr->priority] = curr;
                ready_map |= (1UL << curr->priority);
                need_resched = true;
            }
        }
        curr = curr->next;
    }

    rtos_exit_critical();

    if (need_resched) {
        rtos_yield();
    }
}

RTOS_WEAK void rtos_queue_init(rtos_queue_t *q, void *buffer, uint32_t item_size, uint32_t max_items) {
    if (!q || !buffer || item_size == 0 || max_items == 0) {
        return;
    }
    q->buffer = (uint8_t *)buffer;
    q->item_size = item_size;
    q->max_items = max_items;
    q->head = 0;
    q->tail = 0;
    q->count = 0;
    q->waiting_send = 0;
    q->waiting_recv = 0;
}

RTOS_WEAK bool rtos_queue_send(rtos_queue_t *q, const void *item, uint32_t timeout_ticks) {
    if (!q || !item) {
        return false;
    }

    rtos_enter_critical();

    if (q->count < q->max_items) {
        uint8_t *dst = q->buffer + (q->head * q->item_size);
        memcpy(dst, item, q->item_size);
        q->head = (q->head + 1) % q->max_items;
        q->count++;

        if (q->waiting_recv != 0) {
            tcb_t *w = q->waiting_recv;
            q->waiting_recv = 0;
            w->waiting_on = 0;
            w->timed_out = false;
            w->state = TASK_READY;
            ready_table[w->priority] = w;
            ready_map |= (1UL << w->priority);
        }

        rtos_exit_critical();
        rtos_yield();
        return true;
    }

    if (timeout_ticks == 0 || current_tcb == 0) {
        rtos_exit_critical();
        return false;
    }

    q->waiting_send = current_tcb;
    current_tcb->waiting_on = q;
    current_tcb->timed_out = false;
    current_tcb->delay_ticks = timeout_ticks;
    current_tcb->state = TASK_BLOCKED;
    ready_map &= ~(1UL << current_tcb->priority);

    rtos_exit_critical();
    rtos_yield();

    if (current_tcb->timed_out) {
        return false;
    }

    rtos_enter_critical();
    if (q->count < q->max_items) {
        uint8_t *dst = q->buffer + (q->head * q->item_size);
        memcpy(dst, item, q->item_size);
        q->head = (q->head + 1) % q->max_items;
        q->count++;
        rtos_exit_critical();
        return true;
    }
    rtos_exit_critical();
    return false;
}

RTOS_WEAK bool rtos_queue_receive(rtos_queue_t *q, void *item, uint32_t timeout_ticks) {
    if (!q || !item) {
        return false;
    }

    rtos_enter_critical();

    if (q->count > 0) {
        const uint8_t *src = q->buffer + (q->tail * q->item_size);
        memcpy(item, src, q->item_size);
        q->tail = (q->tail + 1) % q->max_items;
        q->count--;

        if (q->waiting_send != 0) {
            tcb_t *w = q->waiting_send;
            q->waiting_send = 0;
            w->waiting_on = 0;
            w->timed_out = false;
            w->state = TASK_READY;
            ready_table[w->priority] = w;
            ready_map |= (1UL << w->priority);
        }

        rtos_exit_critical();
        rtos_yield();
        return true;
    }

    if (timeout_ticks == 0 || current_tcb == 0) {
        rtos_exit_critical();
        return false;
    }

    q->waiting_recv = current_tcb;
    current_tcb->waiting_on = q;
    current_tcb->timed_out = false;
    current_tcb->delay_ticks = timeout_ticks;
    current_tcb->state = TASK_BLOCKED;
    ready_map &= ~(1UL << current_tcb->priority);

    rtos_exit_critical();
    rtos_yield();

    if (current_tcb->timed_out) {
        return false;
    }

    rtos_enter_critical();
    if (q->count > 0) {
        const uint8_t *src = q->buffer + (q->tail * q->item_size);
        memcpy(item, src, q->item_size);
        q->tail = (q->tail + 1) % q->max_items;
        q->count--;
        rtos_exit_critical();
        return true;
    }
    rtos_exit_critical();
    return false;
}

RTOS_WEAK uint32_t rtos_task_get_stack_watermark(const tcb_t *tcb) {
    if (!tcb || !tcb->stack_base || tcb->stack_size == 0) {
        return 0;
    }
    uint32_t unused = 0;
    for (uint32_t i = 0; i < tcb->stack_size; i++) {
        if (tcb->stack_base[i] == RTOS_STACK_PAINT_PATTERN) {
            unused++;
        } else {
            break;
        }
    }
    return unused;
}

RTOS_WEAK uint32_t rtos_task_get_stack_used_words(const tcb_t *tcb) {
    if (!tcb) {
        return 0;
    }
    uint32_t unused = rtos_task_get_stack_watermark(tcb);
    return (tcb->stack_size >= unused) ? (tcb->stack_size - unused) : tcb->stack_size;
}

#if !defined(UNIT_TEST) && defined(__arm__)
__attribute__((naked)) void PendSV_Handler(void) {
    __asm__ volatile (
        "cpsid i                                \n"
        "ldr r1, =rtos_first_switch             \n"
        "ldr r2, [r1]                           \n"
        "cbz r2, 2f                             \n"
        "movs r2, #0                            \n"
        "str r2, [r1]                           \n"
        "b 1f                                   \n"
        "2:                                     \n"
        "mrs r0, psp                            \n"
        "isb                                    \n"
        "tst lr, #0x10                          \n"
        "it eq                                  \n"
        "vstmdbeq r0!, {s16-s31}                \n"
        "stmdb r0!, {r4-r11, lr}                \n"
        "ldr r1, =current_tcb                   \n"
        "ldr r2, [r1]                           \n"
        "str r0, [r2]                           \n"
        "1:                                     \n"
        "push {lr}                              \n"
        "bl rtos_pick_next_task                 \n"
        "pop {lr}                               \n"
        "cbz r0, 3f                             \n"
        "ldr r1, =current_tcb                   \n"
        "str r0, [r1]                           \n"
        "ldr r0, [r0]                           \n"
        "ldmia r0!, {r4-r11, lr}                \n"
        "tst lr, #0x10                          \n"
        "it eq                                  \n"
        "vldmiaeq r0!, {s16-s31}                \n"
        "msr psp, r0                            \n"
        "isb                                    \n"
        "3:                                     \n"
        "cpsie i                                \n"
        "bx lr                                  \n"
        ::: "memory"
    );
}
#endif

