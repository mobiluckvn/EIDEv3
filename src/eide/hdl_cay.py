# -*- coding: utf-8 -*-
"""Cây mô-đun của một thiết kế HDL — đọc từ quan hệ GỌI MÔ-ĐUN thật trong Verilog.

Đối xứng với `kien_truc.so_do_mo_dun`, chỗ dựng cây phần mềm từ `#include`. Ở đây cạnh đọc từ
**lời gọi mô-đun** (`bram ram ( … );`), vì đó là quan hệ thật của một thiết kế phần cứng.

Ba điều tệp này cố ý làm:

1. **Danh sách tệp lấy từ lệnh tổng hợp ĐÃ CHẠY**, không glob thư mục. Cây vẽ ra khi đó là cây
   của thiết kế **thật sự nằm trong chip**, không phải của mọi tệp `.v` còn sót trong dự án.
   Khác biệt ấy có thật: dự án RISC-V có `blinky.v` không nằm trong SoC nào, và `bai3/` giữ
   ba mô-đun đã ra khỏi phạm vi.

2. **Không có quan hệ thật thì không vẽ.** Giống luật của A5.6. Một sơ đồ toàn ô rời trông như
   một thiết kế không có cấu trúc, mà sự thật chỉ là bộ đọc không đọc được gì — hai điều ấy
   khác nhau và không được hiện ra giống nhau.

3. **Nhãn “chung / riêng / bên thứ ba” suy từ ĐƯỜNG DẪN**, và nói ra rằng nó suy từ đâu. Đó là
   thứ anh Công muốn thấy: nhìn vào biết đổi mô-đun nào thì ảnh hưởng tới đâu. Suy từ đường dẫn
   là một phép đoán, nhưng là phép đoán kiểm lại được bằng mắt — khác với một nhãn gán tay rồi
   không ai biết nó dựa vào gì.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# Từ khoá và cấu trúc KHÔNG phải lời gọi mô-đun, nhưng khớp cùng hình dạng
# `<tên> <tên> (`. Thiếu danh sách này thì `if (…)`, `always @(…)`, `case (…)` đều thành
# "mô-đun", và cây đầy những nút tên `if`.
_TU_KHOA = {
    "module", "endmodule", "input", "output", "inout", "wire", "reg", "logic", "integer",
    "real", "parameter", "localparam", "assign", "always", "always_ff", "always_comb",
    "always_latch", "initial", "begin", "end", "if", "else", "case", "casex", "casez",
    "endcase", "for", "while", "repeat", "forever", "generate", "endgenerate", "genvar",
    "function", "endfunction", "task", "endtask", "return", "posedge", "negedge", "signed",
    "unsigned", "automatic", "static", "const", "typedef", "struct", "union", "enum",
    "package", "endpackage", "import", "export", "interface", "endinterface", "modport",
    "default", "defparam", "specify", "endspecify", "table", "endtable", "primitive",
    "endprimitive", "and", "or", "nand", "nor", "xor", "xnor", "not", "buf", "bufif0",
    "bufif1", "notif0", "notif1", "pmos", "nmos", "cmos", "tran", "tranif0", "tranif1",
    "supply0", "supply1", "tri", "triand", "trior", "trireg", "wand", "wor", "time",
    "disable", "fork", "join", "wait", "assert", "assume", "cover", "property", "endproperty",
    "sequence", "endsequence", "bind", "unique", "priority", "do", "break", "continue",
    # `restrict property (…)` — từ khoá kiểm hình thức của SystemVerilog. PicoRV32 dùng nó ở
    # hai chỗ, và thiếu nó thì cây mô-đun có một nút tên `restrict` mang nhãn "KHÔNG thấy
    # khai ở tệp nào", trông đúng như một tệp bị thiếu.
    "restrict", "expect", "let", "checker", "endchecker", "randcase", "randsequence",
    "constraint", "rand", "randc", "class", "endclass", "extends", "virtual", "pure",
    "local", "protected", "this", "super", "new", "null", "extern", "context",
}

# `module <tên>` — chỗ một mô-đun bắt đầu.
_MO_DUN = re.compile(r"\bmodule\s+([A-Za-z_]\w*)", re.M)
_HET_MO_DUN = re.compile(r"\bendmodule\b")

# Lời gọi mô-đun: `<tên mô-đun> [#(tham số)] <tên thực thể> (`
#
# Bắt buộc có **tên thực thể** giữa hai dấu. Chính nó phân biệt một lời gọi với `if (…)`,
# `case (…)`, `$display(…)`: ba thứ ấy không có tên thực thể. Mẫu này vẫn lọt một số trường
# hợp (khai mảng, gọi hàm có kiểu trả về), nên danh sách từ khoá ở trên là chốt thứ hai.
# Giữa hai tên PHẢI có ranh giới — một khối tham số, hoặc ít nhất một khoảng trắng.
#
# Bản đầu viết `[ \t]*` ở giữa, tức cho phép **không có gì**. Nên `if (` khớp thành mô-đun
# `i` gọi thực thể `f`, `for (` thành `fo` + `r`, `case (` thành `cas` + `e`, `assert (`
# thành `asser` + `t`. Danh sách từ khoá không đỡ được, vì `i` và `fo` không phải từ khoá —
# chúng là **một nửa** của từ khoá. Cây mô-đun của PicoRV32 đầy những nút tên `i`, `cas`,
# `fo`, và mỗi nút ấy đều mang nhãn "KHÔNG thấy khai ở tệp nào" nên trông như thiếu tệp.
#
# Thấy ngay lần chạy đầu trên dự án thật. Không ca kiểm nào trên chuỗi tự soạn bắt được, vì
# tôi sẽ không nghĩ ra việc thử `if (`.
# Neo ở đầu dòng HOẶC sau dấu `;`. Dấu `;` kết thúc một câu lệnh, nên chỗ sau nó cũng là đầu
# một câu lệnh — `module soc; ram r (…); endmodule` viết trên một dòng là hợp lệ, và bản chỉ
# neo `^` bỏ qua hoàn toàn. Không nới rộng hơn thế: neo giữa biểu thức thì mọi lời gọi hàm
# trong một phép gán đều thành "mô-đun".
_GOI = re.compile(
    r"(?:^|;)[ \t]*([A-Za-z_]\w*)"              # tên mô-đun
    r"(?:[ \t]*#[ \t]*\([^;]*?\)[ \t]*|[ \t]+)"  # tham số, HOẶC ít nhất một khoảng trắng
    r"([A-Za-z_]\w*)[ \t]*"                     # tên thực thể
    r"(?:\[[^\]]*\][ \t]*)?"                    # mảng thực thể, hiếm nhưng hợp lệ
    r"\(",
    re.M)


def bo_chu_thich(s: str) -> str:
    """Bỏ chú thích và chuỗi, GIỮ NGUYÊN số dòng.

    Giữ số dòng vì bên gọi có thể muốn chỉ ra chỗ sai; và vì một `\\n` bị ăn mất sẽ dán hai
    dòng lại thành một, làm mẫu `^[ \\t]*` ở trên khớp sai chỗ.
    """
    def _giu_dong(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    s = re.sub(r"/\*.*?\*/", _giu_dong, s, flags=re.S)
    s = re.sub(r"//[^\n]*", _giu_dong, s)
    s = re.sub(r'"(?:[^"\\\n]|\\.)*"', _giu_dong, s)
    return s


def doc_mot_tep(noi_dung: str) -> dict[str, list[str]]:
    """`{tên mô-đun: [mô-đun nó gọi, theo thứ tự xuất hiện]}` cho MỘT tệp.

    Mô-đun khai mà không gọi gì thì vẫn có mặt, với danh sách rỗng — nó là một nút lá thật,
    khác với một mô-đun không được khai ở đâu cả.
    """
    s = bo_chu_thich(noi_dung)
    ra: dict[str, list[str]] = {}

    # Cắt theo từng `module … endmodule`. Không lồng nhau trong Verilog, nên cắt phẳng là đủ.
    for m in _MO_DUN.finditer(s):
        ten = m.group(1)
        if ten in _TU_KHOA:
            continue
        het = _HET_MO_DUN.search(s, m.end())
        than = s[m.end():het.start() if het else len(s)]
        goi: list[str] = []
        for g in _GOI.finditer(than):
            mo, _thuc_the = g.group(1), g.group(2)
            if mo in _TU_KHOA or mo == ten:
                continue
            if mo not in goi:
                goi.append(mo)
        ra[ten] = goi
    return ra


def nhom_cua(duong: str) -> str:
    """Nhãn “chung / bài N / bên thứ ba” suy từ đường dẫn.

    Quy ước của dự án FPGA này, và nó khớp đúng cấu trúc thư mục thật:
      `third_party/…` → bên thứ ba · `baiN/…` → riêng bài N · còn lại → chung.
    """
    p = Path(duong).as_posix()
    if "third_party/" in p or p.startswith("third_party"):
        return "bên thứ ba"
    m = re.search(r"(?:^|/)bai(\d+)/", "/" + p)
    if m:
        return f"bài {m.group(1)}"
    return "chung"


def doc_quan_he(goc: str | Path, duong: list[str]) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Đọc cả tập tệp. Trả `(quan hệ gọi, mô-đun nào khai ở tệp nào)`.

    Tệp đọc không được thì **vắng mặt**, không đoán — giống `_doc_phu_thuoc` của `kien_truc`.
    """
    goc = Path(goc)
    quan_he: dict[str, list[str]] = {}
    o_tep: dict[str, str] = {}
    for d in duong:
        p = Path(d)
        if not p.is_absolute():
            p = goc / d
        try:
            noi = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
        tuong_doi = p.as_posix()
        try:
            tuong_doi = p.resolve().relative_to(goc.resolve()).as_posix()
        except (ValueError, OSError):
            pass
        for ten, goi in doc_mot_tep(noi).items():
            quan_he[ten] = goi
            o_tep[ten] = tuong_doi
    return quan_he, o_tep


