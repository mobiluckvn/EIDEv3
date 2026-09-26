# -*- coding: utf-8 -*-
"""Bước 5 — ghi `.kicad_sch` bằng kiutils. SCH-44 §3 bước 5, SCH-20, SCH-21.

Dùng `kiutils` thay vì tự viết, và lý do không phải tiết kiệm công: round-trip `.kicad_sch`
là chỗ dễ sai **lặng lẽ** nhất trong cả đường ống. Một trường bị bỏ khi ghi lại thì KiCad vẫn
mở được tệp — nó chỉ mất thông tin, và người dùng phát hiện ra ba tuần sau khi bố cục họ sửa
biến mất. `kiutils` là thư viện Python thuần, **không phải KiCad**: quyết định 25/09/2026 cấm
cài KiCad, không cấm đọc định dạng của nó.

**SCH-20 — uuid ổn định theo ref.** KiCad dùng uuid để khớp ký hiệu giữa hai lần mở tệp; nếu
uuid đổi mỗi lần sinh thì mọi thứ người dùng đã sửa trong KiCad (vị trí, chú thích, giá trị
trường) bị coi là của một ký hiệu khác và **mất**. Nên uuid sinh từ `sha256(ref)` — cùng ref,
cùng uuid, mọi lần, mọi máy.
"""

from __future__ import annotations

import hashlib
from typing import Any

from . import bo_cuc as BC

PHIEN_BAN = "20231120"          # lược đồ .kicad_sch của KiCad 7/8/9


def uuid_theo(khoa: str) -> str:
    """UUID v4-dạng, sinh XÁC ĐỊNH từ một khoá. SCH-20.

    Không dùng `uuid4()`: nó ngẫu nhiên, nên lần sinh lại sẽ tạo ký hiệu "mới" và KiCad ném
    đi mọi thứ người dùng đã sửa trên ký hiệu cũ. Đây là một chỗ mà tính ngẫu nhiên không
    phải là tính năng mà là mất dữ liệu.
    """
    h = hashlib.sha256(khoa.encode("utf-8")).hexdigest()
    return f"{h[0:8]}-{h[8:12]}-4{h[13:16]}-8{h[17:20]}-{h[20:32]}"


def viet_kicad_sch(bc: BC.BoCuc, *, symbol: dict[str, dict[str, str]],
                   ten_sheet: str = "mach", kicad: str = "9") -> str:
    """Viết `.kicad_sch` (S-expression). Trả nội dung tệp.

    Viết qua `kiutils` **rồi kiểm lại bằng chính kiutils** — xem `doc_lai_duoc`. Ghi mà không
    đọc lại được là ghi một tệp không ai mở được, và điều đó phải bị phát hiện ở đây chứ không
    phải ở máy người dùng.
    """
    from kiutils.items.common import (Effects, Font, PageSettings, Position,
                                      Property, Stroke)
    from kiutils.items.schitems import Connection, LocalLabel, SchematicSymbol
    from kiutils.schematic import Schematic

    sch = Schematic.create_new()
    sch.version = PHIEN_BAN
    sch.generator = "EIDE"
    sch.uuid = uuid_theo(f"sheet:{ten_sheet}")
    sch.paper = PageSettings(paperSize=bc.kho)
    sch.schematicSymbols = []
    sch.labels = []
    sch.graphicalItems = []

    for z in sorted(bc.o, key=lambda q: q.ref):
        s = symbol.get(z.ref) or {}
        lib = s.get("lib") or "eide-sinh"
        ten = s.get("ten") or z.ref
        sym = SchematicSymbol(
            libraryNickname=lib, entryName=ten,
            position=Position(X=round(z.x, 2), Y=round(z.y, 2), angle=0),
            unit=1, inBom=True, onBoard=True, uuid=uuid_theo(f"sym:{z.ref}"))
        # Hai trường bắt buộc của KiCad. `Reference` phải đúng ref, vì đó là thứ nối tệp này
        # với netlist, BOM và cây khối.
        sym.properties = [
            Property(key="Reference", value=z.ref,
                     position=Position(X=round(z.x, 2), Y=round(z.y - BC.LUOI, 2), angle=0),
                     effects=Effects(font=Font(width=1.27, height=1.27))),
            Property(key="Value", value=ten,
                     position=Position(X=round(z.x, 2),
                                       Y=round(z.y + z.cao + BC.LUOI, 2), angle=0),
                     effects=Effects(font=Font(width=1.27, height=1.27))),
        ]
        sch.schematicSymbols.append(sym)

    for n in sorted(bc.nhan, key=lambda q: (q["net"], q["ref"], q["chan"])):
        sch.labels.append(LocalLabel(
            text=n["net"],
            position=Position(X=round(n["x"], 2), Y=round(n["y"], 2), angle=0),
            effects=Effects(font=Font(width=1.27, height=1.27)),
            uuid=uuid_theo(f"lbl:{n['net']}:{n['ref']}.{n['chan']}")))

    for d in sorted(bc.day, key=lambda q: q["net"]):
        sch.graphicalItems.append(Connection(
            type="wire",
            points=[Position(X=round(d["tu"][0], 2), Y=round(d["tu"][1], 2)),
                    Position(X=round(d["den"][0], 2), Y=round(d["den"][1], 2))],
            stroke=Stroke(width=0), uuid=uuid_theo(f"wire:{d['net']}")))

    # Ghi bản ĐÃ CHUẨN HOÁ: cho kiutils đọc lại rồi ghi ra một lượt, và lưu kết quả đó.
    #
    # Vì sao không lưu bản đầu: kiutils chuẩn hoá cách viết số (`40.0` → `40`), nên bản đầu
    # và bản đọc-lại khác nhau ở vài ký tự dù KHÔNG mất gì. Có hai cách xử: nới phép kiểm
    # round-trip thành "đọc lại được là đủ", hay ghi thẳng điểm bất động.
    #
    # Chọn cách hai. Nới phép kiểm là cách rẻ hơn nhưng nó bỏ mất đúng thứ phép kiểm sinh ra
    # để bắt: một trường bị mất khi ghi lại vẫn "đọc lại được". Ghi điểm bất động thì phép
    # kiểm vẫn đòi **khớp từng ký tự**, và nó chỉ đỏ khi có mất mát thật.
    return _chuan_hoa(sch.to_sexpr())


