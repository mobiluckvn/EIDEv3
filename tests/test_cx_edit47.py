# -*- coding: utf-8 -*-
"""Bộ ca cộng tác CX cho EIDE-EDIT-47 — CX17…CX25, mỗi gói một ca.

§7 của tài liệu đòi: *"Thêm bộ ca CX mới `tests/kich_ban/cx_edit47_*.py` theo mẫu CX05/CX08:
mỗi gói một ca 'đi đúng đường người đi'"*.

**Lệch có ý về chỗ đặt tệp.** Đặc tả nói `tests/kich_ban/cx_edit47_*.py`; tệp này ở
`tests/test_cx_edit47.py`. Lý do đo được: `pytest` chỉ thu các tệp khớp `test_*.py`, nên
một bộ ca tên `cx_edit47_*.py` trong `tests/kich_ban/` **sẽ không bao giờ chạy** trong
`pytest -q` — đúng loại lỗi mà cả gói EDIT-47 sinh ra để vá (cơ chế có sẵn, đường dẫn tới
nó đứt). CX01–CX16 của MDD-40 cũng nằm ở `tests/test_cx_cong_tac.py` vì cùng lý do; bộ này
nối tiếp số thứ tự ấy.

**Nó khác gì chín bộ `test_edit47_*.py` đã có?** Chúng đo từng cơ chế. Bộ này đo **chuyện
cộng tác**: tác tử làm gì → người xen vào → và **lượt SAU của tác tử có thấy không**. Đó là
chiều mà một bộ ca đơn vị không chạm tới, và là chiều N9 nói về:

    CX17  Người lùi CẢ MỘT LƯỢT của tác tử → lượt sau nó biết, và không làm lại (DEV-365)
    CX18  Hai bên sửa cùng một tệp → thẻ xung đột có HAI BẢN THẬT, giải bằng mã (DEV-366)
    CX19  Người đang mở tệp trong app → tác tử ghi tệp ấy phải hỏi (DEV-367)
    CX20  Người sửa SÂU một ô → chỉ ô ấy đổi, hạ nguồn STALE, lượt sau tác tử nhắc (DEV-368)
    CX21  Người sửa tệp BẰNG VS CODE → changeset, và lượt sau tác tử bị buộc nhắc (DEV-369)
    CX22  Người duyệt KÈM BẢN ĐÃ SỬA → đĩa là bản của họ, hai changeset (DEV-370)
    CX23  Người bật một cờ từ A14, và năm lời gọi cài cùng gói chỉ ra một thẻ (DEV-371)
    CX24  Hoàn tác thành công/thất bại đều vào sổ cái, kèm TẦNG (DEV-372)
    CX25  Hai cú bấm trên hiện vật lỗi thời: cập nhật, hoặc chấp nhận (DEV-373)
"""

from __future__ import annotations

import time

import pytest

from eide import Agent, Config, Core
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import GIU_BAN_DA_SUA, GIU_BAN_TAC_TU


def EX(s: str) -> dict:
    return {"summary": s, "why": "theo yêu cầu trong lượt này",
            "sources": [{"kind": "human_act", "ref": "h-0001", "tier": "NGUOI"}],
            "diff_prev": "bản đầu tiên", "next": "chờ người xem lại",
            "confidence": "NGUOI"}


@pytest.fixture
def du_an_cx(tmp_path):
    d = tmp_path / "du-an-cx"
    d.mkdir()
    (d / "drv_eth.c").write_text(
        "// driver ethernet\nint init(void) {\n    return 0;\n}\n", "utf-8")
    return d


@pytest.fixture
def phien(du_an_cx):
    """`(tao, chay, hop)` — cùng khuôn với `test_cx_cong_tac.py`."""
    hop: dict = {}

    def tao(script, **co):
        cfg = Config.for_project(du_an_cx, **{k: v for k, v in co.items()
                                             if k == "autonomy"})
        for k, v in co.items():
            if k != "autonomy":
                setattr(cfg.features, k, v)
        a = Agent(cfg, llm=ScriptedGateway(script), project_name="du-an-cx")
        hop["agent"] = a
        hop["out"] = []
        hop["core"] = Core(a.ledger, a.ids, a.turn, on_emit=hop["out"].append,
                           on_sync=a.paint, on_query=a.hoi_chi_doc)
        return a

    def chay(act, script=None):
        a = hop["agent"]
        if script is not None:
            a.llm.script = ScriptedGateway(script).script
            a.llm._i = 0
        truoc = len(hop["out"])
        hop["core"].console_act(act)
        return hop["out"][truoc:]

    return tao, chay, hop


