# -*- coding: utf-8 -*-
"""Bề mặt không được đổ giá trị máy ra màn hình.

Đo được 29/09/2026 bằng bộ quét giao diện: khối `sim_result:can-bang` hiện nguyên một danh
sách dict Python — `[{'ten': 'A1 khoi tao…', 'dat': True, …}]`. Chỗ hỏng là một dòng dựng bảng
gọi `str(v)` cho MỌI giá trị: vô hướng thì đẹp, có cấu trúc thì lộ nguyên ruột.

Đây đúng thứ N8 cấm — *mọi thứ tác tử làm ra phải có dạng người hiểu được*. Một dòng
`{'do_duoc': False, 'vi_sao': '…'}` không phải một dạng người hiểu được; nó là dạng máy bị bỏ
quên trên đường ra màn hình.

Đáng chú ý: lỗi này chỉ lộ ra khi dự án CÓ kết quả mô phỏng. Nó nằm im suốt nhiều chặng vì
không ai chạy bộ quét trên một dự án đủ đầy — bộ quét chạy thì xanh, vì chẳng có gì để đổ.
"""

from __future__ import annotations

from eide.surfaces import _loi_nguoi


def test_danh_sach_ca_kiem_noi_BAO_NHIEU_DAT():
    """Câu người đọc muốn biết không phải "có một danh sách", mà là "bao nhiêu đạt"."""
    v = [{"ten": "A1", "dat": True}, {"ten": "A2", "dat": False}, {"ten": "A3", "dat": True}]
    assert _loi_nguoi(v) == "2/3 đạt"


def test_khong_bao_gio_tra_ve_dang_python_tho():
    """Đây là phép kiểm chính: không dấu vết nào của `repr` lọt ra màn hình."""
    mau = [
        [{"ten": "A1", "dat": True}],
        {"do_duoc": False, "vi_sao": "không có llvm-cov"},
        {"long": {"sau": [1, 2, 3]}},
        [[1, 2], [3, 4]],
        [{"khong_co_dat": 1}],
    ]
    for v in mau:
        ra = _loi_nguoi(v)
        assert "{'" not in ra and "[{" not in ra and "': " not in ra, f"{v!r} → {ra!r}"


def test_o_trong_noi_la_trong_chu_khong_noi_None():
    for v in (None, [], {}, ()):
        assert _loi_nguoi(v) == "—"


def test_gia_tri_vo_huong_giu_nguyen():
    """Cái phanh không được làm hỏng đường đi đúng."""
    assert _loi_nguoi("8/8 ca đạt") == "8/8 ca đạt"
    assert _loi_nguoi(42) == "42"
    assert _loi_nguoi(3.5) == "3.5"
    assert _loi_nguoi(True) == "có" and _loi_nguoi(False) == "không"


def test_danh_sach_chuoi_noi_ra_tung_cai():
    assert _loi_nguoi(["test/test_ui.c", "firmware/ui_state.c"]) == \
        "test/test_ui.c, firmware/ui_state.c"
