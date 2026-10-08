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


# ================================================== M1-03 — subagent cũng phải qua hàng rào
def test_firmware_KHONG_ghi_duoc_hang_so_khong_nguon(make_agent):
    """TC-M1-03-01 — `POL-N1-constant-guard` phải nổ cả khi lời gọi tới từ subagent.

    Hàng rào của dự án này nằm ở `Agent._one_tool`: plan-lock → pre_tool_use →
    policy.decide → run → post_tool_use. `subagent.chay` gọi thẳng `registry.run`, nên mọi
    luật trong `policy.yaml` đều không nổ — và `firmware` có `fs.write` trong tập công cụ.

    Tức là: luật "hằng số phải có nguồn" (N1) chặn tác tử CHÍNH, nhưng tác tử chính chỉ cần
    bảo một tác tử con ghi hộ là xong. Một hàng rào đi vòng được bằng một lớp gián tiếp thì
    không phải hàng rào.
    """
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write",
                                      {"path": "blink.c",
                                       "content": "#define BAUD 115200\n", "explain": _EX})]),
        Response(text=_bc(ket_luan="chua_du_du_kien", bang_chung=[])),
    ])
    so = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="firmware",
            viec="viết blink.c", ghi_so=lambda k, d: so.append((k, d)))

    assert not (agent.config.paths.project_root / "blink.c").exists(), \
        "subagent đã ghi được một hằng số không nguồn"
    luat = [e.data.get("rule") for e in agent.ledger.read()
            if e.kind == "hook" and e.data.get("hook") == "policy"]
    assert "POL-N1-constant-guard" in luat, f"policy không nổ. Các luật đã chạy: {luat}"


def test_subagent_bi_khoa_khi_dang_soan_ke_hoach(make_agent):
    """TC-M1-03-02 — plan mode khoá công cụ ghi, kể cả qua tác tử con.

    Không có bước này thì khoá plan mode (§B5) chỉ là một gợi ý: đang soạn kế hoạch mà vẫn
    ghi được tệp, chỉ cần ghi qua `task.run`.
    """
    from eide.ke_hoach import MA_KE_HOACH, Buoc, KeHoach

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write",
                                      {"path": "khoa.c", "content": "int main(void){}\n",
                                       "explain": _EX})]),
        Response(text=_bc(ket_luan="chua_du_du_kien", bang_chung=[])),
    ])
    kh = KeHoach(muc_tieu="làm đèn nháy", trang_thai="dang_soan",
                 buoc=[Buoc(viec="viết mã", cong_cu="fs.write", hien_vat="blink.c")])
    agent.store.apply(artefact_id=MA_KE_HOACH, type="plan", op="create", author="test",
                      canonical=kh.to_dict(),
                      explain={"summary": "kế hoạch thử", "why": "ca kiểm", "sources": [],
                               "diff_prev": "—", "next": "—", "confidence": "BAC"},
                      view_hint={"kind": "plan", "path": "kế hoạch"})

    ma_loi = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="firmware",
            viec="viết khoa.c", ghi_so=lambda k, d: ma_loi.append(d.get("code")))

    assert not (agent.config.paths.project_root / "khoa.c").exists()
    assert "E6005" in ma_loi, f"mã lỗi thu được: {ma_loi}"


def test_subagent_gap_cong_thi_E4032_khong_dung_the(make_agent, monkeypatch):
    """TC-M1-03-03 — gặp cổng thì tác tử con DỪNG, không được dựng thẻ cho người duyệt.

    Thẻ cổng là một câu hỏi cho người dùng về việc họ đang theo dõi. Một tác tử con chạy
    trong ngữ cảnh sạch, người dùng không thấy nó, không biết nó đang làm gì — nên một thẻ
    do nó dựng là một câu hỏi không có chỗ đứng. Nó phải ghi vào `chua_lam` và nộp báo cáo.
    """
    monkeypatch.setattr(SA.SUBAGENT["hardware"], "cong_cu",
                        list(SA.SUBAGENT["hardware"].cong_cu) + ["target.flash"])
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "target.flash", {"explain": _EX})]),
        Response(text=_bc(ket_luan="chua_du_du_kien", bang_chung=[])),
    ])
    ma_loi = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="hardware",
            viec="nạp firmware", ghi_so=lambda k, d: ma_loi.append(d.get("code")))

    assert "E4032" in ma_loi, f"mã lỗi thu được: {ma_loi}"
    assert agent.pending_cards == [], "tác tử con đã dựng thẻ cổng"
    assert agent.pending_gates == {}


