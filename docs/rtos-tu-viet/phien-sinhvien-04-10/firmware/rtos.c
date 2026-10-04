#include "rtos.h"
#if defined(__arm__)
#include "stm32f4xx.h"
extern void HAL_IncTick(void);
#endif

/* Ngắt SysTick phục vụ nhịp RTOS và nhịp HAL */
void SysTick_Handler(void) {
#if defined(__arm__)
    HAL_IncTick();
#endif
    rtos_tick();
}

/* Khởi động bộ lập lịch RTOS */
void rtos_start(void) {
    tcb_t *first = rtos_pick_next_task();
    if (!first) {
        while (1) {}
    }

#if defined(__arm__)
    /* Cấu hình ưu tiên ngắt:
     * - PendSV: Mức 15 (thấp nhất tuyệt đối) để context switch không ngắt quãng các ISR khác.
     * - SysTick: Mức 14 (hoặc 15). Đặt mức 14 để SysTick cao hơn PendSV, đảm bảo khi SysTick
     *   kích hoạt PendSV thì PendSV chỉ nổ sau khi SysTick ISR hoàn thành, không bị gián đoạn giữa chừng.
     */
    NVIC_SetPriority(PendSV_IRQn, 0x0F);
    NVIC_SetPriority(SysTick_IRQn, 0x0E);

    /* Cấu hình SysTick ở xung nhịp 180 MHz cho nhịp 1 000 Hz (1 ms):
     * Reload = 180 000 000 / 1 000 - 1 = 179 999
     */
    SysTick->LOAD = (180000000UL / 1000UL) - 1UL;
    SysTick->VAL = 0UL;
    SysTick->CTRL = SysTick_CTRL_CLKSOURCE_Msk |
                    SysTick_CTRL_TICKINT_Msk   |
                    SysTick_CTRL_ENABLE_Msk;
    /* Khởi tạo PSP = 0 để PendSV nhận biết lần chuyển ngữ cảnh đầu tiên */
    __set_PSP(0);
#endif

    /* Chuyển quyền điều khiển cho tác vụ ưu tiên cao nhất */
    rtos_yield();

#if defined(__arm__)
    /* Bật ngắt toàn cục để PendSV được phục vụ ngay */
    __enable_irq();

    while (1) {
        __WFI();
    }
#endif
}
