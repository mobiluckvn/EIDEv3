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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

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

# --------------------------------------------------------------------------- CKM (§C2)
# "Lưu: KG (SQLite nodes/edges) + bảng Fact truy vấn xác định + chỉ mục RAG theo trang."
#
# Hai bảng thay vì một bảng cho mỗi thực thể, vì §C2 liệt kê chín loại thực thể và chín
# loại quan hệ, và danh sách đó sẽ còn dài ra (bus mới, ràng buộc mới). Một lược đồ đồ
# thị chịu được việc thêm loại mà không cần migration; chín bảng thì không.
#
# Điều đáng nói nhất ở đây là `ux_ckm_duoc_gan`. §C2 viết quan hệ ĐƯỢC_GÁN kèm chữ
# "(duy nhất)". Đó là một bất biến vật lý: một chân chip làm được đúng MỘT chức năng tại
# một thời điểm. Nếu để phần mềm nhớ luật đó, thì mỗi đường ghi mới là một cơ hội quên.
# Nên luật nằm trong CHỈ MỤC: SQLite từ chối bản ghi thứ hai, kể cả khi lời nhắc, mô
# hình, và người viết tool đều sai. Đây đúng chỗ N1/N3 muốn luật nằm.
SCHEMA_CKM = """
CREATE TABLE IF NOT EXISTS ckm_nodes (
    node_id    TEXT PRIMARY KEY,          -- "chip:ATmega328P@1.0.0" | "pin:U1.28" | "net:SDA"
    loai       TEXT NOT NULL,             -- chip | pin | net | module | bus | rail | …
    ten        TEXT NOT NULL,
    canonical  TEXT NOT NULL,             -- JSON: thuộc tính của thực thể
    tier       TEXT,                      -- tầng tin cậy của thực thể này, nếu có
    nguon      TEXT,                      -- JSON: fact_id / doc / lời người
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ckm_node_loai ON ckm_nodes(loai);

CREATE TABLE IF NOT EXISTS ckm_edges (
    edge_id    TEXT PRIMARY KEY,          -- "<loai>:<tu>→<den>"
    loai       TEXT NOT NULL,             -- CO_CHAN | NOI | DUOC_GAN | GOM | …
    tu         TEXT NOT NULL,
    den        TEXT NOT NULL,
    canonical  TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ckm_edge_tu  ON ckm_edges(loai, tu);
CREATE INDEX IF NOT EXISTS ix_ckm_edge_den ON ckm_edges(loai, den);

-- ĐƯỢC_GÁN (duy nhất) — §C2. Luật nằm trong kho, không nằm trong lời nhắc.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ckm_duoc_gan
    ON ckm_edges(tu) WHERE loai = 'DUOC_GAN';
"""

