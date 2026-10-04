#include "config.h"
#include <util/twi.h>

void i2c_init(void) {
    /* 9 xung giai phong bus theo muc 3.5 */
    PORTC &= ~((1 << PC4) | (1 << PC5));
    DDRC &= ~(1 << PC4);

    for (uint8_t i = 0; i < 9; i++) {
        DDRC |= (1 << PC5);
        for (volatile uint8_t w = 0; w < 10; w++);
        DDRC &= ~(1 << PC5);
        for (volatile uint8_t w = 0; w < 10; w++);
    }

    /* Dieu kien dung bang tay */
    DDRC |= (1 << PC4);
    for (volatile uint8_t w = 0; w < 10; w++);
    DDRC &= ~(1 << PC4);

    /* Dat phan cung I2C: TWBR = 12, TWSR = 0 theo bang 3.4 */
    TWSR = 0x00;
    TWBR = 12;
    TWCR = (1 << TWEN);
}

bool i2c_start(uint8_t addr) {
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));

    uint8_t status = TW_STATUS;
    if ((status != TW_START) && (status != TW_REP_START)) {
        return false;
    }

    TWDR = addr;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));

    status = TW_STATUS;
    if ((status != TW_MT_SLA_ACK) && (status != TW_MR_SLA_ACK)) {
        return false;
    }

    return true;
}

bool i2c_write(uint8_t data) {
    TWDR = data;
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));

    if (TW_STATUS != TW_MT_DATA_ACK) {
        return false;
    }
    return true;
}

uint8_t i2c_read_ack(void) {
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWEA);
    while (!(TWCR & (1 << TWINT)));
    return TWDR;
}

uint8_t i2c_read_nack(void) {
    TWCR = (1 << TWINT) | (1 << TWEN);
    while (!(TWCR & (1 << TWINT)));
    return TWDR;
}

void i2c_stop(void) {
    TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWSTO);
}
