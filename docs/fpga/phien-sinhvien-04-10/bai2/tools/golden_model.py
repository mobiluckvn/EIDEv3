#!/usr/bin/env python3
"""
golden_model.py
Mo hinh chuan Python tinh phep nhan ma tran va tong kiem (checksum) 32-bit.
Chuc nang:
1. Tinh toan doc lap ket qua ma tran C = A x B cho N in {4, 8, 16, 32}, dtype in {I32, I8}.
2. Sinh tep header C (golden_checksums.h) chua bang tra de firmware tu danh gia ok=1 / ok=0.
3. Doc log UART tu mo phong hoac kit that, doi chieu checksum va bao cao sai lech.
"""

import sys
import re

N_LIST = [4, 8, 16, 32]
DTYPES = ["I32", "I8"]

def init_matrices(n, dtype="I32"):
    a = [0] * (n * n)
    b = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            a[i * n + j] = ((i + j) % 7) + 1
            b[i * n + j] = ((i * 3 + j) % 11) - 5
    return a, b

def matmul(n, a, b):
    c = [0] * (n * n)
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += a[i * n + k] * b[k * n + j]
            c[i * n + j] = s
    return c

def calc_checksum(n, c):
    chk = 0
    for i in range(n * n):
        val_u32 = c[i] & 0xFFFFFFFF
        chk = ((chk * 31) + val_u32) & 0xFFFFFFFF
    return chk

def get_golden_table():
    table = {}
    for n in N_LIST:
        table[n] = {}
        for dtype in DTYPES:
            a, b = init_matrices(n, dtype)
            c = matmul(n, a, b)
            chk = calc_checksum(n, c)
            table[n][dtype] = chk
    return table

def generate_header(header_path):
    table = get_golden_table()
    with open(header_path, "w") as f:
        f.write("/* golden_checksums.h - Sinh tu dong boi golden_model.py */\n")
        f.write("#ifndef GOLDEN_CHECKSUMS_H\n")
        f.write("#define GOLDEN_CHECKSUMS_H\n\n")
        f.write("#include <stdint.h>\n\n")
        f.write("static inline uint32_t get_golden_checksum(int n, int dtype) {\n")
        f.write("    (void)dtype;\n")
        f.write("    switch (n) {\n")
        for n in N_LIST:
            chk = table[n]["I32"]
            f.write(f"        case {n}: return 0x{chk:08x}U;\n")
        f.write("        default: return 0U;\n")
        f.write("    }\n")
        f.write("}\n\n")
        f.write("#endif /* GOLDEN_CHECKSUMS_H */\n")
    print(f"[GOLDEN] Da sinh tep header: {header_path}")

def verify_log(log_path):
    table = get_golden_table()
    pattern = re.compile(
        r"RESULT,n=(\d+),dtype=([A-Z0-9]+),ver=(V\d),hw=([A-Z0-9]+),cycles=(\d+),macs=(\d+),cpm=(\d+),chk=(0x[0-9a-fA-F]+),ok=(\d)"
    )

    total_cells = 0
    passed_cells = 0
    mismatches = 0

    print(f"\n=== DOI CHIEU KET QUA TU LOG: {log_path} ===")
    with open(log_path, "r", errors="ignore") as f:
        for line in f:
            m = pattern.search(line)
            if not m:
                continue
            n = int(m.group(1))
            dtype = m.group(2)
            ver = m.group(3)
            hw = m.group(4)
            cycles = int(m.group(5))
            chk_hex = m.group(8).lower()
            chk_val = int(chk_hex, 16)
            reported_ok = int(m.group(9))

            total_cells += 1
            expected_chk = table.get(n, {}).get(dtype, None)

            if expected_chk is None:
                print(f"[CANH BAO] Khong tim thay golden checksum cho N={n}, dtype={dtype}")
                continue

            match = (chk_val == expected_chk)
            if match and reported_ok == 1:
                passed_cells += 1
                status = "PASS"
            else:
                mismatches += 1
                status = f"FAIL (Mong doi: 0x{expected_chk:08x}, Nhan: {chk_hex})"

            print(f"Cell {total_cells:2d}: N={n:2d} {dtype:3s} {ver} HW={hw} Cycles={cycles:8d} Chk={chk_hex} -> {status}")

    print("\n--------------------------------------------------")
    print(f"Tong so o da kiem tra : {total_cells}")
    print(f"So o khop mo hinh     : {passed_cells}")
    print(f"So o sai lech         : {mismatches}")
    if total_cells == 32 and mismatches == 0:
        print("KET LUAN: TAT CA 32 O CHUAN XAC TUYET DOI!")
    elif total_cells > 0 and mismatches == 0:
        print(f"KET LUAN: {total_cells} o deu hop le, chua du 32 o.")
    else:
        print("KET LUAN: CO SAI LECH VOI MO HINH CHUAN!")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--gen-header":
        generate_header(sys.argv[2])
    elif len(sys.argv) > 2 and sys.argv[1] == "--verify":
        verify_log(sys.argv[2])
    else:
        table = get_golden_table()
        print("=== BANG TONG KIEM CHUAN PYTHON (GOLDEN CHECKSUM) ===")
        for n in N_LIST:
            for dtype in DTYPES:
                chk = table[n][dtype]
                macs = n * n * n
                print(f"N={n:2d}, dtype={dtype:3s}, MACs={macs:5d}, Checksum=0x{chk:08x}")
