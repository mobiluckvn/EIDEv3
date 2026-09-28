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
    """Một ĐƠN VỊ TRÍCH DẪN. Với PDF là một trang; với Office thì không phải.

    `nhan` tồn tại vì ING-43 §4.2 đòi trích dẫn **theo loại tài liệu**: `.docx` không có
    số trang cố định nên trích dẫn của nó là đường tiêu đề + số bảng; `.xlsx` là
    `Sheet!ô`; `.pptx` là số slide. Ép hết về "trang N" thì người mở tệp ra không tìm
    được chỗ ta đang nói tới — mà tìm được chính là toàn bộ điểm của N1.

    `so` vẫn giữ để sắp thứ tự và để đường PDF cũ chạy y nguyên.
    """

    so: int
    chu: str
    nhan: str = ""            # "3.2 Electrical > Bảng 4" · "Sheet1!A1:D20" · "slide 12"
    # Khi đơn vị này là một HÀNG BẢNG: từng ô, và tiêu đề cột của bảng.
    # Đơn vị đo trong datasheet nằm ở cột riêng, nên đọc bảng như một dòng chữ là
    # đánh mất liên hệ giữa con số và đơn vị của nó.
    o: list[str] = field(default_factory=list)
    cot: list[str] = field(default_factory=list)
    # "thong_so" (số kèm đơn vị) · "chan" (bản đồ chân) · "" (bảng trình bày).
    # Hai loại bảng này được ĐỌC khác nhau: bảng thông số cho ra số, bảng chân cho ra
    # quan hệ chân ↔ net ↔ hướng. Gộp chúng thì một trong hai bị đọc sai.
    loai_bang: str = ""

    @property
    def trich_dan(self) -> str:
        return self.nhan or f"trang {self.so}"

    @property
    def la_hang_bang(self) -> bool:
        return bool(self.o and self.cot)


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
    loai: str = "pdf"              # pdf | docx | xlsx | pptx
    don_vi_trich_dan: str = "trang"    # trang | mục | ô | slide
    chuyen_doi_tu: str = ""        # ING-43 §4.2 — "đã chuyển đổi" phải nói ra
    pdf_phai_sinh: str = ""        # bản PDF sinh ra để có số trang, cùng doc_id

    def to_canonical(self) -> dict[str, Any]:
        return {"doc_id": self.doc_id, "title": self.ten, "path": self.duong_dan,
                "hash": self.hash, "pages": self.so_trang, "version": self.phien_ban,
                "publisher": self.nha_phat_hanh, "loai": self.loai,
                "don_vi_trich_dan": self.don_vi_trich_dan,
                "converted_from": self.chuyen_doi_tu,
                "pdf_phai_sinh": self.pdf_phai_sinh,
                "prompt_injection": self.canh_bao_tiem_lenh}

    def don_vi(self, so: int) -> Trang | None:
        return next((t for t in self.trang if t.so == so), None)

    def trich_dan(self, so: int) -> str:
        t = self.don_vi(so)
        return t.trich_dan if t else f"{self.don_vi_trich_dan} {so}"


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


# Bao nhiêu dòng thành một đơn vị trích dẫn cho tài liệu văn bản. 40 dòng vừa một màn hình
# biên tập: người đọc "dòng 121–160" mở tệp ra là thấy ngay chỗ đó, mà đơn vị vẫn đủ hẹp để
# `fact.from_doc` kiểm được giá trị có nằm trong đó thật (N1).
DONG_MOI_DON_VI = 40
TRAN_CHU_VAN_BAN = 8 * 1024 * 1024


