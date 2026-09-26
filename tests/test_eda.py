# -*- coding: utf-8 -*-
"""EDA — netlist, sơ đồ, BOM. EIDE-ING-43 §4.4, ING-09. Ca ING06, ING07, TC062.

Ô đáng giá nhất ở đây là đối chiếu BOM ↔ sơ đồ. Ba loại lệch, và loại thứ ba tệ nhất:
mạch hàn xong **chạy** nhưng sai, nên không ai nghi ngờ nó.
"""

from __future__ import annotations

import pytest

from eide.knowledge.eda import (DongBom, doc_bom_csv, doc_kicad_sch, doc_netlist,
                                doc_sexp, doi_chieu_bom_netlist)

_NET = """(export (version D)
  (components
    (comp (ref R5) (value 4k7) (footprint R_0603))
    (comp (ref C4) (value 100nF) (footprint C_0402))
    (comp (ref U1) (value ATmega328P) (datasheet "http://x/ds.pdf")))
  (nets
    (net (code 1) (name "+3V3") (node (ref U1) (pin 7)) (node (ref C4) (pin 1)))
    (net (code 2) (name "GND") (node (ref U1) (pin 8)) (node (ref C4) (pin 2)))
    (net (code 3) (name "SDA") (node (ref U1) (pin 27)) (node (ref R5) (pin 1)))
    (net (code 4) (name "CHUA_NOI") (node (ref R5) (pin 2)))))
"""


def test_doc_sexp_giu_chuoi_trong_ngoac_kep():
    cay = doc_sexp('(a "chuỗi có (ngoặc)" b)')
    assert cay[0] == ["a", "chuỗi có (ngoặc)", "b"]


def test_ING06_doc_netlist_thanh_cau_truc(tmp_path):
    p = tmp_path / "mach.net"
    p.write_text(_NET, "utf-8")
    m, vi = doc_netlist(p)
    assert m is not None, vi
    assert {l.ref for l in m.linh_kien} == {"R5", "C4", "U1"}
    assert m.theo_ref["R5"].gia_tri == "4k7"
    assert m.theo_ref["U1"].datasheet.endswith("ds.pdf")
    assert len(m.net) == 4
    sda = next(n for n in m.net if n.ten == "SDA")
    assert ("U1", "27") in sda.chan


def test_net_chi_noi_MOT_chan_bi_neu_ra(tmp_path):
    p = tmp_path / "mach.net"
    p.write_text(_NET, "utf-8")
    m, _ = doc_netlist(p)
    assert m.net_mot_chan() == ["CHUA_NOI"]


def test_tep_khong_phai_netlist_thi_noi_that(tmp_path):
    p = tmp_path / "la.net"
    p.write_text("(kicad_sch (version 20230121))\n", "utf-8")
    m, vi = doc_netlist(p)
    assert m is None and "không phải netlist KiCad" in vi


# =========================================================================== ING07
_SCH = """(kicad_sch (version 20230121) (generator eeschema)
  (symbol (lib_id "Device:R")
    (property "Reference" "R5" (at 0 0 0))
    (property "Value" "4k7" (at 0 0 0)))
  (symbol (lib_id "Device:C")
    (property "Reference" "C4" (at 0 0 0))
    (property "Value" "100nF" (at 0 0 0)))
  (symbol (lib_id "power:GND")
    (property "Reference" "#PWR01" (at 0 0 0))
    (property "Value" "GND" (at 0 0 0)))
  (label "SDA" (at 10 10 0))
  (global_label "+3V3" (at 20 20 0)))
"""


def test_ING07_doc_kicad_sch_dung_netlist_noi_bo(tmp_path):
    p = tmp_path / "mach.kicad_sch"
    p.write_text(_SCH, "utf-8")
    m, vi = doc_kicad_sch(p)
    assert m is not None, vi
    assert {l.ref for l in m.linh_kien} == {"R5", "C4"}, "ký hiệu #PWR không phải linh kiện"
    assert {n.ten for n in m.net} == {"SDA", "+3V3"}


def test_ING07_noi_RO_gioi_han_thay_vi_hua_nhieu_hon(tmp_path):
    """Nối theo nhãn, không theo toạ độ dây — phải nói ra, không để người tưởng là đủ."""
    p = tmp_path / "mach.kicad_sch"
    p.write_text(_SCH, "utf-8")
    m, _ = doc_kicad_sch(p)
    assert m.canh_bao and "NHÃN" in m.canh_bao[0]
    assert "dây trần" in m.canh_bao[0] and ".net" in m.canh_bao[0]


# =========================================================================== TC062
def _mach_mau():
    from eide.knowledge.eda import LinhKien, Mach

    m = Mach(nguon="mach.net")
    m.linh_kien = [LinhKien("R5", "4k7"), LinhKien("C4", "100nF"),
                   LinhKien("U1", "ATmega328P")]
    return m


def test_TC062_thieu_linh_kien_trong_BOM():
    kq = doi_chieu_bom_netlist(
        [DongBom(["R5"], "4k7"), DongBom(["U1"], "ATmega328P")], _mach_mau())
    assert not kq["khop"] and kq["thieu_trong_bom"] == ["C4"]
    assert any("hàn xong sẽ thiếu" in d for d in kq["se_mat_vi"])


