#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Một phiên làm việc THẬT trong đó người **bấm** thay vì gõ — và hai chỉ số còn thiếu.

    EIDE_FEATURE_WATCHER=1 EIDE_FEATURE_SUA_LONG=1 EIDE_E2E_MO_HINH=1 \
        .venv/bin/python tools/phien_nguoi_bam.py

§7 của EIDE-EDIT-47 có bốn chỉ số. DEV-372 đo được cả bốn, nhưng hai cái trong đó chỉ có
con số **"trước"**:

* **chỉ số 2** — *lượt người gõ lời cho việc lẽ ra bấm được*: trong 39 kho mẫu, mọi câu đều
  do kịch bản gõ và chúng nói về việc viết mã, nên con số là 0 vì một lý do không liên quan;
* **chỉ số 3** — *thời gian sửa → hạ nguồn cập nhật*: 4 lần đo được (trung vị 41,8 phút) và
  **7 lần không ai cập nhật**, vì tới DEV-373 mới có nút để bấm.

Bộ này chạy đúng phiên ấy: một việc nhỏ nhưng THẬT, và mỗi lần người muốn một thay đổi thì
**bấm** — sửa ô trong bảng, bấm "Cập nhật hạ nguồn", bấm "Chấp nhận STALE" — thay vì gõ một
câu nhờ tác tử làm.

**Nói rõ giới hạn trước khi đọc số.** Người ở đây là một kịch bản đi qua kênh kiểm thử của
chính app (`.eide/ui-test/`), không phải anh Công ngồi trước màn hình. Thứ nó đo được là
*"đường đi của một cú bấm có dẫn tới việc không"*, chứ không phải *"người thật có chọn bấm
thay vì gõ không"* — câu thứ hai chỉ một phiên có người thật trả lời được. Đổi lại, mọi
thông điệp ở đây là **đúng thông điệp mà cái nút gửi**, lấy từ chính `hanh_dong` mà lõi
khai, nên nó không dựng ra một đường đi không tồn tại.

**Bộ này TỐN TIỀN mô hình** (ba lượt `gemini-3.8-flash`), nên nó nằm sau `EIDE_E2E_MO_HINH=1`
và không chạy trong `pytest -q`.
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
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien, PathsThu           # noqa: E402
from thu_nut_lui import _mo_app                            # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"


def _kho(du_an: pathlib.Path):
    from eide.store import Store

    return Store(PathsThu(du_an).store_db)


def _so(du_an: pathlib.Path, kind: str | None = None) -> list[dict]:
    p = du_an / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for l in p.read_text("utf-8", errors="replace").splitlines():
        if not l.strip():
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if kind is None or d.get("kind") == kind:
            ra.append(d)
    return ra


def _stale(du_an: pathlib.Path) -> list[str]:
    return [a["id"] for a in _kho(du_an).list(stale_only=True, limit=200)]


def _nut_cua_khoi_stale(g) -> dict:
    """Lấy ĐÚNG mô tả nút mà lõi khai trên khối A11.4 — không tự soạn thông điệp."""
    g.mo_tab("history")
    a = g.chup("a11-stale")
    k = {x["code"]: x for x in a["khoi_tren_tab"]}.get("A11.4", {})
    return {h.get("ma"): h for h in (k.get("hanh_dong") or [])}


