# -*- coding: utf-8 -*-
"""Thư mục dự án phải CHÉP ĐI ĐƯỢC, và phải tự nói nó là gì.

Toàn bộ một dự án EIDE nằm trong đúng một thư mục, nên chép thư mục là chuyển cả dự án. Hai
điều phải đúng thì câu ấy mới thật:

1. **Không hiện vật nào ghim đường dẫn tuyệt đối.** Đo được 29/09/2026: `target.screen` ghi
   `view_hint.path` bằng đường dẫn tuyệt đối — chép sang máy khác thì ảnh không mở được. Đây
   là chỗ duy nhất trong kho làm vậy; 169 chỗ còn lại nằm trong kết quả công cụ (chỉ lộ bố
   cục máy cũ, không ai đọc để chạy).
2. **Thư mục tự nói nó là gì.** Người cầm thư mục phải biết đây là dự án EIDE bản nào, đang ở
   đâu, và — câu đắt nhất — **chép đi thì phải mang theo cái gì**. Thư mục đo được hôm ấy
   14,5 MB mà 3,0 MB là `.eide/build/`, dựng lại được.
"""

from __future__ import annotations

import json
import pathlib

from eide.du_an import TEN_TEP, ThongTinDuAn, bo_duoc, can_chep


def _du_an(tmp_path) -> pathlib.Path:
    from eide.config import Config
    from eide.llm.offline import ScriptedGateway
    from eide.loop import Agent

    d = tmp_path / "du-an"
    d.mkdir()
    Agent(Config.for_project(d), llm=ScriptedGateway([]), project_name="thu")
    return d


def test_mo_du_an_la_co_the_can_cuoc(tmp_path):
    """Mở dự án — kể cả mở rồi đóng ngay — là phải có `du-an.json`."""
    d = _du_an(tmp_path)
    p = d / TEN_TEP
    assert p.exists(), "thư mục nhìn từ ngoài vẫn là một mớ không tên"
    o = json.loads(p.read_text("utf-8"))
    assert o["eide"]["luoc_do"] >= 1
    assert o["du_an"]["ten"] == "thu"
    assert o["lich_su"]["su_kien"] >= 0


def test_phan_hang_du_lieu_nam_trong_chinh_tep(tmp_path):
    """Phân hạng phải ở trong tệp, không ở trong đầu người viết công cụ sao lưu."""
    d = _du_an(tmp_path)
    o = json.loads((d / TEN_TEP).read_text("utf-8"))
    hang = {m["hang"] for m in o["du_lieu"]["muc"]}
    assert "ben" in hang, "không mục nào được đánh dấu là BỀN"
    # Ba thứ mất là mất hẳn.
    duong = {m["duong"] for m in o["du_lieu"]["muc"] if m["hang"] == "ben"}
    for x in (".eide/ledger.jsonl", ".eide/store.sqlite", "EIDE.md"):
        assert x in duong, f"{x} phải được đánh dấu BỀN"
    assert o["chep_di_the_nao"], "phải nói ra cách chép, không để người đoán"


def test_can_chep_va_bo_duoc_khong_giao_nhau(tmp_path):
    """Một đường dẫn không thể vừa phải-mang-theo vừa bỏ-được. Nếu giao nhau thì người đọc
    hai danh sách sẽ ra hai kết luận ngược nhau về cùng một thư mục."""
    d = _du_an(tmp_path)
    (d / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (d / ".eide" / "build" / "mach.bin").write_bytes(b"\x00" * 2048)
    phai = set(can_chep(d))
    bo = {x for x, _ in bo_duoc(d)}
    assert ".eide/ledger.jsonl" in phai, (
        "danh sách phải-mang-theo là một HỢP ĐỒNG, không phải ảnh chụp hiện trạng — "
        "sổ cái chưa được ghi lần nào vẫn phải có tên trong đó")
    assert not (phai & bo), f"giao nhau: {phai & bo}"
    assert ".eide/build" in bo
    assert dict(bo_duoc(d))[".eide/build"] >= 2048, "phải nói TIẾT KIỆM ĐƯỢC BAO NHIÊU, để "\
        "người quyết bằng số chứ không bằng cảm giác"


def test_khong_hien_vat_nao_ghim_duong_dan_tuyet_doi(tmp_path):
    """`view_hint.path` phải là đường dẫn tương đối so với gốc dự án."""
    import inspect

    from eide.tools import mach_that

    src = inspect.getsource(mach_that)
    i = src.find('"kind": "image"')
    assert i > 0, "không tìm thấy chỗ ghi view_hint ảnh — đọc lại ca kiểm này"
    doan = src[i:i + 400]
    assert "relative_to" in doan, (
        "view_hint ghi đường dẫn tuyệt đối — chép dự án sang máy khác thì ảnh không mở được")
