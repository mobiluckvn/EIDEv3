# -*- coding: utf-8 -*-
"""C1 — thu gọn cơ học, 0 token. EIDE-MEM-42 §6.1.

Bốn việc, tất cả đều bằng mã, không gọi mô hình:

1. **Stub** mọi `tool_result` cũ hơn 8 lượt — giữ `summary_line` + `blob_ref`.
2. **Dedup** — đọc lại cùng tệp cùng phiên bản thì lần cũ thành một dòng trỏ tới lần mới.
3. **Supersede** — tệp đã được sửa thì kết quả đọc bản cũ thành stub nói rõ đã có bản mới.
4. **Thẻ đã đóng** — giữ tiêu đề + câu trả lời của người, bỏ danh sách lựa chọn.

Vì sao C1 đáng làm trước C2: nó thường giảm 30–50 % mà **không tốn một token nào** và
không có rủi ro mất nghĩa. C2 gọi mô hình tóm tắt, tức là đưa một phép đoán vào giữa
đường — chỉ nên tới đó khi C1 đã hết tác dụng.

Điều bản trước làm sai và bộ này sửa: nó đếm **message**, trong khi tài liệu nói **lượt**.
Một lượt thường là 4–10 message, nên "giữ 10 message" thực tế là giữ chưa tới hai lượt —
và đó là lý do người dùng thấy tác tử quên những thứ vừa nói ở đầu cùng một việc.
"""

from __future__ import annotations

from typing import Any

# §5.3 — kết quả không được nhắc trong 8 lượt và không ghim thì thành stub.
LUOT_GIU_NGUYEN_VAN = 8

# Loại HumanAct được ghim tự động (§5.4): chúng là Ý CHÍ của người, nén mất là làm
# ngược ý người.
GHIM_TU_DONG = {"decide", "confirm", "edit", "snapshot", "set", "choose", "undo"}


def _la_tool(m: dict[str, Any]) -> bool:
    return m.get("role") == "tool"


def _da_stub(m: dict[str, Any]) -> bool:
    return bool(m.get("_stub"))


def danh_dau_luot(messages: list[dict[str, Any]]) -> None:
    """Gắn số lượt cho từng message, để đếm theo LƯỢT chứ không theo message.

    Một lượt bắt đầu ở mỗi message `role="user"` không phải nhắc hệ thống — tức mỗi
    lần người thật sự nói hoặc mỗi lần hook Stop bơm thêm một vòng.
    """
    luot = 0
    for m in messages:
        if m.get("role") == "user" and not m.get("_he_thong"):
            luot += 1
        m.setdefault("_luot", luot)


def _stub(m: dict[str, Any], ly_do: str) -> dict[str, Any]:
    env = m.get("envelope") or {}
    dong = env.get("summary_line") or m.get("tool", "kết quả công cụ")
    ref = env.get("blob_ref")
    noi = f"({ly_do}) {dong}"
    if ref:
        noi += f" · nguyên văn: {ref} — đọc bằng blob.read"
    return {"role": "tool", "tool_call_id": m.get("tool_call_id"),
            "tool": m.get("tool"), "_stub": True, "_luot": m.get("_luot", 0),
            "result": {"ok": True, "_da_thu_gon": noi}}


def _khoa_doc(m: dict[str, Any]) -> tuple[str, Any] | None:
    """Khoá nhận diện "cùng một lần đọc": (đường dẫn, phiên bản nội dung)."""
    if m.get("tool") != "fs.read":
        return None
    d = (m.get("result") or {}).get("data")
    if not isinstance(d, dict) or not d.get("path"):
        return None
    return (str(d["path"]), d.get("bytes"))


def c1(messages: list[dict[str, Any]], *, ghim: set[int] | None = None,
       tep_da_sua: set[str] | None = None) -> dict[str, Any]:
    """Thu gọn tại chỗ. Trả về báo cáo để ghi sổ cái và để kiểm."""
    ghim = ghim or set()
    tep_da_sua = tep_da_sua or set()
    danh_dau_luot(messages)
    luot_cuoi = max((m.get("_luot", 0) for m in messages), default=0)

    bc = {"stub_qua_han": 0, "dedup": 0, "supersede": 0, "the_dong": 0,
          "truoc": sum(len(str(m)) for m in messages)}

    # --- 2. Dedup: giữ lần đọc MỚI, lần cũ thành stub.
    da_thay: dict[tuple[str, Any], int] = {}
    for i, m in enumerate(messages):
        k = _khoa_doc(m)
        if k is None or _da_stub(m):
            continue
        if k in da_thay:
            j = da_thay[k]
            if j not in ghim:
                messages[j] = _stub(messages[j], f"đã đọc lại ở #{i}, nội dung không đổi")
                bc["dedup"] += 1
        da_thay[k] = i

    # --- 3. Supersede: tệp đã bị sửa ⇒ kết quả đọc bản cũ không còn đúng.
    for i, m in enumerate(messages):
        if i in ghim or _da_stub(m):
            continue
        k = _khoa_doc(m)
        if k and k[0] in tep_da_sua:
            messages[i] = _stub(m, "bản này đã cũ — tệp đã được sửa sau đó")
            bc["supersede"] += 1

    # --- 1. Quá hạn 8 lượt.
    for i, m in enumerate(messages):
        if i in ghim or not _la_tool(m) or _da_stub(m):
            continue
        if luot_cuoi - m.get("_luot", 0) >= LUOT_GIU_NGUYEN_VAN:
            messages[i] = _stub(m, f"quá {LUOT_GIU_NGUYEN_VAN} lượt, chưa được nhắc lại")
            bc["stub_qua_han"] += 1

    # --- 4. Thẻ đã đóng: giữ tiêu đề + câu trả lời, bỏ danh sách lựa chọn.
    for i, m in enumerate(messages):
        if i in ghim or m.get("role") != "user":
            continue
        t = m.get("text") or ""
        if "→ Duyệt" in t and len(t) > 400:
            dau = t.split("\n", 1)[0]
            messages[i] = {**m, "text": dau + "\n(thẻ đã đóng — lựa chọn đã bỏ khỏi ngữ cảnh)"}
            bc["the_dong"] += 1

    bc["sau"] = sum(len(str(m)) for m in messages)
    bc["giam_phan_tram"] = (round(100 * (1 - bc["sau"] / bc["truoc"]), 1)
                            if bc["truoc"] else 0.0)
    return bc


def chi_so_ghim(messages: list[dict[str, Any]]) -> set[int]:
    """§5.4 — message nào không bao giờ bị nén.

    Ghim theo **ý chí của người**, không theo độ dài hay độ mới. Một câu người gõ ba
    mươi lượt trước vẫn ràng buộc hơn một kết quả tool của lượt vừa xong.
    """
    ra: set[int] = set()
    for i, m in enumerate(messages):
        if m.get("_ghim"):
            ra.add(i)
            continue
        if m.get("role") == "user" and m.get("_kind") in GHIM_TU_DONG:
            ra.add(i)
    return ra
