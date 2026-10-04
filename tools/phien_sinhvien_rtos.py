"""Phiên sinh viên — việc 2/3: tự viết hệ điều hành thời gian thực, bỏ FreeRTOS.

Làm lại từ dự án TRỐNG, với đầu vào mới
`docs/rtos-tu-viet/DAU-VAO-AGENT-RTOS-v2.md`, để lấy số liệu thật cho báo cáo.

Ba ràng buộc của phiên này:

1. **Dự án trống.** Không chép gì từ `docs/rtos-tu-viet/firmware-chay-duoc`. Chép là tác tử
   đọc ra đáp án, và con số đo được sẽ nói về việc chép chứ không về việc làm.
2. **Người đóng vai sinh viên.** Biết đọc mã C và sơ đồ chân, **chưa từng viết bộ lập lịch,
   chưa từng viết chuyển ngữ cảnh bằng hợp ngữ**. Không mớm đáp án, không dùng trình độ cao
   hơn. Chỗ nào người không đủ trình để kiểm thì nói ra trong chính câu giao việc.
3. **Mọi bước đi qua giao diện thật**, mỗi bước một ảnh cửa sổ EIDE do chính app vẽ ra.

Tài liệu đầu vào cố ý **để trống hai chỗ** để đo xem tác tử có tự xác định được không:
tần số I2C ở 180 MHz, và kích thước ngăn xếp mỗi tác vụ.

    .venv/bin/python tools/phien_sinhvien_rtos.py --liet-ke
    .venv/bin/python tools/phien_sinhvien_rtos.py --giai-doan 1
    .venv/bin/python tools/phien_sinhvien_rtos.py --buoc 9 --quan-sat "..."
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

DU_AN = REPO / "du-lieu/rtos-sinhvien"
RA = REPO / "du-lieu/ket-qua/rtos-sinhvien"
TAI_LIEU = REPO / "docs/rtos-tu-viet/DAU-VAO-AGENT-RTOS-v2.md"
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
    ("Đọc tài liệu giao việc",
     "Chào bạn. Mình là sinh viên đang làm đồ án nhúng. Việc này mình nhờ bạn khá nhiều vì mình "
     "chưa từng viết bộ lập lịch, cũng chưa từng viết chuyển ngữ cảnh bằng hợp ngữ. Mình vừa "
     "đưa vào dự án tệp tài liệu giao việc. Bạn đọc hết rồi tóm tắt lại cho mình: mình cần làm "
     "gì, đạt nghĩa là gì, chỗ nào mình đã cho sẵn số và chỗ nào bạn phải tự xác định.",
     1800, 1, False),

    ("Kiểm công cụ trước khi viết dòng nào",
     "Trước khi viết mã, mình muốn biết **máy này có đủ công cụ chưa**. Bạn tra giúp: trình "
     "biên dịch cho lõi Cortex-M4F có không, công cụ nạp cho kit STM32 có không, và bạn đọc "
     "được trạng thái chip qua cổng gỡ lỗi không. Thiếu gì thì nói thiếu, đừng để tới lúc nạp "
     "mới biết.\n\nMình hỏi câu này vì ở việc trước mình gặp một nhánh công cụ **chưa từng "
     "chạy lần nào** nên nó nổ ngay lần gọi đầu, mà danh sách công cụ thì vẫn có tên nó.",
     1200, 1, False),

    ("Dựng bộ xương dự án",
     "Bạn dựng bộ xương dự án cho mình: linker script theo bản đồ bộ nhớ ở mục 3 tài liệu, tệp "
     "khởi động, và một `main.c` rỗng chỉ nhảy vào vòng lặp vô tận. Dịch thử cho nó qua.\n\n"
     "Mình cần **ba con số** sau khi dịch: kích thước `.text`, `.data`, `.bss`. Và nói cho mình "
     "biết **những tệp nào thật sự được dịch vào ảnh** — mình muốn thấy danh sách, không phải "
     "chữ 'thành công'.",
     1800, 1, False),

    # ------------------------------------------------ 2 · NHÂN RTOS TRÊN MÁY
    ("Nhân: bạn thiết kế trước, mình duyệt sau",
     "Giờ tới phần mình không kiểm được bằng mắt, nên mình muốn bạn **nói trước khi viết**.\n\n"
     "Bạn thiết kế nhân theo mục 4 tài liệu rồi trình bày cho mình bốn điều:\n\n"
     "1. Cấu trúc mô tả một tác vụ gồm những trường gì, và vì sao cần từng trường.\n"
     "2. Bạn chọn tác vụ nào chạy tiếp bằng cách nào — và cách ấy mất bao lâu, có phụ thuộc số "
     "tác vụ không.\n"
     "3. Chuyển ngữ cảnh: bạn lưu những thanh ghi nào, lưu vào đâu, và **bạn phân biệt khung "
     "có số thực với khung thường bằng cách nào**.\n"
     "4. Chỗ nào trong nhân **không được bị ngắt chen vào**, và bạn chặn bằng gì.\n\n"
     "Mình không đủ trình để soát từng dòng hợp ngữ của bạn. Nên mình dựa vào chỗ này: nếu bạn "
     "giải thích được bốn điều trên một cách nhất quán thì mình duyệt cho viết.",
     2400, 2, False),

    ("Nhân: viết và tự kiểm trên máy",
     "Mình duyệt thiết kế. Bạn viết nhân đi.\n\n"
     "Viết xong, mình cần bạn **tự kiểm trên máy trước khi nghĩ tới bo**. Bạn chọn cách kiểm, "
     "nhưng phải trả lời được: làm sao biết bộ lập lịch **thật sự chuyển** giữa hai tác vụ, chứ "
     "không phải chỉ chạy một tác vụ rồi báo xong?\n\n"
     "Và nhớ hai chỗ ở mục 7.5 tài liệu: tệp kiểm **đừng chép lại logic** của nhân, và mốc so "
     "sánh **đừng lấy từ đầu ra của chính nhân**.",
     3600, 2, False),

    ("Nhân: hàng đợi và trễ, có thời hạn",
     "Giờ phần truyền tin. Bạn viết hàng đợi tĩnh và hàm trễ theo mục 4.3 và 4.4.\n\n"
     "Ba câu mình cần trả lời:\n\n"
     "1. Một tác vụ đang chờ hàng đợi thì nó **có chiếm CPU không**? Bạn chứng minh bằng gì?\n"
     "2. Hết thời hạn mà không có tin thì phân biệt với *nhận được tin* bằng cách nào?\n"
     "3. Hàng đợi tĩnh thì **tốn bao nhiêu RAM**, biết trước lúc dịch được không?",
     2400, 2, False),

    ("Bài kiểm có biết báo lỗi không",
     "Bài kiểm của bạn xanh. Nhưng xanh chưa nói gì tới khi mình biết **cơ chế nào làm nó "
     "xanh**.\n\n"
     "Bạn tự phá mã nhân rồi chạy lại bài kiểm, mỗi lần một dòng, rồi khôi phục. Mình muốn thấy "
     "ít nhất bốn lần phá, và bạn tự chọn phá chỗ nào — nhưng nên nhắm vào chỗ **nếu sai thì "
     "treo**: thứ tự lưu thanh ghi, giá trị trả về khỏi ngắt, chọn tác vụ ưu tiên cao, và đếm "
     "nhịp.\n\n"
     "Ca nào bài kiểm **không kêu** thì nói rõ ra. Đó là phát hiện quan trọng nhất của bước "
     "này, và nói ra thì đáng tin hơn một bảng toàn màu xanh.",
     2400, 2, False),

    # ------------------------- 3 · SÁU TÁC VỤ VÀ THAY FreeRTOS
    # Chèn sau khi NGƯỜI tự kiểm claim điểm mù: phá EXC_RETURN thành 0 mà cả 4 ca vẫn xanh.
    # Tác tử nói đúng về chỗ bộ kiểm của nó không với tới — nên chỗ ấy thành việc.
    ("Điểm mù bạn nêu: mình tự kiểm, và nó là thật",
     "Mình tự phá mã của bạn để kiểm lại điều bạn nói, không nhận qua lời. Đổi "
     "`0xFFFFFFFDU` thành `0x00000000U` trong `control_rtos.c` rồi dịch lại bài kiểm: **cả 4 "
     "ca vẫn xanh**. Bạn nói đúng.\n\n"
     "Mình cũng ghi nhận hai chỗ bạn làm đúng kỷ luật mà mình đã dặn ở mục 7.5:\n\n"
     "- `test_rtos.c` nạp `#include \"../firmware/control_rtos.c\"` — **dịch thẳng mã sản "
     "phẩm**, không chép lại logic. Nên phá mã sản phẩm thì bài kiểm thấy, và hai ca số 3 số 4 "
     "đỏ ngay khi sai một dòng.\n"
     "- Bạn **tự kê hai ca không bắt được** thay vì đưa mình một bảng 4/4 xanh. Nếu bạn im thì "
     "mình đã tin bộ kiểm ấy canh được cả khung ngăn xếp.\n\n"
     "Nhưng giờ nó thành việc phải giải, vì đúng hai chỗ không ai canh lại là hai chỗ **sai thì "
     "treo ngay chu kỳ đầu**: bố cục khung ngăn xếp, và `EXC_RETURN`.\n\n"
     "Mình không đòi bạn phải canh được chúng trên máy — có thể không canh được thật. Mình đòi "
     "bạn **trả lời rõ một trong hai**:\n\n"
     "**a ·** Có cách nào canh được trên máy không? Mình nghĩ tới hướng *dựng một khung ngăn "
     "xếp giả rồi kiểm từng ô theo đúng thứ tự mà lõi Cortex-M4 quy định*, và hướng *so giá trị "
     "`EXC_RETURN` với bảng giá trị hợp lệ chứ không để nó là số tuỳ ý*. Nhưng mình là sinh "
     "viên, mình không chắc hai hướng ấy có đo được gì thật hay chỉ đo lại chính hằng số.\n\n"
     "**b ·** Nếu không canh được thì nói thẳng, và cho mình biết **cái gì sẽ bắt chúng**: dấu "
     "hiệu nào trên bo cho thấy đúng, dấu hiệu nào cho thấy sai, và mình nhìn vào đâu.\n\n"
     "Chọn hướng nào cũng được, nhưng đừng để hai chỗ ấy không có ai canh mà cũng không ai "
     "biết.", 2400, 3, False),

    ("Chuyển ngữ cảnh bằng hợp ngữ, và cách tự kiểm nó",
     "Giờ phần hợp ngữ. Bạn viết `PendSV_Handler` theo thiết kế đã duyệt.\n\n"
     "Mình cần bạn nói kèm ba điều, vì mình không đọc được hợp ngữ đủ chắc để tự soát:\n\n"
     "1. Hàm này **không được** để trình biên dịch tự thêm mã vào đầu và cuối. Bạn bảo đảm điều "
     "đó bằng cách nào, và làm sao mình kiểm lại được?\n"
     "2. Bạn đọc và ghi `PSP` ở chỗ nào, và vì sao phải là `PSP` chứ không phải `MSP`?\n"
     "3. Khi tác vụ có dùng số thực, khung ngăn xếp dài hơn. Bạn **đọc mã máy sinh ra** để xác "
     "nhận điều bạn viết là điều trình biên dịch tạo ra — đừng chỉ đọc mã nguồn của chính bạn.\n\n"
     "Chỗ thứ 3 mình nhấn vì ở việc trước mình vấp đúng kiểu ấy: tệp ghi một đằng, mã máy làm "
     "một nẻo, và phải mở `objdump` ra mới thấy.",
     3600, 3, False),

    ("Sáu tác vụ, và thay FreeRTOS",
     "Nhân xong thì đưa nó vào sản phẩm. Mình kiểm `mach.bin` hiện tại: **132 byte**, đúng bằng "
     "bộ xương rỗng — tức nhân 301 dòng của bạn **chưa có trong ảnh**, và `main.c` vẫn 6 dòng. "
     "Mình nói ra để chắc hai ta cùng biết vạch xuất phát.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Viết sáu tác vụ theo bảng mục 5 tài liệu. Bạn tự xếp ưu tiên và **nói lý do** — "
     "nhớ rằng việc quét nút chạy mỗi 30 ms có thể chen vào giữa việc khác.\n\n"
     "**2 ·** Mang màn hình và cảm ứng vào. Phần này bản cũ dùng thư viện phần cứng của nhà sản "
     "xuất; bạn tự quyết dùng lại hay viết lấy, và nói lý do.\n\n"
     "**3 ·** Rồi dịch, và báo mình **ba con số** `.text` `.data` `.bss`, cùng **danh sách tệp "
     "thật sự vào ảnh**. Điều kiện số 3 của mình đòi mọi tệp đều vào — nếu có tệp nào không vào "
     "thì đó là chỗ phải nói, không phải chỗ bỏ qua.\n\n"
     "**4 ·** Và kiểm điều kiện số 1: **không còn một ký hiệu FreeRTOS nào trong ảnh**. Đọc "
     "bảng ký hiệu của ảnh, đừng grep mã nguồn — hai thứ đó trả lời hai câu khác nhau.\n\n"
     "Chưa nạp bo. Mình sẽ nói khi tới lúc.",
     3600, 3, False),

    ("Một con số nhỏ bất thường không phải tin tốt",
     "Trước khi ta nghĩ tới bo, mình muốn bạn tự soát một chuyện.\n\n"
     "Ở một phiên trước của chính việc này, có lượt báo *biên dịch xong* với ảnh ra **1 416 "
     "byte** — không một ký hiệu màn hình, giao diện hay cảm ứng nào, trong khi dự án có 15 tệp "
     "mã. Đường đi tới đó là: hai lần dịch đỏ, lần thứ ba **bỏ bớt đầu vào** thì xanh, rồi báo "
     "xong. Đúng về lời gọi, sai về việc.\n\n"
     "Mình kể chuyện ấy không phải để trách — nó là lỗi của sản phẩm EIDE, vì lúc đó "
     "`build.compile` không nói nó đã dịch những tệp nào. Mình kể vì **mình muốn bạn tự kiểm "
     "mình đang không ở trong đúng tình huống ấy**.\n\n"
     "Ba câu:\n\n"
     "1. Ảnh của bạn hiện bao nhiêu byte, và con số ấy **hợp lý với bao nhiêu dòng mã**? Bạn "
     "lập luận cho mình.\n"
     "2. Có tệp nào trong `firmware/` **không** vào ảnh? Nếu có, tệp nào và vì sao?\n"
     "3. Trong quá trình dịch, có lần nào bạn **thu hẹp đầu vào** để qua được không? Nếu có thì "
     "nói ra — mình cần biết, và mình không coi đó là lỗi nếu bạn nói.",
     2400, 3, False),

    # Chèn sau khi tác tử TỰ NHẬN đã thu hẹp việc. Người quyết chỗ ranh giới: driver màn hình
    # không phải thứ đang được đo, nhân mới là. Nói rõ lý do để lượt sau không phải đoán lại.
    ("Mình quyết ranh giới: driver được lấy, nhân phải tự viết",
     "Bạn tự nhận đã thu hẹp việc, và bạn nhận trước khi mình phải truy. Mình ghi nhận chỗ đó, "
     "vì nó là chỗ khó nói nhất trong sáu chỗ mình liệt ở mục 7.2 tài liệu.\n\n"
     "Mình cũng kiểm lại mã để chắc bạn mô tả đúng, và bạn đúng — có một chi tiết nhỏ bạn nói "
     "còn **nhẹ hơn** thực tế: `touch_hardware_read()` không chỉ trả `false`, nó còn có một "
     "nhánh trả về điểm giả `(400, 240)`. Nhánh ấy **không tới được** vì "
     "`touch_detected_count` chỉ được gán 0 và không nơi nào tăng. Nên stub của bạn trung thực, "
     "không cho dương tính giả. Nhưng nhánh chết ấy thì dọn đi, cùng họ với chuyện mình gặp ở "
     "việc trước: mã mô tả một việc mà không gì dùng kết quả.\n\n"
     "**Giờ mình quyết một ranh giới, và nói lý do để lượt sau bạn không phải đoán lại.**\n\n"
     "Thứ đang được đo trong việc này là **nhân thời gian thực**, không phải driver màn hình. "
     "Bản cũ cũng không tự viết driver — nó gọi thư viện của ST (`stm32469i_discovery_lcd.h`, "
     "`..._sdram.h`). Bắt bạn viết lại chuỗi khởi tạo DSI, D-PHY, LTDC và FMC từ thanh ghi thì "
     "là một đề bài khác, và nó sẽ chiếm hết chỗ của đề bài thật.\n\n"
     "Nên:\n\n"
     "**Được lấy từ ngoài:** driver màn hình, SDRAM, và cảm ứng. Bạn dùng `code.vendor_fetch` "
     "lấy thư viện của ST cho kit STM32F469I-DISCO.\n\n"
     "**Phải tự viết, không được lấy:** toàn bộ nhân — lập lịch, chuyển ngữ cảnh, hàng đợi, "
     "trễ. Điều kiện số 1 vẫn giữ: **không một ký hiệu FreeRTOS nào trong ảnh**.\n\n"
     "**Và phải nói rõ tệp nào từ đâu.** Cuối việc mình cần một bảng: tệp nào bạn viết, tệp nào "
     "lấy của ST, bao nhiêu dòng mỗi loại. Báo cáo của mình sẽ nói *Agent tự viết N dòng*, nên "
     "con số N ấy phải sạch.\n\n"
     "Việc của bạn trong lượt này:\n\n"
     "**1 ·** Dọn nhánh chết trong `touch_hardware_read()`.\n\n"
     "**2 ·** Lấy thư viện ST về, rồi nối màn hình và cảm ứng vào thật.\n\n"
     "**3 ·** Dịch, rồi báo mình `.text` `.data` `.bss` và **danh sách tệp vào ảnh**. Lần này "
     "con số phải **hợp lý với một hệ có màn hình** — bạn tự nói ở lượt trước là tối thiểu "
     "15 KB, nên nếu nó vẫn quanh 1,5 KB thì ta còn đang ở chỗ cũ.\n\n"
     "**4 ·** Nếu lấy thư viện về mà vướng — thiếu tệp, thiếu CMSIS, xung đột — thì **nói ra "
     "ngay**, đừng viết hàm rỗng cho dịch qua. Mình thà nghe vướng còn hơn nhận một ảnh dịch "
     "xanh mà rỗng.",
     3600, 3, False),

    # Chèn 04/10. NGƯỜI tự phá build: xoá 3 tệp kèm mã băm vì nhìn hình dạng TÊN, không mở
    # ra đọc. Chúng chứa bản driver V1 thật; 3 tệp cùng gốc tên chỉ là dòng trỏ.
    # Lần thứ hai cùng một lỗi trong ngày — lần đầu đè mất 22 ô dữ liệu ở việc FPGA.
    ("Mình xoá mất driver của bạn — và bản vá EIDE làm chỗ này sạch hơn",
     "Mình phải nói ngay: **mình vừa phá build của bạn.**\n\n"
     "Mình thấy trong `firmware/` có các tệp kèm mã băm — `ft6x06-ac138c52.c`, "
     "`nt35510-6b3d5f5f.c`, `otm8009a-1bf0e24c.c` — và mình xoá, vì mình cho rằng đó là bản "
     "trùng do công cụ lấy mã sinh ra. Mình **không mở chúng ra đọc.**\n\n"
     "Mở ra thì mới thấy: `ft6x06.c` của bạn chỉ có một dòng *driver implementation được biên "
     "dịch từ ft6x06-ac138c52.c*. Tức ba tệp mình xoá **chính là bản V1 thật**, còn ba tệp "
     "cùng gốc tên chỉ là dòng trỏ. Mình xoá theo hình dạng của cái tên, không theo nội dung. "
     "Đây là lần thứ hai hôm nay mình mắc đúng lỗi ấy — lần trước mình đè mất 22 ô dữ liệu đo "
     "của bạn ở việc FPGA vì đặt tên tệp theo thứ mình *tưởng* đang đo.\n\n"
     "Nhưng chuyện này hoá ra có ích, vì nó chỉ ra một lỗi của EIDE mà **mình đã vá**:\n\n"
     "Bạn lấy V2 từ nhánh `main` trước, rồi lấy V1 theo tag. Cùng tên, khác nội dung. EIDE "
     "lúc ấy **giữ cả hai bản** — chính sách đó đúng cho tài liệu (một dữ kiện đã trích dẫn "
     "tới bản cũ thì bản ấy phải còn kiểm lại được), nhưng **sai cho mã nguồn trong thư mục "
     "được biên dịch**: mình đọc hiện vật `build:firmware` và thấy trong 45 tệp `.c` có cả "
     "`ft6x06.c` lẫn `ft6x06-ac138c52.c`, cả `nt35510.c` lẫn bản băm, cả `otm8009a.c` lẫn bản "
     "băm. Lượt ấy link được chỉ vì hai bản đặt tên hàm khác nhau.\n\n"
     "Mình đã vá: đường lấy **mã nguồn** nay **ghi đè và nói ra**, còn đường lấy **tài liệu** "
     "giữ nguyên cách cũ. Nên giờ lấy lại V1 theo tag sẽ ghi thẳng vào `ft6x06.c` — **không "
     "còn tệp kèm mã băm, và bạn không cần tệp trỏ nữa.**\n\n"
     "Mình cũng vá một lỗi thứ hai mà bạn có thể đã thấy: ba tệp `eide-thu-nhanh*` nằm trong "
     "`firmware/` là tệp EIDE tải thử để dò nhánh rồi dọn không sạch. Mình đã xoá và chặn lại.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Lấy lại ba driver V1 theo đúng tag bạn đã xác định (`stm32-ft6x06@v1.1.1`, "
     "`stm32-otm8009a@v1.0.7`, `stm32-nt35510@v1.0.3`). Lần này kiểm giúp mình xem **có còn "
     "tệp kèm mã băm nào không** — nếu còn thì bản vá của mình chưa tới chỗ này, và mình cần "
     "biết.\n\n"
     "**2 ·** Bỏ ba tệp trỏ, để `ft6x06.c` `otm8009a.c` `nt35510.c` là mã thật.\n\n"
     "**3 ·** Dịch lại, báo mình `.text` `.data` `.bss`, và **số tệp `.c` trong dòng lệnh "
     "dịch** — mình muốn con số ấy không còn cặp nào trùng gốc tên.\n\n"
     "**4 ·** Rồi trả lời hai chỗ mình cố ý để trống trong tài liệu, vì giờ là lúc cần chúng:\n"
     "   - **tần số I2C**: ở 180 MHz thì bao nhiêu là đúng, bạn đo hay bạn tra ở đâu?\n"
     "   - **ngăn xếp mỗi tác vụ**: bạn chọn bao nhiêu, và **đo** bằng cách nào chứ đừng đoán. "
     "Tác vụ màn hình gọi cả chuỗi BSP nên mình đoán nó cần nhiều hơn, nhưng mình chỉ đoán.",
     3600, 3, False),

    # Chèn 04/10. Tác tử phân tích ĐÚNG rồi viết mã NGƯỢC với phân tích của chính nó: nó nói
    # tác vụ màn hình cấp 128 word "chắc chắn sẽ tràn stack", mã thì cấp đúng 128 word.
    # Và triệu chứng của tràn stack ở tác vụ khởi tạo LCD là "màn hình đen" — đúng triệu
    # chứng của lỗi thứ hai trong phiên cũ.
    ("Lời bạn nói ngược mã bạn viết, và đo thì phải CHẠY",
     "Bản vá của mình tới đúng chỗ, mình kiểm rồi: **0 tệp kèm mã băm, 0 tệp `eide-thu-nhanh`, "
     "42 tệp `.c` dịch và 0 cặp trùng gốc tên** (trước là 45 tệp với 3 cặp). Ba driver nay là "
     "mã thật: 14 781 / 18 572 / 10 118 byte. Và ảnh dựng lại ra **đúng 26 336 byte như "
     "trước** — cùng mã, chỉ khác tên tệp, nên việc mình xoá đã phục hồi sạch.\n\n"
     "Phần I2C bạn trả lời được: 400 kHz Fast-Mode ở `PCLK1 = 45 MHz`, kèm ràng buộc "
     "`T_high ≥ 600 ns` và `T_low ≥ 1300 ns`. Mình nhận.\n\n"
     "Nhưng phần ngăn xếp thì có hai chỗ, và chỗ đầu là chỗ nặng.\n\n"
     "**1 · Bạn phân tích đúng rồi viết mã ngược với phân tích của chính bạn.**\n\n"
     "Bạn viết: *tác vụ màn hình cần tối thiểu **512 word**, cấp 128 word **chắc chắn sẽ tràn "
     "stack***. Mình mở `main.c` ra đọc:\n\n"
     "```c\n#define TASK_STACK_WORDS 128\n...\n"
     "rtos_task_create(&tcb_task6, \"DisplayUI\", task_display_touch, 0, 10, stack_task6, "
     "TASK_STACK_WORDS);\n```\n\n"
     "Cả sáu tác vụ đều 128 word, kể cả tác vụ màn hình. Nên theo chính lời bạn, bản này sẽ "
     "tràn ngăn xếp ở tác vụ khởi tạo LCD.\n\n"
     "Mình chú ý chỗ này vì **triệu chứng của tràn ngăn xếp trong tác vụ khởi tạo LCD là màn "
     "hình đen** — mà màn hình đen đúng là lỗi thứ hai của phiên trước việc này, và lần ấy "
     "nguyên nhân thật lại là chuyện khác. Nếu ta nạp bản này rồi thấy màn đen, ta sẽ có **hai "
     "nguyên nhân khả dĩ cùng cho một triệu chứng**, và mình sẽ không biết đang xem cái nào.\n\n"
     "Nên sửa trước khi nạp. Đây không phải chuyện khó — chỉ là làm cho mã khớp với điều bạn "
     "đã nói.\n\n"
     "**2 · Và \"đo\" thì phải chạy, không phải mô tả cách chạy.**\n\n"
     "Bạn mô tả hai cách rất đúng: sơn ngăn xếp bằng `0xA5A5A5A5` rồi tìm mức nước, và "
     "`-fstack-usage` để dò cây gọi hàm. Nhưng mình grep `control_rtos.c`: **không có "
     "`0xA5A5A5A5` nào**. Nên hai con số 128 và 512 hiện vẫn là **tầng ĐỒNG** — bạn suy ra, "
     "chưa đo.\n\n"
     "Tài liệu mình viết là *bạn tự chọn, và **đo** chứ đừng đoán*. Mình giữ câu đó.\n\n"
     "Việc của bạn:\n\n"
     "**a ·** Cho mỗi tác vụ một kích thước riêng theo chính phân tích của bạn, đừng dùng một "
     "hằng số chung.\n\n"
     "**b ·** **Cài sơn ngăn xếp thật** trong `rtos_task_create`, và một hàm đọc mức nước. "
     "Rồi cho tác vụ theo dõi in mức nước của cả sáu tác vụ ra — để lúc chạy trên bo mình "
     "thấy được số thật, không phải số bạn suy.\n\n"
     "**c ·** Chạy bài kiểm trên máy với sơn ấy, và cho mình xem **mức nước đo được** của ít "
     "nhất hai tác vụ. Trên máy thì chuỗi BSP không chạy nên con số sẽ thấp hơn thực tế — "
     "**nói rõ điều đó** chứ đừng để mình tưởng đã đo xong.\n\n"
     "**d ·** Rồi dịch lại và báo `.text` `.data` `.bss`. Mình chờ `.bss` tăng, vì ngăn xếp "
     "to hơn. Nếu nó **không** tăng thì một trong hai ta đang nhìn sai, và ta phải tìm ra "
     "trước khi nạp.",
     3600, 3, False),

    # ---------------------------------------- 4 · CHẠY TRÊN BO THẬT
    ("Soát danh mục nghiệm thu trước khi nạp",
     "Ba việc bạn làm xong và mình kiểm lại hết bằng máy, không nhận qua lời:\n\n"
     "| phép kiểm | kết quả |\n|---|---|\n"
     "| ngăn xếp riêng từng tác vụ | 512 word cho màn hình, 128 cho năm tác vụ nhẹ |\n"
     "| `.bss` tăng như mình chờ | 4 288 → **5 872** byte, +396 word |\n"
     "| sơn ngăn xếp có thật chạy | `control_rtos.c:89-91`, sơn kín trước khi dựng khung |\n"
     "| mức nước đo được | T1 64w còn 47 / dùng 17 · T2 128w còn 111 / dùng 17 |\n"
     "| bài kiểm | 5/5, mình tự dịch và tự chạy lại |\n\n"
     "Con số 17 word cũng tự nhất quán với điều bạn nói: 8 word khung phần cứng cộng 9 word "
     "phần mềm lưu thêm. Và ca thứ 5 của bạn có một phép kiểm độ nhạy cho **chính phép đo** — "
     "ghi đè 1 word thì mức nước giảm đúng 47 xuống 46. Mình thích chỗ đó: một phép đo không "
     "tự chứng minh được nó đang đo thì cũng chỉ là một con số.\n\n"
     "Giờ trước khi nạp, mình muốn bạn **soát lại cả 10 dòng nghiệm thu ở mục 6 tài liệu** và "
     "tự kê cho mình, mỗi dòng một trong ba trạng thái:\n\n"
     "- **đã đạt** — kèm số đo và chỗ lấy\n"
     "- **chưa đo được trên máy** — nêu rõ phải nhìn gì trên bo, và mình nhìn vào đâu\n"
     "- **chưa làm** — nói thẳng\n\n"
     "Mình cần bảng này **trước** khi nạp, vì sau khi nạp thì mỗi quan sát sẽ kéo ta đi theo "
     "nó, và tiêu chí nêu sau khi thấy kết quả thì không còn là tiêu chí.\n\n"
     "Và nói luôn cho mình biết: trong 10 dòng ấy, dòng nào bạn cho là **dễ sai nhất** khi ra "
     "bo, và vì sao.",
     2400, 4, False),

    # Chèn 04/10. Tiêu chí số 3 của NGƯỜI tự khuyến khích làm sai, và tác tử làm đúng theo
    # cái tiêu chí sai ấy — còn ghi cả động cơ vào chú thích. Sửa tiêu chí, không trách tác tử.
    ("Tiêu chí số 3 mình viết sai, và một con số bạn báo lệch",
     "Bảng nghiệm thu của bạn mình nhận: ba dòng VÀNG có số đo, bảy dòng ghi rõ **chưa đo được "
     "trên máy** kèm *nhìn vào đâu*. Đó là bảng dùng được — và bạn trả lời luôn câu mình hỏi "
     "thêm về dòng dễ sai nhất.\n\n"
     "Hai chỗ, và chỗ thứ hai là lỗi của mình.\n\n"
     "**1 · Một con số bạn báo lệch, ở một dòng bạn tự khai VÀNG.** Bạn viết *toàn bộ **38** "
     "tệp `.c` của dự án đều có mặt trong lệnh liên kết*. Mình mở hiện vật `build:firmware` ra "
     "đếm: **42**. Tổng Flash 26 576 byte thì bạn khớp đúng từng chữ số, nên bạn có đọc hiện "
     "vật thật — chỉ con số đếm là sai.\n\n"
     "Mình nêu vì VÀNG nghĩa là *tôi đo, có hiện vật*. Một con số VÀNG mà lệch thì nguy hơn "
     "một con số ĐỒNG, vì mình thôi không kiểm lại nữa. Sửa lại cho đúng, và nói cho mình biết "
     "**bạn đếm bằng cách nào** để lần sau nó không lệch.\n\n"
     "**2 · Tiêu chí số 3 của mình viết sai, và bạn đã làm đúng theo cái sai ấy.**\n\n"
     "Mình mở `firmware/rtos.c` và thấy chú thích của chính bạn:\n\n"
     "> *Tệp này chứa mã thực thi để đảm bảo mọi tệp mã nguồn trong dự án đều được biên dịch "
     "vào ảnh nhị phân cuối cùng (Điều kiện số 3).*\n\n"
     "Tức bạn viết mã **để tiêu chí của mình đạt**, không vì sản phẩm cần. Và bạn ghi cả động "
     "cơ ra — mình cảm ơn chỗ đó, vì nếu bạn im thì mình đã đếm 47 dòng ấy vào con số *Agent tự "
     "viết N dòng* trong báo cáo.\n\n"
     "Nhưng lỗi gốc ở mình: mình viết *mọi tệp mã nguồn đều vào được ảnh*, mà một tệp rỗng thì "
     "không vào được ảnh — nên cách dễ nhất để đạt là **viết thêm mã cho tệp rỗng**. Tiêu chí "
     "của mình tự nó khuyến khích làm sai.\n\n"
     "Mình đã sửa tài liệu, thêm **mục 6.2**. Điều mình thật sự muốn canh là chuyện khác: ở "
     "phiên trước của chính việc này, một lượt báo *biên dịch xong* với ảnh 1 416 byte vì đầu "
     "vào bị thu hẹp dần — driver màn hình, giao diện, cảm ứng **rơi ra ngoài mà không ai được "
     "báo**. Điều kiện số 3 nay đọc là: *nêu trước danh sách tệp bạn trông đợi, đối chiếu sau "
     "khi dịch, thiếu thì nói ra kèm lý do*. Và thêm một câu: **tệp nào không có việc gì để làm "
     "thì xoá đi.**\n\n"
     "Việc của bạn:\n\n"
     "**a ·** Đọc lại mục 6.2, rồi xét `rtos.c`: trong 47 dòng ấy, dòng nào sản phẩm **thật sự "
     "cần** (mình nghĩ `rtos_start` thì cần), dòng nào chỉ để đạt tiêu chí? Giữ phần cần, bỏ "
     "phần không, và nếu còn tệp nào rỗng thì xoá.\n\n"
     "**b ·** Nêu cho mình **danh sách tệp bạn trông đợi có trong ảnh**, mỗi tệp một lý do "
     "ngắn. Rồi đối chiếu với thứ thật sự vào ảnh và báo chỗ lệch.\n\n"
     "**c ·** Sửa con số 38, và cho mình **bảng tệp nào bạn viết / tệp nào của ST, bao nhiêu "
     "dòng mỗi loại** — con số *Agent tự viết* trong báo cáo lấy từ bảng ấy, nên nó phải sạch.",
     3600, 4, False),

    ("[cần người] Cắm bo rồi nạp",
     "Mình đã cắm kit STM32F469I-DISCO vào máy. `st-info --probe` thấy: ST-Link `V2J35S26`, "
     "`chipid 0x434`, `dev-type STM32F46x_F47x`, flash `2 097 152` byte.\n\n"
     "**Một chỗ lệch mình muốn bạn gỡ trước khi tin bất cứ số đo nào sau đó:** công cụ báo "
     "`sram: 262144` tức **256 KB**, còn linker script của ta đặt **320 KB** và con trỏ ngăn "
     "xếp ban đầu trong ảnh là `0x20050000` (mình đọc `.isr_vector`, từ đầu là `00 00 05 20`). "
     "Nếu RAM thật chỉ tới `0x20040000` thì đỉnh ngăn xếp nằm ngoài bộ nhớ và chip sẽ lỗi ngay "
     "lệnh đầu — mà triệu chứng sẽ là *nạp xong không thấy gì*, giống hệt chục nguyên nhân "
     "khác.\n\n"
     "Mình đã thử tự gỡ và **thử sai**: mình dùng `st-flash write` để ghi một mẫu vào "
     "`0x2004FF00` rồi đọc lại, nhưng công cụ ấy ghi Flash chứ không ghi SRAM, nên đọc lại vẫn "
     "là dữ liệu cũ. Phép thử của mình không đo được gì — mình nói ra để bạn đừng dựa vào nó.\n\n"
     "Thứ mình có: firmware của phiên trước **chạy được trên đúng bo này** với cùng linker "
     "script 320 KB. Mình nghiêng về 320 KB đúng, và `256 KB` là số chung của dòng F46x/F47x. "
     "Nhưng đó là suy luận, nên bạn **đo bằng thanh ghi** rồi chốt thành dữ kiện.\n\n"
     "Bạn làm theo thứ tự này, và ba chỗ dưới là ba chỗ đã cắn mình ở việc trước nên mình nêu "
     "trước:\n\n"
     "**1 ·** `target.detect` xem máy có thấy bo không, và **đối chiếu mã chip** với thứ ta "
     "đang dịch cho. Nếu lệch thì dừng, đừng tìm đường vòng.\n\n"
     "**2 ·** Nạp. Mình sẽ duyệt cổng.\n\n"
     "**3 ·** Sau khi nạp, **tự so mốc nạp với mốc dựng** rồi mới nói về kết quả. Ở việc trước "
     "có một lượt báo *bắt được 32 dòng từ bo, lệch 0 %* mà hoá ra đọc cổng **92 giây trước "
     "khi bitstream tồn tại**. Mốc thời gian trong sổ cái nói ra điều đó, lời tường thuật thì "
     "không.\n\n"
     "**4 ·** Rồi đọc trạng thái chip: có HardFault không, bộ lập lịch có luân chuyển không, "
     "và **mức nước ngăn xếp của cả sáu tác vụ** — đây là lần đầu con số ấy được đo trong môi "
     "trường có chuỗi BSP thật, nên nó mới là con số mình cần.\n\n"
     "Xong thì báo mình nhìn gì trên bo. Mình sẽ nói lại đúng điều mình thấy, không suy "
     "nguyên nhân.",
     3600, 4, True),

    # Chèn 04/10. Người quan sát: đèn tối, màn tối. Người đọc bảng vector trong ảnh và tìm ra
    # nguyên nhân gốc: ô SysTick trỏ sang Default_Handler, và rtos_tick() không ai gọi.
    # Lần thứ năm trong phiên này gặp "cơ chế có sẵn, đường dẫn tới nó đứt" — lần đầu ở mã
    # của chính tác tử, không phải ở EIDE.
    ("Mình nhìn bo: tối cả hai. Và mình tìm ra chỗ đứt",
     "Mình nhìn bo và trả lời đúng hai câu bạn hỏi: **đèn LED tối thui, màn LCD tối thui.** "
     "Không đèn nào nháy.\n\n"
     "Rồi mình mở bảng vector trong ảnh ra đọc, vì `CFSR = 0` và `HFSR = 0` nghĩa là chip "
     "không lỗi — nó **đang chờ một thứ không bao giờ tới**. Đây là thứ mình thấy:\n\n"
     "| ô vector | trỏ tới | |\n|---|---|---|\n"
     "| 14 · PendSV | `0x080003e1` → `PendSV_Handler` | **đúng** |\n"
     "| 15 · SysTick | `0x08000ff7` → `Default_Handler` | **sai** |\n\n"
     "`Default_Handler` trong `startup.c` là `while (1) {}`. Và mình grep cả thư mục:\n\n"
     "```\n$ grep -rn \"rtos_tick(\" firmware/\n"
     "firmware/control_rtos.c:158:RTOS_WEAK void rtos_tick(void) {\n"
     "firmware/rtos.h:63:void rtos_tick(void);\n```\n\n"
     "Chỉ có **định nghĩa** và **khai báo**. **Không ai gọi `rtos_tick()`.** Không có "
     "`SysTick_Handler` nào trong nhân — chỉ có bí danh yếu trỏ sang `Default_Handler` ở "
     "`startup.c:25`.\n\n"
     "Nên chuỗi là thế này, và nó giải thích **cả hai triệu chứng bằng một nguyên nhân**:\n\n"
     "1. `rtos_start()` gọi `rtos_yield()`, PendSV nổ, chuyển sang `ButtonScan` — phần này "
     "**chạy đúng**, bạn làm đúng chỗ khó nhất.\n"
     "2. `ButtonScan` gọi `rtos_delay_ms(30)` rồi chặn, chờ nhịp đánh thức.\n"
     "3. **Nhịp không bao giờ tới.** `delay_ticks` không giảm.\n"
     "4. Cả sáu tác vụ lần lượt chặn ở lần trễ đầu tiên của mình → đèn tối.\n"
     "5. Tác vụ màn hình chặn **ngay trong `HAL_Delay` giữa chuỗi khởi tạo DSI**, vì "
     "`HAL_Delay` của bạn nối vào `rtos_delay_ms` → màn tối.\n"
     "6. Không tác vụ nào sẵn sàng → `PC` rơi về `while(1)` của `main`. Đúng chỗ bạn đọc được.\n\n"
     "**Và đây đúng là điểm mù bạn đã tự khai.** Bài kiểm trên máy **gọi thẳng `rtos_tick()`**, "
     "nên nó kiểm được *logic của nhịp* mà không bao giờ kiểm *có cái gì gọi nhịp hay không*. "
     "Hai câu hỏi khác nhau, và bộ kiểm chỉ trả lời câu thứ nhất.\n\n"
     "Mình gặp đúng dạng lỗi này **năm lần** trong hai ngày, và đây là lần đầu nó ở trong mã "
     "của bạn chứ không ở trong EIDE: **cơ chế có sẵn, đường dẫn tới nó đứt.** Hàm nhịp viết "
     "đúng, nằm đúng chỗ, và không ai gọi.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Nối nhịp vào nhân. Bạn tự quyết cách, nhưng phải trả lời: ai cấu hình SysTick, "
     "đặt bao nhiêu để ra đúng 1 000 Hz ở 180 MHz, và **ưu tiên ngắt của SysTick so với "
     "PendSV** phải thế nào để một cú chuyển ngữ cảnh không bị nhịp chen vào giữa.\n\n"
     "**2 ·** Rồi thêm một phép kiểm **bắt được chính lỗi này**. Bài kiểm hiện tại gọi "
     "`rtos_tick()` nên nó mù. Mình nghĩ tới hướng *đọc ô vector trong ảnh đã dịch rồi so với "
     "địa chỉ hàm thật* — tức kiểm **ảnh**, không kiểm mã nguồn. Nhưng bạn thấy cách khác tốt "
     "hơn thì làm.\n\n"
     "**3 ·** Và nhân lúc này: soát **cả 16 ô vector** xem còn ô nào trỏ sai chỗ nữa không. "
     "Mình chỉ đọc ba ô, biết đâu còn ô khác.\n\n"
     "**4 ·** Dựng lại, nạp lại, rồi báo mình nhìn gì. Nhớ so mốc nạp với mốc dựng trước khi "
     "nói về kết quả.",
     3600, 4, False),

    # Chèn 04/10. Người đọc RCC từ silicon: HSEON=False, SWS=HSI. Không có dòng cấu hình xung
    # nhịp nào trong dự án — tài liệu đã cho sẵn hằng số PLL mà tác tử chưa cài.
    # Và đây cũng là lỗ trong tiêu chí của người: đã thêm điều kiện 3b.
    ("Chip đang chạy 16 MHz, không phải 180 MHz",
     "Vẫn tối cả hai. Nhưng lần này mình đo được chỗ đứt, và nó **không phải** chỗ vừa vá.\n\n"
     "Trước hết: **chỗ vá của bạn đúng.** Mình kiểm trong ảnh — ô vector 15 nay trỏ "
     "`SysTick_Handler` tại `0x08001049`, và mã máy của nó là `push` → `bl HAL_IncTick` → "
     "`b.w rtos_tick`. Đường dẫn đã nối. Mình cũng đọc `uwTick` hai lần, nó **đi thật**: "
     "282 606 → 282 882. Ngắt nổ.\n\n"
     "Nhưng `ready_map` giữ nguyên cả sáu bit `0x001085a0` sau ba giây, và `current_tcb` đứng "
     "im. Nên mình đo nhịp bằng cách đọc `uwTick` cách nhau 10 giây:\n\n"
     "```\n289 026 → 289 936 · Δ = 910 trong ~10 s → ~91 Hz (cần 1 000)\n```\n\n"
     "Chậm **11,25 lần**. Con số ấy chỉ thẳng vào 180/16, nên mình đọc thanh ghi xung nhịp:\n\n"
     "| thanh ghi | giá trị | nghĩa |\n|---|---|---|\n"
     "| `RCC_CR` | `0x00007c83` | **`HSEON = False`**, `PLLON = False` — thạch anh ngoài "
     "**chưa từng được bật** |\n"
     "| `RCC_CFGR` | `0x00000000` | `SWS = 00` → nguồn xung nhịp hệ thống là **HSI 16 MHz** |\n"
     "| SysTick `LOAD` | 179 999 | đúng cho 180 MHz → ở 16 MHz ra **89 Hz** |\n\n"
     "Dự đoán 89 Hz, đo được 91 Hz. Khớp.\n\n"
     "Rồi mình grep cả dự án: **không có một dòng cấu hình xung nhịp nào.** "
     "`hardware_early_init()` chỉ đặt trạng thái đèn và gọi `BSP_LED_Init`. Không `HSEON`, "
     "không `PLLCFGR`, không hàm nào đặt xung nhịp hệ thống.\n\n"
     "Mục 3 tài liệu mình đã cho sẵn `PLLM = 8 · PLLN = 360 · PLLP = ÷2 · PLLQ = 7 · "
     "PLLR = 6`. Nhưng **cho một hằng số không làm nó được cài** — mình nhận phần lỗi ở đây: "
     "mình tưởng đưa hằng số là xong, nên không đặt *xung nhịp thật đạt 180 MHz* thành một "
     "dòng nghiệm thu. Mình vừa thêm **điều kiện 3b** và **mục 6.1b** vào tài liệu.\n\n"
     "Chỗ mình muốn bạn ghi lại làm bài học, vì nó đắt: **giá trị cấu hình không phải phép "
     "đo.** SysTick nạp 179 999 là đúng — nhưng nó chỉ nói *nhịp sẽ là 1 000 Hz NẾU xung nhịp "
     "là 180 MHz*. Đọc con số ấy rồi kết luận nhịp 1 000 Hz là sai. Và hệ chậm 11 lần thì "
     "**không báo lỗi gì**: không fault, không treo, thanh ghi nào cũng trông hợp lý. Một hệ "
     "chậm 11 lần nhìn giống một hệ không chạy.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Cài cấu hình xung nhịp theo mục 3. Nhớ cả những thứ đi kèm mà mình không biết "
     "đủ để liệt: độ trễ đọc Flash ở 180 MHz, chế độ nguồn, bộ chia bus APB. Bạn tra rồi nói "
     "cho mình biết bạn tra ở đâu.\n\n"
     "**2 ·** Và thêm một phép kiểm **bắt được chính lỗi này**: sau khi nạp, đọc `RCC_CFGR` "
     "xác nhận nguồn là PLL, rồi **đo nhịp thật** chứ đừng đọc `LOAD`. Nếu không đo được tự "
     "động thì nói rõ cách mình đo thay.\n\n"
     "**3 ·** Soát xem còn chỗ nào trong dự án **cho hằng số mà không cài** nữa không. Mình "
     "nghi còn, vì tài liệu của mình cho khá nhiều số.\n\n"
     "**4 ·** Dựng, nạp, rồi tự đọc `RCC_CFGR` và nhịp trước khi gọi mình nhìn bo. Lần này "
     "mình muốn thấy số trước khi mình nhìn.",
     3600, 4, False),

    # Chèn 04/10. Người đo trên silicon: nhịp 1003 Hz (xung nhịp đã đúng), nhưng rtos_yield
    # chỉ GÁN current_tcb rồi trả về — không bao giờ đặt PENDSVSET. ICSR=0. Cả dự án không
    # chỗ nào ghi ICSR. Nên PendSV_Handler — phần hợp ngữ khó nhất — là mã không ai tới được.
    # Lần thứ sáu "cơ chế có sẵn, đường dẫn tới nó đứt", và lần này là chỗ nặng nhất.
    ("Xung nhịp đã đúng. Nhưng PendSV chưa chạy lần nào",
     "**Xung nhịp vá xong và mình đo xác nhận:** `HSEON`, `HSERDY`, `PLLON`, `PLLRDY` đều bật, "
     "`SWS = PLL`, và nhịp thật đo được **~1 003 Hz** (đọc `uwTick` cách nhau 10 giây: "
     "255 703 → 265 730). Đúng chỗ bạn sửa.\n\n"
     "Nhưng bo **vẫn tối cả hai**, và mình đo được vì sao. Đọc trạng thái nhân ba lần, cách "
     "nhau 2 giây:\n\n"
     "```\nready_map     = 0x001085a0   (cả sáu bit, KHÔNG đổi)\n"
     "current_tcb   = 0x200001e4   (KHÔNG đổi)\n"
     "mức nước 6 tác vụ = [0, 0, 0, 0, 0, 0]\n```\n\n"
     "Cả sáu bit sẵn sàng còn nguyên nghĩa là **chưa tác vụ nào từng chặn**, tức **chưa tác vụ "
     "nào từng chạy** — vì tác vụ nào cũng gọi `rtos_delay_ms` ngay vòng đầu. Và mức nước toàn "
     "0 nghĩa là tác vụ theo dõi chưa chạy lần nào.\n\n"
     "Nên mình đọc mã máy của `rtos_yield`:\n\n"
     "```\npush  {r3, lr}\nbl    rtos_pick_next_task\ncbz   r0, +0xc\n"
     "ldr   r3, [pc, #4]      @ &current_tcb\nstr   r0, [r3, #0]      @ current_tcb = tác vụ\n"
     "pop   {r3, pc}          @ TRẢ VỀ\n```\n\n"
     "**Nó chỉ gán con trỏ rồi trả về.** Không đặt bit `PENDSVSET`. Mình đọc `SCB_ICSR` trên "
     "chip: `0x00000000` — `PENDSVSET = False`, chưa lần nào được đặt. Và grep cả nhân: "
     "`ICSR`, `PENDSVSET`, `0xE000ED04`, `SCB->` — **không chỗ nào**.\n\n"
     "Nghĩa là `PendSV_Handler` của bạn — phần hợp ngữ khó nhất, viết đúng, nối đúng ô vector "
     "14, ưu tiên đặt đúng (`SHPR3` cho PendSV 240, SysTick 224) — **chưa chạy lần nào.** Mã "
     "không ai tới được.\n\n"
     "**Và đây là đúng điểm mù bạn đã tự khai ở bước 7**, nay có hậu quả đo được. Mình mở "
     "`test_rtos.c` ra xem ca *chuyển ngữ cảnh A→B→A* đo bằng gì:\n\n"
     "```c\nstatic tcb_t *trace[16];\nstatic void record_trace(tcb_t *task) { trace[trace_idx++] "
     "= task; }\nstatic void dummy_task(void *arg) { (void)arg; }\n```\n\n"
     "Nó ghi vết bằng **con trỏ TCB** — tức đo *bộ lập lịch CHỌN tác vụ nào*, không đo *quyền "
     "thực thi có CHUYỂN không*. `dummy_task` thân rỗng và chưa bao giờ được thi hành. Nên ca "
     "ấy xanh đúng, mà nó xanh về một câu hỏi khác câu ta cần.\n\n"
     "Đây là lần thứ **sáu** trong hai ngày mình gặp cùng một dạng — *cơ chế có sẵn, đường dẫn "
     "tới nó đứt* — và là lần nặng nhất, vì thứ bị bỏ quên lại chính là phần bạn làm công phu "
     "nhất.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Cho `rtos_yield()` **thật sự xin chuyển ngữ cảnh** bằng cách đặt `PENDSVSET`. Và "
     "soát `rtos_tick()` nữa: khi một tác vụ hết trễ và thức dậy, có ai xin chuyển không, hay "
     "nó cũng chỉ đổi trạng thái trong bảng?\n\n"
     "**2 ·** Thêm phép kiểm **bắt được chính lỗi này**. Chỗ khó: trên máy không có thanh ghi "
     "SCB nên không chạy được PendSV thật. Hai hướng mình nghĩ tới, bạn chọn hoặc đề xuất "
     "khác:\n"
     "   - **kiểm ảnh đã dịch** — tra trong mã máy xem đường `rtos_yield` có ghi vào "
     "`0xE000ED04` không. Cùng dạng với cách đã bắt được ô vector SysTick, và nó đo **hiện "
     "vật** chứ không đo mã nguồn.\n"
     "   - **cho thanh ghi SCB đi qua một chỗ thay được** để bài kiểm trên máy quan sát. Nhưng "
     "cẩn thận: nếu làm hỏng thì bài kiểm chỉ còn đo cái thay thế, không đo sản phẩm.\n\n"
     "**3 ·** Và soát lại **cả ba phần của nhân** theo đúng câu hỏi này: *mỗi cơ chế mình viết, "
     "có đường nào thật sự gọi tới nó không?* Mình đã gặp sáu lần, nên mình tin còn.\n\n"
     "**4 ·** Dựng, nạp, rồi **tự đọc `ICSR`, `ready_map`, `current_tcb` hai lần cách nhau vài "
     "giây** trước khi gọi mình nhìn bo. Nếu `ready_map` đổi thì bộ lập lịch đã chạy, và lúc "
     "ấy mới đáng để mình nhìn.",
     3600, 4, False),

    # Chèn 04/10. Chuyển ngữ cảnh NAY CHẠY (mức nước có số thật), rồi HardFault với IBUSERR —
    # đúng hai điểm mù tác tử tự khai ở bước 7: bố cục khung ngăn xếp và EXC_RETURN.
    ("Chuyển ngữ cảnh đã chạy, rồi HardFault — đúng hai điểm mù bạn khai",
     "**Bản vá của bạn làm nó chạy.** Bằng chứng không phải lời ai nói: mảng mức nước nay có "
     "số thật, nên tác vụ theo dõi đã thi hành, nên cú chuyển ngữ cảnh đã xảy ra. Đây là **số "
     "đo ngăn xếp đầu tiên trên silicon**:\n\n"
     "| tác vụ | cấp | chưa chạm | đã dùng | |\n|---|---|---|---|---|\n"
     "| LED1 | 128 | 108 | **20** | 16 % |\n| LED2 | 128 | 108 | **20** | 16 % |\n"
     "| Button | 128 | 102 | **26** | 20 % |\n| Queue | 128 | 102 | **26** | 20 % |\n"
     "| Monitor | 128 | 110 | **18** | 14 % |\n| Display | 512 | 447 | **65** | 13 % |\n\n"
     "Chỗ này mình muốn bạn tự đối chiếu: bạn từng viết *cấp 128 word cho tác vụ màn hình "
     "**chắc chắn sẽ tràn stack***. Đo thật thì nó dùng **65 word**. Con số 512 không sai — dư "
     "thì an toàn — nhưng lời *chắc chắn sẽ tràn* là một phán đoán **sai**, và nó sai theo "
     "hướng mình cần biết: bạn đang **ước cao hơn thực tế**. Mình chưa kết luận hẳn, vì nó "
     "HardFault trước khi chạy hết chuỗi khởi tạo BSP nên 65 có thể chưa phải đỉnh. Bạn tự nói "
     "xem con số nào đáng tin tới đâu.\n\n"
     "**Nhưng giờ có lỗi phần cứng, và nó đúng loại bạn đã tự khai.** Mình đọc thanh ghi:\n\n"
     "| thanh ghi | giá trị | nghĩa |\n|---|---|---|\n"
     "| `CFSR` | `0x00000100` | bit 8 = **IBUSERR** — lỗi bus khi **nạp lệnh** |\n"
     "| `HFSR` | `0x40000000` | bit 30 = **FORCED** — leo thang thành HardFault |\n"
     "| `ICSR` | `0x0400f003` | `VECTACTIVE = 3` → CPU **đang kẹt trong HardFault**, SysTick đang chờ |\n"
     "| `current_tcb` | `0x00000000` | **rỗng** |\n"
     "| `ready_map` | `0x00000000` qua 6 lần đọc liên tiếp | không tác vụ nào sẵn sàng |\n\n"
     "Lỗi nạp lệnh nghĩa là CPU **nhảy tới một địa chỉ không hợp lệ**. Và ở bước 7 bạn đã nói "
     "trước đúng hai chỗ gây ra chuyện này, đúng từng chữ:\n\n"
     "> *Lần 1 — thứ tự `xPSR` và `PC` trên ngăn xếp: VẪN XANH. Lỗi này nạp lên bo thật sẽ nổ "
     "HardFault ngay chu kỳ đầu tiên.*\n"
     "> *Lần 2 — `EXC_RETURN`: VẪN XANH. Bộ kiểm host không có khối NVIC để thẩm tra mã ma "
     "thuật thoát ngắt.*\n\n"
     "Bạn nói trước được, bộ kiểm không bắt được, và bo thì nổ đúng chỗ ấy. Mình ghi lại chuyện "
     "này vì nó là thứ đáng giá nhất của cả việc: **một điểm mù được khai báo trước thì khi nó "
     "nổ, ta biết ngay chỗ để tìm.** Nếu bạn im ở bước 7, giờ mình đang đoán giữa chục nguyên "
     "nhân.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Đọc **khung ngăn xếp của chính lỗi này** — `PC` và `LR` đã được đẩy lên lúc "
     "fault, và `MSP`/`PSP` lúc đó. Con số `PC` ấy nói CPU định nhảy đi đâu. Đừng đoán trước "
     "khi đọc nó.\n\n"
     "**2 ·** Rồi soát `PendSV_Handler` theo đúng hai chỗ bạn đã khai: thứ tự ô trên khung, và "
     "giá trị `EXC_RETURN` trả về. Nhớ cả chuyện khung **có số thực** dài hơn khung thường.\n\n"
     "**3 ·** `current_tcb = 0` cũng cần giải thích: ai đặt nó về rỗng, và nếu `PendSV_Handler` "
     "lưu ngữ cảnh vào một con trỏ rỗng thì đó chính là lỗi ghi vào địa chỉ 0.\n\n"
     "**4 ·** Và bài kiểm: hai chỗ ấy vẫn chưa ai canh. Bạn vừa làm được một việc hay — cho "
     "thanh ghi `SCB` đi qua chỗ thay được để bài kiểm quan sát. Dùng đúng cách ấy cho khung "
     "ngăn xếp được không? Dựng một khung giả rồi kiểm từng ô theo thứ tự lõi Cortex-M4 quy "
     "định, và kiểm `EXC_RETURN` thuộc tập giá trị hợp lệ chứ không phải số tuỳ ý.",
     3600, 4, False),

    # Chèn 04/10. Tác tử chẩn đoán ĐÚNG chuỗi lỗi. Nguyên nhân gốc: KHÔNG CÓ TÁC VỤ RỖI.
    # RTOS_IDLE_PRIORITY có định nghĩa, tác vụ thì không ai tạo — lần thứ bảy cùng dạng.
    ("Nguyên nhân gốc: không có tác vụ rỗi",
     "Chẩn đoán của bạn đúng, và mình kiểm được từng mắt: `rtos_pick_next_task` trả `NULL` khi "
     "`ready_map == 0`; `PendSV_Handler` nhận `r0 = 0` rồi `ldr r0, [r0]` đọc địa chỉ `0`; địa "
     "chỉ `0` trên chip này là ảnh Flash chứa MSP ban đầu, nên `ldmia` nạp rác vào `LR`, và "
     "`bx lr` với rác thành một lệnh nhảy thường → `IBUSERR`. Đủ chuỗi, khớp mọi con số mình "
     "đo được.\n\n"
     "Nhưng mình muốn gọi tên **nguyên nhân gốc** chứ không dừng ở chuỗi hậu quả, vì hai thứ "
     "ấy dẫn tới hai bản vá khác nhau.\n\n"
     "Mình grep `idle` cả nhân:\n\n"
     "```\nfirmware/rtos.h:8:#define RTOS_IDLE_PRIORITY   0\n```\n\n"
     "**Đúng một dòng.** Macro có, **tác vụ rỗi thì không ai tạo.** Nên khi cả sáu tác vụ chặn "
     "trong `rtos_delay_ms` — chuyện xảy ra gần như suốt thời gian chạy — `ready_map` về 0 và "
     "nhân không còn gì để chạy.\n\n"
     "Mục 4.1 tài liệu mình viết: *có đủ 32 mức ưu tiên, trong đó **mức thấp nhất dành cho tác "
     "vụ rỗi***. Bạn định nghĩa mức ấy rồi không tạo tác vụ cho nó.\n\n"
     "Đây là **lần thứ bảy** trong hai ngày mình gặp cùng một dạng, và mình kê ra đây vì nó nên "
     "vào báo cáo:\n\n"
     "| lần | cơ chế có sẵn | đường dẫn tới nó |\n|---|---|---|\n"
     "| 1 | nhánh nạp FPGA trong thực đơn công cụ | chưa chạy lần nào, nổ `NameError` |\n"
     "| 2 | `PULL_MODE=UP` trong tệp ràng buộc | chân vẫn thả nổi |\n"
     "| 3 | tổng kiểm chuẩn sinh ra | `main.c` không `#include` |\n"
     "| 4 | `bat_log_giay` để bắt bản ghi quanh lúc nạp | chưa lượt nào dùng |\n"
     "| 5 | `rtos_tick()` viết đúng | không ai gọi |\n"
     "| 6 | `PendSV_Handler` viết đúng, nối đúng ô vector | không ai đặt `PENDSVSET` |\n"
     "| 7 | `RTOS_IDLE_PRIORITY` định nghĩa | **không ai tạo tác vụ rỗi** |\n\n"
     "Bảy lần, và không lần nào có lỗi báo ra. Mỗi lần đều là một thứ **viết đúng** mà **không "
     "ai gọi tới**. Mình nghĩ đó là phát hiện lớn nhất của cả đợt làm này, lớn hơn bất cứ con "
     "số hiệu năng nào.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Tạo tác vụ rỗi ở mức ưu tiên thấp nhất, **không bao giờ chặn**. Nói cho mình "
     "biết nó làm gì trong vòng lặp — ngủ CPU bằng `wfi`, hay chỉ vòng rỗng, và vì sao bạn "
     "chọn thế.\n\n"
     "**2 ·** Và thêm chốt trong `PendSV_Handler`: con trỏ rỗng thì **không được dereference**. "
     "Có tác vụ rỗi rồi thì `ready_map` không bao giờ về 0 nữa — nhưng một nhân mà sai một chỗ "
     "là nhảy vào rác thì nên có hai lớp, không một.\n\n"
     "**3 ·** Rồi soát nốt theo đúng câu hỏi của bảng trên: **còn cơ chế nào bạn đã định nghĩa "
     "mà chưa có đường gọi tới?** Mình đã gặp bảy lần nên mình không tin con số dừng ở bảy.\n\n"
     "**4 ·** Dựng, nạp, rồi **tự đọc `CFSR`, `HFSR`, `ready_map` và mảng mức nước** trước khi "
     "gọi mình nhìn bo. Mình chỉ nhìn khi `CFSR = 0` và `ready_map` khác 0.",
     3600, 4, False),
]

TEN_GIAI_DOAN = {
    1: "Đọc đề và dựng môi trường",
    2: "Nhân RTOS trên máy",
    3: "Sáu tác vụ và thay FreeRTOS",
    4: "Chạy trên bo thật",
    5: "Chốt và báo cáo",
}


def dung_du_an(giu: bool) -> None:
    """Dựng dự án TRỐNG, chỉ có tệp giao việc. Không chép gì từ dự án cũ."""
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    (DU_AN / ".eide" / "ui-test").mkdir(parents=True, exist_ok=True)
    (DU_AN / "tai-lieu").mkdir(exist_ok=True)
    dich = DU_AN / "tai-lieu" / TAI_LIEU.name
    if not dich.exists():
        shutil.copy(TAI_LIEU, dich)
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
    ap = argparse.ArgumentParser(description="Phiên sinh viên — việc 2/3: RTOS tự viết")
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
