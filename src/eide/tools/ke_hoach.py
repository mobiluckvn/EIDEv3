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

from pathlib import Path
from typing import Any

from ..errors import EideError
from ..ke_hoach import (MA_KE_HOACH, Buoc, KeHoach, doi_chieu, kiem_ke_hoach,
                        la_viec_lon)
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

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


def _tach_tieu_de(than: str, mac_dinh: str) -> tuple[str, str]:
    """Nếu phần này tự mở đầu bằng một tiêu đề mức 1, lấy nó làm tên phần và bỏ khỏi thân.

    Không làm thì tài liệu hợp nhất có tên phần HAI LẦN, một lần do kế hoạch đặt và một lần
    của chính tệp — và hai cái ấy thường không trùng chữ, nên người đọc tưởng là hai mục.
    """
    dong = than.split("\n")
    for i, d in enumerate(dong):
        if not d.strip():
            continue
        if d.lstrip().startswith("# "):
            return d.lstrip()[2:].strip() or mac_dinh, "\n".join(dong[i + 1:]).strip()
        break
    return mac_dinh, than


def _ha_tieu_de(than: str, bac: int) -> str:
    """Hạ mọi tiêu đề trong một phần xuống `bac` cấp, bỏ qua phần trong khối mã.

    Mỗi phần vốn là một tài liệu đứng riêng nên nó mở đầu ở mức `#`. Ghép thẳng vào dưới một
    mục `##` thì thứ bậc **lộn ngược**: mục con hiện ra to hơn mục cha. Đo được ngay lần chạy
    thử đầu của `plan.merge`.

    Bỏ qua khối ```: một dòng `# include` trong mã C không phải tiêu đề, và hạ nó đi là sửa
    mã của người dùng.
    """
    ra: list[str] = []
    trong_ma = False
    for d in than.split("\n"):
        if d.lstrip().startswith("```"):
            trong_ma = not trong_ma
        elif not trong_ma and d.lstrip().startswith("#"):
            dau = d.lstrip()
            n = len(dau) - len(dau.lstrip("#"))
            if 1 <= n <= 6 and dau[n:n + 1] in (" ", "\t"):
                d = "#" * min(n + bac, 6) + dau[n:]
        ra.append(d)
    return "\n".join(ra)


def _cat_di(ctx: Any, kh: KeHoach) -> str:
    """Cất một kế hoạch đang chạy sang mã riêng, trả về mã ấy.

    `plan:current` là **một** hiện vật; thay nội dung nó là mất bản cũ. Một việc lớn trải qua
    nhiều kế hoạch nối nhau (trần 20 bước/kế hoạch) thì không có bản cũ nghĩa là không có cách
    nào nhìn lại toàn bộ chặng đường — đúng lúc người dùng cần nhìn nhất.
    """
    ma = f"plan:{kh.run_id or ctx.run_id}"
    xong = sum(1 for b in kh.buoc if b.xong)
    ctx.store.apply(
        artefact_id=ma, type="plan", op="update" if ctx.store.get(ma) else "create",
        author=f"agent:{ctx.run_id}", canonical={**kh.to_dict(), "trang_thai": "da_cat"},
        explain={"summary": f"cất kế hoạch “{kh.muc_tieu[:50]}” ({xong}/{len(kh.buoc)} bước)",
                 "why": "một kế hoạch mới thay chỗ; bản cũ giữ lại để còn nhìn lại được",
                 "sources": [], "diff_prev": "—", "next": "—", "confidence": "CAU_HINH"},
        view_hint={"kind": "plan", "path": "kế hoạch đã cất"})
    return ma


