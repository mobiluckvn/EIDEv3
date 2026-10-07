# -*- coding: utf-8 -*-
"""M2-06 — một bước kế hoạch sinh mã chỉ "xong" khi phép kiểm của nó đã chạy ĐƯỢC.

`plan.step_done` hiện đòi một **hiện vật mở ra xem được** (E6004) — đó là bước tiến so với
bản đầu nhận cả câu *"tôi đã viết xong chương 1 rồi nhé"*. Nhưng một tệp `.c` tồn tại trên
đĩa **không** nói nó biên dịch được. Tác tử ghi tệp, đánh dấu xong, sang bước sau; lỗi dịch
chỉ lộ ra ở bước cuối, khi đã có bốn bước dựng trên nó.

Nên bước phải khai **kiểm bằng gì**, và `step_done` đối chiếu sổ cái: phép kiểm ấy đã chạy
thành công **SAU** lần ghi của bước hay chưa. Sổ cái đã có đủ dữ liệu cho việc này từ trước
(`tool_result {tool, ok}` ghi theo thứ tự) — chỉ chưa ai đọc nó để trả lời câu hỏi đó.

Mã lỗi: **E6012**. (Bảng TC của nhiệm vụ đặt tên ca là "E6010" — đó là mã của M1-10; phần
thân nhiệm vụ và bảng cấp phát mã ở §6 đều ghi E6012.)
"""

from __future__ import annotations

from typing import Any

import pytest

from eide import ke_hoach as KH

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}


@pytest.fixture
def bo(du_an):
    """Tác tử + registry + ctx, dựng theo cờ truyền vào."""
    from eide import Config
    from eide.config import Features
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    def _lam(**co):
        f = Features(**co)
        cfg = Config.for_project(du_an)
        cfg.features = f
        ag = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
        r = build_registry(f)
        ctx = TurnContext(config=cfg, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                          ids=ag.ids, registry=r, emit=lambda c: None, history=ag.history,
                          agent=ag, run_id="run-1", project_name="du-an-thu")
        return ag, r, ctx
    return _lam


def _kh(**kw) -> KH.KeHoach:
    """Kế hoạch hợp lệ tối thiểu, một bước sinh mã.

    Phải qua được cả `thieu_phan_tich` (E6009) — kế hoạch dựng cái chưa có thì đòi một bước
    CHỌN KIẾN TRÚC và một câu nói CẤU TRÚC MÃ. Đó là luật có từ trước M2-06; kế hoạch thử
    ở đây phải hợp lệ theo luật ấy, không thì ca kiểm đo sai chỗ.
    """
    b = KH.Buoc(viec="viết driver, một mô-đun một tệp", cong_cu="fs.write",
                hien_vat="drv.c", **kw)
    kt = KH.Buoc(viec="chốt hướng", cong_cu="store.adr_create", hien_vat="ADR-01")
    them = [KH.Buoc(viec=f"việc {i}", cong_cu="fs.read", hien_vat=f"ghi chú {i}")
            for i in range(3, KH.TOI_THIEU_BUOC + 1)]
    return KH.KeHoach(muc_tieu="làm driver", buoc=[kt, b] + them)


# =========================================================================== kiểm kế hoạch
def test_buoc_sinh_ma_thieu_kiem_thi_loi():
    """TC-M2-06-01 — bước ghi `.c` mà không nói kiểm bằng gì thì kế hoạch chưa dùng được."""
    loi = KH.kiem_ke_hoach(_kh(), lambda t: True, doi_kiem=True)
    assert any("kiểm bằng gì" in x for x in loi), loi


def test_buoc_sinh_ma_co_kiem_thi_qua():
    loi = KH.kiem_ke_hoach(_kh(kiem="build.compile"), lambda t: True, doi_kiem=True)
    assert loi == [], loi


def test_kiem_khong_thi_phai_noi_ly_do():
    """`kiem="khong"` là một lựa chọn hợp lệ — nhưng phải nói VÌ SAO, không khai suông."""
    loi = KH.kiem_ke_hoach(_kh(kiem="khong"), lambda t: True, doi_kiem=True)
    assert any("ghi_chu" in x or "vì sao" in x.lower() for x in loi), loi

    ok = KH.kiem_ke_hoach(_kh(kiem="khong", ghi_chu="chưa có toolchain cho chip này"),
                          lambda t: True, doi_kiem=True)
    assert ok == [], ok


