/**
  * @file ui.c
  * @brief Giao dien hien thi LCD va xu ly nut bam cam ung cho STM32F469I-DISCO
  */
#include "ui.h"
#include "ui_state.h"
#include "stm32469i_discovery.h"
#include "stm32469i_discovery_lcd.h"
#include "stm32469i_discovery_sdram.h"
#include "logo_ptit.h"
#include "string.h"

/* Toa do nut bam Chi tiet va Hello theo f-nguoi-23952598 (anh cho, chua co tai lieu):
 * Nhan Chi tiet: x=140, y=400, w=240, h=50
 * Nhan Hello: x=420, y=400, w=240, h=50
 */
#define BTN_DETAILS_X      140
#define BTN_DETAILS_Y      400
#define BTN_DETAILS_W      240
#define BTN_DETAILS_H      50

#define BTN_HELLO_X        420
#define BTN_HELLO_Y        400
#define BTN_HELLO_W        240
#define BTN_HELLO_H        50

/* Toa do nut Close quay lai man hinh chinh tren man hinh chi tiet va man hinh Hello */
#define BTN_BACK_X         280
#define BTN_BACK_Y         400
#define BTN_BACK_W         240
#define BTN_BACK_H         50

static void UI_DrawLogo(uint16_t x0, uint16_t y0)
{
    uint32_t width = BSP_LCD_GetXSize();
    uint32_t *fb = (uint32_t *)LCD_FB_START_ADDRESS;

    for (uint32_t r = 0; r < LOGO_PTIT_HEIGHT; r++) {
        for (uint32_t c = 0; c < LOGO_PTIT_WIDTH; c++) {
            uint32_t color = logo_ptit_data[r * LOGO_PTIT_WIDTH + c];
            if ((color & 0xFF000000) != 0) {
                fb[(y0 + r) * width + (x0 + c)] = color;
            }
        }
    }
}

/**
 * @brief Ve nut bam co vien ro net va chu can chinh giua dung hop nut
 */
static void UI_DrawButton(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                          uint32_t bg_color, uint32_t border_color, uint32_t text_color,
                          sFONT *font, const char *label)
{
    /* 1. Nen nut */
    BSP_LCD_SetTextColor(bg_color);
    BSP_LCD_FillRect(x, y, w, h);

    /* 2. Khung vien nut ro net */
    BSP_LCD_SetTextColor(border_color);
    BSP_LCD_DrawRect(x, y, w, h);
    BSP_LCD_DrawRect(x + 1, y + 1, w - 2, h - 2);

    /* 3. Can chu o chinh giua hop nut */
    uint32_t len = 0;
    while (label[len] != '\0') {
        len++;
    }
    uint16_t text_width = len * font->Width;
    uint16_t text_x = x + ((w > text_width) ? ((w - text_width) / 2) : 0);
    uint16_t text_y = y + ((h > font->Height) ? ((h - font->Height) / 2) : 0);

    BSP_LCD_SetBackColor(bg_color);
    BSP_LCD_SetTextColor(text_color);
    BSP_LCD_SetFont(font);
    BSP_LCD_DisplayStringAt(text_x, text_y, (uint8_t *)label, LEFT_MODE);
}

void UI_Init(void)
{
    BSP_SDRAM_Init();
    BSP_LCD_Init();
    BSP_LCD_LayerDefaultInit(0, LCD_FB_START_ADDRESS);
    BSP_LCD_SelectLayer(0);
    BSP_LCD_DisplayOn();
    UI_ShowMainScreen();
}

