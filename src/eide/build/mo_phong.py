# -*- coding: utf-8 -*-
"""Mô phỏng vòng điều khiển bằng chính MÃ CỦA FIRMWARE.

Nguyên tắc duy nhất đáng nhớ ở đây: **mô phỏng phải chạy đúng đoạn mã sẽ nạp vào chip.** Một
mô phỏng chép lại thuật toán bằng Python rồi báo "robot đứng được" là một câu nói về đoạn
Python đó, không phải về firmware — và nó sẽ tiếp tục xanh sau khi ai đó sửa một dấu trừ trong
firmware thật.

Cách làm: firmware tách làm hai phần — phần LOGIC thuần (lọc góc, PID, quy đổi throttle) không
đụng thanh ghi, và phần THANH GHI (ngắt, timer, TWI). Mô phỏng biên dịch phần logic bằng trình
biên dịch của máy chủ cùng một tệp mô hình vật lý, chạy, rồi đọc kết quả ở dạng JSON.

Điều tệp này KHÔNG làm: nó không chấm điểm. Tiêu chí đạt/không do người gọi đưa vào, vì tiêu
chí là thứ đến từ tài liệu (ví dụ §13.4: "robot thẳng đứng → góc ≈ 0") chứ không phải từ đây.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class KetQuaMoPhong:
    dat: bool = False
    chay_duoc: bool = False
    lenh_bien_dich: list[str] = field(default_factory=list)
    loi_bien_dich: str = ""
    ma_thoat: int = 0
    ket_qua: dict[str, Any] = field(default_factory=dict)   # JSON do mô phỏng in ra
    nguyen_van: str = ""
    vi_sao_khong_dat: str = ""
    tep_nguon: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "chay_duoc": self.chay_duoc,
                "lenh_bien_dich": list(self.lenh_bien_dich),
                "loi_bien_dich": self.loi_bien_dich[-2000:],
                "ma_thoat": self.ma_thoat, "ket_qua": self.ket_qua,
                "tep_nguon": list(self.tep_nguon),
                "vi_sao_khong_dat": self.vi_sao_khong_dat,
                "nguyen_van": self.nguyen_van[-3000:]}


def _trinh_bien_dich() -> str:
    for t in ("cc", "clang", "gcc"):
        p = shutil.which(t)
        if p:
            return p
    return ""


def chay_mo_phong(*, goc: Path, nguon: list[Path], thu_muc_build: Path | None = None,
                  tham_so: list[str] | None = None,
                  giay_toi_da: float = 60.0) -> KetQuaMoPhong:
    """Biên dịch `nguon` bằng trình biên dịch máy chủ rồi chạy, đọc JSON ở đầu ra.

    Mô phỏng phải in ra **một dòng JSON** (dòng cuối cùng bắt đầu bằng `{`). Quy ước đó giữ
    cho việc đọc kết quả là đọc dữ liệu, không phải bóc chữ từ một bản báo cáo — một bản báo
    cáo đổi câu chữ thì phép đọc hỏng mà không ai biết.
    """
    kq = KetQuaMoPhong(tep_nguon=[str(p.relative_to(goc)) if p.is_relative_to(goc) else str(p)
                                  for p in nguon])
    cc = _trinh_bien_dich()
    if not cc:
        kq.vi_sao_khong_dat = ("Máy này không có trình biên dịch C (`cc`/`clang`/`gcc`) để "
                               "chạy mô phỏng.")
        return kq
    thieu = [str(p) for p in nguon if not p.exists()]
    if thieu or not nguon:
        kq.vi_sao_khong_dat = ("Không có tệp nguồn nào để mô phỏng."
                               if not nguon else f"Thiếu tệp: {', '.join(thieu)}")
        return kq

    build = thu_muc_build or (goc / ".eide" / "sim")
    build.mkdir(parents=True, exist_ok=True)
    chay = build / "mo_phong"
    kq.lenh_bien_dich = [cc, "-O2", "-std=c11", "-Wall", "-Wextra", "-DEIDE_SIM=1",
                         "-o", str(chay), *[str(p) for p in nguon], "-lm"]
    r = subprocess.run(kq.lenh_bien_dich, capture_output=True, text=True, cwd=str(goc),
                       env={**os.environ, "LC_ALL": "C"})
    if r.returncode != 0 or not chay.exists():
        kq.loi_bien_dich = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
        kq.vi_sao_khong_dat = "Không biên dịch được chương trình mô phỏng."
        return kq

    try:
        rr = subprocess.run([str(chay), *(tham_so or [])], capture_output=True, text=True,
                            cwd=str(goc), timeout=giay_toi_da)
    except subprocess.TimeoutExpired:
        kq.vi_sao_khong_dat = (f"Mô phỏng chạy quá {giay_toi_da:.0f} s mà chưa xong — "
                               "coi như không kết luận được.")
        return kq

    kq.chay_duoc = True
    kq.ma_thoat = rr.returncode
    kq.nguyen_van = ((rr.stdout or "") + "\n" + (rr.stderr or "")).strip()
    dong = [d.strip() for d in (rr.stdout or "").splitlines() if d.strip().startswith("{")]
    if not dong:
        kq.vi_sao_khong_dat = ("Mô phỏng chạy xong nhưng không in ra dòng JSON nào — không "
                               "đọc được kết quả, nên không kết luận gì.")
        return kq
    try:
        kq.ket_qua = json.loads(dong[-1])
    except ValueError as e:
        kq.vi_sao_khong_dat = f"Dòng kết quả không phải JSON hợp lệ: {e}"
        return kq

    # `dat` ở đây CHỈ nói "chương trình chạy trọn vẹn và in ra được kết quả". Đạt hay không
    # là việc của TIÊU CHÍ (`build/tieu_chi.xet_ket_qua`) — xem docstring tệp đó.
    kq.dat = rr.returncode == 0
    if not kq.dat:
        kq.vi_sao_khong_dat = (f"chương trình mô phỏng thoát với mã {rr.returncode}")
    return kq


# ==================================================== unit test trên máy chủ (test.run)
@dataclass(slots=True)
class KetQuaTest:
    chay_duoc: bool = False
    so_ca: int = 0
    so_dat: int = 0
    so_hong: int = 0
    ca: list[dict[str, Any]] = field(default_factory=list)
    do_phu: dict[str, Any] = field(default_factory=dict)
    lenh_bien_dich: list[str] = field(default_factory=list)
    loi_bien_dich: str = ""
    nguyen_van: str = ""
    vi_sao_khong_dat: str = ""
    tep_nguon: list[str] = field(default_factory=list)

    @property
    def dat(self) -> bool:
        return self.chay_duoc and self.so_ca > 0 and self.so_hong == 0

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "chay_duoc": self.chay_duoc, "so_ca": self.so_ca,
                "so_dat": self.so_dat, "so_hong": self.so_hong, "ca": self.ca[:60],
                "do_phu": dict(self.do_phu), "lenh_bien_dich": list(self.lenh_bien_dich),
                "loi_bien_dich": self.loi_bien_dich[-2000:],
                "tep_nguon": list(self.tep_nguon),
                "vi_sao_khong_dat": self.vi_sao_khong_dat,
                "nguyen_van": self.nguyen_van[-3000:]}


def chay_test(*, goc: Path, nguon: list[Path], thu_muc_build: Path | None = None,
              giay_toi_da: float = 120.0, do_phu: bool = True) -> KetQuaTest:
    """Chạy unit test của firmware trên MÁY CHỦ, với phần cứng được thay bằng mock.

    Quy ước đầu ra giống `chay_mo_phong`: chương trình test in **một dòng JSON**
    `{"ca": [{"ten": …, "dat": true/false, "vi": …}, …]}`. Không nhận "mọi test đã chạy" viết
    bằng lời — TC052 đòi *"báo cáo đạt/không đạt và độ phủ"*, và một bản báo cáo bằng lời thì
    không đếm được.

    Độ phủ đo bằng `-fprofile-instr-generate -fcoverage-mapping` nếu trình biên dịch có, và
    **nói rõ khi không đo được** thay vì im lặng bỏ cột đó.
    """
    kq = KetQuaTest(tep_nguon=[str(p.relative_to(goc)) if p.is_relative_to(goc) else str(p)
                               for p in nguon])
    cc = _trinh_bien_dich()
    if not cc:
        kq.vi_sao_khong_dat = "Máy này không có trình biên dịch C để chạy test."
        return kq
    thieu = [str(p) for p in nguon if not p.exists()]
    if not nguon or thieu:
        kq.vi_sao_khong_dat = ("Không có tệp test nào." if not nguon
                               else f"Thiếu tệp: {', '.join(thieu)}")
        return kq

    build = thu_muc_build or (goc / ".eide" / "test")
    build.mkdir(parents=True, exist_ok=True)
    chay = build / "chay_test"
    co_phu = do_phu and "clang" in Path(cc).name.lower() or do_phu and cc.endswith("cc")
    co = ["-fprofile-instr-generate", "-fcoverage-mapping"] if co_phu else []
    kq.lenh_bien_dich = [cc, "-O0", "-g", "-std=c11", "-Wall", "-Wextra", "-DEIDE_TEST=1",
                         *co, "-o", str(chay), *[str(p) for p in nguon], "-lm"]
    r = subprocess.run(kq.lenh_bien_dich, capture_output=True, text=True, cwd=str(goc),
                       env={**os.environ, "LC_ALL": "C"})
    if r.returncode != 0 or not chay.exists():
        # Thử lại không đo độ phủ: thiếu độ phủ là mất một cột, không biên dịch được là mất
        # cả phép thử.
        if co:
            kq.lenh_bien_dich = [x for x in kq.lenh_bien_dich if x not in co]
            r = subprocess.run(kq.lenh_bien_dich, capture_output=True, text=True,
                               cwd=str(goc), env={**os.environ, "LC_ALL": "C"})
            co_phu = False
        if r.returncode != 0 or not chay.exists():
            kq.loi_bien_dich = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
            kq.vi_sao_khong_dat = "Không biên dịch được chương trình test."
            return kq

    prof = build / "test.profraw"
    try:
        rr = subprocess.run([str(chay)], capture_output=True, text=True, cwd=str(goc),
                            timeout=giay_toi_da,
                            env={**os.environ, "LLVM_PROFILE_FILE": str(prof)})
    except subprocess.TimeoutExpired:
        kq.vi_sao_khong_dat = (f"Test chạy quá {giay_toi_da:.0f} s — nhiều khả năng có vòng "
                               "chờ không bao giờ thoát.")
        return kq

    kq.chay_duoc = True
    kq.nguyen_van = ((rr.stdout or "") + "\n" + (rr.stderr or "")).strip()
    dong = [d.strip() for d in (rr.stdout or "").splitlines() if d.strip().startswith("{")]
    if not dong:
        kq.vi_sao_khong_dat = ("Chương trình test không in ra dòng JSON nào — không đếm được "
                               "bao nhiêu ca đạt, nên không kết luận gì.\n" + KHUON_RA)
        return kq
    try:
        d = json.loads(dong[-1])
    except ValueError as e:
        kq.vi_sao_khong_dat = f"Dòng kết quả không phải JSON hợp lệ: {e}"
        return kq

    kq.ca = [dict(x) for x in (d.get("ca") or [])]
    kq.so_ca = len(kq.ca)
    kq.so_dat = sum(1 for x in kq.ca if x.get("dat") is True)
    kq.so_hong = kq.so_ca - kq.so_dat
    if kq.so_ca == 0:
        kq.vi_sao_khong_dat = KHUON_RA + _doan_khuon_sai(dong)
    elif kq.so_hong:
        kq.vi_sao_khong_dat = "; ".join(
            f"{x.get('ten')}: {x.get('vi', 'hỏng')}" for x in kq.ca if not x.get("dat"))[:600]

    kq.do_phu = _do_phu(build=build, prof=prof, chay=chay) if co_phu else {
        "do_duoc": False,
        "vi_sao": "Trình biên dịch trên máy không dựng được bản đo độ phủ; số ca đạt vẫn "
                  "đúng, chỉ là chưa biết test chạm tới bao nhiêu phần mã."}
    return kq


def _do_phu(*, build: Path, prof: Path, chay: Path) -> dict[str, Any]:
    """Độ phủ dòng, nếu `llvm-profdata`/`llvm-cov` có trên máy."""
    pd = shutil.which("llvm-profdata") or shutil.which("xcrun")
    cov = shutil.which("llvm-cov")
    if not prof.exists() or not cov:
        return {"do_duoc": False,
                "vi_sao": "Không có llvm-cov (hoặc chương trình test không sinh hồ sơ đo)."}
    data = build / "test.profdata"
    tron = ([pd, "merge", "-sparse", str(prof), "-o", str(data)] if "profdata" in str(pd)
            else [pd, "llvm-profdata", "merge", "-sparse", str(prof), "-o", str(data)])
    if subprocess.run(tron, capture_output=True, text=True).returncode != 0:
        return {"do_duoc": False, "vi_sao": "Không gộp được hồ sơ đo."}
    r = subprocess.run([cov, "report", str(chay), f"-instr-profile={data}"],
                       capture_output=True, text=True)
    for d in r.stdout.splitlines():
        if d.strip().lower().startswith("total"):
            phan = d.split()
            ty = [x for x in phan if x.endswith("%")]
            return {"do_duoc": True, "dong": ty[1] if len(ty) > 1 else (ty[0] if ty else ""),
                    "nguyen_van": d.strip()}
    return {"do_duoc": False, "vi_sao": "llvm-cov không in ra dòng tổng."}

# Khuôn đầu ra mà `chay_test` đếm được. Nó phải nằm ở một chỗ NÓI RA ĐƯỢC, không chỉ nằm
# trong đầu người viết bộ phân tích.
#
# Đo được ngày 28/09/2026: tác tử viết một tệp test in **mười dòng** JSON cho cùng một ca,
# mỗi dòng đoán một khuôn khác nhau (`{"assert":…}`, `{"type":"case",…}`, `{"ca":…}`, …).
# Đó không phải cẩu thả — đó là dấu vết của một công cụ chỉ nói ra khuôn của mình trong một
# thông báo lỗi chỉ hiện khi CHƯA CÓ tệp test nào. Có tệp rồi thì im lặng, và tác tử đoán.
#
# Và không nới bộ phân tích cho nhận cả mười khuôn ấy: mười dòng kia tự khai "đạt" mà sau
# lưng không có phép khẳng định nào. Nhận chúng là đếm mười ca đạt giả — đúng thứ N6 cấm.
# Chỗ cần sửa là NÓI RA, không phải nhận bừa.
KHUON_RA = (
    "Chương trình test phải in ĐÚNG MỘT dòng JSON, là dòng cuối cùng bắt đầu bằng `{`:\n"
    '  {"ca": [{"ten": "A2 cham giua nut", "dat": true, "vi": "CheckTouch(400,425) = 1"}, '
    '{"ten": "A3 cham ngoai nut", "dat": false, "vi": "mong 0, nhan duoc 1"}]}\n'
    "Một dòng, một mảng `ca`, mỗi ca có `ten` · `dat` (true/false) · `vi` (vì sao). "
    "Các dòng khác in thoải mái — chỉ dòng JSON CUỐI mới được đếm.")


def _doan_khuon_sai(dong: list[str]) -> str:
    """Khi có JSON mà không có `ca`: nói ra tệp test đang in khuôn gì, để khỏi đoán tiếp."""
    if not dong:
        return ""
    import json as _j
    khoa: set[str] = set()
    for d in dong[-12:]:
        try:
            o = _j.loads(d)
        except ValueError:
            continue
        if isinstance(o, dict):
            khoa |= set(o.keys())
    if not khoa:
        return ""
    return ("\nTệp test đang in các khoá: " + ", ".join(sorted(khoa)[:12])
            + f" — trên {len(dong)} dòng JSON. Không khoá nào trong số đó là `ca`, nên "
              "không đếm được ca nào, và im lặng coi là đạt thì sai.")
