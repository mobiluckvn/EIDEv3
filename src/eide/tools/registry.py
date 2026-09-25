# -*- coding: utf-8 -*-
"""Sổ đăng ký công cụ — EIDE-MDD-40 §B3.

    "≈40 công cụ có lược đồ JSON, nạp trễ (tool.search). Mỗi công cụ kiểm tiền đề bên
     trong và trả lỗi có hướng dẫn — lỗi là dữ liệu để mô hình đổi hướng. Mọi công cụ
     ghi hiện vật đều phải nhận trường explain và sinh changeset."

Hợp đồng của một công cụ khai báo đủ thứ để ba lớp xung quanh nó làm việc được mà không
cần biết bên trong nó làm gì:

  - `params`          → dịch thẳng sang function declaration của nhà cung cấp mô hình
  - `requires`        → công cụ tự sinh lỗi E2001 "gọi gì trước" thay vì chết vô nghĩa
  - `writes_artefact` → hook PreToolUse biết có phải kiểm `explain` đủ 6 trường không (N8)
  - `risk` / `gate`   → lớp cấp quyền biết allow/ask/deny mà không cần bảng riêng
  - `produces`        → mô hình biết gọi cái này thì được cái gì

Vì sao KHÔNG có planner đọc `requires` để xếp chuỗi: v3 bỏ planner theo mẫu chuỗi
(§B1 "không có máy trạng thái, không có phân loại ý định, không có planner theo mẫu
chuỗi"). `requires` ở đây chỉ để sinh LỖI CÓ HƯỚNG DẪN. Mô hình tự quyết thứ tự.
"""

from __future__ import annotations

import fnmatch
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from ..errors import EideError, missing_precondition, schema_violation

# Mức rủi ro — dùng cho lớp cấp quyền và cho việc "tin lần sau" (§E7 thẻ cổng).
# R0 người tự làm · R1 đọc · R2 ghi trong dự án · R3 chạm hệ thống/mạng · R4 không đảo ngược
RISK_LEVELS = ("R0", "R1", "R2", "R3", "R4")


@dataclass(slots=True)
class Requirement:
    """Một tiền đề. §B3: công cụ tự kiểm bên trong."""

    artefact: str
    min_count: int = 1
    tier_min: str | None = None
    how_to_get: str = ""          # tên công cụ lấy được thứ này, để lỗi nói ra được
    label_vi: str = ""

    def describe(self) -> str:
        return self.label_vi or f"{self.min_count} {self.artefact}"


@dataclass(slots=True)
class ToolSpec:
    name: str
    group: str
    summary_vi: str
    params: dict[str, Any]                     # JSON Schema (object)
    fn: Callable[..., Any]
    returns_vi: str = ""
    requires: list[Requirement] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)
    writes_artefact: bool = False
    needs_explain: bool = False
    risk: str = "R1"
    gate: str | None = None
    core: bool = True                          # core = luôn hiện; còn lại nạp qua tool.search
    keywords: list[str] = field(default_factory=list)

    def declaration(self) -> dict[str, Any]:
        """Dạng khai báo hàm cho mô hình. Mô tả phải nói cả KHI NÀO KHÔNG dùng."""
        desc = self.summary_vi
        if self.requires:
            desc += " · Cần trước: " + "; ".join(r.describe() for r in self.requires)
        if self.produces:
            desc += " · Sinh ra: " + ", ".join(self.produces)
        if self.gate:
            desc += f" · Đi qua cổng {self.gate} (người phải duyệt)"
        return {"name": self.name, "description": desc, "parameters": self.params}


