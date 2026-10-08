# -*- coding: utf-8 -*-
"""Bộ kiểm có ĐO GÌ KHÔNG — đo bằng cách phá mã sản phẩm rồi xem nó có đỏ lên không.

Vì sao năng lực này tồn tại, đo được trên phiên FreeRTOS ngày 28/09/2026:

Tác tử được giao *"tự viết kế hoạch kiểm thử, tự viết ca kiểm, tự chạy"*. Nó viết
`test/test_ui.c` với **sáu ca kiểm**, mỗi ca có tên, có thông điệp, có ngưỡng, và in kết quả
ra JSON. Ba phép kiểm đầu của tôi — *có hiện vật không · ca có ngưỡng không · có ô đỏ không* —
đều **xanh**.

Rồi tôi phá `firmware/ui.c` thật (đổi mọi toạ độ nút thành `99999`) và chạy lại:

    ĐẠT  TC-01 … ĐẠT  TC-06          ← cả sáu ca, không ca nào nhúc nhích

Tệp test **tự định nghĩa lại** `UI_ToggleScreen` và `UI_HandleTouch` ngay trong chính nó,
không nạp `ui.c`. Nó đang kiểm một bản sao của logic viết trong tệp test, nên nó sẽ xanh mãi
mãi dù sản phẩm làm gì.

**Cấu trúc đúng không chứng minh được nó đo gì.** Một bộ kiểm có đủ tên ca, đủ ngưỡng, đủ
báo cáo JSON, mà không chạm tới mã sản phẩm, thì tệ hơn không có bộ kiểm nào: nó biến một
chỗ chưa được kiểm thành một ô xanh, và ô xanh thì dừng việc tìm lỗi.

Cách đo duy nhất đáng tin là **đột biến**: sửa một chỗ trong mã sản phẩm sao cho hành vi phải
đổi, rồi chạy lại bộ kiểm. Không ca nào đỏ ⇒ bộ kiểm không nhìn thấy chỗ ấy.

## Chỗ mô-đun này KHÔNG làm, và nói ra

Đây **không** phải mutation testing đầy đủ. Nó không sinh hàng trăm đột biến, không tính
mutation score, không phân biệt đột biến tương đương. Nó trả lời đúng một câu nhị phân cho mỗi
tệp: *"bộ kiểm có thấy tệp này không?"* — và đó là câu mà một ô xanh giả cần để bị lật tẩy.
Một bộ kiểm qua được phép này vẫn có thể rất nông; nó chỉ chứng minh mình **không rỗng**.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Các phép đột biến, theo thứ tự ưu tiên. Mỗi cái phải đổi HÀNH VI, không chỉ đổi văn bản.
#
# Không đụng vào chuỗi và chú thích: đổi một chữ trong `printf` thì hành vi không đổi, và
# một đột biến không đổi hành vi mà bộ kiểm "không bắt được" là một cáo buộc sai.
_PHEP: tuple[tuple[str, str, str], ...] = (
    (r"(?<![\w.])(\d{2,})(?![\w.])", "99999", "đổi mọi hằng số từ hai chữ số"),
    (r"([^<>=!])(==)([^=])", r"\1!=\3", "đảo phép so sánh bằng"),
    (r"([^<=])(<)([^<=])", r"\1>\3", "đảo phép so sánh nhỏ hơn"),
    # Nhìn cả hai phía: `i++` có dấu `+` thứ hai mà phía trước không phải chữ cái, nên một
    # lượt nhìn-sau chỉ chặn `\w` vẫn cho nó lọt và sinh ra `i+-` — mã không dịch được. Mà
    # "không dịch được" rất dễ bị đọc thành "bộ kiểm bắt được", tức là một ô xanh giả ngay
    # trong chính công cụ đi vạch mặt ô xanh giả.
    (r"(?<![-+=<>!*/%&|^])(\+)(?![+=])", "-", "đổi cộng thành trừ"),
    # M4-04 — năm phép THÊM, đặt ở CUỐI bảng.
    #
    # Cuối, không chen vào giữa: bốn phép trên được gọi theo **chỉ số** ở nhiều ca kiểm
    # (`dot_bien_van_ban(ma, 1)`), và `do_do_nhay` chế độ theo tệp chỉ dùng `toi_da_phep=3`
    # phép đầu. Thêm vào cuối thì cả hai chuyện ấy không đổi một ly.
    #
    # Phép đầu trong nhóm này là ca DANH-GIA §2.2: `*(--sp) = 0xFFFFFFFDU;` là `EXC_RETURN`
    # của ARM, sai giá trị ấy thì bo nổ `IBUSERR` ngay chu kỳ đầu — và bảng cũ KHÔNG có phép
    # nào chạm tới nó, vì `(?<![\w.])(\d{2,})(?![\w.])` bị chặn bởi chữ `x` đứng trước.
    (r"0[xX][0-9A-Fa-f]+", "0x0", "đổi hằng hex thành 0x0"),
    (r"&&", "||", "đổi AND logic thành OR logic"),
    (r">=", ">", "siết phép so sánh lớn-hơn-hoặc-bằng"),
    # `return <biểu thức>;` → `return 0;`. Bỏ qua `return;` và `return 0;` (không đổi gì).
    (r"\breturn\s+(?!0\s*;)[^;{}]+;", "return 0;", "đổi giá trị trả về thành 0"),
    # Một câu lệnh gọi hàm đứng RIÊNG một dòng — xoá nó đi. Đây là phép bắt được chuyện
    # "gọi hàm phụ mà không ai kiểm nó có được gọi hay không": bộ kiểm chỉ xem giá trị trả
    # về thì xoá cả lời gọi `WDT_Reset();` nó vẫn xanh.
    (r"(?m)^([ \t]*)[A-Za-z_]\w*\s*\([^;{}]*\)\s*;[ \t]*$", r"\1;", "xoá một lời gọi hàm"),
)

# M3-13 — phép đột biến cho VERILOG. Bảng kiểu C không dùng được: `==` còn khớp, nhưng
# `posedge` (sườn lên), `&` trên bus, và hằng `4'd10` thì không phép nào chạm tới — mà đó
# đúng là những chỗ một testbench nông sẽ không canh.
#
# Mỗi phép đổi HÀNH VI của phần cứng, không chỉ đổi văn bản:
#   đảo `if`        — nhánh điều khiển chạy ngược
#   `&` → `|`       — phép logic trên bus ra kết quả khác
#   hằng `'d`       — ngưỡng đếm/so sánh lệch một
#   `posedge`→`negedge` — chốt ở sườn kia của xung nhịp, đúng loại lỗi khó thấy nhất
#   `==` → `!=`     — điều kiện so sánh đảo
PHEP_VERILOG: tuple[tuple[str, Any, str], ...] = (
    (r"\bif\s*\(([^()]*)\)", r"if (!(\1))", "đảo điều kiện if"),
    (r"(?<![&|])\s&\s(?![&|])", " | ", "đổi AND bit thành OR bit"),
    (r"\b(\d+)'([dD])(\d+)\b", lambda m: f"{m.group(1)}'{m.group(2)}{int(m.group(3)) + 1}",
     "đổi hằng số thập phân (+1)"),
    (r"\bposedge\b", "negedge", "đổi sườn lên thành sườn xuống"),
    (r"([^<>=!])(==)([^=])", r"\1!=\3", "đảo phép so sánh bằng"),
)

# Vùng KHÔNG đột biến: chuỗi ký tự, chú thích, và dòng `#include`. Thay trong đó là đổi văn
# bản chứ không đổi hành vi.
_BO_QUA = re.compile(r'"(?:[^"\\]|\\.)*"' r"|'(?:[^'\\]|\\.)*'"
                     r"|//[^\n]*" r"|/\*.*?\*/" r"|^\s*#\s*include[^\n]*",
                     re.S | re.M)


def dot_bien_van_ban(ma: str, phep: int = 0,
                     bang: tuple[tuple[str, Any, str], ...] = _PHEP
                     ) -> tuple[str, str, int]:
    """Áp một phép đột biến lên mã nguồn. Trả `(mã mới, mô tả, số chỗ đổi)`.

    `bang` mặc định là bảng kiểu C — `test.sensitivity` cho firmware đang dùng nó và không
    được đổi một ly. Truyền `PHEP_VERILOG` để đo testbench HDL.
    """
    mau, thay, mo_ta = bang[phep % len(bang)]
    than, giu = _che(ma)
    moi, n = re.subn(mau, thay, than)
    return _bo_che(moi, giu), mo_ta, n


def _che(ma: str) -> tuple[str, list[str]]:
    """Thay chuỗi, chú thích, dòng `#include` bằng chỗ giữ — xem `_ma_cho` cho lý do chữ hoa."""
    giu: list[str] = []

    def _cat(m: re.Match[str]) -> str:
        giu.append(m.group(0))
        return f"\x00{_ma_cho(len(giu) - 1)}\x00"

    return _BO_QUA.sub(_cat, ma), giu


def _bo_che(than: str, giu: list[str]) -> str:
    return re.sub(r"\x00([A-Z]+)\x00", lambda m: giu[_so_cho(m.group(1))], than)


# M4-05 — mã chỗ giữ viết bằng CHỮ HOA, không bằng chữ số.
#
# Bản cũ dùng `\x00{i}\x00` với `i` là số thứ tự. Phép đột biến đầu của bảng C là
# `(?<![\w.])(\d{2,})(?![\w.])` → `99999`, và `\x00` không nằm trong `[\w.]` — nên khi một tệp
# có **từ 10 chuỗi/chú thích trở lên**, chính con số của chỗ giữ bị đột biến thành `99999`, và
# bước phục hồi `giu[99999]` ném `IndexError`.
#
# Đo được ngày 08/10/2026: `test.sensitivity` **đổ** trên cả ba dự án firmware thật trong
# `du-lieu/` (rtos-sinhvien, stm32f469-freertos, thu-nghiem-g6) — mọi tệp firmware thật đều có
# hơn 10 chú thích. Nghĩa là đường đo độ nhạy cho C chưa bao giờ chạy nổi trên một tệp thật;
# các con số cũ đều đến từ tệp nhỏ do ca kiểm tự dựng.
#
# Chữ hoa an toàn với cả hai bảng: bảng C chỉ khớp số, `==`, `<`, `+`; bảng Verilog khớp `if`,
# `&`, hằng `'d`, `posedge`, `==` — không phép nào chạm tới `[A-Z]+`.
def _ma_cho(i: int) -> str:
    ra = ""
    i += 1
    while i:
        i, du = divmod(i - 1, 26)
        ra = chr(ord("A") + du) + ra
    return ra


def _so_cho(s: str) -> int:
    n = 0
    for c in s:
        n = n * 26 + (ord(c) - ord("A") + 1)
    return n - 1



# ============================= M4-04: đột biến TỪNG VỊ TRÍ, và một con số thay cho một câu
#
# `dot_bien_van_ban` dùng `re.subn`, nên nó đổi **mọi** chỗ khớp cùng lúc: "đảo mọi phép `==`
# trong tệp" là một đột biến duy nhất. Một bộ kiểm canh được **một** trong mười chỗ ấy là đủ
# để cả tệp thành `thay` — "bộ kiểm BẮT ĐƯỢC" — và chín chỗ kia không ai hỏi tới.
#
# `liet_ke_dot_bien` + `ap_mot` tách chuyện ấy ra: mỗi vị trí là một đột biến riêng, có số
# dòng, có chữ trước và chữ sau. Từ đó mới dựng được một con số (điểm đột biến) và — quan
# trọng hơn con số — một **danh sách những dòng bộ kiểm không canh**.


@dataclass(frozen=True, slots=True)
class DotBien:
    """Một đột biến ở MỘT vị trí. `thu_tu` là chỗ thứ mấy mà phép `phep` khớp được."""

    phep: int
    thu_tu: int
    mo_ta: str
    dong: int
    truoc: str
    sau: str

    def to_dict(self) -> dict[str, Any]:
        return {"phep": self.mo_ta, "dong": self.dong,
                "truoc": self.truoc, "sau": self.sau}


def _khac_o_dau(a: str, b: str) -> tuple[int, str, str]:
    """Đoạn đầu tiên khác nhau giữa hai bản, theo toạ độ của `a`.

    Đi từ hai đầu vào giữa, nên nó trả đúng đoạn đã đổi chứ không trả cả phần đuôi. Dùng toạ
    độ của **mã gốc**, vì số dòng phải là số dòng người mở tệp ra sẽ thấy — không phải số
    dòng của bản đã che chuỗi và chú thích.
    """
    i = 0
    while i < len(a) and i < len(b) and a[i] == b[i]:
        i += 1
    j, k = len(a), len(b)
    while j > i and k > i and a[j - 1] == b[k - 1]:
        j -= 1
        k -= 1
    return i, a[i:j], b[i:k]


def _che_co_moc(ma: str) -> tuple[str, list[str], list[tuple[int, int, int, int, bool]]]:
    """Như `_che`, nhưng ghi lại BẢN ĐỒ đoạn: `(than_dau, than_cuoi, ma_dau, ma_cuoi, la_giu)`.

    Cần bản đồ vì toạ độ trong bản đã che KHÔNG trùng toạ độ trong mã gốc: một chú thích
    `/* … */` dài ba dòng co lại thành một chỗ giữ không có dòng mới nào. Thiếu bản đồ thì số
    dòng báo ra lệch đúng ở những tệp có nhiều chú thích — tức là mọi tệp thật.
    """
    giu: list[str] = []
    doan: list[tuple[int, int, int, int, bool]] = []
    phan: list[str] = []
    vi_ma = vi_than = 0
    for m in _BO_QUA.finditer(ma):
        if m.start() > vi_ma:
            chu = ma[vi_ma:m.start()]
            phan.append(chu)
            doan.append((vi_than, vi_than + len(chu), vi_ma, m.start(), False))
            vi_than += len(chu)
        giu.append(m.group(0))
        the = f"\x00{_ma_cho(len(giu) - 1)}\x00"
        phan.append(the)
        doan.append((vi_than, vi_than + len(the), m.start(), m.end(), True))
        vi_than += len(the)
        vi_ma = m.end()
    if vi_ma < len(ma):
        chu = ma[vi_ma:]
        phan.append(chu)
        doan.append((vi_than, vi_than + len(chu), vi_ma, len(ma), False))
    return "".join(phan), giu, doan


def _ve_ma_goc(doan: list[tuple[int, int, int, int, bool]], vi: int, *, cuoi: bool) -> int:
    """Toạ độ trong bản đã che → toạ độ trong mã gốc. `cuoi`: lấy mép phải của chỗ giữ."""
    import bisect

    k = bisect.bisect_right([d[0] for d in doan], vi) - 1
    if k < 0:
        return 0
    t_dau, t_cuoi, m_dau, m_cuoi, la_giu = doan[k]
    if la_giu:
        return m_cuoi if cuoi else m_dau
    return min(m_dau + (vi - t_dau), m_cuoi)


def _dong_thu(chu: str, n: int) -> str:
    """Dòng thứ `n` (1-based), đã cắt khoảng trắng hai đầu và giới hạn 120 ký tự."""
    ds = chu.splitlines()
    return ds[n - 1].strip()[:120] if 0 < n <= len(ds) else ""


def liet_ke_dot_bien(ma: str, bang: tuple[tuple[str, Any, str], ...] = _PHEP,
                    *, toi_da: int | None = None, seed: int = 0) -> list[DotBien]:
    """Mọi đột biến áp được lên `ma`, mỗi vị trí một mục. `toi_da` thì lấy mẫu tất định.

    Bỏ qua mục không đổi gì: một đột biến không đổi hành vi mà bộ kiểm "không bắt được" là
    một cáo buộc sai — cùng lý do `_BO_QUA` tồn tại.

    **Không dựng cả tệp cho mỗi chỗ khớp.** Bản đầu của hàm này làm thế, và đo được ngày
    09/10/2026 trên một tệp thật: `du-lieu/rtos-sinhvien/firmware/logo_ptit.c` là 720 KB
    bitmap với **57 600** chỗ khớp phép hằng hex. Dựng một bản 720 KB rồi chạy một lượt regex
    bỏ che cho **từng** chỗ là khoảng 41 GB việc chuỗi — phép đo treo, không đổ, nên nó trông
    như một lượt chạy lâu chứ không như một lỗi.

    Nay chỗ khớp được liệt kê **rẻ** (chỉ vị trí), lấy mẫu TRƯỚC, rồi mới dựng phần chi tiết
    cho những mục còn lại — và số dòng tra qua bản đồ đoạn chứ không qua một phép so hai bản.
    """
    import bisect
    import random

    than, giu, doan = _che_co_moc(ma)
    # Bước 1 — chỉ VỊ TRÍ. Không dựng chuỗi nào ở đây.
    cho: list[tuple[int, int, re.Match[str]]] = []
    for i, (mau, _thay, _mo_ta) in enumerate(bang):
        for k, m in enumerate(re.finditer(mau, than)):
            cho.append((i, k, m))
    if toi_da is not None and len(cho) > toi_da:
        # Tất định nhờ `seed`, không nhờ một bước sắp xếp trước. Bản đầu của tôi sắp xếp cả
        # trước và sau khi lấy mẫu; phép phá cho thấy bước TRƯỚC không đổi gì đo được, nên nó
        # là một dòng không ca kiểm nào canh — bỏ đi (bài học M4-19). Bước SAU thì giữ: nó
        # làm thứ tự danh sách trả về theo vị trí trong tệp, tức theo thứ tự người đọc.
        cho = sorted(random.Random(seed).sample(cho, toi_da),
                     key=lambda x: (x[2].start(), x[0], x[1]))

    dong_moi = [j for j, c in enumerate(ma) if c == "\n"]
    dong_cua_ma = ma.splitlines()
    ra: list[DotBien] = []
    for i, k, m in cho:
        mau, thay, mo_ta = bang[i]
        rep = m.expand(thay) if isinstance(thay, str) else thay(m)
        o1 = _ve_ma_goc(doan, m.start(), cuoi=False)
        o2 = _ve_ma_goc(doan, m.end(), cuoi=True)
        truoc_frag, sau_frag = ma[o1:o2], _bo_che(rep, giu)
        if truoc_frag == sau_frag:
            continue
        dong = bisect.bisect_right(dong_moi, o1) + 1
        # `truoc`/`sau` là CẢ DÒNG, không phải đoạn khác nhau nhỏ nhất: đoạn nhỏ nhất của
        # `x==y` → `x!=y` là đúng một ký tự. Đúng về dữ liệu và vô dụng trên một bản báo cáo.
        cu_dong = dong_cua_ma[dong - 1] if 0 < dong <= len(dong_cua_ma) else ""
        ra.append(DotBien(phep=i, thu_tu=k, mo_ta=mo_ta, dong=dong,
                          truoc=cu_dong.strip()[:120],
                          sau=cu_dong.replace(truoc_frag, sau_frag, 1).strip()[:120]
                          if truoc_frag in cu_dong else sau_frag.strip()[:120]))
    return ra


def ap_mot(ma: str, db: DotBien,
           bang: tuple[tuple[str, Any, str], ...] = _PHEP) -> str:
    """Áp ĐÚNG MỘT đột biến. Dựng lại từ `(phep, thu_tu)` chứ không giữ sẵn cả bản đã phá.

    Giữ sẵn thì một tệp 50 KB với 30 đột biến là 1,5 MB nằm trong bộ nhớ cho một thứ tính lại
    được trong một phần nghìn giây.
    """
    mau, thay, _ = bang[db.phep % len(bang)]
    than, giu = _che(ma)
    for k, m in enumerate(re.finditer(mau, than)):
        if k != db.thu_tu:
            continue
        rep = m.expand(thay) if isinstance(thay, str) else thay(m)
        return _bo_che(than[:m.start()] + rep + than[m.end():], giu)
    return ma

def do_do_nhay(nguon: list[Path], chay: Callable[[Path | None], tuple[bool, str]],
               toi_da_phep: int = 3,
               bang: tuple[tuple[str, Any, str], ...] = _PHEP,
               thu_muc_tam: Path | None = None,
               muc: str = "tep", toi_da_moi_tep: int = 30,
               seed: int = 0) -> dict[str, Any]:
    """Với từng tệp nguồn: nạp nó vào bộ kiểm, phá nó, xem có ca nào đỏ không.

    `chay(p)` do tầng trên đưa vào: `chay(None)` chạy bộ kiểm như tác tử vẫn chạy nó;
    `chay(p)` chạy bộ kiểm **có nạp thêm tệp sản phẩm `p`**. Trả `(mọi ca đều đạt, log)`.
    Mô-đun này không biết gì về trình biên dịch, nên nó đo được cả bộ test đã có lẫn bộ test
    do công cụ khác sinh ra.

    Trả về, với mỗi tệp, một trong **bốn** trạng thái. Bốn, không phải hai — mỗi lần gộp
    chúng lại là một lần nói sai:

    * `thay` — phá thì bộ kiểm đỏ ⇒ nó có nhìn tệp này.
    * `khong_thay` — nạp được, phá rồi mà bộ kiểm vẫn xanh ⇒ nó không nhìn tệp này.
    * `khong_nap_duoc` — bộ kiểm **không dịch nổi cùng** tệp sản phẩm. Đây là bằng chứng
      MẠNH HƠN `khong_thay`, không phải yếu hơn: nếu tệp test đã định nghĩa lại hàm của sản
      phẩm thì trình liên kết báo trùng ký hiệu; nếu mã sản phẩm dính header của bo thì nó
      không dịch được trên máy chủ. Cả hai đều có nghĩa **bộ kiểm chưa từng chạy mã ấy**.
    * `chua_do_duoc` — không có chỗ nào để phá, hoặc không đọc được tệp. Cái này mới thật
      sự là "chưa biết", và gộp nó vào "không thấy" là một cáo buộc sai.

    **M4-04 — `muc="chi_tiet"`: một con số và một DANH SÁCH DÒNG, thay cho một câu nhị phân.**

    Chế độ `"tep"` (mặc định, không đổi một ly) trả lời *"bộ kiểm có thấy tệp này không"*. Đủ
    để lật tẩy một ô xanh giả, không đủ để làm gì tiếp: một tệp 400 dòng mà bộ kiểm chỉ canh
    một hằng số vẫn ra `thay`, y như một tệp được canh từng dòng — vì `re.subn` đổi mọi chỗ
    khớp cùng lúc, nên "đảo mọi phép `==`" là MỘT đột biến.

    Chế độ `"chi_tiet"` áp từng vị trí một và trả thêm: `diem` = bắt / (đã thử − stillborn),
    `so_mutant`, `so_bat`, `so_stillborn`, và `song` — danh sách dòng bộ kiểm **không** canh.
    Danh sách ấy đáng hơn con số: một điểm 0,62 không nói đi sửa chỗ nào.

    **M4-19 — `thu_muc_tam`: đột biến trên BẢN SAO, tệp gốc chỉ được ĐỌC.**

    Không có nó thì hàm này ghi mã đã phá vào **chính tệp của dự án**, rồi trả lại trong
    `finally`. Thế chỉ an toàn với ngoại lệ Python. Một `Ctrl-C`, một lần máy mất điện, một
    `kill -9` giữa vòng đo — và tệp sản phẩm nằm lại ở trạng thái đã bị phá, trong một dự án
    mà người dùng tưởng là nguyên vẹn. Phép đo tự tay làm hỏng thứ nó đi đo.

    **Điều kiện để dùng được:** hàm `chay` phải thật sự ĐỌC đường dẫn nó nhận. `chay` của
    `hdl.sensitivity` thì **không** — nó bỏ qua đối số và dịch lại cả thư mục nguồn, nên bật
    `thu_muc_tam` ở đó là phá bản sao mà biên dịch bản gốc: mọi mutant đều "không thay đổi
    gì", và mọi tệp RTL bị kết luận là **bộ kiểm không canh tới**. Một cáo buộc sai với từng
    tệp, và lượt đo vẫn xanh trơn. Đường cũ (không `thu_muc_tam`) giữ nguyên cho nó.
    """
    if muc not in ("tep", "chi_tiet"):
        raise ValueError(f"muc phải là 'tep' hoặc 'chi_tiet', không phải {muc!r}")
    ra: dict[str, Any] = {"tep": [], "so_thay": 0, "so_khong_thay": 0,
                          "so_khong_nap": 0, "so_chua_do": 0,
                          # M4-05 — số mutant bị BỎ vì không dịch được (stillborn). Luôn có
                          # trong kết quả, kể cả khi bằng 0: một khoá chỉ xuất hiện khi khác 0
                          # buộc bên đọc phải `.get(...)` kèm một mặc định, và mặc định ấy sớm
                          # muộn sai ở một chỗ nào đó.
                          "so_mutant_khong_hop_le": 0}
    if muc == "chi_tiet":
        ra.update({"so_mutant": 0, "so_bat": 0, "so_stillborn": 0, "song": []})
    dat_goc, log_goc = chay(None)
    ra["bo_kiem_xanh_luc_dau"] = dat_goc
    if not dat_goc:
        # Bộ kiểm đang đỏ sẵn thì phép đột biến vô nghĩa: không phân biệt được "đỏ vì đột
        # biến" với "đỏ từ trước".
        ra["vi_sao_khong_do_duoc"] = (
            "bộ kiểm đang ĐỎ từ trước khi đột biến, nên không phân biệt được ca nào đỏ vì "
            "mã bị phá. Sửa cho nó xanh đã, rồi đo lại.")
        ra["log"] = log_goc[-800:]
        return ra

    for thu_tu, p in enumerate(nguon):
        try:
            goc = p.read_text("utf-8")
        except OSError as e:
            ra["tep"].append({"tep": p.name, "trang_thai": "chua_do_duoc",
                              "vi_sao": f"không đọc được: {e}"})
            ra["so_chua_do"] += 1
            continue

        # M4-19 — `lam_viec` là tệp mà vòng đo được phép GHI. Có `thu_muc_tam` thì nó là một
        # bản sao; không thì nó chính là tệp gốc (đường cũ, giữ cho tương thích).
        #
        # Thư mục con theo thứ tự: hai tệp sản phẩm khác thư mục có thể cùng tên
        # (`bai1/dem.c` và `bai2/dem.c`), và gộp chúng vào một chỗ là lượt đo của tệp sau
        # phá mất bản sao của tệp trước.
        lam_viec = p
        if thu_muc_tam is not None:
            rieng = Path(thu_muc_tam) / str(thu_tu)
            rieng.mkdir(parents=True, exist_ok=True)
            lam_viec = rieng / p.name
            lam_viec.write_text(goc, "utf-8")
        try:
            if muc == "chi_tiet":
                _do_chi_tiet(ra, p, lam_viec, goc, chay, bang, toi_da_moi_tep, seed)
            else:
                _do_mot_tep(ra, p, lam_viec, goc, chay, toi_da_phep, bang)
        finally:
            if thu_muc_tam is not None:
                shutil.rmtree(lam_viec.parent, ignore_errors=True)
    # Dọn cả thư mục tạm, không chỉ các thư mục con. Một thư mục rỗng sót lại trong `.eide/`
    # là rác của phép đo nằm trong dự án của người dùng — nhỏ, nhưng nó tích lại mỗi `run_id`.
    if thu_muc_tam is not None:
        shutil.rmtree(thu_muc_tam, ignore_errors=True)
    if muc == "chi_tiet":
        # Mẫu số BỎ stillborn: để chúng trong đó là kéo điểm xuống vì một lý do không nói gì
        # về bộ kiểm — đúng cái lỗi M4-05 vừa sửa ở chế độ theo tệp, lần này hiện ra thành
        # một con số. Và không có mutant nào thì điểm là `None`, không phải `0.0`: `0.0` đọc
        # thành "bộ kiểm không bắt được gì", một cáo buộc; cái đúng là "chưa biết".
        mau_so = ra["so_mutant"] - ra["so_stillborn"]
        ra["diem"] = (ra["so_bat"] / mau_so) if mau_so > 0 else None
        ra["song"] = ra["song"][:20]
    return ra


def _do_chi_tiet(ra: dict[str, Any], p: Path, lam_viec: Path, goc: str,
                 chay: Callable[[Path | None], tuple[bool, str]],
                 bang: tuple[tuple[str, Any, str], ...], toi_da: int, seed: int) -> None:
    """Áp từng đột biến MỘT, và ghi lại những chỗ bộ kiểm không canh."""
    nap_duoc, log_nap = chay(lam_viec)
    if _khong_dich_duoc(log_nap):
        ra["tep"].append({"tep": p.name, "trang_thai": "khong_nap_duoc",
                          "vi_sao": _vi_sao_khong_nap(log_nap), "log": log_nap[-500:]})
        ra["so_khong_nap"] += 1
        return
    if not nap_duoc:
        ra["tep"].append({
            "tep": p.name, "trang_thai": "chua_do_duoc",
            "vi_sao": ("nạp mã thật vào thì bộ kiểm ĐỎ ngay khi chưa phá gì — bộ kiểm và sản "
                       "phẩm đang bất đồng, xử chỗ đó trước rồi đo lại"),
            "log": log_nap[-500:]})
        ra["so_chua_do"] += 1
        return

    ds = liet_ke_dot_bien(goc, bang=bang, toi_da=toi_da, seed=seed)
    if not ds:
        ra["tep"].append({"tep": p.name, "trang_thai": "chua_do_duoc",
                          "vi_sao": "không có chỗ nào để đột biến"})
        ra["so_chua_do"] += 1
        return
    ds.sort(key=lambda x: (x.dong, x.phep, x.thu_tu))
    bat = sb = 0
    for db in ds:
        try:
            lam_viec.write_text(ap_mot(goc, db, bang=bang), "utf-8")
            dat, log = chay(lam_viec)
        finally:
            lam_viec.write_text(goc, "utf-8")
        ra["so_mutant"] += 1
        if not dat and _la_loi_bien_dich(log):
            sb += 1
            ra["so_stillborn"] += 1
            ra["so_mutant_khong_hop_le"] += 1
        elif not dat:
            bat += 1
            ra["so_bat"] += 1
        else:
            ra["song"].append({"tep": p.name, **db.to_dict()})

    da_thu = len(ds) - sb
    ra["tep"].append({
        "tep": p.name,
        "trang_thai": ("thay" if bat else ("chua_do_duoc" if da_thu == 0 else "khong_thay")),
        "vi_sao": (f"bắt {bat}/{da_thu} đột biến" if da_thu
                   else f"mọi đột biến đều làm hỏng biên dịch ({sb} phép)"),
        "diem": (bat / da_thu) if da_thu else None,
        "so_mutant": len(ds), "so_stillborn": sb})
    if bat:
        ra["so_thay"] += 1
    elif da_thu == 0:
        ra["so_chua_do"] += 1
    else:
        ra["so_khong_thay"] += 1


def _do_mot_tep(ra: dict[str, Any], p: Path, lam_viec: Path, goc: str,
                chay: Callable[[Path | None], tuple[bool, str]], toi_da_phep: int,
                bang: tuple[tuple[str, Any, str], ...]) -> None:
    """Đo một tệp. `p` chỉ dùng để GỌI TÊN trong kết quả; `lam_viec` là tệp được phép ghi."""
    # Trước khi phá: bộ kiểm có nạp nổi tệp này không. Hỏi câu này trước vì câu trả lời
    # "không" đã là kết luận, và nó rẻ hơn một vòng đột biến.
    nap_duoc, log_nap = chay(lam_viec)
    if _khong_dich_duoc(log_nap):
        ra["tep"].append({"tep": p.name, "trang_thai": "khong_nap_duoc",
                          "vi_sao": _vi_sao_khong_nap(log_nap),
                          "log": log_nap[-500:]})
        ra["so_khong_nap"] += 1
        return
    if not nap_duoc:
        # Dịch được nhưng đỏ ngay khi có mã thật: bộ kiểm và sản phẩm nói khác nhau.
        ra["tep"].append({
            "tep": p.name, "trang_thai": "chua_do_duoc",
            "vi_sao": ("nạp mã thật vào thì bộ kiểm ĐỎ ngay khi chưa phá gì — bộ kiểm "
                       "và sản phẩm đang bất đồng, xử chỗ đó trước rồi đo lại"),
            "log": log_nap[-500:]})
        ra["so_chua_do"] += 1
        return

    thay_doi = False
    ghi_chu = "không có chỗ nào để đột biến"
    # M4-05 — đếm riêng mutant STILLBORN của tệp này. Nếu MỌI phép đều stillborn thì cả
    # tệp là "chưa đo được", không phải "không thấy": chưa phép kiểm nào chạy để mà thấy.
    stillborn = 0
    for i in range(min(toi_da_phep, len(bang))):
        moi_ma, mo_ta, n = dot_bien_van_ban(goc, i, bang=bang)
        if n == 0 or moi_ma == goc:
            continue
        try:
            lam_viec.write_text(moi_ma, "utf-8")
            dat, log = chay(lam_viec)
        finally:
            lam_viec.write_text(goc, "utf-8")
        # M4-05 — "mã không DỊCH nổi" không phải "bộ kiểm bắt được".
        #
        # Bản cũ chỉ hỏi `not dat`, và `False` có hai nghĩa khác hẳn nhau: bộ kiểm chạy
        # rồi có ca đỏ (nó CÓ canh chỗ ấy), hoặc mutant không dịch được (chưa phép kiểm
        # nào chạy). Gộp lại thì con số độ nhạy đẹp lên một cách giả, và đẹp theo hướng
        # tệ nhất: những phép phá THÔ nhất — loại làm hỏng cú pháp — là loại dễ được tính
        # là "bắt được" nhất, trong khi chúng không nói gì về việc bộ kiểm có đọc giá trị
        # nào của tệp hay không.
        #
        # KHÔNG `break` ở đây: một phép phá không dịch được chưa trả lời câu hỏi nào, nên
        # câu trả lời phải đi tìm ở phép kế tiếp.
        if not dat and _la_loi_bien_dich(log):
            stillborn += 1
            ra["so_mutant_khong_hop_le"] += 1
            ghi_chu = f"{mo_ta} ({n} chỗ) → mutant không dịch được (bỏ qua)"
            continue
        if not dat:
            thay_doi = True
            ghi_chu = f"{mo_ta} ({n} chỗ) → bộ kiểm ĐỎ"
            break
        ghi_chu = f"{mo_ta} ({n} chỗ) → bộ kiểm vẫn xanh"
    if thay_doi:
        ra["tep"].append({"tep": p.name, "trang_thai": "thay", "vi_sao": ghi_chu})
        ra["so_thay"] += 1
    elif "không có chỗ nào" in ghi_chu:
        ra["tep"].append({"tep": p.name, "trang_thai": "chua_do_duoc", "vi_sao": ghi_chu})
        ra["so_chua_do"] += 1
    elif stillborn and "không dịch được" in ghi_chu:
        # Mọi phép phá được đều stillborn — phép phá cuối cùng cũng vậy, nên `ghi_chu`
        # còn mang chữ ấy. Chưa có một lượt chạy nào nói được gì về bộ kiểm.
        ra["tep"].append({
            "tep": p.name, "trang_thai": "chua_do_duoc",
            "vi_sao": (f"mọi đột biến đều làm hỏng biên dịch ({stillborn} phép), nên chưa "
                       "có lượt chạy nào nói được bộ kiểm có canh tệp này hay không")})
        ra["so_chua_do"] += 1
    else:
        ra["tep"].append({"tep": p.name, "trang_thai": "khong_thay", "vi_sao": ghi_chu})
        ra["so_khong_thay"] += 1


# Dấu hiệu "không dịch/liên kết được", tách khỏi "dịch được nhưng ca đỏ". Hai thứ này trông
# giống nhau ở đầu ra (đều là không-đạt) nhưng nói hai điều khác hẳn nhau.
_DAU_HIEU_TRUNG = ("duplicate symbol", "multiple definition", "redefinition of")
_DAU_HIEU_THIEU = ("file not found", "no such file", "fatal error:")
_DAU_HIEU_KHAC = ("undefined symbol", "undefined reference", "error:", "ld: ")


def _khong_dich_duoc(log: str) -> bool:
    l = log.lower()
    return any(x in l for x in _DAU_HIEU_TRUNG + _DAU_HIEU_THIEU + _DAU_HIEU_KHAC)


# M4-05 — tiền tố mà hàm `chay` dùng để KHAI "lượt này không dịch được", thay vì để mô-đun
# này đoán từ nội dung log.
#
# Vì sao không dùng `_khong_dich_duoc` ở trong vòng đột biến: `_DAU_HIEU_KHAC` có `"error:"`,
# và `vi_sao_khong_dat` của một ca test hỏng THẬT rất dễ chứa chữ ấy — `"TC-01: error: mong 1
# nhan 0"`. Một phép dò theo nội dung sẽ gọi mọi ca test hỏng như thế là "mutant không dịch
# được", tức biến một phép đo *bắt được* thành *chưa đo được*, và con số độ nhạy TỤT xuống vì
# một lý do sai. Ở bước nạp mã gốc thì `_khong_dich_duoc` vẫn đúng và vẫn dùng: ở đó log là
# đầu ra của trình biên dịch, không trộn với lời của bộ kiểm.
TIEN_TO_BIEN_DICH = "[BIEN_DICH] "


def _la_loi_bien_dich(log: Any) -> bool:
    return isinstance(log, str) and log.lstrip().startswith(TIEN_TO_BIEN_DICH)


def ket_qua_chay(*, dat: bool, loi_bien_dich: str = "", log: str = "") -> tuple[bool, str]:
    """Dựng giá trị trả về của một hàm `chay` — MỘT chỗ quyết định có gắn tiền tố hay không.

    Hai đường đo (C qua `test.sensitivity`, Verilog qua `hdl.sensitivity`) đều cần đúng một
    luật: **chỉ gắn tiền tố khi có lỗi biên dịch.** Viết luật ấy hai lần là mời chúng lệch
    nhau, và lúc lệch thì một đường tính stillborn còn đường kia thì không — mà không ai nói
    ra. Đo được ở lượt phá đầu của M4-05: hai phép phá nhắm đúng chỗ này đều LỌT, vì luật nằm
    trong hai closure không ca kiểm nào gọi tới được.

    `dat=False` **không** đủ để gắn: quá hạn cũng là không đạt, và một mutant làm bộ kiểm
    **treo** thì không phải mutant không dịch được — nó là một mutant mà phép đo không kết
    luận được, và gọi nó là stillborn là nói sai về nguyên nhân.
    """
    if dat:
        return True, log
    if loi_bien_dich:
        return False, TIEN_TO_BIEN_DICH + loi_bien_dich
    return False, log


def _vi_sao_khong_nap(log: str) -> str:
    """Nói lý do bằng lời người đọc, và nói luôn nó chứng minh điều gì."""
    l = log.lower()
    if any(x in l for x in _DAU_HIEU_TRUNG):
        return ("trình liên kết báo TRÙNG ký hiệu — tệp test tự định nghĩa lại hàm của sản "
                "phẩm, nên nó đang kiểm bản sao viết trong chính nó, không kiểm sản phẩm")
    if any(x in l for x in _DAU_HIEU_THIEU):
        return ("mã sản phẩm không dịch được trên máy chủ (thiếu header của bo), nên bộ kiểm "
                "chưa từng chạy được dòng nào của nó — logic đang dính chặt vào phần cứng")
    if "undefined" in l:
        return ("thiếu ký hiệu khi liên kết — mã sản phẩm cần thứ mà bộ kiểm chưa dựng giả "
                "được")
    return "bộ kiểm không dịch được cùng mã sản phẩm"


def loi_nguoi_doc(d: dict[str, Any]) -> str:
    """Một đoạn cho người đọc. Nói thẳng khi bộ kiểm không đo gì."""
    if d.get("vi_sao_khong_do_duoc"):
        return "Chưa đo được độ nhạy: " + d["vi_sao_khong_do_duoc"]
    if not d["tep"]:
        return "Không có tệp nguồn nào để đo."
    mu = [x for x in d["tep"] if x["trang_thai"] == "khong_thay"]
    ngoai = [x for x in d["tep"] if x["trang_thai"] == "khong_nap_duoc"]
    tong = len(d["tep"])
    # M4-05 — nói ra số mutant bị BỎ. "Bắt 1/1" sau khi một phép phá bị bỏ vì không dịch được
    # là một câu đúng về mẫu số của nó và sai về điều người đọc hiểu.
    sb = int(d.get("so_mutant_khong_hop_le") or 0)
    them_sb = (f" {sb} phép phá bị BỎ vì mutant không dịch được — chúng không nằm trong con "
               "số trên, và cũng không nói gì về bộ kiểm." if sb else "")
    if ngoai or mu:
        dong = [f"**Bộ kiểm không chạm tới {len(ngoai) + len(mu)}/{tong} tệp mã sản phẩm.**"]
        for x in ngoai:
            dong.append(f"- `{x['tep']}` — KHÔNG NẠP ĐƯỢC: {x['vi_sao']}.")
        for x in mu:
            dong.append(f"- `{x['tep']}` — nạp được nhưng phá nó mà không ca nào đỏ "
                        f"({x['vi_sao']}).")
        dong.append("Ô xanh của những tệp ấy không nói gì về sản phẩm: nó nói về mã nằm "
                    "trong chính tệp test. Và ô xanh thì dừng việc tìm lỗi, nên nó tệ hơn "
                    "không có bộ kiểm nào.")
        if d["so_thay"]:
            dong.append(f"Đo được {d['so_thay']}/{tong} tệp thì bộ kiểm CÓ nhìn thấy.")
        if them_sb:
            dong.append(them_sb.strip())
        return "\n".join(dong)
    # M4-05 — không phá được tệp nào thì KHÔNG nói "bộ kiểm nhìn thấy cả 0/N tệp — phá tệp
    # nào cũng có ca đỏ". Câu ấy đọc như một lời khen trong khi chưa lượt chạy nào nói được gì.
    if not d["so_thay"]:
        return ("**CHƯA ĐO ĐƯỢC** độ nhạy của tệp nào: "
                + "; ".join(f"`{x['tep']}` — {x['vi_sao']}" for x in d["tep"][:4])
                + "." + them_sb
                + " Con số độ nhạy ở đây KHÔNG phải 0 — nó là “chưa biết”.")
    return (f"Bộ kiểm nhìn thấy cả {d['so_thay']}/{tong} tệp — phá tệp nào cũng có ca đỏ."
            + (f" ({d['so_chua_do']} tệp chưa đo được.)" if d["so_chua_do"] else "")
            + them_sb
            + " Phép này chỉ chứng minh bộ kiểm KHÔNG RỖNG, không nói nó sâu tới đâu.")
