# -*- coding: utf-8 -*-
"""ING-D — cấu hình vendor và tầng CẤU HÌNH. EIDE-ING-43 §4.5, ING-10/11. Ca ING08.

Điều bộ này canh, một câu: **`.ld` khai 64 KB không làm chip có 64 KB.**

Đó là một lỗi im lặng kinh điển — mã biên dịch xong, nạp vào chạy được một lúc rồi hỏng
ở chỗ không ai ngờ. Có hai con số cạnh nhau thì phát hiện trong một giây; gộp chúng vào
cùng một tầng tin cậy thì không bao giờ phát hiện.
"""

from __future__ import annotations

import pytest

from eide.knowledge.compare import TANG_DUNG_DUOC
from eide.knowledge.vendor import (CAP_DOI_CHIEU, TANG_CAU_HINH, doc_cau_hinh,
                                   doi_chieu_cau_hinh, fact_cau_hinh, loai_tu_ten)


# =========================================================================== ranh giới
def test_ING11_tang_CAU_HINH_khong_bao_gio_la_ve_so_sanh():
    """Giữ bằng CẤU TRÚC, không bằng lời dặn: tầng này không nằm trong tập dùng được,
    nên `fact.compare` tự động từ chối. Không ai phải nhớ quy tắc."""
    assert TANG_CAU_HINH not in TANG_DUNG_DUOC


