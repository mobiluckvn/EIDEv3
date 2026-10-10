# -*- coding: utf-8 -*-
"""Mô hình MÀN HÌNH UI + render HTML — bước 2 của năng lực thiết kế UI nhúng.

Mã lỗi dùng họ **E11xx** và cảnh báo **W11xx**. Bản đầu của tôi dùng `E9001`–`E9006` và suýt
đi qua: dải ấy **đã bị chiếm** bởi sáu bất biến của cây phân cấp (`knowledge/cay.py` ghi rõ
"bất biến cây là E9001–E9006"). Trùng mã lỗi là một lỗi im lặng đặc biệt khó chịu — hai chỗ
khác nhau cùng in `E9001`, và người đọc log đi tra sai chỗ.

Hiện vật gốc là **mô hình có cấu trúc**, HTML là bản **dựng ra** từ nó. Lý do: nếu HTML là bản
gốc thì bước "chuyển thành code" phải đọc lại HTML để suy ra ý định, và đó là việc mất thông
tin — `<div>` không nói nó là nhãn hay nút, `left: 37%` không nói toạ độ pixel nào trên panel.
Cả HTML lẫn code C đều sinh từ một nguồn, nên chúng không bao giờ lệch nhau.

Toạ độ trong mô hình là **pixel thật của panel**, nên HTML render ra đúng tỉ lệ 1:1.

Bốn phép kiểm ở đây là bốn chỗ "trình biên dịch im lặng tuyệt đối" của riêng phần giao diện —
thiết kế sai mà mã vẫn dịch, vẫn nạp, và màn hình thật thì sai:

1. phần tử ra ngoài biên panel → màn hình cắt mất, không lỗi nào kêu;
2. chữ dài hơn ô chứa nó → BSP vẽ tràn hoặc cắt giữa chữ;
3. cỡ chữ không có trong thư viện BSP → mã không dịch được, mà chỉ biết ở bước dịch;
4. hai màu KHÁC NHAU trong thiết kế thành MỘT màu trên panel sau khi lượng hoá RGB565.
"""
from __future__ import annotations

import json

import pytest

from pathlib import Path

from eide.knowledge.man_hinh import HoSoManHinh
from eide.man_hinh import mo_hinh as MO
from eide.man_hinh import html as HT

GOC = Path(__file__).parents[1]


def _hs(he_mau: str = "ARGB8888", **kw) -> HoSoManHinh:
    """Hồ sơ màn hình của bo STM32F469I-DISCO, số lấy từ tài liệu kiến trúc trong repo."""
    d = dict(rong=800, cao=480, he_mau=he_mau, inch=4.0, dpi=233.2, dpi_la_tinh_ra=True,
             driver="OTM8009A", bus="MIPI-DSI", cam_ung=True)
    d.update(kw)
    return HoSoManHinh(**d)


def _mh(*phan_tu, **kw) -> MO.ManHinh:
    d = dict(ten="chinh", rong=800, cao=480, he_mau="ARGB8888", phan_tu=list(phan_tu))
    d.update(kw)
    return MO.ManHinh(**d)


# =========================================================================== font BSP
def test_font_BSP_tra_tu_MA_THAT_trong_repo():
    """Năm font của BSP, kích thước tra từ chính bảng font trong repo — không nhớ.

    Nguồn: `docs/stm32f469/firmware-chay-duoc/font{8,12,16,20,24}.c`, trường `Width`/`Height`
    của `sFONT`. Đây là font ĐƠN CÁCH, nên bề rộng một dòng chữ tính được chính xác — và đó là
    điều làm phép kiểm "chữ có bị cắt không" thành một phép đo chứ không phải một phỏng đoán.
    """
    assert MO.FONT_BSP == {8: (5, 8), 12: (7, 12), 16: (11, 16), 20: (14, 20), 24: (17, 24)}
    assert MO.be_rong_chu("ABC", 24) == 3 * 17
    assert MO.be_rong_chu("", 24) == 0
    assert MO.be_rong_chu("ABC", 13) is None, "cỡ chữ không có trong BSP → KHÔNG BIẾT"


def test_co_chu_khong_co_trong_BSP_thi_CHAN_va_chi_co_gan_nhat():
    """Cỡ chữ 14 không có trong BSP. Chặn ở bước thiết kế, đừng để bước dịch mới biết.

    `BSP_LCD_SetFont(&Font14)` là một `Font14 undeclared` — một lỗi dịch, tức một lỗi người
    dùng chỉ gặp sau khi đã vẽ xong cả màn hình. Nói ngay ở đây, và nói cỡ gần nhất có thật.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=0, y=0, w=200, h=30,
                               chu="Nhiệt độ", co_chu=14)), _hs())
    loi = [x for x in kq.loi if x["ma"] == "E1103"]
    assert loi, [x["ma"] for x in kq.loi]
    assert "14" in loi[0]["vi_sao"] and "12" in loi[0]["vi_sao"], loi[0]["vi_sao"]


# =========================================================================== biên panel
def test_phan_tu_RA_NGOAI_bien_bi_chan():
    """Panel 800×480 thì `x + w` không được vượt 800. Màn hình thật sẽ CẮT, không báo lỗi."""
    kq = MO.kiem(_mh(MO.PhanTu(id="r1", loai="rect", x=700, y=10, w=200, h=50)), _hs())
    loi = [x for x in kq.loi if x["ma"] == "E1101"]
    assert loi, [x["ma"] for x in kq.loi]
    assert "r1" in loi[0]["phan_tu"]
    assert "900" in loi[0]["vi_sao"] and "800" in loi[0]["vi_sao"], loi[0]["vi_sao"]


def test_phan_tu_VUA_KHIT_bien_thi_KHONG_bi_chan():
    """Ca âm, và nó canh một lỗi lệch-một có thật: `x + w == rong` là VỪA KHÍT, không phải tràn.

    Pixel cuối cùng của panel 800 px là `x = 799`, nên một ô `x=700, w=100` chiếm 700..799 —
    đúng vừa. Chặn nó là bắt người dùng để trống một cột pixel mà không có lý do nào.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="r1", loai="rect", x=700, y=430, w=100, h=50)), _hs())
    assert [x for x in kq.loi if x["ma"] == "E1101"] == []


def test_toa_do_AM_bi_chan():
    kq = MO.kiem(_mh(MO.PhanTu(id="r1", loai="rect", x=-5, y=0, w=50, h=50)), _hs())
    assert [x for x in kq.loi if x["ma"] == "E1101"], [x["ma"] for x in kq.loi]


