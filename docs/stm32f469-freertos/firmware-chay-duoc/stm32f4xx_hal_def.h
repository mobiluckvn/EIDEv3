/**
  * Minimal stm32f4xx_hal_def.h for STM32F4 HAL drivers
  */
#ifndef __STM32F4xx_HAL_DEF
#define __STM32F4xx_HAL_DEF

#ifdef __cplusplus
 extern "C" {
#endif

#include "stm32f469xx.h"
#include <stdint.h>
#include <stddef.h>

typedef enum 
{
  HAL_OK       = 0x00U,
  HAL_ERROR    = 0x01U,
  HAL_BUSY     = 0x02U,
  HAL_TIMEOUT  = 0x03U
} HAL_StatusTypeDef;

typedef enum 
{
  HAL_UNLOCKED = 0x00U,
  HAL_LOCKED   = 0x01U
} HAL_LockTypeDef;

#define HAL_MAX_DELAY      0xFFFFFFFFU

#define __HAL_LOCK(__HANDLE__)                                           \
                                do{                                       \
                                    if((__HANDLE__)->Lock == HAL_LOCKED)   \
                                    {                                      \
                                       return HAL_BUSY;                    \
                                    }                                      \
                                    else                                   \
                                    {                                      \
                                       (__HANDLE__)->Lock = HAL_LOCKED;    \
                                    }                                      \
                                  }while (0U)

#define __HAL_UNLOCK(__HANDLE__)                                          \
                                  do{                                       \
                                      (__HANDLE__)->Lock = HAL_UNLOCKED;    \
                                    }while (0U)

#define UNUSED(X) (void)X

#ifdef __cplusplus
}
#endif

#endif /* __STM32F4xx_HAL_DEF */
