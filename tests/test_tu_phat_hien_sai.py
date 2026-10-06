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
    fn = next(f for f in bus._stop if f.__name__ == "kiem_viec_chua_ai_kiem")

    class _Mot:
        @staticmethod
        def stop(ctx):
            return fn(ctx)

    return _Mot()


class _Ev:
    def __init__(self, kind, data):
        self.kind, self.data = kind, data


class _So:
    """Sổ cái giả — chỉ đủ để `co_viec_chua_kiem` đọc ngược."""

    def __init__(self, goi):
        self._ds = [_Ev("tool_use", {"tool": t, "args": a}) for t, a in goi]

    def read(self):
        return list(self._ds)


class _Ctx:
    def __init__(self, noi, cong_cu=(), da_ghi=True, chua_kiem=False, so=None):
        self.said_anything = bool(noi)
        self.loi_da_noi = list(noi)
        self.cong_cu_da_goi = list(cong_cu)
        self.da_ghi_gi_do = da_ghi
        self.da_tu_kiem = False
        self.store = None
        self.registry = None
        # `chua_kiem=True` ⇒ dựng một sổ cái có lời gọi GHI mà chưa có verifier sau nó.
        self.ledger = so if so is not None else (
            _So([("fs.write", {}), ("build.compile", {})]) if chua_kiem else _So([]))


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


def test_CACH_DIEN_DAT_khong_con_lach_duoc():
    """Bản đầu dò "lời tuyên đạt" bằng từ khoá, và nó không nổ lần nào trên phiên FreeRTOS:
    tác tử viết *"FreeRTOS Kernel chạy đa tác vụ thực tế trên phần cứng"* — một lời tuyên
    đạt rõ ràng, không chứa từ nào trong danh sách 14 từ khoá.

    Dò cách DIỄN ĐẠT là chỗ mọi danh sách từ khoá đều thua, và thua im lặng. Điều kiện giờ
    là **có việc chưa ai kiểm**, không phải câu chữ."""
    cau = "FreeRTOS Kernel chạy đa tác vụ thực tế trên phần cứng STM32F469I-DISCO"
    assert _hook_tu_kiem().stop(_Ctx([cau], da_ghi=False, chua_kiem=True)).another_round
    # Và ngược lại: không có việc nào chưa kiểm thì im, dù câu chữ nghe rất "đạt".
    assert _hook_tu_kiem().stop(
        _Ctx(["đã xong hoàn toàn"], da_ghi=False, chua_kiem=False)).another_round is False


def test_chi_bat_MOT_LAN_moi_luot():
    """Vòng thứ hai là vòng tác tử đang TRẢ LỜI chính lời nhắc này; bắt lại sẽ thành vòng lặp."""
    bus, ctx = _hook_tu_kiem(), _Ctx(["đã xong"])
    assert bus.stop(ctx).another_round is True
    assert ctx.da_tu_kiem is True
    assert bus.stop(ctx).another_round is False


def test_LUOT_BAO_CAO_sau_khi_viec_da_ghi_o_luot_TRUOC_van_phai_kiem():
    """Chỗ bản đầu hỏng, và nó hỏng im lặng.

    Đo trên phiên FreeRTOS: hook không nổ lần nào. Lời tuyên "xong" gần như luôn nằm ở một
    lượt **báo cáo** — lượt ấy chỉ đọc, không ghi gì — còn việc thì đã ghi ở các lượt trước.
    Điều kiện "lượt này có ghi" vì thế giết đúng cái ca nó sinh ra để bắt.
    """
    ctx = _Ctx(["FreeRTOS chạy đa tác vụ thành công trên phần cứng"],
               da_ghi=False, chua_kiem=True)
    r = _hook_tu_kiem().stop(ctx)
    assert r.another_round is True


