#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bốn chỉ số của EIDE-EDIT-47 §7, đo từ SỔ CÁI của các dự án thật.

    python tools/do_edit47.py            # bảng cho người đọc
    python tools/do_edit47.py --json     # cho máy, và cho `bao_cao_tong.py`

| Chỉ số | Đo bằng gì |
|---|---|
| 1 · Loại hiện vật sửa được qua giao diện | `dem_sua_duoc.py` — gọi lại, không đếm lần hai |
| 2 · Lượt người GÕ LỜI cho việc lẽ ra bấm được | `human_act kind=say` có từ khoá sửa/đổi/lùi + nhắc một hiện vật mà loại của nó NAY sửa được |
| 3 · Thời gian sửa → hạ nguồn cập nhật | từ changeset của người có `stale` tới changeset của tác tử đầu tiên chạm đúng hiện vật ấy |
| 4 · Hoàn tác thành công / thất bại, theo tầng | sự kiện sổ cái `undo` (DEV-372); sổ cũ không có nó thì nói ra là KHÔNG ĐO ĐƯỢC |

**Ba điều tệp này cố ý làm, vì không làm thì con số đẹp hơn mà sai.**

1. **Chỉ số 1 không đếm lại.** Nó gọi `dem_sua_duoc.main()`. Hai cách đếm cùng một thứ sẽ
   lệch, và lúc lệch thì không ai biết cái nào đúng.

2. **Chỉ số 2 chia bốn rổ, không gộp thành một số.** "Có từ khoá *sửa*" không đồng nghĩa
   "lẽ ra bấm được": phần lớn câu trong kho mẫu là *"sửa mã nguồn giúp tôi"* — việc của
   tác tử, không phải một ô để bấm. Và 217 trong 249 câu khớp từ khoá là **báo cáo dài của
   một tác tử đóng vai sinh viên**, không phải lời người gõ. Gộp cả bốn rổ lại là tự cho
   mình một mẫu số dễ.

3. **Chỉ số 4 phân biệt "0 lần" với "không ghi lại".** Sổ cái trước DEV-372 không có loại
   sự kiện `undo`, nên mọi phiên cũ đều trả về rỗng — và một bảng viết `0/0` ở đó sẽ đọc
   như *"chưa ai hoàn tác"* trong khi sự thật là *"đã hoàn tác mà không ai ghi lại"*. Đây
   đúng cái bẫy mà DEV-372 sinh ra để vá, nên bộ đo của nó không được rơi vào lại.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sqlite3
import statistics
import sys
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

# Từ khoá của §7: câu người gõ đang YÊU CẦU MỘT THAY ĐỔI, chứ không hỏi hay kể.
TU_KHOA = ("sửa", "đổi", "lùi", "về bản", "hoàn tác", "bỏ đi", "đặt lại")

# Mã hiện vật trong một câu tiếng Việt tự do. Hai dạng: `FR-01`/`ADR-02`/`PT-3` và
# `criteria:sim-01`/`build:firmware`.
MA_HIEN_VAT = re.compile(r"\b([A-Z]{2,5}-\d{1,3}|[a-z_]{3,14}:[A-Za-z0-9_.\-]{1,30})\b")


def _ngay(ts: str) -> str:
    return (ts or "")[:10]


