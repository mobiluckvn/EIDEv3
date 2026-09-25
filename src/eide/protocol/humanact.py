# -*- coding: utf-8 -*-
"""HumanAct — 13 loai y chi cua nguoi. EIDE-MDD-40 §D2.

Dinh nghia goc trong tai lieu:

    HumanAct { kind: say|choose|decide|confirm|edit|upload|stop|undo|resume|attend|set|snapshot|branch,
               text, target: {type, id, version?}, data,
               origin: {surface, block?, row?, selection?}, note?: "vi sao" }

Vi sao mot loai thong diep duy nhat (I1): de KHONG co duong vong. Moi cai cham tren
bat ky be mat nao — bam nut Xac nhan mot Fact, sua mot o trong bang REQ, keo tha mot tep —
deu tro thanh HumanAct di qua Console va de lai dung mot dong trong transcript (I2).
Nho vay transcript la hinh chieu cua so cai va phat lai duoc (CX16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import EideError, schema_violation

# ---------------------------------------------------------------- 13 loai
HUMAN_ACT_KINDS: dict[str, str] = {
    "say": "Go tu do",
    "choose": "Chon muc trong the",
    "decide": "Quyet dinh cong (CHI loai nay moi mo cong — I6)",
    "confirm": "Xac nhan/tu choi/sua Fact hoac nguon",
    "edit": "Sua hien vat roi luu (-> duong ong E4)",
    "upload": "Keo tha/chon tep",
    "stop": "Dung khan",
    "undo": "Hoan tac",
    "resume": "Tiep tuc sau su co / mo lai du an",
    "attend": "Chuyen tab / chon hien vat",
    "set": "Doi thiet lap",
    "snapshot": "Ghi ban ung y",
    "branch": "Re/chuyen/gop nhanh",
}

# Be mat hop le — 10 Surface cua §E7 + console.
SURFACES = {
    "console", "requirements", "documents", "knowledge", "design", "tools",
    "code", "simulation", "hardware", "journal", "history", "project", "settings",
}


@dataclass(slots=True)
class Target:
    """Hien vat ma thao tac nham vao.

    Dang chuoi trong tai lieu: `file:src/main.c@v7`, `spec:REQ-set@v2`, `fact:12`,
    `pinout:U1`, `criteria:sim-01`, `changeset:cs-109`, `run:run-43`, `snapshot:snap-3`.
    """

    type: str
    id: str
    version: str | None = None

    @classmethod
    def parse(cls, s: str) -> "Target":
        head, _, rest = s.partition(":")
        if not rest:
            raise schema_violation("target", f"thiếu dấu hai chấm trong {s!r}")
        ident, sep, ver = rest.rpartition("@")
        if sep:
            return cls(type=head, id=ident, version=ver)
        return cls(type=head, id=rest)

    def __str__(self) -> str:
        return f"{self.type}:{self.id}" + (f"@{self.version}" if self.version else "")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "id": self.id}
        if self.version:
            d["version"] = self.version
        return d


@dataclass(slots=True)
class Origin:
    """Xuat xu: cai cham nay den tu dau tren be mat nao.

    I4 — loi khong biet giao dien, nhung PHAI biet xuat xu, vi dong transcript
    "[Ban] Sua <hien vat> ..." va viec phan loai sua (E4.1) deu doc tu day.
    """

    surface: str
    block: str | None = None      # ma khoi UI, vi du "A2.1" (ui_model.py)
    row: str | None = None        # dong trong bang, vi du "FR-03"
    selection: str | None = None  # vung chon trong editor, vi du "L42-L58"

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in
                (("surface", self.surface), ("block", self.block),
                 ("row", self.row), ("selection", self.selection)) if v is not None}


@dataclass(slots=True)
class HumanAct:
    kind: str
    text: str = ""
    target: Target | None = None
    data: dict[str, Any] = field(default_factory=dict)
    origin: Origin = field(default_factory=lambda: Origin(surface="console"))
    note: str | None = None          # "vi sao" — nguoi giai thich thay doi cua ho (E4 buoc 1)
    id: str = ""                     # do loi cap (h-0940); idempotent theo id (I5)
    seq: int = 0                     # thu tu chieu UI -> loi (I5)
    ts: str = ""                     # ISO 8601, do loi dong dau khi nhan

    # ------------------------------------------------------------------ kiem
    def validate(self) -> "HumanAct":
        if self.kind not in HUMAN_ACT_KINDS:
            raise schema_violation(
                "HumanAct.kind",
                f"{self.kind!r} không nằm trong 13 loại: {', '.join(HUMAN_ACT_KINDS)}",
            )
        if self.origin.surface not in SURFACES:
            raise schema_violation("HumanAct.origin.surface", f"bề mặt lạ: {self.origin.surface!r}")

        req = _REQUIRED_DATA.get(self.kind)
        if req:
            missing = [k for k in req if k not in self.data]
            if missing:
                raise schema_violation(
                    f"HumanAct[{self.kind}].data", f"thiếu trường {', '.join(missing)}"
                )

        # I6 duoc canh o day, khong chi o lop cap quyen: mot `decide` khong kem gate_id
        # la mot cau "co" tra loi vao khoang khong.
        if self.kind == "decide" and not self.data.get("gate_id"):
            raise schema_violation("HumanAct[decide]", "thiếu gate_id — một chữ 'có' không mở cổng nào")

        if self.kind == "edit":
            if self.target is None:
                raise schema_violation("HumanAct[edit]", "thiếu target: sửa hiện vật nào?")
            # base_version la thu duy nhat cho phep phat hien nguoi va tac tu dam nhau (E4 buoc 3)
            if "base_version" not in self.data:
                raise schema_violation(
                    "HumanAct[edit].data",
                    "thiếu base_version — không có nó thì không phát hiện được xung đột",
                )
        return self

    # ------------------------------------------------------------------ hien thi
    def transcript_line(self) -> str:
        """Dong "[Ban] ..." — I2 doi MOI HumanAct co dung mot dong."""
        t = str(self.target) if self.target else ""
        body = {
            "say": lambda: self.text,
            "choose": lambda: f"Chọn: {self.data.get('choice', self.text)}",
            "decide": lambda: (
                f"{'Duyệt' if self.data.get('approved') else 'Từ chối'} "
                f"{self.data.get('gate', 'cổng')} ({self.data['gate_id']})"
                + (f" — vì: {self.note}" if self.note else "")
            ),
            "confirm": lambda: f"Xác nhận {t}: {self.data.get('verdict', self.text)}",
            "edit": lambda: (
                f"Sửa {t}: {self.data.get('summary', 'thay đổi')}"
                + (f" — vì: {self.note}" if self.note else "")
            ),
            "upload": lambda: f"Nạp tệp: {', '.join(self.data.get('files', [])) or self.text}",
            "stop": lambda: "DỪNG",
            "undo": lambda: f"Hoàn tác {t}",
            "resume": lambda: "Tiếp tục",
            "attend": lambda: f"Mở {t or self.origin.surface}",
            "set": lambda: f"Đổi thiết lập: {self.data.get('key')} = {self.data.get('value')}",
            "snapshot": lambda: f"Ghi bản ưng ý: {self.data.get('name')}",
            "branch": lambda: f"Nhánh {self.data.get('action')}: {self.data.get('name')}",
        }[self.kind]()
        return f"[Bạn] {body}"

    # ------------------------------------------------------------------ chuyen dang
    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id, "seq": self.seq, "ts": self.ts,
            "kind": self.kind, "text": self.text,
            "data": self.data, "origin": self.origin.to_dict(),
        }
        if self.target:
            d["target"] = self.target.to_dict()
        if self.note:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "HumanAct":
        tgt = d.get("target")
        if isinstance(tgt, str):
            target = Target.parse(tgt)
        elif isinstance(tgt, dict):
            target = Target(type=tgt["type"], id=tgt["id"], version=tgt.get("version"))
        else:
            target = None
        o = d.get("origin") or {"surface": "console"}
        return cls(
            kind=d.get("kind", ""),
            text=d.get("text", "") or "",
            target=target,
            data=d.get("data") or {},
            origin=Origin(surface=o.get("surface", "console"), block=o.get("block"),
                          row=o.get("row"), selection=o.get("selection")),
            note=d.get("note"),
            id=d.get("id", ""),
            seq=int(d.get("seq", 0) or 0),
            ts=d.get("ts", "") or "",
        ).validate()


# Truong `data` bat buoc theo tung loai — rut tu §D2 va §E5/E6.
_REQUIRED_DATA: dict[str, tuple[str, ...]] = {
    "decide": ("gate_id", "approved"),
    "edit": ("base_version",),
    "undo": ("mode",),            # "revert" | "restore_branch"
    "snapshot": ("name",),
    "branch": ("action",),        # create | switch | merge
    "set": ("key", "value"),
    "upload": ("files",),
}


def ensure(act: HumanAct | dict[str, Any]) -> HumanAct:
    """Nhan ca dict tu day day RPC lan doi tuong da dung."""
    if isinstance(act, HumanAct):
        return act.validate()
    return HumanAct.from_dict(act)


__all__ = ["HumanAct", "Target", "Origin", "HUMAN_ACT_KINDS", "SURFACES", "ensure", "EideError"]
