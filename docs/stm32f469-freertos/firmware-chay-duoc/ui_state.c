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

UI_STATE_API int UI_State_CheckTouch(uint16_t x, uint16_t y)
{
    int in_x = (x >= 150 && x <= 650);
    int in_y = ((y >= 380 && y <= 460) || (y >= 20 && y <= 100));
    int in_swap = (y >= 150 && y <= 650) && ((x >= 380 && x <= 460) || (x >= 20 && x <= 100));

    if ((in_x && in_y) || in_swap) {
        return 1;
    }
    return 0;
}