# ----------------------------------------------------------------------- cây khối (HIER-45)
# EIDE-HIER-45 §2.3. Cộng thêm, có `down()` (HIER-15).
#
# Tài liệu viết `ALTER TABLE module ADD COLUMN parent_id` — nhưng ở đây **không có bảng
# `module`**: module là một hàng trong `ckm_nodes` cùng với net, chân, chip. Nên bốn cột
# của §2.3 thành bốn cột của `ckm_nodes`, còn `port`/`connection` thành bảng riêng đúng
# như tài liệu — vì Port có ràng buộc `UNIQUE(module_id, name)` mà lược đồ đồ thị không
# giữ được, và một Port trùng tên trong cùng khối là một cái hợp đồng có hai nghĩa.
#
# Một quyết định đáng nói: **`parent_id` dùng cho MỌI loại nút, không riêng module.**
#
#   khối → cha của nó          net  → khối SỞ HỮU net (scope của §2.2)
#   Port → khối có Port đó     chân → lá có chân đó
#
# §2.3 tách chúng thành `module.parent_id` và `net.scope_module_id`, nhưng cả hai là cùng
# một quan hệ: "nút này nằm trong nút nào". Một cột thì `path` tính được cho mọi thứ bằng
# một hàm, cây đi lên bằng một truy vấn, và không có chỗ nào để hai cột lệch nhau.
SCHEMA_CAY_BANG = """
CREATE INDEX IF NOT EXISTS ix_ckm_node_cha ON ckm_nodes(parent_id);

-- Tên đầy đủ là duy nhất (§2.2 mục 4). Partial index: nút chưa có path thì không bị chặn.
CREATE UNIQUE INDEX IF NOT EXISTS ux_ckm_path
    ON ckm_nodes(path) WHERE path IS NOT NULL;

CREATE TABLE IF NOT EXISTS ckm_port (
    port_id     TEXT PRIMARY KEY,          -- "port:/board/mcu.I2C0"
    module_id   TEXT NOT NULL,
    ten         TEXT NOT NULL,
    huong       TEXT NOT NULL,             -- in|out|bidir|power_in|power_out|passive
    loai        TEXT NOT NULL,             -- single|bus
    members     TEXT NOT NULL DEFAULT '[]',
    rang_buoc   TEXT NOT NULL DEFAULT '{}',
    fact_refs   TEXT NOT NULL DEFAULT '[]',
    chan        TEXT,                      -- Port của LÁ: số chân nó đại diện
    updated_at  TEXT NOT NULL,
    UNIQUE(module_id, ten)
);
CREATE INDEX IF NOT EXISTS ix_ckm_port_module ON ckm_port(module_id);

CREATE TABLE IF NOT EXISTS ckm_connection (
    net_id      TEXT NOT NULL,
    port_id     TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (net_id, port_id)
);
CREATE INDEX IF NOT EXISTS ix_ckm_conn_port ON ckm_connection(port_id);
"""

COT_CAY = ("parent_id", "kind", "path", "lib_ref")


def _them_cot_cay(db: sqlite3.Connection) -> None:
    """Thêm bốn cột cây, bỏ qua cột đã có.

    `ALTER TABLE ADD COLUMN` không có dạng `IF NOT EXISTS`, nên viết nó thành SQL thuần
    sẽ phá luật của chính tệp này: *"up phải chạy lại được nhiều lần mà không hỏng"*. Luật
    đó không phải hình thức — nó là thứ cho phép chạy `nang_cap()` trên một kho không biết
    đang ở đâu mà không phải cầu nguyện. Nên phần cột đi qua `PRAGMA table_info`.
    """
    co = {r[1] for r in db.execute("PRAGMA table_info(ckm_nodes)")}
    for c in COT_CAY:
        if c not in co:
            db.execute(f"ALTER TABLE ckm_nodes ADD COLUMN {c} TEXT")
    db.executescript(SCHEMA_CAY_BANG)


def _go_cot_cay(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMA_CAY_BANG_DOWN)
    co = {r[1] for r in db.execute("PRAGMA table_info(ckm_nodes)")}
    for c in reversed(COT_CAY):
        if c in co:
            db.execute(f"ALTER TABLE ckm_nodes DROP COLUMN {c}")


# `down()` gỡ ĐÚNG thứ `up` thêm, không chạm dữ liệu có trước (SCH-18). Netlist phẳng nằm
# trong hiện vật `netlist:CKM`, không nằm ở đây — nên gỡ cây KHÔNG làm mất mạch đã vẽ.
SCHEMA_CAY_BANG_DOWN = """
DROP INDEX IF EXISTS ix_ckm_conn_port;
DROP TABLE IF EXISTS ckm_connection;
DROP INDEX IF EXISTS ix_ckm_port_module;
DROP TABLE IF EXISTS ckm_port;
DROP INDEX IF EXISTS ux_ckm_path;
DROP INDEX IF EXISTS ix_ckm_node_cha;
"""


