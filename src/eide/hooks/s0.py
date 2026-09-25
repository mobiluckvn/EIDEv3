# -*- coding: utf-8 -*-
"""S0 — bộ luật chặn xác định ở hook UserPromptSubmit.

EIDE-MDD-40 §B4, nguyên tắc N5. Ca canh: TC007, 022, 035, 036, 068, 069, 014, 070.

Ba điều làm nên giá trị của lớp này, và cả ba đều phải giữ khi sửa:

1. **Đọc câu người gõ, không đọc ý định.** Nó chạy trước mọi phép hiểu. Vì vậy nó vẫn
   nổ kể cả khi phần còn lại của tác tử hiểu sai hoàn toàn câu đó.
2. **0 token.** Không gọi mô hình. Một cổng an toàn phụ thuộc vào mô hình thì hỏng
   đúng lúc mô hình hỏng.
3. **Xác định.** Cùng câu → cùng quyết định, 100 %, mãi mãi (§F3). Đo được, hồi quy được.

Đo 23/09 cho thấy lớp này giữ được 5 ca P1 trong khi phần định tuyến sập hoàn toàn —
đó là bằng chứng thực nghiệm cho "an toàn không được nằm sau một phép đoán".
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_RULES = Path(__file__).resolve().parent.parent / "rules" / "s0_rules.yaml"

# Thứ tự ưu tiên quyết định: cái nào "cứng" hơn thì thắng.
_SEVERITY = {"pass": 0, "backref": 1, "annotate": 2, "warn": 3, "ask": 4, "reject": 5}


def normalize_vi(s: str) -> str:
    """Bỏ dấu tiếng Việt + chữ thường, để mẫu trong YAML viết không dấu vẫn khớp.

    `đ` không phân rã được bằng NFD nên phải thay tay — bỏ sót chữ này thì
    "đoản mạch", "điện lưới", "đốt fuse" đều lọt lưới.
    """
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


@dataclass(slots=True)
class Rule:
    id: str
    axis: str
    decision: str
    patterns: list[re.Pattern[str]]
    reply_vi: str = ""
    annotate_vi: str = ""
    notice_vi: str = ""
    why_vi: str = ""
    gate: str | None = None
    gate_card: dict[str, Any] = field(default_factory=dict)
    never_auto: bool = False
    requires_release_snapshot: bool = False
    scan: str = "prompt"           # prompt | attachments
    ca_do: list[str] = field(default_factory=list)

    def match(self, text: str) -> str | None:
        for p in self.patterns:
            m = p.search(text)
            if m:
                return m.group(0)
        return None


@dataclass(slots=True)
class S0Result:
    decision: str = "pass"
    block: bool = False
    reply_vi: str = ""
    annotations: list[str] = field(default_factory=list)
    cards: list[dict[str, Any]] = field(default_factory=list)
    notices: list[dict[str, Any]] = field(default_factory=list)
    fired: list[dict[str, Any]] = field(default_factory=list)
    backrefs: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    @property
    def rule_ids(self) -> list[str]:
        return [f["rule"] for f in self.fired]

    def to_ledger(self) -> dict[str, Any]:
        """§9 tiêu chí: "Sổ cái ghi s0.decision ... cho mọi lượt"."""
        return {
            "hook": "UserPromptSubmit",
            "decision": self.decision,
            "rules": self.fired,
            "blocked": self.block,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


class S0Engine:
    def __init__(self, rules_path: str | Path = DEFAULT_RULES):
        self.path = Path(rules_path)
        self.rules: list[Rule] = []
        self.load()

    def load(self) -> None:
        doc = yaml.safe_load(self.path.read_text("utf-8")) or {}
        rules: list[Rule] = []
        for r in doc.get("rules", []):
            pats = [re.compile(p, re.IGNORECASE) for p in (r.get("match", {}).get("any_of") or [])]
            if not pats:
                raise ValueError(f"Luật {r.get('id')} không có mẫu nào — luật câm là luật chết.")
            rules.append(Rule(
                id=r["id"], axis=r.get("axis", ""), decision=r["decision"], patterns=pats,
                reply_vi=(r.get("reply_vi") or "").strip(),
                annotate_vi=(r.get("annotate_vi") or "").strip(),
                notice_vi=(r.get("notice_vi") or "").strip(),
                why_vi=r.get("why_vi", ""),
                gate=r.get("gate"), gate_card=r.get("gate_card") or {},
                never_auto=bool(r.get("never_auto")),
                requires_release_snapshot=bool(r.get("requires_release_snapshot")),
                scan=r.get("scan", "prompt"),
                ca_do=list(r.get("ca_do") or []),
            ))
        self.rules = rules

    # ------------------------------------------------------------------ chạy
    def run(self, text: str, *, attachments_text: str = "", ledger: Any = None,
            gate_id_factory: Any = None) -> S0Result:
        t0 = time.perf_counter()
        res = S0Result()
        norm_prompt = normalize_vi(text or "")
        norm_attach = normalize_vi(attachments_text or "")

        for rule in self.rules:
            hay = norm_attach if rule.scan == "attachments" else norm_prompt
            if not hay:
                continue
            hit = rule.match(hay)
            if hit is None:
                continue

            res.fired.append({"rule": rule.id, "axis": rule.axis, "decision": rule.decision,
                              "matched": hit, "why_vi": rule.why_vi, "ca_do": rule.ca_do})

            if rule.decision == "reject":
                res.decision = "reject"
                res.block = True
                res.reply_vi = rule.reply_vi
                break  # chặn hẳn thì không cần xét tiếp

            if rule.decision == "ask":
                res.decision = "ask"
                res.block = True
                gid = gate_id_factory() if gate_id_factory else f"gate-{rule.id}"
                res.cards.append(self._gate_card(rule, gid, text))
                # Một số luật vừa hỏi vừa có lời giải thích sẵn (P-QUAL-01).
                if rule.reply_vi:
                    res.reply_vi = rule.reply_vi
                break

            if rule.decision == "warn":
                # KHÔNG chặn: trả lời an toàn ngay rồi vẫn để mô hình giúp tiếp.
                if _SEVERITY["warn"] > _SEVERITY[res.decision]:
                    res.decision = "warn"
                res.reply_vi = (res.reply_vi + "\n\n" + rule.reply_vi).strip()
                if rule.annotate_vi:
                    res.annotations.append(rule.annotate_vi)

            elif rule.decision == "annotate":
                if _SEVERITY["annotate"] > _SEVERITY[res.decision]:
                    res.decision = "annotate"
                if rule.annotate_vi:
                    res.annotations.append(rule.annotate_vi)
                if rule.notice_vi:
                    res.notices.append({"level": "warn", "code": rule.id, "text": rule.notice_vi})

            elif rule.decision == "backref":
                if _SEVERITY["backref"] > _SEVERITY[res.decision]:
                    res.decision = "backref"
                res.backrefs = self._lookup_runs(text, ledger)
                if res.backrefs:
                    res.annotations.append(_backref_note(res.backrefs))
                else:
                    res.annotations.append(
                        "Người dùng nói câu trỏ ngược tới một việc đã làm, nhưng sổ cái chưa có "
                        "lượt nào khớp. Hỏi lại cho rõ họ muốn quay về đâu — đừng đoán."
                    )

        res.elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return res

    # ------------------------------------------------------------------ phụ
    def _gate_card(self, rule: Rule, gate_id: str, original_text: str) -> dict[str, Any]:
        c = rule.gate_card
        return {
            "type": "gate",
            "card_id": gate_id,
            "gate_id": gate_id,
            "gate": rule.gate,
            "rule": rule.id,
            "title": c.get("title", rule.why_vi or rule.id),
            "risk": c.get("risk", "R3"),
            "never_auto": rule.never_auto,
            "requires_release_snapshot": rule.requires_release_snapshot,
            "consequences_vi": c.get("consequences_vi", []),
            "require_vi": c.get("require_vi", ""),
            "require_fields": c.get("require_fields", []),
            "options": c.get("options", ["Duyệt", "Từ chối"]),
            "quote": original_text,
        }

    @staticmethod
    def _lookup_runs(text: str, ledger: Any) -> list[dict[str, Any]]:
        """Giải câu trỏ ngược bằng TRA BẢNG, không bằng phép đoán (§E8.3).

        "quay lại trước khi tối ưu -O3" → tìm trong sổ cái lượt nào có chữ "-O3".
        """
        if ledger is None:
            return []
        # Lấy các từ đáng làm mốc: bỏ từ nối, giữ từ dài / có số / có dấu gạch.
        norm = normalize_vi(text)
        stop = {"quay", "lai", "ve", "truoc", "khi", "lam", "tiep", "tuc", "cai", "cho",
                "toi", "minh", "anh", "hay", "di", "nhu", "hoi", "ban", "phien", "hoan", "tac"}
        keys = [w for w in re.findall(r"[a-z0-9\-]{3,}", norm) if w not in stop]
        hits: list[dict[str, Any]] = []
        seen: set[str] = set()
        for k in keys:
            for r in ledger.find_run(k):
                if r["run_id"] and r["run_id"] not in seen:
                    seen.add(r["run_id"])
                    hits.append({**r, "matched_on": k})
        if not hits:  # không khớp từ nào → đưa vài lượt gần nhất để mô hình hỏi lại có căn cứ
            hits = ledger.find_run("")[-3:]
        return hits[-5:]


def _backref_note(runs: list[dict[str, Any]]) -> str:
    lines = [f"  - {r['run_id']} ({r['ts'][:16]}): {(r.get('text') or '')[:90]}" for r in runs]
    return (
        "Người dùng nhắc tới một việc đã làm trước đó. Sổ cái (xác định, không phải phỏng đoán) "
        "cho các lượt khớp sau:\n" + "\n".join(lines) +
        "\nNếu định quay lui, dùng đúng run_id ở trên. Nếu có nhiều lượt khớp, hỏi người dùng "
        "chọn cái nào — đừng tự chọn."
    )
