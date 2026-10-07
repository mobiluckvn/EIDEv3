# -*- coding: utf-8 -*-
"""ERC theo cây — EIDE-HIER-45 §4.2. Ca HIER06, HIER07, HIER08.

Bốn ràng buộc, và bộ này xếp ca theo mức độ "sai mà vẫn chạy":

  ngân sách dòng  mạch chạy lúc nhẹ tải rồi sụt áp khi đủ tải — rất khó truy
  trùng địa chỉ   bus vẫn ACK, mã vẫn đọc ra số, số của con nào thì không ai biết
  hai cụm pull-up bus CHẠY nhưng sườn sai ở tốc độ cao — tìm cả tuần
  mức logic       thường chết hẳn, nên dễ nhất trong bốn cái

Ca quan trọng nhất không phải bốn cái trên: đó là **"thiếu Fact thì nói chưa đủ dữ kiện"**.
Một ERC đoán nốt phần thiếu thì tệ hơn không có ERC.
"""

from __future__ import annotations

import pytest

from eide.knowledge import cay as C
from eide.knowledge import erc as E
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


def _port(s, module_id, ten, *, huong="passive", chan=None, path=""):
    pid = f"port:{path or module_id}.{ten}"
    s.ckm_dat_port(port_id=pid, module_id=module_id, ten=ten, huong=huong, chan=chan)
    return pid


def _fact(s, subject, key, value, *, unit="", tier="VANG", fid=None):
    s.put_fact({"fact_id": fid or f"f-{subject}-{key}", "subject": subject, "key": key,
                "value": value, "unit": unit, "tier": tier, "origin": "extract",
                "source": {"doc_id": "DS", "page": 7},
                "explain": {"summary": f"{key}={value}"}})


@pytest.fixture
def bo(tmp_path) -> Store:
    """Bo hai khối: nguồn LDO cấp 3V3 cho MCU và cảm biến I2C.

        /board
          ├── pwr   (U3 LDO)     Port VOUT power_out
          ├── mcu   (U1)         Port VDD power_in, SDA
          └── sense (U2 TMP102, R1 pull-up)
    """
    s = Store(tmp_path / "k.sqlite")
    _nut(s, "module:/board", "Bo", loai="module", cha=None, kind="board", path="/board")
    for ma in ("pwr", "mcu", "sense"):
        _nut(s, f"module:/board/{ma}", ma, loai="module", cha="module:/board",
             kind="block", path=f"/board/{ma}")
    _nut(s, "leaf:U3", "AMS1117", loai="linh_kien", cha="module:/board/pwr", kind="leaf",
         path="/board/pwr/U3", ref="U3")
    _nut(s, "leaf:U1", "ATmega328P", loai="linh_kien", cha="module:/board/mcu",
         kind="leaf", path="/board/mcu/U1", ref="U1")
    _nut(s, "leaf:U2", "TMP102", loai="linh_kien", cha="module:/board/sense", kind="leaf",
         path="/board/sense/U2", ref="U2")
    _nut(s, "leaf:R1", "4k7", loai="linh_kien", cha="module:/board/sense", kind="leaf",
         path="/board/sense/R1", ref="R1")

    p_u3 = _port(s, "leaf:U3", "2", huong="power_out", chan="2", path="/board/pwr/U3")
    p_u1v = _port(s, "leaf:U1", "7", huong="power_in", chan="7", path="/board/mcu/U1")
    p_u2v = _port(s, "leaf:U2", "1", huong="power_in", chan="1", path="/board/sense/U2")
    p_u1s = _port(s, "leaf:U1", "27", chan="27", path="/board/mcu/U1")
    p_u2s = _port(s, "leaf:U2", "5", chan="5", path="/board/sense/U2")
    p_r1 = _port(s, "leaf:R1", "1", chan="1", path="/board/sense/R1")

    p_pwr = _port(s, "module:/board/pwr", "VOUT", huong="power_out", path="/board/pwr")
    p_mcuv = _port(s, "module:/board/mcu", "VDD", huong="power_in", path="/board/mcu")
    p_senv = _port(s, "module:/board/sense", "VDD", huong="power_in", path="/board/sense")
    p_mcus = _port(s, "module:/board/mcu", "SDA", huong="bidir", path="/board/mcu")
    p_sens = _port(s, "module:/board/sense", "SDA", huong="bidir", path="/board/sense")

    # net 3V3 ở gốc, nối ba khối qua Port
    n3 = _nut(s, "net:/board.3V3", "3V3", loai="net", cha="module:/board",
              path="/board.3V3", canon={"ten": "3V3", "loai": "power",
                                        "ap_danh_dinh": "3,3 V"})
    for pid in (p_pwr, p_mcuv, p_senv):
        s.ckm_noi(net_id=n3, port_id=pid)
    # net cục bộ trong từng khối, xuống tới chân lá
    for khoi, port_len, chan_la, ten in (("pwr", p_pwr, p_u3, "VOUT_I"),
                                         ("mcu", p_mcuv, p_u1v, "VDD_I"),
                                         ("sense", p_senv, p_u2v, "VDD_I")):
        nid = _nut(s, f"net:/board/{khoi}.{ten}", "3V3", loai="net",
                   cha=f"module:/board/{khoi}", path=f"/board/{khoi}.{ten}",
                   canon={"ten": "3V3", "loai": "power"})
        s.ckm_noi(net_id=nid, port_id=port_len)
        s.ckm_noi(net_id=nid, port_id=chan_la)

    # bus SDA
    nsda = _nut(s, "net:/board.SDA", "SDA", loai="net", cha="module:/board",
                path="/board.SDA", canon={"ten": "SDA", "loai": "bus", "bus": "I2C1"})
    s.ckm_noi(net_id=nsda, port_id=p_mcus)
    s.ckm_noi(net_id=nsda, port_id=p_sens)
    for khoi, port_len, chan_la in (("mcu", p_mcus, p_u1s), ("sense", p_sens, p_u2s)):
        nid = _nut(s, f"net:/board/{khoi}.SDA_I", "SDA", loai="net",
                   cha=f"module:/board/{khoi}", path=f"/board/{khoi}.SDA_I",
                   canon={"ten": "SDA", "loai": "bus"})
        s.ckm_noi(net_id=nid, port_id=port_len)
        s.ckm_noi(net_id=nid, port_id=chan_la)
    s.ckm_noi(net_id="net:/board/sense.SDA_I", port_id=p_r1)      # pull-up trong khối sense
    return s