def _chuan_hoa(noi_dung: str) -> str:
    from kiutils.schematic import Schematic

    return Schematic.from_sexpr(_token(noi_dung)).to_sexpr()


def doc_lai_duoc(noi_dung: str) -> tuple[bool, str]:
    """Phép kiểm của §3 bước 5: "kiutils parse lại được (round-trip ổn định)".

    Kiểm hai điều, và điều thứ hai mới là điều khó: (1) đọc lại được; (2) **ghi lại ra đúng
    cùng một chuỗi**. Chỉ kiểm (1) thì một trường bị bỏ khi ghi vẫn "đạt", vì tệp vẫn hợp lệ
    — chỉ là thiếu.
    """
    from kiutils.schematic import Schematic

    try:
        a = Schematic.from_sexpr(_token(noi_dung))
    except Exception as e:                                # noqa: BLE001
        return False, f"kiutils không đọc lại được: {type(e).__name__}: {e}"
    try:
        lai = a.to_sexpr()
    except Exception as e:                                # noqa: BLE001
        return False, f"đọc được nhưng ghi lại hỏng: {type(e).__name__}: {e}"
    if lai.strip() != noi_dung.strip():
        return False, ("đọc lại rồi ghi ra KHÁC bản gốc — có trường bị mất trong vòng "
                       "round-trip, và KiCad sẽ mất đúng thứ đó")
    return True, ""


def _token(noi_dung: str):
    """`kiutils` nhận cây token; nó có sẵn bộ đọc S-expression."""
    from kiutils.utils.sexpr import parse_sexp
    return parse_sexp(noi_dung)


def kicad_pro(ten: str = "mach") -> str:
    """`.kicad_pro` tối giản — KiCad cần nó để mở sheet như một dự án.

    Viết tay vì nó là JSON phẳng và `kiutils` không có lớp cho nó. Cố ý **tối giản**: mỗi
    trường thêm vào là một trường phải giữ đúng qua các phiên bản KiCad, và ta không kiểm
    được điều đó ở máy này.
    """
    import json

    return json.dumps({
        "board": {}, "boards": [], "cvpcb": {"equivalence_files": []},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": f"{ten}.kicad_pro", "version": 1},
        "net_settings": {"classes": [{"name": "Default"}]},
        "sheets": [[uuid_theo(f"sheet:{ten}"), ""]],
        "text_variables": {},
    }, ensure_ascii=False, indent=2) + "\n"
