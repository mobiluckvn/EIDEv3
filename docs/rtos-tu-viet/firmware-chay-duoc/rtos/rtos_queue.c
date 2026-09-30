/**
 * @file rtos_queue.c
 * @brief Hiện thực cơ chế giao tiếp liên tác vụ (IPC) qua hàng đợi tĩnh dạng Ring-Buffer
 *        đảm bảo an toàn luồng trong môi trường nhân RTOS tiền định.
 */

#include "rtos_types.h"
#include "stm32f469xx.h"
#include "core_cm4.h"

/* Khai báo hàm sao chép bộ nhớ từ thư viện stub của dự án */
extern void *memcpy(void *dest, const void *src, size_t n);

/**
 * @brief Khởi tạo hàng đợi tĩnh IPC.
 */
rtos_status_t rtos_queue_init(
    rtos_queue_t *q,
    void *buffer,
    uint32_t item_size,
    uint32_t capacity
)
{
    if ((q == NULL) || (buffer == NULL) || (item_size == 0) || (capacity == 0)) {
        return RTOS_ERR_PARAM;
    }

    q->buffer = (uint8_t *)buffer;
    q->item_size = item_size;
    q->capacity = capacity;
    q->count = 0;
    q->head = 0;
    q->tail = 0;
    q->waiting_send = NULL;
    q->waiting_recv = NULL;

    return RTOS_OK;
}

/**
 * @brief Đẩy một phần tử dữ liệu vào hàng đợi (Thread-safe).
 */
rtos_status_t rtos_queue_send(
    rtos_queue_t *q,
    const void *item,
    uint32_t timeout_ticks
)
{
    if ((q == NULL) || (item == NULL)) {
        return RTOS_ERR_PARAM;
    }

    while (1) {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();

        /* Nếu hàng đợi còn chỗ trống */
        if (q->count < q->capacity) {
            uint8_t *dest = q->buffer + (q->tail * q->item_size);
            memcpy(dest, item, q->item_size);

            q->tail = (q->tail + 1U) % q->capacity;
            q->count++;

            __set_PRIMASK(primask);
            return RTOS_OK;
        }

        __set_PRIMASK(primask);

        /* Nếu không chờ timeout hoặc đã hết thời gian */
        if (timeout_ticks == 0) {
            return RTOS_ERR_FULL;
        }

        /* Chờ 1 nhịp và thử lại */
        rtos_delay_ms(1);
        timeout_ticks--;
    }
}

/**
 * @brief Lấy một phần tử dữ liệu ra khỏi hàng đợi (Thread-safe).
 */
rtos_status_t rtos_queue_receive(
    rtos_queue_t *q,
    void *item,
    uint32_t timeout_ticks
)
{
    if ((q == NULL) || (item == NULL)) {
        return RTOS_ERR_PARAM;
    }

    while (1) {
        uint32_t primask = __get_PRIMASK();
        __disable_irq();

        /* Nếu hàng đợi có sẵn phần tử */
        if (q->count > 0) {
            uint8_t *src = q->buffer + (q->head * q->item_size);
            memcpy(item, src, q->item_size);

            q->head = (q->head + 1U) % q->capacity;
            q->count--;

            __set_PRIMASK(primask);
            return RTOS_OK;
        }

        __set_PRIMASK(primask);

        /* Nếu không chờ timeout hoặc đã hết thời gian */
        if (timeout_ticks == 0) {
            return RTOS_ERR_EMPTY;
        }

        /* Chờ 1 nhịp và thử lại */
        rtos_delay_ms(1);
        timeout_ticks--;
    }
}