@dataclass(slots=True)
class ToolResult:
    ok: bool
    data: Any = None
    error: EideError | None = None
    elapsed_ms: float = 0.0
    artefact_id: str | None = None

    def to_model(self) -> dict[str, Any]:
        if not self.ok and self.error is not None:
            return self.error.to_tool_result()
        return {"ok": True, "data": self.data}


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}
        self._unlocked: set[str] = set()       # công cụ đã nạp qua tool.search

    # ------------------------------------------------------------------ đăng ký
    def add(self, spec: ToolSpec) -> ToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"Công cụ {spec.name} đã đăng ký rồi.")
        if spec.risk not in RISK_LEVELS:
            raise ValueError(f"Mức rủi ro lạ: {spec.risk}")
        if spec.writes_artefact and not spec.needs_explain:
            # N8 không có ngoại lệ: ghi hiện vật thì phải có lớp giải thích.
            raise ValueError(f"{spec.name} ghi hiện vật nhưng không đòi explain — trái N8.")
        self._tools[spec.name] = spec
        return spec

    def tool(self, name: str, group: str, summary_vi: str, params: dict[str, Any], **kw):
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.add(ToolSpec(name=name, group=group, summary_vi=summary_vi,
                              params=params, fn=fn, **kw))
            return fn
        return deco

    # ------------------------------------------------------------------ tra cứu
    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def all(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def visible(self) -> list[ToolSpec]:
        """Nạp trễ: chỉ công cụ core + cái đã mở bằng tool.search (§B3)."""
        return [t for t in self._tools.values() if t.core or t.name in self._unlocked]

    def declarations(self) -> list[dict[str, Any]]:
        return [t.declaration() for t in self.visible()]

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        """tool.search — tìm rồi MỞ KHOÁ công cụ khớp, để lượt sau mô hình gọi được."""
        q = query.lower().strip()
        scored: list[tuple[int, ToolSpec]] = []
        for t in self._tools.values():
            s = 0
            if fnmatch.fnmatch(t.name, q) or q in t.name.lower():
                s += 10
            if q in t.summary_vi.lower():
                s += 5
            s += sum(3 for k in t.keywords if k.lower() in q or q in k.lower())
            s += sum(1 for w in q.split() if w in t.summary_vi.lower())
            if s:
                scored.append((s, t))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        out = []
        for _, t in scored[:limit]:
            self._unlocked.add(t.name)
            out.append({"name": t.name, "group": t.group, "summary_vi": t.summary_vi,
                        "risk": t.risk, "gate": t.gate,
                        "requires": [r.describe() for r in t.requires],
                        "produces": t.produces})
        return out

    # ------------------------------------------------------------------ chạy
    def check_preconditions(self, spec: ToolSpec, ctx: Any) -> EideError | None:
        """Kiểm tiền đề bằng kho, TRƯỚC khi vào thân công cụ (§B3)."""
        if not spec.requires or ctx is None or getattr(ctx, "store", None) is None:
            return None
        counts = ctx.store.counts()
        for r in spec.requires:
            if counts.get(r.artefact, 0) < r.min_count:
                return missing_precondition(
                    spec.name, r.describe(), r.how_to_get,
                    artefacts_present=[f"{k}×{v}" for k, v in counts.items() if v])
        return None

    def run(self, name: str, args: dict[str, Any], ctx: Any) -> ToolResult:
        t0 = time.perf_counter()
        spec = self._tools.get(name)
        if spec is None:
            near = self.search(name, limit=3)
            return ToolResult(False, error=EideError(
                code="E5004",
                message_vi=f"Không có công cụ tên {name}.",
                hint_for_agent=("Gọi tool.search để tìm đúng tên công cụ. "
                                + (f"Gần nhất: {', '.join(n['name'] for n in near)}" if near else "")),
                alternatives=[n["name"] for n in near], blame="agent"),
                elapsed_ms=(time.perf_counter() - t0) * 1000)

        err = _validate_args(spec, args)
        if err is None:
            err = self.check_preconditions(spec, ctx)
        if err is not None:
            return ToolResult(False, error=err, elapsed_ms=(time.perf_counter() - t0) * 1000)

        try:
            data = spec.fn(ctx=ctx, **args)
            res = data if isinstance(data, ToolResult) else ToolResult(True, data)
        except EideError as e:
            res = ToolResult(False, error=e)
        except Exception as e:
            # Sự cố thật trong công cụ: vẫn trả về dạng dữ liệu để mô hình đổi hướng,
            # nhưng ghi đúng là lỗi hệ thống — không giả vờ là lỗi tham số.
            res = ToolResult(False, error=EideError(
                code="E5999", message_vi=f"Công cụ {name} hỏng: {type(e).__name__}: {e}",
                hint_for_agent="Đây là lỗi bên trong công cụ, không phải lỗi tham số của bạn. "
                               "Thử đường khác hoặc báo cho người dùng.",
                blame="system"))
        res.elapsed_ms = (time.perf_counter() - t0) * 1000
        return res


def _validate_args(spec: ToolSpec, args: dict[str, Any]) -> EideError | None:
    """Kiểm nhẹ theo JSON Schema: đủ trường bắt buộc, không thừa trường lạ."""
    schema = spec.params or {}
    props = schema.get("properties", {})
    required = schema.get("required", [])
    missing = [k for k in required if k not in args or args[k] is None]
    if missing:
        return schema_violation(f"tham số của {spec.name}",
                                f"thiếu {', '.join(missing)}. Cần: {', '.join(props)}")
    extra = [k for k in args if k not in props]
    if extra:
        return schema_violation(f"tham số của {spec.name}",
                                f"không có tham số {', '.join(extra)}. Chỉ nhận: {', '.join(props)}")
    return None
