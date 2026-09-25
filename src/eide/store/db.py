# -*- coding: utf-8 -*-
"""Kho hiện vật — event-sourced. EIDE-MDD-40 §B6, §E5.1.

    "hiện vật có cấu trúc (REQ, Fact, ADR, module) trong store SQLite theo
     event-sourcing: bảng events (append-only) + bảng snapshot trạng thái hiện tại"

Hai bảng, hai vai trò khác hẳn nhau:
  - `events`    : sự thật. Chỉ ghi thêm, không sửa, không xoá. Dựng lại được tất cả.
  - `artefacts` : tiện. Hình chiếu trạng thái hiện tại, để `<inventory>` chạy < 50 ms.
                  Mất cũng được — `rebuild()` dựng lại từ events.

Ở G1 chưa có công cụ nào GHI hiện vật, nên kho gần như rỗng. Nhưng `<inventory>` phải
đọc kho thật chứ không phải một cái rỗng giả: N3 nói tình trạng dự án do mã dựng, và
một bảng kiểm kê bịa ra thì tệ hơn không có (TC008 — mô hình bịa REQ_HW_I2C vì không
ai nói cho nó biết store đang rỗng).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
PRAGMA journal_mode=WAL;

-- Sự thật: chỉ ghi thêm.
CREATE TABLE IF NOT EXISTS events (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    changeset_id  TEXT,
    author        TEXT NOT NULL,            -- "human" | "agent:run-43"
    artefact_id   TEXT NOT NULL,
    artefact_type TEXT NOT NULL,
    op            TEXT NOT NULL,            -- create | update | delete
    version       INTEGER NOT NULL,
    payload       TEXT NOT NULL             -- JSON: {canonical, explain, deps, view_hint}
);
CREATE INDEX IF NOT EXISTS ix_events_artefact ON events(artefact_id, version);
CREATE INDEX IF NOT EXISTS ix_events_cs       ON events(changeset_id);

-- Tiện: hình chiếu trạng thái hiện tại.
CREATE TABLE IF NOT EXISTS artefacts (
    id            TEXT PRIMARY KEY,
    type          TEXT NOT NULL,
    version       INTEGER NOT NULL,
    author        TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    changeset_id  TEXT,
    canonical     TEXT NOT NULL,
    explain       TEXT NOT NULL,
    view_hint     TEXT,
    deps          TEXT,
    stale         INTEGER NOT NULL DEFAULT 0,
    stale_reason  TEXT,
    deleted       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_art_type  ON artefacts(type, deleted);
CREATE INDEX IF NOT EXISTS ix_art_stale ON artefacts(stale);

-- Fact tách riêng: nó được truy vấn theo thực thể/khoá/tầng chứ không theo id (§C1).
CREATE TABLE IF NOT EXISTS facts (
    fact_id       TEXT PRIMARY KEY,
    subject       TEXT NOT NULL,            -- "chip:ATmega328P@1.0.0" | "net:SDA" | "pin:U1.28"
    key           TEXT NOT NULL,            -- "vdd.max"
    value         TEXT,
    unit          TEXT,
    vmin          TEXT, vtyp TEXT, vmax TEXT,
    condition     TEXT,
    tier          TEXT NOT NULL,            -- VANG | BAC | NGUOI | DONG
    origin        TEXT NOT NULL,            -- extract | user | model
    source        TEXT NOT NULL,            -- JSON
    explain       TEXT NOT NULL,            -- JSON
    approved_by   TEXT, approved_at TEXT,
    supersedes    TEXT, superseded_by TEXT,
    errata        INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_fact_subject ON facts(subject, key);
CREATE INDEX IF NOT EXISTS ix_fact_tier    ON facts(tier);
"""

