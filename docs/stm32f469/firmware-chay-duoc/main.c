#include "stm32f4xx_hal.h"
#include "stm32469i_discovery.h"
#include "stm32469i_discovery_lcd.h"
#include "stm32469i_discovery_sdram.h"
#include "logo_ptit.h"

/* Mang luu cac thanh ghi trang thai DCS cua panel OTM8009A trong .data */
volatile uint8_t g_panel_status[8] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x12, 0x34};
volatile uint8_t g_panel_dcs[8] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x12, 0x34};

/* Mang luu ma tra ve cua tung lan goi DSI_IO_ReadCmd (LCD_OK=0, LCD_ERROR=1, LCD_TIMEOUT=2) */
volatile int32_t g_panel_read_ret[8] = {-1, -1, -1, -1, -1, -1, -1, -1};

/* Mang luu trang thai panel do duoc o che do Command Mode (luc khoi tao truoc Video Mode) */
volatile uint8_t g_panel_cmd_status[8] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x12, 0x34};
volatile int32_t g_panel_cmd_ret[8]    = {-1, -1, -1, -1, -1, -1, -1, -1};

/* Luu ma tra ve cua OTM8009A_Init va 4 lenh HAL_DSI_ShortWrite (0xEEEEEEEE = chua chay) */
volatile uint32_t g_otm8009a_init_ret = 0xEEEEEEEE;
volatile uint32_t g_dsi_write_ret[4]  = {0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE, 0xEEEEEEEE};

/* Bien kiem tra phep thu ghi va doc lai do sang panel OTM8009A */
volatile uint8_t  g_bright_before      = 0xEE;
volatile uint8_t  g_bright_val_written = 0x88;
volatile uint8_t  g_bright_after       = 0xEE;
volatile uint32_t g_bright_write_ret   = 0xEEEEEEEE;
volatile int32_t  g_bright_read_ret    = -1;

static void SystemClock_Config(void);
static void DrawLogo(uint32_t x0, uint32_t y0);

