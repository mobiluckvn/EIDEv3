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
MA_SIM = "sim_result:can-bang"


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:
    # ====================================================================== biên dịch
    @r.tool("build.compile", "Mã nguồn",
            "Biên dịch firmware bằng chuỗi công cụ THẬT trên máy (arduino-cli hoặc avr-gcc). "
            "Trả lỗi kèm tệp:dòng:cột, và kích thước Flash/SRAM đọc từ avr-size. Không có "
            "tệp ảnh thì KHÔNG coi là xong.",
            {"type": "object",
             "properties": {
                 "sketch": {"type": "string",
                            "description": "thư mục sketch hoặc tệp nguồn, ví dụ firmware/"},
                 "isa": {"type": "string", "description": "avr8 — mặc định lấy từ hộ chiếu"},
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
                      isa: str = ""):
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

        kq = TC.bien_dich(goc=goc, sketch=p, isa=isa,
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
                       if len(kq.loi) > 12 else "")),
                details={"loi": [x.to_dict() for x in kq.loi[:40]],
                         "nguyen_van": kq.nguyen_van[-2000:],
                         "cong_cu": kq.cong_cu, "lenh": kq.lenh},
                alternatives=["fs.read", "fs.edit"], blame="agent"))

        qua_flash = flash_max and kq.flash > flash_max
        qua_sram = sram_max and kq.sram > sram_max
        return {
            **kq.to_dict(),
            "vua_chip": not (qua_flash or qua_sram),
            "note_vi": (
                f"Biên dịch xong bằng {kq.cong_cu}: {kq.tep_ra}. "
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
                + (" VƯỢT hạn mức bộ nhớ của chip." if (qua_flash or qua_sram) else ""))}

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
                tham_so: list[str] | None = None):
        from ..build import mo_phong as MP

        goc = ctx.config.paths.project_root
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

        kq = MP.chay_mo_phong(goc=goc, nguon=ds, tham_so=tham_so)
        ctx.store.apply(
            artefact_id=MA_SIM, type="sim_result",
            op="update" if ctx.store.get(MA_SIM) else "create",
            author=f"agent:{ctx.run_id}", canonical=kq.to_dict(), explain=explain,
            view_hint={"kind": "table", "path": "sim"})

        if not kq.chay_duoc:
            return ToolResult(False, error=EideError(
                "E4004", f"Mô phỏng chưa chạy được: {kq.vi_sao_khong_dat}",
                hint_for_agent=("Sửa lỗi biên dịch của phần mô phỏng rồi chạy lại.\n"
                                + kq.loi_bien_dich[-1200:]),
                details={"lenh": kq.lenh_bien_dich}, blame="agent"))

        d = kq.ket_qua
        return {
            **kq.to_dict(),
            "note_vi": (
                ("Mô phỏng ĐẠT. " if kq.dat else
                 f"Mô phỏng CHƯA đạt: {kq.vi_sao_khong_dat}. ")
                + (f"Chạy {d.get('thoi_gian_s', '?')} s mô phỏng, "
                   f"góc lớn nhất {d.get('goc_max_do', '?')}°, "
                   f"góc cuối {d.get('goc_cuoi_do', '?')}°"
                   if d else "")
                + (". Đây là kết quả trên MÔ HÌNH: nó nói mã điều khiển tự nhất quán và ổn "
                   "định được với mô hình đó, KHÔNG nói robot thật sẽ đứng — tham số cơ khí "
                   "thật phải đo trên bo (tài liệu bàn giao gọi là hạng L).")),
        }


# --------------------------------------------------------------------------- phụ trợ
def _ho_chieu(ctx: Any) -> dict[str, Any] | None:
    for a in ctx.store.list("passport", limit=5):
        return a.get("canonical") or {}
    return None


def _han_muc(ctx: Any, hc: dict[str, Any] | None) -> tuple[int, int]:
    """Hạn mức Flash/SRAM lấy từ FACT (có nguồn), không từ trí nhớ về chip.

    Không có Fact thì trả 0 và công cụ nói thẳng là chưa biết firmware có vừa chip không —
    thà không kết luận còn hơn kết luận bằng một con số nhớ được.
    """
    def _so(khoa: str) -> int:
        for f in ctx.store.query_facts(key=khoa, limit=20):
            gt = f.get("value")
            try:
                v = float(str(gt).replace(".", "").replace(",", "."))
            except (TypeError, ValueError):
                continue
            dv = str(f.get("unit") or "").upper()
            if dv in ("KB", "K"):
                v *= 1024
            if v > 0:
                return int(v)
        return 0

    return _so("flash.size"), _so("ram.size")
