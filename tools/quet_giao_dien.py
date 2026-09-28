#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quét TOÀN BỘ giao diện: 11 bề mặt · mọi khối · mọi nhãn · mọi nút.

    .venv/bin/python tools/quet_giao_dien.py [--du-an <đường dẫn>]

Câu hỏi bài này trả lời không phải *"app có mở được không"* mà *"có cái nhãn nào rỗng, cái nút
nào bấm mà không làm gì, cái khối nào giao diện không biết vẽ không"*. Mỗi câu là một con số
đọc được từ chính app, cộng một tấm ảnh do app tự vẽ.

Vì sao cần cả ảnh: hai chặng liền trước đều có một ô xanh đúng đi kèm một màn hình sai — thẻ
cổng đã đóng mà nút vẫn bấm được (DEV-289), và nhãn "không còn ở đây" không hiện ra (DEV-290).
Cả hai lần, con số đúng và câu hỏi sai. Nên bộ quét này chụp mọi bề mặt, và ảnh là một phần
của kết quả chứ không phải minh hoạ.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

RA = REPO / "docs/review-v3/test/ket-qua-giao-dien"

# Mã bề mặt → tên người đọc, đúng thứ tự tab trên giao diện.
BE_MAT = [
    ("requirements", "Yêu cầu & Giải pháp"), ("documents", "Tài liệu & Nguồn"),
    ("knowledge", "Tri thức mạch"), ("design", "Thiết kế"), ("tools", "Công cụ"),
    ("code", "Mã nguồn"), ("simulation", "Mô phỏng"), ("hardware", "Mạch thật"),
    ("journal", "Nhật ký"), ("history", "Lịch sử"), ("project", "Dự án & Bộ nhớ"),
]

# Dấu vết của giá trị chưa được dịch sang lời người đọc. Một nhãn mang `None` hay `{'x': 1}`
# là một chỗ mã quên đi qua tầng trình bày — người dùng đọc nó thành một lỗi.
RAC = ("None", "nan", "NaN", "null", "{'", "['", "<built-in", "object at 0x", "Traceback")


class BaoCao:
    def __init__(self, ra: pathlib.Path):
        ra.mkdir(parents=True, exist_ok=True)
        self.ra = ra
        self.muc: list[dict] = []
        self.phan = ""

    def sang_phan(self, t: str) -> None:
        self.phan = t
        print(f"\n▸ {t}", flush=True)

    def ket(self, dat: bool, cau: str, bang_chung: str = "") -> bool:
        self.muc.append({"phan": self.phan, "dat": dat, "cau": cau, "bang_chung": bang_chung})
        print(f"  {'✅' if dat else '❌'} {cau}\n     {bang_chung[:200]}", flush=True)
        return dat

    def ghi(self) -> pathlib.Path:
        dat = sum(1 for m in self.muc if m["dat"])
        d = ["# Quét toàn bộ giao diện — 11 bề mặt, mọi nhãn, mọi nút", "",
             f"**{dat}/{len(self.muc)} ô đạt.** Ảnh do chính app tự vẽ, nằm ở `anh/`.", "",
             "Bộ quét hỏi ba câu cho từng bề mặt: *có nhãn nào rỗng không · có khối nào giao "
             "diện không biết vẽ không · có nút nào bấm mà không làm gì không*. Ô trống được "
             "coi là ĐẠT chỉ khi nó nói đủ ba câu — **chưa có gì · vì sao · cần gì để có** — "
             "vì một ô trống câm là một ô người dùng không biết phải làm gì tiếp.", ""]
        phan = ""
        for m in self.muc:
            if m["phan"] != phan:
                phan = m["phan"]
                d += [f"## {phan}", "", "| Kết quả | Điều được kiểm | Bằng chứng |", "|---|---|---|"]
            bc = m["bang_chung"].replace("|", "\\|").replace("\n", " ")
            d.append(f"| {'✅' if m['dat'] else '❌'} | {m['cau']} | {bc} |")
        d.append("")
        p = self.ra / "KET-QUA.md"
        p.write_text("\n".join(d), "utf-8")
        (self.ra / "ket-qua.json").write_text(
            json.dumps(self.muc, ensure_ascii=False, indent=1), "utf-8")
        return p


