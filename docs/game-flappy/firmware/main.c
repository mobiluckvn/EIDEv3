/**
 * @file main.c
 * @brief Điểm khởi nhập hệ thống, cấu hình phần cứng và 5 tác vụ nhân RTOS Flappy Bird.
 * @details Khởi tạo HAL, cấu hình xung nhịp 180 MHz Over-Drive, khởi động màn hình LCD
 *          và đăng ký 5 tác vụ theo đúng đặc tả ADR-04.
 */

#include <stdint.h>
#include <stdbool.h>
#include "stm32f4xx_hal.h"
#include "stm32469i_discovery.h"
#include "stm32469i_discovery_lcd.h"
#include "stm32469i_discovery_ts.h"
#include "rtos.h"
#include "game.h"
#include "ui.h"

/* Các biến chẩn đoán LCD được tham chiếu bởi bsp/stm32469i_discovery_lcd.c */
volatile uint32_t g_otm8009a_init_ret = 0;
volatile uint8_t  g_bright_before = 0;
volatile uint8_t  g_bright_val_written = 0;
volatile uint32_t g_bright_write_ret = 0;
volatile uint8_t  g_bright_after = 0;
volatile int32_t  g_bright_read_ret = 0;
volatile uint8_t  g_panel_cmd_status[8] = {0};
volatile int32_t  g_panel_cmd_ret[8] = {0};

/* =========================================================================
 * Bộ nhớ ngăn xếp và TCB cho 5 tác vụ hệ thống (đặc tả ADR-04)
 * ========================================================================= */
static uint32_t s_stack_input[256];
static os_tcb_t s_tcb_input;

static uint32_t s_stack_logic[512];
static os_tcb_t s_tcb_logic;

static uint32_t s_stack_render[1024];
static os_tcb_t s_tcb_render;

static uint32_t s_stack_heartbeat[128];
static os_tcb_t s_tcb_heartbeat;

static uint32_t s_stack_idle[128];
static os_tcb_t s_tcb_idle;

/* =========================================================================
 * Cấu hình xung nhịp hệ thống đạt 180 MHz với chế độ Over-Drive
 * ========================================================================= */
static void SystemClock_Config(void) {
    RCC_OscInitTypeDef RCC_OscInitStruct = {0};
    RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /* Cấu hình PLL từ thạch anh ngoài HSE */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    RCC_OscInitStruct.HSEState = RCC_HSE_ON;
    RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLM = 8;
    RCC_OscInitStruct.PLL.PLLN = 360;
    RCC_OscInitStruct.PLL.PLLP = RCC_PLLP_DIV2;
    RCC_OscInitStruct.PLL.PLLQ = 7;
    RCC_OscInitStruct.PLL.PLLR = 6;
    HAL_RCC_OscConfig(&RCC_OscInitStruct);

    /* Kích hoạt chế độ Over-Drive */
    HAL_PWREx_EnableOverDrive();

    /* Thiết lập bộ chia cho các bus hệ thống */
    RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK
                                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
    RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
    HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_ACR_LATENCY_5WS);
}

static void button_init(void) {
    __HAL_RCC_GPIOA_CLK_ENABLE();
    GPIO_InitTypeDef GPIO_InitStruct;
    GPIO_InitStruct.Pin = GPIO_PIN_0;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
}

/* =========================================================================
 * 1. Tác vụ Task_Input (Ưu tiên 3, Chu kỳ 20 ms)
 * ========================================================================= */
static void task_input_fn(void *arg) {
    (void)arg;
    uint8_t btn_prev = 0;
    uint8_t ts_prev = 0;
    TS_StateTypeDef ts_state;

    while (1) {
        uint8_t btn_curr = (uint8_t)HAL_GPIO_ReadPin(GPIOA, GPIO_PIN_0);

        BSP_TS_GetState(&ts_state);
        uint8_t ts_curr = (ts_state.touchDetected > 0) ? 1 : 0;

        if ((btn_curr == GPIO_PIN_SET && btn_prev == GPIO_PIN_RESET) ||
            (ts_curr == 1 && ts_prev == 0)) {
            game_trigger_jump();
        }
        btn_prev = btn_curr;
        ts_prev = ts_curr;
        os_delay(20);
    }
}

/* =========================================================================
 * 2. Tác vụ Task_GameLogic (Ưu tiên 2, Chu kỳ 20 ms)
 * ========================================================================= */
static void task_logic_fn(void *arg) {
    (void)arg;
    while (1) {
        game_tick_20ms();
        os_delay(20);
    }
}

static void int_to_str(char *dst, const char *prefix, uint16_t val) {
    int i = 0;
    while (prefix[i] != '\0') {
        dst[i] = prefix[i];
        i++;
    }
    char tmp[6];
    int t = 0;
    if (val == 0) {
        tmp[t++] = '0';
    } else {
        while (val > 0) {
            tmp[t++] = (char)('0' + (val % 10));
            val /= 10;
        }
    }
    for (int j = t - 1; j >= 0; j--) {
        dst[i++] = tmp[j];
    }
    dst[i] = '\0';
}

