# -*- coding: utf-8 -*-
"""Bộ ca cộng tác CX — EIDE-MDD-40 §F2. Phần thuộc bước G2.

    CX06  Người sửa REQ → hạ nguồn STALE đúng danh sách; tác tử nhắc ở lượt sau
    CX07  Tác tử không nhắc thay đổi của người → hook Stop bắt thêm một vòng
    CX09  Người sửa tệp tác tử đang khoá → merge, trình diff, không ghi đè
    CX10  Hoàn tác một changeset ở giữa chuỗi chạm cùng hiện vật → cảnh báo
    CX16  Phát lại sổ cái + changesets → tái tạo trạng thái 100 %

Các ca này đo **hành vi cộng tác**, không đo chất lượng câu trả lời của mô hình. Nên
chúng chạy với cổng mô hình kịch bản: cái được kiểm là mã xung quanh mô hình có giữ
đúng nguyên tắc N9 hay không, kể cả khi mô hình cư xử tệ (CX07 dựng đúng một mô hình
cư xử tệ — nó lờ thay đổi của người đi).
"""

from __future__ import annotations

import pathlib

import pytest

from eide import Agent, Config, Core
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall


def EX(s: str) -> dict:
    """Lớp giải thích tối thiểu hợp lệ — sáu trường (N8)."""
    return {"summary": s, "why": "theo yêu cầu trong lượt này",
            "sources": [{"kind": "human_act", "ref": "h-0001", "tier": "NGUOI"}],
            "diff_prev": "bản đầu tiên", "next": "chờ người xem lại",
            "confidence": "NGUOI"}


@pytest.fixture
def du_an_g2(tmp_path):
    d = tmp_path / "du-an-g2"
    d.mkdir()
    (d / "drv_eth.c").write_text(
        "// driver ethernet\nint init(void) {\n    return 0;\n}\n", "utf-8")
    return d


@pytest.fixture
def phien(du_an_g2):
    """Trả (tạo_agent, chạy) — tạo agent với kịch bản riêng cho từng lượt."""
    cfg = Config.for_project(du_an_g2)
    hop = {}

    def tao(script):
        a = Agent(cfg, llm=ScriptedGateway(script), project_name="du-an-g2")
        hop["agent"] = a
        hop["out"] = []
        hop["core"] = Core(a.ledger, a.ids, a.turn,
                           on_emit=hop["out"].append, on_sync=a.paint)
        return a

    def chay(act, script=None):
        a = hop["agent"]
        if script is not None:
            a.llm.script = ScriptedGateway(script).script
            a.llm._i = 0
        truoc = len(hop["out"])
        hop["core"].console_act(act)
        return hop["out"][truoc:]

    return tao, chay, hop


def loi_tac_tu(cmds) -> str:
    return "\n".join(c.params["text"] for c in cmds
                     if c.method == "console.post" and c.params.get("role") == "agent")


