# -*- coding: utf-8 -*-
"""Cổng mô hình không gọi mạng: kịch bản sẵn và ghi–phát lại.

Vì sao cần: §F3 đòi "lõi chạy headless" và "unit test cho hook, policy, changeset, merge".
Những thứ đó là mã XÁC ĐỊNH — kiểm chúng bằng cách gọi một mô hình thật thì vừa chậm,
vừa tốn, vừa làm kết quả test phụ thuộc vào một thứ không tất định.

Hai lớp:
  - `ScriptedGateway`  — trả lần lượt các phản hồi đã viết sẵn. Dùng để kiểm chính
                         vòng lặp: hook có chạy đúng thứ tự không, cổng có chặn không,
                         ngân sách có cắt đúng chỗ không.
  - `ReplayGateway`    — phát lại phản hồi THẬT đã ghi từ một lần chạy trước. Dùng để
                         hồi quy 76 ca mà không phải gọi lại mô hình mỗi lần chạy CI.

`RecordingGateway` bọc một cổng thật để sinh ra tệp ghi.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from ..errors import EideError
from .gateway import Response, ToolCall, Usage


def _as_response(x: Any) -> Response:
    if isinstance(x, Response):
        return x
    if callable(x):
        return x
    d = dict(x)
    return Response(
        text=d.get("text", ""),
        tool_calls=[ToolCall(id=c.get("id", f"call-{i}"), tool=c["tool"], args=c.get("args", {}))
                    for i, c in enumerate(d.get("tool_calls", []), 1)],
        usage=Usage(**d.get("usage", {})),
        finish_reason=d.get("finish_reason", "STOP"),
        model=d.get("model", "scripted"),
    )


class ScriptedGateway:
    """Trả phản hồi theo kịch bản. Mỗi phần tử là Response, dict, hoặc hàm(messages)->Response."""

    name = "scripted"

    def __init__(self, script: list[Any]):
        self.script = [_as_response(s) for s in script]
        self.calls: list[dict[str, Any]] = []
        self._i = 0

    def stream(self, *, system: str, messages: list[dict[str, Any]],
               tools: list[dict[str, Any]],
               on_text: Callable[[str], None] | None = None,
               model: str | None = None, temperature: float | None = None) -> Response:
        self.calls.append({"system_chars": len(system), "messages": len(messages),
                           "tools": [t["name"] for t in tools]})
        if self._i >= len(self.script):
            # Kịch bản hết mà vòng lặp vẫn hỏi nghĩa là vòng lặp không dừng đúng chỗ.
            # Đây là một LỖI TEST, phải nổ to, không được trả im lặng một câu rỗng.
            raise EideError("E6004",
                            f"Kịch bản hết sau {self._i} lượt gọi nhưng vòng lặp vẫn gọi tiếp.",
                            hint_for_agent="", blame="system")
        item = self.script[self._i]
        self._i += 1
        r = item(messages) if callable(item) else item
        if r.text and on_text:
            on_text(r.text)
        return r

    def count_tokens(self, text: str) -> int:
        return int(len(text) / 3.0)


class RecordingGateway:
    """Bọc một cổng thật, ghi mọi phản hồi ra JSONL để dùng lại."""

    def __init__(self, inner: Any, path: str | Path):
        self.inner = inner
        self.name = f"recording:{inner.name}"
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def stream(self, **kw) -> Response:
        r = self.inner.stream(**kw)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "text": r.text,
                "tool_calls": [{"id": c.id, "tool": c.tool, "args": c.args} for c in r.tool_calls],
                "usage": r.usage.to_dict(), "finish_reason": r.finish_reason, "model": r.model,
            }, ensure_ascii=False) + "\n")
        return r

    def count_tokens(self, text: str) -> int:
        return self.inner.count_tokens(text)


class ReplayGateway(ScriptedGateway):
    """Phát lại tệp do RecordingGateway ghi."""

    name = "replay"

    def __init__(self, path: str | Path):
        rows = [json.loads(l) for l in Path(path).read_text("utf-8").splitlines() if l.strip()]
        for r in rows:
            u = r.get("usage", {})
            r["usage"] = {"input_tokens": u.get("in", 0), "output_tokens": u.get("out", 0),
                          "cached_tokens": u.get("cached", 0),
                          "thoughts_tokens": u.get("thoughts", 0)}
        super().__init__(rows)
