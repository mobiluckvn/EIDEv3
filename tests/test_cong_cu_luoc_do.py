# -*- coding: utf-8 -*-
"""Lược đồ của MỌI công cụ phải qua nổi SDK mô hình.

Phép kiểm này có từ một lỗi làm Agent **tê liệt hoàn toàn**, đo được trong một phiên thật
ngày 11/10/2026: công cụ `screen.set` khai `{"type": "integer", "enum": [8, 12, 16, 20, 24]}`,
mà SDK của mô hình đòi mọi giá trị `enum` phải là **chuỗi**. Cả lược đồ công cụ vì thế không
serialize nổi, nên **mọi** lời gọi mô hình đổ `ValidationError`.

Hai điều làm nó đặc biệt khó chịu:

* `screen.set` là `core=False`, nên lỗi chỉ nổ **sau khi** `tool.search` mở khoá nó — ba lượt
  đầu của phiên chạy bình thường, rồi từ lượt thứ tư trở đi Agent không chạy được gì nữa;
* 2 232 ca kiểm không bắt được, vì **không ca nào** đưa lược đồ công cụ qua SDK thật.

Đây đúng hình dạng đã lặp suốt dự án: cơ chế kiểm có sẵn (SDK tự xác thực), mà không đường nào
đi tới nó trong bộ kiểm.
"""
from __future__ import annotations

import dataclasses
import os

import pytest


def _registry():
    """Registry với MỌI cờ BẬT."""
    from eide.config import Features
    cu = {x: os.environ.get("EIDE_FEATURE_" + x.upper()) for x in Features.ten_co()}
    for x in Features.ten_co():
        os.environ["EIDE_FEATURE_" + x.upper()] = "1"
    try:
        from eide.tools import build_registry
        return build_registry()
    finally:
        for x, v in cu.items():
            if v is None:
                os.environ.pop("EIDE_FEATURE_" + x.upper(), None)
            else:
                os.environ["EIDE_FEATURE_" + x.upper()] = v


def _moi_cong_cu():
    """Mọi công cụ với MỌI cờ BẬT — kể cả công cụ `core=False` chỉ hiện sau `tool.search`.

    Phải lấy cả nhóm sau cờ: một công cụ chỉ đăng ký khi bật cờ vẫn vào lược đồ của người bật
    cờ ấy, và lược đồ hỏng thì hỏng cho họ.
    """
    from eide.config import Features
    cu = {t: os.environ.get("EIDE_FEATURE_" + t.upper()) for t in Features.ten_co()}
    for t in Features.ten_co():
        os.environ["EIDE_FEATURE_" + t.upper()] = "1"
    try:
        from eide.tools import build_registry
        r = build_registry()
        return list(r.all() if hasattr(r, "all") else r.tools.values())
    finally:
        for t, v in cu.items():
            if v is None:
                os.environ.pop("EIDE_FEATURE_" + t.upper(), None)
            else:
                os.environ["EIDE_FEATURE_" + t.upper()] = v


def _di(o, duong: str, ra: list):
    if isinstance(o, dict):
        if isinstance(o.get("enum"), list):
            for v in o["enum"]:
                if not isinstance(v, str):
                    ra.append((duong, type(v).__name__, v))
        for k, v in o.items():
            _di(v, f"{duong}.{k}", ra)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            _di(v, f"{duong}[{i}]", ra)


def test_moi_gia_tri_enum_la_CHUOI():
    """Không `enum` nào được chứa số — SDK mô hình từ chối, và từ chối cả lược đồ.

    Phép kiểm này đọc thẳng lược đồ nên nó chạy trên mọi máy, kể cả máy không có SDK.
    """
    xau: list = []
    for s in _moi_cong_cu():
        _di(s.params, s.name, xau)
    assert xau == [], (
        "enum phải là chuỗi (SDK mô hình từ chối số, và nó từ chối CẢ lược đồ):\n"
        + "\n".join(f"  {d}: {t} {v!r}" for d, t, v in xau))


def test_luoc_do_qua_duoc_SDK_mo_hinh():
    """Và phép đo thật: dựng `Tool` của SDK từ lược đồ của mọi công cụ.

    Ca trên chỉ bắt được **một** loại sai (enum không phải chuỗi). Ca này bắt được mọi loại
    sai mà SDK biết — nó là phép kiểm duy nhất nói được "lược đồ này gửi đi được".
    """
    genai_types = pytest.importorskip("google.genai.types")

    # Dùng ĐÚNG đường lõi dùng (`loop.py` → `Registry.declarations()` →
    # `gemini.declarations_for`), không dựng lại khai báo ở đây: một bản dựng lại trong ca
    # kiểm có thể hợp lệ trong khi bản thật thì không, và ô xanh lúc ấy nói về ca kiểm.
    from eide.llm.gateway import declarations_for

    r = _registry()
    sp = list(r.all() if hasattr(r, "all") else r.tools.values())
    # `declarations()` chỉ trả công cụ ĐANG hiện; mở khoá HẾT để lược đồ đầy đủ như lúc
    # `tool.search` đã chạy — đó chính là lúc lỗi nổ trong phiên thật, và một ca kiểm chỉ
    # chạm tới công cụ `core=True` sẽ xanh trong khi sản phẩm tê liệt.
    r._unlocked |= {s.name for s in sp}
    decls = declarations_for(r.declarations())
    assert len(decls) >= len(sp) * 0.9, (
        f"chỉ {len(decls)} khai báo cho {len(sp)} công cụ — mở khoá chưa đủ, nên ca kiểm này "
        "sẽ không chạm tới công cụ `core=False`, đúng chỗ lỗi đã nổ")
    try:
        genai_types.Tool(function_declarations=decls)
    except Exception as e:                                   # noqa: BLE001
        pytest.fail(f"SDK từ chối lược đồ của {len(sp)} công cụ:\n{e}")
