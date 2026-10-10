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
    # M5-04 — "max tuyệt đối" và "max khi chạy" là HAI thông số, không phải một cách gọi khác
    # của cùng một thông số. `Absolute maximum ratings` là ngưỡng **phá hỏng chip**;
    # `Recommended operating conditions` là ngưỡng **chạy đúng**. Gộp vào cùng khoá thì hoặc
    # hệ thống báo hai tài liệu mâu thuẫn trong khi cả hai đều đúng, hoặc 4,0 V ghi đè 3,6 V
    # và mọi phép kiểm sau đó cho chip chạy ngoài vùng nhà sản xuất bảo đảm.
    "vdd.abs_max": "Điện áp cấp tối đa TUYỆT ĐỐI (ngưỡng phá hỏng, không phải ngưỡng chạy)",
    "vdd.abs_min": "Điện áp cấp tối thiểu TUYỆT ĐỐI (ngưỡng phá hỏng phía dưới, "
                   "thường là một điện áp ÂM)",
    "vih.min": "Mức logic cao tối thiểu ở đầu vào",
    "vil.max": "Mức logic thấp tối đa ở đầu vào",
    "voh.min": "Mức logic cao tối thiểu ở đầu ra",
    "vol.max": "Mức logic thấp tối đa ở đầu ra",
    "vddio.max": "Điện áp tối đa của chân I/O",
    # M5-04 — các khoá mà đường BẢNG mới với tới được: một hàng `VIH | 2.0 | 5.5 | V`
    # cho cả hai cột, và trước đây không cột nào tới được vì tên trần không khớp mẫu.
    "vih.max": "Mức logic cao tối đa ở đầu vào",
    "vil.min": "Mức logic thấp tối thiểu ở đầu vào",
    "voh.max": "Mức logic cao tối đa ở đầu ra",
    "vol.min": "Mức logic thấp tối thiểu ở đầu ra",
    "vddio.min": "Điện áp tối thiểu của chân I/O",
    "iout.max": "Dòng ra tối đa", "icc.min": "Dòng tiêu thụ tối thiểu",
    "i2c.pullup.min": "Điện trở kéo lên I2C tối thiểu",
    "i2c.pullup.max": "Điện trở kéo lên I2C tối đa",
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


def ve_si(gia_tri: float | str, don_vi: str) -> tuple[float | str, str]:
    """Đưa về đơn vị cơ bản. `4,7 kΩ` → `(4700.0, "Ω")`.

    Không có bước này thì `fact.compare` phải so `5000 mV` với `5 V` bằng chuỗi và sẽ
    kết luận sai — đúng loại lỗi mà một hệ thống "so sánh có bằng chứng" không được có.

    Giá trị KHÔNG phải số (M3-07: `i2c.addr` = `"0x48"`) thì trả nguyên — một địa chỉ không
    có đơn vị để quy đổi, và nhân nó với một hệ số là làm ra một con số vô nghĩa.
    """
    if not isinstance(gia_tri, (int, float)) or isinstance(gia_tri, bool):
        return gia_tri, don_vi
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
    # Những chuyện người nạp tài liệu CẦN BIẾT mà không phải lỗi: đường dự phòng đã
    # dùng, trần đã chạm. Một cờ bật mà đường của nó không chạy thì phải nói ra —
    # không thì cả người bật cờ lẫn hệ thống đều báo `ok` về hai chuyện khác nhau (N6).
    ghi_chu: list[str] = field(default_factory=list)

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

    # M5-04 — hàng bảng NỐI THÊM, không thay trang chữ. Đường theo dòng là đường dự phòng
    # thật: `find_tables()` dò theo nét vẽ, nên một datasheet xuất từ Word (bảng không viền)
    # cho 0 bảng, và lúc ấy đường cũ là đường duy nhất còn đọc được.
    ghi_chu: list[str] = []
    so_trang_chu = len(trang)
    if _bat_pdf_bang():
        from . import bang_pdf

        try:
            hang = bang_pdf.bang_tu_tai_lieu(path)
        except ImportError:
            # Phụ thuộc TUỲ CHỌN (N-10) thiếu thì xuống đường cũ — và NÓI RA. Im lặng ở đây
            # là ca N6: người bật cờ nghĩ đang đọc bảng, hệ thống đang đọc dòng chữ.
            hang = []
            ghi_chu.append("cờ `pdf_bang` đang BẬT nhưng máy này không có `pdfplumber` — "
                           "đã đọc theo DÒNG CHỮ, không đọc theo bảng. Cài: "
                           "`pip install 'eide[pdf]'`.")
        except Exception as e:                               # noqa: BLE001
            hang = []
            ghi_chu.append(f"đọc bảng PDF không chạy được ({type(e).__name__}) — đã đọc theo "
                           "DÒNG CHỮ. Đây KHÔNG phải “tệp không có bảng”.")
        if len(hang) >= bang_pdf.TRAN_HANG:
            ghi_chu.append(f"chạm trần {bang_pdf.TRAN_HANG} hàng bảng — phần sau của tài liệu "
                           "CHƯA đọc theo bảng.")
        trang = trang + hang

    meta = r.metadata or {}
    return TaiLieu(
        doc_id=doc_id, ten=path.name, duong_dan=str(path), hash=h,
        so_trang=so_trang_chu, trang=trang,
        phien_ban=phien_ban or str(meta.get("/Title", "") or "")[:60],
        nha_phat_hanh=nha_phat_hanh or str(meta.get("/Author", "") or "")[:60],
        canh_bao_tiem_lenh=canh, ghi_chu=ghi_chu)


