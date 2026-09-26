# -*- coding: utf-8 -*-
"""ING-E — hình, OCR, đa ngôn ngữ. EIDE-ING-43 §4.6, §4.7. Ca ING10, ING11.

Điều bộ này canh, một câu: **OCR sai không trông như sai.** Một PDF hỏng thì báo lỗi;
một OCR sai thì trả về chữ đọc được, có vẻ hợp lý, và một con số trong đó có thể là
`5.5` đọc từ `8.8`. Nên mọi đường ra đều phải mang điểm tin cậy và trần tầng.
"""

from __future__ import annotations

import pytest

from eide.knowledge.ocr import (BI_DANH_DA_NGU, NGUONG_TIN_CAY, TRAN_TANG_OCR,
                                khoa_tu_bi_danh, kiem_goi, nhan_ngon_ngu, ocr_anh,
                                tim_chu_thich)


# =========================================================================== ING11 ngôn ngữ
@pytest.mark.parametrize("chu,ma", [
    ("Điện áp hoạt động của chip là 3,3 V và nhiệt độ tối đa 85 độ", "vie"),
    ("Operating voltage is 3.3 V and maximum temperature 85 degrees", "eng"),
    ("工作电压为3.3V，工作温度最高85摄氏度", "chi_sim"),
    ("動作電圧は3.3Vです、カタカナもあります", "jpn"),
])
def test_ING11_nhan_dung_ngon_ngu(chu, ma):
    ng = nhan_ngon_ngu(chu)
    assert ng.ma == ma, f"{ng.to_dict()}"
    assert ng.vi_sao, "phải giải trình được vì sao kết luận thế"
    assert 0 < ng.do_chac <= 1


def test_nhan_ngon_ngu_khong_co_chu_thi_noi_khong_ro():
    ng = nhan_ngon_ngu("   \n  ")
    assert ng.ma == "" and ng.do_chac == 0.0
    assert "không có chữ" in ng.vi_sao


def test_kana_thang_han_khi_ca_hai_cung_co():
    """Tiếng Nhật có cả Hán lẫn Kana; tiếng Trung chỉ có Hán."""
    assert nhan_ngon_ngu("漢字とカタカナとひらがな").ma == "jpn"
    assert nhan_ngon_ngu("纯中文文本没有假名").ma == "chi_sim"


# =========================================================================== ING11 gói OCR
def test_ING11_thieu_goi_ngon_ngu_thi_NOI_THANG_khong_doc_bua():
    """Đọc tiếng Việt bằng mô hình tiếng Anh cho ra chữ nhìn như chữ mà SAI."""
    from eide.knowledge.ocr import goi_da_cai

    da_cai = goi_da_cai()
    duoc, vi_sao = kiem_goi("vie")
    if "vie" in da_cai:
        assert duoc
    else:
        assert not duoc
        assert "nhìn như chữ mà sai" in vi_sao
        assert "tesseract-lang" in vi_sao or "tesseract-ocr" in vi_sao, vi_sao


def test_ngon_ngu_la_thi_khong_doan_goi():
    duoc, vi_sao = kiem_goi("tieng-sao-hoa")
    assert not duoc and "gói OCR nào" in vi_sao


def test_ocr_thieu_goi_thi_tra_LOI_chu_khong_tra_chu_rong(tmp_path):
    from eide.knowledge.ocr import goi_da_cai

    if "vie" in goi_da_cai():
        pytest.skip("máy này có gói vie")
    p = tmp_path / "x.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n")
    kq = ocr_anh(p, ma_ngon_ngu="vie")
    assert kq.loi and not kq.chu, "thiếu gói thì phải báo lỗi, không trả chữ rỗng"


# =========================================================================== ING10 tin cậy
def test_ING10_OCR_khong_bao_gio_len_VANG():
    """§6 và TC044 — scan mờ thì tầng tối đa là BẠC, dù điểm có cao."""
    assert TRAN_TANG_OCR == "BAC"


def test_ING10_duoi_nguong_thi_BAT_BUOC_nguoi_ra():
    from eide.knowledge.ocr import KetQuaOcr

    kq = KetQuaOcr(chu="5.5 V", do_tin_cay=0.62, so_tu=2)
    assert kq.can_nguoi_ra
    assert kq.to_dict()["tang_toi_da"] == "BAC"

    tot = KetQuaOcr(chu="5.5 V", do_tin_cay=0.97, so_tu=2)
    assert not tot.can_nguoi_ra


def test_nguong_tin_cay_dung_nhu_tai_lieu():
    assert NGUONG_TIN_CAY == 0.8


def test_ocr_that_chay_het_duong_va_CHAM_DIEM(tmp_path):
    """Chạy tesseract thật — nhưng đo thứ LÀ VIỆC CỦA TA, không đo độ chính xác của
    tesseract.

    Ảnh phông nhỏ cho ra `voDmaxs5V` với điểm 0,16. Đó không phải lỗi của ta; việc của
    ta là **gắn cờ** cho người biết đừng tin. Nếu ca này đo "có đọc ra chữ VDD không"
    thì nó sẽ đỏ theo phông chữ của từng máy, và nó không nói gì về an toàn.
    """
    from eide.knowledge.ocr import goi_da_cai

    if "eng" not in goi_da_cai():
        pytest.skip("máy chưa có tesseract")
    from PIL import Image, ImageDraw

    anh = Image.new("RGB", (420, 90), "white")
    ImageDraw.Draw(anh).text((12, 30), "VDD max 5.5 V", fill="black")
    p = tmp_path / "bang.png"
    anh.save(str(p))

    kq = ocr_anh(p, ma_ngon_ngu="eng")
    assert not kq.loi, kq.loi
    assert kq.so_tu > 0, "phải đọc ra ít nhất một từ"
    assert 0 < kq.do_tin_cay <= 1, "phải có điểm tin cậy thật từ tesseract"

    # Ảnh mờ/phông nhỏ → điểm thấp → BẮT BUỘC người rà. Đây mới là điều đáng canh.
    if kq.do_tin_cay < NGUONG_TIN_CAY:
        assert kq.can_nguoi_ra
        assert any("xác nhận" in c for c in kq.canh_bao), kq.canh_bao
        assert any("điểm dưới" in c for c in kq.canh_bao), kq.canh_bao


