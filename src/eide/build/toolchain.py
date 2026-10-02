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
    # RISC-V 32 bit bare-metal, cho lõi mềm chạy trên FPGA (PicoRV32, NEORV32, VexRiscv…).
    #
    # Dùng `riscv64-unknown-elf-gcc` chứ không phải một trình biên dịch rv32 riêng: bản
    # Homebrew là trình biên dịch đa thư viện, `--print-multi-lib` có sẵn `rv32i/ilp32` và
    # `rv32im/ilp32`. Đo trên máy này ngày 01/10/2026: cả hai `-march` dưới đây dịch được.
    #
    # `_zicsr` cần, và đây là lý do ĐÃ ĐO chứ không phải lý do nhớ lại. Trên gcc 14.2.0 của máy
    # này, ngày 01/10/2026:
    #
    #   -march=rv32i        + `rdcycle a0`        -> dịch được (nó là tên gọi tắt, as vẫn nhận)
    #   -march=rv32i        + `csrr a0, cycle`    -> LỖI ở as
    #   -march=rv32i_zicsr  + cả hai dạng         -> dịch được
    #
    # Nên bỏ `_zicsr` thì chương trình dùng `rdcycle` vẫn dịch, và người viết sẽ tin là không
    # cần — tới khi đổi sang dạng `csrr` chung (để đọc `cycleh`, `instret`, hay thanh ghi tuỳ
    # biến) thì mới vỡ, ở một lượt sửa không liên quan. Để sẵn `_zicsr` cho khỏi bẫy đó.
    #
    # Ghi chú về một lần nhầm: bản đầu của dòng chú thích này viết "thiếu _zicsr thì rdcycle
    # không dịch được". Phép thử ở trên cho thấy câu đó sai. Giữ lại vết để lần sau không ai
    # chép lại một lý do nghe hợp lý mà chưa đo.
    #
    # `objcopy` có mặt vì lõi mềm nạp chương trình bằng `$readmemh` lúc tổng hợp: phải đổi
    # `.elf` thành `.hex` rồi mới nhúng được vào BRAM.
    "rv32i": {"gcc": "riscv64-unknown-elf-gcc", "size": "riscv64-unknown-elf-size",
              "objcopy": "riscv64-unknown-elf-objcopy",
              "objdump": "riscv64-unknown-elf-objdump",
              "march": "rv32i_zicsr", "mabi": "ilp32"},
    "rv32im": {"gcc": "riscv64-unknown-elf-gcc", "size": "riscv64-unknown-elf-size",
               "objcopy": "riscv64-unknown-elf-objcopy",
               "objdump": "riscv64-unknown-elf-objdump",
               "march": "rv32im_zicsr", "mabi": "ilp32"},
    "rv32imac": {"gcc": "riscv64-unknown-elf-gcc", "size": "riscv64-unknown-elf-size",
                 "objcopy": "riscv64-unknown-elf-objcopy",
                 "objdump": "riscv64-unknown-elf-objdump",
                 "march": "rv32imac_zicsr", "mabi": "ilp32"},
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

# Chỗ EIDE đặt công cụ nó tải về. Nó KHÔNG có trong Homebrew (đã tra ngày 01/10/2026: `brew
# search nextpnr` chỉ có `nextpnr-ice40`), nên cách cài là tải tệp nén từ trang phát hành rồi
# giải ra. Giải ra xong thì các lệnh nằm ở `bin/`, mà thư mục đó không tự vào PATH — nên phải
# tìm thêm ở đây, đúng cách đã làm với gói Arduino ở trên.
#
# Vì sao KHÔNG dùng `~/.local` như thói quen trên Linux: đo được ngày 01/10/2026, trên máy này
# `~/.local` do **root** sở hữu với quyền 755, tạo từ 2023. Không user nào ghi vào được, nên
# `tar` báo "Failed to create dir: Permission denied". Sửa quyền thư mục ấy cần `sudo`, tức là
# một điểm dừng phải hỏi người dùng — để cài một công cụ thì cái giá đó quá đắt, và nó biến một
# việc không cần quyền quản trị thành việc cần.
#
# Và vì sao KHÔNG dùng `~/Library/Application Support/EIDE` dù đó là chỗ đúng của macOS: tên
# thư mục ấy **có dấu cách**. Đo được ngày 01/10/2026 — script bọc của gói oss-cad-suite viết
# `exec $release_bindir_abs/tabbypy3 ...` mà KHÔNG bọc nháy biến, nên đường dẫn có dấu cách bị
# cắt làm hai và `gowin_pack` báo "/Users/congvt/Library/Application: No such file or directory".
# Đó là lỗi của gói, nhưng cách chữa phía mình là chọn đường dẫn không có dấu cách.
#
# `~/.eide` do người dùng sở hữu, không dấu cách, và trùng tên với dự án nên người đọc biết ngay
# thư mục ấy của ai.
_THU_MUC_CONG_CU = Path.home() / ".eide/cong-cu"
_OSS_CAD = _THU_MUC_CONG_CU / "oss-cad-suite"


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
    # Lõi mềm RISC-V trên FPGA nạp chương trình lúc TỔNG HỢP, bằng `$readmemh`. Đây là tệp đó —
    # một từ 32 bit mỗi dòng, KHÔNG phải Intel HEX. Hai định dạng cùng đuôi `.hex` mà khác hẳn
    # nhau, nên tách thành trường riêng để không ai đưa nhầm tệp cho nhầm công cụ.
    tep_hex_readmemh: str = ""
    so_tu_readmemh: int = 0
    # Mã máy CÓ THẬT dùng những lệnh mở rộng nào. Đếm từ bản tháo mã, không suy từ cờ
    # `-march`: `-march=rv32im` chỉ CHO PHÉP sinh lệnh nhân, không bảo đảm có lệnh nào được
    # sinh ra. Trường này tồn tại vì ngày 02/10/2026 một phép đo đã so hai cấu hình CPU —
    # có bộ nhân và không có bộ nhân — bằng một mã máy biên dịch với `-march=rv32i`, tức
    # không chứa một lệnh `mul` nào. Hai lượt đo ra số GIỐNG HỆT NHAU, và con số giống nhau
    # ấy bị đọc thành "bộ nhân phần cứng không giúp gì", trong khi nó chỉ có nghĩa là bộ
    # nhân chưa bao giờ được dùng. Xem `kiem_khop_phan_cung()`.
    lenh_mo_rong: dict[str, int] = field(default_factory=dict)
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
                "tep_hex_readmemh": self.tep_hex_readmemh,
                "so_tu_readmemh": self.so_tu_readmemh,
                "lenh_mo_rong": dict(self.lenh_mo_rong),
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

