# -*- coding: utf-8 -*-
"""Kiểu kết quả chung của hook + bus gọi chúng theo đúng thứ tự vòng lặp §B1."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..errors import EideError


@dataclass(slots=True)
class HookResult:
    """Kết quả chung: có chặn không, nói gì với người, gắn gì cho mô hình."""

    block: bool = False
    reply_vi: str = ""
    annotations: list[str] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    notices: list[dict[str, Any]] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PreToolResult:
    """PreToolUse — chạy TRƯỚC lớp cấp quyền (§B1: `pre` rồi mới `policy.decide`)."""

    ok: bool = True
    error: EideError | None = None
    # Chú thích cho lớp cấp quyền đọc: constant_guard.unsourced, target.human_edited…
    facts: dict[str, Any] = field(default_factory=dict)
    fired: list[str] = field(default_factory=list)


@dataclass(slots=True)
class StopResult:
    """Stop hook — quyết định CHO MÔ HÌNH THÊM MỘT VÒNG hay kết thúc lượt.

    §B4: "giả định chưa nói? hiện vật thiếu explain? <human_edits> chưa được nhắc?
    thẻ chờ chưa trả lời? → cho mô hình thêm một vòng; ghi chi phí".
    """

    another_round: bool = False
    reason_vi: str = ""
    injection: str = ""       # nhắc nhở chèn vào transcript để mô hình đọc ở vòng sau
    fired: list[str] = field(default_factory=list)


class HookBus:
    """Nơi đăng ký hook. Giữ thứ tự khai báo; không có hook nào được bỏ qua trong im lặng."""

    def __init__(self) -> None:
        self._pre: list[Callable[..., PreToolResult]] = []
        self._post: list[Callable[..., None]] = []
        self._stop: list[Callable[..., StopResult]] = []

    def on_pre_tool(self, fn: Callable[..., PreToolResult]) -> Callable[..., PreToolResult]:
        self._pre.append(fn)
        return fn

    def on_post_tool(self, fn: Callable[..., None]) -> Callable[..., None]:
        self._post.append(fn)
        return fn

    def on_stop(self, fn: Callable[..., StopResult]) -> Callable[..., StopResult]:
        self._stop.append(fn)
        return fn

    # ------------------------------------------------------------------ chạy
    def pre_tool_use(self, call: dict[str, Any], ctx: Any) -> PreToolResult:
        merged = PreToolResult()
        for fn in self._pre:
            r = fn(call, ctx)
            merged.fired.extend(r.fired)
            merged.facts.update(r.facts)
            if not r.ok:
                # Hook đầu tiên nói không thì dừng — lỗi đầu tiên là lỗi đúng nguyên nhân.
                merged.ok = False
                merged.error = r.error
                return merged
        return merged

    def post_tool_use(self, call: dict[str, Any], result: Any, ctx: Any) -> None:
        for fn in self._post:
            fn(call, result, ctx)

    def stop(self, ctx: Any) -> StopResult:
        out = StopResult()
        parts: list[str] = []
        for fn in self._stop:
            r = fn(ctx)
            out.fired.extend(r.fired)
            if r.another_round:
                out.another_round = True
                if r.injection:
                    parts.append(r.injection)
                if r.reason_vi:
                    out.reason_vi = (out.reason_vi + "; " + r.reason_vi).strip("; ")
        out.injection = "\n".join(parts)
        return out