# EIDE-SCH-44 §2.1 lop bao ve so 4: "Store: bang moi sch_sheets (id, version, path,
# lib_versions, layout_hash, explain)". Bang nay la **so dang ky sheet**: moi lan `sch.write`
# ghi mot sheet, mot dong duoc ghi vao day.
#
# Vi sao can mot bang rieng thay vi mot hien vat JSON: bang uy ban ung y (§E6) phai goi duoc
# so do vao snapshot, va no can biet DUNG danh sach tep + hash bo cuc + phien ban thu vien ky
# hieu cua lan ghi do. Nhet cai do vao mot hien vat thi moi lan ghi lai mot sheet la mot lan
# ghi lai ca danh sach — va hai sheet ghi o hai luot se de len nhau.
SCHEMA_SCH = """
CREATE TABLE IF NOT EXISTS sch_sheets (
    id            TEXT PRIMARY KEY,        -- "sheet:/board/mcu"
    version       INTEGER NOT NULL,        -- tang moi lan ghi lai sheet do
    path          TEXT NOT NULL,           -- duong dan khoi trong cay ("" = trang phang)
    tep           TEXT NOT NULL,           -- ten tep .kicad_sch tuong doi du an
    lib_versions  TEXT NOT NULL DEFAULT '{}',
    layout_hash   TEXT NOT NULL DEFAULT '',
    explain       TEXT NOT NULL DEFAULT '{}',
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sch_sheet_path ON sch_sheets(path);
"""

SCHEMA_SCH_DOWN = """
DROP INDEX IF EXISTS ix_sch_sheet_path;
DROP TABLE IF EXISTS sch_sheets;
"""


# --------------------------------------------------------------------------- migration
# EIDE-SCH-44 §2.1 lop bao ve so 4 va SCH-18: "luoc do chi cong them; migration co
# kiem tra nguoc (down)".
#
# Vi sao can, bang mot cau: `CREATE TABLE IF NOT EXISTS` bien MOI thay doi luoc do thanh
# mot thay doi **khong quay lai duoc**. Them mot bang xong, muon go ra thi khong co
# duong nao ngoai sua tay tren kho cua nguoi dung. `user_version` cho ta biet dang o
# dau, va `down` cho ta duong lui.
#
# Quy tac cho moi migration them sau:
#   - `up` phai chay lai duoc nhieu lan ma khong hong (IF NOT EXISTS / IF EXISTS);
#   - `down` chi go DUNG thu `up` them vao, khong dung toi du lieu co truoc;
#   - phien ban 1 la luoc do goc, nen `down` cua no la xoa sach — chi dung khi go han
#     ca kho, va `ha_cap` tu choi neu khong duoc noi ro (xem `cho_phep_xoa_goc`).


@dataclass(slots=True)
class Migration:
    """Một bậc lược đồ. `up`/`down` là SQL, **hoặc** một hàm nhận connection.

    Cần dạng hàm vì `ALTER TABLE ADD COLUMN` không có `IF NOT EXISTS`: viết nó thành SQL
    thuần thì migration mất tính chạy-lại-được, và một kho không biết đang ở đâu sẽ nổ
    thay vì tự sửa. Xem `_them_cot_cay`.
    """

    phien_ban: int
    mo_ta: str
    up: "str | Callable[[sqlite3.Connection], None]"
    down: "str | Callable[[sqlite3.Connection], None]"


