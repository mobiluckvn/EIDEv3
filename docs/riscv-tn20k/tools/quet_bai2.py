# -*- coding: utf-8 -*-
"""Quét đủ ma trận cấu hình của Bài 2: 96 ô.

    4 giá trị N (4, 8, 16, 32) × 2 kiểu (I8, I32) × 4 cách viết (V0–V3) × 3 cấu hình CPU

Một lượt mô phỏng cho **4 ô** — phần mềm chạy cả bốn cách viết rồi in bốn dòng `RESULT`. Nên
96 ô = **24 lượt**, không phải 96.

Hai chỗ dễ sai mà bộ quét này chặn sẵn:

**Cặp ISA và cấu hình CPU phải khớp.** `H0` dịch bằng `rv32i`, `H1`/`H2` bằng `rv32im`. Ghép
lệch thì hoặc bộ nhân ngồi không (mã máy không có lệnh nhân nào) hoặc CPU bẫy lệnh lạ — và
trường hợp thứ nhất cho **hai lượt ra số bằng nhau**, một con số trông đúng như kết luận. EIDE
cảnh báo chuyện này từ DEV-320; ở đây ghép đúng ngay từ đầu.

**Nhãn `hw` lấy từ dòng `CONFIG`, không lấy từ dòng `RESULT`.** Phần mềm không biết nó đang
chạy trên CPU nào — cấu hình CPU là thuộc tính của bản dựng phần cứng. Nên `main.c` in `hw=?`
và testbench in `CONFIG,hw=H0|H1|H2` suy từ chính macro của nó.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DU_AN = Path(__file__).resolve().parents[1]
REPO = DU_AN.parents[1]
sys.path.insert(0, str(REPO / "src"))

from eide.build import hdl, toolchain  # noqa: E402

N_DS = [4, 8, 16, 32]
KIEU_DS = ["I8", "I32"]
CAU_HINH = [
    ("H0", "rv32i", {"CFG_MUL": "0", "CFG_FAST_MUL": "0", "CFG_PCPI": "0"}),
    ("H1", "rv32im", {"CFG_MUL": "1", "CFG_FAST_MUL": "0", "CFG_PCPI": "0"}),
    ("H2", "rv32im", {"CFG_MUL": "1", "CFG_FAST_MUL": "1", "CFG_PCPI": "0"}),
]

_RESULT = re.compile(
    r"RESULT,n=(?P<n>\d+),dtype=(?P<dtype>\w+),ver=(?P<ver>\w+),hw=(?P<hw>[\w?]+),"
    r"cycles=(?P<cycles>\d+),macs=(?P<macs>\d+),cpm=(?P<cpm>[\d.]+),"
    r"chk=(?P<chk>0x[0-9A-Fa-f]+),ok=(?P<ok>\d)")
_CONFIG = re.compile(r"CONFIG,hw=(?P<hw>\w+)")


def sinh_du_lieu(n: int, kieu: str) -> str:
    """`gen_data.py` → `data_matrix.h`. Trả tổng kiểm đáp án, hoặc "" nếu trượt."""
    r = subprocess.run(
        [sys.executable, str(DU_AN / "tools/gen_data.py"),
         "--n", str(n), "--dtype", kieu, "--seed", "2026",
         "--out", str(DU_AN / "data_matrix.h")],
        capture_output=True, text=True, cwd=str(DU_AN), timeout=120)
    if r.returncode != 0:
        print(f"    gen_data trượt: {(r.stderr or r.stdout)[-300:]}")
        return ""
    m = re.search(r"CHECKSUM=(0x[0-9A-F]+)", r.stdout)
    return m.group(1) if m else ""


def mot_luot(n: int, kieu: str, ten: str, isa: str, dn: dict[str, str]) -> list[dict]:
    b = toolchain.bien_dich(goc=DU_AN, sketch=DU_AN / "bai2/sw", isa=isa)
    if not b.dat:
        print(f"    biên dịch trượt ({isa}): {b.vi_sao_khong_dat[:200]}")
        return []
    # Dọn `obj_dir`: Verilator dựng theo dấu thời gian, và một lượt chỉ đổi `-D` có thể bị
    # bỏ qua hoàn toàn với thông điệp `make: Nothing to be done`.
    obj = DU_AN / ".eide/hdl/obj_dir"
    if obj.exists():
        shutil.rmtree(obj)
    k = hdl.mo_phong(goc=DU_AN, nguon=DU_AN / "bai2/sim", dinh="tb_bai2",
                     bo_may="verilator", dinh_nghia=dn, lenh_mo_rong=b.lenh_mo_rong)
    nv = k.nguyen_van or ""
    for c in k.canh_bao or []:
        if c.get("ma") == "ISA_KHONG_KHOP":
            print(f"    ⚠ {c['thong_diep'][:160]}")

    mc = _CONFIG.search(nv)
    hw_that = mc.group("hw") if mc else ""
    if hw_that != ten:
        print(f"    ⚠ testbench báo CONFIG,hw={hw_that!r} mà ta đang chạy {ten} — "
              "nhãn và cấu hình lệch nhau, KHÔNG dùng lượt này")
        return []

    ra = []
    for m in _RESULT.finditer(nv):
        d = m.groupdict()
        # Nhãn `hw` lấy từ dòng CONFIG. Phần mềm in `?` vì nó không biết được.
        d["hw"] = hw_that
        d["flash"] = str(b.flash)
        ra.append(d)
    if not ra:
        print(f"    KHÔNG có dòng RESULT nào. dat={k.dat} {k.vi_sao_khong_dat[:200]}")
    return ra


def main() -> int:
    tat_ca: list[dict] = []
    dap_an: dict[tuple[int, str], str] = {}
    t0 = time.monotonic()
    tong_luot = len(N_DS) * len(KIEU_DS) * len(CAU_HINH)
    luot = 0

    for n in N_DS:
        for kieu in KIEU_DS:
            chk = sinh_du_lieu(n, kieu)
            if not chk:
                print(f"  N={n} {kieu}: không sinh được dữ liệu, bỏ qua cả ba cấu hình")
                luot += len(CAU_HINH)
                continue
            dap_an[(n, kieu)] = chk
            print(f"  N={n:<3} {kieu:<4} đáp án {chk}")
            for ten, isa, dn in CAU_HINH:
                luot += 1
                g0 = time.monotonic()
                o = mot_luot(n, kieu, ten, isa, dn)
                g = time.monotonic() - g0
                xau = [x for x in o if x["ok"] != "1" or x["chk"].upper() != chk.upper()]
                print(f"    [{luot:2}/{tong_luot}] {ten} {isa:<7} {g:6.1f}s  "
                      f"{len(o)} ô" + (f"  ⚠ {len(xau)} ô SAI" if xau else "")
                      + ("  " + " ".join(f"{x['ver']}={float(x['cpm']):.2f}" for x in o)
                         if o else ""))
                tat_ca.extend(o)

    ra = DU_AN / "results"
    ra.mkdir(exist_ok=True)
    f = ra / "all.csv"
    with f.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["n", "dtype", "ver", "hw", "cycles", "macs",
                                           "cpm", "chk", "ok", "flash"])
        w.writeheader()
        for d in sorted(tat_ca, key=lambda x: (int(x["n"]), x["dtype"], x["hw"], x["ver"])):
            w.writerow(d)

    print(f"\n  {len(tat_ca)}/96 ô · {time.monotonic() - t0:.0f} s · {f}")
    sai = [d for d in tat_ca if d["ok"] != "1"]
    print(f"  ô có ok=0: {len(sai)}" + (f" → {sai[:3]}" if sai else " (không có)"))
    return 0 if tat_ca else 1


if __name__ == "__main__":
    raise SystemExit(main())
