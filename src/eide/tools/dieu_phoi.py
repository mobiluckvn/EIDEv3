# -*- coding: utf-8 -*-
"""Điều phối — `task.run` (Task(subagent) của §B1) và `skill.load`.

Hai công cụ này không tự làm việc gì; chúng quyết **ai làm** và **theo hướng dẫn nào**. Cả
hai đều rẻ và cả hai đều dễ dùng sai theo cùng một cách: gọi cho có, rồi tin kết quả vì nó
đến từ "một tác tử chuyên trách".

Nên `task.run` luôn trả về báo cáo KÈM kết quả kiểm lược đồ và, với firmware/sim tuyên đạt,
kèm luôn kết luận của verifier — kể cả khi verifier bác nó.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:
    from .. import subagent as SA

    @r.tool("task.run", "Điều phối",
            "Giao một việc cho TÁC TỬ CON chuyên trách: nó chạy với ngữ cảnh sạch, tập công "
            "cụ giới hạn, và trả về báo cáo có lược đồ. Ai tuyên “đạt” thì tự động qua "
            "verifier độc lập.",
            {"type": "object",
             "properties": {
                 "subagent": {"type": "string", "enum": sorted(SA.SUBAGENT),
                              "description": "ai làm việc này"},
                 "viec": {"type": "string",
                          "description": "việc cần làm, đủ rõ để làm mà không cần đọc lại "
                                         "cuộc trò chuyện"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["subagent", "viec", "explain"]},
            risk="R2", core=False, needs_explain=True,
            keywords=["subagent", "tác tử con", "giao việc", "task", "kiểm chứng",
                      "verifier", "rà soát"])
    def task_run(ctx: Any, explain: dict[str, Any], subagent: str, viec: str):
        """Vì sao verifier được gọi TỰ ĐỘNG chứ không để mô hình tự quyết.

        Nếu việc gọi verifier là tuỳ chọn thì nó sẽ được gọi đúng những lúc không cần: khi mô
        hình đã tin kết quả. Lúc nó tự tin nhất cũng là lúc nó ít gọi nhất — và đó chính là
        lúc cần nhất. Nên hook SubagentStop gọi, không phải mô hình gọi.
        """
        dn = SA.SUBAGENT.get(subagent)
        if dn is None:
            return ToolResult(False, error=EideError(
                "E5004", f"Không có tác tử con tên “{subagent}”.",
                hint_for_agent="Có: " + ", ".join(
                    f"{k} ({v.muc_dich})" for k, v in SA.SUBAGENT.items()),
                details={"co": sorted(SA.SUBAGENT)}, blame="agent"))
        if not (viec or "").strip():
            return ToolResult(False, error=EideError(
                "E5001", "Việc giao cho tác tử con đang rỗng.",
                hint_for_agent=("Viết đủ rõ để làm mà KHÔNG cần đọc lại cuộc trò chuyện — "
                                "tác tử con không thấy transcript, và đó là cố ý."),
                blame="agent"))

        llm = getattr(getattr(ctx, "agent", None), "llm", None)
        if llm is None:
            return ToolResult(False, error=EideError(
                "E5999", "Không có cổng mô hình để chạy tác tử con.",
                hint_for_agent="Đây là lỗi hệ thống — báo cho người dùng.",
                blame="system"))

        ghi = None
        if getattr(ctx, "ledger", None) is not None:
            def ghi(kind: str, data: dict[str, Any]) -> None:   # noqa: F811
                ctx.ledger.append(kind, {"run_id": getattr(ctx, "run_id", ""), **data})

        bc = SA.chay(llm=llm, registry=ctx.registry, ctx=ctx, ma=subagent, viec=viec,
                     ghi_so=ghi)

        # --- Hook SubagentStop (§B5): kiểm lược đồ, rồi firmware/sim tuyên đạt → verifier.
        if SA.can_goi_verifier(bc):
            kc = SA.chay(llm=llm, registry=ctx.registry, ctx=ctx, ma="verifier",
                         viec=SA.viec_cho_verifier(bc), ghi_so=ghi)
            bc = SA.gop_kiem_chung(bc, kc)
        if ghi is not None:
            ghi("subagent_stop", {"subagent": subagent, "ket_luan": bc.ket_luan,
                                  "hop_le": bc.hop_le, "so_goi": bc.so_goi,
                                  "co_kiem_chung": bc.kiem_chung is not None})

        d = bc.to_dict()
        if not bc.hop_le:
            return ToolResult(False, error=EideError(
                "E5007",
                f"Tác tử con “{subagent}” không nộp được báo cáo đúng lược đồ: "
                + "; ".join(bc.loi_luoc_do),
                hint_for_agent=(
                    "Phần việc nó đã ghi vào kho vẫn còn. Giao lại việc nhỏ hơn, hoặc tự làm "
                    "phần còn lại. ĐỪNG kể lại đoạn văn nó viết như thể đó là kết quả — báo "
                    "cáo không đúng lược đồ thì không có kết luận nào để dùng."),
                details=d, blame="system"))

        kc = bc.kiem_chung or {}
        return {
            **d,
            "note_vi": (
                f"[{dn.ten}] {bc.tom_tat} "
                + f"Kết luận: {_vi_ket_luan(bc.ket_luan)}. "
                + (f"Đã làm {len(bc.da_lam)} việc, {len(bc.bang_chung)} bằng chứng. "
                   if bc.da_lam or bc.bang_chung else "")
                + (f"CHƯA làm: {'; '.join(bc.chua_lam[:3])}. " if bc.chua_lam else "")
                + (("Verifier độc lập đã đọc lại bằng chứng và "
                    + ("ĐỒNG Ý" if kc.get("ket_luan") == "dat" else
                       "KHÔNG đồng ý: " + str(kc.get("tom_tat", ""))[:160])
                    + ". ") if kc else "")
                + "Trình lại cho người dùng bằng lời của họ; đừng chỉ chuyển tiếp JSON."),
        }

    @r.tool("skill.load", "Điều phối",
            "Nạp một SKILL — hướng dẫn viết sẵn cho một loại việc (nêu tiêu chí trước, viết "
            "AVR bare-metal, phân tích hardfault…). Nạp rồi thì làm theo, đừng làm theo trí "
            "nhớ chung.",
            {"type": "object",
             "properties": {
                 "ten": {"type": "string", "description": "tên skill, ví dụ sim-criteria-first"},
                 "tim": {"type": "string", "description": "tìm skill theo từ khoá"}}},
            risk="R1", core=False,
            keywords=["skill", "hướng dẫn", "quy trình", "cách làm", "checklist"])
    def skill_load(ctx: Any, ten: str = "", tim: str = ""):
        from ..skills import doc_skill, tim_skill

        if not ten:
            ds = tim_skill(tim)
            return {"so_skill": len(ds), "skill": ds,
                    "note_vi": ("Có " + ", ".join(f"{s['ten']} ({s['khi_nao']})" for s in ds)
                                + ". Gọi lại với `ten` để nạp nội dung."
                                if ds else
                                "Không có skill nào khớp. Làm theo hiểu biết của bạn, nhưng "
                                "nói rõ với người dùng là chưa có hướng dẫn sẵn cho việc này.")}
        s = doc_skill(ten)
        if s is None:
            return ToolResult(False, error=EideError(
                "E5004", f"Không có skill tên “{ten}”.",
                hint_for_agent="Gọi skill.load không tham số để xem danh sách.",
                details={"co": [x["ten"] for x in tim_skill("")]}, blame="agent"))
        return {**s, "note_vi": (f"Đã nạp skill “{ten}”. Nội dung dưới đây là HƯỚNG DẪN cho "
                                 "bạn làm theo trong việc đang làm.")}


def _vi_ket_luan(k: str) -> str:
    return {"dat": "ĐẠT", "khong_dat": "KHÔNG đạt",
            "chua_du_du_kien": "CHƯA đủ dữ kiện để kết luận"}.get(k, k)
