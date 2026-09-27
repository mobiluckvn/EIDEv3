#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <math.h>

#include "../firmware/control.h"

/**
 * @file plant.c
 * @brief Mô hình con lắc ngược hai bánh và vòng mô phỏng kiểm thử điều khiển cân bằng.
 * Chạy trên máy tính chủ, liên kết với logic firmware/control.c.
 */

/* Quy đổi throttle sang vận tốc bánh xe theo mục 7.6 */
static double throttle_to_velocity(int16_t throttle)
{
    if (throttle == 0) {
        return 0.0;
    }
    double pi_val = 4.0 * atan(1.0);
    if (throttle > 0) {
        return pi_val / ((double)throttle + 1.0);
    } else {
        return -pi_val / ((double)(-throttle) + 1.0);
    }
}

/* Quy đổi vận tốc mong muốn sang throttle theo Bảng 18 mục 7.6 */
static int16_t velocity_to_throttle(double v_des)
{
    double abs_v = fabs(v_des);
    if (abs_v < 0.008) {
        return 0; /* Đứng im dưới 0.008 m/s (tương ứng throttle > 400) */
    }
    double pi_val = 4.0 * atan(1.0);
    double th_val = (pi_val / abs_v) - 1.0;
    if (th_val < 1.0) th_val = 1.0;
    if (th_val > 400.0) th_val = 400.0;

    int16_t th_int = (int16_t)(th_val + 0.5);
    return (v_des > 0.0) ? th_int : (int16_t)(-th_int);
}

int main(void)
{
    const double deg_to_rad = atan(1.0) / 45.0;
    const double rad_to_deg = 45.0 / atan(1.0);

    const double dt = (double)4 / 1000.0; /* Bước 4 ms */
    const int total_steps = 5 * 250;     /* 5 giây */
    const int stable_step = 3 * 250;     /* 2 giây cuối bắt đầu từ giây thứ 3 */

    /* Góc nghiêng ban đầu 3 độ theo yêu cầu */
    double theta = 3.0 * deg_to_rad;
    double theta_dot = 0.0;
    double wheel_vel = 0.0;

    /* Tham số con lắc ngược g/L và 1/L */
    const double g_over_L = 80.0;
    const double one_over_L = 8.0;

    /* Khởi tạo trạng thái bộ điều khiển từ firmware/control.c */
    control_state_t cstate;
    control_init(&cstate);

    pid_config_t pcfg;
    pcfg.kp = 1800;   /* Hệ số P quy đổi sang vận tốc */
    pcfg.ki = 10;     /* Hệ số I */
    pcfg.kd = 120;    /* Hệ số D */
    pcfg.target_mdeg = 0;
    pcfg.max_integral = 5000;
    pcfg.max_output = 1500; /* Vận tốc tối đa ~1.5 m/s */

    double max_angle_deg = 0.0;
    double final_angle_deg = 0.0;
    bool passed = true;

    for (int step = 0; step < total_steps; step++) {
        double current_deg = fabs(theta * rad_to_deg);
        if (current_deg > max_angle_deg) {
            max_angle_deg = current_deg;
        }

        /* Tiêu chí 1: Góc luôn dưới 15 độ */
        if (current_deg >= 15.0) {
            passed = false;
        }

        /* Tiêu chí 2: Trong 2 giây cuối dưới 2 độ */
        if (step >= stable_step && current_deg >= 2.0) {
            passed = false;
        }

        /* 1. Sinh số đo IMU giả từ trạng thái thực của con lắc */
        int16_t raw_ax = (int16_t)(8192.0 * cos(theta));
        int16_t raw_az = (int16_t)(-8192.0 * sin(theta) - 102.0);
        int16_t raw_gy = (int16_t)(theta_dot * rad_to_deg * 131.0);

        /* 2. Gọi CHÍNH XÁC mã logic của firmware/control.c */
        control_update_imu(&cstate, raw_ax, raw_az, raw_gy, 0, 131, 4);
        int16_t pid_out = control_calc_pid(&cstate, &pcfg, 4);

        /* Quy đổi đầu ra PID thành vận tốc mong muốn (m/s) */
        double v_desired = (double)pid_out / 1000.0;

        /* Quy ra throttle theo đúng bảng mục 7.6 */
        int16_t throttle = velocity_to_throttle(v_desired);

        /* 3. Mô hình con lắc ngược và gia tốc bánh xe từ throttle */
        double target_vel = throttle_to_velocity(throttle);

        double wheel_accel = (target_vel - wheel_vel) / dt;
        if (wheel_accel > 12.0) wheel_accel = 12.0;
        if (wheel_accel < -12.0) wheel_accel = -12.0;

        wheel_vel += wheel_accel * dt;

        /* Gia tốc góc: theta_ddot = (g/L)*sin(theta) - (wheel_accel/L)*cos(theta) */
        double theta_ddot = g_over_L * sin(theta) - (wheel_accel * one_over_L) * cos(theta);
        theta_ddot -= 0.15 * theta_dot; /* Lực cản nhớt nhẹ */

        theta_dot += theta_ddot * dt;
        theta += theta_dot * dt;
    }

    final_angle_deg = fabs(theta * rad_to_deg);

    /* In ra ĐÚNG MỘT dòng JSON theo yêu cầu */
    printf("{\"dat\": %s, \"goc_max_do\": %.3f, \"goc_cuoi_do\": %.3f, \"thoi_gian_s\": %.2f}\n",
           passed ? "true" : "false",
           max_angle_deg,
           final_angle_deg,
           5.0);

    return 0;
}
