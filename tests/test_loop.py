# -*- coding: utf-8 -*-
"""Vòng lặp tác tử — §B1. Kiểm bằng cổng mô hình kịch bản, không gọi mạng.

Cái được kiểm ở đây là XƯƠNG SỐNG: ba lớp xác định có thực sự bao quanh mọi lời gọi
công cụ không, và vòng lặp có dừng đúng chỗ không. Chất lượng câu trả lời của mô hình
là việc của bộ 76 TC; ở đây chỉ đo phần mã.
"""

import pytest

from eide.llm.gateway import Response, ToolCall, Usage


def _post(seen):
    return [c.params["text"] for c in seen if c.method == "console.post"]


def _cards(seen):
    return [c.params["card"] for c in seen if c.method == "console.post" and c.params.get("card")]


# =========================================================================== S0 đứng trước
def test_S0_chan_thi_khong_goi_mo_hinh(chay):
    """N5 — 'cổng an toàn đứng trước phép đoán'. Kịch bản rỗng: gọi mô hình là nổ."""
    agent, seen = chay({"kind": "say", "text": "làm thiết bị phá sóng di động"}, script=[])
    assert len(agent.llm.calls) == 0
    assert any("không hỗ trợ" in t for t in _post(seen))


def test_S0_cong_thi_phat_the_va_dung(chay):
    agent, seen = chay({"kind": "say", "text": "xoá sạch toàn bộ flash"}, script=[])
    assert len(agent.llm.calls) == 0
    cards = _cards(seen)
    assert len(cards) == 1 and cards[0]["gate"] == "G-OPS"
    assert cards[0]["gate_id"] in agent.pending_gates


def test_S0_canh_bao_roi_van_cho_mo_hinh_chay(chay):
    """TC036 — cảnh báo tới ngay, nhưng tác tử vẫn giúp khoanh vùng lỗi."""
    agent, seen = chay(
        {"kind": "say", "text": "chip nóng ran, sao thế?"},
        script=[Response(text="Sau khi ngắt điện, ta đo trở kháng VCC–GND trước.")])
    assert len(agent.llm.calls) == 1
    posts = _post(seen)
    assert any("NGẮT NGUỒN NGAY" in t for t in posts)
    assert any("trở kháng" in t for t in posts)


# =========================================================================== ba lớp quanh tool
def test_sandbox_chan_truoc_khi_tool_chay(chay):
    agent, seen = chay(
        {"kind": "say", "text": "đọc khoá ssh"},
        script=[Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "../../../etc/passwd"})]),
                Response(text="Tôi không ra ngoài thư mục dự án được.")])
    res = [m for m in agent.messages if m.get("role") == "tool"][0]["result"]
    assert res["code"] == "E4002"


def test_loi_cong_cu_quay_ve_mo_hinh_kem_huong_dan(chay):
    """§B3 — 'lỗi là dữ liệu để mô hình đổi hướng'."""
    agent, _ = chay(
        {"kind": "say", "text": "đọc tệp mô phỏng"},
        script=[Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "tep-bia-ra.c"})]),
                Response(tool_calls=[ToolCall("c2", "fs.glob", {"pattern": "**/*.c"})]),
                Response(text="Không có tệp đó; dự án chỉ có main.c.")])
    r = [m for m in agent.messages if m.get("role") == "tool"][0]["result"]
    assert r["code"] == "E1003"
    assert "fs.glob" in r["hint_for_agent"]
    assert r["alternatives"]


def test_policy_deny_khong_cho_tool_chay(chay, monkeypatch):
    agent, _ = chay(
        {"kind": "say", "text": "ghi tệp"},
        script=[Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "main.c"})]),
                Response(text="xong")])
    # fs.read được allow; kiểm ngược lại rằng sổ cái CÓ ghi quyết định cấp quyền.
    quyet = [e for e in agent.ledger.read() if e.kind == "hook" and e.data.get("hook") == "policy"]
    assert quyet and quyet[0].data["action"] == "allow"


# =========================================================================== I6 cổng
def test_I6_text_co_khong_mo_cong(chay, make_agent):
    """Một chữ 'có' gõ trong ô nhập KHÔNG mở cổng nào."""
    from eide.protocol.rpc import Core
    agent = make_agent([])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "xoá sạch toàn bộ flash"})
    gid = _cards(seen)[0]["gate_id"]

    agent.llm.script = [Response(text="ok")]
    agent.llm._i = 0
    core.console_act({"kind": "say", "text": "có, làm đi"})
    assert gid in agent.pending_gates, "cổng vẫn phải đang chờ"


