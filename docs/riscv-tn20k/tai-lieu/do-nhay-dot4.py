"""Đo độ nhạy bộ kiểm tb_pcpi_dot4.v: phá mã thật, xem bộ kiểm có thấy không."""
import pathlib
import sys

sys.path.insert(0, "/Users/congvt/Documents/EIDE_v3/src")
from eide.build import hdl

DU_AN = pathlib.Path("/Users/congvt/Documents/EIDE_v3/du-lieu/riscv-tn20k-b")
RTL = DU_AN / "bai3/rtl/pcpi_dot4.v"

PHA = [
    ("bỏ dấu toán hạng A", "wire signed [7:0] a0 = pcpi_rs1[7:0];", "wire [7:0] a0 = pcpi_rs1[7:0];"),
    ("bỏ mở rộng dấu ở cây cộng", "{{16{prod0[15]}}, prod0}", "{16'b0, prod0}"),
    ("lệch làn: a0 nhân b1", "wire signed [15:0] prod0 = a0 * b0;", "wire signed [15:0] prod0 = a0 * b1;"),
    ("không cộng dồn, chỉ gán", "acc <= acc + dot4_sum;", "acc <= dot4_sum;"),
    ("bỏ chốt funct7", "(funct7 == 7'b0000000)", "(funct7 == funct7)"),
    ("sai funct3 của dot4", "(funct3 == 3'b011)", "(funct3 == 3'b100)"),
    ("mất một làn: prod3 thành 0", "wire signed [15:0] prod3 = a3 * b3;", "wire signed [15:0] prod3 = 16'sd0;"),
]


def chay():
    kq = hdl.mo_phong(
        goc=DU_AN,
        nguon=DU_AN / "bai3/sim",
        dinh="tb_pcpi_dot4",
        bo_may="iverilog",
    )
    return kq.dat, f"{kq.pass_fail} · {kq.vi_sao_khong_dat}\n{kq.nguyen_van}"


goc_txt = RTL.read_text()
print("=== mốc: mã nguyên vẹn ===")
ok, ra = chay()
print(f"  dat={ok}")
if not ok:
    print(ra[-3000:])
    sys.exit("Mã nguyên vẹn mà bộ kiểm không đạt — mốc không dùng được.")

print("\n=== bảy phép phá ===")
bat, lot = 0, []
try:
    for nhan, cu, moi in PHA:
        if cu not in goc_txt:
            print(f"  {nhan:32} KHÔNG ÁP ĐƯỢC")
            lot.append(nhan + " [không áp được]")
            continue
        RTL.write_text(goc_txt.replace(cu, moi, 1))
        van_dat, _ = chay()
        print(f"  {nhan:32} {'LỌT (vẫn đạt)' if van_dat else 'BẮT'}")
        if van_dat:
            lot.append(nhan)
        else:
            bat += 1
finally:
    RTL.write_text(goc_txt)
    print("\n  (mã đã phục hồi nguyên vẹn)")

print(f"\n=== độ nhạy: bắt {bat}/{len(PHA)} ===")
for x in lot:
    print(f"  LỌT: {x}")
