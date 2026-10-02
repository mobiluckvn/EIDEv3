#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/parse_log.py — Chuyển bản ghi UART từ bo thật thành CSV kết quả.

Dùng để phân tích kết quả đo chu kỳ ma trận từ UART thật của kit TN20K:
- Nhận một hoặc nhiều tệp bản ghi (.log / .txt).
- Nhãn `hw` bắt buộc lấy từ dòng `CONFIG,hw=...`, không lấy từ dòng `RESULT`.
- Không im lặng bỏ qua rác UART: đếm và báo cáo chi tiết số dòng đọc được,
  số dòng bỏ qua và phân loại lý do.
- Dòng `ok=0` (tính sai) vẫn giữ nguyên và ghi vào CSV để theo dõi.
- Xuất CSV cùng lược đồ với results/all.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

# Biểu thức chính quy cho dòng CONFIG và dòng RESULT
_RE_CONFIG = re.compile(r"^CONFIG,hw=(?P<hw>[A-Za-z0-9_]+)\s*$")
_RE_RESULT = re.compile(
    r"^RESULT,n=(?P<n>\d+),dtype=(?P<dtype>[A-Za-z0-9_]+),ver=(?P<ver>[A-Za-z0-9_]+),"
    r"hw=(?P<hw>[^,]+),cycles=(?P<cycles>\d+),macs=(?P<macs>\d+),cpm=(?P<cpm>[\d.]+),"
    r"chk=(?P<chk>0x[0-9A-Fa-f]+),ok=(?P<ok>[01])\s*$"
)

# Các cột theo đúng lược đồ results/all.csv
CSV_FIELDNAMES = [
    "n",
    "dtype",
    "ver",
    "hw",
    "cycles",
    "macs",
    "cpm",
    "chk",
    "ok",
    "flash",
]


