# -*- coding: utf-8 -*-
"""Sheet phân cấp — EIDE-HIER-45 §7. Bước HIER-D. Ca HIER11, HIER13.

    "KiCad: style=hierarchical → mỗi khối (kind=block/subblock) một sheet (.kicad_sch riêng),
     Port của khối → hierarchical sheet pin, net 'lên cha' → hierarchical label trong sheet
     con; lá vẽ trong sheet của khối chứa nó."

Vì sao phân cấp không phải một kiểu trình bày khác mà là **một cách giữ đúng cấu trúc**: bản
`flat` của SCH-B đặt mọi ký hiệu lên một trang và biến Port thành nhãn, nên khi người dùng mở
tệp trong KiCad, **cây biến mất** — họ thấy một mạch phẳng và mọi thao tác của họ quay về dạng
phẳng. Sheet phân cấp giữ được cây qua vòng đi-về, và đó là điều kiện để `sch.import` dựng lại
cây thay vì chỉ dựng lại netlist.

`depth > 4` thì **tự chuyển** sang phân cấp và nói ra (HIER11): một cây sâu 5 cấp trên một
trang A3 là một trang không ai đọc được, và đó là lý do kỹ thuật chứ không phải khẩu vị.

Điều tệp này cố ý KHÔNG làm: không ghi `instances` cho từng sheet. KiCad tự dựng phần đó khi
mở dự án, và một `instancePath` viết tay sai sẽ làm nó **im lặng gán sai ký hiệu** giữa các
sheet — tệ hơn nhiều so với việc để KiCad tự sinh.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import bo_cuc as BC
from . import ghi as G

# Vị trí hộp sheet trên trang cha. Xếp thành hàng, cách nhau đủ để nhãn không đè.
RONG_SHEET = 38.1               # mm
CAO_MOI_PIN = 2.54
CAO_SHEET_TOI_THIEU = 20.32
CACH_SHEET = 12.7


def gia_tri_mong_doi(cay: Any, symbol: dict[str, dict[str, str]]) -> dict[str, str]:
    """`{ref: giá trị mà bên GHI sẽ viết vào trường Value}`.

    Một hàm, hai chỗ dùng: `_mot_sheet` ghi theo nó, `sch.import` so theo nó. Nếu hai bên tự
    tính riêng thì phép so lệch đúng ở chỗ khó thấy nhất — đo được: lá chưa có `gia_tri` thì
    bên ghi điền TÊN CHIP (KiCad cần trường Value có nội dung), còn bên so lấy giá trị rỗng
    trong kho, nên một lần người dùng sửa Value thật **không được phát hiện**.
    """
    ra: dict[str, str] = {}
    for nid, n in cay.nut.items():
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        s = symbol.get(ref) or {}
        ra[ref] = str(n["canonical"].get("gia_tri") or s.get("ten") or ref)
    return ra


def ten_tep_sheet(path: str) -> str:
    """`/board/mcu/xtal` → `mach_mcu_xtal.kicad_sch`. Phẳng, vì KiCad đặt mọi sheet cạnh nhau."""
    than = "_".join(x for x in (path or "").strip("/").split("/")[1:] if x)
    return f"mach_{than}.kicad_sch" if than else "mach.kicad_sch"


@dataclass(slots=True)
class GoiPhanCap:
    """Toàn bộ tệp của một lần ghi phân cấp: `{tên tệp tương đối: nội dung}`."""

    tep: dict[str, str] = field(default_factory=dict)
    goc: str = "mach.kicad_sch"
    so_sheet: int = 0
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"tep": sorted(self.tep), "goc": self.goc, "so_sheet": self.so_sheet,
                "canh_bao": list(self.canh_bao)}


def viet_phan_cap(cay: Any, *, symbol: dict[str, dict[str, str]],
                  kho: str = "A4") -> GoiPhanCap:
    """Ghi cây thành nhiều `.kicad_sch`: một cho gốc, một cho mỗi khối.

    Lá nằm trong sheet của **khối chứa nó** (§7), nên bố cục tính riêng cho từng sheet — đây là
    chỗ phân cấp trả lãi: mỗi trang chỉ có linh kiện của một khối, nên không còn chuyện 40 điện
    trở tràn khổ A3 như bản phẳng.
    """
    g = GoiPhanCap()
    if not cay.goc:
        g.canh_bao.append("Chưa có cây khối nào.")
        return g

    khoi = [nid for nid, n in cay.nut.items()
            if (n.get("kind") or "") in ("block", "subblock")]
    # Ngưỡng độ sâu thuộc lớp CÂY (`knowledge/cay.SAU_KHUYEN_NGHI`), không phải lớp bố cục:
    # nó là một tính chất của mô hình mạch, và nếu mỗi lớp giữ một con số riêng thì cảnh báo ở
    # hai chỗ sẽ nói hai điều khác nhau về cùng một cây.
    from ..knowledge.cay import SAU_KHUYEN_NGHI

    sau, ai = cay.sau_nhat()
    if sau > SAU_KHUYEN_NGHI:
        g.canh_bao.append(
            f"Cây sâu {sau} cấp ({ai}) — đã chuyển sang sheet phân cấp. Một cây sâu thế này "
            "trên một trang là một trang không ai đọc được.")

    # Sheet cho từng khối, đi từ SÂU ra ngoài để sheet con có tệp trước khi sheet cha trỏ tới.
    # Sâu ra ngoài: sheet con phải có tệp trước khi sheet cha trỏ tới nó.
    from ..knowledge.cay import do_sau

    for nid in sorted(khoi, key=lambda x: (-do_sau(cay.nut[x].get("path") or ""),
                                          cay.nut[x].get("path") or x)):
        g.tep[ten_tep_sheet(cay.nut[nid].get("path") or nid)] = _mot_sheet(
            cay, nid, symbol=symbol, kho=kho)
        g.so_sheet += 1

    g.tep["mach.kicad_sch"] = _mot_sheet(cay, cay.goc, symbol=symbol, kho=kho, la_goc=True)
    g.goc = "mach.kicad_sch"
    g.so_sheet += 1
    return g


def _mot_sheet(cay: Any, nid: str, *, symbol: dict[str, dict[str, str]], kho: str,
               la_goc: bool = False) -> str:
    """Một sheet: lá của khối này + hộp sheet cho khối con + nhãn phân cấp cho Port."""
    from kiutils.items.common import (Effects, Font, PageSettings, Position, Property,
                                      Stroke)
    from kiutils.items.schitems import (HierarchicalLabel, HierarchicalPin,
                                        HierarchicalSheet, SchematicSymbol)
    from kiutils.schematic import Schematic

    path = cay.nut[nid].get("path") or nid
    sch = Schematic.create_new()
    sch.version = G.PHIEN_BAN
    sch.generator = "EIDE"
    sch.uuid = G.uuid_theo(f"sheet:{path}")
    sch.paper = PageSettings(paperSize=kho)
    sch.schematicSymbols = []
    sch.labels = []
    sch.hierarchicalLabels = []
    sch.sheets = []
    sch.graphicalItems = []

    # 1) Nhãn phân cấp cho Port của CHÍNH khối này — đó là cách net trong sheet "lên cha".
    #    Sheet gốc không có Port (nó là biên ngoài cùng của mạch).
    if not la_goc:
        y = BC.LE
        for pid in sorted(cay.port_cua.get(nid, [])):
            p = cay.port[pid]
            sch.hierarchicalLabels.append(HierarchicalLabel(
                text=p["ten"], shape=_hinh_nhan(p["huong"]),
                position=Position(X=BC.LE, Y=round(y, 2), angle=0),
                effects=Effects(font=Font(width=1.27, height=1.27)),
                uuid=G.uuid_theo(f"hlbl:{path}.{p['ten']}")))
            y += BC.CACH_NHAN

    # 2) Lá của khối này, xếp bằng cùng thuật toán bố cục (một cột, cuộn theo trang).
    la = [x for x in sorted(cay.con_truc_tiep(nid)) if cay.nut[x].get("kind") == "leaf"]
    x0 = BC.LE + 50.8
    y0 = BC.LE
    for i, x in enumerate(la):
        n = cay.nut[x]
        ref = n["canonical"].get("ref") or n["ten"]
        s = symbol.get(ref) or {}
        cao = max(BC.CAO_TOI_THIEU,
                  BC.CAO_MOI_CHAN * ((len(cay.port_cua.get(x, [])) + 1) // 2 + 1))
        px, py = BC.tron(x0), BC.tron(y0)
        sym = SchematicSymbol(
            libraryNickname=s.get("lib") or "eide-sinh",
            entryName=s.get("ten") or ref,
            position=Position(X=px, Y=py, angle=0),
            unit=1, inBom=True, onBoard=True, uuid=G.uuid_theo(f"sym:{ref}"))
        sym.properties = [
            Property(key="Reference", value=ref,
                     position=Position(X=px, Y=BC.tron(py - BC.LUOI), angle=0),
                     effects=Effects(font=Font(width=1.27, height=1.27))),
            Property(key="Value", value=gia_tri_mong_doi(cay, symbol).get(ref, ref),
                     position=Position(X=px, Y=BC.tron(py + cao + BC.LUOI), angle=0),
                     effects=Effects(font=Font(width=1.27, height=1.27))),
        ]
        sch.schematicSymbols.append(sym)
        y0 += cao + BC.CACH_NHAU

    # 3) Hộp sheet cho từng khối con, kèm sheet pin = Port của con.
    sx = BC.LE + 50.8 + BC.RONG_IC + CACH_SHEET
    for con in sorted(cay.khoi_con(nid)):
        cpath = cay.nut[con].get("path") or con
        ports = [cay.port[p] for p in sorted(cay.port_cua.get(con, []))]
        cao = max(CAO_SHEET_TOI_THIEU, CAO_MOI_PIN * (len(ports) + 2))
        hs = HierarchicalSheet(
            position=Position(X=BC.tron(sx), Y=BC.tron(BC.LE), angle=0),
            width=RONG_SHEET, height=BC.tron(cao),
            stroke=Stroke(width=0.1524), uuid=G.uuid_theo(f"hsheet:{cpath}"))
        # `Sheetname` mang ĐOẠN PATH (mã khối), không mang tên hiển thị.
        #
        # Đo lần đầu: ghi tên hiển thị ("Vi điều khiển") làm `Sheetname` thì đọc lại ra path
        # `/board/Vi điều khiển` trong khi cây có `/board/MOD-MCU` — và `so_cay` báo **mọi**
        # khối đều "chỉ có ở tệp", tức một round-trip đúng bị kết luận là lệch hoàn toàn.
        #
        # `Sheetname` cũng là thành phần đường dẫn mà KiCad dùng trong netlist phân cấp, nên
        # mã khối là giá trị đúng về cả hai mặt. Tên hiển thị đi vào một Property riêng để
        # không mất — và nếu người dùng đổi `Sheetname` trong KiCad thì đó là một thay đổi
        # CẤU TRÚC, `sch.import` phải hỏi, chứ không được lặng lẽ khớp lại.
        doan = (cpath.rstrip("/").split("/") or [""])[-1]
        hs.sheetName = Property(key="Sheetname", value=doan or cpath,
                                position=Position(X=BC.tron(sx), Y=BC.tron(BC.LE - 1.27),
                                                  angle=0),
                                effects=Effects(font=Font(width=1.27, height=1.27)))
        hs.fileName = Property(key="Sheetfile", value=ten_tep_sheet(cpath),
                               position=Position(X=BC.tron(sx),
                                                 Y=BC.tron(BC.LE + cao + 1.27), angle=0),
                               effects=Effects(font=Font(width=1.27, height=1.27)))
        hs.properties = [Property(
            key="EIDE_ten", value=cay.nut[con]["ten"] or doan,
            position=Position(X=BC.tron(sx), Y=BC.tron(BC.LE - 3.81), angle=0),
            effects=Effects(font=Font(width=1.27, height=1.27)))]
        hs.pins = []
        py = BC.LE + CAO_MOI_PIN
        for p in ports:
            hs.pins.append(HierarchicalPin(
                name=p["ten"], connectionType=_hinh_nhan(p["huong"]),
                position=Position(X=BC.tron(sx), Y=BC.tron(py), angle=180),
                effects=Effects(font=Font(width=1.27, height=1.27)),
                uuid=G.uuid_theo(f"hpin:{cpath}.{p['ten']}")))
            py += CAO_MOI_PIN
        sch.sheets.append(hs)
        sx += RONG_SHEET + CACH_SHEET

    return G._chuan_hoa(sch.to_sexpr())


# §7 — hình nhãn KiCad theo hướng Port. `passive` không có hình riêng nên dùng `passive`.
_HINH = {"in": "input", "out": "output", "bidir": "bidirectional",
         "power_in": "input", "power_out": "output", "passive": "passive"}


def _hinh_nhan(huong: str) -> str:
    return _HINH.get(huong or "", "passive")


# =========================================================================== đọc về cây §7
@dataclass(slots=True)
class CayDocDuoc:
    """Cây đọc lại từ một gói `.kicad_sch` phân cấp."""

    khoi: dict[str, dict[str, Any]] = field(default_factory=dict)   # path → {ten, cha, port}
    la: dict[str, dict[str, Any]] = field(default_factory=dict)     # ref → {ten, gia_tri, path}
    nhan: dict[str, list[str]] = field(default_factory=dict)        # path → [tên nhãn]
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"so_khoi": len(self.khoi), "so_la": len(self.la),
                "khoi": self.khoi, "la": self.la, "nhan": self.nhan,
                "canh_bao": list(self.canh_bao)}


def doc_phan_cap(tep: dict[str, str], *, goc: str = "mach.kicad_sch") -> CayDocDuoc:
    """Gói `.kicad_sch` → cây. Sheet → Module, sheet pin → Port, nhãn phân cấp → net lên cha.

    Đi từ sheet gốc theo `Sheetfile`, nên cấu trúc đọc ra là cấu trúc **tệp nói**, không phải
    cấu trúc ta đoán. Một sheet được trỏ tới mà thiếu tệp thì nói ra chứ không bỏ qua — thiếu
    một sheet nghĩa là thiếu cả một khối của mạch.
    """
    ra = CayDocDuoc()
    if goc not in tep:
        ra.canh_bao.append(f"không có sheet gốc {goc} trong gói")
        return ra
    _doc_mot(ra, tep, goc, path="/board", cha="", sau=0)
    return ra


_TRAN_SAU = 12


def _doc_mot(ra: CayDocDuoc, tep: dict[str, str], ten_tep: str, *, path: str, cha: str,
             sau: int) -> None:
    if sau > _TRAN_SAU:
        ra.canh_bao.append(f"{ten_tep}: sâu quá {_TRAN_SAU} cấp — gói có vòng sheet?")
        return
    try:
        from kiutils.schematic import Schematic
        from kiutils.utils.sexpr import parse_sexp

        s = Schematic.from_sexpr(parse_sexp(tep[ten_tep]))
    except Exception as e:                                # noqa: BLE001
        ra.canh_bao.append(f"{ten_tep}: không đọc được ({type(e).__name__}: {e})")
        return

    ra.khoi.setdefault(path, {"ten": path.rstrip("/").split("/")[-1] or "board",
                              "cha": cha, "port": []})
    # Nhãn phân cấp trong sheet = Port của CHÍNH khối này, nhìn từ bên trong.
    nhan = [l.text for l in (s.hierarchicalLabels or [])]
    if nhan:
        ra.nhan[path] = sorted(nhan)
        ra.khoi[path]["port"] = sorted(nhan)

    for sym in (s.schematicSymbols or []):
        ref = next((p.value for p in (sym.properties or []) if p.key == "Reference"), "")
        val = next((p.value for p in (sym.properties or []) if p.key == "Value"), "")
        if not ref:
            ra.canh_bao.append(f"{ten_tep}: có ký hiệu không có Reference")
            continue
        ra.la[ref] = {"ten": sym.entryName, "gia_tri": val, "path": path}

    for hs in (s.sheets or []):
        ten_con = _gt(hs.sheetName) or "?"
        tep_con = _gt(hs.fileName)
        cpath = f"{path.rstrip('/')}/{ten_con}"
        pins = sorted(p.name for p in (hs.pins or []))
        hien = next((_gt(p) for p in (hs.properties or []) if p.key == "EIDE_ten"), "")
        ra.khoi[cpath] = {"ten": hien or ten_con, "ma": ten_con, "cha": path,
                          "port": pins}
        if not tep_con:
            ra.canh_bao.append(f"{ten_tep}: sheet {ten_con} không nói tệp của nó")
            continue
        if tep_con not in tep:
            ra.canh_bao.append(
                f"{ten_tep}: trỏ tới sheet {tep_con} mà gói không có tệp đó — thiếu một sheet "
                "nghĩa là thiếu cả một khối của mạch")
            continue
        _doc_mot(ra, tep, tep_con, path=cpath, cha=path, sau=sau + 1)


def _gt(p: Any) -> str:
    """`Property` của kiutils, hoặc chuỗi trần ở bản cũ."""
    if p is None:
        return ""
    return str(getattr(p, "value", p) or "")


def so_cay(doc: CayDocDuoc, cay: Any) -> dict[str, Any]:
    """So cây đọc từ tệp với cây trong kho, **theo path** (§7).

    Trả ba nhóm: khối chỉ có ở tệp, khối chỉ có ở kho, và khối lệch tập Port. Ba nhóm khác
    nhau vì việc phải làm khác nhau — và `sch.import` dựa vào đúng chỗ này để biết nên ghi một
    changeset bố cục, hay phải hỏi người.
    """
    o_kho = {n.get("path"): n for n in cay.nut.values()
             if (n.get("kind") or "") in ("board", "block", "subblock") and n.get("path")}
    port_kho = {p: sorted(cay.port[x]["ten"] for x in cay.port_cua.get(nid, []))
                for p, n in o_kho.items() for nid in [n["node_id"]]}
    chi_tep = sorted(set(doc.khoi) - set(o_kho))
    chi_kho = sorted(set(o_kho) - set(doc.khoi))
    lech: dict[str, dict[str, list[str]]] = {}
    for p in sorted(set(doc.khoi) & set(o_kho)):
        a, b = sorted(doc.khoi[p].get("port") or []), port_kho.get(p, [])
        if a != b:
            lech[p] = {"o_tep": a, "o_kho": b}
    return {"khop": not (chi_tep or chi_kho or lech),
            "khoi_chi_co_o_tep": chi_tep, "khoi_chi_co_o_kho": chi_kho,
            "port_lech": lech}