def _tim(ds, luat, ket_luan=None):
    return [x for x in ds if x.luat == luat and (ket_luan is None
                                                or x.ket_luan == ket_luan)]


# =========================================================================== 1. ngân sách dòng
def test_HIER07_khong_co_fact_thi_noi_CHUA_DU_DU_KIEN(bo):
    """Ca quan trọng nhất bộ này: một ERC đoán nốt phần thiếu tệ hơn không có ERC."""
    ds = E.erc(bo)
    x = _tim(ds, "ngan_sach_dong")
    assert x and all(i.ket_luan == "chua_du_du_kien" for i in x), [i.vi for i in x]
    assert "iout_max" in x[0].cach_sua


def test_HIER07_du_dong_thi_dat_va_noi_con_du_bao_nhieu(bo):
    _fact(bo, "leaf:U3", "iout_max", 0.8, unit="A")
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    _fact(bo, "leaf:U2", "i_max", 0.000085, unit="A")
    x = _tim(E.erc(bo), "ngan_sach_dong", "dat")
    assert x, [i.vi for i in E.erc(bo) if i.luat == "ngan_sach_dong"]
    assert "còn dư" in x[0].vi and x[0].path == "/board"


def test_HIER07_thieu_dong_thi_chan_va_noi_thieu_bao_nhieu(bo):
    _fact(bo, "leaf:U3", "iout_max", 0.010, unit="A")     # LDO 10 mA
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    _fact(bo, "leaf:U2", "i_max", 0.000085, unit="A")
    x = _tim(E.erc(bo), "ngan_sach_dong", "khong_dat")
    assert x and x[0].muc == "blocker", [i.vi for i in E.erc(bo)]
    assert "thiếu" in x[0].vi.lower() and "mA" in x[0].vi
    assert "sụt áp" in x[0].vi, "phải nói hậu quả, không chỉ nói con số"


def test_HIER07_thieu_mot_ve_thi_khong_ket_luan_du_da_cong_duoc_phan_con_lai(bo):
    """Cộng được 12 mA mà còn một linh kiện chưa có Fact ⇒ tổng THẬT lớn hơn. Kết luận
    "đủ dòng" ở đây là một câu đúng về con số sai."""
    _fact(bo, "leaf:U3", "iout_max", 0.8, unit="A")
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    ds = _tim(E.erc(bo), "ngan_sach_dong")
    assert ds and ds[0].ket_luan == "chua_du_du_kien"
    assert "U2" in ds[0].vi and "lớn hơn" in ds[0].vi


def test_HIER07_khoi_co_fact_rieng_thi_khong_cong_hai_lan(bo):
    """Khối `sense` đã đo cả cụm (2 mA). Cộng cả 2 mA lẫn 85 µA của U2 là tính hai lần."""
    _fact(bo, "leaf:U3", "iout_max", 0.8, unit="A")
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    _fact(bo, "module:/board/sense", "i_max", 0.002, unit="A")
    _fact(bo, "leaf:U2", "i_max", 0.000085, unit="A")
    x = _tim(E.erc(bo), "ngan_sach_dong", "dat")
    assert x, [i.vi for i in E.erc(bo) if i.luat == "ngan_sach_dong"]
    assert "14 mA" in x[0].vi, x[0].vi          # 12 + 2, KHÔNG phải 12 + 2 + 0,085


