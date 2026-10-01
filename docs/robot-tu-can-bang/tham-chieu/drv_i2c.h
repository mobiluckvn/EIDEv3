#ifndef DRV_I2C_H
#define DRV_I2C_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    I2C_IDLE = 0,
    I2C_BUSY = 1,
    I2C_SUCCESS = 2,
    I2C_ERROR = 3
} i2c_status_t;

void i2c_init(void);
bool i2c_write_async(uint8_t addr, const uint8_t *data, uint8_t len);
bool i2c_read_async(uint8_t addr, uint8_t *data, uint8_t len);
i2c_status_t i2c_get_status(void);
void i2c_tick(void);

#endif // DRV_I2C_H
