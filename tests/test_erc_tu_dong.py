# -*- coding: utf-8 -*-
"""M3-10 — sau mỗi lần sửa bản đồ mạch, tác tử thấy NGAY lỗi chặn do chính nó vừa gây ra.

ERC chỉ chạy khi có ai gọi: `board.check`, `ckm.build`, `sch.netlist`. Nên một tác tử dựng
mạch bằng mười lời gọi `ckm.*` rồi nói "xong" **chưa bao giờ nhìn thấy** bảng ERC — trừ khi
nó tự nhớ gọi. Và nó không nhớ: đo được trên dữ liệu thật ở DEV-338, không phiên nào gọi
`board.check` sau một chuỗi sửa bản đồ.

Vòng đóng ở đây: sửa → ERC chạy → chỉ báo **lỗi MỚI** → lượt không kết thúc khi còn lỗi mới
chưa nhắc tới. Ba chỗ cố ý làm hẹp, và mỗi chỗ chữa một cách hỏng khác nhau:

* **chỉ lỗi MỚI** — báo lại lỗi cũ ở mỗi lời gọi thì sau năm lời gọi tác tử đọc cùng một
  dòng năm lần, và nó học được cách bỏ qua khối ấy;
* **trần 3 lần sửa cho cùng một lỗi** — sửa mãi một lỗi là vòng lặp đốt tiền; tới lần thứ ba
  thì hỏi người, vì nếu hai lần sửa đầu không đúng thì cái sai nằm ở chỗ hiểu đề bài;
* **mặc định TẮT** — nó chèn lời nhắc vào transcript và đổi `result.data`, tức đổi thứ mô
  hình đọc mỗi lượt (N-4).
"""

from __future__ import annotations

from typing import Any

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "VANG"}


@pytest.fixture
def bo(du_an):
    """Tác tử + ctx, dựng theo cờ truyền vào."""
    from eide import Config
    from eide.config import Features
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    def _lam(script=None, **co):
        f = Features(**co)
        cfg = Config.for_project(du_an)
        cfg.features = f
        ag = Agent(cfg, llm=ScriptedGateway(script or []), project_name="du-an-thu")
        ctx = TurnContext(config=cfg, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                          ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                          history=ag.history, agent=ag, run_id="run-1",
                          project_name="du-an-thu")
        return ag, ctx
    return _lam


def _goi(ag, ctx, _ten: str, **kw):
    """Chạy một công cụ rồi cho hook post_tool_use chạy — đúng thứ tự lõi làm."""
    if "explain" in (ag.registry.get(_ten).params.get("properties") or {}):
        kw.setdefault("explain", EX)
    res = ag.registry.run(_ten, kw, ctx)
    ag.hooks.post_tool_use({"tool": _ten, "args": kw, "id": "c1"}, res, ctx)
    return res


def _dung_mach(ag, ctx):
    """Một khối và một Port — đủ để bước sau nối cả rail lẫn đất vào đúng Port ấy.

    Cố ý chỉ dùng `ckm.module_set` + `ckm.port_set`: đó là những gì tác tử thật gọi khi
    dựng bản đồ, và lỗi ta muốn gây (`chap_nguon`) không cần chân lá nào. Dựng lá qua
    `ckm.chip_add` thì phải có Fact pinout trước — đúng luật, nhưng không liên quan gì tới
    thứ nhiệm vụ này đo.
    """
    assert _goi(ag, ctx, "ckm.module_set", ma="A", ten="A", muc_dich="thử").ok
    assert _goi(ag, ctx, "ckm.port_set", khoi="A", ten="P", huong="power_in").ok


def _gay_chap_nguon(ag, ctx):
    """Nối CẢ rail 3V3 lẫn GND vào cùng một Port → hai net thành một nhóm điện."""
    assert _goi(ag, ctx, "ckm.net_set", ten="3V3", loai="power",
                noi_port=[["A", "P"]]).ok
    return _goi(ag, ctx, "ckm.net_set", ten="GND", loai="gnd", noi_port=[["A", "P"]])


# =========================================================================== cờ BẬT
def test_net_set_gay_loi_chan_thi_ket_qua_co_erc_moi(bo):
    """TC-M3-10-01 — lời gọi vừa gây lỗi chặn thì kết quả của chính nó nói ra."""
    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)

    res = _gay_chap_nguon(ag, ctx)
    assert res.ok, getattr(res, "error", None)
    assert res.data.get("erc_moi"), sorted(res.data)
    assert any("chap_nguon" in str(x) for x in res.data["erc_moi"]), res.data["erc_moi"]
    assert "erc_moi" in str(res.data.get("note_vi", "")) or \
        "ERC" in str(res.data.get("note_vi", "")), res.data.get("note_vi")


