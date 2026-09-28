# -*- coding: utf-8 -*-
"""Công cụ plan mode: `plan.enter` / `plan.exit` / `plan.cancel` / `plan.step_done`.

Luồng, đúng theo MDD-40 §B5:

    plan.enter  → khoá mọi công cụ GHI, tác tử chỉ còn đọc và nghĩ
    (đọc, đo, hỏi)
    plan.exit   → kiểm kế hoạch bằng mã → tính `plan.big` → thẻ G-SCOPE nếu lớn
    (người duyệt)
    → kế hoạch thành hiện vật `plan:current`, hiện ở `<pending>` mỗi lượt
    → Stop hook đối chiếu công cụ đã gọi với công cụ trong kế hoạch

Xem `eide/ke_hoach.py` cho phần logic và cho lý do từng quyết định.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from ..ke_hoach import (MA_KE_HOACH, Buoc, KeHoach, doi_chieu, kiem_ke_hoach,
                        la_viec_lon)
from .registry import Registry, ToolResult

_SCHEMA_BUOC = {
    "type": "object",
    "properties": {
        "viec": {"type": "string", "description": "làm gì, một câu"},
        "cong_cu": {"type": "string", "description": "tên công cụ sẽ dùng; phải có thật"},
        "hien_vat": {"type": "string",
                     "description": "bước này để lại gì — tệp, Fact, changeset, số đo"},
        "cong": {"type": "string", "description": "cổng sẽ chạm, bỏ trống nếu không"},
        "chi_phi": {"type": "string", "description": "ước lượng: bao nhiêu lời gọi / bao lâu"},
        "ghi_chu": {"type": "string"}},
    "required": ["viec", "cong_cu", "hien_vat"]}


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def _lay(ctx: Any) -> KeHoach | None:
    a = ctx.store.get(MA_KE_HOACH)
    return KeHoach.from_dict(a.get("canonical") or {}) if a else None


def _ghi(ctx: Any, kh: KeHoach, tom_tat: str, vi_sao: str) -> None:
    ctx.store.apply(
        artefact_id=MA_KE_HOACH, type="plan",
        op="update" if ctx.store.get(MA_KE_HOACH) else "create",
        author=f"agent:{ctx.run_id}", canonical=kh.to_dict(),
        explain={"summary": tom_tat, "why": vi_sao, "sources": [], "diff_prev": "—",
                 "next": "—", "confidence": "CAU_HINH"},
        view_hint={"kind": "plan", "path": "kế hoạch"})


def dang_ky(r: Registry) -> None:
    @r.tool("plan.enter", "Điều phối",
            "VÀO CHẾ ĐỘ KẾ HOẠCH cho một việc lớn. Khoá mọi công cụ GHI lại: từ lúc này bạn "
            "chỉ đọc, đo và nghĩ, cho tới khi kế hoạch được người dùng duyệt. Dùng khi việc "
            "cần nhiều bước, chạm phần cứng, hoặc bạn chưa chắc cách làm — rẻ hơn nhiều so "
            "với đi sai rồi quay lại.",
            {"type": "object",
             "properties": {"viec": {"type": "string",
                                     "description": "việc lớn ấy là gì, một câu"}},
             "required": ["viec"]},
            risk="R1", core=True,
            keywords=["kế hoạch", "plan", "việc lớn", "nhiều bước", "chưa chắc cách làm"])
    def plan_enter(ctx: Any, viec: str):
        cu = _lay(ctx)
        # `da_duyet` KHÔNG chặn: một việc mới lớn hơn có quyền có kế hoạch mới, kể cả khi
        # kế hoạch cũ chưa đi hết — người dùng đổi ý là chuyện bình thường, và bắt tác tử
        # chạy nốt một kế hoạch đã lỗi thời là cách chắc nhất để nó làm sai việc.
        if cu and cu.trang_thai in ("dang_soan", "cho_duyet"):
            return ToolResult(False, error=EideError(
                "E6001", f"Đang có một kế hoạch dở ({cu.trang_thai}): {cu.muc_tieu[:80]}",
                hint_for_agent=("Làm nốt nó bằng `plan.exit`, hoặc bỏ bằng `plan.cancel` "
                                "rồi mới vào kế hoạch mới."),
                alternatives=["plan.exit", "plan.cancel"], blame="agent"))
        kh = KeHoach(muc_tieu=viec.strip(), trang_thai="dang_soan", run_id=ctx.run_id)
        _ghi(ctx, kh, f"vào chế độ kế hoạch: {viec[:60]}",
             "việc lớn — trình cách làm cho người dùng trước khi tiêu lời gọi")
        return {
            "trang_thai": "dang_soan", "muc_tieu": kh.muc_tieu,
            "note_vi": (
                "Đã vào **chế độ kế hoạch**. Mọi công cụ GHI đang bị khoá — bạn còn đọc, "
                "tìm, đo, và hỏi người dùng.\n\n"
                "Giờ hãy đi tìm hiểu đủ để trả lời được từng bước: *làm gì · bằng công cụ "
                "nào · để lại hiện vật gì · chạm cổng nào · tốn bao nhiêu*. Và liệt kê "
                "**giả định** bạn đang dựa vào — đó là phần người dùng bác được nhanh nhất, "
                "vì họ biết những thứ bạn không có cách nào biết.\n\n"
                "Nói rõ cả `ngoai_pham_vi`: thứ bạn cố ý KHÔNG làm. Một kế hoạch không nói "
                "mình không làm gì thì không giới hạn được gì.\n\n"
                "Xong thì gọi `plan.exit`.")}

    @r.tool("plan.exit", "Điều phối",
            "NỘP KẾ HOẠCH để người dùng duyệt. Kế hoạch được kiểm bằng mã trước (tên công cụ "
            "có thật không, bước nào thiếu hiện vật); việc lớn thì dựng thẻ G-SCOPE. Duyệt "
            "xong mới mở lại công cụ ghi.",
            {"type": "object",
             "properties": {
                 "buoc": {"type": "array", "items": _SCHEMA_BUOC,
                          "description": "các bước, theo đúng thứ tự sẽ làm"},
                 "gia_dinh": {"type": "array", "items": {"type": "string"},
                              "description": "điều bạn đang cho là đúng mà chưa kiểm được"},
                 "ngoai_pham_vi": {"type": "array", "items": {"type": "string"},
                                   "description": "thứ bạn cố ý KHÔNG làm trong kế hoạch này"}},
             "required": ["buoc"]},
            risk="R2", core=True,
            keywords=["nộp kế hoạch", "plan exit", "duyệt kế hoạch"])
    def plan_exit(ctx: Any, buoc: list[dict[str, Any]],
                  gia_dinh: list[str] | None = None,
                  ngoai_pham_vi: list[str] | None = None):
        kh = _lay(ctx)
        if kh is None or kh.trang_thai not in ("dang_soan", "cho_duyet"):
            return ToolResult(False, error=EideError(
                "E6002", "Chưa vào chế độ kế hoạch nên không có gì để nộp.",
                hint_for_agent="Gọi `plan.enter` trước.",
                alternatives=["plan.enter"], blame="agent"))
        kh.buoc = [Buoc(**{k: v for k, v in b.items() if k in Buoc.__slots__})
                   for b in (buoc or [])]
        kh.gia_dinh = list(gia_dinh or [])
        kh.ngoai_pham_vi = list(ngoai_pham_vi or [])

        loi = kiem_ke_hoach(kh, lambda t: ctx.registry.get(t) is not None)
        if loi:
            return ToolResult(False, error=EideError(
                "E6003", "Kế hoạch chưa dùng được: " + " · ".join(loi[:4]),
                hint_for_agent=("Sửa rồi gọi lại `plan.exit`. Đừng bỏ qua phần `hien_vat`: "
                                "một bước không để lại gì thì sau này không ai kiểm được nó "
                                "đã làm hay chưa."),
                details={"loi": loi}, blame="agent"))

        lon, vi_sao = la_viec_lon(kh, ctx.registry.get)
        kh.trang_thai = "cho_duyet" if lon else "da_duyet"
        _ghi(ctx, kh, f"nộp kế hoạch {len(kh.buoc)} bước",
             vi_sao or "việc nhỏ — không cần thẻ cổng")
        return {
            "plan_big": lon, "vi_sao_lon": vi_sao, "so_buoc": len(kh.buoc),
            "trang_thai": kh.trang_thai, "ke_hoach": kh.to_dict(),
            "note_vi": (
                (f"Kế hoạch {len(kh.buoc)} bước — **việc lớn** ({vi_sao}). Thẻ **G-SCOPE** "
                 "sẽ hiện ra cho người dùng duyệt; công cụ ghi còn khoá tới lúc đó. Trong "
                 "lúc chờ, đừng hỏi lại bằng lời để lách thẻ."
                 if lon else
                 f"Kế hoạch {len(kh.buoc)} bước — việc nhỏ, không cần thẻ cổng. Công cụ ghi "
                 "đã mở lại, bạn làm được ngay.")
                + (f" Bạn đang dựa vào {len(kh.gia_dinh)} giả định — nếu người dùng bác một "
                   "cái nào, sửa kế hoạch trước khi chạy tiếp." if kh.gia_dinh else
                   " Kế hoạch không nêu giả định nào; nếu thật sự không có thì tốt, còn "
                   "không thì phần bị giấu chính là phần sẽ sai."))}

    @r.tool("plan.step_done", "Điều phối",
            "Đánh dấu một bước của kế hoạch đã xong. Nói rõ hiện vật nó để lại.",
            {"type": "object",
             "properties": {
                 "so": {"type": "integer", "description": "số thứ tự bước, bắt đầu từ 1"},
                 "hien_vat": {"type": "string",
                              "description": "thứ bước ấy thật sự để lại; rỗng thì không "
                                             "đánh dấu xong được"}},
             "required": ["so", "hien_vat"]},
            risk="R1", core=False,
            keywords=["xong bước", "plan step", "đánh dấu bước"])
    def plan_step_done(ctx: Any, so: int, hien_vat: str):
        kh = _lay(ctx)
        if kh is None or kh.trang_thai != "da_duyet":
            return ToolResult(False, error=EideError(
                "E6002", "Không có kế hoạch nào đã duyệt để đánh dấu.",
                hint_for_agent="Chỉ đánh dấu được bước của một kế hoạch ĐÃ DUYỆT.",
                blame="agent"))
        if not 1 <= so <= len(kh.buoc):
            return ToolResult(False, error=EideError(
                "E5001", f"Kế hoạch có {len(kh.buoc)} bước, không có bước {so}.",
                blame="agent"))
        # Đòi hiện vật, không cho đánh dấu suông. Một bước "xong" mà không để lại gì thì
        # dấu tích ấy chỉ nói rằng tác tử tin là nó xong — đúng thứ N6 cấm.
        if not hien_vat.strip():
            return ToolResult(False, error=EideError(
                "E6004", f"Bước {so} chưa nói để lại hiện vật gì.",
                hint_for_agent=("Một bước 'xong' mà không để lại gì thì dấu tích ấy chỉ nói "
                                "rằng BẠN tin là nó xong. Nêu tệp, Fact, changeset hay số "
                                "đo cụ thể."),
                blame="agent"))
        kh.buoc[so - 1].xong = True
        # Xong hết thì ĐÓNG kế hoạch. Để nó ở `da_duyet` mãi thì nó chiếm chỗ "kế hoạch hiện
        # tại" và làm tác tử tưởng việc mới cũng nằm trong nó — đo được đúng thế trên phiên
        # FreeRTOS.
        if all(b.xong for b in kh.buoc):
            kh.trang_thai = "hoan_thanh"
        kh.buoc[so - 1].ghi_chu = (kh.buoc[so - 1].ghi_chu + " · " if kh.buoc[so - 1].ghi_chu
                                   else "") + f"hiện vật: {hien_vat.strip()}"
        _ghi(ctx, kh, f"xong bước {so}/{len(kh.buoc)}", hien_vat.strip()[:120])
        xong = sum(1 for b in kh.buoc if b.xong)
        return {"xong": xong, "tong": len(kh.buoc),
                "note_vi": f"Bước {so} xong ({xong}/{len(kh.buoc)}). Hiện vật: {hien_vat}."}

    @r.tool("plan.cancel", "Điều phối",
            "Bỏ kế hoạch đang soạn hoặc đang chạy, mở lại công cụ ghi. Nói rõ vì sao bỏ.",
            {"type": "object",
             "properties": {"vi_sao": {"type": "string"}},
             "required": ["vi_sao"]},
            risk="R1", core=False,
            keywords=["bỏ kế hoạch", "huỷ kế hoạch", "plan cancel"])
    def plan_cancel(ctx: Any, vi_sao: str):
        kh = _lay(ctx)
        if kh is None or kh.trang_thai == "huy":
            return ToolResult(False, error=EideError(
                "E6002", "Không có kế hoạch nào đang mở.", blame="agent"))
        truoc = kh.trang_thai
        kh.trang_thai = "huy"
        _ghi(ctx, kh, "bỏ kế hoạch", vi_sao.strip()[:160])
        return {"trang_thai_truoc": truoc,
                "note_vi": (f"Đã bỏ kế hoạch ({truoc} → huỷ). Công cụ ghi mở lại. Lý do ghi "
                            f"vào lịch sử: {vi_sao}")}


def ke_hoach_dang_chay(ctx_store: Any) -> KeHoach | None:
    """Kế hoạch ĐÃ DUYỆT đang chạy, nếu có. Dùng cho `<pending>` và Stop hook."""
    a = ctx_store.get(MA_KE_HOACH)
    if not a:
        return None
    kh = KeHoach.from_dict(a.get("canonical") or {})
    return kh if kh.trang_thai == "da_duyet" else None


def bao_cao_doi_chieu(kh: KeHoach, da_goi: list[str]) -> str:
    """Một câu cho người đọc: tác tử có đi đúng kế hoạch không."""
    d = doi_chieu(kh, da_goi)
    if not d["lech"]:
        return f"Đi đúng kế hoạch: {d['xong']}/{d['tong']} bước xong."
    phan = [f"{d['xong']}/{d['tong']} bước xong"]
    if d["ngoai_ke_hoach"]:
        phan.append("ngoài kế hoạch: " + ", ".join(d["ngoai_ke_hoach"][:6]))
    if d["chua_lam"]:
        phan.append("chưa đụng tới: " + ", ".join(d["chua_lam"][:6]))
    return (" · ".join(phan)
            + ". Lệch khỏi kế hoạch KHÔNG phải lỗi — thường là dấu hiệu kế hoạch thiếu. "
              "Nói ra để người dùng quyết: sửa kế hoạch, hay quay lại đúng nó.")