def loi_tac_tu(cmds) -> str:
    return "\n".join(c.params.get("text", "") for c in cmds
                     if c.method == "console.post" and c.params.get("role") == "agent")


def the(cmds) -> list[dict]:
    return [c.params["card"] for c in cmds
            if c.method == "console.post" and c.params.get("card")]


def nhac_cho_mo_hinh(a) -> str:
    return "\n".join(str(m.get("text", "")) for m in a.messages
                     if m.get("role") == "user")


def _ghi_req(a, ma="FR-01", text="≥ 1 MB/s", **kw):
    a.store.apply(artefact_id=ma, type="req", op="update" if a.store.get(ma) else "create",
                  author="agent:run-0", canonical={"text": text}, explain=EX("req"), **kw)


# =========================================================================== CX17
def test_CX17_nguoi_lui_ca_mot_luot_thi_luot_sau_tac_tu_biet(phien, du_an_cx):
    """DEV-365 tầng 3. Lùi một changeset thì tác tử có thể không để ý; lùi **cả lượt** là
    người nói *"bỏ hết đi"* — và lượt sau nó phải biết để không làm lại đúng thứ ấy."""
    tao, chay, hop = phien
    a = tao([
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;",
            "new_string": "return init_phy();",
            "explain": EX("nối driver với PHY")})]),
        Response(text="Đã sửa drv_eth.c."),
    ])
    chay({"kind": "say", "text": "nối driver ethernet với PHY"})
    run = [c.run_id for c in a.history.log.all() if c.run_id][-1]
    assert "init_phy" in (du_an_cx / "drv_eth.c").read_text("utf-8")

    cmds = chay({"kind": "undo", "target": {"type": "run", "id": run},
                 "data": {"mode": "revert"}, "origin": {"surface": "history"}})

    assert "init_phy" not in (du_an_cx / "drv_eth.c").read_text("utf-8"), "đĩa phải lùi"
    assert "hoàn tác" in loi_tac_tu(cmds).lower()
    # Lượt SAU: mô hình đọc được rằng việc ấy đã bị lùi, kèm lệnh đừng làm lại.
    nhac = nhac_cho_mo_hinh(a)
    assert "vừa hoàn tác" in nhac and "Đừng làm lại" in nhac
    # Và sổ cái ghi kết quả kèm tầng (DEV-372) — không phải suy từ chỗ khác.
    u = [e.data for e in a.ledger.read() if e.kind == "undo"]
    assert u and u[-1]["tang"] == "run" and u[-1]["ok"] is True


# =========================================================================== CX18
def test_CX18_hai_ben_sua_mot_tep_thi_the_xung_dot_co_hai_ban_that(phien, du_an_cx):
    """DEV-366. Trước gói ấy, ba chỗ trong app nói "xem diff" mà không có gì để xem; và
    câu trả lời của người rơi xuống vòng lặp công cụ — mô hình tự nghĩ cách ghi lại tệp
    dù nó **chỉ thấy câu trả lời, không thấy hai bản**."""
    tao, chay, hop = phien
    a = tao([])
    cmds = chay({"kind": "edit", "target": {"type": "file", "id": "drv_eth.c"},
                 "data": {"base_version": "hash-cu-khong-con-dung",
                          "content": "// bản của anh\n"},
                 "origin": {"surface": "code"}})

    d = [c.params for c in cmds if c.method == "diff.show"]
    assert d, "phải phát một diff gắn vào thẻ"
    assert d[0]["trai"]["noi_dung"] and d[0]["phai"]["noi_dung"], "hai bản THẬT"
    t = [x for x in the(cmds) if x.get("tra_loi_thanh") == "xung_dot"]
    assert t and d[0]["gan_voi"]["card_id"] == t[0]["card_id"]

    goi_truoc = a.llm._i
    cmds = chay({"kind": "choose",
                 "data": {"card_id": t[0]["card_id"],
                          "answers": {"chon": GIU_BAN_TAC_TU}},
                 "origin": {"surface": "console"}})
    assert a.llm._i == goi_truoc, "ba lựa chọn đều là việc mã làm được — 0 token"
    assert not a.pending_cards, "thẻ đã trả lời phải rời hàng chờ"
    assert (du_an_cx / "drv_eth.c").read_text("utf-8").startswith("// driver ethernet")


