# -*- coding: utf-8 -*-
"""Công cụ `build.*` và `sim.*` — bước G6 của MDD-40, phần tối thiểu để đi hết một dự án.

Hai công cụ này là chỗ dễ nói dối nhất trong cả hệ thống, nên cả hai đều viết quanh một câu:
**không có bằng chứng thì không có kết luận.**

  `build.compile`  đạt chỉ khi trình biên dịch trả 0 **và** có tệp ảnh trên đĩa. Kích thước
                   đọc từ `avr-size`. Không có trình biên dịch thì trả lỗi có chỉ dẫn, không
                   "giả lập biên dịch".

  `sim.run`        chạy đúng mã logic của firmware trong một mô hình vật lý, và kết luận
                   đạt/không do **chương trình mô phỏng** nói ra bằng JSON, không do lời văn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

MA_BUILD = "build:firmware"
MA_MAP = "analysis:build-map"
MA_TEST = "sim_result:unit-test"
# M4-04 — hiện vật của phép đo độ nhạy. Dùng chung với M4-06 theo kế hoạch.
MA_DO_NHAY = "sim_result:test-sensitivity"
MA_SIM = "sim_result:can-bang"


def _ma_tc(ma: str) -> str:
    return f"criteria:{ma or 'sim-01'}"


def _ma_tc_unit(ma: str) -> str:
    """M4-01 — khoá hiện vật của tiêu chí UNIT TEST, luôn có tiền tố `unit-`.

    Tiêu chí mô phỏng và tiêu chí unit test dùng chung không gian khoá `criteria:*`. Nếu `ma`
    đi thẳng vào khoá thì một lần gọi `test.criteria(ma="sim-01")` **xoá sổ** tiêu chí mô
    phỏng mà người dùng đã xác nhận, và `sim.run` sau đó phán theo ngưỡng của unit test. Nên
    tiền tố ép ở đây, không nhờ tác tử gõ đúng.
    """
    ten = (str(ma or "").strip() or "unit-01")
    return f"criteria:{ten if ten.startswith('unit-') else f'unit-{ten}'}"


def _kiem_assert(ds: list[dict[str, Any]]) -> "ToolResult | None":
    """Phần kiểm assert dùng chung cho `sim.criteria` và `test.criteria`.

    Một bản sao thứ hai của phép kiểm này sẽ lệch — và lúc lệch, hai loại tiêu chí nhận những
    thứ khác nhau mà không ai nói ra.
    """
    from ..build import tieu_chi as TC

    thieu = [f"assert #{i + 1}" for i, a in enumerate(ds)
             if not a.get("ma") or not a.get("mo_ta")]
    if not ds or thieu:
        return ToolResult(False, error=EideError(
            "E4007",
            "Tiêu chí phải có ít nhất một assert, và mỗi assert phải có `ma` và `mo_ta`."
            + (" Thiếu: " + ", ".join(thieu) if thieu else ""),
            hint_for_agent=("`ma` là thứ số đo của chương trình trỏ tới (ví dụ A1 cho mô "
                            "phỏng, T1 cho unit test); `mo_ta` là câu người đọc hiểu. Thiếu "
                            "một trong hai thì kết quả sau này không ai đọc được."),
            blame="agent"))

    xau = [a for a in ds if str(a.get("phep_so") or "<=") not in TC.PHEP_SO]
    if xau:
        return ToolResult(False, error=EideError(
            "E4007", "Phép so không hợp lệ: "
                     + ", ".join(str(a.get("phep_so")) for a in xau),
            hint_for_agent="Chỉ nhận: " + ", ".join(TC.PHEP_SO),
            blame="agent"))
    return None


def _bay_gio() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _tep_khong_vao_anh(sketch: Path, kq: Any) -> list[str]:
    """Tệp `.c` có trong cây nguồn mà **không** xuất hiện trong lệnh biên dịch.

    So bằng tên tệp trong dòng lệnh thật đã chạy — không đoán theo quy ước thư mục. Bỏ qua
    `vendor/` (mã hãng, có thể cố ý không dịch hết) và mọi thứ dưới thư mục ẩn.
    """
    lenh = " ".join(kq.lenh or [])
    if not lenh:
        return []
    ra: list[str] = []
    for q in sorted(sketch.rglob("*.c")):
        if any(x.startswith(".") for x in q.parts) or "vendor" in q.parts:
            continue
        if q.name not in lenh and str(q) not in lenh:
            ra.append(str(q.relative_to(sketch.parent)))
    return ra


def _nhan_dinh_cua_tac_tu_con(ctx: Any, dam: str, doi_gi: str) -> str:
    """Giao bảng dữ kiện cho `code-analyst` rồi gắn nhận định của nó vào tài liệu.

    Tách **dữ kiện** khỏi **nhận định** ngay trong tài liệu, mỗi phần ghi rõ ai làm ra nó:
    phần trên do mã quét, phần này do một tác tử đọc hiểu. Người duyệt cần phân biệt được —
    một con số quét ra và một câu suy đoán không đứng cùng một hàng.

    Không gọi được mô hình (chạy trong bộ kiểm, hoặc lỗi mạng) thì **nói ra là thiếu**, chứ
    không im lặng trả về tài liệu chỉ có dữ kiện: người đọc sẽ tưởng phần nhận định là "không
    có gì đáng nói".
    """
    llm = getattr(getattr(ctx, "agent", None), "llm", None)
    if llm is None:
        return ("\n## Nhận định\n\n*Chưa có — lượt này không gọi được mô hình. "
                "Tài liệu mới có phần DỮ KIỆN do mã quét ra.*\n")
    try:
        from .. import subagent as SA

        # GHI SỔ. Không truyền `ghi_so` thì tác tử con chạy xong mà **không để lại dấu nào
        # trong sổ cái** — đo được 30/09/2026: `code-analyst` đã chạy và nhận định của nó nằm
        # trong tài liệu, nhưng sổ cái chỉ thấy `verifier`. Một việc không có dấu trong sổ cái
        # là một việc không truy vết được (N1), và ở đây nó còn là một việc TỐN TIỀN không ai
        # đếm được.
        ghi = None
        if getattr(ctx, "ledger", None) is not None:
            def ghi(kind: str, data: dict[str, Any]) -> None:           # noqa: F811
                ctx.ledger.append(kind, {"run_id": getattr(ctx, "run_id", ""), **data})

        bc = SA.chay(llm=llm, registry=ctx.registry, ctx=ctx, ma="code-analyst",
                     ghi_so=ghi,
                     viec=("Đây là bảng dữ kiện do mã quét ra cho một thay đổi sắp làm. "
                           f"Thay đổi dự định: {doi_gi}\n\n" + dam))
    except Exception as e:                                             # noqa: BLE001
        return (f"\n## Nhận định\n\n*Không lấy được: {e}. Tài liệu mới có phần DỮ KIỆN.*\n")

    L = ["", "## Nhận định của tác tử con `code-analyst`", "",
         f"*Tầng tin cậy: **{bc.do_tin or 'DONG'}** · kết luận: `{bc.ket_luan}`. "
         "Phần trên là DỮ KIỆN do mã quét; phần này là ĐỌC HIỂU — hai thứ khác nhau.*", "",
         bc.tom_tat or "*(không có tóm tắt)*", ""]
    if bc.da_lam:
        L += ["**Đã soi:**"] + [f"* {x}" for x in bc.da_lam] + [""]
    if bc.bang_chung:
        L += ["**Bằng chứng:**"] + [f"* `{b.get('kind')}` → {b.get('ref')}"
                                    for b in bc.bang_chung] + [""]
    if bc.chua_lam:
        L += ["**Cố ý chưa soi:**"] + [f"* {x}" for x in bc.chua_lam] + [""]
    return "\n".join(L)


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:
    # =============================================================== môi trường (G6)
    @r.tool("env.check", "Mã nguồn",
            "Kiểm MÁY NÀY có đủ chuỗi công cụ cho chip của dự án không: cái nào có (kèm "
            "phiên bản đọc được), cái nào thiếu, thiếu thì hỏng việc gì. Không bao giờ tự "
            "kết luận “sẵn sàng biên dịch”.",
            {"type": "object",
             "properties": {
                 "isa": {"type": "string",
                         "description": "avr8 | armv7e-m | rv32imac — bỏ trống thì lấy từ "
                                        "hộ chiếu chip"}}},
            risk="R1", core=False,
            keywords=["môi trường", "toolchain", "chuỗi công cụ", "thiếu", "cài",
                      "biên dịch được chưa", "env"])
    def env_check(ctx: Any, isa: str = ""):
        """TC018 — *"Agent phát hiện, hướng dẫn/đề nghị cài đặt (hỏi trước khi cài), không
        báo biên dịch thành công giả"*.

        Cách chắc chắn nhất để không báo thành công giả là **không bao giờ tự tuyên bố sẵn
        sàng**: công cụ này chỉ liệt kê cái có và cái thiếu, kèm lệnh cài THẬT sẽ chạy nếu
        người dùng đồng ý. Kết luận "chạy được hay không" thuộc về `build.compile`, và nó chỉ
        nói "đạt" khi có tệp ảnh trên đĩa.
        """
        from ..build import toolchain as TC

        hc = _ho_chieu(ctx)
        isa = isa or str((hc or {}).get("isa") or "")
        kq = TC.kiem_moi_truong(isa)
        thieu = [c for c in kq["cong_cu"] if not c["co"]]
        return {
            **kq, "chip": (hc or {}).get("chip", ""),
            "cach_cai": {c["ten"]: c["cach_cai"] for c in thieu if c["cach_cai"]},
            "note_vi": (
                (f"Kiến trúc “{isa}” chưa có trong bảng chuỗi công cụ của EIDE "
                 f"(đang biết: {', '.join(kq['isa_biet'])}). Nói thẳng với người dùng rằng "
                 "EIDE chưa biên dịch được cho chip này — đừng chọn một kiến trúc gần giống, "
                 "mã sinh ra sẽ mang lệnh chip không chạy được. "
                 if kq["isa_chua_biet"] else
                 f"Máy này có {kq['so_co']} công cụ, thiếu {kq['so_thieu']}. "
                 if isa else
                 "Chưa biết chip của dự án nên chỉ kiểm được công cụ dùng chung. Ghim hộ "
                 "chiếu chip trước (passport.pin). ")
                + (("THIẾU: " + ", ".join(f"{c['ten']} ({c['de_lam_gi']})" for c in thieu)
                    + ". Muốn cài thì HỎI người dùng trước bằng tool.install — đừng tự cài, "
                      "và đừng báo biên dịch được khi chưa có trình biên dịch.")
                   if thieu else "Đủ công cụ cho việc biên dịch và mô phỏng."))}

    @r.tool("tool.install", "Mã nguồn",
            "Cài một công cụ còn thiếu vào máy. Chạy đúng lệnh mà env.check đã nêu, và chỉ "
            "chạy sau khi người dùng duyệt — EIDE không tự cài gì.",
            {"type": "object",
             "properties": {
                 "cong_cu": {"type": "string", "description": "tên công cụ, ví dụ avr-gcc"},
                 "isa": {"type": "string"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["cong_cu", "explain"]},
            risk="R3", core=False, needs_explain=True, gate="G-TOOL",
            keywords=["cài", "install", "toolchain", "thiếu công cụ"])
    def tool_install(ctx: Any, explain: dict[str, Any], cong_cu: str, isa: str = ""):
        """Lệnh cài KHÔNG do mô hình soạn.

        Nó lấy từ bảng `CAN_GI` trong mã — cùng chỗ `env.check` đọc ra để hiện cho người dùng.
        Nếu mô hình được tự soạn lệnh shell thì thẻ cổng đang hỏi người dùng duyệt một thứ mà
        lúc soạn câu hỏi chưa ai đọc kỹ, và "duyệt cài đặt" thành "duyệt chạy một lệnh bất kỳ".
        """
        import subprocess as _sp

        from ..build import toolchain as TC

        hc = _ho_chieu(ctx)
        isa = isa or str((hc or {}).get("isa") or "")
        bang = {c["ten"]: c for c in (TC.CAN_GI_CHUNG + TC.CAN_GI.get(isa, []))}
        c = bang.get(cong_cu)
        if c is None:
            return ToolResult(False, error=EideError(
                "E4005", f"EIDE không có lệnh cài sẵn cho “{cong_cu}”.",
                hint_for_agent=("Chỉ cài được những công cụ có trong bảng: "
                                + ", ".join(sorted(bang))
                                + ". Với thứ khác, nói cho người dùng biết cần cài gì và để "
                                  "họ tự cài — đừng soạn lệnh shell."),
                details={"cai_duoc": sorted(bang)}, blame="agent"))
        lenh = str(c.get("cach_cai") or "")
        if not lenh:
            return ToolResult(False, error=EideError(
                "E4005", f"Chưa biết cách cài “{cong_cu}” trên máy này.",
                hint_for_agent="Nói cho người dùng biết cần công cụ đó để làm gì, và để họ "
                               "cài theo cách của họ.",
                blame="agent"))

        if TC._tim_lenh(cong_cu):
            return {"cong_cu": cong_cu, "da_co": True, "lenh": lenh,
                    "note_vi": f"{cong_cu} đã có sẵn trên máy — không cài lại."}

        r = _sp.run(lenh, shell=True, capture_output=True, text=True, timeout=900)
        duong = TC._tim_lenh(cong_cu)
        dat = bool(duong)
        ctx.store.apply(
            artefact_id=f"build:install:{cong_cu}", type="build",
            op="update" if ctx.store.get(f"build:install:{cong_cu}") else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={"cong_cu": cong_cu, "lenh": lenh, "dat": dat,
                       "duong_dan": duong, "ma_thoat": r.returncode,
                       "nguyen_van": ((r.stdout or "") + (r.stderr or ""))[-3000:]})
        if not dat:
            return ToolResult(False, error=EideError(
                "E4006",
                f"Chạy xong lệnh cài nhưng vẫn không thấy {cong_cu} trong PATH "
                f"(mã thoát {r.returncode}).",
                hint_for_agent=("Đọc đầu ra dưới đây, nói lại cho người dùng bằng lời của "
                                "họ, và ĐỪNG coi là đã cài được:\n"
                                + ((r.stdout or "") + (r.stderr or ""))[-1200:]),
                details={"lenh": lenh, "ma_thoat": r.returncode}, blame="system"))
        return {"cong_cu": cong_cu, "da_co": False, "lenh": lenh, "duong_dan": duong,
                "note_vi": f"Đã cài {cong_cu} bằng `{lenh}` — nay có ở {duong}."}

    # ====================================================================== biên dịch
    @r.tool("code.analyze", "Mã nguồn",
            "PHÂN TÍCH MÃ ĐANG CÓ trước khi sửa nó: tệp có những ký hiệu gì, phụ thuộc gì, "
            "và AI ĐANG DÙNG chúng — tức chỗ nào sẽ phải xem lại sau khi sửa. Bắt buộc nói "
            "rõ SẼ ĐỔI GÌ. Sinh ra một tài liệu `.md` để người đọc trước khi duyệt cho sửa.",
            {"type": "object",
             "properties": {
                 "tep": {"type": "array", "items": {"type": "string"},
                         "description": "các tệp sắp sửa, đường dẫn trong dự án"},
                 "doi_gi": {"type": "string",
                            "description": "sẽ đổi gì, cụ thể — không phải 'cải thiện mã'"},
                 "vi_sao": {"type": "string", "description": "vì sao phải đổi"},
                 "ra": {"type": "string",
                        "description": "nơi ghi tài liệu, mặc định `tai-lieu/phan-tich-ma.md`"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["tep", "doi_gi", "vi_sao", "explain"]},
            # `core=True`: đây là CỬA VÀO của quy trình sửa mã, không phải một công cụ phụ.
            # Đo được 30/09/2026 qua giao diện thật: giao đúng việc *"xem giúp rồi sửa"*, tác
            # tử đọc năm tệp bằng `fs.read` rồi tự sửa — **không gọi `code.analyze` lần nào**,
            # vì nó là `core=False` nên không nằm trong danh sách tác tử nhìn thấy. Lần thứ tư
            # trong dự án này cùng một hình dạng lỗi.
            risk="R2", gate="G-FILE", writes_artefact=True, needs_explain=True, core=True,
            keywords=["phân tích mã", "trước khi sửa", "ai đang dùng", "tác động", "đọc mã",
                      "impact", "code analysis", "sẽ sửa gì"],
            returns_vi="Đường dẫn tài liệu, số ký hiệu, và danh sách chỗ phải xem lại")
    def code_analyze(ctx: Any, tep: list[str], doi_gi: str, vi_sao: str,
                     explain: dict[str, Any], ra: str = ""):
        """Vì sao một công cụ riêng, khi đã có `fs.read`.

        `fs.read` cho thấy **một tệp**. Trước khi sửa mã có sẵn thì câu đắt nhất là câu khác:
        **ai đang dùng nó?** Sửa một hàm mà không biết năm chỗ gọi nó thì năm chỗ ấy hỏng lặng
        lẽ — và `fs.read` không trả lời được, vì câu ấy cần quét cả cây mã.

        Đòi `doi_gi` là cố ý: một bản phân tích không nói sẽ đổi gì thì chỉ là một bản liệt kê.
        Người duyệt đọc nó để quyết *"có cho sửa không"*, mà muốn quyết thì phải biết sửa gì.
        """
        from ..phan_tich_ma import dung_tai_lieu, quet
        from .writing import _rel, _sandbox

        if not tep:
            return ToolResult(False, error=EideError(
                "E4021", "Chưa nêu tệp nào để phân tích.",
                hint_for_agent="Liệt kê đúng những tệp sắp sửa; dùng `fs.glob` nếu chưa chắc.",
                alternatives=["fs.glob", "fs.grep"], blame="agent"))
        if len(doi_gi.strip()) < 15:
            return ToolResult(False, error=EideError(
                "E4022", "`doi_gi` quá ngắn — chưa nói được sẽ đổi gì.",
                hint_for_agent=("Viết cụ thể: hàm nào, hành vi nào, thêm hay bớt gì. "
                                "“Cải thiện mã” không phải một nội dung sửa — người duyệt "
                                "đọc nó xong vẫn không biết họ đang duyệt cái gì."),
                blame="agent"))

        goc = Path(ctx.config.paths.project_root).resolve()
        tm = quet(goc, [str(_sandbox(ctx, t).relative_to(goc)) for t in tep])
        thieu = [t.duong for t in tm if t.so_dong < 0]
        noi_dung = dung_tai_lieu(goc, tm, doi_gi, vi_sao)

        # DỮ KIỆN xong thì tới NHẬN ĐỊNH — và nhận định là việc cần đọc hiểu, không phải việc
        # quét văn bản. Giao cho tác tử con `code-analyst`, ngữ cảnh sạch, chỉ có công cụ đọc.
        #
        # Nó được đưa sẵn bảng dữ kiện để khỏi quét lại, và được hỏi đúng ba câu bảng ấy không
        # trả lời được — nặng nhất là câu thứ ba: **chỗ gọi GIÁN TIẾP** qua con trỏ hàm, macro,
        # bảng phân phối. Phép quét văn bản kêu thừa chứ không bỏ sót chỗ gọi thẳng, nhưng chỗ
        # gọi gián tiếp thì nó mù hẳn — mà đó đúng là chỗ hỏng đắt nhất khi sửa firmware.
        nhan_dinh = _nhan_dinh_cua_tac_tu_con(ctx, noi_dung, doi_gi)
        noi_dung += nhan_dinh

        p_ra = _sandbox(ctx, ra or "tai-lieu/phan-tich-ma.md")
        p_ra.parent.mkdir(parents=True, exist_ok=True)
        cu = p_ra.read_text("utf-8", errors="replace") if p_ra.exists() else None
        p_ra.write_text(noi_dung, "utf-8")
        rel = _rel(ctx, p_ra)
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[rel],
            summary=explain.get("summary", "phân tích mã trước khi sửa"), explain=explain,
            noi_dung_truoc={rel: cu} if cu is not None else None, run_id=ctx.run_id)
        ctx.mark_agent_wrote(rel)
        # Phân tích xong thì coi như ĐÃ ĐỌC: bộ dò đọc trọn từng tệp trong phạm vi.
        for t in tm:
            if t.so_dong >= 0:
                ctx.mark_agent_read(t.duong)

        xem_lai = sorted({x for t in tm for ds in t.ai_dung.values() for x in ds})
        return {
            "tai_lieu": rel, "changeset": cs.id,
            "so_tep": len([t for t in tm if t.so_dong >= 0]),
            "so_ky_hieu": sum(len(t.ky_hieu) for t in tm),
            "thieu_tep": thieu, "cho_phai_xem_lai": xem_lai,
            "note_vi": (
                f"`{rel}` — {len([t for t in tm if t.so_dong >= 0])} tệp, "
                f"{sum(len(t.ky_hieu) for t in tm)} ký hiệu, "
                f"**{len(xem_lai)} tệp khác sẽ phải xem lại** sau khi sửa."
                + (f"\n\nKhông có tệp: {', '.join(thieu)} — kiểm lại đường dẫn."
                   if thieu else "")
                + "\n\nĐưa tài liệu này cho người dùng đọc TRƯỚC khi sửa. Và đọc kỹ phần "
                  "*Giới hạn*: phép dò tìm tên trong văn bản, nên gọi gián tiếp qua con trỏ "
                  "hàm hay macro thì nó không thấy.")}

    @r.tool("build.compile", "Mã nguồn",
            "Biên dịch firmware bằng chuỗi công cụ THẬT trên máy (arduino-cli hoặc avr-gcc). "
            "Trả lỗi kèm tệp:dòng:cột, và kích thước Flash/SRAM đọc từ avr-size. Không có "
            "tệp ảnh thì KHÔNG coi là xong.",
            {"type": "object",
             "properties": {
                 "sketch": {"type": "string",
                            "description": "thư mục sketch hoặc tệp nguồn, ví dụ firmware/"},
                 "isa": {"type": "string",
                         "description": "avr8 | armv6-m | armv7-m | armv7e-m — mặc định lấy "
                                        "từ hộ chiếu chip"},
                 "fpu": {"type": "string",
                         "description": ("CHỈ truyền khi có Fact nói chip có FPU, ví dụ "
                                         "fpv4-sp-d16. Bỏ trống thì dùng dấu phẩy động mềm — "
                                         "chậm hơn nhưng chạy trên mọi biến thể.")},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            # R2, không phải R3. Thang rủi ro đọc là: R2 "ghi trong dự án", R3 "chạm hệ
            # thống/mạng". Biên dịch chạy một chương trình có sẵn trên máy, đọc mã trong dự
            # án và ghi kết quả vào `.eide/build` — không cài gì, không ra mạng, và xoá thư
            # mục build là xong. Xếp nó R3 thì mỗi lần biên dịch là một thẻ cổng, và một
            # vòng sửa–dịch–sửa mười lần thành mười lần bấm duyệt; người dùng sẽ bấm duyệt
            # theo phản xạ, và khi một thẻ ĐÁNG đọc hiện ra thì họ cũng bấm nốt.
            risk="R2", produces=["build"], needs_explain=True, writes_artefact=True,
            keywords=["biên dịch", "build", "compile", "firmware", "gcc", "kích thước"])
    def build_compile(ctx: Any, explain: dict[str, Any], sketch: str = "firmware",
                      isa: str = "", fpu: str = ""):
        from ..build import toolchain as TC

        goc = ctx.config.paths.project_root
        p = (goc / sketch).resolve()
        if not p.exists():
            return ToolResult(False, error=EideError(
                "E4001", f"Không có {sketch} trong dự án để biên dịch.",
                hint_for_agent="Viết mã nguồn trước (fs.write), hoặc chỉ đúng thư mục sketch.",
                alternatives=["fs.write", "fs.glob"], blame="agent"))

        hc = _ho_chieu(ctx)
        isa = isa or str((hc or {}).get("isa") or "avr8")
        flash_max, sram_max = _han_muc(ctx, hc)

        kq = TC.bien_dich(goc=goc, sketch=p, isa=isa, fpu=fpu,
                          flash_toi_da=flash_max, sram_toi_da=sram_max)
        ctx.store.apply(
            artefact_id=MA_BUILD, type="build",
            op="update" if ctx.store.get(MA_BUILD) else "create",
            author=f"agent:{ctx.run_id}", canonical=kq.to_dict(), explain=explain,
            view_hint={"kind": "table", "path": kq.tep_ra})

        if not kq.dat:
            return ToolResult(False, error=EideError(
                "E4002",
                (f"Biên dịch KHÔNG thành công: {kq.vi_sao_khong_dat}"
                 + (" Lỗi đầu tiên: " + kq.loi[0].vi if kq.loi else "")),
                hint_for_agent=(
                    "Sửa đúng những dòng dưới đây rồi biên dịch lại; đừng đoán chỗ khác.\n"
                    + "\n".join(x.vi for x in kq.loi[:12])
                    + ("\n(còn " + str(len(kq.loi) - 12) + " lỗi nữa)"
                       if len(kq.loi) > 12 else "")
                    + _goi_y_fpu(kq.loi, fpu)),
                details={"loi": [x.to_dict() for x in kq.loi[:40]],
                         "nguyen_van": kq.nguyen_van[-2000:],
                         "cong_cu": kq.cong_cu, "lenh": kq.lenh},
                alternatives=["fs.read", "fs.edit"], blame="agent"))

        qua_flash = flash_max and kq.flash > flash_max
        qua_sram = sram_max and kq.sram > sram_max

        # TỆP NÀO KHÔNG VÀO ẢNH — phải nói ra, không để nó là chỗ trống.
        #
        # Đo được 30/09/2026 trên phiên dựng RTOS: hai lần biên dịch đầu ĐỎ (`E4002`), lần thứ
        # ba bỏ bớt đầu vào thì XANH — và ảnh ra 1 416 byte, **không một ký hiệu LCD/UI/Touch
        # nào**, trong khi dự án có 15 tệp mã. Tác tử báo "biên dịch xong", đúng về lời gọi và
        # sai về việc: nó đã thu hẹp đầu vào cho tới khi qua được.
        #
        # 1 416 byte trông như một con số, không trông như một vấn đề. Nên phép so phải do MÃ
        # làm: tệp `.c` có trong cây nguồn mà không có mặt trong ảnh là một danh sách, và một
        # danh sách khác rỗng thì không ai đọc nhầm thành "xong".
        bo_sot = _tep_khong_vao_anh(p, kq)
        return {
            **kq.to_dict(),
            "tep_khong_vao_anh": bo_sot,
            "vua_chip": not (qua_flash or qua_sram),
            "note_vi": (
                (f"⚠︎ **{len(bo_sot)} tệp mã trong dự án KHÔNG có mặt trong ảnh vừa dựng**: "
                 + ", ".join(f"`{x}`" for x in bo_sot[:8])
                 + (f" …+{len(bo_sot) - 8}" if len(bo_sot) > 8 else "")
                 + ". Biên dịch “xong” mà thiếu chúng thì cái chạy trên bo không phải cái bạn "
                   "viết. Kiểm lại `sketch` và danh sách nguồn TRƯỚC khi báo là đạt.\n\n"
                 if bo_sot else "")
                + f"Biên dịch xong bằng {kq.cong_cu}: {kq.tep_ra}. "
                + (f"Flash {kq.flash} B"
                   + (f"/{flash_max} B ({kq.flash / flash_max:.0%})" if flash_max else "")
                   + f", SRAM {kq.sram} B"
                   + (f"/{sram_max} B ({kq.sram / sram_max:.0%})" if sram_max else "")
                   + ". " if kq.flash or kq.sram else
                   "Không đọc được kích thước (thiếu avr-size), nên CHƯA biết nó có vừa "
                   "chip không. ")
                + (f"{len(kq.canh_bao)} cảnh báo — đọc và sửa, cảnh báo của trình biên dịch "
                   "trên AVR thường là lỗi thật: "
                   + "; ".join(x.vi for x in kq.canh_bao[:3])
                   if kq.canh_bao else "Không có cảnh báo nào.")
                + (" VƯỢT hạn mức bộ nhớ của chip." if (qua_flash or qua_sram) else "")
                + (f" Có tệp nạp {kq.tep_bin} (ảnh nhị phân thô, dùng cho bo nạp kiểu ổ đĩa)."
                   if kq.tep_bin else "")
                + (" LƯU Ý: máy này KHÔNG có newlib cho ARM, nên firmware được liên kết ở chế "
                   "độ `-nostdlib`. Mọi hàm chuẩn (memset, memcpy, printf, strlen…) sẽ báo "
                   "“undefined reference” khi liên kết — kể cả khi bạn không gọi trực tiếp, vì "
                   "trình biên dịch tự sinh memcpy/memset cho phép gán cấu trúc và khởi tạo "
                   "mảng. Viết mã không dùng thư viện chuẩn, hoặc nhờ người dùng cài newlib "
                   "qua tool.install."
                   if kq.thieu_libc else ""))}

    @r.tool("build.map", "Mã nguồn",
            "Đọc bản đồ bộ nhớ của tệp ảnh vừa biên dịch: từng section chiếm bao nhiêu, "
            "symbol nào to nhất, có vừa ngân sách Flash/RAM không, và nếu tràn thì bỏ gì "
            "trước khi nghĩ tới đổi chip.",
            {"type": "object",
             "properties": {"explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R1", core=False, needs_explain=True, produces=["analysis"],
            writes_artefact=True,
            keywords=["map", "bộ nhớ", "flash", "ram", "tràn", "tối ưu", "kích thước"])
    def build_map(ctx: Any, explain: dict[str, Any]):
        """TC021 — *"phân tích map file, đề xuất tối ưu hoặc đổi MCU"*.

        Một con số tổng nói firmware có vừa chip không; nó không nói **phải bỏ gì** khi không
        vừa. Đó là toàn bộ lý do công cụ này tồn tại tách khỏi `build.compile`.
        """
        from ..build import toolchain as TC

        goc = ctx.config.paths.project_root
        a = ctx.store.get(MA_BUILD)
        if a is None:
            return ToolResult(False, error=EideError(
                "E4001", "Chưa biên dịch lần nào nên chưa có bản đồ bộ nhớ để đọc.",
                hint_for_agent="Gọi build.compile trước.",
                alternatives=["build.compile"], blame="agent"))
        elf = next(iter(sorted((goc / ".eide" / "build").glob("*.elf"))), None)
        if elf is None:
            return ToolResult(False, error=EideError(
                "E4001", "Không có tệp .elf trong .eide/build — chưa đọc được section.",
                hint_for_agent="Biên dịch lại; một số chuỗi công cụ chỉ sinh .hex, khi đó "
                               "nói thẳng là không đọc được bản đồ bộ nhớ.",
                alternatives=["build.compile"], blame="system"))

        flash_max, sram_max = _han_muc(ctx, _ho_chieu(ctx))
        m = TC.doc_map(elf=elf, flash_toi_da=flash_max, sram_toi_da=sram_max)
        ctx.store.apply(
            artefact_id=MA_MAP, type="analysis",
            op="update" if ctx.store.get(MA_MAP) else "create",
            author=f"agent:{ctx.run_id}", canonical=m, explain=explain,
            view_hint={"kind": "table", "path": m.get("tep", "")})
        to_nhat = ", ".join(f"{s['ten']} {s['byte']} B" for s in m["symbol"][:3])
        return {**m,
                "note_vi": (
                    f"Flash {m['flash']} B"
                    + (f"/{flash_max} B" if flash_max else " (chưa biết ngân sách)")
                    + f", SRAM {m['sram']} B"
                    + (f"/{sram_max} B" if sram_max else " (chưa biết ngân sách)")
                    + (f". Chiếm nhiều nhất: {to_nhat}." if to_nhat else ".")
                    + (" " + " ".join(m["de_xuat"]) if m["de_xuat"] else "")
                    + (" " + " ".join(m["canh_bao"]) if m["canh_bao"] else ""))}

    # ====================================================================== tiêu chí
    @r.tool("sim.criteria", "Mô phỏng",
            "Nêu TIÊU CHÍ trước khi chạy mô phỏng: từng assert đo gì, ngưỡng bao nhiêu, "
            "ngưỡng lấy từ đâu, đo YÊU CẦU nào — và phần nào KHÔNG mô phỏng được. Người dùng "
            "xác nhận rồi mới chạy được sim.run.",
            {"type": "object",
             "properties": {
                 "ma": {"type": "string", "description": "sim-01"},
                 "ten": {"type": "string"},
                 "assert": {
                     "type": "array",
                     "description": "từng điều kiện đo được",
                     "items": {"type": "object", "properties": {
                         "ma": {"type": "string", "description": "A1 — số đo trỏ tới mã này"},
                         "mo_ta": {"type": "string"},
                         "phep_so": {"type": "string",
                                     "enum": ["<=", ">=", "<", ">", "==", "trong_khoang"]},
                         "nguong": {"type": "number"},
                         "nguong_tren": {"type": "number"},
                         "don_vi": {"type": "string"},
                         "do_req": {"type": "string", "description": "assert này đo REQ nào"},
                         "nguon_nguong": {"type": "string",
                                          "description": "ngưỡng lấy từ Fact/tài liệu/lời ai"},
                     }}},
                 "khong_mo_phong_duoc": {
                     "type": "array",
                     "description": "phần không mô phỏng được: {gi, vi_sao, cach_bu}",
                     "items": {"type": "object"}},
                 "timeout_s": {"type": "number"},
                 "trich_loi": {"type": "string",
                               "description": "LỜI người dùng xác nhận tiêu chí này"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["assert", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["criteria"],
            keywords=["tiêu chí", "criteria", "assert", "ngưỡng", "nghiệm thu", "mô phỏng"])
    def sim_criteria(ctx: Any, explain: dict[str, Any], **kw: Any):
        """Tiêu chí NÊU TRƯỚC — và không tự xác nhận hộ người dùng.

        TC016 đòi *"Agent nêu trước tiêu chí đạt, chạy mô phỏng, xuất bằng chứng, kết luận"*.
        TC022 đòi chiều ngược lại: *"không được sửa tiêu chí/test để ép đạt; mọi thay đổi
        tiêu chí phải hỏi người dùng"*. Hai câu đó cùng nói một điều: tiêu chí là **của người
        dùng**, nên ở đây `trich_loi` là đường duy nhất để một tiêu chí được coi là đã xác
        nhận, và đổi ngưỡng khi đã có kết quả thì đi qua cổng G-QUAL (xem policy.yaml).
        """
        from ..build import tieu_chi as TC

        ds = kw.get("assert") or []
        if (xau := _kiem_assert(ds)) is not None:
            return xau

        khong_nguon = [str(a.get("ma")) for a in ds if not str(a.get("nguon_nguong") or "")]
        moi = TC.TieuChi.from_dict({**kw, "assert": ds})
        loi = str(kw.get("trich_loi") or "").strip()
        if loi:
            moi.xac_nhan_boi, moi.xac_nhan_luc, moi.trich_loi = "human", _bay_gio(), loi

        cu = ctx.store.get(_ma_tc(moi.ma))
        # Danh sách "không mô phỏng được" biến mất giữa hai lần ghi tiêu chí là đúng cách mà
        # chữ "đạt" bắt đầu trùm lên những thứ chưa ai đo. Ghi đè thì được, im lặng thì không.
        mat_kmp = [x for x in ((cu or {}).get("canonical") or {}).get("khong_mo_phong_duoc")
                   or [] if x not in moi.khong_mo_phong_duoc]
        # M2-01 — từng assert đã khai `do_req`; gom lại thành upstream để sửa một REQ chỉ
        # làm lỗi thời đúng những tiêu chí ĐO nó.
        do_req = [x for x in dict.fromkeys(str(a.get("do_req") or "").strip() for a in ds) if x]
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=_ma_tc(moi.ma), type="criteria",
            op="update" if cu else "create", canonical=moi.to_dict(), explain=explain,
            run_id=ctx.run_id, deps={"upstream": do_req} if do_req else None)
        return {
            **moi.to_dict(), "changeset": cs.id, "thieu_nguon_nguong": khong_nguon,
            "mat_khong_mo_phong_duoc": mat_kmp,
            "note_vi": ((
                f"CẢNH BÁO: lần ghi này BỎ MẤT {len(mat_kmp)} phần từng khai là không mô "
                "phỏng được ("
                + "; ".join(str(x.get("gi", "")) for x in mat_kmp[:3])
                + "). Nếu chúng vẫn chưa mô phỏng được thì khai lại — bỏ chúng đi là để chữ "
                  "“đạt” trùm lên phần chưa ai đo. " if mat_kmp else "") + (
                f"Đã ghi {len(ds)} tiêu chí cho mô phỏng {moi.ma}: "
                + "; ".join(a.vi for a in moi.asserts[:4])
                + (f" (còn {len(ds) - 4} tiêu chí nữa)" if len(ds) > 4 else "") + ". "
                + (f"{len(moi.khong_mo_phong_duoc)} phần KHÔNG mô phỏng được đã ghi kèm — "
                   "chúng sẽ đi cùng mọi kết quả, để không ai đọc “đạt” thành “đạt hết”. "
                   if moi.khong_mo_phong_duoc else
                   "CHƯA khai phần nào không mô phỏng được. Nếu có ngoại vi mà mô hình không "
                   "dựng (WS2812, siêu âm…), khai ra — tuyên bố đạt cho phần chưa mô phỏng "
                   "là đậu giả. ")
                + (f"Thiếu nguồn ngưỡng cho: {', '.join(khong_nguon)} — người rà soát sẽ hỏi "
                   "con số đó ở đâu ra. " if khong_nguon else "")
                + ("Người dùng đã xác nhận, nên sim.run chạy được."
                   if moi.da_xac_nhan else
                   "CHƯA có xác nhận của người dùng: trình bảng này cho họ, và gọi lại với "
                   "trich_loi là câu họ nói. sim.run sẽ từ chối tới khi đó.")))}

    # ====================================================================== mô phỏng
    @r.tool("sim.run", "Mô phỏng",
            "Chạy mô phỏng vòng điều khiển bằng CHÍNH mã logic của firmware (biên dịch cho "
            "máy chủ) trong một mô hình vật lý. Kết luận đạt/không do chương trình mô phỏng "
            "in ra dạng JSON, không do lời văn.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "array", "items": {"type": "string"},
                           "description": "tệp .c cần biên dịch cùng nhau; mặc định là "
                                          "sim/*.c + firmware/control.c"},
                 "tham_so": {"type": "array", "items": {"type": "string"},
                             "description": "tham số dòng lệnh cho chương trình mô phỏng"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            # R2 — cùng lý do với `build.compile`: chạy trong dự án, không chạm hệ thống.
            risk="R2", produces=["sim_result"], needs_explain=True, writes_artefact=True,
            keywords=["mô phỏng", "sim", "kiểm chứng", "vòng điều khiển", "cân bằng"])
    def sim_run(ctx: Any, explain: dict[str, Any], nguon: list[str] | None = None,
                tham_so: list[str] | None = None, ma_tieu_chi: str = "sim-01"):
        from ..build import mo_phong as MP
        from ..build import tieu_chi as TCM

        goc = ctx.config.paths.project_root

        # §B1: "sim.run cần criteria đã xác nhận". Chạy trước rồi mới nêu tiêu chí là mở sẵn
        # cửa cho việc đặt tiêu chí VỪA KHÍT với thứ vừa đo được.
        a_tc = ctx.store.get(_ma_tc(ma_tieu_chi))
        if a_tc is None:
            return ToolResult(False, error=EideError(
                "E4008", f"Chưa có tiêu chí {ma_tieu_chi} nào cho mô phỏng.",
                hint_for_agent=("Nêu tiêu chí TRƯỚC bằng sim.criteria: mỗi assert đo gì, "
                                "ngưỡng bao nhiêu, lấy từ đâu, đo REQ nào. Rồi trình cho "
                                "người dùng xác nhận. Chạy trước rồi đặt tiêu chí sau là "
                                "cách đặt tiêu chí vừa khít với kết quả."),
                alternatives=["sim.criteria"], blame="agent"))
        tc = TCM.TieuChi.from_dict(a_tc["canonical"])
        if not tc.da_xac_nhan:
            return ToolResult(False, error=EideError(
                "E4009", f"Tiêu chí {tc.ma} chưa được người dùng xác nhận.",
                hint_for_agent=("Trình bảng tiêu chí cho người dùng, hỏi họ có đồng ý không, "
                                "rồi gọi lại sim.criteria với trich_loi là câu họ trả lời. "
                                "Đừng tự xác nhận hộ."),
                alternatives=["sim.criteria", "ask_user"], blame="agent"))
        if nguon:
            ds = [(goc / x) for x in nguon]
        else:
            ds = sorted((goc / "sim").glob("*.c")) + sorted((goc / "firmware").glob("control*.c"))
        if not ds:
            return ToolResult(False, error=EideError(
                "E4003",
                "Không tìm thấy tệp nguồn mô phỏng (sim/*.c và firmware/control*.c).",
                hint_for_agent=(
                    "Mô phỏng phải chạy ĐÚNG mã sẽ nạp vào chip. Tách phần logic của "
                    "firmware (lọc góc, PID, quy đổi throttle) ra một tệp không đụng thanh "
                    "ghi AVR, rồi viết sim/ chứa mô hình vật lý và hàm main() in ra một dòng "
                    "JSON có khoá `dat`."),
                alternatives=["fs.write", "fs.glob"], blame="agent"))

        kq = MP.chay_mo_phong(goc=goc, nguon=ds, tham_so=tham_so,
                              giay_toi_da=max(tc.timeout_s, 1.0))
        do = dict((kq.ket_qua or {}).get("do") or {})
        xet = TCM.xet_ket_qua(tc, do)

        # DEV-336. Không một mã assert nào của tiêu chí xuất hiện trong số đo → đây KHÔNG
        # phải sản phẩm sai, mà là **sai tiêu chí hoặc sai nguồn mô phỏng**. Hai chuyện ấy
        # dẫn tới hai việc ngược nhau: một cái bảo đi sửa mã, cái kia bảo gọi lại cho đúng.
        #
        # Vì sao cần chặn thay vì để `dat: False`: `ma_tieu_chi` mặc định là "sim-01" và
        # `nguon` mặc định lấy MỌI tệp `sim/*.c`. Nên chỉ cần thêm một tệp mô phỏng thứ hai
        # là lượt chạy sau đem số đo của nó so với tiêu chí của tệp trước, rồi ghi đè lên
        # cùng một mã hiện vật. Đo được trên phiên robot 04/10/2026: hiện vật
        # `sim_result:can-bang` bản 8 ghi `ma_tieu_chi = sim-01` (đòi A1–A10) với số đo
        # `{C1, C2}` của bộ `sim-ntc`, và `dat = False`.
        #
        # Hậu quả không phải một lỗi kêu lên — mà là **sở cứ nói ngược báo cáo**: tác tử báo
        # 10/10 đạt (đúng, nó đã chạy thật), còn hiện vật lưu lại nói không đạt. Người đọc
        # sở cứ sau này thấy `dat: False` và không có cách nào biết đó là "sai tiêu chí".
        if tc.asserts and not (set(do) & {a.ma for a in tc.asserts}):
            return ToolResult(False, error=EideError(
                "E4023",
                f"Số đo không chứa MỘT mã assert nào của tiêu chí {tc.ma}. "
                f"Tiêu chí đòi {sorted(a.ma for a in tc.asserts)[:8]}, "
                f"chương trình in ra {sorted(do)[:8]}.",
                hint_for_agent=(
                    "Đây KHÔNG phải sản phẩm sai — là sai cặp tiêu chí/nguồn. Hai chỗ hay "
                    "lệch: `ma_tieu_chi` mặc định là \"sim-01\" nên lượt chạy cho một bộ "
                    "tiêu chí khác phải nêu rõ; và `nguon` bỏ trống thì lấy MỌI tệp "
                    "`sim/*.c`, nên có hai chương trình mô phỏng là phải nêu đúng tệp. "
                    "Nêu cả hai rồi gọi lại — đừng sửa mã sản phẩm vì con số này."),
                details={"ma_tieu_chi": tc.ma,
                         "assert_doi": sorted(a.ma for a in tc.asserts),
                         "so_do_nhan_duoc": sorted(do),
                         "tep_nguon": [str(x.relative_to(goc)) for x in ds]},
                alternatives=["sim.criteria", "sim.run"], blame="agent"))
        canon = {**kq.to_dict(), "ma_tieu_chi": tc.ma, "xet": xet, "so_do": do,
                 "khong_mo_phong_duoc": tc.khong_mo_phong_duoc,
                 "dat": bool(kq.chay_duoc and xet["dat"])}
        ctx.store.apply(
            artefact_id=MA_SIM, type="sim_result",
            op="update" if ctx.store.get(MA_SIM) else "create",
            author=f"agent:{ctx.run_id}", canonical=canon, explain=explain,
            view_hint={"kind": "table", "path": "sim"})

        if not kq.chay_duoc:
            treo = "chạy quá" in kq.vi_sao_khong_dat
            return ToolResult(False, error=EideError(
                "E4010" if treo else "E4004",
                f"Mô phỏng chưa chạy được: {kq.vi_sao_khong_dat}",
                hint_for_agent=(
                    (f"Quá {tc.timeout_s:.0f} s mà chưa xong — gần như luôn là một vòng chờ "
                     "cờ không bao giờ bật. Tìm vòng `while` chờ điều kiện trong mã logic, "
                     "và nhớ mô phỏng không có ngắt nào bật cờ hộ."
                     if treo else
                     "Sửa lỗi biên dịch của phần mô phỏng rồi chạy lại.\n"
                     + kq.loi_bien_dich[-1200:])),
                details={"lenh": kq.lenh_bien_dich, "timeout_s": tc.timeout_s},
                blame="agent"))

        dem = xet["dem"]
        return {
            **canon,
            "note_vi": (
                (f"{dem['dat']}/{len(tc.asserts)} tiêu chí ĐẠT"
                 + (f", {dem['khong_dat']} KHÔNG đạt" if dem["khong_dat"] else "")
                 + (f", {dem['chua_do_duoc']} CHƯA đo được" if dem["chua_do_duoc"] else "")
                 + ". ")
                + ("" if xet["dat"] else "Chưa đạt: " + xet["vi_sao_khong_dat"] + ". ")
                + (f"Số đo thừa (không assert nào nhận): {', '.join(xet['so_do_thua'])}. "
                   if xet["so_do_thua"] else "")
                + ("KHÔNG mô phỏng được: "
                   + "; ".join(f"{x.get('gi')} ({x.get('vi_sao')}) — bù bằng "
                               f"{x.get('cach_bu', 'đo trên bo')}"
                               for x in tc.khong_mo_phong_duoc)
                   + ". Phần đó KHÔNG nằm trong kết luận trên. "
                   if tc.khong_mo_phong_duoc else "")
                + "Đây là kết quả trên MÔ HÌNH: nó nói mã điều khiển tự nhất quán và ổn định "
                  "được với mô hình đó, KHÔNG nói mạch thật sẽ chạy."),
        }


    # ====================================================================== unit test
    @r.tool("test.sensitivity", "Mô phỏng",
            "ĐO XEM BỘ KIỂM CÓ ĐO GÌ KHÔNG: phá mã sản phẩm rồi chạy lại test. Không ca nào "
            "đỏ nghĩa là bộ kiểm không nhìn thấy tệp ấy — dù báo cáo có bao nhiêu ô xanh. "
            "Gọi nó SAU khi test.run xanh, trước khi nói với người dùng rằng đã kiểm xong.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "array", "items": {"type": "string"},
                           "description": ("tệp mã SẢN PHẨM cần đo (không phải tệp test); "
                                           "bỏ trống thì lấy firmware/*.c")},
                 "test": {"type": "array", "items": {"type": "string"},
                          "description": "tệp test; bỏ trống thì lấy test/*.c + tests/*.c"},
                 "muc": {"type": "string", "enum": ["tep", "chi_tiet"],
                         "description": ("tep (mặc định): một câu cho mỗi tệp. chi_tiet: phá "
                                         "TỪNG vị trí, trả điểm đột biến và danh sách DÒNG "
                                         "bộ kiểm không canh — chậm hơn nhiều")},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            # M4-04 — nay GHI hiện vật, nên phải đòi `explain`: N8 không có ngoại lệ, và sổ
            # công cụ chặn đúng chỗ ấy (`writes_artefact and not needs_explain`). Vẫn R1 và
            # vẫn không khoá — "rẻ tới mức gọi được ngay" là chuyện mức rủi ro và cửa duyệt,
            # không phải chuyện một trường giải thích. Và một hiện vật mang lời giải thích do
            # chính công cụ sinh ra thì đúng là "lời tự khai mặc áo phép đo" mà DEV-346 vừa
            # đi chữa.
            risk="R1", core=False, writes_artefact=True, needs_explain=True,
            produces=["sim_result"],
            keywords=["độ nhạy", "đột biến", "mutation", "mutation score", "điểm đột biến",
                      "test có đo gì không", "kiểm bộ kiểm", "test giả", "ô xanh giả"])
    def test_sensitivity(ctx: Any, explain: dict[str, Any], nguon: list[str] | None = None,
                         test: list[str] | None = None, muc: str = "tep"):
        """Đo được trên phiên FreeRTOS: tác tử viết `test/test_ui.c` với sáu ca kiểm đầy đủ
        tên, ngưỡng, báo cáo JSON — và **tự định nghĩa lại** hàm của sản phẩm ngay trong tệp
        test. Phá `firmware/ui.c` thật thì cả sáu ca vẫn ĐẠT.

        Cấu trúc đúng không chứng minh được nó đo gì.
        """
        from ..build import dot_bien as DB
        from ..build import mo_phong as MP

        goc = ctx.config.paths.project_root
        tep_test = ([(goc / x) for x in test] if test else
                    sorted((goc / "test").glob("*.c")) + sorted((goc / "tests").glob("*.c")))
        tep_test = [x for x in tep_test if x.exists()]
        if not tep_test:
            return ToolResult(False, error=EideError(
                "E4011", "Chưa có tệp test nào để đo độ nhạy.",
                hint_for_agent="Viết test trước (xem test.run), rồi quay lại đo.",
                alternatives=["test.run"], blame="agent"))
        sp = ([(goc / x) for x in nguon] if nguon else
              [x for x in sorted((goc / "firmware").glob("*.c"))
               if x.name not in ("startup.c", "libc_stub.c")])
        sp = [x for x in sp if x.exists()][:12]
        if not sp:
            return ToolResult(False, error=EideError(
                "E4011", "Không thấy tệp mã sản phẩm nào để phá.",
                hint_for_agent="Nêu `nguon` là các tệp .c của sản phẩm mà bộ kiểm này nhắm tới.",
                blame="agent"))

        def _chay(them: Any = None) -> tuple[bool, str]:
            """`them=None`: chạy bộ kiểm y như tác tử vẫn chạy. `them=p`: nạp thêm tệp sản
            phẩm `p`. Hai lần chạy này phải khác nhau, nếu không phép đo vô nghĩa.

            M4-05 — KHAI ra khi lượt này **không dịch được**, bằng tiền tố `[BIEN_DICH] `.
            `dot_bien` không được tự đoán từ nội dung log: `vi_sao_khong_dat` của một ca test
            hỏng thật rất dễ chứa chữ `error:`, và lúc ấy một phép đo *bắt được* bị đọc thành
            *chưa đo được*.

            Chỉ gắn khi có `loi_bien_dich`. `chay_duoc=False` còn có nghĩa khác — quá hạn
            chẳng hạn — và một mutant làm bộ kiểm treo thì KHÔNG phải mutant không dịch được.
            """
            # Đường tìm header gắn cho CẢ hai lượt, và đó là có chủ ý.
            #
            # Bản đầu của tôi gắn `-I` và chỉ gắn cho lượt có tệp sản phẩm, vì `-I` vào thư
            # mục firmware làm `#include <stdio.h>` của tệp test khớp vào `stdio.h` giả của bo
            # — mốc của `du-lieu/rtos-sinhvien` đổi từ XANH sang ĐỎ, và cả ba dự án thật thành
            # "không đo được". Nhưng cái phải sửa là **loại cờ**, không phải chỗ gắn nó:
            # `-iquote` chỉ đổi đường cho `#include "..."`, và kể cả thế thì thư mục của tệp
            # đang dịch vẫn được tìm trước. Nên gắn nó cho lượt mốc không đổi gì — giữ một
            # nhánh `if` không đổi hành vi chỉ là một nhánh không ca kiểm nào canh được.
            kq = MP.chay_test(goc=goc, nguon=tep_test + ([them] if them else []),
                              them_co=co_include)
            if not kq.chay_duoc:
                return DB.ket_qua_chay(dat=False, loi_bien_dich=kq.loi_bien_dich[-800:],
                                       log=(kq.vi_sao_khong_dat or "")[-800:])
            return DB.ket_qua_chay(dat=kq.so_hong == 0, log=kq.vi_sao_khong_dat or "")

        # M4-19 — đột biến trên BẢN SAO, tệp sản phẩm của người dùng chỉ được ĐỌC.
        #
        # Đường cũ ghi mã đã phá vào chính tệp của dự án rồi trả lại trong `finally`: an toàn
        # với ngoại lệ Python, KHÔNG an toàn với `Ctrl-C` hay mất điện. Suốt M4-05 tôi phải
        # sao `du-lieu/` ra thư mục tạm trước mỗi lượt đo thật, chỉ vì chuyện này.
        #
        # Và cái bẫy đi kèm: bản sao không còn nằm cạnh header của nó, nên `#include "pid.h"`
        # đứt, `cc` đổ, và phép đo xếp tệp ấy là `khong_nap_duoc` — *"bộ kiểm chưa từng chạy
        # một dòng nào của nó"*. Một cáo buộc sai về sản phẩm, sinh ra từ chỗ đặt bản sao. Nên
        # đường tìm header trỏ về **thư mục gốc của từng tệp sản phẩm**.
        #
        # `-iquote`, KHÔNG phải `-I`. `-I` đổi đường tìm cho cả `#include <...>`, nên một
        # thư mục firmware có header giả của bo sẽ che header hệ thống. Đo được ngày
        # 08/10/2026: `du-lieu/rtos-sinhvien/firmware/` có `stdio.h` riêng, và `-I` vào đó làm
        # `#include <stdio.h>` của tệp test khớp vào bản giả — `FILE` thành chưa khai báo, và
        # **11 trong 12** tệp bị xếp là `khong_nap_duoc` (*"thiếu header của bo"*). Một cáo
        # buộc sai với từng tệp, do đúng cái cờ tôi thêm vào để tránh một cáo buộc sai khác.
        #
        # `-iquote` chỉ đổi đường cho `#include "..."` — đúng và chỉ đúng phần bị bản sao làm
        # đứt.
        co_include: list[str] = [
            f"-iquote{d}" for d in dict.fromkeys(str(x.parent) for x in sp)]

        tam = goc / ".eide" / "mutate" / str(ctx.run_id)
        d = DB.do_do_nhay(sp, _chay, thu_muc_tam=tam, muc=muc)
        # `do_do_nhay` dọn thư mục nó được GIAO; thư mục cha `.eide/mutate` là của công cụ
        # này, nên công cụ này dọn. Lồng theo `run_id` để hai lượt chạy song song không phá
        # bản sao của nhau — và vì thế phải có một bước dọn cái vỏ rỗng còn lại.
        try:
            tam.parent.rmdir()
        except OSError:
            pass                      # còn lượt khác đang dùng, hoặc chưa bao giờ được tạo
        xau = [x for x in d.get("tep", [])
               if x["trang_thai"] in ("khong_thay", "khong_nap_duoc")]

        # M4-04 — ghi HIỆN VẬT. Trước đó phép đo này **không ghi gì vào kho**: con số nó tìm
        # ra tắt theo lượt, nên lượt sau không ai biết nó từng xảy ra, và không bề mặt nào
        # hiện được nó. Một phép đo không vào kho thì bằng chưa đo (xem DEV-341 cho cùng mẫu).
        ctx.store.apply(
            artefact_id=MA_DO_NHAY, type="sim_result",
            op="update" if ctx.store.get(MA_DO_NHAY) else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={**{k: v for k, v in d.items() if k != "song"},
                       "muc": muc, "song": (d.get("song") or [])[:20],
                       # M4-06 — PHIÊN BẢN của `sim_result:unit-test` lúc đo. Hook Stop so
                       # con số này, KHÔNG so mốc thời gian: `updated_at` có độ phân giải
                       # thô, nên hai lần ghi trong cùng một giây bằng nhau và phép so
                       # "mới hơn" im lặng sai. Một số phiên bản là dữ kiện chính xác; một
                       # cái đồng hồ thì không.
                       "version_test": ((ctx.store.get(MA_TEST) or {}).get("version"))},
            # M4-06 — KHAI `deps.upstream`: con số này nói về một cặp *(tệp test, tệp sản
            # phẩm)* cụ thể. Thiếu khai thì sửa một trong hai rồi con số cũ **nằm đó như còn
            # đúng** — và một con số đã lỗi thời mà không ai đánh dấu thì tệ hơn không có con
            # số: nó dừng việc đo lại.
            deps={"upstream": [str(x.relative_to(goc)) if x.is_relative_to(goc) else str(x)
                               for x in list(tep_test) + list(sp)]},
            view_hint={"kind": "table", "path": "do-nhay"})

        return {
            **d, "khong_cham": [x["tep"] for x in xau],
            "note_vi": DB.loi_nguoi_doc(d)
            + ("\n\nSửa theo hướng này: tách phần LOGIC (tính toán, máy trạng thái, kiểm "
               "toạ độ) ra một tệp .c KHÔNG `#include` header của bo, rồi cho cả firmware "
               "lẫn tệp test cùng dịch tệp ấy. Đừng chép logic sang tệp test — một bộ kiểm "
               "tự định nghĩa lại thứ nó đang kiểm thì xanh mãi mãi." if xau else "")}

    # ========================================= M4-06: vòng tự nâng bộ kiểm, SAU CỜ và CÓ TRẦN
    @r.tool("test.harden", "Mô phỏng",
            "NÂNG bộ kiểm: với mỗi đột biến còn SỐNG (bộ kiểm không bắt được), gọi một tác tử "
            "con viết thêm một ca. EIDE tự chạy ca mới HAI lần — phải XANH trên mã thật và ĐỎ "
            "trên mã đã phá — ca nào không giết được mutant thì BỊ LOẠI. Có trần vòng và trần "
            "lời gọi; chạy sau khi test.sensitivity đã chỉ ra chỗ không canh.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "array", "items": {"type": "string"},
                           "description": "tệp mã SẢN PHẨM cần nâng độ nhạy cho"},
                 "test": {"type": "array", "items": {"type": "string"},
                          "description": "tệp test hiện có; bỏ trống thì lấy test/*.c"},
                 "max_vong": {"type": "integer",
                              "description": "trần số mutant đem đi nhờ viết ca, mặc định 3"},
                 "toi_da_goi": {"type": "integer",
                                "description": "trần lời gọi mô hình, mặc định 15"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", core=False, feature="test_harden", needs_explain=True,
            keywords=["nâng bộ kiểm", "harden", "thêm ca kiểm", "giết mutant",
                      "đột biến còn sống", "tự nâng test"])
    def test_harden(ctx: Any, explain: dict[str, Any], nguon: list[str] | None = None,
                    test: list[str] | None = None, max_vong: int = 3,
                    toi_da_goi: int = 15):
        """Evaluator–Optimizer, và phần *Evaluator* do MÃ làm chứ không do mô hình làm.

        Vòng tự nâng nào nhận mọi ca do mô hình viết cũng sẽ sinh ra đúng thứ cả mảng này đi
        chữa: **ca xanh mãi mãi**. Mô hình có động cơ rõ ràng để viết một ca như thế — việc nó
        được giao là "làm cho mutant chết", và chép giá trị trong mã sản phẩm sang ca kiểm là
        đường ngắn nhất tới một ô xanh. Nên phép nhận ca KHÔNG hỏi mô hình: EIDE chạy bộ kiểm
        **hai lần** — một lần trên mã thật, một lần trên mã đã phá — và chỉ nhận ca khi lượt
        đầu XANH và lượt sau ĐỎ.

        Trần cứng ở cả hai phía. `muc="chi_tiet"` mất 0,6 s mỗi lượt biên dịch + chạy
        (DEV-350), và mỗi mutant đem đi nhờ viết ca còn tốn một lượt mô hình — nên một vòng
        không trần là một vòng tiêu tới khi hết hạn mức.
        """
        from .. import subagent as SA
        from ..build import dot_bien as DB
        from ..build import mo_phong as MP

        goc = ctx.config.paths.project_root
        tep_test = ([(goc / x) for x in test] if test else
                    sorted((goc / "test").glob("*.c")) + sorted((goc / "tests").glob("*.c")))
        tep_test = [x for x in tep_test if x.exists()]
        sp = [(goc / x) for x in (nguon or [])]
        sp = [x for x in sp if x.exists()] or [
            x for x in sorted((goc / "firmware").glob("*.c"))
            if x.name not in ("startup.c", "libc_stub.c")][:4]
        if not tep_test or not sp:
            return ToolResult(False, error=EideError(
                "E4011", "Cần ít nhất một tệp test và một tệp mã sản phẩm.",
                hint_for_agent="Nêu `nguon` là tệp .c của sản phẩm, `test` là tệp kiểm.",
                blame="agent"))

        co_include = [f"-iquote{d}" for d in dict.fromkeys(str(x.parent) for x in sp)]

        def _chay(ds: list[Any]) -> bool:
            """Bộ kiểm (gồm cả ca mới nếu có) có XANH hay không."""
            kq = MP.chay_test(goc=goc, nguon=ds, them_co=co_include)
            return bool(kq.chay_duoc and kq.so_ca > 0 and kq.so_hong == 0)

        # Tìm mutant còn SỐNG. Đo trên bản sao, không chạm tệp của người dùng (M4-19).
        tam = goc / ".eide" / "harden" / str(ctx.run_id)

        def _do(ds_test: list[Any]) -> dict[str, Any]:
            def chay(them: Any = None) -> tuple[bool, str]:
                kq = MP.chay_test(goc=goc, nguon=ds_test + ([them] if them else []),
                                  them_co=co_include)
                if not kq.chay_duoc:
                    return DB.ket_qua_chay(dat=False,
                                           loi_bien_dich=kq.loi_bien_dich[-800:],
                                           log=(kq.vi_sao_khong_dat or "")[-800:])
                return DB.ket_qua_chay(dat=kq.so_hong == 0, log=kq.vi_sao_khong_dat or "")

            return DB.do_do_nhay(sp, chay, thu_muc_tam=tam, muc="chi_tiet",
                                 toi_da_moi_tep=max(max_vong * 2, 6))

        d0 = _do(tep_test)
        song = list(d0.get("song") or [])[:max_vong]

        nhan: list[dict[str, Any]] = []
        loai: list[dict[str, Any]] = []
        so_goi = 0
        for i, m in enumerate(song):
            if so_goi >= toi_da_goi:
                break
            ten_test = ", ".join(f"`{x.relative_to(goc)}`" for x in tep_test)
            viec = (f"Đột biến còn SỐNG trong `{m['tep']}` dòng {m['dong']} "
                    f"({m['phep']}):\n\n  trước: {m['truoc']}\n  sau  : {m['sau']}\n\n"
                    f"Bộ kiểm hiện tại ({ten_test}) vẫn XANH khi dòng ấy bị sửa như trên.\n\n"
                    "Thêm MỘT ca kiểm đọc được hành vi mà dòng ấy quyết định, **vào chính "
                    f"tệp test đang có** ({ten_test}): đọc nó ra, thêm ca vào mảng `ca` của "
                    "dòng JSON nó in, rồi ghi lại. ĐỪNG tạo tệp test mới — mọi tệp trong "
                    "`test/` được dịch CÙNG NHAU, nên một tệp thứ hai có `main()` làm trình "
                    "liên kết báo trùng ký hiệu và cả bộ kiểm không dịch được.\n\n"
                    "`fs.write` lên một tệp đang có sẽ bị từ chối (E4020) nếu lượt này bạn "
                    "chưa `fs.read` trọn tệp ấy — đọc trước, rồi ghi lại cả tệp.")
            # Ảnh chụp NỘI DUNG, không chỉ danh sách tệp: ca mới phải vào tệp test đang có
            # (xem `viec` ở trên), nên "có ca mới" là *nội dung đổi*, không phải *có tệp mới*.
            truoc_anh = {x: x.read_text("utf-8")
                         for x in sorted((goc / "test").glob("*.c"))} \
                if (goc / "test").is_dir() else {}
            bc = SA.chay(llm=ctx.agent.llm if getattr(ctx, "agent", None) else None,
                         registry=ctx.registry, ctx=ctx, ma="test-writer", viec=viec)
            so_goi += max(int(getattr(bc, "so_goi", 0) or 0), 1)
            sau_anh = {x: x.read_text("utf-8")
                       for x in sorted((goc / "test").glob("*.c"))} \
                if (goc / "test").is_dir() else {}
            da_doi = [x for x, v in sau_anh.items() if truoc_anh.get(x) != v]
            if not da_doi:
                loai.append({**m, "vi_sao": "tác tử con không ghi ca nào"})
                continue
            ca_moi = [x for x in da_doi if x not in truoc_anh]   # tệp mới (nếu có)

            # ===== PHÉP NHẬN: mã làm, không hỏi mô hình. Hai lượt chạy, hai kết luận khác
            # nhau — thiếu một trong hai là loại.
            tep_sp = next((x for x in sp if x.name == m["tep"]), None)
            if tep_sp is None:
                loai.append({**m, "vi_sao": "không tìm lại được tệp sản phẩm"})
                continue
            van = tep_sp.read_text("utf-8")
            db = next((x for x in DB.liet_ke_dot_bien(van)
                       if x.dong == m["dong"] and x.mo_ta == m["phep"]), None)
            if db is None:
                loai.append({**m, "vi_sao": "không dựng lại được đột biến ấy"})
                continue

            ds_moi = sorted(set(tep_test) | set(sau_anh))
            xanh_that = _chay(ds_moi + [tep_sp])
            try:
                tep_sp.write_text(DB.ap_mot(van, db), "utf-8")
                do_mutant = not _chay(ds_moi + [tep_sp])
            finally:
                tep_sp.write_text(van, "utf-8")

            ten_ca = [str(x.relative_to(goc)) for x in da_doi]
            if xanh_that and do_mutant:
                nhan.append({**m, "ca": ten_ca})
                tep_test = ds_moi      # ca đã nhận thì lượt sau đo cùng nó
            else:
                # TRẢ LẠI bộ kiểm như trước: một ca bị loại mà vẫn nằm trong `test/` là một
                # ca xanh mãi mãi ở lại trong dự án — đúng thứ cả mảng này đi chữa.
                for x, v in truoc_anh.items():
                    x.write_text(v, "utf-8")
                for x in ca_moi:
                    x.unlink(missing_ok=True)
                loai.append({
                    **m, "ca": ten_ca,
                    "vi_sao": ("ca mới làm bộ kiểm ĐỎ ngay trên mã thật" if not xanh_that
                               else "ca mới không giết được mutant — nó xanh cả khi mã đã phá")})

        import shutil as _sh
        _sh.rmtree(tam, ignore_errors=True)
        try:
            tam.parent.rmdir()
        except OSError:
            pass

        return {
            "diem_truoc": d0.get("diem"), "so_mutant_song": len(d0.get("song") or []),
            "so_vong": len(song), "so_goi": so_goi,
            "so_ca_nhan": len(nhan), "so_ca_loai": len(loai),
            "nhan": nhan, "loai": loai,
            "note_vi": (
                f"{len(song)} đột biến sống đem đi nhờ viết ca (trần {max_vong}); "
                f"NHẬN {len(nhan)}, LOẠI {len(loai)}."
                + ("".join(f" · {x['tep']}:{x['dong']} — {x['vi_sao']}" for x in loai[:4]))
                + (" Ca bị loại đã bị xoá: một ca xanh mãi mãi làm con số độ nhạy đẹp lên mà "
                   "bộ kiểm không khá hơn." if loai else "")
                + " Chạy lại `test.sensitivity` để lấy con số sau khi nâng."
                if song else
                "Không đột biến nào còn sống trong phạm vi đã đo — không có gì để nâng.")}

    # ======================================= M4-01: tiêu chí cho unit test, nêu TRƯỚC khi chạy
    @r.tool("test.criteria", "Mô phỏng",
            "Nêu TIÊU CHÍ trước khi chạy unit test: từng assert đo gì, ngưỡng bao nhiêu, "
            "ngưỡng lấy từ đâu, đo YÊU CẦU nào. Người dùng xác nhận rồi thì `test.run` phán "
            "theo ngưỡng này — tệp test chỉ còn in SỐ ĐO, không tự in `dat:true`. Không có "
            "tiêu chí thì test.run vẫn chạy, nhưng kết quả là lời TỰ KHAI của tệp test.",
            {"type": "object",
             "properties": {
                 "ma": {"type": "string",
                        "description": "unit-01 (luôn được ép tiền tố `unit-`)"},
                 "ten": {"type": "string"},
                 "assert": {
                     "type": "array",
                     "description": "từng điều kiện đo được",
                     "items": {"type": "object", "properties": {
                         "ma": {"type": "string",
                                "description": "T1 — số đo của tệp test trỏ tới mã này"},
                         "mo_ta": {"type": "string"},
                         "phep_so": {"type": "string",
                                     "enum": ["<=", ">=", "<", ">", "==", "trong_khoang"]},
                         "nguong": {"type": "number"},
                         "nguong_tren": {"type": "number"},
                         "don_vi": {"type": "string"},
                         "do_req": {"type": "string", "description": "assert này đo REQ nào"},
                         "nguon_nguong": {"type": "string",
                                          "description": "ngưỡng lấy từ Fact/tài liệu/lời ai"},
                     }}},
                 "khong_kiem_duoc": {
                     "type": "array",
                     "description": "phần unit test KHÔNG kiểm được: {gi, vi_sao, cach_bu}",
                     "items": {"type": "object"}},
                 "timeout_s": {"type": "number"},
                 "trich_loi": {"type": "string",
                               "description": "LỜI người dùng xác nhận tiêu chí này"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["assert", "explain"]},
            risk="R2", core=False, writes_artefact=True, needs_explain=True,
            produces=["criteria"],
            keywords=["tiêu chí", "criteria", "assert", "ngưỡng", "unit test", "kiểm thử"])
    def test_criteria(ctx: Any, explain: dict[str, Any], **kw: Any):
        """Tiêu chí unit test — và tệp test là thứ TÁC TỬ TỰ VIẾT.

        `sim.criteria` đã làm đúng việc này cho mô phỏng từ lâu. Chỗ unit test cần riêng một
        công cụ vì cái vòng *"thứ bị kiểm tự chấm điểm mình"* ở đây khép kín hơn: tác tử viết
        mã sản phẩm, viết tệp test cho nó, rồi đọc kết quả do chính tệp test ấy in ra. Ở mô
        phỏng, ít nhất mô hình vật lý còn do người dựng.

        Hai điều công cụ này không làm: **không tự xác nhận hộ người dùng** (`trich_loi` là
        đường duy nhất), và **không ép** — `test.run` không nêu `ma_tieu_chi` thì vẫn chạy
        theo đường cũ, chỉ dán nhãn tự khai. Ép sẽ phá tương thích ngược với mọi dự án đang
        có, và một công cụ phá việc cũ thì bị gỡ chứ không được dùng.
        """
        from ..build import tieu_chi as TC

        ds = kw.get("assert") or []
        if (xau := _kiem_assert(ds)) is not None:
            return xau

        khong_nguon = [str(a.get("ma")) for a in ds if not str(a.get("nguon_nguong") or "")]
        khoa = _ma_tc_unit(str(kw.get("ma") or ""))
        moi = TC.TieuChi.from_dict({**kw, "assert": ds,
                                    "ma": khoa.split(":", 1)[1],
                                    # `TieuChi` gọi danh sách này là `khong_mo_phong_duoc`;
                                    # ở đây lược đồ nói `khong_kiem_duoc` vì unit test không
                                    # mô phỏng gì. Cùng một trường, hai tên theo ngữ cảnh.
                                    "khong_mo_phong_duoc": (kw.get("khong_kiem_duoc")
                                                            or kw.get("khong_mo_phong_duoc")
                                                            or [])})
        loi = str(kw.get("trich_loi") or "").strip()
        if loi:
            moi.xac_nhan_boi, moi.xac_nhan_luc, moi.trich_loi = "human", _bay_gio(), loi

        cu = ctx.store.get(khoa)
        mat_kkd = [x for x in ((cu or {}).get("canonical") or {}).get("khong_mo_phong_duoc")
                   or [] if x not in moi.khong_mo_phong_duoc]
        do_req = [x for x in dict.fromkeys(str(a.get("do_req") or "").strip() for a in ds) if x]
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=khoa, type="criteria",
            op="update" if cu else "create", canonical=moi.to_dict(), explain=explain,
            run_id=ctx.run_id, deps={"upstream": do_req} if do_req else None)
        return {
            **moi.to_dict(), "changeset": cs.id, "hien_vat": khoa,
            "thieu_nguon_nguong": khong_nguon, "mat_khong_kiem_duoc": mat_kkd,
            "note_vi": (
                (f"CẢNH BÁO: lần ghi này BỎ MẤT {len(mat_kkd)} phần từng khai là unit test "
                 "không kiểm được (" + "; ".join(str(x.get("gi", "")) for x in mat_kkd[:3])
                 + "). Khai lại nếu chúng vẫn chưa kiểm được. " if mat_kkd else "")
                + f"Đã ghi {len(ds)} tiêu chí cho unit test {moi.ma}: "
                + "; ".join(a.vi for a in moi.asserts[:4])
                + (f" (còn {len(ds) - 4} tiêu chí nữa)" if len(ds) > 4 else "") + ". "
                + ('Từ giờ tệp test in SỐ ĐO, không in kết luận — một dòng JSON cuối '
                   '`{"do": {"' + (moi.asserts[0].ma if moi.asserts else "T1")
                   + '": <số đo>}}`, khoá là mã assert. ')
                + (f"Thiếu nguồn ngưỡng cho: {', '.join(khong_nguon)} — người rà soát sẽ hỏi "
                   "con số đó ở đâu ra. " if khong_nguon else "")
                + ("Người dùng đã xác nhận, nên `test.run(ma_tieu_chi=\"" + moi.ma
                   + "\")` chạy được."
                   if moi.da_xac_nhan else
                   "CHƯA có xác nhận của người dùng: trình bảng này cho họ, và gọi lại với "
                   "`trich_loi` là câu họ nói. `test.run` có nêu mã tiêu chí sẽ từ chối tới "
                   "khi đó."))}

    @r.tool("test.run", "Mô phỏng",
            "Chạy unit test của firmware trên MÁY CHỦ (phần cứng thay bằng mock): bao nhiêu "
            "ca đạt, ca nào hỏng và vì sao, và độ phủ nếu đo được. Nêu `ma_tieu_chi` thì "
            "EIDE PHÁN theo ngưỡng đã xác nhận; không nêu thì kết quả là lời tự khai của "
            "chính tệp test.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "array", "items": {"type": "string"},
                           "description": "tệp .c cần biên dịch cùng nhau; mặc định "
                                          "test/*.c + firmware/control*.c"},
                 "ma_tieu_chi": {"type": "string",
                                 "description": "mã tiêu chí của test.criteria, ví dụ "
                                                "unit-01. Bỏ trống thì kết quả là lời tự "
                                                "khai của tệp test"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", core=False, needs_explain=True, writes_artefact=True,
            produces=["sim_result"],
            keywords=["test", "unit test", "kiểm thử", "độ phủ", "mock"])
    def test_run(ctx: Any, explain: dict[str, Any], nguon: list[str] | None = None,
                 ma_tieu_chi: str = ""):
        """TC052 — *"Test chạy trên máy chủ, có báo cáo đạt/không đạt và độ phủ"*.

        Hai điều công cụ này từ chối làm: nhận một bản báo cáo bằng lời (không đếm được), và
        im lặng bỏ cột độ phủ khi không đo được (người đọc sẽ hiểu là không có gì để nói).

        **M4-01 — `ma_tieu_chi` để trống là CÒN ĐƯỢC, không phải lỗi.** Mọi dự án đang có đi
        đường ấy, và ép tiêu chí ngay sẽ phá chúng. Nhưng lượt tự khai phải **tự nói ra** là
        tự khai: hai lượt khác chế độ mà đọc giống nhau thì con số "3/3 ca đạt" của một lượt
        tệp-test-tự-chấm được đọc ngang một lượt đã phán — đúng lỗi khối A8.0 ở DEV-344.
        """
        from ..build import mo_phong as MP
        from ..build import tieu_chi as TCM

        goc = ctx.config.paths.project_root
        tc = None
        if str(ma_tieu_chi or "").strip():
            khoa = _ma_tc_unit(ma_tieu_chi)
            a_tc = ctx.store.get(khoa)
            # Dùng lại E4008/E4009 của `sim.run`: cùng một chuyện, cùng một mã. Một mã mới
            # cho cùng một chuyện là bắt người đọc học hai lần.
            if a_tc is None:
                return ToolResult(False, error=EideError(
                    "E4008", f"Chưa có tiêu chí `{khoa.split(':', 1)[1]}` nào cho unit test.",
                    hint_for_agent=("Nêu tiêu chí TRƯỚC bằng `test.criteria`: mỗi assert đo "
                                    "gì, ngưỡng bao nhiêu, lấy từ đâu, đo REQ nào. Rồi trình "
                                    "cho người dùng xác nhận. Chạy trước rồi đặt tiêu chí "
                                    "sau là cách đặt tiêu chí vừa khít với kết quả."),
                    alternatives=["test.criteria"], blame="agent"))
            tc = TCM.TieuChi.from_dict(a_tc["canonical"])
            if not tc.da_xac_nhan:
                return ToolResult(False, error=EideError(
                    "E4009", f"Tiêu chí {tc.ma} chưa được người dùng xác nhận.",
                    hint_for_agent=("Trình bảng tiêu chí cho người dùng, hỏi họ có đồng ý "
                                    "không, rồi gọi lại `test.criteria` với `trich_loi` là "
                                    "câu họ trả lời. Đừng tự xác nhận hộ."),
                    alternatives=["test.criteria", "ask_user"], blame="agent"))
        # Tệp TEST phải có ít nhất một cái. Mã logic đi kèm để liên kết, nhưng một mình nó
        # không phải một bộ test — bản trước gom cả `control.c` vào rồi báo "không biên dịch
        # được" (đúng: nó không có main()), trong khi câu đúng là "chưa có test nào".
        tep_test = ([(goc / x) for x in nguon] if nguon else
                    sorted((goc / "test").glob("*.c")) + sorted((goc / "tests").glob("*.c")))
        tep_test = [x for x in tep_test if x.exists()]
        ds = tep_test + ([] if nguon else _logic_dich_duoc_tren_may(goc))
        if not tep_test:
            return ToolResult(False, error=EideError(
                "E4011", "Chưa có tệp test nào (test/*.c hoặc tests/*.c).",
                hint_for_agent=(
                    "Viết test cho phần LOGIC của firmware — phần không đụng thanh ghi. Mỗi "
                    "tệp test có main(). " + MP.KHUON_RA + "\n"
                    "Chưa có test thì nói thẳng là chưa có, đừng coi im lặng là đạt."),
                alternatives=["fs.write", "fs.glob"], blame="agent"))

        kq = MP.chay_test(goc=goc, nguon=ds, tieu_chi=tc)

        # Đã có tiêu chí mà tệp test VẪN in `ca` tự khai: từ chối, và từ chối TRƯỚC khi ghi
        # kho. Nhận im lặng thì tiêu chí thành một tờ giấy dán tường — nó có, đã được người
        # dùng xác nhận, và không phán gì cả; mà hiện vật thì mang `che_do="eide_phan"`.
        if tc is not None and kq.chay_duoc and kq.co_ca_tu_khai:
            return ToolResult(False, error=EideError(
                "E4024",
                f"Tệp test in kết luận TỰ KHAI (`ca`) trong khi đã có tiêu chí {tc.ma}.",
                hint_for_agent=(
                    "Đã có tiêu chí thì tệp test chỉ ĐO, không phán. Bỏ mảng `ca` đi và in số "
                    "đo:\n" + MP.KHUON_SO_DO + "\nMã assert tiêu chí này đòi: "
                    + ", ".join(a.ma for a in tc.asserts[:10]) + "."),
                details={"ma_tieu_chi": tc.ma,
                         "assert_doi": [a.ma for a in tc.asserts],
                         "so_do_nhan_duoc": sorted(kq.so_do),
                         "nguyen_van": kq.nguyen_van[-600:]},
                alternatives=["fs.edit", "test.criteria"], blame="agent"))

        # DEV-336 / E4023 — số đo không chứa MỘT mã assert nào. Đây KHÔNG phải sản phẩm sai,
        # mà là sai cặp tiêu chí/tệp test: hai chuyện ấy dẫn tới hai việc ngược nhau. Cùng
        # cái bẫy đã bắt được ở `sim.run`, và ở đây nó dễ trúng hơn vì `nguon` bỏ trống thì
        # lấy MỌI tệp `test/*.c`.
        if tc is not None and kq.chay_duoc and tc.asserts and not (
                set(kq.so_do) & {a.ma for a in tc.asserts}):
            return ToolResult(False, error=EideError(
                "E4023",
                f"Số đo không chứa MỘT mã assert nào của tiêu chí {tc.ma}. "
                f"Tiêu chí đòi {sorted(a.ma for a in tc.asserts)[:8]}, "
                f"tệp test in ra {sorted(kq.so_do)[:8]}.",
                hint_for_agent=(
                    "Đây KHÔNG phải sản phẩm sai — là sai cặp tiêu chí/tệp test. Hai chỗ hay "
                    "lệch: `ma_tieu_chi` trỏ sang bộ tiêu chí khác, và `nguon` bỏ trống thì "
                    "lấy MỌI tệp `test/*.c` nên có hai bộ test là phải nêu đúng tệp. Nêu cả "
                    "hai rồi gọi lại — đừng sửa mã sản phẩm vì con số này.\n" + MP.KHUON_SO_DO),
                details={"ma_tieu_chi": tc.ma,
                         "assert_doi": sorted(a.ma for a in tc.asserts),
                         "so_do_nhan_duoc": sorted(kq.so_do),
                         "tep_nguon": kq.tep_nguon},
                alternatives=["test.criteria", "test.run"], blame="agent"))

        ctx.store.apply(
            artefact_id=MA_TEST, type="sim_result",
            op="update" if ctx.store.get(MA_TEST) else "create",
            author=f"agent:{ctx.run_id}", canonical=kq.to_dict(), explain=explain,
            view_hint={"kind": "table", "path": "test"})

        if not kq.chay_duoc:
            return ToolResult(False, error=EideError(
                "E4012", f"Test chưa chạy được: {kq.vi_sao_khong_dat}",
                hint_for_agent=("Sửa lỗi rồi chạy lại.\n"
                                + (kq.loi_bien_dich[-1200:] or MP.KHUON_RA)),
                details={"lenh": kq.lenh_bien_dich, "tep_da_dich": kq.tep_nguon},
                blame="agent"))

        # Chạy xong mà KHÔNG CA NÀO là một thất bại, không phải một kết quả rỗng vô hại.
        # Trả thành công ở đây thì tác tử đọc được "0/0 ca đạt" — một câu không có ô đỏ nào —
        # và lời chỉ khuôn đầu ra nằm trong `vi_sao_khong_dat` không bao giờ tới tay nó. Đúng
        # chỗ N6 cấm: im lặng không được phép đọc thành đạt.
        if kq.so_ca == 0:
            return ToolResult(False, error=EideError(
                "E4014", "Test chạy xong nhưng KHÔNG đếm được ca nào.",
                hint_for_agent=kq.vi_sao_khong_dat,
                details={"tep_da_dich": kq.tep_nguon,
                         "nguyen_van": kq.nguyen_van[-800:]},
                alternatives=["fs.edit", "test.sensitivity"], blame="agent"))

        phu = kq.do_phu
        return {
            **kq.to_dict(),
            "note_vi": (
                f"{kq.so_dat}/{kq.so_ca} ca đạt"
                + (f", {kq.so_hong} ca HỎNG: {kq.vi_sao_khong_dat}" if kq.so_hong else "")
                + ". "
                # M4-01 — chế độ đứng NGAY SAU con số, không nằm ở cuối. Con số là thứ được
                # đọc; nếu độ tin của nó nằm cách đó bốn câu thì nó không đi cùng con số.
                + (f"**EIDE phán** theo tiêu chí {tc.ma} ({len(tc.asserts)} assert, người "
                   "dùng đã xác nhận) — tệp test chỉ in số đo. " if tc is not None else
                   "Con số này là lời **TỰ KHAI** của chính tệp test: nó tự in `dat`, nên "
                   "thứ đang bị kiểm cũng là thứ tuyên bố kết quả — độ tin ĐỎ cho một kết "
                   "luận nghiệm thu. Muốn EIDE phán thì nêu tiêu chí bằng `test.criteria` "
                   "rồi gọi lại với `ma_tieu_chi`. ")
                + (f"Độ phủ dòng {phu.get('dong')}. " if phu.get("do_duoc") else
                   f"CHƯA đo được độ phủ — {phu.get('vi_sao', '')} ")
                + _noi_da_dich(goc, ds, tep_test)
                + ("Test chạy trên máy chủ với phần cứng thay bằng mock: nó kiểm LOGIC, "
                   "không kiểm định thời và không kiểm thanh ghi."))}


# --------------------------------------------------------------------------- phụ trợ
# Dấu hiệu "lỗi này là vì thiếu FPU phần cứng". Lấy từ chính câu chữ của trình dịch và của
# FreeRTOS, không đoán theo tên tệp.
_DAU_HIEU_FPU = ("hardware floating point", "floating point support", "__FPU_USED",
                 "fpu is not enabled", "-mfloat-abi", "vfp")


def _goi_y_fpu(loi: list[Any], fpu: str) -> str:
    """Chỉ đường tới tham số `fpu=` khi lỗi biên dịch nói về dấu phẩy động phần cứng.

    Vì sao cần, đo được trên phiên FreeRTOS: port `ARM_CM4F` của FreeRTOS dừng ở
    `#error This port can only be used when the project options are configured to enable
    hardware floating point support.` Câu ấy đúng, nhưng nó nói về *project options* của
    FreeRTOS — trong khi thứ phải đổi nằm ở **lời gọi `build.compile`**. Tác tử đọc nó rất
    dễ đi sửa `FreeRTOSConfig.h`, hoặc tệ hơn, đổi sang port không-FPU: cả hai đều sai, vì
    STM32F469 **có** FPU.
    """
    if fpu:
        return ""          # đã truyền rồi thì lỗi nằm ở chỗ khác, đừng chỉ nhầm đường
    t = " ".join(str(getattr(x, "thong_diep", "") or getattr(x, "vi", "")) for x in loi[:40])
    if not any(d in t.lower() for d in _DAU_HIEU_FPU):
        return ""
    return ("\n\nLỖI NÀY NÓI VỀ DẤU PHẨY ĐỘNG PHẦN CỨNG. EIDE mặc định dịch với "
            "`-mfloat-abi=soft` — cố ý, vì bật hard-float trên một chip KHÔNG có FPU thì "
            "chương trình hard-fault ở lệnh dấu phẩy động đầu tiên, và lỗi ấy chỉ hiện lúc "
            "chạy thật.\n"
            "Chip này có FPU thì truyền thẳng vào `build.compile`: `fpu=\"fpv4-sp-d16\"` "
            "(Cortex-M4F). ĐỪNG sửa cấu hình thư viện và ĐỪNG đổi sang port không-FPU để "
            "lách — cả hai đều giấu mất việc chip có FPU mà ta không dùng.\n"
            "Và ghim một Fact nói chip có FPU, kèm nguồn: con số ấy sẽ được dùng lại.")


def _ho_chieu(ctx: Any) -> dict[str, Any] | None:
    for a in ctx.store.list("passport", limit=5):
        return a.get("canonical") or {}
    return None


def _han_muc(ctx: Any, hc: dict[str, Any] | None) -> tuple[int, int]:
    """Hạn mức Flash/SRAM lấy từ FACT (có nguồn), không từ trí nhớ về chip.

    Không có Fact thì trả 0 và công cụ nói thẳng là chưa biết firmware có vừa chip không —
    thà không kết luận còn hơn kết luận bằng một con số nhớ được.
    """
    from ..knowledge.docs import PHAM_VI_HOP_LY, doc_so, ve_don_vi_co_ban

    def _so(khoa: str) -> int:
        for f in ctx.store.query_facts(key=khoa, limit=20):
            v = doc_so(f.get("value"))
            if v is None:
                continue
            dv = str(f.get("unit") or "")
            # `KB`/`K` trong tài liệu chip là 1024, không phải 1000 — `ve_don_vi_co_ban` dùng
            # bội số thập phân (đúng cho Hz, sai cho bộ nhớ), nên bộ nhớ tính riêng ở đây.
            if dv.upper() in ("KB", "K"):
                v = v * 1024
            elif dv:
                v = ve_don_vi_co_ban(v, dv)
            # Phanh cuối: một Fact vô lý KHÔNG được thành hạn mức. Đo được trên bo STM32F469:
            # mẫu "FLASH Size" khớp vào dòng khai địa chỉ thanh ghi `FLASHSIZE_BASE` và sinh
            # ra `flash.size = 7`; `build.compile` lấy 7 làm trần rồi báo một firmware 224
            # byte chiếm **320 % Flash**. Một con số vô lý đi tiếp được vào mọi phép tính
            # phía sau mà không ai chặn — thà không có hạn mức còn hơn có hạn mức sai.
            lo, hi = PHAM_VI_HOP_LY.get(khoa, (1.0, float("inf")))
            if lo <= v <= hi:
                return int(v)
        return 0

    return _so("flash.size"), _so("ram.size")

# Tệp logic dịch được trên máy chủ: không kéo theo header của bo.
#
# Vì sao cần: bản trước chỉ gom `firmware/control*.c` — một cái tên nghĩ ra từ một dự án
# khác. Dự án FreeRTOS đặt logic ở `ui_state.c`, nên `test.run` không liên kết nó vào, tệp
# test báo "thiếu ký hiệu", và tác tử **chép logic sang tệp test** để có thứ mà chạy. Bộ
# kiểm thành ra xanh mãi mãi. Một cái tên tệp đoán sẵn đã đẻ ra một ô xanh giả.
_HEADER_CUA_BO = ("stm32", "stm32469i_discovery", "cmsis", "core_cm", "FreeRTOS.h", "bsp",
                  "hal_", "nrf", "esp_", "driverlib")


def _logic_dich_duoc_tren_may(goc: Any) -> list[Any]:
    """Nhặt các tệp `.c` trong `firmware/` KHÔNG `#include` header của bo.

    Nhặt theo **tính chất đo được** (nó có kéo header phần cứng không) chứ không theo tên
    tệp. Tệp nào kéo header thì bỏ qua — và chỗ bỏ qua ấy được nói ra ở `note_vi`, vì "bộ
    kiểm không chạm tới nó" là một điều người đọc cần biết, không phải một chi tiết nội bộ.
    """
    import re as _re
    ra = []
    fw = goc / "firmware"
    if not fw.exists():
        return ra
    for p in sorted(fw.glob("*.c")):
        if p.name in ("startup.c", "libc_stub.c", "main.c"):
            continue                       # main() trùng với main() của tệp test
        try:
            t = p.read_text("utf-8", errors="replace")
        except OSError:
            continue
        inc = _re.findall(r'^\s*#\s*include\s*[<"]([^>"]+)', t, _re.M)
        if any(any(k.lower() in h.lower() for k in _HEADER_CUA_BO) for h in inc):
            continue
        ra.append(p)
    return ra[:12]

def _noi_da_dich(goc: Any, ds: list[Any], tep_test: list[Any]) -> str:
    """Nói ra bộ kiểm vừa dịch CÙNG những tệp sản phẩm nào, và bỏ qua tệp nào vì sao.

    Không có câu này thì `12/12 ca đạt` đọc như "sản phẩm đã được kiểm", trong khi nó có
    thể chỉ có nghĩa "tệp test tự kiểm chính nó".
    """
    sp = [p.name for p in ds if p not in tep_test]
    fw = goc / "firmware"
    bo = ([p.name for p in sorted(fw.glob("*.c"))
           if p.name not in sp and p.name not in ("startup.c", "libc_stub.c")]
          if fw.exists() else [])
    if not sp:
        return ("Bộ kiểm KHÔNG dịch cùng tệp mã sản phẩm nào — nó chỉ chạy mã nằm trong "
                "chính tệp test, nên các ô xanh trên không nói gì về sản phẩm. "
                + (f"Bỏ ngoài: {', '.join(bo[:8])}. " if bo else ""))
    return ("Dịch cùng mã sản phẩm: " + ", ".join(sp) + ". "
            + (f"Ngoài tầm (kéo header của bo, chưa kiểm được trên máy chủ): "
               f"{', '.join(bo[:8])}. " if bo else ""))
