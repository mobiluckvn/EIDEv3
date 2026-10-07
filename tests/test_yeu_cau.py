# -*- coding: utf-8 -*-
"""M2-03 — chất lượng của chính YÊU CẦU, đo bằng mã chứ không bằng cảm nhận.

Ba câu hỏi, ba hàm thuần, và cả ba đều trả lời được **0 token**:

* tiêu chí này có đo được không — tức có con số kèm đơn vị hay phép so không;
* câu này có từ mơ hồ nào không — "nhanh", "ổn định", "thông minh";
* yêu cầu này đã có ai viết chưa — hai REQ nói cùng một việc thì không ai biết cái nào
  đang có hiệu lực.

Vì sao cần: `store.req_create` nhận bất cứ câu nào trích được lời người dùng (N7), và
không kiểm gì thêm. Đo được trên bộ usecase TC004: người dùng gõ *"làm cho mình cái mạch
thông minh"*, và một yêu cầu "mạch thông minh" vào kho trót lọt. Yêu cầu ấy không sai —
nó chỉ **không đo được**, nên mọi thứ dựng trên nó cũng không đo được.

Bộ kiểm này KHÔNG chặn ghi: chặn một yêu cầu vì nó mơ hồ là lấy mất quyền của người đang
còn mơ hồ về chính việc họ muốn. Nó nói ra, và chỉ đường `ask_user`.
"""

from __future__ import annotations

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}


@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    def _lam(**co):
        from eide.config import Features

        f = Features(**co)
        cfg = Config.for_project(du_an)
        cfg.features = f
        ag = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
        r = build_registry(f)
        ctx = TurnContext(config=cfg, store=ag.store, ledger=ag.ledger,
                          eide_md=ag.eide_md, ids=ag.ids, registry=r,
                          emit=lambda c: None, history=ag.history, agent=ag,
                          run_id="run-1", project_name="du-an-thu")
        return ag, r, ctx
    return _lam


# =========================================================================== tiêu chí
def test_tieu_chi_khong_so_thi_canh_bao():
    """TC-M2-03-01 — "chạy nhanh" không phải một tiêu chí; "≥ 5 MB/s" thì có."""
    from eide.yeu_cau import kiem_tieu_chi

    assert kiem_tieu_chi("chạy nhanh"), "câu không có số nào mà vẫn qua"
    assert kiem_tieu_chi("") , "tiêu chí rỗng phải bị nói ra"
    assert kiem_tieu_chi("≥ 5 MB/s") == []
    assert kiem_tieu_chi("dưới 120 ms kể từ lúc bấm") == []
    assert kiem_tieu_chi("100 Mbps") == []


def test_tieu_chi_co_so_ma_khong_don_vi_van_bi_keu():
    """Một con số trần không nói gì: "dưới 5" là 5 giây, 5 phần trăm, hay 5 tệp?"""
    from eide.yeu_cau import kiem_tieu_chi

    assert kiem_tieu_chi("dưới 5")


# =========================================================================== từ mơ hồ
def test_tu_mo_ho_bo_dau():
    """TC-M2-03-02 — người gõ không dấu vẫn phải bắt được.

    Người dùng thật gõ cả hai kiểu, thường trong cùng một phiên. Một bộ dò chỉ bắt được
    bản có dấu sẽ im lặng đúng nửa số lần.
    """
    from eide.yeu_cau import tu_mo_ho

    assert "ổn định" in tu_mo_ho("Hệ thống phải ON DINH")
    assert "ổn định" in tu_mo_ho("hệ thống phải ổn định")
    assert "thông minh" in tu_mo_ho("làm cho mình cái mạch thông minh")


def test_tu_mo_ho_khong_bat_trong_long_tu_khac():
    """`bit`, `unit`, `init`, `exit` đều chứa "it" — bắt theo chuỗi con thì kêu oan hết.

    Đo trước khi viết ca này, vì bản đầu tôi lấy ví dụ "thiết bị" cho rằng "thiet" chứa
    "it" — **nó không chứa**, và ca kiểm dựng trên điều đó vẫn xanh cả khi đổi sang phép
    so chuỗi con, tức là nó không canh gì cả. Bốn từ dưới đây thì va thật, và chúng là từ
    thường gặp nhất trong một yêu cầu phần mềm nhúng.
    """
    from eide.yeu_cau import tu_mo_ho

    for cau in ("Thanh ghi 8 bit", "Chạy unit test trước khi nạp", "Gọi init một lần",
                "Thoát bằng exit code 0"):
        assert tu_mo_ho(cau) == [], cau
    # Còn khi "ít" đứng thành một từ thật thì phải bắt được.
    assert tu_mo_ho("Dùng ít RAM") == ["ít"]


# =========================================================================== trùng lặp
def test_trung_lap():
    """TC-M2-03-03 — hai câu nói cùng một việc thì phải chỉ ra mã REQ đã có."""
    from eide.yeu_cau import trung_lap

    ds = [{"id": "FR-01", "canonical": {"text": "Nhận tệp phim qua LAN"}}]
    assert trung_lap("nhận tệp phim qua mạng LAN", ds) == ["FR-01"]
    assert trung_lap("Đo nhiệt độ buồng sấy mỗi 5 giây", ds) == []
    # Chỗ NGƯỠNG thật sự quyết định: hai câu trùng một nửa thì KHÔNG phải trùng lặp.
    # "nhận tệp … qua …" giống nhau 3/7 từ — cùng dạng câu, khác hẳn việc.
    assert trung_lap("Nhận tệp ảnh qua USB", ds) == [], "ngưỡng quá thấp: kêu cả câu khác việc"
    # Và ngưỡng phải đọc được, không phải chôn trong hàm: hạ nó xuống thì câu trên bị kêu.
    assert trung_lap("Nhận tệp ảnh qua USB", ds, nguong=0.4) == ["FR-01"]