def dinh(quan_he: dict[str, list[str]]) -> list[str]:
    """Mô-đun không ai gọi — tức đỉnh của cây. Có thể nhiều (testbench, bài thử rời)."""
    bi_goi = {x for ds in quan_he.values() for x in ds}
    return sorted(t for t in quan_he if t not in bi_goi)


def tap_trong_cay(quan_he: dict[str, list[str]], dinh_goc: str,
                  *, sau_toi_da: int = 8) -> set[str]:
    """Mô-đun THẬT SỰ nằm trong cây tính từ `dinh_goc`.

    Tính từ chính quan hệ, không moi tên ra từ chuỗi cây đã in. Moi từ chuỗi thì mỗi lần đổi
    cách vẽ — thêm nhãn, đổi ký tự nhánh — là một lần phải sửa chỗ moi, và quên thì bảng lệch
    đi trong im lặng.

    Phân biệt này đáng một hàm riêng: một tệp `.v` nằm trong lệnh tổng hợp mà mô-đun của nó
    không ai gọi thì **không vào chip** — Yosys bỏ nó đi. Gộp hai loại vào một bảng thì người
    đọc tưởng thiết kế có thêm vài khối, và con số tài nguyên trông như không khớp.
    """
    ra: set[str] = set()

    def di(ten: str, sau: int) -> None:
        if ten in ra or sau > sau_toi_da:
            return
        ra.add(ten)
        for c in quan_he.get(ten) or []:
            di(c, sau + 1)

    di(dinh_goc, 0)
    return ra


