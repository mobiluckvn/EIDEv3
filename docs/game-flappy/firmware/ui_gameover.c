/* ĐỪNG SỬA TAY — tệp này do `screen.codegen` của EIDE sinh ra từ hiện vật
 * `ui_screen:gameover`. Sửa ở đây sẽ bị ghi đè lần sinh sau; sửa bản thiết kế.
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

void ui_ve_gameover(void)
{
  BSP_LCD_Clear(0xFF4EC0CAU);
  /* ground_grass — rect */
  BSP_LCD_SetTextColor(0xFF5EE270U);
  BSP_LCD_FillRect(0, 420, 800, 15);
  /* ground_dirt — rect */
  BSP_LCD_SetTextColor(0xFFDED895U);
  BSP_LCD_FillRect(0, 435, 800, 45);
  /* ground_line — line */
  BSP_LCD_SetTextColor(0xFF41984CU);
  BSP_LCD_DrawHLine(0, 420, 800);
  /* over_bg — rect */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(220, 45, 360, 60);
  /* over_txt — text */
  BSP_LCD_SetTextColor(0xFFE76F51U);
  BSP_LCD_FillRect(230, 57, 340, 36);
  BSP_LCD_SetFont(&Font24);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFFE76F51U);
  BSP_LCD_DisplayStringAt(323, 57, (uint8_t *)"GAME OVER", LEFT_MODE);
  /* panel_bg — rect */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(220, 125, 360, 140);
  /* score_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(240, 140, 320, 26);
  BSP_LCD_SetFont(&Font20);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(337, 140, (uint8_t *)"SCORE: 18", LEFT_MODE);
  /* best_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(240, 180, 320, 26);
  BSP_LCD_SetFont(&Font20);
  BSP_LCD_SetTextColor(0xFFFFE66DU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(302, 180, (uint8_t *)"BEST SCORE: 45", LEFT_MODE);
  /* medal_txt — text */
  BSP_LCD_SetTextColor(0xFF1B4965U);
  BSP_LCD_FillRect(240, 220, 320, 24);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFA8DADCU);
  BSP_LCD_SetBackColor(0xFF1B4965U);
  BSP_LCD_DisplayStringAt(328, 220, (uint8_t *)"MEDAL: SILVER", LEFT_MODE);
  /* btn_restart — button */
  BSP_LCD_SetTextColor(0xFF2A9D8FU);
  BSP_LCD_FillRect(330, 285, 140, 84);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_DrawRect(330, 285, 140, 84);
  BSP_LCD_SetFont(&Font20);
  BSP_LCD_SetTextColor(0xFFFFFFFFU);
  BSP_LCD_SetBackColor(0xFF2A9D8FU);
  BSP_LCD_DisplayStringAt(351, 317, (uint8_t *)"RESTART", LEFT_MODE);
  /* replay_bg — rect */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(170, 385, 460, 40);
  /* replay_txt — text */
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_FillRect(180, 393, 440, 24);
  BSP_LCD_SetFont(&Font16);
  BSP_LCD_SetTextColor(0xFFF4A261U);
  BSP_LCD_SetBackColor(0xFF264653U);
  BSP_LCD_DisplayStringAt(218, 393, (uint8_t *)"PRESS PA0 OR TAP BUTTON TO REPLAY", LEFT_MODE);
  /* sub_txt — text */
  BSP_LCD_SetTextColor(0xFFDED895U);
  BSP_LCD_FillRect(200, 448, 400, 20);
  BSP_LCD_SetFont(&Font12);
  BSP_LCD_SetTextColor(0xFF264653U);
  BSP_LCD_SetBackColor(0xFFDED895U);
  BSP_LCD_DisplayStringAt(309, 448, (uint8_t *)"STM32F469I-DISCO RTOS GAME", LEFT_MODE);
}