static void draw_score_box(uint16_t score, uint16_t best) {
    char str_score[24];
    char str_best[24];
    int_to_str(str_score, "SCORE: ", score);
    int_to_str(str_best,  "BEST:  ", best);

    BSP_LCD_SetTextColor(0xFF1B4965U);
    BSP_LCD_FillRect(20, 15, 160, 65);

    BSP_LCD_SetFont(&Font20);
    BSP_LCD_SetTextColor(0xFFFFFFFFU);
    BSP_LCD_SetBackColor(0xFF1B4965U);
    BSP_LCD_DisplayStringAt(25, 20, (uint8_t *)str_score, LEFT_MODE);

    BSP_LCD_SetFont(&Font16);
    BSP_LCD_SetTextColor(0xFFFFE66DU);
    BSP_LCD_SetBackColor(0xFF1B4965U);
    BSP_LCD_DisplayStringAt(25, 48, (uint8_t *)str_best, LEFT_MODE);
}

static void erase_bird(int16_t y) {
    if (y < 0) y = 0;
    if (y > 390) y = 390;
    BSP_LCD_SetTextColor(0xFF4EC0CAU);
    BSP_LCD_FillRect(160, y, 52, 30);
}

static void draw_bird(int16_t y) {
    if (y < 0) y = 0;
    if (y > 390) y = 390;
    /* bird_body */
    BSP_LCD_SetTextColor(0xFFF7D02CU);
    BSP_LCD_FillRect(160, y, 40, 30);
    /* bird_wing */
    BSP_LCD_SetTextColor(0xFFE09F3EU);
    BSP_LCD_FillRect(165, y + 8, 18, 14);
    /* bird_eye */
    BSP_LCD_SetTextColor(0xFFFFFFFFU);
    BSP_LCD_FillRect(185, y + 4, 10, 10);
    /* bird_pupil */
    BSP_LCD_SetTextColor(0xFF000000U);
    BSP_LCD_FillRect(191, y + 6, 4, 6);
    /* bird_beak */
    BSP_LCD_SetTextColor(0xFFE76F51U);
    BSP_LCD_FillRect(198, y + 12, 12, 10);
}

static void erase_pipe(int16_t x) {
    if (x >= -70 && x < 800) {
        int16_t draw_x = (x < 0) ? 0 : x;
        int16_t draw_w = 70;
        if (x < 0) draw_w += x;
        if (draw_x + draw_w > 800) draw_w = 800 - draw_x;
        if (draw_w > 0) {
            BSP_LCD_SetTextColor(0xFF4EC0CAU);
            BSP_LCD_FillRect(draw_x, 0, draw_w, 420);
        }
    }
}

static void draw_pipe(int16_t x, int16_t gap_y) {
    if (x <= -70 || x >= 800) return;

    int16_t top_rim_y = gap_y - 65 - 25;
    int16_t bot_rim_y = gap_y + 65;

    /* Thân trên cọc */
    if (top_rim_y > 0) {
        int16_t bx = x + 5;
        int16_t bw = 60;
        if (bx < 0) { bw += bx; bx = 0; }
        if (bx + bw > 800) bw = 800 - bx;
        if (bw > 0) {
            BSP_LCD_SetTextColor(0xFF73BF2EU);
            BSP_LCD_FillRect(bx, 0, bw, top_rim_y);
        }
    }
    /* Vành trên cọc */
    int16_t rx = x;
    int16_t rw = 70;
    if (rx < 0) { rw += rx; rx = 0; }
    if (rx + rw > 800) rw = 800 - rx;
    if (rw > 0 && top_rim_y >= 0 && top_rim_y + 25 <= 420) {
        BSP_LCD_SetTextColor(0xFF558022U);
        BSP_LCD_FillRect(rx, top_rim_y, rw, 25);
    }
    /* Vành dưới cọc */
    if (rw > 0 && bot_rim_y >= 0 && bot_rim_y + 25 <= 420) {
        BSP_LCD_SetTextColor(0xFF558022U);
        BSP_LCD_FillRect(rx, bot_rim_y, rw, 25);
    }
    /* Thân dưới cọc */
    int16_t bot_body_y = bot_rim_y + 25;
    if (bot_body_y < 420) {
        int16_t bx = x + 5;
        int16_t bw = 60;
        if (bx < 0) { bw += bx; bx = 0; }
        if (bx + bw > 800) bw = 800 - bx;
        if (bw > 0) {
            BSP_LCD_SetTextColor(0xFF73BF2EU);
            BSP_LCD_FillRect(bx, bot_body_y, bw, 420 - bot_body_y);
        }
    }
}

