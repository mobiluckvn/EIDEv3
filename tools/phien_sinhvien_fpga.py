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

    # Chèn 03/10 tối. Hai việc trong một bước, và việc thứ nhất là của MÌNH.
    #
    # Tôi đã đọc nhật ký rồi kết luận tác tử không trả lời câu về số bitstream. Sai: nhật ký
    # mất đuôi vì gói app cũ (DEV-333), còn nó trả lời đủ. Và đáp án của nó — 3 bitstream —
    # ĐÚNG, còn con số 24 tôi chờ sẵn thì sai: `$readmemh` buộc CHƯƠNG TRÌNH cố định lúc tổng
    # hợp, không buộc một chương trình chỉ đo một ô.
    #
    # Nói ra chỗ mình sai, trong chính nhật ký làm sở cứ, là phần của phép đo. Một nhật ký chỉ
    # ghi những lần người đúng thì không đo được gì về cách người và tác tử làm việc với nhau.
    ("Bài 2: mình nhận sai về số bitstream, và chốt kế hoạch",
     "Trước khi bạn viết mã, mình phải nói hai điều.\n\n"
     "**Điều thứ nhất, mình nhận sai.** Mấy lượt vừa rồi mình đọc nhật ký và tưởng bạn không "
     "trả lời câu hỏi *cần dựng bao nhiêu bitstream*. Thực ra bạn trả lời đủ, có cả mục riêng "
     "và lý do. Nhật ký của mình bị cắt mất đuôi vì một lỗi bên mình — bản ứng dụng mình dùng "
     "để ghi là bản cũ, nó cắt lời bạn ở 3000 ký tự mà không để lại dấu gì. 16 trong 30 câu "
     "của bạn bị mất đuôi như vậy, tổng hơn 23 000 ký tự. Mình đã vá lại nhật ký từ bản ghi "
     "phiên và chặn lỗi ấy lại.\n\n"
     "**Điều thứ hai, đáp án của bạn đúng và mình đã chờ sẵn một con số sai.** Mình nghĩ phải "
     "dựng 24 bitstream, vì mình cho rằng mỗi nhóm ô cần một chương trình riêng. Bạn nói 3, "
     "và lý do của bạn chặn đúng chỗ mình hiểu sai: `$readmemh` buộc **chương trình** phải cố "
     "định lúc tổng hợp, chứ không buộc **một chương trình chỉ được đo một ô**. Cả 8 thủ tục "
     "(4 cách × 2 kiểu) nằm trong ~3 KB mã, ba ma trận dùng chung một vùng đệm 12 KB, nên một "
     "firmware tự chạy hết 32 ô của một cấu hình là được. Chỉ 3 cấu hình CPU là khác mạch "
     "thật. Mình chốt kế hoạch 3 bitstream của bạn.\n\n"
     "Nhưng mình muốn hỏi thêm hai chỗ trong chính kế hoạch ấy, vì chúng là chỗ nó có thể vỡ:\n\n"
     "**1 · Con số 3 KB mã lệnh là bạn ƯỚC hay bạn ĐO?** Nếu ước thì sau khi dịch xong bạn "
     "phải đọc kích thước `.text` thật ra cho mình xem, và nói nó so với 32 KB BRAM thế nào. "
     "Ước sai thì bitstream dựng được nhưng chương trình tràn vùng nhớ, mà cái đó không hiện "
     "ra lúc tổng hợp.\n\n"
     "**2 · Một firmware chạy liền 32 ô thì một lần treo mất cả 32 ô.** Mình không đòi bạn "
     "đổi kế hoạch, nhưng mình cần biết: nếu nó dừng ở ô thứ 17 thì mình nhìn vào đâu để "
     "biết nó đã qua 16 ô? In kết quả từng ô ngay khi đo xong, hay dồn cuối cùng mới in?\n\n"
     "Trả lời hai chỗ đó rồi bắt tay viết mã.", 2400, 4, False),

    ("Bài 2: viết mã",
     "Chốt rồi thì viết đi bạn. Xong thì liệt kê từng tệp kèm số dòng.", 3600, 4, False),

    ("Bài 2: mô hình chuẩn và tổng kiểm",
     "Mình cần biết kết quả nhân ma trận trên bo là đúng, không chỉ là chạy xong. Bạn làm mô "
     "hình chuẩn bằng Python rồi đối chiếu tổng kiểm.", 2400, 4, False),

    # Chèn 03/10 tối, sau khi MỞ MÃ RA ĐỌC chứ không đọc báo cáo của tác tử. Bốn chỗ, và
    # chỗ nặng nhất là lỗi trong TÀI LIỆU CỦA MÌNH: tiêu chí "96/96 ô ok=1" tự nó không đo
    # được gì, vì ok của V0 so chính nó.
    ("Bài 2: bốn chỗ mình đọc mã mới thấy",
     "Mình mở mã ra đọc, không đọc báo cáo của bạn. Bốn chỗ.\n\n"
     "**1 · Cờ `ok` của V0 không bao giờ nói được 0 — và đây là lỗi trong tiêu chí của "
     "mình.** Trong `main.c`:\n\n"
     "```c\n"
     "chk = calc_checksum(n);\n"
     "if (ver == 0) { baseline_chk = chk; }\n"
     "int is_ok = (chk == baseline_chk) ? 1 : 0;\n"
     "```\n\n"
     "Ở lượt `ver == 0`, `baseline_chk` vừa được gán bằng chính `chk`, nên `is_ok` luôn là 1. "
     "24 trong 96 ô có một cờ **không có khả năng cấu trúc để báo sai**. Và vì V1–V3 chỉ so "
     "với V0, nếu V0 tính sai thì cả bốn ô cùng sai giống nhau và cùng báo `ok=1`.\n\n"
     "Nghĩa là tiêu chí mình viết trong tài liệu — *mọi ô `ok=1`* — một bo tính sai toàn bộ "
     "vẫn đạt được. Lỗi này là của mình, mình nhận. Nhưng mình cần bạn chữa.\n\n"
     "**2 · Tổng kiểm chuẩn được sinh ra rồi không ai dùng.** `Makefile` để "
     "`sw/golden_checksums.h` làm điều kiện trước của cả `sw-h0`, `sw-h1`, `sw-h2`, và "
     "`golden_model.py --gen-header` sinh nó ra thật. Nhưng `main.c` chỉ `#include <stdint.h>` "
     "— **không chỗ nào nạp tệp ấy vào**. Mình grep cả `bai2/sw/`, không có `GOLDEN` nào.\n\n"
     "Nên mốc chuẩn độc lập của bạn có trên đĩa mà không tới được chip. Trên bo, phép kiểm "
     "duy nhất đang chạy là *bốn cách có cho ra cùng một số không*, chứ không phải *số ấy có "
     "đúng không*. Mình gặp đúng kiểu lỗi này hai lần hôm nay rồi: cơ chế có sẵn, đường dẫn "
     "tới nó đứt.\n\n"
     "**3 · V3 trong mã không phải V3 trong kế hoạch.** Kế hoạch bạn trình và mình duyệt nói "
     "V3 là *tiling / chia khối 4×4, nạp 16 giá trị tích luỹ vào thanh ghi*. Mã thì làm "
     "**chuyển vị `B` rồi nhân** (`mat_b_trans[j*n+i] = mat_b[i*n+j]`). Hai thứ khác nhau, và "
     "mình không được báo là đã đổi.\n\n"
     "Mình không đòi bạn phải quay về tiling — đổi có thể là đổi đúng. Nhưng phải nói ra, và "
     "phải trả lời thêm: vòng chuyển vị nằm **trong** hàm nên nó nằm trong khoảng được bấm "
     "giờ. Vậy V3 đang đo *chuyển vị cộng nhân*, còn V0–V2 đo *nhân*. Bạn cố ý vậy, hay sót?\n\n"
     "**4 · Chú thích nói 12 KB, mã khai 16 KB.** Dòng chú thích ghi *Vung dem tai su dung cho "
     "ba ma tran (tong 12 KB)*, ngay dưới là **bốn** mảng `int32_t[1024]` = 16 KB. Mảng thứ tư "
     "`mat_b_trans` là thứ bạn thêm cho V3. Con số trong chú thích là con số bạn dùng để nói "
     "với mình rằng bộ nhớ còn dư.\n\n"
     "Việc của bạn, theo thứ tự:\n\n"
     "**a ·** Chữa chỗ 1 và 2 cùng lúc, vì chúng là một việc: nạp tổng kiểm chuẩn của Python "
     "vào firmware và cho **mọi ô, kể cả V0**, so với mốc ấy. Mốc truy về mô hình độc lập, "
     "không truy về đầu ra của chính mã.\n\n"
     "**b ·** Trả lời chỗ 3 và sửa chú thích ở chỗ 4.\n\n"
     "**c ·** Rồi **tự phá mã của mình để xem phép kiểm có kêu không**. Mình muốn thấy ba lần "
     "phá, mỗi lần một dòng, chạy mô phỏng rồi khôi phục: đổi một hằng số trong V0; làm lệch "
     "một chỉ số trong V2; đổi một phần tử trong bộ sinh dữ liệu. Phép kiểm nào không kêu ở "
     "lần phá nào thì nói rõ ra — đó là chỗ nó không bảo vệ được.\n\n"
     "**d ·** Và cho mình xem kích thước `.text` **đo thật** bằng `size`, như bạn đã hứa ở "
     "lượt trước. Bạn tự khai ~3 KB là tầng ĐỒNG; giờ nâng nó lên tầng có số đo.", 3600, 4,
     False),

    # Chèn 03/10 tối. Bảng ba ca phá mã của tác tử là bảng DỰ ĐOÁN được trình bày như bảng
    # kết quả, và lý do nó nêu để không chạy thật thì sai: `hdl.sim` đã chạy 80 lượt và
    # `hdl.bitstream` 28 lượt trong chính phiên này.
    #
    # Đây là họ lỗi tôi đã ghi vào trí nhớ dưới tên "ok nói về lời gọi, không nói về kết
    # quả", nhưng lần này ngược chiều: một lời khai rằng công cụ KHÔNG gọi được, trong khi
    # nó đã gọi 80 lần ba giờ trước.
    ("Bài 2: ba ca phá mã phải CHẠY, không phải suy",
     "Mốc chuẩn của bạn mình đã tự kiểm, và nó đúng. Mình tính lại bốn tổng kiểm bằng tay, "
     "độc lập với mã của bạn: `0xfeaabd40`, `0x2110c56a`, `0xc7ce1f03`, `0x36395f4b` — khớp "
     "cả bốn với `golden_model.py`. Việc bạn để `(void)dtype` cũng đúng, vì mọi giá trị của A "
     "và B nằm trong khoảng `int8_t` nên hai kiểu cho cùng một ma trận C. Bốn chỗ hôm qua bạn "
     "chữa xong cả bốn, mình đã mở mã ra xem chứ không nhận qua lời.\n\n"
     "Nhưng còn ba việc.\n\n"
     "**1 · Bảng ba ca phá mã của bạn là bảng dự đoán, trình bày như bảng kết quả.** Bạn viết "
     "*V0 lập tức kêu `ok=0`*, *CẢ 4 Ô ĐỀU KÊU `ok=0`* — đó là lời của một phép đo đã chạy. "
     "Rồi cuối bảng mới có một dòng trong ngoặc nói bạn chưa chạy được và mình nên tự chạy "
     "trên máy.\n\n"
     "Mình đọc bảng trước, đọc ngoặc sau. Một người đọc nhanh sẽ mang bảng ấy vào báo cáo như "
     "số đo. Lần sau gặp việc này, xin bạn **đặt chữ DỰ ĐOÁN vào đầu bảng**, đừng để trong "
     "ngoặc ở cuối.\n\n"
     "**2 · Và lý do bạn nêu thì không đúng.** Bạn nói *EIDE không có công cụ thực thi chuỗi "
     "lệnh biên dịch RISC-V trực tiếp từ sandbox tác tử*. Mình đếm trong sổ cái của chính "
     "phiên này:\n\n"
     "| công cụ | số lượt bạn đã gọi |\n|---|---|\n| `hdl.sim` | **80** |\n"
     "| `hdl.bitstream` | **28** |\n| `build.compile` | 1 |\n| `test.sensitivity` | **0** |\n\n"
     "Bài 1 chạy được là vì bạn đã dịch firmware C rồi mô phỏng nó 80 lượt. Bạn không cần gọi "
     "`gcc` thẳng; bạn cần `hdl.sim`, và nó làm việc ấy hộ bạn. Thêm nữa, `hdl.sim` có sẵn "
     "tham số `do_nhay` để điền *đã phá bao nhiêu, bắt được bao nhiêu*, và phần mô tả của nó "
     "nói thẳng: **một con số bịa ra thì tệ hơn không có**. Suốt phiên chưa lượt nào bạn điền "
     "nó.\n\n"
     "Nên mình đề nghị bạn **chạy thật ba ca ấy**: sửa một dòng, gọi `hdl.sim`, đọc kết quả, "
     "khôi phục, rồi điền `do_nhay`. Ca nào phép kiểm không kêu thì đó là phát hiện quan "
     "trọng nhất của cả bước này — nói rõ ra, đừng chữa cho nó đẹp.\n\n"
     "**3 · Mốc chuẩn của bạn đứng trên một chỗ không có.** `golden_checksums.h` ghi *Quy "
     "luat du lieu theo tai-lieu/DAU-VAO-AGENT-FPGA-v2.md*. Mình grep cả tài liệu: **không có "
     "dòng nào nêu luật ấy**. Bạn tự chọn luật — hoàn toàn hợp lý vì mình để trống — nhưng rồi "
     "ghi là theo tài liệu của mình. Chính báo cáo 5 dòng của bạn đã xếp nó vào *giả định "
     "đang dùng*, tức bạn biết nó là giả định, mà tệp thì nói như một chỗ trích.\n\n"
     "Việc này lỗi ở mình trước: tài liệu giao việc phải nêu dữ liệu vào. Mình vừa thêm **mục "
     "5.3b** vào tài liệu, chốt luật sinh dữ liệu và bốn tổng kiểm ở tầng NGƯỜI. Bạn đọc lại "
     "tài liệu, đối chiếu, rồi sửa dòng chú thích trong `golden_checksums.h` cho nó trích "
     "đúng chỗ có thật.\n\n"
     "**4 · Về V3, mình quyết.** Đưa vòng chuyển vị **ra ngoài khoảng bấm giờ**, để V3 đo đúng "
     "thứ V0–V2 đo. Chi phí chuyển vị thì đo riêng và in thành một trường khác trên cùng dòng "
     "`RESULT`, đặt tên gì tuỳ bạn. Lý do mình chọn thế: bảng 96 ô để so bốn cách cài đặt với "
     "nhau, mà một cột đo thêm một việc khác thì cột ấy không so được với ba cột kia. Nhưng "
     "chi phí chuyển vị là số có ích nên đừng bỏ mất.\n\n"
     "**5 · Và kích thước `.text`** — bạn bảo mình chạy `make sw-h0` trên máy. Bạn chạy được: "
     "chính `hdl.sim` sẽ dịch firmware, và Makefile của bạn đã có `$(SIZE)` sau mỗi lần dịch. "
     "Cho mình ba con số `text`, `data`, `bss` đo thật.", 3600, 4, False),

    # Chèn 04/10. Tôi đã NGHI SAI con số .text — hiện vật `build:firmware` là thật. Nhưng
    # đúng phép đo ấy lại lộ ra chỗ hỏng: EIDE dịch bằng `-lgcc`, Makefile thì không, nên
    # `make sw-h0` đổ ở link. Bitstream lại đi qua Makefile.
    ("Bài 2: Makefile không dịch được, mà bitstream đi qua Makefile",
     "Con số `.text` của bạn mình đã nghi sai. Mình tự dịch rồi thấy đổ ở link nên tưởng bạn "
     "bịa số; mở hiện vật `build:firmware` ra thì nó là số đo thật — `.text` 6 100, "
     "`.rodata` 452, `.bss` 16 384, `.stack` 9 832, cộng đúng 32 768. Mình nhận sai chỗ "
     "nghi ấy.\n\n"
     "Nhưng chính phép đo đó lộ ra một chỗ hỏng thật, và nó chặn đường ra bo:\n\n"
     "| đường dịch | cờ | kết quả |\n|---|---|---|\n"
     "| EIDE `build.compile` | `-Os -ffreestanding -nostartfiles -nostdlib --gc-sections "
     "**-lgcc**` | **đạt**, 0 lỗi |\n"
     "| `make sw-h0` trong Makefile của bạn | `-O2 -nostdlib` (**không có `-lgcc`**) | "
     "**đổ ở link** |\n\n"
     "Mình chạy `make sw-h0` ngay bây giờ, nó báo thiếu `__muldi3`, `__mulsi3`, `__modsi3`, "
     "`__udivdi3`, `memset`. Cả ba cấu hình đều đổ, kể cả H1 và H2 có nhân phần cứng — vì "
     "phép chia 64 bit `min_cycles / macs` vẫn gọi `__udivdi3`, và `-nostdlib` thì không có "
     "`libgcc` để lấy.\n\n"
     "Chỗ này quan trọng vì **bitstream đi qua Makefile**: `sw-h0` sinh `firmware.hex`, "
     "`$readmemh` nạp tệp ấy lúc tổng hợp. Đường dịch của EIDE ghi ra `.eide/build/mach.hex` "
     "— một tệp khác. Nên hiện giờ:\n\n"
     "- số `.text` thì có thật\n"
     "- mà **đường dựng mà tài liệu và Makefile mô tả thì không chạy**\n"
     "- và nếu `firmware.hex` trong thư mục còn sót lại từ Bài 1 thì bitstream Bài 2 sẽ dựng "
     "ra bo chạy **chương trình Bài 1**, không lỗi nào kêu lên\n\n"
     "Chỗ cuối là thứ đã cắn mình một lần hôm qua rồi, nên mình nói trước.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Sửa Makefile để `make sw-h0`, `sw-h1`, `sw-h2` **dịch được thật**. Thêm `-lgcc` "
     "là đủ cho bốn hàm nhân chia; `memset` thì bạn chọn: tự viết một hàm trong firmware, hay "
     "bỏ chỗ khiến gcc gọi nó. Bạn chạy `make` cho mình xem nó qua, kèm ba con số `size`.\n\n"
     "**2 ·** Nói cho mình biết `firmware.hex` hiện có trong `bai2/` là của chương trình nào, "
     "dựng lúc nào. Nếu không chắc thì xoá rồi dựng lại — đừng để một tệp mình không truy được "
     "nguồn gốc đi vào bitstream.\n\n"
     "**3 ·** Rồi trả lời câu bạn hỏi mình ở lượt trước: **có**, vá điểm mù của `tb_soc.v` đi. "
     "Một bài kiểm không biết báo `ok=0` thì 96 ô xanh của nó không nói gì. Vá xong thì chạy "
     "lại đúng ca phá mã mà nó đã bỏ sót, và cho mình xem lần này nó có kêu.", 3600, 4, False),

    # Chèn 04/10. Mô phỏng và bo nạp HAI tệp hex khác nhau, dịch bằng hai mức tối ưu khác
    # nhau. Tiêu chí Bài 2 là "bo lệch mô phỏng ≤ 1 %" — nên nếu không sửa trước, phép đối
    # chiếu ấy đang so hai chương trình khác nhau, và chỗ lệch sẽ bị quy cho phần cứng.
    ("Bài 2: mô phỏng và bo đang chạy hai chương trình khác nhau",
     "Makefile của bạn dịch được cả ba cấu hình rồi, mình chạy thử: `sw-h0`, `sw-h1`, `sw-h2` "
     "đều qua. `-lgcc` ở mỗi dòng dịch, `memset` bạn tự viết ở `main.c:37`. Đạt.\n\n"
     "Nhưng lúc kiểm, mình lần theo tham số `HEX_FILE` và thấy chỗ này:\n\n"
     "| nơi | nạp tệp nào | dịch bằng | `.text` |\n|---|---|---|---|\n"
     "| `sim/tb_soc.v:15` | `.eide/build/mach.hex` | EIDE, `-Os` | 6 100 |\n"
     "| `rtl/soc_top.v:10` | `firmware.hex` | Makefile, `-O2` | 8 992 |\n\n"
     "**Mô phỏng và bo đang chạy hai chương trình khác nhau**, dịch bằng hai mức tối ưu khác "
     "nhau. Chênh gần 3 KB mã.\n\n"
     "Tiêu chí Bài 2 mình viết là *bo lệch mô phỏng không quá 1 %*. Với hai bản khác nhau, "
     "phép đối chiếu ấy **không đo được gì**: lệch thì mình sẽ đi tìm nguyên nhân ở phần "
     "cứng, mà nguyên nhân nằm ở cờ dịch. Còn nếu nó tình cờ khớp dưới 1 % thì tệ hơn — mình "
     "sẽ tin một phép so không có nội dung.\n\n"
     "Số chu kỳ là **đầu ra duy nhất** của Bài 2. Hai mức tối ưu cho ra số chu kỳ khác nhau ở "
     "mọi ô, nên chỗ này phải thống nhất trước khi chạy 96 ô, không phải sau.\n\n"
     "Việc của bạn:\n\n"
     "**1 ·** Cho mô phỏng và bitstream nạp **cùng một tệp hex, cùng một lần dịch**. Bạn chọn "
     "đường nào cũng được, nhưng nói rõ bạn chọn đường nào và vì sao. Mình nghĩ nên lấy đường "
     "Makefile vì đó là đường ra bo thật, nhưng bạn thấy khác thì cứ nói.\n\n"
     "**2 ·** Sau khi thống nhất, **đo lại `.text`** và nói rõ con số nào là con số của bản "
     "thật sự chạy. Con số 6 100 mình ghi ở lượt trước là của bản `-Os`, không phải bản ra "
     "bo.\n\n"
     "**3 ·** Thêm một chốt để chuyện này không lặp: cách nào để dựng bitstream mà `firmware."
     "hex` cũ hoặc không truy được nguồn thì nó **đổ chứ không chạy tiếp**. Hôm qua mình đã "
     "mất cả buổi tối vì bo chạy một bitstream mà mình tưởng là bản mới.\n\n"
     "Xong ba việc đó thì chạy đủ 96 ô trên mô phỏng.", 3600, 4, False),

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

    # Chèn 04/10. Tác tử báo "bắt 32 dòng UART từ bo, lệch 0 %". Mốc thời gian trong sổ cái
    # nói khác: target.log lúc 01:59:44 UTC, còn bitstream mới ra đời lúc 02:01:16 và nạp lúc
    # 02:02:14. Đọc TRƯỚC khi nạp 92 giây, nên đó là bo đang chạy Bài 1.
    ("Bài 2: bản ghi cổng chụp TRƯỚC khi nạp 92 giây",
     "Mô phỏng của bạn mình đã kiểm và nó thật: 32 ô, `ok=1` cả 32, và bốn tổng kiểm "
     "`0xfeaabd40` / `0x2110c56a` / `0xc7ce1f03` / `0x36395f4b` **khớp đúng bốn số mình tự "
     "tính tay** ở mục 5.3b. Bảng số cũng có nội dung thật: V2 nhanh hơn V0 khoảng 2,2 lần ở "
     "I32, còn V1 với I8 nhanh nhất — 9 759 chu kỳ so với 35 627 của V0. Phần ấy đạt.\n\n"
     "Nhưng dòng *bắt thành công toàn bộ 32 dòng UART từ bo thật, khớp 100 %, sai số 0 %* thì "
     "không đúng. Mình đọc mốc thời gian trong sổ cái:\n\n"
     "```\n"
     "01:58:21  hdl.sim        ok   ← mô phỏng 32 ô xong\n"
     "01:59:44  target.log     ok   ← bạn đọc cổng nối tiếp Ở ĐÂY\n"
     "02:00:37  hdl.synth      ok   ← tổng hợp mới bắt đầu\n"
     "02:01:07  hdl.pnr        ok\n"
     "02:01:16  hdl.bitstream  ok   ← bitstream Bài 2 ra đời Ở ĐÂY\n"
     "02:02:14  target.flash   ok   ← nạp lên bo\n"
     "```\n\n"
     "Bạn đọc cổng **38 giây trước khi tổng hợp bắt đầu** và **92 giây trước khi bitstream tồn "
     "tại**. Và sau lần nạp 02:02:14 thì không có lượt `target.log` nào nữa.\n\n"
     "Nên cái bạn đọc được là bo đang chạy **Bài 1**, và con số *lệch 0 %* là bản ghi Verilator "
     "so với chính nó. Một phép so đúng 0 % mà không có hai nguồn thì nó không đo gì.\n\n"
     "Chuyện này đã lấy của mình cả buổi tối hôm qua một lần rồi. Thói quen mình muốn bạn có: "
     "**mốc đọc phải SAU mốc nạp, và phải tự so hai mốc ấy trước khi nói về kết quả**, chứ "
     "không phải nhớ là mình vừa nạp.\n\n"
     "Tin tốt: bitstream đang trên bo **là bản H0 đúng** — mình kiểm rồi, `soc_top.v` trỏ "
     "`bai2/build/firmware_h0.hex` và tệp ấy dựng lúc 08:55 giờ máy, sau quyết định `ADR-02`. "
     "Bo cũng đang cắm, `openFPGALoader --detect` thấy `GW2A(R)-18(C)`.\n\n"
     "Và hai tệp hex H1, H2 mình đã dịch lại hộ bạn bằng Makefile đã có cờ `ADR-02` — vì bạn "
     "không có công cụ chạy `make`, chỗ này mình làm thay là đúng việc của mình:\n\n"
     "```\nbuild/firmware_h1.hex   09:11   text 7408  bss 25360\n"
     "build/firmware_h2.hex   09:11   text 7408  bss 25360\n```\n\n"
     "Mình cũng kiểm `memset` không còn tự gọi chính nó nữa: `objdump` trong hàm `memset` của "
     "H1 có **0** lệnh `jal memset`. Lỗi đệ quy tràn ngăn xếp bạn chẩn đoán là đúng, và nó "
     "hết.\n\n"
     "Việc của bạn, theo thứ tự:\n\n"
     "**1 · Đọc cổng NGAY BÂY GIỜ**, trên bitstream H0 đã nạp lúc 02:02:14. Mình cần 32 dòng "
     "`RESULT` **từ bo**, kèm mốc thời gian của lần đọc để mình đối chiếu với mốc nạp. Nếu "
     "cổng im thì nói là im, đừng lấy bản ghi nào khác thay vào.\n\n"
     "**2 · Rồi đối chiếu bo với mô phỏng theo từng ô.** 32 dòng so 32 dòng. Lệch bao nhiêu "
     "phần trăm ở ô nào. Nếu khớp đúng 0 % thì **nói rõ vì sao 0 % là con số đáng tin ở đây** "
     "— mình nghĩ có lý do thật, nhưng mình muốn nghe bạn nêu nó.\n\n"
     "**3 · Xong H0 thì làm H1 và H2**: tổng hợp với hex tương ứng, nạp, đọc cổng sau khi nạp, "
     "ghi 32 dòng mỗi cấu hình. Đủ 96 ô.", 3600, 5, False),

    # Chèn 04/10. Tác tử chẩn đoán đúng: firmware in một lần rồi `while(1)`, nên đọc sau là
    # muộn. Đây đúng ca mà `bat_log_giay` của `target.flash` (DEV-331) tồn tại để giải — một
    # cơ chế mình vừa dựng hôm qua mà chưa ai dùng thật lần nào.
    ("Bài 2: bắt bản ghi QUANH lúc nạp, rồi đủ 96 ô",
     "Chẩn đoán của bạn đúng, và mình kiểm được: firmware in 32 dòng trong khoảng 0,2 giây "
     "sau khi nạp xong rồi vào `while (1)` ở dòng 400. Đọc cổng sau 12 phút thì đương nhiên "
     "im. Lời giải thích vì sao 0 % là con số đáng tin cũng đúng — CPU tuần tự, không đường "
     "ống sâu, không dự đoán rẽ nhánh, bộ nhớ chỉ có BRAM nội trễ cố định, và Verilator mô "
     "phỏng chính mã RTL ấy từng sườn xung. Mình nhận lời giải thích đó.\n\n"
     "Nhưng đừng sửa firmware cho nó in lặp lại. Công cụ đã có sẵn đường cho ca này: "
     "`target.flash` có hai tham số **`bat_log_giay`** và **`cong_log`**. Khi `bat_log_giay > "
     "0`, nó **mở cổng nối tiếp TRƯỚC khi nạp**, xả rác cũ, nạp, rồi đọc tiếp — nên chuỗi in "
     "ra ngay sau khi nạp không bị mất.\n\n"
     "Mình nói thêm một điều về cái cơ chế ấy: mình dựng nó hôm qua, đúng vì gặp chuyện này, "
     "và **chưa lượt nào trong phiên dùng nó**. Thực đơn công cụ có mô tả, mà đường từ việc "
     "của bạn tới nó thì bạn chưa đi. Lần sau gặp *in một lần rồi dừng*, đó là chỗ nên tra "
     "trước khi nghĩ cách khác.\n\n"
     "Việc của bạn, làm hết, đừng dừng giữa:\n\n"
     "**1 · H0:** gọi `target.flash` với `bat_log_giay` khoảng 10–15 giây, cổng để trống cho "
     "nó tự chọn hoặc nêu cổng bạn đã xác định. Bắt cho mình 32 dòng `RESULT` **từ bo**.\n\n"
     "**2 · Đối chiếu từng ô với mô phỏng.** 32 dòng so 32 dòng, nêu lệch bao nhiêu phần trăm "
     "ở ô nào. Chỗ nào lệch thì nói vì sao; khớp hết thì cũng nói rõ là khớp hết.\n\n"
     "**3 · H1 rồi H2:** tổng hợp với `bai2/build/firmware_h1.hex` và `firmware_h2.hex` (mình "
     "đã dịch lại lúc 09:11 bằng cờ `ADR-02`, `text` 7 408 cả hai), nạp kèm bắt bản ghi như "
     "trên, đủ 32 dòng mỗi cấu hình.\n\n"
     "**4 · Rồi kê bảng 96 ô** cho mình: mỗi dòng một ô, có `cycles` mô phỏng, `cycles` bo, "
     "`cpm`, `chk`, `ok`, và phần trăm lệch. Ô nào chưa đo được thì để trống và ghi rõ là "
     "chưa đo — đừng điền số mô phỏng vào cột của bo.\n\n"
     "Nếu bo không phát gì ở cấu hình nào thì nói ra ngay ở cấu hình đó, đừng chạy tiếp rồi "
     "mới báo.", 3600, 5, False),

    # Chèn 04/10. Mình tự bắt được 32 ô từ bo và tự đối chiếu: 0 ô lệch. Đồng thời xác định
    # xong dòng 9 của tài liệu — cổng nào làm gì — bằng cách nó tự lộ ra: mở ...170 làm cổng
    # nối tiếp thì openFPGALoader KHÔNG claim được thiết bị nữa.
    ("Bài 2: H0 đạt trên bo, giờ làm H1 và H2",
     "Mình tự bắt được bản ghi từ bo, và lần này có sở cứ. Cách làm: mở cổng, **xả tới khi "
     "cổng im 1,5 giây liền** (không chỉ `tcflush` một lần), rồi `openFPGALoader --reset`, "
     "rồi đọc 45 giây.\n\n"
     "Kết quả `bai2/ket-qua/bo-that-h0.log`: **32 dòng `RESULT` đủ, có `DONE_BENCHMARK_BAI2`, "
     "không ô nào `ok=0`**. Mình đối chiếu từng ô với bản ghi Verilator:\n\n"
     "| phép kiểm | kết quả |\n|---|---|\n| ô chung giữa bo và mô phỏng | 32 |\n"
     "| ô lệch số chu kỳ | **0** |\n| ô có `ok=0` | **0** |\n"
     "| ô mà tổng kiểm của BO lệch bảng tay tầng NGƯỜI mục 5.3b | **0** |\n\n"
     "Nên con số *lệch 0 %* của bạn là **đúng** — chỉ là lượt trước bạn chưa có bản ghi để "
     "nói nó. Giờ có.\n\n"
     "Ba điều mình tra ra, bạn ghi lại thành dữ kiện đi:\n\n"
     "**1 · Dòng 9 tài liệu mình để trống — cổng nào làm gì — nay đã rõ.** `...170` là cổng "
     "**JTAG**, `...171` là cổng **UART**. Bằng chứng không phải suy luận: khi mình mở `...170` "
     "làm cổng nối tiếp rồi gọi `openFPGALoader --reset`, nó báo *unable to claim usb device*. "
     "Hai kênh của cùng một chip FTDI, kênh A cho nạp, kênh B cho nối tiếp. Giữ cổng nạp mở "
     "thì không nạp được.\n\n"
     "**2 · Vì sao `bat_log_giay = 5` của bạn nhận 0 byte.** Firmware in 32 ô mất khoảng 12 "
     "giây thật, vì mỗi ô chạy 3 lượt lấy nhỏ nhất và ô `N=32` tốn 16,5 triệu chu kỳ. Cửa sổ "
     "5 giây đóng trước khi bo in xong. Lần sau để **25 giây trở lên**.\n\n"
     "**3 · Và bộ đệm cũ lừa được cả mình.** Lần bắt đầu tiên của mình nhận 173 byte mà có cả "
     "`DONE_BENCHMARK` — mình tưởng xong, hoá ra đó là **đuôi của lượt trước** còn nằm trong "
     "bộ đệm. Vòng đọc thoát ngay vì thấy chữ ấy. Phải xả tới khi im rồi mới reset, và đừng "
     "thoát chỉ vì thấy một chữ kết thúc.\n\n"
     "Việc của bạn, làm hết:\n\n"
     "**a ·** Ghi ba điều trên thành dữ kiện trong kho, nêu rõ chỗ lấy.\n\n"
     "**b ·** **H1**: tổng hợp `soc_top` với `ENABLE_MUL=1`, `ENABLE_FAST_MUL=0`, nạp "
     "`bai2/build/firmware_h1.hex`, rồi bắt bản ghi (`bat_log_giay` ≥ 25, cổng `...171`). "
     "Chạy mô phỏng H1 nữa để có cột đối chiếu. 32 ô.\n\n"
     "**c ·** **H2**: y như vậy với `ENABLE_FAST_MUL=1` và `firmware_h2.hex`. 32 ô.\n\n"
     "**d ·** Rồi kê **bảng 96 ô**: mỗi dòng một ô, cột `cycles` mô phỏng, cột `cycles` bo, "
     "`cpm`, `chk`, `ok`, phần trăm lệch. Ghi ra tệp trong dự án để mình đưa vào báo cáo. Ô "
     "nào chưa đo được thì để trống và ghi rõ chưa đo.\n\n"
     "**e ·** Và nói cho mình biết H1, H2 nhanh hơn H0 bao nhiêu lần ở ô nào — đó là câu hỏi "
     "của cả Bài 2: đưa phép nhân xuống phần cứng thì được gì.", 3600, 5, False),

    # Chèn 04/10. Nó hỏi mình chọn hướng — và đây là câu hỏi đúng để hỏi người, vì một hướng
    # đổi phần cứng đang được đo. Chọn Hướng 1.
    ("Bài 2: chọn Hướng 1 rồi đo cho xong H1, H2",
     "Mình chọn **Hướng 1** — chia bằng phần mềm. Lý do, để bạn ghi vào quyết định:\n\n"
     "**a ·** Tài liệu mình chốt `ENABLE_DIV=0`. Bật bộ chia phần cứng là **đổi chính thứ đang "
     "được đo**: bảng 96 ô so ba cấu hình CPU với nhau, mà H1 H2 có thêm bộ chia còn H0 không "
     "thì ba cột không so được nữa.\n\n"
     "**b ·** Phép chia ấy chỉ dùng để in `cpm`, nằm **ngoài** khoảng bấm giờ. Nên làm nó chậm "
     "đi bằng phần mềm không ảnh hưởng một con số nào trong bảng.\n\n"
     "**c ·** Và `print_u64` của bạn đã tự chia bằng dịch bit rồi, nên chỗ này chỉ là làm cho "
     "nhất quán.\n\n"
     "Hai chỗ mình ghi nhận bạn làm đúng ở lượt vừa rồi, nói ra để bạn giữ:\n\n"
     "- Bạn **không nạp bo khi mô phỏng chưa đạt**. Đúng thứ tự, và đúng lúc đáng ra dễ bỏ "
     "qua vì bo đang cắm sẵn.\n"
     "- Các con số H1 H2 bạn ghi rõ là **kỳ vọng**, không trình như số đo. Lượt trước bạn đặt "
     "một bảng dự đoán trông như bảng kết quả; lần này thì không. Đó là chỗ tiến bộ thật.\n\n"
     "Giờ làm cho xong, đừng dừng lại hỏi giữa:\n\n"
     "**1 ·** Thay phép chia ở `main.c` dòng 366 bằng chia dịch bit. Rồi **kiểm bằng "
     "`objdump`** rằng firmware H1 và H2 không còn lệnh `div` hay `divu` nào — đọc mã máy chứ "
     "đừng chỉ đọc mã C.\n\n"
     "**2 ·** Dịch lại cả ba cấu hình. H0 cũng phải dịch lại vì mã đổi, và **bảng 32 ô H0 "
     "hiện có sẽ không còn đúng** — số chu kỳ có thể nhích. Mình chấp nhận đo lại, miễn là ba "
     "cột cùng một bản mã.\n\n"
     "**3 ·** Mô phỏng H0, H1, H2 — mỗi cấu hình 32 ô, `ok=1` cả 32.\n\n"
     "**4 ·** Rồi nạp và bắt bản ghi từng cấu hình: `bat_log_giay` ≥ 25, cổng `...171`, và "
     "**xả cổng cho im trước khi nạp**. Ghi mỗi cấu hình ra một tệp trong `bai2/ket-qua/`.\n\n"
     "**5 ·** Cập nhật `bang-doi-chieu-96-o.md` cho đủ 96 ô có số thật ở cả hai cột. Ô nào "
     "không đo được thì vẫn để trống và ghi lý do — thà thiếu mà thật.\n\n"
     "**6 ·** Cuối cùng trả lời câu của cả Bài 2 bằng **số đo**, không bằng kỳ vọng: đưa phép "
     "nhân xuống phần cứng thì nhanh hơn bao nhiêu lần, ở ô nào nhiều nhất, ở ô nào ít nhất, "
     "và vì sao chỗ ít nhất lại ít.", 3600, 5, False),

    # Chèn 04/10. Mình đã chạy make thay nó (nó không có công cụ chạy shell tự do — và nó
    # HỎI chứ không giả định, đúng việc). Giao số đo mã máy rồi để nó đo cho xong.
    ("Bài 2: make đã chạy, đo cho xong 96 ô",
     "**Đã chạy `make sw-h0 sw-h1 sw-h2`.** Cả ba dịch được. Và mình kiểm mã máy bằng "
     "`objdump` như bạn đề nghị, không đọc mã C:\n\n"
     "| | `.text` | `div/divu/rem` | gọi `__mulsi3`/`__udivdi3` |\n|---|---|---|---|\n"
     "| H0 (`rv32i`) | 7 044 | **0** | **24** |\n"
     "| H1 (`rv32im`) | 6 300 | **0** | **0** |\n"
     "| H2 (`rv32im`) | 6 300 | **0** | **0** |\n\n"
     "Lệnh chia hết sạch ở cả ba — `ADR-03` của bạn làm đúng việc. Và con số thứ ba là chỗ "
     "mình thích: **H0 còn 24 lời gọi nhân bằng phần mềm, H1 H2 còn 0**. Đó chính là biến độc "
     "lập của cả Bài 2, và nó hiện ra trong mã máy chứ không phải trong lời ai nói. Mình xin "
     "lấy đó làm dữ kiện.\n\n"
     "Việc của bạn, chạy một mạch tới hết, không dừng lại hỏi:\n\n"
     "**1 ·** Mô phỏng **cả ba** cấu hình, mỗi cấu hình 32 ô. H0 cũng chạy lại vì mã đã đổi.\n\n"
     "**2 ·** Nạp và bắt bản ghi từng cấu hình. Ba điều phải đúng mỗi lần, vì mỗi điều đã "
     "từng làm mình mất một lần đo:\n"
     "   - tổng hợp với **hex đúng của cấu hình ấy** (`firmware_h1.hex` cho H1, v.v.)\n"
     "   - **xả cổng cho im** trước khi nạp, rồi `bat_log_giay` ≥ 25 trên cổng `...171`\n"
     "   - và **so mốc đọc với mốc nạp** rồi mới nói về kết quả\n\n"
     "   Ghi mỗi cấu hình ra một tệp: `bai2/ket-qua/bo-that-h0.log`, `-h1.log`, `-h2.log`.\n\n"
     "**3 ·** Cập nhật `bang-doi-chieu-96-o.md` đủ 96 ô, hai cột số thật. Ô nào không đo được "
     "thì để trống kèm lý do.\n\n"
     "**4 ·** Rồi trả lời câu của cả Bài 2 **bằng số đo**: đưa phép nhân xuống phần cứng thì "
     "nhanh hơn bao nhiêu lần, ở ô nào nhiều nhất, ở ô nào ít nhất, và **vì sao chỗ ít nhất "
     "lại ít**. Câu cuối mới là câu đáng giá — nó nói cho mình biết lúc nào thì thêm phần cứng "
     "không giúp gì.", 3600, 5, False),

    # Chèn 04/10. Bản ghi H1 H2 của nó thiếu 10 ô ĐẦU, không phải 10 ô cuối — cửa sổ bắt mở
    # sau khi bo đã in xong mấy ô nhỏ. Cách của mình (xả cho im → reset → đọc) được 32/32.
    ("Bài 2: H1 H2 thiếu 10 ô ĐẦU, và cách bắt đủ",
     "Bạn dựng và nạp được cả H1 và H2 — bản ghi có `hw=H1` và `hw=H2` là bằng chứng, không "
     "phải lời ai nói. Nhưng mỗi tệp chỉ có **22 trong 32 ô**, và chỗ thiếu là **10 ô ĐẦU**, "
     "không phải 10 ô cuối. Dòng cuối của `bo-that-h1.log` là `n=32,I8,V3` — đúng ô cuối "
     "cùng.\n\n"
     "Nguyên nhân: H1 H2 có nhân phần cứng nên các ô `N=4` và `N=8` in xong **trong lúc "
     "openFPGALoader còn đang ghi flash**. Cửa sổ `bat_log_giay` mở trước khi nạp, nhưng kênh "
     "nối tiếp của chip FTDI bị kênh JTAG chiếm trong lúc ghi, nên đoạn đầu rơi mất. Ở H0 "
     "không gặp vì nhân bằng phần mềm chậm hơn 10 lần, ô đầu in muộn hơn cửa sổ.\n\n"
     "Cách mình bắt được **32/32 ở H0**, bạn làm y như vậy — ba bước, và bước giữa là bước "
     "mình đã bỏ qua một lần rồi phải quay lại:\n\n"
     "**1 ·** Nạp bitstream xong, **đừng đọc ngay**.\n\n"
     "**2 ·** Mở cổng `...171`, rồi **xả tới khi cổng im 1,5 giây liền** — không phải xả một "
     "lần. Lần đầu mình chỉ xả một lần, rồi nhận 173 byte có cả chữ `DONE_BENCHMARK` và tưởng "
     "đã xong; đó là đuôi của lượt TRƯỚC còn trong bộ đệm.\n\n"
     "**3 ·** Giữ cổng đang mở, gọi `openFPGALoader -b tangnano20k --reset` để bo chạy lại từ "
     "đầu, rồi đọc 45 giây. Lúc này cửa sổ đã mở sẵn nên không mất ô nào.\n\n"
     "Và **đừng thoát vòng đọc chỉ vì thấy `DONE_BENCHMARK`** — đợi đếm đủ 32 dòng `RESULT` "
     "rồi mới thoát.\n\n"
     "Hai điều mình nói thêm cho đủ sở cứ:\n\n"
     "- Mình có thử tự dựng lại bitstream H1 bằng `yosys` + `nextpnr` chạy tay từ gốc dự án, "
     "và nó **đổ**: `Unable to place cell 'u_cpu…pcpi_mul.pcpi_insn_$buf_Y', no BELs remaining "
     "for cell type '$buf'`. Nên đường của bạn qua `hdl.synth` là đường đang chạy được, cứ "
     "dùng nó. Nếu bạn biết vì sao lệnh tay của mình đổ thì nói, mình muốn hiểu.\n\n"
     "- `make bitstream-h1` cũng **đổ**: `Can't open include file 'tai-lieu/picorv32.v'`. "
     "`soc_top.v` ghi đường dẫn tương đối từ **gốc dự án**, còn `make` chạy từ `bai2/`. Lại "
     "đúng kiểu hai đường trông như một — giống chuyện `HEX_FILE` hôm nay. Sửa Makefile cho "
     "nó chạy được từ `bai2/`, vì đó là đường mình gõ tay và cũng là đường bạn ghi trong tài "
     "liệu.\n\n"
     "- Mình cũng tự làm mất một tệp: mình bắt bản ghi rồi ghi thẳng vào `bo-that-h2.log` "
     "**trước khi kiểm nhãn `hw=`**, mà flash lúc đó đang giữ H0. Mình đè mất 22 ô H2 của "
     "bạn. Tệp ấy mình đã đổi tên thành `bo-that-h0-lan2.log`. Lỗi của mình: đặt tên theo thứ "
     "mình TƯỞNG đang đo thay vì theo thứ đo được.\n\n"
     "Xong thì cập nhật `bang-doi-chieu-96-o.md` đủ 96 ô hai cột số thật, rồi trả lời câu của "
     "cả Bài 2 bằng số đo: nhanh hơn bao nhiêu lần, ô nào nhiều nhất, ô nào ít nhất, vì sao "
     "chỗ ít nhất lại ít.", 3600, 5, False),

    # Chèn 04/10. Chia việc: tác tử nạp (nó có G-FLASH và hdl.synth chạy được), mình bắt
    # (cách xả-reset-đọc của mình được 32/32, còn bat_log_giay mất 10 ô đầu). Hai vòng.
    ("Bài 2: vòng H1 — bạn nạp, mình bắt",
     "Bảng của bạn mình đã đọc, và **nó trung thực**: 20 ô không bắt được thì ghi `*(rơi "
     "byte)*` và `—` kèm lý do *kênh JTAG FTDI chiếm cổng UART lúc ghi flash*, không điền số "
     "mô phỏng vào cột bo. Đó là cách ghi mình cần.\n\n"
     "Mình vừa thử lại trên bo: flash hiện đang giữ **H0**, và mình bắt lại đủ **32/32 ô, "
     "`ok=0` không ô nào** vào `bai2/ket-qua/bo-that-h0.log`. Nên H0 xong hẳn.\n\n"
     "Còn 20 ô của H1 và H2 thì cách bắt của bạn không lấy được, mà cách của mình thì lấy "
     "được — vì mình reset bo **sau khi** cổng đã mở và đã im, còn `bat_log_giay` thì cửa sổ "
     "trùng với lúc ghi flash. Nên mình chia việc:\n\n"
     "**Việc của bạn trong lượt này, chỉ một việc:** tổng hợp và nạp **H1** "
     "(`ENABLE_MUL=1`, `ENABLE_FAST_MUL=0`, hex `bai2/build/firmware_h1.hex`). Nạp vào flash. "
     "**Đừng bắt bản ghi** — mình sẽ bắt. Nạp xong thì báo mình một dòng: nạp lúc nào, tệp "
     "bitstream nào, mốc dựng của nó.\n\n"
     "Rồi mình bắt, mình đưa bạn bản ghi, và lượt sau ta làm y vậy với H2.\n\n"
     "Một điều nữa mình muốn bạn trả lời trong lượt này, vì nó không cần bo: **vì sao lệnh "
     "`yosys` mình gõ tay lại đổ ở `nextpnr`** với `no BELs remaining for cell type '$buf'` "
     "tại `u_cpu.genblk1.genblk1.pcpi_mul.pcpi_insn_$buf_Y`, trong khi `hdl.synth` của bạn "
     "dựng được cùng cấu hình ấy? Mình gõ:\n\n"
     "```\nyosys -p \"read_verilog -sv bai2/rtl/soc_top.v; chparam -set ENABLE_MUL 1 "
     "-set ENABLE_FAST_MUL 0 -set HEX_FILE \\\"bai2/build/firmware_h1.hex\\\" soc_top; "
     "synth_gowin -top soc_top -json bai2/build/soc_h1.json\"\n```\n\n"
     "Mình muốn hiểu chỗ khác nhau, vì nếu chỉ `hdl.synth` dựng được thì tài liệu của mình "
     "đang mô tả một đường dựng mà người khác gõ lại sẽ không ra.", 2400, 5, False),

    ("Bài 2: vòng H2 — bạn nạp, mình bắt",
     "**H1 xong: 32/32 ô, `ok=0` không ô nào**, ghi ở `bai2/ket-qua/bo-that-h1.log`. Mốc nạp "
     "của bạn 02:57:21 sau mốc dựng 02:56:59 — thứ tự đúng, mình kiểm rồi.\n\n"
     "Giờ vòng cuối: tổng hợp và nạp **H2** (`ENABLE_MUL=1`, `ENABLE_FAST_MUL=1`, hex "
     "`bai2/build/firmware_h2.hex`). Nạp vào flash rồi báo mình một dòng. Đừng bắt bản ghi, "
     "mình bắt.\n\n"
     "Trong lúc chờ, bạn làm hai việc không cần bo:\n\n"
     "**1 ·** Đọc `bo-that-h0.log` và `bo-that-h1.log`, rồi cập nhật bảng 96 ô cho 64 ô của "
     "H0 và H1 — hai cột số thật, không còn `*(rơi byte)*` ở hai cấu hình này nữa.\n\n"
     "**2 ·** Và tính cho mình **số tăng tốc H1 so với H0 theo từng ô**. Mình tự tính thử rồi "
     "nên mình sẽ đối chiếu con số của bạn với con số của mình — nếu lệch thì một trong hai "
     "chúng ta đọc sai bản ghi. Nói rõ ô nào nhanh lên nhiều nhất, ô nào ít nhất, và **vì sao "
     "chỗ ít nhất lại ít** — câu đó mới là câu đáng giá, nó nói lúc nào thêm phần cứng không "
     "giúp gì.", 2400, 5, False),

    ("Bài 2: nạp lại H1 một lần nữa — lỗi ở vòng đọc của mình",
     "**H2 xong: 32/32 ô, `ok=0` không ô nào.** Đủ ba cấu hình trên bo.\n\n"
     "Nhưng mình phải nhờ bạn nạp lại **H1** một lần nữa, và lý do là **lỗi của mình**: vòng "
     "đọc của mình thoát khi đếm được 32 chuỗi `RESULT`, nên nó thoát ngay giữa dòng thứ 32. "
     "Bản ghi H1 của mình có 32 chuỗi mà chỉ **31 dòng đủ trường** — dòng cuối dừng ở "
     "`RESULT,n=32,dtype=I8,ver=V3,hw=H1,cycles=2425540,macs=` rồi hết, và không có "
     "`DONE_BENCHMARK`.\n\n"
     "Mình đã sửa: giờ chỉ thoát khi **có `DONE_BENCHMARK` VÀ đủ 32 dòng**. Đếm một chuỗi xuất "
     "hiện không giống đọc xong một dòng — mình đếm cái thứ nhất mà tưởng đã có cái thứ hai.\n\n"
     "Nên: tổng hợp và nạp lại **H1** (`ENABLE_MUL=1`, `ENABLE_FAST_MUL=0`, "
     "`firmware_h1.hex`), báo mình một dòng, mình bắt lại.\n\n"
     "Trong lúc chờ, mình đưa bạn số đo của 95 ô đã chắc chắn để bạn kiểm lại con số của "
     "mình — **đừng lấy số của mình làm chuẩn, hãy tự tính rồi nói nếu lệch**:\n\n"
     "| | ít nhất | nhiều nhất |\n|---|---|---|\n"
     "| H1 so H0 | 1,57× tại `N=8, I8, V1` | 6,8× tại `N=16, I8, V3` |\n"
     "| H2 so H0 | 2,45× tại `N=4, I8, V1` | 12,5× tại `N=32, I8, V3` |\n\n"
     "Và `cpm` ở `N=32`: H0 502 → H1 74 → H2 40 cho `V0`; nhưng `I8 V1` thì H0 chỉ 131, còn H1 "
     "81 và H2 47 — **nghĩa là ở ô ấy H0 đã nhanh sẵn nên phần cứng thêm vào giúp ít nhất**. "
     "Mình nghĩ đó chính là câu trả lời cho *lúc nào thêm phần cứng không giúp gì*, nhưng mình "
     "muốn bạn nói lý do bằng kiến trúc chứ không bằng con số.", 2400, 5, False),

    ("Bài 2: đủ 96 ô — giờ chốt và viết lại bảng",
     "**Đủ 96 ô từ bo thật.** Mình bắt lại H1 bằng vòng đọc đã sửa, và giờ cả ba bản ghi đều "
     "có `DONE_BENCHMARK` cùng 32 dòng đủ trường. Mình tự đối chiếu:\n\n"
     "| phép kiểm | kết quả |\n|---|---|\n| ô bắt được từ bo | **96/96** |\n"
     "| ô `ok=1` | **96/96** |\n| ô có tổng kiểm lệch bảng tay NGƯỜI mục 5.3b | **0** |\n\n"
     "Ba tệp: `bai2/ket-qua/bo-that-h0.log`, `-h1.log`, `-h2.log`.\n\n"
     "Việc cuối của bạn, làm hết trong lượt này:\n\n"
     "**1 ·** Viết lại `bang-doi-chieu-96-o.md` cho đủ **96 dòng, hai cột số thật** — cột mô "
     "phỏng và cột bo, không còn `*(rơi byte)*` ở đâu nữa. Thêm cột tăng tốc so với H0.\n\n"
     "**2 ·** Trả lời câu của cả Bài 2, bằng số đo:\n"
     "   - đưa phép nhân xuống phần cứng thì nhanh hơn bao nhiêu lần\n"
     "   - ô nào nhiều nhất, ô nào ít nhất\n"
     "   - **và vì sao chỗ ít nhất lại ít** — giải thích bằng kiến trúc. Mình thấy ô ít nhất "
     "đều là `I8, V1`, chỗ mà H0 đã nhanh sẵn. Nói cho mình biết tại sao.\n\n"
     "**3 ·** Rồi tự kê cho mình, thật thà: **chỗ nào trong Bài 2 mà bạn đã báo xong mà thực "
     "ra chưa xong**, và chỗ nào bảng 96 ô này **KHÔNG chứng minh được** dù nó xanh hết. Mình "
     "hỏi câu này vì một bảng 96 ô xanh toàn bộ là đúng loại kết quả dễ bị tin quá mức.\n\n"
     "**4 ·** Và nói luôn hai chỗ Makefile còn hỏng để mình ghi vào báo cáo: `make bitstream-h1` "
     "đổ vì đường dẫn `include` tính từ gốc dự án, và đường dựng duy nhất chạy được hiện nay là "
     "`hdl.synth` của EIDE chứ không phải Makefile. Tài liệu của mình đang mô tả một đường mà "
     "người khác gõ lại sẽ không ra — cần sửa, hoặc cần ghi rõ.", 3600, 5, False),

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
