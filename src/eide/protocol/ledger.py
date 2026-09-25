# -*- coding: utf-8 -*-
"""So cai — ghi noi tiep, khong bao gio xoa. EIDE-MDD-40 §B6, §E5, §F3.

Vai tro:
  - I2  transcript la HINH CHIEU cua so cai, phat lai duoc (CX16 doi tai tao 100 %).
  - I5  write-ahead HumanAct: ghi truoc khi lam. Mat dien giua luot van biet nguoi da bao gi.
  - F3  "Toan ven lich su: append-only; kiem hash chuoi khi mo du an."
  - §B6 "Moi loi goi mo hinh, tool, cong, changeset trong so cai; export duoc."

Chuoi hash: moi ban ghi mang `prev` = hash cua ban ghi truoc va `hash` cua chinh no.
Sua mot dong o giua se lam vo chuoi tu do tro di va `verify()` chi ra dung dong hong.
Day khong phai chong hacker — day la chong chinh minh ghi de nham, va la dieu kien de
"hoan tac khong xoa lich su" co nghia.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

GENESIS = "0" * 64

# Cac loai su kien. Them loai moi thi them o day — de `verify` va bo phat lai biet.
EVENT_KINDS = {
    "turn.start", "turn.end",
    "human_act",          # write-ahead, truoc moi xu ly (I5)
    "ui_command",         # moi thu nguoi nhin thay
    "hook",               # quyet dinh cua hook S0/pre/post/stop
    "llm_call",           # mot lan goi mo hinh: model, token vao/ra, thoi gian
    "tool_use", "tool_result",
    "gate",               # the cong phat ra / quyet dinh cua nguoi
    "card",               # the lam ro: phat ra / duoc tra loi / bi bo qua
    "tombstone",          # da quen co chu dich (P7) — khong duoc hoi sinh
    "changeset",          # chi muc; noi dung day o changesets.jsonl (§E5.1)
    "incident",           # mang, LLM, timeout, sandbox (UC19)
    "note",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _digest(payload: str, prev: str) -> str:
    return hashlib.sha256((prev + payload).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class Event:
    seq: int
    ts: str
    kind: str
    data: dict[str, Any]
    prev: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {"seq": self.seq, "ts": self.ts, "kind": self.kind,
                "data": self.data, "prev": self.prev, "hash": self.hash}


class Ledger:
    """So cai mot du an. An toan voi nhieu luong trong mot tien trinh."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._seq, self._head = self._tail()

    # ------------------------------------------------------------------ doc
    def _tail(self) -> tuple[int, str]:
        """Doc dong cuoi de biet seq va hash dang o dau. Khong nap ca tep."""
        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0, GENESIS
        last = None
        with self.path.open("rb") as f:
            for raw in f:  # tep so cai mot du an ca nhan — duyet tuan tu la du nhanh
                if raw.strip():
                    last = raw
        if last is None:
            return 0, GENESIS
        rec = json.loads(last)
        return int(rec["seq"]), rec["hash"]

    def read(self, since_seq: int = 0) -> Iterator[Event]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                if r["seq"] > since_seq:
                    yield Event(r["seq"], r["ts"], r["kind"], r["data"], r["prev"], r["hash"])

    # ------------------------------------------------------------------ ghi
    def append(self, kind: str, data: dict[str, Any]) -> Event:
        if kind not in EVENT_KINDS:
            raise ValueError(f"Loại sự kiện lạ: {kind!r}. Thêm vào EVENT_KINDS nếu nó có thật.")
        with self._lock:
            seq = self._seq + 1
            ts = _now()
            body = {"seq": seq, "ts": ts, "kind": kind, "data": data}
            payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            h = _digest(payload, self._head)
            rec = {**body, "prev": self._head, "hash": h}
            line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
            # fsync: write-ahead chi co nghia neu no that su nam tren dia truoc khi ta lam viec.
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            self._seq, self._head = seq, h
            return Event(seq, ts, kind, data, rec["prev"], h)

    # ------------------------------------------------------------------ kiem
    def verify(self) -> tuple[bool, str]:
        """Kiem chuoi hash. Tra (dat, mo ta cho nguoi doc) — goi khi MO DU AN (§F3)."""
        prev = GENESIS
        n = 0
        for i, ev in enumerate(self.read(), 1):
            if ev.seq != i:
                return False, f"Sổ cái đứt thứ tự ở dòng {i}: seq ghi là {ev.seq}."
            if ev.prev != prev:
                return False, f"Sổ cái bị sửa ở sự kiện {ev.seq} ({ev.kind}, {ev.ts}): liên kết trước không khớp."
            body = {"seq": ev.seq, "ts": ev.ts, "kind": ev.kind, "data": ev.data}
            payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if _digest(payload, prev) != ev.hash:
                return False, f"Sổ cái bị sửa ở sự kiện {ev.seq} ({ev.kind}, {ev.ts}): nội dung không khớp hash."
            prev = ev.hash
            n = ev.seq
        return True, f"Sổ cái toàn vẹn: {n} sự kiện."

    @property
    def seq(self) -> int:
        return self._seq

    # ------------------------------------------------------------------ tien ich
    def last_run_id(self) -> str | None:
        run = None
        for ev in self.read():
            if ev.kind == "turn.start":
                run = ev.data.get("run_id")
        return run

    def find_run(self, needle: str) -> list[dict[str, Any]]:
        """Tra bang `run` cho hook BACKREF ("lam lai", "quay lai truoc khi toi uu -O3").

        S0 giai cac cau tro nguoc bang TRA BANG, khong bang phep doan cua mo hinh (§B4).
        """
        runs: list[dict[str, Any]] = []
        for ev in self.read():
            if ev.kind == "turn.start":
                runs.append({"run_id": ev.data.get("run_id"), "ts": ev.ts,
                             "text": ev.data.get("text", ""), "tools": []})
            elif ev.kind == "tool_use" and runs:
                runs[-1]["tools"].append(ev.data.get("tool"))
        if not needle:
            return runs
        low = needle.lower()
        return [r for r in runs
                if low in (r["text"] or "").lower()
                or any(low in (t or "").lower() for t in r["tools"])]