def test_ING11_fact_compare_tu_choi_ve_CAU_HINH(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    agent.store.put_fact({"fact_id": "f_ds", "subject": "chip:X", "key": "flash.size",
                          "value": 32768, "unit": "B", "tier": "BAC",
                          "origin": "extract", "source": {"doc_id": "DS", "page": 5},
                          "explain": {}})
    agent.store.put_fact({"fact_id": "f_cfg", "subject": "config", "key": "config:flash.size",
                          "value": 65536, "unit": "B", "tier": TANG_CAU_HINH,
                          "origin": "config", "source": {"file": "x.ld"}, "explain": {}})
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    r = agent.registry.run("fact.compare", {"luat": "ngan_sach_bo_nho",
                                            "fact_a": "f_ds", "fact_b": "f_cfg"}, ctx)
    assert r.ok and r.data["chua_kiem_chung"], \
        "một vế là CẤU HÌNH thì không được ra kết luận về giới hạn vật lý"
    # Phải từ chối VÌ TẦNG. Tên luật lạ cũng trả `chua_kiem_chung`, nên nếu không kiểm
    # thêm câu này thì ca đo đậu vì lý do sai (N6).
    assert "luật" not in r.data.get("giai_thich", ""), r.data.get("giai_thich")


# =========================================================================== .ld
def test_doc_linker_script(tmp_path):
    p = tmp_path / "link.ld"
    p.write_text("""MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 64K
  RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 20K
}
""", "utf-8")
    c, vi = doc_cau_hinh(p)
    assert c is not None and c.loai == "linker", vi
    assert c.khoa["config:flash.size"] == "65536 B"
    assert c.khoa["config:ram.size"] == "20480 B"
    assert c.khoa["config:flash.origin"] == "0x08000000"


def test_linker_khong_co_MEMORY_thi_noi_ra(tmp_path):
    p = tmp_path / "la.ld"
    p.write_text("INCLUDE common.ld\n", "utf-8")
    c, _ = doc_cau_hinh(p)
    assert c is not None and not c.khoa
    assert c.canh_bao and "MEMORY" in c.canh_bao[0]


# =========================================================================== ING08
def test_ING08_ld_khai_64K_ma_chip_co_32K_thi_PHAT_HIEN(tmp_path):
    ch = [{"fact_id": "fc", "key": "config:flash.size", "value": 65536, "unit": "B",
           "tier": TANG_CAU_HINH, "origin": "config", "source": {"file": "link.ld"}}]
    ds = [{"fact_id": "fd", "key": "flash.size", "value": 32768, "unit": "B",
           "tier": "BAC", "origin": "extract", "source": {"doc_id": "DS", "page": 12}}]
    lech = doi_chieu_cau_hinh(ch, ds)
    assert len(lech) == 1 and lech[0]["muc"] == "vuot"
    assert "32768" in lech[0]["message_vi"] or "32768" in str(lech[0]["tai_lieu"])
    assert "không lộ ra lúc biên dịch" in lech[0]["message_vi"]


def test_ING08_cau_hinh_vua_du_thi_khong_bao_dong(tmp_path):
    ch = [{"fact_id": "fc", "key": "config:flash.size", "value": 32768, "unit": "B",
           "tier": TANG_CAU_HINH, "origin": "config", "source": {}}]
    ds = [{"fact_id": "fd", "key": "flash.size", "value": 32768, "unit": "B",
           "tier": "BAC", "origin": "extract", "source": {}}]
    assert doi_chieu_cau_hinh(ch, ds) == []


def test_dung_gan_het_thi_CANH_BAO_chu_khong_bao_loi():
    ch = [{"fact_id": "fc", "key": "config:flash.used", "value": 31000, "unit": "B",
           "tier": TANG_CAU_HINH, "origin": "config", "source": {}}]
    ds = [{"fact_id": "fd", "key": "flash.size", "value": 32768, "unit": "B",
           "tier": "BAC", "origin": "extract", "source": {}}]
    lech = doi_chieu_cau_hinh(ch, ds)
    assert len(lech) == 1 and lech[0]["muc"] == "gan_het"
    assert "94" in lech[0]["message_vi"] or "%" in lech[0]["message_vi"]


def test_don_vi_khac_nhau_thi_khong_so_bua():
    ch = [{"fact_id": "fc", "key": "config:cpu.freq", "value": 160, "unit": "MHz",
           "tier": TANG_CAU_HINH, "origin": "config", "source": {}}]
    ds = [{"fact_id": "fd", "key": "fmax", "value": 240, "unit": "MHz",
           "tier": "BAC", "origin": "extract", "source": {}}]
    assert doi_chieu_cau_hinh(ch, ds) == [], "160 MHz < 240 MHz thì không có gì lệch"


# =========================================================================== .ioc
def test_doc_cubemx_ioc(tmp_path):
    p = tmp_path / "bo.ioc"
    p.write_text("""Mcu.Name=STM32F103C8Tx
Mcu.Family=STM32F1
PA5.Signal=SPI1_SCK
PA6.Signal=SPI1_MISO
RCC.SYSCLKFreq_VALUE=72000000
""", "utf-8")
    c, _ = doc_cau_hinh(p)
    assert c.loai == "ioc"
    assert c.khoa["config:mcu.name"] == "STM32F103C8Tx"
    assert c.khoa["config:pin.PA5.af"] == "SPI1_SCK"
    # Tần số phải có ĐƠN VỊ — 72000000 trần thì người phải đoán Hz hay kHz.
    assert c.khoa["config:clock.sysclkfreq_value"] == "72000000 Hz"


# =========================================================================== sdkconfig
def test_doc_sdkconfig(tmp_path):
    p = tmp_path / "sdkconfig"
    p.write_text("""CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ=160
CONFIG_FREERTOS_HZ=1000
CONFIG_KHONG_QUAN_TAM=y
""", "utf-8")
    c, _ = doc_cau_hinh(p)
    assert c.loai == "sdkconfig"
    assert c.khoa["config:cpu.freq"] == "160 MHz"
    assert c.khoa["config:rtos.tick"] == "1000 Hz"
    assert "CONFIG_KHONG_QUAN_TAM" in c.tho, "khoá thô vẫn giữ để tra lại"
    assert "config:CONFIG_KHONG_QUAN_TAM" not in c.khoa


# =========================================================================== devicetree
def test_doc_devicetree_va_noi_ro_gioi_han(tmp_path):
    p = tmp_path / "bo.dts"
    p.write_text("""/dts-v1/;
#include <st/f1/stm32f103.dtsi>
&i2c1 {
    clock-frequency = <400000>;
    status = "okay";
};
""", "utf-8")
    c, _ = doc_cau_hinh(p)
    assert c.loai == "devicetree"
    assert c.khoa["config:i2c1.clock-frequency"] == "400000 Hz"
    assert c.khoa["config:i2c1.status"] == '"okay"'
    # Nói rõ giới hạn thay vì hứa nhiều hơn khả năng.
    assert c.canh_bao and "#include" in c.canh_bao[0] and "dtc" in c.canh_bao[0]


# =========================================================================== map
def test_doc_map_tinh_flash_va_ram_da_dung(tmp_path):
    p = tmp_path / "a.map"
    p.write_text(""" .text          0x08000000     0x1000
 .rodata        0x08001000      0x200
 .data          0x20000000       0x40
 .bss           0x20000040      0x100
""", "utf-8")
    c, _ = doc_cau_hinh(p)
    assert c.loai == "map"
    assert c.khoa["config:flash.used"] == f"{0x1000 + 0x200 + 0x40} B"
    assert c.khoa["config:ram.used"] == f"{0x100 + 0x40} B"


# =========================================================================== → Fact
def test_fact_cau_hinh_mang_dung_tang_va_noi_ro_y_nghia(tmp_path):
    p = tmp_path / "link.ld"
    p.write_text("MEMORY { FLASH (rx) : ORIGIN = 0x0, LENGTH = 64K }\n", "utf-8")
    c, _ = doc_cau_hinh(p)
    f = fact_cau_hinh(c, "config:flash.size", c.khoa["config:flash.size"])
    assert f["tier"] == TANG_CAU_HINH and f["origin"] == "config"
    assert f["value"] == pytest.approx(65536)
    assert "DỰ ÁN ĐANG ĐẶT" in f["explain"]["why"]
    assert "Đối chiếu" in f["explain"]["next"]
    assert f["source"]["quote"].startswith("config:flash.size =")


def test_loai_tu_ten_nhan_dung_cac_duoi():
    from pathlib import Path

    assert loai_tu_ten(Path("a.ioc")) == "ioc"
    assert loai_tu_ten(Path("a.dts")) == "devicetree"
    assert loai_tu_ten(Path("a.overlay")) == "devicetree"
    assert loai_tu_ten(Path("a.ld")) == "linker"
    assert loai_tu_ten(Path("a.map")) == "map"
    assert loai_tu_ten(Path("sdkconfig")) == "sdkconfig"
    assert loai_tu_ten(Path("sdkconfig.defaults")) == "sdkconfig"
    assert loai_tu_ten(Path("a.txt")) == ""


def test_moi_cap_doi_chieu_deu_co_TEN_TIENG_VIET():
    for ch, ds, ten in CAP_DOI_CHIEU:
        assert ch.startswith("config:") and ds and ten
        assert ten == ten.lower() or " " in ten, ten


# =========================================================================== qua công cụ
def test_config_load_qua_cong_cu_va_canh_bao_lech(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "link.ld").write_text(
        "MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 64K }\n", "utf-8")
    agent.store.put_fact({"fact_id": "fd", "subject": "chip:X", "key": "flash.size",
                          "value": 32768, "unit": "B", "tier": "BAC",
                          "origin": "extract", "source": {"doc_id": "DS", "page": 12},
                          "explain": {}})

    thay: list = []
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=thay.append, history=agent.history, run_id="run-1")
    ex = {"summary": "nạp cấu hình", "why": "để đối chiếu", "sources": [],
          "diff_prev": "—", "next": "—", "confidence": "CAUHINH"}
    r = agent.registry.run("config.load", {"path": "link.ld", "explain": ex}, ctx)

    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["tang"] == TANG_CAU_HINH
    assert r.data["lech_voi_tai_lieu"], "phải phát hiện 64K vs 32K"
    assert "KHÔNG dùng nó làm vế giới hạn vật lý" in r.data["note_vi"]
    loi = [c for c in thay if c.method == "notice" and c.params.get("level") == "error"]
    assert loi, "lệch kiểu 'vượt' phải là notice mức error, không phải info"


