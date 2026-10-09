# -*- coding: utf-8 -*-
"""M5-01 — tìm trong tài liệu: cả hệ thống chỉ có một phép `in` trên MỘT tài liệu.

`doc.read(tim=…)` lọc `tk in t.chu.lower()` — một phép chứa, không xếp hạng, và **chỉ trên một
`doc_id`**. Nên ba câu hỏi rất thường gặp đều không trả lời được:

* *"chip nào trong các tài liệu đã nạp nói về pull-up I2C"* — phải gọi `doc.read` từng tài liệu
  một và tự so;
* *"tìm `VCC`"* trên một datasheet viết `Supply voltage` — ra **rỗng**, và rỗng ở đây đọc như
  *"tài liệu không có"*;
* *"đoạn nào liên quan NHẤT"* — không có khái niệm đó.

`grep -i "fts5|bm25|embedd|rerank"` trong `src/` trước M5-01 ra **0 kết quả**. Và có một dấu vết
của chuyện ấy: `memory/envelope.py` đã khai chính sách phong bì cho `"rag.ask"` — **một công cụ
không tồn tại**.

Thêm một chỗ: mở lại dự án thì `_lay_tai_lieu` gọi lại `_nap_theo_loai`, tức **chạy lại pypdf
trên toàn bộ PDF**. Chỉ mục lưu bền sửa luôn chuyện đó.
"""

from __future__ import annotations

import pytest

from lam_pdf import lam_pdf

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}

# Hai "datasheet" khác hãng, cố ý dùng HAI CÁCH GỌI khác nhau cho cùng một thứ.
DS_MCU = [
    ["ATmega328P", "Bang dac tinh dien"],
    ["Absolute maximum ratings", "Khong duoc vuot qua cac gioi han nay"],
    ["Supply voltage VDD min 1.8 V max 5.5 V", "I2C pull-up resistor 4.7 kOhm typical",
     "Operating frequency max 20 MHz"],
    ["Flash memory 32768 bytes", "SRAM 2048 bytes"],
]
DS_SENSOR = [
    ["MPU-6050 six axis sensor", "Dieu kien lam viec"],
    ["VCC 3.3 V nominal, 5 V tolerant on VLOGIC",
     "Start-up time 30 ms after power on"],
    ["I2C slave address 0x68 or 0x69", "Bus pull-up 2.2 kOhm recommended"],
]


@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-thu")
    return ag, ctx


