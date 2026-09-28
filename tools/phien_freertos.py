#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phiên FreeRTOS trên bo STM32F469I-DISCO — dự án THỨ HAI trên cùng một bo.

    .venv/bin/python tools/phien_freertos.py [--buoc 1-3] [--giu-du-an]

Dự án đầu (`du-lieu/stm32f469-disco`) **để nguyên**: nó là hiện vật của chặng G7, và phiên
này không được chạm vào nó.

Điều phiên này canh, khác phiên trước: ba năng lực vừa làm xong — plan mode (§B5), verifier
kiểm lời tuyên "đạt" của chính tác tử chính, và `tool.propose` — **lần đầu chạy trên việc
thật**. Kịch bản không bảo tác tử dùng cái nào; nó giao việc rồi đo xem chúng có tự nổ đúng
lúc không. Bảo trước thì phép đo mất nghĩa.

Kết quả vào `docs/stm32f469-freertos/ket-qua/`.
"""

from __future__ import annotations

import argparse
import pathlib
import shutil
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

DU_AN = REPO / "du-lieu/stm32f469-freertos"
RA = REPO / "docs/stm32f469-freertos/ket-qua"
DU_AN_CU = REPO / "du-lieu/stm32f469-disco"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu-du-an", action="store_true",
                    help="không xoá dự án cũ, chạy tiếp trên nó")
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-3 hoặc 4")
    a = ap.parse_args()

    # Hàng rào: phiên này KHÔNG được chạm dự án G7. Kiểm bằng mã thay vì bằng lời hứa —
    # `--giu-du-an` vắng mặt sẽ `rmtree` DU_AN, và một lần gõ nhầm đường dẫn là mất hiện vật.
    if DU_AN.resolve() == DU_AN_CU.resolve():
        print("DỪNG: dự án mới trùng đường dẫn với dự án G7.", file=sys.stderr)
        return 2

    from eide.config import load_dotenv
    load_dotenv()

    from phien_robot import NhatKy                 # noqa: E402

    if not a.giu_du_an:
        if DU_AN.exists():
            shutil.rmtree(DU_AN)
        if RA.exists():
            shutil.rmtree(RA)
    DU_AN.mkdir(parents=True, exist_ok=True)

    nk = NhatKy(RA, tieu_de="FreeRTOS trên bo STM32F469I-DISCO (dự án thứ hai)",
                nguon="thông tin bo đo được ở dự án G7 · FreeRTOS do tác tử tự tìm",
                du_an=str(DU_AN.relative_to(REPO)))
    from kich_ban_freertos import chay            # noqa: E402
    return chay(nk, DU_AN, chi_buoc=a.buoc)


if __name__ == "__main__":
    raise SystemExit(main())
