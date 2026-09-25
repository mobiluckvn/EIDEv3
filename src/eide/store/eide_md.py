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

    def append_line(self, section: str, line: str) -> None:
        cur = self.sections.get(section, "")
        if cur.startswith("_(") and cur.endswith(")_"):
            cur = ""  # thay chỗ giữ chỗ bằng nội dung thật
        self.sections[section] = (cur + "\n" + line).strip()

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