def test_loi_cu_khong_bao_lai(bo):
    """TC-M3-10-02 — ca âm: lỗi đã báo một lần thì lời gọi sau KHÔNG báo lại.

    Báo lại ở mỗi lời gọi thì sau năm lời gọi tác tử đọc cùng một dòng năm lần — và nó học
    được cách bỏ qua khối ấy, kể cả lần có dòng mới.
    """
    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)
    r1 = _gay_chap_nguon(ag, ctx)
    assert r1.data.get("erc_moi")

    r2 = _goi(ag, ctx, "ckm.net_set", ten="GND", loai="gnd", noi_port=[["A", "P"]])
    assert not r2.data.get("erc_moi"), r2.data["erc_moi"]


def test_cong_cu_chi_doc_khong_chay_erc(bo):
    """ERC không chạy sau công cụ chỉ-đọc — nó là phép tính, không phải miễn phí."""
    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)
    _gay_chap_nguon(ag, ctx)

    res = _goi(ag, ctx, "ckm.graph")
    assert "erc_moi" not in (res.data or {}), res.data


def test_stop_cho_them_vong_khi_con_loi_moi_chua_nhac(bo):
    """TC-M3-10-03 — còn lỗi chặn mới mà tác tử chưa nhắc tới thì cho thêm một vòng."""
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)
    _gay_chap_nguon(ag, ctx)

    ctx.said_anything = True
    ctx.loi_da_noi = ["Đã dựng xong bản đồ mạch."]
    r = register_standard_hooks(HookBus()).stop(ctx)
    assert r.another_round, "còn lỗi chặn mới mà lượt vẫn kết thúc gọn"
    assert "erc_chua_xu" in r.fired, r.fired
    assert "chap_nguon" in (r.injection or ""), r.injection


def test_da_nhac_roi_thi_khong_bat_them_vong(bo):
    """Ca âm: tác tử ĐÃ nói ra lỗi thì đừng bắt nó nói lại.

    Không có cửa này thì hook thành một vòng lặp: nó bắt thêm vòng, tác tử nói về lỗi, hook
    vẫn thấy lỗi còn đó và bắt thêm vòng nữa.
    """
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)
    _gay_chap_nguon(ag, ctx)

    ctx.said_anything = True
    ctx.loi_da_noi = ["Bản đồ có lỗi chap_nguon: 3V3 đang nối vào GND, chưa sửa được."]
    r = register_standard_hooks(HookBus()).stop(ctx)
    assert "erc_chua_xu" not in r.fired, r.fired


def test_sua_3_lan_cung_loi_thi_doi_ask_user(bo):
    """TC-M3-10-04 — tới lần sửa thứ ba cho cùng một lỗi thì HỎI NGƯỜI, đừng sửa tiếp.

    Hai lần sửa đầu không đúng thì cái sai thường nằm ở chỗ hiểu đề bài, không ở chỗ gõ —
    và sửa lần thứ tư là đốt tiền để khẳng định điều đó.
    """
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    ag, ctx = bo(erc_tu_dong=True)
    _dung_mach(ag, ctx)
    _gay_chap_nguon(ag, ctx)

    # Một lần ghi NỮA mà lỗi vẫn còn — đó mới là "một lần sửa không ăn", và là lúc bộ đếm
    # tăng. Bản đầu của ca này đặt thẳng bộ đếm lên 3 rồi khẳng định nó khác rỗng, nên nó
    # đo chính câu lệnh của mình chứ không đo mã sản phẩm.
    _goi(ag, ctx, "ckm.net_set", ten="GND", loai="gnd", noi_port=[["A", "P"]])
    assert ctx.erc_lan_sua, "ghi thêm một lần mà lỗi vẫn còn — phải đếm là một lần sửa"

    ctx.said_anything = True
    ctx.loi_da_noi = ["xong"]
    for k in list(ctx.erc_lan_sua):
        ctx.erc_lan_sua[k] = 3

    r = register_standard_hooks(HookBus()).stop(ctx)
    assert r.another_round and "ask_user" in (r.injection or ""), r.injection


# =========================================================================== cờ TẮT
def test_co_tat_hook_khong_cham_ket_qua(bo):
    """TC-M3-10-05 — cờ TẮT: không khoá mới trong kết quả, không thêm vòng."""
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    ag, ctx = bo()
    _dung_mach(ag, ctx)
    res = _gay_chap_nguon(ag, ctx)
    assert "erc_moi" not in (res.data or {}), res.data

    ctx.said_anything = True
    ctx.loi_da_noi = ["xong"]
    r = register_standard_hooks(HookBus()).stop(ctx)
    assert "erc_chua_xu" not in r.fired, r.fired
