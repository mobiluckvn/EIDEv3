# -*- coding: utf-8 -*-
"""Cây khối phân cấp — EIDE-HIER-45 §2–§3. Ca HIER01–04.

Bộ này đo bốn thứ, xếp theo "sai chỗ nào thì tệ nhất":

  1. `flatten` — nếu sai, MỌI tool phẳng (ERC, BOM, sim) nhận dữ liệu sai mà không biết
  2. E9002 nối xuyên cấp — nếu không chặn, "biên khối" chỉ là trang trí
  3. E9004 Port lá thừa — sơ đồ vẽ một chân chip KHÔNG có (N1 ở chỗ khó thấy nhất)
  4. E9006 đóng gói — nếu không đo, "sửa nội bộ không lan STALE" là một lời hứa suông
"""

from __future__ import annotations

import pytest

from eide.knowledge import cay as C
from eide.store import Store


# --------------------------------------------------------------------------- dàn dựng
def _khoi(s: Store, nid: str, ten: str, *, cha: str | None, kind: str, path: str,
          ref: str = "") -> None:
    s.ckm_dat_nut(node_id=nid, loai="module" if kind != "leaf" else "linh_kien",
                  ten=ten, canonical={"ref": ref} if ref else {"ten": ten})
    s.ckm_dat_cay(nid, parent_id=cha, kind=kind, path=path)


def _net(s: Store, ten: str, *, trong: str, path: str) -> str:
    nid = f"net:{path}"
    s.ckm_dat_nut(node_id=nid, loai="net", ten=ten, canonical={"ten": ten})
    s.ckm_dat_cay(nid, parent_id=trong, kind=None, path=path)
    return nid


def _port(s: Store, module_id: str, ten: str, *, huong: str = "bidir",
          loai: str = "single", members=None, chan: str | None = None) -> str:
    pid = f"port:{module_id}.{ten}"
    s.ckm_dat_port(port_id=pid, module_id=module_id, ten=ten, huong=huong, loai=loai,
                   members=members or [], chan=chan)
    return pid


@pytest.fixture
def bo_mach(tmp_path) -> Store:
    """Mạch hai tầng: board → {MOD-PWR, MOD-MCU → {U1}}; board có net 3V3 và SDA.

        /board
          ├── MOD-PWR (U3)      Port: VOUT (power_out)
          ├── MOD-MCU           Port: VDD (power_in), SDA (bidir)
          │     └── U1 (lá)     Port: 7, 27
          └── net 3V3, net SDA_B
    """
    s = Store(tmp_path / "k.sqlite")
    _khoi(s, "module:/board", "Bo mạch", cha=None, kind="board", path="/board")
    _khoi(s, "module:/board/pwr", "Nguồn", cha="module:/board", kind="block",
          path="/board/pwr")
    _khoi(s, "module:/board/mcu", "MCU", cha="module:/board", kind="block",
          path="/board/mcu")
    _khoi(s, "leaf:U3", "LDO", cha="module:/board/pwr", kind="leaf",
          path="/board/pwr/U3", ref="U3")
    _khoi(s, "leaf:U1", "ATmega328P", cha="module:/board/mcu", kind="leaf",
          path="/board/mcu/U1", ref="U1")

    # Port của lá — trong sản phẩm chúng sinh từ Fact pinout.
    p_u3 = _port(s, "leaf:U3", "3", huong="power_out", chan="3")
    p_u1_7 = _port(s, "leaf:U1", "7", huong="power_in", chan="7")
    p_u1_27 = _port(s, "leaf:U1", "27", chan="27")

    # Port ở biên khối — hợp đồng.
    p_pwr_out = _port(s, "module:/board/pwr", "VOUT", huong="power_out")
    p_mcu_vdd = _port(s, "module:/board/mcu", "VDD", huong="power_in")
    p_mcu_sda = _port(s, "module:/board/mcu", "SDA")

    # Net ở board nối hai khối qua Port của chúng.
    n_3v3 = _net(s, "3V3", trong="module:/board", path="/board.3V3")
    s.ckm_noi(net_id=n_3v3, port_id=p_pwr_out)
    s.ckm_noi(net_id=n_3v3, port_id=p_mcu_vdd)
    n_sda = _net(s, "SDA", trong="module:/board", path="/board.SDA")
    s.ckm_noi(net_id=n_sda, port_id=p_mcu_sda)

    # Net cục bộ trong mỗi khối, nối Port "lên cha" với chân lá.
    n_pwr = _net(s, "VOUT_I", trong="module:/board/pwr", path="/board/pwr.VOUT_I")
    s.ckm_noi(net_id=n_pwr, port_id=p_pwr_out)
    s.ckm_noi(net_id=n_pwr, port_id=p_u3)

    n_vdd = _net(s, "VDD_I", trong="module:/board/mcu", path="/board/mcu.VDD_I")
    s.ckm_noi(net_id=n_vdd, port_id=p_mcu_vdd)
    s.ckm_noi(net_id=n_vdd, port_id=p_u1_7)

    n_sdai = _net(s, "SDA_I", trong="module:/board/mcu", path="/board/mcu.SDA_I")
    s.ckm_noi(net_id=n_sdai, port_id=p_mcu_sda)
    s.ckm_noi(net_id=n_sdai, port_id=p_u1_27)
    return s


