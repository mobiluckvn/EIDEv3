#include <stdint.h>
#include "stm32f469xx.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "ui.h"
#include "touch.h"

/* LED Definitions for STM32F469I-DISCO (Active LOW) */
/* LED1: PG6, LED2: PD4, LED3: PD5, LED4: PK3 */
#define LED1_PIN              (6UL)
#define LED2_PIN              (4UL)
#define LED3_PIN              (5UL)
#define LED4_PIN              (3UL)

/* Button Definition (Active HIGH) - WAKEUP: PA0 */
#define BUTTON_PIN            (0UL)

/* Hàng đợi truyền tín hiệu sự kiện từ nút bấm PA0 sang tác vụ LED3 và LCD */
static QueueHandle_t xButtonQueue = NULL;
static QueueHandle_t xUIQueue = NULL;

/* Cung cấp hàm thời gian HAL dựa trên FreeRTOS tick */
uint32_t HAL_GetTick(void)
{
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED) {
        return (uint32_t)xTaskGetTickCount();
    }
    static volatile uint32_t fake_tick = 0;
    return ++fake_tick;
}

void HAL_Delay(uint32_t Delay)
{
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED) {
        vTaskDelay(pdMS_TO_TICKS(Delay));
    } else {
        /* Vòng lặp chờ thô khi scheduler chưa khởi chạy */
        for (volatile uint32_t i = 0; i < Delay * 4000; i++) {
            __asm__("nop");
        }
    }
}

extern uint32_t SystemCoreClock;

/* Cấu hình hệ thống xung nhịp lên 180 MHz từ HSE (Fact f-nguoi-81717370 do anh cho) */
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

    /* 9. Cập nhật biến SystemCoreClock cho FreeRTOS và ngoại vi */
    SystemCoreClock = 180000000UL;
}

/* Khởi tạo ngoại vi phần cứng: 4 LED và nút WAKEUP PA0 */
static void prvSetupHardware(void)
{
    /* Cấu hình SYSCLK 180 MHz */
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

/* Task 1: Nháy LED1 (PG6) theo chu kỳ 1000 ms (500 ms bật, 500 ms tắt) */
static void vTaskLED1(void *pvParameters)
{
    (void)pvParameters;
    for (;;) {
        GPIOG->BSRR = (1UL << (LED1_PIN + 16)); /* Bật LED1 (mức thấp) */
        vTaskDelay(pdMS_TO_TICKS(500));
        GPIOG->BSRR = (1UL << LED1_PIN);        /* Tắt LED1 (mức cao) */
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

/* Task 2: Nháy LED2 (PD4) theo chu kỳ 400 ms (200 ms bật, 200 ms tắt) */
static void vTaskLED2(void *pvParameters)
{
    (void)pvParameters;
    for (;;) {
        GPIOD->BSRR = (1UL << (LED2_PIN + 16)); /* Bật LED2 */
        vTaskDelay(pdMS_TO_TICKS(200));
        GPIOD->BSRR = (1UL << LED2_PIN);        /* Tắt LED2 */
        vTaskDelay(pdMS_TO_TICKS(200));
    }
}

/* Tác vụ đọc nút bấm PA0 và gửi thông điệp vào Queues */
static void vTaskButton(void *pvParameters)
{
    (void)pvParameters;
    uint8_t prev_state = 0;

    for (;;) {
        uint8_t state = (GPIOA->IDR & (1UL << BUTTON_PIN)) ? 1 : 0;
        if (state && !prev_state) {
            uint32_t msg = 1;
            if (xButtonQueue != NULL) {
                xQueueSend(xButtonQueue, &msg, 0);
            }
            if (xUIQueue != NULL) {
                xQueueSend(xUIQueue, &msg, 0);
            }
        }
        prev_state = state;
        vTaskDelay(pdMS_TO_TICKS(30)); /* Lọc rung nút bấm (debounce) */
    }
}

/* Task 3: Chờ tín hiệu từ Queue để đổi trạng thái LED3 (PD5) */
static void vTaskLED3(void *pvParameters)
{
    (void)pvParameters;
    uint32_t rx_msg = 0;
    uint8_t led_state = 0;

    for (;;) {
        if (xQueueReceive(xButtonQueue, &rx_msg, portMAX_DELAY) == pdPASS) {
            led_state = !led_state;
            if (led_state) {
                GPIOD->BSRR = (1UL << (LED3_PIN + 16)); /* Bật LED3 */
            } else {
                GPIOD->BSRR = (1UL << LED3_PIN);        /* Tắt LED3 */
            }
        }
    }
}

/* Task 4: Giám sát hệ thống qua LED4 (PK3) - nhịp tim định kỳ */
static void vTaskMonitor(void *pvParameters)
{
    (void)pvParameters;
    for (;;) {
        GPIOK->BSRR = (1UL << (LED4_PIN + 16)); /* Bật LED4 */
        vTaskDelay(pdMS_TO_TICKS(100));
        GPIOK->BSRR = (1UL << LED4_PIN);        /* Tắt LED4 */
        vTaskDelay(pdMS_TO_TICKS(1900));
    }
}

/* Task 5: Quản lý hiển thị LCD DSI OTM8009A và cập nhật giao diện */
static void vTaskLCD(void *pvParameters)
{
    (void)pvParameters;
    uint32_t rx_msg = 0;

    /* Khởi tạo SDRAM và màn hình LCD DSI */
    UI_Init();

    /* Khởi tạo cảm ứng điện dung qua I2C */
    Touch_Init();

    uint8_t touch_was_pressed = 0;

    for (;;) {
        /* Chờ tín hiệu từ nút bấm vật lý PA0 (timeout 40ms để quét cảm ứng) */
        if (xQueueReceive(xUIQueue, &rx_msg, pdMS_TO_TICKS(40)) == pdPASS) {
            UI_ToggleScreen();
        }

        /* Quét điểm chạm trên màn hình cảm ứng */
        uint16_t tx = 0, ty = 0;
        if (Touch_Read(&tx, &ty)) {
            if (!touch_was_pressed) {
                UI_HandleTouch(tx, ty);
                touch_was_pressed = 1;
            }
        } else {
            touch_was_pressed = 0;
        }
    }
}

int main(void)
{
    prvSetupHardware();

    /* Tạo queue chứa sự kiện nút bấm */
    xButtonQueue = xQueueCreate(4, sizeof(uint32_t));
    xUIQueue     = xQueueCreate(4, sizeof(uint32_t));

    /* Tạo các tác vụ ứng dụng LED, nút bấm và hiển thị LCD */
    xTaskCreate(vTaskLED1,    "LED1_1000ms", configMINIMAL_STACK_SIZE,       NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskLED2,    "LED2_400ms",  configMINIMAL_STACK_SIZE,       NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskButton,  "BtnPoll",     configMINIMAL_STACK_SIZE,       NULL, tskIDLE_PRIORITY + 2, NULL);
    xTaskCreate(vTaskLED3,    "LED3_Queue",  configMINIMAL_STACK_SIZE,       NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskMonitor, "Monitor",     configMINIMAL_STACK_SIZE,       NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskLCD,      "LCD_Task",    configMINIMAL_STACK_SIZE * 4,   NULL, tskIDLE_PRIORITY + 1, NULL);

    /* Bắt đầu FreeRTOS scheduler */
    vTaskStartScheduler();

    /* Không bao giờ tới đây */
    for (;;);
    return 0;
}
