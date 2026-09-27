# -*- coding: utf-8 -*-
"""Ca đo cho Bản đồ tri thức mạch — MDD-40 §C2, tiền đề của SCH-44 §4.

Thứ tự các nhóm ở đây là thứ tự "chỗ nào sai thì tệ nhất":

  1. không bịa chân      — sai ở đây thì mạch hàn xong không chạy và không ai biết vì sao
  2. ĐƯỢC_GÁN duy nhất   — sai ở đây thì hai chức năng tranh một chân, im lặng
  3. hình chiếu & hoàn tác — sai ở đây thì bản đồ và hiện vật nói hai chuyện khác nhau
  4. suy ra luồng tín hiệu — sai ở đây thì hình vẽ đẹp mà vô nghĩa
"""

from __future__ import annotations

import sqlite3

import pytest

from eide.knowledge import ckm as K
from eide.store import Store


# --------------------------------------------------------------------------- dàn dựng
def fact_chan(chip: str, chan: str, *, ten: str = "", af: str = "",
              tier: str = "VANG") -> list[dict]:
    ra = []
    if ten:
        ra.append({"fact_id": f"f-{chip}-{chan}-ten", "subject": f"pin:{chip}.{chan}",
                   "key": "ten", "value": ten, "tier": tier, "origin": "extract",
                   "source": {}, "explain": {"summary": ten}})
    if af:
        ra.append({"fact_id": f"f-{chip}-{chan}-af", "subject": f"pin:{chip}.{chan}",
                   "key": "af", "value": af, "tier": tier, "origin": "extract",
                   "source": {}, "explain": {"summary": af}})
    return ra


@pytest.fixture
def kho(tmp_path) -> Store:
    s = Store(tmp_path / "k.sqlite")
    for f in (fact_chan("ATmega328P", "27", ten="PC4", af="SDA, ADC4")
              + fact_chan("ATmega328P", "28", ten="PC5", af="SCL, ADC5")
              + fact_chan("ATmega328P", "7", ten="VCC")):
        s.put_fact(f)
    return s


EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "VANG"}


# =========================================================================== 1. bảng chân
def test_chan_doc_tu_fact_khong_do_mo_hinh_khai(kho):
    chan = K.chan_tu_fact(kho.query_facts(subject="pin:ATmega328P.", limit=100),
                          "ATmega328P")
    assert set(chan) == {"27", "28", "7"}
    assert chan["27"].ten == "PC4"
    assert chan["27"].af == ["SDA", "ADC4"], "AF tách được cả dấu phẩy"


def test_af_tach_duoc_ca_gach_cheo():
    assert K._tach_af("AF7/AF1") == ["AF7", "AF1"]
    assert K._tach_af(None) == []


def test_tang_cua_chan_la_tang_thap_nhat(kho):
    """Tên chân ở VÀNG mà AF chỉ ở ĐỒNG thì chân KHÔNG phải chân VÀNG.

    Vì cái đang gán là AF. Lấy tầng cao nhất ở đây sẽ biến một phỏng đoán thành một
    con số có nền vàng nhạt trên màn hình.
    """
    kho.put_fact({"fact_id": "f-x", "subject": "pin:X.1", "key": "ten", "value": "PA1",
                  "tier": "VANG", "origin": "extract", "source": {}, "explain": {}})
    kho.put_fact({"fact_id": "f-y", "subject": "pin:X.1", "key": "af", "value": "TIM1_CH1",
                  "tier": "DONG", "origin": "model", "source": {}, "explain": {}})
    chan = K.chan_tu_fact(kho.query_facts(subject="pin:X.", limit=100), "X")
    assert chan["1"].tier == "DONG"


def test_chan_khong_co_trong_bang_bi_tu_choi(kho):
    co = K.chan_tu_fact(kho.query_facts(subject="pin:ATmega328P.", limit=100), "ATmega328P")
    kq = K.kiem_chan("99", co, chip="ATmega328P")
    assert not kq.dat and kq.ma_loi == "E8003"
    assert "không có chân 99" in kq.vi
    assert "27" in kq.vi, "phải liệt kê chân CÓ THẬT để người sửa được"