# =========================================================================== 1. flatten
def test_flatten_hop_nhat_net_qua_port(bo_mach):
    """HIER02/HIER-04 — net board + net cục bộ hai bên Port là MỘT net điện."""
    f = C.flatten(C.Cay.doc(bo_mach))
    assert f["3V3"] == ["U1.7", "U3.3"], f
    assert f["SDA"] == ["U1.27"], f


def test_flatten_lay_ten_o_cap_cao_nhat(bo_mach):
    """Tên net phải là tên người ở ngoài gọi nó, không phải tên cục bộ trong khối."""
    f = C.flatten(C.Cay.doc(bo_mach))
    assert "VOUT_I" not in f and "VDD_I" not in f
    assert set(f) == {"3V3", "SDA"}


def test_flatten_xac_dinh_va_sap_chan_theo_SO(bo_mach):
    """`U1.2` phải đứng trước `U1.10`. Bảng netlist sắp theo chữ làm người quét hai lần."""
    s = bo_mach
    p2 = _port(s, "leaf:U1", "2", chan="2")
    p10 = _port(s, "leaf:U1", "10", chan="10")
    n = _net(s, "X", trong="module:/board/mcu", path="/board/mcu.X")
    s.ckm_noi(net_id=n, port_id=p2)
    s.ckm_noi(net_id=n, port_id=p10)
    f = C.flatten(C.Cay.doc(s))
    assert f["X"] == ["U1.2", "U1.10"]
    assert C.flatten(C.Cay.doc(s)) == f, "cùng cây ⇒ cùng kết quả (N3)"


def test_flatten_khong_de_hai_net_cung_ten_o_hai_khoi(bo_mach):
    """Mỗi khối có một 'VDD' cục bộ là chuyện thường. Nếu để đè thì netlist phẳng MẤT một
    net và không ai biết — nên nhóm thứ hai phải mang tên đầy đủ."""
    s = bo_mach
    for khoi, la, chan in (("module:/board/pwr", "leaf:U3", "1"),
                           ("module:/board/mcu", "leaf:U1", "20")):
        p = _port(s, la, chan, chan=chan)
        n = _net(s, "VDD", trong=khoi, path=f"{khoi.split(':')[1]}.VDD")
        s.ckm_noi(net_id=n, port_id=p)
    f = C.flatten(C.Cay.doc(s))
    co_vdd = [k for k in f if "VDD" in k]
    assert len(co_vdd) == 2, f"hai net VDD phải còn là hai: {co_vdd}"
    assert any(k.startswith("/board/") for k in co_vdd), co_vdd


def test_flatten_giu_net_chua_noi_gi(bo_mach):
    """Net rỗng phải còn trong kết quả — nó là một cái tên vô nghĩa mà người cần thấy."""
    _net(bo_mach, "TREO", trong="module:/board", path="/board.TREO")
    assert C.flatten(C.Cay.doc(bo_mach))["TREO"] == []