def _bat_pdf_bang() -> bool:
    """Cờ `pdf_bang`. Đọc qua `Features.load()` để biến môi trường có hiệu lực ngay.

    `docs.py` là lớp tri thức, không giữ `config` — nên nó hỏi cờ chứ không nhận cờ. Lỗi ở
    đây thì coi như TẮT: một tệp cấu hình hỏng không được làm `doc.load` mất cả tài liệu.
    """
    try:
        from ..config import Features

        return bool(Features.load().bat("pdf_bang"))
    except Exception:                                        # noqa: BLE001
        return False


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
    # `float` cho mọi thông số đo được; `str` cho `i2c.addr` ("0x48") — một địa chỉ không
    # phải một đại lượng, và ép nó thành số thì mất dạng hex mà phép so trùng cần.
    gia_tri: float | str
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
    # M3-07 — hai thông số mà ERC CẦN mà trước đây không có mẫu nào: `iout.max` là vế CẤP
    # của luật ngân sách dòng, `i2c.addr` là vế duy nhất của luật trùng địa chỉ bus. Thiếu
    # chúng thì hai luật ấy chỉ chạy được khi người dùng tự gõ Fact bằng tay — mà ERC vẫn
    # in ra "0 lỗi chặn".
    (re.compile(r"\bI\s*OUT\b|\boutput\s+current\b", re.I), "iout.max"),
    (re.compile(r"\b(?:I2C|slave)\s+address\b", re.I), "i2c.addr"),
    (re.compile(r"\bI\s*OL\b", re.I), "iol.max"),
    (re.compile(r"\bI\s*OH\b", re.I), "ioh.max"),
    (re.compile(r"\bpull-?up\b", re.I), "i2c.pullup.typ"),
    (re.compile(r"\bthroughput\b", re.I), "throughput.max"),
    (re.compile(r"\boperating\s+temperature\b", re.I), "ta.max"),
]

