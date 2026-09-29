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

DINH_DANG = ("docx", "xlsx", "pdf")

# Ảnh chèn vào tài liệu rộng tối đa ngần này (inch) — vừa khổ A4 lề 2,5 cm.
RONG_ANH_TOI_DA = 6.0


# ============================================================================ mô hình khối
@dataclass(slots=True)
class Khoi:
    """Một khối Markdown đã đọc xong. `loai` quyết định các trường nào có nghĩa."""

    loai: str                       # tieu_de | doan | gach_dau | so_thu_tu | bang | ma | anh | ngan | trich
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
            khoi.append(Khoi("doan", " ".join(x.strip() for x in dem_doan).strip()))
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
            khoi.append(Khoi("ma", "\n".join(than), ngon_ngu=ng))
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
            khoi.append(Khoi("trich", d.lstrip()[1:].strip()))
            dang_mo = khoi[-1]
            i += 1
            continue

        if dang_mo is not None:                   # dòng nối tiếp của mục đang mở
            dang_mo.chu = (dang_mo.chu + " " + d.strip()).strip()
        else:
            dem_doan.append(d)
        i += 1

    xa_doan()
    return khoi


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


def _quet(s: str, kieu: frozenset[str], ra: list[tuple[str, frozenset[str]]]) -> None:
    dem: list[str] = []

    def xa() -> None:
        if dem:
            ra.append(("".join(dem), kieu))
            dem.clear()

    i, n = 0, len(s)
    while i < n:
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


# ============================================================================ → .docx
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
            r.italic = "nghieng" in kieu
            if "ma" in kieu:
                r.font.name = "Menlo"
                r.font.size = Pt(9.5)

    for k in khoi:
        if k.loai == "tieu_de":
            tl.add_heading(chu_tran(k.chu), min(max(k.muc, 1), 6))
        elif k.loai == "doan":
            _chu(tl.add_paragraph(), k.chu)
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

    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        wb.save(str(ra))
    except OSError as e:
        kq.vi_sao_khong_dat = f"Không ghi được {ra.name}: {e}"
        return kq
    kq.tep = ra
    kq.do_lai = doc_lai_xlsx(ra)
    return kq


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
        return sang_docx(khoi, ra, tieu_de=tieu_de, goc_anh=goc_anh)
    if dinh_dang == "xlsx":
        return sang_xlsx(khoi, ra)
    return sang_pdf(khoi, ra, tieu_de=tieu_de, goc_anh=goc_anh)
