#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E qua GIAO DIỆN THẬT: việc lớn chia làm nhiều lần, rồi hợp nhất.

    .venv/bin/python tools/thu_chia_viec_lon.py

Kịch bản đúng như anh Công nêu: *viết một tài liệu mô tả toàn bộ thiết kế của một con chip* —
không xong trong một lượt, phải chia, phải ghi kết quả từng lần, rồi ghép lại.

## Đo cái gì

1. Tác tử có **tự vào chế độ kế hoạch** không, hay nó lao vào viết ngay rồi hụt hơi giữa chừng?
2. Kế hoạch có **sống qua việc đóng app** không — mở lại, gõ *"làm tiếp"*, nó đi tiếp đúng
   bước hay bắt đầu lại từ đầu?
3. Mỗi bước có để lại **hiện vật mở ra xem được** không?
4. Cuối cùng có **một tệp hợp nhất** không, và nó có đủ các phần theo đúng thứ tự không?

Câu 2 là câu đắt nhất và là câu duy nhất phải đóng app thật mới trả lời được.
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

from thu_giao_dien import Bo, GiaoDien                                    # noqa: E402

DU_AN = REPO / "du-lieu/thu-chia-viec"


def _mo_app() -> GiaoDien:
    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    time.sleep(1.5)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])
    g = GiaoDien(DU_AN)
    g.san_sang(45)
    return g


def _ke_hoach() -> dict:
    """Đọc kế hoạch thẳng từ KHO của dự án — nguồn không sửa được, không phải lời tác tử."""
    import sqlite3

    db = DU_AN / ".eide" / "store.sqlite"
    if not db.exists():
        return {}
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        r = c.execute("select canonical from artefacts where id='plan:current' "
                      "and deleted=0").fetchone()
        return json.loads(r[0]) if r else {}
    finally:
        c.close()


def _hien_vat_trong_kho() -> set[str]:
    import sqlite3

    db = DU_AN / ".eide" / "store.sqlite"
    if not db.exists():
        return set()
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {r[0] for r in c.execute("select id from artefacts where deleted=0")}
    finally:
        c.close()


def _cong_cu_da_goi() -> list[str]:
    p = DU_AN / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for d in p.read_text("utf-8").splitlines():
        if not d.strip():
            continue
        try:
            o = json.loads(d)
        except ValueError:
            continue
        if o.get("kind") in ("tool_use", "subagent_tool"):
            t = (o.get("data") or {}).get("tool")
            if t:
                ra.append(t)
    return ra


