# -*- coding: utf-8 -*-
"""Đọc một tệp SKiDL thành netlist — bằng `ast`, KHÔNG chạy nó.

Vì sao tệp này tồn tại, và đây là chỗ quan trọng nhất của cả bước SCH-A:

SCH-44 bước 2 nói `sch.netlist` chạy SKiDL rồi so netlist sinh ra với netlist CKM, "lệch →
lỗi kèm diff, không đi tiếp". Phép so đó chỉ có nghĩa khi **hai đường sinh độc lập**. Máy
này không có `skidl` (và cài nó cũng cần thư viện ký hiệu KiCad, mà quyết định 25/09 nói
không cài KiCad) — nên nếu `sch.netlist` tự viết `.net` từ cây rồi so với `flatten(cây)`,
nó đang so chính mình với chính mình. Một phép kiểm như thế **luôn đạt**, và một phép kiểm
luôn đạt tệ hơn không có phép kiểm: nó tạo ra niềm tin không có cơ sở.

Đường độc lập thật ở đây là **đọc lại tệp SKiDL đã sinh**. Tệp đó là một hiện vật: mã sinh
nó, người có thể sửa nó, và SCH14 nói thẳng mô hình có thể "sinh net không có trong CKM".
Đọc nó rồi so với cây là kiểm đúng thứ cần kiểm.

Không chạy tệp vì hai lý do, và lý do thứ hai mới là lý do thật:
  1. chạy cần `skidl` + thư viện ký hiệu, không có;
  2. **chạy một tệp Python do mô hình có thể đã sửa là thực thi mã không kiểm soát.**
     `ast.parse` đọc cấu trúc mà không gọi gì — không import, không mở tệp, không mạng.

Đổi lại, nó chỉ hiểu ĐÚNG tập con mà `soan.py` sinh ra. Gặp gì không hiểu thì **nói ra**
trong `khong_hieu` chứ không bỏ qua — một dòng bị bỏ qua im lặng là một net biến mất khỏi
phép kiểm.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class MachSkidl:
    net: dict[str, list[str]] = field(default_factory=dict)      # tên net → [ref.chan]
    part: dict[str, dict[str, str]] = field(default_factory=dict)  # ref → {lib, ten, value}
    khong_hieu: list[str] = field(default_factory=list)
    loi_cu_phap: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"so_net": len(self.net), "so_part": len(self.part),
                "net": {k: sorted(v) for k, v in self.net.items()},
                "part": self.part, "khong_hieu": list(self.khong_hieu),
                "loi_cu_phap": self.loi_cu_phap}


def doc_skidl(nguon: str) -> MachSkidl:
    """Suy netlist từ nguồn SKiDL. Không ném — lỗi cú pháp trả trong `loi_cu_phap`."""
    m = MachSkidl()
    try:
        cay = ast.parse(nguon)
    except SyntaxError as e:
        m.loi_cu_phap = f"dòng {e.lineno}: {e.msg}"
        return m

    # Hai lượt: lượt một thu hàm khối và Part/Net theo từng phạm vi; lượt hai đi theo lời
    # gọi từ `mach()` xuống, mang theo net thật cho mỗi tham số. Phải hai lượt vì một hàm
    # khối được định nghĩa trước khi biết nó sẽ được gọi với net nào.
    ham: dict[str, ast.FunctionDef] = {}
    for nut in cay.body:
        if isinstance(nut, ast.FunctionDef):
            ham[nut.name] = nut
            continue
        # Câu lệnh ở CẤP NGOÀI CÙNG phải được nhắc tới. Ta không chạy tệp, nên mã chèn ở
        # đây vô hại về mặt thực thi — nhưng im lặng về nó thì người đọc báo cáo tưởng tệp
        # đúng như lúc sinh. Một tệp bị sửa phải THẤY ĐƯỢC là đã bị sửa.
        if isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Constant):
            continue                                   # docstring của tệp
        if isinstance(nut, (ast.Import, ast.ImportFrom)):
            ten = ", ".join(a.name for a in nut.names)
            if ten not in ("skidl",) and not (isinstance(nut, ast.ImportFrom)
                                              and nut.module == "skidl"):
                m.khong_hieu.append(f"cấp ngoài cùng: import lạ ({ten})")
            continue
        if isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Call) \
                and _ten_goi(nut.value) in ("mach", "generate_netlist", "ERC", "erc"):
            continue
        m.khong_hieu.append(
            f"cấp ngoài cùng: câu lệnh lạ {type(nut).__name__} (dòng {nut.lineno})")
    if "mach" not in ham:
        m.khong_hieu.append("không có hàm mach() — tệp không phải do sch.compose sinh")
        return m

    _di(m, ham, ham["mach"], {}, "mach", 0)
    return m


_TRAN_SAU = 12          # chống đệ quy vô hạn nếu tệp bị sửa thành hàm tự gọi


def _di(m: MachSkidl, ham: dict[str, ast.FunctionDef], f: ast.FunctionDef,
        rang: dict[str, str], ten_ham: str, sau: int) -> None:
    """Đi qua thân một hàm. `rang` là ánh xạ tên biến trong hàm → tên net THẬT."""
    if sau > _TRAN_SAU:
        m.khong_hieu.append(f"{ten_ham}: sâu quá {_TRAN_SAU} cấp — có vòng gọi hàm?")
        return
    cuc_bo = dict(rang)

    for nut in f.body:
        if isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Constant):
            continue                                   # docstring
        if isinstance(nut, ast.Pass):
            continue
        if isinstance(nut, ast.Assign) and len(nut.targets) == 1 \
                and isinstance(nut.targets[0], ast.Name) and isinstance(nut.value, ast.Call):
            ten_bien = nut.targets[0].id
            goi = _ten_goi(nut.value)
            if goi == "Net":
                ten_net = _chuoi(nut.value.args[0]) if nut.value.args else ten_bien
                cuc_bo[ten_bien] = ten_net
                m.net.setdefault(ten_net, [])
                continue
            if goi == "Part":
                ref, thong_tin = _doc_part(nut.value)
                if ref:
                    m.part[ref] = thong_tin
                    cuc_bo[ten_bien] = f"#part:{ref}"
                else:
                    m.khong_hieu.append(f"{ten_ham}: Part không có ref")
                continue
            m.khong_hieu.append(f"{ten_ham}: gán từ lời gọi lạ {goi or '?'}()")
            continue

        # `net += part[chân]`
        if isinstance(nut, ast.AugAssign) and isinstance(nut.op, ast.Add) \
                and isinstance(nut.target, ast.Name):
            ten_net = cuc_bo.get(nut.target.id)
            if ten_net is None:
                m.khong_hieu.append(f"{ten_ham}: nối vào net chưa khai {nut.target.id!r}")
                continue
            chan = _doc_chan(nut.value, cuc_bo)
            if chan is None:
                m.khong_hieu.append(f"{ten_ham}: vế phải của += không đọc được")
                continue
            m.net.setdefault(ten_net, []).append(chan)
            continue

        # lời gọi hàm khối: `khoi_x(a, b)`
        if isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Call):
            goi = _ten_goi(nut.value)
            if goi in ham:
                con = ham[goi]
                rang_con: dict[str, str] = {}
                ts = [a.arg for a in con.args.args]
                for i, tham in enumerate(ts):
                    if i >= len(nut.value.args):
                        m.khong_hieu.append(f"{ten_ham}: gọi {goi}() thiếu tham số {tham}")
                        continue
                    v = nut.value.args[i]
                    if isinstance(v, ast.Name) and v.id in cuc_bo:
                        rang_con[tham] = cuc_bo[v.id]
                    elif isinstance(v, ast.Call) and _ten_goi(v) == "Net":
                        ten_net = _chuoi(v.args[0]) if v.args else f"{goi}_{tham}"
                        rang_con[tham] = ten_net
                        m.net.setdefault(ten_net, [])
                    else:
                        m.khong_hieu.append(
                            f"{ten_ham}: tham số {tham} của {goi}() không đọc được")
                _di(m, ham, con, rang_con, goi, sau + 1)
                continue
            if goi in ("generate_netlist", "ERC", "erc"):
                continue
            m.khong_hieu.append(f"{ten_ham}: lời gọi lạ {goi or '?'}()")
            continue

        m.khong_hieu.append(f"{ten_ham}: câu lệnh lạ {type(nut).__name__}")


def _ten_goi(c: ast.Call) -> str:
    if isinstance(c.func, ast.Name):
        return c.func.id
    if isinstance(c.func, ast.Attribute):
        return c.func.attr
    return ""


def _chuoi(n: ast.expr) -> str:
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else ""


def _doc_part(c: ast.Call) -> tuple[str, dict[str, str]]:
    lib = _chuoi(c.args[0]) if len(c.args) > 0 else ""
    ten = _chuoi(c.args[1]) if len(c.args) > 1 else ""
    ref, value = "", ""
    for kw in c.keywords:
        if kw.arg == "ref":
            ref = _chuoi(kw.value)
        elif kw.arg == "value":
            value = _chuoi(kw.value)
    return ref, {"lib": lib, "ten": ten, "value": value}


def _doc_chan(n: ast.expr, cuc_bo: dict[str, str]) -> str | None:
    """`u1["27"]` → `U1.27`. Chỉ nhận dạng chỉ số hằng — chỉ số tính toán thì không đọc."""
    if not isinstance(n, ast.Subscript) or not isinstance(n.value, ast.Name):
        return None
    ma = cuc_bo.get(n.value.id, "")
    if not ma.startswith("#part:"):
        return None
    ref = ma.removeprefix("#part:")
    k = n.slice
    if isinstance(k, ast.Constant):
        return f"{ref}.{k.value}"
    return None
