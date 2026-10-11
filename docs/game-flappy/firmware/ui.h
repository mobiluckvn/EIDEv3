/**
 * @file ui.h
 * @brief Giao diện khai báo các hàm vẽ màn hình đồ hoạ Flappy Bird trên LCD STM32F469I-DISCO.
 * @details Các hàm thực thi được sinh bởi `screen.codegen` từ hiện vật màn hình trong kho.
 */

#ifndef UI_H_
#define UI_H_

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Vẽ toàn bộ giao diện màn hình bắt đầu (ui_screen:batdau).
 */
void ui_ve_batdau(void);

/**
 * @brief Vẽ toàn bộ giao diện màn hình chơi Flappy Bird tĩnh ban đầu (ui_screen:choi).
 */
void ui_ve_choi(void);

/**
 * @brief Vẽ toàn bộ giao diện màn hình kết thúc (ui_screen:gameover).
 */
void ui_ve_gameover(void);

#ifdef __cplusplus
}
#endif

#endif /* UI_H_ */
