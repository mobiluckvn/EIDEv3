# -*- coding: utf-8 -*-
"""Duyệt có sửa — EIDE-EDIT-47 §DEV-370.

Vòng người đang phải đi khi thấy một chỗ sai trong thẻ cổng:

    Không → gõ một câu mô tả chỗ cần sửa → đợi một lượt mô hình → hy vọng nó sửa đúng chỗ

Thẻ cổng chỉ có hai nút, và cả hai đều sai với tình huống thường gặp nhất: *đúng gần hết,
sai một dòng*. Duyệt thì ghi cả cái sai; từ chối thì vứt luôn phần đúng.

Hai thứ gói này canh, và cả hai đều về **ai viết dòng nào**:

* phần người sửa là một changeset RIÊNG `author=human` (§8 của tài liệu: "duyệt có sửa
  làm mờ ranh giới ai viết dòng này");
* hoàn tác changeset ấy thì về **đúng bản tác tử** — nên bản tác tử phải thật sự từng
  nằm trên đĩa.
"""

from __future__ import annotations

import pytest

from eide import Config, Core
from eide.errors import EideError
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

EX = {"summary": "ghi Makefile", "why": "để dịch được", "sources": [],
      "diff_prev": "bản đầu", "next": "—", "confidence": "VANG"}

BAN_TAC_TU = "CFLAGS = -O2 -Wall\nall:\n\t$(CC) $(CFLAGS) main.c\n"
BAN_NGUOI = "CFLAGS = -Og -g -Wall\nall:\n\t$(CC) $(CFLAGS) main.c\n"


@pytest.fixture
def phien(du_an):
    """Một lượt dừng ở cổng G-FILE vì mức tự chủ A1 — ghi tệp thì phải hỏi."""
    def _tao(co: bool = True, noi_dung: str = BAN_TAC_TU, path: str = "Makefile"):
        cfg = Config.for_project(du_an, autonomy="A1")
        cfg.features.duyet_co_sua = co
        cfg.features.cong_co_diff = True
        a = Agent(cfg, llm=ScriptedGateway([
            Response(tool_calls=[ToolCall("c1", "fs.write", {
                "path": path, "content": noi_dung, "explain": EX})]),
            Response(text="Đã ghi xong."),
            Response(text="Tiếp tục."),
        ]), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint)
        core.console_act({"kind": "say", "text": "viết Makefile giúp tôi"})
        gid = next(c.params["card"]["gate_id"] for c in out
                   if c.method == "console.post" and (c.params.get("card") or {}).get("gate_id"))
        out.clear()
        return a, core, out, gid
    return _tao


def _loi(out):
    return "\n".join(c.params.get("text", "") for c in out
                     if c.method == "console.post" and c.params.get("role") == "agent")


def _canh_bao(out):
    return " ".join(c.params.get("text", "") for c in out if c.method == "notice")


def _duyet(gid, **data):
    return {"kind": "decide", "data": {"gate_id": gid, "approved": True, **data},
            "origin": {"surface": "console"}, "note": "cờ -O2 làm mất thông tin gỡ lỗi"}


# =============================================================== lược đồ
def test_tu_choi_ma_kem_ban_da_sua_la_LOI_LUOC_DO():
    """Hai ý chí ngược nhau trong một thông điệp. Nhận nó thì lõi phải đoán — và đoán sai
    ở đây nghĩa là ghi một thứ người vừa từ chối."""
    from eide.protocol.humanact import HumanAct

    with pytest.raises(EideError):
        HumanAct.from_dict({"kind": "decide", "origin": {"surface": "console"},
                            "data": {"gate_id": "g-1", "approved": False,
                                     "amended": {"content": "x"}}})


def test_amended_sai_hinh_dang_thi_tu_choi():
    from eide.protocol.humanact import HumanAct

    for am in ("một chuỗi", {"linh tinh": 1}, []):
        with pytest.raises(EideError):
            HumanAct.from_dict({"kind": "decide", "origin": {"surface": "console"},
                                "data": {"gate_id": "g-1", "approved": True,
                                         "amended": am}})


# =============================================================== đường chính
def test_duyet_voi_ban_da_sua_ghi_dung_BAN_CUA_NGUOI(phien, du_an):
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))

    assert (du_an / "Makefile").read_text("utf-8") == BAN_NGUOI
    assert "anh sửa" in _loi(out)


def test_HAI_changeset_dung_thu_tu_va_dung_tac_gia(phien, du_an):
    """§8 của tài liệu: phần người sửa KHÔNG gộp vào changeset của tác tử."""
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))

    cham = [c for c in a.history.log.all()
            if any(t.artefact_id == "Makefile" for t in c.touches)]
    assert len(cham) == 2, [c.author for c in cham]
    assert cham[0].author.startswith("agent:") and cham[1].author == "human"


def test_hoan_tac_phan_NGUOI_thi_ve_dung_ban_TAC_TU(phien, du_an):
    """Lời hứa này chỉ giữ được nếu bản tác tử THẬT SỰ từng nằm trên đĩa — nên lõi chạy
    lời gọi nguyên bản trước, rồi mới áp bản của người lên trên."""
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))

    cs_nguoi = [c for c in a.history.log.all() if c.by_human][-1]
    kq = a.history.hoan_tac_changeset(cs_nguoi.id, by="human")
    assert kq.ok, kq.message_vi
    assert (du_an / "Makefile").read_text("utf-8") == BAN_TAC_TU


