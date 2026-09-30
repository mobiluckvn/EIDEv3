#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Đo qua APP THẬT ba việc anh Công báo về màn hình tương tác.

    .venv/bin/python tools/thu_doi_du_an_va_nhip.py

1. *"khi tạo mới dự án thì màn hình này vẫn lưu thông tin chat của dự án khác"*
2. *"chưa cập nhật các thông tin như token, số lần gọi tool ở thanh trạng thái"*
3. *"review kỹ các label status xem cái nào chưa tích hợp"*

Ba câu hỏi này **không đo được bằng bộ kiểm đơn vị**: câu 1 hỏi về trạng thái còn lại trong
tiến trình app sau khi đổi dự án, câu 2 hỏi về thứ chỉ tồn tại *trong lúc* một lượt đang chạy.
Cả hai chỉ trả lời được bằng cách mở app thật, làm thật, rồi hỏi app xem trên màn có gì.

Bài này tốn một lượt mô hình thật (mục 2 cần tác tử gọi vài công cụ để có gì mà đếm).
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import threading
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien                                    # noqa: E402

DU_AN_A = REPO / "du-lieu/thu-doi-du-an-A"
DU_AN_B = REPO / "du-lieu/thu-doi-du-an-B"

CAU_A = "Xin chào, tên dự án này là ALPHA-MỘT-HAI-BA nhé, nhớ giúp mình."


def _mo_app(du_an: pathlib.Path) -> GiaoDien:
    # Đợi tiến trình cũ CHẾT HẲN, đừng đợi một con số cố định: `open -a` gọi vào một app
    # đang tắt dở sẽ đánh thức chính nó, và lõi mới không bao giờ khởi tạo — thấy đúng một
    # lần, biểu hiện là `.eide` chỉ có `sessions/` mà không có `store.sqlite`.
    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    het = time.time() + 20
    while time.time() < het:
        if subprocess.run(["pgrep", "-f", "MacOS/EIDE"],
                          capture_output=True).returncode != 0:
            break
        time.sleep(0.5)
    time.sleep(1.0)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(du_an)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])
    g = GiaoDien(du_an)
    g.san_sang(45)
    return g


