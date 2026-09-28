# -*- coding: utf-8 -*-
"""Thư viện khối `block@semver` — EIDE-HIER-45 §5. Ca HIER09, HIER10.

Hai điều bộ này canh, và cả hai đều là chỗ dễ nói dối:

**1. Số dẫn xuất phải có nguồn.** Một khối LDO đặt với `Vout=3,3 V` sinh ra hai điện trở chia
áp *tính được*. Con số tính ra **trông luôn có vẻ đúng** — nó có đơn vị, có mấy chữ số thập
phân, và không ai hỏi nó ở đâu ra. Nên luật ở đây là: thiếu nguồn cho một tham số thì **không
sinh lá nào**, chứ không sinh lá với con số đó.

**2. Khép kín.** Một khối có net chạm ra ngoài mà không qua Port thì đem sang dự án khác sẽ im
lặng hở — vẫn đặt được, vẫn vẽ được, chỉ sai khi hàn.
"""

from __future__ import annotations

import json

import pytest

from eide.knowledge import cay as C
from eide.knowledge import khoi_thu_vien as KTV
from eide.store import Store


# --------------------------------------------------------------------------- dàn dựng
LDO = {
    "ten": "LDO-3V3", "phien_ban": "1.2.0",
    "mo_ta": "Hạ 5 V xuống 3,3 V bằng AMS1117-ADJ, chia áp hồi tiếp",
    "port": [{"ten": "VIN", "huong": "power_in"},
             {"ten": "VOUT", "huong": "power_out"},
             {"ten": "GND", "huong": "power_in"}],
    "params": [{"ten": "vout", "don_vi": "V"},
               {"ten": "vref", "don_vi": "V", "mac_dinh": 1.25},
               {"ten": "r1", "don_vi": "Ω", "mac_dinh": 1000.0},
               {"ten": "r2", "don_vi": "Ω", "cong_thuc": "chia_ap_r2"}],
    "la": [{"ref": "U9", "ten": "AMS1117-ADJ", "gia_tri": "AMS1117-ADJ"},
           {"ref": "R8", "ten": "R", "gia_tri": "{r1}"},
           {"ref": "R9", "ten": "R", "gia_tri": "{r2}"}],
    "net": [{"ten": "FB", "loai": "signal", "chan": ["U9.4", "R8.2", "R9.1"]}],
}


@pytest.fixture
def thu_vien(tmp_path):
    goc = tmp_path / "blocks"
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=goc)
    return goc


def _nut(s, nid, ten, *, loai, cha, kind=None, path, ref="", canon=None):
    c = dict(canon or {})
    if ref:
        c["ref"] = ref
    c.setdefault("ten", ten)
    s.ckm_dat_nut(node_id=nid, loai=loai, ten=ten, canonical=c)
    s.ckm_dat_cay(nid, parent_id=cha, kind=kind, path=path)
    return nid


def _port(s, module_id, ten, *, huong="passive", chan=None, path):
    pid = f"port:{path}.{ten}"
    s.ckm_dat_port(port_id=pid, module_id=module_id, ten=ten, huong=huong, chan=chan)
    return pid


