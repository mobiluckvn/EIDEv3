#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lái một phiên GIAO VIỆC cho Agent qua GIAO DIỆN THẬT, có ghi nhật ký.

    python tools/lai_phien_qua_gui.py mo                # mở app, mở dự án, chụp trạng thái
    python tools/lai_phien_qua_gui.py go "câu nói"      # gõ một câu như người thật
    python tools/lai_phien_qua_gui.py chup [tab]        # chụp trạng thái một tab
    python tools/lai_phien_qua_gui.py anh <nhan>        # app tự vẽ ảnh PNG cửa sổ của nó
    python tools/lai_phien_qua_gui.py cong <id> ok|no   # quyết một cửa duyệt
    python tools/lai_phien_qua_gui.py kho               # liệt kê hiện vật trong kho

Khác `thu_giao_dien.py` ở mục đích: bộ kia **kiểm** giao diện bằng một kịch bản cố định, bộ này
**lái một phiên làm việc thật** — người đọc kết quả rồi quyết câu tiếp theo, và mỗi lượt được
ghi vào nhật ký của dự án.

Dùng lần đầu ngày 11/10/2026 cho phiên game Flappy Bird (README §7.4). Đổi `DU_AN` ở dưới để
lái một dự án khác.

## Hai chỗ đã trả giá, đừng lặp lại

**Đợi theo SỔ CÁI, không theo sự kiện giao diện.** Một lượt Agent có những đoạn dài không sinh
sự kiện giao diện nào (đang đợi mô hình, hay tác tử con đang chạy). Lúc ấy app bận và không trả
`anh_chup`, nên bộ lái báo "app có đang chạy không?" trong khi app chạy bình thường.

**App phải MỞ SẴN dự án thì kênh mới bật.** Kênh `.eide/ui-test/` chỉ bật cho dự án app đang
mở, nên trước lần chạy đầu phải đặt `defaults write vn.mobiluck.eide duAnPath -string <đường>`
rồi mới mở app — không thì `san_sang()` treo tới hết giờ.

Mỗi lần gõ, bộ lái ghi vào `du-lieu/game-flappy/NHAT-KY-GIAO-VIEC.md`: câu tôi gõ, Agent trả
lời gì, nó gọi công cụ nào, hiện vật nào vào kho, và tab nào có gì. Nhật ký là thứ đọc lại
được sau khi phiên đóng — không có nó thì "Agent đã làm xong" chỉ là một câu tôi kể lại.

Không gõ phím qua hệ điều hành và không `screencapture`: kênh `.eide/ui-test/` thay NGÓN TAY
người, mọi thứ vẫn đi qua `AppState.gui(_:)` → `console.act`, đúng một cửa vào lõi (I1).
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path("/Users/congvt/Documents/EIDE_v3")
DU_AN = REPO / "du-lieu/game-flappy"
NHAT_KY = DU_AN / "NHAT-KY-GIAO-VIEC.md"
ANH = DU_AN / "anh-giao-dien"

sys.path.insert(0, str(REPO / "tools"))
from thu_giao_dien import GiaoDien  # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


def _gd(xoa: bool = False) -> GiaoDien:
    return GiaoDien(DU_AN, xoa=xoa)


def _ghi(phan: str) -> None:
    NHAT_KY.parent.mkdir(parents=True, exist_ok=True)
    if not NHAT_KY.exists():
        NHAT_KY.write_text(
            "# Nhật ký giao việc — game Flappy Bird + nhân RTOS\n\n"
            "> Phiên lái qua **giao diện thật** của EIDE (kênh `.eide/ui-test/`, thay ngón tay\n"
            "> người — mọi thứ vẫn đi qua `console.act`). Mỗi mục dưới đây là một lượt: câu\n"
            "> người gõ, Agent trả lời gì, gọi công cụ nào, ghi hiện vật nào.\n", "utf-8")
    with NHAT_KY.open("a", encoding="utf-8") as f:
        f.write(phan)


def _tom_tat(a: dict) -> str:
    """Rút gọn ảnh chụp giao diện thành thứ đọc được."""
    tt = a.get("trang_thai") or {}
    d = [f"- **thanh trạng thái**: dự án `{tt.get('du_an')}` · chip {tt.get('chip')} · "
         f"mô hình `{tt.get('mo_hinh')}`" + (f" · {tt.get('ngu_canh')}" if tt.get("ngu_canh")
                                             else "")]
    kh = a.get("khoi_tren_tab") or []
    if kh:
        d.append(f"- **tab `{a.get('tab')}`**: {len(kh)} khối — "
                 + ", ".join(f"`{k.get('code')}`/{k.get('type')}" for k in kh[:14]))
    tr = a.get("transcript") or a.get("dong_transcript") or []
    if isinstance(tr, list) and tr:
        d.append(f"- **transcript**: {len(tr)} dòng")
    if a.get("the_cong"):
        d.append(f"- **CỬA DUYỆT đang chờ**: {a['the_cong']}")
    return "\n".join(d)


