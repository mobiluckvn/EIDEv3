# -*- coding: utf-8 -*-
"""Vẽ biểu đồ so sánh hiệu năng CPM của Bài 2 từ kết quả results/all.csv.

Biểu đồ trả lời ba câu hỏi chính:
1. Cấu hình CPU đổi được bao nhiêu: H0 (rv32i soft-mul) vs H1 (multicycle) vs H2 (DSP fast-mul).
2. CPM đổi theo kích thước ma trận N thế nào: Trục Y thang log để thấy rõ từ H0 (~600) tới H2 (~37).
3. I8 so với I32: Nét liền (I8) vs Nét đứt (I32) trên cùng một biểu đồ để tiện đối chiếu.

Đang lấy giá trị TỐT NHẤT (min CPM) trong các cách viết (V0–V3) của mỗi tổ hợp.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

# Kiểm tra thư viện matplotlib
try:
    import matplotlib
    matplotlib.use("Agg")  # Chế độ headless, không cần X11
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
except ImportError:
    sys.stderr.write("LỖI: Chưa cài đặt thư viện 'matplotlib'.\n")
    sys.stderr.write("Vui lòng cài đặt trước bằng lệnh: pip install matplotlib\n")
    sys.exit(1)


def main() -> int:
    goc_du_an = Path(__file__).resolve().parent.parent
    csv_path = goc_du_an / "results" / "all.csv"
    out_path = goc_du_an / "results" / "cpm.png"

    # 1. Kiểm tra sự tồn tại của tệp dữ liệu
    if not csv_path.is_file():
        sys.stderr.write(f"LỖI: Không tìm thấy tệp kết quả '{csv_path}'.\n")
        sys.stderr.write("Hãy chạy bộ quét Bài 2 (tools/quet_bai2.py) trước để tạo tệp kết quả.\n")
        return 1

    # 2. Đọc và lọc dữ liệu: tìm cách viết có CPM nhỏ nhất (tốt nhất) cho mỗi (hw, dtype, n)
    best_data: dict[tuple[str, str], dict[int, tuple[float, str]]] = {}
    hw_list = ["H0", "H1", "H2"]
    dtype_list = ["I8", "I32"]
    n_list = [4, 8, 16, 32]

    for hw in hw_list:
        for dt in dtype_list:
            best_data[(hw, dt)] = {}

    total_rows = 0
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total_rows += 1
            if r.get("ok") != "1":
                continue
            n = int(r["n"])
            dt = r["dtype"]
            ver = r["ver"]
            hw = r["hw"]
            cpm = float(r["cpm"])

            key = (hw, dt)
            if key not in best_data:
                continue

            if n not in best_data[key] or cpm < best_data[key][n][0]:
                best_data[key][n] = (cpm, ver)

    # Kiểm tra xem có đủ dữ liệu không
    missing = []
    for hw in hw_list:
        for dt in dtype_list:
            for n in n_list:
                if n not in best_data[(hw, dt)]:
                    missing.append(f"{hw}-{dt}-N{n}")

    if missing:
        sys.stderr.write(f"CẢNH BÁO: Thiếu dữ liệu cho các tổ hợp: {', '.join(missing)}\n")

    # In bảng tóm tắt kết quả tốt nhất ra console
    print("=" * 68)
    print("BẢNG TỔNG HỢP CPM TỐT NHẤT (MIN QUA V0–V3) - BÀI 2")
    print("=" * 68)
    print(f"{'Cấu hình':<10} | {'Kiểu':<6} | {'N=4':<10} | {'N=8':<10} | {'N=16':<10} | {'N=32':<10}")
    print("-" * 68)
    for hw in hw_list:
        for dt in dtype_list:
            vals = []
            for n in n_list:
                if n in best_data[(hw, dt)]:
                    cpm_val, ver_val = best_data[(hw, dt)][n]
                    vals.append(f"{cpm_val:.1f} ({ver_val})")
                else:
                    vals.append("N/A")
            print(f"{hw:<10} | {dt:<6} | {vals[0]:<10} | {vals[1]:<10} | {vals[2]:<10} | {vals[3]:<10}")
    print("=" * 68)

    # 3. Vẽ biểu đồ
    fig, ax = plt.subplots(figsize=(10, 6.8), dpi=300)

    # Quy ước kiểu vẽ:
    # HW: màu sắc
    colors = {
        "H0": "#C0392B",  # Đỏ gạch (Soft-mul)
        "H1": "#2980B9",  # Xanh dương (Multicycle)
        "H2": "#27AE60",  # Xanh lá (DSP Fast-mul)
    }
    hw_labels = {
        "H0": "H0: rv32i (Soft-mul)",
        "H1": "H1: rv32im (Multicycle)",
        "H2": "H2: rv32im (DSP Fast-mul)",
    }

    # Dtype: nét vẽ và điểm đánh dấu (marker)
    styles = {
        "I8": {"linestyle": "-", "marker": "o", "label_suffix": "I8 (int8_t)"},
        "I32": {"linestyle": "--", "marker": "s", "label_suffix": "I32 (int32_t)"},
    }

    for hw in hw_list:
        for dt in dtype_list:
            x_vals = []
            y_vals = []
            for n in n_list:
                if n in best_data[(hw, dt)]:
                    x_vals.append(n)
                    y_vals.append(best_data[(hw, dt)][n][0])

            if not x_vals:
                continue

            lbl = f"{hw_labels[hw]} | {styles[dt]['label_suffix']}"
            ax.plot(
                x_vals,
                y_vals,
                label=lbl,
                color=colors[hw],
                linestyle=styles[dt]["linestyle"],
                marker=styles[dt]["marker"],
                markersize=7,
                linewidth=2.0,
                alpha=0.92,
            )

            # Đính nhãn số CPM tại từng điểm
            for x, y in zip(x_vals, y_vals):
                # Đặt vị trí nhãn so le để tránh đè chữ giữa I8 và I32
                va = "bottom" if dt == "I8" else "top"
                offset = 4 if dt == "I8" else -5
                ax.annotate(
                    f"{y:.1f}",
                    (x, y),
                    textcoords="offset points",
                    xytext=(0, offset),
                    ha="center",
                    va=va,
                    fontsize=8.5,
                    fontweight="bold" if hw == "H2" else "normal",
                    color=colors[hw],
                )

    # Thiết lập trục toạ độ
    ax.set_xscale("log", base=2)
    ax.set_xticks(n_list)
    ax.get_xaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_xlim(3.3, 38.0)

    ax.set_yscale("log")
    ax.set_ylim(25, 1200)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f"))

    # Lưới (grid)
    ax.grid(True, which="major", color="#BDC3C7", linestyle="--", linewidth=0.8, alpha=0.8)
    ax.grid(True, which="minor", color="#ECF0F1", linestyle=":", linewidth=0.5, alpha=0.6)

    # Nhãn và tiêu đề
    ax.set_xlabel("Kích thước ma trận N (Ma trận N × N)", fontsize=11, fontweight="bold", labelpad=8)
    ax.set_ylabel("Số chu kỳ / phép nhân-cộng (CPM) [Thang Log]", fontsize=11, fontweight="bold", labelpad=8)

    plt.title(
        "Hiệu năng nhân ma trận trên PicoRV32 theo cấu hình CPU và kiểu dữ liệu",
        fontsize=13,
        fontweight="bold",
        pad=14,
    )

    # Dòng ghi chú phương pháp lấy số
    ax.text(
        0.5,
        1.015,
        "Đường cơ sở tốt nhất (min CPM giữa các phiên bản V0–V3) | Nét liền: I8, Nét đứt: I32",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=9.5,
        fontstyle="italic",
        color="#555555",
    )

    # Khung chú giải (Legend)
    ax.legend(
        loc="upper right",
        frameon=True,
        framealpha=0.92,
        edgecolor="#CCCCCC",
        fontsize=9,
        labelspacing=0.5,
    )

    # Khung tóm tắt 3 kết luận chính ở góc dưới trái
    nhan_xet = (
        "Ba phát hiện chính (Bài 2):\n"
        "• CPU: H2 (~37 cpm) nhanh gấp ~2× H1 (~71 cpm) và ~16–18× H0 (~600 cpm)\n"
        "• Kích thước: CPM giảm dần khi N tăng (4 → 32) do khấu hao chi phí vòng lặp\n"
        "• Kiểu dữ liệu: I8 và I32 trên H1/H2 chênh lệch rất nhỏ (~1%) vì ALU 32-bit"
    )
    ax.text(
        0.03,
        0.04,
        nhan_xet,
        transform=ax.transAxes,
        fontsize=8.5,
        verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#F8F9F9", edgecolor="#BDC3C7", alpha=0.9),
    )

    # Lưu biểu đồ
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()

    print(f"\n[OK] Đã vẽ biểu đồ thành công: {out_path}")
    print("     Biểu đồ thể hiện thang log trục Y, phân biệt H0/H1/H2 và I8/I32.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
