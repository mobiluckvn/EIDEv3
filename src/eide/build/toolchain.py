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
    # Cortex-M4/M7. `cpu` là cortex-m4 **cố ý**: lệnh của M4 chạy được trên M7 (M7 là tập
    # trên), nên một firmware dịch cho M4 chậm hơn nhưng vẫn đúng, còn dịch cho M7 rồi nạp
    # vào M4 thì sinh lệnh chip không hiểu. Chọn phía sai-thì-chậm, không chọn phía sai-thì-treo.
    #
    # `float: soft` cũng cố ý. ARMv7E-M "có FPU tuỳ biến thể": bật `-mfloat-abi=hard` trên
    # một chip không có FPU thì chương trình hard-fault ngay lệnh dấu phẩy động đầu tiên —
    # một lỗi chạy được tới lúc chạy thật mới hiện. Muốn hard-float thì phải có Fact nói chip
    # này có FPU, và truyền vào qua `fpu=`.
    "armv7e-m": {"gcc": "arm-none-eabi-gcc", "size": "arm-none-eabi-size",
                 "objcopy": "arm-none-eabi-objcopy", "cpu": "cortex-m4", "float": "soft"},
    "armv7-m": {"gcc": "arm-none-eabi-gcc", "size": "arm-none-eabi-size",
                "objcopy": "arm-none-eabi-objcopy", "cpu": "cortex-m3", "float": "soft"},
    "armv6-m": {"gcc": "arm-none-eabi-gcc", "size": "arm-none-eabi-size",
                "objcopy": "arm-none-eabi-objcopy", "cpu": "cortex-m0plus", "float": "soft"},
}

# FPU hợp lệ theo `cpu`. Bảng này tồn tại để một chuỗi FPU sai không lọt xuống trình biên dịch
# rồi hiện ra dưới dạng lỗi khó hiểu của `as`.
FPU_HOP_LE: dict[str, tuple[str, ...]] = {
    "cortex-m4": ("fpv4-sp-d16",),
    "cortex-m7": ("fpv5-sp-d16", "fpv5-d16"),
    "cortex-m33": ("fpv5-sp-d16",),
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
    tep_bin: str = ""             # ảnh nhị phân thô, cần cho bo nạp kiểu ổ đĩa (ST-LINK MSD)
    thieu_libc: bool = False      # máy không có newlib → mọi hàm chuẩn sẽ không liên kết được
    flash: int = 0
    sram: int = 0
    flash_toi_da: int = 0
    sram_toi_da: int = 0
    section: dict[str, int] = field(default_factory=dict)   # từng section, để người kiểm lại
    nguyen_van: str = ""          # đuôi đầu ra thật, để người đọc kiểm được
    vi_sao_khong_dat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "cong_cu": self.cong_cu, "lenh": list(self.lenh),
                "so_loi": len(self.loi), "so_canh_bao": len(self.canh_bao),
                "loi": [x.to_dict() for x in self.loi[:40]],
                "canh_bao": [x.to_dict() for x in self.canh_bao[:20]],
                "tep_ra": self.tep_ra, "tep_bin": self.tep_bin,
                "thieu_libc": self.thieu_libc,
                "section": dict(self.section),
                "flash": self.flash, "sram": self.sram,
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
          "mcu": cau_hinh.get("mcu", ""), "cpu": cau_hinh.get("cpu", ""),
          "float": cau_hinh.get("float", "")}
    for ten in ("arduino-cli", cau_hinh.get("gcc", ""), cau_hinh.get("size", ""),
                cau_hinh.get("objcopy", "")):
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


