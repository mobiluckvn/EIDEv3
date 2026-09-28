# -*- coding: utf-8 -*-
"""Chọn chuỗi công cụ theo DỰ ÁN LÀ GÌ, không theo MÁY CÓ GÌ.

Đo được ngày 28/09/2026, ca TC055 của bộ usecase. Dự án có đúng `firmware/main.c` — mã C
thuần cho AVR, không tệp `.ino` nào. Tác tử gọi `build.compile` không nêu `isa`, và:

    isa = isa or "avr8"                            # mặc định
    if cc.get("arduino-cli") and cc.get("fqbn"):   # avr8 CÓ fqbn, máy CÓ arduino-cli
        kq.cong_cu = "arduino-cli"                 # → chọn, dù không có .ino nào

`arduino-cli compile` đòi một sketch, nên nó trả `E4002` với một thông điệp nói về **định
dạng sketch của Arduino** — cho một người vừa hỏi về `-O3`. Họ sẽ đi tìm một tệp `.ino` mà
dự án không bao giờ cần: đúng nghĩa *một lời khuyên sai tệ hơn im lặng*.

Hậu quả không dừng ở một thông điệp. Nó **chặn đứng** ca kiểm: TC055 không bao giờ tới được
phần chạy hồi quy để phát hiện `-O3` làm hỏng chức năng. Một lỗi ở bước chọn công cụ che mất
toàn bộ thứ nằm sau nó.
"""

from __future__ import annotations

import pytest

from eide.build.toolchain import bien_dich, tim_chuoi_cong_cu

# Hỏi ĐÚNG cái mà mã thật hỏi.
#
# Bản đầu dùng `shutil.which`, và cả hai ca đáng giá nhất đều bị BỎ QUA trên máy này: mã thật
# tìm `avr-gcc` và `arduino-cli` trong cả thư mục `~/Library/Arduino15/…`, không chỉ trên
# PATH. Một ca bị bỏ qua không chứng minh gì, mà bảng kết quả thì vẫn xanh.
_CC = tim_chuoi_cong_cu("avr8") or {}
co_avr = bool(_CC.get("avr-gcc"))
co_arduino = bool(_CC.get("arduino-cli"))


@pytest.mark.skipif(not co_avr, reason="máy không có avr-gcc")
def test_du_an_C_thuan_KHONG_bi_day_sang_arduino_cli(tmp_path):
    """Thư mục có `.c` mà không có `.ino` thì không phải sketch — dù máy có arduino-cli."""
    fw = tmp_path / "firmware"
    fw.mkdir()
    (fw / "main.c").write_text("int main(void){ return 0; }\n", "utf-8")

    kq = bien_dich(goc=tmp_path, sketch=fw, isa="avr8")

    assert kq.cong_cu == "avr-gcc", (
        f"chọn {kq.cong_cu!r} cho một dự án C thuần — người dùng sẽ nhận một lỗi về định "
        "dạng sketch Arduino cho một việc không liên quan gì tới Arduino")
    # Kiểm LỆNH, không kiểm đường dẫn: `avr-gcc` đúng trên máy này nằm ở
    # `~/Library/Arduino15/…`, nên chuỗi "arduino" có mặt trong đường dẫn mà chẳng nói lên
    # điều gì. Dấu hiệu thật của đường arduino-cli là `compile --fqbn`.
    assert "--fqbn" not in kq.lenh and "compile" not in kq.lenh


@pytest.mark.skipif(not co_arduino, reason="máy không có arduino-cli")
def test_thu_muc_CO_ino_van_di_duong_arduino(tmp_path):
    """Cái phanh không được chặn đường đi đúng: sketch thật vẫn phải dịch bằng arduino-cli."""
    fw = tmp_path / "nhay_led"
    fw.mkdir()
    (fw / "nhay_led.ino").write_text("void setup(){} void loop(){}\n", "utf-8")

    kq = bien_dich(goc=tmp_path, sketch=fw, isa="avr8")

    assert kq.cong_cu == "arduino-cli"


@pytest.mark.skipif(not co_arduino, reason="máy không có arduino-cli")
def test_mot_tep_ino_le_van_la_sketch(tmp_path):
    """`sketch` có thể là một TỆP, không chỉ một thư mục."""
    p = tmp_path / "a.ino"
    p.write_text("void setup(){} void loop(){}\n", "utf-8")

    assert bien_dich(goc=tmp_path, sketch=p, isa="avr8").cong_cu == "arduino-cli"


def test_duong_dan_khong_ton_tai_thi_khong_doan_la_sketch(tmp_path):
    """Không có gì ở đó thì không được đoán bừa là sketch — đoán sai ở đây đẻ ra đúng cái
    thông điệp lạc đề mà bài kiểm này sinh ra để chặn."""
    from eide.build.toolchain import _la_sketch_arduino

    assert not _la_sketch_arduino(tmp_path / "khong-co")
    assert not _la_sketch_arduino(tmp_path)
