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
MA_SIM = "sim_result:can-bang"


def _ma_tc(ma: str) -> str:
    return f"criteria:{ma or 'sim-01'}"


def _bay_gio() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        thieu = [f"assert #{i + 1}" for i, a in enumerate(ds)
                 if not a.get("ma") or not a.get("mo_ta")]
        if not ds or thieu:
            return ToolResult(False, error=EideError(
                "E4007",
                "Tiêu chí phải có ít nhất một assert, và mỗi assert phải có `ma` và `mo_ta`."
                + (" Thiếu: " + ", ".join(thieu) if thieu else ""),
                hint_for_agent=("`ma` là thứ số đo của chương trình mô phỏng trỏ tới (ví dụ "
                                "A1); `mo_ta` là câu người đọc hiểu. Thiếu một trong hai thì "
                                "kết quả sau này không ai đọc được."),
                blame="agent"))

        xau = [a for a in ds
               if str(a.get("phep_so") or "<=") not in TC.PHEP_SO]
        if xau:
            return ToolResult(False, error=EideError(
                "E4007", "Phép so không hợp lệ: "
                         + ", ".join(str(a.get("phep_so")) for a in xau),
                hint_for_agent="Chỉ nhận: " + ", ".join(TC.PHEP_SO),
                blame="agent"))

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
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=_ma_tc(moi.ma), type="criteria",
            op="update" if cu else "create", canonical=moi.to_dict(), explain=explain,
            run_id=ctx.run_id)
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
    @r.tool("test.run", "Mô phỏng",
            "Chạy unit test của firmware trên MÁY CHỦ (phần cứng thay bằng mock): bao nhiêu "
            "ca đạt, ca nào hỏng và vì sao, và độ phủ nếu đo được.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "array", "items": {"type": "string"},
                           "description": "tệp .c cần biên dịch cùng nhau; mặc định "
                                          "test/*.c + firmware/control*.c"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", core=False, needs_explain=True, writes_artefact=True,
            produces=["sim_result"],
            keywords=["test", "unit test", "kiểm thử", "độ phủ", "mock"])
    def test_run(ctx: Any, explain: dict[str, Any], nguon: list[str] | None = None):
        """TC052 — *"Test chạy trên máy chủ, có báo cáo đạt/không đạt và độ phủ"*.

        Hai điều công cụ này từ chối làm: nhận một bản báo cáo bằng lời (không đếm được), và
        im lặng bỏ cột độ phủ khi không đo được (người đọc sẽ hiểu là không có gì để nói).
        """
        from ..build import mo_phong as MP

        goc = ctx.config.paths.project_root
        # Tệp TEST phải có ít nhất một cái. Mã logic đi kèm để liên kết, nhưng một mình nó
        # không phải một bộ test — bản trước gom cả `control.c` vào rồi báo "không biên dịch
        # được" (đúng: nó không có main()), trong khi câu đúng là "chưa có test nào".
        tep_test = ([(goc / x) for x in nguon] if nguon else
                    sorted((goc / "test").glob("*.c")) + sorted((goc / "tests").glob("*.c")))
        tep_test = [x for x in tep_test if x.exists()]
        ds = tep_test + ([] if nguon else
                         [x for x in sorted((goc / "firmware").glob("control*.c"))
                          if x.exists()])
        if not tep_test:
            return ToolResult(False, error=EideError(
                "E4011", "Chưa có tệp test nào (test/*.c hoặc tests/*.c).",
                hint_for_agent=(
                    "Viết test cho phần LOGIC của firmware — phần không đụng thanh ghi. Mỗi "
                    "tệp test có main() in ra một dòng JSON "
                    '{"ca": [{"ten": "...", "dat": true, "vi": "..."}]}. '
                    "Chưa có test thì nói thẳng là chưa có, đừng coi im lặng là đạt."),
                alternatives=["fs.write", "fs.glob"], blame="agent"))

        kq = MP.chay_test(goc=goc, nguon=ds)
        ctx.store.apply(
            artefact_id=MA_TEST, type="sim_result",
            op="update" if ctx.store.get(MA_TEST) else "create",
            author=f"agent:{ctx.run_id}", canonical=kq.to_dict(), explain=explain,
            view_hint={"kind": "table", "path": "test"})

        if not kq.chay_duoc:
            return ToolResult(False, error=EideError(
                "E4012", f"Test chưa chạy được: {kq.vi_sao_khong_dat}",
                hint_for_agent=("Sửa lỗi rồi chạy lại.\n" + kq.loi_bien_dich[-1200:]),
                details={"lenh": kq.lenh_bien_dich}, blame="agent"))

        phu = kq.do_phu
        return {
            **kq.to_dict(),
            "note_vi": (
                f"{kq.so_dat}/{kq.so_ca} ca đạt"
                + (f", {kq.so_hong} ca HỎNG: {kq.vi_sao_khong_dat}" if kq.so_hong else "")
                + ". "
                + (f"Độ phủ dòng {phu.get('dong')}. " if phu.get("do_duoc") else
                   f"CHƯA đo được độ phủ — {phu.get('vi_sao', '')} ")
                + ("Test chạy trên máy chủ với phần cứng thay bằng mock: nó kiểm LOGIC, "
                   "không kiểm định thời và không kiểm thanh ghi."))}


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
    from ..knowledge.docs import PHAM_VI_HOP_LY, ve_don_vi_co_ban

    def _so(khoa: str) -> int:
        for f in ctx.store.query_facts(key=khoa, limit=20):
            gt = f.get("value")
            try:
                v = float(str(gt).replace(".", "").replace(",", "."))
            except (TypeError, ValueError):
                continue
            dv = str(f.get("unit") or "")
            v = ve_don_vi_co_ban(v, dv) if dv else v
            if dv.upper() in ("KB", "K"):
                v = float(str(gt).replace(",", ".")) * 1024
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
