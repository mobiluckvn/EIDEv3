# -*- coding: utf-8 -*-
"""Tìm chuỗi công cụ và biên dịch firmware. Không có trình biên dịch thì NÓI RA.

Ba điều tệp này cố ý làm:

1. **Không cài gì.** Nó tìm thứ đã có trên máy (`arduino-cli`, `avr-gcc`) và nếu không thấy
   thì trả về một lời từ chối có chỉ dẫn. Cài đặt là việc của người dùng qua cổng G-TOOL —
   cùng kỷ luật với quyết định "máy này không cài KiCad".

2. **Đọc lỗi của trình biên dịch, không đoán.** Mỗi lỗi thành một bản ghi có tệp, dòng, cột
   và nguyên văn thông điệp, để tác tử sửa đúng chỗ thay vì đọc lại cả tệp.

3. **Kích thước lấy từ `avr-size`.** Tài liệu bàn giao đặt hạn mức bằng byte (32.768 B Flash,
   2.048 B SRAM); một con số ước lượng ở đây sẽ được đem đi so với hạn mức thật và cho ra
   một kết luận sai về việc firmware có vừa chip hay không.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Bảng ISA → cách biên dịch. Mở rộng bằng cách thêm dòng, không bằng cách thêm nhánh `if`.
CHUOI_CONG_CU = {
    "avr8": {"arduino_fqbn": "arduino:avr:nano:cpu=atmega328old",
             "gcc": "avr-gcc", "size": "avr-size", "mcu": "atmega328p"},
}

# Thư mục con của một gói Arduino, dùng khi `avr-gcc` không nằm trong PATH.
_ARDUINO15 = Path.home() / "Library/Arduino15/packages/arduino/tools/avr-gcc"


@dataclass(slots=True)
class LoiBienDich:
    tep: str
    dong: int
    cot: int
    muc: str                  # error | warning | note
    thong_diep: str

    def to_dict(self) -> dict[str, Any]:
        return {"tep": self.tep, "dong": self.dong, "cot": self.cot,
                "muc": self.muc, "thong_diep": self.thong_diep}

    @property
    def vi(self) -> str:
        return f"{self.tep}:{self.dong}:{self.cot} {self.muc}: {self.thong_diep}"


@dataclass(slots=True)
class KetQuaBienDich:
    dat: bool = False
    cong_cu: str = ""             # "arduino-cli" | "avr-gcc"
    lenh: list[str] = field(default_factory=list)
    loi: list[LoiBienDich] = field(default_factory=list)
    canh_bao: list[LoiBienDich] = field(default_factory=list)
    tep_ra: str = ""
    flash: int = 0
    sram: int = 0
    flash_toi_da: int = 0
    sram_toi_da: int = 0
    nguyen_van: str = ""          # đuôi đầu ra thật, để người đọc kiểm được
    vi_sao_khong_dat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "cong_cu": self.cong_cu, "lenh": list(self.lenh),
                "so_loi": len(self.loi), "so_canh_bao": len(self.canh_bao),
                "loi": [x.to_dict() for x in self.loi[:40]],
                "canh_bao": [x.to_dict() for x in self.canh_bao[:20]],
                "tep_ra": self.tep_ra, "flash": self.flash, "sram": self.sram,
                "flash_toi_da": self.flash_toi_da, "sram_toi_da": self.sram_toi_da,
                "ty_le_flash": (round(self.flash / self.flash_toi_da, 3)
                                if self.flash_toi_da else None),
                "ty_le_sram": (round(self.sram / self.sram_toi_da, 3)
                               if self.sram_toi_da else None),
                "vi_sao_khong_dat": self.vi_sao_khong_dat,
                "nguyen_van": self.nguyen_van[-3000:]}


_MAU_LOI = re.compile(
    r"^(?P<tep>[^\s:][^:]*):(?P<dong>\d+):(?P<cot>\d+):\s*"
    r"(?P<muc>error|warning|note|lỗi):\s*(?P<td>.*)$")


def phan_tich_loi(dau_ra: str, *, goc: Path | None = None) -> list[LoiBienDich]:
    """Tách thông điệp trình biên dịch thành bản ghi có toạ độ."""
    ra: list[LoiBienDich] = []
    for d in dau_ra.splitlines():
        m = _MAU_LOI.match(d.strip())
        if not m:
            continue
        tep = m.group("tep")
        if goc is not None:
            try:
                tep = str(Path(tep).resolve().relative_to(goc.resolve()))
            except ValueError:
                pass
        ra.append(LoiBienDich(tep=tep, dong=int(m.group("dong")),
                              cot=int(m.group("cot")),
                              muc=("error" if m.group("muc") == "lỗi" else m.group("muc")),
                              thong_diep=m.group("td").strip()))
    return ra


def _tim_lenh(ten: str) -> str:
    """Tìm trong PATH, rồi trong gói Arduino đã cài. Trả "" nếu không có."""
    p = shutil.which(ten)
    if p:
        return p
    if _ARDUINO15.is_dir():
        for thu_muc in sorted(_ARDUINO15.iterdir(), reverse=True):
            ung = thu_muc / "bin" / ten
            if ung.exists():
                return str(ung)
    return ""


def tim_chuoi_cong_cu(isa: str) -> dict[str, str]:
    """Những gì MÁY NÀY thật sự có cho một kiến trúc. Khoá thiếu nghĩa là không có."""
    cau_hinh = CHUOI_CONG_CU.get(isa or "", {})
    if not cau_hinh:
        return {}
    ra = {"isa": isa, "fqbn": cau_hinh.get("arduino_fqbn", ""),
          "mcu": cau_hinh.get("mcu", "")}
    for ten in ("arduino-cli", cau_hinh.get("gcc", ""), cau_hinh.get("size", "")):
        if ten:
            duong = _tim_lenh(ten)
            if duong:
                ra[ten] = duong
    return ra


def _doc_kich_thuoc(size_bin: str, elf: Path) -> tuple[int, int]:
    """`avr-size -C` → (flash, sram). Không đọc được thì (0, 0) — và bên gọi phải nói ra."""
    if not size_bin or not elf.exists():
        return 0, 0
    r = subprocess.run([size_bin, "-C", str(elf)], capture_output=True, text=True)
    flash = sram = 0
    for d in r.stdout.splitlines():
        m = re.search(r"Program:\s+(\d+)\s+bytes", d)
        if m:
            flash = int(m.group(1))
        m = re.search(r"Data:\s+(\d+)\s+bytes", d)
        if m:
            sram = int(m.group(1))
    return flash, sram


def bien_dich(*, goc: Path, sketch: Path, isa: str = "avr8",
              flash_toi_da: int = 0, sram_toi_da: int = 0,
              thu_muc_build: Path | None = None) -> KetQuaBienDich:
    """Biên dịch `sketch` (một thư mục sketch Arduino hoặc một tệp .ino/.c).

    Trả về kết quả ĐÃ ĐỌC từ trình biên dịch. `dat=True` chỉ khi tiến trình trả 0 **và** có
    tệp ảnh nhị phân trên đĩa: một trình biên dịch trả 0 mà không sinh ra tệp nào là một
    trường hợp đã gặp thật (đường dẫn sai), và nếu tin vào mã trả về thì ta báo "biên dịch
    xong" cho một firmware không tồn tại.
    """
    kq = KetQuaBienDich(flash_toi_da=flash_toi_da, sram_toi_da=sram_toi_da)
    cc = tim_chuoi_cong_cu(isa)
    if not cc:
        kq.vi_sao_khong_dat = (f"Chưa biết biên dịch cho kiến trúc “{isa}”. "
                               f"Đang hỗ trợ: {', '.join(CHUOI_CONG_CU)}.")
        return kq

    build = thu_muc_build or (goc / ".eide" / "build")
    build.mkdir(parents=True, exist_ok=True)

    if cc.get("arduino-cli") and cc.get("fqbn"):
        kq.cong_cu = "arduino-cli"
        kq.lenh = [cc["arduino-cli"], "compile", "--fqbn", cc["fqbn"],
                   "--build-path", str(build), "--warnings", "all", str(sketch)]
    elif cc.get("avr-gcc"):
        kq.cong_cu = "avr-gcc"
        nguon = ([str(x) for x in sorted(sketch.glob("*.c"))] if sketch.is_dir()
                 else [str(sketch)])
        kq.lenh = [cc["avr-gcc"], f"-mmcu={cc.get('mcu', 'atmega328p')}", "-Os",
                   "-DF_CPU=16000000UL", "-std=gnu11", "-Wall", "-Wextra",
                   "-o", str(build / "mach.elf"), *nguon]
    else:
        kq.vi_sao_khong_dat = (
            "Máy này chưa có trình biên dịch cho AVR. Cần `arduino-cli` (kèm nhân "
            "arduino:avr) hoặc `avr-gcc` trong PATH. EIDE không tự cài — đó là việc của "
            "người dùng, qua cổng G-TOOL.")
        return kq

    r = subprocess.run(kq.lenh, capture_output=True, text=True, cwd=str(goc),
                       env={**os.environ, "LC_ALL": "C"})
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    kq.nguyen_van = out.strip()
    ds = phan_tich_loi(out, goc=goc)
    kq.loi = [x for x in ds if x.muc == "error"]
    kq.canh_bao = [x for x in ds if x.muc == "warning"]

    elf = next(iter(sorted(build.glob("*.elf"))), None)
    hex_ = next(iter(sorted(build.glob("*.hex"))), None)
    ra = hex_ or elf
    if r.returncode != 0:
        kq.vi_sao_khong_dat = (f"{kq.cong_cu} trả mã {r.returncode} với {len(kq.loi)} lỗi."
                               if kq.loi else
                               f"{kq.cong_cu} trả mã {r.returncode} nhưng không in ra lỗi nào "
                               "có toạ độ — xem nguyên văn đầu ra.")
        return kq
    if ra is None:
        kq.vi_sao_khong_dat = (
            f"{kq.cong_cu} báo thành công nhưng KHÔNG có tệp ảnh nào trong {build}. "
            "Không coi đây là biên dịch xong.")
        return kq

    kq.tep_ra = str(ra.relative_to(goc)) if ra.is_relative_to(goc) else str(ra)
    if elf is not None:
        kq.flash, kq.sram = _doc_kich_thuoc(cc.get("avr-size", ""), elf)
    kq.dat = True
    return kq
