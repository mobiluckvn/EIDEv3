# -*- coding: utf-8 -*-
"""M4-02 — sửa yếu tệp test sau khi đã có kết quả ĐỎ phải đi qua thẻ người.

Điều bộ này canh, một câu: **đường ngắn nhất tới một "đạt" không phải sửa sản phẩm.**

`POL-N6-doi-tieu-chi` đã chặn đường thứ nhất: đổi NGƯỠNG sau khi đã có kết quả. Nhưng còn
đường thứ hai, rộng hơn và không ai canh — **xoá bớt ca test**. Tệp test có ba ca, một ca đỏ;
ghi lại tệp với một ca còn lại là "3/3 đạt", và mọi hàng rào đều im: `fs.write` là một lời gọi
bình thường, `test.run` là một lời gọi bình thường, không luật nào thấy gì lạ.

Và một chỗ nữa của hàng rào cũ đang rỗng: `criteria.has_result` tra **cứng** mã hiện vật
`sim_result:can-bang`. Nên mọi bộ tiêu chí khác `sim-01` — `sim-ntc`, và từ M4-01 là cả
`unit-*` — luôn được coi là "chưa có kết quả", tức `POL-N6-doi-tieu-chi` không bao giờ nổ cho
chúng. Cơ chế có sẵn, đường dẫn tới nó đứt.
"""

from __future__ import annotations

import pytest

from eide.hooks.base import HookBus
from eide.hooks.standard import register_standard_hooks
from eide.policy import PolicyEngine

_EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
       "confidence": "VANG"}

MA_TEST = "sim_result:unit-test"
MA_SIM = "sim_result:can-bang"

# Tệp test ba ca, một ca đỏ. Đây là trạng thái "đã có kết quả đỏ" mà hàng rào phải bảo vệ.
_BA_CA = (
    '#include <stdio.h>\n'
    'int main(void){\n'
    '  printf("{\\"ca\\": ['
    '{\\"ten\\": \\"pid_zero\\", \\"dat\\": true},'
    '{\\"ten\\": \\"pid_bao_hoa\\", \\"dat\\": false, \\"vi\\": \\"ra 300 > 255\\"},'
    '{\\"ten\\": \\"pid_am\\", \\"dat\\": true}'
    ']}\\n");\n'
    '  return 0;\n}\n')
# Cùng tệp, bỏ hai ca — trong đó có đúng cái ca đang đỏ.
_MOT_CA = (
    '#include <stdio.h>\n'
    'int main(void){\n'
    '  printf("{\\"ca\\": [{\\"ten\\": \\"pid_zero\\", \\"dat\\": true}]}\\n");\n'
    '  return 0;\n}\n')


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1",
                       agent=agent)


def _ket_qua_do(agent, ma: str = MA_TEST) -> None:
    agent.store.apply(artefact_id=ma, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "so_ca": 3, "so_dat": 2, "so_hong": 1})


def _tieu_chi(agent, ctx, *, ma: str, nguong: float = 15.0) -> None:
    r = agent.registry.run("sim.criteria", {
        "ma": ma, "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=",
                    "nguong": nguong, "nguon_nguong": "đề bài"}],
        "trich_loi": "Tôi đồng ý."}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")


# ============================================ TC-M4-02-01: has_result theo MÃ TIÊU CHÍ

