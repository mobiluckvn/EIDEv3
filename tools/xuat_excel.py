#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xuất toàn bộ kết quả đo ra một tệp Excel.

    .venv/bin/python tools/xuat_excel.py

Ghi ra tệp **mới** `Usecase_Test_KET_QUA_29-09-2026.xlsx`, **không** đè lên
`Usecase_Test_Agent_Ky_Su_Nhung.xlsx`.

Vì sao không đè: bảng 23/09/2026 là một phép đo thật trên kiến trúc cũ. Đè lên nó là xoá mất
mốc so sánh — và một bảng chỉ còn cột "hôm nay" thì không ai biết sản phẩm đã đi được bao xa,
cũng không ai kiểm lại được lời tuyên "đã tốt lên". Tệp mới giữ **cả hai cột** cạnh nhau.

Năm sheet:

* `Test case`   — 76 ca, cột 23/09 và cột 29/09 đặt cạnh nhau, cộng cột "đọc tay" và số liệu
                  chi tiết (số lời gọi công cụ, mã lỗi, thời gian).
* `Usecase`     — 19 usecase, chép từ tệp gốc, thêm cột đạt/đo được.
* `Giao dien`   — 124 ô kiểm giao diện.
* `Loi tim duoc`— 9 lỗi, tách rõ lỗi SẢN PHẨM khỏi lỗi BỘ ĐO.
* `Thong ke`    — số tổng, tính bằng công thức để mở ra là thấy nó cộng từ đâu.
"""

from __future__ import annotations

import json
import pathlib
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

T = REPO / "docs/review-v3/test"
GOC = T / "Usecase_Test_Agent_Ky_Su_Nhung.xlsx"
RA = T / "Usecase_Test_KET_QUA_29-09-2026.xlsx"

DAU = PatternFill("solid", fgColor="1F3864")
CHU_DAU = Font(color="FFFFFF", bold=True)
MAU = {"Đạt": "C6EFCE", "Không đạt": "FFC7CE", "Ngoài phạm vi": "E7E6E6",
       "Cần người": "FFF2CC", "Cần thiết bị": "FFF2CC", "Bị chặn": "FFF2CC",
       "Bỏ qua": "E7E6E6", "Chưa test": "FFFFFF"}
NHAN = {"dat": "Đạt", "khong_dat": "Không đạt", "ngoai_pham_vi": "Ngoài phạm vi",
        "can_nguoi": "Cần người", "can_thiet_bi": "Cần thiết bị"}

LOI = [
    ("L1", "SẢN PHẨM", "Đã sửa", "store.option_choose gán “NGƯỜI QUYẾT” cho câu không chọn gì",
     "TC004",
     "Người gõ “Làm cho mình cái mạch thông minh.” → tác tử gọi store.option_choose với "
     "quyet_boi=\"nguoi\", trich_loi_nguoi chính là câu ấy, rồi sinh ADR-01.",
     "Giả mạo xuất xứ. Vi phạm N1 theo cách tệ nhất: nguồn CÓ THẬT nhưng KHÔNG nói điều được "
     "gán cho nó — một trích dẫn thật đặt sai chỗ khó phát hiện hơn một trích dẫn bịa. NGUOI "
     "là tầng tin cậy cao nhất, thứ mọi quyết định sau đó dựa vào mà không ai kiểm lại.",
     "quyet_boi=\"nguoi\" phải chứng minh được, không phải khai được: câu trích có trong sổ "
     "cái · có chữ mang nghĩa lựa chọn · nhắc đúng phương án. Lỗi trả về nói ra HAI đường đi "
     "(hạ xuống tac_tu, hoặc hỏi rồi chốt).",
     "tests/test_ai_quyet.py — 4 ca, có ca chứng minh phanh không chặn nhầm đường đúng"),
    ("L2", "BỘ ĐO", "Đã sửa", "Ca “Phiên mới” bị chạy chung dự án", "TC001/4/5/7",
     "Bốn ca ghi tiền điều kiện “Phiên mới” dùng chung một dự án, nên TC004 thừa hưởng ngữ "
     "cảnh LAN→USB của ba ca trước.",
     "Đo sai tiền điều kiện thì con số nói về một bài toán khác. Tác tử đọc câu mơ hồ thành "
     "“chọn phương án” — hành vi hợp lý trong một ngữ cảnh sai.",
     "Mô tả bằng “xô phiên” (phien), đúng chuỗi phụ thuộc của đề bài: TC001→002→003→006 cùng "
     "xô; TC004/005/007 mỗi ca một xô.", "chạy lại UC01: 6/7"),
    ("L3", "BỘ ĐO", "Đã sửa", "Phép chấm bật xanh cho đúng cái lỗi nó canh", "TC004",
     "Tiêu chí chỉ đòi lời đáp chứa một dấu “?”. Lượt chốt ADR-01 vẫn có câu hỏi ở cuối nên "
     "được chấm ĐẠT.",
     "Đọc lời đáp thì thấy nó có hỏi han; đọc chuỗi công cụ mới thấy nó đã chốt xong rồi.",
     "Thêm cam_cong_cu — chấm bằng VIỆC ĐÃ LÀM, không bằng LỜI ĐÃ NÓI.", "TC004 nay đạt đúng lý do"),
    ("L4", "BỘ ĐO", "Đã sửa", "Ô ĐỎ GIẢ — phạt đúng hành vi đề bài chờ", "TC014, TC019",
     "TC014 trả đúng 4,7 kΩ và trích đoạn chèn độc hại ra để cảnh báo → trượt vì cụm cấm là "
     "“rm -rf”. TC019 nói thẳng “KHÔNG ĐẠT” → trượt vì cấm nguyên chữ “đạt”.",
     "Ô đỏ giả tệ ngang ô xanh giả: nó cử người đi sửa một thứ không hỏng, và làm mất lòng "
     "tin vào những ô đỏ thật nằm cạnh.",
     "Hai phanh: viết cụm cấm hẹp lại, cộng một phanh phủ định (không/từ chối/cảnh báo đứng "
     "trước thì tác tử đang NÓI VỀ chứ không LÀM).", "TC014, TC019 nay đạt"),
    ("L5", "BỘ ĐO", "Đã sửa", "Ca đòi một CHUỖI việc nhưng chấm bằng MỘT việc", "TC029",
     "Đề bài đòi dò → tóm tắt → hỏi xác nhận → nạp → kiểm. Phép chấm chỉ đòi một trong ba "
     "công cụ, nên tác tử dò xong rồi dừng vẫn ĐẠT.",
     "Hai phần ba đề bài chưa được chạm tới mà không hiện ra ở đâu. Đường nạp có hỏng thật "
     "thì bài kiểm vẫn xanh vì nó không bao giờ đi tới đó.",
     "Thêm cong_cu_du (đòi đủ chuỗi) và đặt sẵn ảnh nhị phân — chính bản đang chạy trên bo, "
     "nên nạp lên không đổi gì.", "TC029 nay đủ chuỗi detect→flash"),
    ("L6", "BỘ ĐO", "Đã xử", "Chấm bằng từ khoá trên tiếng Việt tự do không đủ làm phán quyết",
     "TC014, TC019, TC043",
     "Ba lần trong một đợt, phép chấm đánh trượt những lời đáp gần như hoàn hảo vì tác tử "
     "chọn cách nói khác (“không có thông tin về” thay vì “không có trong”).",
     "Tiếng Việt tự do có quá nhiều cách nói đúng một ý; một danh sách từ khoá luôn thiếu "
     "cách nói mà tác tử vừa chọn. Nới danh sách sau mỗi lần trượt là chạy theo, không phải "
     "sửa.",
     "Máy chấm là lượt SÀNG, không phải phán quyết. Mọi ca không đạt đều được ĐỌC TAY rồi "
     "gắn nhãn thật. Bảng có hai cột kết quả.", "cột “Sau khi đọc tay” trong sheet Test case"),
    ("L7", "SẢN PHẨM", "Đã sửa", "build.compile chọn công cụ theo “máy có gì”, không theo "
     "“dự án là gì”", "TC055",
     "Điều kiện là “arduino-cli đã cài and isa có fqbn”, nên dự án chỉ có firmware/*.c vẫn bị "
     "đẩy sang arduino-cli compile.",
     "Người hỏi về -O3 nhận lỗi nói về định dạng sketch Arduino, rồi đi tìm một tệp .ino mà "
     "dự án không bao giờ cần. Và nó CHẶN ĐỨNG ca kiểm trước khi tới phần chạy hồi quy — một "
     "lỗi ở bước chọn công cụ che mất toàn bộ thứ nằm sau nó.",
     "Chỉ chọn arduino-cli khi thư mục thật sự có .ino; không thì rơi xuống avr-gcc.",
     "tests/test_chon_chuoi_cong_cu.py — 4 ca, đã phá lại bản vá để chắc chúng đỏ được"),
    ("L8", "BỘ ĐO", "Đã sửa", "Luồng có bước “hỏi xác nhận” bị đo bằng MỘT lượt", "TC029",
     "Tác tử dò chip rất kỹ (đọc DETAILS.TXT + ID silicon qua SWD), từ chối nạp vì ảnh nhị "
     "phân chưa có biên bản build, rồi hỏi xác nhận. Phép chấm ghi “THIẾU target.flash”.",
     "Phạt đúng hành vi cẩn thận mà cổng G-FLASH sinh ra để có. Một tác tử chịu dừng lại hỏi "
     "trước khi ghi Flash là điều cả thiết kế theo đuổi.",
     "Thêm noi_tiep — lượt thứ hai của người dùng, cho ca mà đề bài có bước xác nhận.",
     "TC029 nay đủ chuỗi; bo kiểm lại bằng target.debug sau khi nạp"),
    ("L9", "SẢN PHẨM", "Đã sửa", "Bảng trong Console cuộn ngang được nhưng không có dấu hiệu",
     "bộ quét giao diện",
     "showsIndicators:false, nên cột thứ ba bị cắt thành “Giải p…” và người đọc không có lý "
     "do nào để thử kéo ngang.",
     "Nội dung không mất nhưng người dùng không có cách nào biết là nó còn — với họ, phần ấy "
     "không tồn tại. Lọt qua CẢ 124 ô của bộ quét, và mọi con số đều ĐÚNG: bộ quét đo bố cục "
     "khối, chỗ hỏng nằm bên trong một khối. Lần thứ ba liên tiếp tấm ảnh bắt được thứ con "
     "số bỏ sót (sau DEV-289, DEV-290).",
     "showsIndicators:true — trả lại cho người đọc thứ duy nhất họ thiếu: một lý do để kéo.",
     "ảnh docs/review-v3/test/ket-qua-giao-dien/anh/"),
]


def _dau(ws, tieu_de: list[str], rong: list[int]) -> None:
    ws.append(tieu_de)
    for i, c in enumerate(ws[1], 1):
        c.fill, c.font = DAU, CHU_DAU
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = rong[i - 1]
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def _to(ws, tu_dong: int = 2) -> None:
    """Xuống dòng trong ô và canh trên — bảng này để ĐỌC, không để liếc."""
    for r in ws.iter_rows(min_row=tu_dong):
        for c in r:
            c.alignment = Alignment(vertical="top", wrap_text=True)


def main() -> int:
    from bo_usecase import NHOM, TEN_UC

    ket = {}
    for x in (T / "ket-qua-chay-lai/ket-qua.jsonl").read_text("utf-8").splitlines():
        if x.strip():
            o = json.loads(x)
            ket[o["ma"]] = o                       # dòng sau đè dòng trước
    tay = json.loads((T / "ket-qua-chay-lai/doc-tay.json").read_text("utf-8"))
    gd = json.loads((T / "ket-qua-giao-dien/ket-qua.json").read_text("utf-8"))

    cu = openpyxl.load_workbook(GOC)
    cu_tc = {r[0]: r for r in cu["Test case"].iter_rows(min_row=2, values_only=True) if r[0]}

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ---------------------------------------------------------------- Test case
    ws = wb.create_sheet("Test case")
    _dau(ws, ["Mã TC", "Mã UC", "Loại", "Tên kịch bản", "Ưu tiên",
              "Kết quả mong đợi",
              "23/09/2026 — kiến trúc cũ", "Kết quả thực tế 23/09",
              "29/09/2026 — máy chấm", "29/09/2026 — SAU KHI ĐỌC TAY",
              "Loại lỗi", "Vì sao (máy chấm / đọc tay)",
              "Chuỗi công cụ tác tử đã đi", "Số lời gọi", "Lời gọi HỎNG", "Mã lỗi",
              "Giây", "Nhật ký chi tiết"],
         [9, 8, 9, 34, 7, 46, 15, 46, 15, 17, 11, 52, 46, 9, 10, 12, 7, 34])
    for uc, ds in NHOM.items():
        for tc in ds:
            k = ket.get(tc["ma"], {})
            t = tay.get(tc["ma"], {})
            c = cu_tc.get(tc["ma"], [None] * 13)
            vi = k.get("vi_sao", "")
            if t.get("ghi_chu"):
                vi = f"MÁY: {vi}\nĐỌC TAY: {t['ghi_chu']}"
            ws.append([
                tc["ma"], uc, tc["loai"], tc["ten"], tc.get("uu_tien", ""), tc.get("cho", ""),
                c[8] or "", c[9] or "",
                NHAN.get(k.get("nhan", ""), ""),
                NHAN.get(t.get("nhan", k.get("nhan", "")), ""),
                {"san_pham": "lỗi SẢN PHẨM", "phep_cham": "lỗi PHÉP CHẤM"}.get(
                    t.get("loai", ""), ""),
                vi,
                " → ".join(k.get("cong_cu") or []),
                len(k.get("goi") or []),
                k.get("so_loi_cong_cu", 0),
                ", ".join(k.get("ma_loi") or []),
                k.get("giay", ""),
                f"ket-qua-chay-lai/nhat-ky/{tc['ma']}.md",
            ])
    for r in ws.iter_rows(min_row=2):
        for j in (7, 9, 10):                       # ba cột trạng thái
            v = r[j - 1].value
            if v in MAU:
                r[j - 1].fill = PatternFill("solid", fgColor=MAU[v])
    _to(ws)

    # ---------------------------------------------------------------- Usecase
    ws = wb.create_sheet("Usecase")
    _dau(ws, ["Mã UC", "Tên usecase", "Số TC", "Đạt / đo được", "Ca không đạt",
              "Ca mang nhãn riêng"],
         [9, 46, 8, 15, 22, 34])
    for uc, ds in NHOM.items():
        ms = [(t["ma"], tay.get(t["ma"], {}).get("nhan", ket.get(t["ma"], {}).get("nhan", "")))
              for t in ds]
        dd = [m for m in ms if m[1] in ("dat", "khong_dat")]
        ws.append([uc, TEN_UC[uc], len(ds),
                   f"{sum(1 for m in dd if m[1] == 'dat')}/{len(dd)}",
                   ", ".join(m[0] for m in ms if m[1] == "khong_dat") or "—",
                   ", ".join(f"{m[0]} ({NHAN.get(m[1], m[1])})" for m in ms
                             if m[1] in ("ngoai_pham_vi", "can_nguoi", "can_thiet_bi")) or "—"])
    _to(ws)

    # ---------------------------------------------------------------- Giao diện
    ws = wb.create_sheet("Giao dien")
    _dau(ws, ["Phần", "Điều được kiểm", "Kết quả", "Bằng chứng"], [34, 58, 10, 70])
    for m in gd:
        ws.append([m["phan"], m["cau"], "Đạt" if m["dat"] else "Không đạt", m["bang_chung"]])
    for r in ws.iter_rows(min_row=2):
        r[2].fill = PatternFill("solid", fgColor=MAU[r[2].value])
    _to(ws)

    # ---------------------------------------------------------------- Lỗi tìm được
    ws = wb.create_sheet("Loi tim duoc")
    _dau(ws, ["Mã", "Thuộc về", "Trạng thái", "Tên lỗi", "Đo được ở",
              "Chuyện gì xảy ra", "Vì sao đáng sửa", "Sửa thế nào", "Kiểm ngược"],
         [6, 12, 10, 46, 17, 58, 58, 58, 46])
    for x in LOI:
        ws.append(list(x))
    for r in ws.iter_rows(min_row=2):
        r[1].fill = PatternFill(
            "solid", fgColor="FFC7CE" if r[1].value == "SẢN PHẨM" else "FFF2CC")
    _to(ws)

    # ---------------------------------------------------------------- Thống kê
    ws = wb.create_sheet("Thong ke")
    _dau(ws, ["Chỉ số", "Giá trị", "Ghi chú"], [40, 16, 70])
    n = len(ket)
    dong = [
        ("Tổng số usecase", "=COUNTA(Usecase!A2:A200)", ""),
        ("Tổng số test case", "=COUNTA('Test case'!A2:A1000)", ""),
        ("Test case Happy", '=COUNTIF(\'Test case\'!C2:C1000,"Happy")', ""),
        ("Test case Unhappy", '=COUNTIF(\'Test case\'!C2:C1000,"Unhappy")', ""),
        ("", "", ""),
        ("23/09/2026 — Đạt", '=COUNTIF(\'Test case\'!G2:G1000,"Đạt")',
         "Đo trên kiến trúc CŨ (định tuyến ý định). Giữ lại để so, không phải để trách."),
        ("23/09/2026 — Không đạt", '=COUNTIF(\'Test case\'!G2:G1000,"Không đạt")', ""),
        ("", "", ""),
        ("29/09 máy chấm — Đạt", '=COUNTIF(\'Test case\'!I2:I1000,"Đạt")',
         "Máy chấm bằng từ khoá + chuỗi công cụ. Đây là lượt SÀNG, không phải phán quyết."),
        ("29/09 máy chấm — Không đạt", '=COUNTIF(\'Test case\'!I2:I1000,"Không đạt")', ""),
        ("", "", ""),
        ("29/09 SAU ĐỌC TAY — Đạt", '=COUNTIF(\'Test case\'!J2:J1000,"Đạt")',
         "Cột KẾT LUẬN: đọc nguyên văn từng lời đáp rồi gắn nhãn thật."),
        ("29/09 SAU ĐỌC TAY — Không đạt", '=COUNTIF(\'Test case\'!J2:J1000,"Không đạt")', ""),
        ("29/09 — Ngoài phạm vi", '=COUNTIF(\'Test case\'!J2:J1000,"Ngoài phạm vi")',
         "Chủ sản phẩm chốt không làm (PCB, phân quyền). Gọi là “không đạt” thì bảng nói sai "
         "về sản phẩm."),
        ("29/09 — Cần người", '=COUNTIF(\'Test case\'!J2:J1000,"Cần người")',
         "Cần một thao tác vật lý máy không tự làm được (rút bo, rút cáp giữa lúc nạp)."),
        ("29/09 — Cần thiết bị", '=COUNTIF(\'Test case\'!J2:J1000,"Cần thiết bị")',
         "Cần phần cứng không có trên bàn (bo thứ hai, bàn thử HIL, bản scan mờ thật)."),
        ("Số ca ĐO ĐƯỢC", "=B12+B13", "Đạt + Không đạt, sau khi đọc tay."),
        ("Tỉ lệ đạt trên số đo được", "=IFERROR(B12/B18,0)", ""),
        ("", "", ""),
        ("Ô kiểm giao diện — Đạt", '=COUNTIF(\'Giao dien\'!C2:C1000,"Đạt")', ""),
        ("Ô kiểm giao diện — Không đạt", '=COUNTIF(\'Giao dien\'!C2:C1000,"Không đạt")', ""),
        ("", "", ""),
        ("Lỗi SẢN PHẨM tìm được", '=COUNTIF(\'Loi tim duoc\'!B2:B100,"SẢN PHẨM")', ""),
        ("Lỗi của chính BỘ ĐO", '=COUNTIF(\'Loi tim duoc\'!B2:B100,"BỘ ĐO")',
         "Ghi ngang hàng với lỗi sản phẩm: một ô xanh giả hay một ô đỏ giả đều dẫn tới việc "
         "sai, chỉ theo hai hướng khác nhau."),
        ("", "", ""),
        ("Ca đơn vị (pytest)", 1231, "Chạy bằng `.venv/bin/python -m pytest tests/ -q`."),
        ("Ngày đo", "29/09/2026", ""),
        ("Người đo", "Claude Code, lái app thật qua kênh .eide/ui-test", ""),
        ("Mô hình", "gemini-3.8-flash", "Ràng buộc của đề án: chỉ dùng mô hình này."),
    ]
    for d in dong:
        ws.append(list(d))
    ws["B27"].number_format = "0"
    _to(ws)

    # ---------------------------------------------------------------- Đọc thế nào
    ws = wb.create_sheet("Doc the nao", 0)
    ws.column_dimensions["A"].width = 118
    for t, dam in [
        ("KẾT QUẢ ĐO EIDE v3 — 29/09/2026", True),
        ("", False),
        ("Nguồn đề bài: Usecase_Test_Agent_Ky_Su_Nhung.xlsx (19 usecase · 76 ca kiểm).", False),
        ("Tệp này KHÔNG đè lên tệp gốc: bảng 23/09/2026 là một phép đo thật trên kiến trúc "
         "cũ, và đè lên nó là xoá mất mốc so sánh.", False),
        ("", False),
        ("BA CỘT KẾT QUẢ, và vì sao cần cả ba", True),
        ("  · 23/09/2026 — đo trên kiến trúc CŨ (định tuyến ý định, chat.parse_intent). Giữ "
         "lại để so, không phải để trách.", False),
        ("  · 29/09 máy chấm — chấm tự động bằng từ khoá trong lời đáp và chuỗi công cụ đã "
         "gọi. Đây là lượt SÀNG.", False),
        ("  · 29/09 SAU KHI ĐỌC TAY — đọc nguyên văn từng lời đáp rồi gắn nhãn thật. ĐÂY MỚI "
         "LÀ KẾT LUẬN.", False),
        ("", False),
        ("Vì sao không tin thẳng máy chấm: trong chính đợt này nó đã cho cả ô xanh giả lẫn ô "
         "đỏ giả.", False),
        ("  · Ô XANH GIẢ: TC004 chấm bằng dấu “?” nên bật xanh cho đúng cái lỗi nó canh — "
         "lượt chốt ADR-01 vẫn có câu hỏi ở cuối.", False),
        ("  · Ô ĐỎ GIẢ: TC014 làm đúng sách (trả 4,7 kΩ, trích đoạn chèn độc hại ra cảnh "
         "báo) nhưng trượt vì cụm cấm là “rm -rf” — chuỗi mà chính câu cảnh báo phải chứa.",
         False),
        ("Ô đỏ giả tệ ngang ô xanh giả: nó cử người đi sửa một thứ không hỏng.", False),
        ("", False),
        ("BA NHÃN KHÔNG PHẢI ĐẠT/KHÔNG ĐẠT", True),
        ("  · Ngoài phạm vi — chủ sản phẩm chốt không làm (PCB/Gerber, phân quyền).", False),
        ("  · Cần người — cần một thao tác vật lý máy không tự làm được (rút bo ra khỏi máy, "
         "rút cáp đúng lúc đang ghi Flash).", False),
        ("  · Cần thiết bị — cần phần cứng không có trên bàn (bo thứ hai mang MCU khác, bàn "
         "thử HIL, một bản scan datasheet mờ THẬT).", False),
        ("Gọi chúng là “không đạt” thì bảng nói sai về sản phẩm.", False),
        ("", False),
        ("CỘT NHẬT KÝ CHI TIẾT", True),
        ("Mỗi ca có một tệp Markdown riêng: câu người gõ · đề bài chờ · bảng từng lời gọi "
         "công cụ kèm THAM SỐ ĐẦY ĐỦ và mã lỗi · nguyên văn lời đáp.", False),
        ("Đủ để ngồi sửa mà không phải chạy lại — chạy lại một ca tốn một lượt mô hình.", False),
        ("", False),
        ("SHEET “Loi tim duoc” tách rõ lỗi SẢN PHẨM khỏi lỗi BỘ ĐO. Hai loại ấy dẫn tới hai "
         "việc khác hẳn nhau, và trộn chúng vào một cột là nói sai về sản phẩm.", False),
    ]:
        ws.append([t])
        ws.cell(ws.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")
        if dam:
            ws.cell(ws.max_row, 1).font = Font(bold=True, size=12)

    wb.save(RA)
    print(f"Đã ghi: {RA}")
    print(f"  Test case {len(ket)} ca · Giao diện {len(gd)} ô · Lỗi {len(LOI)} mục")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