# M5-04 — mẫu tên thông số cho ĐƯỜNG BẢNG. Đây là một chỗ nữa mà kế hoạch nói sai, và chỉ
# phép đo chỉ ra: `_MAU_THONG_SO` ở trên đòi tên **đã kèm** hậu tố (`V DD (max)`), vì nó sinh
# ra cho đường theo DÒNG CHỮ, nơi `VDD (max)   5.5 V` nằm trọn trên một dòng.
#
# Trong một BẢNG thì hậu tố nằm ở **tiêu đề cột**, và ô `Parameter` ghi `VDD` trần — đúng dạng
# mọi datasheet thật dùng. Nên trước việc này `_tu_hang_bang` **không khớp nổi một hàng
# datasheet nào**: nó chỉ chạy trên bảng mà ô tên tự ghi `VDD max`, một dạng do chính bản mẫu
# của bộ kiểm dựng ra. Cơ chế có sẵn, đường dẫn tới nó đứt — lần thứ mười trong dự án này.
#
# Neo `^` là cố ý: ô tên của một hàng bảng là một ô riêng, nên khớp từ đầu ô tránh được chuyện
# một chữ `VDD` trong câu `Conditions` biến cả hàng thành một hàng điện áp.
_MAU_THONG_SO_BANG: list[tuple[re.Pattern[str], str, bool]] = [
    (re.compile(r"^\s*V\s*DDIO\b", re.I), "vddio", False),
    (re.compile(r"^\s*V\s*DD\b|^\s*supply\s+voltage\b", re.I), "vdd", False),
    (re.compile(r"^\s*V\s*IH\b", re.I), "vih", False),
    (re.compile(r"^\s*V\s*IL\b", re.I), "vil", False),
    (re.compile(r"^\s*V\s*OH\b", re.I), "voh", False),
    (re.compile(r"^\s*V\s*OL\b", re.I), "vol", False),
    (re.compile(r"^\s*I\s*CC\b|^\s*supply\s+current\b", re.I), "icc", False),
    (re.compile(r"^\s*I\s*OL\b", re.I), "iol", False),
    (re.compile(r"^\s*I\s*OH\b", re.I), "ioh", False),
    (re.compile(r"^\s*I\s*OUT\b|^\s*output\s+current\b", re.I), "iout", False),
    (re.compile(r"^\s*T\s*A\b|^\s*(?:ambient\s+|operating\s+)?temperature\b", re.I),
     "ta", False),
    (re.compile(r"^\s*pull-?up\b", re.I), "i2c.pullup", False),
    # Bốn khoá CỐ ĐỊNH: cột Min/Typ/Max của chúng không đổi nghĩa khoá. "Flash 32 KB" ở cột
    # Max vẫn là `flash.size` — đây là bài học M5-05, nơi đường bảng từng sinh `flash.max`,
    # một khoá không chỗ nào đọc.
    (re.compile(r"^\s*flash\b", re.I), "flash.size", True),
    (re.compile(r"^\s*(?:S?RAM)\b", re.I), "ram.size", True),
    (re.compile(r"^\s*EEPROM\b", re.I), "eeprom.size", True),
    (re.compile(r"^\s*(?:f\s*max|max(?:imum)?\s+(?:operating\s+)?frequency"
                r"|(?:operating\s+)?frequency)\b", re.I), "fmax", True),
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
            if khoa == "i2c.addr":
                dc = doc_dia_chi_i2c(chu)
                if dc:
                    ra.append(FactUngVien(
                        khoa=khoa, gia_tri=dc, don_vi="", trang=t.so,
                        trich_doan=chu[:200], thuc_the=thuc_the, nguyen_van=dc))
                    if len(ra) >= gioi_han:
                        return _gom(ra)
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


# M3-07 — địa chỉ I2C không phải "số kèm đơn vị", nên `_SO_DON_VI` không bắt được. Hai cách
# datasheet hay ghi, và cả hai phải ra cùng một dạng để `erc.trung_dia_chi_bus` so được:
# `0x48` và `1001000` (nhị phân 7 bit) là **cùng một địa chỉ**.
_DIA_CHI_HEX = re.compile(r"\b0x([0-9a-f]{1,2})\b", re.I)
_DIA_CHI_NHI_PHAN = re.compile(r"\b([01]{7})b?\b")


def doc_dia_chi_i2c(chu: str) -> str:
    """`"0x48"` từ một dòng chữ. Rỗng nếu không thấy địa chỉ nào đọc được.

    Trả dạng hex hai chữ số vì đó là dạng `erc.trung_dia_chi_bus` chuẩn hoá về — hai Fact
    cùng một địa chỉ mà ghi khác dạng thì phép so trùng không bắt được, và đó đúng là lỗi
    nó sinh ra để bắt.
    """
    m = _DIA_CHI_HEX.search(chu)
    if m:
        return f"0x{int(m.group(1), 16):02x}"
    m = _DIA_CHI_NHI_PHAN.search(chu)
    if m:
        return f"0x{int(m.group(1), 2):02x}"
    return ""


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
    "vdd.abs_max": (0.5, 60),
    "vih.min": (0.3, 60), "vil.max": (0.0, 60),
    # Dòng ra của một bộ cấp: từ 1 mA (tham chiếu điện áp) tới 50 A (module nguồn lớn).
    # Có khoảng này là cái phanh cuối cho vế CẤP — một Fact sai ở vế ấy làm ngân sách dòng
    # kết luận "đạt" cho một mạch thiếu nguồn, tức một ô xanh giả đúng chỗ đắt nhất.
    "iout.max": (1e-3, 50),
    "f.max": (1_000, 2_000_000_000),
    "temp.min": (-100, 200), "temp.max": (-100, 200),
    # M5-05 — hai khoá mà bộ trích THẬT SỰ sinh ra. `_MAU_THONG_SO` cho `"fmax"` và `"ta.*"`,
    # còn bảng này khai `"f.max"`/`"temp.*"` — hai bên không gặp nhau, nên phép kiểm khoảng
    # của tần số và nhiệt độ **chưa nổ lần nào**. Thêm, không đổi tên: `tools/xay_dung.py`
    # đọc bảng này theo khoá, và Fact cũ trong kho người dùng vẫn mang khoá cũ.
    "fmax": (1_000, 2_000_000_000),
    "i2c.fmax": (1_000, 1e8), "spi.fmax": (1_000, 1e9),
    "ta.min": (-100, 200), "ta.max": (-100, 200),
}

