#!/usr/bin/env python3
"""
elf2hex.py
Chuyen doi tep nhi phan (.bin) thanh tep .hex cho $readmemh trong Verilog.
Moi dong 1 tu 32-bit little-endian, du 8192 tu (32 KB).
"""

import sys
import struct

def bin2hex(bin_path, hex_path, word_count=8192):
    with open(bin_path, "rb") as f:
        data = f.read()

    rem = len(data) % 4
    if rem != 0:
        data += b"\x00" * (4 - rem)

    total_words = len(data) // 4
    if total_words > word_count:
        print(f"CANH BAO: Du lieu vuot qua dung luong BRAM ({word_count} tu)!", file=sys.stderr)

    with open(hex_path, "w") as f:
        for i in range(word_count):
            if i < total_words:
                val = struct.unpack("<I", data[i*4 : i*4 + 4])[0]
            else:
                val = 0
            f.write(f"{val:08x}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Su dung: python3 elf2hex.py <input.bin> <output.hex> [word_count]")
        sys.exit(1)

    bin_file = sys.argv[1]
    hex_file = sys.argv[2]
    words = int(sys.argv[3]) if len(sys.argv) > 3 else 8192

    bin2hex(bin_file, hex_file, words)
