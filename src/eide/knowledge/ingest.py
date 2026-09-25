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
import tarfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..errors import (corrupt_file, macro_ignored, over_limit, unsupported_format,
                      zip_bomb)

# --------------------------------------------------------------------------- ba mức
# EIDE-ING-43 §2. Nhị phân "đọc được / không đọc được" là chưa đủ để người quyết định:
# giữa hai cực đó có cả một vùng "đọc được chữ nhưng đừng tin số tự trích" — và đúng
# vùng đó là nơi người cần biết mình phải tự rà.
DAY_DU = "day_du"          # đọc cấu trúc · trích Fact ứng viên · trích dẫn được
MOT_PHAN = "mot_phan"      # đọc chữ/bảng vào tri thức, KHÔNG trích Fact tự động
KHONG = "khong"            # từ chối, nói đúng lý do và đường đi tiếp

NHAN_MUC = {DAY_DU: "ĐẦY ĐỦ", MOT_PHAN: "MỘT PHẦN", KHONG: "KHÔNG"}

# Magic bytes → loại. Đọc 16 byte đầu là đủ cho mọi định dạng ở đây.
#
# Lưu ý thứ tự dùng ở `phan_loai`: bảng này KHÔNG còn được duyệt tuyến tính như bản
# trước. ZIP phải được mở ra soi bên trong trước khi gọi là "tệp nén", vì `.docx`,
# `.xlsx`, `.pptx`, `.odt` đều là ZIP (ING-43 §3).
_MAGIC: list[tuple[bytes, str, str]] = [
    (b"%PDF-", "pdf", "PDF"),
    (b"\x89PNG\r\n\x1a\n", "image", "PNG"),
    (b"\xff\xd8\xff", "image", "JPEG"),
    (b"GIF8", "image", "GIF"),
    (b"II*\x00", "image", "TIFF"),
    (b"MM\x00*", "image", "TIFF"),
    (b"\x7fELF", "elf", "ELF"),
]

