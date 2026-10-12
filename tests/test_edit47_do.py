# -*- coding: utf-8 -*-
"""Bốn chỉ số của EIDE-EDIT-47 §7 — và chỗ sổ cái phải ghi để đo được chỉ số thứ tư.

§7 nói đo "hoàn tác thành công / thất bại, **theo tầng**" bằng *"ledger `undo` +
`KetQuaHoanTac.ok`"*. Mở sổ cái ra thì **không có loại sự kiện nào tên `undo`**: ý chí của
người có trong `human_act`, còn KẾT QUẢ thì chỉ suy được từ chuyện sau đó có một
`history.update` hay không.

Suy không phải đo. Một lần lùi thất bại vì *"đã hoàn tác rồi"* trông y hệt một lần lời gọi
không bao giờ chạy — đúng cái lỗ mà cả dự án này gặp đi gặp lại: *"cơ chế có sẵn, đường dẫn
tới nó đứt"*.

Bộ này cũng canh chính **bộ đo**: ba phép lọc của `tools/do_edit47.py` đều có thể trả về
một con số đẹp mà sai, và lần đầu nó đã trả về đúng như thế (một `SELECT` sai tên cột, bị
`except` nuốt, cho 0 lượt trên cả 39 dự án).
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

from eide import Config, Core
from eide.llm import ScriptedGateway
from eide.loop import Agent

GOC = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC / "tools"))

EX = {"summary": "ghi", "why": "w", "sources": [], "diff_prev": "đầu", "next": "—",
      "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    def _tao():
        a = Agent(Config.for_project(du_an), llm=ScriptedGateway([]),
                  project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _undo(a):
    return [e.data for e in a.ledger.read() if e.kind == "undo"]


def _req(a, ma="FR-01", text="≥ 1 MB/s"):
    a.store.apply(artefact_id=ma, type="req", op="update" if a.store.get(ma) else "create",
                  author="agent:run-1", canonical={"text": text}, explain=EX)


def _sua(core, ma="FR-01", text="≥ 5 MB/s"):
    core.console_act({"kind": "edit", "target": {"type": "req", "id": ma},
                      "data": {"base_version": "v1", "fields": {"text": text}},
                      "origin": {"surface": "requirements"}})


# ====================================================== sổ cái ghi kết quả hoàn tác
def test_so_cai_GHI_KET_QUA_hoan_tac_kem_TANG(phien, du_an):
    a, core, out = phien()
    _req(a)
    _sua(core)
    cs = [c for c in a.history.log.all() if c.by_human][-1]

    core.console_act({"kind": "undo", "target": {"type": "changeset", "id": cs.id},
                      "data": {"mode": "revert"}, "origin": {"surface": "history"}})

    ds = _undo(a)
    assert len(ds) == 1, ds
    assert ds[0]["tang"] == "changeset" and ds[0]["target"] == cs.id
    assert ds[0]["ok"] is True and ds[0]["message_vi"]
    assert ds[0]["so_changeset_lui"] >= 1


def test_LUI_THAT_BAI_cung_phai_co_trong_so(phien, du_an):
    """Một lần lùi thất bại trông y hệt một lần không ai bấm, nếu chỉ đọc `history.update`.
    Đây là chỗ phân biệt được hai thứ ấy."""
    a, core, out = phien()
    core.console_act({"kind": "undo",
                      "target": {"type": "changeset", "id": "cs-9999"},
                      "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    ds = _undo(a)
    assert len(ds) == 1 and ds[0]["ok"] is False
    assert "cs-9999" in ds[0]["message_vi"]


def test_THIEU_TARGET_cung_ghi(phien):
    a, core, out = phien()
    core.console_act({"kind": "undo", "data": {"mode": "revert"},
                      "origin": {"surface": "history"}})
    assert _undo(a) and _undo(a)[0]["ok"] is False


def test_danh_sach_TANG_cua_bo_do_khop_bang_trong_ma():
    """Bản đầu của bộ đo kể năm tầng, trong đó có `artefact` — một tầng **không tồn tại**
    trong `_nguoi_hoan_tac`. Một tầng bịa ra thì bảng "tầng chưa có bản ghi" không bao giờ
    hết, và nó đổ lỗi cho sản phẩm vì một thứ sản phẩm không có.

    "Năm tầng" của DEV-365 đếm cả mốc ngầm — nó là `checkpoint`, không có `target.type`
    riêng; người về nó bằng chính `snapshot` hoặc `session`.
    """
    import inspect

    import do_edit47 as do
    from eide.loop import Agent

    bang = inspect.getdoc(Agent._nguoi_hoan_tac) or ""
    for t in do.TANG:
        assert f"`{t}:" in bang, f"{t} không có trong bảng của _nguoi_hoan_tac"
    assert "artefact" not in do.TANG


def test_NAM_TANG_deu_vao_so_dung_ten_tang(phien, du_an):
    """Năm tầng lùi của DEV-365 phải phân biệt được TRONG SỔ, không chỉ trong mã — chỉ số
    thứ tư của §7 đo "theo tầng", nên tầng phải là một trường đọc được."""
    a, core, out = phien()
    _req(a)
    _sua(core)
    snap = a.history.tao_snapshot(ten="mốc một", boi="human")
    _sua(core, text="≥ 9 MB/s")

    for tang, ma in (("snapshot", snap.id), ("session", "es-1"), ("run", "run-001"),
                     ("changeset", "cs-0001")):
        core.console_act({"kind": "undo", "target": {"type": tang, "id": ma},
                          "data": {"mode": "revert"}, "origin": {"surface": "history"}})

    thay = [d["tang"] for d in _undo(a)]
    assert thay == ["snapshot", "session", "run", "changeset"], thay


# ====================================================== bộ đo của §7
def test_bo_do_doc_duoc_HAI_SO_KHAC_NHAU_y_chi_va_ket_qua(phien, du_an):
    """Số lần người bấm và số lần có ghi kết quả là HAI con số. Hiệu của chúng chính là
    phần không đo được — sổ cái cũ (trước gói này) rơi hết vào đó."""
    import do_edit47 as do

    a, core, out = phien()
    _req(a)
    _sua(core)
    cs = [c for c in a.history.log.all() if c.by_human][-1]
    core.console_act({"kind": "undo", "target": {"type": "changeset", "id": cs.id},
                      "data": {"mode": "revert"}, "origin": {"surface": "history"}})

    so = do._doc_so(a.config.paths.ledger)
    u = do._hoan_tac_theo_tang(so)
    assert u["so_lan_nguoi_bam"] == 1 and u["so_lan_co_ghi_ket_qua"] == 1
    assert u["theo_tang"]["changeset"] == {"ok": 1, "hong": 0}

    # Sổ KHÔNG có sự kiện `undo` (phiên cũ) thì ý chí vẫn đếm được, kết quả thì KHÔNG —
    # và bộ đo phải nói ra điều đó chứ không viết 0/0.
    cu = [e for e in so if e.get("kind") != "undo"]
    u2 = do._hoan_tac_theo_tang(cu)
    assert u2["so_lan_nguoi_bam"] == 1 and u2["so_lan_co_ghi_ket_qua"] == 0
    assert u2["theo_tang"] == {}


def test_bo_do_KHONG_NUOT_LOI_khi_kho_doc_khong_duoc(tmp_path):
    """Lần đầu, hàm tra loại hiện vật viết sai tên cột (`artefact_id`; cột thật là `id`) và
    bọc trong `except sqlite3.Error: return {}`. Mọi dự án trả về rỗng, nên chỉ số 2 ra
    **0 lượt** trên cả 39 dự án — một con số trông hoàn toàn hợp lý.

    Nay lỗi phải NỔ. Một phép lọc sai trả về rỗng thì rẻ; trả về số đẹp thì tốn nhiều lượt.
    """
    import sqlite3

    import do_edit47 as do

    vo = tmp_path / "vo.sqlite"
    vo.write_bytes(b"day khong phai sqlite")
    with pytest.raises(sqlite3.Error):
        do._loai_cua_hien_vat(vo)


def test_chi_so_2_TACH_bao_cao_dai_cua_may_khoi_loi_nguoi_go():
    """217 trong 249 câu khớp từ khoá trong kho mẫu là báo cáo của một tác tử ĐÓNG VAI
    sinh viên: dài vài nghìn ký tự, có bảng, có mã, và tình cờ chứa chữ "sửa". Đếm chúng
    rồi gọi là "người gõ lời" thì con số vẫn nghe hợp lý."""
    import do_edit47 as do

    so = [
        _say("Sửa FR-01 thành 5 MB/s giúp tôi"),
        _say("Đổi ADR-02 đi"),
        _say("sửa lại cái ngưỡng ấy đi"),
        _say("Mình đã đọc xong. " + "x" * 400 + " và đã sửa FR-01."),
        _say("biên dịch giúp tôi"),                      # không từ khoá
    ]
    g = do._goi_loi_le_ra_bam_duoc(so, {"FR-01": "req", "ADR-02": "adr"}, {"req"})
    assert [x["chu"][:12] for x in g["bam_duoc"]] == ["Sửa FR-01 th"]
    assert len(g["chua_bam_duoc"]) == 1      # adr có mã nhưng chưa sửa được
    assert len(g["khong_ro"]) == 1           # "cái ngưỡng ấy" — không chỉ rõ hiện vật
    assert len(g["bao_cao_dai"]) == 1


def test_chi_so_3_dem_rieng_lan_KHONG_BAO_GIO_cham_ha_nguon():
    """Con số đáng đọc nhất của chỉ số 3 không phải trung vị, mà là số lần hạ nguồn bị
    đánh STALE rồi **không ai cập nhật**. Trộn nó vào trung vị thì nó biến mất."""
    import do_edit47 as do

    so = [
        _cs("cs-1", "human", ts="2026-10-01T10:00:00+00:00", stale=["build:firmware"]),
        # Người CHẠM LẠI chính hiện vật ấy sau 5 phút. Đây KHÔNG phải "hạ nguồn được cập
        # nhật": việc dựng lại bản dưới là việc của tác tử. Tính nó thì con số đẹp đi một
        # nửa mà nói về chuyện khác.
        _cs("cs-1b", "human", ts="2026-10-01T10:05:00+00:00", touches=["build:firmware"]),
        _cs("cs-2", "agent:run-9", ts="2026-10-01T10:30:00+00:00",
            touches=["build:firmware"]),
        _cs("cs-3", "human", ts="2026-10-01T11:00:00+00:00", stale=["sim_result:x"]),
        # Và một lần hạ nguồn mà CHỈ người chạm lại — vẫn phải vào rổ "không bao giờ".
        _cs("cs-4", "human", ts="2026-10-01T12:00:00+00:00", stale=["doc:ds"]),
        _cs("cs-5", "human", ts="2026-10-01T12:10:00+00:00", touches=["doc:ds"]),
    ]
    h = do._sua_den_ha_nguon(so)
    assert h["so_lan_co_so"] == 1, h
    assert h["trung_vi_giay"] == 1800.0, "phải đo tới changeset của TÁC TỬ, không phải 300 s"
    assert [x["cs"] for x in h["khong_bao_gio_cham"]] == ["cs-3", "cs-4"]


def test_chi_so_1_KHONG_dem_lan_hai():
    """Chỉ số 1 gọi lại `dem_sua_duoc.py`. Hai cách đếm cùng một thứ sẽ lệch, và lúc lệch
    thì không ai biết cái nào đúng."""
    nguon = (GOC / "tools/do_edit47.py").read_text("utf-8")
    assert "import dem_sua_duoc as dsd" in nguon
    assert 'dsd.main(["--du-lieu", str(goc), "--json"])' in nguon


def test_bo_do_chay_duoc_tren_KHO_RONG(tmp_path):
    """Kho rỗng phải ra 0, không ra lỗi — và `None` ở chỗ trung vị, không phải `0` (một
    trung vị 0 giây đọc như "hạ nguồn cập nhật tức thì")."""
    import do_edit47 as do

    kq = do.do(tmp_path)
    assert kq["so_du_an"] == 0
    assert kq["chi_so_3_ha_nguon"]["trung_vi_giay"] is None
    assert kq["chi_so_4_hoan_tac"]["tang_chua_thay"] == list(do.TANG)


def _say(chu: str) -> dict:
    return {"kind": "human_act", "ts": "2026-10-01T10:00:00+00:00",
            "data": {"kind": "say", "text": chu}}


def _cs(ma: str, tac_gia: str, *, ts: str, stale=None, touches=None) -> dict:
    return {"kind": "changeset", "ts": ts,
            "data": {"id": ma, "author": tac_gia, "stale": stale or [],
                     "touches": touches or []}}
