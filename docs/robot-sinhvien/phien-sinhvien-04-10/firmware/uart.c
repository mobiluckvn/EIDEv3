#include "config.h"

#define UART_BUF_SIZE 256
#define UART_BUF_MASK (UART_BUF_SIZE - 1)

static volatile char g_tx_buf[UART_BUF_SIZE];
static volatile uint8_t g_tx_head = 0;
static volatile uint8_t g_tx_tail = 0;
static volatile uint16_t g_dropped_lines = 0;
static uint32_t g_log_seq = 0;
static uint32_t g_stage_seq = 0;

void uart_init(void) {
    /* Bang 3.4: Dat cong noi tiep 9600 baud */
    UBRR0H = 0;
    UBRR0L = 103;
    UCSR0C = (1 << UCSZ01) | (1 << UCSZ00);
    UCSR0B = (1 << RXEN0) | (1 << TXEN0); /* Chua bat UDRIE0 vi dem rong */
    g_tx_head = 0;
    g_tx_tail = 0;
    g_dropped_lines = 0;
    g_log_seq = 0;
    g_stage_seq = 0;
}

#ifndef EIDE_SIM
ISR(USART_UDRE_vect) {
    if (g_tx_head != g_tx_tail) {
        UDR0 = g_tx_buf[g_tx_tail];
        g_tx_tail = (g_tx_tail + 1) & UART_BUF_MASK;
    } else {
        /* Dem rong: tat ngat truyen de tranh ngat lien tuc */
        UCSR0B &= ~(1 << UDRIE0);
    }
}
#endif

uint16_t uart_get_dropped_lines(void) {
    return g_dropped_lines;
}

static uint8_t uart_tx_free_space(void) {
    uint8_t head = g_tx_head;
    uint8_t tail = g_tx_tail;
    return (uint8_t)((tail - head - 1) & UART_BUF_MASK);
}

void uart_putc(char c) {
    /* Khong cho chan: them vao dem neu con cho */
    uint8_t next = (g_tx_head + 1) & UART_BUF_MASK;
    if (next != g_tx_tail) {
        g_tx_buf[g_tx_head] = c;
        g_tx_head = next;
#ifndef EIDE_SIM
        UCSR0B |= (1 << UDRIE0);
#endif
    }
}

void uart_puts(const char *s) {
    while (*s) {
        uart_putc(*s++);
    }
}

/* Gui ca dong: neu dem khong du cho thi bo ca dong va tang bien dem theo muc 3.10 */
void uart_send_line(const char *s) {
    uint8_t len = 0;
    while (s[len]) {
        len++;
    }

    if (len > uart_tx_free_space()) {
        /* Dem khong du cho chua ca dong: bo ca dong va tang bien dem */
        g_dropped_lines++;
        return;
    }

    for (uint8_t i = 0; i < len; i++) {
        g_tx_buf[g_tx_head] = s[i];
        g_tx_head = (g_tx_head + 1) & UART_BUF_MASK;
    }

#ifndef EIDE_SIM
    UCSR0B |= (1 << UDRIE0);
#endif
}

static void str_reverse(char *str, int len) {
    int i = 0, j = len - 1;
    while (i < j) {
        char t = str[i];
        str[i] = str[j];
        str[j] = t;
        i++;
        j--;
    }
}

static int int_to_str(int32_t n, char *out) {
    int i = 0;
    bool neg = false;
    if (n < 0) {
        neg = true;
        n = -n;
    }
    if (n == 0) {
        out[i++] = '0';
        out[i] = '\0';
        return i;
    }
    while (n > 0) {
        out[i++] = (char)('0' + (n % 10));
        n /= 10;
    }
    if (neg) {
        out[i++] = '-';
    }
    out[i] = '\0';
    str_reverse(out, i);
    return i;
}

void uart_put_int(int32_t n) {
    char buf[12];
    int_to_str(n, buf);
    uart_puts(buf);
}

/* Format dong theo doi 100 ms: muc 3.10 va chan doan
   So thu tu, millis(), Trang thai, goc nghieng, gia toc tho, xung trai, xung phai, so dong bi bo, so lan qua han */
void uart_send_telemetry(const char *state_name, float angle, int16_t az, int16_t pulse_l, int16_t pulse_r, uint16_t dropped_lines, uint16_t overrun_count) {
    char line[96];
    uint8_t idx = 0;
    char buf[16];

    /* Truong 1: So thu tu dong tang dan */
    g_log_seq++;
    int len = int_to_str((int32_t)g_log_seq, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 2: Thoi gian millis() cua robot */
    len = int_to_str((int32_t)millis(), buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 3: Copy state_name */
    while (*state_name && idx < 40) {
        line[idx++] = *state_name++;
    }
    line[idx++] = ' ';

    /* Truong 4: Goc nghieng dinh dang: int_part.frac */
    int32_t ang_scaled = (int32_t)(angle * 100.0f);
    if (ang_scaled < 0) {
        line[idx++] = '-';
        ang_scaled = -ang_scaled;
    }
    len = int_to_str(ang_scaled / 100, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = '.';
    int frac = ang_scaled % 100;
    line[idx++] = (char)('0' + (frac / 10));
    line[idx++] = (char)('0' + (frac % 10));
    line[idx++] = ' ';

    /* Truong 5: Gia toc tho az */
    len = int_to_str((int32_t)az, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 6: Gia tri xung banh trai pulse_l */
    len = int_to_str((int32_t)pulse_l, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 7: Gia tri xung banh phai pulse_r */
    len = int_to_str((int32_t)pulse_r, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 8: So dong bi bo drop */
    len = int_to_str((int32_t)dropped_lines, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 9: So lan qua han overrun */
    len = int_to_str((int32_t)overrun_count, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Truong 10: So lan ngat Timer2 (50 kHz) step_ticks */
    len = int_to_str((int32_t)timer_get_step_ticks(), buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    line[idx++] = '\r';
    line[idx++] = '\n';
    line[idx] = '\0';

    uart_send_line(line);
}

void uart_send_timing(uint16_t t_i2c, uint16_t t_filter, uint16_t t_ctrl, uint16_t t_total) {
    char line[96];
    uint8_t idx = 0;
    char buf[12];

    const char *tag = "#STAGE ";
    while (*tag) line[idx++] = *tag++;

    /* So thu tu tang dan cho dong stage */
    g_stage_seq++;
    int len = int_to_str((int32_t)g_stage_seq, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];
    line[idx++] = ' ';

    /* Thoi gian millis() cua robot */
    len = int_to_str((int32_t)millis(), buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    tag = ": i2c=";
    while (*tag) line[idx++] = *tag++;

    len = int_to_str((int32_t)t_i2c, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    tag = " filter=";
    while (*tag) line[idx++] = *tag++;
    len = int_to_str((int32_t)t_filter, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    tag = " ctrl=";
    while (*tag) line[idx++] = *tag++;
    len = int_to_str((int32_t)t_ctrl, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    tag = " total=";
    while (*tag) line[idx++] = *tag++;
    len = int_to_str((int32_t)t_total, buf);
    for (int i = 0; i < len; i++) line[idx++] = buf[i];

    tag = " us\r\n";
    while (*tag) line[idx++] = *tag++;
    line[idx] = '\0';

    uart_send_line(line);
}
