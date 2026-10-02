#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Một phiên làm việc THẬT: lõi RISC-V trên FPGA Sipeed Tang Nano 20K.

    .venv/bin/python tools/phien_fpga.py [--buoc 1-3] [--giu-du-an]

Đề bài do anh Công giao, nằm nguyên văn ở `docs/fpga/yeu-cau-agent-riscv-tang-nano-20k.md`:
dựng một CPU RISC-V trên FPGA, chạy chương trình C trên CPU đó, đo chi phí nhân ma trận, rồi
thêm phần cứng chuyên dụng để giảm chi phí ấy. Ba bài, hai cổng chuẩn bị (G0, G1), sáu điểm
dừng bắt buộc.

## Vì sao phiên này khác hai phiên trước

Phiên viết hệ điều hành và phiên robot đều nằm trong vùng EIDE đã làm được: biên dịch C cho
ARM hoặc AVR, nạp qua ST-Link hoặc avrdude. Phiên này **nằm ngoài hẳn**:

- EIDE chưa có tổng hợp HDL (Yosys), chưa có đặt-đi dây (nextpnr), chưa có đóng gói bitstream.
- EIDE chưa có mô phỏng Verilog (Verilator, Icarus) dù hai công cụ đó đã có trên máy.
- `target.flash` chỉ biết ST-Link và avrdude, không biết openFPGALoader.
- `build.compile` không có đường RISC-V bare-metal, dù `passport.py` có biết tên `rv32imac`.
- Không tab nào hiện được bảng tài nguyên LUT / FF / BSRAM / DSP / Fmax.

Nên phiên này đo hai thứ cùng lúc: **Agent làm được bài FPGA tới đâu**, và **một môi trường
dựng cho vi điều khiển còn thiếu gì khi gặp FPGA**. Chỗ thiếu ghi vào
`tai-lieu/NANG-CAP-AGENT.md` ngay lúc gặp, rồi nâng cấp, rồi làm lại.

## Ghi nhật ký

Chạy lõi với `EIDE_GHI_LLM=1`, nên mỗi lời gọi mô hình để lại **nguyên văn gửi đi và nguyên
văn trả về** ở `<dự án>/.eide/llm/`. Cộng với sổ ghi việc, bản ghi từng phiên và ảnh chụp cửa
sổ, cả phiên dựng lại được từ đầu mà không cần tin vào bản tóm tắt nào.
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

from phien_robot import NhatKy, hoi          # noqa: E402
from thu_giao_dien import GiaoDien           # noqa: E402

XANH, DO, VANG, XAM, HET = "\033[92m", "\033[91m", "\033[93m", "\033[90m", "\033[0m"

DU_AN = REPO / "du-lieu/riscv-tn20k"
RA = REPO / "du-lieu/ket-qua/fpga-riscv"
DE_BAI = REPO / "docs/fpga/yeu-cau-agent-riscv-tang-nano-20k.md"


def cho_luot_dong(du_an: pathlib.Path, han_giay: float = 25.0) -> bool:
    """Chờ sổ ghi việc có `turn.end` cho lượt mới nhất, TRƯỚC khi được phép tắt lõi.

    Vì sao cần: `hoi()` trả về khi lời đáp của tác tử hiện ra trên giao diện, nhưng lõi còn
    phải ghi `turn.end` xuống sổ. Tắt lõi ngay lúc ấy thì bản ghi kết thúc không bao giờ xuống
    đĩa.

    Hậu quả không hiện ra ngay, và đó là chỗ đắt: lần mở lại dự án, khối `<resume>` đọc sổ,
    thấy một lượt có `turn.start` mà không có `turn.end`, rồi nói với tác tử *"Lượt run-00N
    chưa kết thúc"*. Khối ấy còn dặn thêm *"việc dở dang thì nói ra TRƯỚC khi làm"*. Nên tác tử
    đi làm lại đúng việc của lượt trước, thay vì việc vừa được giao.

    Đo được ngày 01/10/2026: bốn lượt liền tác tử lặp lại việc cũ, và nguyên nhân nằm ở đây
    chứ không nằm ở lời giao việc hay ở ngữ cảnh.
    """
    so = du_an / ".eide" / "ledger.jsonl"
    het = time.time() + han_giay
    while time.time() < het:
        try:
            bat_dau: list[str] = []
            ket_thuc: set[str] = set()
            with open(so, encoding="utf-8", errors="replace") as f:
                for dong in f:
                    if '"turn.' not in dong:
                        continue
                    d = json.loads(dong)
                    rid = (d.get("data") or {}).get("run_id")
                    if d.get("kind") == "turn.start" and rid:
                        bat_dau.append(rid)
                    elif d.get("kind") == "turn.end" and rid:
                        ket_thuc.add(rid)
            if bat_dau and bat_dau[-1] in ket_thuc:
                return True
        except (OSError, ValueError):
            pass
        time.sleep(0.5)
    print(f"{DO}  ⚠ lượt cuối chưa thấy turn.end sau {han_giay:.0f}s — lần mở lại sẽ báo "
          f"'dở dang' và tác tử sẽ làm lại việc cũ{HET}")
    return False


