# -*- coding: utf-8 -*-
"""M5-04 — PDF có BẢNG thì đọc theo bảng, không đọc theo dòng chữ.

Vì sao việc này đáng làm: `_tu_hang_bang` đã tồn tại từ trước và nó tồn tại vì một lý do
đo được — datasheet đặt **đơn vị ở cột riêng**, nên nối cả hàng thành một dòng chữ rồi tìm
"số kèm đơn vị" sẽ không bao giờ khớp. Nhưng đường duy nhất cấp `o`/`cot` cho nó là Office.
PDF — đúng định dạng mà mọi datasheet thật dùng — đi đường theo dòng: `nap_tai_lieu` dựng
`Trang(i + 1, p.extract_text())` và **không bao giờ** đặt `o`/`cot`.

Đây lại đúng hình dạng "cơ chế có sẵn, đường dẫn tới nó đứt" đã lặp suốt dự án này.
"""
from __future__ import annotations

import pytest

from eide.knowledge import docs as docs_mod
from lam_pdf import DATASHEET_ATMEGA, lam_pdf, lam_pdf_bang

pdfplumber = pytest.importorskip("pdfplumber")


@pytest.fixture
def bat_co(monkeypatch):
    monkeypatch.setenv("EIDE_FEATURE_PDF_BANG", "1")


