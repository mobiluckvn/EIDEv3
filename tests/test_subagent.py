# -*- coding: utf-8 -*-
"""Subagent, hook SubagentStop, và skill — G6 §B5.

Điều bộ này canh: **một lớp kiểm chứng độc lập phải thật sự độc lập.** Nếu verifier đọc được
đề bài, dùng được công cụ ghi, hoặc kết luận của nó bị nuốt đi khi nó bác — thì nó chỉ là một
lớp đóng dấu tốn tiền.
"""

from __future__ import annotations

import json

from eide import subagent as SA
from eide.llm import Response, ToolCall

_EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
       "confidence": "VANG"}


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1",
                       agent=agent)


def _bc(**kw) -> str:
    d = {"tom_tat": "xong", "da_lam": ["a"], "bang_chung": [{"kind": "file", "ref": "a.c"}],
         "chua_lam": [], "ket_luan": "dat", "do_tin": "BAC"}
    d.update(kw)
    return "Báo cáo:\n" + json.dumps(d, ensure_ascii=False)


# ===================================================================== lược đồ báo cáo
def test_bao_cao_khong_co_JSON_thi_KHONG_hop_le():
    """Không có bước này thì một subagent kết thúc bằng một đoạn văn trôi chảy, và tác tử
    chính đọc đoạn văn đó như thể nó là kết quả."""
    bc = SA.doc_bao_cao("Tôi đã kiểm hết rồi, mọi thứ ổn.", subagent="firmware")
    assert not bc.hop_le and "không có dòng JSON" in bc.loi_luoc_do[0]


def test_thieu_truong_thi_noi_RO_thieu_gi():
    bc = SA.doc_bao_cao('{"tom_tat": "x", "ket_luan": "dat"}', subagent="firmware")
    assert not bc.hop_le
    assert "da_lam" in bc.loi_luoc_do[0] and "bang_chung" in bc.loi_luoc_do[0]


def test_tuyen_DAT_ma_khong_co_bang_chung_la_khong_hop_le():
    """Đây đúng hình dạng của đậu giả: một kết luận không trỏ tới thứ gì mở ra xem được."""
    bc = SA.doc_bao_cao(_bc(bang_chung=[]), subagent="sim-runner")
    assert not bc.hop_le and "KHÔNG có bằng chứng" in bc.loi_luoc_do[0]


def test_ket_luan_la_ba_gia_tri_dong():
    bc = SA.doc_bao_cao(_bc(ket_luan="ok"), subagent="firmware")
    assert not bc.hop_le and "không hợp lệ" in bc.loi_luoc_do[0]


# ===================================================================== verifier
def test_firmware_va_sim_tuyen_DAT_thi_PHAI_qua_verifier():
    for ma in ("firmware", "sim-runner"):
        assert SA.can_goi_verifier(SA.doc_bao_cao(_bc(), subagent=ma)) is True
    # Không tuyên đạt thì không cần kiểm — verifier là để bắt đậu giả, không phải để bắt lỗi.
    assert SA.can_goi_verifier(SA.doc_bao_cao(_bc(ket_luan="khong_dat"),
                                              subagent="firmware")) is False
    # Tác tử khác thì không: rà soát thiết kế "đạt" không phải một tuyên bố về thứ đã chạy.
    assert SA.can_goi_verifier(SA.doc_bao_cao(_bc(), subagent="design-review")) is False


def test_verifier_KHONG_thay_de_bai_chi_thay_bao_cao():
    """Cho nó đọc đề bài là mời nó suy ra kết luận mong đợi rồi đi tìm cách biện minh."""
    bc = SA.doc_bao_cao(_bc(tom_tat="đã biên dịch sạch"), subagent="firmware")
    viec = SA.viec_cho_verifier(bc)
    assert "đã biên dịch sạch" in viec
    assert SA.SUBAGENT["verifier"].doc_duoc_viec is False


def test_verifier_chi_co_cong_cu_DOC():
    """Ghi được thì nó có thể sửa cho đạt đúng thứ nó đang đi kiểm."""
    ghi = {"fs.write", "fs.edit", "build.compile", "sim.run", "sim.criteria", "test.run",
           "ckm.net_set", "fact.assert_human", "snapshot.create"}
    assert not (set(SA.SUBAGENT["verifier"].cong_cu) & ghi)


def test_verifier_BAC_thi_ket_luan_bi_HA_chu_khong_bi_nuot():
    """Một lớp kiểm chứng mà kết luận của nó bị nuốt đi thì chỉ tốn tiền."""
    bc = SA.doc_bao_cao(_bc(), subagent="firmware")
    kc = SA.doc_bao_cao(_bc(ket_luan="khong_dat", tom_tat="tệp a.c không tồn tại"),
                        subagent="verifier")
    gop = SA.gop_kiem_chung(bc, kc)
    assert gop.ket_luan == "khong_dat"
    assert any("Verifier bác" in x for x in gop.chua_lam)
    assert gop.kiem_chung["tom_tat"] == "tệp a.c không tồn tại"