def mo_app(du_an: pathlib.Path) -> GiaoDien:
    """Mở app, bật ghi nhật ký mô hình.

    Gọi thẳng tệp nhị phân chứ không `open -a`: LaunchServices không mang biến môi trường của
    vỏ lệnh sang, mà `EIDE_GHI_LLM` phải tới được lõi — lõi là tiến trình con của app.
    """
    cho_luot_dong(du_an)
    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    # DỌN HỘP THƯ VÀO trước khi mở lại app — giữ hộp ra, bỏ hộp vào.
    #
    # `GiaoDien(..., xoa=False)` được đặt để **giữ hộp ra**, vì nhật ký phiên đọc từ đó. Nhưng
    # nó giữ luôn hộp vào, và app mở lại thì đọc hộp vào **từ đầu tệp** rồi phát lại lời giao
    # việc CŨ NHẤT.
    #
    # Đo được ngày 01/10/2026: ba lượt liền tác tử chạy lại bài blinky, kể cả khi câu giao việc
    # viết thẳng "đừng chạy lại blinky". Nó không cãi — nó **không hề nhận được** câu ấy. Hộp
    # thư có bốn lời giao việc chồng lên nhau, và lần nào app cũng phát lại lời thứ nhất.
    #
    # Mất bốn lượt mới tìm ra, vì mọi dấu hiệu đều trỏ sang chỗ khác: tưởng ngữ cảnh bị việc cũ
    # chiếm chỗ, tưởng khối <resume> bảo nó làm nốt, tưởng lời giao việc quá dài. Cả ba đều là
    # giả thuyết hợp lý, và cả ba đều sai.
    hop_vao = du_an / ".eide" / "ui-test" / "inbox.jsonl"
    if hop_vao.exists():
        hop_vao.write_text("", "utf-8")
    het = time.time() + 20
    while time.time() < het:
        if subprocess.run(["pgrep", "-f", "EIDE.app/Contents/MacOS/EIDE"],
                          capture_output=True).returncode != 0:
            break
        time.sleep(0.5)
    time.sleep(1.0)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(du_an)], check=True)
    g = GiaoDien(du_an, xoa=False)
    # Nới hạn một lượt. Việc FPGA có bước dài hơn hạn mặc định ngay từ bản chất — tổng hợp một
    # lõi CPU mất vài phút, và một lượt quét ba cấu hình phần cứng cần hơn 40 lời gọi công cụ.
    # Xem DEV-319.
    #
    # Hai biến này từng bị quên ở đây: `mo_app` chỉ truyền `EIDE_GHI_LLM`, nên mọi lượt chạy
    # qua nó vẫn dùng hạn mặc định 300 s / 40 lời gọi — trong khi các lệnh chạy tay lại có nới.
    # Tác tử hết lời gọi giữa chừng mà không ai hiểu vì sao, vì hạn "đã được nới" ở chỗ khác.
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env={**os.environ, "EIDE_GHI_LLM": "1",
                          "EIDE_TRAN_GIAY_LUOT": os.environ.get("EIDE_TRAN_GIAY_LUOT", "1800"),
                          "EIDE_TRAN_LOI_GOI_LUOT":
                              os.environ.get("EIDE_TRAN_LOI_GOI_LUOT", "150")},
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(90)
    return g


