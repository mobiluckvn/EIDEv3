/**
 * @file main.c
 * @brief Chương trình chính STM32F469I-DISCO với 6 tác vụ trên nhân RTOS tiền định
 *        chuyển đổi từ tham-khao/main-freertos.c:
 *        1. vTaskLED1
 *        2. vTaskLED2
 *        3. vTaskButton (quét nút USER PA0)
 *        4. vTaskLED3 (chờ hàng đợi từ nút bấm)
 *        5. vTaskMonitor (nhịp tim LED4 PK3)
 *        6. vTaskLCD (quản lý LCD DSI OTM8009A, cảm ứng FT6206)
 */

#include <stdint.h>
#include <stdbool.h>
#include "stm32f469xx.h"
#include "stm32f4xx_hal.h"
#include "rtos/rtos_types.h"
#include "ui.h"
#include "touch.h"

/* Định nghĩa chân LED trên STM32F469I-DISCO (Active LOW) */
/* LED1: PG6, LED2: PD4, LED3: PD5, LED4: PK3 */
#define LED1_PIN              (6UL)
#define LED2_PIN              (4UL)
#define LED3_PIN              (5UL)
#define LED4_PIN              (3UL)

/* Định nghĩa chân nút bấm USER (Active HIGH) - WAKEUP: PA0 */
#define BUTTON_PIN            (0UL)

/* Dung lượng hàng đợi sự kiện */
#define QUEUE_CAPACITY        4U

/* Hàng đợi truyền tín hiệu sự kiện từ nút bấm PA0 sang tác vụ LED3 và LCD */
static uint32_t button_queue_storage[QUEUE_CAPACITY];
static rtos_queue_t xButtonQueue;

static uint32_t ui_queue_storage[QUEUE_CAPACITY];
static rtos_queue_t xUIQueue;

/* Vùng nhớ tĩnh TCB và Stack cho 6 tác vụ */
static rtos_tcb_t tcb_led1;
static uint32_t stack_led1[RTOS_DEFAULT_STACK_WORDS];

static rtos_tcb_t tcb_led2;
static uint32_t stack_led2[RTOS_DEFAULT_STACK_WORDS];

static rtos_tcb_t tcb_button;
static uint32_t stack_button[RTOS_DEFAULT_STACK_WORDS];

static rtos_tcb_t tcb_led3;
static uint32_t stack_led3[RTOS_DEFAULT_STACK_WORDS];

static rtos_tcb_t tcb_monitor;
static uint32_t stack_monitor[RTOS_DEFAULT_STACK_WORDS];

static rtos_tcb_t tcb_lcd;
static uint32_t stack_lcd[1024U]; /* Stack mở rộng cho tác vụ LCD và Touch */

extern uint32_t SystemCoreClock;

/**
 * @brief Cấu hình hệ thống xung nhịp lên 180 MHz từ HSE (tương thích cấu hình tham khảo FreeRTOS).
 */
static void prvSetupClock180MHz(void)
{
    /* 1. Bật HSE */
    RCC->CR |= RCC_CR_HSEON;
    for (volatile uint32_t timeout = 0; timeout < 100000; timeout++) {
        if (RCC->CR & RCC_CR_HSERDY) {
            break;
        }
    }

    /* 2. Bật clock PWR Controller và đặt chế độ Scale 1 */
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC->APB1ENR;
    PWR->CR |= PWR_CR_VOS;

    /* 3. Đặt bộ chia bus APB1 = /4, APB2 = /2 */
    RCC->CFGR |= RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2;

    /* 4. Cấu hình Main PLL: HSE / 8 * 360 / 2 = 180 MHz */
    RCC->PLLCFGR = (8UL << RCC_PLLCFGR_PLLM_Pos)
                 | (360UL << RCC_PLLCFGR_PLLN_Pos)
                 | (0UL << RCC_PLLCFGR_PLLP_Pos)
                 | RCC_PLLCFGR_PLLSRC_HSE
                 | (7UL << RCC_PLLCFGR_PLLQ_Pos)
                 | (6UL << RCC_PLLCFGR_PLLR_Pos);

    /* 5. Bật PLL chính và chờ sẵn sàng */
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY));

    /* 6. Kích hoạt chế độ Over-Drive */
    PWR->CR |= PWR_CR_ODEN;
    while (!(PWR->CSR & PWR_CSR_ODRDY));
    PWR->CR |= PWR_CR_ODSWEN;
    while (!(PWR->CSR & PWR_CSR_ODSWRDY));

    /* 7. Cấu hình Flash 5 Wait States, bật Prefetch, IC và DC */
    FLASH->ACR = FLASH_ACR_LATENCY_5WS | FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN;

    /* 8. Chuyển nguồn SYSCLK sang PLL và chờ hoàn tất */
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | RCC_CFGR_SW_PLL;
    while ((RCC->CFGR & RCC_CFGR_SWS) != RCC_CFGR_SWS_PLL);

    /* 9. Cập nhật biến SystemCoreClock cho RTOS và ngoại vi */
    SystemCoreClock = 180000000UL;
}