# =========================================================================== CX06
def test_CX06_nguoi_sua_REQ_thi_ha_nguon_STALE_va_tac_tu_nhac(phien, du_an_g2):
    """Hạ nguồn STALE đúng danh sách · <inventory> liệt kê · tác tử nhắc ở lượt sau."""
    tao, chay, hop = phien
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "store.req_create", {
            "id": "FR-01", "loai": "FR", "text": "Nhận tệp phim qua LAN",
            "criteria": "≥ 1 MB/s", "source_quote": "copy phim qua mạng LAN vào đó",
            "explain": EX("Ghi yêu cầu nhận tệp qua LAN")})]),
        Response(tool_calls=[ToolCall("c2", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;",
            "new_string": "return init_phy();",
            "explain": EX("Nối driver Ethernet với PHY theo FR-01")})]),
        Response(text="Đã ghi FR-01 và sửa drv_eth.c."),
    ])
    chay({"kind": "say", "text": "Ghi yêu cầu nhận phim qua LAN rồi nối driver"})

    # --- Anh sửa tiêu chí
    cmds = chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
                 "data": {"base_version": "v1", "fields": {"criteria": "≥ 5 MB/s"},
                          "summary": "nâng FR-01 lên ≥ 5 MB/s"},
                 "note": "phim 4K"})

    # 1. Hạ nguồn được đánh dấu, có lý do mang mã changeset.
    stale = agent.store.list(stale_only=True)
    assert [a["id"] for a in stale] == ["drv_eth.c"]
    assert "anh sửa FR-01" in stale[0]["stale_reason"]
    assert stale[0]["stale_reason"].startswith("cs-")

    # 2. Tác tử nói ra hệ quả, và nói rõ nó KHÔNG tự chạy lại.
    loi = loi_tac_tu(cmds)
    assert "drv_eth.c" in loi
    assert "chưa chạy lại" in loi

    # 3. <inventory> liệt kê STALE cho lượt sau.
    inv = agent.history and __import__("eide.store", fromlist=["inventory"]).inventory.build(
        agent.store, ledger=agent.ledger, project_name="du-an-g2")
    assert "drv_eth.c" in inv.render()
    assert "STALE" in inv.render()

    # 4. EIDE.md §"Người vừa sửa" có dòng của anh, kèm vì sao.
    assert "phim 4K" in agent.eide_md.get("Người vừa sửa")

    # 5. Sửa của người là một changeset thật, hoàn tác được, có lớp giải thích.
    cs = [c for c in agent.history.log.all() if c.by_human][-1]
    assert cs.reversible and cs.note == "phim 4K"
    assert cs.explain["confidence"] == "NGUOI"


# =========================================================================== CX07
def test_CX07_tac_tu_lo_thay_doi_thi_Stop_bat_them_mot_vong(phien):
    """Hook Stop bắt thêm một vòng; sau khi nhắc thì changeset được acknowledged."""
    tao, chay, hop = phien
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "store.req_create", {
            "id": "FR-01", "loai": "FR", "text": "Nhận tệp qua LAN",
            "criteria": "≥ 1 MB/s", "source_quote": "copy phim qua LAN",
            "explain": EX("Ghi FR-01")})]),
        Response(text="Xong."),
    ])
    chay({"kind": "say", "text": "ghi yêu cầu"})
    chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
          "data": {"base_version": "v1", "fields": {"criteria": "≥ 5 MB/s"},
                   "summary": "nâng lên 5 MB/s"}, "note": "phim 4K"})

    chua = agent.history.log.human_unacknowledged()
    assert len(chua) == 1, "sửa của người phải đang chờ tác tử nhắc"

    # Lượt sau: mô hình cư xử TỆ — nói một câu không liên quan.
    truoc = len(agent.llm.calls)
    cmds = chay({"kind": "say", "text": "tiếp tục đi"}, script=[
        Response(text="Hôm nay trời đẹp."),                 # lờ thay đổi của anh
        Response(text="Anh vừa sửa FR-01 lên ≥ 5 MB/s vì phim 4K. "
                      "Việc đó làm drv_eth.c cần xem lại."),  # sau khi bị nhắc
    ])
    assert len(agent.llm.calls) - truoc == 2, "hook Stop phải bắt mô hình thêm một vòng"
    nhac = [m["text"] for m in agent.messages if m.get("role") == "user"]
    assert any("chưa nhắc tới thay đổi" in t for t in nhac)
    assert "FR-01" in loi_tac_tu(cmds)
    assert not agent.history.log.human_unacknowledged(), "nhắc rồi thì phải được đánh dấu"


# =========================================================================== CX09
def test_CX09_nguoi_sua_tep_tac_tu_dang_khoa(phien, du_an_g2):
    """lock_broken: tác tử dừng, giữ bản của người, không ghi đè."""
    tao, chay, hop = phien
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;", "new_string": "return 1;",
            "explain": EX("Sửa mã trả về")})]),
        Response(text="Đã sửa."),
    ])
    chay({"kind": "say", "text": "sửa driver"})

    # Tác tử đang giữ soft-lock trong lượt; mô phỏng người sửa giữa chừng.
    agent.locks.add("drv_eth.c")
    hien_tai = (du_an_g2 / "drv_eth.c").read_text("utf-8")

    cmds = chay({"kind": "edit", "target": {"type": "file", "id": "drv_eth.c"},
                 "data": {"base_version": _bam(hien_tai),
                          "content": hien_tai.replace("return 1;", "return init_phy();"),
                          "summary": "dùng init_phy()"},
                 "note": "PHY phải được khởi tạo trước"})

    loi = loi_tac_tu(cmds)
    assert "dừng lại" in loi and "giữ bản của anh" in loi
    assert "không tự ghi đè" in loi
    # Bản của người thắng trên đĩa.
    assert "init_phy()" in (du_an_g2 / "drv_eth.c").read_text("utf-8")
    # Khoá được thả.
    assert "drv_eth.c" not in agent.locks


