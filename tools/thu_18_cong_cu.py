#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Giao ĐÚNG loại việc cho 17 công cụ chưa nổ, xem cái nào vẫn không nổ.

    .venv/bin/python tools/thu_18_cong_cu.py [--giu]

`--giu` giữ lại dự án của lần chạy trước. Mặc định thì xoá đi làm lại cho sạch — nhưng **xoá
dự án là xoá luôn sổ cái**, tức xoá bằng chứng rằng công cụ nào đã từng nổ. Đo được ngay ở
lượt chạy thứ hai của chính bộ này: `fact.review` và `store.procedure_progress` đã nổ ở lượt
một, rồi biến mất khỏi thống kê vì lượt hai dọn sạch chỗ chúng từng nổ.

*Một phép đo phá mất dữ liệu của phép đo trước là một phép đo chỉ nói về lần cuối cùng.*

Sau DEV-306 và DEV-308, còn một nhóm công cụ được xếp là *"cần một loại việc chưa ai giao"*.
Nhãn ấy **rất dễ thành cái cớ**: nói vậy thì công cụ nào cũng có lý do để im.

Cách phân biệt duy nhất là **giao thử đúng loại việc đó một lần**. Vẫn không nổ thì nó là
đường đứt, và lúc ấy mới đi tìm chỗ đứt.

Mỗi ca ở đây là một câu tiếng Việt như người dùng thật sẽ gõ — không nhắc tên công cụ, vì nhắc
tên là mớm bài, và mớm bài thì đo chính lời mớm chứ không đo sản phẩm.
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

DU_AN = REPO / "du-lieu/thu-18"

# (công cụ mong đợi, tên ca, câu người dùng gõ)
CA: list[tuple[str, str, str]] = [
    ("memory.status", "Bộ nhớ đang chứa gì",
     "Bộ nhớ dài hạn của dự án đang chứa những gì, còn bao nhiêu chỗ, có gì nên lược bớt "
     "không?"),
    ("memory.metrics", "Sáu chỉ số bộ nhớ",
     "Cho mình xem các chỉ số đo bộ nhớ của phiên này: mỗi lượt tốn bao nhiêu token, nén mấy "
     "lần, tỉ lệ kiểm đạt ngay lần đầu là bao nhiêu."),
    ("memory.remember_user", "Sở thích xuyên dự án",
     "Lần nào mình cũng nhắc rồi: mọi số đo trong mọi dự án của mình đều dùng đơn vị SI, "
     "đừng dùng mil hay inch nữa nhé. Nhớ giúp mình cho các dự án sau luôn."),
    ("memory.gc", "Dọn blob quá hạn",
     "Thư mục .eide phình to rồi, bạn xem có bản sao nội dung nào không còn ai trỏ tới thì "
     "dọn giúp mình."),
    ("ckm.import_netlist", "Đưa netlist vào bản đồ mạch",
     "Mình có tệp netlist `mach.net` xuất từ KiCad, bạn đọc rồi đưa vào bản đồ tri thức mạch "
     "của dự án giúp mình."),
    ("khoi.list", "Thư viện khối có gì",
     "Thư viện khối tái dùng của EIDE đang có sẵn những khối nào?"),
    ("khoi.place", "Đặt một khối vào mạch",
     "Đặt giúp mình một khối LDO 3,3 V vào mạch, đầu vào 5 V từ USB, dòng tải khoảng 200 mA."),
    ("khoi.extract", "Lưu khối đang có thành khối dùng lại",
     "Khối nguồn vừa đặt ấy mình muốn dùng lại ở dự án sau. Lưu nó thành một khối trong thư "
     "viện giúp mình."),
    ("doc.language", "Máy đọc được ngôn ngữ này chưa",
     "Tài liệu mình sắp đưa vào là tiếng Nhật. Máy mình đã có đủ gói để đọc nó chưa?"),
    ("doc.to_pdf", "Cần số trang để in",
     "Tệp Word `dac-ta.docx` trong dự án ấy, mình cần bản PDF để in và đối chiếu số trang "
     "với thầy."),
    ("doc.figures", "Rút hình trong PDF",
     "Trong tệp `bai-bao.pdf` có mấy cái hình, bạn rút chúng ra thành tri thức đọc được "
     "giúp mình."),
    ("store.procedure_progress", "Báo làm xong một bước quy trình",
     "Quy trình nạp firmware bạn vừa viết ấy — mình làm xong bước 1 và bước 2 rồi, bước 3 "
     "thì hỏng vì máy không thấy ổ bộ nạp."),
    ("fact.review", "Người duyệt Fact BẠC → VÀNG",
     "Mình đã đọc kỹ các Fact đang ở tầng BẠC trong bảng rà soát và thấy đúng hết. "
     "Duyệt chúng lên VÀNG giúp mình."),
    ("ui.explain", "Bấm nút Giải thích thêm",
     "Giải thích thêm cho tôi về A4.2 — Bảng Fact. Nói rõ nó từ đâu ra và tin được tới đâu."),
]


