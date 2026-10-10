# -*- coding: utf-8 -*-
"""Sinh code C `BSP_LCD_*` từ `ManHinh` — bước 3 của năng lực thiết kế UI nhúng.

Đích sinh code là `BSP_LCD_*` của chính bo STM32F469I-DISCO, theo quyết định của chủ sản phẩm
ngày 10/10/2026. Lý do chọn nó thay vì LVGL: tài liệu kiến trúc của dự án ghi bo dùng
`stm32469i_discovery_lcd` + LTDC, **không** có LVGL hay TouchGFX — nên code sinh ra ở đây dịch
thử được bằng `arm-none-eabi-gcc` trên chính header BSP có trong repo, tức mỗi màn hình thiết
kế ra đều **chứng minh được là dịch được**.

## Ba chi tiết của BSP mà chỉ đọc mã nguồn mới biết, và cả ba đổi cách sinh code

Đọc `docs/stm32f469/firmware-chay-duoc/stm32469i_discovery_lcd.c`, hàm
`BSP_LCD_DisplayStringAt` (dòng 832–880):

1. **`CENTER_MODE` căn giữa theo CẢ MÀN HÌNH, không theo ô chứa chữ.** Nguyên văn dòng 848:
   `refcolumn = Xpos + ((xsize - size) * Width) / 2`, với `xsize = BSP_LCD_GetXSize() / Width`.
   Nên một nhãn căn giữa trong một ô 300 px ở `x = 20` mà sinh `CENTER_MODE` sẽ được căn giữa
   **màn hình 800 px rồi dịch thêm 20 px** — tức sai chỗ. Đó là lý do `main.c` của bo truyền
   `Xpos = 0` mỗi lần dùng `CENTER_MODE`.
2. **`RIGHT_MODE` LẤY ÂM `Xpos`.** Dòng 858: `refcolumn = -Xpos + ((xsize - size) * Width)`.
   Truyền một `Xpos` dương vào đó sẽ dịch chữ sang **trái**.
3. **`Xpos = 0` thành `Xpos = 1`.** Dòng 869: `if ((refcolumn < 1) || …) refcolumn = 1`.

Kết luận: bộ sinh code này **luôn** dùng `LEFT_MODE` và **tự tính** toạ độ x cho mọi kiểu căn
lề. Dùng `CENTER_MODE` cho tiện sẽ cho ra một màn hình lệch chỗ mà bản render HTML không hề
báo — vì HTML căn giữa đúng trong ô.

## Điều bộ sinh code này cố ý KHÔNG làm

Nó **không** sinh phần khởi tạo LCD (`BSP_LCD_Init`, `BSP_LCD_LayerDefaultInit`, bật DSI, cấp
bộ đệm khung ở SDRAM). Phần ấy phụ thuộc script liên kết và cấu hình xung nhịp của từng dự án,
và sinh ra một bản "có vẻ đúng" cho nó là cách tạo một tệp người dùng tưởng dùng được. Hàm sinh
ra ở đây chỉ **vẽ**, và nó khai rõ tiền đề trong chú thích đầu tệp.
"""
from __future__ import annotations

import re

from ..knowledge.man_hinh import HoSoManHinh
from .mo_hinh import FONT_BSP, KetQuaKiem, ManHinh, PhanTu, bo_dau, ngoai_bang_font

# `BSP_LCD_*` nhận màu `uint32_t` dạng ARGB8888 — tra từ `LCD_COLOR_WHITE  0xFFFFFFFF` và
# `LCD_COLOR_RED  0xFFFF0000` trong `stm32469i_discovery_lcd.h`, không suy từ tên.
_ALPHA_DAC = 0xFF

_RE_TEN_C = re.compile(r"[^0-9A-Za-z_]")


def ten_ham(ten_man_hinh: str) -> str:
    """Tên hàm C hợp lệ từ tên màn hình. Bắt đầu bằng chữ số thì thêm tiền tố."""
    t = _RE_TEN_C.sub("_", bo_dau(ten_man_hinh or "man_hinh")).strip("_") or "man_hinh"
    if t[0].isdigit():
        t = "mh_" + t
    return "ui_ve_" + t.lower()


def _mau_c(mau: str, mac_dinh: str = "#FFFFFF") -> str:
    m = mau if re.match(r"^#[0-9A-Fa-f]{6}$", mau or "") else mac_dinh
    return f"0x{_ALPHA_DAC:02X}{m[1:].upper()}U"