def test_verifier_khong_kiem_duoc_thi_ha_xuong_CHUA_DU_DU_KIEN():
    bc = SA.doc_bao_cao(_bc(), subagent="sim-runner")
    kc = SA.doc_bao_cao(_bc(ket_luan="chua_du_du_kien", tom_tat="không mở được blob"),
                        subagent="verifier")
    assert SA.gop_kiem_chung(bc, kc).ket_luan == "chua_du_du_kien"


# ===================================================================== chạy thật
def test_subagent_KHONG_dung_duoc_cong_cu_ngoai_tap_cua_no(make_agent):
    """Tập công cụ bị giới hạn là một ràng buộc, không phải một gợi ý."""
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write",
                                      {"path": "x.c", "content": "…", "explain": _EX})]),
        Response(text=_bc(ket_luan="chua_du_du_kien", bang_chung=[])),
    ])
    bc = SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="verifier",
                 viec="kiểm báo cáo")
    kq = [m for m in [] ]  # noqa: F841 — giữ chỗ cho người đọc: kết quả nằm trong bc
    assert bc.cong_cu_da_goi == ["fs.write"]
    assert bc.ket_luan == "chua_du_du_kien"
    assert not (agent.config.paths.project_root / "x.c").exists(), "verifier đã GHI được tệp"


def test_task_run_tu_goi_verifier_khi_firmware_tuyen_dat(make_agent):
    """Nếu việc gọi verifier là tuỳ chọn thì nó sẽ được gọi đúng những lúc không cần."""
    agent = make_agent([
        Response(text=_bc(tom_tat="biên dịch sạch")),                    # firmware
        Response(text=_bc(ket_luan="khong_dat", tom_tat="không có tệp ảnh nào trên đĩa",
                          bang_chung=[{"kind": "fs", "ref": ".eide/build"}])),  # verifier
    ])
    r = agent.registry.run("task.run", {"subagent": "firmware", "viec": "viết blink",
                                        "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["kiem_chung"] is not None
    assert r.data["ket_luan"] == "khong_dat"
    assert "KHÔNG đồng ý" in r.data["note_vi"]


def test_task_run_bao_cao_hong_luoc_do_thi_KHONG_chuyen_tiep_nhu_ket_qua(make_agent):
    agent = make_agent([Response(text="Mọi thứ ổn, tôi đã kiểm.")])
    r = agent.registry.run("task.run", {"subagent": "design-review", "viec": "rà soát",
                                        "explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E5007"
    assert "ĐỪNG kể lại đoạn văn" in r.error.hint_for_agent


def test_task_run_viec_rong_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("task.run", {"subagent": "firmware", "viec": "  ",
                                        "explain": _EX}, _ctx(agent))
    assert not r.ok and "không thấy transcript" in r.error.hint_for_agent


# ===================================================================== skill
def test_skill_load_liet_ke_va_nap_duoc(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    ds = agent.registry.run("skill.load", {}, ctx)
    assert ds.ok and ds.data["so_skill"] >= 5
    assert all(s["khi_nao"] for s in ds.data["skill"]), "skill nào cũng phải nói KHI NÀO dùng"

    r = agent.registry.run("skill.load", {"ten": "sim-criteria-first"}, ctx)
    assert r.ok and "Nêu tiêu chí trước" in r.data["noi_dung"]
    assert "HƯỚNG DẪN" in r.data["note_vi"]


def test_skill_khong_co_thi_noi_that(make_agent):
    agent = make_agent([])
    r = agent.registry.run("skill.load", {"ten": "khong-ton-tai"}, _ctx(agent))
    assert not r.ok and "Không có skill" in r.error.message_vi


def test_tim_skill_theo_tu_khoa(make_agent):
    agent = make_agent([])
    r = agent.registry.run("skill.load", {"tim": "watchdog"}, _ctx(agent))
    assert r.ok and any("hardfault" in s["ten"] for s in r.data["skill"])


def test_skill_duoc_GOI_Y_theo_ngu_canh_cau_nguoi_vua_go(make_agent):
    """§B5: skill "nạp theo ngữ cảnh". Gợi ý chỉ là tên + một câu; nội dung đầy đủ để mô hình
    tự nạp — nhét cả sáu hướng dẫn vào mỗi lượt là trả tiền cho thứ phần lớn lượt không dùng."""
    from eide.context.assemble import build_skills_hint
    from eide.skills import goi_y_cho_ngu_canh

    ds = goi_y_cho_ngu_canh()
    assert ds and all(s["keywords"] for s in ds), "skill nào cũng phải có từ khoá"

    hint = build_skills_hint(ds, "chạy mô phỏng xem robot có đứng được không", 300)
    assert "sim-criteria-first" in hint
    # Câu không liên quan thì KHÔNG gợi ý gì — gợi ý sai chỗ dạy người ta bỏ qua gợi ý.
    assert build_skills_hint(ds, "hôm nay trời đẹp quá", 300) == ""


def test_skill_hint_vao_duoc_ngu_canh_that(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    ctx.human_edits = []
    asm = agent._assemble(ctx, None)
    assert "skills_hint" in asm.blocks
