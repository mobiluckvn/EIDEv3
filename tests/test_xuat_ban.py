# -*- coding: utf-8 -*-
"""Tác tử làm ra tệp `.docx` / `.xlsx` / `.pdf` — `xuat_ban.py` và công cụ `doc.render`.

Bốn ca đầu là **hồi quy của những lỗi chỉ nhìn mới thấy**. Bản đầu chạy trót lọt cả ba định
dạng, mọi con số đều "hợp lý" — số đoạn, số bảng, số trang. Phải mở tệp PDF ra nhìn mới lộ:
dấu sao lọt ra giấy, một gạch đầu dòng vỡ làm đôi, tên tài liệu in hai lần. Số đo đúng, câu
hỏi sai.

Ca thứ năm là hồi quy của một lỗi **mất dữ liệu**, và nó không lộ ra ở tệp nó tạo mà ở một tệp
bên cạnh — thứ không ai nghĩ tới mà đi kiểm.
"""

from __future__ import annotations

import pytest

from eide.xuat_ban import (doc_lai_docx, doc_lai_xlsx, doc_markdown, render, sang_docx,
                           sang_xlsx, tach_chu)

docx = pytest.importorskip("docx")
openpyxl = pytest.importorskip("openpyxl")


def _chu_trong_docx(p) -> str:
    tl = docx.Document(str(p))
    ra = [x.text for x in tl.paragraphs]
    for b in tl.tables:
        for h in b.rows:
            ra += [o.text for o in h.cells]
    return "\n".join(ra)


# ======================================================== bốn lỗi chỉ NHÌN mới thấy
def test_dam_long_trong_nghieng_khong_lam_lot_dau_sao(tmp_path):
    """`*Đề tài: **X** · Y*` từng in ra giấy nguyên dấu `*` ở đầu.

    Bản đầu quét ba kiểu bằng một `finditer`: nhánh hai-sao khớp trước, nên cặp một-sao bọc
    ngoài mất cặp đóng và dấu sao thành chữ.
    """
    kieu = {c: sorted(k) for c, k in tach_chu("*Đề tài: **Phát triển PM** · Vũ Trí Công*")}
    assert "Phát triển PM" in kieu and kieu["Phát triển PM"] == ["dam", "nghieng"]
    assert all("*" not in c for c in kieu), kieu

    p = tmp_path / "a.docx"
    sang_docx(doc_markdown("*Đề tài: **Phát triển PM** · Vũ Trí Công*"), p)
    assert "*" not in _chu_trong_docx(p)


def test_dong_noi_tiep_cua_mot_muc_khong_bi_vo_lam_hai(tmp_path):
    """Một mục dài viết trên hai dòng phải ra MỘT mục.

    Bản đầu đọc dòng thứ hai thành đoạn mới — và vì dấu `**` bị cắt giữa hai dòng, nó in
    nguyên ra giấy.
    """
    md = ("- EIDE chỉ nhận một mô hình. Đặt tên khác thì mã **từ chối ngay khi khởi\n"
          "  động** — không phải một cảnh báo rồi chạy tiếp.\n")
    khoi = doc_markdown(md)
    assert [k.loai for k in khoi] == ["gach_dau"]
    assert "khởi động" in khoi[0].chu

    p = tmp_path / "b.docx"
    sang_docx(khoi, p)
    assert "**" not in _chu_trong_docx(p)


def test_tieu_de_khong_in_hai_lan(tmp_path):
    md = "# Hướng dẫn cài đặt\n\nNội dung.\n"
    p = tmp_path / "c.docx"
    sang_docx(doc_markdown(md), p, tieu_de="Hướng dẫn cài đặt")
    assert _chu_trong_docx(p).count("Hướng dẫn cài đặt") == 1

    q = tmp_path / "d.docx"
    sang_docx(doc_markdown("Chỉ có đoạn.\n"), q, tieu_de="Tên khác hẳn")
    assert "Tên khác hẳn" in _chu_trong_docx(q)


def test_neo_trong_tai_lieu_khong_in_ra_giay():
    """`[Dữ liệu](#du-lieu)` trên giấy chỉ nên còn chữ — cái neo không bấm được."""
    assert "".join(c for c, _ in tach_chu("xem [Dữ liệu](#du-lieu)")) == "xem Dữ liệu"
    assert "https://x.vn" in "".join(c for c, _ in tach_chu("xem [trang](https://x.vn)"))


# ======================================================== lỗi MẤT DỮ LIỆU
def test_render_pdf_khong_pha_tep_docx_ben_canh(tmp_path):
    """Bản trung gian của PDF từng đè rồi XOÁ tệp `.docx` cùng tên nằm cạnh nó.

    Đo được ngay lần chạy thử đầu: dựng cả ba định dạng vào một thư mục, xong thì `.docx`
    không còn ở đó. Ca này kiểm tệp **bên cạnh**, không kiểm tệp nó tạo ra.
    """
    from eide.knowledge.office import co_libreoffice

    md = "# Báo cáo\n\nMột đoạn.\n"
    giu = tmp_path / "bao-cao.docx"
    assert render(md, giu, "docx").dat
    truoc = giu.read_bytes()

    kq = render(md, tmp_path / "bao-cao.pdf", "pdf")
    if not kq.dat:
        assert co_libreoffice() is None, kq.vi_sao_khong_dat
        pytest.skip("máy không có LibreOffice — ca PDF không đo được ở đây")

    assert giu.exists(), "render PDF đã xoá mất tệp .docx nằm cạnh"
    assert giu.read_bytes() == truoc, "render PDF đã ghi đè tệp .docx nằm cạnh"
    assert kq.do_lai["so_trang"] >= 1


