#include <stdint.h>

extern uint32_t _estack;
extern uint32_t _sidata;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;

extern int main(void);
extern void HAL_IncTick(void);
extern void BSP_LCD_LTDC_IRQHandler(void);
extern void BSP_LCD_LTDC_ER_IRQHandler(void);
extern void BSP_LCD_DMA2D_IRQHandler(void);
extern void BSP_LCD_DSI_IRQHandler(void);

void Reset_Handler(void);
void Default_Handler(void);

/* Cortex-M4 Core Exceptions */
void NMI_Handler(void)        __attribute__((weak, alias("Default_Handler")));
void HardFault_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void MemManage_Handler(void)  __attribute__((weak, alias("Default_Handler")));
void BusFault_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void UsageFault_Handler(void) __attribute__((weak, alias("Default_Handler")));
void SVC_Handler(void)        __attribute__((weak, alias("Default_Handler")));
void DebugMon_Handler(void)   __attribute__((weak, alias("Default_Handler")));
void PendSV_Handler(void)     __attribute__((weak, alias("Default_Handler")));

void SysTick_Handler(void) {
    HAL_IncTick();
}

/* STM32F469 Specific External Interrupts */
#define DEFINE_WEAK_IRQ(name) void name(void) __attribute__((weak, alias("Default_Handler")))