@pytest.fixture
def bo(tmp_path) -> Store:
    """Bo có một khối `pwr` KHÉP KÍN: net cục bộ chỉ chạm lá bên trong và Port của khối."""
    s = Store(tmp_path / "k.sqlite")
    _nut(s, "module:/board", "Bo", loai="module", cha=None, kind="board", path="/board")
    _nut(s, "module:/board/pwr", "Nguồn", loai="module", cha="module:/board", kind="block",
         path="/board/pwr")
    _nut(s, "module:/board/mcu", "MCU", loai="module", cha="module:/board", kind="block",
         path="/board/mcu")
    _nut(s, "leaf:U3", "AMS1117", loai="linh_kien", cha="module:/board/pwr", kind="leaf",
         path="/board/pwr/U3", ref="U3", canon={"gia_tri": "AMS1117-3.3"})
    _nut(s, "leaf:C1", "10uF", loai="linh_kien", cha="module:/board/pwr", kind="leaf",
         path="/board/pwr/C1", ref="C1", canon={"gia_tri": "10 µF"})
    _nut(s, "leaf:U1", "ATmega328P", loai="linh_kien", cha="module:/board/mcu",
         kind="leaf", path="/board/mcu/U1", ref="U1")

    p_u3 = _port(s, "leaf:U3", "2", huong="power_out", chan="2", path="/board/pwr/U3")
    p_c1 = _port(s, "leaf:C1", "1", chan="1", path="/board/pwr/C1")
    p_u1 = _port(s, "leaf:U1", "7", huong="power_in", chan="7", path="/board/mcu/U1")
    p_pwr = _port(s, "module:/board/pwr", "VOUT", huong="power_out", path="/board/pwr")
    p_mcu = _port(s, "module:/board/mcu", "VDD", huong="power_in", path="/board/mcu")

    n3 = _nut(s, "net:/board.3V3", "3V3", loai="net", cha="module:/board",
              path="/board.3V3", canon={"ten": "3V3", "loai": "power"})
    s.ckm_noi(net_id=n3, port_id=p_pwr)
    s.ckm_noi(net_id=n3, port_id=p_mcu)
    ni = _nut(s, "net:/board/pwr.VOUT_I", "3V3", loai="net", cha="module:/board/pwr",
              path="/board/pwr.VOUT_I", canon={"ten": "3V3", "loai": "power"})
    s.ckm_noi(net_id=ni, port_id=p_pwr)
    s.ckm_noi(net_id=ni, port_id=p_u3)
    s.ckm_noi(net_id=ni, port_id=p_c1)
    nm = _nut(s, "net:/board/mcu.VDD_I", "3V3", loai="net", cha="module:/board/mcu",
              path="/board/mcu.VDD_I", canon={"ten": "3V3", "loai": "power"})
    s.ckm_noi(net_id=nm, port_id=p_mcu)
    s.ckm_noi(net_id=nm, port_id=p_u1)
    return s


# =========================================================================== 1. manifest
def test_manifest_hop_le(thu_vien):
    assert KTV.kiem_manifest(LDO) == []


def test_manifest_khong_co_Port_bi_tu_choi():
    d = {**LDO, "port": []}
    assert any("không ai nối được" in x for x in KTV.kiem_manifest(d))


def test_manifest_phien_ban_khong_semver_bi_tu_choi():
    assert any("semver" in x for x in KTV.kiem_manifest({**LDO, "phien_ban": "1.2"}))


def test_manifest_cong_thuc_LA_bi_tu_choi_kem_danh_sach_co_san():
    """Danh sách công thức ĐÓNG: manifest đến từ một tệp trên đĩa, có thể do người khác viết.
    `eval` trên nội dung tệp là thực thi mã của người lạ."""
    d = {**LDO, "params": [{"ten": "x", "cong_thuc": "os.system"}]}
    loi = KTV.kiem_manifest(d)
    assert any("công thức lạ" in x and "chia_ap_r2" in x for x in loi), loi


def test_khong_dung_eval_cho_cong_thuc():
    """Canh bằng mã, không bằng lời hứa: mọi công thức phải là một hàm Python đã khai."""
    import inspect

    from eide.knowledge import khoi_thu_vien as m

    nguon = inspect.getsource(m)
    assert "eval(" not in nguon and "exec(" not in nguon
    assert all(callable(v[0]) for v in KTV.CONG_THUC.values())


# =========================================================================== 2. ba tầng §5
def test_tra_khoi_uu_tien_DU_AN_truoc_nguoi_dung(tmp_path):
    """Khối trong dự án là khối người dùng đã sửa cho mạch NÀY, nên nó phải thắng bản chung.
    Ngược lại thì một lần sửa cục bộ sẽ bị một bản thư viện mới lặng lẽ ghi đè."""
    du_an, nguoi = tmp_path / "da", tmp_path / "nd"
    KTV.luu_khoi(KTV.Khoi.from_dict({**LDO, "mo_ta": "bản của dự án"}), goc=du_an)
    KTV.luu_khoi(KTV.Khoi.from_dict({**LDO, "mo_ta": "bản chung"}), goc=nguoi)
    k, cau = KTV.tra_khoi("LDO-3V3", du_an=du_an, nguoi_dung=nguoi)
    assert k is not None and k.mo_ta == "bản của dự án" and k.tang == "du_an"
    assert "dự án" in cau


