# -*- coding: utf-8 -*-
"""Plan mode (MDD-40 §B5) — `plan.enter` khoá công cụ ghi, `plan.exit` qua cổng G-SCOPE.

Điều bộ này canh, một câu: **người dùng phải thấy CÁCH LÀM trước khi tác tử tiêu lời gọi.**

Đo được trên phiên bo STM32F469 (402 lượt, 1078 lời gọi) — đây là những con số mà chặng này
sinh ra để chặn:

* 580 lời gọi (54 %) là `fs.read`/`fs.grep`/`fs.glob` — tác tử dò đường bằng cách đọc, và
  người dùng chỉ thấy kết quả sau khi số lời gọi ấy đã tiêu xong.
* Có lượt nó đốt trọn hạn mức 40 lời gọi rồi dừng giữa việc.
* Nó vá một đầu rồi làm hỏng đầu kia, vì không có bước nào bắt liệt kê "chỗ này còn chạm
  tới đâu".
"""

from __future__ import annotations

import pytest

from eide import ke_hoach as KH


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


def _buoc(n: int, cong_cu: str = "fs.read") -> list[dict]:
    return [{"viec": f"việc {i}", "cong_cu": cong_cu, "hien_vat": f"hiện vật {i}"}
            for i in range(1, n + 1)]


# ============================================================ kiểm kế hoạch bằng mã
def test_ke_hoach_neu_cong_cu_KHONG_TON_TAI_thi_bi_chan(make_agent):
    """Một kế hoạch nêu công cụ không có thật vẫn đọc rất xuôi tai, và người dùng vẫn duyệt
    được — rồi tới lúc chạy mới hỏng. Khi đó thứ đã duyệt không còn là thứ đang chạy."""
    agent = make_agent([])
    r = agent.registry.run("plan.enter", {"viec": "sửa màn hình"}, _ctx(agent))
    assert r.ok
    b = _buoc(2) + [{"viec": "x", "cong_cu": "khong.co.cong.cu.nay", "hien_vat": "y"}]
    r = agent.registry.run("plan.exit", {"buoc": b}, _ctx(agent))
    assert not r.ok and r.error.code == "E6003"
    assert "khong.co.cong.cu.nay" in r.error.message_vi


def test_buoc_KHONG_de_lai_hien_vat_thi_bi_chan(make_agent):
    """Bước không để lại gì thì sau này không ai kiểm được nó đã làm hay chưa."""
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    b = [{"viec": "đọc tài liệu", "cong_cu": "fs.read", "hien_vat": ""},
         {"viec": "sửa", "cong_cu": "fs.edit", "hien_vat": "main.c"}]
    r = agent.registry.run("plan.exit", {"buoc": b}, _ctx(agent))
    assert not r.ok and "hien_vat" in r.error.message_vi


@pytest.mark.parametrize("n,dat", [(0, False), (1, False), (2, True), (20, True), (21, False)])
def test_so_buoc_phai_nam_trong_khoang_doc_duoc(make_agent, n, dat):
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    r = agent.registry.run("plan.exit", {"buoc": _buoc(n)}, _ctx(agent))
    assert r.ok is dat, getattr(r.error, "message_vi", "")


# ============================================================ "việc lớn" tính bằng MÃ
def test_viec_lon_tinh_bang_MA_khong_hoi_mo_hinh(make_agent):
    """Để tác tử tự khai việc của mình có lớn không thì nó sẽ khai "nhỏ" đúng vào lúc nó
    đang định làm việc lớn — không phải vì gian, mà vì lúc ấy nó đang tập trung vào việc chứ
    không vào việc phân loại việc."""
    agent = make_agent([])
    # Ít bước, toàn công cụ đọc → nhỏ.
    kh = KH.KeHoach(muc_tieu="x", buoc=[KH.Buoc(viec="a", cong_cu="fs.read", hien_vat="h"),
                                        KH.Buoc(viec="b", cong_cu="fs.grep", hien_vat="h")])
    lon, _ = KH.la_viec_lon(kh, agent.registry.get)
    assert lon is False
    # Chỉ cần MỘT bước chạm cổng là lớn, dù kế hoạch rất ngắn.
    kh.buoc.append(KH.Buoc(viec="nạp", cong_cu="target.flash", hien_vat="mach.bin"))
    lon, vi_sao = KH.la_viec_lon(kh, agent.registry.get)
    assert lon is True and "target.flash" in vi_sao and "G-FLASH" in vi_sao


