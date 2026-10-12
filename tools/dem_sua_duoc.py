#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đếm: bao nhiêu LOẠI hiện vật người sửa được thẳng trên giao diện.

    python tools/dem_sua_duoc.py            # bảng cho người đọc
    python tools/dem_sua_duoc.py --json     # cho máy so hai lần chạy

Chỉ số thứ nhất của EIDE-EDIT-47 §7. Cách đo: dựng THẬT các bề mặt từ kho mẫu trong
`du-lieu/`, rồi đếm khối nào mang `sua_duoc` (bất biến I8) và nó khai sửa được loại gì.

Vì sao dựng bề mặt thật chứ không grep mã: câu hỏi là *"người mở app lên thì sửa được
cái gì"*, và khối chỉ hiện ra khi kho CÓ hiện vật loại ấy. Một `sua_duoc` viết trong
`surfaces.py` mà khối của nó không bao giờ dựng được thì nó không tồn tại với người dùng.

Phân mẫu số cũng nói ra: **loại có trong kho** chứ không phải mọi loại EIDE biết. Đếm
theo danh sách loại trong mã thì mẫu số phình lên vì những loại chưa dự án nào sinh ra.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sqlite3
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


def _loai_trong_kho(db: pathlib.Path) -> collections.Counter:
    ra: collections.Counter = collections.Counter()
    try:
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for t, n in c.execute(
                "SELECT type, COUNT(*) FROM artefacts WHERE deleted=0 GROUP BY type"):
            ra[t] += n
        c.close()
    except sqlite3.Error:
        pass
    return ra


def _khoi_co_sua_duoc(du_an: pathlib.Path) -> tuple[list[dict], list[str]]:
    """Dựng mọi bề mặt của một dự án, trả (khối mang `sua_duoc`, lỗi nếu có)."""
    from eide import surfaces
    from eide.config import Config
    from eide.store import Store, inventory
    from eide.protocol.ledger import Ledger

    cfg = Config.for_project(du_an)
    store = Store(cfg.paths.store_db)
    ledger = Ledger(cfg.paths.ledger)
    inv = inventory.build(store, ledger=ledger, project_name=du_an.name)

    ra: list[dict] = []
    loi: list[str] = []
    cmds: list = []
    try:
        surfaces.emit_all(cmds.append, store=store, ledger=ledger,
                          eide_md=_eide_md(cfg), inv=inv, cfg=cfg)
    except Exception as e:                                        # noqa: BLE001
        loi.append(f"{du_an.name}: không dựng được bề mặt — {type(e).__name__}: {e}")
    for c in cmds:
        if getattr(c, "method", "") != "surface.set":
            continue
        m = c.params.get("model") or {}
        for b in m.get("blocks", []):
            if b.get("sua_duoc"):
                ra.append({"surface": m.get("surface"), "code": b.get("code"),
                           **b["sua_duoc"]})
    return ra, loi


def _eide_md(cfg):
    from eide.store import EideMd

    return EideMd.load(cfg.paths.eide_md, create_name=cfg.paths.project_root.name)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Đếm loại hiện vật sửa được qua giao diện")
    ap.add_argument("--du-lieu", default="du-lieu")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    goc = (REPO / a.du_lieu) if not pathlib.Path(a.du_lieu).is_absolute() else pathlib.Path(a.du_lieu)
    du_an = sorted(p.parent.parent for p in goc.glob("*/.eide/store.sqlite"))

    trong_kho: collections.Counter = collections.Counter()
    sua_duoc_loai: set[str] = set()
    theo_khoi: dict[str, set[str]] = {}
    loi: list[str] = []
    for d in du_an:
        trong_kho.update(_loai_trong_kho(d / ".eide" / "store.sqlite"))
        ds, l = _khoi_co_sua_duoc(d)
        loi += l
        for s in ds:
            sua_duoc_loai.add(s["loai"])
            theo_khoi.setdefault(f'{s["code"]} ({s["surface"]})', set()).add(s["loai"])

    # Loại khai sửa được mà kho mẫu KHÔNG có: vẫn kể, nhưng kể riêng — nó chưa được một
    # dự án thật nào kiểm chứng.
    co_that = sorted(t for t in sua_duoc_loai if t in trong_kho)
    chua_gap = sorted(t for t in sua_duoc_loai if t not in trong_kho)
    chua_sua = sorted(t for t in trong_kho if t not in sua_duoc_loai)

    kq = {
        "du_an": len(du_an),
        "loai_trong_kho": len(trong_kho),
        "loai_sua_duoc": len(co_that),
        "ty_le": f"{len(co_that)}/{len(trong_kho)}",
        "sua_duoc": co_that,
        "khai_ma_kho_chua_co": chua_gap,
        "chua_sua_duoc": chua_sua,
        "khoi": {k: sorted(v) for k, v in sorted(theo_khoi.items())},
        "loi": loi,
    }
    if a.json:
        print(json.dumps(kq, ensure_ascii=False, indent=1))
        return 0

    print(f"Kho mẫu: {len(du_an)} dự án · {len(trong_kho)} loại hiện vật có thật\n")
    print(f"  {XANH}SỬA ĐƯỢC {len(co_that)}/{len(trong_kho)}{HET}: " + ", ".join(co_that))
    if chua_gap:
        print(f"  {XAM}khai sửa được nhưng kho mẫu chưa có: {', '.join(chua_gap)}{HET}")
    print(f"\n  {VANG}CHƯA sửa được{HET} ({len(chua_sua)}): " + ", ".join(chua_sua))
    print("\n  Khối mang `sua_duoc`:")
    for k, v in kq["khoi"].items():
        print(f"    {k:28} → {', '.join(v)}")
    for x in loi:
        print(f"  {DO}✗ {x}{HET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