def test_tra_khoi_khong_co_phien_ban_thi_lay_MOI_NHAT_va_NOI_RA(tmp_path):
    """Im lặng chọn hộ một phiên bản là chỗ dễ sai nhất của mọi hệ quản gói."""
    du_an, nguoi = tmp_path / "da", tmp_path / "nd"
    for pb in ("1.0.0", "1.10.0", "1.2.0"):
        KTV.luu_khoi(KTV.Khoi.from_dict({**LDO, "phien_ban": pb}), goc=du_an)
    k, cau = KTV.tra_khoi("LDO-3V3", du_an=du_an, nguoi_dung=nguoi)
    assert k.phien_ban == "1.10.0", "1.10.0 > 1.2.0 theo semver, không theo chữ"
    assert "bản mới nhất trong 3 bản" in cau


def test_tra_khoi_khong_co_thi_NOI_RO_tang_thu_ba_chua_co(tmp_path):
    """Một tầng rỗng không được im lặng thành "không có khối nào tồn tại"."""
    k, cau = KTV.tra_khoi("KHONG-CO", du_an=tmp_path / "a", nguoi_dung=tmp_path / "b")
    assert k is None
    assert "M4" in cau and "chưa có" in cau


def test_manifest_hong_khong_lam_chet_viec_liet_ke(tmp_path):
    goc = tmp_path / "blocks"
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=goc)
    (goc / "hong@1.0.0").mkdir(parents=True)
    (goc / "hong@1.0.0" / KTV.MANIFEST).write_text("{ rác", "utf-8")
    assert [k.ten for k in KTV.liet_ke(goc, tang="du_an")] == ["LDO-3V3"]


# =========================================================================== 3. instantiate §5
def test_HIER09_dat_khoi_tinh_dung_dien_tro_chia_ap(thu_vien):
    """Ca HIER09 — "Đặt khối thư viện LDO-3V3@1.2.0 với Vout=3,3: instantiate đúng lá"."""
    k = KTV.Khoi.from_dict(LDO)
    kq = KTV.dat_khoi(k, gia_tri={"vout": 3.3}, nguon={"vout": "anh nói: dùng 3,3 V"})
    assert kq.loi == [] and kq.thieu_nguon == []
    # R2 = R1 / (Vout/Vref − 1) = 1000 / (3,3/1,25 − 1) = 609,76 Ω
    assert abs(kq.dan_xuat["r2"].gia_tri - 609.756) < 0.01
    theo = {x["ref"]: x for x in kq.la}
    assert theo["R9"]["gia_tri"].startswith("609,7")
    assert theo["R8"]["gia_tri"] == "1000"


def test_HIER09_moi_so_dan_xuat_noi_duoc_NO_O_DAU_RA(thu_vien):
    """§5: "mọi số từ công thức có nguồn". Con số tính ra trông luôn có vẻ đúng — nó có đơn
    vị, có mấy chữ số thập phân, và không ai hỏi nó ở đâu ra."""
    kq = KTV.dat_khoi(KTV.Khoi.from_dict(LDO), gia_tri={"vout": 3.3},
                      nguon={"vout": "anh nói: dùng 3,3 V"})
    g = kq.dan_xuat["r2"]
    assert g.cong_thuc == "R2 = R1 / (Vout/Vref − 1)"
    assert g.tham_so == {"vout": 3.3, "vref": 1.25, "r1": 1000.0}
    assert g.nguon["vout"] == "anh nói: dùng 3,3 V"
    assert "mặc định của khối" in g.nguon["vref"]
    cau = g.cau_vi()
    assert "609,756 Ω" in cau and "tính bằng" in cau and "anh nói" in cau


