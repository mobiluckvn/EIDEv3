# -*- coding: utf-8 -*-
"""Phân loại sửa của người và hệ quả — EIDE-MDD-40 §E4.1.

| Loại sửa | Nhận biết | Tác tử làm gì |
|---|---|---|
| Nội dung | Diff chạm trường có nghĩa | Nhắc + STALE + đề nghị chạy lại hạ nguồn |
| Quyết định | Diff chạm `choice`/`chosen` | ADR mới; hỏi giữ nhánh cũ hay bỏ |
| Trình bày | Diff chỉ chạm `label`/`order`/`note` | Nhắc ngắn; **không STALE**; học thói quen |
| Bác bỏ | Đánh dấu "không phải lỗi"/"không đúng ý tôi" | Ghi vào EIDE.md §Đừng; không đề xuất lại |
| lock_broken | HumanAct edit có lock_broken | Dừng sửa tệp đó; 3-way merge; trình diff |

Vì sao việc phân loại này đáng có mã riêng: nếu mọi sửa đều gây STALE thì đổi tên một
khối sẽ làm cả chuỗi hạ nguồn sáng đèn cảnh báo. Người sẽ học được rằng băng cảnh báo
không có nghĩa gì, và lần STALE thật sự quan trọng sẽ bị bỏ qua. Ca CX08 đo đúng chỗ đó.

Phần thứ hai của tệp này là **Fact tầng NGƯỜI tự động** (§E4 bước 3, ca CX05):

    "Số mới trong sửa không có nguồn → tạo Fact tầng NGƯỜI với source = human_act"

Người sửa tiêu chí từ "≥ 1 MB/s" thành "≥ 5 MB/s". Con số 5 chưa từng có trong tài
liệu nào. Nhưng nó cũng không phải phỏng đoán của mô hình — **người dùng khẳng định
nó**, và họ là một nguồn có tên. Nên nó thành Fact tầng NGƯỜI: dùng được để so sánh và
sinh mã như VÀNG, nhưng mọi nơi dùng đều ghi "(anh cho, chưa có tài liệu)", và tác tử
nên đề nghị tìm tài liệu để nâng lên VÀNG.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Trường chỉ ảnh hưởng tới cách trình bày — sửa chúng không làm hạ nguồn lỗi thời.
TRUONG_TRINH_BAY = frozenset({
    "label", "ten", "tieu_de", "order", "thu_tu", "note", "ghi_chu", "mo_ta_ngan",
    "nhom", "mau", "bi_danh",
})

# Trường mang một quyết định.
TRUONG_QUYET_DINH = frozenset({"chon", "choice", "chosen", "da_chon", "quyet_boi"})

# Số có đơn vị kỹ thuật — ứng viên thành Fact.
_SO_CO_DON_VI = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(ms|µs|us|ns|s|Hz|kHz|MHz|GHz|mV|V|kV|mA|uA|µA|A|mAh|Ah|W|mW|"
    r"kΩ|MΩ|Ω|ohm|uF|µF|nF|pF|mH|uH|dB|dBm|bps|kbps|Mbps|Gbps|B/s|KB/s|MB/s|GB/s|"
    r"KB|MB|GB|TB|°C|%)",
    re.IGNORECASE)


@dataclass(slots=True)
class PhanLoai:
    loai: str                      # noi_dung | quyet_dinh | trinh_bay | bac_bo | lock_broken
    truong_doi: list[str] = field(default_factory=list)
    gay_stale: bool = True
    ly_do: str = ""

    @property
    def mo_ta_vi(self) -> str:
        return {
            "noi_dung": "sửa nội dung",
            "quyet_dinh": "đổi quyết định",
            "trinh_bay": "sửa cách trình bày",
            "bac_bo": "bác bỏ",
            "lock_broken": "sửa tệp tác tử đang giữ",
        }.get(self.loai, self.loai)


def phan_loai(*, truoc: dict[str, Any], sau: dict[str, Any],
              lock_broken: bool = False, bac_bo: bool = False) -> PhanLoai:
    """Xếp loại một lần sửa của người theo §E4.1."""
    if lock_broken:
        return PhanLoai("lock_broken", ly_do="người sửa tệp tác tử đang giữ soft-lock")
    if bac_bo:
        return PhanLoai("bac_bo", gay_stale=False,
                        ly_do="người bác bỏ một phát hiện hoặc một đề xuất")

    doi = [k for k in set(truoc) | set(sau) if truoc.get(k) != sau.get(k)]
    if not doi:
        return PhanLoai("trinh_bay", gay_stale=False, ly_do="không có gì đổi")

    if any(k in TRUONG_QUYET_DINH for k in doi):
        return PhanLoai("quyet_dinh", doi, ly_do="chạm trường mang quyết định")

    if all(k in TRUONG_TRINH_BAY for k in doi):
        # CX08 — đổi tên khối không làm mã lỗi thời.
        return PhanLoai("trinh_bay", doi, gay_stale=False,
                        ly_do="chỉ chạm trường trình bày")

    return PhanLoai("noi_dung", doi, ly_do="chạm trường có nghĩa")


# =========================================================================== Fact NGƯỜI
@dataclass(slots=True)
class SoMoi:
    gia_tri: str
    don_vi: str
    truong: str
    nguyen_van: str

    @property
    def khoa(self) -> str:
        """Khoá Fact suy từ tên trường — `criteria` → `criteria.nguong`."""
        return f"{self.truong}.{_ten_theo_don_vi(self.don_vi)}"


def so_moi_khong_nguon(*, truoc: dict[str, Any], sau: dict[str, Any],
                       nguon_da_co: str) -> list[SoMoi]:
    """Tìm số có đơn vị VỪA XUẤT HIỆN trong bản sửa mà chưa truy vết được.

    `nguon_da_co` là khối chữ gom từ Fact đã có + EIDE.md — cùng nguồn mà
    constant-guard dùng, để hai lớp không nói hai điều khác nhau về cùng một con số.
    """
    ra: list[SoMoi] = []
    for truong, gia_tri_sau in sau.items():
        if not isinstance(gia_tri_sau, str):
            continue
        cu = str(truoc.get(truong, ""))
        so_cu = {m.group(0) for m in _SO_CO_DON_VI.finditer(cu)}
        for m in _SO_CO_DON_VI.finditer(gia_tri_sau):
            if m.group(0) in so_cu:
                continue                       # số này vốn đã có, không phải cái mới
            so = m.group(1).replace(",", ".")
            if so in nguon_da_co:
                continue                       # đã truy vết được ở đâu đó
            ra.append(SoMoi(gia_tri=m.group(1), don_vi=m.group(2),
                            truong=truong, nguyen_van=m.group(0)))
    return ra


def _ten_theo_don_vi(dv: str) -> str:
    d = dv.lower()
    if d in ("ms", "µs", "us", "ns", "s"):
        return "thoi_gian"
    if d in ("hz", "khz", "mhz", "ghz"):
        return "tan_so"
    if d in ("mv", "v", "kv"):
        return "dien_ap"
    if d in ("ma", "ua", "µa", "a", "mah", "ah"):
        return "dong"
    if d in ("kω", "mω", "ω", "ohm"):
        return "tro_khang"
    if d in ("uf", "µf", "nf", "pf", "mh", "uh"):
        return "linh_kien"
    if d in ("bps", "kbps", "mbps", "gbps", "b/s", "kb/s", "mb/s", "gb/s"):
        return "thong_luong"
    if d in ("kb", "mb", "gb", "tb"):
        return "dung_luong"
    if d == "°c":
        return "nhiet_do"
    if d == "%":
        return "ty_le"
    return "gia_tri"


def tao_fact_nguoi(store: Any, *, hien_vat: str, so: SoMoi, trich_loi: str,
                   human_act_id: str) -> dict[str, Any]:
    """Ghi một Fact tầng NGƯỜI từ con số người vừa nhập.

    `origin=user`, `tier=NGUOI`, `source` mang trích lời họ. §C1 nói tầng NGƯỜI dùng
    được **như VÀNG** cho so sánh và sinh mã — nhưng mọi nơi dùng đều phải ghi
    "(anh cho, chưa có tài liệu)", và tác tử nên đề nghị tìm tài liệu nâng lên VÀNG.
    """
    fid = f"f-nguoi-{abs(hash((hien_vat, so.khoa))) % 10**8}"
    store.put_fact({
        "fact_id": fid,
        "subject": hien_vat,
        "key": so.khoa,
        "value": so.gia_tri,
        "unit": so.don_vi,
        "tier": "NGUOI",
        "origin": "user",
        "source": {"human_act_id": human_act_id, "quote": trich_loi},
        "explain": {
            "summary": f"{so.khoa} = {so.nguyen_van} — anh đặt khi sửa {hien_vat}",
            "why": "Người dùng khẳng định con số này; chưa có tài liệu nào xác thực.",
            "sources": [{"kind": "human_act", "ref": human_act_id, "tier": "NGUOI"}],
            "diff_prev": "bản đầu tiên",
            "next": "Tìm tài liệu để nâng lên tầng VÀNG.",
            "confidence": "NGUOI",
        },
    })
    return {"fact_id": fid, "key": so.khoa, "value": so.nguyen_van}


def loi_nhac_fact_nguoi(ds: list[dict[str, Any]]) -> str:
    """Câu tác tử nói khi vừa ghi Fact tầng NGƯỜI từ sửa của người."""
    if not ds:
        return ""
    muc = ", ".join(f"**{f['key']} = {f['value']}**" for f in ds)
    nhieu = len(ds) > 1
    return (f"Con số {muc} anh vừa đặt chưa có trong tài liệu nào, nên tôi ghi "
            f"{'chúng' if nhieu else 'nó'} ở **tầng NGƯỜI** — dùng được để so sánh và "
            f"sinh mã, nhưng mọi chỗ dùng tôi sẽ ghi rõ *(anh cho, chưa có tài liệu)*. "
            f"Muốn tôi đi tìm tài liệu để nâng lên tầng VÀNG không?")