_ZIP = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_NEN_KHAC: list[tuple[bytes, str]] = [
    (b"\x1f\x8b", "gzip"),
    (b"BZh", "bzip2"),
    (b"\xfd7zXZ", "xz"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip"),
    (b"Rar!\x1a\x07", "RAR"),
]

# ZIP có [Content_Types].xml + thư mục này → đúng loại Office, không phải tệp nén.
_OFFICE_OPENXML: list[tuple[str, str, str, str]] = [
    ("word/", "docx", "Word (.docx)", DAY_DU),
    ("xl/", "xlsx", "Excel (.xlsx)", DAY_DU),
    ("ppt/", "pptx", "PowerPoint (.pptx)", MOT_PHAN),
]

# Office cũ (OLE2) → đọc được qua LibreOffice. Đuôi phân biệt với Altium, vốn cũng OLE2.
_OFFICE_CU = {".doc": "Word 97–2003 (.doc)", ".xls": "Excel 97–2003 (.xls)",
              ".ppt": "PowerPoint 97–2003 (.ppt)"}

# Định dạng NHẬN RA ĐƯỢC nhưng KHÔNG hỗ trợ — phải nói đúng tên và đường đi tiếp.
_KHONG_HO_TRO: dict[str, tuple[str, list[str]]] = {
    ".pcbdoc": ("Altium PCB (nhị phân)", ["xuất netlist (.net)", "xuất PDF schematic"]),
    ".schdoc": ("Altium Schematic (nhị phân)", ["xuất netlist (.net)", "xuất PDF"]),
    ".prjpcb": ("Altium Project", ["xuất netlist (.net)"]),
    ".dsn": ("OrCAD/Allegro", ["xuất netlist chuẩn", "xuất PDF"]),
    ".ms14": ("Multisim", ["xuất netlist"]),
    ".ms12": ("Multisim", ["xuất netlist"]),
    ".dwg": ("AutoCAD", ["xuất PDF"]),
}

# Đuôi có HAI đời: đời cũ nhị phân, đời mới là văn bản/XML. Không được từ chối theo đuôi
# — phải mở ra xem. Eagle từ v6 lưu XML; từ chối `.sch` theo đuôi là từ chối nhầm đúng
# cái định dạng ING-43 §2 xếp mức MỘT PHẦN.
_NHI_PHAN_EDA: dict[str, tuple[str, list[str]]] = {
    ".sch": ("Eagle schematic đời cũ (nhị phân)", ["mở bằng Eagle rồi lưu lại (XML)",
                                                   "xuất netlist"]),
    ".brd": ("Eagle board đời cũ (nhị phân)", ["mở bằng Eagle rồi lưu lại (XML)",
                                               "xuất netlist"]),
}

_DUOI_NETLIST = {".net", ".cir", ".sp", ".spi", ".kicad_netlist"}
_DUOI_SCHEMATIC_VAN_BAN = {".kicad_sch", ".kicad_pcb", ".kicad_pro"}
_DUOI_CAU_HINH_VENDOR = {".ioc", ".dts", ".dtsi", ".overlay", ".ld", ".map", "sdkconfig"}
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
    loai: str                                   # archive|docx|xlsx|pptx|office_cu|netlist|
                                                # schematic|eagle|source|script|log|capture|
                                                # pdf|image|elf|config|vendor|text|unknown
    mo_ta: str                                  # tên định dạng cho người đọc
    doc_duoc: bool
    muc_ho_tro: str = KHONG                     # day_du | mot_phan | khong (ING-02)
    ly_do_phan_loai: str = ""                   # "zip có word/ → DOCX" (ING-01)
    do_tin_cay: float = 1.0                     # 1,0 = magic bytes · 0,6 = chỉ theo đuôi
    ly_do_khong_doc: str = ""
    de_xuat: list[str] = field(default_factory=list)
    kich_thuoc: int = 0
    so_dong: int | None = None
    so_trang: int | None = None
    canh_bao: list[CanhBaoScript] = field(default_factory=list)
    loi: Any = None                             # EideError khi có mã lỗi cụ thể
    chi_tiet: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "loai": self.loai, "mo_ta": self.mo_ta, "doc_duoc": self.doc_duoc,
            "muc_ho_tro": self.muc_ho_tro, "muc_ho_tro_vi": NHAN_MUC[self.muc_ho_tro],
            "ly_do_phan_loai": self.ly_do_phan_loai, "do_tin_cay": self.do_tin_cay,
            "ly_do_khong_doc": self.ly_do_khong_doc, "de_xuat": self.de_xuat,
            "kich_thuoc": self.kich_thuoc, "so_dong": self.so_dong,
            "so_trang": self.so_trang,
            "ma_loi": getattr(self.loi, "code", None),
            "canh_bao": [{"dong": c.dong, "lenh": c.lenh, "vi_sao": c.vi_sao,
                          "muc": c.muc} for c in self.canh_bao],
            **self.chi_tiet,
        }

    @property
    def can_hoi_nguoi(self) -> bool:
        return any(c.muc == "chan" for c in self.canh_bao)

    @property
    def trich_fact_duoc(self) -> bool:
        """Chỉ mức ĐẦY ĐỦ mới được trích Fact tự động — §2."""
        return self.muc_ho_tro == DAY_DU


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

    # --- 1. Định dạng luôn là nhị phân độc quyền: nói ĐÚNG TÊN (TC025).
    # Phải đứng trước phép kiểm OLE2 bên dưới, vì Altium `.PcbDoc` CŨNG là OLE2 và nếu
    # để nó rơi vào nhánh "Office cũ" thì ta sẽ gửi nó cho LibreOffice một cách vô nghĩa.
    if duoi in _KHONG_HO_TRO:
        ten, cach = _KHONG_HO_TRO[duoi]
        return KetQuaPhanLoai(
            "unsupported", ten, False, muc_ho_tro=KHONG,
            ly_do_phan_loai=f"đuôi {duoi} → {ten}", do_tin_cay=0.9, kich_thuoc=cỡ,
            ly_do_khong_doc=f"Định dạng {ten} không nằm trong danh sách EIDE đọc được.",
            de_xuat=cach, loi=unsupported_format(path.name, ten, _DINH_DANG_DOC_DUOC))

    # --- 2. PDF và ảnh: magic bytes nói chắc chắn.
    for magic, loai, ten in _MAGIC:
        if not dau.startswith(magic):
            continue
        if loai == "pdf":
            return _doc_pdf(path, cỡ)
        if loai == "image":
            return KetQuaPhanLoai(
                "image", ten, False, muc_ho_tro=MOT_PHAN,
                ly_do_phan_loai=f"magic bytes → {ten}", kich_thuoc=cỡ,
                ly_do_khong_doc="Ảnh chỉ đọc được bằng OCR, và số đọc từ ảnh luôn kém "
                                "tin cậy hơn số đọc từ PDF có chữ.",
                de_xuat=["Nạp bản PDF có chữ nếu có",
                         "Chấp nhận đọc ảnh với cảnh báo độ tin cậy"])
        return KetQuaPhanLoai(loai, ten, False, muc_ho_tro=MOT_PHAN,
                              ly_do_phan_loai=f"magic bytes → {ten}", kich_thuoc=cỡ,
                              ly_do_khong_doc=f"Tệp nhị phân định dạng {ten}.")

    # --- 3. ZIP: MỞ RA XEM trước khi gọi là tệp nén (ING-43 §3).
    #
    # Đây là sửa lỗi trung tâm của bước ING-A. `.docx`/`.xlsx`/`.pptx`/`.odt` đều là ZIP;
    # bản trước khớp `PK\x03\x04` rồi dừng, nên một tệp Word bị bóc thành `word/
    # document.xml` — cùng hình dạng với TC023, chỉ khác định dạng.
    if dau.startswith(_ZIP):
        return _doc_zip(path, cỡ)

    # --- 4. OLE2: Office đời cũ (Altium đã bị loại ở bước 1).
    if dau.startswith(_OLE2):
        if duoi in _OFFICE_CU:
            return KetQuaPhanLoai(
                "office_cu", _OFFICE_CU[duoi], True, muc_ho_tro=DAY_DU,
                ly_do_phan_loai=f"OLE2 + đuôi {duoi} → {_OFFICE_CU[duoi]}",
                kich_thuoc=cỡ,
                chi_tiet={"can_chuyen_doi": True, "chuyen_sang": _CHUYEN_SANG[duoi]})
        return KetQuaPhanLoai(
            "unknown", "tài liệu nhị phân OLE2", False, muc_ho_tro=KHONG,
            ly_do_phan_loai="OLE2 nhưng đuôi không nhận ra", do_tin_cay=0.7,
            kich_thuoc=cỡ,
            ly_do_khong_doc="Tệp theo định dạng OLE2 (Office đời cũ hoặc phần mềm EDA) "
                            "nhưng đuôi không cho biết là gì.",
            de_xuat=["Cho biết tệp này do phần mềm nào tạo ra"])

    # --- 5. Các định dạng nén khác.
    for magic, ten in _NEN_KHAC:
        if dau.startswith(magic):
            return _doc_nen_khac(path, ten, cỡ)
    if tarfile.is_tarfile(path):
        return _doc_nen_khac(path, "tar", cỡ)

    # --- 6. Từ đây là văn bản. Đọc thử để loại tệp nhị phân không có magic.
    try:
        chu = path.read_text("utf-8")
    except UnicodeDecodeError:
        if duoi in _NHI_PHAN_EDA:
            ten, cach = _NHI_PHAN_EDA[duoi]
            return KetQuaPhanLoai(
                "unsupported", ten, False, muc_ho_tro=KHONG,
                ly_do_phan_loai=f"đuôi {duoi} nhưng nội dung là nhị phân → đời cũ",
                kich_thuoc=cỡ,
                ly_do_khong_doc=f"{ten} — EIDE đọc được bản XML, không đọc được bản này.",
                de_xuat=cach, loi=unsupported_format(path.name, ten, _DINH_DANG_DOC_DUOC))
        return KetQuaPhanLoai(
            "unknown", "nhị phân", False, muc_ho_tro=KHONG,
            ly_do_phan_loai="không giải mã được UTF-8 và không khớp magic nào",
            do_tin_cay=0.8, kich_thuoc=cỡ,
            ly_do_khong_doc="Tệp không phải văn bản UTF-8 và không khớp định dạng nào "
                            "EIDE nhận ra.",
            de_xuat=["Cho biết tệp này do phần mềm nào tạo ra"])

    so_dong = chu.count("\n") + 1
    dau_chu = chu.lstrip()[:4000]

    def ra(loai: str, mo_ta: str, muc: str, vi_sao: str, **kw: Any) -> KetQuaPhanLoai:
        return KetQuaPhanLoai(loai, mo_ta, True, muc_ho_tro=muc, ly_do_phan_loai=vi_sao,
                              kich_thuoc=cỡ, so_dong=so_dong, **kw)

    # S-expression và XML đứng trước mọi phép kiểm theo đuôi — nội dung nói chắc hơn.
    if duoi in _DUOI_NETLIST or _la_netlist(chu):
        return ra("netlist", _ten_netlist(chu), DAY_DU,
                  "nội dung S-expression `(export`/`(netlist`",
                  chi_tiet={"so_net": _dem_net(chu)})

    if dau_chu.startswith("(kicad_sch") or duoi in _DUOI_SCHEMATIC_VAN_BAN:
        return ra("schematic", "KiCad (văn bản)", MOT_PHAN,
                  "S-expression `(kicad_sch`" if dau_chu.startswith("(kicad_sch")
                  else f"đuôi {duoi}")

    if dau_chu.startswith("<?xml") or dau_chu.startswith("<eagle"):
        if "<eagle" in dau_chu:
            return ra("eagle", "Eagle (XML)", MOT_PHAN, "XML có thẻ <eagle>")
        if "<device" in dau_chu and "peripheral" in chu[:20000].lower():
            return ra("svd", "SVD (thanh ghi từ nhà sản xuất)", DAY_DU,
                      "XML có <device> + <peripheral>")
        return ra("xml", "XML", MOT_PHAN, "bắt đầu bằng <?xml")

    if duoi in _DUOI_SCRIPT or chu.startswith("#!"):
        return ra("script", "script shell", DAY_DU,
                  f"đuôi {duoi}" if duoi in _DUOI_SCRIPT else "bắt đầu bằng #!",
                  canh_bao=quet_script(chu))

    if duoi == ".ioc" and "Mcu.Name" in chu[:8000]:
        return ra("vendor", "STM32CubeMX (.ioc)", DAY_DU, "đuôi .ioc + khoá Mcu.Name")
    if duoi in (".dts", ".dtsi", ".overlay"):
        return ra("vendor", f"devicetree {duoi[1:]}", DAY_DU, f"đuôi {duoi}")
    if duoi == ".ld" or (duoi == ".map" and "MEMORY" in chu[:4000]):
        return ra("vendor", "linker script", DAY_DU, f"đuôi {duoi}")
    if path.name == "sdkconfig" or path.name.startswith("sdkconfig."):
        return ra("vendor", "ESP-IDF sdkconfig", DAY_DU, "tên tệp sdkconfig")

    if duoi in _DUOI_MA:
        return ra("source", f"mã nguồn {duoi[1:]}", DAY_DU, f"đuôi {duoi}")

    if duoi in _DUOI_CAPTURE:
        return _doc_capture(path, chu, cỡ, so_dong)

    if duoi in _DUOI_CAU_HINH:
        return ra("config", f"cấu hình {duoi[1:]}", MOT_PHAN, f"đuôi {duoi}")

    if duoi in (".md", ".markdown"):
        return ra("note", "Markdown", DAY_DU, f"đuôi {duoi}")
    if duoi in (".html", ".htm"):
        return ra("html", "HTML", MOT_PHAN, f"đuôi {duoi}")
    if duoi in _DUOI_LOG:
        return ra("log", "log", DAY_DU, f"đuôi {duoi}")

    return KetQuaPhanLoai("text", "văn bản thuần", True, muc_ho_tro=MOT_PHAN,
                          ly_do_phan_loai="không khớp dấu hiệu nào — coi là văn bản",
                          do_tin_cay=0.5, kich_thuoc=cỡ, so_dong=so_dong)


