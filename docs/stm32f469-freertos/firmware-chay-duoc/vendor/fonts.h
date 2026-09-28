#ifndef __FONTS_H
#define __FONTS_H

#include <stdint.h>

typedef struct _tFont
{    
  const uint8_t *table;
  uint16_t Width;
  uint16_t Height;
} sFONT;

extern sFONT Font24;
extern sFONT Font20;
extern sFONT Font16;
extern sFONT Font12;
extern sFONT Font8;

#endif /* __FONTS_H */
