# -*- coding: utf-8 -*-
"""Cổng mô hình — lớp trừu tượng giữa vòng lặp và nhà cung cấp.

EIDE-MDD-40 §B1 gọi `llm.stream(ctx, msgs, tools=tools.visible())`. Vòng lặp chỉ cần
biết đúng chừng đó. Mọi khác biệt về định dạng của nhà cung cấp (Gemini dùng
`function_call`/`function_response`, OpenAI dùng `tool_calls`…) bị nhốt trong adapter.

Dạng thông điệp nội bộ — cố tình đơn giản, vì nó còn phải ghi được xuống sổ cái và
phát lại được (CX16):

    {"role": "user",  "text": "..."}
    {"role": "model", "text": "...", "tool_calls": [{"id","tool","args"}]}
    {"role": "tool",  "tool_call_id": "...", "tool": "...", "result": {...}}

Hai yêu cầu của §F3 nằm ở đây:
  - **Tất định**: nhiệt độ 0 cho mọi lời gọi. Một tác tử kỹ thuật không được cho hai
    câu trả lời khác nhau cho cùng một câu hỏi về cùng một datasheet.
  - **Không mất việc khi nhà cung cấp hỏng** (UC19/TC073): thử lại có giới hạn rồi trả
    lỗi E6001 — vòng lặp giữ nguyên mọi thứ đã làm trong lượt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol


@dataclass(slots=True)
class ToolCall:
    id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    thoughts_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

    def add(self, other: "Usage") -> "Usage":
        return Usage(self.input_tokens + other.input_tokens,
                     self.output_tokens + other.output_tokens,
                     self.cached_tokens + other.cached_tokens,
                     self.thoughts_tokens + other.thoughts_tokens)

    def to_dict(self) -> dict[str, int]:
        return {"in": self.input_tokens, "out": self.output_tokens,
                "cached": self.cached_tokens, "thoughts": self.thoughts_tokens}


@dataclass(slots=True)
class Response:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    finish_reason: str = ""
    model: str = ""
    elapsed_ms: float = 0.0
    # Bản ghi trung thực các "phần" (part) mô hình trả về, dạng serialize được.
    # Cần cho nhà cung cấp nào đòi gửi lại nguyên trạng lượt trước — Gemini 3.x đòi
    # `thought_signature` đi kèm mỗi function_call, thiếu là lỗi 400. Xem `gemini.py`.
    parts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)

    def to_message(self) -> dict[str, Any]:
        m: dict[str, Any] = {"role": "model", "text": self.text}
        if self.tool_calls:
            m["tool_calls"] = [{"id": c.id, "tool": c.tool, "args": c.args}
                               for c in self.tool_calls]
        if self.parts:
            m["parts"] = self.parts
        return m


class LLMGateway(Protocol):
    """Hợp đồng mà vòng lặp trông vào. Đổi nhà cung cấp = viết một lớp mới ở đây."""

    name: str

    def stream(self, *, system: str, messages: list[dict[str, Any]],
               tools: list[dict[str, Any]],
               on_text: Callable[[str], None] | None = None,
               model: str | None = None,
               temperature: float | None = None) -> Response: ...

    def count_tokens(self, text: str) -> int: ...


# --------------------------------------------------------------------------- tiện chung
_SUPPORTED_SCHEMA_KEYS = {
    "type", "format", "description", "nullable", "enum", "items", "properties",
    "required", "minimum", "maximum", "min_items", "max_items",
}


def sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """JSON Schema → tập con OpenAPI mà các nhà cung cấp chấp nhận.

    Bỏ `additionalProperties`, `$schema`, `default`… Giữ kiểu viết HOA vì API của
    Gemini dùng enum `Type` (OBJECT/STRING/…). Adapter nào cần chữ thường thì tự hạ.
    """
    out: dict[str, Any] = {}
    for k, v in (schema or {}).items():
        if k not in _SUPPORTED_SCHEMA_KEYS:
            continue
        if k == "type" and isinstance(v, str):
            out[k] = v.upper()
        elif k == "properties" and isinstance(v, dict):
            out[k] = {pk: sanitize_schema(pv) for pk, pv in v.items()}
        elif k == "items" and isinstance(v, dict):
            out[k] = sanitize_schema(v)
        else:
            out[k] = v
    return out


def declarations_for(tools: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dọn danh sách khai báo công cụ; bỏ `parameters` rỗng (một số API từ chối)."""
    out = []
    for t in tools:
        d: dict[str, Any] = {"name": t["name"], "description": t.get("description", "")}
        params = sanitize_schema(t.get("parameters") or {})
        if params.get("properties"):
            d["parameters"] = params
        out.append(d)
    return out
