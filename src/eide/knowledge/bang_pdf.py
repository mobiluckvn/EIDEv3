# -*- coding: utf-8 -*-
"""M5-04 — đọc BẢNG của một PDF thành hàng bảng (`o`/`cot`/`loai_bang`).

Vì sao cần: `_tu_hang_bang` trong `docs.py` đã tồn tại từ trước, và nó tồn tại vì một lý do
đo được — datasheet đặt **đơn vị ở cột riêng** (`VDD | 1.8 | 5.5 | V`), nên nối cả hàng
thành một dòng chữ rồi tìm "số kèm đơn vị" thì `5.5` và `V` cách nhau một dấu gạch và không
bao giờ khớp. Nhưng đường duy nhất cấp `o`/`cot` cho nó là Office. PDF — đúng định dạng mà
mọi datasheet thật dùng — đi đường theo dòng, và `nap_tai_lieu` dựng
`Trang(i + 1, p.extract_text())` **không bao giờ** đặt `o`/`cot`.

`pdfplumber` là phụ thuộc **tuỳ chọn** (N-10): thiếu nó thì đường theo dòng chạy y nguyên, và
hệ thống **nói ra** rằng nó đang đi đường dự phòng. Im lặng ở đó là ca N6 kinh điển — người
bật cờ nghĩ đang đọc bảng, hệ thống đang đọc dòng chữ, và cả hai đều báo `ok`.

Giấy phép, tra ngày 10/10/2026 chứ không nhớ lại: `pdfplumber` MIT · `pdfminer.six` MIT ·
`pillow` MIT-CMU · `pypdfium2` BSD-3-Clause/Apache-2.0 · `cryptography` Apache-2.0 OR
BSD-3-Clause · `charset-normalizer` MIT. Không gói nào AGPL — kế hoạch cấm `pymupdf` chính vì
giấy phép ấy, nên chuỗi kéo theo cũng phải tra, không chỉ gói ở ngọn.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                                            # pragma: no cover
    from .docs import Trang

# Mục của datasheet mà tên mục ĐỔI NGHĨA con số bên dưới. Danh sách này ngắn có chủ ý: chỉ
# những mục mà nhãn sai dẫn tới một Fact sai nghĩa, không phải mọi tiêu đề có thể gặp.
_MAU_MUC = re.compile(
    r"(absolute\s+maximum|electrical\s+characteristic|recommended\s+operating"
    r"|dc\s+characteristic|ac\s+characteristic"
    r"|pin\s+(?:description|configuration|assignment)|register\s+map)", re.I)

# Hàng bảng mang số trang riêng để không trùng số của trang chữ. Trích dẫn "trang N" của Fact
# đã nằm trong kho phải giữ nguyên nghĩa — đổi cách đánh số là làm sai trích dẫn của dữ liệu
# cũ, mà dữ liệu cũ không ai sửa lại.
BUOC_TRANG = 10_000

# Trần số hàng bảng đọc từ một tài liệu. Một datasheet 1 200 trang có thể cho hàng chục nghìn
# hàng, và mỗi hàng là một đơn vị trích dẫn trong `TaiLieu` — tức nằm trong bộ nhớ của mọi
# lượt sau. Chạm trần thì NÓI RA, không cắt im lặng.
TRAN_HANG = 4_000


def _nap_pdfplumber() -> Any:
    """Tách ra một hàm để ca kiểm làm nó nổ được.

    Nếu `import` nằm thẳng trong `bang_tu_tai_lieu` thì không ca kiểm nào dựng được tình
    huống "máy không có thư viện" mà không gỡ gói khỏi `.venv` — và một đường dự phòng không
    ca nào đi qua là một đường chưa biết có chạy.
    """
    import pdfplumber                                        # noqa: PLC0415

    return pdfplumber


def _muc_cuoi(chu: str) -> str:
    """Dòng khớp `_MAU_MUC` **cuối cùng** trong đoạn chữ, hoặc rỗng."""
    for dong in reversed((chu or "").splitlines()):
        d = dong.strip()
        if d and _MAU_MUC.search(d):
            return d
    return ""


def tieu_de_gan_nhat(chu: str, dong: str) -> str:
    """Tiêu đề mục gần nhất **phía trên** `dong` trong đoạn chữ của trang.

    Lấy dòng đầu trang thay vì dòng gần nhất là một lỗi có hậu quả cụ thể: một trang
    datasheet thật có nhiều mục, nên bảng thứ hai sẽ mang nhãn của mục thứ nhất — và với
    M5-04 thì nhãn ấy quyết định `vdd.max` hay `vdd.abs_max`, tức một nhãn sai biến ngưỡng
    **phá hỏng chip** thành ngưỡng **chạy được**.
    """
    vt = (chu or "").find(dong or "")
    return _muc_cuoi(chu if vt < 0 else chu[:vt])


def loai_bang_tu_cot(cot: list[str]) -> str:
    """`loai_bang` suy từ TIÊU ĐỀ CỘT, không từ phỏng đoán nội dung.

    Ba loại bảng này được **đọc khác nhau**: bảng thông số cho ra số, bảng chân cho ra quan
    hệ chân ↔ net ↔ hướng, bảng thanh ghi cho ra offset. Và một bảng trình bày (Revision
    history) phải ra `""`: hàng của nó cũng có số (`1.2`, năm), nên nhận bừa là cách sinh
    Fact rác **mang trích dẫn thật** — thứ khó phát hiện hơn hẳn Fact không có trích dẫn.
    """
    thap = {str(c).strip().lower() for c in cot}

    def co(*ten: str) -> bool:
        return any(t in thap for t in ten)

    if co("min", "minimum", "typ", "typical", "max", "maximum") and co("unit", "units"):
        return "thong_so"
    if co("pin", "chân", "chan", "pin number", "pin name") and co(
            "function", "direction", "chức năng", "chuc nang", "hướng", "huong", "i/o", "io"):
        return "chan"
    if co("offset", "address", "addr", "địa chỉ") and co(
            "reset", "reset value", "register", "thanh ghi"):
        return "thanh_ghi"
    return ""


# Mã glyph thô mà `pdfplumber` trả về khi phông của trang không có bảng `ToUnicode`. Một ô
# `(cid:55)(cid:75)(cid:82)` không phải chữ — nó là số hiệu glyph. Đo trên 21 PDF thật của repo
# ngày 10/10/2026: 14 trong 150 hàng bảng tìm được là rác dạng này, và nếu để chúng vào kho
# thì chúng thành ĐƠN VỊ TRÍCH DẪN — tức tác tử sẽ trích dẫn một đoạn không ai đọc được.
_RAC_CID = re.compile(r"\(cid:\d+\)")

# Một bảng phải có ít nhất hai tiêu đề cột đọc được. `find_tables()` dò theo nét vẽ, nên một
# khung trình bày (ảnh có viền, hộp ghi chú) cũng ra "bảng" — và đo được trên dữ liệu thật:
# một "bảng" có tiêu đề `['', '', '', 'Green)', 'Sáng, 1: Tắt)']`. Không có hai tên cột thì
# không có ngữ nghĩa cột, mà đọc theo cột là toàn bộ lý do của đường này.
COT_TOI_THIEU = 2


def _la_rac(*chuoi: str) -> bool:
    """Chuỗi mà phần lớn là mã glyph thô."""
    gop = " ".join(chuoi)
    if not gop.strip():
        return False
    return len(_RAC_CID.findall(gop)) >= 3


def _sach(o: Any) -> str:
    """Ô bảng của pdfplumber có thể là `None` và chứa ngắt dòng trong ô."""
    return re.sub(r"\s+", " ", str(o or "")).strip()


def bang_tu_tai_lieu(path: Path) -> list["Trang"]:
    """Mọi hàng bảng của tệp PDF, mỗi hàng một `Trang`.

    Trả rỗng — không nổ — khi tệp không có bảng nào. Và "không có bảng" ở đây là con số
    **đúng** chứ không phải một phép dò hụt: `find_tables()` mặc định dò theo **nét vẽ**, nên
    một trang chỉ có chữ xếp thẳng hàng cho 0 bảng. Dò theo khoảng trắng (`text` strategy) sẽ
    cho ra những "bảng" mà chính nó tự dựng, và Fact sinh từ đó mang trích dẫn trỏ vào một
    bảng không tồn tại trong tệp.
    """
    from .docs import Trang

    pdfplumber = _nap_pdfplumber()
    ra: list[Trang] = []
    with pdfplumber.open(str(path)) as pdf:
        for i, trang in enumerate(pdf.pages, 1):
            chu_trang = trang.extract_text() or ""
            for k, tb in enumerate(trang.find_tables(), 1):
                try:
                    hang = tb.extract()
                except Exception:                            # noqa: BLE001
                    continue
                if len(hang) < 2:
                    # Một "bảng" một hàng không có tiêu đề cột, nên không có gì để đọc
                    # theo cột — mà đọc theo cột là toàn bộ lý do của đường này.
                    continue
                cot = [_sach(c) for c in hang[0]]
                if sum(1 for c in cot if c) < COT_TOI_THIEU:
                    continue
                if _la_rac(*cot):
                    continue
                loai = loai_bang_tu_cot(cot)
                muc = tieu_de_gan_nhat(chu_trang, " ".join(c for c in cot if c))
                for r, dong in enumerate(hang[1:], 1):
                    o = [_sach(c) for c in dong]
                    if not any(o) or _la_rac(*o):
                        continue
                    if len(ra) >= TRAN_HANG:
                        return ra
                    nhan = f"trang {i}"
                    if muc:
                        nhan += f" > {muc}"
                    nhan += f" > Bảng {k} hàng {r}"
                    ra.append(Trang(
                        so=BUOC_TRANG * i + (k - 1) * 1000 + r,
                        chu=" | ".join(o), nhan=nhan, o=o, cot=cot, loai_bang=loai))
    return ra
