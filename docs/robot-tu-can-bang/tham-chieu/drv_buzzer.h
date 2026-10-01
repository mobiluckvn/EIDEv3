#ifndef DRV_BUZZER_H
#define DRV_BUZZER_H

#include <stdint.h>
#include <stdbool.h>

void buzzer_init(void);
void buzzer_beep_async(uint32_t current_time_ms, uint32_t duration_ms);
void buzzer_update(uint32_t current_time_ms);
void buzzer_stop(void);

#endif // DRV_BUZZER_H