# =========================================================================== giới hạn
# ING-43 §4.1. Mỗi con số ở đây là một cái phanh, và mỗi cái phanh phải nói được nó
# đang phanh vì cái gì — nếu không, người dùng chỉ thấy "không nạp được" và bỏ cuộc.
TRAN_CAP = 3                  # bóc đệ quy tối đa 3 cấp
TRAN_TONG_BYTE = 500 * 1024 * 1024
TRAN_SO_TEP = 2000
TRAN_TY_LE_NEN = 100.0        # giải nén ra gấp > 100 lần → dừng, không bóc thử
NHIEU_TEP = 20                # hơn ngần này thì hỏi người chọn nạp cái nào (ING-04)

# Danh sách đưa vào thông báo lỗi E1001 — thứ EIDE thật sự đọc được hôm nay.
_DINH_DANG_DOC_DUOC = ["PDF có lớp chữ", ".docx/.xlsx/.pptx", "netlist KiCad (.net)",
                       ".kicad_sch", "Eagle XML", "SVD", "mã nguồn", ".csv/.vcd",
                       "Markdown/HTML", "tệp nén (.zip/.tar/.gz/.7z/.rar)"]

_CHUYEN_SANG = {".doc": ".docx", ".xls": ".xlsx", ".ppt": ".pptx"}