def chay() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    if DU_AN.exists():
        shutil.rmtree(DU_AN)
    DU_AN.mkdir(parents=True)
    (DU_AN / "y-tuong.md").write_text(
        "# Chip đo nhiệt độ MT-01\n\n"
        "Chip đo nhiệt độ môi trường, giao tiếp I2C, nguồn 3,3 V, có chế độ ngủ sâu.\n"
        "Dải đo −40…+125 °C, sai số ±0,5 °C.\n", "utf-8")

    g = _mo_app()
    bo = Bo("chia-viec-lon")

    # ------------------------------------------------------------ 1. có chia không
    bo.phan("Giao một việc KHÔNG xong trong một lượt")
    g.go("Bạn viết giúp tôi tài liệu mô tả TOÀN BỘ thiết kế con chip MT-01 trong y-tuong.md: "
         "tổng quan, khối chức năng, bản đồ thanh ghi, giao thức I2C, chế độ nguồn, và kế "
         "hoạch kiểm thử. Việc này dài, bạn cứ chia ra làm dần nhé.")
    g.doi_xong(600)
    cc = _cong_cu_da_goi()
    bo.kiem("Tự vào chế độ kế hoạch", "plan.enter" in cc, f"chuỗi công cụ: {cc[:12]}")

    # Thẻ cổng G-SCOPE (việc lớn) — duyệt hộ người dùng. Đo SỐ BƯỚC SAU khi duyệt: lúc vừa
    # `plan.enter` thì kế hoạch còn `dang_soan` và 0 bước, đo ở đó là đo quá sớm.
    for _ in range(3):
        a = g.chup("cho-duyet")
        cho = a.get("the_dang_cho") or []
        if not cho:
            break
        for the in cho:
            g.quyet_cong(the.get("id") or the.get("gate_id"), True, "Duyệt, làm dần đi.")
        g.doi_xong(600)
    kh = _ke_hoach()
    bo.kiem("Kế hoạch có từ 3 bước trở lên", len(kh.get("steps") or []) >= 3,
            f"{len(kh.get('steps') or [])} bước · trạng thái {kh.get('trang_thai')}")

    # ------------------------------------------------------------ 2. sống qua đóng app
    #
    # Đóng app NGAY khi vừa duyệt kế hoạch, lúc còn bước chưa làm. Bản đầu của bộ đo đóng app
    # sau khi tác tử đã đi hết sáu bước — nên câu "gõ làm tiếp thì đi tiếp" không còn gì để
    # đi tiếp, và ô đỏ ấy nói về phép đo chứ không nói về sản phẩm.
    bo.phan("Đóng app rồi mở lại — kế hoạch có sống không")
    truoc = _ke_hoach()
    xong_truoc = sum(1 for b in truoc.get("steps") or [] if b.get("xong"))
    con_lai = len(truoc.get("steps") or []) - xong_truoc
    bo.kiem("Còn bước chưa làm để mà đo việc đi tiếp", con_lai > 0,
            f"xong {xong_truoc}/{len(truoc.get('steps') or [])}")
    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    time.sleep(2)
    g = _mo_app()
    sau = _ke_hoach()
    bo.kiem("Kế hoạch còn nguyên sau khi tắt app",
            sau.get("muc_tieu") == truoc.get("muc_tieu")
            and len(sau.get("steps") or []) == len(truoc.get("steps") or []),
            f"trước: {len(truoc.get('steps') or [])} bước · sau: "
            f"{len(sau.get('steps') or [])} bước")

    g.go("Làm tiếp nhé.")
    g.doi_xong(900)
    kh2 = _ke_hoach()
    xong_sau = sum(1 for b in kh2.get("steps") or [] if b.get("xong"))
    bo.kiem("Gõ “làm tiếp” thì đi TIẾP, không làm lại từ đầu",
            xong_sau > xong_truoc,
            f"xong {xong_truoc} → {xong_sau} / {len(kh2.get('steps') or [])}")

    # ------------------------------------------------------------ 3. hiện vật từng bước
    bo.phan("Mỗi bước để lại gì")
    buoc_xong = [b for b in (kh2.get("steps") or []) if b.get("xong")]
    co_that = []
    for b in buoc_xong:
        ghi = b.get("ghi_chu") or ""
        thuc = ghi.split("hiện vật:")[-1].strip() if "hiện vật:" in ghi else ""
        # Hiện vật hợp lệ gồm cả mã hiện vật trong kho và mã changeset, không chỉ tệp —
        # bản đầu chỉ thử đường dẫn nên một bước để lại `cs-0003` bị chấm đỏ oan.
        co_that.append(any((DU_AN / x.strip("`',")).exists() or x.startswith("cs-")
                           or x.strip("`',") in _hien_vat_trong_kho()
                           for x in thuc.replace(",", " ").split()))
    bo.kiem("Mọi bước đã xong đều để lại hiện vật CÓ THẬT",
            bool(buoc_xong) and all(co_that),
            f"{sum(co_that)}/{len(buoc_xong)} bước có hiện vật mở được")

    # ------------------------------------------------------------ 4. hợp nhất
    bo.phan("Làm nốt rồi hợp nhất")
    for _ in range(4):
        if all(b.get("xong") for b in (_ke_hoach().get("steps") or [{}])):
            break
        g.go("Làm tiếp nhé.")
        g.doi_xong(900)
    kh3 = _ke_hoach()
    bo.kiem("Đi hết mọi bước",
            bool(kh3.get("steps")) and all(b.get("xong") for b in kh3["steps"]),
            f"{sum(1 for b in kh3.get('steps') or [] if b.get('xong'))}/"
            f"{len(kh3.get('steps') or [])}")

    g.go("Giờ bạn gộp tất cả các phần lại thành một tài liệu hoàn chỉnh cho tôi nhé.")
    g.doi_xong(600)
    cc = _cong_cu_da_goi()
    bo.kiem("Gọi `plan.merge`", "plan.merge" in cc, f"chuỗi công cụ cuối: {cc[-10:]}")

    # Có MỘT tài liệu đầy đủ ở cuối — dù bằng đường gộp hay bằng đường viết dồn một tệp.
    # Cả hai kiểu đều hợp lệ (xem skill `chia-viec-lon`); thứ đáng đo là sản phẩm cuối.
    md = [x for x in DU_AN.rglob("*.md") if ".eide" not in x.parts and x.name != "EIDE.md"]
    lon = max(md, key=lambda x: x.stat().st_size) if md else None
    bo.kiem("Có một tài liệu đầy đủ ở cuối", lon is not None and lon.stat().st_size > 4000,
            str([f"{x.name} {x.stat().st_size}B" for x in md]))
    if lon is not None:
        t = lon.read_text("utf-8", errors="replace")
        bo.kiem("Tệp hợp nhất có mục lục", "Mục lục" in t, lon.name)
        # Đo thứ ĐÁNG quan tâm: đủ các phần, ĐÚNG THỨ TỰ BƯỚC.
        #
        # Bản đầu đòi dấu `*Nguồn:` do `plan.merge` sinh. Nhưng tác tử có quyền sửa lại bản
        # gộp sau đó (`fs.edit` — đúng thứ skill bảo nó làm), và khi ấy dấu ấy mất mà tài liệu
        # vẫn đúng. Đo dấu vết của công cụ là đo sai chỗ; đo NỘI DUNG mới đúng chỗ.
        ten_buoc = [b.get("viec", "") for b in (kh3.get("steps") or [])]
        vi_tri = [t.find(x[:18]) for x in ten_buoc]
        du = all(v >= 0 for v in vi_tri)
        dung_thu_tu = du and vi_tri == sorted(vi_tri)
        bo.kiem("Đủ mọi phần, ĐÚNG thứ tự bước", dung_thu_tu,
                f"{sum(1 for v in vi_tri if v >= 0)}/{len(ten_buoc)} phần có mặt · "
                f"{len(t)} ký tự")

    # ------------------------------------------------------ 5. hỏi THẲNG kiểu mỗi phần một tệp
    #
    # Bốn phần trên đo hành vi MẶC ĐỊNH, và mặc định thì tác tử thích viết dồn vào một tệp:
    # nhanh, và với tài liệu ngắn thì hợp lý. Phần này đo NĂNG LỰC mà anh Công hỏi tới — chia
    # nhỏ, ghi kết quả từng lần, rồi hợp nhất — bằng cách nói rõ ra.
    #
    # Hai thứ ấy khác nhau và không được trộn vào một ô: "nó không tự chọn" khác hẳn "nó không
    # làm được".
    bo.phan("Hỏi THẲNG: mỗi phần một tệp rồi gộp")
    g.go("Giờ làm lại theo cách khác nhé: viết đặc tả kiểm thử cho MT-01, chia làm ba phần — "
         "kiểm điện, kiểm giao thức I2C, kiểm nhiệt — **mỗi phần một tệp riêng** trong "
         "thư mục dac-ta/, làm xong từng phần thì đánh dấu bước, cuối cùng gộp cả ba thành "
         "một tài liệu hoàn chỉnh.")
    for _ in range(4):
        g.doi_xong(900)
        a = g.chup("vong")
        cho = a.get("the_dang_cho") or []
        if cho:
            for the in cho:
                g.quyet_cong(the.get("id") or the.get("gate_id"), True, "Duyệt.")
            continue
        if "plan.merge" in _cong_cu_da_goi()[-30:]:
            break
        g.go("Làm tiếp nhé.")

    cc = _cong_cu_da_goi()
    bo.kiem("Gọi `plan.merge` khi được yêu cầu gộp", "plan.merge" in cc,
            f"chuỗi công cụ cuối: {cc[-12:]}")
    rieng = sorted(x for x in DU_AN.rglob("dac-ta/*.md"))
    bo.kiem("Mỗi phần một tệp riêng", len(rieng) >= 3,
            str([x.name for x in rieng]))
    hop = [x for x in DU_AN.rglob("*.md")
           if ".eide" not in x.parts and x.name != "EIDE.md" and "dac-ta" not in x.parts]
    ghep = [x for x in hop if "Mục lục" in x.read_text("utf-8", errors="replace")
            and "*Nguồn:" in x.read_text("utf-8", errors="replace")]
    bo.kiem("Có tệp gộp do `plan.merge` sinh (có mục lục + ghi nguồn từng phần)",
            bool(ghep), str([x.name for x in hop]))

    g.chup_man_hinh(REPO / "docs/review-v3/test/ket-qua-chia-viec/man-hinh.png", "chia-viec")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