def kich_thuoc_arm(size_bin: str, elf: Path) -> tuple[int, int, dict[str, int]]:
    """`arm-none-eabi-size -A` → (flash, ram, từng section).

    Không dùng `-C` như AVR: `-C` của binutils ARM **không** in "Program:/Data:" mà in bảng
    Berkeley, nên bộ đọc của AVR sẽ khớp 0 dòng và trả về (0, 0) — tức là "firmware nặng 0
    byte", một con số vô lý mà vẫn đi tiếp được vào phép so hạn mức.

    Flash = mọi section nằm trong ảnh nạp (`.text`, `.rodata`, `.data`, các `.isr_vector`);
    RAM = `.data` + `.bss` (+ vùng đã ghi sẵn khác). `.data` đếm CẢ HAI vì nó tốn chỗ trong
    Flash để lưu giá trị khởi tạo *và* chỗ trong RAM lúc chạy.
    """
    if not size_bin or not elf.exists():
        return 0, 0, {}
    r = subprocess.run([size_bin, "-A", str(elf)], capture_output=True, text=True)
    sec: dict[str, int] = {}
    for d in r.stdout.splitlines():
        m = re.match(r"\s*(\.\S+)\s+(\d+)\s+", d)
        if m:
            sec[m.group(1)] = int(m.group(2))
    ram_ten = (".data", ".bss", ".noinit")
    # Mọi section có kích thước mà KHÔNG phải vùng RAM thuần và không phải thông tin gỡ lỗi
    # thì nằm trong ảnh nạp. Liệt kê trắng theo tên sẽ bỏ sót section do linker script tự đặt
    # (`.isr_vector`, `.ARM.exidx`, `.qspi_text`…) và cho ra một con số Flash nhỏ hơn thật.
    flash = sum(v for k, v in sec.items()
                if k not in (".bss", ".noinit", ".stack", ".heap", ".comment")
                and not k.startswith((".debug", ".ARM.attributes")))
    ram = sum(v for k, v in sec.items() if k in ram_ten)
    return flash, ram, sec


def duong_libc(gcc: str, cpu: str, co_fpu: bool = False) -> str:
    """Đường dẫn `libc.a` mà chính gcc sẽ dùng, hoặc "" nếu máy không có newlib.

    Hỏi thẳng trình biên dịch bằng `-print-file-name`: nó trả về đường dẫn tuyệt đối nếu tìm
    thấy, và trả về đúng cái tên vừa hỏi nếu không. Cách này đúng cho mọi cách cài (Homebrew,
    cask của ARM, gói của hãng) vì nó dùng đúng đường tìm kiếm của bản gcc đang chạy — dò tay
    trong `/opt/homebrew` thì sẽ sai ngay khi người dùng cài bằng cách khác.

    `arm-none-eabi-gcc` của Homebrew **không** kèm newlib, nên trên máy này libc không có. Đó
    là một sự thật về môi trường, không phải lỗi của dự án, và nó phải hiện ra thành một câu
    người dùng đọc được chứ không phải `cannot find -lc` từ `ld`.
    """
    if not gcc:
        return ""
    lenh = [gcc, f"-mcpu={cpu}", "-mthumb", "-print-file-name=libc.a"]
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    ra = (r.stdout or "").strip()
    return ra if ra and ra != "libc.a" and Path(ra).exists() else ""


# Thư mục con nhiều tới mấy cũng không nên nổ dòng lệnh. Cây SDK của hãng sâu chừng 5–6 cấp.
TRAN_THU_MUC_INCLUDE = 60


def _duong_include(sketch: Path) -> list[str]:
    """`-I` cho thư mục gốc VÀ mọi thư mục con có header.

    Vì sao không phải một `-I` duy nhất: mã của hãng mang theo `#include` **tương đối** giả
    định đúng cây thư mục gốc của nó. Đo được trên bo STM32F469:

        stm32469i_discovery_lcd.c:58: #include "../../../Utilities/Fonts/fonts.h"

    Ba cấp `..` ấy chỉ đúng khi tệp nằm ở `Drivers/BSP/STM32469I-Discovery/`. Với một thư mục
    phẳng, đường dẫn đó không trỏ vào đâu cả — và người đọc lỗi sẽ đi tìm một tệp `fonts.h`
    bị thiếu, trong khi tệp ấy có thật và nằm ngay trong dự án.

    Nên: giữ được cây thì giữ, và trình biên dịch phải tìm header ở mọi thư mục con.
    """
    if sketch.is_file():
        return [f"-I{sketch.parent}"]
    thu_muc = {sketch}
    for p in sketch.rglob("*.h"):
        thu_muc.add(p.parent)
    ds = sorted(thu_muc, key=lambda x: str(x))[:TRAN_THU_MUC_INCLUDE]
    return [f"-I{d}" for d in ds]