def _doc_so(p: pathlib.Path) -> list[dict]:
    ra = []
    for line in p.read_text("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            ra.append(json.loads(line))
        except ValueError:
            continue
    return ra


def _loai_cua_hien_vat(db: pathlib.Path) -> dict[str, str]:
    """`{mã hiện vật: loại}` của một kho.

    **Ném lỗi ra ngoài, không trả về rỗng.** Bản đầu bọc cả hàm trong `except
    sqlite3.Error: return {}`, và nó viết sai tên cột (`artefact_id` — cột thật tên `id`).
    Hậu quả: mọi dự án trả về `{}`, nên chỉ số 2 ra **0 lượt** cho cả 39 dự án và con số
    ấy trông hoàn toàn hợp lý. Một phép lọc sai trả về rỗng thì rẻ; trả về một con số đẹp
    thì tốn nhiều lượt mới phát hiện.
    """
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {a: t for a, t in c.execute(
            "SELECT id, type FROM artefacts WHERE deleted=0")}
    finally:
        c.close()


# ============================================================== chỉ số 2
# Một câu người gõ để nhờ sửa một ô thì NGẮN. Mọi câu dài hơn ngần này trong kho mẫu đều
# là báo cáo của một tác tử ĐÓNG VAI sinh viên (`tools/phien_sinhvien_*.py`) — nó dài vài
# nghìn ký tự, có bảng, có mã, và tình cờ chứa chữ "sửa".
#
# Đọc 249 câu khớp từ khoá thì 217 câu thuộc loại ấy. Không tách ra thì chỉ số này đếm
# **lời của máy** rồi gọi đó là "người gõ lời" — và con số nghe vẫn hợp lý.
TRAN_CAU_NGUOI = 300


def _goi_loi_le_ra_bam_duoc(so: list[dict], loai: dict[str, str],
                            sua_duoc: set[str]) -> dict[str, list]:
    """Bốn rổ, không gộp thành một số.

    Gộp là chỗ chỉ số này dễ nói sai nhất: "có từ khoá *sửa*" không đồng nghĩa "lẽ ra bấm
    được". Phần lớn câu trong kho mẫu là *"sửa mã nguồn giúp tôi"* — đó là **việc của tác
    tử**, không phải một ô người bấm. Chỉ khi câu ấy chỉ rõ một hiện vật mà loại của nó
    NAY mang `sua_duoc` thì mới nói được rằng lẽ ra họ bấm được.
    """
    ra: dict[str, list] = {"bam_duoc": [], "chua_bam_duoc": [], "khong_ro": [],
                           "bao_cao_dai": []}
    for e in so:
        if e.get("kind") != "human_act":
            continue
        d = e.get("data") or {}
        if d.get("kind") != "say":
            continue
        chu = str(d.get("text") or "")
        thap = chu.lower()
        if not any(k in thap for k in TU_KHOA):
            continue
        gi = {"ts": e.get("ts", ""), "chu": chu[:120], "dai": len(chu)}
        if len(chu) > TRAN_CAU_NGUOI:
            ra["bao_cao_dai"].append(gi)
            continue
        ma = [m for m in MA_HIEN_VAT.findall(chu) if m in loai]
        gi["ma"] = ma
        if not ma:
            ra["khong_ro"].append(gi)
        elif any(loai[m] in sua_duoc for m in ma):
            ra["bam_duoc"].append(gi)
        else:
            ra["chua_bam_duoc"].append(gi)
    return ra


# ============================================================== chỉ số 3
def _sua_den_ha_nguon(so: list[dict]) -> dict[str, object]:
    """Từ một changeset CỦA NGƯỜI có đánh dấu hạ nguồn STALE, tới changeset đầu tiên của
    TÁC TỬ chạm đúng hiện vật ấy. Không bao giờ chạm thì đếm riêng — đó là con số đáng
    đọc nhất ở đây."""
    cs = [e for e in so if e.get("kind") == "changeset"]
    giay: list[float] = []
    chua: list[dict] = []
    for i, e in enumerate(cs):
        d = e.get("data") or {}
        if d.get("author") != "human" or not (d.get("stale") or []):
            continue
        can = set(d["stale"])
        t0 = _gio(e.get("ts", ""))
        thay = None
        for sau in cs[i + 1:]:
            ds = sau.get("data") or {}
            if str(ds.get("author", "")).startswith("agent") and can & set(ds.get("touches") or []):
                thay = sau
                break
        if thay is None:
            chua.append({"cs": d.get("id"), "stale": sorted(can)[:4],
                         "ts": e.get("ts", "")})
        elif t0 is not None:
            t1 = _gio(thay.get("ts", ""))
            if t1 is not None and t1 >= t0:
                giay.append(t1 - t0)
    return {"so_lan_co_so": len(giay),
            "trung_vi_giay": round(statistics.median(giay), 1) if giay else None,
            "nhanh_nhat_giay": round(min(giay), 1) if giay else None,
            "cham_nhat_giay": round(max(giay), 1) if giay else None,
            "khong_bao_gio_cham": chua}


def _gio(ts: str) -> float | None:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return None


# ============================================================== chỉ số 4
# Bốn tầng có `target.type` riêng, lấy từ bảng trong docstring của `loop._nguoi_hoan_tac`.
#
# "Năm tầng lùi" của DEV-365 đếm cả **mốc ngầm trước lần sửa đầu của người** — nó là một
# `checkpoint` và không có nút riêng: người về nó bằng chính `snapshot` hoặc `session`. Nên
# ở đây chỉ có bốn tên, và danh sách này phải khớp bảng ấy chứ không được tự thêm một tên
# nghe hợp lý (bản đầu có `artefact` — một tầng KHÔNG tồn tại trong mã).
TANG = ("changeset", "session", "run", "snapshot")


def _hoan_tac_theo_tang(so: list[dict]) -> dict[str, object]:
    co_ghi = [e for e in so if e.get("kind") == "undo"]
    y_chi = [e for e in so
             if e.get("kind") == "human_act" and (e.get("data") or {}).get("kind") == "undo"]
    theo: dict[str, dict[str, int]] = {}
    for e in co_ghi:
        d = e.get("data") or {}
        t = str(d.get("tang") or "changeset")
        o = theo.setdefault(t, {"ok": 0, "hong": 0})
        o["ok" if d.get("ok") else "hong"] += 1
    return {
        # Ý CHÍ (có trong mọi sổ, kể cả sổ cũ) và KẾT QUẢ (chỉ có từ DEV-372) là hai con
        # số khác nhau. Để riêng, vì hiệu của chúng chính là phần KHÔNG ĐO ĐƯỢC.
        "so_lan_nguoi_bam": len(y_chi),
        "so_lan_co_ghi_ket_qua": len(co_ghi),
        "theo_tang": theo,
    }


# ============================================================== gộp
def do(goc: pathlib.Path) -> dict[str, object]:
    import dem_sua_duoc as dsd

    du_an = sorted(p.parent.parent for p in goc.glob("*/.eide/ledger.jsonl"))

    # Chỉ số 1: gọi lại chính bộ đo của nó, không đếm lần hai.
    from io import StringIO

    cu, sys.stdout = sys.stdout, StringIO()
    try:
        dsd.main(["--du-lieu", str(goc), "--json"])
        c1 = json.loads(sys.stdout.getvalue())
    finally:
        sys.stdout = cu
    sua_duoc = set(c1["sua_duoc"]) | set(c1["khai_ma_kho_chua_co"])

    goi: dict[str, list] = {"bam_duoc": [], "chua_bam_duoc": [], "khong_ro": [],
                            "bao_cao_dai": []}
    ha_nguon = {"so_lan_co_so": 0, "giay": [], "khong_bao_gio_cham": []}
    ht = {"so_lan_nguoi_bam": 0, "so_lan_co_ghi_ket_qua": 0,
          "theo_tang": collections.defaultdict(lambda: {"ok": 0, "hong": 0})}
    theo_du_an = []
    for d in du_an:
        so = _doc_so(d / ".eide" / "ledger.jsonl")
        loai = _loai_cua_hien_vat(d / ".eide" / "store.sqlite")
        g = _goi_loi_le_ra_bam_duoc(so, loai, sua_duoc)
        h = _sua_den_ha_nguon(so)
        u = _hoan_tac_theo_tang(so)
        for k in goi:
            goi[k] += [{**x, "du_an": d.name} for x in g[k]]
        ha_nguon["khong_bao_gio_cham"] += [{**x, "du_an": d.name}
                                          for x in h["khong_bao_gio_cham"]]
        ha_nguon["so_lan_co_so"] += h["so_lan_co_so"]
        if h["trung_vi_giay"] is not None:
            ha_nguon["giay"].append(h["trung_vi_giay"])
        ht["so_lan_nguoi_bam"] += u["so_lan_nguoi_bam"]
        ht["so_lan_co_ghi_ket_qua"] += u["so_lan_co_ghi_ket_qua"]
        for t, o in u["theo_tang"].items():
            ht["theo_tang"][t]["ok"] += o["ok"]
            ht["theo_tang"][t]["hong"] += o["hong"]
        theo_du_an.append({
            "du_an": d.name, "ban_ghi": len(so),
            "goi_loi": len(g["bam_duoc"]), "hoan_tac": u["so_lan_nguoi_bam"],
            "ngay_cuoi": _ngay(so[-1]["ts"]) if so else ""})

    return {
        "so_du_an": len(du_an),
        "chi_so_1_sua_duoc": {"ty_le": c1["ty_le"], "loai": c1["sua_duoc"]},
        "chi_so_2_go_loi": {
            "cau_co_tu_khoa": sum(len(v) for v in goi.values()),
            "bao_cao_dai_cua_may": len(goi["bao_cao_dai"]),
            "cau_ngan_co_the_la_nguoi_go": (len(goi["bam_duoc"])
                                            + len(goi["chua_bam_duoc"])
                                            + len(goi["khong_ro"])),
            "le_ra_bam_duoc": len(goi["bam_duoc"]),
            "hien_vat_chua_sua_duoc": len(goi["chua_bam_duoc"]),
            "khong_chi_ro_hien_vat": len(goi["khong_ro"]),
            "vi_du": (goi["bam_duoc"] + goi["chua_bam_duoc"])[:8],
            "gioi_han": ("Mọi câu trong kho mẫu đều do KỊCH BẢN gõ, không phải người ngồi "
                         "gõ — nên con số này là mốc “trước”, và chỉ phiên có người thật "
                         "ngồi trước giao diện mới cho con số “sau”."),
        },
        "chi_so_3_ha_nguon": {
            "so_lan_do_duoc": ha_nguon["so_lan_co_so"],
            "trung_vi_giay": (round(statistics.median(ha_nguon["giay"]), 1)
                              if ha_nguon["giay"] else None),
            "so_lan_khong_bao_gio_cham": len(ha_nguon["khong_bao_gio_cham"]),
            "vi_du_khong_cham": ha_nguon["khong_bao_gio_cham"][:8],
        },
        "chi_so_4_hoan_tac": {
            "so_lan_nguoi_bam": ht["so_lan_nguoi_bam"],
            "so_lan_co_ghi_ket_qua": ht["so_lan_co_ghi_ket_qua"],
            "khong_do_duoc": ht["so_lan_nguoi_bam"] - ht["so_lan_co_ghi_ket_qua"],
            "theo_tang": {t: dict(o) for t, o in sorted(ht["theo_tang"].items())},
            "tang_chua_thay": [t for t in TANG if t not in ht["theo_tang"]],
        },
        "theo_du_an": theo_du_an,
    }


def _in(kq: dict) -> None:
    c2 = kq["chi_so_2_go_loi"]
    c3 = kq["chi_so_3_ha_nguon"]
    c4 = kq["chi_so_4_hoan_tac"]
    print(f"Sổ cái của {kq['so_du_an']} dự án thật\n")
    print(f"  1 · Loại hiện vật sửa được qua giao diện: "
          f"{XANH}{kq['chi_so_1_sua_duoc']['ty_le']}{HET}")
    print(f"  2 · Lượt người GÕ LỜI cho việc lẽ ra bấm được: "
          f"{VANG}{c2['le_ra_bam_duoc']}{HET}")
    print(f"        {XAM}{c2['cau_co_tu_khoa']} câu khớp từ khoá, trong đó "
          f"{c2['bao_cao_dai_cua_may']} là báo cáo DÀI của tác tử đóng vai sinh viên "
          f"(> {TRAN_CAU_NGUOI} ký tự){HET}")
    print(f"        {XAM}{c2['cau_ngan_co_the_la_nguoi_go']} câu ngắn còn lại: "
          f"{c2['le_ra_bam_duoc']} nhắc hiện vật NAY sửa được · "
          f"{c2['hien_vat_chua_sua_duoc']} nhắc hiện vật chưa sửa được · "
          f"{c2['khong_chi_ro_hien_vat']} không chỉ rõ hiện vật nào (phần lớn là “sửa mã "
          f"nguồn giúp tôi” — việc của tác tử, không phải một ô để bấm){HET}")
    tv = c3["trung_vi_giay"]
    print(f"  3 · Sửa → hạ nguồn cập nhật: đo được {c3['so_lan_do_duoc']} lần"
          + (f", trung vị {tv/60:.1f} phút" if tv else "")
          + f"  {DO}· KHÔNG BAO GIỜ chạm: {c3['so_lan_khong_bao_gio_cham']}{HET}")
    print(f"  4 · Hoàn tác: người bấm {c4['so_lan_nguoi_bam']} lần, "
          f"có ghi kết quả {c4['so_lan_co_ghi_ket_qua']} lần"
          + (f"  {DO}· {c4['khong_do_duoc']} lần KHÔNG ĐO ĐƯỢC (sổ cũ, "
             f"trước DEV-372){HET}" if c4["khong_do_duoc"] else ""))
    for t, o in c4["theo_tang"].items():
        tong = o["ok"] + o["hong"]
        print(f"        {t:10} {o['ok']}/{tong} ok")
    if c4["tang_chua_thay"]:
        print(f"      {XAM}tầng chưa có bản ghi nào: "
              f"{', '.join(c4['tang_chua_thay'])}{HET}")
    if c2["vi_du"]:
        print("\n  Ví dụ câu lẽ ra bấm được:")
        for v in c2["vi_du"]:
            print(f"    {XAM}{v['du_an']:22}{HET} {v['chu'][:84]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Bốn chỉ số EIDE-EDIT-47 §7")
    ap.add_argument("--du-lieu", default="du-lieu")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    goc = pathlib.Path(a.du_lieu)
    if not goc.is_absolute():
        goc = REPO / goc
    kq = do(goc)
    if a.json:
        print(json.dumps(kq, ensure_ascii=False, indent=1))
    else:
        _in(kq)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
