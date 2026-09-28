#ifndef STM32F469XX_H
#define STM32F469XX_H

#include <stdint.h>

/* Base memory addresses */
#define PERIPH_BASE           (0x40000000UL)
#define AHB1PERIPH_BASE       (PERIPH_BASE + 0x00020000UL)

/* RCC peripheral */
#define RCC_BASE              (AHB1PERIPH_BASE + 0x3800UL)

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t PLLCFGR;
    volatile uint32_t CFGR;
    volatile uint32_t CIR;
    volatile uint32_t AHB1RSTR;
    volatile uint32_t AHB2RSTR;
    volatile uint32_t AHB3RSTR;
    uint32_t RESERVED0;
    volatile uint32_t APB1RSTR;
    volatile uint32_t APB2RSTR;
    uint32_t RESERVED1[2];
    volatile uint32_t AHB1ENR;
    volatile uint32_t AHB2ENR;
    volatile uint32_t AHB3ENR;
    uint32_t RESERVED2;
    volatile uint32_t APB1ENR;
    volatile uint32_t APB2ENR;
} RCC_TypeDef;

#define RCC                   ((RCC_TypeDef *) RCC_BASE)

#define RCC_AHB1ENR_GPIOAEN   (1UL << 0)
#define RCC_AHB1ENR_GPIODEN   (1UL << 3)
#define RCC_AHB1ENR_GPIOGEN   (1UL << 6)
#define RCC_AHB1ENR_GPIOKEN   (1UL << 10)

/* GPIO peripheral */
typedef struct {
    volatile uint32_t MODER;
    volatile uint32_t OTYPER;
    volatile uint32_t OSPEEDR;
    volatile uint32_t PUPDR;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t LCKR;
    volatile uint32_t AFR[2];
} GPIO_TypeDef;

#define GPIOA_BASE            (AHB1PERIPH_BASE + 0x0000UL)
#define GPIOD_BASE            (AHB1PERIPH_BASE + 0x0C00UL)
#define GPIOG_BASE            (AHB1PERIPH_BASE + 0x1800UL)
#define GPIOK_BASE            (AHB1PERIPH_BASE + 0x2800UL)

#define GPIOA                 ((GPIO_TypeDef *) GPIOA_BASE)
#define GPIOD                 ((GPIO_TypeDef *) GPIOD_BASE)
#define GPIOG                 ((GPIO_TypeDef *) GPIOG_BASE)
#define GPIOK                 ((GPIO_TypeDef *) GPIOK_BASE)

/* System Control Block (SCB) and FPU */
#define SCB_BASE              (0xE000ED00UL)
#define SCB_CPACR             (*((volatile uint32_t *)(SCB_BASE + 0x88UL)))

/* LED Definitions for STM32F469I-DISCO (Active LOW) */
/* LED1: PG6, LED2: PD4, LED3: PD5, LED4: PK3 */
#define LED1_PIN              (6UL)
#define LED2_PIN              (4UL)
#define LED3_PIN              (5UL)
#define LED4_PIN              (3UL)

/* Button Definition (Active HIGH) */
/* WAKEUP: PA0 */
#define BUTTON_PIN            (0UL)

#endif /* STM32F469XX_H */