def _nguon_bare_metal(sketch: Path) -> tuple[list[str], list[str]]:
    """(tệp nguồn, tệp linker script) trong một thư mục firmware bare-metal."""
    if sketch.is_file():
        return [str(sketch)], []
    nguon = [str(x) for x in sorted(sketch.rglob("*.c"))]
    nguon += [str(x) for x in sorted(sketch.rglob("*.s"))]
    nguon += [str(x) for x in sorted(sketch.rglob("*.S"))]
    return nguon, [str(x) for x in sorted(sketch.rglob("*.ld"))]


def bien_dich(*, goc: Path, sketch: Path, isa: str = "avr8",
              flash_toi_da: int = 0, sram_toi_da: int = 0,
              thu_muc_build: Path | None = None, fpu: str = "") -> KetQuaBienDich:
    """Biên dịch `sketch` (một thư mục sketch Arduino hoặc một tệp .ino/.c).

    Trả về kết quả ĐÃ ĐỌC từ trình biên dịch. `dat=True` chỉ khi tiến trình trả 0 **và** có
    tệp ảnh nhị phân trên đĩa: một trình biên dịch trả 0 mà không sinh ra tệp nào là một
    trường hợp đã gặp thật (đường dẫn sai), và nếu tin vào mã trả về thì ta báo "biên dịch
    xong" cho một firmware không tồn tại.

    `fpu` chỉ truyền khi có Fact nói chip này có FPU (ví dụ `fpv4-sp-d16`). Bỏ trống thì dịch
    dấu phẩy động bằng thư viện — chậm hơn, nhưng chạy trên mọi biến thể.
    """
    kq = KetQuaBienDich(flash_toi_da=flash_toi_da, sram_toi_da=sram_toi_da)
    cc = tim_chuoi_cong_cu(isa)
    if not cc:
        kq.vi_sao_khong_dat = (f"Chưa biết biên dịch cho kiến trúc “{isa}”. "
                               f"Đang hỗ trợ: {', '.join(CHUOI_CONG_CU)}.")
        return kq

    build = thu_muc_build or (goc / ".eide" / "build")
    build.mkdir(parents=True, exist_ok=True)
    la_arm = bool(cc.get("cpu"))

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
    elif la_arm and cc.get("arm-none-eabi-gcc"):
        loi = _lenh_arm(kq, cc, sketch=sketch, build=build, fpu=fpu)
        if loi:
            kq.vi_sao_khong_dat = loi
            return kq
    elif la_arm:
        kq.vi_sao_khong_dat = (
            f"Máy này chưa có `arm-none-eabi-gcc` để biên dịch cho {isa} "
            f"({cc.get('cpu')}). EIDE không tự cài — đó là việc của người dùng, qua cổng "
            "G-TOOL (tool.install).")
        return kq
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
    if elf is not None and la_arm:
        kq.flash, kq.sram, kq.section = kich_thuoc_arm(cc.get("arm-none-eabi-size", ""), elf)
        loi_bin = _sinh_bin(kq, cc, elf=elf, build=build, goc=goc)
        if loi_bin:
            # Không có .bin thì không nạp được vào bo kiểu ổ đĩa — mà "biên dịch xong nhưng
            # không nạp được" là đúng loại nửa-thành-công phải nói ra, không được làm tròn lên.
            kq.vi_sao_khong_dat = loi_bin
            return kq
    elif elf is not None:
        kq.flash, kq.sram = _doc_kich_thuoc(cc.get("avr-size", ""), elf)
    kq.dat = True
    return kq


