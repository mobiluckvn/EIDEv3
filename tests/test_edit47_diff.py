# -*- coding: utf-8 -*-
"""Khối `diff` — EIDE-EDIT-47 §DEV-366.

Ba chỗ EIDE **nói** "xem diff" mà không có gì để xem (rà 12/10/2026):

* thẻ xung đột cho ba lựa chọn, một trong đó là *"Để tôi xem diff rồi quyết"*, và hai bản
  được nhét vào trường `hai_ban` **cắt ở 4 000 ký tự**, hiện ra như chữ thường;
* cổng `G-FILE` nói "ghi đè bản của anh" mà không nói ghi đè CÁI GÌ;
* `history.preview_restore` nói "1 req quay về bản cũ" mà không nói quay về thành gì.

Bộ này đo cả phép tính (`diff_khoi`) lẫn ĐƯỜNG DẪN của nó tới giao diện — vì bài học của
dự án là hai thứ ấy hỏng riêng.
"""

from __future__ import annotations

import pytest

from eide import Config, Core
from eide.llm import ScriptedGateway
from eide.loop import GIU_BAN_DA_SUA, GIU_BAN_NGUOI, GIU_BAN_TAC_TU, Agent
from eide import diff_khoi as dk

EX = {"summary": "ghi thử", "why": "dựng dữ liệu cho ca đo", "sources": [],
      "diff_prev": "bản đầu", "next": "—", "confidence": "VANG"}


def _d(trai: str, phai: str, goc: str | None = None, **kw):
    return dk.dung_diff(loai="tep", trai=trai, phai=phai, goc=goc,
                        tieu_de="thử", diff_id="d-1", **kw)


# =============================================================== phép tính
def test_hunk_doi_them_xoa_dung_khoang_dong():
    d = _d("a\nb\nc\n", "a\nB\nc\n")
    assert [h["loai"] for h in d["hunks"]] == ["doi"]
    h = d["hunks"][0]
    assert (h["dong_trai"], h["so_trai"]) == (2, 1)
    assert (h["dong_phai"], h["so_phai"]) == (2, 1)

    d = _d("a\nc\n", "a\nb\nc\n")
    assert [h["loai"] for h in d["hunks"]] == ["them"]
    assert d["tom_tat"]["them"] == 1

    d = _d("a\nb\nc\n", "a\nc\n")
    assert [h["loai"] for h in d["hunks"]] == ["xoa"]
    assert d["tom_tat"]["bot"] == 1

    assert _d("y hệt\n", "y hệt\n")["hunks"] == [], "giống nhau thì không có hunk nào"


def test_dong_trong_va_dau_ngoac_KHONG_bi_coi_la_rac():
    """`SequenceMatcher` mặc định bỏ qua dòng xuất hiện trong hơn 1 % của chuỗi dài —
    với mã C thì `}` và dòng trống rơi đúng vào đó, và diff lệch hẳn so với `git diff`."""
    # HƠN 200 DÒNG, và con số ấy là cả phép đo: `autojunk` chỉ bật khi chuỗi dài quá 200.
    # Bản đầu của ca này dựng 160 dòng, nên tháo `autojunk=False` ra **không đỏ** — một ca
    # kiểm có dàn dựng làm chính phép phá của nó vô hiệu.
    trai = "\n".join(["void f(void) {", "    int a = 1;", "}", ""] * 80)
    assert len(trai.splitlines()) > 200
    phai = trai.replace("int a = 1;", "int a = 2;", 1)
    d = _d(trai, phai)
    assert len(d["hunks"]) == 1, f"{len(d['hunks'])} đoạn cho MỘT dòng đổi"
    assert d["hunks"][0]["dong_trai"] == 2
    # Đây mới là phép đo. Đếm SỐ ĐOẠN thì không bắt được gì: bật `autojunk` lên, một dòng
    # đổi vẫn ra **một** đoạn — nhưng đoạn ấy rộng 318 dòng, tức diff bảo cả tệp đã đổi.
    assert d["hunks"][0]["so_trai"] == 1, \
        f"một dòng đổi mà tô đỏ {d['hunks'][0]['so_trai']} dòng"
    assert d["tom_tat"]["doi"] == 1


