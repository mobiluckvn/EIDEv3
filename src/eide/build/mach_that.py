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


def soi_chip(dia_chi: list[int] | None = None, *, so_tu: int = 4,
             timeout: float = 60.0) -> dict[str, Any]:
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
