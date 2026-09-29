# -*- coding: utf-8 -*-
"""Đưa tài liệu vào cho tác tử: kéo–thả và nút ghim giấy.

## Vì sao đường này phải CHÉP tệp chứ không gửi đường dẫn

Hộp cát của tác tử là **thư mục dự án**. Một tệp ở `~/Downloads` với nó là không tồn tại —
`fs.read` từ chối, `doc.load` từ chối. Nên "đưa tài liệu vào" là chép tệp vào trong dự án rồi
mới nói tên, không phải đưa một đường dẫn tuyệt đối rồi mong nó đọc được.

Trước chặng này, cách duy nhất để đưa một datasheet vào là mở Finder chép tay rồi gõ bảo tác
tử. Mà cả sản phẩm dựng trên *"mọi con số truy về datasheet"* — chỗ **đưa datasheet vào**
không nên là chỗ khó nhất.

Phần Swift (`ThemTaiLieu`) không chạy được từ pytest, nên ca ở đây canh **hợp đồng phía lõi**:
`upload` phải là một HumanAct hợp lệ, phải mang `files`, và phải tới được mô hình thành một
câu đọc được. Phần kéo–thả đo qua GIAO DIỆN THẬT bằng lệnh `them_tai_lieu` của kênh kiểm —
xem DEV-297 để biết số đo.
"""

from __future__ import annotations

import pytest

from eide.protocol.humanact import HUMAN_ACT_KINDS, HumanAct


def test_upload_la_mot_loai_HumanAct_hop_le():
    assert "upload" in HUMAN_ACT_KINDS


def test_upload_bat_buoc_co_danh_sach_tep():
    """Thiếu `files` thì act này không nói gì cả — một cú kéo–thả rỗng."""
    from eide.protocol.humanact import ensure

    with pytest.raises(Exception):
        ensure({"kind": "upload", "data": {}, "origin": {"surface": "console"}})


def test_upload_toi_duoc_mo_hinh_thanh_mot_cau_doc_duoc():
    """Lõi dựng lời người dùng bằng `act.text or act.transcript_line()`.

    `upload` không có `text`, nên nếu `transcript_line()` không dựng được câu thì mô hình
    nhận một chuỗi rỗng và cú kéo–thả trôi đi trong im lặng.
    """
    a = HumanAct.from_dict({
        "kind": "upload",
        "data": {"files": ["tai-lieu/rm-spi.md", "tai-lieu/so-do.pdf"]},
        "origin": {"surface": "console"}})
    dong = a.transcript_line()
    assert "tai-lieu/rm-spi.md" in dong and "tai-lieu/so-do.pdf" in dong
    assert dong.strip(), "mô hình sẽ nhận một chuỗi rỗng"


def test_duong_dan_gui_di_phai_TUONG_DOI():
    """Đường dẫn tuyệt đối vô dụng với tác tử, và nó còn ghim bố cục máy vào sổ cái.

    Canh ở phía Swift: `ThemTaiLieu.dua` cắt tiền tố gốc dự án.
    """
    import pathlib

    p = pathlib.Path("ui/EIDEApp/Sources/EIDE/State/ThemTaiLieu.swift")
    if not p.exists():
        pytest.skip("không có mã giao diện")
    t = p.read_text("utf-8")
    assert "dropFirst" in t, "phải cắt tiền tố gốc dự án để ra đường dẫn tương đối"
    assert "_tenKhongDe" in t, (
        "phải có phép đặt tên không đè: người kéo nhầm một tệp trùng tên mà mất bản cũ thì "
        "cú kéo ấy đắt hơn nhiều so với một tệp thừa")
