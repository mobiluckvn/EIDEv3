#include <stdint.h>
#include "stm32f469xx.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"

/* Hàng đợi truyền tín hiệu sự kiện từ nút bấm PA0 sang tác vụ LED3 */
static QueueHandle_t xButtonQueue = NULL;

/* Khởi tạo ngoại vi phần cứng: 4 LED và nút WAKEUP PA0 */
static void prvSetupHardware(void)
{
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

/* Tác vụ đọc nút bấm PA0 và gửi thông điệp vào Queue */
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

int main(void)
{
    prvSetupHardware();

    /* Tạo queue chứa tối đa 4 sự kiện nút bấm */
    xButtonQueue = xQueueCreate(4, sizeof(uint32_t));

    /* Tạo 4 tác vụ ứng dụng và 1 tác vụ quét nút bấm */
    xTaskCreate(vTaskLED1,    "LED1_1000ms", configMINIMAL_STACK_SIZE, NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskLED2,    "LED2_400ms",  configMINIMAL_STACK_SIZE, NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskButton,  "BtnPoll",     configMINIMAL_STACK_SIZE, NULL, tskIDLE_PRIORITY + 2, NULL);
    xTaskCreate(vTaskLED3,    "LED3_Queue",  configMINIMAL_STACK_SIZE, NULL, tskIDLE_PRIORITY + 1, NULL);
    xTaskCreate(vTaskMonitor, "Monitor",     configMINIMAL_STACK_SIZE, NULL, tskIDLE_PRIORITY + 1, NULL);

    /* Bắt đầu FreeRTOS scheduler */
    vTaskStartScheduler();

    /* Không bao giờ tới đây */
    for (;;);
    return 0;
}
