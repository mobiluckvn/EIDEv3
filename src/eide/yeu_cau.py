# -*- coding: utf-8 -*-
"""Chất lượng của chính YÊU CẦU — ba phép đo chạy bằng mã, 0 token.

`store.req_create` nhận bất cứ câu nào trích được lời người dùng (N7) và không kiểm gì
thêm. Đo được trên bộ usecase TC004: người dùng gõ *"làm cho mình cái mạch thông minh"*,
và một yêu cầu "mạch thông minh" vào kho trót lọt. Yêu cầu ấy không sai — nó **không đo
được**, nên mọi thứ dựng trên nó cũng không đo được, và chữ "đạt" sau này sẽ trùm lên một
thứ chưa ai định nghĩa.

Ba câu hỏi ở đây đều trả lời được mà không gọi mô hình:

  `kiem_tieu_chi`  tiêu chí có con số kèm đơn vị, hoặc một phép so, hay không
  `tu_mo_ho`       câu có từ nào mà hai người đọc ra hai nghĩa khác nhau
  `trung_lap`      yêu cầu này đã có ai viết rồi chưa

Cả ba **không chặn** việc ghi. Chặn một yêu cầu vì nó mơ hồ là lấy mất quyền của người
đang còn mơ hồ về chính việc họ muốn — việc của ta là nói ra, rồi chỉ đường `ask_user`.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

# Từ mà hai người đọc ra hai nghĩa khác nhau, nên không có cách nào đo. Danh sách ngắn và
# cố ý ngắn: mỗi từ thêm vào là một lần nữa bộ dò có thể kêu oan, và một bộ dò kêu oan thì
# bị tắt đi — lúc ấy nó không còn bắt được gì nữa.
TU_MO_HO: tuple[str, ...] = (
    "nhanh", "ổn định", "thông minh", "dễ dùng", "tốt", "mượt",
    "nhiều", "ít", "tối ưu", "thân thiện",
)

# Một con số KÈM đơn vị, hoặc một phép so. "dưới 5" không đạt: 5 giây, 5 phần trăm, hay 5
# tệp là ba yêu cầu khác nhau.
_CO_SO_DON_VI = re.compile(
    r"(?:≤|≥|<=|>=|<|>|=)?\s*\d+(?:[.,]\d+)?\s*(?:[A-Za-zµΩ%°]+(?:/[A-Za-z]+)?|"
    r"giây|giay|phút|phut|giờ|gio|lần|lan|tệp|tep|byte|ký tự|ky tu)")
# Phép so kèm số, không cần đơn vị — "≥ 5" vẫn mơ hồ, nhưng "trong khoảng 3–5 V" thì không.
_CO_PHEP_SO = re.compile(r"(?:≤|≥|<=|>=|<|>)\s*\d")

# Từ quá ngắn thì không mang nghĩa riêng khi so hai câu — bỏ chúng ra khỏi phép đo Jaccard.
_DAI_TOI_THIEU = 3
_NGUONG_TRUNG = 0.6


def go_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt, kể cả `đ`/`Đ`.

    Bản `_go_dau` trong `tools/design.py` viết `.replace("d", "d")` — một phép thay vô
    nghĩa, chắc là gõ nhầm từ `.replace("đ", "d")`. Hệ quả: `go_dau("ổn định")` ra
    `"on đinh"` còn `go_dau("ON DINH")` ra `"on dinh"`, nên hai câu ấy **không khớp nhau**.
    Ở đây làm đúng, vì người dùng thật gõ cả hai kiểu, thường trong cùng một phiên.
    """
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d")


def _tach_tu(s: str) -> list[str]:
    return [t for t in re.split(r"[^0-9a-z]+", go_dau(s)) if t]


def kiem_tieu_chi(s: str) -> list[str]:
    """Tiêu chí có đo được không. Rỗng = đạt.

    Trả câu tiếng Việt nói rõ thiếu gì, không trả mã lỗi: đây là lời khuyên cho người
    viết yêu cầu, không phải một thứ để chương trình rẽ nhánh.
    """
    t = (s or "").strip()
    if not t:
        return ["tiêu chí để trống — không có gì để đo, nên không có cách nào nói “đạt”"]
    if _CO_PHEP_SO.search(t) or _CO_SO_DON_VI.search(t):
        return []
    if re.search(r"\d", t):
        return ["tiêu chí có số nhưng thiếu đơn vị hoặc phép so — “dưới 5” là 5 giây, "
                "5 phần trăm, hay 5 tệp?"]
    return ["tiêu chí chưa đo được: không có con số nào kèm đơn vị, cũng không có phép so"]