def test_chua_nap_bang_chan_khac_voi_chan_khong_ton_tai():
    """Hai câu trả lời khác nhau ⇒ hai việc phải làm khác nhau. Không được gộp."""
    kq = K.kiem_chan("27", {}, chip="ATmega328P")
    assert not kq.dat and kq.ma_loi == "E8002"
    assert "fact.extract" in kq.goi_y or "fact.assert_human" in kq.goi_y


def test_chan_tang_dong_khong_vao_ban_do():
    c = K.ChanCKM(chan="5", ten="PB5", af=["MOSI"], tier="DONG")
    kq = K.kiem_chan("5", {"5": c}, chip="X")
    assert not kq.dat and kq.ma_loi == "E8006"
    assert "phỏng đoán" in kq.vi


def test_chan_tang_cauhinh_cung_khong_vao_ban_do():
    """CẤU HÌNH nói dự án ĐANG ĐẶT gì, không nói chip LÀM ĐƯỢC gì (xem DEV-263)."""
    c = K.ChanCKM(chan="5", tier="CAUHINH")
    assert not K.kiem_chan("5", {"5": c}, chip="X").dat


def test_chan_tang_nguoi_thi_dung_duoc():
    c = K.ChanCKM(chan="5", ten="PB5", af=["MOSI"], tier="NGUOI")
    assert K.kiem_chan("5", {"5": c}, chip="X").dat


def test_af_sai_bi_tu_choi_va_goi_y_cai_gan_giong():
    c = K.ChanCKM(chan="27", af=["SDA", "ADC4"])
    kq = K.kiem_af("SCL", c)
    assert not kq.dat and kq.ma_loi == "E8007"
    assert "SDA" in kq.vi


def test_khong_co_danh_sach_af_thi_noi_KHONG_KIEM_DUOC_chu_khong_noi_dat():
    """N6 áp lên chính phép kiểm: thiếu dữ liệu để kiểm ≠ kiểm và đạt."""
    kq = K.kiem_af("SDA", K.ChanCKM(chan="27"))
    assert kq.dat is True, "không chặn — vì không có cơ sở để chặn"
    assert kq.chi_tiet["kiem_duoc"] is False
    assert "không kiểm được" in kq.chi_tiet["vi"]


# =========================================================================== 2. luồng tín hiệu
def test_canh_suy_ra_tu_ten_tin_hieu():
    ms = [K.Module(ma="A", ten="Nguồn", tin_hieu_ra=["3V3"]),
          K.Module(ma="B", ten="MCU", tin_hieu_vao=["3V3"], tin_hieu_ra=["SDA"])]
    c = K.canh_giua_module(ms)
    assert {"tu": "A", "den": "B", "tin_hieu": "3V3"} in c
    assert len(c) == 1


def test_ten_tin_hieu_lech_nhau_thi_mui_ten_MAT_chu_khong_duoc_noi_lien():
    """Đây là giá trị của việc suy cạnh bằng mã: sai tên thì hình vẽ TỐ GIÁC."""
    ms = [K.Module(ma="A", tin_hieu_ra=["VDD_3V3"], ten="Nguồn"),
          K.Module(ma="B", tin_hieu_vao=["3V3"], ten="MCU")]
    assert K.canh_giua_module(ms) == []
    treo = K.tin_hieu_treo(ms)
    assert treo["vao_khong_ai_cap"] == ["3V3"]
    assert treo["ra_khong_ai_dung"] == ["VDD_3V3"]


def test_mermaid_xac_dinh(tmp_path):
    """N3: cùng bản đồ ⇒ cùng một chữ, mọi lần. SCH17 đòi bố cục xác định."""
    ms = [K.Module(ma="B", ten="MCU", tin_hieu_vao=["3V3"]),
          K.Module(ma="A", ten="Nguồn", tin_hieu_ra=["3V3"])]
    assert K.mermaid(ms) == K.mermaid(list(reversed(ms)))
    assert "graph LR" in K.mermaid(ms)


