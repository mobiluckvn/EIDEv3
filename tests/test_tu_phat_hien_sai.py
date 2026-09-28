# -*- coding: utf-8 -*-
"""Tác tử tự phát hiện cái sai của chính mình — hai cơ chế, hai tầng.

Anh Công, sau phiên bo STM32F469: *"Agent không tự động phát hiện được sai mà bạn phải phát
hiện."* Đúng. Đo trên sổ cái của phiên ấy:

* 402 lượt, 1078 lời gọi, **0 lần gọi subagent** ⇒ `verifier` chạy **0 lần**. Nó không hỏng —
  `CAN_KIEM_CHUNG` chỉ nổ khi một *subagent* tuyên đạt, mà tác tử chính làm hết mọi việc
  trong lượt của nó. Cái van tồn tại, ống dẫn không đi qua nó.
* Và một hình dạng lỗi lặp **năm lần** ở năm tầng: `ok` nói về LỜI GỌI, không nói về KẾT QUẢ.

Bộ này canh hai cơ chế vá hai chỗ đó, và canh cả **chỗ chúng phải im lặng** — một bộ dò kêu
quá tay sẽ thành máy báo động giả trong một buổi chiều.
"""

from __future__ import annotations

import pytest

from eide.ket_qua import khong_noi_gi


# ===================================================== `ok` mà không có gì chuyển động
@pytest.mark.parametrize("ten,args,data", [
    # Ca thật 1: code.vendor_fetch trả ok với 0/26 tệp.
    ("vendor_fetch 0/26", {"tep": ["a"] * 26}, {"so_dat": 0, "so_hong": 26}),
    # Ca thật 2: soi_chip gộp `-c` nên openocd không in `mdw` — xin 4 địa chỉ, nhận rỗng.
    ("soi_chip o_nho rỗng", {"dia_chi": [1, 2, 3, 4]}, {"o_nho": {}, "dat": True}),
    ("tra 5 ký hiệu không ra gì", {"bien": list("abcde")}, {"ky_hieu": {}, "dat": True}),
])
def test_KEU_khi_xin_mot_tap_cu_the_ma_nhan_ve_rong(ten, args, data):
    keu, ly_do = khong_noi_gi(args, data)
    assert keu is True, ten
    assert str(len(args[next(iter(args))])) in ly_do


@pytest.mark.parametrize("ten,args,data", [
    # Một phép TÌM không thấy gì LÀ câu trả lời, không phải sự im lặng. Bản đầu của bộ dò có
    # `pattern` trong danh sách và nó báo động giả ngay ở ca kiểm đầu tiên.
    ("glob không khớp", {"pattern": "**/*0"}, {"count": 0, "items": []}),
    ("grep không thấy", {"query": "abc"}, {"so_ket_qua": 0}),
    # `0` rất thường là tin TỐT.
    ("0 lỗi biên dịch", {"tep": ["main.c"]}, {"so_loi": 0, "so_byte": 1234}),
    ("lấy đủ 3 tệp", {"tep": ["a", "b", "c"]}, {"so_dat": 3, "so_hong": 0}),
    ("đọc 4 địa chỉ ra 4", {"dia_chi": [1, 2, 3, 4]}, {"o_nho": {"0x1": ["0"]}}),
    # Lời gọi không liệt kê đích danh gì thì nó vốn không hứa hẹn số lượng.
    ("không xin gì cụ thể", {}, {"so_dat": 0}),
    ("kết quả không phải dict", {"tep": ["a"]}, "chuỗi"),
])
def test_IM_LANG_o_nhung_cho_so_0_la_cau_tra_loi_dung(ten, args, data):
    assert khong_noi_gi(args, data)[0] is False, ten


def test_bool_KHONG_duoc_tinh_la_so_lon_hon_0():
    """Trong Python `bool` là con của `int`, nên `dat: True` sẽ được tính là "một số > 0" và
    dập tắt cảnh báo — đúng ở ca `soi_chip` mà bộ dò này sinh ra để bắt."""
    assert khong_noi_gi({"dia_chi": [1, 2]}, {"o_nho": {}, "dat": True})[0] is True


def test_so_HONG_khong_duoc_dap_tat_canh_bao():
    """`so_hong: 26` là số thứ HỎNG — nó xác nhận chứ không bác bỏ việc "không có gì chuyển
    động". Bản đầu xét mọi số trong kết quả, nên chính con số hỏng lại dập tắt cảnh báo."""
    assert khong_noi_gi({"tep": ["a"] * 26}, {"so_dat": 0, "so_hong": 26})[0] is True


def _agent_voi_cong_cu_rong(make_agent, script):
    """Một tác tử có thêm một công cụ luôn trả `ok` kèm kết quả RỖNG.

    Dựng công cụ giả thay vì mượn một công cụ thật: ca kiểm này đo **đường dẫn trong lõi**,
    nên nó không được phụ thuộc vào việc máy có `openocd` hay có mạng hay không.
    """
    agent = make_agent(script)

    @agent.registry.tool("thu.lay_tep", "Tệp & lệnh", "công cụ giả cho ca kiểm",
                         {"type": "object",
                          "properties": {"tep": {"type": "array",
                                                 "items": {"type": "string"}}},
                          "required": ["tep"]},
                         risk="R1")
    def _lay(ctx, tep):
        return {"so_dat": 0, "so_hong": len(tep)}

    return agent


