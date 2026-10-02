#!/usr/bin/env python3
"""
tools/gen_data.py
Sinh dữ liệu kiểm thử ma trận A, B và tổng kiểm C làm đáp án (Bài 2).
Hỗ trợ cả môi trường có NumPy (khuyến nghị) và fallback thư viện chuẩn.
"""

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:
    # Tự động nạp site-packages từ venv python-so-lieu của EIDE nếu chạy bằng python3 hệ thống
    eide_py = Path.home() / ".eide" / "cong-cu" / "py"
    if eide_py.exists():
        for sp in eide_py.glob("lib/python*/site-packages"):
            if str(sp) not in sys.path:
                sys.path.insert(0, str(sp))
    try:
        import numpy as np
    except ImportError:
        np = None


def generate_matrix_data(n: int, dtype: str, seed: int = 2026, rng_type: str = "legacy"):
    """
    Sinh hai ma trận A, B kích thước n x n và tính tích C = A x B cùng tổng kiểm.
    - I8:  giá trị trong [-128, 127], C là int32
    - I32: giá trị trong [-1000, 1000], C là int32 (tránh tràn khi dồn N^3 tích)
    """
    if dtype not in ("I8", "I32"):
        raise ValueError(f"Kieu du lieu khong hop le: {dtype}. Chi ho tro I8 hoac I32.")

    if np is not None:
        if rng_type == "pcg64":
            rng = np.random.default_rng(seed)
            if dtype == "I8":
                a = rng.integers(-128, 128, size=(n, n), dtype=np.int8)
                b = rng.integers(-128, 128, size=(n, n), dtype=np.int8)
            else:
                a = rng.integers(-1000, 1001, size=(n, n), dtype=np.int32)
                b = rng.integers(-1000, 1001, size=(n, n), dtype=np.int32)
        else:
            np.random.seed(seed)
            if dtype == "I8":
                a = np.random.randint(-128, 128, size=(n, n), dtype=np.int8)
                b = np.random.randint(-128, 128, size=(n, n), dtype=np.int8)
            else:
                a = np.random.randint(-1000, 1001, size=(n, n), dtype=np.int32)
                b = np.random.randint(-1000, 1001, size=(n, n), dtype=np.int32)

        # Tính tích C = A x B
        c = np.matmul(a.astype(np.int64), b.astype(np.int64))

        # Danh sách lồng nhau chuẩn Python
        mat_a = a.tolist()
        mat_b = b.tolist()
        mat_c = c.tolist()
    else:
        # Fallback dùng module random chuẩn nếu chưa có NumPy
        import random
        random.seed(seed)
        if dtype == "I8":
            mat_a = [[random.randint(-128, 127) for _ in range(n)] for _ in range(n)]
            mat_b = [[random.randint(-128, 127) for _ in range(n)] for _ in range(n)]
        else:
            mat_a = [[random.randint(-1000, 1000) for _ in range(n)] for _ in range(n)]
            mat_b = [[random.randint(-1000, 1000) for _ in range(n)] for _ in range(n)]

        mat_c = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                mat_c[i][j] = sum(mat_a[i][k] * mat_b[k][j] for k in range(n))

    # Tính tổng kiểm có trọng số: Σ C[i][j] * (i * N + j + 1) mod 2^32
    chk = 0
    for i in range(n):
        for j in range(n):
            weight = i * n + j + 1
            term = mat_c[i][j] * weight
            chk = (chk + term) & 0xFFFFFFFF

    return mat_a, mat_b, mat_c, chk


def emit_header(n: int, dtype: str, seed: int, mat_a, mat_b, chk: int, guard: str = None) -> str:
    elem_type = "int8_t" if dtype == "I8" else "int32_t"
    out_type = "int32_t"
    if guard is None:
        guard = f"DATA_{n}_{dtype}_H"

    lines = []
    lines.append(f"/* Tu dong sinh boi tools/gen_data.py */")
    lines.append(f"/* n={n}, dtype={dtype}, seed={seed} */")
    lines.append(f"#ifndef {guard}")
    lines.append(f"#define {guard}")
    lines.append("")
    lines.append("#include <stdint.h>")
    lines.append("")
    lines.append(f"#define MATRIX_N {n}")
    lines.append(f"#define DTYPE_STR \"{dtype}\"")
    lines.append(f"#define CHECKSUM_REF 0x{chk:08X}UL")
    lines.append("")
    lines.append(f"typedef {elem_type} elem_t;")
    lines.append(f"typedef {out_type} acc_t;")
    lines.append("")

    def format_matrix(name: str, mat):
        res = [f"static const {elem_type} {name}[{n}][{n}] = {{"]
        for row in mat:
            row_str = ", ".join(f"{val:4d}" for val in row)
            res.append(f"    {{ {row_str} }},")
        res.append("};")
        return "\n".join(res)

    lines.append(format_matrix("mat_a", mat_a))
    lines.append("")
    lines.append(format_matrix("mat_b", mat_b))
    lines.append("")
    lines.append(f"#endif /* {guard} */")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sinh du lieu ma tran cho Bai 2")
    parser.add_argument("--n", type=int, required=True, help="Kich thuoc ma tran N (4, 8, 16, 32)")
    parser.add_argument("--dtype", choices=["I8", "I32"], required=True, help="Kieu du lieu: I8 hoac I32")
    parser.add_argument("--seed", type=int, default=2026, help="Hat giong ngau nhien (mac dinh: 2026)")
    parser.add_argument("--rng", choices=["legacy", "pcg64"], default="legacy", help="Bo sinh so ngau nhien")
    parser.add_argument("--out", type=str, default=None, help="Duong dan tep .h dau ra")

    args = parser.parse_args()

    mat_a, mat_b, mat_c, chk = generate_matrix_data(args.n, args.dtype, args.seed, args.rng)
    out_path = args.out or f"data_{args.n}_{args.dtype}.h"
    stem = Path(out_path).stem.upper().replace("-", "_").replace(".", "_")
    guard = f"DATA_{stem}_H" if not stem.startswith("DATA_") else f"{stem}_H"
    header_content = emit_header(args.n, args.dtype, args.seed, mat_a, mat_b, chk, guard=guard)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header_content)

    print(f"Da sinh {out_path}: N={args.n}, dtype={args.dtype}, seed={args.seed}, CHECKSUM=0x{chk:08X}")


if __name__ == "__main__":
    main()
