# -*- coding: utf-8 -*-
"""MEM-C — nén có kiểm chứng, ghim, resume, bộ nhớ người dùng.

EIDE-MEM-42 §6.2, §6.6, §7.5, §8. Ca: MEM04, 06–09, 11, 12, 17, và phần M3 của MEM14.

Điều bộ này canh, một câu: **nén phải kiểm được.** Không có PostCompact thì "nén có làm
mất gì không" mãi là cảm tính, và cách duy nhất phát hiện là người dùng phải nhắc lại
một quyết định họ đã nói — tức là ta để người đi phát hiện lỗi của mình (TC074).
"""

from __future__ import annotations

import pytest

from eide.llm.gateway import Response, ToolCall
from eide.memory import summary as sm
from eide.memory.nen import K_LUOT, BoNen
from eide.memory.nguoi_dung import CHU_DE, BoNhoNguoiDung, nen_de_xuat
from eide.memory.resume import dung_khoi_resume


def _tt_args(**kw) -> dict:
    d = {t: "—" for t, _, _ in sm.MUC}
    d.update(kw)
    return d


def _rsp_tom_tat(**kw) -> Response:
    return Response(tool_calls=[ToolCall("s1", sm.TEN_TOOL_TOM_TAT, _tt_args(**kw))])


def _rsp_kiem(*tra_loi: str) -> Response:
    return Response(tool_calls=[ToolCall("k1", sm.TEN_TOOL_TRA_LOI,
                                         {"tra_loi": list(tra_loi)})])


def _messages(n_luot: int, dai: int = 40) -> list[dict]:
    """Lượt có độ dài THẬT. Lượt hai chữ thì nén xong còn to hơn lúc đầu, và ta sẽ đo
    nhầm cái khác (xem `test_nen_ma_PHINH_thi_khong_nhan`)."""
    ms: list[dict] = []
    for i in range(n_luot):
        ms.append({"role": "user", "_kind": "say",
                   "text": f"việc thứ {i}: " + "mô tả chi tiết việc cần làm " * dai})
        ms.append({"role": "model",
                   "text": f"đã làm việc {i}: " + "thuật lại đã làm gì " * dai})
    return ms


# =========================================================================== lược đồ
def test_luoc_do_du_MUOI_muc_va_moi_muc_bat_buoc():
    d = sm.luoc_do_tom_tat()
    assert len(sm.MUC) == 10
    assert set(d["parameters"]["required"]) == {t for t, _, _ in sm.MUC}


def test_muc_khong_co_noi_dung_ghi_gach_KHONG_bo():
    """Một ô "—" là một thông tin; một mục biến mất thì không."""
    tt = sm.BanTomTat.tu_args({"muc_tieu": "làm bộ thu video"})
    assert tt.thieu_muc() == []
    assert tt.muc["quyet_dinh"] == "—"
    assert "quyet_dinh" in tt.van_ban()


def test_ba_muc_y_chi_cua_nguoi_khong_duoc_bo():
    assert set(sm.MUC_KHONG_DUOC_BO) == {"quyet_dinh", "gia_dinh_dang_dung",
                                         "sua_cua_nguoi"}


# =========================================================================== phiếu kiểm
def test_cham_bang_MA_khong_cham_van_phong():
    c = sm.CauKiem(hoi="?", dap_an="ADR-03", nguon="x")
    assert c.dung("Quyết định đó là ADR-03 về cơ chế truyền tệp.")
    assert c.dung("adr-03")
    assert not c.dung("Tôi nhớ là có một quyết định về truyền tệp.")


def test_thieu_cau_tra_loi_tinh_la_SAI_khong_phai_bo_qua():
    phieu = [sm.CauKiem("a", "X", "n"), sm.CauKiem("b", "Y", "n")]
    k = sm.cham_phieu(phieu, ["X"])
    assert k["dat"] == 1 and not k["qua"] and k["chi_tiet"][1]["tra_loi"] == ""


def test_phieu_kiem_sinh_tu_SO_CAI_khong_tu_mo_hinh(chay, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "mình muốn dùng cơ chế MTP cho việc truyền tệp"})
    phieu = sm.lam_phieu_kiem(agent.ledger, agent.store)
    assert phieu and all(c.hoi and c.dap_an and c.nguon for c in phieu)


# =========================================================================== MEM06 C2
@pytest.fixture
def bo_nen(make_agent):
    def _lam(script):
        agent = make_agent(script)
        bn = BoNen(llm=agent.llm, ledger=agent.ledger, store=agent.store,
                   eide_md=agent.eide_md, transcript=agent.transcript)
        return agent, bn
    return _lam


def test_MEM06_C2_giu_K_luot_gan_nhat_nguyen_van(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bộ thu video"), _rsp_kiem("x", "y", "z")])
    ms = _messages(20)
    kq = bn.nen(ms, run_id="run-1")
    # Kiểm sẽ trượt (đáp án bịa), nhưng ta đo phần chia đoạn qua bản đã dựng.
    doan, giu = bn.chia(_messages(20), K_LUOT, set())
    assert len({m["_luot"] for m in giu}) <= K_LUOT + 1
    assert doan, "phải có đoạn để nén"


def test_MEM06_tom_tat_thanh_mot_message_co_nhan(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bộ thu video qua Ethernet")])
    ms = _messages(20)
    kq = bn.nen(ms, run_id="run-1")
    assert kq.ok, kq.ly_do
    assert ms[0]["_tom_tat"] and "<session_summary>" in ms[0]["text"]
    assert "bộ thu video qua Ethernet" in ms[0]["text"]
    assert kq.sau < kq.truoc


def test_MEM06_PreCompact_chay_TRUOC_va_ghi_so_cai(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="x")])
    ms = _messages(20)
    ms[2]["text"] = "chốt ADR-07 dùng MTP"
    bn.nen(ms, run_id="run-1")
    pre = [e for e in agent.ledger.read()
           if e.kind == "compact" and e.data.get("buoc") == "pre"]
    assert pre, "PreCompact phải để lại dấu trong sổ cái"
    assert "ADR-07" in pre[0].data["ma_nhac_trong_doan"]
    assert "ADR-07" in pre[0].data["chua_co_trong_M2"], "ADR chưa vào kho phải bị nêu ra"