def test_HIER09_THIEU_NGUON_thi_khong_sinh_la_nao(thu_vien):
    """Chốt chặn của bước này. Một điện trở tính từ con số không ai biết ở đâu ra là một điện
    trở sẽ được hàn lên bo thật."""
    kq = KTV.dat_khoi(KTV.Khoi.from_dict(LDO), gia_tri={"vout": 3.3})
    assert kq.la == [], "không có nguồn thì KHÔNG sinh lá"
    assert kq.thieu_nguon == ["vout"]
    assert any("chưa có nguồn" in x for x in kq.loi)


def test_dat_khoi_thieu_tham_so_thi_noi_thieu_cai_gi(thu_vien):
    kq = KTV.dat_khoi(KTV.Khoi.from_dict(LDO), gia_tri={}, nguon={})
    assert any("thiếu tham số vout" in x for x in kq.loi), kq.loi


def test_dat_khoi_cong_thuc_vo_nghia_thi_noi_ra_chu_khong_tra_NaN(thu_vien):
    """Vout ≤ Vref thì mạch chia áp không tồn tại. Trả một số vô nghĩa ở đây sẽ thành một
    điện trở âm trên BOM."""
    kq = KTV.dat_khoi(KTV.Khoi.from_dict(LDO), gia_tri={"vout": 1.0},
                      nguon={"vout": "anh nói"})
    assert kq.la == []
    assert any("phải lớn hơn Vref" in x for x in kq.loi), kq.loi


def test_ba_cong_thuc_tinh_dung():
    assert abs(KTV.CONG_THUC["pull_up"][0](3.3, 0.003) - 1100.0) < 1e-9
    assert abs(KTV.CONG_THUC["tu_loc"][0](0.1, 0.05, 100_000) - 2e-5) < 1e-12
    with pytest.raises(ValueError):
        KTV.CONG_THUC["pull_up"][0](3.3, 0)


# =========================================================================== 4. khép kín §5
def test_HIER10_khoi_khep_kin_thi_dong_goi_duoc(bo):
    kk = KTV.kiem_khep_kin(C.Cay.doc(bo), "module:/board/pwr")
    assert kk.kin, kk.ho
    assert kk.port == ["VOUT"] and set(kk.la) == {"U3", "C1"}


def test_HIER10_net_cham_ra_ngoai_KHONG_qua_Port_thi_tu_choi(bo):
    """Một khối không khép kín đem sang dự án khác sẽ im lặng hở: vẫn đặt được, vẫn vẽ được,
    chỉ sai khi hàn."""
    # net cục bộ của khối pwr chạm thẳng Port của lá U1 nằm trong khối mcu
    bo.ckm_noi(net_id="net:/board/pwr.VOUT_I", port_id="port:/board/mcu/U1.7")
    kk = KTV.kiem_khep_kin(C.Cay.doc(bo), "module:/board/pwr")
    assert not kk.kin
    assert any("ngoài khối" in x for x in kk.ho), kk.ho


def test_khoi_khong_co_linh_kien_thi_khong_dong_goi(bo):
    _nut(bo, "module:/board/rong", "Rỗng", loai="module", cha="module:/board",
         kind="block", path="/board/rong")
    _port(bo, "module:/board/rong", "X", huong="in", path="/board/rong")
    kk = KTV.kiem_khep_kin(C.Cay.doc(bo), "module:/board/rong")
    assert not kk.kin and any("không có linh kiện" in x for x in kk.ho)


def test_khoi_chua_khai_Port_thi_khong_dong_goi(bo):
    bo._db.execute("DELETE FROM ckm_port WHERE module_id='module:/board/pwr'")
    bo._db.commit()
    kk = KTV.kiem_khep_kin(C.Cay.doc(bo), "module:/board/pwr")
    assert not kk.kin and any("không ai nối vào được" in x for x in kk.ho)


def test_goi_tu_khoi_mang_theo_Port_la_net_va_BOM(bo):
    cay = C.Cay.doc(bo)
    k = KTV.goi_tu_khoi(cay, "module:/board/pwr", ten="NGUON-3V3", mo_ta="cụm nguồn")
    assert k.ma == "NGUON-3V3@1.0.0"
    assert [p["ten"] for p in k.port] == ["VOUT"]
    assert {x["ref"] for x in k.la} == {"U3", "C1"}
    assert {x["ref"] for x in k.bom} == {"U3", "C1"}
    assert KTV.kiem_manifest(k.to_dict()) == []


