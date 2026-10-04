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