# =========================================================================== CX19
def test_CX19_nguoi_dang_mo_tep_thi_tac_tu_ghi_tep_ay_phai_hoi(phien, du_an_cx):
    """DEV-367, nửa còn thiếu của khoá mềm. Lõi biết "người ĐÃ sửa" (qua changeset) nhưng
    không biết "người ĐANG sửa" — và giữa hai cái ấy là đúng khoảng thời gian người gõ dở
    một hàm và chưa bấm Lưu."""
    tao, chay, hop = phien
    a = tao([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "drv_eth.c", "content": "// tác tử ghi đè\n",
            "explain": EX("viết lại driver")})]),
        Response(text="Xong."),
        Response(text="Tiếp tục."),
    ], autonomy="A3", khoa_nguoi=True)

    chay({"kind": "attend", "data": {"path": "drv_eth.c", "dang_sua": True},
          "origin": {"surface": "code", "block": "editor", "row": "drv_eth.c"}})
    assert a.locks_nguoi.get("drv_eth.c"), "lõi phải biết người đang mở tệp nào"

    cmds = chay({"kind": "say", "text": "viết lại driver giúp tôi"})
    cong = [x for x in the(cmds) if x.get("gate") == "G-FILE"]
    assert cong, [x.get("gate") for x in the(cmds)]
    assert (du_an_cx / "drv_eth.c").read_text("utf-8").startswith("// driver ethernet"), \
        "chưa ai duyệt thì bản của người còn nguyên"

    # Người duyệt. HAI LỚP là hai lớp thật: lời gọi được chạy lại, và `E4020` ("chưa đọc
    # thì chưa ghi đè") vẫn đỡ phía sau — tác tử chưa hề đọc tệp người đang gõ dở. Rồi
    # NGAY TRONG LƯỢT ẤY nó đi đường đúng: đọc trước, ghi sau.
    cmds = chay({"kind": "decide",
                 "data": {"gate_id": cong[0]["gate_id"], "approved": True},
                 "origin": {"surface": "console"}}, script=[
        Response(tool_calls=[ToolCall("c2", "fs.read", {"path": "drv_eth.c"})]),
        Response(tool_calls=[ToolCall("c3", "fs.write", {
            "path": "drv_eth.c", "content": "// tác tử ghi sau khi ĐỌC\n",
            "explain": EX("viết lại driver, đã đọc bản của anh")})]),
        Response(text="Đã ghi, sau khi đọc bản của anh."),
    ])
    ket = [(m.get("result") or {}).get("code") for m in a.messages
           if m.get("role") == "tool"]
    assert "E4020" in ket, ket
    assert (du_an_cx / "drv_eth.c").read_text("utf-8") == "// tác tử ghi sau khi ĐỌC\n"
    assert not [x for x in the(cmds) if x.get("gate") == "G-FILE"], \
        "đã duyệt trong lượt này thì KHÔNG hỏi lại"


# =========================================================================== CX20
def test_CX20_nguoi_sua_SAU_mot_o_thi_chi_o_ay_doi_va_luot_sau_tac_tu_nhac(phien):
    """DEV-368. Sửa một ô trong bảng con mà làm đổ cả hiện vật thì người sẽ không dám sửa
    nữa; và đổi một ô mà tác tử không biết thì nó dựng tiếp trên một thước đã khác."""
    tao, chay, hop = phien
    a = tao([], sua_long=True)
    a.store.apply(artefact_id="criteria:sim-01", type="criteria", op="create",
                  author="agent:run-0", explain=EX("tiêu chí"),
                  canonical={"ma": "sim-01",
                             "assert": [{"ma": "A1", "mo_ta": "dòng nghỉ",
                                         "phep_so": "<=", "nguong": 3.3, "don_vi": "mA"},
                                        {"ma": "A2", "mo_ta": "khởi động",
                                         "phep_so": "<=", "nguong": 10, "don_vi": "ms"}]})
    a.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                  author="agent:run-0", canonical={"dat": True}, explain=EX("kết quả"),
                  deps={"upstream": ["criteria:sim-01"]})

    cmds = chay({"kind": "edit",
                 "target": {"type": "criteria", "id": "criteria:sim-01"},
                 "data": {"base_version": "v1",
                          "patch": [{"path": "assert/1/nguong", "op": "set", "value": 42}],
                          "summary": "nới ngưỡng khởi động"},
                 "note": "bo thật khởi động chậm hơn mô phỏng"})

    ds = a.store.get("criteria:sim-01")["canonical"]["assert"]
    assert ds[1]["nguong"] == 42, "ô người sửa phải đổi"
    assert ds[0]["nguong"] == 3.3, "ô bên cạnh KHÔNG được đụng tới"
    assert ds[1]["mo_ta"] == "khởi động", "trường khác của cùng dòng cũng không"

    # Hạ nguồn: kết quả cũ đo bằng một thước đã khác.
    assert [x["id"] for x in a.store.list(stale_only=True)] == ["sim_result:can-bang"]
    assert "cần xem lại" in loi_tac_tu(cmds) or "xem lại" in loi_tac_tu(cmds)
    # Lượt sau tác tử phải nhắc — hook Stop đọc đúng danh sách này.
    assert len(a.history.log.human_unacknowledged()) == 1
    assert "bo thật khởi động chậm" in a.eide_md.get("Người vừa sửa")


