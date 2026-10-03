# -*- coding: utf-8 -*-
"""Bộ đo của chính bộ đo: những chỗ mà một phiên có thể nói sai về thứ nó đang đo.

Hai lỗi thật, cùng một họ — **bộ đo đưa ra một sở cứ không khớp với thứ nó làm chứng cho**:

1. Gói `EIDE.app` dựng 30/09, mã Swift đã qua bốn commit sau đó. Mọi phiên giao diện ngày
   03/10 đo bằng bản cũ. Không có lỗi nào kêu lên.
2. Bản cũ cắt lời tác tử ở 3000 ký tự **không dán dấu**, nên 16 câu trong `NHAT-KY.md`
   mất đuôi mà câu cuối trông như một câu kết thúc bình thường. Tôi đã đọc nhật ký ấy rồi
   kết luận sai rằng tác tử không trả lời một câu hỏi — nó trả lời đủ, ở đoạn đã mất.

Bộ kiểm ở đây không hỏi "mã có đúng không". Nó hỏi **"thứ tôi sắp đo có phải là mã tôi
vừa sửa không"**, và **"nhật ký có đang giữ đủ lời hay không"**.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import phien_robot as PR  # noqa: E402


# ------------------------------------------------- gói app phải mới hơn mã nguồn
def test_goi_app_cu_hon_nguon_thi_phien_dung(tmp_path, monkeypatch):
    nguon = tmp_path / "Sources"
    nguon.mkdir()
    (nguon / "A.swift").write_text("// x", "utf-8")
    goi = tmp_path / "EIDE"
    goi.write_bytes(b"nhi phan")
    os.utime(goi, (0, time.time() - 600))          # gói CŨ
    os.utime(nguon / "A.swift", (0, time.time()))  # nguồn MỚI
    monkeypatch.setattr(PR, "APP", goi)
    monkeypatch.setattr(PR, "NGUON_SWIFT", nguon)
    with pytest.raises(SystemExit) as e:
        PR.doi_chieu_app_voi_nguon()
    loi = str(e.value)
    assert "CŨ HƠN MÃ NGUỒN" in loi
    # Phải nêu TÊN TỆP: "có gì cũ" không giúp ai, "tệp nào cũ" thì sửa được ngay.
    assert "A.swift" in loi
    # Và phải chỉ ra cách chữa, vì người đọc lỗi này đang ở giữa một phiên dở dang.
    assert "dong-goi.sh" in loi


def test_goi_app_moi_hon_nguon_thi_khong_can_tro(tmp_path, monkeypatch):
    """Nửa đối: chốt này phải IM khi gói đã mới. Một chốt lúc nào cũng kêu thì bị tắt."""
    nguon = tmp_path / "Sources"
    nguon.mkdir()
    (nguon / "A.swift").write_text("// x", "utf-8")
    os.utime(nguon / "A.swift", (0, time.time() - 600))
    goi = tmp_path / "EIDE"
    goi.write_bytes(b"nhi phan")
    monkeypatch.setattr(PR, "APP", goi)
    monkeypatch.setattr(PR, "NGUON_SWIFT", nguon)
    PR.doi_chieu_app_voi_nguon()   # không được nổ


def test_thieu_goi_app_thi_noi_ro_la_thieu(tmp_path, monkeypatch):
    nguon = tmp_path / "Sources"
    nguon.mkdir()
    monkeypatch.setattr(PR, "APP", tmp_path / "khong-co")
    monkeypatch.setattr(PR, "NGUON_SWIFT", nguon)
    with pytest.raises(SystemExit) as e:
        PR.doi_chieu_app_voi_nguon()
    assert "dong-goi.sh" in str(e.value)


# --------------------------------------------- lấy lại lời đủ từ bản ghi của app
def _du_an_co_ban_ghi(goc: pathlib.Path, loi: list[str]) -> pathlib.Path:
    d = goc / ".eide/sessions/ses-0001"
    d.mkdir(parents=True)
    with (d / "transcript.jsonl").open("w", encoding="utf-8") as f:
        for t in loi:
            f.write(json.dumps({"role": "model", "text": t}, ensure_ascii=False) + "\n")
    return goc


def test_lay_lai_duoc_duoi_bi_cat_tu_ban_ghi(tmp_path):
    day = "Chào anh, " + "A" * 3000 + " KẾT LUẬN: đúng 3 bitstream."
    du_an = _du_an_co_ban_ghi(tmp_path / "da", [day])
    bi_cat = day[:3000]
    ra = PR._loi_day_tu_ban_ghi(du_an, bi_cat)
    assert ra == day
    # Phần giá trị nhất là ĐUÔI — chỗ duy nhất chứa kết luận.
    assert "đúng 3 bitstream" in ra


def test_khong_co_ban_ghi_thi_tra_ve_rong_chu_khong_doan(tmp_path):
    du_an = _du_an_co_ban_ghi(tmp_path / "da", ["Một lời hoàn toàn khác" * 20])
    assert PR._loi_day_tu_ban_ghi(du_an, "Chào anh, " + "A" * 3000) == ""


def test_khong_chep_lan_loi_cua_luot_khac(tmp_path):
    """Khớp phải theo đoạn đầu. Chép lẫn lời lượt khác là làm sở cứ nói sai, tệ hơn thiếu."""
    a = "Lời thứ nhất về reset_gen. " + "A" * 3000 + " đuôi A"
    b = "Lời thứ hai về bitstream. " + "B" * 3000 + " đuôi B"
    du_an = _du_an_co_ban_ghi(tmp_path / "da", [a, b])
    assert PR._loi_day_tu_ban_ghi(du_an, b[:3000]).endswith("đuôi B")
    assert PR._loi_day_tu_ban_ghi(du_an, a[:3000]).endswith("đuôi A")


def test_mam_qua_ngan_thi_khong_khop_bua(tmp_path):
    """Lời ngắn (`ok`, `vâng`) không đủ để khớp — khớp bừa sẽ gắn sai lời cho sai bước."""
    du_an = _du_an_co_ban_ghi(tmp_path / "da", ["ok ạ, em làm ngay đây" + "X" * 3000])
    assert PR._loi_day_tu_ban_ghi(du_an, "ok ạ") == ""


# --------------------------------------------------------- bộ vá nhật ký đã chạy
def test_bo_va_nhat_ky_dan_dau_vao_cho_da_sua(tmp_path):
    """Vá sở cứ mà không nói là đã vá thì chính bản vá trở thành chỗ không ai kiểm được."""
    sys.path.insert(0, str(REPO / "tools"))
    import va_nhat_ky_bi_cat as VA

    day = "Chào anh, " + "A" * 3000 + " KẾT LUẬN: đúng 3 bitstream."
    du_an = _du_an_co_ban_ghi(tmp_path / "da", [day])
    ra = tmp_path / "kq"
    ra.mkdir()
    (ra / "NHAT-KY.md").write_text(
        "## Bước 1. thử\n\n**Tác tử:**\n\n> " + day[:3000].replace("\n", "\n> ")
        + "\n\n**Công cụ tác tử đã gọi**\n", "utf-8")
    VA.main([str(ra), str(du_an)])
    s = (ra / "NHAT-KY.md").read_text("utf-8")
    assert "đúng 3 bitstream" in s
    assert "đã được vá" in s
    # Bản trước khi vá phải còn, để so được.
    assert (ra / "NHAT-KY.md.truoc-khi-va").exists()


def test_nhat_ky_fpga_khong_con_cau_nao_bi_cat_am_tham():
    """Chốt trên sở cứ THẬT: nhật ký phiên FPGA không còn câu nào dừng đúng ở 3000 ký tự.

    Đây là phép kiểm hồi quy trên dữ liệu, không trên mã: nếu ai chạy lại phiên bằng gói
    app cũ, con số 3000 sẽ hiện ra lại ở đây.
    """
    md = REPO / "du-lieu/ket-qua/fpga-sinhvien/NHAT-KY.md"
    if not md.exists():
        pytest.skip("chưa có nhật ký phiên FPGA")
    s = md.read_text("utf-8")
    import re
    xau = []
    for m in re.finditer(r"## Bước (\d+)\..*?(?=\n## Bước |\Z)", s, re.S):
        b = m.group(0)
        t = b.find("**Tác tử:**")
        if t < 0:
            continue
        moc = [x for x in (b.find("\n*(Bản trên", t), b.find("**Công cụ", t)) if x > 0]
        loi = b[t + 11:min(moc) if moc else len(b)].strip()
        # 3000 ký tự nguyên văn + 2 ký tự `> ` mỗi dòng: đoạn trích dài hơn bản gốc, nên
        # so trên bản đã gỡ dấu trích.
        tho = "\n".join(d[2:] if d.startswith("> ") else d for d in loi.split("\n"))
        if len(tho) == 3000:
            xau.append(m.group(1))
    assert not xau, f"các bước còn bị cắt đúng 3000 ký tự: {xau}"
