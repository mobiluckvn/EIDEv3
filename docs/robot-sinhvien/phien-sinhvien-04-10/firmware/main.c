#include "config.h"
#include <avr/wdt.h>

int main(void) {
    /* Buoc 1: Doc roi luu thanh ghi nguyen nhan khoi dong lai, sau do xoa ve 0 */
    uint8_t mcusr_mirror = MCUSR;
    MCUSR = 0;

    /* Buoc 2: Tat bo dem canh treo */
    wdt_disable();

    /* Buoc 3: Dat bon chan dong co la chan ra, ha hai chan xung ve thap */
    motor_init();

    /* Buoc 4: Dat chan coi la chan ra, chan nut la chan vao co keo len */
    BUZZER_DDR |= (1 << PIN_BUZZER);
    BUZZER_PORT &= ~(1 << PIN_BUZZER);

    BUTTON_DDR &= ~(1 << PIN_BUTTON);
    BUTTON_PORT |= (1 << PIN_BUTTON); /* Bat dien tro keo len */

    /* Chan chan do kiem phu luc B va D: D13, A1 va A2 */
    TEST_D13_DDR |= (1 << PIN_TEST_D13);
    TEST_A1_DDR |= (1 << PIN_TEST_A1);
    TEST_A2_DDR |= (1 << PIN_TEST_A2);
    TEST_A2_PORT &= ~(1 << PIN_TEST_A2);

    /* Buoc 5: Dat cong noi tiep o 9600 baud */
    uart_init();

    /* Buoc 6: In ra nguyen nhan khoi dong lai da luu o buoc 1 */
    uart_puts("MCUSR: 0x");
    uart_put_int(mcusr_mirror);
    uart_puts("\r\n");

    /* Buoc 7: Doc chan nut. Neu dang bi giu thi bat co vao che do tu kiem */
    bool self_test = false;
    if (!(BUTTON_PIN & (1 << PIN_BUTTON))) {
        self_test = true;
    }

    /* Buoc 8: Dat hai bo dem Timer0 va Timer2 */
    timer_init();

    /* Buoc 9: Mo ngat chung */
    sei();

    /* Buoc 10: Dat duong I2C roi danh thuc cam bien */
    i2c_init();
    bool mpu_ok = mpu6050_init();

    fsm_init(self_test);

    if (!mpu_ok) {
        /* Loi cam bien: bat coi canh bao */
        BUZZER_PORT |= (1 << PIN_BUZZER);
        uart_puts("MPU6050 ERROR\r\n");
    }

    /* Vao vong lap chinh */
    while (1) {
        fsm_update();
    }

    return 0;
}
