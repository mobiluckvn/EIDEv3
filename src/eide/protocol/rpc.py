# -*- coding: utf-8 -*-
"""Mot cua vao. EIDE-MDD-40 §D, §D2 "Van chuyen".

    "Nguoi va may gap nhau o MOT noi: Ban giao tiep (Console) — mot phuong thuc
     console.act, mot loai thong diep HumanAct, mot dong hoi thoai."

Phuong thuc RPC:
  console.act(act)         NGUOI -> LOI. Cua duy nhat cho y chi cua nguoi (I1).
  hello(client)            May–may. Tra nang luc + seq hien tai.
  resume(last_seq)         May–may. Phat lai UICommand tu last_seq (I5).
  ui.status()              May–may. Trang thai loi, khong phai y chi.
  ping()                   May–may.

Van chuyen: JSON-RPC 2.0 tren stdio (khung Content-Length) hoac WebSocket localhost.
seq hai chieu; idempotent theo id; write-ahead HumanAct vao so cai TRUOC khi lam.
"""

from __future__ import annotations

import json
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from ..errors import EideError, proto, PROTO_CHANNEL, PROTO_DUP, PROTO_GAP
from ..ids import IdGen
from .humanact import HumanAct, ensure
from .ledger import Ledger
from .uicommand import UICommand, notice

# §D2: "resume(last_seq) phat lai, > 500 thong diep -> surface.set toan bo"
REPLAY_LIMIT = 500
OUTBOX_KEEP = 2000


class TurnRunner(Protocol):
    """Thu ma lõi goi khi nguoi bao mot dieu gi do. Hien thuc o `eide.loop`."""

    def __call__(self, act: HumanAct, emit: Callable[[UICommand], None]) -> None: ...


class Session:
    """Mot phien noi voi mot giao dien. Giu seq ra, lich su de phat lai, chong trung."""

    def __init__(self) -> None:
        self._seq_out = 0
        self._outbox: deque[UICommand] = deque(maxlen=OUTBOX_KEEP)
        self._seen_act_ids: set[str] = set()
        self._seq_in = 0
        self._lock = threading.Lock()

    def stamp(self, cmd: UICommand) -> UICommand:
        with self._lock:
            self._seq_out += 1
            cmd.seq = self._seq_out
            self._outbox.append(cmd)
        return cmd

    def replay(self, last_seq: int) -> list[UICommand] | None:
        """None = qua xa, giao dien phai xin surface.set toan bo."""
        with self._lock:
            behind = self._seq_out - last_seq
            if behind < 0:
                raise proto(PROTO_GAP, f"Giao diện báo đã nhận tới {last_seq} nhưng lõi mới gửi tới {self._seq_out}.")
            if behind > REPLAY_LIMIT or (self._outbox and self._outbox[0].seq > last_seq + 1):
                return None
            return [c for c in self._outbox if c.seq > last_seq]

    def accept_in(self, act_id: str, seq: int) -> None:
        with self._lock:
            if act_id in self._seen_act_ids:
                raise proto(PROTO_DUP, f"Thao tác {act_id} đã nhận rồi.", act_id=act_id)
            self._seen_act_ids.add(act_id)
            self._seq_in = max(self._seq_in, seq)

    @property
    def seq_out(self) -> int:
        return self._seq_out


