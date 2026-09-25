#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Theo dõi phiên làm việc thật — đọc sổ cái theo thời gian thực.

    python tools/theo_doi.py --du-an du-lieu/du-an-mau            # theo dõi sống
    python tools/theo_doi.py --du-an ... --tu-dau                  # đọc lại từ đầu
    python tools/theo_doi.py --du-an ... --tong-ket                # chỉ in bản tổng kết

Vì sao làm được việc này mà không phải gắn thêm thiết bị đo: §B6 đã đòi "mọi lời gọi mô
hình, tool, cổng, changeset trong sổ cái; export được", và §F3 đòi "Quan sát". Nên sổ
cái vốn đã là bản ghi đầy đủ của mọi thứ đã xảy ra — bộ theo dõi này chỉ dịch nó sang
tiếng người.

Bản tổng kết cuối phiên trả lời đúng hai câu: **cơ chế nào đã thật sự nổ** (không phải
"có trong mã", mà "đã chạy trong phiên này"), và **chỗ nào hỏng**.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from collections import Counter, defaultdict
from typing import Any

# Cơ chế thiết kế ↔ dấu vết của nó trong sổ cái. Đây là bảng biến "đã hiện thực" thành
# "đã chạy" — điều duy nhất đáng tin khi trả lời "làm được gì rồi".
CO_CHE = {
    "N5 · Hook S0 chặn trước phép đoán":       lambda t: t["s0_chan"] > 0,
    "N5 · Thẻ cổng phát ra":                   lambda t: t["cong_mo"] > 0,
    "N5 · Cổng được người quyết":              lambda t: t["cong_quyet"] > 0,
    "N4 · Hỏi một cụm (ask_user)":             lambda t: t["tool"]["ask_user"] > 0,
    "N3 · Kiểm kê xác định tiêm vào ngữ cảnh": lambda t: t["luot"] > 0,
    "N7 · REQ có trích lời người":             lambda t: t["tool"]["store.req_create"] > 0,
    "N8 · Công cụ ghi đòi lớp giải thích":     lambda t: t["ghi"] > 0,
    "N9 · Changeset sinh ra":                  lambda t: t["changeset"] > 0,
    "N9 · Người tự sửa hiện vật":              lambda t: t["nguoi_sua"] > 0,
    "N9 · Hoàn tác":                           lambda t: t["hoan_tac"] > 0,
    "N9 · Hạ nguồn bị đánh dấu STALE":         lambda t: t["stale"] > 0,
    "N1 · Tra Fact trước khi dùng số":         lambda t: t["tool"]["fact.query"] > 0,
    "Lỗi có hướng dẫn quay về mô hình":        lambda t: t["loi_tool"] > 0,
    "Hook Stop bắt thêm một vòng":             lambda t: t["stop_them_vong"] > 0,
    "Sandbox chặn ra ngoài dự án":             lambda t: t["ma_loi"]["E4002"] > 0,
    "Ngân sách lượt cắt đúng chỗ":             lambda t: t["ma_loi"]["E6002"] > 0,
}

MAU = {"human_act": "\033[94m", "gate": "\033[91m", "incident": "\033[91m",
       "llm_call": "\033[95m", "tool_use": "\033[96m", "tool_result": "\033[96m",
       "hook": "\033[93m", "changeset": "\033[92m", "turn.start": "\033[1m",
       "turn.end": "\033[1m"}
HET = "\033[0m"


def doc(p: pathlib.Path, tu: int = 0):
    if not p.exists():
        return
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                e = json.loads(line)
                if e["seq"] > tu:
                    yield e