def tu_mo_ho(text: str) -> list[str]:
    """Các từ trong `TU_MO_HO` xuất hiện trong câu, so sau khi bỏ dấu.

    So theo **từ trọn**, không theo chuỗi con: sau khi bỏ dấu, "thiết" thành "thiet" có
    chứa "it", và "nhiệt" thành "nhiet" có chứa "nhiet"… một phép `in` đơn giản sẽ kêu oan
    gần như mọi câu kỹ thuật.
    """
    tu = _tach_tu(text)
    ra: list[str] = []
    for cum in TU_MO_HO:
        can = _tach_tu(cum)
        n = len(can)
        for i in range(len(tu) - n + 1):
            if tu[i:i + n] != can:
                continue
            if _co_so_ngay_sau(tu, i + n):
                continue      # "ít nhất 2 lần" — đo được, đừng kêu
            ra.append(cum)
            break
    return ra


def _co_so_ngay_sau(tu: list[str], i: int) -> bool:
    """Ngay sau cụm có một con số không (cho phép một từ đệm như "nhất" chen giữa)?

    Đo trên 37 REQ thật của các dự án đã làm: câu *"in đúng chuỗi ra UART **ít nhất 2
    lần**"* bị kêu vì từ "ít" — mà "ít nhất 2 lần" là một mức ĐO ĐƯỢC, không phải một lời
    mơ hồ. "ít" và "nhiều" đứng trước một con số là lượng từ, không phải tính từ.

    Một bộ dò kêu oan thì bị tắt đi, và lúc ấy nó không bắt được gì nữa — nên chỗ này
    thà bỏ sót một câu mơ hồ hơn là kêu oan một câu đã đo được.
    """
    return any(t.isdigit() for t in tu[i:i + 2])


def trung_lap(text: str, ds_req: list[dict[str, Any]],
              nguong: float = _NGUONG_TRUNG) -> list[str]:
    """Mã các REQ đã có mà câu này nói gần y như vậy (Jaccard theo từ ≥ `nguong`).

    Hai REQ nói cùng một việc thì không ai biết cái nào đang có hiệu lực — và khi sửa một
    cái, cái kia lặng lẽ thành sai. Chính vì thế mô tả của `store.req_create` đã dặn
    *"đổi ý thì `req_update`, ĐỪNG tạo REQ mới"*; đây là phép đo cho lời dặn ấy.
    """
    a = {t for t in _tach_tu(text) if len(t) >= _DAI_TOI_THIEU}
    if not a:
        return []
    ra: list[str] = []
    for rq in ds_req or []:
        b = {t for t in _tach_tu((rq.get("canonical") or {}).get("text", ""))
             if len(t) >= _DAI_TOI_THIEU}
        if not b:
            continue
        chung = len(a & b)
        if chung and chung / len(a | b) >= nguong:
            ra.append(rq["id"])
    return ra


def kiem_yeu_cau(text: str, criteria: str, ds_req: list[dict[str, Any]],
                 *, bo_qua_id: str = "") -> list[dict[str, Any]]:
    """Gộp ba phép đo thành một danh sách cảnh báo **có cấu trúc**.

    Mỗi cảnh báo mang `loai` để chương trình rẽ nhánh được, `vi` để người đọc, và
    `chi_tiet` để không ai phải đoán cảnh báo nói về cái gì.
    """
    ra: list[dict[str, Any]] = []

    mo = tu_mo_ho(text)
    if mo:
        ra.append({"loai": "tu_mo_ho", "chi_tiet": mo,
                   "vi": ("Câu yêu cầu có từ không đo được: " + ", ".join(f"“{x}”" for x in mo)
                          + ". Hai người đọc sẽ ra hai nghĩa, và phép đo sau này sẽ đo theo "
                            "nghĩa của người viết mã.")})

    tc = kiem_tieu_chi(criteria)
    if tc:
        ra.append({"loai": "tieu_chi", "chi_tiet": tc,
                   "vi": "Tiêu chí đo: " + "; ".join(tc)})

    trung = trung_lap(text, [r for r in (ds_req or []) if r.get("id") != bo_qua_id])
    if trung:
        ra.append({"loai": "trung_lap", "chi_tiet": trung,
                   "vi": ("Yêu cầu này nói gần y như " + ", ".join(trung)
                          + " đã có trong kho. Hai REQ cùng một việc thì không ai biết cái "
                            "nào đang có hiệu lực — sửa một cái, cái kia lặng lẽ thành sai. "
                            "Nếu là đổi ý thì dùng `store.req_update`.")})
    return ra


def cau_nhac(canh_bao: list[dict[str, Any]]) -> str:
    """Một câu nối vào `note_vi`, chỉ đường cho tác tử. Rỗng khi không có cảnh báo gì."""
    if not canh_bao:
        return ""
    loai = ", ".join(c["loai"] for c in canh_bao)
    return (f" CẢNH BÁO CHẤT LƯỢNG YÊU CẦU ({loai}): " + " ".join(c["vi"] for c in canh_bao)
            + " Yêu cầu VẪN được ghi — nhưng đừng tự sửa câu hộ người dùng. Dùng `ask_user` "
              "để hỏi đúng con số còn thiếu, rồi `store.req_update`.")
