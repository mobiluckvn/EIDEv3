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

APP = REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE"
NGUON_SWIFT = REPO / "ui/EIDEApp/Sources"


def doi_chieu_app_voi_nguon() -> None:
    """Chặn phiên nếu `EIDE.app` cũ hơn mã Swift. Gọi TRƯỚC khi mở app.

    Vì sao cần: `swift build` dựng `.build/debug/EIDE`, nhưng phiên này chạy
    `EIDE.app/Contents/MacOS/EIDE` — một **bản sao** mà chỉ `dong-goi.sh` cập nhật. Không
    ai nối hai thứ đó lại, nên sửa mã Swift, chạy `swift test` thấy xanh, rồi đo bằng app
    là đo bằng bản cũ.

    Chuyện đã xảy ra thật: phiên FPGA ngày 03/10 đo bằng gói dựng 30/09, trong khi mã
    nguồn đã qua bốn commit (DEV-325, DEV-328, DEV-329, d45c64d). Hậu quả không phải một
    lỗi kêu lên — mà là **15 trong 30 câu trả lời của tác tử bị cắt còn 3000 ký tự, im
    lặng**: bản cũ cắt không dán dấu, nên câu cuối trông như một câu kết thúc bình thường.
    Tôi đã đọc nhật ký ấy rồi kết luận sai rằng tác tử không trả lời một câu hỏi, trong
    khi nó trả lời đủ ở phần đã mất. Bản mới để trần 20 000, dán dấu cắt vào chính chuỗi,
    và ghi bản đủ ra tệp — cả ba thứ đó đã xanh trong `ThongBaoTests` từ 02/10 mà không
    tới được chỗ đo.

    Nên phép kiểm ở đây không hỏi "mã có đúng không" — nó hỏi **"thứ tôi sắp đo có phải
    là mã tôi vừa sửa không"**.
    """
    # `relative_to` chỉ để in cho gọn, nên không được là chỗ hỏng: nó NỔ bằng ValueError
    # với đường dẫn ngoài repo, và một chốt tự nổ thì người ta tắt chốt chứ không sửa gói.
    def goi(p: pathlib.Path) -> str:
        try:
            return str(p.relative_to(REPO))
        except ValueError:
            return str(p)

    if not APP.exists():
        raise SystemExit(f"{DO}Chưa có {goi(APP)} — chạy "
                         f"ui/EIDEApp/dong-goi.sh trước.{HET}")
    moc_app = APP.stat().st_mtime
    tre = [p for p in NGUON_SWIFT.rglob("*.swift") if p.stat().st_mtime > moc_app]
    if tre:
        ds = "\n".join(f"    {goi(p)}  "
                       f"({time.strftime('%d/%m %H:%M', time.localtime(p.stat().st_mtime))})"
                       for p in sorted(tre)[:8])
        raise SystemExit(
            f"{DO}GÓI APP CŨ HƠN MÃ NGUỒN — phiên dừng, vì đo bằng bản này là đo bằng "
            f"mã đã bị thay.{HET}\n"
            f"  EIDE.app dựng lúc {time.strftime('%d/%m %H:%M', time.localtime(moc_app))}, "
            f"còn {len(tre)} tệp Swift mới hơn:\n{ds}\n"
            f"  Chạy:  ui/EIDEApp/dong-goi.sh")


