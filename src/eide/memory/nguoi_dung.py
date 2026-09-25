# -*- coding: utf-8 -*-
"""M3 — bộ nhớ người dùng, xuyên dự án. EIDE-MEM-42 §8.

`~/.eide/memory.md`. Khác M2 (bộ nhớ dự án) ở một điểm quyết định mọi thứ còn lại: **nó
theo NGƯỜI, không theo việc**. Nên ranh giới phải chặt hơn hẳn.

Ba ràng buộc, mỗi cái chặn một kiểu hỏng khác nhau:

1. **Danh sách trắng chủ đề.** Chỉ sáu nhóm được nhớ. Không có danh sách trắng thì
   "ghi nhớ sở thích người dùng" trượt dần thành ghi nhớ *về* người dùng — trình độ,
   tính cách, phỏng đoán — thứ §8 cấm thẳng và thứ không ai muốn máy mình lưu.
2. **Không bao giờ nhớ bí mật.** Khoá, mật khẩu, token đi vào keychain của hệ điều
   hành, không vào một tệp markdown. Có một bộ quét chặn trước khi ghi.
3. **Tác tử không tự ghi.** Nó chỉ ĐỀ XUẤT, và chỉ khi người lặp lại một sở thích ≥ 2
   lần hoặc nói thẳng "nhớ là…". Người bấm đồng ý thì mới ghi. Một bộ nhớ tự lớn lên
   là một bộ nhớ không ai kiểm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

# §8 "được nhớ" — sáu nhóm, không hơn.
CHU_DE = {
    "tu_chu": "Mức tự chủ và các 'tin' đã cấp cho từng công cụ/nguồn",
    "trinh_bay": "Thói quen trình bày: ngắn/đủ/kỹ, diff nguyên văn, tab mặc định",
    "toolchain": "Đường toolchain trên máy này",
    "phan_cung": "Chip và bo hay dùng",
    "nguon_tin": "Nguồn tài liệu tin cậy",
    "ngon_ngu": "Ngôn ngữ trao đổi",
}

# §8 "không bao giờ nhớ". Quét TRƯỚC khi ghi, không phải nhắc trong tài liệu.
_BI_MAT = [
    (re.compile(r"\b[A-Za-z0-9_\-]{20,}\b"), "chuỗi dài giống khoá/token"),
    (re.compile(r"(?i)\b(pass|password|mật khẩu|passwd|secret|token|api[_ -]?key)\b"),
     "nhắc tới mật khẩu hoặc khoá"),
    (re.compile(r"(?i)\b(sk|ghp|gho|AIza)[-_A-Za-z0-9]{10,}"), "khoá API"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"), "khoá riêng"),
]

# Phỏng đoán VỀ người — §8 cấm. Đây là ranh giới dễ trượt nhất nên đặt mẫu cụ thể.
_PHONG_DOAN = re.compile(
    r"(?i)\b(có vẻ|hình như|chắc là|dường như|người dùng (này )?(không|chưa) (biết|rành|"
    r"hiểu)|trình độ|mới học|nghiệp dư|thiếu kinh nghiệm|lười|cẩu thả)\b")

TIEU_DE = """# Bộ nhớ người dùng — EIDE

Tệp này theo **anh**, không theo dự án nào. EIDE đọc nó ở mọi dự án.
Anh xoá được bất kỳ dòng nào, hoặc xoá cả tệp.

