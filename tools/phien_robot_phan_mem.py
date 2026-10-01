#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Một phiên làm việc THẬT: phần mềm giúp robot hai bánh tự đứng cân bằng.

    .venv/bin/python tools/phien_robot_phan_mem.py [--buoc 1-3]

Khác `phien_robot.py` ở **phạm vi**: bài kia dựng phần cứng (sơ đồ khối, netlist, bố trí);
bài này viết **phần mềm điều khiển**, từ đọc tài liệu bàn giao tới mô phỏng chạy được.

Đề bài do anh Công giao, nguyên văn:

> đọc tài liệu về Robot tự cân bằng trong thư mục robot, tạo dự án robot rồi phân tích và
> thiết kế cho phần mềm giúp robot đứng cân bằng. Thao tác cần có quy trình cài đặt như thế
> nào, ví dụ: bật nguồn led nháy, còi kêu rồi sau đó bấm nút thì … rồi tự đứng. Quá trình sẽ
> là phân tích, thiết kế, code, mô phỏng. Sau khi mô phỏng okay báo mình cắm mạch để nạp.

## Vì sao tài liệu này KHÔNG cho sẵn lời giải

Phụ lục B.1 của hồ sơ bàn giao ghi rõ đã **lược bỏ** toàn bộ phần ứng dụng tham chiếu: vòng
điều khiển cân bằng, ước lượng góc bằng lọc bù, chốt mốc thăng bằng, PID. Tài liệu chỉ còn
**ràng buộc phần cứng** — chân, thanh ghi, định thời, cấu trúc bị cấm.

Nghĩa là tác tử không thể chép lời giải ra; nó phải tự thiết kế vòng điều khiển **bên trong**
những ràng buộc ấy. Đó đúng là thứ phiên này đo.

## Ghi log

Chạy lõi với `EIDE_GHI_LLM=1`, nên mỗi lời gọi mô hình để lại **nguyên văn gửi đi và nguyên
văn trả về** ở `<dự án>/.eide/llm/`. Cộng với sổ cái, transcript và ảnh chụp cửa sổ, cả phiên
dựng lại được từ đầu mà không cần tin vào bản tóm tắt nào.
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

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from phien_robot import NhatKy, cong_cu_da_goi, hoi, so_dong_so_cai   # noqa: E402
from thu_giao_dien import GiaoDien                                     # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

DU_AN = REPO / "du-lieu/robot-tu-can-bang"
RA = REPO / "du-lieu/ket-qua/robot-phan-mem"
TAI_LIEU = REPO / "docs/robot/MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx"


def mo_app(du_an: pathlib.Path) -> GiaoDien:
    """Mở app, bật ghi nhật ký LLM.

    Gọi thẳng tệp nhị phân chứ không `open -a`: LaunchServices không mang biến môi trường của
    vỏ lệnh sang, mà `EIDE_GHI_LLM` phải tới được lõi — nó là tiến trình con của app.
    """
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    het = time.time() + 20
    while time.time() < het:
        if subprocess.run(["pgrep", "-f", "EIDE.app/Contents/MacOS/EIDE"],
                          capture_output=True).returncode != 0:
            break
        time.sleep(0.5)
    time.sleep(1.0)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(du_an)], check=True)
    g = GiaoDien(du_an)
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env={**os.environ, "EIDE_GHI_LLM": "1"},
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(90)
    return g


