# -*- coding: utf-8 -*-
"""ING-C — bảng → Fact thống nhất, và đối chiếu chéo nguồn.

EIDE-ING-43 §5.1–5.3. Ca ING09 (ô gộp, min/typ/max chung ô), ING12 (chuẩn hoá),
ING16 (hai phiên bản cùng khoá — TC011).
"""

from __future__ import annotations

import pytest

from eide.knowledge.compare import UU_TIEN_NGUON, doi_chieu_cheo
from eide.knowledge.docs import Trang, TaiLieu, trich_fact_ung_vien


def _bang(hang: list[list[str]], *, tieu_de: list[str] | None = None) -> TaiLieu:
    """Dựng một TaiLieu chỉ gồm các hàng bảng, như bộ đọc Office sinh ra."""
    cot = tieu_de or hang[0]
    dv = []
    for i, r in enumerate(hang[1:], 1):
        dv.append(Trang(i, " | ".join(r), nhan=f"Bảng 1, dòng {i}", o=r, cot=cot))
    return TaiLieu(doc_id="D1", ten="d.docx", duong_dan="d.docx", hash="h",
                   so_trang=len(dv), trang=dv, loai="docx", don_vi_trich_dan="mục")


def _theo_khoa(tl: TaiLieu) -> dict:
    return {u.khoa: u for u in trich_fact_ung_vien(tl, thuc_the="chip:X")}


# =========================================================================== ING09
def test_ING09_min_typ_max_chung_MOT_O_tach_dung():
    tl = _bang([["Parameter", "Value", "Unit"],
                ["VDD max", "2.7 / 3.3 / 5.5", "V"]])
    k = _theo_khoa(tl)
    assert k["vdd.min"].gia_tri == pytest.approx(2.7)
    assert k["vdd.typ"].gia_tri == pytest.approx(3.3)
    assert k["vdd.max"].gia_tri == pytest.approx(5.5)
    assert all(u.don_vi == "V" for u in k.values())


def test_ING09_dai_trong_mot_o():
    tl = _bang([["Parameter", "Value", "Unit"],
                ["Supply voltage", "2.7–5.5", "V"]])
    k = _theo_khoa(tl)
    assert k["vdd.min"].gia_tri == pytest.approx(2.7)
    assert k["vdd.max"].gia_tri == pytest.approx(5.5)


def test_ING09_o_ghi_TBD_KHONG_thanh_Fact():
    """Ô "chưa có số" là một thông tin, nhưng nó không phải một con số."""
    tl = _bang([["Parameter", "Min", "Max", "Unit"],
                ["VDD max", "2.7", "TBD", "V"]])
    k = _theo_khoa(tl)
    assert "vdd.min" in k and k["vdd.min"].gia_tri == pytest.approx(2.7)
    assert "vdd.max" not in k, "TBD không được biến thành một giá trị"


def test_ING09_don_vi_trong_TIEU_DE_COT_duoc_ap_dung():
    tl = _bang([["Parameter", "Max", "Unit"],
                ["Supply current", "470", "mA"]])
    k = _theo_khoa(tl)
    assert k["icc.max"].gia_tri == pytest.approx(0.47)
    assert k["icc.max"].don_vi == "A"


def test_ING09_ky_hieu_ky_thuat_trong_o_bang():
    tl = _bang([["Parameter", "Typ", "Unit"],
                ["Pull-up", "4R7", "Ω"]])
    k = _theo_khoa(tl)
    assert k["i2c.pullup.typ"].gia_tri == pytest.approx(4.7)


def test_ING09_dieu_kien_tu_cot_Conditions_di_theo_Fact():
    tl = _bang([["Parameter", "Conditions", "Min", "Unit"],
                ["VIH", "VDD = 5V", "3.5", "V"]])
    k = _theo_khoa(tl)
    assert k["vih.min"].dieu_kien.get("vdd") == "5V"