def test_flatten_ba_tang_van_hop_nhat_duoc(bo_mach):
    """HIER02 — thêm khối con trong khối MCU (dao động thạch anh)."""
    s = bo_mach
    _khoi(s, "module:/board/mcu/xtal", "Dao động", cha="module:/board/mcu",
          kind="subblock", path="/board/mcu/xtal")
    _khoi(s, "leaf:Y1", "16 MHz", cha="module:/board/mcu/xtal", kind="leaf",
          path="/board/mcu/xtal/Y1", ref="Y1")
    p_y1 = _port(s, "leaf:Y1", "1", chan="1")
    p_xtal = _port(s, "module:/board/mcu/xtal", "XI", huong="out")
    n_trong = _net(s, "XI_I", trong="module:/board/mcu/xtal",
                   path="/board/mcu/xtal.XI_I")
    s.ckm_noi(net_id=n_trong, port_id=p_xtal)
    s.ckm_noi(net_id=n_trong, port_id=p_y1)
    p_u1_9 = _port(s, "leaf:U1", "9", chan="9")
    n_mcu = _net(s, "XTAL1", trong="module:/board/mcu", path="/board/mcu.XTAL1")
    s.ckm_noi(net_id=n_mcu, port_id=p_xtal)
    s.ckm_noi(net_id=n_mcu, port_id=p_u1_9)

    f = C.flatten(C.Cay.doc(s))
    assert f["XTAL1"] == ["U1.9", "Y1.1"], f
    assert not C.kiem_bat_bien(C.Cay.doc(s)), "cây ba tầng này phải hợp lệ"


# =========================================================================== 2. bất biến
def test_cay_dung_thi_khong_vi_pham_gi(bo_mach):
    assert C.kiem_bat_bien(C.Cay.doc(bo_mach)) == []


def test_E9001_chu_trinh(bo_mach):
    # Chỉ đổi CHA, giữ nguyên node_id — cây đi lên theo id, không theo path.
    bo_mach.ckm_dat_cay("module:/board/mcu", parent_id="module:/board/pwr",
                        kind="block", path="/board/pwr/mcu")
    bo_mach.ckm_dat_cay("module:/board/pwr", parent_id="module:/board/mcu",
                        kind="block", path="/board/pwr")
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach))
    assert any(x.ma == C.E_CHU_TRINH for x in v), [x.vi for x in v]


def test_E9001_hai_goc(bo_mach):
    _khoi(bo_mach, "module:/board2", "Bo khác", cha=None, kind="board", path="/board2")
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach))
    assert any(x.ma == C.E_CHU_TRINH and "một gốc" in x.vi for x in v)


def test_E9002_noi_xuyen_cap_bi_tu_choi_va_goi_y_khai_Port(bo_mach):
    """HIER03 — net của board chạm thẳng chân lá nằm trong khối con.

    Không có bất biến này thì mọi lời nói về biên khối là trang trí.
    """
    n = _net(bo_mach, "XUYEN", trong="module:/board", path="/board.XUYEN")
    bo_mach.ckm_noi(net_id=n, port_id="port:leaf:U1.27")
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach))
    x = next((i for i in v if i.ma == C.E_XUYEN_CAP), None)
    assert x is not None, [i.vi for i in v]
    assert "khai một port" in x.goi_y.lower()


def test_E9003_port_bi_hai_net_trong_cung_khoi(bo_mach):
    n = _net(bo_mach, "VDD_I2", trong="module:/board/mcu", path="/board/mcu.VDD_I2")
    bo_mach.ckm_noi(net_id=n, port_id="port:module:/board/mcu.VDD")
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach))
    assert any(x.ma == C.E_PORT_LEN_CHA for x in v), [x.vi for x in v]


def test_E9004_port_la_thieu_va_thua(bo_mach):
    """HIER04 — "không thừa" là chiều quan trọng: một Port thừa làm sơ đồ vẽ chân chip
    KHÔNG có."""
    theo_fact = {"U1": {"7", "27", "28"}}          # bảng chân có 28, cây thì không
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach), chan_theo_fact=theo_fact)
    assert any(x.ma == C.E_PORT_LA and "thiếu" in x.vi for x in v), [x.vi for x in v]

    _port(bo_mach, "leaf:U1", "99", chan="99")
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach), chan_theo_fact={"U1": {"7", "27"}})
    x = next(i for i in v if i.ma == C.E_PORT_LA)
    assert "KHÔNG có" in x.vi and "99" in x.vi