class Core:
    """Lõi nhin tu phia giao thuc. Khong biet gi ve giao dien (I4)."""

    CAPABILITIES = {
        "uap": "1.1",
        "human_acts": 13,
        "ui_commands": 16,
        "gates": ["G-DATA", "G-DESIGN", "G-SCOPE", "G-TOOL", "G-QUAL", "G-FILE",
                  "G-FLASH", "G-OPS", "G-SAFE", "G-HIST", "G-SNAP"],
        "surfaces": ["requirements", "documents", "knowledge", "design", "tools",
                     "code", "simulation", "hardware", "journal", "history"],
    }

    def __init__(self, ledger: Ledger, ids: IdGen, run_turn: TurnRunner,
                 *, on_emit: Callable[[UICommand], None] | None = None,
                 on_sync: Callable[[Callable[[UICommand], None]], None] | None = None):
        self.ledger = ledger
        self.ids = ids
        self.run_turn = run_turn
        self.session = Session()
        self._sink = on_emit or (lambda c: None)
        # Vẽ lại toàn bộ bề mặt. May–may, khong phai y chi cua nguoi (I1/I4).
        self._sync = on_sync

    # ------------------------------------------------------------------ gui ra
    def emit(self, cmd: UICommand, *, phat_lai: bool = False) -> None:
        """Gui mot UICommand cho giao dien.

        `phat_lai=True`: lenh nay dung lai thu DA nam trong so cai (mo lai du an, dung
        lai transcript). Khong ghi so lan nua — neu ghi thi moi lan mo du an lai nhan
        doi lich su, va CX16 ("phat lai tai tao trang thai 100 %") se sai ngay tu lan
        mo thu hai.
        """
        self.session.stamp(cmd)
        if not phat_lai:
            self.ledger.append("ui_command", {"method": cmd.method, "seq": cmd.seq,
                                              "params": _trim(cmd.params)})
        self._sink(cmd)

    # ------------------------------------------------------------------ phuong thuc
    def hello(self, client: dict[str, Any] | None = None) -> dict[str, Any]:
        ok, msg = self.ledger.verify()  # §F3: kiem hash chuoi khi mo du an
        return {
            "core": "eide", "version": "3.0.0a1",
            "capabilities": self.CAPABILITIES,
            "seq_out": self.session.seq_out,
            "ledger": {"ok": ok, "message_vi": msg, "events": self.ledger.seq},
            "client": client or {},
        }

    def resume(self, last_seq: int = 0) -> dict[str, Any]:
        cmds = self.session.replay(int(last_seq))
        if cmds is None:
            return {"mode": "full", "reason_vi": "Cách quá xa, giao diện cần dựng lại toàn bộ bề mặt."}
        return {"mode": "replay", "commands": [c.to_dict() for c in cmds]}

    def ui_status(self) -> dict[str, Any]:
        return {"seq_out": self.session.seq_out, "ledger_seq": self.ledger.seq}

    def ui_sync(self) -> dict[str, Any]:
        """Giao diện vừa mở (hoặc vừa mất đồng bộ) và xin vẽ lại toàn bộ bề mặt.

        Đây là lời gọi MÁY–MÁY: nó không mang ý chí của người, nên không đi qua
        console.act và không để lại dòng nào trong transcript (I1, I2).
        """
        if self._sync is None:
            return {"painted": False,
                    "reason_vi": "Lõi chạy không kèm bộ vẽ bề mặt."}
        n = self._phat_lai_transcript()
        self._sync(self.emit)
        return {"painted": True, "dong_transcript": n, "seq_out": self.session.seq_out}

    def _phat_lai_transcript(self, gioi_han: int = 60) -> int:
        """Dung lai dong hoi thoai tu so cai khi mo lai du an.

        I2: "transcript = hinh chieu so cai, phat lai duoc". Mot giao dien mo len voi
        Console trong trong khi so cai co day du lich su la vi pham dung cau do — va
        no lam nguoi dung tuong phien truoc da mat.
        """
        from .uicommand import console_post, notice

        dong = [ev for ev in self.ledger.read()
                if ev.kind == "ui_command" and ev.data.get("method") == "console.post"]
        if not dong:
            return 0
        cat = len(dong) > gioi_han
        for ev in dong[-gioi_han:]:
            p = ev.data.get("params") or {}
            if p.get("_truncated"):
                continue
            self.emit(console_post(p.get("text", ""), role=p.get("role", "agent"),
                                   card=p.get("card")), phat_lai=True)
        if cat:
            self.emit(notice(
                f"Đã dựng lại {gioi_han} dòng gần nhất của phiên trước "
                f"(tổng {len(dong)} dòng). Mở tab Nhật ký để xem đầy đủ.",
                level="info"), phat_lai=True)
        return min(len(dong), gioi_han)

    def ping(self) -> dict[str, Any]:
        return {"pong": datetime.now(timezone.utc).isoformat(timespec="milliseconds")}

    def console_act(self, act: dict[str, Any] | HumanAct) -> dict[str, Any]:
        """CUA DUY NHAT. Moi thao tac cua nguoi vao loi qua day (I1)."""
        ha = ensure(act)
        if not ha.id:
            ha.id = self.ids.next("h")
        if not ha.ts:
            ha.ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self.session.accept_in(ha.id, ha.seq)

        # Write-ahead: ghi y chi cua nguoi TRUOC khi dong den no (I5, §D2).
        self.ledger.append("human_act", ha.to_dict())

        # I2 — moi HumanAct de lai dung mot dong "[Ban] ...", ke ca thao tac tren tab.
        #
        # Ngoai le DUY NHAT: `attend` (chuyen tab / chon hien vat). Mot dong transcript
        # cho moi cu bam tab se nhan chim chinh cuoc hoi thoai — xem DEV-226. Thao tac
        # van vao so cai o tren, nen phat lai (CX16) khong mat gi.
        if ha.kind != "attend":
            from .uicommand import console_post
            self.emit(console_post(ha.transcript_line(), role="human", act_id=ha.id))

        try:
            self.run_turn(ha, self.emit)
        except EideError as e:
            self.ledger.append("incident", {"act_id": ha.id, **e.to_tool_result()})
            self.emit(UICommand("notice", e.to_notice()))
        except Exception as e:  # su co khong luong truoc — UC19: dung an toan, noi that
            self.ledger.append("incident", {"act_id": ha.id, "kind": type(e).__name__, "why": str(e)})
            self.emit(notice(
                f"Lỗi không lường trước trong lõi: {type(e).__name__}: {e}. "
                "Trạng thái đã được lưu, tiếp tục được.", level="error"))
            raise
        return {"accepted": True, "act_id": ha.id, "seq_out": self.session.seq_out}

    # ------------------------------------------------------------------ dinh tuyen
    def dispatch(self, method: str, params: Any) -> Any:
        p = params if isinstance(params, dict) else {}
        if method == "console.act":
            return self.console_act(p.get("act", p))
        if method == "hello":
            return self.hello(p.get("client"))
        if method == "resume":
            return self.resume(p.get("last_seq", 0))
        if method == "ui.status":
            return self.ui_status()
        if method == "ui.sync":
            return self.ui_sync()
        if method == "ping":
            return self.ping()
        # I1 duoc canh o day: khong co cua thu hai vao lõi.
        raise proto(PROTO_CHANNEL,
                    f"Phương thức {method!r} không tồn tại. Ý chí của người chỉ vào bằng console.act.",
                    method=method)


