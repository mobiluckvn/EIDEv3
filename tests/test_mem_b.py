# -*- coding: utf-8 -*-
"""MEM-B — bộ nhớ dài hạn trên đĩa. EIDE-MEM-42 §7, §10, §12.

Ca đo: MEM03 (fs.write vào EIDE.md bị chặn), MEM10 (EIDE.md vượt trần), MEM13 (quên có
chủ đích), MEM14 (lõi chết giữa tool), MEM16 (tra quá khứ), MEM18 (write-ahead + hash).

Câu hỏi cả bộ này trả lời: **mất điện giữa lượt thì mất gì?** Trước MEM-B, câu trả lời
là "toàn bộ ngữ cảnh mô hình" — và không ai biết là đã mất, vì sổ cái vẫn đầy đủ nên
giao diện dựng lại dòng hội thoại như không có chuyện gì.
"""

from __future__ import annotations

import json

import pytest

from eide.memory.transcript import (CO_TAC_DUNG_PHU, KhoPhien, Transcript, phuc_hoi)
from eide.store.eide_md import TRAN_TOKEN, EideMd


# =========================================================================== MEM18 đĩa
def test_MEM18_moi_message_xuong_dia_ngay(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    ts.ghi({"role": "user", "text": "làm cái này"})
    ts.ghi({"role": "model", "text": "vâng"})
    ms, hong = ts.doc()
    assert [m["text"] for m in ms] == ["làm cái này", "vâng"] and hong == 0


def test_MEM18_dong_cut_bi_DEM_chu_khong_im_lang_bo(tmp_path):
    """Một transcript thiếu một dòng mà không ai biết là một transcript nói dối."""
    p = tmp_path / "t.jsonl"
    ts = Transcript(p)
    ts.ghi({"role": "user", "text": "câu đủ"})
    with p.open("a", encoding="utf-8") as f:
        f.write('{"role": "user", "text": "câu bị cụ')      # mất điện giữa lúc ghi
    ms, hong = ts.doc()
    assert len(ms) == 1 and hong == 1


def test_MEM18_thay_toan_bo_la_ATOMIC(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    for i in range(5):
        ts.ghi({"role": "user", "text": f"m{i}"})
    ts.thay_toan_bo([{"role": "user", "text": "tóm tắt"}])
    ms, _ = ts.doc()
    assert len(ms) == 1 and ms[0]["text"] == "tóm tắt"
    assert not (tmp_path / "t.tmp").exists(), "tệp tạm phải được đổi tên, không để lại"


def test_MEM18_agent_ghi_transcript_ra_dia(chay, make_agent):
    from eide.llm.gateway import Response
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="xong rồi anh")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "ghi giúp mình một yêu cầu"})

    ms, hong = agent.transcript.doc()
    assert ms and hong == 0, "transcript phải nằm trên đĩa sau lượt"
    assert any(m.get("role") == "user" for m in ms)
    assert agent.transcript.path.exists()


def test_MEM18_chuoi_hash_changeset(tmp_path):
    from eide.changeset import Changeset, ChangesetLog, Touch

    log = ChangesetLog(tmp_path / "cs.jsonl")
    for i in range(3):
        log.append(Changeset(id=f"cs-{i}", ts="2026-09-25T00:00:00Z", author="human",
                             touches=[Touch(f"FR-{i}", "artefact", "create")]))
    ok, vi = log.verify()
    assert ok and "3 thay đổi" in vi


def test_MEM18_sua_mot_dong_o_giua_thi_LO_RA(tmp_path):
    from eide.changeset import Changeset, ChangesetLog, Touch

    p = tmp_path / "cs.jsonl"
    log = ChangesetLog(p)
    for i in range(3):
        log.append(Changeset(id=f"cs-{i}", ts="2026-09-25T00:00:00Z", author="human",
                             touches=[Touch(f"FR-{i}", "artefact", "create")]))
    ds = p.read_text("utf-8").splitlines()
    d = json.loads(ds[1])
    d["author"] = "agent:run-9"          # đổi tác giả của một thay đổi đã ghi
    ds[1] = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    p.write_text("\n".join(ds) + "\n", "utf-8")

    ok, vi = ChangesetLog(p).verify()
    assert not ok and "cs-1" in vi