def test_tang_DONG_khong_duoc_lam_ve_so_sanh(bo):
    """N2 — ERC không được kết luận từ phỏng đoán của mô hình, kể cả khi con số nghe đúng."""
    _fact(bo, "leaf:U3", "iout_max", 0.8, unit="A", tier="DONG")
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    ds = _tim(E.erc(bo), "ngan_sach_dong")
    assert ds and ds[0].ket_luan == "chua_du_du_kien", [i.to_dict() for i in ds]


# =========================================================================== 2. địa chỉ bus
def test_HIER08_hai_con_cung_dia_chi_i2c(bo):
    _nut(bo, "leaf:U4", "TMP102", loai="linh_kien", cha="module:/board/sense", kind="leaf",
         path="/board/sense/U4", ref="U4")
    p = _port(bo, "leaf:U4", "5", chan="5", path="/board/sense/U4")
    bo.ckm_noi(net_id="net:/board/sense.SDA_I", port_id=p)
    _fact(bo, "leaf:U2", "i2c.addr", "0x48")
    _fact(bo, "leaf:U4", "i2c.addr", "0x48")
    x = _tim(E.erc(bo), "trung_dia_chi", "khong_dat")
    assert x and x[0].muc == "blocker", [i.vi for i in E.erc(bo)]
    assert "U2" in x[0].vi and "U4" in x[0].vi and "0x48" in x[0].vi
    assert x[0].path.startswith("/board/sense")


def test_dia_chi_khac_nhau_thi_khong_bao(bo):
    _nut(bo, "leaf:U4", "TMP102", loai="linh_kien", cha="module:/board/sense", kind="leaf",
         path="/board/sense/U4", ref="U4")
    p = _port(bo, "leaf:U4", "5", chan="5", path="/board/sense/U4")
    bo.ckm_noi(net_id="net:/board/sense.SDA_I", port_id=p)
    _fact(bo, "leaf:U2", "i2c.addr", "0x48")
    _fact(bo, "leaf:U4", "i2c.addr", "0x49")
    assert _tim(E.erc(bo), "trung_dia_chi", "khong_dat") == []


def test_dia_chi_viet_khac_dang_van_nhan_ra_la_trung(bo):
    """`0x48` và `72` là cùng một địa chỉ. Không chuẩn hoá thì phép kiểm bỏ lọt."""
    _nut(bo, "leaf:U4", "TMP102", loai="linh_kien", cha="module:/board/sense", kind="leaf",
         path="/board/sense/U4", ref="U4")
    p = _port(bo, "leaf:U4", "5", chan="5", path="/board/sense/U4")
    bo.ckm_noi(net_id="net:/board/sense.SDA_I", port_id=p)
    _fact(bo, "leaf:U2", "i2c.addr", "0x48")
    _fact(bo, "leaf:U4", "i2c.addr", "72")
    assert _tim(E.erc(bo), "trung_dia_chi", "khong_dat")


# =========================================================================== 3. pull-up
def test_mot_cum_pull_up_thi_dat(bo):
    x = _tim(E.erc(bo), "pull_up", "dat")
    assert x and "R1 ở /board/sense" in x[0].vi, \
        [i.vi for i in E.erc(bo) if i.luat == "pull_up"]


def test_hai_cum_pull_up_bi_canh_bao_va_noi_hau_qua(bo):
    _nut(bo, "leaf:R9", "4k7", loai="linh_kien", cha="module:/board/mcu", kind="leaf",
         path="/board/mcu/R9", ref="R9")
    p = _port(bo, "leaf:R9", "1", chan="1", path="/board/mcu/R9")
    bo.ckm_noi(net_id="net:/board/mcu.SDA_I", port_id=p)
    x = _tim(E.erc(bo), "pull_up", "canh_bao")
    assert x, [i.vi for i in E.erc(bo) if i.luat == "pull_up"]
    assert "gấp đôi" in x[0].vi and "tìm cả tuần" in x[0].vi
    assert "R9 ở /board/mcu" in x[0].vi, "phải nói điện trở NẰM Ở ĐÂU để người đi sửa"


def test_khong_co_pull_up_thi_bao_thieu(bo):
    bo.ckm_xoa_noi(net_id="net:/board/sense.SDA_I", port_id="port:/board/sense/R1.1")
    x = _tim(E.erc(bo), "pull_up", "khong_dat")
    assert x and "open-drain" in x[0].vi
    assert "4,7 kΩ" in x[0].cach_sua


def test_net_khong_phai_i2c_thi_khong_doi_pull_up(bo):
    ds = E.erc(bo)
    assert not [x for x in ds if x.luat == "pull_up" and "3V3" in x.vi]