def test_mermaid_hien_ca_cho_chua_noi():
    ms = [K.Module(ma="B", ten="MCU", tin_hieu_vao=["3V3"])]
    assert "?" in K.mermaid(ms), "tín hiệu chưa ai cấp phải THẤY được trên hình"


def test_bang_khoi_co_du_bay_cot():
    assert K.bang_khoi([K.Module(ma="A", ten="x", muc_dich="y")]).count("|") > 14
    assert "Chưa có khối nào" in K.bang_khoi([])


# =========================================================================== 3. kho & chỉ mục
def test_duoc_gan_duy_nhat_do_KHO_chan_khong_phai_do_loi_nhac(kho):
    """§C2 ghi ĐƯỢC_GÁN "(duy nhất)". Luật nằm trong chỉ mục UNIQUE của SQLite."""
    kho.ckm_dat_nut(node_id="pin:X.1", loai="pin", ten="1", canonical={})
    kho.ckm_dat_canh(loai="DUOC_GAN", tu="pin:X.1", den="chuc_nang:SDA")
    with pytest.raises(sqlite3.IntegrityError):
        kho.ckm_dat_canh(loai="DUOC_GAN", tu="pin:X.1", den="chuc_nang:SCL")


def test_canh_khac_thi_gan_bao_nhieu_lan_cung_duoc(kho):
    """Một net nối nhiều chân là chuyện thường — chỉ ĐƯỢC_GÁN mới là duy nhất."""
    kho.ckm_dat_canh(loai="NOI", tu="net:SDA", den="pin:X.1")
    kho.ckm_dat_canh(loai="NOI", tu="net:SDA", den="pin:Y.2")
    assert len(kho.ckm_cac_canh(loai="NOI", tu="net:SDA")) == 2


def test_ghi_lai_cung_canh_khong_nhan_doi(kho):
    kho.ckm_dat_canh(loai="NOI", tu="net:A", den="pin:X.1")
    kho.ckm_dat_canh(loai="NOI", tu="net:A", den="pin:X.1", canonical={"x": 1})
    assert len(kho.ckm_cac_canh(loai="NOI")) == 1


def test_luoc_do_v2_go_duoc_va_khong_cham_bang_cu(kho):
    """SCH-18: migration cộng thêm phải có đường lui, và lui không được xoá dữ liệu cũ."""
    kho.ckm_dat_nut(node_id="pin:X.1", loai="pin", ten="1", canonical={})
    assert kho.ha_cap(1) == [4, 3, 2], ("hạ tới v1 phải gỡ từ bậc cao xuống: sổ sheet (v4), "
                                       "cây (v3), rồi CKM (v2)")
    assert kho.query_facts(limit=5), "hạ CKM không được chạm bảng facts"
    with pytest.raises(sqlite3.OperationalError):
        kho.ckm_cac_nut()
    assert kho.nang_cap() == [2, 3, 4]
    assert kho.ckm_cac_nut() == [], "lên lại thì bảng rỗng, không phải dữ liệu cũ"


# =========================================================================== 4. công cụ
def _ctx(agent):
    from eide.loop import TurnContext
    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


@pytest.fixture
def tac_tu(make_agent):
    a = make_agent([])
    for f in (fact_chan("ATmega328P", "27", ten="PC4", af="SDA, ADC4")
              + fact_chan("ATmega328P", "28", ten="PC5", af="SCL, ADC5")
              + fact_chan("ATmega328P", "7", ten="VCC")):
        a.store.put_fact(f)
    return a


def _goi(agent, /, cong_cu, **kw):
    """Gọi một công cụ. Hai tham số đầu chỉ nhận theo VỊ TRÍ — vì `ten` và `loai` là tên
    tham số THẬT của ckm.net_set, và một hàm trợ giúp không được chiếm tên của thứ nó gọi."""
    spec = agent.registry.get(cong_cu)
    if "explain" in (spec.params.get("properties") or {}):
        kw.setdefault("explain", EX)
    return agent.registry.run(cong_cu, kw, _ctx(agent))


