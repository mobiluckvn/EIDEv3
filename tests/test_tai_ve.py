# -*- coding: utf-8 -*-
"""Tải tài liệu từ URL: đúng loại tệp, đúng lý do khi không tải được.

Không test nào ở đây đi ra mạng — `mo_url` được thay bằng một máy chủ giả, vì một bộ kiểm phụ
thuộc mạng sẽ đỏ vì lý do không liên quan tới code và rồi sẽ bị bỏ qua.
"""

from __future__ import annotations

import hashlib
import io

import pytest

from eide.knowledge import tai_ve as tv


class MayChuGia:
    """Trả về nội dung định trước. Ghi lại URL đã gọi để test kiểm cả việc *không* gọi."""

    def __init__(self, noi_dung: bytes, *, content_type: str = "",
                 content_length: str | None = None, loi: Exception | None = None):
        self.noi_dung, self.loi = noi_dung, loi
        self.headers = {}
        if content_type:
            self.headers["Content-Type"] = content_type
        self.headers["Content-Length"] = (content_length if content_length is not None
                                          else str(len(noi_dung)))
        self.da_goi: list[str] = []

    def __call__(self, url: str, *, timeout: float):
        self.da_goi.append(url)
        if self.loi:
            raise self.loi
        may = self

        class Phien(io.BytesIO):
            headers = may.headers

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Phien(self.noi_dung)


PDF = b"%PDF-1.7\n" + b"x" * 2000 + b"\n%%EOF\n"
HTML = (
    "<!DOCTYPE html><html><body>"
    '<a href="/resource/en/datasheet/stm32f469ai.pdf">DS11189 Datasheet</a>'
    '<a href="https://www.st.com/resource/en/reference_manual/rm0386.pdf">'
    "  RM0386 <b>Reference</b> manual </a>"
    '<a href="/en/products.html">Sản phẩm</a>'
    '<a href="/resource/en/datasheet/stm32f469ai.pdf">trùng, phải bỏ</a>'
    "</body></html>"
).encode()


def test_tai_pdf_thi_luu_va_bao_hash(tmp_path):
    may = MayChuGia(PDF, content_type="application/pdf")
    kq = tv.tai_ve("https://www.st.com/x/stm32f469ai.pdf", tmp_path, mo_url=may)
    assert kq.dat and kq.loai == "pdf"
    assert kq.tep == "stm32f469ai.pdf"
    assert (tmp_path / kq.tep).read_bytes() == PDF
    assert kq.hash == hashlib.sha256(PDF).hexdigest()
    assert kq.so_byte == len(PDF)


def test_html_khong_bao_gio_bi_luu_thanh_tai_lieu(tmp_path):
    """Trang tường cookie trả 200 OK cho URL .pdf — không được coi là tải xong."""
    may = MayChuGia(HTML, content_type="text/html")
    kq = tv.tai_ve("https://www.st.com/x/stm32f469ai.pdf", tmp_path, mo_url=may)
    assert not kq.dat
    assert kq.loai == "html"
    assert list(tmp_path.iterdir()) == []          # không rác nào trên đĩa
    assert any(".pdf nhưng nội dung là HTML" in c for c in kq.canh_bao)


def test_html_liet_ke_ung_vien_pdf_tuyet_doi_va_khong_trung(tmp_path):
    may = MayChuGia(HTML, content_type="text/html")
    kq = tv.tai_ve("https://www.st.com/en/kit.html", tmp_path, mo_url=may)
    urls = [u["url"] for u in kq.ung_vien_pdf]
    assert urls == ["https://www.st.com/resource/en/datasheet/stm32f469ai.pdf",
                    "https://www.st.com/resource/en/reference_manual/rm0386.pdf"]
    # Tiêu đề lấy từ chữ trong thẻ <a>, đã bỏ thẻ con và gộp khoảng trắng.
    assert kq.ung_vien_pdf[1]["tieu_de"] == "RM0386 Reference manual"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "data:text/html,<b>x",
                                 "ftp://st.com/ds.pdf", "/tmp/ds.pdf"])
def test_chi_nhan_http_https(url, tmp_path):
    may = MayChuGia(PDF)
    kq = tv.tai_ve(url, tmp_path, mo_url=may)
    assert not kq.dat
    assert "http/https" in kq.vi_sao_khong_dat
    assert may.da_goi == []                        # không mở gì cả, chặn từ trước khi mở