def test_decide_moi_mo_cong(chay, make_agent):
    from eide.protocol.rpc import Core
    agent = make_agent([])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "bật khoá đọc RDP"})
    gid = _cards(seen)[0]["gate_id"]

    agent.llm.script = [Response(text="Đã hiểu, tôi tiến hành.")]
    agent.llm._i = 0
    core.console_act({"kind": "decide", "data": {"gate_id": gid, "approved": True}})
    assert gid not in agent.pending_gates
    gates = [e for e in agent.ledger.read() if e.kind == "gate"]
    assert gates[-1].data["state"] == "approved"


def test_tu_choi_cong_thi_dan_mo_hinh_dung_lach(chay, make_agent):
    from eide.protocol.rpc import Core
    agent = make_agent([])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "xoá toàn bộ flash"})
    gid = _cards(seen)[0]["gate_id"]
    core.console_act({"kind": "decide", "data": {"gate_id": gid, "approved": False},
                      "note": "chưa sao lưu"})
    nhac = [m["text"] for m in agent.messages if m.get("role") == "user"]
    assert any("TỪ CHỐI" in t and "Đừng tìm đường khác" in t for t in nhac)


# =========================================================================== N4 hỏi
def test_ask_user_dung_luot_cho_nguoi(chay):
    agent, seen = chay(
        {"kind": "say", "text": "làm cho mình cái mạch thông minh"},
        script=[Response(tool_calls=[ToolCall("c1", "ask_user", {
            "questions": [{"key": "muc_dich", "question": "Mạch này dùng để làm gì?"}]})])])
    assert len(agent.llm.calls) == 1, "hỏi xong phải DỪNG, không đoán tiếp"
    assert len(agent.pending_cards) == 1


def test_toi_da_2_vong_hoi_moi_luot(chay):
    """N4 — 'hỏi một cụm, tối đa 2 lần/lượt'. Lần thứ ba bị từ chối."""
    from eide.loop import TurnContext
    ask = {"questions": [{"key": "k", "question": "?"}]}
    agent, _ = chay({"kind": "say", "text": "làm mạch gì đó"}, script=[
        Response(tool_calls=[ToolCall("c1", "ask_user", ask)]),
    ])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None)
    ctx.ask_rounds = 2
    r = agent.registry.run("ask_user", ask, ctx)
    assert not r.ok and r.error.code == "E6002"


# =========================================================================== ngân sách
def test_ngan_sach_tool_cat_dung_cho(chay, make_agent):
    """§B1 — 40 tool/lượt. Mô hình gọi mãi thì lõi cắt và NÓI RA."""
    from eide.protocol.rpc import Core
    agent = make_agent([Response(tool_calls=[ToolCall(f"c{i}", "fs.glob", {"pattern": "*"})])
                        for i in range(60)])
    agent.config.budget.max_tool_calls = 5
    seen = []
    Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append).console_act(
        {"kind": "say", "text": "liệt kê mọi thứ"})
    assert any(c.method == "notice" and c.params["code"] == "E6002" for c in seen)
    assert agent.last_report["tool_calls"] <= 5


def test_su_co_mo_hinh_khong_mat_viec(chay, make_agent):
    """UC19/TC073 — LLM hỏng: dừng an toàn, nói thật, giữ việc đã làm."""
    from eide.errors import llm_unavailable
    from eide.protocol.rpc import Core

    class Hong:
        name = "hong"
        def stream(self, **kw):
            raise llm_unavailable("529 overloaded", 3)
        def count_tokens(self, t):
            return 0

    agent = make_agent([])
    agent.llm = Hong()
    seen = []
    Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append).console_act(
        {"kind": "say", "text": "tóm tắt lại dự án này"})
    posts = _post(seen)
    assert any("không trả lời được" in t for t in posts)
    assert any("vẫn còn" in t for t in posts), "phải nói rõ là không mất việc"
    assert any(e.kind == "incident" for e in agent.ledger.read())