static void render_play_frame(const game_snapshot_t *snap, bool is_first) {
    static int16_t s_old_bird_y  = 210;
    static int16_t s_old_pipe1_x = 380;
    static int16_t s_old_pipe2_x = 660;
    static uint16_t s_old_score  = 0xFFFF;

    int16_t curr_bird_y = snap->bird_y >> 3;

    if (is_first) {
        s_old_bird_y  = curr_bird_y;
        s_old_pipe1_x = snap->pipe1_x;
        s_old_pipe2_x = snap->pipe2_x;
        s_old_score   = 0xFFFF;
        draw_score_box(snap->score, snap->best_score);
        return;
    }

    /* 1. Xoá dải cũ của cọc và vẽ lại vị trí mới */
    if (snap->pipe1_x != s_old_pipe1_x) {
        erase_pipe(s_old_pipe1_x);
        draw_pipe(snap->pipe1_x, snap->pipe1_gap_y);
        s_old_pipe1_x = snap->pipe1_x;
    }
    if (snap->pipe2_x != s_old_pipe2_x) {
        erase_pipe(s_old_pipe2_x);
        draw_pipe(snap->pipe2_x, snap->pipe2_gap_y);
        s_old_pipe2_x = snap->pipe2_x;
    }

    /* 2. Xoá vị trí cũ của chim và vẽ vị trí mới (vẽ sau cọc để chim luôn nổi lên) */
    if (curr_bird_y != s_old_bird_y) {
        erase_bird(s_old_bird_y);
        draw_bird(curr_bird_y);
        s_old_bird_y = curr_bird_y;
    }

    /* 3. Cập nhật ô điểm số khi điểm thay đổi hoặc cọc đi qua vùng HUD */
    if (snap->score != s_old_score ||
        (snap->pipe1_x >= 0 && snap->pipe1_x <= 190) ||
        (snap->pipe2_x >= 0 && snap->pipe2_x <= 190)) {
        draw_score_box(snap->score, snap->best_score);
        s_old_score = snap->score;
    }
}

/* =========================================================================
 * 3. Tác vụ Task_Render (Ưu tiên 1, Chu kỳ 33 ms ~ 30 FPS)
 * ========================================================================= */
static void task_render_fn(void *arg) {
    (void)arg;
    game_snapshot_t snap;
    game_state_t prev_state = (game_state_t)0xFF;

    while (1) {
        game_get_snapshot(&snap);

        if (snap.state != prev_state) {
            prev_state = snap.state;
            if (snap.state == GAME_STATE_START) {
                ui_ve_batdau();
            } else if (snap.state == GAME_STATE_PLAY) {
                ui_ve_choi();
                render_play_frame(&snap, true);
            } else if (snap.state == GAME_STATE_PAUSE) {
                /* Giữ nguyên khung hình hiện tại */
            } else if (snap.state == GAME_STATE_GAMEOVER) {
                ui_ve_gameover();
            }
        } else if (snap.state == GAME_STATE_PLAY) {
            /* Vẽ động theo dirty-rect mỗi 33 ms */
            render_play_frame(&snap, false);
        }

        os_delay(33);
    }
}

/* =========================================================================
 * 4. Tác vụ Task_Heartbeat (Ưu tiên 1, Chu kỳ 500 ms)
 * ========================================================================= */
static void task_heartbeat_fn(void *arg) {
    (void)arg;
    while (1) {
        os_delay(500);
    }
}

/* =========================================================================
 * 5. Tác vụ Task_Idle (Ưu tiên 0, Liên tục khi CPU rảnh)
 * ========================================================================= */
static void task_idle_fn(void *arg) {
    (void)arg;
    while (1) {
        __asm volatile ("wfi\n");
        os_yield();
    }
}

/* =========================================================================
 * Điểm vào chính của chương trình (main)
 * ========================================================================= */
int main(void) {
    /* Khởi tạo thư viện HAL và thiết lập xung nhịp 180 MHz */
    HAL_Init();
    SystemClock_Config();
    button_init();

    /* Khởi tạo phần cứng màn hình LCD OTM8009A trên SDRAM ngoài */
    BSP_LCD_Init();
    BSP_LCD_LayerDefaultInit(LTDC_ACTIVE_LAYER_BACKGROUND, LCD_FB_START_ADDRESS);
    BSP_LCD_SelectLayer(LTDC_ACTIVE_LAYER_BACKGROUND);
    BSP_LCD_DisplayOn();

    /* Khởi tạo cảm ứng màn hình FT6206/FT6336G */
    BSP_TS_Init(800, 480);

    /* Khởi tạo nhân RTOS và mô hình game */
    os_init();
    game_init();

    /* Đăng ký 5 tác vụ độc lập theo đúng bảng phân bổ ADR-04 */
    os_task_create(&s_tcb_input, "Input", task_input_fn, NULL,
                   s_stack_input, 256, 3);

    os_task_create(&s_tcb_logic, "Logic", task_logic_fn, NULL,
                   s_stack_logic, 512, 2);

    os_task_create(&s_tcb_render, "Render", task_render_fn, NULL,
                   s_stack_render, 1024, 1);

    os_task_create(&s_tcb_heartbeat, "Heartbeat", task_heartbeat_fn, NULL,
                   s_stack_heartbeat, 128, 1);

    os_task_create(&s_tcb_idle, "Idle", task_idle_fn, NULL,
                   s_stack_idle, 128, 0);

    /* Bắt đầu đa nhiệm thời gian thực (Never Returns) */
    os_start();

    return 0;
}