# =========================================================================== CX21
def test_CX21_nguoi_sua_bang_VS_CODE_thi_tac_tu_bi_buoc_nhac(phien, du_an_cx):
    """DEV-369. Luật nền số 3 nói *"mọi thay đổi gỡ lại được, kể cả do người gõ"* — và câu
    ấy từng chỉ đúng với thứ sửa TRONG app."""
    tao, chay, hop = phien
    a = tao([], watcher=True)
    a._watcher_emit = hop["out"].append

    # Ghi thẳng vào đĩa, không qua app — đúng như VS Code làm.
    (du_an_cx / "drv_eth.c").write_text("// anh sửa bằng VS Code\n", "utf-8")
    a._tep_doi_ngoai_eide(["drv_eth.c"])

    cs = [c for c in a.history.log.all() if a.history.tom_tat(c)["ngoai_eide"]]
    assert len(cs) == 1 and cs[0].author == "human" and cs[0].reversible
    assert "drv_eth.c" in a.eide_md.get("Người vừa sửa")

    # Lượt sau: mô hình cư xử TỆ — nói một câu không liên quan. Hook Stop phải bắt thêm
    # một vòng, đúng như CX07 đòi với sửa trong app.
    truoc = len(a.llm.calls)
    cmds = chay({"kind": "say", "text": "làm tiếp đi"}, script=[
        Response(text="Hôm nay trời đẹp."),
        Response(text="Anh vừa sửa drv_eth.c bên ngoài EIDE — tôi đọc lại trước khi sửa."),
    ])
    assert len(a.llm.calls) - truoc == 2, "Stop hook phải bắt thêm một vòng"
    assert "drv_eth.c" in loi_tac_tu(cmds)
    assert not a.history.log.human_unacknowledged()


# =========================================================================== CX22
def test_CX22_nguoi_duyet_kem_ban_da_sua(phien, du_an_cx):
    """DEV-370. Thẻ cổng chỉ có hai nút, và cả hai đều sai với tình huống thường gặp nhất:
    *đúng gần hết, sai một dòng*."""
    tao, chay, hop = phien
    ban_tac_tu = "CFLAGS = -O2 -Wall\nall:\n\t$(CC) $(CFLAGS) main.c\n"
    ban_nguoi = "CFLAGS = -Og -g -Wall\nall:\n\t$(CC) $(CFLAGS) main.c\n"
    a = tao([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "Makefile", "content": ban_tac_tu,
            "explain": EX("viết Makefile")})]),
        Response(text="Đã ghi Makefile."),
        Response(text="Tiếp tục."),
    ], autonomy="A1", cong_co_diff=True, duyet_co_sua=True)

    cmds = chay({"kind": "say", "text": "viết Makefile giúp tôi"})
    gid = [x["gate_id"] for x in the(cmds) if x.get("gate_id")][0]

    chay({"kind": "decide",
          "data": {"gate_id": gid, "approved": True,
                   "amended": {"content": ban_nguoi}},
          "origin": {"surface": "console"},
          "note": "-O2 làm mất thông tin gỡ lỗi"})

    assert (du_an_cx / "Makefile").read_text("utf-8") == ban_nguoi
    cs = a.history.log.all()
    assert any(c.by_human for c in cs), "phần người sửa là một changeset RIÊNG"
    cua_nguoi = [c for c in cs if c.by_human][-1]
    assert cua_nguoi.reversible
    # Hoàn tác phần của người → về đúng bản tác tử, nên bản ấy phải từng nằm trên đĩa.
    kq = a.history.hoan_tac_changeset(cua_nguoi.id, by="human")
    assert kq.ok, kq.message_vi
    assert (du_an_cx / "Makefile").read_text("utf-8") == ban_tac_tu
    assert "ĐÃ SỬA" in nhac_cho_mo_hinh(a) or "đã sửa" in nhac_cho_mo_hinh(a)