def _lenh_arm(kq: "KetQuaBienDich", cc: dict[str, str], *, sketch: Path, build: Path,
              fpu: str) -> str:
    """Dựng lệnh biên dịch bare-metal ARM. Trả chuỗi lý do nếu KHÔNG dựng được."""
    kq.cong_cu = "arm-none-eabi-gcc"
    nguon, ld = _nguon_bare_metal(sketch)
    if not nguon:
        return (f"Không có tệp .c/.s nào trong {sketch.name} để biên dịch.")
    if not ld:
        # Không tự sinh linker script: nó quyết định địa chỉ Flash/RAM của đúng con chip này,
        # và một địa chỉ đoán ra sẽ cho một firmware dịch xong, nạp xong, rồi không chạy.
        return ("Firmware bare-metal cho ARM cần một linker script (`*.ld`) khai địa chỉ và "
                f"kích thước Flash/RAM của chip. Không thấy tệp .ld nào trong {sketch.name}. "
                "EIDE không tự sinh — hãy viết nó từ số liệu trong datasheet.")
    if len(ld) > 1:
        return ("Có " + str(len(ld)) + " tệp .ld trong thư mục nguồn ("
                + ", ".join(Path(x).name for x in ld)
                + "). Không đoán dùng cái nào — chỉ giữ lại một, hoặc tách thư mục.")

    cpu = cc.get("cpu") or "cortex-m4"
    cờ_fpu = ["-mfloat-abi=soft"]
    if fpu:
        hop_le = FPU_HOP_LE.get(cpu, ())
        if hop_le and fpu not in hop_le:
            return (f"FPU “{fpu}” không hợp lệ cho {cpu} (hợp lệ: {', '.join(hop_le)}). "
                    "Không dịch với FPU sai — chương trình sẽ hard-fault ở lệnh dấu phẩy "
                    "động đầu tiên.")
        cờ_fpu = [f"-mfpu={fpu}", "-mfloat-abi=hard"]

    # Có newlib thì liên kết với nó; không có thì liên kết thuần `libgcc` và NÓI RA. Đổi âm
    # thầm là cách để `undefined reference to memset` xuất hiện sau đó, ở một chỗ không liên
    # quan gì tới nguyên nhân thật.
    libc = duong_libc(cc["arm-none-eabi-gcc"], cpu)
    thu_vien = ["-lc", "-lgcc"] if libc else ["-nostdlib", "-lgcc"]
    if not libc:
        kq.thieu_libc = True

    kq.lenh = [
        cc["arm-none-eabi-gcc"], f"-mcpu={cpu}", "-mthumb", *cờ_fpu,
        "-Os", "-g3", "-std=gnu11", "-Wall", "-Wextra",
        "-ffreestanding", "-ffunction-sections", "-fdata-sections",
        *_duong_include(sketch),
        "-T", ld[0], "-nostartfiles",
        "-Wl,--gc-sections", f"-Wl,-Map={build / 'mach.map'}",
        "-o", str(build / "mach.elf"), *nguon, *thu_vien]
    return ""


def _sinh_bin(kq: "KetQuaBienDich", cc: dict[str, str], *, elf: Path, build: Path,
              goc: Path) -> str:
    """ELF → .bin và .hex. Trả lý do nếu không sinh được."""
    oc = cc.get("arm-none-eabi-objcopy", "")
    if not oc:
        return ("Đã có mach.elf nhưng thiếu `arm-none-eabi-objcopy` nên không tạo được tệp "
                ".bin để nạp vào bo. Cài nó qua tool.install (cổng G-TOOL).")
    for dinh_dang, duoi in (("binary", "bin"), ("ihex", "hex")):
        p = build / f"mach.{duoi}"
        r = subprocess.run([oc, "-O", dinh_dang, str(elf), str(p)],
                           capture_output=True, text=True)
        if r.returncode != 0 or not p.exists() or p.stat().st_size == 0:
            return (f"objcopy không tạo được mach.{duoi}: "
                    f"{(r.stderr or r.stdout or 'không rõ').strip()[:200]}")
    kq.tep_bin = str((build / "mach.bin").relative_to(goc)) \
        if (build / "mach.bin").is_relative_to(goc) else str(build / "mach.bin")
    return ""


# ============================================================ kiểm môi trường (env.check)
@dataclass(slots=True)
class CongCu:
    """Một chương trình cần có trên máy."""

    ten: str
    de_lam_gi: str
    co: bool = False
    duong_dan: str = ""
    phien_ban: str = ""
    bat_buoc: bool = True
    cach_cai: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.ten, "de_lam_gi": self.de_lam_gi, "co": self.co,
                "duong_dan": self.duong_dan, "phien_ban": self.phien_ban,
                "bat_buoc": self.bat_buoc, "cach_cai": self.cach_cai}