# Lỗi của TRÌNH LIÊN KẾT có dạng khác: `đường/dẫn:dòng: thông điệp` — không có cột, không có
# chữ "error:". Mẫu trên không khớp, nên trước ngày 01/10/2026 một lỗi cú pháp trong tệp
# linker script hiện ra thành câu *"trả mã 1 nhưng không in ra lỗi nào có toạ độ"* — đúng lúc
# `ld` đã nói rõ tệp nào dòng nào.
#
# Chuyện này quan trọng hơn vẻ ngoài với dự án FPGA: lõi mềm RISC-V không có linker script sẵn,
# người phải tự viết từ bản đồ địa chỉ của chính thiết kế phần cứng. Nó là tệp bị sửa nhiều
# nhất và sai nhiều nhất, mà lại là tệp duy nhất EIDE không đọc nổi lỗi.
#
# `ld:` ở đầu dòng bị bỏ qua: `ld` thường in `/đường/dẫn/tới/ld:tệp:dòng: lỗi`, nên phải cắt
# phần tên chính nó ra trước, không thì "tệp" nhận được là đường dẫn tới `ld`.
_MAU_LOI_LD = re.compile(
    r"(?:^|[/\s])(?:ld|ld\.lld|collect2)?:?\s*"
    r"(?P<tep>[^\s:][^:]*\.(?:ld|c|h|S|s|cpp|v|sv)):(?P<dong>\d+):\s*"
    r"(?P<td>(?:syntax error|undefined reference|cannot find|multiple definition|"
    r"region .* overflowed|section .* will not fit|non constant|.*)\S.*)$", re.I)


def phan_tich_loi(dau_ra: str, *, goc: Path | None = None) -> list[LoiBienDich]:
    """Tách thông điệp trình biên dịch thành bản ghi có toạ độ."""
    ra: list[LoiBienDich] = []

    def _tuong_doi(tep: str) -> str:
        if goc is None:
            return tep
        try:
            return str(Path(tep).resolve().relative_to(goc.resolve()))
        except ValueError:
            return tep

    for d in dau_ra.splitlines():
        d = d.strip()
        m = _MAU_LOI.match(d)
        if m:
            ra.append(LoiBienDich(
                tep=_tuong_doi(m.group("tep")), dong=int(m.group("dong")),
                cot=int(m.group("cot")),
                muc=("error" if m.group("muc") == "lỗi" else m.group("muc")),
                thong_diep=m.group("td").strip()))
            continue
        # Trình liên kết: `tệp:dòng: thông điệp`, không có cột. Cột = 0 nghĩa là "cả dòng",
        # chứ không phải cột thứ 0 — ghi 1 ở đây sẽ trỏ người đọc vào ký tự đầu dòng như thể
        # đã định vị được chỗ sai.
        m = _MAU_LOI_LD.search(d)
        if m:
            ra.append(LoiBienDich(
                tep=_tuong_doi(m.group("tep")), dong=int(m.group("dong")), cot=0,
                muc="error", thong_diep=m.group("td").strip()))
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
    for thu in (_OSS_CAD / "bin", _THU_MUC_CONG_CU / "bin"):
        ung = thu / ten
        if ung.exists():
            return str(ung)
    return ""


