#ifndef I2C_H_
#define I2C_H_

#include <stdint.h>
#include <stdbool.h>

/* Khởi tạo module TWI phần cứng ở 400 kHz */
void i2c_init(void);

/* Phát điều kiện START và gửi địa chỉ thiết bị + hướng R/W */
bool i2c_start(uint8_t address);

/* Phát điều kiện STOP */
void i2c_stop(void);

/* Gửi một byte dữ liệu */
bool i2c_write(uint8_t data);

/* Đọc một byte dữ liệu và trả ACK */
bool i2c_read_ack(uint8_t *data);

/* Đọc một byte dữ liệu và trả NACK */
bool i2c_read_nack(uint8_t *data);

/* Đọc một khối dữ liệu từ thanh ghi thiết bị */
bool i2c_read_bytes(uint8_t dev_addr, uint8_t reg_addr, uint8_t *buffer, uint8_t length);

/* Ghi một byte vào thanh ghi thiết bị */
bool i2c_write_byte(uint8_t dev_addr, uint8_t reg_addr, uint8_t data);

#endif /* I2C_H_ */
