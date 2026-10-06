# -*- coding: utf-8 -*-
"""M1-02 — lược đồ công cụ hiển thị phải nằm trong ngân sách, và phải ĐO ĐƯỢC.

Hai nửa, và chúng phải tách rời nhau:

* **Phần đo** (`token_luoc_do`, khoá `tool_schema_tokens` trong sổ cái) chạy LUÔN, kể cả
  khi cờ tắt. Không có thước thì không ai biết lược đồ đang tốn bao nhiêu, và cổng 4.3 của
  kế hoạch tối ưu không bao giờ qua được.
* **Phần gọn** (tập `CORE_GON`, cắt mô tả tham số, LRU cho công cụ mở tạm) nằm sau cờ
  `EIDE_FEATURE_GON_CONG_CU`, mặc định TẮT — nó đổi danh sách công cụ mô hình nhìn thấy,
  tức là đổi hành vi tác tử (N-4), và hành vi chỉ đo được bằng bộ eval.

Ca âm `test_tat_co_thi_danh_sach_y_nhu_cu` là ca quan trọng nhất ở đây: nó chụp ảnh 73 tên
công cụ của ngày hôm nay và khẳng định cờ TẮT không đổi một tên nào.
"""

import json

import pytest

from eide.config import Features
from eide.context.assemble import approx_tokens
from eide.llm.gateway import Response, ToolCall
from eide.tools import build_registry
from eide.tools.registry import CORE_GON

# Ảnh chụp 06/10/2026 — tập `core=True` của bản trước M1-02. Cờ TẮT phải trả đúng tập này.
# Để NGUYÊN VĂN trong test chứ không lấy từ mã: một mốc tính từ chính thứ nó canh thì
# không canh được gì (bài học DEV-288).
CORE_73 = [
    "ask_user", "asset.image_to_c", "board.check", "branch.create", "branch.list",
    "build.compile", "ckm.build", "ckm.chip_add", "ckm.from_pinout", "ckm.graph",
    "ckm.import_netlist", "ckm.module_set", "ckm.net_set", "ckm.pinout_set", "ckm.port_set",
    "code.analyze", "code.vendor_fetch", "code.vendor_list", "config.load", "diagram.render",
    "doc.fetch", "doc.load", "doc.render", "doc.search_web", "eda.bom_check",
    "eda.netlist", "fact.assert_human", "fact.compare", "fact.cross_check", "fact.extract",
    "fact.extract_pinout", "fact.query", "fact.review", "fs.edit", "fs.glob",
    "fs.grep", "fs.read", "fs.stat", "fs.write", "history.diff",
    "history.list", "history.undo", "ingest.file", "inventory.get", "ledger.query",
    "memory.note", "memory.read", "passport.isa", "passport.pin", "plan.enter",
    "plan.exit", "project.export", "sim.criteria", "sim.run", "snapshot.compare",
    "snapshot.create", "snapshot.list", "snapshot.propose", "snapshot.release",
    "snapshot.restore", "store.adr_create", "store.bom_set", "store.get", "store.list",
    "store.option_choose", "store.option_create", "store.procedure_set", "store.req_create",
    "target.flash", "tool.propose", "tool.search", "ui.explain", "ui.notice",
]


@pytest.fixture
def co_bat(monkeypatch):
    """Bật cờ gọn bằng BIẾN MÔI TRƯỜNG, đúng đường người dùng sẽ bật."""
    monkeypatch.setenv("EIDE_FEATURE_GON_CONG_CU", "1")
    return Features.load()


# =========================================================================== phần đo
def test_co_ham_do_token_luoc_do():
    """TC-M1-02-01 — có thước đo, và nó đo đúng thứ gửi lên mô hình."""
    r = build_registry()
    n = r.token_luoc_do()
    assert isinstance(n, int) and n > 0
    assert n == approx_tokens(json.dumps(r.declarations(), ensure_ascii=False))


def test_ledger_ghi_token_luoc_do(make_agent):
    """TC-M1-02-04 — mỗi lời gọi mô hình ghi lại lược đồ đã tốn bao nhiêu token."""
    from eide.protocol.humanact import HumanAct

    agent = make_agent([Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "main.c"})]),
                        Response(text="xong")])
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "đọc main.c",
                                   "origin": {"surface": "console"}}), lambda c: None)

    goi = [e for e in agent.ledger.read() if e.kind == "llm_call"]
    assert goi, "không có bản ghi llm_call nào"
    for e in goi:
        assert "tool_schema_tokens" in e.data, sorted(e.data)
        assert e.data["tool_schema_tokens"] > 0


# =========================================================================== cờ TẮT
def test_tat_co_thi_danh_sach_y_nhu_cu(monkeypatch):
    """TC-M1-02-03 — ca âm: cờ TẮT thì tập công cụ hiển thị không đổi một tên nào."""
    monkeypatch.delenv("EIDE_FEATURE_GON_CONG_CU", raising=False)
    r = build_registry(Features())
    assert sorted(t.name for t in r.visible()) == CORE_73
    # Và mô tả tham số KHÔNG bị cắt: lược đồ vẫn là lược đồ đầy đủ.
    assert r.token_luoc_do() > 20_000, "cờ tắt mà lược đồ co lại ⇒ đã đổi hành vi khi tắt"


# =========================================================================== cờ BẬT
def test_bat_co_thi_luoc_do_duoi_6000(co_bat):
    """TC-M1-02-02 — bật cờ: ≤ 6k token, và 18 công cụ nền vẫn còn đủ."""
    r = build_registry(co_bat)
    ten = {t.name for t in r.visible()}
    thieu = [x for x in CORE_GON if x not in ten]
    assert not thieu, f"tập nền thiếu: {thieu}"
    n = r.token_luoc_do()
    assert n <= 6000, f"lược đồ còn {n} token, trần là 6000"