def test_E9004_khong_co_fact_thi_KHONG_KET_LUAN(bo_mach):
    """N6 áp vào phép kiểm: không có bảng chân để so ≠ so và đạt."""
    v = C.kiem_bat_bien(C.Cay.doc(bo_mach), chan_theo_fact={})
    assert not [x for x in v if x.ma == C.E_PORT_LA]


def test_E9005_bus_hai_dau_lech_member(bo_mach):
    s = bo_mach
    a = _port(s, "module:/board/mcu", "I2C0", loai="bus", members=["SDA", "SCL"])
    b = _port(s, "module:/board/pwr", "I2C", loai="bus", members=["SDA"])
    n = _net(s, "I2C", trong="module:/board", path="/board.I2C")
    s.ckm_noi(net_id=n, port_id=a)
    s.ckm_noi(net_id=n, port_id=b)
    v = C.kiem_bat_bien(C.Cay.doc(s))
    assert any(x.ma == C.E_BUS_LECH for x in v), [x.vi for x in v]


# =========================================================================== 3. đóng gói
def test_E9006_sua_trong_khoi_khong_lam_doi_net_ngoai(bo_mach):
    """Đổi net cục bộ trong MCU: flatten bên ngoài phải y nguyên ⇒ đóng gói giữ được."""
    cay0 = C.Cay.doc(bo_mach)
    truoc, bien0 = C.flatten(cay0), C.bien_khoi(cay0, "module:/board/mcu")
    # thêm một điện trở trong khối MCU, nối vào net cục bộ SDA_I
    _khoi(bo_mach, "leaf:R9", "4k7", cha="module:/board/mcu", kind="leaf",
          path="/board/mcu/R9", ref="R9")
    p = _port(bo_mach, "leaf:R9", "1", chan="1")
    bo_mach.ckm_noi(net_id="net:/board/mcu.SDA_I", port_id=p)
    cay1 = C.Cay.doc(bo_mach)
    sau, bien1 = C.flatten(cay1), C.bien_khoi(cay1, "module:/board/mcu")
    assert C.kiem_dong_goi(truoc, sau, trong_khoi={"U1", "R9"},
                           bien_truoc=bien0, bien_sau=bien1) == []
    assert bien0 == bien1 == {"VDD": "3V3", "SDA": "SDA"}


def test_E9006_bat_duoc_khoi_bi_cat_khoi_nguon(bo_mach):
    """Gỡ Port VDD của khối MCU khỏi net 3V3 — khối MẤT NGUỒN.

    Đây là ca đã dạy cho E9006 vế thứ hai: chỉ so `flatten` (đã lọc chân bên trong khối)
    thì `U1.7` bị lọc đi và phép kiểm kết luận "không có gì đổi" — một câu sai về một mạch
    không còn chạy được.
    """
    cay0 = C.Cay.doc(bo_mach)
    truoc, bien0 = C.flatten(cay0), C.bien_khoi(cay0, "module:/board/mcu")
    bo_mach.ckm_xoa_noi(net_id="net:/board.3V3",
                        port_id="port:module:/board/mcu.VDD")
    cay1 = C.Cay.doc(bo_mach)
    sau, bien1 = C.flatten(cay1), C.bien_khoi(cay1, "module:/board/mcu")

    assert C.kiem_dong_goi(truoc, sau, trong_khoi={"U1"}) == [], \
        "chỉ vế flatten thì KHÔNG thấy — đó là lý do có vế biên"
    v = C.kiem_dong_goi(truoc, sau, trong_khoi={"U1"},
                        bien_truoc=bien0, bien_sau=bien1)
    assert any(x.ma == C.E_DONG_GOI for x in v), (bien0, bien1)
    assert "chưa nối" in v[0].vi and "STALE phải lan" in v[0].goi_y


