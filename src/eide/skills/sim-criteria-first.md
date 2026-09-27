# sim-criteria-first
tu_khoa: mô phỏng, tiêu chí, assert, ngưỡng, sim, nghiệm thu, đạt
khi_nao: Trước khi chạy bất kỳ mô phỏng hay phép thử nào có thể "đạt" hoặc "không đạt".

## Thứ tự bắt buộc

1. **Nêu tiêu chí trước.** Gọi `sim.criteria` với từng assert: đo gì, phép so, ngưỡng, đơn
   vị, **đo YÊU CẦU nào**, và **ngưỡng lấy từ đâu**.
2. **Khai phần không mô phỏng được.** Ngoại vi nào mô hình không dựng (đèn WS2812 định thời
   800 kHz, cảm biến siêu âm, bus thật…) — ghi vào `khong_mo_phong_duoc` kèm cách bù.
3. **Trình cho người dùng xác nhận.** Tiêu chí là của họ. Gọi lại `sim.criteria` với
   `trich_loi` là câu họ nói. Không tự xác nhận hộ.
4. **Chạy.** `sim.run` đọc số đo và so với ngưỡng.

## Ba điều không được làm

- **Không chạy trước rồi đặt tiêu chí sau.** Tiêu chí đặt sau kết quả luôn vừa khít với kết
  quả, và nó không còn đo gì nữa.
- **Không sửa ngưỡng để một phép thử thành "đạt".** Nếu ngưỡng sai thì nói nó sai ở đâu và
  vì sao, rồi để người dùng quyết — việc đó đi qua cổng G-QUAL.
- **Không tuyên "đạt" cho phần chưa đo.** Thiếu số đo là *chưa đủ dữ kiện*, và câu đó phải
  xuất hiện trong kết luận chứ không nằm im trong tiêu chí.

## Viết chương trình mô phỏng cho đúng

Chương trình chỉ **đo và in số**, dòng cuối là JSON: `{"do": {"A1": 3.0, "A2": 1.07}}`. Nó
không tự kết luận. Mã assert (`A1`) phải trùng với mã trong tiêu chí — lệch mã thì EIDE báo
"số đo thừa" và assert tương ứng thành "chưa đo được".

Mô phỏng phải gọi **đúng mã sẽ nạp vào chip**. Chép lại thuật toán sang một tệp khác để mô
phỏng là mô phỏng một chương trình khác.
