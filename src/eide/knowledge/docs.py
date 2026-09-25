# -*- coding: utf-8 -*-
"""Kho tài liệu và trích Fact — EIDE-MDD-40 §C1, §C3.

Luồng bảy bước của §C3, và ai làm gì:

| Bước | Ai | Ở đâu trong mã |
|---|---|---|
| 1 Kích hoạt | người nạp / tác tử thấy chip chưa có datasheet | `passport.propose` |
| 2 Tìm | tác tử | `doc.search_web` |
| 3 Duyệt nguồn | **người** | thẻ cổng G-DATA |
| 4 Trích xuất | tác tử | `nap_tai_lieu` + `trich_fact_ung_vien` ở đây |
| 5 Rà soát | **người** | `xac_nhan_fact` → VÀNG |
| 6 Ghim hộ chiếu | tác tử | `passport.pin` |
| 7 Phòng thủ | tác tử | bọc `<document untrusted>`, quét P-INJ |

Câu quan trọng nhất của §C3 bước 4 nằm trong ngoặc:

    "bảng → Fact ứng viên (**giá trị đọc bằng mã**, mô hình chỉ ánh xạ tiêu đề cột lạ
     → key chuẩn)"

Nghĩa là con số **không bao giờ** đi qua mô hình. Mô hình được phép nói "cột tên
'Supply Voltage' ứng với khoá `vdd`", nhưng giá trị 5,5 thì do regex đọc từ trang PDF.
Đó là ranh giới giữa một hệ thống có thể kiểm chứng và một hệ thống phải tin lời.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Khoá chuẩn cho Fact — mô hình ánh xạ tiêu đề cột lạ về đây.
KHOA_CHUAN = {
    "vdd.min": "Điện áp cấp tối thiểu", "vdd.max": "Điện áp cấp tối đa",
    "vdd.typ": "Điện áp cấp danh định",
    "vih.min": "Mức logic cao tối thiểu ở đầu vào",
    "vil.max": "Mức logic thấp tối đa ở đầu vào",
    "voh.min": "Mức logic cao tối thiểu ở đầu ra",
    "vol.max": "Mức logic thấp tối đa ở đầu ra",
    "vddio.max": "Điện áp tối đa của chân I/O",
    "icc.typ": "Dòng tiêu thụ danh định", "icc.max": "Dòng tiêu thụ tối đa",
    "iol.max": "Dòng hút tối đa mỗi chân", "ioh.max": "Dòng đẩy tối đa mỗi chân",
    "flash.size": "Dung lượng Flash", "ram.size": "Dung lượng RAM",
    "eeprom.size": "Dung lượng EEPROM",
    "fmax": "Tần số hoạt động tối đa",
    "ta.min": "Nhiệt độ hoạt động tối thiểu", "ta.max": "Nhiệt độ hoạt động tối đa",
    "i2c.pullup.typ": "Điện trở kéo lên I2C danh định",
    "i2c.fmax": "Tốc độ I2C tối đa",
    "spi.fmax": "Tốc độ SPI tối đa",
    "throughput.max": "Thông lượng tối đa",
}

# Đơn vị → hệ số về đơn vị SI cơ bản, để so sánh không phụ thuộc cách viết.
_HE_SO: dict[str, tuple[float, str]] = {
    "v": (1, "V"), "mv": (1e-3, "V"), "kv": (1e3, "V"), "uv": (1e-6, "V"), "µv": (1e-6, "V"),
    "a": (1, "A"), "ma": (1e-3, "A"), "ua": (1e-6, "A"), "µa": (1e-6, "A"), "na": (1e-9, "A"),
    "hz": (1, "Hz"), "khz": (1e3, "Hz"), "mhz": (1e6, "Hz"), "ghz": (1e9, "Hz"),
    "s": (1, "s"), "ms": (1e-3, "s"), "us": (1e-6, "s"), "µs": (1e-6, "s"), "ns": (1e-9, "s"),
    "ω": (1, "Ω"), "ohm": (1, "Ω"), "kω": (1e3, "Ω"), "mω": (1e6, "Ω"),
    "f": (1, "F"), "uf": (1e-6, "F"), "µf": (1e-6, "F"), "nf": (1e-9, "F"), "pf": (1e-12, "F"),
    "b": (1, "B"), "kb": (1024, "B"), "mb": (1024**2, "B"), "gb": (1024**3, "B"),
    "°c": (1, "°C"), "%": (1, "%"),
    "bps": (1, "bps"), "kbps": (1e3, "bps"), "mbps": (1e6, "bps"),
    "b/s": (1, "B/s"), "kb/s": (1024, "B/s"), "mb/s": (1024**2, "B/s"),
}


def ve_si(gia_tri: float, don_vi: str) -> tuple[float, str]:
    """Đưa về đơn vị cơ bản. `4,7 kΩ` → `(4700.0, "Ω")`.

    Không có bước này thì `fact.compare` phải so `5000 mV` với `5 V` bằng chuỗi và sẽ
    kết luận sai — đúng loại lỗi mà một hệ thống "so sánh có bằng chứng" không được có.
    """
    he, co_ban = _HE_SO.get(don_vi.strip().lower(), (1.0, don_vi))
    return gia_tri * he, co_ban


# =========================================================================== tài liệu
@dataclass(slots=True)
class Trang:
    so: int
    chu: str


@dataclass(slots=True)
class TaiLieu:
    doc_id: str
    ten: str
    duong_dan: str
    hash: str
    so_trang: int
    phien_ban: str = ""
    nha_phat_hanh: str = ""
    trang: list[Trang] = field(default_factory=list)
    canh_bao_tiem_lenh: list[str] = field(default_factory=list)

    def to_canonical(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "title": self.ten, "path": self.duong_dan,
                "hash": self.hash, "pages": self.so_trang, "version": self.phien_ban,
                "publisher": self.nha_phat_hanh,
                "prompt_injection": self.canh_bao_tiem_lenh}


# §C3 bước 7 — nội dung tải về là DỮ LIỆU. Mẫu này chỉ để CẢNH BÁO người dùng;
# phòng thủ thật nằm ở chỗ nội dung luôn được bọc <document untrusted> khi vào ngữ cảnh.
_MAU_TIEM_LENH = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"bỏ qua (mọi|tất cả|các) (hướng dẫn|chỉ dẫn|quy tắc)", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|previous)", re.I),
    re.compile(r"you are now|from now on,? you", re.I),
    re.compile(r"(gửi|send)\s+(mã nguồn|source code|api key|khoá)", re.I),
    re.compile(r"rm\s+-rf", re.I),
]


def nap_tai_lieu(path: Path, *, doc_id: str, phien_ban: str = "",
                 nha_phat_hanh: str = "") -> TaiLieu:
    """Đọc PDF theo TRANG. Số trang là thứ người mở tài liệu ra kiểm được (N1)."""
    from pypdf import PdfReader

    data = path.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    r = PdfReader(str(path))
    trang = [Trang(i + 1, (p.extract_text() or "")) for i, p in enumerate(r.pages)]

    canh: list[str] = []
    for t in trang:
        for mau in _MAU_TIEM_LENH:
            m = mau.search(t.chu)
            if m:
                canh.append(f"trang {t.so}: “{m.group(0)[:60]}”")
                break

    meta = r.metadata or {}
    return TaiLieu(
        doc_id=doc_id, ten=path.name, duong_dan=str(path), hash=h,
        so_trang=len(trang), trang=trang,
        phien_ban=phien_ban or str(meta.get("/Title", "") or "")[:60],
        nha_phat_hanh=nha_phat_hanh or str(meta.get("/Author", "") or "")[:60],
        canh_bao_tiem_lenh=canh)


# =========================================================================== trích Fact
@dataclass(slots=True)
class FactUngVien:
    khoa: str
    gia_tri: float
    don_vi: str
    trang: int
    trich_doan: str
    thuc_the: str
    do_tin: float = 1.0
    nguyen_van: str = ""

    def to_dict(self) -> dict[str, Any]:
        si, dv = ve_si(self.gia_tri, self.don_vi)
        return {"khoa": self.khoa, "gia_tri": self.gia_tri, "don_vi": self.don_vi,
                "si": si, "don_vi_si": dv, "trang": self.trang,
                "trich_doan": self.trich_doan, "thuc_the": self.thuc_the,
                "do_tin": self.do_tin, "nguyen_van": self.nguyen_van}


# Mẫu nhận dạng: tên thông số (tiếng Anh trong datasheet) → khoá chuẩn.
_MAU_THONG_SO: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bV\s*DD\s*(?:\(?\s*max\s*\)?)", re.I), "vdd.max"),
    (re.compile(r"\bV\s*DD\s*(?:\(?\s*min\s*\)?)", re.I), "vdd.min"),
    (re.compile(r"\bsupply\s+voltage\b", re.I), "vdd.typ"),
    (re.compile(r"\bV\s*IH\b", re.I), "vih.min"),
    (re.compile(r"\bV\s*IL\b", re.I), "vil.max"),
    (re.compile(r"\bV\s*OH\b", re.I), "voh.min"),
    (re.compile(r"\bV\s*OL\b", re.I), "vol.max"),
    (re.compile(r"\bV\s*DDIO\b", re.I), "vddio.max"),
    (re.compile(r"\bflash\s+(memory|size)\b", re.I), "flash.size"),
    (re.compile(r"\b(SRAM|RAM)\s+(size|memory)?\b", re.I), "ram.size"),
    (re.compile(r"\bEEPROM\b", re.I), "eeprom.size"),
    (re.compile(r"\b(max(imum)?\s+)?(operating\s+)?frequency\b", re.I), "fmax"),
    (re.compile(r"\bI\s*CC\b|\bsupply\s+current\b", re.I), "icc.typ"),
    (re.compile(r"\bI\s*OL\b", re.I), "iol.max"),
    (re.compile(r"\bI\s*OH\b", re.I), "ioh.max"),
    (re.compile(r"\bpull-?up\b", re.I), "i2c.pullup.typ"),
    (re.compile(r"\bthroughput\b", re.I), "throughput.max"),
    (re.compile(r"\boperating\s+temperature\b", re.I), "ta.max"),
]

_SO_DON_VI = re.compile(
    r"(-?\d+(?:[.,]\d+)?)\s*"
    r"(kΩ|MΩ|Ω|ohm|mV|kV|µV|uV|V|mA|µA|uA|nA|A|GHz|MHz|kHz|Hz|"
    r"ms|µs|us|ns|s|µF|uF|nF|pF|F|GB|MB|KB|B|°C|%|Mbps|kbps|bps|MB/s|KB/s|B/s)"
    r"(?![A-Za-z])")


def trich_fact_ung_vien(tl: TaiLieu, *, thuc_the: str,
                        gioi_han: int = 200) -> list[FactUngVien]:
    """Đọc số từ trang PDF bằng MÃ, không qua mô hình (§C3 bước 4).

    Cách làm: tìm tên thông số trong một dòng, rồi lấy các số có đơn vị **trên chính
    dòng đó**. Datasheet trình bày dạng bảng, và sau khi trích chữ thì một hàng bảng
    thường thành một dòng — nên "cùng dòng" là xấp xỉ đủ tốt cho "cùng hàng".

    Mỗi ứng viên mang theo **số trang và trích đoạn nguyên văn**, để người rà soát mở
    đúng trang mà đối chiếu. Không có hai thứ đó thì Fact không truy vết được, và N1
    chỉ còn là một lời hứa.
    """
    ra: list[FactUngVien] = []
    for t in tl.trang:
        for dong in t.chu.splitlines():
            chu = dong.strip()
            if len(chu) < 3 or len(chu) > 400:
                continue
            khoa = None
            for mau, k in _MAU_THONG_SO:
                if mau.search(chu):
                    khoa = k
                    break
            if khoa is None:
                continue
            for m in _SO_DON_VI.finditer(chu):
                try:
                    gt = float(m.group(1).replace(",", "."))
                except ValueError:
                    continue
                ra.append(FactUngVien(
                    khoa=khoa, gia_tri=gt, don_vi=m.group(2), trang=t.so,
                    trich_doan=chu[:200], thuc_the=thuc_the, nguyen_van=m.group(0)))
                if len(ra) >= gioi_han:
                    return _gom(ra)
    return _gom(ra)


def _gom(ds: list[FactUngVien]) -> list[FactUngVien]:
    """Cùng khoá + cùng giá trị SI thì giữ một, ưu tiên trang sớm nhất."""
    thay: dict[tuple[str, float, str], FactUngVien] = {}
    for f in ds:
        si, dv = ve_si(f.gia_tri, f.don_vi)
        k = (f.khoa, round(si, 9), dv)
        if k not in thay or f.trang < thay[k].trang:
            thay[k] = f
    return sorted(thay.values(), key=lambda x: (x.khoa, x.trang))


def fact_tu_ung_vien(uv: FactUngVien, *, doc: TaiLieu, tier: str = "BAC") -> dict[str, Any]:
    """Ứng viên → bản ghi Fact. Mặc định **BẠC**: nguồn đã duyệt, dòng chưa xác nhận.

    §C1 nói chỉ lên VÀNG khi "người xác nhận dòng". Đặt thẳng VÀNG ở đây sẽ biến một
    phép đọc tự động thành một sự thật đã được kiểm — đúng thứ N1 tồn tại để ngăn.
    """
    si, dv = ve_si(uv.gia_tri, uv.don_vi)
    fid = "f-" + hashlib.sha1(
        f"{uv.thuc_the}|{uv.khoa}|{si}|{doc.hash[:8]}".encode()).hexdigest()[:10]
    return {
        "fact_id": fid, "subject": uv.thuc_the, "key": uv.khoa,
        "value": uv.gia_tri, "unit": uv.don_vi,
        "condition": "", "tier": tier, "origin": "extract",
        "source": {"doc_id": doc.doc_id, "version": doc.phien_ban,
                   "page": uv.trang, "quote": uv.trich_doan},
        "explain": {
            "summary": f"{KHOA_CHUAN.get(uv.khoa, uv.khoa)} = {uv.nguyen_van}",
            "why": f"Đọc bằng mã từ {doc.ten} trang {uv.trang}.",
            "sources": [{"kind": "doc", "ref": f"{doc.doc_id} tr.{uv.trang}",
                         "tier": tier}],
            "diff_prev": "bản đầu tiên",
            "next": ("Người xác nhận đúng dòng này để lên tầng VÀNG."
                     if tier == "BAC" else "—"),
            "confidence": tier,
        },
    }