# =========================================================================== CX23
def test_CX23_nguoi_bat_co_tu_A14_va_nam_loi_goi_cai_chi_ra_mot_the(phien, du_an_cx):
    """DEV-371. Hai chỗ người đang làm thay máy: sửa `.env` để bật một cờ, và đóng hàng
    chục thẻ `tool.install` cho cùng một gói."""
    tao, chay, hop = phien
    a = tao([], autonomy="A1")

    cmds = chay({"kind": "set", "data": {"key": "feature.pdf_bang", "value": True},
                 "origin": {"surface": "project", "block": "A14.7", "row": "pdf_bang"}})
    import json

    p = du_an_cx / ".eide" / "settings.json"
    assert json.loads(p.read_text("utf-8"))["features"]["pdf_bang"] is True
    assert a.config.features.bat("pdf_bang") is True
    assert "4,3" in " ".join(c.params.get("text", "") for c in cmds
                             if c.method == "notice"), "phải nói ra CÁI GIÁ của cờ"
    assert [e.data for e in a.ledger.read() if e.kind == "setting"]

    # Bốn lượt, cùng một gói, thẻ cũ vẫn treo → vẫn đúng MỘT thẻ.
    script = [Response(tool_calls=[ToolCall(f"c{i}", "tool.install",
                                            {"cong_cu": "avr-gcc",
                                             "explain": EX(f"cài lần {i}")})])
              for i in range(4)] + [Response(text="xong")]
    a.llm.script = ScriptedGateway(script).script
    a.llm._i = 0
    tat_ca = []
    for _ in range(4):
        tat_ca += chay({"kind": "say", "text": "cài avr-gcc giúp tôi"})
    assert len([x for x in the(tat_ca) if x.get("gate") == "G-TOOL"]) == 1
    assert len(a.pending_gates) == 1
    ds = [e.data for e in a.ledger.read() if e.kind == "gate"]
    assert sum(1 for d in ds if d.get("state") == "trung_the_dang_cho") == 3


