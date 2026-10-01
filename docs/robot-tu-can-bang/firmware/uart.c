#include "uart.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <util/atomic.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* Kích thước bộ đệm vòng phát 128 byte (§9.3, f-nguoi-20439020) */
#define TX_BUF_SIZE 128

static volatile uint8_t s_tx_buf[TX_BUF_SIZE];
static volatile uint8_t s_tx_head = 0;
static volatile uint8_t s_tx_tail = 0;
static volatile uint16_t s_dropped_lines = 0;

void uart_init(void) {
    /* Đặt tốc độ truyền 9.600 baud ở F_CPU = 16 MHz (§9.1 Bảng 61 dòng 1: UBRR0 = 103) */
    UBRR0H = 0;
    UBRR0L = 103;

    /* Cấu hình khung truyền: 8 bit dữ liệu, 1 stop bit, không kiểm tra chẵn lẻ (§9.4 Bảng 63) */
    UCSR0A = 0x00;
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);

    /* Bật bộ phát và bộ nhận (§9.4) */
    UCSR0B = (1 << RXEN0) | (1 << TXEN0);

    /* Bật điện trở kéo lên nội bộ trên chân RXD (PD0) để chống nhiễu (§9.2, COM-03) */
    DDRD &= ~(1 << PD0);
    PORTD |= (1 << PD0);

    s_tx_head = 0;
    s_tx_tail = 0;
    s_dropped_lines = 0;
}

ISR(USART_UDRE_vect) {
    /* Khi thanh ghi UDR0 sẵn sàng nhận byte mới */
    if (s_tx_head != s_tx_tail) {
        UDR0 = s_tx_buf[s_tx_tail];
        s_tx_tail = (s_tx_tail + 1) & (TX_BUF_SIZE - 1);
    } else {
        /* Bộ đệm đã trống: tắt ngắt UDRE để tránh lặp ngắt (§9.3) */
        UCSR0B &= ~(1 << UDRIE0);
    }
}

bool uart_send_line(const char *str) {
    if (str == NULL) {
        return false;
    }

    uint8_t len = (uint8_t)strlen(str);
    /* Cần thêm 2 byte cho "\r\n" */
    uint8_t total_len = len + 2;

    uint8_t head = s_tx_head;
    uint8_t tail = s_tx_tail;
    uint8_t free_space = (tail - head - 1) & (TX_BUF_SIZE - 1);

    /* Nếu bộ đệm đầy không chứa đủ cả dòng: BỎ DÒNG và tăng biến đếm (§9.3) */
    if (total_len > free_space) {
        s_dropped_lines++;
        return false;
    }

    /* Đưa chuỗi vào bộ đệm vòng phi chặn */
    for (uint8_t i = 0; i < len; i++) {
        s_tx_buf[head] = (uint8_t)str[i];
        head = (head + 1) & (TX_BUF_SIZE - 1);
    }
    s_tx_buf[head] = '\r';
    head = (head + 1) & (TX_BUF_SIZE - 1);
    s_tx_buf[head] = '\n';
    head = (head + 1) & (TX_BUF_SIZE - 1);

    /* Cập nhật head nguyên tử và bật ngắt truyền */
    ATOMIC_BLOCK(ATOMIC_RESTORESTATE) {
        s_tx_head = head;
        UCSR0B |= (1 << UDRIE0);
    }

    return true;
}

void uart_print_reset_reason(uint8_t mcusr_val) {
    char buf[64];
    char *p = buf;

    /* Sao chép tiền tố */
    strcpy(p, "[RESET] MCUSR: ");
    p += strlen(p);

    /* Giải mã các bit nguyên nhân reset theo Bảng 40 (§13.2) */
    bool has_reason = false;
    if (mcusr_val & (1 << PORF)) {
        strcpy(p, "POR(CapNguon) ");
        p += strlen(p);
        has_reason = true;
    }
    if (mcusr_val & (1 << EXTRF)) {
        strcpy(p, "EXT(NutReset/Nap) ");
        p += strlen(p);
        has_reason = true;
    }
    if (mcusr_val & (1 << BORF)) {
        strcpy(p, "BOR(SutAp) ");
        p += strlen(p);
        has_reason = true;
    }
    if (mcusr_val & (1 << WDRF)) {
        strcpy(p, "WDR(Watchdog) ");
        p += strlen(p);
        has_reason = true;
    }

    if (!has_reason) {
        strcpy(p, "UNKNOWN");
    }

    uart_send_line(buf);
}

uint16_t uart_get_dropped_lines(void) {
    return s_dropped_lines;
}

void uart_send_diag_telemetry(robot_state_t state, float pitch, int16_t thr_l, int16_t thr_r, uint16_t miss, uint16_t dropped) {
    const char *st_str = "UNK";
    switch (state) {
        case STATE_INIT:        st_str = "INIT"; break;
        case STATE_CALIBRATING: st_str = "CALI"; break;
        case STATE_READY:       st_str = "REDY"; break;
        case STATE_BALANCING:   st_str = "BALA"; break;
        case STATE_FALLEN:      st_str = "FALL"; break;
        case STATE_STOPPED:     st_str = "STOP"; break;
        case STATE_DIAG_ANGLE:  st_str = "DG_A"; break;
        case STATE_DIAG_MOTOR:  st_str = "DG_M"; break;
    }

    int16_t p_x10 = (int16_t)(pitch * 10.0f);
    char buf[60];
    snprintf(buf, sizeof(buf), "[%s] P:%d.%d Thr:%d/%d M:%u D:%u",
             st_str,
             p_x10 / 10, abs(p_x10 % 10),
             thr_l, thr_r,
             miss, dropped);
    uart_send_line(buf);
}
