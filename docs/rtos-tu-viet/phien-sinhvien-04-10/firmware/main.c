#include "rtos.h"
#include "stm32f4xx_hal.h"
#include "stm32469i_discovery.h"
#include "stm32469i_discovery_lcd.h"
#include "stm32469i_discovery_sdram.h"
#include "stm32469i_discovery_ts.h"

/* Biến chẩn đoán xung nhịp để đọc sau khi nạp (anh cho, chưa có tài liệu) */
volatile uint32_t debug_rcc_cr = 0;
volatile uint32_t debug_rcc_cfgr = 0;
volatile uint32_t debug_sysclk_hz = 0;

/* Biến chẩn đoán cảm ứng và giao diện để đọc qua cổng gỡ lỗi */
volatile uint32_t debug_ts_touch_count = 0;
volatile uint16_t debug_ts_raw_x = 0;
volatile uint16_t debug_ts_raw_y = 0;
volatile uint32_t debug_ui_page_change_count = 0;
volatile uint8_t  debug_ts_init_status = 0xFF;
volatile uint32_t debug_ui_invalid_page_count = 0;
volatile uint32_t debug_ui_last_invalid_page = 0;

typedef enum {
    UI_PAGE_INVALID = 0,
    UI_PAGE_INTRO   = 1,
    UI_PAGE_DETAILS = 2,
    UI_PAGE_HELLO   = 3
} ui_page_t;

static volatile uint32_t led_state_1 = 0;
static volatile uint32_t led_state_2 = 0;
static volatile uint32_t led_state_3 = 0;
volatile uint32_t current_ui_page = UI_PAGE_INTRO;
static volatile uint32_t button_request_next_page = 0;

/* Cấu hình xung nhịp hệ thống theo Mục 3 tài liệu (anh cho, chưa có tài liệu):
 * HSE bật, PLL ON, nguồn HSE.
 * PLLM = 8, PLLN = 360, PLLP = 2, PLLQ = 7, PLLR = 6.
 * SYSCLK = 180000000 Hz.
 */
static void SystemClock_Config(void) {
    RCC_ClkInitTypeDef RCC_ClkInitStruct;
    RCC_OscInitTypeDef RCC_OscInitStruct;

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;
    RCC_OscInitStruct.PLL.PLLN = 360;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 7;
    RCC_OscInitStruct.PLL.PLLR = 6;
    if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK) {
        while (1) {}
    }

    if (HAL_PWREx_EnableOverDrive() != HAL_OK) {
        while (1) {}
    }

    RCC_ClkInitStruct.ClockType = (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2);
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
    if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_5) != HAL_OK) {
        while (1) {}
    }

    debug_rcc_cr = RCC->CR;
    debug_rcc_cfgr = RCC->CFGR;
    debug_sysclk_hz = HAL_RCC_GetSysClockFreq();
}

static void hardware_early_init(void) {
    HAL_Init();
    SystemClock_Config();

    led_state_1 = 0;
    led_state_2 = 0;
    led_state_3 = 0;
    current_ui_page = UI_PAGE_INTRO;

    /* Khởi tạo LED và Nút bấm qua BSP ST */
    BSP_LED_Init(LED1);
    BSP_LED_Init(LED2);
    BSP_LED_Init(LED3);
    BSP_PB_Init(BUTTON_WAKEUP, BUTTON_MODE_GPIO);
}

static void display_hardware_init(void) {
    /* Khởi tạo SDRAM làm vùng đệm khung hiển thị */
    BSP_SDRAM_Init();

    /* Khởi tạo màn hình DSI LCD (OTM8009A) */
    BSP_LCD_Init();
    BSP_LCD_LayerDefaultInit(0, LCD_FB_START_ADDRESS);
    BSP_LCD_SelectLayer(0);
    BSP_LCD_DisplayOn();

    /* Khởi tạo cảm ứng FT6x06 qua I2C */
    debug_ts_init_status = BSP_TS_Init(800, 480);
}

static bool touch_hardware_read(uint16_t *x, uint16_t *y) {
    TS_StateTypeDef ts_state;
    BSP_TS_GetState(&ts_state);
    if (ts_state.touchDetected > 0) {
        debug_ts_touch_count++;
        debug_ts_raw_x = ts_state.touchX[0];
        debug_ts_raw_y = ts_state.touchY[0];
        if (x) *x = ts_state.touchX[0];
        if (y) *y = ts_state.touchY[0];
        return true;
    }
    return false;
}

/* =========================================================================
 * Các hàm vẽ giao diện ba màn hình theo Mục 5.1 tài liệu
 * ========================================================================= */