def dong(e: dict[str, Any], mau: bool = True) -> str | None:
    """Một sự kiện → một dòng cho người đọc. None = không đáng hiện."""
    d, k = e["data"], e["kind"]
    gio = e["ts"][11:19]
    c = MAU.get(k, "") if mau else ""
    h = HET if mau else ""

    if k == "turn.start":
        return f"{c}┏━ {d.get('run_id')} · [{d.get('kind')}] {(d.get('text') or '')[:88]}{h}"
    if k == "turn.end":
        cost = d.get("cost", {})
        tok = cost.get("tokens", {})
        cho = " · ĐANG CHỜ NGƯỜI" if d.get("awaiting_human") else ""
        return (f"{c}┗━ {d.get('run_id')} · {d.get('tool_calls', 0)} công cụ · "
                f"{d.get('seconds', 0)}s · {tok.get('in', 0)}→{tok.get('out', 0)} token{cho}{h}")
    if k == "human_act":
        return f"  {c}◆ NGƯỜI [{d.get('kind')}] {_act(d)}{h}"
    if k == "hook":
        if d.get("hook") == "UserPromptSubmit":
            if d.get("decision") == "pass":
                return None
            luat = ", ".join(r["rule"] for r in d.get("rules", []))
            return (f"  {c}⊗ S0 → {d.get('decision').upper()} [{luat}] "
                    f"{d.get('elapsed_ms', 0)}ms{h}")
        if d.get("hook") == "policy":
            if d.get("action") == "allow":
                return None
            return (f"  {c}⊗ CẤP QUYỀN {d.get('tool')} → {d.get('action').upper()} "
                    f"({d.get('rule')}{', cổng ' + d['gate'] if d.get('gate') else ''}){h}")
        if d.get("hook") == "Stop" and d.get("another_round"):
            return f"  {c}⊗ HOOK STOP bắt thêm một vòng: {d.get('reason')}{h}"
        return None
    if k == "llm_call":
        u = d.get("usage", {})
        goi = (" → gọi " + ", ".join(d["tool_calls"])) if d.get("tool_calls") else " → trả lời"
        return (f"  {c}◇ MÔ HÌNH {u.get('in', 0)}→{u.get('out', 0)} token"
                f"{goi} · {d.get('elapsed_ms', 0)}ms{h}")
    if k == "tool_use":
        return f"  {c}▸ {d.get('tool')}({_args(d.get('args'))}){h}"
    if k == "tool_result":
        if d.get("ok"):
            return f"  {c}  ✓ {d.get('tool')} · {d.get('elapsed_ms', 0)}ms{h}"
        return f"  \033[91m  ✗ {d.get('tool')} → LỖI {d.get('code')}{h}"
    if k == "gate":
        return (f"  {c}▣ CỔNG {d.get('gate') or ''} [{d.get('gate_id')}] "
                f"{d.get('state', '').upper()}"
                + (f" · {d['note']}" if d.get("note") else "") + h)
    if k == "changeset":
        s = f"  {c}● CHANGESET {d.get('id')} bởi {d.get('author')}: {d.get('summary', '')[:60]}"
        if d.get("stale"):
            s += f" → STALE: {', '.join(d['stale'])}"
        if not d.get("reversible"):
            s += " · KHÔNG HOÀN TÁC ĐƯỢC"
        return s + h
    if k == "incident":
        return (f"  \033[91m⚠ SỰ CỐ {d.get('code', d.get('kind', ''))}: "
                f"{(d.get('message_vi') or d.get('why') or '')[:100]}{h}")
    if k == "ui_command":
        m = d.get("method")
        if m == "console.post":
            vt = d.get("params", {}).get("role")
            if vt == "agent":
                txt = (d["params"].get("text") or "").replace("\n", " ⏎ ")
                the = " [KÈM THẺ]" if d["params"].get("card") else ""
                return f"  \033[97m│ TÁC TỬ:{the} {txt[:150]}{h}"
        elif m == "notice":
            p = d.get("params", {})
            return f"  \033[93m│ THÔNG BÁO [{p.get('level')}] {(p.get('text') or '')[:110]}{h}"
        return None
    return None


def _act(d: dict) -> str:
    k = d.get("kind")
    if k == "say":
        return (d.get("text") or "")[:90]
    if k == "attend":
        return f"mở tab {d.get('origin', {}).get('surface')}"
    if k == "decide":
        dd = d.get("data", {})
        return f"{'DUYỆT' if dd.get('approved') else 'TỪ CHỐI'} cổng {dd.get('gate_id')}"
    if k == "edit":
        return f"sửa {d.get('target', {}).get('id')} — {d.get('note') or ''}"
    if k == "undo":
        return f"hoàn tác {d.get('target', {}).get('id')}"
    if k == "choose":
        return f"trả lời thẻ {d.get('data', {}).get('card_id')}"
    return json.dumps(d.get("data", {}), ensure_ascii=False)[:80]


def _args(a: Any, n: int = 70) -> str:
    if not isinstance(a, dict):
        return ""
    bo = {k: v for k, v in a.items() if k != "explain"}
    s = ", ".join(f"{k}={str(v)[:40]!r}" for k, v in bo.items())
    return s if len(s) <= n else s[:n] + "…"


