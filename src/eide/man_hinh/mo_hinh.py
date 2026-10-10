# -*- coding: utf-8 -*-
"""Mô hình một MÀN HÌNH giao diện + phép kiểm nó trên phần cứng THẬT.

Đây là hiện vật gốc của năng lực thiết kế UI: toạ độ là **pixel thật của panel**, nên HTML
render ra đúng tỉ lệ 1:1 và code C sinh ra dùng đúng con số ấy. Một nguồn, hai bản dựng.

## Bốn chỗ "trình biên dịch im lặng tuyệt đối" của riêng phần giao diện

Phần này là lý do module tồn tại. Bốn lỗi dưới đây đều **dịch sạch, nạp trót lọt, và màn hình
thật thì sai** — đúng hình dạng mà `DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md` §3.1 đã trả giá:

1. **E1101 — ra ngoài biên panel.** Màn hình cắt mất phần tràn. Không lỗi nào kêu lên, vì
   `BSP_LCD_FillRect` nhận `uint16_t` và vẽ tới đâu được thì vẽ.
2. **E1102 — chữ dài hơn ô chứa nó.** `BSP_LCD_DisplayStringAt` **không** tự ngắt dòng và
   **không** tự thu nhỏ. Đây là lỗi thiết kế UI nhúng hay gặp nhất, và nó chỉ hiện ra trên màn
   hình thật — vì bản vẽ trên máy tính dùng font co giãn được, còn BSP dùng font bitmap ĐƠN
   CÁCH. Font đơn cách là điều làm phép kiểm này thành một **phép đo** chứ không phải phỏng đoán.
3. **E1103 — cỡ chữ không có trong BSP.** `BSP_LCD_SetFont(&Font14)` là `Font14 undeclared`,
   tức một lỗi người dùng chỉ gặp sau khi đã vẽ xong cả màn hình.
4. **W1101 — hai màu khác nhau thành một màu trên panel.** Gần như mọi màu đều lệch một chút
   khi xuống RGB565, nên kêu vì "có lệch" sẽ kêu ở mọi thiết kế và mất nghĩa. Chỗ thật sự hỏng
   là khi một thiết kế hai tông thành một tông — chữ biến mất vào nền, không lỗi nào ở bất kỳ
   bước nào.

## Mã lỗi: họ E11xx, cảnh báo W11xx

Bản đầu dùng `E9001`–`E9006` và suýt đi qua: dải ấy **đã bị chiếm** bởi sáu bất biến của cây
phân cấp (`knowledge/cay.py` ghi rõ *"bất biến cây là E9001–E9006"*). Trùng mã lỗi là lỗi im
lặng khó chịu riêng — hai chỗ cùng in `E9001`, người đọc log đi tra sai chỗ.

## Con số nào tra, con số nào tính, con số nào là KHUYẾN NGHỊ

* `FONT_BSP` — **tra** từ `docs/stm32f469/firmware-chay-duoc/font{8,12,16,20,24}.c` trong repo,
  trường `Width`/`Height` của `sFONT`. Không nhớ lại.
* bề rộng một dòng chữ — **tính** từ `FONT_BSP` (font đơn cách).
* `MM_VUNG_CHAM` — **khuyến nghị nhân trắc**, không phải hằng số phần cứng. Lời cảnh báo tự
  khai điều đó, vì trộn hai loại nguồn là cách một khuyến nghị trông như một phép đo (N1).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from ..knowledge.man_hinh import HoSoManHinh, bit_moi_diem

# Năm font của BSP STM32 — TRA từ bảng font thật trong repo, không nhớ.
# Nguồn: `docs/stm32f469/firmware-chay-duoc/font{8,12,16,20,24}.c`, trường `Width`/`Height`
# của `sFONT`. Dạng: {cỡ (= chiều cao): (bề rộng một ký tự, chiều cao)}.
FONT_BSP: dict[int, tuple[int, int]] = {
    8: (5, 8), 12: (7, 12), 16: (11, 16), 20: (14, 20), 24: (17, 24),
}
CO_CHU_MAC_DINH = 16

# Phạm vi ký tự của bảng font BSP — ĐO từ chính mã trong repo, không nhớ lại:
#   · `font{8,12,16,20,24}.c`: số byte bảng ÷ (Height × ((Width+7)/8)) = đúng **95** ký tự;
#   · `stm32469i_discovery_lcd.c:817` tra `table[(Ascii - ' ') * …]` và **không kiểm biên**.
#
# Nên một ký tự ngoài 0x20..0x7E KHÔNG phải "mất dấu" — nó là một phép ĐỌC RA NGOÀI BẢNG. `'ộ'`
# (UTF-8 bắt đầu bằng 0xE1) cho chỉ số 0xE1-0x20 = 193, và 193 × 72 = 13 896 byte vào một bảng
# dài 6 840 byte: đọc hơn 7 KB quá bảng. Mã vẫn dịch, vẫn nạp, màn hình hiện pixel rác.
#
# Bằng chứng thứ hai, từ firmware ĐANG CHẠY trên bo: `main.c` viết `"Hoc vien: Vu Tri Cong"`.
ASCII_DAU, ASCII_CUOI = 0x20, 0x7E

# Bảng bỏ dấu tiếng Việt. Dùng `unicodedata` (NFD rồi lọc dấu kết hợp) chứ không gõ bảng tay —
# một bảng gõ tay sẽ thiếu đúng chữ không ai nghĩ tới. `đ`/`Đ` phải khai riêng: chúng KHÔNG
# phải `d` + dấu kết hợp trong Unicode, nên NFD không tách chúng ra.
_RIENG = {"đ": "d", "Đ": "D", "ð": "d"}

LOAI_PHAN_TU = ("text", "rect", "line", "image", "bar", "button")
CAN_LE = ("left", "center", "right")

# Vùng chạm tối thiểu, tính bằng **milimet**. Đây là một KHUYẾN NGHỊ NHÂN TRẮC, không phải một
# hằng số của phần cứng: nguồn là hướng dẫn thiết kế cảm ứng (Microsoft nêu 9 mm; Apple HIG nêu
# 44 pt ≈ 7 mm trên màn hình của họ). Để ở một hằng số có tên để ai không đồng ý thì đổi được,
# và lời cảnh báo TỰ KHAI rằng nó là hướng dẫn — trộn nó với số đo phần cứng là cách một khuyến
# nghị trông như một phép đo.
MM_VUNG_CHAM = 9.0
MM_MOI_INCH = 25.4

_RE_MAU = re.compile(r"^#[0-9A-Fa-f]{6}$")


def bo_dau(chu: str) -> str:
    """Bỏ dấu tiếng Việt, GIỮ ĐÚNG số ký tự.

    Giữ đúng số ký tự là điều kiện để lời khuyên kèm được một bề rộng đúng: bề rộng một dòng
    chữ trên BSP là `số ký tự × Width`, nên một phép bỏ dấu tách `ê` thành hai ký tự sẽ cho một
    bề rộng sai, và người dùng sửa xong vẫn bị cắt chữ.
    """
    import unicodedata

    ra = []
    for c in chu or "":
        if c in _RIENG:
            ra.append(_RIENG[c])
            continue
        tach = unicodedata.normalize("NFD", c)
        goc = "".join(x for x in tach if not unicodedata.combining(x))
        ra.append(goc or c)
    return "".join(ra)


def ngoai_bang_font(chu: str) -> list[str]:
    """Những ký tự của chuỗi KHÔNG có trong bảng font BSP, giữ thứ tự, không trùng."""
    ra: list[str] = []
    for c in chu or "":
        if not (ASCII_DAU <= ord(c) <= ASCII_CUOI) and c not in ra:
            ra.append(c)
    return ra


def be_rong_chu(chu: str, co_chu: int) -> int | None:
    """Bề rộng một dòng chữ, tính bằng pixel. `None` khi cỡ chữ không có trong BSP.

    Tính được chính xác vì font của BSP là font **bitmap đơn cách** — mỗi ký tự chiếm đúng
    `Width` pixel. Đó là lý do phép kiểm "chữ có bị cắt không" ở đây là một phép đo.
    """
    f = FONT_BSP.get(co_chu)
    return None if f is None else len(chu) * f[0]


def co_chu_vua(chu: str, rong: int, cao: int) -> int | None:
    """Cỡ chữ LỚN NHẤT của BSP mà dòng chữ ấy còn vừa ô `rong × cao`. `None` nếu không cỡ nào vừa."""
    for co in sorted(FONT_BSP, reverse=True):
        w, h = FONT_BSP[co]
        if len(chu) * w <= rong and h <= cao:
            return co
    return None


def _tach_mau(mau: str) -> tuple[int, int, int] | None:
    if not _RE_MAU.match(mau or ""):
        return None
    return int(mau[1:3], 16), int(mau[3:5], 16), int(mau[5:7], 16)


# Số bit mỗi kênh của các hệ màu có mất mát. Chỉ khai những hệ LTDC nhận và THẬT SỰ cắt bit —
# `ARGB8888`/`RGB888` giữ đủ 8 bit nên không có mặt ở đây.
_BIT_KENH: dict[str, tuple[int, int, int]] = {
    "RGB565": (5, 6, 5), "BGR565": (5, 6, 5),
    "ARGB1555": (5, 5, 5), "ARGB4444": (4, 4, 4),
}


def luong_hoa(mau: str, he_mau: str) -> str:
    """Màu mà PANEL sẽ hiện ra, sau khi hệ màu cắt bit.

    Phép mở rộng ngược là phép phần cứng dùng thật — `r5 << 3 | r5 >> 2`, tức lặp lại các bit
    cao để lấp chỗ trống. **Không** phải nhân tỉ lệ `r5 * 255 / 31`: hai cách cho hai con số
    khác nhau, và con số đúng là con số LTDC/DMA2D dùng.

    Hệ màu lạ hoặc không mất mát thì trả nguyên màu — không đoán.
    """
    rgb = _tach_mau(mau)
    bit = _BIT_KENH.get((he_mau or "").upper())
    if rgb is None or bit is None:
        return mau
    ra = []
    for v, n in zip(rgb, bit):
        giu = 8 - n
        x = v >> giu
        ra.append((x << giu) | (x >> (n - giu)) if n > giu else (x << giu))
    return "#%02X%02X%02X" % tuple(ra)


@dataclass(slots=True)
class PhanTu:
    """Một phần tử của màn hình. Toạ độ là **pixel thật của panel**, không phải phần trăm."""

    id: str
    loai: str
    x: int
    y: int
    w: int
    h: int
    chu: str = ""
    co_chu: int = CO_CHU_MAC_DINH
    mau_chu: str = "#FFFFFF"
    mau_nen: str = ""                  # rỗng = trong suốt / không tô
    can_le: str = "left"
    gia_tri: float | None = None       # cho `bar`: 0..100
    nguon: str = ""                    # cho `image`: tên tệp bitmap

    @classmethod
    def tu_dict(cls, d: dict[str, Any]) -> "PhanTu":
        """Chịu được trường THIẾU — hiện vật cũ trong kho người dùng không ai sửa lại (DEV-359)."""
        return cls(
            id=str(d.get("id") or ""), loai=str(d.get("loai") or ""),
            x=int(d.get("x") or 0), y=int(d.get("y") or 0),
            w=int(d.get("w") or 0), h=int(d.get("h") or 0),
            chu=str(d.get("chu") or ""),
            co_chu=int(d.get("co_chu") or CO_CHU_MAC_DINH),
            mau_chu=str(d.get("mau_chu") or "#FFFFFF"),
            mau_nen=str(d.get("mau_nen") or ""),
            can_le=str(d.get("can_le") or "left"),
            gia_tri=None if d.get("gia_tri") is None else float(d["gia_tri"]),
            nguon=str(d.get("nguon") or ""))


@dataclass(slots=True)
class ManHinh:
    ten: str
    rong: int
    cao: int
    he_mau: str = ""
    mau_nen: str = "#000000"
    phan_tu: list[PhanTu] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.ten, "rong": self.rong, "cao": self.cao, "he_mau": self.he_mau,
                "mau_nen": self.mau_nen, "phan_tu": [asdict(p) for p in self.phan_tu]}

    @classmethod
    def tu_dict(cls, d: dict[str, Any]) -> "ManHinh":
        return cls(ten=str(d.get("ten") or ""), rong=int(d.get("rong") or 0),
                   cao=int(d.get("cao") or 0), he_mau=str(d.get("he_mau") or ""),
                   mau_nen=str(d.get("mau_nen") or "#000000"),
                   phan_tu=[PhanTu.tu_dict(x) for x in (d.get("phan_tu") or [])])


@dataclass(slots=True)
class KetQuaKiem:
    loi: list[dict[str, Any]] = field(default_factory=list)
    canh_bao: list[dict[str, Any]] = field(default_factory=list)
    chua_kiem: list[dict[str, Any]] = field(default_factory=list)

    @property
    def hop_le(self) -> bool:
        return not self.loi


def _loi(ma: str, phan_tu: str, vi_sao: str, cach_sua: str) -> dict[str, Any]:
    return {"ma": ma, "phan_tu": phan_tu, "vi_sao": vi_sao, "cach_sua": cach_sua}


# Những gì phép kiểm này KHÔNG chạm tới. Danh sách này đi vào bản render, vì một dòng "không
# thấy lỗi nào" không kèm phạm vi sẽ được đọc thành "thiết kế đúng hết" (N6, và bài học
# DEV-362 nguyên văn).
NGOAI_PHAM_VI = (
    "màn hình thật sáng tới đâu, nhìn ngoài trời có đọc được không",
    "tốc độ vẽ lại: thiết kế này có kịp 60 Hz hay không",
    "bố cục có hợp lý với người dùng hay không — đó là việc của người, không của mã",
)


def kiem(mh: ManHinh, hs: HoSoManHinh) -> KetQuaKiem:
    """Bản thiết kế này có chạy được trên **màn hình thật ấy** không.

    Thứ tự cố ý: hồ sơ trước, rồi mô hình ↔ hồ sơ, rồi từng phần tử. Hồ sơ không hợp lệ thì
    không có khung nào để kiểm biên, nên dừng ngay — kiểm tiếp sẽ cho ra một danh sách lỗi
    dựng trên một độ phân giải không có.
    """
    kq = KetQuaKiem()

    if not hs.hop_le:
        kq.loi.append(_loi(
            "E1107", "",
            "Chưa có hồ sơ màn hình hợp lệ: " + (hs.vi_sao_khong_hop_le or "thiếu dữ kiện")
            + " Không có độ phân giải thì không có khung nào để kiểm biên, nên phép kiểm này "
              "KHÔNG chạy — và “không có lỗi” ở đây sẽ là một ô xanh giả.",
            "Gọi `display.profile` trên một tài liệu có nói độ phân giải và hệ màu của panel."))
        return kq

    if (mh.rong, mh.cao) != (hs.rong, hs.cao):
        kq.loi.append(_loi(
            "E1106", "",
            f"Bản thiết kế khai panel {mh.rong}×{mh.cao}, nhưng màn hình thật là "
            f"{hs.rong}×{hs.cao} theo hồ sơ. Mọi toạ độ trong bản thiết kế vì thế đang nói về "
            "một màn hình khác.",
            f"Đặt `rong={hs.rong}`, `cao={hs.cao}` rồi xếp lại các phần tử."))

    if mh.he_mau and hs.he_mau and mh.he_mau.upper() != hs.he_mau.upper():
        hop = [hs.he_mau, *hs.he_mau_khac]
        if mh.he_mau.upper() not in [x.upper() for x in hop]:
            kq.loi.append(_loi(
                "E1106", "",
                f"Bản thiết kế khai hệ màu `{mh.he_mau}`, mà panel nhận {', '.join(hop)}.",
                f"Đổi `he_mau` thành `{hs.he_mau}`."))

    he_mau = mh.he_mau or hs.he_mau
    nguong_cham = None
    if hs.dpi:
        nguong_cham = int(MM_VUNG_CHAM / MM_MOI_INCH * hs.dpi)
    else:
        kq.chua_kiem.append({
            "ma": "W1102", "vi_sao":
            "Chưa kiểm được vùng chạm có đủ to cho ngón tay: hồ sơ không có DPI (thiếu kích "
            "thước vật lý của panel), nên không quy được milimet sang pixel. Đây là CHƯA ĐỦ "
            "DỮ KIỆN, không phải “đạt”."})
    if hs.cam_ung is None:
        kq.chua_kiem.append({
            "ma": "E1105", "vi_sao":
            "Chưa kiểm được các nút có bấm được không: tài liệu không nói panel có cảm ứng "
            "hay không. “Không nói” khác “không có cảm ứng”."})

    ten_thay: set[str] = set()
    for p in mh.phan_tu:
        if p.id in ten_thay:
            kq.loi.append(_loi("E1107", p.id,
                               f"Hai phần tử cùng mã `{p.id}`.",
                               "Đặt mã khác nhau — mã là thứ bản render và code C tra theo."))
        ten_thay.add(p.id)

        if p.loai not in LOAI_PHAN_TU:
            kq.loi.append(_loi(
                "E1107", p.id,
                f"Loại phần tử `{p.loai}` không có trong bộ widget.",
                "Dùng một trong: " + ", ".join(f"`{x}`" for x in LOAI_PHAN_TU)))
            continue

        # --- E1101 biên panel. `x + w == rong` là VỪA KHÍT: pixel cuối của panel 800 px là 799.
        if p.x < 0 or p.y < 0 or p.x + p.w > mh.rong or p.y + p.h > mh.cao:
            kq.loi.append(_loi(
                "E1101", p.id,
                f"`{p.id}` chiếm x {p.x}..{p.x + p.w}, y {p.y}..{p.y + p.h}, ra ngoài panel "
                f"{mh.rong}×{mh.cao}. Màn hình thật sẽ CẮT phần tràn và không lỗi nào kêu lên.",
                f"Giữ `x + w ≤ {mh.rong}` và `y + h ≤ {mh.cao}`, toạ độ không âm."))

        if p.loai in ("text", "button") and p.chu:
            la = ngoai_bang_font(p.chu)
            if la:
                f0 = FONT_BSP.get(p.co_chu) or FONT_BSP[CO_CHU_MAC_DINH]
                moi_kt = f0[1] * ((f0[0] + 7) // 8)
                xa = max(ord(c) for c in la) - ASCII_DAU
                kq.loi.append(_loi(
                    "E1108", p.id,
                    f"Chữ của `{p.id}` có ký tự KHÔNG nằm trong bảng font của BSP: "
                    + " ".join(f"“{c}”" for c in la[:8])
                    + (f" …+{len(la) - 8}" if len(la) > 8 else "")
                    + ". Năm bảng font của bo chỉ có 95 ký tự ASCII 0x20..0x7E (đo từ "
                      "`font*.c` trong repo), và `BSP_LCD_DisplayChar` tra "
                      "`table[(Ascii - ' ') * …]` mà KHÔNG kiểm biên — nên ký tự này cho chỉ "
                      f"số tới {xa}, tức đọc tới ~{xa * moi_kt:,} byte trong một bảng dài "
                      f"{95 * moi_kt:,} byte.".replace(",", " ")
                    + " Đây KHÔNG phải “mất dấu”: nó là một phép đọc ra ngoài bảng, và màn "
                      "hình sẽ hiện pixel rác. Mã vẫn dịch và vẫn nạp.",
                    f"Dùng chữ không dấu: “{bo_dau(p.chu)}”. (Firmware đang chạy trên bo cũng "
                    "viết không dấu — xem `main.c`.) Muốn có dấu thì phải sinh thêm bảng font, "
                    "và đó là một việc khác."))
            f = FONT_BSP.get(p.co_chu)
            if f is None:
                gan = min(FONT_BSP, key=lambda c: abs(c - p.co_chu))
                kq.loi.append(_loi(
                    "E1103", p.id,
                    f"Cỡ chữ {p.co_chu} không có trong thư viện BSP của bo. BSP chỉ có "
                    + ", ".join(f"Font{c}" for c in sorted(FONT_BSP))
                    + f"; `BSP_LCD_SetFont(&Font{p.co_chu})` sẽ là một lỗi DỊCH, tức một lỗi "
                      "chỉ hiện ra sau khi đã vẽ xong cả màn hình.",
                    f"Dùng cỡ {gan} (gần nhất có thật)."))
            else:
                rong_chu, cao_chu = len(p.chu) * f[0], f[1]
                if rong_chu > p.w or cao_chu > p.h:
                    vua = co_chu_vua(p.chu, p.w, p.h)
                    kq.loi.append(_loi(
                        "E1102", p.id,
                        f"Chữ “{p.chu}” ở Font{p.co_chu} chiếm {rong_chu}×{cao_chu} px, không "
                        f"vừa ô {p.w}×{p.h} px. `BSP_LCD_DisplayStringAt` KHÔNG tự ngắt dòng "
                        "và KHÔNG tự thu nhỏ — nó vẽ tràn ra ngoài ô.",
                        (f"Dùng cỡ chữ {vua} (vừa ô này), hoặc nới ô ra "
                         f"{rong_chu}×{cao_chu} px."
                         if vua else
                         f"Không cỡ chữ nào của BSP vừa ô {p.w}×{p.h} với {len(p.chu)} ký tự — "
                         f"nới ô hoặc rút chữ ngắn lại.")))

        if p.loai == "button" and hs.cam_ung is False:
            kq.loi.append(_loi(
                "E1105", p.id,
                f"`{p.id}` là một nút, mà hồ sơ nói panel này KHÔNG có cảm ứng — nên không ai "
                "bấm được nó.",
                "Bỏ nút đi, hoặc nhận lệnh qua phím cứng / UART và vẽ nó bằng `rect` + `text`."))

        if (p.loai == "button" and nguong_cham and hs.cam_ung
                and (p.w < nguong_cham or p.h < nguong_cham)):
            kq.canh_bao.append({
                "ma": "W1102", "phan_tu": p.id,
                "vi_sao": (f"Nút `{p.id}` {p.w}×{p.h} px nhỏ hơn {nguong_cham} px — tức nhỏ "
                           f"hơn {MM_VUNG_CHAM:g} mm ở {hs.dpi:.0f} DPI. Đây là một **hướng "
                           "dẫn** thiết kế cảm ứng (nhân trắc ngón tay), KHÔNG phải một số đo "
                           "của phần cứng: nó là khuyến nghị, không phải phép đo."),
                "cach_sua": f"Nới nút lên ít nhất {nguong_cham}×{nguong_cham} px."})

        if p.loai == "bar" and p.gia_tri is not None and not (0 <= p.gia_tri <= 100):
            kq.loi.append(_loi("E1107", p.id,
                               f"Thanh tiến trình `{p.id}` có giá trị {p.gia_tri}, ngoài 0..100.",
                               "Đặt `gia_tri` trong khoảng 0..100."))

        for ten_mau, mau in (("mau_chu", p.mau_chu), ("mau_nen", p.mau_nen)):
            if mau and not _RE_MAU.match(mau):
                kq.loi.append(_loi("E1107", p.id,
                                   f"`{ten_mau}` của `{p.id}` là “{mau}”, không phải mã màu "
                                   "dạng `#RRGGBB`.",
                                   "Viết màu dạng `#RRGGBB`."))

        # --- E1104 chữ TRÙNG màu nền SAU lượng hoá. Phải so sau lượng hoá: hai màu khác nhau
        # trong thiết kế có thể trùng nhau trên panel RGB565, và lúc ấy chữ vô hình.
        nen = p.mau_nen or mh.mau_nen
        if p.loai in ("text", "button") and p.chu and _RE_MAU.match(p.mau_chu or "") \
                and _RE_MAU.match(nen or ""):
            if luong_hoa(p.mau_chu, he_mau) == luong_hoa(nen, he_mau):
                kq.loi.append(_loi(
                    "E1104", p.id,
                    f"Chữ của `{p.id}` và nền của nó cùng ra màu "
                    f"`{luong_hoa(p.mau_chu, he_mau)}` trên panel {he_mau} — chữ sẽ KHÔNG hiện."
                    + (f" (Thiết kế gõ `{p.mau_chu}` và `{nen}`: hai màu khác nhau, nhưng hệ "
                       f"màu {he_mau} cắt bit nên chúng trùng nhau.)"
                       if p.mau_chu.upper() != nen.upper() else ""),
                    "Đổi một trong hai màu sao cho SAU lượng hoá chúng còn khác nhau."))

    # --- W1101 hai màu KHÁC NHAU trong thiết kế thành MỘT màu trên panel.
    if bit_moi_diem(he_mau) is not None and (he_mau or "").upper() in _BIT_KENH:
        theo_mau: dict[str, list[tuple[str, str]]] = {}
        for p in mh.phan_tu:
            for mau in (p.mau_chu, p.mau_nen):
                if _RE_MAU.match(mau or ""):
                    theo_mau.setdefault(luong_hoa(mau, he_mau), []).append((p.id, mau.upper()))
        for sau, ds in theo_mau.items():
            goc = sorted({m for _, m in ds})
            if len(goc) > 1:
                ten = sorted({i for i, _ in ds})
                kq.canh_bao.append({
                    "ma": "W1101", "phan_tu": ", ".join(ten),
                    "vi_sao": (f"{len(goc)} màu khác nhau trong thiết kế ({', '.join(goc)}) "
                               f"đều thành `{sau}` trên panel {he_mau}. Các phần tử liên quan: "
                               f"{', '.join(ten)}. Một thiết kế nhiều tông sẽ thành một tông, "
                               "và không có lỗi nào ở bất kỳ bước nào."),
                    "cach_sua": (f"Giãn các màu ấy ra xa nhau hơn, hoặc đổi panel sang hệ màu "
                                 "giữ đủ 8 bit mỗi kênh (`RGB888`/`ARGB8888`).")})
    return kq
