/* main.c
 * Chương trình bare-metal Bài 1 chạy trên lõi PicoRV32 (Tang Nano 20K)
 * In chuỗi "Hello from PicoRV32 on Tang Nano 20K, cycle=<số>\r\n"
 * mỗi khoảng 1 giây (đo bằng rdcycle, 27 000 000 chu kỳ) và đảo LED.
 */

#include <stdint.h>

// Địa chỉ MMIO ngoại vi (anh cho, chưa có tài liệu)
#define REG_UART_DATA   (*(volatile uint32_t *)0x10000000)
#define REG_UART_STATUS (*(volatile uint32_t *)0x10000004)
#define REG_LED         (*(volatile uint32_t *)0x20000000)

#ifdef SIM
#define CYCLE_DELAY 1000ULL
#else
#define CYCLE_DELAY 27000000ULL // 1 giây tại 27 MHz (anh cho, chưa có tài liệu)
#endif

// Đọc bộ đếm chu kỳ 64-bit qua lệnh CSR rdcycle / rdcycleh
static inline uint64_t read_cycle(void) {
    uint32_t high0, low, high1;
    do {
        __asm__ volatile ("rdcycleh %0" : "=r"(high0));
        __asm__ volatile ("rdcycle  %0" : "=r"(low));
        __asm__ volatile ("rdcycleh %0" : "=r"(high1));
    } while (high0 != high1);
    return (((uint64_t)high0) << 32) | low;
}

// Gửi một ký tự qua UART TX (chờ busy = 0)
void uart_putc(char c) {
    while (REG_UART_STATUS & 1) {
        // Chờ UART sẵn sàng
    }
    REG_UART_DATA = (uint32_t)(uint8_t)c;
}

// Gửi một chuỗi qua UART TX
void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

// In số nguyên không dấu dạng chuỗi (chia nhị phân không phụ thuộc libgcc)
void print_u64(uint64_t val) {
    char buf[24];
    int idx = 0;
    if (val == 0) {
        uart_putc('0');
        return;
    }
    while (val > 0) {
        uint64_t q = 0;
        uint64_t r = 0;
        for (int i = 63; i >= 0; i--) {
            r = (r << 1) | ((val >> i) & 1);
            if (r >= 10) {
                r -= 10;
                q |= (1ULL << i);
            }
        }
        buf[idx++] = '0' + (char)r;
        val = q;
    }
    while (idx > 0) {
        uart_putc(buf[--idx]);
    }
}

int main(void) {
    uint8_t led_state = 0x01;
    REG_LED = led_state;

    uint64_t last_cycle = read_cycle();

    while (1) {
        uint64_t current_cycle = read_cycle();
        if (current_cycle - last_cycle >= CYCLE_DELAY) {
            last_cycle = current_cycle;

            // In chuỗi định dạng
            uart_puts("Hello from PicoRV32 on Tang Nano 20K, cycle=");
            print_u64(current_cycle);
            uart_puts("\r\n");

            // Đảo LED
            led_state ^= 0x01;
            REG_LED = led_state;
        }
    }

    return 0;
}
