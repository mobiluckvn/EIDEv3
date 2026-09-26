# -*- coding: utf-8 -*-
"""Hình trong tài liệu, OCR và đa ngôn ngữ — EIDE-ING-43 §4.6, §4.7. Bước ING-E.

## Điều quan trọng nhất của cả tệp này: OCR sai KHÔNG trông như sai

Một PDF hỏng thì báo lỗi. Một OCR sai thì trả về **chữ** — chữ đọc được, có vẻ hợp lý,
và một con số trong đó có thể là `5.5` đọc từ `8.8`. Nên mọi thứ ở đây đi kèm ba thứ:

1. **Điểm tin cậy** từ chính tesseract, theo từng khối chữ.
2. **Trần tầng BẠC** — không bao giờ VÀNG, dù điểm có cao (§6, TC044).
3. **Gói ngôn ngữ phải đúng.** Đọc tiếng Việt bằng mô hình tiếng Anh cho ra chữ nhìn
   như chữ mà sai. Máy này hiện chỉ có `eng`; gặp tài liệu tiếng Việt thì phải **nói
   thiếu gói**, không phải đọc bừa rồi đưa số cho người dùng tin.

## Nhận diện ngôn ngữ viết tay, không thêm phụ thuộc

Việc cần làm chỉ là **chọn gói OCR**, không phải phân loại 55 thứ tiếng. Đếm ký tự theo
dải Unicode trả lời đúng câu đó, và nó giải trình được: ai đọc mã cũng thấy vì sao nó
kết luận "tiếng Việt". Một thư viện thống kê n-gram trả lời chính xác hơn cho bài toán
khác, và thêm một thứ phải giải trình khi bảo vệ đề án.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ký tự chỉ có trong tiếng Việt (sau khi đã bỏ phần chung với Latin).
_VIET = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệ"
                   r"ìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]")
_HAN = re.compile(r"[一-鿿]")
_HIRA_KATA = re.compile(r"[぀-ヿ]")
_HANGUL = re.compile(r"[가-힯]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN = re.compile(r"[A-Za-z]")

# Ngôn ngữ → gói tesseract.
GOI_OCR = {"vie": "vie", "eng": "eng", "chi_sim": "chi_sim", "jpn": "jpn",
           "kor": "kor", "rus": "rus"}

TRAN_TANG_OCR = "BAC"          # §6 — OCR không bao giờ lên VÀNG tự động
NGUONG_TIN_CAY = 0.8           # §5.1 bước 3 — dưới mức này thì BẮT BUỘC người rà
MAX_TRANG_OCR = 300            # §7 — hơn nữa thì chạy nền và báo tiến trình


@dataclass(slots=True)
class NgonNgu:
    ma: str                    # vie | eng | chi_sim | …
    ten_vi: str
    do_chac: float             # 0…1
    vi_sao: str

    def to_dict(self) -> dict[str, Any]:
        return {"ma": self.ma, "ten_vi": self.ten_vi, "do_chac": self.do_chac,
                "vi_sao": self.vi_sao}


_TEN_VI = {"vie": "tiếng Việt", "eng": "tiếng Anh", "chi_sim": "tiếng Trung giản thể",
           "jpn": "tiếng Nhật", "kor": "tiếng Hàn", "rus": "tiếng Nga",
           "": "không rõ"}


def nhan_ngon_ngu(chu: str) -> NgonNgu:
    """Đếm ký tự theo dải Unicode. Đủ để CHỌN GÓI OCR, và giải trình được."""
    s = (chu or "")[:20_000]
    if not s.strip():
        return NgonNgu("", _TEN_VI[""], 0.0, "không có chữ để đoán")

    dem = {
        "vie": len(_VIET.findall(s)),
        "chi_sim": len(_HAN.findall(s)),
        "jpn": len(_HIRA_KATA.findall(s)),
        "kor": len(_HANGUL.findall(s)),
        "rus": len(_CYRILLIC.findall(s)),
    }
    latin = len(_LATIN.findall(s))
    tong = sum(dem.values()) + latin
    if tong == 0:
        return NgonNgu("", _TEN_VI[""], 0.0, "không có ký tự chữ nào")

    # Kana thắng Hán: văn bản tiếng Nhật có cả hai, tiếng Trung chỉ có Hán.
    if dem["jpn"] > 0 and dem["jpn"] * 4 > dem["chi_sim"]:
        dem["chi_sim"] = 0

    ma, n = max(dem.items(), key=lambda kv: kv[1])
    if n == 0:
        return NgonNgu("eng", _TEN_VI["eng"], latin / tong,
                       f"chỉ có chữ Latin ({latin} ký tự), không thấy dấu tiếng Việt")
    return NgonNgu(ma, _TEN_VI[ma], min(1.0, n / max(1, tong) * 4),
                   f"{n} ký tự đặc trưng của {_TEN_VI[ma]} trên {tong} ký tự chữ")


def goi_da_cai() -> list[str]:
    """Gói ngôn ngữ tesseract đang có trên máy. Thiếu tesseract thì trả rỗng."""
    try:
        r = subprocess.run(["tesseract", "--list-langs"], capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [d.strip() for d in r.stdout.splitlines()[1:] if d.strip()]


def kiem_goi(ma_ngon_ngu: str) -> tuple[bool, str]:
    """Có gói cho ngôn ngữ này chưa? Thiếu thì trả LÝ DO đọc được."""
    ds = goi_da_cai()
    if not ds:
        return False, ("Máy chưa có tesseract. OCR cần nó; cách khác là xin bản PDF có "
                       "lớp chữ.")
    goi = GOI_OCR.get(ma_ngon_ngu, "")
    if not goi:
        return False, (f"Không biết dùng gói OCR nào cho {_TEN_VI.get(ma_ngon_ngu, ma_ngon_ngu)}.")
    if goi not in ds:
        return False, (
            f"Tài liệu là {_TEN_VI.get(ma_ngon_ngu, ma_ngon_ngu)} nhưng máy chỉ có gói "
            f"{', '.join(ds)}. Đọc bằng gói sai cho ra chữ **nhìn như chữ mà sai** — và "
            f"một con số sai trong đó không trông như lỗi. Cài gói: "
            f"`brew install tesseract-lang` (macOS) hoặc "
            f"`apt install tesseract-ocr-{goi}`.")
    return True, ""


# =========================================================================== OCR
@dataclass(slots=True)
class KetQuaOcr:
    chu: str = ""
    do_tin_cay: float = 0.0            # trung bình theo từ, 0…1
    so_tu: int = 0
    ngon_ngu: str = ""
    canh_bao: list[str] = field(default_factory=list)
    loi: str = ""

    @property
    def can_nguoi_ra(self) -> bool:
        return self.do_tin_cay < NGUONG_TIN_CAY

    def to_dict(self) -> dict[str, Any]:
        return {"chu": self.chu[:4000], "do_tin_cay": round(self.do_tin_cay, 3),
                "so_tu": self.so_tu, "ngon_ngu": self.ngon_ngu,
                "tang_toi_da": TRAN_TANG_OCR, "can_nguoi_ra": self.can_nguoi_ra,
                "canh_bao": list(self.canh_bao), "loi": self.loi}


def ocr_anh(path: Path, *, ma_ngon_ngu: str = "eng") -> KetQuaOcr:
    """OCR một ảnh, kèm điểm tin cậy THEO TỪNG TỪ.

    Điểm trung bình của cả trang che mất chỗ hỏng: một bảng thông số đọc tốt 95 % mà
    đúng cái cột số bị mờ thì trung bình vẫn cao. Nên ta giữ cả điểm thấp nhất và đếm
    số từ dưới ngưỡng.
    """
    kq = KetQuaOcr(ngon_ngu=ma_ngon_ngu)
    duoc, vi_sao = kiem_goi(ma_ngon_ngu)
    if not duoc:
        kq.loi = vi_sao
        return kq
    try:
        import pytesseract
        from PIL import Image

        anh = Image.open(str(path))
        goi = GOI_OCR.get(ma_ngon_ngu, "eng")
        du_lieu = pytesseract.image_to_data(
            anh, lang=goi, output_type=pytesseract.Output.DICT)
    except Exception as e:                                   # noqa: BLE001
        kq.loi = f"OCR không chạy được: {e}"
        return kq

    tu: list[tuple[str, float]] = []
    for chu, diem in zip(du_lieu.get("text", []), du_lieu.get("conf", [])):
        if not str(chu).strip():
            continue
        try:
            d = float(diem)
        except (TypeError, ValueError):
            continue
        if d < 0:
            continue
        tu.append((str(chu), d / 100.0))

    kq.chu = " ".join(t for t, _ in tu)
    kq.so_tu = len(tu)
    kq.do_tin_cay = (sum(d for _, d in tu) / len(tu)) if tu else 0.0
    thap = [t for t, d in tu if d < NGUONG_TIN_CAY]
    if thap:
        kq.canh_bao.append(
            f"{len(thap)}/{len(tu)} từ có điểm dưới {NGUONG_TIN_CAY:.0%}: "
            + ", ".join(thap[:6]))
    if kq.can_nguoi_ra:
        kq.canh_bao.append(
            "Điểm tin cậy dưới ngưỡng — mọi con số đọc từ đây phải được người xác nhận "
            "TỪNG DÒNG trước khi dùng.")
    return kq


# =========================================================================== hình
@dataclass(slots=True)
class Hinh:
    """Một hình trong tài liệu → một đoạn tri thức loại "figure" (§4.6)."""

    so: int
    don_vi: str                        # "trang 12" · "3.2 Electrical"
    chu_thich: str = ""
    duong_dan: str = ""
    ocr: KetQuaOcr | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"so": self.so, "don_vi": self.don_vi, "chu_thich": self.chu_thich,
                "duong_dan": self.duong_dan,
                "ocr": self.ocr.to_dict() if self.ocr else None,
                "tang": "DONG",
                "note_vi": ("Kết quả đọc HÌNH là tầng ĐỒNG — nó là suy đoán từ ảnh, "
                            "không phải trích từ lớp chữ. Người xác nhận thì mới lên.")}


_CHU_THICH = re.compile(
    r"^\s*(?:Figure|Fig\.?|Hình|Bảng|Table)\s*[\d\-.]+\s*[.:–-]?\s*(.{0,120})",
    re.I | re.M)


def tim_chu_thich(chu_trang: str) -> str:
    """Chú thích hình trên cùng trang. Không có thì trả rỗng, không bịa."""
    m = _CHU_THICH.search(chu_trang or "")
    return (m.group(0).strip() if m else "")[:160]


def rut_hinh_tu_pdf(path: Path, thu_muc_ra: Path, *,
                    gioi_han: int = 40) -> tuple[list[Hinh], str]:
    """Rút ảnh nhúng trong PDF bằng `pypdf` — không thêm phụ thuộc mới."""
    try:
        from pypdf import PdfReader
    except ImportError as e:                                 # noqa: BLE001
        return [], f"Không đọc được PDF: {e}"

    thu_muc_ra.mkdir(parents=True, exist_ok=True)
    ra: list[Hinh] = []
    try:
        r = PdfReader(str(path))
    except Exception as e:                                   # noqa: BLE001
        return [], f"PDF không mở được: {e}"

    for i, trang in enumerate(r.pages, 1):
        chu = ""
        try:
            chu = trang.extract_text() or ""
        except Exception:                                    # noqa: BLE001
            pass
        try:
            anh_ds = list(trang.images)
        except Exception:                                    # noqa: BLE001
            continue
        for j, anh in enumerate(anh_ds, 1):
            if len(ra) >= gioi_han:
                return ra, (f"Dừng ở {gioi_han} hình — tài liệu có nhiều hơn. "
                            "Nói cho người dùng biết đã cắt.")
            ten = f"{path.stem}-t{i}-h{j}{Path(anh.name).suffix or '.png'}"
            p_ra = thu_muc_ra / ten
            try:
                p_ra.write_bytes(anh.data)
            except Exception:                                # noqa: BLE001
                continue
            ra.append(Hinh(so=len(ra) + 1, don_vi=f"trang {i}",
                           chu_thich=tim_chu_thich(chu), duong_dan=str(p_ra)))
    return ra, ""


# =========================================================================== từ điển đa ngữ
# §4.7 — bí danh đa ngữ cho khoá chuẩn. Datasheet CH32/GD32 viết tiếng Trung, và
# "工作电压" là đúng cái mà datasheet tiếng Anh gọi "operating voltage".
BI_DANH_DA_NGU: dict[str, str] = {
    # tiếng Trung
    "工作电压": "vdd.range", "电源电压": "vdd.range", "供电电压": "vdd.range",
    "工作温度": "ta.range", "最高频率": "fmax", "主频": "fmax",
    "工作电流": "icc.typ", "静态电流": "icc.typ",
    "闪存": "flash.size", "存储器": "flash.size", "内存": "ram.size",
    # tiếng Việt (tài liệu nội bộ hay viết tiếng Việt)
    "điện áp hoạt động": "vdd.range", "điện áp nguồn": "vdd.range",
    "nhiệt độ hoạt động": "ta.range", "tần số tối đa": "fmax",
    "dòng tiêu thụ": "icc.typ", "bộ nhớ flash": "flash.size", "bộ nhớ ram": "ram.size",
    # tiếng Nhật
    "動作電圧": "vdd.range", "電源電圧": "vdd.range", "動作温度": "ta.range",
}


def khoa_tu_bi_danh(ten: str) -> str:
    """Tên thông số bằng bất kỳ tiếng nào → khoá chuẩn. Không khớp thì trả rỗng."""
    t = (ten or "").strip().lower()
    if t in BI_DANH_DA_NGU:
        return BI_DANH_DA_NGU[t]
    for bd, khoa in BI_DANH_DA_NGU.items():
        if bd in t:
            return khoa
    return ""
