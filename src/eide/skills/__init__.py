# -*- coding: utf-8 -*-
"""SKILL — hướng dẫn viết sẵn cho một loại việc, nạp theo ngữ cảnh (§B5).

Vì sao skill nằm trong tệp chứ không nằm trong hiến pháp: hiến pháp có trần 3.600 token và
phải đúng cho MỌI việc. "Cách viết ISR trên AVR" chỉ đúng khi đang viết ISR trên AVR, và
nhét nó vào hiến pháp là bắt mọi lượt trả tiền cho một hướng dẫn mà phần lớn lượt không dùng.

Mỗi skill là một tệp Markdown có đầu đề ba dòng:

    # <tên>
    khi_nao: <một câu — lúc nào thì nạp cái này>
    ...nội dung...
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

THU_MUC = Path(__file__).parent


def _doc_dau_de(chu: str) -> tuple[str, str, list[str]]:
    ten = ""
    khi_nao = ""
    tu_khoa: list[str] = []
    for d in chu.splitlines()[:8]:
        if d.startswith("# ") and not ten:
            ten = d[2:].strip()
        m = re.match(r"khi_nao:\s*(.+)", d.strip())
        if m:
            khi_nao = m.group(1).strip()
        m = re.match(r"tu_khoa:\s*(.+)", d.strip())
        if m:
            tu_khoa = [x.strip() for x in m.group(1).split(",") if x.strip()]
    return ten, khi_nao, tu_khoa


def tim_skill(tu_khoa: str = "") -> list[dict[str, str]]:
    """Danh sách skill, lọc theo từ khoá nếu có. Trả tóm tắt, không trả nội dung."""
    q = (tu_khoa or "").lower().strip()
    ra: list[dict[str, str]] = []
    for p in sorted(THU_MUC.glob("*.md")):
        chu = p.read_text("utf-8", errors="replace")
        ten, khi_nao, tk = _doc_dau_de(chu)
        ten = ten or p.stem
        if q and q not in (ten + " " + khi_nao + " " + " ".join(tk)
                           + " " + chu[:800]).lower():
            continue
        ra.append({"ten": ten, "khi_nao": khi_nao, "tep": p.name, "tu_khoa": tk,
                   "so_dong": str(len(chu.splitlines()))})
    return ra


def goi_y_cho_ngu_canh() -> list[dict[str, Any]]:
    """Danh sách skill ở dạng `<skills-hint>` của §B2 cần: `name`, `summary`, `keywords`.

    Gợi ý CHỈ là tên và một câu — nội dung đầy đủ nạp bằng `skill.load` khi mô hình thấy cần.
    Nhét cả nội dung vào mỗi lượt là trả tiền cho sáu hướng dẫn trong khi dùng nhiều nhất một.
    """
    return [{"name": s["ten"], "summary": s["khi_nao"], "keywords": s["tu_khoa"]}
            for s in tim_skill("")]


def doc_skill(ten: str) -> dict[str, Any] | None:
    """Nội dung đầy đủ của một skill."""
    for p in sorted(THU_MUC.glob("*.md")):
        chu = p.read_text("utf-8", errors="replace")
        t, khi_nao, tk = _doc_dau_de(chu)
        if (t or p.stem) == ten or p.stem == ten:
            return {"ten": t or p.stem, "khi_nao": khi_nao, "tu_khoa": tk,
                    "noi_dung": chu, "so_dong": len(chu.splitlines())}
    return None
