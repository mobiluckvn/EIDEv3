# -*- coding: utf-8 -*-
"""Trình soạn tệp và khoá mềm HAI CHIỀU — EIDE-EDIT-47 §DEV-367.

`_sua_tep` có từ bước G2: gộp ba chiều, thẻ xung đột, changeset hoàn tác được. Và khối
`code` trên tab Mã nguồn là một `Text(...)` chỉ chọn–copy được — **không đường nào cho
người gõ một chữ vào đó**. Muốn sửa một dòng thì mở VS Code, và lúc ấy EIDE mù.

Soft-lock cũng mới có một chiều: tác tử sửa thì báo cho người (`mark_agent_wrote`). Chiều
kia không có gì — người mở `main.c` ra sửa, tác tử ghi đè ở lượt sau, và người chỉ biết
khi bản của họ biến mất.
"""

from __future__ import annotations

import pytest

from eide import Config, Core
from eide.errors import EideError
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

EX = {"summary": "ghi tệp", "why": "theo yêu cầu", "sources": [], "diff_prev": "đầu",
      "next": "—", "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    def _tao(khoa_nguoi: bool = True, script=None, autonomy: str = "A3"):
        cfg = Config.for_project(du_an, autonomy=autonomy)
        cfg.features.khoa_nguoi = khoa_nguoi
        a = Agent(cfg, llm=ScriptedGateway(script or []), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _the(out):
    return [c.params["card"] for c in out
            if c.method == "console.post" and c.params.get("card")]


def _khoa(out):
    return [(c.method, c.params.get("block"), c.params.get("by"))
            for c in out if c.method in ("surface.lock", "surface.unlock")]


# =============================================================== file.open
def test_mo_tep_tra_du_noi_dung_hash_va_loai(phien, du_an):
    a, core, out, = phien()
    r = core.dispatch("file.open", {"path": "main.c"})
    assert r["ok"] and r["content"] == "int main(void){return 0;}\n"
    assert r["hash"] and r["loai"] == "code" and r["qua_lon"] is False
    assert r["la_eide_md"] is False


def test_mo_tep_NGOAI_HOP_CAT_bi_chan_nhu_cong_cu_cua_tac_tu(phien):
    """Giao diện tự đọc tệp bằng `FileManager` thì hộp cát chỉ còn canh một nửa số đường
    vào — và nửa không canh là nửa người dùng đang ngồi gõ."""
    a, core, out = phien()
    for duong in ("../../etc/passwd", "/etc/passwd", "~/.ssh/id_rsa"):
        with pytest.raises(EideError) as e:
            core.dispatch("file.open", {"path": duong})
        assert "E4002" in str(e.value), "phải là đúng lỗi hộp cát, không phải lỗi khác"


def test_mo_tep_khong_co_va_thieu_duong_dan(phien):
    a, core, out = phien()
    with pytest.raises(EideError):
        core.dispatch("file.open", {"path": "khong-co-tep-nay.c"})
    assert core.dispatch("file.open", {"path": "  "})["ok"] is False


def test_tep_QUA_LON_thi_chi_doc_chu_khong_treo_app(phien, du_an, monkeypatch):
    """Trình soạn giữ cả tệp trong bộ nhớ và gửi cả tệp mỗi lần lưu. Một tệp 50 MB làm app
    đứng hình, và cách hỏng ấy trông giống hệt app chết."""
    monkeypatch.setattr(Agent, "TRAN_MO_TEP", 50)
    (du_an / "to.log").write_text("x" * 500, "utf-8")
    a, core, out = phien()
    r = core.dispatch("file.open", {"path": "to.log"})
    assert r["ok"] and r["qua_lon"] is True and r["content"] == ""
    assert "chỉ mở được ở chế độ đọc" in r["message_vi"]


def test_EIDE_md_mo_duoc_va_TU_KHAI_la_no(phien, du_an):
    a, core, out = phien()
    r = core.dispatch("file.open", {"path": "EIDE.md"})
    assert r["ok"] and r["la_eide_md"] is True


# =============================================================== lưu
def _luu(path, noi_dung, hash_cu, **kw):
    return {"kind": "edit", "target": {"type": "file", "id": path},
            "data": {"base_version": hash_cu, "content": noi_dung,
                     "summary": f"anh sửa {path}", "session_id": "es-1", **kw},
            "origin": {"surface": "code", "block": "editor", "row": path},
            "note": "tôi sửa trong EIDE"}


def test_luu_tu_trinh_soan_sinh_changeset_cua_NGUOI(phien, du_an):
    a, core, out = phien()
    h = core.dispatch("file.open", {"path": "main.c"})["hash"]
    core.console_act(_luu("main.c", "int main(void){return 7;}\n", h))

    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 7;}\n"
    cs = [c for c in a.history.log.all() if c.by_human]
    assert len(cs) == 1 and cs[0].reversible
    assert cs[0].touches[0].type == "code", "loại tệp phải đi vào changeset"


def test_hoan_tac_lan_luu_ay_ve_dung_ban_cu(phien, du_an):
    a, core, out = phien()
    h = core.dispatch("file.open", {"path": "main.c"})["hash"]
    core.console_act(_luu("main.c", "hỏng\n", h))
    cs = [c for c in a.history.log.all() if c.by_human][-1]
    assert a.history.hoan_tac_changeset(cs.id, by="human").ok
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 0;}\n"


