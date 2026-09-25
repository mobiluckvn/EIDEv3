#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""So hai lần chạy của cùng một bộ kiểm — EIDE-SCH-44 §8 bước B/C, yêu cầu SCH-19.

    python tools/so_ket_qua.py <tệp A> <tệp B>
    python tools/so_ket_qua.py --hai-che-do tools/thu_g5.py

Dạng thứ hai chạy đúng một bộ kiểm **hai lần** — cờ tắt rồi cờ bật — rồi so. Đó là
bằng chứng mà §8 đòi trước khi được merge một tính năng có cờ:

    B. Cờ tắt  → kết quả phải giống hệt trước khi có tính năng
    C. Cờ bật, không gọi tính năng → vẫn phải giống hệt

Vì sao so bằng mã chứ không đọc bảng: hai bảng 35 dòng in cạnh nhau thì mắt bắt được
khác biệt lớn, nhưng cái nguy hiểm là **một ô lặng lẽ đổi từ đạt sang không đạt** —
đúng loại thứ mắt bỏ qua và là thứ SCH-19 tồn tại để chặn.

Mã thoát 0 = giống hệt; 1 = có khác biệt; 2 = không chạy được.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


def doc(p: pathlib.Path) -> tuple[dict, dict[tuple[str, str], bool]]:
    if not p.exists():
        print(f"{DO}Không có tệp kết quả: {p}{HET}")
        raise SystemExit(2)
    dong = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()]
    if not dong:
        print(f"{DO}{p} rỗng — bộ kiểm có chạy tới lúc in kết quả không?{HET}")
        raise SystemExit(2)
    dau = dong[0] if "bo" in dong[0] else {}
    ca = {(d["nhom"], d["ten"]): bool(d["dat"]) for d in dong if "ten" in d}
    return dau, ca


def so(pa: pathlib.Path, pb: pathlib.Path) -> int:
    da, a = doc(pa)
    db, b = doc(pb)

    print(f"\n{'═' * 92}\nSO HAI LẦN CHẠY\n{'═' * 92}")
    print(f"  A  {pa}  ·  {len(a)} ca  ·  cờ bật: {da.get('co') or 'không'}")
    print(f"  B  {pb}  ·  {len(b)} ca  ·  cờ bật: {db.get('co') or 'không'}")

    chi_a = [k for k in a if k not in b]
    chi_b = [k for k in b if k not in a]
    doi = [k for k in a if k in b and a[k] != b[k]]

    if not (chi_a or chi_b or doi):
        print(f"\n  {XANH}GIỐNG HỆT — {len(a)}/{len(a)} ca khớp{HET}")
        print("═" * 92)
        return 0

    print(f"\n{DO}KHÁC BIỆT:{HET}")
    for k in doi:
        cu = "đạt" if a[k] else "KHÔNG đạt"
        moi = "đạt" if b[k] else "KHÔNG đạt"
        mau = DO if a[k] and not b[k] else VANG
        print(f"  {mau}≠{HET} [{k[0]}] {k[1]}\n      A: {cu}  →  B: {moi}")
    for k in chi_a:
        print(f"  {DO}−{HET} chỉ có ở A: [{k[0]}] {k[1]}")
    for k in chi_b:
        print(f"  {DO}+{HET} chỉ có ở B: [{k[0]}] {k[1]}")

    xau = [k for k in doi if a[k] and not b[k]]
    if xau:
        print(f"\n  {DO}{len(xau)} ca đang đạt ở A thì KHÔNG đạt ở B — đây là hồi quy.{HET}")
    print("═" * 92)
    return 1


def hai_che_do(kich_ban: str) -> int:
    """Chạy một bộ kiểm hai lần: cờ tắt rồi cờ bật."""
    kb = pathlib.Path(kich_ban)
    if not kb.exists():
        kb = REPO / kich_ban
    if not kb.exists():
        print(f"{DO}Không có kịch bản: {kich_ban}{HET}")
        return 2

    py = str(REPO / ".venv/bin/python")
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="eide-so-"))
    ra: list[pathlib.Path] = []
    for nhan, co in (("tat", "0"), ("bat", "1")):
        out = tmp / f"{kb.stem}-{nhan}.jsonl"
        moi = {**os.environ, "EIDE_KETQUA": str(out), "EIDE_FEATURE_SCHEMATIC": co}
        print(f"\n{VANG}▸ Chạy {kb.name} với cờ schematic = {nhan.upper()}{HET}")
        r = subprocess.run([py, str(kb)], env=moi, cwd=REPO)
        if not out.exists():
            print(f"{DO}Lần chạy {nhan} không ghi kết quả (mã thoát {r.returncode}).{HET}")
            return 2
        ra.append(out)
    return so(ra[0], ra[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tep", nargs="*", help="hai tệp kết quả JSONL")
    ap.add_argument("--hai-che-do", metavar="KỊCH_BẢN",
                    help="chạy một bộ kiểm hai lần (cờ tắt / cờ bật) rồi so")
    a = ap.parse_args()

    if a.hai_che_do:
        return hai_che_do(a.hai_che_do)
    if len(a.tep) != 2:
        ap.error("cần đúng hai tệp, hoặc dùng --hai-che-do")
    return so(pathlib.Path(a.tep[0]), pathlib.Path(a.tep[1]))


if __name__ == "__main__":
    raise SystemExit(main())
