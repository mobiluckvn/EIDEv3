# -*- coding: utf-8 -*-
"""Công cụ lưu trữ QUYẾT ĐỊNH THIẾT KẾ và quy trình — EIDE-MDD-40 §E2.

Bổ sung sau khi đo trên phiên làm việc thật (25/09, 33 lượt). Phiên đó phơi ra một
khoảng trống lớn: người dùng và tác tử **đã chốt xong bo mạch** (Raspberry Pi Zero 2 W),
đã chốt dung lượng, tên nhãn ổ đĩa, cơ chế đồng bộ — nhưng tất cả chỉ nằm trong vài
dòng văn xuôi của `EIDE.md`, vì đó là công cụ ghi duy nhất tác tử có.

Hậu quả của việc đó, theo đúng ngôn ngữ của tài liệu:

  - **Không có phiên bản.** Đổi bo mạch lần hai không tạo ra bản v2 để so với v1.
  - **Không có phụ thuộc.** §E5.4 nói đổi hộ chiếu chip thì pinout/mã/build thành STALE.
    Một dòng trong `EIDE.md` không có hạ nguồn nào để đánh dấu.
  - **Không hoàn tác riêng được.** Cả tệp là một hiện vật; lùi "quyết định bo mạch"
    đồng nghĩa lùi cả mục tiêu dự án ghi cùng lượt.
  - **Không so sánh được phương án.** §E2 đòi bảng so sánh cạnh nhau có cột điểm theo
    ràng buộc; văn xuôi không có cột.

Bốn nhóm công cụ ở đây lấp đúng chỗ đó:
  `store.option_*`  phương án và việc chọn phương án (→ sinh ADR)
  `store.adr_*`     quyết định có hệ quả, truy ngược được về ai quyết
  `store.bom_*`     linh kiện đã chốt mua
  `store.procedure_*` quy trình từng bước cho người làm theo — xem docstring bên dưới
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA


def register(r: Registry) -> Registry:

    # ====================================================================== phương án
    @r.tool("store.option_create", "Store",
            "Ghi một phương án kiến trúc vào kho. Gọi nhiều lần để có 2–4 phương án rồi "
            "mới so sánh. Số nào là ước lượng của bạn thì đánh dấu tầng ĐỒNG.",
            {"type": "object",
             "properties": {
                 "id": {"type": "string", "description": "PA-A, PA-B…"},
                 "ten": {"type": "string"},
                 "kien_truc": {"type": "string", "description": "Mô tả một câu"},
                 "linh_kien_chinh": {"type": "array", "items": {"type": "string"}},
                 "chi_phi_uoc": {"type": "string", "description": "Kèm đơn vị và nói rõ là ước"},
                 "do_kho": {"type": "string", "enum": ["thấp", "trung bình", "cao"]},
                 "rui_ro": {"type": "array", "items": {"type": "string"}},
                 "dap_ung_req": {"type": "array", "items": {"type": "string"},
                                 "description": "Mã REQ mà phương án này đáp ứng"},
                 "khong_dap_ung": {"type": "array", "items": {"type": "string"},
                                   "description": "Mã REQ mà nó KHÔNG đáp ứng — nói thẳng"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["id", "ten", "kien_truc", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["option"],
            keywords=["phương án", "kiến trúc", "lựa chọn", "option"])
    def option_create(ctx: Any, id: str, ten: str, kien_truc: str, explain: dict[str, Any],
                      linh_kien_chinh: list[str] | None = None, chi_phi_uoc: str = "",
                      do_kho: str = "", rui_ro: list[str] | None = None,
                      dap_ung_req: list[str] | None = None,
                      khong_dap_ung: list[str] | None = None):
        cu = ctx.store.get(id)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=id, type="option",
            op="update" if cu else "create",
            canonical={"ten": ten, "kien_truc": kien_truc,
                       "linh_kien_chinh": linh_kien_chinh or [],
                       "chi_phi_uoc": chi_phi_uoc, "do_kho": do_kho,
                       "rui_ro": rui_ro or [], "dap_ung_req": dap_ung_req or [],
                       "khong_dap_ung": khong_dap_ung or [], "da_chon": False},
            explain=explain, run_id=ctx.run_id,
            # M2-01 — `dap_ung_req` vốn đã nằm trong canonical, nhưng đồ thị phụ thuộc không
            # đọc canonical. Ghi thêm vào `deps` để STALE lan đúng phương án nào dựng từ REQ
            # nào, thay vì mọi phương án trong kho cùng sáng đèn.
            deps={"upstream": list(dap_ung_req)} if dap_ung_req else None)
        return {"id": id, "changeset": cs.id,
                "note_vi": "Đã ghi phương án. Khi người dùng chọn, gọi store.option_choose "
                           "— nó sẽ sinh một ADR ghi lại ai quyết và vì sao."}

    @r.tool("store.option_choose", "Store",
            "Chốt một phương án. Sinh kèm một ADR (quyết định kiến trúc) ghi lại: chọn "
            "gì, thay cho gì, hệ quả, và AI quyết. Đây là việc phải làm ngay khi người "
            "dùng nói họ chọn — đừng để quyết định chỉ nằm trong lời nói.",
            {"type": "object",
             "properties": {
                 "id": {"type": "string", "description": "Mã phương án được chọn"},
                 "quyet_boi": {"type": "string", "enum": ["nguoi", "tac_tu"],
                               "description": "Người dùng chọn, hay bạn đề xuất và họ chưa phản đối"},
                 "trich_loi_nguoi": {"type": "string",
                                     "description": "Nguyên văn câu họ chọn, nếu do họ quyết"},
                 "he_qua": {"type": "array", "items": {"type": "string"},
                            "description": "Chọn cái này thì kéo theo gì"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["id", "quyet_boi", "explain"]},
            risk="R2", gate="G-DESIGN", writes_artefact=True, needs_explain=True,
            produces=["adr"], keywords=["chọn phương án", "chốt", "quyết định"])
    def option_choose(ctx: Any, id: str, quyet_boi: str, explain: dict[str, Any],
                      trich_loi_nguoi: str = "", he_qua: list[str] | None = None):
        pa = ctx.store.get(id)
        if pa is None:
            return ToolResult(False, error=EideError(
                "E5005", f"Không có phương án nào mã {id} trong kho.",
                hint_for_agent="Ghi phương án bằng store.option_create trước khi chốt.",
                alternatives=["store.option_create", "store.list"], blame="agent"))

        # "Người quyết" là tầng tin cậy CAO NHẤT. Phải chứng minh được, không phải khai được.
        if quyet_boi == "nguoi":
            loi_chan = _kiem_nguoi_that_su_chon(ctx, pa, id, trich_loi_nguoi)
            if loi_chan is not None:
                return loi_chan

        # Bỏ dấu chọn ở các phương án khác — chỉ một phương án được chọn tại một thời điểm.
        for k in ctx.store.list("option", limit=20):
            if k["id"] != id and k["canonical"].get("da_chon"):
                ctx.history.ghi_kho(
                    author=f"agent:{ctx.run_id}", artefact_id=k["id"], type="option",
                    op="update", canonical={**k["canonical"], "da_chon": False},
                    explain={**explain,
                             "summary": f"Bỏ chọn {k['id']} vì {id} được chốt",
                             "diff_prev": f"{k['id']} không còn là phương án chọn"},
                    run_id=ctx.run_id)

        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=id, type="option", op="update",
            canonical={**pa["canonical"], "da_chon": True}, explain=explain,
            run_id=ctx.run_id)

        khac = [k["id"] for k in ctx.store.list("option", limit=20) if k["id"] != id]
        adr_id = f"ADR-{len(ctx.store.list('adr', limit=200)) + 1:02d}"
        cs_adr = ctx.history.ghi_kho(
            author="human" if quyet_boi == "nguoi" else f"agent:{ctx.run_id}",
            artefact_id=adr_id, type="adr", op="create",
            canonical={
                "tieu_de": f"Chọn {pa['canonical'].get('ten', id)}",
                "boi_canh": pa["canonical"].get("kien_truc", ""),
                "phuong_an_xet": [id] + khac,
                "chon": id,
                "he_qua": he_qua or [],
                "quyet_boi": quyet_boi,
                "trich_loi_nguoi": trich_loi_nguoi},
            explain=explain, run_id=ctx.run_id)

        return {"id": id, "adr": adr_id, "changeset": [cs.id, cs_adr.id],
                "stale": cs.stale_marked + cs_adr.stale_marked,
                "note_vi": f"Đã chốt {id} và ghi quyết định thành {adr_id}. "
                           "Mọi thứ dựng trên phương án khác giờ cần xem lại."}

    # ====================================================================== ADR
    @r.tool("store.adr_create", "Store",
            "Ghi một quyết định kỹ thuật không gắn với phương án nào (chọn giao thức, "
            "chọn thư viện, chọn cách làm). Mọi quyết định có hệ quả đều phải vào đây, "
            "không để nằm trong văn xuôi.",
            {"type": "object",
             "properties": {
                 "id": {"type": "string", "description": "ADR-01…"},
                 "tieu_de": {"type": "string"},
                 "boi_canh": {"type": "string", "description": "Vấn đề cần quyết"},
                 "phuong_an_xet": {"type": "array", "items": {"type": "string"}},
                 "chon": {"type": "string"},
                 "he_qua": {"type": "array", "items": {"type": "string"}},
                 "quyet_boi": {"type": "string", "enum": ["nguoi", "tac_tu"]},
                 "trich_loi_nguoi": {"type": "string"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["id", "tieu_de", "boi_canh", "chon", "quyet_boi", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["adr"],
            keywords=["quyết định", "adr", "chốt", "chọn"])
    def adr_create(ctx: Any, id: str, tieu_de: str, boi_canh: str, chon: str,
                   quyet_boi: str, explain: dict[str, Any],
                   phuong_an_xet: list[str] | None = None,
                   he_qua: list[str] | None = None, trich_loi_nguoi: str = ""):
        cu = ctx.store.get(id)
        cs = ctx.history.ghi_kho(
            author="human" if quyet_boi == "nguoi" else f"agent:{ctx.run_id}",
            artefact_id=id, type="adr", op="update" if cu else "create",
            canonical={"tieu_de": tieu_de, "boi_canh": boi_canh,
                       "phuong_an_xet": phuong_an_xet or [], "chon": chon,
                       "he_qua": he_qua or [], "quyet_boi": quyet_boi,
                       "trich_loi_nguoi": trich_loi_nguoi},
            explain=explain, run_id=ctx.run_id)
        return {"id": id, "changeset": cs.id, "stale": cs.stale_marked}

    # ====================================================================== BOM
    @r.tool("store.bom_set", "Thiết kế",
            "Ghi danh sách linh kiện đã chốt (BOM). Dùng khi người dùng nói họ sẽ mua gì. "
            "Mỗi dòng phải có lý do chọn; linh kiện chưa có datasheet thì nói thẳng.",
            {"type": "object",
             "properties": {
                 "dong": {"type": "array", "items": {"type": "object", "properties": {
                     "ma": {"type": "string"},
                     "ten": {"type": "string"},
                     "so_luong": {"type": "integer"},
                     "ly_do": {"type": "string"},
                     "gia_uoc": {"type": "string"},
                     "datasheet": {"type": "string", "description": "để trống nếu chưa có"}},
                     "required": ["ten", "ly_do"]}},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["dong", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["bom"],
            keywords=["bom", "linh kiện", "mua", "bo mạch", "board"])
    def bom_set(ctx: Any, dong: list[dict[str, Any]], explain: dict[str, Any]):
        cu = ctx.store.get("BOM")
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id="BOM", type="bom",
            op="update" if cu else "create",
            canonical={"dong": dong}, explain=explain, run_id=ctx.run_id)
        thieu = [d.get("ten") for d in dong if not d.get("datasheet")]
        return {"changeset": cs.id, "so_dong": len(dong),
                "chua_co_datasheet": thieu,
                "note_vi": ("Các linh kiện chưa có datasheet: " + ", ".join(thieu)
                            + ". Mọi thông số của chúng hiện là tri thức chung (tầng ĐỒNG), "
                              "không dùng để quyết định hay sinh mã được.") if thieu else ""}

    # ====================================================================== quy trình
    @r.tool("store.procedure_set", "Store",
            "Ghi một QUY TRÌNH TỪNG BƯỚC cho người làm theo (cài đặt, triển khai, đo "
            "kiểm, nạp firmware). Đây là hiện vật có cấu trúc, KHÔNG phải một tệp "
            "markdown: mỗi bước có lệnh, kết quả mong đợi, cách kiểm, và có thể đánh "
            "dấu đã làm xong. Dùng cái này thay vì fs.write một tệp hướng dẫn.",
            {"type": "object",
             "properties": {
                 "id": {"type": "string", "description": "QT-01, QT-trien-khai…"},
                 "tieu_de": {"type": "string"},
                 "muc_dich": {"type": "string", "description": "Làm xong thì đạt được gì"},
                 "chay_o_dau": {"type": "string",
                                "description": "máy phát triển | thiết bị đích | cả hai"},
                 "can_truoc": {"type": "array", "items": {"type": "string"},
                               "description": "Điều kiện phải có trước khi bắt đầu"},
                 "buoc": {"type": "array", "items": {"type": "object", "properties": {
                     "so": {"type": "integer"},
                     "viec": {"type": "string", "description": "Làm gì, một câu"},
                     "lenh": {"type": "string", "description": "Lệnh cụ thể, nếu có"},
                     "script": {"type": "string",
                                "description": "Đường dẫn script trong dự án, nếu bước này chạy script"},
                     "ket_qua_mong_doi": {"type": "string"},
                     "cach_kiem": {"type": "string", "description": "Làm sao biết bước này đã đúng"},
                     "canh_bao": {"type": "string", "description": "Nguy hiểm gì nếu làm sai"},
                     "khong_dao_nguoc": {"type": "boolean"}},
                     "required": ["so", "viec"]}},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["id", "tieu_de", "buoc", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["procedure"],
            keywords=["quy trình", "từng bước", "hướng dẫn", "triển khai", "cài đặt",
                      "step by step", "runbook"])
    def procedure_set(ctx: Any, id: str, tieu_de: str, buoc: list[dict[str, Any]],
                      explain: dict[str, Any], muc_dich: str = "",
                      chay_o_dau: str = "", can_truoc: list[str] | None = None):
        cu = ctx.store.get(id)
        # Bước nào trỏ tới script thì script đó phải tồn tại — một quy trình dẫn tới
        # tệp không có thật là thứ người dùng chỉ phát hiện khi đang đứng trước bo mạch.
        thieu = []
        for b in buoc:
            s = b.get("script")
            if s and not (ctx.config.paths.project_root / s).exists():
                thieu.append(f"bước {b.get('so')}: {s}")
        if thieu:
            return ToolResult(False, error=EideError(
                "E2002",
                "Quy trình trỏ tới script chưa tồn tại: " + "; ".join(thieu),
                hint_for_agent="Ghi các script bằng fs.write TRƯỚC, rồi mới ghi quy trình "
                               "trỏ tới chúng.",
                alternatives=["fs.write"], blame="agent"))

        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=id, type="procedure",
            op="update" if cu else "create",
            canonical={"tieu_de": tieu_de, "muc_dich": muc_dich,
                       "chay_o_dau": chay_o_dau, "can_truoc": can_truoc or [],
                       "buoc": buoc,
                       "tien_do": (cu or {}).get("canonical", {}).get("tien_do", {})},
            explain=explain, run_id=ctx.run_id)
        nguy = [b["so"] for b in buoc if b.get("khong_dao_nguoc")]
        return {"id": id, "so_buoc": len(buoc), "changeset": cs.id,
                "buoc_khong_dao_nguoc": nguy,
                "note_vi": (f"Bước {nguy} không đảo ngược được — khi người dùng chạy tới "
                            "đó, nhắc họ trước." if nguy else "")}

    @r.tool("store.procedure_progress", "Store",
            "Đánh dấu một bước trong quy trình đã làm xong hoặc thất bại. Dùng khi người "
            "dùng báo kết quả từng bước.",
            {"type": "object",
             "properties": {
                 "id": {"type": "string"},
                 "buoc": {"type": "integer"},
                 "trang_thai": {"type": "string", "enum": ["xong", "that_bai", "bo_qua"]},
                 "ghi_chu": {"type": "string"}},
             "required": ["id", "buoc", "trang_thai"]},
            risk="R2", core=False, keywords=["tiến độ", "bước", "xong", "thất bại"])
    def procedure_progress(ctx: Any, id: str, buoc: int, trang_thai: str,
                           ghi_chu: str = ""):
        a = ctx.store.get(id)
        if a is None:
            return ToolResult(False, error=EideError(
                "E5005", f"Không có quy trình {id}.", blame="agent"))
        td = dict(a["canonical"].get("tien_do") or {})
        td[str(buoc)] = {"trang_thai": trang_thai, "ghi_chu": ghi_chu}
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=id, type="procedure", op="update",
            canonical={**a["canonical"], "tien_do": td},
            explain={"summary": f"Bước {buoc} của {id}: {trang_thai}",
                     "why": ghi_chu or "người dùng báo kết quả",
                     "sources": [{"kind": "human_act", "ref": ctx.run_id, "tier": "NGUOI"}],
                     "diff_prev": f"bước {buoc} chuyển sang {trang_thai}",
                     "next": "làm bước tiếp theo", "confidence": "NGUOI"},
            run_id=ctx.run_id)
        xong = sum(1 for v in td.values() if v["trang_thai"] == "xong")
        return {"id": id, "xong": xong, "tong": len(a["canonical"].get("buoc", [])),
                "changeset": cs.id}

    # ====================================================================== Fact NGƯỜI
    @r.tool("fact.assert_human", "Tri thức",
            "Ghi một con số do CHÍNH NGƯỜI DÙNG nói ra thành Fact tầng NGƯỜI. Dùng khi "
            "bạn cần một con số để sinh mã mà nó chưa có trong tài liệu nào — nhưng "
            "người dùng đã nói nó. BẮT BUỘC trích nguyên văn lời họ. Fact tầng NGƯỜI "
            "dùng được như VÀNG, nhưng mọi nơi dùng đều phải ghi '(anh cho, chưa có "
            "tài liệu)'.",
            {"type": "object",
             "properties": {
                 "subject": {"type": "string",
                             "description": "chip:RPi-Zero-2W | net:USB | he-thong"},
                 "key": {"type": "string", "description": "dung_luong.o_dia, i2c.timeout…"},
                 "value": {"type": "string"},
                 "unit": {"type": "string"},
                 "trich_loi_nguoi": {"type": "string",
                                     "description": "NGUYÊN VĂN câu người dùng nói con số này"},
                 "dieu_kien": {"type": "string"}},
             "required": ["subject", "key", "value", "trich_loi_nguoi"]},
            risk="R2", keywords=["fact", "anh cho", "người dùng nói", "con số", "tầng người"])
    def fact_assert_human(ctx: Any, subject: str, key: str, value: str,
                          trich_loi_nguoi: str, unit: str = "", dieu_kien: str = ""):
        if not trich_loi_nguoi.strip():
            return ToolResult(False, error=EideError(
                "E5001", "Fact tầng NGƯỜI phải trích nguyên văn lời người dùng.",
                hint_for_agent="Không trích được câu nào nghĩa là con số này KHÔNG do họ "
                               "nói. Đừng gán tầng NGƯỜI cho phỏng đoán của bạn — hỏi họ "
                               "bằng ask_user.",
                alternatives=["ask_user"], blame="agent"))
        fid = f"f-nguoi-{abs(hash((subject, key))) % 10**8}"
        ctx.store.put_fact({
            "fact_id": fid, "subject": subject, "key": key, "value": value,
            "unit": unit, "condition": dieu_kien, "tier": "NGUOI", "origin": "user",
            "source": {"human_act_id": ctx.run_id, "quote": trich_loi_nguoi},
            "explain": {"summary": f"{key} = {value} {unit}".strip(),
                        "why": "Người dùng nói ra; chưa có tài liệu xác thực.",
                        "sources": [{"kind": "human_act", "ref": ctx.run_id,
                                     "tier": "NGUOI"}],
                        "diff_prev": "bản đầu tiên",
                        "next": "Tìm tài liệu để nâng lên tầng VÀNG.",
                        "confidence": "NGUOI"}})
        return {"fact_id": fid, "tier": "NGUOI",
                "note_vi": f"Đã ghi {key} = {value} {unit} ở tầng NGƯỜI. Dùng được để "
                           "sinh mã, nhưng mọi chỗ dùng phải ghi rõ '(anh cho, chưa có "
                           "tài liệu)', và nên đề nghị tìm tài liệu để nâng lên VÀNG."}

    return r

# ---------------------------------------------------------------- ai quyết, và dựa vào đâu

def _go_dau(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("d", "d")


def _kiem_nguoi_that_su_chon(ctx: Any, pa: dict[str, Any], ma: str, trich: str):
    """`quyet_boi="nguoi"` phải chứng minh được bằng sổ cái, không phải khai được bằng lời.

    Đo được ngày 28/09/2026 (ca TC004 của bộ usecase). Người dùng gõ đúng một câu:

        Làm cho mình cái mạch thông minh.

    Tác tử gọi `store.option_choose` với `quyet_boi="nguoi"` và đặt chính câu ấy vào
    `trich_loi_nguoi`, rồi tuyên "Đã chốt kiến trúc — ADR-01". Câu ấy **không chọn gì cả**:
    không nhắc phương án nào, không có chữ nào mang nghĩa lựa chọn. Nhưng ADR sinh ra sẽ
    vĩnh viễn nói rằng NGƯỜI DÙNG đã quyết, kèm trích dẫn.

    Đây là **giả mạo xuất xứ**, không phải lỗi trình bày. Nó vi phạm N1 theo cách tệ nhất:
    nguồn CÓ THẬT (người dùng có nói câu đó) nhưng KHÔNG nói điều được gán cho nó — và một
    trích dẫn thật đặt sai chỗ khó phát hiện hơn nhiều so với một trích dẫn bịa. `NGUOI` lại
    là tầng cao nhất, thứ mọi quyết định sau đó dựa vào mà không ai kiểm lại.

    Hai câu hỏi, cả hai đều tra được từ dữ liệu đã có — không phải tin lời tác tử:

    1. Câu trích có THẬT là lời người dùng không? Sổ cái ghi mọi `human_act`.
    2. Câu ấy có NHẮC TỚI phương án đang chốt không, theo mã hay theo tên? Không nhắc thì nó
       không thể là câu chọn *phương án đó*.

    Trả `None` nếu qua; trả `ToolResult` lỗi nếu không. Lỗi luôn nói ra HAI đường đi — chặn
    mà không chỉ lối thì tác tử sẽ thử lại đúng lối cũ.
    """
    def _chan(ma_loi: str, vi: str) -> ToolResult:
        return ToolResult(False, error=EideError(
            ma_loi, vi,
            hint_for_agent=(
                "Hai đường đi:\n"
                "1. `quyet_boi=\"tac_tu\"` — bạn đề xuất, người dùng chưa phản đối. Đây là "
                "lời khai trung thực và nó vẫn ghi được quyết định; tầng tin cậy thấp hơn, "
                "đúng với thực tế.\n"
                "2. Hỏi người dùng chọn phương án nào, đợi họ trả lời, rồi chốt bằng chính "
                "câu họ vừa nói.\n"
                "Đừng đặt một câu người dùng có nói vào chỗ một quyết định họ chưa ra: ADR "
                "sinh ra sẽ mang tầng NGUOI — tầng cao nhất — và mọi việc sau đó dựa vào nó "
                "mà không ai kiểm lại."),
            alternatives=["ask_user", "store.option_choose"], blame="agent"))

    if not (trich or "").strip():
        return _chan("E5006",
                     "Khai là NGƯỜI quyết thì phải kèm `trich_loi_nguoi` — nguyên văn câu họ "
                     "đã chọn.")

    # 1. Câu ấy có trong sổ cái không.
    noi_nguoi = [_go_dau(e.data.get("text", ""))
                 for e in ctx.ledger.read() if e.kind == "human_act"]
    t = _go_dau(trich)
    if not any(t in x for x in noi_nguoi):
        return _chan("E5007",
                     f"Câu trích {trich[:60]!r} không khớp lời nào của người dùng trong sổ "
                     "cái. Sổ cái ghi mọi câu họ gõ, nên đây không phải chuyện thiếu dữ "
                     "liệu.")

    # 2. Câu ấy có phải một câu CHỌN không.
    #
    # Chỉ đối chiếu từ ngữ với tên phương án là chưa đủ: bản đầu của phép kiểm này cho lọt
    # đúng ca nó canh, vì "Làm cho mình cái **mạch** thông minh" và tên phương án "Bo **mạch**
    # Linux nhỏ làm USB gadget" cùng có chữ "mạch" — một từ chung của cả lĩnh vực. Nên phải
    # có thêm một DẤU HIỆU CHỌN: người dùng nói chọn/dùng/lấy/đồng ý, chứ không chỉ nhắc tới
    # một danh từ trùng.
    if not any(k in t for k in _DAU_HIEU_CHON):
        return _chan("E5008",
                     f"Câu trích {trich[:60]!r} không có chữ nào mang nghĩa lựa chọn "
                     "(chọn · dùng · lấy · theo · đồng ý · duyệt), nên nó không phải một câu "
                     "quyết định.")

    # 3. Và câu ấy phải nhắc tới ĐÚNG phương án đang chốt.
    ten = str(pa.get("canonical", {}).get("ten") or "")
    tu_ten = [w for w in _go_dau(ten).split()
              if len(w) >= 4 and w not in _TU_CHUNG]
    nhac = _go_dau(ma) in t or any(w in t for w in tu_ten)
    if not nhac:
        return _chan("E5009",
                     f"Câu trích {trich[:60]!r} có ý lựa chọn nhưng không nhắc tới {ma} "
                     f"({ten!r}) — chưa đủ để biết họ chọn phương án NÀO.")
    return None


# Chữ mang nghĩa lựa chọn. Thiếu chúng thì câu ấy không phải một quyết định.
_DAU_HIEU_CHON = ("chon", "dung ", "lay ", "theo ", "dong y", "duyet", "ok ", "chot",
                  "quyet dinh", "di voi", "uu tien")

# Từ chung của cả lĩnh vực — trùng nhau không nói lên điều gì.
_TU_CHUNG = {"mach", "board", "bo", "chip", "thiet", "phuong", "an", "he", "thong", "cho",
             "minh", "lam", "cai", "thong minh", "duoc", "voi", "cua", "tren"}

