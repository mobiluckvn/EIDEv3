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


def test_soi_chip_o_Thread_thi_KHONG_doc_khung_ngat(monkeypatch):
    """Không ở trong ngắt thì không có khung ngoại lệ nào để đọc — đừng dựng một cái ra."""
    import subprocess

    lan: list[int] = []

    def _run(cl, **k):
        lan.append(1)
        return subprocess.CompletedProcess(
            cl, 0, "[stm32f4x.cpu] halted due to debug-request, current mode: Thread\n"
                   "xPSR: 0x01000000 pc: 0x08000200 msp: 0x2002ffd0\n", "")

    monkeypatch.setattr(MT.shutil, "which", lambda x: "/fake/openocd")
    monkeypatch.setattr(MT.subprocess, "run", _run)
    d = MT.soi_chip()
    assert len(lan) == 1 and "khung_ngat" not in d


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