def test_CX09b_tac_tu_ghi_de_tep_nguoi_vua_sua_phai_qua_cong(phien, du_an_g2):
    """§E4 bước 6 — "fs.write vào tệp người vừa sửa → G-FILE"."""
    tao, chay, hop = phien
    agent = tao([])
    hien_tai = (du_an_g2 / "drv_eth.c").read_text("utf-8")
    chay({"kind": "edit", "target": {"type": "file", "id": "drv_eth.c"},
          "data": {"base_version": _bam(hien_tai),
                   "content": hien_tai + "// anh thêm dòng này\n",
                   "summary": "thêm ghi chú"}})

    cmds = chay({"kind": "say", "text": "viết lại driver"}, script=[
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "drv_eth.c", "content": "// tác tử viết đè\n",
            "explain": EX("Viết lại driver")})]),
    ])
    the = [c.params["card"] for c in cmds
           if c.method == "console.post" and c.params.get("card")]
    assert the and the[0]["gate"] == "G-FILE"
    assert "// anh thêm dòng này" in (du_an_g2 / "drv_eth.c").read_text("utf-8"), \
        "chưa duyệt cổng thì KHÔNG được ghi đè"


# =========================================================================== CX10
def test_CX10_hoan_tac_giua_chuoi_thi_canh_bao(phien, du_an_g2):
    """Cảnh báo chuỗi; lịch sử không mất; hoàn tác tạo changeset MỚI."""
    tao, chay, hop = phien
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;", "new_string": "return 1;",
            "explain": EX("bước 1")})]),
        Response(tool_calls=[ToolCall("c2", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 1;", "new_string": "return 2;",
            "explain": EX("bước 2")})]),
        Response(tool_calls=[ToolCall("c3", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 2;", "new_string": "return 3;",
            "explain": EX("bước 3")})]),
        Response(text="Đã sửa ba lần."),
    ])
    chay({"kind": "say", "text": "sửa ba lần"})

    ds = [c for c in agent.history.log.all() if c.touches
          and c.touches[0].artefact_id == "drv_eth.c"]
    assert len(ds) == 3
    giua = ds[1]

    kq = agent.history.hoan_tac_changeset(giua.id, by="human")
    assert kq.canh_bao, "phải cảnh báo còn thay đổi sau nó chạm cùng hiện vật"
    assert "hoàn tác cả chuỗi" in kq.canh_bao[0]
    assert ds[2].id in kq.canh_bao[0]

    # Lịch sử không mất: changeset cũ vẫn còn, chỉ được đánh dấu.
    assert agent.history.log.get(giua.id) is not None
    assert agent.history.log.get(giua.id).undone_by == kq.changeset_moi
    assert len(agent.history.log.all()) > len(ds), "hoàn tác tạo changeset MỚI"


def test_CX10b_hoan_tac_ca_luot_giu_thu_tu_nguoc(phien, du_an_g2):
    """§E5.2 mức 2 — hoàn tác mọi changeset của lượt, thứ tự ngược."""
    tao, chay, hop = phien
    goc = (du_an_g2 / "drv_eth.c").read_text("utf-8")
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 0;", "new_string": "return 1;",
            "explain": EX("bước 1")})]),
        Response(tool_calls=[ToolCall("c2", "fs.edit", {
            "path": "drv_eth.c", "old_string": "return 1;", "new_string": "return 2;",
            "explain": EX("bước 2")})]),
        Response(text="Xong."),
    ])
    chay({"kind": "say", "text": "sửa hai lần"})
    run_id = agent.last_report["run_id"]

    kq = agent.history.hoan_tac_luot(run_id, by="human")
    assert kq.ok and len(kq.da_lui) == 2
    assert (du_an_g2 / "drv_eth.c").read_text("utf-8") == goc


