# -*- coding: utf-8 -*-
"""Ảnh → mảng C để firmware vẽ thẳng lên khung hình.

Một con chip không có trình đọc PNG. Muốn hiện một logo lên màn thì ảnh phải nằm trong Flash
dưới dạng mảng pixel đã giải nén, đúng định dạng mà bộ điều khiển màn hình đọc được. Đây là
bước mà người làm nhúng vẫn phải chạy tay bằng một công cụ rời; không có nó thì tác tử chỉ còn
hai đường — bịa ra một mảng, hoặc bảo người dùng tự đi làm.

Ba điều cố ý:

1. **Tính trước kích thước, từ chối trước khi vẽ.** Một ảnh 800×480 ở ARGB8888 là 1,5 MB —
   vừa Flash 2 MB của chip này, nhưng 1600×1200 thì không. Báo con số ra *trước*, kèm Flash
   còn lại, thay vì để trình liên kết báo `region FLASH overflowed` sau mười phút.
2. **Giữ tỉ lệ khi thu nhỏ.** Ép ảnh vào khung sai tỉ lệ thì logo méo, mà méo là thứ người ta
   nhìn thấy ngay và nghĩ là mình làm hỏng.
3. **Nói rõ đã mất gì.** RGB565 bỏ bớt bit màu và **bỏ hẳn kênh trong suốt**; một logo có nền
   trong suốt sẽ thành nền đen nếu không ai nói trước.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Định dạng → (byte mỗi điểm ảnh, mô tả, kiểu C)
DINH_DANG: dict[str, tuple[int, str, str]] = {
    "rgb565": (2, "16 bit: 5 đỏ · 6 lục · 5 lam, KHÔNG có kênh trong suốt", "uint16_t"),
    "argb8888": (4, "32 bit: 8 trong suốt · 8 đỏ · 8 lục · 8 lam", "uint32_t"),
    "rgb888": (3, "24 bit: 8 đỏ · 8 lục · 8 lam, không trong suốt", "uint8_t"),
}

TRAN_BYTE_RA = 4 * 1024 * 1024


@dataclass(slots=True)
class KetQuaAnh:
    dat: bool = False
    ten_bien: str = ""
    dinh_dang: str = ""
    rong: int = 0
    cao: int = 0
    rong_goc: int = 0
    cao_goc: int = 0
    so_byte: int = 0
    tep_c: str = ""
    tep_h: str = ""
    vi_sao_khong_dat: str = ""
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "ten_bien": self.ten_bien, "dinh_dang": self.dinh_dang,
                "rong": self.rong, "cao": self.cao,
                "rong_goc": self.rong_goc, "cao_goc": self.cao_goc,
                "so_byte": self.so_byte, "tep_c": self.tep_c, "tep_h": self.tep_h,
                "vi_sao_khong_dat": self.vi_sao_khong_dat, "canh_bao": list(self.canh_bao)}


def _sang_565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def doi_anh(anh: Path, ra_thu_muc: Path, *, ten_bien: str, dinh_dang: str = "rgb565",
            rong_toi_da: int = 0, cao_toi_da: int = 0,
            flash_con_lai: int = 0) -> KetQuaAnh:
    """Đổi một tệp ảnh thành cặp `.c`/`.h` chứa mảng điểm ảnh."""
    import re

    kq = KetQuaAnh(dinh_dang=dinh_dang)
    xin = (ten_bien or "").strip()
    ten_bien = re.sub(r"[^A-Za-z0-9_]", "_", xin).strip("_")
    if not ten_bien or ten_bien[0].isdigit():
        kq.vi_sao_khong_dat = (
            f"“{xin}” không dùng được làm tên biến C (phải bắt đầu bằng chữ hoặc `_`).")
        return kq
    if ten_bien != xin:
        # Làm sạch thì được, nhưng đổi tên mà không nói thì tác tử sẽ `#include` một tên
        # khác với tên nó vừa đặt, rồi đọc lỗi "undeclared identifier" mà không hiểu vì sao.
        kq.canh_bao.append(f"Tên biến “{xin}” có ký tự không hợp lệ trong C — đã đổi thành "
                           f"“{ten_bien}”. Dùng đúng tên này trong mã.")
    kq.ten_bien = ten_bien
    if dinh_dang not in DINH_DANG:
        kq.vi_sao_khong_dat = (f"Chưa biết định dạng “{dinh_dang}”. "
                               f"Đang có: {', '.join(DINH_DANG)}.")
        return kq
    if not anh.exists():
        kq.vi_sao_khong_dat = f"Không có tệp ảnh {anh.name}."
        return kq

    try:
        from PIL import Image
    except ImportError:
        kq.vi_sao_khong_dat = ("Máy chưa có thư viện Pillow để đọc ảnh. "
                               "Cài: `pip install pillow`.")
        return kq

    try:
        im = Image.open(anh)
        im.load()
    except Exception as e:                                    # noqa: BLE001
        kq.vi_sao_khong_dat = f"Không đọc được ảnh: {type(e).__name__}: {str(e)[:150]}"
        return kq

    kq.rong_goc, kq.cao_goc = im.size
    co_trong_suot = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
    im = im.convert("RGBA")

    # Thu nhỏ GIỮ TỈ LỆ. Ép vào khung sai tỉ lệ thì logo méo, và méo là thứ nhìn thấy ngay.
    if rong_toi_da or cao_toi_da:
        rx = (rong_toi_da / im.width) if rong_toi_da else 1.0
        ry = (cao_toi_da / im.height) if cao_toi_da else 1.0
        ty_le = min(x for x in (rx, ry, 1.0) if x > 0)
        if ty_le < 1.0:
            im = im.resize((max(1, round(im.width * ty_le)),
                            max(1, round(im.height * ty_le))), Image.LANCZOS)
    kq.rong, kq.cao = im.size

    moi_diem = DINH_DANG[dinh_dang][0]
    kq.so_byte = kq.rong * kq.cao * moi_diem
    if kq.so_byte > TRAN_BYTE_RA:
        kq.vi_sao_khong_dat = (
            f"Mảng sẽ nặng {kq.so_byte / 1e6:.2f} MB ({kq.rong}×{kq.cao}×{moi_diem} B), vượt "
            f"trần {TRAN_BYTE_RA / 1e6:.0f} MB. Thu nhỏ ảnh lại (đặt rong_toi_da/cao_toi_da).")
        return kq
    if flash_con_lai and kq.so_byte > flash_con_lai:
        # Nói TRƯỚC, thay vì để trình liên kết báo `region FLASH overflowed` sau mười phút.
        kq.vi_sao_khong_dat = (
            f"Mảng nặng {kq.so_byte / 1024:.0f} KB nhưng Flash chỉ còn {flash_con_lai / 1024:.0f} "
            "KB. Thu nhỏ ảnh, hoặc đổi sang rgb565 nếu đang dùng argb8888.")
        return kq

    if co_trong_suot and dinh_dang != "argb8888":
        kq.canh_bao.append(
            f"Ảnh gốc CÓ kênh trong suốt nhưng {dinh_dang} không giữ được — phần trong suốt "
            "sẽ thành màu nền đã trộn sẵn (đen). Muốn giữ thì dùng argb8888.")
    if (kq.rong, kq.cao) != (kq.rong_goc, kq.cao_goc):
        kq.canh_bao.append(
            f"Đã thu nhỏ {kq.rong_goc}×{kq.cao_goc} → {kq.rong}×{kq.cao} (giữ tỉ lệ).")

    px = im.load()
    gt: list[str] = []
    for y in range(kq.cao):
        for x in range(kq.rong):
            r, g, b, a = px[x, y]
            if dinh_dang == "rgb565":
                gt.append(f"0x{_sang_565(r, g, b):04X}")
            elif dinh_dang == "argb8888":
                gt.append(f"0x{(a << 24) | (r << 16) | (g << 8) | b:08X}")
            else:
                gt += [f"0x{r:02X}", f"0x{g:02X}", f"0x{b:02X}"]

    moi_dong = {"rgb565": 12, "argb8888": 8, "rgb888": 12}[dinh_dang]
    kieu = DINH_DANG[dinh_dang][2]
    than = "\n".join("    " + ", ".join(gt[i:i + moi_dong]) + ","
                     for i in range(0, len(gt), moi_dong))

    ra_thu_muc.mkdir(parents=True, exist_ok=True)
    tep_c = ra_thu_muc / f"{ten_bien}.c"
    tep_h = ra_thu_muc / f"{ten_bien}.h"
    dau = (f"/* Sinh tự động từ {anh.name} ({kq.rong_goc}×{kq.cao_goc}) — KHÔNG sửa tay.\n"
           f" * Định dạng: {dinh_dang} — {DINH_DANG[dinh_dang][1]}\n"
           f" * Kích thước dùng: {kq.rong}×{kq.cao}, {kq.so_byte} byte trong Flash.\n"
           + "".join(f" * Lưu ý: {c}\n" for c in kq.canh_bao)
           + " */\n")
    tep_c.write_text(
        f"{dau}#include \"{ten_bien}.h\"\n\n"
        f"const {kieu} {ten_bien}_data[{len(gt)}] = {{\n{than}\n}};\n", "utf-8")
    tep_h.write_text(
        f"{dau}#ifndef {ten_bien.upper()}_H\n#define {ten_bien.upper()}_H\n\n"
        "#include <stdint.h>\n\n"
        f"#define {ten_bien.upper()}_WIDTH   {kq.rong}\n"
        f"#define {ten_bien.upper()}_HEIGHT  {kq.cao}\n"
        f"#define {ten_bien.upper()}_BPP     {moi_diem}\n\n"
        f"extern const {kieu} {ten_bien}_data[{len(gt)}];\n\n"
        f"#endif /* {ten_bien.upper()}_H */\n", "utf-8")
    kq.tep_c, kq.tep_h = tep_c.name, tep_h.name
    kq.dat = True
    return kq