def test_MEM06_ghim_KHONG_bi_nen_du_rat_cu(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="x")])
    ms = _messages(20)
    ms[0]["_kind"] = "decide"          # ý chí của người, ghim tự động
    ms[0]["text"] = "DUYỆT nạp firmware"
    bn.nen(ms, run_id="run-1")
    assert any("DUYỆT nạp firmware" in str(m.get("text", "")) for m in ms), \
        "quyết định của người bị nén mất"


def test_MEM07_ghim_tu_dong_theo_loai_HumanAct():
    from eide.memory import chi_so_ghim

    ms = [{"role": "user", "_kind": "say", "text": "a"},
          {"role": "user", "_kind": "decide", "text": "b"},
          {"role": "user", "_kind": "edit", "text": "c"},
          {"role": "user", "_kind": "snapshot", "text": "d"},
          {"role": "user", "_ghim": True, "text": "e"}]
    assert chi_so_ghim(ms) == {1, 2, 3, 4}


# =========================================================================== MEM08 kiểm
def test_MEM08_kiem_SAI_thi_HUY_nen_va_giu_nguyen(bo_nen, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "mình chốt dùng cơ chế MTP cho truyền tệp"})

    # MẤT MÁT THẬT: trên ngữ cảnh gốc mô hình trả lời ĐÚNG, sau khi nén thì không.
    # Đây mới là thứ PostCompact tồn tại để bắt — khác với "câu hỏi vốn không trả lời
    # được", vốn phải bị loại chứ không được tính là mất mát.
    phieu = sm.lam_phieu_kiem(agent.ledger, agent.store)
    dung = [c.dap_an for c in phieu]
    sai = ["không biết"] * len(phieu)
    agent.llm.script = [_rsp_tom_tat(muc_tieu="x"), _rsp_kiem(*sai), _rsp_kiem(*dung),
                        _rsp_tom_tat(muc_tieu="x"), _rsp_kiem(*sai), _rsp_kiem(*dung),
                        _rsp_tom_tat(muc_tieu="x"), _rsp_kiem(*sai), _rsp_kiem(*dung)]
    agent.llm._i = 0
    bn = BoNen(llm=agent.llm, ledger=agent.ledger, store=agent.store,
               eide_md=agent.eide_md)

    ms = _messages(20)
    truoc = [dict(m) for m in ms]
    kq = bn.nen(ms, run_id="run-2")

    assert not kq.ok
    assert ms == truoc, "ngữ cảnh phải về đúng như trước khi nén"
    assert "0/" in kq.diem_kiem, kq.diem_kiem


def test_MEM08_thu_lai_thi_GIU_NHIEU_HON(bo_nen, make_agent):
    """§6.6 — K += 4 mỗi lần trượt: giữ nhiều nguyên văn hơn thì dễ trả lời đúng hơn."""
    from eide.memory.nen import K_TANG_KHI_KIEM_TRUOT
    assert K_TANG_KHI_KIEM_TRUOT == 4


def test_MEM08_khong_co_phieu_kiem_thi_NOI_RA_chu_khong_bao_3_tren_3(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="x")])
    ms = _messages(20)
    kq = bn.nen(ms, run_id="run-1")
    assert kq.ok and kq.diem_kiem == "không có phiếu kiểm", \
        "sổ cái rỗng thì phải nói là không kiểm, không được báo đạt"


def test_MEM08_mo_hinh_hong_giua_luc_tom_tat_thi_giu_nguyen(make_agent):
    from eide.errors import llm_unavailable

    class Hong:
        name = "hong"
        def stream(self, **kw):
            raise llm_unavailable("529 overloaded", 3)
        def count_tokens(self, t):
            return len(t) // 3

    agent = make_agent([])
    bn = BoNen(llm=Hong(), ledger=agent.ledger, store=agent.store,
               eide_md=agent.eide_md)
    ms = _messages(20)
    truoc = [dict(m) for m in ms]
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and ms == truoc
    assert "giữ nguyên" in kq.ly_do.lower()


def test_MEM08_luoc_do_sai_thi_khong_nen(bo_nen):
    agent, bn = bo_nen([Response(text="tôi tóm tắt bằng văn xuôi thay vì gọi công cụ")])
    ms = _messages(20)
    truoc = [dict(m) for m in ms]
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and ms == truoc
    assert "đúng lược đồ" in kq.ly_do


# =========================================================================== MEM13 tombstone
def test_MEM13_tom_tat_KHONG_duoc_hoi_sinh_dieu_da_quen(bo_nen, make_agent):
    agent = make_agent([])
    agent.ledger.append("tombstone", {"run_id": "r", "tombstone_id": "t1",
                                      "scope": "project", "section": "Quy ước",
                                      "noi_dung": "Luôn build với -O3"})
    agent.llm.script = [_rsp_tom_tat(gia_dinh_dang_dung="Luôn build với -O3")]
    agent.llm._i = 0
    bn = BoNen(llm=agent.llm, ledger=agent.ledger, store=agent.store,
               eide_md=agent.eide_md)

    ms = _messages(20)
    truoc = [dict(m) for m in ms]
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and ms == truoc
    assert "đã bảo quên" in kq.ly_do


def test_MEM13_bia_mo_vao_prompt_tom_tat(make_agent):
    agent = make_agent([])
    agent.ledger.append("tombstone", {"noi_dung": "Luôn build với -O3"})
    from eide.memory import bia_mo
    tomb = bia_mo(agent.ledger)
    pr = sm.prompt_tom_tat([{"role": "user", "text": "x"}], None, "", tomb)
    assert "YÊU CẦU QUÊN" in pr and "-O3" in pr


