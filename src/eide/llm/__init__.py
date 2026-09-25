# -*- coding: utf-8 -*-
"""Cổng mô hình — §B1 `llm.stream(...)`. Nhà cung cấp hiện dùng: Google Gemini."""

from .gateway import LLMGateway, Response, ToolCall, Usage, declarations_for, sanitize_schema
from .offline import RecordingGateway, ReplayGateway, ScriptedGateway

__all__ = ["LLMGateway", "Response", "ToolCall", "Usage", "declarations_for",
           "sanitize_schema", "ScriptedGateway", "ReplayGateway", "RecordingGateway",
           "make_gateway"]


def make_gateway(cfg=None, *, offline: bool = False, script=None, replay=None, record=None):
    """Chọn cổng theo cấu hình. Gemini nạp trễ để chạy offline không cần SDK."""
    if script is not None:
        return ScriptedGateway(script)
    if replay is not None:
        return ReplayGateway(replay)
    if offline:
        return ScriptedGateway([])
    from .gemini import GeminiGateway
    gw = GeminiGateway(cfg)
    return RecordingGateway(gw, record) if record else gw
