#include "drv_i2c.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <stddef.h>

#define I2C_TIMEOUT_TICKS 5

volatile i2c_status_t i2c_status = I2C_IDLE;
volatile uint8_t i2c_timeout_counter = 0;

volatile uint8_t i2c_addr;
volatile const uint8_t *i2c_tx_data;
volatile uint8_t *i2c_rx_data;
volatile uint8_t i2c_len;
volatile uint8_t i2c_idx;
volatile bool i2c_is_read;

void i2c_init(void) {
    // ref: ds-021, ATmega328P datasheet rev. DS40002061B, tr.222-224
    TWSR = 0x00;
    TWBR = 12;
    
    uint8_t sreg = SREG;
    cli();
    if (TWCR & (1 << TWEN)) {
        TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWSTO);
    }
    i2c_status = I2C_IDLE;
    i2c_timeout_counter = 0;
    i2c_tx_data = NULL;
    i2c_rx_data = NULL;
    i2c_len = 0;
    i2c_idx = 0;
    
    TWCR = (1 << TWEN) | (1 << TWIE);
    SREG = sreg;
}

bool i2c_write_async(uint8_t addr, const uint8_t *data, uint8_t len) {
    uint8_t sreg = SREG;
    cli();
    if (i2c_status == I2C_BUSY) {
        SREG = sreg;
        return false;
    }
    i2c_status = I2C_BUSY;
    i2c_addr = addr << 1;
    i2c_tx_data = data;
    i2c_len = len;
    i2c_idx = 0;
    i2c_is_read = false;
    i2c_timeout_counter = 0;
    
    // ref: ds-021, ATmega328P datasheet rev. DS40002061B, tr.222-224
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN) | (1 << TWIE);
    SREG = sreg;
    return true;
}

bool i2c_read_async(uint8_t addr, uint8_t *data, uint8_t len) {
    uint8_t sreg = SREG;
    cli();
    if (i2c_status == I2C_BUSY) {
        SREG = sreg;
        return false;
    }
    i2c_status = I2C_BUSY;
    i2c_addr = (addr << 1) | 1;
    i2c_rx_data = data;
    i2c_len = len;
    i2c_idx = 0;
    i2c_is_read = true;
    i2c_timeout_counter = 0;
    
    // ref: ds-021, ATmega328P datasheet rev. DS40002061B, tr.222-224
    TWCR = (1 << TWINT) | (1 << TWSTA) | (1 << TWEN) | (1 << TWIE);
    SREG = sreg;
    return true;
}

i2c_status_t i2c_get_status(void) {
    i2c_status_t st;
    uint8_t sreg = SREG;
    cli();
    st = i2c_status;
    SREG = sreg;
    return st;
}

void i2c_tick(void) {
    uint8_t sreg = SREG;
    cli();
    if (i2c_status == I2C_BUSY) {
        i2c_timeout_counter++;
        if (i2c_timeout_counter > I2C_TIMEOUT_TICKS) {
            // ref: ds-021, ATmega328P datasheet rev. DS40002061B, tr.222-224
            TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWSTO) | (1 << TWIE);
            i2c_status = I2C_ERROR;
        }
    }
    SREG = sreg;
}

ISR(TWI_vect) {
    // ref: ds-022, ATmega328P datasheet rev. DS40002061B, tr.228-232
    uint8_t status = TWSR & 0xF8;
    
    switch (status) {
        case 0x08: // START transmitted
        case 0x10: // Repeated START transmitted
            TWDR = i2c_addr;
            TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE);
            break;
            
        case 0x18: // SLA+W transmitted, ACK received
        case 0x28: // Data transmitted, ACK received
            if (i2c_idx < i2c_len) {
                TWDR = i2c_tx_data[i2c_idx++];
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE);
            } else {
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE) | (1 << TWSTO);
                i2c_status = I2C_SUCCESS;
            }
            break;
            
        case 0x40: // SLA+R transmitted, ACK received
            if (i2c_len > 1) {
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE) | (1 << TWEA);
            } else {
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE);
            }
            break;
            
        case 0x50: // Data received, ACK returned
            i2c_rx_data[i2c_idx++] = TWDR;
            if (i2c_idx < i2c_len - 1) {
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE) | (1 << TWEA);
            } else {
                TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE);
            }
            break;
            
        case 0x58: // Data received, NACK returned
            i2c_rx_data[i2c_idx++] = TWDR;
            TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE) | (1 << TWSTO);
            i2c_status = I2C_SUCCESS;
            break;
            
        case 0x20: // SLA+W transmitted, NACK received
        case 0x30: // Data transmitted, NACK received
        case 0x48: // SLA+R transmitted, NACK received
        case 0x38: // Arbitration lost
        default:
            TWCR = (1 << TWINT) | (1 << TWEN) | (1 << TWIE) | (1 << TWSTO);
            i2c_status = I2C_ERROR;
            break;
    }
    i2c_timeout_counter = 0;
}