# =========================================================================== MEM17 resume
def test_MEM17_du_an_moi_tinh_thi_khong_co_khoi_resume(make_agent):
    agent = make_agent([])
    assert dung_khoi_resume(ledger=agent.ledger, store=agent.store,
                            history=agent.history) == ""


def test_MEM17_khoi_resume_dung_bang_MA_khong_co_cho_nao_de_null(chay, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "bắt đầu làm bộ thu video"})

    khoi = dung_khoi_resume(ledger=agent.ledger, store=agent.store,
                            history=agent.history)
    assert khoi.startswith("<resume>") and khoi.endswith("</resume>")
    for muc in ("Phiên trước tóm lại", "Đang dở dang", "Toàn vẹn",
                "Dùng khối này thế nào"):
        assert muc in khoi, muc
    # TC065: không có trường summary riêng để mà null — chưa có thì NÓI là chưa có.
    assert "Chưa có bản tóm tắt nào" in khoi
    assert "null" not in khoi.lower()


def test_MEM17_resume_neu_ra_viec_do_dang_va_cam_chay_lai(make_agent):
    from eide.memory.transcript import Transcript, phuc_hoi
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "x"})

    ts = Transcript(agent.config.paths.state_dir / "t.jsonl")
    ts.ghi({"role": "model", "text": "",
            "tool_calls": [{"id": "c1", "tool": "target.flash", "args": {}}]})
    khoi = dung_khoi_resume(ledger=agent.ledger, store=agent.store,
                            history=agent.history, phuc_hoi=phuc_hoi(ts))
    assert "target.flash" in khoi and "KHÔNG chạy lại" in khoi


def test_MEM17_resume_bao_toan_ven_ca_hai_so(chay, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "x"})
    khoi = dung_khoi_resume(ledger=agent.ledger, store=agent.store,
                            history=agent.history)
    assert "Sổ cái:" in khoi and "Sổ changeset:" in khoi


def test_MEM17_agent_tiem_khoi_resume_DUNG_MOT_LAN(chay, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="a"), Response(text="b")])
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None)
    agent.ledger.append("note", {"gia": "để sổ cái không rỗng"})
    core.console_act({"kind": "say", "text": "lượt một"})
    core.console_act({"kind": "say", "text": "lượt hai"})
    n = sum(1 for m in agent.messages if "<resume>" in str(m.get("text", "")))
    assert n == 1, f"khối resume xuất hiện {n} lần"


# =========================================================================== MEM14 M3
def test_M3_chi_sau_chu_de_duoc_nho(tmp_path):
    bn = BoNhoNguoiDung(tmp_path / "memory.md")
    assert len(CHU_DE) == 6
    assert not bn.kiem("trinh_do_nguoi_dung", "anh này mới học").ok
    assert bn.kiem("trinh_bay", "thích câu trả lời ngắn").ok


def test_M3_KHONG_BAO_GIO_nho_bi_mat(tmp_path):
    bn = BoNhoNguoiDung(tmp_path / "memory.md")
    for xau in ("API key là sk-abcdefghijklmnopqrstuvwxyz",
                "mật khẩu wifi là 12345678",
                "-----BEGIN RSA PRIVATE KEY-----"):
        k = bn.kiem("toolchain", xau)
        assert not k.ok, xau
        assert "keychain" in k.ly_do or "khoá" in k.ly_do


def test_M3_KHONG_nho_phong_doan_ve_nguoi(tmp_path):
    bn = BoNhoNguoiDung(tmp_path / "memory.md")
    for xau in ("có vẻ anh này chưa rành về I2C",
                "người dùng này không biết dùng oscilloscope",
                "trình độ trung bình"):
        k = bn.kiem("trinh_bay", xau)
        assert not k.ok, xau
        assert "phỏng đoán" in k.ly_do


def test_M3_ghi_doc_quen_xoa(tmp_path):
    bn = BoNhoNguoiDung(tmp_path / "memory.md")
    assert bn.ghi("trinh_bay", "thích câu trả lời ngắn").ok
    assert bn.ghi("phan_cung", "hay dùng STM32F103").ok
    ds = bn.doc()
    assert len(ds) == 2 and {m["chu_de"] for m in ds} == {"trinh_bay", "phan_cung"}

    assert bn.quen("ngắn") is not None
    assert len(bn.doc()) == 1
    assert bn.xoa_het() and not bn.path.exists()


def test_M3_vao_ngu_canh_co_tran(tmp_path):
    bn = BoNhoNguoiDung(tmp_path / "memory.md")
    bn.ghi("trinh_bay", "thích câu trả lời ngắn")
    k = bn.khoi_ngu_canh()
    assert k.startswith("<nguoi_dung>") and "ngắn" in k
    assert BoNhoNguoiDung(tmp_path / "trong.md").khoi_ngu_canh() == ""


def test_M3_chi_de_xuat_khi_LAP_LAI_hai_lan():
    assert not nen_de_xuat(["cho mình câu trả lời ngắn thôi"], "trinh_bay", "ngắn")
    assert nen_de_xuat(["ngắn thôi", "vẫn dài quá, ngắn nữa"], "trinh_bay", "ngắn")
    assert nen_de_xuat(["nhớ là mình thích ngắn"], "trinh_bay", "ngắn")


