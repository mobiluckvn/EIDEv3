#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phiên làm việc THẬT: dựng một RTOS mới cho STM32F469I-DISCO, bỏ FreeRTOS.

    .venv/bin/python tools/phien_rtos.py --giai-doan 1

Đây KHÔNG phải một bộ kiểm — nó là một phiên làm việc có thật, chia giai đoạn để người xem
được từng chặng rồi mới cho đi tiếp. Mỗi giai đoạn in ra: tác tử gọi công cụ gì, để lại hiện
vật gì, và nói gì.

Đích: màn hình LCD 800×480 chạy đúng như bản FreeRTOS hiện có — cùng giao diện, cùng cảm ứng,
cùng các tác vụ chạy song song — mà không còn một dòng FreeRTOS nào.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import GiaoDien                                       # noqa: E402

DU_AN = REPO / "du-lieu/rtos-ptit"


def _so_cai() -> list[dict]:
    p = DU_AN / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for d in p.read_text("utf-8", errors="replace").splitlines():
        if d.strip():
            try:
                ra.append(json.loads(d))
            except ValueError:
                pass
    return ra


def _cc(tu: int = 0) -> list[str]:
    return [(o.get("data") or {}).get("tool") for o in _so_cai()[tu:]
            if o.get("kind") in ("tool_use", "subagent_tool")
            and (o.get("data") or {}).get("tool")]


def mo() -> GiaoDien:
    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    time.sleep(1.5)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    # Chạy THẲNG nhị phân, không qua `open -a`.
    #
    # `open` không truyền biến môi trường sang ứng dụng, mà phiên này cần `EIDE_GHI_LLM=1` để
    # ghi lại toàn bộ lời gọi mô hình — cả prompt gửi đi lẫn phản hồi. Yêu cầu của anh Công.
    import os

    moi_truong = {**os.environ, "EIDE_GHI_LLM": "1"}
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env=moi_truong,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g = GiaoDien(DU_AN)
    g.san_sang(45)
    return g


def _luot(g: GiaoDien, cau: str, giay: int = 900) -> dict:
    n = len(_so_cai())
    print(f"\n▸ BẠN: {cau[:150]}{'…' if len(cau) > 150 else ''}")
    g.go(cau)
    a = g.doi_xong(giay)
    print(f"  công cụ: {', '.join(dict.fromkeys(_cc(n))) or '(không gọi công cụ nào)'}")
    loi = (a.get("loi_tac_tu_cuoi") or "").strip()
    print(f"  TÁC TỬ: {loi[:900]}")
    return a


def duyet_het(g: GiaoDien, lan: int = 4) -> None:
    """Duyệt mọi thẻ cổng đang chờ — người dùng đã đồng ý cho làm việc này."""
    for _ in range(lan):
        a = g.chup("cho-duyet")
        cho = a.get("the_dang_cho") or []
        if not cho:
            return
        for the in cho:
            gid = the.get("id") or the.get("gate_id")
            print(f"  ⇢ duyệt cổng {gid}")
            g.quyet_cong(gid, True, "Duyệt, làm đi.")
        g.doi_xong(900)


def giai_doan_1(g: GiaoDien) -> None:
    _luot(g, "Mình muốn bỏ hẳn FreeRTOS và tự viết một hệ điều hành thời gian thực mới cho "
             "chính con STM32F469NI trên bo này. Đích cuối: màn hình LCD chạy y như bản "
             "FreeRTOS hiện tại — cùng giao diện, cùng cảm ứng, cùng các tác vụ song song.\n\n"
             "Trong thư mục `tham-khao/` có nguyên bản `main-freertos.c` và cấu hình của nó; "
             "`firmware/` đã có sẵn driver LCD, cảm ứng, startup, linker script. "
             "Bạn ĐỌC KỸ trước đã, rồi cho mình một bản PHÂN TÍCH: bản hiện tại dùng đúng "
             "những API nào của FreeRTOS, mỗi API ấy đòi hỏi gì ở tầng dưới, và khối lượng "
             "thật sự phải tự viết là bao nhiêu. Chưa viết mã vội nhé.", 900)