def test_MEM18_danh_dau_sau_KHONG_lam_vo_chuoi(tmp_path):
    """§E5.2 cho phép sửa tại chỗ hai trường đánh dấu — hash không được băm chúng."""
    from eide.changeset import Changeset, ChangesetLog, Touch

    p = tmp_path / "cs.jsonl"
    log = ChangesetLog(p)
    log.append(Changeset(id="cs-1", ts="2026-09-25T00:00:00Z", author="human",
                         touches=[Touch("FR-01", "artefact", "create")]))
    log.mark("cs-1", acknowledged_by_agent="run-7")
    ok, vi = ChangesetLog(p).verify()
    assert ok, vi


# =========================================================================== MEM14 sự cố
def test_MEM14_goi_cong_cu_khong_co_ket_qua_bi_neu_ra(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    ts.ghi({"role": "user", "text": "biên dịch đi"})
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "build.compile", "args": {}}]})
    # …rồi lõi chết. Không có message role=tool nào cho c1.
    bc = phuc_hoi(ts, "ses-1")
    assert len(bc.goi_dang_do) == 1
    assert bc.goi_dang_do[0]["tool"] == "build.compile"
    assert bc.can_hoi_nguoi, "build.compile đổi thứ bên ngoài — phải hỏi"


def test_MEM14_nhac_cam_chay_lai_cong_cu_co_tac_dung_phu(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "target.flash", "args": {}}]})
    nhac = phuc_hoi(ts).nhac_vi()
    assert "ĐỪNG chạy lại" in nhac and "target.flash" in nhac


def test_MEM14_cong_cu_chi_doc_thi_chay_lai_duoc(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "fs.read", "args": {}}]})
    bc = phuc_hoi(ts)
    assert bc.goi_dang_do and not bc.can_hoi_nguoi
    assert "chạy lại được" in bc.nhac_vi()


def test_MEM14_goi_da_co_ket_qua_thi_khong_tinh_la_do_dang(tmp_path):
    ts = Transcript(tmp_path / "t.jsonl")
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "build.compile", "args": {}}]})
    ts.ghi({"role": "tool", "tool_call_id": "c1", "tool": "build.compile",
            "result": {"ok": True}})
    assert phuc_hoi(ts).goi_dang_do == []


def test_MEM14_phien_ket_thuc_sach_thi_khong_phuc_hoi(tmp_path):
    kp = KhoPhien(tmp_path / "sessions")
    kp.transcript("ses-1").ghi({"role": "user", "text": "x"})
    assert not kp.ket_thuc_sach("ses-1")
    kp.danh_dau_ket_thuc("ses-1")
    assert kp.ket_thuc_sach("ses-1")
    assert kp.gan_nhat() == "ses-1"


def test_danh_sach_cong_cu_co_tac_dung_phu_du_thu_nguy_hiem():
    for t in ("fs.write", "target.flash", "target.dangerous", "bash", "tool.install"):
        assert t in CO_TAC_DUNG_PHU, t
    assert "fs.read" not in CO_TAC_DUNG_PHU


# =========================================================================== MEM03 EIDE.md
def _ctx_gia(agent):
    class C:
        config = agent.config
        store = agent.store
        eide_md = agent.eide_md
        registry = agent.registry
        history = agent.history
        loi_nguoi_trong_phien: list = []
    return C()


_EX = {"summary": "ghi", "why": "vì", "sources": [], "diff_prev": "—",
       "next": "—", "confidence": "NGUOI"}


def test_MEM03_fs_write_vao_EIDE_md_bi_CHAN(chay, make_agent):
    """Gọi đúng như mô hình gọi: có explain, nếu không hook explain chặn trước và
    ca này sẽ xanh vì lý do khác."""
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    from eide.policy import PolicyEngine

    agent = make_agent([])
    bus = register_standard_hooks(HookBus())
    pol = PolicyEngine()
    for duong in ("EIDE.md", "./EIDE.md", str(agent.config.paths.eide_md)):
        goi = {"tool": "fs.write",
               "args": {"path": duong, "content": "x", "explain": _EX}}
        f = bus.pre_tool_use(goi, _ctx_gia(agent)).facts
        assert f["target.la_eide_md"] is True, duong
        d = pol.decide(goi, f)
        assert d.action == "deny" and "memory.note" in d.reason_vi, duong


