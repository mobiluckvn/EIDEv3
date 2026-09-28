# -*- coding: utf-8 -*-
"""Hai năng lực cần để đưa được một cái logo lên màn bo thật.

`code.vendor_fetch` — lấy MÃ NGUỒN của hãng về, nhiều tệp một lượt. Đo trên bo STM32F469: để
vẽ lên màn DSI cần khoảng 60–70 tệp (HAL + CMSIS + BSP + driver panel); sáu mươi lượt gọi
`doc.fetch` vượt ngân sách một lượt làm việc và bắt người dùng duyệt cổng sáu mươi lần.

`asset.image_to_c` — chip không có trình đọc PNG. Không có công cụ này thì tác tử chỉ còn hai
đường: bịa ra một mảng điểm ảnh, hoặc bảo người dùng tự đi làm.

Điều cả hai bộ đều canh: **hỏng một phần phải nói ra là hỏng một phần.** Tải 70 tệp mà 3 tệp
lỗi rồi báo "xong" là cách để lỗi hiện ra lúc liên kết, ở một chỗ không liên quan gì tới
nguyên nhân thật.
"""

from __future__ import annotations

import io

import pytest

from eide.knowledge import anh_sang_c as A
from eide.knowledge import sdk_hang as S


class MayChuGia:
    """Trả nội dung theo URL. URL không có trong bảng thì 404."""

    def __init__(self, bang: dict[str, bytes]):
        self.bang = bang
        self.da_goi: list[str] = []

    def __call__(self, url: str, *, timeout: float):
        self.da_goi.append(url)
        noi = next((v for k, v in self.bang.items() if url.endswith(k)), None)
        if noi is None:
            import urllib.error
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        may = self

        class Phien(io.BytesIO):
            headers = {"Content-Length": str(len(noi)), "Content-Type": "text/plain"}

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Phien(noi)


HAL = b"/* stm32f4xx_hal.c */\n#include \"stm32f4xx_hal.h\"\nvoid HAL_Init(void) {}\n"
HDR = b"#ifndef STM32F4XX_HAL_H\n#define STM32F4XX_HAL_H\n#endif\n"


# ===================================================================== lấy SDK
def test_lay_duoc_nhieu_tep_mot_luot(tmp_path):
    may = MayChuGia({"Src/stm32f4xx_hal.c": HAL, "Inc/stm32f4xx_hal.h": HDR})
    kq = S.lay_sdk("STMicroelectronics/stm32f4xx-hal-driver",
                   ["Src/stm32f4xx_hal.c", "Inc/stm32f4xx_hal.h"],
                   tmp_path, nhanh="master", mo_url=may)
    assert kq.so_dat == 2 and kq.tong_byte == len(HAL) + len(HDR)
    # Phẳng: cả hai nằm cùng một thư mục để trình biên dịch chỉ cần một -I.
    assert (tmp_path / "stm32f4xx_hal.c").read_bytes() == HAL
    assert (tmp_path / "stm32f4xx_hal.h").read_bytes() == HDR
    assert all("raw.githubusercontent.com/STMicroelectronics/stm32f4xx-hal-driver/master/"
               in u for u in may.da_goi)


def test_giu_cay_thu_muc_khi_phang_False(tmp_path):
    may = MayChuGia({"Src/stm32f4xx_hal.c": HAL})
    kq = S.lay_sdk("o/r", ["Src/stm32f4xx_hal.c"], tmp_path, phang=False, mo_url=may)
    assert kq.so_dat == 1
    assert (tmp_path / "Src" / "stm32f4xx_hal.c").exists()


def test_mot_tep_hong_KHONG_lam_ca_luot_thanh_cong_im_lang(tmp_path):
    """Thiếu một tệp nguồn thì lỗi hiện ra lúc liên kết, xa chỗ gây ra nó nhất."""
    may = MayChuGia({"Src/co.c": HAL})
    kq = S.lay_sdk("o/r", ["Src/co.c", "Src/khong-co.c"], tmp_path, mo_url=may)
    assert kq.so_dat == 1
    hong = [t for t in kq.tep if not t.dat]
    assert len(hong) == 1 and "404" in hong[0].vi_sao
    assert kq.to_dict()["so_hong"] == 1 and kq.to_dict()["hong"]