def giai_doan_2(g: GiaoDien) -> None:
    _luot(g, "Tốt. Giờ tới phần kiến trúc: cho mình vài hướng thiết kế khác nhau cho cái "
             "nhân RTOS này (ví dụ khác nhau ở cách lập lịch, cách chuyển ngữ cảnh, cách làm "
             "hàng đợi), so sánh chúng bằng tiêu chí đo được — RAM tốn bao nhiêu, độ trễ "
             "chuyển tác vụ, độ phức tạp, rủi ro. Rồi khuyến nghị một hướng và nói rõ vì sao "
             "loại các hướng kia.", 900)
    duyet_het(g)


def giai_doan_3(g: GiaoDien) -> None:
    _luot(g, "Mình chọn hướng bạn khuyến nghị. Giờ lập kế hoạch thực thi: chia nhỏ ra từng "
             "bước làm được, mỗi bước để lại một tệp cụ thể, và nói rõ cấu trúc mã — sẽ có "
             "những tệp nào, ranh giới giữa chúng ở đâu. Nhớ có bước biên dịch để kiểm.", 900)
    duyet_het(g)


def giai_doan_4(g: GiaoDien) -> None:
    """Lập kế hoạch thực thi. Luật `E6009` đòi kế hoạch viết mã mới phải có bước chọn kiến
    trúc — ADR vừa chốt ở giai đoạn 3 thoả điều đó."""
    _luot(g, "Phương án đã chốt rồi. Giờ lập kế hoạch thực thi bằng `plan.enter` nhé: chia "
             "nhỏ ra từng bước làm được, mỗi bước để lại MỘT TỆP cụ thể, và nói rõ cấu trúc "
             "mã — sẽ có những tệp nào trong `firmware/rtos/`, ranh giới giữa chúng ở đâu. "
             "Nhớ có bước biên dịch để kiểm.", 900)
    duyet_het(g)


def giai_doan_5(g: GiaoDien, vong: int = 8) -> None:
    """Thực thi: giục từng chặng, duyệt cổng, dừng khi biên dịch ra tệp ảnh."""
    for i in range(vong):
        print(f"\n══ vòng {i + 1}/{vong} ══")
        _luot(g, "Làm tiếp bước kế tiếp trong kế hoạch nhé.", 900)
        duyet_het(g)
        anh = list(DU_AN.rglob("*.elf")) + list(DU_AN.rglob("*.bin"))
        if anh:
            print(f"\n  ✓ đã có tệp ảnh: {[x.name for x in anh]}")
            break


def giai_doan_6(g: GiaoDien, vong: int = 6) -> None:
    """Ảnh vừa dựng THIẾU driver — bắt dựng lại cho đủ, rồi nạp và xem màn hình."""
    _luot(g, "Ảnh vừa dựng ra chỉ 1 416 byte và trong đó KHÔNG có một ký hiệu LCD, UI hay "
             "Touch nào — tức driver màn hình không hề được biên dịch vào. Bạn biên dịch lại "
             "cho ĐỦ toàn bộ `firmware/` (kể cả ui.c, touch.c, ui_state.c, startup.c và phần "
             "vendor cần thiết), rồi đối chiếu kích thước với bản FreeRTOS cũ khoảng 263 KB "
             "Flash. Đừng báo xong khi ảnh còn thiếu tệp.", 900)
    duyet_het(g)
    for i in range(vong):
        anh = DU_AN / ".eide" / "build" / "mach.bin"
        if anh.exists() and anh.stat().st_size > 50_000:
            print(f"\n  ✓ ảnh đã đủ lớn: {anh.stat().st_size} B")
            return
        print(f"\n══ dựng lại, vòng {i + 1}/{vong} ══")
        _luot(g, "Chưa đủ. Làm tiếp cho tới khi ảnh chứa đủ driver nhé.", 900)
        duyet_het(g)