def test_noi_dung_gui_MOT_lan_chu_khong_nhet_vao_tung_hunk():
    """Một tệp 2 000 dòng đổi rải rác sẽ gửi gần hai lần nội dung nếu mỗi hunk mang chữ."""
    d = _d("a\nb\n", "A\nB\n")
    assert all("trai" not in h and "phai" not in h for h in d["hunks"])
    assert d["trai"]["noi_dung"] == "a\nb\n"


def test_hien_vat_so_theo_JSON_in_dep_va_SAP_KHOA():
    """Thứ tự khoá trong dict không phải nội dung của hiện vật — để nó đổi thì diff hiện
    những dòng "đổi" mà chẳng có gì đổi."""
    a = dk.in_canonical({"b": 2, "a": 1})
    b = dk.in_canonical({"a": 1, "b": 2})
    assert a == b
    assert dk.diff_tom_tat(a, b)["doan"] == 0
    assert "\n" in dk.in_canonical({"a": [1, 2]}), "phải in đẹp, không dồn một dòng"


def test_cat_noi_dung_qua_dai_thi_NOI_RA(monkeypatch):
    monkeypatch.setattr(dk, "TRAN_KY_TU", 50)
    d = _d("x" * 200, "y" * 200)
    assert d["trai"]["cat"] is True and "CẮT Ở" in d["trai"]["noi_dung"]
    # Hash vẫn của bản ĐỦ: nó là thứ dùng làm `base_version` khi người lưu lại.
    assert d["trai"]["hash"] == dk.bam("x" * 200)


# =============================================================== ba bên
def test_ba_ben_CA_HAI_cung_sua_mot_cho_thi_xung_dot():
    goc = "dòng 1\ndòng 2\ndòng 3\n"
    d = _d("dòng 1\nANH sửa\ndòng 3\n", "dòng 1\nTÁC TỬ sửa\ndòng 3\n", goc=goc)
    assert [h["loai"] for h in d["hunks"]] == ["xung_dot"]
    assert d["tom_tat"]["xung_dot"] == 1
    assert d["goc"]["noi_dung"] == goc


def test_ba_ben_CHI_MOT_ben_sua_thi_KHONG_phai_xung_dot():
    """Chỉ một bên đụng thì không có gì phải hỏi người — lấy bên ấy là phép gộp đúng."""
    goc = "dòng 1\ndòng 2\ndòng 3\n"
    d = _d(goc, "dòng 1\nTÁC TỬ sửa\ndòng 3\n", goc=goc)
    assert [h["loai"] for h in d["hunks"]] == ["doi"]
    assert d["tom_tat"]["xung_dot"] == 0


def test_ba_ben_hai_ben_sua_HAI_CHO_KHAC_nhau_thi_khong_xung_dot():
    goc = "a\nb\nc\nd\ne\n"
    d = _d("a\nB\nc\nd\ne\n", "a\nb\nc\nD\ne\n", goc=goc)
    assert d["tom_tat"]["xung_dot"] == 0, [h["loai"] for h in d["hunks"]]
    assert len(d["hunks"]) == 2


def test_xoa_mot_ben_sua_ben_kia_KHONG_duoc_danh_xung_dot(du_an):
    """Giới hạn đã biết của phép tô màu, ghi lại chứ không giấu.

    Một bên xoá trắng đoạn ấy thì không còn dòng nào để hỏi "dòng này có mới không", nên
    hunk không được đánh đỏ — dù diff3 gọi "xoá một bên, sửa bên kia" là xung đột.

    Vì sao chấp nhận được: thứ QUYẾT ĐỊNH có dựng thẻ hay không là `git merge-file`, và ca
    này nó vẫn bắt. Người vẫn thấy thẻ, vẫn thấy hai bản, chỉ thiếu cái nhãn đỏ trên một
    đoạn. Ca kiểm này tồn tại để lần sau ai đó sửa phép tô màu thì biết chỗ cần lo.
    """
    from eide.vcs import Vcs

    goc = "a\nb\nc\n"
    d = _d("a\nc\n", "a\nB\nc\n", goc=goc)          # trái xoá, phải sửa
    assert d["tom_tat"]["xung_dot"] == 0, "nếu ca này xanh lên thì phép tô màu đã khá hơn"
    assert d["hunks"], "vẫn phải hiện ra là hai bên khác nhau ở đoạn ấy"
    assert not Vcs(du_an).merge_ba_chieu(base=goc, cua_nguoi="a\nc\n",
                                         cua_tac_tu="a\nB\nc\n").sach, \
        "git vẫn coi đây là xung đột — nên thẻ vẫn dựng, chỉ khối diff thiếu màu"