def cay_van_ban(quan_he: dict[str, list[str]], o_tep: dict[str, str],
                dinh_goc: str, *, sau_toi_da: int = 8) -> list[str]:
    """Cây dạng chữ, mỗi dòng một nút, kèm nhãn nhóm và tệp khai.

    Mô-đun gọi lại chính một tổ tiên của nó thì dừng và ghi `(vòng)` — Verilog không cho đệ
    quy mô-đun, nên gặp vòng nghĩa là bộ đọc đã khớp sai, và nói ra rẻ hơn là treo.
    """
    ra: list[str] = []

    def di(ten: str, tien_to: str, noi: str, duong_di: tuple[str, ...]) -> None:
        phu = []
        if ten in o_tep:
            phu.append(nhom_cua(o_tep[ten]))
        if ten not in quan_he:
            phu.append("KHÔNG thấy khai ở tệp nào")
        if ten in duong_di:
            phu.append("vòng")
        ra.append(tien_to + noi + ten + (f"   ({' · '.join(phu)})" if phu else ""))

        if ten in duong_di or len(duong_di) >= sau_toi_da:
            return
        con = quan_he.get(ten) or []
        # Tiền tố cho CON: nối tiếp tiền tố của mình, cộng thanh dọc nếu mình chưa phải nút
        # cuối của cha — không có thanh ấy thì cây mất hết nhánh và mọi nút trông cùng một mức.
        tien_to_con = tien_to if noi == "" else tien_to + ("    " if noi.startswith("└") else "│   ")
        for i, c in enumerate(con):
            di(c, tien_to_con, "└── " if i == len(con) - 1 else "├── ", duong_di + (ten,))

    di(dinh_goc, "", "", ())
    return ra


