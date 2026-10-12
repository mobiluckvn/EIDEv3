# -*- coding: utf-8 -*-
"""Năm tầng lùi — EIDE-EDIT-47 §DEV-365.

Chẩn đoán của tài liệu (§1 dòng 3 và 4): `history.py` đã có `tao_snapshot`,
`khoi_phuc_snapshot`, `tao_nhanh`, `chuyen_nhanh`, `gop_nhanh`,
`se_mat_gi_khi_khoi_phuc`, `hoan_tac_luot` từ bước G5 — và **không nút nào gửi
`snapshot`/`branch`, không đường nào gọi `khoi_phuc_snapshot`, `gop_nhanh` chỉ chạy được
khi tác tử tự gọi công cụ**. `grep "kind: .snapshot"` trong `Views/` = 0.

Nên bộ ca này đo đúng một thứ: **ý chí của người đi tới cơ chế ấy được chưa**. Không đo
lại bản thân cơ chế (đã có `test_snapshot.py`, `test_gop_nhanh.py`, CX10/CX11) — đo
ĐƯỜNG DẪN tới nó, qua đúng cửa `console.act` mà giao diện dùng.

Bài học của dự án, README §8: *kiểm thứ làm việc không thay được kiểm đường dẫn tới nó.*
"""

from __future__ import annotations

import pytest

from eide import Config, Core
from eide.llm import ScriptedGateway
from eide.loop import Agent

