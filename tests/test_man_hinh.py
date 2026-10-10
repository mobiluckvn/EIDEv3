# -*- coding: utf-8 -*-
"""Hồ sơ MÀN HÌNH — bước 1 của năng lực thiết kế UI nhúng.

Vì sao hồ sơ phải có trước phần thiết kế: `grep` cả kho ngày 10/10/2026 không ra **một** Fact
nào về màn hình — `KHOA_CHUAN` không có khoá `lcd.*` nào, `HoChieu` của linh kiện cũng không có
trường nào cho màn hình. Nên nếu làm phần thiết kế trước, tác tử sẽ **tự nhớ ra** `800×480`.

Đó không phải một lo xa. Nó đã xảy ra ba lần trong dự án này (bài học "hằng số phần cứng phải
tra, không được dựng lại"): ba hằng số tự nhớ đã tự chế ra ba bằng chứng sai. Một bản thiết kế
UI vẽ đúng đẹp trên một độ phân giải SAI thì mọi toạ độ trong nó đều sai, và màn hình thật sẽ
cắt mất một phần — mà không lỗi nào kêu lên.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from eide.knowledge import man_hinh as MH

GOC = Path(__file__).parents[1]


# =========================================================================== đọc độ phân giải
def test_doc_do_phan_giai_ba_cach_viet():
    """`800x480`, `800 × 480`, `480*272` — ba cách tài liệu thật viết cùng một thứ."""
    assert MH.doc_do_phan_giai("LCD 4 inch 800x480 driver OTM8009A") == [(800, 480)]
    assert MH.doc_do_phan_giai("Resolution: 800 × 480 pixels") == [(800, 480)]
    assert MH.doc_do_phan_giai("panel 480*272") == [(480, 272)]


def test_man_hinh_KY_TU_khong_bi_doc_thanh_pixel():
    """`16x2` là LCD **ký tự** (16 cột × 2 dòng), không phải một panel 16×2 **pixel**.

    Đây là ca sai đắt nhất của phép đọc này, và nó có thật: HD44780 là màn hình phổ biến nhất
    trong dạy học nhúng. Đọc `16x2` thành độ phân giải thì mọi toạ độ của bản thiết kế sẽ nằm
    trong một khung 16×2 — và bản vẽ sẽ trống trơn mà không ai hiểu vì sao.
    """
    assert MH.doc_do_phan_giai("LCD ký tự 16x2 HD44780") == []
    assert MH.doc_man_hinh_ky_tu("LCD ký tự 16x2 HD44780") == [(16, 2)]
    assert MH.doc_man_hinh_ky_tu("display 20x4 character") == [(20, 4)]
    # Và ngược lại: một panel đồ hoạ KHÔNG bị đọc thành màn hình ký tự.
    assert MH.doc_man_hinh_ky_tu("LCD 800x480") == []


def test_khong_doc_con_so_KHONG_PHAI_do_phan_giai():
    """Hai số có dấu `x` ở giữa chưa chắc là độ phân giải.

    `2x AA battery`, `DSI 2-lane`, `1x UART` — và một kích thước vật lý `60 x 40 mm`. Nhận bừa
    là cách sinh ra một hồ sơ màn hình trông hợp lệ mà sai hoàn toàn, mà hồ sơ ấy lại là thứ
    mọi toạ độ của bản thiết kế dựa vào.
    """
    for chu in ("2x AA battery", "DSI 2-lane interface", "board size 60 x 40 mm",
                "1x UART, 2x SPI", "stack 4x1024 words"):
        assert MH.doc_do_phan_giai(chu) == [], chu


# =========================================================================== hệ màu
def test_doc_he_mau():
    assert MH.doc_he_mau("Framebuffer ARGB8888 / RGB565") == ["ARGB8888", "RGB565"]
    assert MH.doc_he_mau("16-bit color RGB565") == ["RGB565"]
    assert MH.doc_he_mau("không nói gì về màu") == []


def test_bit_moi_diem_tra_bang_chu_khong_doan():
    """Số bit mỗi điểm ảnh là một hằng số của ĐỊNH DẠNG, và nó phải tra bảng.

    Nó đi vào phép tính bộ đệm khung, và một con số sai ở đây cho ra một kết luận sai về RAM —
    đúng loại kết luận mà không trình biên dịch nào bác lại.
    """
    assert MH.BIT_MOI_DIEM["RGB565"] == 16
    assert MH.BIT_MOI_DIEM["ARGB8888"] == 32
    assert MH.BIT_MOI_DIEM["RGB888"] == 24
    assert MH.BIT_MOI_DIEM["L8"] == 8
    assert MH.bit_moi_diem("rgb565") == 16, "tra không phân biệt chữ hoa/thường"
    assert MH.bit_moi_diem("KHONG_CO") is None, "định dạng lạ thì nói KHÔNG BIẾT, đừng đoán"


def test_kich_thuoc_dem_khung():
    """800×480 ARGB8888 = 1 536 000 byte. Phép tính, không phải con số nhớ."""
    assert MH.kich_thuoc_dem(800, 480, "ARGB8888") == 800 * 480 * 4
    assert MH.kich_thuoc_dem(800, 480, "RGB565") == 800 * 480 * 2
    assert MH.kich_thuoc_dem(800, 480, "KHONG_CO") is None


# =========================================================================== hồ sơ
def test_ho_so_NOI_RO_truong_nao_THIEU():
    """Không trường nào được điền mặc định. Thiếu thì NÓI RA.

    `cam_ung = False` và `cam_ung = None` là hai điều khác nhau: một nói *"panel này không có
    cảm ứng"*, một nói *"tài liệu không nói"*. Gộp chúng lại là cách một bản thiết kế có nút
    bấm được duyệt cho một màn hình không ai bấm được.
    """
    hs = MH.ho_so_tu_chu("LCD 800x480 RGB565")
    assert (hs.rong, hs.cao) == (800, 480)
    assert hs.he_mau == "RGB565"
    assert hs.cam_ung is None, "tài liệu không nói → KHÔNG BIẾT, không phải False"
    assert hs.inch is None and hs.dpi is None
    assert "lcd.inch" in hs.thieu and "lcd.touch" in hs.thieu, hs.thieu
    assert "lcd.width" not in hs.thieu


def test_dpi_la_so_TINH_RA_khong_phai_so_doc_duoc():
    """DPI = đường chéo pixel / đường chéo inch. Nó phải được TÍNH, và phải tự khai là tính.

    Một Fact "đọc được từ tài liệu" và một số "tính ra từ hai Fact" có độ tin cậy khác nhau,
    và N1 đòi biết cái nào là cái nào.
    """
    hs = MH.ho_so_tu_chu("LCD 4 inch 800x480 RGB565")
    assert hs.inch == 4.0
    assert hs.dpi is not None and 232 < hs.dpi < 234, hs.dpi   # √(800²+480²)/4 ≈ 233.2
    assert hs.dpi_la_tinh_ra is True
    assert "lcd.dpi" not in hs.thieu


def test_ho_so_khong_du_do_phan_giai_thi_KHONG_HOP_LE():
    """Không có độ phân giải thì không có hồ sơ — và `hop_le` phải nói `False`.

    Đây là cửa mà phần thiết kế dựa vào: nó chỉ được chạy khi hồ sơ hợp lệ. Trả về một hồ sơ
    `rong=0` trông như một hồ sơ thật sẽ làm mọi phép kiểm biên sau đó vô nghĩa.
    """
    hs = MH.ho_so_tu_chu("một tài liệu không nói gì về màn hình")
    assert hs.hop_le is False
    assert hs.rong == 0 and hs.cao == 0
    assert "lcd.width" in hs.thieu and "lcd.height" in hs.thieu


def test_ho_so_man_hinh_KY_TU_tu_khai_la_khong_ve_duoc():
    """Màn hình ký tự có hồ sơ, nhưng nó KHÔNG vẽ được bản thiết kế pixel — và nói ra.

    Im lặng ở đây sẽ cho một bản vẽ 16×2 pixel, tức một bản vẽ trống. Nói ra thì người dùng
    biết ngay là phần thiết kế này chưa làm cho loại màn hình ấy.
    """
    hs = MH.ho_so_tu_chu("LCD ký tự 16x2 HD44780")
    assert hs.loai == "ky_tu"
    assert (hs.cot, hs.dong) == (16, 2)
    assert hs.hop_le is False
    assert "ký tự" in hs.vi_sao_khong_hop_le, hs.vi_sao_khong_hop_le


# =========================================================================== bộ đệm vs RAM
def test_dem_khung_KHONG_VUA_ram_noi_thi_keu_len():
    """800×480 ARGB8888 cần **1 536 000 byte**; SRAM nội của bo là **324 KB** theo tài liệu
    kiến trúc của chính dự án. Nó KHÔNG vừa, và chỗ này phải kêu lên.

    Đây là ca "trình biên dịch im lặng tuyệt đối" của riêng phần UI: khai một bộ đệm khung quá
    to thì linker có thể vẫn qua (nếu nó nằm ở `.bss` của SDRAM ngoài theo script liên kết),
    hoặc đổ ở một dòng không ai đọc. Và nếu nó lọt, màn hình sẽ nhiễu — không báo lỗi.
    """
    kq = MH.kiem_dem_khung(800, 480, "ARGB8888", ram_noi_byte=324 * 1024,
                           ram_ngoai_byte=16 * 1024 * 1024)
    assert kq["can_byte"] == 1_536_000
    assert kq["vua_ram_noi"] is False
    assert kq["vua_ram_ngoai"] is True
    assert "SDRAM" in kq["note_vi"] or "ngoài" in kq["note_vi"], kq["note_vi"]


def test_dem_khung_VUA_thi_noi_la_vua():
    """Ca âm: 320×240 RGB565 = 153 600 byte, vừa 324 KB SRAM nội."""
    kq = MH.kiem_dem_khung(320, 240, "RGB565", ram_noi_byte=324 * 1024)
    assert kq["can_byte"] == 153_600
    assert kq["vua_ram_noi"] is True


def test_khong_biet_RAM_thi_KHONG_ket_luan():
    """Không biết RAM thì không nói "vừa" cũng không nói "không vừa".

    `False` ở đây sẽ bị đọc thành *"không vừa"*, và một cảnh báo sai làm người dùng đi sửa một
    thứ không hỏng. `None` = chưa đủ dữ kiện, đúng theo N2.
    """
    kq = MH.kiem_dem_khung(800, 480, "ARGB8888")
    assert kq["can_byte"] == 1_536_000
    assert kq["vua_ram_noi"] is None and kq["vua_ram_ngoai"] is None
    chu = kq["note_vi"].lower()
    assert "chưa kết luận" in chu, kq["note_vi"]
    # Và nó phải nói CẦN GÌ để kết luận, không chỉ nói là chưa biết.
    assert "ram.size" in chu, kq["note_vi"]


# =========================================================================== trên TÀI LIỆU THẬT
def test_tren_TAI_LIEU_THAT_cua_repo():
    """Đo trên `du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md` — tài liệu thật, không
    phải bản mẫu. Nó là lý do năng lực này đọc được gì mà không cần tải tệp từ ngoài.
    """
    p = GOC / "du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md"
    if not p.is_file():
        pytest.skip("không có tài liệu kiến trúc trong repo")
    hs = MH.ho_so_tu_chu(p.read_text("utf-8"))
    assert hs.hop_le is True
    assert (hs.rong, hs.cao) == (800, 480), (hs.rong, hs.cao)
    assert hs.he_mau in ("ARGB8888", "RGB565"), hs.he_mau
    assert hs.driver.upper() == "OTM8009A", hs.driver
    assert "DSI" in hs.bus.upper(), hs.bus
    assert hs.inch == 4.0, hs.inch


def test_moi_truong_cua_ho_so_mang_theo_TRICH_DAN():
    """Mỗi trường của hồ sơ phải nói nó đọc được ở đâu — N1.

    Một hồ sơ không có trích dẫn thì không phân biệt được với một hồ sơ tôi tự gõ ra, và cả
    năng lực thiết kế UI này đứng trên nó.
    """
    chu = "Màn hình LCD 4 inch 800x480\nHệ màu ARGB8888\nDriver OTM8009A qua MIPI-DSI"
    hs = MH.ho_so_tu_chu(chu)
    for khoa in ("lcd.width", "lcd.height", "lcd.format", "lcd.driver", "lcd.inch"):
        assert khoa in hs.nguon, f"{khoa} không có trích dẫn: {sorted(hs.nguon)}"
        assert hs.nguon[khoa].strip(), khoa
        # Trích dẫn phải là NGUYÊN VĂN có trong tài liệu, không phải câu tôi soạn lại.
        assert hs.nguon[khoa] in chu, (khoa, hs.nguon[khoa])


# ============ trích dẫn phải CHỨNG MINH điều nó khai (đo trên tài liệu thật)
def test_trich_dan_phai_la_dong_NOI_VE_MAN_HINH():
    """Một dòng có chữ `ARGB8888` chưa chắc nói về màn hình.

    Đo được trên `tai-lieu-kien-truc-c4.md` của repo: khớp `ARGB8888` **đầu tiên** nằm ở dòng
    nói về *ảnh logo trong firmware* (`Dữ liệu hình ảnh logo_ptit (ARGB8888…)`) — định dạng của
    một **tấm bitmap**, không phải định dạng bộ đệm khung của panel. Dòng đúng nằm sau:
    `FrameBuffer đồ hoạ LCD 800x480 (ARGB8888 / RGB565)`.

    Hai dòng ấy cho **cùng một giá trị**, nên bản đầu của tôi "đúng đáp án mà sai bằng chứng" —
    ca tệ nhất, vì nó không có biểu hiện nào để ai phát hiện. Nếu tấm bitmap là `RGB565` mà
    panel là `ARGB8888` thì hồ sơ sẽ sai, và mọi phép tính bộ đệm khung sai theo.
    """
    chu = ("Dữ liệu hình ảnh logo_ptit (ARGB8888) nằm trong ảnh firmware\n"
           "FrameBuffer đồ hoạ LCD 800x480 (RGB565)\n")
    hs = MH.ho_so_tu_chu(chu)
    assert hs.he_mau == "RGB565", hs.he_mau
    assert "LCD" in hs.nguon["lcd.format"], hs.nguon["lcd.format"]
    assert "logo_ptit" not in hs.nguon["lcd.format"]


def test_khong_co_dong_nao_NOI_VE_MAN_HINH_thi_truong_ay_THIEU():
    """Giá trị chỉ xuất hiện ở dòng không nói về màn hình → coi như tài liệu KHÔNG nói.

    Thà thiếu một trường và nói ra, hơn là điền một trường bằng một bằng chứng không đứng
    được. Hồ sơ này là thứ mọi toạ độ của bản thiết kế dựa vào.
    """
    hs = MH.ho_so_tu_chu("Nén ảnh tài sản sang ARGB8888 trước khi nhúng vào firmware\n"
                         "Panel LCD 800x480\n")
    assert (hs.rong, hs.cao) == (800, 480)
    assert hs.he_mau == "", hs.he_mau
    assert "lcd.format" in hs.thieu
    assert hs.hop_le is False


def test_tren_tai_lieu_THAT_trich_dan_cua_he_mau_noi_ve_man_hinh():
    """Và đo lại trên chính tài liệu thật: trích dẫn của `lcd.format` phải nói về màn hình."""
    p = GOC / "du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md"
    if not p.is_file():
        pytest.skip("không có tài liệu kiến trúc trong repo")
    hs = MH.ho_so_tu_chu(p.read_text("utf-8"))
    tr = hs.nguon.get("lcd.format", "")
    assert tr, hs.thieu
    assert "logo_ptit" not in tr, tr
    assert MH._RE_VE_MAN_HINH.search(tr), tr


def test_dong_goi_ten_TAM_ANH_van_bi_loai_du_da_noi_nhom_tu_he_mau():
    """Nới cửa cho nhóm từ `hệ màu` KHÔNG được nới cho dòng gọi tên một tấm ảnh.

    Đây là phép kiểm gộp của hai lớp: nhóm từ thứ hai (`hệ màu`, `pixel format`) được thêm vào
    vì cửa chỉ-xét-một-dòng quá chặt cho cách tài liệu thật viết. Ca này canh rằng việc nới ấy
    không mở lại đúng cái lỗ nó vừa vá — dòng `logo_ptit (ARGB8888)` gọi tên một **tấm ảnh**,
    không gọi tên một **trường cấu hình của panel**.
    """
    chu = ("Dữ liệu hình ảnh logo_ptit (ARGB8888) nhúng trong firmware\n"
           "Hệ màu RGB565\n")
    hs = MH.ho_so_tu_chu(chu)
    assert hs.he_mau == "RGB565", hs.he_mau
    assert "logo_ptit" not in hs.nguon.get("lcd.format", ""), hs.nguon


# ============ bốn lỗ mà tập phép phá chỉ ra (lượt đầu 61/67)
def test_cua_DON_VI_sau_cap_so_la_lop_chan_DUY_NHAT_o_ca_nay():
    """`100 x 80 mm` phải bị loại, và ở đây **chỉ** cửa đơn vị loại được nó.

    Bản mẫu trước của tôi dùng `60 x 40 mm` — hai số ấy đều **dưới** `PX_TOI_THIEU`, nên cửa
    ngưỡng pixel đã loại chúng rồi và tháo cửa đơn vị đi không đổi gì. Hai lớp chặn độc lập
    thì mỗi lớp cần một ca kiểm chạm tới ĐÚNG nó — không thì một lớp đang được lớp kia che.
    """
    assert MH.doc_do_phan_giai("board size 100 x 80 mm") == []
    assert MH.doc_do_phan_giai("khung nhom 240x160 cm") == []
    # Và cùng cặp số ấy KHÔNG có đơn vị đứng sau thì vẫn đọc được.
    assert MH.doc_do_phan_giai("panel 100x80") == [(100, 80)]


def test_cua_NHAN_sau_cap_so_la_lop_chan_DUY_NHAT_o_ca_nay():
    """`1024x256 words` phải bị loại — cùng lý do, và cùng chỗ bản mẫu trước che mất."""
    assert MH.doc_do_phan_giai("stack 1024x256 words") == []
    assert MH.doc_do_phan_giai("buffer 512x128 bytes") == []
    assert MH.doc_do_phan_giai("panel 1024x256") == [(1024, 256)]


def test_do_phan_giai_lay_tu_dong_NOI_VE_MAN_HINH_khong_lay_khop_dau():
    """Một tấm ảnh `128x128` trong firmware KHÔNG phải độ phân giải panel.

    Bản mẫu trước chỉ có một cặp số trong cả đoạn, nên phép phá "lấy khớp đầu tiên" không đổi
    được gì — lại là một tập **một phần tử**. Hậu quả thật của lỗi này rất đắt: mọi toạ độ của
    bản thiết kế sẽ nằm trong khung 128×128, và bản vẽ gần như trống.
    """
    chu = ("Du lieu hinh anh logo_ptit 128x128 nhung trong firmware\n"
           "Man hinh LCD 800x480 RGB565\n")
    hs = MH.ho_so_tu_chu(chu)
    assert (hs.rong, hs.cao) == (800, 480), (hs.rong, hs.cao)
    assert "logo_ptit" not in hs.nguon["lcd.width"], hs.nguon["lcd.width"]
