# -*- coding: utf-8 -*-
"""Hai cú bấm cho một hiện vật lỗi thời — EIDE-EDIT-47 §7 / §DEV-373.

Đo được 12/10/2026 bằng `tools/do_edit47.py` trên sổ cái 39 dự án thật: **7 lần** hạ nguồn
bị đánh STALE rồi **không ai cập nhật**. Đồ thị phụ thuộc chạy đúng, băng cảnh báo hiện
đúng — chỗ thiếu là đường đi của người.

Tới gói này, cả hai việc người muốn làm với một hiện vật lỗi thời đều phải GÕ MỘT CÂU:

* *"cập nhật đi"* → một lượt mô hình, và lời nhờ do người tự soạn nên nó không mang theo
  danh sách hiện vật lẫn lý do lỗi thời — mô hình phải tự đi tìm;
* *"thôi, giữ nguyên"* → công cụ `stale.accept` có từ bước G5 và **chỉ tác tử gọi được**,
  nên người phải nhờ mô hình làm một việc kế toán.

`deps.py` nói ra chỗ thiếu ấy ngay trong docstring của nó — *"phải có nút chấp nhận
STALE"*. Nút đó chưa bao giờ được vẽ.
"""

from __future__ import annotations

import pathlib

import pytest

from eide import Config, Core, surfaces
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

GOC = pathlib.Path(__file__).resolve().parents[1]