# M5-04 — khoảng hợp lý theo GỐC khoá, tra theo tiền tố DÀI NHẤT. Chỉ dùng khi `PHAM_VI_HOP_LY`
# không có khoá CHÍNH XÁC, nên mọi dòng đã khai ở trên vẫn thắng.
#
# Vì sao cần: bảng trên khai theo khoá đầy đủ (`vdd.max`), và đường BẢNG sinh ra hậu tố theo
# **tiêu đề cột** — nên nó cho ra `vddio.max`, `vol.min`, `icc.max`, `iol.max`… những khoá mà
# bảng trên không có dòng nào. Đo ngày 10/10/2026: **tám gốc khoá có thứ nguyên mà không có
# khoảng nào** — `vddio` · `voh` · `vol` · `icc` · `iol` · `ioh` · `vref` · `i2c.pullup`. Với
# chúng, `hop_ly` chỉ còn kiểm thứ nguyên, nên `vddio = 6 000 V` đi qua: đúng volt, sai chip.
#
# Đây là chỗ RỘNG HƠN phạm vi kế hoạch nêu cho M5-04, và nó là hệ quả trực tiếp: đường bảng
# làm những khoá ấy với tới được lần đầu. Ghi ra để không ai đọc thành "kế hoạch có nói".
#
# Mỗi khoảng là một phanh "có thể là thứ ấy không", không phải thông số của một chip cụ thể —
# cùng loại với các dòng đã có. Nguồn của từng con số:
#   · điện áp (vdd/vddio/vref/vih/vil/voh/vol): 0–60 V — trên 60 V là mạch công suất, không
#     phải chân logic; và `hop_ly` chỉ cần chặn thứ **không thể**, không cần chặn thứ hiếm.
#   · dòng (icc/iol/ioh): biên trên lấy đúng của `iout.max` đã có; biên dưới để ở mức dòng
#     RỈ (pA) chứ không ở mức dòng lái (mA) — xem ghi chú dưới.
#   · điện trở: 0,1 Ω tới 10 MΩ.
#
# Biên DƯỚI của ba dòng và của điện trở từng bị tôi đặt theo **thói quen** — "pull-up I2C
# thường 1–10 kΩ" nên biên dưới 10 Ω, "dòng lái tính bằng mA" nên biên dưới 1 µA. Ca kiểm
# `test_ING09_ky_hieu_ky_thuat_trong_o_bang` (có từ trước) bác ngay: ô bảng ghi `4R7`, tức
# **4,7 Ω**, và 4,7 Ω là một giá trị điện trở có thật. Phanh này chỉ được chặn thứ KHÔNG THỂ;
# chặn thứ hiếm là bỏ mất Fact thật, và lúc ấy tác tử phải hỏi người dùng một con số đang nằm
# sẵn trong datasheet. Ghi lại vì đây đúng là lỗi mà N1 nói tới: con số tự nhớ, không tra.
PHAM_VI_GOC: dict[str, tuple[float, float]] = {
    "vdd": (0.0, 60), "vddio": (0.0, 60), "vref": (0.0, 60),
    "vih": (0.0, 60), "vil": (0.0, 60), "voh": (0.0, 60), "vol": (0.0, 60),
    "icc": (1e-12, 50), "iol": (1e-12, 10), "ioh": (1e-12, 10), "iout": (1e-3, 50),
    "i2c.pullup": (0.1, 1e7),
    "flash": (1024, 64 * 1024 * 1024), "ram": (64, 64 * 1024 * 1024),
    "sram": (64, 64 * 1024 * 1024), "eeprom": (16, 1024 * 1024),
    "fmax": (1_000, 2_000_000_000), "f": (1_000, 2_000_000_000),
    "ta": (-100, 200), "temp": (-100, 200),
}


