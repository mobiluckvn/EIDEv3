# -*- coding: utf-8 -*-
"""Mạch thật: dò bo, nạp firmware, đọc log. MDD-40 §G7, ca TC029–TC037.

Ba nguyên tắc của tệp này, và mỗi cái đến từ một dòng cụ thể trong bảng ca kiểm:

1. **Không báo nạp thành công giả** (TC032). `dat=True` chỉ khi có bằng chứng ĐỌC ĐƯỢC: bo
   nhận lại ổ đĩa và không có `FAIL.TXT`, hoặc trình nạp SWD báo verify khớp. Sao xong một
   tệp *không* phải bằng chứng — ST-LINK kiểu ổ đĩa nhận tệp rồi mới quyết định từ chối.

2. **Đối chiếu chip trước khi nạp** (TC034). Với bo nạp kiểu ổ đĩa thì **không đọc được ID
   chip** — chỉ đọc được tên ổ do firmware ST-LINK khai (`DIS_F469NI`). Đó là bằng chứng về
   *bo*, không phải về *silicon*, và tệp này nói đúng như thế thay vì làm tròn lên. Muốn đối
   chiếu ID chip thật thì cần `st-info`/`openocd`, và khi thiếu thì nói ra để người dùng
   quyết định — không tự bỏ qua phép kiểm.

3. **Không đoán khi không thấy gì** (TC032). Không có bo thì trả về danh sách kiểm tra đủ bốn
   mục mà đề bài đòi: nguồn, cáp, driver, chân BOOT/NRST.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Nơi macOS gắn ổ đĩa ngoài. Bo ST-LINK/DAPLink hiện ra ở đây như một ổ USB.
THU_MUC_O_DIA = Path("/Volumes")
# Nơi có tệp thiết bị của cổng nối tiếp. Là hằng số (không viết thẳng trong hàm) để bộ kiểm
# trỏ được sang thư mục giả — nếu không, phép phân loại cổng chỉ kiểm được bằng cách chép lại
# chính nó vào test, và khi đó test xanh kể cả khi hàm thật sai.
THU_MUC_DEV = Path("/dev")

# Bo tự gắn lại ổ đĩa sau khi ghi xong; đợi bấy nhiêu giây cho việc đó. Là hằng số của
# mô-đun để bộ kiểm rút ngắn được — một ca kiểm chờ 25 giây thật sẽ bị người ta bỏ chạy.
CHO_GAN_LAI_GIAY = 25.0

# Tệp do firmware của bộ nạp để lại — đây là cách nó NÓI kết quả, không phải chỗ ta đoán.
TEP_KET_QUA = ("FAIL.TXT", "fail.txt")
TEP_NHAN_DANG = ("DETAILS.TXT", "MBED.HTM", "INFO_UF2.TXT")

# Tên ổ đĩa mà firmware ST-LINK/DAPLink khai → bo nào. Chỉ những tiền tố hãng đặt.
# `DIS_` = Discovery, `NOD_` = Nucleo. Phần sau là mã chip viết gọn, ví dụ `F469NI`.
_TIEN_TO_BO = {"DIS_": "Discovery", "NOD_": "Nucleo", "NUCLEO": "Nucleo"}

# Cổng nối tiếp trông như một bo cắm qua USB. Tên do driver đặt: `usbmodem` là USB CDC (ST-LINK
# VCP, Arduino), `usbserial`/`wchusbserial`/`SLAB_USBtoUART` là chip chuyển USB-UART rời.
_CONG_CO_THE_LA_BO = ("usbmodem", "usbserial", "wchusbserial", "SLAB_USBtoUART", "usbmodemf")

# Cổng luôn có mặt trên macOS và chắc chắn không phải bo. Chúng vẫn được LIỆT KÊ (im lặng bỏ
# thì người dùng không hiểu vì sao cổng họ thấy trong Terminal lại không có ở đây), nhưng
# được gắn nhãn để tác tử không đi đọc log từ một cái tai nghe.
_CONG_KHONG_PHAI_BO = ("Bluetooth", "debug-console")


@dataclass(slots=True)
class BoTimDuoc:
    """Một thứ có thể là bo, kèm ĐÃ BIẾT GÌ về nó và biết bằng cách nào."""

    loai: str                       # o_dia | cong_noi_tiep | swd
    duong_dan: str
    ten: str = ""
    bo_doan: str = ""               # tên bo suy từ nhãn ổ, rỗng nếu không suy được
    chip_doan: str = ""             # mã chip suy từ nhãn ổ — CHƯA phải ID chip đọc từ silicon
    chip_doc_duoc: str = ""         # ID chip đọc THẬT qua SWD, rỗng nếu chưa đọc
    nap_duoc_bang: str = ""         # sao_tep | st-flash | openocd
    co_the_la_bo: bool = True       # False cho cổng chắc chắn không phải bo (tai nghe, v.v.)
    chi_tiet: dict[str, str] = field(default_factory=dict)
    biet_bang_cach: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"loai": self.loai, "duong_dan": self.duong_dan, "ten": self.ten,
                "bo_doan": self.bo_doan, "chip_doan": self.chip_doan,
                "chip_doc_duoc": self.chip_doc_duoc, "nap_duoc_bang": self.nap_duoc_bang,
                "co_the_la_bo": self.co_the_la_bo,
                "chi_tiet": dict(self.chi_tiet), "biet_bang_cach": self.biet_bang_cach}


DANH_SACH_KIEM_TRA = [
    "Nguồn: bo có đèn nguồn sáng không? Cáp USB cắm vào cổng ST-LINK (CN1), không phải cổng "
    "USB OTG của bo.",
    "Cáp: thử một cáp USB khác — nhiều cáp chỉ có hai dây nguồn, không có dây dữ liệu.",
    "Driver / quyền: máy có thấy thiết bị USB nào mới khi cắm vào không? Trên macOS thử "
    "`ls /dev/cu.*` trước và sau khi cắm.",
    "Chân BOOT/NRST: BOOT0 có bị kéo lên làm chip vào bootloader không? Thử bấm nút RESET, "
    "hoặc nạp ở chế độ connect-under-reset.",
]


def _nhan_o_dia(p: Path) -> BoTimDuoc | None:
    """Một ổ đĩa có phải bộ nạp kiểu mass-storage không, và nó khai gì về mình."""
    try:
        co = [t for t in TEP_NHAN_DANG if (p / t).exists()]
    except OSError:
        return None
    if not co:
        return None
    b = BoTimDuoc(loai="o_dia", duong_dan=str(p), ten=p.name,
                  nap_duoc_bang="sao_tep",
                  biet_bang_cach=f"ổ đĩa có {', '.join(co)} → firmware bộ nạp kiểu "
                                 "mass-storage (ST-LINK/DAPLink/mbed)")
    for t in co:
        try:
            b.chi_tiet[t] = (p / t).read_text("utf-8", errors="replace")[:400].strip()
        except OSError:
            pass
    nhan = p.name.upper()
    for tien_to, ho in _TIEN_TO_BO.items():
        if nhan.startswith(tien_to):
            duoi = nhan[len(tien_to):].strip("_")
            b.bo_doan = f"ST {ho} {duoi}"
            # `DIS_F469NI` → `STM32F469NI`. Đây là suy từ NHÃN Ổ, không phải đọc từ chip.
            if re.fullmatch(r"[FLGHWU]\d[0-9A-Z]{2,6}", duoi):
                b.chip_doan = "STM32" + duoi
            break
    return b


def _cong_noi_tiep() -> list[BoTimDuoc]:
    ra: list[BoTimDuoc] = []
    for p in sorted(THU_MUC_DEV.glob("cu.*")):
        ten = p.name
        if any(x in ten for x in _CONG_KHONG_PHAI_BO):
            vi_sao, la_bo = "cổng cố định của macOS, không phải thiết bị cắm ngoài", False
        elif any(x in ten for x in _CONG_CO_THE_LA_BO):
            vi_sao, la_bo = ("tên có “"
                             + next(x for x in _CONG_CO_THE_LA_BO if x in ten)
                             + "” → cổng USB nối tiếp của một thiết bị cắm ngoài"), True
        else:
            # Tai nghe Bluetooth cũng hiện ra ở /dev/cu.* — đọc log từ nó thì vừa vô nghĩa
            # vừa mất thời gian, và "không thấy chữ nào" sẽ bị hiểu thành firmware chạy sai.
            vi_sao, la_bo = ("không nhận ra là cổng USB — có thể là thiết bị Bluetooth đã "
                             "ghép đôi"), False
        # Cổng USB nối tiếp LÀ một đường nạp — qua bootloader, bằng avrdude. Trước đây trường
        # này để trống nên `do_bo()` kết luận "KHÔNG có đường nạp nào" với một bo Arduino đang
        # cắm hẳn hoi, và tác tử không có cách nào nạp.
        #
        # Nói "có đường nạp" KHÔNG phải nói "có chip": cổng này là con chip cầu USB, nó vẫn
        # hiện ra kể cả khi đã nhổ ATmega khỏi đế. Muốn biết có chip thì phải bắt tay với
        # bootloader — `doc_chu_ky_avr()`, và việc ấy reset bo.
        nap_bang = "avrdude" if la_bo and tim_avrdude()[0] else ""
        ra.append(BoTimDuoc(loai="cong_noi_tiep", duong_dan=str(p), ten=ten,
                            co_the_la_bo=la_bo, nap_duoc_bang=nap_bang,
                            biet_bang_cach=f"/dev/{ten}: {vi_sao}"
                                           + (" · nạp được qua bootloader bằng avrdude "
                                              "(chưa đọc chữ ký chip — việc ấy reset bo)"
                                              if nap_bang else "")))
    return ra


def doc_id_chip() -> tuple[str, str, dict[str, int]]:
    """Chip đọc qua SWD bằng `st-info`. Trả `(tên chip, vì sao không đọc được, bộ nhớ)`.

    Đây là phép kiểm mà TC034 đòi: firmware cho F103 nạp vào bo F401 phải bị dừng TRƯỚC khi
    nạp. Không có `st-info` thì không đọc được, và khi đó phải nói "chưa đọc được" — không
    được lấy tên ổ đĩa rồi trình bày nó như thể đã đọc từ silicon.

    Thứ tự đọc có chủ ý: **`dev-type` trước `chipid`**. `st-info --probe` in cả hai —
    `chipid: 0x434` và `dev-type: STM32F46x_F47x` — và chỉ cái sau là thứ so được với mã chip
    trong hộ chiếu. Bản trước đọc `chipid`, nên phép đối chiếu nhận được chuỗi `chipid 0x434`,
    không khớp `STM32F469NI`, và **chặn việc nạp bằng một báo động giả** — đúng loại cảnh báo
    dạy người dùng bỏ qua cảnh báo.

    Lấy luôn `flash`/`sram`: đó là số đọc từ chính con chip đang cắm, chắc hơn mọi con số
    trích từ tài liệu bằng biểu thức chính quy.
    """
    st = shutil.which("st-info")
    if not st:
        return "", "máy chưa có `st-info` (gói `stlink`) nên không đọc được ID chip qua SWD", {}
    try:
        r = subprocess.run([st, "--probe"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return "", f"gọi st-info thất bại: {type(e).__name__}: {e}", {}
    out = (r.stdout or "") + (r.stderr or "")

    bo_nho: dict[str, int] = {}
    for khoa in ("flash", "sram"):
        m = re.search(rf"^\s*{khoa}:\s*(\d+)", out, re.M)
        if m:
            bo_nho[khoa] = int(m.group(1))

    for mau in (r"^\s*dev-type:\s*(\S+)", r"^\s*descr:\s*(.+)$"):
        m = re.search(mau, out, re.M)
        if m:
            return m.group(1).strip(), "", bo_nho
    m = re.search(r"chipid:\s*(0x[0-9a-fA-F]+)", out)
    if m:
        # Chỉ có mã số: đọc được bo nhưng KHÔNG suy ra được tên chip. Nói đúng như thế.
        return "", (f"st-info chỉ đọc được mã `chipid {m.group(1)}` mà không có `dev-type`, "
                    "nên chưa suy ra được tên chip để đối chiếu"), bo_nho
    return "", ("st-info chạy xong nhưng không thấy bo nào: "
                + " ".join(out.split())[:200]), bo_nho


# =========================================================================== AVR qua bootloader
#
# Trước khối này, cả đường nạp của EIDE chỉ biết ST-LINK: `st-flash` và ổ đĩa MSD của bo
# Discovery/Nucleo. Bo robot MOBILUCK là bo đầu tiên không phải họ ST — Arduino Nano,
# ATmega328P, nạp qua bootloader trên cổng USB-nối tiếp — và tác tử **không có đường nào để
# nạp nó**. Nó biên dịch được (`build.compile` gọi `avr-gcc`) rồi dừng ở đó.
#
# Anh Công: *"Phải để agent làm chứ. Sai thì fix cho agent thông minh hơn."*
#
# Một chỗ phải cẩn thận: mọi thao tác avrdude đều **reset bo** qua đường DTR. Với bo đang chạy
# firmware cân bằng thì reset là robot ngã. Nên phép dò chữ ký chip KHÔNG tự chạy trong
# `do_bo()`; nó là một lựa chọn tác tử phải nêu ra và nói cho người biết.

# Chữ ký ba byte đọc từ silicon → tên chip. Chỉ những chip thật sự gặp; thêm chip mới thì
# thêm dòng, đừng đoán theo mẫu.
_CHU_KY_AVR = {
    "1e950f": "ATmega328P", "1e9514": "ATmega328",  "1e9516": "ATmega328PB",
    "1e9507": "ATmega8",    "1e9306": "ATmega8515", "1e9403": "ATmega16",
    "1e9702": "ATmega1280", "1e9801": "ATmega2560", "1e9587": "ATmega32U4",
}

# Tên chip → mã `-p` của avrdude.
_MA_AVRDUDE = {
    "ATmega328P": "m328p", "ATmega328": "m328", "ATmega328PB": "m328pb",
    "ATmega2560": "m2560", "ATmega1280": "m1280", "ATmega32U4": "m32u4",
    "ATmega8": "m8", "ATmega16": "m16", "ATmega8515": "m8515",
}
# Mọi chip đọc được chữ ký đều phải có mã để nạp — đọc ra tên rồi bảo "không biết nạp thế
# nào" là một ngõ cụt tự mình đào. Có ca kiểm canh đúng bất biến này.

# Nơi tìm avrdude, theo thứ tự ưu tiên. Bản của Arduino đi kèm tệp cấu hình riêng và biết
# những bo mà bản Homebrew không có.
_ARDUINO_AVRDUDE = Path.home() / "Library/Arduino15/packages/arduino/tools/avrdude"


def tim_avrdude() -> tuple[str, str, str]:
    """`(đường dẫn avrdude, đường dẫn avrdude.conf, vì sao không có)`.

    Bản Arduino đi trước bản hệ thống: nó kèm `avrdude.conf` khớp với lõi `arduino:avr` mà
    `build.compile` dùng để biên dịch. Hai bản khác phiên bản thì bảng chip cũng khác, và sự
    khác ấy chỉ lộ ra đúng lúc nạp.
    """
    try:
        thu_muc = sorted(_ARDUINO_AVRDUDE.iterdir(), reverse=True) if \
            _ARDUINO_AVRDUDE.is_dir() else []
    except OSError:
        thu_muc = []
    for d in thu_muc:
        exe, conf = d / "bin" / "avrdude", d / "etc" / "avrdude.conf"
        if exe.is_file():
            return str(exe), (str(conf) if conf.is_file() else ""), ""
    he_thong = shutil.which("avrdude")
    if he_thong:
        return he_thong, "", ""
    return "", "", ("máy chưa có `avrdude` — cài bằng `brew install avrdude`, hoặc cài lõi "
                    "`arduino:avr` bằng `arduino-cli core install arduino:avr`")


def _lenh_avrdude(exe: str, conf: str, ma_chip: str, cong: str, baud: int,
                  *lenh: str) -> list[str]:
    c = [exe]
    if conf:
        c += ["-C", conf]
    return c + ["-p", ma_chip, "-c", "arduino", "-P", cong, "-b", str(baud), *lenh]


def doc_chu_ky_avr(cong: str, *, ma_chip: str = "m328p", baud: int = 57600,
                   timeout: float = 30.0) -> tuple[str, str, str]:
    """Đọc chữ ký ba byte TỪ SILICON qua bootloader. `(tên chip, chữ ký, vì sao không đọc)`.

    Đây là phép đo thật, khác hẳn việc nhìn thấy một cổng `/dev/cu.usbserial-*`: cổng ấy là
    con chip cầu USB (CH340/FTDI), nó vẫn hiện ra kể cả khi ai đó đã nhổ con ATmega ra khỏi
    đế. Chỉ khi bắt tay được với bootloader mới biết có chip và chip nào.

    **Thao tác này RESET bo** — avrdude kéo DTR để đưa chip vào bootloader. Người gọi phải
    biết điều đó và nói cho người dùng.
    """
    exe, conf, thieu = tim_avrdude()
    if not exe:
        return "", "", thieu
    try:
        # `-v` là bắt buộc, không phải để cho đẹp: avrdude **8.0 im lặng** ở mức mặc định —
        # nó bắt tay xong, in đúng một dòng "Avrdude done. Thank you." và KHÔNG in chữ ký.
        # Đo được trên bo thật: lần đầu bài này báo "không đọc được chữ ký" cho một con
        # ATmega328P hoàn toàn khoẻ mạnh, chỉ vì thiếu một chữ `v`.
        r = subprocess.run(_lenh_avrdude(exe, conf, ma_chip, cong, baud, "-n", "-v"),
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        return "", "", f"gọi avrdude thất bại: {type(e).__name__}: {e}"
    out = ((r.stdout or "") + (r.stderr or ""))
    ky = _chu_ky_tu_dau_ra(out)
    if not ky:
        return "", "", ("avrdude không đọc được chữ ký chip: "
                        + " ".join(out.split())[-220:])
    return _CHU_KY_AVR.get(ky, ""), ky, ("" if ky in _CHU_KY_AVR else
                                         f"chữ ký {ky} chưa có trong bảng chip đã biết")


# Ba phiên bản avrdude in chữ ký ba kiểu khác nhau. Dò cả ba, dài trước ngắn.
#
#   6.x (Arduino cũ)  Device signature = 0x1e950f
#   7.x (Homebrew)    Device signature = 0x1e 0x95 0x0f
#   8.x (Arduino nay) Device signature = 1E 95 0F (ATmega328P, ATA6614Q, LGT8F328P)
#
# Đây đúng loại khác biệt chỉ lộ ra khi cắm bo thật: cả ba đều "chạy xong", chỉ khác chỗ in.
_MAU_CHU_KY = (
    re.compile(r"[Dd]evice signature\s*=\s*0x([0-9a-fA-F]{6})"),
    re.compile(r"[Dd]evice signature\s*=\s*0x([0-9a-fA-F]{2})\s+0x([0-9a-fA-F]{2})"
               r"\s+0x([0-9a-fA-F]{2})"),
    re.compile(r"[Dd]evice signature\s*=\s*([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})"
               r"\s+([0-9a-fA-F]{2})"),
)


def _chu_ky_tu_dau_ra(out: str) -> str:
    for mau in _MAU_CHU_KY:
        m = mau.search(out)
        if m:
            return "".join(m.groups()).lower()
    return ""


def _hex_tu_elf(elf: Path) -> tuple[Path | None, str]:
    """`.elf` → `.hex` bằng `avr-objcopy`. avrdude nhận ELF nhưng không mọi phiên bản."""
    oc = shutil.which("avr-objcopy")
    if not oc:
        for d in (sorted((Path.home() / "Library/Arduino15/packages/arduino/tools/avr-gcc")
                         .iterdir(), reverse=True)
                  if (Path.home() / "Library/Arduino15/packages/arduino/tools/avr-gcc").is_dir()
                  else []):
            x = d / "bin" / "avr-objcopy"
            if x.is_file():
                oc = str(x)
                break
    if not oc:
        return None, "máy chưa có `avr-objcopy` để đổi .elf thành .hex"
    ra = elf.with_suffix(".hex")
    try:
        r = subprocess.run([oc, "-O", "ihex", "-R", ".eeprom", str(elf), str(ra)],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"avr-objcopy thất bại: {type(e).__name__}: {e}"
    if r.returncode != 0 or not ra.is_file():
        return None, f"avr-objcopy trả mã {r.returncode}: {(r.stderr or '')[:160]}"
    return ra, ""


def nap_qua_avrdude(anh: Path, cong: str, *, ma_chip: str = "m328p", baud: int = 57600,
                    timeout: float = 300.0) -> KetQuaNap:
    """Nạp `.hex` (hoặc `.elf`, tự đổi) vào AVR qua bootloader, rồi đọc ngược để so.

    avrdude có `-U flash:w:...:i` tự verify và in `verified`. Không thấy dòng ấy thì **không
    coi là nạp xong**, dù mã thoát bằng 0 — cùng một luật với đường `st-flash`.
    """
    kq = KetQuaNap(cach="avrdude", dich=f"{cong} @ {baud} baud")
    exe, conf, thieu = tim_avrdude()
    if not exe:
        kq.vi_sao_khong_dat = thieu
        return kq
    if not anh.exists() or anh.stat().st_size == 0:
        kq.vi_sao_khong_dat = f"Không có tệp {anh.name} hợp lệ để nạp."
        return kq

    tep_nap = anh
    if anh.suffix.lower() == ".elf":
        tep_nap_moi, vi_sao = _hex_tu_elf(anh)
        if tep_nap_moi is None:
            kq.vi_sao_khong_dat = vi_sao
            return kq
        tep_nap = tep_nap_moi
        kq.canh_bao.append(f"Đã đổi {anh.name} thành {tep_nap.name} để nạp.")

    kq.tep = tep_nap.name
    kq.so_byte = tep_nap.stat().st_size
    kq.hash = _hash_tep(tep_nap)

    t0 = time.time()
    try:
        r = subprocess.run(
            _lenh_avrdude(exe, conf, ma_chip, cong, baud,
                          "-D", "-U", f"flash:w:{tep_nap}:i"),
            capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        kq.giay = time.time() - t0
        kq.vi_sao_khong_dat = f"avrdude không chạy được: {type(e).__name__}: {e}"
        return kq
    kq.giay = time.time() - t0
    kq.nguyen_van = ((r.stdout or "") + (r.stderr or "")).strip()
    kq.da_verify = "verified" in kq.nguyen_van.lower()
    if r.returncode != 0:
        kq.vi_sao_khong_dat = (
            f"avrdude trả mã {r.returncode}. Nếu nó dừng giữa lúc ghi thì Flash đang ở trạng "
            "thái KHÔNG nhất quán — nạp lại. Hay gặp nhất: sai tốc độ bootloader (bo cũ dùng "
            "57600, bo mới 115200), hoặc một chương trình khác đang giữ cổng nối tiếp.")
        return kq
    if not kq.da_verify:
        kq.vi_sao_khong_dat = ("avrdude trả mã 0 nhưng KHÔNG in dòng verify. Không coi là nạp "
                               "xong — đọc nguyên văn đầu ra.")
        return kq
    kq.dat = True
    return kq


def doc_nguoc_avr(anh: Path, cong: str, *, ma_chip: str = "m328p", baud: int = 57600,
                  timeout: float = 300.0) -> dict[str, Any]:
    """Đọc ngược Flash TỪ CHIP rồi so từng byte với tệp đã nạp.

    avrdude đã tự verify lúc ghi, nhưng đó là verify của chính công cụ vừa ghi. Đọc lại bằng
    một lượt riêng rồi so ở đây là bằng chứng độc lập — cùng lý do `target.verify` tồn tại cho
    đường ST-LINK.
    """
    import tempfile

    ra: dict[str, Any] = {"dat": False, "vi_sao": "", "so_byte_doc": 0, "so_byte_tep": 0}
    exe, conf, thieu = tim_avrdude()
    if not exe:
        ra["vi_sao"] = thieu
        return ra
    goc = anh
    if anh.suffix.lower() == ".elf":
        goc_moi, vi_sao = _hex_tu_elf(anh)
        if goc_moi is None:
            ra["vi_sao"] = vi_sao
            return ra
        goc = goc_moi
    if not goc.is_file():
        ra["vi_sao"] = f"không có {goc.name} để so"
        return ra

    with tempfile.TemporaryDirectory() as d:
        doc = Path(d) / "doc-nguoc.hex"
        try:
            r = subprocess.run(
                _lenh_avrdude(exe, conf, ma_chip, cong, baud, "-U", f"flash:r:{doc}:i"),
                capture_output=True, text=True, timeout=timeout)
        except (OSError, subprocess.SubprocessError) as e:
            ra["vi_sao"] = f"đọc ngược thất bại: {type(e).__name__}: {e}"
            return ra
        if r.returncode != 0 or not doc.is_file():
            ra["vi_sao"] = ("avrdude đọc ngược trả mã "
                            f"{r.returncode}: {' '.join((r.stderr or '').split())[-200:]}")
            return ra
        a, b = _byte_tu_ihex(goc), _byte_tu_ihex(doc)

    ra["so_byte_tep"], ra["so_byte_doc"] = len(a), len(b)
    if not a:
        ra["vi_sao"] = "không đọc được byte nào từ tệp nguồn"
        return ra
    # Chip luôn đọc ra ĐỦ dung lượng Flash, phần sau chương trình là 0xFF. So đúng phần
    # chương trình; so cả vùng trống sẽ báo lệch ở mọi lần nạp đúng.
    lech = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    ra["so_byte_lech"] = len(lech)
    ra["byte_lech_dau"] = lech[:8]
    ra["dat"] = not lech and len(b) >= len(a)
    if not ra["dat"]:
        ra["vi_sao"] = (f"{len(lech)} byte khác nhau giữa tệp và thứ đọc từ chip"
                        if lech else
                        f"chip chỉ đọc được {len(b)} byte, ít hơn tệp ({len(a)})")
    return ra


def _byte_tu_ihex(p: Path) -> bytes:
    """Đọc Intel HEX thành byte theo địa chỉ. Bỏ qua dòng hỏng thay vì ném ngoại lệ."""
    vung: dict[int, int] = {}
    nen = 0
    try:
        dong = p.read_text("utf-8", errors="replace").splitlines()
    except OSError:
        return b""
    for d in dong:
        d = d.strip()
        if not d.startswith(":") or len(d) < 11:
            continue
        try:
            n = int(d[1:3], 16)
            dia = int(d[3:7], 16)
            loai = int(d[7:9], 16)
            than = bytes.fromhex(d[9:9 + n * 2])
        except ValueError:
            continue
        if loai == 0:
            for i, x in enumerate(than):
                vung[nen + dia + i] = x
        elif loai == 4 and len(than) == 2:
            nen = int.from_bytes(than, "big") << 16
        elif loai == 2 and len(than) == 2:
            nen = int.from_bytes(than, "big") << 4
        elif loai == 1:
            break
    if not vung:
        return b""
    het = max(vung)
    return bytes(vung.get(i, 0xFF) for i in range(het + 1))


def do_bo() -> dict[str, Any]:
    """Máy này đang cắm những gì. Không thấy gì thì trả danh sách kiểm tra, không đoán."""
    ds: list[BoTimDuoc] = []
    try:
        o_dia = sorted(THU_MUC_O_DIA.iterdir())
    except OSError:
        o_dia = []
    for p in o_dia:
        b = _nhan_o_dia(p)
        if b is not None:
            ds.append(b)
    ds += _cong_noi_tiep()

    chip, vi_sao_chip, bo_nho = doc_id_chip()
    if chip or bo_nho:
        ds.append(BoTimDuoc(
            loai="swd", duong_dan="(SWD qua ST-LINK)", ten=chip or "(chưa rõ tên chip)",
            chip_doc_duoc=chip, nap_duoc_bang="st-flash",
            chi_tiet={k: str(v) for k, v in bo_nho.items()},
            biet_bang_cach="st-info --probe đọc qua SWD"))

    bo_nap = [b for b in ds if b.nap_duoc_bang]
    la_bo = [b for b in ds if b.co_the_la_bo]
    return {
        "so_thiet_bi": len(ds),
        "so_co_the_la_bo": len(la_bo),
        "thiet_bi": [b.to_dict() for b in ds],
        "nap_duoc": bool(bo_nap),
        "chip_doc_duoc": chip,
        # Đọc từ CHÍNH con chip đang cắm — chắc hơn mọi con số trích từ tài liệu bằng biểu
        # thức chính quy (xem Fact `flash.size = 7` đọc nhầm từ dòng khai địa chỉ thanh ghi).
        "bo_nho_doc_tu_chip": bo_nho,
        "vi_sao_chua_doc_duoc_chip": vi_sao_chip,
        # Danh sách kiểm tra hiện ra khi không có thứ nào CÓ THỂ là bo — không phải khi
        # không có thiết bị nào, vì một cái tai nghe Bluetooth vẫn tính là "có thiết bị".
        "danh_sach_kiem_tra": list(DANH_SACH_KIEM_TRA) if not la_bo else [],
    }


# =========================================================================== nạp firmware
@dataclass(slots=True)
class KetQuaNap:
    dat: bool = False
    cach: str = ""                  # sao_tep | st-flash
    tep: str = ""
    so_byte: int = 0
    hash: str = ""
    dich: str = ""
    giay: float = 0.0
    da_verify: bool = False
    chip_da_doi_chieu: str = ""     # chip đã đối chiếu, rỗng nếu KHÔNG đối chiếu được
    vi_sao_khong_dat: str = ""
    canh_bao: list[str] = field(default_factory=list)
    nguyen_van: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "cach": self.cach, "tep": self.tep,
                "so_byte": self.so_byte, "hash": self.hash, "dich": self.dich,
                "giay": round(self.giay, 1), "da_verify": self.da_verify,
                "chip_da_doi_chieu": self.chip_da_doi_chieu,
                "vi_sao_khong_dat": self.vi_sao_khong_dat,
                "canh_bao": list(self.canh_bao), "nguyen_van": self.nguyen_van[-2000:]}


def _hash_tep(p: Path) -> str:
    import hashlib

    return hashlib.sha256(p.read_bytes()).hexdigest()


def nap_qua_o_dia(bin_path: Path, o_dia: Path, *, cho_giay: float = 0.0) -> KetQuaNap:
    """Nạp bằng cách SAO `.bin` vào ổ của bộ nạp, rồi đọc kết quả bộ nạp để lại.

    Vì sao không coi "sao xong" là "nạp xong": firmware DAPLink/ST-LINK nhận cả tệp rồi mới
    kiểm, và khi nó từ chối thì nó **gắn lại ổ đĩa kèm `FAIL.TXT`** ghi nguyên nhân. Một phép
    đo dừng ở `shutil.copy` sẽ báo thành công cho cả những lần nạp bị từ chối.
    """
    kq = KetQuaNap(cach="sao_tep", dich=str(o_dia))
    cho_giay = cho_giay or CHO_GAN_LAI_GIAY
    if not bin_path.exists():
        kq.vi_sao_khong_dat = f"Không có tệp {bin_path.name} để nạp."
        return kq
    if not o_dia.is_dir():
        kq.vi_sao_khong_dat = f"Ổ đĩa {o_dia} không còn được gắn — bo đã bị rút?"
        return kq

    kq.tep = bin_path.name
    kq.so_byte = bin_path.stat().st_size
    kq.hash = _hash_tep(bin_path)
    if kq.so_byte == 0:
        kq.vi_sao_khong_dat = "Tệp .bin dài 0 byte — không nạp."
        return kq

    # Dọn FAIL.TXT của lần trước, nếu không thì lần này sẽ đọc lại kết luận của lần trước.
    for t in TEP_KET_QUA:
        try:
            (o_dia / t).unlink(missing_ok=True)
        except OSError:
            pass

    t0 = time.time()
    try:
        shutil.copy(str(bin_path), str(o_dia / bin_path.name))
    except OSError as e:
        kq.giay = time.time() - t0
        kq.vi_sao_khong_dat = (
            f"Sao tệp vào {o_dia.name} thất bại: {e}. Bo có thể đã tự gắn lại ổ giữa lúc "
            "sao — trạng thái Flash của chip lúc này KHÔNG chắc chắn. Bấm RESET rồi dò lại "
            "trước khi kết luận.")
        return kq
    kq.giay = time.time() - t0

    # Bộ nạp gắn lại ổ đĩa sau khi ghi xong. Đợi nó biến mất rồi hiện lại — ĐÓ là dấu hiệu
    # nó đã nhận và xử lý, chứ không phải việc sao tệp trả về 0.
    het = time.time() + cho_giay
    da_ngat = False
    while time.time() < het:
        if not o_dia.is_dir():
            da_ngat = True
        elif da_ngat:
            break
        time.sleep(0.4)

    loi_txt = ""
    if o_dia.is_dir():
        for t in TEP_KET_QUA:
            p = o_dia / t
            if p.exists():
                try:
                    loi_txt = p.read_text("utf-8", errors="replace")[:400].strip()
                except OSError:
                    loi_txt = "(có FAIL.TXT nhưng không đọc được)"
                break
    if loi_txt:
        kq.nguyen_van = loi_txt
        kq.vi_sao_khong_dat = f"Bộ nạp TỪ CHỐI tệp này: {loi_txt}"
        return kq

    kq.dat = True
    if not da_ngat:
        # Không thấy ổ gắn lại thì ta chỉ biết "đã sao xong", chưa biết bo đã ghi. Nói ra.
        kq.canh_bao.append(
            f"Đã sao {kq.so_byte} byte vào {o_dia.name} và KHÔNG có FAIL.TXT, nhưng trong "
            f"{cho_giay:.0f} s không thấy bo gắn lại ổ đĩa. Nghĩa là chưa có bằng chứng bo đã "
            "ghi xong — kiểm bằng cách bấm RESET và xem chương trình có chạy không.")
    kq.canh_bao.append(
        "Nạp kiểu sao tệp KHÔNG verify lại nội dung đã ghi và KHÔNG đọc được ID chip. Muốn "
        "đối chiếu chip trước khi nạp (TC034) và verify sau khi nạp thì cần `st-flash` "
        "hoặc `openocd`.")
    return kq


def nap_qua_st_flash(bin_path: Path, *, dia_chi: int = 0x08000000) -> KetQuaNap:
    """Nạp bằng `st-flash write` — có verify và đọc được ID chip."""
    kq = KetQuaNap(cach="st-flash", dich=f"0x{dia_chi:08X}")
    st = shutil.which("st-flash")
    if not st:
        kq.vi_sao_khong_dat = "Máy chưa có `st-flash` (gói `stlink`)."
        return kq
    if not bin_path.exists() or bin_path.stat().st_size == 0:
        kq.vi_sao_khong_dat = f"Không có tệp {bin_path.name} hợp lệ để nạp."
        return kq
    kq.tep = bin_path.name
    kq.so_byte = bin_path.stat().st_size
    kq.hash = _hash_tep(bin_path)

    t0 = time.time()
    try:
        r = subprocess.run([st, "--reset", "write", str(bin_path), f"0x{dia_chi:08x}"],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        kq.giay = time.time() - t0
        kq.vi_sao_khong_dat = f"st-flash không chạy được: {type(e).__name__}: {e}"
        return kq
    kq.giay = time.time() - t0
    kq.nguyen_van = ((r.stdout or "") + (r.stderr or "")).strip()
    # st-flash tự verify và in "Flash written and verified! jolly good!"
    kq.da_verify = "verified" in kq.nguyen_van.lower()
    if r.returncode != 0:
        kq.vi_sao_khong_dat = (f"st-flash trả mã {r.returncode}. Nếu nó dừng giữa lúc ghi thì "
                               "Flash của chip đang ở trạng thái KHÔNG nhất quán: nạp lại "
                               "bằng connect-under-reset, hoặc vào bootloader ROM (BOOT0=1).")
        return kq
    if not kq.da_verify:
        kq.vi_sao_khong_dat = ("st-flash trả mã 0 nhưng KHÔNG in dòng verify. Không coi là "
                               "nạp xong — đọc nguyên văn đầu ra.")
        return kq
    kq.dat = True
    return kq


def doc_nguoc_flash(bin_path: Path, *, dia_chi: int = 0x08000000) -> dict[str, Any]:
    """Đọc ngược Flash từ chip rồi so từng byte với tệp đã nạp.

    `st-flash write` tự in "verified", nhưng đó là lời của **chính công cụ vừa ghi**. Phép đo
    này đi hỏi silicon: *con chip trên bàn đang chứa bản nào?* Đó mới là câu người dùng hỏi
    khi họ nhìn bo và thấy nó không chạy như mong đợi.

    Trả `dat=False` kèm lý do khi không đo được — và "không đo được" KHÔNG phải "không khớp".
    """
    import hashlib
    import tempfile

    ra: dict[str, Any] = {"dat": False, "do_duoc": False, "so_byte": 0,
                          "hash_tep": "", "hash_chip": "", "so_byte_khac": 0,
                          "vi_sao": "", "dia_chi": f"0x{dia_chi:08X}"}
    st = shutil.which("st-flash")
    if not st:
        ra["vi_sao"] = ("máy chưa có `st-flash` nên không đọc ngược được Flash. Không đọc "
                        "được KHÁC với không khớp — chưa kết luận gì về nội dung trên chip.")
        return ra
    if not bin_path.exists() or bin_path.stat().st_size == 0:
        ra["vi_sao"] = f"không có {bin_path.name} để đối chiếu."
        return ra

    mong = bin_path.read_bytes()
    ra["so_byte"] = len(mong)
    ra["hash_tep"] = hashlib.sha256(mong).hexdigest()
    dich = Path(tempfile.mkdtemp()) / "doc-nguoc.bin"
    try:
        r = subprocess.run([st, "read", str(dich), f"0x{dia_chi:08x}", str(len(mong))],
                           capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao"] = f"st-flash read không chạy được: {type(e).__name__}: {e}"
        return ra
    if r.returncode != 0 or not dich.exists():
        ra["vi_sao"] = ("st-flash read thất bại: "
                        + ((r.stderr or r.stdout or "").strip()[-200:] or "không rõ"))
        return ra

    that = dich.read_bytes()
    ra["do_duoc"] = True
    ra["hash_chip"] = hashlib.sha256(that).hexdigest()
    ra["so_byte_khac"] = sum(1 for a, b in zip(mong, that) if a != b) + abs(
        len(mong) - len(that))
    ra["dat"] = that == mong
    if not ra["dat"]:
        ra["vi_sao"] = (f"Nội dung trên chip KHÁC tệp đã nạp ở {ra['so_byte_khac']} byte. "
                        "Chip đang chạy một bản khác — nạp lại trước khi kết luận gì về "
                        "hành vi quan sát được.")
    return ra


def soi_chip(dia_chi: list[int] | None = None, *, so_tu: int = 4,
             doc_ngan_xep: bool = True, timeout: float = 60.0) -> dict[str, Any]:
    """Dừng chip lại, xem nó ĐANG Ở ĐÂU, đọc vài ô nhớ, rồi cho chạy tiếp.

    Vì sao năng lực này đáng có: đo được trên bo STM32F469 ngày 28/09/2026 — firmware dịch
    sạch, nạp đúng từng byte, `target.verify` khớp hoàn toàn, **mà màn hình đen**. Mọi phép
    đo tĩnh đều xanh. Câu trả lời nằm ở một dòng duy nhất mà chỉ chip đang chạy mới nói được:

        halted due to debug-request, current mode: Handler SysTick

    CPU kẹt trong trình phục vụ ngắt SysTick — vì `SysTick_Handler` là bí danh của
    `Default_Handler`, và `Default_Handler` là `while (1) {}`. `HAL_Init()` bật SysTick, tick
    đầu tiên nhảy vào vòng lặp vô hạn, và chương trình chết trước khi chạm tới dòng vẽ.

    Không có công cụ này thì tác tử chỉ còn cách đọc lại mã và đoán. **`che_do` là phần quan
    trọng nhất của kết quả**: "Thread" nghĩa là đang chạy mã thường; "Handler <tên>" nghĩa là
    đang ở trong một ngắt — và nếu nó ở đó mãi thì đó chính là chỗ chết.
    """
    ra: dict[str, Any] = {"dat": False, "che_do": "", "pc": "", "xpsr": "", "msp": "",
                          "o_nho": {}, "vi_sao_khong_dat": "", "nguyen_van": ""}
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = (
            "máy chưa có `openocd` nên không soi được chip đang chạy. Không soi được KHÁC "
            "với chip chạy đúng — chưa kết luận gì.")
        return ra

    # Thanh ghi trạng thái lỗi của Cortex-M. Đọc LUÔN, không đợi ai nghĩ ra:
    # gặp HardFault mà phải nhớ địa chỉ CFSR mới chẩn đoán được thì đó là một phép đo bị
    # giấu sau một câu đố. Đo được trên bo STM32F469: sau khi sửa SysTick, chip chuyển sang
    # kẹt ở `Handler HardFault` — và câu hỏi kế tiếp luôn luôn là "fault gì, ở địa chỉ nào".
    CFSR, HFSR, MMFAR, BFAR = 0xE000ED28, 0xE000ED2C, 0xE000ED34, 0xE000ED38

    lenh = ["init", "halt"]
    for d in (dia_chi or []):
        lenh.append(f"mdw 0x{d:08x} {max(1, min(so_tu, 32))}")
    lenh += [f"mdw 0x{CFSR:08x} 2", f"mdw 0x{MMFAR:08x} 2", "resume", "exit"]
    try:
        # MỖI lệnh một `-c`. Gộp cả chuỗi vào một `-c` thì openocd chạy đúng nhưng **không
        # in ra kết quả `mdw`** — và một phép đo im lặng trông y hệt một phép đo không có gì
        # để nói. Đo được: gộp → `o_nho` rỗng; tách → đọc ra `0xe000ed28: 00020000`.
        cl = [oo, "-f", "interface/stlink.cfg", "-f", "target/stm32f4x.cfg"]
        for x in lenh:
            cl += ["-c", x]
        r = subprocess.run(cl, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao_khong_dat"] = f"openocd không chạy được: {type(e).__name__}: {e}"
        return ra

    out = (r.stdout or "") + (r.stderr or "")
    ra["nguyen_van"] = out[-3000:]
    m = re.search(r"halted due to [^,]+, current mode: (.+)", out)
    if not m:
        ra["vi_sao_khong_dat"] = ("openocd chạy xong nhưng không dừng được chip — kiểm cáp "
                                  "SWD, hoặc chip đang ở chế độ ngủ sâu.")
        return ra
    ra["che_do"] = m.group(1).strip()
    for khoa, mau in (("pc", r"pc:\s*(0x[0-9a-fA-F]+)"),
                      ("xpsr", r"xPSR:\s*(0x[0-9a-fA-F]+)"),
                      ("msp", r"msp:\s*(0x[0-9a-fA-F]+)")):
        mm = re.search(mau, out)
        if mm:
            ra[khoa] = mm.group(1)
    for mm in re.finditer(r"^(0x[0-9a-fA-F]{8}):\s+([0-9a-fA-F ]+)$", out, re.M):
        ra["o_nho"][mm.group(1)] = mm.group(2).split()

    ra["loi_phan_cung"] = _doc_thanh_ghi_loi(ra["o_nho"])

    # Đang ở trong một ngắt thì đọc luôn khung ngoại lệ ở đỉnh ngăn xếp. Cần một lần gọi
    # openocd thứ hai vì địa chỉ MSP chỉ biết được SAU khi dừng chip — và nó đáng, vì không
    # có khung này thì `pc = Default_Handler` là câu trả lời duy nhất tác tử nhận được, với
    # mọi fault, mãi mãi. Đo được trên bo STM32F469: đúng như thế, hai lượt liền.
    if ra["che_do"].lower().startswith("handler") and ra["msp"]:
        try:
            msp = int(ra["msp"], 16)
        except ValueError:
            msp = 0
        if msp:
            k = _doc_o_nho(oo, [(msp, 8)], timeout=timeout)
            ra["o_nho"].update(k)
            tu = k.get(f"0x{msp:08x}") or []
            ra["khung_ngat"] = giai_khung_ngat(tu)
    elif ra["msp"] and doc_ngan_xep:
        # KHÔNG ở trong ngắt thì không có khung ngoại lệ — nhưng vẫn còn một câu chưa trả lời
        # được từ PC: **ai gọi tới đây**. Đo được trên bo STM32F469: chip dừng trong
        # `HAL_Delay`, mà `main.c` có hai vòng `while(1)` gọi `HAL_Delay` với nghĩa ngược hẳn
        # nhau ("chạy xong xuôi" và "màn hình không khởi tạo được").
        try:
            sp = int(ra["msp"], 16)
        except ValueError:
            sp = 0
        if sp:
            k = _doc_o_nho(oo, [(sp, 32)], timeout=timeout)
            ra["o_nho"].update(k)
            ra["dau_vet"] = doc_dau_vet_ngan_xep(sp, k.get(f"0x{sp:08x}") or [])

    ra["dat"] = True
    return ra


def _doc_o_nho(oo: str, vung: list[tuple[int, int]], *,
               timeout: float = 60.0) -> dict[str, list[str]]:
    """Đọc vài vùng nhớ qua openocd. Trả `{địa chỉ: [từ hệ 16]}`, rỗng nếu không đọc được."""
    cl = [oo, "-f", "interface/stlink.cfg", "-f", "target/stm32f4x.cfg", "-c", "init",
          "-c", "halt"]
    for d, n in vung:
        cl += ["-c", f"mdw 0x{d:08x} {max(1, min(n, 32))}"]
    cl += ["-c", "resume", "-c", "exit"]
    try:
        r = subprocess.run(cl, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return {}
    out = (r.stdout or "") + (r.stderr or "")
    ra: dict[str, list[str]] = {}
    for m in re.finditer(r"^(0x[0-9a-fA-F]{8}):\s+([0-9a-fA-F ]+)$", out, re.M):
        ra[m.group(1)] = m.group(2).split()
    # openocd in mỗi 4 từ một dòng. Ghép các dòng liên tiếp của cùng một vùng lại, nếu không
    # thì xin 8 từ chỉ nhận về 4 và khung ngoại lệ sẽ luôn "chỉ đọc được 4/8".
    for d, n in vung:
        gom: list[str] = []
        for i in range(0, n, 4):
            gom += ra.get(f"0x{d + i * 4:08x}", [])
        if gom:
            ra[f"0x{d:08x}"] = gom
    return ra


# Số ký hiệu in kèm quanh một địa chỉ. Đủ để biết mình đang ở đâu, không đủ để thành một
# bảng ký hiệu dán vào hội thoại.
SO_KY_HIEU_QUANH = 3


def giai_ma_dia_chi(elf: Path, dia_chi: list[int], *,
                    timeout: float = 30.0) -> dict[str, Any]:
    """Địa chỉ → tên hàm + tệp:dòng, đọc từ ELF bằng `addr2line`/`nm`.

    Vì sao năng lực này đáng có, đo được trên bo STM32F469 ngày 28/09/2026: `target.debug`
    nói chip kẹt ở `Handler HardFault`, `pc 0x08000db0`. Tác tử nhận con số đó rồi đi
    **`fs.read` 28 lần** để dò xem hàm nào nằm ở đấy, hết hạn mức 40 lời gọi của lượt và
    dừng giữa việc. `arm-none-eabi-addr2line` trả lời cùng câu hỏi trong 40 ms:
    `OTM8009A_Init_Ext` tại `otm8009a.c:424`.

    Một địa chỉ không tên thì chỉ là một con số; nó bắt tác tử đoán, và đoán bằng cách đọc
    hết mã nguồn là cách đắt nhất để đoán.

    **Phanh quan trọng nhất của hàm này là `canh_bao`**: tên hàm chỉ đúng nếu con chip đang
    chứa ĐÚNG bản dịch ra ELF này. Dịch lại mà chưa nạp là chuyện thường xuyên, và khi đó
    `addr2line` vẫn trả về một cái tên nghe rất thuyết phục — của bản khác. Hàm này KHÔNG tự
    quyết được điều đó (nó không nói chuyện với chip), nên nó trả `can_doi_chieu=True` để
    tầng trên đi hỏi silicon trước khi trình cái tên ra như sở cứ.
    """
    ra: dict[str, Any] = {"dat": False, "ky_hieu": {}, "vi_sao_khong_dat": "",
                          "can_doi_chieu": True, "elf": str(elf)}
    if not elf.exists() or elf.stat().st_size == 0:
        ra["vi_sao_khong_dat"] = (f"không có {elf.name} — biên dịch trước rồi mới giải mã "
                                  "được địa chỉ thành tên hàm.")
        return ra
    a2l = shutil.which("arm-none-eabi-addr2line")
    if not a2l:
        ra["vi_sao_khong_dat"] = ("máy chưa có `arm-none-eabi-addr2line` (đi cùng "
                                  "arm-none-eabi-binutils) nên chưa đổi được địa chỉ thành "
                                  "tên hàm. Không giải mã được KHÁC với địa chỉ không có "
                                  "hàm nào.")
        return ra
    # `if d` ở đây từng làm mất **địa chỉ 0** — chỗ đặt bảng vector, một trong những địa chỉ
    # đáng soi nhất khi chip HardFault. Bỏ im lặng một địa chỉ người ta xin đọc là một câu
    # trả lời thiếu mà trông như đủ.
    ds = [f"0x{d:08x}" for d in dia_chi if isinstance(d, int) and 0 <= d <= 0xFFFFFFFF]
    if not ds:
        ra["vi_sao_khong_dat"] = "không có địa chỉ nào để giải mã."
        return ra
    try:
        r = subprocess.run([a2l, "-f", "-C", "-e", str(elf), *ds],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao_khong_dat"] = f"addr2line không chạy được: {type(e).__name__}: {e}"
        return ra
    if r.returncode != 0:
        ra["vi_sao_khong_dat"] = ("addr2line thất bại: "
                                  + ((r.stderr or r.stdout or "").strip()[-200:] or "?"))
        return ra

    # `addr2line -f` in HAI dòng cho mỗi địa chỉ: tên hàm, rồi tệp:dòng.
    dong = [x.strip() for x in (r.stdout or "").splitlines() if x.strip()]
    for i, d in enumerate(ds):
        ten = dong[2 * i] if 2 * i < len(dong) else "??"
        noi = dong[2 * i + 1] if 2 * i + 1 < len(dong) else "??"
        # `??` là cách addr2line nói "không có ký hiệu ở đây". Nói lại nguyên ý đó, đừng
        # trình một ô trống — ô trống đọc như "chỗ này không sao".
        ra["ky_hieu"][d] = {
            "ham": ten if ten != "??" else "",
            # addr2line nói "không biết" bằng nhiều kiểu: `??`, `??:0`, `??:?`. Gộp cả họ
            # lại, đừng chỉ bắt hai dạng rồi để dạng thứ ba lọt ra như một đường dẫn thật.
            "nguon": "" if noi.startswith("??") else noi.split("/")[-1],
            "nguon_day_du": "" if noi.startswith("??") else noi,
            "ghi_chu": ("" if ten != "??" else
                        "ELF không có ký hiệu nào ở địa chỉ này — có thể chip đang chạy bản "
                        "khác, hoặc địa chỉ nằm ngoài vùng mã (bảng vector, RAM, bootloader)"),
        }
    ra["dat"] = True
    ra["canh_bao"] = ("Tên hàm ở trên đọc từ ELF vừa dịch, KHÔNG đọc từ chip. Nó chỉ đúng nếu "
                      "chip đang chứa đúng bản này — hãy đối chiếu bằng target.verify trước "
                      "khi coi tên hàm là sở cứ.")
    return ra


# Khung ngăn xếp mà Cortex-M tự đẩy khi vào ngoại lệ, theo thứ tự từ địa chỉ thấp.
# Đây là kiến trúc ARMv7-M, không phải quy ước của trình dịch: thứ tự này cố định.
_KHUNG_NGAT = ("r0", "r1", "r2", "r3", "r12", "lr", "pc", "xpsr")


def giai_khung_ngat(tu: list[str]) -> dict[str, Any]:
    """8 từ đọc từ đỉnh ngăn xếp → khung ngoại lệ, tức là **lệnh nào đã gây fault**.

    Vì sao cần: `target.debug` nói chip đang ở `Handler HardFault`, `pc = Default_Handler`.
    Đúng, nhưng vô dụng — `HardFault_Handler` là bí danh của `Default_Handler` nên PC ấy luôn
    là chỗ đó với MỌI fault. Nó là một câu trả lời vòng tròn.

    Địa chỉ đáng quan tâm nằm ở nơi khác: khi vào ngoại lệ, chính CPU đẩy 8 thanh ghi lên
    ngăn xếp, và từ thứ 7 là **PC của lệnh đã fault**. Đó là chỗ tác tử cần đọc mã.

    Hai chỗ số này KHÔNG tin được, và hàm nói ra thay vì để người đọc tự biết:

    * Nếu fault xảy ra *trong lúc* đẩy ngăn xếp (tràn ngăn xếp — bit STKERR/MSTKERR của CFSR)
      thì khung này chưa kịp ghi xong và toàn bộ 8 số là rác.
    * Khung đọc ở MSP chỉ đúng khi chương trình đang chạy trên ngăn xếp chính. Có RTOS thì
      khung nằm ở PSP, và bit 2 của EXC_RETURN (trong LR lúc vào ngắt) mới nói cái nào.
    """
    ra: dict[str, Any] = {"doc_duoc": False}
    if len(tu) < 8:
        ra["vi_sao"] = (f"chỉ đọc được {len(tu)}/8 từ ở đỉnh ngăn xếp — chưa dựng được khung "
                        "ngoại lệ.")
        return ra
    try:
        gt = [int(x, 16) for x in tu[:8]]
    except ValueError:
        ra["vi_sao"] = "nội dung đọc được ở đỉnh ngăn xếp không phải số hệ 16."
        return ra
    ra["doc_duoc"] = True
    for ten, v in zip(_KHUNG_NGAT, gt):
        ra[ten] = f"0x{v:08X}"
    # `pc_fault` là số duy nhất trong khung này đáng đi tra tên hàm. Tách riêng để tầng trên
    # khỏi phải biết offset 0x18 là gì.
    ra["pc_fault"] = gt[6]
    ra["lr_fault"] = gt[5]
    # xPSR bit 24 = cờ T. Bằng 0 nghĩa là CPU đã bị đưa ra khỏi trạng thái Thumb — đúng cái
    # mà bit INVSTATE của CFSR đang báo, và là bằng chứng độc lập cho nó.
    ra["thumb"] = bool(gt[7] & (1 << 24))
    if not ra["thumb"]:
        ra["ghi_chu"] = ("Cờ T trong xPSR đã đẩy = 0: lúc fault, CPU không ở trạng thái "
                         "Thumb. Gần như luôn là một lần nhảy tới địa chỉ CHẴN — con trỏ hàm "
                         "hoặc ô bảng vector thiếu bit 0. Xem `pc_fault` để biết nhảy tới đâu.")
    return ra


# Định dạng điểm ảnh LTDC hiểu → (số byte mỗi điểm, cách xếp kênh). Mã số là giá trị của
# trường PF trong thanh ghi LTDC_LxPFCR, đọc thẳng từ chip được.
DINH_DANG_DIEM = {
    "ARGB8888": (4, "BGRA"),        # LTDC PF=0. Trong bộ nhớ little-endian: B,G,R,A
    "RGB888": (3, "BGR"),           # PF=1
    "RGB565": (2, "RGB565"),        # PF=2
}
_PF_LTDC = {0: "ARGB8888", 1: "RGB888", 2: "RGB565"}

# Trần kích thước một lần đọc framebuffer. 800×480×4 = 1,5 MB đã là cả một màn hình; đọc hơn
# thế qua SWD thì người ta bỏ chạy trước khi nó xong.
TRAN_BYTE_KHUNG_ANH = 4 * 1024 * 1024


# Chuỗi phải thông suốt thì mắt mới thấy gì: bộ nhớ khung ảnh → LTDC → bọc DSI → host DSI →
# panel ra khỏi reset. Đứt bất cứ mắt nào cũng cho ra **cùng một** màn hình đen, và đó chính
# là lý do phải đi dọc nó bằng số thay vì đoán xem mắt nào hỏng.
DSI_GOC = 0x40016C00
LTDC_GOC = 0x40016800
# Chân XRES của panel. Đây là số của RIÊNG bo 32F469IDISCOVERY, đọc từ `BSP_LCD_Reset()` trong
# `stm32469i_discovery_lcd.c`: *"reset the LCD by activation of XRES (active low) connected to
# PH7"*. Bo khác thì chân khác — nên nó là tham số, và kết quả nói rõ mình đang giả định gì.
#
# Mọi con số dưới đây lấy từ `stm32f469xx.h` của ST, KHÔNG từ trí nhớ. Bản trước viết
# `GPIOH_ODR = 0x40021C1C` theo trí nhớ — đó là `LCKR` (offset 0x1C), còn `ODR` ở offset 0x14.
# Phép đo đọc nhầm thanh ghi rồi báo "panel đang bị giữ trong reset", tức là **tự chế ra một
# bằng chứng**; và một bằng chứng sai thì tệ hơn hẳn không có bằng chứng, vì người ta hành
# động theo nó. Cùng lỗi ấy xảy ra với `DSIEN`: bản trước để bit 2, đúng phải là bit 3.
GPIOH_BASE = 0x40021C00                 # AHB1PERIPH_BASE(0x40020000) + 0x1C00
GPIO_MODER, GPIO_IDR, GPIO_ODR = 0x00, 0x10, 0x14
GPIOH_ODR = GPIOH_BASE + GPIO_ODR       # 0x40021C14
CHAN_XRES_MAC_DINH = 7

# Bit của DSI_WCR, từ `stm32f469xx.h`: COLM=0, SHTDN=1, LTDCEN=2, DSIEN=3.
_WCR_COLM, _WCR_SHTDN, _WCR_LTDCEN, _WCR_DSIEN = 0, 1, 2, 3

# Offset thanh ghi bọc DSI, chép từ chính dòng chú thích trong `stm32f469xx.h`:
#
#     __IO uint32_t WCFGR;   /*!< DSI Wrapper Configuration Register,  Address offset: 0x400 */
#     __IO uint32_t WCR;     /*!< DSI Wrapper Control Register,        Address offset: 0x404 */
#
# Bản trước để `WCR = 0x400` — đó là `WCFGR`. Phép đo đọc thanh ghi CẤU HÌNH rồi giải nghĩa
# nó như thanh ghi ĐIỀU KHIỂN: `0x0A` đọc thành "SHTDN = 1, màn đang tắt", trong khi `WCR`
# thật ở `0x404` bằng `0x08` — SHTDN = 0, màn KHÔNG tắt.
#
# Lỗi này lộ ra không phải vì tôi kiểm lại, mà vì **tác tử tự đi đọc cả hai địa chỉ rồi nói
# ra**. Và nó là lần thứ ba liên tiếp trong cùng một hàm một hằng số sai sinh ra một kết luận
# sai — hai lần đầu vì viết theo trí nhớ, lần này vì tin một bộ phân tích header tự viết vội
# thay vì đọc chính dòng chú thích mà ST đã ghi sẵn offset vào.
DSI_WCFGR = 0x400
DSI_WCR = 0x404

# Các thanh ghi còn lại, cũng chép từ dòng chú thích của `stm32f469xx.h` — sau ba lần sai vì
# tự dựng lại con số, mọi offset ở đây đều phải tra được bằng mắt trong header:
#
#   MCR 0x34 · PCTLR 0xA0 · ISR[2] 0xBC–0xC3 · WISR 0x40C   (DSI_TypeDef)
#   CPSR 0x44 · CDSR 0x48                                    (LTDC_TypeDef)
DSI_MCR, DSI_PCTLR, DSI_ISR0, DSI_ISR1, DSI_WISR = 0x34, 0xA0, 0xBC, 0xC0, 0x40C
LTDC_CPSR, LTDC_CDSR = 0x44, 0x48
_MCR_CMDM = 0                 # 0 = chế độ video, 1 = chế độ lệnh
_PCTLR_DEN, _PCTLR_CKE = 1, 2
_WISR_PLLLS = 8


# RCC_CSR — con chip tự khai lần khởi động vừa rồi là do đâu. Bit 24 (RMVF) để xoá cờ.
RCC_CSR = 0x40023874
_BIT_RESET = (
    (31, "LPWRRST — reset do lỗi khi vào chế độ ngủ sâu"),
    (30, "WWDGRST — **chó canh cửa sổ (WWDG) đã cắn**"),
    (29, "IWDGRST — **chó canh độc lập (IWDG) đã cắn**: chương trình không kịp vỗ về nó"),
    (28, "SFTRST — reset do phần mềm tự gọi (NVIC_SystemReset)"),
    (27, "PORRST — bật nguồn (cắm điện / rút cắm lại)"),
    (26, "PINRST — chân NRST bị kéo xuống (nút RESET, hoặc bộ nạp)"),
    (25, "BORRST — điện áp tụt dưới ngưỡng"),
)


def doc_nguyen_nhan_reset(*, timeout: float = 60.0) -> dict[str, Any]:
    """Lần khởi động vừa rồi của chip là do đâu — hỏi chính con chip, không suy từ triệu chứng.

    Vì sao cần: một chương trình *đang reset đi reset lại* và một chương trình *kẹt ở một chỗ*
    nhìn qua cửa sổ gỡ lỗi thì giống hệt nhau — cả hai đều cho ra một PC không tiến lên. Nhưng
    nguyên nhân và cách sửa khác hẳn nhau, và `RCC_CSR` trả lời thẳng câu đó bằng một bit.

    Lưu ý đọc kết quả: các cờ này **dính** cho tới khi có ai xoá (bit RMVF). Thấy `PINRST`
    không có nghĩa là *vừa* bị reset bởi chân NRST — chỉ nghĩa là lần reset gần nhất *mà chưa
    ai xoá cờ* là thế. Hàm nói ra điều này thay vì để người đọc tự biết.
    """
    ra: dict[str, Any] = {"dat": False, "vi_sao_khong_dat": "", "nguyen_nhan": []}
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = "máy chưa có `openocd`."
        return ra
    o = _doc_o_nho(oo, [(RCC_CSR, 1)], timeout=timeout)
    v = o.get(f"0x{RCC_CSR:08x}")
    if not v:
        ra["vi_sao_khong_dat"] = "không đọc được RCC_CSR."
        return ra
    try:
        csr = int(v[0], 16)
    except ValueError:
        ra["vi_sao_khong_dat"] = f"RCC_CSR đọc ra không phải số hệ 16: {v[0]!r}"
        return ra
    ra["dat"] = True
    ra["csr"] = f"0x{csr:08X}"
    ra["nguyen_nhan"] = [ten for bit, ten in _BIT_RESET if csr & (1 << bit)]
    ra["ghi_chu"] = ("Cờ reset DÍNH cho tới khi phần mềm xoá (bit RMVF của RCC_CSR). Đây là "
                     "lần reset gần nhất chưa ai xoá cờ, không nhất thiết là lần vừa xảy ra. "
                     "Muốn đo vòng lặp reset thì xoá cờ, để chạy một lúc, rồi đọc lại.")
    return ra


def lay_mau_pc(so_lan: int = 8, *, timeout: float = 60.0) -> dict[str, Any]:
    """Lấy mẫu PC nhiều lần để biết chương trình ĐANG TIẾN hay đứng yên.

    Một mẫu PC đơn lẻ không phân biệt được ba thứ khác hẳn nhau: chương trình **kẹt** ở một
    chỗ, chương trình **đi qua** chỗ đó liên tục trong một vòng lặp, và chip **reset lại** nên
    lần nào cũng bị bắt gặp ở đoạn khởi động. Cả ba cho ra cùng một con số nếu chỉ nhìn một
    lần — đo được đúng thế trên bo STM32F469: PC nằm ở `HAL_InitTick` sáu lần liên tiếp.

    Nhiều mẫu thì phân biệt được: một địa chỉ duy nhất = kẹt thật; vài địa chỉ gần nhau = một
    vòng lặp; địa chỉ rải khắp = đang chạy bình thường.
    """
    ra: dict[str, Any] = {"dat": False, "mau": [], "vi_sao_khong_dat": ""}
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = "máy chưa có `openocd`."
        return ra
    for _ in range(max(2, min(so_lan, 32))):
        # `doc_ngan_xep=False`: ở đây chỉ cần PC, và mỗi lần đọc ngăn xếp là một lần DỪNG
        # thêm con chip đang chạy. Lấy tám mẫu mà dừng mười sáu lần thì phép đo bắt đầu can
        # thiệp vào chính thứ nó đang đo.
        d = soi_chip(doc_ngan_xep=False, timeout=timeout)
        if d["dat"] and d["pc"]:
            ra["mau"].append(d["pc"])
    if not ra["mau"]:
        ra["vi_sao_khong_dat"] = "không dừng được chip lần nào."
        return ra
    ra["dat"] = True
    dem: dict[str, int] = {}
    for x in ra["mau"]:
        dem[x] = dem.get(x, 0) + 1
    ra["so_dia_chi_khac_nhau"] = len(dem)
    ra["hay_gap_nhat"] = max(dem.items(), key=lambda kv: kv[1])
    # ĐẾM số địa chỉ khác nhau thì không phân biệt được gì cả. Đo được trên bo STM32F469: sáu
    # mẫu rơi vào năm địa chỉ — nghe như "đang chạy bình thường" — nhưng cả năm nằm trong
    # **40 byte** của nhau, tức một vòng lặp chặt bên trong đúng một hàm. Thứ phân biệt được
    # là KHOẢNG TRẢI, không phải số lượng.
    so = [int(x, 16) for x in dem]
    ra["trai_byte"] = max(so) - min(so)
    ra["tu"], ra["den"] = f"0x{min(so):08X}", f"0x{max(so):08X}"
    # Ngưỡng là quy ước, nên nó được nói ra chứ không giấu trong một câu kết luận. 256 byte
    # cỡ một hàm nhỏ đã dịch; rộng hơn thế thì chương trình có đi qua nhiều hàm.
    ra["nguong_trai_byte"] = 256
    ra["ket_luan"] = (
        f"PC không nhúc nhích qua {len(ra['mau'])} lần lấy mẫu — chương trình ĐỨNG YÊN ở "
        "đúng một lệnh." if len(dem) == 1 else
        f"{len(ra['mau'])} mẫu rơi vào {len(dem)} địa chỉ nhưng chỉ trải {ra['trai_byte']} "
        f"byte ({ra['tu']}–{ra['den']}) — chương trình đang QUANH QUẨN trong một vùng nhỏ cỡ "
        "một hàm: hoặc một vòng lặp chặt, hoặc chip reset lại nên lần nào cũng bị bắt gặp ở "
        "cùng đoạn khởi động. Đọc RCC_CSR để phân biệt hai cái, và giải mã địa chỉ ra tên hàm "
        "để biết vùng đó là gì." if ra["trai_byte"] <= ra["nguong_trai_byte"] else
        f"PC trải {ra['trai_byte']} byte qua {len(dem)} địa chỉ — chương trình đang chạy qua "
        "nhiều chỗ, không kẹt.")
    return ra


# Vùng Flash của họ STM32. Dùng để lọc: một từ trên ngăn xếp chỉ đáng nghi là địa chỉ trở về
# nếu nó trỏ vào vùng mã.
FLASH_DAU = 0x08000000
FLASH_CUOI_MAC_DINH = 0x08200000            # 2 MB — bo STM32F469NI


def doc_dau_vet_ngan_xep(sp: int, tu: list[str], *, flash_cuoi: int = FLASH_CUOI_MAC_DINH,
                         toi_da: int = 12) -> dict[str, Any]:
    """Quét ngăn xếp tìm những từ TRÔNG NHƯ địa chỉ trở về → dấu vết chuỗi gọi.

    Vì sao cần, đo được trên bo STM32F469 ngày 28/09/2026: chip dừng trong `HAL_Delay`. Nhưng
    `main.c` có **hai** vòng `while(1)` gọi `HAL_Delay` — vòng chính ở cuối chương trình, và
    vòng bắt lỗi ngay sau `if (BSP_LCD_Init() != LCD_OK)`. Hai vòng ấy nghĩa ngược hẳn nhau:
    một cái là "chạy xong xuôi", cái kia là "màn hình không khởi tạo được". Chỉ nhìn PC thì
    chúng giống hệt nhau.

    Thanh ghi LR không trả lời được: `HAL_Delay` gọi tiếp `HAL_GetTick`, nên LR đã bị ghi đè
    bằng một địa chỉ bên trong chính `HAL_Delay`.

    **Đây là PHỎNG ĐOÁN, và hàm nói thẳng như vậy.** Nó không đọc bảng unwind (`.ARM.exidx`)
    — nó chỉ nhặt những từ trên ngăn xếp trỏ vào vùng Flash và có bit 0 = 1 (bit Thumb của
    địa chỉ trở về). Vài cái trong đó là rác còn sót từ các lần gọi trước. Một dấu vết có lẫn
    rác vẫn hơn hẳn không có gì — miễn là không ai trình bày nó như sự thật.
    """
    ra: dict[str, Any] = {"doc_duoc": False, "khung": [], "la_phong_doan": True,
                          "ghi_chu": ("Đây là PHỎNG ĐOÁN từ nội dung ngăn xếp, không phải "
                                      "chuỗi gọi dựng từ bảng unwind. Có thể lẫn địa chỉ còn "
                                      "sót từ những lần gọi trước; đọc theo thứ tự từ gần "
                                      "đỉnh ngăn xếp xuống, và tin cái gần nhất hơn.")}
    if not tu:
        ra["vi_sao"] = "chưa đọc được từ nào ở đỉnh ngăn xếp."
        return ra
    ung: list[int] = []
    for i, x in enumerate(tu):
        try:
            v = int(x, 16)
        except ValueError:
            continue
        # Bit 0 = 1: địa chỉ trở về trên Cortex-M luôn mang bit Thumb. Lọc này bỏ được phần
        # lớn dữ liệu thường (biến cục bộ, con trỏ vào RAM) mà không cần biết gì về chương
        # trình.
        if v & 1 and FLASH_DAU <= (v & ~1) < flash_cuoi:
            dc = v & ~1
            if not ung or ung[-1] != dc:
                ung.append(dc)
                ra["khung"].append({"dia_chi": f"0x{dc:08X}", "o_lech": i * 4,
                                    "tu_dia_chi": f"0x{sp + i * 4:08X}"})
        if len(ung) >= toi_da:
            break
    ra["doc_duoc"] = bool(ung)
    ra["dia_chi"] = ung
    if not ung:
        ra["vi_sao"] = (f"không từ nào trong {len(tu)} từ ở đỉnh ngăn xếp trông như địa chỉ "
                        "trở về. Ngăn xếp có thể vừa được dựng lại, hoặc chương trình đang ở "
                        "rất sâu trong một hàm không gọi ai.")
    return ra


def doc_duong_hien_thi(*, chan_xres: int = CHAN_XRES_MAC_DINH,
                       odr_xres: int = GPIOH_ODR,
                       timeout: float = 60.0) -> dict[str, Any]:
    """Đi dọc chuỗi LTDC → bọc DSI → host DSI → panel và nói ĐỨT Ở ĐÂU.

    Vì sao cần: `target.screen` trả lời được câu *"vẽ sai hay panel không hiện"*, nhưng khi
    câu trả lời là "panel không hiện" thì nó chỉ nói được tên cả một chuỗi bốn mắt xích. Bốn
    mắt ấy hỏng theo bốn cách khác nhau và cho ra **cùng một** màn hình đen.

    Đo được trên bo STM32F469 ngày 28/09/2026, khi khung ảnh đã vẽ đúng mà màn vẫn đen:

        DSI_WCR = 0x0000000A  → DSIEN = 0 (bọc DSI chưa bật), SHTDN = 1 (đang tắt hiển thị)
        GPIOH_ODR bit 7 = 0   → XRES tích cực thấp vẫn đang được kéo xuống: panel bị giữ reset

    Hai số đó biến "lỗi ở đâu đó trong đường ra màn hình" thành hai dòng sửa được.

    Chỗ hàm này KHÔNG biết, và nói ra: chân XRES là của riêng từng bo. Mặc định lấy theo
    32F469IDISCOVERY; bo khác phải truyền vào, và nếu truyền sai thì dòng về panel là vô nghĩa
    — nên nó luôn đi kèm câu khai mình đang đọc chân nào.
    """
    ra: dict[str, Any] = {"dat": False, "vi_sao_khong_dat": "", "mat_xich": [], "dut_o": []}
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = ("máy chưa có `openocd`. Không đọc được KHÁC với đường hiển "
                                  "thị không có lỗi.")
        return ra
    idr_xres = odr_xres - GPIO_ODR + GPIO_IDR
    vung = [(LTDC_GOC + 0x18, 1), (LTDC_GOC + 0x84, 1),
            (DSI_GOC + 0x04, 1), (DSI_GOC + DSI_WCR, 1), (DSI_GOC + DSI_WCFGR, 1),
            (DSI_GOC + DSI_MCR, 1), (DSI_GOC + DSI_PCTLR, 1),
            (DSI_GOC + DSI_ISR0, 1), (DSI_GOC + DSI_ISR1, 1), (DSI_GOC + DSI_WISR, 1),
            (LTDC_GOC + LTDC_CPSR, 1), (odr_xres, 1), (idr_xres, 1)]
    o = _doc_o_nho(oo, vung, timeout=timeout)
    # CPSR là VỊ TRÍ ĐIỂM ẢNH ĐANG QUÉT. Đọc nó một lần thì chỉ được một con số vô nghĩa; đọc
    # HAI lần rồi so mới trả lời được câu quan trọng nhất của cả chuỗi: LTDC có thật sự đang
    # đẩy điểm ảnh ra không, hay nó chỉ "đã bật" trên giấy.
    o2 = _doc_o_nho(oo, [(LTDC_GOC + LTDC_CPSR, 1)], timeout=timeout)

    def _lay(dc: int) -> int | None:
        v = o.get(f"0x{dc:08x}")
        try:
            return int(v[0], 16) if v else None
        except ValueError:
            return None

    gcr, l1cr = _lay(LTDC_GOC + 0x18), _lay(LTDC_GOC + 0x84)
    dsi_cr, wcr, odr = _lay(DSI_GOC + 0x04), _lay(DSI_GOC + DSI_WCR), _lay(odr_xres)
    wcfgr = _lay(DSI_GOC + DSI_WCFGR)
    idr = _lay(idr_xres)
    mcr, pctlr = _lay(DSI_GOC + DSI_MCR), _lay(DSI_GOC + DSI_PCTLR)
    isr0, isr1 = _lay(DSI_GOC + DSI_ISR0), _lay(DSI_GOC + DSI_ISR1)
    wisr = _lay(DSI_GOC + DSI_WISR)
    cpsr1 = _lay(LTDC_GOC + LTDC_CPSR)
    try:
        v2 = o2.get(f"0x{LTDC_GOC + LTDC_CPSR:08x}")
        cpsr2 = int(v2[0], 16) if v2 else None
    except ValueError:
        cpsr2 = None
    if gcr is None and wcr is None:
        ra["vi_sao_khong_dat"] = "không đọc được thanh ghi nào — cáp SWD, hay chip đang bị giữ?"
        return ra
    ra["dat"] = True

    def _mat(ten: str, dat: bool | None, so: str, giai_thich: str, cach_sua: str = "") -> None:
        ra["mat_xich"].append({"ten": ten, "thong": dat, "so_do": so,
                               "nghia": giai_thich, "cach_sua": cach_sua})
        # `None` = chưa đọc được. KHÔNG gộp vào "đứt" — báo đứt vì không đọc được là một báo
        # động giả, và báo động giả dạy người ta bỏ qua cảnh báo.
        if dat is False:
            ra["dut_o"].append(ten)

    _mat("LTDC bật", None if gcr is None else bool(gcr & 1),
         f"LTDC_GCR = 0x{gcr:08X}" if gcr is not None else "chưa đọc được",
         "bộ điều khiển màn hình có đang quét khung ảnh ra không",
         "HAL_LTDC_Init / __HAL_LTDC_ENABLE")
    _mat("Lớp 1 bật", None if l1cr is None else bool(l1cr & 1),
         f"LTDC_L1CR = 0x{l1cr:08X}" if l1cr is not None else "chưa đọc được",
         "lớp ảnh có được bật để hiện không",
         "BSP_LCD_LayerDefaultInit")
    _mat("Host DSI bật", None if dsi_cr is None else bool(dsi_cr & 1),
         f"DSI_CR = 0x{dsi_cr:08X}" if dsi_cr is not None else "chưa đọc được",
         "khối DSI có đang chạy không", "HAL_DSI_Start")
    if wcr is None:
        _mat("Bọc DSI bật (DSIEN)", None, "chưa đọc được", "", "")
        _mat("Hiển thị không bị tắt (SHTDN)", None, "chưa đọc được", "", "")
    else:
        bit = (f"DSI_WCR(0x{DSI_GOC + DSI_WCR:08X}) = 0x{wcr:08X} → "
               f"COLM={(wcr >> _WCR_COLM) & 1} "
               f"SHTDN={(wcr >> _WCR_SHTDN) & 1} LTDCEN={(wcr >> _WCR_LTDCEN) & 1} "
               f"DSIEN={(wcr >> _WCR_DSIEN) & 1}")
        _mat("Bọc DSI bật (DSIEN)", bool(wcr & (1 << _WCR_DSIEN)), bit,
             "bọc DSI là chỗ ảnh của LTDC được đóng gói rồi đẩy ra đường DSI; tắt thì màn "
             "đen dù LTDC chạy hoàn hảo",
             "__HAL_DSI_WRAPPER_ENABLE / HAL_DSI_Start")
        _mat("Hiển thị không bị tắt (SHTDN)", not (wcr & (1 << _WCR_SHTDN)), bit,
             "bit SHTDN = 1 là trạng thái TẮT hiển thị của bọc DSI (DSI_DISPLAY_OFF trong "
             "HAL). Ảnh vẫn được LTDC quét ra, nhưng bọc DSI không đẩy nó đi đâu cả",
             "xoá bit SHTDN SAU khi mọi bước khởi tạo đã xong — nếu mã đã xoá rồi mà đọc lại "
             "vẫn thấy 1 thì có ai đó bật lại nó về sau; tìm chỗ ghi vào DSI->WCR")
    _mat("LTDC ĐANG QUÉT (không chỉ “đã bật”)",
         None if cpsr1 is None or cpsr2 is None else cpsr1 != cpsr2,
         (f"CPSR đọc hai lần: 0x{cpsr1:08X} → 0x{cpsr2:08X}"
          if cpsr1 is not None and cpsr2 is not None else "chưa đọc được"),
         "CPSR là vị trí điểm ảnh đang quét. Hai lần đọc ra CÙNG một giá trị nghĩa là bộ quét "
         "đứng yên — LTDC bật mà không chạy. Đổi giá trị nghĩa là điểm ảnh đang thật sự chảy "
         "ra đường DSI",
         "kiểm xung nhịp điểm ảnh: PLL của DSI cấp xung cho LTDC ở chế độ video")
    _mat("PLL của DSI đã khoá", None if wisr is None else bool(wisr & (1 << _WISR_PLLLS)),
         f"DSI_WISR = 0x{wisr:08X}, PLLLS = {(wisr >> _WISR_PLLLS) & 1}"
         if wisr is not None else "chưa đọc được",
         "PLL chưa khoá thì không có xung nhịp cho cả đường DSI lẫn LTDC",
         "HAL_DSI_Init — kiểm tham số PLL (NDIV/IDF/ODF)")
    _mat("PHY của DSI bật (DEN + CKE)",
         None if pctlr is None else bool(pctlr & (1 << _PCTLR_DEN))
         and bool(pctlr & (1 << _PCTLR_CKE)),
         f"DSI_PCTLR = 0x{pctlr:08X}, DEN = {(pctlr >> _PCTLR_DEN) & 1}, "
         f"CKE = {(pctlr >> _PCTLR_CKE) & 1}" if pctlr is not None else "chưa đọc được",
         "PHY là phần cứng đẩy bit ra hai làn dữ liệu; tắt thì không byte nào rời khỏi chip",
         "HAL_DSI_Start")
    _mat("Chế độ VIDEO (không phải chế độ lệnh)",
         None if mcr is None else not (mcr & (1 << _MCR_CMDM)),
         f"DSI_MCR = 0x{mcr:08X}, CMDM = {(mcr >> _MCR_CMDM) & 1}"
         if mcr is not None else "chưa đọc được",
         "chế độ lệnh chỉ đẩy khung khi có ai bấm nút refresh (DSI_WCR.LTDCEN); panel "
         "OTM8009A trên bo này chạy chế độ video liên tục",
         "HAL_DSI_ConfigVideoMode")
    _mat("Không có lỗi trên đường DSI",
         None if isr0 is None or isr1 is None else (isr0 == 0 and isr1 == 0),
         f"DSI_ISR0 = 0x{isr0:08X}, DSI_ISR1 = 0x{isr1:08X}"
         if isr0 is not None and isr1 is not None else "chưa đọc được",
         "ISR0 gom lỗi ACK do CHÍNH PANEL báo về; ISR1 gom lỗi PHY và quá hạn. Cả hai bằng 0 "
         "nghĩa là đường truyền sạch — và khi đó màn vẫn đen thì lỗi ở phía panel, không "
         "phải ở đường",
         "đọc chuỗi khởi tạo panel: nó có thật sự chạy hết không, có bị trả lỗi giữa chừng không")

    # ODR là thứ chương trình MUỐN, IDR là thứ chân đang THỰC SỰ ở. Với chân open-drain kéo
    # một tải ngoài, hai cái này lệch nhau được — và chính cái lệch đó là thông tin.
    _mat(f"Panel đã ra khỏi reset (XRES = PH{chan_xres})",
         None if idr is None and odr is None else bool((idr if idr is not None else odr)
                                                       & (1 << chan_xres)),
         (f"ODR(0x{odr_xres:08X}) bit {chan_xres} = {(odr >> chan_xres) & 1 if odr is not None else '?'}"
          f", IDR(0x{idr_xres:08X}) bit {chan_xres} = "
          f"{(idr >> chan_xres) & 1 if idr is not None else '?'}"),
         "XRES tích cực THẤP: bit = 0 nghĩa là panel đang bị giữ trong reset và sẽ không "
         "hiện gì, dù mọi thứ phía trước đều đúng. Đọc cả IDR vì chân này thường là "
         "open-drain — ODR nói ý định, IDR nói thực tế",
         "BSP_LCD_Reset() phải kết thúc bằng việc kéo chân này LÊN (GPIO_PIN_SET)")
    # WCFGR đi kèm để người đọc thấy ngay mình KHÔNG nhầm hai thanh ghi cạnh nhau nữa.
    ra["wcfgr"] = f"0x{wcfgr:08X}" if wcfgr is not None else ""
    ra["chan_xres"] = f"PH{chan_xres}"
    ra["ghi_chu_chan"] = ("Chân XRES là của RIÊNG từng bo; mặc định ở đây lấy theo "
                          "32F469IDISCOVERY (BSP_LCD_Reset trong stm32469i_discovery_lcd.c). "
                          "Bo khác thì truyền `chan_xres`/`odr_xres` khác.")
    ra["thong_suot"] = not ra["dut_o"]
    # Cả chuỗi thông mà mắt vẫn không thấy gì → nói THẲNG phần còn lại nằm ở đâu, thay vì để
    # câu "mọi thứ đều ổn" đứng một mình. Một kết luận toàn dấu ✓ trước một màn hình đen là
    # kiểu báo cáo dạy người ta thôi tin báo cáo.
    if ra["thong_suot"]:
        ra["ket_luan"] = (
            "Mọi mắt phía STM32 đều thông, kể cả “LTDC đang quét” và “không có lỗi trên "
            "đường DSI”. Nếu mắt người vẫn thấy màn đen thì phần còn lại KHÔNG nằm ở cấu "
            "hình phía chip: nghi (1) chuỗi lệnh khởi tạo panel OTM8009A chưa chạy hết hoặc "
            "bị bỏ giữa chừng, (2) lệnh bật màn / đặt độ sáng chưa tới panel, (3) đèn nền, "
            "(4) nhận nhầm loại panel — bo này có hai biến thể, OTM8009A và NT35510.")
    return ra


def doc_khung_anh(dia_chi: int, rong: int, cao: int, dinh_dang: str, ra_tep: Path, *,
                  timeout: float = 300.0) -> dict[str, Any]:
    """Đọc framebuffer từ chip qua SWD rồi ghi thành PNG. Tác tử **xem được** nó đã vẽ gì.

    Vì sao năng lực này đáng có, đo được trên bo STM32F469 ngày 28/09/2026: người dùng nói
    "màn hình đen xì". Câu hỏi đầu tiên phải trả lời là *chương trình vẽ sai, hay nó vẽ đúng
    mà tấm panel không hiện?* Hai nguyên nhân ấy ở hai đầu khác nhau của hệ thống và cách sửa
    không liên quan gì tới nhau — mà nhìn vào một màn hình đen thì không phân biệt được.

    Đọc chính bộ nhớ khung ảnh trả lời được câu đó bằng số: có điểm màu đúng chỗ thì phần vẽ
    xong rồi, lỗi nằm ở đường LTDC → DSI → panel.

    Đây KHÔNG phải ảnh chụp màn hình máy tính. Nó đọc bộ nhớ của con chip trên bàn — không
    liên quan gì tới cửa sổ nào đang mở trên máy, và không dùng `screencapture`.
    """
    ra: dict[str, Any] = {"dat": False, "vi_sao_khong_dat": "", "tep": "",
                          "dia_chi": f"0x{dia_chi:08X}", "rong": rong, "cao": cao,
                          "dinh_dang": dinh_dang}
    if dinh_dang not in DINH_DANG_DIEM:
        ra["vi_sao_khong_dat"] = (f"chưa biết định dạng điểm ảnh `{dinh_dang}`. Biết: "
                                  + ", ".join(DINH_DANG_DIEM))
        return ra
    if rong <= 0 or cao <= 0:
        ra["vi_sao_khong_dat"] = f"kích thước không hợp lệ: {rong}×{cao}."
        return ra
    bpp = DINH_DANG_DIEM[dinh_dang][0]
    so_byte = rong * cao * bpp
    if so_byte > TRAN_BYTE_KHUNG_ANH:
        ra["vi_sao_khong_dat"] = (f"{rong}×{cao}×{bpp} = {so_byte} byte, vượt trần "
                                  f"{TRAN_BYTE_KHUNG_ANH}. Đọc một vùng nhỏ hơn.")
        return ra
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = ("máy chưa có `openocd` nên không đọc được bộ nhớ khung ảnh. "
                                  "Không đọc được KHÁC với màn hình không có gì.")
        return ra
    try:
        from PIL import Image
    except ImportError:
        ra["vi_sao_khong_dat"] = "máy chưa có thư viện Pillow để ghi PNG."
        return ra

    import tempfile

    tho = Path(tempfile.mkdtemp()) / "khung.bin"
    # `dump_image` đọc cả khối một lần. Dùng `mdw` cho 1,5 MB thì phải phân tích hơn ba trăm
    # nghìn dòng chữ — chậm hơn hàng chục lần và dễ mất dòng.
    cl = [oo, "-f", "interface/stlink.cfg", "-f", "target/stm32f4x.cfg",
          "-c", "init", "-c", "halt",
          "-c", f"dump_image {tho} 0x{dia_chi:08x} {so_byte}",
          "-c", "resume", "-c", "exit"]
    try:
        r = subprocess.run(cl, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao_khong_dat"] = f"openocd không chạy được: {type(e).__name__}: {e}"
        return ra
    if not tho.exists() or tho.stat().st_size < so_byte:
        ra["vi_sao_khong_dat"] = (
            f"đọc được {tho.stat().st_size if tho.exists() else 0}/{so_byte} byte. "
            + (((r.stdout or "") + (r.stderr or "")).strip()[-200:] or "không rõ lý do"))
        return ra

    byte = tho.read_bytes()[:so_byte]
    kieu = DINH_DANG_DIEM[dinh_dang][1]
    if kieu == "RGB565":
        anh = Image.frombytes("RGB", (rong, cao), byte, "raw", "BGR;16")
    else:
        anh = Image.frombytes("RGBA" if bpp == 4 else "RGB", (rong, cao), byte, "raw", kieu)
        if bpp == 4:
            anh = anh.convert("RGB")     # kênh alpha của LTDC không nói gì về cái mắt thấy
    ra_tep.parent.mkdir(parents=True, exist_ok=True)
    anh.save(ra_tep, "PNG")
    ra["tep"] = str(ra_tep)
    ra["so_byte"] = so_byte

    # Thống kê để nói được "có vẽ gì không" mà không cần ai mở tệp ảnh ra xem.
    mau = anh.convert("RGB").getcolors(maxcolors=1 << 20)
    if mau:
        mau.sort(reverse=True)
        tong = sum(n for n, _ in mau)
        ra["so_mau"] = len(mau)
        ra["mau_hay_gap"] = [{"mau": "#%02X%02X%02X" % c, "ti_le": round(n / tong, 4)}
                             for n, c in mau[:5]]
        # Một khung ảnh CHỈ có một màu thì chương trình chưa vẽ gì (hoặc mới xoá nền). Đây là
        # phép phân biệt quan trọng nhất của cả hàm, nên nó được tính ra số, không để suy đoán.
        ra["chi_mot_mau"] = len(mau) == 1
    ra["dat"] = True
    return ra


def doc_cau_hinh_ltdc(*, timeout: float = 60.0) -> dict[str, Any]:
    """Đọc từ chính thanh ghi LTDC: khung ảnh ở đâu, bao nhiêu điểm, định dạng gì.

    Không bắt ai gõ tay ba con số ấy vào. Gõ tay thì sai một cái là ảnh đọc ra lệch hàng và
    trông y như "chương trình vẽ sai" — một phép đo tự sinh ra bằng chứng giả.
    """
    LTDC = 0x40016800
    ra: dict[str, Any] = {"dat": False, "vi_sao_khong_dat": ""}
    oo = shutil.which("openocd")
    if not oo:
        ra["vi_sao_khong_dat"] = "máy chưa có `openocd`."
        return ra
    o = _doc_o_nho(oo, [(LTDC + 0x18, 1), (LTDC + 0x84, 1), (LTDC + 0x94, 1),
                        (LTDC + 0xAC, 1), (LTDC + 0xB0, 1), (LTDC + 0xB4, 1),
                        (LTDC + 0x88, 1), (LTDC + 0x8C, 1)], timeout=timeout)

    def _lay(off: int) -> int | None:
        v = o.get(f"0x{LTDC + off:08x}")
        try:
            return int(v[0], 16) if v else None
        except ValueError:
            return None

    gcr, l1cr, pfcr = _lay(0x18), _lay(0x84), _lay(0x94)
    cfbar, cfblr, cfblnr = _lay(0xAC), _lay(0xB0), _lay(0xB4)
    whpcr, wvpcr = _lay(0x88), _lay(0x8C)
    if gcr is None or cfbar is None:
        ra["vi_sao_khong_dat"] = "không đọc được thanh ghi LTDC — chip đang bị giữ, hay cáp SWD?"
        return ra
    ra["dat"] = True
    ra["ltdc_bat"] = bool(gcr & 1)
    ra["lop1_bat"] = bool((l1cr or 0) & 1)
    ra["dia_chi_khung"] = f"0x{cfbar:08X}"
    ra["dinh_dang"] = _PF_LTDC.get((pfcr or 0) & 0x7, f"PF={(pfcr or 0) & 0x7} (chưa biết)")
    ra["cao"] = (cfblnr or 0) & 0x7FF
    bpp = DINH_DANG_DIEM.get(ra["dinh_dang"], (0,))[0]
    # Bước dòng (pitch) nằm ở 16 bit cao của CFBLR; chiều rộng suy từ nó, không đoán.
    buoc = ((cfblr or 0) >> 16) & 0x1FFF
    ra["buoc_dong"] = buoc
    ra["rong"] = buoc // bpp if bpp else 0
    if whpcr is not None and wvpcr is not None:
        ra["rong_cua_so"] = ((whpcr >> 16) & 0xFFF) - (whpcr & 0xFFF) + 1
        ra["cao_cua_so"] = ((wvpcr >> 16) & 0x7FF) - (wvpcr & 0x7FF) + 1
    return ra


# Một hàm có nói chuyện với phần cứng thì không thể nhỏ hơn chừng này byte mã: nạp địa chỉ
# thanh ghi, ghi, đợi, đọc về — riêng phần đó đã vài chục byte. Ngưỡng là quy ước và được nói
# ra, không giấu trong một câu kết luận.
NGUONG_HAM_RONG_TUECH = 16


def _phan_loai_ham_nho(elf: Path, dia_chi: int, kich_thuoc: int, ten: str, *,
                       timeout: float = 30.0) -> dict[str, Any]:
    """Một hàm nhỏ: nó TRẢ HẰNG SỐ, hay chỉ là vỏ mỏng nhảy sang hàm thật?

    Hai thứ này cùng nhỏ như nhau và nghĩa ngược hẳn nhau. Trả hằng số = phép đo giả; vỏ mỏng
    = hoàn toàn bình thường. Phân biệt bằng chính mã máy, không bằng kích thước.
    """
    od = shutil.which("arm-none-eabi-objdump")
    if not od:
        return {"canh_bao": (f"`{ten}` chỉ có {kich_thuoc} byte mã, nhưng máy chưa có "
                             "`arm-none-eabi-objdump` nên chưa phân biệt được “trả hằng số” "
                             "với “vỏ mỏng gọi hàm khác”. Chưa kết luận."),
                "ma_may": ""}
    try:
        r = subprocess.run([od, "-d", f"--start-address=0x{dia_chi:x}",
                            f"--stop-address=0x{dia_chi + kich_thuoc:x}", str(elf)],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return {"canh_bao": "", "ma_may": ""}
    # objdump in `  địa chỉ:\tbyte mã\tlệnh\ttoán hạng`. Lệnh ở cột THỨ BA.
    # Bản đầu lấy `split("\t")[-1]` — đó là cột toán hạng, nên từ khoá lệnh bị mất sạch và
    # phép dò "có nhảy không" luôn trả lời KHÔNG. Nó gán nhãn "trả hằng số" cho cả
    # `BSP_LCD_Init` (thật ra là `movs r0,#1` rồi `b.w BSP_LCD_InitEx`) — đúng loại báo động
    # giả mà cả hàm này sinh ra để tránh.
    lenh: list[tuple[str, str]] = []
    for l in (r.stdout or "").splitlines():
        c = l.split("\t")
        if len(c) >= 3 and c[0].strip().endswith(":"):
            lenh.append((c[2].strip(), c[3].strip() if len(c) > 3 else ""))
    ma = " ; ".join((m + " " + t).strip() for m, t in lenh)
    # `b`, `bl`, `blx`, `b.w`, `b.n` — nhảy đi chỗ khác. `bx lr` là TRỞ VỀ, không tính.
    nhay = any(re.fullmatch(r"(bl|blx|b|b\.w|b\.n)", m)
               or (m.startswith("bx") and not t.startswith("lr"))
               for m, t in lenh)
    if nhay:
        return {"rong_tuech": False, "vo_mong": True, "ma_may": ma,
                "ghi_chu": (f"`{ten}` chỉ {kich_thuoc} byte nhưng CÓ lệnh nhảy — đây là vỏ "
                            "mỏng gọi sang hàm khác, không phải hàm trả hằng số. Bình thường.")}
    return {"tra_hang_so": True, "ma_may": ma,
            "canh_bao": (f"`{ten}` chỉ có {kich_thuoc} byte mã và KHÔNG có lệnh nhảy nào — "
                         f"thân nó chỉ nạp một hằng số rồi trở về ({ma}). "
                         "Giá trị nó trả về là lời của MÃ, không phải lời của phần cứng. Mọi "
                         "kết luận dựa vào nó đều là kết luận về chính mã nguồn.")}


def ky_hieu_theo_ten(elf: Path, ten: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    """Tên biến/hàm → địa chỉ và KÍCH THƯỚC, đọc từ bảng ký hiệu của ELF (`nm -S`).

    Hai việc, và việc thứ hai mới là lý do hàm này đáng có.

    **Địa chỉ**: để đọc được một biến toàn cục trên chip đang chạy mà không phải đi tra địa
    chỉ bằng tay. Đo được trên bo STM32F469 ngày 28/09/2026: đọc `Lcd_Driver_Type` ra `1` =
    `LCD_CTRL_OTM8009A`, tức chương trình *tin rằng* nó đang nói chuyện với panel OTM8009A.

    **Kích thước**: để hỏi tiếp câu mà con số kia không trả lời được — *vì sao* nó tin thế.
    `OTM8009A_ReadID()` trên bo ấy chỉ có **6 byte mã**, vì thân hàm là `return OTM8009A_ID;`.
    Một hàm sáu byte không thể vừa gửi lệnh qua DSI vừa đợi panel trả lời. Nói cách khác:
    phép "dò loại panel" không dò gì cả, nó **khai báo** kết quả — và biến `Lcd_Driver_Type`
    là lời của mã, không phải lời của phần cứng.

    Đây đúng là N6 (không báo đạt giả) xuất hiện bên trong firmware thay vì bên trong EIDE, và
    nó sống sót qua mười lượt gỡ lỗi vì mọi phép đo đều hỏi "giá trị bằng bao nhiêu" chứ không
    ai hỏi "ai đặt ra giá trị ấy".
    """
    ra: dict[str, Any] = {"dat": False, "ky_hieu": {}, "vi_sao_khong_dat": ""}
    if not elf.exists():
        ra["vi_sao_khong_dat"] = f"không có {elf.name} — biên dịch trước."
        return ra
    nm = shutil.which("arm-none-eabi-nm")
    if not nm:
        ra["vi_sao_khong_dat"] = ("máy chưa có `arm-none-eabi-nm`. Không tra được KHÁC với "
                                  "ký hiệu không tồn tại.")
        return ra
    try:
        r = subprocess.run([nm, "-S", "--defined-only", str(elf)],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao_khong_dat"] = f"nm không chạy được: {type(e).__name__}: {e}"
        return ra
    if r.returncode != 0:
        ra["vi_sao_khong_dat"] = "nm thất bại: " + ((r.stderr or "").strip()[-160:] or "?")
        return ra

    muon = set(ten)
    for dong in (r.stdout or "").splitlines():
        p = dong.split()
        # `nm -S` in "địa chỉ [kích thước] loại tên". Kích thước vắng mặt với một số ký hiệu,
        # nên phải chấp nhận cả ba cột lẫn bốn cột — bỏ qua dòng ba cột thì mất đúng những
        # ký hiệu không có kích thước, và chúng im lặng biến thành "không tìm thấy".
        if len(p) == 4:
            dc, kt, loai, t = p[0], int(p[1], 16), p[2], p[3]
        elif len(p) == 3:
            dc, kt, loai, t = p[0], 0, p[1], p[2]
        else:
            continue
        if t not in muon:
            continue
        la_ham = loai.upper() in ("T", "W")
        ra["ky_hieu"][t] = {
            "dia_chi": int(dc, 16), "dia_chi_hex": f"0x{int(dc, 16):08X}",
            "kich_thuoc": kt, "loai": loai, "la_ham": la_ham,
            "rong_tuech": bool(la_ham and 0 < kt < NGUONG_HAM_RONG_TUECH),
        }
    # Hàm nhỏ CHƯA đủ để kết luận. `BSP_LCD_Init` cũng chỉ 6 byte, nhưng thân nó là
    # `return BSP_LCD_InitEx(...)` — một vỏ mỏng nhảy tiếp sang hàm thật, và nó CÓ chạm phần
    # cứng. Gọi nó là "trả hằng số" là một báo động giả, và báo động giả dạy người ta bỏ qua
    # cảnh báo. Thứ phân biệt được nằm trong chính mã máy: có lệnh nhảy đi đâu không.
    for t, v in ra["ky_hieu"].items():
        if v["rong_tuech"]:
            v.update(_phan_loai_ham_nho(elf, v["dia_chi"], v["kich_thuoc"], t,
                                        timeout=timeout))
    ra["thieu"] = sorted(muon - set(ra["ky_hieu"]))
    ra["dat"] = bool(ra["ky_hieu"])
    if not ra["dat"]:
        ra["vi_sao_khong_dat"] = f"không thấy ký hiệu nào trong ELF: {', '.join(sorted(muon))}"
    return ra


def khop_tai_dia_chi(bin_path: Path, dia_chi: int, *, so_byte: int = 32,
                     goc_flash: int = 0x08000000, timeout: float = 60.0) -> dict[str, Any]:
    """Mã tại đúng địa chỉ này trên chip có giống tệp vừa dịch không?

    Đây là phanh cho `giai_ma_dia_chi`. `addr2line` luôn trả về một cái tên nghe thuyết phục
    — của bản ELF đang có trên đĩa. Dịch lại mà chưa nạp là chuyện xảy ra liên tục, và khi đó
    cái tên ấy là tên của một hàm KHÔNG nằm trên chip. Một chẩn đoán dựa vào nó sẽ sai theo
    kiểu khó phát hiện nhất: đúng cú pháp, đúng giọng, sai chỗ.

    Chỉ đọc `so_byte` byte quanh địa chỉ, không đọc ngược cả ảnh nạp: câu hỏi ở đây hẹp — "mã
    ở CHỖ NÀY có phải mã tôi đang đọc tên không" — và một phép đo 32 byte trả lời nó trong
    một giây, nên nó chạy được ở mỗi lần soi chip mà không ai phải chờ.
    """
    import tempfile

    ra: dict[str, Any] = {"do_duoc": False, "khop": False, "vi_sao": "",
                          "dia_chi": f"0x{dia_chi:08X}"}
    st = shutil.which("st-flash")
    if not st:
        ra["vi_sao"] = "chưa có `st-flash` nên không đối chiếu được mã trên chip."
        return ra
    if not bin_path.exists():
        ra["vi_sao"] = f"không có {bin_path.name} để đối chiếu."
        return ra
    lech = dia_chi - goc_flash
    mong_tat_ca = bin_path.read_bytes()
    if lech < 0 or lech >= len(mong_tat_ca):
        ra["vi_sao"] = (f"địa chỉ {ra['dia_chi']} nằm ngoài ảnh nạp "
                        f"({len(mong_tat_ca)} byte từ 0x{goc_flash:08X}) — có thể nó ở RAM, "
                        "ở bootloader, hoặc chip đang chạy bản khác hẳn.")
        return ra
    lech &= ~0x3                                   # st-flash đọc theo từ 32-bit
    n = min(so_byte, len(mong_tat_ca) - lech)
    mong = mong_tat_ca[lech:lech + n]
    dich = Path(tempfile.mkdtemp()) / "mot-doan.bin"
    try:
        r = subprocess.run([st, "read", str(dich), f"0x{goc_flash + lech:08x}", str(n)],
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        ra["vi_sao"] = f"st-flash read không chạy được: {type(e).__name__}: {e}"
        return ra
    if r.returncode != 0 or not dich.exists():
        ra["vi_sao"] = "st-flash read thất bại: " + ((r.stderr or "").strip()[-160:] or "?")
        return ra
    that = dich.read_bytes()[:n]
    ra["do_duoc"] = True
    ra["so_byte"] = n
    ra["khop"] = that == mong
    if not ra["khop"]:
        ra["vi_sao"] = (f"{n} byte tại {ra['dia_chi']} trên chip KHÁC tệp vừa dịch — tên hàm "
                        "giải mã từ ELF không nói về mã đang chạy. Nạp lại rồi soi lại.")
    return ra


# Bit của CFSR → nghĩa. Chỉ những bit trả lời được câu "vì sao fault", không liệt kê cho đủ.
_BIT_CFSR: tuple[tuple[int, str], ...] = (
    (1 << 0, "IACCVIOL — nhảy tới vùng không được thực thi"),
    (1 << 1, "DACCVIOL — đọc/ghi vùng bị MPU cấm"),
    (1 << 3, "MUNSTKERR — lỗi khi khôi phục ngăn xếp lúc ra khỏi ngắt"),
    (1 << 4, "MSTKERR — lỗi khi đẩy ngăn xếp lúc vào ngắt (ngăn xếp tràn?)"),
    (1 << 7, "MMARVALID — địa chỉ gây lỗi nằm ở MMFAR"),
    (1 << 8, "IBUSERR — lỗi bus khi nạp lệnh"),
    (1 << 9, "PRECISERR — lỗi bus CHÍNH XÁC: địa chỉ ở BFAR là chỗ gây lỗi"),
    (1 << 10, "IMPRECISERR — lỗi bus KHÔNG chính xác (ghi bị đệm); địa chỉ không tin được"),
    (1 << 11, "UNSTKERR — lỗi bus khi khôi phục ngăn xếp"),
    (1 << 12, "STKERR — lỗi bus khi đẩy ngăn xếp"),
    (1 << 15, "BFARVALID — địa chỉ gây lỗi nằm ở BFAR"),
    (1 << 16, "UNDEFINSTR — lệnh không hợp lệ"),
    (1 << 17, "INVSTATE — sai trạng thái Thumb (thiếu bit 0 ở địa chỉ hàm?)"),
    (1 << 18, "INVPC — trả về từ ngắt sai"),
    (1 << 19, "NOCP — dùng coprocessor chưa bật (FPU chưa bật?)"),
    (1 << 24, "UNALIGNED — truy cập không căn chỉnh"),
    (1 << 25, "DIVBYZERO — chia cho 0"),
)


def _doc_thanh_ghi_loi(o_nho: dict[str, list[str]]) -> dict[str, Any]:
    """CFSR/MMFAR/BFAR → lời người đọc được. Rỗng nếu không đọc được."""
    ra: dict[str, Any] = {}
    cfsr_raw = o_nho.get("0xe000ed28") or o_nho.get("0xE000ED28")
    if not cfsr_raw:
        return ra
    try:
        cfsr = int(cfsr_raw[0], 16)
        hfsr = int(cfsr_raw[1], 16) if len(cfsr_raw) > 1 else 0
    except (ValueError, IndexError):
        return ra
    ra["cfsr"] = f"0x{cfsr:08X}"
    ra["hfsr"] = f"0x{hfsr:08X}"
    ra["nghia"] = [ten for bit, ten in _BIT_CFSR if cfsr & bit]
    mm = o_nho.get("0xe000ed34") or o_nho.get("0xE000ED34")
    if mm:
        ra["mmfar"] = f"0x{int(mm[0], 16):08X}" if cfsr & (1 << 7) else "(không hợp lệ)"
        if len(mm) > 1:
            ra["bfar"] = f"0x{int(mm[1], 16):08X}" if cfsr & (1 << 15) else "(không hợp lệ)"
    if hfsr & (1 << 30):
        ra["nghia"].append("FORCED — HardFault do một fault khác bị leo thang lên")
    return ra


# =========================================================================== đọc log
def doc_log(cong: str, *, baud: int = 115200, giay: float = 5.0,
            tran_byte: int = 64 * 1024) -> dict[str, Any]:
    """Đọc cổng nối tiếp trong `giay` giây. Không có chữ nào thì NÓI im lặng, đừng suy diễn.

    Không dùng pyserial: đặt baud bằng `stty` rồi đọc tệp thiết bị. Một phụ thuộc ít hơn cho
    việc chỉ cần đọc byte thô, và `stty` có sẵn trên mọi macOS/Linux.
    """
    p = Path(cong)
    ra: dict[str, Any] = {"cong": cong, "baud": baud, "giay": giay,
                          "so_byte": 0, "chu": "", "im_lang": True, "canh_bao": []}
    if not p.exists():
        ra["loi"] = f"Không có cổng {cong}. Bo đã bị rút, hoặc tên cổng khác."
        return ra
    try:
        subprocess.run(["stty", "-f", cong, str(baud), "raw", "-echo"],
                       capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as e:
        ra["canh_bao"].append(f"không đặt được baud bằng stty: {e}")

    dem = bytearray()
    het = time.time() + giay
    try:
        # Mở không chặn: một cổng không có ai gửi gì sẽ làm `read` treo tới hết thời gian chờ
        # của tiến trình, và một phép đo treo trông y như một hệ thống chết.
        import os as _os

        fd = _os.open(cong, _os.O_RDONLY | _os.O_NONBLOCK)
        try:
            while time.time() < het and len(dem) < tran_byte:
                try:
                    b = _os.read(fd, 4096)
                except BlockingIOError:
                    time.sleep(0.05)
                    continue
                except OSError as e:
                    ra["canh_bao"].append(f"đọc dừng giữa đường: {e}")
                    break
                if b:
                    dem += b
                else:
                    time.sleep(0.05)
        finally:
            _os.close(fd)
    except OSError as e:
        ra["loi"] = f"Không mở được {cong}: {e}"
        return ra

    ra["so_byte"] = len(dem)
    ra["chu"] = dem.decode("utf-8", errors="replace")
    ra["im_lang"] = len(dem) == 0
    if ra["im_lang"]:
        ra["canh_bao"].append(
            f"Cổng {cong} không gửi byte nào trong {giay:.0f} s. Điều đó KHÔNG chứng minh "
            "firmware sai: có thể firmware chưa in gì, sai baud, hoặc in ra UART khác. Kiểm "
            "baud trong mã và chân UART nối tới ST-LINK trước khi kết luận.")
    return ra