static void draw_button(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint32_t bg_color, uint32_t text_color, sFONT *font, const char *label) {
    BSP_LCD_SetTextColor(bg_color);
    BSP_LCD_FillRect(x, y, w, h);
    BSP_LCD_SetTextColor(text_color);
    BSP_LCD_SetBackColor(bg_color);
    BSP_LCD_SetFont(font);
    uint32_t len = 0;
    while (label[len]) len++;
    uint16_t text_w = len * font->Width;
    uint16_t tx = (text_w < w) ? (x + (w - text_w) / 2) : x;
    uint16_t ty = (font->Height < h) ? (y + (h - font->Height) / 2) : y;
    BSP_LCD_DisplayStringAt(tx, ty, (uint8_t *)label, LEFT_MODE);
}

static bool is_inside(uint16_t tx, uint16_t ty, uint16_t rx, uint16_t ry, uint16_t rw, uint16_t rh) {
    return (tx >= rx && tx < rx + rw && ty >= ry && ty < ry + rh);
}

#include "logo_ptit.h"

static void draw_logo_ptit(void) {
    /* Vẽ từng điểm ảnh từ mảng 240x240 ARGB8888 (logo_ptit_data) vào vị trí (50, 130) */
    for (uint16_t r = 0; r < LOGO_PTIT_HEIGHT; r++) {
        for (uint16_t c = 0; c < LOGO_PTIT_WIDTH; c++) {
            uint32_t color = logo_ptit_data[r * LOGO_PTIT_WIDTH + c];
            BSP_LCD_DrawPixel(50 + c, 130 + r, color);
        }
    }
}