# =========================================================================== bộ đọc
def _doc_zip(path: Path, cỡ: int) -> KetQuaPhanLoai:
    """ZIP: soi danh sách mục TRƯỚC, rồi mới kết luận là Office hay là tệp nén.

    Thứ tự này là toàn bộ nội dung của ING-43 §3 và là lý do bước ING-A tồn tại.
    """
    try:
        with zipfile.ZipFile(path) as z:
            ds = z.namelist()
            # Office OpenXML: có bảng kê kiểu nội dung + thư mục riêng của từng ứng dụng.
            if "[Content_Types].xml" in ds:
                for tien_to, loai, ten, muc in _OFFICE_OPENXML:
                    if any(n.startswith(tien_to) for n in ds):
                        macro = [n for n in ds
                                 if n.endswith(".bin") and "vbaProject" in n]
                        kq = KetQuaPhanLoai(
                            loai, ten, True, muc_ho_tro=muc,
                            ly_do_phan_loai=f"zip có [Content_Types].xml và {tien_to} → {ten}",
                            kich_thuoc=cỡ,
                            chi_tiet={"so_muc_zip": len(ds),
                                      "so_anh_nhung": sum(1 for n in ds
                                                          if "/media/" in n)})
                        if macro:
                            # ING-14: đọc dữ liệu, KHÔNG chạy macro, và nói ra.
                            kq.loi = macro_ignored(path.name, len(macro))
                            kq.chi_tiet["macro_bi_bo_qua"] = len(macro)
                        return kq
            if "mimetype" in ds:
                try:
                    with z.open("mimetype") as f:
                        mt = f.read(64).decode("ascii", "ignore")
                except Exception:                                # noqa: BLE001
                    mt = ""
                if mt.startswith("application/vnd.oasis"):
                    return KetQuaPhanLoai(
                        "office_cu", f"OpenDocument ({mt.rsplit('.', 1)[-1]})", True,
                        muc_ho_tro=DAY_DU,
                        ly_do_phan_loai=f"zip có mimetype {mt} → OpenDocument",
                        kich_thuoc=cỡ,
                        chi_tiet={"can_chuyen_doi": True, "chuyen_sang": ".docx"})

            # Không phải Office → đúng là tệp nén. Kiểm hỏng và kiểm tỉ lệ nén.
            hong = z.testzip()
            if hong is not None:
                return KetQuaPhanLoai(
                    "archive", "ZIP", False, muc_ho_tro=KHONG,
                    ly_do_phan_loai="zip đọc được nhưng CRC sai", kich_thuoc=cỡ,
                    ly_do_khong_doc=f"Tệp nén bị hỏng: mục “{hong}” không giải nén được.",
                    de_xuat=["Nén lại và nạp bản mới"],
                    loi=corrupt_file(path.name, f"mục “{hong}” sai CRC"))

            bung = sum(i.file_size for i in z.infolist())
            ty_le = bung / max(1, cỡ)
            if ty_le > TRAN_TY_LE_NEN and bung > 50 * 1024 * 1024:
                lon = max(z.infolist(), key=lambda i: i.file_size)
                return KetQuaPhanLoai(
                    "archive", "ZIP", False, muc_ho_tro=KHONG,
                    ly_do_phan_loai=f"tỉ lệ nén {ty_le:.0f}× vượt trần {TRAN_TY_LE_NEN:.0f}×",
                    kich_thuoc=cỡ,
                    ly_do_khong_doc=f"Giải nén ra {bung / 1048576:.0f} MB từ một tệp "
                                    f"{cỡ / 1024:.0f} KB.",
                    de_xuat=["Hỏi nguồn gốc tệp nén", "Nạp từng tệp rời"],
                    loi=zip_bomb(path.name, ty_le, lon.filename))
            if bung > TRAN_TONG_BYTE:
                return KetQuaPhanLoai(
                    "archive", "ZIP", False, muc_ho_tro=KHONG,
                    ly_do_phan_loai=f"nội dung {bung / 1048576:.0f} MB vượt trần",
                    kich_thuoc=cỡ,
                    ly_do_khong_doc=f"Gói này giải nén ra {bung / 1048576:.0f} MB.",
                    de_xuat=["Chọn vài tệp cần nạp thay vì cả gói"],
                    loi=over_limit(path.name, "tổng kích thước sau giải nén",
                                   f"{bung / 1048576:.0f} MB",
                                   f"{TRAN_TONG_BYTE / 1048576:.0f} MB"))
            if len(ds) > TRAN_SO_TEP:
                return KetQuaPhanLoai(
                    "archive", "ZIP", False, muc_ho_tro=KHONG,
                    ly_do_phan_loai=f"{len(ds)} mục vượt trần {TRAN_SO_TEP}",
                    kich_thuoc=cỡ,
                    ly_do_khong_doc=f"Gói này có {len(ds)} tệp.",
                    de_xuat=["Chọn vài tệp cần nạp"],
                    loi=over_limit(path.name, "số tệp", len(ds), TRAN_SO_TEP))
            xau = [n for n in ds if n.startswith("/") or ".." in Path(n).parts]
            if xau:
                return KetQuaPhanLoai(
                    "archive", "ZIP", False, muc_ho_tro=KHONG,
                    ly_do_phan_loai="đường dẫn trong gói trỏ ra ngoài", kich_thuoc=cỡ,
                    ly_do_khong_doc=f"Gói chứa đường dẫn thoát ra ngoài: {xau[0]}.",
                    de_xuat=["Hỏi nguồn gốc gói này"],
                    loi=zip_bomb(path.name, ty_le, xau[0]))

            cay = _cay_tep(ds, z.infolist())
            return KetQuaPhanLoai(
                "archive", "ZIP", True, muc_ho_tro=DAY_DU,
                ly_do_phan_loai=f"zip không có [Content_Types].xml → tệp nén thật "
                                f"({len(ds)} mục)",
                kich_thuoc=cỡ,
                chi_tiet={"so_muc": len(ds), "muc": ds[:50], "cay": cay,
                          "bung_ra": bung, "ty_le_nen": round(ty_le, 1),
                          "can_chon": len(ds) > NHIEU_TEP})
    except zipfile.BadZipFile as e:
        return KetQuaPhanLoai(
            "archive", "ZIP", False, muc_ho_tro=KHONG,
            ly_do_phan_loai="magic ZIP nhưng không mở được", kich_thuoc=cỡ,
            ly_do_khong_doc=f"Tệp nén bị hỏng hoặc cụt: {e}.",
            de_xuat=["Tải lại tệp", "Nén lại từ nguồn gốc"],
            loi=corrupt_file(path.name, str(e)))


