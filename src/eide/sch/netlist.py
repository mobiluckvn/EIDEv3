# -*- coding: utf-8 -*-
"""Bước 2 — netlist KiCad và phép kiểm đẳng cấu. SCH-44 §3 bước 2, ca SCH02/SCH14.

Phép kiểm là lý do tồn tại của bước này: *"Đẳng cấu với netlist CKM (so tập (ref.pin,
net)); lệch → lỗi E8001 kèm diff, không đi tiếp."*

Hai vế của phép so, và chúng phải **độc lập**:

    vế A   `flatten(cây)` — netlist điện suy từ cây khối bằng mã
    vế B   netlist đọc lại từ **tệp SKiDL đã sinh**, bằng `ast` (xem `doc_skidl.py`)

Vế B đi qua một hiện vật mà mô hình có thể đã sửa, nên nó bắt được đúng thứ SCH14 nói:
"SKiDL sinh net không có trong CKM (mô hình bịa)". Nếu thay vế B bằng "viết .net từ cây rồi
so với flatten" thì phép kiểm so chính mình với chính mình — **luôn đạt**, và một phép kiểm
luôn đạt tệ hơn không có phép kiểm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KetQuaDangCau:
    dat: bool
    net_thieu: dict[str, list[str]] = field(default_factory=dict)   # có ở cây, thiếu ở SKiDL
    net_them: dict[str, list[str]] = field(default_factory=dict)    # SKiDL có, cây không
    chan_lech: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    vi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "net_thieu": self.net_thieu, "net_them": self.net_them,
                "chan_lech": self.chan_lech, "vi": self.vi}


def so_dang_cau(phang: dict[str, list[str]],
                tu_skidl: dict[str, list[str]]) -> KetQuaDangCau:
    """So tập `(ref.pin, net)` hai bên. Tên net phải khớp, và tập chân của mỗi net phải khớp.

    Net rỗng hai bên vẫn được so: một net không nối gì là một cái tên vô nghĩa mà người cần
    thấy, và nếu bỏ qua nó thì một net bị mất hẳn khỏi tệp SKiDL cũng không bị phát hiện.
    """
    a = {k: sorted(set(v)) for k, v in phang.items()}
    b = {k: sorted(set(v)) for k, v in tu_skidl.items()}
    kq = KetQuaDangCau(dat=True)
    for ten in sorted(set(a) - set(b)):
        kq.net_thieu[ten] = a[ten]
    for ten in sorted(set(b) - set(a)):
        kq.net_them[ten] = b[ten]
    for ten in sorted(set(a) & set(b)):
        if a[ten] != b[ten]:
            kq.chan_lech[ten] = {
                "thieu_o_skidl": sorted(set(a[ten]) - set(b[ten])),
                "them_o_skidl": sorted(set(b[ten]) - set(a[ten]))}
    kq.dat = not (kq.net_thieu or kq.net_them or kq.chan_lech)
    kq.vi = _cau(kq)
    return kq


def _cau(kq: KetQuaDangCau) -> str:
    if kq.dat:
        return "Netlist từ tệp SKiDL khớp bản đồ mạch — không thừa, không thiếu một chân nào."
    p: list[str] = []
    if kq.net_them:
        # Đây là ca SCH14 và là loại lệch NGUY HIỂM nhất: một net không có trong bản đồ
        # nghĩa là mạch sắp được vẽ có một đường dây không ai quyết.
        p.append("Tệp SKiDL có net KHÔNG có trong bản đồ mạch: "
                 + "; ".join(f"{k} ({', '.join(v) or 'chưa nối gì'})"
                             for k, v in list(kq.net_them.items())[:5]))
    if kq.net_thieu:
        p.append("Bản đồ có net mà tệp SKiDL thiếu: "
                 + "; ".join(f"{k} ({', '.join(v) or 'chưa nối gì'})"
                             for k, v in list(kq.net_thieu.items())[:5]))
    if kq.chan_lech:
        p.append("Net lệch tập chân: "
                 + "; ".join(
                     f"{k} — thiếu {', '.join(v['thieu_o_skidl']) or 'không'} / "
                     f"thừa {', '.join(v['them_o_skidl']) or 'không'}"
                     for k, v in list(kq.chan_lech.items())[:5]))
    return ". ".join(p) + "."


# =========================================================================== viết .net
def viet_net(phang: dict[str, list[str]], *, part: dict[str, dict[str, str]],
             ten_mach: str = "eide") -> str:
    """Viết netlist KiCad (`.net`, S-expression) từ netlist phẳng.

    Viết tay thay vì gọi `kicad-cli` — quyết định 25/09 nói máy này không cài KiCad. Định
    dạng `.net` là S-expression phẳng và ổn định qua KiCad 6→9; đây là chỗ hiếm hoi mà viết
    tay rẻ hơn một phụ thuộc.

    KHÔNG ghi `tstamps` giả: KiCad dùng nó để khớp linh kiện khi cập nhật PCB, và một giá
    trị bịa sẽ làm lần cập nhật sau gán sai chân. Thiếu thì để KiCad tự sinh.
    """
    L = [f'(export (version "E")',
         f'  (design (source "{ten_mach}") (tool "EIDE"))',
         "  (components"]
    for ref in sorted(part):
        p = part[ref]
        L.append(f'    (comp (ref "{ref}")'
                 + (f' (value "{_esc(p.get("value", ""))}")' if p.get("value") else "")
                 + (f' (libsource (lib "{_esc(p.get("lib", ""))}") '
                    f'(part "{_esc(p.get("ten", ""))}"))' if p.get("lib") else "")
                 + ")")
    L.append("  )")
    L.append("  (nets")
    for i, ten in enumerate(sorted(phang), 1):
        L.append(f'    (net (code "{i}") (name "{_esc(ten)}")')
        for c in sorted(set(phang[ten]), key=_khoa):
            ref, _, chan = c.partition(".")
            L.append(f'      (node (ref "{ref}") (pin "{_esc(chan)}"))')
        L.append("    )")
    L += ["  )", ")", ""]
    return "\n".join(L)


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _khoa(c: str) -> tuple[str, int, str]:
    ref, _, so = c.partition(".")
    return (ref, int(so) if so.isdigit() else 10**9, so)