# Các loại hiện vật có trong §E2 (22 dòng bảng) — dùng để kiểm và để đếm trong inventory.
ARTEFACT_TYPES = (
    "req", "option", "adr", "fact", "passport", "ckm", "pinout", "block_diagram",
    "netlist", "bom", "findings", "plan", "code", "diff", "build", "criteria",
    "sim_result", "analysis", "target", "assumptions", "report", "changeset", "snapshot",
    # Thêm ngoài 22 dòng của §E2 — xem DEV-250:
    "doc",             # tài liệu đã nạp theo trang (§C3 cần, §E2 bảng thiếu)
    "procedure",       # quy trình từng bước (EIDE-NOTE-42)
    "classification",  # kết quả phân loại một tệp (ING-43 §8, khối A3.6)
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # ------------------------------------------------------------------ ghi
    def apply(self, *, artefact_id: str, type: str, op: str, author: str,
              canonical: dict[str, Any], explain: dict[str, Any],
              changeset_id: str | None = None, deps: dict[str, Any] | None = None,
              view_hint: dict[str, Any] | None = None) -> int:
        """Ghi một sự kiện và cập nhật hình chiếu. Trả về version mới.

        Không kiểm `explain` ở đây — việc đó là của hook PreToolUse (N8), để lớp kho
        không phải biết luật trình bày. Kho chỉ biết: không có explain thì không lưu.
        """
        if not explain:
            raise ValueError(f"Hiện vật {artefact_id} không có lớp giải thích (N8).")
        with self._lock:
            cur = self._db.execute(
                "SELECT version, created_at FROM artefacts WHERE id=?", (artefact_id,)
            ).fetchone()
            version = (cur["version"] + 1) if cur else 1
            created = cur["created_at"] if cur else _now()
            ts = _now()
            payload = json.dumps({"canonical": canonical, "explain": explain,
                                  "deps": deps or {}, "view_hint": view_hint or {}},
                                 ensure_ascii=False)
            self._db.execute(
                "INSERT INTO events(ts,changeset_id,author,artefact_id,artefact_type,op,version,payload)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (ts, changeset_id, author, artefact_id, type, op, version, payload))
            self._db.execute(
                "INSERT INTO artefacts(id,type,version,author,created_at,updated_at,changeset_id,"
                "canonical,explain,view_hint,deps,stale,stale_reason,deleted)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,0,NULL,?)"
                " ON CONFLICT(id) DO UPDATE SET version=excluded.version, author=excluded.author,"
                " updated_at=excluded.updated_at, changeset_id=excluded.changeset_id,"
                " canonical=excluded.canonical, explain=excluded.explain, view_hint=excluded.view_hint,"
                " deps=excluded.deps, stale=0, stale_reason=NULL, deleted=excluded.deleted",
                (artefact_id, type, version, author, created, ts, changeset_id,
                 json.dumps(canonical, ensure_ascii=False), json.dumps(explain, ensure_ascii=False),
                 json.dumps(view_hint or {}, ensure_ascii=False),
                 json.dumps(deps or {}, ensure_ascii=False), 1 if op == "delete" else 0))
            self._db.commit()
            return version

    def mark_stale(self, artefact_ids: Iterable[str], reason: str) -> int:
        """§E5.4 — không tự xoá, không tự chạy lại, chỉ đánh dấu và nói lý do."""
        ids = list(artefact_ids)
        if not ids:
            return 0
        with self._lock:
            self._db.executemany("UPDATE artefacts SET stale=1, stale_reason=? WHERE id=?",
                                 [(reason, i) for i in ids])
            self._db.commit()
        return len(ids)

    def accept_stale(self, artefact_id: str, why: str) -> None:
        with self._lock:
            self._db.execute("UPDATE artefacts SET stale=0, stale_reason=? WHERE id=?",
                             (f"chấp nhận STALE: {why}", artefact_id))
            self._db.commit()

    # ------------------------------------------------------------------ đọc
    def get(self, artefact_id: str) -> dict[str, Any] | None:
        r = self._db.execute("SELECT * FROM artefacts WHERE id=? AND deleted=0",
                             (artefact_id,)).fetchone()
        return _row_to_artefact(r) if r else None

    def list(self, type: str | None = None, *, stale_only: bool = False,
             limit: int = 200) -> list[dict[str, Any]]:
        q = "SELECT * FROM artefacts WHERE deleted=0"
        args: list[Any] = []
        if type:
            q += " AND type=?"
            args.append(type)
        if stale_only:
            q += " AND stale=1"
        q += " ORDER BY updated_at DESC LIMIT ?"
        args.append(limit)
        return [_row_to_artefact(r) for r in self._db.execute(q, args)]

    def counts(self) -> dict[str, int]:
        return {r["type"]: r["n"] for r in self._db.execute(
            "SELECT type, COUNT(*) n FROM artefacts WHERE deleted=0 GROUP BY type")}

    def history(self, artefact_id: str) -> list[dict[str, Any]]:
        return [{"seq": r["seq"], "ts": r["ts"], "author": r["author"], "op": r["op"],
                 "version": r["version"], "changeset_id": r["changeset_id"],
                 **json.loads(r["payload"])}
                for r in self._db.execute(
                    "SELECT * FROM events WHERE artefact_id=? ORDER BY version", (artefact_id,))]

    # ------------------------------------------------------------------ Fact
    def put_fact(self, fact: dict[str, Any]) -> None:
        f = dict(fact)
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO facts(fact_id,subject,key,value,unit,vmin,vtyp,vmax,"
                "condition,tier,origin,source,explain,approved_by,approved_at,supersedes,"
                "superseded_by,errata) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f["fact_id"], f["subject"], f["key"], _s(f.get("value")), f.get("unit"),
                 _s(f.get("min")), _s(f.get("typ")), _s(f.get("max")), f.get("condition"),
                 f["tier"], f.get("origin", "extract"),
                 json.dumps(f.get("source", {}), ensure_ascii=False),
                 json.dumps(f.get("explain", {}), ensure_ascii=False),
                 f.get("approved_by"), f.get("approved_at"), f.get("supersedes"),
                 f.get("superseded_by"), 1 if f.get("errata") else 0))
            self._db.commit()

    def query_facts(self, *, subject: str | None = None, key: str | None = None,
                    tier: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        q = "SELECT * FROM facts WHERE superseded_by IS NULL"
        args: list[Any] = []
        if subject:
            q += " AND subject LIKE ?"
            args.append(f"%{subject}%")
        if key:
            q += " AND key LIKE ?"
            args.append(f"%{key}%")
        if tier:
            q += " AND tier=?"
            args.append(tier)
        q += " LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self._db.execute(q, args)]

    def fact_tier_counts(self) -> dict[str, int]:
        return {r["tier"]: r["n"] for r in self._db.execute(
            "SELECT tier, COUNT(*) n FROM facts WHERE superseded_by IS NULL GROUP BY tier")}

    # ------------------------------------------------------------------ dựng lại
    def rebuild(self) -> int:
        """Dựng lại hình chiếu từ `events`. CX16 đòi phát lại tái tạo trạng thái 100 %."""
        with self._lock:
            self._db.execute("DELETE FROM artefacts")
            n = 0
            for r in self._db.execute("SELECT * FROM events ORDER BY seq"):
                p = json.loads(r["payload"])
                self._db.execute(
                    "INSERT INTO artefacts(id,type,version,author,created_at,updated_at,"
                    "changeset_id,canonical,explain,view_hint,deps,stale,stale_reason,deleted)"
                    " VALUES(?,?,?,?,?,?,?,?,?,?,?,0,NULL,?)"
                    " ON CONFLICT(id) DO UPDATE SET version=excluded.version,"
                    " author=excluded.author, updated_at=excluded.updated_at,"
                    " changeset_id=excluded.changeset_id, canonical=excluded.canonical,"
                    " explain=excluded.explain, deps=excluded.deps, deleted=excluded.deleted",
                    (r["artefact_id"], r["artefact_type"], r["version"], r["author"], r["ts"],
                     r["ts"], r["changeset_id"],
                     json.dumps(p["canonical"], ensure_ascii=False),
                     json.dumps(p["explain"], ensure_ascii=False),
                     json.dumps(p.get("view_hint", {}), ensure_ascii=False),
                     json.dumps(p.get("deps", {}), ensure_ascii=False),
                     1 if r["op"] == "delete" else 0))
                n += 1
            self._db.commit()
            return n


def _s(v: Any) -> str | None:
    return None if v is None else str(v)


def _row_to_artefact(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"], "type": r["type"], "version": r["version"], "author": r["author"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
        "changeset_id": r["changeset_id"],
        "canonical": json.loads(r["canonical"]), "explain": json.loads(r["explain"]),
        "view_hint": json.loads(r["view_hint"] or "{}"), "deps": json.loads(r["deps"] or "{}"),
        "stale": bool(r["stale"]), "stale_reason": r["stale_reason"],
    }