def _hien_vat_co_that(ctx: Any, s: str) -> tuple[bool, str]:
    """Chuỗi `hien_vat` có trỏ tới thứ MỞ RA XEM ĐƯỢC không?

    Ba loại nhận: đường dẫn tệp có thật trong dự án · mã hiện vật có trong kho · mã changeset
    có trong sổ changeset.

    Vì sao phải kiểm: đo được 30/09/2026, `plan.step_done(1, "tôi đã viết xong chương 1 rồi
    nhé")` được **nhận**, bước thành xong. Phép kiểm cũ chỉ đòi chuỗi khác rỗng. Một dấu tích
    "xong" như thế chỉ nói rằng tác tử tin là nó xong — đúng thứ N6 cấm, và là chỗ đậu giả rẻ
    nhất còn lại trong chế độ kế hoạch.

    Cùng một kỷ luật mà `bang_chung` của tác tử con đã có từ đầu: *"tôi đã kiểm" không phải
    bằng chứng*.
    """
    t = (s or "").strip()
    if not t:
        return False, "rỗng"
    try:
        goc = Path(ctx.config.paths.project_root).resolve()
        for phan in t.replace(",", " ").split():
            q = (goc / phan.strip("`'\"")).resolve()
            if q == goc or goc in q.parents:
                if q.exists():
                    return True, f"tệp `{phan}`"
    except Exception:                                                  # noqa: BLE001
        pass
    kho = getattr(ctx, "store", None)
    if kho is not None:
        for phan in t.replace(",", " ").split():
            if kho.get(phan.strip("`'\"")):
                return True, f"hiện vật `{phan}`"
    lich_su = getattr(ctx, "history", None)
    log = getattr(lich_su, "log", None)
    if log is not None:
        for phan in t.replace(",", " ").split():
            ma = phan.strip("`'\"")
            try:
                if ma.startswith("cs-") and log.get(ma):
                    return True, f"changeset `{ma}`"
            except Exception:                                          # noqa: BLE001
                pass
    return False, "không trỏ tới tệp, hiện vật hay changeset nào có thật"


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
        #
        # NHƯNG không được làm MẤT nó. Đo được 30/09/2026: đang giữa kế hoạch 3 bước, đã xong
        # bước 1, gọi `plan.enter` lần nữa → kế hoạch cũ biến mất sạch, mục tiêu đổi, số bước
        # về 0, không một lời báo. Lý lẽ "người dùng đổi ý" biện minh cho việc CHO PHÉP kế
        # hoạch mới; nó không biện minh cho việc xoá dấu vết phần đã làm.
        #
        # Nên: cất kế hoạch cũ sang một mã riêng rồi mới thay. Hai thứ ấy khác nhau.
        luu_o = ""
        if cu and cu.trang_thai == "da_duyet":
            luu_o = _cat_di(ctx, cu)
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
            "ke_hoach_cu_luu_o": luu_o,
            "note_vi": (
                (f"Kế hoạch trước ({sum(1 for b in cu.buoc if b.xong)}/{len(cu.buoc)} bước "
                 f"đã xong) được cất ở `{luu_o}`, không mất. Nói cho người dùng biết điều "
                 "đó.\n\n" if luu_o else "")
                + "Đã vào **chế độ kế hoạch**. Mọi công cụ GHI đang bị khoá — bạn còn đọc, "
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
        # Nhiều bước cùng khai MỘT hiện vật: nói ra NGAY BÂY GIỜ, lúc sửa còn rẻ.
        #
        # Đây không phải lỗi — một bước hoàn toàn có thể mở rộng tệp bước trước viết. Nhưng
        # nó có hai hệ quả người duyệt cần biết trước khi gật: (a) `plan.merge` sẽ không có
        # gì để ghép, vì tệp ấy đã là bản hợp nhất; (b) hỏng một bước thì phải làm lại cả
        # nhóm dùng chung tệp, chứ không làm lại riêng bước ấy.
        #
        # Đo được 30/09/2026 qua giao diện thật, hai lượt liền: tác tử viết cả 6 rồi cả 8
        # phần vào một tệp, và chuyện ấy chỉ lộ ra ở `plan.merge` — tức sau khi đã làm xong
        # hết. Phát hiện đúng nhưng muộn thì không cứu được lần chạy ấy.
        dung_chung: dict[str, list[int]] = {}
        for n, b in enumerate(kh.buoc, 1):
            dung_chung.setdefault(b.hien_vat.strip(), []).append(n)
        nhom = {h: ds for h, ds in dung_chung.items() if len(ds) > 1 and h}

        return {
            "buoc_dung_chung_hien_vat": {h: ds for h, ds in nhom.items()},
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
                   "không thì phần bị giấu chính là phần sẽ sai.")
                + ("".join(
                    f"\n\n⚠︎ Bước {', '.join(map(str, ds))} cùng ghi vào `{h}`. Hai hệ quả: "
                    "`plan.merge` sẽ KHÔNG có gì để ghép (tệp ấy đã là bản hợp nhất), và hỏng "
                    "một bước thì phải làm lại cả nhóm chứ không làm lại riêng bước ấy. Nếu "
                    "sản phẩm cuối là MỘT tài liệu ghép từ nhiều phần thì cho mỗi bước một "
                    "tệp riêng rồi gộp; nếu cố ý viết dồn thì giữ nguyên và nói với người "
                    "dùng là sẽ không có bước gộp."
                    for h, ds in nhom.items()) if nhom else ""))}

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
        # Đòi hiện vật MỞ RA XEM ĐƯỢC, không cho đánh dấu suông.
        #
        # Bản đầu chỉ đòi chuỗi khác rỗng, nên `plan.step_done(1, "tôi đã viết xong chương 1
        # rồi nhé")` được nhận — đo được 30/09/2026. Một dấu tích "xong" như thế chỉ nói rằng
        # tác tử TIN là nó xong; đúng thứ N6 cấm.
        co_that, vi = _hien_vat_co_that(ctx, hien_vat)
        if not co_that:
            hua = kh.buoc[so - 1].hien_vat.strip()
            return ToolResult(False, error=EideError(
                "E6004",
                f"Bước {so}: “{hien_vat.strip()[:60]}” {vi} — chưa đánh dấu xong được.",
                hint_for_agent=(
                    "`hien_vat` phải trỏ tới thứ NGƯỜI KHÁC MỞ RA XEM ĐƯỢC: đường dẫn tệp có "
                    "thật, mã hiện vật trong kho, hay mã changeset. Một câu kể lại việc mình "
                    "vừa làm không phải hiện vật."
                    + (f" Kế hoạch hứa bước này để lại `{hua}` — làm nó ra trước, hoặc nói "
                       "rõ bạn để lại thứ khác và thứ ấy ở đâu." if hua else "")),
                details={"hua": hua, "nhan_duoc": hien_vat.strip()[:120]},
                alternatives=["fs.write", "store.list", "history.diff"], blame="agent"))
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
        con = [i for i, b in enumerate(kh.buoc, 1) if not b.xong]
        return {"xong": xong, "tong": len(kh.buoc), "kiem_hien_vat": vi,
                "con_lai": con,
                "note_vi": (f"Bước {so} xong ({xong}/{len(kh.buoc)}). Hiện vật: {vi} — đã "
                            "kiểm là mở ra được."
                            + (f" Còn bước {', '.join(map(str, con))}."
                               if con else
                               " Hết bước. Gộp các phần lại bằng `plan.merge` nếu việc này "
                               "cần một sản phẩm hợp nhất."))}

    @r.tool("plan.merge", "Điều phối",
            "GỘP kết quả các bước thành MỘT sản phẩm. Dùng khi việc lớn được chia nhỏ ra làm "
            "nhiều lần — mỗi bước để lại một phần, và cuối cùng người dùng cần một tệp hoàn "
            "chỉnh. Chỉ gộp được khi mọi bước đã xong, và nó NÓI RA phần nào không gộp được.",
            {"type": "object",
             "properties": {
                 "ra": {"type": "string",
                        "description": "tệp .md sẽ tạo — sau đó dùng doc.render nếu cần "
                                       "Word/PDF/PowerPoint"},
                 "tieu_de": {"type": "string", "description": "tên tài liệu hợp nhất"},
                 "mo_dau": {"type": "string",
                            "description": "đoạn mở đầu bạn tự viết; bỏ trống thì không có"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ra", "explain"]},
            risk="R2", gate="G-FILE", writes_artefact=True, needs_explain=True, core=False,
            keywords=["gộp", "hợp nhất", "ghép lại", "merge", "tổng hợp", "ráp các phần"],
            returns_vi="Đường dẫn tệp hợp nhất và danh sách phần KHÔNG gộp được")
    def plan_merge(ctx: Any, ra: str, explain: dict[str, Any], tieu_de: str = "",
                   mo_dau: str = ""):
        """Ghép hiện vật của từng bước thành một tài liệu, theo ĐÚNG thứ tự bước.

        ## Vì sao cần một công cụ riêng cho việc này

        Chế độ kế hoạch chia được việc lớn ra nhiều bước, giữ được qua nhiều lượt và qua cả
        `kill -9`, và đòi mỗi bước để lại hiện vật. Nhưng khi bước cuối xong thì nó chỉ đổi
        `trang_thai` thành `hoan_thanh` rồi thôi — **không ai ráp các phần lại**.

        Với "viết tài liệu thiết kế cho một con chip", mỗi bước ra một chương; phần việc cuối
        cùng — ghép theo thứ tự, sinh mục lục, và nói ra chương nào hụt — trước tệp này không
        có chỗ nào lo. Người dùng nhận về mười tệp rời và tự ráp.

        ## Nó KHÔNG làm gì

        Không viết lại nội dung, không "làm cho mạch lạc", không sửa thuật ngữ cho thống nhất.
        Ghép là ghép; sửa văn là việc tác tử làm bằng `fs.edit` sau đó, và khi ấy diff hiện ra
        đúng chỗ nó sửa. Một công cụ vừa ghép vừa viết lại thì người duyệt không phân biệt
        được chỗ nào là bản gốc chỗ nào là bản nó tự chế.

        Và **không gộp thứ không đọc được thành chữ**: bước để lại một tệp `.elf` hay một mã
        changeset thì nó được kê trong mục "phần không gộp vào được", kèm lý do — chứ không
        bị nhét bừa vào giữa tài liệu, cũng không bị bỏ qua im lặng.
        """
        from .writing import _rel, _sandbox

        kh = _lay(ctx)
        if kh is None or kh.trang_thai not in ("da_duyet", "hoan_thanh"):
            return ToolResult(False, error=EideError(
                "E6002", "Không có kế hoạch nào đã duyệt để gộp.",
                hint_for_agent="Chỉ gộp được kết quả của một kế hoạch ĐÃ DUYỆT.",
                alternatives=["plan.enter"], blame="agent"))
        chua = [i for i, b in enumerate(kh.buoc, 1) if not b.xong]
        if chua:
            return ToolResult(False, error=EideError(
                "E6005",
                f"Còn {len(chua)} bước chưa xong ({', '.join(map(str, chua))}) — chưa gộp "
                "được.",
                hint_for_agent=("Gộp khi mới làm một nửa sẽ ra một tài liệu THIẾU mà trông "
                                "như đủ. Làm nốt rồi `plan.step_done`, hoặc nếu cố ý bỏ thì "
                                "nói với người dùng trước."),
                details={"chua_xong": chua}, blame="agent"))

        p_ra = _sandbox(ctx, ra)
        if p_ra.suffix.lower() != ".md":
            return ToolResult(False, error=EideError(
                "E6006", f"`ra` phải là tệp `.md`, nhận được {p_ra.name}.",
                hint_for_agent=("Gộp ra Markdown trước — đó là dạng xem được diff và hoàn tác "
                                "được. Cần Word/PDF/PowerPoint thì `doc.render` từ tệp ấy."),
                alternatives=["doc.render"], blame="agent"))

        goc = Path(ctx.config.paths.project_root).resolve()
        phan: list[str] = []
        muc_luc: list[str] = []
        bo_lai: list[dict[str, str]] = []
        # Nhiều bước có thể cùng để lại MỘT tệp — tác tử viết dồn vào một chỗ là chuyện
        # thường. Ghép tệp ấy nhiều lần thì tài liệu ra có nội dung lặp y hệt nhau, mà lời
        # gọi vẫn `ok`. Đo được 30/09/2026 qua giao diện thật: sáu bước cùng sửa `y-tuong.md`,
        # bản gộp nhân sáu, và tác tử phải tự viết đè lên để chữa.
        da_lay: dict[Any, str] = {}
        trung: list[dict[str, str]] = []
        for i, b in enumerate(kh.buoc, 1):
            # `ghi_chu` mang "hiện vật: …" do `plan.step_done` ghi vào; nó là thứ ĐÃ ĐƯỢC
            # KIỂM, còn `b.hien_vat` chỉ là lời hứa lúc lập kế hoạch.
            thuc = b.ghi_chu.split("hiện vật:")[-1].strip() if "hiện vật:" in b.ghi_chu \
                else b.hien_vat.strip()
            tep = None
            for x in thuc.replace(",", " ").split():
                q = (goc / x.strip("`'\"")).resolve()
                if (q == goc or goc in q.parents) and q.is_file():
                    tep = q
                    break
            if tep is None or tep.suffix.lower() not in (".md", ".txt"):
                bo_lai.append({"buoc": str(i), "viec": b.viec,
                               "hien_vat": thuc,
                               "vi_sao": ("không phải tệp chữ" if tep is not None
                                          else "không phải một tệp trong dự án")})
                continue
            try:
                than = tep.read_text("utf-8").strip()
            except (OSError, UnicodeDecodeError) as e:
                bo_lai.append({"buoc": str(i), "viec": b.viec, "hien_vat": thuc,
                               "vi_sao": f"không đọc được: {e}"})
                continue
            if tep in da_lay:
                # Nhiều bước cùng trỏ một tệp: ghép nó nhiều lần là nhân bản nội dung.
                trung.append({"buoc": str(i), "viec": b.viec,
                              "cung_voi": da_lay[tep], "tep": _rel(ctx, tep)})
                continue
            da_lay[tep] = str(i)
            ten_phan, than = _tach_tieu_de(than, b.viec)
            muc_luc.append(f"{i}. {ten_phan}")
            phan.append(f"## {i}. {ten_phan}\n\n*Nguồn: `{_rel(ctx, tep)}`*\n\n"
                        + _ha_tieu_de(than, 2))

        if len(phan) == 1 and len(kh.buoc) > 1 and trung:
            # Mọi bước cùng một tệp: tệp ấy ĐÃ LÀ bản hợp nhất, gộp nữa chỉ chép lại nó.
            return ToolResult(False, error=EideError(
                "E6008",
                f"Cả {len(kh.buoc)} bước đều để lại cùng một tệp "
                f"(`{next(iter(da_lay))!s}`) — không có gì để ghép.",
                hint_for_agent=(
                    "Tệp ấy đã là bản hợp nhất rồi: các bước viết dồn vào một chỗ. Nói với "
                    "người dùng điều đó, và nếu họ cần một tệp riêng thì chép/đổi tên nó "
                    "bằng `fs.write`. Lần sau, muốn gộp được thì mỗi bước viết ra MỘT TỆP "
                    "riêng — chia bước sao cho mỗi bước đẻ ra một tệp."),
                details={"tep": _rel(ctx, next(iter(da_lay))),
                         "trung": trung}, blame="agent"))
        if not phan:
            return ToolResult(False, error=EideError(
                "E6007", "Không bước nào để lại tệp chữ để gộp.",
                hint_for_agent=("Gộp chỉ ráp được tệp `.md`/`.txt`. Nếu các bước để lại mã "
                                "hay dữ liệu nhị phân thì việc này không phải việc gộp — nói "
                                "với người dùng thứ họ thật sự đang cần."),
                details={"bo_lai": bo_lai}, blame="agent"))

        d = [f"# {tieu_de.strip() or kh.muc_tieu}", ""]
        if mo_dau.strip():
            d += [mo_dau.strip(), ""]
        d += ["## Mục lục", ""] + [f"{x}" for x in muc_luc] + [""]
        if bo_lai:
            # Nói ra ngay trong tài liệu, không giấu vào kết quả lời gọi. Người đọc bản hợp
            # nhất phải biết nó KHÔNG đủ, chứ không phải người gọi công cụ.
            d += ["> **Chưa gộp vào đây:** "
                  + " · ".join(f"bước {x['buoc']} ({x['viec']}) — {x['vi_sao']}"
                               for x in bo_lai), ""]
        d += ["---", ""] + ["\n\n".join(phan), ""]
        noi_dung = "\n".join(d)

        cu_nd = p_ra.read_text("utf-8", errors="replace") if p_ra.exists() else None
        p_ra.parent.mkdir(parents=True, exist_ok=True)
        p_ra.write_text(noi_dung, "utf-8")
        rel = _rel(ctx, p_ra)
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[rel],
            summary=explain.get("summary", f"gộp {len(phan)} phần của kế hoạch"),
            explain=explain, noi_dung_truoc={rel: cu_nd} if cu_nd is not None else None,
            run_id=ctx.run_id)
        ctx.mark_agent_wrote(rel)
        return {
            "tep": rel, "so_phan_da_gop": len(phan), "so_buoc": len(kh.buoc),
            "khong_gop_duoc": bo_lai, "trung_tep": trung, "changeset": cs.id,
            "ky_tu": len(noi_dung),
            "note_vi": (
                f"Gộp **{len(phan)}/{len(kh.buoc)} bước** thành `{rel}` ({len(noi_dung)} ký "
                "tự), theo đúng thứ tự bước, mỗi phần ghi rõ nguồn."
                + ((f"\n\n{len(trung)} bước dùng chung tệp với bước khác nên chỉ ghép một "
                    "lần: " + " · ".join(f"bước {x['buoc']} ≡ bước {x['cung_voi']}"
                                         for x in trung)) if trung else "")
                + (("\n\n**Không gộp được " + str(len(bo_lai)) + " phần** — đã ghi thẳng "
                    "vào đầu tài liệu chứ không giấu: "
                    + " · ".join(f"bước {x['buoc']} ({x['vi_sao']})" for x in bo_lai))
                   if bo_lai else "")
                + "\n\nGộp là GHÉP, không phải viết lại: thuật ngữ lệch nhau hay chỗ trùng "
                  "lặp giữa các phần thì sửa bằng `fs.edit` để diff hiện đúng chỗ bạn sửa. "
                  "Cần bản Word/PDF/PowerPoint thì `doc.render` từ tệp này.")}

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