# Cần gì cho kiến trúc nào. `cach_cai` là LỆNH THẬT sẽ chạy nếu người dùng đồng ý — viết sẵn
# ở đây để `tool.install` không phải bịa ra lệnh, và để người dùng đọc được trước khi duyệt.
CAN_GI: dict[str, list[dict[str, Any]]] = {
    "avr8": [
        {"ten": "arduino-cli", "de_lam_gi": "biên dịch sketch Arduino cho AVR",
         "bat_buoc": False, "cach_cai": "brew install arduino-cli"},
        {"ten": "avr-gcc", "de_lam_gi": "biên dịch C thuần cho AVR",
         "bat_buoc": False, "cach_cai": "arduino-cli core install arduino:avr"},
        {"ten": "avr-size", "de_lam_gi": "đọc kích thước Flash/SRAM của tệp ảnh",
         "bat_buoc": False, "cach_cai": "brew install avr-binutils"},
        {"ten": "avrdude", "de_lam_gi": "nạp firmware vào bo (bước G7)",
         "bat_buoc": False, "cach_cai": "brew install avrdude"},
    ],
    "armv7e-m": [
        {"ten": "arm-none-eabi-gcc", "de_lam_gi": "biên dịch cho Cortex-M4/M7",
         "bat_buoc": True, "cach_cai": "brew install --cask gcc-arm-embedded"},
        {"ten": "arm-none-eabi-size", "de_lam_gi": "đọc kích thước Flash/RAM",
         "bat_buoc": True, "cach_cai": "brew install --cask gcc-arm-embedded"},
        {"ten": "arm-none-eabi-objcopy", "de_lam_gi": "ELF → .bin/.hex để nạp vào bo",
         "bat_buoc": True, "cach_cai": "brew install arm-none-eabi-binutils"},
        # newlib KHÔNG phải một lệnh nên không dò được bằng PATH. Nó vẫn phải có mặt trong
        # bảng này: `arm-none-eabi-gcc` của Homebrew không kèm newlib, và người dùng chỉ biết
        # điều đó khi trình liên kết báo `cannot find -lc` — một câu không nói được phải làm gì.
        {"ten": "newlib (libc cho ARM)", "kiem": "libc_arm",
         "de_lam_gi": "hàm chuẩn C (memset/memcpy/printf) khi liên kết firmware",
         "bat_buoc": False, "cach_cai": "brew install --cask gcc-arm-embedded"},
        # G7 — mạch thật. Bo ST-LINK kiểu ổ đĩa nạp được bằng cách sao tệp, nhưng **không** đọc
        # được ID chip; mà MDD-40 §B1 đòi "flash đối chiếu ID chip" (TC034). Nên hai công cụ
        # dưới đây là cách duy nhất làm đúng phép đối chiếu đó.
        {"ten": "st-info", "de_lam_gi": "đọc ID chip qua SWD để đối chiếu với hộ chiếu (TC034)",
         "bat_buoc": False, "cach_cai": "brew install stlink"},
        {"ten": "st-flash", "de_lam_gi": "nạp và verify qua SWD (TC029)",
         "bat_buoc": False, "cach_cai": "brew install stlink"},
        {"ten": "openocd", "de_lam_gi": "nạp, gỡ lỗi, đọc thanh ghi ngoại vi (TC030)",
         "bat_buoc": False, "cach_cai": "brew install open-ocd"},
    ],
    "rv32imac": [
        {"ten": "riscv64-unknown-elf-gcc", "de_lam_gi": "biên dịch cho RISC-V",
         "bat_buoc": True, "cach_cai": "brew tap riscv-software-src/riscv && "
                                       "brew install riscv-tools"},
    ],
}

# Công cụ dùng chung, không phụ thuộc kiến trúc.
CAN_GI_CHUNG = [
    {"ten": "cc", "de_lam_gi": "biên dịch phần logic để MÔ PHỎNG trên máy chủ",
     "bat_buoc": True, "cach_cai": "xcode-select --install"},
    {"ten": "git", "de_lam_gi": "lưu lịch sử tệp của dự án",
     "bat_buoc": False, "cach_cai": "xcode-select --install"},
]


