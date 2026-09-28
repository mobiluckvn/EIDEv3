# -*- coding: utf-8 -*-
"""Tác tử TỰ BÙ NĂNG LỰC: `tool.propose` → người duyệt → tự viết → `tool.reload`.

Anh Công, 28/09/2026: *"Agent cũng cần tự thấy thiếu công cụ để viết thêm (tự viết thêm năng
lực)."* Và khi được trình ba hướng, anh chọn hướng đi xa nhất: **tự viết tool thật, qua cổng**.

Số đo làm chặng này ra đời, từ phiên bo STM32F469: tác tử có `pc = 0x08000db0`, cần biết hàm
nào ở đó, gọi **`fs.read` 28 lần**, hết hạn mức 40 lời gọi rồi dừng giữa việc mà vẫn chưa
chắc. `arm-none-eabi-addr2line` trả lời trong **40 ms**. Nó không thiếu thông minh — nó thiếu
**cái miệng** để nói *"tôi cần một công cụ"*.

Bộ này canh bốn hàng rào, vì tác tử ở đây ghi mã Python chạy trong chính tiến trình EIDE.
"""

from __future__ import annotations

import pytest

from eide.nang_luc import duong_ma, duong_test, kiem_de_xuat


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


_EX = {"summary": "xin tự viết code.symbolize", "why": "cày fs.read 28 lần vẫn chưa chắc",
       "sources": [], "diff_prev": "—", "next": "viết mã + test", "confidence": "CAU_HINH"}
_DX = {"ten": "code.symbolize", "nhom": "Mã nguồn",
       "viec": "đổi địa chỉ thành tên hàm và tệp:dòng, đọc từ bảng ký hiệu của ELF",
       "vi_sao": ("tôi đã gọi fs.read 28 lần để dò hàm ở pc 0x08000db0 rồi hết hạn mức 40 "
                  "lời gọi mà vẫn chưa chắc; addr2line trả lời trong 40 ms"),
       "test": "3 ca: có ký hiệu · không có ký hiệu · thiếu ELF (phải nói CHƯA TRA ĐƯỢC)"}


