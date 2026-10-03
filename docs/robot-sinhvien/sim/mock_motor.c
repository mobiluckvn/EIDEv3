/* =========================================================================
 * BÀI KIỂM DỊCH THẲNG firmware/motor.cpp THAY VÌ DÙNG MOCK
 * ========================================================================= */
#include "avr/io.h"

#ifndef ISR
#define ISR(vector) void vector(void)
#endif

#ifndef asm
#define asm __asm__
#endif

#include "../firmware/motor.cpp"