def test_hai_bo_may_dong_y_nhau(du_an):
    """`difflib` ở đây CHỈ TÔ MÀU; quyết định "gộp sạch hay không" vẫn là `git merge-file`
    ở `_sua_tep`. Hai hiện thực lệch nhau thì thẻ nói "đụng nhau" mà diff không có đoạn
    đỏ nào — ca này canh đúng chỗ ấy trên ca thường gặp nhất."""
    from eide.vcs import Vcs

    goc = "dòng 1\ndòng 2\ndòng 3\n"
    nguoi = "dòng 1\nANH sửa\ndòng 3\n"
    tac_tu = "dòng 1\nTÁC TỬ sửa\ndòng 3\n"
    kq = Vcs(du_an).merge_ba_chieu(base=goc, cua_nguoi=nguoi, cua_tac_tu=tac_tu)
    co_xung_dot_theo_git = not kq.sach
    co_xung_dot_theo_diff = _d(nguoi, tac_tu, goc=goc)["tom_tat"]["xung_dot"] > 0
    assert co_xung_dot_theo_git == co_xung_dot_theo_diff is True

    sach = _d(goc, tac_tu, goc=goc)["tom_tat"]["xung_dot"] == 0
    assert Vcs(du_an).merge_ba_chieu(base=goc, cua_nguoi=goc,
                                     cua_tac_tu=tac_tu).sach is sach is True


# =============================================================== lệnh thứ 17
def test_diff_show_la_lenh_hop_le_va_doi_du_truong():
    from eide.protocol.uicommand import UI_COMMANDS, diff_show

    assert "diff.show" in UI_COMMANDS and len(UI_COMMANDS) == 17
    c = diff_show(_d("a\n", "b\n"))
    assert c.method == "diff.show" and c.params["diff_id"] == "d-1"
    with pytest.raises(Exception):
        diff_show({"diff_id": "d-2"})          # thiếu trai/phai/hunks


# =============================================================== thẻ xung đột
@pytest.fixture
def phien(du_an):
    a = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    out: list = []
    core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                on_query=a.hoi_chi_doc)
    return a, core, out


def _diffs(out):
    return [c.params for c in out if c.method == "diff.show"]


def _the(out):
    return [c.params["card"] for c in out
            if c.method == "console.post" and c.params.get("card")]


def _loi(out):
    return "\n".join(c.params.get("text", "") for c in out
                     if c.method == "console.post" and c.params.get("role") == "agent")


def test_the_xung_dot_PHAT_diff_gan_dung_vao_no(phien, du_an):
    a, core, out = phien
    (du_an / "main.c").write_text("int main(void){return 0;}\n", "utf-8")

    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": "khong-phai-hash-nao",
                               "content": "int main(void){return 42;}\n"},
                      "origin": {"surface": "code"}, "note": "thử"})

    the = [t for t in _the(out) if t.get("tra_loi_thanh") == "xung_dot"]
    assert the, "không dựng thẻ xung đột"
    ds = _diffs(out)
    assert len(ds) == 1, "thẻ nói 'xem diff' thì phải có đúng một khối diff đi kèm"
    d = ds[0]
    assert d["gan_voi"]["card_id"] == the[0]["card_id"], \
        "diff không gắn vào thẻ thì giao diện vẽ nó ở đâu?"
    assert d["cho_phep_sua"] is True, "lựa chọn thứ ba là 'dùng bản tôi vừa sửa' — "\
                                      "không có chỗ sửa thì nó là lời mời suông"
    assert d["trai"]["noi_dung"] == "int main(void){return 42;}\n"
    assert d["phai"]["noi_dung"] == "int main(void){return 0;}\n"
    assert d["hunks"], "hai bản khác nhau mà không có đoạn nào?"
    assert GIU_BAN_DA_SUA in the[0]["questions"][0]["choices"]
    assert "hai_ban" not in the[0], "trường cắt-4000-ký-tự phải biến mất, không nằm song song"