def giai_doan_7(g: GiaoDien) -> None:
    """Nạp lên bo thật rồi đọc lại khung hình để xem màn hình có đúng không."""
    _luot(g, "Bo đã cắm vào máy rồi. Bạn nạp firmware này lên bo, đọc ngược lại Flash để "
             "xác nhận đúng byte, rồi chụp khung hình LCD ra PNG cho mình xem màn hình đang "
             "hiện gì.", 1200)
    duyet_het(g, 6)


def giai_doan_8(g: GiaoDien, vong: int = 6) -> None:
    """Đưa về NGANG bản FreeRTOS: đủ 6 tác vụ, LED, nút, cảm ứng — rồi nạp và xem lại."""
    _luot(g, "Màn hình lên rồi, nhân chạy tốt. Nhưng mới có 3 tác vụ, trong khi bản FreeRTOS "
             "trong `tham-khao/main-freertos.c` có SÁU: vTaskLED1 (1000 ms), vTaskLED2 "
             "(400 ms), vTaskButton (quét nút USER PA0, chống rung 30 ms), vTaskLED3 (chờ "
             "hàng đợi), vTaskMonitor, và vTaskLCD (cảm ứng 40 ms, đổi trang). Bạn viết lại "
             "`firmware/main.c` cho ĐỦ sáu tác vụ ấy trên nhân mới, giữ nguyên hành vi và "
             "mức ưu tiên. Xong thì biên dịch, nạp, và chụp lại màn hình.", 1200)
    duyet_het(g, 6)
    for i in range(vong):
        n = len(list((DU_AN / "firmware").rglob("*.c")))
        print(f"\n══ vòng {i + 1}/{vong} ══")
        _luot(g, "Làm tiếp nhé — chưa xong thì đi tiếp, xong rồi thì nạp và chụp màn hình.",
              1200)
        duyet_het(g, 6)


GIAI_DOAN = {1: giai_doan_1, 2: giai_doan_2, 3: giai_doan_3, 4: giai_doan_4,
             5: giai_doan_5, 6: giai_doan_6, 7: giai_doan_7, 8: giai_doan_8}


def main() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--giai-doan", type=int, default=1)
    ap.add_argument("--tiep", action="store_true", help="dùng app đang mở")
    a = ap.parse_args()

    # Mỗi giai đoạn MỞ LẠI app. EIDE vốn nối tiếp phiên cũ từ sổ cái (<resume>), nên
    # không mất gì — và cách này còn chạy qua đúng đường khôi phục mỗi lần.
    g = mo()
    if False:
        # KHÔNG đợi `kenh_mo`: nó chỉ phát một lần lúc app mở, mà `GiaoDien` vừa dọn sạch
        # outbox. Hỏi một ảnh chụp là đủ để biết app còn sống.
        g.chup("tiep")
    GIAI_DOAN[a.giai_doan](g)

    print("\n" + "─" * 88)
    nk = sorted((DU_AN / ".eide" / "llm").glob("*.jsonl")) if (DU_AN / ".eide" / "llm").exists() else []
    if nk:
        import json as _j

        n = sum(1 for _ in nk[-1].open("r", encoding="utf-8"))
        print(f"nhật ký LLM: {nk[-1].relative_to(DU_AN)} — {n} lời gọi, "
              f"{nk[-1].stat().st_size // 1024} KB")
    print("hiện vật trong dự án:")
    for x in sorted(DU_AN.rglob("*")):
        if x.is_file() and ".eide" not in x.parts and "vendor" not in x.parts \
                and x.suffix in (".md", ".c", ".h", ".s", ".ld"):
            print(f"   {x.relative_to(DU_AN)}  ({x.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
