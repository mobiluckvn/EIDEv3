"""Độ nhạy của tb_pcpi_vmini.v. Câu hỏi riêng: đồng hồ canh đã nổ lần nào chưa."""
import pathlib
import sys

sys.path.insert(0, "/Users/congvt/Documents/EIDE_v3/src")
from eide.build import hdl

DU_AN = pathlib.Path("/Users/congvt/Documents/EIDE_v3/du-lieu/riscv-tn20k-b")
RTL = DU_AN / "bai3/rtl/pcpi_vmini.v"

PHA = [
    # Lỗi giao thức — CHỈ đồng hồ canh bắt được. Hai phép này đã sửa lại: bản đầu của tôi
    # chỉ bỏ `reg_wait <= 0`, mà `reg_ready` vẫn lên nên không treo — một phép phá rỗng.
    ("vload kẹt mãi, không báo xong",
     "                            reg_wait  <= 1'b0;\n                            reg_ready <= 1'b1;\n                            step      <= 3'd5;",
     "                            step      <= 3'd4;"),
    ("vdot kẹt mãi, không báo xong",
     "                            step      <= 3'd4;\n                            reg_wait  <= 1'b0;\n                            reg_ready <= 1'b1;",
     "                            step      <= 3'd3;"),
    # Lỗi tính toán.
    ("bỏ dấu một làn", "wire signed [15:0] p0 = m_a0 * m_b0;",
     "wire [15:0] p0 = $unsigned(m_a0) * $unsigned(m_b0);"),
    ("mất một làn: p3 = 0", "wire signed [15:0] p3 = m_a3 * m_b3;",
     "wire signed [15:0] p3 = 16'sd0;"),
    # Lỗi định thời BRAM.
    ("vload nhận dữ liệu sớm 1 chu kỳ",
     "vreg[active_vd][31:0] <= vmem_rdata;", "vreg[active_vd][31:0] <= 32'd0;"),
    # Lỗi giải mã.
    ("bỏ chốt funct7", "(funct7 == 7'b0000000)", "(funct7 == funct7)"),
    # Mặt nạ: phải nhắm vào chốt THẬT SỰ che khi vl=4, không phải chốt `vl > 0` luôn đúng.
    ("bỏ mặt nạ vl (làn che khi vl=4)",
     "m_a0 = (vl > 5'd4)  ? $signed(vreg[active_vs1][ 39: 32]) : 8'sd0;",
     "m_a0 = $signed(vreg[active_vs1][ 39: 32]);"),
]


def chay():
    kq = hdl.mo_phong(goc=DU_AN, nguon=DU_AN / "bai3/sim",
                      dinh="tb_pcpi_vmini", bo_may="iverilog")
    nv = kq.nguyen_van or ""
    return kq.dat, ("FAIL treo" in nv), nv


goc = RTL.read_text()
print("=== mốc: mã nguyên vẹn ===")
ok, treo, nv = chay()
print(f"  dat={ok}  đồng-hồ-canh-nổ={treo}")
if not ok:
    print(nv[-2000:])
    sys.exit("mốc không dùng được")

bat, lot = 0, []
print("\n=== bảy phép phá ===")
try:
    for nhan, cu, moi in PHA:
        if cu not in goc:
            print(f"  {nhan:36} KHÔNG ÁP ĐƯỢC")
            lot.append(nhan + " [không áp được]")
            continue
        RTL.write_text(goc.replace(cu, moi, 1))
        dat, treo, _ = chay()
        ket = "LỌT (vẫn đạt)" if dat else ("BẮT — do đồng hồ canh" if treo else "BẮT")
        print(f"  {nhan:36} {ket}")
        if dat:
            lot.append(nhan)
        else:
            bat += 1
finally:
    RTL.write_text(goc)
    print("\n  (mã đã phục hồi)")

print(f"\n=== độ nhạy: bắt {bat}/{len(PHA)} ===")
for x in lot:
    print(f"  LỌT: {x}")
