# -*- coding: utf-8 -*-
"""Gộp nhánh — phần §E5.5 để ngỏ trong thiết kế gốc.

Trước `branch.merge`, ba công cụ `branch.create`/`switch`/`list` cho thử hai phương án song
song mà **không có đường mang kết quả về**: nhánh thử xong là một ngõ cụt, muốn dùng thì chép
tay từng tệp. Đo 30/09/2026 — `branch.merge` có trong tài liệu thiết kế nhưng không có trong mã.

Một nhánh có **hai nửa** và chúng gộp theo hai cách: tệp bằng git, hiện vật bằng phép so ba
bên. Ca quan trọng nhất ở đây là ca nó **từ chối trộn** — hiện vật cả hai bên cùng đổi thì
không phép trộn nào đúng, và chọn hộ là giả mạo xuất xứ của quyết định.
"""

from __future__ import annotations

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "đầu", "next": "n",
      "confidence": "NGUOI"}


@pytest.fixture
def ag(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent

    a = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    if not a.history.git_san:
        pytest.skip("máy không dùng được git — phép gộp nhánh không đo được ở đây")
    return a


def _ghi(ag, aid, val):
    ag.store.apply(artefact_id=aid, type="req", op="update" if ag.store.get(aid) else "create",
                   author="agent:t", canonical={"text": val}, explain=EX)


def test_gop_lay_hien_vat_chi_MOT_ben_doi(ag, du_an):
    _ghi(ag, "REQ-01", "gốc")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="gốc", boi="eide")

    ag.history.tao_nhanh("thu-a")
    _ghi(ag, "REQ-02", "chỉ nhánh A viết")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trên nhánh A", boi="eide")
    ag.history.chuyen_nhanh("main")

    kq = ag.history.gop_nhanh("thu-a")
    assert kq["ok"], kq["message_vi"]
    assert "REQ-02" in kq["da_lay"]
    assert kq["xung_dot"] == []
    # Hiện vật của nhánh kia THẬT SỰ có trong kho bây giờ, không chỉ trong báo cáo.
    assert ag.store.get("REQ-02")["canonical"]["text"] == "chỉ nhánh A viết"


def test_ca_hai_ben_cung_doi_thi_KHONG_tron(ag):
    """Không phép trộn nào đúng: lấy bên nào cũng là vứt bỏ một quyết định ai đó đã cân nhắc."""
    _ghi(ag, "REQ-01", "gốc")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="gốc", boi="eide")

    ag.history.tao_nhanh("thu-b")
    _ghi(ag, "REQ-01", "bản của nhánh B")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trên B", boi="eide")
    ag.history.chuyen_nhanh("main")
    _ghi(ag, "REQ-01", "bản của main")

    kq = ag.history.gop_nhanh("thu-b")
    assert kq["ok"]
    assert "REQ-01" in kq["xung_dot"]
    assert "REQ-01" not in kq["da_lay"]
    # KHÔNG bị ghi đè — bên này giữ nguyên bản của mình.
    assert ag.store.get("REQ-01")["canonical"]["text"] == "bản của main"
    assert "không tự trộn" in kq["ghi_chu_hien_vat"].lower()


def test_gop_chinh_no_va_nhanh_khong_co_thi_tu_choi(ag):
    assert not ag.history.gop_nhanh(ag.history.nhanh_hien_tai())["ok"]
    kq = ag.history.gop_nhanh("khong-ton-tai")
    assert not kq["ok"] and "Không có nhánh" in kq["message_vi"]


def test_luon_chup_mot_moc_TRUOC_khi_gop(ag):
    """Gộp đổi cả cây làm việc. Đường lui phải có sẵn TRƯỚC khi đi, không dựng lại sau khi hỏng."""
    _ghi(ag, "REQ-01", "gốc")
    ag.history.tao_nhanh("thu-c")
    _ghi(ag, "REQ-09", "x")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trên C", boi="eide")
    ag.history.chuyen_nhanh("main")

    kq = ag.history.gop_nhanh("thu-c")
    assert kq["snapshot_truoc"].startswith("snap-")
    assert ag.history.snapshots.get(kq["snapshot_truoc"]) is not None


def test_ban_chup_GHI_LAI_nhanh_cua_no(ag):
    """Không ghi thì không tìm ra "trạng thái kho của nhánh kia" — mọi bản chụp trông như nhau."""
    ag.history.tao_nhanh("thu-d")
    s = ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="x", boi="eide")
    assert s.contents["nhanh"] == "thu-d"


def test_cong_cu_branch_merge_co_cong_va_R3():
    from eide.tools import build_registry

    t = build_registry().get("branch.merge")
    assert t is not None and t.risk == "R3" and t.gate == "G-HIST"


def test_chuyen_nhanh_KHOI_PHUC_kho_hien_vat(ag):
    """Nửa thứ hai của một nhánh trước đây KHÔNG có.

    `tao_nhanh` ghi trong docstring rằng *"chuyển nhánh sẽ khôi phục nửa thứ hai"*, nhưng mã
    chỉ gọi `git checkout` — nên viết một REQ trên nhánh thử rồi quay về `main` thì REQ ấy
    **vẫn nằm đó**. Hai phương án song song dùng chung một kho thì không phải hai phương án
    song song.

    Lộ ra khi viết `branch.merge`: phép gộp không thấy hiện vật nào "chỉ bên kia đổi", vì
    chúng chưa bao giờ bị tách ra.
    """
    _ghi(ag, "REQ-01", "gốc")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trên main", boi="eide")

    ag.history.tao_nhanh("thu-e")
    _ghi(ag, "REQ-77", "chỉ có trên nhánh E")
    ag.history.tao_snapshot(ten="", kind="checkpoint", ghi_chu="trên E", boi="eide")

    ag.history.chuyen_nhanh("main")
    assert ag.store.get("REQ-77") is None, \
        "hiện vật của nhánh kia còn nằm lại trên main — nhánh không cô lập gì cả"
    assert ag.store.get("REQ-01") is not None, "mất luôn hiện vật của chính nhánh này"

    # Quay lại nhánh thì nó có lại.
    ag.history.chuyen_nhanh("thu-e")
    assert ag.store.get("REQ-77") is not None


def test_chuyen_nhanh_luon_giu_lai_trang_thai_vua_roi_khoi(ag):
    _ghi(ag, "REQ-01", "x")
    ag.history.tao_nhanh("thu-f")
    kq = ag.history.chuyen_nhanh("main")
    assert kq["snapshot_truoc"].startswith("snap-")
    assert ag.history.snapshots.get(kq["snapshot_truoc"]) is not None
