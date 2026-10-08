# -*- coding: utf-8 -*-
"""M4-06 — EIDE tự đo độ nhạy sau khi test xanh, và (sau cờ) tự nâng bộ kiểm.

Điều bộ này canh, một câu: **một lời dặn trong mô tả công cụ không phải một cơ chế.**

Mô tả `test.sensitivity` dặn *"Gọi nó SAU khi test.run xanh, trước khi nói với người dùng rằng
đã kiểm xong"*. Câu ấy đúng và không ai ép: `grep sensitivity` trong `hooks/` và `loop.py` ra
rỗng, nên suốt bao nhiêu phiên, `test.run` xanh rồi tác tử báo "đã kiểm xong" — và không lượt
nào đi đo xem bộ kiểm ấy canh được gì.

Hai nửa của nhiệm vụ này:

* **Luôn làm, không cần cờ** — kết quả đo vào kho kèm `deps.upstream`, để sửa một tệp test hay
  một tệp sản phẩm làm con số độ nhạy **lỗi thời** thay vì nằm đó như còn đúng.
* **Sau cờ `TEST_HARDEN`** — Stop hook nhắc khi test xanh mà chưa ai đo, và công cụ
  `test.harden` chạy một vòng CÓ TRẦN để thêm ca giết mutant còn sống. Sau cờ vì nó đổi thứ
  tác tử đọc mỗi lượt và đổi việc nó làm được (N-4).

Chỗ khó nhất của `test.harden`, và là lý do nó cần một tác tử con riêng: ca mới do mô hình
viết **phải được EIDE tự kiểm hai lần chạy** — XANH trên mã gốc và ĐỎ trên mutant. Thiếu phép
kiểm ấy thì vòng tự nâng sẽ sinh ra những ca xanh-mãi-mãi, tức là nó làm con số độ nhạy đẹp lên
mà bộ kiểm không khá hơn: đúng cái bệnh cả mảng này đi chữa, lần này do chính cái chữa gây ra.
"""

from __future__ import annotations

import shutil

import pytest

from eide.hooks.base import HookBus
from eide.hooks.standard import register_standard_hooks

_EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
       "confidence": "VANG"}

MA_TEST = "sim_result:unit-test"
MA_DO_NHAY = "sim_result:test-sensitivity"

co_cc = bool(shutil.which("cc") or shutil.which("clang") or shutil.which("gcc"))
can_cc = pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")

# Tệp test tự dịch được MỘT MÌNH — `chay(None)` là mốc và nó chỉ dịch tệp test. Xem việc còn
# mở trong `toi-uu/DANG-LAM.md`: một tệp test gọi hàm sản phẩm sẽ làm mốc ĐỎ, và cả phép đo
# dừng trước khi vào vòng đột biến.
_TEST_XANH = ('#include <stdio.h>\n'
              'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"a\\",\\"dat\\":true}]}\\n");'
              ' return 0; }\n')
_SAN_PHAM = "int nguong(void){ return 480; }\nint cho(int x){ return x == 1; }\n"


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1",
                       agent=agent)


def _du_an(agent, *, san_pham: str = _SAN_PHAM, tep_test: str = _TEST_XANH):
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "firmware" / "sp.c").write_text(san_pham, "utf-8")
    (goc / "test" / "t.c").write_text(tep_test, "utf-8")
    return goc


# =============================================== phần LUÔN LÀM: kết quả đo vào kho

