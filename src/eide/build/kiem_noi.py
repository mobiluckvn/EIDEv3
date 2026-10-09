# -*- coding: utf-8 -*-
"""Kiểm "NỐI" tĩnh sau biên dịch — M4-13. Cơ chế viết đúng mà đường dẫn tới nó đứt.

## Vì sao tệp này phải tồn tại

Tài liệu đánh giá của chính dự án ghi **bảy lần** cùng một hình dạng
(`DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md` §3.1), và ba trong bảy nằm đúng ở bước nối firmware:

| lần | cơ chế **viết đúng** | đường dẫn tới nó |
|---|---|---|
| 5 | `rtos_tick()` | ô vector SysTick trỏ `Default_Handler` |
| 6 | `PendSV_Handler` nối đúng ô vector | không ai đặt `PENDSVSET` |
| 7 | `RTOS_IDLE_PRIORITY` | không ai tạo tác vụ rỗi |

> **"Không lần nào có lỗi báo ra."**

Và đó là điểm: cả ba **biên dịch sạch**. Agent viết đúng phần khó — bộ lập lịch, chuyển ngữ
cảnh bằng hợp ngữ naked, hàng đợi tĩnh — rồi quên nối nó vào hệ.

## Chỗ kế hoạch nói sai về CƠ CHẾ, đo được 09/10/2026

Kế hoạch ghi luật dò là: *"ô trỏ `Default_Handler` mà trong mã người dùng có định nghĩa **mạnh**
tên `<X>_Handler` (khác địa chỉ)"*. Luật ấy **không bắt được ca #5**, và không bắt được vì một
lý do về cách GNU ld làm việc:

Startup code chuẩn khai `void SysTick_Handler(void) __attribute__((weak, alias("Default_Handler")))`
và bảng vector **tham chiếu chính ký hiệu ấy**. Nên nếu có một định nghĩa **mạnh** cùng tên ở
đâu đó, linker **tự động** lấy nó và ô vector trỏ đúng — tình huống kế hoạch mô tả gần như
không xảy ra được.

Lối hỏng thật là **cái tên**. Dựng lại bằng chuỗi công cụ thật (`arm-none-eabi-gcc 16.2.0`):
`SysTick_handler` — chữ `h` thường, cách `H` đúng một phím — cho ra

    nm:  08000046 W SysTick_Handler      ← cùng địa chỉ Default_Handler, vẫn là alias
    ld:  removing unused section '.text.SysTick_handler'   ← hàm người viết bị XOÁ HẲN

Ảnh nạp vào chip **không có** mã ấy, và `build.compile` báo đạt. Lối thứ hai cùng hậu quả:
handler viết **đúng tên** nhưng khai `static`, nên linker không thấy.

Nên luật ở đây là: ô trỏ `Default_Handler`, **và** trong mã nguồn có một tên **gần giống**
`<X>_Handler` — kể cả giống hệt (ca `static`). Không có tên gần giống thì **im**: phần lớn ô
vector của một dự án thật trỏ `Default_Handler` và đó là **đúng** (không ai viết
`MemManage_Handler`), nên kêu ở đó là kêu mười lăm lần mỗi lần dịch, và cảnh báo thật nằm lẫn
trong đống ấy.
"""

from __future__ import annotations

import re
import shutil
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Đầu ra `objdump -s`: ` 8000000 00000220 49000008 47000008 47000008  ... I...G...G...`
_RE_DUMP = re.compile(r"^\s*([0-9a-f]+)\s+((?:[0-9a-f]{8}\s+){1,4})", re.M)
# `nm`: `08000046 T Default_Handler`
_RE_NM = re.compile(r"^([0-9a-fA-F]+)\s+(\w)\s+(\S+)\s*$", re.M)
# `--print-gc-sections`: `…ld: removing unused section '.text.X' in file 'Y'`
_RE_GC = re.compile(r"removing unused section '(?P<sec>[^']+)' in file '(?P<tep>[^']*)'")
# Hàm chỉ trả hằng: đúng một lệnh nạp hằng vào r0, rồi `bx lr`.
_RE_HAM_DIS = re.compile(r"^[0-9a-f]+\s+<([^>]+)>:\s*$")
_RE_MOV_HANG = re.compile(r"\b(?:movs?|mov\.w)\s+r0,\s*#(\d+)")
_RE_BX_LR = re.compile(r"\bbx\s+lr\b")

# Ô vector KHÔNG kêu dù trỏ `Default_Handler`: không ai viết chúng, và đó là bình thường.
# (Giữ danh sách để lớp trên đọc được; phép lọc chính vẫn là "có tên gần giống hay không".)
_O_BINH_THUONG = frozenset({
    "NMI_Handler", "HardFault_Handler", "MemManage_Handler", "BusFault_Handler",
    "UsageFault_Handler", "DebugMon_Handler",
})

