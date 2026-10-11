/**
 * @file rtos.c
 * @brief Hiện thực nhân hệ điều hành thời gian thực Preemptive cho ARM Cortex-M4F.
 * @details Cài đặt bộ lập lịch ưu tiên, chuyển ngữ cảnh thông qua PendSV naked,
 *          quản lý nhịp định thời SysTick, và quản lý khung ngăn xếp PSP an toàn FPU.
 *          Đáp ứng đặc tả ADR-01, ADR-03, ADR-04.
 */

#include "rtos.h"

/* =========================================================================
 * Địa chỉ các thanh ghi phần cứng lõi ARM Cortex-M4 / SCB / SysTick
 * ========================================================================= */
#define SYST_CSR_REG            (*(volatile uint32_t *)0xE000E010UL) /**< SysTick Control and Status */
#define SYST_RVR_REG            (*(volatile uint32_t *)0xE000E014UL) /**< SysTick Reload Value */
#define SYST_CVR_REG            (*(volatile uint32_t *)0xE000E018UL) /**< SysTick Current Value */

#define SCB_ICSR_REG            (*(volatile uint32_t *)0xE000ED04UL) /**< Interrupt Control and State */
#define SCB_SHPR3_REG           (*(volatile uint32_t *)0xE000ED20UL) /**< System Handler Priority 3 */

#define SCB_ICSR_PENDSVSET      (1UL << 28) /**< Bit kích hoạt ngắt phần mềm PendSV */

/* Mức xung nhịp lõi hệ thống HCLK trên STM32F469NIH6 = 180 MHz (tài liệu kiến trúc dòng 139) */
#define SYSTEM_CORE_CLOCK_HZ    180000000UL

/* =========================================================================
 * Biến trạng thái nội bộ của nhân RTOS
 * ========================================================================= */
static os_tcb_t *s_task_table[OS_MAX_TASKS];
static uint8_t   s_task_count = 0;
static volatile uint32_t s_tick_counter = 0;

/* Con trỏ tác vụ đang chạy (được truy cập từ hợp ngữ PendSV) */
os_tcb_t *volatile os_current_tcb = NULL;

/* =========================================================================
 * Hàm bẫy kết thúc tác vụ (Task Exit Trap)
 * ========================================================================= */
static void os_task_exit(void) {
    /* Một tác vụ không bao giờ được phép return. Nếu return, treo ở đây để tránh lỗi */
    while (1) {
        os_yield();
    }
}

/* =========================================================================
 * Khởi tạo nhân RTOS
 * ========================================================================= */
void os_init(void) {
    s_task_count = 0;
    s_tick_counter = 0;
    os_current_tcb = NULL;
    for (uint8_t i = 0; i < OS_MAX_TASKS; i++) {
        s_task_table[i] = NULL;
    }
}

/* =========================================================================
 * Đăng ký tác vụ và dựng khung ngăn xếp PSP ban đầu
 * Khung ngăn xếp được khởi tạo giả lập đúng cấu trúc sau khi bị PendSV ngắt:
 * [xPSR, PC, LR, r12, r3, r2, r1, r0] - Khung phần cứng tự động unstack
 * [EXC_RETURN, r11, r10, r9, r8, r7, r6, r5, r4] - Khung phần mềm unstack
 * ========================================================================= */
