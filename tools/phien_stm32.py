#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Một phiên làm việc THẬT trên bo STM32F469I-DISCO đang cắm vào máy.

    .venv/bin/python tools/phien_stm32.py [--buoc 1-3] [--giu-du-an]

Không phải bộ kiểm. Nó đóng vai anh Công ngồi trước EIDE và làm một dự án bo thật từ đầu tới
cuối: tạo dự án → tác tử TỰ TÌM tài liệu và nạp → trích Fact chân → ghim chip → viết firmware
→ biên dịch → nạp vào bo → đọc log để xác nhận chương trình đang chạy thật.

Điều phiên này canh, và là lý do nó tồn tại tách khỏi `tools/thu_*.py`: **mọi câu "xong" phải
có một hiện vật đứng sau.** Nạp xong thì phải có hash và số byte; chạy được thì phải có log do
bo in ra, hoặc một câu nói thẳng là chưa đo được.

Kết quả vào `docs/stm32f469/ket-qua/`:

    NHAT-KY.md          nhật ký người đọc — từng câu, từng công cụ, từng lỗi và cách sửa
    buoc.jsonl          cùng nội dung ở dạng máy đọc, để so hai lần chạy bằng mã
    anh/NN-<tên>.png    ảnh cửa sổ EIDE ở từng mốc (app tự render, KHÔNG screencapture)
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

DU_AN = REPO / "du-lieu/stm32f469-disco"
RA = REPO / "docs/stm32f469/ket-qua"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu-du-an", action="store_true",
                    help="không xoá dự án cũ, chạy tiếp trên nó")
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-3 hoặc 4")
    a = ap.parse_args()

    from eide.config import load_dotenv
    load_dotenv()

    from phien_robot import NhatKy                 # noqa: E402  (dùng lại nguyên lớp)

    # Hàng rào thứ hai, thêm sau khi nó đã cắn: `--buoc 20` nghĩa là "chạy tiếp bước 20 của
    # phiên đang có", nhưng mặc định lại là `rmtree` — nên câu lệnh đọc như "chạy tiếp" mà
    # làm việc "xoá sạch". Tôi đã mất `test/test_ui.c` của tác tử đúng theo cách ấy. Hai cờ
    # này nói ngược nhau thì phải DỪNG và bắt gõ rõ, đừng đoán hộ.
    if a.buoc and not a.giu_du_an and DU_AN.exists():
        print("DỪNG: `--buoc` là chạy tiếp một phiên đang có, nhưng thiếu `--giu-du-an` thì "
              f"{DU_AN} sẽ bị XOÁ SẠCH.\n"
              "  · chạy tiếp:  --buoc ... --giu-du-an\n"
              "  · làm lại từ đầu: bỏ --buoc, hoặc tự xoá thư mục trước.", file=sys.stderr)
        return 2

    if not a.giu_du_an:
        if DU_AN.exists():
            shutil.rmtree(DU_AN)
        if RA.exists():
            shutil.rmtree(RA)
    DU_AN.mkdir(parents=True, exist_ok=True)

    nk = NhatKy(RA, tieu_de="bo STM32F469I-DISCO (mạch thật)",
                nguon="bo thật cắm vào máy · tài liệu do tác tử tự tìm",
                du_an=str(DU_AN.relative_to(REPO)))
    from kich_ban_stm32 import chay                # noqa: E402
    return chay(nk, DU_AN, chi_buoc=a.buoc)


if __name__ == "__main__":
    raise SystemExit(main())