# =========================================================================== 4. mức logic
def test_muc_logic_khong_tuong_thich_bi_chan(bo):
    _fact(bo, "pin:U1.27", "voh", 2.4, unit="V")
    _fact(bo, "pin:U2.5", "vih", 3.0, unit="V")
    x = _tim(E.erc(bo), "muc_logic", "khong_dat")
    assert x and x[0].muc == "blocker", [i.vi for i in E.erc(bo) if i.luat == "muc_logic"]
    assert "SDA" in x[0].vi and "U1.27" in x[0].vi


def test_muc_logic_tuong_thich_thi_dat(bo):
    _fact(bo, "pin:U1.27", "voh", 3.1, unit="V")
    _fact(bo, "pin:U2.5", "vih", 2.1, unit="V")
    assert _tim(E.erc(bo), "muc_logic", "dat")


# =========================================================================== 5. chủ thể Fact
def test_chu_the_theo_cap_sai_thi_canh_bao_chu_khong_chan(bo):
    """Một Fact gắn sai chủ thể vẫn là con số thật người vừa đọc; mất nó tệ hơn giữ nó ở
    chỗ hơi lệch. Nhưng im lặng thì nó không bao giờ được ERC nhìn thấy."""
    assert E.kiem_chu_the(bo, "module:/board/mcu") == ""
    assert E.kiem_chu_the(bo, "leaf:U1") == ""
    assert E.kiem_chu_the(bo, "port:/board/mcu.VDD") == ""

    v = E.kiem_chu_the(bo, "module:/board/khong-co")
    assert "Kiểm lại đường" in v
    assert "ckm.module_set" in E.kiem_chu_the(bo, "module:/board/x")
    assert "ckm.port_set" in E.kiem_chu_the(bo, "port:/board/mcu.KHONGCO")
    assert "ckm.chip_add" in E.kiem_chu_the(bo, "leaf:U99")


def test_chu_the_tu_do_khong_bi_cham(bo):
    """`he-thong`, `chip:RPi-Zero-2W` đã dùng từ trước và hợp lệ."""
    assert E.kiem_chu_the(bo, "he-thong") == ""
    assert E.kiem_chu_the(bo, "chip:RPi-Zero-2W") == ""


def test_khoa_fact_co_bi_danh(bo):
    """Cùng một đại lượng được datasheet gọi nhiều tên; bắt nhớ đúng một tên là bắt sai chỗ."""
    assert E.khoa_chuan("Icc.max") == "i_max"
    assert E.khoa_chuan("IOUT_MAX") == "i_out_max"
    assert E.khoa_chuan("i2c.addr") == "addr"
    assert E.khoa_chuan("mau_sac") is None


# =========================================================================== 6. explain khối
def test_HIER14_explain_khoi_co_hai_cau_do_MA_dung(bo):
    """§8 — "giao tiếp gì (Port)" và "gồm gì (con)" là DỮ LIỆU, không phải văn.

    Bắt mô hình viết chúng là mời nó mô tả khối theo trí nhớ: nó sẽ viết đúng chín lần rồi
    lần thứ mười viết một Port không tồn tại.
    """
    cay = C.Cay.doc(bo)
    ex = E.explain_khoi(cay, "module:/board/sense", ex_cu={"summary": "khối cảm biến"},
                        req=["FR-02"])
    assert "VDD (power_in)" in ex["giao_tiep"] and "SDA" in ex["giao_tiep"]
    assert "U2" in ex["gom"] and "R1" in ex["gom"]
    assert ex["thuc_hien_req"] == "FR-02"
    assert ex["summary"] == "khối cảm biến", "không được xoá phần mô hình đã viết"


def test_explain_khoi_chua_khai_port_thi_noi_thang(bo):
    _nut(bo, "module:/board/x", "x", loai="module", cha="module:/board", kind="block",
         path="/board/x")
    ex = E.explain_khoi(C.Cay.doc(bo), "module:/board/x")
    assert "chưa khai Port nào" in ex["giao_tiep"]
    assert "chưa có gì bên trong" in ex["gom"]


def test_explain_confidence_la_tang_THAP_NHAT_trong_khoi(bo):
    """§8 "tin được đến đâu" — một khối có một lá ở tầng ĐỒNG thì cả khối không đáng tin
    hơn cái lá đó."""
    bo.ckm_dat_nut(node_id="leaf:U2", loai="linh_kien", ten="TMP102",
                   canonical={"ref": "U2"}, tier="DONG")
    bo.ckm_dat_cay("leaf:U2", parent_id="module:/board/sense", kind="leaf",
                   path="/board/sense/U2")
    ex = E.explain_khoi(C.Cay.doc(bo), "module:/board/sense")
    assert ex["confidence"] == "DONG"