@can_cc
def test_sensitivity_ghi_hien_vat(make_agent):
    """TC-M4-06-01 — phép đo phải vào kho. Một phép đo không vào kho thì bằng chưa đo.

    Con số nó tìm ra tắt theo lượt: lượt sau không ai biết nó từng xảy ra, và không bề mặt
    nào hiện được nó. Cùng cái mẫu DEV-341 đã chữa cho Fact → ERC.
    """
    agent = make_agent([])
    _du_an(agent)
    r = agent.registry.run("test.sensitivity", {
        "explain": _EX, "nguon": ["firmware/sp.c"], "test": ["test/t.c"]}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")

    a = agent.store.get(MA_DO_NHAY)
    assert a is not None, "kết quả đo không vào kho"
    assert a["canonical"]["muc"] == "tep", a["canonical"].get("muc")


@can_cc
def test_hien_vat_do_nhay_co_DEPS_UPSTREAM(make_agent):
    """Hiện vật phải khai `deps.upstream` gồm tệp test VÀ tệp sản phẩm.

    Thiếu nó thì sửa một tệp test rồi con số độ nhạy cũ **nằm đó như còn đúng** — và một con
    số đã lỗi thời mà không ai đánh dấu thì tệ hơn không có con số: nó dừng việc đo lại.
    """
    agent = make_agent([])
    _du_an(agent)
    r = agent.registry.run("test.sensitivity", {
        "explain": _EX, "nguon": ["firmware/sp.c"], "test": ["test/t.c"]}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")

    up = ((agent.store.get(MA_DO_NHAY) or {}).get("deps") or {}).get("upstream") or []
    assert any("test/t.c" in str(x) for x in up), up
    assert any("firmware/sp.c" in str(x) for x in up), up


# ================================== phần SAU CỜ: Stop hook nhắc khi test xanh mà chưa đo

def _dat_test_xanh(agent):
    agent.store.apply(artefact_id=MA_TEST, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "so_ca": 3, "so_dat": 3, "so_hong": 0})


def test_hook_bat_khi_test_xanh_chua_do_nhay(make_agent, monkeypatch):
    """TC-M4-06-02 — test xanh mà chưa ai đo độ nhạy thì hook phải nhắc, và MỞ KHOÁ công cụ.

    Mở khoá là nửa thứ hai và nó bắt buộc: `test.sensitivity` là `core=False`, tức tác tử chỉ
    thấy nó sau `tool.search`. Bảo ai đó dùng một thứ họ không nhìn thấy thì không phải là
    bảo — đo được đúng thế ở hook `kiem_viec_chua_ai_kiem` trên phiên FreeRTOS: hook nổ hai
    lượt liền và tác tử không gọi lần nào.
    """
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([])
    agent.config.features = Features.load()
    assert agent.config.features.bat("test_harden") is True
    _dat_test_xanh(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx(agent))
    # Soi `fired`, không soi riêng `another_round`: `bus.stop` chạy MỌI hook Stop và gộp lại,
    # nên một hook khác (`kiem_viec_chua_ai_kiem` chẳng hạn) cũng làm `another_round` thành
    # True. Một ca kiểm soi con cờ gộp ấy sẽ xanh vì một hook khác — và nó xanh cả khi hook
    # này chưa tồn tại.
    assert any("test_xanh_chua_do_nhay" in x for x in r.fired), r.fired
    assert r.another_round is True, r
    assert "test.sensitivity" in agent.registry._unlocked, sorted(agent.registry._unlocked)
    assert "độ nhạy" in (r.injection or ""), r.injection


def test_co_tat_thi_hook_im(make_agent):
    """TC-M4-06-03 — cờ TẮT thì không hook nào mới, không nhắc gì.

    Mặc định TẮT vì hook này chèn chữ vào transcript mỗi lượt, tức đổi thứ mô hình đọc (N-4).
    """
    agent = make_agent([])
    assert agent.config.features.bat("test_harden") is False, "cờ phải mặc định TẮT"
    _dat_test_xanh(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx(agent))
    assert not any("test_xanh_chua_do_nhay" in x for x in r.fired), r.fired
    assert "test.sensitivity" not in agent.registry._unlocked


def test_hook_IM_khi_da_do_nhay_SAU_khi_test_xanh(make_agent, monkeypatch):
    """Đã đo rồi thì im. Một hook nhắc mãi sẽ bị tắt, và lúc ấy nó không canh được gì nữa."""
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([])
    agent.config.features = Features.load()
    _dat_test_xanh(agent)
    # Hiện vật đo phải mang `version_test` của hiện vật test lúc đo — đúng như công cụ ghi.
    # Hook so PHIÊN BẢN chứ không so mốc thời gian: `updated_at` có độ phân giải thô, nên hai
    # lần ghi trong cùng một giây bằng nhau và phép so "mới hơn" im lặng sai.
    v = (agent.store.get(MA_TEST) or {}).get("version")
    agent.store.apply(artefact_id=MA_DO_NHAY, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"muc": "tep", "so_thay": 1, "version_test": v})

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx(agent))
    assert not any("test_xanh_chua_do_nhay" in x for x in r.fired), r.fired