# ===================================================================== nhật ký
class NhatKy:
    """Ghi lại phiên làm việc cho người đọc VÀ cho máy đọc.

    Hai dạng vì hai người dùng khác nhau: `NHAT-KY.md` để đọc và làm sở cứ trong báo cáo;
    `buoc.jsonl` để so hai lần chạy bằng mã (cùng lý do `Bo` trong `thu_giao_dien.py` ghi ra
    jsonl — mắt người bỏ sót đúng loại khác biệt nguy hiểm nhất).
    """

    def __init__(self, ra: pathlib.Path, *, tieu_de: str = "", nguon: str = "",
                 du_an: str = ""):
        # Ba tham số này để một phiên KHÁC dùng lại nguyên lớp nhật ký. Bản đầu viết thẳng
        # tên dự án robot vào phần mở đầu, nên phiên STM32 sẽ ghi ra một tệp nói rằng nó
        # đang làm robot — một sở cứ tự mâu thuẫn với chính nó.
        self.tieu_de = tieu_de or "robot hai bánh tự cân bằng"
        self.nguon = nguon or str(TAI_LIEU.relative_to(REPO))
        self.du_an = du_an or str(DU_AN.relative_to(REPO))
        self.ra = ra
        self.ra.mkdir(parents=True, exist_ok=True)
        (self.ra / "anh").mkdir(exist_ok=True)
        self.md = self.ra / "NHAT-KY.md"
        self.js = self.ra / "buoc.jsonl"
        self.bat_dau = time.time()
        # NỐI vào nhật ký cũ, không ghi đè. Bản đầu ghi đè mỗi lần chạy, nên chạy tiếp một
        # bước là xoá sạch sở cứ của mọi bước trước — đúng thứ mà nhật ký này tồn tại để giữ.
        # Số bước tiếp tục từ số cao nhất đã có, để ảnh chụp không đè lên nhau.
        cu = self.md.read_text("utf-8") if self.md.exists() else ""
        self.so = max([int(x.name.split("-", 1)[0])
                       for x in (self.ra / "anh").glob("*.png")
                       if x.name.split("-", 1)[0].isdigit()] or [0])
        if not cu:
            self.md.write_text(
                f"# Phiên làm việc: {self.tieu_de}\n\n"
                "Ghi tự động. Mỗi mục là một bước có thật trong một phiên EIDE chạy trên "
                "máy, với ảnh chụp cửa sổ EIDE làm sở cứ.\n\n"
                f"- Nguồn: `{self.nguon}`\n"
                f"- Thư mục dự án: `{self.du_an}`\n"
                f"- Bắt đầu: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n---\n", "utf-8")
        else:
            with self.md.open("a", encoding="utf-8") as f:
                f.write(f"\n\n---\n\n*(chạy tiếp lúc {time.strftime('%d/%m/%Y %H:%M:%S')})*"
                        "\n")
        if not self.js.exists():
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
    doi_chieu_app_voi_nguon()
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