def test_nhieu_buoc_la_lon_du_toan_cong_cu_doc(make_agent):
    agent = make_agent([])
    kh = KH.KeHoach(muc_tieu="x",
                    buoc=[KH.Buoc(viec=str(i), cong_cu="fs.read", hien_vat="h")
                          for i in range(KH.BUOC_LA_LON)])
    lon, vi_sao = KH.la_viec_lon(kh, agent.registry.get)
    assert lon is True and str(KH.BUOC_LA_LON) in vi_sao


def test_viec_nho_thi_duyet_luon_khong_can_the(make_agent):
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "việc nhỏ"}, _ctx(agent))
    r = agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    assert r.ok and r.data["plan_big"] is False
    assert r.data["trang_thai"] == "da_duyet"


# ============================================================ khoá công cụ ghi
def test_dang_soan_ke_hoach_thi_cong_cu_GHI_bi_khoa(make_agent):
    """Lấy từ HỢP ĐỒNG của công cụ (`writes_artefact`, `risk`), không từ một danh sách tên:
    một công cụ mới thêm vào mà có `writes_artefact` thì tự động bị khoá."""
    agent = make_agent([])
    r = agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    assert r.ok

    def _khoa(ten: str) -> bool:
        return KH.cong_cu_bi_khoa(agent.registry.get(ten))

    assert _khoa("target.flash") is True          # R4
    assert _khoa("fact.from_doc") is True or _khoa("passport.pin") is True
    assert _khoa("fs.read") is False              # đọc — vẫn dùng được
    assert _khoa("fs.grep") is False
    # Chính bộ công cụ của plan mode và memory.note KHÔNG bị khoá.
    for t in ("plan.exit", "plan.cancel", "memory.note"):
        assert _khoa(t) is False, t


def test_khoa_memory_note_la_cam_ghi_lai_dung_thu_vua_hoc(make_agent):
    """Khoá `memory.note` trong lúc soạn kế hoạch nghĩa là cấm tác tử ghi lại đúng thứ nó
    vừa học được để soạn kế hoạch ấy. Nó nằm trong danh sách miễn, có chủ ý."""
    assert "memory.note" in KH.KHONG_KHOA


def test_vao_ke_hoach_hai_lan_thi_bi_chan(make_agent):
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    r = agent.registry.run("plan.enter", {"viec": "y"}, _ctx(agent))
    assert not r.ok and r.error.code == "E6001"
    assert "plan.cancel" in (r.error.alternatives or [])


def test_plan_exit_khi_chua_vao_ke_hoach(make_agent):
    agent = make_agent([])
    r = agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    assert not r.ok and r.error.code == "E6002"


def test_plan_cancel_mo_lai_cong_cu_ghi(make_agent):
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    r = agent.registry.run("plan.cancel", {"vi_sao": "việc nhỏ hơn tưởng"}, _ctx(agent))
    assert r.ok and r.data["trang_thai_truoc"] == "dang_soan"
    from eide.ke_hoach import MA_KE_HOACH, KeHoach

    kh = KeHoach.from_dict(agent.store.get(MA_KE_HOACH)["canonical"])
    assert kh.trang_thai == "huy"


# ============================================================ đánh dấu bước
def test_danh_dau_buoc_xong_PHAI_neu_hien_vat(make_agent):
    """Một bước "xong" mà không để lại gì thì dấu tích ấy chỉ nói rằng tác tử TIN là nó
    xong — đúng thứ N6 cấm.

    Từ 30/09/2026 phép kiểm chặt hơn: `hien_vat` phải TRỎ TỚI thứ mở ra xem được. Ca này vốn
    dùng `docs/a.md` — một đường dẫn không tồn tại — và nó đi lọt; chính chỗ ấy là lỗ hổng.
    """
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    r = agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "   "}, _ctx(agent))
    assert not r.ok and r.error.code == "E6004"
    # Đường dẫn KHÔNG có thật: vẫn phải đỏ.
    r = agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "docs/khong-co.md"},
                           _ctx(agent))
    assert not r.ok and r.error.code == "E6004"
    # Tệp có thật (fixture `du_an` dựng sẵn `docs/ghi-chu.md`): xanh.
    r = agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "docs/ghi-chu.md"},
                           _ctx(agent))
    assert r.ok and r.data["xong"] == 1