def pham_vi_cua(khoa: str) -> tuple[float, float] | None:
    """Khoảng hợp lý của một khoá: khoá chính xác trước, rồi gốc khoá theo tiền tố dài nhất.

    Hậu tố `abs_` (ngưỡng PHÁ HỎNG, M5-04) tra theo khoá không có nó — `vdd.abs_max` dùng
    khoảng của `vdd`. Và `abs_min` được mở xuống phía âm: ngưỡng phá hỏng phía dưới của một
    chân **là** một điện áp âm (`VDD min = −0,5 V` trong bảng Absolute maximum của gần như mọi
    datasheet). Biên âm lấy ĐỐI của biên trên, không phải một con số mới: nó nói *"độ lớn của
    một ngưỡng phá hỏng không vượt quá độ lớn hợp lý của thứ nguyên ấy"* — không nói chip này
    chịu được bao nhiêu.
    """
    pv = PHAM_VI_HOP_LY.get(khoa)
    if pv is not None:
        return pv
    am = ".abs_min" in khoa
    sach = khoa.replace(".abs_max", ".max").replace(".abs_min", ".min")
    pv = PHAM_VI_HOP_LY.get(sach)
    if pv is None:
        phan = sach.split(".")
        for i in range(len(phan) - 1, 0, -1):
            pv = PHAM_VI_GOC.get(".".join(phan[:i]))
            if pv:
                break
    if pv is None:
        return None
    return (-abs(pv[1]), pv[1]) if am else pv


# M5-05 — THỨ NGUYÊN của một khoá, tra theo tiền tố DÀI NHẤT khớp trước.
#
# Vì sao cần: `hop_ly` quy về đơn vị cơ bản rồi chỉ so ĐỘ LỚN, nên `hop_ly("vdd.max", 25, "°C")`
# trả `True` — 25 nằm trong khoảng điện áp hợp lý, và chẳng ai hỏi *"25 cái gì"*. Một Fact
# `vdd.max = 25 °C` ở tầng BẠC là vế giới hạn của luật ERC quá áp, tức một ô xanh giả đúng chỗ
# đắt nhất.
#
# Tra theo tiền tố dài nhất, không theo "phần trước dấu chấm cuối": ba khoá `i2c.pullup.typ`
# (ohm), `i2c.fmax` (hertz) và `i2c.addr` (không có thứ nguyên) cùng bắt đầu bằng `i2c`, nên
# một phép tra theo tiền tố ngắn sẽ gán sai thứ nguyên cho hai trong ba.
THU_NGUYEN_KHOA: dict[str, str] = {
    "vdd": "V", "vih": "V", "vil": "V", "voh": "V", "vol": "V", "vddio": "V", "vref": "V",
    "icc": "A", "iol": "A", "ioh": "A", "iout": "A",
    "fmax": "Hz", "i2c.fmax": "Hz", "spi.fmax": "Hz", "f": "Hz",
    "ta": "°C", "temp": "°C",
    "flash": "B", "ram": "B", "sram": "B", "eeprom": "B",
    "i2c.pullup": "Ω",
}

# Nhóm thứ nguyên cho phép ĐƠN VỊ RỖNG. Datasheet ghi `Flash: 32768` không kèm đơn vị thật, và
# `ve_don_vi_co_ban` đã có ngữ nghĩa KB=1024 cho nhóm ấy. Với volt/ampe/hertz thì một con số
# không đơn vị là một con số không ai kiểm lại được — và `_SO_DON_VI` vốn luôn bắt kèm đơn vị,
# nên không mất gì.
_CHO_PHEP_RONG = frozenset({"B"})


