# -*- coding: utf-8 -*-
"""Sửa theo đường dẫn lồng, bác bỏ, xác nhận Fact — EIDE-EDIT-47 §DEV-368.

Rà 12/10/2026: lõi sửa được **mọi** hiện vật theo trường, nhưng giao diện chỉ mở ô sửa ở
bốn bảng và chỉ trường **cấp một**. Hệ quả đo được: khoảng ba mươi loại hiện vật trong kho
người **chỉ đọc**. Và hai loại việc nữa có trong giao thức từ đầu mà không ai đi:

* `HumanAct kind=confirm` — đường BẠC→VÀNG mà §C1 nói **chỉ người đi được**. `grep
  "confirm"` trong `loop.py` = 0 trước gói này;
* `bac_bo` — "không phải lỗi" → EIDE.md §Đừng. Có trong `human_edit.py` từ G2, không nút nào.
"""

from __future__ import annotations

import pytest

from eide import Config, Core
from eide import human_edit as he
from eide.errors import EideError
from eide.llm import ScriptedGateway
from eide.loop import Agent

EX = {"summary": "ghi thử", "why": "dựng dữ liệu", "sources": [], "diff_prev": "đầu",
      "next": "—", "confidence": "VANG"}


# =============================================================== ap_patch
def test_bon_phep_set_add_remove_move():
    c = {"a": {"b": 1}, "ds": [{"x": 1}, {"x": 2}, {"x": 3}]}
    assert he.ap_patch(c, [{"path": "a/b", "value": 9}])["a"]["b"] == 9
    assert he.ap_patch(c, [{"path": "ds/-", "op": "add", "value": {"x": 4}}])["ds"][-1] == {"x": 4}
    assert he.ap_patch(c, [{"path": "ds/1", "op": "add", "value": {"x": 9}}])["ds"][1] == {"x": 9}
    assert [d["x"] for d in he.ap_patch(c, [{"path": "ds/0", "op": "remove"}])["ds"]] == [2, 3]
    moved = he.ap_patch(c, [{"path": "ds/0", "op": "move", "to": "ds/-"}])["ds"]
    assert [d["x"] for d in moved] == [2, 3, 1]


def test_KHONG_sua_tai_cho():
    """Người gọi còn giữ bản cũ để so, để ghi `noi_dung_truoc`, và để xếp loại sửa.
    Sửa tại chỗ thì bản "trước" thành bản "sau" ngay dưới tay họ."""
    c = {"ds": [{"x": 1}], "sau": {"trong": [1, 2]}}
    ra = he.ap_patch(c, [{"path": "ds/0/x", "value": 99},
                         {"path": "sau/trong/0", "value": 7}])
    assert c["ds"][0]["x"] == 1 and c["sau"]["trong"][0] == 1
    assert ra["ds"][0]["x"] == 99 and ra["sau"]["trong"][0] == 7


@pytest.mark.parametrize("p, cho", [
    ({"path": "khong/co", "value": 1}, "khong"),
    ({"path": "ds/9/x", "value": 1}, "9"),
    ({"path": "ds/abc", "value": 1}, "abc"),
    ({"path": "", "value": 1}, "rỗng"),
    ({"path": "a/b", "op": "nhan_doi"}, "nhan_doi"),
    ({"path": "a/b/c/d", "value": 1}, "c"),
])
def test_loi_duong_dan_NOI_RA_cho_sai(p, cho):
    """Một lỗi "không tìm thấy" không chỉ ra chỗ sai thì người chỉ còn cách thử lại y nguyên."""
    with pytest.raises(EideError) as e:
        he.ap_patch({"a": {"b": 1}, "ds": [{"x": 1}]}, [p])
    assert cho in str(e.value)


