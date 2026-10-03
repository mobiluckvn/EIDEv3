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

from phien_robot import NhatKy, cong_cu_da_goi, hoi, so_dong_so_cai   # noqa: E402
from thu_giao_dien import GiaoDien                                     # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

DU_AN = REPO / "du-lieu/fpga-sinhvien"
RA = REPO / "du-lieu/ket-qua/fpga-sinhvien"
TAI_LIEU = REPO / "docs/fpga/DAU-VAO-AGENT-FPGA-v2.md"
QUAN_SAT = RA / "quan-sat-nguoi.jsonl"


def mo_app(du_an: pathlib.Path) -> GiaoDien:
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

    # --------------------------------------------- 3 · BÀI 1 TRÊN BO THẬT
    ("Bài 1: dựng bitstream",
     "Mô phỏng xong rồi. Dựng bitstream đi bạn, rồi báo mình tài nguyên dùng hết và Fmax đo "
     "được.", 2400, 3, False),

    ("Bài 1: nạp bo",
     "Mình đã cắm kit vào máy. Bạn nạp bitstream lên bo.", 2400, 3, False),

    ("Bài 1: bo đang chạy đúng bản vừa dựng không",
     "Mình cần chắc bo đang chạy đúng bitstream vừa dựng. Bạn tìm một cách đo để chắc chuyện "
     "đó.", 1800, 3, False),

    ("Bài 1: đọc cổng nối tiếp",
     "Giờ đọc cổng nối tiếp xem bo đang nói gì.", 1800, 3, False),

    ("Bài 1: người quan sát",
     "Mình đang nhìn bo. Đây là những gì mình thấy, nguyên văn:\n\n{quan_sat}\n\n"
     "Từ đúng những gì mình vừa kể, bạn suy ra được gì?", 1800, 3, True),

    # ------------------------------------------------- 4 · BÀI 2, TRÊN MÁY
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
