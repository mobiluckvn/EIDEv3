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

try:
    import fcntl                       # POSIX. Thieu no thi van chay, chi mat khoa lien tien trinh.
except ImportError:                    # pragma: no cover - Windows
    fcntl = None                       # type: ignore[assignment]
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
    "compact",            # nen ngu canh: pre / ok / kiem_truot / loi (MEM-42 §6)
    "changeset",          # chi muc; noi dung day o changesets.jsonl (§E5.1)
    "incident",           # mang, LLM, timeout, sandbox (UC19)
    # Tac tu con (§B5): tung loi goi cong cu cua no, va ket luan luc no dung. Ghi rieng chu
    # khong gop vao `tool_use` vi hai thu tra loi hai cau hoi khac nhau: "luot nay da lam
    # gi" va "AI da lam viec do". Mot bao cao "dat" cua subagent phai tra ve duoc cho toi
    # so cai — neu khong thi lop kiem chung doc lap khong kiem lai duoc.
    "subagent_tool", "subagent_stop",
    "note",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _duoi_tep(f: Any) -> tuple[int, str]:
    """Doc DONG CUOI cua mot tep NHI PHAN dang mo → `(seq, hash)`. `(0, GENESIS)` neu rong.

    Duyet nguoc tu cuoi thay vi doc ca tep: ham nay chay o MOI lan ghi so cai, va so cai cua
    mot phien lam viec that da len hon muoi nghin dong. Doc lai ca tep moi lan ghi bien viec
    ghi tu O(1) thanh O(n), tuc la du an cang lam lau cang cham dan — kieu cham khong ai truy
    ra duoc vi no khong hong o dau ca.

    Tep phai mo o che do NHI PHAN. Nhay toi mot vi tri byte bat ky roi doc o che do van ban
    se cat doi mot ky tu UTF-8 nhieu byte va nem `UnicodeDecodeError` — ma so cai nay day
    tieng Viet co dau, nen loi do khong phai gia thuyet.
    """
    f.seek(0, os.SEEK_END)
    cuoi = f.tell()
    if cuoi == 0:
        return 0, GENESIS
    kich = 4096
    while True:
        dau = max(0, cuoi - kich)
        f.seek(dau)
        dong = [x for x in f.read(cuoi - dau).splitlines() if x.strip()]
        # Can it nhat mot dong TRON VEN. O lan doc dau, dong dau tien co the bi cat giua
        # chung — chi tin no khi da doc toi dau tep, hoac khi con nhieu hon mot dong.
        if len(dong) > 1 or dau == 0:
            break
        if kich > 1 << 20:              # mot dong dai hon 1 MB thi thoi, doc ca tep cho xong
            f.seek(0)
            dong = [x for x in f.read().splitlines() if x.strip()]
            break
        kich *= 2
    if not dong:
        return 0, GENESIS
    try:
        rec = json.loads(dong[-1].decode("utf-8"))
        return int(rec["seq"]), rec["hash"]
    except (ValueError, KeyError, UnicodeDecodeError):
        # Dong cuoi vo (mat dien giua luc ghi?). Noi ra bang cach tra ve GENESIS thi SAI —
        # no se lam ban ghi ke tiep gia vo la dong dau tien. Doc lui them mot dong.
        for x in reversed(dong[:-1]):
            try:
                rec = json.loads(x.decode("utf-8"))
                return int(rec["seq"]), rec["hash"]
            except (ValueError, KeyError, UnicodeDecodeError):
                continue
        return 0, GENESIS


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
    """So cai mot du an. An toan voi nhieu luong VA nhieu tien trinh.

    Vi sao phai lo toi nhieu tien trinh, do duoc ngay trong du an nay: app EIDE dang mo mot
    du an, bo kich ban phien mo **cung** du an do, va ca hai cung ghi. Moi ben giu `_seq`/
    `_head` doc luc khoi tao roi tu dem tiep, nen so cai co hai ban ghi cung mang `seq 9156`
    va chuoi hash dut o do. Chinh tac tu phat hien ra — no doc so cai va bao "lech thu tu o
    dong 9174".

    Do la hong dung cai thuoc tinh ma so cai ton tai de co: §F3 "toan ven lich su". Mot so cai
    khong con la mot thu tu tong thi moi cau chuyen dung tren no deu co the sai ma khong ai
    biet.

    Cach chua: khoa lien tien trinh (`flock`) quanh MOI lan ghi, va **doc lai duoi tep ben
    trong khoa** truoc khi cap `seq`/`prev` — gia tri nho trong bo nho chi la goi y, dia moi
    la su that.
    """

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
            # Mo tep TRUOC khi tinh seq: khoa lien tien trinh phai om tron ca viec doc duoi
            # lan viec ghi. Tinh seq ngoai khoa roi moi khoa de ghi thi hai tien trinh van
            # tinh ra cung mot so — dung cai loi ma khoa nay sinh ra de chua.
            with self.path.open("ab+") as f:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    # Gia tri nho trong bo nho chi la goi y; dia moi la su that. Tien trinh
                    # khac co the da ghi them ke tu lan cuoi ta nhin.
                    seq_dia, head_dia = _duoi_tep(f)
                    seq = max(self._seq, seq_dia) + 1
                    truoc = head_dia if seq_dia >= self._seq else self._head
                    ts = _now()
                    body = {"seq": seq, "ts": ts, "kind": kind, "data": data}
                    payload = json.dumps(body, ensure_ascii=False, sort_keys=True,
                                         separators=(",", ":"))
                    h = _digest(payload, truoc)
                    rec = {**body, "prev": truoc, "hash": h}
                    line = json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n"
                    f.seek(0, os.SEEK_END)
                    f.write(line.encode("utf-8"))
                    f.flush()
                    # fsync: write-ahead chi co nghia neu no that su nam tren dia truoc khi
                    # ta lam viec.
                    os.fsync(f.fileno())
                finally:
                    if fcntl is not None:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            self._seq, self._head = seq, h
            return Event(seq, ts, kind, data, rec["prev"], h)

    # ------------------------------------------------------------------ kiem
    def verify(self) -> tuple[bool, str]:
        """Kiem chuoi hash. Tra (dat, mo ta cho nguoi doc) — goi khi MO DU AN (§F3).

        Phan biet HAI hong hoan toan khac nhau, va day la diem quan trong nhat cua ham:

        * **Bi sua** — noi dung mot ban ghi khong con khop hash cua chinh no. Day la cao buoc,
          va no chi duoc noi khi chung minh duoc.
        * **Hai tien trinh cung ghi** — cac ban ghi deu con nguyen hash cua rieng chung, chi
          co thu tu `seq` bi lap hoac tut lui. Do la tai nan van hanh, khong phai ai sua gi.

        Ban truoc gop ca hai vao mot cau "Sổ cái bị sửa". Do duoc that trong du an nay: app
        EIDE va bo kich ban phien cung mo mot du an, so cai co hai ban ghi cung `seq 9156`, va
        EIDE bao voi nguoi dung rang lich su cua ho **bi sua**. Mot cao buoc sai o dung cho
        nguoi ta phai tin tuyet doi thi dat hon nhieu so voi im lang.
        """
        prev = GENESIS
        n = 0
        for i, ev in enumerate(self.read(), 1):
            if ev.seq != i:
                # Ban ghi nay co tu kiem duoc khong? Neu co thi day la loi THU TU, khong phai
                # loi NOI DUNG — va hai cai doi hoi hai cach xu ly khac han.
                body = {"seq": ev.seq, "ts": ev.ts, "kind": ev.kind, "data": ev.data}
                payload = json.dumps(body, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"))
                tu_kiem = _digest(payload, ev.prev) == ev.hash
                if tu_kiem:
                    return False, (
                        f"Sổ cái đứt thứ tự ở dòng {i}: seq ghi là {ev.seq}, đáng lẽ {i}. "
                        "Nội dung từng bản ghi vẫn khớp hash của chính nó, nên KHÔNG phải ai "
                        "sửa — dấu hiệu của hai tiến trình cùng mở một dự án và cùng ghi. "
                        "Đóng bớt một bên đi; những gì đã ghi vẫn đọc được.")
                return False, (f"Sổ cái đứt thứ tự ở dòng {i}: seq ghi là {ev.seq}, và bản "
                               "ghi này không tự khớp hash của nó.")
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