def _cong_cu() -> list[str]:
    p = DU_AN / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for d in p.read_text("utf-8", errors="replace").splitlines():
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
    giu = "--giu" in sys.argv
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    DU_AN.mkdir(parents=True, exist_ok=True)

    # --- hiện vật để các ca có cái mà làm việc -----------------------------------
    (DU_AN / "y-tuong.md").write_text(
        "# Mạch đo nhiệt độ\n\nCảm biến I2C, nguồn 3,3 V từ USB 5 V, có chế độ ngủ.\n", "utf-8")
    (DU_AN / "mach.net").write_text(
        '(export (version D)\n'
        '  (components\n'
        '    (comp (ref U1) (value LM1117-3.3) (footprint SOT-223))\n'
        '    (comp (ref C1) (value 10uF) (footprint 0805))\n'
        '    (comp (ref C2) (value 22uF) (footprint 0805)))\n'
        '  (nets\n'
        '    (net (code 1) (name "+5V") (node (ref U1) (pin 3)) (node (ref C1) (pin 1)))\n'
        '    (net (code 2) (name "+3V3") (node (ref U1) (pin 2)) (node (ref C2) (pin 1)))\n'
        '    (net (code 3) (name "GND") (node (ref U1) (pin 1)) (node (ref C1) (pin 2))'
        ' (node (ref C2) (pin 2)))))\n', "utf-8")
    goc_docx = REPO / "du-lieu/thu-tai-lieu/y-tuong.docx"
    if goc_docx.exists():
        shutil.copy(goc_docx, DU_AN / "dac-ta.docx")
    pdf = sorted((REPO / "docs/bao-cao-rev-ecit/tai-lieu-tham-khao").glob("*.pdf"))
    if pdf:
        shutil.copy(pdf[0], DU_AN / "bai-bao.pdf")

    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    time.sleep(1.5)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])
    g = GiaoDien(DU_AN)
    g.san_sang(45)
    bo = Bo("18-cong-cu")

    # Ca `store.procedure_progress` cần một quy trình tồn tại trước.
    bo.phan("Dựng sẵn thứ vài ca cần tới")
    g.go("Viết giúp mình quy trình nạp firmware lên bo, ba bước, mỗi bước nói rõ lệnh chạy "
         "và dấu hiệu biết là xong.")
    g.doi_xong(400)
    bo.kiem("Có quy trình để mà báo tiến độ", "store.procedure_set" in _cong_cu(),
            str(_cong_cu()[-6:]))

    bo.phan("Giao đúng loại việc cho từng công cụ")
    for ten_cc, ten_ca, cau in CA:
        truoc = len(_cong_cu())
        try:
            g.go(cau)
            g.doi_xong(420)
        except TimeoutError:
            bo.kiem(f"`{ten_cc}` — {ten_ca}", False, "tác tử chạy quá lâu")
            continue
        sau = _cong_cu()[truoc:]
        bo.kiem(f"`{ten_cc}` — {ten_ca}", ten_cc in sau,
                "đã gọi: " + (", ".join(dict.fromkeys(sau)) or "không gọi công cụ nào"))

    # ------------------------------------------------------ vòng hai: bốn cái cần bối cảnh
    #
    # Chúng không gọi được bằng một câu đơn lẻ — phải dựng tình huống trước. Tách riêng để
    # không lẫn với vòng một, nơi mỗi ca đúng một câu.
    bo.phan("Bốn cái cần dựng bối cảnh trước")

    truoc = len(_cong_cu())
    g.go("Cho mình ba phương án cấp nguồn 3,3 V cho mạch này, so sánh bằng số.")
    g.doi_xong(420)
    g.go("Mình chọn phương án 2 nhé, chốt luôn.")
    g.doi_xong(420)
    sau = _cong_cu()[truoc:]
    bo.kiem("`store.option_choose` — người chọn một phương án",
            "store.option_choose" in sau, "đã gọi: " + ", ".join(dict.fromkeys(sau)))

    truoc = len(_cong_cu())
    g.go("Quên giúp mình cái ghi chú về đơn vị SI vừa nhớ ban nãy đi, mình đổi ý rồi.")
    g.doi_xong(420)
    sau = _cong_cu()[truoc:]
    bo.kiem("`memory.forget` — người bảo quên một điều đã ghi",
            "memory.forget" in sau, "đã gọi: " + ", ".join(dict.fromkeys(sau)))

    truoc = len(_cong_cu())
    g.go("Mình muốn làm một việc lớn: dựng trọn bộ tài liệu bàn giao phần cứng. "
         "Bạn lập kế hoạch trước đi.")
    g.doi_xong(420)
    g.go("Thôi, bỏ kế hoạch đó đi, mình đổi ý rồi, chưa làm vội.")
    g.doi_xong(420)
    sau = _cong_cu()[truoc:]
    bo.kiem("`plan.cancel` — người bỏ kế hoạch giữa chừng",
            "plan.cancel" in sau, "đã gọi: " + ", ".join(dict.fromkeys(sau)))

    truoc = len(_cong_cu())
    g.go("Mạch tới đây coi như xong giai đoạn một. Ghi giúp mình một bản ưng ý tên "
         "“nen-mong-v1” rồi chốt nó thành bản PHÁT HÀNH luôn.")
    g.doi_xong(420)
    a = g.chup("cho-duyet-release")
    for the in (a.get("the_dang_cho") or []):
        g.quyet_cong(the.get("id") or the.get("gate_id"), True, "Duyệt.")
        g.doi_xong(420)
    sau = _cong_cu()[truoc:]
    bo.kiem("`snapshot.release` — chốt bản phát hành",
            "snapshot.release" in sau, "đã gọi: " + ", ".join(dict.fromkeys(sau)))

    g.chup_man_hinh(REPO / "docs/review-v3/test/ket-qua-18/man-hinh.png", "18-cong-cu")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