def test_noi_dung_dai_KHONG_con_bi_cat_o_4000_ky_tu(phien, du_an):
    """Trần cũ cắt một tệp 300 dòng ở đúng chỗ nó bắt đầu khác nhau."""
    a, core, out = phien
    dai = "\n".join(f"// dòng {i} xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" for i in range(200))
    (du_an / "dai.c").write_text(dai + "\n", "utf-8")
    assert len(dai) > 4000

    core.console_act({"kind": "edit", "target": {"type": "file", "id": "dai.c"},
                      "data": {"base_version": "lech", "content": dai + "\n// thêm\n"},
                      "origin": {"surface": "code"}})
    d = _diffs(out)[0]
    assert len(d["phai"]["noi_dung"]) > 4000
    assert d["phai"]["cat"] is False


def test_xung_dot_BA_BEN_thi_diff_mang_ban_goc(phien, du_an):
    a, core, out = phien
    goc = "a\nb\nc\n"
    (du_an / "x.txt").write_text("a\nTÁC TỬ\nc\n", "utf-8")
    bam_goc = a.history.blobs.put(goc)          # bản người đã mở, còn trong kho blob

    core.console_act({"kind": "edit", "target": {"type": "file", "id": "x.txt"},
                      "data": {"base_version": bam_goc, "content": "a\nANH\nc\n"},
                      "origin": {"surface": "code"}})
    ds = _diffs(out)
    assert ds, "hai bên sửa cùng dòng — phải ra thẻ xung đột kèm diff"
    assert ds[0]["goc"]["noi_dung"] == goc
    assert ds[0]["tom_tat"]["xung_dot"] == 1


def test_tra_loi_the_xung_dot_KHONG_ton_mot_luot_mo_hinh(phien, du_an):
    """Trước DEV-366 câu trả lời rơi xuống vòng lặp công cụ: mô hình tự nghĩ cách ghi lại
    tệp, dù nó chỉ thấy câu trả lời chứ không thấy hai bản."""
    a, core, out = phien
    (du_an / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": "lech", "content": "int main(void){return 42;}\n"},
                      "origin": {"surface": "code"}})
    card_id = [t for t in _the(out) if t.get("tra_loi_thanh") == "xung_dot"][0]["card_id"]
    out.clear()

    core.console_act({"kind": "choose",
                      "data": {"card_id": card_id, "answers": {"chon": GIU_BAN_TAC_TU}},
                      "origin": {"surface": "console"}})

    assert a.llm._i == 0, "không được gọi mô hình: ba lựa chọn đều là việc mã làm được"
    assert "Giữ nguyên bản hiện tại" in _loi(out)
    assert (du_an / "main.c").read_text("utf-8") == "int main(void){return 0;}\n"
    assert not [c for c in out if c.method == "console.post"
                and c.params.get("card")], "không dựng thêm thẻ nào"
    # Thẻ phải rời khỏi hàng chờ, nếu không khối nhắc còn bảo mô hình "còn thẻ đang chờ".
    assert not a.pending_cards