# ===================================================================== các bước
#
# Mỗi bước là MỘT câu người giao việc gõ, viết như anh Công sẽ gõ thật: nói việc cần, không
# nhắc tên công cụ. Nhắc tên công cụ là mớm bài, và mớm bài thì đo chính lời mớm.
BUOC: list[tuple[str, str, int]] = [
    ("G0 — đọc đề bài, kê việc, nói trước chỗ không làm được",
     "Trong thư mục dự án có tệp `tai-lieu/yeu-cau-agent-riscv-tang-nano-20k.md`. Đó là đề bài "
     "anh Công giao: dựng một CPU RISC-V trên FPGA Sipeed Tang Nano 20K, chạy chương trình C "
     "trên CPU đó, đo chi phí nhân ma trận, rồi thêm phần cứng chuyên dụng để giảm chi phí ấy.\n\n"
     "Đọc kỹ cả tệp, rồi làm ba việc, theo thứ tự:\n\n"
     "**Một.** Tóm tắt cho mình: việc này gồm mấy giai đoạn, mỗi giai đoạn giao ra cái gì, và "
     "những chỗ nào đề bài bắt buộc dừng lại hỏi người.\n\n"
     "**Hai.** Kê ra **những chỗ EIDE chưa làm được việc này**. Đây là phần mình cần nhất, nên "
     "làm cho kỹ: thử gọi công cụ thật để biết, đừng đoán. Cụ thể là tra xem EIDE có đường nào "
     "để tổng hợp Verilog, để mô phỏng Verilog, để đóng gói bitstream, để nạp FPGA, và để biên "
     "dịch C cho RISC-V bare-metal hay không. Mỗi chỗ thiếu ghi một dòng vào "
     "`tai-lieu/NANG-CAP-AGENT.md`: đã thử gọi gì, lỗi gì, cần thêm năng lực gì.\n\n"
     "Đừng đi đường tắt bằng lệnh hệ thống để che chỗ thiếu. Mình muốn biết chỗ thiếu, vì "
     "chúng ta sẽ nâng cấp EIDE rồi làm lại — đó là một phần của việc này.\n\n"
     "**Ba.** Kiểm môi trường: trên máy này đã có công cụ nào trong bảng B2 của đề bài, thiếu "
     "công cụ nào. Ghi vào `docs/env.md` kèm phiên bản thật đọc được, không phải phiên bản "
     "đoán. Công cụ nào cần quyền quản trị để cài thì **chỉ kê ra**, chưa cài — đề bài có luật "
     "đó và nó là một trong sáu điểm dừng.\n\n"
     "Chưa viết dòng HDL nào ở bước này.", 2400),

    ("G0 — lập bảng 12 thông số phần cứng, mỗi dòng một nguồn",
     "Giờ làm bảng thông số phần cứng ở mục G0 của đề bài: 12 dòng, ghi vào "
     "`docs/hardware-facts.md`.\n\n"
     "Luật của đề bài, mình nhắc lại vì nó là chỗ dễ trượt nhất: **mỗi dòng phải có link "
     "nguồn**. Những giá trị đề bài ghi `[XÁC MINH]` là giá trị ban đầu, **chưa được tin** — "
     "phải đối chiếu với Sipeed wiki, sơ đồ nguyên lý của kit, hoặc tài liệu Gowin, rồi ghi "
     "link vào. Chân clock và chân UART thì đề bài đòi lấy từ nguồn chính thức.\n\n"
     "Dòng nào không tìm được nguồn chính thức thì **ghi rõ là chưa có nguồn**, đừng điền số "
     "cho đủ bảng. Đề bài có điểm dừng số 1 cho đúng trường hợp này: hết G0 mà còn dòng không "
     "xác minh được thì dừng lại hỏi.\n\n"
     "Có hai chuyện mình đã trả giá ở dự án robot nên nói trước:\n"
     "- **Hằng số phần cứng phải tra, không được dựng lại từ trí nhớ.** Ở dự án robot có ba "
     "hằng số tự nhớ, và chúng tự sinh ra ba bằng chứng sai.\n"
     "- **Một con số lạ chưa đủ để kết luận lại về phần cứng.** Thấy một giá trị khác dự kiến "
     "thì tra thêm nguồn, đừng đổi mô hình ngay.\n\n"
     "Xong thì chỉ viết `constraints/tangnano20k.cst` với **đúng những chân đã xác minh**, "
     "không thêm chân nào chưa có nguồn.", 2400),
]


def dung_du_an(giu: bool) -> None:
    if DU_AN.exists() and not giu:
        shutil.rmtree(DU_AN)
    (DU_AN / ".eide" / "ui-test").mkdir(parents=True, exist_ok=True)
    (DU_AN / "tai-lieu").mkdir(exist_ok=True)
    dich = DU_AN / "tai-lieu" / DE_BAI.name
    if not dich.exists():
        shutil.copy(DE_BAI, dich)


def chay(buoc_chon: set[int] | None, giu: bool) -> int:
    from eide.config import load_dotenv

    load_dotenv()
    dung_du_an(giu)
    nk = NhatKy(RA, tieu_de="lõi RISC-V trên FPGA Sipeed Tang Nano 20K",
                nguon=str(DE_BAI.relative_to(REPO)),
                du_an=str(DU_AN.relative_to(REPO)))
    g = mo_app(DU_AN)

    for i, (ten, cau, giay) in enumerate(BUOC, 1):
        if buoc_chon and i not in buoc_chon:
            continue
        nk.buoc(ten)
        hoi(g, nk, DU_AN, cau, giay=giay)
        nk.anh(g, ten.lower().replace(" ", "-").replace("—", "")[:28])

    llm = sorted((DU_AN / ".eide" / "llm").glob("*.jsonl"))
    n = sum(1 for p in llm for d in p.read_text("utf-8", errors="replace").splitlines()
            if d.strip())
    nk.ghi("Nhật ký lời gọi mô hình",
           f"{len(llm)} tệp · {n} lời gọi, mỗi lời gọi kèm nguyên văn gửi đi và trả về "
           f"({DU_AN / '.eide' / 'llm'})")
    print(f"\n{VANG}Nhật ký: {nk.md}{HET}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--buoc", default="", help="chỉ chạy các bước này, ví dụ 1-2 hoặc 2")
    ap.add_argument("--giu-du-an", action="store_true", help="không xoá dự án cũ")
    a = ap.parse_args()
    chon: set[int] | None = None
    if a.buoc:
        chon = set()
        for phan in a.buoc.split(","):
            if "-" in phan:
                x, y = phan.split("-", 1)
                chon |= set(range(int(x), int(y) + 1))
            else:
                chon.add(int(phan))
    return chay(chon, a.giu_du_an)


if __name__ == "__main__":
    raise SystemExit(main())