# ------------------------------------------------------------- lấy từ lệnh tổng hợp đã chạy

_TEP_TRONG_LENH = re.compile(r"\S+\.s?v\b")
_DINH_TRONG_LENH = re.compile(r"-top\s+([A-Za-z_]\w*)")


def tu_lenh_tong_hop(lenh: list[str]) -> tuple[list[str], str]:
    """Rút `(danh sách tệp, tên mô-đun đỉnh)` từ lệnh `yosys` đã chạy.

    Vì sao đọc từ đây chứ không glob thư mục: cây vẽ ra phải là cây của thiết kế **thật sự đã
    tổng hợp**. Glob thì nó gộp cả tệp không nằm trong chip nào — dự án RISC-V có `blinky.v`
    rời và ba mô-đun của một bài đã ra khỏi phạm vi. Một cây gộp chúng vào trông như thiết kế
    có thêm ba khối không ai dùng.
    """
    noi = " ".join(str(x) for x in lenh)
    tep = _TEP_TRONG_LENH.findall(noi)
    m = _DINH_TRONG_LENH.search(noi)
    return tep, (m.group(1) if m else "")


def cay_tu_kho(store: Any, goc: str | Path) -> dict[str, Any]:
    """Cây mô-đun dựng từ hiện vật `build:hdl:synth`. Rỗng thì trả `{}`.

    Trả cả `vi_sao_rong` khi không dựng được, để khối trên tab nói ra lý do thay vì hiện một ô
    trống không giải thích gì.
    """
    a = store.get("build:hdl:synth")
    if not a:
        return {}
    c = a.get("canonical") or {}
    tep, dinh_goc = tu_lenh_tong_hop(c.get("lenh") or [])
    if not tep:
        return {"vi_sao_rong": "Hiện vật tổng hợp không ghi tệp nguồn nào."}
    quan_he, o_tep = doc_quan_he(goc, tep)
    if not quan_he:
        return {"vi_sao_rong": f"Không đọc được mô-đun nào trong {len(tep)} tệp nguồn."}
    if not dinh_goc:
        ds = dinh(quan_he)
        dinh_goc = ds[0] if ds else next(iter(quan_he))
    so_canh = sum(len(v) for v in quan_he.values())
    return {"quan_he": quan_he, "o_tep": o_tep, "dinh": dinh_goc,
            "so_tep": len(tep), "so_mo_dun": len(quan_he), "so_canh": so_canh,
            "cay": cay_van_ban(quan_he, o_tep, dinh_goc)}