def _kiem_libc_arm(isa: str) -> str:
    """Có newlib cho ISA này không. Trả đường dẫn `libc.a` hoặc "" — cùng giao kèo `_tim_lenh`."""
    cf = CHUOI_CONG_CU.get(isa or "", {})
    gcc = _tim_lenh(str(cf.get("gcc") or ""))
    return duong_libc(gcc, str(cf.get("cpu") or "cortex-m4")) if gcc else ""


# Thứ cần có mà KHÔNG phải một lệnh trong PATH thì dò bằng hàm riêng ở đây.
_KIEM_RIENG: dict[str, Any] = {"libc_arm": _kiem_libc_arm}


def _phien_ban(duong_dan: str) -> str:
    """Dòng đầu của `--version`. Không đọc được thì trả rỗng, KHÔNG đoán.

    Bỏ qua dòng lỗi: `arduino-cli --version` trả *"Error: unknown flag: --version"* (nó dùng
    `version` làm lệnh con), và nếu nhận dòng đó làm phiên bản thì bảng môi trường hiện một
    câu lỗi ở chỗ đáng lẽ là số phiên bản — trông như công cụ hỏng trong khi nó chạy tốt.
    """
    for co in ("--version", "-version", "version", "-V"):
        try:
            r = subprocess.run([duong_dan, co], capture_output=True, text=True, timeout=8)
        except (OSError, subprocess.SubprocessError):
            continue
        dong = [d for d in ((r.stdout or "") + "\n" + (r.stderr or "")).splitlines()
                if d.strip()]
        if not dong:
            continue
        d0 = dong[0].strip()
        if d0.lower().startswith(("error", "unknown", "usage", "invalid")):
            continue
        return d0[:120]
    return ""


def kiem_moi_truong(isa: str = "") -> dict[str, Any]:
    """Máy này có gì, thiếu gì, và thiếu thì hỏng việc nào.

    Trả về sự thật đo được, không kèm kết luận "sẵn sàng biên dịch". Kết luận đó là việc của
    công cụ gọi: TC018 nói rõ hệ thống **không được báo biên dịch thành công giả** khi thiếu
    chuỗi công cụ, mà cách chắc chắn nhất để không báo giả là không bao giờ tự tuyên bố sẵn
    sàng — chỉ liệt kê cái có và cái thiếu.
    """
    ds: list[CongCu] = []
    for c in CAN_GI_CHUNG + CAN_GI.get(isa or "", []):
        duong = (_KIEM_RIENG[str(c["kiem"])](isa) if c.get("kiem")
                 else _tim_lenh(str(c["ten"])))
        ds.append(CongCu(
            ten=str(c["ten"]), de_lam_gi=str(c["de_lam_gi"]), co=bool(duong),
            duong_dan=duong, phien_ban=_phien_ban(duong) if duong else "",
            bat_buoc=bool(c.get("bat_buoc", True)), cach_cai=str(c.get("cach_cai", ""))))

    thieu = [c for c in ds if not c.co]
    thieu_bb = [c for c in thieu if c.bat_buoc]
    bien_dich_duoc = bool(isa) and bool(tim_chuoi_cong_cu(isa).get("arduino-cli")
                                        or tim_chuoi_cong_cu(isa).get(
                                            CHUOI_CONG_CU.get(isa, {}).get("gcc", "")))
    return {
        "isa": isa, "cong_cu": [c.to_dict() for c in ds],
        "so_co": sum(1 for c in ds if c.co), "so_thieu": len(thieu),
        "thieu": [c.ten for c in thieu], "thieu_bat_buoc": [c.ten for c in thieu_bb],
        "bien_dich_duoc": bien_dich_duoc,
        "isa_biet": sorted(CHUOI_CONG_CU),
        "isa_chua_biet": bool(isa) and isa not in CHUOI_CONG_CU,
    }