def test_MEM03_tep_khac_khong_bi_anh_huong(chay, make_agent):
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    agent = make_agent([])
    goi = {"tool": "fs.write",
           "args": {"path": "src/main.c", "content": "int x;", "explain": _EX}}
    f = register_standard_hooks(HookBus()).pre_tool_use(goi, _ctx_gia(agent)).facts
    assert f["target.la_eide_md"] is False


def test_muc_Dung_chi_NGUOI_ghi_duoc(tmp_path):
    md = EideMd.load(tmp_path / "EIDE.md", create_name="thu")
    duoc, vi_sao = md.duoc_ghi("Đừng", "tac_tu")
    assert not duoc and "ranh giới do người đặt" in vi_sao
    assert md.duoc_ghi("Đừng", "nguoi")[0]
    assert md.duoc_ghi("Quyết định", "tac_tu")[0]


def test_nguon_goc_dong(tmp_path):
    md = EideMd.load(tmp_path / "EIDE.md", create_name="thu")
    md.append_line("Quyết định", "- Chọn MTP", boi="run-43")
    assert "[run-43]" in md.get("Quyết định")
    md.append_line("Quyết định", "- Người tự ghi", boi="h-0940")
    assert "[h-0940]" in md.get("Quyết định")


# =========================================================================== MEM10 trần
def test_MEM10_vuot_tran_thi_de_xuat_luoc_chu_KHONG_tu_xoa(tmp_path):
    md = EideMd.load(tmp_path / "EIDE.md", create_name="thu")
    for i in range(30):
        md.append_line("Quyết định", f"- ADR-{i:02d}: quyết định thứ {i}", boi="run-1")
    md.save()

    de = md.de_xuat_luoc()
    assert de, "phải đề xuất lược"
    quyet = next(d for d in de if d["muc"] == "Quyết định")
    assert quyet["so_dong"] == 15 and quyet["vi_sao"]
    # P5: đề xuất, KHÔNG tự xoá.
    assert len(md.get("Quyết định").splitlines()) == 30


def test_MEM10_tran_tinh_tren_TEP_khong_phai_luc_render(tmp_path):
    """Cắt lúc render là giấu vấn đề; trần trên tệp là nói ra vấn đề."""
    md = EideMd.load(tmp_path / "EIDE.md", create_name="thu")
    md.set("Mục tiêu", "x" * int(TRAN_TOKEN * 3 * 1.5))
    md.save()
    assert md.qua_tran and md.so_token > TRAN_TOKEN
    assert len(md.render(12000)) <= 12000, "render vẫn cắt để giữ trần ngữ cảnh"


def test_EIDE_md_binh_thuong_thi_khong_bao_gi(tmp_path):
    md = EideMd.load(tmp_path / "EIDE.md", create_name="thu")
    md.save()
    assert not md.qua_tran and md.de_xuat_luoc() == []


