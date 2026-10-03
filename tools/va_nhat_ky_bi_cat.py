#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vá lại những câu trả lời bị cắt trong một nhật ký phiên, lấy bản đủ từ bản ghi của app.

    .venv/bin/python tools/va_nhat_ky_bi_cat.py du-lieu/ket-qua/fpga-sinhvien \
                                                du-lieu/fpga-sinhvien [--thu]

Vì sao tệp này tồn tại: gói `EIDE.app` dùng trong phiên FPGA ngày 03/10 được dựng ngày
30/09, trước DEV-325. Bản cũ cắt lời tác tử ở 3000 ký tự **không dán dấu gì** — nên 15
trong 30 câu trong `NHAT-KY.md` mất đuôi mà câu cuối vẫn trông như một câu kết thúc bình
thường. Tôi đã đọc nhật ký đó rồi kết luận sai rằng tác tử không trả lời câu hỏi về số
bitstream, trong khi nó trả lời đủ — ở đoạn đã mất.

Vá được vì `.eide/sessions/ses-*/transcript.jsonl` của app giữ **nguyên văn**. Nghĩa là
chỗ hỏng chỉ ở đường dẫn ra nhật ký, không phải ở dữ liệu gốc.

Nguyên tắc khi vá sở cứ: không im lặng sửa. Mỗi chỗ vá được dán một dòng ghi rõ đã lấy
lại từ đâu và dài bao nhiêu, để người đọc báo cáo sau này thấy được bản này đã qua tay.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


def lay_loi_model(du_an: pathlib.Path) -> list[str]:
    """Mọi lời tác tử trong mọi bản ghi phiên của dự án, theo thứ tự thời gian."""
    ra: list[str] = []
    for tep in sorted((du_an / ".eide/sessions").glob("ses-*/transcript.jsonl"),
                      key=lambda p: p.stat().st_mtime):
        for dong in tep.read_text("utf-8").splitlines():
            try:
                o = json.loads(dong)
            except Exception:
                continue
            if o.get("role") == "model" and (o.get("text") or "").strip():
                ra.append(o["text"])
    return ra


def go_dau_trich(khoi: str) -> str:
    """Bỏ `> ` ở đầu mỗi dòng để lấy lại nguyên văn."""
    return "\n".join(d[2:] if d.startswith("> ") else d[1:] if d == ">" else d
                     for d in khoi.split("\n"))


def dat_dau_trich(cau: str) -> str:
    return "> " + cau.replace("\n", "\n> ")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc_ket_qua")
    ap.add_argument("thu_muc_du_an")
    ap.add_argument("--thu", action="store_true", help="chỉ báo, không ghi")
    a = ap.parse_args(argv)

    md = pathlib.Path(a.thu_muc_ket_qua) / "NHAT-KY.md"
    goc = lay_loi_model(pathlib.Path(a.thu_muc_du_an))
    print(f"{VANG}Bản ghi phiên có {len(goc)} lời tác tử{HET}")

    s = md.read_text("utf-8")
    # Mỗi câu trả lời là khối trích dẫn ngay sau nhãn `**Tác tử:**`.
    mau = re.compile(r"(\*\*Tác tử:\*\*\n\n)((?:>[^\n]*\n)+)")
    va = []

    def thay(m: re.Match) -> str:
        cu = go_dau_trich(m.group(2).rstrip("\n"))
        # Khớp theo 300 ký tự đầu: đuôi là thứ đã mất nên không dùng để khớp được.
        mam = cu[:300]
        if len(mam) < 40:
            return m.group(0)
        ung = [t for t in goc if t.startswith(mam) and len(t) > len(cu) + 20]
        if not ung:
            return m.group(0)
        day = max(ung, key=len)
        va.append((len(cu), len(day)))
        ghi = (f"\n*(Bản trên đã được vá: gói EIDE.app ngày 30/09 cắt chuỗi giao diện ở "
               f"3000 ký tự mà không dán dấu, nên nhật ký chỉ giữ {len(cu)} ký tự. "
               f"Nguyên văn {len(day)} ký tự lấy lại từ "
               f"`{a.thu_muc_du_an}/.eide/sessions/*/transcript.jsonl`.)*\n")
        return m.group(1) + dat_dau_trich(day) + "\n" + ghi

    moi = mau.sub(thay, s)
    print(f"  vá được {len(va)} câu:")
    for cu, day in va:
        print(f"    {XAM}{cu:>5} → {day:>6} ký tự  (+{day - cu}){HET}")
    tong = sum(d - c for c, d in va)
    print(f"  {XANH}lấy lại tổng {tong} ký tự{HET}")

    if a.thu:
        print(f"{VANG}--thu: không ghi{HET}")
        return 0
    md.with_suffix(".md.truoc-khi-va").write_text(s, "utf-8")
    md.write_text(moi, "utf-8")
    print(f"  đã ghi {md}; bản trước ở {md.with_suffix('.md.truoc-khi-va').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