def tim_chuoi_cong_cu(isa: str) -> dict[str, str]:
    """Những gì MÁY NÀY thật sự có cho một kiến trúc. Khoá thiếu nghĩa là không có."""
    cau_hinh = CHUOI_CONG_CU.get(isa or "", {})
    if not cau_hinh:
        return {}
    # `march`/`mabi` phải có mặt ở đây, không chỉ trong `CHUOI_CONG_CU`: bên gọi nhận biết một
    # dự án RISC-V bằng cách xem `cc["march"]` có bắt đầu bằng "rv32" hay không. Quên mang hai
    # khoá này sang thì mọi dự án RISC-V rơi xuống nhánh AVR và nhận về một câu nói thiếu
    # `avr-gcc` — đúng loại lỗi chỉ dẫn người đi sai hướng. Đã trúng một lần ngày 01/10/2026.
    ra = {"isa": isa, "fqbn": cau_hinh.get("arduino_fqbn", ""),
          "mcu": cau_hinh.get("mcu", ""), "cpu": cau_hinh.get("cpu", ""),
          "float": cau_hinh.get("float", ""),
          "march": cau_hinh.get("march", ""), "mabi": cau_hinh.get("mabi", "")}
    for ten in ("arduino-cli", cau_hinh.get("gcc", ""), cau_hinh.get("size", ""),
                cau_hinh.get("objcopy", ""), cau_hinh.get("objdump", "")):
        if ten:
            duong = _tim_lenh(ten)
            if duong:
                ra[ten] = duong
    # Khoá theo VAI, không theo tên lệnh: bên gọi cần "trình tháo mã của kiến trúc này" mà
    # không phải biết nó tên gì. Tên lệnh ở trên vẫn giữ, vì `_lenh_rv32` tra theo tên.
    if cau_hinh.get("objdump") and cau_hinh["objdump"] in ra:
        ra["objdump"] = ra[cau_hinh["objdump"]]
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
    la_rv32 = str(cc.get("march") or "").startswith("rv32")

    # Chọn công cụ theo DỰ ÁN LÀ GÌ, không theo MÁY CÓ GÌ.
    #
    # Bản trước hỏi "máy này có cài arduino-cli không". Đo được ngày 28/09/2026 (ca TC055):
    # một dự án chỉ có `firmware/main.c`, không tệp `.ino` nào, vẫn bị đẩy sang
    # `arduino-cli compile` — và người đang hỏi về `-O3` nhận về một lỗi nói chuyện định dạng
    # sketch của Arduino. Họ sẽ đi tìm một tệp `.ino` mà dự án không bao giờ cần.
    #
    # Hai câu hỏi ấy khác hẳn nhau, và câu đúng là câu thứ hai. `arduino-cli` chỉ dịch được
    # sketch; một thư mục có `.c` mà không có `.ino` rõ ràng không phải sketch.
    la_sketch = _la_sketch_arduino(sketch)
    if cc.get("arduino-cli") and cc.get("fqbn") and la_sketch:
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
    elif la_rv32 and cc.get("riscv64-unknown-elf-gcc"):
        loi = _lenh_rv32(kq, cc, sketch=sketch, build=build)
        if loi:
            kq.vi_sao_khong_dat = loi
            return kq
    elif la_rv32:
        kq.vi_sao_khong_dat = (
            f"Máy này chưa có `riscv64-unknown-elf-gcc` để biên dịch cho {isa} "
            f"(-march={cc.get('march')}). EIDE không tự cài — đó là việc của người dùng, qua "
            "cổng G-TOOL (tool.install).")
        return kq
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
    elif elf is not None and la_rv32:
        kq.flash, kq.sram, kq.section = kich_thuoc_arm(
            cc.get("riscv64-unknown-elf-size", ""), elf)
        loi_hex = _sinh_hex_readmemh(kq, cc, elf=elf, build=build, goc=goc)
        if loi_hex:
            # Lõi mềm nạp chương trình lúc TỔNG HỢP, bằng `$readmemh` đọc một tệp hex. Không
            # có tệp đó thì bitstream dựng ra mang một BRAM rỗng: FPGA cấu hình xong, CPU chạy,
            # và nó chạy toàn lệnh 0. Đúng loại nửa-thành-công phải nói ra.
            kq.vi_sao_khong_dat = loi_hex
            return kq
        kq.lenh_mo_rong = _dem_lenh_mo_rong(cc, elf=elf)
    elif elf is not None:
        kq.flash, kq.sram = _doc_kich_thuoc(cc.get("avr-size", ""), elf)
    kq.dat = True
    return kq


# Lệnh của từng phần mở rộng RV32, nhóm theo phần. Chỉ các lệnh mà việc CÓ hay KHÔNG CÓ
# chúng trong mã máy đổi hẳn nghĩa của một phép đo hiệu năng.
_LENH_THEO_PHAN = {
    "m": ("mul", "mulh", "mulhsu", "mulhu", "div", "divu", "rem", "remu"),
    "a": ("lr.w", "sc.w", "amoswap.w", "amoadd.w", "amoand.w", "amoor.w", "amoxor.w"),
    "c": ("c.add", "c.lw", "c.sw", "c.li", "c.mv", "c.jr"),
}

# Hàm libgcc thay cho lệnh không có. Có mặt chúng nghĩa là trình dịch phải làm phép toán
# bằng một vòng lặp phần mềm.
_HAM_THAY_LENH = ("__mulsi3", "__muldi3", "__divsi3", "__udivsi3", "__modsi3", "__umodsi3")