def test_hook_NHAC_LAI_khi_test_chay_lai_sau_lan_do(make_agent, monkeypatch):
    """Test chạy lại SAU lần đo thì con số độ nhạy cũ không còn nói về bộ kiểm hiện tại.

    Đây là lý do mốc thời gian đáng kể: so `updated_at` chứ không chỉ hỏi "đã có hiện vật
    chưa". Hỏi kiểu sau thì một lần đo duy nhất ở đầu dự án khoá hook im mãi mãi.
    """
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([])
    agent.config.features = Features.load()
    # Đo TRƯỚC (lúc chưa có hiện vật test), rồi `test.run` chạy → phiên bản test đổi, nên
    # con số đo cũ không còn nói về bộ kiểm hiện tại.
    agent.store.apply(artefact_id=MA_DO_NHAY, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"muc": "tep", "version_test": None})
    _dat_test_xanh(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx(agent))
    assert any("test_xanh_chua_do_nhay" in x for x in r.fired), r.fired


def test_hook_IM_khi_test_DO(make_agent, monkeypatch):
    """Test đang ĐỎ thì việc cần làm là sửa cho nó xanh, không phải đi đo độ nhạy.

    Nhắc đo độ nhạy lúc bộ kiểm còn đỏ là nhắc một việc không làm được: `do_do_nhay` sẽ trả
    ngay *"bộ kiểm đang ĐỎ từ trước khi đột biến"*.
    """
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([])
    agent.config.features = Features.load()
    agent.store.apply(artefact_id=MA_TEST, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "so_ca": 3, "so_hong": 1})

    bus = register_standard_hooks(HookBus())
    r = bus.stop(_ctx(agent))
    assert not any("test_xanh_chua_do_nhay" in x for x in r.fired), r.fired


def test_hook_moi_luot_chi_nhac_MOT_lan(make_agent, monkeypatch):
    """Nhắc hai lượt liền cho cùng một chuyện là cách một lời nhắc bị học thành tiếng ồn."""
    from eide.config import Features

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([])
    agent.config.features = Features.load()
    _dat_test_xanh(agent)

    bus = register_standard_hooks(HookBus())
    ctx = _ctx(agent)
    assert any("test_xanh_chua_do_nhay" in x for x in bus.stop(ctx).fired)
    assert not any("test_xanh_chua_do_nhay" in x for x in bus.stop(ctx).fired), (
        "nhắc lại trong cùng một lượt")


# ======================================= phần SAU CỜ: công cụ test.harden

def test_cong_cu_harden_chi_co_khi_CO_BAT(make_agent, monkeypatch):
    """TC — cờ TẮT thì công cụ KHÔNG được đăng ký, không chỉ bị giấu.

    Không đăng ký là mạnh hơn giấu: tác tử không gọi được, và lược đồ công cụ không tăng một
    token nào (SCH-44 §2.1).
    """
    from eide.config import Features
    from eide.tools import build_registry

    assert build_registry().get("test.harden") is None, "cờ TẮT mà công cụ vẫn đăng ký"

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    reg = build_registry(Features.load())
    t = reg.get("test.harden")
    assert t is not None, "cờ BẬT mà không có công cụ"
    assert t.core is False, "core=True là nạp lược đồ này vào MỌI lượt"
    assert t.feature == "test_harden", t.feature


