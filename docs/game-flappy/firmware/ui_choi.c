/* ĐỪNG SỬA TAY — tệp này do `screen.codegen` của EIDE sinh ra từ hiện vật
 * `ui_screen:choi`. Sửa ở đây sẽ bị ghi đè lần sinh sau; sửa bản thiết kế.
 *
 * Panel: 800×480 px, hệ màu ARGB8888, driver OTM8009A, bus MIPI-DSI.
 *
 * TIỀN ĐỀ — hàm này chỉ VẼ. Trước khi gọi nó, dự án phải đã chạy:
 *   BSP_LCD_Init();  BSP_LCD_LayerDefaultInit(0, <địa chỉ bộ đệm khung>);
 *   BSP_LCD_SelectLayer(0);  BSP_LCD_DisplayOn();
 * Bộ sinh code KHÔNG sinh phần ấy: nó phụ thuộc script liên kết và cấu hình xung
 * nhịp của từng dự án, nên một bản “có vẻ đúng” cho nó là một tệp người dùng tưởng
 * dùng được.
 */

#include "stm32469i_discovery_lcd.h"

void ui_ve_choi(void)
{
  BSP_LCD_Clear(0xFF4EC0CAU);
  /* bg_cloud1 — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(80, 80, 120, 40);
  /* bg_cloud2 — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(350, 60, 160, 50);
  /* bg_cloud3 — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(620, 100, 130, 40);
  /* ground_grass — rect */
  BSP_LCD_SetTextColor(0xFF5EE270U);
  BSP_LCD_FillRect(0, 420, 800, 15);
  /* ground_dirt — rect */
  BSP_LCD_SetTextColor(0xFFDED895U);
  BSP_LCD_FillRect(0, 435, 800, 45);
  /* ground_line — rect */
  BSP_LCD_SetTextColor(0xFF41984CU);
  BSP_LCD_FillRect(0, 420, 800, 2);
  /* pipe1_top_body — rect */
  BSP_LCD_SetTextColor(0xFF73BF2EU);
  BSP_LCD_FillRect(385, 0, 60, 140);
  /* pipe1_top_rim — rect */
  BSP_LCD_SetTextColor(0xFF558022U);
  BSP_LCD_FillRect(380, 120, 70, 25);
  /* pipe1_bot_rim — rect */
  BSP_LCD_SetTextColor(0xFF558022U);
  BSP_LCD_FillRect(380, 275, 70, 25);
  /* pipe1_bot_body — rect */
  BSP_LCD_SetTextColor(0xFF73BF2EU);
  BSP_LCD_FillRect(385, 300, 60, 120);
  /* pipe2_top_body — rect */
  BSP_LCD_SetTextColor(0xFF73BF2EU);
  BSP_LCD_FillRect(665, 0, 60, 180);
  /* pipe2_top_rim — rect */
  BSP_LCD_SetTextColor(0xFF558022U);
  BSP_LCD_FillRect(660, 160, 70, 25);
  /* pipe2_bot_rim — rect */
  BSP_LCD_SetTextColor(0xFF558022U);
  BSP_LCD_FillRect(660, 315, 70, 25);
  /* pipe2_bot_body — rect */
  BSP_LCD_SetTextColor(0xFF73BF2EU);
  BSP_LCD_FillRect(665, 340, 60, 80);
  /* bird_body — rect */
  BSP_LCD_SetTextColor(0xFFF7D02CU);
  BSP_LCD_FillRect(160, 210, 40, 30);
  /* bird_wing — rect */
  BSP_LCD_SetTextColor(0xFFE09F3EU);
  BSP_LCD_FillRect(165, 218, 18, 14);
  /* bird_eye — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(185, 214, 10, 10);
  /* bird_pupil — rect */
  BSP_LCD_SetTextColor(0xFF000000U);
  BSP_LCD_FillRect(191, 216, 4, 6);
  /* bird_beak — rect */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(198, 222, 12, 10);
  /* hud_score_bg — rect */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(20, 15, 160, 65);
  /* hud_score_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(25, 20, 150, 25);
  BSP_LCD_SetFont(&Font20);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(25, 20, (uint8_t *)"SCORE: 12", LEFT_MODE);
  /* hud_best_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(25, 48, 150, 25);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFFFE66DU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(25, 48, (uint8_t *)"BEST:  45", LEFT_MODE);
  /* hud_bar_label — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(490, 20, 80, 20);
  BSP_LCD_SetFont(&Font12);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(502, 20, (uint8_t *)"FLAP PWR", LEFT_MODE);
  /* hud_pwr_bar — bar */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_DrawRect(575, 20, 85, 20);
  BSP_LCD_FillRect(576, 21, 70, 18);
  /* btn_pause — button */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(700, 15, 84, 84);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_DrawRect(700, 15, 84, 84);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFFE76F51U);
  BSP_LCD_DisplayStringAt(714, 49, (uint8_t *)"PAUSE", LEFT_MODE);
  /* banner_hint_bg — rect */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(180, 442, 440, 30);
  /* banner_hint_txt — text */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(185, 448, 430, 20);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFF4A261U);
  BSP_LCD_SetBackColor(0xFF264653U);
  BSP_LCD_DisplayStringAt(229, 448, (uint8_t *)"TAP SCREEN OR PRESS PA0 TO JUMP", LEFT_MODE);
}