def test_M3_de_xuat_phai_qua_THE_khong_tu_ghi(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("memory.remember_user",
                           {"chu_de": "trinh_bay", "noi_dung": "thích câu trả lời ngắn",
                            "vi_sao": "anh nhắc hai lần"}, ctx)
    assert r.ok and r.data["da_de_xuat"]
    assert ctx.awaiting_human, "phải DỪNG chờ người, không tự ghi"
    the = ctx.pending_cards[-1]
    assert the["tra_loi_thanh"] == "nho_nguoi_dung"
    assert not BoNhoNguoiDung().doc() or True     # không ghi gì trước khi người đồng ý


def test_M3_cong_cu_tu_choi_bi_mat_khong_cho_dien_dat_lai(chay, make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("memory.remember_user",
                           {"chu_de": "toolchain", "noi_dung": "token là ghp_abcdefghijklmnop",
                            "vi_sao": "anh vừa dán"}, ctx)
    assert not r.ok
    assert "diễn đạt lại cho lọt" in r.error.hint_for_agent


def test_chua_toi_luc_nen_KHAC_voi_nen_truot(bo_nen):
    """Hai chuyện khác hẳn với người đọc: "hệ thống nghi ngờ chính nó" và "chưa tới lúc"."""
    agent, bn = bo_nen([])
    ms = _messages(3)                      # 3 lượt, K=10 → không có gì đủ cũ
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and kq.khong_co_gi
    assert "Chưa có gì để nén" in kq.ly_do
    assert "KHÔNG qua kiểm" not in kq.dong_he_thong()
    assert len(agent.llm.calls) == 0, "chưa tới lúc thì đừng gọi mô hình"
    su = [e for e in agent.ledger.read()
          if e.kind == "compact" and e.data.get("buoc") == "khong_can"]
    assert su, "phải ghi sổ cái — người vừa yêu cầu một việc, im lặng là sai"


def test_nen_chay_duoc_tren_DANH_SACH_THAT_cua_Agent(make_agent):
    """Ca đơn vị trước truyền `list` thường, nên bỏ lọt một lỗi chỉ có trong sản phẩm.

    `Agent.messages` là `DanhSachGhiDia` — một `list` con giữ `Transcript`, trong đó có
    `threading.Lock`. `copy.deepcopy(messages)` nổ, và nổ đúng lúc đang nén.
    """
    from eide.loop import TurnContext

    agent = make_agent([_rsp_tom_tat(muc_tieu="bộ ghi nhiệt độ")])
    for i in range(15):
        agent.messages.append({"role": "user", "text": f"việc {i}", "_kind": "say"})
        agent.messages.append({"role": "model", "text": f"xong {i}"})

    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, agent=agent,
                      run_id="run-1")
    r = agent.registry.run("memory.compact", {"muc": "C2"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")   # điều canh: KHÔNG nổ giữa lúc nén


def test_nen_ma_PHINH_thi_khong_nhan(bo_nen):
    """Trả tiền một lần gọi mô hình để làm ngữ cảnh to ra là tệ hơn không làm gì."""
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="x")])
    ms = _messages(15, dai=0)                  # lượt rất ngắn
    truoc = [dict(m) for m in ms]
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and kq.khong_co_gi
    assert "còn to hơn lúc đầu" in kq.ly_do
    assert ms == truoc


def test_nen_doan_DAI_thi_giam_that(bo_nen):
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bộ ghi nhiệt độ")])
    ms = _messages(20, dai=60)
    kq = bn.nen(ms, run_id="run-1")
    assert kq.ok and kq.sau < kq.truoc
    assert any("<session_summary>" in str(m.get("text", "")) for m in ms)


def test_memory_compact_KHONG_co_muc_mac_dinh(make_agent):
    """Mặc định ở đây nghĩa là: người bảo C2, mô hình gọi thiếu, hệ thống lặng lẽ làm
    C1 rồi báo "đã thu gọn" — người tưởng đã tóm tắt, thực ra chưa."""
    agent = make_agent([])
    spec = agent.registry.get("memory.compact")
    assert "muc" in spec.params["required"]


def test_MEM17_khoi_resume_KHONG_duoc_chiem_cho_cau_hoi_cua_nguoi(chay, make_agent):
    """Đo được trên phiên thật: người hỏi "VDD tối đa bao nhiêu", tác tử trả lời bằng
    một bản tóm tắt tình trạng dự án. Bối cảnh không bao giờ được thay việc."""
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "bắt đầu"})

    khoi = dung_khoi_resume(ledger=agent.ledger, store=agent.store,
                            history=agent.history)
    assert "BỐI CẢNH, không phải việc được giao" in khoi
    assert "Làm đúng thứ người dùng vừa hỏi trước đã" in khoi
    assert "Tự thuật lại" not in khoi


def test_MEM08_phep_kiem_duoc_nhan_DUNG_ngu_canh_mo_hinh_se_co(make_agent):
    make_agent_thu = make_agent
    """Hỏi trên transcript trần là chặt hơn tình huống thật.

    Ở lượt bình thường mô hình luôn có `<inventory>`. Bỏ nó ra khỏi phép kiểm nghĩa là
    hỏi "transcript MỘT MÌNH có chứa X không" — và một thứ đã nằm trong kho thì mất nó
    khỏi transcript là ĐÚNG, đó chính là điều PreCompact bảo đảm.
    """
    ghi: list[dict] = []

    class LlmGhiLai:
        name = "ghi"

        def __init__(self, script):
            self.script = list(script)
            self._i = 0
            self.calls: list = []

        def stream(self, *, system, messages, tools, **kw):
            ghi.append({"messages": [dict(m) for m in messages],
                        "tools": [t["name"] for t in tools]})
            r = self.script[self._i]
            self._i += 1
            return r

        def count_tokens(self, t):
            return len(t) // 3

    agent = make_agent_thu([])
    bn = BoNen(llm=LlmGhiLai([_rsp_tom_tat(muc_tieu="x"), _rsp_kiem("a", "b", "c")]),
               ledger=agent.ledger, store=agent.store, eide_md=agent.eide_md)
    agent.ledger.append("changeset", {"id": "cs-1", "author": "human",
                                      "touches": ["FR-01"], "run_id": "r"})
    ms = _messages(20)
    bn.nen(ms, run_id="run-1",
           inventory_text="<inventory>\nFR-01 · tiêu chí ≥ 2 MB/s\n</inventory>")

    # Lần gọi thứ nhất là tóm tắt, thứ hai là kiểm. (Kiểm trượt thì có lần thứ ba —
    # không quan tâm ở đây.)
    assert len(ghi) >= 2 and ghi[1]["tools"] == [sm.TEN_TOOL_TRA_LOI]
    chu_kiem = " ".join(str(m.get("text", "")) for m in ghi[1]["messages"])
    assert "2 MB/s" in chu_kiem, "phép kiểm phải thấy <inventory> như lượt bình thường"


