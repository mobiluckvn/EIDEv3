#ifndef DRV_BUTTON_H
#define DRV_BUTTON_H

#include <stdint.h>

typedef enum {
    BUTTON_EVENT_NONE = 0,
    BUTTON_EVENT_PRESSED,
    BUTTON_EVENT_RELEASED
} button_event_t;

void button_init(void);
button_event_t button_get_event(uint32_t current_time_ms);

#endif // DRV_BUTTON_H