def test_duong_dan_co_HAI_CHAM_bi_chan_ke_ca_khi_no_doc_duoc():
    """Phép phá "bỏ chặn `..`" LỌT ở lượt đầu, và vì sao: trên một canonical thường, bỏ
    chặn ra lỗi *"không có nhánh `..`"* — cũng là một lỗi, cũng chứa hai dấu chấm, nên ca
    kiểm không phân biệt được hai cái.

    Nên dựng một canonical mà `..` ĐỌC ĐƯỢC: bỏ chặn thì nó ghi thành công, giữ chặn thì
    nó nổ. Lúc ấy phép phá mới nói về cái chặn chứ không nói về phép tra bảng.
    """
    with pytest.raises(EideError) as e:
        he.ap_patch({"..": {"x": 1}}, [{"path": "../x", "value": 2}])
    assert "patch[0].path" in str(e.value)


def test_xoa_nhanh_khong_co_thi_bao_chu_khong_im():
    with pytest.raises(EideError):
        he.ap_patch({"a": 1}, [{"path": "b", "op": "remove"}])


def test_set_vao_nhanh_CHUA_CO_thi_tu_choi_con_add_thi_duoc():
    """`set` một nhánh chưa có gần như luôn là gõ nhầm tên trường. `add` thì nói rõ ý
    định là thêm mới, nên cho."""
    with pytest.raises(EideError):
        he.ap_patch({"a": 1}, [{"path": "ghi_chu", "value": "x"}])
    assert he.ap_patch({"a": 1}, [{"path": "ghi_chu", "op": "add", "value": "x"}])["ghi_chu"] == "x"


# =============================================================== phân loại theo đường dẫn
def test_phan_loai_theo_DOAN_CUOI_cua_duong_dan():
    """`elements/3/mau` là sửa màu: trình bày. `elements/3/x` là dời đi chỗ khác: nội
    dung. Hai đường chung đoạn ĐẦU, nên xếp theo đoạn đầu thì một trong hai sai."""
    assert he.phan_loai(truoc={}, sau={}, duong_dan_doi=["phan_tu/3/mau"]).gay_stale is False
    assert he.phan_loai(truoc={}, sau={}, duong_dan_doi=["phan_tu/3/x"]).gay_stale is True
    # Một đường trình bày + một đường nội dung = nội dung. Không được "trung bình" ra
    # trình bày: một nửa thay đổi có nghĩa thì cả lần sửa có nghĩa.
    pl = he.phan_loai(truoc={}, sau={}, duong_dan_doi=["phan_tu/3/mau", "phan_tu/3/x"])
    assert pl.loai == "noi_dung" and pl.gay_stale is True
    assert he.phan_loai(truoc={}, sau={}, duong_dan_doi=["chon"]).loai == "quyet_dinh"


def test_CX08_van_xanh_tren_duong_cu():
    """Ca CX08 đo đường cấp một; thêm tham số mới không được làm nó đổi nghĩa."""
    assert he.phan_loai(truoc={"ten": "A"}, sau={"ten": "B"}).gay_stale is False
    assert he.phan_loai(truoc={"criteria": "1"}, sau={"criteria": "5"}).gay_stale is True


# =============================================================== đường người đi
@pytest.fixture
def phien(du_an):
    def _tao(sua_long: bool = True):
        cfg = Config.for_project(du_an)
        cfg.features.sua_long = sua_long
        a = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _loi(out):
    return "\n".join(c.params.get("text", "") for c in out
                     if c.method == "console.post" and c.params.get("role") == "agent")


def _canh_bao(out):
    return " ".join(c.params.get("text", "") for c in out if c.method == "notice")


def _tieu_chi(a):
    a.history.ghi_kho(author="agent:r", artefact_id="criteria:sim-01", type="criteria",
                      op="create", explain=EX,
                      canonical={"ma": "sim-01",
                                 "assert": [{"ma": "A1", "nguong": 3.3, "phep_so": ">="},
                                            {"ma": "A2", "nguong": 10, "phep_so": "<="}]})
    return a.store.get("criteria:sim-01")


def _sua(ma, patch, ver, **kw):
    return {"kind": "edit", "target": {"type": "criteria", "id": ma},
            "data": {"base_version": f"v{ver}", "patch": patch,
                     "summary": "sửa sâu", **kw},
            "origin": {"surface": "simulation", "block": "A8.1", "row": "A1"},
            "note": kw.pop("note", "vì tôi đo lại rồi")}