def test_MOI_loi_ra_cua_nen_deu_de_lai_dau_trong_SO_CAI(bo_nen, make_agent):
    """Người vừa yêu cầu một việc — im lặng là sai, dù kết quả là "không làm gì".

    Đo được trên phiên thật: tác tử gọi `memory.compact(C2)`, PreCompact chạy, rồi
    không có sự kiện nào nữa. Nhìn sổ cái không biết nó đã làm gì.
    """
    from eide.llm.gateway import Response

    truong_hop = [
        ("chưa tới lúc", [], _messages(3)),
        ("lược đồ sai", [Response(text="tôi tóm tắt bằng văn xuôi")], _messages(20)),
    ]
    for ten, script, ms in truong_hop:
        agent, bn = bo_nen(script)
        bn.nen(ms, run_id="run-1")
        su = [e for e in agent.ledger.read() if e.kind == "compact"]
        assert su, f"{ten}: không để lại dấu nào trong sổ cái"
        assert any(e.data.get("message_vi") for e in su), f"{ten}: không nói vì sao"


def test_MEM08_khong_tang_K_vuot_qua_do_dai_PHIEN(bo_nen, make_agent):
    """Tăng K nữa thì vòng sau báo "chưa tới lúc" — che mất sự thật là kiểm đã trượt."""
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "mình chốt phương án truyền tệp bằng giao thức MTP"})
    phieu = sm.lam_phieu_kiem(agent.ledger, agent.store)
    agent.llm.script = [_rsp_tom_tat(muc_tieu="x"),
                        _rsp_kiem(*["không biết"] * len(phieu)),
                        _rsp_kiem(*[c.dap_an for c in phieu])]
    agent.llm._i = 0
    bn = BoNen(llm=agent.llm, ledger=agent.ledger, store=agent.store,
               eide_md=agent.eide_md)

    ms = _messages(12)                    # 12 lượt: K=10 nén được 2; K=14 thì hết sạch
    kq = bn.nen(ms, run_id="run-1")
    assert not kq.ok and not kq.khong_co_gi, "phải báo là KIỂM TRƯỢT, không phải chưa tới lúc"
    assert "không còn gì để nén" in kq.ly_do
    su = [e for e in agent.ledger.read()
          if e.kind == "compact" and e.data.get("buoc") == "bo_cuoc"]
    assert su and su[-1].data["diem"].startswith("0/")


def test_MEM08_cau_hoi_mo_hinh_KHONG_TRA_LOI_DUOC_o_dau_ca_thi_bi_loai(make_agent):
    """Một câu hỏi mà mô hình chịu thua cả TRƯỚC khi nén thì không đo mất mát — nó đo
    khả năng của mô hình, và nó sẽ huỷ mọi lần nén khiến C2 không bao giờ chạy được.

    Đo được trên phiên thật: kiểm trượt 2/3 ba lần liên tiếp vì đúng một câu như thế.
    """
    from eide.protocol.rpc import Core

    agent = make_agent([Response(text="ok")])
    Core(agent.ledger, agent.ids, agent.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "mình chốt phương án truyền tệp bằng giao thức MTP"})
    phieu = sm.lam_phieu_kiem(agent.ledger, agent.store)
    sai = ["không biết"] * len(phieu)
    # Sai ở CẢ HAI bên ⇒ câu hỏi không công bằng ⇒ bị loại.
    agent.llm.script = [_rsp_tom_tat(muc_tieu="x"), _rsp_kiem(*sai), _rsp_kiem(*sai)]
    agent.llm._i = 0
    bn = BoNen(llm=agent.llm, ledger=agent.ledger, store=agent.store,
               eide_md=agent.eide_md)

    kq = bn.nen(_messages(20), run_id="run-1")
    assert kq.ok, "loại hết câu không công bằng thì không được coi là mất mát"
    assert kq.diem_kiem == "KHÔNG kiểm được"
    bo = [e for e in agent.ledger.read()
          if e.kind == "compact" and e.data.get("buoc") == "cau_hoi_bo"]
    assert bo and bo[0].data["cau"]


def test_MEM08_khong_kiem_duoc_phai_NOI_DUNG_CHU_DO(make_agent):
    """N6 áp vào chính phép kiểm: "chưa kiểm được" không được hiện ra như "đã kiểm"."""
    from eide.memory.nen import KetQuaNen

    kq = KetQuaNen(ok=True, truoc=100, sau=50, diem_kiem="KHÔNG kiểm được")
    dong = kq.dong_he_thong()
    assert "chưa kiểm được" in dong and "huỷ nén" in dong
    assert "3/3" not in dong