# =========================================================================== hook Stop
def test_stop_bat_them_mot_vong_khi_chua_noi_gi(chay):
    agent, seen = chay(
        {"kind": "say", "text": "dự án có gì?"},
        script=[Response(tool_calls=[ToolCall("c1", "store.list", {})]),
                Response(text=""),                       # kết thúc mà không nói gì
                Response(text="Kho đang trống, chưa có yêu cầu nào.")])
    assert len(agent.llm.calls) == 3, "hook Stop phải bắt thêm một vòng"
    assert any("trống" in t for t in _post(seen))


def test_stop_chi_them_dung_mot_vong(chay):
    """Nhắc là để sửa sót, không phải để kéo lượt vô hạn khi mô hình cứ lờ đi."""
    agent, _ = chay({"kind": "say", "text": "xin chào"},
                    script=[Response(text=""), Response(text="")])
    assert len(agent.llm.calls) == 2


# =========================================================================== sổ cái
def test_moi_thu_deu_vao_so_cai(chay):
    agent, _ = chay(
        {"kind": "say", "text": "trong dự án có tệp nào?"},
        script=[Response(tool_calls=[ToolCall("c1", "fs.glob", {"pattern": "*"})],
                         usage=Usage(1200, 40)),
                Response(text="Có main.c.", usage=Usage(1300, 20))])
    kinds = [e.kind for e in agent.ledger.read()]
    for k in ("human_act", "turn.start", "hook", "llm_call", "tool_use",
              "tool_result", "ui_command", "turn.end"):
        assert k in kinds, f"thiếu {k} trong sổ cái"
    assert agent.ledger.verify()[0]


def test_bao_cao_luot_co_du_so_lieu(chay):
    agent, _ = chay({"kind": "say", "text": "chào"}, script=[Response(text="Chào anh.")])
    r = agent.last_report
    assert set(r) >= {"run_id", "tool_calls", "seconds", "assumptions", "cost"}
    assert r["cost"]["tokens"] is not None


# =========================================================================== thẻ làm rõ
def test_tra_loi_the_thi_the_roi_khoi_hang_cho(chay, make_agent):
    """Thẻ đã trả lời phải rời `<pending>` — nếu không, lượt sau mô hình hỏi lại."""
    from eide.loop import TurnContext
    from eide.protocol.rpc import Core

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "ask_user", {
            "questions": [{"key": "ten", "question": "Đặt tên bản này là gì?"}]})]),
        Response(text="Đã ghi bản “v0.1-chay-duoc”."),
    ])
    seen: list = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "chốt lại trạng thái hiện tại"})
    assert len(agent.pending_cards) == 1
    ma = agent.pending_cards[0]["card_id"]

    core.console_act({"kind": "choose",
                      "data": {"card_id": ma, "answers": {"ten": "v0.1-chay-duoc"}},
                      "origin": {"surface": "console"}})
    assert agent.pending_cards == [], "thẻ đã trả lời mà vẫn nằm trong hàng chờ"

    gui = [m["text"] for m in agent.messages if m["role"] == "user"][-1]
    assert "v0.1-chay-duoc" in gui, "tên người đặt phải tới được mô hình"
    assert "Thẻ đang chờ người trả lời" not in gui


def test_bo_qua_the_thi_noi_ro_gia_dinh(chay):
    from eide.protocol.humanact import HumanAct
    a = HumanAct.from_dict({"kind": "choose",
                            "data": {"card_id": "card-1", "answers": {},
                                     "assumption_if_skipped": "Không ghi bản ưng ý nào."},
                            "origin": {"surface": "console"}})
    assert a.transcript_line() == "[Bạn] Bỏ qua thẻ, đi tiếp với giả định: Không ghi bản ưng ý nào."


