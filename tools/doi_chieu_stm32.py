#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đối chiếu firmware sinh ra với TÀI LIỆU mà chính tác tử đã nạp — bằng mã, không bằng mắt.

    .venv/bin/python tools/doi_chieu_stm32.py [--du-an du-lieu/stm32f469-disco]

Nguyên tắc: bộ này **không có sẵn đáp án**. Nó không biết LED1 nối chân nào; nó đọc tài liệu
trong kho của dự án rồi so với mã nguồn. Nếu tác tử nạp nhầm tài liệu thì bộ này cũng sai theo
— và đó là đúng, vì câu hỏi nó trả lời là *"firmware có khớp với nguồn mà dự án đang dựa vào
không"*, chứ không phải *"firmware có đúng với thứ người viết bộ đo nhớ được không"*.

Viết ra `docs/stm32f469/ket-qua/doi-chieu.md`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

RA = REPO / "docs/stm32f469/ket-qua/doi-chieu.md"

# Chân kiểu PG6 / PD4. Cũng bắt dạng tài liệu viết rời: `GPIOG` + `GPIO_PIN_6`.
_MAU_CHAN = re.compile(r"\bP([A-K])(\d{1,2})\b")
# `\b` sau [A-K] không khớp `GPIOG_BSRR` (`_` là ký tự từ); `(?![A-Z])` để
# `GPIOAEN` của RCC không bị đọc thành cổng A.
_MAU_CONG = re.compile(r"\bGPIO([A-K])(?![A-Z])")
_MAU_SO_CHAN = re.compile(r"\bGPIO_PIN_(\d{1,2})\b")


def _kho(du_an: pathlib.Path):
    from eide.store import Store

    return Store(du_an / ".eide" / "store.sqlite")


def _tai_lieu_van_ban(store) -> list[tuple[str, pathlib.Path, str]]:
    """(doc_id, đường dẫn, nội dung) của các tài liệu văn bản đã nạp."""
    ra = []
    for a in store.list("doc", limit=50):
        c = a.get("canonical") or {}
        p = pathlib.Path(str(c.get("path") or ""))
        if p.exists() and str(c.get("don_vi_trich_dan")) == "dòng":
            ra.append((a["id"], p, p.read_text("utf-8", errors="replace")))
    return ra


# Bit dùng cùng một cổng trên cùng một dòng: `1 << 6`, `1u<<6`, `(6 * 2)`, `BSRR = 0x40`.
_MAU_DICH = re.compile(r"\b1[uUlL]*\s*<<\s*\(?\s*(\d{1,2})")
_MAU_NHAN2 = re.compile(r"\(\s*(\d{1,2})\s*\*\s*2\s*\)")


def _cap_chan_trong(chu: str) -> tuple[set[str], bool]:
    """Các chân nêu trong một đoạn chữ, chuẩn hoá `PG6`. Trả `(tập chân, có đo được không)`.

    Ba cách viết phải bắt được, vì firmware và tài liệu viết khác nhau:

      `PG6`                                   người viết trong chú thích / bảng
      `GPIOG` + `GPIO_PIN_6` trên cùng dòng   header BSP của ST
      `GPIOG->BSRR = (1u << 6)`               firmware bare-metal — dạng THƯỜNG GẶP NHẤT

    Cờ thứ hai tồn tại vì một tập rỗng có hai nghĩa trái ngược: "firmware không dùng chân nào
    trong tài liệu" và "bộ đo không đọc nổi mã này". Trả về cùng một `set()` cho cả hai là
    biến cái thứ hai thành cái thứ nhất, và bảng đối chiếu sẽ ghi "không" cho mọi LED — một
    kết luận sai trông như đã kiểm.

    Ghép cổng với bit CHỈ trong cùng một dòng và chỉ khi dòng đó có đúng một cổng: ghép theo
    thứ tự trên cả tệp sẽ tạo ra những chân không tồn tại.
    """
    ra = {f"P{c}{n}" for c, n in _MAU_CHAN.findall(chu)}
    do_duoc = bool(ra)
    for dong in chu.splitlines():
        cong = _MAU_CONG.findall(dong)
        if len(cong) != 1:
            continue
        do_duoc = True                       # có nhắc tới một cổng GPIO cụ thể → đọc được
        bit = set(_MAU_SO_CHAN.findall(dong)) | set(_MAU_DICH.findall(dong)) \
            | set(_MAU_NHAN2.findall(dong))
        ra |= {f"P{cong[0]}{b}" for b in bit}
    return ra, do_duoc