def test_danh_dau_buoc_ngoai_pham_vi(make_agent):
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    r = agent.registry.run("plan.step_done", {"so": 9, "hien_vat": "y"}, _ctx(agent))
    assert not r.ok and "không có bước 9" in r.error.message_vi


# ============================================================ Stop hook đối chiếu
def test_doi_chieu_chi_ra_ca_hai_phia_va_KHONG_goi_lech_la_loi():
    """Đi thêm việc ngoài kế hoạch thường là dấu hiệu kế hoạch THIẾU, không phải tác tử sai.
    Một hook phạt sẽ dạy tác tử viết kế hoạch thật rộng cho an toàn — tức là phá đúng thứ mà
    plan mode sinh ra để có."""
    kh = KH.KeHoach(muc_tieu="x", trang_thai="da_duyet", buoc=[
        KH.Buoc(viec="a", cong_cu="fs.read", hien_vat="docs/ghi-chu.md", xong=True),
        KH.Buoc(viec="b", cong_cu="build.compile", hien_vat="main.c")])
    d = KH.doi_chieu(kh, ["fs.read", "target.flash", "fs.grep", "fs.read"])
    assert d["lech"] is True
    assert d["ngoai_ke_hoach"] == ["target.flash", "fs.grep"]
    assert d["chua_lam"] == ["build.compile"]
    assert (d["xong"], d["tong"]) == (1, 2)

    cau = __import__("eide.tools.ke_hoach", fromlist=["x"]).bao_cao_doi_chieu(
        kh, ["fs.read", "target.flash"])
    assert "KHÔNG phải lỗi" in cau


def test_doi_chieu_dung_ke_hoach_thi_noi_gon():
    from eide.tools.ke_hoach import bao_cao_doi_chieu

    kh = KH.KeHoach(muc_tieu="x", trang_thai="da_duyet", buoc=[
        KH.Buoc(viec="a", cong_cu="fs.read", hien_vat="docs/ghi-chu.md", xong=True),
        KH.Buoc(viec="b", cong_cu="fs.grep", hien_vat="main.c", xong=True)])
    assert "Đi đúng kế hoạch: 2/2" in bao_cao_doi_chieu(kh, ["fs.read", "fs.grep"])


def test_plan_bi_khoa_khong_tinh_cong_cu_cua_chinh_plan_mode():
    """`plan.step_done` gọi trong lúc chạy kế hoạch không được tính là "ngoài kế hoạch"."""
    kh = KH.KeHoach(muc_tieu="x", trang_thai="da_duyet",
                    buoc=[KH.Buoc(viec="a", cong_cu="fs.read", hien_vat="h", xong=True)])
    d = KH.doi_chieu(kh, ["fs.read", "plan.step_done"])
    assert d["ngoai_ke_hoach"] == []


# ============================================================ khoá thật sự chặn trong LÕI
def test_LOI_chan_cong_cu_ghi_khi_dang_soan_ke_hoach(chay):
    """Phân loại đúng ở `cong_cu_bi_khoa` chưa đủ — phải chứng minh lõi THẬT SỰ chặn.

    Một phép kiểm chỉ gọi hàm phân loại sẽ xanh kể cả khi không ai nối nó vào đường đi của
    lời gọi công cụ, và khi đó khoá là một cái khoá treo trên cửa không có bản lề.
    """
    from eide.llm import Response, ToolCall

    agent, _ = chay(
        {"kind": "say", "text": "sửa giúp tôi cả hệ thống hiển thị"},
        script=[Response(tool_calls=[ToolCall("c1", "plan.enter", {"viec": "sửa hiển thị"})]),
                Response(tool_calls=[ToolCall("c2", "fs.write",
                                              {"path": "a.c", "content": "int x;"})]),
                Response(text="Tôi soạn kế hoạch trước đã.")])
    kq = [m for m in agent.messages if m.get("role") == "tool"]
    assert kq[0]["result"].get("ok") is not False              # plan.enter chạy được
    assert kq[1]["result"]["code"] == "E6005"                  # fs.write bị khoá
    assert "chế độ kế hoạch" in kq[1]["result"]["hint_for_agent"]
    # Và tệp KHÔNG được tạo — chặn thật, không phải chỉ báo lỗi rồi vẫn ghi.
    assert not (agent.config.paths.project_root / "a.c").exists()


