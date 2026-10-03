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


def _goc_chip(s: str) -> str:
    """`st.atmega328p@1.0.0` hoặc `ATmega328P` → `ATmega328P`.

    Hộ chiếu chip ghi theo dạng `ns.part@semver`, còn bảng mã avrdude tra theo tên chip. Lấy
    nhầm cả chuỗi hộ chiếu thì tra không ra, và lúc ấy công cụ sẽ báo "không biết mã chip"
    cho một dự án đã ghim chip đàng hoàng.
    """
    from ..build import mach_that as MT

    t = str(s or "").split("@", 1)[0].rsplit(".", 1)[-1]
    thuong = t.lower()
    return next((x for x in MT._MA_AVRDUDE if x.lower() == thuong), t)


def _noi_avr(d: dict[str, Any]) -> str:
    """Câu về phần AVR. Nói rõ ĐÃ ĐỌC hay CHƯA ĐỌC, và việc đọc đã reset bo."""
    a = d.get("avr")
    if a is None:
        co_cong = any(t["loai"] == "cong_noi_tiep" and t["nap_duoc_bang"]
                      for t in d.get("thiet_bi", []))
        return ("Có cổng nạp AVR qua bootloader, nhưng CHƯA bắt tay với chip — cổng USB nối "
                "tiếp vẫn hiện ra kể cả khi không có chip trong đế. Muốn biết chắc thì gọi "
                "lại với `doc_chu_ky_avr=true`, và nói trước cho người dùng rằng việc đó "
                "RESET bo. " if co_cong else "")
    if a.get("doc_duoc"):
        return (f"ĐÃ ĐỌC chữ ký từ silicon qua bootloader: `{a['chu_ky']}` "
                f"→ {a.get('chip') or 'chip chưa có trong bảng'} "
                f"(cổng {a['cong']}, {a['baud']} baud). Bo đã bị RESET khi đọc. ")
    return (f"KHÔNG đọc được chữ ký AVR: {a.get('vi_sao', '')}. "
            "Hay gặp: sai tốc độ bootloader (bo cũ 57600, bo mới 115200), hoặc một chương "
            "trình khác đang giữ cổng. ")


