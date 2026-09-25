# -*- coding: utf-8 -*-
"""Công cụ GHI — bước G2. EIDE-MDD-40 §B3, §E5.1.

    "Mọi công cụ ghi hiện vật đều phải nhận trường `explain` và sinh changeset."
    "Không có thay đổi nào ngoài changeset (tool ghi thẳng bị hook từ chối)."

Câu thứ hai được cài bằng cấu trúc, không bằng kỷ luật: không công cụ nào ở đây gọi
`store.apply` hay ghi tệp trực tiếp. Tất cả đi qua `ctx.history`, và chỉ nơi đó mới
biết cách sinh phép nghịch đảo. Muốn ghi mà không sinh changeset thì phải sửa
`history.py` — đủ rõ ràng để không ai làm nhầm.

Lược đồ `explain` sáu trường được nhắc lại trong từng lược đồ tham số, vì mô hình đọc
lược đồ trước khi đọc hiến pháp.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import EideError, path_not_found
from ..protocol import uicommand as uic
from .registry import Registry, ToolResult

# Lược đồ dùng chung cho `explain` — §E3.1.
EXPLAIN_SCHEMA = {
    "type": "object",
    "description": "Lớp giải thích bắt buộc — sáu trường, viết cho người đọc (N8)",
    "properties": {
        "summary": {"type": "string", "description": "Một câu ≤ 30 từ, không thuật ngữ mới"},
        "why": {"type": "string",
                "description": "Ràng buộc/REQ/Fact nào dẫn tới; nếu là lựa chọn thì vì sao loại cái khác"},
        "sources": {"type": "array", "description": "Mỗi con số trong summary/why phải có nguồn ở đây",
                    "items": {"type": "object", "properties": {
                        "kind": {"type": "string", "enum": ["fact", "doc", "human_act", "tool", "changeset"]},
                        "ref": {"type": "string"},
                        "tier": {"type": "string", "enum": ["VANG", "BAC", "NGUOI", "DONG"]}},
                        "required": ["kind", "ref"]}},
        "diff_prev": {"type": "string",
                      "description": "Khác bản trước ở đâu, bằng lời; 'bản đầu tiên' nếu chưa có"},
        "next": {"type": "string", "description": "Đúng một hành động tiếp theo"},
        "confidence": {"type": "string", "enum": ["VANG", "BAC", "NGUOI", "DONG", "hỗn hợp"],
                       "description": "Tầng thấp nhất trong sources"},
    },
    "required": ["summary", "why", "sources", "diff_prev", "next", "confidence"],
}


def _sandbox(ctx: Any, raw: str) -> Path:
    from .builtin import _resolve
    return _resolve(ctx, raw)


def _rel(ctx: Any, p: Path) -> str:
    try:
        return str(p.relative_to(Path(ctx.config.paths.project_root).resolve()))
    except ValueError:
        return str(p)


def register(r: Registry) -> Registry:
    """Thêm bộ công cụ ghi vào sổ đăng ký đã có."""

    # ====================================================================== tệp
    @r.tool("fs.write", "Tệp & lệnh",
            "Ghi một tệp trong dự án (tạo mới hoặc thay toàn bộ nội dung). Sinh changeset "
            "hoàn tác được. Đọc tệp trước bằng fs.read nếu nó đã tồn tại.",
            {"type": "object",
             "properties": {"path": {"type": "string", "description": "Đường dẫn tương đối"},
                            "content": {"type": "string"},
                            "explain": EXPLAIN_SCHEMA},
             "required": ["path", "content", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            produces=["code"], keywords=["ghi", "tạo tệp", "viết tệp"])
    def fs_write(ctx: Any, path: str, content: str, explain: dict[str, Any]):
        p = _sandbox(ctx, path)
        rel = _rel(ctx, p)
        cu = p.read_text("utf-8", errors="replace") if p.exists() else None

        # §E4 bước 6: "KHÔNG ghi đè sửa của người nếu không được đồng ý". Lớp cấp quyền
        # đã dựng thẻ G-FILE cho chuyện này; tới được đây nghĩa là đã được duyệt.
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, "utf-8")

        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[rel],
            summary=explain.get("summary", "ghi tệp"), explain=explain,
            noi_dung_truoc={rel: cu} if cu is not None else None,
            run_id=ctx.run_id)
        ctx.mark_agent_wrote(rel)
        return {"path": rel, "bytes": len(content.encode("utf-8")),
                "changeset": cs.id, "tao_moi": cu is None,
                "stale": cs.stale_marked,
                "note_vi": _note_stale(cs)}

    @r.tool("fs.edit", "Tệp & lệnh",
            "Thay một đoạn văn bản trong tệp bằng đoạn khác. Đoạn cũ phải khớp CHÍNH XÁC "
            "và xuất hiện đúng một lần — nếu không, đọc lại tệp bằng fs.read.",
            {"type": "object",
             "properties": {"path": {"type": "string"},
                            "old_string": {"type": "string"},
                            "new_string": {"type": "string"},
                            "explain": EXPLAIN_SCHEMA},
             "required": ["path", "old_string", "new_string", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            keywords=["sửa", "thay", "edit"])
    def fs_edit(ctx: Any, path: str, old_string: str, new_string: str,
                explain: dict[str, Any]):
        p = _sandbox(ctx, path)
        rel = _rel(ctx, p)
        if not p.exists():
            raise path_not_found(rel)
        cu = p.read_text("utf-8")
        n = cu.count(old_string)
        if n == 0:
            return ToolResult(False, error=EideError(
                "E1005", f"Không tìm thấy đoạn cần thay trong {rel}.",
                hint_for_agent="Đọc lại tệp bằng fs.read rồi sao chép CHÍNH XÁC đoạn cần "
                               "thay, kể cả khoảng trắng đầu dòng.",
                alternatives=["fs.read"], blame="agent"))
        if n > 1:
            return ToolResult(False, error=EideError(
                "E1006", f"Đoạn cần thay xuất hiện {n} lần trong {rel} — không rõ thay cái nào.",
                hint_for_agent="Mở rộng đoạn cũ cho tới khi nó chỉ khớp một chỗ.",
                alternatives=["fs.read"], blame="agent"))

        p.write_text(cu.replace(old_string, new_string, 1), "utf-8")
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[rel],
            summary=explain.get("summary", "sửa tệp"), explain=explain,
            noi_dung_truoc={rel: cu}, run_id=ctx.run_id)
        ctx.mark_agent_wrote(rel)
        return {"path": rel, "changeset": cs.id, "stale": cs.stale_marked,
                "note_vi": _note_stale(cs)}

    # ====================================================================== yêu cầu
    @r.tool("store.req_create", "Store",
            "Ghi một yêu cầu (REQ) vào kho. BẮT BUỘC trích đúng lời người dùng vào "
            "source_quote — không trích được câu nào thì đó không phải yêu cầu của họ "
            "(N7: chỉ thị cho bạn và rủi ro bạn tự thấy đều KHÔNG thành yêu cầu).",
            {"type": "object",
             "properties": {
                 "id": {"type": "string", "description": "FR-01, NFR-02, UR-03…"},
                 "loai": {"type": "string", "enum": ["FR", "NFR", "UR"]},
                 "text": {"type": "string", "description": "Yêu cầu, một câu"},
                 "criteria": {"type": "string", "description": "Tiêu chí đo được"},
                 "source_quote": {"type": "string",
                                  "description": "Trích NGUYÊN VĂN câu của người dùng"},
                 "risk": {"type": "array", "items": {"type": "string"},
                          "description": "Rủi ro đi kèm — KHÔNG phải yêu cầu"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["id", "loai", "text", "source_quote", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            produces=["req"], keywords=["yêu cầu", "req", "đặc tả", "fr", "nfr"])
    def store_req_create(ctx: Any, id: str, loai: str, text: str, source_quote: str,
                         explain: dict[str, Any], criteria: str = "",
                         risk: list[str] | None = None):
        cu = ctx.store.get(id)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=id, type="req",
            op="update" if cu else "create",
            canonical={"loai": loai, "text": text, "criteria": criteria,
                       "source_quote": source_quote, "risk": risk or []},
            explain=explain, run_id=ctx.run_id)
        return {"id": id, "version": cs.touches[0].to_version, "changeset": cs.id,
                "stale": cs.stale_marked, "note_vi": _note_stale(cs)}

    @r.tool("store.req_update", "Store",
            "Sửa một yêu cầu đã có. Hạ nguồn của nó sẽ được đánh dấu cần cập nhật.",
            {"type": "object",
             "properties": {"id": {"type": "string"},
                            "text": {"type": "string"},
                            "criteria": {"type": "string"},
                            "explain": EXPLAIN_SCHEMA},
             "required": ["id", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, core=False,
            keywords=["sửa yêu cầu", "cập nhật req"])
    def store_req_update(ctx: Any, id: str, explain: dict[str, Any],
                         text: str | None = None, criteria: str | None = None):
        cu = ctx.store.get(id)
        if cu is None:
            return ToolResult(False, error=EideError(
                "E5005", f"Không có yêu cầu nào mã {id} trong kho.",
                hint_for_agent="Gọi store.list type=req để xem kho có gì.",
                alternatives=["store.list"], blame="agent"))
        can = dict(cu["canonical"])
        if text is not None:
            can["text"] = text
        if criteria is not None:
            can["criteria"] = criteria
        cs = ctx.history.ghi_kho(author=f"agent:{ctx.run_id}", artefact_id=id, type="req",
                                 op="update", canonical=can, explain=explain,
                                 run_id=ctx.run_id)
        return {"id": id, "version": cs.touches[0].to_version, "changeset": cs.id,
                "stale": cs.stale_marked, "note_vi": _note_stale(cs)}

    # ====================================================================== bộ nhớ
    @r.tool("memory.note", "Store",
            "Ghi vào EIDE.md — bộ nhớ dài hạn của dự án. Dùng cho quyết định, giả định, "
            "quy ước, hoặc điều người dùng bảo 'đừng làm nữa'.",
            {"type": "object",
             "properties": {
                 "section": {"type": "string",
                             "enum": ["Mục tiêu", "Chip & phần cứng", "Quyết định",
                                      "Giả định", "Quy ước", "Đừng"]},
                 "line": {"type": "string", "description": "Một dòng, viết cho người đọc"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["section", "line", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            keywords=["ghi nhớ", "quyết định", "giả định", "eide.md", "đừng"])
    def memory_note(ctx: Any, section: str, line: str, explain: dict[str, Any]):
        cu = ctx.eide_md.path.read_text("utf-8") if ctx.eide_md.path.exists() else ""
        ctx.eide_md.append_line(section, f"- {line}")
        ctx.eide_md.save()
        # EIDE.md là bộ nhớ dự án, không phải mã — đặt đúng loại để nó không lọt vào
        # đồ thị phụ thuộc của mã và không bị đếm là "tệp mã" trong kiểm kê.
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=["EIDE.md"], loai="memory",
            summary=explain.get("summary", f"ghi vào §{section}"), explain=explain,
            noi_dung_truoc={"EIDE.md": cu}, run_id=ctx.run_id)
        return {"section": section, "changeset": cs.id}

    # ====================================================================== lịch sử
    @r.tool("history.diff", "Lịch sử",
            "Xem một changeset đã đổi những gì.",
            {"type": "object", "properties": {"changeset": {"type": "string"}},
             "required": ["changeset"]},
            risk="R1", keywords=["diff", "thay đổi", "changeset"])
    def history_diff(ctx: Any, changeset: str):
        return ctx.history.diff(changeset)

    @r.tool("history.undo", "Lịch sử",
            "Hoàn tác một changeset hoặc cả một lượt chạy. Không xoá lịch sử — tạo một "
            "thay đổi mới lùi lại. Thao tác không đảo ngược được (nạp chip, cài công cụ) "
            "sẽ được giữ nguyên kèm cảnh báo.",
            {"type": "object",
             "properties": {
                 "scope": {"type": "string", "enum": ["changeset", "run"]},
                 "target": {"type": "string", "description": "cs-0109 hoặc run-43"}},
             "required": ["scope", "target"]},
            risk="R2", gate="G-HIST", keywords=["hoàn tác", "undo", "quay lại", "lùi"])
    def history_undo(ctx: Any, scope: str, target: str):
        kq = (ctx.history.hoan_tac_changeset(target, by=f"agent:{ctx.run_id}")
              if scope == "changeset"
              else ctx.history.hoan_tac_luot(target, by=f"agent:{ctx.run_id}"))
        if kq.canh_bao:
            for c in kq.canh_bao:
                ctx.emit(uic.notice(c, level="warn"))
        return kq.to_dict()

    @r.tool("ui.explain", "Người & UI",
            "Giải thích một hiện vật cho người dùng khi họ bấm 'Giải thích thêm'. "
            "Trả lời trong Console và tô sáng chỗ liên quan. KHÔNG tạo changeset — đây "
            "là giải thích, không phải thay đổi.",
            {"type": "object",
             "properties": {
                 "artefact": {"type": "string", "description": "Mã hiện vật đang được hỏi"},
                 "giai_thich": {"type": "string",
                                "description": "Viết cho người đọc, không thuật ngữ mới"},
                 "to_sang": {"type": "array", "items": {"type": "string"},
                             "description": "Mã dòng/net/tệp cần tô sáng, nếu có"},
                 "be_mat": {"type": "string",
                            "description": "Bề mặt chứa chỗ cần tô sáng"}},
             "required": ["artefact", "giai_thich"]},
            risk="R1", keywords=["giải thích", "vì sao", "tại sao", "explain"])
    def ui_explain(ctx: Any, artefact: str, giai_thich: str,
                   to_sang: list[str] | None = None, be_mat: str = ""):
        a = ctx.store.get(artefact)
        ctx.emit(uic.explain_show(artefact, {
            **(a["explain"] if a else {}),
            "giai_thich_them": giai_thich,
        }))
        if to_sang and be_mat:
            ctx.emit(uic.surface_highlight(be_mat, block=artefact, refs=to_sang,
                                           why=giai_thich[:120]))
        return {"artefact": artefact, "da_to_sang": to_sang or [],
                "note_vi": "Đã giải thích trong Console. Không có thay đổi nào được ghi."}

    @r.tool("stale.accept", "Lịch sử",
            "Đánh dấu 'chấp nhận STALE' cho một hiện vật: nó lỗi thời nhưng người dùng "
            "quyết định giữ nguyên. Phải nêu lý do.",
            {"type": "object",
             "properties": {"id": {"type": "string"}, "why": {"type": "string"}},
             "required": ["id", "why"]},
            risk="R2", core=False, keywords=["chấp nhận", "stale", "bỏ qua cảnh báo"])
    def stale_accept(ctx: Any, id: str, why: str):
        a = ctx.store.get(id)
        if a is None:
            return ToolResult(False, error=EideError(
                "E5005", f"Không có hiện vật {id}.", blame="agent"))
        ctx.store.accept_stale(id, why)
        return {"id": id, "note_vi": f"Đã tắt băng cảnh báo cho {id}. Lý do được ghi lại."}

    return r


def _note_stale(cs: Any) -> str:
    """§E5.4 — báo hạ nguồn lỗi thời, và nói rõ tác tử KHÔNG tự chạy lại."""
    if not cs.stale_marked:
        return ""
    return ("Thay đổi này làm các hiện vật sau lỗi thời: "
            + ", ".join(cs.stale_marked)
            + ". Tôi KHÔNG tự chạy lại chúng — hãy nói cho người dùng biết và đề nghị "
              "kế hoạch cập nhật.")
