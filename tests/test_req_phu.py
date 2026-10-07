# -*- coding: utf-8 -*-
"""M2-02 — hook Stop nhắc khi còn YÊU CẦU chưa ai đo.

Lượt kết thúc bằng "đã xong" trong khi hai yêu cầu chưa có một phép đo nào là một lượt nói
quá về việc đã làm. Hook này không chặn lượt — nó cho thêm **một** vòng và nói rõ hai lối
ra: viết tiêu chí/test cho những REQ ấy, hoặc nói thẳng chúng ngoài phạm vi lượt này.

Cửa thoát phải nằm ngay trong lời nhắc. Thiếu nó, lời nhắc thành áp lực đẻ ra tiêu chí cho
có — và một tiêu chí viết cho có thì tệ hơn không có, vì nó làm cột "đã kiểm" sáng lên.
"""

from __future__ import annotations

from typing import Any

import pytest

from eide.hooks.base import HookBus
from eide.hooks.standard import register_standard_hooks

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}


class _Co:
    def __init__(self, bat: bool):
        self._bat = bat

    def bat(self, ten: str) -> bool:
        return self._bat and ten == "req_phu"


class _Cfg:
    def __init__(self, bat: bool):
        self.features = _Co(bat)


class _Ctx:
    """Như `_Ctx` của test_hoi_xong_thi_lam.py, thêm `store` thật và `config`."""

    def __init__(self, store: Any, *, bat: bool = True, da_ghi: bool = True):
        self.cong_cu_da_goi = ["fs.write"]
        self.da_ghi_gi_do = da_ghi
        self.da_nhac_rong: set[str] = set()
        self.assumptions: list[Any] = []
        self.said_anything = True
        self.awaiting_human = False
        self.human_edits: list[Any] = []
        self.loi_da_noi: list[str] = ["xong"]
        self.da_tu_kiem = True
        self.store = store
        self.registry = None
        self.ledger = None
        self.config = _Cfg(bat)


def _chay(ctx: Any):
    return register_standard_hooks(HookBus()).stop(ctx)


@pytest.fixture
def kho(du_an):
    """Kho thật, có FR-01 đã được đo và FR-02 mồ côi."""
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    r = build_registry()
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=r, emit=lambda c: None, history=ag.history,
                      agent=ag, run_id="run-1", project_name="du-an-thu")
    for ma, text in (("FR-01", "đèn nháy 1 Hz"), ("FR-02", "nút bấm đổi chế độ")):
        r.get("store.req_create").fn(ctx, id=ma, loai="FR", text=text,
                                     source_quote=f"anh nói: {text}", explain=EX)
    r.get("sim.criteria").fn(ctx, explain=EX, ma="sim-01", ten="đo nháy", **{
        "assert": [{"ma": "A1", "mo_ta": "chu kỳ 1 s", "phep_so": "<=", "nguong": 1.0,
                    "do_req": "FR-01", "nguon_nguong": "tài liệu"}]})
    return ag


def test_hook_nhac_REQ_mo_coi_khi_co_bat(kho):
    """TC-M2-02-03 — cờ BẬT, còn REQ chưa ai đo → thêm một vòng, và nêu đúng mã REQ."""
    r = _chay(_Ctx(kho.store))
    assert r.another_round, "còn REQ chưa ai đo mà lượt vẫn kết thúc gọn"
    assert "req_chua_phu" in r.fired, r.fired
    t = r.injection or ""
    assert "FR-02" in t, t
    assert "FR-01" not in t, "FR-01 đã có phép đo — nhắc nó là nhắc sai"
    # Cửa thoát: không có nó thì lời nhắc thành áp lực đẻ tiêu chí cho có.
    assert "ngoài phạm vi" in t.lower(), t


def test_co_tat_hook_im(kho):
    """TC-M2-02-04 — cờ TẮT: hook không nổ, số vòng của lượt không đổi."""
    r = _chay(_Ctx(kho.store, bat=False))
    assert "req_chua_phu" not in r.fired, r.fired


def test_dang_giua_ke_hoach_thi_hoan(kho):
    """TC-M2-02-05 — ca âm: đang giữa một kế hoạch đã duyệt thì khoan nhắc.

    Cùng lý lẽ với `kiem_viec_chua_ai_kiem`: kế hoạch bảy bước mà mỗi bước bị nhắc một vòng
    thì bảy bước thành mười bốn lượt. Phủ yêu cầu là câu hỏi của lúc KẾT THÚC.
    """
    from eide.ke_hoach import MA_KE_HOACH, Buoc, KeHoach

    kh = KeHoach(muc_tieu="làm đèn", trang_thai="da_duyet",
                 buoc=[Buoc(viec="viết mã", cong_cu="fs.write", hien_vat="blink.c"),
                       Buoc(viec="đo", cong_cu="sim.criteria", hien_vat="tiêu chí")])
    kho.store.apply(artefact_id=MA_KE_HOACH, type="plan", op="create", author="test",
                    canonical=kh.to_dict(), explain=EX,
                    view_hint={"kind": "plan", "path": "kế hoạch"})

    r = _chay(_Ctx(kho.store))
    assert "req_chua_phu" not in r.fired, r.fired


def test_chua_ghi_gi_thi_khong_nhac(kho):
    """Lượt chỉ đọc, chưa ghi gì — chưa tới lúc hỏi "đã đo chưa"."""
    r = _chay(_Ctx(kho.store, da_ghi=False))
    assert "req_chua_phu" not in r.fired, r.fired


def test_moi_luot_chi_nhac_MOT_lan(kho):
    """Vòng thứ hai là vòng tác tử đang TRẢ LỜI lời nhắc — nhắc lại là vòng lặp."""
    ctx = _Ctx(kho.store)
    assert _chay(ctx).another_round
    r2 = _chay(ctx)
    assert "req_chua_phu" not in r2.fired, r2.fired