def test_sua_SAU_trong_hien_vat_di_duoc_tu_cua_console(phien):
    a, core, out = phien()
    c = _tieu_chi(a)
    core.console_act(_sua("criteria:sim-01",
                          [{"path": "assert/0/nguong", "value": 5.0}], c["version"]))
    sau = a.store.get("criteria:sim-01")["canonical"]
    assert sau["assert"][0]["nguong"] == 5.0
    assert sau["assert"][1]["nguong"] == 10, "phần tử khác KHÔNG được đụng tới"
    cs = [x for x in a.history.log.all() if x.by_human]
    assert len(cs) == 1 and cs[0].reversible


def test_mot_lan_luu_NHIEU_o_ra_DUNG_MOT_changeset(phien):
    """Mỗi ô một `edit` thì một dòng bốn trường thành bốn changeset, bốn dòng lịch sử,
    và bốn lần đánh STALE cho cùng một việc."""
    a, core, out = phien()
    c = _tieu_chi(a)
    core.console_act(_sua("criteria:sim-01", [
        {"path": "assert/0/nguong", "value": 5.0},
        {"path": "assert/0/phep_so", "value": "<="},
        {"path": "assert/1/nguong", "value": 20},
    ], c["version"]))
    assert len([x for x in a.history.log.all() if x.by_human]) == 1
    can = a.store.get("criteria:sim-01")["canonical"]
    assert (can["assert"][0]["nguong"], can["assert"][0]["phep_so"]) == (5.0, "<=")
    assert can["assert"][1]["nguong"] == 20


def test_duong_dan_sai_thi_KHONG_ghi_NUA_VOI(phien):
    """I9 — lưu của người là nguyên tử: không hợp lệ thì không có changeset nào."""
    a, core, out = phien()
    c = _tieu_chi(a)
    core.console_act(_sua("criteria:sim-01", [
        {"path": "assert/0/nguong", "value": 5.0},
        {"path": "assert/9/nguong", "value": 7.0},      # phần tử không có
    ], c["version"]))
    assert a.store.get("criteria:sim-01")["canonical"]["assert"][0]["nguong"] == 3.3
    assert not [x for x in a.history.log.all() if x.by_human]
    assert "chưa ghi gì cả" in _canh_bao(out)


def test_co_TAT_thi_duong_patch_khong_chay(phien):
    a, core, out = phien(sua_long=False)
    c = _tieu_chi(a)
    core.console_act(_sua("criteria:sim-01",
                          [{"path": "assert/0/nguong", "value": 5.0}], c["version"]))
    assert a.store.get("criteria:sim-01")["canonical"]["assert"][0]["nguong"] == 3.3
    assert "EIDE_FEATURE_SUA_LONG" in _canh_bao(out)
    assert not [x for x in a.history.log.all() if x.by_human]


def test_xung_dot_theo_DUONG_DAN_chu_khong_theo_truong_cap_mot(phien):
    """Hai người sửa hai phần tử KHÁC NHAU của cùng một danh sách là hai việc không đụng
    nhau. Đường cũ so ở cấp một nên cả hai cùng chạm `assert` — một xung đột không có thật."""
    a, core, out = phien()
    c = _tieu_chi(a)
    # Tác tử sửa phần tử 1 trong lúc người đang mở bản cũ.
    a.history.ghi_kho(author="agent:r2", artefact_id="criteria:sim-01", type="criteria",
                      op="update", explain=EX,
                      canonical={"ma": "sim-01",
                                 "assert": [{"ma": "A1", "nguong": 3.3, "phep_so": ">="},
                                            {"ma": "A2", "nguong": 99, "phep_so": "<="}]})
    out.clear()
    core.console_act(_sua("criteria:sim-01",
                          [{"path": "assert/0/nguong", "value": 5.0}], c["version"]))
    assert not [x for x in out if x.method == "console.post"
                and (x.params.get("card") or {}).get("tra_loi_thanh") == "xung_dot"], \
        "hai phần tử khác nhau mà vẫn hỏi người giữ bản nào"
    can = a.store.get("criteria:sim-01")["canonical"]
    assert can["assert"][0]["nguong"] == 5.0 and can["assert"][1]["nguong"] == 99