def test_has_result_theo_ma_tieu_chi(make_agent):
    """TC-M4-02-01 — kết quả của `sim-ntc` phải làm `has_result` của `sim-ntc` thành True.

    Bản cũ tra cứng `sim_result:can-bang`, nên một dự án dùng mã tiêu chí khác đi qua cổng
    N6 **mà không ai hỏi gì**. Đúng hình dạng "cơ chế có sẵn, đường dẫn tới nó đứt": luật
    `POL-N6-doi-tieu-chi` viết đúng, và nó chưa bao giờ nổ ngoài `sim-01`.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    _tieu_chi(agent, ctx, ma="sim-ntc")
    # Kết quả nằm ở MỘT KHOÁ KHÁC `can-bang`, và nó khai `ma_tieu_chi`.
    agent.store.apply(artefact_id="sim_result:ntc", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "ma_tieu_chi": "sim-ntc"})
    assert agent.store.get(MA_SIM) is None, "dàn dựng sai: ca này phải KHÔNG có can-bang"

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "sim.criteria", "args": {
        "ma": "sim-ntc", "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 45.0}]}},
        ctx)
    assert r.facts["criteria.exists"] and r.facts["criteria.changed"]
    assert r.facts["criteria.has_result"] is True, r.facts
    assert "A1.nguong: 15.0 → 45.0" in r.facts["criteria.doi_gi"]


def test_has_result_khong_keu_cho_tieu_chi_KHAC(make_agent):
    """Ca âm của phép trên: kết quả của `sim-ntc` KHÔNG làm `sim-01` thành có-kết-quả.

    Nếu chỉ cần "có hiện vật sim_result nào đó" là đủ, thì thêm một bộ mô phỏng thứ hai sẽ
    khoá cổng N6 cho **mọi** bộ tiêu chí — kể cả bộ chưa chạy lần nào. Hỏi ở đó dạy người
    dùng bấm duyệt theo phản xạ.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    _tieu_chi(agent, ctx, ma="sim-01")
    agent.store.apply(artefact_id="sim_result:ntc", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "ma_tieu_chi": "sim-ntc"})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "sim.criteria", "args": {
        "ma": "sim-01", "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 45.0}]}},
        ctx)
    assert r.facts["criteria.changed"] is True
    assert r.facts["criteria.has_result"] is False, r.facts


def test_has_result_giu_duong_cu_cho_can_bang(make_agent):
    """Hiện vật cũ `sim_result:can-bang` KHÔNG khai `ma_tieu_chi` — vẫn phải tính cho sim-01.

    Mọi kho đã lưu trước hôm nay đều ở trạng thái ấy. Một phép tra chỉ nhận hiện vật mới sẽ
    **nới hàng rào** đúng ở những dự án đã chạy thật.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    _tieu_chi(agent, ctx, ma="sim-01")
    agent.store.apply(artefact_id=MA_SIM, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX, canonical={"dat": False})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "sim.criteria", "args": {
        "ma": "sim-01", "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 45.0}]}},
        ctx)
    assert r.facts["criteria.has_result"] is True, r.facts


def test_has_result_cho_ca_tieu_chi_UNIT_TEST(make_agent):
    """M4-01 vừa thêm `criteria:unit-*`; cổng N6 phải nổ cho chúng nữa.

    Không thì `test.criteria` thành một cửa sau: đổi ngưỡng unit test sau khi đã có kết quả
    đỏ mà không ai hỏi, trong khi cùng việc ấy ở `sim.criteria` thì phải qua thẻ.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    r0 = agent.registry.run("test.criteria", {
        "ma": "unit-01", "explain": _EX,
        "assert": [{"ma": "T1", "mo_ta": "Ra PWM", "phep_so": "<=", "nguong": 255,
                    "nguon_nguong": "PWM 8 bit"}],
        "trich_loi": "Tôi đồng ý."}, ctx)
    assert r0.ok, getattr(r0.error, "message_vi", "")
    agent.store.apply(artefact_id=MA_TEST, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "ma_tieu_chi": "unit-01",
                                 "che_do": "eide_phan"})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "test.criteria", "args": {
        "ma": "unit-01", "explain": _EX,
        "assert": [{"ma": "T1", "mo_ta": "Ra PWM", "phep_so": "<=", "nguong": 999}]}}, ctx)
    assert r.facts["criteria.exists"] is True, r.facts
    assert r.facts["criteria.changed"] is True, r.facts
    assert r.facts["criteria.has_result"] is True, r.facts
    assert "255" in r.facts["criteria.doi_gi"] and "999" in r.facts["criteria.doi_gi"]