def _doc_nen_khac(path: Path, ten: str, cỡ: int) -> KetQuaPhanLoai:
    """gzip/bzip2/xz/7z/rar/tar. Chỉ `tar` đọc được danh sách mà không cần gói ngoài."""
    if ten == "tar":
        try:
            with tarfile.open(path) as t:
                ds = [m.name for m in t.getmembers()]
                bung = sum(m.size for m in t.getmembers())
        except tarfile.TarError as e:
            return KetQuaPhanLoai("archive", "tar", False, muc_ho_tro=KHONG,
                                  ly_do_phan_loai="tar không mở được", kich_thuoc=cỡ,
                                  ly_do_khong_doc=f"Tệp tar hỏng: {e}.",
                                  loi=corrupt_file(path.name, str(e)))
        if bung > TRAN_TONG_BYTE:
            return KetQuaPhanLoai(
                "archive", "tar", False, muc_ho_tro=KHONG, kich_thuoc=cỡ,
                ly_do_phan_loai=f"nội dung {bung / 1048576:.0f} MB vượt trần",
                ly_do_khong_doc=f"Gói giải nén ra {bung / 1048576:.0f} MB.",
                loi=over_limit(path.name, "tổng kích thước sau giải nén",
                               f"{bung / 1048576:.0f} MB",
                               f"{TRAN_TONG_BYTE / 1048576:.0f} MB"))
        return KetQuaPhanLoai("archive", "tar", True, muc_ho_tro=DAY_DU,
                              ly_do_phan_loai=f"tar đọc được ({len(ds)} mục)",
                              kich_thuoc=cỡ,
                              chi_tiet={"so_muc": len(ds), "muc": ds[:50],
                                        "cay": _cay_tep(ds, None), "bung_ra": bung,
                                        "can_chon": len(ds) > NHIEU_TEP})
    # 7z/rar cần gói ngoài; gzip đơn lẻ cần bung mới biết bên trong là gì.
    return KetQuaPhanLoai(
        "archive", ten, False, muc_ho_tro=MOT_PHAN,
        ly_do_phan_loai=f"magic bytes → {ten}", kich_thuoc=cỡ,
        ly_do_khong_doc=f"EIDE nhận ra đây là tệp nén {ten} nhưng chưa có bộ bóc cho "
                        "định dạng này.",
        de_xuat=[f"Bung {ten} ra rồi nạp thư mục", "Nén lại dạng .zip hoặc .tar"])