def test_subagent_test_writer_KHONG_ghi_duoc_ngoai_test():
    """Tác tử con viết test không được sửa mã sản phẩm.

    Cho nó quyền ấy là cho đúng cái tác tử đang bị đo sửa thứ nó bị đo — và lần này tệ hơn
    `sim-runner` (xem M4-02): ở đây nó có động cơ rõ ràng, vì việc của nó là làm cho mutant
    chết.
    """
    from eide.subagent import SUBAGENT

    dn = SUBAGENT.get("test-writer")
    assert dn is not None, sorted(SUBAGENT)
    assert "fs.write" in dn.cong_cu and "test.run" in dn.cong_cu, dn.cong_cu
    # Không có công cụ nào sửa được mã sản phẩm hay chạm bo.
    assert not ({"fs.edit", "build.compile", "target.flash"} & set(dn.cong_cu)), dn.cong_cu
    assert "test/" in dn.system, "system prompt không nói ra giới hạn ghi"


@can_cc
def test_harden_loai_ca_khong_do_tren_mutant(make_agent, monkeypatch):
    """TC-M4-06-04 — ca mới luôn XANH thì bị LOẠI, và nói ra vì sao.

    Đây là ca đắt nhất của nhiệm vụ. Một vòng tự nâng nhận mọi ca do mô hình viết sẽ sinh ra
    đúng thứ cả mảng này đi chữa: ca xanh mãi mãi, làm con số độ nhạy đẹp lên mà bộ kiểm
    không khá hơn một chút nào. Nên EIDE phải **tự chạy hai lần**: XANH trên mã gốc, ĐỎ trên
    mutant. Chỉ một trong hai không đúng là loại.
    """
    from eide.config import Features
    from eide.llm import Response, ToolCall
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([
        # `fs.read` TRƯỚC: `fs.write` lên một tệp đang có mà lượt này chưa đọc trọn thì bị
        # từ chối bằng E4020 — một hàng rào có sẵn, và nó bắt đúng ở đây. Kịch bản phải đi
        # đúng đường thật, không thì ca kiểm đo một đường khác đường tác tử đi.
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "test/t.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "test/t.c", "explain": _EX,
            # Ca "mới" này xanh bất kể sản phẩm làm gì.
            "content": ('#include <stdio.h>\nint main(void){ printf("{\\"ca\\": '
                        '[{\\"ten\\":\\"luon_xanh\\",\\"dat\\":true}]}\\n"); return 0; }\n')})]),
        Response(text='Báo cáo:\n{"tom_tat": "đã thêm ca", "da_lam": ["sửa test/t.c"], '
                      '"bang_chung": [{"kind": "file", "ref": "test/t.c"}], '
                      '"chua_lam": [], "ket_luan": "dat", "do_tin": "DONG"}'),
    ])
    agent.config.features = Features.load()
    agent.registry = build_registry(agent.config.features)
    _du_an(agent)

    t = agent.registry.get("test.harden")
    assert t is not None
    r = t.fn(_ctx(agent), explain=_EX, nguon=["firmware/sp.c"], test=["test/t.c"],
             max_vong=1, toi_da_goi=6)
    d = r if isinstance(r, dict) else getattr(r, "data", {}) or {}
    assert d.get("so_ca_nhan") == 0, d
    assert d.get("so_ca_loai", 0) >= 1, d
    assert any("không giết được mutant" in str(x.get("vi_sao", "")) for x in d.get("loai", [])), (
        [x.get("vi_sao") for x in d.get("loai", [])], d.get("note_vi"))
    # Và bộ kiểm phải được TRẢ LẠI: một ca bị loại mà còn nằm trong `test/` là một ca xanh
    # mãi mãi ở lại trong dự án — đúng thứ cả mảng này đi chữa.
    assert (agent.config.paths.project_root / "test" / "t.c").read_text("utf-8") == _TEST_XANH
    assert "không giết được mutant" in d["note_vi"], d["note_vi"]