# =========================================================================== 7. công cụ
def test_board_check_noi_ro_CHUA_DU_DU_KIEN_khong_goi_la_dat(make_agent):
    """Một ERC gọi "chưa đủ dữ kiện" là "đạt" thì tệ hơn không có ERC (N6)."""
    from eide.loop import TurnContext

    a = make_agent([])
    ex = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "VANG"}
    ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger, eide_md=a.eide_md,
                      ids=a.ids, registry=a.registry, emit=lambda c: None,
                      history=a.history, run_id="run-1")

    def goi(cong_cu, /, **kw):
        if "explain" in (a.registry.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", ex)
        return a.registry.run(cong_cu, kw, ctx)

    assert goi("ckm.module_set", ma="PWR", ten="Nguồn", muc_dich="3V3").ok
    assert goi("ckm.port_set", khoi="PWR", ten="VOUT", huong="power_out").ok
    assert goi("ckm.net_set", ten="3V3", loai="power",
               noi_port=[["PWR", "VOUT"]]).ok
    r = goi("board.check")
    assert r.ok and r.data["so_phat_hien"] >= 1
    assert "CHƯA ĐỦ DỮ KIỆN" in r.data["note_vi"]
    assert r.data["ket_qua"]["dat"] == []


def test_board_check_khong_co_gi_de_kiem_thi_noi_can_goi_gi(make_agent):
    from eide.loop import TurnContext

    a = make_agent([])
    ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger, eide_md=a.eide_md,
                      ids=a.ids, registry=a.registry, emit=lambda c: None,
                      history=a.history, run_id="run-1")
    r = a.registry.run("board.check", {}, ctx)
    assert r.ok and r.data["so_phat_hien"] == 0
    assert "ckm.net_set" in r.data["note_vi"]


def test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao(bo):
    """Một dòng "thiếu pull-up" không nói ở khối nào thì trên mạch 40 khối là vô dụng.

    Hai thông tin KHÁC NHAU và phải có cả hai: `path` là khối mà luật áp dụng (khối sở hữu
    bus), còn câu giải thích nói linh kiện NẰM Ở ĐÂU — đó là thứ người cầm đi sửa.
    """
    ds = E.erc(bo)
    assert ds and all(x.path for x in ds), [x.to_dict() for x in ds]
    pu = _tim(ds, "pull_up", "dat")
    assert pu and "R1 ở /board/sense" in pu[0].vi, pu[0].vi if pu else ds


# =========================================================================== 8. STALE theo cây §6
def test_HIER05_sua_noi_bo_khoi_KHONG_lan_sang_anh_em(bo):
    """Bảng §6 dòng 1: sửa nội bộ khối X → chỉ X; anh em KHÔNG stale; cha chỉ nhận cờ.

    Chuỗi STALE theo LOẠI hiện vật không diễn đạt được câu này: nó làm STALE mọi netlist và
    mọi mã. Trên mạch 40 khối thì một thay đổi bật đèn ở 40 chỗ, và người học được rằng băng
    cảnh báo không có nghĩa gì. Đó là cách tệ nhất để mất một cơ chế an toàn — không phải
    nó tắt, mà là nó luôn bật.
    """
    lan = C.lan_stale(C.Cay.doc(bo), loai="noi_bo", muc_tieu="module:/board/sense",
                      ly_do="cs-0010 (đổi giá trị R1)")
    assert "/board/sense" in lan.stale
    assert "/board/mcu" not in lan.stale and "/board/pwr" not in lan.stale
    assert lan.chi_bao_tin["/board"].startswith("con đã đổi")
    assert "/board" not in lan.stale, "cha chỉ nhận THÔNG TIN, không phải việc phải làm"


def test_HIER05_sua_noi_bo_lan_xuong_la_ben_trong(bo):
    lan = C.lan_stale(C.Cay.doc(bo), loai="noi_bo", muc_tieu="module:/board/sense",
                      ly_do="cs-0010")
    assert "/board/sense/U2" in lan.stale and "/board/sense/R1" in lan.stale


def test_HIER06_doi_Port_lan_tu_cha_va_anh_em_NOI_VAO_net_do(bo):
    """Bảng §6 dòng 2: đổi Port của X → X, cha của X, và khối anh em NỐI VÀO net đó."""
    lan = C.lan_stale(C.Cay.doc(bo), loai="port", muc_tieu="module:/board/mcu",
                      ly_do="cs-0011 (đổi Port VDD)", net_lien_quan="3V3")
    assert "/board/mcu" in lan.stale
    assert "/board" in lan.stale, "cha phải xem lại net nối vào Port đó"
    assert "/board/pwr" in lan.stale and "/board/sense" in lan.stale


def test_HIER06_anh_em_KHONG_noi_vao_net_do_thi_khong_lan(bo):
    """§6: "Các nhánh không nối" thì không lan. Đây là chỗ phân biệt một cảnh báo có nghĩa
    với một cảnh báo phát cho cả bo."""
    _nut(bo, "module:/board/rf", "rf", loai="module", cha="module:/board", kind="block",
         path="/board/rf")
    lan = C.lan_stale(C.Cay.doc(bo), loai="port", muc_tieu="module:/board/mcu",
                      ly_do="cs-0011", net_lien_quan="3V3")
    assert "/board/rf" not in lan.stale


