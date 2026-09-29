# -*- coding: utf-8 -*-
"""Xuất và nhập một dự án EIDE thành `.zip`.

Chép thư mục vốn đã mang dự án đi được. Lệnh này tồn tại vì làm tay thì hai chuyện hay xảy ra,
và cả hai chỉ lộ ra về sau:

* **Chép cả đống** — đo trên dự án FreeRTOS: 14,4 MB, trong đó `.eide/build/` chiếm 3,0 MB
  dựng lại được.
* **Lọc bằng cảm giác rồi bỏ mất sổ cái** — `.eide/` là thư mục ẩn, tên không gợi gì, và
  trong dự án còn bị `.gitignore`. Người gọn gàng sẽ bỏ nó, và mất im lặng: bản chép vẫn mở
  được, chỉ là không còn quá khứ.
"""

from __future__ import annotations

import zipfile

import pytest

from eide.goi_du_an import KE_KHAI, nhap, xuat


def _du_an(tmp_path, ten="goc"):
    from eide.config import Config
    from eide.llm.offline import ScriptedGateway
    from eide.loop import Agent

    d = tmp_path / ten
    d.mkdir()
    ag = Agent(Config.for_project(d), llm=ScriptedGateway([]), project_name=ten)
    (d / "firmware").mkdir()
    (d / "firmware/main.c").write_text("int main(void){return 0;}\n", "utf-8")
    (d / ".eide/build").mkdir(parents=True, exist_ok=True)
    (d / ".eide/build/mach.bin").write_bytes(b"\x00" * 200_000)   # thứ dựng lại được
    ag.ledger.append("turn.end", {"run_id": "run-1"})
    return d


def test_goi_gon_bo_thu_dung_lai_duoc_va_giu_thu_ben(tmp_path):
    d = _du_an(tmp_path)
    k = xuat(d, tmp_path / "goi.zip")
    assert k.dat, k.vi_sao_khong_dat
    ten = set(zipfile.ZipFile(tmp_path / "goi.zip").namelist())
    assert ".eide/ledger.jsonl" in ten, "BỎ SỔ CÁI là mất toàn bộ quá khứ"
    assert "EIDE.md" in ten and "firmware/main.c" in ten
    assert not any(x.startswith(".eide/build/") for x in ten), "bản biên dịch dựng lại được"
    assert dict(k.da_bo).get(".eide/build", 0) >= 200_000, (
        "phải nói TIẾT KIỆM ĐƯỢC BAO NHIÊU — người quyết bằng số, không bằng cảm giác")


def test_goi_khong_gon_thi_giu_tat_ca(tmp_path):
    d = _du_an(tmp_path)
    xuat(d, tmp_path / "day-du.zip", gon=False)
    ten = set(zipfile.ZipFile(tmp_path / "day-du.zip").namelist())
    assert any(x.startswith(".eide/build/") for x in ten)


def test_xuat_vao_TRONG_du_an_khong_tu_goi_chinh_minh(tmp_path):
    """Gói ghi vào trong dự án thì vòng quét bắt gặp chính nó.

    Đo được 29/09/2026: lệnh chạy MÃI không dừng và tệp phình tới khi hết đĩa — một vòng lặp
    không có ai chặn, và nó chỉ lộ ra khi đã muộn. Công cụ `project.export` bắt buộc ghi vào
    trong dự án (để không ghi ra ngoài hộp cát), nên đây là đường đi thường gặp nhất, không
    phải một ca hiếm.
    """
    d = _du_an(tmp_path)
    k = xuat(d, d / "goi" / "ban-giao.zip")
    assert k.dat
    ten = set(zipfile.ZipFile(d / "goi/ban-giao.zip").namelist())
    assert "goi/ban-giao.zip" not in ten
    assert k.byte_goi < 5_000_000, "gói phình bất thường — nhiều khả năng đã tự gói chính nó"


def test_nhap_lai_mo_duoc_va_so_cai_con_toan_ven(tmp_path):
    d = _du_an(tmp_path)
    xuat(d, tmp_path / "goi.zip")
    n = nhap(tmp_path / "goi.zip", tmp_path / "moi")
    assert n.dat, n.vi_sao_khong_dat
    assert n.so_cai_toan_ven is True, n.so_cai_noi
    assert (tmp_path / "moi/firmware/main.c").exists()
    assert KE_KHAI not in {x.name for x in (tmp_path / "moi").rglob("*")}


def test_nhap_vao_thu_muc_DANG_CO_du_an_thi_tu_choi(tmp_path):
    """Trộn hai lịch sử vào nhau là hỏng cả hai, và hỏng theo cách không ai gỡ được."""
    d = _du_an(tmp_path)
    xuat(d, tmp_path / "goi.zip")
    cu = _du_an(tmp_path, "da-co")
    n = nhap(tmp_path / "goi.zip", cu)
    assert not n.dat and "trộn hai lịch" in n.vi_sao_khong_dat


def test_goi_co_muc_tro_ra_ngoai_thi_khong_giai_nen(tmp_path):
    """Một gói dựng bằng tay có thể mang `../../` trong tên mục — giải nén thẳng là ghi đè
    tệp NGOÀI thư mục đích."""
    xau = tmp_path / "xau.zip"
    with zipfile.ZipFile(xau, "w") as z:
        z.writestr("../thoat-ra.txt", "x")
    n = nhap(xau, tmp_path / "dich")
    assert not n.dat and "ra ngoài" in n.vi_sao_khong_dat
    assert not (tmp_path / "thoat-ra.txt").exists()
