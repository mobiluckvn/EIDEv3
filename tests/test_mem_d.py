# -*- coding: utf-8 -*-
"""MEM-D — C3/C4, retention, đo lường. EIDE-MEM-42 §6.4, §6.5, §7.4, §13.

Nguyên tắc duy nhất của phần dọn rác, và nó quyết định toàn bộ thiết kế: **dọn theo
THAM CHIẾU, không theo tuổi.** Một blob 30 ngày mà một snapshot có tên đang trỏ tới là
bằng chứng của một bản người dùng sẽ quay về; xoá nó theo tuổi là biến "khôi phục được"
thành một lời hứa suông.
"""

from __future__ import annotations

import json

import pytest

from eide.memory.don_dep import GIU, KHONG_BAO_GIO_DON, do_luong, gc
from eide.memory.nen import c4


# =========================================================================== C4
def _ms(n: int) -> list[dict]:
    r: list[dict] = []
    for i in range(n):
        r.append({"role": "user", "text": f"việc {i}", "_kind": "say"})
        r.append({"role": "tool", "tool": "fs.read", "tool_call_id": f"c{i}",
                  "result": {"ok": True, "data": {"content": "nội dung " * 300}},
                  "envelope": {"summary_line": f"fs.read f{i}.c",
                               "blob_ref": f"blob:sha256:{i:064d}"}})
    return r


def test_C4_bo_MOI_ket_qua_cong_cu_ke_ca_moi_nhat():
    """Khác C1: C4 không tha kết quả của lượt gần nhất. Ở 95 % thì không còn chỗ tha."""
    ms = _ms(5)
    bc = c4(ms)
    assert bc["stub"] == 5
    assert all(m.get("_stub") for m in ms if m["role"] == "tool")
    assert bc["sau"] < bc["truoc"] and bc["giam_phan_tram"] > 50


def test_C4_KHONG_goi_mo_hinh(make_agent):
    """Ở mức 95 %, mỗi lời gọi mô hình thêm vào là một rủi ro hỏng giữa chừng."""
    agent = make_agent([])
    ms = _ms(5)
    c4(ms)
    assert len(agent.llm.calls) == 0


def test_C4_van_giu_duong_doc_lai():
    ms = _ms(3)
    c4(ms)
    stub = next(m for m in ms if m.get("_stub"))
    assert "blob:sha256:" in stub["result"]["_da_thu_gon"]
    assert "blob.read" in stub["result"]["_da_thu_gon"]


def test_C4_khong_cham_message_GHIM():
    ms = _ms(3)
    bc = c4(ms, ghim={1})
    assert not ms[1].get("_stub"), "ghim thì C4 cũng không được chạm"
    assert bc["stub"] == 2


def test_C4_khong_vut_message_nao():
    ms = _ms(4)
    n = len(ms)
    c4(ms)
    assert len(ms) == n, "C4 thu gọn, không cắt bỏ"


def test_C4_chay_lai_khong_hong():
    ms = _ms(3)
    c4(ms)
    assert c4(ms)["stub"] == 0


def test_C4_qua_vong_lap_ghi_so_cai_va_NOI_VOI_NGUOI(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    for m in _ms(6):
        agent.messages.append(m)
    thay: list = []
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=thay.append, history=agent.history, agent=agent,
                      run_id="run-1")
    agent._compact(ctx, "C4")

    su = [e for e in agent.ledger.read()
          if e.kind == "compact" and e.data.get("buoc") == "c4"]
    assert su, "C4 phải để lại dấu trong sổ cái"
    bao = [c for c in thay if c.method == "notice" and c.params.get("code") == "C4"]
    assert bao and "blob.read" in bao[0].params["text"]
    assert "mở một lượt mới" in bao[0].params["text"]


# =========================================================================== C3
def test_C3_ha_K_xuong_6(make_agent):
    """§6.4 — phiên rất dài thì giữ ít nguyên văn hơn để còn chỗ."""
    from eide.memory.nen import K_GIAM_C3, K_LUOT

    assert K_LUOT == 10 and K_GIAM_C3 == 6


# =========================================================================== retention
def _blob(paths, noi: str) -> str:
    import hashlib

    b = noi.encode("utf-8")
    h = hashlib.sha256(b).hexdigest()
    p = paths.blobs / h[:2] / h
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b)
    return h


def _lam_cu(paths, h: str, ngay: int) -> None:
    import os
    import time

    p = paths.blobs / h[:2] / h
    t = time.time() - ngay * 86400
    os.utime(p, (t, t))


def test_MEM19_blob_CO_THAM_CHIEU_thi_giu_du_bao_nhieu_ngay(make_agent):
    agent = make_agent([])
    p = agent.config.paths
    h = _blob(p, "bằng chứng của một snapshot")
    _lam_cu(p, h, 400)
    (p.state_dir / "snapshots.jsonl").write_text(
        json.dumps({"id": "snap-01", "contents": {"store_export_hash": h}}) + "\n",
        "utf-8")

    bc = gc(p, thu=True)
    assert h not in bc.blob_se_xoa, "snapshot đang trỏ tới — không được xoá"
    assert bc.blob_co_tham_chieu >= 1


def test_MEM19_blob_khong_ai_tro_va_qua_han_thi_de_xuat_xoa(make_agent):
    agent = make_agent([])
    p = agent.config.paths
    h = _blob(p, "kết quả fs.read không ai cần nữa")
    _lam_cu(p, h, GIU["blob_ngay"] + 5)

    bc = gc(p, thu=True)
    assert h in bc.blob_se_xoa and bc.byte_thu_hoi > 0
    # thu=True thì KHÔNG được xoá thật.
    assert (p.blobs / h[:2] / h).exists()
    assert "Chưa xoá gì" in bc.dong_vi() or "có thể thu hồi" in bc.dong_vi().lower()