def test_CUNG_mot_duong_dan_thi_VAN_hoi_nguoi(phien):
    a, core, out = phien()
    c = _tieu_chi(a)
    a.history.ghi_kho(author="agent:r2", artefact_id="criteria:sim-01", type="criteria",
                      op="update", explain=EX,
                      canonical={"ma": "sim-01",
                                 "assert": [{"ma": "A1", "nguong": 7.7, "phep_so": ">="},
                                            {"ma": "A2", "nguong": 10, "phep_so": "<="}]})
    out.clear()
    core.console_act(_sua("criteria:sim-01",
                          [{"path": "assert/0/nguong", "value": 5.0}], c["version"]))
    the = [x.params["card"] for x in out
           if x.method == "console.post" and x.params.get("card")]
    assert the and the[0].get("tra_loi_thanh") == "xung_dot"
    assert a.store.get("criteria:sim-01")["canonical"]["assert"][0]["nguong"] == 7.7


def test_sua_trinh_bay_SAU_trong_hien_vat_khong_danh_STALE(phien):
    a, core, out = phien()
    a.history.ghi_kho(author="agent:r", artefact_id="MH-1", type="ui_screen", op="create",
                      explain=EX,
                      canonical={"ten": "chinh",
                                 "phan_tu": [{"id": "p1", "x": 10, "mau": "#fff"}]})
    v = a.store.get("MH-1")["version"]
    core.console_act({"kind": "edit", "target": {"type": "ui_screen", "id": "MH-1"},
                      "data": {"base_version": f"v{v}",
                               "patch": [{"path": "phan_tu/0/mau", "value": "#000"}]},
                      "origin": {"surface": "screen"}, "note": "cho dễ nhìn"})
    cs = [x for x in a.history.log.all() if x.by_human][-1]
    assert cs.stale_marked == [], "đổi màu một nhãn không được làm cả chuỗi sáng đèn"
    assert "không đụng tới nội dung kỹ thuật" in _loi(out)


# =============================================================== bác bỏ
def test_bac_bo_ghi_vao_EIDE_md_muc_DUNG_va_danh_dau_hien_vat(phien):
    a, core, out = phien()
    a.history.ghi_kho(author="agent:r", artefact_id="PT-1", type="analysis", op="create",
                      explain=EX, canonical={"vi_sao": "hàm này không ai gọi"})
    core.console_act({"kind": "edit", "target": {"type": "analysis", "id": "PT-1"},
                      "data": {"base_version": "", "bac_bo": True},
                      "origin": {"surface": "code"},
                      "note": "nó là ISR, trình liên kết gọi qua bảng vector"})
    # Đọc đúng MỤC §Đừng, không phải cả tệp: `_nguoi_sua` cũng ghi một dòng vào §Người
    # vừa sửa, nên tìm "PT-1" trong cả tệp thì xanh kể cả khi §Đừng rỗng — phép phá
    # "không ghi vào §Đừng" LỌT ở lượt đầu đúng vì thế.
    dung = a.eide_md.dont_list()
    assert any("PT-1" in d and "bảng vector" in d for d in dung), dung
    can = a.store.get("PT-1")["canonical"]
    assert can["bac_bo"]["ly_do"].startswith("nó là ISR")
    cs = [x for x in a.history.log.all() if x.by_human][-1]
    assert cs.stale_marked == [], "bác bỏ một phát hiện không làm hạ nguồn lỗi thời"


# =============================================================== xác nhận Fact
def _fact(a, tier="BAC", fid="f-1"):
    a.store.put_fact({"fact_id": fid, "subject": "chip:X", "key": "vdd.max",
                      "value": "3.6", "unit": "V", "tier": tier, "origin": "extract",
                      "source": {"doc": "ds.pdf", "page": 12}, "explain": EX})
    return fid


