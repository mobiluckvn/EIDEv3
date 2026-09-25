# -*- coding: utf-8 -*-
"""Lớp cấp quyền, sổ đăng ký công cụ, kiểm kê — phần XÁC ĐỊNH của lõi.

§F3: "Tất định: hook/tool/changeset/undo 100 %". Những gì kiểm ở đây phải đúng mọi lần,
không phụ thuộc mô hình.
"""

import pytest

from eide.policy import PolicyEngine
from eide.store import Store, inventory
from eide.tools import build_registry


@pytest.fixture(scope="module")
def reg():
    return build_registry()


@pytest.fixture
def pol():
    return PolicyEngine()


# =========================================================================== cấp quyền
@pytest.mark.parametrize("tool,args,pre,action,gate", [
    ("fs.read", {"path": "a.c"}, {}, "allow", None),
    ("fact.query", {}, {}, "allow", None),
    ("ask_user", {}, {}, "allow", None),
    ("store.req_create", {"text": "x"}, {}, "deny", None),                      # N7
    ("fs.write", {"path": "m.c"}, {"explain.complete": False}, "deny", None),   # N8
    ("fs.write", {"path": "m.c"}, {"explain.complete": True,
                                   "constant_guard.unsourced": 3}, "deny", None),  # N1
    ("fact.compare", {}, {"tier.ok": False}, "deny", None),                     # N2
    ("target.flash", {}, {}, "ask", "G-FLASH"),
    ("target.dangerous", {}, {"snapshot.has_release": True}, "ask", "G-OPS"),
    ("sim.criteria", {"exists": True, "changed": True},
     {"explain.complete": True}, "ask", "G-QUAL"),
    ("history.undo", {"scope": "run"}, {}, "ask", "G-HIST"),
    ("snapshot.restore", {}, {}, "ask", "G-HIST"),
    # Tên không có trong lời người → CHẶN. Khoá trên một sự thật đo được, không trên
    # trường `by` do chính tác tử khai (xem DEV-246).
    ("snapshot.create", {"ten": "sau-khi-sua-driver"},
     {"snapshot.ten_tu_nguoi": False}, "deny", None),
    ("snapshot.create", {"ten": "v0.2-them-nhiet"},
     {"snapshot.ten_tu_nguoi": True}, "allow", None),
    ("doc.approve_request", {"domain": "vn.com"}, {}, "ask", "G-DATA"),
    ("tool.install", {"pkg": "gcc"}, {}, "ask", "G-TOOL"),
])
def test_quyet_dinh(pol, reg, tool, args, pre, action, gate):
    d = pol.decide({"tool": tool, "args": args}, pre, reg.get(tool))
    assert d.action == action, f"{tool} → {d.action} ({d.rule_id})"
    if gate:
        assert d.gate == gate


def test_CX15_khong_release_thi_khong_khoa_chip(pol):
    """CX15: RDP khi chưa có snapshot release → bị chặn với lý do, đề nghị tạo release."""
    d = pol.decide({"tool": "target.dangerous", "args": {}}, {"snapshot.has_release": False})
    assert d.action == "deny"
    assert "release" in d.reason_vi.lower()


def test_G_OPS_khong_bao_gio_tu_dong(pol):
    """never_auto: không mức tự chủ nào, không phím 'Tin' nào bỏ qua được."""
    pol.autonomy = "A4"
    pol.trusted.add("target.dangerous")
    d = pol.decide({"tool": "target.dangerous", "args": {}}, {"snapshot.has_release": True})
    assert d.action == "ask" and d.never_auto is True


def test_tin_nguon_thi_G_DATA_tu_qua(pol):
    call = {"tool": "doc.approve_request", "args": {"domain": "st.com"}}
    assert pol.decide(call, {}).action == "ask"
    pol.trusted.add("st.com")
    assert pol.decide(call, {}).action == "allow"


def test_muc_tu_chu_thap_thi_ghi_phai_hoi(pol, reg):
    call = {"tool": "fs.write", "args": {"path": "m.c"}}
    pre = {"explain.complete": True, "constant_guard.unsourced": 0}
    assert pol.decide(call, pre, reg.get("fs.write")).action == "allow"
    pol.autonomy = "A1"
    assert pol.decide(call, pre, reg.get("fs.write")).action == "ask"


def test_dieu_kien_sai_cu_phap_thi_no_chu_khong_cho_qua(pol):
    """Một điều kiện không tính được KHÔNG được âm thầm thành 'allow'."""
    pol.rules.insert(0, {"id": "XX", "tool": "fs.read", "when": "này ( sai cú pháp",
                         "action": "deny", "reason_vi": "x"})
    with pytest.raises(ValueError):
        pol.decide({"tool": "fs.read", "args": {}}, {})


# =========================================================================== công cụ
def test_moi_cong_cu_co_hop_dong_du(reg):
    for t in reg.all():
        assert t.summary_vi and len(t.summary_vi) > 20, f"{t.name} mô tả quá sơ sài"
        assert t.params.get("type") == "OBJECT" or t.params.get("type") == "object"
        assert t.risk in ("R0", "R1", "R2", "R3", "R4")
        if t.writes_artefact:
            assert t.needs_explain, f"{t.name} ghi hiện vật mà không đòi explain — trái N8"