def test_MEM19_blob_moi_thi_giu_va_NOI_VI_SAO(make_agent):
    agent = make_agent([])
    p = agent.config.paths
    h = _blob(p, "mới đọc hôm nay")
    bc = gc(p, thu=True)
    assert h not in bc.blob_se_xoa
    assert any("mới" in g for g in bc.giu_lai_vi), bc.giu_lai_vi


def test_MEM19_thuc_hien_thi_xoa_that(make_agent):
    agent = make_agent([])
    p = agent.config.paths
    h = _blob(p, "rác thật")
    _lam_cu(p, h, GIU["blob_ngay"] + 1)
    gc(p, thu=False)
    assert not (p.blobs / h[:2] / h).exists()


def test_MEM19_tham_chieu_tim_trong_MOI_noi_co_the_tro(make_agent):
    """Bỏ sót một chỗ trỏ nghĩa là xoá một bằng chứng — thà quét rộng tay."""
    agent = make_agent([])
    p = agent.config.paths
    for ten in ("changesets.jsonl", "ledger.jsonl"):
        h = _blob(p, f"được trỏ từ {ten}")
        _lam_cu(p, h, 500)
        (p.state_dir / ten).write_text(json.dumps({"blob": h}) + "\n", "utf-8")
        assert h not in gc(p, thu=True).blob_se_xoa, ten


def test_MEM19_nhung_thu_VINH_VIEN_khong_bao_gio_bi_don():
    for ten in ("ledger.jsonl", "changesets.jsonl", "store.sqlite", "EIDE.md"):
        assert ten in KHONG_BAO_GIO_DON


def test_gc_tren_du_an_chua_co_blob_nao(make_agent):
    agent = make_agent([])
    bc = gc(agent.config.paths, thu=True)
    assert bc.blob_tong >= 0 and bc.blob_se_xoa == []


# =========================================================================== §13 đo lường
def test_MEM24_do_luong_doc_tu_SO_CAI(make_agent):
    """Biến đếm trong bộ nhớ chỉ đúng khi tiến trình còn sống; câu hỏi "bộ nhớ có tốt
    lên không" là câu hỏi qua nhiều phiên."""
    agent = make_agent([])
    for i in range(12):
        agent.ledger.append("turn.end", {
            "run_id": f"run-{i}", "cost": {"tokens": {"vao": 40_000 + i, "ra": 500}}})
    agent.ledger.append("compact", {"run_id": "run-5", "buoc": "ok", "lan": 1,
                                    "diem": "3/3"})

    d = do_luong(agent.ledger, cua_so=1_000_000)
    assert d.so_luot == 12
    assert 40_000 <= d.token_trung_vi <= 40_012
    assert d.ty_le_cua_so < 0.05
    assert d.so_lan_c2 == 1 and d.ty_le_kiem_dat_lan_dau == 1.0
    assert d.luot_moi_lan_c2 == pytest.approx(12.0)


def test_MEM24_chua_du_du_lieu_thi_noi_CHUA_DU_khong_noi_dat(make_agent):
    """N6 áp vào chính phép đo: không có dữ liệu không phải là đạt."""
    agent = make_agent([])
    agent.ledger.append("turn.end", {"run_id": "r1",
                                     "cost": {"tokens": {"vao": 100, "ra": 10}}})
    bang = do_luong(agent.ledger).dat_khong()
    assert bang and all(b["ket_qua"] == "chưa đủ dữ liệu" for b in bang), bang


def test_MEM24_dem_so_lan_KHONG_kiem_duoc(make_agent):
    agent = make_agent([])
    agent.ledger.append("compact", {"buoc": "khong_kiem_duoc", "lan": 1})
    agent.ledger.append("compact", {"buoc": "khong_kiem_duoc", "lan": 1})
    assert do_luong(agent.ledger).so_lan_khong_kiem_duoc == 2


def test_MEM24_moi_chi_so_deu_co_MUC_TIEU_doc_duoc(make_agent):
    agent = make_agent([])
    d = do_luong(agent.ledger)
    assert set(d.muc_tieu) >= {"token_moi_luot", "tan_suat_c2", "kiem_dat_lan_dau",
                               "chi_phi_nen"}
    for b in d.dat_khong():
        assert b["muc_tieu"] and b["chi_so"]


# =========================================================================== qua công cụ
def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, agent=agent,
                       run_id="run-1")


def test_memory_gc_mac_dinh_chi_DE_XUAT(make_agent):
    agent = make_agent([])
    p = agent.config.paths
    h = _blob(p, "rác")
    _lam_cu(p, h, GIU["blob_ngay"] + 2)
    r = agent.registry.run("memory.gc", {}, _ctx(agent))
    assert r.ok and r.data["thu"] is True
    assert (p.blobs / h[:2] / h).exists(), "mặc định KHÔNG được xoá"
    assert "Chưa xoá gì" in r.data["note_vi"]
    assert "THAM CHIẾU, không theo tuổi" in r.data["note_vi"]


def test_memory_metrics_qua_cong_cu(make_agent):
    agent = make_agent([])
    r = agent.registry.run("memory.metrics", {}, _ctx(agent))
    assert r.ok and "danh_gia" in r.data
    assert "CHƯA đủ dữ liệu" in r.data["note_vi"] or r.data["so_luot"] > 0
