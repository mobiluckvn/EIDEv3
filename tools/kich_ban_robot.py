#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kịch bản phiên robot cân bằng — từng bước người dùng gõ, và cách đối chiếu kết quả.

Tách khỏi `phien_robot.py` (hạ tầng: app, nhật ký, ảnh chụp) vì hai thứ đổi theo hai nhịp
khác nhau: hạ tầng gần như đứng yên, còn kịch bản thì thêm bước mỗi lần dự án đi xa hơn.

Sự thật để đối chiếu nằm trong `docs/robot/…v1.1.docx` — bảng 12 (bản đồ chân), bảng 30 và 33
(đấu dây A4988), bảng 91 (giá trị thanh ghi), bảng 84 (trình tự khởi tạo), bảng 83 (cấu trúc
bị cấm). Các hằng dưới đây CHÉP từ tài liệu; không suy diễn thêm.
"""

from __future__ import annotations

import pathlib
import shutil
import time
from typing import Any

# ============================================================ sự thật chép từ tài liệu
# Bảng 12 — bản đồ chân đầy đủ. (chân Arduino, cổng AVR, hướng, net)
CHAN_TAI_LIEU: list[tuple[str, str, str, str]] = [
    ("D0", "PD0", "vao", "JQ6500_TX"),
    ("D1", "PD1", "ra", "JQ6500_RX"),
    ("D2", "PD2", "vao", "SRF04_ECHO"),
    ("D3", "PD3", "ra", "SRF04_TRIG"),
    ("D4", "PD4", "ra", "DIR1"),
    ("D5", "PD5", "ra", "STEP1"),
    ("D6", "PD6", "ra", "DIR2"),
    ("D7", "PD7", "ra", "STEP2"),
    ("D10", "PB2", "ra", "BUZZER"),
    ("D11", "PB3", "ra", "WS2812_DIN"),
    ("D12", "PB4", "vao", "BUTTON"),
    ("A0", "PC0", "vao", "ADC_BAT"),
    ("A4", "PC4", "hai_chieu", "SDA"),
    ("A5", "PC5", "hai_chieu", "SCL"),
]

# Bảng 33 — mức DIR để đi tới. Hạng L: xác định bằng bài đi thẳng, không suy từ datasheet.
DIR_DI_TOI = {"phai": ("D4", "LOW"), "trai": ("D6", "HIGH")}

# Bảng 91 — giá trị thanh ghi bắt buộc.
THANH_GHI = {
    "TCCR2A": 0x02, "TCCR2B": 0x02, "OCR2A": 39, "TIMSK2": 0x02,
    "TCCR0A": 0x02, "TCCR0B": 0x03, "OCR0A": 249, "TIMSK0": 0x02,
    "TCCR1A": 0x00, "TCCR1B": 0x01,
    "UBRR0L": 207, "UCSR0A": 0x02, "UCSR0B": 0x98, "UCSR0C": 0x06,
    "TWSR": 0x00, "TWBR": 12, "TWCR": 0x04,
    "ADMUX": 0x40, "ADCSRA": 0x87,
}

# Bảng 48 — khởi tạo MPU6050.
MPU_INIT = {0x6B: 0x00, 0x1B: 0x00, 0x1C: 0x08, 0x1A: 0x03}

HANG_SO = {"F_CPU": 16_000_000, "I2C_ADDR": 0x68, "I2C_HZ": 400_000,
           "VI_BUOC": 16, "BUOC_MOI_VONG": 3200, "NGAT_US": 20,
           "BAUD_CHAN_DOAN": 9600, "BAN_KINH_BANH_MM": 32,
           "HE_SO_CHIA_AP": 3.55, "LECH_LAP_LSB": 102}


def chay(nk: Any, du_an: pathlib.Path, *, chi_buoc: str = "") -> int:
    from phien_robot import RA, TAI_LIEU, ctx_cua_bo_do, hoi, mo_app

    def lam(n: int) -> bool:
        if not chi_buoc:
            return True
        if "-" in chi_buoc:
            a, b = chi_buoc.split("-")
            return int(a) <= n <= int(b)
        return n == int(chi_buoc)

    # ------------------------------------------------------------------ 1. tạo dự án
    nk.buoc("Tạo dự án mới và mở EIDE trên nó")
    (du_an / "README.md").write_text(
        "# Robot hai bánh tự cân bằng — MOBILUCK\n\n"
        "Dự án firmware cho bo BLKLab_Balancing_Robot_Shield_v1 (ATmega328P 16 MHz).\n",
        "utf-8")
    g = mo_app(du_an)
    nk.ghi("Thư mục dự án", str(du_an))
    a0 = g.chup("mo-du-an")
    nk.ghi("Lõi đã kết nối", f"{a0.get('so_dong_hoi_thoai', 0)} dòng hội thoại, "
                             f"tab đang mở: {a0.get('tab_dang_mo', '?')}")
    nk.anh(g, "mo-du-an")
    ctx = ctx_cua_bo_do(du_an)

    # ------------------------------------------------------------------ 2. nạp tài liệu
    if lam(2):
        nk.buoc("Nạp tài liệu bàn giao phần cứng (.docx, 43 trang, 93 bảng)")
        dich = du_an / "tai-lieu" / TAI_LIEU.name
        dich.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TAI_LIEU, dich)
        nk.ghi("Đã chép tài liệu vào dự án", str(dich.relative_to(du_an)))
        loi, cc = hoi(g, nk, du_an,
                      "Chào bạn. Mình bắt đầu một dự án mới: robot hai bánh tự cân bằng của "
                      "MOBILUCK. Mình vừa chép tài liệu bàn giao phần cứng vào thư mục "
                      f"tai-lieu/{TAI_LIEU.name}. Bạn nạp tài liệu đó vào dự án giúp mình, "
                      "rồi nói cho mình biết nó gồm những gì.")
        docs = ctx.store.list("doc", limit=20)
        nk.ket(bool(docs), "Tài liệu đã vào kho dưới dạng hiện vật doc",
               "; ".join(f"{d['id']}: {d['canonical'].get('ten', '')[:60]}" for d in docs))
        nk.anh(g, "nap-tai-lieu")

    # ------------------------------------------------------------- 3. trích xuất bản đồ chân
    if lam(3):
        nk.buoc("Trích xuất bản đồ chân từ bảng trong tài liệu")
        loi, cc = hoi(g, nk, du_an,
                      "Trong tài liệu có bảng “Bảng chân đầy đủ” ở chương 4. Bạn trích xuất "
                      "bản đồ chân từ đó ra Fact giúp mình, nhớ ghi rõ mỗi chân lấy ở đâu "
                      "trong tài liệu. Sau đó liệt kê cho mình các chân đã trích được.")
        fs = ctx.store.query_facts(limit=500)
        nk.ghi("Số Fact trong kho", str(len(fs)))

        # Đối chiếu TỪNG chân của bảng 12 với Fact trong kho — không tin lời kể của tác tử.
        theo_chan: dict[str, dict[str, Any]] = {}
        for f in fs:
            sub = str(f.get("subject", ""))
            if not sub.startswith("pin:"):
                continue
            ten = sub.split(".", 1)[-1]
            theo_chan.setdefault(ten, {})[str(f.get("key"))] = str(f.get("value"))
        dung, sai = [], []
        for chan, cong, huong, net in CHAN_TAI_LIEU:
            co = theo_chan.get(chan) or theo_chan.get(cong) or {}
            ok_net = net.replace("_", " ") in co.get("net", "").replace("_", " ")
            ok_h = co.get("huong", "") == huong
            (dung if (co and ok_net and ok_h) else sai).append(
                f"{chan}→{co.get('net', '∅')}/{co.get('huong', '∅')}"
                + ("" if (co and ok_net and ok_h) else f" (tài liệu: {net}/{huong})"))
        nk.ket(len(dung) == len(CHAN_TAI_LIEU),
               f"Bản đồ chân khớp tài liệu: {len(dung)}/{len(CHAN_TAI_LIEU)} chân",
               "ĐÚNG: " + ", ".join(dung) + ("\nLỆCH: " + "; ".join(sai) if sai else ""))
        nk.ghi("Trích dẫn của một Fact chân (N1)",
               str(next((f.get("source") for f in fs
                         if str(f.get("subject", "")).startswith("pin:")), "—"))[:400])
        nk.anh(g, "trich-xuat")

    # ------------------------------------------------------------------ 4. ghim chip
    if lam(4):
        nk.buoc("Ghim hộ chiếu chip ATmega328P")
        loi, cc = hoi(g, nk, du_an,
                      "Bo này dùng ATmega328P chạy 16 MHz. Bạn ghim hộ chiếu chip cho mình "
                      "từ tài liệu đang có, rồi cho mình biết hộ chiếu ghi được những gì.")
        hc = [x for x in ctx.store.list("passport", limit=10)]
        nk.ket(bool(hc), "Hộ chiếu chip đã được ghim",
               "; ".join(f"{p['id']}: {list(p['canonical'])[:6]}" for p in hc))
        nk.anh(g, "ho-chieu")

    # ------------------------------------------------------ 5. bản đồ mạch (cây khối CKM)
    if lam(5):
        nk.buoc("Dựng bản đồ mạch: khối, Port, net — lấy từ chính Fact vừa trích")
        loi, cc = hoi(g, nk, du_an,
                      "Giờ dựng bản đồ mạch. Dùng ckm.from_pinout để MÃ dựng net và khối từ "
                      "chính Fact chân vừa trích — đừng chép tay từng net, vì bảng có 23 chân "
                      "và chép tay là chỗ sai không ai kiểm được. Sau khi nó dựng xong, bạn "
                      "rà lại kết quả: khối nào tên chưa gọn thì đặt lại bằng ckm.module_set, "
                      "rồi gộp bản đồ bằng ckm.build và nói cho mình biết bản đồ có gì.",
                      giay=1500)
        from eide.knowledge import cay as C
        from eide.knowledge import ckm as K
        cay = C.Cay.doc(ctx.store)
        phang = C.flatten(cay)
        nk.ghi("Cây khối dựng được",
               "\n".join(f"{n.get('path', ''):34} {n.get('kind', ''):9} {n['ten'][:40]}"
                          for _, n in sorted(cay.nut.items(),
                                             key=lambda x: x[1].get("path") or "")
                          if n.get("kind") in ("board", "block", "subblock", "leaf")),
               ma=True)
        nk.ghi("Netlist phẳng",
               "\n".join(f"{t:16} {', '.join(sorted(c))}" for t, c in sorted(phang.items())),
               ma=True)
        nk.anh(g, "ban-do-mach")

        # Đối chiếu net ↔ chân với bảng 12: net nào của tài liệu đã có mặt và nối đúng chân?
        chan_cua_net: dict[str, set[str]] = {}
        for ten, chan in phang.items():
            for c in chan:
                chan_cua_net.setdefault(ten.upper().replace("_", " "), set()).add(c)
        thieu, co = [], []
        for chan, cong, huong, net in CHAN_TAI_LIEU:
            kh = net.upper().replace("_", " ")
            tim = [t for t in chan_cua_net if kh in t or t in kh]
            noi = {c for t in tim for c in chan_cua_net[t]}
            dung_chan = any(c.split(".", 1)[-1] in (chan, cong) for c in noi)
            (co if (tim and dung_chan) else thieu).append(
                f"{net}@{chan}" + ("" if (tim and dung_chan) else
                                   f" (net {'có' if tim else 'KHÔNG'} trong bản đồ, "
                                   f"chân nối: {sorted(noi) or '∅'})"))
        nk.ket(len(co) >= 10,
               f"Net đúng chân theo bảng 12: {len(co)}/{len(CHAN_TAI_LIEU)}",
               "ĐÚNG: " + ", ".join(co) + ("\nCHƯA: " + "; ".join(thieu) if thieu else ""))

    # ------------------------------------------- 5b. nối cho đủ hai đầu, thêm linh kiện thật
    if lam(5):
        nk.buoc("Hoàn thiện: đặt linh kiện thật vào từng khối và nối đủ HAI đầu mỗi net")
        loi, cc = hoi(g, nk, du_an,
                      "Mình xem bản đồ rồi: các khối đã có Port đúng, nhưng bên trong khối "
                      "ngoại vi chưa có linh kiện nào, nên mỗi net mới chỉ có một đầu là chân "
                      "của vi điều khiển. Bạn thêm linh kiện thật vào từng khối và nối cho đủ "
                      "hai đầu: U2 và U3 là hai A4988 (chương 7.2 có bảng đấu dây từng chân: "
                      "STEP, DIR, EN nối GND, MS1/MS2/MS3 lên +5 V, RST nối SLP, VMOT, VDD, "
                      "1A/1B/2A/2B ra cuộn động cơ), U4 là MPU6050 nối SDA/SCL, còi, nút, "
                      "chuỗi WS2812, SRF04 và JQ6500. Mỗi net phải chạm cả chân vi điều khiển "
                      "lẫn chân linh kiện phía kia.",
                      giay=1800)
        from eide.knowledge import cay as C2
        cay = C2.Cay.doc(ctx.store)
        phang = C2.flatten(cay)
        nk.ghi("Netlist sau khi hoàn thiện",
               "\n".join(f"{t:16} {len(c)} đầu: {', '.join(sorted(c))}"
                          for t, c in sorted(phang.items())), ma=True)
        du_hai_dau = [t for t, c in phang.items() if len(set(c)) >= 2]
        nk.ket(len(du_hai_dau) >= 12,
               f"{len(du_hai_dau)}/{len(phang)} net có đủ từ hai đầu trở lên",
               "; ".join(f"{t}({len(set(c))})" for t, c in sorted(phang.items())))
        nk.anh(g, "ban-do-day-du")

    # ------------------------------------------------------------------ 6. ERC theo cây
    if lam(6):
        nk.buoc("Chạy kiểm tra điện (ERC) trên bản đồ mạch")
        loi, cc = hoi(g, nk, du_an,
                      "Bạn chạy kiểm tra điện trên bản đồ mạch này và nói cho mình biết có "
                      "phát hiện gì. Chỗ nào chưa đủ dữ kiện để kết luận thì nói thẳng là "
                      "chưa đủ, đừng kết luận là đạt.")
        bc = ctx.store.get("report:board-check") or ctx.store.get("findings:erc")
        nk.ghi("Báo cáo ERC trong kho", str((bc or {}).get("canonical", "—"))[:800], ma=True)
        nk.anh(g, "erc")

    # ------------------------------------------------------------- 7. sơ đồ nguyên lý
    if lam(7):
        nk.buoc("Sinh sơ đồ nguyên lý KiCad và vẽ ra ảnh")
        loi, cc = hoi(g, nk, du_an,
                      "Bây giờ sinh sơ đồ nguyên lý KiCad từ bản đồ mạch giúp mình: soạn "
                      "tệp SKiDL, kiểm netlist khớp bản đồ, chọn ký hiệu, xếp bố cục, ghi "
                      "tệp .kicad_sch rồi vẽ ra ảnh. Nói rõ từng bước kiểm được gì.",
                      giay=1800)
        tep = sorted(x.name for x in (du_an / "sch").glob("*")) if (du_an / "sch").exists() \
            else []
        nk.ghi("Tệp sơ đồ sinh ra", "\n".join(tep) or "— chưa có tệp nào —", ma=True)
        nk.ket(any(x.endswith(".kicad_sch") for x in tep),
               "Có tệp .kicad_sch mở được bằng KiCad", ", ".join(tep))
        nk.anh(g, "so-do")

    # ------------------------------------------------------- 8. firmware: phần logic thuần
    if lam(8):
        nk.buoc("Viết phần LOGIC của firmware (không đụng thanh ghi) để mô phỏng được")
        loi, cc = hoi(g, nk, du_an,
                      "Giờ ta viết firmware. Tách làm hai phần đã: bạn viết trước "
                      "firmware/control.h và firmware/control.c chứa phần logic THUẦN, tuyệt "
                      "đối không đụng thanh ghi AVR và không include avr/io.h — để mình biên "
                      "dịch được nó trên máy tính mà mô phỏng. Phần này gồm: lọc bù ghép góc "
                      "từ gia tốc kế và con quay, bộ PID giữ thăng bằng, và hàm quy đổi "
                      "throttle sang số nhịp 20 µs giữa hai xung bước theo đúng bảng ở mục "
                      "7.6 của tài liệu. Dùng số nguyên, không dùng số thực trong đường chạy "
                      "nhanh. Ánh xạ trục IMU và các hằng hiệu chuẩn lấy đúng theo mục 8.3 và "
                      "chương 11 của tài liệu.",
                      giay=1800)
        ds = sorted(x.name for x in (du_an / "firmware").glob("*")) \
            if (du_an / "firmware").exists() else []
        nk.ghi("Tệp firmware hiện có", ", ".join(ds) or "— chưa có —")
        ctrl = (du_an / "firmware/control.c")
        nk.ket(ctrl.exists()
               and not phu_thuoc_avr(ctrl.read_text("utf-8", errors="replace")),
               "Có control.c và nó KHÔNG phụ thuộc thanh ghi AVR (mô phỏng được)",
               f"{ctrl.stat().st_size if ctrl.exists() else 0} byte")
        nk.anh(g, "control-c")

    # ---------------------------------------------- 9. firmware: phần thanh ghi + ngắt
    if lam(9):
        nk.buoc("Viết phần THANH GHI: timer, TWI, UART, watchdog, trình tự khởi tạo")
        # Chia làm hai lượt: một lượt ĐỌC tài liệu đã tiêu hết 40 lời gọi công cụ và lượt
        # đó kết thúc mà chưa viết được dòng mã nào. Giao việc vừa một lượt là việc của
        # người dùng, không phải của tác tử.
        hoi(g, nk, du_an,
            "Trước khi viết main.c: bạn đọc mục 12.5 (thanh ghi ba bộ định thời), mục 8.4 "
            "(cấu hình khối TWI) và phụ lục A.2 (giá trị khởi tạo thanh ghi) rồi GHI từng "
            "giá trị thanh ghi thành Fact có trích dẫn — dùng fact.from_doc cho từng cái: "
            "TCCR2A, TCCR2B, OCR2A, TIMSK2, TCCR0A, TCCR0B, OCR0A, TIMSK0, TCCR1B, UBRR0L, "
            "UCSR0A, UCSR0B, UCSR0C, TWSR, TWBR, TWCR, ADMUX, ADCSRA, và địa chỉ I2C của "
            "MPU6050. Có Fact rồi thì lát nữa bạn mới viết được mã mà không vướng chốt hằng "
            "số. Chưa viết mã ở lượt này.",
            giay=1800)
        loi, cc = hoi(g, nk, du_an,
                      "Giờ viết firmware/main.c theo đúng bốn mục bạn vừa đọc. Dùng thanh ghi "
                      "thật: Timer2 CTC chia 8 OCR2A=39 sinh nhịp 20 µs cho tầng sinh xung "
                      "bước; Timer0 CTC chia 64 OCR0A=249 làm nhịp 1 ms cho bộ lập lịch; "
                      "Timer1 chạy tự do chia 1 để đo; TWI 400 kHz với TWBR=12, TWSR=0; UART0 "
                      "9600 baud dùng U2X với UBRR0=207; MPU6050 ở địa chỉ 0x68 khởi tạo bốn "
                      "thanh ghi 0x6B, 0x1B, 0x1C, 0x1A rồi đọc khối 14 byte từ 0x3B; ADC0 "
                      "đọc điện áp pin. Trình tự khởi tạo đúng 11 bước, đọc–xoá MCUSR rồi tắt "
                      "watchdog là việc đầu tiên. Không dùng delay(), String, malloc, pulseIn "
                      "hay số thực trong ISR. Gọi phần logic trong control.c, đừng viết lại "
                      "thuật toán. Viết thẳng ra tệp, đừng đọc thêm tài liệu nữa.",
                      giay=2400)
        # Mã thanh ghi nằm ở `main.c` hay `firmware.ino` là chuyện của chuẩn dự án, không
        # phải chuyện của phép đo. Hỏi "có mã thanh ghi không", đừng hỏi "có tệp tên này không".
        tep = sorted(x.name for x in (du_an / "firmware").glob("*")
                     if x.suffix in (".c", ".h", ".ino", ".cpp"))
        nk.ket(bool(tep), "Có mã firmware trong thư mục firmware/", ", ".join(tep) or "trống")
        src = nguon_firmware(du_an / "firmware")
        if src.strip():
            tg = thanh_ghi_trong_ma(src)
            nk.ghi("Thanh ghi đọc được từ mã",
                   "\n".join(f"{k:8} = 0x{v:02X} ({v})" for k, v in sorted(tg.items())),
                   ma=True)
            dung = {k: v for k, v in THANH_GHI.items() if tg.get(k) == v}
            lech = {k: (v, tg.get(k)) for k, v in THANH_GHI.items() if tg.get(k) != v}
            nk.ket(len(dung) >= 14,
                   f"Giá trị thanh ghi khớp bảng 91: {len(dung)}/{len(THANH_GHI)}",
                   "ĐÚNG: " + ", ".join(sorted(dung))
                   + ("\nLỆCH/THIẾU: " + "; ".join(
                       f"{k} cần 0x{c:02X}, mã có {'0x%02X' % t if t is not None else '∅'}"
                       for k, (c, t) in sorted(lech.items())) if lech else ""))

            import re as _re
            pham = [(mo_ta, m.group(0)) for mau, mo_ta in DIEU_CAM
                    for m in [_re.search(mau, src)] if m]
            nk.ket(not pham, "Không dùng cấu trúc bị cấm ở bảng 83",
                   "; ".join(f"{t} ({d})" for d, t in pham) or "sạch")
            nk.ket("MCUSR" in src and src.index("MCUSR") < src.index("wdt_disable")
                   if "wdt_disable" in src else False,
                   "Đọc–xoá MCUSR TRƯỚC khi tắt watchdog (mục 13.2)",
                   "MCUSR ở vị trí " + str(src.find("MCUSR"))
                   + ", wdt_disable ở " + str(src.find("wdt_disable")))
        nk.anh(g, "main-c")

    # ------------------------------------------------------------------ 10. biên dịch
    if lam(10):
        nk.buoc("Biên dịch firmware cho ATmega328P và sửa tới khi sạch lỗi")
        loi, cc = hoi(g, nk, du_an,
                      "Biên dịch firmware giúp mình. Có lỗi thì sửa rồi biên dịch lại cho tới "
                      "khi sạch, và nói cho mình biết nó chiếm bao nhiêu Flash và SRAM so với "
                      "hạn mức của chip.",
                      giay=2400)
        a = ctx.store.get("build:firmware")
        canon = (a or {}).get("canonical") or {}
        nk.ghi("Hiện vật build trong kho",
               "\n".join(f"{k}: {v}" for k, v in canon.items()
                          if k in ("dat", "cong_cu", "tep_ra", "flash", "sram",
                                   "ty_le_flash", "ty_le_sram", "so_loi", "so_canh_bao")),
               ma=True)
        nk.ket(bool(canon.get("dat")),
               "Firmware biên dịch được bằng chuỗi công cụ THẬT",
               f"{canon.get('cong_cu', '?')} → {canon.get('tep_ra', '—')} · "
               f"Flash {canon.get('flash', 0)} B, SRAM {canon.get('sram', 0)} B")
        nk.anh(g, "bien-dich")

    # ------------------------------------------------------------------ 11. mô phỏng
    if lam(11):
        nk.buoc("Mô phỏng vòng điều khiển bằng chính mã logic của firmware")
        # Một lượt viết, một lượt chạy–sửa. Gộp lại thì lượt đầu tiêu hết ngân sách vào
        # việc đọc và chưa viết được dòng nào — đã xảy ra đúng như vậy.
        hoi(g, nk, du_an,
            "Viết tệp sim/plant.c (chỉ tệp này thôi, đừng đọc lại tài liệu): một mô hình con "
            "lắc ngược hai bánh và hàm main(). Mô hình: trạng thái gồm góc nghiêng, tốc độ "
            "góc, vị trí và tốc độ bánh; mỗi bước 4 ms, gia tốc góc = g/L·sin(góc) trừ đóng "
            "góp của gia tốc bánh; throttle do control.c trả về quy ra tốc độ bánh theo đúng "
            "bảng ở mục 7.6. Sinh số đo IMU giả từ góc thật (gia tốc kế và con quay, cùng tỷ "
            "lệ LSB như tài liệu) rồi gọi control_system_step của firmware/control.c — mô "
            "phỏng phải chạy ĐÚNG mã đó, không viết lại thuật toán. Chạy 5 giây mô phỏng từ "
            "góc nghiêng ban đầu 3 độ, rồi in ra MỘT dòng JSON gồm: dat (true nếu góc luôn "
            "dưới 15 độ và 2 giây cuối dưới 2 độ), goc_max_do, goc_cuoi_do, thoi_gian_s.",
            giay=2400)
        loi, cc = hoi(g, nk, du_an,
                      "Giờ chạy mô phỏng bằng công cụ sim.run. Nếu nó không biên dịch được "
                      "hoặc robot ngã thì sửa sim/plant.c hoặc tham số PID trong control.c "
                      "rồi chạy lại, tối đa vài vòng, và nói cho mình biết kết quả thật — "
                      "đừng kết luận đạt nếu nó chưa đạt.",
                      giay=2400)
        a = ctx.store.get("sim_result:can-bang")
        canon = (a or {}).get("canonical") or {}
        nk.ghi("Kết quả mô phỏng trong kho", str(canon.get("ket_qua") or canon)[:600], ma=True)
        nk.ket(bool(canon.get("dat")),
               "Mô phỏng chạy được và kết luận robot giữ được thăng bằng",
               str(canon.get("vi_sao_khong_dat") or canon.get("ket_qua"))[:200])
        nk.anh(g, "mo-phong")

    # --------------------------------------------- 12. sửa cho tới khi robot đứng được
    if lam(12):
        nk.buoc("Sửa vòng điều khiển cho tới khi robot đứng được trong mô phỏng")
        for vong in range(4):
            a = ctx.store.get("sim_result:can-bang")
            kq = ((a or {}).get("canonical") or {}).get("ket_qua") or {}
            if kq.get("dat") is True:
                break
            loi, cc = hoi(g, nk, du_an,
                          f"Mô phỏng đang cho kết quả {kq or 'chưa có'} — robot chưa đứng "
                          "được. Mục 11.5 của tài liệu nói có ba chỗ có thể đảo dấu trong "
                          "vòng phản hồi (chiều trục cảm biến, chiều lắp động cơ, dấu đầu ra "
                          "bộ điều khiển). Bạn xem lại dấu và hệ số PID trong "
                          "firmware/control.c, sửa, rồi chạy lại sim.run. Nói rõ bạn đổi gì "
                          "và vì sao. Đừng sửa mô hình vật lý để nó đẹp lên — sửa bộ điều "
                          "khiển.",
                          giay=2400)
            a = ctx.store.get("sim_result:can-bang")
            kq = ((a or {}).get("canonical") or {}).get("ket_qua") or {}
            nk.ghi(f"Kết quả mô phỏng sau vòng sửa {vong + 1}", str(kq)[:300])
        a = ctx.store.get("sim_result:can-bang")
        kq = ((a or {}).get("canonical") or {}).get("ket_qua") or {}
        nk.ket(kq.get("dat") is True,
               "Robot giữ được thăng bằng trong mô phỏng",
               f"góc lớn nhất {kq.get('goc_max_do')}°, góc cuối {kq.get('goc_cuoi_do')}°, "
               f"chạy {kq.get('thoi_gian_s')} s")
        nk.anh(g, "mo-phong-dat")

    # ------------------------------------- 13. bù phần firmware còn thiếu so với tài liệu
    if lam(13):
        nk.buoc("Đối chiếu firmware với bảng 91 và bù phần còn thiếu")
        src = nguon_firmware(du_an / "firmware")
        tg = thanh_ghi_trong_ma(src)
        thieu = {k: v for k, v in THANH_GHI.items() if tg.get(k) != v}
        nk.ghi("Thanh ghi còn lệch hoặc thiếu",
               "\n".join(f"{k}: tài liệu 0x{v:02X}, mã "
                          + (f"0x{tg[k]:02X}" if k in tg else "KHÔNG CÓ")
                          for k, v in sorted(thieu.items())) or "không thiếu gì", ma=True)
        if thieu:
            loi, cc = hoi(g, nk, du_an,
                          "Mình đối chiếu firmware với bảng giá trị thanh ghi ở phụ lục A.2 "
                          "của tài liệu thì thấy còn thiếu: "
                          + "; ".join(f"{k} phải là 0x{v:02X}" for k, v in sorted(thieu.items()))
                          + ". Bạn bổ sung đúng những chỗ đó vào firmware (nhớ Timer0 là nhịp "
                            "1 ms của bộ lập lịch, mục 12.5), rồi biên dịch lại và cho mình "
                            "biết kết quả.",
                          giay=2400)
            src = nguon_firmware(du_an / "firmware")
            tg = thanh_ghi_trong_ma(src)
        khop = {k: v for k, v in THANH_GHI.items() if tg.get(k) == v}
        nk.ket(len(khop) >= 18,
               f"Giá trị thanh ghi khớp bảng 91: {len(khop)}/{len(THANH_GHI)}",
               "; ".join(f"{k}=0x{v:02X}" for k, v in sorted(khop.items())))
        a = ctx.store.get("build:firmware")
        canon = (a or {}).get("canonical") or {}
        nk.ket(bool(canon.get("dat")), "Firmware vẫn biên dịch được sau khi bổ sung",
               f"Flash {canon.get('flash', 0)} B · SRAM {canon.get('sram', 0)} B")
        nk.anh(g, "firmware-du")

    nk.buoc("Kết thúc phần đã chạy", loai="ket")
    nk.ghi("Nhật ký", str(RA / "NHAT-KY.md"))
    return 0


# ==================================================================== đối chiếu firmware
# Tên bit của AVR dùng trong biểu thức thanh ghi. Chép từ datasheet ATmega328P; cần thiết vì
# firmware viết `(1 << WGM21)` chứ không viết `0x02`, và đối chiếu phải hiểu cả hai.
BIT_AVR = {
    "WGM20": 0, "WGM21": 1, "WGM22": 3, "CS20": 0, "CS21": 1, "CS22": 2, "OCIE2A": 1,
    "WGM00": 0, "WGM01": 1, "WGM02": 3, "CS00": 0, "CS01": 1, "CS02": 2, "OCIE0A": 1,
    "CS10": 0, "CS11": 1, "CS12": 2, "WGM12": 3, "OCIE1A": 1,
    "U2X0": 1, "UCSZ00": 1, "UCSZ01": 2, "TXEN0": 3, "RXEN0": 4, "RXCIE0": 7, "UDRIE0": 5,
    "TWEN": 2, "TWIE": 0, "TWINT": 7, "TWSTA": 5, "TWSTO": 4, "TWEA": 6,
    "REFS0": 6, "REFS1": 7, "ADEN": 7, "ADSC": 6, "ADIE": 3,
    "ADPS0": 0, "ADPS1": 1, "ADPS2": 2, "ADC0D": 0,
    "WDRF": 3, "WDCE": 4, "WDE": 3, "PB5": 5, "PD5": 5, "PD7": 7,
}


def _tinh_bieu_thuc(bt: str) -> int | None:
    """Tính một biểu thức thanh ghi đơn giản: `(1 << WGM21) | (1 << CS21)`, `0x27`, `39`.

    Chỉ nhận dịch trái, hoặc, và, số — đủ cho mọi giá trị trong bảng 91, và **không** chạy mã
    tuỳ ý: đây là đọc mã người khác viết, nên nó phải đọc được mà không tin được.
    """
    import re as _re

    t = bt.strip().rstrip(";").strip()
    if not t or len(t) > 200:
        return None
    t = _re.sub(r"\b([A-Z][A-Z0-9_]*)\b", lambda m: str(BIT_AVR.get(m.group(1), "\x00")), t)
    if "\x00" in t or not _re.fullmatch(r"[\s0-9xXa-fA-F()<>|&+~-]*", t):
        return None
    try:
        return int(eval(t, {"__builtins__": {}}, {})) & 0xFF   # noqa: S307 — đã lọc ký tự
    except Exception:
        return None


def bo_chu_thich(nguon: str) -> str:
    """Bỏ `//…` và `/*…*/`.

    Cần vì một phép so chuỗi trên mã nguồn sẽ trúng cả chú thích. Đo được: ca kiểm
    "control.c không phụ thuộc AVR" báo ĐỎ cho một tệp sạch, vì trong đầu tệp có dòng chú
    thích *"Không chứa mã phụ thuộc phần cứng, không include avr/io.h"*. Phép đo đọc lời
    người viết thay vì đọc mã họ viết.
    """
    import re as _re

    s = _re.sub(r"/\*.*?\*/", " ", nguon, flags=_re.S)
    return _re.sub(r"//[^\n]*", " ", s)


def phu_thuoc_avr(nguon: str) -> bool:
    """Tệp này có đụng phần cứng AVR không — đọc CHỈ THỊ include, không đọc chú thích."""
    import re as _re

    return bool(_re.search(r"#\s*include\s*[<\"]avr/", bo_chu_thich(nguon)))


def nguon_firmware(thu_muc: pathlib.Path) -> str:
    """Toàn bộ mã firmware: `.c`, `.h` VÀ `.ino`.

    Bỏ `.ino` là bỏ đúng chỗ mã thanh ghi nằm khi dự án theo chuẩn Arduino — phép đo khi đó
    báo "0 thanh ghi" cho một firmware đầy thanh ghi, hoặc tệ hơn: báo một con số đúng ở lần
    chạy này và sai ở lần sau, tuỳ tác tử đặt mã vào tệp nào.
    """
    ra = []
    for x in sorted(thu_muc.glob("*")):
        if x.suffix in (".c", ".h", ".ino", ".cpp"):
            ra.append(x.read_text("utf-8", errors="replace"))
    return "\n".join(ra)


def thanh_ghi_trong_ma(nguon: str) -> dict[str, int]:
    """`{tên thanh ghi: giá trị}` đọc từ mã nguồn firmware."""
    import re as _re

    nguon = bo_chu_thich(nguon)
    ra: dict[str, int] = {}
    for m in _re.finditer(r"^\s*([A-Z][A-Z0-9_]{2,8})\s*=\s*([^;]+);", nguon, _re.M):
        gt = _tinh_bieu_thuc(m.group(2))
        if gt is not None:
            ra[m.group(1)] = gt
    return ra


# Bảng 83 — cấu trúc bị cấm, và vì sao. Mẫu tìm phải đủ hẹp để không báo nhầm.
DIEU_CAM = [
    (r"\bmalloc\s*\(|\bfree\s*\(|\bnew\s+[A-Za-z]", "cấp phát động (2 KB SRAM, không MMU)"),
    (r"\bString\b", "lớp String của Arduino gây phân mảnh SRAM"),
    (r"\bdelay(Microseconds)?\s*\(", "delay() chặn tầng dưới, làm trượt hạn"),
    (r"\bpulseIn\s*\(", "pulseIn chiếm vi điều khiển hàng chục ms"),
    (r"\bSerial\.print", "Serial.print trong firmware này dùng UART thanh ghi, không dùng lớp"),
]
