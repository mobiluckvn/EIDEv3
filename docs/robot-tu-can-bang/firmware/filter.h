#ifndef FILTER_H_
#define FILTER_H_

typedef struct {
    float angle;      /* Góc nghiêng ước lượng hiện tại (độ) */
    float gyro_rate;  /* Tốc độ góc (độ/giây) */
    float alpha;      /* Trọng số bộ lọc bù (anh cho, chưa có tài liệu) */
    float dt;         /* Khoảng thời gian lấy mẫu (giây) */
} comp_filter_t;

/* Khởi tạo bộ lọc bù với chu kỳ lấy mẫu dt và hệ số alpha */
void filter_init(comp_filter_t *f, float alpha, float dt);

/* Cập nhật bộ lọc bù với dữ liệu gia tốc và con quay */
float filter_update(comp_filter_t *f, float accel_angle, float gyro_rate);

#endif /* FILTER_H_ */