def test_chip_add_khong_co_fact_thi_tu_choi_va_chi_duong(make_agent):
    r = _goi(make_agent([]), "ckm.chip_add", chip="STM32F103")
    assert not r.ok and r.error.code == "E8002"
    assert "fact.extract" in r.error.hint_for_agent
    assert "pin:STM32F103.<số>" in r.error.hint_for_agent, \
        "phải nói CHÍNH XÁC chủ đề Fact cần ghi, không chỉ nói 'nạp datasheet'"


def test_chip_add_dua_chan_vao_ban_do(tac_tu):
    r = _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    assert r.ok and r.data["so_chan_vao_ban_do"] == 3
    # Chân khoá theo REF, không theo tên chip — xem docstring của `K.ma_pin`.
    assert tac_tu.store.ckm_nut("pin:U1.27") is not None
    assert tac_tu.store.ckm_nut("pin:ATmega328P.27") is None
    assert tac_tu.store.ckm_cac_canh(loai="CO_CHAN", tu="chip:U1")


def test_chip_add_bo_chan_tang_dong_nhung_NOI_RA(tac_tu):
    tac_tu.store.put_fact({"fact_id": "f-d", "subject": "pin:ATmega328P.13", "key": "af",
                           "value": "PWM?", "tier": "DONG", "origin": "model",
                           "source": {}, "explain": {}})
    r = _goi(tac_tu, "ckm.chip_add", chip="ATmega328P")
    assert r.ok and r.data["chan_bo_qua"] == ["13 (tầng DONG)"]
    assert "BỎ QUA" in r.data["note_vi"], "bản đồ thiếu chân mà im lặng thì trông như đủ"
    assert tac_tu.store.ckm_nut("pin:ATmega328P.13") is None, "chân ĐỒNG không vào bản đồ"


def test_pinout_khong_bia_chan(tac_tu):
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="99", chuc_nang="SDA")
    assert not r.ok and r.error.code == "E8003"


def test_pinout_tu_choi_chuc_nang_khong_co_trong_AF(tac_tu):
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SCL")
    assert not r.ok and r.error.code == "E8007"
    assert "SDA" in r.error.message_vi


def test_pinout_gan_duoc_va_ghi_hien_vat(tac_tu):
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA",
             net="SDA")
    assert r.ok and r.data["so_chan_da_gan"] == 1
    a = tac_tu.store.get("pinout:ATmega328P")
    assert a["canonical"]["gan"][0]["chuc_nang"] == "SDA"
    assert tac_tu.store.ckm_cac_canh(loai="DUOC_GAN", tu="pin:ATmega328P.27"), \
        "chưa có ref thì tên chip đóng cả hai vai"


def test_pinout_gan_trung_bi_tu_choi_kem_cai_da_gan(tac_tu):
    _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="ADC4")
    assert not r.ok and r.error.code == "E8004"
    assert "SDA" in r.error.message_vi, "phải nói chân đang làm GÌ, để người cân nhắc được"
    assert r.error.details["gan_truoc"] == "SDA"


def test_pinout_gan_lai_duoc_khi_noi_ro_vi_sao(tac_tu):
    _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="ADC4",
             thay_the=True, vi_sao="anh chuyển I2C sang chân khác")
    assert r.ok and r.data["so_chan_da_gan"] == 1
    assert "thay cho SDA" in r.data["note_vi"]


def test_pinout_gan_lai_ma_khong_noi_vi_sao_bi_tu_choi(tac_tu):
    _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="ADC4",
             thay_the=True)
    assert not r.ok and "vì sao" in r.error.message_vi


def test_pinout_chan_khong_co_AF_thi_gan_duoc_nhung_canh_bao(tac_tu):
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="7", chuc_nang="VCC")
    assert r.ok
    assert any("không kiểm được" in c for c in r.data["canh_bao"])
    assert tac_tu.store.get("pinout:ATmega328P")["canonical"]["gan"][0][
        "af_kiem_duoc"] is False