# ===================================================================== các bước
#
# Mỗi bước là MỘT câu người dùng gõ, viết như anh Công sẽ gõ thật: nói việc cần, không nhắc
# tên công cụ. Nhắc tên công cụ là mớm bài, và mớm bài thì đo chính lời mớm.
BUOC: list[tuple[str, str, int]] = [
    ("Đọc tài liệu bàn giao",
     "Mình vừa đưa vào dự án tệp hồ sơ bàn giao phần cứng của con robot hai bánh tự cân "
     "bằng. Bạn đọc kỹ giúp mình rồi tóm tắt: robot có những khối gì, vi điều khiển nào, "
     "cảm biến gì, lái động cơ ra sao, và có những ngoại vi báo hiệu nào. Nói rõ chỗ nào "
     "tài liệu đã chốt cứng mà phần mềm không đổi được.", 900),

    ("Chốt đặc tả yêu cầu phần mềm",
     "Giờ mình cần đặc tả yêu cầu cho PHẦN MỀM giúp robot đứng cân bằng. Yêu cầu của mình: "
     "bật nguồn thì đèn nháy báo đang khởi động, còi kêu báo đã sẵn sàng; người đặt robot "
     "nằm yên để nó tự hiệu chuẩn; bấm nút thì nó vào chế độ cân bằng; dựng robot lên qua "
     "điểm thăng bằng rồi thả tay thì nó tự đứng. Ngã quá nghiêng thì phải tự tắt động cơ "
     "cho an toàn, và bấm nút lần nữa thì dừng hẳn. Bạn ghi thành đặc tả có tiêu chí đo "
     "được, kèm cả các ràng buộc thời gian thực mà tài liệu đã bắt buộc.", 900),

    ("Ba phương án kiến trúc, rồi chốt một",
     "Với đặc tả đó, bạn nêu cho mình ba phương án kiến trúc phần mềm khác nhau, so sánh "
     "bằng số: cách ước lượng góc nghiêng, cách tổ chức vòng điều khiển, cách sinh xung "
     "bước, tốn bao nhiêu RAM và bao nhiêu phần trăm CPU trong ngân sách của ATmega328P. "
     "Nói rõ rủi ro từng phương án rồi đề xuất một cái, mình sẽ duyệt.", 900),

    ("Thiết kế máy trạng thái khởi động",
     "Chốt phương án đó nhé. Giờ thiết kế chi tiết cho mình QUY TRÌNH VẬN HÀNH dưới dạng "
     "máy trạng thái: từ lúc bật nguồn, đèn nháy thế nào, còi kêu lúc nào và mấy tiếng, "
     "hiệu chuẩn bao lâu, bấm nút thì chuyển trạng thái nào, điều kiện nào thì vào cân "
     "bằng, điều kiện nào thì ngã và tắt động cơ. Vẽ sơ đồ trạng thái cho mình xem, ghi rõ "
     "mỗi chuyển trạng thái do sự kiện gì và mất bao lâu.", 900),

    ("Chia việc rồi viết mã",
     "Thiết kế ổn rồi. Bạn lập kế hoạch chia việc viết mã, rồi viết firmware cho "
     "ATmega328P theo đúng thiết kế ấy — tách mô-đun rõ ràng, tuân thủ các ràng buộc thời "
     "gian thực và những cấu trúc bị cấm mà tài liệu đã nêu.", 1800),

    ("Biên dịch",
     "Biên dịch giúp mình xem có lỗi gì không, và cho mình biết firmware chiếm bao nhiêu "
     "Flash và bao nhiêu RAM so với giới hạn của chip.", 900),

    ("Tiêu chí mô phỏng — nêu TRƯỚC khi chạy",
     "Trước khi mô phỏng, bạn nêu tiêu chí nghiệm thu bằng số: thế nào là vòng điều khiển "
     "chạy đúng nhịp, thế nào là robot đứng được, thế nào là phát hiện ngã kịp. Nêu tiêu "
     "chí trước đã, đừng chạy vội.", 900),

    ("Mô phỏng",
     "Giờ chạy mô phỏng đối chiếu với đúng những tiêu chí vừa nêu, rồi báo cho mình từng "
     "tiêu chí đạt hay không đạt và vì sao.", 1800),
]


def dung_du_an(giu: bool) -> None:
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    (DU_AN / ".eide" / "ui-test").mkdir(parents=True, exist_ok=True)
    (DU_AN / "tai-lieu").mkdir(exist_ok=True)
    dich = DU_AN / "tai-lieu" / TAI_LIEU.name
    if not dich.exists():
        shutil.copy(TAI_LIEU, dich)


def chay(buoc_chon: set[int] | None, giu: bool) -> int:
    from eide.config import load_dotenv

    load_dotenv()
    dung_du_an(giu)
    nk = NhatKy(RA, tieu_de="phần mềm robot hai bánh tự cân bằng",
                nguon=str(TAI_LIEU.relative_to(REPO)),
                du_an=str(DU_AN.relative_to(REPO)))
    g = mo_app(DU_AN)

    for i, (ten, cau, giay) in enumerate(BUOC, 1):
        if buoc_chon and i not in buoc_chon:
            continue
        nk.buoc(f"{ten}")
        hoi(g, nk, DU_AN, cau, giay=giay)
        nk.anh(g, ten.lower().replace(" ", "-")[:28])

    # Nhật ký LLM: đếm và nói ra, để phần "ghi log đầy đủ" có con số kiểm được.
    llm = sorted((DU_AN / ".eide" / "llm").glob("*.jsonl"))
    n = sum(1 for p in llm for d in p.read_text("utf-8", errors="replace").splitlines()
            if d.strip())
    nk.ghi("Nhật ký lời gọi mô hình",
           f"{len(llm)} tệp · {n} lời gọi, mỗi lời gọi kèm nguyên văn gửi đi và trả về "
           f"({DU_AN / '.eide' / 'llm'})")
    print(f"\n{VANG}Nhật ký: {nk.md}{HET}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-3 hoặc 4")
    ap.add_argument("--giu-du-an", action="store_true", help="không xoá dự án cũ")
    a = ap.parse_args()
    chon: set[int] | None = None
    if a.buoc:
        chon = set()
        for phan in a.buoc.split(","):
            if "-" in phan:
                x, y = phan.split("-", 1)
                chon |= set(range(int(x), int(y) + 1))
            else:
                chon.add(int(phan))
    return chay(chon, a.giu_du_an)


if __name__ == "__main__":
    raise SystemExit(main())