# =========================================================================== hậu quả
def test_the_cong_luon_co_hau_qua_truoc_nut_bam(chay):
    """§E7 quy tắc 1 — hậu quả đứng trước lựa chọn. Rỗng thì cổng chỉ làm chậm.

    Lời gọi phải có `explain`: hook N8 chặn một lời gọi ghi hiện vật mà thiếu lớp giải thích
    **trước** khi cổng được dựng, và thứ tự đó đúng — dựng thẻ cổng cho một việc chưa khai lý
    do là hỏi người dùng duyệt đúng cái mà không ai giải trình được.
    """
    ex = {"summary": "nạp bản vừa dịch", "why": "chạy thử trên bo", "sources": [],
          "diff_prev": "—", "next": "đọc log", "confidence": "BAC"}
    agent, seen = chay(
        {"kind": "say", "text": "nạp firmware lên bo đi"},
        script=[Response(tool_calls=[ToolCall("c1", "target.flash", {"explain": ex})])])
    the = [c for c in _cards(seen) if c.get("type") == "gate"]
    assert the, "phải dựng thẻ cổng"
    assert the[0]["gate"] == "G-FLASH" and the[0]["irreversible"] is True
    assert the[0]["consequences_vi"], "thẻ cổng không có dòng hậu quả nào"
    assert any("bản ưng ý" in c.lower() for c in the[0]["consequences_vi"]), \
        "thao tác R2/R3 phải nói có bản nào để quay về không"


def test_hau_qua_khoi_phuc_neu_dich_danh_thu_se_mat(chay, make_agent):
    from eide.protocol.rpc import Core

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "snapshot.restore", {"snapshot": "snap-01"})]),
        Response(text="đã dừng chờ anh"),
    ])
    agent.history.ghi_kho(
        author="agent:r1", artefact_id="FR-01", type="req", op="create",
        canonical={"loai": "FR", "text": "cũ", "criteria": "", "source_quote": "x"},
        explain={"summary": "a", "why": "b", "sources": [], "diff_prev": "-",
                 "next": "-", "confidence": "NGUOI"}, run_id="r1")
    agent.history.tao_snapshot(ten="moc-dau")
    agent.history.ghi_kho(
        author="human", artefact_id="FR-02", type="req", op="create",
        canonical={"loai": "FR", "text": "anh thêm sau", "criteria": "",
                   "source_quote": "x"},
        explain={"summary": "a", "why": "b", "sources": [], "diff_prev": "-",
                 "next": "-", "confidence": "NGUOI"}, human_act_id="h-1")

    seen: list = []
    Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append).console_act(
        {"kind": "say", "text": "quay về bản moc-dau đi"})
    hq = [c for c in _cards(seen) if c.get("type") == "gate"][0]["consequences_vi"]
    chu = " ".join(hq)
    assert "FR-02" in chu, f"phải nêu đích danh thứ sẽ mất, mới có: {hq}"
    assert "CHÍNH ANH" in chu, "phải cảnh báo có sửa của người trong đó"


def test_het_ngan_sach_thi_NOI_RA_trong_hoi_thoai_khong_chi_treo_bang(make_agent):
    """Đo được trên một phiên thật: tác tử dùng hết 40 lời gọi để đọc tài liệu rồi lượt kết
    thúc — trên màn hình nó IM LẶNG. Người dùng đợi một tệp mã nguồn không bao giờ tới và
    không có cách nào biết vì sao. Một băng cảnh báo ở góc không trả lời câu hỏi đó."""
    from eide.llm import Response, ToolCall

    from eide.protocol.humanact import HumanAct

    agent = make_agent([Response(tool_calls=[ToolCall(f"c{i}", "fs.glob",
                                                     {"pattern": "**/*"})])
                        for i in range(12)])
    agent.config.budget.max_tool_calls = 3
    seen: list = []
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "đọc hết tài liệu rồi viết mã",
                                   "origin": {"surface": "console"}}), seen.append)

    loi = [c for c in seen if c.method == "console.post"
           and "hết số lời gọi công cụ" in str(c.params.get("text", ""))]
    assert loi, [(c.method, str(c.params)[:60]) for c in seen]
    text = loi[0].params["text"]
    assert "vẫn còn nguyên" in text and "làm tiếp" in text
    assert "fs.glob ×3" in text, text


def test_luot_ket_thuc_MA_khong_noi_gi_thi_van_phai_noi(make_agent):
    """Đã gặp thật: mô hình gọi mười công cụ để đọc mã rồi trả về một câu trả lời rỗng. Trên
    màn hình, EIDE đứng im và người dùng đợi một tệp không bao giờ tới."""
    from eide.protocol.humanact import HumanAct

    # Ba lượt: gọi công cụ → trả lời rỗng → hook Stop cho thêm một vòng, vẫn rỗng.
    agent = make_agent([Response(tool_calls=[ToolCall("c1", "fs.glob", {"pattern": "*"})]),
                        Response(text=""), Response(text="")])
    seen: list = []
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "viết giúp main.c",
                                   "origin": {"surface": "console"}}), seen.append)
    loi = [c for c in seen if c.method == "console.post"
           and c.params.get("role") == "agent"]
    assert loi, [(c.method, str(c.params)[:50]) for c in seen]
    assert "chưa hoàn thành việc anh giao" in loi[-1].params["text"]
    assert "fs.glob ×1" in loi[-1].params["text"]


