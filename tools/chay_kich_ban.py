#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bộ chạy kịch bản đo — EIDE-MDD-40 §F1, §F3.

    "Chạy qua HumanAct (headless UI) mỗi ca 5 lần; chấm theo lần chạy đầy đủ;
     ca đạt phải nêu cơ chế bảo vệ."

Cách dùng:

    # Chạy thật (cần GEMINI_API_KEY trong .env)
    python tools/chay_kich_ban.py --bo tests/kich_ban/tc001_007.yaml --lan 5

    # Chỉ một ca, xem toàn bộ lời qua tiếng lại
    python tools/chay_kich_ban.py --ca TC004 --lan 1 --chi-tiet

    # Ghi lại phản hồi thật để phát lại trong CI mà không tốn quota
    python tools/chay_kich_ban.py --ghi ket-qua-do/ban-ghi/

Nguyên tắc chấm (N6 — không đạt giả):
  - Tiêu chí nằm trong tệp YAML, không nằm trong đầu người chạy.
  - Không sửa tiêu chí để ép đạt. Ca không đạt thì ghi rõ vì sao.
  - Ca ngoài phạm vi bước hiện tại được đánh dấu riêng, KHÔNG tính là "không đạt" —
    gọi một khoảng trống phạm vi là lỗi thì bảng kết quả nói sai về sản phẩm.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from datetime import date
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import yaml  # noqa: E402

from eide import Config, load_dotenv  # noqa: E402
from eide.errors import EideError  # noqa: E402
from eide.llm import make_gateway  # noqa: E402
from eide.loop import Agent  # noqa: E402
from eide.protocol.rpc import Core  # noqa: E402

SO_CO_DON_VI = re.compile(
    r"\d[\d.,]*\s*(?:%|kbps|Mbps|bps|bit/s|B/s|KB/s|MB/s|GB|TB|MB|KB|mAh|Ah|mA|A|mV|V|W|mW|"
    r"kHz|MHz|GHz|Hz|ms|µs|us|ns|s|giây|phút|giờ|ngày|tháng|năm|đồng|VND|USD|\$)",
    re.IGNORECASE)


class _KhongCoKhoa:
    """Cổng mô hình khi chưa cấu hình khoá — nổ đúng lý do thay vì im lặng trả rỗng."""

    name = "khong-co-khoa"

    def __init__(self, err: EideError):
        self.err = err

    def stream(self, **kw):
        raise self.err

    def count_tokens(self, text: str) -> int:
        return int(len(text) / 3.0)


# =========================================================================== chạy một lần
def chay_mot_lan(ca: dict[str, Any], thu_muc: pathlib.Path, *, ghi: pathlib.Path | None,
                 chi_tiet: bool) -> dict[str, Any]:
    cfg = Config.for_project(thu_muc)
    try:
        gw = make_gateway(cfg.model, record=(ghi / f"{ca['ma']}.jsonl") if ghi else None)
    except EideError as e:
        # Chưa có khoá: các ca được S0 giải quyết xác định VẪN chạy và vẫn chấm được —
        # đó chính là điều đáng đo ở lớp 0 token. Ca cần mô hình sẽ báo đúng lý do.
        gw = _KhongCoKhoa(e)
    agent = Agent(cfg, llm=gw, project_name=thu_muc.name)

    loi_tac_tu: list[str] = []
    the: list[dict[str, Any]] = []
    thong_bao: list[dict[str, Any]] = []

    def nhan(cmd):
        p = cmd.params
        if cmd.method == "console.post" and p.get("role") == "agent":
            loi_tac_tu.append(p["text"])
            if p.get("card"):
                the.append(p["card"])
            if chi_tiet:
                print(p["text"])
        elif cmd.method == "notice":
            thong_bao.append(p)
            if chi_tiet:
                print(f"  [{p['level']}] {p['text'][:120]}")

    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=nhan)
    t0 = time.perf_counter()
    loi_he_thong = ""
    try:
        core.console_act({"kind": "say", "text": ca["nhap"]})
    except Exception as e:                                    # noqa: BLE001
        loi_he_thong = f"{type(e).__name__}: {e}"

    s0 = next((e.data for e in agent.ledger.read()
               if e.kind == "hook" and e.data.get("hook") == "UserPromptSubmit"), {})
    bao_cao = agent.last_report or {}
    return {
        "loi_tac_tu": "\n\n".join(loi_tac_tu),
        "the": the,
        "thong_bao": thong_bao,
        "s0": s0,
        "cong_cu_da_goi": [e.data["tool"] for e in agent.ledger.read() if e.kind == "tool_use"],
        "goi_mo_hinh": len([e for e in agent.ledger.read() if e.kind == "llm_call"]),
        "cho_nguoi": bool(bao_cao.get("awaiting_human")),
        "giay": round(time.perf_counter() - t0, 2),
        "token": bao_cao.get("cost", {}).get("tokens", {}),
        "so_lan_hoi": len([c for c in the if c.get("type") == "clarify"]),
        "loi_he_thong": loi_he_thong,
    }


