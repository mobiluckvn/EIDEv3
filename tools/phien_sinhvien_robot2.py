"""Phiên sinh viên — việc 3/3: robot hai bánh tự cân bằng, làm lại từ dự án trống.

Đầu vào: `docs/robot-sinhvien/YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx` bản 1.1,
cộng `docs/robot-sinhvien/PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md` — phụ lục vá hai lỗ trong chính
tài liệu của người, soát ra sau hai việc trước:

1. mốc so sánh không nằm trong tài liệu, nên bộ kiểm có thể so mã với chính nó;
2. không có dòng nghiệm thu nào đòi ĐO tần số ngắt, chỉ cho sẵn con số 50 kHz.

Ba ràng buộc như hai phiên trước: dự án TRỐNG, người đóng vai sinh viên không dùng trình độ
cao hơn, và mọi bước đi qua giao diện thật kèm ảnh cửa sổ EIDE.

    .venv/bin/python tools/phien_sinhvien_robot2.py --liet-ke
    .venv/bin/python tools/phien_sinhvien_robot2.py --buoc 1-3
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

DU_AN = REPO / "du-lieu/robot-sinhvien2"
RA = REPO / "du-lieu/ket-qua/robot-sinhvien2"
TAI_LIEU = REPO / "docs/robot-sinhvien/YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx"
PHU_LUC = REPO / "docs/robot-sinhvien/PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md"
QUAN_SAT = RA / "quan-sat-nguoi.jsonl"


def mo_app(du_an: pathlib.Path) -> GiaoDien:
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
    env = {**os.environ, "EIDE_GHI_LLM": "1",
           "EIDE_TRAN_GIAY_LUOT": os.environ.get("EIDE_TRAN_GIAY_LUOT", "3600"),
           "EIDE_TRAN_LOI_GOI_LUOT": os.environ.get("EIDE_TRAN_LOI_GOI_LUOT", "220")}
    print(f"{VANG}Hạn lượt: {env['EIDE_TRAN_LOI_GOI_LUOT']} lời gọi · "
          f"{env['EIDE_TRAN_GIAY_LUOT']} giây{HET}")
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(90)
    return g


# (tên, câu gõ, giây chờ, giai đoạn, cần người quan sát)
BUOC: list[tuple[str, str, int, int, bool]] = [

    # ------------------------------------- 1 · ĐỌC ĐỀ VÀ DỰNG MÔI TRƯỜNG
    ("Đọc tài liệu giao việc và phụ lục",
     "Chào bạn. Mình là sinh viên đang làm đồ án nhúng. Việc này là robot hai bánh tự cân "
     "bằng — nó phải tự đứng được, không có bánh chống.\n\n"
     "Mình vừa đưa vào dự án **hai tệp**:\n\n"
     "- `YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx` — tài liệu giao việc bản 1.1\n"
     "- `PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md` — phụ lục mình **vừa thêm hôm nay**\n\n"
     "Phụ lục ấy là chỗ mình **vá hai lỗ trong chính tài liệu của mình**, soát ra sau hai việc "
     "trước. Mình nói trước để bạn đọc nó cho kỹ, vì nó đổi cách nghiệm thu:\n\n"
     "**Lỗ 1 —** mục 4.1 đòi *khớp với bản mẫu đã chạy được* mà **không nói con số mốc ở "
     "đâu**. Nếu bạn tự sinh mốc bằng cách chạy mã của bạn thì bài kiểm chỉ so mã với chính "
     "nó — bắt được cả bốn phép phá mà vẫn bảo vệ nguyên cái lỗi. Chuyện này **đã xảy ra "
     "thật** ở một phiên trước. Phụ lục có **bảng A.1 và A.2** là mốc do mình tự tính từ công "
     "thức ở mục 2.2, không đọc mã nào.\n\n"
     "**Lỗ 2 —** tài liệu cho sẵn *ngắt 50 kHz* mà không có dòng nghiệm thu nào đòi **đo tần "
     "số thật**. Phụ lục thêm ba dòng `NT-A`, `NT-B`, `NT-C`.\n\n"
     "Bạn đọc hết cả hai rồi tóm tắt cho mình: mình cần làm gì, đạt nghĩa là gì, chỗ nào mình "
     "đã cho sẵn số và chỗ nào bạn phải tự tìm. Và nói luôn **chỗ nào bạn thấy tài liệu của "
     "mình còn mâu thuẫn hoặc còn thiếu** — mình viết nó nên mình cũng sai được.",
     1800, 1, False),

    ("Kiểm công cụ trước khi viết dòng nào",
     "Trước khi viết mã, cho mình biết **máy này có đủ công cụ chưa**: trình biên dịch cho "
     "ATmega328P có không, công cụ nạp có không, và bạn đọc được mã máy đã dịch không — câu "
     "cuối quan trọng vì dòng `NT-C` của mình đòi đọc `objdump`.\n\n"
     "Thiếu gì thì nói thiếu ngay. Ở việc trước mình gặp một nhánh công cụ **chưa từng chạy "
     "lần nào** nên nó nổ ngay lần gọi đầu, mà danh sách công cụ thì vẫn có tên nó.",
     1200, 1, False),

    ("Bốn điều cấm: nói lại bằng lời của bạn",
     "Mục 1.4 tài liệu có bốn điều cấm. Mình muốn bạn **nói lại từng điều bằng lời của bạn**, "
     "kèm trả lời: *vi phạm điều này thì triệu chứng nhìn thấy sẽ là gì?*\n\n"
     "Mình hỏi vì bốn điều ấy có một đặc tính chung mà mình muốn chắc bạn thấy: **vi phạm thì "
     "chương trình vẫn dịch được, vẫn nạp được**, và robot chỉ đơn giản là không đứng. Không "
     "có lỗi nào báo ra.\n\n"
     "Ở hai việc trước mình gặp **bảy lần** đúng dạng ấy — một cơ chế viết đúng mà không ai "
     "gọi tới, hoặc một hằng số cho sẵn mà không ai cài. Nên mình muốn vào việc này với mắt "
     "đã mở sẵn.",
     1800, 1, False),

    # ------------------------------------------ 2 · MÃ TRÊN MÁY VÀ BỘ KIỂM
    ("Năm chỗ bạn nêu: mình nhận bốn, trả lời một",
     "Bạn chỉ ra năm chỗ thiếu trong tài liệu của mình. Mình nhận bốn, và chỗ thứ nhất là lỗi "
     "thao tác của mình.\n\n"
     "**1 · Thiếu tệp phụ lục — đúng, và lỗi của mình.** Lượt trước mình nói đã đưa phụ lục "
     "vào dự án, nhưng lệnh chép của mình không chạy. **Bạn là người phát hiện**, và bạn phát "
     "hiện bằng cách đúng: ghi ra là thiếu thay vì đoán xem nó nói gì.\n\n"
     "Đây là lần thứ **ba** trong ngày mình khẳng định một tệp đã ở chỗ cần mà nó không ở đó. "
     "Gốc không phải thiếu cẩn thận: mình chạy một lệnh có thể thất bại rồi khẳng định kết quả "
     "mà **không kiểm hậu điều kiện** — đúng thứ mình đòi ở bạn suốt hai ngày. Mình đã vá bằng "
     "mã: bộ đo nay đếm và so kích thước từng tệp đầu vào, thiếu thì dừng phiên. Phụ lục giờ "
     "đã có thật trong `tai-lieu/`.\n\n"
     "**2 · `OCR2A = 39` với chia tần 8 — đúng, và đây là chỗ bạn bắt hay nhất.** Tài liệu "
     "mình nói ngắt 50 kHz và mỗi lần ngắt có 320 nhịp CPU. Cả hai đều đúng. Nhưng **320 không "
     "nhét được vào bộ đếm 8 bit**, và bảng 3.4 của mình không nói phải chia tần. Mình cho con "
     "số đích mà không cho đường tới nó — đúng loại lỗ đã làm mình mất một lượt nạp ở việc "
     "trước.\n\n"
     "Bạn tự chốt giá trị thanh ghi cho cả Timer2 và Timer0, và **nói rõ bạn tính ra bằng "
     "cách nào** để mình kiểm lại được.\n\n"
     "**3 · `fsm.c` gọi sang bốn tệp khác — đúng.** Mục 4.1 của mình khuyên tệp kiểm "
     "`#include` thẳng mã sản phẩm, và mình vẫn giữ nguyên tắc ấy, vì chép lại logic vào tệp "
     "kiểm là cách chắc chắn nhất để bài kiểm xanh mà không đo gì.\n\n"
     "Nhưng bạn đúng là phải có chỗ thay cho thanh ghi phần cứng. Mình nêu một ranh giới: "
     "**chỗ thay chỉ được thay PHẦN CỨNG, không được thay mã sản phẩm.** Ở một phiên trước có "
     "chuyện tệp kiểm tự định nghĩa lại hàm của sản phẩm, rồi phá mã thật mà bài kiểm vẫn "
     "xanh cả sáu ca.\n\n"
     "**4 · Điều kiện tự học điểm cân bằng và ngưỡng pin 420 — đúng cả hai.** Ngưỡng pin thì "
     "phải đo đồng hồ, mình sẽ làm khi tới đó.\n\n"
     "**Còn chỗ mình KHÔNG nhận:** bạn viết *số bù 92 là của bo mẫu, bo thật cần tự đo*. Đúng "
     "về phần cứng — nhưng **bảng A.1 trong phụ lục thì không phải số của bo**. Nó là mốc tính "
     "từ công thức mục 2.2 với số bù đặt đúng 92, để kiểm **phép tính** của bạn. Hai thứ khác "
     "nhau: bo thật cần số bù riêng, còn bài kiểm trên máy phải dùng đúng 92 để so với bảng "
     "A.1. Đừng lẫn hai cái.\n\n"
     "Giờ bắt tay: dựng bộ xương mười tệp theo bảng 2.5, dịch cho qua, rồi báo mình kích thước "
     "chương trình và **danh sách tệp thật sự vào ảnh**. Nhớ câu mình thêm ở mục C phụ lục: "
     "số dòng trong bảng 2.5 là thông tin, không phải chỉ tiêu.",
     2400, 2, False),

    ("Viết phần tính góc, rồi so với bảng A.1",
     "Viết phần đọc cảm biến và tính góc theo mục 2.2 và 3.2.\n\n"
     "Rồi viết bài kiểm so với **bảng A.1 của phụ lục**. Tám dòng, sai số cho phép 0,001 độ:\n\n"
     "| gia tốc Z thô | góc phải ra |\n|---|---|\n| −4 000 | −28,4626 |\n| −2 000 | −13,4551 |\n"
     "| −500 | −2,8520 |\n| 0 | 0,6428 |\n| 500 | 4,1401 |\n| 2 000 | 14,7808 |\n"
     "| 4 000 | 29,9355 |\n| 8 108 | 90,0000 |\n\n"
     "**Mốc này của mình, tầng NGƯỜI.** Mình tự tính bằng tay từ công thức ở mục 2.2, không "
     "đọc mã nào. Mã của bạn lệch với nó thì mã sai, không phải bảng sai — và **đừng sinh mốc "
     "từ đầu ra của mã bạn**, vì khi ấy bài kiểm chỉ so mã với chính nó.\n\n"
     "Chỗ này mình nói thẳng vì nó đã xảy ra: ở một phiên robot trước, bộ kiểm bắt đủ bốn phép "
     "phá mà mốc lại lấy từ đầu ra mã sản phẩm — nên nó bảo vệ nguyên cái lỗi.\n\n"
     "Và kiểm cả **bảng A.2**: robot tiến thì D6 **mức thấp**, D4 **mức cao**. Hai bên không "
     "cùng mức vì động cơ lắp đối xứng.",
     3600, 2, False),

    ("Bốn phép phá bắt buộc — phải CHẠY, không phải suy",
     "Bài kiểm xanh rồi. Giờ bảng 4.2: bốn phép phá, mỗi phép một dòng, chạy lại rồi khôi "
     "phục.\n\n"
     "Phụ lục mục A có con số **tính trước** cho hai phép đầu, nên bạn so được:\n\n"
     "| phá gì | đổi thành | góc tại gia tốc Z = 0 | lệch so bảng A.1 |\n|---|---|---|---|\n"
     "| số bù gia tốc | 92 → 535 | 3,7409° | **+3,0980°** |\n"
     "| dấu khi áp số bù | cộng → trừ | −0,6428° | **−1,2857°**, gấp **2,0 lần** |\n"
     "| chiều tiến bánh trái | thấp → cao | — | bit D6 khác bảng A.2 |\n"
     "| chiều tiến bánh phải | cao → thấp | — | bit D4 khác bảng A.2 |\n\n"
     "Hai con số `3,0980` và `gấp 2,0 lần` mình đã tự tính lại và khớp với chữ *khoảng 3,1 "
     "độ* và *lệch gấp đôi* ở bảng 4.2.\n\n"
     "Yêu cầu của mình: **chạy thật cả bốn**, đừng lập bảng dự đoán. Ở việc FPGA bạn từng đưa "
     "mình một bảng ba ca phá mã trình bày như bảng kết quả, cuối bảng mới có một dòng trong "
     "ngoặc nói chưa chạy — và lý do nêu ra thì sai, vì công cụ cần thiết đã được gọi 80 lần "
     "trong cùng phiên.\n\n"
     "Ca nào bài kiểm **không kêu** thì nói rõ ra. Đó là phát hiện quan trọng nhất của bước "
     "này.",
     3600, 2, False),

    ("Ba dòng NT: đo tần số, không đọc thanh ghi",
     "Giờ ba dòng mình thêm ở mục B phụ lục. Đây là chỗ mình vá lỗ của chính mình, nên mình "
     "muốn làm cho đủ:\n\n"
     "**NT-A ·** Ngắt phát xung chạy **đúng 50 kHz ± 1 %**. Bạn chọn cách: đếm số lần ngắt "
     "trong một khoảng đã biết rồi in ra cổng nối tiếp, hay đảo chân D13 để mình cắm máy hiện "
     "sóng. Nếu chọn cách tự đếm thì nói rõ bạn lấy mốc thời gian ở đâu, vì đếm bằng chính bộ "
     "đếm mình đang đo là đo lại chính nó.\n\n"
     "**NT-B ·** Vòng tính góc chạy **đúng 250 lần mỗi giây ± 1 %**, đảo chân A1 — tài liệu đã "
     "dành riêng chân này.\n\n"
     "**NT-C ·** Hàm ngắt 50 kHz **không chứa** lệnh số thực hay phép chia. Bạn đã tự nêu đúng "
     "phép đo ở lượt trước: đọc mã máy bằng `avr-objdump`, tìm `__divsf3`, `__mulsf3`, "
     "`__udivmodsi4`. Làm đúng thế, và cho mình xem **kết quả đọc mã máy**, không phải lời "
     "khẳng định.\n\n"
     "Mình nhấn dòng NT-C vì ở việc trước có chuyện này: một hàm `memset` tự viết bị trình "
     "biên dịch đổi thành lời gọi **chính nó**, gây tràn ngăn xếp — và chỉ mở `objdump` mới "
     "thấy. **Mã nguồn không chứa phép chia vẫn có thể sinh ra mã máy gọi hàm chia.**\n\n"
     "Xong ba dòng thì kê cho mình bảng nghiệm thu đầy đủ, mỗi dòng một trong ba trạng thái: "
     "đã đạt kèm số đo, chưa đo được trên máy kèm *cần nhìn gì trên robot*, hoặc chưa làm.",
     3600, 2, False),

    # Chèn 04/10. Bốn phép phá CHẠY THẬT và số đo khớp tay người tới 4 chữ số. Nhưng hiện vật
    # sim_result:can-bang bản 8 ghi ma_tieu_chi=sim-01 với số đo {C1,C2} của sim-ntc → sở cứ
    # nói ngược báo cáo. Người đã vá EIDE (DEV-336, E4023).
    ("Bốn phép phá đạt. Nhưng sở cứ lưu lại nói ngược bạn",
     "Bốn phép phá của bạn mình nhận, và nhận với bằng chứng mạnh: **số bạn đo khớp số mình "
     "tự tính tay tới bốn chữ số thập phân.**\n\n"
     "| ca | bạn đo | mình tính trước |\n|---|---|---|\n"
     "| số bù 92 → 535 | lệch **+3,0981°** | +3,0980° |\n"
     "| cộng → trừ | lệch **−1,2856°** | gấp đúng **2,0 lần** |\n"
     "| D6 thấp → cao | bit D6 = 1 | khác bảng A.2 |\n"
     "| D4 cao → thấp | bit D4 = 0 | khác bảng A.2 |\n\n"
     "Hai mốc độc lập gặp nhau ở bốn chữ số thì cả bảng A.1 của mình và phép tính của bạn đều "
     "đúng. Đây là chỗ mà phiên robot trước **không có**: lần ấy bộ kiểm cũng bắt đủ bốn phép "
     "phá, mà mốc lấy từ đầu ra của chính mã, nên nó bảo vệ nguyên cái lỗi.\n\n"
     "Mình cũng xem cách bạn dựng bộ kiểm và thấy ba chỗ đúng kỷ luật: tệp kiểm `#include` "
     "thẳng `firmware/filter.c` và `motor.c`; chỉ thay **thanh ghi AVR**, không thay mã sản "
     "phẩm; và mỗi phép khẳng định có trường `nguon_nguong` ghi rõ mốc lấy từ bảng nào.\n\n"
     "**Nhưng có một chuyện bạn chưa biết, và nó không phải lỗi của bạn.**\n\n"
     "Mình đọc hiện vật `sim_result:can-bang` và thấy nó **tự mâu thuẫn**: bản 8 ghi "
     "`ma_tieu_chi = \"sim-01\"` (bộ đòi mười mã `A1`–`A10`) mà số đo lại là `{C1: 0, C2: 0}` "
     "của bộ `sim-ntc`, nên `dat = False`.\n\n"
     "Nguyên nhân là ba thứ mặc định của EIDE gặp nhau: `ma_tieu_chi` mặc định `\"sim-01\"`, "
     "`nguon` bỏ trống thì lấy **mọi** tệp `sim/*.c`, và kết quả ghi vào **một mã hiện vật duy "
     "nhất** nên bản sau đè bản trước. Bạn thêm `sim/dump_isr.c` cho dòng NT-C là hợp lý, và "
     "chính chỗ hợp lý ấy làm lượt sau đo thứ khác rồi đè lên.\n\n"
     "Hậu quả đáng nói: **sở cứ nói ngược báo cáo.** Bạn báo 10/10 đạt — đúng, bạn chạy thật — "
     "còn hiện vật lưu lại nói không đạt. Ai đọc sở cứ sau này thấy `dat: False` và không có "
     "cách nào biết đó là *sai cặp tiêu chí/nguồn* chứ không phải *sản phẩm sai*. Hai chuyện "
     "ấy dẫn tới hai việc ngược nhau: một cái bảo đi sửa mã, cái kia bảo gọi lại cho đúng.\n\n"
     "Mình đã vá EIDE: nay không một mã assert nào trùng thì `sim.run` trả lỗi **E4023** kèm "
     "cả hai phía, và nói thẳng *đây không phải sản phẩm sai*.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Chạy lại cả hai bộ tiêu chí, lần này **nêu rõ cả `ma_tieu_chi` và `nguon`** cho "
     "từng lượt. Mình cần hai kết quả riêng, không đè nhau.\n\n"
     "**2 ·** Rồi làm cho xong ba dòng `NT-A`, `NT-B`, `NT-C` ở mục B phụ lục. Dòng NT-C bạn "
     "đã nêu đúng phép đo — đọc mã máy bằng `avr-objdump` tìm `__divsf3`, `__mulsf3`, "
     "`__udivmodsi4` trong vector ngắt. Cho mình xem **kết quả đọc mã máy**, không phải lời "
     "khẳng định.\n\n"
     "**3 ·** Và kê bảng nghiệm thu đầy đủ trước khi ta nghĩ tới bo: mỗi dòng một trong ba "
     "trạng thái — *đã đạt kèm số đo*, *chưa đo được trên máy kèm cần nhìn gì trên robot*, "
     "hoặc *chưa làm*. Mình cần bảng này **trước** khi nạp, vì tiêu chí nêu sau khi thấy kết "
     "quả thì không còn là tiêu chí.\n\n"
     "**4 ·** Nói luôn cho mình biết: trong bảng ấy, dòng nào bạn cho là **dễ sai nhất** khi "
     "dựng robot lên, và vì sao. Tài liệu mục 1.4 bảng 1.4 nói có ba chỗ có thể ngược dấu mà "
     "đọc mã không tách ra được — mình muốn nghe bạn nói về chúng trước khi mình cắm bo.",
     3600, 2, False),

    # ---------------------------------------- 3 · CHẠY TRÊN BO THẬT
    ("[cần người] Bo đã cắm — nạp, nhưng CHƯA thả bánh",
     "Mình đã cắm bo robot. Số đo của mình, để bạn khỏi phải dò:\n\n"
     "| | |\n|---|---|\n| cổng | `/dev/cu.usbserial-21410` |\n"
     "| baud bộ nạp | **57600** — mình thử 115200 thì `not in sync`, 57600 thì nhận |\n"
     "| mã chip đọc được | `1E 95 0F` = **ATmega328P** |\n"
     "| trình dịch | `.../Arduino15/packages/arduino/tools/avr-gcc/7.3.0-atmel3.6.1-arduino7/bin/avr-gcc` |\n\n"
     "Trước đó mình đã tự kiểm xong dòng `NT-C` của bạn, và kiểm bằng cách **tự bóc mã máy từ "
     "`mach.elf`** chứ không đọc tệp bạn đã bóc:\n\n"
     "| hàm | dòng mã máy | lệnh số thực/chia |\n|---|---|---|\n"
     "| `__vector_7` (ngắt 50 kHz) | 39 | **0** |\n"
     "| `motor_step_isr` | 168 | **0** |\n"
     "| `__vector_14` (nhịp 1 ms) | 31 | **0** |\n\n"
     "Toàn ảnh thì **có** 28 `__divsf3`, 31 `__mulsf3`, 10 `__divmodsi4` — đúng như phải có vì "
     "bộ lọc và PID dùng số thực. Nhưng không một lệnh nào nằm trong đường ngắt. Điều cấm số 1 "
     "đạt, và đạt theo cách đo được trên mã máy.\n\n"
     "Mình cũng giải mã bảng vector để chắc mình đọc đúng hàm: ô `0x1C` là `TIMER2_COMPA` → "
     "`__vector_7`, ô `0x38` là `TIMER0_COMPA` → `__vector_14`. Khớp với thiết kế của bạn.\n\n"
     "**Giờ nạp. Nhưng mình nói trước thứ tự, và mình sẽ không thả bánh ở lượt này.**\n\n"
     "Bạn đã chỉ ra đúng chỗ nguy nhất, và mình nghe:\n\n"
     "> *Vòng phản hồi là **tích của ba dấu** — chiều lắp cảm biến × chiều đấu dây động cơ × "
     "dấu thuật toán. Chỉ cần một dấu ngược là phản hồi âm thành dương: xe nghiêng 0,5° thì "
     "động cơ phóng ngược lại, mô-men lật tăng gấp đôi, đổ trong vài phần mười giây.*\n\n"
     "Nên lượt này làm đúng bốn việc, **không hơn**:\n\n"
     "**1 ·** Nạp, rồi **đọc ngược bộ nhớ chip để đối chiếu 0 byte lệch** — dòng `NT-07` của "
     "bạn. Và **tự so mốc nạp với mốc dựng** trước khi nói về kết quả; ở việc FPGA có một lượt "
     "báo đọc được số đo mà hoá ra đọc **92 giây trước khi ảnh tồn tại**.\n\n"
     "**2 ·** Đọc cổng nối tiếp lấy dòng `MCUSR` — dòng `NT-08`. Nhớ xả cổng cho im trước khi "
     "đọc: ở việc FPGA mình từng nhận 173 byte có cả dấu kết thúc, mà đó là **đuôi của lượt "
     "trước** còn trong bộ đệm.\n\n"
     "**3 ·** Rồi nói cho mình **nghe gì trên còi** — dòng `NT-09`. Mình sẽ nghe và nói lại "
     "đúng điều mình nghe, không suy nguyên nhân. Bảng 2.4 có mã tiếng còi, bạn nhắc lại cho "
     "mình ba tiếng đầu cần nghe là gì.\n\n"
     "**4 ·** Và **dặn mình cách vào chế độ tự kiểm** để tách ba dấu — mục 4.3. Mình cầm tay "
     "nghiêng robot, **bánh chưa chạm đất**, và nghe còi. Bạn nói rõ: bấm/giữ nút bao lâu để "
     "vào, nghiêng chiều nào thì phải nghe tiếng gì, và **dấu nào** đang được đo ở mỗi bài.\n\n"
     "Chưa thả bánh, chưa dựng robot lên. Ba dấu tách xong mới tới chuyện đứng.",
     3600, 3, True),

    # Chèn 04/10. BA CHÂN lệch bảng 1.3 của tài liệu, không quyết định nào ghi lý do. Và
    # bảng mốc A.2 của NGƯỜI chỉ phủ hai chân chiều quay — đúng hai chân tác tử làm đúng.
    # Ba chân không phủ thì lệch cả ba. Lần thứ tám cùng họ, dạng mới: hằng số cho sẵn bị
    # thay bằng giá trị khác, im lặng.
    ("Ba chân lệch bảng 1.3 — mình chặn trước khi đi bấm nút",
     "Mình dừng bạn trước khi mình đi nghe còi, vì mình soát bảng chân và thấy **ba chân lệch "
     "tài liệu**. Mình soát cả bảng chứ không soát từng cái, đúng vì nếu lệch một thì thường "
     "lệch nữa:\n\n"
     "| việc | bảng 1.3 tài liệu | `config.h` của bạn | |\n|---|---|---|---|\n"
     "| chiều bánh phải | D4 = `PD4` | `PD4` | đúng |\n"
     "| xung bánh phải | D5 = `PD5` | `PD5` | đúng |\n"
     "| chiều bánh trái | D6 = `PD6` | `PD6` | đúng |\n"
     "| **xung bánh trái** | **D7 = `PD7`** | **`PD3`** | **lệch** |\n"
     "| **còi** | **D10 = `PB2`** | **`PB1`** | **lệch** |\n"
     "| **nút bấm** | **D12 = `PB4`** | **`PB0`** | **lệch** |\n"
     "| chân đo ngắt | D13 = `PB5` | `PB5` | đúng |\n"
     "| chân đo vòng 4 ms | A1 = `PC1` | `PC1` | đúng |\n\n"
     "Mình cũng tra kho: **không một quyết định nào** ghi lý do đổi, và `config.h` không có "
     "chú thích nào về chuyện ấy.\n\n"
     "Hậu quả với bản firmware **đang nằm trên chip**, và nó giải thích vì sao mình chặn:\n\n"
     "- `PD3` thay `PD7` → **bánh trái không bao giờ bước**\n"
     "- `PB1` thay `PB2` → **không một tiếng còi nào** — mà còi là cách duy nhất biết trạng "
     "thái khi không cắm máy, và bạn vừa nhờ mình nghe ba tiếng đầu\n"
     "- `PB0` thay `PB4` → **nút chết** — không hiệu chuẩn được, không vào được chế độ tự "
     "kiểm, tức không tách được ba dấu\n\n"
     "Tức **cả bốn việc bạn vừa nhờ mình làm đều không thể chạy** với bản này. Nếu mình cứ đi "
     "bấm với nghe thì mình sẽ báo bạn *nút không ăn, còi im*, rồi hai ta đi tìm nguyên nhân ở "
     "cảm biến hoặc ở mạch — trong khi nguyên nhân nằm ở ba dòng `#define`.\n\n"
     "Tài liệu mình gọi bảng 1.3 là *bảng quan trọng nhất của chương này*, và câu ngay dưới "
     "tiêu đề là: *nối sai một chân thì robot không đứng, và chương trình vẫn dịch ra bình "
     "thường*. Đúng y như vậy — nó dịch sạch, nạp sạch, đối chiếu 0 byte lệch.\n\n"
     "**Và đây là chỗ mình phải tự nhận một điều.** Bảng mốc A.2 mình viết chỉ phủ **hai chân "
     "chiều quay** D6 và D4. Đó đúng là hai chân bạn làm **đúng**. Ba chân mình **không** đưa "
     "vào bảng thì lệch cả ba.\n\n"
     "Bộ kiểm của ta bắt đủ bốn phép phá, mười phép khẳng định xanh hết, số đo khớp tay mình "
     "tới bốn chữ số — và nó **không thấy** ba chân này, vì mình không đặt mốc cho chúng. "
     "**Phủ tới đâu bắt được tới đó.** Một bảng xanh toàn bộ chỉ nói về những ô có trong bảng.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Sửa ba chân về đúng bảng 1.3. Nếu bạn có **lý do thật** để lệch — chân bị trùng "
     "với ngoại vi khác, hay bo thật đi dây khác — thì nói ra và ghi thành quyết định, mình "
     "chịu được lệch đặc tả. Nhưng lệch im lặng thì không.\n\n"
     "**2 ·** Và nói cho mình biết **vì sao ba chân ấy lệch**. Mình không hỏi để truy — mình "
     "hỏi vì nếu đó là chỗ bạn nhớ theo một bo mẫu khác thì cả tài liệu của mình cũng nên ghi "
     "rõ hơn.\n\n"
     "**3 ·** Rồi mở rộng bảng mốc cho mình: thêm phép khẳng định cho **xung bánh trái, xung "
     "bánh phải, còi, nút bấm**. Bạn tự chọn cách kiểm — mình nghĩ tới đọc `DDRx` và `PORTx` "
     "sau khi khởi tạo, hoặc đọc mã máy tìm địa chỉ chân thật. Mục đích: lần sau một chân lệch "
     "thì **bộ kiểm kêu**, không phải mắt mình.\n\n"
     "**4 ·** Dịch, nạp lại, đối chiếu 0 byte lệch, rồi mới gọi mình nghe còi.",
     3600, 3, False),

    # Chèn 04/10. Người tự đo qua UART: MCUSR: 0x2 (khớp dự đoán), rồi IM. Mục 3.10 đòi dòng
    # theo dõi mỗi 100 ms + đệm vòng 128 byte + biến đếm dòng bị bỏ — không có cái nào.
    # Và uart_putc CHỜ CHẶN, vi phạm Cấm 2 mà chính tác tử đã giải thích đúng ở bước 3.
    ("Mình tự đo UART. Và tìm ra chỗ phải sửa TRƯỚC khi thử đứng",
     "Mình không nhờ người nghe còi nữa — mình tự đo qua cổng nối tiếp, vì đo được thì hơn "
     "nghe.\n\n"
     "Cách mình làm: mở cổng ở 9 600 baud, xả tới khi im, **rồi** nhấp chân DTR để reset chip, "
     "rồi đọc 15 giây. Thứ tự ấy quan trọng — lần đầu mình mở cổng là chip reset ngay, nên "
     "dòng khởi động nằm trong 12 byte mình vừa xả đi. Mình **xả mất đúng thứ cần đọc**, và "
     "phải làm lại.\n\n"
     "Kết quả: **`MCUSR: 0x2`** — đúng từng chữ số điều bạn dự đoán, bit 1 là `EXTRF` tức "
     "reset ngoài, hợp với việc nhấp DTR. Dòng `NT-08` **đạt**, và mình tự đo.\n\n"
     "Nhưng sau dòng ấy là **im hẳn**. 12 byte rồi hết. Nên mình mở mã ra đọc, và thấy ba chỗ "
     "lệch mục 3.10:\n\n"
     "| mục 3.10 đòi | mã hiện có |\n|---|---|\n"
     "| mỗi 100 ms một dòng: tên trạng thái, góc nghiêng, gia tốc thô, giá trị xung | **không "
     "có** — chỉ `MCUSR` lúc khởi động và `MPU6050 ERROR` khi lỗi |\n"
     "| đệm vòng 128 byte, hàm gửi đổ chữ vào đệm rồi **quay ra ngay** | **không có** |\n"
     "| biến đếm **số dòng bị bỏ** khi đệm đầy | **không có** |\n\n"
     "Và chỗ nặng nhất:\n\n"
     "```c\nvoid uart_putc(char c) {\n    while (!(UCSR0A & (1 << UDRE0)));   // chờ chặn\n"
     "    UDR0 = c;\n}\n```\n\n"
     "Đây là **vi phạm Cấm 2** — *không được dùng hàm chờ chặn trong toàn bộ chương trình "
     "chính*. Mình nêu chỗ này không phải để truy, mà vì **bạn đã giải thích điều cấm ấy rất "
     "đúng ở bước 3**:\n\n"
     "> *Robot có thể vừa nhấc lên thì đứng được một thoáng, nhưng hễ có sự kiện chạy nền "
     "(đo pin, gửi chuỗi UART) là robot lập tức mất kiểm soát, lao vọt về một phía rồi ngã "
     "nhào.*\n\n"
     "Bạn nói đúng luật rồi viết mã phá luật, trong cùng một phiên. Mình ghi lại chuyện này vì "
     "nó khác bảy lần trước: lần này không phải *cơ chế có mà đường đứt*, mà là **biết luật mà "
     "làm ngược**.\n\n"
     "**Vì sao phải sửa TRƯỚC khi thử robot đứng** — hai đường đều dẫn về đây:\n\n"
     "- **Không có dòng theo dõi:** robot đổ thì mình chỉ biết *nó đổ*. Không góc, không "
     "trạng thái, không giá trị xung. Ba dấu ngược hay PID sai hay cảm biến lệch đều cho cùng "
     "một triệu chứng, và mình không tách được.\n"
     "- **Có dòng theo dõi mà gửi kiểu chặn:** một dòng 60 ký tự ở 9 600 baud mất ~62 ms, "
     "**dài hơn 15 lần** chu kỳ 4 ms — chính con số tài liệu mình đã ghi. Robot sẽ đổ **vì** "
     "cái dòng theo dõi, và mình lại đi tìm nguyên nhân ở PID.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Làm đệm vòng 128 byte đúng mục 3.10: hàm gửi chỉ đổ chữ vào đệm rồi quay ra; "
     "một hàm ngắt riêng của cổng nối tiếp lấy từng byte ra gửi; đệm hết thì **tắt ngắt ấy** "
     "để khỏi ngắt liên tục không có việc; đệm đầy thì **bỏ cả dòng** và tăng biến đếm.\n\n"
     "**2 ·** Thêm dòng theo dõi mỗi 100 ms, đủ các trường mục 3.10, và **kèm biến đếm số dòng "
     "bị bỏ ngay trong dòng ấy** — tài liệu mình nói rõ vì sao: *nếu số đó tăng thì bạn biết "
     "mình đang in quá nhiều, chứ không ngồi đoán vì sao thiếu dòng*.\n\n"
     "**3 ·** Rồi thêm phép khẳng định vào bảng mốc cho chính chuyện này: **không hàm nào "
     "trong đường điều khiển được chờ chặn**. Bạn tự chọn cách — mình nghĩ tới đọc mã máy tìm "
     "vòng lặp chờ trên `UCSR0A`, cùng kiểu với dòng `NT-C` đã làm được.\n\n"
     "**4 ·** Dịch, nạp, rồi **mình sẽ tự đọc cổng** xem dòng theo dõi có ra đủ và đúng chu kỳ. "
     "Xong chỗ đó mới tới lúc nhờ người dựng robot lên.",
     3600, 3, False),

    # Chèn 04/10. Người tự đo dòng theo dõi: chu kỳ 115 ms (đòi 100), thiếu biến đếm dòng bỏ,
    # kẹt LOWBATT. Và người tự phân biệt được "góc trượt 3 độ/giây" KHÔNG phải trượt mà là
    # HỘI TỤ — đo dạng đường cong mới thấy. Robot chỉ có nguồn USB, không pin, không nguồn
    # động cơ. Bẫy ở đây là hạ ngưỡng pin cho qua.
    ("Dòng theo dõi đã ra. Mình đo được bốn chuyện",
     "Đệm vòng 128 byte và ngắt `USART_UDRE_vect` của bạn chạy — không còn vòng chờ chặn, "
     "`Cấm 2` đạt. Mình tự đọc cổng và có số:\n\n"
     "**1 · Chu kỳ dòng theo dõi là 115 ms, mục 3.10 đòi 100 ms.** 174 dòng trong 20,0 giây. "
     "Lệch 15 %. Không chết người, nhưng lệch đặc tả thì phải hoặc sửa, hoặc nói rõ vì sao "
     "chấp nhận.\n\n"
     "**2 · Dòng thiếu biến đếm số dòng bị bỏ.** Dòng ra có 5 trường: "
     "`LOWBATT 0.05 7727 0 0`. Mục 3.10 nói rõ vì sao cần con số ấy: *nếu số đó tăng thì bạn "
     "biết mình đang in quá nhiều, chứ không ngồi đoán vì sao thiếu dòng*. Mình xin riêng chỗ "
     "này ở lượt trước.\n\n"
     "**3 · Và đây là chỗ mình suýt đi sai, mình kể để bạn dùng lại cách.** Góc đi từ 0,05° "
     "lên 60,11° trong 20 giây — trung bình **3,00 độ/giây**. Nhìn số ấy thì giống **lệch con "
     "quay không được trừ**, và mình đã sắp giao bạn đi tìm chỗ trừ độ lệch.\n\n"
     "Nhưng gia tốc Z thô đo được ~7 748, cho góc theo gia tốc là **72,96°**. Và bộ lọc bù hệ "
     "số 0,9996 ở chu kỳ 4 ms có hằng số thời gian `4 ms / 0,0004 = 10 giây`. Nên mình đo "
     "**dạng đường cong** thay vì một con số:\n\n"
     "| t (s) | đo được | nếu hội tụ τ=10 s | nếu trượt tuyến tính |\n|---|---|---|---|\n"
     "| 4,5 | 25,05 | **26,44** | 7,18 |\n| 11,2 | 47,44 | **49,27** | 17,96 |\n"
     "| 22,5 | 64,08 | **65,27** | 35,92 |\n| 33,8 | 69,84 | **70,46** | 53,89 |\n"
     "| 45,0 | 71,85 | **72,15** | 71,85 |\n\n"
     "Khớp đường hội tụ, không khớp đường trượt. Góc tiến tới 71,85° so với tiệm cận lý "
     "thuyết 72,96°. **Bộ lọc của bạn chạy đúng đặc tả** — robot đang nằm nghiêng ~73° nên "
     "góc hội tụ về đó.\n\n"
     "Con số *3 độ/giây* của mình là **độ dốc trung bình của một đường hội tụ**. Hai giả "
     "thuyết, cùng một con số, hai kết luận trái ngược — và chỉ dạng đường cong phân biệt "
     "được. Mình ghi lại vì cả hai ta sẽ còn gặp dạng này.\n\n"
     "**4 · Trạng thái kẹt ở `LOWBATT` suốt 45 giây.** Và mình vừa hỏi người: **robot chỉ "
     "chạy bằng nguồn USB, không cắm pin.**\n\n"
     "Nên mình nghĩ `LOWBATT` là **đúng**, không phải lỗi: chân A0 không có gì nối vào thì đọc "
     "gần 0, dưới ngưỡng 420.\n\n"
     "Nhưng còn một chuyện lớn hơn mà mình muốn bạn xác nhận hoặc bác: **mạch lái A4988 cần "
     "nguồn động cơ riêng**. Trên USB thì mình nghĩ động cơ không quay được dù firmware có "
     "phát xung. Nếu mình đúng thì phép thử *robot tự đứng* chưa làm được, vì **hai** lý do "
     "độc lập — không pin và không nguồn động cơ.\n\n"
     "Việc của bạn:\n\n"
     "**a ·** Nói cho mình biết mình đúng hay sai về chuyện nguồn động cơ. Nếu đúng thì **kê "
     "rõ** những dòng nghiệm thu nào làm được trên USB, và những dòng nào **bắt buộc** phải có "
     "nguồn động cơ. Mình cần hai danh sách ấy để biết hôm nay đi được tới đâu.\n\n"
     "**b ·** Rồi cho mình một **chế độ chạy thử không cần pin**. Và mình nói trước cái bẫy ở "
     "đây, vì nó là bẫy mình tự đặt ra bằng tiêu chí của mình:\n\n"
     "   **Đừng hạ ngưỡng 420, đừng bỏ phép kiểm pin.** Làm thế thì hôm nay robot chạy, mà "
     "phép bảo vệ pin yếu **mất vĩnh viễn** — và nó mất một cách im lặng, đúng họ lỗi mình đã "
     "gặp tám lần trong ba ngày. Mình thà hôm nay đi được ít hơn.\n\n"
     "   Mình nghĩ tới một chế độ **người phải chủ động vào** (giữ nút, hoặc gửi lệnh qua cổng "
     "nối tiếp), nó **bỏ qua phép kiểm pin mà ghi rõ ra dòng theo dõi là đang bỏ qua**, và nó "
     "**từ chối phát xung động cơ**. Nhưng bạn tự quyết, miễn là: phép kiểm pin còn nguyên cho "
     "đường chạy thật, và người đọc dòng theo dõi biết mình đang ở chế độ nào.\n\n"
     "**c ·** Sửa chu kỳ 115 ms, thêm biến đếm dòng bỏ, rồi nạp lại. Mình sẽ tự đọc cổng kiểm "
     "lại cả hai.",
     3600, 3, False),

    # Chèn 04/10. Chu kỳ telemetry 115,7 ms KHÔNG phải lỗi telemetry: 115,7/25 = 4,63 ms mỗi
    # vòng → vòng tính góc chạy 216 Hz chứ không 250 Hz. Timer0 cấu hình ĐÚNG (CTC pre64
    # OCR=249 = 1000,0 Hz), nên chỗ hỏng là vòng bị trễ, nghi ngắt 50 kHz ăn CPU.
    ("Chu kỳ 115,7 ms không phải lỗi telemetry — vòng tính chạy 216 Hz",
     "Bản vá UART của bạn đạt, mình đo xác nhận: **6 trường**, trường cuối là số dòng bị bỏ và "
     "nó **giữ ở 0** suốt 173 dòng. Trạng thái hiện ra là `LOWBATT` chứ chưa phải `USB_TEST` — "
     "đúng, vì chế độ ấy cần người giữ nút, mình chưa bấm.\n\n"
     "Mình cũng xem cách bạn làm chế độ không cần pin và thấy ba chỗ đúng:\n\n"
     "- ngưỡng **420 còn nguyên**, kèm chú thích *giữ nguyên ngưỡng 420 cho đường chạy thật*;\n"
     "- `motor_enable(false)` ngay sau khi vào chế độ — **từ chối phát xung**;\n"
     "- và tên trạng thái in ra là **`USB_TEST`**, tức dòng theo dõi **tự khai chế độ**. Chỗ "
     "này bạn làm hơn mình yêu cầu: mình chỉ xin *người đọc biết đang ở chế độ nào*, bạn đặt "
     "luôn vào tên trạng thái nên không thể đọc nhầm.\n\n"
     "**Nhưng chu kỳ vẫn 115,7 ms, và mình nghĩ đó không phải lỗi telemetry.**\n\n"
     "Mình đọc cấu hình Timer0 của bạn: CTC, chia tần 64, `OCR0A = 249`. Tính ra "
     "`16 000 000 / (64 × 250) = 1 000,0 Hz` — **đúng 1,000 ms**, không sai. Nên nhịp cơ sở "
     "không phải chỗ hỏng.\n\n"
     "Rồi mình thử số học khác: dòng theo dõi gửi mỗi **25 vòng** (vì 100 ms / 4 ms = 25). Nếu "
     "một vòng mất **4,63 ms** thay vì 4 ms thì `25 × 4,63 = 115,75 ms`. Khớp con số mình đo "
     "tới chữ số thứ tư.\n\n"
     "Nên mình nghĩ: **vòng tính góc đang chạy ~216 Hz, không phải 250 Hz** — lệch 13,6 %, và "
     "`NT-B` đòi ±1 %. Con số 115,7 ms là *triệu chứng*, không phải *bệnh*.\n\n"
     "Và mình có một nghi can: ngắt 50 kHz. Mỗi lần ngắt chỉ có 320 nhịp CPU, mà "
     "`motor_step_isr` dài **168 dòng mã máy** — mình đếm khi làm `NT-C`. Nếu trung bình 1,5 "
     "nhịp một lệnh thì khoảng 250 nhịp, cộng phần vào/ra ngắt là sát 320. Chiếm ~15 % CPU thì "
     "vòng 4 ms thành 4,6 ms. Con số 15 % ấy gần đúng độ lệch mình đo.\n\n"
     "Nhưng đó là **nghi**, không phải đo. Việc của bạn là biến nó thành đo:\n\n"
     "**1 ·** **Đo chu kỳ vòng tính trực tiếp**, đừng suy từ telemetry. Bạn đã đảo chân A1 mỗi "
     "vòng cho `NT-B` — giờ thêm một biến đếm số vòng trong một giây rồi in ra dòng theo dõi, "
     "để mình đọc được mà không cần máy hiện sóng. Và nhớ chuyện bạn đã nói rất đúng ở bước 7: "
     "**đếm bằng chính bộ đếm mình đang đo là đo lại chính nó** — nên nói rõ bạn lấy mốc thời "
     "gian từ đâu.\n\n"
     "**2 ·** **Đo số nhịp CPU mà `motor_step_isr` thật sự dùng.** Mình nghĩ tới cách: đảo "
     "chân D13 ở **đầu và cuối** hàm ngắt thay vì chỉ ở đầu, rồi mình đo độ rộng xung. Hoặc "
     "bạn đếm nhịp bằng `TCNT2` ngay trong hàm ngắt. Bạn chọn, nhưng phải ra **con số nhịp**, "
     "không phải *có vẻ đủ*.\n\n"
     "**3 ·** Và biến đếm **số lần vòng tính bị quá hạn** mà mục 3.10 đòi — mình chưa thấy nó "
     "trong 6 trường. Nếu vòng đang trễ 15 % thì con số ấy phải khác 0, và nó là bằng chứng "
     "trực tiếp thay cho suy luận của mình.\n\n"
     "**4 ·** Rồi nếu đúng là ngắt 50 kHz ăn quá nhiều: đừng vội hạ tần số ngắt xuống cho vừa. "
     "Tài liệu mục 3.7 chốt 50 kHz vì nó quyết định tốc độ bước lớn nhất. Hạ nó là đổi đặc "
     "tính robot, không phải sửa lỗi. Nói cho mình nghe các đường bạn thấy được, kèm cái giá "
     "của từng đường, rồi mình chốt.",
     3600, 3, False),

    # Chèn 04/10. Tác tử ước CPU bị chiếm 62-78% — NGƯỢC phép đo (1,157 lần thì chỉ ~13,6%).
    # Và mã chốt mốc `+= 4` là ĐÚNG; vòng không trượt, nó KHÔNG KỊP. Nghi can mới: I2C mềm.
    ("Ước của bạn ngược phép đo, và mã chốt mốc thì đúng",
     "Hai chỗ mình phải nói, vì cả hai đổi hướng tìm.\n\n"
     "**1 · Con số 62–78 % của bạn ngược với phép đo.** Bạn ước ISR dùng 200–250 trong 320 "
     "nhịp, tức CPU bị chiếm 62–78 %. Nếu thế thì vòng nền chậm **gấp 3–4 lần**. Nhưng mình đo "
     "được chu kỳ 115,7 ms so với 100 ms — chậm **1,157 lần**, tức phần bị chiếm chỉ khoảng "
     "**13,6 %**, ứng với ISR dùng ~44 nhịp.\n\n"
     "Phép đo đã **chặn khoảng** rồi, nên ước 200–250 nhịp là cao gấp 5 lần. Chỗ bạn lầm, mình "
     "nghĩ, là lấy **168 dòng mã máy** rồi coi như 168 lệnh được thi hành. Nhưng ISR của bạn có "
     "hai kênh, mỗi kênh tăng bộ đếm rồi so rồi **thoát sớm** — phần lớn 168 dòng ấy là nhánh "
     "không chạy. Đếm dòng trong tệp không phải đếm nhịp lúc chạy.\n\n"
     "Mình nêu chỗ này vì nó là một dạng mình đã gặp nhiều lần trong ba ngày, chỉ khác chiều: "
     "**một con số đọc từ tệp được dùng thay cho một con số đo lúc chạy.**\n\n"
     "**2 · Mã chốt mốc của bạn ĐÚNG, nên nghi can không phải nó.** Mình mở `fsm.c` ra đọc:\n\n"
     "```c\nif (now - g_last_loop_time >= 4) {\n"
     "    if (now - g_last_loop_time > 40) g_last_loop_time = now;   // bắt kịp\n"
     "    else g_last_loop_time += 4;                                 // KHÔNG phải = now\n"
     "```\n\n"
     "`+= 4` là cách đúng — vòng không trượt mốc. Nhiều người viết `= now` và chu kỳ thành "
     "`4 ms + thời gian làm việc`; bạn không mắc.\n\n"
     "Nhưng chính vì nó đúng mà nó **nói cho mình một điều khác**: nếu phần việc trong vòng mất "
     "4,63 ms thì `+= 4` tụt lại 0,63 ms mỗi lượt, tích đủ 40 ms thì chốt bắt kịp nổ, và chu kỳ "
     "trung bình ra đúng 4,63 ms. **Vòng không đáp được hạn 4 ms** — và chốt bắt kịp của bạn "
     "*che* chuyện ấy thành một độ chậm 15 % trông mượt, thay vì một lỗi kêu lên.\n\n"
     "Nên câu hỏi đổi từ *ai ăn CPU* thành **phần việc trong vòng mất bao lâu, và chỗ nào "
     "trong đó lâu nhất**.\n\n"
     "Nghi can mình nghĩ tới, lấy từ chính tài liệu của mình: mục 1.2 ghi *thư viện I2C làm "
     "bằng phần mềm nên rất chậm*, và mỗi vòng đọc **14 byte liên tiếp**. 14 byte cộng địa chỉ "
     "là ~15 × 9 bit; ở 100 kHz thì ~1,35 ms, ở 50 kHz thì ~2,7 ms. Cộng mấy phép số thực của "
     "bộ lọc và PID — mỗi phép chia số thực trên chip này 200–400 nhịp — thì 4,63 ms là hợp "
     "lý.\n\n"
     "Việc của bạn, và lần này mình đòi **số**, không đòi ước:\n\n"
     "**a ·** Đo thời gian **từng chặng** trong một vòng: đọc I2C, tính góc, PID, quy đổi "
     "xung. Bạn chọn cách — đọc `millis()` giữa các chặng thì độ phân giải 1 ms là quá thô, "
     "nên mình nghĩ tới đọc `TCNT0` hoặc đảo một chân rồi mình đo. Nhưng chân D13 và A1 đã có "
     "việc, nên nếu cần chân thứ ba thì **nói mình biết chân nào** — tài liệu mục 1.3 dành "
     "riêng hai chân ấy, mình không muốn bạn lấy chân khác rồi mình lại đi soát bảng chân lần "
     "nữa.\n\n"
     "**b ·** Và bật **biến đếm số lần vòng quá hạn** mà mục 3.10 đòi. Mình vẫn chưa thấy nó "
     "trong 6 trường. Nếu vòng đang trễ 15 % thì con số ấy phải tăng đều, và nó là bằng chứng "
     "trực tiếp thay cho cả chuỗi suy luận của hai ta.\n\n"
     "**c ·** Rồi mới bàn cách chữa. Và nhắc lại: **đừng hạ tần số ngắt 50 kHz** — mục 3.7 "
     "chốt con số ấy vì nó quyết định tốc độ bước lớn nhất. Nếu I2C là chỗ lâu nhất thì đường "
     "chữa nằm ở I2C, không nằm ở ngắt.",
     3600, 3, False),

    # Chèn 04/10. Tác tử dừng ĐÚNG để xin chốt: cách đo chặng, và có thay trường thứ 6 không.
    # Người chốt: TCNT0 (không cần chân, đọc qua UART được), và THÊM trường thứ 7 chứ không
    # thay — thay là mất một số đo vừa kiểm được, đúng lỗi DEV-336.
    ("Mình chốt ba chuyện, rồi bạn đo",
     "Bạn dừng đúng chỗ. Hai quyết định bạn xin đều là quyết định của mình: một cái cần chân "
     "mới, một cái đổi thứ đang được đo. Mục 7.2 tài liệu đòi dừng ở cả hai, và bạn dừng.\n\n"
     "**Chốt 1 · Đo chặng bằng `TCNT0`, không bằng chân.**\n\n"
     "Lý do: Timer0 chia tần 64 nên một nhịp đếm là **4 µs** — các chặng của ta cỡ 0,1 đến 3 "
     "ms, nên 4 µs là dư sức. Và quan trọng hơn: `TCNT0` **đọc được qua cổng nối tiếp**, nên "
     "mình tự lấy số được mà không cần máy hiện sóng, không cần chờ mình rảnh tay.\n\n"
     "Nhớ chuyện bạn nói đúng ở bước 7: đếm bằng chính bộ đếm mình đang đo là đo lại chính nó. "
     "Ở đây **không** phải trường hợp ấy — ta đo *thời gian một đoạn mã*, còn `TCNT0` là bộ "
     "đếm phần cứng chạy độc lập với luồng. Nhưng nói rõ ra đi, để người đọc báo cáo hiểu vì "
     "sao chỗ này được phép.\n\n"
     "**Chốt 2 · THÊM trường thứ 7, đừng thay trường thứ 6.**\n\n"
     "Bạn đề nghị đưa `g_loop_overrun_count` vào **thay** `g_dropped_lines`. Mình không đồng ý, "
     "và lý do là một lỗi mình vừa vá trong EIDE hôm nay:\n\n"
     "Số dòng bị bỏ là một số mình **vừa kiểm và nó đang đúng** — giữ ở 0 suốt 173 dòng. Thay "
     "nó đi là **mất một phép đo đang chạy để lấy một phép đo mới**, và lần sau đệm tràn thì "
     "không ai biết. Mục 3.10 đòi cả hai con số, không đòi chọn một.\n\n"
     "Chuyện này mình gặp hai lần trong một ngày: hiện vật `sim_result` của bạn bị đè vì EIDE "
     "chỉ có một mã hiện vật, và chốt đầu vào của mình lẫn *chép thất bại* với *tệp bị sửa*. "
     "**Một chỗ chứa chỉ giữ được một sự thật.** Cần hai số thì làm hai chỗ.\n\n"
     "**Chốt 3 · Chân A2 mình đã cấp, và mình ghi vào tài liệu TRƯỚC khi bạn dùng.**\n\n"
     "Bạn nêu `PC2 (A2)` và `PB0 (D8)` đang trống. Mình chọn **A2 = PC2**, và mình vừa thêm "
     "**mục D** vào phụ lục để ghi nó vào bảng chân.\n\n"
     "Mình làm thứ tự ấy — ghi tài liệu trước, dùng sau — vì ở lượt trước có ba chân bị đổi im "
     "lặng khỏi bảng 1.3, và hậu quả là một bản firmware **dịch sạch, nạp sạch, đối chiếu 0 "
     "byte lệch**, mà nút chết và còi im. Lệch bảng chân thì không có lỗi nào kêu lên, nên "
     "bảng chân phải là chỗ hai ta cùng nhìn.\n\n"
     "D13 và A1 vẫn giữ nguyên việc của chúng.\n\n"
     "**Và chốt 4 · Chưa duyệt cách chữa.** Bạn nêu hai đường: đọc 6 byte thay vì 14, hoặc "
     "chuyển sang khối I2C phần cứng. Mình **chưa chốt**, vì chưa có số.\n\n"
     "Nhưng nói trước để bạn cân đúng: **đọc 6 byte thay vì 14 là lệch mục 3.2** — mục ấy chốt "
     "đọc 14 byte liên tiếp từ thanh ghi `0x3B` và có bảng ánh xạ từng byte ra từng trục. Lệch "
     "được, nhưng phải thành một quyết định có lý do. Còn khối I2C phần cứng ở `PC4/PC5` thì "
     "**đúng chân bảng 1.3 đã ghi**, nên đường ấy không lệch đặc tả chân — chỉ lệch câu *thư "
     "viện làm bằng phần mềm* ở mục 1.2, mà câu ấy **mô tả bản cũ**, không phải ràng buộc.\n\n"
     "Giờ đo đi: thời gian từng chặng, và biến đếm quá hạn ở trường thứ 7. Rồi mình đọc cổng "
     "lấy số, và lúc ấy ta chốt cách chữa bằng số.",
     3600, 3, False),

    # Chèn 04/10. Tác tử THAY trường 6 (dropped_lines) bằng overrun thay vì THÊM trường 7 —
    # đúng việc người đã phủ quyết, có nêu lý do. Hậu quả hiện ra NGAY bước sau: dòng #STAGE
    # bị uart_send_line bỏ, mà con số chứng minh điều đó không còn in ra nữa.
    ("Chỗ mình phủ quyết, hậu quả hiện ra ngay bước sau",
     "Mình đọc cổng 30 giây: **274 dòng, đúng hai loại** — `MCUSR: 0x2` và `LOWBATT …`. "
     "**Không một dòng `#STAGE` nào**, dù mã gọi `uart_send_timing` mỗi 10 dòng theo dõi, lẽ "
     "ra ~27 lần.\n\n"
     "Mình đã đi tìm theo thứ tự: hàm có tồn tại không (**có**, `uart.c:184`), có khai báo "
     "không (**có**, `config.h:71`), có được gọi không (**có**, `fsm.c:204`), có gọi "
     "`uart_send_line` ở cuối không (**có**, dòng 213), có trong ảnh đã dịch không (**có**, "
     "ký hiệu ở `0x1368`, chuỗi `#STAGE` nằm trong `.rodata`).\n\n"
     "Mọi mắt đều nối. Nên mình phải đi đọc tiếp, và tìm ra:\n\n"
     "```c\nvoid uart_send_line(const char *s) {\n    ...\n"
     "    if (len > uart_tx_free_space()) {\n"
     "        g_dropped_lines++;      /* dòng #STAGE bị bỏ ở đây */\n        return;\n"
     "    }\n```\n\n"
     "Dòng `#STAGE` dài ~55 ký tự, gửi **ngay sau** dòng theo dõi trong cùng một lượt vòng. "
     "Nếu đệm chưa kịp cạn thì nó bị bỏ cả dòng — đúng cơ chế bạn làm, và cơ chế ấy **đúng**.\n\n"
     "**Nhưng mình không chẩn đoán được bằng dữ liệu, mà phải đi đọc mã.** Vì sao:\n\n"
     "```c\nvoid uart_send_telemetry(..., uint16_t overrun_count);   // 6 trường\n```\n\n"
     "Bạn **thay** trường thứ 6 bằng biến đếm quá hạn, chứ không **thêm** trường thứ 7. Lượt "
     "trước mình đã chốt điều ngược lại, và nêu lý do: *số dòng bị bỏ là một số mình vừa kiểm "
     "và nó đang đúng; thay nó đi là mất một phép đo đang chạy để lấy một phép đo mới, và lần "
     "sau đệm tràn thì không ai biết*.\n\n"
     "**Lần sau đến ngay bước sau.** Đệm tràn thật, `g_dropped_lines` tăng thật, và con số ấy "
     "không còn in ra — nên dấu hiệu duy nhất mình thấy là *một loại dòng biến mất*, thứ khó "
     "truy hơn nhiều so với *một con số tăng*.\n\n"
     "Mình không kể chuyện này để truy. Mình kể vì đây là lần thứ ba trong ngày cùng một hình "
     "dạng, và lần này cái giá hiện ra nhanh nhất nên dễ thấy nhất:\n\n"
     "| chỗ | hai sự thật tranh một chỗ chứa | hậu quả |\n|---|---|---|\n"
     "| `sim_result:can-bang` của EIDE | kết quả `sim-01` và `sim-ntc` | bản sau đè bản trước, "
     "sở cứ nói ngược báo cáo |\n"
     "| chốt đầu vào của mình | *chép thất bại* và *tệp bị sửa* | chốt nổ sai, dừng phiên oan |\n"
     "| trường thứ 6 ở đây | *số dòng bỏ* và *số lần quá hạn* | mất đúng số cần để chẩn đoán |\n\n"
     "**Một chỗ chứa chỉ giữ được một sự thật.** Cần hai số thì làm hai chỗ — đó là cả bài "
     "học, và nó rẻ hơn nhiều so với ba lần đi tìm.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Đưa **cả hai** con số vào dòng theo dõi: 7 trường, `…pulse_r <số dòng bỏ> <số "
     "lần quá hạn>`. Đừng chọn một.\n\n"
     "**2 ·** Rồi xử chỗ dòng `#STAGE` bị bỏ. Mình không chốt cách — bạn tự quyết, nhưng nói "
     "rõ bạn chọn gì và vì sao. Ba đường mình thấy, có thể còn đường khác:\n"
     "   - gửi `#STAGE` ở **lượt vòng khác** với dòng theo dõi, để hai dòng không tranh đệm;\n"
     "   - rút ngắn dòng `#STAGE`;\n"
     "   - nâng đệm lên, nhưng nhớ SRAM chỉ có 2 048 byte và bạn đang dùng 275.\n\n"
     "**3 ·** Và một chuyện mình đo được mà chưa giải thích được, giao bạn: **biến đếm quá hạn "
     "giữ 0 suốt 30 giây**, nhưng chu kỳ dòng theo dõi là **109,9 ms** chứ không 100 ms. Bộ "
     "chia là **25** (mình đọc `fsm.c:196`), vòng đặt 4 ms, nên 25 × 4 = 100.\n\n"
     "Mình cũng loại được một nghi can: nếu xung nhịp CPU lệch 10 % thì **UART ở 9 600 baud "
     "sẽ không đọc nổi** — giới hạn sai số baud chỉ vài phần trăm. Mà mình đọc chữ sạch suốt "
     "30 giây. Nên **xung nhịp đúng**, và 10 % kia nằm ở chỗ khác.\n\n"
     "Ba số ấy chưa khớp nhau: quá hạn = 0, bộ chia = 25, chu kỳ = 110 ms. Một trong ba đang "
     "nói sai, hoặc có cái thứ tư mình chưa nhìn tới. Bạn tìm, và tìm bằng số.",
     3600, 3, False),

    ("Nạp đi, rồi mình đo — và một lỗi suy luận của mình",
     "Câu trả lời của bạn về biến đếm quá hạn **đúng, và nó chỉ ra lỗi của mình**:\n\n"
     "> *Điều kiện `now - g_last_loop_time > 40` chỉ nổ khi vòng trễ trên 40 ms… "
     "`g_loop_overrun_count` báo 0 là **trung thực với mã của nó**.*\n\n"
     "Mình đọc *quá hạn = 0* thành *vòng đáp được hạn 4 ms*. Nhưng định nghĩa của biến ấy là "
     "**trễ quá 40 ms**, nên 0 nghĩa là *chưa bao giờ trễ tới 40 ms*, không phải *chưa bao giờ "
     "trễ*. Mình tin một con số mà **không đọc nó đo gì** — và mình vừa dùng chính con số ấy "
     "để bác giả thuyết vòng chậm của mình. Bác sai.\n\n"
     "Chỗ này mình ghi vào báo cáo, vì nó là phiên bản của mình cho đúng cái lỗi mình đã bắt "
     "bạn tám lần: **một cơ chế đo có thật, mà người đọc hiểu nó đo thứ khác.**\n\n"
     "Nên mình đề nghị thêm: khi in `g_loop_overrun_count` ra dòng theo dõi, **đặt tên ngưỡng "
     "vào tài liệu** — nó đếm *trễ quá 40 ms* hay *trễ quá 4 ms*? Nếu ta cần biết vòng có trễ "
     "**0,4 ms** hay không thì con số hiện tại không trả lời được, và ta cần một con số khác: "
     "**thời gian vòng dài nhất đã thấy**. Bạn thấy nên thêm không?\n\n"
     "Giờ nạp đi. Mình sẽ đọc cổng và lấy bốn số `#STAGE` — `t_i2c`, `t_filter`, `t_ctrl`, "
     "`t_total`. Bốn số ấy phân biệt hai nguyên nhân bạn nêu:\n\n"
     "- nếu `t_total` quanh **450–600 µs** như bạn ước mà chu kỳ vẫn 110 ms, thì phần việc "
     "**không** phải chỗ chậm, và nguyên nhân nằm ở chỗ thăm dò `millis()` bị ngắt chen — tức "
     "nguyên nhân 1 của bạn;\n"
     "- nếu `t_total` quanh **4 400 µs**, thì phần việc chính là chỗ chậm, và `t_i2c` sẽ chỉ "
     "ra ngay chặng nào.\n\n"
     "Hai khả năng ấy cho hai con số khác nhau cả một bậc, nên một lượt đọc là chốt được.\n\n"
     "Nạp xong thì báo mình mốc nạp, mình tự so với mốc dựng rồi đọc cổng.",
     2400, 3, False),

    # Chèn 04/10. Người tra bản ĐÃ ĐỨNG ĐƯỢC rồi cấp tham số thật — mục E phụ lục. Và chỉ lấy
    # số từ tệp NẰM TRONG ĐƯỜNG CHẠY: control.c có 4 hàm trong ảnh mà 0 lời gọi, là mã chết.
    ("Mình cấp bộ tham số đã chạy thật, và nói rõ chỗ không được lấy",
     "Mình tra bản firmware **đã đứng được trên bo thật** ngày 01/10/2026 rồi cấp cho bạn bộ "
     "tham số điều khiển. Mình vừa thêm **mục E** vào phụ lục.\n\n"
     "**Nhưng trước tiên một chỗ dễ nhầm, và mình phải nói vì nó quyết định bộ số nào đáng "
     "tin.** Bản chạy được ấy có tệp `control.c` với bốn hàm, và cả bốn **đều nằm trong ảnh đã "
     "nạp**. Mình đọc mã máy:\n\n"
     "```\navr-nm mach.elf   → control_init, control_reset, control_set_state, "
     "control_update_4ms\navr-objdump -d    → số lời gọi tới control_* = 0\n```\n\n"
     "**Không ai gọi chúng.** `control.c` là mã chết trong chính bản đã làm robot đứng. Nên mọi "
     "hằng số trong tệp ấy **chưa bao giờ góp phần vào việc robot đứng** — lấy số từ đó là lấy "
     "một bộ tham số chưa từng chạy. Đường chạy thật là `fsm.c` → `pid.c` → `motor.c`, và mọi "
     "số mình cấp đều lấy từ ba tệp ấy.\n\n"
     "Bộ số chính:\n\n"
     "| | giá trị | lấy ở |\n|---|---|---|\n"
     "| `Kp` | **12,0** | `pid.c:4` |\n| `Ki` | **0,4** | `pid.c:5` |\n"
     "| `Kd` | **10,0** | `pid.c:6` |\n| kẹp tích phân | **±400,0** | `pid.c:36-37` |\n"
     "| kẹp ngõ ra | **±400,0** | `pid.c:45-46` |\n"
     "| ngưỡng ngã | **±30,0°** | `config.h:81`, ghi `(V1:319)` |\n"
     "| cửa sổ kích hoạt | **±0,5°** | `config.h:82`, ghi `(V1:414)` |\n\n"
     "Và **hai chi tiết mình thấy trong mã mà tài liệu chính của mình KHÔNG nêu** — mình nhận "
     "đây là chỗ tài liệu thiếu:\n\n"
     "- **Phản hồi ngõ ra vào sai số:** khi `|ngõ ra| > 10` thì sai số cộng thêm "
     "`ngõ ra × 0,015` (`pid.c:30-31`).\n"
     "- **Tự học điểm cân bằng:** mỗi vòng, ngõ ra âm thì điểm cân bằng `+= 0,002`, ngõ ra "
     "dương thì `-= 0,002` (`pid.c:57-58`). **Đây đúng chỗ bạn nêu ở lượt đọc đề** là mục 3.8 "
     "còn mơ hồ. Bạn nêu đúng, và đây là con số thật.\n\n"
     "Quy đổi ngõ ra sang xung, công thức phi tuyến ở `motor.c:57-61`, và dải chu kỳ bước "
     "`|thr| = (50 000 / f) − 1` kẹp trong **1…2 000** — đủ trong mục E.\n\n"
     "Ghi chú `(V1:nnn)` trong `config.h` trỏ về dòng trong mã **V1 của nhà cung cấp**, tức bộ "
     "số đã làm một con robot đứng thật, không phải số mình nghĩ ra. Mình giữ nguyên cách ghi "
     "xuất xứ ấy trong mục E để bạn truy lại được.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Đọc mục E rồi áp bộ số vào mã của bạn. Chỗ nào bạn đang dùng số khác thì **nói "
     "ra**, đừng im — có thể bạn có lý do, và mình muốn nghe.\n\n"
     "**2 ·** Thêm phép khẳng định vào bảng mốc cho **ba hệ số PID và hai ngưỡng góc**. Lý do: "
     "bảng mốc của mình từng chỉ phủ hai chân chiều quay, và ba chân mình không phủ thì lệch "
     "cả ba. Phủ tới đâu bắt được tới đó — nên lần này phủ luôn.\n\n"
     "**3 ·** Và việc còn nợ từ lượt trước: `mach.hex` trên đĩa **cũ hơn `mach.elf` 22 phút**, "
     "nên bản bạn nạp lần rồi là bản cũ — đó là lý do dòng `#STAGE` không ra dù mã có. Mình đã "
     "vá EIDE: nay nạp `.hex` cũ hơn `.elf` thì **bị từ chối** kèm cả hai mốc. Nạp lại cho "
     "đúng, rồi mình đọc bốn số `#STAGE` để chốt chỗ 110 ms.\n\n"
     "Chưa cần robot dựng lên. Bo chỉ có nguồn USB nên động cơ chưa quay được, và mình sẽ nói "
     "khi có pin.",
     3600, 3, False),

    # Chèn 04/10. Bốn số #STAGE: total=916 µs → LOẠI giả thuyết "vòng không kịp" của NGƯỜI.
    # Ba phép đo nay chặn bài toán: việc 916 µs, đồng hồ robot chậm 12%, UART đọc sạch nên
    # thạch anh đúng → nhịp Timer0 đang BỊ MẤT.
    ("Bốn số đã loại giả thuyết của mình. Nhịp Timer0 đang bị mất",
     "Bộ tham số bạn áp xong, mình kiểm: tám hằng số đúng mục E, bảng mốc lên **22 phép khẳng "
     "định** với `A18`–`A22` phủ ba hệ số PID và hai ngưỡng góc. Và lần này **chip khớp từng "
     "byte với ảnh vừa dựng** — mình đọc ngược flash ra so, `#STAGE` có cả trên chip lẫn trong "
     "ảnh. Chốt `DEV-337` làm đúng việc: `mach.hex` nay mốc 20:36:21, sau `mach.elf` 20:36:06.\n\n"
     "**Và bốn số `#STAGE` loại hẳn giả thuyết của mình:**\n\n"
     "```\n#STAGE: i2c=488 filter=420 ctrl=8 total=916 us\n```\n\n"
     "Phần việc trong vòng mất **916 µs**, không phải 4 630 µs. Vòng **thừa sức** đáp hạn 4 ms. "
     "Nên giả thuyết *vòng không kịp* của mình **sai**, và nghi can I2C của mình cũng sai — "
     "488 µs chỉ là 12 % của một vòng 4 ms.\n\n"
     "Mình ghi lại chỗ này vì nó là lần thứ ba trong phiên mình đoán sai rồi phải để số đo "
     "chữa: lần một là *góc trượt 3 độ/giây* hoá ra đường hội tụ; lần hai là *quá hạn = 0* "
     "nghĩa là *chưa trễ tới 40 ms* chứ không phải *chưa trễ*; lần này là *vòng không kịp*.\n\n"
     "**Nhưng chu kỳ vẫn 112,2 ms.** Và giờ ba phép đo chặn bài toán rất chặt:\n\n"
     "| phép đo | nói gì |\n|---|---|\n"
     "| `total = 916 µs` < 4 000 | phần việc không phải chỗ chậm |\n"
     "| chu kỳ 112,2 ms cho mốc 100 ms của robot | **đồng hồ của robot chậm 12 % so với thực** |\n"
     "| UART 9 600 baud đọc chữ sạch suốt 25 giây | **thạch anh đúng** — lệch 12 % thì sai số "
     "baud vượt giới hạn vài phần trăm và mình sẽ nhận được rác |\n\n"
     "Hai điều cuối cùng nhau dẫn tới một kết luận: **thạch anh đúng, mà `millis` đếm thiếu.** "
     "Tức nhịp Timer0 đang **bị mất**, không phải chạy sai tần. Cấu hình Timer0 thì mình đã "
     "kiểm rồi — CTC, chia tần 64, `OCR0A = 249` → đúng 1 000,0 Hz.\n\n"
     "Việc của bạn, và mình muốn **số** chứ không muốn đường suy luận:\n\n"
     "**1 ·** **Đếm số nhịp Timer0 bị mất.** Cách mình nghĩ tới: trong ngắt Timer0, đọc cờ "
     "`OCF0A` **trước khi** xoá — nếu nó đã bật lại thì có một nhịp đã trôi qua trong lúc CPU "
     "còn ở chỗ khác. Hoặc so `TCNT0` lúc vào ngắt với giá trị mong đợi. Bạn chọn, nhưng con "
     "số phải ra được một biến mình đọc qua cổng.\n\n"
     "**2 ·** **Đo thời gian ngắt 50 kHz chiếm bao lâu.** Mình vẫn chưa có con số ấy, và nó là "
     "nghi can còn lại duy nhất: ngắt chạy mỗi 20 µs, nếu nó dùng ~2,5 µs thì chiếm ~13 % — "
     "khớp đúng độ chậm 12 % mình đo được. Cách đo: đọc `TCNT2` ở đầu và cuối hàm ngắt rồi "
     "nhớ giá trị lớn nhất. Một nhịp `TCNT2` là 0,5 µs nên độ phân giải dư sức.\n\n"
     "Nhưng ngắt chiếm 13 % CPU thì **không làm mất nhịp Timer0** — cờ ngắt có mạch chốt, nhịp "
     "chỉ bị *trễ* chứ không *mất*, trừ khi trễ quá cả 1 ms. Nên nếu bạn đo ra ~13 % mà nhịp "
     "vẫn mất, thì ta còn thiếu một mảnh. Đừng vá khi chưa thấy mảnh ấy.\n\n"
     "**3 ·** Và một chỗ mình muốn bạn tự soát: **có đoạn nào trong mã cấm ngắt lâu không?** "
     "`cli()`/`sei()` quanh một đoạn dài, hoặc đọc biến 32 bit `millis` mà cấm ngắt cả lúc "
     "tính toán. Cấm ngắt 1 ms là mất đúng một nhịp, và chuyện ấy **không** hiện ra trong con "
     "số 13 % kia.\n\n"
     "Chưa cần robot dựng lên. Bo chỉ có nguồn USB.",
     3600, 3, False),

    # Chèn 04/10. NGƯỜI nhận ra khả năng cả hai chưa loại: dòng mất TRÊN ĐƯỜNG TRUYỀN, không
    # phải robot gửi chậm. 250 gửi / 223 nhận = thiếu 10,8 % ≈ đúng 12% đo được. Phép phân
    # biệt: số thứ tự trên mỗi dòng.
    ("Một khả năng cả hai mình chưa loại, và nó rẻ nhất để thử",
     "Phép đo chéo của bạn đúng hướng — đếm ngắt Timer2 giữa hai ngắt Timer0, chuẩn là 50, "
     "**≥ 95 là mất ít nhất một nhịp**. Và bạn tự soát `cli()` ra cùng kết quả với mình: chỉ "
     "hai chỗ trong `millis()` và `micros()`, mỗi chỗ vài nhịp.\n\n"
     "Mình cũng ghi nhận bạn báo verifier **hết hạn 15 lượt** và **không tự kết luận đạt**. Đó "
     "là chỗ đáng tin — mình thà nghe *chưa đủ dữ kiện* còn hơn nghe một chữ *đạt* không có "
     "chứng thực. Hạn 15 lượt ấy là lỗ của EIDE, không phải của bạn; mình có ghi nó trong danh "
     "sách việc chờ làm.\n\n"
     "**Nhưng mình vừa nhận ra một khả năng cả hai mình chưa loại, và nó giải thích 12 % gọn "
     "hơn mọi giả thuyết đang có.**\n\n"
     "Mình đếm **223 dòng trong 25 giây** rồi suy ra chu kỳ 112 ms. Nhưng phép suy ấy giả định "
     "**mọi dòng robot gửi đều tới tay mình**. Nếu robot gửi đủ 250 dòng mà 27 dòng mất trên "
     "đường thì thiếu đúng **10,8 %** — và mình sẽ đo ra *chu kỳ 112 ms* trong khi robot chạy "
     "hoàn toàn đúng 100 ms.\n\n"
     "Chỗ mất có thể ở: đường USB-nối tiếp, bộ đệm hệ điều hành, hay chính vòng đọc của mình. "
     "Và **biến đếm dòng bỏ của bạn vẫn 0 là đúng** — vì chỗ mất nằm **sau** UART của chip, "
     "ngoài tầm nó đếm.\n\n"
     "Nếu đúng vậy thì cả chuỗi suy luận của hai mình về *mất nhịp Timer0* đang đi tìm một lỗi "
     "**không tồn tại**. Mình kể cả quá trình ra vì nó đáng ghi: ba số đo đúng — 916 µs, 112 "
     "ms, UART đọc sạch — ghép lại thành một kết luận sai, chỉ vì một giả định **không ai nói "
     "ra**: rằng đếm dòng nhận được bằng đếm dòng gửi đi.\n\n"
     "**Phép phân biệt rẻ nhất: đánh số thứ tự mỗi dòng.**\n\n"
     "Việc của bạn, làm trước mọi thứ khác:\n\n"
     "**1 ·** Thêm **số thứ tự tăng dần** vào đầu mỗi dòng theo dõi và mỗi dòng `#STAGE`. Một "
     "lượt đọc là mình biết ngay:\n"
     "   - số thứ tự **liên tục** mà tới chậm → robot gửi chậm thật, và ta quay lại chuyện mất "
     "nhịp;\n"
     "   - số thứ tự **nhảy cóc** → dòng mất trên đường, robot không có lỗi gì, và cả giả "
     "thuyết mất nhịp Timer0 tự tan.\n\n"
     "**2 ·** Và thêm luôn **giá trị `millis()` của chính robot** vào dòng. Có nó thì mình so "
     "trực tiếp đồng hồ robot với đồng hồ máy mình, không cần suy qua số dòng nữa — đây là "
     "phép đo mà đáng ra mình phải xin từ đầu thay vì suy ba lần.\n\n"
     "**3 ·** Phép đo chéo Timer2-giám-sát-Timer0 của bạn thì vẫn làm, nhưng **làm sau**. Nếu "
     "số thứ tự cho thấy dòng mất trên đường thì không cần tới nó nữa, và ta tiết kiệm được "
     "một lượt.\n\n"
     "Nạp xong báo mình, mình đọc cổng lấy số.",
     3600, 3, False),

    # Chèn 04/10. KẾT: không có lỗi định thời nào. 372/372 khoảng đúng 100 ms, 0 số thứ tự
    # thiếu. Cả chuỗi 115,7→112,2→90,85 ms là GIẢ TẠO do phép đếm của NGƯỜI: hai loại dòng
    # chu kỳ khác nhau dùng chung một dãy số thứ tự.
    ("Không có lỗi định thời nào. Năm lượt vừa rồi mình đuổi một cái không tồn tại",
     "Số thứ tự và `millis` bạn thêm đã kết thúc chuyện này trong **một lượt đọc**, và kết quả "
     "là: **robot chạy đúng đặc tả, chưa từng có lỗi định thời.**\n\n"
     "| phép đo | kết quả |\n|---|---|\n"
     "| số thứ tự thiếu, khi đếm **cả hai** loại dòng | **0** |\n"
     "| khoảng `millis` giữa hai dòng theo dõi liền nhau | **372/372 khoảng = đúng 100 ms** |\n"
     "| đồng hồ robot so đồng hồ tường | **+0,02 %** |\n"
     "| phần việc trong vòng | 908–920 µs trên hạn 4 000 |\n\n"
     "Chỗ mình đọc sai nằm ngay trong dòng thô:\n\n"
     "```\n10 2498 LOWBATT ...\n#STAGE 11 2546: i2c=484 filter=420 ctrl=16 total=920 us\n"
     "12 2598 LOWBATT ...\n```\n\n"
     "Số thứ tự **dùng chung** cho hai loại dòng. Mỗi số thứ 11 thuộc dòng `#STAGE`. Bộ lọc "
     "của mình chỉ nhận dòng theo dõi, nên nó báo 57 *số thứ tự thiếu* — **chính bộ lọc dựng "
     "ra cái lỗ**. Và vì `#STAGE` phát giữa chu kỳ (2546, cách 2498 có 48 ms), chu kỳ trung "
     "bình theo số thứ tự bị nén xuống 90,9 ms.\n\n"
     "**Cả chuỗi số mình đã truy năm lượt — 115,7 → 115,0 → 112,2 → 110 → 90,85 ms — là giả "
     "tạo do phép đếm của mình.** Mình đếm dòng rồi chia cho thời gian tường, trong khi hai "
     "loại dòng có chu kỳ khác nhau.\n\n"
     "Mình kê lại để cả hai dùng được về sau, vì đây là lượt đáng giá nhất của phiên:\n\n"
     "| lượt | mình kết luận | sự thật |\n|---|---|---|\n"
     "| 1 | góc **trượt** 3 độ/giây | đường **hội tụ** về 73°, τ = 10 s, đúng đặc tả |\n"
     "| 2 | *quá hạn = 0* ⇒ vòng đáp hạn 4 ms | biến ấy đếm *trễ quá **40 ms*** |\n"
     "| 3 | vòng **không kịp** 4 ms | vòng dùng **916 µs** trên 4 000 |\n"
     "| 4 | **mất nhịp** Timer0 | `millis` chính xác tới **0,02 %** |\n"
     "| 5 | dòng **mất trên đường** | 0 dòng mất; số thứ tự liền mạch |\n\n"
     "Năm lần, và **mỗi phép đo riêng lẻ đều đúng**. Chỗ sai luôn là chỗ mình **ghép** chúng "
     "lại: mỗi lần mình lấy một con số rồi suy ra một kết luận mà con số ấy không chứa.\n\n"
     "Và thứ gỡ được nó là việc đơn giản nhất có thể: **hỏi thiết bị xem nó nghĩ mấy giờ.** "
     "Mình suy năm lượt trước khi xin con số ấy. Nếu lần sau mình lại đi đo một thứ bằng cách "
     "đếm **bên ngoài** nó, bạn nhắc mình xin mốc thời gian **từ bên trong** trước.\n\n"
     "Chuyện này cũng không vô ích: trên đường đi ta tìm ra `DEV-337` thật — `mach.hex` cũ hơn "
     "`mach.elf` 22 phút, nạp bản cũ mà đối chiếu vẫn đạt. Lỗi ấy có thật và đã vá. Nhưng cái "
     "mình **đuổi** thì không tồn tại.\n\n"
     "Việc của bạn, gọn:\n\n"
     "**1 ·** Đổi dòng `#STAGE` sang **dãy số thứ tự riêng**, hoặc ghi rõ trong tài liệu rằng "
     "hai loại dòng dùng chung dãy. Mình nghiêng về **dãy riêng**, vì một dãy liền mạch là "
     "cách rẻ nhất để biết có mất dòng hay không — mà đó đúng là câu mình cần hỏi khi robot "
     "dựng lên và đổ.\n\n"
     "**2 ·** Bỏ phép đo chéo Timer2-giám-sát-Timer0 khỏi việc cần làm. Không còn lý do.\n\n"
     "**3 ·** Rồi kê cho mình **bảng nghiệm thu cập nhật**: dòng nào đã đạt kèm số đo, dòng "
     "nào còn chờ **pin và nguồn động cơ**. Mình muốn chốt phần làm được trên USB trước khi "
     "nghỉ, để lúc có pin thì vào thẳng phần ba dấu.",
     3600, 3, False),

    # Chèn 04/10. Bảng nghiệm thu có HAI lỗi trong cùng một dòng NT-A: gọi sai ngoại vi
    # (Timer1 top 319 thay vì Timer2 pre8 OCR39), và ĐẠT bằng cấu hình chứ không bằng phép đo
    # — đúng điều mục 6.1b mà NGƯỜI viết trong chính phiên này cấm.
    ("Bảng nghiệm thu: hai lỗi trong cùng một dòng",
     "Bảng của bạn ghi đúng xuất xứ — các dòng mình đo đều ghi *(anh đo)*, và đó là cách ghi "
     "mình cần. Dãy số thứ tự riêng cho `#STAGE` cũng xong.\n\n"
     "Nhưng dòng **NT-A** có hai lỗi, và cả hai cùng nằm ở một chỗ.\n\n"
     "**1 · Gọi sai ngoại vi.** Bảng ghi *Timer1 CTC top 319*. Mình mở `firmware/timer.c` ra "
     "đọc:\n\n"
     "```c\nTCCR2A = (1 << WGM21);\nTCCR2B = (1 << CS21);   /* chia tần 8 */\n"
     "OCR2A  = 39;\nTIMSK2 = (1 << OCIE2A);\n```\n\n"
     "Là **Timer2**, chia tần 8, `OCR2A = 39`. Và hàm ngắt là `ISR(TIMER2_COMPA_vect)`.\n\n"
     "Chỗ đáng chú ý: cả hai cấu hình **đều cho 50 kHz về số học** — `16/(1×320)` và "
     "`16/(8×40)`. Nên lỗi này **vô hình với người kiểm phép tính**; chỉ mở mã ra mới thấy nó "
     "gọi sai ngoại vi. Nếu ai đọc báo cáo rồi đi tìm Timer1 trong mã thì họ sẽ không tìm "
     "thấy, và họ sẽ không biết mình đang đọc sai hay mã đang sai.\n\n"
     "**2 · ĐẠT bằng cấu hình, không bằng phép đo.** Bằng chứng bạn ghi cho NT-A là *đã cấu "
     "hình Timer… chạy liên tục*. Đó là một lời khai về **cấu hình**, không phải một **số đo "
     "tần số**.\n\n"
     "Và mục **6.1b** phụ lục nói thẳng điều này — mục ấy **mình viết trong chính phiên này**, "
     "sau khi mất một lượt nạp ở việc RTOS vì đúng lỗi ấy:\n\n"
     "> *Giá trị cấu hình không phải phép đo. SysTick nạp 179 999 là đúng, nhưng nó chỉ nói "
     "nhịp sẽ là 1 000 Hz NẾU xung nhịp là 180 MHz.*\n\n"
     "Ở đây y như vậy: `OCR2A = 39` đúng, nhưng nó chỉ nói *ngắt sẽ là 50 kHz NẾU chia tần "
     "đúng 8 và thạch anh đúng 16 MHz*.\n\n"
     "**Nhưng giờ đo được thật, và đo được vì một chuyện vừa xảy ra.** `millis` của bạn đã "
     "được mình đối chiếu với đồng hồ tường: lệch **+0,02 %** trên 372 khoảng. Nên `millis` "
     "nay là một mốc thời gian **đã kiểm**, không còn là lời khai.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Thêm một biến đếm **số lần ngắt 50 kHz** đã chạy, in ra dòng theo dõi. Mình đọc "
     "hai dòng cách nhau, lấy hiệu số đếm chia hiệu `millis` là ra **tần số thật**. Chuẩn là "
     "50 lần mỗi mili-giây.\n\n"
     "Chỗ này bạn từng cảnh báo rất đúng ở bước 7 — *đếm bằng chính bộ đếm mình đang đo là đo "
     "lại chính nó*. Mình nghĩ lần này **không** phải trường hợp ấy, và muốn bạn kiểm lại lập "
     "luận của mình: Timer0 và Timer2 là hai bộ chia khác nhau, nên tỉ số của chúng chỉ nói về "
     "hai bộ chia; **nhưng** thạch anh đã được đối chiếu độc lập với đồng hồ tường của mình, "
     "nên tỉ số cộng với mốc tường cho ra con số tuyệt đối. Bạn thấy lập luận ấy kín chưa? Nếu "
     "hở thì nói, mình sẽ tìm cách khác.\n\n"
     "**2 ·** Sửa dòng NT-A trong bảng: gọi đúng **Timer2 / chia tần 8 / `OCR2A = 39`**, và "
     "**đổi trạng thái từ ĐẠT về chờ đo** cho tới khi có con số. Mình thà bảng có một dòng "
     "*chưa đo* còn hơn có một dòng *đạt* mà không có số.\n\n"
     "**3 ·** Và soát nốt cả bảng theo đúng câu ấy: **còn dòng nào đang ĐẠT bằng cấu hình chứ "
     "không bằng số đo?** Mình nghi còn, vì mình vừa tìm thấy một dòng.",
     3600, 3, False),

    # Chèn 04/10. Tác tử tìm thêm HAI dòng đạt-bằng-cấu-hình (người chỉ tìm được một), và tìm
    # ra lỗ "đọc rách" trong phép đo người đề xuất. Nhưng dòng τ=10s thì nó tự nhận nhẹ hơn
    # thực: chuyển tiếp lúc bật nguồn CHÍNH LÀ một kích xung, và người đã so 5 điểm.
    ("Bạn tìm thêm hai dòng, và một dòng mình phải bảo vệ",
     "Ba chỗ bạn làm hay ở lượt này, mình nêu để bạn giữ cách:\n\n"
     "**Bạn kiểm lại lập luận của mình rồi làm nó chặt hơn.** Mình chỉ nói *hai bộ chia khác "
     "nhau nên tỉ số không phải đo lại chính nó*; bạn bổ sung đúng mắt còn thiếu: vì đồng hồ "
     "tường đã chốt `millis` ở +0,02 %, thạch anh **được kiểm định** ở ~16,0032 MHz, nên tỉ số "
     "cho ra **tần số tuyệt đối** với độ không đảm bảo ±0,02 %. `NT-A` đòi ±1 %, nên dư.\n\n"
     "**Bạn tìm ra một lỗ mình không nghĩ tới:** đọc rách biến `uint32_t` trên CPU 8 bit. Mình "
     "đề xuất phép đo mà không nghĩ tới chuyện ấy, và bạn đã đóng gói phép đọc nguyên tử sẵn.\n\n"
     "**Và bạn biến một rủi ro thành một phép kiểm:** nếu tỉ số ra đúng 50 lần/ms thì đồng "
     "thời chứng minh firmware không nghẽn ngắt ở chặng nào. Một phép đo trả lời hai câu.\n\n"
     "**Hai dòng bạn tìm thêm thì mình nhận một, và bảo vệ một.**\n\n"
     "**Dòng I2C 400 kHz — bạn đúng hẳn.** Con số ấy tính từ `TWBR = 12`, chưa ai kẹp máy hiện "
     "sóng vào chân SCL. Đổi về *chờ đo*. Và chỗ này đáng để nhớ: tài liệu mình nêu bản cũ "
     "từng sập vì **I2C quá nhanh sau khi nâng xung nhịp**, nên đây đúng là dòng không được "
     "đạt bằng phép tính.\n\n"
     "**Dòng `τ = 10 s` — mình bảo vệ, và mình giải thích vì sao.** Bạn viết *chưa có thí "
     "nghiệm kích xung góc nghiêng để đo thời gian hồi phục 63,2 %*. Nhưng mình nghĩ ta **đã "
     "có** một kích xung, chỉ là ta không gọi nó bằng tên ấy: **chuyển tiếp lúc bật nguồn**. "
     "Góc chạy khởi tạo ở 0, góc theo gia tốc là 72,96°, nên bật nguồn chính là một bước nhảy "
     "từ 0 lên 73°.\n\n"
     "Và mình đã so **năm điểm** trên đường ấy với dự đoán `τ = 10 s`:\n\n"
     "| t (s) | đo được | dự đoán τ=10 s | nếu trượt tuyến tính |\n|---|---|---|---|\n"
     "| 4,5 | 25,05 | **26,44** | 7,18 |\n| 11,2 | 47,44 | **49,27** | 17,96 |\n"
     "| 22,5 | 64,08 | **65,27** | 35,92 |\n| 33,8 | 69,84 | **70,46** | 53,89 |\n"
     "| 45,0 | 71,85 | **72,15** | 71,85 |\n\n"
     "Năm điểm khớp đường hội tụ và lệch hẳn đường tuyến tính. Đó là một **phép đo đáp ứng "
     "bước** thật, chỉ khác là bước đầu vào do bật nguồn tạo ra chứ không do mình nghiêng tay. "
     "Nên mình giữ dòng ấy ở **đạt**, mà ghi rõ *đo từ chuyển tiếp lúc bật nguồn, 5 điểm*.\n\n"
     "Mình nói chỗ này ra vì nguyên tắc *cấu hình không phải phép đo* không có nghĩa là **mọi "
     "con số trùng với cấu hình đều đáng nghi**. Nếu một phép đo độc lập ra đúng con số mà cấu "
     "hình dự đoán, thì đó là bằng chứng mạnh — không phải bằng chứng yếu. Ranh giới là: ta có "
     "**đo** không, hay ta chỉ **đọc thanh ghi rồi tính**.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Nạp bản có biến đếm ngắt (mình thấy bạn đã dựng lúc 13:58:38 mà chưa nạp), rồi "
     "mình đọc cổng lấy tỉ số, chốt `NT-A` bằng số.\n\n"
     "**2 ·** Sửa bảng: `NT-A` gọi đúng **Timer2 / chia tần 8 / `OCR2A = 39`**; dòng I2C về "
     "*chờ đo*; dòng `τ` giữ **đạt** với ghi chú *đo từ chuyển tiếp bật nguồn, 5 điểm*.\n\n"
     "**3 ·** Rồi chốt bảng cuối thành hai phần rõ: **đạt trên nguồn USB** và **chờ pin cùng "
     "nguồn động cơ**. Mình sẽ lưu trạng thái ở đó.",
     3600, 3, False),

    # Chèn 04/10. NT-A đo được 50,0005 kHz (+0,0009 %), neo vào đồng hồ tường. Và người lại
    # vừa lặp đúng lỗi cũ: lọc dòng theo tiền tố "#T " tự đoán, 406 dòng ra 0 dòng khớp.
    ("NT-A: 50,0005 kHz — và mình lại lọc sai một lần nữa",
     "Đo xong. **`NT-A` đạt bằng số, không bằng cấu hình nữa.**\n\n"
     "| | |\n|---|---|\n| Δ`millis` | 36 800 ms |\n| Δ`step_ticks` | 1 840 017 lần |\n"
     "| tỉ số | **50,00046 lần/ms** |\n| tần số | **50,0005 kHz** |\n"
     "| lệch so với 50 kHz | **+0,0009 %** |\n| `NT-A` cho phép | ±1 % |\n\n"
     "Dư hơn một nghìn lần so với ngưỡng.\n\n"
     "**Và phép quy chiếu tuyệt đối khép lại.** Đồng hồ tường của mình: 40,015 s. Robot báo đã "
     "chạy 38,398 s, cộng 1,598 s trước dòng đầu tiên (bộ nạp khởi động) là 39,996 s — hụt "
     "19 ms, bằng đúng chỗ lượt thu cắt giữa dòng. Nên con số 50 kHz này **neo vào đồng hồ "
     "tường**, không neo vào thanh ghi `OCR2A`. Đó là khác biệt giữa dòng này hôm nay và dòng "
     "ấy hôm qua.\n\n"
     "**Và dự đoán của bạn thành một kết quả thứ hai:** `0` số thứ tự thiếu trên 369 dòng. Nên "
     "phép đo này đồng thời chứng minh **không nghẽn ngắt ở chặng nào** — đúng như bạn nói. "
     "Một phép đo trả lời hai câu.\n\n"
     "**Giờ chỗ mình làm sai, nói ra để vào sổ.** Lượt thu đầu tiên mình lọc dòng theo tiền tố "
     "`#T `, vì mình *đoán* dòng theo dõi có tiền tố như `#STAGE`. Kết quả: thu **406 dòng**, "
     "lọc ra **0 dòng**. Mở dữ liệu thô ra mới thấy dòng theo dõi **không có tiền tố nào** — "
     "nó bắt đầu luôn bằng số thứ tự.\n\n"
     "Đây là **lần thứ hai trong phiên này** mình lọc theo một tiền tố tự nhớ rồi đọc sai dữ "
     "liệu. Lần trước nó tạo ra năm lượt đuổi một lỗi định thời không tồn tại. Lần này nó chỉ "
     "mất một lượt thu, vì `0 dòng` thì không ai tin được — nó **gãy to**, nên nó rẻ. Lần "
     "trước nó cho ra `115,7 ms` — một con số **trông hợp lý**, nên nó đắt.\n\n"
     "Rút ra: một phép lọc sai mà trả về rỗng thì vô hại; một phép lọc sai mà trả về **số đẹp** "
     "thì tốn năm lượt. Nên khi nào lọc dữ liệu thô, việc đầu tiên phải là **mở dữ liệu thô ra "
     "xem**, chứ không phải tin vào định dạng mình nhớ. Mình sẽ ghi điều này vào mục B phụ "
     "lục.\n\n"
     "Việc cuối của bạn hôm nay:\n\n"
     "**1 ·** Chốt dòng `NT-A` thành **ĐẠT** với số đo `50,0005 kHz (+0,0009 %)`, ghi rõ cách "
     "đo là *tỉ số Timer2/Timer0 neo vào đồng hồ tường, 36,8 giây*, và gọi đúng **Timer2 / "
     "chia tần 8 / `OCR2A = 39`**.\n\n"
     "**2 ·** Thêm một dòng mới cho kết quả đi kèm: *không nghẽn ngắt — 0 số thứ tự thiếu trên "
     "369 dòng*.\n\n"
     "**3 ·** Rồi **in bảng nghiệm thu cuối cùng**, hai phần rõ rệt: **đạt trên nguồn USB** "
     "(kèm số đo và ai đo) và **chờ pin cùng nguồn động cơ**. Mình sẽ lưu bảng ấy vào sở cứ và "
     "dừng phiên ở đó, để lúc có pin thì vào thẳng phần ba dấu.\n\n"
     "Một chuyện nhỏ mình thấy mà chưa hỏi: trường qua hạn đứng yên ở **2** suốt 369 dòng, và "
     "dòng đầu tiên đã là 2. Nên hai lần ấy xảy ra **lúc khởi động**, không phải lúc chạy. Bạn "
     "có biết hai lần ấy ở đâu ra không? Nếu biết thì ghi vào bảng; nếu không thì ghi là *chưa "
     "truy được* — đừng đoán.",
     3600, 3, False),

    # Chèn 04/10. Tác tử xếp NT-B (250 Hz) vào phần chờ máy hiện sóng. Người cho rằng dữ liệu
    # đã có sẵn — nhưng lập luận có nguy cơ VÒNG TRÒN vì vòng lặp được nhịp bằng chính millis.
    # Hỏi tác tử soát vòng tròn, không tự kết luận.
    ("NT-B: mình nghĩ đã đo được, nhưng lập luận có thể vòng tròn",
     "Bảng này sạch. Và chỗ hay nhất là `NT-OVERRUN`: mình hỏi *hai lần qua hạn ấy ở đâu ra*, "
     "và bạn **truy ra được**, dẫn `fsm.c:90-92`, chỉ rõ một lần do pha hiệu chuẩn 1,5 s và một "
     "lần do mốc thời gian chưa gán lại sau đó. Nên `overrun = 2` không còn là con số lơ lửng "
     "trong báo cáo — nó có nguyên nhân. Bạn đã không đoán, và đó là việc mình cần.\n\n"
     "Còn một dòng mình muốn bàn: **`NT-B` — vòng điều khiển 250 Hz.** Bạn xếp nó vào phần chờ, "
     "cần *máy hiện sóng đo chân A1*. Mình nghĩ **dữ liệu để chốt nó đã có trong tay rồi**, "
     "nhưng mình **không chắc lập luận của mình kín**, nên nhờ bạn soát — chứ không phải nhờ "
     "bạn làm theo.\n\n"
     "Lập luận của mình:\n\n"
     "1. Dòng theo dõi phát mỗi **25 nhịp** vòng điều khiển.\n"
     "2. Mình đã đo **372/372 khoảng** giữa các dòng ấy đúng **100 ms** theo `millis`.\n"
     "3. `millis` neo vào đồng hồ tường ở **+0,02 %**.\n"
     "4. Vậy 25 nhịp = 100,0 ms thực → một nhịp = 4,00 ms → **250 Hz**.\n\n"
     "**Chỗ mình nghi vòng tròn.** Từ lời giải thích `overrun` của bạn, vòng lặp được **nhịp "
     "bằng chính `millis`** (`now - g_last_loop_time`). Nếu vậy thì khoảng 100 ms giữa hai dòng "
     "theo dõi có phần là **do xây dựng** mà ra, không phải do đo: vòng lặp chờ cho tới khi "
     "`millis` đủ 4 ms, nên tất nhiên 25 nhịp ra 100 ms. Đo như thế là đo lại chính cái lịch "
     "mình đặt — đúng cái bẫy bạn cảnh báo mình ở bước 7.\n\n"
     "**Và chỗ mình nghĩ nó vẫn còn giá trị.** Nếu vòng lặp **không theo nổi** lịch 4 ms, nhịp "
     "sẽ dài ra và khoảng giữa hai dòng sẽ **vượt** 100 ms — ta sẽ thấy. Ta không thấy, và "
     "`overrun` không tăng lần nào trong 369 chu kỳ. Nên phép đo này chứng minh **vòng lặp đáp "
     "ứng đúng lịch của nó**, mà cái lịch ấy lại neo vào đồng hồ tường.\n\n"
     "Nên câu hỏi của mình gọn thế này: **“vòng lặp đáp ứng đúng lịch 4 ms neo đồng hồ tường, "
     "0 lần trễ trên 369 chu kỳ” có đủ để chốt `NT-B` chưa, hay nó vẫn là một dạng đo lại chính "
     "mình và phải chờ máy hiện sóng?**\n\n"
     "Mình nghiêng về **đủ**, nhưng mình đã sai năm lượt liền trong phiên này vì tin vào lập "
     "luận của mình mà không kiểm, nên lần này mình hỏi trước.\n\n"
     "Nếu bạn thấy **đủ**: chuyển `NT-B` sang Phần I với số đo và ghi rõ phương pháp là *đáp "
     "ứng lịch, không phải đo xung độc lập* — người đọc phải thấy được khác biệt ấy.\n"
     "Nếu bạn thấy **chưa đủ**: giữ ở Phần II, mà sửa điều kiện cần cho đúng — vì nó **không "
     "cần pin**, chỉ cần máy hiện sóng. Xếp lẫn với mấy dòng chờ pin làm người đọc tưởng cả ba "
     "dòng cùng một lý do.",
     3600, 3, False),
]

TEN_GIAI_DOAN = {
    1: "Đọc đề và dựng môi trường",
    2: "Mã trên máy và bộ kiểm",
    3: "Chạy trên bo thật",
    4: "Chốt và báo cáo",
}


def dung_du_an(giu: bool) -> None:
    """Dựng dự án TRỐNG, chỉ có tệp giao việc. Không chép gì từ dự án cũ."""
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    (DU_AN / ".eide" / "ui-test").mkdir(parents=True, exist_ok=True)
    (DU_AN / "tai-lieu").mkdir(exist_ok=True)

    # Chép TỪNG tệp đầu vào, rồi KIỂM LẠI từng tệp đã có mặt và đúng kích thước.
    #
    # Vì sao phải kiểm thay vì tin `shutil.copy`: trong một ngày tôi ba lần khẳng định một tệp
    # đã ở chỗ cần mà nó không ở đó — `cp` thất bại im lặng với `logo_ptit.h`, xoá nhầm ba tệp
    # driver vì nhìn hình dạng tên, và phép thay chuỗi không khớp nên phụ lục này chưa bao giờ
    # được chép. Lần thứ ba thì tác tử là người phát hiện: *"Thiếu tệp Phụ lục"*.
    #
    # Ba lần cùng một gốc, và gốc KHÔNG phải thiếu cẩn thận: tôi chạy một lệnh có thể thất bại
    # rồi khẳng định kết quả mà không kiểm hậu điều kiện. Đúng thứ tôi đòi ở tác tử suốt hai
    # ngày. Nên chỗ này tự kiểm, và thiếu thì DỪNG PHIÊN.
    thieu = []
    for nguon in (TAI_LIEU, PHU_LUC):
        if not nguon.exists():
            thieu.append(f"{nguon} — không có ở NGUỒN")
            continue
        dich = DU_AN / "tai-lieu" / nguon.name
        if not dich.exists():
            shutil.copy(nguon, dich)
        # DỪNG chỉ khi tệp THIẾU hoặc RỖNG. Lệch kích thước thì **nói ra**, không dừng.
        #
        # Bản đầu của chốt này so bằng kích thước rồi kết luận "chép không tới", và nó nổ sai
        # ngay lần đầu gặp chuyện thật: tác tử bổ sung mục NT-D vào phụ lục trong dự án — việc
        # hợp lý, nó báo rõ — nên bản trong dự án lớn hơn bản gốc.
        #
        # Lẫn "chép thất bại" với "tệp đã được sửa" là đúng cùng hình dạng lỗi mà DEV-336 vừa
        # vá trong EIDE: một kết luận gộp hai nguyên nhân dẫn tới hai việc ngược nhau — một
        # cái bảo chép lại, cái kia bảo đọc xem ai sửa gì.
        if not dich.exists() or dich.stat().st_size == 0:
            thieu.append(f"{dich.name} — thiếu hoặc rỗng")
        elif dich.stat().st_size != nguon.stat().st_size:
            print(f"{VANG}  · {dich.name}: bản trong dự án {dich.stat().st_size} byte, "
                  f"bản gốc {nguon.stat().st_size} byte — tệp đã được sửa trong dự án, "
                  f"KHÔNG chép đè.{HET}")
    if thieu:
        raise SystemExit(f"{DO}ĐẦU VÀO KHÔNG ĐỦ — phiên dừng, vì giao việc thiếu tài liệu là "
                         f"giao một đề bài khác:{HET}\n  " + "\n  ".join(thieu))
    RA.mkdir(parents=True, exist_ok=True)


def ghi_quan_sat(buoc: int, ten: str, cau: str) -> None:
    RA.mkdir(parents=True, exist_ok=True)
    with QUAN_SAT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"buoc": buoc, "ten": ten, "nguoi_noi": cau,
                            "luc": time.strftime("%Y-%m-%d %H:%M:%S")},
                           ensure_ascii=False) + "\n")


def chay(buoc_chon: set[int] | None, giu: bool, quan_sat: str) -> int:
    from eide.config import load_dotenv

    load_dotenv()
    dung_du_an(giu)

    thieu = [(i, t) for i, (t, _, _, _, can) in enumerate(BUOC, 1)
             if can and (not buoc_chon or i in buoc_chon) and not quan_sat.strip()]
    if thieu:
        print(f"{DO}Bước cần câu quan sát của người mà chưa có:{HET}")
        for i, t in thieu:
            print(f"  bước {i}: {t}")
        return 2

    nk = NhatKy(RA, tieu_de="phiên sinh viên — hệ điều hành thời gian thực tự viết",
                nguon=str(TAI_LIEU.relative_to(REPO)),
                du_an=str(DU_AN.relative_to(REPO)))
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
        nk.anh(g, ten.lower().replace(" ", "-")[:34])

        cc = cong_cu_da_goi(DU_AN, tu=truoc)
        dat = sum(1 for c in cc if c.get("ok"))
        nk.ghi("Công cụ đã gọi trong lượt này",
               f"{len(cc)} lời gọi ({dat} chạy được · {len(cc) - dat} báo lỗi): "
               + ", ".join(sorted({c['tool'] for c in cc})) if cc
               else "Không gọi công cụ nào.")
        print(f"{XAM}  công cụ: {len(cc)} lời gọi, {dat} chạy được{HET}")
        da_chay += 1

    llm = sorted((DU_AN / ".eide" / "llm").glob("*.jsonl"))
    n = sum(1 for p in llm for d in p.read_text("utf-8", errors="replace").splitlines()
            if d.strip())
    nk.ghi("Dấu vết phiên để lại",
           f"Sổ cái {so_dong_so_cai(DU_AN)} dòng · nhật ký mô hình {n} lời gọi · "
           f"{len(list((RA / 'anh').glob('*.png')))} ảnh cửa sổ EIDE")
    print(f"\n{XANH}Đã chạy {da_chay} bước.{HET}\n{VANG}Nhật ký: {nk.md}{HET}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Phiên sinh viên — việc 3/3: robot tự cân bằng")
    ap.add_argument("--giai-doan", type=int, choices=sorted(TEN_GIAI_DOAN))
    ap.add_argument("--buoc", default="")
    ap.add_argument("--quan-sat", default="")
    ap.add_argument("--giu-du-an", action="store_true")
    ap.add_argument("--liet-ke", action="store_true")
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

    if chon and min(chon) > 1 and not a.giu_du_an:
        print(f"{DO}Chạy từ bước {min(chon)} thì phải thêm --giu-du-an, "
              f"không thì dự án bị dựng lại từ trống.{HET}")
        return 2

    return chay(chon, a.giu_du_an, a.quan_sat)


if __name__ == "__main__":
    raise SystemExit(main())
