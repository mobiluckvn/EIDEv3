/**
 * @file rtos.h
 * @brief Nhân hệ điều hành thời gian thực (RTOS Kernel) tự viết cho ARM Cortex-M4F.
 * @details Hỗ trợ đa tác vụ Preemptive, chuyển ngữ cảnh dựa trên PendSV & SysTick,
 *          quản lý ngăn xếp riêng biệt (PSP) và hỗ trợ ngữ cảnh FPU.
 *          Tuân thủ đặc tả kiến trúc ADR-01, ADR-03, ADR-04.
 */

#ifndef RTOS_H_
#define RTOS_H_

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* =========================================================================
 * Cấu hình tham số hệ thống nhân RTOS
 * ========================================================================= */
#define OS_MAX_TASKS            8       /**< Số tác vụ tối đa hệ thống quản lý */
#define OS_TICK_RATE_HZ         1000    /**< Tần số nhịp định thời SysTick (1 ms) */

/* =========================================================================
 * Định nghĩa máy trạng thái tác vụ
 * ========================================================================= */
typedef enum {
    OS_TASK_READY = 0,      /**< Tác vụ sẵn sàng nhận quyền CPU */
    OS_TASK_BLOCKED,        /**< Tác vụ đang ngủ hoặc chờ tài nguyên */
    OS_TASK_SUSPENDED       /**< Tác vụ bị tạm ngưng vô thời hạn */
} os_task_state_t;

typedef void (*os_task_func_t)(void *arg);

/* =========================================================================
 * Cấu trúc khối điều khiển tác vụ (Task Control Block - TCB)
 * Khớp hoàn toàn với đặc tả trong hiện vật ADR-03.
 * LƯU Ý: Trường 'sp' BẮT BUỘC đặt ở offset 0 để mã hợp ngữ PendSV truy cập trực tiếp.
 * ========================================================================= */
typedef struct os_tcb {
    uint32_t           *sp;                 /**< [Offset 0] Đỉnh ngăn xếp PSP hiện tại */
    uint32_t            priority;           /**< Mức ưu tiên (số càng lớn ưu tiên càng cao) */
    os_task_state_t     state;              /**< Trạng thái hiện thời của tác vụ */
    uint32_t            delay_ticks;        /**< Số tick còn lại cần ngủ (dùng cho os_delay) */
    uint32_t           *stack_base;         /**< Con trỏ đáy ngăn xếp dùng kiểm tra tràn stack */
    uint32_t            stack_size_words;   /**< Kích thước ngăn xếp tính theo đơn vị từ 32-bit */
    const char         *name;               /**< Chuỗi tên tác vụ phục vụ giám sát và debug */
} os_tcb_t;

/* =========================================================================
 * Giao diện lập trình ứng dụng (RTOS Public API)
 * ========================================================================= */

/**
 * @brief Khởi tạo các cấu trúc dữ liệu nội bộ của nhân RTOS.
 */
void os_init(void);

/**
 * @brief Tạo và đăng ký một tác vụ mới vào nhân RTOS.
 * @param tcb Con trỏ tới khối TCB của tác vụ.
 * @param name Tên tác vụ mô tả (ASCII).
 * @param entry Hàm điểm vào của tác vụ (Task Entry Point).
 * @param arg Tham số truyền vào hàm tác vụ.
 * @param stack Mảng bộ nhớ ngăn xếp do người dùng cấp phát (căn lề 8-byte).
 * @param stack_size_words Kích thước mảng ngăn xếp tính theo đơn vị từ (word = 4 bytes).
 * @param priority Mức ưu tiên (0..255).
 * @return 0 nếu thành công, -1 nếu đầy danh sách tác vụ hoặc tham số không hợp lệ.
 */
int8_t os_task_create(os_tcb_t *tcb,
                      const char *name,
                      os_task_func_t entry,
                      void *arg,
                      uint32_t *stack,
                      uint32_t stack_size_words,
                      uint32_t priority);

/**
 * @brief Khởi động nhân RTOS, cấu hình SysTick/PendSV và nhảy vào tác vụ ưu tiên cao nhất.
 * @note Hàm này chuyển từ MSP sang PSP và không bao giờ quay lại (Never Returns).
 */
void os_start(void);

/**
 * @brief Tạm dừng tác vụ hiện tại trong một khoảng thời gian xác định (tính bằng ms/tick).
 * @param ticks Thời gian tạm dừng tính theo chu kỳ tick (1 tick = 1 ms).
 */
void os_delay(uint32_t ticks);

/**
 * @brief Chủ động nhường quyền CPU cho tác vụ khác có cùng hoặc cao hơn mức ưu tiên.
 */
void os_yield(void);

/**
 * @brief Lấy giá trị bộ đếm nhịp hệ thống (System Tick Counter).
 * @return Giá trị tick tăng dần kể từ khi nhân khởi chạy.
 */
uint32_t os_get_tick(void);

#ifdef __cplusplus
}
#endif

#endif /* RTOS_H_ */
