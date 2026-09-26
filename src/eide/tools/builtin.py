# -*- coding: utf-8 -*-
"""Bộ công cụ G1: 10 công cụ đọc + ask_user + tool.search + ui.notice.

EIDE-MDD-40 Phần G bước G1: "tool registry + 10 tool đọc + ask_user".

Không có công cụ nào GHI hiện vật ở bước này — vì hiện vật hai dạng và changeset là
G2/G3. Không đăng ký một công cụ ghi rỗng chỉ để cho đủ bộ: một công cụ hứa làm việc
mà không làm được thì mô hình sẽ gọi nó, và ta lại có thêm một ca "đạt nhờ tai nạn".
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..errors import (
    EideError, budget_exhausted, corrupt_file, outside_sandbox, path_not_found,
)
from ..protocol import uicommand as uic
from .registry import Registry, ToolResult

MAX_READ_BYTES = 200_000       # đọc quá mức này thì phải nói ra, không cắt lặng lẽ
MAX_GLOB_HITS = 300
MAX_GREP_HITS = 200


# --------------------------------------------------------------------------- sandbox
def _resolve(ctx: Any, raw: str) -> Path:
    """Mọi đường dẫn đi qua đây. §B3 "Sandbox"; N5; TC070.

    Chặn vì THIẾT KẾ chứ không vì tai nạn: kiểm sau khi resolve() nên `../../..` và
    symlink trỏ ra ngoài đều không lách được.
    """
    root = Path(ctx.config.paths.project_root).resolve()
    p = Path(os.path.expanduser(raw))
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if p != root and root not in p.parents:
        raise outside_sandbox(str(p), [str(root)])
    return p


def _rel(ctx: Any, p: Path) -> str:
    root = Path(ctx.config.paths.project_root).resolve()
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


# --------------------------------------------------------------------------- lược đồ
_S_PATH = {"type": "string", "description": "Đường dẫn tương đối tới gốc dự án"}


def build_registry(features: Any = None) -> Registry:
    """Dựng bộ công cụ. `features` quyết định nhóm nào được ĐĂNG KÝ (SCH-44 §2.1).

    Không truyền gì ⇒ đọc cờ từ `~/.eide/settings.json` + biến môi trường. Cờ tắt thì
    công cụ của tính năng đó không tồn tại với mô hình, không phải chỉ bị giấu.
    """
    from ..config import Features
    r = Registry(features if features is not None else Features.load())

    # ====================================================================== fs
    @r.tool("fs.read", "Tệp & lệnh",
            "Đọc nội dung một tệp văn bản trong dự án. Dùng khi cần biết tệp có gì — "
            "không bao giờ đoán nội dung tệp.",
            {"type": "object",
             "properties": {"path": _S_PATH,
                            "offset": {"type": "integer", "description": "Dòng bắt đầu (1-based)"},
                            "limit": {"type": "integer", "description": "Số dòng tối đa"}},
             "required": ["path"]},
            risk="R1", keywords=["đọc", "tệp", "file", "xem", "nội dung"],
            returns_vi="Nội dung tệp kèm số dòng")
    def fs_read(ctx: Any, path: str, offset: int | None = None, limit: int | None = None):
        p = _resolve(ctx, path)
        if not p.exists():
            raise path_not_found(_rel(ctx, p))
        if p.is_dir():
            raise EideError("E1004", f"{_rel(ctx, p)} là thư mục, không phải tệp.",
                            hint_for_agent="Dùng fs.glob để liệt kê thư mục.",
                            alternatives=["fs.glob"], blame="agent")
        size = p.stat().st_size
        try:
            text = p.read_text("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise corrupt_file(_rel(ctx, p), "không phải tệp văn bản UTF-8 (có thể là tệp nhị phân)")
        lines = text.splitlines()
        start = max(0, (offset or 1) - 1)
        end = min(len(lines), start + limit) if limit else len(lines)
        body = "\n".join(f"{i + 1:5d}\t{l}" for i, l in enumerate(lines[start:end], start))
        truncated = len(body) > MAX_READ_BYTES
        if truncated:
            body = body[:MAX_READ_BYTES]
        return {"path": _rel(ctx, p), "bytes": size, "lines_total": len(lines),
                "lines_shown": [start + 1, end], "truncated": truncated,
                "content": body,
                # PR5 "không giấu thất bại": nói rõ đã đọc tới đâu, không im lặng cắt.
                "note_vi": (f"Chỉ hiện {end - start}/{len(lines)} dòng."
                            if (end - start) < len(lines) else "")}

    @r.tool("fs.glob", "Tệp & lệnh",
            "Tìm tệp theo mẫu tên (ví dụ '**/*.c', 'du-lieu/**'). Dùng khi chưa chắc "
            "đường dẫn — TUYỆT ĐỐI không tự bịa một đường dẫn rồi gọi tool khác lên nó.",
            {"type": "object",
             "properties": {"pattern": {"type": "string", "description": "Mẫu glob"},
                            "limit": {"type": "integer"}},
             "required": ["pattern"]},
            risk="R1", keywords=["tìm", "tệp", "glob", "liệt kê", "thư mục"])
    def fs_glob(ctx: Any, pattern: str, limit: int | None = None):
        root = Path(ctx.config.paths.project_root).resolve()
        hits = []
        for p in sorted(root.glob(pattern)):       # sorted: cùng dự án → cùng kết quả (§F3)
            if p.is_file():
                hits.append({"path": _rel(ctx, p), "bytes": p.stat().st_size})
            if len(hits) >= (limit or MAX_GLOB_HITS):
                break
        return {"pattern": pattern, "count": len(hits), "files": hits,
                "note_vi": "" if hits else
                f"Không có tệp nào khớp '{pattern}'. Đừng đoán một đường dẫn khác — "
                f"thử mẫu rộng hơn hoặc hỏi người dùng."}

    @r.tool("fs.grep", "Tệp & lệnh",
            "Tìm chuỗi/biểu thức chính quy trong các tệp của dự án.",
            {"type": "object",
             "properties": {"pattern": {"type": "string"},
                            "glob": {"type": "string", "description": "Giới hạn tệp, ví dụ '**/*.c'"},
                            "limit": {"type": "integer"}},
             "required": ["pattern"]},
            risk="R1", keywords=["tìm", "grep", "chuỗi", "search"])
    def fs_grep(ctx: Any, pattern: str, glob: str | None = None, limit: int | None = None):
        import re as _re
        try:
            rx = _re.compile(pattern)
        except _re.error as e:
            raise EideError("E5001", f"Biểu thức không hợp lệ: {e}",
                            hint_for_agent="Sửa lại biểu thức chính quy.", blame="agent")
        root = Path(ctx.config.paths.project_root).resolve()
        hits: list[dict[str, Any]] = []
        for p in sorted(root.glob(glob or "**/*")):
            if not p.is_file() or ".eide" in p.parts or ".git" in p.parts:
                continue
            try:
                for i, line in enumerate(p.read_text("utf-8", errors="ignore").splitlines(), 1):
                    if rx.search(line):
                        hits.append({"path": _rel(ctx, p), "line": i, "text": line.strip()[:200]})
                        if len(hits) >= (limit or MAX_GREP_HITS):
                            return {"pattern": pattern, "count": len(hits), "hits": hits,
                                    "truncated": True}
            except OSError:
                continue
        return {"pattern": pattern, "count": len(hits), "hits": hits, "truncated": False,
                "note_vi": "" if hits else f"Không dòng nào khớp '{pattern}'."}

    @r.tool("fs.stat", "Tệp & lệnh",
            "Xem một đường dẫn có tồn tại không và là gì (tệp/thư mục, kích thước, đuôi). "
            "Gọi cái này trước khi dùng một đường dẫn bạn không chắc.",
            {"type": "object", "properties": {"path": _S_PATH}, "required": ["path"]},
            risk="R1", keywords=["tồn tại", "kiểm tra", "stat"])
    def fs_stat(ctx: Any, path: str):
        try:
            p = _resolve(ctx, path)
        except EideError as e:
            return ToolResult(False, error=e)
        if not p.exists():
            return {"path": path, "exists": False,
                    "note_vi": "Đường dẫn này KHÔNG tồn tại. Đừng dùng nó cho bất kỳ công cụ "
                               "nào khác — tìm bằng fs.glob hoặc hỏi người dùng."}
        st = p.stat()
        return {"path": _rel(ctx, p), "exists": True,
                "kind": "dir" if p.is_dir() else "file",
                "bytes": st.st_size, "suffix": p.suffix.lower()}

    # ====================================================================== kho
    @r.tool("store.list", "Store",
            "Liệt kê hiện vật trong kho theo loại (req, option, adr, passport, netlist, "
            "pinout, bom, code, build, criteria, sim_result…).",
            {"type": "object",
             "properties": {"type": {"type": "string"},
                            "stale_only": {"type": "boolean"},
                            "limit": {"type": "integer"}}},
            risk="R1", keywords=["yêu cầu", "req", "hiện vật", "danh sách", "kho"])
    def store_list(ctx: Any, type: str | None = None, stale_only: bool = False,
                   limit: int | None = None):
        rows = ctx.store.list(type, stale_only=stale_only, limit=limit or 100)
        return {"count": len(rows),
                "items": [{"id": a["id"], "type": a["type"], "version": a["version"],
                           "author": a["author"], "stale": a["stale"],
                           "summary": (a["explain"] or {}).get("summary", "")} for a in rows],
                "note_vi": "" if rows else
                f"Kho chưa có hiện vật loại {type or '(bất kỳ)'} nào. Đừng nhắc tới cái "
                f"không có trong danh sách này."}

    @r.tool("store.get", "Store",
            "Đọc đầy đủ một hiện vật: dạng máy (canonical), lớp giải thích, phụ thuộc.",
            {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
            risk="R1", keywords=["đọc", "hiện vật", "chi tiết"])
    def store_get(ctx: Any, id: str):
        a = ctx.store.get(id)
        if a is None:
            return ToolResult(False, error=EideError(
                "E5005", f"Không có hiện vật nào mang mã {id} trong kho.",
                hint_for_agent="Gọi store.list để xem kho thật sự có gì. Đừng nhắc tới mã này nữa.",
                alternatives=["store.list"], blame="agent"))
        return a

    @r.tool("fact.query", "Tri thức",
            "Tra Fact theo thực thể/khoá/tầng. Mọi con số dùng để so sánh, quyết định hay "
            "sinh mã phải đến từ đây (N1). Không có Fact thì KHÔNG có số.",
            {"type": "object",
             "properties": {"subject": {"type": "string",
                                        "description": "chip:ATmega328P | net:SDA | pin:U1.28"},
                            "key": {"type": "string", "description": "vdd.max, flash.size…"},
                            "tier": {"type": "string", "enum": ["VANG", "BAC", "NGUOI", "DONG"]}}},
            risk="R1", keywords=["fact", "thông số", "datasheet", "giá trị", "tra"])
    def fact_query(ctx: Any, subject: str | None = None, key: str | None = None,
                   tier: str | None = None):
        rows = ctx.store.query_facts(subject=subject, key=key, tier=tier)
        return {"count": len(rows), "facts": rows,
                "note_vi": "" if rows else
                "Không có Fact nào khớp. Nghĩa là dự án CHƯA CÓ con số nào về thứ này truy "
                "vết được tới tài liệu. Đừng dùng số nhớ được — hãy đề nghị nạp datasheet, "
                "hoặc hỏi người dùng (số họ cho sẽ thành Fact tầng NGƯỜI)."}

    @r.tool("inventory.get", "Store",
            "Đọc lại bảng kiểm kê dự án (dạng có cấu trúc). Bảng này do mã dựng, là sự thật "
            "về dự án đang có gì.",
            {"type": "object", "properties": {}},
            risk="R1", keywords=["kiểm kê", "dự án", "trạng thái", "inventory"])
    def inventory_get(ctx: Any):
        return ctx.build_inventory().to_dict()

    @r.tool("memory.read", "Store",
            "Đọc EIDE.md — bộ nhớ dài hạn của dự án (mục tiêu, chip, quyết định, giả định, "
            "quy ước, §Đừng, §Người vừa sửa).",
            {"type": "object",
             "properties": {"section": {"type": "string", "description": "Tên mục, bỏ trống = tất cả"}}},
            risk="R1", keywords=["eide.md", "bộ nhớ", "quy ước", "quyết định", "đừng"])
    def memory_read(ctx: Any, section: str | None = None):
        md = ctx.eide_md
        if section:
            body = md.get(section)
            return {"section": section, "body": body,
                    "note_vi": "" if body else f"EIDE.md không có mục '{section}'."}
        return md.to_dict()

    @r.tool("history.list", "Lịch sử",
            "Liệt kê các lượt đã chạy và sự kiện trong sổ cái. Dùng để trả lời 'lần trước "
            "mình làm gì', thay vì nhớ.",
            {"type": "object",
             "properties": {"contains": {"type": "string", "description": "Lọc theo từ khoá"},
                            "limit": {"type": "integer"}}},
            risk="R1", keywords=["lịch sử", "lượt", "trước", "đã làm", "run"])
    def history_list(ctx: Any, contains: str | None = None, limit: int | None = None):
        runs = ctx.ledger.find_run(contains or "")
        runs = runs[-(limit or 20):]
        return {"count": len(runs), "runs": runs,
                "note_vi": "" if runs else "Sổ cái chưa có lượt nào khớp."}

    @r.tool("blob.read", "Tệp & lệnh",
            "Đọc lại phần kết quả đã bị cắt khỏi ngữ cảnh. Khi một kết quả công cụ có "
            "trường `_cat`, dùng `ref` trong đó để lấy nguyên văn theo khoảng ký tự.",
            {"type": "object",
             "properties": {
                 "ref": {"type": "string", "description": "blob:sha256:… lấy từ trường _cat"},
                 "tu": {"type": "integer", "description": "Ký tự bắt đầu, mặc định 0"},
                 "den": {"type": "integer", "description": "Ký tự kết thúc"}},
             "required": ["ref"]},
            risk="R1", core=False,
            keywords=["blob", "đọc lại", "phần còn lại", "đã cắt", "nguyên văn"])
    def blob_read(ctx: Any, ref: str, tu: int = 0, den: int | None = None):
        """MEM-42 §5.2. Không có công cụ này thì "cắt" trở thành "mất"."""
        bam = ref.split(":")[-1].strip()
        if ctx.history is None or not bam:
            raise EideError(
                "E5003", "Không có kho blob trong phiên này.",
                hint_for_agent="Gọi lại công cụ gốc với phạm vi hẹp hơn.",
                alternatives=["fs.read với offset/limit"], blame="system")
        data = ctx.history.blobs.get(bam)
        if data is None:
            raise EideError(
                "E5003", f"Không còn nội dung nào ở {ref}.",
                hint_for_agent=("Tham chiếu này sai hoặc đã bị dọn. Gọi lại công cụ gốc "
                                "thay vì đoán nội dung."),
                alternatives=["gọi lại công cụ gốc"], blame="agent")
        chu = data.decode("utf-8", "replace")
        het = len(chu) if den is None else min(len(chu), max(tu, den))
        phan = chu[tu:het]
        # Trần cứng: blob.read không được trở thành cửa sau để nhét cả tệp vào ngữ cảnh.
        if len(phan) > 60_000:
            phan = phan[:60_000]
            het = tu + 60_000
        return {"ref": ref, "tong_ky_tu": len(chu), "tu": tu, "den": het,
                "noi_dung": phan,
                "note_vi": ("" if het >= len(chu) else
                            f"Còn {len(chu) - het} ký tự. Gọi tiếp với tu={het}.")}

    @r.tool("ledger.query", "Lịch sử",
            "TRA sổ cái để trả lời câu hỏi về quá khứ: 'ban đầu anh nói gì về…', 'vì "
            "sao chọn MTP', 'lần trước lỗi gì'. Dùng cái này TRƯỚC khi trả lời bất kỳ "
            "câu hỏi nào về những gì đã xảy ra — đừng kể lại từ trí nhớ.",
            {"type": "object",
             "properties": {
                 "chua": {"type": "string",
                          "description": "Từ khoá tìm trong nội dung sự kiện"},
                 "loai": {"type": "string",
                          "description": "human_act | gate | changeset | tool_use | "
                                         "incident | tombstone | llm_call"},
                 "run_id": {"type": "string"},
                 "limit": {"type": "integer", "description": "mặc định 30"}}},
            risk="R1",
            keywords=["tra", "lịch sử", "quá khứ", "ban đầu", "vì sao", "lần trước",
                      "đã nói", "sổ cái"])
    def ledger_query(ctx: Any, chua: str = "", loai: str = "", run_id: str = "",
                     limit: int | None = None):
        """MEM-42 §10 — truy hồi có chủ đích, thay cho việc mô hình đoán.

        Tra được thì phải TRA. Một câu trả lời về quá khứ dựng từ transcript đã nén là
        một câu trả lời nghe đúng mà không ai kiểm được — đúng chỗ nguy hiểm mà TC074
        chỉ ra.
        """
        import json as _json

        n = int(limit or 30)
        low = (chua or "").lower()
        ra: list[dict[str, Any]] = []
        for ev in ctx.ledger.read():
            if loai and ev.kind != loai:
                continue
            if run_id and ev.data.get("run_id") != run_id:
                continue
            chu = _json.dumps(ev.data, ensure_ascii=False, default=str)
            if low and low not in chu.lower():
                continue
            ra.append({"seq": ev.seq, "ts": ev.ts, "loai": ev.kind,
                       "run_id": ev.data.get("run_id", ""),
                       "tom_tat": chu[:220]})
        tong = len(ra)
        return {"tong": tong, "su_kien": ra[-n:],
                "note_vi": ("" if tong else
                            "Sổ cái không có sự kiện nào khớp. Nói THẲNG là không tìm "
                            "thấy — đừng dựng lại câu chuyện từ trí nhớ.")}

    @r.tool("ledger.verify", "Lịch sử",
            "Kiểm tính toàn vẹn của sổ cái (chuỗi hash). Gọi khi nghi ngờ lịch sử bị sửa.",
            {"type": "object", "properties": {}},
            risk="R1", core=False, keywords=["toàn vẹn", "hash", "sổ cái", "kiểm"])
    def ledger_verify(ctx: Any):
        ok, msg = ctx.ledger.verify()
        return {"ok": ok, "message_vi": msg}

    # ====================================================================== người & UI
    @r.tool("ask_user", "Người & UI",
            "Hỏi người dùng MỘT CỤM câu hỏi (nhiều mục trong một thẻ). Dùng khi thiếu thông "
            "tin mà không công cụ nào lấy được. KHÔNG dùng cho cổng an toàn — cổng là thẻ "
            "riêng do lớp cấp quyền phát. Tối đa 2 lần mỗi lượt (N4).",
            {"type": "object",
             "properties": {
                 "intro": {"type": "string",
                           "description": "Một câu nói bạn đang hiểu việc gì và vì sao cần hỏi"},
                 "questions": {"type": "array", "description": "Cả cụm, hỏi một lần",
                               "items": {"type": "object", "properties": {
                                   "key": {"type": "string"},
                                   "question": {"type": "string"},
                                   "why": {"type": "string",
                                           "description": "Vì sao cần biết — người có quyền biết"},
                                   "choices": {"type": "array", "items": {"type": "string"}},
                                   "prefill": {"type": "string",
                                               "description": "Điều bạn ĐÃ biết từ câu họ vừa nói, "
                                                              "điền sẵn để họ khỏi gõ lại"},
                                   "required": {"type": "boolean"}},
                                   "required": ["key", "question"]}},
                 "assumption_if_skipped": {
                     "type": "string",
                     "description": "Giả định bạn sẽ dùng nếu họ bỏ qua — phải nói ra (N4)"}},
             "required": ["questions"]},
            risk="R1", keywords=["hỏi", "làm rõ", "thiếu thông tin"])
    def ask_user(ctx: Any, questions: list[dict[str, Any]], intro: str = "",
                 assumption_if_skipped: str = ""):
        if ctx.ask_rounds >= ctx.config.budget.max_ask_rounds:
            # N4: hết vòng thì đi tiếp VỚI GIẢ ĐỊNH ĐƯỢC NÓI RA, không hỏi mãi.
            return ToolResult(False, error=budget_exhausted(
                "số lần hỏi trong một lượt", ctx.config.budget.max_ask_rounds))
        if not questions:
            return ToolResult(False, error=EideError(
                "E5001", "ask_user gọi mà không có câu hỏi nào.",
                hint_for_agent="Đưa ít nhất một câu hỏi, hoặc đừng gọi.", blame="agent"))

        ctx.ask_rounds += 1
        card_id = ctx.ids.next("card")
        card = {"type": "clarify", "card_id": card_id, "intro": intro,
                "questions": questions, "assumption_if_skipped": assumption_if_skipped}
        ctx.emit(uic.console_post("[Tác tử] " + _render_ask(intro, questions,
                                                           assumption_if_skipped),
                                  role="agent", card=card))
        ctx.said_anything = True
        ctx.pending_cards.append(card)
        ctx.awaiting_human = True      # vòng lặp dừng ở đây và trả lượt cho người
        return {"asked": True, "card_id": card_id, "count": len(questions),
                "note_vi": "Đã hỏi người dùng. KẾT THÚC lượt ở đây và chờ họ trả lời — "
                           "đừng đoán câu trả lời và đừng gọi thêm công cụ nào."}

    @r.tool("ui.notice", "Người & UI",
            "Gửi một thông báo ngắn cho người dùng (thông tin/cảnh báo), không tạo thay đổi nào.",
            {"type": "object",
             "properties": {"text": {"type": "string"},
                            "level": {"type": "string", "enum": ["info", "warn", "error"]}},
             "required": ["text"]},
            risk="R1", keywords=["thông báo", "cảnh báo"])
    def ui_notice(ctx: Any, text: str, level: str = "info"):
        ctx.emit(uic.notice(text, level=level))
        return {"sent": True}

    @r.tool("history.undo_30s", "Lịch sử",
            "Hoàn tác lượt vừa xong trong cửa sổ 30 giây, không cần thẻ cổng (§E5.2). "
            "Chỉ dùng khi người dùng vừa bảo 'thôi, bỏ đi' ngay sau một lượt.",
            {"type": "object", "properties": {"run_id": {"type": "string"}},
             "required": ["run_id"]},
            risk="R1", core=False, keywords=["hoàn tác nhanh", "bỏ đi", "thôi"])
    def history_undo_30s(ctx: Any, run_id: str):
        import time as _t
        xong = ctx.thoi_diem_ket_thuc.get(run_id)
        if xong is None or _t.time() - xong > 30:
            return ToolResult(False, error=EideError(
                "E7003", "Cửa sổ 30 giây đã qua — hoàn tác lượt này phải đi qua thẻ G-HIST.",
                hint_for_agent="Gọi history.undo scope=run; nó sẽ dựng thẻ cổng.",
                alternatives=["history.undo"], blame="agent"))
        return ctx.history.hoan_tac_luot(run_id, by="human").to_dict()

    @r.tool("tool.search", "Điều phối",
            "Tìm công cụ theo việc muốn làm. Công cụ tìm được sẽ mở khoá để gọi ở lượt sau.",
            {"type": "object",
             "properties": {"query": {"type": "string", "description": "Việc muốn làm"}},
             "required": ["query"]},
            risk="R1", keywords=["công cụ", "tool", "tìm"])
    def tool_search(ctx: Any, query: str):
        found = ctx.registry.search(query)
        return {"count": len(found), "tools": found,
                "note_vi": "" if found else
                "Không có công cụ nào cho việc này. Nói thẳng với người dùng rằng EIDE chưa "
                "làm được việc đó — đừng thay bằng một việc gần giống."}

    from . import ckm, design, knowledge, sch, snapshots, writing
    writing.register(r)
    design.register(r)
    knowledge.register(r)
    snapshots.register(r)
    ckm.register(r)
    # Cờ tắt (mặc định) thì `register` không đăng ký gì — xem Registry.add và SCH-44 §2.1.
    sch.register(r)
    return r


def _render_ask(intro: str, questions: list[dict[str, Any]], assumption: str) -> str:
    """Dạng chữ của thẻ hỏi, cho transcript. Một cụm, đánh số, nói vì sao hỏi."""
    L: list[str] = []
    if intro:
        L.append(intro)
        L.append("")
    for i, q in enumerate(questions, 1):
        line = f"{i}. {q['question']}"
        if q.get("prefill"):
            line += f"  *({q['prefill']} — anh vừa nói trong câu)*"
        L.append(line)
        if q.get("why"):
            L.append(f"   _vì sao hỏi: {q['why']}_")
        if q.get("choices"):
            L.append("   " + " · ".join(f"[{c}]" for c in q["choices"]))
    if assumption:
        L.append("")
        L.append(f"_Nếu anh bỏ qua, tôi sẽ đi tiếp với giả định: {assumption}_")
    return "\n".join(L)