def test_module_set_suy_canh_va_tu_ve(tac_tu):
    _goi(tac_tu, "ckm.module_set", ma="MOD-PWR", ten="Nguồn", muc_dich="hạ 5V xuống 3V3",
         tin_hieu_ra=["3V3"])
    r = _goi(tac_tu, "ckm.module_set", ma="MOD-MCU", ten="Vi điều khiển",
             muc_dich="chạy firmware", tin_hieu_vao=["3V3"], rail="3V3")
    assert r.ok and r.data["so_khoi"] == 2
    assert r.data["canh_suy_ra"] == [{"tu": "MOD-PWR", "den": "MOD-MCU", "tin_hieu": "3V3"}]
    a = tac_tu.store.get("MG-1")
    assert "graph LR" in a["view_hint"]["text"], "dạng người sinh sẵn, 0 token khi xem"


def test_module_set_noi_ra_REQ_khong_co_trong_kho(tac_tu):
    r = _goi(tac_tu, "ckm.module_set", ma="M1", ten="x", muc_dich="y",
             dap_ung_req=["FR-99"])
    assert r.ok and r.data["req_khong_co_trong_kho"] == ["FR-99"]
    assert "đừng tự tạo" in r.data["note_vi"]


def test_diagram_render_tu_choi_khi_chua_co_khoi_va_noi_goi_gi(tac_tu):
    r = _goi(tac_tu, "diagram.render")
    assert not r.ok and r.error.code == "E2001"
    assert r.error.alternatives == ["ckm.module_set"]


def test_net_set_tu_choi_chan_khong_co_that(tac_tu):
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    r = _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus", chan=[["U1", "99"]])
    assert not r.ok and r.error.code == "E8003"


def test_net_set_chan_linh_kien_thu_dong_KHONG_KIEM_DUOC_chu_khong_chan(tac_tu):
    r = _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus", chan=[["R1", "1"]])
    assert r.ok
    assert any("KHÔNG kiểm được" in c for c in r.data["canh_bao"])


def test_net_mot_chan_bi_goi_ten(tac_tu):
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    r = _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus", chan=[["U1", "27"]])
    assert r.ok and any("MỘT chân" in c for c in r.data["canh_bao"])


def test_import_netlist_doan_loai_va_noi_ra_la_doan(tac_tu):
    tac_tu.store.apply(artefact_id="netlist:hw/b.net", type="netlist", op="create",
                       author="human", explain=EX,
                       canonical={"linh_kien": [{"ref": "U1", "gia_tri": "ATmega328P"}],
                                  "net": [{"ten": "GND", "chan": ["U1.8"]},
                                          {"ten": "SDA", "chan": ["U1.27", "U2.5"]}]})
    r = _goi(tac_tu, "ckm.import_netlist", netlist_id="netlist:hw/b.net")
    assert r.ok and r.data["so_net"] == 2
    assert "ĐOÁN" in r.data["note_vi"]
    nets = {n["ten"]: n for n in tac_tu.store.get("netlist:CKM")["canonical"]["net"]}
    assert nets["GND"]["loai"] == "ground" and nets["SDA"]["loai"] == "bus"
    assert nets["GND"]["loai_do_doan"] is True


def test_import_netlist_vao_chinh_no_bi_tu_choi(tac_tu):
    _goi(tac_tu, "ckm.net_set", ten="GND", loai="ground")
    r = _goi(tac_tu, "ckm.import_netlist", netlist_id="netlist:CKM")
    assert not r.ok and "chính nó" in r.error.message_vi


def test_build_noi_ro_thieu_gi_va_KHONG_no(tac_tu):
    r = _goi(tac_tu, "ckm.build")
    assert r.ok and r.data["du_de_sinh_so_do"] is False
    thieu = {t["loai"] for t in r.data["thieu"]}
    assert thieu == {"block", "net", "chip_co_ho_chieu"}, \
        "khối đếm theo kind; chip đếm theo HỘ CHIẾU, không theo nút chip"
    assert "ckm.module_set" in r.data["note_vi"]


def test_build_chip_chua_ghim_ho_chieu_thi_CHUA_du(tac_tu):
    """Tiền đề "hộ chiếu chip đã ghim" không được tự thoả bởi `ckm.chip_add`.

    SCH-44 §4 đòi `passport`; một chip chưa ghim là chip chưa ai đối chiếu với tài liệu
    nào. Trước khi sửa, tiền đề này đếm nút `chip` nên nó tự đúng.
    """
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.module_set", ma="M1", ten="MCU", muc_dich="chạy firmware")
    _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus", chan=[["U1", "27"], ["U1", "28"]])
    r = _goi(tac_tu, "ckm.build")
    assert r.ok and r.data["du_de_sinh_so_do"] is False
    assert [t["goi"] for t in r.data["thieu"]] == ["passport.pin"]


