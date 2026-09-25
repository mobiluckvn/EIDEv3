# -*- coding: utf-8 -*-
"""EIDE v3 — lõi tác tử kỹ sư nhúng.

Thiết kế: EIDE-MDD-40 v3.0 (docs/review-v3/docs/md/). Tài liệu là nguồn sự thật; mọi
chỗ mã khác tài liệu phải được ghi vào docs/md/EIDE-DEV-LOG.md dạng [DEV-2xx].

Dựng một tác tử:

    from eide import Config, Agent, make_gateway, Core, IdGen
    cfg = Config.for_project("du-lieu/du-an-cua-toi")
    agent = Agent(cfg, llm=make_gateway(cfg.model))
    core = Core(agent.ledger, agent.ids, agent.turn, on_emit=print)
    core.console_act({"kind": "say", "text": "Làm bộ chuyển LAN sang USB cho TV"})
"""

from .config import Config, ModelConfig, load_dotenv
from .errors import EideError
from .ids import IdGen
from .llm import make_gateway
from .loop import Agent, TurnContext
from .protocol import HumanAct, Origin, Target, UICommand
from .protocol.rpc import Core

__version__ = "3.0.0a1"

__all__ = ["Config", "ModelConfig", "load_dotenv", "Agent", "TurnContext", "Core",
           "HumanAct", "Target", "Origin", "UICommand", "EideError", "IdGen",
           "make_gateway", "__version__"]