EX = {"summary": "ghi", "why": "w", "sources": [], "diff_prev": "đầu", "next": "—",
      "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    def _tao(script: list | None = None):
        a = Agent(Config.for_project(du_an), llm=ScriptedGateway(script or []),
                  project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _dung_chuoi(a):
    """REQ → mã → build. Sửa REQ thì `build:firmware` thành lỗi thời."""
    a.store.apply(artefact_id="FR-01", type="req", op="create", author="agent:run-1",
                  canonical={"text": "≥ 1 MB/s"}, explain=EX)
    a.store.apply(artefact_id="build:firmware", type="build", op="create",
                  author="agent:run-1", explain=EX,
                  canonical={"dat": True, "flash": 1234},
                  deps={"upstream": ["FR-01"]})


def _sua_req(core, text="≥ 5 MB/s"):
    core.console_act({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
                      "data": {"base_version": "v1", "fields": {"text": text}},
                      "origin": {"surface": "requirements"}})


def _a11(a):
    from eide.store import inventory

    inv = inventory.build(a.store, ledger=a.ledger, project_name="du-an-thu")
    mat = surfaces.history(a.store, inv, a.history)
    return {b["code"]: b for b in mat["blocks"]}


def _tb(out):
    return " ".join(c.params.get("text", "") for c in out if c.method == "notice")


def _loi(out):
    return "\n".join(c.params.get("text", "") for c in out
                     if c.method == "console.post" and c.params.get("role") == "agent")


# ======================================================== lõi khai ra hai cái nút
def test_A11_4_KHAI_hai_hanh_dong_tren_tung_dong(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)

    k = _a11(a)["A11.4"]
    assert k["type"] == "table", "một danh sách chuỗi thì không có chỗ nào để đặt nút"
    assert ["build:firmware", "build"] == k["rows"][0][:2]

    hd = {h["ma"]: h for h in k["hanh_dong"]}
    assert set(hd) == {"cap_nhat_tat_ca", "cap_nhat_mot", "chap_nhan"}
    # Lõi khai GỬI GÌ, giao diện không suy (I8 mở rộng cho việc làm).
    assert hd["chap_nhan"]["kind"] == "edit"
    assert hd["chap_nhan"]["target"] == {"type": "{loai}", "id": "{ma}"}
    assert hd["chap_nhan"]["data"] == {"chap_nhan_stale": True}
    assert hd["chap_nhan"]["can_ly_do"] is True
    assert not hd["chap_nhan"].get("ton_token")
    # Nút tốn tiền thì PHẢI tự khai là tốn tiền.
    assert hd["cap_nhat_tat_ca"]["ton_token"] is True
    assert hd["cap_nhat_tat_ca"]["muc"] == "khoi"
    assert hd["cap_nhat_mot"]["muc"] == "dong"


def test_KHONG_co_gi_STALE_thi_o_trong_noi_that(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    k = _a11(a)["A11.4"]
    assert k["type"] == "empty" and "hai nút" in k["can_gi"]


def test_APP_doc_duoc_hanh_dong_ay():
    """Lõi khai mà app không đọc thì cái nút không tồn tại với người dùng."""
    sv = (GOC / "ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift").read_text("utf-8")
    hd = (GOC / "ui/EIDEApp/Sources/EIDE/Views/HanhDong.swift").read_text("utf-8")
    assert 'block.arr("hanh_dong")' in sv and "NutHanhDong(" in sv
    assert 'raw["can_ly_do"]' in hd and 'of: "{ma}"' in hd


# ======================================================== chấp nhận STALE (0 token)
def test_chap_nhan_stale_TAT_bang_canh_bao_va_HOAN_TAC_DUOC(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)
    assert a.store.get("build:firmware")["stale"] is True
    ly_do_cu = a.store.get("build:firmware")["stale_reason"]
    out.clear()

    core.console_act({"kind": "edit",
                      "target": {"type": "build", "id": "build:firmware"},
                      "data": {"chap_nhan_stale": True},
                      "note": "bản dựng này chỉ để đo kích thước, ngưỡng mới không đụng tới",
                      "origin": {"surface": "history", "block": "A11.4"}})

    hv = a.store.get("build:firmware")
    assert hv["stale"] is False
    assert "chấp nhận STALE" in hv["stale_reason"]
    assert hv["canonical"] == {"dat": True, "flash": 1234}, \
        "tắt một cái cờ KHÔNG được sửa nội dung hiện vật"
    assert hv["version"] == 1, "cũng không được sinh phiên bản mới"

    cs = [c for c in a.history.log.all() if c.by_human][-1]
    assert cs.reversible and any(f.get("kind") == "stale" for f in cs.forward)
    assert "bản dựng này chỉ để đo" in (cs.note or "")

    # Và hoàn tác thì cờ bật lại NGUYÊN VĂN lý do cũ — không phải một câu dựng lại.
    kq = a.history.hoan_tac_changeset(cs.id, by="human")
    assert kq.ok, kq.message_vi
    sau = a.store.get("build:firmware")
    assert sau["stale"] is True and sau["stale_reason"] == ly_do_cu


def test_chap_nhan_stale_KHONG_TON_MOT_LUOT_MO_HINH(phien, du_an):
    """Việc này là kế toán: mã làm xong trong một dòng. Nhờ mô hình làm nó là đốt tiền
    cho một phép ghi."""
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)
    a.llm.script = []          # mô hình KHÔNG có gì để trả lời; gọi là đổ ngay
    a.llm._i = 0

    core.console_act({"kind": "edit",
                      "target": {"type": "build", "id": "build:firmware"},
                      "data": {"chap_nhan_stale": True}, "note": "giữ nguyên, tôi biết",
                      "origin": {"surface": "history", "block": "A11.4"}})
    assert a.store.get("build:firmware")["stale"] is False
    assert not [e for e in a.ledger.read() if e.kind == "llm_call"]


def test_chap_nhan_stale_BAT_BUOC_co_ly_do(phien, du_an):
    """Một hiện vật lỗi thời bị tắt cảnh báo mà không ai ghi vì sao thì sáu tháng sau
    không ai dám tin nó, và cũng không ai dám bật lại."""
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)
    out.clear()

    core.console_act({"kind": "edit",
                      "target": {"type": "build", "id": "build:firmware"},
                      "data": {"chap_nhan_stale": True},
                      "origin": {"surface": "history", "block": "A11.4"}})

    assert a.store.get("build:firmware")["stale"] is True, "không lý do thì không tắt"
    assert "vì sao" in _tb(out)


def test_chap_nhan_mot_hien_vat_KHONG_lo_thoi_thi_noi_that(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    out.clear()
    core.console_act({"kind": "edit",
                      "target": {"type": "build", "id": "build:firmware"},
                      "data": {"chap_nhan_stale": True}, "note": "thử",
                      "origin": {"surface": "history", "block": "A11.4"}})
    assert "không đang lỗi thời" in _tb(out)
    assert not [c for c in a.history.log.all() if c.by_human]


def test_TAC_TU_BIET_nguoi_da_chap_nhan(phien, du_an):
    """Thiếu dòng này thì lượt sau tác tử vẫn thấy hiện vật ấy trong danh sách "cần dựng
    lại" và lại đề nghị dựng lại đúng thứ người vừa quyết giữ nguyên."""
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)
    core.console_act({"kind": "edit",
                      "target": {"type": "build", "id": "build:firmware"},
                      "data": {"chap_nhan_stale": True},
                      "note": "chỉ đo kích thước, không đụng ngưỡng",
                      "origin": {"surface": "history", "block": "A11.4"}})
    md = a.config.paths.eide_md.read_text("utf-8")
    assert "build:firmware" in md and "chỉ đo kích thước" in md


# ======================================================== cập nhật hạ nguồn (LÕI soạn)
def test_loi_nho_do_LOI_SOAN_mang_theo_danh_sach_va_cach_dung_lai(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)

    from eide.protocol.humanact import HumanAct

    act = HumanAct.from_dict({
        "kind": "say", "text": "Cập nhật những hiện vật đang lỗi thời.",
        "data": {"nut": "cap_nhat_ha_nguon"},
        "origin": {"surface": "history", "block": "A11.4"}})
    lenh = a._lenh_cap_nhat_ha_nguon(act)

    assert "build:firmware" in lenh, "thiếu danh sách thì mô hình phải tự đi tìm"
    assert "build.compile" in lenh, "lõi biết công cụ dựng lại — phải nói ra"
    assert "lỗi thời vì" in lenh, "lý do lỗi thời là thứ quyết định dựng lại cái gì trước"
    # Hai điều cấm, nói ra trong chính lời nhờ.
    assert "stale.accept" in lenh and "để nguyên cờ" in lenh


def test_loi_nho_CHI_MOT_hien_vat_khi_nguoi_bam_tren_mot_dong(phien, du_an):
    a, core, out = phien()
    _dung_chuoi(a)
    a.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                  author="agent:run-1", canonical={"dat": True}, explain=EX,
                  deps={"upstream": ["FR-01"]})
    _sua_req(core)

    from eide.protocol.humanact import HumanAct

    act = HumanAct.from_dict({
        "kind": "say", "text": "Cập nhật build:firmware.",
        "data": {"nut": "cap_nhat_ha_nguon", "hien_vat": ["build:firmware"]},
        "origin": {"surface": "history", "block": "A11.4"}})
    lenh = a._lenh_cap_nhat_ha_nguon(act)
    assert "build:firmware" in lenh and "sim_result:can-bang" not in lenh