def test_content_length_khai_qua_tran_thi_khong_tai(tmp_path):
    may = MayChuGia(PDF, content_length="99999999")
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, tran_byte=1000, mo_url=may)
    assert not kq.dat and "vượt trần" in kq.vi_sao_khong_dat


def test_content_length_noi_doi_van_bi_chan_trong_luc_doc(tmp_path):
    """Máy chủ khai 10 byte nhưng đẩy 200 KB — thước là số byte đã đọc, không phải lời khai."""
    may = MayChuGia(b"%PDF-" + b"y" * 200_000, content_length="10")
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, tran_byte=50_000, mo_url=may)
    assert not kq.dat
    assert "quá trần" in kq.vi_sao_khong_dat
    assert list(tmp_path.iterdir()) == []


def test_dinh_dang_la_thi_khong_luu(tmp_path):
    may = MayChuGia(b"\x7fELF\x02\x01\x01" + b"z" * 100, content_type="application/pdf")
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, mo_url=may)
    assert not kq.dat and kq.loai == "khong_biet"
    assert "không nhận ra định dạng" in kq.vi_sao_khong_dat
    assert list(tmp_path.iterdir()) == []


def test_zero_byte_khong_phai_thanh_cong(tmp_path):
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, mo_url=MayChuGia(b""))
    assert not kq.dat and "0 byte" in kq.vi_sao_khong_dat


def test_loi_http_noi_ro_ma(tmp_path):
    import urllib.error
    may = MayChuGia(b"", loi=urllib.error.HTTPError(
        "https://x.com/a.pdf", 403, "Forbidden", {}, None))
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, mo_url=may)
    assert not kq.dat and "HTTP 403" in kq.vi_sao_khong_dat


def test_cung_ten_khac_noi_dung_thi_giu_ca_hai(tmp_path):
    """Ghi đè im lặng sẽ xoá bản tài liệu mà các Fact cũ đang trích dẫn tới."""
    tv.tai_ve("https://x.com/ds.pdf", tmp_path, mo_url=MayChuGia(PDF))
    khac = b"%PDF-1.4\nban moi\n%%EOF\n"
    kq = tv.tai_ve("https://x.com/ds.pdf", tmp_path, mo_url=MayChuGia(khac))
    assert kq.dat and kq.tep != "ds.pdf"
    assert (tmp_path / "ds.pdf").read_bytes() == PDF        # bản cũ còn nguyên
    assert (tmp_path / kq.tep).read_bytes() == khac
    assert any("cùng tên" in c for c in kq.canh_bao)


def test_cung_ten_cung_noi_dung_thi_ghi_lai_khong_sinh_ban_thu_hai(tmp_path):
    tv.tai_ve("https://x.com/ds.pdf", tmp_path, mo_url=MayChuGia(PDF))
    kq = tv.tai_ve("https://x.com/ds.pdf", tmp_path, mo_url=MayChuGia(PDF))
    assert kq.dat and kq.tep == "ds.pdf"
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("url,mong", [
    ("https://st.com/a/b/DS11189.pdf", "DS11189.pdf"),
    ("https://st.com/a/../../etc/passwd", "passwd"),
    ("https://st.com/resource/en/user%20manual/um2032.pdf", "um2032.pdf"),
    ("https://st.com/", "tai-lieu"),
    ("https://st.com/x?q=1#f", "x"),
])
def test_ten_tu_url_khong_bao_gio_co_duong_dan(url, mong):
    ten = tv.ten_tu_url(url)
    assert ten == mong
    assert "/" not in ten and ".." not in ten


def test_ten_tep_do_nguoi_dat_cung_duoc_lam_sach(tmp_path):
    kq = tv.tai_ve("https://x.com/a.pdf", tmp_path, ten_tep="../../thoat/ds",
                   mo_url=MayChuGia(PDF))
    assert kq.dat and "/" not in kq.tep and kq.tep.endswith(".pdf")
    assert (tmp_path / kq.tep).exists()


def test_docx_nhan_ra_qua_magic_zip(tmp_path):
    kq = tv.tai_ve("https://x.com/tl.docx", tmp_path,
                   mo_url=MayChuGia(b"PK\x03\x04" + b"q" * 500))
    assert kq.dat and kq.loai == "zip" and kq.tep == "tl.docx"


