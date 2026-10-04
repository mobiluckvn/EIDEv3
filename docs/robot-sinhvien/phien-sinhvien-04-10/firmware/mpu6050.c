#include "config.h"

#define MPU_ADDR_WRITE 0xD0
#define MPU_ADDR_READ  0xD1

static int32_t g_gx_offset = 0;
static int32_t g_gy_offset = 0;

static bool mpu_write_reg(uint8_t reg, uint8_t val) {
    if (!i2c_start(MPU_ADDR_WRITE)) return false;
    if (!i2c_write(reg)) { i2c_stop(); return false; }
    if (!i2c_write(val)) { i2c_stop(); return false; }
    i2c_stop();
    return true;
}

static uint8_t mpu_read_reg(uint8_t reg) {
    uint8_t val = 0;
    if (!i2c_start(MPU_ADDR_WRITE)) return 0;
    i2c_write(reg);
    if (!i2c_start(MPU_ADDR_READ)) return 0;
    val = i2c_read_nack();
    i2c_stop();
    return val;
}

bool mpu6050_init(void) {
    /* Bang 3.4: Danh thuc cam bien */
    if (!mpu_write_reg(0x6B, 0x00)) return false;
    /* Bat bo loc trong cam bien */
    if (!mpu_write_reg(0x1A, 0x03)) return false;
    /* Thang do toc do goc nho nhat */
    if (!mpu_write_reg(0x1B, 0x00)) return false;
    /* Thang do gia toc */
    if (!mpu_write_reg(0x1C, 0x08)) return false;

    /* Kiem tra lai thanh ghi 0x1C theo doan 222 */
    if (mpu_read_reg(0x1C) != 0x08) return false;

    /* Kiem tra nhan dang WHO_AM_I theo doan 221 */
    uint8_t who = mpu_read_reg(0x75);
    if (who != 0x68 && who != 0x72) return false;

    return true;
}

void mpu6050_calibrate(void) {
    int32_t sum_gx = 0;
    int32_t sum_gy = 0;

    for (uint16_t i = 0; i < 500; i++) {
        int16_t az, gx, gy;
        mpu6050_read_raw(&az, &gx, &gy);
        sum_gx += gx;
        sum_gy += gy;
        delay_ms(3);
    }

    g_gx_offset = sum_gx / 500;
    g_gy_offset = sum_gy / 500;
}

bool mpu6050_read_raw(int16_t *az, int16_t *gx, int16_t *gy) {
    if (!i2c_start(MPU_ADDR_WRITE)) return false;
    if (!i2c_write(0x3B)) { i2c_stop(); return false; }
    if (!i2c_start(MPU_ADDR_READ)) return false;

    /* Doc 14 byte theo bang 3.2 */
    (void)i2c_read_ack(); /* byte 0: ax high */
    (void)i2c_read_ack(); /* byte 1: ax low */
    (void)i2c_read_ack(); /* byte 2: ay high */
    (void)i2c_read_ack(); /* byte 3: ay low */

    uint8_t az_h = i2c_read_ack(); /* byte 4 */
    uint8_t az_l = i2c_read_ack(); /* byte 5 */

    (void)i2c_read_ack(); /* byte 6: temp high */
    (void)i2c_read_ack(); /* byte 7: temp low */

    uint8_t gx_h = i2c_read_ack(); /* byte 8 */
    uint8_t gx_l = i2c_read_ack(); /* byte 9 */

    uint8_t gy_h = i2c_read_ack(); /* byte 10 */
    uint8_t gy_l = i2c_read_ack(); /* byte 11 */

    (void)i2c_read_ack();  /* byte 12: gz high */
    (void)i2c_read_nack(); /* byte 13: gz low */
    i2c_stop();

    if (az) *az = (int16_t)((az_h << 8) | az_l);
    if (gx) *gx = (int16_t)((gx_h << 8) | gx_l) - (int16_t)g_gx_offset;
    if (gy) *gy = (int16_t)((gy_h << 8) | gy_l) - (int16_t)g_gy_offset;

    return true;
}