static void draw_screen_1_intro(void) {
    BSP_LCD_Clear(LCD_COLOR_WHITE);

    /* Tiêu đề trên cùng (màu đỏ, giữa màn hình) */
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_SetTextColor(LCD_COLOR_RED);
    BSP_LCD_SetBackColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(0, 30, (uint8_t *)"HOC VIEN CONG NGHE BUU CHINH VIEN THONG", CENTER_MODE);
    BSP_LCD_DisplayStringAt(0, 55, (uint8_t *)"KHOA KY THUAT DIEN TU 1", CENTER_MODE);

    /* Thông tin đồ án (x = 300) */
    BSP_LCD_SetFont(&Font20);
    BSP_LCD_SetTextColor(LCD_COLOR_DARKBLUE);
    BSP_LCD_DisplayStringAt(300, 130, (uint8_t *)"DE AN TOT NGHIEP", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 160, (uint8_t *)"HE THONG TAC TU EIDE v3", LEFT_MODE);

    BSP_LCD_SetFont(&Font16);
    BSP_LCD_SetTextColor(LCD_COLOR_BLACK);
    BSP_LCD_DisplayStringAt(300, 210, (uint8_t *)"DT: PHAT TRIEN PHAN MEM NHUNG", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 240, (uint8_t *)"CO UNG DUNG TRI TUE NHAN TAO(AI)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 280, (uint8_t *)"Hoc vien  : Vu Tri Cong", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 310, (uint8_t *)"GVHD      : TS. Nguyen Trung Hieu", LEFT_MODE);

    /* Logo PTIT bên trái */
    draw_logo_ptit();

    /* Hai nút ở hàng dưới (y = 400, kích thước 240 x 50) */
    /* Nút 1: x = 140, nền xanh dương, nhãn "Chi tiet" */
    draw_button(140, 400, 240, 50, LCD_COLOR_BLUE, LCD_COLOR_WHITE, &Font20, "Chi tiet");

    /* Nút 2: x = 420, nền xanh lá, nhãn "Hello" */
    draw_button(420, 400, 240, 50, LCD_COLOR_GREEN, LCD_COLOR_WHITE, &Font20, "Hello");
}

static void draw_screen_2_details(void) {
    BSP_LCD_Clear(LCD_COLOR_DARKBLUE);

    /* Tiêu đề giữa y = 25, màu vàng */
    BSP_LCD_SetFont(&Font20);
    BSP_LCD_SetTextColor(LCD_COLOR_YELLOW);
    BSP_LCD_SetBackColor(LCD_COLOR_DARKBLUE);
    BSP_LCD_DisplayStringAt(0, 25, (uint8_t *)"=== TINH NANG HE THONG EIDE v3 ===", CENTER_MODE);

    /* Mục 1 */
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(30, 75, (uint8_t *)"1. He dieu hanh thoi gian thuc TU VIET da tac vu:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(30, 100, (uint8_t *)"   - Task 1: LED1 nhay chu ky 1000 ms", LEFT_MODE);
    BSP_LCD_DisplayStringAt(30, 125, (uint8_t *)"   - Task 2: LED2 nhay chu ky 400 ms", LEFT_MODE);
    BSP_LCD_DisplayStringAt(30, 150, (uint8_t *)"   - Task 3: Quet nut bam PA0, chong rung 30 ms", LEFT_MODE);

    /* Mục 2 */
    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(30, 185, (uint8_t *)"2. Phan cung STM32F469NIH6 Cortex-M4F:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(30, 210, (uint8_t *)"   - Man hinh DSI 800x480 IC OTM8009A", LEFT_MODE);
    BSP_LCD_DisplayStringAt(30, 235, (uint8_t *)"   - Bo nho mo rong SDRAM FMC (FrameBuffer)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(30, 260, (uint8_t *)"   - Cam ung dien dung FocalTech FT6206 qua I2C", LEFT_MODE);

    /* Mục 3 */
    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(30, 295, (uint8_t *)"3. Nhan tu viet, khong dung FreeRTOS:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(30, 320, (uint8_t *)"   - Lap lich tien dinh 32 muc, chuyen ngu canh PendSV", LEFT_MODE);
    BSP_LCD_DisplayStringAt(30, 345, (uint8_t *)"   - Hang doi tinh co thoi han, 0 ky hieu FreeRTOS", LEFT_MODE);

    /* Nút Tro ve (x = 280, y = 400, 240 x 50) */
    draw_button(280, 400, 240, 50, LCD_COLOR_BLUE, LCD_COLOR_WHITE, &Font20, "Tro ve");
}

static void draw_screen_3_hello(void) {
    BSP_LCD_Clear(LCD_COLOR_BLACK);

    /* Tiêu đề & nội dung ở giữa màn hình */
    BSP_LCD_SetBackColor(LCD_COLOR_BLACK);

    BSP_LCD_SetFont(&Font24);
    BSP_LCD_SetTextColor(LCD_COLOR_YELLOW);
    BSP_LCD_DisplayStringAt(0, 150, (uint8_t *)"Xin chao", CENTER_MODE);

    BSP_LCD_SetFont(&Font20);
    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(0, 210, (uint8_t *)"Chao mung ban den voi He thong EIDE v3!", CENTER_MODE);

    BSP_LCD_SetFont(&Font16);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(0, 260, (uint8_t *)"Bo mach STM32F469I-DISCO san sang phuc vu", CENTER_MODE);

    /* Nút Tro ve (x = 280, y = 400, 240 x 50) */
    draw_button(280, 400, 240, 50, LCD_COLOR_BLUE, LCD_COLOR_WHITE, &Font20, "Tro ve");
}

/* =========================================================================
 * Định nghĩa 6 Tác vụ theo Bảng mục 5 của Tài liệu
 * ========================================================================= */

/* Kích thước ngăn xếp riêng cho từng tác vụ (anh cho, chưa có tài liệu)
 * Task 1 đến Task 5: 128 word mỗi tác vụ (f-nguoi-46896913).
 * Task 6 DisplayUI: 512 word (f-nguoi-5887700) để đảm bảo chuỗi BSP LCD/TS/SDRAM.
 */
#define STACK_WORDS_TASK1_LED1   128
#define STACK_WORDS_TASK2_LED2   128
#define STACK_WORDS_TASK3_BUTTON 128
#define STACK_WORDS_TASK4_QUEUE  128
#define STACK_WORDS_TASK5_MON    128
#define STACK_WORDS_TASK6_LCD    512

static uint32_t stack_task1[STACK_WORDS_TASK1_LED1];
static uint32_t stack_task2[STACK_WORDS_TASK2_LED2];
static uint32_t stack_task3[STACK_WORDS_TASK3_BUTTON];
static uint32_t stack_task4[STACK_WORDS_TASK4_QUEUE];
static uint32_t stack_task5[STACK_WORDS_TASK5_MON];
static uint32_t stack_task6[STACK_WORDS_TASK6_LCD];

static tcb_t tcb_task1;
static tcb_t tcb_task2;
static tcb_t tcb_task3;
static tcb_t tcb_task4;
static tcb_t tcb_task5;
static tcb_t tcb_task6;

/* Hàng đợi tĩnh truyền thông điệp giữa Tác vụ 3 (Nút bấm) và Tác vụ 4 (Đèn LED) */
#define QUEUE_MSG_CAPACITY 8
static rtos_queue_t button_event_queue;
static uint32_t queue_storage[QUEUE_MSG_CAPACITY];

/* Tác vụ 1: Nháy đèn 1 chu kỳ 1000 ms (Ưu tiên 7) */
static void task_led1_1000ms(void *arg) {
    (void)arg;
    while (1) {
        led_state_1 = !led_state_1;
        BSP_LED_Toggle(LED1);
        rtos_delay_ms(500);
    }
}

/* Tác vụ 2: Nháy đèn 2 chu kỳ 400 ms (Ưu tiên 8) */
static void task_led2_400ms(void *arg) {
    (void)arg;
    while (1) {
        led_state_2 = !led_state_2;
        BSP_LED_Toggle(LED2);
        rtos_delay_ms(200);
    }
}

/* Tác vụ 3: Quét nút bấm PA0 mỗi 30 ms, chống rung (Ưu tiên 20 - Cao nhất) */
static void task_button_scan_30ms(void *arg) {
    (void)arg;
    uint32_t last_raw_state = 0;
    uint32_t stable_counter = 0;
    uint32_t debounced_state = 0;

    while (1) {
        uint32_t current_raw = BSP_PB_GetState(BUTTON_WAKEUP);

        if (current_raw == last_raw_state) {
            stable_counter++;
            if (stable_counter >= 2) {
                if (current_raw != debounced_state) {
                    debounced_state = current_raw;
                    if (debounced_state != 0) {
                        button_request_next_page = 1;
                        uint32_t msg = 1;
                        rtos_queue_send(&button_event_queue, &msg, 10);
                    }
                }
            }
        } else {
            stable_counter = 0;
            last_raw_state = current_raw;
        }

        rtos_delay_ms(30);
    }
}

/* Tác vụ 4: Đèn LED chỉ nháy khi nhận được tin qua hàng đợi (Ưu tiên 15) */
static void task_led_queue_event(void *arg) {
    (void)arg;
    uint32_t received_msg = 0;

    while (1) {
        bool received = rtos_queue_receive(&button_event_queue, &received_msg, 500);
        if (received) {
            led_state_3 = 1;
            BSP_LED_On(LED3);
            rtos_delay_ms(100);
            led_state_3 = 0;
            BSP_LED_Off(LED3);
        }
    }
}

/* Bảng ghi nhận mức nước ngăn xếp của cả 6 tác vụ */
typedef struct {
    uint32_t watermark_words; /* Số word chưa chạm tới từ đáy ngăn xếp */
    uint32_t used_words;      /* Số word đã sử dụng tối đa */
} task_stack_telemetry_t;

static volatile task_stack_telemetry_t task_stack_telemetry[6];

/* Tác vụ 5: Theo dõi và báo trạng thái hệ thống (Ưu tiên 5) */
static void task_system_monitor(void *arg) {
    (void)arg;
    const tcb_t *task_array[6] = {
        &tcb_task1, &tcb_task2, &tcb_task3,
        &tcb_task4, &tcb_task5, &tcb_task6
    };

    while (1) {
        for (uint32_t i = 0; i < 6; i++) {
            task_stack_telemetry[i].watermark_words = rtos_task_get_stack_watermark(task_array[i]);
            task_stack_telemetry[i].used_words = rtos_task_get_stack_used_words(task_array[i]);
        }

        rtos_delay_ms(2000);
    }
}

/* Tác vụ 6: Màn hình DSI và Cảm ứng (Ưu tiên 10) */
static void task_display_touch(void *arg) {
    (void)arg;
    display_hardware_init();

    uint32_t active_page = current_ui_page;
    if (active_page != UI_PAGE_INTRO && active_page != UI_PAGE_DETAILS && active_page != UI_PAGE_HELLO) {
        debug_ui_invalid_page_count++;
        debug_ui_last_invalid_page = active_page;
        active_page = UI_PAGE_INTRO;
        current_ui_page = UI_PAGE_INTRO;
    }
    draw_screen_1_intro();

    uint32_t touch_released = 1;

    while (1) {
        uint32_t next_page = active_page;

        /* Kiểm tra yêu cầu đổi trang từ nút bấm PA0 (Task 3) */
        if (button_request_next_page) {
            button_request_next_page = 0;
            /* PA0: sang trang kế tiếp theo vòng: INTRO -> DETAILS -> HELLO -> INTRO */
            switch (active_page) {
                case UI_PAGE_INTRO:
                    next_page = UI_PAGE_DETAILS;
                    break;
                case UI_PAGE_DETAILS:
                    next_page = UI_PAGE_HELLO;
                    break;
                case UI_PAGE_HELLO:
                    next_page = UI_PAGE_INTRO;
                    break;
                default:
                    debug_ui_invalid_page_count++;
                    debug_ui_last_invalid_page = active_page;
                    next_page = UI_PAGE_INTRO;
                    break;
            }
        }

        /* Kiểm tra cảm ứng chạm màn hình */
        uint16_t touch_x = 0;
        uint16_t touch_y = 0;
        if (touch_hardware_read(&touch_x, &touch_y)) {
            if (touch_released) {
                touch_released = 0;

                switch (active_page) {
                    case UI_PAGE_INTRO:
                        /* Nút 1: Chi tiet (x = 140, y = 400, w = 240, h = 50) */
                        if (is_inside(touch_x, touch_y, 140, 400, 240, 50)) {
                            next_page = UI_PAGE_DETAILS;
                        }
                        /* Nút 2: Hello (x = 420, y = 400, w = 240, h = 50) */
                        else if (is_inside(touch_x, touch_y, 420, 400, 240, 50)) {
                            next_page = UI_PAGE_HELLO;
                        }
                        break;

                    case UI_PAGE_DETAILS:
                        /* Nút Tro ve (x = 280, y = 400, w = 240, h = 50) */
                        if (is_inside(touch_x, touch_y, 280, 400, 240, 50)) {
                            next_page = UI_PAGE_INTRO;
                        }
                        break;

                    case UI_PAGE_HELLO:
                        /* Nút Tro ve (x = 280, y = 400, w = 240, h = 50) */
                        if (is_inside(touch_x, touch_y, 280, 400, 240, 50)) {
                            next_page = UI_PAGE_INTRO;
                        }
                        break;

                    default:
                        debug_ui_invalid_page_count++;
                        debug_ui_last_invalid_page = active_page;
                        next_page = UI_PAGE_INTRO;
                        break;
                }
            }
        } else {
            touch_released = 1;
        }

        /* Chốt kiểm tra an toàn (runtime guard): nếu next_page không hợp lệ */
        if (next_page != UI_PAGE_INTRO && next_page != UI_PAGE_DETAILS && next_page != UI_PAGE_HELLO) {
            debug_ui_invalid_page_count++;
            debug_ui_last_invalid_page = next_page;
            next_page = UI_PAGE_INTRO;
        }

        /* Nếu trang thay đổi, vẽ lại toàn bộ màn hình tương ứng */
        if (next_page != active_page) {
            active_page = next_page;
            current_ui_page = active_page;
            debug_ui_page_change_count++;

            switch (active_page) {
                case UI_PAGE_INTRO:
                    draw_screen_1_intro();
                    break;
                case UI_PAGE_DETAILS:
                    draw_screen_2_details();
                    break;
                case UI_PAGE_HELLO:
                    draw_screen_3_hello();
                    break;
                default:
                    debug_ui_invalid_page_count++;
                    debug_ui_last_invalid_page = active_page;
                    active_page = UI_PAGE_INTRO;
                    current_ui_page = UI_PAGE_INTRO;
                    draw_screen_1_intro();
                    break;
            }
        }

        rtos_delay_ms(40);
    }
}

/* =========================================================================
 * Hàm Main: Khởi tạo phần cứng và nhân RTOS
 * ========================================================================= */

int main(void) {
    hardware_early_init();
    rtos_init();

    rtos_queue_init(&button_event_queue, queue_storage, sizeof(uint32_t), QUEUE_MSG_CAPACITY);

    /* Khởi tạo 6 tác vụ */
    rtos_task_create(&tcb_task3, "ButtonScan", task_button_scan_30ms, 0, 20, stack_task3, STACK_WORDS_TASK3_BUTTON);
    rtos_task_create(&tcb_task4, "LedQueue",   task_led_queue_event,  0, 15, stack_task4, STACK_WORDS_TASK4_QUEUE);
    rtos_task_create(&tcb_task6, "DisplayUI",  task_display_touch,    0, 10, stack_task6, STACK_WORDS_TASK6_LCD);
    rtos_task_create(&tcb_task2, "Led400ms",   task_led2_400ms,       0,  8, stack_task2, STACK_WORDS_TASK2_LED2);
    rtos_task_create(&tcb_task1, "Led1000ms",  task_led1_1000ms,      0,  7, stack_task1, STACK_WORDS_TASK1_LED1);
    rtos_task_create(&tcb_task5, "SysMonitor", task_system_monitor,   0,  5, stack_task5, STACK_WORDS_TASK5_MON);

    rtos_start();

    while (1) {
    }
    return 0;
}