int8_t os_task_create(os_tcb_t *tcb,
                      const char *name,
                      os_task_func_t entry,
                      void *arg,
                      uint32_t *stack,
                      uint32_t stack_size_words,
                      uint32_t priority) {
    if (!tcb || !entry || !stack || stack_size_words < 64 || s_task_count >= OS_MAX_TASKS) {
        return -1;
    }

    /* Đỉnh ngăn xếp trỏ vào cuối mảng stack và căn lề 8-byte chuẩn ARM AAPCS */
    uint32_t *sp = &stack[stack_size_words];
    sp = (uint32_t *)((uintptr_t)sp & ~7UL);

    /* 1. Khung phần cứng Cortex-M4 (CPU tự unstack khi thoát ngắt) */
    *(--sp) = 0x01000000UL;             /* xPSR: bit 24 (T-bit Thumb mode) = 1 */
    *(--sp) = (uint32_t)(uintptr_t)entry; /* PC: địa chỉ bắt đầu thực thi tác vụ */
    *(--sp) = (uint32_t)(uintptr_t)os_task_exit; /* LR: hàm bẫy khi tác vụ kết thúc */
    *(--sp) = 0x12121212UL;             /* r12 */
    *(--sp) = 0x03030303UL;             /* r3 */
    *(--sp) = 0x02020202UL;             /* r2 */
    *(--sp) = 0x01010101UL;             /* r1 */
    *(--sp) = (uint32_t)(uintptr_t)arg; /* r0: tham số đầu tiên truyền vào hàm entry */

    /* 2. Khung phần mềm (PendSV unstack khi chuyển ngữ cảnh) */
    *(--sp) = 0xFFFFFFFDUL;             /* EXC_RETURN: Thread Mode, dùng PSP, chuẩn không FPU */
    *(--sp) = 0x11111111UL;             /* r11 */
    *(--sp) = 0x10101010UL;             /* r10 */
    *(--sp) = 0x09090909UL;             /* r9 */
    *(--sp) = 0x08080808UL;             /* r8 */
    *(--sp) = 0x07070707UL;             /* r7 */
    *(--sp) = 0x06060606UL;             /* r6 */
    *(--sp) = 0x05050505UL;             /* r5 */
    *(--sp) = 0x04040404UL;             /* r4 */

    /* Thiết lập các trường trong TCB */
    tcb->sp = sp;
    tcb->priority = priority;
    tcb->state = OS_TASK_READY;
    tcb->delay_ticks = 0;
    tcb->stack_base = stack;
    tcb->stack_size_words = stack_size_words;
    tcb->name = name ? name : "unnamed";

    s_task_table[s_task_count++] = tcb;
    return 0;
}

/* =========================================================================
 * Bộ lập lịch chọn tác vụ kế tiếp (Priority-based Preemptive Scheduler)
 * ========================================================================= */
void os_scheduler(void) {
    os_tcb_t *highest_tcb = NULL;
    uint32_t highest_priority = 0;

    for (uint8_t i = 0; i < s_task_count; i++) {
        os_tcb_t *t = s_task_table[i];
        if (t && t->state == OS_TASK_READY) {
            if (!highest_tcb || t->priority > highest_priority) {
                highest_tcb = t;
                highest_priority = t->priority;
            }
        }
    }

    if (highest_tcb) {
        os_current_tcb = highest_tcb;
    }
}

/* =========================================================================
 * Trình xử lý chuyển ngữ cảnh PendSV (Naked Assembly)
 * ========================================================================= */
__attribute__((naked)) void PendSV_Handler(void) {
    __asm volatile (
        "cpsid i                        \n" /* Chặn ngắt trong lúc hoán đổi TCB */
        
        /* 1. Lưu ngữ cảnh của tác vụ hiện tại (nếu đã có tác vụ chạy) */
        "ldr   r3, =os_current_tcb      \n"
        "ldr   r1, [r3]                 \n"
        "cbz   r1, 1f                   \n" /* Nếu os_current_tcb == NULL (lần đầu), nhảy tới phục hồi */
        
        "mrs   r0, psp                  \n" /* Đọc đỉnh ngăn xếp tiến trình PSP hiện thời */
        
#if defined(__ARM_FP) && (__ARM_FP > 0)
        /* Kiểm tra xem tác vụ có kích hoạt ngữ cảnh FPU hay không (bit 4 của EXC_RETURN == 0) */
        "tst   lr, #0x10                \n"
        "it    eq                       \n"
        "vstmdbeq r0!, {s16-s31}        \n" /* Lưu mở rộng s16-s31 nếu FPU đang dùng */
#endif
        
        "stmdb r0!, {r4-r11, lr}        \n" /* Lưu r4-r11 và EXC_RETURN vào ngăn xếp */
        "str   r0, [r1]                 \n" /* Ghi lại con trỏ PSP mới vào os_current_tcb->sp */
        
        /* 2. Chọn tác vụ mới qua bộ lập lịch */
        "1:                             \n"
        "push  {r3, lr}                 \n"
        "bl    os_scheduler             \n" /* os_scheduler() cập nhật os_current_tcb */
        "pop   {r3, lr}                 \n"
        
        /* 3. Phục hồi ngữ cảnh của tác vụ được chọn */
        "ldr   r1, [r3]                 \n" /* r1 = os_current_tcb */
        "ldr   r0, [r1]                 \n" /* r0 = os_current_tcb->sp */
        
        "ldmia r0!, {r4-r11, lr}        \n" /* Phục hồi r4-r11 và EXC_RETURN */
        
#if defined(__ARM_FP) && (__ARM_FP > 0)
        "tst   lr, #0x10                \n"
        "it    eq                       \n"
        "vldmiaeq r0!, {s16-s31}        \n" /* Phục hồi s16-s31 nếu tác vụ dùng FPU */
#endif
        
        "msr   psp, r0                  \n" /* Thiết lập lại PSP cho tác vụ mới */
        "cpsie i                        \n" /* Mở lại ngắt */
        "bx    lr                       \n" /* Thoát ngắt: CPU tự động unstack r0-r3, r12, lr, pc, xPSR */
    );
}

