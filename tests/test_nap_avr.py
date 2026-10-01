# -*- coding: utf-8 -*-
"""Tác tử phải tự nạp được bo AVR, không chỉ bo ST.

Phiên robot MOBILUCK chạm vào một lỗ hổng: tác tử biên dịch được firmware ATmega328P
(`build.compile` gọi `avr-gcc`) rồi **dừng ở đó**. Cả đường nạp của EIDE chỉ biết ST-LINK —
`st-flash` và ổ đĩa MSD của bo Discovery/Nucleo. `avrdude` chỉ có tên trong danh sách kiểm
công cụ, không nằm trên đường nạp nào.

Đo được trên bo thật đang cắm: `target.detect` trả `nap_duoc=false`, `note_vi` ghi *"KHÔNG có
đường nạp nào"* — với một bo Arduino Nano cắm hẳn hoi ở `/dev/cu.usbserial-21410`.

Anh Công: *"Phải để agent làm chứ. Sai thì fix cho agent thông minh hơn."*

## Hai chỗ dễ sai mà bộ kiểm này canh

**Cổng USB nối tiếp KHÔNG phải bằng chứng có chip.** Nó là con chip cầu USB (CH340/FTDI) và
vẫn hiện ra kể cả khi đã nhổ ATmega khỏi đế. Chỉ khi bắt tay được với bootloader mới biết.

**Mọi thao tác avrdude đều reset bo** qua đường DTR. Với robot đang cân bằng thì reset là ngã.
Nên phép đọc chữ ký KHÔNG tự chạy — nó là lựa chọn tác tử phải nêu ra.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from eide.build import mach_that as MT
from eide.tools.mach_that import _goc_chip, _noi_avr


# ========================================================= chữ ký chip: đọc từ SILICON
def test_chu_ky_doc_duoc_thanh_ten_chip(monkeypatch):
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(
        0, "avrdude: Device signature = 0x1e950f (probably m328p)"))
    ten, ky, vi_sao = MT.doc_chu_ky_avr("/dev/cu.usbserial-1")
    assert (ten, ky, vi_sao) == ("ATmega328P", "1e950f", "")


def test_nhan_ca_hai_kieu_in_chu_ky(monkeypatch):
    """avrdude 6.x (bản Arduino) và 7.x (bản Homebrew) in khác nhau. Nhận cả hai."""
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(
        0, "Device signature = 0x1e 0x95 0x0f"))
    assert MT.doc_chu_ky_avr("/dev/x")[:2] == ("ATmega328P", "1e950f")


def test_chu_ky_la_thi_NOI_RA_chu_khong_doan(monkeypatch):
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(
        0, "Device signature = 0xabcdef"))
    ten, ky, vi_sao = MT.doc_chu_ky_avr("/dev/x")
    assert ten == "" and ky == "abcdef" and "chưa có trong bảng" in vi_sao


def test_khong_bat_tay_duoc_thi_noi_nguyen_van(monkeypatch):
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(
        1, "avrdude: stk500_recv(): programmer is not responding"))
    ten, ky, vi_sao = MT.doc_chu_ky_avr("/dev/x")
    assert ten == "" and ky == ""
    assert "not responding" in vi_sao


def test_thieu_avrdude_thi_noi_cach_cai(monkeypatch):
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("", "", "máy chưa có `avrdude`"))
    assert "avrdude" in MT.doc_chu_ky_avr("/dev/x")[2]


# ===================================================== cổng nối tiếp LÀ một đường nạp
def test_cong_usb_duoc_tinh_la_nap_duoc(monkeypatch, tmp_path):
    """Trước bản vá, trường này để trống nên `do_bo()` kết luận KHÔNG có đường nạp nào."""
    (tmp_path / "cu.usbserial-21410").touch()
    monkeypatch.setattr(MT, "THU_MUC_DEV", tmp_path)
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    ds = MT._cong_noi_tiep()
    cong = [b for b in ds if "usbserial" in b.ten]
    assert cong and cong[0].nap_duoc_bang == "avrdude"


def test_khong_co_avrdude_thi_KHONG_khai_nap_duoc(monkeypatch, tmp_path):
    """Khai có đường nạp trong khi máy thiếu công cụ là hứa một việc sẽ hỏng lúc làm thật."""
    (tmp_path / "cu.usbserial-21410").touch()
    monkeypatch.setattr(MT, "THU_MUC_DEV", tmp_path)
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("", "", "chưa cài"))
    assert all(not b.nap_duoc_bang for b in MT._cong_noi_tiep())


def test_bluetooth_khong_bi_tinh_la_bo(monkeypatch, tmp_path):
    (tmp_path / "cu.Bluetooth-Incoming-Port").touch()
    (tmp_path / "cu.JBLTune520BT").touch()
    monkeypatch.setattr(MT, "THU_MUC_DEV", tmp_path)
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    assert all(not b.nap_duoc_bang for b in MT._cong_noi_tiep())


# ================================================ "có cổng" KHÁC "có chip" — câu chữ phải rõ
def test_co_cong_nhung_chua_doc_chip_thi_NOI_RO():
    d = {"thiet_bi": [{"loai": "cong_noi_tiep", "nap_duoc_bang": "avrdude"}]}
    c = _noi_avr(d)
    assert "CHƯA bắt tay" in c
    assert "kể cả khi không có chip" in c
    assert "RESET bo" in c


def test_da_doc_chu_ky_thi_noi_da_reset():
    c = _noi_avr({"avr": {"doc_duoc": True, "chu_ky": "1e950f", "chip": "ATmega328P",
                          "cong": "/dev/cu.x", "baud": 57600}})
    assert "ĐÃ ĐỌC" in c and "1e950f" in c and "RESET" in c


def test_khong_co_cong_AVR_thi_cau_ve_AVR_rong():
    assert _noi_avr({"thiet_bi": [{"loai": "o_dia", "nap_duoc_bang": "sao_tep"}]}) == ""


# =========================================================== đọc Intel HEX để so từng byte
def test_doc_ihex_dung_theo_dia_chi(tmp_path):
    p = tmp_path / "a.hex"
    p.write_text(":03000000AABBCC93\n:00000001FF\n", "utf-8")
    assert MT._byte_tu_ihex(p) == bytes([0xAA, 0xBB, 0xCC])


def test_ihex_co_khoang_trong_thi_dien_FF(tmp_path):
    p = tmp_path / "a.hex"
    p.write_text(":01000000AA55\n:01000400BB40\n:00000001FF\n", "utf-8")
    assert MT._byte_tu_ihex(p) == bytes([0xAA, 0xFF, 0xFF, 0xFF, 0xBB])


def test_dong_hong_bi_bo_qua_chu_khong_nem_ngoai_le(tmp_path):
    p = tmp_path / "a.hex"
    p.write_text("rác\n:03000000AABBCC93\nZZZ\n:00000001FF\n", "utf-8")
    assert MT._byte_tu_ihex(p) == bytes([0xAA, 0xBB, 0xCC])


# ======================================================================== nạp: luật xanh/đỏ
def test_ma_thoat_0_ma_KHONG_co_verify_thi_khong_tinh_la_nap_xong(monkeypatch, tmp_path):
    """Cùng một luật với đường st-flash: lời của trình nạp không thay được bằng chứng."""
    h = tmp_path / "a.hex"
    h.write_text(":00000001FF\n", "utf-8")
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(0, "writing flash (5710 bytes)"))
    kq = MT.nap_qua_avrdude(h, "/dev/x")
    assert not kq.dat and "KHÔNG in dòng verify" in kq.vi_sao_khong_dat


def test_co_verify_thi_dat(monkeypatch, tmp_path):
    h = tmp_path / "a.hex"
    h.write_text(":00000001FF\n", "utf-8")
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(
        0, "5710 bytes of flash written\n5710 bytes of flash verified"))
    kq = MT.nap_qua_avrdude(h, "/dev/x")
    assert kq.dat and kq.da_verify and kq.cach == "avrdude"


def test_ma_thoat_khac_0_thi_noi_Flash_co_the_KHONG_nhat_quan(monkeypatch, tmp_path):
    h = tmp_path / "a.hex"
    h.write_text(":00000001FF\n", "utf-8")
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Ra(1, "stk500_recv(): timeout"))
    kq = MT.nap_qua_avrdude(h, "/dev/x")
    assert not kq.dat
    assert "KHÔNG nhất quán" in kq.vi_sao_khong_dat
    assert "57600" in kq.vi_sao_khong_dat   # gợi đúng nguyên nhân hay gặp nhất


def test_tep_rong_thi_tu_choi_truoc_khi_goi_avrdude(monkeypatch, tmp_path):
    h = tmp_path / "a.hex"
    h.write_bytes(b"")
    goi = []
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: goi.append(a) or _Ra(0, ""))
    kq = MT.nap_qua_avrdude(h, "/dev/x")
    assert not kq.dat and not goi, "đã gọi avrdude với một tệp rỗng"


# ===================================================================== tra mã chip avrdude
@pytest.mark.parametrize("vao,ra", [
    ("st.atmega328p@1.0.0", "ATmega328P"),
    ("ATmega328P", "ATmega328P"),
    ("atmega328p", "ATmega328P"),
    ("arduino.ATmega2560@2.1", "ATmega2560"),
    ("STM32F469NI", "STM32F469NI"),
])
def test_go_ho_chieu_ra_ten_chip(vao, ra):
    """Hộ chiếu ghi `ns.part@semver`; bảng avrdude tra theo tên. Lấy nhầm cả chuỗi thì tra
    không ra, và công cụ sẽ báo 'không biết mã chip' cho một dự án đã ghim chip đàng hoàng."""
    assert _goc_chip(vao) == ra


def test_moi_chu_ky_deu_tra_duoc_ma_avrdude():
    """Chip có trong bảng chữ ký mà không có mã avrdude thì đọc ra rồi vẫn không nạp được."""
    thieu = [t for t in MT._CHU_KY_AVR.values() if t not in MT._MA_AVRDUDE]
    assert not thieu, f"đọc được chữ ký nhưng không biết mã để nạp: {thieu}"


# =============================================================================== phụ
class _Ra:
    def __init__(self, ma: int, chu: str):
        self.returncode, self.stdout, self.stderr = ma, chu, ""


# ============================ ba phiên bản avrdude in chữ ký ba kiểu — bắt được trên bo thật
@pytest.mark.parametrize("dau_ra,mong", [
    ("Device signature = 0x1e950f", "1e950f"),                       # avrdude 6.x
    ("Device signature = 0x1e 0x95 0x0f", "1e950f"),                 # avrdude 7.x
    ("Device signature = 1E 95 0F (ATmega328P, ATA6614Q)", "1e950f"),  # avrdude 8.x
])
def test_doc_duoc_chu_ky_cua_CA_BA_phien_ban(dau_ra, mong):
    """Cả ba đều "chạy xong", chỉ khác chỗ in — đúng loại khác biệt chỉ lộ khi cắm bo thật."""
    assert MT._chu_ky_tu_dau_ra(dau_ra) == mong


def test_khong_co_chu_ky_thi_tra_rong():
    assert MT._chu_ky_tu_dau_ra("Avrdude done.  Thank you.") == ""


def test_lenh_doc_chu_ky_CO_co_v(monkeypatch):
    """avrdude 8.0 im lặng ở mức mặc định: bắt tay xong vẫn không in chữ ký.

    Lần đầu bài này báo "không đọc được chữ ký" cho một ATmega328P hoàn toàn khoẻ mạnh, chỉ
    vì thiếu một chữ `v`. Ca này canh đúng chữ ấy.
    """
    giu = {}
    monkeypatch.setattr(MT, "tim_avrdude", lambda: ("/giả/avrdude", "", ""))
    monkeypatch.setattr(subprocess, "run",
                        lambda c, **k: giu.update(lenh=c) or _Ra(0, "Device signature = 1E 95 0F"))
    MT.doc_chu_ky_avr("/dev/x")
    assert "-v" in giu["lenh"], "thiếu -v thì avrdude 8 không in chữ ký"
    assert "-n" in giu["lenh"], "thiếu -n thì phép DÒ lại đi GHI vào chip"
