# -*- coding: utf-8 -*-
"""Snapshot — "bản ưng ý". EIDE-MDD-40 §E6.

    "Người: nút 'Ghi bản ưng ý'… luôn được (R0); tác tử bổ sung explain.
     Tác tử đề xuất: sau mốc → thẻ G-SNAP: người đặt tên/ghi chú/hoặc từ chối.
     **Tác tử không tự tạo snapshot có tên.**"

Câu in đậm là cả thiết kế của tệp này. Một bản ưng ý là thứ người sẽ quay về sáu tháng
sau, khi họ không còn nhớ hôm đó đã làm gì. Cái tên là thứ duy nhất dẫn họ về đúng chỗ,
và chỉ họ mới biết đặt tên sao cho mình hiểu. Tác tử đặt tên hộ sẽ tạo ra một danh sách
"snapshot-1, snapshot-2, sau-khi-sua-driver" — đúng kiểu không ai dùng được.

## Ba loại snapshot, ba vai trò khác nhau

| Loại | Ai tạo | Có tên | Hiện trong danh sách |
|---|---|---|---|
| `checkpoint` | tự động, trước mỗi run và mỗi hoàn tác lớn | không | không (ẩn mặc định) |
| `named` | **người** | có | có |
| `release` | người đánh dấu | có | có, kèm ★ |

`release` không chỉ là một cái nhãn: §E6.2 nói nó là **điều kiện** cho `target.dangerous`
(RDP, eFuse). Lý do thẳng thắn — sau khi khoá chip thì không còn đường lùi, nên phải có
một bản đã biết là chạy được để đối chiếu.

## Bất biến

`immutable: true` được giữ bằng mã: `SnapshotStore.ghi` từ chối ghi đè một id đã có, và
`doi_ten` chỉ sửa được phần **ghi chú** của bản chưa đánh dấu release. Một bản ưng ý mà
sửa được thì nó không còn là mốc để quay về.
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class Snapshot:
    id: str
    ts: str
    kind: str                                   # checkpoint | named | release
    name: str = ""
    note: str = ""
    created_by: str = "human"                   # human | agent(+approved)
    at_changeset: str | None = None
    contents: dict[str, Any] = field(default_factory=dict)
    passed: list[str] = field(default_factory=list)
    chip: str | None = None
    immutable: bool = True

    @property
    def co_ten(self) -> bool:
        return self.kind in ("named", "release")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "ts": self.ts, "kind": self.kind, "name": self.name,
                "note": self.note, "created_by": self.created_by,
                "at_changeset": self.at_changeset, "contents": self.contents,
                "passed": self.passed, "chip": self.chip, "immutable": self.immutable}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Snapshot":
        return cls(id=d["id"], ts=d["ts"], kind=d.get("kind", "named"),
                   name=d.get("name", ""), note=d.get("note", ""),
                   created_by=d.get("created_by", "human"),
                   at_changeset=d.get("at_changeset"),
                   contents=d.get("contents", {}), passed=d.get("passed", []),
                   chip=d.get("chip"), immutable=d.get("immutable", True))

    def tom_tat(self) -> str:
        c = self.contents
        phan = []
        if c.get("so_req"):
            phan.append(f"{c['so_req']} yêu cầu")
        if c.get("facts_tier_counts"):
            t = c["facts_tier_counts"]
            phan.append(f"{sum(t.values())} Fact ({', '.join(f'{k} {v}' for k, v in t.items())})")
        if c.get("so_tep"):
            phan.append(f"{c['so_tep']} tệp")
        if c.get("docs"):
            phan.append(f"{len(c['docs'])} tài liệu")
        return " · ".join(phan) or "trống"


class SnapshotStore:
    """`snapshots.jsonl` — chỉ ghi thêm, không sửa, không xoá."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def ghi(self, s: Snapshot) -> Snapshot:
        if self.get(s.id) is not None:
            raise ValueError(f"Snapshot {s.id} đã tồn tại — bản ưng ý là bất biến.")
        line = json.dumps(s.to_dict(), ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        return s

    def doc(self) -> Iterator[Snapshot]:
        if not self.path.exists():
            return
        for line in self.path.read_text("utf-8").splitlines():
            if line.strip():
                yield Snapshot.from_dict(json.loads(line))

    def all(self, *, gom_checkpoint: bool = False) -> list[Snapshot]:
        return [s for s in self.doc() if gom_checkpoint or s.kind != "checkpoint"]

    def get(self, sid: str) -> Snapshot | None:
        for s in self.doc():
            if s.id == sid:
                return s
        return None

    def theo_ten(self, ten: str) -> Snapshot | None:
        for s in self.doc():
            if s.co_ten and s.name == ten:
                return s
        return None

    def gan_nhat(self) -> Snapshot | None:
        ds = self.all()
        return ds[-1] if ds else None

    def co_release(self) -> bool:
        return any(s.kind == "release" for s in self.doc())

    def danh_dau_release(self, sid: str) -> Snapshot | None:
        """Nâng một bản ưng ý lên release. Đây là thay đổi DUY NHẤT được phép.

        Nó không sửa nội dung — chỉ ghi nhận một quyết định xảy ra SAU: người tuyên bố
        bản này là bản phát hành. Nội dung vẫn bất biến.
        """
        rows = [s.to_dict() for s in self.doc()]
        thay = False
        for r in rows:
            if r["id"] == sid and r["kind"] == "named":
                r["kind"] = "release"
                thay = True
        if not thay:
            return None
        with self._lock:
            tmp = self.path.with_suffix(".jsonl.tmp")
            tmp.write_text("".join(json.dumps(r, ensure_ascii=False,
                                              separators=(",", ":")) + "\n"
                                   for r in rows), "utf-8")
            tmp.replace(self.path)
        return self.get(sid)


# =========================================================================== xuất kho
def xuat_kho(store: Any) -> dict[str, Any]:
    """Chụp toàn bộ kho hiện vật + Fact thành một cấu trúc phẳng.

    Đây là "store_export" của §E6.1. Nó phải **đủ để dựng lại**, không chỉ đủ để so
    sánh — vì `snapshot.restore` dùng chính nó.
    """
    return {
        "artefacts": [
            {"id": a["id"], "type": a["type"], "version": a["version"],
             "author": a["author"], "canonical": a["canonical"],
             "explain": a["explain"], "deps": a.get("deps", {}),
             "stale": a["stale"], "stale_reason": a["stale_reason"]}
            for a in store.list(limit=5000)
        ],
        "facts": store.query_facts(limit=5000),
    }


def bam(o: Any) -> str:
    return hashlib.sha256(
        json.dumps(o, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


# =========================================================================== so sánh
@dataclass(slots=True)
class KhacBiet:
    loai: str                                   # req | fact | code | doc | passport…
    them: list[str] = field(default_factory=list)
    bot: list[str] = field(default_factory=list)
    doi: list[dict[str, Any]] = field(default_factory=list)

    @property
    def co_gi_doi(self) -> bool:
        return bool(self.them or self.bot or self.doi)

    def to_dict(self) -> dict[str, Any]:
        return {"loai": self.loai, "them": self.them, "bot": self.bot, "doi": self.doi}


def so_sanh_kho(a: dict[str, Any], b: dict[str, Any]) -> list[KhacBiet]:
    """So hai bản xuất kho, nhóm theo LOẠI hiện vật — §E6.3.

    Nhóm theo loại chứ không liệt kê phẳng, vì câu người hỏi khi so hai bản ưng ý là
    "yêu cầu có đổi không", "Fact nào khác", "mã khác ở đâu" — chứ không phải "cho tôi
    danh sách 200 thứ".
    """
    ra: dict[str, KhacBiet] = {}

    def lay(loai: str) -> KhacBiet:
        return ra.setdefault(loai, KhacBiet(loai))

    ta = {x["id"]: x for x in a.get("artefacts", [])}
    tb = {x["id"]: x for x in b.get("artefacts", [])}
    for i in tb.keys() - ta.keys():
        lay(tb[i]["type"]).them.append(i)
    for i in ta.keys() - tb.keys():
        lay(ta[i]["type"]).bot.append(i)
    for i in ta.keys() & tb.keys():
        if ta[i]["canonical"] != tb[i]["canonical"]:
            lay(ta[i]["type"]).doi.append({
                "id": i, "tu_ban": ta[i]["version"], "sang_ban": tb[i]["version"],
                "tom_tat": (tb[i].get("explain") or {}).get("summary", "")})

    fa = {f["fact_id"]: f for f in a.get("facts", [])}
    fb = {f["fact_id"]: f for f in b.get("facts", [])}
    for i in fb.keys() - fa.keys():
        lay("fact").them.append(f"{fb[i]['key']} = {fb[i]['value']} {fb[i]['unit'] or ''}")
    for i in fa.keys() - fb.keys():
        lay("fact").bot.append(f"{fa[i]['key']} = {fa[i]['value']} {fa[i]['unit'] or ''}")
    for i in fa.keys() & fb.keys():
        if (fa[i]["value"], fa[i]["tier"]) != (fb[i]["value"], fb[i]["tier"]):
            lay("fact").doi.append({
                "id": fa[i]["key"],
                "tu_ban": f"{fa[i]['value']} [{fa[i]['tier']}]",
                "sang_ban": f"{fb[i]['value']} [{fb[i]['tier']}]",
                "tom_tat": "giá trị hoặc tầng tin cậy đổi"})

    return [k for k in ra.values() if k.co_gi_doi]


# =========================================================================== sẽ mất gì
def se_mat_gi(hien_tai: dict[str, Any], snap: dict[str, Any],
              *, changeset_sau: list[Any]) -> dict[str, Any]:
    """§E6.3 — thẻ G-HIST phải liệt kê **sẽ mất gì** TRƯỚC khi khôi phục.

    Người bấm "khôi phục" thường đang bực mình vì thứ gì đó hỏng, và đó chính là lúc
    dễ mất việc nhất. Nên câu hỏi phải là "anh có chấp nhận mất những thứ này không",
    không phải "anh chắc chưa".
    """
    # Chiều so sánh là bản-ưng-ý → hiện-tại, KHÔNG phải ngược lại. Đọc theo chiều này thì
    # `them` = sinh ra sau snapshot = thứ sẽ MẤT; `bot` = đã xoá sau snapshot = thứ sẽ QUAY
    # LẠI. Đảo chiều là đảo luôn ý nghĩa của thẻ G-HIST, nên viết rõ ở đây.
    kb = so_sanh_kho(snap, hien_tai)
    cua_nguoi = [c for c in changeset_sau if getattr(c, "by_human", False)]
    cua_tac_tu = [c for c in changeset_sau if not getattr(c, "by_human", False)]
    khong_lui = [c for c in changeset_sau if not getattr(c, "reversible", True)]

    dong: list[str] = []
    for k in kb:
        if k.them:
            dong.append(f"mất {len(k.them)} {k.loai} mới: " + ", ".join(k.them[:4]))
        if k.doi:
            dong.append(f"{len(k.doi)} {k.loai} quay về bản cũ: "
                        + ", ".join(x["id"] for x in k.doi[:4]))
        if k.bot:
            dong.append(f"{len(k.bot)} {k.loai} đã xoá sẽ quay lại: "
                        + ", ".join(k.bot[:4]))
    return {
        "khac_biet": [k.to_dict() for k in kb],
        "so_changeset_sau": len(changeset_sau),
        "cua_nguoi": [c.id for c in cua_nguoi],
        "cua_tac_tu": [c.id for c in cua_tac_tu],
        "khong_hoan_tac_duoc": [{"id": c.id, "ly_do": c.ly_do_khong_hoan_tac() or ""}
                                for c in khong_lui],
        "se_mat_vi": dong,
        "co_sua_cua_nguoi": bool(cua_nguoi),
    }
