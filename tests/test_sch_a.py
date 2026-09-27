# -*- coding: utf-8 -*-
"""SCH-A — soạn SKiDL từ cây, đọc lại, so đẳng cấu. Ca SCH01–04, SCH14, SCH16, SCH18.

Điều bộ này canh, một câu: **phép kiểm đẳng cấu phải đi qua hai đường độc lập.**

Nếu `sch.netlist` viết `.net` từ cây rồi so với `flatten(cây)` thì nó so chính mình với
chính mình — luôn đạt, và một phép kiểm luôn đạt tệ hơn không có phép kiểm: nó tạo niềm tin
không có cơ sở. Nên vế thứ hai là **đọc lại tệp SKiDL đã sinh**, tức đi qua một hiện vật mà
mô hình có thể đã sửa. Ca `test_SCH14_*` là ca chứng minh phép kiểm có tác dụng.
"""

from __future__ import annotations

import pytest

from eide.knowledge import cay as C
from eide.sch import doc_skidl, so_dang_cau, soan_skidl, viet_net
from eide.store import Store


# --------------------------------------------------------------------------- dàn dựng
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
    """Mạch ba tầng: board → {pwr(U3), mcu(U1, xtal(Y1))}.

    Ba tầng vì HIER-45 §7 đòi "cây → cấu trúc gọi hàm 1-1": hai tầng không phân biệt được
    một hàm gọi hàm với một hàm gọi Part.
    """
    s = Store(tmp_path / "k.sqlite")
    _nut(s, "module:/board", "Bo", loai="module", cha=None, kind="board", path="/board")
    _nut(s, "module:/board/pwr", "Nguồn", loai="module", cha="module:/board", kind="block",
         path="/board/pwr")
    _nut(s, "module:/board/mcu", "MCU", loai="module", cha="module:/board", kind="block",
         path="/board/mcu")
    _nut(s, "module:/board/mcu/xtal", "Dao động", loai="module", cha="module:/board/mcu",
         kind="subblock", path="/board/mcu/xtal")
    _nut(s, "leaf:U3", "AMS1117", loai="linh_kien", cha="module:/board/pwr", kind="leaf",
         path="/board/pwr/U3", ref="U3", canon={"gia_tri": "AMS1117-3.3"})
    _nut(s, "leaf:U1", "ATmega328P", loai="linh_kien", cha="module:/board/mcu", kind="leaf",
         path="/board/mcu/U1", ref="U1")
    _nut(s, "leaf:Y1", "16 MHz", loai="linh_kien", cha="module:/board/mcu/xtal",
         kind="leaf", path="/board/mcu/xtal/Y1", ref="Y1", canon={"gia_tri": "16MHz"})

    p_u3 = _port(s, "leaf:U3", "2", huong="power_out", chan="2", path="/board/pwr/U3")
    p_u1v = _port(s, "leaf:U1", "7", huong="power_in", chan="7", path="/board/mcu/U1")
    p_u1x = _port(s, "leaf:U1", "9", chan="9", path="/board/mcu/U1")
    p_y1 = _port(s, "leaf:Y1", "1", chan="1", path="/board/mcu/xtal/Y1")

    p_pwr = _port(s, "module:/board/pwr", "VOUT", huong="power_out", path="/board/pwr")
    p_mcu = _port(s, "module:/board/mcu", "VDD", huong="power_in", path="/board/mcu")
    p_xtal = _port(s, "module:/board/mcu/xtal", "XI", huong="out", path="/board/mcu/xtal")

    n3 = _nut(s, "net:/board.3V3", "3V3", loai="net", cha="module:/board",
              path="/board.3V3", canon={"ten": "3V3", "loai": "power"})
    s.ckm_noi(net_id=n3, port_id=p_pwr)
    s.ckm_noi(net_id=n3, port_id=p_mcu)
    for khoi, port_len, chan_la, ten in (("pwr", p_pwr, p_u3, "VOUT_I"),
                                        ("mcu", p_mcu, p_u1v, "VDD_I")):
        nid = _nut(s, f"net:/board/{khoi}.{ten}", "3V3", loai="net",
                   cha=f"module:/board/{khoi}", path=f"/board/{khoi}.{ten}",
                   canon={"ten": "3V3", "loai": "power"})
        s.ckm_noi(net_id=nid, port_id=port_len)
        s.ckm_noi(net_id=nid, port_id=chan_la)

    nx = _nut(s, "net:/board/mcu.XTAL1", "XTAL1", loai="net", cha="module:/board/mcu",
              path="/board/mcu.XTAL1", canon={"ten": "XTAL1", "loai": "clock"})
    s.ckm_noi(net_id=nx, port_id=p_xtal)
    s.ckm_noi(net_id=nx, port_id=p_u1x)
    nxi = _nut(s, "net:/board/mcu/xtal.XI_I", "XTAL1", loai="net",
               cha="module:/board/mcu/xtal", path="/board/mcu/xtal.XI_I",
               canon={"ten": "XTAL1", "loai": "clock"})
    s.ckm_noi(net_id=nxi, port_id=p_xtal)
    s.ckm_noi(net_id=nxi, port_id=p_y1)
    return s


SYM = {"U1": {"lib": "MCU_Microchip_ATmega", "ten": "ATmega328P-PU"},
       "U3": {"lib": "Regulator_Linear", "ten": "AMS1117-3.3"},
       "Y1": {"lib": "Device", "ten": "Crystal"}}


# =========================================================================== 1. soạn
def test_SCH01_moi_khoi_mot_ham_va_cay_thanh_cau_truc_goi_1_1(bo):
    """HIER-45 §7 — "cây → cấu trúc gọi hàm 1-1"."""
    ng, cb = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert "def khoi_board_pwr(VOUT):" in ng
    assert "def khoi_board_mcu(VDD):" in ng
    assert "def khoi_board_mcu_xtal(XI):" in ng
    assert "def mach():" in ng
    assert cb == [], cb


def test_ham_con_duoc_dinh_nghia_TRUOC_ham_cha_goi_no(bo):
    """Python đọc từ trên xuống: hàm cha gọi hàm con chưa định nghĩa thì tệp chạy hỏng."""
    ng, _ = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert ng.index("def khoi_board_mcu_xtal") < ng.index("def khoi_board_mcu(")


def test_net_noi_vao_Port_KHONG_tao_bien_moi(bo):
    """Net cục bộ nối vào Port "lên cha" chính là tham số của hàm — `flatten` hợp nhất hai
    bên Port thành một net điện, nên tạo thêm một `Net()` ở đây là tách một net thành hai."""
    ng, _ = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    trong_ham = ng.split("def khoi_board_pwr(VOUT):")[1].split("def ")[0]
    assert "Net(" not in trong_ham, trong_ham
    assert "VOUT += U3" in trong_ham.replace('U3["2"]', "U3")


def test_SCH04_khong_bia_chan_chan_dung_deu_co_Port_tu_Fact(bo):
    """Chân dùng trong tệp chỉ là chân CÓ PORT, và Port của lá sinh từ Fact pinout — nên kỷ
    luật "không bịa chân" của bước CKM đi thẳng vào tệp SKiDL."""
    ng, _ = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert 'U1["7"]' in ng and 'U1["9"]' in ng
    assert 'U1["28"]' not in ng, "chân không có Port thì không được xuất hiện"


def test_SCH18_soan_hai_lan_ra_dung_mot_tep(bo):
    """SCH17/N3 — cùng cây ⇒ cùng tệp. Tệp đổi thứ tự dòng mỗi lần sinh làm mọi phép so
    phía sau vô nghĩa."""
    a, _ = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    b, _ = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert a == b and a.count("def ") == 4


def test_thieu_symbol_thi_NOI_RA_chu_khong_bia_lib(bo):
    ng, cb = soan_skidl(C.Cay.doc(bo))
    assert any("chưa có ký hiệu" in c for c in cb), cb
    assert '"?"' in ng, "phải thấy được là lib chưa biết"


def test_khoi_chua_khai_Port_thi_noi_ra(bo):
    _nut(bo, "module:/board/rf", "RF", loai="module", cha="module:/board", kind="block",
         path="/board/rf")
    _, cb = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert any("chưa khai Port nào" in c for c in cb), cb


def test_Port_chua_noi_thi_sinh_net_roi_va_NOI_RA_mach_dang_ho(bo):
    _port(bo, "module:/board/mcu", "ALERT", huong="in", path="/board/mcu")
    ng, cb = soan_skidl(C.Cay.doc(bo), symbol=SYM)
    assert any("mạch thì đang hở" in c for c in cb), cb
    assert "ALERT_chua_noi" in ng


# =========================================================================== 2. đọc lại
def test_doc_lai_tep_vua_soan_ra_dung_netlist(bo):
    """Vòng khép kín: soạn → đọc lại → so với `flatten`. Đây là phép kiểm của SCH02."""
    cay = C.Cay.doc(bo)
    ng, _ = soan_skidl(cay, symbol=SYM)
    m = doc_skidl(ng)
    assert m.loi_cu_phap == "" and m.khong_hieu == [], m.to_dict()
    assert set(m.part) == {"U1", "U3", "Y1"}
    kq = so_dang_cau(C.flatten(cay), m.net)
    assert kq.dat, kq.to_dict()


def test_doc_skidl_KHONG_chay_tep(bo):
    """Đọc bằng `ast`, không `exec`. Tệp là hiện vật mô hình có thể đã sửa — chạy nó là thực
    thi mã không kiểm soát."""
    m = doc_skidl('import os\nos.system("echo HONG > /tmp/eide-khong-duoc-chay")\n'
                  'def mach():\n    pass\n')
    import pathlib
    assert not pathlib.Path("/tmp/eide-khong-duoc-chay").exists()
    assert any("cấp ngoài cùng" in k for k in m.khong_hieu), m.khong_hieu