def _dem_lenh_mo_rong(cc: dict[str, str], *, elf: Path) -> dict[str, int]:
    """Đếm lệnh mở rộng CÓ THẬT trong mã máy, bằng cách tháo mã.

    Vì sao phải tháo mã chứ không đọc cờ `-march`: `-march=rv32im` chỉ *cho phép* trình dịch
    sinh lệnh nhân. Nó không bảo đảm có lệnh nào được sinh. Và ngược lại, `-march=rv32i`
    *bảo đảm* không có lệnh nhân nào — nên một mã máy dịch bằng cờ ấy **không thể** phân biệt
    một CPU có bộ nhân với một CPU không có.

    Đếm riêng cả lời gọi `__mulsi3`/`__divsi3`: chúng là phép nhân, phép chia làm bằng vòng
    lặp phần mềm, và biết chúng nằm ở đâu quan trọng hơn biết chúng có bao nhiêu — một lời
    gọi trong vòng lặp nóng đáng giá hàng trăm lần một lời gọi trong `main`.
    """
    duong = cc.get("objdump") or cc.get("riscv64-unknown-elf-objdump")
    if not duong or not Path(duong).exists() or not elf.exists():
        return {}
    try:
        r = subprocess.run([duong, "-d", str(elf)], capture_output=True, text=True,
                           timeout=120)
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}

    dem: dict[str, int] = {}
    ham_hien_tai = ""
    ham_co_goi: dict[str, set[str]] = {}
    for dong in r.stdout.splitlines():
        nhan = re.match(r"^[0-9a-f]+ <(.+)>:", dong)
        if nhan:
            ham_hien_tai = nhan.group(1)
            continue
        if not re.match(r"^\s+[0-9a-f]+:", dong):
            continue
        # Cột lệnh nằm sau mã máy, tách bằng tab.
        phan = dong.split("\t")
        ma_lenh = phan[2].strip().split()[0] if len(phan) > 2 and phan[2].strip() else ""
        for phan_isa, ds in _LENH_THEO_PHAN.items():
            if ma_lenh in ds:
                dem[f"lenh_{phan_isa}"] = dem.get(f"lenh_{phan_isa}", 0) + 1
        for ham in _HAM_THAY_LENH:
            if ham in dong:
                dem[f"goi_{ham.strip('_')}"] = dem.get(f"goi_{ham.strip('_')}", 0) + 1
                # Lời gọi NẰM TRONG chính hàm ấy là nhãn nội bộ, không phải người dùng gọi.
                if ham_hien_tai and not ham_hien_tai.startswith("__"):
                    ham_co_goi.setdefault(ham, set()).add(ham_hien_tai)
    for ham, ds in ham_co_goi.items():
        dem[f"noi_goi_{ham.strip('_')}"] = len(ds)
    return dem


def kiem_khop_phan_cung(lenh_mo_rong: dict[str, int],
                        cau_hinh: dict[str, str]) -> list[str]:
    """Mã máy và cấu hình CPU có khớp nhau không. Trả danh sách câu cảnh báo.

    Một phép đo so hai cấu hình CPU chỉ có nghĩa khi mã máy **chạm tới** chỗ khác nhau giữa
    chúng. Hàm này nói ra khi điều đó không đúng, vì cái sai ấy không hiện ra thành lỗi: cả
    hai lượt đo đều chạy xong, đều in ra số, và hai con số bằng nhau — trông đúng như một
    kết luận ("phần cứng ấy không giúp gì") trong khi nó chỉ là một phép đo rỗng.

    `cau_hinh` là các `define` truyền cho mô phỏng, ví dụ `{"CFG_MUL": "1"}`.
    """
    canh: list[str] = []
    if not lenh_mo_rong:
        return canh

    def bat(ten: str) -> bool:
        return str(cau_hinh.get(ten, "0")).strip() not in ("", "0")

    co_mul = any(lenh_mo_rong.get(k, 0) for k in ("lenh_m",))
    mul_phan_mem = lenh_mo_rong.get("goi_mulsi3", 0) + lenh_mo_rong.get("goi_muldi3", 0)
    noi_goi = lenh_mo_rong.get("noi_goi_mulsi3", 0) + lenh_mo_rong.get("noi_goi_muldi3", 0)

    ten_mul = [t for t in ("CFG_MUL", "CFG_FAST_MUL", "ENABLE_MUL", "ENABLE_FAST_MUL")
               if t in cau_hinh]
    if ten_mul and any(bat(t) for t in ten_mul) and not co_mul:
        canh.append(
            "Cấu hình bật bộ nhân phần cứng (" + ", ".join(f"{t}={cau_hinh[t]}" for t in ten_mul
                                                           if bat(t))
            + ") nhưng mã máy KHÔNG CHỨA một lệnh nhân nào — nó được biên dịch cho một ISA "
              "không có phần `m`. Bộ nhân sẽ ngồi không suốt lượt đo. Nếu đang so cấu hình "
              "này với cấu hình không có bộ nhân thì hai lượt sẽ ra số BẰNG NHAU, và con số "
              "bằng nhau ấy không nói gì về bộ nhân cả. Hãy biên dịch lại với `isa=\"rv32im\"`."
            + (f" (Mã máy đang làm phép nhân bằng {mul_phan_mem} lời gọi phần mềm"
               + (f", từ {noi_goi} hàm." if noi_goi else ", đều là nhãn nội bộ của libgcc.")
               + ")" if mul_phan_mem else ""))
    if ten_mul and not any(bat(t) for t in ten_mul) and co_mul:
        canh.append(
            f"Mã máy chứa {lenh_mo_rong.get('lenh_m', 0)} lệnh của phần `m` (nhân/chia) "
            "nhưng cấu hình CPU TẮT bộ nhân. CPU sẽ coi chúng là lệnh lạ và nhảy vào bẫy — "
            "chương trình không chạy tới đích. Hãy biên dịch lại với `isa=\"rv32i\"`, hoặc "
            "bật bộ nhân trong cấu hình.")
    return canh


