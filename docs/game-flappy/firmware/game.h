/**
 * @file game.h
 * @brief Giao diện máy trạng thái game và logic vật lý chim/cọc Flappy Bird.
 * @details Cung cấp kiểu dữ liệu snapshot đồng bộ cho tác vụ vẽ Task_Render.
 */

#ifndef GAME_H_
#define GAME_H_

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    GAME_STATE_START = 0,   /**< Màn hình mở đầu */
    GAME_STATE_PLAY,        /**< Đang chơi thời gian thực */
    GAME_STATE_PAUSE,       /**< Tạm dừng */
    GAME_STATE_GAMEOVER     /**< Kết thúc ván chơi */
} game_state_t;

typedef struct {
    game_state_t state;
    int16_t      bird_y;
    int16_t      bird_vy;
    int16_t      pipe1_x;
    int16_t      pipe1_gap_y;
    int16_t      pipe2_x;
    int16_t      pipe2_gap_y;
    uint16_t     score;
    uint16_t     best_score;
    uint8_t      flap_power;
} game_snapshot_t;

void game_init(void);
void game_tick_20ms(void);
void game_trigger_jump(void);
void game_toggle_pause(void);
void game_restart(void);
void game_get_snapshot(game_snapshot_t *out_snapshot);
game_state_t game_get_state(void);

#ifdef __cplusplus
}
#endif

#endif /* GAME_H_ */
