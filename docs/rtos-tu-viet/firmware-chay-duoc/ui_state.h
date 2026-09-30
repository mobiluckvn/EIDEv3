#ifndef UI_STATE_H
#define UI_STATE_H

#include <stdint.h>

typedef enum {
    UI_SCREEN_MAIN = 0,
    UI_SCREEN_DETAILS = 1,
    UI_SCREEN_HELLO = 2
} ui_screen_t;

typedef enum {
    UI_BTN_NONE = 0,
    UI_BTN_DETAILS = 1,
    UI_BTN_HELLO = 2,
    UI_BTN_BACK = 3
} ui_btn_t;

void UI_State_Init(void);
ui_screen_t UI_State_Get(void);
void UI_State_Set(ui_screen_t screen);
ui_screen_t UI_State_Toggle(void);
ui_btn_t UI_State_CheckTouchBtn(uint16_t x, uint16_t y);
int UI_State_CheckTouch(uint16_t x, uint16_t y);
int UI_State_HandleTouch(uint16_t x, uint16_t y);

#endif /* UI_STATE_H */