@can_cc
def test_harden_dung_o_tran_vong(make_agent, monkeypatch):
    """TC-M4-06-05 — trần vòng là trần CỨNG: `max_vong=1` thì đúng một vòng.

    Một vòng tự nâng không có trần là một vòng tiêu tiền mô hình tới khi hết hạn mức, và
    `chi_tiet` mất 0,6 s mỗi lượt biên dịch + chạy (DEV-350) nên trần phải tính bằng số đo
    ấy. Ca này cấp đúng kịch bản cho MỘT vòng: thêm vòng nữa là `ScriptedGateway` hết kịch
    bản, và chuyện đó phải không xảy ra.
    """
    from eide.config import Features
    from eide.llm import Response
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([
        Response(text='Báo cáo:\n{"tom_tat": "không viết được ca nào", "da_lam": [], '
                      '"bang_chung": [], "chua_lam": ["chưa nghĩ ra ca"], '
                      '"ket_luan": "chua_du_du_kien", "do_tin": "DONG"}'),
    ])
    agent.config.features = Features.load()
    agent.registry = build_registry(agent.config.features)
    _du_an(agent)

    t = agent.registry.get("test.harden")
    r = t.fn(_ctx(agent), explain=_EX, nguon=["firmware/sp.c"], test=["test/t.c"],
             max_vong=1, toi_da_goi=6)
    d = r if isinstance(r, dict) else getattr(r, "data", {}) or {}
    assert d.get("so_vong") == 1, d
    assert d.get("so_ca_nhan") == 0, d


@can_cc
def test_hien_vat_do_nhay_mang_PHIEN_BAN_cua_hien_vat_test(make_agent):
    """Hiện vật đo phải mang `version_test` — mốc để hook biết con số còn nói về bộ kiểm nào.

    Không có nó thì hook chỉ hỏi được *"đã có hiện vật đo chưa"*, và một lần đo duy nhất ở
    đầu dự án khoá hook im mãi mãi — trong khi mỗi lần `test.run` chạy lại là con số cũ không
    còn nói về bộ kiểm hiện tại.

    Và nó phải là **phiên bản**, không phải mốc thời gian: `updated_at` có độ phân giải thô,
    nên hai lần ghi trong cùng một giây bằng nhau và phép so "mới hơn" im lặng sai — trúng
    ngay ở ca kiểm đầu tiên của hook này.
    """
    agent = make_agent([])
    _du_an(agent)
    _dat_test_xanh(agent)
    v = (agent.store.get(MA_TEST) or {}).get("version")

    r = agent.registry.run("test.sensitivity", {
        "explain": _EX, "nguon": ["firmware/sp.c"], "test": ["test/t.c"]}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", "")

    c = (agent.store.get(MA_DO_NHAY) or {}).get("canonical") or {}
    assert c.get("version_test") == v, (c.get("version_test"), v)


@can_cc
def test_harden_loai_ca_DO_NGAY_tren_ma_that(make_agent, monkeypatch):
    """Ca mới ĐỎ ngay trên mã thật cũng bị LOẠI — phép nhận đòi CẢ HAI chiều.

    Chỉ đòi "đỏ trên mutant" là nhận cả những ca đỏ sẵn: bộ kiểm thành đỏ vĩnh viễn, và lượt
    sau `do_do_nhay` trả ngay *"bộ kiểm đang ĐỎ từ trước khi đột biến"* — vòng tự nâng tự khoá
    chính nó lại, bằng một ca mà nó vừa nhận.
    """
    from eide.config import Features
    from eide.llm import Response, ToolCall
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "test/t.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "test/t.c", "explain": _EX,
            # Ca này ĐỎ với mã thật (`nguong()` trả 480, không phải 999).
            "content": ('#include <stdio.h>\nint nguong(void);\n'
                        'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"sai\\",\\"dat\\":'
                        '%s}]}\\n", nguong() == 999 ? "true" : "false"); return 0; }\n')})]),
        Response(text='Báo cáo:\n{"tom_tat": "đã thêm ca", "da_lam": ["sửa test/t.c"], '
                      '"bang_chung": [{"kind": "file", "ref": "test/t.c"}], '
                      '"chua_lam": [], "ket_luan": "dat", "do_tin": "DONG"}'),
    ])
    agent.config.features = Features.load()
    agent.registry = build_registry(agent.config.features)
    _du_an(agent)

    t = agent.registry.get("test.harden")
    r = t.fn(_ctx(agent), explain=_EX, nguon=["firmware/sp.c"], test=["test/t.c"],
             max_vong=1, toi_da_goi=6)
    d = r if isinstance(r, dict) else getattr(r, "data", {}) or {}
    assert d.get("so_ca_nhan") == 0, d
    assert any("ĐỎ ngay trên mã thật" in str(x.get("vi_sao", "")) for x in d.get("loai", [])), (
        [x.get("vi_sao") for x in d.get("loai", [])])
    assert (agent.config.paths.project_root / "test" / "t.c").read_text("utf-8") == _TEST_XANH