def nap_van_ban(path: Path, *, doc_id: str, loai: str = "text", phien_ban: str = "",
                nha_phat_hanh: str = "", dong_moi_don_vi: int = DONG_MOI_DON_VI) -> TaiLieu:
    """Nạp tài liệu dạng VĂN BẢN (mã nguồn, header, linker script, Markdown, log).

    Trước bước này `phan_loai` nhận ra mã nguồn và nói `doc_duoc=True`, nhưng `doc.load` chỉ
    có đường cho PDF và Office — nên tác tử được bảo là "đọc được" rồi bị từ chối ở bước sau.
    Đo trên bo STM32F469 ngày 27/09/2026: tài liệu chân của kit mà còn với tới được lại là
    **header BSP do chính hãng viết**, và không nạp được nó nghĩa là không có Fact chân nào có
    trích dẫn.

    Đơn vị trích dẫn là KHOẢNG DÒNG, không phải "trang": tệp văn bản không có trang, và bịa ra
    số trang thì người mở tệp ra không kiểm lại được — mất đúng thứ N1 tồn tại để bảo vệ.
    """
    data = path.read_bytes()
    if len(data) > TRAN_CHU_VAN_BAN:
        raise ValueError(
            f"{path.name} nặng {len(data) / 1e6:.1f} MB, vượt trần "
            f"{TRAN_CHU_VAN_BAN / 1e6:.0f} MB cho tài liệu văn bản.")
    h = hashlib.sha256(data).hexdigest()
    chu = data.decode("utf-8", errors="replace")
    dong = chu.splitlines()

    buoc = max(1, dong_moi_don_vi)
    trang: list[Trang] = []
    for i in range(0, max(len(dong), 1), buoc):
        khuc = dong[i:i + buoc]
        dau, cuoi = i + 1, i + len(khuc)
        trang.append(Trang(len(trang) + 1, "\n".join(khuc),
                           nhan=(f"dòng {dau}" if dau == cuoi else f"dòng {dau}–{cuoi}")))

    canh: list[str] = []
    for t in trang:
        for mau in _MAU_TIEM_LENH:
            m = mau.search(t.chu)
            if m:
                canh.append(f"{t.trich_dan}: “{m.group(0)[:60]}”")
                break

    return TaiLieu(
        doc_id=doc_id, ten=path.name, duong_dan=str(path), hash=h,
        so_trang=len(trang), trang=trang, loai=loai, don_vi_trich_dan="dòng",
        phien_ban=phien_ban, nha_phat_hanh=nha_phat_hanh, canh_bao_tiem_lenh=canh)


# ======================================================= trích từ #define (ING-43, tài liệu mã)
# `#define TEN     GIA_TRI` — có thể có ngoặc, ép kiểu, chú thích đuôi.
_MAU_DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+?)\s*(?:/\*.*)?$")
# Cặp khai chân của header BSP nhà sản xuất: `X_GPIO_PORT` + `X_PIN`.
_HAU_TO_CONG = ("_GPIO_PORT", "_GPIO_Port", "_PORT")
_HAU_TO_CHAN = ("_PIN", "_Pin")
_CONG_TRONG_GT = re.compile(r"\bGPIO([A-K])\b")
_SO_CHAN_TRONG_GT = re.compile(r"\bGPIO_PIN_(\d{1,2})\b|\b(?:1[uUlL]*\s*<<\s*)(\d{1,2})\b")


@dataclass(slots=True)
class DinhNghiaUngVien:
    """Một `#define` đọc được từ tài liệu mã nguồn, kèm chỗ nó nằm."""

    ten: str
    gia_tri: str
    don_vi_trich_dan: int
    nguyen_van: str

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.ten, "gia_tri": self.gia_tri,
                "don_vi": self.don_vi_trich_dan, "nguyen_van": self.nguyen_van}


def trich_dinh_nghia(tl: TaiLieu, *, gioi_han: int = 400) -> list[DinhNghiaUngVien]:
    """Mọi `#define` trong một tài liệu VĂN BẢN, kèm đơn vị trích dẫn chứa nó.

    Vì sao cần bộ trích riêng: `trich_fact_ung_vien` khớp theo tên thông số điện của datasheet
    (VDD, VIH, nhiệt độ…). Một header BSP không có chữ nào trong bộ mẫu đó, nên nó trả **0 ứng
    viên và vẫn báo thành công** — đo được trên bo STM32F469: tác tử gọi `fact.extract` hai
    lần, cả hai `ok`, kho vẫn rỗng, rồi nó viết firmware bằng số đọc được từ tài liệu mà
    **không có Fact nào đứng sau**. Đó đúng là thứ N1 tồn tại để ngăn.
    """
    ra: list[DinhNghiaUngVien] = []
    for t in tl.trang:
        for i, dong in enumerate(t.chu.splitlines()):
            m = _MAU_DEFINE.match(dong)
            if not m:
                continue
            gt = m.group(2).strip()
            if not gt or gt.startswith("\\"):        # macro nhiều dòng — bỏ, không đoán
                continue
            ra.append(DinhNghiaUngVien(ten=m.group(1), gia_tri=gt[:120],
                                       don_vi_trich_dan=t.so, nguyen_van=dong.strip()[:160]))
            if len(ra) >= gioi_han:
                return ra
    return ra


