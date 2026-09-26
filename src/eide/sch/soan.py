# -*- coding: utf-8 -*-
"""Bước 1 — soạn tệp SKiDL từ cây khối. SCH-44 §3 bước 1, HIER-45 §7.

HIER-45 §7 **sửa** SCH-44 ở đây, và sửa đúng chỗ quan trọng:

    "mỗi khối → một hàm Python có tham số là các Port (Net/Bus objects); lá → Part; net
     cục bộ tạo trong hàm; gốc gọi các hàm và nối Port. Cây → cấu trúc gọi hàm 1-1"

SCH-44 bản đầu coi mỗi module là một *vùng trên một sheet*. Khác biệt không phải hình thức:
một hàm có tham số là một **hợp đồng kiểm được**, còn một vùng trên sheet thì không. Nếu
khối MCU cần ba Port thì hàm có ba tham số, và gọi thiếu một cái là lỗi cú pháp Python —
phát hiện trước khi có ai vẽ gì.

**Toạ độ, tên biến, thứ tự — tất cả do MÃ sinh.** Mô hình chỉ chọn `style` và gợi ý luồng
(§4 cuối). Cùng một cây phải ra **đúng một tệp**, mọi lần: SCH17 đòi chạy 5 lần cùng toạ độ,
và một tệp SKiDL đổi thứ tự dòng mỗi lần sinh thì mọi phép so sánh phía sau đều vô nghĩa.
"""

from __future__ import annotations

import re
from typing import Any

from ..knowledge import cay as C

# Bí danh Python hợp lệ cho một đường dẫn/ref. `/board/mcu` → `board_mcu`.
_XAU = re.compile(r"[^0-9A-Za-z_]")


def bien(s: str) -> str:
    x = _XAU.sub("_", (s or "").strip("/")).strip("_")
    x = re.sub(r"_+", "_", x)
    return x if x and not x[0].isdigit() else f"n_{x}"


def ham_khoi(path: str) -> str:
    return f"khoi_{bien(path)}"


def _lit(s: str) -> str:
    """Chuỗi Python một dòng, escape đủ. Tên net do người đặt, nên có thể chứa dấu nháy."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def soan_skidl(cay: C.Cay, *, style: str = "hierarchical",
               symbol: dict[str, dict[str, str]] | None = None) -> tuple[str, list[str]]:
    """Trả `(nguồn Python, cảnh báo)`. Không ném: thiếu gì thì nói ra trong cảnh báo.

    `symbol` là ánh xạ ref → {lib, ten} nếu `sch.symbols` đã chạy; chưa có thì để trống và
    tệp dùng `lib="?"`, kèm cảnh báo — một tệp SKiDL trỏ tới thư viện bịa sẽ chạy hỏng ở máy
    người khác, và đó là lỗi khó hiểu nhất để nhận.
    """
    if not cay.goc:
        return "", ["Chưa có cây khối nào để soạn."]
    canh_bao: list[str] = []
    sym = symbol or {}

    L: list[str] = [
        "# -*- coding: utf-8 -*-",
        '"""Mạch sinh từ Bản đồ tri thức mạch của EIDE — KHÔNG sửa tay tệp này.',
        "",
        "Tệp do mã sinh từ cây khối (EIDE-HIER-45 §7): mỗi khối là một hàm, tham số là các",
        "Port ở biên khối, lá là Part. Sửa tay ở đây sẽ bị ghi đè lần sinh sau; muốn đổi mạch",
        "thì đổi cây khối (ckm.*) rồi sinh lại.",
        '"""',
        "",
        "from skidl import Net, Part, generate_netlist, subcircuit",
        "",
    ]

    # Hàm cho từng khối, đi từ SÂU ra NGOÀI để hàm con được định nghĩa trước khi hàm cha gọi.
    for nid in sorted(_khoi_theo_sau(cay), key=lambda x: (-C.do_sau(cay.nut[x].get("path") or ""),
                                                          cay.nut[x].get("path") or "")):
        L += _ham(cay, nid, sym, canh_bao)

    # Gốc: tạo net ở phạm vi gốc rồi gọi từng khối con.
    goc = cay.goc
    L += [f"def mach():", f'    """{cay.nut[goc].get("path") or "/board"} — gốc của cây."""']
    tham: dict[str, str] = {}
    for net in sorted(cay.net_cua(goc)):
        n = cay.nut[net]
        v = bien(n["ten"])
        tham[net] = v
        L.append(f"    {v} = Net({_lit(n['ten'])})")
    if not tham:
        L.append("    pass  # gốc chưa có net nào")
    for con in sorted(cay.khoi_con(goc)):
        goi = _loi_goi(cay, con, tham, canh_bao)
        L.append(f"    {goi}")
    for la in sorted(x for x in cay.con_truc_tiep(goc)
                     if cay.nut[x].get("kind") == "leaf"):
        L += ["    " + d for d in _part_va_noi(cay, la, tham, sym, canh_bao)]
    L += ["", "", "mach()", "generate_netlist()", ""]
    return "\n".join(L), canh_bao