# ===================================================== hàng rào 1: đề xuất phải nói được gì
def test_vi_sao_PHAI_co_so_do_khong_phai_cam_giac(make_agent):
    """Phần `vi_sao` là phần người dùng đọc để quyết. "Tôi thấy hơi chậm" không đủ để ai
    quyết; "tôi gọi fs.read 28 lần rồi hết hạn mức" thì đủ."""
    agent = make_agent([])
    d = dict(_DX, vi_sao="tôi thấy việc này hơi chậm và bất tiện khi làm bằng tay")
    r = agent.registry.run("tool.propose", {**d, "explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E7001"
    assert "SỐ ĐO" in r.error.message_vi


def test_test_chua_noi_kiem_ca_nao_thi_bi_chan(make_agent):
    agent = make_agent([])
    r = agent.registry.run("tool.propose", {**dict(_DX, test="sẽ kiểm"), "explain": _EX},
                           _ctx(agent))
    assert not r.ok and "lời hứa thành sự kiện" in r.error.message_vi


@pytest.mark.parametrize("ten", ["Code.Symbolize", "symbolize", "code symbolize", "a.b.c"])
def test_ten_phai_dung_dang_nhom_viec(make_agent, ten):
    agent = make_agent([])
    r = agent.registry.run("tool.propose", {**dict(_DX, ten=ten), "explain": _EX},
                           _ctx(agent))
    assert not r.ok


def test_khong_de_xuat_lai_cong_cu_DA_CO(make_agent):
    agent = make_agent([])
    r = agent.registry.run("tool.propose", {**dict(_DX, ten="fs.read"), "explain": _EX},
                           _ctx(agent))
    assert not r.ok and "đã có công cụ tên" in r.error.message_vi


def test_de_xuat_hop_le_tra_ve_KHUNG_MA_va_duong_dan(make_agent):
    agent = make_agent([])
    r = agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    assert r.ok, getattr(r.error, "message_vi", r)
    assert r.data["duong_ma"] == ".eide/cong-cu/code_symbolize.py"
    assert r.data["duong_test"] == ".eide/cong-cu/test_code_symbolize.py"
    assert "def dang_ky(r)" in r.data["khuon_ma"]
    # Khung mã mang theo ba bài học đã trả giá, để chúng ở ngay chỗ tác tử đang viết.
    assert "`ok` nói về lời gọi" in r.data["khuon_ma"]
    assert "không đo được" in r.data["khuon_ma"]


def test_the_cong_la_G_TOOL_va_R3(make_agent):
    """Tác tử ghi mã chạy trong chính tiến trình EIDE — không thể là thao tác tự động."""
    agent = make_agent([])
    sp = agent.registry.get("tool.propose")
    assert sp.gate == "G-TOOL" and sp.risk == "R3" and sp.needs_explain


# ===================================================== hàng rào 2 + 3: chỉ ghi vào them/, test phải xanh
def test_duong_ma_luon_nam_trong_thu_muc_RIENG():
    """Nguồn gốc của mã phải nhìn thấy được khi ai đó đọc repo về sau. Và tác tử không sửa
    được công cụ đang có: bù năng lực khác với đổi năng lực."""
    for t in ("code.symbolize", "target.doc_gi_do", "a_b.c_d"):
        assert duong_ma(t).startswith(".eide/cong-cu/")
        assert duong_test(t).startswith(".eide/cong-cu/test_")


def test_reload_khi_CHUA_duyet(make_agent):
    agent = make_agent([])
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert not r.ok and r.error.code == "E7002"


def test_reload_khi_THIEU_bo_kiem(make_agent, tmp_path):
    """Công cụ không có bộ kiểm thì nó là một lời hứa, không phải một năng lực."""
    agent = make_agent([])
    agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    goc = agent.config.paths.project_root
    p = goc / duong_ma("code.symbolize")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# chưa có gì\n", "utf-8")
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert not r.ok and r.error.code == "E7003"
    assert "test_code_symbolize.py" in r.error.message_vi


def _viet(agent, ten: str, ma: str, tst: str) -> None:
    goc = agent.config.paths.project_root
    for duong, noi in ((duong_ma(ten), ma), (duong_test(ten), tst)):
        p = goc / duong
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(noi, "utf-8")


def test_BO_KIEM_DO_thi_cong_cu_KHONG_duoc_dang_ky(make_agent):
    """Hàng rào quan trọng nhất. Không có nó thì ta vừa cho tác tử một cách rất nhanh để tự
    tin vào một thứ sai."""
    agent = make_agent([])
    agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    _viet(agent, "code.symbolize",
          "def dang_ky(r):\n    pass\n",
          "def test_do():\n    assert 1 == 2\n")
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert not r.ok and r.error.code == "E7005"
    assert "không được đăng ký" in r.error.message_vi
    assert "Đừng sửa test cho vừa mã" in r.error.hint_for_agent
    assert agent.registry.get("code.symbolize") is None


# ===================================================== hàng rào 4 + trọn vòng đời
_MA_THAT = '''
def doi(dia_chi):
    """Đổi một địa chỉ thành tên hàm. Bảng giả, đủ cho ca kiểm."""
    bang = {0x08000db0: "OTM8009A_Init_Ext"}
    if dia_chi not in bang:
        return {"ham": "", "vi_sao": "không có ký hiệu ở địa chỉ này"}
    return {"ham": bang[dia_chi], "vi_sao": ""}


def dang_ky(r):
    @r.tool("code.symbolize", "Mã nguồn", "đổi địa chỉ thành tên hàm",
            {"type": "object",
             "properties": {"dia_chi": {"type": "array", "items": {"type": "integer"}}},
             "required": ["dia_chi"]},
            risk="R1", core=False)
    def _cs(ctx, dia_chi):
        return {"ky_hieu": {hex(d): doi(d) for d in dia_chi}}
'''

_TEST_THAT = '''
import importlib.util, pathlib
_s = importlib.util.spec_from_file_location(
    "cs", pathlib.Path(__file__).with_name("code_symbolize.py"))
_m = importlib.util.module_from_spec(_s); _s.loader.exec_module(_m)


def test_co_ky_hieu():
    assert _m.doi(0x08000db0)["ham"] == "OTM8009A_Init_Ext"


def test_KHONG_co_ky_hieu_thi_noi_ra_chu_khong_bia():
    r = _m.doi(0x12345678)
    assert r["ham"] == "" and "không có ký hiệu" in r["vi_sao"]


def test_co_ham_dang_ky():
    assert hasattr(_m, "dang_ky")
'''


def test_TRON_VONG_DOI_de_xuat_viet_kiem_nap_dung_duoc(make_agent):
    """Ca quan trọng nhất của bộ này: tác tử đi hết vòng và **dùng được** công cụ nó tự viết.

    Từng mảnh xanh riêng không chứng minh được cái vòng khép lại — mà cái vòng khép lại mới
    là thứ anh Công yêu cầu.
    """
    agent = make_agent([])
    r = agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    assert r.ok
    assert agent.registry.get("code.symbolize") is None, "chưa viết thì chưa có"

    _viet(agent, "code.symbolize", _MA_THAT, _TEST_THAT)
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert r.ok, getattr(r.error, "details", getattr(r.error, "message_vi", r))
    assert r.data["da_dang_ky"] == ["code.symbolize"]

    # Và nó DÙNG ĐƯỢC ngay, không phải khởi động lại EIDE.
    assert agent.registry.get("code.symbolize") is not None
    r = agent.registry.run("code.symbolize", {"dia_chi": [0x08000DB0]}, _ctx(agent))
    assert r.ok and r.data["ky_hieu"]["0x8000db0"]["ham"] == "OTM8009A_Init_Ext"


def test_nap_ma_KHONG_co_dang_ky_thi_tu_choi(make_agent):
    agent = make_agent([])
    agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    _viet(agent, "code.symbolize", "x = 1\n", "def test_ok():\n    assert True\n")
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert not r.ok and r.error.code == "E7006"
    assert "bộ kiểm chưa chạm tới phần đăng ký" in r.error.hint_for_agent


def test_dang_ky_SAI_TEN_so_voi_cai_da_duyet_thi_tu_choi(make_agent):
    """Người dùng duyệt một cái tên cụ thể — đăng ký tên khác là lách cổng."""
    agent = make_agent([])
    agent.registry.run("tool.propose", {**_DX, "explain": _EX}, _ctx(agent))
    ma = ('def dang_ky(r):\n'
          '    @r.tool("code.khac_han", "Mã nguồn", "việc khác",\n'
          '            {"type": "object", "properties": {}}, risk="R1", core=False)\n'
          '    def _x(ctx):\n        return {}\n')
    _viet(agent, "code.symbolize", ma, "def test_ok():\n    assert True\n")
    r = agent.registry.run("tool.reload", {"ten": "code.symbolize"}, _ctx(agent))
    assert not r.ok and r.error.code == "E7007"
    assert "code.khac_han" in str(r.error.details)