def test_thieu_tham_so_bat_buoc(reg):
    r = reg.run("fs.read", {}, ctx=None)
    assert not r.ok and r.error.code == "E5001"
    assert "path" in r.error.message_vi


def test_tham_so_la_bi_tu_choi(reg, cfg):
    ctx = _ctx(cfg)
    r = reg.run("fs.read", {"path": "main.c", "khong_co_tham_so_nay": 1}, ctx)
    assert not r.ok and "không có tham số" in r.error.message_vi


def test_cong_cu_khong_ton_tai_thi_goi_y(reg):
    r = reg.run("fs.doc_khong_co", {}, ctx=None)
    assert not r.ok and r.error.code == "E5004"
    assert "tool.search" in r.error.hint_for_agent


def test_sandbox_chan_duong_dan_ra_ngoai(reg, cfg):
    ctx = _ctx(cfg)
    for path in ("../../../etc/passwd", "~/.ssh/id_rsa", "/etc/hosts"):
        r = reg.run("fs.read", {"path": path}, ctx)
        assert not r.ok and r.error.code == "E4002", path


def test_duong_dan_khong_ton_tai_day_sang_hoi_khong_phai_doan(reg, cfg):
    r = reg.run("fs.read", {"path": "tep-bia-ra-tu-cau-noi.c"}, _ctx(cfg))
    assert not r.ok and r.error.code == "E1003"
    assert "fs.glob" in r.error.hint_for_agent
    assert "không" in r.error.hint_for_agent.lower()


def test_fs_glob_tat_dinh(reg, cfg):
    ctx = _ctx(cfg)
    kq = {tuple(f["path"] for f in reg.run("fs.glob", {"pattern": "**/*"}, ctx).data["files"])
          for _ in range(5)}
    assert len(kq) == 1


def test_fact_query_rong_noi_thang(reg, cfg):
    r = reg.run("fact.query", {"subject": "chip:ATmega328P"}, _ctx(cfg))
    assert r.ok and r.data["count"] == 0
    assert "CHƯA CÓ" in r.data["note_vi"] or "Không có Fact" in r.data["note_vi"]
    assert "NGƯỜI" in r.data["note_vi"], "phải chỉ ra đường đi tiếp, không chỉ báo rỗng"


def test_tool_search_mo_khoa(reg):
    assert reg.get("ledger.verify").core is False
    assert "ledger.verify" not in [t.name for t in reg.visible()]
    reg.search("kiểm toàn vẹn sổ cái")
    assert "ledger.verify" in [t.name for t in reg.visible()]


# =========================================================================== kiểm kê
def test_kho_rong_thi_noi_thang_la_rong(tmp_path):
    """N3 / TC008: mô hình bịa REQ_HW_I2C vì không ai nói cho nó biết kho rỗng."""
    inv = inventory.build(Store(tmp_path / "s.db"), project_name="x")
    txt = inv.render()
    assert "DỰ ÁN TRỐNG" in txt
    assert "CHƯA GHIM" in txt
    assert "không được kể ra bất kỳ REQ" in txt


def test_kiem_ke_tat_dinh_va_nhanh(tmp_path):
    s = Store(tmp_path / "s.db")
    for i in range(50):
        s.apply(artefact_id=f"REQ-{i:03d}", type="req", op="create", author="agent:run-1",
                canonical={"t": i}, explain={"summary": "x", "why": "y", "sources": [],
                                             "diff_prev": "bản đầu", "next": "z",
                                             "confidence": "NGUOI"})
    outs = {inventory.build(s, project_name="x").render() for _ in range(10)}
    assert len(outs) == 1, "§F3: cùng store → cùng kiểm kê 100 %"
    assert inventory.build(s, project_name="x").elapsed_ms < 50, "§F3: inventory < 50 ms"


def test_kiem_ke_trong_ngan_sach_800_token(tmp_path):
    from eide.context import approx_tokens
    s = Store(tmp_path / "s.db")
    for i in range(30):
        s.apply(artefact_id=f"A-{i}", type="req", op="create", author="a",
                canonical={}, explain={"summary": "x"})
    s.mark_stale([f"A-{i}" for i in range(20)], "cs-0001")
    assert approx_tokens(inventory.build(s, project_name="x").render()) <= 800


def test_dung_lai_hinh_chieu_tu_events(tmp_path):
    """CX16: phát lại sổ cái + changeset phải tái tạo trạng thái store 100 %."""
    s = Store(tmp_path / "s.db")
    ex = {"summary": "x", "why": "y", "sources": [], "diff_prev": "bản đầu",
          "next": "z", "confidence": "NGUOI"}
    s.apply(artefact_id="REQ-01", type="req", op="create", author="a", canonical={"v": 1}, explain=ex)
    s.apply(artefact_id="REQ-01", type="req", op="update", author="human", canonical={"v": 2}, explain=ex)
    truoc = s.get("REQ-01")
    s.rebuild()
    sau = s.get("REQ-01")
    assert truoc["version"] == sau["version"] == 2
    assert sau["canonical"] == {"v": 2} and sau["author"] == "human"


def _ctx(cfg):
    """Ngữ cảnh tối thiểu cho công cụ đọc: sandbox + kho."""
    class C:
        config = cfg
        store = Store(cfg.paths.store_db)
    return C()