def test_bam_nut_khi_KHONG_con_gi_lo_thoi_thi_noi_that(phien, du_an):
    from eide.protocol.humanact import HumanAct

    a, core, out = phien()
    _dung_chuoi(a)
    lenh = a._lenh_cap_nhat_ha_nguon(HumanAct.from_dict({
        "kind": "say", "text": "Cập nhật.", "data": {"nut": "cap_nhat_ha_nguon"},
        "origin": {"surface": "history"}}))
    assert "KHÔNG còn hiện vật nào lỗi thời" in lenh
    assert "đừng dựng lại gì" in lenh


def test_cau_NGUOI_GO_binh_thuong_khong_bi_thay(phien, du_an):
    """Chỉ lần bấm NÚT mới được thay lời; một câu người gõ phải tới mô hình nguyên văn."""
    from eide.protocol.humanact import HumanAct

    a, core, out = phien()
    _dung_chuoi(a)
    _sua_req(core)
    assert a._lenh_cap_nhat_ha_nguon(HumanAct.from_dict({
        "kind": "say", "text": "cập nhật hạ nguồn giúp tôi",
        "origin": {"surface": "history"}})) == ""


def test_LOI_NHO_toi_mo_hinh_that_khi_nguoi_bam(phien, du_an):
    """Đường thật: lõi soạn đơn công việc, và nó phải nằm trong thứ GỬI ĐI cho mô hình —
    không chỉ tồn tại trong một hàm không ai gọi."""
    a, core, out = phien([Response(text="Tôi dựng lại rồi.")])
    _dung_chuoi(a)
    _sua_req(core)

    core.console_act({"kind": "say", "text": "Cập nhật những hiện vật đang lỗi thời.",
                      "data": {"nut": "cap_nhat_ha_nguon"},
                      "origin": {"surface": "history", "block": "A11.4"}})

    gui = [m for m in a.messages if m.get("role") == "user"]
    assert any("build.compile" in str(m.get("text", "")) for m in gui), \
        [str(m.get("text", ""))[:80] for m in gui]
    # Và dòng hội thoại người đọc vẫn là câu của người, không phải đơn công việc.
    assert "Cập nhật những hiện vật đang lỗi thời." in str(
        [e.data.get("text") for e in a.ledger.read() if e.kind == "human_act"])


