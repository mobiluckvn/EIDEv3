#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Một phiên làm việc THẬT: dựng robot hai bánh tự cân bằng từ tài liệu bàn giao.

    EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/phien_robot.py [--tu-buoc N]

Khác mọi bộ trong `tools/thu_*.py`: đây **không phải** một bộ kiểm. Nó đóng vai người dùng
ngồi trước EIDE và làm một dự án có thật từ đầu tới cuối — gõ từng câu vào ô nhập, đợi tác tử
làm, rồi ghi lại mọi thứ: lời của tác tử, công cụ đã gọi, hiện vật sinh ra, và **ảnh chụp cửa
sổ EIDE** ở từng mốc.

Ảnh chụp chỉ lấy ĐÚNG khung cửa sổ EIDE (app tự khai qua `khung_cua_so`). Lần chụp toàn màn
hình đầu tiên đã lọt vào ảnh cửa sổ trò chuyện riêng và tệp `.env` kèm khoá API — một ảnh làm
sở cứ không được mang theo thứ nó không cần.

Kết quả đi vào `du-lieu/ket-qua/robot/`:

    NHAT-KY.md          nhật ký người đọc: từng bước, từng câu, từng kết luận
    buoc.jsonl          cùng nội dung ở dạng máy đọc
    anh/NN-<tên>.png    ảnh cửa sổ EIDE tại từng mốc
    doi-chieu.md        đối chiếu sơ đồ sinh ra với bảng 12/30/33 của tài liệu

Nguồn sự thật để đối chiếu: `docs/robot/MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx`.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import GiaoDien, PathsThu           # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

DU_AN = REPO / "du-lieu/robot-canbang"
RA = REPO / "du-lieu/ket-qua/robot"
TAI_LIEU = REPO / "docs/robot/MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx"


# ===================================================================== nhật ký
class NhatKy:
    """Ghi lại phiên làm việc cho người đọc VÀ cho máy đọc.

    Hai dạng vì hai người dùng khác nhau: `NHAT-KY.md` để đọc và làm sở cứ trong báo cáo;
    `buoc.jsonl` để so hai lần chạy bằng mã (cùng lý do `Bo` trong `thu_giao_dien.py` ghi ra
    jsonl — mắt người bỏ sót đúng loại khác biệt nguy hiểm nhất).
    """

    def __init__(self, ra: pathlib.Path):
        self.ra = ra
        self.ra.mkdir(parents=True, exist_ok=True)
        (self.ra / "anh").mkdir(exist_ok=True)
        self.md = self.ra / "NHAT-KY.md"
        self.js = self.ra / "buoc.jsonl"
        self.so = 0
        self.bat_dau = time.time()
        self.md.write_text(
            "# Phiên làm việc: robot hai bánh tự cân bằng\n\n"
            "Ghi tự động bởi `tools/phien_robot.py`. Mỗi mục là một bước có thật trong một "
            "phiên EIDE chạy trên máy, với ảnh chụp cửa sổ EIDE làm sở cứ.\n\n"
            f"- Tài liệu nguồn: `{TAI_LIEU.relative_to(REPO)}`\n"
            f"- Thư mục dự án: `{DU_AN.relative_to(REPO)}`\n"
            f"- Bắt đầu: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n---\n", "utf-8")
        self.js.write_text("", "utf-8")

    def buoc(self, ten: str, *, loai: str = "buoc") -> int:
        self.so += 1
        print(f"\n{VANG}▸ Bước {self.so}. {ten}{HET}")
        with self.md.open("a", encoding="utf-8") as f:
            f.write(f"\n## Bước {self.so}. {ten}\n\n")
        self._js({"su_kien": "buoc", "so": self.so, "ten": ten, "loai": loai})
        return self.so

    def noi(self, ai: str, cau: str) -> None:
        nhan = {"nguoi": "**Anh gõ:**", "tac_tu": "**Tác tử:**",
                "may": "**Máy:**"}.get(ai, f"**{ai}:**")
        with self.md.open("a", encoding="utf-8") as f:
            f.write(f"{nhan}\n\n> " + cau.replace("\n", "\n> ") + "\n\n")
        mau = {"nguoi": XANH, "tac_tu": XAM}.get(ai, "")
        print(f"{mau}  [{ai}] {cau[:260].replace(chr(10), ' ')}{HET}")
        self._js({"su_kien": "noi", "ai": ai, "cau": cau})

    def ghi(self, tieu_de: str, noi_dung: str, *, ma: bool = False) -> None:
        with self.md.open("a", encoding="utf-8") as f:
            f.write(f"**{tieu_de}**\n\n")
            f.write(f"```\n{noi_dung}\n```\n\n" if ma else f"{noi_dung}\n\n")
        print(f"{XAM}  · {tieu_de}: {noi_dung[:200].replace(chr(10), ' ')}{HET}")
        self._js({"su_kien": "ghi", "tieu_de": tieu_de, "noi_dung": noi_dung[:4000]})

    def ket(self, dat: bool, cau: str, bang_chung: str = "") -> bool:
        dau = "✅" if dat else "❌"
        with self.md.open("a", encoding="utf-8") as f:
            f.write(f"{dau} {cau}\n\n" + (f"```\n{bang_chung}\n```\n\n" if bang_chung else ""))
        print(f"  {XANH if dat else DO}{dau} {cau}{HET}"
              + (f"\n    {XAM}{bang_chung[:220]}{HET}" if bang_chung else ""))
        self._js({"su_kien": "ket_luan", "dat": bool(dat), "cau": cau,
                  "bang_chung": bang_chung[:2000]})
        return dat

    def anh(self, g: GiaoDien, ten: str) -> None:
        p = (self.ra / "anh" / f"{self.so:02d}-{ten}.png")
        got = g.chup_man_hinh(p, nhan=ten)
        if got:
            with self.md.open("a", encoding="utf-8") as f:
                f.write(f"![{ten}](anh/{p.name})\n\n")
            print(f"{XAM}  📷 anh/{p.name}{HET}")
            self._js({"su_kien": "anh", "tep": f"anh/{p.name}"})
        else:
            self.ghi("Ảnh chụp", "KHÔNG chụp được cửa sổ EIDE ở mốc này.")

    def _js(self, o: dict) -> None:
        o["t"] = round(time.time() - self.bat_dau, 1)
        with self.js.open("a", encoding="utf-8") as f:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")


