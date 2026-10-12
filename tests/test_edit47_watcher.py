# -*- coding: utf-8 -*-
"""Bắt sửa từ BÊN NGOÀI EIDE — EIDE-EDIT-47 §DEV-369.

Luật nền số 3 của README: *"mọi thay đổi gỡ lại được, **kể cả do người gõ**"*. Câu ấy đúng
với thứ sửa TRONG app, và sai với cách kỹ sư nhúng làm thật — mở `main.c` bằng VS Code,
sửa, lưu. Lần sửa ấy không có changeset, không đánh dấu hạ nguồn, không phá soft-lock, và
tác tử không biết gì cho tới khi nó tình cờ đọc lại tệp.

Tài liệu nói *"`changeset.kind="external"` đã có từ G5, không ai tạo nó"*. Mở mã ra thì
chữ ấy đã có người dùng, với một nghĩa KHÁC: `forward.kind="external"` là *tác động ra
ngoài máy* (nạp bo, cài công cụ — §E5.3). Nên nhãn "sửa ngoài app" của gói này nhận ra
bằng `explain.sources`, và ca `test_NAP_BO_khong_dinh_nhan_ngoai_EIDE` giữ hai nghĩa ấy
không lẫn vào nhau.

Bộ này chạy bằng đường quét `mtime` (không cần `watchdog`), và gọi thẳng `quet_mot_lan()`
thay vì ngủ chờ thread — một bộ đo phải ngủ 1,5 giây mỗi phép kiểm là một bộ đo không ai
chạy lại.
"""

from __future__ import annotations

import time

import pytest

from eide import Config, Core
from eide import watcher as wt
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