def _loi_day_tu_ban_ghi(du_an: pathlib.Path, dau: str) -> str:
    """Tìm trong bản ghi phiên của app lời tác tử BẮT ĐẦU bằng `dau`, trả nguyên văn.

    Khớp theo đoạn đầu chứ không theo thứ tự: một lượt có thể sinh nhiều lời, và lời cuối
    trong tệp chưa chắc là lời giao diện vừa đưa ra.
    """
    mam = dau.split("⟨CẮT")[0][:300]
    if len(mam) < 40:
        return ""
    ds = sorted((du_an / ".eide/sessions").glob("ses-*/transcript.jsonl"),
                key=lambda p: p.stat().st_mtime, reverse=True)
    for tep in ds[:3]:
        for dong in reversed(tep.read_text("utf-8").splitlines()):
            try:
                o = json.loads(dong)
            except Exception:
                continue
            t = o.get("text") or ""
            if o.get("role") == "model" and t.startswith(mam) and len(t) > len(dau):
                return t
    return ""


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
    # Thẻ ĐÃ xử lý thì không ghi lại và không duyệt lại. Bản trước duyệt theo danh sách
    # `the_dang_cho` của mỗi vòng thăm dò, mà một thẻ vừa duyệt vẫn còn trong ảnh chụp kế
    # tiếp — nên nhật ký chép 18 thẻ cho một lượt chỉ có 2 thẻ thật, và sở cứ nói sai về
    # chính thứ nó đang làm chứng.
    da_xu_ly: set[str] = set()
    rong_lien_tiep = 0
    for _ in range(16):
        the = [c for c in (a.get("the_dang_cho") or [])
               if c.get("gate_id") and c["gate_id"] not in da_xu_ly]
        if not the:
            # Dừng sau HAI vòng liên tiếp không thấy thẻ mới, không phải sau một vòng: duyệt
            # một thẻ làm tác tử chạy tiếp và nó có thể dựng thẻ kế ngay sau đó. Dừng sớm thì
            # lượt bị bỏ dở ở một thẻ đang mở, và nhật ký chép cái thẻ ấy như thể đó là câu
            # trả lời của tác tử.
            rong_lien_tiep += 1
            if rong_lien_tiep >= 2:
                break
            a = g.doi_xong(giay)
            continue
        rong_lien_tiep = 0
        for c in the:
            da_xu_ly.add(c["gate_id"])
            nk.ghi("Thẻ cổng hiện ra — người dùng bấm Duyệt",
                   f"{c.get('gate')} · {c.get('tieu_de', '')[:120]} · "
                   f"{c.get('so_hau_qua', 0)} hậu quả")
            g.quyet_cong(c["gate_id"], True, note="đồng ý, đây là việc mình vừa nhờ")
        a = g.doi_xong(giay)
    con_mo = [c.get("gate_id") for c in (a.get("the_dang_cho") or [])
              if c.get("gate_id") and c["gate_id"] not in da_xu_ly]
    if con_mo:
        nk.ghi("BỎ DỞ — còn thẻ cổng chưa trả lời",
               f"{len(con_mo)} thẻ: {', '.join(map(str, con_mo))}. Lượt này dừng giữa chừng, "
               "nên kết quả dưới đây CHƯA phải là việc tác tử làm xong.")
    # Tác tử có NÓI gì ở lượt này không, hay chỉ gọi công cụ rồi im? Không hỏi câu đó thì
    # `loi_tac_tu_cuoi` trả về lời của lượt TRƯỚC và nhật ký chép nhầm một cách rất hợp lý.
    loi = (a.get("loi_tac_tu_cuoi", "")
           if a.get("so_loi_tac_tu", 0) > truoc_loi
           else "(lượt này tác tử không nói gì — chỉ gọi công cụ)")
    # Chuỗi nhận được có ĐỦ không? App khai riêng độ dài thật ở `loi_tac_tu_do_dai`, nên
    # so hai con số là đủ để biết. Thiếu mà không ai so thì nhật ký mất đoạn cuối một cách
    # hoàn toàn êm — xem `doi_chieu_app_voi_nguon` ở đầu tệp.
    #
    # Lấy lại bản đủ từ `transcript.jsonl` của app chứ không chỉ kêu lên: sở cứ phải đủ
    # ngay lúc ghi. Chép lại được vì bản ghi phiên giữ nguyên văn — chính nhờ nó mà 15 câu
    # bị cắt hôm 03/10 vá lại được, chứ nếu chỉ có nhật ký thì mất là mất.
    dai_that = int(a.get("loi_tac_tu_do_dai") or 0)
    if dai_that > len(loi) > 0:
        day = _loi_day_tu_ban_ghi(du_an, loi)
        if day:
            nk.ghi("Chuỗi giao diện bị cắt — đã lấy lại bản đủ từ bản ghi phiên",
                   f"app đưa ra {len(loi)} ký tự, lời thật dài {dai_that} ký tự; "
                   f"bản lấy lại dài {len(day)} ký tự")
            loi = day
        else:
            nk.ghi("CHUỖI BỊ CẮT VÀ KHÔNG LẤY LẠI ĐƯỢC",
                   f"app đưa ra {len(loi)} ký tự nhưng lời thật dài {dai_that} ký tự. "
                   "Phần dưới đây THIẾU ĐUÔI — đừng kết luận tác tử không nói điều gì chỉ "
                   "vì không thấy nó ở đây.")
    # Đợi kết quả được ghi xuống sổ cái trước khi chép vào nhật ký.
    #
    # Một lời gọi bị cổng chặn sẽ CHẠY Ở LƯỢT SAU (`run-113` mở cổng, `run-121` chạy), và nếu
    # đọc sổ cái ngay lúc lượt vừa nhàn rỗi thì dòng `tool_result` chưa kịp có. Bản trước chép
    # thẳng thành `LỖI None` — nhật ký nói sai về chính thứ nó đang làm chứng, ở đây là nói
    # một lời gọi THÀNH CÔNG (22 s, `ok: true`) là thất bại.
    cc = cong_cu_da_goi(du_an, truoc)
    for _ in range(20):
        if not any(c["ok"] is None for c in cc):
            break
        time.sleep(1.0)
        cc = cong_cu_da_goi(du_an, truoc)

    nk.noi("tac_tu", loi or "(không nói gì)")
    if cc:
        nk.ghi("Công cụ tác tử đã gọi",
               "\n".join(
                   f"{i+1:2}. {c['tool']:20} "
                   + ("ok  " if c["ok"] else
                      "CHƯA RÕ (kết quả chưa ghi xong) " if c["ok"] is None else
                      f"LỖI {c['loi']} ")
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