def ghep_chan_tu_dinh_nghia(ds: list[DinhNghiaUngVien]) -> dict[str, dict[str, Any]]:
    """`{"LED1": {"chan": "PG6", "don_vi": [3, 3], "nguyen_van": [...]}}`.

    Ghép `X_GPIO_PORT` với `X_PIN` theo **cùng tiền tố X**, không theo thứ tự xuất hiện: ghép
    theo thứ tự sẽ nối cổng của khai báo này với số chân của khai báo kia và tạo ra một chân
    không tồn tại — sai mà trông đúng.
    """
    cong: dict[str, DinhNghiaUngVien] = {}
    so: dict[str, DinhNghiaUngVien] = {}
    for d in ds:
        for h in _HAU_TO_CONG:
            if d.ten.endswith(h):
                cong[d.ten[: -len(h)]] = d
                break
        else:
            for h in _HAU_TO_CHAN:
                if d.ten.endswith(h):
                    so[d.ten[: -len(h)]] = d
                    break

    ra: dict[str, dict[str, Any]] = {}
    for ten in sorted(set(cong) & set(so)):
        mc = _CONG_TRONG_GT.search(cong[ten].gia_tri)
        ms = _SO_CHAN_TRONG_GT.search(so[ten].gia_tri)
        if not mc or not ms:
            continue
        n = ms.group(1) or ms.group(2)
        ra[ten] = {"chan": f"P{mc.group(1)}{n}",
                   "cong": f"GPIO{mc.group(1)}", "so_chan": int(n),
                   "don_vi": [cong[ten].don_vi_trich_dan, so[ten].don_vi_trich_dan],
                   "nguyen_van": [cong[ten].nguyen_van, so[ten].nguyen_van]}
    return ra


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
    dieu_kien: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        si, dv = ve_si(self.gia_tri, self.don_vi)
        return {"khoa": self.khoa, "gia_tri": self.gia_tri, "don_vi": self.don_vi,
                "si": si, "don_vi_si": dv, "trang": self.trang,
                "trich_doan": self.trich_doan, "thuc_the": self.thuc_the,
                "do_tin": self.do_tin, "nguyen_van": self.nguyen_van,
                "dieu_kien": dict(self.dieu_kien)}


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
        # --- Hàng bảng: đọc theo CỘT. Đơn vị nằm ở cột riêng, giá trị ở cột Min/Typ/Max.
        if t.la_hang_bang:
            ra.extend(_tu_hang_bang(t, thuc_the))
            if len(ra) >= gioi_han:
                return _gom(ra[:gioi_han])
            continue
        for dong in t.chu.splitlines():
            chu = dong.strip()
            if len(chu) < 3 or len(chu) > 400:
                continue
            if _la_dong_dia_chi(chu):
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
                if not hop_ly(khoa, gt, m.group(2)):
                    continue
                ra.append(FactUngVien(
                    khoa=khoa, gia_tri=gt, don_vi=m.group(2), trang=t.so,
                    trich_doan=chu[:200], thuc_the=thuc_the, nguyen_van=m.group(0)))
                if len(ra) >= gioi_han:
                    return _gom(ra)
    return _gom(ra)


# Dòng khai ĐỊA CHỈ, không phải khai giá trị. Trong một header CMSIS,
# `#define FLASHSIZE_BASE 0x1FFF7A22UL /*!< FLASH Size register base address */`
# khớp mẫu "FLASH Size" nhưng con số trong đó là **địa chỉ của thanh ghi ghi kích thước**,
# không phải kích thước. Đo được trên bo STM32F469: dòng này sinh ra Fact `flash.size = 7.0`,
# rồi `build.compile` lấy nó làm hạn mức và báo firmware 224 byte chiếm **320 % Flash**.
_MAU_DIA_CHI = re.compile(
    r"#\s*define\s+\w*(?:_BASE|_ADDR|_ADDRESS|_REG)\b|base\s+address|register\s+base", re.I)


