# -*- coding: utf-8 -*-
"""Phiên sinh viên học nhúng — vòng kín từ tài liệu yêu cầu tới robot đứng trên bo thật.

Khác hai phiên robot trước ở ba chỗ, và cả ba chỗ đều là chủ ý:

1. **Đầu vào là TÀI LIỆU YÊU CẦU PHẦN MỀM**, không phải hồ sơ bàn giao phần cứng. Tài liệu đó
   đã có đủ 28 tham số đã chạy được. Nên phiên này không đo "tác tử có tự nghĩ ra được tham
   số không" — câu đó đã trả lời rồi, và trả lời là KHÔNG. Nó đo câu khác: *cho một đặc tả đủ
   số, tác tử có đi hết vòng mà không tự bỏ bước nào không.*

2. **Dự án trống.** Không chép firmware cũ sang. Nếu chép thì tác tử đọc ra đáp án và phiên
   này không đo gì cả.

3. **Có người trong vòng.** Giai đoạn 5 dừng lại, chờ anh Công cắm bo và nói robot ngã về phía
   nào, rồi đưa đúng câu đó vào làm lượt tiếp. Ba dấu của vòng điều khiển chỉ đo được như vậy.

Mọi lượt đi qua GIAO DIỆN EIDE THẬT. Ảnh từng mốc do chính app vẽ ra cửa sổ của nó, không dùng
`screencapture`.

Chạy:
    .venv/bin/python tools/phien_sinhvien_robot.py --giai-doan 1
    .venv/bin/python tools/phien_sinhvien_robot.py --giai-doan 5 --quan-sat "robot ngã về trước, bánh trái quay ngược"
    .venv/bin/python tools/phien_sinhvien_robot.py --buoc 7-9 --giu-du-an
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from phien_robot import (NhatKy, cong_cu_da_goi, doi_chieu_app_voi_nguon, hoi,
                         so_dong_so_cai)   # noqa: E402
from thu_giao_dien import GiaoDien                                     # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

DU_AN = REPO / "du-lieu/robot-sinhvien"
RA = REPO / "du-lieu/ket-qua/robot-sinhvien"
TAI_LIEU = (REPO / "docs/robot-tu-can-bang"
            / "YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx")

# Chỗ giữ câu quan sát của người, để lượt sau đọc lại được và để báo cáo tra lại được.
QUAN_SAT = RA / "quan-sat-nguoi.jsonl"


def mo_app(du_an: pathlib.Path) -> GiaoDien:
    """Mở app với `EIDE_GHI_LLM=1`.

    Gọi thẳng tệp nhị phân chứ không `open -a`: LaunchServices không mang biến môi trường của
    vỏ lệnh sang, mà biến đó phải tới được lõi — lõi là tiến trình con của app.
    """
    doi_chieu_app_voi_nguon()
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    het = time.time() + 20
    while time.time() < het:
        if subprocess.run(["pgrep", "-f", "EIDE.app/Contents/MacOS/EIDE"],
                          capture_output=True).returncode != 0:
            break
        time.sleep(0.5)
    time.sleep(1.0)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(du_an)], check=True)
    g = GiaoDien(du_an)

    # Nới hạn lượt cho phần viết mã.
    #
    # Đo được ở lượt đầu của bước "viết firmware": tác tử dùng 31 trong 40 lời gọi cho
    # `fact.from_doc` — tức chỉ để đưa chính những con số của tài liệu vào kho Fact, vì lớp
    # cấp quyền không cho ghi hằng số chưa truy vết được nguồn. Hết ngân sách trước khi ghi
    # nổi một tệp. Viết mười mô-đun là việc **dài hơn một lượt ngay từ bản chất công việc**,
    # không phải vì tác tử chậm — đúng tình huống mà §B1 đã nới cho việc FPGA.
    #
    # Mặc định của kho KHÔNG đổi; chỉ phiên này đặt biến.
    env = {**os.environ, "EIDE_GHI_LLM": "1"}
    if os.environ.get("PHIEN_NOI_HAN"):
        env["EIDE_TRAN_LOI_GOI_LUOT"] = os.environ.get("EIDE_TRAN_LOI_GOI_LUOT", "200")
        env["EIDE_TRAN_GIAY_LUOT"] = os.environ.get("EIDE_TRAN_GIAY_LUOT", "1800")
        print(f"{VANG}Nới hạn lượt: {env['EIDE_TRAN_LOI_GOI_LUOT']} lời gọi · "
              f"{env['EIDE_TRAN_GIAY_LUOT']} giây{HET}")

    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(90)
    return g


# ===================================================================== các bước
#
# Mỗi bước là MỘT câu sinh viên gõ vào ô nhập. Nguyên tắc viết câu:
#   - Nói việc cần, KHÔNG nhắc tên công cụ. Nhắc tên công cụ là mớm bài, và mớm bài thì phép
#     đo đang đo chính lời mớm chứ không đo tác tử.
#   - Luôn đòi SỐ ĐO kèm chỗ lấy số. Lời "đã xong" không được tính là kết quả.
#   - Chỗ nào tài liệu đã chốt con số thì bắt đối chiếu lại với tài liệu, không cho tự nhớ.
#
# (tên bước, câu gõ, giây chờ, giai đoạn, cần người quan sát)
BUOC: list[tuple[str, str, int, int, bool]] = [

    # ---------------------------------------------------------- 1 · TÌM HIỂU
    ("Đọc tài liệu yêu cầu",
     "Chào bạn. Mình là sinh viên đang làm đồ án về lập trình nhúng, đề tài robot hai bánh "
     "tự cân bằng. Mình chưa từng làm bài điều khiển cân bằng nào nên sẽ nhờ bạn khá nhiều. "
     "Mình vừa đưa vào dự án một tệp tài liệu yêu cầu phần mềm. Bạn đọc hết giúp mình rồi "
     "tóm tắt lại: tài liệu chia làm mấy phần, robot phải làm được những việc gì, chạy trên "
     "vi điều khiển nào, có những khối phần cứng nào. Nói rõ tài liệu này cho sẵn những gì "
     "và bắt mình phải tự làm những gì.", 900, 1, False),

    ("Kê bảng ràng buộc và bốn điều cấm",
     "Cảm ơn bạn. Giờ mình cần một bảng tra để lúc viết mã khỏi quên. Bạn đọc lại tài liệu "
     "rồi kê cho mình thành bảng: mọi điều kiện bắt buộc và mọi điều bị cấm, mỗi dòng ghi rõ "
     "lấy ở mục nào của tài liệu. Riêng phần bị cấm thì giải thích thêm giúp mình vì sao "
     "cấm, vì mình đọc mà chưa hiểu hết lý do.", 900, 1, False),

    ("Hỏi những chỗ tài liệu chưa nói",
     "Trước khi thiết kế, mình muốn chắc một chuyện. Bạn rà lại tài liệu và nói thẳng cho "
     "mình biết: có con số hay chi tiết nào bạn sẽ cần khi viết mã mà tài liệu KHÔNG ghi "
     "không? Nếu có thì liệt kê ra để mình đi tìm, đừng tự điền giá trị mình đoán. Mình đã "
     "đọc một bài học là tự nhớ hằng số phần cứng thì sẽ tự chế ra bằng chứng sai.", 900, 1, False),

    # ------------------------------------------------- 2 · PHÂN TÍCH & THIẾT KẾ
    #
    # Bước này sinh ra TỪ câu trả lời của tác tử ở bước 3: nó chỉ ra tài liệu không nói trục
    # nào là trục nghiêng, trục nào là trục xoay. Đọc lại mã bản đã chạy thì đúng là thiếu —
    # tài liệu chỉ viết "trục trước sau" và "trục xoay" mà không nói đó là byte nào trong 14
    # byte. Nên tài liệu được sửa lên bản 1.1, và lượt này đưa bản sửa vào.
    ("Nạp lại tài liệu đã sửa theo chỗ bạn chỉ ra",
     "Bạn chỉ ra đúng một chỗ thiếu: tài liệu không nói trục nào là trục nghiêng, trục nào là "
     "trục xoay. Mình đã về sửa tài liệu, thêm một mục mới kê rõ mười bốn byte đọc từ cảm "
     "biến thì byte nào là số đo nào, và trong sáu số đo thì vòng điều khiển dùng ba số nào. "
     "Bản mới đã nằm trong dự án, cùng tên tệp. Bạn nạp lại rồi đọc mục mới đó, nhắc lại cho "
     "mình nghe ánh xạ trục để mình chắc là bạn đọc đúng. Nếu mục mới vẫn còn thiếu gì thì "
     "nói tiếp, mình sửa tiếp.", 900, 2, False),

    ("Bản đồ chân, đối chiếu lại với tài liệu",
     "Bắt đầu phần thiết kế nhé. Việc đầu tiên: lập cho mình bản đồ chân của toàn bộ hệ "
     "thống, chân nào nối gì, hướng vào hay ra. Làm xong thì đối chiếu lại từng dòng với "
     "bảng chân trong tài liệu và báo cho mình số dòng khớp trên tổng số dòng. Mình muốn "
     "thấy con số đối chiếu, không chỉ muốn nghe là đã khớp.", 900, 2, False),

    ("Ba phương án kiến trúc, so bằng số",
     "Giờ bạn nêu cho mình ba phương án kiến trúc phần mềm khác nhau cho bài này, so sánh "
     "bằng số chứ không bằng lời: cách tổ chức các nhịp thời gian, cách sinh xung bước, mỗi "
     "phương án tốn bao nhiêu byte bộ nhớ chạy và chiếm bao nhiêu phần trăm thời gian của "
     "chip. Nói rõ rủi ro từng phương án, rồi đề xuất một cái kèm lý do. Mình sẽ duyệt.", 900, 2, False),

    ("Máy trạng thái và bảng tiếng còi",
     "Mình chốt phương án bạn đề xuất. Giờ thiết kế chi tiết phần vận hành: vẽ cho mình máy "
     "trạng thái đầy đủ, mỗi trạng thái robot đang làm gì, mỗi lần chuyển trạng thái do sự "
     "kiện gì và mất bao lâu, động cơ có phát xung hay không. Kèm một bảng tiếng còi: nghe "
     "tiếng nào thì biết robot đang ở trạng thái nào. Đối chiếu lại với bảng trạng thái và "
     "bảng còi trong tài liệu, lệch chỗ nào thì nói ra chỗ đó.", 900, 2, False),

    # Bước này sinh ra TỪ một cổng chặn, và cổng ấy chặn đúng người sai: ở bước 7 câu chốt
    # của mình là "Mình chốt phương án bạn đề xuất." — có chữ mang nghĩa lựa chọn nhưng
    # không nhắc tên phương án nào, nên `store.option_choose` trả E5009 và quyết định thiết
    # kế KHÔNG được ghi vào kho. Nếu cứ thế đi sang viết mã thì mã sẽ không gắn với phương
    # án nào cả. Nên chốt lại bằng câu có gọi đúng tên.
    ("Chốt lại phương án bằng đúng tên",
     "Mình xem lại thì câu chốt vừa rồi của mình nói không rõ, nên hệ thống không ghi được "
     "là mình đã chọn cái nào. Mình nói lại cho rõ: mình chọn phương án Kiến trúc 3 tầng "
     "thời gian độc lập. Bạn ghi quyết định này vào kho giúp mình, kèm lý do mình chọn là nó "
     "khớp với ràng buộc thời gian thực mà tài liệu đã bắt buộc. Ghi xong thì cho mình xem "
     "lại là kho đã nhận quyết định chưa, đừng chỉ nói là đã ghi.", 900, 2, False),

    # ------------------------------------------------------- 3 · LẬP TRÌNH
    ("Chia việc trước khi viết",
     "Thiết kế ổn rồi. Trước khi gõ mã, bạn lập cho mình kế hoạch chia việc: sẽ có những tệp "
     "nào, mỗi tệp làm gì, viết theo thứ tự nào và vì sao thứ tự đó. Mình muốn biết đường đi "
     "trước khi bạn bắt đầu, để giữa đường mình còn theo được.", 900, 3, False),

    ("Viết firmware theo đúng tham số của tài liệu",
     "Giờ viết firmware đi bạn. Một việc mình nhấn mạnh: tài liệu có một bảng tham số nói rõ "
     "là những con số đó đã chạy được trên bo thật. Bạn lấy đúng từng con số trong bảng đó, "
     "đừng đổi, đừng làm tròn, đừng tự chọn giá trị khác vì thấy hợp lý hơn. Nếu có con số "
     "nào bạn thấy sai thì nói cho mình trước, chứ đừng tự sửa. Viết xong thì liệt kê lại "
     "từng tham số bạn đã đặt vào mã kèm tên tệp và số dòng, để mình soát.", 2400, 3, False),

    ("Biên dịch và tính bộ nhớ cho đủ",
     "Biên dịch giúp mình xem có lỗi gì không. Rồi cho mình biết firmware chiếm bao nhiêu bộ "
     "nhớ chương trình và bao nhiêu bộ nhớ chạy, so với giới hạn của chip. Lưu ý giúp mình "
     "cách tính: tài liệu có nhắc là lấy riêng một đoạn thì ra số nhỏ hơn thực tế. Bạn nói rõ "
     "mình cộng những đoạn nào lại.", 900, 3, False),

    ("Tự chứng minh hàm ngắt không vi phạm điều cấm",
     "Tài liệu cấm dùng số thực và phép chia trong hàm ngắt nhanh nhất. Mình không muốn tin "
     "lời, mình muốn thấy bằng chứng. Bạn tìm cách mở tệp đã dịch ra xem máy thật sự chạy "
     "những lệnh gì trong hàm ngắt đó, rồi báo cho mình: có lệnh gọi hàm nào không, có lệnh "
     "chia nào không, có hàm số thực nào không, và tổng cộng bao nhiêu lệnh.", 1200, 3, False),

    # Hai bước dưới đây sinh ra từ ĐO ĐƯỢC, không từ kế hoạch:
    #
    #  - Bước "viết firmware" hết ngân sách 40 lời gọi khi mới nạp xong 30 Fact, chưa ghi nổi
    #    tệp nào. Lớp cấp quyền chặn `fs.write` vì hằng số chưa truy vết được nguồn — chặn
    #    đúng. Nên cần một lượt "làm tiếp", chạy lại được nhiều lần.
    #
    #  - Bước "tự chứng minh hàm ngắt" trả về một bảng bằng chứng với kết luận "HOÀN TOÀN
    #    KHÔNG có lệnh call", kèm số lệnh ước lượng theo từng khối — trong khi chưa có tệp
    #    nào được dịch và cả lượt chỉ gọi `doc.read` 5 lần. Đó là đọc đặc tả rồi kể lại,
    #    không phải đo. Phải rút lại, và phải nói rõ vì sao nó sai.
    ("Viết tiếp cho xong mã",
     "Lượt trước bạn hết ngân sách lời gọi khi vừa nạp xong các Fact, chưa ghi được tệp nào. "
     "Mình đã nới ngân sách lượt cho bạn. Giờ viết tiếp cho xong, đừng đọc lại những thứ đã "
     "đọc. Làm xong tới đâu thì cuối lượt liệt kê cho mình tên từng tệp đã ghi và số dòng, "
     "còn tệp nào chưa viết thì ghi rõ là chưa viết.", 2400, 3, False),

    ("Rút lại câu trả lời về hàm ngắt",
     "Mình phải nói với bạn một chuyện. Lượt trước mình hỏi bạn mở tệp đã dịch ra xem máy "
     "thật sự chạy lệnh gì trong hàm ngắt. Bạn trả lời là hoàn toàn không có lệnh gọi hàm "
     "nào, kèm bảng số lệnh từng khối. Nhưng lúc đó chưa có tệp nào được dịch cả, và cả lượt "
     "bạn chỉ gọi công cụ đọc tài liệu. Nên câu trả lời đó là đọc đặc tả rồi kể lại, không "
     "phải đo trên tệp đã dịch. Mình không coi đó là bằng chứng.\n\n"
     "Mình cần hai việc. Một: bạn xác nhận lại là câu trả lời đó không có giá trị làm bằng "
     "chứng, và nói cho mình biết vì sao lúc ấy bạn lại trả lời như đã đo. Hai: từ giờ, khi "
     "mình hỏi một con số mà bạn chưa đo được, bạn nói thẳng là chưa đo được — mình thà "
     "không có số còn hơn có một con số trông như đã đo.", 1200, 3, False),

    # Bước này sinh ra từ việc đọc MÃ TRÊN ĐĨA, không từ việc đọc lời tác tử. Tác tử báo đã
    # viết xong 8 tệp và `build.compile` ĐẠT — cả hai đều đúng. Nhưng đối chiếu `config.h`
    # với Bảng 1.3 thì bốn chỗ lệch, và bản dịch vẫn xanh. Một bản dịch xanh không nói gì về
    # việc mã có nối đúng chân hay không.
    ("Đối chiếu bản đồ chân trong mã với Bảng 1.3",
     "Mình vừa mở tệp firmware/config.h ra đọc và đối chiếu với Bảng 1.3 của tài liệu. Có "
     "bốn chỗ lệch, mình kê ra đây:\n\n"
     "1. Chiều bánh trái: tài liệu ghi chân D6, mã bạn viết D2.\n"
     "2. Xung bước bánh trái: tài liệu ghi chân D7, mã bạn viết D3.\n"
     "3. Còi ở chân D10 và nút bấm ở chân D12: mình grep cả tám tệp, không có một dòng nào "
     "nhắc tới hai chân này. Nghĩa là yêu cầu YC-01 báo hiệu bằng còi và YC-03 nhận lệnh từ "
     "nút bấm hiện chưa có trong mã.\n"
     "4. Chân D13: tài liệu nói rõ đây là chân đo thời gian chạy của hàm ngắt, và dặn đừng "
     "dùng cho việc khác vì đó là chỗ cắm máy hiện sóng khi nghiệm thu. Mã bạn viết đặt nó "
     "thành đèn báo trạng thái, mà tài liệu thì không có yêu cầu nào về đèn.\n\n"
     "Mình muốn ba việc. Một: nói cho mình biết con số D2 và D3 bạn lấy ở đâu ra, vì mình cần "
     "biết tài liệu của mình có chỗ nào gây hiểu sai không. Hai: sửa lại cho khớp Bảng 1.3 và "
     "làm cả phần còi với nút. Ba: sau khi sửa, tự đối chiếu lại từng dòng chân với Bảng 1.3 "
     "rồi báo mình số dòng khớp trên tổng số dòng.", 2400, 3, False),

    # ------------------------------------------------------- 4 · MÔ PHỎNG
    ("Nêu tiêu chí TRƯỚC khi chạy",
     "Sắp mô phỏng rồi. Nhưng bạn nêu tiêu chí nghiệm thu trước đã, đừng chạy vội. Tiêu chí "
     "phải bằng số: thế nào là vòng điều khiển chạy đúng nhịp, thế nào là robot đứng được, "
     "thế nào là phát hiện ngã kịp. Mình muốn tiêu chí được chốt trước khi có kết quả, vì "
     "nêu tiêu chí sau khi thấy kết quả thì tiêu chí sẽ bị uốn theo kết quả.", 900, 4, False),

    ("Chạy mô phỏng",
     "Giờ chạy mô phỏng đối chiếu với đúng những tiêu chí vừa chốt, rồi báo cho mình từng "
     "tiêu chí đạt hay không đạt, kèm số đo thật của từng tiêu chí. Nếu có tiêu chí nào "
     "không đạt thì cứ báo không đạt, mình cần biết đúng tình hình hơn là cần một bảng toàn "
     "màu xanh.", 1800, 4, False),

    ("Bộ kiểm có biết báo lỗi không",
     "Mô phỏng xanh thì mình chưa dám tin ngay, vì tài liệu có dặn: một phép đo báo đạt bất "
     "kể sản phẩm đúng hay sai thì nó không đo gì cả. Tài liệu nêu bốn phép phá bắt buộc. "
     "Bạn làm lần lượt bốn phép đó lên chính mã sản phẩm, chạy lại bộ kiểm sau mỗi lần, và "
     "báo cho mình bộ kiểm có báo lỗi hay không. Làm xong thì khôi phục mã lại nguyên như "
     "trước, và cho mình xem bảng bốn lần phá bốn lần báo lỗi.", 1800, 4, False),

    # Bước này là TRẢ LỜI cho `ask_user` của tác tử ở bước 18. Nó không tự dựng bảng kết quả
    # đột biến — nó dừng lại và hỏi bốn phép phá nằm ở đâu, kèm một bộ bốn phép nó tự đề
    # xuất. Bộ nó đề xuất khác bộ của tài liệu, nên phải trả lời bằng đúng bốn dòng Bảng 4.2.
    ("Bốn phép phá đúng theo Bảng 4.2",
     "Bốn phép phá nằm ở Chương 4, mục 4.2, Bảng 4.2 của tài liệu. Mình chép nguyên bốn dòng "
     "ra đây để bạn khỏi phải đi tìm:\n\n"
     "1. Số bù gia tốc: đổi từ 92 thành 535. Bài kiểm phải báo góc tính ra lệch khoảng 3,1 độ "
     "so với bản mẫu.\n"
     "2. Chiều tiến bánh trái: đổi từ mức thấp sang mức cao. Bài kiểm phải báo bit chân D6 "
     "khác bản mẫu.\n"
     "3. Chiều tiến bánh phải: đổi từ mức cao sang mức thấp. Bài kiểm phải báo bit chân D4 "
     "khác bản mẫu.\n"
     "4. Dấu khi áp số bù: đổi phép cộng thành phép trừ. Bài kiểm phải báo góc tính ra lệch "
     "gấp đôi.\n\n"
     "Bốn phép bạn tự đề xuất thì cũng hợp lý, nhưng mình cần đúng bốn phép của tài liệu, vì "
     "danh mục nghiệm thu đang tính theo bốn phép ấy. Làm lần lượt từng phép lên chính mã sản "
     "phẩm, chạy lại bài kiểm sau mỗi lần, ghi lại bài kiểm báo gì. Xong thì khôi phục mã về "
     "nguyên trạng và cho mình xem bảng bốn lần phá bốn lần báo lỗi. Nếu có lần nào bài kiểm "
     "vẫn báo đạt thì nói thẳng ra — đó là thông tin mình cần nhất.", 2400, 4, False),

    ("A3 và A4 không đạt: lỗi sản phẩm hay lỗi phép đo",
     "Mô phỏng của bạn báo 3 đạt 2 không đạt, và mình cảm ơn vì bạn không đưa cho mình một "
     "bảng toàn xanh. Giờ mình cần tách rõ hai thứ. Với A3 là góc vọt lố 11,139 độ vượt "
     "ngưỡng 10 độ, và A4 là chưa bắt được sự kiện ngã trong cửa sổ 0,2 giây: từng cái một, "
     "bạn nói cho mình biết đó là lỗi của mã sản phẩm, hay là hạn chế của chương trình mô "
     "phỏng mình viết ra để đo.\n\n"
     "Và một điều mình muốn nói trước: nếu bạn thấy cần nới ngưỡng hay nới cửa sổ đo thì cứ "
     "đề xuất, nhưng đừng tự sửa. Đổi tiêu chí sau khi đã thấy kết quả là việc mình phải "
     "duyệt, không thì cái bảng nghiệm thu sẽ chỉ đo lại chính nó.", 1800, 4, False),

    # Hai bước dưới đây là chỗ nặng nhất của cả phiên, và cả hai sinh ra từ việc đọc mã chứ
    # không từ việc đọc lời tác tử.
    #
    # Bước 21: mã dùng sai cả BA trục so với Bảng 3.2 — đúng cái bảng mà chính tác tử đòi
    # thêm ở bước 3, và đã đọc lại đúng ở bước 4. Cùng một dạng với lỗi D2/D3: có bảng đúng
    # trong tay, đọc lại đúng, rồi viết mã theo thói quen.
    #
    # Bước 22: bốn phép phá đều sống sót, và tác tử đã tự chẩn đúng hai cơ chế. Phải vá bộ
    # đo trước khi ra bo, không thì mọi phép đo sau đây đều vô nghĩa.
    ("Mã dùng sai cả ba trục của cảm biến",
     "Mình mở firmware/mpu6050.cpp và firmware/control.cpp ra đọc, rồi đối chiếu với Bảng 3.2 "
     "của tài liệu. Cả ba trục đều lệch:\n\n"
     "- Trục trước sau: tài liệu ghi byte 4 và 5, tức accel_z. Mã bạn dùng accel_y, tức byte "
     "2 và 3.\n"
     "- Trục nghiêng: tài liệu ghi byte 10 và 11, tức gyro_y. Mã bạn dùng gyro_x, tức byte 8 "
     "và 9.\n"
     "- Trục xoay: tài liệu ghi byte 8 và 9, tức gyro_x. Mã bạn dùng gyro_z, tức byte 12 và "
     "13.\n\n"
     "Phần tách 14 byte trong mpu6050.cpp thì đúng, có bỏ hai byte nhiệt độ. Lệch nằm ở chỗ "
     "gán vai trò.\n\n"
     "Điều mình muốn bạn nghĩ cùng mình: Bảng 3.2 là bảng do chính bạn đòi mình thêm vào ở "
     "lượt thứ ba, vì lúc đó bạn nói tài liệu chưa nói trục nào là trục nào. Mình thêm vào, "
     "rồi lượt sau bạn đọc lại nó đúng từng dòng cho mình nghe. Vậy mà lúc viết mã thì lại "
     "dùng bộ trục khác. Đây là lần thứ hai trong phiên, lần trước là chân D2 với D3. Bạn nói "
     "cho mình biết chỗ nào trong cách bạn làm việc dẫn tới chuyện đó, vì mình cần biết để "
     "lần sau đặt câu hỏi khác đi.\n\n"
     "Rồi sửa lại cho khớp Bảng 3.2, và sau khi sửa thì đối chiếu lại từng trục rồi báo mình.",
     2400, 4, False),

    ("Vá bộ đo cho nó bắt được bốn phép phá",
     "Bốn phép phá đều sống sót, và bạn đã tự chẩn đúng hai cơ chế: bộ sinh dữ liệu mô phỏng "
     "dùng chính macro số bù nên khi phá macro thì hai bên tự triệt tiêu, và bộ mô phỏng liên "
     "kết với mock_motor.c nên không bao giờ chạm tới motor.cpp là nơi ghi bit chân. Mình đã "
     "kiểm lại cả hai chỗ trong mã và bạn chẩn đúng.\n\n"
     "Giờ vá bộ đo. Ba việc:\n\n"
     "1. Bộ sinh dữ liệu mô phỏng không được dùng lại macro số bù. Hãy dùng một dãy số đo "
     "mẫu cố định, để khi mã sản phẩm sai thì kết quả lệch đi chứ không triệt tiêu.\n"
     "2. Bài kiểm phải dịch thẳng firmware/motor.cpp và kiểm được bit chân DIR, chứ không "
     "dùng mock thay cho nó. Phần nào thật sự là phần cứng thì mới được mock.\n"
     "3. Thêm một phép so với dãy góc mẫu, để phá dấu hay phá số bù thì thấy lệch.\n\n"
     "Vá xong thì chạy lại đúng bốn phép phá của Bảng 4.2. Lần này bài kiểm phải báo lỗi cả "
     "bốn lần. Nếu còn phép nào sống sót thì nói thẳng là còn, đừng vá cho vừa đủ qua.", 2400, 4, False),

    # Bước này là chỗ sâu nhất của cả phiên. Bộ đo sau khi vá thì BẮT ĐƯỢC cả bốn phép phá —
    # nhưng nó bắt theo một mức kỳ vọng SAI. Mã sản phẩm đặt D6 lên mức CAO khi tiến, tài
    # liệu Bảng 3.3 ghi mức THẤP, và bài kiểm mới đi khẳng định mức CAO là đúng.
    #
    # Một bài kiểm nhạy mà chỉnh sai mốc thì tệ hơn một bài kiểm không nhạy: nó chủ động bảo
    # vệ cái lỗi. Sửa mã cho khớp tài liệu thì bài kiểm sẽ báo đỏ lên mã đúng.
    ("Bài kiểm nhạy nhưng chỉnh sai mốc",
     "Bộ đo của bạn giờ bắt được cả bốn phép phá, và mình ghi nhận việc đó. Nhưng mình đọc kỹ "
     "lời bạn viết thì thấy một chỗ phải dừng lại.\n\n"
     "Bạn viết bài kiểm khẳng định: chân D6 phải ở mức CAO khi tốc độ bánh trái lớn hơn hoặc "
     "bằng 0. Mình mở Bảng 3.3 của tài liệu ra đọc, nó ghi ngược lại: chiều tiến bánh trái là "
     "mức THẤP ở chân D6. Mình mở firmware/motor.cpp dòng 58 và 59 thì thấy mã của bạn đặt D6 "
     "lên mức CAO khi tiến. Nghĩa là mã sai so với tài liệu, và bài kiểm thì đi khẳng định "
     "cái sai đó là đúng.\n\n"
     "Chỗ này mình muốn nói cho rõ, vì nó quan trọng hơn bản thân lỗi: một bài kiểm nhạy mà "
     "chỉnh sai mốc thì tệ hơn một bài kiểm không nhạy. Bài kiểm không nhạy thì chỉ là không "
     "đo được gì. Bài kiểm nhạy mà sai mốc thì nó chủ động bảo vệ cái lỗi — ai sửa mã cho "
     "khớp tài liệu sẽ thấy bài kiểm báo đỏ, rồi tưởng mình vừa làm hỏng.\n\n"
     "Mình đoán nguyên nhân là bạn viết bài kiểm bằng cách đọc mã rồi ghi lại mã đang làm gì. "
     "Làm thế thì bài kiểm chỉ xác nhận lại chính mã, không bao giờ bắt được lỗi của mã.\n\n"
     "Ba việc mình cần:\n\n"
     "1. Sửa chiều bánh trái trong mã cho khớp Bảng 3.3. Và đặt hai hằng số chiều tiến ra "
     "config.h kèm trích chỗ lấy, đừng viết cứng mức logic trong motor.cpp — hiện config.h "
     "không có hằng số chiều tiến nào, nên không ai soát được nó đúng hay sai.\n"
     "2. Sửa bài kiểm để mức kỳ vọng lấy từ Bảng 3.3, không lấy từ hành vi hiện thời của mã.\n"
     "3. Chạy lại bốn phép phá. Và chạy thêm một phép nữa: sửa chiều bánh trái về đúng mức "
     "CAO như cũ, bài kiểm phải báo đỏ. Nếu nó báo xanh thì mốc vẫn còn sai.", 2400, 4, False),

    # --------------------------------------------------- 5 · PHẦN CỨNG THẬT
    ("Dò bo và nạp lần đầu",
     "Mình đã cắm bo vào máy rồi. Bạn dò xem có nhận ra bo không, nhận ra chip gì, rồi nạp "
     "firmware vào. Nạp xong thì đọc ngược lại từ chip để so với tệp vừa nạp, và báo cho "
     "mình số byte lệch. Một điều mình được dặn: công cụ nạp so tệp trên chip với đúng cái "
     "tệp mình đưa cho nó, nên nếu đưa sai tệp thì nó vẫn báo không lệch. Bạn tìm thêm một "
     "cách nữa để chắc là bo đang chạy đúng bản vừa dịch.", 1800, 5, False),

    ("Nghe cổng nối tiếp xem bo đang chạy gì",
     "Giờ mở cổng nối tiếp đọc cho mình xem bo đang nói gì. Mình muốn thấy dòng nhận dạng "
     "lúc khởi động, và dòng số đo chạy đều. Đọc xong thì giải thích từng cột số đo đó nghĩa "
     "là gì, để lát nữa mình ngồi nhìn còn hiểu.", 1200, 5, False),

    ("Người quan sát — lượt một",
     "Mình vừa đặt robot xuống và làm theo trình tự trong tài liệu. Đây là những gì mình "
     "thấy và nghe, nguyên văn:\n\n{quan_sat}\n\n"
     "Từ đúng những gì mình vừa kể, bạn suy ra được điều gì? Mình muốn bạn nói rõ ba phần "
     "riêng: một là quan sát này loại trừ được khả năng nào, hai là nó chưa nói được gì, ba "
     "là bước đo tiếp theo mình nên làm để tách phần còn lại. Đừng sửa mã ngay, vì mình chưa "
     "biết lỗi nằm ở phần cứng hay phần mềm.", 1800, 5, True),

    ("Ba bài đo tách dấu",
     "Tài liệu có ba bài đo để tách ba dấu của vòng điều khiển, vì khi robot đứng yên thì ba "
     "dấu nhân lại thành một dấu nên đọc mã không tách ra được. Bạn hướng dẫn mình làm lần "
     "lượt ba bài đó: mình phải bấm gì, giữ bao lâu, nghe tiếng gì, nhìn cái gì, và kết quả "
     "nào thì nghĩa là dấu nào đang sai. Viết thành từng bước ngắn để mình vừa đọc vừa làm "
     "được, vì hai tay mình đang giữ robot.", 1200, 5, False),

    ("Người quan sát — lượt hai, sau ba bài đo",
     "Mình làm xong ba bài đo. Kết quả nguyên văn:\n\n{quan_sat}\n\n"
     "Giờ thì đã tách được dấu chưa? Nếu có chỗ cần sửa trong mã thì sửa, nhưng trước khi "
     "sửa bạn nói cho mình biết sẽ sửa cái gì và vì sao, rồi hãy sửa. Sửa xong thì nạp lại "
     "và báo mình số byte lệch.", 1800, 5, True),

    ("Người quan sát — lượt chốt",
     "Mình thử lại sau khi bạn sửa. Kết quả nguyên văn:\n\n{quan_sat}\n\n"
     "Bạn đánh giá giúp mình: đã đạt chưa, còn thiếu gì. Nếu còn thiếu thì nói rõ bước đo "
     "tiếp theo chứ đừng đoán tiếp.", 1800, 5, True),

    # ----------------------------------------------------------- 6 · CHỐT
    ("Soát lại chín điều nghiệm thu",
     "Tài liệu có một danh mục chín điều nghiệm thu, mỗi điều đòi một số đo chứ không nhận "
     "lời nói. Bạn soát lại cả chín điều, mỗi điều ghi: đạt hay chưa, số đo là bao nhiêu, và "
     "lấy số đó ở đâu. Điều nào chưa làm thì ghi chưa làm, đừng ghi đạt.", 1200, 6, False),

    ("Tự kê những chỗ mình đã báo xong mà chưa xong",
     "Câu cuối, và mình hỏi thật. Trong cả phiên này, có lúc nào bạn báo với mình là đã xong "
     "hoặc đã kiểm, mà thực ra lúc đó chưa xong hoặc phép kiểm chưa đo được cái cần đo "
     "không? Nếu có thì kê ra hết, kèm lượt nào. Mình cần biết để viết vào báo cáo, và mình "
     "sẽ không coi đó là lỗi của bạn nếu bạn tự nói ra.", 1200, 6, False),

    ("Xuất tài liệu tổng kết",
     "Cuối cùng, bạn làm cho mình một tệp tài liệu tổng kết cả phiên để mình nộp kèm đồ án: "
     "đã đi qua những bước nào, mỗi bước số đo ra sao, chỗ nào phải sửa và vì sao, chỗ nào "
     "còn chưa xong. Ghi cả những lần sai, đừng chỉ ghi phần thành công.", 1800, 6, False),
]

TEN_GIAI_DOAN = {
    1: "Tìm hiểu",
    2: "Phân tích và thiết kế",
    3: "Lập trình",
    4: "Mô phỏng",
    5: "Phần cứng thật — có người trong vòng",
    6: "Chốt và báo cáo",
}


def dung_du_an(giu: bool) -> None:
    """Dựng dự án TRỐNG, chỉ có tệp tài liệu yêu cầu.

    Không chép firmware cũ sang. Chép sang thì tác tử đọc ra đáp án, và phiên này không còn
    đo được gì ngoài khả năng chép tệp.
    """
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    (DU_AN / ".eide" / "ui-test").mkdir(parents=True, exist_ok=True)
    (DU_AN / "tai-lieu").mkdir(exist_ok=True)
    dich = DU_AN / "tai-lieu" / TAI_LIEU.name
    if not dich.exists():
        shutil.copy(TAI_LIEU, dich)
    RA.mkdir(parents=True, exist_ok=True)


def ghi_quan_sat(buoc: int, ten: str, cau: str) -> None:
    with QUAN_SAT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"buoc": buoc, "ten": ten, "nguoi_noi": cau,
                            "luc": time.strftime("%Y-%m-%d %H:%M:%S")},
                           ensure_ascii=False) + "\n")


def chay(buoc_chon: set[int] | None, giu: bool, quan_sat: str) -> int:
    from eide.config import load_dotenv

    load_dotenv()
    dung_du_an(giu)

    nk = NhatKy(RA, tieu_de="phiên sinh viên — vòng kín robot hai bánh tự cân bằng",
                nguon=str(TAI_LIEU.relative_to(REPO)),
                du_an=str(DU_AN.relative_to(REPO)))

    # Kiểm trước khi mở app: bước nào cần người mà chưa có câu quan sát thì dừng ngay, đừng
    # mở app rồi mới phát hiện. Mở app xong mới dừng là bỏ một lượt khởi động vô ích.
    thieu = [(i, t) for i, (t, _, _, _, can) in enumerate(BUOC, 1)
             if can and (not buoc_chon or i in buoc_chon) and not quan_sat.strip()]
    if thieu:
        print(f"{DO}Bước cần câu quan sát của người mà chưa có:{HET}")
        for i, t in thieu:
            print(f"  bước {i}: {t}")
        print(f"\n{VANG}Thêm: --quan-sat \"robot ngã về trước, bánh trái quay ngược, "
              f"còi kêu hai tiếng\"{HET}")
        return 2

    g = mo_app(DU_AN)
    da_chay = 0

    for i, (ten, cau, giay, gd, can_nguoi) in enumerate(BUOC, 1):
        if buoc_chon and i not in buoc_chon:
            continue

        if can_nguoi:
            cau = cau.replace("{quan_sat}", quan_sat.strip())
            ghi_quan_sat(i, ten, quan_sat.strip())

        nk.buoc(f"[Giai đoạn {gd} · {TEN_GIAI_DOAN[gd]}] {ten}")
        print(f"\n{VANG}── bước {i}/{len(BUOC)} · giai đoạn {gd} · {ten}{HET}")

        truoc = so_dong_so_cai(DU_AN)
        hoi(g, nk, DU_AN, cau, giay=giay)

        # Ảnh giao diện ở TỪNG bước, không chỉ cuối giai đoạn. Ảnh do app tự vẽ cửa sổ của
        # nó, không dùng `screencapture`.
        nk.anh(g, f"{ten.lower().replace(' ', '-')[:34]}")

        # Sở cứ: công cụ tác tử đã gọi trong đúng lượt này, đọc từ sổ cái của app.
        cc = cong_cu_da_goi(DU_AN, tu=truoc)
        dat = sum(1 for c in cc if c.get("ok"))
        nk.ghi("Công cụ đã gọi trong lượt này",
               f"{len(cc)} lời gọi ({dat} chạy được · {len(cc) - dat} báo lỗi): "
               + ", ".join(sorted({c['tool'] for c in cc})) if cc
               else "Không gọi công cụ nào.")
        print(f"{XAM}  công cụ: {len(cc)} lời gọi, {dat} chạy được{HET}")
        da_chay += 1

    # Đếm nhật ký mô hình để phần "lưu đủ log" có con số kiểm lại được, không phải lời hứa.
    llm = sorted((DU_AN / ".eide" / "llm").glob("*.jsonl"))
    n = sum(1 for p in llm for d in p.read_text("utf-8", errors="replace").splitlines()
            if d.strip())
    so_cai = so_dong_so_cai(DU_AN)
    anh = len(list((RA / "anh").glob("*.png")))

    nk.ghi("Dấu vết phiên để lại",
           f"Sổ cái {so_cai} dòng · nhật ký mô hình {len(llm)} tệp / {n} lời gọi · "
           f"{anh} ảnh cửa sổ EIDE · bản ghi quan sát của người: {QUAN_SAT.name}")

    print(f"\n{XANH}Đã chạy {da_chay} bước.{HET}")
    print(f"{VANG}Nhật ký: {nk.md}{HET}")
    print(f"{XAM}Sổ cái {so_cai} dòng · {n} lời gọi mô hình · {anh} ảnh{HET}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phiên sinh viên — vòng kín từ tài liệu yêu cầu tới bo thật")
    ap.add_argument("--giai-doan", type=int, choices=sorted(TEN_GIAI_DOAN),
                    help="chạy cả một giai đoạn")
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-3 hoặc 7")
    ap.add_argument("--quan-sat", default="",
                    help="câu người quan sát được trên bo thật, dùng cho các bước cần người")
    ap.add_argument("--giu-du-an", action="store_true",
                    help="không xoá dự án cũ (bắt buộc dùng khi chạy tiếp giai đoạn sau)")
    ap.add_argument("--liet-ke", action="store_true", help="in danh sách bước rồi thoát")
    a = ap.parse_args()

    if a.liet_ke:
        gd_truoc = 0
        for i, (ten, _, giay, gd, can) in enumerate(BUOC, 1):
            if gd != gd_truoc:
                print(f"\n{VANG}Giai đoạn {gd} — {TEN_GIAI_DOAN[gd]}{HET}")
                gd_truoc = gd
            dau = f"{DO}[cần người]{HET} " if can else ""
            print(f"  {i:2d}. {dau}{ten}  {XAM}(chờ tối đa {giay}s){HET}")
        return 0

    chon: set[int] | None = None
    if a.giai_doan:
        chon = {i for i, (_, _, _, gd, _) in enumerate(BUOC, 1) if gd == a.giai_doan}
    if a.buoc:
        chon = set()
        for phan in a.buoc.split(","):
            if "-" in phan:
                x, y = phan.split("-", 1)
                chon |= set(range(int(x), int(y) + 1))
            else:
                chon.add(int(phan))

    # Giai đoạn 1 được phép dựng dự án mới. Từ giai đoạn 2 trở đi mà xoá dự án là xoá sạch
    # mã tác tử vừa viết, nên bắt buộc phải có --giu-du-an.
    if chon and min(chon) > 1 and not a.giu_du_an:
        print(f"{DO}Chạy từ bước {min(chon)} thì phải thêm --giu-du-an, "
              f"không thì dự án bị dựng lại từ trống.{HET}")
        return 2

    return chay(chon, a.giu_du_an, a.quan_sat)


if __name__ == "__main__":
    raise SystemExit(main())