def _chuoi_c(s: str) -> str:
    """Chuỗi C. Đã qua `ngoai_bang_font` nên chỉ còn ASCII in được — chỉ cần thoát `\\` và `"`."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _x_chu(p: PhanTu, rong_chu: int) -> int:
    """Toạ độ x THẬT của dòng chữ, tự tính cho mọi kiểu căn lề.

    Phải tự tính: `CENTER_MODE` của BSP căn giữa theo cả màn hình và `RIGHT_MODE` lấy âm
    `Xpos` (xem ghi chú đầu module). Và kẹp xuống tối thiểu 1, vì BSP biến `Xpos = 0` thành 1.
    """
    if p.can_le == "center":
        x = p.x + max(0, (p.w - rong_chu)) // 2
    elif p.can_le == "right":
        x = p.x + max(0, p.w - rong_chu)
    else:
        x = p.x
    return max(1, x)


def _ve(p: PhanTu, mh: ManHinh) -> list[str]:
    """Một phần tử → các lời gọi BSP. Mỗi phần tử mở đầu bằng một chú thích mang `id` của nó."""
    d: list[str] = [f"  /* {p.id} — {p.loai} */"]
    nen_mh = _mau_c(mh.mau_nen, "#000000")

    if p.loai == "rect":
        if p.mau_nen:
            d += [f"  BSP_LCD_SetTextColor({_mau_c(p.mau_nen)});",
                  f"  BSP_LCD_FillRect({p.x}, {p.y}, {p.w}, {p.h});"]
        else:
            d += [f"  BSP_LCD_SetTextColor({_mau_c(p.mau_chu)});",
                  f"  BSP_LCD_DrawRect({p.x}, {p.y}, {p.w}, {p.h});"]

    elif p.loai == "line":
        mau = _mau_c(p.mau_nen or p.mau_chu)
        d.append(f"  BSP_LCD_SetTextColor({mau});")
        if p.h <= p.w:
            d.append(f"  BSP_LCD_DrawHLine({p.x}, {p.y}, {p.w});")
        else:
            d.append(f"  BSP_LCD_DrawVLine({p.x}, {p.y}, {p.h});")

    elif p.loai == "bar":
        gt = 0.0 if p.gia_tri is None else max(0.0, min(100.0, p.gia_tri))
        trong = int(p.w * gt / 100)
        d += [f"  BSP_LCD_SetTextColor({_mau_c(p.mau_chu)});",
              f"  BSP_LCD_DrawRect({p.x}, {p.y}, {p.w}, {p.h});"]
        if trong > 2 and p.h > 2:
            d.append(f"  BSP_LCD_FillRect({p.x + 1}, {p.y + 1}, {trong - 2}, {p.h - 2});")

    elif p.loai == "image":
        # `BSP_LCD_DrawBitmap` nhận con trỏ tới một ảnh BMP trong bộ nhớ. Tệp ấy do người dùng
        # nhúng vào dự án, nên ở đây chỉ KHAI nó `extern` — sinh ra một mảng rỗng sẽ cho một
        # tệp dịch được mà vẽ ra một khoảng đen, tức một ô xanh giả.
        bien = _RE_TEN_C.sub("_", bo_dau(p.nguon or p.id)).strip("_").lower() or p.id
        d += [f"  /* Ảnh “{p.nguon}”: khai extern — tệp BMP do dự án nhúng vào, bộ sinh code",
              "     này KHÔNG tạo dữ liệu ảnh. Thiếu nó thì LIÊN KẾT đỏ, và đỏ ở đó là đúng. */",
              f"  extern const uint8_t {bien}[];",
              f"  BSP_LCD_DrawBitmap({p.x}, {p.y}, (uint8_t *){bien});"]

    elif p.loai in ("text", "button"):
        if p.loai == "button":
            d += [f"  BSP_LCD_SetTextColor({_mau_c(p.mau_chu)});",
                  f"  BSP_LCD_DrawRect({p.x}, {p.y}, {p.w}, {p.h});"]
        if p.chu:
            f = FONT_BSP.get(p.co_chu)
            if f is None:
                return d + [f"  /* BỎ QUA: cỡ chữ {p.co_chu} không có trong BSP. */"]
            rong_chu = len(p.chu) * f[0]
            x = _x_chu(p, rong_chu)
            y = p.y + max(0, (p.h - f[1])) // 2 if p.loai == "button" else p.y
            d += [f"  BSP_LCD_SetFont(&Font{p.co_chu});",
                  f"  BSP_LCD_SetTextColor({_mau_c(p.mau_chu)});",
                  f"  BSP_LCD_SetBackColor({_mau_c(p.mau_nen) if p.mau_nen else nen_mh});",
                  # LEFT_MODE + x tự tính. Xem ghi chú đầu module: `CENTER_MODE` căn giữa theo
                  # CẢ MÀN HÌNH, nên dùng nó cho một ô con sẽ sai chỗ.
                  f'  BSP_LCD_DisplayStringAt({x}, {y}, (uint8_t *)"{_chuoi_c(p.chu)}", '
                  "LEFT_MODE);"]
    return d


def sinh_c(mh: ManHinh, hs: HoSoManHinh, *, kq: KetQuaKiem | None = None) -> str:
    """Tệp C vẽ màn hình ấy. Trả chuỗi; người gọi quyết định ghi vào đâu.

    Tệp tự khai ba thứ ở đầu: nó do mã sinh (đừng sửa tay), nó cần những gì đã chạy trước
    (`BSP_LCD_Init`…), và nó KHÔNG làm gì.
    """
    ham = ten_ham(mh.ten)
    he_mau = mh.he_mau or hs.he_mau
    d: list[str] = [
        "/* ĐỪNG SỬA TAY — tệp này do `screen.codegen` của EIDE sinh ra từ hiện vật",
        f" * `ui_screen:{mh.ten}`. Sửa ở đây sẽ bị ghi đè lần sinh sau; sửa bản thiết kế.",
        " *",
        f" * Panel: {hs.rong}×{hs.cao} px, hệ màu {he_mau}"
        + (f", driver {hs.driver}" if hs.driver else "")
        + (f", bus {hs.bus}" if hs.bus else "") + ".",
        " *",
        " * TIỀN ĐỀ — hàm này chỉ VẼ. Trước khi gọi nó, dự án phải đã chạy:",
        " *   BSP_LCD_Init();  BSP_LCD_LayerDefaultInit(0, <địa chỉ bộ đệm khung>);",
        " *   BSP_LCD_SelectLayer(0);  BSP_LCD_DisplayOn();",
        " * Bộ sinh code KHÔNG sinh phần ấy: nó phụ thuộc script liên kết và cấu hình xung",
        " * nhịp của từng dự án, nên một bản “có vẻ đúng” cho nó là một tệp người dùng tưởng",
        " * dùng được.",
    ]
    if kq is not None and kq.loi:
        d += [" *",
              f" * CẢNH BÁO: bản thiết kế này còn {len(kq.loi)} lỗi khi sinh ra tệp này:"]
        for x in kq.loi:
            d.append(f" *   {x['ma']} {x.get('phan_tu', '')}: {x['vi_sao'][:110]}")
        d.append(" * Code vẫn sinh ra để bạn đọc được nó, nhưng nó KHÔNG chạy đúng trên panel.")
    d += [" */", "", '#include "stm32469i_discovery_lcd.h"', "",
          f"void {ham}(void)", "{",
          f"  BSP_LCD_Clear({_mau_c(mh.mau_nen, '#000000')});"]

    for p in mh.phan_tu:
        if p.chu and ngoai_bang_font(p.chu):
            # Không sinh một chuỗi có ký tự ngoài bảng font: lời gọi ấy ĐỌC RA NGOÀI bảng
            # (xem `mo_hinh.ASCII_DAU`), và nó dịch sạch. Bỏ qua + nói ra ở đây, chứ không
            # âm thầm bỏ dấu hộ: bỏ dấu hộ là sửa thiết kế của người khác mà không hỏi.
            d += [f"  /* {p.id} — BỎ QUA: chữ “{p.chu}” có ký tự ngoài bảng font BSP",
                  f"     (ASCII 0x20..0x7E). Sửa bản thiết kế thành “{bo_dau(p.chu)}”",
                  "     rồi sinh lại. Sinh lời gọi ấy ra đây sẽ là một phép đọc ra ngoài",
                  "     bảng font — dịch sạch, nạp xong, màn hình hiện pixel rác. */"]
            continue
        d += _ve(p, mh)

    d += ["}", ""]
    return "\n".join(d)