# =========================================================================== chấm
def cham(ca: dict[str, Any], kq: dict[str, Any]) -> list[dict[str, Any]]:
    loi = kq["loi_tac_tu"].lower()
    ra: list[dict[str, Any]] = []

    def them(ten: str, dat: bool, vi: str) -> None:
        ra.append({"tieu_chi": ten, "dat": dat, "chi_tiet": vi})

    for k in ca.get("kiem", []):
        t = k["loai"]

        if t == "s0_decision":
            thuc = kq["s0"].get("decision", "?")
            them("S0 quyết định", thuc == k["gia_tri"], f"{thuc} (mong {k['gia_tri']})")

        elif t == "s0_rule":
            luat = [r["rule"] for r in kq["s0"].get("rules", [])]
            them("S0 luật nổ", k["gia_tri"] in luat, ", ".join(luat) or "không luật nào")

        elif t == "goi_mo_hinh":
            them("Số lần gọi mô hình", kq["goi_mo_hinh"] <= k["toi_da"],
                 f"{kq['goi_mo_hinh']} (tối đa {k['toi_da']})")

        elif t == "the_cong":
            g = [c.get("gate") for c in kq["the"]]
            them("Thẻ cổng", k["gia_tri"] in g, ", ".join(x for x in g if x) or "không thẻ nào")

        elif t == "phai_hoi":
            phu = [ten for ten, tu in k["chu_de"].items() if any(x in loi for x in tu)]
            them(f"Hỏi ≥ {k['toi_thieu']} chủ đề", len(phu) >= k["toi_thieu"],
                 f"{len(phu)}/{len(k['chu_de'])}: {', '.join(phu) or 'không chủ đề nào'}")

        elif t == "phai_noi":
            phu = [i for i, nhom in enumerate(k["cum"]) if any(x in loi for x in nhom)]
            thieu = [k["cum"][i][0] for i in range(len(k["cum"])) if i not in phu]
            them(f"Nói ≥ {k['toi_thieu']} ý", len(phu) >= k["toi_thieu"],
                 f"{len(phu)}/{len(k['cum'])}" + (f" · thiếu: {', '.join(thieu)}" if thieu else ""))

        elif t == "khong_duoc_noi":
            hit = [x for x in k["cum"] if x.lower() in loi]
            them("Không nói điều cấm", not hit, ", ".join(hit) or "sạch")

        elif t == "khong_goi":
            hit = [c for c in k["cong_cu"] if c in kq["cong_cu_da_goi"]]
            them("Không gọi công cụ cấm", not hit, ", ".join(hit) or "sạch")

        elif t == "co_so":
            so = SO_CO_DON_VI.findall(kq["loi_tac_tu"])
            them(f"Có ≥ {k['toi_thieu']} số có đơn vị", len(so) >= k["toi_thieu"],
                 f"{len(so)} số")

        elif t == "ket_thuc_cho":
            them("Kết thúc chờ người", kq["cho_nguoi"],
                 "đang chờ" if kq["cho_nguoi"] else "không chờ ai")

        else:
            them(t, False, "loại kiểm không nhận ra — tiêu chí hỏng")

    if kq["loi_he_thong"]:
        them("Không lỗi hệ thống", False, kq["loi_he_thong"])
    return ra


