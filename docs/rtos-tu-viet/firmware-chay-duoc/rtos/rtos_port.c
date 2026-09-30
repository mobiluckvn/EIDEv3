/**
 * @file rtos_port.c
 * @brief Hiện thực tầng phụ thuộc phần cứng (Port) cho ARM Cortex-M4F (STM32F469).
 *        Bao gồm khởi tạo stack tác vụ, trình xử lý chuyển ngữ cảnh PendSV
 *        và trình đếm nhịp hệ thống SysTick.
 */

#include "rtos_types.h"
#include "stm32f469xx.h"
#include "core_cm4.h"

/* Biến tham chiếu từ lõi điều phối rtos_core.c */
extern volatile rtos_tcb_t *rtos_current_tcb;
extern void rtos_core_switch_context(void);
extern void rtos_core_tick_handler(void);

/* Tần số xung nhịp hệ thống định nghĩa từ vendor/system_stm32f4xx.c */
extern uint32_t SystemCoreClock;

/**
 * @brief Hàm bẫy nếu một tác vụ kết thúc mà không tự hủy.
 */
static void rtos_task_exit_handler(void)
{
    while (1) {
        __WFI();
    }
}

/**
 * @brief Khởi tạo khung stack ban đầu cho tác vụ theo kiến trúc Cortex-M4F.
 *
 * @param entry Địa chỉ hàm tác vụ
 * @param arg Đối số truyền vào hàm tác vụ
 * @param stack_top Đỉnh stack cấp phát cho tác vụ
 * @return uint32_t* Con trỏ stack sau khi đã bố trí khung thanh ghi
 */
uint32_t *rtos_port_stack_init(
    rtos_task_func_t entry,
    void *arg,
    uint32_t *stack_top
)
{
    /* Căn lề stack về ranh giới 8-byte (AAPCS) */
    uint32_t *sp = (uint32_t *)((uint32_t)stack_top & ~0x7UL);

    /* ------------------------------------------------------------- */
    /* 1. Khung phần cứng tự động unstack khi thoát ngắt (8 words)   */
    /* ------------------------------------------------------------- */
    *(--sp) = RTOS_INITIAL_XPSR;                 /* xPSR: Thumb mode bit 24 = 1 */
    *(--sp) = (uint32_t)entry;                   /* PC: địa chỉ bắt đầu của tác vụ */
    *(--sp) = (uint32_t)rtos_task_exit_handler;  /* LR: hàm đón nếu tác vụ return */
    *(--sp) = 0x12121212UL;                      /* R12 */
    *(--sp) = 0x03030303UL;                      /* R3 */
    *(--sp) = 0x02020202UL;                      /* R2 */
    *(--sp) = 0x01010101UL;                      /* R1 */
    *(--sp) = (uint32_t)arg;                     /* R0: tham số truyền vào hàm */

    /* ------------------------------------------------------------- */
    /* 2. Khung phần mềm được PendSV lưu và khôi phục (9 words)      */
    /* ------------------------------------------------------------- */
    *(--sp) = RTOS_EXC_RETURN_THREAD_PSP;        /* EXC_RETURN: Thread mode, dùng PSP */
    *(--sp) = 0x11111111UL;                      /* R11 */
    *(--sp) = 0x10101010UL;                      /* R10 */
    *(--sp) = 0x09090909UL;                      /* R9 */
    *(--sp) = 0x08080808UL;                      /* R8 */
    *(--sp) = 0x07070707UL;                      /* R7 */
    *(--sp) = 0x06060606UL;                      /* R6 */
    *(--sp) = 0x05050505UL;                      /* R5 */
    *(--sp) = 0x04040404UL;                      /* R4 */

    return sp;
}

/**
 * @brief Kích hoạt ngắt mềm PendSV để yêu cầu đổi ngữ cảnh.
 */
void rtos_port_trigger_pendsv(void)
{
    SCB->ICSR = SCB_ICSR_PENDSVSET_Msk;
}

