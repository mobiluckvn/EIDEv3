#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#if __has_include("ui_state.h")
#include "ui_state.h"
#elif __has_include("firmware/ui_state.h")
#include "firmware/ui_state.h"
#elif __has_include("../firmware/ui_state.h")
#include "../firmware/ui_state.h"
#endif

#define UI_STATE_API __attribute__((weak))
#if __has_include("firmware/ui_state.c")
#include "firmware/ui_state.c"
#elif __has_include("../firmware/ui_state.c")
#include "../firmware/ui_state.c"
#elif __has_include("ui_state.c")
#include "ui_state.c"
#endif

typedef struct {
    const char *ten;
    bool dat;
    char vi[128];
} test_case_t;

int main(void)
{
    test_case_t cases[10];
    int count = 0;

    /* A1: Khoi tao trang thai ban dau la UI_SCREEN_MAIN */
    UI_State_Init();
    ui_screen_t s1 = UI_State_Get();
    cases[count].ten = "A1 khoi tao UI_SCREEN_MAIN";
    cases[count].dat = (s1 == UI_SCREEN_MAIN);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "State_Get() = %d, mong doi %d", s1, UI_SCREEN_MAIN);
    count++;

    /* A2: Cham vao giua nut (400, 425) */
    int r2 = UI_State_CheckTouch(400, 425);
    cases[count].ten = "A2 cham giua nut";
    cases[count].dat = (r2 == 1);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "CheckTouch(400, 425) = %d, mong doi 1", r2);
    count++;

    /* A3: Cham ngoai vung nut (50, 50) */
    int r3 = UI_State_CheckTouch(50, 50);
    cases[count].ten = "A3 cham ngoai nut";
    cases[count].dat = (r3 == 0);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "CheckTouch(50, 50) = %d, mong doi 0", r3);
    count++;

    /* A4: Chuyen trang thai tu Main sang Details */
    UI_State_Init();
    ui_screen_t s4 = UI_State_Toggle();
    cases[count].ten = "A4 toggle MAIN sang DETAILS";
    cases[count].dat = (s4 == UI_SCREEN_DETAILS);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "State_Toggle() = %d, mong doi %d", s4, UI_SCREEN_DETAILS);
    count++;

    /* A5: Chuyen trang thai tu Details ve Main */
    ui_screen_t s5 = UI_State_Toggle();
    cases[count].ten = "A5 toggle DETAILS ve MAIN";
    cases[count].dat = (s5 == UI_SCREEN_MAIN);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "State_Toggle() = %d, mong doi %d", s5, UI_SCREEN_MAIN);
    count++;

    /* A6: Toa do hoan doi truc (425, 400) do huong FT6206 */
    int r6 = UI_State_CheckTouch(425, 400);
    cases[count].ten = "A6 hoan doi truc FT6206";
    cases[count].dat = (r6 == 1);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "CheckTouch(425, 400) = %d, mong doi 1", r6);
    count++;

    /* A7: Cham bien trong nut (150, 380) */
    int r7 = UI_State_CheckTouch(150, 380);
    cases[count].ten = "A7 bien trong nut (150, 380)";
    cases[count].dat = (r7 == 1);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "CheckTouch(150, 380) = %d, mong doi 1", r7);
    count++;

    /* A8: Cham ngay ngoai bien nut (149, 380) */
    int r8 = UI_State_CheckTouch(149, 380);
    cases[count].ten = "A8 ngay ngoai bien (149, 380)";
    cases[count].dat = (r8 == 0);
    snprintf(cases[count].vi, sizeof(cases[count].vi), "CheckTouch(149, 380) = %d, mong doi 0", r8);
    count++;

    int failed = 0;
    for (int i = 0; i < count; i++) {
        if (!cases[i].dat) failed++;
    }

    /* In dung mot dong JSON o cuoi bat dau bang { */
    printf("{\"ca\": [");
    for (int i = 0; i < count; i++) {
        printf("{\"ten\": \"%s\", \"dat\": %s, \"vi\": \"%s\"}%s",
               cases[i].ten,
               cases[i].dat ? "true" : "false",
               cases[i].vi,
               (i < count - 1) ? ", " : "");
    }
    printf("]}\n");

    return (failed == 0) ? 0 : 1;
}