def _cay_tep(ten_muc: list[str], info: Any) -> list[dict[str, Any]]:
    """Cây tệp trong gói: loại đoán theo đuôi + mức hỗ trợ, để người biết nên nạp cái nào.

    Đây là ĐOÁN theo đuôi, không mở từng tệp con — nên `do_tin_cay` thấp và được nói
    thẳng ra. Bóc thật rồi phân loại từng tệp là việc của `ingest.file` khi người đã
    chọn, không phải của một cái danh sách.
    """
    co: dict[str, int] = {}
    if info:
        co = {i.filename: i.file_size for i in info}
    ra: list[dict[str, Any]] = []
    for n in ten_muc[:200]:
        if n.endswith("/"):
            continue
        d = Path(n).suffix.lower()
        loai, muc = _DOAN_THEO_DUOI.get(d, ("unknown", MOT_PHAN))
        ra.append({"duong_dan": n, "loai_doan": loai, "muc_ho_tro": muc,
                   "muc_ho_tro_vi": NHAN_MUC[muc], "kich_thuoc": co.get(n, 0),
                   "cap": len(Path(n).parts) - 1})
    return ra


_DOAN_THEO_DUOI: dict[str, tuple[str, str]] = {
    ".pdf": ("pdf", DAY_DU), ".docx": ("docx", DAY_DU), ".xlsx": ("xlsx", DAY_DU),
    ".pptx": ("pptx", MOT_PHAN), ".doc": ("office_cu", DAY_DU),
    ".xls": ("office_cu", DAY_DU), ".net": ("netlist", DAY_DU),
    ".kicad_sch": ("schematic", MOT_PHAN), ".ioc": ("vendor", DAY_DU),
    ".ld": ("vendor", DAY_DU), ".dts": ("vendor", DAY_DU),
    ".c": ("source", DAY_DU), ".h": ("source", DAY_DU), ".py": ("source", DAY_DU),
    ".sh": ("script", DAY_DU), ".csv": ("capture", DAY_DU), ".vcd": ("capture", DAY_DU),
    ".md": ("note", DAY_DU), ".html": ("html", MOT_PHAN), ".txt": ("log", DAY_DU),
    ".png": ("image", MOT_PHAN), ".jpg": ("image", MOT_PHAN),
    ".pcbdoc": ("unsupported", KHONG), ".schdoc": ("unsupported", KHONG),
}


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
