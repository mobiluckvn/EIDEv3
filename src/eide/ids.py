# -*- coding: utf-8 -*-
"""Sinh dinh danh co the doc bang mat va lap lai duoc.

Tai lieu dung cac dinh danh dang `cs-0109`, `run-43`, `h-0940`, `snap-3`. Chung xuat
hien trong loi tac tu noi voi nguoi ("hoan tac cs-0109"), nen phai NGAN va DOC DUOC,
khong dung uuid.

Bo dem nam trong `.eide/counters.json` cua tung du an. Vi F3 doi "phat lai so cai
tai tao trang thai 100 %" (CX16), bo dem phai la mot phan trang thai du an, khong phai
bien toan cuc cua tien trinh.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

# Tien to -> do rong so (de sap xep theo ten van dung thu tu)
_WIDTH = {"cs": 4, "run": 3, "h": 4, "snap": 2, "gate": 4, "ev": 6, "card": 4, "inc": 3}


class IdGen:
    """Bo sinh id tang dan, ben vung qua cac phien."""

    def __init__(self, state_dir: Path):
        self._path = Path(state_dir) / "counters.json"
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        if self._path.exists():
            try:
                self._counters = json.loads(self._path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                # Bo dem hong thi KHONG duoc bat dau lai tu 0 — se de id trung len
                # id cu trong so cai. Doc so cai de tim moc cao nhat la viec cua store;
                # o day dung han, de goi tu biet la co chuyen.
                raise

    def next(self, prefix: str) -> str:
        with self._lock:
            n = self._counters.get(prefix, 0) + 1
            self._counters[prefix] = n
            self._flush()
        return f"{prefix}-{n:0{_WIDTH.get(prefix, 4)}d}"

    def peek(self, prefix: str) -> int:
        return self._counters.get(prefix, 0)

    def bump_to(self, prefix: str, n: int) -> None:
        """Keo bo dem len it nhat `n` (dung khi phat lai so cai)."""
        with self._lock:
            if n > self._counters.get(prefix, 0):
                self._counters[prefix] = n
                self._flush()

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self._counters, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self._path)  # ghi nguyen tu: khong bao gio de lai tep cut


def parse(ident: str) -> tuple[str, int]:
    """`cs-0109` -> (`cs`, 109). Nem ValueError neu khong dung dang."""
    prefix, _, num = ident.rpartition("-")
    if not prefix or not num.isdigit():
        raise ValueError(f"Dinh danh khong dung dang: {ident!r}")
    return prefix, int(num)
