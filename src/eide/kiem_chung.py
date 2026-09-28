# -*- coding: utf-8 -*-
"""Có việc nào đã GHI mà chưa ai kiểm chứng độc lập chưa? — đọc từ SỔ CÁI.

Vì sao không giữ một cờ trong bộ nhớ: đo được trên phiên FreeRTOS, app EIDE **khởi động lại
giữa các bước làm việc**, nên một cờ nằm trong đối tượng `Agent` reset về `False` mỗi lần —
và việc đã ghi ở tiến trình trước thành vô hình. Cờ ấy chỉ đúng trong một phiên liền mạch,
mà "liền mạch" là điều kiện ta không kiểm soát được.

Sổ cái thì bền: nó ghi mọi lời gọi công cụ, và câu hỏi *"kể từ lần verifier chạy gần nhất, có
lời gọi GHI nào không"* trả lời được chỉ bằng cách đọc ngược nó.
"""

from __future__ import annotations

from typing import Any

# Công cụ được coi là GHI. Lấy từ hợp đồng khi có `registry`; danh sách này chỉ là lưới
# hứng cho trường hợp không có registry trong tay (ví dụ đọc sổ cái ngoài tiến trình).
_GHI_CHAC_CHAN = ("fs.write", "fs.edit", "target.flash", "build.compile")

# Đọc ngược bấy nhiêu bản ghi là đủ: verifier chạy ở cuối mỗi đợt việc, nên nếu lùi xa hơn
# thế mà chưa gặp nó thì câu trả lời đã rõ rồi.
TRAN_DOC_NGUOC = 3000


def co_viec_chua_kiem(ledger: Any, registry: Any = None) -> tuple[bool, str]:
    """`(còn việc chưa kiểm, lời giải thích)`.

    Đọc ngược sổ cái tới lần `task.run(subagent="verifier")` gần nhất. Gặp một lời gọi GHI
    trước khi gặp nó ⇒ còn việc chưa ai kiểm.
    """
    if ledger is None:
        return False, ""
    try:
        ds = list(ledger.read())
    except Exception:                                        # noqa: BLE001
        return False, ""
    ghi: list[str] = []
    for ev in reversed(ds[-TRAN_DOC_NGUOC:]):
        if ev.kind != "tool_use":
            continue
        d = ev.data or {}
        ten = d.get("tool") or ""
        if ten == "task.run" and (d.get("args") or {}).get("subagent") == "verifier":
            break
        if _la_ghi(ten, registry):
            ghi.append(ten)
    if not ghi:
        return False, ""
    # Giữ thứ tự xuôi cho người đọc, và bỏ trùng liên tiếp.
    xuoi: list[str] = []
    for t in reversed(ghi):
        if not xuoi or xuoi[-1] != t:
            xuoi.append(t)
    return True, " → ".join(xuoi[-8:])


def _la_ghi(ten: str, registry: Any) -> bool:
    if ten in _GHI_CHAC_CHAN:
        return True
    if registry is None:
        return False
    sp = registry.get(ten)
    return bool(getattr(sp, "writes_artefact", False)) if sp is not None else False