# ===================================================================== ngữ cảnh
def ctx_cua_bo_do(du_an: pathlib.Path):
    """Ngữ cảnh công cụ cho TIẾN TRÌNH KIỂM — kho dùng chung với app, sổ cái riêng.

    Dùng để ĐỌC kết quả (kho, hiện vật, tệp) và để đối chiếu, không để làm thay tác tử.
    """
    from eide import Config
    from eide.config import Features
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        paths = PathsThu(du_an)
        store = Store(paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="robot-canbang")
        registry = build_registry(Features(schematic=True))
        ids = IdGen(paths.state_dir)
        ledger = Ledger(paths.ledger)
        history = History(paths=paths, store=store, ledger=ledger, ids=ids)
        run_id = "run-robot"
        tai_lieu: dict = {}
        pending_cards: list = []
        loi_nguoi_trong_phien: list = []
        awaiting_human = False
        agent = None
        def emit(self, c): pass
    return C()


def cong_cu_da_goi(du_an: pathlib.Path, tu: int = 0) -> list[dict]:
    """Đọc sổ cái của APP để biết tác tử đã gọi những công cụ nào (sở cứ, không phải lời khai)."""
    p = du_an / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    # Sổ cái ghi HAI dòng cho mỗi lời gọi: `tool_use` (tên + tham số) và `tool_result` (đạt
    # hay không, mã lỗi). Bản đầu tìm `kind == "tool"` — không có kind nào tên thế, nên mọi
    # bước đều báo "không gọi công cụ nào" trong khi tác tử vừa gọi 56 lần. Một phép đo luôn
    # trả về rỗng trông y hệt một hệ thống không làm gì.
    dung: dict[str, dict] = {}
    thu_tu: list[str] = []
    for l in p.read_text("utf-8", errors="replace").splitlines()[tu:]:
        try:
            o = json.loads(l)
        except ValueError:
            continue
        k, d = o.get("kind"), o.get("data") or {}
        if k == "tool_use" and d.get("tool"):
            cid = d.get("call_id") or f"{d['tool']}-{len(thu_tu)}"
            dung[cid] = {"tool": d["tool"], "args": d.get("args") or {},
                         "ok": None, "loi": None, "ms": None}
            thu_tu.append(cid)
        elif k == "tool_result":
            cid = d.get("call_id")
            m = dung.get(cid) if cid else next(
                (dung[c] for c in reversed(thu_tu)
                 if dung[c]["tool"] == d.get("tool") and dung[c]["ok"] is None), None)
            if m is not None:
                m.update(ok=d.get("ok"), loi=d.get("code"), ms=d.get("elapsed_ms"))
    return [dung[c] for c in thu_tu]


