/* ĐỪNG SỬA TAY — tệp này do `screen.codegen` của EIDE sinh ra từ hiện vật
 * `ui_screen:batdau`. Sửa ở đây sẽ bị ghi đè lần sinh sau; sửa bản thiết kế.
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

void ui_ve_batdau(void)
{
  BSP_LCD_Clear(0xFF4EC0CAU);
  /* bg_cloud1 — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(100, 80, 120, 40);
  /* bg_cloud2 — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(550, 70, 150, 50);
  /* ground_grass — rect */
  BSP_LCD_SetTextColor(0xFF5EE270U);
  BSP_LCD_FillRect(0, 420, 800, 15);
  /* ground_dirt — rect */
  BSP_LCD_SetTextColor(0xFFDED895U);
  BSP_LCD_FillRect(0, 435, 800, 45);
  /* ground_line — line */
  BSP_LCD_SetTextColor(0xFF41984CU);
  BSP_LCD_DrawHLine(0, 420, 800);
  /* title_bg — rect */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(180, 60, 440, 70);
  /* title_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(190, 75, 420, 36);
  BSP_LCD_SetFont(&Font24);
  BSP_LCD_SetTextColor(0xFFFFE66DU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(306, 75, (uint8_t *)"FLAPPY BIRD", LEFT_MODE);
  /* bird_body — rect */
  BSP_LCD_SetTextColor(0xFFF7D02CU);
  BSP_LCD_FillRect(380, 165, 40, 30);
  /* bird_wing — rect */
  BSP_LCD_SetTextColor(0xFFE09F3EU);
  BSP_LCD_FillRect(385, 173, 18, 14);
  /* bird_eye — rect */
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_FillRect(405, 169, 10, 10);
  /* bird_pupil — rect */
  BSP_LCD_SetTextColor(0xFF000000U);
  BSP_LCD_FillRect(411, 171, 4, 6);
  /* bird_beak — rect */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(418, 177, 12, 10);
  /* btn_start — button */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(340, 235, 120, 84);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_DrawRect(340, 235, 120, 84);
  BSP_LCD_SetFont(&Font20);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFFE76F51U);
  BSP_LCD_DisplayStringAt(365, 267, (uint8_t *)"START", LEFT_MODE);
  /* guide_bg — rect */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(140, 345, 520, 50);
  /* guide_txt — text */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(150, 358, 500, 24);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFF4A261U);
  BSP_LCD_SetBackColor(0xFF264653U);
  BSP_LCD_DisplayStringAt(229, 358, (uint8_t *)"TAP SCREEN OR PRESS PA0 TO FLAP", LEFT_MODE);
  /* sub_txt — text */
  BSP_LCD_SetTextColor(0xFFDED895U);
  BSP_LCD_FillRect(200, 448, 400, 20);
  BSP_LCD_SetFont(&Font12);
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_SetBackColor(0xFFDED895U);
  BSP_LCD_DisplayStringAt(309, 448, (uint8_t *)"STM32F469I-DISCO RTOS GAME", LEFT_MODE);
}
