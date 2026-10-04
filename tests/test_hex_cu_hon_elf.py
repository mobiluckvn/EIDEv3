# -*- coding: utf-8 -*-
"""DEV-337 — nạp `.hex` cũ hơn `.elf` bên cạnh, và đối chiếu vẫn thành công.

Đo được trên phiên robot ngày 04/10/2026.

`build.compile` sinh ra `.elf`. Trong `nap_qua_avrdude`, phép đổi elf→hex chỉ chạy khi người
gọi đưa đúng `.elf`; đưa `.hex` thì nạp nguyên tệp hex đang nằm trên đĩa, **già bao nhiêu cũng
nạp**. Trên đĩa lúc ấy: `mach.elf` dựng 19:30:08, `mach.hex` còn từ 19:08:58 — già 22 phút.

Hai chỗ khiến lỗi này **im lặng hoàn toàn**:

1. **Đối chiếu sau khi nạp vẫn ĐẠT.** Nó đọc ngược chip rồi so với tệp vừa ghi, nên nó khẳng
   định *thứ tôi ghi đúng là thứ đang nằm đó* — không khẳng định *thứ tôi dựng đúng là thứ
   đang nằm đó*.
2. **Phép so mốc dựng với mốc nạp cũng ĐẠT.** Nạp 12:30:30 vẫn sau dựng 12:30:08. Mốc đúng
   thứ tự mà nội dung vẫn sai, vì giữa hai mốc ấy có một **tệp thứ ba** không được cập nhật.

Hậu quả: ba lượt liền đo cổng nối tiếp không thấy dòng `#STAGE` mà mã nguồn có. Soát hàm có
tồn tại không — có. Có khai báo không — có. Có được gọi không — có. Có trong ảnh đã dịch không
— có, cả ký hiệu lẫn chuỗi trong `.rodata`. Mọi mắt đều nối. Chỉ **đọc ngược flash từ chip rồi
so nội dung** mới thấy chip đang chạy bản khác: 6 937 byte lệch, `#STAGE` có trong ảnh mà
không có trên chip.

Đây là anh em sinh đôi của lỗi bitstream FPGA hôm 03/10, chỉ nằm ở đường AVR.
"""

from __future__ import annotations

import pathlib
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from eide.build import mach_that as MT      # noqa: E402


def _dung_cap(tmp: pathlib.Path, *, hex_cu_hon: bool) -> pathlib.Path:
    """Dựng một cặp `mach.elf` / `mach.hex` với mốc thời gian đặt trước."""
    elf = tmp / "mach.elf"
    hx = tmp / "mach.hex"
    elf.write_bytes(b"\x7fELF" + b"\x00" * 64)
    hx.write_text(":00000001FF\n", "utf-8")
    moc = time.time()
    if hex_cu_hon:
        import os
        os.utime(hx, (moc - 600, moc - 600))     # hex già 10 phút
        os.utime(elf, (moc, moc))
    else:
        import os
        os.utime(elf, (moc - 600, moc - 600))    # elf già hơn: hex mới, bình thường
        os.utime(hx, (moc, moc))
    return hx


def test_hex_cu_hon_elf_thi_TU_CHOI_nap(tmp_path, monkeypatch):
    hx = _dung_cap(tmp_path, hex_cu_hon=True)
    # Chặn mọi thứ chạm tới phần cứng: ca này chỉ đo chốt mốc thời gian.
    monkeypatch.setattr(MT, "_thieu_cong_cu_avr", lambda *a, **k: "", raising=False)
    kq = MT.nap_qua_avrdude(hx, cong="/dev/null", ma_chip="m328p", baud=57600)
    assert not kq.dat, "nạp tệp hex cũ hơn elf mà vẫn báo đạt"
    assert "CŨ HƠN" in kq.vi_sao_khong_dat, (
        f"lý do phải nói rõ hex cũ hơn elf, nhận: {kq.vi_sao_khong_dat!r}")
    # Phải nêu CẢ HAI mốc, vì người đọc cần thấy lệch bao nhiêu.
    assert "mach.elf" in kq.vi_sao_khong_dat and "mach.hex" in kq.vi_sao_khong_dat
    assert any("thay vì" in c for c in kq.canh_bao), (
        "phải chỉ ra cách chữa — nạp .elf, hoặc sinh lại hex")