int main(void)
{
  /* 1. Khoi tao HAL */
  HAL_Init();

  /* 2. Cau hinh xung nhip he thong */
  SystemClock_Config();

  /* 3. Khoi tao man hinh LCD */
  if (BSP_LCD_Init() != LCD_OK)
  {
    while (1)
    {
      HAL_Delay(100);
    }
  }

  /* 4. Khoi tao layer mac dinh tai vung nho SDRAM */
  BSP_LCD_LayerDefaultInit(LTDC_ACTIVE_LAYER_BACKGROUND, LCD_FB_START_ADDRESS);
  BSP_LCD_SelectLayer(LTDC_ACTIVE_LAYER_BACKGROUND);

  /* 5. Bat hien thi man hinh */
  BSP_LCD_DisplayOn();

  /* 5b. Thong chuoi DSI va dua panel ra khoi reset */
  __HAL_RCC_GPIOH_CLK_ENABLE();
  GPIO_InitTypeDef gpio_xres = {0};
  gpio_xres.Pin = GPIO_PIN_7;
  gpio_xres.Mode = GPIO_MODE_OUTPUT_PP;
  gpio_xres.Pull = GPIO_PULLUP;
  gpio_xres.Speed = GPIO_SPEED_HIGH;
  HAL_GPIO_Init(GPIOH, &gpio_xres);
  HAL_GPIO_WritePin(GPIOH, GPIO_PIN_7, GPIO_PIN_SET);

  /* Xoa SHTDN (bit 3) va bat DSIEN (bit 0) tren DSI Wrapper */
  DSI->WCR &= ~DSI_WCR_SHTDN;
  DSI->WCR |= DSI_WCR_DSIEN;

/* 5c. Gui truc tiep cac lenh khoi tao OTM8009A qua DSI DCS Short Write */
  extern DSI_HandleTypeDef hdsi_eval;
  extern int32_t DSI_IO_ReadCmd(uint32_t Reg, uint8_t *pData, uint32_t Size);

  /* Bat BTA flow control tren DSI Host */
  HAL_DSI_ConfigFlowControl(&hdsi_eval, DSI_FLOW_CONTROL_BTA);

  /* 0x11: Sleep Out */
  g_dsi_write_ret[0] = (uint32_t)HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11, 0x00);
  HAL_Delay(120);
  /* 0x51: WRDISBV - dat do sang toi da (0xFF) */
  g_dsi_write_ret[1] = (uint32_t)HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x51, 0xFF);
  /* 0x53: WRCTRLD - bat BCTRL (0x2C: BCTRL=1, DD=1, BL=1) */
  g_dsi_write_ret[2] = (uint32_t)HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x53, 0x2C);
  /* 0x29: Display On */
  g_dsi_write_ret[3] = (uint32_t)HAL_DSI_ShortWrite(&hdsi_eval, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29, 0x00);
  HAL_Delay(50);

  /* Doc cac thanh ghi trang thai DCS cua panel va luu ma tra ve */
  g_panel_read_ret[0] = DSI_IO_ReadCmd(0xDA, (uint8_t *)&g_panel_status[0], 1); g_panel_dcs[0] = g_panel_status[0]; /* ID1 */
  g_panel_read_ret[1] = DSI_IO_ReadCmd(0x0A, (uint8_t *)&g_panel_status[1], 1); g_panel_dcs[1] = g_panel_status[1]; /* Power Mode */
  g_panel_read_ret[2] = DSI_IO_ReadCmd(0x0B, (uint8_t *)&g_panel_status[2], 1); g_panel_dcs[2] = g_panel_status[2]; /* MADCTL */
  g_panel_read_ret[3] = DSI_IO_ReadCmd(0x0C, (uint8_t *)&g_panel_status[3], 1); g_panel_dcs[3] = g_panel_status[3]; /* COLMOD */
  g_panel_read_ret[4] = DSI_IO_ReadCmd(0x52, (uint8_t *)&g_panel_status[4], 1); g_panel_dcs[4] = g_panel_status[4]; /* Brightness */
  g_panel_read_ret[5] = DSI_IO_ReadCmd(0x54, (uint8_t *)&g_panel_status[5], 1); g_panel_dcs[5] = g_panel_status[5]; /* CTRL Display */
  g_panel_read_ret[6] = DSI_IO_ReadCmd(0x0F, (uint8_t *)&g_panel_status[6], 1); g_panel_dcs[6] = g_panel_status[6]; /* Self-Diagnostic */
  g_panel_read_ret[7] = DSI_IO_ReadCmd(0x0D, (uint8_t *)&g_panel_status[7], 1); g_panel_dcs[7] = g_panel_status[7]; /* Image Mode */

  /* 6. Xoa man hinh ve mau trang */
  BSP_LCD_Clear(LCD_COLOR_WHITE);

  uint32_t lcd_w = BSP_LCD_GetXSize();

  /* 7. Ve Logo PTIT (240x240) ra giua man hinh */
  uint32_t logo_x = (lcd_w > LOGO_PTIT_WIDTH) ? ((lcd_w - LOGO_PTIT_WIDTH) / 2) : 0;
  uint32_t logo_y = 30;
  DrawLogo(logo_x, logo_y);

  /* 8. Hien thi 4 dong chu thong tin theo yeu cau */
  BSP_LCD_SetBackColor(LCD_COLOR_WHITE);
  BSP_LCD_SetTextColor(LCD_COLOR_DARKBLUE);
  BSP_LCD_SetFont(&Font20);

  /* Dong 1: EIDE v3 — IDE nhung co tac tu dong tac gia */
  BSP_LCD_DisplayStringAt(0, 290, (uint8_t *)"EIDE v3 - IDE nhung co tac tu dong tac gia", CENTER_MODE);

  BSP_LCD_SetTextColor(LCD_COLOR_BLACK);
  BSP_LCD_SetFont(&Font16);

  /* Dong 2: Hoc vien: Vu Tri Cong */
  BSP_LCD_DisplayStringAt(0, 330, (uint8_t *)"Hoc vien: Vu Tri Cong", CENTER_MODE);

  /* Dong 3: Giang vien huong dan: TS. Nguyen Trung Hieu */
  BSP_LCD_DisplayStringAt(0, 360, (uint8_t *)"Giang vien huong dan: TS. Nguyen Trung Hieu", CENTER_MODE);

  BSP_LCD_SetTextColor(LCD_COLOR_RED);
  /* Dong 4: Hoc vien Cong nghe Buu chinh Vien thong */
  BSP_LCD_DisplayStringAt(0, 400, (uint8_t *)"Hoc vien Cong nghe Buu chinh Vien thong", CENTER_MODE);

  /* Dong 5: Trang thai DCS panel do o Command Mode va Video Mode */
  static const char hex_chars[] = "0123456789ABCDEF";
  char cmd_buf[48] = "CMD: ID=00 PWR=00 BRT=00 CTL=00";
  cmd_buf[8]  = hex_chars[(g_panel_cmd_status[0] >> 4) & 0x0F];
  cmd_buf[9]  = hex_chars[g_panel_cmd_status[0] & 0x0F];
  cmd_buf[15] = hex_chars[(g_panel_cmd_status[1] >> 4) & 0x0F];
  cmd_buf[16] = hex_chars[g_panel_cmd_status[1] & 0x0F];
  cmd_buf[22] = hex_chars[(g_panel_cmd_status[4] >> 4) & 0x0F];
  cmd_buf[23] = hex_chars[g_panel_cmd_status[4] & 0x0F];
  cmd_buf[29] = hex_chars[(g_panel_cmd_status[5] >> 4) & 0x0F];
  cmd_buf[30] = hex_chars[g_panel_cmd_status[5] & 0x0F];

  char vid_buf[48] = "VID: ID=00 PWR=00 BRT=00 CTL=00";
  vid_buf[8]  = hex_chars[(g_panel_dcs[0] >> 4) & 0x0F];
  vid_buf[9]  = hex_chars[g_panel_dcs[0] & 0x0F];
  vid_buf[15] = hex_chars[(g_panel_dcs[1] >> 4) & 0x0F];
  vid_buf[16] = hex_chars[g_panel_dcs[1] & 0x0F];
  vid_buf[22] = hex_chars[(g_panel_dcs[4] >> 4) & 0x0F];
  vid_buf[23] = hex_chars[g_panel_dcs[4] & 0x0F];
  vid_buf[29] = hex_chars[(g_panel_dcs[5] >> 4) & 0x0F];
  vid_buf[30] = hex_chars[g_panel_dcs[5] & 0x0F];

  BSP_LCD_SetTextColor(LCD_COLOR_BLACK);
  BSP_LCD_SetFont(&Font12);
  BSP_LCD_DisplayStringAt(0, 435, (uint8_t *)cmd_buf, CENTER_MODE);
  BSP_LCD_DisplayStringAt(0, 452, (uint8_t *)vid_buf, CENTER_MODE);

  while (1)
  {
    HAL_Delay(1000);
  }
}