def test_da_kiem_roi_thi_luot_bao_cao_KHONG_bi_bat_lai():
    """Cờ tắt khi verifier chạy — nếu không, mọi lượt báo cáo về sau đều bị bắt lại."""
    ctx = _Ctx(["đã xong"], da_ghi=False, chua_kiem=False)
    assert _hook_tu_kiem().stop(ctx).another_round is False


def test_LOI_bat_tat_co_khi_verifier_chay(make_agent):
    """Cờ `ghi_chua_kiem` phải BẬT khi ghi và TẮT khi verifier chạy — đo trong lõi."""
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    agent = make_agent([
        Response(tool_calls=[ToolCall("c1", "fs.write",
                                      {"path": "a.c", "content": "int x;",
                                       "explain": {"summary": "tạo a.c", "why": "thử",
                                                   "sources": [], "diff_prev": "mới",
                                                   "next": "—", "confidence": "CAU_HINH"}})]),
        Response(text="xong")])
    assert agent.ghi_chua_kiem is False
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "tạo giúp a.c",
                                   "origin": {"surface": "console"}}), lambda c: None)
    assert agent.ghi_chua_kiem is True, "ghi xong mà cờ không bật"


def test_verifier_da_chay_thi_viec_TRUOC_no_khong_tinh_la_chua_kiem():
    """Đọc ngược tới lần verifier gần nhất rồi DỪNG. Không dừng thì mọi lời gọi ghi từ đầu
    dự án đều tính là chưa kiểm, và hook sẽ nổ mãi mãi."""
    from eide.kiem_chung import co_viec_chua_kiem

    so = _So([("fs.write", {}),
              ("task.run", {"subagent": "verifier"}),
              ("fs.read", {})])
    chua, _ = co_viec_chua_kiem(so, None)
    assert chua is False

    so = _So([("task.run", {"subagent": "verifier"}),
              ("fs.write", {})])
    chua, vet = co_viec_chua_kiem(so, None)
    assert chua is True and "fs.write" in vet


def test_task_run_voi_subagent_KHAC_khong_tinh_la_da_kiem():
    """`task.run` còn chạy năm loại tác tử con khác — đọc `subagent` từ tham số, không từ
    tên công cụ."""
    from eide.kiem_chung import co_viec_chua_kiem

    so = _So([("fs.write", {}), ("task.run", {"subagent": "firmware"})])
    assert co_viec_chua_kiem(so, None)[0] is True


def test_so_cai_BEN_qua_khoi_dong_lai(tmp_path):
    """Chỗ bản trước hỏng: cờ nằm trong đối tượng `Agent`, mà app khởi động lại giữa các
    bước làm việc — nên việc ghi ở tiến trình TRƯỚC thành vô hình, và hook im suốt."""
    from eide.kiem_chung import co_viec_chua_kiem
    from eide.protocol.ledger import Ledger

    p = tmp_path / "ledger.jsonl"
    Ledger(p).append("tool_use", {"tool": "fs.write", "args": {}})
    # "Tiến trình mới": một đối tượng Ledger khác, đọc lại từ đĩa.
    assert co_viec_chua_kiem(Ledger(p), None)[0] is True


def test_verifier_NHIN_DUOC_ban_ung_y():
    """Đo trên phiên FreeRTOS: verifier được giao kiểm bản ưng ý vừa tạo, thử
    `store.get("snap-01")` và nhận `E5005` — snapshot nằm ở cây riêng, không trong kho hiện
    vật chung. Nó kết luận `khong_dat` **vì không có công cụ để nhìn**, không vì có gì sai.

    Một người kiểm chứng bị bịt mắt đúng chỗ cần nhìn thì mọi kết luận của họ đều nói về cái
    bịt mắt, không nói về thứ đang được kiểm.
    """
    from eide.subagent import SUBAGENT

    cc = SUBAGENT["verifier"].cong_cu
    assert "snapshot.list" in cc
    # Và vẫn CHỈ có công cụ đọc — thêm mắt, không thêm tay.
    assert not any(t.startswith(("fs.write", "fs.edit", "target.", "build.")) for t in cc)