def test_buoc_tai_lieu_khong_bi_doi_kiem():
    """TC-M2-06-05 — ca âm: bước ghi `.md` là viết tài liệu, không đòi phép kiểm nào.

    Báo động giả dạy người ta bỏ qua cảnh báo, nên nó đắt hơn hẳn việc không có cảnh báo —
    cùng lý lẽ đã chữa lỗi `.m` khớp trong `tai-lieu/1.md` ở `_la_ma`.
    """
    kh = KH.KeHoach(muc_tieu="viết tài liệu",
                    buoc=[KH.Buoc(viec="viết chương 1", cong_cu="fs.write",
                                  hien_vat="tai-lieu/1.md")]
                         + [KH.Buoc(viec=f"việc {i}", cong_cu="fs.read",
                                    hien_vat=f"ghi chú {i}")
                            for i in range(2, KH.TOI_THIEU_BUOC + 1)])
    assert KH.kiem_ke_hoach(kh, lambda t: True, doi_kiem=True) == []


def test_co_tat_thi_khong_doi_kiem():
    """Cờ TẮT: `kiem_ke_hoach` xử sự y như trước, không đòi trường mới nào."""
    assert KH.kiem_ke_hoach(_kh(), lambda t: True) == []


def test_ke_hoach_cu_tren_dia_khong_co_truong_kiem():
    """TC-M2-06-06 — ca biên: kế hoạch đã lưu từ trước không có `kiem`/`req`.

    Phiên cũ phải mở lại được (N-7). Thiếu trường thì nhận giá trị mặc định, không nổ.
    """
    d = {"muc_tieu": "x", "trang_thai": "da_duyet",
         "steps": [{"viec": "a", "cong_cu": "fs.read", "hien_vat": "b"}]}
    kh = KH.KeHoach.from_dict(d)
    assert kh.buoc[0].kiem == "" and kh.buoc[0].req == []
    # Và ghi lại thì hai trường mới có mặt, không làm hỏng dạng cũ.
    assert "kiem" in kh.buoc[0].to_dict() and "req" in kh.buoc[0].to_dict()


# =========================================================================== step_done
def _vao_ke_hoach(ag, r, ctx, kiem: str):
    """Vào plan mode, nộp một kế hoạch có `kiem`, rồi đóng dấu đã duyệt."""
    r.get("plan.enter").fn(ctx, viec="làm driver")
    kh = _kh(kiem=kiem)
    ra = r.get("plan.exit").fn(ctx, buoc=[b.to_dict() for b in kh.buoc])
    assert not hasattr(ra, "ok") or ra.ok, getattr(ra, "error", None)
    a = ag.store.get(KH.MA_KE_HOACH)
    cur = KH.KeHoach.from_dict(a["canonical"])
    cur.trang_thai = "da_duyet"
    ag.store.apply(artefact_id=KH.MA_KE_HOACH, type="plan", op="update", author="test",
                   canonical=cur.to_dict(), explain=EX,
                   view_hint={"kind": "plan", "path": "kế hoạch"})
    return cur


def _ghi_so(ag, tool: str, ok: bool = True):
    ag.ledger.append("tool_result", {"run_id": "run-1", "tool": tool, "ok": ok})


def test_step_done_chua_build_thi_E6012(bo, du_an):
    """TC-M2-06-02 — ghi tệp rồi đánh dấu xong, mà chưa biên dịch lần nào → E6012."""
    ag, r, ctx = bo(ke_hoach_cong_kiem=True)
    _vao_ke_hoach(ag, r, ctx, "build.compile")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "fs.write")

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert hasattr(ra, "ok") and not ra.ok, ra
    assert ra.error.code == "E6012", ra.error.code
    assert "build.compile" in ra.error.hint_for_agent