/**
 * @brief Khởi động tác vụ đầu tiên và bật bộ định thời SysTick.
 */
void rtos_port_start_first_task(void)
{
    /* Đặt mức ưu tiên thấp nhất (0xFF) cho PendSV và SysTick */
    NVIC_SetPriority(PendSV_IRQn, 0xFF);
    NVIC_SetPriority(SysTick_IRQn, 0xFF);

    /* Cấu hình chu kỳ SysTick tạo ngắt mỗi 1 ms */
    SysTick_Config(SystemCoreClock / RTOS_TICK_RATE_HZ);

    /* Đặt PSP về 0 để PendSV nhận diện lần chuyển ngữ cảnh đầu tiên */
    __set_PSP(0);

    /* Kích hoạt PendSV để tải ngữ cảnh của tác vụ có mức ưu tiên cao nhất */
    rtos_port_trigger_pendsv();

    /* Bật ngắt toàn cục và rào cản lệnh */
    __enable_irq();
    __ISB();
    __DSB();

    /* Chờ chuyển ngữ cảnh */
    while (1) {
        __WFI();
    }
}

/**
 * @brief Trình xử lý ngắt SysTick, phục vụ đếm tick và giải tỏa tác vụ ngủ.
 */
void SysTick_Handler(void)
{
    rtos_core_tick_handler();
}

/**
 * @brief Trình chuyển ngữ cảnh PendSV bằng hợp ngữ cho Cortex-M4F.
 *        Hỗ trợ lưu/khôi phục ngữ cảnh chuẩn (r4-r11) và FPU lazy stacking (s16-s31).
 */
__attribute__((naked)) void PendSV_Handler(void)
{
    __asm volatile (
        "cpsid i                         \n" /* Tắt ngắt để bảo vệ dữ liệu nhân */
        "mrs   r0, psp                   \n" /* Đọc con trỏ stack hiện tại của tác vụ */
        "cbz   r0, pendsv_restore        \n" /* Nếu PSP == 0, bỏ qua lưu (lần chạy đầu) */

        /* Kiểm tra tác vụ hiện thời có sử dụng FPU không (bit 4 của EXC_RETURN lr) */
        "tst   lr, #0x10                 \n"
        "it    eq                        \n"
        "vstmdbeq r0!, {s16-s31}         \n" /* Lưu s16-s31 nếu có ngữ cảnh FPU */

        /* Lưu các thanh ghi phần mềm r4-r11 cùng EXC_RETURN */
        "stmdb r0!, {r4-r11, lr}         \n"

        /* Lưu đỉnh stack mới vào TCB của tác vụ hiện thời */
        "ldr   r1, =rtos_current_tcb     \n"
        "ldr   r1, [r1]                  \n"
        "str   r0, [r1]                  \n"

    "pendsv_restore:                     \n"
        /* Gọi bộ lập lịch để cập nhật rtos_current_tcb sang tác vụ tiếp theo */
        "bl    rtos_core_switch_context  \n"

        /* Nạp con trỏ stack từ TCB của tác vụ mới */
        "ldr   r1, =rtos_current_tcb     \n"
        "ldr   r1, [r1]                  \n"
        "ldr   r0, [r1]                  \n"

        /* Khôi phục r4-r11 và EXC_RETURN */
        "ldmia r0!, {r4-r11, lr}         \n"

        /* Khôi phục ngữ cảnh FPU nếu tác vụ mới có kích hoạt FPU */
        "tst   lr, #0x10                 \n"
        "it    eq                        \n"
        "vldmiaeq r0!, {s16-s31}         \n"

        /* Cập nhật lại thanh ghi PSP */
        "msr   psp, r0                   \n"
        "cpsie i                         \n" /* Bật lại ngắt */
        "bx    lr                        \n" /* Trở về Thread mode qua EXC_RETURN */
    );
}
