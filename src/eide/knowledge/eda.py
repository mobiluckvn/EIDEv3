# -*- coding: utf-8 -*-
"""EDA — netlist, sơ đồ KiCad, BOM. EIDE-ING-43 §4.4. Bước ING-D.

## Ba việc, và cái thứ ba là cái đáng giá nhất

1. **Đọc netlist** (`.net`) — đã có từ G4 ở mức đếm net; ở đây đọc thành cấu trúc.
2. **Đọc `.kicad_sch`** — dựng netlist nội bộ từ sơ đồ, không cần KiCad chạy.
3. **Đối chiếu BOM ↔ netlist** — ca TC062.

Việc thứ ba là chỗ lỗi thật hay xảy ra và khó thấy nhất: sơ đồ có `C4` nhưng BOM quên
mua nó, hoặc BOM ghi `R5 10k` trong khi sơ đồ vẽ `R5 4k7`. Không ai phát hiện ở bàn làm
việc — người ta phát hiện lúc hàn xong và mạch không chạy. Hai danh sách cạnh nhau thì
máy so trong một giây.

Bộ đọc S-expression viết tay, không thêm phụ thuộc: định dạng KiCad là S-expression
thuần, và một bộ đọc 40 dòng đủ dùng cho `components` và `nets` — hai thứ ta cần. Dùng
thư viện ngoài cho việc này là thêm một thứ phải giải trình khi bảo vệ đề án mà không
đổi được kết quả.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =========================================================================== S-expression
def doc_sexp(chu: str) -> list[Any]:
    """S-expression → danh sách lồng nhau. Chuỗi trong ngoặc kép giữ nguyên."""
    ra: list[Any] = []
    ngan_xep: list[list[Any]] = [ra]
    i, n = 0, len(chu)
    while i < n:
        c = chu[i]
        if c == "(":
            moi: list[Any] = []
            ngan_xep[-1].append(moi)
            ngan_xep.append(moi)
            i += 1
        elif c == ")":
            if len(ngan_xep) > 1:
                ngan_xep.pop()
            i += 1
        elif c == '"':
            j = i + 1
            buf: list[str] = []
            while j < n:
                if chu[j] == "\\" and j + 1 < n:
                    buf.append(chu[j + 1])
                    j += 2
                    continue
                if chu[j] == '"':
                    break
                buf.append(chu[j])
                j += 1
            ngan_xep[-1].append("".join(buf))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not chu[j].isspace() and chu[j] not in "()\"":
                j += 1
            ngan_xep[-1].append(chu[i:j])
            i = j
    return ra


def _tim(cay: Any, ten: str) -> list[list[Any]]:
    """Mọi nút `(ten …)` ở bất kỳ độ sâu nào."""
    ra: list[list[Any]] = []
    if isinstance(cay, list):
        if cay and cay[0] == ten:
            ra.append(cay)
        for x in cay:
            ra.extend(_tim(x, ten))
    return ra


def _gia_tri(nut: list[Any], ten: str, mac_dinh: str = "") -> str:
    for x in nut:
        if isinstance(x, list) and len(x) >= 2 and x[0] == ten:
            return str(x[1])
    return mac_dinh


# =========================================================================== netlist
@dataclass(slots=True)
class LinhKien:
    ref: str
    gia_tri: str = ""
    footprint: str = ""
    datasheet: str = ""


@dataclass(slots=True)
class Net:
    ten: str
    chan: list[tuple[str, str]] = field(default_factory=list)   # (ref, số chân)


@dataclass(slots=True)
class Mach:
    """Netlist nội bộ — dạng chung cho `.net`, `.kicad_sch`, Eagle, EasyEDA."""

    nguon: str
    linh_kien: list[LinhKien] = field(default_factory=list)
    net: list[Net] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    @property
    def theo_ref(self) -> dict[str, LinhKien]:
        return {l.ref: l for l in self.linh_kien}

    def to_dict(self) -> dict[str, Any]:
        return {
            "nguon": self.nguon,
            "so_linh_kien": len(self.linh_kien), "so_net": len(self.net),
            "linh_kien": [{"ref": l.ref, "gia_tri": l.gia_tri,
                           "footprint": l.footprint} for l in self.linh_kien],
            "net": [{"ten": n.ten, "so_chan": len(n.chan),
                     "chan": [f"{r}.{p}" for r, p in n.chan]} for n in self.net],
            "canh_bao": list(self.canh_bao),
        }

    def net_mot_chan(self) -> list[str]:
        """Net chỉ nối một chân — gần như luôn là lỗi vẽ (ERC cơ bản)."""
        return [n.ten for n in self.net if len(n.chan) == 1]


def doc_netlist(path: Path) -> tuple[Mach | None, str]:
    """`.net` của KiCad: `(export (components …) (nets …))`."""
    chu = path.read_text("utf-8", errors="replace")
    cay = doc_sexp(chu)
    xuat = _tim(cay, "export")
    if not xuat:
        return None, f"{path.name}: không thấy khối (export …) — không phải netlist KiCad."

    m = Mach(nguon=path.name)
    for comp in _tim(xuat[0], "comp"):
        ref = _gia_tri(comp, "ref")
        if not ref:
            continue
        m.linh_kien.append(LinhKien(
            ref=ref, gia_tri=_gia_tri(comp, "value"),
            footprint=_gia_tri(comp, "footprint"),
            datasheet=_gia_tri(comp, "datasheet")))
    for net in _tim(xuat[0], "net"):
        ten = _gia_tri(net, "name") or _gia_tri(net, "code")
        if not ten:
            continue
        chan: list[tuple[str, str]] = []
        for nut in net:
            if isinstance(nut, list) and nut and nut[0] == "node":
                chan.append((_gia_tri(nut, "ref"), _gia_tri(nut, "pin")))
        m.net.append(Net(ten=ten, chan=chan))
    return m, ""


# =========================================================================== .kicad_sch
def doc_kicad_sch(path: Path) -> tuple[Mach | None, str]:
    """Dựng netlist nội bộ từ sơ đồ, KHÔNG cần KiCad chạy.

    Cách làm và giới hạn của nó, nói thẳng: KiCad nối dây theo **toạ độ** — hai chân
    trùng điểm là nối nhau. Bộ này nối theo **nhãn** (`label`, `global_label`,
    `hierarchical_label`), vì nhãn là thứ đọc được mà không phải dựng lại hình học của
    cả trang. Nên nó thấy đủ linh kiện và các net CÓ NHÃN; net chỉ nối bằng dây trần
    thì nó **nói là không thấy** thay vì đoán.
    """
    chu = path.read_text("utf-8", errors="replace")
    cay = doc_sexp(chu)
    goc = _tim(cay, "kicad_sch")
    if not goc:
        return None, f"{path.name}: không thấy khối (kicad_sch …)."

    m = Mach(nguon=path.name)
    for sym in _tim(goc[0], "symbol"):
        ref = ""
        gia_tri = ""
        for pr in _tim(sym, "property"):
            if len(pr) >= 3 and pr[1] == "Reference":
                ref = str(pr[2])
            elif len(pr) >= 3 and pr[1] == "Value":
                gia_tri = str(pr[2])
        if ref and not ref.startswith("#"):
            m.linh_kien.append(LinhKien(ref=ref, gia_tri=gia_tri))

    nhan: set[str] = set()
    for ten_nut in ("label", "global_label", "hierarchical_label"):
        for nut in _tim(goc[0], ten_nut):
            if len(nut) >= 2 and isinstance(nut[1], str):
                nhan.add(nut[1])
    for t in sorted(nhan):
        m.net.append(Net(ten=t))

    m.canh_bao.append(
        "Netlist dựng từ NHÃN trên sơ đồ, không từ toạ độ dây. Net nối bằng dây trần "
        "không có nhãn sẽ không xuất hiện ở đây — muốn đủ thì xuất .net từ KiCad.")
    return m, ""


# =========================================================================== BOM
_COT_REF = {"ref", "refs", "reference", "references", "designator", "designators",
            "mã", "ký hiệu"}
_COT_GIA_TRI = {"value", "val", "giá trị", "giatri"}
_COT_SL = {"qty", "quantity", "số lượng", "sl"}
_COT_MPN = {"mpn", "part", "part number", "mã linh kiện"}


@dataclass(slots=True)
class DongBom:
    ref: list[str]
    gia_tri: str = ""
    so_luong: int = 0
    mpn: str = ""


def doc_bom_csv(path: Path) -> tuple[list[DongBom], str]:
    """BOM `.csv`. Dò tiêu đề mềm dẻo — mỗi công cụ EDA đặt tên cột một kiểu."""
    import csv

    chu = path.read_text("utf-8", errors="replace")
    dau = chu.splitlines()[0] if chu.strip() else ""
    ky_tu = ";" if dau.count(";") > dau.count(",") else ","
    ds: list[DongBom] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        doc = csv.reader(f, delimiter=ky_tu)
        hang = list(doc)
    if not hang:
        return [], f"{path.name}: tệp rỗng."

    tieu_de = [c.strip().lower() for c in hang[0]]
    i_ref = next((i for i, c in enumerate(tieu_de) if c in _COT_REF), None)
    if i_ref is None:
        return [], (f"{path.name}: không thấy cột mã linh kiện (Ref/Designator). "
                    "Không đoán cột nào là cột nào — hỏi người dùng hoặc xuất lại BOM.")
    i_gt = next((i for i, c in enumerate(tieu_de) if c in _COT_GIA_TRI), None)
    i_sl = next((i for i, c in enumerate(tieu_de) if c in _COT_SL), None)
    i_mpn = next((i for i, c in enumerate(tieu_de) if c in _COT_MPN), None)

    for r in hang[1:]:
        if not any(x.strip() for x in r):
            continue
        tho = r[i_ref] if i_ref < len(r) else ""
        refs = [x.strip() for x in re.split(r"[,\s;]+", tho) if x.strip()]
        if not refs:
            continue
        sl = 0
        if i_sl is not None and i_sl < len(r):
            m = re.search(r"\d+", r[i_sl])
            sl = int(m.group(0)) if m else 0
        ds.append(DongBom(
            ref=refs,
            gia_tri=(r[i_gt].strip() if i_gt is not None and i_gt < len(r) else ""),
            so_luong=sl or len(refs),
            mpn=(r[i_mpn].strip() if i_mpn is not None and i_mpn < len(r) else "")))
    return ds, ""


def doi_chieu_bom_netlist(bom: list[DongBom], mach: Mach) -> dict[str, Any]:
    """TC062 — BOM ≠ netlist. Ba loại lệch, mỗi loại một hậu quả khác nhau.

    - **thiếu trong BOM**: sơ đồ có mà không ai mua → hàn xong thiếu linh kiện.
    - **thừa trong BOM**: mua mà sơ đồ không có → tốn tiền, và có thể là dấu hiệu sơ đồ
      đã đổi mà BOM chưa cập nhật.
    - **giá trị khác nhau**: tệ nhất, vì mạch hàn xong **chạy** nhưng sai.
    """
    from .chuan_hoa import chuan_hoa

    ref_bom: dict[str, DongBom] = {}
    for d in bom:
        for r in d.ref:
            ref_bom[r.upper()] = d
    ref_mach = {r.upper(): l for r, l in mach.theo_ref.items()}

    thieu = sorted(set(ref_mach) - set(ref_bom))
    thua = sorted(set(ref_bom) - set(ref_mach))

    khac: list[dict[str, Any]] = []
    for r in sorted(set(ref_bom) & set(ref_mach)):
        a, b = (ref_bom[r].gia_tri or "").strip(), (ref_mach[r].gia_tri or "").strip()
        if not a or not b or a.lower() == b.lower():
            continue
        ga, gb = chuan_hoa(a), chuan_hoa(b)
        if ga.co_so and gb.co_so and ga.don_vi == gb.don_vi:
            if ga.gia_tri is not None and gb.gia_tri is not None and \
                    abs(ga.gia_tri - gb.gia_tri) < 1e-12:
                continue                      # "4k7" và "4700" là cùng một giá trị
        khac.append({"ref": r, "bom": a, "so_do": b,
                     "bom_chuan": ga.hien_vi(), "so_do_chuan": gb.hien_vi()})

    dong: list[str] = []
    if thieu:
        dong.append(f"{len(thieu)} linh kiện có trong sơ đồ mà KHÔNG có trong BOM: "
                    + ", ".join(thieu[:8]) + " — hàn xong sẽ thiếu.")
    if thua:
        dong.append(f"{len(thua)} linh kiện có trong BOM mà không có trong sơ đồ: "
                    + ", ".join(thua[:8]) + " — hoặc mua thừa, hoặc sơ đồ đã đổi mà BOM "
                    "chưa cập nhật.")
    for k in khac[:8]:
        dong.append(f"{k['ref']}: BOM ghi {k['bom']}, sơ đồ vẽ {k['so_do']} — mạch hàn "
                    "xong sẽ CHẠY nhưng sai.")

    return {
        "khop": not (thieu or thua or khac),
        "thieu_trong_bom": thieu, "thua_trong_bom": thua, "gia_tri_khac": khac,
        "so_linh_kien_so_do": len(ref_mach), "so_linh_kien_bom": len(ref_bom),
        "se_mat_vi": dong,
        "note_vi": ("BOM và sơ đồ khớp nhau." if not dong else
                    "BOM và sơ đồ KHÔNG khớp. Trình từng dòng cho người dùng — đây là "
                    "loại lỗi chỉ lộ ra khi đã hàn."),
    }