def test_step_done_sau_build_ok_thi_qua(bo, du_an):
    """TC-M2-06-03 — biên dịch xong SAU lần ghi thì bước được đánh dấu."""
    ag, r, ctx = bo(ke_hoach_cong_kiem=True)
    _vao_ke_hoach(ag, r, ctx, "build.compile")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "fs.write")
    _ghi_so(ag, "build.compile", ok=True)

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert not hasattr(ra, "ok") or ra.ok, getattr(ra, "error", None)
    assert ra["xong"] == 1, ra


def test_build_TRUOC_lan_ghi_khong_tinh(bo, du_an):
    """Thứ tự là cả vấn đề: biên dịch TRƯỚC khi sửa tệp không nói gì về tệp sau khi sửa.

    Đây là chỗ một phép kiểm "đã chạy chưa" hoá ra vô nghĩa nếu không xét thứ tự — và cũng
    là chỗ sổ cái trả lời được mà không cần thêm dữ liệu gì mới.
    """
    ag, r, ctx = bo(ke_hoach_cong_kiem=True)
    _vao_ke_hoach(ag, r, ctx, "build.compile")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "build.compile", ok=True)      # dịch TRƯỚC
    _ghi_so(ag, "fs.write")                    # rồi mới sửa tệp

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert hasattr(ra, "ok") and not ra.ok and ra.error.code == "E6012", ra


def test_build_DO_khong_tinh_la_da_kiem(bo, du_an):
    ag, r, ctx = bo(ke_hoach_cong_kiem=True)
    _vao_ke_hoach(ag, r, ctx, "build.compile")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "fs.write")
    _ghi_so(ag, "build.compile", ok=False)

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert hasattr(ra, "ok") and not ra.ok and ra.error.code == "E6012", ra


def test_co_tat_step_done_nhu_cu(bo, du_an):
    """TC-M2-06-04 — cờ TẮT: chỉ kiểm hiện vật, y như hiện nay."""
    ag, r, ctx = bo()
    _vao_ke_hoach(ag, r, ctx, "build.compile")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "fs.write")

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert not hasattr(ra, "ok") or ra.ok, getattr(ra, "error", None)


def test_buoc_kiem_khong_thi_step_done_khong_doi_gi(bo, du_an):
    """`kiem="khong"` đã khai lý do ở lúc duyệt — step_done không đòi thêm."""
    ag, r, ctx = bo(ke_hoach_cong_kiem=True)
    r.get("plan.enter").fn(ctx, viec="làm driver")
    kh = _kh(kiem="khong", ghi_chu="chưa có toolchain")
    r.get("plan.exit").fn(ctx, buoc=[b.to_dict() for b in kh.buoc])
    a = ag.store.get(KH.MA_KE_HOACH)
    cur = KH.KeHoach.from_dict(a["canonical"])
    cur.trang_thai = "da_duyet"
    ag.store.apply(artefact_id=KH.MA_KE_HOACH, type="plan", op="update", author="test",
                   canonical=cur.to_dict(), explain=EX,
                   view_hint={"kind": "plan", "path": "kế hoạch"})
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    _ghi_so(ag, "fs.write")

    ra = r.get("plan.step_done").fn(ctx, so=2, hien_vat="drv.c")
    assert not hasattr(ra, "ok") or ra.ok, getattr(ra, "error", None)


def test_co_tat_luoc_do_buoc_khong_co_kiem():
    """Cờ TẮT thì lược đồ `plan.exit` không mọc thêm trường nào."""
    from eide.config import Features
    from eide.tools import build_registry

    r = build_registry(Features())
    tv = r.get("plan.exit").params["properties"]["buoc"]["items"]["properties"]
    assert "kiem" not in tv and "req" not in tv, sorted(tv)


def test_co_bat_luoc_do_buoc_co_kiem_va_req(monkeypatch):
    from eide.config import Features
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_KE_HOACH_CONG_KIEM", "1")
    r = build_registry(Features.load())
    tv = r.get("plan.exit").params["properties"]["buoc"]["items"]["properties"]
    assert "kiem" in tv and "req" in tv, sorted(tv)
    assert "build.compile" in tv["kiem"]["enum"] and "khong" in tv["kiem"]["enum"]