def _chan_cua_led_trong_tai_lieu(chu: str) -> dict[str, str]:
    """`{"LED1": "PG6", ...}` đọc từ header BSP. Rỗng nếu tài liệu không viết theo lối đó."""
    cong = {m.group(1): m.group(2)
            for m in re.finditer(r"#define\s+(LED\d)_GPIO_PORT\s+.*?GPIO([A-K])", chu)}
    so = {m.group(1): m.group(2)
          for m in re.finditer(r"#define\s+(LED\d)_PIN\s+.*?GPIO_PIN_(\d{1,2})", chu)}
    return {k: f"P{cong[k]}{so[k]}" for k in cong if k in so}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--du-an", default="du-lieu/stm32f469-disco")
    a = ap.parse_args()
    du_an = (REPO / a.du_an).resolve()
    if not (du_an / ".eide" / "store.sqlite").exists():
        print(f"Chưa có kho ở {du_an}. Chạy tools/phien_stm32.py trước.")
        return 1

    store = _kho(du_an)
    tl = _tai_lieu_van_ban(store)
    fw = du_an / "firmware"
    ma = "\n".join(p.read_text("utf-8", errors="replace")
                   for p in sorted(fw.rglob("*"))
                   if p.is_file() and p.suffix in (".c", ".h", ".s", ".S", ".ld")) \
        if fw.is_dir() else ""

    L: list[str] = ["# Đối chiếu firmware ↔ tài liệu\n",
                    "Sinh tự động bởi `tools/doi_chieu_stm32.py`. Bộ này **không có sẵn đáp "
                    "án**: nó đọc tài liệu trong kho của dự án rồi so với mã nguồn.\n"]

    L.append(f"\n## Tài liệu văn bản đã nạp ({len(tl)})\n")
    for did, p, chu in tl:
        L.append(f"- `{did}` · `{p.name}` · {len(chu.splitlines())} dòng")
    if not tl:
        L.append("- *(chưa có tài liệu văn bản nào — phần đối chiếu chân sẽ bỏ trống)*")

    # --- chân LED
    L.append("\n## Chân LED\n")
    bang = {}
    for did, p, chu in tl:
        for led, chan in _chan_cua_led_trong_tai_lieu(chu).items():
            bang.setdefault(led, (chan, did, p.name))
    if not bang:
        L.append("*Tài liệu đã nạp không viết chân LED theo lối `LEDn_GPIO_PORT` + "
                 "`LEDn_PIN`, nên không đối chiếu được bằng mã.*")
    else:
        trong_ma, do_duoc = _cap_chan_trong(ma)
        L.append("| LED | Tài liệu nói | Nguồn | Có trong firmware? |")
        L.append("|---|---|---|---|")
        for led in sorted(bang):
            chan, did, ten = bang[led]
            ket = ("**có**" if chan in trong_ma else "không") if do_duoc \
                else "*không đọc được mã*"
            L.append(f"| {led} | `{chan}` | `{did}` ({ten}) | {ket} |")
        if not do_duoc:
            L.append("\n> Cột cuối để trống có chủ đích: trong `firmware/` không có mẫu nào "
                     "bộ đo đọc được (`PG6`, `GPIOG`+`GPIO_PIN_6`, hay `GPIOG->… 1 << 6`). "
                     "**Không đọc được** khác **không dùng** — không được ghi “không” cho cả "
                     "bốn LED rồi để người đọc hiểu là firmware sai chân.")
        else:
            thua = sorted(trong_ma - {v[0] for v in bang.values()})
            if thua:
                L.append("\nChân có trong firmware mà tài liệu (phần LED) không nhắc tới: "
                         + ", ".join(f"`{x}`" for x in thua)
                         + " — mỗi chân như thế phải có một Fact khác đứng sau.")

    # --- Fact trong kho
    fs = store.query_facts(limit=800)
    L.append(f"\n## Fact trong kho ({len(fs)})\n")
    if fs:
        L.append("| Chủ đề | Khoá | Giá trị | Tầng | Trích dẫn |")
        L.append("|---|---|---|---|---|")
        for f in fs[:60]:
            ng = f.get("source")
            if isinstance(ng, str):
                try:
                    ng = json.loads(ng)
                except ValueError:
                    ng = {"cite": ng}
            ng = ng or {}
            L.append(f"| `{f.get('subject')}` | {f.get('key')} | {f.get('value')} | "
                     f"{f.get('tier')} | {ng.get('doc_id', '?')} · "
                     f"{ng.get('cite', '**KHÔNG CÓ**')} |")
    else:
        L.append("*Chưa có Fact nào.*")

    # --- kết quả biên dịch và nạp
    for ma_hv, tieu in (("build:firmware", "Biên dịch"), ("target:flash", "Nạp vào bo"),
                        ("target:log", "Log từ bo")):
        hv = store.get(ma_hv)
        L.append(f"\n## {tieu}\n")
        if not hv:
            L.append("*Chưa có.*")
            continue
        c = hv.get("canonical") or {}
        for k, v in c.items():
            if k in ("nguyen_van", "chu", "lenh", "section", "loi", "canh_bao"):
                continue
            L.append(f"- **{k}**: `{v}`")

    RA.parent.mkdir(parents=True, exist_ok=True)
    RA.write_text("\n".join(L) + "\n", "utf-8")
    print(f"▸ Đã ghi {RA.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
