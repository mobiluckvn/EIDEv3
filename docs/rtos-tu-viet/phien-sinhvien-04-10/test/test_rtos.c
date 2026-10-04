#include <stdio.h>
#include <stdbool.h>
#define RTOS_WEAK __attribute__((weak))
#include "../firmware/control_rtos.c"

static tcb_t *trace[16];
static uint32_t trace_idx = 0;

static void dummy_task(void *arg) {
    (void)arg;
}

static void record_trace(tcb_t *task) {
    if (trace_idx < 16) {
        trace[trace_idx++] = task;
    }
}

int main(void) {
    rtos_init();

    /* ========================================================
     * Ca 1: Chuyển ngữ cảnh giữa Task A và Task B khi Task A trễ
     * ======================================================== */
    uint32_t stack_a[64];
    uint32_t stack_b[64];
    tcb_t tcb_a;
    tcb_t tcb_b;

    trace_idx = 0;

    /* Task A có ưu tiên cao hơn Task B */
    uint8_t prio_a = 15;
    uint8_t prio_b = 8;
    uint32_t delay_ticks = 5;

    bool c1 = rtos_task_create(&tcb_a, "TaskA", dummy_task, 0, prio_a, stack_a, 64);
    bool c2 = rtos_task_create(&tcb_b, "TaskB", dummy_task, 0, prio_b, stack_b, 64);

    /* 1. Ban đầu bộ lập lịch phải chọn Task A */
    tcb_t *curr = rtos_pick_next_task();
    bool ca1_step1 = (c1 && c2 && curr == &tcb_a);
    if (curr) record_trace(curr);

    mock_scb_icsr = 0;
    /* 2. Task A gọi trễ 5 nhịp -> Task A bị BLOCKED */
    rtos_delay_ms(delay_ticks);
    bool ca1_yield_pendsv = ((mock_scb_icsr & SCB_ICSR_PENDSVSET_BIT) != 0);

    /* Bộ lập lịch BẮT BUỘC phải chuyển sang Task B */
    curr = rtos_pick_next_task();
    bool ca1_step2 = (curr == &tcb_b);
    if (curr) record_trace(curr);

    /* 3. Cho nhịp tick chạy 5 lần để hết trễ */
    mock_scb_icsr = 0;
    for (uint32_t i = 0; i < delay_ticks; i++) {
        rtos_tick();
    }
    bool ca1_tick_pendsv = ((mock_scb_icsr & SCB_ICSR_PENDSVSET_BIT) != 0);

    /* 4. Task A hết trễ, sẵn sàng trở lại -> bộ lập lịch tiền định chọn lại Task A */
    curr = rtos_pick_next_task();
    bool ca1_step3 = (curr == &tcb_a);
    if (curr) record_trace(curr);

    /* Mốc so sánh ĐỘC LẬP: vết thực thi đúng thứ tự [&tcb_a, &tcb_b, &tcb_a] VÀ có xin chuyển ngữ cảnh qua PendSV */
    bool ca1_ok = ca1_step1 && ca1_step2 && ca1_step3 && ca1_yield_pendsv && ca1_tick_pendsv && (trace_idx == 3) &&
                  (trace[0] == &tcb_a) && (trace[1] == &tcb_b) && (trace[2] == &tcb_a);

    /* ========================================================
     * Ca 2: Hàng đợi tĩnh - Task B gửi tin đánh thức Task A
     * ======================================================== */
    rtos_init();
    rtos_task_create(&tcb_a, "TaskA", dummy_task, 0, prio_a, stack_a, 64);
    rtos_task_create(&tcb_b, "TaskB", dummy_task, 0, prio_b, stack_b, 64);

    rtos_queue_t queue;
    uint32_t q_buffer[4];
    rtos_queue_init(&queue, q_buffer, sizeof(uint32_t), 4);

    /* Task A đọc từ hàng đợi rỗng với timeout -> Task A bị BLOCKED */
    uint32_t received_val = 0;
    bool recv_ret = rtos_queue_receive(&queue, &received_val, 10);
    bool ca2_step1 = (!recv_ret && tcb_a.state == TASK_BLOCKED);

    /* Bộ lập lịch chuyển sang Task B */
    curr = rtos_pick_next_task();
    bool ca2_step2 = (curr == &tcb_b);

    /* Task B gửi dữ liệu vào hàng đợi */
    uint32_t send_val = 99;
    bool send_ret = rtos_queue_send(&queue, &send_val, 0);

    /* Task A phải được đánh thức về READY ngay lập tức và được chọn chạy lại */
    curr = rtos_pick_next_task();
    bool ca2_step3 = (send_ret && curr == &tcb_a && tcb_a.state == TASK_READY);

    bool ca2_ok = ca2_step1 && ca2_step2 && ca2_step3;

    /* ========================================================
     * Ca 3: Hàng đợi hết thời hạn (Timeout) trả về false
     * ======================================================== */
    rtos_init();
    rtos_task_create(&tcb_a, "TaskA", dummy_task, 0, prio_a, stack_a, 64);
    rtos_queue_init(&queue, q_buffer, sizeof(uint32_t), 4);

    /* Task A chờ nhận tin với timeout 3 nhịp */
    rtos_queue_receive(&queue, &received_val, 3);
    bool ca3_step1 = (tcb_a.state == TASK_BLOCKED);

    /* Cho 3 nhịp tick trôi qua mà không ai gửi tin */
    rtos_tick();
    rtos_tick();
    rtos_tick();

    /* Task A phải hết timeout, quay lại READY và có timed_out = true */
    bool ca3_ok = ca3_step1 && (tcb_a.state == TASK_READY) && (tcb_a.timed_out == true);

    /* ========================================================
     * Ca 4: Tiền định theo 32 mức ưu tiên dùng CLZ
     * ======================================================== */
    rtos_init();
    tcb_t tcb_low, tcb_mid, tcb_high;
    uint32_t s_low[64], s_mid[64], s_high[64];

    rtos_task_create(&tcb_low, "Low", dummy_task, 0, 1, s_low, 64);
    rtos_task_create(&tcb_mid, "Mid", dummy_task, 0, 14, s_mid, 64);
    rtos_task_create(&tcb_high, "High", dummy_task, 0, 31, s_high, 64);

    /* Bộ lập lịch phải chọn High (31) */
    curr = rtos_pick_next_task();
    bool ca4_step1 = (curr == &tcb_high);

    /* Chặn High -> phải chuyển sang Mid (14) */
    rtos_delay_ms(10);
    curr = rtos_pick_next_task();
    bool ca4_step2 = (curr == &tcb_mid);

    /* Chặn Mid -> phải chuyển sang Low (1) */
    rtos_delay_ms(10);
    curr = rtos_pick_next_task();
    bool ca4_step3 = (curr == &tcb_low);

    bool ca4_ok = ca4_step1 && ca4_step2 && ca4_step3;

    /* ========================================================
     * Ca 5: Sơn ngăn xếp 0xA5A5A5A5 và đo mức nước (Watermark)
     * ======================================================== */
    rtos_init();
    tcb_t tcb_test1, tcb_test2;
    uint32_t s_test1[64], s_test2[128];

    rtos_task_create(&tcb_test1, "TestTask1", dummy_task, 0, 10, s_test1, 64);
    rtos_task_create(&tcb_test2, "TestTask2", dummy_task, 0, 20, s_test2, 128);

    uint32_t wm1_init = rtos_task_get_stack_watermark(&tcb_test1);
    uint32_t used1_init = rtos_task_get_stack_used_words(&tcb_test1);
    uint32_t wm2_init = rtos_task_get_stack_watermark(&tcb_test2);
    uint32_t used2_init = rtos_task_get_stack_used_words(&tcb_test2);

    /* Kiểm tra tính toàn vẹn: tổng mức nước chưa dùng + đã dùng = kích thước stack */
    bool ca5_step1 = (wm1_init > 0) && (wm1_init + used1_init == 64);
    bool ca5_step2 = (wm2_init > 0) && (wm2_init + used2_init == 128);

    /* Mô phỏng tác vụ dùng thêm ngăn xếp bằng cách ghi đè 1 word gần đáy nhất đã dùng */
    if (wm1_init > 0) {
        s_test1[wm1_init - 1] = 0;
    }
    uint32_t wm1_after = rtos_task_get_stack_watermark(&tcb_test1);
    bool ca5_step3 = (wm1_after == wm1_init - 1);

    bool ca5_ok = ca5_step1 && ca5_step2 && ca5_step3;

    /* ========================================================
     * Ca 6: Kiem tra 16 o vector trong anh nhi phan (.bin)
     * ======================================================== */
    bool ca6_ok = false;
    char ca6_msg[128] = "Khong mo duoc anh mach.bin";
    FILE *fbin = fopen(".eide/build/mach.bin", "rb");
    if (!fbin) {
        fbin = fopen("../.eide/build/mach.bin", "rb");
    }
    if (fbin) {
        uint32_t vec[16] = {0};
        size_t n = fread(vec, sizeof(uint32_t), 16, fbin);
        if (n == 16) {
            uint32_t default_handler = vec[2];
            bool reset_valid = ((vec[1] & 1) == 1) && (vec[1] != default_handler);
            bool reserved_zero = (vec[7] == 0 && vec[8] == 0 && vec[9] == 0 && vec[10] == 0 && vec[13] == 0);
            bool pendsv_valid = ((vec[14] & 1) == 1) && (vec[14] != default_handler);
            bool systick_valid = ((vec[15] & 1) == 1) && (vec[15] != default_handler);

            if (reset_valid && reserved_zero && pendsv_valid && systick_valid) {
                ca6_ok = true;
                snprintf(ca6_msg, sizeof(ca6_msg), "SysTick va PendSV hop le, khac Default_Handler");
            } else {
                snprintf(ca6_msg, sizeof(ca6_msg), "Loi vector: SysTick hoac PendSV tro Default_Handler");
            }
        }
        fclose(fbin);
    }

    /* ========================================================
     * Ca 7: Kiem tra SCB_ICSR (0xE000ED04) & PENDSVSET trong mach.bin
     * ======================================================== */
    bool ca7_ok = false;
    char ca7_msg[128] = "Khong tim thay SCB_ICSR trong mach.bin";
    fbin = fopen(".eide/build/mach.bin", "rb");
    if (!fbin) {
        fbin = fopen("../.eide/build/mach.bin", "rb");
    }
    if (fbin) {
        fseek(fbin, 0, SEEK_END);
        long sz = ftell(fbin);
        fseek(fbin, 0, SEEK_SET);
        if (sz > 0 && sz < 2 * 1024 * 1024) {
            uint8_t *bin_buf = (uint8_t *)s_mid; /* Dung tam vung dem stack stack_mid */
            bool found_icsr = false;
            bool found_pendsvset = false;
            uint8_t scb_base_pat[4] = {0x00, 0xED, 0x00, 0xE0};
            uint8_t icsr_pat[4] = {0x04, 0xED, 0x00, 0xE0};
            uint8_t pend_pat[4] = {0x00, 0x00, 0x00, 0x10};

            uint8_t win[4] = {0};
            size_t rd = fread(win, 1, 4, fbin);
            if (rd == 4) {
                while (1) {
                    if ((win[0] == icsr_pat[0] && win[1] == icsr_pat[1] && win[2] == icsr_pat[2] && win[3] == icsr_pat[3]) ||
                        (win[0] == scb_base_pat[0] && win[1] == scb_base_pat[1] && win[2] == scb_base_pat[2] && win[3] == scb_base_pat[3])) {
                        found_icsr = true;
                    }
                    if (win[0] == pend_pat[0] && win[1] == pend_pat[1] && win[2] == pend_pat[2] && win[3] == pend_pat[3]) {
                        found_pendsvset = true;
                    }
                    int next_b = fgetc(fbin);
                    if (next_b == EOF) break;
                    win[0] = win[1];
                    win[1] = win[2];
                    win[2] = win[3];
                    win[3] = (uint8_t)next_b;
                }
            }
            if (found_icsr && found_pendsvset) {
                ca7_ok = true;
                snprintf(ca7_msg, sizeof(ca7_msg), "Da tim thay SCB (0xE000ED00/04) va PENDSVSET (0x10000000) trong anh nhi phan");
            } else {
                snprintf(ca7_msg, sizeof(ca7_msg), "Thieu literal pool SCB=%d hoac PENDSVSET=%d trong mach.bin", found_icsr, found_pendsvset);
            }
        }
        fclose(fbin);
    }

    /* In ĐÚNG MỘT dòng JSON ở dòng cuối cùng theo quy ước của test.run */
    printf("{\"ca\": ["
           "{\"ten\": \"Chuyen ngu canh Task A -> Task B -> Task A khi delay\", \"dat\": %s, \"vi\": \"Vong lap dieu phoi ghi nhan dung chuoi vet thuc thi [A, B, A] va co xin chuyen ngu canh qua PendSV\"},"
           "{\"ten\": \"Danh thuc tac vu tien dinh qua hang doi tinh\", \"dat\": %s, \"vi\": \"Task B gui tin danh thuc Task A dang blocked ve ready lap tuc\"},"
           "{\"ten\": \"Hang doi het thoi han (Timeout)\", \"dat\": %s, \"vi\": \"Task A het timeout sau 3 tick va danh dau timed_out chinh xac\"},"
           "{\"ten\": \"Tien dinh 32 muc uu tien bang CLZ\", \"dat\": %s, \"vi\": \"Bo lap lich luon chon dung tac vu co muc uu tien cao nhat\"},"
           "{\"ten\": \"Son ngan xep va do muc nuoc\", \"dat\": %s, \"vi\": \"T1 (64w): con %u w chua cham / da dung %u w; T2 (128w): con %u w / da dung %u w\"},"
           "{\"ten\": \"Kiem tra 16 o vector trong anh nhi phan (.bin)\", \"dat\": %s, \"vi\": \"%s\"},"
           "{\"ten\": \"Kiem tra SCB_ICSR va PENDSVSET trong anh nhi phan (.bin)\", \"dat\": %s, \"vi\": \"%s\"}"
           "]}\n",
           ca1_ok ? "true" : "false",
           ca2_ok ? "true" : "false",
           ca3_ok ? "true" : "false",
           ca4_ok ? "true" : "false",
           ca5_ok ? "true" : "false",
           wm1_init, used1_init, wm2_init, used2_init,
           ca6_ok ? "true" : "false",
           ca6_msg,
           ca7_ok ? "true" : "false",
           ca7_msg);

    return (ca1_ok && ca2_ok && ca3_ok && ca4_ok && ca5_ok && ca6_ok && ca7_ok) ? 0 : 1;
}