def dang_ky(r: Registry) -> None:
    @r.tool("target.detect", "Mạch thật",
            "Dò xem máy này đang cắm bo nào: ổ đĩa của bộ nạp, cổng nối tiếp, và ID chip đọc "
            "qua SWD nếu có công cụ. Nói rõ từng thứ biết được BẰNG CÁCH NÀO, và phân biệt "
            "“mã chip suy từ nhãn ổ đĩa” với “ID chip đọc từ silicon”. Với bo AVR nạp qua "
            "bootloader (Arduino Nano/Uno), đặt `doc_chu_ky_avr=true` để ĐỌC CHỮ KÝ TỪ "
            "SILICON — nhưng việc đó RESET bo, nên phải nói trước cho người dùng.",
            {"type": "object",
             "properties": {
                 "doc_chu_ky_avr": {
                     "type": "boolean",
                     "description": ("true = bắt tay với bootloader AVR để đọc chữ ký ba byte "
                                     "từ silicon. CẢNH BÁO: thao tác này RESET bo — nếu bo "
                                     "đang chạy thì nó khởi động lại.")},
                 "cong": {"type": "string",
                          "description": "cổng nối tiếp; bỏ trống = tự chọn cổng USB đầu tiên"},
                 "baud_bootloader": {
                     "type": "integer",
                     "description": "tốc độ bootloader, mặc định 57600 (bo Nano cũ); bo mới "
                                    "thường 115200"}},
             },
            risk="R1", core=False,
            keywords=["dò bo", "board", "bộ nạp", "st-link", "cổng", "usb", "detect",
                      "mạch thật", "chip id", "avr", "arduino", "chữ ký chip"])
    def target_detect(ctx: Any, doc_chu_ky_avr: bool = False, cong: str = "",
                      baud_bootloader: int = 57600):
        from ..build import mach_that as MT

        d = MT.do_bo()
        # Đọc chữ ký AVR chỉ khi được bảo. Đây là phép đo THẬT trên silicon, nhưng nó reset
        # bo — không được tự ý làm trong một công cụ R1 mà người dùng tưởng là chỉ nhìn.
        if doc_chu_ky_avr:
            c = cong or next((t["duong_dan"] for t in d["thiet_bi"]
                              if t["loai"] == "cong_noi_tiep" and t["co_the_la_bo"]), "")
            if not c:
                d["avr"] = {"doc_duoc": False,
                            "vi_sao": "không thấy cổng USB nối tiếp nào để bắt tay"}
            else:
                ten, ky, vi_sao = MT.doc_chu_ky_avr(c, baud=baud_bootloader)
                d["avr"] = {"doc_duoc": bool(ky), "cong": c, "chu_ky": ky, "chip": ten,
                            "baud": baud_bootloader, "vi_sao": vi_sao,
                            "da_reset_bo": True}
                if ten:
                    # Chữ ký đọc từ silicon ĐÈ lên mọi phỏng đoán từ nhãn ổ đĩa: đây là bằng
                    # chứng về chính con chip, không phải về cái bo mang nó.
                    d["chip_doc_duoc"] = ten
                    d["vi_sao_chua_doc_duoc_chip"] = ""
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
                   "và ĐỪNG báo nạp được." if d["danh_sach_kiem_tra"] else "")
                + _noi_avr(d))}

    @r.tool("target.flash", "Mạch thật",
            "NẠP firmware vào bo thật. Không hoàn tác được: bản đang chạy trên chip bị ghi "
            "đè. Đối chiếu chip trước khi nạp; nếu không đọc được ID chip thì phải có "
            "`dong_y_khong_doi_chieu_chip=true` mới nạp.",
            {"type": "object",
             "properties": {
                 "tep": {"type": "string",
                         "description": ("đường dẫn tệp ảnh. Bỏ trống: .eide/build/mach.bin "
                                         "cho ARM, .eide/build/mach.elf cho AVR")},
                 "cach": {"type": "string",
                          "enum": ["tu_chon", "sao_tep", "st-flash", "avrdude",
                                   "openfpgaloader"],
                          "description": ("tu_chon = st-flash nếu có, rồi avrdude cho bo AVR "
                                          "qua bootloader, cuối cùng mới sao tệp")},
                 "cong": {"type": "string",
                          "description": "avrdude: cổng nối tiếp; bỏ trống = tự chọn"},
                 "baud_bootloader": {"type": "integer",
                                     "description": "avrdude: mặc định 57600 (Nano cũ)"},
                 "ma_chip_avrdude": {"type": "string",
                                     "description": "avrdude: mã -p, ví dụ m328p. Bỏ trống = "
                                                    "suy từ hộ chiếu chip của dự án"},
                 "bo_kit_fpga": {"type": "string",
                                 "description": "openfpgaloader: tên kit, mặc định tangnano20k"},
                 "giu_sau_tat": {"type": "boolean",
                                 "description": ("openfpgaloader: true = nạp vào flash trên "
                                                 "kit (giữ sau khi tắt nguồn). Mặc định false "
                                                 "= nạp vào SRAM, chạy ngay nhưng MẤT khi tắt "
                                                 "nguồn")},
                 "bat_log_giay": {
                     "type": "number",
                     "description": ("mở cổng nối tiếp TRƯỚC khi nạp rồi đọc thêm bấy nhiêu "
                                     "giây sau khi nạp. Dùng cho firmware in MỘT LẦN rồi "
                                     "dừng — gọi target.log sau khi nạp thì đã muộn, byte "
                                     "phát ra lúc không ai mở cổng là mất. 0 = tắt")},
                 "cong_log": {
                     "type": "string",
                     "description": ("cổng để bắt bản ghi khi dùng bat_log_giay; bỏ trống = "
                                     "cổng nối tiếp duy nhất của bo đang cắm")},
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
                     dong_y_khong_doi_chieu_chip: bool = False, cong: str = "",
                     baud_bootloader: int = 57600, ma_chip_avrdude: str = "",
                     bo_kit_fpga: str = "tangnano20k", giu_sau_tat: bool = False,
                     bat_log_giay: float = 0.0, cong_log: str = ""):
        from ..build import mach_that as MT

        goc = ctx.config.paths.project_root
        p = (goc / tep).resolve() if tep else (goc / ".eide" / "build" / "mach.bin")
        # Chuỗi công cụ AVR không sinh `.bin` — `build.compile` để lại `.elf`, và avrdude
        # nhận `.hex` (tự đổi). Lùi về `.elf` thay vì báo thiếu tệp một cách khó hiểu.
        if not p.exists() and not tep:
            elf = goc / ".eide" / "build" / "mach.elf"
            if elf.exists():
                p = elf
        if not p.exists():
            return ToolResult(False, error=EideError(
                "E4001",
                f"Không có tệp {tep or '.eide/build/mach.bin'} để nạp.",
                hint_for_agent="Biên dịch trước (build.compile) — nó sinh mach.bin cho ARM.",
                alternatives=["build.compile"], blame="agent"))

        d = MT.do_bo()
        # Bo AVR: ĐỌC CHỮ KÝ ngay tại đây, trước khi đối chiếu.
        #
        # `do_bo()` cố ý không tự đọc — việc ấy reset bo, và `target.detect` là công cụ R1 mà
        # người dùng tưởng là chỉ nhìn. Nhưng ở đây thì khác: sắp NẠP, mà nạp cũng reset bo,
        # nên phép đọc không thêm tác dụng phụ nào.
        #
        # Thiếu chỗ này thì phép đối chiếu chip — thứ TC034 tồn tại để bắt — tụt xuống thành
        # "người dùng đã bỏ qua". Đo được trên bo thật: tác tử vừa đọc `1e950f` xong, vừa ghim
        # hộ chiếu ATmega328P xong, mà vẫn phải nạp bằng `dong_y_khong_doi_chieu_chip=true`.
        # Nó cầm đủ hai vế mà công cụ không ghép được.
        cong_avr_som = cong or next((t["duong_dan"] for t in d["thiet_bi"]
                                     if t["nap_duoc_bang"] == "avrdude"), "")
        if not d["chip_doc_duoc"] and cong_avr_som and cach in ("tu_chon", "avrdude"):
            hc_som = _ho_chieu(ctx) or {}
            ma_som = (ma_chip_avrdude
                      or MT._MA_AVRDUDE.get(_goc_chip(str(hc_som.get("chip") or "")), "m328p"))
            ten_avr, ky_avr, _ = MT.doc_chu_ky_avr(cong_avr_som, ma_chip=ma_som,
                                                   baud=baud_bootloader)
            if ten_avr:
                d["chip_doc_duoc"] = ten_avr
                d["vi_sao_chua_doc_duoc_chip"] = ""
                d["avr"] = {"doc_duoc": True, "chu_ky": ky_avr, "chip": ten_avr,
                            "cong": cong_avr_som, "baud": baud_bootloader}
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
                    # Lời khuyên phải khớp với ĐÚNG lý do vừa nêu. Đo được trên phiên
                    # FreeRTOS: thông điệp tự nói *"đọc được STM32F46x_F47x từ bo"* rồi
                    # khuyên "cài st-info" — thứ đã cài rồi, và đã dùng để đọc ra chính câu
                    # ấy. Thứ thiếu là HỘ CHIẾU của dự án. Một lời khuyên không khớp lý do
                    # thì tệ hơn im lặng: nó gửi tác tử đi làm một việc vốn đã xong.
                    ("Đã ĐỌC ĐƯỢC ID chip từ bo; thứ thiếu là dự án CHƯA GHIM chip nào để "
                     "so. Ghim bằng `passport.pin` (kèm nguồn), rồi nạp lại — lúc đó phép "
                     "đối chiếu mới có đủ hai vế.\nVẫn muốn nạp ngay mà bỏ qua phép đối "
                     "chiếu thì gọi lại với `dong_y_khong_doi_chieu_chip=true`."
                     if thay_that and not chip_du_an else
                     "Hai đường đi, để NGƯỜI DÙNG chọn — đừng tự chọn:\n"
                     "1. Cài `st-info`/`st-flash` (tool.install, gói `stlink`) rồi nạp có "
                     "đối chiếu và có verify.\n"
                     "2. Nạp kiểu sao tệp mà KHÔNG đối chiếu ID chip: gọi lại với "
                     "`dong_y_khong_doi_chieu_chip=true`.")
                    + " Nói rõ với người dùng rằng khi bỏ đối chiếu thì phép kiểm “đúng "
                      "chip” chỉ dựa vào nhãn ổ đĩa"
                    + (f" (đang là {thay_doan})" if thay_doan else "")
                    + ", và việc nạp không hoàn tác được."),
                details={"chip_du_an": chip_du_an, "chip_theo_nhan_o": thay_doan,
                         "vi_sao": d["vi_sao_chua_doc_duoc_chip"]},
                alternatives=["tool.install", "target.flash"], blame="user"))

        # Chọn cách nạp.
        co_st = any(t["nap_duoc_bang"] == "st-flash" for t in d["thiet_bi"])
        cong_avr = cong or next((t["duong_dan"] for t in d["thiet_bi"]
                                 if t["nap_duoc_bang"] == "avrdude"), "")
        o_dia = next((Path(t["duong_dan"]) for t in d["thiet_bi"]
                      if t["nap_duoc_bang"] == "sao_tep"), None)
        if cach == "openfpgaloader":
            # Đường FPGA KHÔNG bao giờ được chọn tự động. Nạp một tệp `.fs` vào một bo vi điều
            # khiển, hoặc ngược lại, là chuyện phải do người gõ ra chứ không do máy đoán.
            #
            # DEV-331. `bat_log_giay > 0`: mở cổng nối tiếp TRƯỚC khi nạp rồi đọc tiếp sau.
            # Với firmware in một lần rồi dừng, gọi `target.log` sau khi nạp là đã muộn —
            # đo được 35 ms cho Bài 2 trên Tang Nano 20K. Xem `bat_log_quanh_viec`.
            if bat_log_giay and bat_log_giay > 0:
                if bat_log_giay > 120:
                    return ToolResult(False, error=EideError(
                        "E5001", f"`bat_log_giay` tối đa 120, nhận {bat_log_giay}.",
                        hint_for_agent="Bắt bản ghi lâu hơn 2 phút thì treo cả lượt làm việc.",
                        blame="agent"))
                c_log = cong_log
                if not c_log:
                    ung = [t["duong_dan"] for t in d["thiet_bi"]
                           if t["loai"] == "cong_noi_tiep" and t["co_the_la_bo"]]
                    if len(ung) != 1:
                        return ToolResult(False, error=EideError(
                            "E4011",
                            (f"Có {len(ung)} cổng nối tiếp có thể là bo — không đoán dùng "
                             "cổng nào để bắt bản ghi."
                             if ung else "Không có cổng nối tiếp nào của bo đang cắm."),
                            hint_for_agent=("Đặt `cong_log` cho rõ. Kit FPGA thường hiện HAI "
                                            "cổng: một kênh nạp, một kênh UART — đoán sai "
                                            "kênh thì bản ghi im lặng mà firmware vẫn đúng."),
                            details={"cong": ung},
                            alternatives=["target.detect"], blame="agent"))
                    c_log = ung[0]
                blog = MT.bat_log_quanh_viec(
                    c_log, baud=115200, giay=bat_log_giay,
                    viec=lambda: MT.nap_qua_openfpgaloader(
                        p, bo_kit=bo_kit_fpga, giu_sau_tat=giu_sau_tat))
                kq = blog.get("kq_viec")
                if kq is None:
                    return ToolResult(False, error=EideError(
                        "E4011", str(blog.get("loi") or "Không nạp được và không bắt được "
                                     "bản ghi."),
                        details={"bat_log": blog}, blame="system"))
                kq.canh_bao.extend(blog.get("canh_bao") or [])
                # Bản ghi đi kèm kết quả nạp, để không ai phải ghép hai lời gọi lại với nhau.
                kq.nguyen_van = ((kq.nguyen_van or "") + "\n--- bản ghi cổng nối tiếp ("
                                 + f"{blog['so_byte']} byte) ---\n" + blog["chu"]).strip()
            else:
                kq = MT.nap_qua_openfpgaloader(p, bo_kit=bo_kit_fpga, giu_sau_tat=giu_sau_tat)
        elif cach == "st-flash" or (cach == "tu_chon" and co_st):
            kq = MT.nap_qua_st_flash(p)
        elif cach == "avrdude" or (cach == "tu_chon" and cong_avr):
            if not cong_avr:
                return ToolResult(False, error=EideError(
                    "E4011", "Chọn nạp bằng avrdude nhưng không thấy cổng nối tiếp nào.",
                    hint_for_agent="Gọi target.detect xem máy có cổng USB nối tiếp không.",
                    alternatives=["target.detect"], blame="user"))
            ma = ma_chip_avrdude or MT._MA_AVRDUDE.get(_goc_chip(chip_du_an), "")
            if not ma:
                return ToolResult(False, error=EideError(
                    "E4015",
                    f"Không biết mã avrdude cho chip “{chip_du_an or '(dự án chưa ghim)'}”.",
                    hint_for_agent=("Ghim chip bằng `passport.pin`, hoặc truyền thẳng "
                                    "`ma_chip_avrdude` (ví dụ m328p). Đoán mã chip rồi nạp "
                                    "nhầm họ chip là hỏng bo."),
                    details={"chip_du_an": chip_du_an,
                             "ma_da_biet": sorted(MT._MA_AVRDUDE)},
                    alternatives=["passport.pin", "target.flash"], blame="agent"))
            kq = MT.nap_qua_avrdude(p, cong_avr, ma_chip=ma, baud=baud_bootloader)
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

    @r.tool("target.verify", "Mạch thật",
            "ĐỌC NGƯỢC Flash từ chip rồi so từng byte với tệp đã nạp. Đây là bằng chứng độc "
            "lập: `st-flash write` tự nói “verified”, nhưng đó là lời của chính công cụ vừa "
            "ghi. Công cụ này đi hỏi silicon con chip đang chứa bản nào.",
            {"type": "object",
             "properties": {
                 "tep": {"type": "string",
                         "description": "đường dẫn .bin để đối chiếu (mặc định "
                                        ".eide/build/mach.bin)"}}},
            risk="R2", core=False,
            keywords=["verify", "đối chiếu", "đọc ngược", "chip đang chạy bản nào",
                      "kiểm tra sau khi nạp"])
    def target_verify(ctx: Any, tep: str = ""):
        from ..build import mach_that as MT

        goc = ctx.config.paths.project_root
        p = (goc / tep).resolve() if tep else (goc / ".eide" / "build" / "mach.bin")
        if not p.exists() and not tep and (goc / ".eide" / "build" / "mach.elf").exists():
            p = goc / ".eide" / "build" / "mach.elf"
        # Đọc ngược bằng ĐÚNG đường đã nạp. Lần nạp gần nhất ghi lại `cach` trong kho; dùng
        # st-flash để đọc một con AVR thì không phải "chưa đối chiếu được", mà là đo nhầm
        # con chip — và câu trả lời sai ấy trông y hệt một câu trả lời đúng.
        cach_da_nap = str(((ctx.store.get(MA_NAP) or {}).get("canonical") or {}).get("cach", ""))
        if cach_da_nap == "avrdude":
            bo = MT.do_bo()
            c = next((t["duong_dan"] for t in bo["thiet_bi"]
                      if t["nap_duoc_bang"] == "avrdude"), "")
            hc2 = _ho_chieu(ctx) or {}
            ma = MT._MA_AVRDUDE.get(_goc_chip(str(hc2.get("chip") or "")), "m328p")
            d = MT.doc_nguoc_avr(p, c, ma_chip=ma) if c else {
                "dat": False, "do_duoc": False,
                "vi_sao": "lần nạp trước dùng avrdude nhưng giờ không thấy cổng nối tiếp nào"}
            d.setdefault("do_duoc", bool(d.get("so_byte_doc")))
        else:
            d = MT.doc_nguoc_flash(p)
        a = ctx.store.get(MA_NAP)
        c = (a or {}).get("canonical") or {}
        if a is not None:
            ctx.store.apply(
                artefact_id=MA_NAP, type="target", op="update",
                author=f"agent:{ctx.run_id}",
                canonical={**c, "doc_nguoc": d},
                explain={"summary": "đọc ngược Flash để đối chiếu",
                         "why": "lời của trình nạp không phải bằng chứng về nội dung trên chip",
                         "sources": [str(p.name)], "diff_prev": "—", "next": "—",
                         "confidence": "BAC"},
                view_hint={"kind": "kv", "path": p.name})

        if not d["do_duoc"]:
            return ToolResult(False, error=EideError(
                "E4015", f"Chưa đối chiếu được nội dung trên chip: {d['vi_sao']}",
                hint_for_agent=("KHÔNG đo được khác với KHÔNG khớp — đừng nói chip sai bản. "
                                "Nếu thiếu st-flash thì đề nghị người dùng cài qua "
                                "tool.install."),
                details=d, alternatives=["tool.install", "target.detect"], blame="external"))
        if not d["dat"]:
            return ToolResult(False, error=EideError(
                "E4016", d["vi_sao"],
                hint_for_agent=("Chip đang chạy một bản KHÁC. Nạp lại (target.flash) rồi đối "
                                "chiếu lần nữa TRƯỚC khi giải thích bất cứ hành vi nào quan "
                                "sát được trên bo."),
                details=d, alternatives=["target.flash"], blame="external"))
        return {
            **d,
            "note_vi": (
                f"Đọc ngược {d['so_byte']} byte từ {d['dia_chi']} và so từng byte: GIỐNG HỆT "
                f"tệp đã nạp (sha256 {d['hash_tep'][:16]}). Đây là bằng chứng độc lập với lời "
                "của trình nạp — con chip đang chứa đúng bản này. Nó KHÔNG chứng minh chương "
                "trình đang chạy đúng; muốn biết điều đó thì phải quan sát hành vi.")}

    @r.tool("target.screen", "Mạch thật",
            "ĐỌC BỘ NHỚ KHUNG ẢNH của bo và ghi ra PNG để XEM chương trình đã vẽ được gì. "
            "Dùng khi người dùng nói màn hình đen/sai: nó tách được hai nguyên nhân hoàn toàn "
            "khác nhau — chương trình vẽ sai, hay nó vẽ đúng mà tấm panel không hiện. Bỏ "
            "trống tham số thì tự đọc địa chỉ/kích thước/định dạng từ thanh ghi LTDC.",
            {"type": "object",
             "properties": {
                 "dia_chi": {"type": "integer",
                             "description": "địa chỉ khung ảnh; bỏ trống = đọc từ LTDC"},
                 "rong": {"type": "integer"}, "cao": {"type": "integer"},
                 "dinh_dang": {"type": "string",
                               "enum": ["ARGB8888", "RGB888", "RGB565"],
                               "description": "bỏ trống = đọc từ LTDC_L1PFCR"},
                 "tep": {"type": "string",
                         "description": "nơi ghi PNG; mặc định .eide/anh-man-hinh.png"}},
             "required": []},
            risk="R2", core=False,
            keywords=["màn hình", "màn hình đen", "lcd", "hiển thị", "vẽ", "framebuffer",
                      "khung ảnh", "ltdc", "dsi", "ảnh màn hình", "screen"])
    def target_screen(ctx: Any, dia_chi: int = 0, rong: int = 0, cao: int = 0,
                      dinh_dang: str = "", tep: str = ""):
        from ..build import mach_that as MT

        cau = MT.doc_cau_hinh_ltdc()
        # Thiếu số nào thì lấy từ thanh ghi. Bắt tác tử gõ tay ba con số này thì sai một cái
        # là ảnh đọc ra lệch hàng và trông y như "chương trình vẽ sai" — phép đo tự sinh ra
        # bằng chứng giả, đúng loại sai nguy hiểm nhất.
        if cau["dat"]:
            dia_chi = dia_chi or int(cau["dia_chi_khung"], 16)
            rong = rong or cau["rong"]
            cao = cao or cau["cao"]
            dinh_dang = dinh_dang or cau["dinh_dang"]
        if not (dia_chi and rong and cao and dinh_dang):
            return ToolResult(False, error=EideError(
                "E4019",
                "Chưa biết khung ảnh ở đâu: " + (cau["vi_sao_khong_dat"]
                                                 or "LTDC chưa được cấu hình."),
                hint_for_agent=("LTDC chưa cấu hình thì chưa có gì để đọc — đó ĐÃ là một câu "
                                "trả lời: chương trình chưa chạy tới chỗ bật màn hình. Kiểm "
                                "bằng target.debug xem nó đang kẹt ở đâu."),
                details=cau, alternatives=["target.debug"], blame="external"))

        goc = Path(ctx.config.paths.project_root)
        ra_tep = (goc / tep) if tep else (goc / ".eide" / "anh-man-hinh.png")
        d = MT.doc_khung_anh(dia_chi, rong, cao, dinh_dang, ra_tep)
        if not d["dat"]:
            return ToolResult(False, error=EideError(
                "E4019", f"Chưa đọc được khung ảnh: {d['vi_sao_khong_dat']}",
                hint_for_agent=("KHÔNG đọc được khác với màn hình không có gì. Thiếu openocd "
                                "thì đề nghị người dùng cài qua tool.install."),
                details=d, alternatives=["tool.install", "target.debug"], blame="external"))

        # Khung ảnh có nội dung mà người dùng vẫn thấy đen → đi dọc chuỗi hiển thị NGAY, đừng
        # để tác tử chỉ nhận được tên cả một chuỗi bốn mắt xích. Bốn mắt ấy hỏng theo bốn cách
        # khác nhau và cho ra cùng một màn hình đen.
        duong = MT.doc_duong_hien_thi() if not d.get("chi_mot_mau") else {"dat": False}

        ctx.store.apply(
            artefact_id="target:screen", type="target",
            op="update" if ctx.store.get("target:screen") else "create",
            author=f"agent:{ctx.run_id}", canonical={**d, "ltdc": cau, "duong": duong},
            explain={"summary": f"đọc khung ảnh {rong}×{cao} {dinh_dang}",
                     "why": "phân biệt vẽ sai với panel không hiện",
                     "sources": ["openocd", "LTDC"], "diff_prev": "—", "next": "—",
                     "confidence": "VANG"},
            # Đường dẫn TƯƠNG ĐỐI so với gốc dự án.
            #
            # Hiện vật sống lâu hơn cái máy sinh ra nó: chép thư mục dự án sang máy khác thì
            # một đường dẫn tuyệt đối trỏ về chỗ cũ, và ảnh không mở được. Đo được ngày
            # 29/09/2026 — đây là chỗ DUY NHẤT trong kho ghim đường dẫn tuyệt đối vào một
            # hiện vật (169 chỗ còn lại đều nằm trong kết quả công cụ, chỉ lộ bố cục máy cũ
            # chứ không ai đọc để chạy).
            view_hint={"kind": "image",
                       "path": str(ra_tep.relative_to(goc)
                                   if ra_tep.is_relative_to(goc) else ra_tep)})
        cau_duong = ""
        if duong.get("dat"):
            cau_duong = "Đi dọc chuỗi hiển thị: " + " · ".join(
                ("✓" if m["thong"] else "✗" if m["thong"] is False else "?") + " " + m["ten"]
                for m in duong["mat_xich"]) + ". "
            if duong["dut_o"]:
                cau_duong += ("**ĐỨT Ở: " + ", ".join(duong["dut_o"]) + "** — "
                              + "; ".join(f"{m['ten']}: {m['so_do']} → {m['cach_sua']}"
                                          for m in duong["mat_xich"]
                                          if m["thong"] is False and m["cach_sua"]) + ". "
                              + duong["ghi_chu_chan"] + " ")
            else:
                cau_duong += ("Cả chuỗi đều thông, nên nếu mắt vẫn không thấy gì thì nghi đèn "
                              "nền hoặc chính tấm panel — không phải cấu hình. ")

        return {
            **d, "ltdc": cau, "duong": duong,
            "note_vi": (
                f"Đọc {d['so_byte']} byte khung ảnh tại {d['dia_chi']} ({rong}×{cao} "
                f"{dinh_dang}) → `{d['tep']}`. "
                + (f"Khung ảnh CHỈ CÓ MỘT MÀU ({d['mau_hay_gap'][0]['mau']}): chương trình "
                   "chưa vẽ gì, hoặc mới xoá nền xong. Lỗi nằm ở phần VẼ — đừng đi sửa panel. "
                   if d.get("chi_mot_mau") else
                   f"Khung ảnh có {d.get('so_mau', '?')} màu, hay gặp nhất: "
                   + ", ".join(f"{m['mau']} ({m['ti_le']:.1%})"
                               for m in d.get("mau_hay_gap", []))
                   + ". Có nhiều màu nghĩa là **chương trình ĐÃ vẽ**. Nếu người dùng vẫn thấy "
                     "màn hình đen thì lỗi KHÔNG ở phần vẽ mà ở đường đưa ảnh ra tấm hiển "
                     "thị: LTDC → DSI → panel (OTM8009A), hoặc đèn nền. ")
                + cau_duong
                + "Đây là bộ nhớ của con chip trên bàn, không phải ảnh chụp màn hình máy tính.")}

    @r.tool("target.debug", "Mạch thật",
            "SOI chip đang chạy: dừng nó lại, xem nó đang ở đâu (mã thường hay trong một "
            "ngắt), đọc PC/xPSR/MSP, ĐỌC THANH GHI LỖI CFSR/HFSR và dịch từng bit thành lời, "
            "ĐỔI ĐỊA CHỈ THÀNH TÊN HÀM + tệp:dòng, rồi cho chạy tiếp. Dùng khi firmware dịch "
            "sạch và nạp đúng MÀ hành vi vẫn sai — đừng đi đọc cả cây mã nguồn để đoán hàm "
            "nào ở địa chỉ nào, công cụ này trả lời sẵn.",
            {"type": "object",
             "properties": {
                 "dia_chi": {"type": "array", "items": {"type": "integer"},
                             "description": "địa chỉ cần đọc, ví dụ [0x40016800] cho LTDC"},
                 "so_tu": {"type": "integer",
                           "description": "đọc mấy từ 32-bit mỗi địa chỉ (mặc định 4)"},
                 "bien": {"type": "array", "items": {"type": "string"},
                          "description": ("tên biến/hàm toàn cục cần tra, ví dụ "
                                          "[\"Lcd_Driver_Type\", \"OTM8009A_ReadID\"]. "
                                          "Biến thì đọc luôn giá trị trên chip; hàm thì "
                                          "báo kích thước mã và cảnh báo nếu nó chỉ trả "
                                          "về một hằng số")},
                 "lay_mau": {"type": "integer",
                             "description": ("lấy mẫu PC bấy nhiêu lần để biết chương trình "
                                             "đang tiến hay quanh quẩn một chỗ; 0 = không "
                                             "lấy mẫu (mặc định)")}}},
            risk="R2", core=False,
            keywords=["gỡ lỗi", "debug", "treo", "đứng", "không chạy", "màn hình đen",
                      "thanh ghi", "chip đang làm gì", "halt", "pc"])
    def target_debug(ctx: Any, dia_chi: list[int] | None = None, so_tu: int = 4,
                     lay_mau: int = 0, bien: list[str] | None = None):
        from ..build import mach_that as MT

        # Tra tên → địa chỉ TRƯỚC khi dừng chip, để đọc biến trong cùng một lần dừng.
        goc0 = Path(ctx.config.paths.project_root)
        ky = MT.ky_hieu_theo_ten(goc0 / ".eide" / "build" / "mach.elf",
                                 list(bien or [])) if bien else {}
        dia_chi = list(dia_chi or [])
        for v in (ky.get("ky_hieu") or {}).values():
            if not v["la_ham"]:
                dia_chi.append(v["dia_chi"])

        d = MT.soi_chip(dia_chi, so_tu=so_tu)
        if not d["dat"]:
            return ToolResult(False, error=EideError(
                "E4018", f"Chưa soi được chip: {d['vi_sao_khong_dat']}",
                hint_for_agent=("KHÔNG soi được khác với chip chạy đúng. Thiếu openocd thì "
                                "đề nghị người dùng cài qua tool.install."),
                details=d, alternatives=["tool.install", "target.detect"], blame="external"))

        # PC là một con số; tác tử cần một cái TÊN. Đo được trên bo STM32F469: nhận
        # `pc 0x08000db0` xong, tác tử đi `fs.read` 28 lần để dò hàm nào ở đấy rồi hết hạn
        # mức lời gọi và dừng giữa việc. `addr2line` trả lời trong 40 ms, nên EIDE trả lời
        # luôn thay vì để nó phải đọc cả cây mã nguồn.
        goc = Path(ctx.config.paths.project_root)
        elf = goc / ".eide" / "build" / "mach.elf"
        xin = ([int(d["pc"], 16)] if d.get("pc") else []) + list(dia_chi or [])
        # Khung ngoại lệ có địa chỉ ĐÁNG quan tâm hơn cả PC: `pc_fault` là lệnh đã gây fault,
        # `lr_fault` là chỗ gọi nó. PC lúc dừng chỉ là `Default_Handler` — đúng với mọi fault,
        # nên tự nó không dẫn tới đâu.
        kn = d.get("khung_ngat") or {}
        if kn.get("doc_duoc"):
            xin += [kn["pc_fault"], kn["lr_fault"] & ~1]
        dv = d.get("dau_vet") or {}
        xin += list(dv.get("dia_chi") or [])[:6]
        ten = MT.giai_ma_dia_chi(elf, xin)
        d["ky_hieu"] = ten.get("ky_hieu") or {}
        d["ky_hieu_vi_sao_khong_co"] = ten.get("vi_sao_khong_dat", "")

        # Và ngay sau khi có tên, đi hỏi silicon xem cái tên ấy có nói về mã đang chạy không.
        # Đo được trên bo STM32F469: PC 0x08000db0 giải mã thành `OTM8009A_Init_Ext`, mà 32
        # byte tại đúng địa chỉ đó trên chip KHÁC tệp vừa dịch — tức chip đang chạy bản cũ và
        # cái tên kia sẽ dẫn tác tử đi sửa một hàm không liên quan.
        d["ky_hieu_tin_duoc"] = None
        if d["ky_hieu"] and d.get("pc"):
            k = MT.khop_tai_dia_chi(goc / ".eide" / "build" / "mach.bin", int(d["pc"], 16))
            d["doi_chieu_tai_pc"] = k
            d["ky_hieu_tin_duoc"] = k["khop"] if k["do_duoc"] else None

        # Chip không ở trong ngắt mà hành vi vẫn sai → câu hỏi đổi thành "nó có TIẾN lên
        # không". Một mẫu PC đơn lẻ không trả lời được: kẹt một chỗ, quanh quẩn một vòng lặp,
        # và chip reset lại đều cho ra cùng một con số. Nên lấy nhiều mẫu, cộng với lý do
        # reset do chính chip khai.
        d["nhieu_mau"] = MT.lay_mau_pc(lay_mau) if lay_mau else {}
        d["nguyen_nhan_reset"] = MT.doc_nguyen_nhan_reset() if lay_mau else {}
        if d["nhieu_mau"].get("dat"):
            xin_them = sorted({int(x, 16) for x in d["nhieu_mau"]["mau"]})
            dia_chi = list(dia_chi or []) + xin_them[:8]

        trong_ngat = d["che_do"].lower().startswith("handler")
        lp = d.get("loi_phan_cung") or {}
        # Thanh ghi lỗi phải đi vào CÂU NÓI, không chỉ nằm trong payload. Đo được trên bo
        # STM32F469: `loi_phan_cung` có đủ CFSR=0x00020000 → INVSTATE, nhưng `note_vi` không
        # nhắc tới nó, nên manh mối quyết định nằm ở một khoá lồng sâu trong JSON mà lời văn
        # thì vẫn đang chỉ sang `SysTick_Handler` — tức là chỉ sang lỗi của LẦN TRƯỚC.
        cau_loi = ""
        if lp.get("nghia"):
            cau_loi = ("**Thanh ghi lỗi của CPU nói rõ hơn tên handler**: CFSR = "
                       f"{lp['cfsr']}, HFSR = {lp.get('hfsr', '?')} → "
                       + "; ".join(lp["nghia"]) + ". ")
            for k, nh in (("mmfar", "địa chỉ gây lỗi truy cập bộ nhớ"),
                          ("bfar", "địa chỉ gây lỗi bus")):
                if lp.get(k) and lp[k] != "(không hợp lệ)":
                    cau_loi += f"{nh.capitalize()}: {lp[k]}. "
        elif lp:
            cau_loi = (f"CFSR = {lp.get('cfsr')} — không bit lỗi nào bật, nên chỗ dừng này "
                       "không phải do fault. ")

        # Khung ngoại lệ: nói TRƯỚC tên hàm ở PC, vì nó là chỗ tác tử phải đi sửa. Đo được
        # trên bo STM32F469: PC = `Default_Handler` (vô dụng), còn khung nói `pc_fault = 0x0`
        # và `lr = 0x080006F7` → `OTM8009A_ReadID_Ext` tại otm8009a.c:472 — tức là một lần
        # gọi con trỏ hàm NULL, chỉ đúng một dòng.
        cau_khung = ""
        if kn.get("doc_duoc"):
            def _ten(a: int) -> str:
                v = (d["ky_hieu"] or {}).get(f"0x{a:08x}") or {}
                return ((v.get("ham") or "") + (f" ({v['nguon']})" if v.get("nguon") else "")
                        or "không có ký hiệu ở địa chỉ này")

            cau_khung = (
                "**Khung ngoại lệ ở đỉnh ngăn xếp — đây là chỗ đáng đọc, không phải PC**: "
                f"lệnh gây fault ở {kn['pc']} = {_ten(kn['pc_fault'])}; chỗ gọi nó "
                f"(LR) {kn['lr']} = {_ten(kn['lr_fault'] & ~1)}. ")
            if kn.get("ghi_chu"):
                cau_khung += kn["ghi_chu"] + " "
            if any("STKERR" in x for x in lp.get("nghia", [])):
                cau_khung += ("⚠️ CFSR có bit STKERR: fault xảy ra TRONG LÚC đẩy ngăn xếp, "
                              "nên tám số của khung này là rác — đừng tin chúng. ")
        elif kn:
            cau_khung = f"Chưa dựng được khung ngoại lệ: {kn.get('vi_sao', 'không rõ')} "

        # Tên hàm, kèm ĐÚNG mức tin được. Ba trạng thái, không gộp: tin được / biết là sai /
        # chưa đo được. Gộp hai cái sau thành "không tin" thì tác tử bỏ mất một manh mối thật;
        # gộp vào "tin được" thì nó đi sửa hàm của một bản firmware không còn trên chip.
        # Dấu vết ngăn xếp: nói NGAY SAU khung ngoại lệ, vì khi chip không fault thì đây là
        # thứ duy nhất trả lời được "ai gọi tới chỗ này".
        cau_vet = ""
        if dv.get("doc_duoc"):
            ten_vet = []
            for k in dv["khung"]:
                v = (d["ky_hieu"] or {}).get(k["dia_chi"].lower()) or {}
                ten_vet.append(k["dia_chi"] + (f" = {v['ham']}" if v.get("ham") else "")
                               + (f" ({v['nguon']})" if v.get("nguon") else ""))
            cau_vet = ("**Dấu vết ngăn xếp** (gần đỉnh trước): " + "; ".join(ten_vet) + ". "
                       + dv["ghi_chu"] + " ")
        elif dv:
            cau_vet = f"Chưa dựng được dấu vết ngăn xếp: {dv.get('vi_sao', '?')} "

        # Biến toàn cục: giá trị đọc từ chip, kèm câu hỏi mà giá trị ấy KHÔNG trả lời được —
        # ai đặt ra nó. Đo được trên bo STM32F469: `Lcd_Driver_Type = 1 = LCD_CTRL_OTM8009A`,
        # nghe như đã dò được panel; mà `OTM8009A_ReadID()` chỉ có 4 byte mã
        # (`movs r0,#64 ; bx lr`) — nó KHAI BÁO kết quả chứ không dò gì. N6 nằm trong firmware.
        cau_bien = ""
        if ky.get("ky_hieu"):
            d["bien"] = {}
            phan = []
            for ten, v in sorted(ky["ky_hieu"].items()):
                if v["la_ham"]:
                    mo = f"{ten}: hàm, {v['kich_thuoc']} byte mã tại {v['dia_chi_hex']}"
                    if v.get("canh_bao"):
                        mo += f" ⚠️ {v['canh_bao']}"
                    elif v.get("ghi_chu"):
                        mo += f" ({v['ghi_chu']})"
                else:
                    o = d["o_nho"].get(f"0x{v['dia_chi']:08x}") or []
                    gt = o[0] if o else "?"
                    v["gia_tri"] = gt
                    mo = f"{ten} @ {v['dia_chi_hex']} = 0x{gt}"
                d["bien"][ten] = v
                phan.append(mo)
            cau_bien = "**Ký hiệu tra được**: " + " · ".join(phan) + ". "
            if ky.get("thieu"):
                cau_bien += f"Không thấy trong ELF: {', '.join(ky['thieu'])}. "
        elif bien:
            cau_bien = (f"Chưa tra được ký hiệu: {ky.get('vi_sao_khong_dat', '?')} ")

        cau_mau = ""
        nm = d.get("nhieu_mau") or {}
        if nm.get("dat"):
            cau_mau = nm["ket_luan"] + " "
            nnr = d.get("nguyen_nhan_reset") or {}
            if nnr.get("dat"):
                cau_mau += (f"Lý do khởi động gần nhất do chip khai (RCC_CSR = {nnr['csr']}): "
                            + ("; ".join(nnr["nguyen_nhan"]) or "không cờ nào bật") + ". "
                            + nnr["ghi_chu"] + " ")
        elif nm:
            cau_mau = f"Chưa lấy được nhiều mẫu PC: {nm.get('vi_sao_khong_dat', '?')} "

        cau_ten = ""
        if d["ky_hieu"]:
            ds = "; ".join(
                f"{a} = {v['ham'] or '(không có ký hiệu)'}"
                + (f" ({v['nguon']})" if v["nguon"] else "")
                for a, v in d["ky_hieu"].items())
            tin = d.get("ky_hieu_tin_duoc")
            dc = d.get("doi_chieu_tai_pc") or {}
            cau_ten = (
                f"**Địa chỉ → mã nguồn** (giải từ mach.elf): {ds}. "
                + ("Mã tại PC trên chip khớp tệp vừa dịch, nên tên hàm này nói về đúng mã "
                   "đang chạy. " if tin is True else
                   "⚠️ NHƯNG mã tại PC trên chip **KHÁC** tệp vừa dịch: " + dc.get("vi_sao", "")
                   + " Đừng đi sửa hàm vừa nêu tên — nó thuộc bản khác. "
                   if tin is False else
                   "Chưa đối chiếu được mã trên chip với tệp vừa dịch ("
                   + (dc.get("vi_sao") or "không rõ")
                   + "), nên tên hàm này chỉ đúng NẾU chip đang chạy đúng bản vừa dịch. "))
        elif d.get("ky_hieu_vi_sao_khong_co"):
            cau_ten = f"Chưa đổi được địa chỉ thành tên hàm: {d['ky_hieu_vi_sao_khong_co']} "
        ctx.store.apply(
            artefact_id="target:debug", type="target",
            op="update" if ctx.store.get("target:debug") else "create",
            author=f"agent:{ctx.run_id}", canonical=d,
            explain={"summary": f"soi chip: {d['che_do']}",
                     "why": "firmware dịch sạch và nạp đúng mà hành vi vẫn sai",
                     "sources": ["openocd"], "diff_prev": "—", "next": "—",
                     "confidence": "BAC"},
            view_hint={"kind": "kv", "path": "openocd"})
        return {
            **d,
            "dang_ket_trong_ngat": trong_ngat,
            "note_vi": (
                f"Chip đang ở chế độ **{d['che_do']}**, PC = {d['pc'] or '?'}. "
                + cau_loi + cau_khung + cau_vet + cau_bien + cau_mau + cau_ten
                + ("ĐÂY LÀ MANH MỐI CHÍNH: “Handler …” nghĩa là CPU đang nằm trong một trình "
                   "phục vụ ngắt. Nếu nó ở đó mãi thì chương trình chính đã chết ở đúng chỗ "
                   "ấy — hay gặp nhất là một handler để mặc định thành `while(1){}` trong "
                   "startup, ví dụ `SysTick_Handler` sau khi `HAL_Init()` bật SysTick. "
                   if trong_ngat else
                   "“Thread” nghĩa là đang chạy mã thường — chỗ chết (nếu có) nằm trong một "
                   "vòng lặp của chính chương trình, không phải trong ngắt. ")
                + (f"Ô nhớ đọc được: {d['o_nho']}. " if d["o_nho"] else "")
                + "Đây là trạng thái tại ĐÚNG lúc dừng, không phải suy từ mã nguồn.")}

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
