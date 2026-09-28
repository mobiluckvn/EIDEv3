/**
 * @file touch.c
 * @brief Driver cảm ứng điện dung FT6206 / FT6336G qua I2C1 (PB8=SCL, PB9=SDA)
 */
#include "touch.h"
#include "stm32f469xx.h"

#define TS_ADDR_1 0x70  /* 7-bit 0x38 << 1 (FT6336G / FT6206 chuẩn) */
#define TS_ADDR_2 0x54  /* 7-bit 0x2A << 1 (Một số biến thể FT6206) */

static uint8_t g_ts_addr = TS_ADDR_1;

static inline void i2c_delay(void)
{
    for (volatile int i = 0; i < 150; i++) {
        __asm__ volatile("nop");
    }
}

static inline void scl_high(void)
{
    GPIOB->BSRR = (1UL << 8);
}

static inline void scl_low(void)
{
    GPIOB->BSRR = (1UL << (8 + 16));
}

static inline void sda_high(void)
{
    GPIOB->BSRR = (1UL << 9);
}

static inline void sda_low(void)
{
    GPIOB->BSRR = (1UL << (9 + 16));
}

static inline uint8_t sda_read(void)
{
    return (GPIOB->IDR & (1UL << 9)) ? 1 : 0;
}

static void i2c_start(void)
{
    sda_high();
    scl_high();
    i2c_delay();
    sda_low();
    i2c_delay();
    scl_low();
    i2c_delay();
}

static void i2c_stop(void)
{
    sda_low();
    i2c_delay();
    scl_high();
    i2c_delay();
    sda_high();
    i2c_delay();
}

static uint8_t i2c_write_byte(uint8_t byte)
{
    for (int i = 0; i < 8; i++) {
        if (byte & 0x80) {
            sda_high();
        } else {
            sda_low();
        }
        byte <<= 1;
        i2c_delay();
        scl_high();
        i2c_delay();
        scl_low();
    }
    
    /* Đọc ACK */
    sda_high();
    i2c_delay();
    scl_high();
    i2c_delay();
    uint8_t ack = sda_read();
    scl_low();
    i2c_delay();
    
    return ack; /* 0 = ACK, 1 = NACK */
}

static uint8_t i2c_read_byte(uint8_t send_ack)
{
    uint8_t byte = 0;
    sda_high();
    for (int i = 0; i < 8; i++) {
        byte <<= 1;
        scl_high();
        i2c_delay();
        if (sda_read()) {
            byte |= 0x01;
        }
        scl_low();
        i2c_delay();
    }
    
    /* Gửi ACK hoặc NACK */
    if (send_ack) {
        sda_low();
    } else {
        sda_high();
    }
    i2c_delay();
    scl_high();
    i2c_delay();
    scl_low();
    sda_high();
    i2c_delay();
    
    return byte;
}

static int i2c_read_regs(uint8_t dev_addr, uint8_t reg, uint8_t *buf, uint16_t len)
{
    i2c_start();
    if (i2c_write_byte(dev_addr & 0xFE) != 0) {
        i2c_stop();
        return -1;
    }
    if (i2c_write_byte(reg) != 0) {
        i2c_stop();
        return -1;
    }
    
    i2c_start();
    if (i2c_write_byte(dev_addr | 0x01) != 0) {
        i2c_stop();
        return -1;
    }
    
    for (uint16_t i = 0; i < len; i++) {
        buf[i] = i2c_read_byte(i < (len - 1));
    }
    i2c_stop();
    return 0;
}

int Touch_Init(void)
{
    /* Bật clock GPIOB */
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOBEN;
    
    /* Cấu hình PB8 (SCL) và PB9 (SDA): Output Open-Drain, Pull-up, High Speed */
    /* PB8: MODER bits 17:16 = 01 */
    /* PB9: MODER bits 19:18 = 01 */
    GPIOB->MODER &= ~((3UL << (8 * 2)) | (3UL << (9 * 2)));
    GPIOB->MODER |=  ((1UL << (8 * 2)) | (1UL << (9 * 2)));
    
    /* Open-drain: OTYPER bit 8 = 1, bit 9 = 1 */
    GPIOB->OTYPER |= (1UL << 8) | (1UL << 9);
    
    /* Pull-up: PUPDR bits 17:16 = 01, bits 19:18 = 01 */
    GPIOB->PUPDR &= ~((3UL << (8 * 2)) | (3UL << (9 * 2)));
    GPIOB->PUPDR |=  ((1UL << (8 * 2)) | (1UL << (9 * 2)));
    
    /* Very High speed: OSPEEDR bits 17:16 = 11, bits 19:18 = 11 */
    GPIOB->OSPEEDR |= ((3UL << (8 * 2)) | (3UL << (9 * 2)));
    
    /* 9 xung unlock bus I2C */
    sda_high();
    for (int i = 0; i < 9; i++) {
        scl_low();
        i2c_delay();
        scl_high();
        i2c_delay();
    }
    i2c_stop();
    
    /* Quét địa chỉ IC cảm ứng */
    i2c_start();
    if (i2c_write_byte(TS_ADDR_1) == 0) {
        g_ts_addr = TS_ADDR_1;
        i2c_stop();
        return 0;
    }
    i2c_stop();
    
    i2c_start();
    if (i2c_write_byte(TS_ADDR_2) == 0) {
        g_ts_addr = TS_ADDR_2;
        i2c_stop();
        return 0;
    }
    i2c_stop();
    
    /* Mặc định dùng TS_ADDR_1 */
    g_ts_addr = TS_ADDR_1;
    return 0;
}

int Touch_Read(uint16_t *x, uint16_t *y)
{
    uint8_t data[5];
    /* Đọc 5 byte từ thanh ghi 0x02 (TD_STATUS) đến 0x06 */
    if (i2c_read_regs(g_ts_addr, 0x02, data, 5) != 0) {
        return 0;
    }
    
    uint8_t touches = data[0] & 0x0F;
    if (touches == 0 || touches > 2) {
        return 0;
    }
    
    uint16_t raw_x = ((uint16_t)(data[1] & 0x0F) << 8) | data[2];
    uint16_t raw_y = ((uint16_t)(data[3] & 0x0F) << 8) | data[4];
    
    /* Trên màn hình STM32F469I-DISCO OTM8009A ở chế độ Landscape (800x480):
     * raw_y là trục dài (0..799)
     * raw_x là trục ngắn (0..479)
     */
    if (x != 0) {
        *x = raw_y;
    }
    if (y != 0) {
        *y = raw_x;
    }
    return 1;
}