def test_LOI_that_su_nhac_va_chi_nhac_MOT_LAN_moi_cong_cu(make_agent):
    """Hàm phân loại đúng chưa đủ — phải chứng minh LÕI thật sự chèn lời nhắc.

    Và chỉ nhắc một lần: nhắc lại mỗi lần gọi sẽ thành tiếng ồn, mà tiếng ồn thì bị bỏ qua,
    kể cả lần nó đáng đọc.
    """
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    agent = _agent_voi_cong_cu_rong(make_agent, [
        Response(tool_calls=[ToolCall("c1", "thu.lay_tep", {"tep": ["a", "b", "c"]})]),
        Response(tool_calls=[ToolCall("c2", "thu.lay_tep", {"tep": ["d", "e"]})]),
        Response(text="xong")])
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "lấy giúp mấy tệp",
                                   "origin": {"surface": "console"}}), lambda c: None)
    nhac = [m for m in agent.messages
            if m.get("_he_thong") and "vừa trả về **thành công**" in str(m.get("text", ""))]
    assert len(nhac) == 1, [str(m)[:90] for m in nhac]
    assert "thu.lay_tep" in nhac[0]["text"] and "xin 3 thứ" in nhac[0]["text"]


def test_nhac_nho_noi_viec_can_lam_khong_mang():
    from eide.ket_qua import nhac_nho

    t = nhac_nho("code.vendor_fetch", "xin 26 thứ mà rỗng")
    assert "vì sao rỗng là đúng ở đây" in t and "gọi lại cách khác" in t
    assert "mười bảy lượt" in t          # nói ra cái giá đã trả, để lời nhắc có trọng lượng


# ===================================================== verifier cho tác tử CHÍNH
def _hook_tu_kiem():
    """Lấy ĐÚNG hook cần kiểm ra khỏi bus, không chạy cả bus.

    Chạy cả bus thì ca kiểm này phải dựng một `ctx` giả đủ dùng cho **mọi** hook khác, và
    mỗi hook ai đó thêm sau sẽ làm nó đỏ vì một lý do không liên quan gì tới thứ nó đo.
    """
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    bus = register_standard_hooks(HookBus())
    fn = next(f for f in bus._stop if f.__name__ == "tu_kiem_khi_tuyen_dat")

    class _Mot:
        @staticmethod
        def stop(ctx):
            return fn(ctx)

    return _Mot()


class _Ctx:
    def __init__(self, noi, cong_cu=(), da_ghi=True):
        self.loi_da_noi = list(noi)
        self.cong_cu_da_goi = list(cong_cu)
        self.da_ghi_gi_do = da_ghi
        self.da_tu_kiem = False
        self.store = None


def test_tuyen_dat_sau_khi_GHI_thi_bi_bat_kiem_chung():
    """Lời tuyên "xong" của tác tử CHÍNH — thứ người dùng thật sự đọc — trước nay chưa bao
    giờ bị ai kiểm."""
    r = _hook_tu_kiem().stop(_Ctx(["Tôi đã sửa xong, firmware chạy được rồi."]))
    assert r.another_round is True
    assert "verifier" in r.injection and "N6" in r.injection
    assert "bản nháy đèn cũ" in r.injection      # cái giá đã trả, nói ra để có trọng lượng


def test_luot_THUAN_DOC_thi_KHONG_bat_kiem_chung():
    """Một câu "xong rồi" sau một lượt thuần đọc thường là trả lời một câu hỏi, không phải
    tuyên bố một việc đã làm. Bắt nó kiểm chứng là dựng thủ tục quanh một cuộc trò chuyện."""
    r = _hook_tu_kiem().stop(_Ctx(["Đã xong, I2C chạy ở 100 kHz."], da_ghi=False))
    assert r.another_round is False


def test_da_goi_verifier_roi_thi_thoi():
    r = _hook_tu_kiem().stop(_Ctx(["đã xong"], cong_cu=["fs.write", "task.run"]))
    assert r.another_round is False
    assert "tu_kiem_da_chay" in r.fired


def test_khong_tuyen_dat_thi_khong_bat():
    r = _hook_tu_kiem().stop(_Ctx(["Tôi đang đo tiếp, chưa kết luận được gì."]))
    assert r.another_round is False


def test_chi_bat_MOT_LAN_moi_luot():
    """Vòng thứ hai là vòng tác tử đang TRẢ LỜI chính lời nhắc này; bắt lại sẽ thành vòng lặp."""
    bus, ctx = _hook_tu_kiem(), _Ctx(["đã xong"])
    assert bus.stop(ctx).another_round is True
    assert ctx.da_tu_kiem is True
    assert bus.stop(ctx).another_round is False