# =========================================================================== 4. độ sâu
def test_canh_bao_do_sau_khong_cam(bo_mach):
    """HIER11 — sâu 6 cấp thì CẢNH BÁO, vẫn hợp lệ. Giới hạn cứng sẽ dạy người dựng cây
    méo để lách."""
    s, cha, path = bo_mach, "module:/board/mcu", "/board/mcu"
    for i in range(1, 5):
        path = f"{path}/l{i}"
        nid = f"module:{path}"
        _khoi(s, nid, f"L{i}", cha=cha, kind="subblock", path=path)
        cha = nid
    cay = C.Cay.doc(s)
    assert C.canh_bao_do_sau(cay).startswith("Cây sâu 6 cấp")
    assert C.kiem_bat_bien(cay) == [], "sâu không phải lỗi"


def test_khong_canh_bao_khi_du_nong(bo_mach):
    assert C.canh_bao_do_sau(C.Cay.doc(bo_mach)) == ""


# =========================================================================== 5. di cư HIER01
def _tac_tu_phang(make_agent):
    """Một dự án làm theo mô hình PHẲNG, đúng như trước HIER-45."""
    from eide.loop import TurnContext

    a = make_agent([])
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}
    for so, ten, af in (("7", "VCC", ""), ("8", "GND", ""), ("27", "PC4", "SDA, ADC4"),
                        ("28", "PC5", "SCL, ADC5")):
        a.store.put_fact({"fact_id": f"f-{so}", "subject": f"pin:ATmega328P.{so}",
                          "key": "ten", "value": ten, "tier": "VANG",
                          "origin": "extract", "source": {}, "explain": {}})
        if af:
            a.store.put_fact({"fact_id": f"f-af-{so}", "subject": f"pin:ATmega328P.{so}",
                              "key": "af", "value": af, "tier": "VANG",
                              "origin": "extract", "source": {}, "explain": {}})

    def goi(cong_cu, /, **kw):
        # Chỉ nhận theo VỊ TRÍ: `ten` và `loai` là tên tham số THẬT của ckm.net_set.
        if "explain" in (a.registry.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", ex)
        ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger,
                          eide_md=a.eide_md, ids=a.ids, registry=a.registry,
                          emit=lambda c: None, history=a.history, run_id="run-1")
        r = a.registry.run(cong_cu, kw, ctx)
        assert r.ok, getattr(r.error, "message_vi", "")
        return r

    goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    goi("ckm.module_set", ma="MOD-MCU", ten="Vi điều khiển", muc_dich="chạy firmware",
        linh_kien=["U1"], tin_hieu_vao=["3V3"], tin_hieu_ra=["SDA", "SCL"], rail="3V3")
    goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn", muc_dich="hạ 5V xuống 3V3",
        linh_kien=["U3"], tin_hieu_ra=["3V3"])
    goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
        chan=[["U1", "7"], ["U3", "3"]])
    goi("ckm.net_set", ten="GND", loai="ground", chan=[["U1", "8"], ["U3", "2"]])
    goi("ckm.net_set", ten="SDA", loai="bus", chan=[["U1", "27"], ["U9", "5"]])
    return a


def _netlist_phang(store) -> dict[str, list[str]]:
    """Netlist phẳng như hiện vật đang ghi — thứ mọi tool cũ đang đọc."""
    a = store.get("netlist:CKM")
    return {n["ten"]: sorted(n.get("chan") or [], key=C._khoa_chan)
            for n in (a["canonical"].get("net") if a else [])}


def test_HIER01_flatten_sau_di_cu_bang_netlist_cu_100(make_agent):
    """Ca HIER01, phần quan trọng nhất của cả bước: *"flatten = netlist cũ 100 %"*.

    Nếu câu này sai thì mọi tool phẳng (ERC, BOM, sim, target) bắt đầu đọc một mạch khác
    với mạch người đã vẽ — và không có bước nào sau đó phát hiện.
    """
    a = _tac_tu_phang(make_agent)
    cu = _netlist_phang(a.store)
    assert cu, "phải có netlist phẳng để so"

    moi = C.flatten(C.Cay.doc(a.store))
    assert moi == cu, f"\ncũ : {cu}\nmới: {moi}"