/* =========================================================================
 * Trình xử lý ngắt nhịp hệ thống SysTick
 * ========================================================================= */
void os_tick_handler(void) {
    s_tick_counter++;

    /* Cập nhật thời gian ngủ cho các tác vụ đang BLOCKED */
    uint8_t need_schedule = 0;
    for (uint8_t i = 0; i < s_task_count; i++) {
        os_tcb_t *t = s_task_table[i];
        if (t && t->state == OS_TASK_BLOCKED) {
            if (t->delay_ticks > 0) {
                t->delay_ticks--;
                if (t->delay_ticks == 0) {
                    t->state = OS_TASK_READY;
                    need_schedule = 1;
                }
            }
        }
    }

    /* Kích hoạt chuyển ngữ cảnh nếu có tác vụ thức dậy */
    if (need_schedule) {
        SCB_ICSR_REG = SCB_ICSR_PENDSVSET;
    }
}

/* =========================================================================
 * Khởi động hệ điều hành đa nhiệm
 * ========================================================================= */
void os_start(void) {
    /* 1. Thiết lập ưu tiên ngắt: PendSV thấp nhất (0xFF), SysTick (0xFE) */
    SCB_SHPR3_REG |= (0xFFUL << 16);    /* PendSV Priority = 0xFF (thấp nhất) */
    SCB_SHPR3_REG |= (0xFEUL << 24);    /* SysTick Priority = 0xFE */

    /* 2. Cấu hình SysTick Timer chu kỳ 1 ms tại xung 180 MHz */
    uint32_t reload = (SYSTEM_CORE_CLOCK_HZ / OS_TICK_RATE_HZ) - 1UL;
    SYST_RVR_REG = reload & 0x00FFFFFFUL;
    SYST_CVR_REG = 0UL;
    SYST_CSR_REG = 7UL;                 /* ENABLE=1, TICKINT=1, CLKSOURCE=1 (Core clock) */

    /* 3. Đánh thức bộ lập lịch chọn tác vụ ban đầu */
    os_current_tcb = NULL;
    SCB_ICSR_REG = SCB_ICSR_PENDSVSET;  /* Kích hoạt PendSV nạp tác vụ đầu tiên */

    /* Mở ngắt toàn cục và lặp chờ ngắt phục vụ */
    __asm volatile ("cpsie i\n");

    while (1) {
        __asm volatile ("wfi\n");
    }
}

/* =========================================================================
 * Hàm tạm dừng tác vụ có định thời
 * ========================================================================= */
void os_delay(uint32_t ticks) {
    if (ticks == 0 || !os_current_tcb) {
        return;
    }

    __asm volatile ("cpsid i\n");
    os_current_tcb->delay_ticks = ticks;
    os_current_tcb->state = OS_TASK_BLOCKED;
    SCB_ICSR_REG = SCB_ICSR_PENDSVSET;  /* Yêu cầu đổi ngữ cảnh */
    __asm volatile ("cpsie i\n");

    /* Chờ cho đến khi được đánh thức */
    while (os_current_tcb->state == OS_TASK_BLOCKED) {
        /* Chờ ngắt PendSV chuyển quyền */
    }
}

/* =========================================================================
 * Hàm chủ động nhường quyền CPU
 * ========================================================================= */
void os_yield(void) {
    SCB_ICSR_REG = SCB_ICSR_PENDSVSET;
}

/* =========================================================================
 * Đọc nhịp hệ thống
 * ========================================================================= */
uint32_t os_get_tick(void) {
    return s_tick_counter;
}