def _khoi_theo_sau(cay: C.Cay) -> list[str]:
    return [nid for nid, n in cay.nut.items()
            if (n.get("kind") or "") in ("block", "subblock")]


def _ham(cay: C.Cay, nid: str, sym: dict[str, dict[str, str]],
         canh_bao: list[str]) -> list[str]:
    """Một khối → một hàm `@subcircuit`, tham số là Port của nó."""
    n = cay.nut[nid]
    path = n.get("path") or nid
    ports = [cay.port[p] for p in cay.port_cua.get(nid, [])]
    if not ports:
        canh_bao.append(f"Khối {path} chưa khai Port nào, nên hàm của nó không nhận gì — "
                        "bên ngoài không nối được vào khối này.")
    ts = ", ".join(bien(p["ten"]) for p in ports)

    L = ["@subcircuit",
         f"def {ham_khoi(path)}({ts}):",
         f'    """{path} — {n["ten"]}."""']
    # Net cục bộ: net thuộc phạm vi khối này. Net nào nối vào một Port thì KHÔNG tạo biến
    # mới — nó chính là tham số đó, vì `flatten` hợp nhất hai bên Port thành một net điện.
    tham: dict[str, str] = {}
    for net in sorted(cay.net_cua(nid)):
        qua = _port_cua_khoi_nay(cay, net, nid)
        if qua is not None:
            tham[net] = bien(cay.port[qua]["ten"])
            continue
        v = bien(cay.nut[net]["ten"])
        tham[net] = v
        L.append(f"    {v} = Net({_lit(cay.nut[net]['ten'])})")

    than: list[str] = []
    for con in sorted(cay.khoi_con(nid)):
        than.append("    " + _loi_goi(cay, con, tham, canh_bao))
    for la in sorted(x for x in cay.con_truc_tiep(nid)
                     if cay.nut[x].get("kind") == "leaf"):
        than += ["    " + d for d in _part_va_noi(cay, la, tham, sym, canh_bao)]
    if not than:
        than = ["    pass  # khối chưa có gì bên trong"]
    return L + than + ["", ""]


def _port_cua_khoi_nay(cay: C.Cay, net_id: str, nid: str) -> str | None:
    """Net này có nối vào Port "lên cha" của chính khối đang xét không?"""
    for pid in cay.noi.get(net_id, []):
        if cay.port.get(pid, {}).get("module_id") == nid:
            return pid
    return None


def _loi_goi(cay: C.Cay, con: str, tham: dict[str, str], canh_bao: list[str]) -> str:
    """Lời gọi hàm khối con: mỗi Port của con nhận net ở khối cha nối vào Port đó."""
    path = cay.nut[con].get("path") or con
    dau: list[str] = []
    for pid in cay.port_cua.get(con, []):
        p = cay.port[pid]
        net = next((x for x in cay.noi_port.get(pid, []) if x in tham), None)
        if net is None:
            # Port chưa nối ở cấp này: truyền một net mới có tên theo Port, và NÓI RA. Đây
            # là một chân lơ lửng — hợp lệ về cú pháp, gần như luôn là thiếu sót về mạch.
            canh_bao.append(f"Port {p['ten']} của {path} chưa nối net nào ở khối cha — "
                            "sinh một net rời để tệp chạy được, nhưng mạch thì đang hở.")
            dau.append(f"Net({_lit(p['ten'] + '_chua_noi')})")
        else:
            dau.append(tham[net])
    return f"{ham_khoi(path)}({', '.join(dau)})"


def _part_va_noi(cay: C.Cay, la: str, tham: dict[str, str],
                 sym: dict[str, dict[str, str]], canh_bao: list[str]) -> list[str]:
    """Một lá → một `Part`, rồi nối từng chân vào net.

    Chân dùng ở đây **chỉ** là chân có Port, và Port của lá sinh từ Fact pinout — nên kỷ
    luật "không bịa chân" của bước CKM đi thẳng vào tệp SKiDL mà không cần kiểm lại.
    """
    n = cay.nut[la]
    ref = n["canonical"].get("ref") or n["ten"]
    v = bien(ref)
    s = sym.get(ref) or {}
    lib, ten = s.get("lib", ""), s.get("ten", "")
    if not lib:
        canh_bao.append(f"{ref} chưa có ký hiệu (symbol) — tệp ghi lib='?' và sẽ KHÔNG chạy "
                        "được cho tới khi gọi sch.symbols.")
        lib, ten = "?", n["canonical"].get("ten") or ref
    gt = n["canonical"].get("gia_tri") or n["canonical"].get("ten") or ""
    L = [f"{v} = Part({_lit(lib)}, {_lit(ten)}, ref={_lit(ref)}, value={_lit(gt)})"]
    for pid in cay.port_cua.get(la, []):
        p = cay.port[pid]
        chan = p.get("chan") or p["ten"]
        net = next((x for x in cay.noi_port.get(pid, []) if x in tham), None)
        if net is None:
            continue          # chân không nối gì trong phạm vi này — không bịa net
        L.append(f"{tham[net]} += {v}[{_lit(chan)}]")
    return L
