#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ước lượng PERT: nếu một đội người làm tay thì mất bao nhiêu ngày công và bao nhiêu tiền.

    python tools/uoc_luong_pert.py            # chạy cả ba bảng, kèm phép tự kiểm
    python tools/uoc_luong_pert.py riscv      # một bảng

Vì sao có tệp này thay vì gõ số vào Markdown: bảng ước lượng đầu tiên (robot 04/10) được tính
tay, và mọi con số dẫn xuất — độ lệch chuẩn, phần theo vai, ba kịch bản tiền — nằm rải trong
một tệp Markdown không ai tính lại được. Bảng thứ hai và thứ ba mà cũng gõ tay thì ba bảng sẽ
trôi khỏi nhau, và không ai biết chúng có cùng phương pháp không.

Nên: **bảng robot nằm ngay trong tệp này làm phép tự kiểm**. Chạy script là nó tính lại và so
với con số đã in trong `docs/robot-sinhvien/phien-sinhvien-04-10/SO-SANH-VOI-NGUOI.md`. Lệch
một chữ số là nó kêu. Hai bảng mới vì thế dùng **đúng** phương pháp ấy, chứng minh được.

## Phương pháp

* mỗi dòng việc ba mức — nhanh / thường / chậm, đơn vị **ngày công**;
* kỳ vọng PERT `(nhanh + 4 × thường + chậm) / 6`;
* độ lệch chuẩn tổng `sqrt(Σ((chậm − nhanh) / 6)²)` — cộng phương sai, nên nó giả định các
  dòng **độc lập**; chỗ này là một giả định, không phải một phép đo (xem "Điều nó không nói");
* quản lý dự án tính thêm **20 %** tổng ngày công;
* tiền: lương tháng ÷ **21** ngày làm việc × **1,4** (bảo hiểm, chỗ ngồi, thiết bị).

## Điều bảng này KHÔNG nói

