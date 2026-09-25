# -*- coding: utf-8 -*-
"""EIDE.md — bộ nhớ dài hạn của dự án, người và tác tử cùng sửa.

EIDE-MDD-40 §B2, §B6, §E4 bước 5.

    "Gốc dự án: mục tiêu, chip, quyết định, giả định, quy ước, 'đừng', §'Người vừa sửa'"
    "Người và tác tử cùng sửa; tác tử sửa qua fs.edit → changeset"

Đây là tệp Markdown thường, để người mở ra đọc và sửa bằng bất cứ thứ gì. Không dùng
định dạng riêng: một bộ nhớ mà người không đọc được thì không kiểm được, và N8 nói mọi
thứ tác tử làm ra phải có dạng người hiểu được.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

# Thứ tự mục là cố định — mô hình đọc theo thứ tự này mỗi lượt.
SECTIONS = ["Mục tiêu", "Chip & phần cứng", "Quyết định", "Giả định", "Quy ước",
            "Đừng", "Người vừa sửa"]

HUMAN_EDITS_SECTION = "Người vừa sửa"
MAX_HUMAN_EDIT_LINES = 10      # §E4 bước 5: "giữ ≤ 10 dòng gần nhất"

# MEM-42 §7.1 — trần 3 000 token trên CHÍNH TỆP, không chỉ lúc đưa vào ngữ cảnh.
#
# Bản trước chỉ cắt ở `render()`. Nghĩa là tệp thật vẫn phình vô hạn, mô hình nhận một
# bản cụt mà không ai biết, và người mở tệp ra thì thấy một thứ khác hẳn. Cắt lúc đọc
# là giấu vấn đề; trần trên tệp là nói ra vấn đề.
TRAN_TOKEN = 3000
KY_TU_MOI_TOKEN = 3.0

# §7.1 "ai được ghi mục nào". Mục "Đừng" là ranh giới NGƯỜI đặt — tác tử tự thêm vào đó
# là tự đặt ra một luật rồi tự tuân theo, đúng thứ N7 cấm.
CHI_NGUOI_GHI = {"Đừng"}


def _uoc_token(s: str) -> int:
    return int(len(s) / KY_TU_MOI_TOKEN)

TEMPLATE = """# EIDE.md — {name}

Tệp này là bộ nhớ dài hạn của dự án. Cả anh và tác tử đều sửa được. Tác tử đọc nó
mỗi lượt, nên những gì viết ở đây có hiệu lực cho mọi việc về sau.

## Mục tiêu

_(chưa có — tác tử sẽ ghi vào đây khi đặc tả yêu cầu được chốt)_

## Chip & phần cứng

_(chưa ghim hộ chiếu chip nào)_

## Quyết định

_(chưa có ADR nào)_

## Giả định

_(chưa có giả định nào đang dùng)_

## Quy ước

- Ngôn ngữ trao đổi: tiếng Việt. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh, giải thích khi lần đầu xuất hiện.
- Mọi con số dùng để quyết định phải truy vết được tới tài liệu (N1).

## Đừng

- Không bật khoá đọc (RDP) hay ghi eFuse khi chưa có một snapshot đánh dấu release.

## Người vừa sửa

