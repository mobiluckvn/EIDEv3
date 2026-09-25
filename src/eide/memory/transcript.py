# -*- coding: utf-8 -*-
"""M1 — transcript phiên trên đĩa. EIDE-MEM-42 §7.2, §7.3, §12.

Trước bước này, `Agent.messages` là một `list` Python và chỉ có thế: lõi chết giữa lượt
là mất sạch ngữ cảnh mô hình; mở lại dự án hôm sau thì tác tử không biết hôm qua đã bàn
gì. Sổ cái vẫn đủ để dựng lại **dòng hội thoại cho người**, nhưng nó không phải là thứ
mô hình đọc.

Ba tính chất, mỗi cái sửa một cách hỏng khác nhau:

1. **Write-ahead + fsync.** Mỗi message xuống đĩa TRƯỚC khi được xử lý tiếp. Lõi chết
   giữa chừng thì dòng cuối hợp lệ vẫn còn. Không fsync thì "đã ghi" chỉ là đã nằm
   trong bộ đệm của hệ điều hành — đúng thứ biến mất khi máy mất điện.
2. **Đổi tên atomic khi nén.** Ghi tệp mới rồi `rename` đè lên tệp cũ. `rename` trong
   cùng một hệ tệp là thao tác nguyên tử, nên không có khoảnh khắc nào transcript ở
   trạng thái "đã cắt nhưng chưa có bản thay thế" (§12).
3. **Công cụ có tác dụng phụ chạy dở thì KHÔNG chạy lại.** Nếu `tool_use` đã ghi mà
   `tool_result` chưa, ta biết công cụ *có thể* đã chạy. Với `fs.read` thì chạy lại vô
   hại; với `target.flash` thì chạy lại là nạp chip hai lần. Nên phục hồi đánh dấu
   "không rõ kết quả" và bắt hỏi người (ca MEM14).
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Công cụ ĐỔI trạng thái bên ngoài lõi. Chạy lại một cái trong đây sau sự cố là làm
# thêm một lần nữa, không phải làm lại. Danh sách này nghiêng về phía an toàn: thà
# hỏi thừa một lần còn hơn nạp chip hai lần.
CO_TAC_DUNG_PHU = {
    "fs.write", "fs.edit", "bash", "tool.install",
    "target.flash", "target.dangerous", "target.reset",
    "build.compile", "sim.run", "doc.search_web",
}


@dataclass(slots=True)
class BaoCaoPhucHoi:
    """Kết quả đọc lại một phiên dở. Dùng để dựng khối nhắc cho mô hình."""

    session_id: str = ""
    so_message: int = 0
    dong_hong: int = 0                      # dòng JSONL đọc không được
    goi_dang_do: list[dict[str, Any]] = field(default_factory=list)

    @property
    def can_hoi_nguoi(self) -> bool:
        return any(g["co_tac_dung_phu"] for g in self.goi_dang_do)

    def nhac_vi(self) -> str:
        if not self.goi_dang_do:
            return ""
        L = ["<system-reminder>",
             "Phiên trước dừng giữa chừng. Những lời gọi công cụ sau đã BẮT ĐẦU nhưng "
             "không có kết quả trong sổ:"]
        for g in self.goi_dang_do:
            if g["co_tac_dung_phu"]:
                L.append(f"- {g['tool']} — KHÔNG RÕ đã chạy xong chưa, và nó đổi thứ "
                         "bên ngoài. ĐỪNG chạy lại; hỏi người dùng kiểm tra rồi cho biết.")
            else:
                L.append(f"- {g['tool']} — chạy lại được (chỉ đọc).")
        L.append("</system-reminder>")
        return "\n".join(L)


class Transcript:
    """Một tệp JSONL, một message một dòng, chỉ ghi thêm cho tới khi nén."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ ghi
    def ghi(self, m: dict[str, Any]) -> None:
        """Write-ahead: xuống đĩa và fsync TRƯỚC khi lõi đi tiếp."""
        dong = json.dumps(m, ensure_ascii=False, default=str) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(dong)
            f.flush()
            os.fsync(f.fileno())

    def thay_toan_bo(self, messages: list[dict[str, Any]]) -> None:
        """Thay cả tệp bằng danh sách mới — dùng sau khi nén (§12 "nén là giao dịch").

        Ghi ra tệp tạm, fsync, rồi `rename`. Hỏng ở bất kỳ bước nào thì bản cũ còn
        nguyên; không có trạng thái nửa vời.
        """
        tam = self.path.with_suffix(".tmp")
        with self._lock:
            with tam.open("w", encoding="utf-8") as f:
                for m in messages:
                    f.write(json.dumps(m, ensure_ascii=False, default=str) + "\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tam, self.path)

    # ------------------------------------------------------------------ đọc
    def doc(self) -> tuple[list[dict[str, Any]], int]:
        """Đọc lại. Trả (messages, số dòng hỏng).

        Dòng cuối có thể cụt nếu lõi chết đúng lúc đang ghi — bỏ nó và ĐẾM, không im
        lặng. Một transcript thiếu một dòng mà không ai biết là một transcript nói dối.
        """
        if not self.path.exists():
            return [], 0
        ms: list[dict[str, Any]] = []
        hong = 0
        for dong in self.path.read_text("utf-8", errors="replace").splitlines():
            if not dong.strip():
                continue
            try:
                ms.append(json.loads(dong))
            except ValueError:
                hong += 1
        return ms, hong


class KhoPhien:
    """`.eide/sessions/` — mỗi phiên một thư mục (§7.3)."""

    def __init__(self, goc: str | Path):
        self.goc = Path(goc)
        self.goc.mkdir(parents=True, exist_ok=True)

    def thu_muc(self, sid: str) -> Path:
        d = self.goc / sid
        d.mkdir(parents=True, exist_ok=True)
        return d

    def transcript(self, sid: str) -> Transcript:
        return Transcript(self.thu_muc(sid) / "transcript.jsonl")

    def danh_sach(self) -> list[str]:
        return sorted(p.name for p in self.goc.iterdir() if p.is_dir())

    def gan_nhat(self, tru: str | None = None) -> str | None:
        ds = [s for s in self.danh_sach() if s != tru]
        return ds[-1] if ds else None

    def danh_dau_ket_thuc(self, sid: str) -> None:
        (self.thu_muc(sid) / "ket-thuc").write_text("", "utf-8")

    def ket_thuc_sach(self, sid: str) -> bool:
        return (self.thu_muc(sid) / "ket-thuc").exists()


def phuc_hoi(ts: Transcript, sid: str = "") -> BaoCaoPhucHoi:
    """Đọc một phiên dở và chỉ ra lời gọi công cụ nào không rõ kết quả (MEM14)."""
    ms, hong = ts.doc()
    bc = BaoCaoPhucHoi(session_id=sid, so_message=len(ms), dong_hong=hong)

    da_co_kq = {m.get("tool_call_id") for m in ms if m.get("role") == "tool"}
    for m in ms:
        if m.get("role") != "model":
            continue
        for c in m.get("tool_calls") or []:
            if c.get("id") in da_co_kq:
                continue
            ten = c.get("tool", "")
            bc.goi_dang_do.append({"tool": ten, "call_id": c.get("id"),
                                   "co_tac_dung_phu": ten in CO_TAC_DUNG_PHU})
    return bc