def test_TC062_thua_linh_kien_trong_BOM():
    kq = doi_chieu_bom_netlist(
        [DongBom(["R5"], "4k7"), DongBom(["C4"], "100nF"),
         DongBom(["U1"], "ATmega328P"), DongBom(["D9"], "LED")], _mach_mau())
    assert kq["thua_trong_bom"] == ["D9"]
    assert any("sơ đồ đã đổi" in d for d in kq["se_mat_vi"])


def test_TC062_GIA_TRI_KHAC_la_loai_te_nhat():
    """Mạch hàn xong CHẠY nhưng sai — không ai nghi ngờ nó."""
    kq = doi_chieu_bom_netlist(
        [DongBom(["R5"], "10k"), DongBom(["C4"], "100nF"),
         DongBom(["U1"], "ATmega328P")], _mach_mau())
    assert len(kq["gia_tri_khac"]) == 1
    k = kq["gia_tri_khac"][0]
    assert k["ref"] == "R5" and k["bom"] == "10k" and k["so_do"] == "4k7"
    assert any("CHẠY nhưng sai" in d for d in kq["se_mat_vi"])


def test_TC062_cung_gia_tri_khac_cach_viet_thi_KHONG_bao_lech():
    kq = doi_chieu_bom_netlist(
        [DongBom(["R5"], "4700"), DongBom(["C4"], "100nF"),
         DongBom(["U1"], "ATmega328P")], _mach_mau())
    assert kq["gia_tri_khac"] == [], "4k7 và 4700 là cùng một giá trị"


def test_TC062_khop_thi_noi_la_khop():
    kq = doi_chieu_bom_netlist(
        [DongBom(["R5"], "4k7"), DongBom(["C4"], "100nF"),
         DongBom(["U1"], "ATmega328P")], _mach_mau())
    assert kq["khop"] and kq["se_mat_vi"] == []
    assert "khớp nhau" in kq["note_vi"]


def test_ref_gop_trong_mot_dong_BOM():
    from eide.knowledge.eda import LinhKien, Mach

    m = Mach(nguon="x")
    m.linh_kien = [LinhKien("C1", "100nF"), LinhKien("C2", "100nF")]
    kq = doi_chieu_bom_netlist([DongBom(["C1", "C2"], "100nF", so_luong=2)], m)
    assert kq["khop"]


# =========================================================================== BOM csv
def test_doc_bom_do_tieu_de_mem_deo(tmp_path):
    p = tmp_path / "bom.csv"
    p.write_text("Designator;Value;Qty\nR5;4k7;1\nC4;100nF;1\n", "utf-8")
    ds, vi = doc_bom_csv(p)
    assert not vi and len(ds) == 2
    assert ds[0].ref == ["R5"] and ds[0].gia_tri == "4k7" and ds[0].so_luong == 1


def test_bom_khong_co_cot_ma_thi_KHONG_DOAN(tmp_path):
    """Đoán cột nào là cột mã linh kiện là cách nhanh nhất để so sai cả bảng."""
    p = tmp_path / "bom.csv"
    p.write_text("Cột A,Cột B\nx,y\n", "utf-8")
    ds, vi = doc_bom_csv(p)
    assert ds == [] and "không đoán cột nào" in vi.lower()


# =========================================================================== qua công cụ
def _ctx(agent, thay=None):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=(thay.append if thay is not None else (lambda c: None)),
                       history=agent.history, run_id="run-1")


_EX = {"summary": "đọc mạch", "why": "để kiểm", "sources": [], "diff_prev": "—",
       "next": "—", "confidence": "NGUOI"}


def test_eda_netlist_va_bom_check_qua_cong_cu(make_agent):
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "mach.net").write_text(_NET, "utf-8")
    (goc / "bom.csv").write_text("Ref,Value\nR5,10k\nU1,ATmega328P\n", "utf-8")

    thay: list = []
    ctx = _ctx(agent, thay)
    r = agent.registry.run("eda.netlist", {"path": "mach.net", "explain": _EX}, ctx)
    assert r.ok and r.data["so_linh_kien"] == 3
    assert r.data["net_mot_chan"] == ["CHUA_NOI"]
    assert "lỗi vẽ" in r.data["note_vi"]

    r2 = agent.registry.run("eda.bom_check",
                            {"bom": "bom.csv", "netlist": "netlist:mach.net"}, ctx)
    assert r2.ok and not r2.data["khop"]
    assert r2.data["thieu_trong_bom"] == ["C4"]
    assert r2.data["gia_tri_khac"][0]["ref"] == "R5"
    assert [c for c in thay if c.method == "notice"], "lệch phải hiện cho người"


def test_bom_check_doi_netlist_truoc(make_agent):
    agent = make_agent([])
    (agent.config.paths.project_root / "bom.csv").write_text("Ref\nR5\n", "utf-8")
    r = agent.registry.run("eda.bom_check", {"bom": "bom.csv", "netlist": "chua-co"},
                           _ctx(agent))
    assert not r.ok and "eda.netlist" in r.error.alternatives