@pytest.mark.parametrize("duong", ["Doc/anh.png", "lib/libc.a", "Release_Notes.html.zip"])
def test_khong_lay_tep_khong_phai_ma_nguon(duong, tmp_path):
    may = MayChuGia({duong: b"x" * 50})
    kq = S.lay_sdk("o/r", [duong], tmp_path, mo_url=may)
    assert kq.so_dat == 0
    assert "đuôi không nằm trong danh sách" in kq.tep[0].vi_sao
    assert may.da_goi == [], "không được tải trước rồi mới loại"


def test_noi_dung_nhi_phan_thi_bo_di_khong_de_lai_trong_firmware(tmp_path):
    may = MayChuGia({"Src/a.c": b"\x7fELF\x02\x01" + bytes(range(1, 30)) * 10})
    kq = S.lay_sdk("o/r", ["Src/a.c"], tmp_path, mo_url=may)
    assert kq.so_dat == 0
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("duong,mong", [
    ("../../../etc/passwd", "passwd"),
    ("Src/../../x.c", "x.c"),
    ("a/b/c/stm32.c", "stm32.c"),
])
def test_khong_bao_gio_ghi_ra_ngoai_thu_muc_dich(duong, mong, tmp_path):
    assert S._ten_an_toan(duong, phang=True) == mong
    t = S._ten_an_toan(duong, phang=False)
    assert ".." not in t and not t.startswith("/")


@pytest.mark.parametrize("repo", ["", "khong-co-gach-cheo", "a/b/c", "o/r r"])
def test_ten_repo_sai_thi_tu_choi_truoc_khi_goi_mang(repo, tmp_path):
    may = MayChuGia({})
    kq = S.lay_sdk(repo, ["Src/a.c"], tmp_path, mo_url=may)
    assert kq.so_dat == 0 and "owner/name" in kq.vi_sao_khong_dat
    assert may.da_goi == []


def test_qua_nhieu_tep_thi_bao_chia_nho(tmp_path):
    kq = S.lay_sdk("o/r", [f"Src/t{i}.c" for i in range(S.TRAN_SO_TEP + 1)], tmp_path,
                   mo_url=MayChuGia({}))
    assert kq.so_dat == 0 and "vượt trần" in kq.vi_sao_khong_dat


# ===================================================================== ảnh → C
def _anh(tmp_path, rong=64, cao=32, trong_suot=False):
    from PIL import Image

    im = Image.new("RGBA" if trong_suot else "RGB", (rong, cao), (200, 30, 40))
    if trong_suot:
        im.putpixel((0, 0), (0, 0, 0, 0))
    p = tmp_path / "logo.png"
    im.save(p)
    return p


def test_sinh_dung_kich_thuoc_va_so_byte(tmp_path):
    kq = A.doi_anh(_anh(tmp_path, 64, 32), tmp_path / "ra", ten_bien="logo_ptit")
    assert kq.dat and kq.rong == 64 and kq.cao == 32
    assert kq.so_byte == 64 * 32 * 2                  # rgb565 = 2 byte/điểm
    h = (tmp_path / "ra" / kq.tep_h).read_text("utf-8")
    assert "LOGO_PTIT_WIDTH   64" in h and "LOGO_PTIT_HEIGHT  32" in h
    assert "extern const uint16_t logo_ptit_data[2048];" in h
    c = (tmp_path / "ra" / kq.tep_c).read_text("utf-8")
    assert c.count("0x") == 2048