def _xn(fid, verdict, note="tôi tra datasheet trang 12, đúng là 3,6 V", **d):
    return {"kind": "confirm", "target": {"type": "fact", "id": fid},
            "data": {"verdict": verdict, **d},
            "origin": {"surface": "knowledge", "block": "A4.2", "row": fid},
            "note": note}


def _tang(a, fid):
    return next(f["tier"] for f in a.store.query_facts(limit=99)
                if f["fact_id"] == fid)


def test_confirm_dung_nang_BAC_len_VANG_va_co_changeset(phien):
    a, core, out = phien()
    fid = _fact(a)
    core.console_act(_xn(fid, "dung"))
    assert _tang(a, fid) == "VANG"
    cs = [x for x in a.history.log.all() if x.by_human]
    assert len(cs) == 1 and cs[0].reversible, "nâng tầng phải hoàn tác được"
    assert "VÀNG" in _loi(out)


def test_confirm_KHONG_CO_LOI_NGUOI_thi_khong_nang(phien):
    """Tầng VÀNG nói “đã có người xác nhận”. Một xác nhận không có lời của người là một
    xác nhận của máy đội tên người."""
    a, core, out = phien()
    fid = _fact(a)
    core.console_act(_xn(fid, "dung", note=""))
    assert _tang(a, fid) == "BAC"
    assert "E8009" in str([c.params for c in out if c.method == "notice"])


def test_confirm_sai_ha_xuong_DONG_va_danh_dau_ha_nguon(phien):
    a, core, out = phien()
    fid = _fact(a)
    # Một hiện vật dựng TRÊN Fact ấy. Dùng `option` chứ không phải `analysis`:
    # `analysis` nằm trong `deps.KHONG_STALE` vì nó là một lát cắt của một lần đọc, và
    # đánh lỗi thời một lát cắt quá khứ thì vô nghĩa.
    a.history.ghi_kho(author="agent:r", artefact_id="TK-1", type="option", op="create",
                      explain=EX, canonical={"ten": "chọn trở theo vdd.max"},
                      deps={"upstream": [f"fact:{fid}"]})
    core.console_act(_xn(fid, "sai", note="bo của tôi là bản 2V8, số này của bản khác"))
    assert _tang(a, fid) == "DONG"
    assert a.store.get("TK-1")["stale"], "thứ dựng trên một con số vừa bị bác phải cần xem lại"


def test_confirm_sua_thanh_Fact_tang_NGUOI(phien):
    a, core, out = phien()
    fid = _fact(a)
    core.console_act(_xn(fid, "sua", gia_tri_moi="2.8",
                         note="tôi đo trên bo: 2,8 V"))
    f = next(x for x in a.store.query_facts(limit=99) if x["fact_id"] == fid)
    assert f["tier"] == "NGUOI" and str(f["value"]) == "2.8"
    assert "anh cho, chưa có tài liệu" in _loi(out)


def test_confirm_sua_thieu_gia_tri_va_phan_quyet_la(phien):
    a, core, out = phien()
    fid = _fact(a)
    core.console_act(_xn(fid, "sua"))
    assert _tang(a, fid) == "BAC"
    # KÈM `gia_tri_moi`: thiếu nó thì một phán quyết lạ rơi vào nhánh "sửa" rồi dừng ở
    # chỗ thiếu giá trị, và ca kiểm xanh vì một lý do khác lý do nó muốn đo.
    core.console_act(_xn(fid, "co_le_dung", gia_tri_moi="9.9"))
    assert _tang(a, fid) == "BAC", "phán quyết lạ mà vẫn đổi được tầng tin cậy"
    assert "Phán quyết lạ" in _canh_bao(out)
    core.console_act(_xn("f-khong-co", "dung"))
    assert "Không có Fact" in _canh_bao(out)