def test_luu_va_doc_lai_khoi_khong_mat_gi(tmp_path, bo):
    cay = C.Cay.doc(bo)
    k = KTV.goi_tu_khoi(cay, "module:/board/pwr", ten="NGUON-3V3")
    d = KTV.luu_khoi(k, goc=tmp_path / "b")
    lai = KTV.Khoi.from_dict(json.loads((d / KTV.MANIFEST).read_text("utf-8")))
    assert lai.to_dict() == k.to_dict()


# =========================================================================== 5. công cụ
def _agent_khoi(make_agent):
    from eide.loop import TurnContext

    a = make_agent([])
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}

    def goi(cong_cu, /, **kw):
        if "explain" in (a.registry.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", ex)
        ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger,
                          eide_md=a.eide_md, ids=a.ids, registry=a.registry,
                          emit=lambda c: None, history=a.history, run_id="run-1")
        return a.registry.run(cong_cu, kw, ctx)
    return a, goi


def test_khoi_list_rong_thi_KHONG_noi_la_khong_ton_tai(make_agent):
    a, goi = _agent_khoi(make_agent)
    r = goi("khoi.list")
    assert r.ok and r.data["so_khoi"] == 0
    assert "M4" in r.data["note_vi"] and "chưa có" in r.data["note_vi"]


def test_khoi_place_thieu_nguon_bi_tu_choi_va_chi_ro_tham_so_nao(make_agent):
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    r = goi("khoi.place", ma="LDO-3V3", khoi="MOD-PWR", tham_so={"vout": 3.3})
    assert not r.ok and r.error.code == "E8002"
    assert "vout" in r.error.hint_for_agent
    assert "hàn lên bo thật" in r.error.hint_for_agent


def test_khoi_place_du_nguon_thi_dat_duoc_va_ghi_block_semver(make_agent):
    """HIER-16 — snapshot/hộ chiếu ghi `block@semver` đã dùng."""
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    r = goi("khoi.place", ma="LDO-3V3@1.2.0", khoi="MOD-PWR", tham_so={"vout": 3.3},
            nguon={"vout": "anh nói: dùng 3,3 V"})
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_linh_kien"] == 3
    canon = a.store.get("MG-1")["canonical"]
    assert canon["khoi_thu_vien"]["MOD-PWR"]["ma"] == "LDO-3V3@1.2.0"
    assert "609,756" in r.data["note_vi"] and "anh nói" in r.data["note_vi"]
    # Fact dẫn xuất vào kho, mang theo công thức
    f = a.store.query_facts(subject="khoi:LDO-3V3@1.2.0", key="r2", limit=5)
    assert f and "cong_thuc" in json.loads(f[0]["source"])


def test_khoi_place_di_qua_cong_G_DESIGN(make_agent):
    """§5: "người duyệt (G-DESIGN) mới đặt vào cây". Đặt một khối mang theo linh kiện, giá trị
    và cả một cụm Fact vào mạch của người dùng."""
    a, _ = _agent_khoi(make_agent)
    assert a.registry.get("khoi.place").gate == "G-DESIGN"
    assert a.registry.get("khoi.upgrade").gate == "G-DESIGN"


def test_khoi_place_khong_co_khoi_thi_noi_dang_co_gi(make_agent):
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    r = goi("khoi.place", ma="KHONG-CO", khoi="M1")
    assert not r.ok and "LDO-3V3@1.2.0" in r.error.message_vi
    assert "khoi.extract" in r.error.alternatives


def test_khoi_extract_tu_choi_khoi_khong_khep_kin(make_agent):
    a, goi = _agent_khoi(make_agent)
    goi("ckm.module_set", ma="MOD-X", ten="X", muc_dich="chưa có gì")
    r = goi("khoi.extract", khoi="MOD-X", ten="THU-1")
    assert not r.ok and r.error.code == "E9002"
    assert "ckm.port_set" in r.error.alternatives


