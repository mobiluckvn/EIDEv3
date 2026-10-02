# -*- coding: utf-8 -*-
"""Từ Markdown tác tử viết ra → `.docx` / `.xlsx` / `.pdf`.

## Vì sao nguồn là Markdown chứ không ghi thẳng nhị phân

Đo ngày 29/09/2026: trong toàn bộ `src/eide/tools/` **không một công cụ nào ghi byte** —
`fs.write` gọi `write_text`, nên `.docx` (vốn là một tệp ZIP) không có đường nào ra. Cách sửa
nhanh nhất là cho tác tử ghi thẳng nhị phân. Không chọn, vì hai lẽ:

* **Một thay đổi không xem được là một thay đổi không duyệt được.** Sổ cái giữ được nhị phân
  và hoàn tác được nó, nhưng người duyệt sẽ thấy "12 KB đổi thành 13 KB". Nguồn Markdown thì
  `history.py` cho ra diff đọc bằng mắt — đúng thứ G-FILE dựng ra để bảo vệ.
* **Phân hạng đã có sẵn chỗ cho việc này.** `du_an.py` chia dữ liệu thành `ben` /
  `dung_lai_duoc` / `tam`. Nguồn là `ben`; bản `.docx` render ra là `dung_lai_duoc` — dựng lại
  được từ nguồn bất cứ lúc nào, nên gói mang đi không phải cõng theo.

Đổi lại, tác tử phải sửa tài liệu ở **nguồn** rồi render lại, chứ không sửa trong Word. Đó là
cái giá, và nó nói ra ở đây để không ai ngạc nhiên.

## Hai chỗ tệp này cố ý TỪ CHỐI

1. **Excel từ văn xuôi.** Không bảng thì `sang_xlsx` báo lỗi chứ không đổ cả đoạn văn vào ô
   `A1`. Một tệp `.xlsx` mở lên được nhưng vô dụng **trông giống thành công** — và thứ trông
   giống thành công thì đắt hơn hẳn một lỗi nói thẳng.
2. **PDF khi máy không có LibreOffice.** Báo thiếu, kèm cách khác. Không tự vẽ một PDF thô sơ
   để "có tệp": người nhận sẽ tưởng đó là bản in được.

## Và một chỗ nó bắt buộc phải làm

Render xong thì **mở lại tệp vừa tạo** và đếm — bao nhiêu đoạn, bao nhiêu hàng, bao nhiêu
trang. Báo con số ấy, không báo "đã ghi xong 12 KB".

Bài học cũ của dự án này: *`ok` nói về lời gọi, không nói về kết quả.* Một lời gọi
`python-docx` không ném ngoại lệ mới chỉ chứng minh thư viện chạy; nó chưa chứng minh trong
tệp có chữ.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DINH_DANG = ("docx", "xlsx", "pdf", "pptx")

# Ảnh chèn vào tài liệu rộng tối đa ngần này (inch) — vừa khổ A4 lề 2,5 cm.
RONG_ANH_TOI_DA = 6.0


# ============================================================================ mô hình khối
@dataclass(slots=True)
class Khoi:
    """Một khối Markdown đã đọc xong. `loai` quyết định các trường nào có nghĩa."""

    loai: str                       # tieu_de | doan | gach_dau | so_thu_tu | bang | ma | anh
                                    # | ngan | trich | so_do | cong_thuc
    chu: str = ""
    muc: int = 0                    # bậc tiêu đề, hoặc bậc thụt của gạch đầu dòng
    hang: list[list[str]] = field(default_factory=list)   # bảng: hàng đầu là tiêu đề cột
    ngon_ngu: str = ""              # khối mã


@dataclass(slots=True)
class KetQuaRender:
    tep: Path | None = None
    dinh_dang: str = ""
    do_lai: dict[str, Any] = field(default_factory=dict)
    vi_sao_khong_dat: str = ""

    @property
    def dat(self) -> bool:
        return self.tep is not None and not self.vi_sao_khong_dat

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "tep": str(self.tep) if self.tep else None,
                "dinh_dang": self.dinh_dang, "do_lai": self.do_lai,
                "vi_sao_khong_dat": self.vi_sao_khong_dat}


# ============================================================================ đọc Markdown
_TIEU_DE = re.compile(r"^(#{1,6})\s+(.*)$")
_GACH = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_SO = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_ANH = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
_NGAN = re.compile(r"^\s*([-*_])\1{2,}\s*$")
_HANG_BANG = re.compile(r"^\s*\|(.+)\|\s*$")
_KE_BANG = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


def _o_bang(dong: str) -> list[str]:
    return [o.strip() for o in dong.strip().strip("|").split("|")]


def doc_markdown(md: str) -> list[Khoi]:
    """Markdown → danh sách khối.

    Cố ý nhận một TẬP CON: tiêu đề, đoạn, gạch đầu dòng, danh sách số, bảng, khối mã, ảnh,
    đường ngăn, trích dẫn. Không nhận HTML nhúng, chú thích chân trang, danh sách lồng sâu.

    Nhận tập con là một lựa chọn, không phải một thiếu sót: một trình đọc Markdown đầy đủ là
    một thứ nữa phải bảo trì, còn tập con này đã phủ hết những gì một tài liệu kỹ thuật cần và
    **hỏng ở đâu thì nhìn ra ngay ở đó**.
    """
    khoi: list[Khoi] = []
    dong = md.replace("\r\n", "\n").split("\n")
    i, n = 0, len(dong)
    dem_doan: list[str] = []
    # Mục danh sách / trích dẫn đang mở, để nuốt DÒNG NỐI TIẾP.
    #
    # Markdown cho phép viết một mục dài thành nhiều dòng liền nhau, không thụt. Bản đầu đọc
    # dòng thứ hai thành một đoạn mới — và bản in ra giấy vỡ mục làm đôi, tệ hơn là dấu `**`
    # bị cắt giữa hai dòng nên **in nguyên ra giấy**. Đo được bằng cách nhìn trang PDF, không
    # bằng con số nào: số đoạn vẫn "hợp lý", chỉ có mắt mới thấy sai.
    dang_mo: Khoi | None = None

    def xa_doan() -> None:
        if dem_doan:
            chu = " ".join(x.strip() for x in dem_doan).strip()
            # Đoạn chỉ có một công thức `$$…$$` là công thức TRÌNH BÀY — căn giữa, đứng riêng.
            # Nhận ra ở đây, một lần, để Word và PowerPoint cùng dùng; trước đây phép nhận
            # này nằm trong bộ dựng Word nên PowerPoint in cả dấu đô-la ra slide.
            if chu.startswith("$$") and chu.endswith("$$") and len(chu) > 4 \
                    and "$$" not in chu[2:-2]:
                khoi.append(Khoi("cong_thuc", chu[2:-2].strip()))
            else:
                khoi.append(Khoi("doan", chu))
            dem_doan.clear()

    while i < n:
        d = dong[i]

        if d.strip().startswith("```"):
            xa_doan()
            ng = d.strip()[3:].strip()
            i += 1
            than: list[str] = []
            while i < n and not dong[i].strip().startswith("```"):
                than.append(dong[i])
                i += 1
            i += 1                                   # bỏ hàng rào đóng
            # `mermaid` là SƠ ĐỒ, không phải mã để đọc. Trước đây nó in nguyên cú pháp vào
            # giữa trang Word — đúng thứ người nhận không đọc được, và đúng chỗ người ta
            # chờ một hình.
            # ```math / ```latex / ```tex là CÔNG THỨC, không phải mã để đọc — cùng lý do với
            # ```mermaid. Trước đây `\tau = R \cdot C` in ra dưới dạng khối mã đẳng khoảng,
            # nguyên cú pháp TeX.
            loai = ("so_do" if ng.lower() == "mermaid"
                    else "cong_thuc" if ng.lower() in ("math", "latex", "tex")
                    else "ma")
            khoi.append(Khoi(loai, "\n".join(than), ngon_ngu=ng))
            dang_mo = None
            continue

        if not d.strip():
            xa_doan()
            dang_mo = None
            i += 1
            continue

        if _NGAN.match(d):
            xa_doan()
            khoi.append(Khoi("ngan"))
            dang_mo = None
            i += 1
            continue

        m = _TIEU_DE.match(d)
        if m:
            xa_doan()
            khoi.append(Khoi("tieu_de", m.group(2).strip(), muc=len(m.group(1))))
            dang_mo = None
            i += 1
            continue

        m = _ANH.match(d.strip())
        if m:
            xa_doan()
            # Chú thích ảnh đi nhờ ô `ngon_ngu` — ô ấy chỉ có nghĩa với khối mã.
            khoi.append(Khoi("anh", m.group(2).strip(), ngon_ngu=m.group(1)))
            dang_mo = None
            i += 1
            continue

        # Bảng: một hàng `| … |` NGAY SAU đó là hàng kẻ `|---|---|`. Đòi hỏi hàng kẻ để một
        # đoạn văn có dấu `|` không bị đọc nhầm thành bảng.
        if _HANG_BANG.match(d) and i + 1 < n and _KE_BANG.match(dong[i + 1]):
            xa_doan()
            hang = [_o_bang(d)]
            i += 2
            while i < n and _HANG_BANG.match(dong[i]):
                hang.append(_o_bang(dong[i]))
                i += 1
            khoi.append(Khoi("bang", hang=hang))
            dang_mo = None
            continue

        m = _GACH.match(d)
        if m:
            xa_doan()
            khoi.append(Khoi("gach_dau", m.group(2).strip(), muc=len(m.group(1)) // 2))
            dang_mo = khoi[-1]
            i += 1
            continue

        m = _SO.match(d)
        if m:
            xa_doan()
            khoi.append(Khoi("so_thu_tu", m.group(2).strip(), muc=len(m.group(1)) // 2))
            dang_mo = khoi[-1]
            i += 1
            continue

        if d.lstrip().startswith(">"):
            xa_doan()
            # Gộp các dòng `>` LIỀN NHAU thành MỘT khối trích dẫn.
            #
            # Tách mỗi dòng thành một khối thì bản Word ra ba đoạn trích dẫn rời, mỗi đoạn một
            # khung — đo được ở mục 5 của báo cáo RTOS: một lời ghi chú ba dòng hiện ra như ba
            # lời ghi chú khác nhau.
            nd = [d.lstrip()[1:].strip()]
            i += 1
            while i < n and dong[i].lstrip().startswith(">"):
                nd.append(dong[i].lstrip()[1:].strip())
                i += 1
            khoi.append(Khoi("trich", " ".join(x for x in nd if x).strip()))
            dang_mo = khoi[-1]
            continue

        if dang_mo is not None:                   # dòng nối tiếp của mục đang mở
            dang_mo.chu = (dang_mo.chu + " " + d.strip()).strip()
        else:
            dem_doan.append(d)
        i += 1

    xa_doan()
    return khoi


# Công thức `$$…$$` — đổi cú pháp TeX hay gặp sang ký hiệu Unicode.
#
# Không phải một bộ dựng TeX, và không giả vờ là: chỉ đổi những lệnh xuất hiện thật trong tài
# liệu tác tử viết. Trước đây một dòng `$$\text{PLLM} = 8, \quad \frac{8}{2}$$` in nguyên
# cú pháp vào giữa trang PDF — người đọc thấy mã chứ không thấy công thức.
# Thứ tự có nghĩa: gỡ `\text{…}` TRƯỚC `\frac{…}{…}`. Ngược lại thì `\frac{8\text{ MHz}}{8}`
# không khớp — mẫu của `\frac` không nhận ngoặc lồng, nên nó bỏ qua và cú pháp TeX lọt ra
# trang giấy. Đo trên chính tài liệu kiến trúc: một phân số giữ nguyên `\frac{...}{...}`.
# Một "hạng" của công thức: một lệnh TeX, một số, một tên, hoặc một ký tự lẻ.
#
# Số tách riêng khỏi tên đứng sau nó, vì trong TeX `2R` nghĩa là `2·R` — gộp chúng làm một
# hạng thì `\frac{1}{2R}` ra `1/2R`, mà `1/2R` đọc thành `(1/2)·R`. Tên thì cho phép chứa chữ
# số ở giữa (`R2`, `f_VCO`), chỉ không cho **bắt đầu** bằng chữ số.
_HANG = re.compile(r"\\[A-Za-z]+|\d+(?:[.,]\d+)?|[A-Za-z_][A-Za-z0-9_.]*|\S")


def _mot_hang(x: str) -> bool:
    """Vế này có đúng một hạng không — tức bỏ ngoặc đi cũng không đổi nghĩa."""
    return len(_HANG.findall(x)) == 1


def _boc(x: str) -> str:
    x = x.strip()
    return x if _mot_hang(x) else f"({x})"


def _phan_so(tu: str, mau: str) -> str:
    """`\\frac{a}{b}` → `a/b`; chỉ đóng ngoặc khi vế đó THẬT SỰ cần.

    Đóng ngoặc vô điều kiện cho ra `(1)/(1000)` — đúng nhưng đọc vướng, và trên một trang đầy
    công thức thì cái vướng ấy cộng dồn.

    Nhưng đếm theo *ký tự phép toán* thì hỏng: `\\frac{1}{2\\pi\\tau}` không có dấu cộng hay
    khoảng trắng nào, nên ra `1/2πτ` — mà `1/2πτ` **đọc thành `(1/2)·π·τ`**, sai nghĩa hẳn.
    Thấy trên trang PDF, không con số nào của bộ kiểm kêu.

    Nên đếm theo **hạng**: một lệnh TeX, một tên, hay một số là một hạng. Nhiều hơn một hạng
    thì đóng ngoặc.
    """
    return f"{_boc(tu)}/{_boc(mau)}"


_TEX = (
    (re.compile(r"\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}"), r"\1"),
    # Độ là ký hiệu HẬU TỐ, không phải số mũ: `2^{\circ}` phải ra `2°`, không phải `2^°`.
    # Đổi trước mọi luật mũ, nếu không thì `^{…}` biến nó thành `^\circ` rồi thành `^°`.
    (re.compile(r"\^\s*\{?\s*\\(?:circ|degree)\s*\}?"), "°"),
    (re.compile(r"\\sqrt\{([^{}]*)\}"), lambda m: "√" + _boc(m[1])),
    (re.compile(r"\\frac\{([^{}]*)\}\{([^{}]*)\}"), lambda m: _phan_so(m[1], m[2])),
    (re.compile(r"\\(?:quad|qquad|,|;|!)"), " "),
    # `\left(` / `\right]` là lệnh chỉnh cỡ ngoặc — bỏ đi là đúng. Nhưng không có
    # `(?![A-Za-z])` thì nó ăn luôn đầu của `\leftrightarrow` và `\leftarrow`, để lại
    # `rightarrow` nằm giữa công thức. Bắt được bằng ca kiểm phủ CẢ BẢNG ký hiệu, không
    # phải bằng ca thử một lệnh.
    (re.compile(r"\\(?:left|right)(?![A-Za-z])"), ""),
    (re.compile(r"_\{([^{}]*)\}"), r"_\1"),
    (re.compile(r"\^\{([^{}]*)\}"), r"^\1"),
)
_TEX_KY_HIEU = {
    # phép toán và so sánh
    r"\times": "×", r"\cdot": "·", r"\div": "÷", r"\pm": "±", r"\mp": "∓",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥", r"\neq": "≠", r"\ne": "≠",
    r"\approx": "≈", r"\equiv": "≡", r"\sim": "∼", r"\propto": "∝",
    r"\ll": "≪", r"\gg": "≫", r"\ast": "∗",
    # mũi tên
    r"\implies": "⇒", r"\Rightarrow": "⇒", r"\Leftarrow": "⇐", r"\iff": "⇔",
    r"\Leftrightarrow": "⇔", r"\leftrightarrow": "↔",
    r"\rightarrow": "→", r"\to": "→", r"\leftarrow": "←", r"\mapsto": "↦",
    # tập hợp và logic
    r"\in": "∈", r"\notin": "∉", r"\subset": "⊂", r"\subseteq": "⊆",
    r"\cup": "∪", r"\cap": "∩", r"\emptyset": "∅", r"\varnothing": "∅",
    r"\forall": "∀", r"\exists": "∃", r"\land": "∧", r"\lor": "∨", r"\neg": "¬",
    # giải tích
    r"\infty": "∞", r"\sum": "∑", r"\prod": "∏", r"\int": "∫",
    r"\partial": "∂", r"\nabla": "∇", r"\sqrt": "√",
    # chữ Hy Lạp — đủ bộ, vì thiếu một chữ là một công thức in ra cú pháp thô
    r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\Gamma": "Γ",
    r"\delta": "δ", r"\Delta": "Δ", r"\epsilon": "ε", r"\varepsilon": "ε",
    r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ", r"\Theta": "Θ",
    r"\iota": "ι", r"\kappa": "κ", r"\lambda": "λ", r"\Lambda": "Λ",
    r"\mu": "µ", r"\nu": "ν", r"\xi": "ξ", r"\Xi": "Ξ",
    r"\pi": "π", r"\Pi": "Π", r"\rho": "ρ", r"\sigma": "σ", r"\Sigma": "Σ",
    r"\tau": "τ", r"\upsilon": "υ", r"\phi": "φ", r"\varphi": "φ", r"\Phi": "Φ",
    r"\chi": "χ", r"\psi": "ψ", r"\Psi": "Ψ", r"\omega": "ω", r"\Omega": "Ω",
    # linh tinh hay gặp trong tài liệu kỹ thuật
    r"\ldots": "…", r"\dots": "…", r"\cdots": "⋯", r"\angle": "∠",
    r"\degree": "°", r"\circ": "°", r"\prime": "′", r"\percent": "%",
    r"\perp": "⊥", r"\parallel": "∥", r"\star": "⋆",
    r"\uparrow": "↑", r"\downarrow": "↓", r"\ohm": "Ω", r"\micro": "µ",
    # Lệnh BỐ CỤC — không có ký hiệu nào tương ứng, nên bỏ đi.
    #
    # Mười ba mục dưới đây vốn chỉ có ở bảng phía Swift. Thiếu chúng ở đây thì một công thức
    # viết `\left( \frac{a}{b} \right)` in ra tệp Word thành `\left( a/b \right)` — ký hiệu
    # đổi đúng mà hai lệnh bố cục còn nằm đó, và chúng là thứ đập vào mắt nhất.
    #
    # Hai bảng nay GIỐNG NHAU từng mục, và ca kiểm `test_hai_bang_ky_hieu_phai_giong_nhau`
    # đọc thẳng tệp Swift để canh. Xem DEV-325.
    r"\left": "", r"\right": "", r"\displaystyle": "", r"\limits": "",
    # `\quad` và `\qquad` đáng ra là khoảng rộng khác nhau, nhưng ở đây cả hai thành
    # MỘT dấu cách — và nói ra chứ không giấu. Hàm này kết thúc bằng
    # `re.sub(r"\s+", " ")`, nên mọi khoảng nhiều hơn một dấu cách đều co lại; ánh xạ
    # chúng thành hai hay bốn dấu cách chỉ tạo ra một lời hứa mà bước sau xoá đi. Ca
    # kiểm phủ cả bảng (`test_MOI_lenh_trong_bang_doi_dung_mot_minh_no`) bắt đúng chỗ
    # này ngày 02/10/2026, lúc tôi vừa thêm hai mục ấy vào bảng.
    r"\quad": " ", r"\qquad": " ",
    r"\,": " ", r"\;": " ", r"\:": " ", r"\!": "", r"\ ": " ",
}

# Một lượt duyệt cho cả bảng. Hai thuộc tính giữ cho `\le` không ăn mất `\leq`:
#
#   * nhánh alternation xếp **dài trước ngắn**, nên Python thử `\leq` trước và thắng;
#   * `(?![A-Za-z])` từ chối khớp khi còn chữ cái đằng sau.
#
# Hai cái này **thừa nhau** — đo rồi: bỏ riêng cái nào bộ kiểm cũng không đỏ, bỏ cả hai mới
# đỏ. Nói ra chứ không giấu, vì bản trước có tận BA chốt như vậy nằm rải ra (kể cả thứ tự
# khai trong bảng, một chốt vô hình) và không ai biết cái nào đang thật sự làm việc. Nay cả
# hai nằm trong một biểu thức, đọc một chỗ là thấy hết.
#
# Thứ **đo được** thì nằm ở chỗ khác: ca kiểm phủ CẢ BẢNG. Chính nó bắt được `\leftrightarrow`
# bị luật xoá `\left` ăn mất đầu — một lỗi không chốt nào ở đây chạm tới.
#
# HAI NHÓM, không một nhóm. Chốt `(?![A-Za-z])` chỉ đúng với lệnh viết bằng CHỮ.
#
# Với `\left`, chốt ấy là thứ phải có: `\leftb` không phải lệnh `\left` theo sau một chữ `b`,
# nó là một lệnh khác. Nhưng với lệnh dạng DẤU CÂU — `\,` `\;` `\:` `\!` `\ ` — tên lệnh kết
# thúc ngay ở dấu ấy, nên một chữ đứng sau là cách dùng hoàn toàn thường: `a\,b`. Gộp chúng
# vào cùng một chốt thì `a\:b` và `a\ b` **không đổi được**, và công thức in ra còn nguyên
# gạch chéo.
#
# Lệch này nằm im cho tới 02/10/2026, lúc mười ba lệnh bố cục được thêm vào bảng và ca kiểm
# phủ cả bảng thử từng lệnh TRONG NGỮ CẢNH. Trước đó bảng không có lệnh dấu câu nào, nên một
# chốt là đủ và không ai thấy thiếu.
def _nhanh(ds: list[str]) -> str:
    return "|".join(sorted((re.escape(k) for k in ds), key=len, reverse=True))


_LENH_CHU = [k for k in _TEX_KY_HIEU if k[1:2].isalpha()]
_LENH_DAU = [k for k in _TEX_KY_HIEU if not k[1:2].isalpha()]

_MOT_LUOT = re.compile(
    "(?:(?:" + _nhanh(_LENH_CHU) + r")(?![A-Za-z])"
    + "|(?:" + _nhanh(_LENH_DAU) + "))")

# Ký tự TeX thoát bằng gạch chéo — `\%` là dấu phần trăm, không phải một lệnh.
# Đổi SAU cùng, nếu không thì `\%` bị bảng ký hiệu trên nhìn thành lệnh `\p…`.
_TEX_THOAT = re.compile(r"\\([%&#_${}])")

# Lệnh TeX còn sót sau khi đổi hết — dùng để ĐẾM, không để xoá.
_TEX_CON_SOT = re.compile(r"\\[A-Za-z]+")


def cong_thuc_nguoi_doc(s: str) -> str:
    """`$$…$$` → một dòng người đọc được. Đổi được chừng nào hay chừng ấy, phần còn lại giữ
    nguyên — giữ nguyên còn hơn nuốt mất một ký hiệu mà không ai biết là đã mất."""
    t = s.strip()
    for boc in ("$$", "$", "\\[", "\\]"):
        t = t.strip().removeprefix(boc).removesuffix(boc).strip()
    for _ in range(3):                        # ngoặc lồng nhau: lặp vài lượt cả bộ
        truoc = t
        for mau, thay in _TEX:
            t = mau.sub(thay, t)
        if t == truoc:
            break
    t = _MOT_LUOT.sub(lambda m: _TEX_KY_HIEU[m.group(0)], t)
    t = _TEX_THOAT.sub(r"\1", t)              # `\%` → `%`, sau cùng
    return re.sub(r"\s+", " ", t).strip()


def tex_con_sot(khoi: list[Khoi]) -> list[str]:
    """Lệnh TeX chưa đổi được — soi **bản ĐÃ đổi**, không soi nguồn.

    Soi nguồn thì `\\frac` và `\\times` cũng bị đếm, trong khi chúng đổi được hết; con số ấy
    sẽ báo động mỗi lần và nhanh chóng bị bỏ qua. *Một cảnh báo luôn kêu thì bằng không kêu.*

    Bộ đổi này cố ý **không phải một bộ dựng TeX**. Nhưng im lặng bỏ qua một lệnh lạ thì người
    đọc nhận một trang giấy có `\\varrho` nằm giữa câu mà không ai báo trước. Nói ra ở
    `note_vi` của `doc.render` thì tác tử sửa được nguồn; im lặng thì không ai sửa gì.
    """
    sot: set[str] = set()
    for k in khoi:
        if k.loai == "cong_thuc":
            sot |= set(_TEX_CON_SOT.findall(cong_thuc_nguoi_doc(k.chu)))
            continue
        if k.loai in ("ma", "so_do"):        # mã và sơ đồ giữ nguyên văn, không phải công thức
            continue
        phan = [k.chu] + [o for h in k.hang for o in h]
        for x in phan:
            for c, kieu in tach_chu(x):
                if "cong_thuc" in kieu:
                    sot |= set(_TEX_CON_SOT.findall(c))
    return sorted(sot)


# ------------------------------------------------------------------- chữ trong dòng
_LIEN_KET = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
# Một lượt duyệt cho cả ba kiểu, không ba lượt thay thế lồng nhau: `**a `b` c**` phải ra đúng
# một lần, còn ba lượt nối tiếp sẽ ăn lẫn dấu của nhau.
_CHU_CO_KIEU = re.compile(r"\*\*(.+?)\*\*|(?<!\*)\*([^*]+?)\*(?!\*)|`([^`]+?)`")


def tach_chu(s: str) -> list[tuple[str, frozenset[str]]]:
    """`"a **b** c"` → `[("a ", ∅), ("b", {"dam"}), (" c", ∅)]`.

    Quét **đệ quy** chứ không thay thế phẳng. Bản đầu dùng một `finditer` cho cả ba kiểu, và
    `*Đề tài: **Phát triển…** · Vũ Trí Công*` in ra giấy thành `*Đề tài: Phát triển…` — nhánh
    hai-sao khớp trước nên cặp một-sao bọc ngoài không còn cặp để đóng, và **dấu sao lọt ra
    bản in**. Không con số nào bắt được chuyện đó; phải nhìn trang PDF.

    Trả về tập kiểu, không phải một kiểu: chữ vừa đậm vừa nghiêng là chuyện thường.

    Liên kết rút về phần chữ kèm địa chỉ trong ngoặc — trừ **neo trong chính tài liệu**
    (`#muc-nao-do`), vì trên giấy một cái neo không bấm được chỉ là rác.
    """
    s = _LIEN_KET.sub(_go_lien_ket, s)
    ra: list[tuple[str, frozenset[str]]] = []
    _quet(s, frozenset(), ra)
    return ra or [(s, frozenset())]


def _go_lien_ket(m: re.Match[str]) -> str:
    chu, dia_chi = m.group(1), m.group(2).strip()
    if not chu:
        return dia_chi
    return chu if dia_chi.startswith("#") else f"{chu} ({dia_chi})"


def _dong_cong_thuc(s: str, i: int) -> tuple[int, str] | None:
    """`$…$` hoặc `$$…$$` bắt đầu ở `i`? Trả `(vị trí sau dấu đóng, ruột)` hoặc `None`.

    Đây là chỗ khó nhất của việc đọc công thức giữa dòng: **dấu đô-la cũng là tiền**. Một câu
    "giá $5 và $10 nữa" mà đọc thành công thức thì ăn mất cả đoạn chữ ở giữa.

    Bốn điều kiện, mỗi cái loại một kiểu nhầm có thật:

    * có dấu đóng trên **cùng một đoạn** (không có ở đây thì `$` chỉ là ký tự thường);
    * ruột **không bắt đầu và không kết thúc bằng khoảng trắng** — "giá $5 và $10" có ruột
      `"5 và "` kết thúc bằng khoảng trắng, nên bị loại đúng như mong muốn;
    * ruột không rỗng và không quá 300 ký tự — quá dài gần như chắc chắn là hai dấu tiền ở
      hai câu khác nhau;
    * ruột không chứa dấu `$` nào nữa.
    """
    dai = 2 if s.startswith("$$", i) else 1
    dau = "$$" if dai == 2 else "$"
    j = s.find(dau, i + dai)
    if j == -1:
        return None
    ruot = s[i + dai:j]
    if not la_cong_thuc_chu_khong_phai_tien(ruot):
        return None
    return j + dai, ruot


def la_cong_thuc_chu_khong_phai_tien(ruot: str) -> bool:
    """Ruột giữa hai dấu `$` là CÔNG THỨC hay là TIỀN?

    Tách ra thành vị từ riêng để **bộ kiểm hai bên gọi được cùng một hình dạng**: phía Swift có
    `MathText.laCongThucChuKhongPhaiTien` làm đúng việc này, và cả hai bộ kiểm đọc chung tập
    mẫu `tests/du-lieu-chung/cong-thuc-giua-dong.json`.

    Ngày 02/10/2026 hai bên lệch nhau và anh Công nhìn thấy trên màn hình: `$[-128, 127]$` còn
    nguyên hai dấu đô-la trên chat, mà trong tệp Word thì đúng. Luật Swift khi ấy đòi công thức
    phải có lệnh TeX, chữ cái, `^` hoặc `_` — `[-128, 127]` không có thứ nào. Và luật ấy còn
    sai chiều ngược: `giá $5 và $10 nữa` có ruột `"5 và "` **chứa chữ cái**, nên nó bị đọc
    thành công thức và ăn mất đoạn chữ ở giữa.

    Bốn điều kiện, mỗi cái loại một kiểu nhầm có thật — xem docstring của `_dong_cong_thuc`.
    """
    if not ruot or ruot != ruot.strip() or "$" in ruot or len(ruot) > 300:
        return False
    # Ruột chỉ có chữ số, dấu chấm phẩy và khoảng trắng thì đó là TIỀN, không phải công thức:
    # `$5$`, `$1.000$`, `$4,450$`. Một công thức thật luôn có thêm thứ gì đó — biến, phép
    # toán, hoặc một lệnh TeX.
    return not re.fullmatch(r"[\d.,\s]+", ruot)


def _quet(s: str, kieu: frozenset[str], ra: list[tuple[str, frozenset[str]]]) -> None:
    dem: list[str] = []

    def xa() -> None:
        if dem:
            ra.append(("".join(dem), kieu))
            dem.clear()

    i, n = 0, len(s)
    while i < n:
        # Công thức đứng TRƯỚC mọi kiểu nhấn mạnh: `$a * b$` có dấu sao, và nếu để nhánh
        # nghiêng đọc trước thì công thức bị cắt làm đôi ở giữa.
        #
        # Đặt phép đổi công thức ở ĐÂY, trong bộ quét chữ, chứ không ở chỗ dựng đoạn văn —
        # vì mọi ngữ cảnh đều đi qua `tach_chu`: đoạn văn, gạch đầu dòng, ô bảng, trích dẫn,
        # tiêu đề, slide PowerPoint, ô Excel. Bản trước chỉ đổi khi CẢ ĐOẠN là `$$…$$` và chỉ
        # trong Word, nên năm chỗ còn lại in nguyên cú pháp TeX ra giấy.
        if s[i] == "$":
            kq = _dong_cong_thuc(s, i)
            if kq is not None:
                sau, ruot = kq
                xa()
                ra.append((cong_thuc_nguoi_doc(ruot), kieu | {"cong_thuc"}))
                i = sau
                continue
        if s.startswith("**", i):
            j = s.find("**", i + 2)
            if j != -1:
                xa()
                _quet(s[i + 2:j], kieu | {"dam"}, ra)
                i = j + 2
                continue
        elif s[i] == "*":
            j = _sao_don(s, i + 1)
            if j != -1:
                xa()
                _quet(s[i + 1:j], kieu | {"nghieng"}, ra)
                i = j + 1
                continue
        elif s[i] == "`":
            j = s.find("`", i + 1)
            if j != -1:
                # Trong khối mã không đọc nhấn mạnh: `a*b*c` phải giữ nguyên dấu sao.
                xa()
                ra.append((s[i + 1:j], kieu | {"ma"}))
                i = j + 1
                continue
        dem.append(s[i])
        i += 1
    xa()


def _sao_don(s: str, tu: int) -> int:
    """Vị trí dấu `*` đơn đóng cặp, bỏ qua mọi cặp `**` nằm giữa. -1 nếu không có."""
    i = tu
    while i < len(s):
        if s.startswith("**", i):
            i += 2
            continue
        if s[i] == "*":
            return i
        i += 1
    return -1


def chu_tran(s: str) -> str:
    """Bỏ hết dấu Markdown, còn lại chữ người đọc — dùng cho ô Excel."""
    return "".join(c for c, _ in tach_chu(s))


def _anh_so_do(nguon: str) -> tuple[Path | None, str]:
    """Vẽ một khối mermaid ra PNG tạm. Trả `(đường dẫn, lý do nếu không vẽ được)`.

    Ảnh nằm trong thư mục tạm của hệ điều hành, không nằm cạnh tài liệu: nó là thứ dựng lại
    được từ nguồn, và để nó lại cạnh tệp `.docx` thì người dùng sẽ thấy một đống PNG lạ mà
    không ai nói cho biết chúng ở đâu ra.
    """
    import tempfile

    from .so_do import ve_png

    d = Path(tempfile.mkdtemp(prefix="eide-sodo-"))
    return ve_png(nguon, d / "so-do.png")


def _chen_so_do(tl: Any, nguon: str, Inches: Any, CANH: Any, Pt: Any, _chu: Any) -> None:
    """Chèn sơ đồ vào tài liệu Word. Không vẽ được thì in mã KÈM LỜI GIẢI THÍCH."""
    from .so_do import tom_tat

    anh, vi_sao = _anh_so_do(nguon)
    if anh is None:
        # Nói rõ vì sao, ngay trong tài liệu. Im lặng in mã thô sẽ để người nhận tự đoán
        # xem tác tử viết sai hay phần mềm thiếu — và đoán thì thường đoán nhầm.
        p = tl.add_paragraph()
        r = p.add_run(f"[sơ đồ chưa vẽ được: {vi_sao} — dưới đây là nguyên văn mã]")
        r.italic = True
        r.font.size = Pt(9.5)
        m = tl.add_paragraph()
        rm = m.add_run(nguon)
        rm.font.name = "Menlo"
        rm.font.size = Pt(9)
        return
    try:
        tl.add_picture(str(anh), width=Inches(RONG_ANH_TOI_DA))
        tl.paragraphs[-1].alignment = CANH.CENTER
    except Exception:                                                  # noqa: BLE001
        return
    c = tl.add_paragraph()
    c.alignment = CANH.CENTER
    rc = c.add_run(tom_tat(nguon))
    rc.italic = True
    rc.font.size = Pt(9.5)


# ============================================================================ → .docx
def _rong_cot(bang: Any, hang: list[list[str]], Inches: Any) -> None:
    """Chia bề rộng cột theo độ dài chữ, có cận dưới và cận trên.

    Cận dưới để một cột toàn số không teo lại thành sợi chỉ; cận trên để một cột văn xuôi
    không nuốt hết trang. Phần còn lại chia theo tỉ lệ độ dài trung bình — không theo độ dài
    lớn nhất, vì một ô ngoại lệ dài gấp ba sẽ kéo lệch cả bảng.
    """
    if not hang:
        return
    sc = max(len(h) for h in hang)
    dai = []
    for j in range(sc):
        o = [len(chu_tran(h[j])) for h in hang if j < len(h)]
        dai.append(sum(o) / len(o) if o else 1)
    # Bố cục CỐ ĐỊNH, nếu không thì `cell.width` chỉ là lời đề nghị và thuật toán tự co của
    # trình đọc ghi đè lên nó — đo được: đặt bề rộng xong mà cột đầu vẫn teo còn một inch.
    bang.autofit = False
    # Cận dưới của mỗi cột = đủ chứa TỪ DÀI NHẤT trong cột ấy.
    #
    # Một hằng số 0,55 inch làm chữ "Senior" gãy thành "Senio/r" — đo trên bảng WBS. Ngắt dòng
    # giữa một từ thì người đọc phải ghép lại trong đầu, mà cái giá để tránh chỉ là vài phần
    # mười inch.
    tu_dai = []
    for j in range(sc):
        w = [max((len(x) for x in chu_tran(h[j]).split()), default=1)
             for h in hang if j < len(h)]
        tu_dai.append(max(w) if w else 1)
    tong = sum(dai) or 1
    KHUNG = 6.4                                    # bề rộng dùng được của khổ A4, lề 2,5 cm
    rong = [max(0.18 + tu_dai[j] * 0.075, min(3.4, KHUNG * d / tong))
            for j, d in enumerate(dai)]
    he_so = KHUNG / sum(rong)
    rong = [r * he_so for r in rong]
    # Đặt CẢ LƯỚI (`tblGrid`) lẫn từng ô.
    #
    # Chỉ đặt `cell.width` là không đủ: đo trên tệp sinh ra, mọi ô đã đúng 3,54 inch mà
    # `gridCol` vẫn 1440 twips (1 inch) cho mọi cột — và LibreOffice, thứ dựng bản PDF, đọc
    # LƯỚI chứ không đọc ô. Hai chỗ cùng nói về một thứ thì phải sửa cả hai.
    for j, r in enumerate(rong):
        if j < len(bang.columns):
            bang.columns[j].width = Inches(r)
    for h in bang.rows:
        for j, o in enumerate(h.cells):
            if j < len(rong):
                o.width = Inches(rong[j])


def sang_docx(khoi: list[Khoi], ra: Path, *, tieu_de: str = "",
              goc_anh: Path | None = None) -> KetQuaRender:
    kq = KetQuaRender(dinh_dang="docx")
    try:
        import docx
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except ImportError as e:                                           # pragma: no cover
        kq.vi_sao_khong_dat = f"Thiếu thư viện python-docx: {e}"
        return kq

    tl = docx.Document()
    # Nguồn đã mở đầu bằng đúng tiêu đề ấy thì bỏ trang bìa đi — bản đầu in tên tài liệu hai
    # lần liền nhau, và người đọc tưởng lỗi sao chép.
    dau = next((k for k in khoi if k.loai != "ngan"), None)
    if (tieu_de and dau is not None and dau.loai == "tieu_de"
            and chu_tran(dau.chu).strip().casefold() == tieu_de.strip().casefold()):
        tieu_de = ""
    if tieu_de:
        h = tl.add_heading(tieu_de, 0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def _chu(p: Any, s: str) -> None:
        for c, kieu in tach_chu(s):
            r = p.add_run(c)
            r.bold = "dam" in kieu
            # Công thức để nghiêng như quy ước toán học — và nghiêng cũng là dấu hiệu đọc
            # được bằng mắt rằng chỗ này ĐÃ qua bộ đổi, chứ không phải chữ thường trùng hình.
            r.italic = "nghieng" in kieu or "cong_thuc" in kieu
            if "ma" in kieu:
                r.font.name = "Menlo"
                r.font.size = Pt(9.5)

    for k in khoi:
        if k.loai == "tieu_de":
            tl.add_heading(chu_tran(k.chu), min(max(k.muc, 1), 6))
        elif k.loai == "doan":
            _chu(tl.add_paragraph(), k.chu)
        elif k.loai == "cong_thuc":
            p = tl.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(cong_thuc_nguoi_doc(k.chu))
            r.italic = True
        elif k.loai in ("gach_dau", "so_thu_tu"):
            kieu = "List Bullet" if k.loai == "gach_dau" else "List Number"
            p = tl.add_paragraph(style=kieu)
            p.paragraph_format.left_indent = Inches(0.25 * (k.muc + 1))
            _chu(p, k.chu)
        elif k.loai == "trich":
            p = tl.add_paragraph(style="Intense Quote")
            _chu(p, k.chu)
        elif k.loai == "ma":
            p = tl.add_paragraph()
            r = p.add_run(k.chu)
            r.font.name = "Menlo"
            r.font.size = Pt(9)
            r.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        elif k.loai == "ngan":
            # Vẽ viền dưới của một đoạn rỗng. Bản đầu rải 40 ký tự `─`, và bản in ra một gạch
            # cụt lủn — phông mặc định của LibreOffice không có ô vẽ ấy nên nó thay bằng thứ
            # khác. Viền là thuộc tính của đoạn, không phụ thuộc phông.
            p = tl.add_paragraph()
            pr = p._p.get_or_add_pPr()
            bd = OxmlElement("w:pBdr")
            duoi = OxmlElement("w:bottom")
            duoi.set(qn("w:val"), "single")
            duoi.set(qn("w:sz"), "6")
            duoi.set(qn("w:color"), "BBBBBB")
            bd.append(duoi)
            pr.append(bd)
        elif k.loai == "bang" and k.hang:
            b = tl.add_table(rows=len(k.hang), cols=max(len(h) for h in k.hang))
            b.style = "Light Grid Accent 1"
            # Cho Word TỰ CO CỘT theo nội dung.
            #
            # Mặc định `python-docx` để bố cục cột cố định, nên một bảng 6 cột có cột đầu dài
            # (tên hạng mục) và năm cột ngắn (con số) sẽ chia đều — cột đầu bị bóp còn một
            # inch và chữ xuống dòng năm lần, trong khi các cột số thừa chỗ. Đo được trên bảng
            # WBS của báo cáo RTOS: mỗi hàng cao gấp bốn lần cần thiết.
            # ĐẶT BỀ RỘNG CỘT THEO NỘI DUNG, không phó mặc autofit.
            #
            # `autofit` là lời đề nghị, và LibreOffice — thứ dựng bản PDF — bỏ qua nó. Đo được
            # trên bảng WBS 6 cột của báo cáo RTOS: cột đầu (tên hạng mục, 40–60 ký tự) bị chia
            # đều bằng năm cột số, còn một inch, chữ xuống dòng năm lần và mỗi hàng cao gấp bốn
            # lần cần thiết. Tính bề rộng bằng mã thì kết quả giống nhau ở mọi trình đọc.
            _rong_cot(b, k.hang, Inches)
            for i, hang in enumerate(k.hang):
                for j, o in enumerate(hang):
                    if j >= len(b.columns):
                        continue
                    o_ = b.cell(i, j)
                    o_.text = ""
                    p = o_.paragraphs[0]
                    _chu(p, o)
                    if i == 0:
                        for r in p.runs:
                            r.bold = True
            # Một đoạn rỗng sau bảng. Hai bảng liền nhau không có khoảng cách thì trông như
            # MỘT bảng — đo được trên mục 5.5 của báo cáo RTOS: bảng đơn giá và bảng kịch bản
            # chi phí dính liền, hàng tiêu đề của bảng sau đọc ra như một hàng dữ liệu.
            tl.add_paragraph()
        elif k.loai == "so_do":
            _chen_so_do(tl, k.chu, Inches, WD_ALIGN_PARAGRAPH, Pt, _chu)
        elif k.loai == "anh":
            p = Path(k.chu)
            if not p.is_absolute() and goc_anh is not None:
                p = goc_anh / k.chu
            if p.is_file():
                try:
                    tl.add_picture(str(p), width=Inches(RONG_ANH_TOI_DA))
                except Exception:                                      # noqa: BLE001
                    tl.add_paragraph(f"[không chèn được ảnh: {k.chu}]")
            else:
                # Nói ra chỗ ảnh thiếu, ngay trong tài liệu. Im lặng bỏ qua thì người đọc
                # bản in sẽ không bao giờ biết là đáng ra có một hình ở đây.
                tl.add_paragraph(f"[thiếu ảnh: {k.chu}]")
            if k.ngon_ngu:
                c = tl.add_paragraph()
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = c.add_run(k.ngon_ngu)
                r.italic = True
                r.font.size = Pt(9.5)

    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        tl.save(str(ra))
    except OSError as e:
        kq.vi_sao_khong_dat = f"Không ghi được {ra.name}: {e}"
        return kq
    kq.tep = ra
    kq.do_lai = doc_lai_docx(ra)
    return kq


# ============================================================================ → .xlsx
def sang_xlsx(khoi: list[Khoi], ra: Path) -> KetQuaRender:
    """Mỗi bảng Markdown thành một sheet. Không bảng thì TỪ CHỐI."""
    kq = KetQuaRender(dinh_dang="xlsx")
    bang = [k for k in khoi if k.loai == "bang" and k.hang]
    if not bang:
        # Từ chối chứ không đổ văn xuôi vào ô A1. Xem docstring đầu tệp.
        kq.vi_sao_khong_dat = (
            "Nguồn không có bảng Markdown nào, nên không có gì để thành Excel. Một tệp .xlsx "
            "chứa cả đoạn văn trong một ô thì mở lên được nhưng vô dụng — và nó TRÔNG GIỐNG "
            "thành công. Thêm ít nhất một bảng dạng `| cột | cột |` kèm hàng kẻ `|---|---|`, "
            "hoặc render sang docx/pdf.")
        return kq
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter
    except ImportError as e:                                           # pragma: no cover
        kq.vi_sao_khong_dat = f"Thiếu thư viện openpyxl: {e}"
        return kq

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    dem: dict[str, int] = {}
    # Tiêu đề gần nhất phía trên bảng thành tên sheet — người mở tệp nhận ra bảng nào là bảng
    # nào mà không phải đọc nội dung.
    ten_gan: list[str] = []
    ten_cho_bang: list[str] = []
    for k in khoi:
        if k.loai == "tieu_de":
            ten_gan = [chu_tran(k.chu)]
        elif k.loai == "bang" and k.hang:
            ten_cho_bang.append(ten_gan[0] if ten_gan else "")

    for idx, k in enumerate(bang):
        goc = (ten_cho_bang[idx] if idx < len(ten_cho_bang) else "") or f"Bảng {idx + 1}"
        # Excel: tên sheet ≤ 31 ký tự, không chứa : \ / ? * [ ]
        ten = re.sub(r"[:\\/?*\[\]]", "-", goc)[:31] or f"Bảng {idx + 1}"
        dem[ten] = dem.get(ten, 0) + 1
        if dem[ten] > 1:
            ten = f"{ten[:27]} ({dem[ten]})"
        ws = wb.create_sheet(ten)
        for i, hang in enumerate(k.hang, start=1):
            for j, o in enumerate(hang, start=1):
                ws.cell(i, j, chu_tran(o))
        for j in range(1, max(len(h) for h in k.hang) + 1):
            o = ws.cell(1, j)
            o.font = Font(bold=True)
            o.fill = PatternFill("solid", fgColor="DDE8F5")
            o.alignment = Alignment(vertical="center", wrap_text=True)
            rong = max((len(str(ws.cell(i, j).value or "")) for i in range(1, ws.max_row + 1)),
                       default=8)
            ws.column_dimensions[get_column_letter(j)].width = min(max(rong + 2, 10), 60)
        ws.freeze_panes = "A2"

    # Sơ đồ: mỗi cái một sheet riêng, chèn ảnh. Không nhét vào sheet bảng — một tấm ảnh nằm
    # đè lên dữ liệu là thứ không ai lọc hay sắp xếp được.
    for idx, k in enumerate([x for x in khoi if x.loai == "so_do"], start=1):
        anh, _vi = _anh_so_do(k.chu)
        if anh is None:
            continue
        from openpyxl.drawing.image import Image as AnhXl

        ws = wb.create_sheet(f"Sơ đồ {idx}")
        ws.add_image(AnhXl(str(anh)), "B2")

    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(str(ra))
    except OSError as e:
        kq.vi_sao_khong_dat = f"Không ghi được {ra.name}: {e}"
        return kq
    kq.tep = ra
    kq.do_lai = doc_lai_xlsx(ra)
    return kq


def sang_pptx(khoi: list[Khoi], ra: Path, *, tieu_de: str = "",
              goc_anh: Path | None = None) -> KetQuaRender:
    """Bản trình chiếu: **mỗi tiêu đề một slide**.

    Quy ước ấy là quy ước duy nhất đọc được từ một tệp Markdown. Cắt theo số dòng hay số chữ
    sẽ cắt giữa câu; cắt theo tiêu đề thì chỗ cắt do người viết nguồn quyết, và họ biết bài
    của họ chia làm mấy phần.

    Bảng và sơ đồ đi vào slide của phần chứa nó. Slide quá dài thì **vẫn để nguyên, không cắt
    bớt** — mất một dòng trong bản trình chiếu thì người trình bày không biết là đã mất.
    """
    kq = KetQuaRender(dinh_dang="pptx")
    try:
        from pptx import Presentation
        from pptx.util import Emu, Inches, Pt
    except ImportError as e:                                           # pragma: no cover
        kq.vi_sao_khong_dat = f"Thiếu thư viện python-pptx: {e}"
        return kq

    tr = Presentation()
    tr.slide_width, tr.slide_height = Inches(13.333), Inches(7.5)      # 16:9
    trang_bia = tr.slide_layouts[0]
    trang_noi_dung = tr.slide_layouts[1]
    trang_trong = tr.slide_layouts[6]

    dau = next((k for k in khoi if k.loai != "ngan"), None)
    ten = tieu_de or (chu_tran(dau.chu) if dau is not None and dau.loai == "tieu_de" else "")
    if ten:
        s = tr.slides.add_slide(trang_bia)
        s.shapes.title.text = ten
        if len(s.placeholders) > 1:
            s.placeholders[1].text = ""

    def slide_moi(tieu: str):
        s = tr.slides.add_slide(trang_noi_dung)
        s.shapes.title.text = chu_tran(tieu)
        return s, s.placeholders[1].text_frame

    hien: Any = None
    than: Any = None
    bo_qua_dau = bool(ten)
    for k in khoi:
        if k.loai == "tieu_de":
            if bo_qua_dau and chu_tran(k.chu).strip().casefold() == ten.strip().casefold():
                bo_qua_dau = False
                continue
            hien, than = slide_moi(k.chu)
            continue
        if hien is None:
            hien, than = slide_moi(ten or "Nội dung")

        if k.loai in ("doan", "gach_dau", "so_thu_tu", "trich"):
            p = than.add_paragraph() if than.text or len(than.paragraphs[0].runs) else \
                than.paragraphs[0]
            p.text = chu_tran(k.chu)
            p.level = min(k.muc, 4)
            p.font.size = Pt(18)
        elif k.loai == "cong_thuc":
            p = than.add_paragraph()
            p.text = cong_thuc_nguoi_doc(k.chu)
            p.font.size = Pt(20)
            p.font.italic = True
        elif k.loai == "ma":
            p = than.add_paragraph()
            p.text = k.chu
            p.font.name = "Menlo"
            p.font.size = Pt(12)
        elif k.loai == "bang" and k.hang:
            _bang_pptx(tr, trang_trong, k, Inches, Pt)
            hien = than = None
        elif k.loai == "so_do":
            anh, vi_sao = _anh_so_do(k.chu)
            s = tr.slides.add_slide(trang_trong)
            if anh is None:
                h = s.shapes.add_textbox(Inches(0.6), Inches(0.6), Inches(12), Inches(6))
                h.text_frame.text = f"[sơ đồ chưa vẽ được: {vi_sao}]\n\n{k.chu}"
                h.text_frame.paragraphs[0].font.size = Pt(12)
            else:
                from PIL import Image as _I

                with _I.open(anh) as im:
                    tl = im.width / im.height
                rong = min(Inches(12), Emu(int(Inches(6.2) * tl)))
                cao = Emu(int(rong / tl))
                s.shapes.add_picture(str(anh), int((tr.slide_width - rong) / 2),
                                     int((tr.slide_height - cao) / 2),
                                     width=int(rong))
            hien = than = None

    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        tr.save(str(ra))
    except OSError as e:
        kq.vi_sao_khong_dat = f"Không ghi được {ra.name}: {e}"
        return kq
    kq.tep = ra
    kq.do_lai = doc_lai_pptx(ra)
    return kq


def _bang_pptx(tr: Any, trang: Any, k: Khoi, Inches: Any, Pt: Any) -> None:
    s = tr.slides.add_slide(trang)
    cot = max(len(h) for h in k.hang)
    b = s.shapes.add_table(len(k.hang), cot, Inches(0.5), Inches(0.6),
                           Inches(12.3), Inches(0.4) * len(k.hang)).table
    for i, hang in enumerate(k.hang):
        for j in range(cot):
            o = b.cell(i, j)
            o.text = chu_tran(hang[j]) if j < len(hang) else ""
            for p in o.text_frame.paragraphs:
                p.font.size = Pt(14)
                p.font.bold = i == 0


# ============================================================================ → .pdf
def sang_pdf(khoi: list[Khoi], ra: Path, *, tieu_de: str = "",
             goc_anh: Path | None = None) -> KetQuaRender:
    """Render docx rồi nhờ LibreOffice đổi sang PDF.

    Đi vòng qua docx thay vì vẽ PDF trực tiếp: một trình vẽ PDF tự viết sẽ phải tự lo ngắt
    dòng, ngắt trang, phông có dấu tiếng Việt — ba việc LibreOffice đã làm đúng từ lâu. Đo
    được trên máy này: `/Applications/LibreOffice.app` có sẵn, và `office.chuyen_doi()` đã bọc
    nó từ trước cho chiều đọc vào.

    **Bản trung gian nằm ở thư mục tạm của hệ điều hành, không nằm cạnh tệp ra.** Bản đầu đặt
    nó ở `ra.parent/<cùng tên>.docx` rồi xoá sau khi đổi xong — nghĩa là render `bao-cao.pdf`
    trong thư mục đang có `bao-cao.docx` sẽ **đè rồi xoá luôn tệp docx của người dùng**. Đo
    được ngay lần chạy thử đầu tiên: dựng cả ba định dạng vào một thư mục, xong thì `.docx`
    không còn ở đó. Mất im lặng, và chỉ lộ ra khi đi tìm.
    """
    import tempfile

    from .knowledge.office import chuyen_doi, co_libreoffice

    kq = KetQuaRender(dinh_dang="pdf")
    if co_libreoffice() is None:
        kq.vi_sao_khong_dat = (
            "Máy chưa có LibreOffice nên không dựng được PDF. Cách khác: render sang `docx` "
            "rồi mở bằng Word/Pages và chọn Xuất PDF. Không tự vẽ một PDF thô sơ ở đây, vì "
            "người nhận sẽ tưởng đó là bản in được.")
        return kq

    ra.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="eide-pdf-") as td:
        tam = Path(td)
        tam_docx = tam / "nguon.docx"
        trung_gian = sang_docx(khoi, tam_docx, tieu_de=tieu_de, goc_anh=goc_anh)
        if not trung_gian.dat:
            kq.vi_sao_khong_dat = (
                f"Bước dựng docx trung gian hỏng: {trung_gian.vi_sao_khong_dat}")
            return kq
        pdf, vi_sao = chuyen_doi(tam_docx, "pdf", tam)
        if pdf is None:
            kq.vi_sao_khong_dat = vi_sao or "LibreOffice không tạo được PDF."
            return kq
        ra.write_bytes(pdf.read_bytes())
    kq.tep = ra
    kq.do_lai = doc_lai_pdf(ra)
    return kq


# ============================================================================ đọc lại để ĐO
def doc_lai_docx(p: Path) -> dict[str, Any]:
    """Mở lại tệp vừa tạo và đếm. Xem docstring đầu tệp về lý do."""
    try:
        import docx

        tl = docx.Document(str(p))
        chu = sum(len(x.text) for x in tl.paragraphs)
        for b in tl.tables:
            for h in b.rows:
                for o in h.cells:
                    chu += len(o.text)
        return {"so_doan": len(tl.paragraphs), "so_bang": len(tl.tables),
                "so_ky_tu": chu, "byte": p.stat().st_size}
    except Exception as e:                                             # noqa: BLE001
        return {"khong_doc_lai_duoc": str(e), "byte": p.stat().st_size if p.exists() else 0}


def doc_lai_xlsx(p: Path) -> dict[str, Any]:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(str(p), read_only=True)
        sheet = {ws.title: {"hang": ws.max_row, "cot": ws.max_column} for ws in wb.worksheets}
        wb.close()
        return {"so_sheet": len(sheet), "sheet": sheet,
                "tong_hang": sum(s["hang"] for s in sheet.values()),
                "byte": p.stat().st_size}
    except Exception as e:                                             # noqa: BLE001
        return {"khong_doc_lai_duoc": str(e), "byte": p.stat().st_size if p.exists() else 0}


def doc_lai_pptx(p: Path) -> dict[str, Any]:
    try:
        from pptx import Presentation

        tr = Presentation(str(p))
        chu = 0
        anh = 0
        for s in tr.slides:
            for sh in s.shapes:
                if sh.has_text_frame:
                    chu += len(sh.text_frame.text)
                if sh.shape_type == 13:                    # PICTURE
                    anh += 1
        return {"so_slide": len(tr.slides), "so_ky_tu": chu, "so_hinh": anh,
                "byte": p.stat().st_size}
    except Exception as e:                                             # noqa: BLE001
        return {"khong_doc_lai_duoc": str(e), "byte": p.stat().st_size if p.exists() else 0}


def doc_lai_pdf(p: Path) -> dict[str, Any]:
    try:
        from pypdf import PdfReader

        r = PdfReader(str(p))
        chu = 0
        for t in r.pages[:20]:
            try:
                chu += len(t.extract_text() or "")
            except Exception:                                          # noqa: BLE001
                pass
        return {"so_trang": len(r.pages), "so_ky_tu_20_trang_dau": chu,
                "byte": p.stat().st_size,
                "ghi_chu": ("Số trang chỉ đúng với chính tệp này — nó phụ thuộc phông chữ và "
                            "khổ giấy. Trích dẫn theo mục, đừng theo số trang.")}
    except Exception as e:                                             # noqa: BLE001
        return {"khong_doc_lai_duoc": str(e), "byte": p.stat().st_size if p.exists() else 0}


# ============================================================================ cửa vào
def render(md: str, ra: Path, dinh_dang: str, *, tieu_de: str = "",
           goc_anh: Path | None = None) -> KetQuaRender:
    """Markdown → tệp. Một cửa cho cả ba định dạng."""
    if dinh_dang not in DINH_DANG:
        return KetQuaRender(dinh_dang=dinh_dang,
                            vi_sao_khong_dat=f"Không biết định dạng {dinh_dang!r}. "
                                             f"Có: {', '.join(DINH_DANG)}.")
    khoi = doc_markdown(md)
    if not khoi:
        return KetQuaRender(dinh_dang=dinh_dang,
                            vi_sao_khong_dat="Nguồn rỗng — không có gì để render.")
    if dinh_dang == "docx":
        kq = sang_docx(khoi, ra, tieu_de=tieu_de, goc_anh=goc_anh)
    elif dinh_dang == "xlsx":
        kq = sang_xlsx(khoi, ra)
    elif dinh_dang == "pptx":
        kq = sang_pptx(khoi, ra, tieu_de=tieu_de, goc_anh=goc_anh)
    else:
        kq = sang_pdf(khoi, ra, tieu_de=tieu_de, goc_anh=goc_anh)

    # Lệnh TeX không đổi được thì **nói ra**, chứ không lặng lẽ in cú pháp thô ra giấy.
    # Bộ đổi này cố ý không phải một bộ dựng TeX; giới hạn của nó phải hiện ở kết quả, nếu
    # không thì nó là một giới hạn chỉ người đọc bản in mới phát hiện — quá muộn.
    if kq.dat:
        sot = tex_con_sot(khoi)
        if sot:
            kq.do_lai["tex_chua_doi_duoc"] = sot
    return kq