@can_cc
def test_harden_dung_o_TRAN_LOI_GOI_du_con_mutant(make_agent, monkeypatch):
    """Trần lời gọi là trần thứ hai, độc lập với trần vòng.

    `max_vong` chặn theo số mutant; `toi_da_goi` chặn theo **tiền mô hình**. Cần cả hai vì một
    mutant có thể tốn nhiều lượt gọi (tác tử con có `toi_da_goi=8` riêng), nên ba mutant
    "trong trần vòng" vẫn có thể là hai mươi lượt mô hình.
    """
    from eide.config import Features
    from eide.llm import Response
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_TEST_HARDEN", "1")
    agent = make_agent([
        Response(text='Báo cáo:\n{"tom_tat": "chưa nghĩ ra", "da_lam": [], "bang_chung": [], '
                      '"chua_lam": ["x"], "ket_luan": "chua_du_du_kien", "do_tin": "DONG"}'),
    ])
    agent.config.features = Features.load()
    agent.registry = build_registry(agent.config.features)
    _du_an(agent)

    t = agent.registry.get("test.harden")
    # Trần vòng cho 3 mutant, nhưng trần lời gọi chỉ cho 1 — nên đúng MỘT mutant được thử,
    # và `ScriptedGateway` chỉ có một kịch bản (thử mutant thứ hai là hết kịch bản).
    r = t.fn(_ctx(agent), explain=_EX, nguon=["firmware/sp.c"], test=["test/t.c"],
             max_vong=3, toi_da_goi=1)
    d = r if isinstance(r, dict) else getattr(r, "data", {}) or {}
    assert d.get("so_goi", 0) >= 1, d
    assert d.get("so_ca_loai", 0) == 1, d
    assert d.get("so_vong", 0) >= 1, d


def test_bo_do_tai_lieu_dem_ca_cong_cu_sau_CO_KHAC_schematic():
    """`kiem_tai_lieu` phải đếm công cụ sau MỌI cờ, không chỉ sau `schematic`.

    Docstring của `_tat_ca_cong_cu` tự khai là *"kể cả công cụ nằm sau cờ tính năng"*, nhưng
    bản cũ bật đúng một cờ theo TÊN. Thêm `test.harden` (cờ `test_harden`) là nó báo một công
    cụ **có thật** thành "không tồn tại" — và một bảng đầy báo động sai thì không ai đọc tới
    dòng thứ ba, đúng điều docstring ấy nói.

    Đây cũng là mẫu `cong_cu_bi_khoa` đã chọn tránh: lấy từ **danh sách cờ** (`ten_co()`),
    không từ một tên gõ cứng, vì cái quên cập nhật sẽ là cái lọt qua.
    """
    import sys
    from pathlib import Path as _P

    sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "tools"))
    from kiem_tai_lieu import _cong_cu_that

    ten = _cong_cu_that()
    assert "test.harden" in ten, "công cụ sau cờ `test_harden` bị bỏ sót"
    assert "sch.compose" in ten, "công cụ sau cờ `schematic` bị bỏ sót"