def test_doi_Fact_cua_la_lan_LEN_theo_duong_Port(bo):
    """Bảng §6 dòng 3: Fact của lá đổi → mọi ràng buộc dùng Fact đó, từ lá lên tới gốc."""
    lan = C.lan_stale(C.Cay.doc(bo), loai="fact_la", muc_tieu="leaf:U2",
                      ly_do="cs-0012 (datasheet mới)")
    assert "/board/sense/U2" in lan.stale
    assert "/board/sense" in lan.stale and "/board" in lan.stale
    assert "/board/mcu" not in lan.stale, "nhánh khác không liên quan"


def test_doi_REQ_lan_tới_khoi_THUC_HIEN_no(bo):
    bo.ckm_dat_nut(node_id="module:/board/sense", loai="module", ten="sense",
                   canonical={"ten": "sense", "dap_ung_req": ["FR-02"]})
    bo.ckm_dat_cay("module:/board/sense", parent_id="module:/board", kind="block",
                   path="/board/sense")
    lan = C.lan_stale(C.Cay.doc(bo), loai="req", muc_tieu="FR-02", ly_do="cs-0013")
    assert lan.stale == {"/board/sense": "cs-0013"}


def test_loai_thay_doi_la_thi_NO_chu_khong_im_lang_tra_rong(bo):
    """Một loại lạ trả về rỗng nghĩa là "không lan gì" — một câu sai nghe như đúng."""
    with pytest.raises(ValueError, match="loại thay đổi lạ"):
        C.lan_stale(C.Cay.doc(bo), loai="cai-gi-do", muc_tieu="module:/board", ly_do="x")


def _agent_cay(make_agent):
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


def test_port_set_ghi_STALE_theo_nut_vao_hien_vat(make_agent):
    a, goi = _agent_cay(make_agent)
    goi("ckm.module_set", ma="PWR", ten="Nguồn", muc_dich="3V3")
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="firmware")
    goi("ckm.port_set", khoi="PWR", ten="VOUT", huong="power_out")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="power_in")
    goi("ckm.net_set", ten="3V3", loai="power", noi_port=[["PWR", "VOUT"], ["MCU", "VDD"]])

    r = goi("ckm.port_set", khoi="MCU", ten="VDD", huong="bidir")
    assert r.ok
    nut = a.store.get("MG-1")["canonical"].get("stale_nut") or {}
    assert "/board/MCU" in nut and "/board" in nut
    assert "/board/PWR" in nut, "khối cùng nối vào net 3V3 phải xem lại"
    assert "Đổi Port thì CÓ lan" in r.data["note_vi"]


def test_chap_nhan_STALE_cho_mot_nut_va_ca_nhanh(make_agent):
    a, goi = _agent_cay(make_agent)
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="x")
    goi("ckm.module_set", ma="XTAL", ten="Dao động", muc_dich="y", cha="MCU")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="power_in")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="bidir")
    assert (a.store.get("MG-1")["canonical"].get("stale_nut") or {})

    r = goi("stale.accept", id="/board/MCU", why="anh chấp nhận, sẽ sửa sau")
    assert r.ok and r.data["nut"] == ["/board/MCU"]
    canon = a.store.get("MG-1")["canonical"]
    assert "/board/MCU" not in (canon.get("stale_nut") or {})
    assert "anh chấp nhận" in canon["stale_da_chap_nhan"]["/board/MCU"], \
        "lý do phải được GIỮ, không xoá trắng — lịch sử cần thấy nó từng bật"


def test_chap_nhan_STALE_cho_nut_khong_stale_thi_noi_nut_nao_dang_stale(make_agent):
    a, goi = _agent_cay(make_agent)
    goi("ckm.module_set", ma="MCU", ten="MCU", muc_dich="x")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="power_in")
    goi("ckm.port_set", khoi="MCU", ten="VDD", huong="bidir")
    r = goi("stale.accept", id="/board/KHONG-CO", why="x")
    assert not r.ok and "/board/MCU" in r.error.hint_for_agent


def test_stale_accept_phan_biet_ma_hien_vat_voi_duong_dan_nut(make_agent):
    a, goi = _agent_cay(make_agent)
    r = goi("stale.accept", id="KHONG-CO-HIEN-VAT", why="x")
    assert not r.ok and "bắt đầu bằng '/'" in r.error.hint_for_agent


def test_lan_stale_khong_bao_gio_tra_rong_vi_muc_tieu_khong_la_nut(bo):
    """Ca này canh đúng lỗi vừa sửa: `req` nhận MÃ REQ chứ không phải node_id, nên phép tra
    nút ở đầu hàm làm nó lặng lẽ trả rỗng — "đổi REQ không làm gì lỗi thời", sai và im."""
    bo.ckm_dat_nut(node_id="module:/board/mcu", loai="module", ten="mcu",
                   canonical={"ten": "mcu", "dap_ung_req": ["FR-01"]})
    bo.ckm_dat_cay("module:/board/mcu", parent_id="module:/board", kind="block",
                   path="/board/mcu")
    assert C.lan_stale(C.Cay.doc(bo), loai="req", muc_tieu="FR-01",
                       ly_do="cs-1").stale == {"/board/mcu": "cs-1"}