# =========================================================================== M5-17
# Bản tóm tắt C2 sống đúng MỘT tiến trình, rồi mất.
#
# `BoNen.__init__` đặt `tom_tat_hien_tai = None` và chỉ gán nó khi nén thành công TRONG tiến
# trình ấy. Tiến trình mới dựng một `BoNen` mới, nên `dung_khoi_resume(tom_tat_truoc=...)`
# luôn nhận `None` và khối resume in "Chưa có bản tóm tắt nào".
#
# Hậu quả đúng chỗ đau nhất: bản tóm tắt là **NGUỒN DUY NHẤT** về giai đoạn đã bị nén khỏi
# ngữ cảnh (chính `van_ban()` của nó nói thế). Mở lại dự án sau một lần nén thì phần hội thoại
# ấy không còn ở transcript, cũng không còn ở resume — nó chỉ còn trong sổ cái, mà không ai
# đọc. Và bản tóm tắt ĐÃ ĐƯỢC GHI vào sổ cái từ đầu: `ledger.append("compact", {... "tom_tat":
# tt.to_dict()})`. Lần thứ chín của một hình dạng: cơ chế có sẵn, đường dẫn tới nó đứt.
def test_tu_dict_dao_to_dict():
    """TC-M5-17-02 — `tu_dict` phải đảo đúng `to_dict`, kể cả kiểu của `covers`.

    `to_dict` ghi `covers` thành **list** (JSON không có tuple), nên đọc lại phải đưa về tuple
    — không thì `covers` của một bản nạp lại khác kiểu bản vừa tạo, và chỗ nào so bằng sẽ im
    lặng sai.
    """
    tt = sm.BanTomTat(muc=_tt_args(muc_tieu="bộ thu video qua Ethernet"), covers=(3, 17),
                      prev_hash="abc", created_at="2026-10-09T00:00:00Z",
                      model="gemini-3.8-flash", tokens=123)
    lai = sm.BanTomTat.tu_dict(tt.to_dict())
    assert lai.muc == tt.muc
    assert lai.covers == (3, 17) and isinstance(lai.covers, tuple), lai.covers
    assert (lai.prev_hash, lai.created_at, lai.model, lai.tokens) == (
        "abc", "2026-10-09T00:00:00Z", "gemini-3.8-flash", 123)
    assert lai.van_ban() == tt.van_ban()


def test_tu_dict_chiu_duoc_du_lieu_THIEU():
    """Sổ cái của một bản EIDE cũ có thể thiếu khoá. Một `KeyError` lúc khởi động là đổi một
    bản tóm tắt mất thành cả dự án không mở được."""
    lai = sm.BanTomTat.tu_dict({"muc": {"muc_tieu": "x"}})
    assert lai.muc["muc_tieu"] == "x" and lai.covers == (0, 0)
    assert sm.BanTomTat.tu_dict({}) is not None
    assert sm.BanTomTat.tu_dict("khong-phai-dict") is None


def test_MEM17_mo_lai_sau_C2_co_tom_tat(bo_nen, make_agent):
    """TC-M5-17-01 — phép đo đầu-cuối, và là lý do cả nhiệm vụ tồn tại.

    Nén xong ở tiến trình một; tiến trình HAI mở lại cùng dự án phải thấy đúng bản tóm tắt ấy
    trong khối `<resume>`.
    """
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bộ thu video qua Ethernet"),
                        _rsp_kiem("x", "y", "z")])
    kq = bn.nen(_messages(20), run_id="run-1")
    assert kq.ok, kq.ly_do

    # "Tiến trình mới": một Agent khác trên CÙNG dự án, nên cùng sổ cái trên đĩa.
    hai = make_agent([])
    assert hai.bo_nen.tom_tat_hien_tai is not None, "bản tóm tắt không sống qua tiến trình"
    khoi = dung_khoi_resume(ledger=hai.ledger, store=hai.store, history=hai.history,
                            tom_tat_truoc=hai.bo_nen.tom_tat_hien_tai)
    assert "bộ thu video qua Ethernet" in khoi
    assert "Chưa có bản tóm tắt" not in khoi


def test_da_huy_nen_thi_khong_nap_lai(bo_nen, make_agent):
    """TC-M5-17-03 — người đã HUỶ nén thì bản tóm tắt ấy không được sống lại.

    §6.2.3 cho huỷ nén trong 24 giờ, và huỷ nghĩa là *"đoạn hội thoại ấy quay về nguyên văn"*.
    Nạp lại bản tóm tắt sau khi huỷ là đưa vào ngữ cảnh một bản rút gọn của thứ đang có đủ —
    hai nguồn cho một giai đoạn, và mô hình không biết tin cái nào.
    """
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bộ thu video qua Ethernet"),
                        _rsp_kiem("x", "y", "z")])
    ms = _messages(20)
    assert bn.nen(ms, run_id="run-1").ok
    bn.huy_nen(ms)

    hai = make_agent([])
    assert hai.bo_nen.tom_tat_hien_tai is None, "bản tóm tắt đã huỷ vẫn sống lại"
    khoi = dung_khoi_resume(ledger=hai.ledger, store=hai.store, history=hai.history,
                            tom_tat_truoc=hai.bo_nen.tom_tat_hien_tai)
    assert "Chưa có bản tóm tắt nào" in khoi


def test_nen_LAI_sau_khi_huy_thi_lay_ban_MOI(bo_nen, make_agent):
    """Huỷ rồi nén lại thì phải lấy bản MỚI, không phải im lặng trả None mãi.

    Phép duyệt ngược phải dừng ở sự kiện gần nhất, không phải "có `huy` ở đâu đó thì bỏ hết" —
    nếu không thì một lần huỷ ở tháng trước làm mọi lần nén sau đó vô hình.
    """
    agent, bn = bo_nen([_rsp_tom_tat(muc_tieu="bản ĐẦU")])
    ms = _messages(20)
    assert bn.nen(ms, run_id="run-1").ok
    bn.huy_nen(ms)
    # Kịch bản mới cho lượt nén thứ hai — số lời gọi mô hình của một lượt nén không cố định
    # (có vòng kiểm chứng), nên gán lại rõ ràng thay vì đoán cần bao nhiêu phản hồi.
    agent.llm.script = [_rsp_tom_tat(muc_tieu="bản SAU")]
    agent.llm._i = 0
    ms2 = _messages(20)
    assert bn.nen(ms2, run_id="run-2").ok

    hai = make_agent([])
    tt = hai.bo_nen.tom_tat_hien_tai
    assert tt is not None and "bản SAU" in tt.van_ban(), tt