def _la_dong_dia_chi(chu: str) -> bool:
    return bool(_MAU_DIA_CHI.search(chu))


# Khoảng giá trị hợp lý cho từng khoá, theo ĐƠN VỊ CƠ BẢN (V, A, Hz, byte, °C).
# Đây là cái phanh cuối: một mẫu khớp nhầm dòng vẫn có thể cho ra một con số, và một con số
# vô lý đi tiếp được vào mọi phép tính phía sau mà không ai chặn. Thà bỏ một Fact đúng hiếm
# gặp còn hơn để một Fact sai thành hạn mức bộ nhớ.
PHAM_VI_HOP_LY: dict[str, tuple[float, float]] = {
    "flash.size": (1024, 64 * 1024 * 1024),
    "ram.size": (64, 64 * 1024 * 1024),
    "sram.size": (64, 64 * 1024 * 1024),
    "eeprom.size": (16, 1024 * 1024),
    "vdd.min": (0.5, 60), "vdd.max": (0.5, 60), "vdd.typ": (0.5, 60),
    "vih.min": (0.3, 60), "vil.max": (0.0, 60),
    "f.max": (1_000, 2_000_000_000),
    "temp.min": (-100, 200), "temp.max": (-100, 200),
}

_NHAN_DON_VI = {
    "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "n": 1e-9,
}


def ve_don_vi_co_ban(gia_tri: float, don_vi: str) -> float:
    """`2 MB` → 2 000 000. Đơn vị lạ thì trả nguyên giá trị."""
    dv = (don_vi or "").strip()
    if len(dv) >= 2 and dv[0] in _NHAN_DON_VI:
        return gia_tri * _NHAN_DON_VI[dv[0]]
    # `KB`/`MB` viết liền, và dạng `Kbyte`/`Mbytes`.
    m = re.match(r"^([kKMG])(?:B|byte|bytes|b)$", dv)
    if m:
        return gia_tri * _NHAN_DON_VI[m.group(1)]
    return gia_tri


def doc_so(gt: Any) -> float | None:
    """Chuỗi số trong tài liệu → số. `None` nếu không đọc ra số.

    Cái khó duy nhất ở đây là dấu chấm: `2.097.152` là hai triệu (kiểu Âu), còn `2097152.0`
    là hai triệu *đã* viết dấu thập phân. Bản trước xoá sạch mọi dấu chấm, nên
    `"2097152.0"` thành `20971520` — **hạn mức Flash gấp mười lần chip thật**, và một hạn
    mức quá rộng không bao giờ kêu: firmware nào cũng "vừa", kể cả bản 3 MB không nạp được.

    Quy tắc: dấu chấm/phẩy chỉ là dấu phân nhóm nghìn khi nó CHIA THÀNH ĐÚNG NHÓM BA CHỮ SỐ
    (`1.234`, `2.097.152`). Mọi trường hợp khác nó là dấu thập phân.

    Chỗ còn mơ hồ, nói ra để không ai tin quá: một mình chuỗi `1.234` thì không cách nào biết
    nó là *một nghìn hai trăm ba mươi tư* hay *một phẩy hai ba tư* — hàm này chọn nghĩa thứ
    nhất. Phanh thứ hai là `hop_ly()`: giá trị ra khỏi khoảng hợp lý của khoá thì bị bỏ, nên
    một lần đoán sai nghĩa thường thành "không có số" chứ không thành "số sai".
    """
    s = str(gt).strip().replace(" ", "").replace("_", "")
    if not s:
        return None
    dau = "-" if s[0] == "-" else ""
    s = s.lstrip("+-")
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", s):
        return float(int(s, 16))
    co_cham, co_phay = "." in s, "," in s
    if co_cham and co_phay:
        # Cái nào ở sau là dấu thập phân; cái kia là phân nhóm nghìn.
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    else:
        for d in (".", ","):
            if d in s and re.fullmatch(r"\d{1,3}(?:\%s\d{3})+" % d, s):
                s = s.replace(d, "")       # đúng nhóm ba → phân nhóm nghìn
                break
        s = s.replace(",", ".")            # còn lại thì đó là dấu thập phân
    try:
        return float(dau + s)
    except ValueError:
        return None