def test_khoi_upgrade_noi_ro_Port_co_doi_khong(make_agent):
    """§6 dòng cuối — nâng phiên bản là "đổi Port" nếu manifest Port đổi, là "nội bộ" nếu chỉ
    đổi bên trong. Đây là chỗ quyết định STALE lan tới đâu."""
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    KTV.luu_khoi(KTV.Khoi.from_dict({**LDO, "phien_ban": "1.3.0",
                                     "la": LDO["la"] + [{"ref": "C9", "ten": "C",
                                                         "gia_tri": "100 nF"}]}),
                 goc=a.config.paths.blocks)
    goi("khoi.place", ma="LDO-3V3@1.2.0", khoi="MOD-PWR", tham_so={"vout": 3.3},
        nguon={"vout": "anh nói"})
    r = goi("khoi.upgrade", khoi="MOD-PWR", ma="LDO-3V3@1.3.0")
    assert r.ok and r.data["doi_port"] is False
    assert "Port KHÔNG đổi" in r.data["note_vi"]

    KTV.luu_khoi(KTV.Khoi.from_dict({**LDO, "phien_ban": "2.0.0",
                                     "port": LDO["port"] + [{"ten": "EN", "huong": "in"}]}),
                 goc=a.config.paths.blocks)
    r = goi("khoi.upgrade", khoi="MOD-PWR", ma="LDO-3V3@2.0.0")
    assert r.ok and r.data["doi_port"] is True
    assert "lan STALE" in r.data["note_vi"]


def test_khoi_upgrade_khoi_khong_tu_thu_vien_thi_noi_thang(make_agent):
    a, goi = _agent_khoi(make_agent)
    goi("ckm.module_set", ma="MOD-TAY", ten="vẽ tay", muc_dich="x")
    r = goi("khoi.upgrade", khoi="MOD-TAY", ma="LDO-3V3@1.2.0")
    assert not r.ok and "không phải đặt từ thư viện" in r.error.message_vi


def test_khoi_extract_di_HET_duong_va_dat_lai_duoc_o_du_an_khac(make_agent, tmp_path):
    """Ca này đi hết vòng: dựng mạch → trích khối → lưu thư viện NGƯỜI DÙNG → đặt lại.

    Thêm sau khi 29 ca đầu xanh ngay lần chạy đầu. Đọc lại thì thấy chưa ca nào đi qua thân
    `khoi.extract` với một khối khép kín thật — chỉ có ca từ chối khối KHÔNG kín. Một bộ đo
    toàn màu xanh mà chưa chạm đường thành công là một bộ đo chưa nói gì về đường đó.
    """
    from eide.knowledge import ckm as K

    a, goi = _agent_khoi(make_agent)
    for so, ten in (("1", "IN"), ("2", "OUT"), ("3", "GND")):
        a.store.put_fact({"fact_id": f"f{so}", "subject": f"pin:AMS1117.{so}",
                          "key": "ten", "value": ten, "tier": "VANG", "origin": "extract",
                          "source": {"doc_id": "DS-AMS1117", "page": 4}, "explain": {}})
    assert goi("ckm.chip_add", chip="AMS1117", ref="U3").ok
    assert goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn", muc_dich="hạ 5 V xuống 3,3 V",
               linh_kien=["U3"]).ok
    assert goi("ckm.port_set", khoi="MOD-PWR", ten="VOUT", huong="power_out",
               rang_buoc={"i_max": "800 mA"}).ok
    assert goi("ckm.net_set", ten="3V3", loai="power", chan=[["U3", "2"]],
               noi_port=[["MOD-PWR", "VOUT"]]).ok

    r = goi("khoi.extract", khoi="MOD-PWR", ten="NGUON-3V3", mo_ta="cụm nguồn 3V3",
            dung_chung=False)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["ma"] == "NGUON-3V3@1.0.0"
    assert r.data["so_port"] == 1 and r.data["so_linh_kien"] >= 1
    assert r.data["so_fact"] >= 3, "Fact của lá phải đi theo khối (§5)"
    assert "khép kín" in r.data["note_vi"].lower()

    # Đặt lại khối vừa trích — đây là chỗ chứng minh gói dùng được, không chỉ ghi được.
    r2 = goi("khoi.place", ma="NGUON-3V3", khoi="MOD-PWR-2")
    assert r2.ok, getattr(r2.error, "message_vi", "")
    assert r2.data["block"] == "NGUON-3V3@1.0.0"
    canon = a.store.get("MG-1")["canonical"]
    assert canon["khoi_thu_vien"]["MOD-PWR-2"]["ma"] == "NGUON-3V3@1.0.0"


