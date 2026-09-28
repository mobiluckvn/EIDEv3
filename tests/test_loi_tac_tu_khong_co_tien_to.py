# -*- coding: utf-8 -*-
"""Lời tác tử không được mang tiền tố `[Tác tử] ` chèn trong chữ.

Đo được ngày 28/09/2026 bằng bộ quét giao diện: lời đáp của tác tử mở đầu bằng một tiêu đề
Markdown, và trên màn hình người dùng đọc thấy nguyên hai dấu thăng:

    [Tác tử] ## Kết quả chạy kiểm thử và đo độ nhạy bộ kiểm

Bộ dựng Markdown nhận tiêu đề bằng `dòng bắt đầu bằng "#"`. Chèn `[Tác tử] ` vào đầu dòng ấy
làm nó không còn bắt đầu bằng `#`, nên khối đầu tiên của MỌI lời đáp có tiêu đề đều hiện ra ở
dạng thô.

Và tiền tố ấy vốn đã thừa: `ConsoleView` in nhãn vai (**BẠN** / **TÁC TỬ**) ở cột trái cho
từng dòng. Người dùng đọc tên người nói hai lần, trong đó một lần làm hỏng cách trình bày.

Bỏ nó đi sửa cả một LỚP lỗi chứ không một chỗ: mọi khối mở đầu — tiêu đề, trích dẫn, gạch
đầu dòng, bảng, khối mã — đều bị cùng một kiểu.
"""

from __future__ import annotations

import pathlib
import re

GOC = pathlib.Path(__file__).resolve().parents[1] / "src" / "eide"


def test_khong_con_cho_nao_chen_tien_to_vao_loi_tac_tu():
    """Quét cả mã nguồn, không chỉ một tệp — nó đã nằm rải ở 21 chỗ thuộc 4 tệp."""
    dinh = []
    for p in GOC.rglob("*.py"):
        for i, dong in enumerate(p.read_text("utf-8").splitlines(), 1):
            if "[Tác tử]" in dong:
                dinh.append(f"{p.relative_to(GOC)}:{i}")
    assert not dinh, ("còn chèn tiền tố vai vào chữ — nhãn vai đã có ở cột trái của "
                      f"Console, và tiền tố này làm hỏng khối Markdown đầu tiên: {dinh}")


def test_bo_dung_markdown_nhan_tieu_de_o_dau_dong():
    """Ghim lại LÝ DO: bộ dựng nhận tiêu đề bằng dòng bắt đầu bằng `#`.

    Nếu một ngày nó đổi cách nhận (ví dụ cho phép khoảng trắng trước), bài kiểm trên vẫn
    đúng nhưng lý do của nó thì không — và ca này sẽ nhắc người sửa đọc lại.
    """
    md = (pathlib.Path(__file__).resolve().parents[1]
          / "ui/EIDEApp/Sources/EIDE/Views/Markdown.swift")
    if not md.exists():
        return
    t = md.read_text("utf-8")
    assert re.search(r'hasPrefix\("#"\)', t), (
        "Markdown.swift không còn nhận tiêu đề bằng `hasPrefix(\"#\")` — đọc lại "
        "test_khong_con_cho_nao_chen_tien_to_vao_loi_tac_tu xem lý do còn đúng không")
