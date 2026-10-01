#include "i2c.h"
#include "config.h"
#include <avr/io.h>

void i2c_init(void) {
    /* TWBR = 12 với F_CPU = 16 MHz và Prescaler = 1 tạo xung SCL 400 kHz */
    TWSR = 0x00;
    TWBR = 12;
    TWCR = (1 << TWEN);
}

static bool i2c_wait_twint(void) {
    uint16_t timeout = I2C_TIMEOUT_CYCLES;
    while (!(TWCR & (1 << TWINT))) {
        if (--timeout == 0) {
            return false; /* Hết thời gian chờ - tránh treo CPU */
        }
    }
    return true;
}

bool i2c_start(uint8_t address) {
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    if (!i2c_wait_twint()) {
        return false;
    }

    TWDR = address;
    TWCR = (1 << TWINT) | (1 << TWEN);
    return i2c_wait_twint();
}

void i2c_stop(void) {
    TWCR = (1 << TWINT) | (1 << TWSTO) | (1 << TWEN);
    uint16_t timeout = I2C_TIMEOUT_CYCLES;
    while (TWCR & (1 << TWSTO)) {
        if (--timeout == 0) {
            break; /* Hết thời gian chờ - tránh treo CPU */
        }
    }
}

bool i2c_write(uint8_t data) {
    TWDR = data;
    TWCR = (1 << TWINT) | (1 << TWEN);
    return i2c_wait_twint();
}

bool i2c_read_ack(uint8_t *data) {
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWEA);
    if (!i2c_wait_twint()) {
        return false;
    }
    *data = TWDR;
    return true;
}

bool i2c_read_nack(uint8_t *data) {
    TWCR = (1 << TWINT) | (1 << TWEN);
    if (!i2c_wait_twint()) {
        return false;
    }
    *data = TWDR;
    return true;
}

bool i2c_write_byte(uint8_t dev_addr, uint8_t reg_addr, uint8_t data) {
    if (!i2c_start((dev_addr << 1) | 0)) {
        i2c_stop();
        return false;
    }
    if (!i2c_write(reg_addr)) {
        i2c_stop();
        return false;
    }
    if (!i2c_write(data)) {
        i2c_stop();
        return false;
    }
    i2c_stop();
    return true;
}

bool i2c_read_bytes(uint8_t dev_addr, uint8_t reg_addr, uint8_t *buffer, uint8_t length) {
    if (!i2c_start((dev_addr << 1) | 0)) {
        i2c_stop();
        return false;
    }
    if (!i2c_write(reg_addr)) {
        i2c_stop();
        return false;
    }
    if (!i2c_start((dev_addr << 1) | 1)) {
        i2c_stop();
        return false;
    }
    for (uint8_t i = 0; i < length; i++) {
        if (i == (length - 1)) {
            if (!i2c_read_nack(&buffer[i])) {
                i2c_stop();
                return false;
            }
        } else {
            if (!i2c_read_ack(&buffer[i])) {
                i2c_stop();
                return false;
            }
        }
    }
    i2c_stop();
    return true;
}