def test_LOI_van_cho_doc_khi_dang_soan_ke_hoach(chay):
    """Khoá ghi mà khoá luôn đọc thì tác tử không soạn nổi kế hoạch — nó cần đo để soạn."""
    from eide.llm import Response, ToolCall

    agent, _ = chay(
        {"kind": "say", "text": "sửa giúp tôi"},
        script=[Response(tool_calls=[ToolCall("c1", "plan.enter", {"viec": "x"})]),
                Response(tool_calls=[ToolCall("c2", "fs.read", {"path": "main.c"})]),
                Response(text="xong")])
    kq = [m for m in agent.messages if m.get("role") == "tool"]
    assert kq[1]["result"].get("code") is None


def test_ke_hoach_DA_DUYET_thi_mo_lai_cong_cu_ghi(chay):
    """Kế hoạch nhỏ được duyệt luôn ⇒ `da_duyet` ⇒ hết khoá."""
    from eide.llm import Response, ToolCall

    b = [{"viec": "đọc", "cong_cu": "fs.read", "hien_vat": "nội dung main.c"},
         {"viec": "ghi", "cong_cu": "fs.write", "hien_vat": "a.c"}]
    agent, _ = chay(
        {"kind": "say", "text": "làm giúp tôi"},
        script=[Response(tool_calls=[ToolCall("c1", "plan.enter", {"viec": "x"})]),
                Response(tool_calls=[ToolCall("c2", "plan.exit", {"buoc": b})]),
                Response(tool_calls=[ToolCall("c3", "fs.write",
                                              {"path": "a.c", "content": "int x;",
                                               "explain": {"summary": "tạo a.c", "why": "bước 2 của kế hoạch", "sources": [], "diff_prev": "tệp mới", "next": "biên dịch", "confidence": "CAU_HINH"}})]),
                Response(text="xong")])
    kq = [m for m in agent.messages if m.get("role") == "tool"]
    assert kq[1]["result"]["data"]["plan_big"] is False
    assert kq[2]["result"].get("code") is None
    assert (agent.config.paths.project_root / "a.c").exists()


def test_ke_hoach_da_duyet_hien_o_pending_moi_luot(make_agent):
    """Kế hoạch đã duyệt phải vào `<pending>`; kế hoạch đang SOẠN thì không.

    Nhắc lại bản nháp của chính mình mỗi lượt là cách nhanh nhất để tác tử chốt vào ý đầu
    tiên nó nghĩ ra, đúng lúc nó đang cần nghĩ rộng.
    """
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    assert agent._plan_cho_ngu_canh() is None, "đang soạn thì KHÔNG vào ngữ cảnh"
    agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    p = agent._plan_cho_ngu_canh()
    assert p is not None and len(p["steps"]) == 2

    from eide.context.assemble import build_pending_block

    ra = build_pending_block(cards=[], stopped_run=None, assumptions=[], plan=p,
                             budget_tokens=300)
    assert "Kế hoạch đã duyệt: 0/2 bước xong" in ra


# ============================================================ kế hoạch CỦA VIỆC NÀO
def test_pending_NOI_RO_ke_hoach_ay_cho_viec_gi(make_agent):
    """Đo trên phiên FreeRTOS: `<pending>` in "Kế hoạch đã duyệt: 7/8 bước xong" — một con số
    không nội dung. Người dùng giao một việc MỚI (màn hình có nút, cảm ứng), tác tử thấy dòng
    ấy, tưởng mình đang chạy dưới một kế hoạch đã duyệt cho việc mới, và **không lập kế hoạch
    nào cả**.

    Cùng họ với "Lượt chạy dở: run-256": một mã số không nội dung thì người đọc tự điền nội
    dung vào, và thường điền sai.
    """
    from eide.context.assemble import build_pending_block

    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "tích hợp FreeRTOS và nháy LED"}, _ctx(agent))
    agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    ra = build_pending_block(cards=[], stopped_run=None, assumptions=[],
                             plan=agent._plan_cho_ngu_canh(), budget_tokens=300)
    assert "CHO VIỆC: “tích hợp FreeRTOS và nháy LED”" in ra
    assert "soạn kế hoạch mới" in ra


