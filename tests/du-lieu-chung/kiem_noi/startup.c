extern int main(void);
void Reset_Handler(void) { main(); for(;;){} }
void Default_Handler(void) { for(;;){} }
void NMI_Handler(void)     __attribute__((weak, alias("Default_Handler")));
void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)  __attribute__((weak, alias("Default_Handler")));
extern unsigned _estack;
__attribute__((section(".isr_vector"), used))
void *const g_vector[16] = {
    (void *)&_estack, Reset_Handler, NMI_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, 0, 0, 0, 0,
    Default_Handler, Default_Handler, 0, PendSV_Handler, SysTick_Handler,
};
