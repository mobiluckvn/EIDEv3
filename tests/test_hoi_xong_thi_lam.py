# -*- coding: utf-8 -*-
"""Hỏi xong mà chưa làm gì thì phải được nhắc: phần nào KHÔNG phụ thuộc câu trả lời?

Đo được 29/09/2026 trên ba ca Happy của bộ usecase — TC006, TC008, TC052 — và đây là thứ
DUY NHẤT cả 76 ca nói là sai với sản phẩm. Cả ba kết thúc bằng một câu hỏi hợp lý và không
một hiện vật nào.

TC052 lộ rõ nhất: được nhờ viết unit test, tác tử đọc mã, thấy `main.c` gắn cứng thanh ghi
AVR nên không chạy được trên máy chủ, ĐỀ XUẤT ĐÚNG cách sửa (tách logic sang `control.c`),
in ra giả định sẽ dùng nếu người bỏ qua — rồi dừng. Việc tách ấy không phụ thuộc câu trả lời
nào.

Luật KHÔNG phải "hỏi ít đi" (đi ngược N4, mở đường cho đạt giả) mà là "làm phần làm được
trước, rồi hỏi phần còn lại".
"""

from __future__ import annotations

from typing import Any

from eide.hooks.base import HookBus
from eide.hooks.standard import register_standard_hooks


class _Ctx:
    """Ngữ cảnh tối thiểu cho hook Stop — chỉ những trường hook này đọc."""

    def __init__(self, goi: list[str], da_ghi: bool = False):
        self.cong_cu_da_goi = list(goi)
        self.da_ghi_gi_do = da_ghi
        self.da_nhac_rong: set[str] = set()
        # Các trường hook Stop khác đọc — đặt sao cho chúng im lặng.
        self.assumptions: list[Any] = []
        self.said_anything = True
        self.awaiting_human = False
        self.human_edits: list[Any] = []
        self.loi_da_noi: list[str] = ["xong"]
        self.da_tu_kiem = True
        self.store = None
        self.registry = None
        self.ledger = None


def _chay(ctx: Any):
    return register_standard_hooks(HookBus()).stop(ctx)


def test_hoi_ma_chua_lam_gi_thi_bi_nhac():
    r = _chay(_Ctx(["fs.glob", "fs.read", "ask_user"]))
    assert r.another_round, "lượt kết thúc bằng câu hỏi mà không để lại gì — phải nhắc"
    assert "hoi_xong_thi_lam_phan_khong_phu_thuoc" in r.fired
    t = r.injection or ""
    assert "KHÔNG phụ thuộc câu trả lời" in t
    # Cửa thoát phải nằm ngay trong lời nhắc, nếu không nó thành áp lực đẻ hiện vật rác.
    assert "hợp lệ" in t and "đừng tạo một hiện vật cho có" in t


def test_da_ghi_duoc_gi_do_thi_khong_nhac():
    """Hỏi mà vẫn làm được việc thì không có gì để nhắc."""
    r = _chay(_Ctx(["fs.read", "store.req_create", "ask_user"], da_ghi=True))
    assert "hoi_xong_thi_lam_phan_khong_phu_thuoc" not in r.fired


def test_khong_hoi_thi_khong_nhac():
    """Luật này chỉ canh lượt KẾT THÚC BẰNG CÂU HỎI, không canh mọi lượt không ghi gì.

    Một lượt chỉ đọc và trả lời (“dự án này đang ở đâu?”) là hợp lệ và thường xuyên — bắt nó
    phải đẻ ra hiện vật là ép làm cho có.
    """
    r = _chay(_Ctx(["fs.glob", "ledger.query"]))
    assert "hoi_xong_thi_lam_phan_khong_phu_thuoc" not in r.fired


def test_chi_nhac_dung_mot_lan_moi_luot():
    """Nhắc vòng hai là ép làm cho có — tác tử đã nghe và đã quyết."""
    c = _Ctx(["ask_user"])
    assert _chay(c).another_round
    r2 = _chay(c)
    assert "hoi_xong_thi_lam_phan_khong_phu_thuoc" not in r2.fired


def test_trich_lai_chinh_cau_tac_tu_vua_noi():
    """Lời nhắc chung chung nổ đúng lúc nhưng KHÔNG đổi hành vi — đo được ở TC052.

    Tác tử nhận nhắc rồi chỉ hỏi lại một câu gọn hơn. Mà ngay trong thẻ nó vừa dựng đã có
    câu trả lời: *"nếu anh bỏ qua, em sẽ tách logic sang control.c rồi chạy test"*. Chỉ vào
    đúng câu ấy thì việc cần làm hết mơ hồ — và không phải ai áp đặt một việc mới, đó là
    việc chính nó vừa chọn.
    """
    class _SoCai:
        class _Ev:
            kind = "tool_use"
            data = {"tool": "ask_user", "run_id": "run-9",
                    "args": {"assumption_if_skipped": "tách logic sang control.c rồi chạy test"}}

        def read(self):
            return [self._Ev()]

    c = _Ctx(["fs.read", "ask_user"])
    c.ledger = _SoCai()
    c.run_id = "run-9"
    r = _chay(c)
    assert r.another_round
    t = r.injection or ""
    assert "tách logic sang control.c" in t, "phải trích lại chính lời tác tử vừa viết"
    assert "hoàn tác được" in t, "phải nhắc rằng làm rồi vẫn lùi được — đó là lý do dám làm"


def test_khong_co_gia_dinh_thi_van_nhac_duoc():
    """Không có câu "nếu bỏ qua" thì lời nhắc vẫn dùng được, chỉ kém sắc hơn."""
    r = _chay(_Ctx(["ask_user"]))
    assert r.another_round and "KHÔNG phụ thuộc câu trả lời" in (r.injection or "")