EX = {"summary": "ghi", "why": "w", "sources": [], "diff_prev": "đầu", "next": "—",
      "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    def _tao(bat: bool = True):
        cfg = Config.for_project(du_an)
        cfg.features.watcher = bat
        a = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _chin_ngay(w):
    """Quét và coi như đã qua thời gian gộp — không ngủ thật."""
    w.quet_mot_lan()
    for p in list(w._cho):
        w._cho[p] -= wt.GIAY_GOM + 0.1
    return w.quet_mot_lan()


def _cs_ngoai(a):
    return [c for c in a.history.log.all() if a.history.tom_tat(c)["ngoai_eide"]]


# =============================================================== phần phát hiện
def test_bo_qua_thu_MAY_SINH_RA():
    """Luật thứ nhất: thứ máy sinh ra. Theo dõi `build/` là coi mỗi lần biên dịch là một
    lần người sửa mã."""
    from pathlib import Path

    assert wt.dang_theo_doi(Path("src/main.c"))
    assert wt.dang_theo_doi(Path("Makefile"))
    for xau in ("build/out.elf", "dist/app.bin", "src/__pycache__/x.pyc",
                "node_modules/a/b.js", "target/debug/x", "out/x.hex"):
        assert not wt.dang_theo_doi(Path(xau)), xau


def test_bo_qua_moi_thanh_phan_BAT_DAU_BANG_DAU_CHAM():
    """Luật thứ hai, tách khỏi luật trên vì nó bảo vệ thứ khác: `.eide/` là tiếng của
    chính lõi, và `.env` là **khoá API** — theo dõi nó là chép khoá vào blob changeset."""
    from pathlib import Path

    for xau in (".env", ".eide/store.sqlite", ".git/HEAD", ".venv/bin/python",
                ".vscode/settings.json", "src/.ghi-chu-rieng.md", ".DS_Store",
                ".pytest_cache/x", "a/b/.cache/c"):
        assert not wt.dang_theo_doi(Path(xau)), xau


def test_KHOA_API_khong_vao_changeset(phien, du_an):
    """Ràng buộc bảo mật của dự án: khoá chỉ ở `.env`. Một changeset "người sửa .env" là
    nguyên văn khoá nằm trong blob của kho lịch sử — tức khoá đã rời khỏi `.env`."""
    a, core, out = phien()
    a._watcher_emit = out.append
    (du_an / ".env").write_text("GEMINI_API_KEY=AIza-bi-mat\n", "utf-8")

    w = wt.Watcher(du_an, khi_doi=lambda _: None)
    w._dau = {}
    assert ".env" not in _chin_ngay(w), "watcher không được báo .env"

    a._tep_doi_ngoai_eide([".env"])         # cả khi bị gọi thẳng cũng không được ghi
    assert not _cs_ngoai(a)
    for cs in a.history.log.all():
        assert "AIza-bi-mat" not in str(cs.explain), cs.id


def test_theo_doi_bo_qua_THU_MUC_CUA_CHINH_MINH(du_an):
    """`.eide/` là chỗ lõi ghi liên tục — theo dõi nó là tự nghe tiếng của mình và gọi đó
    là người dùng sửa."""
    w = wt.Watcher(du_an, khi_doi=lambda _: None)
    w._dau = w._chup()
    (du_an / ".eide").mkdir(exist_ok=True)
    (du_an / ".eide" / "rac.jsonl").write_text("x\n", "utf-8")
    assert _chin_ngay(w) == []


def test_nhi_phan_va_tep_qua_lon_bi_bo_qua(du_an):
    """Hai dấu hiệu nhị phân, và chúng KHÔNG trùng nhau — nên phải có một tệp cho mỗi
    dấu, không thì tháo một dấu mà bộ kiểm vẫn xanh:

    * `rac.dat` hợp lệ UTF-8 **nhưng có byte 0** — chỉ phép dò byte 0 bắt được;
    * `utf16.txt` không có byte 0 ở 4096 byte đầu **nhưng không giải mã được** — chỉ phép
      `decode` bắt được.
    """
    (du_an / "anh.png").write_bytes(b"\x89PNG\x00\x01\x02")
    (du_an / "rac.dat").write_bytes(b"chu thuong\x00chu thuong")
    (du_an / "utf16.txt").write_bytes(b"\xff\xfe\xc0\xc1 van ban khong giai ma duoc")
    (du_an / "to.bin").write_bytes(b"a" * (wt.TRAN_BYTE + 10))

    assert wt.la_nhi_phan(du_an / "rac.dat"), "byte 0 là nhị phân dù giải mã được"
    assert wt.la_nhi_phan(du_an / "utf16.txt"), "không giải mã được là nhị phân"
    for ten in ("anh.png", "rac.dat", "utf16.txt", "to.bin"):
        assert wt.noi_dung_doc_duoc(du_an / ten) is None, ten
    assert wt.noi_dung_doc_duoc(du_an / "main.c") is not None


def test_GOM_su_kien_mot_lan_luu_khong_thanh_ba_lan(du_an):
    """Một lần Cmd-S của trình soạn hiện đại có thể là ba sự kiện tệp (ghi tạm · đổi tên ·
    chmod). Ba changeset cho một lần lưu thì tab Lịch sử thành thứ không ai đọc."""
    w = wt.Watcher(du_an, khi_doi=lambda _: None)
    w._dau = w._chup()
    (du_an / "main.c").write_text("lần 1\n", "utf-8")
    assert w.quet_mot_lan() == [], "chưa qua thời gian gộp thì chưa chín"
    (du_an / "main.c").write_text("lần 2\n", "utf-8")
    (du_an / "main.c").write_text("lần 3\n", "utf-8")
    assert _chin_ngay(w) == ["main.c"], "ba lần ghi liên tiếp phải gom thành MỘT"


# =============================================================== thành changeset
def test_sua_ngoai_EIDE_thanh_changeset_HOAN_TAC_DUOC(phien, du_an):
    a, core, out = phien()
    a.bat_dau_theo_doi(out.append)
    a.dung_theo_doi()                      # không cần thread; gọi thẳng cho tất định
    a._tep_doi_ngoai_eide([])

    (du_an / "main.c").write_text("int main(void){return 42;}\n", "utf-8")
    a._watcher_emit = out.append
    a._tep_doi_ngoai_eide(["main.c"])

    cs = _cs_ngoai(a)
    assert len(cs) == 1, [c.explain.get("summary") for c in cs]
    assert cs[0].author == "human" and cs[0].reversible
    assert "bên ngoài EIDE" in cs[0].explain["summary"]

    kq = a.history.hoan_tac_changeset(cs[0].id, by="human")
    assert kq.ok, kq.message_vi
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 0;}\n"


