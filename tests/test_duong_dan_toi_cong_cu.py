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


def test_STALE_neu_CA_HAI_loi_ra(du_an):
    """`stale.accept` chưa nổ lần nào: `<inventory>` chỉ nói "cần cập nhật".

    Nhưng có thật những lần thượng nguồn đổi mà hạ nguồn vẫn đúng — đổi tên một Fact không làm
    sai một đoạn mã dùng giá trị của nó. Chỉ nêu một lối thì tác tử hoặc sửa thừa, hoặc lờ đi.
    """
    from eide.store.inventory import Inventory

    inv = Inventory(project_name="x")
    inv.stale = [{"id": "CODE-01", "type": "code", "stale_reason": "REQ-01 đổi"}]
    ra = inv.render()
    assert "stale.accept" in ra
    assert "vẫn đúng" in ra


def test_req_create_chi_duong_SUA_yeu_cau_da_co():
    """Bảng hiến pháp chỉ nói "yêu cầu người dùng nêu → `store.req_create`" và không nói gì về
    việc SỬA một yêu cầu đã có — nên `store.req_update` chưa nổ lần nào.

    Hệ quả đo được ở TC006: tác tử cập nhật cả ba phương án nhưng không ai gọi nó là "v2", vì
    nó không có đường ra bản v2 trong đầu.
    """
    from eide.tools import build_registry

    t = build_registry().get("store.req_create")
    assert "store.req_update" in t.summary_vi
    assert "ĐỪNG tạo một REQ mới" in t.summary_vi


def test_bao_nen_ngu_canh_NOI_duong_lui():
    """Một phép đảo ngược không ai biết là có thì cũng như không có."""
    from eide.memory.nen import KetQuaNen

    k = KetQuaNen(muc="C2", ok=True, truoc=9000, sau=3000, diem_kiem="3/3")
    d = k.dong_he_thong()
    assert "memory.undo_compact" in d and "24 giờ" in d