def test_CX11_hoan_tac_luot_co_thao_tac_khong_dao_nguoc(phien):
    """CX11 — changeset không hoàn tác được giữ nguyên, kèm cảnh báo rõ ràng."""
    tao, chay, hop = phien
    agent = tao([])
    agent.history.ghi_khong_hoan_tac(
        author="agent:run-001", what="target.flash", run_id="run-001",
        reason_vi="đã nạp vào chip",
        explain=EX("Nạp firmware v9 vào bo"))
    kq = agent.history.hoan_tac_luot("run-001", by="human")
    assert kq.giu_nguyen and kq.giu_nguyen[0]["ly_do"] == "đã nạp vào chip"
    assert any("KHÔNG hoàn tác được" in c for c in kq.canh_bao)


# =========================================================================== CX16
def test_CX16_phat_lai_tai_tao_trang_thai(phien, du_an_g2):
    """Phát lại sổ cái + changesets tái tạo transcript và trạng thái store 100 %."""
    tao, chay, hop = phien
    agent = tao([
        Response(tool_calls=[ToolCall("c1", "store.req_create", {
            "id": "FR-01", "loai": "FR", "text": "Nhận tệp qua LAN", "criteria": "≥ 1 MB/s",
            "source_quote": "copy phim qua LAN", "explain": EX("Ghi FR-01")})]),
        Response(tool_calls=[ToolCall("c2", "store.req_create", {
            "id": "FR-02", "loai": "FR", "text": "TV đọc như USB", "criteria": "10 s",
            "source_quote": "cắm vào TV", "explain": EX("Ghi FR-02")})]),
        Response(text="Đã ghi hai yêu cầu."),
    ])
    chay({"kind": "say", "text": "ghi hai yêu cầu"})
    chay({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
          "data": {"base_version": "v1", "fields": {"criteria": "≥ 5 MB/s"},
                   "summary": "nâng lên 5 MB/s"}, "note": "phim 4K"})

    truoc = {a["id"]: (a["version"], a["canonical"], a["author"])
             for a in agent.store.list(limit=100)}

    # 1. Dựng lại hình chiếu kho từ bảng events.
    agent.store.rebuild()
    sau = {a["id"]: (a["version"], a["canonical"], a["author"])
           for a in agent.store.list(limit=100)}
    assert sau == truoc

    # 2. Sổ cái toàn vẹn và phát lại được transcript.
    ok, msg = agent.ledger.verify()
    assert ok, msg
    dong = [e.data["params"]["text"] for e in agent.ledger.read()
            if e.kind == "ui_command" and e.data["method"] == "console.post"]
    assert any(t.startswith("[Bạn] Sửa req:FR-01") for t in dong)

    # 3. Mọi thay đổi đều có changeset; không có thay đổi nào ngoài changeset.
    su_kien_ghi = [e for e in agent.ledger.read() if e.kind == "changeset"]
    assert len(su_kien_ghi) == len(agent.history.log.all())

    # 4. Changeset nào cũng có phép nghịch đảo (trừ loại không đảo ngược được).
    for cs in agent.history.log.all():
        if cs.reversible and cs.touches:
            assert cs.inverse, f"{cs.id} hoàn tác được mà không có phép nghịch đảo"


