# -*- coding: utf-8 -*-
"""Bước 6 — render SVG bằng bộ vẽ NỘI BỘ. EIDE-SCH-44 §3 bước 6, §6 mức R1.

§6 nói rõ mức R1 là *"renderer nội bộ … đọc .kicad_sch + .kicad_sym → SVG"*, và *"không cam
kết giống KiCad 100 %"*. Bản này tự viết thay vì thêm một phụ thuộc vẽ: SVG là XML phẳng, và
thứ cần vẽ ở đây có sáu loại (hộp ký hiệu, chân, chữ ref/value, nhãn net, dây, ký hiệu nguồn).

**Ba phép kiểm của §3 bước 6, và chúng là lý do tệp này trả về nhiều hơn một chuỗi SVG:**

    ảnh không rỗng              → `so_ky_hieu > 0`
    số ký hiệu trong SVG = số ref → `so_ky_hieu == len(ref)`; lệch thì nói ra
    text không đè                → `kiem_bbox()` đếm cặp chữ chồng nhau

Phép thứ ba là phép đáng giá nhất. Một sơ đồ có hai nhãn đè nhau vẫn "render thành công" —
ảnh có, không lỗi, và người đọc thấy một chuỗi ký tự vô nghĩa ở đúng chỗ họ cần đọc net.

Toạ độ KiCad tính bằng mm, gốc ở góc trên-trái, y hướng xuống — trùng quy ước SVG, nên không
có phép biến đổi nào ngoài một hệ số phóng.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any

PX_MOI_MM = 4.0               # 1 mm → 4 px: đọc được trên màn hình, tệp không quá to

# Cỡ chữ lấy từ lớp BỐ CỤC, không tự đoán lại ở đây. Bố cục làm việc bằng mm và nó là chỗ
# quyết định khoảng cách giữa hai nhãn; bộ vẽ chỉ đổi sang px. Hai bên đoán riêng thì hộp bao
# chữ và chữ thật lệch nhau, và phép kiểm "chữ không đè" trở thành trang trí.
from .bo_cuc import CAO_CHU_MM

CO_CHU_PX = CAO_CHU_MM * PX_MOI_MM
CHU_RONG_TREN_CAO = 0.6       # tỉ lệ rộng/cao cho phông đều nét


@dataclass(slots=True)
class KetQuaVe:
    svg: str = ""
    so_ky_hieu: int = 0
    so_nhan: int = 0
    so_day: int = 0
    ref_trong_svg: list[str] = field(default_factory=list)
    chu_de_nhau: list[str] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"so_ky_hieu": self.so_ky_hieu, "so_nhan": self.so_nhan,
                "so_day": self.so_day, "ref_trong_svg": list(self.ref_trong_svg),
                "chu_de_nhau": list(self.chu_de_nhau), "canh_bao": list(self.canh_bao),
                "byte_svg": len(self.svg.encode("utf-8"))}


# =========================================================================== đọc .kicad_sch
_SO = r"-?\d+(?:\.\d+)?"


def doc_kicad_sch(noi_dung: str) -> dict[str, Any]:
    """Đọc `.kicad_sch` lấy đúng thứ cần để vẽ: ký hiệu, nhãn, dây, khổ giấy.

    Dùng `kiutils` nếu có (đường chính), và có đường lui bằng biểu thức chính quy nếu không.
    Đường lui tồn tại vì §6 mức R3: thiếu thư viện thì **suy giảm**, không chết — và render
    là thứ người dùng nhìn, nên nó không được biến mất chỉ vì một import.
    """
    try:
        from kiutils.schematic import Schematic
        from kiutils.utils.sexpr import parse_sexp

        s = Schematic.from_sexpr(parse_sexp(noi_dung))
        kho = getattr(getattr(s, "paper", None), "paperSize", None) or "A4"
        ky_hieu = []
        for sym in s.schematicSymbols or []:
            ref = next((p.value for p in (sym.properties or [])
                        if p.key == "Reference"), "")
            val = next((p.value for p in (sym.properties or []) if p.key == "Value"), "")
            ky_hieu.append({"ref": ref, "ten": val or sym.entryName,
                            "x": float(sym.position.X), "y": float(sym.position.Y)})
        nhan = [{"text": l.text, "x": float(l.position.X), "y": float(l.position.Y)}
                for l in (s.labels or [])]
        day = []
        for g in (s.graphicalItems or []):
            pts = getattr(g, "points", None)
            if pts and len(pts) >= 2:
                day.append({"tu": [float(pts[0].X), float(pts[0].Y)],
                            "den": [float(pts[-1].X), float(pts[-1].Y)]})
        return {"kho": kho, "ky_hieu": ky_hieu, "nhan": nhan, "day": day, "bang": "kiutils"}
    except Exception:                                     # noqa: BLE001
        return _doc_tho(noi_dung)


def _doc_tho(noi_dung: str) -> dict[str, Any]:
    """Đường lui: đọc bằng biểu thức chính quy. Kém chính xác hơn, và NÓI RA điều đó."""
    kho = (re.search(r'\(paper\s+"([^"]+)"', noi_dung) or [None, "A4"])[1]
    ky_hieu: list[dict[str, Any]] = []
    for m in re.finditer(r'\(symbol \(lib_id "([^"]*)"\) \(at (' + _SO + r") (" + _SO + r")",
                         noi_dung):
        ky_hieu.append({"ref": "", "ten": m.group(1).split(":")[-1],
                        "x": float(m.group(2)), "y": float(m.group(3))})
    for i, m in enumerate(re.finditer(r'\(property "Reference" "([^"]*)"', noi_dung)):
        if i < len(ky_hieu):
            ky_hieu[i]["ref"] = m.group(1)
    nhan = [{"text": m.group(1), "x": float(m.group(2)), "y": float(m.group(3))}
            for m in re.finditer(r'\(label "([^"]*)" \(at (' + _SO + r") (" + _SO + r")",
                                 noi_dung)]
    day = [{"tu": [float(m.group(1)), float(m.group(2))],
            "den": [float(m.group(3)), float(m.group(4))]}
           for m in re.finditer(r"\(wire \(pts \(xy (" + _SO + r") (" + _SO + r")\) "
                                r"\(xy (" + _SO + r") (" + _SO + r")\)\)", noi_dung)]
    return {"kho": kho, "ky_hieu": ky_hieu, "nhan": nhan, "day": day, "bang": "regex"}


# =========================================================================== vẽ
def ve(noi_dung_sch: str, *, hop: dict[str, tuple[float, float]] | None = None) -> KetQuaVe:
    """`.kicad_sch` → SVG. `hop` là kích thước từng ký hiệu (ref → (rộng, cao)) nếu biết.

    Không biết kích thước thì vẽ hộp mặc định — và ghi cảnh báo, vì một hộp sai kích thước
    làm phép kiểm "chữ không đè" nói về một hình khác với hình người thấy.
    """
    from .bo_cuc import KHO_GIAY

    d = doc_kicad_sch(noi_dung_sch)
    kq = KetQuaVe()
    if d["bang"] == "regex":
        kq.canh_bao.append("Đọc .kicad_sch bằng biểu thức chính quy (kiutils không dùng "
                           "được) — hình có thể thiếu chi tiết.")
    rong_mm, cao_mm = KHO_GIAY.get(d["kho"], KHO_GIAY["A4"])
    W, H = rong_mm * PX_MOI_MM, cao_mm * PX_MOI_MM

    L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}">',
         '<rect width="100%" height="100%" fill="#fffef8"/>',
         '<g stroke="#1a1a1a" fill="none" stroke-width="1.2" '
         'font-family="ui-monospace, monospace">']

    chu: list[tuple[float, float, float, float, str]] = []      # bbox chữ để kiểm đè

    for s in sorted(d["day"], key=lambda z: (z["tu"], z["den"])):
        x1, y1 = [v * PX_MOI_MM for v in s["tu"]]
        x2, y2 = [v * PX_MOI_MM for v in s["den"]]
        L.append(f'<path d="M {x1:.1f} {y1:.1f} L {x2:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}" '
                 'stroke="#1f6f3f"/>')
        kq.so_day += 1

    for s in sorted(d["ky_hieu"], key=lambda z: z["ref"] or z["ten"]):
        ref = s["ref"] or "?"
        w, h = (hop or {}).get(ref, (25.4, 15.24))
        x, y = s["x"] * PX_MOI_MM, s["y"] * PX_MOI_MM
        pw, ph = w * PX_MOI_MM, h * PX_MOI_MM
        # `data-ref` để giao diện bấm vào ký hiệu rồi hỏi về nó (§3 bước 6: "bản đồ id ký
        # hiệu → ref").
        L.append(f'<g data-ref="{html.escape(ref)}">')
        L.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{pw:.1f}" height="{ph:.1f}" '
                 'fill="#fffbe8" stroke="#8a6d1f"/>')
        L.append(_chu(x + 2, y - 3, ref, weight="bold"))
        chu.append((*_bbox(ref, x + 2, y - 3), ref))
        ten = s["ten"] or ""
        if ten:
            L.append(_chu(x + 2, y + ph + 9, ten, mau="#555"))
            chu.append((*_bbox(ten, x + 2, y + ph + 9), ten))
        L.append("</g>")
        kq.so_ky_hieu += 1
        kq.ref_trong_svg.append(ref)

    for n in sorted(d["nhan"], key=lambda z: (z["text"], z["x"], z["y"])):
        x, y = n["x"] * PX_MOI_MM, n["y"] * PX_MOI_MM
        L.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="#1f6f3f" stroke="none"/>')
        L.append(_chu(x + 4, y + 3, n["text"], mau="#1f6f3f"))
        chu.append((*_bbox(n["text"], x + 4, y + 3), n["text"]))
        kq.so_nhan += 1

    L += ["</g>", "</svg>", ""]
    kq.svg = "\n".join(L)
    kq.chu_de_nhau = kiem_bbox(chu)
    if kq.chu_de_nhau:
        kq.canh_bao.append(f"{len(kq.chu_de_nhau)} cặp chữ đè nhau — người đọc sẽ thấy một "
                           "chuỗi ký tự vô nghĩa ở đúng chỗ họ cần đọc: "
                           + "; ".join(kq.chu_de_nhau[:4]))
    if kq.so_ky_hieu == 0:
        kq.canh_bao.append("Ảnh KHÔNG có ký hiệu nào — đây là một hình rỗng, không phải một "
                           "sơ đồ.")
    return kq


def _chu(x: float, y: float, t: str, *, mau: str = "#1a1a1a", weight: str = "normal") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{CO_CHU_PX:.1f}" '
            f'fill="{mau}" stroke="none" font-weight="{weight}">{html.escape(t)}</text>')


def _bbox(t: str, x: float, y: float) -> tuple[float, float, float, float]:
    """Hộp bao của một chuỗi chữ (px). `y` là đường chân chữ, như SVG quy ước.

    Ước lượng rộng tay: thà báo hai chữ đè nhau khi chúng chỉ gần nhau, còn hơn bỏ lọt một
    cặp thật sự đè. Một cảnh báo oan thì người xem hình rồi bỏ qua; một cặp bỏ lọt thì họ đọc
    sai tên net.
    """
    rong = len(t) * CO_CHU_PX * CHU_RONG_TREN_CAO
    return (x, y - CO_CHU_PX, x + rong, y)


def kiem_bbox(chu: list[tuple[float, float, float, float, str]]) -> list[str]:
    """Cặp chữ chồng hộp bao nhau. §3 bước 6: "text không đè (kiểm bbox)".

    Đây là phép kiểm mà một renderer "chạy thành công" không bao giờ tự làm: ảnh vẫn có, không
    lỗi nào, và hai nhãn net đè nhau thành một chuỗi không đọc được.
    """
    ra: list[str] = []
    for i in range(len(chu)):
        for j in range(i + 1, len(chu)):
            x1, y1, x2, y2, t1 = chu[i]
            a1, b1, a2, b2, t2 = chu[j]
            if x1 < a2 and a1 < x2 and y1 < b2 and b1 < y2:
                ra.append(f"{t1!r} × {t2!r}")
    return ra