# =========================================================================== qua công cụ
def test_req_create_co_bat_tra_canh_bao(bo):
    """TC-M2-03-04 — cờ BẬT: có cảnh báo, mà REQ **vẫn được ghi**."""
    ag, r, ctx = bo(req_chat_luong=True)
    ra = r.get("store.req_create").fn(ctx, id="FR-01", loai="FR",
                                      text="Hệ thống phải chạy nhanh và ổn định",
                                      source_quote="anh nói: cho nó nhanh với ổn định vào",
                                      explain=EX)
    assert "canh_bao_chat_luong" in ra, sorted(ra)
    loai = {c["loai"] for c in ra["canh_bao_chat_luong"]}
    assert "tu_mo_ho" in loai and "tieu_chi" in loai, ra["canh_bao_chat_luong"]
    assert ag.store.get("FR-01") is not None, "cảnh báo đã CHẶN mất việc ghi"
    assert "ask_user" in ra["note_vi"], ra["note_vi"]


def test_req_create_bat_trung_lap_voi_REQ_da_co(bo):
    ag, r, ctx = bo(req_chat_luong=True)
    r.get("store.req_create").fn(ctx, id="FR-01", loai="FR",
                                 text="Nhận tệp phim qua LAN",
                                 source_quote="anh nói: nhận phim qua LAN",
                                 explain=EX)
    ra = r.get("store.req_create").fn(ctx, id="FR-02", loai="FR",
                                      text="nhận tệp phim qua mạng LAN",
                                      source_quote="anh nói: nhận phim qua mạng LAN",
                                      explain=EX)
    trung = [c for c in ra["canh_bao_chat_luong"] if c["loai"] == "trung_lap"]
    assert trung and "FR-01" in str(trung[0]), ra["canh_bao_chat_luong"]


def test_req_update_cung_kiem(bo):
    ag, r, ctx = bo(req_chat_luong=True)
    r.get("store.req_create").fn(ctx, id="FR-01", loai="FR", text="Chép tệp ≥ 5 MB/s",
                                 criteria="≥ 5 MB/s qua LAN 100 Mbps",
                                 source_quote="anh nói: chép cho nhanh, 5 MB/s",
                                 explain=EX)
    ra = r.get("store.req_update").fn(ctx, id="FR-01", text="Chép tệp cho mượt", explain=EX)
    assert "canh_bao_chat_luong" in ra, sorted(ra)
    assert any(c["loai"] == "tu_mo_ho" for c in ra["canh_bao_chat_luong"])


def test_co_tat_ket_qua_y_cu(bo):
    """TC-M2-03-05 — cờ TẮT: không có khoá mới nào trong kết quả."""
    ag, r, ctx = bo()
    ra = r.get("store.req_create").fn(ctx, id="FR-01", loai="FR",
                                      text="Hệ thống phải chạy nhanh và ổn định",
                                      source_quote="anh nói: nhanh với ổn định",
                                      explain=EX)
    assert "canh_bao_chat_luong" not in ra, sorted(ra)
    assert ag.store.get("FR-01") is not None


def test_REQ_tot_khong_bi_keu(bo):
    """TC-M2-03-06 — ca âm: một yêu cầu viết đúng thì danh sách cảnh báo RỖNG.

    Ca này quan trọng hơn mấy ca bắt lỗi: một bộ dò kêu cả vào câu đúng sẽ bị tắt đi,
    và lúc ấy nó không còn bắt được gì nữa.
    """
    ag, r, ctx = bo(req_chat_luong=True)
    ra = r.get("store.req_create").fn(
        ctx, id="FR-01", loai="FR",
        text="Tốc độ chép tệp đạt ≥ 5 MB/s qua LAN 100 Mbps",
        criteria="đo bằng 10 lần chép tệp 200 MB, trung vị ≥ 5 MB/s",
        source_quote="anh nói: chép tệp phải được 5 MB/s trở lên",
        explain=EX)
    assert ra["canh_bao_chat_luong"] == [], ra["canh_bao_chat_luong"]


def test_it_nhat_2_lan_la_do_duoc_khong_phai_mo_ho():
    """Lượng từ đứng trước một con số thì KHÔNG mơ hồ.

    Đo trên 37 REQ thật: câu *"in đúng chuỗi ra UART ít nhất 2 lần"* bị bản đầu của bộ dò
    kêu vì từ "ít". Đó là một mức đo được. Một bộ dò kêu oan thì bị tắt đi, và lúc ấy nó
    không bắt được gì nữa — nên ở đây thà bỏ sót hơn kêu oan.
    """
    from eide.yeu_cau import tu_mo_ho

    assert tu_mo_ho("in đúng chuỗi ra UART ít nhất 2 lần") == []
    assert tu_mo_ho("gửi nhiều hơn 10 gói mỗi giây") == []
    # Vẫn phải bắt khi nó thật sự là tính từ, không có con số nào theo sau.
    assert tu_mo_ho("Dùng ít RAM") == ["ít"]
    assert tu_mo_ho("hỗ trợ nhiều thiết bị") == ["nhiều"]
