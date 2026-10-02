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
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "explain"]},
            risk="R1", core=False, needs_explain=True, writes_artefact=True,
            keywords=["mô phỏng", "testbench", "verilog", "simulation", "pass fail",
                      "số chu kỳ", "verilator", "iverilog"])
    def hdl_sim(ctx: Any, explain: dict[str, Any], nguon: str, dinh: str = "",
                bo_may: str = "iverilog", dinh_nghia: dict[str, str] | None = None):
        from ..build import hdl as H

        goc = _goc(ctx)
        kq = H.mo_phong(goc=goc, nguon=goc / nguon, dinh=dinh, bo_may=bo_may,
                        ra=_thu_muc_hdl(ctx), dinh_nghia=dinh_nghia,
                        lenh_mo_rong=_lenh_mo_rong_cua_firmware(ctx))
        _ghi_kho(ctx, explain, kq, "sim")
        if not kq.dat:
            return _loi_chang(kq, (
                "Nếu testbench không in gì: đó là lỗi của testbench, không phải của thiết kế. "
                "Thêm `$display(\"PASS\")` / `$display(\"FAIL ...\")` kèm điều kiện kiểm, và "
                "nhớ `$finish`. Nếu in FAIL: đọc dòng ngay trước nó để biết ca nào trượt."))
        return {**kq.to_dict(),
                "note_vi": f"Testbench in PASS sau {kq.giay:.1f} s bằng {kq.cong_cu}."}

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
                          ra=_thu_muc_hdl(ctx))
        _ghi_kho(ctx, explain, kq, "pnr")
        if not kq.dat:
            return _loi_chang(kq, (
                "Nếu thiếu tệp mạng cổng: chạy `hdl.synth` trước. Nếu không đạt định thời: "
                "đường tổ hợp dài nhất quá dài — chia nó bằng thanh ghi, hoặc hạ tần số và "
                "NÓI RA rằng đã hạ."))
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