def hop_ly(khoa: str, gia_tri: float, don_vi: str) -> bool:
    """Giá trị này có thể là thứ mà khoá đó nói tới không."""
    pv = PHAM_VI_HOP_LY.get(khoa)
    if pv is None:
        return True                       # chưa có khoảng cho khoá này thì không chặn
    co_ban = ve_don_vi_co_ban(gia_tri, don_vi)
    return pv[0] <= co_ban <= pv[1]


# Tên cột → hậu tố khoá. "VDD" ở cột Max thành `vdd.max`, ở cột Min thành `vdd.min`.
_HAU_TO_COT = {
    "min": "min", "minimum": "min", "nhỏ nhất": "min",
    "typ": "typ", "typical": "typ", "nom": "typ", "value": "typ", "giá trị": "typ",
    "max": "max", "maximum": "max", "lớn nhất": "max", "rating": "max",
}
_COT_DON_VI = {"unit", "units", "đơn vị"}
_COT_TEN = {"parameter", "symbol", "thông số", "ký hiệu", "tên"}


def _tu_hang_bang(t: "Trang", thuc_the: str) -> list["FactUngVien"]:
    """Một hàng bảng → các Fact ứng viên, mỗi cột giá trị một cái.

    Vì sao phải đọc theo cột thay vì theo dòng chữ: datasheet đặt đơn vị ở **cột riêng**
    ("VDD max | 2.7 | 5.5 | V"). Nối cả hàng thành một chuỗi rồi tìm "số kèm đơn vị" thì
    `5.5` và `V` cách nhau một dấu gạch và không bao giờ khớp — bộ trích sẽ trả về rỗng
    trên đúng loại tài liệu nó sinh ra để đọc.
    """
    thap = [str(c).strip().lower() for c in t.cot]
    i_don_vi = next((i for i, c in enumerate(thap) if c in _COT_DON_VI), None)
    don_vi_chung = (str(t.o[i_don_vi]).strip()
                    if i_don_vi is not None and i_don_vi < len(t.o) else "")

    ten = ""
    for i, c in enumerate(thap):
        if c in _COT_TEN and i < len(t.o) and str(t.o[i]).strip():
            ten = str(t.o[i]).strip()
            break
    if not ten:
        ten = str(t.o[0]).strip() if t.o else ""
    if not ten:
        return []

    khoa_goc = None
    for mau, k in _MAU_THONG_SO:
        if mau.search(ten):
            khoa_goc = k.rsplit(".", 1)[0]
            break
    if khoa_goc is None:
        return []

    from .chuan_hoa import chuan_hoa

    # Chú thích của hàng (Note 1, Note 2) và điều kiện ghi ngay trong ô Conditions.
    dieu_kien_hang: dict[str, str] = {}
    for i, c in enumerate(thap):
        if c in ("conditions", "condition", "điều kiện") and i < len(t.o):
            dieu_kien_hang.update(__import__(
                "eide.knowledge.chuan_hoa", fromlist=["x"]).tach_dieu_kien(str(t.o[i])))

    ra: list[FactUngVien] = []
    for i, c in enumerate(thap):
        hau_to = _HAU_TO_COT.get(c)
        if hau_to is None or i >= len(t.o):
            continue
        g = chuan_hoa(str(t.o[i]), don_vi_cot=don_vi_chung, ngu_canh=ten)
        if not g.co_so:
            # Ô ghi "—", "N/A", "TBD": KHÔNG tạo Fact, và không biến thành 0. Ô như thế
            # là một thông tin ("chưa có số"), nhưng nó không phải một con số.
            continue

        # Một ô có thể chứa cả min/typ/max hoặc một dải — tách thành nhiều ứng viên,
        # mỗi cái mang đúng hậu tố của nó, thay vì nhét cả cụm vào một khoá.
        cap: list[tuple[str, float]] = []
        if g.la_dai or g.vtyp is not None:
            for ht, v in (("min", g.vmin), ("typ", g.vtyp), ("max", g.vmax)):
                if v is not None:
                    cap.append((ht, v))
        elif g.gia_tri is not None:
            cap.append((hau_to, g.gia_tri))

        for ht, v in cap:
            ra.append(FactUngVien(
                khoa=f"{khoa_goc}.{ht}", gia_tri=v, don_vi=g.don_vi, trang=t.so,
                trich_doan=t.chu[:200], thuc_the=thuc_the,
                nguyen_van=g.raw.strip(),
                dieu_kien={**dieu_kien_hang, **g.dieu_kien}))
    return ra