DEFINE_WEAK_IRQ(WWDG_IRQHandler);
DEFINE_WEAK_IRQ(PVD_IRQHandler);
DEFINE_WEAK_IRQ(TAMP_STAMP_IRQHandler);
DEFINE_WEAK_IRQ(RTC_WKUP_IRQHandler);
DEFINE_WEAK_IRQ(FLASH_IRQHandler);
DEFINE_WEAK_IRQ(RCC_IRQHandler);
DEFINE_WEAK_IRQ(EXTI0_IRQHandler);
DEFINE_WEAK_IRQ(EXTI1_IRQHandler);
DEFINE_WEAK_IRQ(EXTI2_IRQHandler);
DEFINE_WEAK_IRQ(EXTI3_IRQHandler);
DEFINE_WEAK_IRQ(EXTI4_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream0_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream1_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream2_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream3_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream4_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream5_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream6_IRQHandler);
DEFINE_WEAK_IRQ(ADC_IRQHandler);
DEFINE_WEAK_IRQ(CAN1_TX_IRQHandler);
DEFINE_WEAK_IRQ(CAN1_RX0_IRQHandler);
DEFINE_WEAK_IRQ(CAN1_RX1_IRQHandler);
DEFINE_WEAK_IRQ(CAN1_SCE_IRQHandler);
DEFINE_WEAK_IRQ(EXTI9_5_IRQHandler);
DEFINE_WEAK_IRQ(TIM1_BRK_TIM9_IRQHandler);
DEFINE_WEAK_IRQ(TIM1_UP_TIM10_IRQHandler);
DEFINE_WEAK_IRQ(TIM1_TRG_COM_TIM11_IRQHandler);
DEFINE_WEAK_IRQ(TIM1_CC_IRQHandler);
DEFINE_WEAK_IRQ(TIM2_IRQHandler);
DEFINE_WEAK_IRQ(TIM3_IRQHandler);
DEFINE_WEAK_IRQ(TIM4_IRQHandler);
DEFINE_WEAK_IRQ(I2C1_EV_IRQHandler);
DEFINE_WEAK_IRQ(I2C1_ER_IRQHandler);
DEFINE_WEAK_IRQ(I2C2_EV_IRQHandler);
DEFINE_WEAK_IRQ(I2C2_ER_IRQHandler);
DEFINE_WEAK_IRQ(SPI1_IRQHandler);
DEFINE_WEAK_IRQ(SPI2_IRQHandler);
DEFINE_WEAK_IRQ(USART1_IRQHandler);
DEFINE_WEAK_IRQ(USART2_IRQHandler);
DEFINE_WEAK_IRQ(USART3_IRQHandler);
DEFINE_WEAK_IRQ(EXTI15_10_IRQHandler);
DEFINE_WEAK_IRQ(RTC_Alarm_IRQHandler);
DEFINE_WEAK_IRQ(OTG_FS_WKUP_IRQHandler);
DEFINE_WEAK_IRQ(TIM8_BRK_TIM12_IRQHandler);
DEFINE_WEAK_IRQ(TIM8_UP_TIM13_IRQHandler);
DEFINE_WEAK_IRQ(TIM8_TRG_COM_TIM14_IRQHandler);
DEFINE_WEAK_IRQ(TIM8_CC_IRQHandler);
DEFINE_WEAK_IRQ(DMA1_Stream7_IRQHandler);
DEFINE_WEAK_IRQ(FMC_IRQHandler);
DEFINE_WEAK_IRQ(SDIO_IRQHandler);
DEFINE_WEAK_IRQ(TIM5_IRQHandler);
DEFINE_WEAK_IRQ(SPI3_IRQHandler);
DEFINE_WEAK_IRQ(UART4_IRQHandler);
DEFINE_WEAK_IRQ(UART5_IRQHandler);
DEFINE_WEAK_IRQ(TIM6_DAC_IRQHandler);
DEFINE_WEAK_IRQ(TIM7_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream0_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream1_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream2_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream3_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream4_IRQHandler);
DEFINE_WEAK_IRQ(ETH_IRQHandler);
DEFINE_WEAK_IRQ(ETH_WKUP_IRQHandler);
DEFINE_WEAK_IRQ(CAN2_TX_IRQHandler);
DEFINE_WEAK_IRQ(CAN2_RX0_IRQHandler);
DEFINE_WEAK_IRQ(CAN2_RX1_IRQHandler);
DEFINE_WEAK_IRQ(CAN2_SCE_IRQHandler);
DEFINE_WEAK_IRQ(OTG_FS_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream5_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream6_IRQHandler);
DEFINE_WEAK_IRQ(DMA2_Stream7_IRQHandler);
DEFINE_WEAK_IRQ(USART6_IRQHandler);
DEFINE_WEAK_IRQ(I2C3_EV_IRQHandler);
DEFINE_WEAK_IRQ(I2C3_ER_IRQHandler);
DEFINE_WEAK_IRQ(OTG_HS_EP1_OUT_IRQHandler);
DEFINE_WEAK_IRQ(OTG_HS_EP1_IN_IRQHandler);
DEFINE_WEAK_IRQ(OTG_HS_WKUP_IRQHandler);
DEFINE_WEAK_IRQ(OTG_HS_IRQHandler);
DEFINE_WEAK_IRQ(DCMI_IRQHandler);
DEFINE_WEAK_IRQ(HASH_RNG_IRQHandler);
DEFINE_WEAK_IRQ(FPU_IRQHandler);
DEFINE_WEAK_IRQ(UART7_IRQHandler);
DEFINE_WEAK_IRQ(UART8_IRQHandler);
DEFINE_WEAK_IRQ(SPI4_IRQHandler);
DEFINE_WEAK_IRQ(SPI5_IRQHandler);
DEFINE_WEAK_IRQ(SPI6_IRQHandler);
DEFINE_WEAK_IRQ(SAI1_IRQHandler);
DEFINE_WEAK_IRQ(QUADSPI_IRQHandler);

void LTDC_IRQHandler(void) {
    BSP_LCD_LTDC_IRQHandler();
}

void LTDC_ER_IRQHandler(void) {
    BSP_LCD_LTDC_ER_IRQHandler();
}

void DMA2D_IRQHandler(void) {
    BSP_LCD_DMA2D_IRQHandler();
}

void DSI_IRQHandler(void) {
    BSP_LCD_DSI_IRQHandler();
}

