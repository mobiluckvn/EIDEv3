#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm MEM-B qua giao diện thật — bộ nhớ dài hạn trên đĩa.

    python tools/thu_mem_b.py

Happy: transcript nằm trên đĩa sau mỗi lượt · tác tử ghi EIDE.md qua đúng cửa và dòng có
nguồn gốc · tra được quá khứ bằng ledger.query thay vì nhớ.

Unhappy (bảy đường): ghi thẳng EIDE.md · tự thêm vào mục "Đừng" · quên một dòng rồi hỏi
lại · EIDE.md vượt trần · sổ changeset bị sửa tay · lõi chết giữa `fs.write` · tra một
thứ chưa ai từng nói.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien        # noqa: E402

XANH, HET = "\033[92m", "\033[0m"
EX = {"summary": "thử", "why": "kiểm thử", "sources": [], "diff_prev": "—",
      "next": "—", "confidence": "NGUOI"}


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang(60)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    # ================================================================== HAPPY
    b.phan("A · TRANSCRIPT NẰM TRÊN ĐĨA SAU MỖI LƯỢT (MEM18)")
    g.go("Dự án của mình là bộ ghi dữ liệu nhiệt độ. Mình muốn dùng cơ chế MTP để "
         "truyền tệp về máy tính, không dùng USB MSC. Ghi nhớ giúp mình quyết định này.")
    a = g.doi_xong(300)

    ses = sorted((du_an / ".eide" / "sessions").glob("*/transcript.jsonl"))
    b.kiem("Có tệp transcript trên đĩa", bool(ses),
           "; ".join(str(p.parent.name) for p in ses) or "không có")
    ms = []
    if ses:
        ms = [json.loads(l) for l in ses[-1].read_text("utf-8").splitlines() if l.strip()]
        b.kiem("Transcript có cả lượt người và lượt mô hình",
               any(m.get("role") == "user" for m in ms)
               and any(m.get("role") == "model" for m in ms),
               f"{len(ms)} message: " + ", ".join(sorted({m.get('role', '?') for m in ms})))
        b.kiem("Không dòng nào hỏng",
               all(isinstance(m, dict) for m in ms), f"{len(ms)} dòng đọc được")

    b.phan("B · EIDE.md VÀO ĐÚNG CỬA, DÒNG CÓ NGUỒN GỐC (MEM03)")
    md = (du_an / "EIDE.md").read_text("utf-8")
    # §10 nói quyết định kỹ thuật đi vào `store.adr_create`, KHÔNG vào memory.note —
    # nên chấp nhận cả hai chỗ. Điều phải đúng là: nó rời khỏi hội thoại vào một hiện
    # vật có phiên bản, chứ không phải nó nằm ở tệp nào.
    from eide.store import Store
    kho = Store(du_an / ".eide" / "store.sqlite")
    adr = [a for a in kho.list("adr", limit=20)
           if "MTP" in str(a["canonical"]).upper()]
    b.kiem("Quyết định rời khỏi hội thoại vào một hiện vật có phiên bản",
           bool(adr) or "MTP" in md.upper(),
           (f"ADR {adr[0]['id']} v{adr[0]['version']}" if adr
            else ([l for l in md.splitlines() if "MTP" in l.upper()][:1] or "chưa ghi")))
    dong_tac_tu = [l for l in md.splitlines() if "[run-" in l]
    b.kiem("Dòng tác tử ghi có nguồn gốc [run-xx]", bool(dong_tac_tu),
           dong_tac_tu[0][:110] if dong_tac_tu else "không dòng nào có nguồn gốc")

    b.phan("C · TRA QUÁ KHỨ THAY VÌ NHỚ (MEM16)")
    g.go("Ban đầu mình nói muốn dùng cơ chế gì để truyền tệp, và vì sao? "
         "Tra lại giúp mình.")
    a = g.doi_xong(300)
    loi = a["loi_tac_tu_cuoi"]
    b.kiem("Trả lời đúng cơ chế đã chốt", "MTP" in loi.upper(), loi[:150])

    from eide.tools import build_registry
    reg = build_registry()
    ctx = _ctx(du_an)
    r = reg.run("ledger.query", {"chua": "MTP"}, ctx)
    b.kiem("ledger.query tra được sự kiện thật",
           r.ok and r.data["tong"] >= 1,
           f"{r.data.get('tong')} sự kiện khớp" if r.ok else str(r.error))

    # ================================================================== UNHAPPY
    b.phan("D · BẢY ĐƯỜNG HỎNG")
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    from eide.policy import PolicyEngine
    bus = register_standard_hooks(HookBus())
    pol = PolicyEngine()

    b.buoc("1. Ghi thẳng vào EIDE.md bằng fs.write")
    goi = {"tool": "fs.write",
           "args": {"path": "EIDE.md", "content": "# ghi đè", "explain": EX}}
    f = bus.pre_tool_use(goi, ctx).facts
    d = pol.decide(goi, f)
    b.kiem("Bị chặn, và chỉ đúng cửa phải đi",
           f.get("target.la_eide_md") is True and d.action == "deny"
           and "memory.note" in d.reason_vi,
           d.reason_vi[:130])

    b.buoc("2. Tác tử tự thêm vào mục “Đừng”")
    r = reg.run("memory.note",
                {"section": "Đừng", "line": "Đừng dùng MSC nữa", "explain": EX}, ctx)
    b.kiem("Từ chối — ranh giới đó do người đặt",
           not r.ok and "ranh giới do người đặt" in r.error.message_vi,
           r.error.message_vi[:130] if r.error else "lọt!")
    b.kiem("Chỉ đường đề xuất thay vì tự ghi",
           bool(r.error) and "ask_user" in r.error.hint_for_agent,
           r.error.hint_for_agent[:100] if r.error else "")

    b.buoc("3. Quên một dòng rồi hỏi lại")
    reg.run("memory.note",
            {"section": "Quy ước", "line": "Luôn build với -O3", "explain": EX}, ctx)
    r = reg.run("memory.forget",
                {"section": "Quy ước", "chua": "-O3", "explain": EX}, ctx)
    b.kiem("Xoá được dòng và ghi bia mộ",
           r.ok and r.data.get("tombstone"),
           f"tombstone {r.data.get('tombstone')}" if r.ok else str(r.error))
    md2 = (du_an / "EIDE.md").read_text("utf-8")
    b.kiem("Dòng đã biến khỏi EIDE.md", "-O3" not in md2,
           "còn sót" if "-O3" in md2 else "đã xoá")
    tomb = [e for e in ctx.ledger.read() if e.kind == "tombstone"]
    b.kiem("Bia mộ nằm trong sổ cái — không hồi sinh được",
           bool(tomb) and "-O3" in tomb[-1].data["noi_dung"],
           tomb[-1].data["noi_dung"][:90] if tomb else "không có bia mộ")

    b.buoc("4. EIDE.md vượt trần 3 000 token")
    from eide.store import EideMd
    md3 = EideMd.load(du_an / "EIDE.md")
    for i in range(40):
        md3.append_line("Quyết định", f"- ADR-{i:02d}: một quyết định dài dòng", boi="run-x")
    md3.save()
    md3 = EideMd.load(du_an / "EIDE.md")
    de = md3.de_xuat_luoc()
    b.kiem("Đề xuất lược, nói rõ lược gì và vì sao", bool(de) and all(d["vi_sao"] for d in de),
           "; ".join(f"{d['muc']}: {d['so_dong']} dòng" for d in de))
    b.kiem("KHÔNG tự xoá dòng nào (P5)",
           len([l for l in md3.get("Quyết định").splitlines() if l.strip()]) >= 40,
           f"{len(md3.get('Quyết định').splitlines())} dòng còn nguyên")

    b.buoc("5. Sổ changeset bị sửa tay")
    from eide.changeset import ChangesetLog
    p_cs = du_an / ".eide" / "changesets.jsonl"
    ok_truoc, vi_truoc = ChangesetLog(p_cs).verify()
    b.kiem("Trước khi sửa: chuỗi toàn vẹn", ok_truoc, vi_truoc)
    ds = p_cs.read_text("utf-8").splitlines()
    if ds:
        o = json.loads(ds[0])
        o["author"] = "agent:run-gia"
        ds[0] = json.dumps(o, ensure_ascii=False, separators=(",", ":"))
        p_cs.write_text("\n".join(ds) + "\n", "utf-8")
        ok_sau, vi_sau = ChangesetLog(p_cs).verify()
        b.kiem("Sau khi sửa: LỘ RA, nói đúng changeset nào",
               not ok_sau and o["id"] in vi_sau, vi_sau[:130])

    b.buoc("6. Lõi chết giữa fs.write")
    from eide.memory.transcript import Transcript, phuc_hoi
    tsp = du_an / ".eide" / "sessions" / "ses-gia" / "transcript.jsonl"
    ts = Transcript(tsp)
    ts.ghi({"role": "user", "text": "ghi tệp cấu hình giúp mình"})
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "fs.write", "args": {"path": "a.conf"}}]})
    bc = phuc_hoi(ts, "ses-gia")
    b.kiem("Nhận ra lời gọi không có kết quả",
           len(bc.goi_dang_do) == 1 and bc.can_hoi_nguoi,
           f"{bc.goi_dang_do}")
    b.kiem("Cấm chạy lại và bắt hỏi người",
           "ĐỪNG chạy lại" in bc.nhac_vi(), bc.nhac_vi()[-140:])

    b.buoc("7. Tra một thứ chưa ai từng nói")
    r = reg.run("ledger.query", {"chua": "cảm biến áp suất chưa ai nhắc"}, ctx)
    b.kiem("Nói thẳng không tìm thấy, cấm dựng lại câu chuyện",
           r.ok and r.data["tong"] == 0
           and "đừng dựng lại" in r.data["note_vi"].lower(),
           r.data.get("note_vi", "")[:120] if r.ok else "")

    return b.tong()


def _ctx(du_an):
    from eide import Config
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        store = Store(config.paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-mem-b")
        registry = build_registry()
        ids = IdGen(config.paths.state_dir)
        ledger = Ledger(config.paths.ledger)
        history = History(paths=config.paths, store=store, ledger=ledger, ids=ids)
        run_id = "run-thu"
        tai_lieu: dict = {}
        pending_cards: list = []
        loi_nguoi_trong_phien: list = []
        awaiting_human = False
        def emit(self, c): pass
    return C()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-mem-b").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "main.c").write_text("int main(void){return 0;}\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
