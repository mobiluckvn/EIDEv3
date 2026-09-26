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
    assert set(tat.bo_qua_vi_co) == {"sch.compose", "sch.netlist", "sch.symbols"}
    bat = build_registry(Features(schematic=True))
    assert len([t for t in bat.all() if t.name.startswith("sch.")]) == 3
    assert len(bat.all()) == len(tat.all()) + 3


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