def test_KHONG_doi_kieu_hien_vat_thanh_external(phien, du_an):
    """`ghi_tep(loai=...)` là **kiểu hiện vật** trong kho, không phải "loại changeset".

    Bản đầu của gói này truyền `loai="external"` theo đúng chữ trong tài liệu, và hậu quả
    là `main.c` đổi kiểu từ `code` thành `external` — mất chỗ trong đồ thị phụ thuộc, nên
    sửa nó không đánh dấu hạ nguồn lỗi thời nữa. Đúng cái mà gói này ra đời để vá.
    """
    a, core, out = phien()
    a._watcher_emit = out.append
    (du_an / "main.c").write_text("int main(void){return 7;}\n", "utf-8")
    a._tep_doi_ngoai_eide(["main.c"])

    hv = a.store.get("main.c")
    assert hv and hv["type"] == "code", hv
    assert _cs_ngoai(a)[0].touches[0].type == "code"


def test_NAP_BO_khong_dinh_nhan_ngoai_EIDE(phien, du_an):
    """Chữ "external" có HAI nghĩa trong mã này: `forward.kind="external"` là *tác động ra
    ngoài máy* (nạp bo, cài công cụ — §E5.3), còn nhãn của gói này là *sửa ngoài app*.

    Nhận nhãn bằng `explain.sources` mà không kẹp điều kiện thì một lần nạp bo cũng hiện
    là "anh sửa bên ngoài EIDE".
    """
    a, core, out = phien()
    cs = a.history.ghi_khong_hoan_tac(
        author="human", what="target:stm32f469", reason_vi="đã ghi vào flash của bo",
        explain={**EX, "sources": [{"kind": "external", "ref": "bo", "tier": "NGUOI"}]})
    assert not a.history.tom_tat(cs)["ngoai_eide"]


def test_EIDE_vua_ghi_thi_KHONG_sinh_changeset_trung(phien, du_an):
    """Thiếu phép lọc này thì mỗi lần tác tử ghi tệp đẻ ra HAI changeset, cái thứ hai
    mang tên người — và tab Lịch sử nói sai về ai làm gì."""
    a, core, out = phien()
    a.llm.script = ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "moi.c", "content": "int g(void){return 1;}\n", "explain": EX})]),
        Response(text="xong"),
    ]).script
    a.llm._i = 0
    core.console_act({"kind": "say", "text": "ghi giúp tôi"})
    truoc = len(a.history.log.all())

    a._watcher_emit = out.append
    a._tep_doi_ngoai_eide(["moi.c"])
    assert not _cs_ngoai(a)
    assert len(a.history.log.all()) == truoc


def test_DU_AN_KHONG_GIT_van_khong_sinh_changeset_trung(phien, du_an):
    """Hai phép lọc trông giống nhau nhưng bảo vệ hai thứ khác nhau, và ca kiểm phải tách
    được chúng ra — không thì tháo một cái vẫn xanh.

    * lọc theo **mốc git** (`_ban_eide_biet`) trả lời "tệp có đổi so với bản đã commit";
      dự án chưa `git init` thì nó mù;
    * lọc theo **dấu EIDE tự ghi** (`la_tieng_cua_eide`) là thứ duy nhất còn lại ở đó.

    Thiếu phép lọc thứ hai thì mọi dự án chưa `git init` đẻ ra một changeset "người sửa"
    cho đúng mỗi lần tác tử ghi tệp.
    """
    a, core, out = phien()
    a.history.git_san = False
    assert a._ban_eide_biet("moi.c") is None, "không git thì không có mốc nội dung"

    a.llm.script = ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "moi.c", "content": "int g(void){return 1;}\n", "explain": EX})]),
        Response(text="xong"),
    ]).script
    a.llm._i = 0
    core.console_act({"kind": "say", "text": "ghi giúp tôi"})

    a._watcher_emit = out.append
    a._tep_doi_ngoai_eide(["moi.c"])
    assert not _cs_ngoai(a)

    # Và lần sửa THẬT của người ở dự án không git chỉ được ghi MỘT lần: quét lại cùng một
    # tệp không đổi gì nữa thì không có gì để ghi. Thiếu dấu "đã ghi xong" thì ở đây mỗi
    # nhịp quét (2 giây một lần) đẻ thêm một changeset cho cùng một lần sửa.
    (du_an / "moi.c").write_text("int g(void){return 2;}\n", "utf-8")
    a._tep_doi_ngoai_eide(["moi.c"])
    assert len(_cs_ngoai(a)) == 1
    a._tep_doi_ngoai_eide(["moi.c"])
    a._tep_doi_ngoai_eide(["moi.c"])
    assert len(_cs_ngoai(a)) == 1, "một lần sửa, một changeset — quét lại không đẻ thêm"


