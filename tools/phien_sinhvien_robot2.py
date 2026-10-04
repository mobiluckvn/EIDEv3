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
        if not dich.exists() or dich.stat().st_size != nguon.stat().st_size:
            thieu.append(f"{dich.name} — chép không tới hoặc lệch kích thước")
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
