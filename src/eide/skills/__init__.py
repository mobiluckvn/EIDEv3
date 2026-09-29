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
    """Danh sách skill, lọc theo từ khoá nếu có. Trả tóm tắt, không trả nội dung.

    Khớp theo **từng chữ**, không theo cả cụm, và xếp cái khớp nhiều chữ lên trước.

    Bản đầu đòi cả cụm phải nằm nguyên trong chuỗi mô tả. Nghĩa là mọi truy vấn nhiều chữ đều
    trượt: `tim_skill("vẽ sơ đồ")` trả **rỗng** trong khi skill `trinh-bay-bang-hinh` có cả
    `sơ đồ` lẫn `vẽ` trong từ khoá — chỉ vì chúng không đứng liền nhau. Đo được 29/09/2026;
    lỗi này có từ đầu và chạm tới mọi skill, không riêng skill mới.

    Cách nói của người không bao giờ trùng khít cách viết trong tệp. Một bộ tìm đòi trùng khít
    là một bộ tìm không ai dùng được — và nó hỏng **im lặng**: trả rỗng trông y như "không có
    skill nào cho việc này".
    """
    chu_q = [x for x in re.split(r"[\s,;/]+", (tu_khoa or "").lower().strip()) if x]
    ra: list[dict[str, str]] = []
    for p in sorted(THU_MUC.glob("*.md")):
        chu = p.read_text("utf-8", errors="replace")
        ten, khi_nao, tk = _doc_dau_de(chu)
        ten = ten or p.stem
        # Từ khoá KHAI BÁO nặng hơn chữ tình cờ có trong thân bài. Không phân biệt thì
        # `tim_skill("vẽ sơ đồ")` cho `design-review-checklist` đứng trước
        # `trinh-bay-bang-hinh` — cả hai khớp hai chữ, và thứ tự quyết bởi bảng chữ cái.
        khai = (ten + " " + " ".join(tk)).lower()
        than = (khi_nao + " " + chu[:800]).lower()
        khop = sum(3 for x in chu_q if x in khai) + sum(1 for x in chu_q if x in than)
        if chu_q and khop == 0:
            continue
        ra.append({"ten": ten, "khi_nao": khi_nao, "tep": p.name, "tu_khoa": tk,
                   "so_dong": str(len(chu.splitlines())), "_khop": khop})
    ra.sort(key=lambda d: (-d.pop("_khop"), d["ten"]))
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
