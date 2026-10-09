# -*- coding: utf-8 -*-
"""Hình cho bài 3 (mở rộng năng lực)."""
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_figs import Canvas, render, FILL_A, FILL_B, FILL_C, FILL_D
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, numpy as np
OUT = os.path.dirname(os.path.abspath(__file__))

# Hình 1: khung đo — ba thước năng lực + trục "phần việc nằm trong máy"
def fig1():
    c = Canvas(1000, 1120, base=26)
    c.text(500, 40, "Năng suất (đo được, so với ước lượng người làm tay)", size=26, weight=700, anchor="middle")
    c.box(40, 60, 290, 110, ["giờ của một người", "so với ngày công một đội"], title="Thời gian", size=20, tsize=24, fill=FILL_B, name="tg")
    c.box(355, 60, 290, 110, ["tiền mô hình so với", "lương đội (PERT, COCOMO)"], title="Tiền", size=20, tsize=24, fill=FILL_B, name="tien")
    c.box(670, 60, 290, 110, ["phần việc nằm trong máy", "so với phần chạm vật thật"], title="Điều kiện", size=20, tsize=24, fill=FILL_C, name="dk")
    c.text(500, 210, "Năng lực (ba thước, đếm được từ sổ ghi việc)", size=26, weight=700, anchor="middle")
    c.box(40, 230, 290, 150, ["phép đo, lần đọc ngược,", "điều kiện đối chiếu lại,", "changeset gỡ lại được"], title="1. Làm đủ bước", size=20, tsize=24, fill=FILL_D, name="t1")
    c.box(355, 230, 290, 150, ["công cụ tự viết, tự kiểm;", "việc ngoài vùng từng làm", "đi được tới bo thật"], title="2. Vào vùng mới", size=20, tsize=24, fill=FILL_D, name="t2")
    c.box(670, 230, 290, 150, ["điểm mù khai trước rồi", "nổ đúng chỗ; nhận sai", "trước khi bị truy"], title="3. Tự khai điểm mù", size=20, tsize=24, fill=FILL_D, name="t3")
    c.text(500, 440, "Chiều bắt lỗi (đếm từ nhật ký hai phiên cùng đề bài)", size=26, weight=700, anchor="middle")
    c.box(60, 460, 420, 120, ["phép đo người thiết kế,", "người đọc mã rồi hỏi lại"], title="Lỗi tác tử do người bắt", size=21, tsize=24, fill=FILL_A, name="l1")
    c.box(520, 460, 420, 120, ["tác tử bác kết luận sai,", "tìm lỗ trong phép đo của người"], title="Lỗi người do tác tử bắt", size=21, tsize=24, fill=FILL_A, name="l2")
    c.arrow(480, 515, 520, 515); c.arrow(520, 540, 480, 540)
    # trục phần việc trong máy
    c.text(500, 640, "Mức lợi tỉ lệ với phần việc nằm trong máy tính", size=26, weight=700, anchor="middle")
    c.path("M 80 760 L 920 760", arrow=True)
    c.text(80, 800, "ít (gỡ lỗi trên bo, cần người dựng robot)", size=20, italic=True, color="#444")
    c.text(920, 800, "nhiều (đọc tài liệu, tra thanh ghi, viết mã)", size=20, italic=True, color="#444", anchor="end")
    c.text(500, 840, "phần việc nằm trong máy tính →", size=20, italic=True, color="#444", anchor="middle")
    for x, lab, sub in [(200, "Robot", "giờ chênh ≈ 33–57 lần"), (500, "FPGA", "chưa ước lượng người"), (800, "Nhân RTOS", "giờ chênh ≈ 190 lần")]:
        c.box(x - 110, 680, 220, 56, [lab], size=22, weight=700, fill=FILL_C, r=28, name=lab)
        c.text(x, 758 - 12, "", size=10)
        c.items.append(f'<circle cx="{x}" cy="760" r="9" fill="#333"/>')
        c.text(x, 890, sub, size=19, italic=True, color="#444", anchor="middle")
    c.box(60, 930, 880, 160, ["Tác tử làm đúng theo tiêu chí sai, nhanh và triệt để.", "Ba tiêu chí viết lỏng → 24 ô đo không thể báo sai,", "36 dòng mã không ai gọi, một bản nạp chậm 11 lần mà không ai biết"], title="Điều kiện quyết định: chất lượng đề bài do người viết", size=20, tsize=24, fill=FILL_C, name="db")
    c.check_overlap()
    return c.svg()

# Hình 2: hai phiên robot — chiều bắt lỗi
def fig2():
    plt.rcParams["font.family"] = "Inter"
    fig, ax = plt.subplots(figsize=(3.4, 2.2), dpi=300)
    cats = ["Lỗi tác tử\ndo người bắt", "Lỗi người\ndo tác tử bắt", "Lời gọi công cụ\nbị chặn (%)"]
    l1 = [6, 0, 6.6]; l2 = [1, 3, 3.3]
    x = np.arange(3); w = 0.34
    b1 = ax.bar(x - w/2, l1, w, color="#9aa5b1", label="Phiên 03/10 (trước khi vá, đề bài cũ)")
    b2 = ax.bar(x + w/2, l2, w, color="#1f2d3d", label="Phiên 04/10 (đã vá 7 lỗi, đề bài tường minh)")
    for bars, vals in ((b1, l1), (b2, l2)):
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width()/2, v + 0.12, f"{v:g}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(x); ax.set_xticklabels(cats, fontsize=7)
    ax.set_ylim(0, 11); ax.set_yticks([0, 2, 4, 6, 8]); ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=6, frameon=False, loc="upper left")
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig3_2_robot_hai_phien.png"))

# Hình 3: giờ người (ước lượng) so với giờ tác tử (đo) — thang log
def fig3():
    plt.rcParams["font.family"] = "Inter"
    fig, ax = plt.subplots(figsize=(3.4, 2.2), dpi=300)
    jobs = ["Nhân RTOS\n(lần 1)", "Robot\n(lần 1)", "Robot\n(lần 2)"]
    nguoi = [31.7 * 8, 31.0 * 8, 32.1 * 8]   # ngày công × 8 giờ
    tactu = [81.2 / 60, 7.4, 4.53]
    x = np.arange(3); w = 0.34
    b1 = ax.bar(x - w/2, nguoi, w, color="#9aa5b1", label="Đội người làm tay (ước lượng PERT, giờ công)")
    b2 = ax.bar(x + w/2, tactu, w, color="#1f2d3d", label="Phiên tác tử (đo được, giờ)")
    ax.set_yscale("log"); ax.set_ylim(0.5, 30000)
    for bars, vals in ((b1, nguoi), (b2, tactu)):
        for r, v in zip(bars, vals):
            ax.text(r.get_x() + r.get_width()/2, v * 1.15, f"{v:.0f}" if v >= 10 else f"{v:.1f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks(x); ax.set_xticklabels(jobs, fontsize=7)
    ax.set_ylabel("giờ (thang lôgarit)", fontsize=7); ax.tick_params(axis="y", labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(fontsize=5.8, frameon=False, loc="upper left")
    plt.tight_layout(); plt.savefig(os.path.join(OUT, "fig3_3_gio_nguoi_tac_tu.png"))

async def main():
    await render(fig1(), "fig3_1_khung_do")
    fig2(); fig3(); print("ok")
asyncio.run(main())
