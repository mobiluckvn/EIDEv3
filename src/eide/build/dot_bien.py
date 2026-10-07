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
    giu: list[str] = []

    def _cat(m: re.Match[str]) -> str:
        giu.append(m.group(0))
        return f"\x00{len(giu) - 1}\x00"

    than = _BO_QUA.sub(_cat, ma)
    moi, n = re.subn(mau, thay, than)
    moi = re.sub(r"\x00(\d+)\x00", lambda m: giu[int(m.group(1))], moi)
    return moi, mo_ta, n


def do_do_nhay(nguon: list[Path], chay: Callable[[Path | None], tuple[bool, str]],
               toi_da_phep: int = 3,
               bang: tuple[tuple[str, Any, str], ...] = _PHEP) -> dict[str, Any]:
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
    """
    ra: dict[str, Any] = {"tep": [], "so_thay": 0, "so_khong_thay": 0,
                          "so_khong_nap": 0, "so_chua_do": 0}
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

    for p in nguon:
        try:
            goc = p.read_text("utf-8")
        except OSError as e:
            ra["tep"].append({"tep": p.name, "trang_thai": "chua_do_duoc",
                              "vi_sao": f"không đọc được: {e}"})
            ra["so_chua_do"] += 1
            continue

        # Trước khi phá: bộ kiểm có nạp nổi tệp này không. Hỏi câu này trước vì câu trả lời
        # "không" đã là kết luận, và nó rẻ hơn một vòng đột biến.
        nap_duoc, log_nap = chay(p)
        if _khong_dich_duoc(log_nap):
            ra["tep"].append({"tep": p.name, "trang_thai": "khong_nap_duoc",
                              "vi_sao": _vi_sao_khong_nap(log_nap),
                              "log": log_nap[-500:]})
            ra["so_khong_nap"] += 1
            continue
        if not nap_duoc:
            # Dịch được nhưng đỏ ngay khi có mã thật: bộ kiểm và sản phẩm nói khác nhau.
            ra["tep"].append({
                "tep": p.name, "trang_thai": "chua_do_duoc",
                "vi_sao": ("nạp mã thật vào thì bộ kiểm ĐỎ ngay khi chưa phá gì — bộ kiểm "
                           "và sản phẩm đang bất đồng, xử chỗ đó trước rồi đo lại"),
                "log": log_nap[-500:]})
            ra["so_chua_do"] += 1
            continue

        thay_doi = False
        ghi_chu = "không có chỗ nào để đột biến"
        for i in range(min(toi_da_phep, len(bang))):
            moi_ma, mo_ta, n = dot_bien_van_ban(goc, i, bang=bang)
            if n == 0 or moi_ma == goc:
                continue
            try:
                p.write_text(moi_ma, "utf-8")
                dat, _ = chay(p)
            finally:
                p.write_text(goc, "utf-8")
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
        else:
            ra["tep"].append({"tep": p.name, "trang_thai": "khong_thay", "vi_sao": ghi_chu})
            ra["so_khong_thay"] += 1
    return ra


# Dấu hiệu "không dịch/liên kết được", tách khỏi "dịch được nhưng ca đỏ". Hai thứ này trông
# giống nhau ở đầu ra (đều là không-đạt) nhưng nói hai điều khác hẳn nhau.
_DAU_HIEU_TRUNG = ("duplicate symbol", "multiple definition", "redefinition of")
_DAU_HIEU_THIEU = ("file not found", "no such file", "fatal error:")
_DAU_HIEU_KHAC = ("undefined symbol", "undefined reference", "error:", "ld: ")


def _khong_dich_duoc(log: str) -> bool:
    l = log.lower()
    return any(x in l for x in _DAU_HIEU_TRUNG + _DAU_HIEU_THIEU + _DAU_HIEU_KHAC)


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
        return "\n".join(dong)
    return (f"Bộ kiểm nhìn thấy cả {d['so_thay']}/{tong} tệp — phá tệp nào cũng có ca đỏ."
            + (f" ({d['so_chua_do']} tệp chưa đo được.)" if d["so_chua_do"] else "")
            + " Phép này chỉ chứng minh bộ kiểm KHÔNG RỖNG, không nói nó sâu tới đâu.")