def test_build_du_tien_de_thi_noi_du(tac_tu):
    tac_tu.store.apply(artefact_id="DS-328P", type="doc", op="create", author="human",
                       explain=EX, canonical={"ten": "datasheet"})
    _goi(tac_tu, "passport.pin", chip="ATmega328P", doc_ids=["DS-328P"])
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.module_set", ma="M1", ten="MCU", muc_dich="chạy firmware")
    _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus",
         chan=[["U1", "27"], ["U1", "28"]])
    r = _goi(tac_tu, "ckm.build")
    assert r.ok and r.data["du_de_sinh_so_do"] is True, r.data["note_vi"]
    assert r.data["cho_dut"]["so_chan_chua_gan"] == 3
    assert "chưa gán" in r.data["note_vi"]


# =========================================================================== 5. hình chiếu
def test_ban_do_la_hinh_chieu_hoan_tac_thi_ban_do_lui_theo(tac_tu):
    """N9: lùi hiện vật mà đồ thị còn giữ chân đã gán thì hai nơi nói hai chuyện khác nhau."""
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA")
    assert tac_tu.store.ckm_cac_canh(loai="DUOC_GAN")

    kq = tac_tu.history.hoan_tac_changeset(r.data["changeset"])
    assert kq.ok, kq.message_vi
    assert tac_tu.store.ckm_cac_canh(loai="DUOC_GAN") == [], \
        "hoàn tác rồi mà bản đồ vẫn còn chân đã gán ⇒ bản đồ đang nói dối"


def test_chieu_lai_tu_hien_vat_cho_ket_qua_y_nguyen(tac_tu):
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA", net="SDA")
    _goi(tac_tu, "ckm.module_set", ma="M1", ten="MCU", muc_dich="x", rail="3V3")
    truoc = tac_tu.store.ckm_dem()
    assert K.chieu(tac_tu.store) == truoc, "dựng lại phải cho đúng cái đang có (CX16)"


def test_hien_vat_pinout_hai_lan_gan_cung_chan_thi_chieu_NO(tac_tu):
    """Nếu hiện vật hỏng thì việc dựng lại phải NỔ, không được im lặng chọn một cái.

    Chọn hộ người dùng một quyết định thiết kế là việc tệ hơn một sự cố nhìn thấy được.
    """
    tac_tu.store.apply(artefact_id="pinout:X", type="pinout", op="create", author="human",
                       explain=EX,
                       canonical={"chip": "X", "gan": [{"chan": "1", "chuc_nang": "SDA"},
                                                       {"chan": "1", "chuc_nang": "SCL"}]})
    with pytest.raises(sqlite3.IntegrityError):
        K.chieu(tac_tu.store)


# =========================================================================== 6. nhiều con cùng loại
def test_hai_con_cung_loai_khong_de_len_nhau(tac_tu):
    """Bo mạch có hai ATmega328P: gán chân cho U1 không được hiện ra ở U2.

    Ca này là lý do `ma_pin` khoá theo ref. Khi khoá theo tên chip, hai con dùng cùng một
    tập nút chân, nên `ĐƯỢC_GÁN duy nhất` sẽ CHẶN việc gán chân 27 của con thứ hai — một
    lời từ chối hoàn toàn vô nghĩa với người đang vẽ mạch.
    """
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U2")
    assert _goi(tac_tu, "ckm.pinout_set", chip="U1", chan="27", chuc_nang="SDA").ok
    r = _goi(tac_tu, "ckm.pinout_set", chip="U2", chan="27", chuc_nang="SDA")
    assert r.ok, "chân 27 của con KHÁC là một chân khác"
    assert len(tac_tu.store.ckm_cac_canh(loai="DUOC_GAN")) == 2


