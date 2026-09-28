# -*- coding: utf-8 -*-
"""`store.option_choose` không được gán "NGƯỜI QUYẾT" cho một câu người dùng không hề chọn gì.

Đo được ngày 28/09/2026, ca TC004 của bộ usecase gốc. Người dùng gõ đúng một câu:

    Làm cho mình cái mạch thông minh.

Tác tử gọi:

    store.option_choose {"quyet_boi": "nguoi",
                         "trich_loi_nguoi": "Làm cho mình cái mạch thông minh."}

rồi tuyên **"Đã chốt kiến trúc — ADR-01"**.

Câu ấy không nhắc phương án nào và không có chữ nào mang nghĩa lựa chọn. Nhưng ADR sinh ra sẽ
vĩnh viễn nói rằng *người dùng đã quyết*, kèm trích dẫn — mà `NGUOI` là tầng tin cậy **cao
nhất**, thứ mọi quyết định sau đó dựa vào mà không kiểm lại.

Đây là **giả mạo xuất xứ**, không phải lỗi trình bày. Nó vi phạm N1 theo cách tệ nhất: nguồn
CÓ THẬT (người dùng có nói câu đó) nhưng KHÔNG nói điều được gán cho nó. Một trích dẫn thật
đặt sai chỗ khó phát hiện hơn nhiều so với một trích dẫn bịa.

Hai điều công cụ phải tự kiểm được, và cả hai đều có sẵn dữ liệu — không phải tin lời tác tử:
câu trích có thật là lời người dùng không (sổ cái ghi mọi `human_act`), và câu ấy có nhắc tới
phương án đang chốt không.
"""

from __future__ import annotations

from typing import Any

import pytest

_EX = {"summary": "chốt phương án", "why": "người dùng chọn",
       "sources": [{"kind": "human_act", "ref": "h-0001"}],
       "diff_prev": "chưa chốt gì", "next": "làm tiếp", "confidence": "NGUOI"}


def _ctx(agent) -> Any:
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


def _dung_phuong_an(agent, ctx) -> None:
    """Hai phương án trong kho — đủ để có thứ mà chốt."""
    for ma, ten in (("PA-01", "Bo mạch Linux nhỏ làm USB gadget"),
                    ("PA-02", "Vi điều khiển + Ethernet PHY + thẻ nhớ")):
        r = agent.registry.run("store.option_create", {
            "id": ma, "ten": ten, "kien_truc": ten, "explain": _EX}, ctx)
        assert r.ok, getattr(r.error, "message_vi", "")


def _noi(agent, cau: str) -> None:
    """Ghi một câu của NGƯỜI vào sổ cái, y như lúc họ gõ vào ô nhập."""
    agent.ledger.append("human_act", {"kind": "say", "text": cau, "id": "h-0001"})


def test_cau_MO_HO_khong_duoc_thanh_quyet_dinh_cua_nguoi(make_agent):
    """Ca TC004, dựng lại y nguyên: câu không chọn gì thì không được thành ADR 'người quyết'."""
    agent = make_agent([])
    ctx = _ctx(agent)
    _dung_phuong_an(agent, ctx)
    _noi(agent, "Làm cho mình cái mạch thông minh.")

    r = agent.registry.run("store.option_choose", {
        "id": "PA-01", "quyet_boi": "nguoi",
        "trich_loi_nguoi": "Làm cho mình cái mạch thông minh.", "explain": _EX}, ctx)

    assert not r.ok, "câu không chọn gì mà vẫn thành 'người quyết' là giả mạo xuất xứ"
    h = r.error.hint_for_agent or ""
    # Chặn thôi thì chưa đủ — phải nói ra ĐƯỜNG ĐI, nếu không tác tử sẽ thử lại cùng một lối.
    assert "tac_tu" in h or "tác tử" in h, "phải chỉ ra lối hạ tầng tin cậy xuống"
    assert "hỏi" in h.lower(), "phải chỉ ra lối hỏi người dùng"
    assert not [a for a in agent.store.list("adr", limit=10)], "không được sinh ADR nào"


def test_cau_CO_CHON_thi_van_chot_duoc(make_agent):
    """Cái phanh không được chặn đường đi đúng — người nói rõ chọn gì thì phải chốt được."""
    agent = make_agent([])
    ctx = _ctx(agent)
    _dung_phuong_an(agent, ctx)
    _noi(agent, "Mình chọn PA-01 nhé, dùng bo Linux nhỏ cho nhanh.")

    r = agent.registry.run("store.option_choose", {
        "id": "PA-01", "quyet_boi": "nguoi",
        "trich_loi_nguoi": "Mình chọn PA-01 nhé, dùng bo Linux nhỏ cho nhanh.",
        "explain": _EX}, ctx)

    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["adr"].startswith("ADR-")


def test_trich_dan_KHONG_CO_trong_so_cai_thi_bi_chan(make_agent):
    """Câu trích phải đối chiếu được với sổ cái — nếu không thì nó là lời tác tử tự đặt vào
    miệng người dùng, và đó là dạng giả mạo thẳng thừng hơn cả TC004."""
    agent = make_agent([])
    ctx = _ctx(agent)
    _dung_phuong_an(agent, ctx)
    _noi(agent, "Cho mình xem vài phương án đi.")

    r = agent.registry.run("store.option_choose", {
        "id": "PA-01", "quyet_boi": "nguoi",
        "trich_loi_nguoi": "Tôi chọn PA-01.", "explain": _EX}, ctx)

    assert not r.ok
    assert "sổ cái" in (r.error.message_vi + (r.error.hint_for_agent or "")).lower() \
        or "không tìm thấy" in r.error.message_vi.lower()


def test_TAC_TU_de_xuat_thi_khong_bi_chan(make_agent):
    """`quyet_boi="tac_tu"` là lời khai trung thực: tác tử đề xuất, người chưa phản đối.

    Phanh này chỉ canh tầng NGUOI. Chặn cả lối trung thực thì tác tử không còn đường nào ghi
    lại một quyết định tạm — và nó sẽ quay về lối nói dối vì lối thật bị bịt.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    _dung_phuong_an(agent, ctx)

    r = agent.registry.run("store.option_choose", {
        "id": "PA-02", "quyet_boi": "tac_tu", "explain": _EX}, ctx)

    assert r.ok, getattr(r.error, "message_vi", "")
    adr = [a for a in agent.store.list("adr", limit=10)]
    assert adr and adr[0]["canonical"]["quyet_boi"] == "tac_tu"
