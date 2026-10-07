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
# Danh sách tham số của MỘT hàm: không vượt `{`/`}`/`;`, và cho phép đúng một lớp ngoặc
# lồng (con trỏ hàm: `void f(void (*cb)(int))`).
#
# Bản đầu viết `[^;]*`, và nó THAM LAM: một hàm thân rỗng không có dấu `;` nào, nên mẫu
# vượt qua nó và nuốt luôn các hàm phía sau. Đo được: ba hàm thân rỗng liền nhau thì chỉ
# hàm đầu được thấy — hai hàm kia biến mất khỏi tài liệu mà không ai biết.
_THAM_SO = r"\([^;{}()]*(?:\([^;{}()]*\)[^;{}()]*)*\)"

_HAM = {
    ".c": re.compile(r"^[A-Za-z_][\w \*]*\s+\**(\w+)\s*" + _THAM_SO + r"\s*\{", re.M),
    ".h": re.compile(r"^[A-Za-z_][\w \*]*\s+\**(\w+)\s*\([^;{]*\)\s*;", re.M),
    ".py": re.compile(r"^\s*(?:async\s+)?def\s+(\w+)|^class\s+(\w+)", re.M),
    ".swift": re.compile(r"^\s*(?:public\s+|private\s+|internal\s+)?"
                         r"(?:func\s+(\w+)|struct\s+(\w+)|class\s+(\w+)|enum\s+(\w+))", re.M),
}
_HAM[".cpp"] = _HAM[".c"]
_HAM[".hpp"] = _HAM[".h"]

# NGẮT. Ba cách viết, và không cách nào khớp mẫu hàm thường ở trên vì hai cách đầu không có
# kiểu trả về đứng trước tên.
#
# Vì sao đáng một mẫu riêng: ngắt là chỗ đắt nhất để bỏ sót. Nó chạy ngoài luồng chính, nó
# chạm biến chia sẻ, và một lỗi đồng bộ ở đó không bao giờ tái hiện được bằng cách đọc luồng
# chính. Đo trên firmware robot: `timer.c` có hai ngắt, `uart.c` có một — cả ba vắng mặt
# trong tài liệu phân tích suốt thời gian qua.
_ISR_MACRO = re.compile(r"^\s*ISR\s*\(\s*(\w+)", re.M)          # AVR: ISR(TIMER0_COMPA_vect)
_ISR_ATTR = re.compile(r"__attribute__\s*\(\(\s*(?:interrupt|signal)[^)]*\)\)"
                       r"\s*(?:[\w \*]+\s+)?(\w+)\s*\(")
_TEN_ISR = re.compile(r"^\w+_(?:IRQ)?Handler$")                   # ARM: TIM2_IRQHandler

_DUOI_C = (".c", ".cpp", ".h", ".hpp")


def _la_ten_isr(ten: str) -> bool:
    return bool(_TEN_ISR.match(ten))


def _tim_ky_hieu(p: Path, chu: str) -> list[tuple[int, str, str]]:
    """(vị trí, tên, loại) cho mọi ký hiệu thấy được. Giữ THỨ TỰ xuất hiện trong tệp.

    Gộp nhiều mẫu rồi sắp theo vị trí, chứ không nối đuôi nhau: thứ tự trong tài liệu phải
    là thứ tự người đọc thấy khi mở tệp ra, không phải thứ tự các mẫu regex chạy.
    """
    ra: list[tuple[int, str, str]] = []
    mau = _HAM.get(p.suffix.lower())
    if mau is not None:
        for m in mau.finditer(chu):
            ten = next((g for g in m.groups() if g), None)
            if not ten:
                continue
            dong = chu[m.start():m.start(1)]
            loai = ("isr" if _la_ten_isr(ten)
                    else "static" if re.match(r"^\s*static\b", dong) else "ham")
            ra.append((m.start(1), ten, loai))
    if p.suffix.lower() in _DUOI_C:
        for mau_isr in (_ISR_MACRO, _ISR_ATTR):
            for m in mau_isr.finditer(chu):
                ra.append((m.start(1), m.group(1), "isr"))
    ra.sort(key=lambda x: x[0])
    # Một tên có thể khớp hai mẫu (ví dụ `__attribute__((interrupt)) SysTick_Handler`):
    # giữ lần đầu, và để loại "isr" thắng nếu bất kỳ mẫu nào nói nó là ngắt.
    thay: dict[str, str] = {}
    thu_tu: list[str] = []
    for _, ten, loai in ra:
        if ten not in thay:
            thay[ten] = loai
            thu_tu.append(ten)
        elif loai == "isr":
            thay[ten] = "isr"
    return [(i, ten, thay[ten]) for i, ten in enumerate(thu_tu)]