def _kho() -> list[tuple[str, str, bool]]:
    import sqlite3
    p = DU_AN / ".eide" / "store.sqlite"
    if not p.is_file():
        return []
    cx = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        cot = [c[1] for c in cx.execute("pragma table_info(artefacts)")]
        if not cot:
            return []
        ten_stale = "stale" if "stale" in cot else None
        q = "select id, type" + (", stale" if ten_stale else "") + " from artefacts order by id"
        return [(r[0], r[1], bool(r[2]) if ten_stale else False) for r in cx.execute(q)]
    except Exception:
        return []
    finally:
        cx.close()


def _in_kho() -> str:
    ds = _kho()
    if not ds:
        return "_(kho chưa có hiện vật nào)_"
    theo: dict[str, list[str]] = {}
    for ma, loai, stale in ds:
        theo.setdefault(loai, []).append(ma + (" ⚠STALE" if stale else ""))
    return "\n".join(f"- `{k}` ({len(v)}): " + ", ".join(f"`{x}`" for x in v)
                     for k, v in sorted(theo.items()))


# =========================================================================== lệnh
def mo() -> int:
    DU_AN.mkdir(parents=True, exist_ok=True)
    g = GiaoDien(DU_AN, xoa=True)
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1.0)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang(40)
    print(f"{XANH}Kênh giao diện đã mở{HET}")
    o = g.mo_gan_day(DU_AN)
    print(f"mở dự án: {o.get('su_kien')}")
    a = g.chup("ban-dau")
    print(_tom_tat(a))
    _ghi(f"\n---\n\n## Mở phiên — {time.strftime('%d/%m/%Y %H:%M')}\n\n"
         f"Dự án `{DU_AN.name}`, tài liệu đã đặt sẵn: `de-bai.md`, "
         f"`bo-stm32f469-kien-truc.md`.\n\n{_tom_tat(a)}\n")
    return 0


SO_CAI = DU_AN / ".eide" / "ledger.jsonl"


def _so_dong_so_cai() -> int:
    try:
        with SO_CAI.open("rb") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _doc_so_cai(tu_dong: int) -> list[dict]:
    if not SO_CAI.is_file():
        return []
    ds = []
    with SO_CAI.open(encoding="utf-8", errors="replace") as f:
        for i, l in enumerate(f):
            if i >= tu_dong and l.strip():
                try:
                    ds.append(json.loads(l))
                except Exception:
                    pass
    return ds


def _doi_agent_xong(tu_dong: int, tran: float = 600) -> tuple[list[dict], float]:
    """Đợi theo SỔ CÁI, không theo sự kiện giao diện.

    Bản trước đợi 12 s không có sự kiện giao diện rồi xin ảnh chụp — và nó hỏng vì một lượt
    Agent có những đoạn dài **không sinh sự kiện giao diện nào** (lúc đang đợi mô hình trả
    lời, hay lúc tác tử con chạy). Lúc ấy app đang bận và không trả `anh_chup`, nên bộ lái
    báo "app có đang chạy không?" trong khi app chạy bình thường.

    Sổ cái thì ghi MỌI thứ — mỗi lời gọi công cụ, mỗi lượt mô hình. Im 25 s trên sổ cái là
    Agent thật sự đã dừng.
    """
    t0 = cuoi = time.time()
    n = tu_dong
    while time.time() - cuoi < 45 and time.time() - t0 < tran:
        m = _so_dong_so_cai()
        if m > n:
            n, cuoi = m, time.time()
            print(f"{XAM}  …{m - tu_dong} bản ghi sổ cái{HET}", end="\r", flush=True)
        time.sleep(1.0)
    return _doc_so_cai(tu_dong), time.time() - t0