# =========================================================================== MEM13 quên
def test_MEM13_forget_xoa_dong_va_ghi_BIA_MO(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    ex = {"summary": "quên", "why": "anh bảo quên", "sources": [],
          "diff_prev": "—", "next": "—", "confidence": "NGUOI"}

    agent.eide_md.append_line("Quy ước", "- Luôn dùng -O3 khi build", boi="run-0")
    agent.eide_md.save()

    r = agent.registry.run("memory.forget",
                           {"section": "Quy ước", "chua": "-O3", "explain": ex}, ctx)
    assert r.ok, r.error
    assert "-O3" not in agent.eide_md.get("Quy ước")

    tomb = [e for e in agent.ledger.read() if e.kind == "tombstone"]
    assert len(tomb) == 1 and "-O3" in tomb[0].data["noi_dung"]
    assert "ĐỪNG nhắc lại" in r.data["note_vi"]


def test_MEM13_forget_dong_khong_co_thi_noi_that(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    ex = {"summary": "x", "why": "y", "sources": [], "diff_prev": "—",
          "next": "—", "confidence": "NGUOI"}
    r = agent.registry.run("memory.forget",
                           {"section": "Quy ước", "chua": "không có câu này",
                            "explain": ex}, ctx)
    assert not r.ok and "Không có dòng nào" in r.error.message_vi


def test_memory_status_noi_duoc_dang_nho_gi(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    agent.eide_md.save()
    r = agent.registry.run("memory.status", {}, ctx)
    assert r.ok
    assert r.data["eide_md"]["tran"] == 3000
    assert "Đừng" in r.data["eide_md"]["muc"]
    assert r.data["da_quen"] == []


# =========================================================================== MEM16 tra
def test_MEM16_ledger_query_tra_duoc_qua_khu(chay, make_agent):
    from eide.llm.gateway import Response
    from eide.loop import TurnContext
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "mình muốn truyền tệp bằng MTP chứ không dùng USB MSC"})

    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-2")
    r = agent.registry.run("ledger.query", {"chua": "MTP"}, ctx)
    assert r.ok and r.data["tong"] >= 1
    assert any("MTP" in s["tom_tat"] for s in r.data["su_kien"])


def test_MEM16_khong_tim_thay_thi_NOI_THANG(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("ledger.query", {"chua": "chưa ai từng nói câu này"}, ctx)
    assert r.ok and r.data["tong"] == 0
    assert "đừng dựng lại câu chuyện" in r.data["note_vi"].lower()


def test_MEM16_hien_phap_bat_TRA_truoc_khi_tra_loi():
    from eide.context.assemble import CONSTITUTION_PATH

    s = CONSTITUTION_PATH.read_text("utf-8")
    assert "ledger.query" in s and "TRA, đừng nhớ" in s
    assert "blob.read" in s, "mô hình phải biết cách đọc lại phần đã cắt"


def test_hien_phap_khong_day_goi_cong_cu_KHONG_TON_TAI():
    """Một chỉ dẫn gọi công cụ không có thật là một lời hứa hão với mô hình."""
    import re

    from eide.context.assemble import CONSTITUTION_PATH
    from eide.tools import build_registry

    reg = build_registry()
    s = CONSTITUTION_PATH.read_text("utf-8")
    nhac = set(re.findall(r"`([a-z_]+\.[a-z_]+)\(?`?", s))
    khong_co = {t for t in nhac if reg.get(t) is None}
    assert not khong_co, f"hiến pháp nhắc công cụ không tồn tại: {sorted(khong_co)}"


def test_MEM18_danh_dau_KHONG_duoc_lam_RUNG_chuoi_hash(tmp_path):
    """Lỗi tìm ra khi chạy thật: `mark()` đọc qua from_dict→to_dict làm rụng hai
    trường hash, và một lần đánh dấu là xoá chuỗi của CẢ tệp."""
    from eide.changeset import Changeset, ChangesetLog, Touch

    p = tmp_path / "cs.jsonl"
    log = ChangesetLog(p)
    for i in range(3):
        log.append(Changeset(id=f"cs-{i}", ts="2026-09-25T00:00:00Z", author="human",
                             touches=[Touch(f"FR-{i}", "artefact", "create")]))
    log.mark("cs-1", acknowledged_by_agent="run-7")

    ds = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()]
    assert all("hash" in d and "prev_hash" in d for d in ds), "đánh dấu làm rụng hash"
    ok, vi = ChangesetLog(p).verify()
    assert ok, vi


def test_MEM18_dong_chua_ky_KHONG_duoc_bao_la_toan_ven(tmp_path):
    """N6 áp vào chính phép kiểm: "chưa kiểm được" khác "đã kiểm và đạt"."""
    from eide.changeset import ChangesetLog

    p = tmp_path / "cs.jsonl"
    p.write_text(json.dumps({"id": "cs-0", "ts": "t", "author": "human",
                             "touches": []}, ensure_ascii=False) + "\n", "utf-8")
    ok, vi = ChangesetLog(p).verify()
    assert not ok and "không kiểm được" in vi
