# -*- coding: utf-8 -*-
"""Điểm vào lõi: `eide-core`.

    eide-core --du-an <thư mục> --stdio          # cho app Swift chạy lõi làm tiến trình con
    eide-core --du-an <thư mục> --ws [--cong N]  # WebSocket localhost
    eide-core --du-an <thư mục> --go "câu nói"   # một lượt, in ra terminal (để thử nhanh)
"""

from __future__ import annotations

import argparse
import json
import sys

from .config import Config, load_dotenv
from .llm import make_gateway
from .loop import Agent
from .protocol.rpc import Core, StdioTransport


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="eide-core", description="Lõi tác tử EIDE v3")
    ap.add_argument("--du-an", "--project", dest="project", required=True,
                    help="Thư mục dự án (sandbox của tác tử)")
    ap.add_argument("--stdio", action="store_true", help="Phục vụ JSON-RPC trên stdio")
    ap.add_argument("--ws", action="store_true", help="Phục vụ JSON-RPC trên WebSocket")
    ap.add_argument("--cong", "--port", dest="port", type=int, default=8777)
    ap.add_argument("--go", dest="say", help="Chạy một lượt rồi thoát")
    ap.add_argument("--muc-tu-chu", dest="autonomy", default="A3",
                    choices=["A0", "A1", "A2", "A3", "A4"])
    a = ap.parse_args(argv)

    load_dotenv()
    cfg = Config.for_project(a.project, autonomy=a.autonomy)
    agent = Agent(cfg, llm=make_gateway(cfg.model))

    if a.say:
        def show(cmd):
            p = cmd.params
            if cmd.method == "console.post":
                print(p["text"], flush=True)
            elif cmd.method == "notice":
                print(f"[{p['level']}] {p['text']}", file=sys.stderr, flush=True)
        core = Core(agent.ledger, agent.ids, agent.turn, on_emit=show)
        core.console_act({"kind": "say", "text": a.say})
        print("\n--- báo cáo lượt ---", file=sys.stderr)
        print(json.dumps(agent.last_report, ensure_ascii=False, indent=1), file=sys.stderr)
        return 0

    core = Core(agent.ledger, agent.ids, agent.turn, on_sync=agent.paint)
    if a.ws:
        import asyncio
        from .protocol.rpc import serve_websocket

        async def run():
            await serve_websocket(core, port=a.port)
            print(f"EIDE core nghe ws://127.0.0.1:{a.port}", file=sys.stderr, flush=True)
            await asyncio.Event().wait()
        asyncio.run(run())
        return 0

    StdioTransport(core).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