def test_HIER01_di_cu_dung_cay_va_khong_vi_pham_bat_bien(make_agent):
    a = _tac_tu_phang(make_agent)
    cay = C.Cay.doc(a.store)

    assert cay.goc == C.GOC
    khoi = {cay.nut[x]["path"] for x in cay.khoi_con(C.GOC)}
    assert "/board/MOD-MCU" in khoi and "/board/MOD-PWR" in khoi

    # Lá U1 phải nằm TRONG khối khai nó, không nằm ở gốc.
    u1 = next(n for n in cay.nut.values() if n["ten"] == "ATmega328P")
    assert u1["kind"] == "leaf"
    assert cay.nut[u1["parent_id"]]["path"] == "/board/MOD-MCU"

    v = C.kiem_bat_bien(cay)
    assert v == [], [x.to_dict() for x in v]


def test_HIER01_net_goc_cham_chan_trong_khoi_thi_sinh_Port_len_cha(make_agent):
    """Net 3V3 ở gốc chạm chân U1 nằm trong MOD-MCU. Nối thẳng là vi phạm E9002 — nên di
    cư phải sinh Port ở biên khối cộng một net cục bộ, đúng như §2.3 nói."""
    a = _tac_tu_phang(make_agent)
    cay = C.Cay.doc(a.store)
    mcu = next(n for n in cay.nut.values() if n.get("path") == "/board/MOD-MCU")
    ten_port = {cay.port[p]["ten"] for p in cay.port_cua.get(mcu["node_id"], [])}
    assert {"3V3", "SDA", "GND"} <= ten_port, ten_port
    assert any(n.get("path", "").startswith("/board/MOD-MCU.")
               for n in cay.nut.values() if n["loai"] == "net"), "phải có net cục bộ"


def test_HIER01_di_cu_lam_lai_nhieu_lan_cho_cung_mot_cay(make_agent):
    """`dung_cay` chạy mỗi lần `chieu()` chạy, nên nó phải XÁC ĐỊNH — nếu không, mỗi lần
    ghi một hiện vật là một lần cây đổi hình mà không ai sửa gì."""
    a = _tac_tu_phang(make_agent)
    from eide.knowledge import ckm as K
    lan1 = C.flatten(C.Cay.doc(a.store))
    K.chieu(a.store)
    K.chieu(a.store)
    lan3 = C.flatten(C.Cay.doc(a.store))
    assert lan1 == lan3
    assert C.kiem_bat_bien(C.Cay.doc(a.store)) == []


def test_HIER01_chan_linh_kien_khong_co_bang_chan_van_vao_flatten(make_agent):
    """U9 chỉ được netlist nhắc tới, chưa có datasheet. Nó vẫn phải có mặt trong netlist
    phẳng — bỏ nó đi là làm mạch trông như đã nối đủ."""
    a = _tac_tu_phang(make_agent)
    f = C.flatten(C.Cay.doc(a.store))
    assert "U9.5" in f["SDA"], f["SDA"]


# =========================================================================== 6. công cụ
def _reg(a):
    from eide.loop import TurnContext

    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}

    def goi(cong_cu, /, **kw):
        if "explain" in (a.registry.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", ex)
        ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger,
                          eide_md=a.eide_md, ids=a.ids, registry=a.registry,
                          emit=lambda c: None, history=a.history, run_id="run-1")
        return a.registry.run(cong_cu, kw, ctx)
    return goi


def test_module_set_khoi_con_vao_dung_cho_trong_cay(make_agent):
    a = make_agent([])
    goi = _reg(a)
    assert goi("ckm.module_set", ma="MOD-MCU", ten="MCU", muc_dich="chạy firmware").ok
    r = goi("ckm.module_set", ma="MOD-XTAL", ten="Dao động", muc_dich="16 MHz",
            cha="MOD-MCU")
    assert r.ok and r.data["duong"] == "/board/MOD-MCU/MOD-XTAL"
    assert r.data["kind"] == "subblock"


def test_module_set_cha_khong_co_thi_tu_choi_va_liet_ke_khoi_dang_co(make_agent):
    a = make_agent([])
    goi = _reg(a)
    goi("ckm.module_set", ma="MOD-MCU", ten="MCU", muc_dich="x")
    r = goi("ckm.module_set", ma="MOD-X", ten="X", muc_dich="y", cha="KHONG-CO")
    assert not r.ok and r.error.code == "E2001"
    assert "MOD-MCU" in r.error.hint_for_agent