# =========================================================================== CX24
def test_CX24_hoan_tac_thanh_cong_va_that_bai_deu_vao_so_kem_tang(phien, du_an_cx):
    """DEV-372. §7 đòi đo "hoàn tác thành công/thất bại THEO TẦNG" từ sổ cái — mà sổ cái
    không có loại sự kiện ấy. Suy từ "sau đó có `history.update` hay không" thì một lần lùi
    thất bại trông y hệt một lần không ai bấm."""
    tao, chay, hop = phien
    a = tao([])
    _ghi_req(a)
    chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
          "data": {"base_version": "v1", "fields": {"text": "≥ 5 MB/s"},
                   "session_id": "es-1"},
          "origin": {"surface": "requirements"}})
    cs = [c for c in a.history.log.all() if c.by_human][-1]

    chay({"kind": "undo", "target": {"type": "changeset", "id": cs.id},
          "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    # Lùi lại cái vừa lùi → THẤT BẠI, và sổ phải nói ra là thất bại.
    chay({"kind": "undo", "target": {"type": "changeset", "id": cs.id},
          "data": {"mode": "revert"}, "origin": {"surface": "history"}})

    u = [e.data for e in a.ledger.read() if e.kind == "undo"]
    assert [x["ok"] for x in u] == [True, False], u
    assert all(x["tang"] == "changeset" for x in u)
    assert "đã được hoàn tác rồi" in u[1]["message_vi"]
    assert a.store.get("FR-01")["canonical"]["text"] == "≥ 1 MB/s"


# =========================================================================== CX25
def test_CX25_hai_cu_bam_tren_hien_vat_loi_thoi(phien, du_an_cx):
    """DEV-373. Đo được trên sổ cái 39 dự án thật: 7 lần hạ nguồn bị đánh STALE rồi KHÔNG
    AI cập nhật. Cơ chế chạy đúng; chỗ thiếu là đường đi của người."""
    from eide import surfaces
    from eide.store import inventory

    tao, chay, hop = phien
    a = tao([])
    _ghi_req(a)
    a.store.apply(artefact_id="drv_eth.c", type="code", op="create",
                  author="agent:run-0", canonical={"path": "drv_eth.c"},
                  explain=EX("mã"), deps={"upstream": ["FR-01"]})

    chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
          "data": {"base_version": "v1", "fields": {"text": "≥ 5 MB/s"}},
          "origin": {"surface": "requirements"}})
    assert [x["id"] for x in a.store.list(stale_only=True)] == ["drv_eth.c"]

    # Lõi KHAI hai cú bấm trên khối A11.4 — giao diện không tự soạn thông điệp.
    inv = inventory.build(a.store, ledger=a.ledger, project_name="du-an-cx")
    k = {b["code"]: b for b in surfaces.history(a.store, inv, a.history)["blocks"]}["A11.4"]
    hd = {h["ma"]: h for h in k["hanh_dong"]}
    assert hd["cap_nhat_tat_ca"]["ton_token"] is True
    assert hd["chap_nhan"]["can_ly_do"] is True

    # Cú bấm 1 — "Cập nhật hạ nguồn": lời nhờ do LÕI soạn, và tác tử dựng lại thật.
    cmds = chay({"kind": "say", "text": "Cập nhật những hiện vật đang lỗi thời.",
                 "data": {"nut": "cap_nhat_ha_nguon"},
                 "origin": {"surface": "history", "block": "A11.4"}}, script=[
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;",
            "new_string": "return init_phy();   // theo FR-01 mới",
            "explain": EX("dựng lại theo ngưỡng mới")})]),
        Response(text="Đã cập nhật drv_eth.c theo FR-01 mới."),
    ])
    nhac = nhac_cho_mo_hinh(a)
    assert "drv_eth.c" in nhac and "lỗi thời vì" in nhac, "đơn công việc phải tới mô hình"
    assert "không có công cụ sinh tự động" in nhac, "lõi nói KHÔNG BIẾT ở chỗ không biết"
    assert "stale.accept" in nhac, "và cấm tắt cờ cho xong"
    assert not a.store.list(stale_only=True), "dựng lại xong thì cờ tự tắt"
    assert "init_phy" in (du_an_cx / "drv_eth.c").read_text("utf-8")
    assert "cập nhật" in loi_tac_tu(cmds).lower()

    # Cú bấm 2 — "Chấp nhận STALE": 0 token, bắt buộc lý do, hoàn tác được.
    chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
          "data": {"base_version": "v2", "fields": {"text": "≥ 9 MB/s"}},
          "origin": {"surface": "requirements"}})
    assert [x["id"] for x in a.store.list(stale_only=True)] == ["drv_eth.c"]
    goi_truoc = a.llm._i

    chay({"kind": "edit", "target": {"type": "code", "id": "drv_eth.c"},
          "data": {"chap_nhan_stale": True},
          "note": "ngưỡng mới chỉ đụng tới lớp trên, driver không liên quan",
          "origin": {"surface": "history", "block": "A11.4", "row": "drv_eth.c"}})

    assert a.llm._i == goi_truoc, "việc kế toán này mã làm xong — 0 token"
    assert not a.store.list(stale_only=True)
    cs = [c for c in a.history.log.all() if c.by_human][-1]
    assert any(f.get("kind") == "stale" for f in cs.forward) and cs.reversible
    kq = a.history.hoan_tac_changeset(cs.id, by="human")
    assert kq.ok and a.store.get("drv_eth.c")["stale"] is True, \
        "hoàn tác thì băng cảnh báo bật lại"


# =========================================================================== bao phủ
def test_moi_goi_cua_EDIT_47_co_dung_mot_ca_CX():
    """Chín gói, chín ca. Một bảng "đã có ca CX" mà thiếu một gói thì nó nói sai về chính
    phạm vi đo — nên đếm bằng mã, không bằng ký ức."""
    import pathlib
    import re

    nguon = pathlib.Path(__file__).read_text("utf-8")
    goi = set(re.findall(r"DEV-3(6[5-9]|7[0-3])", nguon))
    assert len(goi) == 9, sorted(goi)
    ca = re.findall(r"^def (test_CX\d\d)_", nguon, re.M)
    assert len(ca) == 9 and len(set(ca)) == 9, ca
