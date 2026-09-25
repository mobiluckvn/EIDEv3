# -*- coding: utf-8 -*-
"""Hạ tầng SCH-0 — cờ tính năng · migration lược đồ · so hai lần chạy.

Ba thứ mà EIDE-SCH-44 §2.1 và §8 dựa vào nhưng bản đang chạy chưa có. Làm trước SCH-A
vì chúng là *bằng chứng* mà quy trình đưa tính năng vào đòi, chứ không phải phần của
tính năng.

Ca đo: SCH-17 (cờ tắt = không nhánh nào chạy), SCH-18 (migration có down),
SCH-19 (hồi quy hai chế độ giống 100 %).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from eide.config import Features
from eide.store.db import MIGRATIONS, SCHEMA_VERSION, Store
from eide.tools.registry import Registry, ToolSpec

REPO = Path(__file__).resolve().parents[1]


# =========================================================================== SCH-17 cờ
def _spec(ten: str, feature: str | None = None) -> ToolSpec:
    return ToolSpec(name=ten, group="Thử", summary_vi="thử", params={"type": "object"},
                    fn=lambda ctx: None, feature=feature)


def test_co_tat_thi_KHONG_DANG_KY_chu_khong_phai_giau(tmp_path):
    """SCH-44 §2.1: "tool sch.* không được đăng ký (mô hình không thấy)".

    Khác `core=False` (nạp trễ): cái đó vẫn đăng ký, chỉ giấu khỏi lược đồ cho tới khi
    `tool.search` mở ra — tức mô hình VẪN mở được. Cờ tắt thì không có đường nào.
    """
    r = Registry(Features(schematic=False))
    r.add(_spec("sch.compose", feature="schematic"))
    assert r.get("sch.compose") is None, "cờ tắt mà vẫn đăng ký"
    assert "sch.compose" not in [t.name for t in r.all()]
    assert "sch.compose" in r.bo_qua_vi_co

    # Kể cả tool.search cũng không moi ra được.
    assert not [x for x in r.search("sơ đồ kicad compose") if "sch" in x["name"]]


def test_co_bat_thi_dang_ky_binh_thuong():
    r = Registry(Features(schematic=True))
    r.add(_spec("sch.compose", feature="schematic"))
    assert r.get("sch.compose") is not None
    assert r.bo_qua_vi_co == []


def test_khong_biet_co_nao_thi_coi_nhu_TAT():
    """Thiếu thông tin thì nghiêng về phía an toàn, không nghiêng về phía tiện."""
    r = Registry(None)
    r.add(_spec("sch.compose", feature="schematic"))
    assert r.get("sch.compose") is None


def test_cong_cu_khong_gan_co_thi_khong_bi_anh_huong():
    r = Registry(Features(schematic=False))
    r.add(_spec("fs.read"))
    assert r.get("fs.read") is not None


def test_co_tat_thi_luoc_do_tool_khong_tang_mot_token_nao():
    """§2.2: điểm chạm registry phải đo được bằng token khối 2 (MEM-42 §4.1)."""
    from eide.tools import build_registry

    tat = build_registry(Features(schematic=False))
    bat = build_registry(Features(schematic=True))
    # Chưa có tool sch nào nên hai bên bằng nhau. Ca này canh cho LÚC SAU: khi SCH-A
    # thêm 8 tool, bên TẮT phải không đổi một công cụ, một token nào.
    #
    # Cố ý KHÔNG chốt cứng con số 48: bước khác thêm công cụ là chuyện bình thường, và
    # một ca đo đỏ vì lý do bình thường sẽ bị người ta sửa cho qua thay vì đọc.
    assert len(tat.all()) == len(bat.all())
    assert ([d["name"] for d in tat.declarations()]
            == [d["name"] for d in bat.declarations()])
    assert tat.bo_qua_vi_co == bat.bo_qua_vi_co == []


def test_co_doc_tu_bien_moi_truong(monkeypatch):
    """Cần để chạy hồi quy hai chế độ mà không sửa settings.json của người dùng."""
    monkeypatch.setenv("EIDE_FEATURE_SCHEMATIC", "1")
    assert Features.load().schematic is True
    monkeypatch.setenv("EIDE_FEATURE_SCHEMATIC", "0")
    assert Features.load().schematic is False


def test_mac_dinh_moi_co_deu_TAT():
    """SCH-17: mặc định tắt. Một tính năng mới không được tự bật trên máy ai."""
    monkey = Features()
    assert monkey.dang_bat() == []
    assert monkey.to_dict() == {"schematic": False}


def test_settings_json_hong_khong_lam_chet_app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    d = tmp_path / ".eide"
    d.mkdir()
    (d / "settings.json").write_text("{ rác không phải json", "utf-8")
    assert Features.load().schematic is False        # không nổ, và nghiêng về TẮT


def test_settings_json_bat_duoc_co(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("EIDE_FEATURE_SCHEMATIC", raising=False)
    d = tmp_path / ".eide"
    d.mkdir()
    (d / "settings.json").write_text('{"features": {"schematic": true}}', "utf-8")
    assert Features.load().schematic is True


# =========================================================================== SCH-18 lược đồ
def test_kho_moi_duoc_danh_so_luoc_do(tmp_path):
    s = Store(tmp_path / "k.sqlite")
    assert s.phien_ban_luoc_do == SCHEMA_VERSION == 1


def test_mo_lai_khong_ap_lai_migration(tmp_path):
    p = tmp_path / "k.sqlite"
    Store(p).close()
    s = Store(p)
    assert s.nang_cap() == [], "mở lại kho không được chạy lại migration"


def test_kho_cu_chua_danh_so_van_nang_cap_duoc(tmp_path):
    """Kho đã tồn tại từ trước khi có migration: `user_version` = 0, bảng đã có sẵn."""
    import sqlite3
    from eide.store.db import SCHEMA

    p = tmp_path / "cu.sqlite"
    db = sqlite3.connect(p)
    db.executescript(SCHEMA)
    db.commit()
    db.close()

    s = Store(p)
    assert s.phien_ban_luoc_do == 1, "phải nhận ra và đánh số, không nổ"
    s.put_fact({"fact_id": "f1", "subject": "chip:X", "key": "k", "value": 1,
                "unit": "V", "tier": "BAC", "origin": "extract", "source": {},
                "explain": {}})
    assert len(s.query_facts(limit=5)) == 1


def test_ha_cap_xuong_0_bi_tu_choi_neu_khong_noi_ro(tmp_path):
    """Gỡ một tính năng không được phép vô tình xoá cả kho của người."""
    s = Store(tmp_path / "k.sqlite")
    with pytest.raises(ValueError, match="xoá toàn bộ kho"):
        s.ha_cap(0)
    assert s.phien_ban_luoc_do == 1


def test_ha_cap_noi_ro_thi_go_duoc_va_len_lai_duoc(tmp_path):
    s = Store(tmp_path / "k.sqlite")
    assert s.ha_cap(0, cho_phep_xoa_goc=True) == [1]
    assert s.phien_ban_luoc_do == 0
    assert s.nang_cap() == [1]
    assert s.phien_ban_luoc_do == 1
    s.put_fact({"fact_id": "f1", "subject": "chip:X", "key": "k", "value": 1,
                "unit": "V", "tier": "BAC", "origin": "extract", "source": {},
                "explain": {}})
    assert len(s.query_facts(limit=5)) == 1


def test_moi_migration_co_du_bon_truong():
    for m in MIGRATIONS:
        assert m.phien_ban >= 1 and m.mo_ta and m.up and m.down, m


def test_phien_ban_migration_lien_tuc_va_tang_dan():
    assert [m.phien_ban for m in MIGRATIONS] == list(range(1, len(MIGRATIONS) + 1))


# =========================================================================== SCH-19 so
def _ghi(p: Path, ca: list[tuple[str, str, bool]], co: list[str] | None = None) -> None:
    with p.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"bo": "thu", "so_ca": len(ca), "co": co or []}) + "\n")
        for nhom, ten, dat in ca:
            f.write(json.dumps({"nhom": nhom, "ten": ten, "dat": dat},
                               ensure_ascii=False) + "\n")


def _so(a: Path, b: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "tools/so_ket_qua.py"),
                           str(a), str(b)], capture_output=True, text=True)


def test_hai_lan_chay_giong_het_thi_thoat_0(tmp_path):
    ca = [("A", "x", True), ("A", "y", True), ("B", "z", False)]
    _ghi(tmp_path / "a.jsonl", ca)
    _ghi(tmp_path / "b.jsonl", ca, co=["schematic"])
    r = _so(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
    assert r.returncode == 0, r.stdout
    assert "GIỐNG HỆT" in r.stdout


def test_mot_o_doi_tu_dat_sang_khong_dat_bi_goi_la_HOI_QUY(tmp_path):
    """Đây là thứ mắt bỏ qua khi đọc hai bảng 35 dòng — lý do lệnh này tồn tại."""
    _ghi(tmp_path / "a.jsonl", [("A", "x", True), ("A", "y", True)])
    _ghi(tmp_path / "b.jsonl", [("A", "x", True), ("A", "y", False)])
    r = _so(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
    assert r.returncode == 1
    assert "hồi quy" in r.stdout and "y" in r.stdout


def test_ca_them_bot_cung_bi_bat(tmp_path):
    _ghi(tmp_path / "a.jsonl", [("A", "x", True)])
    _ghi(tmp_path / "b.jsonl", [("A", "x", True), ("A", "moi", True)])
    r = _so(tmp_path / "a.jsonl", tmp_path / "b.jsonl")
    assert r.returncode == 1
    assert "chỉ có ở B" in r.stdout


def test_tep_rong_hoac_thieu_thi_thoat_2_khong_bao_la_GIONG(tmp_path):
    """Không có kết quả ≠ kết quả giống nhau — N6 áp vào chính bộ kiểm."""
    _ghi(tmp_path / "a.jsonl", [("A", "x", True)])
    (tmp_path / "rong.jsonl").write_text("", "utf-8")
    assert _so(tmp_path / "a.jsonl", tmp_path / "rong.jsonl").returncode == 2
    assert _so(tmp_path / "a.jsonl", tmp_path / "khong-co.jsonl").returncode == 2


def test_bo_ghi_ra_dung_dinh_dang(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools"))
    monkeypatch.setenv("EIDE_KETQUA", str(tmp_path / "ra.jsonl"))
    import thu_giao_dien

    b = thu_giao_dien.Bo("thu-nghiem")
    b.phan("Phần A")
    b.kiem("ca một", True, "bằng chứng này đổi mỗi lần chạy")
    b.kiem("ca hai", False)
    b.tong()

    dong = [json.loads(l) for l in (tmp_path / "ra.jsonl").read_text("utf-8").splitlines()]
    assert dong[0]["bo"] == "thu-nghiem" and dong[0]["so_ca"] == 2
    assert dong[1] == {"nhom": "Phần A", "ten": "ca một", "dat": True}
    assert "bc" not in dong[1], "bằng chứng KHÔNG được vào phép so — nó đổi mỗi lần chạy"
