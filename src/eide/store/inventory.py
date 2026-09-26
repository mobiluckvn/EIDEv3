# -*- coding: utf-8 -*-
"""<inventory> — bảng "dự án đang có gì", dựng bằng mã.

EIDE-MDD-40 §B2 và nguyên tắc N3:

    "Kiểm kê thì xác định: tình trạng dự án do mã dựng, tiêm vào ngữ cảnh;
     mô hình không đoán dự án có gì."

Vì sao khối này tồn tại: trong đợt đo 23/09, TC008 chạy hết chuỗi trên một kho RỖNG và
mô hình bịa ra `REQ_HW_I2C`, `REQ_FR_READ_TEMP`, `REQ_FR_PRINT_UART` — những mã không
có trong store. Nó bịa vì không ai nói cho nó biết kho rỗng. Khối này nói.

Hai ràng buộc cứng (§B2, §F3):
  - ≤ 800 token → cắt cứng theo ngân sách ký tự, và cắt ở chỗ nói rõ là đã cắt.
  - < 50 ms    → truy vấn đếm, không nạp nội dung hiện vật.

Và một ràng buộc không ghi trong bảng nhưng suy ra từ §F3 "tất định 100 %": cùng một
kho phải cho ra cùng một chuỗi ký tự. Nên ở đây không có dấu thời gian hiện tại, không
có thứ tự phụ thuộc vào tốc độ đĩa, không có gì ngẫu nhiên.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# Thứ tự dòng cố định — mô hình học được chỗ nào nói gì.
# Tên và thứ tự tầng lấy từ MỘT nguồn (xem `knowledge/compare.py`) — bảng này từng bị
# sao ra hai chỗ, và thêm một tầng làm vỡ chỗ không ai để ý (xem DEV-261).
from ..knowledge.compare import THU_TU_TANG as _TIER_ORDER
from ..knowledge.compare import ten_tang as _ten_tang

# Chặng C1–C7 suy ra từ cái đang có, không hỏi mô hình (§A4).
_STAGE_RULES = [
    ("C6 Mạch thật", lambda c: c.get("target", 0) > 0),
    ("C5 Mô phỏng", lambda c: c.get("sim_result", 0) > 0 or c.get("criteria", 0) > 0),
    ("C4 Firmware", lambda c: c.get("build", 0) > 0 or c.get("code", 0) > 0),
    ("C3 Môi trường công cụ", lambda c: c.get("_toolchain", 0) > 0),
    ("C2 Tài liệu & tri thức mạch", lambda c: c.get("passport", 0) > 0 or c.get("netlist", 0) > 0),
    ("C1 Làm rõ & giải pháp", lambda c: c.get("req", 0) > 0 or c.get("option", 0) > 0),
]


@dataclass(slots=True)
class Inventory:
    counts: dict[str, int] = field(default_factory=dict)
    fact_tiers: dict[str, int] = field(default_factory=dict)
    passport: str | None = None
    isa: str | None = None
    docs: list[str] = field(default_factory=list)
    stale: list[dict[str, Any]] = field(default_factory=list)
    last_run: dict[str, Any] | None = None
    unfinished_run: dict[str, Any] | None = None
    pending_cards: list[dict[str, Any]] = field(default_factory=list)
    last_snapshot: dict[str, Any] | None = None
    changesets_since_snapshot: int = 0
    branch: str = "main"
    project_name: str = ""
    elapsed_ms: float = 0.0

    # ------------------------------------------------------------------ dạng mô hình đọc
    def render(self, budget_chars: int = 3200) -> str:
        L: list[str] = ["<inventory>",
                        "Bảng này do mã dựng từ kho dự án. Nó là SỰ THẬT về dự án đang có gì.",
                        "Đừng mô tả dự án bằng trí nhớ hay phỏng đoán — đọc ở đây.",
                        ""]
        c = self.counts
        L.append(f"Dự án: {self.project_name or '(chưa đặt tên)'} · nhánh: {self.branch} · chặng: {self._stage()}")

        # --- Yêu cầu & giải pháp
        L.append(f"Yêu cầu (REQ): {c.get('req', 0)} · phương án: {c.get('option', 0)} · ADR: {c.get('adr', 0)}")

        # --- Chip & Fact
        if self.passport:
            L.append(f"Hộ chiếu chip: {self.passport}" + (f" · ISA: {self.isa}" if self.isa else ""))
        else:
            L.append("Hộ chiếu chip: CHƯA GHIM. Không có chip nào được ghim trong dự án này.")
        if self.fact_tiers:
            tiers = " · ".join(f"{_ten_tang(t)} {self.fact_tiers.get(t, 0)}"
                               for t in _TIER_ORDER if self.fact_tiers.get(t))
            L.append(f"Fact: {sum(self.fact_tiers.values())} ({tiers})")
        else:
            L.append("Fact: 0. Chưa có con số nào truy vết được tới tài liệu.")

        # --- Tài liệu
        if self.docs:
            L.append(f"Tài liệu đã nạp ({len(self.docs)}): " + ", ".join(self.docs[:8])
                     + (" …" if len(self.docs) > 8 else ""))
        else:
            L.append("Tài liệu: 0. Chưa nạp datasheet hay tài liệu nào.")

        # --- Thiết kế & mã
        L.append(
            f"Thiết kế: module {c.get('block_diagram', 0)} · netlist {c.get('netlist', 0)} · "
            f"pinout {c.get('pinout', 0)} · BOM {c.get('bom', 0)}")
        L.append(
            f"Mã & chạy: tệp mã {c.get('code', 0)} · build {c.get('build', 0)} · "
            f"tiêu chí {c.get('criteria', 0)} · mô phỏng {c.get('sim_result', 0)} · "
            f"nạp/dò board {c.get('target', 0)}")

        # --- Lịch sử
        if self.last_snapshot:
            L.append(f"Snapshot gần nhất: {self.last_snapshot.get('name')} "
                     f"({self.last_snapshot.get('id')}), cách đây {self.changesets_since_snapshot} changeset")
        else:
            L.append("Snapshot: chưa có bản ưng ý nào được ghi.")

        if self.stale:
            L.append(f"Hiện vật STALE ({len(self.stale)}) — cần cập nhật vì thượng nguồn đã đổi:")
            for s in self.stale[:6]:
                L.append(f"  - {s['id']} ({s['type']}): {s.get('stale_reason') or 'không rõ lý do'}")
            if len(self.stale) > 6:
                L.append(f"  … và {len(self.stale) - 6} cái nữa")
        else:
            L.append("STALE: 0.")

        # --- Việc dở
        if self.unfinished_run:
            L.append(f"Lượt chạy dở: {self.unfinished_run.get('run_id')} — "
                     f"{(self.unfinished_run.get('text') or '')[:70]}")
        if self.pending_cards:
            L.append(f"Thẻ đang chờ người trả lời ({len(self.pending_cards)}): "
                     + ", ".join(f"{p.get('gate') or p.get('type')}[{p.get('card_id')}]"
                                 for p in self.pending_cards[:4]))

        if not any(c.values()) and not self.fact_tiers and not self.docs:
            L.append("")
            L.append("DỰ ÁN TRỐNG: chưa có yêu cầu, chưa có tài liệu, chưa có thiết kế, chưa có mã.")
            L.append("Nếu người dùng hỏi về nội dung dự án, câu trả lời đúng là 'chưa có gì' —")
            L.append("không được kể ra bất kỳ REQ, module hay Fact nào.")

        L.append("</inventory>")
        out = "\n".join(L)
        if len(out) > budget_chars:
            out = out[:budget_chars - 60] + "\n…(kiểm kê bị cắt vì quá dài)\n</inventory>"
        return out

    def to_dict(self) -> dict[str, Any]:
        return {"counts": self.counts, "fact_tiers": self.fact_tiers, "passport": self.passport,
                "isa": self.isa, "docs": self.docs, "stale": self.stale,
                "last_run": self.last_run, "unfinished_run": self.unfinished_run,
                "pending_cards": self.pending_cards, "last_snapshot": self.last_snapshot,
                "changesets_since_snapshot": self.changesets_since_snapshot,
                "branch": self.branch, "project_name": self.project_name,
                "elapsed_ms": round(self.elapsed_ms, 2)}

    def _stage(self) -> str:
        for name, pred in _STAGE_RULES:
            if pred(self.counts):
                return name
        return "C1 Làm rõ & giải pháp (chưa bắt đầu)"


def build(store: Any, *, ledger: Any = None, project_name: str = "",
          branch: str = "main", pending_cards: list[dict[str, Any]] | None = None) -> Inventory:
    """Dựng bảng kiểm kê. 0 token, xác định, mục tiêu < 50 ms."""
    t0 = time.perf_counter()
    inv = Inventory(project_name=project_name, branch=branch,
                    pending_cards=list(pending_cards or []))

    inv.counts = store.counts()
    inv.fact_tiers = store.fact_tier_counts()

    passports = store.list("passport", limit=1)
    if passports:
        can = passports[0]["canonical"]
        inv.passport = can.get("id") or passports[0]["id"]
        inv.isa = can.get("isa")

    inv.docs = [a["canonical"].get("title") or a["id"] for a in store.list("doc", limit=20)]

    inv.stale = [{"id": a["id"], "type": a["type"], "stale_reason": a["stale_reason"]}
                 for a in store.list(stale_only=True, limit=50)]

    snaps = store.list("snapshot", limit=1)
    if snaps:
        inv.last_snapshot = {"id": snaps[0]["id"], "name": snaps[0]["canonical"].get("name")}
        inv.changesets_since_snapshot = store.counts().get("changeset", 0)

    if ledger is not None:
        runs = ledger.find_run("")
        if runs:
            inv.last_run = runs[-1]
            # Lượt dở = lượt có turn.start mà không có turn.end tương ứng.
            ended = {ev.data.get("run_id") for ev in ledger.read() if ev.kind == "turn.end"}
            if runs[-1]["run_id"] not in ended:
                inv.unfinished_run = runs[-1]

    inv.elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return inv