def phan_loai(p: Path, chu: str) -> dict[str, str]:
    """Tên ký hiệu → `"ham"` | `"isr"` | `"static"`.

    Tách khỏi `_ky_hieu` thay vì đổi kiểu trả về của nó: `TepMa.ky_hieu` là `list[str]` và
    `ai_dung` dùng nó làm khoá (xem `tools/xay_dung.py` `code_analyze`). Đổi kiểu ở đó là
    đổi hợp đồng của `code.analyze` — việc này chỉ cần THÊM một cái nhìn, không cần đổi cái
    đang có.
    """
    return {ten: loai for _, ten, loai in _tim_ky_hieu(p, chu)}

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
    # M2-08 — ngắt tách riêng khỏi `ky_hieu` (vẫn nằm trong `ky_hieu`, chỉ thêm một cái
    # nhìn). Người đọc tài liệu trước khi sửa cần thấy NGAY tệp này có chạy ngoài luồng
    # chính hay không: ngắt chạm biến chia sẻ, và lỗi đồng bộ ở đó không tái hiện được
    # bằng cách đọc luồng chính.
    isr: list[str] = field(default_factory=list)


def _ky_hieu(p: Path, chu: str) -> list[str]:
    """Tên ký hiệu, theo thứ tự xuất hiện. Kiểu trả về giữ nguyên `list[str]` (M2-08)."""
    return [ten for _, ten, _ in _tim_ky_hieu(p, chu)]


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
        pl = phan_loai(p, chu)
        ra.append(TepMa(duong=t, so_dong=len(chu.splitlines()), byte=p.stat().st_size,
                        ky_hieu=list(pl), phu_thuoc=_phu_thuoc(chu),
                        isr=[k for k, v in pl.items() if v == "isr"]))

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
         "| Tệp | Dòng | Ký hiệu | Ngắt (ISR) | Phụ thuộc |", "|---|---|---|---|---|"]
    for t in tm:
        if t.so_dong < 0:
            L.append(f"| `{t.duong}` | — | **không có tệp này** | — | — |")
            continue
        L.append(f"| `{t.duong}` | {t.so_dong} | "
                 + (", ".join(f"`{k}`" for k in t.ky_hieu[:8]) or "—")
                 + (f" …+{len(t.ky_hieu) - 8}" if len(t.ky_hieu) > 8 else "") + " | "
                 + (", ".join(f"`{k}`" for k in t.isr) or "—") + " | "
                 + (", ".join(f"`{d}`" for d in t.phu_thuoc[:5]) or "—") + " |")

    # Có ngắt thì nói thành một câu, không chỉ một ô trong bảng: đây là thứ đổi cách người
    # ta đọc cả phần còn lại của tài liệu.
    co_isr = [(t.duong, k) for t in tm for k in t.isr]
    if co_isr:
        L += ["", f"**Có {len(co_isr)} ngắt (ISR) trong phạm vi sửa:** "
                  + ", ".join(f"`{k}` (`{d}`)" for d, k in co_isr) + ".",
              "", "Ngắt chạy NGOÀI luồng chính. Biến nào vừa bị ngắt ghi vừa bị luồng chính "
              "đọc thì phải `volatile`, và đoạn đọc nhiều byte phải chặn ngắt — một lỗi đồng "
              "bộ ở đây không tái hiện được bằng cách đọc luồng chính, nên nó không lộ ra "
              "trong lúc thử."]

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