def test_luu_EIDE_md_di_qua_eide_md_chu_khong_ghi_thang(phien, du_an):
    """Ghi thẳng thì tệp đúng, nhưng `self.eide_md` trong bộ nhớ tiến trình giữ bản cũ —
    và nó là thứ dựng khối `<eide_md>` cho mọi lượt sau. Lần ghi kế của tác tử sẽ lưu lại
    bản cũ ấy đè lên bản người vừa sửa, im lặng và toàn phần."""
    a, core, out = phien()
    r = core.dispatch("file.open", {"path": "EIDE.md"})
    moi = r["content"] + "\n## Quy ước\n\nGõ tiếng Việt có dấu trong tài liệu.\n"
    core.console_act(_luu("EIDE.md", moi, r["hash"]))

    assert "Gõ tiếng Việt có dấu" in (du_an / "EIDE.md").read_text("utf-8")
    assert "Gõ tiếng Việt có dấu" in a.eide_md.get("Quy ước"), \
        "bản trong bộ nhớ vẫn là bản cũ — lần ghi sau của tác tử sẽ nuốt mất sửa của người"


def test_tac_tu_sua_trong_luc_nguoi_go_thi_GOP_ba_chieu(phien, du_an):
    """Đường này có từ G2; ca kiểm ở đây canh rằng trình soạn mới KHÔNG đi vòng qua nó —
    và rằng bản người MỞ RA tìm lại được (không thì mọi lần như thế rơi xuống thẻ xung
    đột, kể cả khi hai bên sửa hai chỗ chẳng liên quan).

    Tệp phải đủ DÀI. Trên một tệp một dòng thì mọi phép sửa đều kề nhau, và `git
    merge-file` gọi đó là xung đột — đúng về git, nhưng khi ấy ca kiểm đang đo cách dựng
    dữ liệu của chính nó chứ không đo phép gộp.
    """
    a, core, out = phien()
    # Tạo tệp SAU khi lõi đã khởi tạo git: nó chưa nằm trong commit nào, nên `_tim_ban_goc`
    # không tra ngược được bằng `git log`. Bản duy nhất để gộp ba chiều là bản `file.open`
    # cất vào kho blob — và đó đúng là tình huống thật với một tệp tác tử vừa viết ra.
    goc = "\n".join(f"// dòng {i}" for i in range(1, 9)) + "\nint main(void){return 0;}\n"
    (du_an / "dai.c").write_text(goc, "utf-8")
    r = core.dispatch("file.open", {"path": "dai.c"})
    # Tác tử thêm một dòng ở ĐẦU, cách xa chỗ người đang sửa ở cuối.
    (du_an / "dai.c").write_text("// tác tử thêm\n" + goc, "utf-8")
    core.console_act(_luu("dai.c", goc.replace("return 0", "return 7"), r["hash"]))

    sau = (du_an / "dai.c").read_text("utf-8")
    assert "// tác tử thêm" in sau and "return 7" in sau, sau
    assert not [t for t in _the(out) if t.get("tra_loi_thanh") == "xung_dot"], \
        "hai chỗ cách xa nhau mà vẫn bắt người chọn giữ bản nào"


# =============================================================== khoá hai chiều
def test_nguoi_mo_tep_thi_LOI_KHOA_va_bo_khoa_khi_dong(phien):
    a, core, out = phien()
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    assert a.locks_nguoi.get("main.c")
    assert ("surface.lock", "main.c", "human") in _khoa(out)

    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": False},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    assert "main.c" not in a.locks_nguoi
    assert ("surface.unlock", "main.c", None) in _khoa(out)


def test_attend_KHONG_PHAI_TU_TRINH_SOAN_thi_khong_khoa_gi(phien):
    """`attend` là loại thao tác hay nhất trong lượt — bảy cú bấm chuyển tab không được
    đẻ ra bảy cái khoá.

    Ca này phải có một `attend` **mang theo đường dẫn** nhưng không từ trình soạn (bấm
    một dòng tệp trên bảng A7.1 chẳng hạn). Chỉ thử chuyển tab trơn thì bỏ phép kiểm
    `block == "editor"` đi vẫn xanh — vì lúc ấy không có đường dẫn nào để mà khoá.
    """
    a, core, out = phien()
    core.console_act({"kind": "attend", "origin": {"surface": "design"}})
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "A7.1", "row": "main.c"}})
    assert not a.locks_nguoi and not _khoa(out)