def _rac(s: str) -> list[str]:
    return [r for r in RAC if r in (s or "")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--du-an", default="du-lieu/stm32f469-freertos",
                    help="dự án ĐÃ CÓ NỘI DUNG — quét trên dự án rỗng thì mọi bề mặt đều "
                         "trống và bài đo không nói được gì")
    a = ap.parse_args()

    from eide.config import load_dotenv
    load_dotenv()
    from phien_robot import mo_app

    du_an = (REPO / a.du_an).resolve()
    bc = BaoCao(RA)
    anh = RA / "anh"
    anh.mkdir(parents=True, exist_ok=True)

    g = mo_app(du_an)
    time.sleep(3)
    d0 = g.chup("mo")

    # ---------------------------------------------------------------- khung chung
    bc.sang_phan("Khung chung")
    tabs = d0.get("tab_co_the_chon") or []
    bc.ket(len(tabs) == 11 and [t for t, _ in BE_MAT] == tabs,
           "Đủ 11 tab, đúng thứ tự tài liệu", f"{tabs}")
    khung = d0.get("khung_cua_so") or {}
    bc.ket(bool(khung), "Đọc được khung cửa sổ để đo tràn", f"{khung}")

    # Ba nút bề rộng Console.
    px = {}
    for muc in ("Hẹp", "Vừa", "Rộng"):
        o = g.be_rong(muc)
        time.sleep(0.6)
        px[muc] = o.get("rong_dat")
    bc.ket(len({v for v in px.values() if v}) == 3,
           "Ba nút Hẹp / Vừa / Rộng của Console cho ba bề rộng KHÁC nhau", f"{px}")
    g.be_rong("Vừa")
    time.sleep(0.5)
    dv = g.chup("be-rong-vua")
    bc.ket(dv.get("be_rong_console") == "Vừa",
           "Bấm nút bề rộng thì trạng thái đổi theo", f"{dv.get('be_rong_console')}")

    # ---------------------------------------------------------------- từng bề mặt
    tong_khoi = 0
    for ma, ten in BE_MAT:
        bc.sang_phan(f"Bề mặt {ma} — {ten}")
        g.mo_tab(ma)
        time.sleep(1.2)
        g.ve_lai()
        time.sleep(1.0)
        d = g.chup(f"tab-{ma}")
        bc.ket(d.get("tab_dang_xem") == ma, "Bấm tab thì đúng bề mặt ấy hiện ra",
               f"đang xem: {d.get('tab_dang_xem')}")

        # Khoá là `khoi_tren_tab`, không phải `khoi` — dùng nhầm thì mọi bề mặt báo
        # "0 khối" và cả bộ quét xanh vì không có gì để soi.
        khoi = d.get("khoi_tren_tab") or []
        tong_khoi += len(khoi)
        bc.ket(bool(khoi), "Bề mặt có khối để hiện", f"{len(khoi)} khối")
        if not khoi:
            continue

        khong_ten = [b["code"] for b in khoi if not (b.get("title") or "").strip()]
        bc.ket(not khong_ten, "Mọi khối đều có TIÊU ĐỀ", f"thiếu: {khong_ten or '—'}")

        khong_ve = [b["code"] for b in khoi if not b.get("ve_duoc", True)]
        bc.ket(not khong_ve,
               "Giao diện biết vẽ mọi kiểu khối lõi gửi sang",
               f"không vẽ được: {khong_ve or '—'} · kiểu lạ toàn app: "
               f"{d.get('khoi_chua_biet_ve')}")

        rong = [b for b in khoi if (b.get("so_hang", 0) == 0 and b.get("so_muc", 0) == 0
                                    and b.get("so_buoc", 0) == 0
                                    and b.get("so_nut_cay", 0) == 0
                                    and not (b.get("summary") or "").strip())]
        cam = [b["code"] for b in rong
               if not ((b.get("chua_co") or "").strip() and (b.get("vi_sao") or "").strip())]
        bc.ket(not cam,
               "Ô trống nói đủ: chưa có gì · vì sao · cần gì để có",
               f"{len(rong)} khối trống, câm: {cam or '—'}")

        thieu_ex = [b["code"] for b in khoi
                    if b.get("co_explain") and not b.get("explain_du_6_truong")]
        bc.ket(not thieu_ex,
               "Khối nào có nút \"Vì sao?\" thì lớp giải thích đủ SÁU trường (N8)",
               f"thiếu trường: {thieu_ex or '—'}")

        ban = [(b["code"], _rac(b.get("chu_da_dung", ""))) for b in khoi]
        ban = [x for x in ban if x[1]]
        bc.ket(not ban, "Không nhãn nào lộ giá trị thô (None / dict / traceback)",
               f"{ban or '—'}")

        bc.ket(not (d.get("khoi_de_nhau") or []), "Không khối nào đè lên khối khác",
               f"{d.get('khoi_de_nhau') or '—'}")

        # So với BỀ RỘNG KHUNG PHẢI, không với bề rộng cửa sổ.
        #
        # Khối nằm ở khung bên phải; Console chiếm `min(bề rộng đã chọn, 38 % cửa sổ)` bên
        # trái (`RootView`). Lấy cả cửa sổ làm chuẩn thì một khối tràn khỏi khung phải vẫn
        # lọt — tức phép đo rộng hơn thứ nó định đo, và nó sẽ xanh cho đúng cái lỗi nó canh.
        rw = d.get("khung_cua_so", {}).get("rong") or khung.get("rong") or 0
        cw = min(d.get("be_rong_console_px") or 0, rw * 0.38) if rw else 0
        phai = int(rw - cw) if rw else 0
        rk = d.get("rong_khoi") or {}
        tran = {k: v for k, v in rk.items() if phai and v > phai}
        bc.ket(not tran, "Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn)",
               f"khung phải ≈ {phai} px (cửa sổ {rw} − console {int(cw)}) · tràn: {tran or '—'}")

        ch = d.get("khung_cua_so", {}).get("cao") or khung.get("cao") or 0
        ck = d.get("cao_khoi") or {}
        qua_cao = {k: v for k, v in ck.items() if ch and v > ch * 4}
        bc.ket(not qua_cao,
               "Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết)",
               f"khung cao {ch} · {qua_cao or '—'}")

        g.chup_man_hinh(anh / f"{ma}.png", ma)

    bc.sang_phan("Tổng các bề mặt")
    bc.ket(tong_khoi > 0, "Tổng số khối đã soi qua 11 bề mặt", f"{tong_khoi} khối")

    # ---------------------------------------------------------------- bảng Giới thiệu
    bc.sang_phan("Bảng Giới thiệu")
    g._gui({"ui": "gioi_thieu"})
    try:
        g._doi("da_mo_gioi_thieu", 15)
        time.sleep(1.2)
        p = g.chup_man_hinh(anh / "gioi-thieu.png", "gioi-thieu")
        bc.ket(bool(p), "Mở được bảng Giới thiệu từ menu và chụp lại được", str(p))
    except TimeoutError as e:
        bc.ket(False, "Mở được bảng Giới thiệu từ menu", str(e))

    # ---------------------------------------------------------------- khổ cửa sổ
    bc.sang_phan("Cửa sổ nhỏ nhất")
    g._gui({"ui": "co_cua_so", "rong": 1100, "cao": 720})
    try:
        g._doi("da_doi_co", 15)
    except TimeoutError:
        pass
    time.sleep(1.5)
    g.mo_tab("project")
    time.sleep(1.0)
    dn = g.chup("cua-so-nho")
    kh = dn.get("khung_cua_so") or {}
    rw = kh.get("rong") or kh.get("w") or 0
    tran = {k: v for k, v in (dn.get("rong_khoi") or {}).items() if rw and v > rw}
    bc.ket(not tran, "Ở khổ nhỏ nhất (1100×720) vẫn không khối nào tràn ngang",
           f"khung {kh} · tràn: {tran or '—'}")
    g.chup_man_hinh(anh / "cua-so-nho.png", "cua-so-nho")

    # ---------------------------------------------------------------- thanh trạng thái
    bc.sang_phan("Thanh trạng thái")
    g._gui({"ui": "co_cua_so", "rong": 1700, "cao": 1100})
    try:
        g._doi("da_doi_co", 15)
    except TimeoutError:
        pass
    time.sleep(1.2)
    dt = g.chup("thanh-trang-thai")
    tt = dt.get("trang_thai") or {}
    bc.ket(bool(tt), "Thanh trạng thái có dữ liệu", f"{tt}")
    trong = [k for k, v in tt.items() if isinstance(v, str) and not v.strip()]
    bc.ket(not trong, "Không ô nào trên thanh trạng thái bỏ trống câm",
           f"ô rỗng: {trong or '—'} · đủ: {sorted(tt)}")
    ban = {k: _rac(v) for k, v in tt.items() if isinstance(v, str) and _rac(v)}
    bc.ket(not ban, "Thanh trạng thái không lộ giá trị thô", f"{ban or '—'}")

    # ---------------------------------------------------------------- người sửa tay
    bc.sang_phan("Widget sửa tay (§E2 — người sửa được gì)")
    co_cot = []
    for ma, _ in BE_MAT:
        g.mo_tab(ma)
        time.sleep(0.9)
        dd = g.chup(f"cot-sua-{ma}")
        for b in dd.get("khoi_tren_tab") or []:
            if b.get("cot_sua"):
                co_cot.append((ma, b["code"], b["cot_sua"]))
    bc.ket(bool(co_cot),
           "Có ít nhất một khối cho người sửa trực tiếp bằng widget",
           "; ".join(f"{m}/{c}: {','.join(k)}" for m, c, k in co_cot[:6]) or "không khối nào")

    # ---------------------------------------------------------------- thông báo
    bc.sang_phan("Thông báo và hội thoại")
    dc = g.chup("cuoi")
    bc.ket(dc.get("so_the_con_nut", 0) == 0,
           "Không thẻ nào còn nút bấm được sau khi đã trả lời / hết hạn",
           f"{dc.get('so_the_con_nut')} thẻ còn nút · {len(dc.get('the_dang_cho') or [])} chờ")
    tb = dc.get("thong_bao") or []
    xau = [t for t in tb if _rac(t.get("chu", ""))]
    bc.ket(not xau, "Thông báo không lộ giá trị thô", f"{len(tb)} thông báo · {xau or '—'}")
    ren = dc.get("loi_tac_tu_render") or ""
    con_sao = [x for x in ("**", "##", "`") if x in ren]
    bc.ket(not con_sao,
           "Lời tác tử đã được DỰNG thành chữ, không còn dấu Markdown thô trên màn",
           f"còn: {con_sao or '—'}")

    p = bc.ghi()
    print(f"\nBáo cáo: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
