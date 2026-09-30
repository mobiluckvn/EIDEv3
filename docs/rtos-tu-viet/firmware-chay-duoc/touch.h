#ifndef TOUCH_H
#define TOUCH_H

#include <stdint.h>

/**
 * @brief Khoi tao controller cam ung FT6206 / FT6336G qua I2C1 (PB8=SCL, PB9=SDA).
 * @return 0 neu thanh cong, -1 neu khong tim thay IC cam ung.
 */
int Touch_Init(void);

/**
 * @brief Doc toa do diem cham hien tai tren man hinh.
 * @param x Con tro nhan toa do X (0..799)
 * @param y Con tro nhan toa do Y (0..479)
 * @return 1 neu co cham (touch detected), 0 neu khong co cham.
 */
int Touch_Read(uint16_t *x, uint16_t *y);

#endif /* TOUCH_H */
