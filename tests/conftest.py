# -*- coding: utf-8 -*-
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from eide import Config  # noqa: E402
from eide.loop import Agent  # noqa: E402
from eide.llm import ScriptedGateway  # noqa: E402


@pytest.fixture
def du_an(tmp_path):
    """Một dự án trống, có sandbox thật."""
    root = tmp_path / "du-an-thu"
    root.mkdir()
    (root / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    (root / "docs").mkdir()
    (root / "docs" / "ghi-chu.md").write_text("# Ghi chú\nI2C chạy ở 100 kHz.\n", "utf-8")
    return root


@pytest.fixture
def cfg(du_an):
    return Config.for_project(du_an)


@pytest.fixture
def make_agent(cfg):
    def _make(script=None):
        return Agent(cfg, llm=ScriptedGateway(script or []), project_name="du-an-thu")
    return _make


@pytest.fixture
def chay(make_agent):
    """Chạy một lượt, trả (agent, danh sách UICommand đã phát)."""
    from eide.protocol.rpc import Core

    def _chay(act, script=None):
        agent = make_agent(script)
        seen = []
        core = Core(agent.ledger, agent.ids, agent.turn, on_emit=seen.append)
        core.console_act(act)
        return agent, seen
    return _chay