void UI_ShowMainScreen(void)
{
    UI_State_Set(UI_SCREEN_MAIN);

    BSP_LCD_Clear(LCD_COLOR_WHITE);

    /* Logo PTIT */
    UI_DrawLogo(30, 120);

    /* Thong tin De tai & Hoc vien */
    BSP_LCD_SetBackColor(LCD_COLOR_WHITE);
    
    BSP_LCD_SetTextColor(LCD_COLOR_RED);
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_DisplayStringAt(0, 30, (uint8_t *)"HOC VIEN CONG NGHE BUU CHINH VIEN THONG", CENTER_MODE);
    BSP_LCD_DisplayStringAt(0, 55, (uint8_t *)"KHOA KY THUAT DIEN TU 1", CENTER_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_DARKBLUE);
    BSP_LCD_SetFont(&Font20);
    BSP_LCD_DisplayStringAt(300, 130, (uint8_t *)"DE AN TOT NGHIEP", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 160, (uint8_t *)"HE THONG TAC TU EIDE v3", LEFT_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_BLACK);
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_DisplayStringAt(300, 210, (uint8_t *)"DT: PHAT TRIEN PHAN MEM NHUNG", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 240, (uint8_t *)"CO UNG DUNG TRI TUE NHAN TAO(AI)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 280, (uint8_t *)"Hoc vien  : Vu Tri Cong", LEFT_MODE);
    BSP_LCD_DisplayStringAt(300, 310, (uint8_t *)"GVHD      : TS. Nguyen Trung Hieu", LEFT_MODE);

    /* Nut 1: Thu gon nut Chi tiet (ben trai) theo f-nguoi-23952598 */
    UI_DrawButton(BTN_DETAILS_X, BTN_DETAILS_Y, BTN_DETAILS_W, BTN_DETAILS_H,
                  LCD_COLOR_BLUE, LCD_COLOR_DARKBLUE, LCD_COLOR_WHITE,
                  &Font20, "Chi tiet");

    /* Nut 2: Nut Hello bo sung (ben phai) theo f-nguoi-23952598 */
    UI_DrawButton(BTN_HELLO_X, BTN_HELLO_Y, BTN_HELLO_W, BTN_HELLO_H,
                  LCD_COLOR_GREEN, LCD_COLOR_DARKBLUE, LCD_COLOR_WHITE,
                  &Font20, "Hello");
}

void UI_ShowDetailsScreen(void)
{
    UI_State_Set(UI_SCREEN_DETAILS);

    BSP_LCD_Clear(LCD_COLOR_DARKBLUE);

    BSP_LCD_SetBackColor(LCD_COLOR_DARKBLUE);
    BSP_LCD_SetTextColor(LCD_COLOR_YELLOW);
    BSP_LCD_SetFont(&Font20);
    BSP_LCD_DisplayStringAt(0, 25, (uint8_t *)"=== TINH NANG HE THONG EIDE v3 ===", CENTER_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_DisplayStringAt(50, 75,  (uint8_t *)"1. He dieu hanh FreeRTOS v10 da tac vu:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(80, 100, (uint8_t *)"- Task 1: Blink 4 LEDs (PG6, PD4, PD5, PK3)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(80, 125, (uint8_t *)"- Task 2: Giam sat nut bam User PA0 (Debounce)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(80, 150, (uint8_t *)"- Task 3: Quan ly giao dien LCD & cam ung DSI", LEFT_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(50, 185, (uint8_t *)"2. Phan cung STM32F469NIH6 Cortex-M4F:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(80, 210, (uint8_t *)"- Man hinh DSI 800x480 IC OTM8009A", LEFT_MODE);
    BSP_LCD_DisplayStringAt(80, 235, (uint8_t *)"- Bo nho mo rong SDRAM FMC (FrameBuffer)", LEFT_MODE);
    BSP_LCD_DisplayStringAt(80, 260, (uint8_t *)"- Cam ung dien dung FocalTech FT6206 qua I2C1", LEFT_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_WHITE);
    BSP_LCD_DisplayStringAt(50, 295, (uint8_t *)"3. Hien phap tac tu PRS-16 v3:", LEFT_MODE);
    BSP_LCD_SetTextColor(LCD_COLOR_CYAN);
    BSP_LCD_DisplayStringAt(80, 320, (uint8_t *)"- Datasheet la nguon su that, 4 tang tin cay", LEFT_MODE);
    BSP_LCD_DisplayStringAt(80, 345, (uint8_t *)"- 10 dieu khoan hiem hoa & kien truc co khao chung", LEFT_MODE);

    /* Nut cam ung Close tren man hinh chi tiet */
    UI_DrawButton(BTN_BACK_X, BTN_BACK_Y, BTN_BACK_W, BTN_BACK_H,
                  LCD_COLOR_RED, LCD_COLOR_WHITE, LCD_COLOR_WHITE,
                  &Font20, "Close");
}

void UI_ShowHelloScreen(void)
{
    UI_State_Set(UI_SCREEN_HELLO);

    BSP_LCD_Clear(LCD_COLOR_WHITE);

    BSP_LCD_SetBackColor(LCD_COLOR_WHITE);

    /* Tieu de Xin chao */
    BSP_LCD_SetTextColor(LCD_COLOR_DARKBLUE);
    BSP_LCD_SetFont(&Font24);
    BSP_LCD_DisplayStringAt(0, 150, (uint8_t *)"Xin chao", CENTER_MODE);

    /* Loi chao chi tiet */
    BSP_LCD_SetTextColor(LCD_COLOR_BLACK);
    BSP_LCD_SetFont(&Font20);
    BSP_LCD_DisplayStringAt(0, 210, (uint8_t *)"Chao mung ban den voi He thong EIDE v3!", CENTER_MODE);

    BSP_LCD_SetTextColor(LCD_COLOR_BLUE);
    BSP_LCD_SetFont(&Font16);
    BSP_LCD_DisplayStringAt(0, 260, (uint8_t *)"Bo mach STM32F469I-DISCO san sang phuc vu", CENTER_MODE);

    /* Nut cam ung Close de quay lai man hinh chinh */
    UI_DrawButton(BTN_BACK_X, BTN_BACK_Y, BTN_BACK_W, BTN_BACK_H,
                  LCD_COLOR_RED, LCD_COLOR_DARKBLUE, LCD_COLOR_WHITE,
                  &Font20, "Close");
}

void UI_ToggleScreen(void)
{
    if (UI_State_Toggle() == UI_SCREEN_DETAILS) {
        UI_ShowDetailsScreen();
    } else {
        UI_ShowMainScreen();
    }
}

ui_screen_t UI_GetCurrentScreen(void)
{
    return UI_State_Get();
}

int UI_HandleTouch(uint16_t x, uint16_t y)
{
    if (UI_State_HandleTouch(x, y)) {
        ui_screen_t scr = UI_State_Get();
        if (scr == UI_SCREEN_MAIN) {
            UI_ShowMainScreen();
        } else if (scr == UI_SCREEN_DETAILS) {
            UI_ShowDetailsScreen();
        } else if (scr == UI_SCREEN_HELLO) {
            UI_ShowHelloScreen();
        }
        return 1;
    }
    return 0;
}