def test_tim_nut_nhan_ca_node_id_va_duong_dan(bo):
    """Ba dạng trông giống nhau và rất dễ lẫn: `module:MOD-MCU` (node_id), `/board/mcu`
    (đường dẫn), và `module:/board/mcu` — dạng thứ ba KHÔNG có thật nhưng trông đúng nhất.

    Bộ E2E của tôi gọi bằng dạng thứ ba và mọi phép lan STALE trả rỗng, tức "đổi Port không
    ảnh hưởng gì" — sai và im. Nay nhận cả ba, và id lạ thì NỔ.
    """
    assert C.tim_nut(C.Cay.doc(bo), "module:/board/mcu") == "module:/board/mcu"
    assert C.tim_nut(C.Cay.doc(bo), "/board/mcu") == "module:/board/mcu"
    assert C.tim_nut(C.Cay.doc(bo), "khong-co-gi") is None


def test_lan_stale_muc_tieu_la_thi_NO_chu_khong_tra_rong(bo):
    with pytest.raises(KeyError, match="không có nút nào"):
        C.lan_stale(C.Cay.doc(bo), loai="port", muc_tieu="module:KHONG-CO", ly_do="x")


def test_khoi_cap_nhan_ra_bang_FACT_du_Port_chua_biet_huong(bo):
    """Port của lá sinh khi di cư mô hình phẳng có hướng `passive` (không đoán hướng tín
    hiệu). Gate theo hướng làm một LDO có Fact `iout_max` hẳn hoi vẫn "không phải khối
    cấp", và cả ràng buộc im lặng biến thành "chưa đủ dữ kiện"."""
    bo.ckm_dat_port(port_id="port:/board/pwr/U3.2", module_id="leaf:U3", ten="2",
                    huong="passive", chan="2")          # hướng bị mất, như sau di cư
    _fact(bo, "leaf:U3", "iout_max", 0.8, unit="A")
    _fact(bo, "leaf:U1", "i_max", 0.012, unit="A")
    _fact(bo, "leaf:U2", "i_max", 0.000085, unit="A")
    x = _tim(E.erc(bo), "ngan_sach_dong", "dat")
    assert x, [i.vi for i in E.erc(bo) if i.luat == "ngan_sach_dong"]


# =========================================================================== 5. quá áp trên net
#
# Luật này khác bốn luật kia ở một điểm: ba luật kia bắt mạch CHẠY SAI, luật này bắt mạch
# HỎNG. 5 V vào một chân chịu 3,6 V không làm sai sườn hay lệch số đo — nó phá con chip, và
# không có cách nào "chạy lại để xem". Nên nó là luật duy nhất ở đây mà phát hiện muộn một
# lần đã là quá muộn.
#
# Trước M3-01, `compare.qua_ap` đã có sẵn: câu chữ, mức blocker, cách chặn vế ĐỒNG — đủ cả.
# Nhưng `erc()` chỉ gọi bốn luật và không luật nào gọi nó, nên con đường từ "có luật" tới
# "luật nổ" bị đứt. Tác tử phải TỰ NHỚ gọi `fact.compare` mới thấy, mà một phép kiểm phụ
# thuộc vào việc ai đó nhớ gọi nó thì không phải một phép kiểm.
def _dat_rail(bo, ap: str):
    """Đổi điện áp danh định của net 3V3 ở gốc."""
    bo.ckm_dat_nut(node_id="net:/board.3V3", loai="net", ten="3V3",
                   canonical={"ten": "3V3", "loai": "power", "ap_danh_dinh": ap})


def test_qua_ap_rail_5V_vao_chan_3V6_bi_chan(bo):
    """TC-M3-01-01 — rail 5 V, chân U2 chịu 3,6 V → blocker, và nói ở khối nào."""
    _dat_rail(bo, "5 V")
    _fact(bo, "leaf:U2", "vdd.max", 3.6, unit="V")

    ds = E.erc(bo)
    x = _tim(ds, "qua_ap", "khong_dat")
    assert x, [f"{i.luat}/{i.ket_luan}" for i in ds]
    assert x[0].muc == "blocker", x[0].muc
    assert "U2" in x[0].vi, x[0].vi
    assert x[0].path.startswith("/board/sense"), x[0].path
    # Hai vế phải nêu được nguồn, không chỉ nêu kết luận.
    assert len(x[0].bang_chung) >= 2, x[0].bang_chung


