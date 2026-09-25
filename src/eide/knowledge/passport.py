# -*- coding: utf-8 -*-
"""Hộ chiếu chip và kho ISA — EIDE-MDD-40 §C2, §C3 bước 6.

Hộ chiếu là `ns.part@semver` — không phải một cái tên trần. Lý do nằm ở [DEV-183]:

    "KHÔNG tự ghim tên chip trần vào ns.part@semver (lỗi 'câu trả lời sai tệ hơn ô
     trống'). Ghim chỉ sau khi có tài liệu."

Ghép `ATmega328P` thành một hộ chiếu rồi tra ra rỗng trong im lặng còn tệ hơn nói thẳng
"chưa ghim chip nào". Nên `pin()` ở đây **từ chối** khi chưa có tài liệu nào cho chip đó.

Phần thứ hai là kho ISA. TC018 phát hiện một khoảng trống thật của sản phẩm: kho chỉ có
`armv7e-m` (Cortex-M4/M7 có FPU+DSP), `avr8`, `rv32imac` — **thiếu `armv7-m`**, tức
thiếu đúng Cortex-M3 của STM32F103, một trong những chip phổ biến nhất. Chọn `armv7e-m`
cho M3 sẽ sinh mã mang lệnh chip không chạy được. Kho dưới đây bổ sung nó.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- kho ISA
@dataclass(slots=True)
class ISA:
    ma: str
    ten: str
    loi: str
    toolchain: str
    co_fpu: bool = False
    ghi_chu: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ma": self.ma, "ten": self.ten, "loi": self.loi,
                "toolchain": self.toolchain, "co_fpu": self.co_fpu,
                "ghi_chu": self.ghi_chu}


ISA_MANIFEST: dict[str, ISA] = {
    "armv6-m": ISA("armv6-m", "ARMv6-M", "Cortex-M0/M0+/M1", "arm-none-eabi-gcc",
                   ghi_chu="Tập lệnh Thumb rút gọn; không có chia phần cứng."),
    "armv7-m": ISA("armv7-m", "ARMv7-M", "Cortex-M3", "arm-none-eabi-gcc",
                   ghi_chu="STM32F1, LPC17xx. KHÔNG có FPU và KHÔNG có lệnh DSP — "
                           "biên dịch bằng armv7e-m sẽ sinh lệnh chip không chạy được."),
    "armv7e-m": ISA("armv7e-m", "ARMv7E-M", "Cortex-M4/M7", "arm-none-eabi-gcc",
                    co_fpu=True, ghi_chu="Có DSP; FPU tuỳ biến thể."),
    "armv8-m": ISA("armv8-m", "ARMv8-M", "Cortex-M23/M33", "arm-none-eabi-gcc",
                   co_fpu=True, ghi_chu="Có TrustZone-M ở một số biến thể."),
    "avr8": ISA("avr8", "AVR 8-bit", "ATmega/ATtiny", "avr-gcc",
                ghi_chu="Harvard 8-bit; bộ nhớ chương trình tách khỏi dữ liệu."),
    "rv32imac": ISA("rv32imac", "RISC-V RV32IMAC", "ESP32-C3, CH32V",
                    "riscv-none-elf-gcc"),
    "xtensa-lx6": ISA("xtensa-lx6", "Xtensa LX6", "ESP32", "xtensa-esp32-elf-gcc"),
    "xtensa-lx7": ISA("xtensa-lx7", "Xtensa LX7", "ESP32-S3", "xtensa-esp32s3-elf-gcc"),
    "aarch64": ISA("aarch64", "ARM 64-bit", "Raspberry Pi Zero 2 W, Pi 3/4/5",
                   "aarch64-linux-gnu-gcc",
                   ghi_chu="Chạy Linux — phần mềm là tiến trình, không phải firmware."),
    "armv6": ISA("armv6", "ARM11", "Raspberry Pi Zero / Zero W", "arm-linux-gnueabihf-gcc",
                 ghi_chu="Chạy Linux."),
}

# Họ chip → ISA. Dùng để NÓI ĐƯỢC ISA ngay cả khi chưa có datasheet — nhưng kết quả
# mang tầng ĐỒNG cho tới khi hộ chiếu được ghim.
HO_CHIP: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"^ATmega|^ATtiny|^AT90", re.I), "avr8", "mchp"),
    (re.compile(r"^STM32[FLGWH]0", re.I), "armv6-m", "st"),
    (re.compile(r"^STM32[FL]1", re.I), "armv7-m", "st"),
    (re.compile(r"^STM32[FLGH][2347]", re.I), "armv7e-m", "st"),
    (re.compile(r"^STM32[LU]5|^STM32H5", re.I), "armv8-m", "st"),
    (re.compile(r"^ESP32-C", re.I), "rv32imac", "esp"),
    (re.compile(r"^ESP32-S3", re.I), "xtensa-lx7", "esp"),
    (re.compile(r"^ESP32(?!-)", re.I), "xtensa-lx6", "esp"),
    (re.compile(r"^ESP8266", re.I), "xtensa-lx6", "esp"),
    (re.compile(r"^nRF52", re.I), "armv7e-m", "nordic"),
    (re.compile(r"^nRF51", re.I), "armv6-m", "nordic"),
    (re.compile(r"^RP2040", re.I), "armv6-m", "rpi"),
    (re.compile(r"^RP2350", re.I), "armv8-m", "rpi"),
    (re.compile(r"Zero\s*2\s*W|Pi\s*[345]", re.I), "aarch64", "rpi"),
    (re.compile(r"Pi\s*Zero(?!\s*2)", re.I), "armv6", "rpi"),
    (re.compile(r"^CH32V", re.I), "rv32imac", "wch"),
    (re.compile(r"^GD32F1", re.I), "armv7-m", "gd"),
    (re.compile(r"^GD32F[347]", re.I), "armv7e-m", "gd"),
]


def doan_isa(ten_chip: str) -> tuple[str | None, str]:
    """Suy ISA từ tên chip. Trả `(mã ISA hoặc None, namespace)`.

    Đây là **tri thức chung**, tầng ĐỒNG. Nó đủ để nói "STM32F103 là Cortex-M3, cần
    armv7-m" mà không cần datasheet — nhưng không đủ để ghim hộ chiếu.
    """
    t = ten_chip.strip()
    for mau, isa, ns in HO_CHIP:
        if mau.search(t):
            return isa, ns
    return None, "unknown"


# --------------------------------------------------------------------------- hộ chiếu
@dataclass(slots=True)
class HoChieu:
    ma: str                       # ns.part@semver
    ten_chip: str
    isa: str | None
    tai_lieu: list[str] = field(default_factory=list)
    so_fact: dict[str, int] = field(default_factory=dict)
    bi_danh: list[str] = field(default_factory=list)

    def to_canonical(self) -> dict[str, Any]:
        isa = ISA_MANIFEST.get(self.isa or "")
        return {
            "id": self.ma, "chip": self.ten_chip, "isa": self.isa,
            "isa_ten": isa.ten if isa else None,
            "isa_co_trong_kho": isa is not None,
            "toolchain": isa.toolchain if isa else None,
            "tai_lieu": self.tai_lieu, "so_fact": self.so_fact,
            "bi_danh": self.bi_danh,
        }


def ma_ho_chieu(ten_chip: str, *, ns: str = "", phien_ban: str = "1.0.0") -> str:
    """`ATmega328P` → `mchp.atmega328p@1.0.0`."""
    if not ns:
        _, ns = doan_isa(ten_chip)
    part = re.sub(r"[^a-z0-9]+", "", ten_chip.lower())
    return f"{ns}.{part}@{phien_ban}"


def kiem_truoc_khi_ghim(ten_chip: str, *, so_tai_lieu: int) -> str | None:
    """Trả lý do KHÔNG được ghim, hoặc None nếu ghim được (§C3 bước 6, DEV-183)."""
    if so_tai_lieu <= 0:
        return (f"Chưa có tài liệu nào cho {ten_chip}. Ghim một cái tên trần vào hộ "
                f"chiếu sẽ tạo ra một hiện vật tra đâu cũng rỗng — câu trả lời sai tệ "
                f"hơn một ô trống. Nạp datasheet trước, hoặc để tôi đi tìm rồi anh duyệt.")
    return None


def bao_cao_isa(ten_chip: str) -> dict[str, Any]:
    """Nói thật về ISA: có trong kho hay không, và nếu không thì hệ quả là gì (TC018)."""
    isa, ns = doan_isa(ten_chip)
    if isa is None:
        return {"chip": ten_chip, "isa": None, "co_trong_kho": False,
                "message_vi": f"Tôi không suy được kiến trúc lệnh của {ten_chip} từ tên. "
                              "Cho tôi biết lõi của nó (ví dụ Cortex-M3, AVR 8-bit), "
                              "hoặc nạp datasheet."}
    m = ISA_MANIFEST.get(isa)
    if m is None:
        return {"chip": ten_chip, "isa": isa, "co_trong_kho": False,
                "message_vi": f"{ten_chip} dùng {isa}, nhưng kho của EIDE chưa có "
                              f"manifest cho kiến trúc đó. Tôi KHÔNG chọn một kiến trúc "
                              f"gần giống thay thế — làm vậy sẽ sinh mã mang lệnh chip "
                              f"không chạy được."}
    return {"chip": ten_chip, "isa": isa, "co_trong_kho": True,
            "toolchain": m.toolchain, "co_fpu": m.co_fpu, "ghi_chu": m.ghi_chu,
            "message_vi": f"{ten_chip} là {m.loi} ({m.ten}), biên dịch bằng "
                          f"{m.toolchain}." + (f" {m.ghi_chu}" if m.ghi_chu else "")}
