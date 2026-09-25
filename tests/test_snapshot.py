# -*- coding: utf-8 -*-
"""Snapshot và rẽ nhánh — EIDE-MDD-40 §E5.5, §E6. Bước G5.

Ca đo: CX11 (hoàn tác lượt có flash), CX12 (tác tử đề xuất snapshot), CX13 (khôi phục
khi có sửa của người sau đó), CX14 (so sánh hai snapshot), CX15 (RDP khi chưa có release).
"""

from __future__ import annotations

import pytest

from eide import Agent, Config
from eide.llm import ScriptedGateway


def EX(s: str) -> dict:
    return {"summary": s, "why": "kiểm thử", "sources": [],
            "diff_prev": "bản đầu tiên", "next": "—", "confidence": "NGUOI"}


@pytest.fixture
def agent(tmp_path):
    d = tmp_path / "du-an-snap"
    d.mkdir()
    (d / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    return Agent(Config.for_project(d), llm=ScriptedGateway([]), project_name="du-an-snap")


def _req(a, ma: str, text: str, tieu_chi: str = ""):
    return a.history.ghi_kho(
        author="agent:run-1", artefact_id=ma, type="req", op="update"
        if a.store.get(ma) else "create",
        canonical={"loai": "FR", "text": text, "criteria": tieu_chi,
                   "source_quote": "người dùng nói"},
        explain=EX(f"Ghi {ma}"), run_id="run-1")


# =========================================================================== tạo
def test_ban_ung_y_phai_co_ten(agent):
    """§E6.2 — tên là thứ dẫn người quay về đúng chỗ. Không có tên thì không ghi."""
    with pytest.raises(ValueError, match="phải có tên"):
        agent.history.tao_snapshot(ten="   ")
    with pytest.raises(ValueError, match="phải có tên"):
        agent.history.tao_snapshot(ten="", kind="release")


def test_checkpoint_ngam_khong_can_ten(agent):
    s = agent.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trước run-1")
    assert s.kind == "checkpoint" and not s.co_ten
    assert s not in agent.history.snapshots.all(), "checkpoint ẩn khỏi danh sách"
    assert s.id in [x.id for x in agent.history.snapshots.all(gom_checkpoint=True)]


def test_trung_ten_bi_tu_choi(agent):
    _req(agent, "FR-01", "Nhận tệp qua LAN")
    agent.history.tao_snapshot(ten="v0.1-chay-duoc")
    with pytest.raises(ValueError, match="Đã có bản ưng ý tên"):
        agent.history.tao_snapshot(ten="v0.1-chay-duoc")


def test_snapshot_bat_bien(agent):
    """`immutable: true` được giữ bằng mã, không bằng lời hứa."""
    _req(agent, "FR-01", "x")
    s = agent.history.tao_snapshot(ten="mot-ban")
    assert s.immutable
    with pytest.raises(ValueError, match="bất biến"):
        agent.history.snapshots.ghi(s)


def test_noi_dung_snapshot_du_de_dung_lai(agent):
    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 5 MB/s")
    agent.store.put_fact({"fact_id": "f1", "subject": "chip:X", "key": "vdd.max",
                          "value": 5.5, "unit": "V", "tier": "VANG", "origin": "extract",
                          "source": {"doc_id": "DS", "page": 258}, "explain": {}})
    s = agent.history.tao_snapshot(ten="co-noi-dung")
    c = s.contents
    assert c["store_export_hash"], "phải có bản xuất kho để khôi phục được"
    assert c["facts_tier_counts"] == {"VANG": 1}
    assert c["so_req"] == 1
    assert agent.history.blobs.exists(c["store_export_hash"])
    assert "1 yêu cầu" in s.tom_tat() and "VANG 1" in s.tom_tat()


# =========================================================================== khôi phục
def test_CX13_khoi_phuc_khong_xoa_lich_su(agent):
    """§E6.3 — khôi phục tạo changeset MỚI; bản trước vẫn nằm trong dòng thời gian."""
    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 1 MB/s")
    s = agent.history.tao_snapshot(ten="truoc-khi-sua")
    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 9 MB/s")
    _req(agent, "FR-02", "Thêm yêu cầu sau snapshot")
    so_cs_truoc = len(agent.history.log.all())

    kq = agent.history.khoi_phuc_snapshot(s.id)
    assert kq.ok
    assert len(agent.history.log.all()) > so_cs_truoc, "phải tạo changeset mới"
    assert agent.store.get("FR-01")["canonical"]["criteria"] == "≥ 1 MB/s"
    assert agent.store.get("FR-02") is None, "hiện vật sinh sau snapshot phải được gỡ"
    assert "không mất gì" in kq.message_vi


def test_CX13_liet_ke_se_mat_gi_truoc_khi_hoi(agent):
    """Thẻ G-HIST phải nói SẼ MẤT GÌ, không chỉ hỏi "anh chắc chưa"."""
    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 1 MB/s")
    s = agent.history.tao_snapshot(ten="moc")
    _req(agent, "FR-02", "Yêu cầu mới")
    agent.history.ghi_kho(author="human", artefact_id="FR-01", type="req", op="update",
                          canonical={"loai": "FR", "text": "anh sửa", "criteria": "≥ 7 MB/s",
                                     "source_quote": "x"},
                          explain=EX("anh sửa"), human_act_id="h-1")

    bc = agent.history.se_mat_gi_khi_khoi_phuc(s.id)
    assert bc["ok"]
    assert bc["co_sua_cua_nguoi"], "phải cảnh báo có sửa của người sẽ mất"
    assert bc["cua_nguoi"], "phải liệt kê đúng changeset nào của người"
    assert bc["se_mat_vi"], "phải nói bằng lời sẽ mất gì"
    assert any("FR-02" in x for x in bc["se_mat_vi"])


def test_CX13_giu_ban_hien_tai_truoc_khi_khoi_phuc(agent):
    """§E6.3 gợi ý: ghi bản hiện tại thành snapshot trước, rồi mới khôi phục."""
    _req(agent, "FR-01", "bản gốc")
    s = agent.history.tao_snapshot(ten="goc")
    _req(agent, "FR-01", "bản thử nghiệm")

    kq = agent.history.khoi_phuc_snapshot(s.id, giu_ban_hien_tai="thu-nghiem-dma")
    assert kq.ok
    assert agent.history.snapshots.theo_ten("thu-nghiem-dma") is not None
    assert any("thu-nghiem-dma" in c for c in kq.canh_bao)
    assert agent.store.get("FR-01")["canonical"]["text"] == "bản gốc"


def test_khoi_phuc_snapshot_khong_ton_tai(agent):
    kq = agent.history.khoi_phuc_snapshot("snap-99")
    assert not kq.ok and "snap-99" in kq.message_vi


# =========================================================================== so sánh
def test_CX14_so_sanh_hai_snapshot_theo_loai_hien_vat(agent):
    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 1 MB/s")
    a = agent.history.tao_snapshot(ten="ban-a")

    _req(agent, "FR-01", "Nhận tệp qua LAN", "≥ 5 MB/s")
    _req(agent, "FR-02", "TV đọc như USB")
    agent.store.put_fact({"fact_id": "f1", "subject": "chip:X", "key": "vdd.max",
                          "value": 5.5, "unit": "V", "tier": "VANG", "origin": "extract",
                          "source": {}, "explain": {}})
    b = agent.history.tao_snapshot(ten="ban-b")

    kq = agent.history.so_sanh_snapshot(a.id, b.id)
    assert kq["ok"] and not kq["giong_nhau"]
    theo_loai = {k["loai"]: k for k in kq["khac_biet"]}
    assert "req" in theo_loai
    assert "FR-02" in theo_loai["req"]["them"]
    assert any(x["id"] == "FR-01" for x in theo_loai["req"]["doi"])
    assert "fact" in theo_loai and theo_loai["fact"]["them"]


def test_so_sanh_hai_ban_giong_nhau(agent):
    _req(agent, "FR-01", "x")
    a = agent.history.tao_snapshot(ten="a")
    b = agent.history.tao_snapshot(ten="b")
    kq = agent.history.so_sanh_snapshot(a.id, b.id)
    assert kq["ok"] and kq["giong_nhau"]
    assert "giống hệt" in kq["message_vi"]


def test_so_sanh_voi_hien_tai(agent):
    _req(agent, "FR-01", "cũ")
    a = agent.history.tao_snapshot(ten="a")
    _req(agent, "FR-01", "mới")
    kq = agent.history.so_sanh_snapshot(a.id, "hien_tai")
    assert kq["ok"] and not kq["giong_nhau"]
    assert kq["sang"]["ten"] == "hiện tại"


# =========================================================================== release
def test_CX15_release_la_dieu_kien_cho_thao_tac_khoa_vinh_vien(agent):
    """Sau khi khoá chip thì không còn đường lùi — phải có bản đã biết là chạy được."""
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks
    from eide.policy import PolicyEngine

    bus = register_standard_hooks(HookBus())
    pol = PolicyEngine()
    goi = {"tool": "target.dangerous", "args": {"what": "rdp"}}

    class C:
        config = agent.config
        store = agent.store
        eide_md = agent.eide_md
        registry = agent.registry
        history = agent.history
        loi_nguoi_trong_phien: list = []

    r = bus.pre_tool_use(goi, C())
    assert r.facts["snapshot.has_release"] is False
    d = pol.decide(goi, r.facts)
    assert d.action == "deny" and "release" in d.reason_vi.lower()

    _req(agent, "FR-01", "x")
    s = agent.history.tao_snapshot(ten="v1.0-chay-tren-bo-that")
    agent.history.snapshots.danh_dau_release(s.id)

    r2 = bus.pre_tool_use(goi, C())
    assert r2.facts["snapshot.has_release"] is True
    assert pol.decide(goi, r2.facts).action == "ask", "có release rồi thì hỏi, không chặn"


def test_checkpoint_khong_danh_dau_release_duoc(agent):
    """Checkpoint ngầm không phải bản người chọn — không thể thành release."""
    s = agent.history.tao_snapshot(ten="", kind="checkpoint")
    assert agent.history.snapshots.danh_dau_release(s.id) is None
    assert not agent.history.snapshots.co_release()


# =========================================================================== nhánh
def test_re_nhanh_va_chuyen_nhanh(agent):
    _req(agent, "FR-01", "x")
    kq = agent.history.tao_nhanh("thu-mtp")
    assert kq["ok"] and kq["nhanh"] == "thu-mtp"
    assert agent.history.nhanh_hien_tai() == "thu-mtp"
    assert "thu-mtp" in agent.history.danh_sach_nhanh()
    assert kq["tu_nhanh"] in agent.history.danh_sach_nhanh()

    ve = agent.history.chuyen_nhanh(kq["tu_nhanh"])
    assert ve["ok"] and agent.history.nhanh_hien_tai() == kq["tu_nhanh"]


def test_chuyen_nhanh_khong_ton_tai(agent):
    kq = agent.history.chuyen_nhanh("nhanh-khong-co")
    assert not kq["ok"]


def test_danh_sach_snapshot_co_khoang_cach(agent):
    """§E6.3 — "mở lại dự án luôn nêu snapshot gần nhất và khoảng cách"."""
    _req(agent, "FR-01", "x")
    agent.history.tao_snapshot(ten="moc-dau")
    _req(agent, "FR-02", "y")
    _req(agent, "FR-03", "z")

    ds = agent.history.danh_sach_snapshot()
    assert len(ds) == 1
    assert ds[0]["khoang_cach"] == 2, "hai changeset kể từ bản ưng ý đó"
    assert ds[0]["tom_tat"]


# =========================================================================== tên do người đặt
def _hook_ten(agent, ten: str, loi: list[str]) -> dict:
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    class C:
        config = agent.config
        store = agent.store
        eide_md = agent.eide_md
        registry = agent.registry
        history = agent.history
        loi_nguoi_trong_phien = loi
    return register_standard_hooks(HookBus()).pre_tool_use(
        {"tool": "snapshot.create", "args": {"ten": ten}}, C()).facts


def test_ten_phai_co_trong_loi_nguoi(agent):
    """§E6.2 — cấm bằng lời trong mô tả công cụ là cấm không đo được."""
    assert _hook_ten(agent, "sau-khi-sua-driver", ["ghi lại giúp mình"])[
        "snapshot.ten_tu_nguoi"] is False
    assert _hook_ten(agent, "v0.1-chay-duoc", ["ghi bản ưng ý tên v0.1-chay-duoc nhé"])[
        "snapshot.ten_tu_nguoi"] is True


def test_ten_chuan_hoa_van_la_ten_cua_nguoi(agent):
    """Người gõ có dấu và có khoảng trắng; tác tử chuẩn hoá — vẫn là tên của người."""
    assert _hook_ten(agent, "v0.2-them-nhiet", ["ghi bản v0.2 thêm nhiệt đi"])[
        "snapshot.ten_tu_nguoi"] is True


def test_cong_cu_khac_khong_bi_chot_chan_nay(agent):
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    class C:
        config = agent.config
        store = agent.store
        eide_md = agent.eide_md
        registry = agent.registry
        history = agent.history
        loi_nguoi_trong_phien: list = []
    f = register_standard_hooks(HookBus()).pre_tool_use(
        {"tool": "snapshot.list", "args": {}}, C()).facts
    assert f["snapshot.ten_tu_nguoi"] is True