EX = {"summary": "ghi thử", "why": "dựng dữ liệu cho ca đo", "sources": [],
      "diff_prev": "bản đầu", "next": "—", "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    """Lõi thật + cửa `console.act` thật. Mô hình không bị gọi: không ý chí nào ở đây cần nó."""
    a = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    out: list = []
    core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                on_query=a.hoi_chi_doc)
    return a, core, out


def _ghi(a, aid: str, text: str, *, run_id: str = "run-cu") -> str:
    """Một hiện vật do TÁC TỬ ghi — để người có cái mà sửa, mà lùi."""
    cu = a.store.get(aid)
    cs = a.history.ghi_kho(author=f"agent:{run_id}", artefact_id=aid, type="req",
                           op="update" if cu else "create", canonical={"text": text},
                           explain=EX, run_id=run_id)
    return cs.id


def _sua(a, aid: str, text: str, *, session: str | None = None, note: str = "vì tôi muốn vậy"):
    """Đúng thông điệp mà `OSuaDuoc`/`FormEditor` gửi khi người bấm Lưu."""
    d: dict = {"base_version": f"v{a.store.get(aid)['version']}",
               "fields": {"text": text}, "summary": f"sửa {aid}"}
    if session:
        d["session_id"] = session
    return {"kind": "edit", "target": {"type": "req", "id": aid}, "data": d,
            "origin": {"surface": "requirements", "block": "A2.1", "row": aid},
            "note": note}


def _moc(a) -> list[str]:
    return [c.id for c in a.history.log.all()
            if any(f.get("kind") == "checkpoint" for f in c.forward)]


def _loi(out) -> str:
    return "\n".join(c.params.get("text", "") for c in out
                     if c.method == "console.post" and c.params.get("role") == "agent")


def _canh_bao(out) -> list[str]:
    return [c.params.get("text", "") for c in out if c.method == "notice"]


def _lich_su(out) -> list[dict]:
    return [c.params for c in out if c.method == "history.update"]


# =============================================================== (1) về bản ưng ý
def test_undo_target_snapshot_ve_ban_ung_y_va_KHONG_xoa_ban_do(phien):
    """Tầng 4 — "Về bản…". `khoi_phuc_snapshot` có từ G5; trước gói này không ai gọi nó.

    Ba điều phải đúng cùng lúc: kho về đúng trạng thái cũ; **bản ưng ý vẫn còn** (khôi phục
    không ghi đè lịch sử, nó thêm một changeset mới); và bản đang bỏ lại được giữ lại thành
    một bản có tên, vì §E6.3 nói thẻ G-HIST phải đưa ra lựa chọn ấy.
    """
    a, core, out = phien
    _ghi(a, "FR-01", "≥ 1 MB/s")
    s = a.history.tao_snapshot(ten="trước khi thử hướng khác", boi="human")
    _ghi(a, "FR-01", "≥ 9 MB/s")
    _ghi(a, "FR-02", "sinh ra SAU bản ưng ý")
    truoc = len(a.history.log.all())

    core.console_act({
        "kind": "undo", "target": {"type": "snapshot", "id": s.id},
        "data": {"mode": "restore_branch", "giu_ban_hien_tai": "hướng đã thử"},
        "origin": {"surface": "history"}})

    assert a.store.get("FR-01")["canonical"]["text"] == "≥ 1 MB/s"
    sau_moc = a.store.get("FR-02")
    assert sau_moc is None or not sau_moc["canonical"], \
        "hiện vật sinh sau bản ưng ý phải được gỡ, không để lại lẫn vào"

    assert a.history.snapshots.get(s.id) is not None, "khôi phục KHÔNG được xoá bản ưng ý"
    assert len(a.history.log.all()) > truoc, "khôi phục là một changeset MỚI, không phải xoá"
    assert a.history.snapshots.theo_ten("hướng đã thử") is not None, \
        "bản đang bỏ lại phải được giữ — đó là lựa chọn §E6.3 đòi thẻ G-HIST đưa ra"

    # Về một trạng thái nhất quán thì KHÔNG đánh dấu hạ nguồn lỗi thời: băng cảnh báo nổ ở
    # chỗ không có gì phải làm sẽ dạy người dùng bỏ qua nó.
    assert "FR-01" not in [x["id"] for x in a.store.list(stale_only=True, limit=50)]
    assert s.name in _loi(out)


def test_undo_snapshot_khong_co_thi_noi_that_chu_khong_im(phien):
    a, core, out = phien
    core.console_act({"kind": "undo", "target": {"type": "snapshot", "id": "snap-404"},
                      "data": {"mode": "restore_branch"}, "origin": {"surface": "history"}})
    assert "snap-404" in _loi(out)


# =============================================================== (2) lùi cả lượt
def test_undo_target_run_lui_ca_luot_va_KE_phan_khong_lui_duoc(phien):
    """Tầng 3 — "Lùi cả lượt". CX11: phần đã tác động ra ngoài máy vẫn còn, và người phải biết."""
    a, core, out = phien
    _ghi(a, "FR-01", "bản gốc", run_id="run-truoc")
    _ghi(a, "FR-01", "bản của lượt xấu", run_id="run-xau")
    _ghi(a, "FR-03", "cũng của lượt xấu", run_id="run-xau")
    khong_lui = a.history.ghi_khong_hoan_tac(
        author="agent:run-xau", what="target.flash", run_id="run-xau",
        reason_vi="đã nạp vào chip", explain=EX)

    core.console_act({"kind": "undo", "target": {"type": "run", "id": "run-xau"},
                      "data": {"mode": "revert"}, "origin": {"surface": "console"}})

    assert a.store.get("FR-01")["canonical"]["text"] == "bản gốc"
    canh = " ".join(_canh_bao(out))
    assert "KHÔNG hoàn tác được" in canh and khong_lui.id in canh
    assert "đã nạp vào chip" in canh, "phải nói LÝ DO, không chỉ làm mờ cái nút"
    # Mô hình cũng phải biết, để nó đừng làm lại thứ vừa bị lùi.
    assert any("vừa hoàn tác" in str(m.get("text", "")) for m in a.messages)


# =============================================== (3) mốc lùi trước lần sửa đầu (I10)
def test_lan_sua_dau_cua_nguoi_sinh_DUNG_MOT_moc_lui(phien):
    """I10 — đối xứng với luật của tác tử: một mốc mỗi lượt, không phải mỗi lần lưu.

    Người sửa bốn ô trong một biểu mẫu muốn quay về *trước khi tôi bắt đầu sửa*, không phải
    về giữa bốn lần ấy. Chỗ gom là MÃ PHIÊN SỬA — xem `_moc_lui_cho_nguoi`.
    """
    a, core, out = phien
    _ghi(a, "FR-01", "bản gốc")
    n0 = len(_moc(a))

    core.console_act(_sua(a, "FR-01", "lần sửa thứ nhất", session="es-1"))
    assert len(_moc(a)) == n0 + 1, "lần sửa đầu của người phải có một mốc lùi"
    moc1 = _moc(a)[-1]

    core.console_act(_sua(a, "FR-01", "lần sửa thứ hai", session="es-1"))
    assert len(_moc(a)) == n0 + 1, "cùng một lượt ngồi sửa thì KHÔNG đẻ thêm mốc"

    core.console_act(_sua(a, "FR-01", "một lần ngồi sửa khác", session="es-2"))
    assert len(_moc(a)) == n0 + 2, "lượt sửa mới thì lại phải có mốc riêng"

    cs = a.history.log.get(moc1)
    assert "trước khi anh sửa" in cs.explain["summary"]
    assert cs.author == "eide", "mốc là của hệ thống, không đứng tên người hay tác tử"


def test_sua_khong_co_ma_phien_van_co_moc(phien):
    """Bốn bảng cũ (A2.1, A5.8c, A8, A14) chưa gửi `session_id` — chúng vẫn phải có đường lui."""
    a, core, out = phien
    _ghi(a, "FR-01", "bản gốc")
    n0 = len(_moc(a))
    core.console_act(_sua(a, "FR-01", "sửa không kèm mã phiên"))
    assert len(_moc(a)) == n0 + 1


# ====================================================== (3b) lùi cả một lượt ngồi sửa
def test_undo_target_session_lui_het_phien_sua_va_KHONG_dung_phien_khac(phien):
    """Tầng 2 — thanh "Đã ghi … · Hoàn tác" sau khi lưu lùi *cái người vừa làm*.

    Không phải changeset cuối cùng: một lần ngồi sửa biểu mẫu là nhiều lần lưu.
    """
    a, core, out = phien
    _ghi(a, "FR-01", "gốc một")
    _ghi(a, "FR-02", "gốc hai")
    core.console_act(_sua(a, "FR-01", "sửa trong phiên 7", session="es-7"))
    core.console_act(_sua(a, "FR-01", "sửa lần nữa trong phiên 7", session="es-7"))
    core.console_act(_sua(a, "FR-02", "sửa trong phiên 8", session="es-8"))

    assert len(a.history.changeset_cua_phien_sua("es-7")) == 2

    core.console_act({"kind": "undo", "target": {"type": "session", "id": "es-7"},
                      "data": {"mode": "revert"}, "origin": {"surface": "requirements"}})

    assert a.store.get("FR-01")["canonical"]["text"] == "gốc một"
    assert a.store.get("FR-02")["canonical"]["text"] == "sửa trong phiên 8", \
        "lùi một lượt sửa không được chạm vào lượt sửa khác"
    assert a.history.changeset_cua_phien_sua("es-7") == [], "đã lùi thì không lùi lại lần nữa"


# =============================================================== (4) gộp nhánh
def test_branch_action_merge_xung_dot_thi_KHONG_ghi_de_va_ke_ra(phien, du_an):
    """Gộp đi được từ giao diện; xung đột thì huỷ phép gộp và nói ra, không để cây gộp dở."""
    a, core, out = phien
    if not a.history.git_san:
        pytest.skip("máy không dùng được git — phép gộp nhánh không đo được ở đây")

    goc = (du_an / "main.c").read_text("utf-8")

    def _ghi_tep(noi_dung: str, truoc: str):
        (du_an / "main.c").write_text(noi_dung, "utf-8")
        a.history.ghi_tep(author="human", paths=["main.c"], summary="sửa main.c",
                          explain=EX, noi_dung_truoc={"main.c": truoc})

    a.history.tao_nhanh("thu-nhanh")
    _ghi_tep("int main(void){return 1;}\n", goc)
    a.history.chuyen_nhanh("main")
    _ghi_tep("int main(void){return 2;}\n", goc)
    ban_cua_main = (du_an / "main.c").read_text("utf-8")

    out.clear()
    core.console_act({"kind": "branch", "data": {"action": "merge", "name": "thu-nhanh"},
                      "origin": {"surface": "history"}})

    assert (du_an / "main.c").read_text("utf-8") == ban_cua_main, \
        "xung đột thì huỷ hẳn phép gộp — không ghi đè, không để lại thẻ xung đột trong tệp"
    assert "UU" not in a.history.vcs._git("status", "--porcelain", check=False), \
        "không được để cây làm việc ở trạng thái gộp dở: người dùng không xin nó"
    canh = " ".join(_canh_bao(out))
    assert "main.c" in canh and "xung đột" in canh.lower()


def test_branch_thieu_ten_thi_khong_lam_gi(phien):
    a, core, out = phien
    core.console_act({"kind": "branch", "data": {"action": "create", "name": "  "},
                      "origin": {"surface": "history"}})
    assert "cần tên nhánh" in " ".join(_canh_bao(out))
    assert a.history.danh_sach_nhanh() in ([], ["main"]), "không tạo nhánh nào tên rỗng"


def test_branch_list_khong_can_ten(phien):
    a, core, out = phien
    core.console_act({"kind": "branch", "data": {"action": "list"},
                      "origin": {"surface": "history"}})
    assert "Các nhánh" in _loi(out)


# ======================================================= (5) xem trước: không đổi gì
def test_preview_restore_la_CHI_DOC_khong_tao_changeset_nao(phien):
    """Thẻ G-HIST phải liệt kê "sẽ mất gì" TRƯỚC khi hỏi — và phép xem trước ấy không đổi gì.

    Đếm trên ĐĨA, không đếm trên đối tượng trong bộ nhớ: câu cần trả lời là sổ changeset có
    dài thêm một dòng nào không.
    """
    a, core, out = phien
    _ghi(a, "FR-01", "bản gốc")
    s = a.history.tao_snapshot(ten="mốc đo", boi="human")
    _ghi(a, "FR-02", "sinh sau mốc")

    so = a.config.paths.changesets
    truoc_cs = so.read_text("utf-8")
    truoc_so_cai = a.ledger.seq
    truoc_out = len(out)

    r = core.dispatch("history.preview_restore", {"snapshot_id": s.id})

    assert r["ok"] and r["se_mat_vi"], "phải nói sẽ mất gì, không trả về một dict rỗng"
    assert any("FR-02" in dong for dong in r["se_mat_vi"])
    assert r["co_sua_cua_nguoi"] is False
    assert so.read_text("utf-8") == truoc_cs, "xem trước mà ghi changeset là xem trước nói dối"
    assert a.ledger.seq == truoc_so_cai, "máy–máy, chỉ đọc: không một dòng sổ cái nào"
    assert len(out) == truoc_out, "không phát lệnh giao diện nào, không dòng transcript nào"


def test_preview_restore_thieu_tham_so_va_ban_khong_co(phien):
    a, core, out = phien
    assert core.dispatch("history.preview_restore", {})["ok"] is False
    assert core.dispatch("history.preview_restore", {"snapshot_id": "snap-404"})["ok"] is False


def test_loi_khong_kem_bo_tra_loi_thi_BAO_LOI_chu_khong_im_lang(du_an):
    """Lõi chạy ở chế độ `--go` không có bộ trả lời. Im lặng trả rỗng thì thẻ G-HIST mất
    phần hậu quả mà không ai biết."""
    from eide.errors import EideError

    a = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    core = Core(a.ledger, a.ids, a.turn)
    with pytest.raises(EideError):
        core.dispatch("history.preview_restore", {"snapshot_id": "snap-1"})


# ======================================= (6) đi đúng đường người đi (§0 mục 6)
def test_DUONG_NGUOI_DI_sua_o_tab_roi_hoan_tac_bang_dung_thu_loi_dua_ra(phien):
    """Người bấm ở tab → HumanAct → lõi → changeset → tác tử thấy → lùi lại được.

    Ca này đi hết đường, qua đúng cửa `console.act`, và kiểm cả **thứ lõi gửi cho giao diện
    để vẽ cái nút** — vì một cơ chế có sẵn mà đường lên giao diện đứt thì vẫn là không có.
    """
    a, core, out = phien
    _ghi(a, "FR-01", "≥ 1 MB/s")
    out.clear()

    core.console_act(_sua(a, "FR-01", "≥ 5 MB/s", session="es-7", note="phim 4K nên cần hơn"))

    # 1 · một changeset của NGƯỜI, mang theo lý do của họ
    cua_nguoi = [c for c in a.history.log.all() if c.by_human]
    assert len(cua_nguoi) == 1
    cs = cua_nguoi[0]
    assert cs.note == "phim 4K nên cần hơn"
    assert cs.explain["sources"][0]["session"] == "es-7", \
        "mã phiên sửa phải nằm trong xuất xứ — nó là chỗ gom để lùi cả lượt sửa"

    # 2 · tác tử biết, bằng EIDE.md §Người vừa sửa (nó đọc mục này mỗi lượt)
    md = a.config.paths.eide_md.read_text("utf-8")
    assert "FR-01" in md and "phim 4K nên cần hơn" in md

    # 3 · lõi KHAI cho giao diện biết cái gì vừa được ghi, để thanh "Hoàn tác" có target thật
    vg = [p["vua_ghi"] for p in _lich_su(out) if p.get("vua_ghi")]
    assert vg, "không có `vua_ghi` thì giao diện phải tự suy ra — và nó suy sai"
    assert vg[0]["changeset"] == cs.id
    assert vg[0]["session"] == "es-7" and vg[0]["hoan_tac_duoc"] is True

    # 4 · tab A11 hiện changeset ấy
    a11 = [c.params["model"] for c in out
           if c.method == "surface.set" and c.params["surface"] == "history"][-1]
    dong = [b for b in a11["blocks"] if b["code"] == "A11.1"][0]
    assert any(x["id"] == cs.id and x["cua_nguoi"] for x in dong["items"])

    # 5 · bấm "Hoàn tác" trên thanh ấy, với ĐÚNG target lõi vừa đưa ra
    core.console_act({"kind": "undo",
                      "target": {"type": "session", "id": vg[0]["session"]},
                      "data": {"mode": "revert"}, "origin": {"surface": "requirements"}})
    assert a.store.get("FR-01")["canonical"]["text"] == "≥ 1 MB/s"


# =============================== nút "Lùi cả lượt" chỉ sáng khi lượt có thay đổi
def test_so_thay_doi_cua_luot_do_LOI_dem_va_bo_moc_ngam_ra(phien):
    """Giao diện chỉ thấy 40 changeset gần nhất, nên nó không đếm được. Và mốc ngầm không
    phải một thay đổi — đếm nó vào thì nút sáng ở lượt không đổi gì."""
    a, core, out = phien
    _ghi(a, "FR-01", "bản gốc")

    core.console_act({"kind": "undo", "target": {"type": "changeset", "id": "cs-404"},
                      "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    assert a.last_report["so_thay_doi"] == 0
    r = [c.params for c in out if c.method == "run.update"][-1]
    assert r["so_thay_doi"] == 0 and "Lùi cả lượt" not in r["buttons"]

    out.clear()
    core.console_act(_sua(a, "FR-01", "có sửa thật", session="es-9"))
    assert a.last_report["so_thay_doi"] == 1, \
        "một lần sửa + một mốc ngầm = MỘT thay đổi, không phải hai"
    r = [c.params for c in out if c.method == "run.update"][-1]
    assert "Lùi cả lượt" in r["buttons"] and "Ghi bản ưng ý" in r["buttons"]


def test_ghi_ban_ung_y_tu_giao_dien_khong_di_qua_mo_hinh(phien):
    """§E6.2 — người đặt tên thì MÃ ghi. Nút trên thanh trạng thái gửi đúng `kind=snapshot`."""
    a, core, out = phien
    _ghi(a, "FR-01", "x")
    core.console_act({"kind": "snapshot", "data": {"name": "xong phần nạp", "note": "đo trên bo"},
                      "origin": {"surface": "console"}})
    s = a.history.snapshots.theo_ten("xong phần nạp")
    assert s is not None and s.created_by == "human"
    assert a.llm._i == 0, "không một lời gọi mô hình nào: tên đã có, nội dung do kho quyết"
    # Danh sách bản ưng ý và nhánh đi kèm cho menu trên thanh trạng thái.
    p = _lich_su(out)[-1]
    assert any(x["id"] == s.id for x in p["snapshots"])
    assert p["nhanh"]["hien_tai"] and isinstance(p["nhanh"]["danh_sach"], list)

    # Và ô "Bản ưng ý" trên thanh trạng thái nói đúng tên bản vừa ghi.
    tt = [c.params["value"] for c in out
          if c.method == "ui.set" and c.params.get("key") == "status_bar"][-1]
    assert tt["snapshot"] == "xong phần nạp", (
        "ô ấy đọc `store.list('snapshot')` — kho hiện vật không giữ bản ưng ý, nên nó "
        f"trống suốt từ đầu: {tt['snapshot']!r}")