Ba mức của mỗi dòng là **phán đoán**, không phải số đo — không có bộ dữ liệu lịch sử nào của
đội nào ở đây. Nên con số ra là một **thang so sánh giữa ba việc dùng chung một thước**, không
phải một lời hứa về chi phí. Và giả định độc lập làm độ lệch chuẩn **hẹp hơn** thực tế: trong
một dự án thật, việc trượt thường trượt cùng nhau.
"""
from __future__ import annotations

import math
import sys

# Lương tháng, triệu đồng — (thấp, giữa, cao). Giữ y nguyên bảng của lần ước lượng đầu để ba
# việc so được với nhau; đổi ở đây là đổi cho cả ba.
LUONG = {"Senior": (40, 55, 70), "Mid": (20, 27, 35), "QA": (15, 20, 25), "QL": (35, 50, 65)}
NGAY_CONG_THANG = 21
HE_SO_PHI = 1.4
TY_LE_QUAN_LY = 0.20


def pert(o: float, m: float, p: float) -> float:
    return (o + 4 * m + p) / 6


class Bang:
    def __init__(self, ten: str, dong: list[tuple[str, str, float, float, float]]):
        self.ten = ten
        self.dong = dong

    @property
    def tong(self) -> float:
        return sum(pert(o, m, p) for _, _, o, m, p in self.dong)

    @property
    def sd(self) -> float:
        return math.sqrt(sum(((p - o) / 6) ** 2 for _, _, o, m, p in self.dong))

    @property
    def theo_vai(self) -> dict[str, float]:
        d: dict[str, float] = {}
        for _, vai, o, m, p in self.dong:
            d[vai] = d.get(vai, 0.0) + pert(o, m, p)
        return d

    @property
    def quan_ly(self) -> float:
        return self.tong * TY_LE_QUAN_LY

    def tien(self, muc: int) -> tuple[float, float]:
        """(tiền phát triển, tiền kèm quản lý) — triệu đồng."""
        pt = sum(ng * LUONG[v][muc] / NGAY_CONG_THANG * HE_SO_PHI
                 for v, ng in self.theo_vai.items())
        ql = self.quan_ly * LUONG["QL"][muc] / NGAY_CONG_THANG * HE_SO_PHI
        return pt, pt + ql

    def markdown(self) -> str:
        d = [f"| Việc | Vai | Nhanh | Thường | Chậm | **Ngày công** |",
             "|---|---|---|---|---|---|"]
        for ten, vai, o, m, p in self.dong:
            d.append(f"| {ten} | {vai} | {o:g} | {m:g} | {p:g} | **{pert(o, m, p):.2f}** |")
        no = sum(o for _, _, o, _, _ in self.dong)
        nm = sum(m for _, _, _, m, _ in self.dong)
        np_ = sum(p for _, _, _, _, p in self.dong)
        d.append(f"| **TỔNG** | | **{no:g}** | **{nm:g}** | **{np_:g}** | "
                 f"**{self.tong:.1f} ngày công** |")
        return "\n".join(d)

    def in_ra(self) -> None:
        print(f"\n=== {self.ten}")
        print(f"  tổng {self.tong:.1f} ngày công · độ lệch chuẩn ±{self.sd:.1f}")
        print(f"  ~68 %: {self.tong - self.sd:.0f}–{self.tong + self.sd:.0f} · "
              f"~95 %: {self.tong - 2 * self.sd:.0f}–{self.tong + 2 * self.sd:.0f}")
        print("  theo vai: " + " · ".join(
            f"{v} {n:.1f} ({n / self.tong * 100:.0f} %)"
            for v, n in sorted(self.theo_vai.items(), key=lambda x: -x[1])))
        print(f"  quản lý (20 %): {self.quan_ly:.1f}")
        for i, nhan in enumerate(("Thấp", "Giữa", "Cao")):
            pt, kq = self.tien(i)
            print(f"  {nhan:5}: phát triển {pt:.1f} tr · kèm quản lý ≈ {kq:.0f} tr")


# =========================================================================== phép TỰ KIỂM
#
# Bảng robot 04/10, chép nguyên văn từ `SO-SANH-VOI-NGUOI.md` §2. Nó ở đây KHÔNG phải để tính
# lại — nó ở đây để chứng minh script này dùng đúng phương pháp đã in trong tài liệu ấy.
ROBOT = Bang("Robot hai bánh — làm lại 04/10 (phép tự kiểm)", [
    ("Đọc tài liệu phần cứng và phụ lục mốc NGƯỜI, lập bản đồ chân", "Senior", 1, 2, 4),
    ("Dựng bảng điều kiện nghiệm thu đối chiếu được", "Mid", 1, 2, 4),
    ("Thiết kế cấu trúc 10 mô-đun, chốt phân tầng", "Senior", 1, 2, 4),
    ("Thiết kế máy trạng thái 7 trạng thái", "Mid", 0.5, 1, 2),
    ("Hàm ngắt 50 kHz: 0 số thực, 0 phép chia", "Senior", 1, 3, 8),
    ("I2C bare-metal, MPU6050, bộ lọc bù", "Mid", 1, 2, 4),
    ("PID và quy đổi ngõ ra sang chu kỳ bước", "Senior", 1, 2, 5),
    ("Máy trạng thái, đo pin bằng ADC, chế độ khoá khi chạy USB", "Mid", 1, 2, 3),
    ("UART vòng đệm, bản tin 10 trường có số thứ tự", "Mid", 1, 2, 4),
    ("Gỡ lỗi trên bo tới khi robot đứng", "Senior", 2, 5, 12),
    ("Đo nghiệm thu: tần số ISR, objdump, chu kỳ vòng", "Senior", 1, 2, 5),
    ("Bộ kiểm trên máy và đo độ nhạy bộ kiểm", "QA", 1, 2, 4),
    ("Tài liệu và báo cáo", "Mid", 1, 2, 4),
])

# Con số đã in trong tài liệu. Script phải tái lập ĐÚNG từng cái.
ROBOT_DA_IN = {"tong": 32.1, "sd": 2.6, "Senior": 18.2, "Mid": 11.7, "QA": 2.2,
               "quan_ly": 6.4, "tien": [(66.3, 81), (90.6, 112), (115.8, 144)]}


def tu_kiem() -> bool:
    ok = True

    def so(ten, duoc, mong, dung_sai=0.05):
        nonlocal ok
        dat = abs(duoc - mong) <= dung_sai
        ok = ok and dat
        print(f"  {'✓' if dat else '✗'} {ten:22} tính {duoc:7.1f}  ·  tài liệu in {mong:7.1f}")

    print("=== TỰ KIỂM: tính lại bảng robot 04/10 và so với con số đã in")
    so("tổng ngày công", ROBOT.tong, ROBOT_DA_IN["tong"])
    so("độ lệch chuẩn", ROBOT.sd, ROBOT_DA_IN["sd"])
    for v in ("Senior", "Mid", "QA"):
        so(f"ngày công {v}", ROBOT.theo_vai[v], ROBOT_DA_IN[v])
    so("quản lý 20 %", ROBOT.quan_ly, ROBOT_DA_IN["quan_ly"])
    for i, (pt, kq) in enumerate(ROBOT_DA_IN["tien"]):
        so(f"tiền mức {i} — phát triển", ROBOT.tien(i)[0], pt, 0.1)
        so(f"tiền mức {i} — kèm QL", ROBOT.tien(i)[1], kq, 0.6)
    print("  → " + ("phương pháp KHỚP tài liệu, hai bảng dưới dùng đúng nó"
                    if ok else "LỆCH — đừng tin hai bảng dưới"))
    return ok


# =========================================================================== RISC-V trên FPGA
#
# Phạm vi lấy từ những gì ĐÃ LÀM, ghi trong `docs/riscv-tn20k/` và README §7.3: lõi RV32I tuần
# tự ba cấu hình bộ nhân, chuỗi công cụ Yosys/nextpnr/openFPGALoader, phần mềm C + hợp ngữ +
# linker + Makefile, bốn cách cài đặt nhân ma trận, bộ thu 96 ô qua UART, mô phỏng Verilator,
# và bảng tổng kiểm tính tay ở tầng NGƯỜI.
RISCV = Bang("Lõi RISC-V trên FPGA Tang Nano 20K", [
    ("Đọc tài liệu kit Tang Nano 20K / GW2AR-18, bảng chân, mức điện", "Senior", 1, 2, 4),
    ("Dựng chuỗi công cụ: Yosys + nextpnr + openFPGALoader + riscv32-gcc, "
     "chạy thông tới bitstream", "Senior", 1, 3, 8),
    ("Thiết kế vi kiến trúc lõi RV32I tuần tự: giải mã, khối thanh ghi, bus BRAM",
     "Senior", 2, 4, 8),
    ("Viết RTL lõi RV32I + bộ nhớ + UART phát", "Senior", 3, 6, 12),
    ("Ba cấu hình bộ nhân: không nhân · tuần tự · DSP", "Senior", 1, 3, 6),
    ("Ràng buộc chân `.cst`, mạch reset, cây xung nhịp", "Mid", 0.5, 1, 3),
    ("Bài 1: nạp bitstream, LED chạy trên bo thật", "Mid", 0.5, 1, 3),
    ("Phần mềm nhúng: startup hợp ngữ, linker script, Makefile ba cấu hình", "Mid", 1, 2, 5),
    ("Bốn cách cài đặt nhân ma trận × hai kiểu dữ liệu", "Mid", 1, 3, 6),
    ("Bộ đếm chu kỳ, giao thức bản tin UART, tổng kiểm", "Mid", 1, 2, 4),
    ("Mô phỏng Verilator: testbench, chạy khớp RTL", "Senior", 1, 3, 6),
    ("Bộ thu 96 ô qua cổng nối tiếp bằng Python, gộp bảng", "Mid", 1, 2, 4),
    ("Bảng bốn tổng kiểm tính tay ở tầng NGƯỜI, chốt trước khi đo", "Senior", 0.5, 1, 2),
    ("Chạy đủ 96 ô trên bo, đối chiếu bo ↔ mô phỏng", "QA", 1, 3, 6),
    ("Gỡ lỗi tới khi 96/96 ô đạt", "Senior", 2, 5, 12),
    ("Tài liệu, báo cáo, bảng kết quả", "Mid", 1, 2, 4),
])

# =========================================================================== Game Flappy Bird
#
# Phạm vi lấy từ `docs/game-flappy/` và README §7.4. KHÔNG tính phần BSP của hãng (94 877 dòng
# lấy nguyên, không sửa) — một đội người cũng lấy nguyên nó, nên nó không phải ngày công của ai.
GAME = Bang("Game Flappy Bird + nhân RTOS tự viết trên STM32F469I-DISCO", [
    ("Đọc tài liệu bo (LCD/DSI/SDRAM/cảm ứng/nút), chốt yêu cầu nghiệm thu",
     "Senior", 0.5, 1, 2),
    ("Lập hồ sơ panel: độ phân giải, hệ màu, DPI, bộ đệm khung so với RAM", "Mid", 0.5, 1, 2),
    ("Thiết kế ba màn hình theo toạ độ pixel thật, bảng phần tử sửa được", "Mid", 1, 2, 4),
    ("Thiết kế nhân RTOS: bảng tác vụ, TCB, ngân sách ngăn xếp, cơ chế chuyển ngữ cảnh",
     "Senior", 1, 2, 5),
    ("Viết nhân RTOS: lập lịch, SysTick, PendSV hợp ngữ naked, ngữ cảnh FPU",
     "Senior", 1, 3, 8),
    ("Dựng nền BSP: xung nhịp 180 MHz + Over-Drive, LTDC/DSI, SDRAM, cảm ứng I2C",
     "Senior", 1, 3, 8),
    ("Viết mã vẽ ba màn hình bằng `BSP_LCD_*`", "Mid", 1, 2, 4),
    ("Lớp vẽ từng khung theo dirty-rect: xoá/vẽ chim, cọc, điểm", "Mid", 1, 2, 5),
    ("Máy trạng thái game, vật lý, va chạm, tính điểm", "Mid", 1, 2, 4),
    ("Đường đầu vào: nút PA0 chống rung và cảm ứng FT6206 qua I2C", "Mid", 0.5, 1, 3),
    ("Chỉnh vật lý cho chơi được (trọng lực, xung vỗ cánh, khe cọc)", "Mid", 0.5, 1, 3),
    ("Nạp và gỡ lỗi trên bo tới khi chơi được", "Senior", 1, 3, 8),
    ("Đo nghiệm thu: nhịp nhân, đọc ngược Flash, bảng vector, ngân sách RAM", "QA", 0.5, 1, 3),
    ("Tài liệu và báo cáo", "Mid", 0.5, 1, 3),
])

BANG = {"robot": ROBOT, "riscv": RISCV, "game": GAME}

if __name__ == "__main__":
    if not tu_kiem():
        sys.exit(1)
    chon = sys.argv[1:] or ["riscv", "game"]
    for k in chon:
        BANG[k].in_ra()