# Thứ tự 16 ô đầu của bảng vector Cortex-M (ARMv7-M §B1.5.2). Ô 7–10 và 13 là dự trữ.
TEN_O_CORTEX_M = (
    "_estack", "Reset_Handler", "NMI_Handler", "HardFault_Handler", "MemManage_Handler",
    "BusFault_Handler", "UsageFault_Handler", "", "", "", "", "SVC_Handler",
    "DebugMon_Handler", "", "PendSV_Handler", "SysTick_Handler",
)


@dataclass(slots=True)
class IsrBoQuen:
    o: int
    ten: str
    dia_chi: int
    gan_giong: str = ""
    vi_sao: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"o": self.o, "ten": self.ten, "dia_chi": f"0x{self.dia_chi:08X}",
                "gan_giong": self.gan_giong, "vi_sao": self.vi_sao}


@dataclass(slots=True)
class HamTraHang:
    ten: str
    gia_tri: int

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.ten, "gia_tri": self.gia_tri}


# =========================================================================== đọc
def doc_vector(dump: str) -> list[tuple[int, int]]:
    """Đầu ra `objdump -s -j .isr_vector` → `[(chỉ số ô, địa chỉ)]`.

    **Gỡ bit Thumb** (bit 0). Mọi con trỏ hàm trên Cortex-M mang bit ấy bằng 1, nên không gỡ
    thì mọi địa chỉ lệch một và phép so *"ô này có trỏ `Default_Handler` không"* trượt hết —
    im lặng, và theo chiều "không thấy gì".
    """
    byte = bytearray()
    for m in _RE_DUMP.finditer(dump or ""):
        for tu in m.group(2).split():
            # `objdump -s` in từng từ 32 bit theo thứ tự byte của tệp (little-endian).
            byte += bytes.fromhex(tu)
    ra: list[tuple[int, int]] = []
    for i in range(len(byte) // 4):
        (v,) = struct.unpack_from("<I", byte, i * 4)
        ra.append((i, v & ~1 if i else v))     # ô 0 là con trỏ ngăn xếp, không có bit Thumb
    return ra


def doc_nm(chu: str) -> dict[str, tuple[int, str]]:
    """`nm` → `{tên: (địa chỉ, loại)}`.

    Giữ **loại**: `W` (weak) và `T` (strong) nói hai chuyện khác nhau, và chính chỗ ấy phân
    biệt một handler đã nối với một handler còn là alias của `Default_Handler`.
    """
    ra: dict[str, tuple[int, str]] = {}
    for m in _RE_NM.finditer(chu or ""):
        ra[m.group(3)] = (int(m.group(1), 16), m.group(2))
    return ra


# =========================================================================== luật
def _chuan(x: str) -> str:
    return x.replace("_", "").lower()


def _tim_gan_giong(ten: str, nguon_chu: str) -> str:
    """Tên trong MÃ NGUỒN gần giống `ten` — kể cả giống hệt.

    Giống hệt vẫn tính, và đó là ca `static`: tên khớp hoàn toàn nhưng linker không thấy ký
    hiệu, nên ô vector giữ `Default_Handler`. Hai lối hỏng khác nhau, một hậu quả.
    """
    muc = _chuan(ten)
    for m in re.finditer(r"\b(\w*_?[Hh]andler|\w+_vect)\b", nguon_chu or ""):
        if _chuan(m.group(1)) == muc:
            return m.group(1)
    return ""


def isr_bi_bo_quen(vector: list[tuple[int, int]], syms: dict[str, tuple[int, str]],
                   nguon_chu: str) -> list[IsrBoQuen]:
    """Ô vector trỏ `Default_Handler` **và** mã nguồn có một tên gần giống.

    Hai vế, và vế thứ hai là vế giữ cho cảnh báo còn nghĩa: phần lớn ô vector của một dự án
    thật trỏ `Default_Handler` một cách **đúng đắn**.
    """
    dh = syms.get("Default_Handler")
    if dh is None:
        return []
    dia_chi_dh = dh[0] & ~1
    ra: list[IsrBoQuen] = []
    for i, dia_chi in vector:
        if i == 0 or dia_chi == 0 or (dia_chi & ~1) != dia_chi_dh:
            continue
        ten = TEN_O_CORTEX_M[i] if i < len(TEN_O_CORTEX_M) else f"IRQ{i - 16}"
        # Ô dự trữ (7–10, 13) có tên rỗng trong bảng, và chúng rơi ở vế dưới: biểu
        # thức tên handler đòi ít nhất chữ `handler`, nên tên rỗng không khớp nổi một
        # ký hiệu nào. Một cửa riêng cho chúng ở đây là mã CHẾT — phép phá chỉ ra điều
        # đó (DEV-362): xoá cửa ấy không đổi một kết quả nào.
        gan = _tim_gan_giong(ten, nguon_chu)
        if not gan:
            continue
        loai = (syms.get(ten) or (0, "?"))[1]
        ra.append(IsrBoQuen(
            o=i, ten=ten, dia_chi=dia_chi, gan_giong=gan,
            vi_sao=(f"ô {i} của bảng vector trỏ `Default_Handler`, nhưng mã nguồn có "
                    f"`{gan}`"
                    + (" — khác `" + ten + "` ở cách viết, nên linker giữ alias yếu và hàm "
                       "bạn viết KHÔNG BAO GIỜ chạy" if gan != ten else
                       " — tên khớp mà linker không thấy ký hiệu (khai `static`?), nên ô "
                       "vector giữ alias yếu")
                    + f". Ký hiệu `{ten}` hiện là loại `{loai}`.")))
    return ra


def ham_bi_loai(log_link: str) -> list[str]:
    """Hàm bị linker loại vì không ai gọi — đọc log `--print-gc-sections`.

    Chỉ nhận section `.text.*` (bỏ `.rodata`/`.bss`: bỏ một hằng không dùng là chuyện bình
    thường, không phải lỗi nối), và bỏ tệp trong `vendor/` — kế hoạch cấm quét nó.
    """
    ra: list[str] = []
    for m in _RE_GC.finditer(log_link or ""):
        sec, tep = m.group("sec"), m.group("tep")
        if not sec.startswith(".text."):
            continue
        if "vendor/" in tep or "/vendor/" in tep:
            continue
        ten = sec[len(".text."):]
        if ten and ten not in ra:
            ra.append(ten)
    return ra


def ham_tra_hang(dis: str) -> list[HamTraHang]:
    """Hàm mà cả thân chỉ là *"nạp một hằng vào r0 rồi về"* — một hàm chưa viết xong.

    `target.debug` đã có cảnh báo này, nhưng **chỉ khi chạy trên chip** (`tools/mach_that.py`).
    Nhìn thấy nó ở bước dịch thì không cần cắm bo.

    Bỏ `main` và mọi `*_Handler`: `main(){return 0;}` và một handler rỗng có **đúng** hình dạng
    ấy, mà cả hai là chuyện thường. Kêu chúng lên là kêu ở mọi dự án, và cảnh báo mất nghĩa.
    """
    ra: list[HamTraHang] = []
    ten = ""
    lenh: list[str] = []

    def _chot() -> None:
        if not ten or ten == "main" or ten.endswith(("_Handler", "_handler")):
            return
        if len(lenh) == 2 and _RE_BX_LR.search(lenh[1]):
            m = _RE_MOV_HANG.search(lenh[0])
            if m:
                ra.append(HamTraHang(ten=ten, gia_tri=int(m.group(1))))

    for dong in (dis or "").splitlines():
        m = _RE_HAM_DIS.match(dong)
        if m:
            _chot()
            ten, lenh = m.group(1), []
            continue
        if ten and dong.strip():
            lenh.append(dong)
    _chot()
    return ra


# =========================================================================== chạy thật
_TIEN_TO = {"arm": "arm-none-eabi-", "arm32": "arm-none-eabi-", "cortex-m": "arm-none-eabi-"}


def kiem_noi_tu_elf(elf: Path, *, isa: str = "arm", nguon_chu: str = "",
                    log_link: str = "") -> dict[str, Any]:
    """Đọc một ELF đã dựng và trả ba danh sách.

    Kiến trúc khác Cortex-M thì `ho_tro=False` kèm lý do — **không** trả rỗng im lặng. AVR và
    RISC-V không có `.isr_vector` kiểu này, và một kết quả rỗng ở đó sẽ được đọc là *"nối đúng
    hết"*, đúng cái N6 cấm.
    """
    rong: dict[str, Any] = {"ho_tro": False, "vi_sao": "", "so_o_vector": 0,
                            "isr_bo_quen": [], "ham_bi_loai": [], "ham_tra_hang": []}
    tien_to = _TIEN_TO.get((isa or "").lower())
    if tien_to is None:
        rong["vi_sao"] = (f"chưa hỗ trợ kiến trúc `{isa}` — bảng vector kiểu `.isr_vector` là "
                          "của Cortex-M; AVR và RISC-V nối ngắt theo cách khác")
        return rong
    if not Path(elf).is_file():
        rong["vi_sao"] = f"không có tệp ảnh `{Path(elf).name}` để đọc"
        return rong
    for cc in ("objdump", "nm"):
        if not shutil.which(tien_to + cc):
            rong["vi_sao"] = f"thiếu `{tien_to}{cc}` trên máy này"
            return rong

    def _chay(ten: str, *co: str) -> str:
        r = subprocess.run([tien_to + ten, *co, str(elf)], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""

    dump = _chay("objdump", "-s", "-j", ".isr_vector")
    if not dump.strip():
        rong["vi_sao"] = ("ảnh này không có section `.isr_vector` — có thể là ảnh của một "
                          "kiến trúc khác, hoặc script liên kết đặt tên section khác")
        return rong
    vector = doc_vector(dump)
    syms = doc_nm(_chay("nm"))
    bo_quen = isr_bi_bo_quen(vector, syms, nguon_chu)
    tra_hang = ham_tra_hang(_chay("objdump", "-d"))
    return {"ho_tro": True, "vi_sao": "", "so_o_vector": len(vector),
            "isr_bo_quen": [x.to_dict() for x in bo_quen],
            "ham_bi_loai": ham_bi_loai(log_link),
            "ham_tra_hang": [x.to_dict() for x in tra_hang]}
