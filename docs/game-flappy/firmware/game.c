/**
 * @file game.c
 * @brief Hiện thực máy trạng thái và mô hình vật lý game Flappy Bird.
 * @details Chạy định kỳ 20 ms trong tác vụ Task_GameLogic.
 *          Xử lý rơi tự do, đập cánh, di chuyển cọc, kiểm tra va chạm và tính điểm.
 *          Mô hình toạ độ và hình học khớp 100% với bản thiết kế ui_screen:choi.
 *          Sử dụng số cố định 1/8 pixel cho toạ độ và vận tốc chim để vật lý mượt mà.
 */

#include "game.h"

/* Các thông số kích thước truy vết từ thiết kế ui_screen:choi */
#define SCREEN_WIDTH            800
#define SCREEN_HEIGHT           480
#define GROUND_LEVEL_Y          420     /* ui_screen:choi ground_grass tại y=420 */

#define BIRD_COORD_X            160
#define BIRD_BOX_W              40
#define BIRD_BOX_H              30
#define BIRD_INIT_Y             210     /* ui_screen:choi bird_body tại y=210 */

#define PIPE_BOX_W              70      /* Khớp chiều rộng vành cọc rim (w=70) */
#define PIPE_GAP_HALF           65      /* Khe 130 px (y=145 đến y=275), tâm 210 */
#define PIPE1_INIT_X            380     /* ui_screen:choi pipe1_top_rim tại x=380 */
#define PIPE2_INIT_X            660     /* ui_screen:choi pipe2_top_rim tại x=660 */

/* Hằng số vật lý theo đơn vị fixed-point 1/8 pixel */
#define SUBPIXEL_SHIFT          3
#define TO_SUBPIXEL(px)         ((int16_t)((px) << SUBPIXEL_SHIFT))
#define TO_PIXEL(sub)           ((int16_t)((sub) >> SUBPIXEL_SHIFT))

#define GRAVITY_SUB             1       /* +1 đơn vị 1/8 px mỗi nhịp 20 ms = 0,125 px/tick^2 */
#define FLAP_VY_SUB             (-40)   /* -40 đơn vị 1/8 px mỗi nhịp = -5 px/tick */
#define MAX_FALL_VY_SUB         64      /* Giới hạn tốc độ rơi tối đa 8 px/tick */

/* Biến trạng thái tĩnh nội bộ của game */
static game_state_t s_state = GAME_STATE_START;

/* Toạ độ và vận tốc chim lưu ở định dạng fixed-point 1/8 pixel */
static int16_t s_bird_y     = TO_SUBPIXEL(BIRD_INIT_Y);
static int16_t s_bird_vy    = 0;

static int16_t s_pipe1_x     = PIPE1_INIT_X;
static int16_t s_pipe1_gap_y = 210;     /* Tâm khe cọc 1: (145 + 275) / 2 = 210 */
static bool    s_pipe1_passed = false;

static int16_t s_pipe2_x     = PIPE2_INIT_X;
static int16_t s_pipe2_gap_y = 250;     /* Tâm khe cọc 2: (185 + 315) / 2 = 250 */
static bool    s_pipe2_passed = false;

static uint16_t s_score      = 0;
static uint16_t s_best_score = 0;
static uint8_t  s_flap_power = 80;

/* =========================================================================
 * Khởi tạo trò chơi
 * ========================================================================= */
void game_init(void) {
    s_state = GAME_STATE_START;
    s_bird_y = TO_SUBPIXEL(BIRD_INIT_Y);
    s_bird_vy = 0;
    s_pipe1_x = PIPE1_INIT_X;
    s_pipe1_gap_y = 210;
    s_pipe1_passed = false;
    s_pipe2_x = PIPE2_INIT_X;
    s_pipe2_gap_y = 250;
    s_pipe2_passed = false;
    s_score = 0;
    s_flap_power = 80;
}

/* =========================================================================
 * Khởi động lại ván chơi
 * ========================================================================= */
void game_restart(void) {
    s_bird_y = TO_SUBPIXEL(BIRD_INIT_Y);
    s_bird_vy = 0;
    s_pipe1_x = PIPE1_INIT_X;
    s_pipe1_gap_y = 210;
    s_pipe1_passed = false;
    s_pipe2_x = PIPE2_INIT_X;
    s_pipe2_gap_y = 250;
    s_pipe2_passed = false;
    s_score = 0;
    s_flap_power = 80;
    s_state = GAME_STATE_PLAY;
}

/* =========================================================================
 * Xử lý sự kiện đập cánh nhảy lên (Jump)
 * ========================================================================= */
void game_trigger_jump(void) {
    if (s_state == GAME_STATE_START) {
        s_state = GAME_STATE_PLAY;
        s_bird_vy = FLAP_VY_SUB;
    } else if (s_state == GAME_STATE_PLAY) {
        s_bird_vy = FLAP_VY_SUB;
        s_flap_power = 100;
    } else if (s_state == GAME_STATE_GAMEOVER) {
        game_restart();
    }
}

/* =========================================================================
 * Bật/Tắt chế độ tạm dừng
 * ========================================================================= */