def _gom(ds: list[FactUngVien]) -> list[FactUngVien]:
    """Cùng khoá + cùng giá trị SI thì giữ một, ưu tiên trang sớm nhất."""
    thay: dict[tuple[str, float, str], FactUngVien] = {}
    for f in ds:
        si, dv = ve_si(f.gia_tri, f.don_vi)
        k = (f.khoa, round(si, 9), dv)
        if k not in thay or f.trang < thay[k].trang:
            thay[k] = f
    return sorted(thay.values(), key=lambda x: (x.khoa, x.trang))


# ING-43 §6 — tầng mặc định theo NGUỒN, không theo định dạng.
#
# Quyết định của chủ sản phẩm 25/09/2026 cho ING-19: tài liệu Office do người dùng hoặc
# đồng nghiệp tự viết gán tầng **NGƯỜI**, không phải BẠC. Lý do nằm ở chỗ Fact đó sẽ
# được đọc lại sáu tháng sau: tầng NGƯỜI vẫn so sánh được (nó nằm trong TANG_DUNG_DUOC),
# nhưng trích dẫn của nó trỏ về *người*, không trỏ về datasheet — nên khi in ra, người
# đọc thấy ngay đây là số nội bộ. Gán BẠC thì nó đứng ngang hàng datasheet nhà sản xuất
# trong mọi bảng so sánh, và không ai phân biệt được nữa.
TANG_THEO_NGUON = {
    "nha_san_xuat": "BAC",     # đã duyệt nguồn, chưa xác nhận từng dòng
    "ben_thu_ba": "BAC",       # cùng tầng nhưng mang nhãn "bên thứ ba"
    "noi_bo": "NGUOI",         # người tự viết — không có tài liệu chuẩn đứng sau
}


def tang_mac_dinh(nguon: str, loai: str = "pdf") -> str:
    """Tầng cho Fact trích từ một tài liệu. Nguồn lạ thì chọn phía thận trọng."""
    return TANG_THEO_NGUON.get(nguon, "NGUOI")


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
        "condition": "; ".join(f"{k}={v}" for k, v in sorted(uv.dieu_kien.items())),
        "tier": tier, "origin": "extract",
        "source": {"doc_id": doc.doc_id, "version": doc.phien_ban,
                   "page": uv.trang, "cite": doc.trich_dan(uv.trang),
                   "quote": uv.trich_doan},
        "explain": {
            "summary": f"{KHOA_CHUAN.get(uv.khoa, uv.khoa)} = {uv.nguyen_van}",
            "why": f"Đọc bằng mã từ {doc.ten}, {doc.trich_dan(uv.trang)}.",
            "sources": [{"kind": "doc",
                         "ref": f"{doc.doc_id} · {doc.trich_dan(uv.trang)}",
                         "tier": tier}],
            "diff_prev": "bản đầu tiên",
            "next": ("Người xác nhận đúng dòng này để lên tầng VÀNG."
                     if tier == "BAC" else
                     "Tìm tài liệu chuẩn chứng thực để nâng lên VÀNG."
                     if tier == "NGUOI" else "—"),
            "confidence": tier,
        },
    }


