# -*- coding: utf-8 -*-
"""Công cụ sinh sơ đồ nguyên lý — EIDE-SCH-44 §3, sửa theo EIDE-HIER-45 §7. Bước SCH-A.

Ba công cụ đầu của đường ống bảy bước: `sch.compose` → `sch.netlist` → `sch.symbols`.

**Mọi công cụ ở đây mang `feature="schematic"`.** Cờ tắt (mặc định) thì chúng không được
ĐĂNG KÝ — mô hình không thấy, không gọi được, và lược đồ tool không tăng một token nào
(SCH-44 §2.1 lớp bảo vệ số 1). Đó là lý do bộ hồi quy hai chế độ phải giống 100 %: khi cờ
tắt, sản phẩm phải **y nguyên** như trước khi có tính năng này.

Ràng buộc cứng (quyết định 25/09/2026): máy này KHÔNG cài KiCad. Không gọi `kicad-cli`,
không đề nghị người dùng cài KiCad — có chốt chặn ở hook `Stop`, vì cấm bằng lời trong hiến
pháp là cấm không đo được.

Suy giảm R3 (§6): bước nào không làm được thì **nói thẳng** và trả về thứ đang có (sơ đồ
khối + đồ thị net), chứ không trả một tệp nửa vời trông như đã xong.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from ..knowledge import cay as KC
from ..knowledge import ckm as K
from ..protocol import uicommand as uic
from .registry import Registry, Requirement, ToolResult
from .writing import EXPLAIN_SCHEMA

MA_SKIDL = "skidl:mach"
MA_BO_CUC = "layout:mach"
MA_NETLIST_KICAD = "netlist_kicad:mach"
MA_SYMBOL = "symbol_map:mach"

TEP_SKIDL = "sch/mach_skidl.py"
TEP_NET = "sch/mach.net"
TEP_SYM = "sch/eide-sinh.kicad_sym"
TEP_SCH = "sch/mach.kicad_sch"
TEP_PRO = "sch/mach.kicad_pro"
TEP_SVG = "sch/mach.svg"
THU_MUC_GOI = "sch/goi"


def register(r: Registry) -> Registry:

    # ====================================================================== 1. soạn
    @r.tool("sch.compose", "Thiết kế",
            "Soạn tệp SKiDL mô tả mạch từ cây khối: mỗi khối thành một hàm, Port thành tham "
            "số, linh kiện thành Part. Mã sinh tệp — bạn chỉ chọn style. Chân dùng phải có "
            "trong Fact pinout, nên nó không bịa được chân.",
            {"type": "object",
             "properties": {
                 "style": {"type": "string", "enum": ["hierarchical", "flat"],
                           "description": "hierarchical = mỗi khối một sheet (mặc định, "
                                          "đúng cho cây sâu); flat = tất cả trên một sheet"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            # KHÔNG khai `requires` ở đây, dù §3.1 ghi "requires: module_graph ≥ 1,
            # netlist_ckm, passport". Lý do đo được: `check_preconditions` chạy TRƯỚC thân
            # công cụ và trả một câu chung ("thiếu 1 ckm"), che mất câu R3 giàu thông tin hơn
            # mà thân công cụ dựng được — nó liệt kê đúng thứ đang thiếu, gọi gì để có, và
            # nhắc rằng sơ đồ khối vẫn dùng được. Hai chỗ kiểm cùng một điều kiện thì chỗ có
            # nhiều ngữ cảnh hơn phải là chỗ nói.
            risk="R2", feature="schematic", writes_artefact=True, needs_explain=True,
            produces=["skidl_src"],
            keywords=["sơ đồ", "schematic", "skidl", "soạn", "sinh sơ đồ", "kicad"])
    def compose(ctx: Any, explain: dict[str, Any], style: str = "hierarchical"):
        from ..sch import soan
        from ..sch import kyhieu as KH

        cay = KC.Cay.doc(ctx.store)
        if not cay.goc:
            return _r3(ctx, "Chưa có cây khối nào để soạn sơ đồ.",
                       goi=["ckm.module_set", "ckm.build"])

        # Tiền đề của SCH-44 §3 bước 1 — và chúng đã được `ckm.build` tính sẵn, nên đọc lại
        # thay vì tính lần hai: hai chỗ tính cùng một điều kiện là hai chỗ để lệch nhau.
        thieu = K.thieu_gi(_dem(ctx))
        if thieu:
            return _r3(ctx, "Bản đồ mạch chưa đủ để sinh sơ đồ. Thiếu: "
                            + "; ".join(t["can"] for t in thieu) + ".",
                       goi=[t["goi"].split()[0] for t in thieu] + ["ckm.build"],
                       chi_tiet={"thieu": thieu})

        # TÍNH LẠI bất biến, không đọc kết quả của lần chiếu trước. `vi_pham_cay()` trả về
        # giá trị đã ghi nhớ; nếu đồ thị bị đổi bằng đường khác kể từ lần chiếu đó thì nó
        # đang nói về một cái cây không còn tồn tại. Một phép chặn đứng trước bước tốn kém
        # nhất phải được TÍNH, không được nhớ.
        vi_pham = [v.to_dict() for v in
                   KC.kiem_bat_bien(cay, chan_theo_fact=K.chan_theo_fact(ctx.store, cay))]
        if vi_pham:
            return ToolResult(False, error=EideError(
                "E8005",
                "Cây khối đang vi phạm bất biến, nên sơ đồ sinh ra sẽ là một mạch KHÁC mạch "
                "anh vẽ: " + "; ".join(f"{v['ma']} {v['vi']}" for v in vi_pham[:3]),
                hint_for_agent="Sửa các vi phạm rồi gọi ckm.build để kiểm lại. Đừng sinh sơ "
                               "đồ từ một cây lệch.",
                alternatives=["ckm.graph", "ckm.build"],
                details={"vi_pham": vi_pham}, blame="agent"))

        # Ký hiệu: có `sch.symbols` chạy trước thì dùng, chưa có thì soạn vẫn chạy nhưng tệp
        # mang lib='?' và cảnh báo — thà có một tệp nói rõ nó chưa chạy được.
        sm = ctx.store.get(MA_SYMBOL)
        sym = (sm["canonical"].get("anh_xa") or {}) if sm else {}
        thieu_pinout = KH.anh_xa(cay)[1]
        if thieu_pinout:
            return ToolResult(False, error=EideError(
                "E8002",
                "Chưa có pinout đã duyệt cho " + ", ".join(sorted(thieu_pinout))
                + " — không bịa chân.",
                hint_for_agent=("Nạp datasheet (doc.load → fact.extract → fact.review) rồi "
                                "ckm.chip_add; hoặc nếu người dùng đọc datasheet và nói cho "
                                "bạn, ghi bằng fact.assert_human."),
                alternatives=["doc.load", "fact.extract", "fact.assert_human", "ask_user"],
                details={"thieu_pinout": sorted(thieu_pinout)}, blame="agent"))

        ng, canh_bao = soan.soan_skidl(cay, style=style, symbol=sym)
        if not ng:
            return _r3(ctx, "Không soạn được tệp SKiDL: " + "; ".join(canh_bao),
                       goi=["ckm.build"])

        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[TEP_SKIDL],
            summary=f"soạn tệp SKiDL từ cây khối ({style})", explain=explain,
            noi_dung_truoc=_noi_dung_cu(ctx, TEP_SKIDL), run_id=ctx.run_id)
        _ghi(ctx, TEP_SKIDL, ng)
        ctx.store.apply(artefact_id=MA_SKIDL, type="skidl_src",
                        op="update" if ctx.store.get(MA_SKIDL) else "create",
                        author=f"agent:{ctx.run_id}",
                        canonical={"tep": TEP_SKIDL, "style": style,
                                   "so_ham": ng.count("def "), "canh_bao": canh_bao},
                        explain=explain,
                        view_hint={"kind": "code", "lang": "python", "path": TEP_SKIDL})
        return {"tep": TEP_SKIDL, "style": style, "so_ham": ng.count("def "),
                "so_dong": len(ng.splitlines()), "changeset": cs.id,
                "canh_bao": canh_bao,
                "note_vi": (f"Đã soạn {TEP_SKIDL}: {ng.count('def ')} hàm (mỗi khối một "
                            "hàm, Port là tham số)."
                            + (" Cảnh báo: " + "; ".join(canh_bao[:3]) if canh_bao else "")
                            + " Bước tiếp: sch.netlist để sinh netlist và KIỂM nó khớp bản "
                              "đồ mạch.")}

    # ====================================================================== 2. netlist
    @r.tool("sch.netlist", "Thiết kế",
            "Sinh netlist KiCad (.net) từ tệp SKiDL, và KIỂM nó khớp bản đồ mạch. Lệch thì "
            "dừng kèm diff — một net không có trong bản đồ nghĩa là mạch sắp vẽ có một đường "
            "dây không ai quyết.",
            {"type": "object",
             "properties": {"explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["netlist_kicad"],
            requires=[Requirement("skidl_src", 1, how_to_get="sch.compose",
                                  label_vi="tệp SKiDL (sch.compose)")],
            keywords=["netlist", "kicad", ".net", "đẳng cấu", "erc"])
    def netlist(ctx: Any, explain: dict[str, Any]):
        from ..sch import doc_skidl, so_dang_cau, viet_net

        a = ctx.store.get(MA_SKIDL)
        if a is None:
            return ToolResult(False, error=EideError(
                "E2001", "Chưa có tệp SKiDL nào.",
                hint_for_agent="Gọi sch.compose trước.",
                alternatives=["sch.compose"], blame="agent"))
        p = _duong(ctx, a["canonical"].get("tep") or TEP_SKIDL)
        if not p.exists():
            return _r3(ctx, f"Tệp {p.name} không còn trên đĩa.", goi=["sch.compose"])

        m = doc_skidl(p.read_text("utf-8", errors="replace"))
        if m.loi_cu_phap:
            return ToolResult(False, error=EideError(
                "E8001", f"Tệp SKiDL có lỗi cú pháp ({m.loi_cu_phap}) — không đọc được để "
                         "kiểm, nên KHÔNG đi tiếp.",
                hint_for_agent="Sinh lại bằng sch.compose. Nếu người dùng đã sửa tay tệp "
                               "này thì nói cho họ biết chỗ lỗi.",
                alternatives=["sch.compose"], blame="agent"))

        cay = KC.Cay.doc(ctx.store)
        phang = KC.flatten(cay)
        kq = so_dang_cau(phang, m.net)
        if not kq.dat:
            # SCH-44 bước 2: "lệch → lỗi kèm diff, không đi tiếp". Đây là ca SCH14.
            return ToolResult(False, error=EideError(
                "E8001", kq.vi,
                hint_for_agent=("Netlist từ tệp SKiDL KHÔNG khớp bản đồ mạch. Đừng sửa tệp "
                                "cho khớp — sửa BẢN ĐỒ nếu mạch thật khác, hoặc sinh lại tệp "
                                "bằng sch.compose nếu tệp bị sửa tay."),
                alternatives=["sch.compose", "ckm.graph", "ask_user"],
                details=kq.to_dict(), blame="agent"))

        noi_dung = viet_net(phang, part=m.part, ten_mach=ctx.eide_md.project_name
                            if hasattr(ctx.eide_md, "project_name") else "eide")
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[TEP_NET],
            summary="sinh netlist KiCad từ tệp SKiDL", explain=explain,
            noi_dung_truoc=_noi_dung_cu(ctx, TEP_NET), run_id=ctx.run_id)
        _ghi(ctx, TEP_NET, noi_dung)
        ctx.store.apply(artefact_id=MA_NETLIST_KICAD, type="netlist_kicad",
                        op="update" if ctx.store.get(MA_NETLIST_KICAD) else "create",
                        author=f"agent:{ctx.run_id}",
                        canonical={"tep": TEP_NET, "so_net": len(phang),
                                   "so_linh_kien": len(m.part),
                                   "dang_cau": kq.to_dict(),
                                   "khong_hieu": m.khong_hieu},
                        explain=explain,
                        view_hint={"kind": "code", "lang": "lisp", "path": TEP_NET})

        # ERC nội bộ: dùng lại `board.check` thay vì viết luật lần hai.
        from ..knowledge import erc as ERC
        ph = ERC.erc(ctx.store)
        nang = [x for x in ph if x.ket_luan == "khong_dat"]
        return {"tep": TEP_NET, "so_net": len(phang), "so_linh_kien": len(m.part),
                "dang_cau": kq.to_dict(), "khong_hieu": m.khong_hieu,
                "erc_loi_chan": [x.to_dict() for x in nang], "changeset": cs.id,
                "note_vi": (f"Netlist {len(phang)} net khớp bản đồ mạch — kiểm bằng cách "
                            "ĐỌC LẠI tệp SKiDL rồi so với cây, không phải so cây với chính "
                            "nó."
                            + (f" Có {len(m.khong_hieu)} dòng trong tệp không đọc được: "
                               + "; ".join(m.khong_hieu[:2]) + " — nói cho người dùng biết."
                               if m.khong_hieu else "")
                            + (f" ERC còn {len(nang)} lỗi chặn, xem board.check."
                               if nang else ""))}

    # ====================================================================== 3. ký hiệu
    @r.tool("sch.symbols", "Thiết kế",
            "Chọn ký hiệu cho từng linh kiện: thư viện chính thức nếu có và KHỚP Fact pinout, "
            "không thì sinh ký hiệu từ Fact. Ký hiệu sinh ra ghi rõ nó lấy chân từ đâu.",
            {"type": "object",
             "properties": {
                 "uu_tien": {"type": "string", "enum": ["official", "generated"],
                             "description": "official = thử thư viện chính thức trước"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["symbol_map"],
            keywords=["ký hiệu", "symbol", "kicad_sym", "thư viện"])
    def symbols(ctx: Any, explain: dict[str, Any], uu_tien: str = "official"):
        from ..sch import kyhieu as KH

        cay = KC.Cay.doc(ctx.store)
        if not cay.goc:
            return _r3(ctx, "Chưa có cây khối nào.", goi=["ckm.module_set"])

        tv = _thu_vien_da_tai(ctx) if uu_tien == "official" else {}
        ds, thieu = KH.anh_xa(cay, thu_vien=tv, nguon_fact=_nguon_fact(ctx, cay))
        if thieu:
            return ToolResult(False, error=EideError(
                "E8002",
                "Chưa có pinout đã duyệt cho " + ", ".join(sorted(thieu))
                + " — không bịa chân.",
                hint_for_agent="Nạp datasheet rồi ckm.chip_add, hoặc fact.assert_human nếu "
                               "người dùng đọc datasheet và nói cho bạn.",
                alternatives=["doc.load", "fact.extract", "fact.assert_human"],
                details={"thieu_pinout": sorted(thieu)}, blame="agent"))

        sinh = [k for k in ds.values() if k.sinh_tu_fact]
        noi_dung = KH.viet_kicad_sym(ds)
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[TEP_SYM],
            summary=f"ký hiệu cho {len(ds)} linh kiện ({len(sinh)} sinh từ Fact)",
            explain=explain, noi_dung_truoc=_noi_dung_cu(ctx, TEP_SYM), run_id=ctx.run_id)
        _ghi(ctx, TEP_SYM, noi_dung)
        ctx.store.apply(artefact_id=MA_SYMBOL, type="symbol_map",
                        op="update" if ctx.store.get(MA_SYMBOL) else "create",
                        author=f"agent:{ctx.run_id}",
                        canonical={"tep": TEP_SYM,
                                   "anh_xa": {k: {"lib": v.lib or "eide-sinh",
                                                  "ten": v.ten} for k, v in ds.items()},
                                   "chi_tiet": [v.to_dict() for v in ds.values()]},
                        explain=explain)
        cb = [f"{k.ref}: {k.canh_bao}" for k in ds.values() if k.canh_bao]
        return {"tep": TEP_SYM, "so_ky_hieu": len(ds), "so_sinh_tu_fact": len(sinh),
                "changeset": cs.id, "canh_bao": cb,
                "note_vi": (f"{len(ds)} ký hiệu, {len(sinh)} sinh từ Fact pinout."
                            + (" Chưa có thư viện KiCad chính thức nào tải về, nên ký hiệu "
                               "sinh từ Fact — mỗi ký hiệu ghi rõ nó lấy chân từ đâu."
                               if not tv else "")
                            + (" " + "; ".join(cb[:3]) if cb else ""))}

    # ====================================================================== 4. bố cục
    @r.tool("sch.place", "Thiết kế",
            "Tính bố cục sơ đồ: vùng cho từng khối theo luồng tín hiệu, vị trí từng ký hiệu, "
            "nhãn net. MÃ tính toạ độ — bạn chỉ chọn khổ giấy. Tiêu chí nghiệm thu đo bằng "
            "SỐ (không ký hiệu nào chồng nhau, không dây cắt thân, ≤ 70 % net dùng nhãn).",
            {"type": "object",
             "properties": {
                 "kho": {"type": "string", "enum": ["A4", "A3"],
                         "description": "Chật thì mã tự nới vùng, rồi tự đổi lên A3"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["layout"],
            keywords=["bố cục", "place", "toạ độ", "xếp", "layout"])
    def place(ctx: Any, explain: dict[str, Any], kho: str = "A4"):
        from ..sch import bo_cuc as BC

        if ctx.store.get(MA_NETLIST_KICAD) is None:
            return ToolResult(False, error=EideError(
                "E2001", "Chưa có netlist đã kiểm. Bố cục dựng trên netlist, nên phải kiểm "
                         "nó khớp bản đồ trước — nếu không thì ta xếp đẹp một mạch sai.",
                hint_for_agent="Gọi sch.netlist trước.",
                alternatives=["sch.compose", "sch.netlist"], blame="agent"))

        cay = KC.Cay.doc(ctx.store)
        phang = KC.flatten(cay)
        bc = BC.tinh_bo_cuc(cay, phang, kho=kho)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=MA_BO_CUC, type="layout",
            op="update" if ctx.store.get(MA_BO_CUC) else "create",
            canonical=bc.to_dict(), explain=explain, run_id=ctx.run_id)
        tc = bc.tieu_chi
        return {"kho": bc.kho, "so_ky_hieu": tc["so_ky_hieu"], "so_vung": tc["so_vung"],
                "so_nhan": tc["so_nhan"], "so_day": tc["so_day"],
                "tieu_chi": tc, "so_lan_noi": bc.so_lan_noi, "canh_bao": bc.canh_bao,
                "changeset": cs.id,
                "note_vi": (f"Bố cục {tc['so_ky_hieu']} ký hiệu trong {tc['so_vung']} vùng "
                            f"trên khổ {bc.kho}"
                            + (f", nới vùng {bc.so_lan_noi} lần" if bc.so_lan_noi else "")
                            + (". Tiêu chí ĐẠT." if tc["dat"] else
                               ". Tiêu chí CHƯA đạt: " + "; ".join(tc["vi_pham"][:3]) + ".")
                            + (f" {tc['ty_le_net_dung_nhan']:.0%} net dùng nhãn"
                               " — bản này chưa đi dây giữa các khối, nên tỉ lệ nhãn cao là"
                               " điều chờ đợi." if tc["so_nhan"] else ""))}

    # ====================================================================== 5. ghi
    @r.tool("sch.write", "Thiết kế",
            "Ghi tệp .kicad_sch (+ .kicad_pro) từ bố cục. uuid sinh theo ref nên lần sinh lại "
            "KHÔNG làm mất thứ người dùng đã sửa trong KiCad. Ghi xong đọc lại bằng chính "
            "thư viện để chắc tệp mở được.",
            {"type": "object",
             "properties": {
                 "ten_sheet": {"type": "string"},
                 "style": {"type": "string", "enum": ["auto", "hierarchical", "flat"],
                           "description": "auto (mặc định) = có khối thì phân cấp, mạch một "
                                          "tầng thì một trang. hierarchical = mỗi khối một "
                                          "sheet (giữ được CÂY khi người mở trong KiCad); "
                                          "flat = một trang. Cây sâu hơn 4 cấp thì tự chuyển "
                                          "sang hierarchical."},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["code"],
            keywords=["ghi", "kicad_sch", "write", "xuất tệp"])
    def write(ctx: Any, explain: dict[str, Any], ten_sheet: str = "mach",
              style: str = "auto"):
        from ..knowledge.cay import SAU_KHUYEN_NGHI
        from ..sch import ghi as G
        from ..sch import phan_cap as PC

        cay = KC.Cay.doc(ctx.store)
        sau, sau_o = cay.sau_nhat()
        co_khoi = bool(cay.khoi_con(cay.goc)) if cay.goc else False
        if style == "auto":
            # Hình tệp đi theo hình thiết kế: có khối thì phân cấp (một sheet mỗi khối), mạch
            # một tầng thì một trang. Mặc định cứng "hierarchical" từng làm sheet gốc của mạch
            # phẳng rỗng không, còn mặc định cứng "flat" thì mọi mạch có khối đều mất cây khi
            # mở trong KiCad.
            style = "hierarchical" if co_khoi else "flat"
        if style == "flat" and sau > SAU_KHUYEN_NGHI:
            # HIER-45 §7: "depth > 4 → tự chuyển sang hierarchical và cảnh báo". Không hỏi
            # lại: một cây sâu thế này trên một trang là một trang không ai đọc được, và đó
            # là lý do kỹ thuật chứ không phải khẩu vị.
            style = "hierarchical"

        if style == "hierarchical" and cay.goc:
            return _ghi_phan_cap(ctx, cay, explain, ten_sheet=ten_sheet,
                                 tu_chuyen=(sau > SAU_KHUYEN_NGHI), sau=sau, sau_o=sau_o)

        a = ctx.store.get(MA_BO_CUC)
        if a is None:
            return ToolResult(False, error=EideError(
                "E2001", "Chưa có bố cục nào để ghi.",
                hint_for_agent="Gọi sch.place trước.",
                alternatives=["sch.place"], blame="agent"))
        bc = _bo_cuc_tu(a["canonical"])
        sm = ctx.store.get(MA_SYMBOL)
        sym = (sm["canonical"].get("anh_xa") or {}) if sm else {}

        noi_dung = G.viet_kicad_sch(bc, symbol=sym, ten_sheet=ten_sheet)
        ok, vi = G.doc_lai_duoc(noi_dung)
        if not ok:
            # §3 bước 5 đòi "kiutils parse lại được (round-trip ổn định)". Không đạt thì
            # KHÔNG ghi: một tệp không mở lại được là một tệp làm mất công người dùng.
            return ToolResult(False, error=EideError(
                "E8001", f"Tệp .kicad_sch sinh ra không qua được phép kiểm round-trip: {vi}",
                hint_for_agent="Đừng ghi tệp này. Báo cho người dùng và thử lại sau khi "
                               "sửa bố cục, hoặc nói rõ là chưa sinh được (mức R3).",
                alternatives=["sch.place", "diagram.render"], blame="system"))

        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[TEP_SCH, TEP_PRO],
            summary=f"ghi sơ đồ KiCad ({len(bc.o)} ký hiệu)", explain=explain,
            noi_dung_truoc={**_noi_dung_cu(ctx, TEP_SCH), **_noi_dung_cu(ctx, TEP_PRO)},
            run_id=ctx.run_id)
        _ghi(ctx, TEP_SCH, noi_dung)
        _ghi(ctx, TEP_PRO, G.kicad_pro(ten_sheet))
        mat_cay = ("" if not co_khoi else
                   f" Mạch này có {len(cay.khoi_con(cay.goc))} khối nhưng ghi ở dạng MỘT "
                   "trang, nên cây khối KHÔNG còn trong tệp: mở trong KiCad sẽ thấy một "
                   "trang phẳng. Muốn giữ cây thì ghi lại với style=hierarchical.")
        return {"tep": [TEP_SCH, TEP_PRO], "so_ky_hieu": len(bc.o), "style": "flat",
                "round_trip": True, "changeset": cs.id, "mat_cay": bool(co_khoi),
                "uuid_mau": {z.ref: G.uuid_theo(f"sym:{z.ref}") for z in bc.o[:3]},
                "note_vi": (mat_cay + f" Đã ghi {TEP_SCH} ({len(bc.o)} ký hiệu) và đọc lại được khớp "
                            "từng ký tự. uuid sinh theo ref, nên sinh lại KHÔNG làm mất bố "
                            "cục người dùng đã sửa trong KiCad. Máy này không cài KiCad — "
                            "muốn mở bằng KiCad thì xuất gói rồi mở ở máy khác.")}

    # ====================================================================== 6. render
    @r.tool("sch.render", "Thiết kế",
            "Vẽ sơ đồ thành ảnh SVG bằng bộ vẽ nội bộ (máy không cài KiCad). Kiểm luôn ba "
            "điều: ảnh có ký hiệu, số ký hiệu khớp số ref, và chữ không đè nhau.",
            {"type": "object",
             "properties": {"explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R1", feature="schematic", writes_artefact=True, needs_explain=True,
            produces=["report"],
            keywords=["vẽ", "render", "svg", "hình", "xem sơ đồ"])
    def render(ctx: Any, explain: dict[str, Any]):
        from ..sch import ve_svg

        d = _duong(ctx, "sch")
        ds = sorted(d.glob("*.kicad_sch")) if d.exists() else []
        if not ds:
            return _r3(ctx, f"Chưa có {TEP_SCH} để vẽ.", goi=["sch.place", "sch.write"])
        a = ctx.store.get(MA_BO_CUC)
        hop = {z["ref"]: (z["rong"], z["cao"])
               for z in ((a["canonical"].get("o") or []) if a else [])}

        # Vẽ MỌI sheet, không chỉ sheet gốc. Với mạch phân cấp, gốc chỉ có hộp sheet — vẽ một
        # mình nó ra một ảnh không có linh kiện nào, và người mở ra tưởng render hỏng.
        tep_svg: list[str] = []
        tong = {"so_ky_hieu": 0, "so_nhan": 0, "so_day": 0, "so_sheet": 0}
        ref: list[str] = []
        de_nhau: list[str] = []
        canh_bao: list[str] = []
        for p in ds:
            kq = ve_svg.ve(p.read_text("utf-8", errors="replace"), hop=hop)
            ten_svg = f"sch/{p.stem}.svg"
            _ghi(ctx, ten_svg, kq.svg)
            tep_svg.append(ten_svg)
            for k in tong:
                tong[k] += getattr(kq, k)
            ref += kq.ref_trong_svg
            de_nhau += [f"{p.name}: {x}" for x in kq.chu_de_nhau]
            canh_bao += [f"{p.name}: {x}" for x in kq.canh_bao]

        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=tep_svg,
            summary=f"render {len(tep_svg)} sheet ra SVG",
            explain=explain, run_id=ctx.run_id)
        canon = {**tong, "tep": tep_svg, "ref_trong_svg": sorted(ref),
                 "chu_de_nhau": de_nhau, "canh_bao": canh_bao}
        ctx.store.apply(artefact_id="report:sch-render", type="report", op="update"
                        if ctx.store.get("report:sch-render") else "create",
                        author=f"agent:{ctx.run_id}", canonical=canon, explain=explain,
                        view_hint={"kind": "svg", "path": tep_svg[0]})
        return {**canon, "changeset": cs.id,
                "note_vi": (f"Đã vẽ {len(tep_svg)} sheet: {tong['so_ky_hieu']} ký hiệu, "
                            f"{tong['so_nhan']} nhãn, {tong['so_sheet']} hộp sheet con."
                            + (" " + " ".join(canh_bao[:3]) if canh_bao else
                               " Chữ không đè nhau, không ảnh nào rỗng."))}

    # ====================================================================== 7. xuất gói
    @r.tool("sch.export", "Thiết kế",
            "Xuất gói sơ đồ (.kicad_sch + .kicad_sym + .net + SVG + .kicad_pro) vào một thư "
            "mục để người mở ở máy KHÁC đã có KiCad. Máy này không cài KiCad.",
            {"type": "object",
             "properties": {"explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["report"],
            keywords=["xuất", "export", "gói", "gửi", "mở ở máy khác"])
    def export(ctx: Any, explain: dict[str, Any]):
        import shutil

        goc = _duong(ctx, "sch")
        dich = _duong(ctx, THU_MUC_GOI)
        if not goc.exists():
            return _r3(ctx, "Chưa có tệp sơ đồ nào để xuất.",
                       goi=["sch.place", "sch.write"])
        dich.mkdir(parents=True, exist_ok=True)
        da: list[str] = []
        for p in sorted(goc.iterdir()):
            if p.is_file() and p.suffix in (".kicad_sch", ".kicad_sym", ".kicad_pro",
                                            ".net", ".svg"):
                shutil.copy2(p, dich / p.name)
                da.append(p.name)
        if not da:
            return _r3(ctx, "Thư mục sch/ không có tệp nào xuất được.",
                       goi=["sch.write", "sch.render"])

        doc = _doc_me(ctx, da)
        (dich / "DOC-TRUOC-KHI-MO.md").write_text(doc, "utf-8")
        da.append("DOC-TRUOC-KHI-MO.md")
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}",
            paths=[f"{THU_MUC_GOI}/{x}" for x in da],
            summary=f"xuất gói sơ đồ ({len(da)} tệp)", explain=explain, run_id=ctx.run_id)
        ctx.store.apply(artefact_id="report:sch-export", type="report",
                        op="update" if ctx.store.get("report:sch-export") else "create",
                        author=f"agent:{ctx.run_id}",
                        canonical={"thu_muc": THU_MUC_GOI, "tep": da}, explain=explain)
        return {"thu_muc": THU_MUC_GOI, "tep": da, "changeset": cs.id,
                "note_vi": (f"Đã xuất {len(da)} tệp vào {THU_MUC_GOI}/. Mở `mach.kicad_sch` "
                            "ở máy đã có KiCad 8 hoặc 9. Máy này không cài KiCad, nên ảnh "
                            "SVG trong gói là do bộ vẽ nội bộ của EIDE — nó đọc được nhưng "
                            "không cam kết giống KiCad từng nét.")}

    # ====================================================================== 8. nạp lại
    @r.tool("sch.import", "Thiết kế",
            "Nạp lại sơ đồ người dùng đã sửa trong KiCad. So với bản đồ mạch rồi phân loại: "
            "chỉ bố cục · đổi giá trị linh kiện · đổi CẤU TRÚC. Cấu trúc đổi thì HỎI, không "
            "bao giờ tự ghi đè bản đồ.",
            {"type": "object",
             "properties": {
                 "thu_muc": {"type": "string",
                             "description": "Thư mục chứa .kicad_sch (mặc định sch/)"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", feature="schematic", core=False, writes_artefact=True,
            needs_explain=True, produces=["report"],
            keywords=["nạp lại", "import", "round-trip", "người sửa", "kicad"])
    def sch_import(ctx: Any, explain: dict[str, Any], thu_muc: str = "sch"):
        from ..sch import nap_lai as NL
        from ..sch import phan_cap as PC

        d = _duong(ctx, thu_muc)
        tep = {p.name: p.read_text("utf-8", errors="replace")
               for p in sorted(d.glob("*.kicad_sch"))} if d.exists() else {}
        if not tep:
            return _r3(ctx, f"Không có tệp .kicad_sch nào trong {thu_muc}/.",
                       goi=["sch.write"])

        doc = PC.doc_phan_cap(tep)
        cay = KC.Cay.doc(ctx.store)
        so = PC.so_cay(doc, cay)
        sm = ctx.store.get(MA_SYMBOL)
        gia_tri_kho = PC.gia_tri_mong_doi(
            cay, (sm["canonical"].get("anh_xa") or {}) if sm else {})
        kq = NL.phan_loai(doc=doc, cay=cay, so=so, gia_tri_kho=gia_tri_kho)

        # Changeset của NGƯỜI: thay đổi này do họ làm trong KiCad, không do tác tử.
        cs = ctx.history.ghi_kho(
            author="human", artefact_id="report:sch-import", type="report",
            op="update" if ctx.store.get("report:sch-import") else "create",
            canonical={"thu_muc": thu_muc, "so_tep": len(tep), "so_cay": so,
                       **kq.to_dict()},
            explain=explain, run_id=ctx.run_id,
            # Chỉ bố cục thì KHÔNG đánh STALE (§7 mục 3a): mỗi lần người sắp lại trang mà cả
            # chuỗi hạ nguồn sáng đèn thì họ học được rằng băng cảnh báo vô nghĩa.
            gay_stale=bool(kq.theo_loai["gia_tri"] or kq.theo_loai["cau_truc"]))

        the = NL.the_hoi(kq)
        if the:
            ctx.pending_cards.append({"loai": "clarify", "nguon": "sch.import", **the})
            ctx.emit(uic.notice(
                f"Sơ đồ có {len(kq.theo_loai['cau_truc'])} thay đổi cấu trúc — cần anh quyết.",
                level="warn", code="SCH-13"))
        return {"so_tep": len(tep), "so_cay": so, **kq.to_dict(),
                "the_hoi": the, "changeset": cs.id,
                "note_vi": (kq.cau_vi()
                            + (" EIDE KHÔNG tự chọn: hai lựa chọn dẫn tới hai mạch khác "
                               "nhau. Hỏi người dùng bằng thẻ vừa tạo." if the else "")
                            + (" " + " ".join(kq.canh_bao) if kq.canh_bao else ""))}

    return r


def _doc_me(ctx: Any, tep: list[str]) -> str:
    """Tệp hướng dẫn trong gói. Nói rõ hai điều người nhận cần biết ngay."""
    return (
        "# Gói sơ đồ do EIDE sinh\n\n"
        f"Tệp trong gói: {', '.join(sorted(tep))}.\n\n"
        "## Mở thế nào\n\n"
        "Mở `mach.kicad_sch` bằng KiCad 8 hoặc 9 trên một máy ĐÃ CÓ KiCad. Máy sinh ra gói "
        "này không cài KiCad — đó là một quyết định của dự án, không phải một thiếu sót.\n\n"
        "## Hai điều cần biết\n\n"
        "1. **Ảnh SVG là do bộ vẽ nội bộ của EIDE.** Nó đọc được và đúng về chân/nhãn, nhưng "
        "không cam kết giống KiCad từng nét.\n"
        "2. **Sửa trong KiCad thì nạp lại bằng `sch.import`.** EIDE sẽ phân loại thay đổi của "
        "anh: chỉ bố cục · đổi giá trị · đổi cấu trúc. Riêng cấu trúc thì nó HỎI trước khi "
        "chạm vào bản đồ mạch.\n")


def _ghi_phan_cap(ctx: Any, cay: Any, explain: dict[str, Any], *, ten_sheet: str,
                  tu_chuyen: bool, sau: int, sau_o: str) -> Any:
    """Ghi gói sheet phân cấp — HIER-45 §7, mỗi khối một tệp."""
    from ..sch import ghi as G
    from ..sch import phan_cap as PC

    sm = ctx.store.get(MA_SYMBOL)
    sym = (sm["canonical"].get("anh_xa") or {}) if sm else {}
    a = ctx.store.get(MA_BO_CUC)
    kho = (a["canonical"].get("kho") if a else "A4") or "A4"

    goi = PC.viet_phan_cap(cay, symbol=sym, kho=kho)
    if not goi.tep:
        return _r3(ctx, "Không ghi được sheet phân cấp: " + "; ".join(goi.canh_bao),
                   goi=["ckm.module_set", "ckm.build"])
    for ten, nd in sorted(goi.tep.items()):
        ok, vi = G.doc_lai_duoc(nd)
        if not ok:
            return ToolResult(False, error=EideError(
                "E8001", f"Sheet {ten} không qua được phép kiểm round-trip: {vi}",
                hint_for_agent="Đừng ghi gói này. Báo cho người dùng và thử style=flat.",
                alternatives=["sch.write", "diagram.render"], blame="system"))

    paths = [f"sch/{t}" for t in sorted(goi.tep)] + [TEP_PRO]
    cu = {}
    for t in paths:
        cu.update(_noi_dung_cu(ctx, t))
    cs = ctx.history.ghi_tep(
        author=f"agent:{ctx.run_id}", paths=paths,
        summary=f"ghi sơ đồ KiCad phân cấp ({goi.so_sheet} sheet)", explain=explain,
        noi_dung_truoc=cu, run_id=ctx.run_id)
    for t, nd in sorted(goi.tep.items()):
        _ghi(ctx, f"sch/{t}", nd)
    _ghi(ctx, TEP_PRO, G.kicad_pro(ten_sheet))

    # Kiểm ngay: đọc lại gói vừa ghi và so cây. HIER13 đòi "nạp lại dựng lại đúng cây".
    doc = PC.doc_phan_cap(goi.tep)
    so = PC.so_cay(doc, cay)
    return {"tep": paths, "style": "hierarchical", "so_sheet": goi.so_sheet,
            "round_trip": True, "doc_lai_dung_cay": so["khop"], "so_cay": so,
            "changeset": cs.id, "canh_bao": goi.canh_bao,
            "note_vi": (f"Đã ghi {goi.so_sheet} sheet phân cấp — mỗi khối một tệp, Port của "
                        "khối thành sheet pin. "
                        + (f"Cây sâu {sau} cấp ({sau_o}) nên TỰ chuyển sang phân cấp: một "
                           "cây sâu thế này trên một trang là một trang không ai đọc được. "
                           if tu_chuyen else "")
                        + ("Đọc lại gói dựng đúng cây." if so["khop"] else
                           "CẢNH BÁO: đọc lại gói KHÔNG dựng đúng cây — "
                           + str(so)[:200]))}


def _bo_cuc_tu(canon: dict[str, Any]):
    """Dựng lại `BoCuc` từ hiện vật. Bố cục là hiện vật, nên `sch.write` đọc từ kho chứ
    không tính lại — hai lần tính là hai cơ hội ra hai kết quả."""
    from ..sch import bo_cuc as BC

    bc = BC.BoCuc(kho=canon.get("kho", "A4"),
                  day=list(canon.get("day") or []),
                  nhan=list(canon.get("nhan") or []),
                  tieu_chi=dict(canon.get("tieu_chi") or {}),
                  canh_bao=list(canon.get("canh_bao") or []),
                  so_lan_noi=int(canon.get("so_lan_noi") or 0))
    bc.vung = [BC.Vung(**v) for v in (canon.get("vung") or [])]
    bc.o = [BC.O(**z) for z in (canon.get("o") or [])]
    return bc


# --------------------------------------------------------------------------- phụ trợ
def _r3(ctx: Any, vi: str, *, goi: list[str],
        chi_tiet: dict[str, Any] | None = None) -> ToolResult:
    """Suy giảm R3 (§6): không sinh được thì NÓI THẲNG và trả về thứ đang có.

    Không ném lỗi hệ thống và không trả một tệp nửa vời: §6 nói mức R3 là *"sơ đồ khối + đồ
    thị net hiện có của CKM (không đổi) — như hiện nay, hệ thống cũ không bị ảnh hưởng"*.
    """
    return ToolResult(False, error=EideError(
        "E8005", vi + " Vẫn dùng được sơ đồ khối và đồ thị net đang có (mức R3).",
        hint_for_agent="Nói cho người dùng biết sơ đồ nguyên lý chưa sinh được và vì sao; "
                       "sơ đồ khối trên tab Thiết kế vẫn đúng. Cần: " + ", ".join(goi),
        alternatives=goi + ["diagram.render", "ckm.graph"],
        details=chi_tiet or {}, blame="agent"))


def _dem(ctx: Any) -> dict[str, int]:
    dem = dict(ctx.store.ckm_dem())
    dem["chip_co_ho_chieu"] = sum(
        1 for c in ctx.store.ckm_cac_nut(loai="chip") if c["canonical"].get("ho_chieu"))
    return dem


def _duong(ctx: Any, rel: str):
    from pathlib import Path
    return Path(ctx.config.paths.project_root) / rel


def _ghi(ctx: Any, rel: str, noi_dung: str) -> None:
    p = _duong(ctx, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(noi_dung, "utf-8")


def _noi_dung_cu(ctx: Any, rel: str) -> dict[str, str]:
    """Nội dung trước khi ghi — để changeset hoàn tác được (N9) khi không có git."""
    p = _duong(ctx, rel)
    return {rel: p.read_text("utf-8", errors="replace")} if p.exists() else {}


def _thu_vien_da_tai(ctx: Any) -> dict[str, dict[str, Any]]:
    """Thư viện ký hiệu KiCad đã tải về như DỮ LIỆU (§5). Chưa có thì rỗng.

    Trả rỗng là câu trả lời đúng, không phải một lỗi: §5 nói thư viện chính thức được tải qua
    G-DATA và cache ở M4. Chưa tải thì ký hiệu sinh từ Fact, và điều đó được nói ra.
    """
    a = ctx.store.get("symbol_lib:kicad")
    return (a["canonical"].get("ky_hieu") or {}) if a else {}


def _nguon_fact(ctx: Any, cay: Any) -> dict[str, str]:
    """Câu "DS rev X p.Y" cho từng ref — N1 áp vào ký hiệu (§5)."""
    import json

    ra: dict[str, str] = {}
    for nid, n in cay.nut.items():
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        ten = n["canonical"].get("ten") or n["ten"]
        for f in ctx.store.query_facts(subject=f"pin:{ten}.", limit=5):
            s = f.get("source")
            if isinstance(s, str):
                try:
                    s = json.loads(s)
                except ValueError:
                    s = {}
            if isinstance(s, dict) and s.get("doc_id"):
                ra[ref] = (f"{s['doc_id']}"
                           + (f" trang {s['page']}" if s.get("page") else ""))
                break
    return ra
