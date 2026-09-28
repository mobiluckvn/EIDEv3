# -*- coding: utf-8 -*-
"""Tài liệu thiết kế không được nói khác mã.

Bộ dò `tools/kiem_tai_lieu.py` đối chiếu bốn thứ KIỂM ĐƯỢC BẰNG MÁY giữa tài liệu và mã: tên
công cụ · đường dẫn · mã lỗi · con số đếm được. Ca kiểm này gọi nó trong hồi quy, để tài liệu
không trôi khỏi mã một cách lặng lẽ.

Vì sao đáng một ca kiểm chứ không phải một việc nhớ làm định kỳ: tài liệu thiết kế của dự án
dài hơn 8000 dòng. Đọc tay thì mỗi lần sửa mã phải đọc lại tất cả, nên thực tế là không ai đọc
lại. Một con số sai trong tài liệu thiết kế tệ hơn không có con số — nó **nghe hợp lý**, không
ai kiểm, và nó làm mọi con số khác cùng trang mất giá. README từng ghi `836 test` khi thực tế
đã là 1231 (DEV-292).

Ca này chỉ canh phần máy kiểm được. Phần "tài liệu mô tả ĐÚNG cách hệ thống hoạt động không"
thì vẫn phải đọc, và nói ra giới hạn ấy còn hơn để một ô xanh nói hộ.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]


def test_khong_co_cho_nao_tai_lieu_noi_khac_ma():
    r = subprocess.run([sys.executable, str(REPO / "tools/kiem_tai_lieu.py")],
                       capture_output=True, text=True, cwd=str(REPO))
    assert r.returncode == 0, (
        "tài liệu nói khác mã — tên công cụ, đường dẫn hoặc mã lỗi không còn tồn tại:\n"
        + r.stdout[-3000:])