"""


@dataclass(slots=True)
class KetQuaGhi:
    ok: bool
    ly_do: str = ""
    dong: str = ""


class BoNhoNguoiDung:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path.home() / ".eide" / "memory.md"

    # ------------------------------------------------------------------ kiểm
    @staticmethod
    def kiem(chu_de: str, noi_dung: str) -> KetQuaGhi:
        """Được phép ghi không? Trả lý do đọc được nếu không."""
        if chu_de not in CHU_DE:
            return KetQuaGhi(False, (
                f"“{chu_de}” không nằm trong danh sách chủ đề được nhớ. "
                f"Chỉ sáu nhóm: {', '.join(CHU_DE)}. Nội dung dự án thuộc EIDE.md, "
                "không thuộc bộ nhớ người dùng."))
        for mau, vi_sao in _BI_MAT:
            if mau.search(noi_dung):
                return KetQuaGhi(False, (
                    f"Không ghi: {vi_sao}. Khoá và mật khẩu thuộc keychain của hệ điều "
                    "hành, không thuộc một tệp markdown."))
        if _PHONG_DOAN.search(noi_dung):
            return KetQuaGhi(False, (
                "Không ghi: câu này là một phỏng đoán VỀ người dùng. §8 chỉ cho nhớ "
                "sở thích họ nói ra, không cho nhớ nhận xét về họ."))
        return KetQuaGhi(True)

    # ------------------------------------------------------------------ đọc/ghi
    def doc(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        ra: list[dict[str, str]] = []
        chu_de = ""
        for d in self.path.read_text("utf-8").splitlines():
            m = re.match(r"^##\s+(\w+)", d)
            if m:
                chu_de = m.group(1)
            elif d.strip().startswith("- ") and chu_de:
                ra.append({"chu_de": chu_de, "dong": d.strip()[2:]})
        return ra

    def ghi(self, chu_de: str, noi_dung: str) -> KetQuaGhi:
        k = self.kiem(chu_de, noi_dung)
        if not k.ok:
            return k
        self.path.parent.mkdir(parents=True, exist_ok=True)
        chu = self.path.read_text("utf-8") if self.path.exists() else TIEU_DE
        dong = f"- {noi_dung.strip()} _({date.today().isoformat()})_"
        if f"## {chu_de}" in chu:
            chu = chu.replace(f"## {chu_de}\n", f"## {chu_de}\n{dong}\n", 1)
        else:
            chu = chu.rstrip() + f"\n\n## {chu_de}\n{dong}\n"
        self.path.write_text(chu, "utf-8")
        return KetQuaGhi(True, dong=dong)

    def quen(self, chua: str) -> str | None:
        """Xoá một dòng. Trả dòng đã xoá."""
        if not self.path.exists():
            return None
        ds = self.path.read_text("utf-8").splitlines()
        for i, d in enumerate(ds):
            if d.strip().startswith("- ") and chua.strip().lower() in d.lower():
                ds.pop(i)
                self.path.write_text("\n".join(ds) + "\n", "utf-8")
                return d.strip()[2:]
        return None

    def xoa_het(self) -> bool:
        if self.path.exists():
            self.path.unlink()
            return True
        return False

    # ------------------------------------------------------------------ vào ngữ cảnh
    def khoi_ngu_canh(self, tran_token: int = 300) -> str:
        """§10 — M3 vào khối hiến pháp mở rộng, trần 300 token."""
        ds = self.doc()
        if not ds:
            return ""
        L = ["<nguoi_dung>", "Sở thích và thiết lập của người này (dùng chung mọi dự án):"]
        for m in ds:
            L.append(f"- [{m['chu_de']}] {m['dong']}")
        L.append("</nguoi_dung>")
        out = "\n".join(L)
        cap = int(tran_token * 3.0)
        return out if len(out) <= cap else out[:cap] + "\n…\n</nguoi_dung>"


def nen_de_xuat(loi_nguoi: list[str], chu_de: str, mau: str) -> bool:
    """§8 — chỉ đề xuất khi người LẶP LẠI ≥ 2 lần, hoặc nói thẳng "nhớ là…".

    Ngưỡng hai lần không phải con số tuỳ tiện: một lần là một yêu cầu cho việc đang làm,
    hai lần mới là một thói quen. Đề xuất ngay lần đầu biến mọi câu nói thành một mục
    trong bộ nhớ vĩnh viễn.
    """
    chu = " ".join(loi_nguoi).lower()
    if re.search(r"(?i)\b(nhớ là|nhớ giúp|từ nay|lần sau (cứ|thì)|luôn luôn)\b", chu):
        return True
    return len(re.findall(re.escape(mau.lower()), chu)) >= 2
