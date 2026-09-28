#ifndef UI_H
#define UI_H

#include <stdint.h>

typedef enum {
    UI_SCREEN_MAIN = 0,
    UI_SCREEN_DETAILS = 1
} ui_screen_t;

void UI_Init(void);
void UI_ShowMainScreen(void);
void UI_ShowDetailsScreen(void);
void UI_ToggleScreen(void);
ui_screen_t UI_GetCurrentScreen(void);

/**
 * @brief Xu ly su kien cham cam ung tren man hinh.
 * @param x Toa do X diem cham
 * @param y Toa do Y diem cham
 * @return 1 neu cham trung nut va da chuyen man hinh, 0 neu khong.
 */
int UI_HandleTouch(uint16_t x, uint16_t y);

#endif /* UI_H */
