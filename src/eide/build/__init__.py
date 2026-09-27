# -*- coding: utf-8 -*-
"""Biên dịch và mô phỏng — bước G6 của MDD-40, phần tối thiểu để một dự án đi hết vòng.

Hai công cụ, hai kỷ luật giống nhau:

  `build.compile`  gọi trình biên dịch THẬT của chuỗi công cụ đã ghi trong hộ chiếu chip,
                   đọc lỗi nó in ra, và **không bao giờ báo đạt khi không có tệp ảnh nhị
                   phân**. Kích thước Flash/SRAM lấy từ `avr-size`, không ước lượng.

  `sim.run`        biên dịch phần LOGIC của firmware bằng trình biên dịch của máy chủ rồi
                   chạy nó trong một mô hình vật lý. Nó mô phỏng *mã thật*, không mô phỏng
                   một bản chép lại của thuật toán — một mô phỏng chạy trên mã khác với mã
                   nạp vào chip là một mô phỏng nói về một robot khác.

Vì sao tách khỏi `eide/tools/`: mọi thứ ở đây chạy tiến trình con và đọc kết quả thật, nên
nó cần được thử riêng mà không cần dựng cả một tác tử.
"""

from .mo_phong import KetQuaMoPhong, chay_mo_phong
from .toolchain import KetQuaBienDich, LoiBienDich, bien_dich, tim_chuoi_cong_cu

__all__ = ["KetQuaBienDich", "LoiBienDich", "bien_dich", "tim_chuoi_cong_cu",
           "KetQuaMoPhong", "chay_mo_phong"]