def test_bang_CONG_CU_LAM_MOI_noi_KHONG_BIET_o_cho_khong_biet(phien):
    """Một bảng đoán bừa sẽ bảo tác tử gọi `build.compile` cho một `netlist`, và nó sẽ
    thử — rồi báo lỗi như thể dự án hỏng."""
    a, _, _ = phien()
    b = a.CONG_CU_LAM_MOI
    assert b["build"] == "build.compile"
    assert "không có công cụ sinh tự động" in b["code"]
    assert "KHÔNG tự nạp bo" in b["target"]
    # Mọi loại trong bảng phải là loại CÓ THẬT trong đồ thị phụ thuộc.
    from eide import deps

    moi_loai = set(deps.HA_NGUON) | {t for v in deps.HA_NGUON.values() for t in v}
    assert set(b) <= moi_loai, set(b) - moi_loai


def test_nut_cap_nhat_KHONG_lam_xau_chi_so_cua_chinh_no():
    """Chỉ số 2 của §7 đếm "lượt người GÕ LỜI cho việc lẽ ra bấm được". Một lần bấm nút
    gửi `say`, nên nếu bộ đo không phân biệt thì **cái nút tự làm xấu con số mà nó sinh ra
    để cải thiện** — và lần đo sau sẽ nói ngược lại sự thật."""
    import sys

    sys.path.insert(0, str(GOC / "tools"))
    import do_edit47 as do

    # Chữ của nút hôm nay (*"Cập nhật …"*) tình cờ KHÔNG chứa từ khoá nào của §7, nên
    # hôm nay nó không lọt. Phép lọc vẫn phải có: chữ trên nút là thứ đổi được bất cứ
    # lúc nào, và lúc nó đổi thì chỉ số sẽ xấu đi vì một lý do chẳng liên quan gì tới
    # người dùng. Nên ca kiểm dựng đúng tình huống ấy.
    so = [
        {"kind": "human_act", "ts": "2026-10-01T10:00:00+00:00",
         "data": {"kind": "say", "text": "Sửa FR-01 thành 5 MB/s giúp tôi"}},
        {"kind": "human_act", "ts": "2026-10-01T10:01:00+00:00",
         "data": {"kind": "say", "text": "Dựng lại và sửa FR-01 nếu cần.",
                  "data": {"nut": "cap_nhat_ha_nguon"}}},
    ]
    g = do._goi_loi_le_ra_bam_duoc(so, {"FR-01": "req"}, {"req"})
    assert len(g["bam_duoc"]) == 1, "câu bấm NÚT không phải câu người gõ"
    assert len(g["tu_nut"]) == 1

    # Và chữ của nút THẬT hôm nay: kiểm bằng chính thứ lõi khai, không bằng ký ức.
    from eide.surfaces import hanh_dong

    h = hanh_dong("x", "Cập nhật", "say", text="Cập nhật {ma}.",
                  data={"nut": "cap_nhat_ha_nguon"})
    assert h["data"]["nut"] == "cap_nhat_ha_nguon"