# =========================================================================== chữ bị cắt
def test_chu_DAI_HON_o_chua_no_thi_keu_len():
    """`Font24` rộng 17 px/ký tự. 12 ký tự = 204 px, không vừa một ô 150 px.

    BSP `DisplayStringAt` không tự ngắt dòng và không tự thu nhỏ — nó vẽ tiếp ra ngoài ô, hoặc
    bị cắt ở biên panel. Đây là lỗi thiết kế UI nhúng hay gặp nhất, và nó **chỉ hiện ra trên
    màn hình thật** vì bản vẽ trên máy tính dùng font co giãn được.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=150, h=30,
                               chu="Nhiệt độ: 25", co_chu=24)), _hs())
    loi = [x for x in kq.loi if x["ma"] == "E1102"]
    assert loi, [x["ma"] for x in kq.loi]
    assert "204" in loi[0]["vi_sao"], loi[0]["vi_sao"]
    # Và nó phải nói CÁCH SỬA bằng số: cỡ chữ nào thì vừa.
    assert "16" in loi[0]["cach_sua"] or "12" in loi[0]["cach_sua"], loi[0]["cach_sua"]


def test_chu_VUA_o_thi_khong_keu():
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=220, h=30,
                               chu="Nhiệt độ: 25", co_chu=16)), _hs())
    assert [x for x in kq.loi if x["ma"] == "E1102"] == [], kq.loi


def test_chu_CAO_HON_o_chua_no_thi_keu_len():
    """`Font24` cao 24 px. Một ô cao 20 px không chứa nổi nó."""
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=400, h=20,
                               chu="OK", co_chu=24)), _hs())
    assert [x for x in kq.loi if x["ma"] == "E1102"], [x["ma"] for x in kq.loi]


# =========================================================================== lượng hoá màu
def test_luong_hoa_RGB565_tra_dung_mau_PANEL_SE_HIEN():
    """RGB565 giữ 5 bit đỏ, 6 bit lục, 5 bit lam. `#FF8040` trên panel là `#FF8242`.

    Phép mở rộng ngược phải là phép BSP/LTDC dùng thật (`r5<<3 | r5>>2`), không phải nhân
    tỉ lệ — hai cách cho hai con số khác nhau, và con số đúng là con số phần cứng dùng.
    """
    assert MO.luong_hoa("#FF8040", "RGB565") == "#FF8242"
    assert MO.luong_hoa("#000000", "RGB565") == "#000000"
    assert MO.luong_hoa("#FFFFFF", "RGB565") == "#FFFFFF"
    # ARGB8888 giữ nguyên 8 bit mỗi kênh — không lượng hoá gì.
    assert MO.luong_hoa("#FF8040", "ARGB8888") == "#FF8040"


def test_hai_mau_KHAC_NHAU_thanh_MOT_mau_tren_panel_thi_keu_len():
    """Đây là phép kiểm đáng giá nhất của lượng hoá màu.

    Gần như MỌI màu đều lệch một chút khi xuống RGB565, nên kêu lên vì "có lệch" sẽ kêu ở mọi
    thiết kế và mất nghĩa. Chỗ thật sự hỏng là khi **hai màu khác nhau trong thiết kế thành
    một màu trên panel** — lúc ấy một thiết kế hai tông thành một tông, chữ biến mất vào nền,
    và không có lỗi nào ở bất kỳ bước nào.

    `#FF0000` và `#FF0400`: lục 0x00 và 0x04 đều cho `g6 = 1`… thực ra `0x04>>2 = 1` và
    `0x00>>2 = 0`, nên phải chọn cặp thật sự trùng — `#FF0000` và `#FF0300` (3>>2 = 0).
    """
    a, b = "#FF0000", "#FF0300"
    assert MO.luong_hoa(a, "RGB565") == MO.luong_hoa(b, "RGB565"), "cặp mẫu phải THẬT SỰ trùng"
    kq = MO.kiem(_mh(MO.PhanTu(id="n1", loai="rect", x=0, y=0, w=100, h=100, mau_nen=a),
                     MO.PhanTu(id="n2", loai="rect", x=200, y=0, w=100, h=100, mau_nen=b),
                     he_mau="RGB565"), _hs("RGB565"))
    canh = [x for x in kq.canh_bao if x["ma"] == "W1101"]
    assert canh, [x["ma"] for x in kq.canh_bao]
    assert "n1" in canh[0]["vi_sao"] and "n2" in canh[0]["vi_sao"], canh[0]["vi_sao"]


def test_mau_lech_IT_thi_KHONG_keu():
    """Ca âm: hai màu vẫn khác nhau sau lượng hoá → không kêu.

    Không có ca này thì phép kiểm trên có thể đang kêu ở mọi cặp màu, và con số "0 cảnh báo"
    của một thiết kế sạch sẽ không nói gì.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="n1", loai="rect", x=0, y=0, w=100, h=100, mau_nen="#FF0000"),
                     MO.PhanTu(id="n2", loai="rect", x=200, y=0, w=100, h=100, mau_nen="#00FF00"),
                     he_mau="RGB565"), _hs("RGB565"))
    assert [x for x in kq.canh_bao if x["ma"] == "W1101"] == []


def test_chu_TRUNG_mau_nen_sau_luong_hoa_la_LOI_khong_phai_canh_bao():
    """Chữ cùng màu nền thì nó **không hiện**. Đó là lỗi, không phải gợi ý.

    Và nó phải được bắt SAU lượng hoá: hai màu khác nhau trong thiết kế có thể trùng nhau trên
    panel RGB565, nên phép so trước lượng hoá sẽ nói "khác nhau" về một chữ vô hình.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=0, y=0, w=300, h=30, chu="Ẩn",
                               co_chu=16, mau_chu="#FF0000", mau_nen="#FF0300"),
                     he_mau="RGB565"), _hs("RGB565"))
    assert [x for x in kq.loi if x["ma"] == "E1104"], [x["ma"] for x in kq.loi]


# =========================================================================== vùng chạm
def test_nut_QUA_NHO_cho_ngon_tay_thi_canh_bao_va_noi_ro_NGUON_CUA_NGUONG():
    """Ngưỡng 9 mm là **hướng dẫn nhân trắc**, không phải hằng số phần cứng — và lời cảnh báo
    phải nói ra điều đó.

    Dự án này có luật N1 về con số: con số nào cũng phải truy được về nguồn. Một ngưỡng lấy từ
    hướng dẫn thiết kế thì nguồn của nó là **tên hướng dẫn ấy**, chứ không phải một datasheet —
    và trộn hai loại nguồn là cách một khuyến nghị trông như một phép đo.

    9 mm ở 233 DPI ≈ 82 px, nên một nút 40 px là quá nhỏ.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="b1", loai="button", x=10, y=10, w=40, h=40, chu="OK",
                               co_chu=12)), _hs())
    canh = [x for x in kq.canh_bao if x["ma"] == "W1102"]
    assert canh, [x["ma"] for x in kq.canh_bao]
    assert "82" in canh[0]["vi_sao"] or "81" in canh[0]["vi_sao"], canh[0]["vi_sao"]
    assert "hướng dẫn" in canh[0]["vi_sao"].lower(), (
        "ngưỡng nhân trắc phải TỰ KHAI là hướng dẫn, không phải số đo phần cứng")