def test_khoi_extract_luu_vao_thu_vien_NGUOI_DUNG_khi_duoc_yeu_cau(make_agent, monkeypatch,
                                                                   tmp_path):
    """`dung_chung=true` phải ghi vào `~/.eide/blocks` — đó là điều làm khối dùng lại được ở
    dự án khác (§5 tầng 2)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    a, goi = _agent_khoi(make_agent)
    for so, ten in (("1", "IN"), ("2", "OUT")):
        a.store.put_fact({"fact_id": f"g{so}", "subject": f"pin:AMS1117.{so}", "key": "ten",
                          "value": ten, "tier": "VANG", "origin": "extract",
                          "source": {"doc_id": "DS", "page": 4}, "explain": {}})
    goi("ckm.chip_add", chip="AMS1117", ref="U3")
    goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn", muc_dich="x", linh_kien=["U3"])
    goi("ckm.port_set", khoi="MOD-PWR", ten="VOUT", huong="power_out")
    goi("ckm.net_set", ten="3V3", loai="power", chan=[["U3", "2"]],
        noi_port=[["MOD-PWR", "VOUT"]])
    r = goi("khoi.extract", khoi="MOD-PWR", ten="NGUON-CHUNG", dung_chung=True)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["tang"] == "nguoi_dung"
    assert (tmp_path / ".eide" / "blocks" / "NGUON-CHUNG@1.0.0" / KTV.MANIFEST).exists()
    assert "dự án khác dùng được" in r.data["note_vi"]


def test_dat_cung_mot_khoi_HAI_LAN_thi_ref_khong_trung(make_agent):
    """HIER-45 §2.2 mục 4: "ref linh kiện duy nhất toàn mạch". Hai con LDO trên một bo là
    chuyện thường — và lần đặt thứ hai phải được cấp ref mới, có nói ra ánh xạ.

    Ca này tìm ra một lỗi thật: lần đặt thứ hai làm `UNIQUE(path)` của kho nổ, tức công cụ
    chết bằng E5999 thay vì làm việc.
    """
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    ng = {"vout": "anh nói: dùng 3,3 V"}
    r1 = goi("khoi.place", ma="LDO-3V3", khoi="MOD-PWR-A", tham_so={"vout": 3.3}, nguon=ng)
    r2 = goi("khoi.place", ma="LDO-3V3", khoi="MOD-PWR-B", tham_so={"vout": 3.3}, nguon=ng)
    assert r1.ok and r2.ok, getattr(r2.error, "message_vi", "")
    assert r1.data["anh_xa_ref"] == {}, "lần đầu không phải đổi gì"
    assert set(r2.data["anh_xa_ref"]) == {"U9", "R8", "R9"}, r2.data["anh_xa_ref"]
    assert "Ref đổi để không trùng" in r2.data["note_vi"]

    # Tiền tố chữ phải được GIỮ: KiCad và người đọc BOM dùng nó để biết linh kiện loại gì.
    for cu, moi in r2.data["anh_xa_ref"].items():
        assert moi[0] == cu[0], f"{cu}→{moi} mất tiền tố"
    nl = a.store.get("netlist:CKM")["canonical"]["linh_kien"]
    refs = [x["ref"] for x in nl]
    assert len(refs) == len(set(refs)) == 6, refs


def test_HIER16_snapshot_ghi_block_semver_da_dung(make_agent):
    """Quay về một bản ưng ý mà không biết nó dựng trên khối thư viện phiên bản nào thì
    "khôi phục được" là một lời hứa suông — LDO-3V3@1.2.0 và @2.0.0 có thể khác cả tập Port."""
    a, goi = _agent_khoi(make_agent)
    KTV.luu_khoi(KTV.Khoi.from_dict(LDO), goc=a.config.paths.blocks)
    goi("khoi.place", ma="LDO-3V3@1.2.0", khoi="MOD-PWR", tham_so={"vout": 3.3},
        nguon={"vout": "anh nói"})
    s = a.history.tao_snapshot(ten="thu-mot", ghi_chu="trước khi đổi nguồn", boi="human")
    assert s.contents["khoi_thu_vien"] == {"MOD-PWR": "LDO-3V3@1.2.0"}
    assert s.chip is None or isinstance(s.chip, str)


# ============================== lượt dở phải mang theo NÓ ĐANG LÀM GÌ
def test_luot_do_khai_luon_cong_cu_da_goi(tmp_path):
    """Đo được trên phiên bo STM32F469: dòng `<inventory>` cũ chỉ in `run_id` và 70 ký tự đầu
    của câu người dùng. Mỗi lượt mới, tác tử lại tiêu 3–10 lời gọi cho `ledger.query` /
    `history.diff` chỉ để nhớ ra mình đang dở việc gì — có lượt hết sạch hạn mức 40 lời gọi
    **trước khi làm được việc nào**.

    Danh sách công cụ nó vừa gọi là câu trả lời rẻ nhất cho câu "lúc nãy tôi đang làm gì", và
    nó đã nằm sẵn trong sổ cái. Không đưa vào là bắt tác tử trả tiền hai lần cho cùng một
    thông tin.
    """
    from eide.protocol.ledger import Ledger
    from eide.store import inventory as INV
    from eide.store.db import Store

    led = Ledger(tmp_path / "ledger.jsonl")
    led.append("turn.start", {"run_id": "run-1"})
    led.append("ui_command", {"run_id": "run-1", "text": "sửa màn hình đen giúp tôi"})
    for t in ("target.screen", "fs.read", "fs.read", "fs.read", "fs.edit", "build.compile"):
        led.append("tool_use", {"run_id": "run-1", "tool": t})
    # Không có turn.end → lượt này dở.

    inv = INV.build(Store(tmp_path / "store"), ledger=led)
    assert inv.unfinished_run and inv.unfinished_run["run_id"] == "run-1"
    cc = inv.unfinished_run["cong_cu"]
    assert cc == ["target.screen", "fs.read ×3", "fs.edit", "build.compile"], cc

    ra = inv.render()
    assert "Lượt chạy dở: run-1" in ra
    assert "target.screen → fs.read ×3 → fs.edit → build.compile" in ra
    # Và nói thẳng hai việc: đừng đi đọc lại sổ cái, và hãy ghi chỗ dở vào EIDE.md.
    assert "Đừng đi đọc lại sổ cái" in ra and "EIDE.md" in ra


def test_luot_da_xong_thi_KHONG_bao_do(tmp_path):
    from eide.protocol.ledger import Ledger
    from eide.store import inventory as INV
    from eide.store.db import Store

    led = Ledger(tmp_path / "ledger.jsonl")
    led.append("turn.start", {"run_id": "run-1"})
    led.append("tool_use", {"run_id": "run-1", "tool": "fs.read"})
    led.append("turn.end", {"run_id": "run-1"})
    inv = INV.build(Store(tmp_path / "store"), ledger=led)
    assert inv.unfinished_run is None
    assert "Lượt chạy dở" not in inv.render()


def test_cong_cu_cua_luot_chi_giu_muoi_hai_cai_cuoi(tmp_path):
    """Chép cả sổ cái vào ngữ cảnh là đúng thứ bảng này sinh ra để khỏi phải làm."""
    from eide.protocol.ledger import Ledger
    from eide.store.inventory import SO_CONG_CU_NHO_LAI, _cong_cu_cua_luot

    led = Ledger(tmp_path / "ledger.jsonl")
    for i in range(40):
        led.append("tool_use", {"run_id": "run-1", "tool": f"cong_cu_{i}"})
    led.append("tool_use", {"run_id": "run-KHAC", "tool": "khong_tinh"})
    cc = _cong_cu_cua_luot(led, "run-1")
    assert len(cc) == SO_CONG_CU_NHO_LAI
    assert cc[-1] == "cong_cu_39" and "khong_tinh" not in cc