def test_thu_nho_GIU_TI_LE_va_noi_ra(tmp_path):
    """Ép vào khung sai tỉ lệ thì logo méo, và méo là thứ nhìn thấy ngay."""
    kq = A.doi_anh(_anh(tmp_path, 600, 400), tmp_path / "ra", ten_bien="logo",
                   rong_toi_da=240, cao_toi_da=240)
    assert kq.dat and (kq.rong, kq.cao) == (240, 160)      # 600:400 = 3:2 giữ nguyên
    assert any("giữ tỉ lệ" in c for c in kq.canh_bao)


def test_anh_nho_hon_khung_thi_KHONG_phong_to(tmp_path):
    kq = A.doi_anh(_anh(tmp_path, 40, 20), tmp_path / "ra", ten_bien="logo",
                   rong_toi_da=400, cao_toi_da=400)
    assert (kq.rong, kq.cao) == (40, 20)


def test_mat_kenh_trong_suot_thi_phai_noi(tmp_path):
    kq = A.doi_anh(_anh(tmp_path, 32, 32, trong_suot=True), tmp_path / "ra",
                   ten_bien="logo", dinh_dang="rgb565")
    assert kq.dat
    assert any("trong suốt" in c and "argb8888" in c for c in kq.canh_bao)


def test_argb8888_giu_trong_suot_va_khong_canh_bao(tmp_path):
    kq = A.doi_anh(_anh(tmp_path, 8, 8, trong_suot=True), tmp_path / "ra",
                   ten_bien="logo", dinh_dang="argb8888")
    assert kq.dat and kq.so_byte == 8 * 8 * 4
    assert not any("trong suốt" in c for c in kq.canh_bao)
    c = (tmp_path / "ra" / kq.tep_c).read_text("utf-8")
    assert "0x00000000" in c                  # điểm trong suốt giữ nguyên alpha = 0


def test_qua_to_so_voi_FLASH_CON_LAI_thi_noi_TRUOC(tmp_path):
    """Nói trước, thay vì để trình liên kết báo `region FLASH overflowed` sau mười phút."""
    kq = A.doi_anh(_anh(tmp_path, 400, 400), tmp_path / "ra", ten_bien="logo",
                   flash_con_lai=100 * 1024)
    assert not kq.dat
    assert "Flash chỉ còn" in kq.vi_sao_khong_dat
    assert "rgb565" in kq.vi_sao_khong_dat or "Thu nhỏ" in kq.vi_sao_khong_dat
    assert not (tmp_path / "ra").exists() or not list((tmp_path / "ra").glob("*.c"))


@pytest.mark.parametrize("ten", ["", "2logo", "  ", "!!!"])
def test_ten_bien_khong_cuu_duoc_thi_tu_choi(ten, tmp_path):
    kq = A.doi_anh(_anh(tmp_path), tmp_path / "ra", ten_bien=ten)
    assert not kq.dat and "tên biến C" in kq.vi_sao_khong_dat


def test_ten_bien_lam_sach_duoc_thi_lam_NHUNG_PHAI_NOI(tmp_path):
    """Đổi tên mà không nói thì tác tử `#include` một tên khác tên nó vừa đặt."""
    kq = A.doi_anh(_anh(tmp_path), tmp_path / "ra", ten_bien="logo ptit!")
    assert kq.dat and kq.ten_bien == "logo_ptit"
    assert any("đã đổi thành" in c and "logo_ptit" in c for c in kq.canh_bao)
    assert (tmp_path / "ra" / "logo_ptit.h").exists()


def test_khong_co_tep_anh_thi_noi_ro(tmp_path):
    kq = A.doi_anh(tmp_path / "khong-co.png", tmp_path / "ra", ten_bien="logo")
    assert not kq.dat and "Không có tệp ảnh" in kq.vi_sao_khong_dat


def test_dinh_dang_la_thi_liet_ke_cai_dang_co(tmp_path):
    kq = A.doi_anh(_anh(tmp_path), tmp_path / "ra", ten_bien="logo", dinh_dang="rgb332")
    assert not kq.dat and "rgb565" in kq.vi_sao_khong_dat