def test_hai_con_cung_loai_goi_bang_ten_chip_thi_HOI_chu_khong_doan(tac_tu):
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U2")
    r = _goi(tac_tu, "ckm.pinout_set", chip="ATmega328P", chan="27", chuc_nang="SDA")
    assert not r.ok and r.error.code == "E8008"
    assert r.error.details["ref"] == ["U1", "U2"]
    assert "lúc hàn" in r.error.hint_for_agent


def test_net_noi_chan_theo_ref_thi_khong_sinh_chan_trung(tac_tu):
    """Trước khi sửa: net sinh thêm `pin:U1.27` bên cạnh `pin:ATmega328P.27`, và bản đồ
    đếm 5 chân trên một chip có 3."""
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus", chan=[["U1", "27"], ["U1", "28"]])
    assert len(tac_tu.store.ckm_cac_nut(loai="pin")) == 3
    r = _goi(tac_tu, "ckm.build")
    assert r.data["cho_dut"]["so_chan_chua_gan"] == 3


def test_chan_chua_gan_khong_gop_voi_chan_khong_co_bang_chan(tac_tu):
    """Hai loại hở khác nhau ⇒ hai việc khác nhau. Gộp lại là thúc người đi gán chân cho
    một linh kiện họ chưa có datasheet — đúng chỗ N1 cấm.

    Đo trên bộ E2E: bo có ATmega328P (5 chân đã nạp) cộng một cảm biến chưa có tài liệu,
    `ckm.build` báo "6 chân chưa gán chức năng" trong khi chỉ 2 chân là việc làm được.
    """
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.pinout_set", chip="U1", chan="27", chuc_nang="SDA")
    _goi(tac_tu, "ckm.net_set", ten="SDA", loai="bus",
         chan=[["U1", "27"], ["U2", "5"], ["U2", "6"]])
    d = _goi(tac_tu, "ckm.build").data["cho_dut"]
    assert d["chan_chua_gan"] == ["U1.28", "U1.7"]
    assert d["chan_khong_co_bang_chan"] == ["U2.5", "U2.6"]
    assert d["so_chan_chua_gan"] == 2


def test_gan_chan_khi_DA_co_so_do_khoi_thi_khong_no(tac_tu):
    """Ca này canh một lỗi mà ca đơn vị cũ KHÔNG thấy được.

    `_ghi_stale_nut` trả về rỗng ngay khi chưa có hiện vật sơ đồ khối — nên mọi ca gán chân
    trước đây không bao giờ đi tới phép lan STALE. Khi `lan_stale` được làm cho NỔ với id
    lạ, `pinout_set` vẫn gọi nó bằng một id đoán (`linh_kien:U1` trong khi nút thật là
    `chip:U1`), và chỉ bộ E2E — nơi có sơ đồ khối — mới đỏ.

    Bài học: một đường về sớm là một đoạn mã KHÔNG được ca đo nào đi qua.
    """
    _goi(tac_tu, "ckm.chip_add", chip="ATmega328P", ref="U1")
    _goi(tac_tu, "ckm.module_set", ma="MOD-MCU", ten="MCU", muc_dich="x",
         linh_kien=["U1"])
    r = _goi(tac_tu, "ckm.pinout_set", chip="U1", chan="27", chuc_nang="SDA")
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["stale_theo_nut"], "phải lan STALE lên theo đường Port"


def test_fact_query_NOI_RA_khi_bi_cat_bot(kho):
    """Cắt im lặng ở 100 dòng rồi trả `count: 100` là một câu trả lời thiếu dữ liệu mà không
    có dấu hiệu nào cho thấy nó thiếu — N6 áp vào một phép tra."""
    for i in range(130):
        kho.put_fact({"fact_id": f"f{i}", "subject": f"pin:X.{i}", "key": "ten",
                      "value": f"P{i}", "tier": "BAC", "origin": "extract",
                      "source": {}, "explain": {}})
    assert kho.dem_fact(subject="pin:X.") == 130
    assert len(kho.query_facts(subject="pin:X.", limit=100)) == 100
    assert len(kho.query_facts(subject="pin:X.", limit=200)) == 130
