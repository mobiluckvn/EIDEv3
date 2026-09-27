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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "không có st-info"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "chưa có st-info"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
    monkeypatch.setattr(MT, "_cong_noi_tiep", lambda: [])
    d = MT.do_bo()
    assert d["so_thiet_bi"] == 0 and not d["nap_duoc"]


def test_khong_co_bo_thi_tra_danh_sach_kiem_tra_du_bon_muc(tmp_path, monkeypatch):
    """TC032 đòi đúng bốn thứ: nguồn, cáp, driver, chân BOOT/NRST."""
    (tmp_path / "Volumes").mkdir()
    monkeypatch.setattr(MT, "THU_MUC_O_DIA", tmp_path / "Volumes")
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
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
                        lambda: (chip_doc, "" if chip_doc else "chưa có st-info"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
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
    monkeypatch.setattr(MT, "doc_id_chip", lambda: ("", "x"))
    r = agent.registry.run("target.log", {"giay": 0.2}, _ctx(agent))
    assert not r.ok and "không đoán dùng cổng nào" in r.error.message_vi
    assert "tai nghe Bluetooth" in r.error.hint_for_agent


def test_log_qua_lau_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("target.log", {"giay": 600}, _ctx(agent))
    assert not r.ok and r.error.code == "E5001"