# =================================================== bản đồ chân từ bảng (ING-43 §5, N1)
@dataclass(slots=True)
class ChanUngVien:
    """Một hàng của bảng bản đồ chân, đã tách thành các phần có nghĩa.

    Khác `FactUngVien` ở bản chất: ứng viên thông số là **một con số kèm đơn vị**, còn ứng
    viên chân là **một quan hệ** (chân này nối vào net kia, theo hướng nọ). Ép chân vào khuôn
    của số thì mất đúng phần mang thông tin.
    """

    so_chan: str                   # "D4" — tên người dùng gọi trên bo
    cong: str = ""                 # "PD4" — tên cổng của vi điều khiển
    huong: str = ""                # vào | ra | hai_chieu | ""
    net: str = ""                  # "DIR1"
    khoi: str = ""                 # "A4988 #1"
    chuc_nang: str = ""
    don_vi_trich_dan: int = 0      # số thứ tự `Trang` để tra lại trích dẫn

    def to_dict(self) -> dict[str, Any]:
        return {"so_chan": self.so_chan, "cong": self.cong, "huong": self.huong,
                "net": self.net, "khoi": self.khoi, "chuc_nang": self.chuc_nang}


_HUONG_VI = {
    "vào": "vao", "vao": "vao", "in": "vao", "input": "vao", "đầu vào": "vao",
    "ra": "ra", "out": "ra", "output": "ra", "đầu ra": "ra",
    "hai chiều": "hai_chieu", "hai chieu": "hai_chieu", "bidir": "hai_chieu",
    "i/o": "hai_chieu", "io": "hai_chieu", "inout": "hai_chieu",
}

_COT_CHAN = ("chân", "chan", "pin", "chân số", "số chân", "pin number")
_COT_HUONG = ("hướng", "huong", "direction", "i/o", "io", "dir")
_COT_NET = ("net", "tín hiệu", "tin hieu", "signal", "kết nối", "net · khối", "net/khối")
_COT_CHUC_NANG = ("chức năng", "chuc nang", "function", "mô tả", "ghi chú")


def _chon_cot(cot: list[str], ten: tuple[str, ...]) -> int:
    """Tìm cột theo tên, khớp cả khi tiêu đề dài hơn.

    Tiêu đề thật trong tài liệu là *"Chức năng và ghi chú"*, không phải *"Chức năng"*. So
    bằng dấu bằng thì cột đó không bao giờ khớp và phần ghi chú của từng chân — chỗ chứa
    "Mức THẤP = tiến", "chuỗi 4 đèn", "kéo lên ngoài 10 kΩ" — bị bỏ lại trong tài liệu.
    """
    thap = [str(c).strip().lower() for c in cot]
    for i, t in enumerate(thap):                      # khớp đúng trước
        if t in ten or t.split("·")[0].strip() in ten:
            return i
    for i, t in enumerate(thap):                      # rồi mới khớp phần đầu
        if any(t.startswith(x) for x in ten):
            return i
    return -1


def _tach_chan_cong(o: str) -> tuple[str, str]:
    """`"D4 · PD4"` → `("D4", "PD4")`; `"PB2"` → `("PB2", "PB2")`.

    Tài liệu viết cả hai tên vì người dùng gọi chân theo nhãn trên bo (`D4`) còn thanh ghi
    thì theo cổng (`PD4`). Giữ cả hai: mất tên cổng thì mã cấu hình DDR không viết được, mất
    tên bo thì người cầm bo không tìm ra chân.
    """
    phan = [x.strip() for x in re.split(r"[·|,/]| - ", str(o)) if x.strip()]
    if not phan:
        return "", ""
    if len(phan) == 1:
        return phan[0], (phan[0] if re.fullmatch(r"P[A-F]\d", phan[0]) else "")
    cong = next((x for x in phan if re.fullmatch(r"P[A-F]\d", x)), "")
    ten = next((x for x in phan if x != cong), phan[0])
    return ten, cong


