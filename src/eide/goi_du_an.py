# -*- coding: utf-8 -*-
"""Xuất và nhập một dự án EIDE thành một tệp `.zip`.

## Vì sao cần, khi chép thư mục vốn đã chạy được

Chép thư mục **là** cách mang dự án đi, và nó đúng. Nhưng làm tay thì hai chuyện hay xảy ra,
và cả hai đều chỉ lộ ra về sau:

* **Chép cả đống.** Đo trên `stm32f469-freertos`: 14,5 MB, trong đó `.eide/build/` chiếm
  **3,0 MB** dựng lại được. Gửi qua thư thì đó là 3 MB không ai cần.
* **Lọc bằng cảm giác rồi bỏ mất sổ cái.** `.eide/` là thư mục ẩn, tên nó không gợi gì, và
  trong dự án nó còn bị `.gitignore`. Người gọn gàng sẽ bỏ nó — và mất toàn bộ lịch sử,
  changeset, phép hoàn tác, bản ưng ý. Mất im lặng: bản chép vẫn mở được, chỉ là không còn
  quá khứ.

Phân hạng `ben` / `dung_lai_duoc` / `tam` đã nằm sẵn trong `du-an.json` (xem `du_an.py`). Tệp
này chỉ làm đúng một việc: **đọc phân hạng ấy rồi làm theo**, thay vì để mỗi người tự nhớ.

## Nhập thì kiểm trước khi mở

Một gói mang sổ cái có chuỗi hash. Giải nén xong mà không kiểm thì một gói hỏng — hoặc bị sửa
— sẽ mở ra như bình thường và chỉ lộ ra ở một lúc nào đó rất xa. Nên `nhap()` **kiểm sổ cái
trước khi trả về**, và nếu gãy thì nói thẳng gãy ở đâu chứ không mở im lặng.

## Chỗ nó KHÔNG làm

Không nén thứ nằm ngoài thư mục dự án; không gộp hai dự án; không đổi dữ liệu. Gói xuất ra
**mở được bằng bất kỳ trình giải nén nào** — không có định dạng riêng, vì một định dạng riêng
là một thứ nữa phải bảo trì và một thứ nữa có thể mất khả năng đọc.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .du_an import HANG, TEN_TEP, ThongTinDuAn

# Tên tệp kê khai bên trong gói — để nhận ra một `.zip` có phải gói EIDE không mà không
# phải giải nén cả gói.
KE_KHAI = "eide-goi.json"
PHIEN_BAN_GOI = 1


@dataclass(slots=True)
class KetQuaXuat:
    tep: Path | None = None
    so_tep: int = 0
    byte_goi: int = 0
    da_bo: list[tuple[str, int]] = field(default_factory=list)
    vi_sao_khong_dat: str = ""

    @property
    def dat(self) -> bool:
        return self.tep is not None and not self.vi_sao_khong_dat

    def to_dict(self) -> dict[str, Any]:
        bo = sum(n for _, n in self.da_bo)
        return {
            "dat": self.dat, "tep": str(self.tep) if self.tep else None,
            "so_tep": self.so_tep, "byte_goi": self.byte_goi,
            "da_bo": [{"duong": d, "byte": n} for d, n in self.da_bo],
            "byte_da_bo": bo, "vi_sao_khong_dat": self.vi_sao_khong_dat,
        }


@dataclass(slots=True)
class KetQuaNhap:
    goc: Path | None = None
    so_tep: int = 0
    so_cai_toan_ven: bool | None = None
    so_cai_noi: str = ""
    vi_sao_khong_dat: str = ""

    @property
    def dat(self) -> bool:
        return self.goc is not None and not self.vi_sao_khong_dat


def _duoi_goc(goc: Path, p: Path) -> str:
    return str(p.relative_to(goc))


def xuat(goc: Path, ra: Path, *, gon: bool = True) -> KetQuaXuat:
    """Đóng gói dự án thành `.zip`.

    `gon=True` (mặc định) bỏ mọi thứ hạng `dung_lai_duoc` và `tam`. `gon=False` gói tất cả —
    dùng khi muốn một bản sao y hệt để dò lỗi, không phải để gửi đi.
    """
    kq = KetQuaXuat()
    goc = Path(goc)
    if not goc.is_dir():
        kq.vi_sao_khong_dat = f"{goc} không phải một thư mục."
        return kq

    bo_qua: set[str] = set()
    if gon:
        for d, h, _ in HANG:
            if h in ("dung_lai_duoc", "tam") and (goc / d).exists():
                n = sum(x.stat().st_size for x in (goc / d).rglob("*") if x.is_file()) \
                    if (goc / d).is_dir() else (goc / d).stat().st_size
                kq.da_bo.append((d, n))
                bo_qua.add(d)

    # Cập nhật `du-an.json` ngay trước khi gói: kê khai phải nói về thứ đang được gói, không
    # về lần mở trước.
    ThongTinDuAn(goc).ghi(ten=goc.name)

    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(ra, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(KE_KHAI, json.dumps({
                "goi": PHIEN_BAN_GOI, "ten_du_an": goc.name, "gon": gon,
                "da_bo": [{"duong": d, "byte": n} for d, n in kq.da_bo],
                "ghi_chu": ("Gói EIDE. Giải nén ra một thư mục rồi mở bằng EIDE, hoặc dùng "
                            "`goi_du_an.nhap`. Mục `da_bo` là thứ dựng lại được, cố ý không "
                            "gói theo."),
            }, ensure_ascii=False, indent=1))
            # Bỏ qua CHÍNH TỆP GÓI đang ghi.
            #
            # Gói thường được ghi vào trong dự án (công cụ `project.export` bắt buộc thế, để
            # không ghi ra ngoài hộp cát). Quét `rglob` trong lúc đang ghi sẽ bắt gặp chính
            # nó và gói nó vào chính nó — đo được: lệnh chạy mãi không dừng, tệp phình tới
            # khi hết đĩa. Một vòng lặp không có ai chặn, và nó chỉ lộ ra khi đã muộn.
            that = ra.resolve()
            for p in sorted(goc.rglob("*")):
                if not p.is_file() or p.resolve() == that:
                    continue
                rel = _duoi_goc(goc, p)
                if any(rel == b or rel.startswith(b + "/") for b in bo_qua):
                    continue
                z.write(p, rel)
                kq.so_tep += 1
    except OSError as e:
        kq.vi_sao_khong_dat = f"Không ghi được gói: {e}"
        return kq

    kq.tep = ra
    kq.byte_goi = ra.stat().st_size
    return kq


def nhap(goi: Path, den: Path) -> KetQuaNhap:
    """Giải nén một gói ra thư mục `den`, rồi **kiểm sổ cái trước khi trả về**."""
    kq = KetQuaNhap()
    goi, den = Path(goi), Path(den)
    if not goi.is_file():
        kq.vi_sao_khong_dat = f"Không có tệp gói ở {goi}."
        return kq
    if den.exists() and any(den.iterdir()):
        kq.vi_sao_khong_dat = (
            f"{den} đã có sẵn nội dung. Nhập vào một thư mục đang có dự án sẽ trộn hai lịch "
            "sử vào nhau — chọn thư mục rỗng.")
        return kq

    try:
        with zipfile.ZipFile(goi) as z:
            # Không giải nén thứ nằm ngoài thư mục đích. Một gói dựng bằng tay có thể mang
            # `../../` trong tên mục — giải nén thẳng là ghi đè tệp ngoài dự án.
            xau = [n for n in z.namelist()
                   if n.startswith("/") or ".." in Path(n).parts]
            if xau:
                kq.vi_sao_khong_dat = (
                    f"Gói có {len(xau)} mục trỏ ra ngoài thư mục đích ({xau[0]!r}…) — "
                    "không giải nén.")
                return kq
            den.mkdir(parents=True, exist_ok=True)
            for n in z.namelist():
                if n == KE_KHAI:
                    continue
                z.extract(n, den)
                kq.so_tep += 1
    except (OSError, zipfile.BadZipFile) as e:
        kq.vi_sao_khong_dat = f"Không đọc được gói: {e}"
        return kq

    kq.goc = den
    so_cai = den / ".eide" / "ledger.jsonl"
    if not so_cai.exists():
        kq.so_cai_toan_ven = None
        kq.so_cai_noi = ("Gói không có sổ cái — dự án này chưa chạy lượt nào, hoặc người gói "
                         "đã bỏ `.eide/`. Mở vẫn được, nhưng không có quá khứ.")
        return kq
    try:
        from .protocol.ledger import Ledger

        ok, vi = Ledger(so_cai).verify()
        kq.so_cai_toan_ven, kq.so_cai_noi = bool(ok), str(vi)
        if not ok:
            kq.vi_sao_khong_dat = f"Sổ cái trong gói KHÔNG toàn vẹn: {vi}"
    except Exception as e:                                             # noqa: BLE001
        kq.so_cai_toan_ven = None
        kq.so_cai_noi = f"Chưa kiểm được sổ cái: {e}"
    return kq