# =========================================================================== tổng kết
def thong_ke(events: list[dict]) -> dict[str, Any]:
    t: dict[str, Any] = {
        "luot": 0, "s0_chan": 0, "cong_mo": 0, "cong_quyet": 0, "changeset": 0,
        "nguoi_sua": 0, "hoan_tac": 0, "stale": 0, "ghi": 0, "loi_tool": 0,
        "stop_them_vong": 0, "token_in": 0, "token_out": 0, "giay": 0.0,
        "tool": Counter(), "ma_loi": Counter(), "su_co": [], "s0_luat": Counter(),
        "humanact": Counter(), "cong": Counter(), "cho_nguoi": 0,
    }
    GHI = {"fs.write", "fs.edit", "store.req_create", "store.req_update", "memory.note"}
    for e in events:
        d, k = e["data"], e["kind"]
        if k == "turn.start":
            t["luot"] += 1
        elif k == "turn.end":
            t["giay"] += float(d.get("seconds", 0) or 0)
            if d.get("awaiting_human"):
                t["cho_nguoi"] += 1
        elif k == "human_act":
            t["humanact"][d.get("kind")] += 1
            if d.get("kind") == "edit":
                t["nguoi_sua"] += 1
            if d.get("kind") == "undo":
                t["hoan_tac"] += 1
        elif k == "hook":
            if d.get("hook") == "UserPromptSubmit":
                for r in d.get("rules", []):
                    t["s0_luat"][r["rule"]] += 1
                if d.get("blocked"):
                    t["s0_chan"] += 1
            elif d.get("hook") == "Stop" and d.get("another_round"):
                t["stop_them_vong"] += 1
        elif k == "llm_call":
            u = d.get("usage", {})
            t["token_in"] += u.get("in", 0)
            t["token_out"] += u.get("out", 0)
        elif k == "tool_use":
            t["tool"][d.get("tool")] += 1
            if d.get("tool") in GHI:
                t["ghi"] += 1
        elif k == "tool_result":
            if not d.get("ok"):
                t["loi_tool"] += 1
                t["ma_loi"][d.get("code")] += 1
        elif k == "gate":
            t["cong"][d.get("gate") or "?"] += 1
            if d.get("state") == "open":
                t["cong_mo"] += 1
            elif d.get("state") in ("approved", "rejected"):
                t["cong_quyet"] += 1
        elif k == "changeset":
            t["changeset"] += 1
            t["stale"] += len(d.get("stale") or [])
        elif k == "incident":
            t["su_co"].append(f"{d.get('code', d.get('kind', ''))}: "
                              f"{(d.get('message_vi') or d.get('why') or '')[:120]}")
    return t


def in_tong_ket(events: list[dict]) -> None:
    t = thong_ke(events)
    W = 92
    print("\n" + "═" * W)
    print("TỔNG KẾT PHIÊN")
    print("═" * W)
    print(f"{t['luot']} lượt · {t['giay']:.0f}s · {t['token_in']:,}→{t['token_out']:,} token "
          f"· {t['cho_nguoi']} lượt kết thúc bằng chờ người")

    if t["humanact"]:
        print("\nAnh đã làm gì:")
        for k, n in t["humanact"].most_common():
            print(f"  {k:10s} ×{n}")

    if t["tool"]:
        print("\nCông cụ tác tử đã gọi:")
        for k, n in t["tool"].most_common():
            print(f"  {k:22s} ×{n}")

    if t["s0_luat"]:
        print("\nLuật S0 đã nổ:")
        for k, n in t["s0_luat"].most_common():
            print(f"  {k:14s} ×{n}")

    if t["cong"]:
        print("\nCổng:")
        for k, n in t["cong"].most_common():
            print(f"  {k:10s} ×{n}")

    print("\n" + "─" * W)
    print("CƠ CHẾ ĐÃ THẬT SỰ CHẠY TRONG PHIÊN NÀY")
    print("─" * W)
    chay, chua = [], []
    for ten, kiem in CO_CHE.items():
        (chay if kiem(t) else chua).append(ten)
    for x in chay:
        print(f"  ✓ {x}")
    if chua:
        print("\n  Chưa chạm tới trong phiên này (không có nghĩa là hỏng):")
        for x in chua:
            print(f"  · {x}")

    if t["ma_loi"]:
        print("\n" + "─" * W)
        print("LỖI CÔNG CỤ (lỗi là dữ liệu — xem mô hình có đổi hướng được không)")
        print("─" * W)
        for k, n in t["ma_loi"].most_common():
            print(f"  {k} ×{n}")

    if t["su_co"]:
        print("\n" + "─" * W)
        print("SỰ CỐ — CẦN XEM LẠI")
        print("─" * W)
        for s in t["su_co"]:
            print(f"  ⚠ {s}")
    print("═" * W)


# =========================================================================== main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Theo dõi phiên làm việc qua sổ cái")
    ap.add_argument("--du-an", required=True)
    ap.add_argument("--tu-dau", action="store_true", help="Đọc lại từ sự kiện đầu tiên")
    ap.add_argument("--tong-ket", action="store_true", help="Chỉ in tổng kết rồi thoát")
    ap.add_argument("--khong-mau", action="store_true")
    a = ap.parse_args(argv)

    p = pathlib.Path(a.du_an) / ".eide" / "ledger.jsonl"
    mau = not a.khong_mau

    if a.tong_ket:
        in_tong_ket(list(doc(p)))
        return 0

    tat_ca = list(doc(p))
    moc = 0 if a.tu_dau else (tat_ca[-1]["seq"] if tat_ca else 0)
    if a.tu_dau:
        for e in tat_ca:
            s = dong(e, mau)
            if s:
                print(s, flush=True)
    print(f"\n{'─' * 92}\nĐang theo dõi {p} từ sự kiện #{moc}. Anh cứ thao tác trên app.\n"
          f"{'─' * 92}", flush=True)

    ds: list[dict] = list(tat_ca) if a.tu_dau else []
    try:
        while True:
            moi = list(doc(p, moc))
            for e in moi:
                ds.append(e)
                moc = e["seq"]
                s = dong(e, mau)
                if s:
                    print(s, flush=True)
            time.sleep(0.4)
    except KeyboardInterrupt:
        in_tong_ket(ds if a.tu_dau else list(doc(p)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