def test_ING09_nguyen_van_giu_de_nguoi_doi_chieu():
    tl = _bang([["Parameter", "Max", "Unit"], ["VDD max", "5.5", "V"]])
    k = _theo_khoa(tl)
    assert k["vdd.max"].nguyen_van == "5.5"


def test_bang_khong_co_ten_thong_so_thi_khong_bia_Fact():
    tl = _bang([["Parameter", "Max", "Unit"], ["Màu vỏ", "3", "cái"]])
    assert trich_fact_ung_vien(tl, thuc_the="chip:X") == []


# =========================================================================== ING16
def _fact(fid, key, val, unit="V", *, doc="DS", ver="", origin="extract",
          errata=False, tier="BAC"):
    return {"fact_id": fid, "subject": "chip:X", "key": key, "value": val,
            "unit": unit, "tier": tier, "origin": origin,
            "source": {"doc_id": doc, "version": ver, "errata": errata},
            "explain": {}}


def test_ING16_hai_ban_khac_nhau_thi_HIEN_RA(tmp_path):
    lech = doi_chieu_cheo([
        _fact("f1", "vdd.max", 5.5, ver="rev A"),
        _fact("f2", "vdd.max", 6.0, ver=""),
    ])
    assert len(lech) == 1
    d = lech[0]
    assert d["khoa"] == "vdd.max" and d["so_nguon"] == 2
    assert d["can_nguoi_chon"] and "ĐỪNG tự chọn" in d["note_vi"]


def test_ING16_cung_gia_tri_khac_cach_viet_thi_KHONG_bao_lech():
    lech = doi_chieu_cheo([
        _fact("f1", "vdd.max", 5.5, unit="V"),
        _fact("f2", "vdd.max", 5500, unit="mV"),
    ])
    assert lech == [], "5,5 V và 5500 mV là cùng một số"


def test_ING16_errata_duoc_de_xuat_truoc_datasheet():
    lech = doi_chieu_cheo([
        _fact("f_ds", "vdd.max", 6.0, ver="rev A"),
        _fact("f_er", "vdd.max", 5.5, doc="ERRATA-01", errata=True),
    ])
    assert lech[0]["de_xuat"] == "f_er"
    assert "errata" in lech[0]["vi_sao"].lower()


def test_ING16_cau_hinh_va_ma_xep_SAU_tai_lieu():
    """`.ld` nói dự án ĐANG đặt gì; nó không nói chip chịu được gì."""
    lech = doi_chieu_cheo([
        _fact("f_cfg", "flash.size", 65536, unit="B", origin="config"),
        _fact("f_ds", "flash.size", 32768, unit="B", ver="rev B"),
    ])
    assert lech[0]["de_xuat"] == "f_ds"
    assert UU_TIEN_NGUON.index("config") > UU_TIEN_NGUON.index("datasheet_moi")


def test_ING16_mot_nguon_thi_khong_co_gi_de_doi_chieu():
    assert doi_chieu_cheo([_fact("f1", "vdd.max", 5.5)]) == []


def test_ING16_de_xuat_luon_kem_LY_DO():
    lech = doi_chieu_cheo([_fact("f1", "vdd.max", 5.5, ver="B"),
                           _fact("f2", "vdd.max", 6.0)])
    assert lech[0]["vi_sao"], "đề xuất mà không nói vì sao thì người không cãi lại được"
    assert all(b.get("nguon") for b in lech[0]["cac_ban"])


# =========================================================================== qua công cụ
def test_fact_cross_check_qua_cong_cu(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    for f in (_fact("f1", "vdd.max", 5.5, ver="rev A"),
              _fact("f2", "vdd.max", 6.0)):
        agent.store.put_fact(f)
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("fact.cross_check", {}, ctx)
    assert r.ok and r.data["so_lech"] == 1
    assert "Đừng tự chọn" in r.data["note_vi"]


def test_khong_lech_thi_khong_bao_dong(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    agent.store.put_fact(_fact("f1", "vdd.max", 5.5))
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("fact.cross_check", {}, ctx)
    assert r.ok and r.data["so_lech"] == 0 and r.data["note_vi"] == ""