def test_doc_skidl_loi_cu_phap_thi_noi_dong_nao(bo):
    m = doc_skidl("def mach(:\n  pass\n")
    assert m.loi_cu_phap.startswith("dòng 1"), m.loi_cu_phap


def test_doc_skidl_khong_co_ham_mach_thi_noi_thang(bo):
    m = doc_skidl("x = 1\n")
    assert any("không phải do sch.compose sinh" in k for k in m.khong_hieu)


def test_doc_skidl_cau_lenh_la_KHONG_bi_bo_qua_im_lang(bo):
    """Một dòng bị bỏ qua im lặng là một net biến mất khỏi phép kiểm."""
    m = doc_skidl('def mach():\n    a = Net("A")\n    for i in range(3):\n        pass\n')
    assert m.khong_hieu and "câu lệnh lạ" in m.khong_hieu[0]


def test_doc_skidl_chan_tinh_toan_thi_khong_doc_bua(bo):
    m = doc_skidl('def mach():\n    a = Net("A")\n'
                  '    u = Part("l", "p", ref="U1")\n    a += u[1 + 1]\n')
    assert any("không đọc được" in k for k in m.khong_hieu), m.khong_hieu


# =========================================================================== 3. đẳng cấu
def test_SCH14_net_mo_hinh_BIA_bi_bat_va_dung(bo):
    """Ca quan trọng nhất: mô hình sửa tệp SKiDL, thêm một net không có trong bản đồ.

    Nếu phép kiểm so cây với chính nó thì ca này ĐẬU và một đường dây không ai quyết đi vào
    mạch. Vì vế thứ hai đọc từ tệp, nó bị bắt.
    """
    cay = C.Cay.doc(bo)
    ng, _ = soan_skidl(cay, symbol=SYM)
    # Sửa đúng như một mô hình sẽ sửa: chèn một net mới vào thân `mach()`.
    moc = "    khoi_board_pwr(n_3V3)"
    assert moc in ng, ng
    bia = ng.replace(moc, '    bia = Net("VBUS_BIA")\n'
                          '    u1_bia = Part("x", "y", ref="U1")\n'
                          '    bia += u1_bia["7"]\n' + moc)
    assert bia != ng, "phải sửa được tệp để ca này có nghĩa"
    m = doc_skidl(bia)
    kq = so_dang_cau(C.flatten(cay), m.net)
    assert not kq.dat
    assert "VBUS_BIA" in kq.net_them
    assert "KHÔNG có trong bản đồ" in kq.vi


def test_net_thieu_o_skidl_cung_bi_bat(bo):
    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    kq = so_dang_cau(phang, {k: v for k, v in phang.items() if k != "XTAL1"})
    assert not kq.dat and "XTAL1" in kq.net_thieu
    assert "thiếu" in kq.vi


def test_chan_lech_tren_cung_net_bi_bat(bo):
    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    doi = {k: list(v) for k, v in phang.items()}
    doi["3V3"] = [x for x in doi["3V3"] if not x.startswith("U1")]
    kq = so_dang_cau(phang, doi)
    assert not kq.dat and "3V3" in kq.chan_lech
    assert kq.chan_lech["3V3"]["thieu_o_skidl"] == ["U1.7"]


def test_net_rong_hai_ben_van_duoc_so(bo):
    """Net không nối gì là một cái tên vô nghĩa mà người cần thấy; bỏ qua nó thì một net bị
    mất hẳn khỏi tệp cũng không bị phát hiện."""
    kq = so_dang_cau({"TREO": []}, {})
    assert not kq.dat and "TREO" in kq.net_thieu


# =========================================================================== 4. viết .net
def test_viet_net_dung_dang_kicad_va_xac_dinh(bo):
    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    m = doc_skidl(soan_skidl(cay, symbol=SYM)[0])
    a = viet_net(phang, part=m.part, ten_mach="thu")
    assert a.startswith("(export") and '(tool "EIDE")' in a
    assert '(comp (ref "U1")' in a and '(node (ref "U1") (pin "7"))' in a
    assert a == viet_net(phang, part=m.part, ten_mach="thu")


def test_viet_net_KHONG_ghi_tstamp_bia(bo):
    """KiCad dùng `tstamps` để khớp linh kiện khi cập nhật PCB; một giá trị bịa làm lần cập
    nhật sau gán sai chân. Thiếu thì để KiCad tự sinh."""
    cay = C.Cay.doc(bo)
    a = viet_net(C.flatten(cay), part={"U1": {"lib": "x", "ten": "y", "value": "z"}})
    assert "tstamp" not in a


def test_viet_net_sap_chan_theo_SO(bo):
    a = viet_net({"X": ["U1.10", "U1.2"]}, part={})
    assert a.index('(pin "2")') < a.index('(pin "10")')


# =========================================================================== 5. ký hiệu §5
def test_ky_hieu_sinh_tu_Fact_ghi_ro_LAY_CHAN_TU_DAU(bo):
    """§5 gọi đây là "N1 áp vào ký hiệu": một ký hiệu không nói nó lấy chân từ đâu thì không
    khác gì một hình vẽ."""
    from eide.sch import kyhieu as KH

    ds, thieu = KH.anh_xa(C.Cay.doc(bo), nguon_fact={"U1": "DS-328P trang 13"})
    assert thieu == []
    assert ds["U1"].sinh_tu_fact and ds["U1"].nguon == "DS-328P trang 13"
    sym = KH.viet_kicad_sym(ds)
    assert "Sinh từ DS-328P trang 13 — EIDE" in sym
    assert '(pin power_in line' in sym, "kiểu chân suy từ hướng Port"


def test_ky_hieu_kieu_chan_chua_biet_thi_passive_chu_khong_doan(bo):
    """Đoán `input` cho một chân chưa rõ sẽ làm ERC của KiCad báo lỗi sai ở máy người khác."""
    from eide.sch import kyhieu as KH

    ds, _ = KH.anh_xa(C.Cay.doc(bo))
    y1 = ds["Y1"]
    assert [c["kieu"] for c in y1.chan] == ["passive"]


def test_thu_vien_lech_Fact_thi_KHONG_dung_im_lang(bo):
    """§5: "lệch → không dùng im lặng". Số chân khác nhau nghĩa là HAI CON CHIP khác nhau."""
    from eide.sch import kyhieu as KH

    tv = {"U1": {"lib": "MCU_X", "ten": "ATmega328P", "version": "8.0",
                 "chan": [{"so": "1"}, {"so": "2"}, {"so": "3"}]}}
    ds, _ = KH.anh_xa(C.Cay.doc(bo), thu_vien=tv)
    assert ds["U1"].sinh_tu_fact, "phải rơi về ký hiệu sinh"
    assert "chỉ khớp" in ds["U1"].canh_bao and "thiếu chân" in ds["U1"].canh_bao


def test_thu_vien_khop_thi_dung_va_ghi_phien_ban(bo):
    from eide.sch import kyhieu as KH

    tv = {"U1": {"lib": "MCU_X", "ten": "ATmega328P-PU", "version": "8.0",
                 "chan": [{"so": "7"}, {"so": "9"}]}}
    ds, _ = KH.anh_xa(C.Cay.doc(bo), thu_vien=tv)
    assert not ds["U1"].sinh_tu_fact
    assert ds["U1"].lib == "MCU_X" and "8.0" in ds["U1"].nguon


def test_la_khong_co_chan_thi_vao_danh_sach_THIEU_chu_khong_bia(bo):
    _nut(bo, "leaf:U9", "Chip lạ", loai="linh_kien", cha="module:/board", kind="leaf",
         path="/board/U9", ref="U9")
    from eide.sch import kyhieu as KH

    _, thieu = KH.anh_xa(C.Cay.doc(bo))
    assert thieu == ["U9"]


# =========================================================================== 6. cờ tính năng
def test_SCH16_co_TAT_thi_sch_khong_duoc_DANG_KY():
    """SCH-44 §2.1 lớp bảo vệ số 1: cờ tắt thì mô hình không THẤY, không chỉ bị giấu — và
    lược đồ tool không tăng một token nào."""
    from eide.config import Features
    from eide.tools import build_registry

    tat = build_registry(Features(schematic=False))
    assert [t for t in tat.all() if t.name.startswith("sch.")] == []
    assert all(n.startswith("sch.") for n in tat.bo_qua_vi_co), tat.bo_qua_vi_co
    bat = build_registry(Features(schematic=True))
    sch_bat = [t.name for t in bat.all() if t.name.startswith("sch.")]
    # KHÔNG chốt cứng con số: SCH-B/C/D còn thêm tool, và một ca đo đỏ vì lý do bình thường
    # sẽ bị sửa cho qua thay vì được đọc.
    assert len(sch_bat) >= 3
    assert len(bat.all()) == len(tat.all()) + len(sch_bat)


def test_co_khong_biet_thi_nghieng_ve_TAT():
    """`Registry(features=None)` — không biết cờ nào bật thì coi như tắt, đúng phía an toàn."""
    from eide.tools.registry import Registry, ToolSpec

    r = Registry(None)
    r.add(ToolSpec(name="sch.x", group="g", summary_vi="s", params={}, fn=lambda **k: None,
                   feature="schematic"))
    assert r.get("sch.x") is None