# =========================================================================== chạy bộ
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chạy bộ ca đo qua HumanAct, headless")
    ap.add_argument("--bo", default="tests/kich_ban/tc001_007.yaml")
    ap.add_argument("--ca", help="Chỉ chạy một ca, ví dụ TC004")
    ap.add_argument("--lan", type=int, default=5, help="Số lần chạy mỗi ca (mặc định 5)")
    ap.add_argument("--chi-tiet", action="store_true", help="In toàn bộ lời tác tử")
    ap.add_argument("--ghi", help="Thư mục ghi lại phản hồi mô hình để phát lại")
    ap.add_argument("--ra", default="ket-qua-do", help="Thư mục kết quả")
    a = ap.parse_args(argv)

    load_dotenv()
    bo = yaml.safe_load(pathlib.Path(a.bo).read_text("utf-8"))
    ds = [c for c in bo["ca"] if not a.ca or c["ma"] == a.ca.upper()]
    if not ds:
        print(f"Không có ca nào tên {a.ca}", file=sys.stderr)
        return 2

    ra_dir = pathlib.Path(a.ra)
    ra_dir.mkdir(parents=True, exist_ok=True)
    ghi = pathlib.Path(a.ghi) if a.ghi else None
    tong: list[dict[str, Any]] = []

    for ca in ds:
        print(f"\n{'═' * 96}\n{ca['ma']} · {ca['ten']}  ({ca['uu_tien']}, {ca['loai']})")
        print(f"  Nhập: {ca['nhap']}")
        if ca.get("ngoai_pham_vi_g1"):
            print(f"  ⚑ Ngoài phạm vi G1: {' '.join(ca['ngoai_pham_vi_g1'].split())[:150]}")
        print("─" * 96)

        lan_kq = []
        for i in range(1, a.lan + 1):
            import tempfile
            tm = pathlib.Path(tempfile.mkdtemp()) / f"{ca['ma'].lower()}-lan{i}"
            tm.mkdir(parents=True)
            if a.chi_tiet:
                print(f"\n── lần {i} " + "─" * 80)
            kq = chay_mot_lan(ca, tm, ghi=ghi, chi_tiet=a.chi_tiet)
            diem = cham(ca, kq)
            dat = all(d["dat"] for d in diem)
            lan_kq.append({"lan": i, "dat": dat, "diem": diem, **{
                k: kq[k] for k in ("giay", "token", "goi_mo_hinh", "so_lan_hoi",
                                   "cong_cu_da_goi", "loi_he_thong")}})
            bieu = "✓" if dat else "✗"
            chua = [d for d in diem if not d["dat"]]
            print(f"  lần {i}: {bieu}  {kq['giay']:5.1f}s · {kq['goi_mo_hinh']} lượt mô hình · "
                  f"{kq['token'].get('in', 0) + kq['token'].get('out', 0)} token · "
                  f"{kq['so_lan_hoi']} lần hỏi"
                  + ("" if dat else "  ← " + "; ".join(
                      f"{d['tieu_chi']}: {d['chi_tiet']}" for d in chua)[:120]))

        so_dat = sum(1 for x in lan_kq if x["dat"])
        ty_le = so_dat / len(lan_kq)
        trang_thai = ("Đạt" if ty_le == 1 else
                      "Không ổn định" if so_dat else
                      ("Chưa đủ năng lực ở G1" if ca.get("ngoai_pham_vi_g1") else "Không đạt"))
        print(f"  → {trang_thai} · {so_dat}/{len(lan_kq)} lần")
        if ty_le == 1:
            print(f"    Cơ chế bảo vệ: {' '.join(ca['co_che'].split())}")

        tong.append({"ma": ca["ma"], "uc": ca["uc"], "ten": ca["ten"], "uu_tien": ca["uu_tien"],
                     "trang_thai": trang_thai, "so_dat": so_dat, "so_lan": len(lan_kq),
                     "ty_le": ty_le, "co_che": " ".join(ca["co_che"].split()),
                     "ngoai_pham_vi_g1": bool(ca.get("ngoai_pham_vi_g1")),
                     "lan": lan_kq})

    _in_tong_ket(tong)
    stamp = date.today().isoformat()
    (ra_dir / f"ket-qua-{stamp}.json").write_text(
        json.dumps(tong, ensure_ascii=False, indent=1), "utf-8")
    (ra_dir / f"ket-qua-{stamp}.md").write_text(_bang_md(tong, stamp), "utf-8")
    print(f"\nĐã ghi: {ra_dir}/ket-qua-{stamp}.json và .md")
    return 0 if all(t["ty_le"] == 1 or t["ngoai_pham_vi_g1"] for t in tong) else 1


def _in_tong_ket(tong: list[dict[str, Any]]) -> None:
    print(f"\n{'═' * 96}\nTỔNG KẾT\n{'═' * 96}")
    print(f"{'Ca':8s} {'Ưu tiên':8s} {'Trạng thái':22s} {'Tỉ lệ':8s} Tên")
    for t in tong:
        print(f"{t['ma']:8s} {t['uu_tien']:8s} {t['trang_thai']:22s} "
              f"{t['so_dat']}/{t['so_lan']:<6d} {t['ten'][:44]}")
    trong = [t for t in tong if not t["ngoai_pham_vi_g1"]]
    dat = sum(1 for t in trong if t["ty_le"] == 1)
    print(f"\nTrong phạm vi G1: {dat}/{len(trong)} đạt"
          + (f" · {len(tong) - len(trong)} ca cần bước sau" if len(trong) != len(tong) else ""))


def _bang_md(tong: list[dict[str, Any]], stamp: str) -> str:
    L = [f"# Kết quả đo bước G1 — {stamp}", "",
         "Chạy qua HumanAct (headless), mỗi ca nhiều lần, chấm theo lần chạy đầy đủ.",
         "Tiêu chí nằm trong `tests/kich_ban/tc001_007.yaml` — không sửa tiêu chí để ép đạt (N6).",
         "",
         "| Mã | UC | Ưu tiên | Trạng thái | Tỉ lệ | Cơ chế thiết kế bảo vệ ca này |",
         "|---|---|---|---|---|---|"]
    for t in tong:
        L.append(f"| {t['ma']} | {t['uc']} | {t['uu_tien']} | {t['trang_thai']} | "
                 f"{t['so_dat']}/{t['so_lan']} | {t['co_che'] if t['ty_le'] == 1 else '—'} |")
    L += ["", "## Chi tiết từng lần chạy", ""]
    for t in tong:
        L.append(f"### {t['ma']} · {t['ten']}")
        for l in t["lan"]:
            L.append(f"- **lần {l['lan']}** — {'ĐẠT' if l['dat'] else 'KHÔNG ĐẠT'} · "
                     f"{l['giay']}s · {l['goi_mo_hinh']} lượt mô hình · "
                     f"{l['token'].get('in', 0) + l['token'].get('out', 0)} token")
            for d in l["diem"]:
                L.append(f"    - {'✓' if d['dat'] else '✗'} {d['tieu_chi']}: {d['chi_tiet']}")
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