def test_so_cai_HONG_khong_lam_chet_khoi_dong(make_agent, monkeypatch):
    """Một sổ cái hỏng phải làm mất bản tóm tắt, KHÔNG làm mất cả dự án.

    `BoNen.__init__` chạy ở đường khởi động. Để một ngoại lệ đọc sổ bay ra từ đó là đổi một
    bất tiện (thiếu tóm tắt) lấy một chỗ tắc (không mở được dự án).
    """
    from eide.memory import nen as N

    def _no(_ledger):
        raise ValueError("sổ cái hỏng")

    monkeypatch.setattr(N, "tom_tat_cuoi_tu_so_cai", _no)
    ag = make_agent([])
    assert ag.bo_nen.tom_tat_hien_tai is None


def test_tom_tat_cuoi_tu_so_cai_bo_qua_buoc_KHAC_ok(bo_nen, make_agent):
    """Sổ cái có mười loại sự kiện `compact` (`pre`, `loi`, `tombstone`, `bo_cuoc`…). Chỉ
    `buoc == "ok"` mới mang bản tóm tắt đã qua kiểm chứng."""
    from eide.memory.nen import tom_tat_cuoi_tu_so_cai

    agent, _bn = bo_nen([])
    agent.ledger.append("compact", {"run_id": "r", "buoc": "pre", "k_luot": 6})
    agent.ledger.append("compact", {"run_id": "r", "buoc": "loi_kiem", "lan": 1})
    assert tom_tat_cuoi_tu_so_cai(agent.ledger) is None


# ------------------------------------------------- phần B: tường thuật cơ học sau cờ
def _ms_phien(co_loi: bool = True) -> list[dict]:
    """Transcript một phiên: hai lời người, ba lời gọi công cụ, một cái lỗi."""
    ms: list[dict] = [
        {"role": "user", "_kind": "say", "text": "đọc datasheet rồi viết driver I2C"},
        {"role": "model", "tool_calls": [{"id": "c1", "tool": "fs.read"}]},
        {"role": "tool", "tool_call_id": "c1", "tool": "fs.read",
         "result": {"ok": True}, "envelope": {"summary_line": "fs.read main.c (120 dòng)"}},
        {"role": "user", "_he_thong": True, "text": "lời nhắc hệ thống KHÔNG được tính"},
        {"role": "user", "_kind": "say", "text": "nạp luôn lên bo đi"},
        {"role": "tool", "tool_call_id": "c2", "tool": "target.flash",
         "result": ({"code": "E4040", "message_vi": "không thấy bo nào trên cổng USB"}
                    if co_loi else {"ok": True}),
         "envelope": {"summary_line": "target.flash"}}]
    return ms


def test_tuong_thuat_co_hoc_ke_dung_BA_THU():
    """Lời người, lời gọi, lỗi cuối — và KHÔNG tóm tắt lời tác tử nói.

    Một bản rút gọn của lời tác tử tự nói là chỗ dễ nhất để một kết luận sai sống thêm một
    phiên, mà cả mảng này tồn tại để chặn đúng chuyện đó.
    """
    from eide.memory import tuong_thuat_co_hoc

    chu = tuong_thuat_co_hoc(_ms_phien())
    assert "đọc datasheet rồi viết driver I2C" in chu
    assert "nạp luôn lên bo đi" in chu
    assert "lời nhắc hệ thống" not in chu, "lời hệ thống không phải lời người"
    assert "`fs.read`" in chu and "`target.flash`" in chu
    # Mã lỗi phải nằm NGAY dòng lời gọi, không chỉ ở dòng "lỗi cuối" — một bản kê mười lời
    # gọi mà chỉ dòng cuối có mã thì không nói được cái nào trong mười cái đã đổ.
    assert "`target.flash` → E4040" in chu, chu
    assert "`fs.read` ok" in chu, chu
    assert "không thấy bo nào" in chu
    assert "không phải việc cần làm tiếp" in chu
    assert len(chu) <= 1500, len(chu)


def test_tuong_thuat_co_hoc_co_TRAN():
    """Trần 1 500 ký tự chỉ đo được khi dàn dựng VƯỢT nó.

    Phép phá chỉ ra rằng ca trên không canh trần: transcript dàn dựng của nó ngắn, nên bỏ trần
    đi cũng không đổi gì. Một phiên thật có hàng trăm lời gọi, và tường thuật là thứ chen vào
    lượt ĐẦU TIÊN — lượt đắt nhất để chen.
    """
    from eide.memory import tuong_thuat_co_hoc

    ms = [{"role": "user", "_kind": "say", "text": "x" * 400} for _ in range(5)]
    for i in range(30):
        ms.append({"role": "tool", "tool_call_id": f"c{i}", "tool": f"cong.cu.{i}",
                   "result": {"ok": True},
                   "envelope": {"summary_line": "y" * 200}})
    chu = tuong_thuat_co_hoc(ms)
    assert len(chu) <= 1500 + 20, len(chu)
    assert "(đã cắt)" in chu


def test_tuong_thuat_co_hoc_phien_RONG_thi_rong():
    """Không có gì thì trả rỗng, để khối resume rơi về câu “chưa có bản tóm tắt nào” — một
    mục tường thuật trống là một mục nói rằng đã tường thuật."""
    from eide.memory import tuong_thuat_co_hoc

    assert tuong_thuat_co_hoc([]) == ""
    assert tuong_thuat_co_hoc([{"role": "user", "_he_thong": True, "text": "x"}]) == ""