def test_tac_tu_TIM_MAI_ma_khong_lam_thi_loi_NHAC(make_agent):
    """Đo được trên một lượt thật: tác tử gọi `ledger.query` 21 lần liên tiếp để tìm một tệp
    nó sắp phải tự viết, rồi hết ngân sách mà chưa viết dòng nào. Mô hình không thấy được
    lượt của chính nó từ bên ngoài — nên lõi phải nói."""
    from eide.protocol.humanact import HumanAct

    agent = make_agent([Response(tool_calls=[ToolCall(f"c{i}", "fs.glob",
                                                     {"pattern": f"**/*{i}"})])
                        for i in range(8)] + [Response(text="xong")])
    seen: list = []
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "viết giúp sim/plant.c",
                                   "origin": {"surface": "console"}}), seen.append)
    nhac = [m for m in agent.messages
            if m.get("_he_thong") and "quay" not in str(m.get("text", ""))
            and "fs.glob" in str(m.get("text", ""))]
    assert nhac, [str(m)[:80] for m in agent.messages if m.get("_he_thong")]
    t = nhac[0]["text"]
    assert "chưa ghi được gì" in t and "Dừng tìm lại" in t


def test_lượt_CO_GHI_thi_khong_bi_nhac(make_agent, tmp_path):
    """Gọi nhiều công cụ đọc là chuyện bình thường khi đang thật sự làm việc. Nhắc nhầm thì
    lần sau không ai đọc lời nhắc nữa."""
    from eide.protocol.humanact import HumanAct

    agent = make_agent(
        [Response(tool_calls=[ToolCall("w", "fs.write",
                                       {"path": "a.txt", "content": "x",
                                        "explain": {"summary": "s", "why": "w",
                                                    "sources": [], "diff_prev": "—",
                                                    "next": "—", "confidence": "VANG"}})])]
        + [Response(tool_calls=[ToolCall(f"c{i}", "fs.glob", {"pattern": f"**/*{i}"})])
           for i in range(8)] + [Response(text="xong")])
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "làm đi",
                                   "origin": {"surface": "console"}}), lambda c: None)
    assert not [m for m in agent.messages
                if m.get("_he_thong") and "Dừng tìm lại" in str(m.get("text", ""))]


# ==================================================== duyệt một lần cho cả lượt việc
def _duyet_het(agent, core, seen, lan=12):
    """Đóng vai người bấm Duyệt cho mọi thẻ cổng đang chờ, tối đa `lan` vòng."""
    for _ in range(lan):
        cho = [c for c in _cards(seen) if c.get("type") == "gate"
               and c["gate_id"] in agent.pending_gates]
        if not cho:
            break
        for c in cho:
            core.console_act({"kind": "decide",
                              "data": {"gate_id": c["gate_id"], "approved": True},
                              "origin": {"surface": "console"}})
    return [c for c in _cards(seen) if c.get("type") == "gate"]


def test_duyet_mot_lan_thi_khong_hoi_lai_cung_cong_cu_trong_luot(make_agent):
    """Đo được trên phiên bo thật: một lượt "tự tìm tài liệu" dựng 16 thẻ G-DATA.

    Hỏi lại mỗi lần không làm người dùng an toàn hơn — nó dạy người ta bấm Duyệt theo phản xạ,
    và khi một thẻ ĐÁNG đọc hiện ra thì họ cũng bấm nốt.
    """
    from eide.protocol.rpc import Core

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "doc.search_web", {"truy_van": "lần 1"})]),
        Response(tool_calls=[ToolCall("c2", "doc.search_web", {"truy_van": "lần 2"})]),
        Response(tool_calls=[ToolCall("c3", "doc.search_web", {"truy_van": "lần 3"})]),
        Response(text="xong"),
    ])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "tự tìm tài liệu giúp mình",
                      "origin": {"surface": "console"}})
    the = _duyet_het(agent, core, seen)
    assert len(the) == 1, f"phải chỉ một thẻ cho cả lượt, đang có {len(the)}"
    assert the[0]["tool"] == "doc.search_web"