def test_qua_ap_trong_gioi_han_khong_bao(bo):
    """TC-M3-01-02 — ca âm: rail 3,3 V, chân chịu 5,5 V → KHÔNG dòng nào, kể cả "đạt".

    Không chỉ "không có blocker": luật này không được thêm một dòng `đạt` nào vào bảng.
    Bảng ERC đầy dòng "đạt" cho thứ chưa ai hỏi là cách nhanh nhất để người đọc học được
    rằng bảng ấy không đáng đọc — và `test_board_check…_dat == []` canh đúng điều đó.
    """
    _fact(bo, "leaf:U2", "vdd.max", 5.5, unit="V")
    ds = E.erc(bo)
    assert _tim(ds, "qua_ap", "khong_dat") == []
    assert _tim(ds, "qua_ap") == [], [x.vi for x in _tim(ds, "qua_ap")]


def test_qua_ap_ve_DONG_thi_chua_du_du_kien(bo):
    """TC-M3-01-03 — vế ĐỒNG thì KHÔNG kết luận (N2), dù con số nhìn là vượt rõ."""
    _dat_rail(bo, "5 V")
    _fact(bo, "leaf:U2", "vdd.max", 3.6, unit="V", tier="DONG")

    ds = E.erc(bo)
    assert _tim(ds, "qua_ap", "khong_dat") == []
    x = _tim(ds, "qua_ap", "chua_du_du_kien")
    assert x, [f"{i.luat}/{i.ket_luan}" for i in ds]


def test_qua_ap_tin_hieu_voh_vuot_vmax_chan_thu(bo):
    """TC-M3-01-04 — không có rail thì lấy VOH của bên phát làm vế cấp.

    Đây là đường vào thật của lỗi mức 5 V: không phải ai cũng cấp sai nguồn, nhưng nối một
    chân ra 5 V vào một chân vào 3,3 V thì rất dễ — hai con chip đều "đúng" khi đọc riêng.
    """
    _fact(bo, "pin:U1.27", "voh", 4.8, unit="V")
    _fact(bo, "pin:U2.5", "v_max", 3.6, unit="V")

    x = _tim(E.erc(bo), "qua_ap", "khong_dat")
    assert x, "VOH 4,8 V vào chân chịu 3,6 V mà không ai báo"
    assert x[0].muc == "blocker"
    assert "U2" in x[0].vi, x[0].vi


def test_qua_ap_chan_chiu_5V_khong_bao(bo):
    """TC-M3-01-05 — ca âm: chân khai chịu được 5 V thì không báo, dù rail là 5 V.

    Chân 5V-tolerant là chuyện có thật và rất thường gặp (STM32, nhiều chân I/O). Báo oan
    ở đây thì bảng ERC mất uy tín đúng vào loại mạch phổ biến nhất.
    """
    _dat_rail(bo, "5 V")
    _fact(bo, "leaf:U2", "vdd.max", 3.6, unit="V")
    _fact(bo, "pin:U2.1", "v_tolerant", "1")

    assert _tim(E.erc(bo), "qua_ap", "khong_dat") == []


def test_qua_ap_khong_bao_tren_net_DAT(bo):
    """Net đất không có "điện áp cấp" theo nghĩa này — báo ở đó là một dòng vô nghĩa.

    Bản đầu của ca này **rỗng**: dàn dựng `bo` không có net GND nào, nên nó xanh cả khi tôi
    bỏ hẳn phép bỏ qua net đất. Nay nó DỰNG một net GND, và dựng đúng tình huống làm phép
    bỏ qua ấy có việc: một net `loai="gnd"` mang `ap_danh_dinh` (người khai nhầm, chuyện có
    thật) cùng một chân có `v_max`. Thiếu phép bỏ qua thì ERC báo blocker trên net đất.
    """
    _fact(bo, "leaf:U2", "vdd.max", 3.6, unit="V")
    g = _nut(bo, "net:/board.GND", "GND", loai="net", cha="module:/board",
             path="/board.GND", canon={"ten": "GND", "loai": "gnd",
                                       "ap_danh_dinh": "5 V"})
    pg = _port(bo, "leaf:U2", "4", chan="4", path="/board/sense/U2")
    bo.ckm_noi(net_id=g, port_id=pg)
    _fact(bo, "pin:U2.4", "v_max", 3.6, unit="V")

    tren_dat = [x for x in _tim(E.erc(bo), "qua_ap") if "GND" in x.vi.upper()]
    assert tren_dat == [], [x.vi for x in tren_dat]


def test_qua_ap_khong_co_fact_thi_IM_khong_lam_nhieu_bang(bo):
    """Không có Fact `v_max` nào thì luật này KHÔNG sinh dòng "đạt" cho mọi chân.

    Bảng ERC đầy dòng "đạt" cho những thứ chưa ai đo là cách nhanh nhất để người đọc học
    được rằng bảng ấy không đáng đọc. Ca `test_board_check..._dat == []` canh đúng điều này.
    """
    assert _tim(E.erc(bo), "qua_ap") == []