def test_mo_hinh_duoc_BAO_rang_no_dang_dung_tren_ban_cua_nguoi(phien, du_an):
    """Không báo thì lượt sau nó ghi đè lại bằng bản cũ của chính nó — và lần ấy không có
    cổng nào nổ, vì công cụ đã được duyệt trong lượt này."""
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))
    nhac = [str(m.get("text", "")) for m in a.messages
            if "ĐÃ SỬA nội dung" in str(m.get("text", ""))]
    assert nhac, "mô hình không được báo gì về bản của người"
    assert "BẢN CỦA HỌ" in nhac[0] and "đừng ghi đè lại" in nhac[0]


def test_so_cai_ghi_amended_de_ra_soat_lai_duoc(phien):
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))
    ev = [e.data for e in a.ledger.read() if e.kind == "gate" and e.data.get("amended")]
    assert ev and ev[0]["state"] == "approved" and ev[0]["changeset"].startswith("cs-")


def test_EIDE_md_ghi_lai_de_luot_sau_tac_tu_doc_duoc(phien, du_an):
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))
    md = (du_an / "EIDE.md").read_text("utf-8")
    assert "Makefile" in md.split("## Người vừa sửa", 1)[-1]


# =============================================================== cờ tắt
def test_co_TAT_thi_ghi_ban_tac_tu_va_NOI_RA(phien, du_an):
    """Im lặng bỏ qua phần người sửa là tệ nhất: họ bấm Duyệt, thấy tệp được ghi, và
    tưởng bản của mình đã vào."""
    a, core, out, gid = phien(co=False)
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))

    assert (du_an / "Makefile").read_text("utf-8") == BAN_TAC_TU
    assert "EIDE_FEATURE_DUYET_CO_SUA" in _canh_bao(out)
    assert not [c for c in a.history.log.all() if c.by_human]


def test_duyet_BINH_THUONG_khong_doi_gi(phien, du_an):
    """Cờ bật nhưng người không sửa gì — đường cũ phải y nguyên."""
    a, core, out, gid = phien()
    core.console_act(_duyet(gid))
    assert (du_an / "Makefile").read_text("utf-8") == BAN_TAC_TU
    assert not [c for c in a.history.log.all() if c.by_human]
    assert not [m for m in a.messages if "ĐÃ SỬA nội dung" in str(m.get("text", ""))]


# =============================================================== ca biên
def test_loi_goi_cua_tac_tu_HONG_thi_khong_ghi_phan_nguoi(phien, du_an):
    """`fs.write` vào một tệp đã có mà lượt này chưa đọc → E4020. Không có bản nào để
    sửa lên, nên phần người sửa cũng không được ghi lén."""
    (du_an / "Makefile").write_text("đã có sẵn\n", "utf-8")
    a, core, out, gid = phien()
    core.console_act(_duyet(gid, amended={"content": BAN_NGUOI}))
    assert (du_an / "Makefile").read_text("utf-8") == "đã có sẵn\n"
    assert not [c for c in a.history.log.all() if c.by_human]
    assert "chưa ghi" in _canh_bao(out)


def test_sua_HIEN_VAT_bang_patch_khi_duyet(phien, du_an):
    """`amended` nhận cả `patch`, không chỉ `content` — cùng đường với DEV-368."""
    cfg = Config.for_project(du_an, autonomy="A1")
    cfg.features.duyet_co_sua = True
    cfg.features.sua_long = True
    a = Agent(cfg, llm=ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "store.req_create", {
            "id": "FR-09", "loai": "FR", "text": "nhận tệp qua LAN",
            "criteria": "≥ 1 MB/s", "source_quote": "copy phim qua LAN",
            "explain": EX})]),
        Response(text="Đã ghi."), Response(text="Tiếp."),
    ]), project_name="du-an-thu")
    out: list = []
    core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint)
    core.console_act({"kind": "say", "text": "ghi yêu cầu giúp tôi"})
    the = [c.params["card"] for c in out
           if c.method == "console.post" and (c.params.get("card") or {}).get("gate_id")]
    if not the:
        pytest.skip("mức tự chủ này không dựng cổng cho store.req_create")
    core.console_act(_duyet(the[0]["gate_id"],
                            amended={"patch": [{"path": "criteria", "value": "≥ 5 MB/s"}],
                                     "artefact_id": "FR-09"}))
    assert a.store.get("FR-09")["canonical"]["criteria"] == "≥ 5 MB/s"
    assert [c for c in a.history.log.all() if c.by_human]


def test_cot_phai_cua_the_cong_chi_SUA_DUOC_khi_co_bat(du_an):
    """Mở ô sửa khi lõi chưa nhận được bản sửa là dựng một cái nút nuốt việc của người:
    họ gõ lại cả một đoạn mã, bấm Duyệt, và bản của tác tử vẫn là thứ được ghi."""
    for bat in (False, True):
        cfg = Config.for_project(du_an, autonomy="A1")
        cfg.features.cong_co_diff = True
        cfg.features.duyet_co_sua = bat
        a = Agent(cfg, llm=ScriptedGateway([
            Response(tool_calls=[ToolCall("c1", "fs.write", {
                "path": f"M-{bat}.mk", "content": BAN_TAC_TU, "explain": EX})]),
            Response(text="chờ duyệt"),
        ]), project_name="du-an-thu")
        out: list = []
        Core(a.ledger, a.ids, a.turn, on_emit=out.append,
             on_sync=a.paint).console_act({"kind": "say", "text": "ghi giúp tôi"})
        d = [c.params for c in out if c.method == "diff.show"]
        assert d, "cờ diff bật mà không có khối diff nào"
        assert d[0]["cho_phep_sua"] is bat