def test_dang_giua_ke_hoach_thi_HOAN_kiem_chung(make_agent):
    """Đo trên phiên FreeRTOS: hook đòi kiểm chứng ở MỌI lượt có ghi, nên tác tử tiêu một
    lượt cho verifier sau mỗi bước — kế hoạch bảy bước thành mười bốn lượt.

    Plan mode đã có kỷ luật từng bước (`plan.step_done` đòi hiện vật). Kiểm chứng ĐỘC LẬP
    thuộc về lúc kết thúc, không phải mỗi chặng nghỉ giữa đường.
    """
    from eide.loop import TurnContext

    agent = make_agent([])
    c = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                    eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                    emit=lambda x: None, history=agent.history, run_id="run-1")
    agent.registry.run("plan.enter", {"viec": "việc lớn"}, c)
    agent.registry.run("plan.exit", {"buoc": [
        {"viec": "a", "cong_cu": "fs.read", "hien_vat": "h"},
        {"viec": "b", "cong_cu": "fs.write", "hien_vat": "h"}]}, c)

    ctx = _Ctx(["đã làm xong bước 1"], da_ghi=True)
    ctx.store = agent.store
    r = _hook_tu_kiem().stop(ctx)
    assert r.another_round is False
    assert "tu_kiem_hoan_lai_vi_dang_theo_ke_hoach" in r.fired

    # Xong hết bước → kế hoạch đóng → lần kết lượt sau phải kiểm.
    # `hien_vat` phải trỏ tới thứ mở ra xem được (từ 30/09/2026); fixture có sẵn hai tệp này.
    agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "main.c"}, c)
    agent.registry.run("plan.step_done", {"so": 2, "hien_vat": "docs/ghi-chu.md"}, c)
    ctx2 = _Ctx(["xong cả kế hoạch"], da_ghi=True)
    ctx2.store = agent.store
    assert _hook_tu_kiem().stop(ctx2).another_round is True


def test_nhac_rong_KHONG_chen_giua_goi_va_ket_qua(make_agent):
    """TC-M1-01-02 — lời nhắc "kết quả rỗng" phải đứng SAU kết quả, không chen vào giữa.

    `_one_tool` append lời nhắc `role=user` ngay khi thấy kết quả rỗng, tức là TRƯỚC khi
    append kết quả của chính lời gọi ấy. Lịch sử thành: lượt mô hình gọi `c1` → một lời
    nhắc của người → rồi mới kết quả `c1`. Lời nhắc đúng, chỗ đặt sai: nó cắt đôi cặp
    gọi ↔ trả mà `kiem_cap_goi_tra` canh.
    """
    from eide.llm import Response, ToolCall
    from eide.loop import kiem_cap_goi_tra
    from eide.protocol.humanact import HumanAct

    agent = _agent_voi_cong_cu_rong(make_agent, [
        Response(tool_calls=[ToolCall("c1", "thu.lay_tep", {"tep": ["a", "b", "c"]})]),
        Response(text="xong")])
    agent.turn(HumanAct.from_dict({"kind": "say", "text": "lấy giúp mấy tệp",
                                   "origin": {"surface": "console"}}), lambda c: None)

    vai = [m.get("role") for m in agent.messages]
    i_model = next(k for k, m in enumerate(agent.messages)
                   if m.get("role") == "model" and m.get("tool_calls"))
    sau = agent.messages[i_model + 1]
    assert sau.get("role") == "tool" and sau.get("tool_call_id") == "c1", (
        f"ngay sau lượt gọi phải là kết quả của c1, đang là {str(sau)[:120]}. Vai: {vai}")

    i_nhac = next(k for k, m in enumerate(agent.messages)
                  if "vừa trả về **thành công**" in str(m.get("text", "")))
    assert i_nhac > i_model + 1, "lời nhắc phải đứng sau kết quả, không chen vào giữa"
    assert kiem_cap_goi_tra(list(agent.messages)) == []