# ============================================ trang web CHÍNH LÀ tài liệu (nhan_html=True)
def test_nhan_html_luu_ca_ban_goc_va_ban_chu(tmp_path):
    """Trích dẫn "dòng 42" phải trỏ vào tệp mở ra kiểm được, nên bản chữ là tệp riêng."""
    body = ("<html><head><title>t</title><style>p{color:red}</style></head><body>"
            "<h1>STM32F469 Discovery</h1>"
            "<p>STM32F469NIH6 microcontroller featuring 2 Mbytes of Flash memory</p>"
            "<p>and 324 Kbytes of RAM in BGA216 package</p>"
            "<ul><li>4 color user LEDs</li><li>On-board ST-LINK/V2-1</li></ul>"
            "<script>var x = 'không được lẫn vào chữ'</script>"
            + "<p>đệm cho đủ 200 ký tự</p>" * 6
            + "</body></html>")
    kq = tv.tai_ve("https://www.proe.vn/stm32f469", tmp_path, nhan_html=True,
                   mo_url=MayChuGia(body.encode(), content_type="text/html"))
    assert kq.dat and kq.tep == "stm32f469.txt" and kq.tep_goc == "stm32f469.html"
    chu = (tmp_path / kq.tep).read_text("utf-8")
    assert "STM32F469NIH6" in chu and "4 color user LEDs" in chu
    assert "không được lẫn vào chữ" not in chu      # <script> bị bỏ
    assert "color:red" not in chu                   # <style> bị bỏ
    assert "<p>" not in chu                         # không còn thẻ
    assert (tmp_path / kq.tep_goc).read_bytes() == body.encode()   # bản gốc còn nguyên
    assert any("BÓC RA từ một trang web" in c for c in kq.canh_bao)
    assert any("ben_thu_ba" in c for c in kq.canh_bao)


def test_nhan_html_trang_rong_chu_thi_khong_dat(tmp_path):
    """Trang dựng bằng JS bóc ra gần như không có chữ — nói thẳng, đừng lưu tệp rỗng."""
    body = b"<html><body><div id=app></div><script>render()</script></body></html>"
    kq = tv.tai_ve("https://x.com/a", tmp_path, nhan_html=True,
                   mo_url=MayChuGia(body, content_type="text/html"))
    assert not kq.dat and "JavaScript" in kq.vi_sao_khong_dat
    assert list(tmp_path.iterdir()) == []


def test_khong_nhan_html_thi_goi_y_dung_cach(tmp_path):
    kq = tv.tai_ve("https://www.proe.vn/stm32f469", tmp_path,
                   mo_url=MayChuGia(b"<html><body>" + b"a" * 300 + b"</body></html>",
                                    content_type="text/html"))
    assert not kq.dat and "nhan_html=true" in kq.vi_sao_khong_dat


def test_chu_tu_html_giu_ranh_gioi_dong_theo_the_khoi():
    chu = tv.chu_tu_html("<p>một</p><p>hai</p><li>ba</li><br>bốn<div>năm</div>")
    assert [d for d in chu.splitlines() if d] == ["một", "hai", "ba", "bốn", "năm"]


def test_chu_tu_html_giai_ma_thuc_the():
    assert "3.3 V & 85 °C" in tv.chu_tu_html("<p>3.3 V &amp; 85 &#176;C</p>")


# ============================================ tìm kiếm: hạn mức khác mất mạng
def test_het_han_muc_khong_bi_goi_la_loi_mang(tmp_path):
    """Hai lỗi này dẫn tới hai hành động khác nhau, nên không được mang cùng một tên."""
    import urllib.error

    from eide.knowledge import tim_kiem as tk

    class Dau(dict):
        def get(self, k, d=None):                     # header không phân biệt hoa thường
            return super().get(k.lower(), d)

    import time as _t
    e = urllib.error.HTTPError(
        "https://api.github.com/orgs/X/repos", 403, "rate limit exceeded",
        Dau({"x-ratelimit-remaining": "0",
             "x-ratelimit-reset": str(int(_t.time()) + 900)}), None)

    def mo_loi(*a, **k):
        raise e

    import urllib.request
    that = urllib.request.urlopen
    urllib.request.urlopen = mo_loi
    try:
        kq = tk.tim_github("STM32F469 discovery LED", cache=tmp_path)
    finally:
        urllib.request.urlopen = that
    assert not kq.dat and kq.het_han_muc is True
    assert "HẾT HẠN MỨC" in kq.vi_sao_khong_dat
    assert "phút" in kq.vi_sao_khong_dat          # nói KHI NÀO thử lại được
    assert "EIDE_GITHUB_TOKEN" in kq.vi_sao_khong_dat


