/**
  * Minimal stm32f4xx_hal.h wrapper for STM32F469I-DISCO LCD & SDRAM
  */
#ifndef __STM32F4xx_HAL_H
#define __STM32F4xx_HAL_H

#ifdef __cplusplus
 extern "C" {
#endif

#include "stm32f4xx_hal_def.h"
#include <string.h>

/* Include HAL drivers */
#include "stm32f4xx_ll_fmc.h"
#include "stm32f4xx_hal_sdram.h"
#include "stm32f4xx_hal_dsi.h"
#include "stm32f4xx_hal_ltdc.h"
#include "stm32f4xx_hal_dma2d.h"

uint32_t HAL_GetTick(void);
void HAL_Delay(uint32_t Delay);

#ifdef __cplusplus
}
#endif

#endif /* __STM32F4xx_HAL_H */
