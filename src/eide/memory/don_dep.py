# -*- coding: utf-8 -*-
"""Retention và dọn rác — EIDE-MEM-42 §7.4, MEM-19. Bước MEM-D.

Nguyên tắc duy nhất, và nó quyết định toàn bộ thiết kế: **dọn theo THAM CHIẾU, không
theo tuổi.**

Một blob 30 ngày tuổi mà một snapshot có tên đang trỏ tới là bằng chứng của một bản
người dùng sẽ quay về. Xoá nó theo tuổi là biến "khôi phục được" thành một lời hứa suông.
Ngược lại, một blob của `fs.read` hôm qua mà không ai trỏ tới thì giữ chỉ để tốn đĩa.

Nên `gc` làm hai việc theo đúng thứ tự: **đếm tham chiếu trước, xét tuổi sau**. Và nó
luôn chạy ở chế độ *đề xuất* trước — `thu=True` cho biết sẽ xoá gì, người quyết.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# §7.4 — giữ bao lâu. Mỗi con số đi kèm một câu nói vì sao.
GIU = {
    "transcript_ngay": 90,      # đủ để người quay lại một việc bỏ dở mấy tháng
    "blob_ngay": 30,            # chỉ áp dụng cho blob KHÔNG ai trỏ tới
    "checkpoint_nen_gio": 24,   # cửa sổ huỷ nén
    "checkpoint_hoan_tac_ngay": 30,
}

# Vĩnh viễn, không bao giờ dọn: sổ cái, changeset, kho, snapshot có tên, EIDE.md.
KHONG_BAO_GIO_DON = ("ledger.jsonl", "changesets.jsonl", "store.sqlite", "EIDE.md")

_HASH = re.compile(r"\b([0-9a-f]{64})\b")


@dataclass(slots=True)
class BaoCaoDon:
    thu: bool = True                      # True = chỉ đề xuất, chưa xoá
    blob_tong: int = 0
    blob_co_tham_chieu: int = 0
    blob_se_xoa: list[str] = field(default_factory=list)
    byte_thu_hoi: int = 0
    transcript_se_xoa: list[str] = field(default_factory=list)
    checkpoint_se_xoa: list[str] = field(default_factory=list)
    giu_lai_vi: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"thu": self.thu, "blob_tong": self.blob_tong,
                "blob_co_tham_chieu": self.blob_co_tham_chieu,
                "so_blob_se_xoa": len(self.blob_se_xoa),
                "byte_thu_hoi": self.byte_thu_hoi,
                "transcript_se_xoa": self.transcript_se_xoa,
                "checkpoint_se_xoa": self.checkpoint_se_xoa,
                "giu_lai_vi": self.giu_lai_vi}

    def dong_vi(self) -> str:
        if self.thu:
            return (f"Có thể thu hồi {self.byte_thu_hoi / 1e6:.1f} MB: "
                    f"{len(self.blob_se_xoa)}/{self.blob_tong} blob không ai trỏ tới và "
                    f"quá {GIU['blob_ngay']} ngày. Chưa xoá gì — anh duyệt thì tôi làm.")
        return (f"Đã thu hồi {self.byte_thu_hoi / 1e6:.1f} MB "
                f"({len(self.blob_se_xoa)} blob).")


def _tham_chieu(paths: Any, ledger: Any = None) -> set[str]:
    """Mọi hash đang được trỏ tới, từ MỌI nơi có thể trỏ.

    Quét thô bằng regex trên văn bản JSON thay vì đi theo lược đồ từng loại: bỏ sót một
    chỗ trỏ nghĩa là xoá một bằng chứng người dùng cần, nên ở đây thà quét rộng tay còn
    hơn quét đúng kiểu. Giữ thừa một blob tốn vài KB; xoá thiếu một blob làm một
    snapshot không khôi phục được.
    """
    ra: set[str] = set()
    for ten in ("changesets.jsonl", "ledger.jsonl", "snapshots.jsonl"):
        p = Path(paths.state_dir) / ten
        if p.exists():
            ra |= set(_HASH.findall(p.read_text("utf-8", errors="replace")))
    d_snap = Path(paths.state_dir) / "snapshots"
    if d_snap.exists():
        for p in d_snap.rglob("*.json"):
            ra |= set(_HASH.findall(p.read_text("utf-8", errors="replace")))
    d_ses = Path(paths.state_dir) / "sessions"
    if d_ses.exists():
        for p in d_ses.rglob("*.jsonl"):
            ra |= set(_HASH.findall(p.read_text("utf-8", errors="replace")))
    return ra


def _tuoi_ngay(p: Path) -> float:
    return (time.time() - p.stat().st_mtime) / 86400.0


def gc(paths: Any, *, thu: bool = True, ledger: Any = None) -> BaoCaoDon:
    """Dọn blob không ai trỏ tới và quá hạn. `thu=True` chỉ đề xuất."""
    bc = BaoCaoDon(thu=thu)
    goc = Path(paths.blobs)
    if not goc.exists():
        return bc

    duoc_tro = _tham_chieu(paths, ledger)
    for p in goc.rglob("*"):
        if not p.is_file():
            continue
        bc.blob_tong += 1
        if p.name in duoc_tro:
            bc.blob_co_tham_chieu += 1
            continue
        tuoi = _tuoi_ngay(p)
        if tuoi < GIU["blob_ngay"]:
            bc.giu_lai_vi.append(
                f"{p.name[:12]}… chưa ai trỏ tới nhưng mới {tuoi:.0f} ngày "
                f"(giữ tới {GIU['blob_ngay']} ngày)")
            continue
        bc.blob_se_xoa.append(p.name)
        bc.byte_thu_hoi += p.stat().st_size
        if not thu:
            p.unlink(missing_ok=True)

    # Checkpoint trước nén: giữ 24 giờ (cửa sổ huỷ nén).
    d_ses = Path(paths.state_dir) / "sessions"
    if d_ses.exists():
        han = datetime.now(timezone.utc) - timedelta(hours=GIU["checkpoint_nen_gio"])
        for p in d_ses.rglob("precompact*.jsonl"):
            if datetime.fromtimestamp(p.stat().st_mtime, timezone.utc) < han:
                bc.checkpoint_se_xoa.append(str(p.name))
                if not thu:
                    p.unlink(missing_ok=True)

    # Transcript quá 90 ngày: chuyển thành bản tóm tắt cuối rồi xoá messages.
    if d_ses.exists():
        for d in d_ses.iterdir():
            if not d.is_dir():
                continue
            t = d / "transcript.jsonl"
            if t.exists() and _tuoi_ngay(t) > GIU["transcript_ngay"]:
                bc.transcript_se_xoa.append(d.name)
    return bc


# =========================================================================== đo lường §13
@dataclass(slots=True)
class DoLuong:
    """Sáu chỉ số của §13. Tính từ SỔ CÁI, không từ biến đếm trong bộ nhớ.

    Lý do: một biến đếm chỉ đúng khi tiến trình còn sống, và câu hỏi "bộ nhớ có tốt lên
    không" là câu hỏi qua nhiều phiên. Sổ cái là thứ duy nhất sống lâu hơn tiến trình.
    """

    so_luot: int = 0
    token_trung_vi: float = 0.0
    ty_le_cua_so: float = 0.0
    so_lan_c2: int = 0
    luot_moi_lan_c2: float = 0.0
    ty_le_kiem_dat_lan_dau: float = 0.0
    so_lan_khong_kiem_duoc: int = 0
    chi_phi_nen_tren_phien: float = 0.0
    muc_tieu: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "so_luot": self.so_luot,
            "token_trung_vi": round(self.token_trung_vi),
            "ty_le_cua_so": round(self.ty_le_cua_so, 3),
            "so_lan_c2": self.so_lan_c2,
            "luot_moi_lan_c2": round(self.luot_moi_lan_c2, 1),
            "ty_le_kiem_dat_lan_dau": round(self.ty_le_kiem_dat_lan_dau, 3),
            "so_lan_khong_kiem_duoc": self.so_lan_khong_kiem_duoc,
            "chi_phi_nen_tren_phien": round(self.chi_phi_nen_tren_phien, 4),
            "muc_tieu": dict(self.muc_tieu),
        }

    def dat_khong(self) -> list[dict[str, Any]]:
        """So với mục tiêu §13. Chưa đủ dữ liệu thì nói CHƯA ĐỦ, không nói đạt."""
        ra: list[dict[str, Any]] = []

        def them(ten: str, gia: float, dat: bool, muc: str, du: bool) -> None:
            ra.append({"chi_so": ten, "gia_tri": gia, "muc_tieu": muc,
                       "ket_qua": ("chưa đủ dữ liệu" if not du
                                   else "đạt" if dat else "CHƯA đạt")})

        them("Token vào mỗi lượt / cửa sổ", self.ty_le_cua_so,
             self.ty_le_cua_so <= 0.45, "≤ 45 %", self.so_luot >= 10)
        them("Số lượt giữa hai lần C2", self.luot_moi_lan_c2,
             self.luot_moi_lan_c2 >= 25, "≥ 25 lượt/lần", self.so_lan_c2 >= 1)
        them("Kiểm sau nén đạt lần đầu", self.ty_le_kiem_dat_lan_dau,
             self.ty_le_kiem_dat_lan_dau >= 0.95, "≥ 95 %", self.so_lan_c2 >= 3)
        them("Chi phí nén / chi phí phiên", self.chi_phi_nen_tren_phien,
             self.chi_phi_nen_tren_phien <= 0.05, "≤ 5 %", self.so_lan_c2 >= 1)
        return ra


def do_luong(ledger: Any, *, cua_so: int = 1_000_000) -> DoLuong:
    """§13 — đọc sổ cái, tính sáu chỉ số."""
    d = DoLuong(muc_tieu={
        "token_moi_luot": "≤ 45 % cửa sổ",
        "tan_suat_c2": "≤ 1 lần / 25 lượt",
        "kiem_dat_lan_dau": "≥ 95 %",
        "chi_phi_nen": "≤ 5 % chi phí phiên",
    })
    token_luot: list[int] = []
    tong_token = 0
    token_nen = 0
    lan_c2 = 0
    dat_lan_dau = 0

    for e in ledger.read():
        if e.kind == "turn.end":
            d.so_luot += 1
            t = ((e.data.get("cost") or {}).get("tokens") or {})
            n = int(t.get("vao", 0) or t.get("in", 0) or 0)
            if n:
                token_luot.append(n)
            tong_token += n + int(t.get("ra", 0) or t.get("out", 0) or 0)
        elif e.kind == "llm_call" and str(e.data.get("muc_dich", "")).startswith("nen"):
            token_nen += int(e.data.get("tokens_in", 0)) + int(e.data.get("tokens_out", 0))
        elif e.kind == "compact":
            buoc = e.data.get("buoc")
            if buoc == "ok":
                lan_c2 += 1
                if int(e.data.get("lan", 1)) == 1 and "/" in str(e.data.get("diem", "")):
                    dat_lan_dau += 1
            elif buoc == "khong_kiem_duoc":
                d.so_lan_khong_kiem_duoc += 1

    d.so_lan_c2 = lan_c2
    if token_luot:
        sx = sorted(token_luot)
        d.token_trung_vi = float(sx[len(sx) // 2])
        d.ty_le_cua_so = d.token_trung_vi / max(1, cua_so)
    if lan_c2:
        d.luot_moi_lan_c2 = d.so_luot / lan_c2
        d.ty_le_kiem_dat_lan_dau = dat_lan_dau / lan_c2
    if tong_token:
        d.chi_phi_nen_tren_phien = token_nen / tong_token
    return d