def trich_chan_ung_vien(tl: TaiLieu, *, gioi_han: int = 200) -> list[ChanUngVien]:
    """Đọc BẢNG BẢN ĐỒ CHÂN bằng mã. Mô hình không tham gia — cùng kỷ luật với §C3 bước 4.

    Chỉ đọc những hàng mà bộ đọc tài liệu đã nhận là bảng chân (`loai_bang == "chan"`), tức
    quyết định "đây có phải bản đồ chân không" nằm ở tiêu đề cột, không nằm ở phỏng đoán.
    """
    ra: list[ChanUngVien] = []
    for t in tl.trang:
        if getattr(t, "loai_bang", "") != "chan" or not t.o or not t.cot:
            continue
        i_chan = _chon_cot(t.cot, _COT_CHAN)
        if i_chan < 0 or i_chan >= len(t.o):
            continue
        ten, cong = _tach_chan_cong(t.o[i_chan])
        if not ten or ten.strip().lower() in _COT_CHAN:
            continue

        def lay(cot_ten: tuple[str, ...]) -> str:
            i = _chon_cot(t.cot, cot_ten)
            return str(t.o[i]).strip() if 0 <= i < len(t.o) else ""

        net_o = lay(_COT_NET)
        net, khoi = "", ""
        if net_o and net_o not in ("—", "-", ""):
            phan = [x.strip() for x in net_o.split("·")]
            net = phan[0]
            khoi = phan[1] if len(phan) > 1 else ""
        h = lay(_COT_HUONG).lower()
        ra.append(ChanUngVien(
            so_chan=ten, cong=cong, huong=_HUONG_VI.get(h, ""), net=net, khoi=khoi,
            chuc_nang=lay(_COT_CHUC_NANG)[:300], don_vi_trich_dan=t.so))
        if len(ra) >= gioi_han:
            break
    return ra


def fact_tu_chan(uv: ChanUngVien, *, doc: TaiLieu, chip: str,
                 tier: str = "BAC") -> list[dict[str, Any]]:
    """Một hàng bảng chân → các Fact `pin:<chip>.<số>`.

    Khoá theo đúng quy ước mà `knowledge/ckm.chan_tu_fact` đọc (`ten`, `af`), cộng hai khoá
    riêng của bo: `net` và `huong`. Nhờ vậy bản đồ chân trích ra **đi thẳng** vào cây khối và
    sơ đồ, không cần ai chép tay lần nữa — chép tay là chỗ sai không ai kiểm được.
    """
    cite = doc.trich_dan(uv.don_vi_trich_dan)
    goc = {"doc_id": doc.doc_id, "version": doc.phien_ban,
           "page": uv.don_vi_trich_dan, "cite": cite,
           "quote": f"{uv.so_chan} | {uv.huong} | {uv.net} | {uv.chuc_nang}"[:200]}
    ra: list[dict[str, Any]] = []
    # `khoi` đi cùng `net` vì bảng bàn giao viết chúng trong MỘT ô ("DIR1 · A4988 #1"): net
    # nối đi đâu, và đầu kia thuộc khối nào. Giữ lại thì bản đồ mạch dựng được BẰNG MÃ; bỏ đi
    # thì phải có người chép tay 14 net từ bảng sang bản đồ, và chép tay là chỗ sai không ai
    # kiểm được.
    for khoa, gt in (("ten", uv.cong or uv.so_chan), ("net", uv.net), ("khoi", uv.khoi),
                     ("huong", uv.huong), ("af", uv.chuc_nang if uv.chuc_nang else "")):
        if not gt:
            continue
        fid = "f-" + hashlib.sha1(
            f"pin:{chip}.{uv.so_chan}|{khoa}|{gt}|{doc.hash[:8]}".encode()).hexdigest()[:10]
        ra.append({
            "fact_id": fid, "subject": f"pin:{chip}.{uv.so_chan}", "key": khoa,
            "value": gt, "unit": "", "condition": "", "tier": tier, "origin": "extract",
            "source": goc,
            "explain": {
                "summary": f"chân {uv.so_chan} · {khoa} = {gt}",
                "why": f"Đọc bằng mã từ bảng bản đồ chân trong {doc.ten}, {cite}.",
                "sources": [{"kind": "doc", "ref": f"{doc.doc_id} · {cite}", "tier": tier}],
                "diff_prev": "bản đầu tiên",
                "next": ("Người xác nhận đúng hàng này để lên tầng VÀNG."
                         if tier == "BAC" else "Đối chiếu với bo thật."),
                "confidence": tier}})
    return ra