def test_module_set_tu_lam_cha_cua_chinh_no_bi_tu_choi(make_agent):
    goi = _reg(make_agent([]))
    goi("ckm.module_set", ma="M1", ten="x", muc_dich="y")
    r = goi("ckm.module_set", ma="M1", ten="x", muc_dich="y", cha="M1")
    assert not r.ok and r.error.code == C.E_CHU_TRINH


def test_port_set_khai_hop_dong_cua_khoi(make_agent):
    a = make_agent([])
    goi = _reg(a)
    goi("ckm.module_set", ma="MOD-MCU", ten="MCU", muc_dich="x")
    r = goi("ckm.port_set", khoi="MOD-MCU", ten="VDD", huong="power_in",
            rang_buoc={"v_min": "2.7 V", "v_max": "5.5 V"})
    assert r.ok and r.data["so_port"] == 1
    p = a.store.ckm_cac_port(module_id="module:MOD-MCU")[0]
    assert p["huong"] == "power_in" and p["rang_buoc"]["v_max"] == "5.5 V"
    assert "hợp đồng" in r.data["note_vi"]


def test_port_set_khoi_chua_co_thi_noi_goi_gi_truoc(make_agent):
    r = _reg(make_agent([]))("ckm.port_set", khoi="MOD-X", ten="VDD", huong="in")
    assert not r.ok and r.error.alternatives[0] == "ckm.module_set"


def test_port_bus_khong_ke_thanh_vien_bi_tu_choi(make_agent):
    goi = _reg(make_agent([]))
    goi("ckm.module_set", ma="M1", ten="x", muc_dich="y")
    r = goi("ckm.port_set", khoi="M1", ten="I2C0", huong="bidir", loai="bus")
    assert not r.ok and r.error.code == C.E_BUS_LECH
    assert "members" in r.error.hint_for_agent


def test_net_trong_khoi_va_noi_qua_port(make_agent):
    """Dựng cây THẬT: net của mạch nối Port của khối, không chạm chân bên trong."""
    a = make_agent([])
    goi = _reg(a)
    goi("ckm.module_set", ma="PWR", ten="Nguồn", muc_dich="3V3", tin_hieu_ra=["3V3"])
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="firmware")
    goi("ckm.port_set", khoi="PWR", ten="VOUT", huong="power_out")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="power_in")
    r = goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
            noi_port=[["PWR", "VOUT"], ["MCU", "VDD"]])
    assert r.ok, getattr(r.error, "message_vi", "")
    cay = C.Cay.doc(a.store)
    assert len(cay.noi.get("net:3V3", [])) == 2
    assert C.kiem_bat_bien(cay) == []


def test_build_noi_ra_vi_pham_va_KHONG_cho_sinh_so_do(make_agent):
    """Đủ tiền đề nhưng cây lệch thì `du_de_sinh_so_do` phải là False.

    Một cái cây có net đi xuyên cấp làm `flatten` ra một mạch KHÁC mạch người vẽ, và mọi
    thứ hạ nguồn đọc cái sai đó mà không biết.
    """
    a = make_agent([])
    goi = _reg(a)
    for so, ten in (("7", "VCC"), ("27", "PC4")):
        a.store.put_fact({"fact_id": f"f{so}", "subject": f"pin:ATmega328P.{so}",
                          "key": "ten", "value": ten, "tier": "VANG", "origin": "extract",
                          "source": {}, "explain": {}})
    goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="x", linh_kien=["U1"])
    goi("ckm.net_set", ten="VDD", loai="power", chan=[["U1", "7"]])
    r = goi("ckm.build")
    assert r.ok and r.data["du_de_sinh_so_do"] is False
    # Chưa ghim hộ chiếu ⇒ thiếu chip; nhưng cây thì không vi phạm gì.
    assert r.data["vi_pham_bat_bien"] == [], r.data["vi_pham_bat_bien"]
    assert "cay" in a.store.get("CKM-1")["canonical"]
    assert r.data["so_net_phang"] >= 1


def test_graph_hien_cay_dang_chu(make_agent):
    a = make_agent([])
    goi = _reg(a)
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="x")
    goi("ckm.module_set", ma="XTAL", ten="Dao động", muc_dich="y", cha="MCU")
    r = goi("ckm.graph")
    assert r.ok
    assert any("/board/MCU/XTAL" in d for d in r.data["cay"]), r.data["cay"]
    assert r.data["cay"][0].startswith("/board")