# =========================================================================== 7. công cụ
def _agent_sch(make_agent):
    """Tác tử với cờ sơ đồ BẬT — chỉ dùng trong bộ này."""
    from eide.config import Features
    from eide.loop import TurnContext
    from eide.tools import build_registry

    a = make_agent([])
    a.registry = build_registry(Features(schematic=True))
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}

    def goi(cong_cu, /, **kw):
        if "explain" in (a.registry.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", ex)
        ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger,
                          eide_md=a.eide_md, ids=a.ids, registry=a.registry,
                          emit=lambda c: None, history=a.history, run_id="run-1")
        return a.registry.run(cong_cu, kw, ctx)
    return a, goi, ex


def _dung_mach(a, goi):
    """Mạch nhỏ đủ để sinh sơ đồ: có hộ chiếu, khối, Port, net, chân từ Fact."""
    for so, ten, af in (("7", "VCC", ""), ("27", "PC4", "SDA, ADC4")):
        a.store.put_fact({"fact_id": f"f{so}", "subject": f"pin:ATmega328P.{so}",
                          "key": "ten", "value": ten, "tier": "VANG", "origin": "extract",
                          "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
        if af:
            a.store.put_fact({"fact_id": f"fa{so}", "subject": f"pin:ATmega328P.{so}",
                              "key": "af", "value": af, "tier": "VANG", "origin": "extract",
                              "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
    a.store.apply(artefact_id="DS-328P", type="doc", op="create", author="human",
                  explain={"summary": "ds"}, canonical={"ten": "datasheet"})
    goi("passport.pin", chip="ATmega328P", doc_ids=["DS-328P"])
    goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    goi("ckm.module_set", ma="MCU", ten="Vi điều khiển", muc_dich="chạy firmware",
        linh_kien=["U1"])
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="power_in")
    goi("ckm.net_set", ten="3V3", loai="power", chan=[["U1", "7"]],
        noi_port=[["MCU", "VDD"]])
    goi("ckm.build")


def test_compose_sinh_tep_va_ghi_changeset(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    r = goi("sch.symbols")
    assert r.ok, getattr(r.error, "message_vi", "")
    r = goi("sch.compose")
    assert r.ok, getattr(r.error, "message_vi", "")
    p = a.config.paths.project_root / "sch/mach_skidl.py"
    assert p.exists() and "def khoi_board_MCU" in p.read_text("utf-8")
    assert r.data["changeset"] and a.store.get("skidl:mach") is not None


def test_netlist_kiem_bang_cach_DOC_LAI_tep(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    goi("sch.compose")
    r = goi("sch.netlist")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["dang_cau"]["dat"] is True
    assert "ĐỌC LẠI" in r.data["note_vi"], "phải nói rõ phép kiểm đi qua đường nào"
    assert (a.config.paths.project_root / "sch/mach.net").exists()


def test_SCH14_netlist_tu_choi_khi_tep_bi_sua_them_net(make_agent):
    """Ca SCH14 qua công cụ: mô hình sửa tệp, thêm một net không có trong bản đồ."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    goi("sch.compose")
    p = a.config.paths.project_root / "sch/mach_skidl.py"
    ng = p.read_text("utf-8")
    p.write_text(ng.replace("    khoi_board_MCU(n_3V3)",
                            '    bia = Net("VBUS_BIA")\n'
                            '    ub = Part("x", "y", ref="U1")\n'
                            '    bia += ub["7"]\n'
                            "    khoi_board_MCU(n_3V3)"), "utf-8")
    r = goi("sch.netlist")
    assert not r.ok and r.error.code == "E8001"
    assert "VBUS_BIA" in r.error.details["net_them"]
    assert "Đừng sửa tệp cho khớp" in r.error.hint_for_agent


def test_compose_tu_choi_khi_ban_do_chua_du_tien_de(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    goi("ckm.module_set", ma="MCU", ten="x", muc_dich="y")
    r = goi("sch.compose")
    assert not r.ok and r.error.code in ("E8005", "E2001")


def test_compose_tu_choi_khi_cay_VI_PHAM_bat_bien(make_agent):
    """Sinh sơ đồ từ một cây lệch nghĩa là vẽ một mạch KHÁC mạch người vẽ."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    # Thêm một Port cho lá mà bảng chân KHÔNG có → E9004. Đặt SAU lần chiếu cuối: `chieu()`
    # dựng lại đồ thị từ hiện vật nên nó sẽ xoá chỗ hỏng này — và đó chính là điều ca đo cần,
    # vì nó buộc `sch.compose` phải TỰ TÍNH bất biến thay vì đọc kết quả chiếu trước.
    a.store.ckm_dat_port(port_id="port:/board/MCU/U1.99", module_id="chip:U1", ten="99",
                         huong="passive", chan="99")
    r = goi("sch.compose")
    assert not r.ok and r.error.code == "E8005"
    assert "mạch KHÁC" in r.error.message_vi


def test_netlist_chua_soan_thi_noi_goi_gi_truoc(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    r = goi("sch.netlist")
    assert not r.ok and "sch.compose" in (r.error.alternatives or [])


# =========================================================================== 8. SCH-09
def _ctx_stop(loi: list[str]):
    class C:
        assumptions: list = []
        assumptions_stated: list = []
        human_edits: list = []
        said_anything = True
        awaiting_human = False
        loi_da_noi = loi
    return C()


def test_SCH09_de_nghi_cai_KiCad_bi_CHAN_va_bat_noi_lai():
    """Ràng buộc về *thứ không được xuất hiện* không tự giữ được. Mô hình rất dễ "giúp" bằng
    câu "anh cài KiCad rồi mở tệp này" — đúng lúc nó tưởng đang hữu ích nhất.

    Cấm bằng một dòng trong hiến pháp là cấm KHÔNG ĐO ĐƯỢC: lời nhắc trôi đi sau vài lần
    nén, và không ai biết nó đã trôi.
    """
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx_stop(["Anh cài KiCad rồi mở tệp sch/mach.kicad_sch nhé."]))
    assert r.another_round and "khong_cai_kicad" in r.fired
    assert "không cài KiCad" in r.injection
    assert "sch.export" in r.injection, "phải chỉ đường ĐÚNG, không chỉ chặn"


def test_SCH09_bat_ca_cach_viet_khac_va_ca_kicad_cli():
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    bus = register_standard_hooks(HookBus())
    for cau in ("Chạy kicad-cli sch export svg là xong.",
                "You can install KiCad from the website.",
                "Anh tải KiCad bản 9 về nhé."):
        assert bus.stop(_ctx_stop([cau])).another_round, cau


def test_SCH09_noi_ve_KiCad_ma_khong_de_nghi_cai_thi_KHONG_bi_chan():
    """Chặn quá tay thì tác tử không nói được về định dạng KiCad — mà nó phải nói."""
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx_stop(["Đã ghi sch/mach.kicad_sch — mở được trong KiCad 8 hoặc 9 ở "
                            "máy có sẵn KiCad; ở đây tôi render SVG bằng bộ vẽ nội bộ."]))
    assert not r.another_round, r.injection


# =========================================================================== 9. suy giảm R3
def test_R3_chua_co_cay_thi_noi_thang_va_chi_ve_so_do_khoi(make_agent):
    """§6 mức R3: không sinh được thì trả về thứ đang có, KHÔNG trả một tệp nửa vời."""
    a, goi, _ = _agent_sch(make_agent)
    r = goi("sch.compose")
    assert not r.ok and r.error.code in ("E8005", "E2001")
    if r.error.code == "E8005":
        assert "mức R3" in r.error.message_vi
        assert "diagram.render" in r.error.alternatives


# =========================================================================== 10. bố cục §4
def test_SCH17_bo_cuc_XAC_DINH_chay_nam_lan_cung_toa_do(bo):
    """SCH17 đòi "cùng CKM chạy 5 lần: toạ độ giống hệt".

    Không phải chuyện gọn gàng: mọi phép so phía sau (uuid ổn định, diff bố cục, "người đã
    sửa gì") đều dựa trên việc cùng đầu vào cho cùng đầu ra.
    """
    from eide.sch import bo_cuc as BC

    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    ds = [BC.tinh_bo_cuc(cay, phang).to_dict() for _ in range(5)]
    assert all(x == ds[0] for x in ds)


def test_bo_cuc_moi_ky_hieu_dung_luoi_1_27(bo):
    from eide.sch import bo_cuc as BC

    bc = BC.tinh_bo_cuc(C.Cay.doc(bo), C.flatten(C.Cay.doc(bo)))
    for z in bc.o:
        assert abs(z.x / BC.LUOI - round(z.x / BC.LUOI)) < 1e-6, z
        assert abs(z.y / BC.LUOI - round(z.y / BC.LUOI)) < 1e-6, z


def test_bo_cuc_khong_ky_hieu_nao_chong_nhau(bo):
    from eide.sch import bo_cuc as BC

    bc = BC.tinh_bo_cuc(C.Cay.doc(bo), C.flatten(C.Cay.doc(bo)))
    assert bc.tieu_chi["cap_chong_nhau"] == 0, bc.tieu_chi["vi_pham"]


def test_bo_cuc_xep_khoi_theo_HUONG_PORT_khong_theo_ten(bo):
    """§4: nguồn vào bên trái, trung tâm ở giữa. Suy từ tên khối ("PWR") sẽ đúng trên mạch
    mẫu và sai trên mạch thật, vì tên khối do người đặt."""
    from eide.sch import bo_cuc as BC

    bc = BC.tinh_bo_cuc(C.Cay.doc(bo), C.flatten(C.Cay.doc(bo)))
    theo_khoi = {v.khoi: v.x for v in bc.vung}
    pwr = theo_khoi.get("module:/board/pwr")
    mcu = theo_khoi.get("module:/board/mcu")
    assert pwr is not None and mcu is not None, theo_khoi
    assert pwr < mcu, "khối chỉ có power_out phải nằm bên trái"


def test_bo_cuc_tieu_chi_bao_ty_le_NHAN_qua_cao(bo):
    """Bản này chưa đi dây giữa các khối, nên tỉ lệ nhãn cao là điều CHỜ ĐỢI — và tiêu chí
    §4 phải nói ra, không được lặng lẽ cho qua."""
    from eide.sch import bo_cuc as BC

    bc = BC.tinh_bo_cuc(C.Cay.doc(bo), C.flatten(C.Cay.doc(bo)))
    tc = bc.tieu_chi
    assert 0.0 <= tc["ty_le_net_dung_nhan"] <= 1.0
    if tc["ty_le_net_dung_nhan"] > BC.NGUONG_NHAN:
        assert any("khó đọc" in v for v in tc["vi_pham"]), tc["vi_pham"]


def test_bo_cuc_chat_thi_TU_DOI_len_A3_chu_khong_bo_tieu_chi(bo):
    """Một trang chật là lý do thật để đổi khổ, không phải lý do để bỏ tiêu chí."""
    from eide.sch import bo_cuc as BC

    # Nhồi 40 lá vào một khối để A4 không chứa nổi.
    for i in range(40):
        _nut(bo, f"leaf:R{i}", f"R{i}", loai="linh_kien", cha="module:/board/mcu",
             kind="leaf", path=f"/board/mcu/R{i}", ref=f"R{i}")
        _port(bo, f"leaf:R{i}", "1", chan="1", path=f"/board/mcu/R{i}")
    bc = BC.tinh_bo_cuc(C.Cay.doc(bo), C.flatten(C.Cay.doc(bo)))
    assert bc.kho == "A3" or not bc.tieu_chi["dat"], bc.tieu_chi
    if bc.kho == "A3":
        assert bc.tieu_chi["trong_kho_giay"], bc.tieu_chi["vi_pham"]


def test_bo_cuc_cach_nhan_du_de_chu_khong_de_nhau(bo):
    """Khoảng cách hai nhãn kề nhau phải ≥ chiều cao chữ. Lớp bố cục sở hữu con số này và
    bộ vẽ đọc lại — nếu hai bên tự đoán riêng thì phép kiểm "chữ không đè" thành trang trí."""
    from eide.sch import bo_cuc as BC
    from eide.sch import ve_svg

    assert BC.CACH_NHAN >= BC.CAO_CHU_MM
    assert abs(ve_svg.CO_CHU_PX - BC.CAO_CHU_MM * ve_svg.PX_MOI_MM) < 1e-9


# =========================================================================== 11. ghi .kicad_sch
def test_SCH20_uuid_on_dinh_theo_ref(bo):
    """KiCad dùng uuid để khớp ký hiệu giữa hai lần mở tệp. uuid ngẫu nhiên nghĩa là mọi thứ
    người dùng đã sửa trong KiCad bị coi là của một ký hiệu khác và MẤT."""
    from eide.sch import ghi as G

    assert G.uuid_theo("sym:U1") == G.uuid_theo("sym:U1")
    assert G.uuid_theo("sym:U1") != G.uuid_theo("sym:U2")
    import re
    assert re.fullmatch(r"[0-9a-f-]{36}", G.uuid_theo("sym:U1"))


def test_ghi_kicad_sch_doc_lai_duoc_khop_tung_ky_tu(bo):
    """§3 bước 5 — "kiutils parse lại được (round-trip ổn định)".

    Kiểm khớp từng ký tự, không chỉ "đọc được": chỉ kiểm đọc được thì một trường bị bỏ khi
    ghi vẫn đạt, vì tệp vẫn hợp lệ — chỉ là thiếu.
    """
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G

    cay = C.Cay.doc(bo)
    bc = BC.tinh_bo_cuc(cay, C.flatten(cay))
    noi_dung = G.viet_kicad_sch(bc, symbol=SYM)
    ok, vi = G.doc_lai_duoc(noi_dung)
    assert ok, vi
    assert noi_dung == G.viet_kicad_sch(bc, symbol=SYM), "ghi hai lần phải giống nhau"


def test_ghi_kicad_sch_co_du_ref_va_khong_mat_ky_hieu_nao(bo):
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G

    cay = C.Cay.doc(bo)
    bc = BC.tinh_bo_cuc(cay, C.flatten(cay))
    noi_dung = G.viet_kicad_sch(bc, symbol=SYM)
    for z in bc.o:
        assert f'"{z.ref}"' in noi_dung, z.ref
    assert noi_dung.count("(symbol (lib_id") == len(bc.o)


# =========================================================================== 12. render SVG
def test_render_svg_co_du_ky_hieu_va_ban_do_ref(bo):
    """§3 bước 6: "số ký hiệu trong SVG = số ref" và "bản đồ id ký hiệu → ref"."""
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G
    from eide.sch import ve_svg

    cay = C.Cay.doc(bo)
    bc = BC.tinh_bo_cuc(cay, C.flatten(cay))
    kq = ve_svg.ve(G.viet_kicad_sch(bc, symbol=SYM),
                   hop={z.ref: (z.rong, z.cao) for z in bc.o})
    assert kq.so_ky_hieu == len(bc.o)
    assert sorted(kq.ref_trong_svg) == sorted(z.ref for z in bc.o)
    for z in bc.o:
        assert f'data-ref="{z.ref}"' in kq.svg, z.ref


def test_render_svg_bat_duoc_CHU_DE_NHAU(bo):
    """Phép kiểm đáng giá nhất của bước render: một sơ đồ có hai nhãn đè nhau vẫn "render
    thành công" — ảnh có, không lỗi, và người đọc thấy một chuỗi ký tự vô nghĩa."""
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G
    from eide.sch import ve_svg

    bc = BC.BoCuc(kho="A4", o=[BC.O(ref="U1", x=12.7, y=12.7, rong=25.4, cao=20.32)],
                  nhan=[{"net": "SDA", "ref": "U1", "chan": "27", "x": 40.0, "y": 14.0},
                        {"net": "SCL", "ref": "U1", "chan": "28", "x": 40.0, "y": 14.4}])
    kq = ve_svg.ve(G.viet_kicad_sch(bc, symbol={}), hop={"U1": (25.4, 20.32)})
    assert kq.chu_de_nhau, "hai nhãn cách 0,4 mm phải bị bắt là đè"
    assert any("đè nhau" in c for c in kq.canh_bao)


def test_render_anh_rong_thi_NOI_LA_RONG(bo):
    """"Render thành công" với không ký hiệu nào là một hình rỗng, không phải một sơ đồ."""
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G
    from eide.sch import ve_svg

    kq = ve_svg.ve(G.viet_kicad_sch(BC.BoCuc(kho="A4"), symbol={}))
    assert kq.so_ky_hieu == 0
    assert any("hình rỗng" in c for c in kq.canh_bao)


def test_render_duong_lui_khi_kiutils_khong_doc_duoc(bo):
    """§6 mức R3 — render là thứ người dùng NHÌN, nên nó không được biến mất chỉ vì một
    import; có đường lui bằng biểu thức chính quy, và nó NÓI RA là đang đi đường lui."""
    from eide.sch import ve_svg

    tho = ('(kicad_sch (paper "A4")\n'
           '  (symbol (lib_id "L:ATmega328P") (at 12.7 12.7 0)\n'
           '    (property "Reference" "U1" (at 0 0 0)))\n'
           '  (label "SDA" (at 40 14 0))\n)')
    d = ve_svg._doc_tho(tho)
    assert d["bang"] == "regex" and d["ky_hieu"][0]["ref"] == "U1"
    assert d["nhan"][0]["text"] == "SDA" and d["kho"] == "A4"


# =========================================================================== 13. công cụ B
def test_place_write_render_chay_het_duong_ong(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    for b in ("sch.symbols", "sch.compose", "sch.netlist"):
        assert goi(b).ok, b

    r = goi("sch.place")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_ky_hieu"] >= 1 and r.data["tieu_chi"]["cap_chong_nhau"] == 0

    r = goi("sch.write")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["round_trip"] is True
    p = a.config.paths.project_root / "sch/mach.kicad_sch"
    assert p.exists() and "(kicad_sch" in p.read_text("utf-8")
    assert (a.config.paths.project_root / "sch/mach.kicad_pro").exists()

    r = goi("sch.render")
    assert r.ok, getattr(r.error, "message_vi", "")
    # Vẽ MỌI sheet: với mạch phân cấp, gốc chỉ có hộp sheet nên một ảnh của riêng nó không có
    # linh kiện nào — và người mở ra sẽ tưởng render hỏng.
    assert len(r.data["tep"]) == r.data["tep"].__len__() >= 1
    assert r.data["so_ky_hieu"] >= 1, r.data
    noi = "".join((a.config.paths.project_root / t).read_text("utf-8")
                  for t in r.data["tep"])
    assert "data-ref=" in noi and noi.count("<svg") == len(r.data["tep"])


def test_place_tu_choi_khi_netlist_chua_kiem(make_agent):
    """Xếp đẹp một mạch chưa kiểm là xếp đẹp một mạch có thể sai."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    r = goi("sch.place")
    assert not r.ok and "sch.netlist" in (r.error.alternatives or [])
    assert "mạch sai" in r.error.message_vi


def test_write_tu_choi_khi_chua_co_bo_cuc(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    r = goi("sch.write")
    assert not r.ok and r.error.alternatives == ["sch.place"]


def test_render_chua_co_tep_thi_suy_giam_R3(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    r = goi("sch.render")
    assert not r.ok and "mức R3" in r.error.message_vi
    assert "diagram.render" in r.error.alternatives


# =========================================================================== 14. sheet phân cấp §7
def test_HIER13_moi_khoi_mot_sheet_va_sheet_pin_la_Port(bo):
    """HIER-45 §7 — "mỗi khối một sheet; Port của khối → hierarchical sheet pin"."""
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    g = PC.viet_phan_cap(cay, symbol=SYM)
    assert set(g.tep) == {"mach.kicad_sch", "mach_pwr.kicad_sch", "mach_mcu.kicad_sch",
                          "mach_mcu_xtal.kicad_sch"}, sorted(g.tep)
    con = g.tep["mach_mcu.kicad_sch"]
    assert "(hierarchical_label" in con or "hierarchical_label" in con
    assert '"VDD"' in con, "Port của khối thành nhãn phân cấp trong sheet con"
    goc = g.tep["mach.kicad_sch"]
    assert goc.count("(sheet ") == 2, "gốc có hai hộp sheet (pwr, mcu)"
    assert '"Sheetfile"' in goc and "mach_mcu.kicad_sch" in goc


def test_HIER13_doc_lai_goi_dung_lai_DUNG_cay(bo):
    """Điều kiện để `sch.import` dựng lại CÂY thay vì chỉ dựng lại netlist."""
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    g = PC.viet_phan_cap(cay, symbol=SYM)
    d = PC.doc_phan_cap(g.tep)
    assert d.canh_bao == [], d.canh_bao
    so = PC.so_cay(d, cay)
    assert so["khop"], so
    assert set(d.la) == {"U1", "U3", "Y1"}
    assert d.la["Y1"]["path"] == "/board/mcu/xtal"


def test_Sheetname_mang_DOAN_PATH_chu_khong_mang_ten_hien_thi(bo):
    """Đo lần đầu: ghi tên hiển thị làm `Sheetname` thì đọc lại ra `/board/Vi điều khiển` trong
    khi cây có `/board/mcu` — và `so_cay` báo MỌI khối đều "chỉ có ở tệp", tức một round-trip
    đúng bị kết luận là lệch hoàn toàn."""
    from eide.sch import phan_cap as PC

    bo.ckm_dat_nut(node_id="module:/board/mcu", loai="module", ten="Vi điều khiển",
                   canonical={"ten": "Vi điều khiển"})
    bo.ckm_dat_cay("module:/board/mcu", parent_id="module:/board", kind="block",
                   path="/board/mcu")
    cay = C.Cay.doc(bo)
    d = PC.doc_phan_cap(PC.viet_phan_cap(cay, symbol=SYM).tep)
    assert "/board/mcu" in d.khoi, sorted(d.khoi)
    assert d.khoi["/board/mcu"]["ten"] == "Vi điều khiển", "tên hiển thị KHÔNG mất"
    assert PC.so_cay(d, cay)["khop"]


def test_thieu_mot_sheet_trong_goi_thi_NOI_RA(bo):
    """Thiếu một sheet nghĩa là thiếu cả một khối của mạch — không được bỏ qua im lặng."""
    from eide.sch import phan_cap as PC

    g = PC.viet_phan_cap(C.Cay.doc(bo), symbol=SYM)
    thieu = {k: v for k, v in g.tep.items() if k != "mach_mcu_xtal.kicad_sch"}
    d = PC.doc_phan_cap(thieu)
    assert any("thiếu cả một khối" in c for c in d.canh_bao), d.canh_bao


def test_ghi_phan_cap_XAC_DINH(bo):
    from eide.sch import phan_cap as PC

    a = PC.viet_phan_cap(C.Cay.doc(bo), symbol=SYM).tep
    b = PC.viet_phan_cap(C.Cay.doc(bo), symbol=SYM).tep
    assert a == b


def test_moi_sheet_qua_duoc_phep_kiem_round_trip(bo):
    from eide.sch import ghi as G
    from eide.sch import phan_cap as PC

    for ten, nd in PC.viet_phan_cap(C.Cay.doc(bo), symbol=SYM).tep.items():
        ok, vi = G.doc_lai_duoc(nd)
        assert ok, f"{ten}: {vi}"


# =========================================================================== 15. phân loại §7
def _doc_gia(la: dict[str, dict], khoi: dict[str, dict] | None = None):
    class D:
        canh_bao: list = []
    d = D()
    d.la = la
    d.khoi = khoi if khoi is not None else {}
    d.nhan = {}
    return d


def test_SCH10_chi_doi_BO_CUC_thi_khong_lam_gi_loi_thoi(bo):
    """§7 mục 3(a). Nếu đánh STALE ở đây thì mỗi lần người sắp lại trang là một lần cả chuỗi
    hạ nguồn sáng đèn, và họ học được rằng băng cảnh báo vô nghĩa."""
    from eide.sch import nap_lai as NL
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    d = PC.doc_phan_cap(PC.viet_phan_cap(cay, symbol=SYM).tep)
    kq = NL.phan_loai(doc=d, cay=cay, so=PC.so_cay(d, cay),
                       gia_tri_kho=PC.gia_tri_mong_doi(cay, SYM))
    assert kq.thay_doi == [], [t.to_dict() for t in kq.thay_doi]
    assert not kq.can_hoi
    assert any("KHÔNG so từng toạ độ" in c for c in kq.canh_bao), \
        "phải nói ra giới hạn, không giả vờ đã đo"


def test_doi_GIA_TRI_linh_kien_thi_vao_loai_gia_tri(bo):
    from eide.sch import nap_lai as NL
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    so = PC.so_cay(PC.doc_phan_cap(PC.viet_phan_cap(cay, symbol=SYM).tep), cay)
    d = _doc_gia({"U3": {"ten": "AMS1117", "gia_tri": "AMS1117-5.0",
                         "path": "/board/pwr"},
                  "U1": {"ten": "ATmega328P", "gia_tri": "ATmega328P",
                         "path": "/board/mcu"},
                  "Y1": {"ten": "16MHz", "gia_tri": "16MHz", "path": "/board/mcu/xtal"}},
                 khoi={p: {"ten": p, "cha": "", "port": v}
                       for p, v in (("/board", []), ("/board/pwr", ["VOUT"]),
                                    ("/board/mcu", ["VDD"]),
                                    ("/board/mcu/xtal", ["XI"]))})
    kq = NL.phan_loai(doc=d, cay=cay, so=so,
                      gia_tri_kho={"U3": "AMS1117-3.3", "U1": "ATmega328P", "Y1": "16MHz"})
    gt = kq.theo_loai["gia_tri"]
    assert len(gt) == 1 and "AMS1117-3.3 → AMS1117-5.0" in gt[0].vi
    assert not kq.can_hoi, "đổi giá trị KHÔNG cần hỏi — đó là quyết định của họ"


def test_SCH12_them_linh_kien_moi_thi_PHAI_HOI(bo):
    """Ca SCH12 — "người thêm net mới trong KiCad rồi nạp lại: thẻ hỏi, không ghi đè im lặng"."""
    from eide.sch import nap_lai as NL
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    so = PC.so_cay(PC.doc_phan_cap(PC.viet_phan_cap(cay, symbol=SYM).tep), cay)
    d = _doc_gia({"U1": {"ten": "ATmega328P", "gia_tri": "", "path": "/board/mcu"},
                  "U3": {"ten": "AMS1117", "gia_tri": "", "path": "/board/pwr"},
                  "Y1": {"ten": "16MHz", "gia_tri": "", "path": "/board/mcu/xtal"},
                  "R9": {"ten": "R", "gia_tri": "4k7", "path": "/board/mcu"}})
    kq = NL.phan_loai(doc=d, cay=cay, so=so,
                      gia_tri_kho=PC.gia_tri_mong_doi(cay, SYM))
    assert kq.can_hoi
    ct = kq.theo_loai["cau_truc"]
    assert any("R9" in x.vi for x in ct), [x.vi for x in ct]

    the = NL.the_hoi(kq)
    assert the and len(the["lua_chon"]) == 2
    assert all(x["hau_qua"] for x in the["lua_chon"]), "mỗi lựa chọn phải nói HẬU QUẢ"
    assert "không chọn hộ" in the["khong_tu_chon"]


def test_SCH13_doi_CAU_TRUC_cay_thi_phai_hoi(bo):
    from eide.sch import nap_lai as NL
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    so = {"khop": False, "khoi_chi_co_o_tep": ["/board/rf"], "khoi_chi_co_o_kho": [],
          "port_lech": {"/board/mcu": {"o_tep": ["VDD", "ALERT"], "o_kho": ["VDD"]}}}
    kq = NL.phan_loai(doc=_doc_gia({}), cay=cay, so=so,
                      gia_tri_kho=PC.gia_tri_mong_doi(cay, SYM))
    assert kq.can_hoi and len(kq.theo_loai["cau_truc"]) >= 2
    assert any("lệch tập Port" in x.vi for x in kq.theo_loai["cau_truc"])


def test_la_chuyen_sang_khoi_khac_la_CAU_TRUC_khong_phai_bo_cuc(bo):
    """Chuyển một linh kiện sang sheet khác đổi khối chứa nó, tức đổi cả biên khối mà nó nằm
    trong — không phải kéo ký hiệu cho dễ đọc."""
    from eide.sch import nap_lai as NL
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    so = PC.so_cay(PC.doc_phan_cap(PC.viet_phan_cap(cay, symbol=SYM).tep), cay)
    d = _doc_gia({"U1": {"ten": "ATmega328P", "gia_tri": "", "path": "/board/pwr"},
                  "U3": {"ten": "AMS1117", "gia_tri": "", "path": "/board/pwr"},
                  "Y1": {"ten": "16MHz", "gia_tri": "", "path": "/board/mcu/xtal"}})
    kq = NL.phan_loai(doc=d, cay=cay, so=so,
                      gia_tri_kho=PC.gia_tri_mong_doi(cay, SYM))
    assert kq.can_hoi
    assert any("chuyển từ khối" in x.vi for x in kq.theo_loai["cau_truc"])


# =========================================================================== 16. công cụ C
def test_write_style_hierarchical_ghi_nhieu_sheet(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    for b in ("sch.symbols", "sch.compose", "sch.netlist", "sch.place"):
        assert goi(b).ok, b
    r = goi("sch.write", style="hierarchical")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["style"] == "hierarchical" and r.data["so_sheet"] >= 2
    assert r.data["doc_lai_dung_cay"] is True, r.data["so_cay"]
    d = a.config.paths.project_root / "sch"
    assert (d / "mach.kicad_sch").exists() and (d / "mach_MCU.kicad_sch").exists()


def test_HIER11_cay_sau_hon_4_cap_thi_TU_chuyen_sang_phan_cap(make_agent):
    """HIER-45 §7 — "depth > 4 → tự chuyển sang hierarchical và cảnh báo"."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    cha = "MCU"
    for i in range(1, 5):
        assert goi("ckm.module_set", ma=f"L{i}", ten=f"Tầng {i}", muc_dich="thử sâu",
                   cha=cha).ok
        cha = f"L{i}"
    for b in ("sch.symbols", "sch.compose", "sch.netlist", "sch.place"):
        goi(b)
    r = goi("sch.write", style="flat")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["style"] == "hierarchical", "phải TỰ chuyển, không cần hỏi lại"
    assert "TỰ chuyển sang phân cấp" in r.data["note_vi"]


def test_export_goi_co_tep_huong_dan_va_noi_ro_may_nay_khong_cai_kicad(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    for b in ("sch.symbols", "sch.compose", "sch.netlist", "sch.place", "sch.write",
              "sch.render"):
        goi(b)
    r = goi("sch.export")
    assert r.ok, getattr(r.error, "message_vi", "")
    d = a.config.paths.project_root / "sch/goi"
    assert (d / "mach.kicad_sch").exists() and (d / "mach.svg").exists()
    doc = (d / "DOC-TRUOC-KHI-MO.md").read_text("utf-8")
    assert "không cài KiCad" in doc and "sch.import" in doc
    assert "không cài KiCad" in r.data["note_vi"]


def test_export_chua_co_gi_thi_suy_giam_R3(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    r = goi("sch.export")
    assert not r.ok and "mức R3" in r.error.message_vi


def test_import_khong_doi_gi_thi_KHONG_danh_STALE(make_agent):
    """§7 mục 3(a) — chỉ bố cục thì không có gì lỗi thời."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    for b in ("sch.symbols", "sch.compose", "sch.netlist", "sch.place"):
        goi(b)
    goi("sch.write", style="hierarchical")
    r = goi("sch.import")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["can_hoi"] is False and r.data["so_thay_doi"] == 0
    assert "khớp bản đồ mạch" in r.data["note_vi"]


def test_import_them_linh_kien_thi_TAO_THE_HOI_khong_tu_ghi(make_agent):
    """Ca SCH12/SCH13 qua công cụ: sửa tệp trong KiCad rồi nạp lại."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    for b in ("sch.symbols", "sch.compose", "sch.netlist", "sch.place"):
        goi(b)
    goi("sch.write", style="hierarchical")

    p = a.config.paths.project_root / "sch/mach_MCU.kicad_sch"
    txt = p.read_text("utf-8")
    them = ('  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid 11111111-2222-4333-8444-555555555555)\n'
            '    (property "Reference" "R99" (at 100 98 0)\n'
            '      (effects (font (size 1.27 1.27)))\n'
            "    )\n"
            '    (property "Value" "4k7" (at 100 102 0)\n'
            '      (effects (font (size 1.27 1.27)))\n'
            "    )\n"
            "  )\n")
    p.write_text(txt.rstrip()[:-1] + them + ")\n", "utf-8")

    truoc = a.store.get("MG-1")["canonical"]
    r = goi("sch.import")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["can_hoi"] is True
    assert any("R99" in x["vi"] for x in r.data["theo_loai"]["cau_truc"])
    assert r.data["the_hoi"] and len(r.data["the_hoi"]["lua_chon"]) == 2
    # KHÔNG tự ghi đè bản đồ — đó là cả nội dung của SCH13.
    assert a.store.get("MG-1")["canonical"]["khoi"] == truoc["khoi"]


def test_import_khong_co_tep_thi_suy_giam_R3(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    r = goi("sch.import")
    assert not r.ok and "mức R3" in r.error.message_vi


# ================================================== 17. SCH-D1 — bố cục THEO SHEET (SCH07)
def _mach_lon(a, goi, *, so_khoi: int = 4, moi_khoi: int = 30):
    """Mạch `so_khoi × moi_khoi` linh kiện thụ động — SCH07 nói 120."""
    _dung_mach(a, goi)
    for k in range(so_khoi):
        ma = f"K{k}"
        goi("ckm.module_set", ma=ma, ten=f"Khối {k}", muc_dich="thử mạch lớn",
            linh_kien=[f"R{k}{i:02d}" for i in range(moi_khoi)])
        goi("ckm.port_set", khoi=ma, ten="IN", huong="in")
        # Port khai rồi phải NỐI: Port treo sinh net `IN_chua_noi`, và `sch.netlist` bắt đúng
        # nó — mạch hở là mạch hở, kể cả trong một bộ đo về bố cục.
        # Mọi điện trở phải có CHÂN trong một net, vì lá của cây sinh ra từ chân — một ref chỉ
        # nằm trong `linh_kien` mà không có chân nào thì chưa phải một linh kiện trên mạch.
        goi("ckm.net_set", ten=f"N{k}", loai="signal",
            chan=[[f"R{k}{i:02d}", "1"] for i in range(moi_khoi)],
            noi_port=[[ma, "IN"]])
    goi("ckm.build")


def test_SCH07_mach_120_linh_kien_de_nghi_phan_cap_va_moi_sheet_do_rieng(make_agent):
    """SCH07 — "Mạch 120 linh kiện → đề nghị hierarchical; mỗi sheet đạt tiêu chí".

    "Mỗi sheet đạt" là một đòi hỏi KHÁC "cả mạch đạt": một mạch chia khối có thể đạt trên
    tổng thể mà vẫn có một trang tràn. Nên phép đo phải chạy trên từng trang.
    """
    a, goi, _ = _agent_sch(make_agent)
    _mach_lon(a, goi)
    goi("sch.compose")
    goi("sch.symbols")
    rn = goi("sch.netlist")
    assert rn.ok, getattr(rn.error, "message_vi", "")
    r = goi("sch.place")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_ky_hieu"] >= 120, r.data["so_ky_hieu"]
    assert r.data["de_nghi_phan_cap"]["nen_phan_cap"] is True, r.data["de_nghi_phan_cap"]
    assert "style=hierarchical" in r.data["de_nghi_phan_cap"]["vi"]
    # Mỗi sheet có tiêu chí RIÊNG, và số của nó là số của trang đó chứ không phải của cả mạch.
    assert r.data["so_sheet"] >= 5
    tcs = r.data["tieu_chi_sheet"]
    assert sum(t["so_ky_hieu"] for t in tcs.values()) == r.data["so_ky_hieu"]
    assert r.data["sheet_chua_dat"] == [], {k: v["vi_pham"] for k, v in tcs.items()
                                            if not v["dat"]}


def test_ly_do_de_nghi_phan_cap_la_SO_do_duoc_khong_phai_khau_vi(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _mach_lon(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist")
    r = goi("sch.place")
    ld = r.data["de_nghi_phan_cap"]["ly_do"]
    assert ld and all(any(c.isdigit() for c in x) for x in ld), ld


def test_mach_chat_nhung_CHUA_CHIA_KHOI_thi_noi_chia_khoi_truoc(make_agent):
    """Đề nghị "chia sheet" cho một cây chỉ có một khối là một lời khuyên vô dụng: chia sheet
    lấy khối làm đơn vị, nên không có khối thì không có gì để chia."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("ckm.module_set", ma="MCU", ten="Vi điều khiển", muc_dich="chạy firmware",
        linh_kien=["U1"] + [f"R{i:02d}" for i in range(60)])
    goi("ckm.build")
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist")
    r = goi("sch.place")
    dn = r.data["de_nghi_phan_cap"]
    assert dn["nen_phan_cap"] is False and "chia khối trước" in dn["vi"], dn


def test_ty_le_nhan_cua_MOT_SHEET_dem_net_cua_sheet_do(bo):
    """Mẫu số phải là net của trang đó. Lấy net của cả mạch thì một sheet 2 net trên tổng 20
    net luôn "rất ít nhãn" — một con số luôn đẹp là một con số không đo gì."""
    from eide.sch import bo_cuc as BC

    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    sheet = BC.tinh_bo_cuc_theo_sheet(cay, phang, kho="A4")
    rieng = BC._phang_cua_sheet(cay, phang, "module:/board/mcu")
    # Cùng tên net, nhưng CHÂN bị giới hạn trong sheet — U3 và Y1 ở sheet khác.
    assert sum(len(v) for v in rieng.values()) < sum(len(v) for v in phang.values())
    assert all(c.split(".")[0] == "U1" for ds in rieng.values() for c in ds), rieng
    assert "/board/mcu" in sheet and sheet["/board/mcu"].tieu_chi["so_ky_hieu"] == 1


def test_hop_sheet_con_VAO_phep_dem_chong_va_phep_kiem_tran_trang(bo):
    """Hộp sheet là vật thể lớn nhất trên trang cha. Tiêu chí không nhìn thấy nó thì câu
    "0 ký hiệu chồng nhau" chỉ nói về nửa trang."""
    from eide.sch import bo_cuc as BC

    cay = C.Cay.doc(bo)
    bc = BC._bo_cuc_mot_sheet(cay, {}, "module:/board", kho="A4")
    assert bc.hop_sheet and bc.tieu_chi is not None
    # Đẩy một hộp sheet lên đúng chỗ một ký hiệu → phải bị bắt.
    bc.o.append(BC.O(ref="X9", x=bc.hop_sheet[0].x, y=bc.hop_sheet[0].y, rong=5.08, cao=5.08))
    tc = BC.kiem_tieu_chi(bc, {})
    assert not tc["dat"] and any("chồng nhau" in v for v in tc["vi_pham"]), tc
    # Và tràn trang cũng phải thấy hộp sheet.
    bc.o.pop()
    bc.hop_sheet[0].x = 900.0
    tc = BC.kiem_tieu_chi(bc, {})
    assert not tc["dat"] and any("tràn khỏi khổ" in v for v in tc["vi_pham"]), tc


def test_ghi_phan_cap_dung_DUNG_toa_do_cua_bo_cuc(bo):
    """Bên ghi ghi theo bố cục, không tự xếp: hai lần tính là hai cơ hội ra hai kết quả."""
    from eide.sch import bo_cuc as BC
    from eide.sch import phan_cap as PC

    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    sheet = BC.tinh_bo_cuc_theo_sheet(cay, phang, kho="A4")
    goi = PC.viet_phan_cap(cay, symbol=SYM, bo_cuc_sheet=sheet)
    bc = sheet["/board/mcu"]
    z = next(x for x in bc.o if x.ref == "U1")
    txt = goi.tep[PC.ten_tep_sheet("/board/mcu")]
    assert f"(at {z.x:g} {z.y:g} 0)" in txt, (z.x, z.y, txt[:400])


# ============================== 18. SCH-D2 — sổ đăng ký sheet và gói vào bản ưng ý (SCH-16)
def test_so_dang_ky_sheet_mot_dong_moi_sheet_kem_bam_bo_cuc(make_agent):
    """§2.1(4) — `sch_sheets(id, version, path, lib_versions, layout_hash, explain)`."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    r = goi("sch.write", style="hierarchical")
    assert r.ok, getattr(r.error, "message_vi", "")
    ds = a.store.sch_cac_sheet()
    assert len(ds) == r.data["so_sheet_ghi_so"] == len(r.data["tep"]) - 1
    assert all(x["layout_hash"] for x in ds), ds
    assert all("eide-sinh" in x["lib_versions"] for x in ds), ds
    # Ghi lại lần hai thì `version` tăng — đó là thứ cho phép nói "bản 2 của sheet này".
    goi("sch.write", style="hierarchical")
    assert {x["version"] for x in a.store.sch_cac_sheet()} == {2}


def test_sheet_bien_mat_thi_BI_GO_khoi_so_dang_ky(make_agent):
    """Đổi từ 3 khối xuống 2 thì một tệp sheet không còn. Để dòng cũ lại thì bản ưng ý sau đó
    gói theo một tệp không tồn tại — và "khôi phục được" thành lời hứa suông."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("ckm.module_set", ma="PWR", ten="Nguồn", muc_dich="hạ áp", linh_kien=["U3"])
    goi("ckm.net_set", ten="5V", loai="power", chan=[["U3", "1"]])
    goi("ckm.build")
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    goi("sch.write", style="hierarchical")
    truoc = {x["tep"] for x in a.store.sch_cac_sheet()}
    assert any("PWR" in t for t in truoc), truoc

    # Gỡ khối bằng đường có thật: bỏ nó khỏi bản đồ rồi chiếu lại (hiện vật là sự thật,
    # đồ thị là hình chiếu).
    mg = a.store.get("MG-1")
    a.store.apply(artefact_id="MG-1", type="block_diagram", op="update", author="human",
                  explain={"summary": "bỏ khối PWR"},
                  canonical={**mg["canonical"],
                             "khoi": [k for k in mg["canonical"]["khoi"]
                                      if k.get("ma") != "PWR"]})
    from eide.knowledge import ckm as K
    K.chieu(a.store)
    goi("sch.place")
    r = goi("sch.write", style="hierarchical")
    sau = {x["tep"] for x in a.store.sch_cac_sheet()}
    assert not any("PWR" in t for t in sau), sau
    assert r.data["sheet_go_khoi_so"] >= 1, r.data


def test_SCH16_ban_ung_y_goi_so_do_va_khoi_phuc_dua_TEP_ve(make_agent):
    """SCH-16 — "Gói sch vào snapshot/release", và gói ở đây là gói cả NỘI DUNG.

    Một bản ưng ý chỉ nhớ tên tệp thì việc quay về được phụ thuộc vào tệp còn nguyên — tức
    phụ thuộc vào đúng thứ mà người ta ghi bản ưng ý để KHÔNG phải phụ thuộc vào.
    """
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    goi("sch.write", style="hierarchical")

    snap = a.history.tao_snapshot(ten="co-so-do", ghi_chu="thử SCH-16", boi="human")
    sd = snap.contents["so_do"]
    assert sd["so_sheet"] >= 2 and all(x["co_tep"] for x in sd["sheet"]), sd
    assert sd["lib_versions"], sd
    assert any(k["tep"].endswith(".kicad_sym") for k in sd["kem"]), sd

    goc = a.config.paths.project_root
    p = goc / sd["sheet"][0]["tep"]
    that = p.read_text("utf-8")
    p.write_text("(kicad_sch BỊ SỬA TAY)\n", "utf-8")
    (goc / "sch/eide-sinh.kicad_sym").unlink()

    kq = a.history.khoi_phuc_snapshot(snap.id, by="human")
    assert kq.ok, kq.message_vi
    assert p.read_text("utf-8") == that
    assert (goc / "sch/eide-sinh.kicad_sym").exists()
    assert "tệp sơ đồ về đúng nội dung" in kq.message_vi


def test_ban_ung_y_NOI_RA_khi_mot_sheet_da_dang_ky_khong_con_tep(make_agent):
    """Im lặng bỏ qua thì bản ưng ý nói "gói 5 sheet" trong khi chỉ khôi phục được 3 — và điều
    đó chỉ vỡ ra vào lúc người ta cần nó nhất."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    goi("sch.write", style="hierarchical")
    ds = a.store.sch_cac_sheet()
    (a.config.paths.project_root / ds[0]["tep"]).unlink()

    snap = a.history.tao_snapshot(ten="thieu-tep", boi="human")
    sd = snap.contents["so_do"]
    assert sd["canh_bao"] and "không còn trên đĩa" in sd["canh_bao"][0], sd
    assert any(x["co_tep"] is False for x in sd["sheet"])


# ================= 19. SCH-D3 — ký hiệu sinh từ Fact phải được NGƯỜI xác nhận (SCH-14/15)
def test_ky_hieu_sinh_tu_Fact_thi_CHO_xac_nhan_lib_khop_100_thi_khong(make_agent):
    """§9 — widget "Symbol sinh từ Fact: xem, xác nhận, sửa kiểu chân" là loại **edit**.

    Kiểu chân sinh ra là phép SUY (hướng Port → kiểu chân KiCad), và ERC của KiCad dựa vào nó.
    Ký hiệu lấy từ thư viện chính thức khớp 100 % thì không cần xác nhận: ở đó tác giả thư viện
    đã là con người đó.
    """
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    r = goi("sch.symbols")
    assert r.ok and r.data["cho_xac_nhan"] == ["U1"], r.data.get("cho_xac_nhan")
    assert "CHỜ người xác nhận" in r.data["note_vi"]

    # Có thư viện chính thức khớp 100 % ⇒ không phải hỏi ai.
    chan = [{"so": c["so"], "ten": c["ten"]}
            for c in next(x for x in r.data["chi_tiet"] if x["ref"] == "U1")["chan"]]
    a.store.apply(artefact_id="symbol_lib:kicad", type="report", op="create", author="human",
                  explain={"summary": "thư viện tải về"},
                  canonical={"phien_ban": "8.0.1",
                             "ky_hieu": {"ATmega328P": {"lib": "MCU_Microchip_ATmega",
                                                        "ten": "ATmega328P-PU",
                                                        "version": "8.0.1", "chan": chan}}})
    r2 = goi("sch.symbols")
    assert r2.data["cho_xac_nhan"] == [], r2.data["cho_xac_nhan"]


def test_tac_tu_KHONG_tu_xac_nhan_ho_nguoi_dung(make_agent):
    """Một xác nhận không có lời của người là một xác nhận của MÁY đội tên người."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    r = goi("sch.symbol_confirm", ref="U1", trich_loi="")
    assert not r.ok and r.error.code == "E8009"
    assert "Đừng tự xác nhận hộ" in r.error.hint_for_agent


def test_nguoi_sua_kieu_chan_thanh_Fact_tang_NGUOI_co_trich_loi(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    r = goi("sch.symbol_confirm", ref="U1",
            trich_loi="chân 7 là chân nguồn vào, tôi xem datasheet rồi",
            kieu_chan={"7": "power_in"})
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["con_cho_xac_nhan"] == []
    f = [x for x in a.store.query_facts(subject="pin:ATmega328P.7", limit=10)
         if x["key"] == "kieu_chan"]
    assert f and f[0]["tier"] == "NGUOI", f
    src = f[0]["source"]
    if isinstance(src, str):
        import json as _j
        src = _j.loads(src)
    assert "datasheet rồi" in src["quote"]


def test_xac_nhan_va_kieu_chan_nguoi_sua_SONG_SOT_qua_lan_sinh_lai(make_agent):
    """Nếu `sch.symbols` quên phần này thì người dùng xác nhận lần thứ ba rồi thôi."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    goi("sch.symbol_confirm", ref="U1", trich_loi="đúng rồi, chân 27 là chân số",
        kieu_chan={"27": "bidirectional"})
    r = goi("sch.symbols")
    u1 = next(x for x in r.data["chi_tiet"] if x["ref"] == "U1")
    assert u1["xac_nhan_boi"] == "human" and u1["can_xac_nhan"] is False
    c27 = next(c for c in u1["chan"] if c["so"] == "27")
    assert c27["kieu"] == "bidirectional" and c27.get("kieu_boi_nguoi") == "có"
    # Và tệp .kicad_sym mang kiểu chân của NGƯỜI, không mang phép suy của máy.
    txt = (a.config.paths.project_root / "sch/eide-sinh.kicad_sym").read_text("utf-8")
    assert "(pin bidirectional line" in txt, txt[:300]


def test_sua_kieu_chan_cho_mot_chan_KHONG_TON_TAI_thi_tu_choi(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    r = goi("sch.symbol_confirm", ref="U1", trich_loi="chân 99 là nguồn",
            kieu_chan={"99": "power_in"})
    assert not r.ok and r.error.code == "E8011"
    r2 = goi("sch.symbol_confirm", ref="U1", trich_loi="đặt kiểu lạ",
             kieu_chan={"7": "chan_nguon"})
    assert not r2.ok and r2.error.code == "E8010"


def test_sch_write_NOI_RA_con_ky_hieu_chua_ai_xac_nhan(make_agent):
    """Im lặng thì người mở KiCad thấy ERC báo lỗi nguồn và tin rằng MẠCH của họ sai."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    r = goi("sch.write", style="flat")
    assert r.ok and r.data["cho_xac_nhan_ky_hieu"] == ["U1"]
    assert "chưa ai xác nhận" in r.data["note_vi"], r.data["note_vi"]


def test_nguoi_bam_sua_kieu_chan_TREN_GIAO_DIEN_di_cung_mot_duong(make_agent):
    """§9 — widget edit trên tab Thiết kế phải đi qua ĐÚNG công cụ mà tác tử dùng.

    Nếu giao diện có đường ghi riêng thì luật "phải có lời của người" và "kiểu chân thành Fact
    tầng NGƯỜI" tồn tại ở hai chỗ, và một ngày nào đó chỉ còn ở một chỗ.
    """
    from eide.protocol.humanact import HumanAct

    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")

    seen: list = []
    act = HumanAct.from_dict({
        "kind": "edit", "target": "symbol:U1",
        "data": {"base_version": "v1", "fields": {"chan.7": "power_in"}},
        "origin": {"surface": "design", "block": "A5.8c", "row": "U1"},
        "note": "tôi tra datasheet, chân 7 là VCC nên là power_in"})
    a.turn(act, seen.append)

    f = [x for x in a.store.query_facts(subject="pin:ATmega328P.7", limit=10)
         if x["key"] == "kieu_chan"]
    assert f and f[0]["tier"] == "NGUOI" and f[0]["value"] == "power_in", f
    assert any("xác nhận" in getattr(c, "params", {}).get("text", "") for c in seen), seen


def test_nguoi_bam_xac_nhan_MA_KHONG_viet_gi_thi_khong_ghi(make_agent):
    from eide.protocol.humanact import HumanAct

    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    seen: list = []
    a.turn(HumanAct.from_dict({
        "kind": "edit", "target": "symbol:U1",
        "data": {"base_version": "v1", "fields": {"chan.7": "power_in"}},
        "origin": {"surface": "design"}}), seen.append)
    assert not [x for x in a.store.query_facts(subject="pin:ATmega328P.7", limit=10)
                if x["key"] == "kieu_chan"]
    assert any(getattr(c, "params", {}).get("code") == "E8009" for c in seen), seen


# ============================ 20. SCH-D4 — khối A5.8 trên tab Thiết kế (SCH-06, SCH-07, §9)
def _design(store):
    from eide import surfaces as S

    class Inv:
        def __getattr__(self, k): return 0
    return {b["code"]: b for b in S.design(store, Inv())["blocks"]}


def test_chua_sinh_so_do_thi_tab_Thiet_ke_KHONG_doi_mot_khoi_nao(make_agent):
    """Điều kiện của cờ tính năng (§2.1 mục 2): bật cờ mà chưa gọi sch thì giao diện y như cũ.

    Nên ở đây KHÔNG có cả ô trống trung thực — một ô trống cũng là một khối mới."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    assert not [k for k in _design(a.store) if k.startswith("A5.8")]


def test_A5_8_hien_anh_so_do_moi_trang_mot_muc_va_bam_duoc(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    goi("sch.write", style="hierarchical")
    goi("sch.render")

    kh = _design(a.store)
    sd = kh["A5.8"]
    assert sd["type"] == "svg" and len(sd["tep"]) >= 2, sd
    assert "U1" in sd["ref"], sd["ref"]
    # Câu hỏi khi bấm do LÕI soạn, nên nội dung nó không nằm rải trong mã Swift.
    assert "{ref}" in sd["bam_ky_hieu"] and "{net}" in sd["bam_net"]
    # Lớp giải thích đủ sáu trường — hợp đồng E2 áp cho khối này như mọi khối khác.
    assert set(sd["explain"]) >= {"summary", "why", "sources", "diff_prev", "next",
                                 "confidence"}


def test_A5_8b_bang_chat_luong_co_MOT_DONG_moi_trang_va_ket_luan_bang_chu(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _mach_lon(a, goi, so_khoi=3, moi_khoi=20)
    goi("sch.compose"); goi("sch.symbols"); goi("sch.netlist"); goi("sch.place")
    b = _design(a.store)["A5.8b"]
    assert b["columns"][0] == "Trang" and len(b["rows"]) >= 4, b["rows"]
    assert all(r[-1].startswith(("ĐẠT", "CHƯA")) for r in b["rows"]), b["rows"]
    assert "sheet phân cấp" in b["summary"], b["summary"]


def test_A5_8c_bang_ky_hieu_SUA_DUOC_va_di_dung_loai_doi_tuong(make_agent):
    """`loai_sua` là thứ nói cho giao diện biết ô này sửa KÝ HIỆU, không phải sửa yêu cầu."""
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    b = _design(a.store)["A5.8c"]
    assert b["loai_sua"] == "symbol" and "Kiểu chân" in b["cot_sua"]
    assert any("CHỜ ANH XEM" in str(c) for r in b["rows"] for c in r), b["rows"]
    assert "ERC trong KiCad dựa vào kiểu chân" in b["summary"]

    goi("sch.symbol_confirm", ref="U1", trich_loi="đúng cả, tôi xem rồi")
    b2 = _design(a.store)["A5.8c"]
    assert any("anh đã xác nhận" in str(c) for r in b2["rows"] for c in r), b2["rows"]


def test_A5_8d_noi_ro_muc_render_va_KHONG_de_nghi_cai_KiCad(make_agent):
    a, goi, _ = _agent_sch(make_agent)
    _dung_mach(a, goi)
    goi("sch.symbols")
    b = _design(a.store)["A5.8d"]
    assert b.get("pairs"), "khối kv phải gửi `pairs`, không phải `items`"
    chu = " ".join(f"{k} {v}" for k, v in b["pairs"]) + b["summary"]
    assert "KHÔNG cài KiCad" in chu
    for xau in ("hãy cài", "nên cài", "cài KiCad để", "brew install"):
        assert xau not in chu, xau


def test_o_bang_dang_7_power_in_duoc_tach_dung(make_agent):
    from eide.loop import _tach_kieu_chan

    assert _tach_kieu_chan("7=power_in, 27=bidirectional") == {"7": "power_in",
                                                              "27": "bidirectional"}
    # Gõ thiếu một cặp không được làm mất phần gõ đúng.
    assert _tach_kieu_chan("7=power_in, 28") == {"7": "power_in"}
    assert _tach_kieu_chan("") == {}


def test_nhan_net_trong_SVG_mang_data_net_de_bam_duoc(bo):
    """SCH-07 — "bấm net → tô sáng toàn net + ERC". Không có `data-net` thì nửa sau của câu
    tương tác đó không thực hiện được."""
    from eide.sch import bo_cuc as BC
    from eide.sch import ghi as G
    from eide.sch import ve_svg

    cay = C.Cay.doc(bo)
    phang = C.flatten(cay)
    bc = BC.tinh_bo_cuc(cay, phang)
    kq = ve_svg.ve(G.viet_kicad_sch(bc, symbol=SYM), hop={})
    assert 'data-net="3V3"' in kq.svg, kq.svg[:400]
    assert "3V3" in kq.to_dict()["net_trong_svg"]
