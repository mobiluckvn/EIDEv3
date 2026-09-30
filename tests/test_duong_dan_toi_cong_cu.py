# -*- coding: utf-8 -*-
"""Công cụ có mà tác tử không nhìn thấy thì đúng bằng không có.

Đo ngày 30/09/2026 trên toàn bộ sổ cái của mọi dự án trong `du-lieu/`: **31 trên 120 công cụ
chưa nổ lần nào**, và 25 trong số đó là `core=False` — tức chỉ hiện ra sau một lần
`tool.search`, mà tác tử chỉ tìm khi nó biết có thứ để tìm.

Đây là hình dạng lỗi lặp lại nhiều nhất trong dự án này: verifier chạy 0/402 lượt · `task.run`
bị hook bảo gọi mà không mở khoá · `tool.propose` chưa từng nổ · `plan.step_done` không ai gọi
dù kế hoạch nằm ngay trước mặt (DEV-302, DEV-305).

Ba ca dưới đây khoá ba đường dẫn vừa nối lại. Ca thứ tư ghi lại một chỗ **KHÔNG phải lỗi**, để
lần sau không ai đi sửa nhầm.
"""

from __future__ import annotations

import time

import pytest


@pytest.fixture
def agent(make_agent):
    return make_agent([])


def test_skill_load_LUON_nhin_thay_duoc(agent):
    """8 skill hiện tên trong `<skills-hint>` mỗi lượt, mà công cụ nạp chúng thì tác tử không
    nhìn thấy. Đo được **0 lần nạp** trong toàn bộ lịch sử chạy.

    Gợi ý một danh mục rồi giấu cái nút mở nó đi thì danh mục ấy chỉ tốn token.
    """
    assert agent.registry.get("skill.load").core is False, \
        "vẫn để core=False — nên phải mở khoá theo ngữ cảnh"
    agent._mo_khoa_theo_ngu_canh()
    assert "skill.load" in agent.registry._unlocked


def test_undo_30s_chi_hien_KHI_CON_trong_cua_so(agent):
    """Menu ⌥⌘Z gửi câu *“Hoàn tác việc bạn vừa làm giúp mình”*. Lúc ấy tác tử chỉ thấy
    `history.undo` (R2, cổng G-HIST) nên nó dựng thẻ cổng cho một việc lẽ ra lùi được ngay —
    đúng thứ cửa sổ 30 giây sinh ra để tránh.

    Nhưng chỉ mở khi CÒN trong cửa sổ: hết 30 giây thì công cụ ấy chỉ trả lỗi, và một công cụ
    luôn hiện mà luôn hỏng là một công cụ dạy người ta bỏ qua nó.
    """
    agent.thoi_diem_ket_thuc.clear()
    agent._mo_khoa_theo_ngu_canh()
    assert "history.undo_30s" not in agent.registry._unlocked

    agent.thoi_diem_ket_thuc["run-1"] = time.time()
    agent._mo_khoa_theo_ngu_canh()
    assert "history.undo_30s" in agent.registry._unlocked

    agent.registry._unlocked.discard("history.undo_30s")
    agent.thoi_diem_ket_thuc["run-1"] = time.time() - 60      # quá hạn
    agent._mo_khoa_theo_ngu_canh()
    assert "history.undo_30s" not in agent.registry._unlocked


def test_hang_doi_ra_soat_Fact_NOI_CACH_xac_nhan():
    """`fact.review` là đường DUY NHẤT để một Fact lên VÀNG, và nó **chưa nổ lần nào** — nghĩa
    là chưa Fact nào từng thành VÀNG.

    Công cụ ấy `core=True` nên tác tử vẫn nhìn thấy; chỗ đứt nằm ở phía NGƯỜI: khối rà soát
    báo có hàng đợi rồi để họ tự đoán phải làm gì. Một hàng đợi không nói cách xử lý là một
    hàng đợi không ai xử lý.
    """
    from eide.surfaces import knowledge

    class _Kho:
        def get(self, *a, **k):
            return None

        def list(self, *a, **k):
            return []

        def query_facts(self, limit=300):
            return [{"fact_id": "FACT-07", "subject": "MT-01", "key": "vdd_max",
                     "value": "3.6", "unit": "V", "tier": "BAC", "cite": {},
                     "doc_id": "DOC-1", "page": 9, "quote": "VDD max 3.6 V"}]

    class _Inv:
        fact_tiers = {"BAC": 1}
        passport = None
        isa = None

    m = knowledge(_Kho(), _Inv())
    kh = {b["id"]: b for b in m["blocks"]}
    assert "A4.2b" in kh
    s = kh["A4.2b"]["summary"]
    assert "fact.review" in s, "không nói tên công cụ sẽ chạy"
    assert "FACT-07" in s, "không nói câu cụ thể người dùng gõ được"


def test_ledger_verify_KHONG_phai_duong_dut(du_an):
    """Ghi lại một chỗ **KHÔNG phải lỗi**, để lần sau không ai sửa nhầm.

    Công cụ `ledger.verify` chưa nổ lần nào — nhưng *cơ chế* thì chạy liên tục: bề mặt Nhật ký
    gọi `ledger.verify()` mỗi lần vẽ lại, `du-an.json` ghi kết quả mỗi lần mở dự án, và
    `goi_du_an.nhap()` kiểm trước khi trả về. Công cụ chỉ là lối thoát hiểm thủ công.

    *Số lần chạy bằng 0 là một phát hiện, không phải một kết luận* — phải hỏi tiếp cơ chế ấy
    có đường nào khác để nổ không.
    """
    import inspect

    from eide import surfaces

    assert "ledger.verify()" in inspect.getsource(surfaces.journal)