def thu_nguyen_cua(khoa: str) -> str:
    """Thứ nguyên khai báo của khoá, hoặc `""` nếu chưa khai.

    Tra `khoa` nguyên vẹn trước, rồi bỏ dần đoạn cuối: `i2c.pullup.typ` → `i2c.pullup` (Ω),
    `i2c.addr` → `i2c` (chưa khai) → `""`.
    """
    phan = (khoa or "").split(".")
    for i in range(len(phan), 0, -1):
        tn = THU_NGUYEN_KHOA.get(".".join(phan[:i]))
        if tn:
            return tn
    return ""

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
    """Giá trị này có thể là thứ mà khoá đó nói tới không.

    Hai phép kiểm, và chúng trả lời hai câu khác nhau:

    * **thứ nguyên** — `vdd` đo volt, nên `25 °C` không phải điện áp. Đây là phép kiểm M5-05
      thêm vào, và nó bắt được đúng cái mà phép so độ lớn bỏ qua: một con số **đúng độ lớn mà
      sai loại**. `hop_ly("vdd.max", 25, "°C")` trước đây trả `True`.
    * **độ lớn** — `vdd.max = 600 V` thì đúng thứ nguyên mà không phải chip này.

    Khoá chưa khai gì (cả thứ nguyên lẫn khoảng) thì **không chặn**: một phép kiểm chặn cả thứ
    nó không biết sẽ bỏ mất Fact thật, và lúc ấy tác tử phải hỏi người dùng những con số đang
    nằm sẵn trong datasheet.
    """
    tn = thu_nguyen_cua(khoa)
    if tn and isinstance(gia_tri, (int, float)) and not isinstance(gia_tri, bool):
        _, co_ban_dv = ve_si(gia_tri, don_vi)
        dv = (don_vi or "").strip()
        if not dv:
            if tn not in _CHO_PHEP_RONG:
                return False
        elif co_ban_dv != tn:
            return False
    pv = pham_vi_cua(khoa)
    if pv is None:
        return True                       # chưa có khoảng cho khoá này thì không chặn
    if not isinstance(gia_tri, (int, float)) or isinstance(gia_tri, bool):
        # Giá trị KHÔNG phải số (M3-07: `i2c.addr` = `"0x48"`) thì không có khoảng nào áp
        # được. Thiếu cửa này thì `pv[0] <= "0x48"` ném `TypeError` — tìm ra bằng tập phá
        # của M5-05: `i2c.addr` chỉ sống sót vì nó KHÔNG có khoảng trong bảng, nên cái lỗi
        # nằm đó im lặng chờ người đầu tiên thêm một khoảng cho một khoá giá trị-chuỗi.
        return True
    co_ban = ve_don_vi_co_ban(gia_tri, don_vi)
    return pv[0] <= co_ban <= pv[1]