def _ke_lai(ds: list[dict]) -> str:
    """Kể lại một lượt từ sổ cái: công cụ nào, Agent nói gì, cửa duyệt nào."""
    d: list[str] = []
    cc = [x["data"]["tool"] for x in ds if x.get("kind") == "tool_use"]
    if cc:
        d.append("**Công cụ đã gọi** (" + str(len(cc)) + "): "
                 + ", ".join(f"`{x}`" for x in cc))
    llm = sum(1 for x in ds if x.get("kind") == "llm_call")
    cs = [x["data"].get("id", "") for x in ds if x.get("kind") == "changeset"]
    if llm or cs:
        d.append(f"**{llm} lượt mô hình** · **{len(cs)} changeset**")
    noi = []
    for x in ds:
        if x.get("kind") == "ui_command" and (x["data"].get("method") == "console.post"):
            p = x["data"].get("params") or {}
            t = p.get("text") or p.get("markdown") or ""
            if t.strip() and not t.startswith("[Bạn]"):
                noi.append(t)
    for x in ds:
        if x.get("kind") == "say":
            t = (x["data"] or {}).get("text") or ""
            if t.strip():
                noi.append(t)
    if noi:
        d.append("\n**Agent nói:**\n\n" + "\n\n".join(noi[-3:]))
    cong = [x["data"] for x in ds if x.get("kind") == "gate" or (
        x.get("kind") == "ui_command" and x["data"].get("method") == "gate.open")]
    if cong:
        d.append("\n**CỬA DUYỆT**: " + json.dumps(cong[-1], ensure_ascii=False)[:600])
    return "\n\n".join(d)


def go(cau: str) -> int:
    g = _gd()
    print(f"{VANG}▸ gõ:{HET} {cau[:160]}…\n")
    n0 = _so_dong_so_cai()
    g.go(cau)
    ds, giay = _doi_agent_xong(n0)
    ke = _ke_lai(ds)
    print(f"{XAM}({giay:.0f}s · {len(ds)} bản ghi sổ cái){HET}\n")
    print(ke[:5000])
    print(f"\n{XAM}kho:{HET}\n{_in_kho()}")
    _ghi(f"\n### ▸ Người gõ\n\n> {cau}\n\n**Agent** ({giay:.0f}s, "
         f"{len(ds)} bản ghi sổ cái)\n\n{ke}\n\n**Kho sau lượt này**\n\n{_in_kho()}\n")
    return 0


def chup(tab: str = "") -> int:
    g = _gd()
    # Xin lõi vẽ lại TRƯỚC khi chuyển tab: chuyển tab không làm lõi vẽ lại (`attend` là sự
    # chú ý, không phải yêu cầu), nên một phiên mới vừa mở chưa có khối nào cho tab ấy.
    g.ve_lai()
    if tab:
        g.mo_tab(tab)
        time.sleep(1.2)
    a = g.chup(tab or "chup")
    print(json.dumps(a.get("khoi_tren_tab") or [], ensure_ascii=False, indent=1)[:6000])
    print(_tom_tat(a))
    _ghi(f"\n### Ảnh chụp tab `{tab or a.get('tab')}`\n\n{_tom_tat(a)}\n\n"
         + "```json\n"
         + json.dumps(a.get("khoi_tren_tab") or [], ensure_ascii=False, indent=1)[:4000]
         + "\n```\n")
    return 0


def anh(nhan: str) -> int:
    g = _gd()
    ra = ANH / f"{nhan}.png"
    p = g.chup_man_hinh(ra, nhan)
    if p:
        print(f"{XANH}ảnh:{HET} {p} ({p.stat().st_size} byte)")
        _ghi(f"\n![{nhan}](anh-giao-dien/{nhan}.png)\n")
        return 0
    print(f"{DO}app không vẽ được ảnh{HET}")
    return 1


def cong(gate_id: str, quyet: str) -> int:
    g = _gd()
    g.quyet_cong(gate_id, quyet in ("ok", "duyet", "yes"))
    time.sleep(3)
    a = g.chup("sau-cong")
    print(_tom_tat(a))
    _ghi(f"\n### Cửa duyệt `{gate_id}` → **{quyet}**\n\n{_tom_tat(a)}\n")
    return 0


def kho() -> int:
    print(_in_kho())
    return 0


if __name__ == "__main__":
    lenh = sys.argv[1] if len(sys.argv) > 1 else "chup"
    arg = sys.argv[2:]
    sys.exit({"mo": lambda: mo(), "go": lambda: go(arg[0]),
              "chup": lambda: chup(arg[0] if arg else ""),
              "anh": lambda: anh(arg[0]), "cong": lambda: cong(arg[0], arg[1]),
              "kho": lambda: kho()}[lenh]())