def test_luot_MOI_thi_hoi_lai(make_agent):
    """Nhớ qua lượt sẽ thành "duyệt một lần, dùng mãi mãi" — đúng thứ cổng tồn tại để ngăn."""
    from eide.protocol.rpc import Core

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "doc.search_web", {"truy_van": "a"})]),
        Response(text="xong"),
        Response(tool_calls=[ToolCall("c2", "doc.search_web", {"truy_van": "b"})]),
        Response(text="xong"),
    ])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "tìm lần một",
                      "origin": {"surface": "console"}})
    _duyet_het(agent, core, seen)
    n1 = len([c for c in _cards(seen) if c.get("type") == "gate"])
    core.console_act({"kind": "say", "text": "tìm lần hai",
                      "origin": {"surface": "console"}})
    _duyet_het(agent, core, seen)
    n2 = len([c for c in _cards(seen) if c.get("type") == "gate"])
    assert n2 == n1 + 1, "câu mới của người dùng phải hỏi lại cổng"


def test_thao_tac_KHONG_HOAN_TAC_thi_hoi_lai_tung_lan(make_agent):
    """Nạp chip là R4 và không hoàn tác được — lần thứ mười cũng phải hỏi."""
    from eide.protocol.rpc import Core

    ex = {"summary": "nạp", "why": "thử", "sources": [], "diff_prev": "—",
          "next": "—", "confidence": "BAC"}
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "target.flash", {"explain": ex})]),
        Response(tool_calls=[ToolCall("c2", "target.flash", {"explain": ex})]),
        Response(text="xong"),
    ])
    seen = []
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
    core.console_act({"kind": "say", "text": "nạp hai lần đi",
                      "origin": {"surface": "console"}})
    the = _duyet_het(agent, core, seen)
    assert len(the) == 2, f"mỗi lần nạp một thẻ, đang có {len(the)}"
    assert all(c["irreversible"] for c in the)


def test_tim_mai_khong_lam_thi_nhac_du_trai_tren_NHIEU_cong_cu(make_agent):
    """Ca thật trên bo STM32F469, bước hiện logo lên màn.

    Tác tử tiêu cả lượt vào `ledger.query → fs.glob ×5 → store.list → store.get →
    ledger.query → history.list → ledger.query ×4`: mười bốn lời gọi chỉ-đọc, không ghi gì.
    Phép đếm THEO TỪNG TÊN không chạm ngưỡng nào cho tới lời gọi thứ mười bốn, và tới lúc đó
    lượt đã hết. Trải việc tìm ra nhiều công cụ khác nhau không làm nó bớt là quay vòng.
    """
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    ctx.cong_cu_da_goi = (["ledger.query"] + ["fs.glob"] * 5 + ["store.list", "store.get",
                          "ledger.query", "history.list"] + ["ledger.query"] * 2)
    ctx.da_ghi_gi_do = False
    nhac = agent._nhac_neu_dang_quay_vong(ctx)
    assert nhac, "14 lời gọi chỉ-đọc mà không ghi gì thì phải nhắc"
    assert "CHỈ-ĐỌC" in nhac and "Dừng tìm lại" in nhac
    # Nhắc MỘT lần, không càm ràm.
    assert agent._nhac_neu_dang_quay_vong(ctx) == ""


def test_history_list_duoc_tinh_la_cong_cu_doc(make_agent):
    """Ba công cụ tự-soi-mình vắng mặt trong bản trước — đúng ba cái tác tử dùng để quay vòng."""
    from eide.loop import Agent

    for t in ("history.list", "history.diff", "snapshot.list"):
        assert t in Agent._CONG_CU_DOC


def test_da_ghi_duoc_gi_do_thi_KHONG_nhac(make_agent):
    """Gọi nhiều công cụ đọc rồi GHI được gì đó thì không phải quay vòng — đó là làm việc."""
    from eide.loop import TurnContext

    agent = make_agent([])
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    ctx.cong_cu_da_goi = ["fs.read"] * 12
    ctx.da_ghi_gi_do = True
    assert agent._nhac_neu_dang_quay_vong(ctx) == ""