def test_GIT_REVERT_HONG_thi_blob_van_keo_ban_cu_ve(phien, du_an):
    """`_lui_tep` ưu tiên `git revert`, nên khi git chạy ngon thì bản sao nội dung cũ
    không được dùng tới — và một changeset external **không giữ bản cũ** vẫn hoàn tác
    được, nghĩa là ca kiểm hoàn tác ở trên không đo được cái nó tưởng.

    Đây là ca đo đúng nó: cho `git revert` ngã (repo lạ, xung đột) rồi đòi bản cũ về.
    """
    from eide.vcs import GitKhongSan

    a, core, out = phien()
    a._watcher_emit = out.append
    goc = (du_an / "main.c").read_text("utf-8")
    (du_an / "main.c").write_text("int main(void){return 42;}\n", "utf-8")
    a._tep_doi_ngoai_eide(["main.c"])
    cs = _cs_ngoai(a)
    assert len(cs) == 1

    def revert_hong(*_a, **_k):
        raise GitKhongSan("giả lập: git revert xung đột")

    a.history.vcs.revert = revert_hong
    kq = a.history.hoan_tac_changeset(cs[0].id, by="human")
    assert kq.ok, kq.message_vi
    assert (du_an / "main.c").read_text("utf-8") == goc


def test_TAB_LICH_SU_co_nhan_ngoai_EIDE(phien, du_an):
    """Lõi gắn nhãn mà app không đọc thì nhãn ấy không tồn tại với người dùng — lỗi lặp
    lại nhiều nhất của dự án này là *"cơ chế có sẵn, đường dẫn tới nó đứt"*.
    """
    from pathlib import Path

    from eide import surfaces

    a, core, out = phien()
    a._watcher_emit = out.append
    (du_an / "main.c").write_text("sửa ngoài\n", "utf-8")
    a._tep_doi_ngoai_eide(["main.c"])

    # Đường thật: lệnh `history.update` là thứ app nhận ngay khi watcher bắt được.
    gui = [c.params["changesets"] for c in out if c.method == "history.update"]
    assert gui and any(x["ngoai_eide"] for x in gui[-1]), gui

    # Và một lần vẽ lại tab A11 sau đó cũng phải còn nhãn.
    from eide.store import inventory

    inv = inventory.build(a.store, ledger=a.ledger, project_name="du-an-thu")
    mat = surfaces.history(a.store, inv, hist=a.history)
    dong = [k for k in mat["blocks"] if k["code"] == "A11.1"][0]["items"]
    assert any(c["ngoai_eide"] for c in dong), dong

    sw = (Path("ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift")).read_text("utf-8")
    assert 'cs["ngoai_eide"]' in sw, "app không đọc nhãn thì người không thấy nó"
    assert "ngoài EIDE" in sw


def test_EIDE_MD_va_DU_AN_JSON_khong_thanh_sua_ngoai(phien, du_an):
    """Lõi tự ghi `EIDE.md` và `du-an.json` ở cuối MỖI LƯỢT, bằng một đường không đi qua
    `mark_agent_wrote`.

    Đo được qua app thật 12/10/2026: bản đầu lọc tiếng của chính lõi bằng một cửa sổ thời
    gian 3 giây, và hai tệp này lọt qua — watcher ghi "anh sửa EIDE.md bên ngoài EIDE",
    rồi bốn phép đo khác của bộ E2E đỏ theo vì lịch sử có thêm changeset lạ. Nên luật đổi
    thành so NỘI DUNG, và ca kiểm này cố tình để **quá** cửa sổ thời gian cũ.
    """
    a, core, out = phien()
    a.llm.script = ScriptedGateway([Response(text="xong")]).script
    a.llm._i = 0
    core.console_act({"kind": "say", "text": "chào"})

    # Lõi ghi EIDE.md ở cuối lượt, nên nội dung trên đĩa đã KHÁC bản trong git — mốc git
    # không còn che được nữa, và dấu "EIDE tự ghi" là thứ duy nhất đứng giữa.
    a.eide_md.append_line("Đang làm", "thử bộ đo watcher", boi="run-do")
    a.eide_md.save()
    assert a._ban_eide_biet("EIDE.md") != a.config.paths.eide_md.read_text("utf-8")

    a._watcher_emit = out.append
    time.sleep(0.2)
    a._tep_doi_ngoai_eide(["EIDE.md", "du-an.json"])
    assert not _cs_ngoai(a), [c.explain["summary"] for c in _cs_ngoai(a)]

    # Nhưng NGƯỜI sửa thật EIDE.md bằng trình soạn thì vẫn phải bắt được.
    md = a.config.paths.eide_md
    md.write_text(md.read_text("utf-8") + "\n## Đừng\n\nđừng dùng malloc trong ISR\n",
                  "utf-8")
    a._tep_doi_ngoai_eide(["EIDE.md"])
    assert [c for c in _cs_ngoai(a)], "sửa thật thì phải thành changeset"