def parse_single_log(file_path: Path) -> tuple[list[dict], int, Counter]:
    """Đọc và bóc tách một tệp log UART.

    Trả về:
        (danh_sach_ket_qua, tong_so_dong, bo_dem_ly_do_bo_qua)
    """
    results: list[dict] = []
    reasons = Counter()
    total_lines = 0
    current_hw: str | None = None

    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as exc:
        sys.stderr.write(f"Lỗi: Không thể đọc tệp {file_path}: {exc}\n")
        reasons["loi_doc_tep"] += 1
        return results, 0, reasons

    total_lines = len(lines)

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Dòng trống
        if not line:
            reasons["dong_trong"] += 1
            continue

        # Kiểm tra dòng CONFIG
        m_cfg = _RE_CONFIG.match(line)
        if m_cfg:
            current_hw = m_cfg.group("hw")
            reasons["dong_config"] += 1
            continue

        # Kiểm tra dòng RESULT
        if line.startswith("RESULT,"):
            m_res = _RE_RESULT.match(line)
            if not m_res:
                reasons["result_sai_dinh_dang"] += 1
                sys.stderr.write(
                    f"  [{file_path.name}:{line_idx}] CẢNH BÁO: Dòng RESULT hỏng cú pháp: {line!r}\n"
                )
                continue

            d = m_res.groupdict()

            # Quy tắc 1: hw lấy từ dòng CONFIG, không lấy từ dòng RESULT
            if not current_hw:
                reasons["result_thieu_config"] += 1
                sys.stderr.write(
                    f"  [{file_path.name}:{line_idx}] LỖI: Dòng RESULT thiếu dòng CONFIG đi trước. "
                    f"Phần mềm in hw={d['hw']!r}, không được dùng. Dòng bị bỏ qua.\n"
                )
                continue

            # Ghi đè nhãn hw từ cấu hình phần cứng đã phát hiện
            d["hw"] = current_hw
            # Mặc định cột flash rỗng nếu UART không in thông tin bộ nhớ
            d.setdefault("flash", "")
            results.append(d)
            continue

        # Các dòng thông tin hệ thống chuẩn
        if line.startswith("===") or line in ("DONE", "PASS", "FAIL"):
            reasons["dong_thong_tin_he_thong"] += 1
            continue

        # Còn lại là rác UART hoặc ký tự không đồng bộ
        reasons["dong_rac_uart"] += 1

    return results, total_lines, reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Chuyển log UART đo chu kỳ ma trận thành file CSV theo đúng lược đồ."
    )
    parser.add_argument(
        "logs",
        nargs="*",
        help="Đường dẫn một hoặc nhiều tệp bản ghi UART (.log, .txt)",
    )
    parser.add_argument(
        "--out",
        "-o",
        default="results/board.csv",
        help="Đường dẫn tệp CSV kết quả xuất ra (mặc định: results/board.csv)",
    )

    args = parser.parse_args(argv)

    if not args.logs:
        parser.print_usage(sys.stderr)
        sys.stderr.write("Lỗi: Thiếu tệp bản ghi đầu vào. Hãy truyền ít nhất một tệp log.\n")
        return 2

    log_files: list[Path] = []
    missing_files: list[str] = []
    for p_str in args.logs:
        p = Path(p_str)
        if not p.is_file():
            missing_files.append(p_str)
        else:
            log_files.append(p)

    if missing_files:
        sys.stderr.write(
            f"Lỗi: Không tìm thấy các tệp bản ghi sau:\n  "
            + "\n  ".join(missing_files)
            + "\n"
        )
        return 1

    all_results: list[dict] = []
    grand_total_lines = 0
    total_reasons = Counter()

    print(f"Bắt đầu xử lý {len(log_files)} tệp bản ghi:")

    for file_path in log_files:
        res, count, reasons = parse_single_log(file_path)
        all_results.extend(res)
        grand_total_lines += count
        total_reasons.update(reasons)

        ignored_count = count - len(res)
        print(
            f"  - {file_path.name}: đọc {count} dòng -> {len(res)} kết quả hợp lệ, "
            f"{ignored_count} dòng bỏ qua."
        )

    # In báo cáo chi tiết các dòng bỏ qua (Quy tắc 2: không im lặng bỏ qua)
    total_ignored = grand_total_lines - len(all_results)
    print("\nThống kê dòng:")
    print(f"  Tổng số dòng đọc được : {grand_total_lines}")
    print(f"  Dòng kết quả hợp lệ   : {len(all_results)}")
    print(f"  Tổng số dòng bỏ qua   : {total_ignored}")

    if total_reasons:
        print("  Chi tiết các dòng không thành kết quả CSV:")
        label_map = {
            "dong_trong": "Dòng trống",
            "dong_config": "Dòng thiết lập phần cứng (CONFIG,hw=...)",
            "dong_thong_tin_he_thong": "Dòng tiêu đề / trạng thái (===, DONE...)",
            "dong_rac_uart": "Ký tự rác / dòng ngoài định dạng UART",
            "result_sai_dinh_dang": "Dòng RESULT hỏng cú pháp",
            "result_thieu_config": "Dòng RESULT thiếu nhãn CONFIG phía trước",
            "loi_doc_tep": "Lỗi đọc tệp",
        }
        for k, v in total_reasons.items():
            desc = label_map.get(k, k)
            print(f"    * {desc:<45}: {v} dòng")

    # Kiểm tra số kết quả ok=0 (Quy tắc 3: giữ nguyên ok=0)
    failed_results = [r for r in all_results if r.get("ok") != "1"]
    if failed_results:
        print(f"\nChú ý: Có {len(failed_results)} phép đo báo sai kết quả (ok=0). Đã giữ nguyên trong CSV.")

    # Ghi ra tệp CSV kết quả
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with out_path.open("w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=CSV_FIELDNAMES)
            writer.writeheader()
            for r in all_results:
                writer.writerow(r)
        print(f"\nĐã ghi thành công {len(all_results)} dòng vào {out_path}.")
    except Exception as exc:
        sys.stderr.write(f"Lỗi: Không thể ghi tệp đầu ra {out_path}: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