def test_KHONG_biet_DPI_thi_KHONG_kiem_vung_cham():
    """Không có DPI thì không quy được mm sang pixel — nên KHÔNG kết luận, và nói vì sao.

    `False` ở đây là một cảnh báo dựng trên một con số không có, và N2 gọi đó là "chưa đủ dữ
    kiện" chứ không phải "đạt" hay "không đạt".
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="b1", loai="button", x=10, y=10, w=40, h=40, chu="OK",
                               co_chu=12)), _hs(inch=None, dpi=None))
    assert [x for x in kq.canh_bao if x["ma"] == "W1102"] == []
    assert any("DPI" in x.get("vi_sao", "") for x in kq.chua_kiem), kq.chua_kiem


def test_panel_KHONG_cam_ung_ma_thiet_ke_co_NUT_thi_la_LOI():
    """Một nút trên màn hình không cảm ứng là một nút không ai bấm được.

    Và đây là chỗ `cam_ung = None` khác `cam_ung = False` có hậu quả thật: `None` thì chưa kết
    luận được, `False` thì nút ấy chắc chắn vô dụng.
    """
    kq = MO.kiem(_mh(MO.PhanTu(id="b1", loai="button", x=10, y=10, w=200, h=100, chu="OK",
                               co_chu=16)), _hs(cam_ung=False))
    assert [x for x in kq.loi if x["ma"] == "E1105"], [x["ma"] for x in kq.loi]
    # Và khi CHƯA BIẾT thì không kết luận.
    kq2 = MO.kiem(_mh(MO.PhanTu(id="b1", loai="button", x=10, y=10, w=200, h=100, chu="OK",
                                co_chu=16)), _hs(cam_ung=None))
    assert [x for x in kq2.loi if x["ma"] == "E1105"] == []
    assert any("cảm ứng" in x.get("vi_sao", "") for x in kq2.chua_kiem), kq2.chua_kiem


# =========================================================================== hồ sơ ↔ mô hình
def test_mo_hinh_LECH_ho_so_thi_bi_chan():
    """Mô hình khai 480×272 mà panel là 800×480 → chặn.

    Đây là cửa giữ cho cả năng lực này còn nghĩa: bản thiết kế phải vẽ cho **đúng màn hình
    thật**, không cho một màn hình tác tử nghĩ ra.
    """
    kq = MO.kiem(_mh(rong=480, cao=272), _hs())
    loi = [x for x in kq.loi if x["ma"] == "E1106"]
    assert loi, [x["ma"] for x in kq.loi]
    assert "480×272" in loi[0]["vi_sao"] and "800×480" in loi[0]["vi_sao"], loi[0]["vi_sao"]


def test_ho_so_KHONG_HOP_LE_thi_tu_choi_kiem():
    """Hồ sơ màn hình không hợp lệ thì không có khung nào để kiểm biên — từ chối, đừng vẽ."""
    kq = MO.kiem(_mh(), HoSoManHinh())
    assert kq.hop_le is False
    assert [x for x in kq.loi if x["ma"] == "E1107"], [x["ma"] for x in kq.loi]


# =========================================================================== vòng JSON
def test_mo_hinh_di_qua_JSON_khong_mat_gi():
    """Mô hình là HIỆN VẬT, nên nó phải đi qua JSON nguyên vẹn — kho lưu JSON."""
    mh = _mh(MO.PhanTu(id="t1", loai="text", x=1, y=2, w=3, h=4, chu="Ä", co_chu=12,
                       mau_chu="#102030", mau_nen="#405060", can_le="center"),
             MO.PhanTu(id="b1", loai="bar", x=5, y=6, w=700, h=20, gia_tri=42.5))
    lai = MO.ManHinh.tu_dict(json.loads(json.dumps(mh.to_dict())))
    assert lai == mh


def test_tu_dict_CHIU_DUOC_truong_thieu():
    """Hiện vật cũ không có trường mới. `tu_dict` phải chịu được, đừng đổ.

    Bài học DEV-359: `BanTomTat.tu_dict` phải chịu được khoá thiếu, vì hiện vật đã nằm trong
    kho người dùng không ai sửa lại.
    """
    mh = MO.ManHinh.tu_dict({"ten": "x", "rong": 800, "cao": 480,
                             "phan_tu": [{"id": "a", "loai": "rect",
                                          "x": 0, "y": 0, "w": 10, "h": 10}]})
    assert mh.he_mau == "" and mh.phan_tu[0].co_chu == MO.CO_CHU_MAC_DINH


# =========================================================================== render HTML
def test_html_render_dung_TI_LE_1_1():
    """Khung thiết bị trong HTML phải đúng `800px × 480px` — 1:1 với panel.

    Render theo tỉ lệ phần trăm sẽ cho một bản xem đẹp mà vô dụng: người xem không đối chiếu
    được nó với màn hình thật, và đó là toàn bộ lý do bản render này tồn tại.
    """
    h = HT.dung_html(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=20, w=300, h=30,
                                   chu="Nhiệt độ", co_chu=24)), _hs())
    assert "width:800px" in h.replace(" ", "")
    assert "height:480px" in h.replace(" ", "")
    assert "left:10px" in h.replace(" ", "") and "top:20px" in h.replace(" ", "")


def test_html_hien_mau_PANEL_SE_HIEN_khong_hien_mau_thiet_ke():
    """HTML phải vẽ bằng màu panel hiện ra, không bằng màu người thiết kế gõ vào.

    Đây là lựa chọn N6 của bản render: nếu vẽ bằng `#FF8040` thì bản xem **đẹp hơn** màn hình
    thật, và người dùng duyệt một thứ họ sẽ không nhận được. Vẽ bằng `#FF8242` thì bản xem nói
    đúng sự thật.
    """
    h = HT.dung_html(_mh(MO.PhanTu(id="r1", loai="rect", x=0, y=0, w=100, h=100,
                                   mau_nen="#FF8040"), he_mau="RGB565"), _hs("RGB565"))
    assert "#FF8242" in h.upper(), "phải là màu SAU lượng hoá"
    assert "#FF8040" not in h.upper().replace("#FF8242", ""), "không được vẽ bằng màu thiết kế"


def test_html_KHONG_goi_ra_ngoai():
    """Không `<script src>`, không `<link href=http`, không `@import` — trang chạy ngoại tuyến.

    Giao diện mở trang này trong `WKWebView`. Một tài nguyên ngoài mạng trong đó là một đường
    ra Internet từ một bản thiết kế do mô hình sinh, và dự án này không cho phép thế.
    """
    h = HT.dung_html(_mh(MO.PhanTu(id="t1", loai="text", x=0, y=0, w=200, h=30, chu="X",
                                   co_chu=16)), _hs())
    for xau in ("http://", "https://", "//cdn", "@import", "<script src"):
        assert xau not in h.lower(), xau


def test_html_tu_khai_do_phan_giai_va_NGUON_cua_no():
    """Trang HTML phải tự nói nó vẽ cho panel nào, và cấu hình ấy đọc từ đâu.

    Một bản render không nói độ phân giải thì không phân biệt được với một ảnh chụp màn hình
    máy tính, và cả điểm của năng lực này là "vẽ đúng màn hình thật".
    """
    hs = _hs()
    hs.nguon["lcd.width"] = "Màn hình màu LCD 4 inch 800x480"
    h = HT.dung_html(_mh(), hs)
    assert "800" in h and "480" in h
    assert "OTM8009A" in h
    assert "Màn hình màu LCD 4 inch 800x480" in h, "trích dẫn nguồn phải có trong trang"


def test_html_THOAT_chu_nguoi_dung_nhap():
    """Chữ trong thiết kế đi vào HTML phải được thoát.

    Chữ ấy có thể do mô hình sinh từ lời người dùng, nên `<` và `&` trong đó không được thành
    thẻ. Đây không phải lo xa về bảo mật — nó là lý do một nhãn `a < b` làm vỡ cả trang.
    """
    h = HT.dung_html(_mh(MO.PhanTu(id="t1", loai="text", x=0, y=0, w=400, h=30,
                                   chu="<b>a & b</b>", co_chu=12)), _hs())
    assert "&lt;b&gt;" in h and "&amp;" in h
    assert "<b>a" not in h


def test_html_ve_du_SAU_loai_phan_tu():
    """Sáu loại phần tử của bộ widget đã chốt — mỗi loại phải ra một thứ nhìn thấy được."""
    mh = _mh(
        MO.PhanTu(id="t", loai="text", x=0, y=0, w=200, h=24, chu="T", co_chu=16),
        MO.PhanTu(id="r", loai="rect", x=0, y=30, w=100, h=40, mau_nen="#112233"),
        MO.PhanTu(id="l", loai="line", x=0, y=80, w=200, h=1, mau_nen="#445566"),
        MO.PhanTu(id="i", loai="image", x=0, y=90, w=64, h=64, nguon="logo.bmp"),
        MO.PhanTu(id="p", loai="bar", x=0, y=170, w=300, h=20, gia_tri=60),
        MO.PhanTu(id="b", loai="button", x=0, y=200, w=200, h=90, chu="OK", co_chu=20))
    h = HT.dung_html(mh, _hs())
    for pid in ("t", "r", "l", "i", "p", "b"):
        assert f'data-id="{pid}"' in h, pid
    assert "60%" in h or "width:180px" in h.replace(" ", ""), "thanh tiến trình phải thể hiện 60%"


def test_html_mang_theo_KET_QUA_KIEM_khi_co_loi():
    """Bản render phải nói ra lỗi của chính nó, không vẽ một màn hình đẹp rồi im lặng.

    Một phần tử tràn biên vẫn vẽ được trong HTML (trình duyệt không cắt), nên nếu trang không
    tự khai thì nó **đẹp hơn** màn hình thật — đúng cái N6 cấm.
    """
    mh = _mh(MO.PhanTu(id="r1", loai="rect", x=700, y=10, w=200, h=50))
    kq = MO.kiem(mh, _hs())
    h = HT.dung_html(mh, _hs(), kq=kq)
    assert "E1101" in h
    assert "r1" in h


def test_html_khong_co_loi_thi_TU_KHAI_PHAM_VI_da_kiem():
    """"Không lỗi" phải kèm danh sách đã kiểm gì — không thì nó đọc thành "thiết kế đúng hết".

    Đúng bài học DEV-362: một dòng "không thấy gì" không kèm phạm vi sẽ được đọc thành "không
    có gì". Bản render này KHÔNG kiểm được màn hình thật sáng ra sao, nên nó phải nói.
    """
    mh = _mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=400, h=30, chu="OK", co_chu=16))
    h = HT.dung_html(mh, _hs(), kq=MO.kiem(mh, _hs()))
    assert "biên" in h.lower() and "cỡ chữ" in h.lower()
    assert "KHÔNG" in h, "phải tự khai những gì nó không kiểm được"


# =========================================================================== E2E hồ sơ thật
def test_E2E_tu_TAI_LIEU_THAT_den_HTML(tmp_path):
    """Đi hết đường: tài liệu thật trong repo → hồ sơ → mô hình → kiểm → HTML.

    Không bước nào trong chuỗi này dùng một con số tôi gõ vào: `800×480` đến từ
    `tai-lieu-kien-truc-c4.md`, kích thước font đến từ `font24.c`, và cả hai đều nằm trong repo.
    """
    from pathlib import Path

    from eide.knowledge.man_hinh import ho_so_tu_chu

    p = Path(__file__).parents[1] / "du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md"
    if not p.is_file():
        pytest.skip("không có tài liệu kiến trúc trong repo")
    hs = ho_so_tu_chu(p.read_text("utf-8"))
    assert hs.hop_le

    mh = MO.ManHinh(ten="chinh", rong=hs.rong, cao=hs.cao, he_mau=hs.he_mau, phan_tu=[
        MO.PhanTu(id="tieu_de", loai="text", x=20, y=16, w=760, h=24,
                  chu="PTIT - FreeRTOS", co_chu=24, mau_chu="#FFFFFF"),
        MO.PhanTu(id="vach", loai="line", x=20, y=48, w=760, h=2, mau_nen="#2563EB"),
        MO.PhanTu(id="nhiet", loai="text", x=20, y=70, w=400, h=20,
                  chu="Nhiet do: 25 C", co_chu=20, mau_chu="#E5E7EB"),
        MO.PhanTu(id="tt", loai="bar", x=20, y=110, w=760, h=24, gia_tri=65),
    ])
    kq = MO.kiem(mh, hs)
    assert kq.loi == [], kq.loi
    h = HT.dung_html(mh, hs, kq=kq)
    (tmp_path / "mh.html").write_text(h, "utf-8")
    assert (tmp_path / "mh.html").stat().st_size > 800
    assert "800" in h and "OTM8009A" in h


# ============ chữ ngoài ASCII: ĐỌC RA NGOÀI BẢNG FONT, không phải "mất dấu"
def test_chu_CO_DAU_la_LOI_doc_ra_ngoai_bang_font():
    """Một nhãn tiếng Việt có dấu trên panel này **không phải** "mất dấu" — nó là một phép
    đọc ra ngoài bảng font, và nó vẽ ra pixel rác.

    Đo trên chính mã BSP trong repo, không nhớ lại:

    * `font{8,12,16,20,24}.c` mỗi bảng có đúng **95 ký tự** — suy từ số byte bảng chia cho
      `Height × ((Width + 7) / 8)`. Tức ASCII **0x20..0x7E**.
    * `stm32469i_discovery_lcd.c:817` tra `table[(Ascii - ' ') * Height * ((Width+7)/8)]` —
      **không** kiểm biên.

    Nên `'ộ'` (UTF-8 `0xE1 0xBB 0xD9`) cho chỉ số `0xE1 - 0x20 = 193`, và `193 × 72 = 13 896`
    byte vào một bảng dài **6 840** byte: đọc hơn 7 KB quá bảng. Mã vẫn dịch, vẫn nạp, và màn
    hình hiện pixel rác — đúng hình dạng "trình biên dịch im lặng tuyệt đối".

    Bằng chứng thứ hai, từ firmware ĐANG CHẠY trên bo: `main.c` viết
    `"Hoc vien: Vu Tri Cong"` — chữ không dấu. Người viết nó đã biết điều này.
    """
    assert (MO.ASCII_DAU, MO.ASCII_CUOI) == (0x20, 0x7E)
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=700, h=30,
                               chu="Nhiệt độ", co_chu=24)), _hs())
    loi = [x for x in kq.loi if x["ma"] == "E1108"]
    assert loi, [x["ma"] for x in kq.loi]
    assert "ệ" in loi[0]["vi_sao"] or "ộ" in loi[0]["vi_sao"], loi[0]["vi_sao"]
    # Phải nói CÁCH SỬA bằng chính chuỗi không dấu, để người dùng dán vào được.
    assert "Nhiet do" in loi[0]["cach_sua"], loi[0]["cach_sua"]


def test_chu_KHONG_DAU_thi_khong_keu():
    """Ca âm — và nó cần, vì không có nó thì phép kiểm trên có thể đang kêu ở mọi chuỗi."""
    kq = MO.kiem(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=700, h=30,
                               chu="Nhiet do: 25 C", co_chu=24)), _hs())
    assert [x for x in kq.loi if x["ma"] == "E1108"] == [], kq.loi


def test_bo_dau_giu_dung_SO_KY_TU():
    """Phép bỏ dấu phải giữ đúng số ký tự, vì bề rộng chữ tính theo số ký tự.

    `"Nhiệt độ"` có 8 ký tự; nếu phép bỏ dấu cho ra 10 ký tự (tách `ê` thành `e` + dấu) thì
    lời khuyên "dùng chuỗi này" sẽ kèm một bề rộng sai, và người dùng sửa xong vẫn bị cắt chữ.
    """
    assert MO.bo_dau("Nhiệt độ") == "Nhiet do"
    assert len(MO.bo_dau("Nhiệt độ")) == len("Nhiệt độ")
    assert MO.bo_dau("Đường Đi") == "Duong Di"
    assert MO.bo_dau("ASCII 123") == "ASCII 123"


# =========================================================================== sinh code C
def test_sinh_C_luon_dung_LEFT_MODE_va_TU_TINH_x():
    """Căn giữa phải tự tính x, KHÔNG được sinh `CENTER_MODE`.

    Đọc `stm32469i_discovery_lcd.c:846-848`: `CENTER_MODE` tính
    `refcolumn = Xpos + ((xsize - size) * Width) / 2` với `xsize = BSP_LCD_GetXSize()/Width`
    — tức căn giữa theo **cả màn hình 800 px**, không theo ô chứa chữ. Một nhãn căn giữa trong
    ô `x=100, w=300` mà sinh `CENTER_MODE` sẽ nằm sai chỗ, và bản render HTML **không báo gì**
    vì HTML căn giữa đúng trong ô.

    Chữ "OK" ở Font24 rộng 2×17 = 34 px; ô 300 px → x = 100 + (300-34)/2 = 233.
    """
    from eide.man_hinh import sinh_c as SC

    c = SC.sinh_c(_mh(MO.PhanTu(id="t1", loai="text", x=100, y=50, w=300, h=30,
                                chu="OK", co_chu=24, can_le="center")), _hs())
    assert "CENTER_MODE" not in c, "CENTER_MODE căn giữa theo CẢ MÀN HÌNH — xem BSP dòng 848"
    assert "RIGHT_MODE" not in c, "RIGHT_MODE lấy ÂM Xpos — xem BSP dòng 858"
    assert "BSP_LCD_DisplayStringAt(233, 50," in c, c


def test_sinh_C_KEP_x_toi_thieu_1():
    """`x = 0` phải thành `1` trong code sinh ra.

    `stm32469i_discovery_lcd.c:869`: `if ((refcolumn < 1) || …) refcolumn = 1;` — BSP tự đổi
    `Xpos = 0` thành `1`. Sinh ra `0` thì code và màn hình lệch nhau một pixel mà không ai biết
    vì sao; sinh ra `1` thì tệp C nói đúng điều thiết bị làm.
    """
    from eide.man_hinh import sinh_c as SC

    c = SC.sinh_c(_mh(MO.PhanTu(id="t1", loai="text", x=0, y=10, w=400, h=30,
                                chu="X", co_chu=16)), _hs())
    assert "BSP_LCD_DisplayStringAt(1, 10," in c, c


def test_sinh_C_mau_la_ARGB8888_tra_tu_header():
    """Màu trong code C là `0xFFRRGGBB` — tra từ `LCD_COLOR_WHITE 0xFFFFFFFF` trong header."""
    from eide.man_hinh import sinh_c as SC

    c = SC.sinh_c(_mh(MO.PhanTu(id="r1", loai="rect", x=0, y=0, w=10, h=10,
                                mau_nen="#2563EB")), _hs())
    assert "0xFF2563EBU" in c, c


def test_sinh_C_KHONG_sinh_chuoi_co_ky_tu_ngoai_bang_font():
    """Chuỗi có dấu thì KHÔNG sinh lời gọi — và nói rõ vì sao, không âm thầm bỏ dấu hộ.

    Sinh ra lời gọi ấy là sinh ra một phép **đọc ra ngoài bảng font** (xem E1108): dịch sạch,
    nạp xong, màn hình hiện pixel rác. Còn bỏ dấu hộ là sửa thiết kế của người khác mà không
    hỏi — và lần sau họ sinh lại sẽ thấy một chuỗi mình không gõ.
    """
    from eide.man_hinh import sinh_c as SC

    c = SC.sinh_c(_mh(MO.PhanTu(id="t1", loai="text", x=10, y=10, w=700, h=30,
                                chu="Nhiệt độ", co_chu=24)), _hs())
    assert "DisplayStringAt" not in c
    assert "BỎ QUA" in c and "Nhiet do" in c, c


def test_sinh_C_tu_khai_TIEN_DE_va_canh_bao_khi_con_loi():
    """Tệp C phải tự khai nó cần gì đã chạy trước, và phải chép lỗi vào đầu tệp nếu còn lỗi.

    Một tệp sinh ra từ một bản thiết kế còn lỗi mà không nói gì sẽ được đọc là một tệp dùng
    được — và nó dịch sạch, nên không bước nào bác lại.
    """
    from eide.man_hinh import sinh_c as SC

    mh = _mh(MO.PhanTu(id="r1", loai="rect", x=700, y=10, w=200, h=50))
    c = SC.sinh_c(mh, _hs(), kq=MO.kiem(mh, _hs()))
    assert "BSP_LCD_Init" in c and "TIỀN ĐỀ" in c
    assert "KHÔNG sinh" in c, "phải tự khai nó không sinh phần khởi tạo"
    assert "E1101" in c, "lỗi của bản thiết kế phải có trong đầu tệp"


def test_ten_ham_C_hop_le():
    from eide.man_hinh import sinh_c as SC

    assert SC.ten_ham("chinh") == "ui_ve_chinh"
    assert SC.ten_ham("Màn hình chính") == "ui_ve_man_hinh_chinh"
    assert SC.ten_ham("2-trang") == "ui_ve_mh_2_trang"
    assert SC.ten_ham("") == "ui_ve_man_hinh"


# =========================================================================== DỊCH THẬT
def _bsp():
    from pathlib import Path
    return Path(__file__).parents[1] / "docs/stm32f469/firmware-chay-duoc"


_CO_ARM = __import__("shutil").which("arm-none-eabi-gcc") is not None
can_arm = pytest.mark.skipif(not _CO_ARM, reason="máy không có arm-none-eabi-gcc")


@can_arm
def test_code_sinh_ra_DICH_DUOC_bang_trinh_dich_THAT(tmp_path):
    """Phép đo của cả bước sinh code: `arm-none-eabi-gcc` dịch được tệp sinh ra, trên chính
    header BSP có trong repo.

    Vì sao ca này là ca đáng giá nhất ở đây: mọi ca trên chỉ so chuỗi, và một bộ sinh code
    "khớp chuỗi" có thể sinh ra `BSP_LCD_FillRect(1,2,3)` — thiếu một tham số — mà mọi phép so
    chuỗi vẫn xanh. Chỉ trình dịch mới nói được điều đó. Đây đúng bài học "ô xanh của bộ kiểm
    nói về tệp test": test xanh chưa nói gì về sản phẩm.

    Cờ dịch: `-mcpu=cortex-m4 -mthumb -ffreestanding` — `-ffreestanding` cần vì bo không có
    newlib trên máy này, và đó là một phép đo, không phải một phỏng đoán (xem DEV log).
    """
    import subprocess

    from eide.man_hinh import sinh_c as SC

    bsp = _bsp()
    if not (bsp / "stm32469i_discovery_lcd.h").is_file():
        pytest.skip("không có header BSP trong repo")

    mh = _mh(
        MO.PhanTu(id="tieu_de", loai="text", x=20, y=16, w=760, h=24,
                  chu="PTIT - FreeRTOS", co_chu=24, mau_chu="#FFFFFF", can_le="center"),
        MO.PhanTu(id="vach", loai="line", x=20, y=48, w=760, h=2, mau_nen="#2563EB"),
        MO.PhanTu(id="khung", loai="rect", x=20, y=60, w=360, h=120, mau_chu="#6B7280"),
        MO.PhanTu(id="nen", loai="rect", x=400, y=60, w=380, h=120, mau_nen="#111827"),
        MO.PhanTu(id="nhiet", loai="text", x=30, y=70, w=340, h=20,
                  chu="Nhiet do: 25 C", co_chu=20, can_le="right"),
        MO.PhanTu(id="tt", loai="bar", x=20, y=200, w=760, h=24, gia_tri=65),
        MO.PhanTu(id="logo", loai="image", x=20, y=240, w=64, h=64, nguon="logo_ptit.bmp"),
        MO.PhanTu(id="nut", loai="button", x=560, y=380, w=220, h=90, chu="BAT DAU",
                  co_chu=20))
    kq = MO.kiem(mh, _hs())
    assert kq.loi == [], kq.loi

    c = SC.sinh_c(mh, _hs(), kq=kq)
    tep = tmp_path / "ui_chinh.c"
    tep.write_text(c, "utf-8")

    r = subprocess.run(
        ["arm-none-eabi-gcc", "-c", "-o", str(tmp_path / "ui_chinh.o"),
         "-mcpu=cortex-m4", "-mthumb", "-ffreestanding",
         "-Wall", "-Wextra", "-Werror", "-I", str(bsp), str(tep)],
        capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, f"KHÔNG dịch được:\n{r.stdout}\n{r.stderr}\n--- tệp:\n{c}"
    assert (tmp_path / "ui_chinh.o").stat().st_size > 0

    # Và `nm` phải thấy đúng hàm vẽ — một tệp `.o` rỗng cũng "dịch được".
    n = subprocess.run(["arm-none-eabi-nm", str(tmp_path / "ui_chinh.o")],
                       capture_output=True, text=True, timeout=60)
    assert "ui_ve_chinh" in n.stdout, n.stdout


@can_arm
def test_code_sinh_ra_GOI_DUNG_chu_ky_BSP(tmp_path):
    """Và phép phá của chính ca trên: thiếu một tham số thì trình dịch phải ĐỎ.

    Không có ca này thì ca trên có thể đang xanh vì `-Werror` không bật được, hay vì tệp
    chẳng gọi hàm BSP nào. Ca này chứng minh vòng dịch THẬT SỰ bắt lỗi — tức ô xanh ở trên
    nói về sản phẩm, không nói về cách tôi gọi `subprocess`.
    """
    import subprocess

    bsp = _bsp()
    if not (bsp / "stm32469i_discovery_lcd.h").is_file():
        pytest.skip("không có header BSP trong repo")
    xau = ('#include "stm32469i_discovery_lcd.h"\n'
           "void f(void){ BSP_LCD_FillRect(1, 2, 3); }\n")      # thiếu tham số thứ tư
    tep = tmp_path / "xau.c"
    tep.write_text(xau, "utf-8")
    r = subprocess.run(
        ["arm-none-eabi-gcc", "-c", "-o", str(tmp_path / "xau.o"),
         "-mcpu=cortex-m4", "-mthumb", "-ffreestanding", "-Wall", "-Wextra", "-Werror",
         "-I", str(bsp), str(tep)],
        capture_output=True, text=True, timeout=180)
    assert r.returncode != 0, "vòng dịch KHÔNG bắt lỗi → ô xanh của ca trên vô nghĩa"


# =========================================================================== E2E qua CÔNG CỤ
EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}

_TL_MAN_HINH = """# Bo thu nghiem