static void DrawLogo(uint32_t x0, uint32_t y0)
{
  for (uint32_t y = 0; y < LOGO_PTIT_HEIGHT; y++)
  {
    for (uint32_t x = 0; x < LOGO_PTIT_WIDTH; x++)
    {
      uint32_t pixel = logo_ptit_data[y * LOGO_PTIT_WIDTH + x];
      uint8_t a = (pixel >> 24) & 0xFF;
      if (a > 0)
      {
        if (a == 255)
        {
          BSP_LCD_DrawPixel(x0 + x, y0 + y, pixel);
        }
        else
        {
          uint32_t r = (pixel >> 16) & 0xFF;
          uint32_t g = (pixel >> 8) & 0xFF;
          uint32_t b = pixel & 0xFF;
          r = (r * a + 255 * (255 - a)) / 255;
          g = (g * a + 255 * (255 - a)) / 255;
          b = (b * a + 255 * (255 - a)) / 255;
          BSP_LCD_DrawPixel(x0 + x, y0 + y, 0xFF000000UL | (r << 16) | (g << 8) | b);
        }
      }
    }
  }
}

static void SystemClock_Config(void)
{
  RCC_ClkInitTypeDef RCC_ClkInitStruct;
  RCC_OscInitTypeDef RCC_OscInitStruct;

  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

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

  HAL_PWREx_EnableOverDrive();

  RCC_ClkInitStruct.ClockType = (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2);
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV4;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV2;
  HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_ACR_LATENCY_5WS);
}