def test_khoa_cua_nguoi_HET_HAN(phien):
    """Người mở một tệp rồi đi ăn trưa. Khoá không tự nhả thì mọi lần tác tử ghi tệp ấy
    đều dựng một thẻ không ai bấm — và người ta học cách bấm qua cho nhanh."""
    import time as _t

    a, core, out = phien()
    a.locks_nguoi["main.c"] = _t.time() - (Agent.GIAY_KHOA_NGUOI + 1)
    assert a._nguoi_dang_mo("main.c") is False
    assert "main.c" not in a.locks_nguoi, "hết hạn thì dọn luôn, không để rác"


def _agent_ghi(a, core, out, path="main.c"):
    a.llm.script = ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": path, "old_string": "return 0;", "new_string": "return 1;",
            "explain": EX})]),
        Response(text="xong"),
    ]).script
    a.llm._i = 0
    out.clear()
    core.console_act({"kind": "say", "text": "sửa giúp tôi"})


def test_co_BAT_tac_tu_ghi_tep_nguoi_dang_mo_thi_PHAI_HOI(phien, du_an):
    a, core, out = phien(khoa_nguoi=True)
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    _agent_ghi(a, core, out)

    cong = [t for t in _the(out) if t.get("gate") == "G-FILE"]
    assert cong, "tác tử ghi đè tệp người đang mở mà không hỏi"
    assert "đang mở tệp này" in cong[0]["title"]
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 0;}\n"


def test_co_TAT_thi_tac_tu_ghi_thang_nhu_cu(phien, du_an):
    a, core, out = phien(khoa_nguoi=False)
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    _agent_ghi(a, core, out)
    assert not [t for t in _the(out) if t.get("gate") == "G-FILE"]
    assert "return 1;" in (du_an / "main.c").read_text("utf-8")


def test_tac_tu_DOC_tep_nguoi_dang_mo_thi_KHONG_bi_chan(phien, du_an):
    """Chặn tác tử đọc là chặn đúng việc nó cần làm để khỏi ghi đè."""
    a, core, out = phien(khoa_nguoi=True)
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    a.llm.script = ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "main.c"})]),
        Response(text="đọc xong"),
    ]).script
    a.llm._i = 0
    out.clear()
    core.console_act({"kind": "say", "text": "đọc giúp tôi"})
    assert not [t for t in _the(out) if t.get("gate") == "G-FILE"]


def test_tep_KHAC_thi_khong_bi_hoi(phien, du_an):
    (du_an / "khac.c").write_text("int f(void){return 0;}\n", "utf-8")
    a, core, out = phien(khoa_nguoi=True)
    core.console_act({"kind": "attend", "data": {"path": "main.c", "dang_sua": True},
                      "origin": {"surface": "code", "block": "editor", "row": "main.c"}})
    _agent_ghi(a, core, out, path="khac.c")
    assert not [t for t in _the(out) if t.get("gate") == "G-FILE"]


# ===================================================== hai lớp chắn sau khi người lưu
def test_tac_tu_khong_the_am_tham_de_len_ban_nguoi_vua_luu(phien, du_an):
    """HAI lớp, và ca này đo cả hai — vì lớp thứ nhất che mất lớp thứ hai.

    Bản đầu của ca kiểm này đòi thấy `E4020` ("chưa đọc thì chưa ghi đè"). Nó ĐỎ, và lý
    do hoá ra là tin tốt: một luật policy có sẵn — *"tệp này người dùng vừa sửa"* — dựng
    thẻ **G-FILE** trước khi lời gọi chạy tới `fs.write`. Lớp hai không nổ vì lớp một đã
    chặn.

    Nên đo cả chuỗi: chặn ở cổng → duyệt cổng → vẫn còn E4020 đỡ phía sau.
    """
    a, core, out = phien()
    h = core.dispatch("file.open", {"path": "main.c"})["hash"]
    core.console_act(_luu("main.c", "int main(void){return 7;}\n", h))

    a.llm.script = ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "main.c", "content": "int main(void){return 0;}\n", "explain": EX})]),
        Response(text="xong"),
    ]).script
    a.llm._i = 0
    out.clear()
    core.console_act({"kind": "say", "text": "ghi lại giúp tôi"})

    cong = [t for t in _the(out) if t.get("gate") == "G-FILE"]
    assert cong, "lớp 1 — tác tử ghi đè bản người vừa lưu mà không hỏi"
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 7;}\n"

    # Người lỡ tay bấm Duyệt: lớp 2 vẫn đỡ, vì lượt này tác tử CHƯA ĐỌC bản mới.
    out.clear()
    core.console_act({"kind": "decide",
                      "data": {"gate_id": cong[0]["gate_id"], "approved": True},
                      "origin": {"surface": "console"}})
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 7;}\n", \
        "lớp 2 — ghi đè mù một tệp chưa đọc trong lượt"
    assert any("E4020" in str(m.get("result", "")) for m in a.messages
               if m.get("role") == "tool")
