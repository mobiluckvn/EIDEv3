/* Ca #3: bảng tổng kiểm SINH RA nhưng main.c không #include/không gọi */
unsigned long tong_kiem_chuan(const unsigned char *p, unsigned n) {
    unsigned long t = 0; while (n--) t += *p++; return t;
}
/* Ca #7: RTOS_IDLE_PRIORITY có, nhưng KHÔNG AI tạo tác vụ rỗi */
#define RTOS_IDLE_PRIORITY 7
static void vTaskIdle(void *a) { (void)a; for(;;){} }
/* Ca #5: handler sai tên một chữ */
void SysTick_handler(void) { }
void PendSV_Handler(void) { }
/* Hàm chưa viết xong: chỉ trả hằng */
int doc_pin_mv(void) { return 3300; }
int main(void) { return 0; }
