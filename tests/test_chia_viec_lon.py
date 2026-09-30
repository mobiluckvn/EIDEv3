# -*- coding: utf-8 -*-
"""Chia một việc lớn ra làm nhiều lần, ghi kết quả từng lần, rồi HỢP NHẤT.

Chế độ kế hoạch vốn đã chia được việc và giữ được qua nhiều lượt. Bộ này đo ba chỗ nó **chưa**
làm được, cả ba đều đo ra ngày 30/09/2026:

1. `plan.step_done` nhận một câu kể lại làm "hiện vật" — bước thành xong mà không có gì mở ra
   xem được. Chỗ đậu giả rẻ nhất còn lại trong chế độ kế hoạch.
2. `plan.enter` lần thứ hai **đè mất** kế hoạch đang chạy: mục tiêu đổi, số bước về 0, không
   một lời báo. Phần đã làm biến mất khỏi hồ sơ.
3. Không có bước hợp nhất: xong hết thì kế hoạch chỉ đổi trạng thái, các phần nằm rời.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eide.ke_hoach import MA_KE_HOACH, KeHoach
from eide.tools.ke_hoach import _ha_tieu_de, _tach_tieu_de

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "đầu", "next": "n",
      "confidence": "NGUOI"}


@pytest.fixture
def bo(du_an):
    """(agent, registry, hàm dựng ctx mới) — mỗi bước một LƯỢT khác nhau, như đời thật."""
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")

    def ctx_moi():
        return TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger,
                           eide_md=ag.eide_md, ids=ag.ids, registry=ag.registry,
                           emit=lambda c: None, history=ag.history, agent=ag,
                           run_id=ag.ids.next("run"), project_name="du-an-thu")
    return ag, build_registry(), ctx_moi


def _lap_ke_hoach(ag, r, ctx, ten: list[str]) -> None:
    r.get("plan.enter").fn(ctx, viec="Viết tài liệu thiết kế chip")
    r.get("plan.exit").fn(
        ctx,
        buoc=[{"viec": t, "cong_cu": "fs.write", "hien_vat": f"tai-lieu/{i}.md",
               "chi_phi": "3 lời gọi"} for i, t in enumerate(ten, 1)],
        gia_dinh=[], ngoai_pham_vi=[])
    a = ag.store.get(MA_KE_HOACH)
    kh = KeHoach.from_dict(a["canonical"])
    kh.trang_thai = "da_duyet"
    ag.store.apply(artefact_id=MA_KE_HOACH, type="plan", op="update", author="t",
                   canonical=kh.to_dict(), explain=EX)


# ======================================================== 1. hiện vật phải MỞ RA XEM ĐƯỢC
def test_khong_danh_dau_xong_bang_mot_cau_ke_lai(bo):
    """`plan.step_done(1, "tôi đã viết xong chương 1 rồi nhé")` từng được NHẬN."""
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["Tổng quan", "Khối chức năng"])

    ra = r.get("plan.step_done").fn(ctx, so=1, hien_vat="tôi đã viết xong chương 1 rồi nhé")
    assert not ra.ok and ra.error.code == "E6004"
    assert "mở ra xem được" in ra.error.hint_for_agent.lower()
    # Lỗi phải nhắc lại thứ kế hoạch đã HỨA, để tác tử biết đi làm gì.
    assert "tai-lieu/1.md" in ra.error.hint_for_agent

    kh = KeHoach.from_dict(ag.store.get(MA_KE_HOACH)["canonical"])
    assert not kh.buoc[0].xong, "bước bị đánh dấu xong dù hiện vật không có thật"


def test_nhan_ba_loai_hien_vat_co_that(bo):
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["A", "B"])
    r.get("fs.write").fn(ctx, path="tai-lieu/1.md", content="# A\n\nnội dung", explain=EX)

    # (a) đường dẫn tệp có thật
    assert r.get("plan.step_done").fn(ctx, so=1, hien_vat="tai-lieu/1.md")["xong"] == 1
    # (b) mã hiện vật có trong kho — chính tệp vừa ghi đã thành hiện vật
    assert r.get("plan.step_done").fn(ctx, so=2, hien_vat="tai-lieu/1.md")["xong"] == 2


# ======================================================== 2. không đè mất kế hoạch đang chạy
def test_ke_hoach_moi_khong_lam_MAT_ke_hoach_dang_chay(bo):
    """Đo được: đang giữa kế hoạch 3 bước (xong 1), `plan.enter` lần nữa → mục tiêu đổi, số
    bước về 0, phần đã làm biến mất khỏi hồ sơ.

    Cho phép kế hoạch mới là đúng (người dùng đổi ý là chuyện thường). Làm mất bản cũ thì
    không — hai chuyện ấy khác nhau.
    """
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["A", "B", "C"])
    r.get("fs.write").fn(ctx, path="tai-lieu/1.md", content="# A\n\nx", explain=EX)
    r.get("plan.step_done").fn(ctx, so=1, hien_vat="tai-lieu/1.md")

    ra = r.get("plan.enter").fn(ctx_moi(), viec="Một việc lớn khác hẳn")
    ma_cu = ra["ke_hoach_cu_luu_o"]
    assert ma_cu, "kế hoạch cũ không được cất đi đâu cả"
    assert "1/3" in ra["note_vi"], ra["note_vi"]

    cu = KeHoach.from_dict(ag.store.get(ma_cu)["canonical"])
    assert cu.muc_tieu == "Viết tài liệu thiết kế chip"
    assert len(cu.buoc) == 3 and cu.buoc[0].xong


# ======================================================== 3. hợp nhất
def test_gop_theo_dung_thu_tu_buoc_va_sinh_muc_luc(bo, du_an):
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["Tổng quan", "Khối chức năng", "Bản đồ thanh ghi"])
    than = {1: "# Tổng quan\n\nChip đo nhiệt độ.\n\n## Yêu cầu\n\nI2C.",
            2: "# Khối chức năng\n\n- ADC 12 bit",
            3: "# Bản đồ thanh ghi\n\n| Địa chỉ | Tên |\n|---|---|\n| 0x00 | ID |"}
    for i in (1, 2, 3):
        c = ctx_moi()
        r.get("fs.write").fn(c, path=f"tai-lieu/{i}.md", content=than[i], explain=EX)
        r.get("plan.step_done").fn(c, so=i, hien_vat=f"tai-lieu/{i}.md")

    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/HOP-NHAT.md",
                                tieu_de="Thiết kế chip", explain=EX)
    assert ra["so_phan_da_gop"] == 3 and ra["khong_gop_duoc"] == []
    t = (du_an / "tai-lieu/HOP-NHAT.md").read_text("utf-8")
    assert t.startswith("# Thiết kế chip")
    assert "## Mục lục" in t
    # đúng THỨ TỰ BƯỚC, không phải thứ tự bảng chữ cái hay thứ tự tệp
    assert t.index("Tổng quan") < t.index("Khối chức năng") < t.index("Bản đồ thanh ghi")
    # mỗi phần ghi rõ nguồn — người đọc lần ngược về tệp gốc được
    assert "`tai-lieu/2.md`" in t
    assert ra["changeset"].startswith("cs-")


def test_gop_KHI_CON_BUOC_CHUA_XONG_thi_tu_choi(bo):
    """Gộp lúc mới làm một nửa ra một tài liệu THIẾU mà trông như đủ."""
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["A", "B"])
    r.get("fs.write").fn(ctx, path="tai-lieu/1.md", content="# A\n\nx", explain=EX)
    r.get("plan.step_done").fn(ctx, so=1, hien_vat="tai-lieu/1.md")

    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/x.md", explain=EX)
    assert not ra.ok and ra.error.code == "E6005"
    assert ra.error.details["chua_xong"] == [2]


def test_phan_khong_gop_duoc_phai_NOI_RA_trong_chinh_tai_lieu(bo, du_an):
    """Bước để lại một tệp nhị phân thì nó không vào được tài liệu — và người đọc BẢN HỢP
    NHẤT phải biết điều đó, chứ không phải người gọi công cụ."""
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["Chương chữ", "Ảnh sơ đồ"])
    r.get("fs.write").fn(ctx, path="tai-lieu/1.md", content="# Chương\n\nx", explain=EX)
    r.get("plan.step_done").fn(ctx, so=1, hien_vat="tai-lieu/1.md")
    (du_an / "so-do.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    r.get("plan.step_done").fn(ctx_moi(), so=2, hien_vat="so-do.png")

    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/y.md", explain=EX)
    assert ra["so_phan_da_gop"] == 1
    assert ra["khong_gop_duoc"][0]["buoc"] == "2"
    t = (du_an / "tai-lieu/y.md").read_text("utf-8")
    assert "Chưa gộp vào đây" in t, "phần thiếu bị giấu khỏi chính tài liệu"


def test_gop_ra_dinh_dang_khac_md_thi_tu_choi(bo):
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["A", "B"])
    for i in (1, 2):
        r.get("fs.write").fn(ctx, path=f"tai-lieu/{i}.md", content="# x\n\ny", explain=EX)
        r.get("plan.step_done").fn(ctx, so=i, hien_vat=f"tai-lieu/{i}.md")
    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/z.docx", explain=EX)
    assert not ra.ok and ra.error.code == "E6006"
    assert "doc.render" in ra.error.alternatives


# ======================================================== thứ bậc tiêu đề
def test_ha_cap_tieu_de_va_bo_tieu_de_trung():
    """Mỗi phần vốn là tài liệu đứng riêng nên mở đầu ở mức `#`. Ghép thẳng dưới một mục `##`
    thì mục con hiện to hơn mục cha — đo được ngay lần chạy thử đầu."""
    ten, than = _tach_tieu_de("# Tổng quan\n\nnội dung\n\n## Yêu cầu\n\nx", "mặc định")
    assert ten == "Tổng quan" and than.startswith("nội dung")
    assert _ha_tieu_de("## Yêu cầu", 2) == "#### Yêu cầu"
    # `# include` trong khối mã KHÔNG phải tiêu đề — hạ nó là sửa mã của người dùng.
    assert "#include" in _ha_tieu_de("```c\n#include <x.h>\n```", 2)
    # Không vượt quá mức 6.
    assert _ha_tieu_de("##### sâu", 3) == "###### sâu"


def test_nhieu_buoc_cung_MOT_tep_thi_khong_ghep_lai_nhieu_lan(bo, du_an):
    """Đo được 30/09/2026 qua giao diện thật: tác tử viết cả sáu phần dồn vào `y-tuong.md`,
    nên `plan.merge` ghép đúng tệp ấy **sáu lần** — `ok=True` mà nội dung nhân sáu. Tác tử
    phải tự `fs.write` đè lên để chữa.

    Một lời gọi `ok` cho ra thứ vô nghĩa thì tệ hơn một lỗi nói thẳng.
    """
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["Phần A", "Phần B", "Phần C"])
    r.get("fs.write").fn(ctx, path="tai-lieu/chung.md", content="# Chung\n\nmột nội dung",
                         explain=EX)
    for i in (1, 2, 3):
        r.get("plan.step_done").fn(ctx_moi(), so=i, hien_vat="tai-lieu/chung.md")

    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/gop.md", explain=EX)
    assert not ra.ok and ra.error.code == "E6008"
    assert "đã là bản hợp nhất" in ra.error.hint_for_agent
    assert not (du_an / "tai-lieu/gop.md").exists(), "từ chối mà vẫn để lại tệp thì tệ hơn"


def test_mot_so_buoc_trung_tep_thi_ghep_mot_lan_va_NOI_RA(bo, du_an):
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    _lap_ke_hoach(ag, r, ctx, ["A", "B", "C"])
    r.get("fs.write").fn(ctx, path="tai-lieu/1.md", content="# A\n\nx", explain=EX)
    r.get("fs.write").fn(ctx, path="tai-lieu/3.md", content="# C\n\nz", explain=EX)
    r.get("plan.step_done").fn(ctx_moi(), so=1, hien_vat="tai-lieu/1.md")
    r.get("plan.step_done").fn(ctx_moi(), so=2, hien_vat="tai-lieu/1.md")   # trùng bước 1
    r.get("plan.step_done").fn(ctx_moi(), so=3, hien_vat="tai-lieu/3.md")

    ra = r.get("plan.merge").fn(ctx_moi(), ra="tai-lieu/g.md", explain=EX)
    assert ra["so_phan_da_gop"] == 2
    assert ra["trung_tep"][0]["buoc"] == "2" and ra["trung_tep"][0]["cung_voi"] == "1"
    assert "dùng chung tệp" in ra["note_vi"]
    t = (du_an / "tai-lieu/g.md").read_text("utf-8")
    assert t.count("*Nguồn:") == 2, "nội dung bị ghép lặp"


def test_co_ke_hoach_thi_TAC_TU_NHIN_THAY_step_done_va_merge(bo):
    """Đo được 30/09/2026 qua giao diện thật: tác tử có kế hoạch ba bước ngay trong
    `<pending>`, được bảo *"làm tiếp"*, nó sửa tệp rồi dừng — **không gọi `plan.step_done`
    lần nào**. Kế hoạch đứng yên 0/3 và không lỗi nào được ném ra.

    Lý do: hai công cụ ấy là `core=False`, chỉ hiện sau một lần `tool.search`. Cùng hình dạng
    lỗi với hook kiểm chứng từng bảo tác tử gọi `task.run` mà không mở khoá — *bảo ai đó dùng
    một thứ họ không nhìn thấy thì không phải là bảo.*
    """
    ag, r, ctx_moi = bo
    kho = getattr(ag.registry, "_unlocked", None)
    assert kho is not None

    # Chưa có kế hoạch: hai công cụ ấy vẫn khoá (không tốn lược đồ ở mọi phiên).
    ag._mo_khoa_cong_cu_ke_hoach()
    assert "plan.step_done" not in kho

    _lap_ke_hoach(ag, r, ctx_moi(), ["A", "B"])
    ag._mo_khoa_cong_cu_ke_hoach()
    for t in ("plan.step_done", "plan.merge", "plan.cancel"):
        assert t in kho, f"{t} vẫn khoá dù đang giữa một kế hoạch đã duyệt"


def test_pending_NOI_TEN_cong_cu_phai_goi():
    """Danh sách bước cho tác tử biết PHẢI LÀM GÌ; nó vẫn cần biết ĐÁNH DẤU BẰNG CÁI GÌ."""
    from eide.context.assemble import build_pending_block

    ra = build_pending_block(
        cards=[], stopped_run=None, assumptions=[],
        plan={"muc_tieu": "viết tài liệu", "trang_thai": "da_duyet",
              "steps": [{"viec": "phần 1", "cong_cu": "fs.write", "xong": True},
                        {"viec": "phần 2", "cong_cu": "fs.write", "xong": False}]},
        budget_tokens=900)
    assert "plan.step_done" in ra
    # Chưa xong hết thì chưa giục gộp.
    assert "plan.merge" not in ra

    het = build_pending_block(
        cards=[], stopped_run=None, assumptions=[],
        plan={"muc_tieu": "x", "trang_thai": "da_duyet",
              "steps": [{"viec": "a", "cong_cu": "fs.write", "xong": True}]},
        budget_tokens=900)
    assert "plan.merge" in het


def test_plan_exit_CANH_BAO_khi_nhieu_buoc_cung_mot_hien_vat(bo):
    """Nói lúc lập kế hoạch, không đợi tới lúc gộp.

    Đo được 30/09/2026 qua giao diện thật, hai lượt liền: tác tử viết cả 6 rồi cả 8 phần vào
    một tệp, và chuyện ấy chỉ lộ ra ở `plan.merge` — tức sau khi đã làm xong hết. Phát hiện
    đúng nhưng muộn thì không cứu được lần chạy ấy.
    """
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    r.get("plan.enter").fn(ctx, viec="Viết tài liệu dài")
    ra = r.get("plan.exit").fn(ctx, buoc=[
        {"viec": "Phần A", "cong_cu": "fs.write", "hien_vat": "tai-lieu/all.md"},
        {"viec": "Phần B", "cong_cu": "fs.write", "hien_vat": "tai-lieu/all.md"},
        {"viec": "Phần C", "cong_cu": "fs.write", "hien_vat": "tai-lieu/c.md"}], gia_dinh=[],
        ngoai_pham_vi=[])
    assert ra["buoc_dung_chung_hien_vat"] == {"tai-lieu/all.md": [1, 2]}
    assert "plan.merge` sẽ KHÔNG có gì để ghép" in ra["note_vi"]
    # Không phải lỗi: kế hoạch vẫn được nhận.
    assert ra["so_buoc"] == 3


def test_khong_canh_bao_khi_moi_buoc_mot_tep(bo):
    """Cảnh báo kêu quá tay sẽ thành báo động giả, mà báo động giả dạy người ta bỏ qua."""
    ag, r, ctx_moi = bo
    ctx = ctx_moi()
    r.get("plan.enter").fn(ctx, viec="x")
    ra = r.get("plan.exit").fn(ctx, buoc=[
        {"viec": "A", "cong_cu": "fs.write", "hien_vat": "tai-lieu/1.md"},
        {"viec": "B", "cong_cu": "fs.write", "hien_vat": "tai-lieu/2.md"}], gia_dinh=[],
        ngoai_pham_vi=[])
    assert ra["buoc_dung_chung_hien_vat"] == {}
    assert "⚠︎" not in ra["note_vi"]
