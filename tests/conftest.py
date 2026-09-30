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


@pytest.fixture(autouse=True)
def _nha_rieng(request, tmp_path_factory, monkeypatch):
    """Mỗi ca kiểm có một thư mục NHÀ riêng — không ca nào chạm `~` của máy thật.

    Bốn chỗ trong mã ghi dưới `~/.eide`: bộ nhớ người dùng (`memory.md`), **thư viện khối mức
    người dùng** (`blocks/`), thiết lập, và bộ đệm tìm kiếm. Không tách ra thì:

    * ca kiểm **đỏ hay xanh tuỳ máy ai chạy** — đo được 30/09/2026: một lượt E2E lưu khối
      `LDO-3V3` vào `~/.eide/blocks`, và ca `khoi.list phải rỗng` đỏ ngay ở lần chạy sau. Lúc
      ấy tưởng là lỗi sản phẩm, mất một lúc mới thấy lỗi ở phép đo;
    * và tệ hơn: bộ kiểm **ghi vào thư mục nhà của người chạy nó**. Một bộ kiểm để lại rác
      ngoài kho là một bộ kiểm không ai dám chạy hai lần.

    `Path.home()` đọc `$HOME` trên POSIX, nên đặt biến ấy là đủ — không phải vá từng hàm.

    **Lối ra:** ca nào cần MÁY THẬT thì đánh dấu `@pytest.mark.nha_that`. Có thật những ca
    như thế: `test_xay_dung` gọi `arduino-cli`, mà nó cất chuỗi công cụ dưới `$HOME` — đổi nhà
    là nó tải lại từ đầu rồi biên dịch hỏng. Cách ly mọi thứ bằng mọi giá sẽ biến ba ca đo
    **máy thật** thành ba ca đo một thư mục rỗng.
    """
    if request.node.get_closest_marker("nha_that") is not None:
        return None
    nha = tmp_path_factory.mktemp("nha")
    monkeypatch.setenv("HOME", str(nha))
    return nha
