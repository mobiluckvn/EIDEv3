# -*- coding: utf-8 -*-
"""Công cụ THIẾT KẾ GIAO DIỆN cho màn hình của bo — năm công cụ, một đường đi.

    display.profile ──► screen.set ──► screen.check ──► screen.render ──► screen.codegen
     (hồ sơ panel)      (bản thiết kế)   (chạy được?)      (xem 1:1)      (tệp C BSP_LCD_*)

Thứ tự ấy **bắt buộc theo dữ liệu**, không theo một planner: mỗi công cụ tự kiểm tiền đề của
mình và khi thiếu thì trả một lỗi NÓI RÕ phải gọi gì trước. Mô hình đi sai thứ tự nhận một câu
chỉ đường, không phải một sự cố — cùng kỷ luật với `tools/ckm.py`.

## Vì sao `display.profile` phải đi trước, và không có đường tắt

`grep` cả kho ngày 10/10/2026 không ra một Fact nào về màn hình. Nếu `screen.set` nhận một
độ phân giải do mô hình tự điền thì tác tử sẽ **tự nhớ ra** `800×480` — và dự án này đã trả giá
ba lần cho đúng chuyện ấy. Nên `screen.set` **không có tham số độ phân giải**: nó lấy từ hồ
sơ. Một bản thiết kế vẽ đúng đẹp trên độ phân giải sai thì mọi toạ độ trong nó đều sai, màn
hình thật cắt mất một phần, và không lỗi nào kêu lên.

## Vì sao tiền tố là `screen.` chứ không `ui.`

`ui.explain` và `ui.notice` đã tồn tại, và chúng nói về **giao diện của chính EIDE** — bề mặt,
thẻ cổng, thông báo. Màn hình trên bo là một chủ thể khác hẳn. Đặt `ui.render` cạnh `ui.explain`
là mời mô hình gọi sai công cụ, và nó sẽ gọi sai ở đúng lúc khó phát hiện nhất.

## Năm công cụ này KHÔNG có cờ, và vì sao

Tất cả `core=False`: chúng chỉ hiện ra sau `tool.search`, nên chúng không đổi lược đồ mỗi lượt
của những dự án không có màn hình. Và chúng không đổi hành vi của bất kỳ đường nào đang có —
`doc.load`, `build.compile`, `fact.*` chạy y nguyên. Theo N-4 thì chỗ cần cờ là chỗ đổi thứ mô
hình nhìn thấy **mỗi lượt**; thêm công cụ mới không phải chỗ ấy.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..errors import EideError
from ..knowledge import man_hinh as MH
from ..man_hinh import html as HT
from ..man_hinh import mo_hinh as MO
from ..man_hinh import sinh_c as SC
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

# Thư mục trong dự án để đặt bản render và tệp C. Đặt dưới `.eide/` vì chúng là thứ MÃ sinh ra,
# không phải thứ người viết — trộn chúng vào cây nguồn là cách một lần sinh lại ghi đè tay người.
THU_MUC_UI = Path(".eide") / "ui"


def _goc(ctx: Any) -> Path:
    return Path(ctx.config.paths.project_root)


def _ma_ho_so(ten: str) -> str:
    return f"display:{ten}"


def _ma_man_hinh(ten: str) -> str:
    return f"ui_screen:{ten}"


def _doc_ho_so(ctx: Any, ten: str) -> MH.HoSoManHinh:
    """Hồ sơ panel từ kho. Thiếu thì NÓI PHẢI GỌI GÌ, không dựng một hồ sơ rỗng."""
    a = ctx.store.get(_ma_ho_so(ten))
    if a is None:
        raise EideError(
            "E1110", f"Chưa có hồ sơ màn hình `{_ma_ho_so(ten)}` trong kho.",
            hint_for_agent=("Gọi `display.profile` trước, trên một tài liệu đã nạp có nói độ "
                            "phân giải và hệ màu của panel. Không có hồ sơ thì mọi toạ độ của "
                            "bản thiết kế là toạ độ trên một màn hình không ai biết."),
            alternatives=["display.profile", "doc.load"], blame="agent")
    d = dict(a.get("canonical") or {})
    d.pop("note_vi", None)
    d.pop("dem_khung", None)
    return MH.HoSoManHinh(
        rong=int(d.get("rong") or 0), cao=int(d.get("cao") or 0),
        he_mau=str(d.get("he_mau") or ""),
        inch=d.get("inch"), dpi=d.get("dpi"),
        dpi_la_tinh_ra=bool(d.get("dpi_la_tinh_ra")),
        driver=str(d.get("driver") or ""), bus=str(d.get("bus") or ""),
        cam_ung=d.get("cam_ung"), loai=str(d.get("loai") or "do_hoa"),
        cot=int(d.get("cot") or 0), dong=int(d.get("dong") or 0),
        he_mau_khac=list(d.get("he_mau_khac") or []),
        nguon=dict(d.get("nguon") or {}), thieu=list(d.get("thieu") or []),
        vi_sao_khong_hop_le=str(d.get("vi_sao_khong_hop_le") or ""))


def _doc_man_hinh(ctx: Any, ten: str) -> MO.ManHinh:
    a = ctx.store.get(_ma_man_hinh(ten))
    if a is None:
        raise EideError(
            "E1111", f"Chưa có bản thiết kế `{_ma_man_hinh(ten)}` trong kho.",
            hint_for_agent="Gọi `screen.set` trước để ghi bản thiết kế.",
            alternatives=["screen.set"], blame="agent")
    return MO.ManHinh.tu_dict(a.get("canonical") or {})


def _kq_dict(kq: MO.KetQuaKiem) -> dict[str, Any]:
    return {"loi": kq.loi, "canh_bao": kq.canh_bao, "chua_kiem": kq.chua_kiem,
            "so_loi": len(kq.loi), "so_canh_bao": len(kq.canh_bao)}


_S_PHAN_TU = {
    "type": "array",
    "description": "Các phần tử của màn hình. Toạ độ là PIXEL THẬT của panel.",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "mã riêng, dùng để tra trong bản render"},
            "loai": {"type": "string", "enum": list(MO.LOAI_PHAN_TU)},
            "x": {"type": "integer"}, "y": {"type": "integer"},
            "w": {"type": "integer"}, "h": {"type": "integer"},
            "chu": {"type": "string",
                    "description": ("CHỈ ASCII 0x20..0x7E — bảng font của BSP có đúng 95 ký "
                                    "tự ấy, và ký tự ngoài khoảng đó làm BSP đọc RA NGOÀI "
                                    "bảng font. Viết không dấu.")},
            "co_chu": {"type": "integer", "enum": sorted(MO.FONT_BSP)},
            "mau_chu": {"type": "string", "description": "#RRGGBB"},
            "mau_nen": {"type": "string", "description": "#RRGGBB; rỗng = trong suốt"},
            "can_le": {"type": "string", "enum": list(MO.CAN_LE)},
            "gia_tri": {"type": "number", "description": "cho `bar`: 0..100"},
            "nguon": {"type": "string", "description": "cho `image`: tên tệp BMP"}},
        "required": ["id", "loai", "x", "y", "w", "h"]},
}


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:

    # ================================================================== display.profile
    @r.tool("display.profile", "Tri thức",
            "Đọc CẤU HÌNH MÀN HÌNH THẬT từ một tài liệu đã nạp: độ phân giải, hệ màu, đường "
            "chéo, driver, bus, cảm ứng. Mỗi trường mang trích dẫn nguyên văn; trường tài "
            "liệu không nói thì để TRỐNG, không điền mặc định.",
            {"type": "object",
             "properties": {
                 "doc_id": {"type": "string", "description": "tài liệu đã nạp bằng doc.load"},
                 "ten": {"type": "string",
                         "description": "tên hồ sơ, mặc định `main`"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["doc_id", "explain"]},
            risk="R2", core=False, needs_explain=True, produces=["display"],
            writes_artefact=True,
            keywords=["màn hình", "lcd", "độ phân giải", "hệ màu", "panel", "display",
                      "dpi", "cảm ứng", "framebuffer"])
    def display_profile(ctx: Any, doc_id: str, explain: dict[str, Any], ten: str = "main"):
        """Không có hồ sơ này thì tác tử sẽ TỰ NHỚ ra `800×480`.

        Và đó không phải một lo xa: `grep` cả kho ngày 10/10/2026 không ra một Fact nào về màn
        hình — `KHOA_CHUAN` không có khoá `lcd.*` nào. Dự án này đã trả giá ba lần cho hằng số
        phần cứng tự nhớ (xem `hang-so-phan-cung-phai-tra`).

        Trích dẫn của mỗi trường phải là một dòng **nói về màn hình**. Phép đo trên
        `tai-lieu-kien-truc-c4.md` của repo chỉ ra vì sao: khớp `ARGB8888` đầu tiên nằm ở dòng
        nói về *ảnh logo trong firmware*, không phải định dạng bộ đệm khung của panel. Hai dòng
        ấy cho **cùng một giá trị**, nên bản không kiểm sẽ "đúng đáp án mà sai bằng chứng" —
        ca tệ nhất, vì nó không có biểu hiện nào để ai phát hiện.
        """
        a = ctx.store.get(doc_id)
        if a is None:
            raise EideError(
                "E1112", f"Chưa nạp tài liệu `{doc_id}`.",
                hint_for_agent="Gọi `doc.load` trên tệp tài liệu trước.",
                alternatives=["doc.load", "store.list"], blame="agent")

        from ..knowledge import docs as docs_mod

        duong = ((a.get("canonical") or {}).get("path") or "")
        p = Path(duong)
        if not p.is_absolute():
            p = _goc(ctx) / duong
        if not p.is_file():
            raise EideError(
                "E1112", f"Tệp của tài liệu `{doc_id}` không còn ở `{duong}`.",
                hint_for_agent="Nạp lại tài liệu bằng `doc.load`.",
                alternatives=["doc.load"], blame="user")

        try:
            tl = docs_mod.nap_bat_ky(p, doc_id=doc_id) if hasattr(docs_mod, "nap_bat_ky") \
                else docs_mod.nap_van_ban(p, doc_id=doc_id)
            chu = "\n".join(t.chu for t in tl.trang)
        except Exception:                                    # noqa: BLE001
            chu = p.read_text("utf-8", errors="replace")

        hs = MH.ho_so_tu_chu(chu)
        d = {
            "ten": ten, "rong": hs.rong, "cao": hs.cao, "he_mau": hs.he_mau,
            "he_mau_khac": hs.he_mau_khac, "inch": hs.inch, "dpi": hs.dpi,
            "dpi_la_tinh_ra": hs.dpi_la_tinh_ra, "driver": hs.driver, "bus": hs.bus,
            "cam_ung": hs.cam_ung, "loai": hs.loai, "cot": hs.cot, "dong": hs.dong,
            "nguon": hs.nguon, "thieu": hs.thieu, "doc_id": doc_id,
            "vi_sao_khong_hop_le": hs.vi_sao_khong_hop_le,
        }
        dem = MH.kiem_dem_khung(hs.rong, hs.cao, hs.he_mau) if hs.hop_le else None
        if dem:
            d["dem_khung"] = dem

        ctx.store.apply(
            artefact_id=_ma_ho_so(ten), type="display",
            op="update" if ctx.store.get(_ma_ho_so(ten)) else "create",
            author=f"agent:{ctx.run_id}", explain=explain, canonical=d,
            view_hint={"kind": "kv", "path": ""})

        if not hs.hop_le:
            return {**d, "hop_le": False, "note_vi": (
                f"Hồ sơ `{ten}` đã ghi, nhưng nó **chưa dùng được để thiết kế**: "
                + hs.vi_sao_khong_hop_le
                + f" Tài liệu `{doc_id}` không nói: "
                + ", ".join(f"`{k}`" for k in hs.thieu) + ".")}
        return {**d, "hop_le": True, "note_vi": (
            f"Panel `{ten}`: **{hs.rong}×{hs.cao} px**, hệ màu {hs.he_mau}"
            + (f" (panel cũng nhận {', '.join(hs.he_mau_khac)})" if hs.he_mau_khac else "")
            + (f", {hs.inch:g}\" → **{hs.dpi:.0f} DPI** (TÍNH ra, không đọc được)"
               if hs.dpi else "")
            + (f", driver {hs.driver}" if hs.driver else "")
            + (f", bus {hs.bus}" if hs.bus else "")
            + (", có cảm ứng" if hs.cam_ung else
               (", KHÔNG cảm ứng" if hs.cam_ung is False else ", chưa biết có cảm ứng không"))
            + ". Mỗi trường mang trích dẫn nguyên văn một dòng của tài liệu."
            + (f" Tài liệu KHÔNG nói: {', '.join('`' + k + '`' for k in hs.thieu)} — những "
               "trường ấy để TRỐNG, không điền mặc định." if hs.thieu else "")
            + (" " + dem["note_vi"] if dem else ""))}

    # ================================================================== ui.screen_set
    @r.tool("screen.set", "Thiết kế",
            "Ghi BẢN THIẾT KẾ một màn hình giao diện. Toạ độ là pixel thật của panel; độ phân "
            "giải lấy từ hồ sơ `display.profile`, KHÔNG khai ở đây. Sáu loại phần tử: text, "
            "rect, line, image, bar, button.",
            {"type": "object",
             "properties": {
                 "ten": {"type": "string", "description": "tên màn hình, ví dụ `chinh`"},
                 "ho_so": {"type": "string", "description": "tên hồ sơ panel, mặc định `main`"},
                 "mau_nen": {"type": "string", "description": "#RRGGBB, mặc định #000000"},
                 "phan_tu": _S_PHAN_TU,
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ten", "phan_tu", "explain"]},
            risk="R2", core=False, needs_explain=True, produces=["ui_screen"],
            writes_artefact=True,
            keywords=["thiết kế giao diện", "ui", "màn hình", "bố cục", "nhãn", "nút",
                      "screen", "layout"])
    def ui_screen_set(ctx: Any, ten: str, phan_tu: list[dict[str, Any]],
                      explain: dict[str, Any], ho_so: str = "main",
                      mau_nen: str = "#000000"):
        """Công cụ này **không có tham số độ phân giải**, và đó là một quyết định.

        Nhận `rong`/`cao` từ mô hình là mở lại đúng cửa mà hồ sơ màn hình dựng ra để đóng: mô
        hình sẽ điền `800×480` từ ký ức, và một bản thiết kế vẽ cho một màn hình tưởng tượng
        thì mọi toạ độ trong nó sai mà không lỗi nào kêu lên.
        """
        hs = _doc_ho_so(ctx, ho_so)
        if not hs.hop_le:
            raise EideError(
                "E1113", f"Hồ sơ `{_ma_ho_so(ho_so)}` chưa dùng được: "
                + (hs.vi_sao_khong_hop_le or "thiếu dữ kiện"),
                hint_for_agent=("Nạp một tài liệu có nói độ phân giải và hệ màu của panel rồi "
                                "gọi lại `display.profile`. Không có hồ sơ hợp lệ thì bản "
                                "thiết kế không có khung nào để kiểm biên."),
                alternatives=["doc.load", "display.profile"], blame="agent")

        mh = MO.ManHinh(ten=ten, rong=hs.rong, cao=hs.cao, he_mau=hs.he_mau,
                        mau_nen=mau_nen,
                        phan_tu=[MO.PhanTu.tu_dict(x) for x in (phan_tu or [])])
        kq = MO.kiem(mh, hs)

        ctx.store.apply(
            artefact_id=_ma_man_hinh(ten), type="ui_screen",
            op="update" if ctx.store.get(_ma_man_hinh(ten)) else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={**mh.to_dict(), "ho_so": ho_so, "kiem": _kq_dict(kq)},
            deps={"upstream": [_ma_ho_so(ho_so)]},
            view_hint={"kind": "html", "path": ""})

        return {"ten": ten, "so_phan_tu": len(mh.phan_tu), **_kq_dict(kq),
                "note_vi": (
                    f"Đã ghi bản thiết kế `{_ma_man_hinh(ten)}`: {len(mh.phan_tu)} phần tử trên "
                    f"panel {hs.rong}×{hs.cao} ({hs.he_mau}). "
                    + (f"**{len(kq.loi)} lỗi** — bản thiết kế này KHÔNG chạy đúng trên panel "
                       "thật: " + "; ".join(f"{x['ma']} {x.get('phan_tu', '')}"
                                            for x in kq.loi[:5])
                       + (f" …+{len(kq.loi) - 5}" if len(kq.loi) > 5 else "")
                       + ". Gọi `screen.check` để xem đầy đủ vì sao và cách sửa."
                       if kq.loi else
                       "Không lỗi nào ở những chỗ phép kiểm chạm tới (biên panel, cỡ chữ và bề "
                       "rộng chữ theo bảng font BSP, hệ màu, bộ đệm khung). Nó KHÔNG kiểm được "
                       "bố cục có hợp lý với người dùng hay không.")
                    + (f" {len(kq.canh_bao)} cảnh báo." if kq.canh_bao else ""))}

    # ================================================================== ui.check
    @r.tool("screen.check", "Thiết kế",
            "Bản thiết kế này có chạy đúng trên PANEL THẬT không: phần tử ra ngoài biên, chữ "
            "dài hơn ô chứa nó, cỡ chữ không có trong thư viện BSP, ký tự ngoài bảng font, hai "
            "màu thành một màu sau lượng hoá. Năm thứ ấy đều biên dịch SẠCH.",
            {"type": "object",
             "properties": {"ten": {"type": "string"},
                            "ho_so": {"type": "string"}},
             "required": ["ten"]},
            risk="R1", core=False,
            keywords=["kiểm giao diện", "ui check", "biên", "tràn", "cỡ chữ", "lượng hoá",
                      "cắt chữ"])
    def ui_check(ctx: Any, ten: str, ho_so: str = ""):
        mh = _doc_man_hinh(ctx, ten)
        a = ctx.store.get(_ma_man_hinh(ten)) or {}
        hs = _doc_ho_so(ctx, ho_so or (a.get("canonical") or {}).get("ho_so") or "main")
        kq = MO.kiem(mh, hs)
        return {**_kq_dict(kq), "ngoai_pham_vi": list(MO.NGOAI_PHAM_VI),
                "note_vi": (
                    (f"**{len(kq.loi)} lỗi**: "
                     + "; ".join(f"{x['ma']} `{x.get('phan_tu', '')}` — {x['vi_sao']}"
                                 for x in kq.loi)
                     if kq.loi else
                     "Không lỗi nào ở những chỗ phép kiểm này chạm tới.")
                    + (f" **{len(kq.canh_bao)} cảnh báo**: "
                       + "; ".join(f"{x['ma']} — {x['vi_sao']}" for x in kq.canh_bao)
                       if kq.canh_bao else "")
                    + (" Chưa đủ dữ kiện để kiểm: "
                       + "; ".join(x["vi_sao"] for x in kq.chua_kiem)
                       if kq.chua_kiem else "")
                    + " Phép kiểm này KHÔNG chạm tới: " + "; ".join(MO.NGOAI_PHAM_VI) + ".")}

    # ================================================================== ui.render
    @r.tool("screen.render", "Thiết kế",
            "Dựng trang HTML xem bản thiết kế — tỉ lệ 1:1 với panel thật, vẽ bằng màu PANEL SẼ "
            "HIỆN sau lượng hoá (không phải màu gõ vào), và tự khai cấu hình panel kèm trích "
            "dẫn nguồn. Giao diện mở trang này ở tab Màn hình.",
            {"type": "object",
             "properties": {"ten": {"type": "string"},
                            "ho_so": {"type": "string"},
                            "explain": EXPLAIN_SCHEMA},
             "required": ["ten", "explain"]},
            risk="R2", core=False, needs_explain=True, produces=["ui_render"],
            writes_artefact=True,
            keywords=["render", "xem giao diện", "html", "bản vẽ", "preview", "màn hình"])
    def ui_render(ctx: Any, ten: str, explain: dict[str, Any], ho_so: str = ""):
        """Vẽ bằng màu panel SẼ HIỆN, không bằng màu người thiết kế gõ vào.

        Nếu vẽ `#FF8040` trong khi panel RGB565 hiện `#FF8242` thì bản xem **đẹp hơn** màn hình
        thật, và người dùng duyệt một thứ họ sẽ không nhận được. Đó là N6 áp vào một bức tranh.
        """
        mh = _doc_man_hinh(ctx, ten)
        a = ctx.store.get(_ma_man_hinh(ten)) or {}
        ten_hs = ho_so or (a.get("canonical") or {}).get("ho_so") or "main"
        hs = _doc_ho_so(ctx, ten_hs)
        kq = MO.kiem(mh, hs)

        thu_muc = _goc(ctx) / THU_MUC_UI
        thu_muc.mkdir(parents=True, exist_ok=True)
        tep = thu_muc / f"{SC.ten_ham(ten)[6:]}.html"
        tep.write_text(HT.dung_html(mh, hs, kq=kq), "utf-8")
        tuong_doi = str(tep.relative_to(_goc(ctx)))

        ctx.store.apply(
            artefact_id=f"ui_render:{ten}", type="ui_render",
            op="update" if ctx.store.get(f"ui_render:{ten}") else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={"ten": ten, "tep": tuong_doi, "rong": mh.rong, "cao": mh.cao,
                       "he_mau": mh.he_mau or hs.he_mau, "kiem": _kq_dict(kq)},
            deps={"upstream": [_ma_man_hinh(ten), _ma_ho_so(ten_hs)]},
            view_hint={"kind": "html", "path": "tep"})

        return {"tep": tuong_doi, "rong": mh.rong, "cao": mh.cao, **_kq_dict(kq),
                "note_vi": (
                    f"Đã dựng `{tuong_doi}` — xem ở tab **Màn hình**. Khung vẽ đúng "
                    f"{mh.rong}×{mh.cao} px, tỉ lệ 1:1 với panel. Màu trong khung là màu panel "
                    f"SẼ HIỆN sau khi hệ màu {mh.he_mau or hs.he_mau} cắt bit, không phải màu "
                    "gõ vào bản thiết kế. Trang tự khai cấu hình panel, trích dẫn nguồn của "
                    "cấu hình ấy, và những gì phép kiểm KHÔNG chạm tới."
                    + (f" Trang có in {len(kq.loi)} lỗi của bản thiết kế." if kq.loi else ""))}

    # ================================================================== screen.codegen
    @r.tool("screen.codegen", "Mã nguồn",
            "Sinh tệp C vẽ màn hình bằng `BSP_LCD_*` của bo. Tự tính toạ độ cho mọi kiểu căn "
            "lề (CENTER_MODE của BSP căn giữa theo CẢ MÀN HÌNH, không theo ô), và KHÔNG sinh "
            "phần khởi tạo LCD. Dịch thử bằng `build.compile`.",
            {"type": "object",
             "properties": {"ten": {"type": "string"},
                            "ho_so": {"type": "string"},
                            "duong_dan": {"type": "string",
                                          "description": "nơi ghi tệp .c; mặc định .eide/ui/"},
                            "explain": EXPLAIN_SCHEMA},
             "required": ["ten", "explain"]},
            risk="R2", core=False, needs_explain=True, produces=["ui_code"],
            writes_artefact=True,
            keywords=["sinh code", "codegen", "bsp_lcd", "c", "vẽ màn hình", "firmware ui"])
    def ui_codegen(ctx: Any, ten: str, explain: dict[str, Any], ho_so: str = "",
                   duong_dan: str = ""):
        """Sinh code từ một bản thiết kế **còn lỗi** vẫn chạy — nhưng tệp tự khai lỗi ấy.

        Từ chối sinh sẽ bắt người dùng sửa hết mới được xem code, mà đọc code là một cách hiểu
        bản thiết kế. Sinh im lặng thì tệp ấy dịch sạch và được đọc là dùng được. Nên: sinh, và
        chép danh sách lỗi vào đầu tệp.
        """
        mh = _doc_man_hinh(ctx, ten)
        a = ctx.store.get(_ma_man_hinh(ten)) or {}
        ten_hs = ho_so or (a.get("canonical") or {}).get("ho_so") or "main"
        hs = _doc_ho_so(ctx, ten_hs)
        kq = MO.kiem(mh, hs)

        ma_c = SC.sinh_c(mh, hs, kq=kq)
        tep = (_goc(ctx) / duong_dan) if duong_dan else \
            (_goc(ctx) / THU_MUC_UI / f"{SC.ten_ham(ten)}.c")
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text(ma_c, "utf-8")
        tuong_doi = str(tep.relative_to(_goc(ctx)))

        bo_qua = [p.id for p in mh.phan_tu if p.chu and MO.ngoai_bang_font(p.chu)]
        ctx.store.apply(
            artefact_id=f"ui_code:{ten}", type="ui_code",
            op="update" if ctx.store.get(f"ui_code:{ten}") else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={"ten": ten, "tep": tuong_doi, "ham": SC.ten_ham(ten),
                       "bo_qua": bo_qua, "kiem": _kq_dict(kq)},
            deps={"upstream": [_ma_man_hinh(ten), _ma_ho_so(ten_hs)]},
            view_hint={"kind": "code", "path": "tep"})

        return {"tep": tuong_doi, "ham": SC.ten_ham(ten), "bo_qua": bo_qua, **_kq_dict(kq),
                "note_vi": (
                    f"Đã sinh `{tuong_doi}`, hàm `{SC.ten_ham(ten)}()`. Tệp **chỉ vẽ**: nó "
                    "không sinh `BSP_LCD_Init`/`LayerDefaultInit`/`DisplayOn` vì phần ấy phụ "
                    "thuộc script liên kết và cấu hình xung nhịp của dự án — tiền đề ghi ở đầu "
                    "tệp. Mọi chữ dùng `LEFT_MODE` với toạ độ x tự tính, vì `CENTER_MODE` của "
                    "BSP căn giữa theo CẢ MÀN HÌNH chứ không theo ô chứa chữ "
                    "(`stm32469i_discovery_lcd.c:848`)."
                    + (f" **Bỏ qua {len(bo_qua)} phần tử** có ký tự ngoài bảng font BSP: "
                       + ", ".join(f"`{x}`" for x in bo_qua)
                       + " — sinh lời gọi ấy là sinh một phép đọc ra ngoài bảng font."
                       if bo_qua else "")
                    + (f" Bản thiết kế còn {len(kq.loi)} lỗi, đã chép vào đầu tệp."
                       if kq.loi else "")
                    + " Gọi `build.compile` để dịch thử — dịch được mới là bằng chứng.")}
