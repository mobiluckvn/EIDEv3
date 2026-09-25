# -*- coding: utf-8 -*-
"""Hook — mã xác định chạy quanh mỗi lời gọi công cụ và mỗi lượt.

EIDE-MDD-40 §B4. Sáu hook, mỗi cái canh một nhóm nguyên tắc:

    UserPromptSubmit  S0 rule engine (0 token)                 N5
    PreToolUse        constant-guard, tier-check, sandbox,      N1 N2 N8
                      kiểm explain đủ 6 trường, base_version
    PostToolUse       changeset + sổ cái + đồng bộ Surface      N6 N9
                      + đánh dấu STALE + lint log rỗng
    Stop              giả định đã nói? explain? người vừa sửa   N4 N8 N9
                      đã được nhắc? thẻ chờ? chi phí
    SubagentStop      kiểm lược đồ báo cáo, gọi verifier        N6
    PreCompact        rút quyết định/giả định vào EIDE.md       N9

Vì sao các nguyên tắc sống ở đây chứ không trong lời dặn mô hình: một lời dặn bị bỏ
qua thì không ai biết; một hook bị bỏ qua thì mã không chạy. §A3 đòi mỗi nguyên tắc
chỉ rõ "sống ở đâu (mã, không chỉ lời dặn)".
"""

from .base import HookBus, HookResult, PreToolResult, StopResult
from .s0 import S0Engine, S0Result

__all__ = ["HookBus", "HookResult", "PreToolResult", "StopResult", "S0Engine", "S0Result"]
