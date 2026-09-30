#include "ui_state.h"

#ifndef UI_STATE_API
#define UI_STATE_API
#endif

static ui_screen_t current_ui_state = UI_SCREEN_MAIN;

UI_STATE_API void UI_State_Init(void)
{
    current_ui_state = UI_SCREEN_MAIN;
}

UI_STATE_API ui_screen_t UI_State_Get(void)
{
    return current_ui_state;
}

UI_STATE_API void UI_State_Set(ui_screen_t screen)
{
    current_ui_state = screen;
}

UI_STATE_API ui_screen_t UI_State_Toggle(void)
{
    if (current_ui_state == UI_SCREEN_MAIN) {
        current_ui_state = UI_SCREEN_DETAILS;
    } else {
        current_ui_state = UI_SCREEN_MAIN;
    }
    return current_ui_state;
}

static void normalize_touch(uint16_t x, uint16_t y, uint16_t *tx, uint16_t *ty)
{
    /* Kiem tra toa do bi hoan doi truc do huong cam ung FT6206 */
    if ((y >= 150 && y <= 650) && ((x >= 380 && x <= 460) || (x >= 20 && x <= 100))) {
        *tx = y;
        *ty = x;
    } else {
        *tx = x;
        *ty = y;
    }

    /* Kiem tra truc Y bi dao chieu */
    if (*ty >= 20 && *ty <= 100) {
        *ty = 480 - *ty;
    }
}

UI_STATE_API ui_btn_t UI_State_CheckTouchBtn(uint16_t x, uint16_t y)
{
    uint16_t tx = 0, ty = 0;
    normalize_touch(x, y, &tx, &ty);

    /* Vung nut tong the theo chieu doc Y trong khoang [380, 460] */
    if (ty < 380 || ty > 460) {
        return UI_BTN_NONE;
    }

    /* Vung ngang X hop le tu 150 den 650 */
    if (tx < 150 || tx > 650) {
        return UI_BTN_NONE;
    }

    if (current_ui_state == UI_SCREEN_MAIN) {
        /* Nua trai la nut Chi tiet, nua phai la nut Hello */
        if (tx <= 400) {
            return UI_BTN_DETAILS;
        } else {
            return UI_BTN_HELLO;
        }
    } else {
        /* Tren man hinh DETAILS va HELLO, nut Close o giua */
        return UI_BTN_BACK;
    }
}

UI_STATE_API int UI_State_CheckTouch(uint16_t x, uint16_t y)
{
    return (UI_State_CheckTouchBtn(x, y) != UI_BTN_NONE) ? 1 : 0;
}

UI_STATE_API int UI_State_HandleTouch(uint16_t x, uint16_t y)
{
    ui_btn_t btn = UI_State_CheckTouchBtn(x, y);

    if (current_ui_state == UI_SCREEN_MAIN) {
        if (btn == UI_BTN_DETAILS) {
            current_ui_state = UI_SCREEN_DETAILS;
            return 1;
        } else if (btn == UI_BTN_HELLO) {
            current_ui_state = UI_SCREEN_HELLO;
            return 1;
        }
    } else {
        if (btn != UI_BTN_NONE) {
            current_ui_state = UI_SCREEN_MAIN;
            return 1;
        }
    }

    return 0;
}