void game_toggle_pause(void) {
    if (s_state == GAME_STATE_PLAY) {
        s_state = GAME_STATE_PAUSE;
    } else if (s_state == GAME_STATE_PAUSE) {
        s_state = GAME_STATE_PLAY;
    }
}

/* =========================================================================
 * Kiểm tra va chạm hộp biên (AABB) giữa chim và một cặp cọc
 * ========================================================================= */
static bool check_pipe_collision(int16_t pipe_x, int16_t pipe_gap_y) {
    if ((BIRD_COORD_X + BIRD_BOX_W >= pipe_x) &&
        (BIRD_COORD_X <= pipe_x + PIPE_BOX_W)) {
        int16_t gap_top = pipe_gap_y - PIPE_GAP_HALF;
        int16_t gap_bottom = pipe_gap_y + PIPE_GAP_HALF;
        int16_t bird_y_px = TO_PIXEL(s_bird_y);

        if ((bird_y_px < gap_top) || (bird_y_px + BIRD_BOX_H > gap_bottom)) {
            return true;
        }
    }
    return false;
}

/* =========================================================================
 * Cập nhật chu kỳ vật lý 20 ms (50 Hz)
 * ========================================================================= */
void game_tick_20ms(void) {
    if (s_state != GAME_STATE_PLAY) {
        return;
    }

    /* 1. Trọng lực tác động lên chim (+1 subpixel mỗi nhịp 20 ms) */
    s_bird_vy += GRAVITY_SUB;
    if (s_bird_vy > MAX_FALL_VY_SUB) {
        s_bird_vy = MAX_FALL_VY_SUB;
    }
    s_bird_y += s_bird_vy;

    /* Giảm dần xung lực trên thanh hiển thị HUD */
    if (s_flap_power > 40) {
        s_flap_power -= 2;
    }

    /* Kiểm tra trần màn hình */
    if (s_bird_y < 0) {
        s_bird_y = 0;
        s_bird_vy = 0;
    }

    /* Kiểm tra va chạm mặt đất (mặt đất y=420 px, chim cao 30 px) */
    int16_t ground_sub = TO_SUBPIXEL(GROUND_LEVEL_Y - BIRD_BOX_H);
    if (s_bird_y >= ground_sub) {
        s_bird_y = ground_sub;
        s_state = GAME_STATE_GAMEOVER;
        if (s_score > s_best_score) {
            s_best_score = s_score;
        }
        return;
    }

    /* 2. Di chuyển các cọc ống nước sang trái */
    s_pipe1_x -= 3;
    if (s_pipe1_x < -PIPE_BOX_W) {
        s_pipe1_x += SCREEN_WIDTH;
        s_pipe1_gap_y = 170 + ((s_pipe1_gap_y * 7) % 100);
        s_pipe1_passed = false;
    }

    s_pipe2_x -= 3;
    if (s_pipe2_x < -PIPE_BOX_W) {
        s_pipe2_x += SCREEN_WIDTH;
        s_pipe2_gap_y = 190 + ((s_pipe2_gap_y * 11) % 100);
        s_pipe2_passed = false;
    }

    /* 3. Tính điểm khi chim vượt qua cọc */
    if (!s_pipe1_passed && (BIRD_COORD_X > s_pipe1_x + PIPE_BOX_W)) {
        s_score++;
        s_pipe1_passed = true;
        if (s_score > s_best_score) {
            s_best_score = s_score;
        }
    }
    if (!s_pipe2_passed && (BIRD_COORD_X > s_pipe2_x + PIPE_BOX_W)) {
        s_score++;
        s_pipe2_passed = true;
        if (s_score > s_best_score) {
            s_best_score = s_score;
        }
    }

    /* 4. Kiểm tra va chạm với cọc */
    if (check_pipe_collision(s_pipe1_x, s_pipe1_gap_y) ||
        check_pipe_collision(s_pipe2_x, s_pipe2_gap_y)) {
        s_state = GAME_STATE_GAMEOVER;
        if (s_score > s_best_score) {
            s_best_score = s_score;
        }
    }
}

/* =========================================================================
 * Xuất bản sao snapshot an toàn cho tác vụ render (toạ độ chuyển về pixel)
 * ========================================================================= */
void game_get_snapshot(game_snapshot_t *out_snapshot) {
    if (!out_snapshot) {
        return;
    }
    out_snapshot->state = s_state;
    out_snapshot->bird_y = s_bird_y;
    out_snapshot->bird_vy = TO_PIXEL(s_bird_vy);
    out_snapshot->pipe1_x = s_pipe1_x;
    out_snapshot->pipe1_gap_y = s_pipe1_gap_y;
    out_snapshot->pipe2_x = s_pipe2_x;
    out_snapshot->pipe2_gap_y = s_pipe2_gap_y;
    out_snapshot->score = s_score;
    out_snapshot->best_score = s_best_score;
    out_snapshot->flap_power = s_flap_power;
}

/* =========================================================================
 * Đọc trạng thái game hiện tại
 * ========================================================================= */
game_state_t game_get_state(void) {
    return s_state;
}
