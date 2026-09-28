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
        ra.append(BoTimDuoc(loai="cong_noi_tiep", duong_dan=str(p), ten=ten,
                            co_the_la_bo=la_bo,
                            biet_bang_cach=f"/dev/{ten}: {vi_sao}"))
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
