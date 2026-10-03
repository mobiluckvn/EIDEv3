# -*- coding: utf-8 -*-
"""Phiên FPGA trên bo thật — việc cuối cùng của đề án RISC-V trên Tang Nano 20K.

`docs/riscv-tn20k/TRANG-THAI-TAM-DUNG.md` ghi: phần làm được mà không cần phần cứng đã xong.
Việc duy nhất còn lại là **đối chiếu số mô phỏng với số đo trên bo, đề bài đòi chênh ≤ 1 %**.
Kit về ngày 03/10/2026.

Thứ tự bốn việc lấy đúng từ mục "Khi kit về thì làm gì" của tài liệu ấy, không tự nghĩ lại.

**Một điều khác hẳn phiên robot, và nó lấy từ §5 của cùng tài liệu:** *giao một việc mỗi lượt.*
Đo được 02/10: ba lượt liền tác tử đọc đề rồi kết lượt mà không ghi gì — không phải hết ngân
sách (hạn 220 lời gọi, nó dùng 13–17). **Đề dài có bảng và sáu mục thì nó đọc rồi dừng; đề một
câu một việc thì nó làm ngay.** Nên câu trong tệp này ngắn, mỗi câu đúng một việc.

Hạn lượt: mặc định 300 giây / 40 lời gọi là quá chặt cho việc HDL. Tài liệu chốt
`EIDE_TRAN_GIAY_LUOT=3600 EIDE_TRAN_LOI_GOI_LUOT=220`, và tệp này đặt sẵn.

Chạy:
    .venv/bin/python tools/phien_fpga_bo_that.py --liet-ke
    .venv/bin/python tools/phien_fpga_bo_that.py --giai-doan 1
    .venv/bin/python tools/phien_fpga_bo_that.py --buoc 4 --quan-sat "đèn LED0 sáng, không nhấp nháy"
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

from phien_robot import doi_chieu_app_voi_nguon, NhatKy, cong_cu_da_goi, hoi, so_dong_so_cai   # noqa: E402
from thu_giao_dien import GiaoDien                                     # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

# Dự án SỐNG là `-b`: nó có `results/all.csv` 96 dòng để đối chiếu. Dự án `riscv-tn20k`
# (không `-b`) là bản cũ của phiên 01/10 và KHÔNG có all.csv.
DU_AN = REPO / "du-lieu/riscv-tn20k-b"
RA = REPO / "du-lieu/ket-qua/fpga-bo-that"
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


# ===================================================================== các bước
#
# (tên, câu gõ, giây chờ, giai đoạn, cần người quan sát)
#
# Câu NGẮN, mỗi câu một việc. Không nhắc tên công cụ.
BUOC: list[tuple[str, str, int, int, bool]] = [

    # ----------------------------------------------- 1 · KIỂM BO TRƯỚC KHI NẠP
    ("Dò bo",
     "Kit Tang Nano 20K đã cắm vào máy. Bạn dò xem có nhận ra bo không, và cho mình biết nó "
     "nhận ra chip gì.", 900, 1, False),

    ("Hai chỗ phải sửa trước khi nạp",
     "Trong kho có tệp đánh giá nạp bo thật của Bài 1, nêu hai chỗ phải sửa trước khi nạp. Bạn "
     "tìm đọc rồi nói lại cho mình hai chỗ đó là gì.", 900, 1, False),

    ("Sửa hai chỗ đó",
     "Sửa hai chỗ ấy đi. Sửa xong thì cho mình xem phần đã đổi.", 1200, 1, False),

    # ------------------------------------------------------- 2 · NẠP BÀI 1
    ("Dựng lại bitstream Bài 1",
     "Dựng lại bitstream Bài 1 sau khi sửa. Báo mình Fmax đo được và tài nguyên dùng hết.",
     2400, 2, False),

    ("Nạp Bài 1 lên bo",
     "Nạp bitstream vừa dựng lên bo.", 1800, 2, False),

    ("Bo đang chạy đúng bản vừa dựng không",
     "Mình cần chắc bo đang chạy đúng bitstream vừa dựng, không phải bản cũ còn trên flash. "
     "Bạn tìm một cách đo để chắc chuyện đó.", 1200, 2, False),

    ("Đọc UART xem có Hello không",
     "Mở cổng nối tiếp đọc cho mình xem bo đang nói gì. Đề bài đòi ra dòng Hello from "
     "PicoRV32.", 1200, 2, False),

    ("Người quan sát — đèn và nút",
     "Mình đang nhìn bo. Đây là những gì mình thấy, nguyên văn:\n\n{quan_sat}\n\n"
     "Từ đúng những gì mình vừa kể, bạn suy ra được gì?", 1200, 2, True),

    # ------------------------------------------- 3 · HAI MƯƠI BỐN LƯỢT BÀI 2
    ("Kê trước 24 lượt sẽ chạy",
     "Sắp chạy Bài 2 trên bo. Trước khi chạy, kê cho mình danh sách 24 lượt: mỗi lượt là cấu "
     "hình nào, dịch bằng tập lệnh nào.", 1200, 3, False),

    # Ba việc phải chốt TRƯỚC khi chạy 24 lượt, vì mỗi lượt tốn vài phút tổng hợp. Chạy sai
    # cách thì mất cả giờ và tệ hơn: ra 96 ô đầy đủ, trông như đã đo, mà phần lớn là một
    # chương trình chạy lặp lại.
    ("Chốt ba việc trước khi chạy",
     "Trước khi chạy, mình cần chốt ba việc.\n\n"
     "Một. Mình đo được một chuyện trên bo mà bạn chưa biết: nạp vào SRAM thì **không giữ "
     "được**. Bo tự cấu hình lại từ flash SPI và quay về demo nhà máy. Mình đã nạp bốn lần và "
     "lần nào cũng chạy một lúc rồi mất. Lúc bạn đọc được dòng Hello ở lượt trước là vì bạn "
     "mở cổng ngay sau khi nạp. Nên với mỗi lượt, bạn phải bắt bản ghi cổng nối tiếp **ngay** "
     "sau khi nạp, đừng để trống thời gian ở giữa.\n\n"
     "Hai. Bạn gom 24 lượt theo ba nhóm phần cứng. Mình muốn bạn nói rõ: cả phiên này cần "
     "dựng **bao nhiêu** bitstream, và vì sao đúng con số đó? Bạn mở `rtl/bram.v` và "
     "`rtl/soc_top.v` ra xem chương trình được nạp vào bộ nhớ ở thời điểm nào, rồi trả lời.\n\n"
     "Ba. Bạn nói N nhỏ hơn 16 thì V3 tự chuyển về V2. Mình mở `bai2/sw/main.c` dòng 209 đến "
     "214 thì thấy khối `#if MATRIX_N >= 16` có hai nhánh **gọi y hệt nhau**, cùng là "
     "`run_benchmark(\"V3\", matmul_v3, overhead)`. Bạn đọc lại rồi nói cho mình biết thật ra "
     "V3 chạy với những N nào.", 1800, 3, False),

    ("Chạy 24 lượt trên bo và bắt bản ghi UART",
     "Chốt rồi thì chạy đi bạn. Chạy lần lượt 24 lượt trên bo, mỗi lượt bắt bản ghi cổng nối "
     "tiếp ngay sau khi nạp. Lượt nào không bắt được dữ liệu thì ghi là không bắt được, đừng "
     "bỏ qua im lặng — mình thà thiếu dòng còn hơn có một dòng không biết từ đâu ra.", 3600, 3, False),

    # Bước này sinh ra từ một loạt phép đo của người, sau khi bước 11 báo 0 byte. Nó khoanh
    # vùng lỗi xuống đúng firmware Bài 2, và loại hết những chỗ khác.
    ("Firmware Bài 2 im lặng — đây là các phép đo đã loại trừ",
     "Mình đã đo thêm và khoanh được vùng lỗi. Mình kể hết số đo cho bạn:\n\n"
     "Những chỗ mình đã LOẠI, mỗi chỗ bằng một phép đo:\n"
     "- Chuỗi nạp, đồng hồ 27 MHz, chân LED: `blinky.fs` nháy đúng 1 giây trên bo, mắt mình thấy.\n"
     "- Đúng chip: `openFPGALoader --detect` đọc ra `idcode 0x81b`, `GW2A(R)-18(C)`.\n"
     "- Đường UART và cổng: firmware **Bài 1** in được `Hello from PicoRV32` trên chính bo "
     "này, 127 byte. Cổng `...171` là UART, cổng `...170` là JTAG — giữ 170 mở thì chặn luôn "
     "việc nạp.\n"
     "- Khe hở thời gian: mình đã mở cổng TRƯỚC khi nạp rồi đọc xuyên qua lần cấu hình lại. "
     "Vẫn 0 byte. Nên im lặng không còn giải thích được bằng chuyện bắt bản ghi muộn.\n"
     "- Bo không giữ cấu hình: đã ghi bitstream vào flash trên kit, `--verify` khớp. Bản "
     "bitstream nhà máy đã sao lưu ra `sao-luu-flash/`.\n"
     "- Lệnh lạ: mình dịch ngược `.eide/build/mach.elf`, **0 lệnh nhân/chia** — bản dịch "
     "`rv32i` đúng, không có chỗ nào làm CPU bẫy lệnh lạ.\n"
     "- Ảnh chương trình: `mach.hex` từ đầu tiên là `00008117` (`auipc sp, 8`), tức mã thật "
     "nằm đúng địa chỉ 0. Hai tệp linker của Bài 1 và Bài 2 giống nhau ở mọi dòng quan trọng. "
     "Các đoạn: text 3 468 B, rodata 252 B, bss 64 B — vừa BRAM 32 KB.\n\n"
     "Còn lại đúng một chỗ: **firmware Bài 1 in được, firmware Bài 2 không in gì.** Cùng bo, "
     "cùng cổng, cùng cách bắt bản ghi.\n\n"
     "Bạn tìm xem khác nhau ở đâu. Mình gợi ý một chỗ để bắt đầu nhưng đừng coi là đáp án: "
     "Bài 1 in **trong vòng lặp vô hạn**, Bài 2 tính xong hết rồi mới in **một lần ở cuối**. "
     "Nếu CPU dừng hoặc treo giữa lúc tính thì Bài 1 vẫn kịp in còn Bài 2 thì không bao giờ "
     "in. Tìm cách đo xem CPU có chạy tới chỗ in hay không — và nhớ bo có 6 đèn LED mà mình "
     "nhìn được.", 2400, 3, False),

    ("Không đèn nào sáng — CPU không vào nổi main()",
     "Có số đo mới, và nó loại được một nửa.\n\n"
     "Bạn phác kế hoạch 6 mốc đèn. Mốc 3 của bạn thì **đã có sẵn trong mã**: "
     "`bai2/sw/main.c:199` có `LED_REG = 0x01` là lệnh đầu tiên của `main()`, và "
     "`rtl/soc_top.v:203` có `assign led = ~led_reg`, nên vào được `main()` là LED0 phải "
     "sáng. Mình nạp lại rồi nhìn bo: **không đèn nào sáng.** Nên CPU không vào tới `main()`.\n\n"
     "Thêm hai số đo nữa:\n"
     "- Mình giải mã mã máy đầu `mach.hex`: `auipc sp,8` cho ngăn xếp 0x8000, rồi vòng xoá "
     "`.bss` từ 0xEB8 tới 0xEF8 khớp đúng biên `.bss` trong ELF, rồi `jal` vào `main`. Phần "
     "khởi động đúng.\n"
     "- Lúc bo chạy demo nhà máy thì anh thấy các đèn chạy. Giờ không đèn nào sáng, nên bo "
     "**cũng không chạy demo nhà máy**. Không phải thiết kế của mình, cũng không phải của họ.\n\n"
     "Bạn tìm xem FPGA có thật sự được cấu hình và CPU có thật sự chạy không. Mình nhắc một "
     "chuyện bạn tự nói ở lượt trước: `openFPGALoader` báo `Done` chỉ nghĩa là chuỗi JTAG nhận "
     "đủ byte, không nghĩa là chip đang chạy thiết kế đó.", 2400, 3, False),

    ("Duyệt sơ đồ ba tầng đèn, kèm một điều kiện",
     "Mình duyệt sơ đồ ba tầng đèn của bạn. Nó tách đúng ba thứ cần tách: LED5 lấy từ đồng hồ "
     "nên không phụ thuộc reset hay CPU, LED4 lấy từ `sys_resetn`, LED3–0 do CPU ghi. Làm đi.\n\n"
     "Một điều kiện: đây là **bản dựng để chẩn đoán**, không phải bản dùng để đo 24 lượt. "
     "Thêm mạch vào thì tài nguyên và Fmax đổi, mà Bài 2 lại so số chu kỳ với mô phỏng ở mức "
     "1 phần trăm. Nên hãy làm sao gỡ ra được sạch — một tham số hoặc một cờ biên dịch, mặc "
     "định TẮT — để bản đo cuối cùng không mang mạch chẩn đoán trong người. Và nói cho mình "
     "biết bạn chọn cách gỡ nào.\n\n"
     "Dựng xong thì nạp lên bo rồi bảo mình nhìn, mình sẽ kể lại đèn nào sáng đèn nào nháy.",
     2400, 3, False),

    ("LED5 nháy — và một hướng đo mới về khởi tạo BRAM",
     "Số đo mới từ bo: **LED5 nháy.** Nên FPGA đã được cấu hình, đã vào chế độ chạy, và đồng "
     "hồ 27 MHz sống. Tầng 1 của bạn đạt. Giả thuyết 'bitstream không vào được chế độ chạy' "
     "bị loại.\n\n"
     "Mình chưa có số đo cho LED4 nên chưa biết reset đã nhả hay chưa. Trong lúc chờ, mình "
     "đo thêm được mấy con số và nó mở ra một hướng:\n\n"
     "- BRAM khai 8 192 từ, chương trình Bài 2 chỉ 942 từ — thừa chỗ, không bị cắt vì thiếu "
     "dung lượng.\n"
     "- Nhưng `_start` ở địa chỉ 0x000 còn **`main` ở 0x714, tức từ thứ 453**.\n\n"
     "Chỗ mình muốn bạn đo: **phần khởi tạo BRAM trong bitstream có phủ tới từ thứ 453 "
     "không?** Nếu nó chỉ phủ được vài từ đầu thì `start.S` vẫn chạy mà mã của `main` lại là "
     "số 0 — và điều đó khớp với mọi thứ ta thấy: CPU chạy, nhưng không bao giờ ghi được vào "
     "thanh ghi đèn.\n\n"
     "Tài liệu đánh giá Bài 1 có một phép đo gần giống: thay cả chương trình thành số 0 rồi so "
     "mã băm tệp `.fs`. Phép đó chứng minh bitstream **đổi theo** chương trình, nhưng chưa "
     "chứng minh nó phủ **tới đâu**. Bạn nghĩ ra một phép đo mạnh hơn cho câu 'phủ tới từ "
     "nào', rồi làm. Nếu bạn thấy hướng khác đáng đo hơn thì nói, mình nghe.", 2400, 3, False),

    ("LED4 tắt — CPU bị giữ trong reset",
     "Có số đo cho LED4: **chỉ duy nhất LED5 nháy, mọi đèn khác tắt hết.**\n\n"
     "`led[4] = ~sys_resetn`, đèn tích cực thấp, nên LED4 tắt nghĩa là `led[4] = 1`, nghĩa là "
     "**`sys_resetn = 0`: CPU bị giữ trong reset.** Tầng 2 của bạn trượt.\n\n"
     "Mình đọc khối reset ở `soc_top.v` dòng 22–35: bộ đếm `por_cnt` tăng bình thường, sau 16 "
     "chu kỳ thì `sys_resetn` lên 1. Nên chỉ có một đường duy nhất để nó mắc ở 0: **`btn_s1` "
     "đọc ra 0**, tức chân nút như đang bị nhấn liên tục.\n\n"
     "Mình đã thử một giả thuyết và nó SAI, kể để bạn khỏi đi lại: mình nghi `BANK_VCCIO=3.3` "
     "thêm vào tệp ràng buộc làm hỏng chân nút. Nhưng so mốc giờ thì `cs-0140` xảy ra 15:36:03 "
     "còn Bài 1 in được `Hello` lúc 15:41:55 và 15:54:41 — đều SAU đó. Nên thay đổi ấy không "
     "phải nguyên nhân.\n\n"
     "Và một chuyện đáng chú ý: `tai-lieu/DANH-GIA-NAP-BO-THAT.md` mục 3 đã **tiên đoán đúng "
     "lỗi này** từ 01/10, trước khi có kit — *chân thả nổi đọc ra 0 thì bo nằm trong reset "
     "vĩnh viễn*. Nhưng mục đó kết luận ĐẠT vì nó chỉ **kiểm chữ** trong tệp ràng buộc thấy có "
     "`PULL_MODE=UP`. Đọc chữ không phải đo hành vi của chân.\n\n"
     "Mình đề xuất một phép đo cắt đứt được câu hỏi, không cần mắt người: dựng một bitstream "
     "mà `sys_resetn` **bỏ hẳn `btn_s1`**, chỉ dùng bộ đếm khởi động. Nếu CPU chạy và UART ra "
     "chữ thì chân nút đúng là nguyên nhân; nếu vẫn im thì nguyên nhân ở chỗ khác và ta loại "
     "được chân nút. Bạn thấy phép này ổn thì làm, thấy phép khác mạnh hơn thì nói mình nghe.",
     2400, 3, False),

    ("Chốt bản RTL để giao, trước khi chạy 24 lượt",
     "Phép đo của bạn thắng. Bỏ `btn_s1` khỏi mạch reset thì mọi thứ chạy ngay, và lượt 1 cho "
     "bốn dòng `RESULT` khớp mô phỏng **lệch 0,000 %** cả bốn, checksum `0xFFFE6A17` đúng. Nên "
     "nguyên nhân gốc đã chốt: **chân `btn_s1` PIN 88 đọc ra 0, giữ CPU trong reset.**\n\n"
     "Giờ chốt bản RTL để giao. Hai việc, cùng một lượt vì cùng sửa `soc_top.v`:\n\n"
     "Một. Đề bài §5 Bài 1 đòi *reset gồm power-on-reset VÀ nút S1*. Bản hiện tại bỏ nút đi "
     "nên lệch đặc tả. Bạn tìm cách để nút dùng được thật — đồng bộ hai tầng, lọc chống rung, "
     "hay xác định lại PIN 88 có đúng là S1 trên bản bo này. Nếu bạn kết luận **không nên** "
     "dùng nút cho reset thì cũng được, nhưng phải ghi thành một quyết định có lý do và có "
     "trích chỗ lấy, đừng để kho nói một đằng mã làm một nẻo.\n\n"
     "Hai. Tắt `DIAG_LEDS` cho bản giao. Lý do: bản đo 24 lượt phải là **đúng thiết kế đã mô "
     "phỏng**, không mang mạch chẩn đoán trong người — nếu không thì con số 1 phần trăm đang "
     "so hai thiết kế khác nhau.\n\n"
     "Xong hai việc thì dựng lại và cho mình biết tài nguyên với Fmax của bản giao.", 2400, 3, False),

    ("Chạy 24 lượt trên bản giao",
     "Mình duyệt ADR-05. Nó ghi đúng cách: nêu chỗ lệch đặc tả §5, nêu phép đo đã bác đặc tả, "
     "nêu cả mặt dở là nút S1 không dùng để reset tay được nữa, và khai tầng VÀNG chứ không "
     "khai NGƯỜI. Bản giao cũng đúng: LUT giảm từ 2 211 xuống 2 168, đúng bằng phần mạch chẩn "
     "đoán đã gỡ.\n\n"
     "Giờ chạy cả **24 lượt** trên bản giao này. Mình chạy lại từ lượt 1, không dùng lại số "
     "của lượt 1 cũ — vì lượt ấy chạy trên bản còn mạch chẩn đoán, và mình muốn cả 96 ô đến "
     "từ đúng một thiết kế.\n\n"
     "Hai điều mình đã đo xong, bạn dùng luôn khỏi phải dò lại:\n"
     "- Cổng `...171` là UART, cổng `...170` là JTAG. Giữ 170 mở thì chặn chính việc nạp.\n"
     "- `target.flash` giờ có tham số bắt bản ghi **bao quanh** lần nạp: mở cổng trước, vét "
     "rác, nạp, rồi đọc. Dùng nó, đừng gọi đọc log sau khi nạp — firmware Bài 2 in một lần "
     "rồi dừng nên gọi sau là mất.\n\n"
     "Lượt nào không bắt được thì ghi là không bắt được.", 3600, 3, False),

    ("Đo thẳng chân 88, không qua CPU",
     "Anh Công vừa cho mình một dữ kiện: **S1 là nút bên tay phải, S2 là nút bên tay trái.** "
     "Nên chân 88 trong tệp ràng buộc đúng là nhắm vào S1.\n\n"
     "Vậy `ADR-05` có thể kết luận sớm. Nó bỏ nút khỏi mạch reset dựa trên *triệu chứng* chân "
     "kẹp 0, mà ta chưa bao giờ đo **thẳng** cái chân ấy — mọi lần đo đều đi qua CPU, qua "
     "reset, qua BRAM.\n\n"
     "Mình muốn một bitstream nhỏ nhất có thể, **không có CPU, không có BRAM, không có UART**, "
     "chỉ làm hai việc:\n"
     "- một đèn phản chiếu thẳng mức của chân 88\n"
     "- một đèn khác nháy theo đồng hồ, để biết bitstream đang chạy\n\n"
     "Dựng xong thì nạp, rồi bảo mình nhìn. Mình sẽ báo hai thứ: đèn phản chiếu sáng hay tắt "
     "lúc không bấm, và nó có đổi khi mình bấm giữ nút bên phải.\n\n"
     "Phép này rẻ hơn hẳn — mạch nhỏ nên tổng hợp nhanh — và nó trả lời đúng câu còn lại: chân "
     "88 có nối tới S1 không, và nó đọc ra gì. Nếu chân đọc đúng thì mình sẽ sửa `ADR-05`.",
     2400, 3, False),

    ("Dựng board.csv từ bản ghi",
     "Trong kho có công cụ đọc bản ghi UART ra CSV, viết sẵn cho đúng việc này. Dùng nó dựng "
     "results/board.csv từ các bản ghi vừa bắt.", 1800, 3, False),

    # ------------------------------------------------- 4 · ĐỐI CHIẾU ≤ 1 %
    ("So board.csv với all.csv",
     "So results/board.csv với results/all.csv. Đề bài đòi chênh không quá 1 phần trăm. Báo "
     "mình từng dòng chênh bao nhiêu, và bao nhiêu dòng vượt 1 phần trăm.", 1800, 4, False),

    ("Chỗ nào chênh thì vì sao",
     "Dòng nào chênh nhiều nhất thì nói cho mình biết vì sao nó chênh. Nếu chưa đo được thì "
     "nói là chưa đo được.", 1800, 4, False),

    ("Phép đối chiếu này KHÔNG chứng minh được gì",
     "Bạn tự kê cho mình: phép đối chiếu vừa rồi không chứng minh được những gì.", 1200, 4, False),

    ("Tự kê chỗ đã báo xong mà chưa xong",
     "Câu cuối, và mình hỏi thật. Trong cả phiên này có lúc nào bạn báo đã xong hoặc đã kiểm, "
     "mà thực ra lúc đó chưa xong, hoặc phép kiểm chưa đo được cái cần đo không? Có thì kê ra "
     "hết.", 1200, 4, False),
]

TEN_GIAI_DOAN = {
    1: "Kiểm bo trước khi nạp",
    2: "Nạp Bài 1 và đọc UART",
    3: "Hai mươi bốn lượt Bài 2 trên bo",
    4: "Đối chiếu ≤ 1 % và chốt",
}


def ghi_quan_sat(buoc: int, ten: str, cau: str) -> None:
    RA.mkdir(parents=True, exist_ok=True)
    with QUAN_SAT.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"buoc": buoc, "ten": ten, "nguoi_noi": cau,
                            "luc": time.strftime("%Y-%m-%d %H:%M:%S")},
                           ensure_ascii=False) + "\n")


def chay(buoc_chon: set[int] | None, quan_sat: str) -> int:
    from eide.config import load_dotenv

    load_dotenv()
    if not DU_AN.exists():
        print(f"{DO}Không có dự án {DU_AN}{HET}")
        return 2
    RA.mkdir(parents=True, exist_ok=True)

    thieu = [(i, t) for i, (t, _, _, _, can) in enumerate(BUOC, 1)
             if can and (not buoc_chon or i in buoc_chon) and not quan_sat.strip()]
    if thieu:
        print(f"{DO}Bước cần câu quan sát của người mà chưa có:{HET}")
        for i, t in thieu:
            print(f"  bước {i}: {t}")
        return 2

    nk = NhatKy(RA, tieu_de="FPGA RISC-V trên Tang Nano 20K — phiên bo thật",
                nguon="docs/riscv-tn20k/TRANG-THAI-TAM-DUNG.md",
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
    ap = argparse.ArgumentParser(description="Phiên FPGA trên bo thật")
    ap.add_argument("--giai-doan", type=int, choices=sorted(TEN_GIAI_DOAN))
    ap.add_argument("--buoc", default="")
    ap.add_argument("--quan-sat", default="")
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
    return chay(chon, a.quan_sat)


if __name__ == "__main__":
    raise SystemExit(main())