# Tên cột → hậu tố khoá. "VDD" ở cột Max thành `vdd.max`, ở cột Min thành `vdd.min`.
_HAU_TO_COT = {
    "min": "min", "minimum": "min", "nhỏ nhất": "min",
    "typ": "typ", "typical": "typ", "nom": "typ", "value": "typ", "giá trị": "typ",
    "max": "max", "maximum": "max", "lớn nhất": "max", "rating": "max",
}
_COT_DON_VI = {"unit", "units", "đơn vị"}
# Chỉ nhãn mục mới nói được một hàng thuộc bảng "max tuyệt đối" hay bảng "max khi chạy".
_LA_ABS_MAX = re.compile(r"absolute\s+maximum", re.I)
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

    # M5-05 — chỉ CẮT hậu tố khi nó đúng là một hậu tố mà CỘT BẢNG cấp được.
    #
    # Bản trước cắt mù `k.rsplit(".", 1)[0]`, nên đường bảng và đường dòng chữ sinh ra **hai
    # khoá khác nhau cho cùng một thông số**: `flash.size` thành `flash` + hậu tố cột →
    # `flash.max`, và `fmax` (một đoạn, không có hậu tố nào để cắt) thành `fmax.max`. Cả hai
    # khoá ấy không có trong `KHOA_CHUAN`, không có trong `PHAM_VI_HOP_LY`, và
    # `tools/xay_dung._han_muc` không đọc `flash.max` — nên một dung lượng Flash đọc từ BẢNG
    # chưa bao giờ thành hạn mức, và không ai thấy vì nó vẫn là một Fact trông hợp lệ.
    #
    # Tìm ra bằng tập phá của chính nhiệm vụ này, ngoài phạm vi kế hoạch nêu. Sửa được vì hai
    # khoá bị đổi (`flash.max`, `fmax.max`) là hai khoá **không chỗ nào đọc** — đổi chúng
    # không làm lệch Fact cũ nào đang khớp với ai.
    khoa_goc = None
    khoa_co_dinh = False
    # M5-04 — mẫu dành riêng cho BẢNG đi TRƯỚC: ô tên của bảng ghi tên trần, và hậu tố do
    # cột cấp. Mẫu của đường dòng chữ giữ làm vế dự phòng, cho những bảng mà ô tên tự ghi
    # luôn hậu tố (`VDD max`) — dạng ấy có thật trong tài liệu nội bộ.
    for mau, k, co_dinh in _MAU_THONG_SO_BANG:
        if mau.search(ten):
            khoa_goc, khoa_co_dinh = k, co_dinh
            break
    if khoa_goc is None:
        for mau, k in _MAU_THONG_SO:
            if mau.search(ten):
                dau, _, cuoi = k.rpartition(".")
                if dau and cuoi in ("min", "typ", "max"):
                    khoa_goc = dau
                else:
                    khoa_goc, khoa_co_dinh = k, True
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
            # M5-04 — bảng `Absolute maximum ratings` cho một khoá KHÁC. Nhãn của hàng là
            # thứ duy nhất phân biệt được hai bảng ấy: nội dung hàng của chúng giống nhau
            # tới từng ô (`VDD | 4.0 | V` so với `VDD | 3.6 | V`).
            # Cả HAI biên của bảng "max tuyệt đối" đều là ngưỡng phá hỏng, không chỉ biên
            # trên. Cột Min của bảng ấy ghi thứ như `VDD = −0,5 V` — một điện áp ÂM, và đọc
            # nó thành `vdd.min` (điện áp cấp tối thiểu khi chạy) là sai nghĩa hoàn toàn:
            # nó sẽ nói chip chạy được từ −0,5 V.
            if ht in ("min", "max") and _LA_ABS_MAX.search(t.nhan or ""):
                ht = "abs_" + ht
            khoa = khoa_goc if khoa_co_dinh else f"{khoa_goc}.{ht}"
            # M5-05 — đường HÀNG BẢNG cũng phải qua `hop_ly`, và nó là đường duy nhất trước
            # đây không qua. Mà bảng là đường CHÍNH của datasheet: `_tu_hang_bang` tồn tại
            # chính vì đơn vị nằm ở cột riêng, nên nó có đủ dữ kiện để kiểm thứ nguyên.
            #
            # Tra bằng khoá ĐẦY ĐỦ, không bằng `khoa_goc`: thứ nguyên tra theo tiền tố nên
            # `"vdd"` cũng ra `"V"`, nhưng `PHAM_VI_HOP_LY` không có khoá `"vdd"` — dùng khoá
            # gốc thì phép kiểm **khoảng** im lặng mất, và một `600 V` đúng thứ nguyên mà
            # không phải chip này sẽ đi qua.
            #
            # Bỏ TỪNG Ô, không bỏ cả hàng: một hàng có ô đúng và ô sai là hình dạng có thật —
            # bộ đọc bảng cắt lệch một cột thì giá trị `Conditions` rơi vào một cột giá trị.
            if not hop_ly(khoa, v, g.don_vi):
                continue
            ra.append(FactUngVien(
                khoa=khoa, gia_tri=v, don_vi=g.don_vi, trang=t.so,
                trich_doan=t.chu[:200], thuc_the=thuc_the,
                nguyen_van=g.raw.strip(),
                dieu_kien={**dieu_kien_hang, **g.dieu_kien}))
    return ra


def _gom(ds: list[FactUngVien]) -> list[FactUngVien]:
    """Cùng khoá + cùng giá trị SI thì giữ một, ưu tiên trang sớm nhất."""
    thay: dict[tuple[str, Any, str], FactUngVien] = {}
    for f in ds:
        si, dv = ve_si(f.gia_tri, f.don_vi)
        # Giá trị không phải số (`i2c.addr`) thì gom theo chính chuỗi ấy — `round` trên một
        # chuỗi là một `TypeError`, và nó sẽ nổ ở đúng chỗ khó đoán nhất: lúc gom kết quả.
        k = (f.khoa, round(si, 9) if isinstance(si, (int, float)) else str(si), dv)
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