def test_giai_xung_dot_bang_ban_nguoi_SUA_thi_ghi_dung_noi_dung_ay(phien, du_an):
    """Tiêu chí chấp nhận của DEV-366: bấm *Giữ bản đã sửa* → đúng nội dung ấy nằm trên
    đĩa và trong `blobs/`, một changeset `author=human`."""
    a, core, out = phien
    (du_an / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": "lech", "content": "int main(void){return 42;}\n"},
                      "origin": {"surface": "code"}})
    d = _diffs(out)[0]
    card_id = d["gan_voi"]["card_id"]
    da_sua = "int main(void){return 7;}\n"          # người sửa thẳng trong cột phải

    # Giao diện gửi HAI thao tác, nội dung TRƯỚC rồi lựa chọn SAU.
    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": d["phai"]["hash"], "content": da_sua,
                               "summary": "giải xung đột"},
                      "origin": {"surface": "history", "block": "the-xung-dot"}})
    core.console_act({"kind": "choose",
                      "data": {"card_id": card_id, "answers": {"chon": GIU_BAN_DA_SUA}},
                      "origin": {"surface": "console"}})

    assert (du_an / "main.c").read_text("utf-8") == da_sua
    cua_nguoi = [c for c in a.history.log.all() if c.by_human]
    assert len(cua_nguoi) == 1 and cua_nguoi[0].reversible
    # Bản TRƯỚC khi ghi phải còn trong blob — không thì "hoàn tác được" là lời hứa suông.
    # `blob_truoc` nằm ở phép NGHỊCH ĐẢO — nó là thứ dùng để lùi, không phải để tiến.
    blob = (cua_nguoi[0].inverse[0].get("blob_truoc") or {}).get("main.c")
    assert blob and a.history.blobs.get(blob).decode() == "int main(void){return 0;}\n"


def test_chon_mot_thu_la_thi_KHONG_doan_ho(phien, du_an):
    a, core, out = phien
    (du_an / "main.c").write_text("x\n", "utf-8")
    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": "lech", "content": "y\n"},
                      "origin": {"surface": "code"}})
    card_id = _diffs(out)[0]["gan_voi"]["card_id"]
    out.clear()
    core.console_act({"kind": "choose",
                      "data": {"card_id": card_id, "answers": {"chon": "ừ thì sao cũng được"}},
                      "origin": {"surface": "console"}})
    assert "Chưa rõ anh chọn" in _loi(out)
    assert (du_an / "main.c").read_text("utf-8") == "x\n"


def test_chon_giu_ban_nguoi_ma_giao_dien_quen_gui_noi_dung_thi_NOI_RA(phien, du_an):
    a, core, out = phien
    (du_an / "main.c").write_text("x\n", "utf-8")
    core.console_act({"kind": "edit", "target": {"type": "file", "id": "main.c"},
                      "data": {"base_version": "lech", "content": "y\n"},
                      "origin": {"surface": "code"}})
    card_id = _diffs(out)[0]["gan_voi"]["card_id"]
    out.clear()
    core.console_act({"kind": "choose",
                      "data": {"card_id": card_id, "answers": {"chon": GIU_BAN_NGUOI}},
                      "origin": {"surface": "console"}})
    assert "chưa ghi gì cả" in _loi(out), "im lặng ở đây là người tưởng đã lưu xong"


# =============================================================== cổng G-FILE
def _agent_co_co(du_an, bat: bool, call: dict):
    """Chạy MỘT LƯỢT THẬT tới lúc cổng G-FILE mở ra.

    Dựng `TurnContext` giả thì nhanh hơn, và nó đã bị từ chối ở đây: ba lớp chặn
    (`check_sandbox` trước hết) đọc `ctx.config`, nên một ctx giả vừa đủ cho phép đo sẽ
    **đi vòng qua chính mấy lớp** mà thẻ cổng là kết quả của chúng.
    """
    from eide.llm.gateway import Response, ToolCall

    cfg = Config.for_project(du_an, autonomy="A1")      # mức thấp: ghi tệp phải hỏi
    cfg.features.cong_co_diff = bat
    a = Agent(cfg, llm=ScriptedGateway([
        Response(tool_calls=[ToolCall("c1", call["tool"], call["args"])]),
        Response(text="Đợi anh duyệt."),
    ]), project_name="du-an-thu")
    out: list = []
    core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint)
    core.console_act({"kind": "say", "text": "ghi tệp giúp tôi"})
    return a, out


def _goi(tool="fs.write", **args):
    return {"tool": tool, "args": {"explain": EX, **args}}


def test_co_TAT_thi_cong_G_FILE_khong_phat_diff(du_an):
    (du_an / "main.c").write_text("cũ\n", "utf-8")
    a, out = _agent_co_co(du_an, False, _goi(path="main.c", content="mới\n"))
    assert [t for t in _the(out) if t.get("gate") == "G-FILE"], "phải có thẻ cổng G-FILE"
    assert not _diffs(out), "cờ tắt mà vẫn đổi nội dung thẻ tác tử dựng"