def _sinh_hex_readmemh(kq: "KetQuaBienDich", cc: dict[str, str], *, elf: Path, build: Path,
                       goc: Path) -> str:
    """`.elf` → `mach.hex` dạng `$readmemh` đọc được: một từ 32 bit mỗi dòng, hệ 16, không tiền tố.

    Đây KHÔNG phải Intel HEX. `$readmemh` của Verilog đọc một định dạng khác hẳn: chỉ các chữ
    số hệ 16 cách nhau bằng khoảng trắng, không có byte count, không có địa chỉ, không có tổng
    kiểm. Đưa một tệp Intel HEX cho `$readmemh` thì nó nạp cả `:10000000` vào bộ nhớ như dữ
    liệu — bitstream dựng ra vẫn xong, và CPU chạy rác.

    Thứ tự byte là little-endian, vì RISC-V là little-endian và BRAM được đọc theo từ.
    """
    oc = cc.get("riscv64-unknown-elf-objcopy", "")
    if not oc:
        return ("Không có `riscv64-unknown-elf-objcopy` để đổi `.elf` thành tệp hex cho "
                "`$readmemh`. Cài qua cổng G-TOOL (tool.install).")

    # Canh bằng CHÍNH CON SỐ, trước khi gọi objcopy.
    #
    # Bản đầu chỉ dựa vào việc `objcopy` báo lỗi "has no sections". Bộ kiểm bắt được chỗ hở:
    # nếu linker script có khai một section rỗng (ví dụ `.bss`) thì tệp ảnh *có* section, nên
    # `objcopy` chạy được, sinh ra một tệp nhị phân rỗng, và EIDE báo **đạt** cho một chương
    # trình không có một lệnh nào. Một phép đo xanh cho một tệp ảnh rỗng thì nó không đo gì cả.
    #
    # `kq.flash` đã được đọc từ `size -A` ngay trước lời gọi này, nên nó là con số thật.
    if kq.flash <= 0:
        return (
            f"Biên dịch và liên kết trả 0, nhưng tệp ảnh có **{kq.flash} byte mã**. Không có "
            "lệnh nào trong đó, nên đây không phải là biên dịch xong.\n\n"
            "Nguyên nhân thường gặp: EIDE dịch với `-ffunction-sections -fdata-sections` và "
            "liên kết với `--gc-sections`, nên section nào không ai với tới sẽ bị dọn. Trong "
            "chương trình bare-metal **không ai gọi `_start`** — nó là điểm vào — nên linker "
            "script phải nói rõ hai điều:\n"
            "  1. `ENTRY(_start)` ở đầu tệp, để trình liên kết biết đâu là gốc.\n"
            "  2. `KEEP(*(.init))` (hoặc đúng tên section chứa `_start`) để nó không bị dọn.\n\n"
            "Thiếu hai dòng đó thì trình liên kết **vẫn trả mã 0**. Đây là chỗ duy nhất phát "
            "hiện ra.")
    thonhi = build / "mach.bin"
    r = subprocess.run([oc, "-O", "binary", str(elf), str(thonhi)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not thonhi.exists():
        loi = (r.stderr or "").strip()
        # "has no sections" là một câu đúng mà vô ích: nó nói hậu quả, không nói nguyên nhân.
        # Nguyên nhân gần như luôn là một cặp: EIDE dịch với `-ffunction-sections` và
        # `--gc-sections`, nên trình liên kết dọn mọi section không ai với tới. Chương trình
        # bare-metal không có ai gọi `_start` — nó là điểm vào — nên nếu linker script không
        # khai `ENTRY` và không `KEEP` section khởi động thì cả chương trình bị dọn sạch, và
        # trình liên kết **vẫn trả mã 0**. Người đọc câu gốc sẽ đi tìm lỗi trong mã C.
        if "no sections" in loi.lower():
            return (
                f"`objcopy` nói tệp ảnh không có section nào. Tệp `.elf` chỉ "
                f"{elf.stat().st_size if elf.exists() else 0} byte, tức trình liên kết đã dọn "
                "sạch chương trình.\n\n"
                "Nguyên nhân thường gặp: EIDE dịch với `-ffunction-sections -fdata-sections` "
                "và liên kết với `--gc-sections`, nên section nào không ai với tới sẽ bị dọn. "
                "Trong chương trình bare-metal **không ai gọi `_start`** — nó là điểm vào — nên "
                "linker script phải nói rõ hai điều:\n"
                "  1. `ENTRY(_start)` ở đầu tệp, để trình liên kết biết đâu là gốc.\n"
                "  2. `KEEP(*(.init))` (hoặc đúng tên section chứa `_start`) để nó không bị dọn.\n\n"
                "Thiếu cả hai thì liên kết **vẫn trả mã 0** và sinh ra một tệp ảnh rỗng — đây là "
                "chỗ duy nhất phát hiện ra.")
        return f"`objcopy -O binary` trả mã {r.returncode}: {loi[:300]}"
    raw = thonhi.read_bytes()
    # Đệm cho đủ bội số 4: một từ thiếu byte sẽ thành một từ sai, không phải một từ ngắn.
    if len(raw) % 4:
        raw += b"\x00" * (4 - len(raw) % 4)
    dong = [f"{int.from_bytes(raw[i:i + 4], 'little'):08x}" for i in range(0, len(raw), 4)]
    ra = build / "mach.hex"
    ra.write_text("\n".join(dong) + "\n", "utf-8")
    kq.tep_hex_readmemh = str(ra.relative_to(goc)) if ra.is_relative_to(goc) else str(ra)
    kq.so_tu_readmemh = len(dong)
    return ""


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


def _lenh_rv32(kq: "KetQuaBienDich", cc: dict[str, str], *, sketch: Path,
               build: Path) -> str:
    """Dựng lệnh biên dịch bare-metal RISC-V 32 bit. Trả chuỗi lý do nếu KHÔNG dựng được.

    Khác `_lenh_arm` ở ba chỗ, và cả ba đều là chỗ làm giống ARM thì sai:

    - **Không có `-mthumb`, không có `-mfloat-abi`.** RISC-V chọn phần dấu phẩy động bằng đuôi
      `f`/`d` trong `-march` cộng với `-mabi`, chứ không bằng một cờ riêng.
    - **`-mabi` phải đi cùng `-march`.** Trình biên dịch là bản đa thư viện; đưa một cặp
      không có trong `--print-multi-lib` thì trình liên kết báo thiếu `libgcc`, một câu không
      chỉ ra cặp cờ nào sai.
    - **Luôn `-nostdlib`.** Lõi mềm trên FPGA không có đủ chỗ cho newlib, và bài này tự viết
      `start.S`. Nhưng vẫn liên kết `libgcc` vì cấu hình RV32I **không có lệnh nhân** — phép
      `a * b` trong C biến thành lời gọi `__mulsi3` nằm trong `libgcc`. Thiếu nó thì đúng cấu
      hình H0 của đề bài không liên kết được.
    """
    kq.cong_cu = "riscv64-unknown-elf-gcc"
    nguon, ld = _nguon_bare_metal(sketch)
    if not nguon:
        return f"Không có tệp .c/.s nào trong {sketch.name} để biên dịch."
    if not ld:
        return ("Chương trình bare-metal cho lõi RISC-V cần một linker script (`*.ld`) khai "
                "địa chỉ và kích thước bộ nhớ. Với lõi mềm trên FPGA, các con số đó do CHÍNH "
                "thiết kế phần cứng quyết định (đáy BRAM, đỉnh BRAM làm đỉnh ngăn xếp, bản đồ "
                f"địa chỉ ngoại vi). Không thấy tệp .ld nào trong {sketch.name}. EIDE không tự "
                "sinh — một địa chỉ đoán ra cho một chương trình dịch xong, nạp xong, rồi "
                "không chạy.")
    if len(ld) > 1:
        return ("Có " + str(len(ld)) + " tệp .ld trong thư mục nguồn ("
                + ", ".join(Path(x).name for x in ld)
                + "). Không đoán dùng cái nào — chỉ giữ lại một, hoặc tách thư mục.")

    march = cc.get("march") or "rv32i_zicsr"
    mabi = cc.get("mabi") or "ilp32"
    kq.lenh = [
        cc["riscv64-unknown-elf-gcc"], f"-march={march}", f"-mabi={mabi}",
        "-Os", "-g3", "-std=gnu11", "-Wall", "-Wextra",
        "-ffreestanding", "-ffunction-sections", "-fdata-sections",
        *_duong_include(sketch),
        "-T", ld[0], "-nostartfiles", "-nostdlib",
        "-Wl,--gc-sections", f"-Wl,-Map={build / 'mach.map'}",
        "-o", str(build / "mach.elf"), *nguon, "-lgcc"]
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

# Hai ISA rv32 còn lại cần đúng bộ công cụ như `rv32imac`, chỉ khác `-march`. Sinh bằng mã chứ
# không chép tay ba lần: chép tay thì sửa một chỗ quên hai chỗ, và chỗ quên chỉ hiện ra khi
# người dùng chọn đúng ISA ấy.
_CAN_GI_RV32 = [
    {"ten": "riscv64-unknown-elf-gcc", "de_lam_gi": "biên dịch C cho lõi RISC-V 32 bit",
     "bat_buoc": True,
     "cach_cai": "brew tap riscv-software-src/riscv && brew install riscv-tools"},
    {"ten": "riscv64-unknown-elf-size", "de_lam_gi": "đọc kích thước chương trình trong BRAM",
     "bat_buoc": False,
     "cach_cai": "brew tap riscv-software-src/riscv && brew install riscv-tools"},
    {"ten": "riscv64-unknown-elf-objcopy",
     "de_lam_gi": "đổi .elf thành tệp hex cho `$readmemh` nạp vào BRAM lúc tổng hợp",
     "bat_buoc": True,
     "cach_cai": "brew tap riscv-software-src/riscv && brew install riscv-tools"},
]
for _isa in ("rv32i", "rv32im"):
    CAN_GI[_isa] = [dict(x) for x in _CAN_GI_RV32]

# ------------------------------------------------------------------ chuỗi công cụ FPGA
#
# Đây là nhóm đầu tiên trong bảng này KHÔNG phải một ISA. Nó là một **luồng công cụ**: từ mã
# Verilog tới tệp cấu hình nạp được vào FPGA, qua bốn chặng rời nhau — tổng hợp, đặt-đi dây,
# đóng gói, nạp. Bốn chặng là bốn chương trình khác nhau, và chặng nào thiếu thì ba chặng kia
# vô dụng, nên cả bốn đều `bat_buoc`.
#
# Vì sao `cach_cai` của ba chặng đầu là **cùng một lệnh**: Yosys, nextpnr và Apicula đi chung
# trong gói `oss-cad-suite`. Cài rời từng cái thì phải tự khớp phiên bản giữa chúng, mà bản
# không khớp cho ra lỗi ở chặng sau dưới dạng "unknown cell type" — một câu không chỉ ra rằng
# nguyên nhân là phiên bản.
#
# `openFPGALoader` tách riêng vì nó là chặng nạp, dùng được độc lập với ba chặng kia.
CAN_GI_FPGA_GOWIN = [
    # `yosys` CÓ trong Homebrew (0.69, đã tra 01/10/2026) và bản đó kèm sẵn `synth_gowin`.
    {"ten": "yosys", "de_lam_gi": "tổng hợp Verilog thành mạng cổng (`synth_gowin`)",
     "bat_buoc": True, "cach_cai": "brew install yosys"},
    # `nextpnr-himbaechel` KHÔNG có trong Homebrew — `brew search nextpnr` chỉ ra
    # `nextpnr-ice40`, một bản khác chip. Cách cài là tải gói oss-cad-suite của trang phát hành
    # rồi giải nén. Lệnh dưới đây tự tra bản mới nhất thay vì ghim một ngày, vì một ngày ghim
    # cứng sẽ hết hạn và lúc đó lỗi hiện ra là "404", một câu không nói được phải sửa gì.
    #
    # Không cần quyền quản trị: tải về thư mục của người dùng rồi giải ra `~/.local`.
    {"ten": "nextpnr-himbaechel",
     "de_lam_gi": "đặt-đi dây cho chip Gowin, và báo Fmax đạt được",
     "bat_buoc": True,
     # Lệnh này tìm bản phát hành mới nhất **có tệp cho đúng kiến trúc máy này**, chứ không
     # lấy mù bản `latest`. Lý do đã đo được ngày 01/10/2026: bản `latest` hôm ấy chỉ có tệp
     # `darwin-x64`, không có `darwin-arm64` — nên lấy `latest` trên máy Apple Silicon cho ra
     # một URL 404, rồi `tar` báo "not in gzip format", một câu không chỉ ra nguyên nhân thật.
     # Mười một bản trước đó đều có arm64, nên quét lùi là đủ.
     #
     # Dùng `python3` để đọc JSON, không dùng `sed`: biểu thức `sed` cho việc này phải lồng ba
     # lớp nháy, và một lớp thoát sai lại cho ra đúng cái URL rỗng ấy.
     "cach_cai": (
         'set -e; '
         'case "$(uname -m)" in arm64) P=darwin-arm64;; x86_64) P=darwin-x64;; '
         '*) echo "chua biet kien truc $(uname -m)"; exit 1;; esac; '
         'U=$(curl -fsSL '
         '"https://api.github.com/repos/YosysHQ/oss-cad-suite-build/releases?per_page=20" '
         '| P=$P python3 -c '
         '"import json,os,sys'
         '\nfor r in json.load(sys.stdin):'
         '\n    for a in r[\'assets\']:'
         '\n        if os.environ[\'P\'] in a[\'name\']:'
         '\n            print(a[\'browser_download_url\']); sys.exit(0)'
         '\nsys.exit(1)"); '
         'test -n "$U"; echo "tai: $U"; '
         'D="$HOME/.eide/cong-cu"; mkdir -p "$D"; '
         'curl -fL "$U" -o /tmp/oss-cad.tgz; '
         'tar -xzf /tmp/oss-cad.tgz -C "$D"; rm -f /tmp/oss-cad.tgz')},
    # `gowin_pack` là một lệnh của gói Python Apicula (tên trên PyPI: `apycula`, 0.33). Nó
    # KHÔNG có trong Homebrew. Cài vào `~/.local/bin` bằng `--user` để không cần quyền quản trị
    # và không làm bẩn môi trường ảo của dự án.
    {"ten": "gowin_pack",
     "de_lam_gi": "đóng gói thành tệp cấu hình `.fs` nạp được vào FPGA (Apicula)",
     "bat_buoc": True,
     "cach_cai": (
         'D="$HOME/.eide/cong-cu"; mkdir -p "$D"; '
         'python3 -m pip install --upgrade --target "$D/py" apycula; '
         'mkdir -p "$D/bin"; '
         'for f in "$D"/py/bin/*; do [ -e "$f" ] && ln -sf "$f" "$D/bin/"; done; '
         'echo "apycula o $D/py"')},
    {"ten": "openFPGALoader", "de_lam_gi": "nạp `.fs` vào SRAM hoặc flash của kit",
     "bat_buoc": True, "cach_cai": "brew install openfpgaloader"},
    {"ten": "verilator",
     "de_lam_gi": "mô phỏng nhanh để ĐO SỐ CHU KỲ (Icarus quá chậm cho bài nhân ma trận)",
     "bat_buoc": True, "cach_cai": "brew install verilator"},
    {"ten": "iverilog", "de_lam_gi": "mô phỏng testbench nhỏ, kiểm từng khối",
     "bat_buoc": False, "cach_cai": "brew install icarus-verilog"},
    {"ten": "gtkwave", "de_lam_gi": "xem dạng sóng khi cần người nhìn mắt",
     "bat_buoc": False, "cach_cai": "brew install --cask gtkwave"},
]
CAN_GI["fpga-gowin"] = CAN_GI_FPGA_GOWIN

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


# Môi trường ảo Python của EIDE, cho các gói tính toán mà dự án cần (NumPy để làm mô hình
# chuẩn, matplotlib để vẽ biểu đồ).
#
# Vì sao phải là môi trường ảo chứ không `pip install --user`: Python của Homebrew đánh dấu
# "externally managed" theo PEP 668, nên `--user` bị chặn thẳng. Gợi ý `--break-system-packages`
# trong thông báo lỗi đúng tên của nó — nó phá môi trường hệ thống, và EIDE không được làm thế
# với máy của người dùng. Đề bài của anh Công cũng nêu đúng cách này: *"venv + pip"*.
_VENV_PY = _THU_MUC_CONG_CU / "py"


def _kiem_goi_python(ten_goi: str) -> str:
    """Gói Python có nhập được trong môi trường ảo của EIDE không.

    Trả đường dẫn trình thông dịch nếu có, "" nếu không — cùng giao kèo `_tim_lenh`, để bảng
    môi trường hiện nó như mọi công cụ khác.
    """
    py = _VENV_PY / "bin" / "python3"
    if not py.exists():
        return ""
    r = subprocess.run([str(py), "-c", f"import {ten_goi}"], capture_output=True)
    return str(py) if r.returncode == 0 else ""


# Thứ cần có mà KHÔNG phải một lệnh trong PATH thì dò bằng hàm riêng ở đây.
_KIEM_RIENG: dict[str, Any] = {
    "libc_arm": _kiem_libc_arm,
    "numpy": lambda _isa: _kiem_goi_python("numpy"),
    "matplotlib": lambda _isa: _kiem_goi_python("matplotlib"),
}

# Gói Python cho phần tính toán và vẽ biểu đồ. Một lệnh cài dựng cả môi trường ảo rồi cài cả
# hai gói, vì dựng môi trường ảo hai lần là thừa và dễ lệch phiên bản.
_LENH_CAI_PY = (
    'D="$HOME/.eide/cong-cu/py"; '
    'test -x "$D/bin/python3" || python3 -m venv "$D"; '
    '"$D/bin/pip" install -q --upgrade pip numpy matplotlib; '
    'echo "da cai vao $D"')

CAN_GI["python-so-lieu"] = [
    {"ten": "numpy", "kiem": "numpy",
     "de_lam_gi": "mô hình chuẩn để đối chiếu kết quả tính của phần cứng",
     "bat_buoc": True, "cach_cai": _LENH_CAI_PY},
    {"ten": "matplotlib", "kiem": "matplotlib",
     "de_lam_gi": "vẽ biểu đồ số chu kỳ theo cấu hình",
     "bat_buoc": False, "cach_cai": _LENH_CAI_PY},
]


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

def _la_sketch_arduino(sketch: Path) -> bool:
    """Chỗ này có phải một sketch Arduino không — hỏi cái THƯ MỤC, không hỏi cái MÁY.

    `arduino-cli compile` chỉ nhận một sketch: một tệp `.ino`, hoặc một thư mục chứa `.ino`
    (theo lệ Arduino thì trùng tên thư mục, nhưng `arduino-cli` nhận rộng hơn).
    """
    if sketch.is_file():
        return sketch.suffix.lower() == ".ino"
    if not sketch.is_dir():
        return False
    return any(sketch.glob("*.ino"))