# ======================================================== đọc Markdown
def test_bang_phai_co_hang_ke_moi_tinh_la_bang():
    """Một đoạn văn có dấu `|` không được đọc nhầm thành bảng."""
    assert doc_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n")[0].loai == "bang"
    assert doc_markdown("Chạy `a | b` rồi xem.\n")[0].loai == "doan"


def test_khoi_ma_giu_nguyen_dau_nhan_manh(tmp_path):
    p = tmp_path / "e.docx"
    sang_docx(doc_markdown("```\nint *p = &x;\n```\n"), p)
    assert "int *p = &x;" in _chu_trong_docx(p)


def test_anh_thieu_thi_NOI_RA_trong_tai_lieu(tmp_path):
    """Im lặng bỏ qua thì người cầm bản in không bao giờ biết đáng ra có một hình ở đây."""
    p = tmp_path / "f.docx"
    sang_docx(doc_markdown("![sơ đồ](khong-co.png)\n"), p, goc_anh=tmp_path)
    assert "thiếu ảnh" in _chu_trong_docx(p)


# ======================================================== Excel từ chối văn xuôi
def test_xlsx_tu_choi_khi_nguon_khong_co_bang(tmp_path):
    """Một `.xlsx` chứa cả đoạn văn trong ô A1 mở lên được nhưng vô dụng — và nó TRÔNG GIỐNG
    thành công. Thà báo lỗi."""
    kq = sang_xlsx(doc_markdown("# Tiêu đề\n\nMột đoạn văn dài.\n"), tmp_path / "g.xlsx")
    assert not kq.dat
    assert "bảng" in kq.vi_sao_khong_dat
    assert not (tmp_path / "g.xlsx").exists(), "từ chối mà vẫn để lại tệp thì tệ hơn"


def test_xlsx_moi_bang_mot_sheet_dat_ten_theo_tieu_de(tmp_path):
    md = ("## Kết quả đo\n\n| Ca | Đạt |\n|---|---|\n| A | có |\n| B | không |\n\n"
          "## Công cụ\n\n| Tên | Nhóm |\n|---|---|\n| fs.read | Tệp |\n")
    p = tmp_path / "h.xlsx"
    assert sang_xlsx(doc_markdown(md), p).dat
    do = doc_lai_xlsx(p)
    assert do["so_sheet"] == 2
    assert set(do["sheet"]) == {"Kết quả đo", "Công cụ"}
    assert do["sheet"]["Kết quả đo"]["hang"] == 3          # 1 tiêu đề + 2 hàng


def test_xlsx_bo_dau_markdown_trong_o(tmp_path):
    p = tmp_path / "i.xlsx"
    sang_xlsx(doc_markdown("| Cột |\n|---|\n| **đậm** và `mã` |\n"), p)
    wb = openpyxl.load_workbook(str(p))
    assert wb.worksheets[0].cell(2, 1).value == "đậm và mã"


# ======================================================== đọc lại để ĐO
def test_do_lai_dem_tu_CHINH_TEP_chu_khong_tu_nguon(tmp_path):
    """`ok` nói về lời gọi, không nói về kết quả — nên số đo phải mở lại tệp mà đếm."""
    p = tmp_path / "j.docx"
    kq = sang_docx(doc_markdown("# A\n\nMột.\n\nHai.\n\n| x |\n|---|\n| 1 |\n"), p)
    assert kq.do_lai["so_bang"] == 1
    assert kq.do_lai["so_ky_tu"] > 0
    assert kq.do_lai == doc_lai_docx(p)


def test_dinh_dang_la_va_nguon_rong_bi_tu_choi(tmp_path):
    assert "Không biết định dạng" in render("x", tmp_path / "k.odt", "odt").vi_sao_khong_dat
    assert "rỗng" in render("   \n\n", tmp_path / "k.docx", "docx").vi_sao_khong_dat


# ======================================================== công cụ doc.render
def _goi(du_an, **kw):
    """Gọi thẳng công cụ trên `agent.turn` — đó mới là `ctx` mà công cụ nhận lúc chạy thật."""
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent
    from eide.tools import build_registry

    from eide.loop import TurnContext

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger,
                      eide_md=ag.eide_md, ids=ag.ids, registry=ag.registry,
                      emit=lambda _c: None, history=ag.history, agent=ag,
                      run_id=ag.ids.next("run"), project_name="du-an-thu")
    r = build_registry()
    kw.setdefault("explain", {"summary": "s", "why": "w", "sources": [],
                              "diff_prev": "bản đầu", "next": "n", "confidence": "NGUOI"})
    return r.get("doc.render").fn(ctx, **kw)


def test_cong_cu_doi_dung_duoi_tep(du_an):
    ra = _goi(du_an, nguon="docs/ghi-chu.md", ra="bao-cao.pdf", dinh_dang="docx")
    assert not ra.ok and ra.error.code == "E2011"
    assert "bao-cao.docx" in ra.error.hint_for_agent


def test_cong_cu_bao_thieu_nguon_va_chi_duong(du_an):
    ra = _goi(du_an, nguon="khong-co.md", ra="a.docx", dinh_dang="docx")
    assert not ra.ok and ra.error.code == "E2010"
    assert "fs.write" in ra.error.alternatives


def test_cong_cu_tao_tep_va_sinh_changeset(du_an):
    ra = _goi(du_an, nguon="docs/ghi-chu.md", ra="ghi-chu.docx", dinh_dang="docx")
    assert (du_an / "ghi-chu.docx").is_file()
    assert ra["changeset"].startswith("cs-")
    assert ra["do_lai"]["so_doan"] >= 1
    # Câu báo phải mang SỐ ĐO, không mang chữ "đã ghi xong".
    assert "đoạn" in ra["note_vi"] and "mở lại" in ra["note_vi"]
