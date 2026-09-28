#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Review ba tính năng nền: tạo dự án · mở dự án · tắt app mở lại làm việc tiếp.

Không đọc mã rồi kết luận. Mỗi câu hỏi là một phép thử chạy qua app THẬT:

    B1  Trỏ app vào một thư mục RỖNG  → nó có tự dựng dự án không, dựng ra gì?
    B2  Hỏi tác tử một việc, để nó ghi một điều vào bộ nhớ dự án.
    B3  Chụp toàn bộ trạng thái trên đĩa.
    B4  GIẾT app (kill -9, như máy sập — không phải thoát tử tế).
    B5  Mở lại đúng thư mục ấy, hỏi "việc mình vừa nhờ là gì" → nó có nhớ không?
    B6  So trạng thái sau với trước: cái gì sống, cái gì mất.

Chạy:  .venv/bin/python <tệp này>
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import time

REPO = pathlib.Path("/Users/congvt/Documents/EIDE_v3")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

DU_AN = REPO / "du-lieu/thu-ben-vung"
RA = REPO / "du-lieu/ket-qua/ben-vung"


def anh_trang_thai(d: pathlib.Path) -> dict:
    """Chụp những gì nằm trên đĩa — đếm được, không mô tả."""
    e = d / ".eide"
    ra: dict = {"co_eide": e.exists()}
    if not e.exists():
        return ra
    ra["tep_trong_eide"] = sorted(p.name for p in e.iterdir())
    ra["so_dong_so_cai"] = (
        len([x for x in (e / "ledger.jsonl").read_text("utf-8").splitlines() if x.strip()])
        if (e / "ledger.jsonl").exists() else 0)
    ra["so_changeset"] = (
        len([x for x in (e / "changesets.jsonl").read_text("utf-8").splitlines() if x.strip()])
        if (e / "changesets.jsonl").exists() else 0)
    ra["phien"] = sorted(p.name for p in (e / "sessions").iterdir()) \
        if (e / "sessions").exists() else []
    ra["bo_dem"] = json.loads((e / "counters.json").read_text("utf-8")) \
        if (e / "counters.json").exists() else None
    ra["transcript"] = sorted(p.name for p in (e / "transcripts").iterdir()) \
        if (e / "transcripts").exists() else []
    if (e / "store.sqlite").exists():
        try:
            c = sqlite3.connect(f"file:{e / 'store.sqlite'}?mode=ro", uri=True)
            ra["bang_trong_kho"] = sorted(
                r[0] for r in c.execute(
                    "select name from sqlite_master where type='table'"))
            for b in ("artefacts", "artefact", "objects"):
                if b in ra["bang_trong_kho"]:
                    ra["so_hien_vat"] = c.execute(f"select count(*) from {b}").fetchone()[0]
                    break
            c.close()
        except Exception as ex:                                       # noqa: BLE001
            ra["kho_loi"] = str(ex)
    ra["co_eide_md"] = (d / "EIDE.md").exists()
    ra["eide_md_dong"] = len((d / "EIDE.md").read_text("utf-8").splitlines()) \
        if (d / "EIDE.md").exists() else 0
    return ra


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    from phien_robot import NhatKy, hoi, mo_app

    if DU_AN.exists():
        shutil.rmtree(DU_AN)
    if RA.exists():
        shutil.rmtree(RA)
    DU_AN.mkdir(parents=True)          # thư mục RỖNG — chưa có .eide, chưa có EIDE.md

    nk = NhatKy(RA, tieu_de="Review ba tính năng nền: tạo · mở · tắt-mở-làm-tiếp",
                nguon="thư mục rỗng, không chép sẵn gì",
                du_an=str(DU_AN.relative_to(REPO)))

    # ---------------------------------------------------------------- B1: trỏ vào rỗng
    nk.buoc("Trỏ app vào một thư mục RỖNG — nó tự dựng được dự án không?")
    truoc = anh_trang_thai(DU_AN)
    nk.ghi("Trước khi mở", json.dumps(truoc, ensure_ascii=False, indent=1), ma=True)
    g = mo_app(DU_AN)
    time.sleep(2)
    sau_mo = anh_trang_thai(DU_AN)
    nk.ghi("Sau khi app mở", json.dumps(sau_mo, ensure_ascii=False, indent=1), ma=True)
    nk.ket(sau_mo["co_eide"], "App tự dựng được dự án từ thư mục rỗng",
           f"tệp trong .eide: {sau_mo.get('tep_trong_eide')}")
    nk.ket(sau_mo.get("co_eide_md", False),
           "Có EIDE.md — bộ nhớ dài hạn của dự án, thứ tác tử đọc mỗi lượt",
           f"{sau_mo.get('eide_md_dong', 0)} dòng")
    nk.anh(g, "01-mo-thu-muc-rong")

    # ---------------------------------------------------------------- B2: giao việc
    nk.buoc("Giao một việc có DẤU VẾT — tác tử phải ghi một điều vào bộ nhớ dự án")
    loi, cc = hoi(g, nk, DU_AN,
                  "Mình bắt đầu một dự án mới trên bo STM32F469I-DISCO.\n\n"
                  "Việc đầu tiên rất nhỏ: ghi vào bộ nhớ dài hạn của dự án đúng một điều — "
                  "**thạch anh của bo này là 8 MHz, và mình đặt tên dự án là DEN-NHAY-8M**.\n\n"
                  "Ghi xong thì nói lại cho mình biết bạn ghi vào đâu.",
                  giay=900)
    nk.ghi("Chuỗi công cụ", " → ".join(c["tool"] for c in cc) or "—")
    truoc_tat = anh_trang_thai(DU_AN)
    nk.ghi("Trạng thái TRƯỚC khi tắt",
           json.dumps(truoc_tat, ensure_ascii=False, indent=1), ma=True)
    md = (DU_AN / "EIDE.md").read_text("utf-8") if (DU_AN / "EIDE.md").exists() else ""
    nk.ket("DEN-NHAY-8M" in md or "8 MHz" in md or "8MHz" in md,
           "Điều được giao đã nằm trên ĐĨA (EIDE.md), không chỉ trong hội thoại",
           f"EIDE.md {len(md.splitlines())} dòng · có 'DEN-NHAY-8M': "
           f"{'DEN-NHAY-8M' in md} · có '8 MHz': {'8 MHz' in md or '8MHz' in md}")
    nk.anh(g, "02-sau-khi-giao-viec")

    # ---------------------------------------------------------------- B3: giết app
    nk.buoc("GIẾT app bằng kill -9 — như máy sập, không phải thoát tử tế")
    subprocess.run(["pkill", "-9", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(3)
    sau_giet = anh_trang_thai(DU_AN)
    nk.ghi("Trạng thái NGAY SAU khi bị giết",
           json.dumps(sau_giet, ensure_ascii=False, indent=1), ma=True)
    # `store.sqlite-wal` / `-shm` là tệp phụ của SQLite: chúng BIẾN MẤT vì WAL đã được gộp
    # vào CSDL, tức là dữ liệu vào chỗ bền hơn chứ không mất. Bản đầu của phép kiểm này so cả
    # danh sách tệp nên báo đỏ vì đúng cái chuyển động ấy — một báo động sai, và một báo động
    # sai làm người đọc mất lòng tin vào những ô đỏ THẬT bên cạnh.
    def _loc(a: dict) -> dict:
        return {k: v for k, v in a.items() if k != "tep_trong_eide"} | {
            "tep_trong_eide": [x for x in (a.get("tep_trong_eide") or [])
                               if not x.startswith("store.sqlite-")]}

    t, s_ = _loc(truoc_tat), _loc(sau_giet)
    mat = {k: (t.get(k), s_.get(k)) for k in t if t.get(k) != s_.get(k)}
    nk.ket(not mat, "Không mất gì trên đĩa khi bị giết đột ngột",
           f"khác biệt: {json.dumps(mat, ensure_ascii=False)}" if mat else "giống hệt")

    # ---------------------------------------------------------------- B4: mở lại
    nk.buoc("Mở lại đúng dự án ấy — tác tử có nhớ việc lượt trước không?")
    g2 = mo_app(DU_AN)
    time.sleep(2)
    sau_mo_lai = anh_trang_thai(DU_AN)
    nk.ghi("Trạng thái sau khi mở lại",
           json.dumps(sau_mo_lai, ensure_ascii=False, indent=1), ma=True)
    nk.ket(sau_mo_lai.get("so_dong_so_cai", 0) >= truoc_tat.get("so_dong_so_cai", 0),
           "Sổ cái KHÔNG bị ghi đè khi mở lại (mở lại không phải bắt đầu lại)",
           f"trước tắt {truoc_tat.get('so_dong_so_cai')} dòng · "
           f"sau mở lại {sau_mo_lai.get('so_dong_so_cai')} dòng")
    nk.ket(sau_mo_lai.get("phien", []) != truoc_tat.get("phien", []),
           "Mở lại tạo PHIÊN MỚI (không ghi chồng lên phiên cũ)",
           f"trước: {truoc_tat.get('phien')} · sau: {sau_mo_lai.get('phien')}")

    loi2, cc2 = hoi(g2, nk, DU_AN,
                    "Mình vừa tắt app rồi mở lại.\n\n"
                    "Không tra lại tài liệu gì cả, trả lời mình bằng thứ bạn đang có: "
                    "**tên dự án này là gì, và thạch anh của bo bao nhiêu MHz?** "
                    "Nếu bạn không biết thì nói thẳng là không biết — đừng đoán.",
                    giay=900)
    nk.ghi("Chuỗi công cụ", " → ".join(c["tool"] for c in cc2) or "—")
    nho = ("DEN-NHAY-8M" in loi2) and ("8" in loi2)
    nk.ket(nho, "Tác tử NHỚ được việc của phiên trước sau khi tắt app",
           f"lời đáp có 'DEN-NHAY-8M': {'DEN-NHAY-8M' in loi2} · "
           f"gọi {len(cc2)} công cụ: {' → '.join(c['tool'] for c in cc2)}")
    nk.ket(not cc2 or any(c["tool"] in ("fs.read", "memory.note", "ledger.query",
                                        "store.get", "store.list") for c in cc2),
           "Nếu phải tra thì tra được — có đường tới trí nhớ cũ",
           " → ".join(c["tool"] for c in cc2) or "không cần tra, trả lời thẳng")
    nk.anh(g2, "03-sau-khi-mo-lai")

    nk.ghi("Kết thúc", f"nhật ký: {nk.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