# =========================================================================== hình
@pytest.mark.parametrize("chu,co", [
    ("Figure 4-2. Block diagram of the I2C peripheral", True),
    ("Hình 3.1: sơ đồ khối", True),
    ("Table 12 — Electrical characteristics", True),
    ("một đoạn văn bình thường", False),
])
def test_tim_chu_thich_hinh(chu, co):
    assert bool(tim_chu_thich(chu)) is co


def test_hinh_la_tang_DONG_khong_phai_BAC():
    """Đọc hình là suy đoán từ ảnh — khác hẳn trích từ lớp chữ."""
    from eide.knowledge.ocr import Hinh

    h = Hinh(so=1, don_vi="trang 12", chu_thich="Figure 4-2")
    d = h.to_dict()
    assert d["tang"] == "DONG"
    assert "suy đoán" in d["note_vi"]


def test_rut_hinh_tu_pdf_khong_nem_ngoai_le_khi_pdf_hong(tmp_path):
    from eide.knowledge.ocr import rut_hinh_tu_pdf

    p = tmp_path / "hong.pdf"
    p.write_bytes(b"%PDF-1.4 rac")
    ds, vi_sao = rut_hinh_tu_pdf(p, tmp_path / "ra")
    assert ds == [] and vi_sao


# =========================================================================== ING11 bí danh
@pytest.mark.parametrize("ten,khoa", [
    ("工作电压", "vdd.range"),
    ("电源电压", "vdd.range"),
    ("工作温度", "ta.range"),
    ("主频", "fmax"),
    ("điện áp hoạt động", "vdd.range"),
    ("Nhiệt độ hoạt động", "ta.range"),
    ("動作電圧", "vdd.range"),
])
def test_ING11_bi_danh_da_ngu_anh_xa_dung_khoa(ten, khoa):
    assert khoa_tu_bi_danh(ten) == khoa


def test_bi_danh_khop_trong_mot_cau_dai():
    assert khoa_tu_bi_danh("Bảng 4: 工作电压 (V)") == "vdd.range"


def test_ten_la_thi_tra_rong_khong_doan():
    assert khoa_tu_bi_danh("màu vỏ hộp") == ""
    assert khoa_tu_bi_danh("") == ""


def test_moi_bi_danh_deu_tro_ve_khoa_co_dang_chuan():
    import re

    for bd, khoa in BI_DANH_DA_NGU.items():
        assert re.fullmatch(r"[a-z0-9_]+(\.[a-z0-9_]+)*", khoa), (bd, khoa)


# =========================================================================== qua công cụ
def _ctx(agent, thay=None):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=(thay.append if thay is not None else (lambda c: None)),
                       history=agent.history, run_id="run-1")


def test_doc_language_qua_cong_cu(make_agent, tmp_path):
    import sys

    sys.path.insert(0, "tests")
    from lam_pdf import DATASHEET_ATMEGA, lam_pdf

    agent = make_agent([])
    p = agent.config.paths.project_root / "ds.pdf"
    lam_pdf(p, DATASHEET_ATMEGA)
    ctx = _ctx(agent)
    ex = {"summary": "nạp", "why": "để đọc", "sources": [], "diff_prev": "—",
          "next": "—", "confidence": "BAC"}
    agent.registry.run("doc.load", {"path": "ds.pdf", "doc_id": "DS",
                                    "nguon": "nha_san_xuat", "explain": ex}, ctx)
    r = agent.registry.run("doc.language", {"doc_id": "DS"}, ctx)
    assert r.ok and r.data["ngon_ngu"]["ma"] in ("eng", "vie")
    assert isinstance(r.data["goi_da_cai"], list)


def test_doc_figures_doi_tai_lieu_da_nap(make_agent):
    agent = make_agent([])
    r = agent.registry.run("doc.figures", {"doc_id": "CHUA-CO"}, _ctx(agent))
    assert not r.ok and "doc.load" in r.error.alternatives


def test_doc_figures_tu_choi_tai_lieu_khong_phai_pdf(make_agent, tmp_path):
    import docx

    agent = make_agent([])
    d = docx.Document()
    d.add_paragraph("xin chào")
    p = agent.config.paths.project_root / "a.docx"
    d.save(str(p))
    ctx = _ctx(agent)
    ex = {"summary": "nạp", "why": "để đọc", "sources": [], "diff_prev": "—",
          "next": "—", "confidence": "NGUOI"}
    agent.registry.run("doc.load", {"path": "a.docx", "doc_id": "W1",
                                    "nguon": "noi_bo", "explain": ex}, ctx)
    r = agent.registry.run("doc.figures", {"doc_id": "W1"}, ctx)
    assert not r.ok and "chỉ làm với PDF" in r.error.message_vi