## Man hinh
Man hinh mau LCD 4 inch 800x480, driver OTM8009A noi qua bus 2-lane MIPI-DSI.
FrameBuffer do hoa LCD 800x480 (RGB565), co cam ung dien dung.
"""


@pytest.fixture
def du_an_mh(tmp_path):
    goc = tmp_path / "du-an-mh"
    goc.mkdir()
    (goc / "bo.md").write_text(_TL_MAN_HINH, "utf-8")
    return goc


@pytest.fixture
def bo(du_an_mh):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    ag = Agent(Config.for_project(du_an_mh), llm=ScriptedGateway([]), project_name="du-an-mh")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-mh")
    return ag, ctx


def test_luoc_do_nam_cong_cu(bo):
    """Năm công cụ `core=False`, mô tả ≤ 400 ký tự (N-11), và tiền tố KHÔNG lẫn với `ui.*`.

    `ui.explain`/`ui.notice` đã tồn tại và chúng nói về giao diện của chính EIDE. Đặt
    `ui.render` cạnh `ui.explain` là mời mô hình gọi sai công cụ.
    """
    ag, _ = bo
    ten = {"display.profile", "screen.set", "screen.check", "screen.render", "screen.codegen"}
    sp = {s.name: s for s in (ag.registry.all() if hasattr(ag.registry, "all")
                              else ag.registry.tools.values())}
    assert ten <= set(sp), sorted(ten - set(sp))
    for t in ten:
        assert sp[t].core is False, t
        assert len(sp[t].summary_vi) <= 400, (t, len(sp[t].summary_vi))
    assert "ui.render" not in sp and "ui.screen_set" not in sp


def test_E2E_cong_cu_tu_TAI_LIEU_den_HTML_va_C(bo):
    """Đi hết năm công cụ trên một dự án thật: tài liệu → hồ sơ → thiết kế → kiểm → HTML → C.

    Không bước nào nhận một con số do tôi gõ vào: `800×480` và `RGB565` đến từ tệp tài liệu
    trong dự án, và cả hai đi qua kho dưới dạng hiện vật.
    """
    ag, ctx = bo

    r = ag.registry.run("doc.load", {"path": "bo.md", "doc_id": "BO-1",
                                     "nguon": "noi_bo", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")

    r = ag.registry.run("display.profile", {"doc_id": "BO-1", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["hop_le"] is True, r.data
    assert (r.data["rong"], r.data["cao"]) == (800, 480), r.data
    assert r.data["he_mau"] == "RGB565", r.data
    # Hiện vật phải vào kho, không chỉ trả về trong kết quả (DEV-341).
    a = ag.store.get("display:main")
    assert a is not None and a["type"] == "display", a
    assert a["canonical"]["nguon"]["lcd.width"], a["canonical"]["nguon"]

    r = ag.registry.run("screen.set", {
        "ten": "chinh", "explain": EX, "mau_nen": "#000000",
        "phan_tu": [
            {"id": "tieu_de", "loai": "text", "x": 20, "y": 16, "w": 760, "h": 24,
             "chu": "PTIT - FreeRTOS", "co_chu": 24, "mau_chu": "#FFFFFF",
             "can_le": "center"},
            {"id": "vach", "loai": "line", "x": 20, "y": 48, "w": 760, "h": 2,
             "mau_nen": "#2563EB"},
            {"id": "tt", "loai": "bar", "x": 20, "y": 200, "w": 760, "h": 24,
             "gia_tri": 65},
        ]}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_loi"] == 0, r.data["loi"]
    b = ag.store.get("ui_screen:chinh")
    assert b is not None and b["type"] == "ui_screen"
    # Bản thiết kế phải khai nó dựng từ hồ sơ nào — không thì sửa hồ sơ không làm nó STALE.
    assert "display:main" in str(b.get("deps") or b.get("canonical", {}).get("deps") or "") \
        or "display:main" in str(b), "phải khai upstream là hồ sơ panel"

    r = ag.registry.run("screen.check", {"ten": "chinh"}, ctx)
    assert r.ok and r.data["so_loi"] == 0, r.data
    assert r.data["ngoai_pham_vi"], "phải TỰ KHAI những gì nó không kiểm được"

    r = ag.registry.run("screen.render", {"ten": "chinh", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    tep = ag.config.paths.project_root / r.data["tep"]
    assert tep.is_file(), r.data
    h = tep.read_text("utf-8")
    assert "width:800px" in h.replace(" ", "") and "OTM8009A" in h
    assert "800x480" in h or "800 × 480" in h

    r = ag.registry.run("screen.codegen", {"ten": "chinh", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    c = (ag.config.paths.project_root / r.data["tep"]).read_text("utf-8")
    assert "ui_ve_chinh" in c and "BSP_LCD_DisplayStringAt" in c
    assert "CENTER_MODE" not in c


def test_screen_set_KHONG_CHAY_khi_chua_co_ho_so(bo):
    """Không có hồ sơ panel thì `screen.set` phải TỪ CHỐI và nói gọi gì trước.

    Đây là cửa giữ cho cả năng lực còn nghĩa: cho phép thiết kế mà chưa có hồ sơ là mời mô
    hình tự điền `800×480` — đúng cái lỗi hồ sơ màn hình dựng ra để chặn.
    """
    ag, ctx = bo
    r = ag.registry.run("screen.set", {
        "ten": "x", "explain": EX,
        "phan_tu": [{"id": "a", "loai": "rect", "x": 0, "y": 0, "w": 10, "h": 10}]}, ctx)
    assert not r.ok
    assert r.error.code == "E1110", r.error.code
    assert "display.profile" in str(r.error.alternatives), r.error.alternatives


def test_screen_set_KHONG_CO_tham_so_do_phan_giai(bo):
    """Lược đồ của `screen.set` KHÔNG được có `rong`/`cao`.

    Nếu có, mô hình sẽ điền chúng từ ký ức, và bản thiết kế sẽ vẽ cho một màn hình tưởng
    tượng. Ca này canh một quyết định thiết kế, không canh một dòng mã — nên nó phải đọc
    chính lược đồ.
    """
    ag, _ = bo
    sp = {s.name: s for s in (ag.registry.all() if hasattr(ag.registry, "all")
                              else ag.registry.tools.values())}
    thuoc_tinh = set((sp["screen.set"].params.get("properties") or {}))
    assert "rong" not in thuoc_tinh and "cao" not in thuoc_tinh, sorted(thuoc_tinh)
    assert "he_mau" not in thuoc_tinh, "hệ màu cũng phải lấy từ hồ sơ"


def test_ho_so_KHONG_HOP_LE_thi_screen_set_tu_choi(bo):
    """Tài liệu không nói gì về màn hình → hồ sơ ghi được nhưng `screen.set` từ chối.

    Hồ sơ vẫn được ghi (nó là bằng chứng rằng tài liệu ấy KHÔNG nói), nhưng nó không mở cửa
    cho bước thiết kế — và lời từ chối phải nói tài liệu thiếu gì.
    """
    ag, ctx = bo
    (ag.config.paths.project_root / "khac.md").write_text(
        "# Bo khac\nChip STM32F103, 64 KB Flash.\n", "utf-8")
    r = ag.registry.run("doc.load", {"path": "khac.md", "doc_id": "BO-2",
                                     "nguon": "noi_bo", "explain": EX}, ctx)
    assert r.ok
    r = ag.registry.run("display.profile", {"doc_id": "BO-2", "ten": "khac",
                                            "explain": EX}, ctx)
    assert r.ok and r.data["hop_le"] is False, r.data
    assert "lcd.width" in r.data["thieu"], r.data["thieu"]
    r = ag.registry.run("screen.set", {
        "ten": "y", "ho_so": "khac", "explain": EX,
        "phan_tu": [{"id": "a", "loai": "rect", "x": 0, "y": 0, "w": 10, "h": 10}]}, ctx)
    assert not r.ok and r.error.code == "E1113", getattr(r.error, "code", None)


# =========================================================================== bề mặt A15
def test_be_mat_A15_co_trong_danh_sach():
    from eide.surfaces import SURFACES

    assert ("screen", "A15", "Màn hình") in SURFACES, SURFACES


def test_be_mat_A15_RONG_noi_du_BA_THU(bo):
    """Bề mặt rỗng phải nói: chưa có gì · vì sao chưa có · cần gì để có (E3.2 §5).

    Đây là chỗ dễ nói dối nhất của tab này: một khung vẽ trống trông **y như** một màn hình
    đen hợp lệ, nên "không có gì" phải nói ra bằng chữ.
    """
    from eide import surfaces

    ag, _ = bo
    m = surfaces.screen(ag.store, ag.inv if hasattr(ag, "inv") else None,
                        str(ag.config.paths.project_root))
    assert m["code"] == "A15" and m["surface"] == "screen"
    rong = [b for b in m["blocks"] if b["type"] == "empty"]
    assert rong, [b["type"] for b in m["blocks"]]
    for b in rong:
        assert b.get("chua_co") and b.get("vi_sao") and b.get("can_gi"), b
    # Và khối rỗng của hồ sơ phải nói ĐÚNG cái rủi ro, không nói chung chung.
    hs = next(b for b in rong if b["code"] == "A15.1")
    assert "tự nhớ" in hs["vi_sao"], hs["vi_sao"]


def test_be_mat_A15_dung_tu_HIEN_VAT_that(bo):
    """Đi hết năm công cụ rồi dựng bề mặt: khối `html` phải trỏ đúng tệp, và bảng kiểm phải
    có mặt kèm phần TỰ KHAI phạm vi.
    """
    from eide import surfaces

    ag, ctx = bo
    assert ag.registry.run("doc.load", {"path": "bo.md", "doc_id": "BO-1",
                                        "nguon": "noi_bo", "explain": EX}, ctx).ok
    assert ag.registry.run("display.profile", {"doc_id": "BO-1", "explain": EX}, ctx).ok
    assert ag.registry.run("screen.set", {
        "ten": "chinh", "explain": EX,
        "phan_tu": [{"id": "t", "loai": "text", "x": 20, "y": 16, "w": 400, "h": 24,
                     "chu": "Xin chao", "co_chu": 20}]}, ctx).ok
    r = ag.registry.run("screen.render", {"ten": "chinh", "explain": EX}, ctx)
    assert r.ok
    assert ag.registry.run("screen.codegen", {"ten": "chinh", "explain": EX}, ctx).ok

    m = surfaces.screen(ag.store, None, str(ag.config.paths.project_root))
    theo = {b["code"]: b for b in m["blocks"]}

    hs = theo["A15.1"]
    assert hs["type"] == "table"
    hang = {r[0]: r for r in hs["rows"]}
    assert "800 × 480 px" in hang["Độ phân giải"][1], hang["Độ phân giải"]
    assert hang["Độ phân giải"][2].strip() not in ("", "— không có trích dẫn"), \
        "mỗi dòng hồ sơ phải mang TRÍCH DẪN"

    html_khoi = [b for b in m["blocks"] if b["type"] == "html"]
    assert html_khoi, [b["type"] for b in m["blocks"]]
    tep = ag.config.paths.project_root / html_khoi[0]["tep"]
    assert tep.is_file(), html_khoi[0]
    assert "{ref}" in html_khoi[0]["bam_phan_tu"], "câu hỏi khi bấm do LÕI soạn"

    assert theo["A15.3"]["type"] == "table"
    # Phần tự khai phạm vi phải LUÔN có, kể cả khi không lỗi — không thì "không lỗi" ở trên
    # sẽ được đọc thành "thiết kế đúng hết".
    pv = theo["A15.3b"]
    muc = {s["title"]: s["items"] for s in pv["sections"]}
    assert muc["Đã chạm tới"] and muc["KHÔNG kiểm được"], pv

    assert theo["A15.4"]["type"] == "table" and theo["A15.4"]["rows"], theo["A15.4"]
    assert "ui_ve_chinh" in str(theo["A15.4"]["rows"]), theo["A15.4"]["rows"]


def test_giao_dien_biet_ve_khoi_html():
    """Giao diện Swift phải có nhánh cho khối `html`.

    Không có nhánh thì `SurfaceView` rơi vào `default` và hiện *"Giao diện chưa biết vẽ khối
    loại html"* — tức cả tab này thành một dòng cảnh báo. Ca kiểm đọc chính tệp Swift, vì đây
    là một hợp đồng giữa hai phía viết bằng hai ngôn ngữ khác nhau.
    """
    sw = (GOC / "ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift").read_text("utf-8")
    assert 'case "html":' in sw, "SurfaceView chưa biết vẽ khối `html`"
    assert "struct KhoiHTML" in sw and "struct TrangHTML" in sw
    # Trang mở từ TỆP, không nhận chuỗi HTML qua giao thức — một trang vài chục KB trong mỗi
    # `surface.set` sẽ làm nặng mọi lượt kể cả khi không ai mở tab này.
    assert "loadFileURL" in sw


def test_tab_moi_co_ten_ngan_trong_giao_dien():
    """Thanh tab rút gọn tên khi cửa sổ chật; tab mới thiếu tên ngắn sẽ hiện tên dài và đẩy
    các tab khác ra ngoài khung."""
    sw = (GOC / "ui/EIDEApp/Sources/EIDE/Views/RootView.swift").read_text("utf-8")
    assert '"screen": "Màn hình"' in sw, "thiếu tên ngắn cho tab `screen`"


def test_luong_hoa_dung_phep_PHAN_CUNG_khong_dung_nhan_ti_le():
    """`#181818` phân biệt được hai phép mở rộng; `#FF8040` thì không.

    Kênh 5 bit: `0x18 >> 3 = 3`. Phép phần cứng lặp bit cao — `(3 << 3) | (3 >> 2) = 24`, tức
    `0x18`. Phép nhân tỉ lệ — `3 × 255 / 31 = 24,68 → 25`, tức `0x19`. Hai con số khác nhau,
    và con số ĐÚNG là con số LTDC/DMA2D dùng.

    Bản mẫu trước của tôi dùng `#FF8040`, và với giá trị ấy **hai phép cho cùng kết quả** —
    nên phép phá "đổi sang nhân tỉ lệ" LỌT. Đúng hình dạng "hai vế tình cờ bằng nhau" đã lặp
    suốt dự án này; chỗ chữa là chọn dữ liệu PHÂN BIỆT được hai nhánh, không phải thêm ca.
    """
    assert MO.luong_hoa("#181818", "RGB565") == "#181818"
    assert MO.luong_hoa("#181818", "RGB565") != "#191819", "đây là kết quả của NHÂN TỈ LỆ"
    # Và một giá trị nữa cho chắc, ở kênh lục 6 bit.
    assert MO.luong_hoa("#000C00", "RGB565") == "#000C00"