def test_bat_co_thi_cat_mo_ta_tham_so(co_bat):
    """Mô tả tham số cắt còn ≤ 160 ký tự, nhưng `spec.params` gốc giữ nguyên.

    Đo trên `fact.compare` — tham số `luat` của nó có mô tả **475 ký tự**, dài nhất trong
    cả bộ công cụ. Đây là ca duy nhất đo được phép cắt một cách không mơ hồ.

    Bản đầy đủ vẫn phải còn: `tool.search` và các lỗi tham số đọc `spec.params` để nói cho
    mô hình biết trường ấy cần gì. Cắt luôn bản gốc là đổi hợp đồng công cụ, không phải
    tiết kiệm token.
    """
    r = build_registry(co_bat)
    spec = r.get("fact.compare")
    goc = dict(_mo_ta(spec.params))
    assert len(goc[".properties.luat"]) > 160, "ảnh chụp lệch: mô tả gốc không còn dài"

    cat = dict(_mo_ta(spec.declaration(gon=True).get("parameters") or {}))
    assert len(cat[".properties.luat"]) <= 160, len(cat[".properties.luat"])
    # Gốc KHÔNG bị sửa theo: declaration() phải làm việc trên bản sao.
    assert dict(_mo_ta(spec.params)) == goc

    # Và mọi mô tả trong lược đồ ĐANG gửi đi đều trong hạn.
    dai = [(d["name"], k, len(v))
           for d in r.declarations()
           for k, v in _mo_ta(d.get("parameters") or {})
           if len(v) > 160]
    assert not dai, dai[:5]


def test_bat_co_thi_declarations_sap_theo_ten(co_bat):
    """Prefix ổn định thì cache của Gemini mới dùng lại được giữa các lượt."""
    r = build_registry(co_bat)
    ten = [d["name"] for d in r.declarations()]
    assert ten == sorted(ten), ten[:10]


def test_lru_go_cong_cu_khong_dung(co_bat, cfg, monkeypatch):
    """TC-M1-02-05 — mở khoá một công cụ rồi bỏ đó 3 lượt thì nó rời lược đồ.

    Vì sao cần: `_unlocked` chỉ được `add`, không bao giờ gỡ. Một phiên dài mở khoá dần
    mấy chục công cụ và lược đồ phình lên theo thời gian — đúng lúc cửa sổ ngữ cảnh đã
    chật nhất.
    """
    from eide.llm import ScriptedGateway
    from eide.loop import Agent
    from eide.protocol.humanact import HumanAct

    cfg.features = co_bat
    agent = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
    agent.registry.search("ledger.verify")
    assert "ledger.verify" in {t.name for t in agent.registry.visible()}

    def mot_luot(i):
        agent.llm.script = [Response(text=f"xong {i}")]
        agent.llm._i = 0
        agent.turn(HumanAct.from_dict({"kind": "say", "text": f"việc {i}",
                                       "origin": {"surface": "console"}}), lambda c: None)

    for i in range(3):
        mot_luot(i)
    ten = agent.llm.calls[-1]["tools"]
    assert "ledger.verify" not in ten, "3 lượt không ai gọi mà nó vẫn còn trong lược đồ"
    assert "fs.read" in ten, "gỡ quá tay: công cụ nền phải còn"


def test_lru_khong_go_cong_cu_ke_hoach_dang_neu(co_bat, cfg):
    """Kế hoạch còn nêu công cụ nào thì công cụ ấy không bị gỡ, dù chưa gọi lần nào."""
    from eide.ke_hoach import MA_KE_HOACH, Buoc, KeHoach
    from eide.llm import ScriptedGateway
    from eide.loop import Agent
    from eide.protocol.humanact import HumanAct

    cfg.features = co_bat
    agent = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
    kh = KeHoach(buoc=[Buoc(viec="đo lại", cong_cu="ledger.verify", hien_vat="báo cáo")],
                 trang_thai="da_duyet")
    agent.store.apply(artefact_id=MA_KE_HOACH, type="plan", op="create", author="test",
                      canonical=kh.to_dict(),
                      explain={"summary": "kế hoạch thử", "why": "ca kiểm", "sources": [],
                               "diff_prev": "—", "next": "—", "confidence": "BAC"},
                      view_hint={"kind": "plan", "path": "kế hoạch"})
    agent.registry.search("ledger.verify")

    for i in range(4):
        agent.llm.script = [Response(text=f"xong {i}")]
        agent.llm._i = 0
        agent.turn(HumanAct.from_dict({"kind": "say", "text": f"việc {i}",
                                       "origin": {"surface": "console"}}), lambda c: None)

    ten = agent.llm.calls[-1]["tools"]
    assert "ledger.verify" in ten, "kế hoạch đang nêu nó mà nó bị gỡ"


def _mo_ta(schema, duong=""):
    """Mọi `description` trong một JSON Schema, kèm đường dẫn tới nó."""
    ra = []
    if isinstance(schema, dict):
        if isinstance(schema.get("description"), str):
            ra.append((duong or ".", schema["description"]))
        for k, v in schema.items():
            if k != "description":
                ra.extend(_mo_ta(v, f"{duong}.{k}"))
    elif isinstance(schema, list):
        for i, v in enumerate(schema):
            ra.extend(_mo_ta(v, f"{duong}[{i}]"))
    return ra