def test_co_BAT_thi_cong_G_FILE_hien_ghi_de_cai_gi_len_cai_gi(du_an):
    (du_an / "main.c").write_text("cũ\n", "utf-8")
    a, out = _agent_co_co(du_an, True, _goi(path="main.c", content="mới\n"))
    ds = _diffs(out)
    assert len(ds) == 1
    the = [t for t in _the(out) if t.get("gate") == "G-FILE"][0]
    assert ds[0]["gan_voi"]["gate_id"] == the["gate_id"]
    assert ds[0]["trai"]["noi_dung"] == "cũ\n" and ds[0]["phai"]["noi_dung"] == "mới\n"
    assert ds[0]["cho_phep_sua"] is False, "sửa thẳng rồi duyệt là DEV-370 — mở ô sửa khi "\
                                           "lõi chưa nhận bản sửa là nuốt mất việc của người"


def test_cong_fs_edit_hien_ket_qua_cua_phep_THAY(du_an):
    (du_an / "main.c").write_text("a\nb\nc\n", "utf-8")
    a, out = _agent_co_co(du_an, True, _goi("fs.edit", path="main.c",
                                            old_string="b", new_string="B"))
    assert _diffs(out)[0]["phai"]["noi_dung"] == "a\nB\nc\n"


def test_phep_thay_sap_hong_thi_KHONG_ve_diff_doan(du_an):
    """`fs.edit` với đoạn cũ khớp 0 hoặc 2 lần sẽ bị công cụ từ chối (E1005/E1006). Vẽ
    một diff cho phép thay ấy là nói sai về thứ sắp xảy ra."""
    (du_an / "main.c").write_text("b\nb\n", "utf-8")
    a, out = _agent_co_co(du_an, True, _goi("fs.edit", path="main.c",
                                            old_string="b", new_string="B"))
    assert not _diffs(out)


def test_ghi_tep_MOI_thi_cot_trai_rong_va_NOI_RA(du_an):
    a, out = _agent_co_co(du_an, True, _goi(path="chua-co.c", content="nội dung\n"))
    assert _diffs(out)[0]["trai"]["noi_dung"] == ""
    assert "Chưa có tệp này" in _diffs(out)[0]["trai"]["nhan"]


def test_ghi_Y_HET_ban_dang_co_thi_khong_co_gi_de_xem(du_an):
    (du_an / "y-het.c").write_text("y hệt\n", "utf-8")
    a, out = _agent_co_co(du_an, True, _goi(path="y-het.c", content="y hệt\n"))
    assert not _diffs(out)


# =============================================================== xem trước khôi phục
def test_preview_restore_noi_moi_hien_vat_doi_MAY_DONG(phien):
    a, core, out = phien
    a.history.ghi_kho(author="agent:r", artefact_id="FR-01", type="req", op="create",
                      canonical={"text": "≥ 1 MB/s", "ghi_chu": "bản đầu"}, explain=EX)
    s = a.history.tao_snapshot(ten="mốc", boi="human")
    a.history.ghi_kho(author="agent:r", artefact_id="FR-01", type="req", op="update",
                      canonical={"text": "≥ 9 MB/s", "ghi_chu": "bản đầu"}, explain=EX)
    a.history.ghi_kho(author="agent:r", artefact_id="FR-02", type="req", op="create",
                      canonical={"text": "sinh sau"}, explain=EX)

    r = core.dispatch("history.preview_restore", {"snapshot_id": s.id})
    tt = {x["id"]: x for x in r["diff_tom_tat"]}
    assert tt["FR-01"]["viec"] == "quay về bản cũ" and tt["FR-01"]["doi"] == 1
    assert tt["FR-02"]["viec"] == "gỡ bỏ"
    # Chỉ CON SỐ: một bản ưng ý cách hiện tại hai mươi hiện vật thì gửi cả hai mươi nội
    # dung là trả giá cho thứ người chưa mở ra xem.
    assert all("noi_dung" not in x for x in r["diff_tom_tat"])
