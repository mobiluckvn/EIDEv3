# -*- coding: utf-8 -*-
"""Luồng công cụ HDL: từ Verilog tới tệp cấu hình nạp được vào FPGA.

Bốn chặng rời nhau, bốn chương trình khác nhau:

    Verilog ──yosys──▶ mạng cổng ──nextpnr──▶ bố trí đã đi dây ──gowin_pack──▶ .fs ──▶ FPGA

Chặng nào thiếu thì ba chặng kia vô dụng, nên cả bốn đều bắt buộc.

Ba điều tệp này cố ý làm, và cả ba đều học từ những chỗ đã sai thật trong dự án này:

1. **Không kết luận từ mã thoát.** Mỗi chặng chỉ "đạt" khi có **tệp ra trên đĩa và tệp ấy
   không rỗng**. Một chương trình trả 0 mà không sinh ra tệp nào là chuyện đã gặp (ở phần
   biên dịch ARM, DEV-275), và tin vào mã thoát thì ta báo xong cho một thứ không tồn tại.

2. **Con số đọc từ đầu ra thật, không đoán.** Số LUT, số FF, số BSRAM, số DSP và Fmax đều
   trích bằng biểu thức từ nguyên văn của `yosys` và `nextpnr`. Không có con số nào trong tệp
   này được tính ra bằng công thức — chúng là thứ ta đi đo để biết thiết kế có vừa chip
   không, nên một con số ước lượng ở đây sẽ bị đem so với hạn mức thật và cho kết luận sai.

3. **Kết quả mô phỏng do CHƯƠNG TRÌNH nói, không do lời văn.** `hdl.sim` đọc `PASS`/`FAIL` mà
   testbench tự in ra. Đề bài của anh Công ghi thẳng: *"Testbench phải tự kiểm tra và in
   PASS/FAIL. Không dựa vào việc người xem dạng sóng."*
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .toolchain import _tim_lenh

# Hạn thời gian từng chặng, tính bằng giây. Tổng hợp và đặt-đi dây một lõi CPU mất vài phút,
# nên hạn phải rộng; nhưng không được vô hạn — một chặng treo mà không có hạn thì cả lượt treo
# theo, và người dùng không có cách nào biết nên chờ tới bao giờ.
HAN_GIAY = {"lint": 120, "sim": 900, "synth": 1800, "pnr": 1800, "pack": 300}

# Thiết bị Gowin của kit Tang Nano 20K. Hai chuỗi này KHÁC NHAU và không thay nhau được:
# `yosys`/`nextpnr` nhận tên họ chip, `gowin_pack` nhận mã đóng gói đầy đủ.
THIET_BI = {
    "tangnano20k": {"family": "GW2A-18C", "device": "GW2AR-LV18QN88C8/I7",
                    "pack": "GW2AR-18C", "mo_ta": "Sipeed Tang Nano 20K"},
}


@dataclass(slots=True)
class KetQuaHdl:
    """Kết quả một chặng. `dat` chỉ True khi có tệp ra THẬT trên đĩa."""

    chang: str = ""
    dat: bool = False
    cong_cu: str = ""
    lenh: list[str] = field(default_factory=list)
    ma_thoat: int | None = None
    giay: float = 0.0
    tep_ra: str = ""
    so_byte_ra: int = 0
    tai_nguyen: dict[str, Any] = field(default_factory=dict)
    fmax_mhz: float | None = None
    loi: list[dict[str, Any]] = field(default_factory=list)
    canh_bao: list[dict[str, Any]] = field(default_factory=list)
    pass_fail: str = ""           # "PASS" | "FAIL" | "" — do testbench tự in
    # Độ nhạy bộ kiểm: bắt mấy trên mấy phép phá mã. Rỗng nghĩa là CHƯA ĐO, và khối A8.0
    # nói ra điều đó thay vì im lặng hiện một chữ PASS màu xanh — một bộ kiểm PASS mà chưa
    # ai phá mã thì chưa biết nó canh được gì.
    do_nhay: dict[str, int] = field(default_factory=dict)
    nguyen_van: str = ""
    vi_sao_khong_dat: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"chang": self.chang, "dat": self.dat, "cong_cu": self.cong_cu,
                "lenh": list(self.lenh), "ma_thoat": self.ma_thoat,
                "giay": round(self.giay, 2),
                "tep_ra": self.tep_ra, "so_byte_ra": self.so_byte_ra,
                "tai_nguyen": dict(self.tai_nguyen), "fmax_mhz": self.fmax_mhz,
                "so_loi": len(self.loi), "so_canh_bao": len(self.canh_bao),
                "loi": self.loi[:30], "canh_bao": self.canh_bao[:20],
                "pass_fail": self.pass_fail,
                "do_nhay": dict(self.do_nhay),
                "vi_sao_khong_dat": self.vi_sao_khong_dat,
                "nguyen_van": self.nguyen_van[-4000:]}


# ------------------------------------------------------------------ đọc thông điệp công cụ

# Verilator và Icarus báo lỗi theo cùng hình dạng `%Error: tệp:dòng:cột: thông điệp`, nhưng
# Verilator thêm tiền tố `%Error`/`%Warning` còn Icarus thì không.
_MAU_VERILATOR = re.compile(
    r"^%(?P<muc>Error|Warning)(?:-(?P<ma>[A-Z_]+))?:\s*"
    r"(?P<tep>[^\s:][^:]*):(?P<dong>\d+):(?:(?P<cot>\d+):)?\s*(?P<td>.*)$")
_MAU_ICARUS = re.compile(
    r"^(?P<tep>[^\s:][^:]*\.s?v):(?P<dong>\d+):\s*(?P<muc>error|warning|sorry):\s*(?P<td>.*)$",
    re.I)
# Yosys không dùng toạ độ cho mọi lỗi; nhiều thông điệp chỉ là `ERROR: ...`.
_MAU_YOSYS = re.compile(r"^(?P<muc>ERROR|Warning):\s*(?P<td>.*)$")


def doc_thong_diep(dau_ra: str, *, goc: Path | None = None) -> tuple[list, list]:
    """Tách lỗi và cảnh báo của công cụ HDL thành bản ghi có toạ độ khi có thể.

    Dòng nào không có toạ độ vẫn được giữ, với `dong = 0`. Bỏ chúng đi thì lỗi của Yosys —
    phần lớn không có toạ độ — biến mất hoàn toàn, và người đọc nhận về "trả mã 1 nhưng không
    có lỗi nào", đúng câu vô dụng mà bản ARM từng trả.
    """
    loi: list[dict[str, Any]] = []
    canh: list[dict[str, Any]] = []

    def _tuong_doi(t: str) -> str:
        if goc is None:
            return t
        try:
            return str(Path(t).resolve().relative_to(goc.resolve()))
        except (ValueError, OSError):
            return t

    for d in dau_ra.splitlines():
        d = d.rstrip()
        m = _MAU_VERILATOR.match(d.strip()) or _MAU_ICARUS.match(d.strip())
        if m:
            g = m.groupdict()
            ban = {"tep": _tuong_doi(g["tep"]), "dong": int(g["dong"]),
                   "cot": int(g.get("cot") or 0), "thong_diep": g["td"].strip(),
                   "ma": g.get("ma") or ""}
            (loi if g["muc"].lower().startswith(("error", "sorry")) else canh).append(ban)
            continue
        m = _MAU_YOSYS.match(d.strip())
        if m:
            ban = {"tep": "", "dong": 0, "cot": 0,
                   "thong_diep": m.group("td").strip(), "ma": ""}
            (loi if m.group("muc") == "ERROR" else canh).append(ban)
    return loi, canh


# Yosys in bảng đếm ô dạng `        25   LUT1` — **số đứng TRƯỚC tên**, không phải ngược lại.
#
# Đòi ít nhất HAI khoảng trắng giữa số và tên là chỗ phân biệt duy nhất: cùng bảng ấy còn có
# `      109 wires` và `       60 cells` — một khoảng trắng — là thống kê chung chứ không phải
# loại ô. Nhận nhầm chúng thì bảng tài nguyên có một dòng tên "wires" với 109 "ô".
_MAU_O_YOSYS = re.compile(r"^\s+(?P<so>\d+)\s{2,}(?P<ten>[A-Za-z_][\w\.]*)\s*$")

# Ô của họ GW2A, gom về tên người đọc hiểu. Khoá là tiền tố, vì Yosys đặt tên theo biến thể
# (`LUT1`…`LUT4`, `DFFRE`, `DFFCE`…) và đếm riêng từng loại — cộng rời thì bảng dài vô ích.
_GOM_O = (("LUT", "lut"), ("MUX2_LUT", "lut"), ("ALU", "lut"), ("DFF", "ff"), ("SDP", "bsram"),
          ("DP", "bsram"), ("SP", "bsram"), ("pROM", "bsram"), ("MULT", "dsp"),
          ("PADD", "dsp"), ("ALU54", "dsp"), ("IBUF", "io"), ("OBUF", "io"),
          ("IOBUF", "io"), ("TBUF", "io"))


def doc_tai_nguyen_yosys(dau_ra: str) -> dict[str, int]:
    """Đếm ô từ bảng `Printing statistics` của Yosys.

    Gom theo nhóm người đọc hiểu (lut / ff / bsram / dsp / io) **và** giữ nguyên bảng chi tiết,
    vì hai thứ trả lời hai câu khác nhau: nhóm trả lời "có vừa chip không", chi tiết trả lời
    "chỗ nào ăn tài nguyên".

    Chỉ đọc bảng thống kê CUỐI CÙNG. Yosys in bảng sau mỗi bước, và bảng đầu là trước khi ánh
    xạ về ô của chip — lấy nhầm bảng ấy thì con số không nói gì về chip này.
    """
    # Ưu tiên khối "design hierarchy" — nó đếm **cả mô-đun con**. Khối "Local Count" ngay
    # trên nó chỉ đếm mô-đun đỉnh, nên với một SoC có CPU bên trong, nó báo vài chục ô cho một
    # thiết kế thật ra dùng vài nghìn. Thiết kế phẳng thì hai khối trùng nhau, nên lấy khối
    # sau không bao giờ sai.
    if "=== design hierarchy ===" in dau_ra:
        phan = dau_ra.rsplit("=== design hierarchy ===", 1)[-1]
    else:
        khoi = dau_ra.rsplit("Printing statistics.", 1)
        phan = khoi[-1] if len(khoi) > 1 else dau_ra
    chi_tiet: dict[str, int] = {}
    for d in phan.splitlines():
        m = _MAU_O_YOSYS.match(d)
        if m:
            chi_tiet[m.group("ten")] = int(m.group("so"))
    gom: dict[str, int] = {}
    for ten, so in chi_tiet.items():
        for tien_to, nhom in _GOM_O:
            if ten.upper().startswith(tien_to.upper()):
                gom[nhom] = gom.get(nhom, 0) + so
                break
    if chi_tiet:
        gom["chi_tiet"] = chi_tiet          # type: ignore[assignment]
    return gom


# nextpnr in:  `Info: Max frequency for clock '...': 42.19 MHz (PASS at 27.00 MHz)`
_MAU_FMAX = re.compile(
    r"Max frequency for clock\s+'(?P<clk>[^']*)':\s*(?P<f>[\d.]+)\s*MHz"
    r"(?:\s*\((?P<ket>PASS|FAIL)\s+at\s+(?P<dich>[\d.]+)\s*MHz\))?", re.I)
# và:  `Info:            LUT4:  1234/20736    5%`
_MAU_DUNG_PNR = re.compile(
    r"^\s*(?:Info:)?\s*(?P<ten>[A-Za-z_][\w]*)\s*:\s*(?P<dung>\d+)\s*/\s*(?P<tong>\d+)")


def doc_ket_qua_pnr(dau_ra: str) -> tuple[float | None, dict[str, Any], list[dict[str, Any]]]:
    """Fmax và mức dùng tài nguyên, đọc từ nguyên văn `nextpnr`.

    Trả `(fmax_mhz, tai_nguyen, dong_ho)`. `fmax_mhz` là **nhỏ nhất** trong các miền đồng hồ —
    lấy lớn nhất thì một thiết kế có hai đồng hồ, một nhanh một chậm, sẽ báo con số của cái
    nhanh và che mất cái không đạt.
    """
    dong_ho = [{"dong_ho": m.group("clk"), "fmax_mhz": float(m.group("f")),
                "ket": (m.group("ket") or "").upper(),
                "dich_mhz": float(m.group("dich")) if m.group("dich") else None}
               for m in _MAU_FMAX.finditer(dau_ra)]
    fmax = min((d["fmax_mhz"] for d in dong_ho), default=None)

    dung: dict[str, Any] = {}
    for d in dau_ra.splitlines():
        m = _MAU_DUNG_PNR.match(d)
        if not m:
            continue
        tong = int(m.group("tong"))
        if tong <= 0:
            continue
        dung[m.group("ten")] = {"dung": int(m.group("dung")), "tong": tong,
                                "ty_le": round(int(m.group("dung")) / tong, 4)}
    return fmax, dung, dong_ho


# ------------------------------------------------------------------ chạy một chặng

def _diet_ca_nhom(p: subprocess.Popen, cho_giay: float = 3.0) -> None:
    """Diệt cả nhóm tiến trình, không chỉ tiến trình con trực tiếp.

    Thử `SIGTERM` trước để công cụ kịp dọn tệp tạm, rồi `SIGKILL` cho những gì còn sống.
    Nếu nhóm đã tan thì `ProcessLookupError` là chuyện bình thường, không phải lỗi.
    """
    import signal

    try:
        nhom = os.getpgid(p.pid)
    except ProcessLookupError:
        return
    for tin_hieu in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(nhom, tin_hieu)
        except ProcessLookupError:
            return
        try:
            p.wait(timeout=cho_giay if tin_hieu == signal.SIGTERM else 1.0)
            return
        except subprocess.TimeoutExpired:
            continue


def _chay(kq: KetQuaHdl, lenh: list[str], *, cwd: Path, han: int,
          goc: Path | None = None) -> None:
    """Chạy một chương trình, ghi nguyên văn và thông điệp vào `kq`. KHÔNG kết luận `dat`."""
    import time

    kq.lenh = [str(x) for x in lenh]
    t0 = time.monotonic()
    try:
        # `HOME` giữ nguyên nhưng thêm `XDG_*` trỏ vào chỗ ghi được: gói oss-cad-suite cố ghi
        # vào `~/.local/share`, mà thư mục ấy trên máy này do root sở hữu. Không đặt thì mỗi
        # lời gọi in thêm một dòng "Permission denied" trông như lỗi mà không phải.
        moi = {**os.environ}
        kho = Path.home() / ".eide/cong-cu/xdg"
        kho.mkdir(parents=True, exist_ok=True)
        moi.setdefault("XDG_DATA_HOME", str(kho))
        moi.setdefault("XDG_CACHE_HOME", str(kho / "cache"))
        moi["LC_ALL"] = "C"
        # `start_new_session=True` đặt tiến trình vào một NHÓM riêng, và lúc hết hạn ta diệt
        # cả nhóm. Bản trước dùng `subprocess.run(timeout=...)`, mà nó chỉ diệt đúng tiến
        # trình con trực tiếp. `yosys` gọi `sh -c yosys-abc ...`, nên diệt `yosys` xong thì
        # `sh` và `yosys-abc` SỐNG SÓT và tiếp tục cày. Ngày 02/10/2026 một `yosys-abc` mồ
        # côi chạy 49 phút sau khi lượt tổng hợp của nó đã bị dừng và đã báo trượt — nó
        # giành CPU của lượt chạy kế tiếp, nên lượt sau chậm đi mà không ai biết vì sao.
        # Một phép đo thời gian bị một tiến trình mồ côi làm lệch là một phép đo sai mà
        # trông không có gì sai cả.
        p = subprocess.Popen(kq.lenh, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, cwd=str(cwd), env=moi, start_new_session=True)
        try:
            ra, loi = p.communicate(timeout=han)
            kq.ma_thoat = p.returncode
            kq.nguyen_van = ((ra or "") + "\n" + (loi or "")).strip()
        except subprocess.TimeoutExpired:
            _diet_ca_nhom(p)
            ra, loi = p.communicate()
            kq.ma_thoat = None
            kq.nguyen_van = (((ra or "") + "\n" + (loi or "")).strip()
                             + f"\n(quá hạn {han} s — đã dừng cả nhóm tiến trình)").strip()
            kq.vi_sao_khong_dat = (
                f"`{Path(kq.lenh[0]).name}` chạy quá {han} giây và bị dừng. Đây KHÔNG phải "
                "kết luận về thiết kế — chỉ là hết hạn chờ. Thiết kế lớn thì nới hạn; thiết "
                "kế có vòng lặp tổ hợp thì công cụ sẽ chạy mãi, hãy xem lại mã trước khi nới.")
    except FileNotFoundError:
        kq.ma_thoat = None
        kq.vi_sao_khong_dat = f"Không chạy được `{kq.lenh[0]}` — không thấy tệp lệnh."
    kq.giay = time.monotonic() - t0
    # CỘNG THÊM, không gán. Bên gọi có thể đã đặt vào đây những cảnh báo mà công cụ không
    # thể tự biết — ví dụ "mã máy không chứa lệnh nhân nào mà cấu hình lại bật bộ nhân".
    # Bản đầu viết `kq.loi, kq.canh_bao = ...`, và phép gán ấy xoá sạch chúng. Cảnh báo
    # được dựng ra rồi bị bỏ đi trong im lặng: đúng cái mẫu cơ chế có sẵn mà đường dẫn tới
    # nó đứt, và lần này chính bộ kiểm bắt được.
    loi_moi, canh_moi = doc_thong_diep(kq.nguyen_van, goc=goc)
    kq.loi = list(kq.loi) + loi_moi
    kq.canh_bao = list(kq.canh_bao) + canh_moi


def _don_tep_ra(ra: Path) -> None:
    """Xoá tệp ra TRƯỚC khi chạy, để "tệp có mặt" nghĩa là "lần chạy NÀY sinh ra nó".

    Không có bước này thì một tệp còn sót từ lần chạy trước làm chặng thất bại báo thành công.
    Đo được ngày 01/10/2026: `nextpnr` dừng với `ERROR: Failed to open ... No such file` và trả
    mã 1, nhưng `blinky_pnr.json` của lần chạy trước vẫn nằm đó — nên chặng báo **đạt**, kèm
    `fmax_mhz=None`, và phép canh định thời bị bỏ qua hoàn toàn.

    Trong một dây chuyền nhiều chặng, đây là lỗi nguy hiểm nhất: chặng sau ăn tệp CŨ, mọi thứ
    xanh, và bitstream mang thiết kế của lần sửa trước.
    """
    try:
        ra.unlink(missing_ok=True)
    except OSError:
        pass


def _doi_tep_ra(kq: KetQuaHdl, ra: Path, goc: Path) -> None:
    """Chốt `dat` bằng TỆP TRÊN ĐĨA **do lần chạy này sinh ra**, không bằng mã thoát.

    Ba điều kiện, thiếu một là không đạt:
      1. lệnh không trả mã lỗi,
      2. tệp ra có mặt,
      3. tệp ra không rỗng.

    Điều kiện 1 từng không có. Khi ấy một lệnh thất bại mà tệp cũ còn sót lại vẫn báo đạt.
    """
    if kq.vi_sao_khong_dat:
        return
    if kq.ma_thoat not in (0, None):
        kq.vi_sao_khong_dat = (
            f"`{Path(kq.lenh[0]).name}` trả mã {kq.ma_thoat} với {len(kq.loi)} lỗi."
            if kq.loi else
            f"`{Path(kq.lenh[0]).name}` trả mã {kq.ma_thoat} nhưng không in ra lỗi nào có "
            "toạ độ — xem nguyên văn đầu ra.")
        return
    if False and not ra.exists():
        kq.vi_sao_khong_dat = (
            f"`{Path(kq.lenh[0]).name}` trả mã {kq.ma_thoat} với {len(kq.loi)} lỗi."
            if kq.loi else
            f"`{Path(kq.lenh[0]).name}` trả mã {kq.ma_thoat} nhưng không in ra lỗi nào — "
            "xem nguyên văn đầu ra.")
        return
    if not ra.exists():
        kq.vi_sao_khong_dat = (
            f"`{Path(kq.lenh[0]).name}` trả mã {kq.ma_thoat} nhưng **không có tệp "
            f"`{ra.name}`** trên đĩa. Không coi đây là {kq.chang} xong.")
        return
    kq.so_byte_ra = ra.stat().st_size
    if kq.so_byte_ra == 0:
        kq.vi_sao_khong_dat = (
            f"Tệp `{ra.name}` có trên đĩa nhưng **rỗng (0 byte)**. Chặng sau sẽ nhận đầu vào "
            "rỗng và cũng báo xong — lỗi chỉ hiện ra ở bo mạch. Không coi là xong.")
        return
    kq.tep_ra = str(ra.relative_to(goc)) if ra.is_relative_to(goc) else str(ra)
    kq.dat = True


def _thieu(ten: str, de_lam_gi: str) -> KetQuaHdl:
    kq = KetQuaHdl(chang=ten)
    kq.vi_sao_khong_dat = (
        f"Máy này chưa có `{ten}` để {de_lam_gi}. EIDE không tự cài — cài qua cổng G-TOOL "
        f"(`tool.install` với `isa=\"fpga-gowin\"`).")
    return kq


def _nguon_hdl(duong: Path) -> list[str]:
    """Tệp `.v`/`.sv` trong cây nguồn, bỏ thư mục ẩn và thư mục dựng lại được.

    Trả đường dẫn **tuyệt đối**. Mọi chặng chạy công cụ với `cwd` đặt ở gốc dự án, nên một
    đường dẫn tương đối so với thư mục hiện tại của tiến trình gọi sẽ không tìm thấy — và lỗi
    hiện ra là `Cannot find file containing module`, một câu trông như thiếu mô-đun chứ không
    như sai đường dẫn. Đã trúng một lần ngày 01/10/2026.
    """
    duong = duong.resolve()
    if duong.is_file():
        return [str(duong)]
    bo = {"build", "obj_dir", "node_modules"}
    return [str(p) for p in sorted(duong.rglob("*.v")) + sorted(duong.rglob("*.sv"))
            if not any(x.startswith(".") or x in bo for x in p.parts)]


# ------------------------------------------------------------------ bốn chặng

def lint(*, goc: Path, nguon: Path, dinh: str = "") -> KetQuaHdl:
    """Soát cú pháp và lỗi cấu trúc bằng Verilator, không tổng hợp, không chạy.

    Chặng này rẻ (vài giây) và bắt được phần lớn lỗi mà nếu để tới chặng tổng hợp thì phải chờ
    vài phút mới biết. `--lint-only` **không** sinh tệp nào, nên đây là chặng duy nhất trong
    tệp này kết luận theo mã thoát — và nói rõ điều đó ra.
    """
    goc = goc.resolve()
    kq = KetQuaHdl(chang="lint", cong_cu="verilator")
    v = _tim_lenh("verilator")
    if not v:
        return _thieu("verilator", "soát cú pháp Verilog")
    ds = _nguon_hdl(nguon)
    if not ds:
        kq.vi_sao_khong_dat = f"Không có tệp .v/.sv nào trong {nguon}."
        return kq
    lenh = [v, "--lint-only", "-Wall", "-Wno-fatal"]
    if dinh:
        lenh += ["--top-module", dinh]
    _chay(kq, lenh + ds, cwd=goc, han=HAN_GIAY["lint"], goc=goc)
    if not kq.vi_sao_khong_dat:
        kq.dat = kq.ma_thoat == 0 and not kq.loi
        if not kq.dat:
            kq.vi_sao_khong_dat = (
                f"Verilator tìm thấy {len(kq.loi)} lỗi." if kq.loi else
                f"Verilator trả mã {kq.ma_thoat}.")
    return kq


def mo_phong(*, goc: Path, nguon: Path, dinh: str = "", ra: Path | None = None,
             bo_may: str = "iverilog", dinh_nghia: dict[str, str] | None = None,
             lenh_mo_rong: dict[str, int] | None = None) -> KetQuaHdl:
    """Chạy testbench, và đọc `PASS`/`FAIL` mà **chính testbench in ra**.

    `bo_may`:
      - `iverilog` — nhanh để dựng, đủ cho testbench nhỏ. Mặc định.
      - `verilator` — dịch sang C++ rồi chạy; dựng lâu hơn nhưng chạy nhanh hơn nhiều bậc.
        Đề bài của anh Công bắt buộc dùng nó cho bài đo số chu kỳ, vì *"Icarus quá chậm với
        H0, N=32"*.

    Kết luận `dat` KHÔNG phải "chương trình chạy xong". Nó là: testbench in `PASS` và không in
    `FAIL`. Một testbench chạy xong mà không in gì thì **không đạt**, và lời từ chối nói rõ vì
    sao — đó là lỗi của testbench, không phải của thiết kế.
    """
    goc = goc.resolve()
    kq = KetQuaHdl(chang="mo_phong", cong_cu=bo_may)
    ds = _nguon_hdl(nguon)
    if not ds:
        kq.vi_sao_khong_dat = f"Không có tệp .v/.sv nào trong {nguon}."
        return kq
    build = ra or (goc / ".eide" / "hdl")
    build.mkdir(parents=True, exist_ok=True)
    dn = dinh_nghia or {}

    # Mã máy nạp vào lõi mềm có chạm tới chỗ mà `dinh_nghia` đang bật/tắt không. Cảnh báo
    # này ra TRƯỚC khi chạy, vì cái sai nó bắt được không hiện ra thành lỗi: lượt đo chạy
    # xong, in ra số, và số ấy bằng số của cấu hình kia. Xem `toolchain.kiem_khop_phan_cung`.
    if lenh_mo_rong:
        from .toolchain import kiem_khop_phan_cung
        for cau in kiem_khop_phan_cung(lenh_mo_rong, dn):
            kq.canh_bao.append({"ma": "ISA_KHONG_KHOP", "thong_diep": cau})

    if bo_may == "iverilog":
        iv = _tim_lenh("iverilog")
        vvp = _tim_lenh("vvp")
        if not iv or not vvp:
            return _thieu("iverilog", "mô phỏng testbench")
        anh = build / "sim.vvp"
        lenh = [iv, "-g2012", "-o", str(anh)]
        for k, val in dn.items():
            lenh += [f"-D{k}={val}" if val != "" else f"-D{k}"]
        if dinh:
            lenh += ["-s", dinh]
        _chay(kq, lenh + ds, cwd=goc, han=HAN_GIAY["sim"], goc=goc)
        if kq.vi_sao_khong_dat or not anh.exists():
            if not kq.vi_sao_khong_dat:
                kq.vi_sao_khong_dat = "iverilog không sinh ra tệp mô phỏng."
            return kq
        kq2 = KetQuaHdl(chang="mo_phong", cong_cu="vvp")
        _chay(kq2, [vvp, str(anh)], cwd=goc, han=HAN_GIAY["sim"], goc=goc)
        kq.nguyen_van = (kq.nguyen_van + "\n" + kq2.nguyen_van).strip()
        kq.ma_thoat = kq2.ma_thoat
        kq.giay += kq2.giay
    else:
        vl = _tim_lenh("verilator")
        if not vl:
            return _thieu("verilator", "mô phỏng để đo số chu kỳ")
        obj = build / "obj_dir"
        lenh = [vl, "--binary", "-j", "0", "-Wno-fatal", "--Mdir", str(obj),
                "-o", "sim"]
        for k, val in dn.items():
            lenh += [f"-D{k}={val}" if val != "" else f"-D{k}"]
        if dinh:
            lenh += ["--top-module", dinh]
        _chay(kq, lenh + ds, cwd=goc, han=HAN_GIAY["sim"], goc=goc)
        anh = obj / "sim"
        if kq.vi_sao_khong_dat or not anh.exists():
            if not kq.vi_sao_khong_dat:
                kq.vi_sao_khong_dat = (
                    "Verilator trả 0 nhưng không có tệp chạy được trong `obj_dir`.")
            return kq
        kq2 = KetQuaHdl(chang="mo_phong", cong_cu="sim")
        _chay(kq2, [str(anh)], cwd=goc, han=HAN_GIAY["sim"], goc=goc)
        kq.nguyen_van = (kq.nguyen_van + "\n" + kq2.nguyen_van).strip()
        kq.ma_thoat = kq2.ma_thoat
        kq.giay += kq2.giay

    tren = kq.nguyen_van.upper()
    co_pass, co_fail = "PASS" in tren, "FAIL" in tren
    kq.pass_fail = "FAIL" if co_fail else ("PASS" if co_pass else "")
    kq.dat = co_pass and not co_fail
    if not kq.dat:
        kq.vi_sao_khong_dat = (
            "Testbench in FAIL." if co_fail else
            "Testbench chạy xong nhưng **không in PASS cũng không in FAIL**. Theo đề bài, "
            "testbench phải tự kiểm rồi tự in kết quả — không in thì không có phép đo nào ở "
            "đây, và đó là lỗi của testbench chứ không phải của thiết kế.")
    return kq


def tong_hop(*, goc: Path, nguon: Path, dinh: str, bo_kit: str = "tangnano20k",
             ra: Path | None = None) -> KetQuaHdl:
    """Yosys `synth_gowin` → tệp JSON mạng cổng, kèm bảng đếm ô."""
    goc = goc.resolve()
    kq = KetQuaHdl(chang="tong_hop", cong_cu="yosys")
    ys = _tim_lenh("yosys")
    if not ys:
        return _thieu("yosys", "tổng hợp Verilog")
    tb = THIET_BI.get(bo_kit)
    if not tb:
        kq.vi_sao_khong_dat = (f"Chưa biết kit “{bo_kit}”. Đang biết: "
                               f"{', '.join(THIET_BI)}.")
        return kq
    ds = _nguon_hdl(nguon)
    if not ds:
        kq.vi_sao_khong_dat = f"Không có tệp .v/.sv nào trong {nguon}."
        return kq
    build = ra or (goc / ".eide" / "hdl")
    build.mkdir(parents=True, exist_ok=True)
    json_ra = build / f"{dinh}.json"
    _don_tep_ra(json_ra)
    kich = "; ".join([f"read_verilog -sv {' '.join(ds)}",
                      f"synth_gowin -top {dinh} -json {json_ra}"])
    _chay(kq, [ys, "-p", kich], cwd=goc, han=HAN_GIAY["synth"], goc=goc)
    _doi_tep_ra(kq, json_ra, goc)
    if kq.dat:
        kq.tai_nguyen = doc_tai_nguyen_yosys(kq.nguyen_van)
    return kq


def dat_di_day(*, goc: Path, json_mang: Path, cst: Path, bo_kit: str = "tangnano20k",
               tan_so_mhz: float = 27.0, ra: Path | None = None) -> KetQuaHdl:
    """nextpnr-himbaechel → tệp bố trí, kèm Fmax và mức dùng tài nguyên thật."""
    goc = goc.resolve()
    kq = KetQuaHdl(chang="dat_di_day", cong_cu="nextpnr-himbaechel")
    np = _tim_lenh("nextpnr-himbaechel")
    if not np:
        return _thieu("nextpnr-himbaechel", "đặt-đi dây cho chip Gowin")
    tb = THIET_BI.get(bo_kit)
    if not tb:
        kq.vi_sao_khong_dat = f"Chưa biết kit “{bo_kit}”."
        return kq
    if not json_mang.exists():
        kq.vi_sao_khong_dat = (
            f"Không có tệp mạng cổng `{json_mang.name}`. Chạy `hdl.synth` trước.")
        return kq
    if not cst.exists():
        kq.vi_sao_khong_dat = (
            f"Không có tệp ràng buộc chân `{cst.name}`. Thiếu nó thì nextpnr tự chọn chân, "
            "và bitstream dựng ra sẽ nối tín hiệu vào những chân không ai định — nạp lên bo "
            "thì không chạy, mà mọi chặng đều báo xong.")
        return kq
    build = ra or (goc / ".eide" / "hdl")
    build.mkdir(parents=True, exist_ok=True)
    pnr_ra = build / (json_mang.stem + "_pnr.json")
    _don_tep_ra(pnr_ra)
    _chay(kq, [np, "--json", str(json_mang), "--write", str(pnr_ra),
               "--device", tb["device"], "--vopt", f"cst={cst}",
               "--vopt", f"family={tb['family']}", "--freq", str(tan_so_mhz)],
          cwd=goc, han=HAN_GIAY["pnr"], goc=goc)
    # Đọc Fmax TRƯỚC khi chốt đạt/không đạt, và đọc cả khi lệnh trả mã lỗi.
    #
    # nextpnr trả mã khác 0 khi không đạt định thời. Nếu chỉ báo "trả mã 1" thì người đọc mất
    # đúng cái câu cần nghe — rằng thiết kế chạy không nổi tần số ấy — và sẽ đi tìm lỗi cú
    # pháp. Nguyên nhân và hậu quả là hai thứ khác nhau; phải nói nguyên nhân.
    fmax, dung, dong_ho = doc_ket_qua_pnr(kq.nguyen_van)
    kq.fmax_mhz = fmax
    kq.tai_nguyen = {"dung": dung, "dong_ho": dong_ho}
    khong_dat_dinh_thoi = (
        (fmax is not None and fmax < tan_so_mhz)
        or any(d.get("ket") == "FAIL" for d in dong_ho))
    if khong_dat_dinh_thoi:
        kq.dat = False
        do = f"Fmax {fmax:.2f} MHz < {tan_so_mhz:.2f} MHz cần chạy" if fmax is not None \
            else "có miền đồng hồ nextpnr đánh FAIL"
        kq.vi_sao_khong_dat = (
            f"Đặt-đi dây xong nhưng **không đạt định thời**: {do}. Bitstream dựng từ đây vẫn "
            "nạp được và vẫn chạy sai — sai theo kiểu lúc được lúc không, khó tìm nhất. Không "
            "coi là xong.")
        return kq

    _doi_tep_ra(kq, pnr_ra, goc)

    # Đạt mà KHÔNG đọc được Fmax thì phép canh định thời vừa rồi không đo gì cả. Nói ra, thay
    # vì để một ô xanh im lặng — đã trúng một lần ngày 01/10/2026: `fmax_mhz=None` mà vẫn đạt.
    if kq.dat and fmax is None:
        kq.canh_bao.append({
            "tep": "", "dong": 0, "cot": 0, "ma": "FMAX_KHONG_DOC_DUOC",
            "thong_diep": (
                "nextpnr không in dòng 'Max frequency' nào, nên KHÔNG kiểm được thiết kế có "
                f"chạy nổi {tan_so_mhz:.2f} MHz hay không. Chặng này đạt về mặt sinh ra tệp, "
                "nhưng về định thời thì chưa đo gì.")})
    return kq


def _doc_chip_tu_pnr(pnr_json: Path) -> str:
    """Tên cơ sở dữ liệu chip mà nextpnr đã ghi vào tệp bố trí (`packer.chipdb`).

    Trả "" nếu không đọc được — bên gọi sẽ lùi về giá trị trong bảng, và nếu giá trị ấy lệch
    thì `gowin_pack` tự báo, nên không có đường nào im lặng sinh ra bitstream sai chip.
    """
    import json

    try:
        d = json.loads(pnr_json.read_text("utf-8", errors="replace"))
        st = (((d.get("modules") or {}).get("top") or {}).get("settings") or {})
        return str(st.get("packer.chipdb") or "").strip()
    except (OSError, ValueError, AttributeError):
        return ""


def dong_goi(*, goc: Path, pnr_json: Path, bo_kit: str = "tangnano20k",
             ra: Path | None = None) -> KetQuaHdl:
    """gowin_pack → tệp `.fs` nạp được vào FPGA."""
    goc = goc.resolve()
    kq = KetQuaHdl(chang="dong_goi", cong_cu="gowin_pack")
    gp = _tim_lenh("gowin_pack")
    if not gp:
        return _thieu("gowin_pack", "đóng gói bitstream")
    tb = THIET_BI.get(bo_kit)
    if not tb:
        kq.vi_sao_khong_dat = f"Chưa biết kit “{bo_kit}”."
        return kq
    if not pnr_json.exists():
        kq.vi_sao_khong_dat = (
            f"Không có tệp bố trí `{pnr_json.name}`. Chạy `hdl.pnr` trước.")
        return kq
    build = ra or (goc / ".eide" / "hdl")
    build.mkdir(parents=True, exist_ok=True)
    fs = build / (pnr_json.stem.replace("_pnr", "") + ".fs")
    _don_tep_ra(fs)

    # Tên chip ĐỌC TỪ chính tệp bố trí, không lấy từ bảng hằng số.
    #
    # Lý do đo được ngày 01/10/2026: bảng ghi `GW2AR-18C` (đúng mã bán của chip trên kit), còn
    # nextpnr ghi vào tệp `GW2A-18C` (tên cơ sở dữ liệu của họ chip). Truyền giá trị trong bảng
    # thì `gowin_pack` dừng với câu *"The netlist was generated for chip GW2A-18C, but chip
    # GW2AR-18C is specified"*. Hai chuỗi ấy đều đúng, chỉ khác hệ quy chiếu.
    #
    # Đọc từ tệp làm chuyện lệch này **không xảy ra được**, thay vì làm nó xảy ra rồi mới sửa
    # bảng — mà sửa bảng thì lần sau đổi kit lại lệch tiếp.
    chip = _doc_chip_tu_pnr(pnr_json) or tb["pack"]
    kq.tai_nguyen = {"chip_doc_tu_tep_bo_tri": chip}
    _chay(kq, [gp, "-d", chip, "-o", str(fs), str(pnr_json)],
          cwd=goc, han=HAN_GIAY["pack"], goc=goc)
    _doi_tep_ra(kq, fs, goc)
    return kq
