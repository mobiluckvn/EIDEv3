# -*- coding: utf-8 -*-
"""Mở lại dự án: dựng lại hội thoại cũ mà KHÔNG dựng lại những cái nút đã chết.

Đo được trên app thật ngày 28/09/2026, trên một dự án có hai thẻ cổng đều **đã được duyệt
xong**:

    Vừa mở lại   : dòng hội thoại = 15 | thẻ đang chờ = 2      ← hai thẻ đã trả lời rồi
    Sau Cmd-R x1 : dòng hội thoại = 30 | thẻ đang chờ = 4
    Sau Cmd-R x2 : dòng hội thoại = 45 | thẻ đang chờ = 6
    Sau Cmd-R x3 : dòng hội thoại = 60 | thẻ đang chờ = 8

Và bấm "Duyệt" trên một thẻ được dựng lại thì nhận `E_GATE_STALE` — **một cái nút bấm được mà
không làm gì**. Thứ trả lời được một thẻ (lời gọi công cụ đang treo) nằm trong bộ nhớ của tiến
trình đã chết, nên dòng chữ phát lại được còn cái nút thì không.

Ba bài kiểm dưới đây khoá ba hành vi: đóng thẻ đã có quyết định · cho hết hạn thẻ chưa ai trả
lời · và chỉ phát lại đúng một lần.
"""

from __future__ import annotations

from typing import Any

import pytest

from eide.ids import IdGen
from eide.protocol.ledger import Ledger
from eide.protocol.rpc import Core


def _core(tmp_path) -> tuple[Core, list[Any]]:
    """Một lõi trần, chỉ đủ để gọi `ui.sync`. Không cần mô hình."""
    ra: list[Any] = []
    lg = Ledger(tmp_path / "ledger.jsonl")
    c = Core(lg, IdGen(tmp_path / "counters.json"),
             run_turn=lambda *a, **k: None,
             on_emit=ra.append, on_sync=lambda emit: None)
    return c, ra


def _dang_the(lg: Ledger, gid: str, gate: str, *, quyet: str | None) -> None:
    """Ghi vào sổ cái một thẻ cổng và (nếu có) quyết định của người, y như lúc chạy thật."""
    lg.append("gate", {"run_id": "run-001", "gate_id": gid, "gate": gate,
                       "tool": "target.flash", "state": "open"})
    lg.append("ui_command", {
        "method": "console.post",
        "params": {"text": f"[Cổng {gate}]", "role": "agent",
                   "card": {"type": "gate", "card_id": gid, "gate_id": gid, "gate": gate,
                            "options": ["Duyệt", "Từ chối"]}}})
    if quyet:
        lg.append("gate", {"run_id": "run-002", "gate_id": gid, "state": quyet,
                           "act_id": "h-0001"})


def _lenh(ra: list[Any], method: str) -> list[Any]:
    return [c for c in ra if getattr(c, "method", None) == method]


def test_the_da_co_quyet_dinh_thi_dung_lai_o_trang_thai_DA_TRA_LOI(tmp_path):
    """Sổ cái BIẾT thẻ đã được duyệt. Dựng lại nó thành câu hỏi đang chờ là nói sai về chính
    cái lịch sử nó đang chiếu ra — và người sẽ bấm vào một nút không làm gì."""
    c, ra = _core(tmp_path)
    _dang_the(c.ledger, "gate-0001", "G-FLASH", quyet="approved")
    _dang_the(c.ledger, "gate-0002", "G-DATA", quyet="rejected")

    c.ui_sync()

    dong = _lenh(ra, "card.resolve")
    assert {x.params["card_id"] for x in dong} == {"gate-0001", "gate-0002"}
    chon = {x.params["card_id"]: x.params.get("choice") for x in dong}
    assert chon["gate-0001"] == "Duyệt" and chon["gate-0002"] == "Từ chối", \
        "phải nói người đã chọn gì, không chỉ đóng thẻ"
    assert not _lenh(ra, "card.expire"), "thẻ đã có quyết định thì không phải hết hạn"


def test_the_chua_ai_tra_loi_thi_HET_HAN_chu_khong_treo_tiep(tmp_path):
    """Thẻ mở lúc app chết: thứ trả lời được nó nằm trong bộ nhớ tiến trình đã chết.

    Hai lối sai đều tệ theo hai kiểu. Để nó treo tiếp thì người bấm Duyệt và nhận
    `E_GATE_STALE` — mất quyền quyết định mà không biết. Tự chạy lại thì một việc chưa ai
    đồng ý đã xảy ra. Lối đúng là nói thẳng nó hết hiệu lực, kèm cách làm lại.
    """
    c, ra = _core(tmp_path)
    _dang_the(c.ledger, "gate-0007", "G-FLASH", quyet=None)

    c.ui_sync()

    het = _lenh(ra, "card.expire")
    assert [x.params["card_id"] for x in het] == ["gate-0007"]
    vi = het[0].params.get("why", "")
    assert "không còn hiệu lực" in vi and "nhờ lại" in vi, \
        "phải nói vì sao VÀ phải làm gì tiếp — im lặng đóng thẻ cũng là mất quyền quyết"
    assert not _lenh(ra, "card.resolve")