def test_xong_HET_buoc_thi_ke_hoach_DONG_LAI(make_agent):
    """Để nó ở `da_duyet` mãi thì nó chiếm chỗ "kế hoạch hiện tại" và làm tác tử tưởng việc
    mới cũng nằm trong nó."""
    from eide.ke_hoach import MA_KE_HOACH, KeHoach

    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "x"}, _ctx(agent))
    agent.registry.run("plan.exit", {"buoc": _buoc(2)}, _ctx(agent))
    agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "docs/ghi-chu.md"},
                       _ctx(agent))
    assert agent._plan_cho_ngu_canh() is not None, "chưa xong hết thì vẫn là kế hoạch hiện tại"
    agent.registry.run("plan.step_done", {"so": 2, "hien_vat": "main.c"}, _ctx(agent))
    kh = KeHoach.from_dict(agent.store.get(MA_KE_HOACH)["canonical"])
    assert kh.trang_thai == "hoan_thanh"
    assert agent._plan_cho_ngu_canh() is None, "xong hết rồi thì thôi chiếm chỗ"


def test_viec_moi_duoc_phep_co_ke_hoach_moi_du_cai_cu_chua_di_het(make_agent):
    """Người dùng đổi ý là chuyện bình thường, và bắt tác tử chạy nốt một kế hoạch đã lỗi
    thời là cách chắc nhất để nó làm sai việc."""
    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "việc cũ"}, _ctx(agent))
    agent.registry.run("plan.exit", {"buoc": _buoc(3)}, _ctx(agent))
    r = agent.registry.run("plan.enter", {"viec": "việc mới hẳn"}, _ctx(agent))
    assert r.ok and r.data["muc_tieu"] == "việc mới hẳn"


def test_pending_LIET_KE_cac_buoc_chu_khong_chi_dem(make_agent):
    """Không có danh sách bước, tác tử không đọc được kế hoạch của CHÍNH NÓ.

    Đo trên phiên FreeRTOS: nó tiêu 10 lời gọi đọc (5 `ledger.query`, 3 `fs.grep`, 1
    `tool.search`, 1 `fs.glob`) để dựng lại bảy bước mà vẫn chưa đủ, rồi phải tự viết một
    công cụ `plan.get` chỉ để nhìn thấy thứ lẽ ra đã ở trước mặt.
    """
    from eide.context.assemble import build_pending_block

    agent = make_agent([])
    agent.registry.run("plan.enter", {"viec": "làm màn hình có nút"}, _ctx(agent))
    # Hai công cụ KHÔNG chạm cổng, để kế hoạch là "việc nhỏ" và được duyệt luôn — ca này đo
    # cách hiển thị, không đo cổng.
    b = [{"viec": "lấy HAL của ST", "cong_cu": "fs.read", "hien_vat": "vendor/"},
         {"viec": "viết giao diện hai màn", "cong_cu": "fs.grep", "hien_vat": "ui.c"}]
    agent.registry.run("plan.exit", {"buoc": b}, _ctx(agent))
    # Hiện vật phải TRỎ TỚI thứ mở ra xem được (từ 30/09/2026) — `docs/` có thật trong
    # fixture, còn "vendor/ 12 tệp" là một câu kể lại.
    agent.registry.run("plan.step_done", {"so": 1, "hien_vat": "docs"}, _ctx(agent))

    ra = build_pending_block(cards=[], stopped_run=None, assumptions=[],
                             plan=agent._plan_cho_ngu_canh(), budget_tokens=400)
    assert "[x] 1. lấy HAL của ST · fs.read" in ra
    assert "[ ] 2. viết giao diện hai màn · fs.grep" in ra