def test_hex_moi_hon_elf_thi_KHONG_bi_chan(tmp_path, monkeypatch):
    """Nửa đối: hex mới hơn elf là chuyện bình thường, chốt phải im.

    Không có ca này thì bản vá có thể chặn mọi lượt nạp `.hex`, và người ta sẽ tắt chốt.
    """
    hx = _dung_cap(tmp_path, hex_cu_hon=False)
    goi = {}

    def gia_chay(lenh, **k):
        goi["lenh"] = lenh
        raise RuntimeError("tới được chỗ gọi avrdude — chốt đã cho qua")

    monkeypatch.setattr(MT.subprocess, "run", gia_chay)
    try:
        kq = MT.nap_qua_avrdude(hx, cong="/dev/null", ma_chip="m328p", baud=57600)
    except RuntimeError as e:
        assert "chốt đã cho qua" in str(e)
        return
    # Nếu không tới được avrdude thì ít nhất lý do KHÔNG được là chuyện mốc thời gian.
    assert "CŨ HƠN" not in (kq.vi_sao_khong_dat or ""), (
        f"hex mới hơn elf mà vẫn bị chặn vì mốc: {kq.vi_sao_khong_dat!r}")


def test_khong_co_elf_ben_canh_thi_khong_chan(tmp_path, monkeypatch):
    """Chỉ có `.hex` thì không có gì để so — đừng chặn.

    Người dùng có thể nạp một tệp hex lấy từ nơi khác, và chốt này không được cản việc đó.
    """
    hx = tmp_path / "ngoai.hex"
    hx.write_text(":00000001FF\n", "utf-8")

    def gia_chay(lenh, **k):
        raise RuntimeError("tới được chỗ gọi avrdude")

    monkeypatch.setattr(MT.subprocess, "run", gia_chay)
    try:
        kq = MT.nap_qua_avrdude(hx, cong="/dev/null", ma_chip="m328p", baud=57600)
    except RuntimeError:
        return
    assert "CŨ HƠN" not in (kq.vi_sao_khong_dat or "")


def test_chenh_duoi_mot_giay_thi_khong_chan(tmp_path, monkeypatch):
    """Dựng xong rồi sinh hex ngay thì hai mốc gần nhau — không được coi là cũ.

    Ngưỡng 1 giây có trong mã vì hệ tệp làm tròn mốc, và một chốt kêu vì nửa giây sẽ kêu suốt.
    """
    import os
    elf = tmp_path / "mach.elf"; hx = tmp_path / "mach.hex"
    elf.write_bytes(b"\x7fELF"); hx.write_text(":00000001FF\n", "utf-8")
    moc = time.time()
    os.utime(hx, (moc - 0.4, moc - 0.4))
    os.utime(elf, (moc, moc))

    def gia_chay(lenh, **k):
        raise RuntimeError("tới được chỗ gọi avrdude")

    monkeypatch.setattr(MT.subprocess, "run", gia_chay)
    try:
        kq = MT.nap_qua_avrdude(hx, cong="/dev/null", ma_chip="m328p", baud=57600)
    except RuntimeError:
        return
    assert "CŨ HƠN" not in (kq.vi_sao_khong_dat or ""), "chênh 0,4 giây mà đã chặn"


def test_chot_nam_trong_ma_va_noi_ro_vi_sao():
    """Chốt phải nói thẳng *đối chiếu không bắt được chuyện này*, không thì lần sau lại tin nó."""
    nguon = (REPO / "src/eide/build/mach_that.py").read_text("utf-8")
    i = nguon.find("CŨ HƠN")
    assert i > 0, "mất chốt DEV-337"
    doan = nguon[max(0, i - 2200):i + 400]
    assert "DEV-337" in doan, "chốt phải có mã tra được"
    assert "thứ tôi ghi" in doan and "thứ tôi dựng" in doan, (
        "chú thích phải nói rõ đối chiếu khẳng định điều gì và KHÔNG khẳng định điều gì")
    assert "tệp thứ ba" in doan, (
        "phải nói vì sao phép so mốc dựng/mốc nạp không bắt được: có một tệp thứ ba ở giữa")
