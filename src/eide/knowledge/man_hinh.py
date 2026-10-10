# -*- coding: utf-8 -*-
"""Hồ sơ MÀN HÌNH đọc từ tài liệu — nền của năng lực thiết kế UI nhúng.

Vì sao module này phải có TRƯỚC phần thiết kế: `grep` cả kho ngày 10/10/2026 không ra **một**
Fact nào về màn hình. `KHOA_CHUAN` trong `docs.py` không có khoá `lcd.*` nào; `HoChieu` của
linh kiện cũng không có trường nào cho màn hình. Nên nếu làm phần thiết kế trước, tác tử sẽ
**tự nhớ ra** `800×480` — và dự án này đã trả giá ba lần cho đúng chuyện ấy (ba hằng số phần
cứng tự nhớ đã tự chế ra ba bằng chứng sai).

Một bản thiết kế UI vẽ đẹp trên một độ phân giải SAI thì **mọi toạ độ trong nó đều sai**, màn
hình thật cắt mất một phần, và không lỗi nào kêu lên. Đó là ca "trình biên dịch im lặng tuyệt
đối" của riêng phần giao diện.

Ba điều module này cố ý KHÔNG làm:

* **Không điền mặc định.** Thiếu trường nào thì tên trường ấy vào `thieu`, và `cam_ung` là
  `None` chứ không phải `False` — *"panel không có cảm ứng"* và *"tài liệu không nói"* là hai
  điều khác nhau, gộp lại là cách một bản thiết kế có nút bấm được duyệt cho một màn hình
  không ai bấm được.
* **Không đoán số bit mỗi điểm ảnh.** Định dạng lạ thì trả `None`, vì con số ấy đi vào phép
  tính bộ đệm khung và một con số sai ở đó cho ra kết luận sai về RAM.
* **Không kết luận khi chưa biết RAM.** `kiem_dem_khung` trả `None` thay vì `False` — một
  cảnh báo sai làm người dùng đi sửa thứ không hỏng (N2).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# Khoá Fact của màn hình. Đặt tiền tố `lcd.` chứ không `display.` vì `thu_nguyen_cua` trong
# `docs.py` tra theo tiền tố, và `lcd` là tiền tố không trùng khoá nào đang có.
KHOA_MAN_HINH: dict[str, str] = {
    "lcd.width": "Độ phân giải ngang (pixel)",
    "lcd.height": "Độ phân giải dọc (pixel)",
    "lcd.format": "Hệ màu của bộ đệm khung",
    "lcd.inch": "Đường chéo vật lý (inch)",
    "lcd.dpi": "Mật độ điểm ảnh — TÍNH ra từ hai khoá trên, không đọc được",
    "lcd.driver": "Chip điều khiển panel",
    "lcd.bus": "Bus nối panel với vi điều khiển",
    "lcd.touch": "Panel có cảm ứng hay không",
    "lcd.cols": "Số cột ký tự (màn hình ký tự)",
    "lcd.rows": "Số dòng ký tự (màn hình ký tự)",
}

# Số bit mỗi điểm ảnh — TRA BẢNG, không tính từ tên. Danh sách lấy theo các định dạng mà
# LTDC/DMA2D của STM32 nhận (`BSP_LCD_*`), vì đó là đích sinh code đã chốt.
BIT_MOI_DIEM: dict[str, int] = {
    "ARGB8888": 32, "RGBA8888": 32, "XRGB8888": 32,
    "RGB888": 24, "BGR888": 24,
    "RGB565": 16, "BGR565": 16, "ARGB1555": 16, "ARGB4444": 16, "AL88": 16,
    "L8": 8, "AL44": 8,
    "L4": 4,
}

# Một panel ĐỒ HOẠ: hai chiều đều ít nhất 64 px. Dưới ngưỡng ấy thì cặp số gần như luôn là
# một thứ khác — số cột × số dòng của màn hình ký tự (`16x2`), số pin, số kênh.
PX_TOI_THIEU = 64
PX_TOI_DA = 7680

# Màn hình KÝ TỰ (HD44780 và họ hàng): cột trong 8..40, dòng trong 1..4. Đây là ca sai đắt
# nhất của phép đọc này và nó có thật — HD44780 là màn hình phổ biến nhất trong dạy học nhúng,
# và đọc `16x2` thành độ phân giải sẽ cho một bản vẽ 16×2 pixel, tức một bản vẽ trống.
_COT_KY_TU = (8, 40)
_DONG_KY_TU = (1, 4)

_RE_CAP = re.compile(r"(?<![\w.])(\d{1,5})\s*[x×*]\s*(\d{1,5})(?![\w.])", re.I)

# Đơn vị đứng ngay sau cặp số thì cặp số ấy KHÔNG phải độ phân giải: `60 x 40 mm` là kích
# thước bo. Đo được trên tài liệu thật của repo, nên cửa này không phải đề phòng suông.
_RE_DON_VI_SAU = re.compile(r"\s*(mm|cm|m|inch|in|\"|mil|µm|um)\b", re.I)
# Và từ đứng NGAY TRƯỚC: `2x AA`, `stack 4x1024`, `DSI 2-lane`.
_RE_NHAN_SAU = re.compile(r"\s*(lane|lanes|bit|bits|byte|bytes|word|words|AA|AAA|"
                          r"pin|pins|ch|channel|channels|UART|SPI|I2C|USB)\b", re.I)

_RE_HE_MAU = re.compile("|".join(sorted(BIT_MOI_DIEM, key=len, reverse=True)), re.I)

# Chip điều khiển panel hay gặp. Danh sách này KHÔNG phải để nhận ra mọi driver — nó để nhận ra
# driver trong tài liệu của chính các bo dự án dùng. Không có trong danh sách thì `driver` rỗng
# và `lcd.driver` vào `thieu`, chứ không đoán.
_RE_DRIVER = re.compile(
    r"\b(OTM8009A|NT35510|ILI9341|ILI9488|ILI9881C|ST7789|ST7735|ST7796|SSD1306|SSD1963|"
    r"R61581|HX8357|RA8875|GC9A01|SH1106|FT5336|FT6236)\b", re.I)

_RE_BUS = re.compile(
    r"\b(MIPI[- ]?DSI|DSI|LTDC|RGB666|RGB565\s+parallel|parallel\s+RGB|SPI|QSPI|I2C|"
    r"FSMC|FMC|8080|6800)\b", re.I)

_RE_INCH = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:inch|in\b|\")", re.I)

_RE_CAM_UNG = re.compile(r"\b(c[aả]m\s*[uứ]ng|touch(?:screen)?|capacitive|resistive|"
                         r"FT5336|FT6236|multi-?touch)\b", re.I)
_RE_KHONG_CAM_UNG = re.compile(r"\bkh[oô]ng\s+c[aả]m\s*[uứ]ng\b|\bno\s+touch\b", re.I)

_RE_KY_TU = re.compile(r"\b(k[yý]\s*t[uự]|character|char\s*lcd|HD44780|PCF8574|text\s*lcd)\b",
                       re.I)

# Dòng có nói về MÀN HÌNH hay không. Đây là cửa quan trọng nhất của module, và nó có từ một
# phép đo chứ không từ đề phòng suông: trên `tai-lieu-kien-truc-c4.md` của repo, khớp
# `ARGB8888` **đầu tiên** nằm ở dòng nói về *ảnh logo trong firmware*
# (`Dữ liệu hình ảnh logo_ptit (ARGB8888…)`) — định dạng của một tấm **bitmap**, không phải
# định dạng bộ đệm khung của **panel**. Dòng đúng nằm sau:
# `FrameBuffer đồ hoạ LCD 800x480 (ARGB8888 / RGB565)`.
#
# Hai dòng ấy cho CÙNG một giá trị, nên bản đầu "đúng đáp án mà sai bằng chứng" — ca tệ nhất,
# vì nó không có biểu hiện nào để ai phát hiện. Nếu tấm bitmap là `RGB565` mà panel là
# `ARGB8888` thì hồ sơ sai, và mọi phép tính bộ đệm khung sai theo.
#
# Nhóm từ thứ hai (`hệ màu`, `pixel format`, `độ phân giải`…) có vì cửa chỉ-xét-một-dòng quá
# chặt cho cách tài liệu thật viết: chủ đề nằm ở tiêu đề mục, còn giá trị nằm ở một dòng riêng
# bên dưới (`Hệ màu ARGB8888`). Những từ ấy TỰ NÓ là từ về màn hình, nên nhận chúng không nới
# cửa ra cho dòng `logo_ptit` — dòng đó gọi tên một TẤM ẢNH, không gọi tên một trường cấu hình.
_RE_VE_MAN_HINH = re.compile(
    r"\b(LCD|TFT|OLED|panel|m[aà]n\s*h[iì]nh|display|hi[eể]n\s*th[iị]|screen|"
    r"framebuffer|frame\s*buffer|b[oộ]\s*[dđ][eệ]m\s*khung|LTDC|DSI|DPI|"
    r"h[eệ]\s*m[aà]u|[dđ][iị]nh\s*d[aạ]ng\s*m[aà]u|pixel\s*format|color\s*format|"
    r"[dđ][oộ]\s*ph[aâ]n\s*gi[aả]i|resolution|bits?\s*per\s*pixel|bpp)\b", re.I)


def _khop_ve_man_hinh(chu: str, mau: re.Pattern[str]) -> re.Match[str] | None:
    """Khớp ĐẦU TIÊN mà **dòng chứa nó** cũng nói về màn hình.

    Thà thiếu một trường và nói ra, hơn là điền một trường bằng một bằng chứng không đứng
    được — hồ sơ này là thứ mọi toạ độ của bản thiết kế dựa vào (N1).
    """
    for m in mau.finditer(chu or ""):
        if _RE_VE_MAN_HINH.search(_dong_chua(chu, m.start())):
            return m
    return None


def _dong_chua(chu: str, vi_tri: int) -> str:
    """Dòng NGUYÊN VĂN chứa vị trí ấy — đây là trích dẫn của một trường hồ sơ.

    Phải là nguyên văn: một câu tôi soạn lại không phân biệt được với một câu tôi tự nghĩ ra,
    và cả năng lực thiết kế UI đứng trên hồ sơ này (N1).
    """
    dau = chu.rfind("\n", 0, vi_tri) + 1
    cuoi = chu.find("\n", vi_tri)
    return chu[dau:cuoi if cuoi >= 0 else len(chu)].strip()


def _cap_hop_le(chu: str, m: re.Match[str]) -> bool:
    """Cặp số này có thể là một kích thước màn hình không — hai cửa, cả hai cần."""
    sau = chu[m.end():m.end() + 12]
    if _RE_DON_VI_SAU.match(sau) or _RE_NHAN_SAU.match(sau):
        return False
    return True


def doc_do_phan_giai(chu: str) -> list[tuple[int, int]]:
    """Mọi cặp `rộng × cao` là độ phân giải ĐỒ HOẠ trong đoạn chữ, giữ thứ tự gặp.

    Hai cửa, và cả hai đo được từ tài liệu thật: cặp số không được có **đơn vị hay nhãn đứng
    ngay sau** (`60 x 40 mm` là kích thước bo, `DSI 2-lane` là số lane), và cả hai chiều phải
    từ `PX_TOI_THIEU` px trở lên (dưới ngưỡng ấy gần như luôn là màn hình ký tự).
    """
    ra: list[tuple[int, int]] = []
    for m in _RE_CAP.finditer(chu or ""):
        if not _cap_hop_le(chu, m):
            continue
        a, b = int(m.group(1)), int(m.group(2))
        if not (PX_TOI_THIEU <= a <= PX_TOI_DA and PX_TOI_THIEU <= b <= PX_TOI_DA):
            continue
        if (a, b) not in ra:
            ra.append((a, b))
    return ra


def doc_man_hinh_ky_tu(chu: str) -> list[tuple[int, int]]:
    """Cặp `cột × dòng` của một màn hình KÝ TỰ (`16x2`, `20x4`)."""
    ra: list[tuple[int, int]] = []
    for m in _RE_CAP.finditer(chu or ""):
        if not _cap_hop_le(chu, m):
            continue
        c, d = int(m.group(1)), int(m.group(2))
        if not (_COT_KY_TU[0] <= c <= _COT_KY_TU[1] and _DONG_KY_TU[0] <= d <= _DONG_KY_TU[1]):
            continue
        if (c, d) not in ra:
            ra.append((c, d))
    return ra


def doc_he_mau(chu: str) -> list[str]:
    """Hệ màu tài liệu khai, giữ thứ tự gặp và viết HOA chuẩn."""
    ra: list[str] = []
    for m in _RE_HE_MAU.finditer(chu or ""):
        t = m.group(0).upper()
        if t not in ra:
            ra.append(t)
    return ra


def bit_moi_diem(he_mau: str) -> int | None:
    """Số bit mỗi điểm ảnh. Định dạng lạ → `None`, **không đoán**.

    Con số này đi vào phép tính bộ đệm khung, và một con số sai ở đó cho ra một kết luận sai về
    RAM — đúng loại kết luận mà không trình biên dịch nào bác lại.
    """
    return BIT_MOI_DIEM.get((he_mau or "").strip().upper())


def kich_thuoc_dem(rong: int, cao: int, he_mau: str) -> int | None:
    """Số byte một bộ đệm khung. `None` khi chưa biết số bit mỗi điểm ảnh."""
    bit = bit_moi_diem(he_mau)
    if bit is None or rong <= 0 or cao <= 0:
        return None
    return rong * cao * bit // 8


def kiem_dem_khung(rong: int, cao: int, he_mau: str, *,
                   ram_noi_byte: int | None = None,
                   ram_ngoai_byte: int | None = None,
                   so_dem: int = 1) -> dict:
    """Bộ đệm khung có vừa RAM không — và nói RÕ khi chưa biết RAM.

    Vì sao phép kiểm này đáng có: `800×480 ARGB8888` cần **1 536 000 byte**, còn SRAM nội của
    STM32F469I-DISCO là **324 KB** theo tài liệu kiến trúc của chính dự án. Nó không vừa, và
    nếu không ai kêu lên thì hoặc linker đổ ở một dòng không ai đọc, hoặc nó **lọt** (bộ đệm
    rơi vào SDRAM ngoài theo script liên kết) rồi màn hình nhiễu — không báo lỗi.

    `None` chứ không `False` khi chưa biết RAM: `False` sẽ bị đọc thành *"không vừa"*, và một
    cảnh báo sai làm người dùng đi sửa thứ không hỏng (N2).
    """
    can = kich_thuoc_dem(rong, cao, he_mau)
    if can is None:
        return {"can_byte": None, "vua_ram_noi": None, "vua_ram_ngoai": None,
                "note_vi": (f"Chưa biết số bit mỗi điểm ảnh của hệ màu “{he_mau}”, nên **chưa "
                            "biết** bộ đệm khung cần bao nhiêu byte. Khai hệ màu mà LTDC nhận "
                            f"({', '.join(sorted(BIT_MOI_DIEM))}).")}
    can *= max(1, so_dem)
    vua_noi = None if ram_noi_byte is None else can <= ram_noi_byte
    vua_ngoai = None if ram_ngoai_byte is None else can <= ram_ngoai_byte

    kb = can / 1024
    phan = [f"Bộ đệm khung {rong}×{cao} {he_mau}"
            + (f" × {so_dem} bộ" if so_dem > 1 else "")
            + f" cần **{can:,} byte** ({kb:,.1f} KB).".replace(",", " ")]
    if vua_noi is None and vua_ngoai is None:
        phan.append("Chưa biết dung lượng RAM của bo, nên **chưa kết luận** được nó có vừa "
                    "không — nạp Fact `ram.size` rồi gọi lại.")
    elif vua_noi:
        phan.append("Vừa RAM nội.")
    else:
        if ram_noi_byte is not None:
            phan.append(f"**KHÔNG vừa RAM nội** ({ram_noi_byte:,} byte)."
                        .replace(",", " "))
        if vua_ngoai:
            phan.append("Vừa RAM ngoài — nên bộ đệm phải nằm ở **SDRAM ngoài**, và script "
                        "liên kết phải đặt nó ở đó. Đặt ở RAM nội thì linker đổ, mà đặt sai "
                        "vùng thì màn hình nhiễu **không báo lỗi**.")
        elif vua_ngoai is False:
            phan.append("**KHÔNG vừa cả RAM ngoài** — thiết kế này không chạy được trên bo "
                        "ấy; giảm hệ màu hoặc dùng một bộ đệm một phần (partial framebuffer).")
    return {"can_byte": can, "vua_ram_noi": vua_noi, "vua_ram_ngoai": vua_ngoai,
            "note_vi": " ".join(phan)}


@dataclass(slots=True)
class HoSoManHinh:
    """Cấu hình màn hình THẬT, mỗi trường kèm trích dẫn nguyên văn.

    `hop_le` là cửa mà phần thiết kế dựa vào: nó chỉ chạy khi hồ sơ hợp lệ. Trả về một hồ sơ
    `rong=0` trông như hồ sơ thật sẽ làm mọi phép kiểm biên sau đó vô nghĩa.
    """

    rong: int = 0
    cao: int = 0
    he_mau: str = ""
    inch: float | None = None
    dpi: float | None = None
    dpi_la_tinh_ra: bool = False
    driver: str = ""
    bus: str = ""
    cam_ung: bool | None = None
    loai: str = "do_hoa"                     # do_hoa | ky_tu
    cot: int = 0
    dong: int = 0
    he_mau_khac: list[str] = field(default_factory=list)
    nguon: dict[str, str] = field(default_factory=dict)
    thieu: list[str] = field(default_factory=list)
    vi_sao_khong_hop_le: str = ""

    @property
    def hop_le(self) -> bool:
        return self.loai == "do_hoa" and self.rong > 0 and self.cao > 0 and bool(self.he_mau)


def ho_so_tu_chu(chu: str) -> HoSoManHinh:
    """Đọc hồ sơ màn hình từ đoạn chữ của một tài liệu.

    Khi tài liệu khai **nhiều** độ phân giải (một datasheet họ chip liệt kê cả dòng sản phẩm),
    lấy cặp ĐẦU TIÊN và giữ cả danh sách trong `nguon` — không tự chọn cặp "hợp lý nhất", vì
    chọn hộ ở đây là đoán hộ, và một độ phân giải sai làm mọi toạ độ sai.
    """
    chu = chu or ""
    hs = HoSoManHinh()

    # --- màn hình ký tự: nhận ra TRƯỚC, vì `16x2` cũng là một cặp số
    ky_tu = _RE_KY_TU.search(chu)
    cap_ky_tu = doc_man_hinh_ky_tu(chu)
    do_phan_giai = doc_do_phan_giai(chu)
    if ky_tu and cap_ky_tu and not do_phan_giai:
        hs.loai = "ky_tu"
        hs.cot, hs.dong = cap_ky_tu[0]
        hs.nguon["lcd.cols"] = _dong_chua(chu, chu.find(f"{hs.cot}") if hs.cot else 0)
        hs.nguon["lcd.rows"] = hs.nguon["lcd.cols"]
        hs.vi_sao_khong_hop_le = (
            f"Đây là màn hình **ký tự** {hs.cot}×{hs.dong} (cột × dòng), không phải panel đồ "
            "hoạ. Phần thiết kế UI theo pixel chưa làm cho loại màn hình này — vẽ một bản "
            f"thiết kế trong khung {hs.cot}×{hs.dong} pixel sẽ cho ra một bản vẽ trống.")
        hs.thieu = [k for k in ("lcd.width", "lcd.height", "lcd.format") ]
        return hs

    for m in _RE_CAP.finditer(chu):
        if not (_cap_hop_le(chu, m) and (int(m.group(1)), int(m.group(2))) in do_phan_giai):
            continue
        dong = _dong_chua(chu, m.start())
        if not _RE_VE_MAN_HINH.search(dong):
            continue
        hs.nguon["lcd.width"] = hs.nguon["lcd.height"] = dong
        hs.rong, hs.cao = int(m.group(1)), int(m.group(2))
        break

    # Hệ màu LẤY TỪ DÒNG NÓI VỀ MÀN HÌNH, không lấy khớp đầu tiên trong tài liệu — xem ghi
    # chú ở `_RE_VE_MAN_HINH`. Và lấy mọi hệ màu trên CHÍNH dòng ấy, vì tài liệu hay viết
    # `ARGB8888 / RGB565` nghĩa là panel nhận cả hai.
    m = _khop_ve_man_hinh(chu, _RE_HE_MAU)
    if m:
        dong = _dong_chua(chu, m.start())
        he = doc_he_mau(dong)
        hs.he_mau, hs.he_mau_khac = he[0], he[1:]
        hs.nguon["lcd.format"] = dong

    m = _khop_ve_man_hinh(chu, _RE_INCH)
    if m:
        try:
            hs.inch = float(m.group(1).replace(",", "."))
            hs.nguon["lcd.inch"] = _dong_chua(chu, m.start())
        except ValueError:
            hs.inch = None

    m = _khop_ve_man_hinh(chu, _RE_DRIVER)
    if m:
        hs.driver = m.group(1)
        hs.nguon["lcd.driver"] = _dong_chua(chu, m.start())

    m = _khop_ve_man_hinh(chu, _RE_BUS)
    if m:
        hs.bus = m.group(1)
        hs.nguon["lcd.bus"] = _dong_chua(chu, m.start())

    m = _khop_ve_man_hinh(chu, _RE_KHONG_CAM_UNG)
    if m:
        hs.cam_ung = False
        hs.nguon["lcd.touch"] = _dong_chua(chu, m.start())
    else:
        m = _khop_ve_man_hinh(chu, _RE_CAM_UNG)
        if m:
            hs.cam_ung = True
            hs.nguon["lcd.touch"] = _dong_chua(chu, m.start())

    # DPI là số TÍNH RA, và nó tự khai là tính ra: một Fact đọc được từ tài liệu và một số
    # suy ra từ hai Fact có độ tin cậy khác nhau, và N1 đòi biết cái nào là cái nào.
    if hs.rong and hs.cao and hs.inch:
        hs.dpi = math.hypot(hs.rong, hs.cao) / hs.inch
        hs.dpi_la_tinh_ra = True

    hs.thieu = [k for k, co in (
        ("lcd.width", hs.rong > 0), ("lcd.height", hs.cao > 0),
        ("lcd.format", bool(hs.he_mau)), ("lcd.inch", hs.inch is not None),
        ("lcd.dpi", hs.dpi is not None), ("lcd.driver", bool(hs.driver)),
        ("lcd.bus", bool(hs.bus)), ("lcd.touch", hs.cam_ung is not None),
    ) if not co]

    if not hs.hop_le:
        can = [k for k in ("lcd.width", "lcd.height", "lcd.format") if k in hs.thieu]
        hs.vi_sao_khong_hop_le = (
            "Chưa đủ để vẽ: tài liệu không nói " + ", ".join(f"`{k}`" for k in can)
            + ". Phần thiết kế UI cần đủ ba thứ ấy, vì toạ độ của bản thiết kế là **pixel thật "
              "của panel** — thiếu độ phân giải thì không có khung nào để kiểm biên.")
    return hs
