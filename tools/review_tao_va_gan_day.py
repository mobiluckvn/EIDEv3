#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ba tính năng vòng đời dự án, đo qua GUI thật: tạo mới · đóng · mở lại gần đây.

Trước DEV-290, cả ba đều không tồn tại trên giao diện:

* "Tạo dự án" CHẠY ĐƯỢC nhưng không nhìn được — nó chỉ là hệ quả của việc mở một thư mục
  rỗng, và `CommandGroup(replacing: .newItem) {}` đã xoá trắng File ▸ New.
* Danh sách gần đây không có: chỉ một chuỗi `duAnPath` bị ghi đè mỗi lần.
* `AppState.dong()` chưa từng được gọi ở đâu, nên một khi đã đặt dự án thì **không có đường
  quay lại màn mở** — danh sách gần đây có làm ra cũng không ai tới được. Đó là lý do bài đo
  này kiểm cả ba cùng nhau chứ không kiểm riêng từng cái: hai cái đầu vô nghĩa nếu thiếu cái
  thứ ba.

Chạy:  .venv/bin/python tools/review_tao_va_gan_day.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

GOC = REPO / "du-lieu/thu-vong-doi"
RA = REPO / "du-lieu/ket-qua/vong-doi"


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    from phien_robot import NhatKy, mo_app

    for p in (GOC, RA):
        if p.exists():
            shutil.rmtree(p)
    (GOC / "mot").mkdir(parents=True)          # dự án đầu, mở bằng đường cũ

    nk = NhatKy(RA, tieu_de="Vòng đời dự án: tạo mới · đóng · mở lại gần đây",
                nguon="ba thư mục dựng tại chỗ", du_an=str((GOC / "mot").relative_to(REPO)))

    # ---------------------------------------------------------------- 1. dự án đầu
    nk.buoc("Mở dự án thứ nhất")
    g = mo_app(GOC / "mot")
    time.sleep(2)
    a = g.chup("da-mo-mot")
    nk.ket(a.get("man_hinh") == "lam-viec", "Đang ở màn làm việc",
           f"man_hinh = {a.get('man_hinh')}")
    nk.ket("mot" in json.dumps(a.get("du_an_gan_day") or [], ensure_ascii=False),
           "Dự án TỰ MỞ lúc khởi động cũng vào danh sách gần đây",
           f"gần đây: {a.get('du_an_gan_day')}")

    # ---------------------------------------------------------------- 2. tạo dự án mới
    nk.buoc("Tạo dự án MỚI — thứ trước đây không có nút nào gọi được")
    hai = GOC / "hai"
    o = g.du_an_moi(hai)
    time.sleep(4)
    b = g.chup("da-tao-hai")
    nk.ket(o.get("su_kien") == "du_an_moi" and hai.is_dir(),
           "Tạo được thư mục dự án mới từ giao diện",
           f"{o} · thư mục có: {hai.is_dir()}")
    nk.ket((hai / ".eide").is_dir() and (hai / "EIDE.md").exists(),
           "Lõi tự dựng `.eide/` và `EIDE.md` cho dự án mới — app KHÔNG tự dựng hộ",
           f".eide: {(hai / '.eide').is_dir()} · EIDE.md: {(hai / 'EIDE.md').exists()}")
    nk.ket(b.get("man_hinh") == "lam-viec", "Tạo xong thì mở luôn, không phải mở lại bằng tay",
           f"man_hinh = {b.get('man_hinh')}")

    # ---------------------------------------------------------------- 3. luật không lồng
    nk.buoc("Từ chối tạo dự án LỒNG trong một dự án khác")
    o = g.du_an_moi(GOC / "mot" / "long-ben-trong")
    nk.ket(o.get("su_kien") == "du_an_moi_loi"
           and not (GOC / "mot" / "long-ben-trong").exists(),
           "Chặn dự án lồng nhau, và nói rõ vì sao",
           f"{o.get('loi', o)}")
    o2 = g.du_an_moi(hai)
    nk.ket(o2.get("su_kien") == "du_an_moi_loi",
           "Từ chối khi chỗ ấy đã có sẵn thứ gì đó", f"{o2.get('loi', o2)}")

    # ---------------------------------------------------------------- 4. đóng dự án
    nk.buoc("Đóng dự án — đường quay lại màn mở, trước đây không có")
    g.dong_du_an()
    time.sleep(2)
    c = g.chup("da-dong")
    nk.ket(c.get("man_hinh") == "mo-du-an", "Về được màn mở dự án",
           f"man_hinh = {c.get('man_hinh')}")

    # ---------------------------------------------------------------- 5. mở lại gần đây
    nk.buoc("Mở lại dự án thứ nhất từ danh sách gần đây — không gõ lại đường dẫn")
    ds = c.get("du_an_gan_day") or []
    nk.ket(len(ds) >= 2, "Danh sách gần đây có cả hai dự án, mới nhất trước",
           f"{ds}")
    g.mo_gan_day(GOC / "mot")
    time.sleep(3)
    d = g.chup("da-mo-lai-mot")
    nk.ket(d.get("man_hinh") == "lam-viec" and (d.get("du_an_gan_day") or [None])[0]
           == str(GOC / "mot"),
           "Mở lại được, và nó nhảy lên đầu danh sách",
           f"man_hinh = {d.get('man_hinh')} · gần đây: {d.get('du_an_gan_day')}")

    # ---------------------------------------------------------------- 6. dự án đã biến mất
    nk.buoc("Dự án trong danh sách bị xoá khỏi đĩa — hiện thế nào?")
    g.dong_du_an()
    time.sleep(1.5)
    shutil.rmtree(hai)
    e = g.chup("mot-du-an-da-mat")
    con = str(hai) in (e.get("du_an_gan_day") or [])
    nk.ket(con,
           "Vẫn HIỆN trong danh sách (mờ, không bấm được) thay vì lặng lẽ biến mất",
           "lặng lẽ lọc ra thì người thấy một mục mất đi mà không biết vì sao — mà lý do "
           "thường là họ vừa đổi tên hoặc chuyển thư mục, đúng lúc họ cần biết nhất")
    nk.anh(g, "man-mo-du-an")

    nk.ghi("Kết thúc", f"nhật ký: {nk.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