def chay() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    for d in (DU_AN_A, DU_AN_B):
        if d.exists():
            shutil.rmtree(d)
    # A: tạo sẵn thư mục kênh để bật lần đầu. B: **không được tồn tại**, vì "tạo dự án mới"
    # từ chối mọi đường dẫn đã có — kênh tự theo sang B (xem `daTungBat` trong UITestChannel).
    (DU_AN_A / ".eide" / "ui-test").mkdir(parents=True)
    (DU_AN_A / "ghi-chu.md").write_text("# Dự án ALPHA\n", "utf-8")

    bo = Bo("doi-du-an-va-nhip")

    # ---------------------------------------------------------------- 1 · dự án A nói gì đó
    bo.phan("Dự án A — để lại dấu vết trên màn hình")
    g = _mo_app(DU_AN_A)
    g.go(CAU_A)
    g.doi_xong(420)
    a = g.chup("A-sau-khi-noi")
    chu_a = str(a.get("loi_tac_tu_render") or "") + json.dumps(a.get("thong_bao") or [],
                                                              ensure_ascii=False)
    bo.kiem("Dự án A có chữ trên màn hình", len(chu_a.strip()) > 20, f"{len(chu_a)} ký tự")
    bo.kiem("Thanh trạng thái mang tên dự án A",
            (a.get("trang_thai") or {}).get("du_an") == DU_AN_A.name,
            str((a.get("trang_thai") or {}).get("du_an")))

    # Con số sau một lượt THẬT — dùng để so với dự án B ở dưới.
    tt_a = (a.get("trang_thai") or {})
    tok_a = (tt_a.get("token") or {}).get("phien", 0)
    tool_a = (tt_a.get("ngan_sach") or {}).get("da_dung_tool", 0)
    bo.kiem("Sau một lượt, thanh trạng thái CÓ token của phiên", tok_a > 0, f"{tok_a} token")
    bo.kiem("Sau một lượt, thanh trạng thái CÓ số lời gọi công cụ",
            tool_a > 0, f"{tool_a} lời gọi")

    # ------------------------------------------------------------- 2 · đổi sang dự án B
    #
    # Đây là câu hỏi chính. Đổi dự án BẰNG ĐÚNG ĐƯỜNG người dùng đi (menu → mở dự án khác),
    # không phải bằng cách tắt app rồi mở lại — vì tắt app thì tất nhiên sạch, và bài đo sẽ
    # trả lời một câu không ai hỏi.
    bo.phan("Đổi sang dự án B bằng đúng đường người dùng đi")
    kq = g.du_an_moi(DU_AN_B)
    bo.kiem("App nhận lệnh tạo dự án mới", kq.get("su_kien") == "du_an_moi",
            json.dumps(kq, ensure_ascii=False)[:120])
    time.sleep(3.0)
    # `xoa=False`: app đã tự mở kênh ở B và ghi `kenh_mo` rồi. Dựng một `GiaoDien` mặc định
    # ở đây sẽ cắt trắng outbox, tức xoá đúng dòng mình sắp đợi.
    g2 = GiaoDien(DU_AN_B, xoa=False)
    g2.san_sang(45)
    b = g2.chup("B-vua-mo")

    chu_b = (str(b.get("loi_tac_tu_render") or "")
             + json.dumps(b.get("khoi_markdown") or [], ensure_ascii=False)
             + json.dumps(b.get("thong_bao") or [], ensure_ascii=False))
    bo.kiem("Màn hình dự án B KHÔNG còn chữ của dự án A",
            "ALPHA-MỘT-HAI-BA" not in chu_b and "ALPHA" not in chu_b,
            "còn thấy chuỗi của A" if "ALPHA" in chu_b else "sạch")
    bo.kiem("Không còn thẻ cổng nào của dự án cũ",
            not (b.get("the_dang_cho") or []),
            f"{len(b.get('the_dang_cho') or [])} thẻ")

    tt_b = (b.get("trang_thai") or {})
    bo.kiem("Thanh trạng thái đã đổi sang tên dự án B",
            tt_b.get("du_an") == DU_AN_B.name, str(tt_b.get("du_an")))
    bo.kiem("Token của phiên đã VỀ 0 ở dự án mới",
            (tt_b.get("token") or {}).get("phien", -1) == 0,
            str((tt_b.get("token") or {}).get("phien")))
    bo.kiem("Số lời gọi công cụ đã VỀ 0 ở dự án mới",
            (tt_b.get("ngan_sach") or {}).get("da_dung_tool", -1) == 0,
            str((tt_b.get("ngan_sach") or {}).get("da_dung_tool")))

    # ------------------------------------------------- 3 · số đo có SỐNG giữa lượt không
    #
    # Hỏi app liên tục trong lúc tác tử đang làm. Trước bản vá, mọi lần hỏi đều trả `0/40`
    # cho tới khi lượt kết thúc.
    bo.phan("Số đo giữa lượt — hỏi app trong lúc nó đang chạy")
    thay: list[dict] = []

    def soi() -> None:
        het = time.time() + 240
        while time.time() < het:
            try:
                anh = g2.chup("giua-luot")
            except Exception:
                break
            d = anh.get("trang_thai") or {}
            # `run_trang_thai` nằm ở MỨC TRÊN của bản chụp, không trong `trang_thai` — nó là
            # dữ liệu cho bộ đo chứ không phải một ô trên thanh (xem `UITestChannel`).
            chay = anh.get("run_trang_thai", "")
            thay.append({"tool": (d.get("ngan_sach") or {}).get("da_dung_tool", 0),
                         "token": (d.get("token") or {}).get("luot", 0),
                         "chay": chay})
            if chay != "running" and len(thay) > 3:
                break
            time.sleep(2.0)

    t = threading.Thread(target=soi, daemon=True)
    g2.go("Đọc giúp mình mọi tệp trong dự án, liệt kê tên và số dòng từng tệp, "
          "rồi viết một tệp `tom-tat.md` ghi lại danh sách đó.")
    t.start()
    g2.doi_xong(420)
    time.sleep(1.0)

    giua = [x for x in thay if x["chay"] == "running"]
    bo.kiem("Có bắt được khoảnh khắc lượt ĐANG chạy", bool(giua), f"{len(giua)}/{len(thay)} lần soi")
    bo.kiem("Số lời gọi công cụ TĂNG trong lúc lượt còn chạy",
            any(x["tool"] > 0 for x in giua),
            "dãy tool: " + ", ".join(str(x["tool"]) for x in thay[:12]))
    bo.kiem("Token của lượt TĂNG trong lúc lượt còn chạy",
            any(x["token"] > 0 for x in giua),
            "dãy token: " + ", ".join(str(x["token"]) for x in thay[:12]))
    bo.kiem("Bộ đếm KHÔNG chạy ngược",
            all(b >= a for a, b in zip([x["tool"] for x in giua],
                                       [x["tool"] for x in giua][1:])),
            "dãy tool giữa lượt: " + ", ".join(str(x["tool"]) for x in giua))

    # ---------------------------------------------------------- 4 · nhãn nào chưa tích hợp
    bo.phan("Nhãn trên thanh trạng thái")
    cuoi = g2.chup("cuoi").get("trang_thai") or {}
    for ten in ("du_an", "chip", "chang", "mo_hinh", "ngan_sach", "token", "ngu_canh"):
        bo.kiem(f"Thanh trạng thái có `{ten}`", ten in cuoi, str(cuoi.get(ten))[:60])
    bo.kiem("Token phiên KHÁC 0 sau khi làm việc",
            (cuoi.get("token") or {}).get("phien", 0) > 0,
            str((cuoi.get("token") or {}).get("phien")))

    g2.chup_man_hinh(REPO / "docs/review-v3/test/ket-qua-thanh-trang-thai/man-hinh.png",
                     "thanh-trang-thai")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