def _trim(params: dict[str, Any], limit: int = 4000) -> dict[str, Any]:
    """So cai giu du de phat lai, nhung khong giu ca mot tep log 50 MB."""
    s = json.dumps(params, ensure_ascii=False, default=str)
    if len(s) <= limit:
        return params
    return {"_truncated": True, "_bytes": len(s), "_head": s[:limit]}


# =========================================================================== stdio
class StdioTransport:
    """Khung Content-Length nhu LSP. Dung cho app Swift chay lõi nhu tien trinh con."""

    def __init__(self, core: Core, inp=None, out=None):
        self.core = core
        self.inp = inp or sys.stdin.buffer
        self.out = out or sys.stdout.buffer
        self._wlock = threading.Lock()
        core._sink = self._send_command

    def _write(self, obj: dict[str, Any]) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        with self._wlock:
            self.out.write(b"Content-Length: %d\r\n\r\n" % len(body))
            self.out.write(body)
            self.out.flush()

    def _send_command(self, cmd: UICommand) -> None:
        # UICommand di theo chieu loi -> UI duoi dang thong bao JSON-RPC (khong co id).
        self._write({"jsonrpc": "2.0", "method": cmd.method,
                     "params": {**cmd.params, "_seq": cmd.seq}})

    def _read(self) -> dict[str, Any] | None:
        length = 0
        while True:
            line = self.inp.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            if line.lower().startswith(b"content-length:"):
                length = int(line.split(b":", 1)[1])
        if not length:
            return None
        return json.loads(self.inp.read(length).decode("utf-8"))

    def serve_forever(self) -> None:
        while True:
            try:
                msg = self._read()
            except (json.JSONDecodeError, ValueError) as e:
                self._write({"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32700, "message": f"JSON hỏng: {e}"}})
                continue
            if msg is None:
                return
            self._handle(msg)

    def _handle(self, msg: dict[str, Any]) -> None:
        mid = msg.get("id")
        try:
            result = self.core.dispatch(msg.get("method", ""), msg.get("params"))
            if mid is not None:
                self._write({"jsonrpc": "2.0", "id": mid, "result": result})
        except EideError as e:
            if mid is not None:
                self._write({"jsonrpc": "2.0", "id": mid,
                             "error": {"code": -32000, "message": e.message_vi,
                                       "data": e.to_tool_result()}})
        except Exception as e:
            if mid is not None:
                self._write({"jsonrpc": "2.0", "id": mid,
                             "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"}})


# =========================================================================== websocket
async def serve_websocket(core: Core, host: str = "127.0.0.1", port: int = 8777):
    """WebSocket localhost. Chi bind loopback — day la ung dung mot nguoi tren may ca nhan."""
    import asyncio

    import websockets

    async def handler(ws):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[UICommand] = asyncio.Queue()

        core._sink = lambda c: loop.call_soon_threadsafe(queue.put_nowait, c)

        async def pump():
            while True:
                cmd = await queue.get()
                await ws.send(json.dumps({"jsonrpc": "2.0", "method": cmd.method,
                                          "params": {**cmd.params, "_seq": cmd.seq}},
                                         ensure_ascii=False, default=str))

        task = asyncio.create_task(pump())
        try:
            async for raw in ws:
                msg = json.loads(raw)
                mid = msg.get("id")
                try:
                    # Mot luot co the chay hang chuc giay — khong duoc chan vong asyncio.
                    result = await loop.run_in_executor(
                        None, core.dispatch, msg.get("method", ""), msg.get("params"))
                    if mid is not None:
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result},
                                                 ensure_ascii=False, default=str))
                except EideError as e:
                    if mid is not None:
                        await ws.send(json.dumps({"jsonrpc": "2.0", "id": mid,
                                                  "error": {"code": -32000, "message": e.message_vi,
                                                            "data": e.to_tool_result()}},
                                                 ensure_ascii=False))
        finally:
            task.cancel()

    return await websockets.serve(handler, host, port)
