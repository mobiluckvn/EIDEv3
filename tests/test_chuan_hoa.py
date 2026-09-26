# -*- coding: utf-8 -*-
"""Chuẩn hoá đơn vị và ký hiệu — EIDE-ING-43 §5.2. Ca ING12.

Vì sao bộ này dày: mỗi dòng ở đây là một cách một con số đi sai vào một con linh kiện
người ta đi mua. `4R7` đọc thành 4,7 Ω hay 47 Ω là khác nhau mười lần; `100n` không có
đơn vị mà đoán bừa thành 100 nF trong khi tài liệu nói 100 nH là sai loại linh kiện.
"""

from __future__ import annotations

import pytest

from eide.knowledge.chuan_hoa import GiaTri, chuan_hoa, tach_dieu_kien


def gt(s: str, **kw) -> GiaTri:
    return chuan_hoa(s, **kw)


# =========================================================================== ING12 ký hiệu
@pytest.mark.parametrize("chu,val,dv", [
    ("4R7", 4.7, "Ω"),
    ("3V3", 3.3, "V"),
    ("5V0", 5.0, "V"),
    ("1A5", 1.5, "A"),
    ("2M2", 2.2e6, "Ω"),          # 2,2 MΩ trong ngữ cảnh điện trở
])
def test_ING12_ky_hieu_ky_thuat(chu, val, dv):
    g = gt(chu, ngu_canh="điện trở pull-up")
    assert g.gia_tri == pytest.approx(val), g.to_dict()
    assert g.don_vi == dv
    assert g.raw == chu, "raw phải giữ NGUYÊN VĂN để người đối chiếu với tài liệu"


def test_ING12_100n_can_ngu_canh_moi_doan_duoc_don_vi():
    # Có ngữ cảnh tụ → nF.
    g = gt("100n", ngu_canh="tụ lọc nguồn")
    assert g.gia_tri == pytest.approx(100e-9) and g.don_vi == "F"

    # KHÔNG có ngữ cảnh → không bịa. Một đơn vị sai tệ hơn không có đơn vị.
    g2 = gt("100n")
    assert g2.gia_tri is None and g2.don_vi == ""
    assert "không rõ đơn vị" in g2.co


def test_ING12_don_vi_lay_tu_COT_khi_o_chi_co_so():
    g = gt("5.5", don_vi_cot="V")
    assert g.gia_tri == 5.5 and g.don_vi == "V"

    # Tiền tố nằm trong tiêu đề cột: "mV" → hệ số 1e-3.
    g2 = gt("470", don_vi_cot="mV")
    assert g2.gia_tri == pytest.approx(0.47) and g2.don_vi == "V"


def test_so_tran_khong_co_cot_don_vi_thi_NOI_RA():
    g = gt("5.5")
    assert g.gia_tri == 5.5 and not g.don_vi
    assert "thiếu cột Đơn vị" in g.co


# =========================================================================== dải
@pytest.mark.parametrize("chu", ["2.7–5.5 V", "2,7 ~ 5,5 V", "2.7 to 5.5V",
                                 "2.7 .. 5.5 V", "2,7 đến 5,5 V"])
def test_ING12_dai_min_max(chu):
    g = gt(chu)
    assert g.la_dai and g.vmin == pytest.approx(2.7) and g.vmax == pytest.approx(5.5)
    assert g.don_vi == "V"


def test_dai_nhiet_do_am():
    g = gt("-40 to +85 °C")
    assert g.vmin == -40 and g.vmax == 85 and g.don_vi == "°C"


def test_min_typ_max_chung_MOT_O():
    g = gt("2.7 / 3.3 / 5.5 V")
    assert (g.vmin, g.vtyp, g.vmax) == (2.7, 3.3, 5.5) and g.don_vi == "V"


# =========================================================================== không có số
@pytest.mark.parametrize("chu,vi_sao", [
    ("—", "để trống"),
    ("N/A", "N/A"),
    ("TBD", "TBD"),
    ("Note 3", "chú thích"),
    ("", "ô trống"),
])
def test_ING12_khong_co_so_KHONG_duoc_thanh_0(chu, vi_sao):
    """Biến "chưa có số" thành 0 là cách nhanh nhất để mạch chạy sai mà không ai hiểu."""
    g = gt(chu)
    assert not g.co_so, f"{chu!r} không được có giá trị"
    assert g.gia_tri is None
    assert vi_sao.lower() in g.co.lower(), g.co


# =========================================================================== điều kiện
def test_ING12_dieu_kien_co_CAU_TRUC():
    """VIH ở 3,3 V và VIH ở 5 V là hai số khác nhau — gộp lại là tạo kết luận sai."""
    d = tach_dieu_kien("@ 100 kHz, VDD = 3.3 V")
    assert d["freq"] == "100 kHz" and d["vdd"] == "3.3 V"


def test_dieu_kien_tach_khoi_gia_tri():
    g = gt("2.4 V (VDD=5V)")
    assert g.gia_tri == 2.4 and g.don_vi == "V"
    assert g.dieu_kien.get("vdd") == "5V"


# =========================================================================== tiền tố SI
@pytest.mark.parametrize("chu,val,dv", [
    ("4.7 kΩ", 4700, "Ω"),
    ("4,7kohm", 4700, "Ω"),
    ("100 nF", 100e-9, "F"),
    ("1 MHz", 1e6, "Hz"),
    ("20 mA", 0.02, "A"),
    ("1.5 µs", 1.5e-6, "s"),
    ("8 MB", 8e6, "B"),
    ("25 °C", 25, "°C"),
])
def test_tien_to_SI(chu, val, dv):
    g = gt(chu)
    assert g.gia_tri == pytest.approx(val), g.to_dict()
    assert g.don_vi == dv


def test_M_hoa_va_m_thuong_KHAC_nhau():
    """`M` là mega, `m` là mili — nhầm là sai một tỉ lần."""
    assert gt("1 MHz").gia_tri == pytest.approx(1e6)
    assert gt("1 mHz").gia_tri == pytest.approx(1e-3)
    assert gt("20 mA").gia_tri == pytest.approx(0.02)
    assert gt("20 MA").gia_tri == pytest.approx(20e6)


# =========================================================================== dấu thập phân
def test_dau_phay_va_dau_cham_deu_doc_duoc():
    assert gt("3,3 V").gia_tri == pytest.approx(3.3)
    assert gt("3.3 V").gia_tri == pytest.approx(3.3)


def test_hien_cho_nguoi_viet_dung_dau_PHAY():
    assert gt("3.3 V").hien_vi() == "3,3 V"
    assert gt("2.7–5.5 V").hien_vi() == "2,7…5,5 V"
    assert "—" in gt("TBD").hien_vi()


# =========================================================================== không đoán bừa
def test_khong_doc_duoc_thi_NOI_THANG():
    g = gt("xem hình 4-2")
    assert not g.co_so and "không đọc được" in g.co


def test_doan_don_vi_chi_khi_CHAC_CHAN():
    from eide.knowledge.chuan_hoa import _doan_don_vi

    assert _doan_don_vi("tụ lọc 100n") == "F"
    assert _doan_don_vi("điện trở pull-up") == "Ω"
    assert _doan_don_vi("cuộn cảm") == "H"
    assert _doan_don_vi("một câu chẳng nói gì") == ""


def test_raw_LUON_con_du_doc_duoc_hay_khong():
    for s in ("4R7", "N/A", "xem hình", "2.7–5.5 V", ""):
        assert chuan_hoa(s).raw == s