def test_confirm_KHONG_goi_mo_hinh(phien):
    a, core, out = phien()
    core.console_act(_xn(_fact(a), "dung"))
    assert a.llm._i == 0, "nâng tầng là việc mã làm được; không lượt mô hình nào"


# =============================================================== đặc tả sửa được (I8)
def test_khoi_khai_sua_duoc_va_giao_dien_khong_phai_doan():
    from eide import surfaces as S

    sd = S.sua_duoc("req", [S.truong("text", "Yêu cầu", kieu="van_ban_dai",
                                     bat_buoc=True)])
    assert sd["loai"] == "req" and sd["id_tu"] == "row"
    assert sd["truong"][0]["bat_buoc"] is True and sd["truong"][0]["gay_stale"] is True
    cu = S._sua_duoc_tu_cot_sua({"Yêu cầu": "text"}, "req")
    assert cu["truong"][0]["path"] == "text" and cu["truong"][0]["cot"] == "Yêu cầu"


def test_bang_REQ_mang_sua_duoc_va_van_giu_cot_sua_cu(du_an):
    """Bốn bảng cũ gửi `fields`, đi đường KHÔNG cần cờ. Gỡ `cot_sua` ngay là bắt người
    dùng bật một cờ mới mới sửa được thứ họ vẫn sửa."""
    from eide import surfaces as S
    from eide.store import Store, inventory
    from eide.protocol.ledger import Ledger

    cfg = Config.for_project(du_an)
    st = Store(cfg.paths.store_db)
    st.apply(artefact_id="FR-01", type="req", op="create", author="agent:r",
             canonical={"text": "x", "criteria": "y"}, explain=EX)
    m = S.requirements(st, inventory.build(st, ledger=Ledger(cfg.paths.ledger),
                                           project_name="t"), Ledger(cfg.paths.ledger))
    b = [x for x in m["blocks"] if x["code"] == "A2.1"][0]
    assert b["sua_duoc"]["loai"] == "req"
    assert "cot_sua" in b, "bỏ đường cũ cùng lúc là bắt người bật cờ mới mới sửa được"


def test_moi_be_mat_cua_loi_deu_gui_duoc_HumanAct():
    """Hai danh sách viết cùng một thứ ở hai nơi — và một trong hai đã lệch.

    `surfaces.SURFACES` có `screen` từ DEV-364; `humanact.SURFACES` thì không. Nên MỌI
    thao tác của người từ tab Màn hình bị `validate()` ném trả — một tab vẽ ra được, bấm
    được, và không gửi được gì. Chỉ lộ ra khi DEV-368 mở ô sửa ở đó.
    """
    from eide import surfaces as S
    from eide.protocol.humanact import SURFACES as HA

    thieu = [t for t, _, _ in S.SURFACES if t not in HA]
    assert not thieu, f"lõi vẽ bề mặt {thieu} mà người không gửi được gì từ đó"


def test_khong_tim_lai_duoc_BAN_GOC_thi_hoi_nguoi_chu_khong_ghi_de(phien):
    """Sổ changeset không có phiên bản người đã mở — không biết đường ấy có đổi hay
    không. Không biết thì hỏi, đừng đoán rồi ghi đè."""
    a, core, out = phien()
    a.store.apply(artefact_id="criteria:sim-02", type="criteria", op="create",
                  author="agent:r", explain=EX,
                  canonical={"assert": [{"ma": "A1", "nguong": 1}]})
    a.store.apply(artefact_id="criteria:sim-02", type="criteria", op="update",
                  author="agent:r", explain=EX,
                  canonical={"assert": [{"ma": "A1", "nguong": 2}]})
    out.clear()
    core.console_act(_sua("criteria:sim-02",
                          [{"path": "assert/0/nguong", "value": 5.0}], 1))
    the = [x.params["card"] for x in out
           if x.method == "console.post" and x.params.get("card")]
    assert the and the[0].get("tra_loi_thanh") == "xung_dot", \
        "không có bản gốc để so mà vẫn ghi đè"
    assert a.store.get("criteria:sim-02")["canonical"]["assert"][0]["nguong"] == 2