def test_config_load_tu_choi_tep_khong_phai_cau_hinh(make_agent):
    from eide.loop import TurnContext

    agent = make_agent([])
    (agent.config.paths.project_root / "a.txt").write_text("xin chào\n", "utf-8")
    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, run_id="run-1")
    ex = {"summary": "x", "why": "y", "sources": [], "diff_prev": "—", "next": "—",
          "confidence": "CAUHINH"}
    r = agent.registry.run("config.load", {"path": "a.txt", "explain": ex}, ctx)
    assert not r.ok and "chưa có bộ đọc cấu hình" in r.error.message_vi
    assert "ingest.file" in r.error.alternatives


def test_ten_tang_KHONG_BAO_GIO_lam_chet_mot_luot():
    """Lỗi tìm ra khi chạy thật: thêm tầng CẤU HÌNH làm `KeyError` trong hàm dựng
    `<inventory>` — tức giết cả lượt TRƯỚC khi mô hình được gọi.

    Một phép tra TÊN HIỂN THỊ không được phép có sức mạnh đó.
    """
    from eide.knowledge.compare import TEN_TANG_VI, THU_TU_TANG, ten_tang

    assert ten_tang("CAUHINH") == "CẤU HÌNH"
    assert ten_tang("TANG-CHUA-CO") == "TANG-CHUA-CO"   # lạ thì hiện mã, không nổ
    assert ten_tang("") == "?"
    assert ten_tang("cauhinh") == "CẤU HÌNH"            # không phân biệt hoa/thường
    assert set(THU_TU_TANG) == set(TEN_TANG_VI)


def test_kiem_ke_render_duoc_voi_tang_moi(make_agent):
    from eide.store import inventory

    agent = make_agent([])
    for ma, tang in (("f1", "BAC"), ("f2", TANG_CAU_HINH), ("f3", "TANG-LA")):
        agent.store.put_fact({"fact_id": ma, "subject": "chip:X", "key": f"k{ma}",
                              "value": 1, "unit": "V", "tier": tang,
                              "origin": "extract", "source": {}, "explain": {}})
    inv = inventory.build(agent.store, ledger=agent.ledger, project_name="x")
    chu = inv.render()
    assert "CẤU HÌNH 1" in chu
    assert "BẠC 1" in chu
