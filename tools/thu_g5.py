#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm G5 qua giao diện thật — bản ưng ý, khôi phục, rẽ nhánh.

    python tools/thu_g5.py

Happy (CX12→CX14): tác tử ĐỀ XUẤT ghi bản ưng ý sau một mốc và để người đặt tên →
người đặt tên qua thẻ → làm tiếp rồi so sánh hai bản → khôi phục về bản cũ mà không
mất việc của người → đánh dấu release.

Unhappy (tám đường): khôi phục bản không có; ghi trùng tên; sửa bản bất biến; đánh dấu
release cho checkpoint ngầm; RDP khi chưa có release (CX15); so sánh với bản đã mất
blob; chuyển nhánh không tồn tại; tác tử tự đặt tên bản ưng ý.
"""

from __future__ import annotations

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


def lich_su(du_an: pathlib.Path):
    """Mở lại kho của app từ ngoài — đọc đúng cái app vừa ghi, không phải bản trong đầu."""
    from eide import Config
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import Store

    cfg = Config.for_project(du_an)
    st = Store(cfg.paths.store_db)
    h = History(paths=cfg.paths, store=st, ledger=Ledger(cfg.paths.ledger),
                ids=IdGen(cfg.paths.state_dir))
    return h, st


def the_snapshot(anh: dict) -> dict | None:
    for k in anh["khoi_tren_tab"]:
        if k["type"] == "snapshots":
            return k
    return None


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang()
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    # ================================================================== HAPPY
    b.phan("A · TAB LỊCH SỬ KHI CHƯA CÓ BẢN ƯNG Ý NÀO")
    g.mo_tab("history")
    a = g.chup("lich-su-trong")
    kh = next((k for k in a["khoi_tren_tab"] if "ưng ý" in k["title"]), None)
    b.kiem("Tab Lịch sử có mục Bản ưng ý", kh is not None,
           "; ".join(k["title"] for k in a["khoi_tren_tab"]))
    if kh:
        ba = [kh.get("chua_co", ""), kh.get("vi_sao", ""), kh.get("can_gi", "")]
        b.kiem("Ô trống nói ba điều: chưa có gì · vì sao · cần gì",
               kh["type"] == "empty" and all(x.strip() for x in ba),
               " | ".join(x[:45] for x in ba))
        b.kiem("KHÔNG còn câu 'Snapshot là bước G5'",
               any(ba) and "G5" not in " ".join(ba), ba[1][:90])

    b.phan("B · MỘT MỐC ĐÁNG NHỚ → TÁC TỬ ĐỀ XUẤT, NGƯỜI ĐẶT TÊN (CX12)")
    g.go("Dự án của mình: bộ thu video qua Ethernet cho máy soi công nghiệp. "
         "Ghi giúp mình hai yêu cầu: luồng video phải đạt tối thiểu 8 MB/s, "
         "và thiết bị phải khởi động xong trong 3 giây.")
    a = g.doi_xong(300)

    hist, st = lich_su(du_an)
    reqs = st.list("req", limit=20)
    b.kiem("Ghi được yêu cầu vào kho", len(reqs) >= 2, f"{len(reqs)} yêu cầu")

    g.go("Hai yêu cầu này mình chốt rồi. Mình muốn ghi lại trạng thái này "
         "để sau có làm hỏng thì quay về được.")
    a = g.doi_xong(300)

    the = [c for c in a["the_dang_cho"] if c["loai"] == "clarify"]
    b.kiem("Tác tử dựng thẻ hỏi, KHÔNG tự ghi", bool(the),
           f"{len(a['the_dang_cho'])} thẻ: " +
           "; ".join(f"{c['loai']}/{c['tieu_de'][:40]}" for c in a["the_dang_cho"]))
    b.kiem("Tác tử KHÔNG tự đặt tên bản ưng ý (§E6.2)",
           not hist.snapshots.all(),
           f"{len(hist.snapshots.all())} bản đã ghi trước khi người trả lời")
    if the:
        b.kiem("Thẻ có hỏi tên", the[0]["so_cau_hoi"] >= 1,
               f"{the[0]['so_cau_hoi']} câu")
        b.kiem("Thẻ nói bỏ qua thì giả định gì", the[0]["co_gia_dinh"])

        # Người gõ tên vào thẻ rồi bấm "Gửi trả lời" — đúng đường nút bấm đi.
        g._gui({"kind": "choose",
                "data": {"card_id": the[0].get("card_id") or the[0]["gate_id"],
                         "answers": {"ten": "v0.1-chot-yeu-cau",
                                     "ghi_chu": "hai yêu cầu đầu đã chốt"}},
                "origin": {"surface": "console"}})
        a = g.doi_xong(300)

        hist, st = lich_su(du_an)
        ds = hist.snapshots.all()
        b.kiem("Bản ưng ý được ghi ĐÚNG TÊN người đặt",
               any(s.name == "v0.1-chot-yeu-cau" for s in ds),
               "; ".join(s.name for s in ds) or "không bản nào")
        b.kiem("Thẻ đã trả lời rời khỏi hàng chờ",
               not [c for c in a["the_dang_cho"] if c["loai"] == "clarify"],
               f"{len(a['the_dang_cho'])} thẻ còn lại")

    g.mo_tab("history")
    a = g.chup("co-snapshot")
    kh = the_snapshot(a)
    b.kiem("Tab Lịch sử hiện bản ưng ý vừa ghi", kh is not None and kh["so_muc"] >= 1,
           kh["summary"][:100] if kh else "không có khối snapshots")

    b.phan("C · LÀM TIẾP RỒI SO SÁNH HAI BẢN (CX14)")
    g.go("Thêm một yêu cầu nữa: thiết bị phải chạy được ở 60 °C. "
         "Xong thì ghi tiếp một bản ưng ý tên v0.2-them-nhiet nhé.")
    a = g.doi_xong(300)

    hist, st = lich_su(du_an)
    ds = sorted(hist.snapshots.all(), key=lambda s: s.ts)
    b.kiem("Có hai bản ưng ý", len(ds) >= 2, "; ".join(s.name for s in ds))

    if len(ds) >= 2:
        g.go(f"So sánh giúp mình bản {ds[0].name} với bản {ds[-1].name} khác nhau chỗ nào.")
        a = g.doi_xong(300)
        loi = a["loi_tac_tu_cuoi"]
        b.kiem("Tác tử nói ra được khác biệt cụ thể",
               any(x in loi.lower() for x in ("yêu cầu", "req", "60", "nhiệt")),
               loi[:160])

        kq = hist.so_sanh_snapshot(ds[0].id, ds[-1].id)
        b.kiem("So sánh nhóm theo LOẠI hiện vật, không phẳng",
               kq["ok"] and all("loai" in k for k in kq["khac_biet"]),
               "; ".join(f"{k['loai']}: +{len(k['them'])}/~{len(k['doi'])}"
                         for k in kq["khac_biet"]))

    b.phan("D · KHÔI PHỤC KHÔNG XOÁ LỊCH SỬ, KHÔNG NUỐT VIỆC CỦA NGƯỜI (CX13)")
    if len(ds) >= 2:
        truoc = hist.se_mat_gi_khi_khoi_phuc(ds[0].id)
        b.kiem("Liệt kê SẼ MẤT GÌ trước khi hỏi", bool(truoc.get("se_mat_vi")),
               "; ".join(truoc.get("se_mat_vi", []))[:150])
        so_cs = len(hist.log.all())

        g.go(f"Mình muốn quay về bản {ds[0].name}. Nhưng giữ lại bản hiện tại "
             "thành một nhánh tên thu-60-do để còn xem lại.")
        a = g.doi_xong(300)

        # Khôi phục là R2/G-HIST: nó PHẢI dừng lại hỏi. Người bấm duyệt ở đây.
        cong = [c for c in a["the_dang_cho"] if c["loai"] == "gate"]
        b.kiem("Khôi phục dừng lại hỏi, không tự làm",
               bool(cong), "; ".join(c["gate"] for c in a["the_dang_cho"]) or "không thẻ nào")
        if cong:
            b.kiem("Thẻ cổng nói rõ sẽ mất gì trước khi có nút bấm",
                   cong[0]["so_hau_qua"] >= 1, f"{cong[0]['so_hau_qua']} dòng hậu quả")
            g.quyet_cong(cong[0]["gate_id"], True, "đồng ý, mình đã giữ nhánh rồi")
            a = g.doi_xong(300)

        hist, st = lich_su(du_an)
        b.kiem("Khôi phục tạo changeset MỚI, không xoá cái cũ",
               len(hist.log.all()) > so_cs,
               f"{so_cs} → {len(hist.log.all())} changeset")
        b.kiem("Bản hiện tại được giữ lại trước khi lùi",
               hist.snapshots.theo_ten("thu-60-do") is not None
               or "thu-60-do" in hist.danh_sach_nhanh(),
               "; ".join(s.name for s in hist.snapshots.all()))
        b.kiem("Kho quay về đúng nội dung bản cũ",
               len(st.list("req", limit=20)) == 2,
               f"{len(st.list('req', limit=20))} yêu cầu")

        g.mo_tab("history")
        a = g.chup("sau-khoi-phuc")
        b.kiem("Dòng thời gian vẫn còn đủ các bước đã đi",
               any(k["type"] == "timeline" or k["so_muc"] >= 3
                   for k in a["khoi_tren_tab"]),
               "; ".join(f"{k['title']}={k['so_muc']}" for k in a["khoi_tren_tab"]))

    b.phan("Đ · MÀN HÌNH KHÔNG CÒN KÝ TỰ MARKDOWN THÔ")
    tho: list[str] = []
    for tab in ("console", "requirements", "knowledge", "history", "code", "documents"):
        g.mo_tab(tab)
        a = g.chup(f"tho-{tab}")
        if "**" in a.get("loi_tac_tu_render", ""):
            tho.append(f"{tab}: lời tác tử")
        for k in a["khoi_tren_tab"]:
            if "**" in k.get("chu_da_dung", ""):
                tho.append(f"{tab}/{k['code']} {k['title']}")
    b.kiem("Không tab nào còn hiện ** chưa dựng", not tho,
           "; ".join(tho[:4]) if tho else "sạch trên 6 tab")

    g.mo_tab("console")
    a = g.chup("render-console")
    b.kiem("Lời tác tử trong Console đã qua bộ dựng",
           "**" not in a.get("loi_tac_tu_render", ""),
           a.get("loi_tac_tu_render", "")[:130])
    b.kiem("Bộ dựng tách được cấu trúc, không dồn thành một đoạn",
           len(set(a.get("khoi_markdown") or [])) >= 2,
           ", ".join(a.get("khoi_markdown") or []))

    # ================================================================== UNHAPPY
    b.phan("E · TÁM ĐƯỜNG HỎNG")
    from eide.tools import build_registry
    reg = build_registry()
    ctx = _ctx(du_an)
    hist = ctx.history

    b.buoc("1. Khôi phục một bản không tồn tại")
    r = reg.run("snapshot.restore", {"snapshot": "snap-999"}, ctx)
    b.kiem("Từ chối và chỉ đường tra danh sách",
           not r.ok and "snap-999" in r.error.message_vi
           and "snapshot.list" in r.error.alternatives,
           r.error.message_vi[:120] if r.error else "lọt!")

    b.buoc("2. Ghi bản ưng ý trùng tên")
    ten = "ban-de-thu-trung-ten"
    if hist.snapshots.theo_ten(ten) is None:
        hist.tao_snapshot(ten=ten)          # dựng điều kiện, không mượn phần happy
    r = reg.run("snapshot.create", {"ten": ten}, ctx)
    b.kiem("Từ chối trùng tên, nói rõ bản nào đang giữ tên đó",
           not r.ok and "Đã có bản ưng ý tên" in r.error.message_vi,
           r.error.message_vi[:130] if r.error else "ghi được — hai bản cùng tên!")
    b.kiem("Không xui tác tử tự đổi tên người đặt",
           bool(r.error) and "đừng tự đổi tên" in r.error.hint_for_agent,
           r.error.hint_for_agent[:110] if r.error else "")

    b.buoc("2b. Tác tử tự nghĩ ra tên bản ưng ý (§E6.2)")
    from eide.hooks import HookBus as _HB
    from eide.hooks.standard import register_standard_hooks as _rsh
    from eide.policy import PolicyEngine as _PE
    ctx.loi_nguoi_trong_phien = ["ghi lại giúp mình trạng thái này"]
    goi_ten = {"tool": "snapshot.create", "args": {"ten": "sau-khi-sua-driver"}}
    f = _rsh(_HB()).pre_tool_use(goi_ten, ctx).facts
    d = _PE().decide(goi_ten, f)
    b.kiem("Chặn — tên đó người dùng chưa từng nói",
           f["snapshot.ten_tu_nguoi"] is False and d.action == "deny",
           d.reason_vi[:130])
    ctx.loi_nguoi_trong_phien = ["ghi bản ưng ý tên v9-thu-nghiem nhé"]
    goi_ok = {"tool": "snapshot.create", "args": {"ten": "v9-thu-nghiem"}}
    f2 = _rsh(_HB()).pre_tool_use(goi_ok, ctx).facts
    b.kiem("Người đã nói tên thì KHÔNG hỏi lại (N4)",
           f2["snapshot.ten_tu_nguoi"] is True
           and _PE().decide(goi_ok, f2).action == "allow",
           f"ten_tu_nguoi={f2['snapshot.ten_tu_nguoi']}")

    b.buoc("3. Sửa một bản ưng ý đã ghi (bất biến)")
    s0 = hist.snapshots.all()[0] if hist.snapshots.all() else None
    if s0:
        try:
            hist.snapshots.ghi(s0)
            b.kiem("Bản ưng ý là bất biến", False, "ghi đè được!")
        except ValueError as e:
            b.kiem("Bản ưng ý là bất biến — chặn bằng mã, không bằng lời hứa",
                   "bất biến" in str(e), str(e)[:120])

    b.buoc("4. Đánh dấu release cho một checkpoint ngầm")
    cp = hist.tao_snapshot(ten="", kind="checkpoint", ghi_chu="thử")
    r = reg.run("snapshot.release", {"snapshot": cp.id}, ctx)
    b.kiem("Từ chối — checkpoint không phải bản người chọn",
           not r.ok and "Checkpoint" in r.error.message_vi,
           r.error.message_vi[:130] if r.error else "lọt!")

    b.buoc("5. RDP khi chưa có bản release (CX15)")
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    from eide.policy import PolicyEngine
    bus = register_standard_hooks(HookBus())
    goi = {"tool": "target.dangerous", "args": {"what": "rdp"}}
    f = bus.pre_tool_use(goi, ctx).facts
    d = PolicyEngine().decide(goi, f)
    b.kiem("Chặn khi chưa có release, nói rõ vì sao",
           f["snapshot.has_release"] is False and d.action == "deny"
           and "release" in d.reason_vi.lower(), d.reason_vi[:130])

    b.buoc("6. Có release rồi thì chuyển sang HỎI, không chặn cứng")
    if s0:
        hist.snapshots.danh_dau_release(s0.id)
        f2 = bus.pre_tool_use(goi, _ctx(du_an)).facts
        d2 = PolicyEngine().decide(goi, f2)
        b.kiem("Có release → thẻ cổng, người quyết",
               f2["snapshot.has_release"] is True and d2.action == "ask",
               f"has_release={f2['snapshot.has_release']} → {d2.action}")

    b.buoc("7. Chuyển sang một nhánh không tồn tại")
    r = reg.run("branch.switch", {"ten": "nhanh-khong-bao-gio-co"}, ctx)
    kq = r.data if r.ok else {}
    b.kiem("Nói không có nhánh đó và liệt kê nhánh đang có",
           (not r.ok) or (not kq.get("ok") and kq.get("dang_co")),
           str(kq)[:130] if r.ok else r.error.message_vi[:130])

    b.buoc("8. So sánh với một bản đã mất bản sao nội dung")
    from eide.snapshot import Snapshot, _now
    hist.snapshots.ghi(Snapshot(id="snap-hong", ts=_now(), kind="named", name="hong",
                                contents={"store_export_hash": "0" * 64}))
    r = hist.se_mat_gi_khi_khoi_phuc("snap-hong")
    b.kiem("Gọi thẳng là lỗi TOÀN VẸN, không im lặng khôi phục rỗng",
           not r["ok"] and "toàn vẹn" in r["message_vi"],
           r["message_vi"][:130])

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
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-g5")
        registry = build_registry()
        ids = IdGen(config.paths.state_dir)
        history = History(paths=config.paths, store=store,
                          ledger=Ledger(config.paths.ledger), ids=ids)
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
    d = (REPO / "du-lieu/thu-nghiem-g5").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "main.c").write_text(
        "#include <stdint.h>\n\nint main(void)\n{\n    return 0;\n}\n", "utf-8")
    (d / "ghi-chu.md").write_text(
        "# Bộ thu video Ethernet\n\nMáy soi công nghiệp, truyền ảnh về máy tính.\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
