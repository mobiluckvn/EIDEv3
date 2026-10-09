# -*- coding: utf-8 -*-
"""Hình cho bài 4 (quá trình thiết kế và phát triển)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_figs import Canvas, render, FILL_A, FILL_B, FILL_C, FILL_D
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))

# Hình 1: dòng thời gian 05/09 → 04/10 (toàn trang)
def fig1():
    c = Canvas(2100, 800, base=24)
    c.path("M 60 420 L 2040 420", arrow=True, sw=4)
    marks = [
        (140, "05/09", "Hồ sơ thiết kế", ["34 tài liệu, 242 năng lực", "56 ca dùng · rà 40 vùng", "kho mã 1.x bắt đầu"], FILL_B, "top"),
        (370, "11/09", "Firmware thật đầu tiên", ["ELF ARM trong hộp cát", "QEMU chạy ELF AVR", "182 năng lực"], FILL_A, "bot"),
        (620, "14–17/09", "Bản 1.x gần đủ", ["220/242 năng lực", "1 628 ca kiểm Python", "26 màn hình, chưa có bo"], FILL_A, "top"),
        (870, "18/09", "Viết lại giao diện", ["ứng dụng Swift riêng", "32 lỗi im lặng lộ ra", "ở chỗ nối với lõi"], FILL_C, "bot"),
        (1120, "23–24/09", "Đo lần 1, rà soát", ["76 ca: 16/67 đạt", "GAP-35: 95 mục, 5 CÓ", "39/51 lỗi do định tuyến"], FILL_C, "top"),
        (1370, "25/09", "Thiết kế lại, kho mới", ["vòng lặp + ba lớp chặn", "lộ trình G1–G7", "44 mục nhật ký ngày đầu"], FILL_B, "bot"),
        (1620, "29/09", "Đo lần 2", ["cùng 76 ca", "68/68 đạt", "0 ca xấu đi"], FILL_C, "top"),
        (1880, "27/09–04/10", "Việc thật trên bo", ["nhân RTOS, robot, FPGA", "vá DEV-330…337", "40 ca kiểm Swift"], FILL_D, "bot"),
    ]
    for x, d, t, ls, f, side in marks:
        c.items.append(f'<circle cx="{x}" cy="420" r="12" fill="#333"/>')
        c.text(x, 462 if side == "top" else 392, d, size=22, weight=700, anchor="middle")
        y = 100 if side == "top" else 490
        c.box(x - 135, y, 270, 190, ls, title=t, size=18, tsize=20, fill=f, name=t)
        if side == "top": c.arrow(x, 290, x, 406)
        else: c.arrow(x, 490, x, 434)
    c.text(60, 60, "Năm 2026 · kho 1.x: 299 lần ghi mã, 247 mục nhật ký sai khác (05–25/09) · kho v3: 180 lần ghi mã, 102 mục (25/09–04/10)", size=22, italic=True, color="#444")
    c.text(1050, 760, "Nguyên tắc xuyên suốt hai kho: tài liệu là nguồn sự thật; mã khác tài liệu phải ghi vào nhật ký; mọi khẳng định phải có số đo", size=22, weight=700, anchor="middle")
    c.check_overlap()
    return c.svg()

# Hình 2: vòng quy trình (cột)
def fig2():
    c = Canvas(1000, 960, base=26)
    W = 560; X = 60
    steps = [
        ("1. Tài liệu thiết kế", ["nguồn sự thật; mỗi năng lực một hợp đồng"], FILL_B),
        ("2. Tác tử lập trình viết mã", ["theo tài liệu; chủ sản phẩm đọc, duyệt, đo"], FILL_A),
        ("3. Đo bằng bốn mức", ["đơn vị · giao thức · ứng dụng thật · bo thật"], FILL_C),
        ("4. Nhật ký sai lệch", ["mã khác tài liệu ở đâu, vì sao, đề nghị"], FILL_A),
        ("5. Chủ sản phẩm quyết", ["sửa mã hay sửa tài liệu; ghi quyết định"], FILL_D),
    ]
    ys = []; y = 40
    for i, (t, ls, f) in enumerate(steps):
        c.box(X, y, W, 100, ls, title=t, size=21, tsize=25, fill=f, name=t); ys.append(y)
        if i < len(steps) - 1: c.arrow(X + W/2, y + 100, X + W/2, y + 150)
        y += 150
    # vòng về 1
    c.path(f"M {X} {ys[4]+50} L 30 {ys[4]+50} L 30 {ys[0]+50} L {X} {ys[0]+50}")
    c.text(22, (ys[0] + ys[4]) / 2 + 60, "lặp", size=22, italic=True, color="#444")
    # chú thích phải
    c.box(660, ys[1] - 20, 310, 140, ["mỗi lần: một gói giao việc", "(brief, tài liệu .md,", "bộ 76 ca kiểm)"], title="Gói giao việc", size=20, tsize=23, fill=FILL_B, name="goi")
    c.arrow(X + W, ys[1] + 50, 660, ys[1] + 50)
    c.box(660, ys[3] - 20, 310, 140, ["102 mục; 28 mục đề nghị", "sửa tài liệu; 44 mục", "ngay ngày đầu"], title="Nhật ký DEV-2xx", size=20, tsize=23, fill=FILL_C, name="nk")
    c.arrow(X + W, ys[3] + 50, 660, ys[3] + 50)
    c.text(500, 900, "Không ai được im lặng làm khác tài liệu, và không được tự sửa tài liệu.", size=22, italic=True, color="#444", anchor="middle")
    c.check_overlap()
    return c.svg()

# Hình 4: 76 ca theo kịch bản, trước và sau thiết kế lại
def fig4():
    plt.rcParams["font.family"] = "Inter"
    uc = ["UC01", "UC02", "UC03", "UC04", "UC05", "UC06", "UC07", "UC08–10", "UC11", "UC12–15", "UC16–17", "UC18–19"]
    before = [2/7, 0/7, 1/8, 0/6, 5/5, 2/4, 1/2, 0/7, 0/1, 0/8, 1/4, 4/8]
    after = [1]*12
    fig, ax = plt.subplots(figsize=(3.4, 2.3), dpi=300)
    x = np.arange(len(uc)); w = 0.38
    ax.bar(x - w/2, [b*100 for b in before], w, color="#9aa5b1", label="23/09 — định tuyến ý định")
    ax.bar(x + w/2, [a*100 for a in after], w, color="#1f2d3d", label="29/09 — vòng lặp có kiểm soát")
    ax.set_xticks(x); ax.set_xticklabels(uc, fontsize=5.6, rotation=45, ha="right")
    ax.set_ylabel("tỷ lệ ca đạt (%)", fontsize=7); ax.set_ylim(0, 140); ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=6, frameon=False, loc="upper left", ncol=1)
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig4_4_76ca.png"))

async def main():
    await render(fig1(), "fig4_1_dong_thoi_gian")
    await render(fig2(), "fig4_2_vong_quy_trinh")
    fig4(); print("ok")
asyncio.run(main())