# =========================================================================== TC-M5-04-01
def test_bang_thong_so_doc_theo_cot(tmp_path, bat_co):
    """TC-M5-04-01 — bảng Electrical characteristics cho `vdd.min` VÀ `vdd.max`.

    Hàng `VDD | 1.8 | | 5.5 | V` phải ra HAI Fact mang đúng hậu tố của cột, và đơn vị `V`
    phải lấy từ **cột Unit** — không từ chữ trên dòng.
    """
    p = lam_pdf_bang(tmp_path / "ds.pdf", [(
        "Electrical characteristics",
        ["Parameter", "Min", "Typ", "Max", "Unit"],
        [["VDD", "1.8", "", "5.5", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BANG")
    uv = docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")
    theo = {f.khoa: f for f in uv}
    assert "vdd.min" in theo and "vdd.max" in theo, sorted(theo)
    assert theo["vdd.min"].gia_tri == 1.8 and theo["vdd.min"].don_vi == "V"
    assert theo["vdd.max"].gia_tri == 5.5 and theo["vdd.max"].don_vi == "V"


def test_trich_dan_tro_dung_hang_bang(tmp_path, bat_co):
    """Trích dẫn phải nói được **hàng nào của bảng nào** — N1: người mở tệp ra tìm được chỗ.

    "trang 1" cho cả một trang bảng là một trích dẫn không kiểm được: một trang datasheet
    có hàng chục hàng, và con số 5.5 V chỉ nằm ở một hàng.
    """
    p = lam_pdf_bang(tmp_path / "ds.pdf", [(
        "Electrical characteristics",
        ["Parameter", "Min", "Max", "Unit"],
        [["VDD", "1.8", "5.5", "V"], ["ICC", "", "1.5", "mA"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BANG")
    hang = [t for t in tl.trang if t.o]
    assert hang, "không Trang nào là hàng bảng"
    nhan = hang[0].nhan
    assert "Bảng 1" in nhan and "hàng 1" in nhan, nhan
    assert "Electrical characteristics" in nhan, nhan


def test_so_trang_chu_cu_KHONG_doi(tmp_path, bat_co):
    """Các `Trang` chữ cũ giữ nguyên `so` = 1..N.

    Kế hoạch cấm đổi chúng, và lý do là mọi Fact đã nằm trong kho đều mang `trang = <số ấy>`.
    Đổi cách đánh số là làm sai **trích dẫn của dữ liệu cũ**, mà dữ liệu cũ không ai sửa lại.
    """
    p = lam_pdf_bang(tmp_path / "ds.pdf", [
        ("Electrical characteristics", ["Parameter", "Max", "Unit"], [["VDD", "5.5", "V"]]),
        ("Pin description", ["Pin", "Function", "Direction"], [["PB5", "SCK", "Output"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BANG")
    chu = [t for t in tl.trang if not t.o]
    assert [t.so for t in chu] == [1, 2], [t.so for t in chu]
    # Khẳng định này TRƯỚC phép kiểm dưới: không có hàng bảng nào thì `all(... if t.o)`
    # đúng vô điều kiện, và ca kiểm sẽ xanh mà chưa chạm tới dòng nó tưởng đang canh.
    hang = [t for t in tl.trang if t.o]
    assert len(hang) == 2, [t.nhan for t in hang]
    # Hàng bảng mang số KHÁC, để không hai đơn vị trích dẫn nào trùng số.
    so = [t.so for t in tl.trang]
    assert len(so) == len(set(so)), so
    assert all(t.so > 10000 for t in hang), [t.so for t in hang]


# =========================================================================== TC-M5-04-02
def test_abs_max_khac_operating(tmp_path, bat_co):
    """TC-M5-04-02 — "max tuyệt đối" và "max khi chạy" là HAI thông số, không phải một.

    `Absolute maximum ratings` là ngưỡng **phá hỏng chip**; `Recommended operating
    conditions` là ngưỡng **chạy đúng**. Gộp chúng vào cùng khoá `vdd.max` thì hoặc hệ thống
    báo hai tài liệu mâu thuẫn (trong khi cả hai đều đúng), hoặc một con số 4,0 V ghi đè
    3,6 V và mọi phép kiểm sau đó cho chip chạy ngoài vùng nhà sản xuất bảo đảm.
    """
    p = lam_pdf_bang(tmp_path / "ds.pdf", [
        ("Absolute maximum ratings", ["Parameter", "Max", "Unit"], [["VDD", "4.0", "V"]]),
        ("Recommended operating conditions",
         ["Parameter", "Min", "Max", "Unit"], [["VDD", "1.7", "3.6", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BANG")
    theo = {f.khoa: f.gia_tri for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")}
    assert theo.get("vdd.abs_max") == 4.0, sorted(theo)
    assert theo.get("vdd.max") == 3.6, sorted(theo)


def test_abs_max_KHONG_bi_bao_lech_voi_max(tmp_path, bat_co):
    """Và vì chúng là hai khoá, `doi_chieu_cheo` KHÔNG được báo lệch.

    Đây là vế đo được của ca trên: trước M5-04, hai bảng ấy cho hai giá trị cùng khoá
    `vdd.max`, nên hệ thống báo một mâu thuẫn **không tồn tại** — và N1 chỉ còn nghĩa khi
    những lần nó kêu lên đều là lần đáng kêu.
    """
    from eide.knowledge.compare import doi_chieu_cheo

    p = lam_pdf_bang(tmp_path / "ds.pdf", [
        ("Absolute maximum ratings", ["Parameter", "Max", "Unit"], [["VDD", "4.0", "V"]]),
        ("Recommended operating conditions",
         ["Parameter", "Min", "Max", "Unit"], [["VDD", "1.7", "3.6", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BANG")
    facts = [{"subject": "chip:X", "key": f.khoa, "value": f.gia_tri, "unit": f.don_vi,
              "source": {"doc_id": "DS-BANG", "page": f.trang}, "tier": "BAC"}
             for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")]
    # Phải có ĐỦ HAI vế trước khi hỏi "có lệch không": `doi_chieu_cheo` trên một danh sách
    # rỗng cũng trả rỗng, nên không có khẳng định này thì ca kiểm xanh vì **không trích được
    # gì**, đúng cái nó định bác bỏ.
    khoa = {f["key"] for f in facts}
    assert {"vdd.abs_max", "vdd.max"} <= khoa, sorted(khoa)
    lech = [x for x in doi_chieu_cheo(facts) if x.get("key") == "vdd.max"]
    assert lech == [], lech


def test_khoa_abs_max_co_trong_KHOA_CHUAN():
    """Một khoá không có trong `KHOA_CHUAN` là một khoá không bề mặt nào gọi được tên.

    Bài học M5-05: đường bảng từng sinh ra `flash.max`/`fmax.max` — khoá đúng cú pháp mà
    **không chỗ nào đọc**, nên Fact vẫn trông hợp lệ trong khi nó vô dụng.
    """
    assert "vdd.abs_max" in docs_mod.KHOA_CHUAN


# =========================================================================== TC-M5-04-03
def test_pinout_pdf(tmp_path, bat_co):
    """TC-M5-04-03 — bảng Pin/Function/Direction trên PDF cho ra bản đồ chân."""
    p = lam_pdf_bang(tmp_path / "pinout.pdf", [(
        "Pin description",
        ["Pin", "Function", "Direction"],
        [["PB5", "SCK", "Output"], ["PC4", "SDA", "Bidirectional"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-CHAN")
    chan = docs_mod.trich_chan_ung_vien(tl)
    assert len(chan) >= 2, [c.so_chan for c in chan]
    theo = {c.so_chan: c for c in chan}
    # `_HUONG_VI` dịch "output" → "ra" (tiếng Việt), không → "out". Tra bảng thật chứ
    # không viết theo mong đợi của mình — đây là lỗi tôi mắc ở lượt viết ca kiểm này.
    assert "PB5" in theo and theo["PB5"].huong == "ra", theo["PB5"].huong
    assert "SCK" in theo["PB5"].chuc_nang


def test_loai_bang_suy_tu_TIEU_DE_COT(tmp_path, bat_co):
    """`loai_bang` phải suy từ tiêu đề cột, không từ phỏng đoán — ba loại, ba cách đọc.

    Và một bảng trình bày (Revision history) KHÔNG được nhận là bảng thông số: hàng của nó
    có số (`Rev 1.2`, ngày tháng), nên nhận bừa là cách sinh Fact rác mang trích dẫn thật.
    """
    p = lam_pdf_bang(tmp_path / "ba.pdf", [
        ("Electrical characteristics", ["Parameter", "Max", "Unit"], [["VDD", "5.5", "V"]]),
        ("Pin description", ["Pin", "Function", "Direction"], [["PB5", "SCK", "Output"]]),
        ("Register map", ["Offset", "Register", "Reset"], [["0x00", "CR1", "0x0000"]]),
        ("Revision history", ["Revision", "Date", "Changes"], [["1.2", "2024", "Initial"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS-BA")
    # Tra theo SỐ TRANG, không theo tên mục trong nhãn: `Revision history` **không** khớp mẫu
    # mục nào (có chủ ý — danh sách mục chỉ gồm những mục mà tên mục đổi nghĩa con số), nên
    # nhãn của nó không có phần mục để tách ra. Lọc theo nhãn ở đây là lọc sai, và nó sẽ trả
    # về một từ điển trông hợp lý — đúng cái bẫy "lọc sai ra số đẹp".
    hang = {t.so // 10000: t for t in tl.trang if t.o}
    assert sorted(hang) == [1, 2, 3, 4], sorted(hang)
    assert hang[1].loai_bang == "thong_so", hang[1].nhan
    assert hang[2].loai_bang == "chan", hang[2].nhan
    assert hang[3].loai_bang == "thanh_ghi", hang[3].nhan
    assert hang[4].loai_bang == "", (hang[4].nhan, hang[4].cot)
    # Và bảng trình bày ấy KHÔNG được sinh Fact nào, dù hàng của nó có số (`1.2`, `2024`).
    fact = docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")
    assert all(f.trang // 10000 != 4 for f in fact), [(f.khoa, f.trang) for f in fact]


# =========================================================================== TC-M5-04-04
def test_co_tat_y_nhu_cu(tmp_path):
    """TC-M5-04-04 — cờ TẮT thì nạp y như cũ: 3 trang, không `Trang` nào có `o`.

    N-4: cờ này đổi **tập Fact tác tử nhìn thấy**, nên nó phải TẮT mặc định. Và "y như cũ"
    nghĩa là không thêm một đơn vị trích dẫn nào, không chỉ là không thêm Fact.
    """
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS40002061B")
    assert tl.so_trang == 3
    assert all(not t.o and not t.cot for t in tl.trang)


def test_co_tat_thi_KHONG_MO_pdfplumber(tmp_path, monkeypatch):
    """Cờ tắt thì cũng không được **mở tệp** bằng pdfplumber.

    Một phép đo thừa trên mỗi lần nạp tài liệu là chi phí thật: `pdfplumber` dựng lại cây
    đối tượng của cả tệp. Ca kiểm này canh chuyện ấy bằng cách làm chính hàm mở tệp nổ —
    nếu đường bảng vẫn chạy khi cờ tắt thì nó sẽ nổ ở đây, không im lặng tốn thời gian.
    """
    from eide.knowledge import bang_pdf

    def no(*a, **k):
        raise AssertionError("cờ TẮT mà vẫn mở pdfplumber")

    monkeypatch.setattr(bang_pdf, "bang_tu_tai_lieu", no)
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    assert docs_mod.nap_tai_lieu(p, doc_id="DS").so_trang == 3


# =========================================================================== TC-M5-04-05
def test_thieu_thu_vien_khong_sap(tmp_path, bat_co, monkeypatch):
    """TC-M5-04-05 — bật cờ mà máy không có `pdfplumber` thì nạp vẫn chạy theo đường cũ.

    `pdfplumber` là phụ thuộc TUỲ CHỌN (N-10). Một cờ bật trên máy thiếu thư viện phải
    xuống đường dự phòng, không được làm `doc.load` đổ — vì lúc ấy tác tử mất cả tài liệu,
    không chỉ mất phần bảng.
    """
    from eide.knowledge import bang_pdf

    monkeypatch.setattr(bang_pdf, "_nap_pdfplumber",
                        lambda: (_ for _ in ()).throw(ImportError("không có pdfplumber")))
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS40002061B")
    assert tl.so_trang == 3
    assert all(not t.o for t in tl.trang)
    assert docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X"), "đường cũ phải vẫn trích được"


def test_thieu_thu_vien_thi_NOI_RA(tmp_path, bat_co, monkeypatch):
    """Và nó phải NÓI RA một lần, không im lặng.

    Im lặng ở đây là ca N6 kinh điển: người bật cờ nghĩ đang đọc bảng, hệ thống đang đọc
    dòng chữ, và cả hai đều báo `ok`. Bài học DEV-362 nguyên văn: "không thấy gì" không kèm
    phạm vi sẽ được đọc thành "không có gì".
    """
    from eide.knowledge import bang_pdf

    monkeypatch.setattr(bang_pdf, "_nap_pdfplumber",
                        lambda: (_ for _ in ()).throw(ImportError("x")))
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    chu = " ".join(getattr(tl, "ghi_chu", []) or [])
    assert "pdfplumber" in chu, getattr(tl, "ghi_chu", None)


# =========================================================================== bang_pdf đơn vị
def test_bang_tu_trang_tra_RONG_khi_trang_khong_co_bang(tmp_path):
    """Trang không vẽ khung bảng nào → 0 hàng bảng, và đó là con số ĐÚNG.

    Ca này tồn tại để con số của ca trên nói được điều gì: nếu `bang_tu_tai_lieu` trả hàng
    cho một trang chỉ có chữ thì nó đang dò bừa theo khoảng trắng, và bảng "đọc được" của
    nó là bảng nó tự dựng ra.
    """
    from eide.knowledge.bang_pdf import bang_tu_tai_lieu

    p = lam_pdf(tmp_path / "chu.pdf", DATASHEET_ATMEGA)
    assert bang_tu_tai_lieu(p) == []


def test_tieu_de_muc_lay_dong_GAN_NHAT_phia_tren(tmp_path):
    """Ngữ cảnh mục lấy dòng khớp mẫu gần nhất **phía trên** bảng, không phải dòng đầu trang.

    Một trang datasheet thật có nhiều mục. Lấy dòng đầu trang thì bảng thứ hai mang nhãn của
    mục thứ nhất — và với M5-04 thì nhãn ấy quyết định `vdd.max` hay `vdd.abs_max`, tức một
    nhãn sai làm ngưỡng phá hỏng chip thành ngưỡng chạy.
    """
    from eide.knowledge.bang_pdf import tieu_de_gan_nhat

    chu = ("Absolute maximum ratings\nVDD 4.0 V\n"
           "Recommended operating conditions\nVDD 3.6 V\n")
    assert tieu_de_gan_nhat(chu, "VDD 3.6 V") == "Recommended operating conditions"
    assert tieu_de_gan_nhat(chu, "VDD 4.0 V") == "Absolute maximum ratings"


def test_bang_khong_co_tieu_de_muc_thi_nhan_KHONG_bia(tmp_path, bat_co):
    """Bảng không nằm dưới mục nào khớp mẫu → nhãn chỉ nói trang và số bảng, không bịa tên.

    Bịa một tên mục là bịa một trích dẫn, và trích dẫn bịa còn tệ hơn không có trích dẫn:
    nó mời người đọc đi tìm một mục không tồn tại rồi kết luận hệ thống nói đúng.
    """
    p = lam_pdf_bang(tmp_path / "x.pdf", [(
        "Table 7-3",  # không khớp mẫu mục nào
        ["Parameter", "Max", "Unit"], [["VDD", "5.5", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    hang = [t for t in tl.trang if t.o]
    assert hang
    assert "Bảng 1" in hang[0].nhan and "trang 1" in hang[0].nhan
    for xau in ("absolute", "recommended", "electrical"):
        assert xau not in hang[0].nhan.lower(), hang[0].nhan


def test_co_PDF_BANG_co_ten_va_mac_dinh_TAT():
    """Cờ phải có tên trong `Features` và mặc định TẮT (N-4)."""
    import dataclasses

    from eide.config import Features

    f = {x.name: x for x in dataclasses.fields(Features)}
    assert "pdf_bang" in f, sorted(f)
    assert f["pdf_bang"].default is False
    assert Features().bat("pdf_bang") is False


# ============ hai chỗ đo trên 21 PDF THẬT của repo chỉ ra (10/10/2026)
def test_bo_hang_toan_MA_GLYPH_tho():
    """`(cid:55)(cid:75)(cid:82)` không phải chữ — nó là số hiệu glyph.

    `pdfplumber` trả dạng này khi phông của trang không có bảng `ToUnicode`. Đo trên 21 PDF
    thật của repo: **14 trong 150** hàng bảng tìm được là rác dạng ấy. Để chúng vào kho thì
    chúng thành **đơn vị trích dẫn**, và tác tử sẽ trích dẫn một đoạn không ai đọc được —
    rồi N1 ("mọi con số truy về một trích dẫn kiểm được") mất nghĩa đúng ở chỗ nó cần nhất.
    """
    from eide.knowledge.bang_pdf import _la_rac

    assert _la_rac("(cid:55)(cid:75)(cid:82)(cid:88)")
    assert _la_rac("", "(cid:50)(cid:69)(cid:86)(cid:3)(cid:20)", "")
    # Và chữ thật KHÔNG bị nhận là rác, kể cả khi có ngoặc và số.
    assert not _la_rac("VDD (max)", "5.5", "V")
    assert not _la_rac("Parameter", "Min", "Max", "Unit")
    assert not _la_rac("")


def test_bo_bang_co_it_hon_HAI_tieu_de_cot():
    """Khung trình bày có viền cũng ra "bảng" — nhưng nó không có ngữ nghĩa cột.

    Đo được trên dữ liệu thật: một "bảng" tiêu đề `['', '', '', 'Green)', 'Sáng, 1: Tắt)']`.
    Đọc theo cột là toàn bộ lý do của đường này, nên không có hai tên cột thì không có gì để
    đọc — và nhận bừa là cách sinh đơn vị trích dẫn rác mang nhãn thật.
    """
    from eide.knowledge.bang_pdf import COT_TOI_THIEU

    assert COT_TOI_THIEU == 2


def test_khung_mot_cot_KHONG_thanh_hang_bang(tmp_path, bat_co):
    """Và đo qua cả đường nạp: bảng chỉ có một tiêu đề cột → 0 hàng bảng."""
    p = lam_pdf_bang(tmp_path / "khung.pdf", [(
        "Electrical characteristics", ["Ghi chú", "", ""],
        [["Chỉ dùng cho bản A", "", ""]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert [t.nhan for t in tl.trang if t.o] == []


def test_hang_bang_mang_RAC_bi_bo_qua_hang_SACH_thi_giu(tmp_path, bat_co):
    """Bỏ TỪNG HÀNG rác, không bỏ cả bảng: một bảng có hàng đọc được và hàng không là
    hình dạng có thật — phông của một ô có thể khác phông của ô khác trong cùng bảng."""
    from eide.knowledge import bang_pdf

    goc = bang_pdf._sach

    def ban(o):
        s = goc(o)
        return "(cid:20)(cid:21)(cid:22)(cid:23)" if s == "ICC" else s

    p = lam_pdf_bang(tmp_path / "ds.pdf", [(
        "Electrical characteristics", ["Parameter", "Max", "Unit"],
        [["VDD", "5.5", "V"], ["ICC", "1.5", "mA"]])])
    import pytest as _p
    with _p.MonkeyPatch.context() as mp:
        mp.setattr(bang_pdf, "_sach", ban)
        tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    hang = [t for t in tl.trang if t.o]
    assert len(hang) == 1, [t.o for t in hang]
    assert hang[0].o[0] == "VDD"


# ============ mười một lỗ mà tập phép phá chỉ ra (lượt đầu 17/29)
def test_bang_co_cot_Pin_ma_KHONG_co_Function_thi_khong_la_bang_chan():
    """Hai vế, và ca cũ chỉ đo được một.

    Bản mẫu cũ có đủ cả `Pin` và `Direction`, nên bỏ vế thứ hai đi cũng không đổi kết quả —
    ca kiểm xanh mà chưa phân biệt được "có cả hai" với "có một". Một bảng `Pin | Package`
    (bảng đóng gói) nhận thành bản đồ chân sẽ sinh ra những chân có net rỗng, hướng rỗng.
    """
    from eide.knowledge.bang_pdf import loai_bang_tu_cot

    assert loai_bang_tu_cot(["Pin", "Package"]) == ""
    assert loai_bang_tu_cot(["Pin", "Function"]) == "chan"


def test_bang_co_Offset_ma_KHONG_co_Reset_thi_khong_la_bang_thanh_ghi():
    """Cùng hình dạng: `Offset | Description` là một bảng mục lục, không phải register map."""
    from eide.knowledge.bang_pdf import loai_bang_tu_cot

    assert loai_bang_tu_cot(["Offset", "Description"]) == ""
    assert loai_bang_tu_cot(["Offset", "Register", "Reset"]) == "thanh_ghi"


def test_cham_TRAN_hang_bang_thi_DUNG_va_NOI_RA(tmp_path, bat_co, monkeypatch):
    """Trần số hàng bảng phải thật sự chặn, và chạm trần phải NÓI RA.

    Mỗi hàng bảng là một đơn vị trích dẫn nằm trong `TaiLieu`, tức nằm trong bộ nhớ của mọi
    lượt sau. Một trần không ai canh thì không phải trần (DEV-254). Và cắt im lặng ở đây
    đọc thành *"tài liệu chỉ có bấy nhiêu bảng"* — một con số sai mang vẻ đầy đủ.
    """
    from eide.knowledge import bang_pdf

    monkeypatch.setattr(bang_pdf, "TRAN_HANG", 2)
    p = lam_pdf_bang(tmp_path / "nhieu.pdf", [(
        "Electrical characteristics", ["Parameter", "Max", "Unit"],
        [["VDD", "5.5", "V"], ["ICC", "1.5", "mA"], ["IOL", "40", "mA"],
         ["VIH", "3.0", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert len([t for t in tl.trang if t.o]) == 2
    assert any("trần" in g for g in tl.ghi_chu), tl.ghi_chu


def test_tieu_de_cot_toan_RAC_thi_bo_CA_BANG(tmp_path, bat_co, monkeypatch):
    """Hai lớp lọc rác độc lập, nên phải có ca riêng cho LỚP TRÊN.

    Nếu chỉ có ca cho lớp hàng thì tháo riêng lớp tiêu đề không đổi gì — bảng nào có tiêu đề
    rác thì hàng của nó cũng rác, nên lớp dưới dọn hết. Ca này dựng đúng hình dạng mà lớp
    dưới KHÔNG dọn được: tiêu đề rác, hàng sạch. Tiêu đề rác nghĩa là không biết cột nào là
    cột gì — đọc theo cột lúc ấy là đọc theo thứ tự ngẫu nhiên.
    """
    from eide.knowledge import bang_pdf

    goc = bang_pdf._sach

    def ban(o):
        s = goc(o)
        return "(cid:51)(cid:52)(cid:53)(cid:54)" if s == "Parameter" else s

    monkeypatch.setattr(bang_pdf, "_sach", ban)
    p = lam_pdf_bang(tmp_path / "rac.pdf", [(
        "Electrical characteristics", ["Parameter", "Max", "Unit"],
        [["VDD", "5.5", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert [t.o for t in tl.trang if t.o] == []


def test_sach_GOP_khoang_trang_trong_mot_o():
    """Một ô bảng có hai dòng chữ thì `pdfplumber` trả `"Supply\\nvoltage"`.

    Giữ ngắt dòng trong ô làm hai chuyện hỏng: mẫu tên neo `^\\s*V\\s*DD` vẫn khớp nhưng
    `chuan_hoa` nhận một chuỗi có `\\n`, và `chu` của hàng (chính là trích đoạn) có ngắt dòng
    giữa câu. Ca này đo thẳng vào dòng ấy — bản mẫu PDF của bộ kiểm đặt mỗi ô một dòng, nên
    không bản mẫu nào chạm tới nó.
    """
    from eide.knowledge.bang_pdf import _sach

    assert _sach("Supply\nvoltage") == "Supply voltage"
    assert _sach("  VDD \t max  ") == "VDD max"
    assert _sach(None) == ""


def test_co_TAT_thi_tai_lieu_KHONG_co_ghi_chu_nao(tmp_path, monkeypatch):
    """Cờ TẮT thì đường bảng không chạy — và đo bằng `ghi_chu`, không bằng một ngoại lệ.

    Ca cũ của tôi dựng một hàm nổ `AssertionError` để canh chỗ này, và nó xanh vì **lý do
    sai**: `nap_tai_lieu` bắt `except Exception`, nên nó nuốt luôn `AssertionError` của ca
    kiểm rồi ghi một dòng `ghi_chu`. Phép phá "bỏ cửa cờ" vì thế vẫn LỌT. Đo đúng chỗ: cờ
    TẮT thì `ghi_chu` phải RỖNG — không một dòng nào nói về đường bảng.
    """
    from eide.knowledge import bang_pdf

    def no(*a, **k):
        raise AssertionError("cờ TẮT mà vẫn gọi đường bảng")

    monkeypatch.setattr(bang_pdf, "bang_tu_tai_lieu", no)
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert tl.so_trang == 3
    assert tl.ghi_chu == [], tl.ghi_chu


def test_so_trang_DEM_trang_chu_chu_khong_dem_hang_bang(tmp_path, bat_co):
    """`so_trang` là số trang của TỆP, không phải số đơn vị trích dẫn.

    Nó đi vào `to_canonical()` rồi vào hiện vật `doc:*`, và mọi bề mặt hiển thị *"tài liệu N
    trang"* đọc từ đó. Một PDF 2 trang báo "8 trang" là một con số người mở tệp ra bác bỏ
    được ngay — đúng loại sai mà N1 tồn tại để chặn.
    """
    p = lam_pdf_bang(tmp_path / "ds.pdf", [
        ("Electrical characteristics", ["Parameter", "Max", "Unit"],
         [["VDD", "5.5", "V"], ["ICC", "1.5", "mA"]]),
        ("Pin description", ["Pin", "Function"], [["PB5", "SCK"], ["PC4", "SDA"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert len([t for t in tl.trang if t.o]) == 4, "phải có 4 hàng bảng để con số dưới có nghĩa"
    assert tl.so_trang == 2, tl.so_trang
    assert tl.to_canonical()["pages"] == 2


def test_doc_bang_DO_thi_noi_ro_khong_phai_tep_khong_co_bang(tmp_path, bat_co, monkeypatch):
    """Một lỗi khi đọc bảng KHÁC với "tệp này không có bảng", và hai thứ ấy không được
    cùng một biểu hiện.

    Im lặng ở đây làm một tệp đọc hỏng trông y như một tệp không có bảng nào — và người bật
    cờ sẽ kết luận datasheet của mình "không có bảng", chứ không đi tìm lỗi.
    """
    from eide.knowledge import bang_pdf

    monkeypatch.setattr(bang_pdf, "bang_tu_tai_lieu",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("hỏng")))
    p = lam_pdf(tmp_path / "DS.pdf", DATASHEET_ATMEGA)
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    assert tl.so_trang == 3
    assert any("ValueError" in g for g in tl.ghi_chu), tl.ghi_chu
    assert any("KHÔNG phải" in g for g in tl.ghi_chu), tl.ghi_chu


def test_ten_thong_so_khop_tu_DAU_O_chu_khong_giua_cau(tmp_path, bat_co):
    """Mẫu tên của đường bảng neo `^`: nó đọc Ô TÊN, không đọc cả hàng.

    Datasheet thật viết điều kiện **vào trong ô tên**: `VOL (VDD = 5 V)`. Bỏ neo đi thì mẫu
    `vdd` — đứng TRƯỚC `vol` trong danh sách — khớp chữ `VDD` trong ngoặc, nên 0,9 V (một mức
    logic thấp) vào kho với khoá `vdd.max`: đúng thứ nguyên, đúng khoảng, sai thông số. Cả
    hai phanh của `hop_ly` đều không bắt được loại sai này.

    Bản mẫu trước của tôi đặt điều kiện ở **cột `Conditions`**, và phép phá vì thế LỌT: ô tên
    lấy từ cột `Parameter`, nên cột `Conditions` không tham gia phép khớp tên lần nào — ca
    kiểm xanh mà chưa chạm tới dòng nó tưởng đang canh.
    """
    p = lam_pdf_bang(tmp_path / "dk.pdf", [(
        "Electrical characteristics",
        ["Parameter", "Max", "Unit"],
        [["VOL (VDD = 5 V)", "0.9", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    khoa = {f.khoa for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")}
    assert "vol.max" in khoa, sorted(khoa)
    assert not any(k.startswith("vdd.") for k in khoa), sorted(khoa)


def test_bang_abs_max_chi_doi_cot_MAX_thanh_abs_max(tmp_path, bat_co):
    """Bảng `Absolute maximum ratings` cũng có cột Min (ví dụ −0,5 V), và cột ấy KHÔNG phải
    `abs_max`.

    Bản mẫu cũ của tôi chỉ có cột Max — một tập một phần tử, nên phép phá "mọi cột đều thành
    abs_max" không đổi được gì. Đây là lần thứ tám trong chiến dịch này chỗ LỌT nằm ở bản
    mẫu chứ không ở mã.
    """
    p = lam_pdf_bang(tmp_path / "am.pdf", [(
        "Absolute maximum ratings",
        ["Parameter", "Min", "Max", "Unit"],
        [["VDD", "-0.5", "4.0", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    theo = {f.khoa: f.gia_tri for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")}
    # Và cột Min của bảng ấy là `vdd.abs_min`, KHÔNG phải `vdd.min`: −0,5 V là ngưỡng phá
    # hỏng phía dưới, còn `vdd.min` nghĩa là "chạy được từ bao nhiêu volt". Đọc lẫn hai thứ
    # này sẽ nói chip chạy được từ −0,5 V.
    assert theo.get("vdd.abs_max") == 4.0, sorted(theo)
    assert theo.get("vdd.abs_min") == -0.5, sorted(theo)
    assert "vdd.min" not in theo, sorted(theo)


def test_abs_max_NGOAI_khoang_hop_ly_bi_chan(tmp_path, bat_co):
    """`vdd.abs_max` phải có khoảng hợp lý, như `vdd.max`.

    Thiếu một dòng trong `PHAM_VI_HOP_LY` thì `hop_ly` trả `True` vô điều kiện cho khoá ấy
    (*"chưa có khoảng cho khoá này thì không chặn"*) — và phép kiểm **khoảng** im lặng mất.
    Đúng hình dạng M5-05: khoá `fmax` có mẫu sinh ra nó mà bảng khoảng ghi `f.max`, nên phép
    kiểm tần số **chưa nổ lần nào**.
    """
    assert "vdd.abs_max" in docs_mod.PHAM_VI_HOP_LY
    p = lam_pdf_bang(tmp_path / "xa.pdf", [(
        "Absolute maximum ratings", ["Parameter", "Max", "Unit"],
        [["VDD", "4.0", "V"], ["VDDIO", "6000", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    theo = {f.khoa: f.gia_tri for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")}
    assert theo.get("vdd.abs_max") == 4.0, sorted(theo)
    assert "vddio.abs_max" not in theo, "6 000 V không phải điện áp cấp của một chip"


def test_khoang_cua_GOC_khoa_chi_chan_thu_KHONG_THE():
    """Phanh độ lớn chỉ được chặn thứ **không thể**, không chặn thứ hiếm.

    Biên dưới của `i2c.pullup` từng đặt ở 10 Ω theo thói quen *"pull-up I2C thường 1–10 kΩ"*,
    và một ca kiểm có từ trước bác ngay: ô bảng ghi `4R7` — **4,7 Ω**, một giá trị điện trở có
    thật. Chặn thứ hiếm là bỏ mất Fact thật, rồi tác tử phải hỏi người dùng một con số đang
    nằm sẵn trong datasheet.
    """
    from eide.knowledge.docs import hop_ly, pham_vi_cua

    assert hop_ly("i2c.pullup.typ", 4.7, "Ω"), "4,7 Ω là điện trở có thật"
    assert hop_ly("icc.min", 2e-8, "A"), "20 nA là dòng ngủ sâu có thật"
    assert hop_ly("vddio.max", 3.6, "V")
    # Và nó vẫn chặn thứ không thể.
    assert not hop_ly("vddio.max", 6000, "V")
    assert not hop_ly("i2c.pullup.typ", 5e8, "Ω")
    # Tra theo GỐC chỉ dùng khi không có khoá chính xác — dòng đã khai vẫn thắng.
    assert pham_vi_cua("vdd.min") == docs_mod.PHAM_VI_HOP_LY["vdd.min"]
    assert pham_vi_cua("vddio.max") == docs_mod.PHAM_VI_GOC["vddio"]
    assert pham_vi_cua("khong.co.khoa.nao") is None


def test_abs_min_duoc_mo_xuong_phia_AM():
    """`vdd.abs_min = −0,5 V` là một giá trị ĐÚNG, và khoảng của `vdd.min` sẽ bác nó.

    `PHAM_VI_HOP_LY["vdd.min"]` là `(0.5, 60)` — đúng cho "chạy được từ bao nhiêu volt", sai
    cho "phá hỏng từ bao nhiêu volt". Hai khoá, hai khoảng.
    """
    from eide.knowledge.docs import hop_ly, pham_vi_cua

    assert hop_ly("vdd.abs_min", -0.5, "V")
    assert not hop_ly("vdd.min", -0.5, "V"), "chạy được từ −0,5 V là vô nghĩa"
    assert pham_vi_cua("vdd.abs_min")[0] < 0
    assert pham_vi_cua("vdd.abs_max") == docs_mod.PHAM_VI_HOP_LY["vdd.abs_max"]


def test_bang_abs_max_KHONG_doi_cot_Typ(tmp_path, bat_co):
    """Chỉ hai BIÊN của bảng Absolute maximum là ngưỡng phá hỏng; một cột Typ thì không.

    Bản mẫu abs_max trước của tôi không có cột Typ, nên phép phá "mọi cột đều thành abs_*"
    LỌT — lại là một tập chỉ có hai phần tử, trong khi dòng mã nói về ba.
    """
    p = lam_pdf_bang(tmp_path / "t.pdf", [(
        "Absolute maximum ratings", ["Parameter", "Min", "Typ", "Max", "Unit"],
        [["VDD", "-0.5", "3.3", "4.0", "V"]])])
    tl = docs_mod.nap_tai_lieu(p, doc_id="DS")
    theo = {f.khoa: f.gia_tri for f in docs_mod.trich_fact_ung_vien(tl, thuc_the="chip:X")}
    assert theo.get("vdd.abs_min") == -0.5 and theo.get("vdd.abs_max") == 4.0, sorted(theo)
    assert theo.get("vdd.typ") == 3.3, sorted(theo)
    assert "vdd.abs_typ" not in theo, sorted(theo)


def test_THU_TU_tra_khoang_la_HOP_DONG_chu_khong_phai_trung_hop(monkeypatch):
    """Ba luật thứ tự của `pham_vi_cua`, ghim bằng bảng DỰNG RIÊNG.

    Phải dựng bảng riêng vì hai bảng số thật hiện **trùng nhau ở mọi khoá**: `vdd.abs_max`
    bằng `vdd.max`, `PHAM_VI_GOC["ta"]` bằng `PHAM_VI_HOP_LY["ta.max"]`, và `PHAM_VI_GOC` phủ
    đúng những gốc mà `PHAM_VI_HOP_LY` phủ. Trên dữ liệu trùng như thế, ba phép phá tháo ba
    luật khác nhau đều cho **cùng một con số** — tức ba luật ấy đang được bảo vệ bởi một sự
    tình cờ, không bởi một ca kiểm. Đây là lần thứ ba trong chiến dịch gặp hình dạng "hai vế
    tình cờ bằng nhau".
    """
    from eide.knowledge import docs as DD

    monkeypatch.setattr(DD, "PHAM_VI_HOP_LY", {
        "x.max": (1.0, 2.0),
        "x.abs_max": (3.0, 4.0),       # khoá CHÍNH XÁC, khác hẳn `x.max`
        "y.min": (1.0, 2.0),           # có dòng chính xác, KHÔNG có gốc trong PHAM_VI_GOC
    })
    monkeypatch.setattr(DD, "PHAM_VI_GOC", {
        "x": (5.0, 6.0),
        "a": (7.0, 8.0),
        "a.b": (9.0, 10.0),            # tiền tố DÀI, khác hẳn tiền tố ngắn
    })
    # 1 · khoá chính xác thắng tất — kể cả khi `x.max` cũng có dòng riêng
    assert DD.pham_vi_cua("x.abs_max") == (3.0, 4.0)
    # 2 · `abs_*` rút về khoá gốc rồi tra CHÍNH XÁC lần nữa, trước khi rơi xuống tiền tố.
    #     `y` không có gốc, nên đây là chỗ DUY NHẤT phân biệt được luật này: bỏ phép rút thì
    #     kết quả là `None` chứ không phải một khoảng khác.
    assert DD.pham_vi_cua("y.abs_min") == (-2.0, 2.0)
    # 3 · không có cả hai thì rơi xuống tiền tố DÀI NHẤT, và `abs_min` mở xuống phía âm
    assert DD.pham_vi_cua("x.abs_min") == (-6.0, 6.0)
    assert DD.pham_vi_cua("a.b.max") == (9.0, 10.0)
    assert DD.pham_vi_cua("a.c.max") == (7.0, 8.0)