def test_has_result_ep_tien_to_unit_khi_tac_tu_chi_gui_so(make_agent):
    """`test.criteria(ma="01")` ghi hiện vật `criteria:unit-01` — hook phải tra ĐÚNG khoá ấy.

    Hook lặp lại quy ước đặt khoá của công cụ. Nếu nó không ép tiền tố thì nó tra
    `criteria:01` — một khoá không tồn tại — và kết luận "tiêu chí mới" cho **mọi** lần đổi
    ngưỡng. Cổng N6 im, và cái im ấy trông y như "không có gì đổi".
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    r0 = agent.registry.run("test.criteria", {
        "ma": "01", "explain": _EX,
        "assert": [{"ma": "T1", "mo_ta": "Ra PWM", "phep_so": "<=", "nguong": 255,
                    "nguon_nguong": "PWM 8 bit"}],
        "trich_loi": "Tôi đồng ý."}, ctx)
    assert r0.ok and agent.store.get("criteria:unit-01") is not None, r0.data

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "test.criteria", "args": {
        "ma": "01", "explain": _EX,
        "assert": [{"ma": "T1", "mo_ta": "Ra PWM", "phep_so": "<=", "nguong": 999}]}}, ctx)
    assert r.facts["criteria.exists"] is True, (
        "hook tra sai khoá, nên mọi lần đổi ngưỡng đọc thành “tiêu chí mới”")
    assert r.facts["criteria.changed"] is True, r.facts


# ============================================ TC-M4-02-02: xoá ca test sau kết quả đỏ

def test_xoa_ca_test_sau_ket_qua_do_thi_weakened(make_agent):
    """TC-M4-02-02 — ba ca thành một ca, sau khi đã có kết quả đỏ → `test.weakened`.

    Và `test.doi_gi` phải nói **từ bao nhiêu sang bao nhiêu**. Một thẻ hỏi "sửa tệp test?"
    mà không nói nó bỏ mất gì thì người dùng bấm duyệt theo phản xạ — đúng lý do mà hook
    `doi_tieu_chi` phải hiện "15.0 → 45.0" chứ không chỉ hiện "đổi ngưỡng".
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test" / "test_pid.c").write_text(_BA_CA, "utf-8")
    _ket_qua_do(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "test/test_pid.c", "content": _MOT_CA, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is True, r.facts
    doi = r.facts["test.doi_gi"]
    assert "3" in doi and "1" in doi, doi


def test_fs_edit_xoa_dong_FAIL_cung_tinh_la_weakened(make_agent):
    """`fs.edit` phải được áp `old`→`new` rồi mới đếm, không chỉ xét `content`.

    Nếu hook chỉ đọc `content` thì `fs.edit` là một cửa sau rộng bằng `fs.write`: xoá đúng
    cái dòng in `FAIL` bằng một phép thay chuỗi nhỏ, và không ai thấy gì.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    tb = (goc / "test" / "tb_dem.v")
    tb.write_text(
        "module tb_dem;\n"
        "  initial begin\n"
        '    if (q !== 4\'d5) $display("KET QUA: FAIL q=%0d", q);\n'
        '    else $display("KET QUA: PASS");\n'
        "  end\n"
        "endmodule\n", "utf-8")
    agent.store.apply(artefact_id="build:hdl:sim", type="build", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": False, "pass_fail": "FAIL"})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.edit", "args": {
        "path": "test/tb_dem.v", "explain": _EX,
        "old": '    if (q !== 4\'d5) $display("KET QUA: FAIL q=%0d", q);\n'
               '    else $display("KET QUA: PASS");\n',
        "new": '    $display("KET QUA: PASS");\n'}}, ctx)
    assert r.facts["test.weakened"] is True, r.facts


def test_so_cho_canh_KHONG_DOI_thi_khong_keu(make_agent):
    """Sửa tệp test mà số chỗ canh **không đổi** là việc thường — đổi tên ca, sửa chữ, dọn mã.

    Phép đo là *"yếu đi bao nhiêu"*, không phải *"có sửa hay không"*. Một hàng rào kêu ở mọi
    lần sửa tệp test sẽ bị tắt, và lúc ấy nó không chặn được gì nữa.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test" / "test_pid.c").write_text(_BA_CA, "utf-8")
    _ket_qua_do(agent)

    doi_ten = _BA_CA.replace("pid_bao_hoa", "pid_tran_pwm")
    assert doi_ten != _BA_CA, "dàn dựng sai: nội dung không đổi gì"
    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "test/test_pid.c", "content": doi_ten, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is False, r.facts


def test_testbench_NGOAI_thu_muc_test_cung_duoc_canh(make_agent):
    """`rtl/tb_dem.v` cũng là tệp đo, dù không nằm trong `test/`.

    Dự án FPGA của anh Công đặt testbench cạnh RTL (`docs/riscv-tn20k/bai3/sim/tb_*.v`, và
    `phien-bo-that-03-10/rtl/`). Một phép lọc chỉ nhận `test/**` sẽ bỏ sót đúng những tệp đo
    của mảng FPGA — mảng mà DEV-344 vừa cho thấy một testbench in PASS vô điều kiện trông y
    như một testbench thật.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "rtl").mkdir(parents=True, exist_ok=True)
    (goc / "rtl" / "tb_dem.v").write_text(
        "module tb_dem;\n"
        '  initial if (q !== 4\'d5) $display("KET QUA: FAIL"); else $display("PASS");\n'
        "endmodule\n", "utf-8")
    agent.store.apply(artefact_id="build:hdl:sim", type="build", op="create",
                      author="agent:run-1", explain=_EX, canonical={"dat": False})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "rtl/tb_dem.v", "explain": _EX,
        "content": 'module tb_dem;\n  initial $display("PASS");\nendmodule\n'}}, ctx)
    assert r.facts["test.weakened"] is True, r.facts


def test_them_ca_test_thi_KHONG_keu(make_agent):
    """Thêm ca test sau một kết quả đỏ là việc ĐÚNG — không được hỏi.

    Ca này quan trọng ngang ca dương: một hàng rào kêu cả khi người ta đang làm đúng thì nó
    bị tắt, và lúc ấy nó không còn chặn được gì nữa.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test" / "test_pid.c").write_text(_MOT_CA, "utf-8")
    _ket_qua_do(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "test/test_pid.c", "content": _BA_CA, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is False, r.facts


# ====================================== TC-M4-02-04: ca âm — không có gì để ép thì im

@pytest.mark.parametrize("dung_kho,duong", [
    (False, "test/test_pid.c"),      # chưa có kết quả nào
    (True, "firmware/pid.c"),        # có kết quả đỏ, nhưng đây là tệp SẢN PHẨM
])
def test_tao_test_moi_hoac_chua_co_ket_qua_thi_KHONG_keu(make_agent, dung_kho, duong):
    """TC-M4-02-04 — chưa có kết quả thì không có gì để ép; và tệp sản phẩm không phải tệp test.

    Sửa mã sản phẩm sau một kết quả đỏ là **đúng việc cần làm**. Nếu hook kêu ở đó thì nó
    chặn đúng con đường duy nhất đi tới chỗ sửa thật.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / duong).parent.mkdir(parents=True, exist_ok=True)
    (goc / duong).write_text(_BA_CA, "utf-8")
    if dung_kho:
        _ket_qua_do(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": duong, "content": _MOT_CA, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is False, r.facts


def test_ket_qua_DAT_thi_sua_test_khong_phai_hoi(make_agent):
    """Kết quả đang XANH thì sửa tệp test là việc thường — không có "đạt" nào đang bị ép."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test" / "test_pid.c").write_text(_BA_CA, "utf-8")
    agent.store.apply(artefact_id=MA_TEST, type="sim_result", op="create",
                      author="agent:run-1", explain=_EX, canonical={"dat": True})

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "test/test_pid.c", "content": _MOT_CA, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is False, r.facts


def test_tep_test_CHUA_CO_tren_dia_thi_khong_keu(make_agent):
    """Tạo tệp test MỚI không bị chặn — chưa có gì để làm yếu đi.

    Kế hoạch ghi rõ chỗ này trong "không được làm", và nó đáng một ca riêng: một hook đọc
    tệp cũ bằng `read_text()` mà không phòng tệp chưa tồn tại sẽ **nổ** ở đúng lượt tác tử
    viết bộ test đầu tiên.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    _ket_qua_do(agent)

    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "fs.write", "args": {
        "path": "test/hoan_toan_moi.c", "content": _BA_CA, "explain": _EX}}, ctx)
    assert r.facts["test.weakened"] is False, r.facts


# ============================================== TC-M4-02-03: luật trong policy.yaml

def test_policy_hoi_G_QUAL_khi_test_bi_sua_yeu():
    """TC-M4-02-03 — `test.weakened` phải thành một thẻ G-QUAL, và không bao giờ tự động.

    Hook chỉ cấp dữ kiện; nếu không có luật nào đọc dữ kiện ấy thì cả phép đo vô nghĩa —
    đúng cái mẫu `kiem_cap_goi_tra()` đang mắc: soát được mà chưa chặn được.
    """
    pol = PolicyEngine()
    d = pol.decide({"tool": "fs.write", "args": {"path": "test/t.c"}},
                   {"explain.complete": True, "constant_guard.unsourced": 0,
                    "test.weakened": True, "test.doi_gi": "3 ca → 1 ca"})
    assert d.action == "ask", f"{d.action} ({d.rule_id})"
    assert d.gate == "G-QUAL", d.gate
    assert d.never_auto is True, "mức tự chủ cao sẽ bỏ qua được thẻ này"


def test_policy_KHONG_hoi_khi_test_khong_bi_sua_yeu():
    pol = PolicyEngine()
    d = pol.decide({"tool": "fs.write", "args": {"path": "test/t.c"}},
                   {"explain.complete": True, "constant_guard.unsourced": 0,
                    "test.weakened": False})
    assert d.action == "allow", f"{d.action} ({d.rule_id})"


@pytest.mark.parametrize("tool,args", [
    ("fs.write", {"path": "m.c"}),
    ("fs.edit", {"path": "test/t.c"}),
    ("sim.criteria", {"ma": "sim-01"}),
    ("test.criteria", {"ma": "unit-01"}),
])
def test_luat_moi_KHONG_lam_do_ca_luot_khi_hook_im(tool, args):
    """Một luật trỏ tới nhóm dữ kiện mà hook chưa cấp thì **dừng cả lượt**, không phải "không nổ".

    `_eval` cố ý ném `ValueError` cho điều kiện không tính được — im lặng cho qua thì tệ hơn.
    Nhưng hệ quả là: nhóm `test` không có trong danh sách "nhóm phải luôn tồn tại" của
    `_env` thì `POL-N6-sua-test` làm **mọi** `fs.write` đổ, kể cả khi hook im đúng cách.

    Đo được ngay khi thêm luật: `test_muc_tu_chu_thap_thi_ghi_phai_hoi` (ca cũ, tự dựng `pre`)
    đỏ với *"Điều kiện policy không tính được: 'test.weakened'"*. Ca này canh chỗ ấy cho cả
    bốn công cụ mà hai luật mới khớp tới.
    """
    pol = PolicyEngine()
    d = pol.decide({"tool": tool, "args": args},
                   {"explain.complete": True, "constant_guard.unsourced": 0})
    assert d.action in ("allow", "ask", "deny"), d


def test_policy_hoi_G_QUAL_khi_doi_nguong_UNIT_TEST():
    """`test.criteria` phải đi qua cùng cái cổng N6 với `sim.criteria`.

    Hook cấp đúng dữ kiện là chưa đủ: nếu `POL-N6-doi-tieu-chi` không liệt `test.criteria`
    trong danh sách công cụ thì dữ kiện ấy không luật nào đọc — và `test.criteria` thành một
    cửa sau cho đúng việc mà `sim.criteria` bị chặn.
    """
    pol = PolicyEngine()
    d = pol.decide({"tool": "test.criteria", "args": {"ma": "unit-01"}},
                   {"explain.complete": True, "criteria.exists": True,
                    "criteria.changed": True, "criteria.has_result": True,
                    "criteria.doi_gi": "T1.nguong: 255 → 999"})
    assert d.action == "ask", f"{d.action} ({d.rule_id})"
    assert d.gate == "G-QUAL", d.gate
    assert d.never_auto is True, d.rule_id


def test_POL_N6_sua_test_khong_bao_gio_tu_dong():
    """Mức tự chủ A4 và công cụ được tin cũng không bỏ qua được — `never_auto`."""
    pol = PolicyEngine()
    pol.autonomy = "A4"
    pol.trusted.add("fs.write")
    d = pol.decide({"tool": "fs.write", "args": {"path": "test/t.c"}},
                   {"explain.complete": True, "constant_guard.unsourced": 0,
                    "test.weakened": True})
    assert d.action == "ask" and d.never_auto is True, f"{d.action} ({d.rule_id})"


# ======================================= TC-M4-02-05: cờ sim_runner_gioi_han, mặc định TẮT

def test_co_tat_sim_runner_van_ghi_duoc_ngoai_sim(make_agent):
    """TC-M4-02-05 — cờ chưa bật thì hành vi cũ giữ nguyên, không E5006.

    Phần siết công cụ của sim-runner đặt sau cờ vì nó **đổi tập việc một tác tử con làm
    được**, tức đổi hành vi tác tử (N-4). Mặc định TẮT cho tới khi có bộ eval nói nó không
    làm sim-runner tệ đi.
    """
    from eide import subagent as SA
    from eide.llm import Response, ToolCall

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "test/x.c", "content": "int main(void){return 0;}\n", "explain": _EX})]),
        Response(text='Báo cáo:\n{"tom_tat": "x", "da_lam": ["a"], "bang_chung": [], '
                      '"chua_lam": [], "ket_luan": "chua_du_du_kien", "do_tin": "DONG"}'),
    ])
    assert agent.config.features.bat("sim_runner_gioi_han") is False, "cờ phải mặc định TẮT"
    so: list = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="sim-runner",
            viec="chạy test", ghi_so=lambda _k, d: so.append(d))
    assert not [d for d in so if d.get("code") == "E5006"], so
    assert (agent.config.paths.project_root / "test" / "x.c").exists(), (
        "cờ TẮT mà lời gọi vẫn không ghi được tệp — đã siết sớm hơn cờ")


def test_co_BAT_thi_sim_runner_khong_ghi_duoc_ngoai_sim(make_agent, monkeypatch):
    """Cờ bật thì `fs.write` của sim-runner ra ngoài `sim/` bị từ chối, kèm lời chỉ đường.

    Vì sao siết đúng sim-runner: nó là tác tử con **nêu tiêu chí và chạy đo**. Cho nó ghi
    vào `test/` là cho đúng cái tác tử đang bị đo quyền sửa thước đo của mình.
    """
    from eide import subagent as SA
    from eide.llm import Response, ToolCall

    monkeypatch.setenv("EIDE_FEATURE_SIM_RUNNER_GIOI_HAN", "1")
    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "test/x.c", "content": "int main(void){return 0;}\n", "explain": _EX})]),
        Response(tool_calls=[ToolCall("c2", "fs.write", {
            "path": "sim/plant.c", "content": "int main(void){return 0;}\n",
            "explain": _EX})]),
        Response(text='Báo cáo:\n{"tom_tat": "x", "da_lam": ["a"], "bang_chung": [], '
                      '"chua_lam": [], "ket_luan": "chua_du_du_kien", "do_tin": "DONG"}'),
    ])
    from eide.config import Features
    agent.config.features = Features.load()
    assert agent.config.features.bat("sim_runner_gioi_han") is True

    so: list = []
    SA.chay(llm=agent.llm, registry=agent.registry, ctx=_ctx(agent), ma="sim-runner",
            viec="chạy test", ghi_so=lambda _k, d: so.append(d))
    goc = agent.config.paths.project_root
    chan = [d for d in so if d.get("code") == "E5006"]
    assert len(chan) == 1, so
    assert not (goc / "test" / "x.c").exists(), "cờ BẬT mà vẫn ghi được vào test/"
    # Và lời gọi thứ hai — ghi vào `sim/` — phải đi qua. Một cái cổng chặn cả đường đúng thì
    # sim-runner không làm được việc của nó, và nó sẽ bị tắt cờ chứ không được dùng.
    assert (goc / "sim" / "plant.c").exists(), "cổng chặn cả đường ghi ĐÚNG vào sim/"


def test_co_moi_co_trong_ten_co_va_to_dict():
    """Cờ không có trong `ten_co()` thì `EIDE_FEATURE_…` không nạp được nó, và tab cờ không
    thấy nó — một cờ chỉ tồn tại trong dataclass là một cờ không bật được."""
    from eide.config import Features

    assert "sim_runner_gioi_han" in Features.ten_co()
    assert "sim_runner_gioi_han" in Features().to_dict()
    assert Features().bat("sim_runner_gioi_han") is False