def test_cham_tep_ma_KHONG_DOI_GI_thi_khong_ghi(phien, du_an):
    a, core, out = phien()
    a._watcher_emit = out.append
    (du_an / "main.c").touch()
    a._tep_doi_ngoai_eide(["main.c"])
    assert not _cs_ngoai(a), "một lần `touch` không có gì để hoàn tác"


def test_pha_khoa_khi_tac_tu_dang_giu_tep(phien, du_an):
    """Tác tử đang giữ soft-lock mà người sửa tệp ấy bên ngoài → đúng đường `lock_broken`
    đã có: nó dừng sửa tệp đó, không tự ghi đè."""
    a, core, out = phien()
    a.locks.add("main.c")
    a._watcher_emit = out.append
    (du_an / "main.c").write_text("người sửa ngoài\n", "utf-8")
    a._tep_doi_ngoai_eide(["main.c"])

    assert "main.c" not in a.locks
    assert any(c.method == "surface.unlock" and c.params.get("block") == "main.c"
               for c in out)


def test_noi_cho_NGUOI_va_cho_TAC_TU_biet(phien, du_an):
    a, core, out = phien()
    a._watcher_emit = out.append
    (du_an / "main.c").write_text("sửa ngoài\n", "utf-8")
    a._tep_doi_ngoai_eide(["main.c"])

    # Người: một thông báo kèm mã changeset, và thanh "vừa ghi" để hoàn tác.
    tb = [c.params for c in out if c.method == "notice"]
    assert any("bên ngoài EIDE" in t.get("text", "") for t in tb), tb
    vg = [c.params["vua_ghi"] for c in out
          if c.method == "history.update" and c.params.get("vua_ghi")]
    assert vg and vg[0]["hoan_tac_duoc"] is True
    # Tác tử: EIDE.md §Người vừa sửa là thứ nó đọc mỗi lượt.
    assert "main.c" in (du_an / "EIDE.md").read_text("utf-8")


def test_co_TAT_thi_khong_bat_theo_doi(phien, du_an):
    a, core, out = phien(bat=False)
    assert a.bat_dau_theo_doi(out.append) == ""
    assert a._watcher is None


def test_co_BAT_thi_noi_dang_theo_doi_bang_duong_nao(phien):
    a, core, out = phien(bat=True)
    loi = a.bat_dau_theo_doi(out.append)
    try:
        assert "theo dõi" in loi and a._watcher is not None
        assert a._watcher.cach, "phải nói đang chạy bằng đường nào"
    finally:
        a.dung_theo_doi()


def test_thread_song_qua_mot_lan_loi_cua_nguoi_goi(du_an):
    """Một lỗi trong tay người gọi KHÔNG được giết thread theo dõi: lần sửa sau vẫn phải
    bắt được."""
    no = {"lan": 0}

    def khi_doi(paths):
        no["lan"] += 1
        raise RuntimeError("hỏng")

    w = wt.Watcher(du_an, khi_doi=khi_doi, nhip=0.05)
    w.bat_dau()
    try:
        (du_an / "main.c").write_text("a\n", "utf-8")
        time.sleep(wt.GIAY_GOM + 0.4)
        (du_an / "main.c").write_text("b\n", "utf-8")
        time.sleep(wt.GIAY_GOM + 0.4)
    finally:
        w.dung()
    assert no["lan"] >= 2, f"thread chết sau lần lỗi đầu ({no['lan']} lần gọi)"
