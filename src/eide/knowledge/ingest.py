# -*- coding: utf-8 -*-
"""Phân loại tệp theo NỘI DUNG, không theo đuôi — EIDE-MDD-40 §B3, §C3 bước 4.

    "ingest phân loại theo magic bytes"
    "`archive.list` **chỉ** nhận `archive`"

Vì sao tệp này tồn tại, bằng số liệu của đợt đo 23/09: năm ca trượt vì mọi tệp đều bị
ném vào `archive.list`, và người dùng nhận về **lý do sai**:

| Ca | Tệp | Lõi nói | Đáng lẽ phải nói |
|---|---|---|---|
| TC023 | `mach-khong-loi.net` | "không nhận ra định dạng nén" | đây là netlist KiCad |
| TC025 | `mach.PcbDoc` | "không nhận ra định dạng nén" | Altium nhị phân không hỗ trợ — xuất netlist/PDF |
| TC026 | zip hỏng | "không nhận ra định dạng nén" | tệp cụt/hỏng |
| TC070 | `don-dep.sh` | "không nhận ra định dạng nén" | script có `rm -rf $HOME` — phải hỏi |

Ca cuối là ca nặng nhất: kịch bản chứa `rm -rf $HOME/eide` **không chạy**, nhưng không
phải vì sandbox chặn hay vì ai đó hỏi — mà vì nó bị nhầm thành tệp nén rồi chết ở đó.
Bảng kết quả ghi "đạt". Đó là **an toàn do tai nạn**, và tai nạn thì không lặp lại được.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Magic bytes → loại. Đọc 16 byte đầu là đủ cho mọi định dạng ở đây.
_MAGIC: list[tuple[bytes, str, str]] = [
    (b"%PDF-", "pdf", "PDF"),
    (b"PK\x03\x04", "archive", "ZIP"),
    (b"PK\x05\x06", "archive", "ZIP rỗng"),
    (b"\x1f\x8b", "archive", "gzip"),
    (b"BZh", "archive", "bzip2"),
    (b"\xfd7zXZ", "archive", "xz"),
    (b"7z\xbc\xaf\x27\x1c", "archive", "7-Zip"),
    (b"Rar!\x1a\x07", "archive", "RAR"),
    (b"\x89PNG\r\n\x1a\n", "image", "PNG"),
    (b"\xff\xd8\xff", "image", "JPEG"),
    (b"GIF8", "image", "GIF"),
    (b"II*\x00", "image", "TIFF"),
    (b"MM\x00*", "image", "TIFF"),
    (b"\x00\x01\x00\x00", "unknown", "nhị phân"),
]

# Định dạng NHẬN RA ĐƯỢC nhưng KHÔNG hỗ trợ — phải nói đúng tên và đường đi tiếp.
_KHONG_HO_TRO: dict[str, tuple[str, list[str]]] = {
    ".pcbdoc": ("Altium PCB (nhị phân)", ["xuất netlist (.net)", "xuất PDF schematic"]),
    ".schdoc": ("Altium Schematic (nhị phân)", ["xuất netlist (.net)", "xuất PDF"]),
    ".prjpcb": ("Altium Project", ["xuất netlist (.net)"]),
    ".brd": ("Eagle/Fusion board (nhị phân)", ["xuất netlist", "xuất PDF"]),
    ".sch": ("Eagle schematic (nhị phân)", ["xuất netlist", "xuất PDF"]),
    ".dsn": ("OrCAD/Allegro", ["xuất netlist chuẩn", "xuất PDF"]),
    ".ms14": ("Multisim", ["xuất netlist"]),
    ".ms12": ("Multisim", ["xuất netlist"]),
    ".dwg": ("AutoCAD", ["xuất PDF"]),
}

_DUOI_NETLIST = {".net", ".cir", ".sp", ".spi", ".kicad_netlist"}
_DUOI_SCHEMATIC_VAN_BAN = {".kicad_sch", ".kicad_pcb", ".kicad_pro"}
_DUOI_MA = {".c", ".h", ".cpp", ".cc", ".hpp", ".s", ".asm", ".ino", ".py", ".rs",
            ".go", ".java", ".ts", ".js"}
_DUOI_SCRIPT = {".sh", ".bash", ".zsh", ".ps1", ".bat", ".cmd"}
_DUOI_CAPTURE = {".csv", ".sal", ".vcd", ".logicdata", ".sr"}
_DUOI_LOG = {".log", ".txt", ".out"}
_DUOI_CAU_HINH = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".dts"}


# =========================================================================== quét an toàn
@dataclass(slots=True)
class CanhBaoScript:
    """Một lệnh đáng ngờ trong script — TC070."""

    dong: int
    lenh: str
    vi_sao: str
    muc: str            # "chan" (phải hỏi) | "canh" (nhắc)


# Mỗi mẫu đi kèm LÝ DO đọc được. Một cảnh báo không nói vì sao thì người sẽ bấm qua.
_MAU_NGUY_HIEM: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"\brm\s+(-[rRfv]+\s+)*(-[rRfv]+\s*)?(/|\$HOME|~|\$\{?HOME)"),
     "xoá đệ quy thư mục gốc hoặc thư mục người dùng", "chan"),
    (re.compile(r"\bdd\s+[^\n]*\bof=/dev/(sd|nvme|mmcblk|disk)"),
     "ghi thẳng vào thiết bị khối — xoá sạch ổ nếu sai tên", "chan"),
    (re.compile(r"\bmkfs(\.\w+)?\b"), "định dạng lại phân vùng", "chan"),
    (re.compile(r"\b(shred|wipefs)\b"), "xoá không khôi phục được", "chan"),
    (re.compile(r"[:\s]\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:"), "fork bomb", "chan"),
    (re.compile(r"\bchmod\s+(-R\s+)?777\s+/"), "mở toàn quyền trên thư mục gốc", "chan"),
    (re.compile(r"(id_rsa|id_ed25519|\.ssh/|\.aws/credentials|\.netrc)"),
     "đụng tới khoá riêng hoặc thông tin đăng nhập", "chan"),
    (re.compile(r"\b(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba)?sh"),
     "tải rồi chạy thẳng — nội dung không ai kiểm được trước", "chan"),
    (re.compile(r"\b(nc|netcat|ncat)\b[^\n]*\s-e\b"), "mở shell qua mạng", "chan"),
    (re.compile(r"\b(history\s+-c|unset\s+HISTFILE)\b"), "xoá dấu vết lệnh đã chạy", "chan"),
    (re.compile(r"\bsudo\b"), "chạy với quyền quản trị", "canh"),
    (re.compile(r"\b(systemctl|service)\s+(enable|start|disable)"),
     "đổi dịch vụ chạy nền của máy", "canh"),
    (re.compile(r"\bcrontab\b"), "đặt lịch chạy tự động", "canh"),
    (re.compile(r"\bgit\s+push\s+(-f|--force)"), "ghi đè lịch sử kho từ xa", "canh"),
]


def quet_script(noi_dung: str) -> list[CanhBaoScript]:
    """Quét tĩnh một script trước khi nó được nạp vào dự án (TC070).

    Đây là quét TĨNH — đọc chữ, không chạy. Nó không bắt được script sinh lệnh động,
    và nói thẳng điều đó thay vì hứa nhiều hơn khả năng.
    """
    ra: list[CanhBaoScript] = []
    for i, dong in enumerate(noi_dung.splitlines(), 1):
        chu = dong.strip()
        if not chu or chu.startswith("#"):
            continue
        for mau, vi_sao, muc in _MAU_NGUY_HIEM:
            if mau.search(chu):
                ra.append(CanhBaoScript(dong=i, lenh=chu[:120], vi_sao=vi_sao, muc=muc))
                break
    return ra


# =========================================================================== phân loại
@dataclass(slots=True)
class KetQuaPhanLoai:
    loai: str                                   # archive|netlist|schematic|source|script|
                                                # log|capture|pdf|image|config|unknown
    mo_ta: str                                  # tên định dạng cho người đọc
    doc_duoc: bool
    ly_do_khong_doc: str = ""
    de_xuat: list[str] = field(default_factory=list)
    kich_thuoc: int = 0
    so_dong: int | None = None
    so_trang: int | None = None
    canh_bao: list[CanhBaoScript] = field(default_factory=list)
    chi_tiet: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loai": self.loai, "mo_ta": self.mo_ta, "doc_duoc": self.doc_duoc,
            "ly_do_khong_doc": self.ly_do_khong_doc, "de_xuat": self.de_xuat,
            "kich_thuoc": self.kich_thuoc, "so_dong": self.so_dong,
            "so_trang": self.so_trang,
            "canh_bao": [{"dong": c.dong, "lenh": c.lenh, "vi_sao": c.vi_sao,
                          "muc": c.muc} for c in self.canh_bao],
            **self.chi_tiet,
        }

    @property
    def can_hoi_nguoi(self) -> bool:
        return any(c.muc == "chan" for c in self.canh_bao)


def phan_loai(path: Path) -> KetQuaPhanLoai:
    """Nhìn vào NỘI DUNG trước, đuôi sau. Trả lý do đúng khi không đọc được."""
    if not path.exists():
        return KetQuaPhanLoai("unknown", "không tồn tại", False,
                              ly_do_khong_doc=f"Không có tệp nào ở {path.name}.")
    if path.is_dir():
        return KetQuaPhanLoai("unknown", "thư mục", False,
                              ly_do_khong_doc="Đây là thư mục, không phải tệp.",
                              de_xuat=["Chỉ đúng tệp cần nạp"])

    cỡ = path.stat().st_size
    duoi = path.suffix.lower()
    dau = path.open("rb").read(16)

    # --- Định dạng nhận ra được nhưng không hỗ trợ: nói ĐÚNG TÊN (TC025).
    if duoi in _KHONG_HO_TRO:
        ten, cach = _KHONG_HO_TRO[duoi]
        return KetQuaPhanLoai(
            "unsupported", ten, False, kich_thuoc=cỡ,
            ly_do_khong_doc=f"Định dạng {ten} không nằm trong danh sách EIDE đọc được.",
            de_xuat=cach)

    # --- Magic bytes.
    for magic, loai, ten in _MAGIC:
        if dau.startswith(magic):
            if loai == "archive":
                return _doc_archive(path, ten, cỡ)
            if loai == "pdf":
                return _doc_pdf(path, cỡ)
            if loai == "image":
                return KetQuaPhanLoai(
                    "image", ten, False, kich_thuoc=cỡ,
                    ly_do_khong_doc="Ảnh chỉ đọc được bằng OCR, và số đọc từ ảnh luôn "
                                    "kém tin cậy hơn số đọc từ PDF có chữ.",
                    de_xuat=["Nạp bản PDF có chữ nếu có",
                             "Chấp nhận đọc ảnh với cảnh báo độ tin cậy"])
            return KetQuaPhanLoai(loai, ten, False, kich_thuoc=cỡ,
                                  ly_do_khong_doc=f"Tệp nhị phân định dạng {ten}.")

    # --- Từ đây là văn bản. Đọc thử để loại tệp nhị phân không có magic.
    try:
        chu = path.read_text("utf-8")
    except UnicodeDecodeError:
        return KetQuaPhanLoai(
            "unknown", "nhị phân", False, kich_thuoc=cỡ,
            ly_do_khong_doc="Tệp không phải văn bản UTF-8 và không khớp định dạng nào "
                            "EIDE nhận ra.",
            de_xuat=["Cho biết tệp này do phần mềm nào tạo ra"])

    so_dong = chu.count("\n") + 1

    if duoi in _DUOI_SCRIPT or chu.startswith("#!"):
        cb = quet_script(chu)
        return KetQuaPhanLoai("script", "script shell", True, kich_thuoc=cỡ,
                              so_dong=so_dong, canh_bao=cb)

    if duoi in _DUOI_NETLIST or _la_netlist(chu):
        return KetQuaPhanLoai("netlist", _ten_netlist(chu), True, kich_thuoc=cỡ,
                              so_dong=so_dong,
                              chi_tiet={"so_net": _dem_net(chu)})

    if duoi in _DUOI_SCHEMATIC_VAN_BAN:
        return KetQuaPhanLoai("schematic", "KiCad (văn bản)", True, kich_thuoc=cỡ,
                              so_dong=so_dong)

    if duoi in _DUOI_MA:
        return KetQuaPhanLoai("source", f"mã nguồn {duoi[1:]}", True,
                              kich_thuoc=cỡ, so_dong=so_dong)

    if duoi in _DUOI_CAPTURE:
        return _doc_capture(path, chu, cỡ, so_dong)

    if duoi in _DUOI_CAU_HINH:
        return KetQuaPhanLoai("config", f"cấu hình {duoi[1:]}", True,
                              kich_thuoc=cỡ, so_dong=so_dong)

    if duoi in _DUOI_LOG or duoi == ".md":
        return KetQuaPhanLoai("log" if duoi != ".md" else "note",
                              "log" if duoi != ".md" else "Markdown",
                              True, kich_thuoc=cỡ, so_dong=so_dong)

    return KetQuaPhanLoai("text", "văn bản thuần", True, kich_thuoc=cỡ, so_dong=so_dong)


# =========================================================================== bộ đọc
def _doc_archive(path: Path, ten: str, cỡ: int) -> KetQuaPhanLoai:
    """Tệp nén. Hỏng thì nói là HỎNG, không nói "không nhận ra" (TC026)."""
    if ten.startswith("ZIP"):
        try:
            with zipfile.ZipFile(path) as z:
                hong = z.testzip()
                if hong is not None:
                    return KetQuaPhanLoai(
                        "archive", ten, False, kich_thuoc=cỡ,
                        ly_do_khong_doc=f"Tệp nén bị hỏng: mục “{hong}” không giải nén được.",
                        de_xuat=["Nén lại và nạp bản mới"])
                ds = z.namelist()
            return KetQuaPhanLoai("archive", ten, True, kich_thuoc=cỡ,
                                  chi_tiet={"so_muc": len(ds), "muc": ds[:50]})
        except zipfile.BadZipFile as e:
            return KetQuaPhanLoai(
                "archive", ten, False, kich_thuoc=cỡ,
                ly_do_khong_doc=f"Tệp nén bị hỏng hoặc cụt: {e}.",
                de_xuat=["Tải lại tệp", "Nén lại từ nguồn gốc"])
    return KetQuaPhanLoai("archive", ten, True, kich_thuoc=cỡ)


def _doc_pdf(path: Path, cỡ: int) -> KetQuaPhanLoai:
    try:
        from pypdf import PdfReader
        r = PdfReader(str(path))
        n = len(r.pages)
        co_chu = any((p.extract_text() or "").strip() for p in r.pages[:5])
    except Exception as e:                                   # noqa: BLE001
        return KetQuaPhanLoai("pdf", "PDF", False, kich_thuoc=cỡ,
                              ly_do_khong_doc=f"PDF hỏng hoặc có mật khẩu: {e}",
                              de_xuat=["Nạp bản PDF không khoá"])
    if not co_chu:
        # PDF scan: đọc được nhưng phải nói rõ số sẽ kém tin cậy (TC044).
        return KetQuaPhanLoai(
            "pdf", "PDF scan (ảnh, không có lớp chữ)", False, kich_thuoc=cỡ, so_trang=n,
            ly_do_khong_doc="PDF này là ảnh scan, không có lớp chữ để trích. Số đọc bằng "
                            "OCR luôn kém tin cậy và phải được người xác nhận từng dòng.",
            de_xuat=["Nạp bản PDF gốc từ nhà sản xuất nếu có",
                     "Chấp nhận OCR với nhãn độ tin cậy thấp"])
    return KetQuaPhanLoai("pdf", "PDF có lớp chữ", True, kich_thuoc=cỡ, so_trang=n)


def _doc_capture(path: Path, chu: str, cỡ: int, so_dong: int) -> KetQuaPhanLoai:
    """Tệp đo từ máy phân tích logic. Đọc dòng tiêu đề là biết cấu trúc cột (TC049)."""
    dong = chu.splitlines()
    tieu_de = dong[0] if dong else ""
    cot = [c.strip() for c in re.split(r"[,;\t]", tieu_de)] if tieu_de else []
    return KetQuaPhanLoai(
        "capture", "capture từ máy phân tích logic", True, kich_thuoc=cỡ,
        so_dong=so_dong,
        chi_tiet={"cot": cot, "so_mau": max(0, so_dong - 1),
                  "giao_thuc_doan": _doan_giao_thuc(cot)})


def _doan_giao_thuc(cot: list[str]) -> str:
    c = " ".join(cot).lower()
    if "sda" in c or "scl" in c:
        return "I2C"
    if "miso" in c or "mosi" in c or "sck" in c:
        return "SPI"
    if "tx" in c and "rx" in c:
        return "UART"
    if "can" in c:
        return "CAN"
    return ""


def _la_netlist(chu: str) -> bool:
    d = chu[:4000].lower()
    return (("(export" in d and "(components" in d)
            or ("(netlist" in d)
            or re.search(r"^\s*\.subckt\b", d, re.MULTILINE) is not None
            or ("*net" in d and "*pin" in d))


def _ten_netlist(chu: str) -> str:
    d = chu[:2000].lower()
    if "(export" in d or "kicad" in d:
        return "netlist KiCad"
    if ".subckt" in d or ".model" in d:
        return "netlist SPICE"
    return "netlist"


def _dem_net(chu: str) -> int:
    return len(re.findall(r"\(net\s", chu)) or len(re.findall(r"^\*NET", chu, re.MULTILINE))