__attribute__((section(".isr_vector"), used))
const uint32_t *vector_table[] = {
    (uint32_t *)&_estack,
    (uint32_t *)Reset_Handler,
    (uint32_t *)NMI_Handler,
    (uint32_t *)HardFault_Handler,
    (uint32_t *)MemManage_Handler,
    (uint32_t *)BusFault_Handler,
    (uint32_t *)UsageFault_Handler,
    0, 0, 0, 0,
    (uint32_t *)SVC_Handler,
    (uint32_t *)DebugMon_Handler,
    0,
    (uint32_t *)PendSV_Handler,
    (uint32_t *)SysTick_Handler,

    /* External Interrupts (0 - 92) */
    (uint32_t *)WWDG_IRQHandler,                   /* 0 */
    (uint32_t *)PVD_IRQHandler,                    /* 1 */
    (uint32_t *)TAMP_STAMP_IRQHandler,             /* 2 */
    (uint32_t *)RTC_WKUP_IRQHandler,               /* 3 */
    (uint32_t *)FLASH_IRQHandler,                  /* 4 */
    (uint32_t *)RCC_IRQHandler,                    /* 5 */
    (uint32_t *)EXTI0_IRQHandler,                  /* 6 */
    (uint32_t *)EXTI1_IRQHandler,                  /* 7 */
    (uint32_t *)EXTI2_IRQHandler,                  /* 8 */
    (uint32_t *)EXTI3_IRQHandler,                  /* 9 */
    (uint32_t *)EXTI4_IRQHandler,                  /* 10 */
    (uint32_t *)DMA1_Stream0_IRQHandler,           /* 11 */
    (uint32_t *)DMA1_Stream1_IRQHandler,           /* 12 */
    (uint32_t *)DMA1_Stream2_IRQHandler,           /* 13 */
    (uint32_t *)DMA1_Stream3_IRQHandler,           /* 14 */
    (uint32_t *)DMA1_Stream4_IRQHandler,           /* 15 */
    (uint32_t *)DMA1_Stream5_IRQHandler,           /* 16 */
    (uint32_t *)DMA1_Stream6_IRQHandler,           /* 17 */
    (uint32_t *)ADC_IRQHandler,                    /* 18 */
    (uint32_t *)CAN1_TX_IRQHandler,                /* 19 */
    (uint32_t *)CAN1_RX0_IRQHandler,               /* 20 */
    (uint32_t *)CAN1_RX1_IRQHandler,               /* 21 */
    (uint32_t *)CAN1_SCE_IRQHandler,               /* 22 */
    (uint32_t *)EXTI9_5_IRQHandler,                /* 23 */
    (uint32_t *)TIM1_BRK_TIM9_IRQHandler,          /* 24 */
    (uint32_t *)TIM1_UP_TIM10_IRQHandler,          /* 25 */
    (uint32_t *)TIM1_TRG_COM_TIM11_IRQHandler,     /* 26 */
    (uint32_t *)TIM1_CC_IRQHandler,                /* 27 */
    (uint32_t *)TIM2_IRQHandler,                   /* 28 */
    (uint32_t *)TIM3_IRQHandler,                   /* 29 */
    (uint32_t *)TIM4_IRQHandler,                   /* 30 */
    (uint32_t *)I2C1_EV_IRQHandler,                /* 31 */
    (uint32_t *)I2C1_ER_IRQHandler,                /* 32 */
    (uint32_t *)I2C2_EV_IRQHandler,                /* 33 */
    (uint32_t *)I2C2_ER_IRQHandler,                /* 34 */
    (uint32_t *)SPI1_IRQHandler,                   /* 35 */
    (uint32_t *)SPI2_IRQHandler,                   /* 36 */
    (uint32_t *)USART1_IRQHandler,                 /* 37 */
    (uint32_t *)USART2_IRQHandler,                 /* 38 */
    (uint32_t *)USART3_IRQHandler,                 /* 39 */
    (uint32_t *)EXTI15_10_IRQHandler,              /* 40 */
    (uint32_t *)RTC_Alarm_IRQHandler,              /* 41 */
    (uint32_t *)OTG_FS_WKUP_IRQHandler,            /* 42 */
    (uint32_t *)TIM8_BRK_TIM12_IRQHandler,         /* 43 */
    (uint32_t *)TIM8_UP_TIM13_IRQHandler,          /* 44 */
    (uint32_t *)TIM8_TRG_COM_TIM14_IRQHandler,     /* 45 */
    (uint32_t *)TIM8_CC_IRQHandler,                /* 46 */
    (uint32_t *)DMA1_Stream7_IRQHandler,           /* 47 */
    (uint32_t *)FMC_IRQHandler,                    /* 48 */
    (uint32_t *)SDIO_IRQHandler,                   /* 49 */
    (uint32_t *)TIM5_IRQHandler,                   /* 50 */
    (uint32_t *)SPI3_IRQHandler,                   /* 51 */
    (uint32_t *)UART4_IRQHandler,                  /* 52 */
    (uint32_t *)UART5_IRQHandler,                  /* 53 */
    (uint32_t *)TIM6_DAC_IRQHandler,               /* 54 */
    (uint32_t *)TIM7_IRQHandler,                   /* 55 */
    (uint32_t *)DMA2_Stream0_IRQHandler,           /* 56 */
    (uint32_t *)DMA2_Stream1_IRQHandler,           /* 57 */
    (uint32_t *)DMA2_Stream2_IRQHandler,           /* 58 */
    (uint32_t *)DMA2_Stream3_IRQHandler,           /* 59 */
    (uint32_t *)DMA2_Stream4_IRQHandler,           /* 60 */
    (uint32_t *)ETH_IRQHandler,                    /* 61 */
    (uint32_t *)ETH_WKUP_IRQHandler,               /* 62 */
    (uint32_t *)CAN2_TX_IRQHandler,                /* 63 */
    (uint32_t *)CAN2_RX0_IRQHandler,               /* 64 */
    (uint32_t *)CAN2_RX1_IRQHandler,               /* 65 */
    (uint32_t *)CAN2_SCE_IRQHandler,               /* 66 */
    (uint32_t *)OTG_FS_IRQHandler,                 /* 67 */
    (uint32_t *)DMA2_Stream5_IRQHandler,           /* 68 */
    (uint32_t *)DMA2_Stream6_IRQHandler,           /* 69 */
    (uint32_t *)DMA2_Stream7_IRQHandler,           /* 70 */
    (uint32_t *)USART6_IRQHandler,                 /* 71 */
    (uint32_t *)I2C3_EV_IRQHandler,                /* 72 */
    (uint32_t *)I2C3_ER_IRQHandler,                /* 73 */
    (uint32_t *)OTG_HS_EP1_OUT_IRQHandler,         /* 74 */
    (uint32_t *)OTG_HS_EP1_IN_IRQHandler,          /* 75 */
    (uint32_t *)OTG_HS_WKUP_IRQHandler,            /* 76 */
    (uint32_t *)OTG_HS_IRQHandler,                 /* 77 */
    (uint32_t *)DCMI_IRQHandler,                   /* 78 */
    0,                                             /* 79: Reserved */
    (uint32_t *)HASH_RNG_IRQHandler,               /* 80 */
    (uint32_t *)FPU_IRQHandler,                    /* 81 */
    (uint32_t *)UART7_IRQHandler,                  /* 82 */
    (uint32_t *)UART8_IRQHandler,                  /* 83 */
    (uint32_t *)SPI4_IRQHandler,                   /* 84 */
    (uint32_t *)SPI5_IRQHandler,                   /* 85 */
    (uint32_t *)SPI6_IRQHandler,                   /* 86 */
    (uint32_t *)SAI1_IRQHandler,                   /* 87 */
    (uint32_t *)LTDC_IRQHandler,                   /* 88 */
    (uint32_t *)LTDC_ER_IRQHandler,                /* 89 */
    (uint32_t *)DMA2D_IRQHandler,                  /* 90 */
    (uint32_t *)QUADSPI_IRQHandler,                /* 91 */
    (uint32_t *)DSI_IRQHandler                     /* 92 */
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

    main();

    while (1) {}
}

void Default_Handler(void) {
    while (1) {}
}
