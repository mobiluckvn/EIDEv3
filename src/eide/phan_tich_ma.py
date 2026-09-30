# -*- coding: utf-8 -*-
"""Đọc mã ĐANG CÓ rồi dựng một tài liệu phân tích — trước khi sửa nó.

## Vì sao cần, khi đã có `fs.read`

`fs.read` cho thấy **một tệp**. Sửa mã có sẵn thì câu hỏi không phải "tệp này viết gì" mà là
ba câu khác:

* Tệp này có những gì — hàm nào, kích thước ra sao?
* **Ai đang dùng nó?** Sửa một hàm mà không biết năm chỗ gọi nó thì năm chỗ ấy hỏng lặng lẽ.
* Sẽ đổi gì, và đổi xong thì chỗ nào phải xem lại?

Câu thứ hai là câu đắt nhất và là câu `fs.read` không trả lời được — nó cần quét cả cây mã.

## Chỗ nó KHÔNG làm

Không phân tích ngữ nghĩa, không dựng đồ thị gọi hàm đúng nghĩa. Nó dò **tên ký hiệu xuất
hiện ở đâu** bằng cách quét văn bản. Cách ấy có thể **kêu thừa** (tên trùng trong chú thích)
nhưng không **bỏ sót** — và với một tài liệu để người đọc trước khi sửa, kêu thừa rẻ hơn bỏ
sót nhiều lần.

Giới hạn ấy được ghi thẳng vào tài liệu sinh ra, không giấu trong mã.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ngôn ngữ nhận diện được ký hiệu. Cái gì không có ở đây thì vẫn đếm dòng và liệt kê được,
# chỉ không tách ra được hàm.
_HAM = {
    ".c": re.compile(r"^[A-Za-z_][\w \*]*\s+\**(\w+)\s*\([^;]*\)\s*\{", re.M),
    ".h": re.compile(r"^[A-Za-z_][\w \*]*\s+\**(\w+)\s*\([^;{]*\)\s*;", re.M),
    ".py": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)|^class\s+(\w+)", re.M),
    ".swift": re.compile(r"^\s*(?:public\s+|private\s+|internal\s+)?"
                         r"(?:func\s+(\w+)|struct\s+(\w+)|class\s+(\w+)|enum\s+(\w+))", re.M),
}
_HAM[".cpp"] = _HAM[".c"]
_HAM[".hpp"] = _HAM[".h"]

# Tệp không bao giờ quét: sinh ra được, hoặc không phải mã của người.
BO_QUA = (".eide", ".git", "node_modules", "__pycache__", "vendor", "build", ".venv")


@dataclass(slots=True)
class TepMa:
    duong: str
    so_dong: int = 0
    byte: int = 0
    ky_hieu: list[str] = field(default_factory=list)
    phu_thuoc: list[str] = field(default_factory=list)      # include/import thấy trong tệp
    ai_dung: dict[str, list[str]] = field(default_factory=dict)   # ký hiệu → tệp gọi nó


def _ky_hieu(p: Path, chu: str) -> list[str]:
    mau = _HAM.get(p.suffix.lower())
    if mau is None:
        return []
    ra: list[str] = []
    for m in mau.finditer(chu):
        ten = next((g for g in m.groups() if g), None)
        if ten and ten not in ra:
            ra.append(ten)
    return ra


def _phu_thuoc(chu: str) -> list[str]:
    ra = re.findall(r'^\s*#include\s+[<"]([^>"]+)[>"]', chu, re.M)
    ra += re.findall(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", chu, re.M)
    ra += re.findall(r"^\s*import\s+(\w+)\s*$", chu, re.M)
    return sorted({x for t in ra for x in ((t,) if isinstance(t, str) else t) if x})


def quet(goc: Path, tep: list[str]) -> list[TepMa]:
    """Đọc từng tệp, rồi tìm AI ĐANG DÙNG ký hiệu của nó trong cả cây mã."""
    ra: list[TepMa] = []
    for t in tep:
        p = (goc / t).resolve()
        if not p.is_file():
            ra.append(TepMa(duong=t, so_dong=-1))
            continue
        chu = p.read_text("utf-8", errors="replace")
        ra.append(TepMa(duong=t, so_dong=len(chu.splitlines()), byte=p.stat().st_size,
                        ky_hieu=_ky_hieu(p, chu), phu_thuoc=_phu_thuoc(chu)))

    # Quét ngược: ký hiệu của những tệp trên xuất hiện ở tệp nào khác.
    can = {k: tm for tm in ra for k in tm.ky_hieu}
    if not can:
        return ra
    for q in sorted(goc.rglob("*")):
        if not q.is_file() or q.suffix.lower() not in _HAM:
            continue
        if any(b in q.parts for b in BO_QUA):
            continue
        rel = str(q.relative_to(goc))
        if rel in tep:
            continue
        try:
            chu = q.read_text("utf-8", errors="replace")
        except OSError:
            continue
        for k, tm in can.items():
            if re.search(r"\b" + re.escape(k) + r"\b", chu):
                tm.ai_dung.setdefault(k, []).append(rel)
    return ra


def dung_tai_lieu(goc: Path, tm: list[TepMa], doi_gi: str, vi_sao: str) -> str:
    """Tài liệu Markdown — thứ người đọc TRƯỚC khi duyệt cho sửa."""
    L = ["# Phân tích mã trước khi sửa", "",
         f"**Sẽ đổi gì:** {doi_gi.strip()}", "",
         f"**Vì sao:** {vi_sao.strip()}", "",
         "## Tệp trong phạm vi", "",
         "| Tệp | Dòng | Ký hiệu | Phụ thuộc |", "|---|---|---|---|"]
    for t in tm:
        if t.so_dong < 0:
            L.append(f"| `{t.duong}` | — | **không có tệp này** | — |")
            continue
        L.append(f"| `{t.duong}` | {t.so_dong} | "
                 + (", ".join(f"`{k}`" for k in t.ky_hieu[:8]) or "—")
                 + (f" …+{len(t.ky_hieu) - 8}" if len(t.ky_hieu) > 8 else "") + " | "
                 + (", ".join(f"`{d}`" for d in t.phu_thuoc[:5]) or "—") + " |")

    L += ["", "## Ai đang dùng — chỗ phải xem lại sau khi sửa", ""]
    co = False
    for t in tm:
        for k, ds in sorted(t.ai_dung.items()):
            co = True
            L.append(f"* `{k}` (trong `{t.duong}`) → " + ", ".join(f"`{x}`" for x in ds[:8])
                     + (f" …+{len(ds) - 8}" if len(ds) > 8 else ""))
    if not co:
        L.append("* Không tệp nào khác nhắc tới ký hiệu của các tệp trên. "
                 "**Đọc kỹ dòng này**: nó có thể nghĩa là phạm vi sửa gọn, "
                 "hoặc nghĩa là phép dò chưa nhìn tới chỗ cần nhìn.")

    L += ["", "## Giới hạn của phép dò này", "",
          "Đây là dò **tên ký hiệu trong văn bản**, không phải đồ thị gọi hàm. Nó có thể kêu "
          "thừa (tên trùng nằm trong chú thích hay chuỗi) nhưng không bỏ sót chỗ gọi thẳng. "
          "Gọi gián tiếp qua con trỏ hàm, macro nối chuỗi, hay phản chiếu thì nó **không thấy** "
          "— chỗ nào nghi thì đọc bằng mắt.", ""]
    return "\n".join(L)