def chay(du_an: pathlib.Path) -> int:
    b = Bo("phien_nguoi_bam")
    g = GiaoDien(du_an)
    _mo_app(g)
    print("Kênh kiểm thử giao diện đã mở\n")

    # ============================================================ 1 · một việc THẬT
    b.phan("1 · GIAO MỘT VIỆC THẬT (gõ — vì đây là việc KHÔNG có nút nào)")

    # Hạ mức tự chủ xuống A2 để tác tử ghi được tệp trong dự án mà không dựng cổng cho
    # từng lần ghi: phiên này đo đường đi của NÚT, không đo cổng (phần H đã đo cổng).
    g._gui({"kind": "set", "data": {"key": "autonomy", "value": "A2"},
            "origin": {"surface": "settings"}})
    time.sleep(1.5)

    g.go("Ghi một yêu cầu FR-01: firmware phải gửi được tệp qua UART ở tốc độ ≥ 1 MB/s. "
         "Rồi viết `firmware/uart.c` hiện thực nó — một hàm `uart_send` đơn giản, và KHAI "
         "rằng tệp ấy hiện thực FR-01.")
    a = g.doi_xong(240)
    kho = _kho(du_an)
    req = kho.get("FR-01")
    b.kiem("Tác tử ghi được yêu cầu FR-01", req is not None,
           json.dumps((req or {}).get("canonical", {}), ensure_ascii=False)[:120])
    ma = [x for x in kho.list("code", limit=50)]
    b.kiem("Và ghi được một tệp mã trong dự án", bool(ma),
           ", ".join(x["id"] for x in ma) or "không có")
    if req is None or not ma:
        print(f"{DO}Lượt đầu không dựng được dữ liệu — dừng, không đo tiếp trên nền sai.{HET}")
        return b.tong()

    # ============================================================ 2 · người SỬA bằng cách BẤM
    b.phan("2 · NGƯỜI ĐỔI NGƯỠNG — bằng cách BẤM VÀO Ô, không gõ một câu")

    g.mo_tab("requirements")
    a = g.chup("a2-truoc")
    kh = [k for k in a["khoi_tren_tab"] if k.get("sua_duoc_loai") == "req"]
    b.kiem("Lõi KHAI ô nào của yêu cầu sửa được (I8) — nên có cái để bấm", bool(kh),
           " · ".join(f"{k['code']}→{k.get('sua_duoc_duong')}" for k in kh) or "không khối nào")

    truoc_sua = time.time()
    # Đúng thông điệp `OSuaTheoDuong`/`FormEditor` gửi khi người sửa một ô trong bảng A2.1.
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
            "data": {"base_version": f"v{req['version']}",
                     "fields": {"criteria": "≥ 5 MB/s"},
                     "summary": "nâng ngưỡng FR-01 lên ≥ 5 MB/s",
                     "session_id": "es-nguoi-bam"},
            "note": "bo thật đo được 5 MB/s nên lấy luôn mức ấy",
            "origin": {"surface": "requirements", "block": "A2.1", "row": "FR-01"}})
    g.doi_xong()

    st = _stale(du_an)
    b.kiem("Sửa xong thì hạ nguồn sáng đèn cần xem lại", bool(st),
           ", ".join(st) or "không hiện vật nào")

    # ============================================================ 3 · bấm "Cập nhật hạ nguồn"
    b.phan("3 · BẤM “CẬP NHẬT HẠ NGUỒN” — một cú bấm thay cho một câu nhờ")

    hd = _nut_cua_khoi_stale(g)
    b.kiem("Lõi khai đủ hai cú bấm trên khối A11.4",
           {"cap_nhat_tat_ca", "chap_nhan"} <= set(hd),
           " · ".join(sorted(hd)) or "không khai nút nào")
    nut = hd.get("cap_nhat_tat_ca") or {}
    b.kiem("Và nó tự khai là TỐN TIỀN mô hình", nut.get("ton_token") is True,
           str(nut.get("ton_token")))

    if not nut:
        print(f"{DO}Không có nút để bấm — dừng.{HET}")
        return b.tong()

    # Gửi đúng thứ `NutHanhDong` gửi: `kind`/`text`/`data` lấy từ mô tả của lõi.
    g._gui({"kind": nut.get("kind", "say"),
            "text": "Cập nhật những hiện vật đang lỗi thời.",
            "data": {"nut": "cap_nhat_ha_nguon"},
            "origin": {"surface": "history", "block": "A11.4"}})
    a = g.doi_xong(300)
    # Đợi theo ĐIỀU KIỆN, không tin một lần `doi_xong`.
    #
    # Đo được: lần chạy thứ ba báo đỏ với "8,4 giây" trong khi sổ cái nói lượt ấy chạy
    # 103 giây và tác tử đã cập nhật xong (cs-0006). `doi_xong` trả về sớm — nó thấy một
    # sự kiện kết lượt còn lại từ lượt TRƯỚC. Nên con số 8,4 giây không phải sản phẩm
    # nhanh, mà là bộ đo đọc đồng hồ trước khi việc xong.
    #
    # Một phép đo trả về sớm thì nó không đo gì cả — và tệ hơn: nó báo đỏ cho một việc
    # đã làm đúng, hoặc báo xanh cho một việc chưa xong.
    han = time.time() + 300
    while time.time() < han and _stale(du_an):
        time.sleep(2.0)
    sau_cap_nhat = time.time()

    con = _stale(du_an)
    b.kiem("Sau một cú bấm, hạ nguồn KHÔNG còn lỗi thời",
           not con, ", ".join(con) or "sạch")
    cs_tac_tu = [x for x in _so(du_an, "changeset")
                 if str((x.get("data") or {}).get("author", "")).startswith("agent")]
    b.kiem("Và tác tử thật sự GHI một thay đổi để cập nhật (không chỉ nói)",
           len(cs_tac_tu) >= 2,
           " → ".join((x.get("data") or {}).get("summary", "")[:40]
                      for x in cs_tac_tu[-2:]) or "không changeset nào")
    b.kiem("Tác tử nói ra nó đã làm gì", (a.get("so_loi_tac_tu") or 0) >= 1,
           (a.get("loi_tac_tu_cuoi") or "")[:140])

    # ============================================================ 4 · hai chỉ số "sau"
    b.phan("4 · HAI CHỈ SỐ CÒN THIẾU CỦA §7 — nay có con số “sau”")

    sys.path.insert(0, str(REPO / "tools"))
    import do_edit47 as do

    so = _so(du_an)
    loai = {a["id"]: a["type"] for a in kho.list(limit=500)}
    sua_duoc = set(json.loads(subprocess.run(
        [sys.executable, str(REPO / "tools/dem_sua_duoc.py"), "--json"],
        capture_output=True, text=True, cwd=REPO).stdout or "{}").get("sua_duoc", []))

    goi = do._goi_loi_le_ra_bam_duoc(so, loai, sua_duoc)
    c3 = do._sua_den_ha_nguon(so)

    b.kiem("Chỉ số 2 · KHÔNG lượt nào người gõ lời cho việc lẽ ra bấm được",
           len(goi["bam_duoc"]) == 0,
           f"{len(goi['bam_duoc'])} lượt · (câu giao việc đầu phiên không tính: nó là "
           f"việc KHÔNG có nút nào) · lần bấm nút: {len(goi['tu_nut'])}")
    b.kiem("Chỉ số 3 · ĐO ĐƯỢC thời gian sửa → hạ nguồn cập nhật",
           c3["so_lan_co_so"] >= 1,
           f"{c3['so_lan_co_so']} lần · "
           + (f"{c3['trung_vi_giay']:.1f} s" if c3["trung_vi_giay"] else "chưa có"))
    # `_sua_den_ha_nguon` trả DANH SÁCH `khong_bao_gio_cham`; khoá `so_lan_…` chỉ sinh ra
    # ở `do()` khi nó gộp 39 dự án. Đọc đúng tên trường thay vì đoán theo tên mình muốn.
    bo_quen = c3["khong_bao_gio_cham"]
    b.kiem("Chỉ số 3 · KHÔNG còn lần nào hạ nguồn bị bỏ quên",
           len(bo_quen) == 0,
           f"{len(bo_quen)} lần không ai cập nhật"
           + (": " + ", ".join(str(x.get("cs")) for x in bo_quen) if bo_quen else ""))

    giay_bam = sau_cap_nhat - truoc_sua
    print(f"\n  {XAM}Đo trên đồng hồ thật, từ lúc người bấm Lưu tới lúc hạ nguồn sạch: "
          f"{giay_bam:.1f} giây (đợi theo điều kiện, không theo một lần `doi_xong`){HET}")
    print(f"  {XAM}Mốc cũ (sổ 39 dự án, DEV-372): trung vị 41,8 PHÚT khi có ai cập nhật, "
          f"và 7 lần không ai cập nhật.{HET}")

    # Chi phí: nói ra, vì bộ này tốn tiền.
    # Đọc ĐÚNG tên trường trong sổ (`usage.in` / `usage.out` / `usage.cached`), không đoán
    # theo tên mình muốn. Bản đầu đọc `tokens_in`/`tokens_out` — hai khoá không tồn tại —
    # nên nó in "0 token" cho một phiên 19 lời gọi mô hình. Một con số bằng 0 vì đọc sai
    # tên trường là một con số nói dối về chi phí, ở đúng chỗ người cần biết giá.
    llm = _so(du_an, "llm_call")
    vao = sum(int(((e.get("data") or {}).get("usage") or {}).get("in", 0) or 0) for e in llm)
    ra_tok = sum(int(((e.get("data") or {}).get("usage") or {}).get("out", 0) or 0)
                 for e in llm)
    cache = sum(int(((e.get("data") or {}).get("usage") or {}).get("cached", 0) or 0)
                for e in llm)
    assert not llm or vao > 0, "đọc sai tên trường usage — xem chú thích trên"
    print(f"  {XAM}Chi phí phiên: {len(llm)} lời gọi mô hình · vào {vao:,} token "
          f"(trong đó {cache:,} lấy từ cache) · ra {ra_tok:,} token{HET}")

    ra = REPO / "du-lieu/ket-qua/phien_nguoi_bam.json"
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text(json.dumps({
        "luc": datetime.now().isoformat(timespec="seconds"),
        "chi_so_2_le_ra_bam_duoc": len(goi["bam_duoc"]),
        "chi_so_2_lan_bam_nut": len(goi["tu_nut"]),
        "chi_so_3_so_lan_do_duoc": c3["so_lan_co_so"],
        "chi_so_3_trung_vi_giay": c3["trung_vi_giay"],
        "chi_so_3_khong_ai_cap_nhat": len(c3["khong_bao_gio_cham"]),
        "giay_tu_luc_sua_den_luc_sach": round(giay_bam, 1),
        "so_loi_goi_mo_hinh": len(llm),
        "token_vao": vao, "token_cache": cache, "token_ra": ra_tok,
        "gioi_han": ("Người ở đây là một kịch bản đi qua kênh kiểm thử của app, không phải "
                     "người ngồi trước màn hình. Đo được đường đi của cú bấm; không đo "
                     "được việc người THẬT có chọn bấm thay vì gõ."),
    }, ensure_ascii=False, indent=1), "utf-8")
    print(f"  {XAM}kết quả: {ra}{HET}")
    return b.tong()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phiên thật: người bấm thay vì gõ")
    ap.add_argument("--du-an", default="du-lieu/phien-nguoi-bam")
    ap.add_argument("--giu", action="store_true")
    a = ap.parse_args(argv)

    if not os.environ.get("EIDE_E2E_MO_HINH"):
        print("Bộ này TỐN TIỀN mô hình. Chạy lại với:\n\n"
              "  EIDE_FEATURE_WATCHER=1 EIDE_FEATURE_SUA_LONG=1 EIDE_E2E_MO_HINH=1 \\\n"
              "      .venv/bin/python tools/phien_nguoi_bam.py\n")
        return 2

    from eide.config import load_dotenv
    load_dotenv()

    d = pathlib.Path(a.du_an).resolve()
    if d.exists() and not a.giu:
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "firmware").mkdir(exist_ok=True)
    (d / "firmware" / "main.c").write_text("int main(void){ for(;;); }\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
