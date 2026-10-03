# -*- coding: utf-8 -*-
"""Phiên sinh viên — việc 1/3: lõi RISC-V trên FPGA Tang Nano 20K.

Làm lại toàn bộ đề án FPGA từ dự án TRỐNG, với đầu vào mới
`docs/fpga/DAU-VAO-AGENT-FPGA-v2.md`, để lấy số liệu thật cho báo cáo.

Ba điều giữ nghiêm, vì nếu lỏng thì phiên này không đo được gì:

1. **Dự án trống.** Không chép gì từ `du-lieu/riscv-tn20k-b`. Chép là tác tử đọc ra đáp án.

2. **Người giao việc ở trình độ SINH VIÊN.** Câu hỏi viết như một sinh viên làm đồ án: biết C
   và Verilog, đã nạp vi điều khiển, **chưa từng dựng CPU trên FPGA**. Không mớm đáp án, không
   nhắc tên công cụ, và **không nói trước những cái bẫy mà phiên 03/10 đã rơi vào** — chân 88
   đọc ra 0, cổng nào JTAG cổng nào UART, phải mở cổng trước khi nạp, cần đúng 24 bitstream.
   Đưa những thứ ấy vào là phát đáp án, và phiên mới sẽ đo chính lời phát ấy.

3. **Câu NGẮN, mỗi lượt một việc.** Đo được 02/10: đề dài có bảng và sáu mục thì tác tử đọc
   rồi dừng mà không ghi gì — không phải hết ngân sách (hạn 220 lời gọi, nó dùng 13–17). Đề
   một câu một việc thì nó làm ngay.

Hạn lượt: 220 lời gọi / 3600 giây, theo `docs/riscv-tn20k/TRANG-THAI-TAM-DUNG.md` §6 — mặc
định 40/300 quá chặt cho việc HDL.

Chạy:
    .venv/bin/python tools/phien_sinhvien_fpga.py --liet-ke
    .venv/bin/python tools/phien_sinhvien_fpga.py --giai-doan 1
    .venv/bin/python tools/phien_sinhvien_fpga.py --buoc 9 --quan-sat "..."
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

DU_AN = REPO / "du-lieu/fpga-sinhvien"
RA = REPO / "du-lieu/ket-qua/fpga-sinhvien"
TAI_LIEU = REPO / "docs/fpga/DAU-VAO-AGENT-FPGA-v2.md"
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

    # --------------------------------------- 1 · ĐỌC ĐỀ VÀ DỰNG MÔI TRƯỜNG
    ("Đọc tài liệu giao việc",
     "Chào bạn. Mình là sinh viên đang làm đồ án, đề tài đưa phép nhân ma trận xuống phần "
     "cứng FPGA. Mình chưa từng dựng CPU trên FPGA nên sẽ nhờ bạn khá nhiều. Mình vừa đưa vào "
     "dự án tệp tài liệu giao việc. Bạn đọc hết rồi tóm tắt lại cho mình: mình cần làm mấy "
     "bài, mỗi bài đạt nghĩa là gì, và chỗ nào mình đã cho sẵn số còn chỗ nào bạn phải tự "
     "tìm.", 1800, 1, False),

    ("Hỏi những chỗ tài liệu chưa nói",
     "Trước khi bắt tay, bạn rà lại tài liệu rồi nói thẳng: có con số hay chi tiết nào bạn sẽ "
     "cần mà mình chưa cho không? Có thì liệt kê để mình đi tìm, đừng tự điền giá trị mình "
     "đoán.", 1800, 1, False),

    ("Kiểm môi trường",
     "Giờ kiểm môi trường máy mình trước đã. Mục 7 của tài liệu có ba việc kiểm sớm. Bạn làm "
     "ba việc đó rồi báo mình kết quả từng việc.", 2400, 1, False),

    # Bước này sinh ra TỪ câu trả lời của tác tử ở bước 2. Nó tìm ra hai chỗ tài liệu giao
    # việc chưa chốt — dải giá trị phần tử ma trận, và giải thuật tổng kiểm — và cả hai đều
    # thật. Tài liệu đầu vào KHÔNG sửa lại: nó đã commit trước khi phiên chạy, và sửa nó bây
    # giờ là phá mất chính bằng chứng "đầu vào có trước kết quả". Nên trả lời bằng một lượt
    # hỏi đáp, và lượt ấy nằm trong nhật ký phiên.
    ("Trả lời hai câu bạn hỏi, và hỏi lại về ba lỗi",
     "Hai chỗ bạn chỉ ra đều đúng, mình chưa nghĩ tới. Trả lời:\n\n"
     "**Dải giá trị phần tử.** Bạn tính giúp mình: với `I32` cộng dồn vào `int32_t`, N bằng 32, "
     "thì dải nào là an toàn không tràn? Chọn dải theo con số bạn tính ra, đừng chọn theo cảm "
     "giác, rồi ghi lý do vào `docs/decisions.md`.\n\n"
     "**Tổng kiểm.** Bạn chọn giải thuật nào cũng được, miễn ba điều: cài giống nhau ở C và "
     "Python, mình đọc mã là hiểu được, và bạn chứng minh được hai bên cho cùng kết quả trên "
     "một ví dụ nhỏ.\n\n"
     "Và một câu nữa. Lượt kiểm môi trường của bạn có **3 lời gọi công cụ báo lỗi**. Bạn nói "
     "cho mình biết ba lỗi đó là gì, và ba việc kiểm môi trường cuối cùng có đạt hay không.",
     1800, 1, False),

    # Bước này bắt một lời khai sai, và bắt đúng chỗ người vừa hỏi thẳng ở lượt trước. Tác
    # tử khai "giải trình rõ 3 lỗi công cụ và lưu toàn bộ vào docs/decisions.md" — cả hai nửa
    # đều không có: không dòng nào trong lượt trả lời, và grep ba mã lỗi trong tệp ra 0.
    #
    # Đáng ghi là nó CÓ cố tìm: 11 lời gọi đầu toàn ledger.query và fs.grep. Tìm không ra rồi
    # báo như đã làm. Đó là chỗ đáng chữa, không phải chỗ đáng mắng.
    ("Ba lỗi bạn chưa giải trình",
     "Dải `[-8191, 8191]` thì mình duyệt — mình tự tính lại và khớp: 32 × 8191² = "
     "2 146 959 392 ≤ 2³¹−1, còn 32 × 8192² thì vượt. Con số tính ra chứ không phải chọn theo "
     "cảm giác, đúng điều mình cần. Fletcher-32 cũng duyệt.\n\n"
     "Nhưng một chỗ mình phải nói. Bạn báo *\"giải trình rõ 3 lỗi công cụ và lưu toàn bộ vào "
     "`docs/decisions.md`\"*. Mình kiểm cả hai nửa:\n"
     "- Trong cả lượt trả lời của bạn **không có một dòng nào** về ba lỗi đó.\n"
     "- Mình grep `E3006`, `E4020`, `E4030` trong 80 dòng `docs/decisions.md` → **0 kết quả**.\n\n"
     "Mình thấy bạn **có cố tìm** — 11 lời gọi đầu toàn là tra sổ cái. Nên mình không nghĩ bạn "
     "định nói sai. Mình đoán là tìm không ra rồi báo như đã làm.\n\n"
     "Hai việc. Một: ba lỗi ấy là `code.vendor_fetch` lỗi `E3006`, `fs.write` lỗi `E4020`, "
     "`hdl.sim` lỗi `E4030` — bạn tra rồi nói cho mình biết từng lỗi là gì, và **ba việc kiểm "
     "môi trường cuối cùng có đạt hay không**. Hai: nói cho mình biết vì sao lúc tìm không ra "
     "thì bạn lại báo là đã giải trình, thay vì báo là chưa tìm được. Mình hỏi để lần sau đặt "
     "câu khác đi, không phải để bắt lỗi bạn.\n\n"
     "Và một chi tiết nhỏ nữa: dòng 3 báo cáo của bạn ghi *giả định ma trận cố định N = 32×32*. "
     "Tài liệu mình viết N nhận bốn giá trị 4, 8, 16, 32. Cận trên thì vẫn đúng vì 32 là xấu "
     "nhất, nhưng câu giả định thì sai.", 1800, 1, False),

    # ------------------------------------------------- 2 · BÀI 1, TRÊN MÁY
    ("Bài 1: thiết kế trước khi viết",
     "Bắt đầu Bài 1. Trước khi gõ mã, bạn mô tả cho mình thiết kế: có những khối gì, nối với "
     "nhau thế nào, và tệp nào làm việc gì. Mình muốn thấy đường đi trước khi bạn viết.",
     1800, 2, False),

    ("Bài 1: viết mã",
     "Thiết kế ổn rồi, viết đi bạn. Xong thì liệt kê từng tệp đã ghi kèm số dòng.", 3600, 2, False),

    ("Bài 1: tiêu chí mô phỏng, nêu TRƯỚC khi chạy",
     "Sắp mô phỏng. Bạn nêu tiêu chí nghiệm thu bằng số trước đã, đừng chạy vội.", 1800, 2, False),

    ("Bài 1: chạy mô phỏng",
     "Giờ chạy mô phỏng đối chiếu đúng những tiêu chí vừa nêu. Báo mình từng tiêu chí đạt hay "
     "không, kèm số đo thật.", 2400, 2, False),

    ("Bài 1: bài kiểm có biết báo lỗi không",
     "Mô phỏng xanh thì mình chưa dám tin ngay. Bạn phá mã sản phẩm vài chỗ rồi chạy lại, xem "
     "bài kiểm có báo đỏ không. Xong thì khôi phục mã và cho mình xem bảng phá gì báo gì. Chỗ "
     "nào vẫn xanh thì nói thẳng là vẫn xanh.", 2400, 2, False),

    # Bước này sinh ra từ chính kết quả bước 10: tác tử tự khai ca 4 VẪN XANH, và điểm mù nó
    # chỉ ra là thật — `tb_soc_run.v` khai `wire [5:0] leds` và nối `.led(leds)` nhưng không
    # có dòng nào kiểm giá trị. Mà danh mục nghiệm thu Bài 1 dòng 3 lại đòi "LED nháy".
    ("Vá điểm mù LED của bài kiểm",
     "Ba ca đầu đỏ, và mình đã tự kiểm: ba tệp RTL bạn khôi phục đúng nguyên trạng. Ca 4 vẫn "
     "xanh thì bạn **tự khai ra**, không chờ mình hỏi — mình ghi nhận chuyện đó.\n\n"
     "Mình kiểm lại điểm mù bạn nói và đúng: `sim/tb_soc_run.v` dòng 19 có khai "
     "`wire [5:0] leds`, dòng 40 có nối `.led (leds)`, nhưng **không dòng nào kiểm giá trị**. "
     "Tín hiệu có nối mà không ai assert.\n\n"
     "Chỗ này phải vá, vì danh mục nghiệm thu Bài 1 của mình có dòng *terminal hiện chuỗi lặp "
     "lại, **và LED nháy***. Nếu mô phỏng không kiểm đèn thì yêu cầu ấy chưa được chứng minh ở "
     "đâu cả — mà lát nữa lên bo thì mình chỉ nhìn được bằng mắt, không đo được.\n\n"
     "Bạn thêm phép kiểm đèn vào testbench: nó phải chứng minh LED **thật sự đổi trạng thái**, "
     "không chỉ là có dây nối. Vá xong thì chạy lại đúng ca 4 — ép cứng `led_n = 6'b000000` — "
     "và lần này bài kiểm phải **báo đỏ**. Nếu vẫn xanh thì nói thẳng là vẫn xanh.", 2400, 2, False),

    # --------------------------------------------- 3 · BÀI 1 TRÊN BO THẬT
    ("Bài 1: dựng bitstream",
     "Mô phỏng xong rồi. Dựng bitstream đi bạn, rồi báo mình tài nguyên dùng hết và Fmax đo "
     "được.", 2400, 3, False),

    # Tác tử dừng đúng chỗ và hỏi: `target.flash` trả E4013 "Found 0 stlink programmers" cho
    # một kit FPGA, và nó xin phép bỏ qua đối chiếu chip. Trả lời bằng BẢN VÁ chứ không bằng
    # lối lách — chính lời chặn đã dặn "đừng tìm đường vòng để lách".
    ("Bài 1: nạp bo",
     "Mình đã cắm kit vào máy. Bạn nạp bitstream lên bo.\n\n"
     "Lượt trước bạn dừng lại hỏi mình về lỗi `E4013` — công cụ đi tìm mạch nạp ST-Link cho "
     "một kit FPGA. Bạn hỏi đúng chỗ, và mình **không chọn lối bỏ qua đối chiếu chip**: mình "
     "đã vá công cụ để nó đọc định danh FPGA bằng IDCODE qua JTAG. Giờ thử lại.", 2400, 3, False),

    ("Bài 1: bo đang chạy đúng bản vừa dựng không",
     "Mình cần chắc bo đang chạy đúng bitstream vừa dựng. Bạn tìm một cách đo để chắc chuyện "
     "đó.", 1800, 3, False),

    ("Bài 1: đọc cổng nối tiếp",
     "Giờ đọc cổng nối tiếp xem bo đang nói gì.", 1800, 3, False),

    ("Bài 1: người quan sát",
     "Mình đang nhìn bo. Đây là những gì mình thấy, nguyên văn:\n\n{quan_sat}\n\n"
     "Từ đúng những gì mình vừa kể, bạn suy ra được gì?", 1800, 3, True),

    ("Bấm S1 không có tác dụng — nghĩ cách tách ba hướng",
     "Mình bấm giữ nút S1 rồi nhả ra: **không có gì đổi cả, bo vẫn tối thui.**\n\n"
     "Mình nghĩ về cái này và thấy nó **chưa tách được** ba hướng của bạn, nên mình nói ra chứ "
     "không kết luận hộ bạn:\n"
     "- Nếu chân 88 kẹp mức 0 thì lúc nghỉ reset bị giữ nên tối, bấm vẫn 0 nên vẫn tối — "
     "**khớp**.\n"
     "- Nếu chân 88 đọc đúng, tức nghỉ là mức 1, thì lúc nghỉ reset đã nhả và LED0 phải nháy "
     "— **không khớp**.\n"
     "- Nhưng hướng 2 và hướng 3 của bạn, CPU vào bẫy lỗi hoặc bus treo, **cũng cho đèn tối "
     "bất kể mình bấm hay không**.\n\n"
     "Nên quan sát của mình chỉ loại được *chân 88 đọc đúng*. Ba hướng còn lại vẫn nguyên.\n\n"
     "Bạn nghĩ cho mình một phép đo **tách được** chúng. Điều kiện: phép đo ấy phải chỉ ra "
     "**một** hướng chứ không chỉ nói 'có vấn đề'. Và nếu nó cần mắt mình thì nói rõ mình "
     "phải nhìn cái gì, vì mình chỉ thấy được đèn, không đo được tín hiệu bên trong chip.",
     2400, 3, True),

    ("Duyệt bảng 6 đèn chẩn đoán, kèm một điều kiện",
     "Mình duyệt. Thiết kế này tách được cả ba hướng, và mình thích nhất LED3: bạn không chỉ "
     "phơi `mem_ready` ra đèn mà **dựng một bộ dò** đếm 64 chu kỳ rồi chốt. Phơi thẳng thì mắt "
     "mình không thấy được, vì nó nhảy ở 27 MHz. Bạn nghĩ tới chỗ đó.\n\n"
     "Một điều kiện: đây là **bản dựng để chẩn đoán**, không phải bản để đo Bài 2. Thêm mạch "
     "vào thì tài nguyên và định thời đổi, mà Bài 2 lại so số chu kỳ với mô phỏng ở mức 1 phần "
     "trăm — bản đo phải là đúng thiết kế đã mô phỏng. Nên làm sao **gỡ ra được sạch**: một "
     "tham số hoặc một cờ, mặc định TẮT. Và nói cho mình biết bạn chọn cách nào.\n\n"
     "Dựng xong thì nạp lên bo rồi bảo mình nhìn. Mình sẽ đọc cho bạn trạng thái từng đèn theo "
     "thứ tự LED0 đến LED5.", 2400, 3, False),

    ("Tách hướng 1 bằng kênh UART, không cần mắt người",
     "Hai tin cho bạn.\n\n"
     "**Tin thứ nhất, và đây là lỗi của mình.** Suốt mấy lượt vừa rồi, mọi quan sát đèn đều "
     "nói về **một bitstream khác**, không phải bản của mình. Chiều nay mình đã ghi flash trên "
     "kit bằng bitstream của một dự án cũ, nên mỗi lần nạp SRAM xong là bo nạp lại từ flash và "
     "đè lên. Bằng chứng: mình nạp Bài 1 rồi bắt bản ghi UART, cổng phát ra "
     "`=== BAI 2: MATRIX MULTIPLICATION BENCHMARK ===` của dự án cũ.\n\n"
     "Mình đã ghi flash lại bằng bản Bài 1 của bạn, `--verify` khớp. Nên từ giờ bo chạy đúng "
     "thiết kế của mình.\n\n"
     "Rút ra một điều mình muốn bạn nhớ: **nạp SRAM xong, phải xác nhận bo chạy bản SRAM chứ "
     "không phải bản trong flash.** Trên kit này, flash đã ghi thì SRAM không thắng.\n\n"
     "**Tin thứ hai:** sau khi ghi flash bản Bài 1, cổng nối tiếp **vẫn im hoàn toàn**, 0 byte "
     "sau khi đã vét sạch hàng đợi. Mà Bài 1 in lặp vô hạn, nên im nghĩa là CPU không chạy.\n\n"
     "Mình chưa đọc được đèn ngay. Nhưng UART là kênh mình **đo được bằng máy**, không cần mắt "
     "ai. Bạn nghĩ cho mình một phép đo dùng **chỉ kênh UART** để tách hướng 1 của bạn — reset "
     "bị giữ — ra khỏi hai hướng còn lại. Làm được thì làm luôn rồi báo kết quả.", 2400, 3, False),

    ("Duyệt bộ phát chẩn đoán — và ghi vào FLASH, không nạp SRAM",
     "Mình duyệt. Thiết kế này hơn cách mình từng nghĩ, vì nó **đọc được bằng máy** chứ không "
     "cần mắt ai. Và phần giải thích vì sao đọc thụ động không tách được — cả ba hướng đều "
     "giữ TX ở mức nghỉ nên không có cạnh xuống Start bit — là lý do cơ chế, đúng chỗ.\n\n"
     "Làm đi. Hai lưu ý khi nạp:\n\n"
     "Một: **ghi vào flash trên kit**, đừng nạp SRAM. Mình đã đo: trên bo này flash đã ghi thì "
     "SRAM không thắng, nạp SRAM xong là bị đè ngay. Dùng cờ ghi flash kèm đọc ngược để đối "
     "chiếu.\n\n"
     "Hai: giữ cờ gỡ mạch chẩn đoán. Và mình nhắc lại một điều lượt trước bạn chưa làm đúng: "
     "mình yêu cầu **mặc định TẮT**, mà mã ra `parameter DIAG_ENABLE = 1`. Phần cơ chế thì "
     "đúng — khối `generate` nên đặt 0 là mạch biến mất hẳn — nhưng mặc định thì ngược. Sửa "
     "lại cho mặc định là 0, rồi khi dựng bản chẩn đoán thì truyền 1 vào.\n\n"
     "Nạp xong thì tự đọc cổng nối tiếp rồi báo mình kết quả phân lập.", 2400, 3, False),

    ("R:0 — tách nhánh cuối: chân 88 hay bộ đếm khởi động",
     "Bộ phát của bạn chạy, và nó trả lời. Mình tự đọc cổng, vét sạch trước, 12 giây được "
     "1 788 byte:\n\n"
     "```\n[DIAG] R:0 T:0 H:0 B:0\n```\n\n"
     "lặp đều. Nên: đồng hồ sống, bitstream chạy, đường UART TX thông — và **`rst_n = 0`, "
     "reset đang bị giữ.** Hướng 1 của bạn đúng.\n\n"
     "Mình ghi nhận một chỗ: bảng tiêu chí bạn viết dự đoán *hướng 1 thì bộ phát cũng kẹt "
     "reset nên 0 byte*. Nhưng khi viết mã bạn đặt bộ phát **ngoài vùng reset** và báo `R` ra "
     "thành một trường. **Bản cài đặt tốt hơn bản thiết kế** — thay vì im lặng mơ hồ, mình có "
     "một con số nói thẳng.\n\n"
     "Còn một nhánh cuối. `rst_n` sinh từ hai thứ: bộ đếm giữ reset sau cấp nguồn, và nút S1 "
     "chân 88. Mình cần biết **cái nào** giữ nó ở 0:\n"
     "- nếu chân 88 đọc ra 0 lúc không ai bấm → lỗi ở chân\n"
     "- nếu chân 88 đọc ra 1 mà `rst_n` vẫn 0 → lỗi ở logic bộ đếm\n\n"
     "Bộ phát của bạn làm được việc này: thêm một trường báo **mức thô của chân 88**, và thêm "
     "giá trị bộ đếm khởi động. Rồi dựng lại, ghi flash, và tự đọc cổng báo mình.", 2400, 3, False),

    ("Sửa cho xong Bài 1",
     "Nguyên nhân gốc đã chốt, bạn tìm ra bằng chính bộ phát của bạn: `S:0` — chân 88 đọc mức "
     "0 khi không ai bấm; `C:40` — bộ đếm khởi động chạy đủ, không lỗi. Nên `rst_n` bị giữ chỉ "
     "vì chân 88.\n\n"
     "Giờ mình muốn bạn **tập trung sửa cho xong Bài 1**. Việc của bạn, theo thứ tự:\n\n"
     "**1 · Sửa để CPU chạy được.** Bạn tự chọn cách. Hai đường mình nghĩ tới, nhưng bạn thấy "
     "đường thứ ba tốt hơn thì cứ làm:\n"
     "- làm cho nút dùng được thật — lọc, đồng bộ, hoặc xem lại cực tính\n"
     "- bỏ nút khỏi mạch reset, chỉ giữ bộ đếm khởi động\n\n"
     "Nếu bạn chọn bỏ nút thì **phải ghi thành một quyết định có lý do và có trích chỗ lấy**, "
     "vì tài liệu mình viết đòi *reset gồm power-on-reset và nút S1*. Lệch đặc tả thì mình "
     "chịu được, nhưng kho ghi một đằng mã làm một nẻo thì không.\n\n"
     "**2 · Tắt mạch chẩn đoán** cho bản giao. Bản đo phải là đúng thiết kế đã mô phỏng.\n\n"
     "**3 · Dựng, ghi vào flash, rồi TỰ ĐỌC cổng nối tiếp.** Mình cần thấy chuỗi `Hello from "
     "PicoRV32 on Tang Nano 20K, cycle=<số>` **lặp lại**, và `cycle` phải **tăng khoảng "
     "27 000 000 mỗi dòng**. Nhớ ghi flash chứ đừng nạp SRAM — trên bo này flash đã ghi thì "
     "SRAM không thắng.\n\n"
     "**4 · Báo mình danh mục nghiệm thu Bài 1**, bốn dòng, mỗi dòng ghi đạt hay chưa kèm số "
     "đo và chỗ lấy số. Dòng nào cần mắt mình thì ghi rõ là cần mình.", 3600, 3, False),

    # ------------------------------------------------- 4 · BÀI 2, TRÊN MÁY
    ("Bài 1 đóng, và một chỗ còn sót trong mã",
     "Bài 1 **đạt cả bốn dòng nghiệm thu**. Mình tự đọc cổng chứ không nhận qua lời bạn:\n\n"
     "```\nHello from PicoRV32 on Tang Nano 20K, cycle=1485001241\n"
     "Δcycle: 27 000 001 · 27 000 031 · 27 000 024\n```\n\n"
     "Và sau khi mình rút điện cắm lại, `cycle` đọc được là 1 404 001 194 — lớn hơn hẳn lần "
     "trước (837 000 733), nên bo chạy liên tục chứ không khởi động lại rồi đếm từ đầu. Đèn "
     "LED0 vẫn nháy. Dòng 4 đạt.\n\n"
     "`ADR-01` của bạn mình cũng duyệt: ghi rõ lý do, ghi cả mặt dở *không reset tay được bằng "
     "S1*, và tự khai tầng VÀNG chứ không khai NGƯỜI. Đúng cách.\n\n"
     "Nhưng còn một chỗ sót, nhỏ mà mình muốn bạn dọn trước khi sang Bài 2. Trong "
     "`reset_gen.v`, hai thanh ghi `btn_s1_sync1` và `btn_s1_sync2` **vẫn được tính mỗi chu "
     "kỳ nhưng không ai đọc** — mình grep cả thư mục `rtl/`, không có chỗ dùng nào.\n\n"
     "Trình tổng hợp sẽ bỏ đi nên không tốn tài nguyên. Nhưng mã nguồn đang nói *ta đồng bộ "
     "nút qua hai tầng flip-flop* trong khi **không gì dùng kết quả ấy** — người đọc sau sẽ "
     "tưởng nút còn trong mạch reset. Đây cùng họ với mọi lỗi mình gặp hôm nay: **mã mô tả một "
     "việc, thực tế làm việc khác**.\n\n"
     "Bạn dọn cho gọn, theo cách bạn thấy đúng: bỏ hẳn, hoặc giữ lại và nối ra chỗ nào có "
     "dùng. Nói cho mình biết bạn chọn cách nào và vì sao.", 1800, 4, False),

    ("Bài 2: kê trước mọi ô sẽ đo",
     "Sang Bài 2. Trước khi làm gì, bạn kê cho mình danh sách đầy đủ các ô sẽ đo: mỗi ô là "
     "kích thước nào, kiểu dữ liệu nào, cấu hình CPU nào, dịch bằng tập lệnh nào. Và nói cho "
     "mình biết cả phiên này cần dựng bao nhiêu bitstream, vì sao đúng con số đó.", 2400, 4, False),

    ("Bài 2: bốn cách cài đặt",
     "Bạn chọn bốn cách cài đặt thuật toán rồi giải thích mỗi cách khác nhau ở đâu. Cách nào "
     "chỉ hợp với ma trận lớn thì nói rõ, và nói luôn bạn xử lý thế nào khi ma trận nhỏ.",
     1800, 4, False),

    ("Bài 2: cách đo số chu kỳ",
     "Mục 4 của tài liệu mình nêu bốn điều về cách đo. Bạn xem có đúng không, thiếu gì thì bổ "
     "sung, rồi nói cho mình cách bạn sẽ đo.", 1800, 4, False),

    ("Bài 2: viết mã",
     "Chốt rồi thì viết đi bạn. Xong thì liệt kê từng tệp kèm số dòng.", 3600, 4, False),

    ("Bài 2: mô hình chuẩn và tổng kiểm",
     "Mình cần biết kết quả nhân ma trận trên bo là đúng, không chỉ là chạy xong. Bạn làm mô "
     "hình chuẩn bằng Python rồi đối chiếu tổng kiểm.", 2400, 4, False),

    ("Bài 2: chạy mô phỏng đủ các ô",
     "Chạy mô phỏng cho đủ các ô đi bạn. Ô nào không chạy được thì ghi là không chạy được, "
     "đừng bỏ qua im lặng.", 3600, 4, False),

    ("Bài 2: bài kiểm có biết báo lỗi không",
     "Lại phá mã rồi chạy lại như ở Bài 1. Mình muốn thấy bài kiểm của Bài 2 cũng biết báo "
     "đỏ.", 2400, 4, False),

    # --------------------------------------------- 5 · BÀI 2 TRÊN BO THẬT
    ("Bài 2: chạy trên bo",
     "Mô phỏng xong rồi. Giờ chạy trên bo thật, bắt bản ghi cổng nối tiếp của từng ô. Ô nào "
     "không bắt được thì ghi là không bắt được.", 3600, 5, False),

    ("Bài 2: người quan sát",
     "Mình đang nhìn bo. Nguyên văn những gì mình thấy:\n\n{quan_sat}\n\n"
     "Bạn suy ra được gì?", 1800, 5, True),

    ("Bài 2: đối chiếu bo với mô phỏng",
     "Giờ đối chiếu số đo trên bo với số mô phỏng. Tài liệu đòi lệch không quá 1 phần trăm. "
     "Báo mình từng ô lệch bao nhiêu, và bao nhiêu ô vượt ngưỡng.", 2400, 5, False),

    ("Bài 2: chỗ nào lệch thì vì sao",
     "Ô nào lệch nhiều nhất thì nói cho mình biết vì sao. Chưa đo được thì nói chưa đo được.",
     1800, 5, False),

    # ------------------------------------------------------ 6 · CHỐT
    ("Phép đối chiếu này KHÔNG chứng minh được gì",
     "Bạn tự kê cho mình: cả hai bài vừa rồi, những gì vẫn chưa được chứng minh.", 1800, 6, False),

    ("Soát lại danh mục nghiệm thu",
     "Tài liệu có danh mục nghiệm thu cho từng bài. Bạn soát lại từng dòng: đạt hay chưa, số "
     "đo là bao nhiêu, lấy ở đâu. Dòng nào chưa làm thì ghi chưa làm.", 2400, 6, False),

    ("Tự kê chỗ đã báo xong mà chưa xong",
     "Câu cuối, mình hỏi thật. Trong cả phiên này có lúc nào bạn báo đã xong hoặc đã kiểm, mà "
     "thực ra lúc đó chưa xong, hoặc phép kiểm chưa đo được cái cần đo không? Có thì kê ra "
     "hết. Mình cần biết để viết báo cáo, và mình không coi đó là lỗi nếu bạn tự nói ra.",
     1800, 6, False),

    ("Xuất tài liệu tổng kết",
     "Cuối cùng, làm cho mình một tài liệu tổng kết cả phiên để nộp kèm đồ án: đi qua những "
     "bước nào, mỗi bước số đo ra sao, chỗ nào phải sửa và vì sao, chỗ nào còn chưa xong. Ghi "
     "cả những lần sai, đừng chỉ ghi phần thành công.", 2400, 6, False),
]

TEN_GIAI_DOAN = {
    1: "Đọc đề và dựng môi trường",
    2: "Bài 1 trên máy",
    3: "Bài 1 trên bo thật",
    4: "Bài 2 trên máy",
    5: "Bài 2 trên bo thật",
    6: "Chốt và báo cáo",
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

    nk = NhatKy(RA, tieu_de="phiên sinh viên — lõi RISC-V trên FPGA Tang Nano 20K",
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
    ap = argparse.ArgumentParser(description="Phiên sinh viên — việc 1/3: FPGA RISC-V")
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
