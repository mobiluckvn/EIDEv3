#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

int main(void);
extern void SystemInit(void);

void Reset_Handler(void);
void Default_Handler(void) {
    while (1) {}
}

void NMI_Handler(void) __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void) __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void) __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void) __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")));

__attribute__((section(".isr_vector"), used))
const uint32_t * const isr_vector[] = {
    (const uint32_t *)&_estack,
    (const uint32_t *)Reset_Handler,
    (const uint32_t *)NMI_Handler,
    (const uint32_t *)HardFault_Handler,
    (const uint32_t *)MemManage_Handler,
    (const uint32_t *)BusFault_Handler,
    (const uint32_t *)UsageFault_Handler,
    0, 0, 0, 0,
    (const uint32_t *)SVC_Handler,
    (const uint32_t *)DebugMon_Handler,
    0,
    (const uint32_t *)PendSV_Handler,
    (const uint32_t *)SysTick_Handler,
};

void Reset_Handler(void) {
    uint32_t *src = &_sidata;
    uint32_t *dst = &_sdata;
    while (dst < &_edata) {
        *dst++ = *src++;
    }

    dst = &_sbss;
    while (dst < &_ebss) {
        *dst++ = 0;
    }

    SystemInit();

    main();

    while (1) {}
}
