# -*- coding: utf-8 -*-
"""Lắp ngữ cảnh mỗi lượt — EIDE-MDD-40 §B2.

Bảy khối, mỗi khối một nguồn và một ngân sách:

| Khối            | Nguồn                                          | Ngân sách |
|-----------------|------------------------------------------------|-----------|
| Hiến pháp       | PRS-16 v3 (tệp cố định)                        | ~2 k, cache |
| EIDE.md         | Gốc dự án                                      | ≤ 3 k |
| `<inventory>`   | Dựng bằng mã từ kho (N3)                       | ≤ 800 |
| `<facts>`       | fact.query theo thực thể nhắc trong 3 lượt gần | ≤ 2 k |
| `<human_edits>` | Changeset author=human chưa được nhắc (N9)     | ≤ 1 k |
| `<pending>`     | Thẻ chờ, run dừng, giả định, plan đã duyệt     | ≤ 300 |
| `<skills-hint>` | Skill khớp từ khoá                             | ≤ 300 |

Hiến pháp đi vào `system_instruction` (ổn định, cache được). Sáu khối còn lại đổi mỗi
lượt nên đi vào lượt người dùng dưới dạng `<system-reminder>` — mô hình đọc chúng như
ngữ cảnh chứ không như lời người nói.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import ContextBudget

CONSTITUTION_PATH = Path(__file__).resolve().parent / "constitution.md"

# Tiếng Việt trên tokenizer của Gemini: xấp xỉ 1 token ≈ 3 ký tự. Dùng 3.0 cho an toàn
# (ước thấp hơn thực tế thì ta cắt sớm hơn cần, không bao giờ tràn).
CHARS_PER_TOKEN = 3.0


def approx_tokens(s: str) -> int:
    return int(len(s) / CHARS_PER_TOKEN)


def budget_chars(tokens: int) -> int:
    return int(tokens * CHARS_PER_TOKEN)


# --------------------------------------------------------------------------- thực thể
# Rút thực thể để biết nên nạp Fact nào. XÁC ĐỊNH, 0 token.
# Lưu ý phạm vi: việc này CHỈ dùng để chọn Fact đưa vào ngữ cảnh. Nó KHÔNG định tuyến,
# KHÔNG điền tham số cho tool, KHÔNG quyết định gì — kiến trúc v3 bỏ tầng phân loại ý
# định, và cái ở đây không được lén dựng lại tầng đó.
_CHIP = re.compile(
    r"\b("
    r"(?:ATmega|ATtiny|AT90)\w+"                       # AVR
    r"|STM32[A-Z]\d[A-Z0-9]*"                          # STM32
    r"|(?:ESP32|ESP8266)(?:-[A-Z0-9]+)*"               # Espressif
    r"|(?:nRF)\d{4,5}\w*"                              # Nordic
    r"|RP\d{4}"                                        # Raspberry Pi
    r"|(?:PIC|dsPIC)\d+\w*"                            # Microchip
    r"|MSP430\w*|CH32[A-Z]\d+\w*|GD32[A-Z]\d[A-Z0-9]*"
    r"|ENC28J60|W5500|LAN8720|CP210\d|CH340\w?|FT232\w*"
    r")\b", re.IGNORECASE)
_NET = re.compile(r"\b(?:net[:\s]+)([A-Z][A-Z0-9_+\-]{1,15})\b")
_PIN = re.compile(r"\b([UJQRCD]\d{1,3})\.(\w{1,6})\b")
_REQ = re.compile(r"\b((?:REQ|FR|NFR|UR|ADR|TC|UC)-[A-Z0-9\-]{2,})\b", re.IGNORECASE)


def mentioned_entities(texts: list[str]) -> list[str]:
    """Thực thể nhắc trong các lượt gần nhất, theo thứ tự xuất hiện, không trùng."""
    seen: list[str] = []

    def add(v: str) -> None:
        if v and v not in seen:
            seen.append(v)

    for t in texts:
        for m in _CHIP.finditer(t):
            add(f"chip:{m.group(1)}")
        for m in _NET.finditer(t):
            add(f"net:{m.group(1)}")
        for m in _PIN.finditer(t):
            add(f"pin:{m.group(1)}.{m.group(2)}")
        for m in _REQ.finditer(t):
            add(m.group(1).upper())
    return seen


# --------------------------------------------------------------------------- khối
@dataclass(slots=True)
class Assembled:
    system_instruction: str
    reminder: str
    blocks: dict[str, str] = field(default_factory=dict)
    tokens: dict[str, int] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(self.tokens.values())


def _fact_line(f: dict[str, Any]) -> str:
    val = f.get("value")
    if val is None and (f.get("vmin") or f.get("vmax")):
        val = f"{f.get('vmin', '?')}…{f.get('vmax', '?')}"
    unit = f" {f['unit']}" if f.get("unit") else ""
    cond = f" ({f['condition']})" if f.get("condition") else ""
    src = f.get("source") or {}
    if isinstance(src, str):
        import json
        try:
            src = json.loads(src)
        except ValueError:
            src = {}
    if src.get("page"):
        cite = f"{src.get('doc_id', 'tài liệu')} tr.{src['page']}"
    elif src.get("human_act_id"):
        cite = f"anh nói ({src['human_act_id']}), chưa có tài liệu"
    else:
        cite = "không rõ nguồn"
    return f"  {f['subject']} · {f['key']} = {val}{unit}{cond} · [{f['tier']}] {cite}"


def build_facts_block(store: Any, entities: list[str], budget_tokens: int) -> str:
    """§B2 `<facts>`: Fact theo thực thể nhắc trong 3 lượt gần nhất, kèm tầng + trích dẫn."""
    if not entities:
        return ""
    rows: list[str] = []
    for ent in entities:
        subject = ent if ":" in ent else None
        if subject is None:
            continue
        for f in store.query_facts(subject=subject.split(":", 1)[1], limit=20):
            rows.append(_fact_line(f))
    if not rows:
        ents = ", ".join(entities[:6])
        return (f"<facts>\nChưa có Fact nào cho: {ents}.\n"
                "Nghĩa là KHÔNG có con số nào về chúng truy vết được tới tài liệu. "
                "Đừng dùng số nhớ được để so sánh hay sinh mã — hãy nạp/tìm datasheet, "
                "hoặc hỏi người dùng (số họ cho sẽ thành Fact tầng NGƯỜI).\n</facts>")
    body = "\n".join(dict.fromkeys(rows))  # bỏ trùng, giữ thứ tự
    cap = budget_chars(budget_tokens) - 80
    if len(body) > cap:
        body = body[:cap] + "\n  …(còn nữa — gọi fact.query để xem đầy đủ)"
    return f"<facts>\n{body}\n</facts>"


def build_human_edits_block(changesets: list[dict[str, Any]], budget_tokens: int) -> str:
    """§B2 `<human_edits>` — N9. Đây là khối hook Stop sẽ kiểm xem tác tử đã nhắc chưa."""
    if not changesets:
        return ""
    L = ["<human_edits>",
         "Người dùng vừa tự tay sửa những thứ sau. Bạn BẮT BUỘC phải nhắc tới chúng bằng lời",
         "trong lượt này, nêu hệ quả, và KHÔNG được ghi đè.", ""]
    for cs in changesets:
        ex = cs.get("explain") or {}
        L.append(f"- {cs.get('id')} · {', '.join(t.get('artefact_id', '?') for t in cs.get('touches', []))}")
        if ex.get("summary"):
            L.append(f"    thay đổi: {ex['summary']}")
        if cs.get("note"):
            L.append(f"    vì: {cs['note']}")
        if cs.get("stale_marked"):
            L.append(f"    kéo theo STALE: {', '.join(cs['stale_marked'])}")
    L.append("</human_edits>")
    out = "\n".join(L)
    cap = budget_chars(budget_tokens)
    return out if len(out) <= cap else out[:cap - 20] + "\n…\n</human_edits>"


def build_pending_block(*, cards: list[dict[str, Any]], stopped_run: dict[str, Any] | None,
                        assumptions: list[str], plan: dict[str, Any] | None,
                        budget_tokens: int) -> str:
    if not (cards or stopped_run or assumptions or plan):
        return ""
    L = ["<pending>"]
    for c in cards:
        L.append(f"- Thẻ đang chờ người trả lời: {c.get('gate') or c.get('type')} "
                 f"[{c.get('card_id')}] — {c.get('title', '')}")
    if stopped_run:
        L.append(f"- Lượt chạy dừng giữa chừng: {stopped_run.get('run_id')}")
    for a in assumptions:
        L.append(f"- Giả định đang dùng: {a}")
    if plan:
        # NÓI RÕ kế hoạch ấy cho việc gì.
        #
        # Bản đầu chỉ in "Kế hoạch đã duyệt: 7/8 bước xong" — một con số không nội dung. Đo
        # được trên phiên FreeRTOS: người dùng giao một việc MỚI (màn hình có nút, cảm ứng),
        # tác tử thấy dòng ấy, tưởng mình đang chạy dưới một kế hoạch đã duyệt cho việc mới,
        # và **không lập kế hoạch nào cả**. Cùng họ với lỗi "Lượt chạy dở: run-256": một mã
        # số không nội dung thì người đọc tự điền nội dung vào, và thường điền sai.
        b = plan.get("steps", []) or []
        done = sum(1 for s in b if s.get("xong") or s.get("done"))
        muc = str(plan.get("muc_tieu") or "").strip()
        L.append(f"- Kế hoạch đã duyệt: {done}/{len(b)} bước xong"
                 + (f" — CHO VIỆC: “{muc[:110]}”" if muc else ""))
        # LIỆT KÊ luôn các bước, gọn thôi. Không có chúng, tác tử không đọc được kế hoạch
        # của CHÍNH NÓ — đo được trên phiên FreeRTOS: nó tiêu 10 lời gọi đọc (5 ledger.query,
        # 3 fs.grep, 1 tool.search, 1 fs.glob) để dựng lại bảy bước mà vẫn chưa đủ, rồi phải
        # tự viết một công cụ `plan.get` chỉ để nhìn thấy thứ lẽ ra đã ở trước mặt.
        for i, buoc in enumerate(b, 1):
            dau = "x" if (buoc.get("xong") or buoc.get("done")) else " "
            L.append(f"  [{dau}] {i}. {str(buoc.get('viec') or '')[:72]}"
                     + (f" · {buoc.get('cong_cu')}" if buoc.get("cong_cu") else ""))
        # NÓI TÊN CÔNG CỤ ra. Đo được 30/09/2026 qua giao diện thật: tác tử có kế hoạch ba
        # bước ngay trước mặt, được bảo "làm tiếp", nó sửa tệp bằng `fs.edit` rồi dừng —
        # **không gọi `plan.step_done` lần nào**, nên kế hoạch đứng yên 0/3 và không có gì để
        # gộp. Danh sách bước cho nó biết PHẢI LÀM GÌ; nó vẫn cần biết ĐÁNH DẤU BẰNG CÁI GÌ.
        L.append("  Làm xong một bước thì `plan.step_done(so, hien_vat)` NGAY, đừng để dồn — "
                 "`hien_vat` phải trỏ tới tệp/hiện vật/changeset có thật.")
        if done == len(b) and b:
            L.append("  Hết bước rồi: `plan.merge(ra=…)` nếu việc này cần một sản phẩm hợp "
                     "nhất từ các phần.")
        if muc:
            L.append("  Việc người dùng vừa giao mà KHÁC việc trên thì kế hoạch này không "
                     "phủ nó: soạn kế hoạch mới (`plan.enter`), đừng chạy tiếp cái cũ.")
    L.append("</pending>")
    out = "\n".join(L)
    cap = budget_chars(budget_tokens)
    return out if len(out) <= cap else out[:cap - 15] + "\n…\n</pending>"


def build_skills_hint(skills: list[dict[str, Any]], text: str, budget_tokens: int) -> str:
    """§B2 `<skills-hint>`: chỉ GỢI Ý tên skill; mô hình tự nạp bằng skill.load."""
    if not skills:
        return ""
    low = text.lower()
    hits = [s for s in skills if any(k.lower() in low for k in s.get("keywords", []))]
    if not hits:
        return ""
    L = ["<skills-hint>", "Có thể hữu ích (gọi skill.load để đọc đầy đủ):"]
    L += [f"- {s['name']}: {s.get('summary', '')}" for s in hits[:5]]
    L.append("</skills-hint>")
    out = "\n".join(L)
    cap = budget_chars(budget_tokens)
    return out if len(out) <= cap else out[:cap - 18] + "\n</skills-hint>"


# --------------------------------------------------------------------------- lắp
def assemble(*, eide_md: Any, inventory_text: str, store: Any,
             recent_texts: list[str], human_edit_changesets: list[dict[str, Any]] | None = None,
             pending_cards: list[dict[str, Any]] | None = None,
             stopped_run: dict[str, Any] | None = None,
             assumptions: list[str] | None = None, plan: dict[str, Any] | None = None,
             skills: list[dict[str, Any]] | None = None,
             s0_annotations: list[str] | None = None,
             budget: ContextBudget | None = None) -> Assembled:
    b = budget or ContextBudget()

    system = CONSTITUTION_PATH.read_text("utf-8")

    ents = mentioned_entities(recent_texts[-3:])
    blocks: dict[str, str] = {
        "eide_md": eide_md.render(budget_chars(b.eide_md)) if eide_md else "",
        "inventory": inventory_text,
        "facts": build_facts_block(store, ents, b.facts),
        "human_edits": build_human_edits_block(human_edit_changesets or [], b.human_edits),
        "pending": build_pending_block(cards=pending_cards or [], stopped_run=stopped_run,
                                       assumptions=assumptions or [], plan=plan,
                                       budget_tokens=b.pending),
        "skills_hint": build_skills_hint(skills or [], " ".join(recent_texts[-1:]), b.skills_hint),
    }

    parts: list[str] = []
    if blocks["eide_md"]:
        parts.append("<eide_md>\nBộ nhớ dài hạn của dự án (anh và tác tử cùng sửa):\n\n"
                     + blocks["eide_md"] + "\n</eide_md>")
    for k in ("inventory", "facts", "human_edits", "pending", "skills_hint"):
        if blocks[k]:
            parts.append(blocks[k])
    if s0_annotations:
        parts.append("<s0_notes>\n" + "\n\n".join(s0_annotations) + "\n</s0_notes>")

    reminder = ("<system-reminder>\n" + "\n\n".join(parts) + "\n</system-reminder>") if parts else ""

    return Assembled(
        system_instruction=system,
        reminder=reminder,
        blocks=blocks,
        tokens={"constitution": approx_tokens(system),
                **{k: approx_tokens(v) for k, v in blocks.items() if v}},
        entities=ents,
    )
