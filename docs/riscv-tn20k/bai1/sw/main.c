#include <stdint.h>

#define UART_TX_REG     (*(volatile uint32_t *)0x10000000)
#define UART_STATUS_REG (*(volatile uint32_t *)0x10000004)
#define LED_REG         (*(volatile uint32_t *)0x20000000)

#define SIM 1
#ifdef SIM
#define CYCLES_PER_SEC 1000U
#else
#define CYCLES_PER_SEC 27000000U
#endif

static inline uint32_t get_cycle(void) {
    uint32_t c;
    __asm__ volatile ("rdcycle %0" : "=r"(c));
    return c;
}

static void uart_putc(char c) {
    while (UART_STATUS_REG & 1) {
        /* Chờ bit bận ở UART_STATUS hạ xuống */
    }
    UART_TX_REG = (uint32_t)(uint8_t)c;
}

static void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

static uint32_t divmod10(uint32_t n, uint32_t *r) {
    uint32_t q = 0;
    uint32_t rem = 0;
    for (int i = 31; i >= 0; i--) {
        rem = (rem << 1) | ((n >> i) & 1);
        if (rem >= 10) {
            rem -= 10;
            q |= (1U << i);
        }
    }
    if (r) *r = rem;
    return q;
}

static void uart_put_num(uint32_t val) {
    char buf[11];
    int idx = 0;
    if (val == 0) {
        uart_putc('0');
        return;
    }
    while (val > 0) {
        uint32_t rem = 0;
        val = divmod10(val, &rem);
        buf[idx++] = (char)('0' + rem);
    }
    while (idx > 0) {
        uart_putc(buf[--idx]);
    }
}

int main(void) {
    uint32_t led_state = 0;
    LED_REG = led_state;

    while (1) {
        uint32_t cycle = get_cycle();
        uart_puts("Hello from PicoRV32 on Tang Nano 20K, cycle=");
        uart_put_num(cycle);
        uart_puts("\r\n");

        /* Đảo 1 LED */
        led_state ^= 1;
        LED_REG = led_state;

        /* Chờ 1 giây theo chu kỳ clock */
        uint32_t start = get_cycle();
        while ((get_cycle() - start) < CYCLES_PER_SEC) {
            /* chờ */
        }
    }

    return 0;
}