_(chưa có thay đổi nào của anh chờ tác tử nhắc tới)_
"""


@dataclass(slots=True)
class EideMd:
    path: Path
    sections: dict[str, str] = field(default_factory=dict)
    preamble: str = ""

    # ------------------------------------------------------------------ đọc/ghi
    @classmethod
    def load(cls, path: str | Path, *, create_name: str | None = None) -> "EideMd":
        p = Path(path)
        if not p.exists():
            if create_name is None:
                return cls(path=p)
            p.write_text(TEMPLATE.format(name=create_name), "utf-8")
        obj = cls(path=p)
        obj._parse(p.read_text("utf-8") if p.exists() else "")
        return obj

    def _parse(self, text: str) -> None:
        self.sections = {}
        cur: str | None = None
        buf: list[str] = []
        pre: list[str] = []
        for line in text.splitlines():
            m = re.match(r"^##\s+(.+?)\s*$", line)
            if m:
                if cur is not None:
                    self.sections[cur] = "\n".join(buf).strip()
                else:
                    pre = buf
                cur, buf = m.group(1), []
            else:
                buf.append(line)
        if cur is not None:
            self.sections[cur] = "\n".join(buf).strip()
        else:
            pre = buf
        self.preamble = "\n".join(pre).strip()

    def save(self) -> None:
        parts = [self.preamble] if self.preamble else []
        order = [s for s in SECTIONS if s in self.sections]
        order += [s for s in self.sections if s not in SECTIONS]
        for s in order:
            parts.append(f"## {s}\n\n{self.sections[s]}".rstrip())
        self.path.write_text("\n\n".join(parts).rstrip() + "\n", "utf-8")

    # ------------------------------------------------------------------ dùng
    def get(self, section: str) -> str:
        return self.sections.get(section, "")

    def set(self, section: str, body: str) -> None:
        self.sections[section] = body.strip()

    def append_line(self, section: str, line: str, *, boi: str | None = None) -> None:
        """Thêm một dòng vào mục. `boi` là nguồn gốc: `run-43` hoặc `h-0940`.

        §7.1 "nguồn gốc dòng": mỗi dòng nói được **ai ghi**. Không có nó thì sáu tháng
        sau không ai phân biệt được điều mình tự quyết với điều máy suy ra — và đó là
        lúc người ta ngừng tin cả tệp.
        """
        if boi and not line.rstrip().endswith("]"):
            line = f"{line.rstrip()} [{boi}]"
        cur = self.sections.get(section, "")
        if cur.startswith("_(") and cur.endswith(")_"):
            cur = ""  # thay chỗ giữ chỗ bằng nội dung thật
        self.sections[section] = (cur + "\n" + line).strip()

    def xoa_dong(self, section: str, chua: str) -> str | None:
        """Xoá dòng đầu tiên trong mục có chứa `chua`. Trả dòng đã xoá, hoặc None."""
        ds = self.sections.get(section, "").splitlines()
        for i, d in enumerate(ds):
            if chua.strip() and chua.strip().lower() in d.lower():
                ds.pop(i)
                self.sections[section] = "\n".join(ds).strip()
                return d
        return None

    # ------------------------------------------------------------------ trần và lược
    @property
    def so_token(self) -> int:
        return _uoc_token(self.path.read_text("utf-8") if self.path.exists() else "")

    @property
    def qua_tran(self) -> bool:
        return self.so_token > TRAN_TOKEN

    def de_xuat_luoc(self) -> list[dict[str, Any]]:
        """§7.1 "Lược" — ĐỀ XUẤT, không tự xoá (P5).

        Tự xoá cái cũ là cách nhanh nhất để mất một quyết định mà không ai nhớ đã mất.
        Nên hàm này chỉ trả về danh sách, và người duyệt.
        """
        ra: list[dict[str, Any]] = []
        for muc, than in self.sections.items():
            ds = [d for d in than.splitlines() if d.strip().startswith("- ")]
            if muc == HUMAN_EDITS_SECTION and len(ds) > MAX_HUMAN_EDIT_LINES:
                ra.append({"muc": muc, "so_dong": len(ds) - MAX_HUMAN_EDIT_LINES,
                           "vi_sao": ("dòng đã được tác tử nhắc tới và cũ hơn 10 thay "
                                      "đổi — chuyển sang sổ cái, tra lại được bằng "
                                      "ledger.query"),
                           "dong": ds[:-MAX_HUMAN_EDIT_LINES]})
            elif muc == "Quyết định" and len(ds) > 15:
                ra.append({"muc": muc, "so_dong": len(ds) - 15,
                           "vi_sao": ("§7.1 giữ 15 ADR mới nhất trong tệp; các ADR cũ "
                                      "vẫn nằm đủ trong kho, tra bằng store.list"),
                           "dong": ds[:-15]})
            elif muc == "Ghi chú tự do" and len(ds) > 20:
                ra.append({"muc": muc, "so_dong": len(ds) - 20,
                           "vi_sao": "ghi chú tự do giữ tối đa 20 dòng",
                           "dong": ds[:-20]})
        if self.qua_tran and not ra:
            dai = max(self.sections.items(), key=lambda kv: len(kv[1]), default=("", ""))
            ra.append({"muc": dai[0], "so_dong": 0,
                       "vi_sao": (f"Tệp {self.so_token} token, vượt trần {TRAN_TOKEN}. "
                                  f"Mục dài nhất là “{dai[0]}” — gộp hoặc rút gọn nó."),
                       "dong": []})
        return ra

    def duoc_ghi(self, section: str, boi_ai: str) -> tuple[bool, str]:
        """§7.1 "ai được ghi mục nào". `boi_ai` là "nguoi" hoặc "tac_tu"."""
        if section in CHI_NGUOI_GHI and boi_ai != "nguoi":
            return False, (
                f"Mục “{section}” là ranh giới do người đặt — chỉ họ thêm hoặc bỏ được. "
                "Bạn có thể ĐỀ XUẤT qua một thẻ để họ duyệt, nhưng không tự ghi.")
        return True, ""

    def note_human_edit(self, *, artefact: str, summary: str, why: str | None,
                        when: str | None = None) -> None:
        """§E4 bước 5(a): ghi lại thay đổi của người, có ngày, hiện vật, tóm tắt, vì sao."""
        d = when or date.today().isoformat()
        line = f"- {d} · **{artefact}** — {summary}" + (f" · vì: {why}" if why else "")
        self.append_line(HUMAN_EDITS_SECTION, line)
        self._trim_human_edits()

    def _trim_human_edits(self) -> None:
        body = self.sections.get(HUMAN_EDITS_SECTION, "")
        lines = [l for l in body.splitlines() if l.strip().startswith("- ")]
        if len(lines) > MAX_HUMAN_EDIT_LINES:
            lines = lines[-MAX_HUMAN_EDIT_LINES:]
        self.sections[HUMAN_EDITS_SECTION] = "\n".join(lines)

    def dont_list(self) -> list[str]:
        """§"Đừng" — cái người đã bác bỏ. Tác tử không được đề xuất lại (§E4.1)."""
        return [l.strip("- ").strip() for l in self.get("Đừng").splitlines()
                if l.strip().startswith("- ")]

    # ------------------------------------------------------------------ vào ngữ cảnh
    def render(self, budget_chars: int = 12000) -> str:
        """Dạng đưa vào ngữ cảnh mỗi lượt (§B2, ngân sách ≤ 3 k token ≈ 12 k ký tự).

        Cắt từ dưới lên: các mục cuối (Quy ước, Người vừa sửa) quan trọng hơn phần
        mô tả dài ở đầu, nên giữ nguyên mục, chỉ cắt thân mục dài nhất.
        """
        parts = [f"## {s}\n{self.sections[s]}" for s in SECTIONS if self.sections.get(s)]
        parts += [f"## {s}\n{b}" for s, b in self.sections.items()
                  if s not in SECTIONS and b]
        text = "\n\n".join(parts)
        if len(text) <= budget_chars:
            return text
        keep = budget_chars - 200
        return text[:keep] + "\n\n_(EIDE.md bị cắt bớt vì quá dài — mở tệp để xem đầy đủ)_"

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "sections": dict(self.sections)}