/**
 * @brief Cung cấp hàm thời gian HAL dựa trên RTOS tick count.
 */
uint32_t HAL_GetTick(void)
{
    return rtos_get_tick_count();
}

/**
 * @brief Hàm trễ phần cứng thích ứng với RTOS delay.
 */
void HAL_Delay(uint32_t Delay)
{
    if (Delay == 0) {
        return;
    }
    if (rtos_get_tick_count() > 0) {
        rtos_delay_ms(Delay);
    } else {
        /* Vòng lặp chờ thô khi scheduler chưa khởi chạy */
        for (volatile uint32_t i = 0; i < Delay * 40000; i++) {
            __asm__("nop");
        }
    }
}

/**
 * @brief Khởi tạo ngoại vi phần cứng: 4 LED và nút WAKEUP PA0.
 */
static void prvSetupHardware(void)
{
    /* Cấu hình xung nhịp hệ thống lên 180 MHz từ HSE */
    prvSetupClock180MHz();

    /* Bật clock AHB1 cho GPIOA, GPIOD, GPIOG, GPIOK */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIODEN | RCC_AHB1ENR_GPIOGEN | RCC_AHB1ENR_GPIOKEN;

    /* Cấu hình PA0 (Nút WAKEUP): Chế độ Input (00), Pull-down (10) */
    GPIOA->MODER &= ~(3UL << (BUTTON_PIN * 2));
    GPIOA->PUPDR &= ~(3UL << (BUTTON_PIN * 2));
    GPIOA->PUPDR |= (2UL << (BUTTON_PIN * 2));

    /* Cấu hình PG6 (LED1): Chế độ Output (01), tắt ban đầu (LED tích cực mức thấp) */
    GPIOG->MODER &= ~(3UL << (LED1_PIN * 2));
    GPIOG->MODER |= (1UL << (LED1_PIN * 2));
    GPIOG->BSRR = (1UL << LED1_PIN);

    /* Cấu hình PD4 (LED2) & PD5 (LED3): Chế độ Output (01), tắt ban đầu */
    GPIOD->MODER &= ~((3UL << (LED2_PIN * 2)) | (3UL << (LED3_PIN * 2)));
    GPIOD->MODER |= ((1UL << (LED2_PIN * 2)) | (1UL << (LED3_PIN * 2)));
    GPIOD->BSRR = (1UL << LED2_PIN) | (1UL << LED3_PIN);

    /* Cấu hình PK3 (LED4): Chế độ Output (01), tắt ban đầu */
    GPIOK->MODER &= ~(3UL << (LED4_PIN * 2));
    GPIOK->MODER |= (1UL << (LED4_PIN * 2));
    GPIOK->BSRR = (1UL << LED4_PIN);
}

/**
 * @brief Task 1: Nháy LED1 (PG6) theo chu kỳ.
 */
static void vTaskLED1(void *arg)
{
    (void)arg;
    for (;;) {
        GPIOG->BSRR = (1UL << (LED1_PIN + 16)); /* Bật LED1 (mức thấp) */
        rtos_delay_ms(500U);
        GPIOG->BSRR = (1UL << LED1_PIN);        /* Tắt LED1 (mức cao) */
        rtos_delay_ms(500U);
    }
}

/**
 * @brief Task 2: Nháy LED2 (PD4) theo chu kỳ.
 */
static void vTaskLED2(void *arg)
{
    (void)arg;
    for (;;) {
        GPIOD->BSRR = (1UL << (LED2_PIN + 16)); /* Bật LED2 */
        rtos_delay_ms(200U);
        GPIOD->BSRR = (1UL << LED2_PIN);        /* Tắt LED2 */
        rtos_delay_ms(200U);
    }
}

/**
 * @brief Task 3: Đọc nút bấm PA0 (quét định kỳ, chống rung) và gửi thông điệp vào Queues.
 */
static void vTaskButton(void *arg)
{
    (void)arg;
    uint8_t prev_state = 0;

    for (;;) {
        uint8_t state = (GPIOA->IDR & (1UL << BUTTON_PIN)) ? 1U : 0U;
        if (state && !prev_state) {
            uint32_t msg = 1U;
            rtos_queue_send(&xButtonQueue, &msg, 0U);
            rtos_queue_send(&xUIQueue, &msg, 0U);
        }
        prev_state = state;
        rtos_delay_ms(30U);
    }
}

/**
 * @brief Task 4: Chờ tín hiệu từ Queue để đảo trạng thái LED3 (PD5).
 */