def test_phat_lai_dung_MOT_lan_du_goi_ui_sync_bao_nhieu_lan(tmp_path):
    """`ui.sync` còn chạy khi người bấm "Vẽ lại" (Cmd-R) và khi giao diện mất đồng bộ — lúc
    ấy Console đang có sẵn các dòng cũ. Đo được: mỗi lần Cmd-R cộng 15 dòng và 2 thẻ, tuyến
    tính, không ai gộp trùng.
    """
    c, ra = _core(tmp_path)
    _dang_the(c.ledger, "gate-0001", "G-FLASH", quyet="approved")

    lan_1 = c.ui_sync()
    n1 = len(_lenh(ra, "console.post"))
    lan_2 = c.ui_sync()
    lan_3 = c.ui_sync()

    assert lan_1["dong_transcript"] == 1
    assert lan_2["dong_transcript"] == 0 and lan_3["dong_transcript"] == 0
    assert len(_lenh(ra, "console.post")) == n1, "Cmd-R không được nhân đôi Console"
    assert len(_lenh(ra, "card.resolve")) == 1
    # Nhưng bề mặt thì VẪN phải được vẽ lại — đó mới là việc chính của Cmd-R.
    assert lan_2["painted"] and lan_3["painted"]


def test_phat_lai_khong_ghi_them_vao_so_cai(tmp_path):
    """CX16: phát lại tái tạo trạng thái, không tạo ra lịch sử mới. Nếu các lệnh đóng thẻ bị
    ghi lại thì lần mở thứ hai sẽ thấy một lịch sử khác lần đầu."""
    c, ra = _core(tmp_path)
    _dang_the(c.ledger, "gate-0001", "G-FLASH", quyet="approved")
    truoc = len(list(c.ledger.read()))

    c.ui_sync()

    assert len(list(c.ledger.read())) == truoc


def test_tro_du_an_vao_mot_TEP_thi_noi_ro_chu_khong_nem_loi_he_thong(tmp_path):
    """Ô "Thư mục dự án" là một ô VĂN BẢN — người gõ tay được, nên chặn ở bộ chọn là chưa đủ.

    Trước: `mkdir` ném `NotADirectoryError: …/main.c/.eide`. Đúng chỗ, nhưng người đọc không
    hiểu chuyện gì xảy ra và cũng không biết phải làm gì.
    """
    from eide.config import Config

    tep = tmp_path / "main.c"
    tep.write_text("int main(void){return 0;}\n", "utf-8")
    with pytest.raises(NotADirectoryError) as e:
        Config.for_project(tep).paths.ensure()
    vi = str(e.value)
    assert "là một TỆP" in vi and "thư mục" in vi
    assert "Chọn thư mục chứa tệp ấy" in vi, "phải nói làm gì tiếp, không chỉ nói sai ở đâu"


def test_thu_muc_rong_van_mo_duoc(tmp_path):
    """"Tạo dự án" trong EIDE = mở một thư mục rỗng. Nếu phép rào trên cũng chặn luôn thư
    mục chưa tồn tại thì nó đã giết mất cách duy nhất để bắt đầu một dự án."""
    from eide.config import Config

    moi = tmp_path / "du-an-moi"
    p = Config.for_project(moi).paths.ensure()
    assert p.state_dir.is_dir() and p.blobs.is_dir()


def test_noi_thang_rang_tac_tu_KHONG_mang_theo_tri_nho_hoi_thoai(tmp_path):
    """Console dựng lại nguyên cuộc trò chuyện hôm qua; tác tử thì bắt đầu với ngữ cảnh rỗng.

    Hai thứ ấy là hai kho khác nhau, và cái im lặng giữa chúng đọc như "tác tử vẫn nhớ mọi
    thứ". Người dùng sẽ phát hiện ra điều ngược lại vào đúng lúc đắt nhất — khi họ nói "làm
    tiếp cái hôm qua" và nhận lại một câu hỏi lại từ đầu.
    """
    c, ra = _core(tmp_path)
    _dang_the(c.ledger, "gate-0001", "G-FLASH", quyet="approved")

    c.ui_sync()

    bao = [x for x in _lenh(ra, "notice")]
    assert bao, "phải có một dòng nói rõ đây là hình chiếu, không phải trí nhớ"
    t = " ".join(x.params.get("text", "") for x in bao)
    assert "KHÔNG mang theo trí nhớ hội thoại" in t
    assert "EIDE.md" in t, "phải chỉ ra nó lấy hiểu biết từ đâu, không chỉ nói nó thiếu gì"
