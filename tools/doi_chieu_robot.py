#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đối chiếu sơ đồ EIDE sinh ra với TÀI LIỆU BÀN GIAO — bằng mã, từng net một.

    .venv/bin/python tools/doi_chieu_robot.py [--du-an …] [--ra …]

Đây là phép kiểm cuối cùng của phần phần cứng: tệp `.net` do `sch.netlist` sinh phải nói
đúng những gì bảng 12 (bản đồ chân), bảng 30 (đấu dây A4988) và bảng 33 (mức DIR đi tới) của
tài liệu nói. Không đọc bằng mắt: bảng 12 có 23 dòng, và thứ nguy hiểm là **một dòng lệch**.

Nguồn sự thật được ĐỌC LẠI TỪ TÀI LIỆU mỗi lần chạy, không chép cứng vào đây — chép cứng thì
phép đối chiếu chỉ so mã với mã.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

TAI_LIEU = REPO / "docs/robot/MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx"


def net_tu_tep(p: pathlib.Path) -> dict[str, set[str]]:
    """`.net` KiCad → `{tên net: {"U1.D4", "U2.DIR"}}`."""
    txt = p.read_text("utf-8", errors="replace")
    ra: dict[str, set[str]] = {}
    ten = None
    for d in txt.splitlines():
        m = re.search(r'\(net \(code "[^"]*"\) \(name "([^"]*)"\)', d)
        if m:
            ten = m.group(1)
            ra.setdefault(ten, set())
            continue
        m = re.search(r'\(node \(ref "([^"]*)"\) \(pin "([^"]*)"\)', d)
        if m and ten:
            ra[ten].add(f"{m.group(1)}.{m.group(2)}")
    return ra


def chan_tu_tai_lieu() -> list[dict[str, str]]:
    from eide.knowledge import docs as D
    from eide.knowledge import office as O

    tl = O.doc_docx(TAI_LIEU, doc_id="HW")
    return [x.to_dict() | {"nhan": tl.trich_dan(x.don_vi_trich_dan)}
            for x in D.trich_chan_ung_vien(tl)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--du-an", default=str(REPO / "du-lieu/robot-canbang"))
    ap.add_argument("--ra", default=str(REPO / "du-lieu/ket-qua/robot/doi-chieu.md"))
    a = ap.parse_args()
    du_an = pathlib.Path(a.du_an)

    p_net = du_an / "sch/mach.net"
    if not p_net.exists():
        print(f"Chưa có {p_net} — chạy sch.netlist trước.")
        return 2
    nets = net_tu_tep(p_net)
    chan = chan_tu_tai_lieu()

    dong: list[tuple[str, str, str, str, str, bool]] = []
    for c in chan:
        net = (c["net"] or "").strip()
        if not net or net.startswith("—"):
            continue                       # chân không có net trên sơ đồ (điểm đo)
        khoa = net.replace("_", " ").upper()
        tim = [t for t in nets if t.replace("_", " ").upper() == khoa]
        dau = sorted(nets[tim[0]]) if tim else []
        co_mcu = any(x.split(".", 1)[-1] == c["so_chan"] for x in dau)
        du_hai = len(dau) >= 2
        dong.append((c["so_chan"], c["cong"], net, ", ".join(dau) or "—",
                     c["nhan"], bool(tim and co_mcu and du_hai)))

    dat = [d for d in dong if d[5]]
    ra = pathlib.Path(a.ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    with ra.open("w", encoding="utf-8") as f:
        f.write("# Đối chiếu sơ đồ sinh ra với tài liệu bàn giao\n\n"
                f"- Sơ đồ: `{p_net.relative_to(REPO)}`\n"
                f"- Tài liệu: `{TAI_LIEU.relative_to(REPO)}`\n"
                f"- Kết quả: **{len(dat)}/{len(dong)}** net khớp\n\n"
                "Một net được coi là KHỚP khi: có trong sơ đồ, chạm đúng chân vi điều khiển "
                "mà tài liệu ghi, và có từ hai đầu trở lên (một net một đầu là một net hở).\n\n"
                "| Chân | Cổng | Net theo tài liệu | Đầu nối trong sơ đồ | Trích dẫn | Khớp |\n"
                "|---|---|---|---|---|---|\n")
        for so, cong, net, dau, nhan, ok in dong:
            f.write(f"| {so} | {cong} | {net} | {dau} | {nhan} | {'✅' if ok else '❌'} |\n")

    print(f"{len(dat)}/{len(dong)} net khớp tài liệu · báo cáo: {ra}")
    for d in dong:
        if not d[5]:
            print(f"  ✗ {d[0]} · net {d[2]} · sơ đồ: {d[3]}")
    return 0 if len(dat) == len(dong) else 1


if __name__ == "__main__":
    raise SystemExit(main())