def test_het_han_muc_ma_co_nho_dem_cu_thi_dung_no_va_khai_ra(tmp_path):
    import json as _json
    import urllib.error
    import urllib.request

    from eide.knowledge import tim_kiem as tk

    (tmp_path / "org-STMicroelectronics.json").write_text(
        _json.dumps([["STM32CubeF4", "master"]]), "utf-8")

    import os
    os.utime(tmp_path / "org-STMicroelectronics.json",
             (0, 0))                                # làm cho nhớ đệm quá hạn

    class Dau(dict):
        def get(self, k, d=None):
            return super().get(k.lower(), d)

    import time as _t
    goi: list[str] = []

    def mo(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        goi.append(url)
        raise urllib.error.HTTPError(
            url, 403, "rate limit", Dau({"x-ratelimit-remaining": "0",
                                         "x-ratelimit-reset": str(int(_t.time()) + 60)}), None)

    that = urllib.request.urlopen
    urllib.request.urlopen = mo
    try:
        kq = tk.tim_github("STM32F469 discovery LED", cache=tmp_path)
    finally:
        urllib.request.urlopen = that
    # Danh sách repo lấy từ nhớ đệm cũ; cây tệp vẫn hết hạn mức nên không có ứng viên —
    # nhưng lý do phải nói rõ là HẠN MỨC, và phải khai là đã dùng nhớ đệm cũ.
    assert kq.het_han_muc is True
    assert any("nhớ đệm cũ" in g for g in kq.ghi_chu)
    assert any("HẾT HẠN MỨC" in g for g in kq.ghi_chu)


def test_khong_nhan_ra_hang_thi_noi_thang_chu_khong_tim_bua(tmp_path):
    """Một repo của người lạ trùng tên chip sẽ trông y như tài liệu hãng — sai mà trông đúng."""
    from eide.knowledge import tim_kiem as tk

    kq = tk.tim_github("cảm biến nhiệt độ loại nào tốt", cache=tmp_path)
    assert not kq.dat and not kq.het_han_muc
    assert "Không nhận ra hãng nào" in kq.vi_sao_khong_dat


def test_to_chuc_suy_dung_tu_dong_chip():
    from eide.knowledge.tim_kiem import to_chuc_cho

    assert to_chuc_cho("STM32F469I-DISCO pinout") == "STMicroelectronics"
    assert to_chuc_cho("esp32-s3 datasheet") == "espressif"
    assert to_chuc_cho("nRF52840 gpio") == "NordicSemiconductor"
    assert to_chuc_cho("con chip gì đó") == ""


def test_bien_the_tu_khoa_bat_duoc_ten_repo_theo_HO_chip():
    """Tên repo của hãng theo HỌ hoặc theo MÃ ĐẶT HÀNG, không theo mã chip đầy đủ."""
    from eide.knowledge.tim_kiem import _bien_the, _diem_repo

    bt = _bien_the("stm32f469i")
    assert "stm32f4" in bt and "f4" in bt and "stm32" in bt      # theo họ
    assert "32f469i" in bt and "f469i" in bt                     # theo mã đặt hàng
    assert "stm32469" in bt                                      # ST bỏ chữ họ khi đặt tên bo
    # Biến thể ĐẶC HIỆU phải nặng hơn biến thể HỌ.
    assert bt["32f469i"] > bt["stm32f4"] > bt["stm32"]

    tu = ["stm32f469", "discovery"]
    assert _diem_repo("STM32CubeF4", tu) > _diem_repo("STM32CubeF0", tu)
    assert _diem_repo("STM32CubeF4", tu) > _diem_repo("khong-lien-quan", tu)


def test_repo_dung_bo_thang_repo_bo_KHAC_cung_ho():
    """Ca thật: với "STM32F469I-DISCO", bo F407 (`stm32f4discovery-bsp`) từng thắng.

    Nó thắng vì điểm được CỘNG DỒN cho `stm32`, `stm32f4` và `f4` — ba lần điểm cho cùng một
    sự thật "thuộc họ F4" — đủ để đè một tên khớp đúng mã bo. Nay lấy max theo độ đặc hiệu.
    """
    from eide.knowledge.tim_kiem import _diem_repo, _tu_khoa

    tu = _tu_khoa("STM32F469I-DISCO bảng chân LED")
    dung = _diem_repo("32f469idiscovery-bsp", tu)          # ĐÚNG bo
    sai_ho = _diem_repo("stm32f4discovery-bsp", tu)        # cùng họ F4, bo F407
    sai_eval = _diem_repo("stm32469i-eval-bsp", tu)        # cùng chip, bo EVAL
    assert dung > sai_ho, f"{dung} phải hơn {sai_ho}"
    assert dung > sai_eval, f"{dung} phải hơn {sai_eval}"


def test_duong_dan_khop_qua_bien_the_bo_chu_ho():
    """`Drivers/BSP/STM32469I-Discovery/stm32469i_discovery.h` — không có chữ F trong tên."""
    from eide.knowledge.tim_kiem import _diem_duong_dan, _tu_khoa

    tu = _tu_khoa("STM32F469I-DISCO chân LED")
    dung = _diem_duong_dan(
        "Drivers/BSP/STM32469I-Discovery/stm32469i_discovery.h", tu)
    khac = _diem_duong_dan(
        "Drivers/BSP/STM32F4-Discovery/stm32f4_discovery.h", tu)
    assert dung > 0 and dung > khac
    # Tệp không liên quan trong cùng repo thì 0 điểm, không phải "hơi liên quan".
    assert _diem_duong_dan("Middlewares/Third_Party/FatFs/src/ff.h", tu) == 0.0


# ============================================ văn bản thuần: doc.fetch phải nhận
def test_header_C_tai_ve_duoc(tmp_path):
    """`doc.load` nạp được mã nguồn, nên `doc.fetch` mà từ chối là hệ thống tự nói ngược nhau.

    Ca thật: tác tử tìm đúng `stm32469i_discovery.h` trên GitHub của ST rồi bị chính EIDE chặn
    ở bước tải, và nó kết luận "hãng không lưu tài liệu trên GitHub" — một kết luận sai rút ra
    từ một lỗi của ta.
    """
    h = ("/* stm32469i_discovery.h */\n"
         "#define LED1_PIN GPIO_PIN_6\n"
         "#define LED1_GPIO_PORT GPIOG\n").encode()
    kq = tv.tai_ve("https://raw.githubusercontent.com/STMicroelectronics/"
                   "32f469idiscovery-bsp/main/stm32469i_discovery.h", tmp_path,
                   mo_url=MayChuGia(h, content_type="text/plain"))
    assert kq.dat and kq.loai == "van_ban"
    assert kq.tep == "stm32469i_discovery.h"
    assert (tmp_path / kq.tep).read_bytes() == h


@pytest.mark.parametrize("ten,noi_dung", [
    ("mach.ld", b"MEMORY {\n  FLASH (rx) : ORIGIN = 0x08000000\n}\n"),
    ("README.md", "# Bo STM32F469\n\nBốn đèn LED người dùng.\n".encode()),
    ("chan.csv", b"ten,cong,huong\nLED1,PG6,ra\n"),
])
def test_cac_dang_van_ban_khac_cung_tai_duoc(ten, noi_dung, tmp_path):
    kq = tv.tai_ve(f"https://x.com/{ten}", tmp_path, mo_url=MayChuGia(noi_dung))
    assert kq.dat and kq.loai == "van_ban" and kq.tep == ten


def test_nhi_phan_khong_magic_van_bi_tu_choi(tmp_path):
    """Giải mã được UTF-8 chưa đủ — một tệp nhị phân vẫn có thể tình cờ hợp lệ UTF-8."""
    kq = tv.tai_ve("https://x.com/a.bin", tmp_path,
                   mo_url=MayChuGia(bytes(range(1, 32)) * 40))
    assert not kq.dat and kq.loai == "khong_biet"
    assert "không phải văn bản" in kq.vi_sao_khong_dat
    assert list(tmp_path.iterdir()) == []


def test_html_van_bi_tu_choi_truoc_khi_toi_nhanh_van_ban(tmp_path):
    """HTML cũng là văn bản — nhưng nó phải rơi vào nhánh HTML, không phải nhánh văn bản."""
    kq = tv.tai_ve("https://st.com/x.pdf", tmp_path,
                   mo_url=MayChuGia(HTML, content_type="text/html"))
    assert not kq.dat and kq.loai == "html"
    assert list(tmp_path.iterdir()) == []
