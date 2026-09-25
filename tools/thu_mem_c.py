#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm MEM-C qua giao diện thật — nén có kiểm chứng, ghim, resume, bộ nhớ người dùng.

    python tools/thu_mem_c.py

Happy: dựng một phiên có quyết định thật → nén C2 bằng mô hình thật → kiểm ngược đạt →
tóm tắt giữ đủ quyết định → hỏi lại quyết định đó vẫn trả lời đúng.

Unhappy (bảy đường): kiểm sai thì huỷ · mô hình hỏng giữa lúc tóm tắt · tóm tắt không
theo lược đồ · hồi sinh điều đã quên · ghim bị nén · huỷ nén khi chưa nén · M3 nhớ bí mật.
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


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang(60)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    # ================================================================== HAPPY
    b.phan("A · DỰNG MỘT PHIÊN CÓ QUYẾT ĐỊNH THẬT")
    g.go("Dự án: bộ ghi nhiệt độ dùng ATmega328P. Mình chốt hai điều: một là truyền "
         "tệp bằng MTP chứ không dùng USB MSC; hai là tốc độ ghi thẻ SD phải đạt tối "
         "thiểu 2 MB/s. Ghi lại cả hai giúp mình.")
    a = g.doi_xong(300)

    g.go("Thêm nữa: mình muốn thiết bị chạy được ở 60 °C. Và nhớ giúp là mình thích "
         "câu trả lời ngắn gọn, từ nay lần nào cũng ngắn thôi nhé.")
    a = g.doi_xong(300)

    # Đọc kho SAU hai lượt: tác tử có quyền tra sổ trước rồi mới ghi ở lượt sau, và
    # đó là hành vi đúng — ép nó ghi ngay trong lượt đầu là ép sai.
    from eide.store import Store
    kho = Store(du_an / ".eide" / "store.sqlite")
    reqs = kho.list("req", limit=20)
    adrs = kho.list("adr", limit=20)
    # Đo thứ ĐÁNG đo: quyết định rời khỏi hội thoại vào một hiện vật CÓ PHIÊN BẢN.
    # Ép nó phải là ADR chứ không được là REQ là ép một lựa chọn trình bày — cả hai đều
    # hoàn tác được, đều có explain, đều tra lại được.
    co_mtp = any("MTP" in str(a["canonical"]).upper() for a in reqs + adrs)
    b.kiem("Quyết định rời khỏi hội thoại vào hiện vật có phiên bản",
           bool(reqs) and co_mtp,
           f"{len(reqs)} REQ · {len(adrs)} ADR · nhắc MTP: {co_mtp}")

    b.phan("B · NÉN C2 BẰNG MÔ HÌNH THẬT, CÓ KIỂM NGƯỢC (MEM06, MEM08)")
    # C2 giữ 10 lượt gần nhất nguyên văn, nên phải có hơn 10 lượt thì mới có việc để
    # nén. Dựng bằng lượt THẬT qua giao diện — nếu dựng bằng cách nhét message vào
    # danh sách thì ta đang kiểm một thứ khác với thứ chạy trong sản phẩm.
    # C2 giữ K=10 lượt nguyên văn, và mỗi lần kiểm trượt thì K += 4. Phiên phải đủ dài
    # để sau một lần trượt vẫn còn chỗ nén — nếu không, ta đo nhầm "chưa tới lúc".
    print("  (dựng thêm 16 lượt để C2 có việc thật, kể cả sau một lần kiểm trượt…)")
    for i in range(16):
        g.go(f"Ghi chú {i + 1}: mình vừa xem lại phần nguồn của bo. Đường 3V3 lấy từ "
             f"LDO, tụ lọc 100 nF sát chân VDD, và mình đã đo thử điểm thứ {i + 1} "
             "trên bo mẫu. Ghi nhận giúp mình, chưa cần làm gì thêm.")
        g.doi_xong(200)

    g.go("Ngữ cảnh dài rồi. Nén giúp mình ở mức C2 đi.")
    a = g.doi_xong(400)

    from eide.protocol.ledger import Ledger
    so = Ledger(du_an / ".eide" / "ledger.jsonl")
    nen = [e for e in so.read() if e.kind == "compact"]
    b.kiem("Có ghi nhật ký nén trong sổ cái", bool(nen),
           ", ".join(sorted({str(e.data.get("buoc")) for e in nen})) or "không có")

    pre = [e for e in nen if e.data.get("buoc") == "pre"]
    b.kiem("PreCompact chạy TRƯỚC khi gọi mô hình", bool(pre),
           f"{len(pre)} lần · mã nhắc: {pre[0].data.get('ma_nhac_trong_doan') if pre else '—'}")

    xong = [e for e in nen if e.data.get("buoc") == "ok"]
    truot = [e for e in nen if e.data.get("buoc") == "kiem_truot"]
    khong = [e for e in nen if e.data.get("buoc") in ("khong_can", "khong_loi")]
    b.kiem("Nén ĐẠT kiểm, bị HUỶ, hay chưa tới lúc — luôn nói rõ là cái nào",
           bool(xong) or bool(truot) or bool(khong),
           f"{len(xong)} đạt · {len(truot)} trượt · {len(khong)} chưa tới lúc")

    # Ba ô dưới đây TỪNG bị bỏ qua im lặng khi C2 không chạy, làm số ca của bộ này lúc
    # 20 lúc 23 — và một bộ kiểm đổi số ca giữa hai lần chạy thì không so được với
    # chính nó (SCH-19). Nay luôn chấm, và "C2 không chạy" là một ô ĐỎ chứ không phải
    # một ô biến mất.
    b.kiem("C2 thật sự chạy và qua kiểm — tiền đề của cả phần này",
           bool(xong), f"{len(xong)} lần đạt")
    tt = (xong[-1].data.get("tom_tat", {}).get("muc", {})) if xong else {}
    b.kiem("Bản tóm tắt đủ mười mục, không mục nào biến mất",
           len(tt) == 10, f"{len(tt)} mục: {', '.join(list(tt)[:4])}…" if tt
           else "chưa có bản tóm tắt nào")
    b.kiem("Mục quyết định giữ được nội dung thật",
           any(k in str(tt.get("quyet_dinh", "")).upper() for k in ("MTP", "ADR")),
           str(tt.get("quyet_dinh", ""))[:120] or "—")
    b.kiem("Kiểm ngược có điểm số, không phải một lời hứa",
           bool(xong) and "/" in str(xong[-1].data.get("diem", "")),
           f"kiểm {xong[-1].data.get('diem')}" if xong else "—")

    b.phan("C · SAU KHI NÉN VẪN TRẢ LỜI ĐÚNG VỀ QUÁ KHỨ (MEM06)")
    g.go("Nhắc lại giúp mình: mình đã chốt dùng cơ chế gì để truyền tệp?")
    a = g.doi_xong(300)
    loi = a["loi_tac_tu_cuoi"]
    b.kiem("Vẫn trả lời đúng MTP sau khi nén", "MTP" in loi.upper(), loi[:140])

    b.phan("D · KHỐI BỘ NHỚ TRÊN GIAO DIỆN (MEM11, MEM12)")
    g.mo_tab("project")
    a = g.chup("tab-du-an")
    ma = {k["code"]: k for k in a["khoi_tren_tab"]}
    b.kiem("Có khối đồng hồ ngữ cảnh A14.6.1", "A14.6.1" in ma,
           ", ".join(sorted(ma)) or "không có khối nào")
    b.kiem("Có khối bản tóm tắt phiên A14.6.2", "A14.6.2" in ma,
           ma.get("A14.6.2", {}).get("summary", "")[:100])
    b.kiem("Có nhật ký nén A14.6.3 với điểm kiểm",
           "A14.6.3" in ma and ma["A14.6.3"]["so_hang"] > 0,
           ma.get("A14.6.3", {}).get("summary", "")[:100] or
           "chưa nén lần nào nên chưa có nhật ký")
    b.kiem("Có danh sách đang ghim A14.6.4", "A14.6.4" in ma,
           ma.get("A14.6.4", {}).get("summary", "")[:90])
    b.kiem("Không còn ký tự markdown thô trên tab",
           all("**" not in (k.get("chu_da_dung") or "") for k in a["khoi_tren_tab"]),
           "sạch")

    # ================================================================== UNHAPPY
    b.phan("E · BẢY ĐƯỜNG HỎNG")
    from eide.llm.gateway import Response, ToolCall
    from eide.memory import summary as sm
    from eide.memory.nen import BoNen

    def tt_args(**kw):
        d = {t: "—" for t, _, _ in sm.MUC}
        d.update(kw)
        return d

    def rsp_tt(**kw):
        return Response(tool_calls=[ToolCall("s", sm.TEN_TOOL_TOM_TAT, tt_args(**kw))])

    def rsp_kiem(*tl):
        return Response(tool_calls=[ToolCall("k", sm.TEN_TOOL_TRA_LOI,
                                             {"tra_loi": list(tl)})])

    def ms(n, dai=40):
        """Lượt có độ dài THẬT — lượt hai chữ thì nén xong còn to hơn lúc đầu, và ta
        sẽ đo nhầm cái khác."""
        r = []
        for i in range(n):
            r.append({"role": "user", "_kind": "say",
                      "text": f"việc {i}: " + "mô tả chi tiết việc cần làm " * dai})
            r.append({"role": "model",
                      "text": f"xong {i}: " + "thuật lại đã làm gì " * dai})
        return r

    ctx = _ctx(du_an)

    b.buoc("1. MẤT MÁT THẬT: gốc trả lời được, sau nén thì không → huỷ nén")
    from eide.llm import ScriptedGateway
    phieu = sm.lam_phieu_kiem(ctx.ledger, ctx.store)
    dung = [c.dap_an for c in phieu]
    sai = ["không biết"] * len(phieu)
    llm = ScriptedGateway([rsp_tt(muc_tieu="x"), rsp_kiem(*sai), rsp_kiem(*dung),
                           rsp_tt(muc_tieu="x"), rsp_kiem(*sai), rsp_kiem(*dung),
                           rsp_tt(muc_tieu="x"), rsp_kiem(*sai), rsp_kiem(*dung)])
    bn = BoNen(llm=llm, ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    m = ms(20)
    truoc = [dict(x) for x in m]
    kq = bn.nen(m, run_id="run-thu")
    b.kiem("Huỷ nén và ngữ cảnh về đúng như trước",
           not kq.ok and m == truoc, f"{kq.diem_kiem} · {kq.ly_do[:80]}")
    b.kiem("Điểm kiểm nói rõ mất mấy câu", "0/" in kq.diem_kiem, kq.diem_kiem)

    b.buoc("1b. Câu hỏi mô hình KHÔNG trả lời được ở đâu cả thì bị LOẠI")
    llm2 = ScriptedGateway([rsp_tt(muc_tieu="x"), rsp_kiem(*sai), rsp_kiem(*sai)])
    bn1b = BoNen(llm=llm2, ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    kq1b = bn1b.nen(ms(20), run_id="run-thu")
    b.kiem("Không tính là mất mát, và nói rõ là CHƯA kiểm",
           kq1b.ok and kq1b.diem_kiem == "KHÔNG kiểm được", kq1b.diem_kiem)
    b.kiem("Dòng báo cho người không được giả vờ đã kiểm",
           "chưa kiểm được" in kq1b.dong_he_thong(), kq1b.dong_he_thong()[:120])

    b.buoc("2. Mô hình hỏng giữa lúc tóm tắt")
    from eide.errors import llm_unavailable

    class Hong:
        name = "hong"
        def stream(self, **kw): raise llm_unavailable("529 overloaded", 3)
        def count_tokens(self, t): return len(t) // 3

    bn2 = BoNen(llm=Hong(), ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    m = ms(20)
    truoc = [dict(x) for x in m]
    kq = bn2.nen(m, run_id="run-thu")
    b.kiem("Giữ nguyên, không để transcript ở trạng thái nửa vời",
           not kq.ok and m == truoc, kq.ly_do[:110])

    b.buoc("3. Mô hình tóm tắt bằng văn xuôi thay vì theo lược đồ")
    bn3 = BoNen(llm=ScriptedGateway([Response(text="tôi tóm tắt thế này…")]),
                ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    m = ms(20)
    truoc = [dict(x) for x in m]
    kq = bn3.nen(m, run_id="run-thu")
    b.kiem("Không nhận, giữ nguyên", not kq.ok and m == truoc, kq.ly_do[:110])

    b.buoc("4. Bản tóm tắt hồi sinh điều người đã bảo quên")
    ctx.ledger.append("tombstone", {"noi_dung": "Luôn build với -O3",
                                    "section": "Quy ước"})
    bn4 = BoNen(llm=ScriptedGateway([rsp_tt(gia_dinh_dang_dung="Luôn build với -O3")]),
                ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    m = ms(20)
    truoc = [dict(x) for x in m]
    kq = bn4.nen(m, run_id="run-thu")
    b.kiem("Huỷ nén vì tóm tắt chứa điều đã quên",
           not kq.ok and "đã bảo quên" in kq.ly_do, kq.ly_do[:110])

    b.buoc("5. Message được ghim KHÔNG bị nén dù rất cũ")
    bn5 = BoNen(llm=ScriptedGateway([rsp_tt(muc_tieu="x")]),
                ledger=ctx.ledger, store=ctx.store, eide_md=ctx.eide_md)
    m = ms(20)
    m[0]["_kind"] = "decide"
    m[0]["text"] = "DUYỆT nạp firmware lên bo"
    bn5.nen(m, run_id="run-thu")
    b.kiem("Quyết định của người còn nguyên văn",
           any("DUYỆT nạp firmware" in str(x.get("text", "")) for x in m),
           "còn" if any("DUYỆT" in str(x.get("text", "")) for x in m) else "MẤT")

    b.buoc("6. Huỷ nén khi chưa nén lần nào")
    bn6 = BoNen(llm=ScriptedGateway([]), ledger=ctx.ledger, store=ctx.store,
                eide_md=ctx.eide_md)
    kq6 = bn6.huy_nen([])
    b.kiem("Nói thẳng là chưa có gì để huỷ",
           not kq6["ok"] and "chưa nén" in kq6["message_vi"].lower(),
           kq6["message_vi"][:100])

    b.buoc("7. Bộ nhớ người dùng từ chối bí mật và phỏng đoán")
    from eide.memory import BoNhoNguoiDung
    bnd = BoNhoNguoiDung(du_an / "memory-thu.md")
    k1 = bnd.kiem("toolchain", "token là ghp_abcdefghijklmnopqrst")
    k2 = bnd.kiem("trinh_bay", "có vẻ anh này chưa rành về I2C")
    k3 = bnd.kiem("trinh_bay", "thích câu trả lời ngắn")
    b.kiem("Từ chối khoá/token", not k1.ok and "keychain" in k1.ly_do, k1.ly_do[:100])
    b.kiem("Từ chối phỏng đoán về người", not k2.ok and "phỏng đoán" in k2.ly_do,
           k2.ly_do[:100])
    b.kiem("Nhận sở thích trình bày", k3.ok, "nhận")

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
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-mem-c")
        registry = build_registry()
        ids = IdGen(config.paths.state_dir)
        ledger = Ledger(config.paths.ledger)
        history = History(paths=config.paths, store=store, ledger=ledger, ids=ids)
        run_id = "run-thu"
        tai_lieu: dict = {}
        pending_cards: list = []
        loi_nguoi_trong_phien: list = []
        awaiting_human = False
        agent = None
        def emit(self, c): pass
    return C()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-mem-c").resolve()
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