def test_khoi_con_khong_tinh_la(bo_mach):
    """Một hàm tên "khối con" mà trả về cả lá làm mọi phép đếm dùng nó lệch âm thầm.

    Đo trên bộ E2E: gốc có hai khối + một lá (linh kiện chỉ netlist biết, chưa khối nào
    nhận), và phép đếm khối trả về 3.
    """
    _khoi(bo_mach, "leaf:J1", "Đầu nối", cha="module:/board", kind="leaf",
          path="/board/J1", ref="J1")
    cay = C.Cay.doc(bo_mach)
    assert len(cay.khoi_con("module:/board")) == 2
    assert len(cay.con_truc_tiep("module:/board")) == 3


def test_net_cham_port_cua_LA_con_truc_tiep_van_hop_le(bo_mach):
    """Phạm vi tính theo con TRỰC TIẾP, và lá cũng là con trực tiếp — một net ở gốc chạm
    chân một linh kiện nằm ngay ở gốc thì hợp lệ."""
    _khoi(bo_mach, "leaf:J1", "Đầu nối", cha="module:/board", kind="leaf",
          path="/board/J1", ref="J1")
    p = _port(bo_mach, "leaf:J1", "1", chan="1")
    n = _net(bo_mach, "VIN", trong="module:/board", path="/board.VIN")
    bo_mach.ckm_noi(net_id=n, port_id=p)
    assert [x for x in C.kiem_bat_bien(C.Cay.doc(bo_mach)) if x.ma == C.E_XUYEN_CAP] == []


def test_net_khai_ca_noi_port_va_chan_thi_KHONG_mat_chan(make_agent):
    """Hai cách khai là hai MỨC CHI TIẾT của cùng một net, không phải hai net.

    Trước khi sửa, `_noi_net` bỏ qua net nào đã có kết nối Port — nên một net khai cả
    `noi_port` (biên khối) lẫn `chan` (chân linh kiện) mất hẳn phần chân, và netlist phẳng
    thiếu `U1.7` mà không ai biết.
    """
    a = _tac_tu_phang(make_agent)
    from eide.loop import TurnContext
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}
    ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger, eide_md=a.eide_md,
                      ids=a.ids, registry=a.registry, emit=lambda c: None,
                      history=a.history, run_id="run-2")
    a.registry.run("ckm.port_set", {"khoi": "MOD-MCU", "ten": "VDD",
                                    "huong": "power_in", "explain": ex}, ctx)
    r = a.registry.run("ckm.net_set", {"ten": "3V3", "loai": "power",
                                       "chan": [["U1", "7"], ["U3", "3"]],
                                       "noi_port": [["MOD-MCU", "VDD"]],
                                       "explain": ex}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    f = C.flatten(C.Cay.doc(a.store))
    assert "U1.7" in f["3V3"] and "U3.3" in f["3V3"], f


def test_di_cu_dung_lai_Port_nguoi_da_khai_thay_vi_sinh_Port_trung_vai(make_agent):
    """Người khai `VDD`; sinh thêm một Port `3V3` bên cạnh là làm hợp đồng của khối có hai
    cửa cho cùng một đường."""
    a = _tac_tu_phang(make_agent)
    from eide.loop import TurnContext
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}
    ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger, eide_md=a.eide_md,
                      ids=a.ids, registry=a.registry, emit=lambda c: None,
                      history=a.history, run_id="run-2")
    a.registry.run("ckm.port_set", {"khoi": "MOD-MCU", "ten": "VDD",
                                    "huong": "power_in", "explain": ex}, ctx)
    a.registry.run("ckm.net_set", {"ten": "3V3", "loai": "power",
                                    "chan": [["U1", "7"]],
                                    "noi_port": [["MOD-MCU", "VDD"]],
                                    "explain": ex}, ctx)
    ten = {p["ten"] for p in a.store.ckm_cac_port(module_id="module:MOD-MCU")}
    assert "VDD" in ten
    assert "3V3" not in ten, f"không được sinh Port trùng vai: {sorted(ten)}"