MIGRATIONS: list[Migration] = [
    Migration(
        phien_ban=1,
        mo_ta="lược đồ gốc: events (event-sourcing) + artefacts (hình chiếu) + facts",
        up=SCHEMA,
        down=(
            "DROP INDEX IF EXISTS ix_fact_tier; DROP INDEX IF EXISTS ix_fact_subject;"
            "DROP TABLE IF EXISTS facts;"
            "DROP INDEX IF EXISTS ix_art_stale; DROP INDEX IF EXISTS ix_art_type;"
            "DROP TABLE IF EXISTS artefacts;"
            "DROP INDEX IF EXISTS ix_events_cs; DROP INDEX IF EXISTS ix_events_artefact;"
            "DROP TABLE IF EXISTS events;"
        ),
    ),
    Migration(
        phien_ban=2,
        mo_ta="Bản đồ tri thức mạch (CKM) — MDD-40 §C2: KG nodes/edges",
        up=SCHEMA_CKM,
        down=(
            "DROP INDEX IF EXISTS ux_ckm_duoc_gan;"
            "DROP INDEX IF EXISTS ix_ckm_edge_den; DROP INDEX IF EXISTS ix_ckm_edge_tu;"
            "DROP TABLE IF EXISTS ckm_edges;"
            "DROP INDEX IF EXISTS ix_ckm_node_loai;"
            "DROP TABLE IF EXISTS ckm_nodes;"
        ),
    ),
    Migration(
        phien_ban=3,
        mo_ta="Cây khối phân cấp — HIER-45 §2.3: parent/kind/path/lib_ref + Port + Connection",
        up=_them_cot_cay,
        down=_go_cot_cay,
    ),
    Migration(
        phien_ban=4,
        mo_ta="Sổ đăng ký sheet sơ đồ — SCH-44 §2.1(4): sch_sheets + layout_hash + lib_versions",
        up=SCHEMA_SCH,
        down=SCHEMA_SCH_DOWN,
    ),
]

SCHEMA_VERSION = MIGRATIONS[-1].phien_ban

