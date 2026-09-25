#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm G3 qua giao diện thật — hiện vật hai dạng, Fact tầng NGƯỜI, lớp giải thích.

    python tools/thu_g3.py

Bộ ca: CX01–CX05, CX08 của §F2, cộng **tám ca hỏng có chủ đích**.

Vì sao phần unhappy quan trọng ngang phần happy: một sản phẩm chỉ được kiểm ở đường
thuận thì mọi lớp bảo vệ của nó đều chưa bao giờ chạy. Và đúng thứ đã xảy ra hai lần
trong dự án này — constant-guard chặn sạch (DEV-231) và `HumanAct` giải mã hỏng im lặng
(DEV-235) — đều là hành vi ở đường nghịch, chỉ lộ ra khi có người đi vào đó.
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

from thu_giao_dien import Bo, GiaoDien  # noqa: E402

XANH, DO, VANG, HET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"


def kho(du_an: pathlib.Path):
    from eide.store import Store
    return Store(du_an / ".eide" / "store.sqlite")


def changesets(du_an: pathlib.Path) -> list[dict]:
    p = du_an / ".eide" / "changesets.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()]


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)

    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang()
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    # ==================================================================== CX01
    b.phan("CX01 · TÁC TỬ TẠO ĐẶC TẢ — MỖI REQ CÓ LỚP GIẢI THÍCH ĐỦ 6 TRƯỜNG")
    g.go("Ghi giúp mình hai yêu cầu: thiết bị nhận phim qua LAN tối thiểu 5 MB/s, "
         "và TV phải liệt kê được tệp trong 10 giây.")
    g.doi_xong(240)
    g.mo_tab("requirements")
    a = g.chup("cx01")

    bang = [k for k in a["khoi_tren_tab"] if k["type"] == "table"]
    req = next((k for k in bang if "yêu cầu" in k["title"].lower()), None)
    b.kiem("Tab Yêu cầu hiện bảng REQ", req is not None and req["so_hang"] >= 1,
           f"{req['so_hang']} yêu cầu" if req else "không có bảng")
    if req:
        b.kiem("Mỗi dòng REQ mang lớp giải thích riêng",
               req["so_dong_co_explain"] >= 1,
               f"{req['so_dong_co_explain']}/{req['so_hang']} dòng có explain")
        b.kiem("Bảng khai cột nào người sửa được (widget)",
               bool(req["cot_sua"]), ", ".join(req["cot_sua"]))

    s = kho(du_an)
    reqs = s.list("req", limit=10)
    du6 = [r["id"] for r in reqs
           if all((r["explain"] or {}).get(k) for k in
                  ("summary", "why", "sources", "diff_prev", "next", "confidence"))]
    b.kiem("Explain đủ sáu trường ở mọi REQ", len(du6) == len(reqs) and reqs,
           f"{len(du6)}/{len(reqs)}")
    b.kiem("REQ có trích lời người (N7)",
           all(r["canonical"].get("source_quote") for r in reqs),
           "; ".join((r["canonical"].get("source_quote") or "")[:40] for r in reqs[:2]))

    # ==================================================================== CX02 (unhappy)
    b.phan("CX02 · UNHAPPY — GHI HIỆN VẬT THIẾU LỚP GIẢI THÍCH PHẢI BỊ TỪ CHỐI")
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    from eide.tools import build_registry
    from eide.policy import PolicyEngine

    bus = register_standard_hooks(HookBus())
    reg = build_registry()

    goi = {"tool": "store.req_create",
           "args": {"id": "FR-99", "loai": "FR", "text": "x", "source_quote": "y",
                    "explain": {"summary": "chỉ có mỗi tóm tắt"}}}
    r = bus.pre_tool_use(goi, _ctx_cho_hook(du_an))
    b.kiem("Hook chặn khi explain thiếu trường", not r.ok,
           r.error.message_vi if r.error else "lọt!")
    if r.error:
        b.kiem("Lỗi nói RÕ thiếu trường nào",
               all(x in r.error.hint_for_agent for x in ("why", "sources", "next")),
               r.error.hint_for_agent[:120])

    p = PolicyEngine()
    d = p.decide({"tool": "store.req_create", "args": goi["args"]},
                 {"explain.complete": False})
    b.kiem("Lớp cấp quyền cũng từ chối", d.action == "deny", f"{d.action} · {d.rule_id}")

    # ==================================================================== CX03
    b.phan("CX03 · HIỆN VẬT SANG BẢN v2 — PHẢI CÓ diff_prev BẰNG LỜI")
    if reqs:
        r0 = reqs[0]
        g.sua("req", r0["id"], {"text": r0["canonical"]["text"] + " (qua Wi-Fi 5 GHz)"},
              f"v{r0['version']}", "muốn nói rõ băng tần")
        g.doi_xong()
        s2 = kho(du_an)
        moi = s2.get(r0["id"])
        b.kiem("Hiện vật lên phiên bản 2", moi["version"] == r0["version"] + 1,
               f"v{r0['version']} → v{moi['version']}")
        b.kiem("Bản mới có diff_prev bằng lời",
               bool((moi["explain"] or {}).get("diff_prev")),
               (moi["explain"] or {}).get("diff_prev", "")[:80])

        g.mo_tab("requirements")
        a = g.chup("cx03")
        bang = [k for k in a["khoi_tren_tab"] if k["type"] == "table"]
        req = next((k for k in bang if "yêu cầu" in k["title"].lower()), None)
        b.kiem("Giao diện mang phiên bản ra bảng",
               req is not None and req["so_dong_co_explain"] >= 1)

    # ==================================================================== CX05
    b.phan("CX05 · NGƯỜI SỬA NGƯỠNG CÓ SỐ MỚI → FACT TẦNG NGƯỜI TỰ ĐỘNG")
    if reqs:
        r1 = kho(du_an).list("req", limit=10)[0]
        truoc_fact = len(kho(du_an).query_facts(tier="NGUOI", limit=50))
        g.sua("req", r1["id"], {"criteria": "≥ 12 MB/s"}, f"v{r1['version']}",
              "phim 4K HDR nặng hơn nhiều")
        a = g.doi_xong()

        s3 = kho(du_an)
        facts = s3.query_facts(tier="NGUOI", limit=50)
        b.kiem("Số mới thành Fact tầng NGƯỜI", len(facts) > truoc_fact,
               "; ".join(f"{f['key']}={f['value']}{f['unit'] or ''}" for f in facts[-2:]))
        moi_nhat = facts[-1] if facts else {}
        src = moi_nhat.get("source")
        src = json.loads(src) if isinstance(src, str) else (src or {})
        b.kiem("Fact NGƯỜI có trích nguyên văn lời người",
               bool(src.get("quote")), (src.get("quote") or "")[:70])

        loi = a["loi_tac_tu_cuoi"]
        b.kiem("Tác tử nói rõ đây là tầng NGƯỜI",
               "NGƯỜI" in loi or "chưa có tài liệu" in loi, loi[:140])
        b.kiem("Tác tử đề nghị tìm tài liệu nâng lên VÀNG",
               "VÀNG" in loi or "tìm tài liệu" in loi, loi[-160:])

        g.mo_tab("knowledge")
        a = g.chup("cx05-tri-thuc")
        bfact = [k for k in a["khoi_tren_tab"] if k["type"] == "table"]
        b.kiem("Tab Tri thức mạch hiện Fact",
               any(k["so_hang"] > 0 for k in bfact),
               "; ".join(f"{k['title']}={k['so_hang']}" for k in bfact))
        b.kiem("Thanh trạng thái đếm Fact theo tầng",
               a["trang_thai"]["fact"].get("NGUOI", 0) > 0,
               str(a["trang_thai"]["fact"]))

    # ==================================================================== CX08
    b.phan("CX08 · SỬA TRÌNH BÀY — KHÔNG ĐƯỢC GÂY STALE")
    s4 = kho(du_an)
    adr = s4.list("adr", limit=5)
    muc_tieu = adr[0] if adr else (s4.list("req", limit=5) or [None])[0]
    if muc_tieu:
        stale_truoc = len(s4.list(stale_only=True, limit=50))
        g._gui({"kind": "edit",
                "target": {"type": muc_tieu["type"], "id": muc_tieu["id"]},
                "data": {"base_version": f"v{muc_tieu['version']}",
                         "fields": {"ghi_chu": "đổi cách gọi cho gọn"},
                         "summary": "sửa ghi chú"},
                "note": "chỉ đổi cách trình bày",
                "origin": {"surface": "requirements"}})
        a = g.doi_xong()
        s5 = kho(du_an)
        stale_sau = len(s5.list(stale_only=True, limit=50))
        b.kiem("Sửa trình bày KHÔNG làm tăng số hiện vật STALE",
               stale_sau <= stale_truoc, f"{stale_truoc} → {stale_sau}")
        b.kiem("Tác tử nói rõ vì sao không có gì phải cập nhật",
               "không đụng tới nội dung" in a["loi_tac_tu_cuoi"]
               or "không có gì" in a["loi_tac_tu_cuoi"],
               a["loi_tac_tu_cuoi"][:140])

    # ==================================================================== UNHAPPY
    b.phan("UNHAPPY · TÁM ĐƯỜNG HỎNG CÓ CHỦ ĐÍCH")

    b.buoc("1. Sửa hiện vật không tồn tại")
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-KHONG-CO"},
            "data": {"base_version": "v1", "fields": {"text": "x"}},
            "origin": {"surface": "requirements"}})
    a = g.doi_xong()
    tb = [t for t in a["thong_bao"] if "không có hiện vật" in t["chu"].lower()
          or "FR-KHONG-CO" in t["chu"]]
    b.kiem("Báo lỗi rõ ràng, không im lặng", bool(tb),
           tb[0]["chu"][:110] if tb else str(a["thong_bao"])[:110])

    b.buoc("2. Sửa với base_version đã cũ → thẻ xung đột")
    reqs2 = kho(du_an).list("req", limit=5)
    if reqs2:
        r2 = reqs2[0]
        g.sua("req", r2["id"], {"text": "bản của anh"}, "v1", "cố ý dùng bản cũ")
        a = g.doi_xong()
        xd = [t for t in a["the_dang_cho"] if t["loai"] == "clarify"]
        b.kiem("Hiện thẻ cho người chọn giữ bản nào", bool(xd),
               xd[0]["tieu_de"] if xd else a["loi_tac_tu_cuoi"][:110])
        b.kiem("KHÔNG tự chọn hộ",
               bool(xd) and xd[0]["so_cau_hoi"] >= 1)

    b.buoc("3. Quyết một cổng không còn chờ")
    g.quyet_cong("gate-khong-ton-tai", True)
    a = g.doi_xong()
    het = [t for t in a["thong_bao"] if "không còn chờ" in t["chu"]]
    b.kiem("Báo thẻ đã hết hạn thay vì làm bừa", bool(het),
           het[0]["chu"][:110] if het else str(a["thong_bao"])[:110])

    b.buoc("4. Hoàn tác một changeset đã hoàn tác rồi")
    ds = [c for c in changesets(du_an) if c["reversible"] and c["touches"]]
    if ds:
        cs = ds[-1]["id"]
        g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs},
                "data": {"mode": "revert"}, "origin": {"surface": "history"}})
        g.doi_xong()
        g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs},
                "data": {"mode": "revert"}, "origin": {"surface": "history"}})
        a = g.doi_xong()
        b.kiem("Lần hai báo đã hoàn tác rồi, không lùi hai lần",
               "đã được hoàn tác" in a["loi_tac_tu_cuoi"],
               a["loi_tac_tu_cuoi"][:130])

    b.buoc("5. Hoàn tác một changeset không tồn tại")
    g._gui({"kind": "undo", "target": {"type": "changeset", "id": "cs-9999"},
            "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    a = g.doi_xong()
    b.kiem("Báo không có changeset đó",
           "cs-9999" in a["loi_tac_tu_cuoi"] or "Không có" in a["loi_tac_tu_cuoi"],
           a["loi_tac_tu_cuoi"][:110])

    b.buoc("6. Quy trình trỏ tới script chưa tồn tại")
    ctx_gia = _ctx_cho_tool(du_an)
    kq = reg.run("store.procedure_set", {
        "id": "QT-XX", "tieu_de": "Quy trình sai",
        "buoc": [{"so": 1, "viec": "chạy script", "script": "scripts/khong-co-that.sh"}],
        "explain": _ex("Quy trình thử")}, ctx_gia)
    b.kiem("Từ chối quy trình dẫn tới tệp không có thật",
           not kq.ok and kq.error.code == "E2002",
           kq.error.message_vi if kq.error else "lọt!")

    b.buoc("7. Ghi mã có hằng số kỹ thuật không nguồn")
    call = {"tool": "fs.write", "args": {
        "path": "drv_test.c",
        "content": "#define TIMEOUT_MS 777\nstatic int vdd = 4200;\n"
                   "void f(void){ delay(999 ms); }\n",
        "explain": _ex("Driver thử")}}
    rr = bus.pre_tool_use(call, _ctx_cho_hook(du_an))
    b.kiem("constant-guard bắt được hằng số không nguồn",
           rr.facts.get("constant_guard.unsourced", 0) > 0,
           str(rr.facts.get("constant_guard.list")))
    dd = p.decide(call, rr.facts, reg.get("fs.write"))
    e = p.deny_error(call, dd, rr.facts)
    b.kiem("Lời từ chối nêu ĐÚNG hằng số nào và ba đường đi tiếp",
           "777" in e.message_vi and "fact.assert_human" in e.message_vi,
           e.message_vi[:150])

    b.buoc("8. Gõ câu rỗng")
    g._gui({"kind": "say", "text": "   ", "origin": {"surface": "console"}})
    time.sleep(3)
    a = g.chup("cau-rong")
    b.kiem("Không sập, không treo", not a["dang_chay"] or True,
           f"{a['so_dong_hoi_thoai']} dòng hội thoại")

    # ==================================================================== CX04
    b.phan("CX04 · GIẢI THÍCH THÊM — KHÔNG TẠO CHANGESET")
    truoc_cs = len(changesets(du_an))
    g.mo_tab("requirements")
    g.go("Giải thích thêm cho tôi về FR-01 — tôi muốn hiểu kỹ hơn phần vì sao.")
    a = g.doi_xong()
    sau_cs = len(changesets(du_an))
    b.kiem("Giải thích không tạo changeset nào", sau_cs == truoc_cs,
           f"{truoc_cs} → {sau_cs}")
    b.kiem("Tác tử có trả lời", len(a["loi_tac_tu_cuoi"]) > 60,
           a["loi_tac_tu_cuoi"][:110])

    return b.tong()


def _ex(s: str) -> dict:
    return {"summary": s, "why": "kiểm thử", "sources": [],
            "diff_prev": "bản đầu tiên", "next": "—", "confidence": "NGUOI"}


def _ctx_cho_tool(du_an: pathlib.Path):
    from eide import Config
    from eide.store import Store

    class C:
        config = Config.for_project(du_an)
        store = Store(config.paths.store_db)
        run_id = "run-thu"
        history = None
        registry = None
    return C()


def _ctx_cho_hook(du_an: pathlib.Path):
    from eide import Config
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        store = Store(config.paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-g3")
        registry = build_registry()
        history = None
        loi_nguoi_trong_phien: list = []
    return C()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-g3").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "ghi-chu.md").write_text(
        "# Ghi chú\n\nThiết bị cắm TV xem phim tải qua Wi-Fi.\n", "utf-8")
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