def _bam(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# =========================================================================== git riêng
def test_du_an_trong_kho_git_khac_van_co_kho_rieng(tmp_path):
    """Kho git của dự án phải là của CHÍNH NÓ, không phải kho của thư mục cha.

    `git rev-parse --git-dir` đi ngược lên cây thư mục. Nếu chỉ hỏi câu đó, một dự án
    nằm trong thư mục con của một kho git khác sẽ bị coi là "đã có git" — và EIDE sẽ
    commit tệp của người dùng vào kho của người khác. Ca này canh đúng chuyện đó.
    """
    import subprocess
    cha = tmp_path / "kho-cha"
    cha.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=cha, check=True)

    du_an = cha / "du-an-con"
    du_an.mkdir()
    (du_an / "main.c").write_text("int main(void){return 0;}\n", "utf-8")

    from eide.vcs import Vcs
    v = Vcs(du_an)
    assert v.san_sang is False, "chưa có kho riêng thì phải báo là chưa có"
    v.khoi_tao()
    assert v.san_sang is True
    assert (du_an / ".git").exists(), "phải tạo kho git ngay trong thư mục dự án"

    top = subprocess.run(["git", "-C", str(du_an), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True).stdout.strip()
    assert pathlib.Path(top).resolve() == du_an.resolve()

    # Kho cha không có gì được thêm vào chỉ mục.
    r = subprocess.run(["git", "-C", str(cha), "status", "--porcelain"],
                       capture_output=True, text=True).stdout
    assert "du-an-con/main.c" not in r


# =========================================================================== constant-guard
def test_constant_guard_khong_chan_tai_lieu_van_xuoi(du_an_g2):
    """DEV-231 — tài liệu hướng dẫn cho người đọc KHÔNG bị soi hằng số.

    Lỗi thật: trong phiên 25/09, tác tử bị chặn khi ghi `HD-TRIEN-KHAI.md` vì con số
    "32 GB" trong đó — chính con số người dùng vừa nói. Kết quả: 33 lượt, không ghi
    nổi một tệp nào.
    """
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    bus = register_standard_hooks(HookBus())
    ctx = _ctx_gia(du_an_g2)

    call = {"tool": "fs.write", "args": {
        "path": "HD-TRIEN-KHAI.md",
        "content": "# Hướng dẫn\n\nTạo ổ đĩa ảo 32 GB, nhãn PTIT_USB.\n"
                   "Chạy ở tốc độ 480 Mbps qua USB 2.0.\n",
        "explain": EX("Hướng dẫn triển khai")}}
    r = bus.pre_tool_use(call, ctx)
    assert r.facts["constant_guard.unsourced"] == 0


def test_constant_guard_chan_hang_so_ky_thuat_trong_ma(du_an_g2):
    """Nhưng con số kỹ thuật trong MÃ thì vẫn phải có nguồn (N1)."""
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    bus = register_standard_hooks(HookBus())
    ctx = _ctx_gia(du_an_g2)

    call = {"tool": "fs.write", "args": {
        "path": "drv_i2c.c",
        "content": "#define I2C_TIMEOUT_MS 50\nstatic const int vdd_max = 5500;\n"
                   "// chờ 120 ms rồi thử lại\nvoid wait(void){ delay(120 ms); }\n",
        "explain": EX("Driver I2C")}}
    r = bus.pre_tool_use(call, ctx)
    assert r.facts["constant_guard.unsourced"] > 0, "hằng số kỹ thuật trong mã phải bị bắt"


def test_constant_guard_chap_nhan_so_nguoi_dung_da_noi(du_an_g2):
    """Con số chính người dùng nói ra là có nguồn — họ là một nguồn có tên (tầng NGƯỜI)."""
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    bus = register_standard_hooks(HookBus())
    ctx = _ctx_gia(du_an_g2)
    ctx.loi_nguoi_trong_phien = ["I2C của mình chạy timeout 50 ms nhé"]

    call = {"tool": "fs.write", "args": {
        "path": "drv_i2c.c", "content": "#define I2C_TIMEOUT_MS 50\n",
        "explain": EX("Driver I2C")}}
    r = bus.pre_tool_use(call, ctx)
    assert r.facts["constant_guard.unsourced"] == 0


def test_loi_tu_choi_noi_ro_hang_so_nao(du_an_g2):
    """Một lời từ chối không nói rõ cái gì sai thì mô hình chỉ biết thử lại y nguyên."""
    from eide.policy import PolicyEngine
    p = PolicyEngine()
    d = p.decide({"tool": "fs.write", "args": {"path": "a.c"}},
                 {"explain.complete": True, "constant_guard.unsourced": 2,
                  "constant_guard.list": ["50 ms", "5500"]})
    e = p.deny_error({"tool": "fs.write"}, d,
                     {"constant_guard.list": ["50 ms", "5500"]})
    assert "50 ms" in e.message_vi and "5500" in e.message_vi
    assert "fact.assert_human" in e.message_vi


def _ctx_gia(du_an):
    """Ngữ cảnh tối thiểu cho hook: sandbox, kho, EIDE.md, sổ đăng ký, lời người."""
    from eide import Config
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        store = Store(config.paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="du-an-g2")
        registry = build_registry()
        history = None
        loi_nguoi_trong_phien: list = []
    return C()


# =========================================================================== CX02 chi tiết
def test_CX02_sources_rong_hop_le_khi_khong_co_so(du_an_g2):
    """N8 — `sources` rỗng chấp nhận được khi summary/why không có con số nào.

    §E3.1 ràng buộc *con số* phải có nguồn, không ràng buộc *danh sách phải khác rỗng*.
    Bắt chặt hơn thế sẽ chặn mọi hiện vật thuần mô tả, và mô hình học cách nhét một
    nguồn giả vào cho qua cửa — đổi một quy tắc đúng lấy một thói quen sai.
    """
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    bus = register_standard_hooks(HookBus())
    ctx = _ctx_gia(du_an_g2)

    khong_so = {"summary": "Đổi tên khối cho gọn", "why": "người dùng thấy khó đọc",
                "sources": [], "diff_prev": "chỉ đổi tên", "next": "—",
                "confidence": "NGUOI"}
    r = bus.pre_tool_use({"tool": "store.req_create",
                          "args": {"id": "FR-1", "loai": "FR", "text": "x",
                                   "source_quote": "y", "explain": khong_so}}, ctx)
    assert r.ok, "hiện vật không có con số nào thì sources rỗng là hợp lệ"

    co_so = {**khong_so, "summary": "Nâng ngưỡng lên 5 MB/s",
             "why": "phim 4K cần 5 MB/s"}
    r2 = bus.pre_tool_use({"tool": "store.req_create",
                           "args": {"id": "FR-2", "loai": "FR", "text": "x",
                                    "source_quote": "y", "explain": co_so}}, ctx)
    assert not r2.ok, "có con số trong summary/why mà không dẫn nguồn thì phải bị chặn"
    assert "sources" in r2.error.hint_for_agent


def test_CX08_sua_trinh_bay_khong_gay_stale(du_an_g2):
    """§E4.1 — đổi tên/ghi chú không làm hạ nguồn lỗi thời."""
    from eide import human_edit as he
    pl = he.phan_loai(truoc={"ten": "Khối A", "text": "nội dung"},
                      sau={"ten": "Khối B", "text": "nội dung"})
    assert pl.loai == "trinh_bay" and pl.gay_stale is False

    pl2 = he.phan_loai(truoc={"criteria": "≥ 1 MB/s"}, sau={"criteria": "≥ 5 MB/s"})
    assert pl2.loai == "noi_dung" and pl2.gay_stale is True

    pl3 = he.phan_loai(truoc={"da_chon": False}, sau={"da_chon": True})
    assert pl3.loai == "quyet_dinh"


def test_CX05_so_moi_thanh_fact_nguoi(du_an_g2):
    """§E4 bước 3 — số mới người nhập mà chưa truy vết được thành Fact tầng NGƯỜI."""
    from eide import human_edit as he
    ds = he.so_moi_khong_nguon(truoc={"criteria": "≥ 1 MB/s"},
                               sau={"criteria": "≥ 5 MB/s"},
                               nguon_da_co="")
    assert len(ds) == 1
    assert ds[0].gia_tri == "5" and ds[0].don_vi == "MB/s"
    assert ds[0].khoa == "criteria.thong_luong"

    # Số đã có nguồn thì không tạo lại.
    assert not he.so_moi_khong_nguon(truoc={"criteria": "≥ 1 MB/s"},
                                     sau={"criteria": "≥ 5 MB/s"},
                                     nguon_da_co="ngưỡng 5 MB/s đã chốt trong ADR-01")

    # Số vốn đã có trong bản cũ thì không phải "mới".
    assert not he.so_moi_khong_nguon(truoc={"t": "chạy 50 ms rồi nghỉ"},
                                     sau={"t": "chạy 50 ms rồi nghỉ lâu hơn"},
                                     nguon_da_co="")
