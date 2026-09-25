# -*- coding: utf-8 -*-
"""Changeset — đơn vị thay đổi. EIDE-MDD-40 §E5, nguyên tắc N9.

    "Mọi thay đổi — của người hay tác tử — là một changeset hoàn tác được; lịch sử
     không bị xoá; sửa của người được tác tử biết và nhắc tới ở lượt sau."

Hai câu trong §E5.1 quyết định toàn bộ thiết kế của tệp này:

  - "Mỗi lời gọi tool ghi hiện vật = một changeset; mỗi HumanAct edit = một changeset.
     **Không có thay đổi nào ngoài changeset** (tool ghi thẳng bị hook từ chối)."
  - "Hoàn tác không xoá lịch sử (append-only)."

Từ đó suy ra ba thứ không được thoả hiệp:

1. **Phép nghịch đảo phải sinh cùng lúc với phép thuận.** Sinh sau là đã muộn: lúc đó
   trạng thái cũ có thể không còn ai biết. Kho lưu `canonical` bản trước ngay trong
   `inverse`, tệp lưu sha commit — hai cách, cùng một ý.

2. **Hoàn tác tạo changeset MỚI**, không xoá cái cũ (§E5.2). Nghĩa là hoàn tác của
   hoàn tác cũng hoàn tác được, và dòng thời gian không bao giờ có lỗ.

3. **Có thứ không hoàn tác được** (§E5.3: flash, option bytes, cài công cụ). Changeset
   vẫn được ghi, mang `reversible=false` kèm lý do bằng tiếng Việt cho người đọc —
   chứ không phải im lặng bỏ qua. Ca CX11 đo đúng chuyện này.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Loại thao tác trên một hiện vật.
OPS = ("create", "update", "delete", "restore")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class Touch:
    """Một hiện vật bị chạm trong changeset này."""

    artefact_id: str
    type: str
    op: str
    from_version: int | None = None
    to_version: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"artefact_id": self.artefact_id, "type": self.type, "op": self.op,
                "from_version": self.from_version, "to_version": self.to_version}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Touch":
        return cls(d["artefact_id"], d["type"], d["op"],
                   d.get("from_version"), d.get("to_version"))


@dataclass(slots=True)
class Changeset:
    """§E5.1 — cấu trúc lấy nguyên từ tài liệu."""

    id: str
    ts: str
    author: str                                  # "human" | "agent:run-43"
    run_id: str | None = None
    human_act_id: str | None = None
    tool_call_id: str | None = None
    touches: list[Touch] = field(default_factory=list)
    forward: list[dict[str, Any]] = field(default_factory=list)
    inverse: list[dict[str, Any]] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)
    reversible: bool = True
    irreversible_reason: str | None = None
    stale_marked: list[str] = field(default_factory=list)
    acknowledged_by_agent: str | None = None
    snapshot_id: str | None = None
    note: str | None = None                      # "vì sao" của người (§E4 bước 1)
    undoes: str | None = None                    # changeset này hoàn tác cái nào
    undone_by: str | None = None

    @property
    def by_human(self) -> bool:
        return self.author == "human"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "ts": self.ts, "author": self.author, "run_id": self.run_id,
            "human_act_id": self.human_act_id, "tool_call_id": self.tool_call_id,
            "touches": [t.to_dict() for t in self.touches],
            "forward": self.forward, "inverse": self.inverse, "explain": self.explain,
            "reversible": self.reversible, "irreversible_reason": self.irreversible_reason,
            "stale_marked": self.stale_marked,
            "acknowledged_by_agent": self.acknowledged_by_agent,
            "snapshot_id": self.snapshot_id, "note": self.note,
            "undoes": self.undoes, "undone_by": self.undone_by,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Changeset":
        return cls(
            id=d["id"], ts=d["ts"], author=d["author"], run_id=d.get("run_id"),
            human_act_id=d.get("human_act_id"), tool_call_id=d.get("tool_call_id"),
            touches=[Touch.from_dict(t) for t in d.get("touches", [])],
            forward=d.get("forward", []), inverse=d.get("inverse", []),
            explain=d.get("explain", {}), reversible=d.get("reversible", True),
            irreversible_reason=d.get("irreversible_reason"),
            stale_marked=d.get("stale_marked", []),
            acknowledged_by_agent=d.get("acknowledged_by_agent"),
            snapshot_id=d.get("snapshot_id"), note=d.get("note"),
            undoes=d.get("undoes"), undone_by=d.get("undone_by"))

    # ------------------------------------------------------------------ hiển thị
    def tom_tat(self) -> str:
        """Dòng cho tab Lịch sử — §E2 dòng "Changeset"."""
        ai = "Anh" if self.by_human else f"Tác tử ({self.run_id})"
        gi = self.explain.get("summary") or ", ".join(
            f"{t.op} {t.artefact_id}" for t in self.touches[:3])
        return f"{ai}: {gi}"

    def ly_do_khong_hoan_tac(self) -> str | None:
        return None if self.reversible else (
            self.irreversible_reason or "thao tác đã tác động ra ngoài máy")


# =========================================================================== sổ changeset
GENESIS = "0" * 64


class ChangesetLog:
    """`changesets.jsonl` — append-only, là chỉ mục chung cho cả kho và git (§E5.1).

    Vì sao có tệp riêng thay vì chỉ dùng sổ cái: sổ cái ghi *mọi thứ đã xảy ra* (kể cả
    lời gọi mô hình, lệnh giao diện); sổ changeset chỉ ghi *cái gì đã đổi*. Tab Lịch sử,
    hoàn tác và snapshot đều đọc cái thứ hai, và nó phải đọc nhanh mà không phải lọc
    qua hàng nghìn sự kiện không liên quan.

    Sửa tại chỗ chỉ được phép cho hai trường đánh dấu (`acknowledged_by_agent`,
    `undone_by`) — chúng ghi lại một sự kiện xảy ra SAU, và §E5.2 vẫn đúng vì không
    có nội dung thay đổi nào bị xoá.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._head = self._doc_hash_cuoi()

    # ------------------------------------------------------------------ chuỗi hash
    # MEM-42 §12 và MEM-18. Sổ cái đã có chuỗi hash từ G1; sổ changeset thì chưa — mà
    # nó mới là thứ hoàn tác và snapshot đọc. Một dòng bị sửa ở giữa mà không ai biết
    # nghĩa là "hoàn tác không xoá lịch sử" mất luôn cơ sở để nói.
    #
    # Chỉ băm phần NỘI DUNG (bỏ hai trường đánh dấu sau: `acknowledged_by_agent`,
    # `undone_by`), vì hai trường đó được phép sửa tại chỗ theo §E5.2 — băm cả chúng
    # thì chuỗi vỡ mỗi lần tác tử nhắc tới một thay đổi của người.
    _BO_QUA_KHI_BAM = ("acknowledged_by_agent", "undone_by", "prev_hash", "hash")

    def _doc_hash_cuoi(self) -> str:
        cuoi = GENESIS
        if not self.path.exists():
            return cuoi
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                cuoi = (json.loads(line).get("hash") or cuoi)
        return cuoi

    @classmethod
    def _bam(cls, d: dict[str, Any], prev: str) -> str:
        than = {k: v for k, v in d.items() if k not in cls._BO_QUA_KHI_BAM}
        chu = json.dumps(than, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256((prev + chu).encode("utf-8")).hexdigest()

    def append(self, cs: Changeset) -> Changeset:
        d = cs.to_dict()
        d["prev_hash"] = self._head
        d["hash"] = self._bam(d, self._head)
        line = json.dumps(d, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        self._head = d["hash"]
        return cs

    def verify(self) -> tuple[bool, str]:
        """Kiểm chuỗi — gọi khi MỞ DỰ ÁN. Lệch thì nói đúng changeset nào."""
        prev = GENESIS
        n = 0
        chua_ky = 0
        if not self.path.exists():
            return True, "Chưa có changeset nào."
        for i, line in enumerate(self.path.read_text("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            d = json.loads(line)
            if "hash" not in d:
                # Dòng ghi trước khi có chuỗi hash (kho cũ). KHÔNG được tính là toàn
                # vẹn — "chưa kiểm được" khác "đã kiểm và đạt" (N6).
                chua_ky += 1
                n += 1
                continue
            if d.get("prev_hash") != prev:
                return False, (f"Sổ changeset bị sửa ở {d.get('id')} (dòng {i}): "
                               "liên kết trước không khớp.")
            if self._bam(d, prev) != d["hash"]:
                return False, (f"Sổ changeset bị sửa ở {d.get('id')} (dòng {i}): "
                               "nội dung không khớp hash.")
            prev = d["hash"]
            n += 1
        if chua_ky:
            return False, (
                f"{chua_ky}/{n} changeset KHÔNG có chuỗi hash nên không kiểm được — "
                "hoặc chúng được ghi trước khi có cơ chế này, hoặc tệp đã bị ghi lại "
                "bằng đường khác. Đừng coi là toàn vẹn.")
        return True, f"Sổ changeset toàn vẹn: {n} thay đổi."

    def read(self) -> Iterator[Changeset]:
        if not self.path.exists():
            return
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                yield Changeset.from_dict(json.loads(line))

    def all(self) -> list[Changeset]:
        return list(self.read())

    def get(self, cs_id: str) -> Changeset | None:
        for cs in self.read():
            if cs.id == cs_id:
                return cs
        return None

    def of_run(self, run_id: str) -> list[Changeset]:
        return [cs for cs in self.read() if cs.run_id == run_id]

    def touching(self, artefact_id: str) -> list[Changeset]:
        return [cs for cs in self.read()
                if any(t.artefact_id == artefact_id for t in cs.touches)]

    def human_unacknowledged(self) -> list[Changeset]:
        """Sửa của người mà tác tử chưa nhắc tới — nguồn của khối `<human_edits>` (N9)."""
        return [cs for cs in self.read()
                if cs.by_human and not cs.acknowledged_by_agent and not cs.undone_by]

    def mark(self, cs_id: str, **fields: Any) -> None:
        """Đánh dấu `acknowledged_by_agent` / `undone_by`. Giữ nguyên mọi thứ khác.

        Đọc lại từ **JSON thô**, không qua `Changeset.from_dict → to_dict`. Vòng đó làm
        rụng `prev_hash`/`hash` vì chúng không phải field của dataclass — và một lần
        đánh dấu là đủ xoá sạch chuỗi hash của cả tệp. Lỗi này im lặng: `verify()` sau
        đó vẫn báo "toàn vẹn" vì không còn hash nào để mà lệch.
        """
        if not self.path.exists():
            return
        rows = [json.loads(l) for l in self.path.read_text("utf-8").splitlines()
                if l.strip()]
        for r in rows:
            if r.get("id") == cs_id:
                r.update(fields)
        with self._lock:
            tmp = self.path.with_suffix(".jsonl.tmp")
            tmp.write_text(
                "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                        for r in rows), "utf-8")
            tmp.replace(self.path)

    def sau(self, cs_id: str) -> list[Changeset]:
        """Các changeset xảy ra SAU một changeset — dùng để cảnh báo chuỗi (CX10)."""
        thay = False
        out: list[Changeset] = []
        for cs in self.read():
            if thay:
                out.append(cs)
            elif cs.id == cs_id:
                thay = True
        return out


# =========================================================================== blob
class BlobStore:
    """Hiện vật lớn (log, VCD, PDF) lưu theo hash nội dung — §E5.1.

    "changeset chỉ trỏ tới hash — hoàn tác không mất bằng chứng."

    Đó là câu quan trọng: khi hoàn tác một lượt có mô phỏng, kết quả mô phỏng bị gỡ
    khỏi trạng thái hiện tại, nhưng cái log chứng minh nó từng chạy vẫn còn nguyên.
    Không có chỗ này thì "không đạt giả" (N6) mất đi bằng chứng của chính nó.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes | str) -> str:
        b = data.encode("utf-8") if isinstance(data, str) else data
        h = hashlib.sha256(b).hexdigest()
        p = self.root / h[:2] / h
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b)
        return h

    def get(self, h: str) -> bytes | None:
        p = self.root / h[:2] / h
        return p.read_bytes() if p.exists() else None

    def exists(self, h: str) -> bool:
        return (self.root / h[:2] / h).exists()


# =========================================================================== dựng
def for_store_write(*, cs_id: str, author: str, artefact_id: str, type: str, op: str,
                    from_version: int | None, to_version: int,
                    canonical_truoc: dict[str, Any] | None,
                    canonical_sau: dict[str, Any],
                    explain: dict[str, Any], run_id: str | None = None,
                    tool_call_id: str | None = None,
                    human_act_id: str | None = None,
                    note: str | None = None) -> Changeset:
    """Changeset cho một lần ghi vào kho.

    Phép nghịch đảo được dựng NGAY ở đây, từ trạng thái trước mà ta còn đang cầm trong
    tay. Đợi tới lúc hoàn tác mới đi tìm bản cũ là đánh cược vào việc nó còn tồn tại.
    """
    forward = [{"kind": "store", "op": op, "artefact_id": artefact_id, "type": type,
                "version": to_version, "canonical": canonical_sau, "explain": explain}]
    if op == "create":
        inverse = [{"kind": "store", "op": "delete", "artefact_id": artefact_id,
                    "type": type, "version": to_version}]
    else:
        inverse = [{"kind": "store", "op": "restore", "artefact_id": artefact_id,
                    "type": type, "version": from_version,
                    "canonical": canonical_truoc or {}, "explain": explain}]
    return Changeset(
        id=cs_id, ts=_now(), author=author, run_id=run_id,
        tool_call_id=tool_call_id, human_act_id=human_act_id,
        touches=[Touch(artefact_id, type, op, from_version, to_version)],
        forward=forward, inverse=inverse, explain=explain, note=note)


def for_file_write(*, cs_id: str, author: str, paths: list[str], sha: str | None,
                   sha_truoc: str | None, explain: dict[str, Any],
                   run_id: str | None = None, tool_call_id: str | None = None,
                   human_act_id: str | None = None, note: str | None = None,
                   blob_truoc: dict[str, str] | None = None) -> Changeset:
    """Changeset cho một lần ghi tệp. Phép nghịch đảo = revert commit git.

    `blob_truoc` giữ hash nội dung cũ của từng tệp để hoàn tác được cả khi kho git
    hỏng — git là đường chính, blob là đường lui.
    """
    forward = [{"kind": "file", "op": "commit", "sha": sha, "paths": paths}]
    inverse = [{"kind": "file", "op": "revert", "sha": sha, "paths": paths,
                "sha_truoc": sha_truoc, "blob_truoc": blob_truoc or {}}]
    return Changeset(
        id=cs_id, ts=_now(), author=author, run_id=run_id,
        tool_call_id=tool_call_id, human_act_id=human_act_id,
        touches=[Touch(p, "code", "update") for p in paths],
        forward=forward, inverse=inverse, explain=explain, note=note)


def irreversible(*, cs_id: str, author: str, what: str, reason_vi: str,
                 explain: dict[str, Any], run_id: str | None = None,
                 tool_call_id: str | None = None) -> Changeset:
    """§E5.3 — target.flash, target.dangerous, tool.install, gửi tài liệu ra ngoài.

    Vẫn là một changeset: nó vào lịch sử, hiện trên dòng thời gian, và khi người hoàn
    tác cả lượt thì nó được GIỮ NGUYÊN kèm cảnh báo "bo vẫn đang chạy bản X" (CX11).
    """
    return Changeset(
        id=cs_id, ts=_now(), author=author, run_id=run_id, tool_call_id=tool_call_id,
        touches=[Touch(what, "target", "update")],
        forward=[{"kind": "external", "what": what}], inverse=[],
        explain=explain, reversible=False, irreversible_reason=reason_vi)
