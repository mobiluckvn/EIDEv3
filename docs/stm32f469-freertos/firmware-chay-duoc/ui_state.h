#ifndef UI_STATE_H
#define UI_STATE_H

#include <stdint.h>

typedef enum {
    UI_SCREEN_MAIN = 0,
    UI_SCREEN_DETAILS = 1
} ui_screen_t;

void UI_State_Init(void);
ui_screen_t UI_State_Get(void);
void UI_State_Set(ui_screen_t screen);
ui_screen_t UI_State_Toggle(void);
int UI_State_CheckTouch(uint16_t x, uint16_t y);

#endif /* UI_STATE_H */
