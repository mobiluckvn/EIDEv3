# -*- coding: utf-8 -*-
"""Lớp cấp quyền — EIDE-MDD-40 §B4.

    perm = policy.decide(call, pre)   # allow | ask (thẻ cổng riêng) | deny (lỗi cho LLM)

Ba điều đáng nói về thiết kế:

1. **Cổng là thẻ riêng (I6).** `ask` không phải là "hỏi trong hội thoại". Nó phát ra một
   THẺ có `gate_id`, và chỉ một `HumanAct{kind:"decide", gate_id:...}` mới mở được. Lý do
   nằm ở UC18: nếu câu xác nhận nạp firmware trộn chung với câu làm rõ yêu cầu, thì một
   chữ "Có" của người trả lời cả hai thứ — và một trong hai thứ đó là nạp vào chip thật.

2. **`deny` là lỗi có ích, không phải sự cố.** Nó quay về mô hình kèm `hint_for_agent`.
   Mô hình đọc, sửa lời gọi, gọi lại. Đó là cách N1/N7/N8 được thi hành mà không cần
   trông vào việc mô hình có nhớ hiến pháp hay không.

3. **`never_auto` không có ngoại lệ.** Mức tự chủ A4 cũng không bỏ qua được G-OPS.

Về `eval`: biểu thức điều kiện được ước lượng bằng `eval` với không gian tên rỗng. An
toàn ở đây dựa trên một sự thật: `policy.yaml` là tệp của SẢN PHẨM, không phải đầu vào
của người dùng hay của mô hình. Không bao giờ được nạp policy từ nguồn không tin cậy.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..errors import denied_by_policy

DEFAULT_POLICY = Path(__file__).resolve().parent / "policy.yaml"
_RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}


@dataclass(slots=True)
class Decision:
    action: str                       # allow | ask | deny
    rule_id: str = ""
    gate: str | None = None
    reason_vi: str = ""
    summary_vi: str = ""
    never_auto: bool = False
    irreversible: bool = False
    require_fields: list[str] = field(default_factory=list)
    principle: str = ""

    @property
    def allow(self) -> bool:
        return self.action == "allow"

    def to_ledger(self) -> dict[str, Any]:
        return {"action": self.action, "rule": self.rule_id, "gate": self.gate,
                "principle": self.principle}


class PolicyEngine:
    def __init__(self, path: str | Path = DEFAULT_POLICY, *, autonomy: str | None = None):
        self.path = Path(path)
        doc = yaml.safe_load(self.path.read_text("utf-8")) or {}
        self.rules: list[dict[str, Any]] = doc.get("rules", [])
        self.autonomy_table: dict[str, Any] = doc.get("autonomy", {})
        self.autonomy: str = autonomy or doc.get("autonomy_default", "A3")
        self.trusted: set[str] = set()      # nguồn/gói người đã bấm "Tin" (§E7, MM-remember)

    # ------------------------------------------------------------------ quyết
    def decide(self, call: dict[str, Any], pre_facts: dict[str, Any] | None = None,
               spec: Any = None) -> Decision:
        name = call.get("tool") or call.get("name") or ""
        env = self._env(call, pre_facts or {}, spec)

        for rule in self.rules:
            if not _tool_matches(rule.get("tool", "*"), name):
                continue
            cond = rule.get("when")
            if cond and not _eval(cond, env):
                continue

            action = rule.get("action", "allow")

            if action == "by_risk":
                return self._by_risk(spec, rule, name)

            if action == "allow":
                # Luật allow có trần rủi ro: ghi tự do chỉ khi mức tự chủ cho phép.
                cap = rule.get("max_autonomy_risk")
                if cap and not self._autonomy_allows(cap):
                    return Decision("ask", rule.get("id", ""), gate=_gate_for(name),
                                    summary_vi=f"Mức tự chủ {self.autonomy} chưa cho tự động "
                                               f"thao tác mức {cap}.")
                return Decision("allow", rule.get("id", ""))

            if action == "deny":
                return Decision("deny", rule.get("id", ""),
                                reason_vi=_one_line(rule.get("reason_vi", "")),
                                gate=rule.get("gate"),
                                principle=rule.get("principle", ""))

            if action == "ask":
                auto_if = rule.get("auto_if")
                never = bool(rule.get("never_auto"))
                if not never and auto_if and _eval(auto_if, env):
                    return Decision("allow", rule.get("id", ""))
                # "Tin lần sau" chỉ áp dụng cho R0–R2 (§E7 thẻ cổng, MM-remember).
                if not never and self._is_trusted(name, call) and _risk(spec) <= 2:
                    return Decision("allow", rule.get("id", ""))
                return Decision("ask", rule.get("id", ""), gate=rule.get("gate"),
                                summary_vi=_one_line(rule.get("summary_vi", "")),
                                never_auto=never,
                                irreversible=bool(rule.get("irreversible")),
                                require_fields=list(rule.get("require_fields") or []),
                                principle=rule.get("principle", ""))

        return self._by_risk(spec, {"id": "POL-fallback"}, name)

    # ------------------------------------------------------------------ phụ
    def _by_risk(self, spec: Any, rule: dict[str, Any], name: str) -> Decision:
        risk = getattr(spec, "risk", "R2") if spec is not None else "R2"
        gate = getattr(spec, "gate", None) if spec is not None else None
        if self._autonomy_allows(risk):
            return Decision("allow", rule.get("id", ""))
        return Decision("ask", rule.get("id", ""), gate=gate or _gate_for(name),
                        summary_vi=f"Thao tác mức {risk}, mức tự chủ hiện tại là {self.autonomy}.")

    def _autonomy_allows(self, risk: str) -> bool:
        cap = (self.autonomy_table.get(self.autonomy) or {}).get("auto_max_risk", "R2")
        return _RISK_ORDER.get(risk, 4) <= _RISK_ORDER.get(cap, 2)

    def _is_trusted(self, name: str, call: dict[str, Any]) -> bool:
        if name in self.trusted:
            return True
        dom = (call.get("args") or {}).get("domain")
        return bool(dom and dom in self.trusted)

    def _env(self, call: dict[str, Any], pre: dict[str, Any], spec: Any) -> dict[str, Any]:
        args = call.get("args") or {}
        env: dict[str, Any] = {
            "args": _Dot(args),
            "autonomy": self.autonomy,
            "trusted": self.trusted,
            "tool": _Dot({"risk": getattr(spec, "risk", "R2") if spec else "R2",
                          "writes_artefact": bool(getattr(spec, "writes_artefact", False))}),
        }
        # Các nhóm hook PreToolUse đưa xuống: constant_guard.*, target.*, explain.*…
        groups: dict[str, dict[str, Any]] = {}
        for k, v in pre.items():
            head, _, tail = k.partition(".")
            if tail:
                groups.setdefault(head, {})[tail] = v
            else:
                env[k] = v
        for g, d in groups.items():
            env[g] = _Dot(d)
        # Nhóm nào hook chưa đưa xuống thì vẫn phải có mặt, để `!explain.complete` đọc
        # được là "chưa có" thay vì nổ NameError — một điều kiện không tính được sẽ
        # dừng cả lượt (xem `_eval`), và ta không muốn dừng vì hook im lặng.
        # M4-02 — `test` và `criteria` phải có trong danh sách này, và chỗ này đáng đọc kỹ:
        # một nhóm THIẾU ở đây không làm luật "không nổ", nó làm **cả lượt dừng** bằng
        # `ValueError`. `POL-N6-sua-test` khớp mọi `fs.write`, nên thiếu nhóm `test` là mọi
        # lời gọi ghi tệp đều đổ — kể cả khi hook im đúng cách. Đo được ngay khi thêm luật:
        # `test_muc_tu_chu_thap_thi_ghi_phai_hoi` đỏ với "Điều kiện policy không tính được".
        #
        # `criteria` cũng chưa có ở đây từ trước. Nó chưa nổ chỉ vì hook `doi_tieu_chi` luôn
        # cấp đủ ba khoá ở MỌI nhánh — tức là hàng rào đang dựa vào một thói quen tốt của
        # một hook, không dựa vào một bảo đảm.
        for known in ("constant_guard", "target", "explain", "plan", "snapshot", "tier",
                      "touches", "test", "criteria"):
            env.setdefault(known, _Dot({}))
        return env

    def deny_error(self, call: dict[str, Any], d: Decision,
                   facts: dict[str, Any] | None = None):
        """Lỗi từ chối. Kèm CHI TIẾT từ hook, vì một lời từ chối không nói rõ cái gì sai
        thì mô hình chỉ có thể thử lại y nguyên — và đó là vòng lặp vô ích đã đo được."""
        ly_do = d.reason_vi or "không được phép"
        ds = (facts or {}).get("constant_guard.list")
        if ds:
            ly_do += " Các hằng số chưa có nguồn: " + ", ".join(str(x) for x in ds) + "."
        thieu = (facts or {}).get("explain.missing")
        if thieu:
            ly_do += " Trường explain còn thiếu: " + ", ".join(thieu) + "."
        return denied_by_policy(call.get("tool", "?"), ly_do, d.gate)


# --------------------------------------------------------------------------- tiện
class _Dot(dict):
    """Cho phép viết `args.path` và `constant_guard.unsourced` trong điều kiện YAML.

    Khoá không có → None (falsy), để `!args.source_quote` có nghĩa "không có / rỗng".
    """

    def __getattr__(self, k: str) -> Any:
        return self.get(k)


def _tool_matches(pattern: str, name: str) -> bool:
    return any(fnmatch.fnmatch(name, p.strip()) for p in pattern.split("|"))


_TRANSLATE = [(r"&&", " and "), (r"\|\|", " or "), (r"(?<![=!<>])!(?!=)", " not ")]


def _eval(expr: str, env: dict[str, Any]) -> bool:
    py = expr
    for pat, rep in _TRANSLATE:
        py = re.sub(pat, rep, py)
    try:
        return bool(eval(py, {"__builtins__": {}}, env))  # noqa: S307 — xem docstring module
    except Exception:
        # Điều kiện sai cú pháp KHÔNG được âm thầm thành "cho qua".
        raise ValueError(f"Điều kiện policy không tính được: {expr!r}")


def _risk(spec: Any) -> int:
    return _RISK_ORDER.get(getattr(spec, "risk", "R2") if spec else "R2", 4)


def _gate_for(name: str) -> str:
    head = name.split(".", 1)[0]
    return {"target": "G-FLASH", "fs": "G-FILE", "store": "G-DESIGN", "sim": "G-QUAL",
            "doc": "G-DATA", "tool": "G-TOOL", "history": "G-HIST",
            "snapshot": "G-HIST", "plan": "G-SCOPE"}.get(head, "G-SCOPE")


def _one_line(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())
