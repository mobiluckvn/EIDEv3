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

    kq.dat = bool(rr.returncode == 0 and kq.ket_qua.get("dat") is True)
    if not kq.dat:
        kq.vi_sao_khong_dat = str(kq.ket_qua.get("vi_sao")
                                  or f"mô phỏng kết luận chưa đạt (mã thoát {rr.returncode})")
    return kq