# ============================================================ đọc map/ELF (build.map)
def doc_map(*, elf: Path, size_bin: str = "", nm_bin: str = "",
            flash_toi_da: int = 0, sram_toi_da: int = 0) -> dict[str, Any]:
    """Kích thước theo section và các symbol lớn nhất — để biết *cái gì* chiếm chỗ.

    Một con số tổng ("3.520 B Flash") nói firmware có vừa chip không; nó không nói phải bỏ
    gì khi không vừa. TC021 đòi đúng phần sau: *"phân tích map file, đề xuất tối ưu hoặc đổi
    MCU"* — và không đề xuất được nếu không biết bảng nào to nhất.
    """
    ra: dict[str, Any] = {"tep": str(elf), "section": [], "symbol": [], "canh_bao": []}
    if not elf.exists():
        ra["canh_bao"].append(f"Không có {elf} — biên dịch trước đã.")
        return ra

    size_bin = size_bin or _tim_lenh("avr-size") or _tim_lenh("size")
    if size_bin:
        r = subprocess.run([size_bin, "-A", str(elf)], capture_output=True, text=True)
        for d in r.stdout.splitlines():
            p = d.split()
            if len(p) >= 2 and p[0].startswith("."):
                try:
                    ra["section"].append({"ten": p[0], "byte": int(p[1])})
                except ValueError:
                    continue
    else:
        ra["canh_bao"].append("Không có avr-size/size trên máy — chưa đọc được section.")

    nm_bin = nm_bin or _tim_lenh("avr-nm") or _tim_lenh("nm")
    if nm_bin:
        r = subprocess.run([nm_bin, "--print-size", "--size-sort", "--radix=d", str(elf)],
                           capture_output=True, text=True)
        for d in r.stdout.splitlines():
            p = d.split()
            # `avr-nm --print-size` in "value size type name" cho symbol CÓ kích thước, và
            # "value type name" cho symbol không có. Không phân biệt hai dạng thì cột `type`
            # bị đọc thành kích thước — bảng hiện `_etext = 8.388.720 B`, một con số vô lý
            # đứng đầu danh sách "chiếm chỗ nhiều nhất".
            if len(p) == 4 and p[0].isdigit() and p[1].isdigit():
                ra["symbol"].append({"ten": p[3], "byte": int(p[1]), "loai": p[2]})
        ra["symbol"] = sorted(ra["symbol"], key=lambda x: -x["byte"])[:15]
    else:
        ra["canh_bao"].append("Không có avr-nm/nm trên máy — chưa đọc được symbol.")

    # Flash = text + data (data được chép từ Flash sang RAM lúc khởi động); RAM = data + bss.
    theo_ten = {s["ten"]: s["byte"] for s in ra["section"]}
    flash = theo_ten.get(".text", 0) + theo_ten.get(".data", 0)
    sram = theo_ten.get(".data", 0) + theo_ten.get(".bss", 0)
    ra["flash"], ra["sram"] = flash, sram
    ra["flash_toi_da"], ra["sram_toi_da"] = flash_toi_da, sram_toi_da
    ra["vua_flash"] = (flash <= flash_toi_da) if flash_toi_da else None
    ra["vua_sram"] = (sram <= sram_toi_da) if sram_toi_da else None

    de_xuat: list[str] = []
    if flash_toi_da and flash > flash_toi_da:
        to = ", ".join(f"{s['ten']} ({s['byte']} B)" for s in ra["symbol"][:3])
        de_xuat.append(f"Flash vượt {flash - flash_toi_da} B. Chỗ chiếm nhiều nhất: {to}. "
                       "Xem có bảng tra hằng nào đưa được vào PROGMEM, hoặc bỏ printf dấu "
                       "phẩy động, trước khi tính đổi chip.")
    if sram_toi_da and sram > sram_toi_da:
        de_xuat.append(f"SRAM vượt {sram - sram_toi_da} B. Trên AVR, chuỗi hằng nằm trong "
                       "RAM trừ khi đánh dấu PROGMEM — kiểm chỗ đó trước.")
    if sram_toi_da and sram > sram_toi_da * 0.75:
        de_xuat.append(f"SRAM đã dùng {sram}/{sram_toi_da} B. Ngăn xếp và biến cục bộ nằm ở "
                       "phần còn lại và KHÔNG có trong con số này — tràn ngăn xếp trên AVR "
                       "không sinh ngoại lệ mà lặng lẽ hỏng.")
    ra["de_xuat"] = de_xuat
    return ra