# Các loại hiện vật có trong §E2 (22 dòng bảng) — dùng để kiểm và để đếm trong inventory.
ARTEFACT_TYPES = (
    "req", "option", "adr", "fact", "passport", "ckm", "pinout", "block_diagram",
    "netlist", "bom", "findings", "plan", "code", "diff", "build", "criteria",
    "sim_result", "analysis", "target", "assumptions", "report", "changeset", "snapshot",
    # Thêm ngoài 22 dòng của §E2 — xem DEV-250:
    "doc",             # tài liệu đã nạp theo trang (§C3 cần, §E2 bảng thiếu)
    "procedure",       # quy trình từng bước (EIDE-NOTE-42)
    "classification",  # kết quả phân loại một tệp (ING-43 §8, khối A3.6)
    # SCH-44 §3.1 — hiện vật của đường ống sinh sơ đồ. Cộng thêm; cờ tắt thì không ai ghi.
    "skidl_src", "netlist_kicad", "symbol_map", "layout", "symbol_lib",
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
        self.nang_cap()

    def close(self) -> None:
        self._db.close()

    # ------------------------------------------------------------------ lược đồ
    @property
    def phien_ban_luoc_do(self) -> int:
        return int(self._db.execute("PRAGMA user_version").fetchone()[0])

    def nang_cap(self, den: int | None = None) -> list[int]:
        """Áp các migration còn thiếu. Trả về danh sách phiên bản đã áp."""
        dich = SCHEMA_VERSION if den is None else den
        da_ap: list[int] = []
        for m in MIGRATIONS:
            if self.phien_ban_luoc_do >= m.phien_ban or m.phien_ban > dich:
                continue
            with self._lock:
                self._ap(m.up)
                self._db.execute(f"PRAGMA user_version = {m.phien_ban}")
                self._db.commit()
            da_ap.append(m.phien_ban)
        return da_ap

    def _ap(self, buoc: "str | Callable[[sqlite3.Connection], None]") -> None:
        if callable(buoc):
            buoc(self._db)
        else:
            self._db.executescript(buoc)

    def ha_cap(self, den: int, *, cho_phep_xoa_goc: bool = False) -> list[int]:
        """Gỡ ngược các migration cho tới phiên bản `den` — SCH-18.

        Hạ xuống 0 nghĩa là xoá sạch ba bảng gốc, tức xoá kho. Việc đó phải được nói ra
        bằng `cho_phep_xoa_goc=True`; mặc định từ chối, vì một lệnh gỡ tính năng không
        được phép vô tình xoá cả dự án.
        """
        if den < 1 and not cho_phep_xoa_goc:
            raise ValueError(
                "Hạ lược đồ xuống 0 sẽ xoá toàn bộ kho hiện vật. Nếu thật sự muốn, "
                "gọi lại với cho_phep_xoa_goc=True.")
        da_go: list[int] = []
        for m in reversed(MIGRATIONS):
            if m.phien_ban <= den or self.phien_ban_luoc_do < m.phien_ban:
                continue
            with self._lock:
                self._ap(m.down)
                self._db.execute(f"PRAGMA user_version = {m.phien_ban - 1}")
                self._db.commit()
            da_go.append(m.phien_ban)
        return da_go

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

    # ------------------------------------------------------------------ CKM (§C2)
    def ckm_dat_nut(self, *, node_id: str, loai: str, ten: str,
                    canonical: dict[str, Any], tier: str | None = None,
                    nguon: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO ckm_nodes(node_id,loai,ten,canonical,tier,nguon,updated_at)"
                " VALUES(?,?,?,?,?,?,?)"
                " ON CONFLICT(node_id) DO UPDATE SET loai=excluded.loai, ten=excluded.ten,"
                " canonical=excluded.canonical, tier=excluded.tier, nguon=excluded.nguon,"
                " updated_at=excluded.updated_at",
                (node_id, loai, ten, json.dumps(canonical, ensure_ascii=False), tier,
                 json.dumps(nguon or {}, ensure_ascii=False), _now()))
            self._db.commit()

    def ckm_dat_canh(self, *, loai: str, tu: str, den: str,
                     canonical: dict[str, Any] | None = None) -> str:
        """Ghi một quan hệ. `sqlite3.IntegrityError` ở đây là ĐƯỢC_GÁN bị gán hai lần —
        người gọi phải bắt và biến thành lỗi có hướng dẫn, không được để nó chết trần."""
        eid = f"{loai}:{tu}→{den}"
        with self._lock:
            self._db.execute(
                "INSERT INTO ckm_edges(edge_id,loai,tu,den,canonical,updated_at)"
                " VALUES(?,?,?,?,?,?)"
                " ON CONFLICT(edge_id) DO UPDATE SET canonical=excluded.canonical,"
                " updated_at=excluded.updated_at",
                (eid, loai, tu, den, json.dumps(canonical or {}, ensure_ascii=False), _now()))
            self._db.commit()
        return eid

    def ckm_xoa_canh(self, *, loai: str, tu: str, den: str | None = None) -> int:
        with self._lock:
            if den is None:
                cur = self._db.execute("DELETE FROM ckm_edges WHERE loai=? AND tu=?",
                                       (loai, tu))
            else:
                cur = self._db.execute(
                    "DELETE FROM ckm_edges WHERE loai=? AND tu=? AND den=?", (loai, tu, den))
            self._db.commit()
            return cur.rowcount

    def ckm_nut(self, node_id: str) -> dict[str, Any] | None:
        r = self._db.execute("SELECT * FROM ckm_nodes WHERE node_id=?", (node_id,)).fetchone()
        return _row_to_nut(r) if r else None

    def ckm_cac_nut(self, *, loai: str | None = None, tien_to: str | None = None,
                    limit: int = 2000) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM ckm_nodes WHERE 1=1", []
        if loai:
            q += " AND loai=?"
            args.append(loai)
        if tien_to:
            q += " AND node_id LIKE ?"
            args.append(f"{tien_to}%")
        q += " ORDER BY node_id LIMIT ?"
        args.append(limit)
        return [_row_to_nut(r) for r in self._db.execute(q, args)]

    def ckm_cac_canh(self, *, loai: str | None = None, tu: str | None = None,
                     den: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM ckm_edges WHERE 1=1", []
        for cot, gt in (("loai", loai), ("tu", tu), ("den", den)):
            if gt:
                q += f" AND {cot}=?"
                args.append(gt)
        q += " ORDER BY edge_id LIMIT ?"
        args.append(limit)
        return [{"edge_id": r["edge_id"], "loai": r["loai"], "tu": r["tu"], "den": r["den"],
                 "canonical": json.loads(r["canonical"] or "{}")}
                for r in self._db.execute(q, args)]

    # ------------------------------------------------------------------ cây (HIER-45)
    def ckm_dat_cay(self, node_id: str, *, parent_id: str | None, kind: str,
                    path: str, lib_ref: str | None = None) -> None:
        """Đặt vị trí của một nút trong cây. Nút phải đã tồn tại."""
        with self._lock:
            self._db.execute(
                "UPDATE ckm_nodes SET parent_id=?, kind=?, path=?, lib_ref=?, updated_at=?"
                " WHERE node_id=?",
                (parent_id, kind, path, lib_ref, _now(), node_id))
            self._db.commit()

    def ckm_con(self, parent_id: str, *, kind: str | None = None) -> list[dict[str, Any]]:
        q = "SELECT * FROM ckm_nodes WHERE parent_id=?"
        args: list[Any] = [parent_id]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        return [_row_to_nut(r) for r in self._db.execute(q + " ORDER BY node_id", args)]

    def ckm_goc(self) -> dict[str, Any] | None:
        r = self._db.execute(
            "SELECT * FROM ckm_nodes WHERE kind='board' ORDER BY node_id LIMIT 1").fetchone()
        return _row_to_nut(r) if r else None

    def ckm_dat_port(self, *, port_id: str, module_id: str, ten: str, huong: str,
                     loai: str = "single", members: list[str] | None = None,
                     rang_buoc: dict[str, Any] | None = None,
                     fact_refs: list[str] | None = None, chan: str | None = None) -> None:
        """Ghi một Port. `UNIQUE(module_id, ten)` của kho chặn Port trùng tên trong khối —
        một hợp đồng có hai nghĩa thì không còn là hợp đồng."""
        with self._lock:
            self._db.execute(
                "INSERT INTO ckm_port(port_id,module_id,ten,huong,loai,members,rang_buoc,"
                "fact_refs,chan,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(port_id) DO UPDATE SET module_id=excluded.module_id,"
                " ten=excluded.ten, huong=excluded.huong, loai=excluded.loai,"
                " members=excluded.members, rang_buoc=excluded.rang_buoc,"
                " fact_refs=excluded.fact_refs, chan=excluded.chan,"
                " updated_at=excluded.updated_at",
                (port_id, module_id, ten, huong, loai,
                 json.dumps(members or [], ensure_ascii=False),
                 json.dumps(rang_buoc or {}, ensure_ascii=False),
                 json.dumps(fact_refs or [], ensure_ascii=False), chan, _now()))
            self._db.commit()

    def ckm_cac_port(self, *, module_id: str | None = None,
                     port_id: str | None = None) -> list[dict[str, Any]]:
        q, args = "SELECT * FROM ckm_port WHERE 1=1", []
        if module_id:
            q += " AND module_id=?"
            args.append(module_id)
        if port_id:
            q += " AND port_id=?"
            args.append(port_id)
        return [{"port_id": r["port_id"], "module_id": r["module_id"], "ten": r["ten"],
                 "huong": r["huong"], "loai": r["loai"],
                 "members": json.loads(r["members"] or "[]"),
                 "rang_buoc": json.loads(r["rang_buoc"] or "{}"),
                 "fact_refs": json.loads(r["fact_refs"] or "[]"), "chan": r["chan"]}
                for r in self._db.execute(q + " ORDER BY port_id", args)]

    def ckm_noi(self, *, net_id: str, port_id: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO ckm_connection(net_id,port_id,updated_at)"
                " VALUES(?,?,?)", (net_id, port_id, _now()))
            self._db.commit()

    def ckm_xoa_noi(self, *, net_id: str | None = None,
                    port_id: str | None = None) -> int:
        """Gỡ kết nối. Không nhận cả hai None — xoá sạch bảng phải nói ra bằng
        `ckm_xoa_het()`, không lọt qua một lời gọi thiếu tham số."""
        if net_id is None and port_id is None:
            raise ValueError("ckm_xoa_noi cần ít nhất net_id hoặc port_id.")
        q, args = "DELETE FROM ckm_connection WHERE 1=1", []
        if net_id:
            q += " AND net_id=?"
            args.append(net_id)
        if port_id:
            q += " AND port_id=?"
            args.append(port_id)
        with self._lock:
            cur = self._db.execute(q, args)
            self._db.commit()
            return cur.rowcount

    def ckm_cac_noi(self, *, net_id: str | None = None,
                    port_id: str | None = None) -> list[dict[str, str]]:
        q, args = "SELECT net_id, port_id FROM ckm_connection WHERE 1=1", []
        if net_id:
            q += " AND net_id=?"
            args.append(net_id)
        if port_id:
            q += " AND port_id=?"
            args.append(port_id)
        return [{"net_id": r["net_id"], "port_id": r["port_id"]}
                for r in self._db.execute(q + " ORDER BY net_id, port_id", args)]

    def ckm_xoa_het(self) -> None:
        """Xoá sạch đồ thị để dựng lại từ hiện vật. An toàn vì đồ thị là hình chiếu —
        xem `knowledge/ckm.chieu()`. Không được gọi từ chỗ nào khác."""
        with self._lock:
            self._db.execute("DELETE FROM ckm_connection")
            self._db.execute("DELETE FROM ckm_port")
            self._db.execute("DELETE FROM ckm_edges")
            self._db.execute("DELETE FROM ckm_nodes")
            self._db.commit()

    # ------------------------------------------------------- sổ đăng ký sheet sơ đồ (SCH-44)
    def sch_dat_sheet(self, *, path: str, tep: str, lib_versions: dict[str, Any],
                      layout_hash: str, explain: dict[str, Any]) -> int:
        """Ghi/cập nhật một sheet, trả về `version` mới.

        `version` tăng mỗi lần sheet đó được ghi lại — đó là thứ cho phép một bản ưng ý nói
        "sơ đồ lúc ấy là bản 3 của sheet này", chứ không chỉ "có một tệp tên thế".

        Bốn trường sau đều **bắt buộc** và mỗi lần ghi là ghi cả dòng: chúng mô tả LẦN GHI vừa
        xảy ra, nên một mặc định rỗng sẽ xoá thông tin của lần trước, còn "giữ giá trị cũ" thì
        để lại một `layout_hash` nói về một bố cục không còn tồn tại. Cả hai đều tệ hơn việc
        buộc bên gọi nói ra.
        """
        # Khoá theo TỆP, không theo path khối: một tệp là một thứ mà bản ưng ý gói và khôi
        # phục. Bản đầu khoá theo path, nên ghi `flat` rồi ghi `hierarchical` để lại HAI dòng
        # trỏ vào cùng `sch/mach.kicad_sch` (path "" và path "/board") — và bản ưng ý gói tệp
        # đó hai lần trong khi nói rằng nó có 8 sheet.
        sid = f"sheet:{tep}"
        with self._lock:
            cu = self._db.execute("SELECT version FROM sch_sheets WHERE id = ?",
                                  (sid,)).fetchone()
            v = int(cu["version"]) + 1 if cu else 1
            self._db.execute(
                "INSERT INTO sch_sheets (id, version, path, tep, lib_versions, layout_hash,"
                " explain, updated_at) VALUES (?,?,?,?,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET version=excluded.version,"
                " tep=excluded.tep, lib_versions=excluded.lib_versions,"
                " layout_hash=excluded.layout_hash, explain=excluded.explain,"
                " updated_at=excluded.updated_at",
                (sid, v, path or "", tep,
                 json.dumps(lib_versions or {}, ensure_ascii=False), layout_hash,
                 json.dumps(explain or {}, ensure_ascii=False), _now()))
            self._db.commit()
        return v

    def sch_cac_sheet(self) -> list[dict[str, Any]]:
        return [{"id": r["id"], "version": r["version"], "path": r["path"],
                 "tep": r["tep"], "lib_versions": json.loads(r["lib_versions"]),
                 "layout_hash": r["layout_hash"], "explain": json.loads(r["explain"]),
                 "updated_at": r["updated_at"]}
                for r in self._db.execute(
                    "SELECT * FROM sch_sheets ORDER BY path, id")]

    def sch_xoa_sheet_ngoai(self, tep_con_lai: list[str]) -> int:
        """Xoá dòng của sheet KHÔNG còn trong gói vừa ghi.

        Đổi từ 5 khối xuống 3 thì hai tệp sheet biến mất; để dòng cũ lại thì bản ưng ý sau đó
        gói theo hai tệp không tồn tại, và "khôi phục được" thành một lời hứa suông.
        """
        giu = set(tep_con_lai)
        with self._lock:
            xoa = [r["id"] for r in self._db.execute("SELECT id, tep FROM sch_sheets")
                   if r["tep"] not in giu]
            for i in xoa:
                self._db.execute("DELETE FROM sch_sheets WHERE id = ?", (i,))
            self._db.commit()
        return len(xoa)

    def ckm_dem(self) -> dict[str, int]:
        d = {r["loai"]: r["n"] for r in self._db.execute(
            "SELECT loai, COUNT(*) n FROM ckm_nodes GROUP BY loai")}
        for r in self._db.execute("SELECT loai, COUNT(*) n FROM ckm_edges GROUP BY loai"):
            d[r["loai"]] = r["n"]
        for ten, sql in (("port", "SELECT COUNT(*) n FROM ckm_port"),
                         ("connection", "SELECT COUNT(*) n FROM ckm_connection")):
            n = self._db.execute(sql).fetchone()["n"]
            if n:
                d[ten] = n
        for r in self._db.execute(
                "SELECT kind, COUNT(*) n FROM ckm_nodes WHERE kind IS NOT NULL GROUP BY kind"):
            d[f"kind:{r['kind']}"] = r["n"]
        return d

    # ------------------------------------------------------------------ dựng lại
    def rebuild(self) -> int:
        """Dựng lại hình chiếu từ `events`. CX16 đòi phát lại tái tạo trạng thái 100 %.

        Dựng lại bảng `artefacts` thôi. Bản đồ mạch (`ckm_nodes/ckm_edges`) là hình chiếu
        của *hiện vật*, một lớp nữa ở trên — người gọi phải gọi `knowledge.ckm.chieu()`
        sau. Kho không tự gọi vì kho không được biết gì về tri thức mạch.
        """
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


def _row_to_nut(r: sqlite3.Row) -> dict[str, Any]:
    d = {"node_id": r["node_id"], "loai": r["loai"], "ten": r["ten"],
         "canonical": json.loads(r["canonical"] or "{}"), "tier": r["tier"],
         "nguon": json.loads(r["nguon"] or "{}")}
    # Bốn cột cây chỉ có từ lược đồ v3. Kho đã hạ cấp vẫn đọc được — `sqlite3.Row` không
    # có `.get`, nên phải hỏi `keys()`; thiếu thì trả None chứ không nổ.
    co = set(r.keys())
    for c in ("parent_id", "kind", "path", "lib_ref"):
        d[c] = r[c] if c in co else None
    return d


def _row_to_artefact(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": r["id"], "type": r["type"], "version": r["version"], "author": r["author"],
        "created_at": r["created_at"], "updated_at": r["updated_at"],
        "changeset_id": r["changeset_id"],
        "canonical": json.loads(r["canonical"]), "explain": json.loads(r["explain"]),
        "view_hint": json.loads(r["view_hint"] or "{}"), "deps": json.loads(r["deps"] or "{}"),
        "stale": bool(r["stale"]), "stale_reason": r["stale_reason"],
    }
