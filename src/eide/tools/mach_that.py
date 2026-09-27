# -*- coding: utf-8 -*-
"""Công cụ mạch thật (G7): dò bo, nạp, đọc log. MDD-40 §B1 nhóm "Build/Sim/Target".

  `target.detect`  liệt kê những gì ĐANG cắm và nói rõ biết bằng cách nào. Không có bo thì trả
                   danh sách kiểm tra bốn mục (TC032), không đoán.
  `target.flash`   R4, cổng G-FLASH, changeset **không hoàn tác được**. Đối chiếu chip trước
                   khi nạp (TC034); không đối chiếu được thì nói ra và đòi người dùng xác nhận
                   tường minh, chứ không lặng lẽ bỏ qua phép kiểm.
  `target.log`     đọc cổng nối tiếp có thời hạn. Im lặng là im lặng, không phải "firmware sai".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

MA_NAP = "target:flash"
MA_LOG = "target:log"


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def _ho_chieu(ctx: Any) -> dict[str, Any] | None:
    from .xay_dung import _ho_chieu as hc

    return hc(ctx)


def dang_ky(r: Registry) -> None:
    @r.tool("target.detect", "Mạch thật",
            "Dò xem máy này đang cắm bo nào: ổ đĩa của bộ nạp, cổng nối tiếp, và ID chip đọc "
            "qua SWD nếu có công cụ. Nói rõ từng thứ biết được BẰNG CÁCH NÀO, và phân biệt "
            "“mã chip suy từ nhãn ổ đĩa” với “ID chip đọc từ silicon”.",
            {"type": "object", "properties": {}},
            risk="R1", core=False,
            keywords=["dò bo", "board", "bộ nạp", "st-link", "cổng", "usb", "detect",
                      "mạch thật", "chip id"])
    def target_detect(ctx: Any):
        from ..build import mach_that as MT

        d = MT.do_bo()
        hc = _ho_chieu(ctx) or {}
        chip_du_an = str(hc.get("chip") or "")
        doan = [t["chip_doan"] for t in d["thiet_bi"] if t["chip_doan"]]
        khop: str | None = None
        if chip_du_an and (d["chip_doc_duoc"] or doan):
            thay = d["chip_doc_duoc"] or doan[0]
            khop = "khop" if _cung_chip(chip_du_an, thay) else "lech"

        return {
            **d, "chip_du_an": chip_du_an, "khop_chip": khop,
            "note_vi": (
                (f"{d['so_co_the_la_bo']}/{d['so_thiet_bi']} thiết bị đang cắm có thể là bo. "
                 if d["so_thiet_bi"] else "Không có thiết bị nào đang cắm. ")
                + (f"Nạp được bằng: "
                   + ", ".join(sorted({t["nap_duoc_bang"] for t in d["thiet_bi"]
                                       if t["nap_duoc_bang"]})) + ". "
                   if d["nap_duoc"] else "KHÔNG có đường nạp nào. ")
                + (f"ID chip đọc được: {d['chip_doc_duoc']}. "
                   if d["chip_doc_duoc"] else
                   f"CHƯA đọc được ID chip ({d['vi_sao_chua_doc_duoc_chip']}). Mã chip suy từ "
                   f"nhãn ổ đĩa ({', '.join(doan) or 'không có'}) là bằng chứng về BO, không "
                   "phải về silicon — đừng trình bày nó như đã đọc từ chip. ")
                + ({"khop": f"Chip dự án ({chip_du_an}) khớp với thứ tìm thấy. ",
                    "lech": f"KHÁC NHAU: dự án ghim {chip_du_an} nhưng bo báo "
                            f"{d['chip_doc_duoc'] or (doan[0] if doan else '?')}. DỪNG, đừng "
                            "nạp — hỏi người dùng. ",
                    }.get(khop or "", ""))
                + ("Không thấy bo: đưa `danh_sach_kiem_tra` cho người dùng làm theo thứ tự, "
                   "và ĐỪNG báo nạp được." if d["danh_sach_kiem_tra"] else ""))}

    @r.tool("target.flash", "Mạch thật",
            "NẠP firmware vào bo thật. Không hoàn tác được: bản đang chạy trên chip bị ghi "
            "đè. Đối chiếu chip trước khi nạp; nếu không đọc được ID chip thì phải có "
            "`dong_y_khong_doi_chieu_chip=true` mới nạp.",
            {"type": "object",
             "properties": {
                 "tep": {"type": "string",
                         "description": "đường dẫn .bin (bỏ trống: .eide/build/mach.bin)"},
                 "cach": {"type": "string", "enum": ["tu_chon", "sao_tep", "st-flash"],
                          "description": "tu_chon = dùng st-flash nếu có, không thì sao tệp"},
                 "dong_y_khong_doi_chieu_chip": {
                     "type": "boolean",
                     "description": ("true = người dùng đã biết rằng KHÔNG đối chiếu được ID "
                                     "chip và vẫn muốn nạp")},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R4", gate="G-FLASH", needs_explain=True, produces=["target"],
            writes_artefact=True,
            keywords=["nạp", "flash", "ghi firmware", "program", "nạp bo", "nạp chip"])
    def target_flash(ctx: Any, explain: dict[str, Any], tep: str = "", cach: str = "tu_chon",
                     dong_y_khong_doi_chieu_chip: bool = False):
        from ..build import mach_that as MT

        goc = ctx.config.paths.project_root
        p = (goc / tep).resolve() if tep else (goc / ".eide" / "build" / "mach.bin")
        if not p.exists():
            return ToolResult(False, error=EideError(
                "E4001",
                f"Không có tệp {tep or '.eide/build/mach.bin'} để nạp.",
                hint_for_agent="Biên dịch trước (build.compile) — nó sinh mach.bin cho ARM.",
                alternatives=["build.compile"], blame="agent"))

        d = MT.do_bo()
        if not d["nap_duoc"]:
            return ToolResult(False, error=EideError(
                "E4011", "Không tìm thấy đường nào để nạp: máy không có bộ nạp nào đang cắm.",
                hint_for_agent=("Đưa danh sách kiểm tra dưới đây cho người dùng theo đúng thứ "
                                "tự. ĐỪNG báo nạp thành công.\n"
                                + "\n".join(f"{i+1}. {x}"
                                            for i, x in enumerate(d["danh_sach_kiem_tra"]))),
                details={"danh_sach_kiem_tra": d["danh_sach_kiem_tra"],
                         "thiet_bi": d["thiet_bi"]},
                alternatives=["target.detect"], blame="user"))

        # TC034 — đối chiếu chip TRƯỚC khi nạp.
        hc = _ho_chieu(ctx) or {}
        chip_du_an = str(hc.get("chip") or "")
        doan = [t["chip_doan"] for t in d["thiet_bi"] if t["chip_doan"]]
        thay_that = d["chip_doc_duoc"]
        thay_doan = doan[0] if doan else ""
        # CHỈ chặn khi chứng minh được là LỆCH. "Chưa so được" rơi xuống nhánh xin xác nhận
        # bên dưới — chặn vì không so được là một báo động giả, và báo động giả dạy người
        # dùng bấm qua cảnh báo.
        if chip_du_an and thay_that and so_chip(chip_du_an, thay_that) == "lech":
            return ToolResult(False, error=EideError(
                "E4012",
                f"DỪNG: dự án ghim chip {chip_du_an} nhưng bo đang cắm là {thay_that}.",
                hint_for_agent=("Không nạp. Nói cho người dùng biết hai mã chip khác nhau và "
                                "hỏi họ muốn gì: đổi hộ chiếu chip, hay cắm bo khác."),
                details={"chip_du_an": chip_du_an, "chip_tren_bo": thay_that},
                alternatives=["passport.pin", "target.detect"], blame="user"))
        if (chip_du_an and thay_doan and not thay_that
                and so_chip(chip_du_an, thay_doan) == "lech"):
            return ToolResult(False, error=EideError(
                "E4012",
                f"DỪNG: dự án ghim {chip_du_an} nhưng nhãn ổ đĩa của bộ nạp cho thấy bo là "
                f"{thay_doan}.",
                hint_for_agent=("Đây là nhãn ổ đĩa, không phải ID chip — nhưng nó đã đủ để "
                                "thấy KHÔNG khớp. Không nạp; hỏi người dùng."),
                details={"chip_du_an": chip_du_an, "chip_theo_nhan_o": thay_doan},
                alternatives=["passport.pin", "target.detect"], blame="user"))
        da_doi_chieu = bool(chip_du_an and thay_that
                            and so_chip(chip_du_an, thay_that) == "khop")
        if not da_doi_chieu and not dong_y_khong_doi_chieu_chip:
            return ToolResult(False, error=EideError(
                "E4013",
                "Chưa đối chiếu được ID CHIP: "
                + (str(d["vi_sao_chua_doc_duoc_chip"])
                   if d["vi_sao_chua_doc_duoc_chip"] else
                   (f"đọc được “{thay_that}” từ bo nhưng dự án chưa ghim chip nào để so"
                    if thay_that and not chip_du_an else
                    f"đọc được “{thay_that}” từ bo, không suy ra được nó có phải "
                    f"{chip_du_an} hay không" if thay_that else
                    "không đọc được qua SWD"))
                + ". MDD-40 đòi nạp phải đối chiếu ID chip.",
                hint_for_agent=(
                    "Hai đường đi, để NGƯỜI DÙNG chọn — đừng tự chọn:\n"
                    "1. Cài `st-info`/`st-flash` (tool.install, gói `stlink`) rồi nạp có đối "
                    "chiếu và có verify.\n"
                    "2. Nạp kiểu sao tệp mà KHÔNG đối chiếu ID chip: gọi lại với "
                    "`dong_y_khong_doi_chieu_chip=true`. Nói rõ với người dùng rằng khi đó "
                    "phép kiểm “đúng chip” chỉ dựa vào nhãn ổ đĩa"
                    + (f" (đang là {thay_doan})" if thay_doan else "")
                    + ", và việc nạp không hoàn tác được."),
                details={"chip_du_an": chip_du_an, "chip_theo_nhan_o": thay_doan,
                         "vi_sao": d["vi_sao_chua_doc_duoc_chip"]},
                alternatives=["tool.install", "target.flash"], blame="user"))

        # Chọn cách nạp.
        co_st = any(t["nap_duoc_bang"] == "st-flash" for t in d["thiet_bi"])
        o_dia = next((Path(t["duong_dan"]) for t in d["thiet_bi"]
                      if t["nap_duoc_bang"] == "sao_tep"), None)
        if cach == "st-flash" or (cach == "tu_chon" and co_st):
            kq = MT.nap_qua_st_flash(p)
        elif o_dia is not None:
            kq = MT.nap_qua_o_dia(p, o_dia)
        else:
            return ToolResult(False, error=EideError(
                "E4011", f"Không có cách nạp “{cach}” trên máy này.",
                hint_for_agent="Gọi target.detect để xem đường nạp nào đang có.",
                alternatives=["target.detect"], blame="agent"))

        kq.chip_da_doi_chieu = thay_that or ""
        ctx.store.apply(
            artefact_id=MA_NAP, type="target",
            op="update" if ctx.store.get(MA_NAP) else "create",
            author=f"agent:{ctx.run_id}", explain=explain,
            canonical={**kq.to_dict(), "chip_du_an": chip_du_an,
                       "chip_theo_nhan_o": thay_doan,
                       # §G7 — nạp không hoàn tác được, và changeset phải nói thế.
                       "reversible": False,
                       "vi_sao_khong_hoan_tac": "Ghi đè Flash của chip; bản cũ không còn."},
            view_hint={"kind": "kv", "path": kq.tep})

        if not kq.dat:
            return ToolResult(False, error=EideError(
                "E4014", f"Nạp KHÔNG thành công: {kq.vi_sao_khong_dat}",
                hint_for_agent=("Đọc nguyên văn dưới đây và nói lại đúng nguyên nhân. Nếu quá "
                                "trình nạp dừng giữa đường thì trạng thái Flash của chip "
                                "KHÔNG nhất quán — nói điều đó ra.\n" + kq.nguyen_van[-800:]),
                details=kq.to_dict(), alternatives=["target.detect", "target.flash"],
                blame="external"))
        return {
            **kq.to_dict(),
            "note_vi": (
                f"Đã nạp {kq.so_byte} byte ({kq.tep}, sha256 {kq.hash[:12]}) vào {kq.dich} "
                f"bằng {kq.cach} trong {kq.giay:.1f} s. "
                + ("Trình nạp đã VERIFY nội dung ghi. " if kq.da_verify
                   else "KHÔNG verify được nội dung đã ghi. ")
                + (f"Chip đã đối chiếu: {kq.chip_da_doi_chieu}. " if kq.chip_da_doi_chieu
                   else "Chip KHÔNG được đối chiếu bằng ID đọc từ silicon. ")
                + "Việc nạp KHÔNG hoàn tác được — bản firmware cũ trên chip đã mất. "
                + " ".join(kq.canh_bao))}

    @r.tool("target.log", "Mạch thật",
            "Đọc log từ cổng nối tiếp của bo trong một khoảng thời gian. Cổng im lặng thì nói "
            "là im lặng — đó KHÔNG phải bằng chứng firmware sai.",
            {"type": "object",
             "properties": {
                 "cong": {"type": "string",
                          "description": "ví dụ /dev/cu.usbmodem1103; bỏ trống thì tự chọn "
                                         "cổng USB duy nhất đang cắm"},
                 "baud": {"type": "integer", "description": "mặc định 115200"},
                 "giay": {"type": "number", "description": "đọc bao lâu, mặc định 5"}},
             "properties_required": [], "required": []},
            risk="R2", core=False,
            keywords=["log", "uart", "serial", "nối tiếp", "đọc log", "in ra", "printf"])
    def target_log(ctx: Any, cong: str = "", baud: int = 115200, giay: float = 5.0):
        from ..build import mach_that as MT

        if giay <= 0 or giay > 120:
            return ToolResult(False, error=EideError(
                "E5001", f"`giay` phải trong khoảng 0–120, nhận {giay}.",
                hint_for_agent="Đọc log lâu hơn 2 phút thì treo cả lượt làm việc.",
                blame="agent"))
        if not cong:
            d = MT.do_bo()
            ung = [t for t in d["thiet_bi"]
                   if t["loai"] == "cong_noi_tiep" and t["co_the_la_bo"]]
            if len(ung) != 1:
                return ToolResult(False, error=EideError(
                    "E4011",
                    (f"Có {len(ung)} cổng nối tiếp có thể là bo — không đoán dùng cổng nào."
                     if ung else "Không có cổng nối tiếp nào của bo đang cắm."),
                    hint_for_agent=("Gọi target.detect, trình danh sách cổng cho người dùng "
                                    "và hỏi họ chọn. Đừng đọc log từ một cổng không rõ là gì "
                                    "— tai nghe Bluetooth cũng hiện ra ở /dev/cu.*."),
                    details={"cong": [t["duong_dan"] for t in ung]},
                    alternatives=["target.detect"], blame="agent"))
            cong = ung[0]["duong_dan"]

        d = MT.doc_log(cong, baud=baud, giay=giay)
        if d.get("loi"):
            return ToolResult(False, error=EideError(
                "E4011", str(d["loi"]),
                hint_for_agent="Kiểm lại tên cổng bằng target.detect.",
                details=d, alternatives=["target.detect"], blame="user"))
        ctx.store.apply(
            artefact_id=MA_LOG, type="target",
            op="update" if ctx.store.get(MA_LOG) else "create",
            author=f"agent:{ctx.run_id}",
            canonical={k: v for k, v in d.items() if k != "chu"} | {"chu": d["chu"][-8000:]},
            explain={"summary": f"đọc log {cong}", "why": "xem firmware in gì khi chạy thật",
                     "sources": [cong], "diff_prev": "—", "next": "—", "confidence": "BAC"},
            view_hint={"kind": "log", "path": cong})
        return {
            **d,
            "note_vi": (
                f"Đọc {d['so_byte']} byte từ {cong} ở {baud} baud trong {giay:.0f} s. "
                + (" ".join(d["canh_bao"]) if d["canh_bao"] else
                   "Đây là nguyên văn bo in ra — dùng nó làm bằng chứng, đừng kể lại theo ý."))}


def so_chip(a: str, b: str) -> str:
    """Hai mã chip nói về cùng một con chip không. Trả `khop` | `lech` | `chua_so_duoc`.

    **Ba giá trị, không phải hai.** "Không chứng minh được là giống nhau" và "chứng minh được
    là khác nhau" dẫn tới hai hành động trái ngược: cái sau phải chặn việc nạp, cái trước chỉ
    được hỏi người dùng. Gộp chúng thành `False` là biến mọi chỗ không so được thành một lời
    buộc tội — đo được trên bo thật: `st-info` trả `chipid 0x434`, phép so cũ không hiểu mã
    số đó, và việc nạp bị **chặn bằng một báo động giả**. Một cảnh báo sai dạy người dùng bỏ
    qua cảnh báo.

    So lỏng có chủ ý ở nhánh `khop`: hộ chiếu ghi `STM32F469NIH6`, nhãn ổ đĩa khai
    `STM32F469NI`, `st-info` khai `STM32F46x_F47x`. Bắt khớp từng ký tự sẽ báo "sai chip" cho
    đúng con chip đang cắm.
    """
    import re

    def gon(x: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", x.upper())

    ga, gb = gon(a), gon(b)
    if not ga or not gb:
        return "chua_so_duoc"
    if ga.startswith(gb) or gb.startswith(ga):
        return "khop"
    # `STM32F469NIH6` vs `F46X_F47X`: lấy phần chữ+số đầu của mỗi bên rồi so tới chỗ có `X`.
    ma_a = re.search(r"([FLGHWU]\d{1,2}[0-9A-Z]*)", ga)
    ma_b = re.search(r"([FLGHWU]\d{1,2}[0-9A-Z]*)", gb)
    if not ma_a or not ma_b:
        # Một bên không có dạng mã chip nào nhận ra được (ví dụ chuỗi `CHIPID0X434`).
        return "chua_so_duoc"
    ta, tb = ma_a.group(1), ma_b.group(1)
    for i in range(min(len(ta), len(tb))):
        if tb[i] == "X" or ta[i] == "X":
            return "khop"
        if ta[i] != tb[i]:
            return "lech"
    return "khop"


def _cung_chip(a: str, b: str) -> bool:
    """Giữ cho chỗ gọi cũ. Chỉ `khop` mới là True — `chua_so_duoc` KHÔNG phải là khớp."""
    return so_chip(a, b) == "khop"
