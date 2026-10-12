# -*- coding: utf-8 -*-
"""UICommand — 16 lenh loi gui cho giao dien. EIDE-MDD-40 §D2.

I3: giao dien khong quyet gi ca, chi render thu loi gui. Nen moi thu nguoi nhin thay
phai di qua mot trong 16 lenh nay. Neu mot thong tin khong the dien dat bang 16 lenh
nay thi do la khoang trong THIET KE, phai ghi DEV-2xx — khong duoc mo mot duong rieng
cho giao dien tu quyet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..errors import schema_violation

UI_COMMANDS: dict[str, str] = {
    "console.post": "Dang loi tac tu + the",
    "console.stream": "Stream van ban (delta)",
    "card.resolve": "Dong the (da duoc tra loi)",
    "card.expire": "The het han",
    "surface.set": "Thay toan bo mo hinh be mat",
    "surface.patch": "Va mot phan be mat",
    "surface.append": "Noi them (log, timeline)",
    "surface.focus": "Dua mat nguoi toi mot vi tri",
    "surface.highlight": "To sang",
    "surface.lock": "Soft-lock khoi tac tu dang sua",
    "surface.unlock": "Bo khoa",
    "run.update": "The Run: tien trinh, chi phi, nut",
    "notice": "Thong bao ngan",
    "ui.set": "Thiet lap giao dien do loi quyet",
    "history.update": "Cap nhat changeset/snapshot/STALE",
    "explain.show": "Hien lop giai thich cua mot hien vat",
}


@dataclass(slots=True)
class UICommand:
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    seq: int = 0  # thu tu chieu loi -> UI (I5)

    def __post_init__(self) -> None:
        if self.method not in UI_COMMANDS:
            raise schema_violation(
                "UICommand.method",
                f"{self.method!r} không nằm trong 16 lệnh: {', '.join(UI_COMMANDS)}",
            )

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "method": self.method, "params": self.params}


# --------------------------------------------------------------------------- dung san
# Cac ham duoi day la CACH DUY NHAT lõi noi voi giao dien. Viet san de khong ai
# phai nho ten tham so, va de doi hop dong thi doi mot cho.


def console_post(text: str, *, role: str = "agent", card: dict[str, Any] | None = None,
                 act_id: str | None = None) -> UICommand:
    """Mot dong trong transcript. role: agent | human | system (I2)."""
    p: dict[str, Any] = {"role": role, "text": text}
    if card:
        p["card"] = card
    if act_id:
        p["in_reply_to"] = act_id
    return UICommand("console.post", p)


def console_stream(delta: str, *, stream_id: str, done: bool = False) -> UICommand:
    return UICommand("console.stream", {"stream_id": stream_id, "delta": delta, "done": done})


def card_resolve(card_id: str, *, by: str, choice: Any = None) -> UICommand:
    return UICommand("card.resolve", {"card_id": card_id, "by": by, "choice": choice})


def card_expire(card_id: str, *, why: str) -> UICommand:
    return UICommand("card.expire", {"card_id": card_id, "why": why})


def surface_set(surface: str, model: dict[str, Any]) -> UICommand:
    return UICommand("surface.set", {"surface": surface, "model": model})


def surface_patch(surface: str, block: str, patch: Any) -> UICommand:
    return UICommand("surface.patch", {"surface": surface, "block": block, "patch": patch})


def surface_append(surface: str, block: str, items: list[Any]) -> UICommand:
    return UICommand("surface.append", {"surface": surface, "block": block, "items": items})


def surface_focus(surface: str, *, block: str | None = None, row: str | None = None) -> UICommand:
    return UICommand("surface.focus", {"surface": surface, "block": block, "row": row})


def surface_highlight(surface: str, *, block: str, refs: list[str], why: str = "") -> UICommand:
    return UICommand("surface.highlight",
                     {"surface": surface, "block": block, "refs": refs, "why": why})


def surface_lock(surface: str, *, block: str, by: str, why: str) -> UICommand:
    """Soft-lock: giao dien CANH BAO nhung VAN CHO nguoi sua (§E4 buoc 1).

    Khoa cung se bien tac tu thanh cai chan duong; ca CX09 do dung chuyen nguoi pha khoa.
    """
    return UICommand("surface.lock", {"surface": surface, "block": block, "by": by, "why": why})


def surface_unlock(surface: str, *, block: str) -> UICommand:
    return UICommand("surface.unlock", {"surface": surface, "block": block})


def run_update(run_id: str, *, status: str, steps: list[dict[str, Any]] | None = None,
               cost: dict[str, Any] | None = None, assumptions: list[str] | None = None,
               buttons: list[str] | None = None, so_thay_doi: int = 0) -> UICommand:
    """The Run. `so_thay_doi` = so changeset luot nay de lai (bo checkpoint ngam).

    Vi sao LOI dem chu khong de giao dien tu dem (I3): giao dien chi thay 40 changeset gan
    nhat qua `history.update`, nen no khong biet luot nay dong gop bao nhieu. Mot nut
    "Lui ca luot" sang len khi luot khong doi gi la mot nut bam duoc ma khong lam gi.
    """
    return UICommand("run.update", {
        "run_id": run_id, "status": status, "steps": steps or [],
        "cost": cost or {}, "assumptions": assumptions or [], "buttons": buttons or [],
        "so_thay_doi": so_thay_doi,
    })


def notice(text: str, *, level: str = "info", code: str | None = None,
           alternatives: list[str] | None = None) -> UICommand:
    return UICommand("notice", {"level": level, "text": text, "code": code,
                                "alternatives": alternatives or []})


def ui_set(key: str, value: Any) -> UICommand:
    return UICommand("ui.set", {"key": key, "value": value})


def history_update(*, changesets: list[dict[str, Any]] | None = None,
                   snapshots: list[dict[str, Any]] | None = None,
                   stale: list[dict[str, Any]] | None = None,
                   nhanh: dict[str, Any] | None = None,
                   vua_ghi: dict[str, Any] | None = None) -> UICommand:
    """Capture nhat ve lich su — EIDE-EDIT-47 DEV-365 them `nhanh` va `vua_ghi`.

    `nhanh = {"hien_tai": str, "danh_sach": [str]}` — de giao dien ve menu nhanh ma khong
    phai `paint` ca tab Lich su, va khong phai tu goi git (giao dien khong chay lenh).

    `vua_ghi` — **lan luu vua roi cua NGUOI**, de hien thanh "Da ghi cs-12 · Hoan tac" song
     30 giay (§3.3 README "go 30 giay"). Loi khai thay vi de giao dien suy ra tu danh sach
    changeset: cung mot lenh nay con duoc phat cuoi moi luot voi 40 changeset, nen "cai nao
    la cai nguoi vua luu" khong doc duoc tu danh sach. Suy ra se cho toast noi sai.
    """
    return UICommand("history.update", {"changesets": changesets or [],
                                        "snapshots": snapshots or [], "stale": stale or [],
                                        "nhanh": nhanh or {}, "vua_ghi": vua_ghi})


def explain_show(artefact: str, explain: dict[str, Any]) -> UICommand:
    """Nut "Vi sao?" — hien explain da co san, KHONG ton token (§E3.3)."""
    return UICommand("explain.show", {"artefact": artefact, "explain": explain})
