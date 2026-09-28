# -*- coding: utf-8 -*-
"""G7 — mạch thật: dò bo, nạp, đọc log. Ca TC029, TC032, TC033, TC034.

Điều bộ này canh, một câu: **không bao giờ báo nạp thành công giả.** Với bo ST-LINK kiểu ổ
đĩa, `shutil.copy` trả về 0 kể cả khi bộ nạp sau đó từ chối tệp và ghi `FAIL.TXT` — nên một
phép đo dừng ở chỗ sao tệp sẽ báo "đã nạp" cho những lần nạp đã thất bại.

Không test nào ở đây cần bo thật: `/Volumes` và `/dev` được trỏ sang thư mục tạm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eide.build import mach_that as MT

BIN = b"\x00\x00\x05\x20\x09\x00\x00\x08" + b"\xaa" * 64


def _o_gia(tmp_path: Path, ten: str = "DIS_F469NI", *, details: str = "Version: 0221\n"):
    """Một ổ đĩa giả trông như bộ nạp ST-LINK kiểu mass-storage."""
    d = tmp_path / "Volumes" / ten
    d.mkdir(parents=True)
    (d / "DETAILS.TXT").write_text(details, "utf-8")
    (d / "MBED.HTM").write_text("<html></html>", "utf-8")
    return d


# ===================================================================== dò bo
def test_nhan_ra_bo_va_suy_chip_tu_nhan_o_dia(tmp_path, monkeypatch):
    o = _o_gia(tmp_path)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "không có st-info", {}))
    monkeypatch.setattr(MT, "_cong_noi_tiep", lambda: [])
    d = MT.do_bo()
    assert d["so_thiet_bi"] == 1 and d["nap_duoc"]
    t = d["thiet_bi"][0]
    assert t["bo_doan"] == "ST Discovery F469NI"
    assert t["chip_doan"] == "STM32F469NI"
    assert t["nap_duoc_bang"] == "sao_tep"
    assert "DETAILS.TXT" in t["biet_bang_cach"]
    assert str(o) == t["duong_dan"]


def test_chip_doan_khac_chip_doc_duoc(tmp_path, monkeypatch):
    """Nhãn ổ đĩa là bằng chứng về BO; ID chip là bằng chứng về silicon. Không gộp hai thứ."""
    _o_gia(tmp_path)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "chưa có st-info", {}))
    monkeypatch.setattr(MT, "_cong_noi_tiep", lambda: [])
    d = MT.do_bo()
    assert d["chip_doc_duoc"] == ""
    assert d["thiet_bi"][0]["chip_doan"] == "STM32F469NI"
    assert d["thiet_bi"][0]["chip_doc_duoc"] == ""
    assert "st-info" in d["vi_sao_chua_doc_duoc_chip"]


def test_o_dia_thuong_khong_bi_coi_la_bo(tmp_path, monkeypatch):
    (tmp_path / "Volumes" / "Macintosh HD").mkdir(parents=True)
    (tmp_path / "Volumes" / "USB cua toi").mkdir(parents=True)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    monkeypatch.setattr(MT, "_cong_noi_tiep", lambda: [])
    d = MT.do_bo()
    assert d["so_thiet_bi"] == 0 and not d["nap_duoc"]


def test_khong_co_bo_thi_tra_danh_sach_kiem_tra_du_bon_muc(tmp_path, monkeypatch):
    """TC032 đòi đúng bốn thứ: nguồn, cáp, driver, chân BOOT/NRST."""
    (tmp_path / "Volumes").mkdir()
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    monkeypatch.setattr(MT, "_cong_noi_tiep", lambda: [])
    d = MT.do_bo()
    ds = " ".join(d["danh_sach_kiem_tra"]).lower()
    assert len(d["danh_sach_kiem_tra"]) == 4
    for tu in ("nguồn", "cáp", "driver", "boot0"):
        assert tu in ds, tu


def test_tai_nghe_bluetooth_khong_bi_coi_la_bo(tmp_path, monkeypatch):
    """Đọc log từ một cái tai nghe thì im lặng, và im lặng sẽ bị đọc thành firmware sai.

    Kiểm ĐÚNG hàm thật `_cong_noi_tiep` bằng cách trỏ `THU_MUC_DEV` sang thư mục giả — bản
    đầu của ca này chép lại phép phân loại vào chính test, nên nó xanh kể cả khi hàm thật sai.
    """
    dev = tmp_path / "dev"
    dev.mkdir()
    for t in ("cu.Bluetooth-Incoming-Port", "cu.JBLTune520BT", "cu.debug-console",
              "cu.usbmodem1103", "cu.wchusbserial110"):
        (dev / t).write_text("", "utf-8")
    monkeypatch.setattr(MT, "THU_MUC_DEV", dev)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    d = MT.do_bo()
    theo_ten = {t["ten"]: t["co_the_la_bo"] for t in d["thiet_bi"]}
    assert theo_ten["cu.usbmodem1103"] is True
    assert theo_ten["cu.wchusbserial110"] is True
    assert theo_ten["cu.JBLTune520BT"] is False
    assert theo_ten["cu.Bluetooth-Incoming-Port"] is False
    assert theo_ten["cu.debug-console"] is False
    assert d["so_co_the_la_bo"] == 2
    # Nói rõ VÌ SAO loại — người dùng thấy cổng đó trong Terminal và sẽ hỏi tại sao thiếu.
    ly_do = {t["ten"]: t["biet_bang_cach"] for t in d["thiet_bi"]}
    assert "Bluetooth" in ly_do["cu.JBLTune520BT"]
    assert "macOS" in ly_do["cu.debug-console"]


def test_chi_co_cong_khong_phai_bo_thi_van_ra_danh_sach_kiem_tra(tmp_path, monkeypatch):
    """4 thiết bị mà không cái nào là bo vẫn là "không thấy bo" — TC032 phải hiện ra."""
    dev = tmp_path / "dev"
    dev.mkdir()
    for t in ("cu.Bluetooth-Incoming-Port", "cu.JBLTune520BT", "cu.debug-console"):
        (dev / t).write_text("", "utf-8")
    monkeypatch.setattr(MT, "THU_MUC_DEV", dev)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    d = MT.do_bo()
    assert d["so_thiet_bi"] == 3 and d["so_co_the_la_bo"] == 0
    assert len(d["danh_sach_kiem_tra"]) == 4


# ===================================================================== nạp qua ổ đĩa
def test_FAIL_TXT_thi_KHONG_phai_nap_xong(tmp_path):
    """Bộ nạp nhận cả tệp rồi mới từ chối, và nó nói lý do bằng FAIL.TXT."""
    o = _o_gia(tmp_path)
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)

    that = MT.shutil.copy

    def copy_roi_that_bai(src, dst):
        that(src, dst)
        (o / "FAIL.TXT").write_text("The transfer timed out.", "utf-8")
        return dst

    MT.shutil.copy = copy_roi_that_bai
    try:
        kq = MT.nap_qua_o_dia(b, o, cho_giay=0.6)
    finally:
        MT.shutil.copy = that
    assert not kq.dat
    assert "TỪ CHỐI" in kq.vi_sao_khong_dat
    assert "timed out" in kq.vi_sao_khong_dat


def test_FAIL_TXT_cu_bi_don_truoc_khi_nap(tmp_path):
    """Không dọn thì lần này đọc lại kết luận của lần trước — sai theo cả hai hướng."""
    o = _o_gia(tmp_path)
    (o / "FAIL.TXT").write_text("lỗi của lần trước", "utf-8")
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_o_dia(b, o, cho_giay=0.6)
    assert kq.dat, kq.vi_sao_khong_dat
    assert not (o / "FAIL.TXT").exists()


def test_nap_xong_nhung_o_khong_gan_lai_thi_noi_la_chua_co_bang_chung(tmp_path):
    o = _o_gia(tmp_path)
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_o_dia(b, o, cho_giay=0.6)
    assert kq.dat
    assert any("chưa có bằng chứng bo đã ghi xong" in c for c in kq.canh_bao)
    assert any("KHÔNG verify" in c for c in kq.canh_bao)
    assert kq.da_verify is False
    assert kq.so_byte == len(BIN)
    assert (o / "mach.bin").read_bytes() == BIN


def test_tep_rong_thi_khong_nap(tmp_path):
    o = _o_gia(tmp_path)
    b = tmp_path / "mach.bin"
    b.write_bytes(b"")
    kq = MT.nap_qua_o_dia(b, o)
    assert not kq.dat and "0 byte" in kq.vi_sao_khong_dat
    assert not (o / "mach.bin").exists()


def test_rut_cap_giua_luc_nap_thi_noi_trang_thai_khong_chac(tmp_path):
    """TC033 — nạp thất bại giữa chừng: phải nói Flash có thể không nhất quán."""
    o = _o_gia(tmp_path)
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)

    that = MT.shutil.copy

    def rut_cap(src, dst):
        raise OSError("Input/output error")

    MT.shutil.copy = rut_cap
    try:
        kq = MT.nap_qua_o_dia(b, o, cho_giay=0.3)
    finally:
        MT.shutil.copy = that
    assert not kq.dat
    assert "KHÔNG chắc chắn" in kq.vi_sao_khong_dat
    assert "RESET" in kq.vi_sao_khong_dat


def test_o_dia_bien_mat_truoc_khi_nap(tmp_path):
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_o_dia(b, tmp_path / "Volumes" / "KHONG_CO")
    assert not kq.dat and "không còn được gắn" in kq.vi_sao_khong_dat


def test_hash_ghi_lai_dung_tep_da_nap(tmp_path):
    import hashlib

    o = _o_gia(tmp_path)
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_o_dia(b, o, cho_giay=0.4)
    assert kq.hash == hashlib.sha256(BIN).hexdigest()


# ===================================================================== st-flash
def test_st_flash_thieu_cong_cu_thi_noi_ro(tmp_path, monkeypatch):
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_st_flash(b)
    assert not kq.dat and "st-flash" in kq.vi_sao_khong_dat


def test_st_flash_ma_0_ma_khong_verify_thi_khong_tinh_la_xong(tmp_path, monkeypatch):
    """Mã thoát 0 không phải bằng chứng; dòng "verified" mới là."""
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(
        MT.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "ghi xong", ""))
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_st_flash(b)
    assert not kq.dat and "KHÔNG in dòng verify" in kq.vi_sao_khong_dat


def test_st_flash_verify_khop_thi_dat(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(
        MT.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(
            a[0], 0, "Flash written and verified! jolly good!", ""))
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_st_flash(b)
    assert kq.dat and kq.da_verify and kq.cach == "st-flash"


def test_st_flash_ma_khac_0_thi_huong_dan_khoi_phuc(tmp_path, monkeypatch):
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(
        MT.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "Failed to write"))
    b = tmp_path / "mach.bin"
    b.write_bytes(BIN)
    kq = MT.nap_qua_st_flash(b)
    assert not kq.dat
    assert "connect-under-reset" in kq.vi_sao_khong_dat
    assert "bootloader ROM" in kq.vi_sao_khong_dat


# ===================================================================== đọc log
def test_cong_khong_ton_tai_thi_bao_loi(tmp_path):
    d = MT.doc_log(str(tmp_path / "cu.khong-co"), giay=0.2)
    assert "loi" in d and "Không có cổng" in d["loi"]


def test_im_lang_khong_phai_bang_chung_firmware_sai(tmp_path):
    """Đây là câu quan trọng nhất của công cụ log."""
    p = tmp_path / "cu.gia"
    p.write_bytes(b"")
    d = MT.doc_log(str(p), giay=0.3)
    assert d["im_lang"] is True and d["so_byte"] == 0
    canh = " ".join(d["canh_bao"])
    assert "KHÔNG chứng minh firmware sai" in canh
    assert "baud" in canh


def test_doc_duoc_chu_thi_tra_nguyen_van(tmp_path):
    p = tmp_path / "cu.gia"
    p.write_bytes("EIDE: LED xanh nhấp nháy, chu kỳ 500 ms\n".encode())
    d = MT.doc_log(str(p), giay=0.4)
    assert d["im_lang"] is False
    assert "LED xanh nhấp nháy" in d["chu"]
    assert d["so_byte"] > 0


# ===================================================================== so mã chip
@pytest.mark.parametrize("a,b,mong", [
    ("STM32F469NIH6", "STM32F469NI", True),      # hộ chiếu dài hơn nhãn ổ
    ("STM32F469NI", "STM32F469NIH6", True),
    ("STM32F469NIH6", "F46x/F47x", True),        # st-info khai theo họ
    ("STM32F469NIH6", "STM32F407VG", False),     # khác con chip
    ("STM32F103C8", "STM32F401RE", False),       # đúng ca TC034
    ("STM32F469NI", "", False),
    ("", "STM32F469NI", False),
])
def test_so_ma_chip_long_dung_muc(a, b, mong):
    from eide.tools.mach_that import _cung_chip

    assert _cung_chip(a, b) is mong


# ===================================================================== qua công cụ target.*
def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


_EX = {"summary": "nạp", "why": "chạy thử trên bo", "sources": [], "diff_prev": "—",
       "next": "—", "confidence": "BAC"}


def _ghim_chip(agent, chip: str):
    from eide.knowledge.passport import doan_isa

    isa, _ = doan_isa(chip)
    agent.store.apply(artefact_id=f"passport:{chip}", type="passport", op="create",
                      author="test", canonical={"chip": chip, "isa": isa},
                      explain=_EX)


def _bo_gia(monkeypatch, tmp_path, *, chip_doan="STM32F469NI", chip_doc=""):
    # Ổ giả không bao giờ tự gắn lại, nên không rút ngắn thì mỗi ca nạp chờ đủ 25 giây.
    monkeypatch.setattr(MT, "CHO_GAN_LAI_GIAY", 0.5)
    o = _o_gia(tmp_path, f"DIS_{chip_doan.removeprefix('STM32')}" if chip_doan else "USB")
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "THU_MUC_DEV", tmp_path / "dev-rong")
    (tmp_path / "dev-rong").mkdir(exist_ok=True)
    monkeypatch.setattr(MT, "doc_id_chip",
                        lambda: (chip_doc, "" if chip_doc else "chưa có st-info", {}))
    return o


def test_detect_noi_ro_chua_doc_duoc_id_chip(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    _bo_gia(monkeypatch, tmp_path)
    _ghim_chip(agent, "STM32F469NIH6")
    r = agent.registry.run("target.detect", {}, _ctx(agent))
    assert r.ok
    assert r.data["chip_doc_duoc"] == ""
    assert r.data["khop_chip"] == "khop"          # khớp theo NHÃN Ổ
    assert "CHƯA đọc được ID chip" in r.data["note_vi"]
    assert "bằng chứng về BO, không phải về silicon" in r.data["note_vi"]


def test_TC034_sai_chip_thi_dung_truoc_khi_nap(make_agent, tmp_path, monkeypatch):
    """Firmware cho F103 mà bo là F469 → dừng, không nạp."""
    agent = make_agent([])
    _bo_gia(monkeypatch, tmp_path, chip_doan="STM32F469NI")
    _ghim_chip(agent, "STM32F103C8")
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4012"
    assert "STM32F103C8" in r.error.message_vi and "F469" in r.error.message_vi
    assert r.error.details["chip_theo_nhan_o"] == "STM32F469NI"
    # Và KHÔNG được sao tệp nào vào ổ — dừng nghĩa là chưa chạm vào bo.
    assert not (tmp_path / "Volumes" / "DIS_F469NI" / "mach.bin").exists()


def test_khong_doc_duoc_id_chip_thi_doi_xac_nhan_tuong_minh(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    o = _bo_gia(monkeypatch, tmp_path)
    _ghim_chip(agent, "STM32F469NIH6")
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4013"
    assert "dong_y_khong_doi_chieu_chip=true" in r.error.hint_for_agent
    assert "tool.install" in r.error.alternatives
    assert not (o / "mach.bin").exists()          # chưa nạp gì


def test_dong_y_roi_thi_nap_va_khai_ro_chua_verify(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    o = _bo_gia(monkeypatch, tmp_path)
    _ghim_chip(agent, "STM32F469NIH6")
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run(
        "target.flash",
        {"explain": _EX, "dong_y_khong_doi_chieu_chip": True}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert (o / "mach.bin").read_bytes() == BIN
    assert r.data["da_verify"] is False
    assert "KHÔNG hoàn tác được" in r.data["note_vi"]
    assert "KHÔNG verify được" in r.data["note_vi"]
    # Changeset phải ghi là không hoàn tác được (§G7).
    a = agent.store.get("target:flash")
    assert a["canonical"]["reversible"] is False
    assert a["canonical"]["vi_sao_khong_hoan_tac"]


def test_khong_co_bo_thi_bao_loi_kem_danh_sach_kiem_tra(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    (tmp_path / "Volumes").mkdir()
    (tmp_path / "dev-rong").mkdir()
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "THU_MUC_DEV", tmp_path / "dev-rong")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4011"
    assert len(r.error.details["danh_sach_kiem_tra"]) == 4
    assert "ĐỪNG báo nạp thành công" in r.error.hint_for_agent


def test_chua_bien_dich_thi_noi_thieu_bin(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    _bo_gia(monkeypatch, tmp_path)
    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and "build.compile" in r.error.alternatives


def test_target_flash_la_R4_va_cong_G_FLASH(make_agent):
    agent = make_agent([])
    s = agent.registry._tools["target.flash"]
    assert s.risk == "R4" and s.gate == "G-FLASH"


def test_log_nhieu_cong_thi_khong_doan(make_agent, tmp_path, monkeypatch):
    agent = make_agent([])
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "cu.usbmodem1").write_text("", "utf-8")
    (dev / "cu.usbmodem2").write_text("", "utf-8")
    monkeypatch.setattr(MT, "THU_MUC_DEV", dev)
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    (tmp_path / "Volumes").mkdir(exist_ok=True)
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x", {}))
    r = agent.registry.run("target.log", {"giay": 0.2}, _ctx(agent))
    assert not r.ok and "không đoán dùng cổng nào" in r.error.message_vi
    assert "tai nghe Bluetooth" in r.error.hint_for_agent


def test_log_qua_lau_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("target.log", {"giay": 600}, _ctx(agent))
    assert not r.ok and r.error.code == "E5001"


# ============================== so chip: ba giá trị, không phải hai
@pytest.mark.parametrize("a,b,mong", [
    ("STM32F469NI", "STM32F46x_F47x", "khop"),     # st-info khai theo họ
    ("STM32F469NIH6", "STM32F469NI", "khop"),      # hộ chiếu dài hơn nhãn ổ
    ("STM32F469NI", "chipid 0x434", "chua_so_duoc"),   # ca thật đã chặn nhầm
    ("STM32F469NI", "", "chua_so_duoc"),
    ("", "STM32F469NI", "chua_so_duoc"),
    ("STM32F103C8", "STM32F401RE", "lech"),        # TC034
    ("STM32F469NI", "STM32F407VG", "lech"),
])
def test_so_chip_ba_gia_tri(a, b, mong):
    from eide.tools.mach_that import so_chip

    assert so_chip(a, b) == mong


def test_chua_so_duoc_thi_HOI_chu_khong_chan(make_agent, tmp_path, monkeypatch):
    """Ca thật: st-info trả `chipid 0x434`, phép so cũ không hiểu, và việc nạp bị CHẶN.

    Chặn vì không so được là một báo động giả, và báo động giả dạy người dùng bấm qua cảnh
    báo. "Không chứng minh được là giống" phải dẫn tới HỎI, không dẫn tới DỪNG.
    """
    agent = make_agent([])
    _bo_gia(monkeypatch, tmp_path, chip_doan="STM32F469NI", chip_doc="chipid 0x434")
    _ghim_chip(agent, "STM32F469NIH6")
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4013", "phải là XIN XÁC NHẬN, không phải DỪNG"
    assert "dong_y_khong_doi_chieu_chip=true" in r.error.hint_for_agent


def test_doc_duoc_dev_type_thi_nap_thang_khong_can_xac_nhan(make_agent, tmp_path, monkeypatch):
    """Đọc được `dev-type: STM32F46x_F47x` và nó khớp hộ chiếu → đã đối chiếu, nạp được."""
    agent = make_agent([])
    o = _bo_gia(monkeypatch, tmp_path, chip_doan="STM32F469NI",
                chip_doc="STM32F46x_F47x")
    _ghim_chip(agent, "STM32F469NIH6")
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    r = agent.registry.run("target.flash", {"explain": _EX, "cach": "sao_tep"}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert r.data["chip_da_doi_chieu"] == "STM32F46x_F47x"
    assert "Chip đã đối chiếu" in r.data["note_vi"]
    assert (o / "mach.bin").read_bytes() == BIN


def test_st_info_doc_duoc_bo_nho_tu_chip(monkeypatch):
    """Flash/SRAM đọc từ chính con chip chắc hơn mọi con số trích từ tài liệu bằng regex."""
    import subprocess

    ra = ("Found 1 stlink programmers\n  version:    V2J35S26\n"
          "  flash:      2097152 (pagesize: 16384)\n  sram:       262144\n"
          "  chipid:     0x434\n  dev-type:   STM32F46x_F47x\n")
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-info")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, ra, ""))
    ten, vi_sao, bo_nho = MT.doc_id_chip()
    assert ten == "STM32F46x_F47x" and not vi_sao
    assert bo_nho == {"flash": 2097152, "sram": 262144}


def test_chi_co_chipid_thi_noi_la_chua_suy_ra_duoc_ten(monkeypatch):
    import subprocess

    ra = "Found 1 stlink programmers\n  chipid:     0x434\n"
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-info")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 0, ra, ""))
    ten, vi_sao, _ = MT.doc_id_chip()
    assert ten == "" and "chưa suy ra được tên chip" in vi_sao


# ============================== target.verify — hỏi silicon, không tin lời trình nạp
def test_verify_khop_thi_noi_ro_no_KHONG_chung_minh_chuong_trinh_chay_dung(
        make_agent, tmp_path, monkeypatch):
    import subprocess

    agent = make_agent([])
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)

    def gia_read(cmd, *a, **k):
        pathlib_Path = type(b)
        pathlib_Path(cmd[2]).write_bytes(BIN)          # st-flash read <ra> <addr> <len>
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(MT.subprocess, "run", gia_read)
    r = agent.registry.run("target.verify", {}, _ctx(agent))
    assert r.ok and r.data["dat"] and r.data["so_byte_khac"] == 0
    assert "GIỐNG HỆT" in r.data["note_vi"]
    # Câu quan trọng nhất: khớp byte KHÔNG có nghĩa là chương trình chạy đúng.
    assert "KHÔNG chứng minh chương trình đang chạy đúng" in r.data["note_vi"]


def test_verify_lech_thi_bao_chip_dang_chay_ban_khac(make_agent, tmp_path, monkeypatch):
    import subprocess

    agent = make_agent([])
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)

    def gia_read(cmd, *a, **k):
        type(b)(cmd[2]).write_bytes(BIN[:-4] + b"\xff\xff\xff\xff")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(MT.subprocess, "run", gia_read)
    r = agent.registry.run("target.verify", {}, _ctx(agent))
    assert not r.ok and r.error.code == "E4016"
    assert "KHÁC tệp đã nạp" in r.error.message_vi
    assert "TRƯỚC khi giải thích bất cứ hành vi nào" in r.error.hint_for_agent


def test_thieu_st_flash_thi_KHONG_DO_DUOC_chu_khong_phai_khong_khop(make_agent, monkeypatch):
    """Cùng bài học với `chua_do_duoc`: hai trạng thái khác nhau, hai hành động khác nhau."""
    agent = make_agent([])
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    r = agent.registry.run("target.verify", {}, _ctx(agent))
    assert not r.ok and r.error.code == "E4015"
    assert "KHÔNG đo được khác với KHÔNG khớp" in r.error.hint_for_agent
    assert r.error.details["do_duoc"] is False


# ============================== soi_chip — đo chip ĐANG CHẠY, không đọc mã rồi đoán
# Đo được trên bo STM32F469 ngày 28/09/2026: firmware dịch sạch, nạp đúng từng byte,
# `target.verify` khớp hoàn toàn, **mà màn hình đen**. Mọi phép đo tĩnh đều xanh. Chỉ chip
# đang chạy nói được sự thật, nên bộ này canh đúng cái đường ống dẫn sự thật đó.

_RA_HARDFAULT = """Info : clock speed 2000 kHz
Info : stm32f4x.cpu: hardware has 6 breakpoints, 4 watchpoints
[stm32f4x.cpu] halted due to debug-request, current mode: Handler HardFault
xPSR: 0x21000003 pc: 0x08000db0 msp: 0x2002ffd0
0xe000ed28: 00020000 40000000
0xe000ed34: e000edf8 e000edf8
"""


def _openocd_gia(monkeypatch, ra: str, *, giu: list | None = None):
    import subprocess

    def _run(cl, **k):
        if giu is not None:
            giu.append(list(cl))
        return subprocess.CompletedProcess(cl, 0, ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)


def test_soi_chip_tach_tung_c_chu_khong_gop_mot_chuoi(monkeypatch):
    """Gộp cả chuỗi lệnh vào MỘT `-c` thì openocd chạy đúng nhưng không in kết quả `mdw`.

    Đo được: gộp → `o_nho` rỗng; tách → đọc ra `0xe000ed28: 00020000`. Một phép đo im lặng
    trông y hệt một phép đo không có gì để nói, nên lỗi này tự nó không kêu — phải có test.
    """
    giu: list[list[str]] = []
    _openocd_gia(monkeypatch, _RA_HARDFAULT, giu=giu)
    MT.soi_chip([0x20000000])
    cl = giu[0]
    assert "; " not in " ".join(cl), f"lệnh bị gộp vào một -c: {cl}"
    lenh = [cl[i + 1] for i, x in enumerate(cl) if x == "-c"]
    assert lenh[:2] == ["init", "halt"] and lenh[-1] == "exit"
    assert "mdw 0x20000000 4" in lenh          # địa chỉ người gọi xin
    assert "mdw 0xe000ed28 2" in lenh          # CFSR+HFSR: đọc LUÔN, không đợi ai nghĩ ra


def test_soi_chip_doc_duoc_cfsr_thi_dich_ra_loi_nguoi_doc_duoc(monkeypatch):
    _openocd_gia(monkeypatch, _RA_HARDFAULT)
    d = MT.soi_chip()
    assert d["dat"] and d["che_do"] == "Handler HardFault" and d["pc"] == "0x08000db0"
    lp = d["loi_phan_cung"]
    assert lp["cfsr"] == "0x00020000" and lp["hfsr"] == "0x40000000"
    assert any("INVSTATE" in x for x in lp["nghia"])
    assert any("FORCED" in x for x in lp["nghia"])
    # MMARVALID/BFARVALID đều tắt → địa chỉ trong MMFAR/BFAR là rác. Nói "không hợp lệ"
    # thay vì in ra một con số trông như sở cứ.
    assert lp["mmfar"] == "(không hợp lệ)" and lp["bfar"] == "(không hợp lệ)"


def test_soi_chip_khong_dung_duoc_chip_thi_KHONG_DAT_chu_khong_bao_chay_dung(monkeypatch):
    _openocd_gia(monkeypatch, "Error: init mode failed (unable to connect to the target)\n")
    d = MT.soi_chip()
    assert not d["dat"] and "không dừng được chip" in d["vi_sao_khong_dat"]
    assert d["che_do"] == ""


def test_soi_chip_thieu_openocd_thi_noi_KHAC_voi_chip_chay_dung(monkeypatch):
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    d = MT.soi_chip()
    assert not d["dat"] and "Không soi được KHÁC" in d["vi_sao_khong_dat"]


def test_soi_chip_khong_doc_duoc_thanh_ghi_thi_loi_phan_cung_RONG(monkeypatch):
    """Không đọc được CFSR ≠ CFSR bằng 0. Trả rỗng, đừng dựng lên một chẩn đoán "sạch"."""
    ra = ("[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
          "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2002ffd0\n")
    _openocd_gia(monkeypatch, ra)
    d = MT.soi_chip()
    assert d["dat"] and d["che_do"] == "Thread" and d["loi_phan_cung"] == {}


# ============================== địa chỉ → tên hàm, và phanh "tên này có tin được không"
def test_giai_ma_dia_chi_tra_ten_ham_va_dong_nguon(tmp_path, monkeypatch):
    """Một địa chỉ không tên thì chỉ là một con số, và nó bắt tác tử đọc cả cây mã để đoán.

    Đo được trên bo STM32F469: nhận `pc 0x08000db0`, tác tử gọi `fs.read` 28 lần rồi hết hạn
    mức lời gọi của lượt và dừng giữa việc. `addr2line` trả lời trong 40 ms.
    """
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF" * 40)
    ra = ("OTM8009A_Init_Ext\n/du-an/firmware/otm8009a.c:424\n"
          "??\n??:0\n")
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/addr2line")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda cl, **k: subprocess.CompletedProcess(cl, 0, ra, ""))
    d = MT.giai_ma_dia_chi(elf, [0x08000DB0, 0xE000ED28])
    assert d["dat"]
    a = d["ky_hieu"]["0x08000db0"]
    assert a["ham"] == "OTM8009A_Init_Ext" and a["nguon"] == "otm8009a.c:424"
    b = d["ky_hieu"]["0xe000ed28"]
    assert b["ham"] == "" and b["nguon"] == "" and "không có ký hiệu" in b["ghi_chu"]
    # Tên đọc từ ELF chứ không từ chip — hàm phải NÓI RA điều đó, không để tầng trên tự đoán.
    assert d["can_doi_chieu"] and "target.verify" in d["canh_bao"]


def test_giai_ma_dia_chi_khong_bo_mat_dia_chi_0(tmp_path, monkeypatch):
    """Địa chỉ 0 là chỗ đặt bảng vector — một trong những chỗ đáng soi nhất khi HardFault.

    `if d` lọc nó đi mất, và câu trả lời thiếu một địa chỉ trông y hệt câu trả lời đủ.
    """
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    giu: list[list[str]] = []

    def _run(cl, **k):
        giu.append(list(cl))
        return subprocess.CompletedProcess(cl, 0, "_vector\n??:0\n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/addr2line")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.giai_ma_dia_chi(elf, [0])
    assert "0x00000000" in giu[0] and "0x00000000" in d["ky_hieu"]


def test_giai_ma_dia_chi_nguon_kieu_hoi_hoi_dau_cham_hoi(tmp_path, monkeypatch):
    """addr2line nói "không biết" bằng `??`, `??:0` VÀ `??:?`. Bỏ sót dạng thứ ba thì nó lọt
    ra ngoài như một đường dẫn thật."""
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/addr2line")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda cl, **k: subprocess.CompletedProcess(cl, 0, "_sdata\n??:?\n", ""))
    d = MT.giai_ma_dia_chi(elf, [0x20000000])
    assert d["ky_hieu"]["0x20000000"]["nguon"] == ""


def test_giai_ma_dia_chi_thieu_elf_thi_noi_chua_dich(tmp_path):
    d = MT.giai_ma_dia_chi(tmp_path / "khong-co.elf", [0x08000000])
    assert not d["dat"] and "biên dịch trước" in d["vi_sao_khong_dat"]


def test_giai_ma_dia_chi_thieu_addr2line_thi_KHONG_GIAI_DUOC_chu_khong_phai_khong_co_ham(
        tmp_path, monkeypatch):
    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    d = MT.giai_ma_dia_chi(elf, [0x08000000])
    assert not d["dat"] and "KHÁC với địa chỉ không có hàm nào" in d["vi_sao_khong_dat"]


def test_khop_tai_dia_chi_bat_duoc_chip_dang_chay_ban_khac(tmp_path, monkeypatch):
    """Đo được trên bo STM32F469: PC giải mã thành `OTM8009A_Init_Ext`, mà 32 byte tại đúng
    địa chỉ đó trên chip KHÁC tệp vừa dịch — chip đang chạy bản cũ, và cái tên kia sẽ dẫn tác
    tử đi sửa một hàm không liên quan. Đây là phanh cho `giai_ma_dia_chi`."""
    import subprocess

    b = tmp_path / "mach.bin"
    b.write_bytes(bytes(range(256)) * 8)

    def _run(cl, **k):
        Path(cl[2]).write_bytes(b"\xff" * 64)      # chip chứa thứ khác
        return subprocess.CompletedProcess(cl, 0, "", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.khop_tai_dia_chi(b, 0x08000100)
    assert d["do_duoc"] and not d["khop"]
    assert "KHÁC tệp vừa dịch" in d["vi_sao"]


def test_khop_tai_dia_chi_khop_thi_ten_ham_tin_duoc(tmp_path, monkeypatch):
    import subprocess

    noi_dung = bytes(range(256)) * 8
    b = tmp_path / "mach.bin"
    b.write_bytes(noi_dung)

    def _run(cl, **k):
        lech = int(cl[3], 16) - 0x08000000
        Path(cl[2]).write_bytes(noi_dung[lech:lech + int(cl[4])])
        return subprocess.CompletedProcess(cl, 0, "", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    assert MT.khop_tai_dia_chi(b, 0x08000100)["khop"] is True


def test_khop_tai_dia_chi_ngoai_anh_nap_thi_noi_ro_chu_khong_bao_LECH(tmp_path, monkeypatch):
    """PC nằm ngoài ảnh nạp (RAM, bootloader) không phải bằng chứng chip chạy bản khác."""
    b = tmp_path / "mach.bin"
    b.write_bytes(b"\x00" * 64)
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-flash")
    d = MT.khop_tai_dia_chi(b, 0x20000100)
    assert not d["do_duoc"] and not d["khop"] and "nằm ngoài ảnh nạp" in d["vi_sao"]


def test_khop_tai_dia_chi_thieu_st_flash_thi_chua_do_duoc(tmp_path, monkeypatch):
    b = tmp_path / "mach.bin"
    b.write_bytes(b"\x00" * 64)
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    d = MT.khop_tai_dia_chi(b, 0x08000000)
    assert not d["do_duoc"] and "chưa có `st-flash`" in d["vi_sao"]


def test_target_debug_NOI_RA_thanh_ghi_loi_va_ten_ham_trong_note_vi(
        make_agent, tmp_path, monkeypatch):
    """Manh mối nằm trong payload mà lời văn không nhắc tới thì coi như không có.

    Đo được trên bo STM32F469: `loi_phan_cung` đã có CFSR=0x00020000 → INVSTATE, nhưng
    `note_vi` chỉ nói về `SysTick_Handler` — tức chỉ sang lỗi của LẦN TRƯỚC — và tác tử đi
    theo lời văn, không đi theo JSON.
    """
    import subprocess

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"ELF" * 40)
    (goc / ".eide" / "build" / "mach.bin").write_bytes(bytes(range(256)) * 16)

    def _which(x):
        return {"openocd": "/fake/openocd", "arm-none-eabi-addr2line": "/fake/a2l",
                "st-flash": "/fake/st-flash"}.get(x)

    def _run(cl, **k):
        if "openocd" in cl[0]:
            return subprocess.CompletedProcess(cl, 0, _RA_HARDFAULT, "")
        if "a2l" in cl[0]:
            return subprocess.CompletedProcess(
                cl, 0, "OTM8009A_Init_Ext\n/du-an/firmware/otm8009a.c:424\n", "")
        Path(cl[2]).write_bytes(b"\x7f" * 64)      # chip chứa bản KHÁC
        return subprocess.CompletedProcess(cl, 0, "", "")

    monkeypatch.setattr(MT.shutil, "which", _which)
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.debug", {}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    n = r.data["note_vi"]
    assert "CFSR = 0x00020000" in n and "INVSTATE" in n and "FORCED" in n
    assert "OTM8009A_Init_Ext" in n and "otm8009a.c:424" in n
    # Và phanh: chip đang chạy bản khác → KHÔNG được để tác tử đi sửa hàm vừa nêu tên.
    assert r.data["ky_hieu_tin_duoc"] is False
    assert "KHÁC" in n and "Đừng đi sửa hàm vừa nêu tên" in n


def test_target_debug_chua_doi_chieu_duoc_thi_khong_noi_la_tin_duoc(
        make_agent, tmp_path, monkeypatch):
    """Thiếu `st-flash` → chưa biết chip chạy bản nào. Ba trạng thái, không gộp thành hai."""
    import subprocess

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"ELF" * 40)

    def _which(x):
        return {"openocd": "/fake/openocd", "arm-none-eabi-addr2line": "/fake/a2l"}.get(x)

    def _run(cl, **k):
        if "openocd" in cl[0]:
            return subprocess.CompletedProcess(cl, 0, _RA_HARDFAULT, "")
        return subprocess.CompletedProcess(cl, 0, "OTM8009A_Init_Ext\n/x/otm8009a.c:424\n", "")

    monkeypatch.setattr(MT.shutil, "which", _which)
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.debug", {}, _ctx(agent))
    assert r.ok and r.data["ky_hieu_tin_duoc"] is None
    assert "chỉ đúng NẾU chip đang chạy đúng bản vừa dịch" in r.data["note_vi"]


# ============================== khung ngoại lệ: lệnh NÀO đã fault, không phải handler nào
def test_giai_khung_ngat_chi_ra_lenh_gay_fault_va_cho_goi_no():
    """`pc = Default_Handler` là câu trả lời vòng tròn — nó đúng với MỌI fault.

    Đo được trên bo STM32F469: khung ngoại lệ nói `pc_fault = 0x00000000` và
    `lr = 0x080006F7` → `OTM8009A_ReadID_Ext` tại otm8009a.c:472, tức một lần gọi con trỏ hàm
    NULL, chỉ đúng một dòng. Không có khung này thì tác tử chỉ nhận được tên của cái handler
    bắt tất cả.
    """
    d = MT.giai_khung_ngat(["00000000", "00000001", "20000000", "00000000",
                            "ffffffff", "080006f7", "00000000", "00000000"])
    assert d["doc_duoc"] and d["pc"] == "0x00000000" and d["lr"] == "0x080006F7"
    assert d["pc_fault"] == 0 and d["lr_fault"] == 0x080006F7
    # Cờ T = 0 → lúc fault CPU không ở trạng thái Thumb: bằng chứng ĐỘC LẬP cho bit INVSTATE.
    assert d["thumb"] is False and "địa chỉ CHẴN" in d["ghi_chu"]


def test_giai_khung_ngat_co_thumb_thi_khong_doan_bua():
    d = MT.giai_khung_ngat(["0"] * 7 + ["01000000"])
    assert d["thumb"] is True and "ghi_chu" not in d


@pytest.mark.parametrize("tu", [[], ["0"] * 7, ["xyz"] * 8])
def test_giai_khung_ngat_doc_thieu_thi_NOI_THIEU_chu_khong_dung_khung_rac(tu):
    d = MT.giai_khung_ngat(tu)
    assert not d["doc_duoc"] and d["vi_sao"]


def test_soi_chip_dang_o_handler_thi_doc_luon_khung_ngat(monkeypatch):
    """Địa chỉ MSP chỉ biết được SAU khi dừng chip, nên cần lần gọi openocd thứ hai."""
    import subprocess

    lan: list[list[str]] = []

    def _run(cl, **k):
        lan.append(list(cl))
        if len(lan) == 1:
            return subprocess.CompletedProcess(cl, 0, _RA_HARDFAULT, "")
        # openocd in mỗi 4 từ một dòng — xin 8 từ thì về HAI dòng.
        ra = ("0x2002ffd0: 00000000 00000001 20000000 00000000 \n"
              "0x2002ffe0: ffffffff 080006f7 00000000 00000000 \n")
        return subprocess.CompletedProcess(cl, 0, ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.soi_chip()
    assert len(lan) == 2, "phải gọi openocd lần thứ hai để đọc đỉnh ngăn xếp"
    k = d["khung_ngat"]
    assert k["doc_duoc"], k
    assert k["pc_fault"] == 0 and k["lr_fault"] == 0x080006F7


def test_doc_o_nho_ghep_cac_dong_4_tu_lai(monkeypatch):
    """openocd in 4 từ một dòng. Không ghép thì xin 8 từ luôn chỉ nhận 4, và khung ngoại lệ
    sẽ mãi mãi báo "chỉ đọc được 4/8" — một phép đo thiếu trông y hệt một phép đo bất lực."""
    import subprocess

    ra = ("0x20000000: 11111111 22222222 33333333 44444444 \n"
          "0x20000010: 55555555 66666666 77777777 88888888 \n")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda cl, **k: subprocess.CompletedProcess(cl, 0, ra, ""))
    d = MT._doc_o_nho("/fake/openocd", [(0x20000000, 8)])
    assert len(d["0x20000000"]) == 8


def test_soi_chip_o_Thread_thi_KHONG_doc_khung_ngat_ma_doc_DAU_VET(monkeypatch):
    """Không ở trong ngắt thì không có khung ngoại lệ nào để đọc — đừng dựng một cái ra.

    Nhưng vẫn còn một câu PC không trả lời được: **ai gọi tới đây**. Ở chế độ Thread thì câu
    đó do dấu vết ngăn xếp trả lời.
    """
    import subprocess

    lan: list[int] = []

    def _run(cl, **k):
        lan.append(1)
        if len(lan) == 1:
            return subprocess.CompletedProcess(
                cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                       "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2002ffd0\n", "")
        return subprocess.CompletedProcess(
            cl, 0, "0x2002ffd0: 00000000 20002a40 080006db 00000001 \n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.soi_chip()
    assert "khung_ngat" not in d
    assert d["dau_vet"]["dia_chi"] == [0x080006DA]


def test_soi_chip_tat_doc_ngan_xep_thi_chi_dung_chip_MOT_lan(monkeypatch):
    """Mỗi lần đọc ngăn xếp là một lần DỪNG thêm con chip đang chạy. Lấy tám mẫu mà dừng mười
    sáu lần thì phép đo bắt đầu can thiệp vào chính thứ nó đang đo."""
    import subprocess

    lan: list[int] = []

    def _run(cl, **k):
        lan.append(1)
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2002ffd0\n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.soi_chip(doc_ngan_xep=False)
    assert len(lan) == 1 and "dau_vet" not in d


def test_target_debug_NOI_lenh_gay_fault_TRUOC_ten_handler(make_agent, monkeypatch):
    """Thứ tự trong lời văn là một quyết định thiết kế: chỗ đáng sửa phải nói trước.

    Đo được trên bo STM32F469: PC = `Default_Handler` (đúng mà vô dụng), khung ngoại lệ =
    gọi con trỏ hàm NULL từ otm8009a.c:472. Nếu `note_vi` mở đầu bằng `Default_Handler` thì
    tác tử đi đọc startup.c — nó đã làm đúng thế, 28 lần `fs.read`.
    """
    import subprocess

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"ELF" * 40)

    def _which(x):
        return {"openocd": "/fake/openocd", "arm-none-eabi-addr2line": "/fake/a2l"}.get(x)

    lan: list[str] = []

    def _run(cl, **k):
        if "a2l" in cl[0]:
            # Ba địa chỉ: PC, pc_fault (0x0), lr_fault. Trả theo đúng thứ tự xin.
            return subprocess.CompletedProcess(
                cl, 0, "Default_Handler\n/x/startup.c:272\n"
                       "??\n??:0\n"
                       "OTM8009A_ReadID_Ext\n/x/otm8009a.c:472\n", "")
        lan.append("oo")
        if len(lan) == 1:
            return subprocess.CompletedProcess(cl, 0, _RA_HARDFAULT, "")
        return subprocess.CompletedProcess(
            cl, 0, "0x2002ffd0: 00000000 00000001 20000000 00000000 \n"
                   "0x2002ffe0: ffffffff 080006f7 00000000 00000000 \n", "")

    monkeypatch.setattr(MT.shutil, "which", _which)
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.debug", {}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    n = r.data["note_vi"]
    assert "OTM8009A_ReadID_Ext" in n and "otm8009a.c:472" in n
    assert "địa chỉ CHẴN" in n            # cờ T = 0 → nhảy tới địa chỉ chẵn
    assert n.index("Khung ngoại lệ") < n.index("Địa chỉ → mã nguồn")


# ============================== target.screen — XEM chip đã vẽ gì, không chỉ đoán
def _openocd_dump(monkeypatch, noi_dung: bytes, *, ltdc: dict | None = None):
    """openocd giả: `mdw` cho thanh ghi LTDC, `dump_image` cho khung ảnh."""
    import subprocess

    tt = ltdc or {0x18: 0x00002221, 0x84: 1, 0x94: 0, 0xAC: 0xC0000000,
                  0xB0: 0x0C800C83, 0xB4: 0x000001E0, 0x88: 0x03430024, 0x8C: 0x01EF0010}

    def _run(cl, **k):
        lenh = [cl[i + 1] for i, x in enumerate(cl) if x == "-c"]
        ra = ""
        for l in lenh:
            if l.startswith("dump_image"):
                _, tep, dc, n = l.split()
                Path(tep).write_bytes(noi_dung[:int(n)])
            elif l.startswith("mdw"):
                d = int(l.split()[1], 16)
                ra += f"0x{d:08x}: {tt.get(d - 0x40016800, 0):08x} \n"
        return subprocess.CompletedProcess(cl, 0, ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: f"/fake/{x}")
    monkeypatch.setattr(MT.subprocess, "run", _run)


def test_doc_cau_hinh_ltdc_suy_kich_thuoc_tu_THANH_GHI_khong_bat_go_tay(monkeypatch):
    """Gõ tay ba con số này thì sai một cái là ảnh đọc ra lệch hàng và trông y như “chương
    trình vẽ sai” — một phép đo tự sinh ra bằng chứng giả."""
    _openocd_dump(monkeypatch, b"")
    c = MT.doc_cau_hinh_ltdc()
    assert c["dat"] and c["ltdc_bat"] and c["lop1_bat"]
    assert c["dia_chi_khung"] == "0xC0000000" and c["dinh_dang"] == "ARGB8888"
    assert (c["rong"], c["cao"]) == (800, 480)      # 0x0C80 / 4 byte, 0x1E0 dòng


def test_target_screen_nhieu_mau_thi_noi_CHUONG_TRINH_DA_VE(make_agent, monkeypatch):
    """Đo được trên bo STM32F469: người dùng thấy màn hình đen, mà khung ảnh có 200 màu —
    #FFFFFF 82,8 %, #000000 12,2 %, **#DE2019 2,1 %** (đúng đỏ logo PTIT).

    Hai nguyên nhân "vẽ sai" và "panel không hiện" ở hai đầu khác nhau của hệ thống, cách sửa
    không liên quan gì nhau, và nhìn vào một màn hình đen thì không phân biệt được. Đây là
    phép đo tách chúng ra.
    """
    agent = make_agent([])
    khung = (bytes([0x19, 0x20, 0xDE, 0xFF]) * 4 + bytes([0xFF]) * 16) * 4
    _openocd_dump(monkeypatch, khung)
    r = agent.registry.run("target.screen",
                           {"dia_chi": 0xC0000000, "rong": 4, "cao": 8,
                            "dinh_dang": "ARGB8888"}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert not r.data["chi_mot_mau"]
    assert "#DE2019" in " ".join(m["mau"] for m in r.data["mau_hay_gap"])
    n = r.data["note_vi"]
    assert "chương trình ĐÃ vẽ" in n and "LTDC → DSI → panel" in n
    assert Path(r.data["tep"]).exists()


def test_target_screen_mot_mau_thi_noi_LOI_O_PHAN_VE(make_agent, monkeypatch):
    """Một khung ảnh chỉ có một màu là câu trả lời ngược lại, và nó phải nói ngược lại."""
    agent = make_agent([])
    _openocd_dump(monkeypatch, b"\x00\x00\x00\xff" * 32)
    r = agent.registry.run("target.screen",
                           {"dia_chi": 0xC0000000, "rong": 4, "cao": 8,
                            "dinh_dang": "ARGB8888"}, _ctx(agent))
    assert r.ok and r.data["chi_mot_mau"]
    assert "Lỗi nằm ở phần VẼ" in r.data["note_vi"]


def test_target_screen_tu_lay_thong_so_tu_LTDC_khi_khong_truyen_gi(make_agent, monkeypatch):
    agent = make_agent([])
    _openocd_dump(monkeypatch, b"\x10\x20\x30\xff" * (800 * 480))
    r = agent.registry.run("target.screen", {}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert (r.data["rong"], r.data["cao"]) == (800, 480)
    assert r.data["dinh_dang"] == "ARGB8888"


def test_target_screen_LTDC_chua_bat_thi_DO_LA_MOT_CAU_TRA_LOI(make_agent, monkeypatch):
    """LTDC chưa cấu hình → chưa có khung ảnh nào. Đó không phải thất bại của phép đo, mà là
    kết quả của nó: chương trình chưa chạy tới chỗ bật màn hình."""
    agent = make_agent([])
    _openocd_dump(monkeypatch, b"", ltdc={0x18: 0, 0x84: 0, 0x94: 0, 0xAC: 0,
                                          0xB0: 0, 0xB4: 0, 0x88: 0, 0x8C: 0})
    r = agent.registry.run("target.screen", {}, _ctx(agent))
    assert not r.ok and r.error.code == "E4019"
    assert "chưa chạy tới chỗ bật màn hình" in r.error.hint_for_agent


def test_doc_khung_anh_qua_lon_thi_tu_choi_truoc_khi_doc(tmp_path, monkeypatch):
    """Từ chối TRƯỚC khi đọc, không phải sau — đọc 20 MB qua SWD rồi mới báo lỗi thì người
    dùng đã bỏ đi từ lâu."""
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    d = MT.doc_khung_anh(0xC0000000, 4000, 4000, "ARGB8888", tmp_path / "a.png")
    assert not d["dat"] and "vượt trần" in d["vi_sao_khong_dat"]


def test_doc_khung_anh_doc_thieu_byte_thi_KHONG_ghi_anh_cut(tmp_path, monkeypatch):
    """Đọc thiếu mà vẫn ghi ảnh thì ra một khung lệch hàng — trông y hệt chương trình vẽ sai."""
    _openocd_dump(monkeypatch, b"\x00" * 16)          # xin nhiều hơn số có
    d = MT.doc_khung_anh(0xC0000000, 10, 10, "ARGB8888", tmp_path / "a.png")
    assert not d["dat"] and "/400 byte" in d["vi_sao_khong_dat"]
    assert not (tmp_path / "a.png").exists()


def test_doc_khung_anh_dinh_dang_la_thi_noi_biet_nhung_gi(tmp_path):
    d = MT.doc_khung_anh(0xC0000000, 8, 8, "YUV420", tmp_path / "a.png")
    assert not d["dat"] and "ARGB8888" in d["vi_sao_khong_dat"]


# ============================== đi dọc chuỗi hiển thị: đứt ở MẮT NÀO
def _openocd_reg(monkeypatch, gia_tri: dict[int, int], *, cpsr_dung_yen: bool = False):
    """openocd giả. `CPSR` đổi giá trị mỗi lần đọc, vì trên bo thật bộ quét đang chạy —
    trừ khi ca kiểm muốn dựng cảnh LTDC bật mà đứng yên."""
    import subprocess

    dem = {"cpsr": 0}
    CPSR = MT.LTDC_GOC + MT.LTDC_CPSR

    def _run(cl, **k):
        ra = ""
        for i, x in enumerate(cl):
            if x == "-c" and cl[i + 1].startswith("mdw"):
                d = int(cl[i + 1].split()[1], 16)
                if d == CPSR and not cpsr_dung_yen:
                    dem["cpsr"] += 0x111
                    v = 0x01000000 + dem["cpsr"]
                else:
                    v = gia_tri.get(d, 0)
                ra += f"0x{d:08x}: {v:08x} \n"
        return subprocess.CompletedProcess(cl, 0, ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)


# `0x40017000` là WCFGR (cấu hình), `0x40017004` mới là WCR (điều khiển). Trên bo thật hai
# thanh ghi cạnh nhau này mang hai giá trị khác nhau — 0x0A và 0x08 — và chính cái đó làm
# lộ ra lỗi: đọc nhầm sang WCFGR thì `0x0A` giải nghĩa thành "SHTDN = 1, màn đang tắt".
_DUONG_HONG = {0x40016818: 0xC0002221, 0x40016884: 1,     # LTDC bật, lớp 1 bật
               0x40016C04: 1,                             # host DSI bật
               0x40017000: 0x0000000A,                    # WCFGR — KHÔNG phải WCR
               0x40017004: 0x0000000A,                    # WCR: SHTDN=1, DSIEN=1
               0x40016C34: 0,                             # MCR: CMDM=0 → chế độ video
               0x40016CA0: 0b110,                         # PCTLR: DEN=1, CKE=1
               0x40016CBC: 0, 0x40016CC0: 0,              # ISR0/ISR1: không lỗi
               0x4001700C: 1 << 8,                        # WISR: PLL đã khoá
               0x40021C14: 1 << 7, 0x40021C10: 1 << 7}    # XRES cao → panel đã ra khỏi reset


def test_dia_chi_va_bit_lay_tu_HEADER_cua_ST_khong_tu_tri_nho():
    """Hai lỗi của chính phép đo, cả hai đều **tự chế ra bằng chứng**, bắt được ngày 28/09/2026:

    * `GPIOH_ODR` viết theo trí nhớ là `0x40021C1C` — đó là `LCKR` (offset 0x1C); `ODR` ở
      offset 0x14. Phép đo đọc nhầm thanh ghi rồi báo *"panel đang bị giữ trong reset"*.
    * `DSIEN` để ở bit 2 — đúng là bit 3 (bit 2 là `LTDCEN`). Phép đo báo *"bọc DSI chưa
      bật"* trong khi nó đang bật.

    Một bằng chứng sai tệ hơn hẳn không có bằng chứng, vì người ta hành động theo nó: cả tôi
    lẫn tác tử đều đã đi sửa hai chỗ không hỏng. Bộ kiểm này neo từng con số vào `stm32f469xx.h`.
    """
    assert MT.GPIOH_BASE == 0x40020000 + 0x1C00        # AHB1PERIPH_BASE + 0x1C00
    assert (MT.GPIO_MODER, MT.GPIO_IDR, MT.GPIO_ODR) == (0x00, 0x10, 0x14)
    assert MT.GPIOH_ODR == 0x40021C14                  # KHÔNG phải 0x40021C1C (= LCKR)
    # stm32f469xx.h: COLM_Pos 0, SHTDN_Pos 1, LTDCEN_Pos 2, DSIEN_Pos 3
    assert (MT._WCR_COLM, MT._WCR_SHTDN, MT._WCR_LTDCEN, MT._WCR_DSIEN) == (0, 1, 2, 3)
    assert MT.DSI_GOC == 0x40016C00 and MT.LTDC_GOC == 0x40016800
    # Lỗi thứ BA trong cùng một hàm, và lần này do tác tử tìm ra chứ không phải tôi:
    #   __IO uint32_t WCFGR;  /*!< DSI Wrapper Configuration Register,  Address offset: 0x400 */
    #   __IO uint32_t WCR;    /*!< DSI Wrapper Control Register,        Address offset: 0x404 */
    # Bản trước để WCR = 0x400 — đó là WCFGR. Phép đo đọc thanh ghi CẤU HÌNH rồi giải nghĩa
    # nó như thanh ghi ĐIỀU KHIỂN.
    assert (MT.DSI_WCFGR, MT.DSI_WCR) == (0x400, 0x404)


def test_doc_duong_hien_thi_doc_WCR_chu_khong_phai_WCFGR_canh_no(monkeypatch):
    """Hai thanh ghi cạnh nhau, tên gần giống nhau, và trên bo thật mang hai giá trị khác
    nhau. Đọc nhầm cái nào cũng ra một con số trông hoàn toàn hợp lý."""
    _openocd_reg(monkeypatch, {**_DUONG_HONG,
                               0x40017000: 0x0000000A,     # WCFGR: nếu đọc nhầm → "SHTDN=1"
                               0x40017004: 0x00000008})    # WCR thật: SHTDN=0, DSIEN=1
    d = MT.doc_duong_hien_thi()
    assert d["thong_suot"], d["dut_o"]
    assert "0x40017004" in next(m["so_do"] for m in d["mat_xich"] if "SHTDN" in m["ten"])
    assert d["wcfgr"] == "0x0000000A"


def test_doc_duong_hien_thi_chi_dung_mat_xich_bi_dut(monkeypatch):
    """Sáu mắt xích hỏng theo sáu cách khác nhau và cho ra CÙNG MỘT màn hình đen.

    Số đo thật trên bo STM32F469 khi khung ảnh đã vẽ đúng mà màn vẫn đen: `DSI_WCR = 0x0A` →
    **SHTDN = 1** (bọc DSI đang ở trạng thái tắt hiển thị) trong khi DSIEN = 1 và XRES đã cao.
    Đúng MỘT mắt đứt, và nó biến "lỗi ở đâu đó trong đường ra màn hình" thành một dòng.
    """
    _openocd_reg(monkeypatch, _DUONG_HONG)
    d = MT.doc_duong_hien_thi()
    assert d["dat"] and not d["thong_suot"]
    assert d["dut_o"] == ["Hiển thị không bị tắt (SHTDN)"]
    # Mọi mắt kia vẫn thông — phép đo phải nói ra điều đó, không gộp cả chuỗi thành "hỏng".
    assert all(m["thong"] for m in d["mat_xich"]
               if m["ten"] != "Hiển thị không bị tắt (SHTDN)")
    assert all(m["cach_sua"] for m in d["mat_xich"] if m["thong"] is False)


def test_doc_duong_hien_thi_doc_ca_ODR_lan_IDR_cua_chan_XRES(monkeypatch):
    """ODR nói chương trình MUỐN gì, IDR nói chân đang THỰC SỰ ở đâu. Với chân open-drain kéo
    tải ngoài, hai cái lệch nhau được — và chính cái lệch đó là thông tin."""
    _openocd_reg(monkeypatch, {**_DUONG_HONG, 0x40021C14: 1 << 7, 0x40021C10: 0})
    d = MT.doc_duong_hien_thi()
    m = next(x for x in d["mat_xich"] if "XRES" in x["ten"])
    assert m["thong"] is False, "IDR nói chân vẫn thấp → panel vẫn trong reset"
    assert "0x40021C14" in m["so_do"] and "0x40021C10" in m["so_do"]


def test_doc_duong_hien_thi_thong_suot_thi_NOI_RA_phan_con_lai_o_dau(monkeypatch):
    """Một kết luận toàn dấu ✓ đứng trước một màn hình đen là kiểu báo cáo dạy người ta thôi
    tin báo cáo. Thông suốt thì phải nói thẳng phần chưa đo được nằm ở đâu."""
    _openocd_reg(monkeypatch, {**_DUONG_HONG, 0x40017004: 0x00000008})   # SHTDN=0, DSIEN=1
    d = MT.doc_duong_hien_thi()
    assert d["thong_suot"] and d["dut_o"] == []
    assert "OTM8009A" in d["ket_luan"] and "đèn nền" in d["ket_luan"]
    assert "NT35510" in d["ket_luan"], "bo này có hai biến thể panel — phải nhắc"


def test_LTDC_bat_ma_DUNG_YEN_thi_bi_bat(monkeypatch):
    """“Đã bật” và “đang chạy” là hai chuyện. CPSR là vị trí điểm ảnh đang quét: đọc hai lần
    ra cùng một giá trị nghĩa là bộ quét đứng yên, dù `LTDC_GCR` bit 0 vẫn bằng 1.

    Đo trên bo thật: CPSR đổi mỗi lần đọc (0x024B012B → 0x0015008F), nên phép đo này phân
    biệt được hai trạng thái — và đó là lý do nó tồn tại.
    """
    _openocd_reg(monkeypatch, {**_DUONG_HONG, 0x40017004: 0x00000008,
                               MT.LTDC_GOC + MT.LTDC_CPSR: 0x00010001},
                 cpsr_dung_yen=True)
    d = MT.doc_duong_hien_thi()
    assert "LTDC ĐANG QUÉT (không chỉ “đã bật”)" in d["dut_o"]
    # Mắt "LTDC bật" vẫn phải xanh: hai mắt hỏi hai câu khác nhau.
    assert next(m["thong"] for m in d["mat_xich"] if m["ten"] == "LTDC bật") is True


@pytest.mark.parametrize("dia_chi,gia_tri,mat", [
    (0x4001700C, 0, "PLL của DSI đã khoá"),
    (0x40016CA0, 0b010, "PHY của DSI bật (DEN + CKE)"),          # DEN=1 mà CKE=0
    (0x40016C34, 1, "Chế độ VIDEO (không phải chế độ lệnh)"),
    (0x40016CBC, 1 << 4, "Không có lỗi trên đường DSI"),
    (0x40016CC0, 1 << 2, "Không có lỗi trên đường DSI"),
])
def test_tung_mat_cua_tang_lien_ket_DSI_deu_bat_duoc_rieng(monkeypatch, dia_chi, gia_tri, mat):
    """Năm mắt của tầng liên kết DSI hỏng theo năm cách khác nhau và cho ra cùng một màn hình
    đen. Mỗi mắt phải tự bắt được phần của nó."""
    _openocd_reg(monkeypatch, {**_DUONG_HONG, 0x40017004: 0x00000008, dia_chi: gia_tri})
    d = MT.doc_duong_hien_thi()
    assert d["dut_o"] == [mat], d["dut_o"]
    assert "ket_luan" not in d


def test_doc_duong_hien_thi_chan_xres_la_cua_RIENG_TUNG_BO(monkeypatch):
    """Đọc nhầm chân thì dòng về panel là vô nghĩa — nên nó là tham số, và kết quả luôn khai
    mình đang đọc chân nào."""
    _openocd_reg(monkeypatch, {**_DUONG_HONG, 0x40020814: 1 << 3, 0x40020810: 1 << 3})
    d = MT.doc_duong_hien_thi(chan_xres=3, odr_xres=0x40020814)
    assert d["chan_xres"] == "PH3" and "RIÊNG từng bo" in d["ghi_chu_chan"]
    assert "Panel đã ra khỏi reset (XRES = PH3)" not in d["dut_o"]


def test_doc_duong_hien_thi_khong_doc_duoc_thi_KHONG_bao_dut(monkeypatch):
    """`None` = chưa đọc được. Báo đứt vì không đọc được là một báo động giả, và báo động giả
    dạy người ta bỏ qua cảnh báo."""
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda cl, **k: subprocess.CompletedProcess(
                            cl, 0, "0x40016818: c0002221 \n", ""))
    d = MT.doc_duong_hien_thi()
    assert d["dat"] and d["dut_o"] == []
    assert any(m["thong"] is None for m in d["mat_xich"])


def test_target_screen_noi_thang_DUT_O_DAU(make_agent, monkeypatch):
    import subprocess

    agent = make_agent([])
    khung = (bytes([0x19, 0x20, 0xDE, 0xFF]) * 4 + bytes([0xFF]) * 16) * 4
    tt = {0x40016818: 0x00002221, 0x40016884: 1, 0x40016894: 0, 0x400168AC: 0xC0000000,
          0x400168B0: 0x0C800C83, 0x400168B4: 0x000001E0, 0x40016888: 0x03430024,
          0x4001688C: 0x01EF0010, **_DUONG_HONG, 0x40017004: 0x0000000A}

    def _run(cl, **k):
        ra = ""
        for i, x in enumerate(cl):
            if x != "-c":
                continue
            l = cl[i + 1]
            if l.startswith("dump_image"):
                _, tep, dc, n = l.split()
                Path(tep).write_bytes(khung[:int(n)])
            elif l.startswith("mdw"):
                d = int(l.split()[1], 16)
                ra += f"0x{d:08x}: {tt.get(d, 0):08x} \n"
        return subprocess.CompletedProcess(cl, 0, ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: f"/fake/{x}")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.screen", {"rong": 4, "cao": 8}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    n = r.data["note_vi"]
    assert "chương trình ĐÃ vẽ" in n and "ĐỨT Ở:" in n
    assert "Hiển thị không bị tắt (SHTDN)" in n and "DSI->WCR" in n
    assert r.data["duong"]["dut_o"]


# ============================== kẹt, quanh quẩn, hay đang reset lại — ba thứ khác hẳn nhau
def test_lay_mau_pc_dem_so_dia_chi_KHONG_du_phai_do_KHOANG_TRAI(monkeypatch):
    """Đo được trên bo STM32F469: sáu mẫu rơi vào **năm** địa chỉ — nghe như "đang chạy bình
    thường" — nhưng cả năm nằm trong **42 byte** của nhau, tức một vòng lặp chặt bên trong
    đúng một hàm (`HAL_InitTick`). Thứ phân biệt được là khoảng trải, không phải số lượng.
    """
    import subprocess

    dia = ["0x0800199c", "0x080019be", "0x080019c2", "0x080019c4", "0x080019c6",
           "0x080019be", "0x080019c2", "0x0800199c"]
    n = iter(dia)

    def _run(cl, **k):
        p = next(n, dia[-1])
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   f"xPSR: 0x01000000 pc: {p} msp: 0x2004fef8\n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.lay_mau_pc(8)
    assert len(dia) == 8, "lấy mẫu KHÔNG được tốn thêm lần dừng chip nào cho ngăn xếp"
    assert d["dat"] and d["so_dia_chi_khac_nhau"] == 5
    assert d["trai_byte"] == 42
    assert "QUANH QUẨN" in d["ket_luan"] and "reset lại" in d["ket_luan"]


def test_lay_mau_pc_chay_that_thi_noi_la_chay_that(monkeypatch):
    import subprocess

    dia = ["0x08000100", "0x08004500", "0x08009000", "0x0800c300",
           "0x08001200", "0x08007700"]
    n = iter(dia)
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", lambda cl, **k: subprocess.CompletedProcess(
        cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
               f"xPSR: 0x01000000 pc: {next(n, dia[-1])} msp: 0x2004fef8\n", ""))
    d = MT.lay_mau_pc(6)
    assert d["trai_byte"] > d["nguong_trai_byte"] and "không kẹt" in d["ket_luan"]


def test_lay_mau_pc_ket_o_dung_mot_lenh(monkeypatch):
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", lambda cl, **k: subprocess.CompletedProcess(
        cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
               "xPSR: 0x01000000 pc: 0x08000db0 msp: 0x2004fef8\n", ""))
    d = MT.lay_mau_pc(5)
    assert d["so_dia_chi_khac_nhau"] == 1 and "ĐỨNG YÊN" in d["ket_luan"]


@pytest.mark.parametrize("csr,mong", [
    (0x0E000000, "PORRST"),          # đo được trên bo: bật nguồn + NRST + BOR
    (1 << 29, "IWDGRST"),            # chó canh cắn — lý do rất khác, cách sửa rất khác
    (1 << 28, "SFTRST"),
    (0, None),
])
def test_doc_nguyen_nhan_reset_hoi_chinh_con_chip(monkeypatch, csr, mong):
    """Một chương trình đang reset đi reset lại và một chương trình kẹt một chỗ nhìn qua cửa
    sổ gỡ lỗi thì giống hệt nhau. `RCC_CSR` trả lời thẳng bằng một bit."""
    import subprocess

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", lambda cl, **k: subprocess.CompletedProcess(
        cl, 0, f"0x{MT.RCC_CSR:08x}: {csr:08x} \n", ""))
    d = MT.doc_nguyen_nhan_reset()
    assert d["dat"] and d["csr"] == f"0x{csr:08X}"
    if mong:
        assert any(mong in x for x in d["nguyen_nhan"])
    else:
        assert d["nguyen_nhan"] == []
    # Cờ DÍNH: thấy PINRST không có nghĩa là VỪA bị reset bởi chân NRST.
    assert "DÍNH" in d["ghi_chu"]


def test_target_debug_lay_mau_thi_noi_ca_ket_luan_va_ly_do_reset(make_agent, monkeypatch):
    import subprocess

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"ELF" * 40)
    dia = ["0x0800199c", "0x080019be", "0x080019c2", "0x080019c4"]
    n = iter(dia * 3)

    def _which(x):
        return {"openocd": "/fake/openocd", "arm-none-eabi-addr2line": "/fake/a2l"}.get(x)

    def _run(cl, **k):
        if "a2l" in cl[0]:
            so = sum(1 for i, x in enumerate(cl) if x == "-e") and len(cl) - 5
            return subprocess.CompletedProcess(
                cl, 0, "HAL_InitTick\n/x/stm32f4xx_hal.c:264\n" * max(1, so), "")
        lenh = [cl[i + 1] for i, x in enumerate(cl) if x == "-c"]
        if any(l.startswith("mdw") and hex(MT.RCC_CSR)[2:] in l for l in lenh):
            return subprocess.CompletedProcess(cl, 0, f"0x{MT.RCC_CSR:08x}: 0e000000 \n", "")
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   f"xPSR: 0x01000000 pc: {next(n, dia[-1])} msp: 0x2004fef8\n", "")

    monkeypatch.setattr(MT.shutil, "which", _which)
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.debug", {"lay_mau": 6}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert r.data["nhieu_mau"]["dat"] and r.data["nguyen_nhan_reset"]["dat"]
    n_vi = r.data["note_vi"]
    assert "QUANH QUẨN" in n_vi and "RCC_CSR = 0x0E000000" in n_vi and "PORRST" in n_vi


def test_target_debug_khong_lay_mau_thi_khong_ton_them_lan_dung_chip(make_agent, monkeypatch):
    """Lấy mẫu phải là việc tác tử XIN, không phải việc luôn xảy ra: mỗi mẫu là một lần dừng
    con chip đang chạy, và dừng chip là can thiệp vào chính thứ đang đo."""
    import subprocess

    agent = make_agent([])
    dem: list[int] = []

    def _run(cl, **k):
        dem.append(1)
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2004fef8\n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd" if x == "openocd" else None)
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run("target.debug", {}, _ctx(agent))
    assert r.ok and r.data["nhieu_mau"] == {} and r.data["nguyen_nhan_reset"] == {}
    # Hai lần: một lần dừng+đọc thanh ghi, một lần đọc ngăn xếp. KHÔNG có lần nào cho lấy mẫu.
    assert len(dem) == 2


# ============================== hai vòng while(1) giống hệt nhau nếu chỉ nhìn PC
def test_dau_vet_ngan_xep_phan_biet_duoc_hai_vong_while(monkeypatch):
    """Đo được trên bo STM32F469: chip dừng trong `HAL_Delay`. Nhưng `main.c` có **hai** vòng
    `while(1)` gọi `HAL_Delay` — vòng chính ở cuối, và vòng bắt lỗi ngay sau
    `if (BSP_LCD_Init() != LCD_OK)`. Nghĩa của chúng ngược hẳn nhau: "chạy xong xuôi" và
    "màn hình không khởi tạo được". Chỉ nhìn PC thì chúng giống hệt nhau.

    LR không trả lời được: `HAL_Delay` gọi tiếp `HAL_GetTick`, nên LR đã bị ghi đè bằng một
    địa chỉ bên trong chính `HAL_Delay`.
    """
    tu = ["00000000", "20002a40", "080006db", "00000001", "ffffffff", "080001a1"]
    d = MT.doc_dau_vet_ngan_xep(0x2004FEF8, tu)
    assert d["doc_duoc"] and d["la_phong_doan"]
    assert d["dia_chi"] == [0x080006DA, 0x080001A0]     # bit Thumb đã bị bỏ
    assert d["khung"][0]["o_lech"] == 8
    assert d["khung"][0]["tu_dia_chi"] == "0x2004FF00"


def test_dau_vet_ngan_xep_bo_qua_gia_tri_khong_phai_dia_chi_tro_ve():
    """Lọc bằng hai điều kiện độc lập: nằm trong vùng Flash, và có bit Thumb. Không có chúng
    thì mọi biến cục bộ đều thành một "khung" và dấu vết chỉ còn là nhiễu."""
    tu = ["20000010",          # RAM — không phải mã
          "08000100",          # trong Flash nhưng bit 0 = 0 → không phải địa chỉ trở về
          "0a000001",          # ngoài vùng Flash
          "deadbeef"]
    assert MT.doc_dau_vet_ngan_xep(0x20000000, tu)["doc_duoc"] is False


def test_dau_vet_ngan_xep_gop_dia_chi_lap_lien_nhau():
    tu = ["080006db", "080006db", "080006db", "080001a1"]
    d = MT.doc_dau_vet_ngan_xep(0x20000000, tu)
    assert d["dia_chi"] == [0x080006DA, 0x080001A0]


def test_dau_vet_ngan_xep_NOI_RO_no_la_phong_doan():
    """Nó không đọc bảng unwind — nó nhặt những từ trông giống địa chỉ trở về. Vài cái là rác
    còn sót từ các lần gọi trước. Một dấu vết có lẫn rác vẫn hơn không có gì, MIỄN LÀ không ai
    trình bày nó như sự thật."""
    d = MT.doc_dau_vet_ngan_xep(0x20000000, ["080006db"])
    assert d["la_phong_doan"] and "PHỎNG ĐOÁN" in d["ghi_chu"]
    assert "lẫn địa chỉ còn sót" in d["ghi_chu"]


def test_dau_vet_ngan_xep_khong_thay_gi_thi_noi_ra(monkeypatch):
    d = MT.doc_dau_vet_ngan_xep(0x20000000, [])
    assert not d["doc_duoc"] and "chưa đọc được từ nào" in d["vi_sao"]
    d = MT.doc_dau_vet_ngan_xep(0x20000000, ["00000000"] * 8)
    assert not d["doc_duoc"] and "không từ nào" in d["vi_sao"]


# ============================== "ai đặt ra giá trị ấy" — N6 nằm trong firmware
def test_ky_hieu_theo_ten_tra_dia_chi_bien_toan_cuc(tmp_path, monkeypatch):
    """Đọc một biến toàn cục trên chip đang chạy mà không phải tra địa chỉ bằng tay."""
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    ra = ("200000b0 00000001 B Lcd_Driver_Type\n"
          "08000f94 00000004 T OTM8009A_ReadID\n"
          "0800158c 00000006 T BSP_LCD_Init\n"
          "08000810 00000744 T OTM8009A_Init_Ext\n")
    monkeypatch.setattr(MT.shutil, "which",
                        lambda x: "/fake/nm" if x.endswith("nm") else None)
    monkeypatch.setattr(MT.subprocess, "run",
                        lambda cl, **k: subprocess.CompletedProcess(cl, 0, ra, ""))
    d = MT.ky_hieu_theo_ten(elf, ["Lcd_Driver_Type", "OTM8009A_Init_Ext", "khong_co"])
    assert d["dat"]
    assert d["ky_hieu"]["Lcd_Driver_Type"]["dia_chi"] == 0x200000B0
    assert d["ky_hieu"]["Lcd_Driver_Type"]["la_ham"] is False
    assert d["ky_hieu"]["OTM8009A_Init_Ext"]["kich_thuoc"] == 0x744
    assert not d["ky_hieu"]["OTM8009A_Init_Ext"]["rong_tuech"]
    # Ký hiệu xin mà không có phải được NÓI RA, không im lặng biến mất.
    assert d["thieu"] == ["khong_co"]


def test_ham_TRA_HANG_SO_bi_bat_con_VO_MONG_thi_khong(tmp_path, monkeypatch):
    """Đo được trên bo STM32F469 ngày 28/09/2026, và đây là lỗi sống lâu nhất của phiên:

        uint16_t OTM8009A_ReadID(void) { return OTM8009A_ID; }
        static inline uint16_t NT35510_ReadID(void) { return 0; }

    Phép "dò loại panel" của BSP không dò gì — nó **khai báo** kết quả. Biến
    `Lcd_Driver_Type` đọc ra `LCD_CTRL_OTM8009A` là lời của MÃ, không phải lời của panel. Nó
    sống sót qua mười lượt gỡ lỗi vì mọi phép đo đều hỏi "giá trị bằng bao nhiêu" chứ không
    ai hỏi "ai đặt ra giá trị ấy". N6 (không báo đạt giả), lần này nằm trong firmware.

    Nhưng kích thước KHÔNG đủ để kết luận: `BSP_LCD_Init` cũng chỉ 6 byte, mà thân nó là
    `movs r0,#1 ; b.w BSP_LCD_InitEx` — một vỏ mỏng, hoàn toàn bình thường. Gọi nó là "trả
    hằng số" là báo động giả, và báo động giả dạy người ta bỏ qua cảnh báo.
    """
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    nm_ra = ("08000f94 00000004 T OTM8009A_ReadID\n"
             "0800158c 00000006 T BSP_LCD_Init\n")
    dis = {0x08000F94: " 8000f94:\t2040      \tmovs\tr0, #64\n 8000f96:\t4770      \tbx\tlr\n",
           0x0800158C: (" 800158c:\t2001      \tmovs\tr0, #1\n"
                        " 800158e:\tf7ff beed \tb.w\t800136c <BSP_LCD_InitEx>\n")}

    def _run(cl, **k):
        if "objdump" in cl[0]:
            dc = int(next(x for x in cl if x.startswith("--start-address")).split("=")[1], 16)
            return subprocess.CompletedProcess(cl, 0, dis[dc], "")
        return subprocess.CompletedProcess(cl, 0, nm_ra, "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: f"/fake/{x}")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.ky_hieu_theo_ten(elf, ["OTM8009A_ReadID", "BSP_LCD_Init"])

    stub = d["ky_hieu"]["OTM8009A_ReadID"]
    assert stub["tra_hang_so"] and "lời của MÃ" in stub["canh_bao"]
    assert "movs r0, #64" in stub["ma_may"] and "bx lr" in stub["ma_may"]

    vo = d["ky_hieu"]["BSP_LCD_Init"]
    assert vo["vo_mong"] and vo["rong_tuech"] is False
    assert "canh_bao" not in vo and "Bình thường" in vo["ghi_chu"]


def test_ham_nho_ma_thieu_objdump_thi_CHUA_KET_LUAN(tmp_path, monkeypatch):
    """"Chưa phân biệt được" không phải "trả hằng số" — trạng thái thứ ba, lần thứ N."""
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    monkeypatch.setattr(MT.shutil, "which",
                        lambda x: "/fake/nm" if x.endswith("nm") else None)
    monkeypatch.setattr(MT.subprocess, "run", lambda cl, **k: subprocess.CompletedProcess(
        cl, 0, "08000f94 00000004 T OTM8009A_ReadID\n", ""))
    v = MT.ky_hieu_theo_ten(elf, ["OTM8009A_ReadID"])["ky_hieu"]["OTM8009A_ReadID"]
    assert "Chưa kết luận" in v["canh_bao"] and "tra_hang_so" not in v


def test_ky_hieu_theo_ten_doc_duoc_dong_BA_COT(tmp_path, monkeypatch):
    """`nm -S` bỏ cột kích thước với một số ký hiệu. Bỏ qua dòng ba cột thì đúng những ký
    hiệu ấy im lặng biến thành "không tìm thấy"."""
    import subprocess

    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/nm")
    monkeypatch.setattr(MT.subprocess, "run", lambda cl, **k: subprocess.CompletedProcess(
        cl, 0, "20000100 D uwTick\n", ""))
    d = MT.ky_hieu_theo_ten(elf, ["uwTick"])
    assert d["ky_hieu"]["uwTick"]["dia_chi"] == 0x20000100
    assert d["ky_hieu"]["uwTick"]["kich_thuoc"] == 0 and not d["thieu"]


def test_ky_hieu_theo_ten_thieu_nm_thi_KHONG_TRA_DUOC_chu_khong_phai_khong_ton_tai(
        tmp_path, monkeypatch):
    elf = tmp_path / "mach.elf"
    elf.write_bytes(b"ELF")
    monkeypatch.setattr(MT.shutil, "which", lambda x: None)
    d = MT.ky_hieu_theo_ten(elf, ["x"])
    assert not d["dat"] and "KHÁC với ký hiệu không tồn tại" in d["vi_sao_khong_dat"]


def test_target_debug_doc_bien_theo_TEN_va_to_cao_ham_tra_hang_so(make_agent, monkeypatch):
    """Câu hỏi "giá trị bằng bao nhiêu" và câu hỏi "ai đặt ra giá trị ấy" là hai câu khác
    nhau, và suốt mười lượt gỡ lỗi chỉ câu thứ nhất được hỏi."""
    import subprocess

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"ELF" * 40)
    nm_ra = ("200000b0 00000001 B Lcd_Driver_Type\n"
             "08000f94 00000004 T OTM8009A_ReadID\n")

    def _run(cl, **k):
        if "nm" in cl[0]:
            return subprocess.CompletedProcess(cl, 0, nm_ra, "")
        if "objdump" in cl[0]:
            return subprocess.CompletedProcess(
                cl, 0, " 8000f94:\t2040      \tmovs\tr0, #64\n 8000f96:\t4770      \tbx\tlr\n", "")
        if "a2l" in cl[0]:
            return subprocess.CompletedProcess(cl, 0, "main\n/x/main.c:79\n" * 9, "")
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2002ffd0\n"
                   "0x200000b0: 00000001 \n", "")

    monkeypatch.setattr(MT.shutil, "which",
                        lambda x: {"openocd": "/fake/openocd",
                                   "arm-none-eabi-nm": "/fake/nm",
                                   "arm-none-eabi-objdump": "/fake/objdump",
                                   "arm-none-eabi-addr2line": "/fake/a2l"}.get(x))
    monkeypatch.setattr(MT.subprocess, "run", _run)
    r = agent.registry.run(
        "target.debug", {"bien": ["Lcd_Driver_Type", "OTM8009A_ReadID"]}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    n = r.data["note_vi"]
    assert "Lcd_Driver_Type @ 0x200000B0 = 0x00000001" in n
    assert "OTM8009A_ReadID" in n and "lời của MÃ" in n
    assert r.data["bien"]["OTM8009A_ReadID"]["tra_hang_so"] is True


def test_loi_khuyen_phai_KHOP_voi_ly_do_vua_neu(make_agent, monkeypatch):
    """Đo trên phiên FreeRTOS: `target.flash` nói *"đọc được STM32F46x_F47x từ bo nhưng dự án
    chưa ghim chip nào để so"* — rồi khuyên **"cài `st-info`/`st-flash`"**. Thứ ấy đã cài
    rồi, và chính nó vừa đọc ra câu trên.

    Một lời khuyên không khớp lý do thì tệ hơn im lặng: nó gửi tác tử đi làm một việc vốn đã
    xong. Thứ thiếu ở đây là **hộ chiếu chip của dự án**.
    """
    import subprocess

    agent = make_agent([])
    o = _o_gia(tmp_o := agent.config.paths.project_root / "V", "DIS_F469NI")
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_o / "Volumes")
    monkeypatch.setattr(MT, "THU_MUC_DEV", agent.config.paths.project_root)
    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/st-info")
    monkeypatch.setattr(MT.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a[0], 0, "  dev-type:   STM32F46x_F47x\n", ""))
    b = agent.config.paths.project_root / ".eide" / "build" / "mach.bin"
    b.parent.mkdir(parents=True, exist_ok=True)
    b.write_bytes(BIN)
    assert o.exists()

    r = agent.registry.run("target.flash", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4013"
    h = r.error.hint_for_agent
    assert "passport.pin" in h and "CHƯA GHIM" in h
    assert "Cài `st-info`" not in h, "đừng bảo cài thứ vừa dùng để đọc ra kết quả"