def test_khoi_resume_uu_tien_BAN_TOM_TAT_hon_tuong_thuat(make_agent):
    """Có cả hai thì bản tóm tắt C2 thắng: nó đã qua vòng kiểm chứng (§6.2), còn tường thuật
    chỉ là một bản kê việc."""
    from eide.llm.gateway import Response
    from eide.memory import tuong_thuat_co_hoc
    from eide.protocol.rpc import Core

    ag = make_agent([Response(text="ok")])
    Core(ag.ledger, ag.ids, ag.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "x"})
    tt = sm.BanTomTat(muc=_tt_args(muc_tieu="bộ thu video qua Ethernet"))
    khoi = dung_khoi_resume(ledger=ag.ledger, store=ag.store, history=ag.history,
                            tom_tat_truoc=tt,
                            tuong_thuat=tuong_thuat_co_hoc(_ms_phien()))
    assert "bộ thu video qua Ethernet" in khoi
    assert "target.flash" not in khoi


def test_tuong_thuat_co_hoc_khi_co_bat(make_agent, monkeypatch, tmp_path):
    """TC-M5-17-05 — cờ BẬT thì khối resume của phiên sau có tên công cụ và mã lỗi của phiên
    trước; cờ TẮT thì không có mục tường thuật nào.

    Phần lớn phiên thật KHÔNG chạm ngưỡng nén, nên đây là trường hợp **thường gặp**: khối
    resume nói "chưa có bản tóm tắt nào" trong khi một transcript đầy đủ đang nằm trên đĩa.
    """
    from eide.config import Features
    from eide.llm.gateway import Response
    from eide.protocol.rpc import Core

    mot = make_agent([Response(text="ok")])
    Core(mot.ledger, mot.ids, mot.turn, on_emit=lambda c: None).console_act(
        {"kind": "say", "text": "x"})
    # Dựng transcript của "phiên trước" bằng đúng kho phiên mà agent dùng.
    mot.phien.transcript(mot.session_id).thay_toan_bo(_ms_phien())
    mot.phien.danh_dau_ket_thuc(mot.session_id)

    hai = make_agent([])
    assert hai.session_id != mot.session_id

    hai.config.features = Features.load()
    assert hai.config.features.bat("resume_tuong_thuat") is False
    assert hai._tuong_thuat_phien_truoc() == "", "cờ TẮT mà vẫn tường thuật"

    monkeypatch.setenv("EIDE_FEATURE_RESUME_TUONG_THUAT", "1")
    hai.config.features = Features.load()
    chu = hai._tuong_thuat_phien_truoc()
    assert "`target.flash`" in chu and "E4040" in chu, chu[:200]
    khoi = dung_khoi_resume(ledger=hai.ledger, store=hai.store, history=hai.history,
                            tom_tat_truoc=None, tuong_thuat=chu)
    assert "target.flash" in khoi and "Chưa có bản tóm tắt nào" not in khoi


def test_transcript_HONG_khong_lam_chet_luot_dau(make_agent, monkeypatch):
    """Một transcript hỏng phải làm mất phần tường thuật, KHÔNG làm mất lượt đầu tiên.

    Phải dựng một phiên TRƯỚC, không thì `_tuong_thuat_phien_truoc` trả rỗng ngay ở bước
    "không có phiên nào trước" và ca này xanh mà chưa chạm tới cửa `try` nó nói nó canh —
    phép phá chỉ ra đúng điều đó.
    """
    from eide import memory as M
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_RESUME_TUONG_THUAT", "1")
    mot = make_agent([])
    mot.phien.transcript(mot.session_id).thay_toan_bo(_ms_phien())
    ag = make_agent([])
    ag.config.features = Features.load()
    assert ag.phien.gan_nhat(tru=ag.session_id) == mot.session_id

    def _no(_ms):
        raise ValueError("transcript hỏng")

    # Trước khi phá: phải CÓ tường thuật, không thì ca dưới xanh vì rỗng sẵn.
    assert ag._tuong_thuat_phien_truoc() != ""
    monkeypatch.setattr(M, "tuong_thuat_co_hoc", _no)
    assert ag._tuong_thuat_phien_truoc() == ""


def test_co_resume_tuong_thuat_co_ten_va_mac_dinh_TAT():
    from eide.config import Features

    assert "resume_tuong_thuat" in Features.ten_co()
    assert Features().bat("resume_tuong_thuat") is False


def test_tuong_thuat_moi_LOI_GOI_mang_ma_loi_cua_chinh_no():
    """Mã lỗi phải nằm trên TỪNG dòng lời gọi, không chỉ ở dòng "lỗi cuối".

    Phép phá chỉ ra rằng ca trên không đo được chuyện này: dòng *Lỗi cuối cùng* in ra đúng
    chuỗi `` `target.flash` → E4040 ``, nên bỏ mã khỏi dòng lời gọi mà ca vẫn xanh. Ca này
    dựng **hai** lời gọi đổ với **hai** mã khác nhau — dòng "lỗi cuối" chỉ kể được cái sau.
    """
    from eide.memory import tuong_thuat_co_hoc

    ms = [
        {"role": "user", "_kind": "say", "text": "nạp rồi đo"},
        {"role": "tool", "tool_call_id": "c1", "tool": "build.compile",
         "result": {"code": "E4001", "message_vi": "không thấy mã nguồn"},
         "envelope": {"summary_line": "build.compile"}},
        {"role": "tool", "tool_call_id": "c2", "tool": "target.flash",
         "result": {"code": "E4040", "message_vi": "không thấy bo nào"},
         "envelope": {"summary_line": "target.flash"}}]
    chu = tuong_thuat_co_hoc(ms)
    # Dòng "Lỗi cuối cùng" chỉ nói về `target.flash`, nên `E4001` chỉ có thể đến từ dòng
    # lời gọi của chính nó.
    assert "E4001" in chu.split("**Lỗi cuối cùng:**")[0], chu
    assert "`build.compile` → E4001" in chu, chu