def test_firmware_ghi_hop_le_van_ghi_duoc(make_agent):
    """TC-M1-03-04 — ca âm: thêm hàng rào mà không khoá luôn đường đi đúng."""
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write",
                                      {"path": "sach.c",
                                       "content": "int main(void){return 0;}\n",
                                       "explain": _EX})]),
        Response(text=_bc()),
    ])
    ok = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="firmware",
            viec="viết sach.c", ghi_so=lambda k, d: ok.append(d.get("ok")))

    assert (agent.config.paths.project_root / "sach.c").exists(), "đường đi đúng bị khoá"
    assert ok and all(ok), ok


def test_moi_loi_goi_cua_subagent_deu_qua_hang_rao(make_agent):
    """Mỗi `subagent_tool` trong sổ phải có một dòng `hook policy` đi kèm.

    Đây là phép soát của "Tiêu chí xong", viết thành ca kiểm để nó chạy mãi: khoá
    `khong_qua_hang_rao` chỉ xuất hiện khi lời gọi KHÔNG đi qua ba lớp, và nó phải không
    bao giờ xuất hiện trên đường chạy thật.
    """
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "main.c"})]),
        Response(text=_bc()),
    ])
    dong = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="firmware",
            viec="đọc main.c", ghi_so=lambda k, d: dong.append(d))

    assert dong, "không có bản ghi subagent_tool nào"
    di_vong = [d for d in dong if d.get("khong_qua_hang_rao")]
    assert not di_vong, di_vong
    policy = [e for e in agent.ledger.read()
              if e.kind == "hook" and e.data.get("hook") == "policy"]
    assert len(policy) >= len(dong), f"{len(dong)} lời gọi mà chỉ {len(policy)} lần qua policy"


# ===================================================================== M4-07 gói bằng chứng
"""Verifier nhận gói bằng chứng do MÃ dựng, không nhận đề bài tác tử chính tự viết.

`DinhNghia.doc_duoc_viec=False` có trong mã từ G6 và **không dòng nào đọc nó**: `SA.chay`
nhận `viec` rồi gửi nguyên văn. Nên trên đường `task.run(subagent="verifier")` — đường mà
tác tử chính tự gọi — verifier vẫn đọc đúng thứ tác tử chính muốn nó đọc, kèm cả lập luận.
Đường tự động (`viec_cho_verifier`) thì đã sạch từ đầu; M4-07 chỉ vá đường tay.
"""


def _bat_co(monkeypatch, agent):
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_VERIFIER_GOI_BANG_CHUNG", "1")
    agent.config.features = Features.load()
    assert agent.config.features.bat("verifier_goi_bang_chung") is True
    return agent


def _bat_tin(hop: list):
    """Một phần tử kịch bản: ghi lại `messages` rồi nộp báo cáo hợp lệ."""
    def _f(messages):
        hop.append([dict(m) for m in messages])
        return Response(text=_bc(ket_luan="chua_du_du_kien", bang_chung=[]))
    return _f