static void vTaskLED3(void *arg)
{
    (void)arg;
    uint32_t rx_msg = 0;
    uint8_t led_state = 0;

    for (;;) {
        if (rtos_queue_receive(&xButtonQueue, &rx_msg, 1000U) == RTOS_OK) {
            led_state = !led_state;
            if (led_state) {
                GPIOD->BSRR = (1UL << (LED3_PIN + 16)); /* Bật LED3 */
            } else {
                GPIOD->BSRR = (1UL << LED3_PIN);        /* Tắt LED3 */
            }
        }
    }
}

/**
 * @brief Task 5: Giám sát hệ thống qua LED4 (PK3) - nhịp tim định kỳ.
 */
static void vTaskMonitor(void *arg)
{
    (void)arg;
    for (;;) {
        GPIOK->BSRR = (1UL << (LED4_PIN + 16)); /* Bật LED4 */
        rtos_delay_ms(100U);
        GPIOK->BSRR = (1UL << LED4_PIN);        /* Tắt LED4 */
        rtos_delay_ms(1900U);
    }
}

/**
 * @brief Task 6: Quản lý hiển thị LCD DSI OTM8009A và quét cảm ứng điện dung FT6206.
 */
static void vTaskLCD(void *arg)
{
    (void)arg;
    uint32_t rx_msg = 0;

    /* Khởi tạo SDRAM và màn hình LCD DSI */
    UI_Init();

    /* Khởi tạo cảm ứng điện dung qua I2C */
    Touch_Init();

    uint8_t touch_was_pressed = 0;

    for (;;) {
        /* Chờ tín hiệu từ nút bấm vật lý PA0 (timeout để kết hợp quét cảm ứng) */
        if (rtos_queue_receive(&xUIQueue, &rx_msg, 40U) == RTOS_OK) {
            UI_ToggleScreen();
        }

        /* Quét điểm chạm trên màn hình cảm ứng */
        uint16_t tx = 0;
        uint16_t ty = 0;
        if (Touch_Read(&tx, &ty)) {
            if (!touch_was_pressed) {
                UI_HandleTouch(tx, ty);
                touch_was_pressed = 1U;
            }
        } else {
            touch_was_pressed = 0U;
        }
    }
}

/**
 * @brief Điểm khởi nhập chính của ứng dụng firmware.
 */
int main(void)
{
    /* 1. Thiết lập phần cứng (GPIO LED và nút bấm) */
    prvSetupHardware();

    /* 2. Khởi tạo lõi RTOS */
    rtos_init();

    /* 3. Khởi tạo hàng đợi tĩnh IPC cho sự kiện nút bấm */
    rtos_queue_init(
        &xButtonQueue,
        button_queue_storage,
        sizeof(uint32_t),
        QUEUE_CAPACITY
    );

    rtos_queue_init(
        &xUIQueue,
        ui_queue_storage,
        sizeof(uint32_t),
        QUEUE_CAPACITY
    );

    /* 4. Tạo 6 tác vụ với các mức ưu tiên riêng biệt (0 cao nhất, 31 idle).
     * Nhân O(1) quy định mỗi mức ưu tiên chỉ gắn với 1 tác vụ:
     * - Button (1U): ưu tiên cao nhất để quét nút bấm kịp thời
     * - LCD (2U): ưu tiên cao cho tương tác giao diện và cảm ứng
     * - LED3 (3U): phản hồi sự kiện từ hàng đợi nút bấm
     * - LED2 (4U): tác vụ nháy chu kỳ 400 ms
     * - LED1 (5U): tác vụ nháy chu kỳ 1000 ms
     * - Monitor (6U): tác vụ giám sát nhịp tim hệ thống
     */
    rtos_task_create(&tcb_button,  "BtnPoll",     vTaskButton,  NULL, 1U, stack_button,  RTOS_DEFAULT_STACK_WORDS);
    rtos_task_create(&tcb_lcd,     "LCD_Task",    vTaskLCD,     NULL, 2U, stack_lcd,     1024U);
    rtos_task_create(&tcb_led3,    "LED3_Queue",  vTaskLED3,    NULL, 3U, stack_led3,    RTOS_DEFAULT_STACK_WORDS);
    rtos_task_create(&tcb_led2,    "LED2_400ms",  vTaskLED2,    NULL, 4U, stack_led2,    RTOS_DEFAULT_STACK_WORDS);
    rtos_task_create(&tcb_led1,    "LED1_1000ms", vTaskLED1,    NULL, 5U, stack_led1,    RTOS_DEFAULT_STACK_WORDS);
    rtos_task_create(&tcb_monitor, "Monitor",     vTaskMonitor, NULL, 6U, stack_monitor, RTOS_DEFAULT_STACK_WORDS);

    /* 5. Khởi động bộ lập lịch RTOS tiền định */
    rtos_start();

    /* Bẫy vòng lặp nếu nhân bị dừng bất thường */
    while (1) {
        __WFI();
    }

    return 0;
}
