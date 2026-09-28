# -*- coding: utf-8 -*-
"""Công cụ snapshot và nhánh — bước G5. EIDE-MDD-40 §E5.5, §E6.

Điều đáng nhớ nhất khi đọc nhóm này: **tác tử không tự đặt tên bản ưng ý** (§E6.2).
`snapshot.propose` chỉ đề xuất; lớp cấp quyền dựng thẻ G-SNAP; người đặt tên. Nếu tác
tử được phép đặt tên, danh sách bản ưng ý sẽ đầy những "sau-khi-sua-driver" — đúng kiểu
sáu tháng sau không ai dùng được.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from ..protocol import uicommand as uic
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA


def register(r: Registry) -> Registry:

    @r.tool("snapshot.list", "Lịch sử",
            "Liệt kê các bản ưng ý đã ghi, kèm khoảng cách (bao nhiêu changeset kể từ đó).",
            {"type": "object",
             "properties": {"gom_checkpoint": {"type": "boolean",
                                               "description": "Gồm cả checkpoint ngầm"}}},
            risk="R1", keywords=["snapshot", "bản ưng ý", "mốc", "danh sách"])
    def snapshot_list(ctx: Any, gom_checkpoint: bool = False):
        ds = ctx.history.danh_sach_snapshot(gom_checkpoint=gom_checkpoint)
        return {"so_ban": len(ds), "ban": ds,
                "co_release": ctx.history.snapshots.co_release(),
                "note_vi": "" if ds else
                "Chưa có bản ưng ý nào. Sau một mốc đáng nhớ (mô phỏng đạt, nạp thành "
                "công, trước một thao tác không đảo ngược), hãy ĐỀ XUẤT ghi một bản — "
                "nhưng để người dùng đặt tên."}

    @r.tool("snapshot.propose", "Lịch sử",
            "Đề xuất ghi một bản ưng ý sau một mốc đáng nhớ. Bạn KHÔNG tự đặt tên — "
            "công cụ này dựng thẻ để người dùng đặt tên và ghi chú, hoặc từ chối.",
            {"type": "object",
             "properties": {
                 "ly_do": {"type": "string",
                           "description": "Vì sao đây là mốc đáng ghi, một câu"},
                 "ten_goi_y": {"type": "string",
                               "description": "Gợi ý thôi — người dùng sửa được"},
                 "passed": {"type": "array", "items": {"type": "string"},
                            "description": "Mã REQ đã đạt tại mốc này, nếu biết"}},
             "required": ["ly_do"]},
            risk="R2", gate="G-SNAP",
            keywords=["đề xuất snapshot", "ghi bản ưng ý", "mốc"])
    def snapshot_propose(ctx: Any, ly_do: str, ten_goi_y: str = "",
                         passed: list[str] | None = None):
        # Tới được đây nghĩa là lớp cấp quyền đã cho qua (hoặc người đã duyệt thẻ).
        dem = ctx.store.counts()
        card_id = ctx.ids.next("card")
        card = {
            "type": "clarify", "card_id": card_id,
            "intro": f"{ly_do}\n\nĐây là lúc hợp lý để ghi một bản ưng ý. Bản này sẽ "
                     f"gồm: {dem.get('req', 0)} yêu cầu, "
                     f"{sum(ctx.store.fact_tier_counts().values())} Fact, "
                     f"{dem.get('code', 0)} tệp mã, "
                     f"{len(ctx.store.list('doc', limit=50))} tài liệu.",
            "questions": [
                {"key": "ten", "question": "Đặt tên cho bản này là gì?",
                 "why": "Tên là thứ dẫn anh quay về đúng chỗ khi không còn nhớ hôm nay "
                        "đã làm gì. Tôi không đặt hộ.",
                 "prefill": ten_goi_y, "required": True},
                {"key": "ghi_chu", "question": "Ghi chú thêm gì không?",
                 "why": "Ví dụ: đã chạy trên bo thật, mô phỏng đạt 5/5."},
            ],
            "assumption_if_skipped": "Không ghi bản ưng ý nào.",
            # Người trả lời thẻ này thì vòng lặp GHI LUÔN, không hỏi lại mô hình.
            "tra_loi_thanh": "snapshot",
        }
        ctx.emit(uic.console_post(
            f"{ly_do}\n\nAnh muốn ghi lại làm **bản ưng ý** không? "
            "Nếu có, anh đặt tên giúp — tôi không đặt hộ vì tên là thứ anh sẽ đọc lại "
            "sau này.", role="agent", card=card))
        ctx.pending_cards.append(card)
        ctx.awaiting_human = True
        return {"da_de_xuat": True, "card_id": card_id,
                "note_vi": "Đã hỏi người dùng. KẾT THÚC lượt và chờ họ đặt tên."}

    @r.tool("snapshot.create", "Lịch sử",
            "Ghi một bản ưng ý với cái tên NGƯỜI DÙNG đã nói ra. Chỉ dùng khi họ đã đặt "
            "tên trong câu của họ — nếu chưa, dùng snapshot.propose để hỏi. Bạn không "
            "được nghĩ ra tên.",
            {"type": "object",
             "properties": {
                 "ten": {"type": "string",
                         "description": "Đúng cái tên người dùng đã gõ, không sửa lại"},
                 "ghi_chu": {"type": "string"},
                 "passed": {"type": "array", "items": {"type": "string"},
                            "description": "Mã REQ đã đạt tại mốc này, nếu biết"}},
             "required": ["ten"]},
            risk="R2", keywords=["ghi bản ưng ý", "snapshot", "chốt", "đặt tên"])
    def snapshot_create(ctx: Any, ten: str, ghi_chu: str = "", passed: list[str] | None = None):
        try:
            s = ctx.history.tao_snapshot(ten=ten, ghi_chu=ghi_chu, boi="human",
                                         passed=passed or [])
        except ValueError as e:
            return ToolResult(False, error=EideError(
                "E7007", str(e),
                hint_for_agent="Hỏi người dùng một cái tên khác, đừng tự đổi tên họ đặt.",
                alternatives=["snapshot.list", "snapshot.propose"], blame="user"))
        return {"snapshot": s.to_dict(), "tom_tat": s.tom_tat(),
                "note_vi": f"Đã ghi “{s.name}”. Nói lại cho người dùng bản này gồm gì."}

    @r.tool("snapshot.compare", "Lịch sử",
            "So sánh hai bản ưng ý theo loại hiện vật: yêu cầu thêm/bớt, Fact đổi, mã "
            "khác, tài liệu. Dùng 'hien_tai' cho vế thứ hai để so với trạng thái bây giờ.",
            {"type": "object",
             "properties": {"a": {"type": "string"},
                            "b": {"type": "string",
                                  "description": "snap-2 hoặc 'hien_tai'"}},
             "required": ["a"]},
            risk="R1", keywords=["so sánh", "snapshot", "khác nhau"])
    def snapshot_compare(ctx: Any, a: str, b: str = "hien_tai"):
        return ctx.history.so_sanh_snapshot(a, b)

    @r.tool("snapshot.restore", "Lịch sử",
            "Khôi phục dự án về một bản ưng ý. KHÔNG xoá lịch sử — tạo một changeset "
            "mới. Trước khi gọi, hãy gọi snapshot.compare để biết sẽ mất gì và nói cho "
            "người dùng.",
            {"type": "object",
             "properties": {
                 "snapshot": {"type": "string"},
                 "giu_ban_hien_tai": {
                     "type": "string",
                     "description": "Tên bản ưng ý để ghi lại trạng thái hiện tại trước "
                                    "khi khôi phục. Dùng khi người dùng có sửa chưa nằm "
                                    "trong bản ưng ý nào."}},
             "required": ["snapshot"]},
            risk="R2", gate="G-HIST",
            keywords=["khôi phục", "quay về", "restore", "snapshot"])
    def snapshot_restore(ctx: Any, snapshot: str, giu_ban_hien_tai: str = ""):
        truoc = ctx.history.se_mat_gi_khi_khoi_phuc(snapshot)
        if not truoc.get("ok"):
            return ToolResult(False, error=EideError(
                "E7004", truoc.get("message_vi", "không khôi phục được"),
                hint_for_agent="Gọi snapshot.list để xem có những bản ưng ý nào.",
                alternatives=["snapshot.list"], blame="agent"))

        kq = ctx.history.khoi_phuc_snapshot(
            snapshot, by="human", giu_ban_hien_tai=giu_ban_hien_tai or None)
        for c in kq.canh_bao:
            ctx.emit(uic.notice(c, level="info"))
        return {**kq.to_dict(), "da_mat": truoc.get("se_mat_vi", [])}

    @r.tool("snapshot.release", "Lịch sử",
            "Đánh dấu một bản ưng ý là RELEASE. Release là điều kiện cho các thao tác "
            "khoá vĩnh viễn (RDP, eFuse) — vì sau khi khoá thì không còn đường lùi, nên "
            "phải có một bản đã biết là chạy được.",
            {"type": "object",
             "properties": {"snapshot": {"type": "string"}},
             "required": ["snapshot"]},
            risk="R2", gate="G-SNAP",
            keywords=["release", "phát hành", "đánh dấu"])
    def snapshot_release(ctx: Any, snapshot: str):
        s = ctx.history.snapshots.danh_dau_release(snapshot)
        if s is None:
            cu = ctx.history.snapshots.get(snapshot)
            ly_do = (f"{snapshot} đã là release rồi." if cu and cu.kind == "release"
                     else f"Không có bản ưng ý có tên nào mã {snapshot}. "
                          "Checkpoint ngầm không đánh dấu release được.")
            return ToolResult(False, error=EideError(
                "E7005", ly_do, hint_for_agent="Gọi snapshot.list để xem danh sách.",
                alternatives=["snapshot.list"], blame="agent"))
        return {"snapshot": s.id, "ten": s.name, "kind": s.kind,
                "note_vi": f"“{s.name}” giờ là bản phát hành. Các thao tác khoá vĩnh "
                           "viễn trên chip đã có một bản để đối chiếu."}

    # ====================================================================== nhánh
    @r.tool("branch.create", "Lịch sử",
            "Rẽ một nhánh để thử phương án khác song song, không đụng tới nhánh hiện "
            "tại. Dùng khi người dùng muốn thử hai hướng mà chưa chốt hướng nào.",
            {"type": "object",
             "properties": {"ten": {"type": "string",
                                    "description": "thu-mtp, thu-mass-storage…"}},
             "required": ["ten"]},
            risk="R2", keywords=["nhánh", "branch", "thử", "song song"])
    def branch_create(ctx: Any, ten: str):
        kq = ctx.history.tao_nhanh(ten)
        if not kq.get("ok"):
            return ToolResult(False, error=EideError(
                "E7006", kq["message_vi"], blame="system"))
        return kq

    @r.tool("branch.switch", "Lịch sử",
            "Chuyển sang một nhánh khác. Trạng thái hiện tại được ghi checkpoint ngầm "
            "trước khi chuyển.",
            {"type": "object",
             "properties": {"ten": {"type": "string"}},
             "required": ["ten"]},
            risk="R2", core=False, keywords=["chuyển nhánh", "switch"])
    def branch_switch(ctx: Any, ten: str):
        kq = ctx.history.chuyen_nhanh(ten)
        if not kq.get("ok"):
            return ToolResult(False, error=EideError(
                "E7006", kq["message_vi"], blame="agent"))
        return kq

    @r.tool("branch.list", "Lịch sử",
            "Liệt kê các nhánh và cho biết đang ở nhánh nào.",
            {"type": "object", "properties": {}},
            risk="R1", keywords=["nhánh", "branch", "danh sách"])
    def branch_list(ctx: Any):
        ds = ctx.history.danh_sach_nhanh()
        return {"nhanh": ds, "dang_o": ctx.history.nhanh_hien_tai(),
                "note_vi": "" if len(ds) > 1 else
                "Chỉ có một nhánh. Muốn thử hai phương án song song thì gọi branch.create."}

    return r