def test_verifier_KHONG_thay_lap_luan_tac_tu_chinh(make_agent, monkeypatch):
    """TC-M4-07-01 — cờ bật: lập luận của tác tử chính không tới được verifier.

    "Chắc chắn PID đúng" là một kết luận, không phải một dữ kiện. Đưa nó vào đề bài là mời
    verifier đi tìm cách biện minh thay vì đi mở bằng chứng ra xem.
    """
    agent = _bat_co(monkeypatch, make_agent([]))
    hop: list = []
    agent.llm.script = [_bat_tin(hop)]

    r = agent.registry.run("task.run", {
        "subagent": "verifier",
        "viec": "Đã xong vì chắc chắn PID đúng, kiểm a.c",
        "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")

    assert hop, "verifier chưa được gọi"
    chu = hop[0][0]["text"]
    assert "chắc chắn" not in chu, chu
    assert "vì" not in chu.split("BẰNG CHỨNG")[0], chu
    assert "BẰNG CHỨNG" in chu, chu


def test_goi_bang_chung_co_changeset_tu_so_cai(make_agent, monkeypatch):
    """TC-M4-07-02 — gói bằng chứng dựng từ SỔ CÁI, nên nó nói tệp nào vừa đổi.

    Đây là nửa làm cho lớp kiểm chứng còn dùng được: cắt lập luận đi mà không đưa dữ kiện
    vào thì verifier chỉ còn một câu rỗng và nó sẽ kết luận `chua_du_du_kien` mọi lần.
    """
    agent = _bat_co(monkeypatch, make_agent([]))
    ctx = _ctx(agent)
    w = agent.registry.run("fs.write", {"path": "a.c", "content": "int a(void){return 1;}\n",
                                        "explain": _EX}, ctx)
    assert w.ok, getattr(w.error, "message_vi", "")

    hop: list = []
    agent.llm.script = [_bat_tin(hop)]
    r = agent.registry.run("task.run", {"subagent": "verifier", "viec": "kiểm a.c",
                                        "explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")

    chu = hop[0][0]["text"]
    assert "a.c" in chu, chu
    assert "cs-" in chu, chu


def test_loc_claim_cat_300_va_bo_lap_luan():
    """TC-M4-07-03 — trần ký tự và phép bỏ câu lập luận."""
    chu = ("Tôi đã sửa a.c. " * 40) + "Nó đạt vì tôi đã kiểm bằng tay."
    assert len(chu) > 300
    ra = SA.loc_claim(chu)
    assert len(ra) <= 300, len(ra)
    assert "vì" not in ra and "đã kiểm" not in ra, ra


def test_loc_claim_bo_dung_nam_dau_hieu():
    """Năm dấu hiệu kế hoạch nêu, mỗi dấu hiệu một câu — câu còn lại phải là câu dữ kiện."""
    for xau in ("Đạt vì mã đúng.", "Chắc chắn đạt.", "Tôi đã kiểm rồi.",
                "Đã xác nhận trên bo.", "Mã đúng nên đạt."):
        ra = SA.loc_claim("Tôi sửa tệp a.c. " + xau)
        assert "a.c" in ra, ra
        assert xau not in ra, (xau, ra)


def test_loc_claim_khong_con_cau_nao_thi_noi_RO(make_agent):
    """Một claim toàn lập luận thì lọc xong còn rỗng — phải nói ra, đừng gửi chuỗi trắng."""
    ra = SA.loc_claim("Chắc chắn đạt vì tôi đã kiểm.")
    assert ra.strip(), "lọc sạch thành chuỗi rỗng"


def test_co_tat_viec_di_nguyen_van(make_agent):
    """TC-M4-07-04 — cờ TẮT thì không đổi gì. Mặc định TẮT vì nó đổi thứ verifier đọc (N-4)."""
    agent = make_agent([])
    assert agent.config.features.bat("verifier_goi_bang_chung") is False, "cờ phải mặc định TẮT"
    hop: list = []
    agent.llm.script = [_bat_tin(hop)]
    viec = "Đã xong vì chắc chắn PID đúng, kiểm a.c"
    r = agent.registry.run("task.run", {"subagent": "verifier", "viec": viec,
                                        "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert hop[0][0]["text"] == viec


def test_subagent_khac_khong_bi_doi_viec(make_agent, monkeypatch):
    """TC-M4-07-05 — ca âm: chỉ tác tử con có `doc_duoc_viec=False` mới bị thay đề bài.

    Thay đề bài của `firmware` là cắt mất thứ nó cần để làm việc. Điều kiện lấy từ HỢP ĐỒNG
    (`doc_duoc_viec`), không lấy từ một danh sách tên — thêm một verifier thứ hai sau này thì
    nó tự được bảo vệ.
    """
    agent = _bat_co(monkeypatch, make_agent([]))
    hop: list = []
    agent.llm.script = [_bat_tin(hop)]
    viec = "Viết blink.c vì đèn phải nháy 1 Hz"
    r = agent.registry.run("task.run", {"subagent": "firmware", "viec": viec,
                                        "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert hop[0][0]["text"] == viec
    assert SA.SUBAGENT["firmware"].doc_duoc_viec is True


def test_goi_bang_chung_noi_version_va_STALE_cua_hien_vat(make_agent):
    """Gói phải nói **phiên bản** và cờ STALE, không chỉ nói tên.

    Một hiện vật tên đúng mà đã lỗi thời thì nó là bằng chứng cho một trạng thái không còn
    tồn tại. Verifier không có cách nào biết điều đó nếu gói chỉ liệt kê tên.
    """
    agent = make_agent([])
    agent.store.apply(artefact_id="build:firmware", type="build", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "tep_ra": "build/a.hex"})
    agent.store.mark_stale(["build:firmware"], "cs-9: tác tử sửa mã")

    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "build:firmware" in goi, goi
    assert "v1" in goi, goi
    assert "STALE" in goi, goi


def test_goi_bang_chung_DUNG_o_lan_verifier_gan_nhat(make_agent):
    """Gói chỉ gồm việc KỂ TỪ lần verifier gần nhất — giống `co_viec_chua_kiem`.

    Nếu nó dồn cả phiên vào thì verifier phải kiểm lại thứ đã có người kiểm, và phần việc
    mới — phần duy nhất cần kiểm — bị chìm trong đó.
    """
    agent = make_agent([])
    agent.ledger.append("changeset", {"id": "cs-1", "author": "agent:run-1", "run_id": "run-1",
                                      "snapshot_id": None, "touches": ["cu.c"],
                                      "reversible": True, "stale": [], "summary": "việc cũ"})
    agent.ledger.append("tool_use", {"run_id": "run-1", "tool": "task.run",
                                     "args": {"subagent": "verifier"}, "call_id": "c0"})
    agent.ledger.append("changeset", {"id": "cs-2", "author": "agent:run-2", "run_id": "run-2",
                                      "snapshot_id": None, "touches": ["moi.c"],
                                      "reversible": True, "stale": [], "summary": "việc mới"})

    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "moi.c" in goi and "cs-2" in goi, goi
    assert "cu.c" not in goi and "cs-1" not in goi, goi


def test_goi_bang_chung_co_tran_ky_tu(make_agent):
    """Trần là một con số, không phải một hy vọng: 200 changeset không được thành 200 KB."""
    agent = make_agent([])
    for i in range(200):
        agent.ledger.append("changeset", {
            "id": f"cs-{i}", "author": "agent:run-1", "run_id": "run-1", "snapshot_id": None,
            "touches": [f"tep-{i}-ten-that-dai-de-ton-nhieu-ky-tu.c"],
            "reversible": True, "stale": [], "summary": "x" * 200})
    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history,
                                      toi_da_ky_tu=1500)
    assert len(goi) <= 1500, len(goi)
    assert "cắt" in goi or "…" in goi, goi[-200:]


def test_goi_bang_chung_noi_ket_qua_build_test_sim_gan_nhat(make_agent):
    """Ba con số verifier cần nhất: build, test, sim — và `dat` của từng cái."""
    agent = make_agent([])
    agent.store.apply(artefact_id="build:firmware", type="build", op="create",
                      author="agent:run-1", explain=_EX, canonical={"dat": True})
    agent.store.apply(artefact_id="sim_result:unit-test", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "so_ca": 4, "so_hong": 1})

    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "build:firmware" in goi and "sim_result:unit-test" in goi, goi
    assert "dat=True" in goi and "dat=False" in goi, goi


def test_so_cai_ghi_lai_che_do_dau_vao_cua_subagent(make_agent, monkeypatch):
    """Đổi đầu vào của một lớp kiểm chứng mà không ghi lại thì sau không ai soát được.

    `subagent_input` là chỗ trả lời câu "lượt ấy verifier đọc cái gì" — mà không có nó thì
    hai chế độ đầu vào trông giống hệt nhau trong sổ.
    """
    agent = _bat_co(monkeypatch, make_agent([]))
    hop: list = []
    agent.llm.script = [_bat_tin(hop)]
    agent.registry.run("task.run", {"subagent": "verifier", "viec": "kiểm a.c",
                                    "explain": _EX}, _ctx(agent))
    ds = [e for e in agent.ledger.read() if e.kind == "subagent_input"]
    assert ds, "không có bản ghi subagent_input nào"
    assert ds[-1].data["che_do"] == "goi_bang_chung"
    assert ds[-1].data["so_ky_tu"] == len(hop[0][0]["text"])


def test_duong_TU_DONG_khong_bi_doi(make_agent, monkeypatch):
    """Giới hạn phạm vi: đường SubagentStop vẫn dùng `viec_cho_verifier`, cờ bật hay tắt.

    Nó đã sạch từ G6 — verifier ở đó chỉ thấy báo cáo. Đổi nó theo là tự tạo thêm một đường
    để làm sai ở chỗ vốn đang đúng.
    """
    agent = _bat_co(monkeypatch, make_agent([]))
    hop: list = []
    agent.llm.script = [
        Response(text=_bc(tom_tat="biên dịch sạch")),            # firmware tuyên đạt
        _bat_tin(hop),                                           # verifier TỰ ĐỘNG
    ]
    r = agent.registry.run("task.run", {"subagent": "firmware", "viec": "viết blink",
                                        "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    chu = hop[0][0]["text"]
    assert "BÁO CÁO (dữ liệu" in chu, chu
    assert "biên dịch sạch" in chu, chu
    assert "BẰNG CHỨNG (dữ liệu)" not in chu, chu


def test_MOI_co_khai_trong_dataclass_deu_co_trong_ten_co(monkeypatch):
    """`ten_co()` là danh sách gõ tay, và nó LỆCH — M4-07 trúng đúng chỗ ấy.

    Cờ `verifier_goi_bang_chung` khai đúng trường trong `Features`, mà `Features.load()` trả
    về `False` cả khi `EIDE_FEATURE_VERIFIER_GOI_BANG_CHUNG=1`: `load()` chỉ vòng qua
    `ten_co()`. Hệ quả kéo theo `to_dict()` (tab cờ), và `tools/kiem_tai_lieu.py` (nó bật
    MỌI cờ theo đúng danh sách ấy để đếm công cụ).

    Ca kiểm cũ `test_co_moi_co_trong_ten_co_va_to_dict` nêu đúng bất biến này nhưng kiểm nó
    trên MỘT tên gõ sẵn, nên nó xanh suốt trong khi cờ thứ chín vô hình. Đây là phép so hai
    danh sách — thêm cờ mới mà quên khai thì nó đỏ ngay.
    """
    from dataclasses import fields

    from eide.config import Features

    khai = {f.name for f in fields(Features)}
    assert khai == set(Features.ten_co()), khai ^ set(Features.ten_co())

    # Và phép đo thật: biến môi trường của cờ mới nhất phải nạp được.
    for ten in Features.ten_co():
        monkeypatch.setenv(f"EIDE_FEATURE_{ten.upper()}", "1")
    assert Features.load().dang_bat() == list(Features.ten_co())


def test_loc_claim_bo_PHAN_QUYET_trich_san():
    """Dấu hiệu thứ sáu, thêm vì một PHÉP ĐO chứ không vì kế hoạch nói.

    Năm dấu hiệu kế hoạch nêu chỉ bỏ được 11 trong 1 706 câu của 323 đề bài verifier thật.
    Chỗ rò thật không phải chữ "vì" — tác tử chính **trích sẵn phán quyết**: `kết quả
    'dat: false'`, `(dat=true, chip GW…)`. Thêm dấu hiệu ấy thì 95/1 706 câu bị bỏ.

    Bỏ câu ấy đi là đúng việc: giá trị `dat` thật nằm trong khối C của gói bằng chứng, đọc
    thẳng từ kho — còn con số tác tử chính nhắc lại thì không ai kiểm.
    """
    for xau in ("Hiện vật build:firmware có kết quả 'dat: false'.",
                "Đối chiếu với hdl.bitstream (dat=true, chip GW2A).",
                "Trường pass_fail của bản ghi là PASS.",
                "Bản ghi nói chay_duoc=true.",
                "Bộ kiểm không đạt ở ca thứ ba.",
                "Bước này đã đạt từ lượt trước."):
        ra = SA.loc_claim("Mở store.get('build:firmware'). " + xau)
        assert "store.get" in ra, ra
        assert xau not in ra, (xau, ra)

    # Và một quan sát thì KHÔNG bị bỏ: "chạy thành công, mã thoát 0" là dữ kiện, không phải
    # kết luận. Bỏ nó đi là lấy mất dữ kiện của verifier.
    quan_sat = "Lệnh chạy thành công, mã thoát 0."
    assert quan_sat in SA.loc_claim("Mở log ra. " + quan_sat)


def test_goi_bang_chung_noi_PHIEN_BAN_TAI_LUC_DOI_khi_co_so_changeset(make_agent):
    """`history` không phải tham số trang trí: nó cho **phiên bản tại lúc đổi**.

    Số ấy đứng cạnh phiên bản hiện tại trong kho sẽ nói ngay có ai đổi thêm sau changeset
    hay không — mà sổ cái một mình chỉ ghi tên tệp, không ghi version của từng lần chạm.

    Đo trên dự án thật `du-lieu/rtos-sinhvien`: có sổ changeset thì gói dài 2 142 → 2 322 ký
    tự, và mỗi dòng mang thêm `(update→v24)`.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    w = agent.registry.run("fs.write", {"path": "b.c", "content": "int b(void){return 2;}\n",
                                        "explain": _EX}, ctx)
    assert w.ok, getattr(w.error, "message_vi", "")

    khong = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, None)
    co = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "b.c" in khong and "→v" not in khong, khong
    assert "b.c (create→v1)" in co, co


def test_goi_bang_chung_co_KHOI_B_doc_lai_hien_vat_bi_cham(make_agent):
    """Khối B đọc lại hiện vật bị chạm **từ kho**, không nhắc lại lời sổ cái.

    Khối A nói *"changeset cs-3 chạm a.c"* — đó là chuyện đã xảy ra. Khối B nói *"a.c trong
    kho hiện là v1 và nó đang STALE"* — đó là chuyện ĐANG đúng. Hai câu khác nhau, và câu
    thứ hai mới trả lời được "bằng chứng này còn giá trị không".

    Phép phá "bỏ khối B" LỌT ở lượt đầu: ca kiểm cũ của khối A thấy `a.c` qua dòng
    changeset, nên nó xanh cả khi khối B biến mất. Đúng hình dạng DEV-344 — một ca xanh vì
    MỘT DÒNG KHÁC.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    w = agent.registry.run("fs.write", {"path": "c.c", "content": "int c(void){return 3;}\n",
                                        "explain": _EX}, ctx)
    assert w.ok, getattr(w.error, "message_vi", "")
    agent.store.mark_stale(["c.c"], "cs-99: anh sửa mã")

    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "B. Hiện vật bị chạm" in goi, goi
    khoi_b = goi.split("B. Hiện vật bị chạm")[1].split("\n\nC.")[0]
    assert "c.c" in khoi_b and "v1" in khoi_b, khoi_b
    assert "STALE: cs-99" in khoi_b, khoi_b
    # Và nó KHÔNG phải khối C: `c.c` là mã, không phải kết quả đo.
    assert "c.c" not in goi.split("C. ")[-1], goi


def test_goi_bang_chung_NOI_RA_khi_khong_co_changeset_nao(make_agent):
    """Không có changeset thì phải NÓI RA, đừng im.

    Im lặng và "không có gì để kiểm" trông giống nhau với người đọc, mà hai điều ấy khác
    nhau hẳn: cái sau là một kết luận, cái trước là một đường dẫn có thể đã đứt. Verifier
    đọc một gói thiếu khối A sẽ không biết nên tin khối nào.
    """
    agent = make_agent([])
    goi = SA.goi_bang_chung_tu_so_cai(agent.ledger, agent.store, agent.history)
    assert "A. Không có changeset nào" in goi, goi