def so_dong_so_cai(du_an: pathlib.Path) -> int:
    p = du_an / ".eide" / "ledger.jsonl"
    return len(p.read_text("utf-8", errors="replace").splitlines()) if p.exists() else 0


def mo_app(du_an: pathlib.Path) -> GiaoDien:
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1.2)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(du_an)], check=True)
    g = GiaoDien(du_an)
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env={**os.environ, "EIDE_FEATURE_SCHEMATIC": "1"},
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(90)
    return g


def hoi(g: GiaoDien, nk: NhatKy, du_an: pathlib.Path, cau: str, *,
        giay: float = 600) -> tuple[str, list[dict]]:
    """Gõ một câu vào ô nhập và đợi tác tử làm xong. Trả (lời cuối, công cụ đã gọi)."""
    truoc = so_dong_so_cai(du_an)
    truoc_loi = (g.chup("truoc-khi-hoi") or {}).get("so_loi_tac_tu", 0)
    nk.noi("nguoi", cau)
    g.go(cau)
    a = g.doi_xong(giay)
    # Thẻ cổng: đóng vai người dùng bấm Duyệt. Ghi lại vào nhật ký — một lần duyệt cổng là
    # một quyết định của người, và sở cứ phải thấy được nó.
    for _ in range(4):
        the = [c for c in (a.get("the_dang_cho") or []) if c.get("gate_id")]
        if not the:
            break
        for c in the:
            nk.ghi("Thẻ cổng hiện ra — người dùng bấm Duyệt",
                   f"{c.get('gate')} · {c.get('tieu_de', '')[:120]} · "
                   f"{c.get('so_hau_qua', 0)} hậu quả")
            g.quyet_cong(c["gate_id"], True, note="đồng ý, đây là việc mình vừa nhờ")
        a = g.doi_xong(giay)
    # Tác tử có NÓI gì ở lượt này không, hay chỉ gọi công cụ rồi im? Không hỏi câu đó thì
    # `loi_tac_tu_cuoi` trả về lời của lượt TRƯỚC và nhật ký chép nhầm một cách rất hợp lý.
    loi = (a.get("loi_tac_tu_cuoi", "")
           if a.get("so_loi_tac_tu", 0) > truoc_loi
           else "(lượt này tác tử không nói gì — chỉ gọi công cụ)")
    cc = cong_cu_da_goi(du_an, truoc)
    nk.noi("tac_tu", loi or "(không nói gì)")
    if cc:
        nk.ghi("Công cụ tác tử đã gọi",
               "\n".join(
                   f"{i+1:2}. {c['tool']:20} "
                   + ("ok  " if c["ok"] else f"LỖI {c['loi']} ")
                   + json.dumps(c["args"], ensure_ascii=False)[:90]
                   for i, c in enumerate(cc)), ma=True)
    else:
        nk.ghi("Công cụ tác tử đã gọi", "— không gọi công cụ nào —", ma=True)
    return loi, cc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu-du-an", action="store_true",
                    help="không xoá dự án cũ, chạy tiếp trên nó")
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-3 hoặc 4")
    a = ap.parse_args()

    from eide.config import load_dotenv
    load_dotenv()

    if not a.giu_du_an:
        if DU_AN.exists():
            shutil.rmtree(DU_AN)
        if RA.exists():
            shutil.rmtree(RA)
    DU_AN.mkdir(parents=True, exist_ok=True)

    nk = NhatKy(RA)
    from kich_ban_robot import chay          # noqa: E402  (kịch bản ở tệp riêng)
    return chay(nk, DU_AN, chi_buoc=a.buoc)


if __name__ == "__main__":
    raise SystemExit(main())
