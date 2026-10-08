# -*- coding: utf-8 -*-
"""Công cụ `hdl.*` — từ Verilog tới tệp cấu hình nạp được vào FPGA.

Năm công cụ, bốn chặng của luồng, cộng một chặng soát trước cho rẻ:

    hdl.lint ─▶ hdl.sim ─▶ hdl.synth ─▶ hdl.pnr ─▶ hdl.bitstream ─▶ target.flash

Nhóm này viết quanh cùng một câu như `build.*`: **không có bằng chứng thì không có kết luận.**
Mỗi chặng chỉ "đạt" khi có tệp ra trên đĩa và tệp ấy không rỗng; con số tài nguyên và Fmax đọc
từ nguyên văn công cụ; kết quả mô phỏng do chính testbench in ra.

Chỗ khác `build.*`: ở đây **mỗi chặng ăn đầu ra của chặng trước**, nên một chặng báo xong sai
sẽ kéo cả dây. Vì thế chặng nào cũng kiểm đầu vào của mình có thật không trước khi chạy, thay
vì để công cụ bên dưới báo một lỗi khó đọc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

MA_HDL = "build:hdl"


def _goc(ctx: Any) -> Path:
    # `ctx.config.paths.project_root`, KHÔNG phải `ctx.project_root` — bản đầu viết nhầm và cả
    # năm công cụ đổ với `E5999 AttributeError`, một mã lỗi không nói được gì cho tác tử.
    # Bộ kiểm trước đó chỉ gọi lớp lõi nên không đụng tới lớp bọc; ca
    # `test_cong_cu_hdl_goi_duoc_qua_registry` nay canh chỗ này.
    return Path(ctx.config.paths.project_root).resolve()


def _thu_muc_hdl(ctx: Any) -> Path:
    d = _goc(ctx) / ".eide" / "hdl"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lenh_mo_rong_cua_firmware(ctx: Any) -> dict[str, int]:
    """Lệnh mở rộng mà mã máy nạp vào lõi mềm CÓ THẬT dùng, đọc từ `build:firmware`.

    Tác tử không phải tự nhớ con số này, và không phải tự nghĩ ra việc đối chiếu nó với
    `dinh_nghia`. Đường dẫn tới dữ kiện phải tự nối — một dữ kiện có trong kho mà không
    đường nào dẫn tới nó thì bằng không có.
    """
    try:
        muc = ctx.store.get("build:firmware")
    except Exception:
        return {}
    if not muc:
        return {}
    goc = getattr(muc, "canonical", None) or (muc.get("canonical") if isinstance(muc, dict) else None)
    if not isinstance(goc, dict):
        return {}
    ra = goc.get("lenh_mo_rong")
    return ra if isinstance(ra, dict) else {}


def _fact_chan_kit(ctx: Any, bo_kit: str) -> dict[str, dict[str, str]]:
    """M3-18 — bản đồ chân của kit, đọc từ Fact `pin:<kit>.<số chân>`.

    Khoá trả về là **số chân** dạng chuỗi, vì `.cst` nói bằng số chân (`IO_LOC "led[0]" 15;`)
    chứ không nói bằng tên chức năng. Khớp hai bên qua số chân là chỗ duy nhất hai tài liệu
    chắc chắn dùng cùng một từ vựng.

    Không có Fact nào thì trả `{}`, và `cst.kiem` sẽ **khai ra** là đã bỏ phần đối chiếu kit
    thay vì im lặng — một phép kiểm im lặng khi thiếu dữ liệu sẽ được đọc thành "đã kiểm, không
    sao cả". Đo ngày 08/10/2026: **không kho nào** trong `du-lieu/` có Fact `pin:tangnano20k.*`,
    nên hôm nay hai luật ấy chưa nổ được trên dữ liệu thật — xem DEV-345.
    """
    try:
        ds = ctx.store.query_facts(subject=f"pin:{bo_kit}.", limit=400) or []
    except Exception:
        return {}
    ra: dict[str, dict[str, str]] = {}
    for f in ds:
        chu_de = str(f.get("subject") or "")
        so = chu_de.rsplit(".", 1)[-1].strip()
        if not so:
            continue
        ra.setdefault(so, {})[str(f.get("key") or "")] = str(f.get("value") or "")
    return ra


def _ghi_kho(ctx: Any, explain: dict[str, Any], kq: Any, ten: str) -> None:
    """Ghi kết quả một chặng thành một mục trong kho, để tab và lịch sử thấy được."""
    ma = f"{MA_HDL}:{ten}"
    ctx.store.apply(
        artefact_id=ma, type="build",
        op="update" if ctx.store.get(ma) else "create",
        author=f"agent:{ctx.run_id}", explain=explain,
        canonical=kq.to_dict())


def _loi_chang(kq: Any, goi_y: str) -> ToolResult:
    """Lời từ chối của một chặng: nói ngắn chuyện gì, rồi đưa nguyên văn cho tác tử đọc."""
    return ToolResult(False, error=EideError(
        "E4030", kq.vi_sao_khong_dat or f"Chặng {kq.chang} không đạt.",
        hint_for_agent=(goi_y + "\n\nNguyên văn công cụ (đuôi):\n" + kq.nguyen_van[-1500:]),
        details={"chang": kq.chang, "lenh": kq.lenh, "ma_thoat": kq.ma_thoat,
                 "loi": kq.loi[:10]},
        blame="agent"))


def register(r: Registry) -> None:
    # ============================================================== soát cú pháp
    @r.tool("hdl.lint", "Mạch thật",
            "Soát cú pháp và lỗi cấu trúc trong Verilog bằng Verilator, KHÔNG tổng hợp và "
            "KHÔNG chạy. Rẻ (vài giây) và bắt được phần lớn lỗi mà nếu để tới chặng tổng hợp "
            "thì phải chờ vài phút mới biết.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "string",
                           "description": "thư mục hoặc tệp .v/.sv (tương đối so với dự án)"},
                 "dinh": {"type": "string", "description": "tên mô-đun đỉnh"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "explain"]},
            risk="R1", core=False, needs_explain=True,
            keywords=["verilog", "lint", "soát cú pháp", "hdl", "fpga", "verilator"])
    def hdl_lint(ctx: Any, explain: dict[str, Any], nguon: str, dinh: str = ""):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.lint(goc=goc, nguon=goc / nguon, dinh=dinh)
        if not kq.dat:
            return _loi_chang(kq, "Sửa từng lỗi theo tệp và dòng trong `loi`, rồi soát lại.")
        return {**kq.to_dict(),
                "note_vi": (f"Không lỗi. {len(kq.canh_bao)} cảnh báo — đọc chúng trước khi "
                            "tổng hợp: Verilator cảnh báo về chốt (latch) và tín hiệu nhiều "
                            "nguồn, hai thứ tổng hợp vẫn chạy được mà bo mạch thì không.")}

    # ============================================================== mô phỏng
    @r.tool("hdl.sim", "Mô phỏng",
            "Chạy testbench Verilog và đọc PASS/FAIL mà CHÍNH testbench in ra. Không kết "
            "luận từ việc chương trình chạy xong: testbench không in gì thì KHÔNG đạt. "
            "`bo_may=verilator` cho bài đo số chu kỳ (nhanh hơn Icarus nhiều bậc).",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "string", "description": "thư mục chứa rtl + testbench"},
                 "dinh": {"type": "string", "description": "tên mô-đun testbench"},
                 "bo_may": {"type": "string", "enum": ["iverilog", "verilator"],
                            "description": "iverilog (mặc định) | verilator (đo chu kỳ)"},
                 "dinh_nghia": {"type": "object",
                                "description": "macro truyền vào, ví dụ {\"SIM\": \"1\"}"},
                 "do_nhay": {"type": "object",
                             "description": "ĐÃ phá mã và chạy lại thì điền: "
                                            "{\"bat\": 7, \"tong\": 7}. Chỉ điền khi đã "
                                            "thật sự làm — con số này nói bộ kiểm canh được "
                                            "gì, và một con số bịa ra thì tệ hơn không có.",
                             "properties": {"bat": {"type": "integer"},
                                            "tong": {"type": "integer"}}},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "explain"]},
            risk="R1", core=False, needs_explain=True, writes_artefact=True,
            keywords=["mô phỏng", "testbench", "verilog", "simulation", "pass fail",
                      "số chu kỳ", "verilator", "iverilog"])
    def hdl_sim(ctx: Any, explain: dict[str, Any], nguon: str, dinh: str = "",
                bo_may: str = "iverilog", dinh_nghia: dict[str, str] | None = None,
                do_nhay: dict[str, int] | None = None):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.mo_phong(goc=goc, nguon=goc / nguon, dinh=dinh, bo_may=bo_may,
                        ra=_thu_muc_hdl(ctx), dinh_nghia=dinh_nghia,
                        lenh_mo_rong=_lenh_mo_rong_cua_firmware(ctx))
        # Độ nhạy đi THEO hiện vật, không chỉ trả về cho mô hình.
        #
        # `test.sensitivity` đã đo được chuyện này cho firmware C, nhưng nó không ghi hiện
        # vật nào — con số chỉ nằm trong hội thoại rồi mất. Nên khối A8.0 trên tab Mô phỏng
        # không có cách nào biết, và nó hiện "CHƯA ĐO" vĩnh viễn kể cả sau khi tác tử vừa
        # phá mã bảy lần.
        #
        # Một phép đo không vào kho thì lượt sau không ai biết nó từng xảy ra.
        if do_nhay and do_nhay.get("tong"):
            # M3-13 — ĐÁNH DẤU là lời khai. Không cấm: có lúc tác tử thật sự đã phá mã bằng
            # tay. Nhưng kho phải phân biệt được "đo bằng mã" với "khai bằng lời", vì hai
            # thứ ấy đáng tin khác nhau và khối A8.0 trước đây hiện chúng giống hệt nhau.
            kq.do_nhay = {"bat": int(do_nhay.get("bat") or 0),
                          "tong": int(do_nhay["tong"]), "do_bang": "tu_khai"}
        _ghi_kho(ctx, explain, kq, "sim")
        if not kq.dat:
            return _loi_chang(kq, (
                "Nếu testbench không in gì: đó là lỗi của testbench, không phải của thiết kế. "
                "Thêm `$display(\"PASS\")` / `$display(\"FAIL ...\")` kèm điều kiện kiểm, và "
                "nhớ `$finish`. Nếu in FAIL: đọc dòng ngay trước nó để biết ca nào trượt."))
        return {**kq.to_dict(),
                "note_vi": f"Testbench in PASS sau {kq.giay:.1f} s bằng {kq.cong_cu}."}

    @r.tool("hdl.sensitivity", "Mô phỏng",
            "ĐO độ nhạy testbench Verilog: phá mã RTL thật (đảo if, & thành |, hằng +1, "
            "posedge thành negedge, == thành !=) rồi chạy lại. Testbench in PASS vô điều "
            "kiện sẽ lộ ra — phá gì nó cũng xanh. Ghi số đo vào kho, thay con số tự khai.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "string", "description": "thư mục chứa rtl + testbench"},
                 "nguon_rtl": {"type": "array", "items": {"type": "string"},
                               "description": "các tệp .v SẢN PHẨM sẽ bị phá (không phải tb)"},
                 "dinh": {"type": "string", "description": "tên mô-đun testbench"},
                 "bo_may": {"type": "string", "enum": ["iverilog", "verilator"]},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "nguon_rtl", "explain"]},
            risk="R1", core=False, needs_explain=True, writes_artefact=True,
            keywords=["độ nhạy", "sensitivity", "đột biến", "mutation", "testbench",
                      "verilog", "phá mã"])
    def hdl_sensitivity(ctx: Any, explain: dict[str, Any], nguon: str,
                        nguon_rtl: list[str], dinh: str = "", bo_may: str = "iverilog"):
        from ..build import hdl as H

        goc = _goc(ctx)
        rtl = [goc / x for x in nguon_rtl]
        thieu = [str(p) for p in rtl if not p.is_file()]
        if thieu:
            return ToolResult(False, error=EideError(
                "E1002", "Không có tệp RTL: " + ", ".join(thieu),
                hint_for_agent="Nêu đường dẫn tương đối từ gốc dự án, ví dụ `rtl/dem.v`.",
                blame="agent"))

        r_do = H.do_do_nhay_hdl(goc=goc, rtl=rtl, nguon=goc / nguon, dinh=dinh,
                                bo_may=bo_may)
        if not r_do.get("bo_kiem_xanh_luc_dau"):
            return ToolResult(False, error=EideError(
                "E4030", r_do.get("vi_sao_khong_do_duoc") or "Không đo được độ nhạy.",
                hint_for_agent=("Bộ kiểm phải XANH trước khi đo độ nhạy — không thì không "
                                "phân biệt được ca đỏ vì đột biến với ca đỏ từ trước."),
                blame="agent"))

        bat = int(r_do["so_thay"])
        tong = bat + int(r_do["so_khong_thay"])
        # Ghi ĐÈ con số tự khai (nếu có) bằng con số đo được: một phép đo thắng một lời khai.
        cu = ctx.store.get(f"{MA_HDL}:sim")
        can = dict((cu or {}).get("canonical") or {})
        # M4-05 — số mutant bị BỎ vì không dịch được, đi cùng con số độ nhạy ở mọi chỗ. Một
        # "1/1" sau khi hai phép phá bị bỏ là câu đúng về mẫu số của nó và sai về điều người
        # đọc hiểu — cùng cái lỗi DEV-344 vừa sửa ở nhãn đơn vị.
        sb = int(r_do.get("so_mutant_khong_hop_le") or 0)
        can["do_nhay"] = {"bat": bat, "tong": tong, "do_bang": "ma",
                          "so_mutant_khong_hop_le": sb, "chi_tiet": r_do["tep"]}
        ctx.store.apply(
            artefact_id=f"{MA_HDL}:sim", type="build",
            op="update" if cu else "create", author=f"agent:{ctx.run_id}",
            explain=explain, canonical=can)
        return {
            "bat": bat, "tong": tong, "tep": r_do["tep"],
            "so_chua_do": r_do["so_chua_do"], "so_khong_nap": r_do["so_khong_nap"],
            "so_mutant_khong_hop_le": sb,
            "note_vi": (
                # Nói ra mẫu số là TỆP. Vòng đo dừng ở phép phá đầu tiên làm bộ kiểm đỏ,
                # nên "1/1" nghĩa là "1 trong 1 tệp RTL", KHÔNG phải "1 trong 1 phép phá"
                # — và càng không so được với con số kiểu "7/7 phép" của một bản đo tay.
                f"Độ nhạy ĐO ĐƯỢC: {bat}/{tong} tệp RTL bị phá thì testbench ĐỎ."
                + ("" if bat == tong else
                   f" Còn {tong - bat} tệp bị phá mà testbench **vẫn xanh** — nghĩa là "
                   "testbench không canh phần ấy, và chữ PASS của nó không nói gì về chúng.")
                + (f" {r_do['so_chua_do']} tệp chưa đo được." if r_do["so_chua_do"] else "")
                + (f" {sb} phép phá bị BỎ vì mutant không dịch được — chúng KHÔNG nằm trong "
                   "con số trên, và cũng không nói gì về testbench." if sb else ""))}

    # ============================================================== tổng hợp
    @r.tool("hdl.synth", "Mạch thật",
            "Tổng hợp Verilog thành mạng cổng cho chip Gowin (Yosys `synth_gowin`). Báo số "
            "LUT, FF, BSRAM, DSP ĐỌC TỪ bảng thống kê của Yosys — không ước lượng. Đạt chỉ "
            "khi có tệp mạng cổng trên đĩa và tệp ấy không rỗng.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "string", "description": "thư mục chứa mã RTL"},
                 "dinh": {"type": "string", "description": "tên mô-đun đỉnh"},
                 "bo_kit": {"type": "string",
                            "description": "tangnano20k (mặc định)"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "dinh", "explain"]},
            risk="R2", core=False, needs_explain=True, writes_artefact=True,
            produces=["build"],
            keywords=["tổng hợp", "synthesis", "yosys", "fpga", "lut", "tài nguyên", "gowin"])
    def hdl_synth(ctx: Any, explain: dict[str, Any], nguon: str, dinh: str,
                  bo_kit: str = "tangnano20k"):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.tong_hop(goc=goc, nguon=goc / nguon, dinh=dinh, bo_kit=bo_kit,
                        ra=_thu_muc_hdl(ctx))
        _ghi_kho(ctx, explain, kq, "synth")
        if not kq.dat:
            return _loi_chang(kq, (
                "Chạy `hdl.lint` trước nếu chưa — nó chỉ ra lỗi cú pháp nhanh hơn nhiều. Lỗi "
                "của Yosys phần lớn không có số dòng, nên đọc nguyên văn."))
        tn = {k: v for k, v in kq.tai_nguyen.items() if k != "chi_tiet"}
        return {**kq.to_dict(),
                "note_vi": (
                    "Tổng hợp xong: " + " · ".join(f"{k} {v}" for k, v in sorted(tn.items()))
                    + ". Đây là số ô SAU khi ánh xạ về chip, nhưng **chưa phải** số thật dùng "
                      "trên silicon — con số ấy do `hdl.pnr` báo, và nó thường khác.")}

    # ============================================== M3-18: kiểm ràng buộc chân trước khi dựng
    @r.tool("hdl.constraints_check", "Mạch thật",
            "KIỂM tệp ràng buộc chân `.cst` với cổng mô-đun đỉnh: cổng nào thiếu `IO_LOC`, "
            "ràng buộc nào thừa, hai cổng nào trùng chân, và chân nào lệch Fact của kit. "
            "Thiếu `IO_LOC` thì nextpnr TỰ CHỌN chân — bitstream dựng xong, mọi chặng báo "
            "đạt, và mạch nối sai chân. Chạy trước `hdl.pnr` để biết trước khi tốn 3 phút.",
            {"type": "object",
             "properties": {
                 "dinh": {"type": "string", "description": "tên mô-đun đỉnh (đã tổng hợp)"},
                 "cst": {"type": "string",
                         "description": "tệp ràng buộc chân, ví dụ constraints/tangnano20k.cst"},
                 "bo_kit": {"type": "string"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["dinh", "cst", "explain"]},
            risk="R1", core=False, needs_explain=True,
            keywords=["ràng buộc chân", "cst", "io_loc", "gán chân", "pinout fpga",
                      "constraints"])
    def hdl_constraints_check(ctx: Any, explain: dict[str, Any], dinh: str, cst: str,
                              bo_kit: str = "tangnano20k"):
        from ..build import hdl as H

        goc = _goc(ctx)
        tep_cst = goc / cst
        if not tep_cst.is_file():
            return ToolResult(False, error=EideError(
                "E1002", f"Không có tệp ràng buộc chân `{cst}`.",
                hint_for_agent="Nêu đường dẫn tương đối từ gốc dự án.", blame="agent"))

        r_do = H.kiem_rang_buoc_chan(json_mang=_thu_muc_hdl(ctx) / f"{dinh}.json",
                                     cst=tep_cst, dinh=dinh,
                                     fact_chan_kit=_fact_chan_kit(ctx, bo_kit))
        if not r_do.get("doc_duoc"):
            return ToolResult(False, error=EideError(
                # E4033, không phải E4031: `loop.py` đã dùng E4031 cho "chưa chạy, vì chờ
                # cổng". Hai chuyện khác nhau mang cùng một mã là một lời nói sai ở chỗ người
                # đọc không kiểm lại được. Đã trúng một lần ở M2-06 (E6010).
                "E4033", r_do.get("vi_sao") or "Không kiểm được ràng buộc chân.",
                hint_for_agent=("Cần tệp mạng cổng của `hdl.synth` để biết mô-đun đỉnh có "
                                "những cổng nào. Chạy `hdl.synth` trước."),
                blame="agent"))

        pt = r_do["phat_hien"]
        chan = r_do["blocker"]
        dem: dict[str, int] = {}
        for p in pt:
            dem[p["loai"]] = dem.get(p["loai"], 0) + 1
        return {
            "dat": not chan, "dinh": r_do["dinh"], "so_cong": len(r_do["cong"]),
            "phat_hien": pt, "so_theo_loai": dem, "loi_cu_phap": r_do["loi_cu_phap"],
            "note_vi": (
                (f"{len(chan)} chỗ CHẶN đường dựng: "
                 + "; ".join(p["thong_diep"] for p in chan)
                 if chan else
                 f"Không chỗ nào chặn. {len(r_do['cong'])} cổng của `{r_do['dinh']}` đều có "
                 "`IO_LOC`.")
                + (f" Còn {len(pt) - len(chan)} chỗ phải đọc (không chặn)."
                   if len(pt) > len(chan) else "")
                + (f" {len(r_do['loi_cu_phap'])} dòng `.cst` không đọc được."
                   if r_do["loi_cu_phap"] else ""))}

    # ============================================================== đặt-đi dây
    @r.tool("hdl.pnr", "Mạch thật",
            "Đặt-đi dây mạng cổng lên chip thật (nextpnr-himbaechel) và báo **Fmax thật đo "
            "được**. KHÔNG đạt nếu Fmax thấp hơn tần số định chạy: bitstream dựng từ một "
            "thiết kế không đạt định thời vẫn nạp được và vẫn chạy sai — sai kiểu lúc được "
            "lúc không, khó tìm nhất.",
            {"type": "object",
             "properties": {
                 "dinh": {"type": "string", "description": "tên mô-đun đỉnh (đã tổng hợp)"},
                 "cst": {"type": "string",
                         "description": "tệp ràng buộc chân, ví dụ constraints/tangnano20k.cst"},
                 "tan_so_mhz": {"type": "number", "description": "tần số định chạy, mặc định 27"},
                 "bo_kit": {"type": "string"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["dinh", "cst", "explain"]},
            risk="R2", core=False, needs_explain=True, writes_artefact=True,
            produces=["build"],
            keywords=["đặt đi dây", "place route", "nextpnr", "fmax", "định thời", "timing"])
    def hdl_pnr(ctx: Any, explain: dict[str, Any], dinh: str, cst: str,
                tan_so_mhz: float = 27.0, bo_kit: str = "tangnano20k"):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.dat_di_day(goc=goc, json_mang=_thu_muc_hdl(ctx) / f"{dinh}.json",
                          cst=goc / cst, bo_kit=bo_kit, tan_so_mhz=tan_so_mhz,
                          ra=_thu_muc_hdl(ctx),
                          fact_chan_kit=_fact_chan_kit(ctx, bo_kit))
        _ghi_kho(ctx, explain, kq, "pnr")
        if not kq.dat:
            return _loi_chang(kq, (
                "Nếu thiếu tệp mạng cổng: chạy `hdl.synth` trước. Nếu ràng buộc chân bị chặn: "
                "sửa tệp `.cst` cho đủ `IO_LOC`, và chạy `hdl.constraints_check` để xem lại "
                "trước khi tốn một lượt đặt-đi dây. Nếu không đạt định thời: đường tổ hợp dài "
                "nhất quá dài — chia nó bằng thanh ghi, hoặc hạ tần số và NÓI RA rằng đã hạ."))
        return {**kq.to_dict(),
                "note_vi": (f"Fmax {kq.fmax_mhz} MHz ≥ {tan_so_mhz} MHz cần chạy. Số tài "
                            "nguyên trong `tai_nguyen.dung` là số THẬT trên silicon, dùng nó "
                            "để báo cáo chứ không dùng số của `hdl.synth`.")}

    # ============================================================== đóng gói
    @r.tool("hdl.bitstream", "Mạch thật",
            "Đóng gói bố trí đã đi dây thành tệp `.fs` nạp được vào FPGA (gowin_pack). Tên "
            "chip đọc THẲNG từ tệp bố trí, không lấy từ bảng — nên không có đường nào sinh ra "
            "bitstream cho nhầm chip.",
            {"type": "object",
             "properties": {
                 "dinh": {"type": "string", "description": "tên mô-đun đỉnh (đã đặt-đi dây)"},
                 "bo_kit": {"type": "string"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["dinh", "explain"]},
            risk="R2", core=False, needs_explain=True, writes_artefact=True,
            produces=["build"],
            keywords=["bitstream", "gowin_pack", "đóng gói", "fs", "apicula"])
    def hdl_bitstream(ctx: Any, explain: dict[str, Any], dinh: str,
                      bo_kit: str = "tangnano20k"):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.dong_goi(goc=goc, pnr_json=_thu_muc_hdl(ctx) / f"{dinh}_pnr.json",
                        bo_kit=bo_kit, ra=_thu_muc_hdl(ctx))
        _ghi_kho(ctx, explain, kq, "bitstream")
        if not kq.dat:
            return _loi_chang(kq, (
                "Nếu thiếu tệp bố trí: chạy `hdl.pnr` trước."))
        return {**kq.to_dict(),
                "note_vi": (f"Có `{kq.tep_ra}`, {kq.so_byte_ra} byte, cho chip "
                            f"{kq.tai_nguyen.get('chip_doc_tu_tep_bo_tri')}. Nạp bằng "
                            "`target.flash` với `cach=\"openfpgaloader\"`.")}