def _nap(ag, ctx, ten: str, doc_id: str, trang: list[list[str]]):
    lam_pdf(ag.config.paths.project_root / ten, trang)
    r = ag.registry.run("doc.load", {"path": ten, "doc_id": doc_id,
                                     "nguon": "nha_san_xuat", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    return r


def _nap_ca_hai(ag, ctx):
    _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    _nap(ag, ctx, "sensor.pdf", "DS-SEN", DS_SENSOR)


# ===================================================== lớp chỉ mục
def test_ghi_chi_muc_va_tim_co_XEP_HANG(bo):
    """TC-M5-01-01 — tìm trên NHIỀU tài liệu, có xếp hạng, và hai cách gọi cùng một thứ đều
    tìm được.

    `VCC` và `Supply voltage` là cùng một thông số viết theo hai hãng. Một phép `in` trả rỗng
    cho một nửa số tài liệu, và rỗng ở đây đọc như *"tài liệu không có"* — đúng loại câu trả
    lời sai mà N1 không bắt được, vì nó không bịa gì cả.
    """
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)

    ra = CM.tim(ag.store, "VCC supply voltage", k=8)
    assert ra, "không tìm thấy gì"
    assert {d["doc_id"] for d in ra} >= {"DS-MCU", "DS-SEN"}, [d["doc_id"] for d in ra]
    # Xếp hạng: đoạn nói đúng về điện áp cấp phải đứng trước đoạn chỉ nhắc qua.
    dau = ra[0]
    assert "voltage" in dau["chu"].lower() or "vcc" in dau["chu"].lower(), dau["chu"][:120]
    # Điểm phải GIẢM dần — một danh sách không xếp hạng thì "kết quả đầu" không nghĩa gì.
    diem = [d["diem"] for d in ra]
    assert diem == sorted(diem, reverse=True), diem


def test_dong_nghia_VCC_ra_duoc_SUPPLY_VOLTAGE(bo):
    """Mở rộng truy vấn bằng bảng đồng nghĩa. Tài liệu MCU **không có chữ `VCC`** ở đâu cả —
    nó viết `Supply voltage VDD`. Tìm `VCC` mà không ra nó là bỏ sót đúng tài liệu cần."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    assert not any("VCC" in " ".join(d) for d in DS_MCU)

    ra = CM.tim(ag.store, "VCC", k=8)
    assert "DS-MCU" in {d["doc_id"] for d in ra}, [d["doc_id"] for d in ra]


def test_dong_nghia_start_up_ba_cach_viet(bo):
    """`start-up` · `startup` · `startup time` — ba cách viết, một thứ. Và phép tách từ của
    FTS5 cắt `start-up` thành hai token, nên không mở rộng thì `startup` không khớp."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    for tv in ("startup", "start-up time", "startup time"):
        ra = CM.tim(ag.store, tv, k=8)
        assert any("Start-up" in d["chu"] for d in ra), (tv, [d["chu"][:60] for d in ra])


def test_tim_loc_duoc_theo_doc_ids(bo):
    """Lọc theo tài liệu: người dùng hỏi "trong datasheet con cảm biến" thì không được trả
    về kết quả của con MCU."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    ra = CM.tim(ag.store, "pull-up", doc_ids=["DS-SEN"], k=8)
    assert ra and {d["doc_id"] for d in ra} == {"DS-SEN"}, [d["doc_id"] for d in ra]


def test_ghi_chi_muc_LAI_khong_nhan_doi(bo):
    """Nạp lại cùng một `doc_id` (tài liệu sửa, phiên bản mới) thì chỉ mục phải THAY, không
    cộng thêm — hai bản của một trang trong chỉ mục là hai kết quả cho một chỗ."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    n1 = CM.dem_chunk(ag.store, "DS-MCU")
    _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    assert CM.dem_chunk(ag.store, "DS-MCU") == n1, "chỉ mục nhân đôi sau khi nạp lại"


def test_o_bang_cung_vao_chi_muc(bo):
    """Đơn vị trích dẫn dạng HÀNG BẢNG mang chữ ở `o`, không ở `chu`. Bỏ `o` đi là bỏ chính
    phần datasheet đặt số vào — bảng đặc tính điện."""
    from eide.knowledge import chi_muc as CM
    from eide.knowledge.docs import TaiLieu, Trang

    ag, _ctx = bo
    tl = TaiLieu(doc_id="D-BANG", ten="b.pdf", duong_dan="/b.pdf", hash="h" * 16,
                 so_trang=1,
                 trang=[Trang(so=1, chu="", nhan="Bảng 4", loai_bang="thong_so",
                              o=["VDD", "1.8", "5.5", "V"],
                              cot=["Parameter", "Min", "Max", "Unit"])])
    CM.ghi_chi_muc(ag.store, tl)
    ra = CM.tim(ag.store, "VDD", k=5)
    assert ra and ra[0]["doc_id"] == "D-BANG", ra
    assert "VDD" in ra[0]["chu"] and "|" in ra[0]["chu"], ra[0]["chu"]


# ===================================================== công cụ doc.search
def test_doc_search_qua_cong_cu(bo):
    """TC-M5-01-02 — qua sổ công cụ, như tác tử gọi."""
    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    r = ag.registry.run("doc.search", {"truy_van": "pull-up"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_tai_lieu_da_tim"] == 2, r.data
    kq = r.data["ket_qua"]
    assert kq and all({"doc_id", "so", "trich_dan", "diem", "doan"} <= set(d) for d in kq)
    assert any("pull-up" in d["doan"].lower() for d in kq), [d["doan"][:60] for d in kq]
    # Đoạn trả về phải GỌN và phải chứa chỗ khớp — một trang 2 000 ký tự vào ngữ cảnh cho
    # mỗi kết quả là tám trang cho một phép tìm.
    assert all(len(d["doan"]) <= 650 for d in kq), [len(d["doan"]) for d in kq]


def test_doc_search_tran_k(bo):
    """`k` có trần 20. Một phép tìm trả 200 đoạn là một phép tìm không ai đọc."""
    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    r = ag.registry.run("doc.search", {"truy_van": "V", "k": 500}, ctx)
    assert r.ok and len(r.data["ket_qua"]) <= 20, len(r.data["ket_qua"])


def test_kho_rong_thi_noi_ro(bo):
    """TC-M5-01-04 — chưa nạp tài liệu nào là một chuyện KHÁC với "không tìm thấy".

    Hai câu ấy dẫn tới hai việc ngược nhau: một cái bảo đi nạp tài liệu, cái kia bảo nói với
    người dùng là tài liệu không có phần đó.
    """
    ag, ctx = bo
    r = ag.registry.run("doc.search", {"truy_van": "pull-up"}, ctx)
    assert not r.ok and r.error.code == "E2004", r
    assert "doc.load" in (r.error.alternatives or []), r.error.alternatives
    assert "chưa nạp" in r.error.message_vi.lower() or "chưa có tài liệu" in r.error.message_vi.lower()


def test_khong_tim_thay_KHAC_kho_rong(bo):
    """Đã có tài liệu mà không khớp thì `ok` + rỗng + nói rõ — không phải lỗi.

    Truy vấn ở đây là một CÂU TIẾNG VIỆT đầy đủ, cố ý: tác tử gọi `doc.search` bằng lời của
    người dùng, không bằng vài từ khoá. Và chính câu ấy tìm ra một lỗi thật — `khong` · `co` ·
    `trong` · `nao` khớp gần như mọi trang, nên `ket_qua` **không bao giờ rỗng**. Mà *"không
    khớp đoạn nào"* là tín hiệu duy nhất bảo tác tử dừng đoán; một tín hiệu không bao giờ nổ
    thì bằng không có.
    """
    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    r = ag.registry.run("doc.search", {"truy_van": "zzzqqq khong co trong tai lieu nao"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["ket_qua"] == []
    assert "không khớp" in r.data["note_vi"].lower(), r.data["note_vi"]
    # Và phải nói thẳng việc cần làm: nói với người dùng, ĐỪNG điền bằng số nhớ được.
    assert "đừng" in r.data["note_vi"].lower(), r.data["note_vi"]


def test_luoc_do_va_core_false(bo):
    """TC-M5-01-05 — `core=False` (chỉ hiện sau `tool.search`) và mô tả ≤ 400 ký tự (N-11)."""
    ag, _ctx = bo
    sp = ag.registry.get("doc.search")
    assert sp is not None and sp.core is False
    assert len(sp.summary_vi) <= 400, len(sp.summary_vi)


# ===================================================== chỉ mục SỐNG qua mở lại
def test_chi_muc_song_qua_mo_lai(bo, make_agent, monkeypatch):
    """TC-M5-01-03 — mở lại dự án thì tìm được NGAY, không phân tích lại PDF.

    Trước M5-01, `_lay_tai_lieu` gọi lại `_nap_theo_loai` mỗi lần mở lại — tức chạy pypdf trên
    toàn bộ PDF để trả lời một phép tìm. Monkeypatch cho `nap_tai_lieu` NỔ: nếu nó bị gọi thì
    ca này đỏ, nên "không phân tích lại" là một phép đo chứ không phải một lời hứa.
    """
    ag, ctx = bo
    _nap_ca_hai(ag, ctx)

    hai = make_agent([])
    from eide.knowledge import docs as docs_mod

    def _no(*a, **k):
        raise AssertionError("đã phân tích lại PDF — chỉ mục không sống qua mở lại")

    monkeypatch.setattr(docs_mod, "nap_tai_lieu", _no)
    from eide.loop import TurnContext

    ctx2 = TurnContext(config=hai.config, store=hai.store, ledger=hai.ledger,
                       eide_md=hai.eide_md, ids=hai.ids, registry=hai.registry,
                       emit=lambda c: None, history=hai.history, agent=hai, run_id="run-2")
    r = hai.registry.run("doc.search", {"truy_van": "pull-up"}, ctx2)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["ket_qua"], r.data


def test_migration_v5_len_duoc_va_xuong_duoc(du_an):
    """TC-M5-01-05 (phần lược đồ) — SCH-18: migration phải có đường LÙI.

    `CREATE TABLE IF NOT EXISTS` một mình biến mọi đổi lược đồ thành đổi không quay lại được.
    """
    from eide.store.db import SCHEMA_VERSION, Store

    st = Store(du_an / "kho.sqlite")
    assert SCHEMA_VERSION >= 5
    assert st.phien_ban_luoc_do == SCHEMA_VERSION

    def co_bang(ten: str) -> bool:
        return bool(st._db.execute(
            "SELECT 1 FROM sqlite_master WHERE name=?", (ten,)).fetchone())

    assert co_bang("doc_chunks")
    st.ha_cap(4)
    assert st.phien_ban_luoc_do == 4
    assert not co_bang("doc_chunks") and not co_bang("doc_fts")
    # Và dữ liệu cũ không bị chạm: ba bảng gốc còn nguyên.
    assert co_bang("events") and co_bang("artefacts") and co_bang("facts")
    st.nang_cap()
    assert st.phien_ban_luoc_do == SCHEMA_VERSION and co_bang("doc_chunks")


def test_khong_co_FTS5_thi_van_tim_duoc(bo, monkeypatch):
    """Dự phòng: SQLite không có FTS5 thì xếp hạng bằng số từ khoá khớp.

    Không phải chuyện lý thuyết — FTS5 là một module **biên dịch tuỳ chọn** của SQLite, và
    `doc.search` không được biến thành thứ chỉ chạy trên máy tôi. Thiếu nó thì nói rõ và rơi
    về đường cũ (N-10), không lỗi cứng.
    """
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    monkeypatch.setattr(ag.store, "co_fts", False)
    ra = CM.tim(ag.store, "pull-up resistor", k=8)
    assert ra, "đường dự phòng không trả về gì"
    assert all("diem" in d for d in ra)
    r = ag.registry.run("doc.search", {"truy_van": "pull-up"}, ctx)
    assert r.ok and r.data["ket_qua"]
    assert r.data["duong_xep_hang"] == "khong_fts", r.data["duong_xep_hang"]
    assert "KHÔNG phải BM25" in r.data["note_vi"], r.data["note_vi"]
    assert "KHÔNG có FTS5" in r.data["note_vi"], r.data["note_vi"]


def test_doc_load_HONG_chi_muc_thi_van_nap_duoc(bo, monkeypatch):
    """Lỗi chỉ mục KHÔNG được làm hỏng `doc.load`.

    Chỉ mục là tiện lợi; nạp tài liệu là việc chính. Đổi một phép tìm chậm lấy một tài liệu
    không nạp được là đổi sai chiều.
    """
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo

    def _no(*a, **k):
        raise RuntimeError("chỉ mục hỏng")

    monkeypatch.setattr(CM, "ghi_chi_muc", _no)
    seen: list = []
    ctx.emit = seen.append
    r = _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    assert r.ok
    assert any("chỉ mục" in str(getattr(c, "params", c)).lower() for c in seen), seen


def test_envelope_doi_khoa_rag_ask_thanh_doc_search():
    """`memory/envelope.py` khai chính sách cho `"rag.ask"` — một công cụ **không tồn tại**.

    Đó là dấu vết của một tính năng đã được nghĩ tới rồi bỏ dở, và nó nằm đúng chỗ dễ làm
    người đọc tin là có RAG. Nay khoá ấy trỏ về công cụ thật.
    """
    from eide.memory.envelope import CHINH_SACH

    assert "doc.search" in CHINH_SACH
    assert "rag.ask" not in CHINH_SACH


# ============================== năm chỗ phép phá sẽ chỉ ra là ca kiểm CHƯA chạm tới
def test_co_fts_PHAN_ANH_dung_bang_co_that(bo):
    """`Store.co_fts` phải nói đúng chuyện *"kho này CÓ bảng `doc_fts` hay không"*.

    Không hỏi `sqlite3.sqlite_version`: hai chuyện khác nhau, và một kho cũ có thể đã tạo bảng
    trước khi ai đó đổi bản SQLite. Đặt cứng `True` thì đường dự phòng chết; đặt cứng `False`
    thì BM25 không bao giờ chạy mà **không ai thấy** — kết quả vẫn trả về, chỉ xếp hạng tệ hơn.
    """
    ag, _ctx = bo
    co_bang = bool(ag.store._db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='doc_fts'").fetchone())
    assert ag.store.co_fts is co_bang


def test_chi_muc_FTS_duoc_do_du_lieu_vao(bo):
    """Chỉ mục FTS5 phải THẬT SỰ có dữ liệu.

    Nếu `ghi_chi_muc` quên ghi vào `doc_fts` thì phép tìm vẫn trả kết quả — nó rơi im lặng
    xuống đường dự phòng. Tức BM25 không chạy lần nào, và không ca kiểm nào kêu: một cơ chế
    có sẵn với đường dẫn tới nó đứt, đúng hình dạng cả đợt này đi vá.
    """
    ag, ctx = bo
    if not ag.store.co_fts:
        pytest.skip("máy này không có FTS5")
    _nap_ca_hai(ag, ctx)
    n_fts = ag.store._db.execute("SELECT COUNT(*) n FROM doc_fts").fetchone()["n"]
    from eide.knowledge import chi_muc as CM
    assert n_fts == CM.dem_chunk(ag.store), (n_fts, CM.dem_chunk(ag.store))


def test_nhan_cua_don_vi_cung_vao_chi_muc(bo):
    """`nhan` là đường tiêu đề (`"3.2 Electrical > Bảng 4"`). Người dùng hỏi *"bảng 4 nói gì"*
    thì chỉ `nhan` trả lời được — `chu` của một hàng bảng không chứa tên bảng."""
    from eide.knowledge import chi_muc as CM
    from eide.knowledge.docs import TaiLieu, Trang

    ag, _ctx = bo
    tl = TaiLieu(doc_id="D-NHAN", ten="b.pdf", duong_dan="/b.pdf", hash="h" * 16, so_trang=1,
                 trang=[Trang(so=1, chu="1.8 5.5", nhan="3.2 Dac tinh dien > Bang 4",
                              loai_bang="thong_so", o=["VDD"], cot=["Parameter"])])
    CM.ghi_chi_muc(ag.store, tl)
    ra = CM.tim(ag.store, "Bang 4", k=5)
    assert ra and ra[0]["doc_id"] == "D-NHAN", ra


def test_tran_chunk_cat_thi_van_nap_phan_dau(bo, monkeypatch):
    """Trần số chunk của một tài liệu. Một datasheet 800 trang là chuyện có thật."""
    from eide.knowledge import chi_muc as CM
    from eide.knowledge.docs import TaiLieu, Trang

    ag, _ctx = bo
    monkeypatch.setattr(CM, "TRAN_CHUNK", 3)
    tl = TaiLieu(doc_id="D-DAI", ten="d.pdf", duong_dan="/d.pdf", hash="h" * 16, so_trang=10,
                 trang=[Trang(so=i + 1, chu=f"trang so {i + 1} noi ve chuyen {i + 1}")
                        for i in range(10)])
    assert CM.ghi_chi_muc(ag.store, tl) == 3
    assert CM.dem_chunk(ag.store, "D-DAI") == 3


def test_truy_van_co_dau_GACH_NGANG_khong_thanh_phep_NOT(bo):
    """`pull-up` chưa bọc nháy kép thì FTS5 đọc `-` là toán tử **NOT**: truy vấn thành
    *"pull VÀ KHÔNG up"* — tức **ngược hẳn** ý người hỏi, và nó trả về kết quả nên không ai
    thấy là sai."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    ra = CM.tim(ag.store, "pull-up", k=8)
    assert ra, "truy vấn có dấu gạch ngang không trả về gì"
    assert any("pull-up" in d["chu"].lower() for d in ra), [d["chu"][:60] for d in ra]


def test_duong_xep_hang_noi_RA_khi_khong_phai_BM25(bo):
    """Phép phá tìm ra chỗ này, và nó là một lỗ thật.

    `pull-up` chưa bọc nháy kép thì FTS5 nổ `no such column: up`. Bản đầu **nuốt im lặng** rồi
    rơi xuống đường thô — nhưng `note_vi` vẫn khai là BM25, nên tác tử đọc một thứ tự xếp hạng
    thô mà tin là xếp hạng tốt. Nay `doc.search` khai thẳng `duong_xep_hang`.
    """
    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    if not ag.store.co_fts:
        pytest.skip("máy này không có FTS5")

    r = ag.registry.run("doc.search", {"truy_van": "pull-up"}, ctx)
    assert r.ok and r.data["ket_qua"]
    assert r.data["duong_xep_hang"] == "bm25", r.data["duong_xep_hang"]
    assert "KHÔNG phải BM25" not in r.data["note_vi"]

    # Và khi thật sự không khớp gì thì nói đúng lý do ấy, không khai là BM25.
    r2 = ag.registry.run("doc.search", {"truy_van": "zzzqqqwww"}, ctx)
    assert r2.ok and r2.data["ket_qua"] == []
    assert r2.data["duong_xep_hang"] == "khong_khop", r2.data["duong_xep_hang"]


# ============ tám chỗ nữa phép phá chỉ ra là DÀN DỰNG của ca kiểm chưa phân biệt được
def _co_fts5_tren_may() -> bool:
    """Máy này có FTS5 hay không — hỏi SQLite trực tiếp, KHÔNG hỏi `store.co_fts`.

    Hỏi `store.co_fts` thì ca kiểm tự vô hiệu hoá chính nó: phép phá *"migration không tạo
    `doc_fts`"* làm `co_fts` thành False, ca `skipif` theo nó sẽ **skip** thay vì **đỏ**.
    """
    import sqlite3

    c = sqlite3.connect(":memory:")
    try:
        c.execute("CREATE VIRTUAL TABLE t USING fts5(x)")
        return True
    except sqlite3.OperationalError:
        return False
    finally:
        c.close()


@pytest.mark.skipif(not _co_fts5_tren_may(), reason="SQLite của máy này không có FTS5")
def test_migration_TAO_bang_fts_khi_may_co_FTS5(du_an):
    """Máy có FTS5 thì migration **phải** tạo `doc_fts`. Không tạo thì BM25 không bao giờ
    chạy — và mọi phép tìm vẫn trả kết quả, chỉ xếp hạng tệ hơn, nên không ai thấy."""
    from eide.store.db import Store

    st = Store(du_an / "kho-fts.sqlite")
    assert st.co_fts is True
    assert st._db.execute(
        "SELECT 1 FROM sqlite_master WHERE name='doc_fts'").fetchone() is not None


def test_co_fts_thanh_FALSE_khi_bang_khong_con(du_an):
    """`co_fts` phải đọc TRẠNG THÁI THẬT của kho, không đặt cứng.

    Dựng đúng tình huống phân biệt được: gỡ bảng rồi mở lại kho. Đặt cứng `True` thì mọi phép
    tìm sẽ đâm vào một bảng không tồn tại.
    """
    from eide.store.db import Store

    p = du_an / "kho-go.sqlite"
    st = Store(p)
    st._db.execute("DROP TABLE IF EXISTS doc_fts")
    st._db.commit()
    st.close()
    assert Store(p).co_fts is False


def test_ghi_chi_muc_LAI_khong_nhan_doi_O_CA_HAI_BANG(bo):
    """Nạp lại không được nhân đôi ở **cả** `doc_chunks` lẫn `doc_fts`.

    Phép phá chỉ ra rằng ca trước không phân biệt được: `doc_chunks` có khoá chính `(doc_id,
    so)` nên `INSERT OR REPLACE` tự dọn, còn `doc_fts` **không có khoá chính** — bỏ phép
    `DELETE` thì một trang có hai bản trong chỉ mục FTS, tức một chỗ trả về hai kết quả.
    """
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    _nap(ag, ctx, "mcu.pdf", "DS-MCU", DS_MCU)
    if ag.store.co_fts:
        n = ag.store._db.execute(
            "SELECT COUNT(*) n FROM doc_fts WHERE doc_id='DS-MCU'").fetchone()["n"]
        assert n == CM.dem_chunk(ag.store, "DS-MCU"), (n, CM.dem_chunk(ag.store, "DS-MCU"))
    ra = CM.tim(ag.store, "pull-up resistor", k=20)
    khoa = [(d["doc_id"], d["so"]) for d in ra]
    assert len(khoa) == len(set(khoa)), khoa


def _tl(doc_id: str, trang: list[tuple[int, str]]):
    from eide.knowledge.docs import TaiLieu, Trang

    return TaiLieu(doc_id=doc_id, ten="x.pdf", duong_dan="/x.pdf", hash="h" * 16,
                   so_trang=len(trang),
                   trang=[Trang(so=so, chu=chu) for so, chu in trang])


def test_XEP_HANG_dung_chieu_chu_khong_chi_don_dieu(bo):
    """Phép phá *"trả thẳng bm25"* LỌT vì ca trước chỉ kiểm điểm **đơn điệu giảm**.

    `bm25()` trả số ÂM và càng âm càng khớp, nên `ORDER BY diem DESC` trên số thô ra **ngược
    hẳn** — mà danh sách vẫn "giảm dần", nên một phép kiểm đơn điệu không thấy gì. Phải kiểm
    **chiều liên quan**: trang nhắc từ khoá nhiều lần, trong một trang ngắn, phải đứng trước.
    """
    from eide.knowledge import chi_muc as CM

    ag, _ctx = bo
    CM.ghi_chi_muc(ag.store, _tl("D-X", [
        (1, "pullup pullup pullup pullup pullup"),                  # dày, ngắn
        (2, "chuyen khac " * 120 + " pullup " + "chuyen khac " * 120),  # một lần, rất dài
    ]))
    ra = CM.tim(ag.store, "pullup", k=5)
    assert len(ra) == 2, ra
    assert ra[0]["so"] == 1, [(d["so"], d["diem"]) for d in ra]


def test_duong_THO_cung_chia_theo_do_dai(bo, monkeypatch):
    """Đường dự phòng cũng phải chia theo độ dài — cùng ý với BM25.

    Không chia thì một trang 5 000 ký tự nhắc từ khoá một lần thắng một trang 50 ký tự nói
    đúng về nó, chỉ vì nó dài.
    """
    from eide.knowledge import chi_muc as CM

    ag, _ctx = bo
    # Trang DÀI đặt TRƯỚC: không thì hai điểm bằng nhau và phép sắp xếp phụ (theo `so`) đưa
    # trang ngắn lên đầu — ca kiểm xanh mà không đo được phép chia nào. Đúng cái bẫy mà tập
    # phá vừa chỉ ra ở bốn nhiệm vụ trước.
    CM.ghi_chi_muc(ag.store, _tl("D-T", [
        (1, "chuyen khac " * 400 + " pullup "),
        (2, "pullup 4.7 kOhm"),
    ]))
    monkeypatch.setattr(ag.store, "co_fts", False)
    ra = CM.tim(ag.store, "pullup", k=5)
    assert len(ra) == 2 and ra[0]["so"] == 2, [(d["so"], d["diem"]) for d in ra]


def test_tran_k_do_duoc_khi_co_HON_20_doan_khop(bo):
    """Trần `k` chỉ đo được khi có **hơn 20** đoạn khớp. Phép phá chỉ ra rằng ca trước xanh
    vì kho chỉ có 7 trang — bỏ trần đi cũng không đổi gì."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    CM.ghi_chi_muc(ag.store, _tl("D-N", [(i + 1, f"pullup trang {i + 1}") for i in range(30)]))
    assert len(CM.tim(ag.store, "pullup", k=500)) == 20
    r = ag.registry.run("doc.search", {"truy_van": "pullup", "k": 500}, ctx)
    assert r.ok and len(r.data["ket_qua"]) == 20, len(r.data["ket_qua"])


def test_dong_nghia_theo_CUM_hai_tu(bo):
    """Nhóm đồng nghĩa có cả thành viên **hai từ** (`"supply voltage"`), và phép dò phải nhìn
    cả cụm.

    Phép phá chỉ ra rằng ca `VCC` không đo được chuyện này: `vcc` là một token đơn nên nó khớp
    kiểu nào cũng được. Ca này truy vấn **chỉ bằng cụm** `supply voltage`, và tài liệu cần tìm
    chỉ viết `VCC`.
    """
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    _nap_ca_hai(ag, ctx)
    assert not any("supply" in " ".join(d).lower() for d in DS_SENSOR)

    ra = CM.tim(ag.store, "supply voltage", k=8)
    assert "DS-SEN" in {d["doc_id"] for d in ra}, [d["doc_id"] for d in ra]


def test_cua_so_quanh_CHO_KHOP_tren_trang_dai(bo):
    """Cửa sổ 600 ký tự phải bám chỗ khớp. Phép phá chỉ ra rằng ca trước xanh vì mọi trang
    dàn dựng đều ngắn hơn 600 ký tự — cắt kiểu nào cũng ra cả trang."""
    from eide.knowledge import chi_muc as CM

    ag, ctx = bo
    CM.ghi_chi_muc(ag.store, _tl(
        "D-DAI", [(1, "dau trang " * 200 + " PULLUP-4K7-RIENG " + "cuoi trang " * 200)]))
    r = ag.registry.run("doc.search", {"truy_van": "PULLUP-4K7-RIENG"}, ctx)
    assert r.ok and r.data["ket_qua"], r.data
    doan = r.data["ket_qua"][0]["doan"]
    assert "PULLUP-4K7-RIENG" in doan, doan[:80]
    assert len(doan) <= 650, len(doan)
