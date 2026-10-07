# -*- coding: utf-8 -*-
"""Luồng công cụ HDL: Verilog → mạng cổng → bố trí → bitstream.

Bộ kiểm này canh ba thứ, và cả ba đều là chỗ một lỗi im lặng đi được tới tận bo mạch:

1. **Không chặng nào được "đạt" khi không có tệp ra, hoặc tệp ra rỗng.** Mỗi chặng ăn đầu ra
   của chặng trước, nên một chặng báo xong sai sẽ kéo cả dây — và lỗi chỉ hiện ở FPGA.
2. **Con số tài nguyên và Fmax phải đọc đúng từ nguyên văn công cụ.** Chúng là thứ ta đi đo để
   biết thiết kế có vừa chip và có chạy nổi tần số không; đọc sai thì so với hạn mức thật ra
   kết luận sai.
3. **Fmax thấp hơn tần số định chạy thì KHÔNG đạt.** Bitstream từ một thiết kế không đạt định
   thời vẫn nạp được và vẫn chạy sai — sai kiểu lúc được lúc không, khó tìm nhất.

Ca nào cần chương trình thật thì tự bỏ qua khi máy chưa có nó, chứ không giả lập: một bộ kiểm
giả lập `yosys` chỉ kiểm chính bản giả lập.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import pytest

from eide.build import hdl as H

CO_YOSYS = bool(H._tim_lenh("yosys"))
CO_PNR = bool(H._tim_lenh("nextpnr-himbaechel"))
CO_PACK = bool(H._tim_lenh("gowin_pack"))
CO_IV = bool(H._tim_lenh("iverilog")) and bool(H._tim_lenh("vvp"))
CO_VL = bool(H._tim_lenh("verilator"))

can_yosys = pytest.mark.skipif(not CO_YOSYS, reason="máy chưa có yosys")
can_pnr = pytest.mark.skipif(not CO_PNR, reason="máy chưa có nextpnr-himbaechel")
can_pack = pytest.mark.skipif(not CO_PACK, reason="máy chưa có gowin_pack")
can_iv = pytest.mark.skipif(not CO_IV, reason="máy chưa có iverilog")
can_vl = pytest.mark.skipif(not CO_VL, reason="máy chưa có verilator")

BLINKY = """\
module blinky #(parameter CLK_HZ = 27_000_000) (
    input  wire clk,
    output reg  [5:0] led
);
    reg [24:0] dem = 0;
    always @(posedge clk) begin
        if (dem == CLK_HZ/2 - 1) begin
            dem <= 0;
            led <= ~led;
        end else begin
            dem <= dem + 1'b1;
        end
    end
endmodule
"""

CST = """\
IO_LOC "clk" 4;
IO_PORT "clk" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "led[0]" 15;
IO_LOC "led[1]" 16;
IO_LOC "led[2]" 17;
IO_LOC "led[3]" 18;
IO_LOC "led[4]" 19;
IO_LOC "led[5]" 20;
"""

TB_PASS = """\
module tb;
    reg clk = 0;
    always #1 clk = ~clk;
    integer i;
    initial begin
        for (i = 0; i < 10; i = i + 1) @(posedge clk);
        $display("PASS");
        $finish;
    end
endmodule
"""

TB_FAIL = TB_PASS.replace('$display("PASS")', '$display("FAIL: ca 3 sai")')
TB_IM_LANG = TB_PASS.replace('$display("PASS");\n        ', "")


def _du_an(tmp_path: Path, **tep: str) -> Path:
    (tmp_path / "rtl").mkdir()
    (tmp_path / "constraints").mkdir()
    (tmp_path / "rtl" / "blinky.v").write_text(BLINKY, "utf-8")
    (tmp_path / "constraints" / "tangnano20k.cst").write_text(CST, "utf-8")
    for ten, noi in tep.items():
        (tmp_path / "rtl" / ten).write_text(noi, "utf-8")
    return tmp_path


# =============================================================== đọc đầu ra công cụ

def test_doc_tai_nguyen_so_dung_truoc_ten():
    """Yosys in `   25   LUT1` — số TRƯỚC tên. Đọc ngược thì bảng rỗng, và bảng rỗng im lặng."""
    ra = H.doc_tai_nguyen_yosys("""
2.50. Printing statistics.

=== design hierarchy ===

        +----------Count including submodules.
        |
      109 wires
       60 cells
        1   GND
       25   LUT1
        4   LUT4
       10   MUX2_LUT5
        6   OBUF
       25   ALU
        6   DFFE
       25   DFFR
""")
    assert ra["lut"] == 25 + 4 + 10 + 25, "LUT* và MUX2_LUT* và ALU đều ăn LUT"
    assert ra["ff"] == 6 + 25
    assert ra["io"] == 6
    assert ra["chi_tiet"]["LUT1"] == 25


def test_doc_tai_nguyen_khong_nhan_dong_thong_ke_chung():
    """`109 wires` có MỘT khoảng trắng — là thống kê chung, không phải loại ô."""
    ra = H.doc_tai_nguyen_yosys("=== design hierarchy ===\n      109 wires\n       60 cells\n")
    assert "wires" not in ra.get("chi_tiet", {})
    assert "cells" not in ra.get("chi_tiet", {})


def test_doc_tai_nguyen_lay_khoi_tinh_ca_mo_dun_con():
    """Khối 'Local Count' chỉ đếm mô-đun đỉnh; một SoC có CPU bên trong sẽ bị đếm thiếu."""
    ra = H.doc_tai_nguyen_yosys("""
Printing statistics.
        +----------Local Count, excluding submodules.
       10   LUT4
=== design hierarchy ===
        +----------Count including submodules.
     5000   LUT4
""")
    assert ra["lut"] == 5000, "phải lấy khối tính cả mô-đun con"


def test_doc_fmax_lay_dong_ho_CHAM_nhat():
    """Hai miền đồng hồ, một nhanh một chậm — lấy cái nhanh thì che mất cái không đạt."""
    fmax, dung, dh = H.doc_ket_qua_pnr(
        "Info: Max frequency for clock 'clk_a': 287.36 MHz (PASS at 27.00 MHz)\n"
        "Info: Max frequency for clock 'clk_b': 19.50 MHz (FAIL at 27.00 MHz)\n")
    assert fmax == 19.50, "phải lấy đồng hồ chậm nhất"
    assert len(dh) == 2 and dh[1]["ket"] == "FAIL"


def test_doc_muc_dung_tai_nguyen():
    fmax, dung, _ = H.doc_ket_qua_pnr("Info:            LUT4:    59/ 20736     0%\n")
    assert dung["LUT4"]["dung"] == 59 and dung["LUT4"]["tong"] == 20736
    # `ty_le` làm tròn 4 chữ số — đủ cho người đọc, và tránh một số thập phân dài vô ích.
    assert dung["LUT4"]["ty_le"] == pytest.approx(59 / 20736, abs=1e-4)


def test_doc_thong_diep_giu_ca_loi_khong_co_toa_do():
    """Lỗi Yosys phần lớn không có số dòng. Bỏ chúng thì người đọc nhận 'không có lỗi nào'."""
    loi, canh = H.doc_thong_diep(
        "%Error: rtl/a.v:12:5: syntax error\n"
        "ERROR: Module `\\\\foo' not found!\n"
        "Warning: Wire a.b is used but has no driver.\n")
    assert len(loi) == 2 and len(canh) == 1
    assert loi[0]["dong"] == 12 and loi[1]["dong"] == 0


# =============================================================== chạy thật

@can_yosys
def test_tong_hop_ra_tep_va_doc_duoc_so(tmp_path):
    goc = _du_an(tmp_path)
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert kq.dat, kq.vi_sao_khong_dat
    assert kq.so_byte_ra > 0, "tệp rỗng thì không được coi là xong"
    assert kq.tai_nguyen.get("lut", 0) > 0, "số LUT phải đọc được, không được rỗng"
    assert kq.tai_nguyen.get("ff", 0) > 0


@can_yosys
def test_tong_hop_loi_cu_phap_thi_KHONG_dat(tmp_path):
    # Tên phải có đuôi `.v`, nếu không `_nguon_hdl` không nạp và ca này thành vô nghĩa —
    # đã trúng một lần: bản đầu đặt tên "hong" không đuôi, Yosys không thấy, ca báo xanh.
    goc = _du_an(tmp_path, **{"hong.v": "module hong(; endmodule\n"})
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert not kq.dat
    assert kq.loi, "lỗi cú pháp phải hiện ra, không được im lặng"


@can_yosys
@can_pnr
def test_pnr_bao_fmax_va_muc_dung_that(tmp_path):
    goc = _du_an(tmp_path)
    assert H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky").dat
    kq = H.dat_di_day(goc=goc, json_mang=goc / ".eide/hdl/blinky.json",
                      cst=goc / "constraints/tangnano20k.cst", tan_so_mhz=27.0)
    assert kq.dat, kq.vi_sao_khong_dat
    assert kq.fmax_mhz and kq.fmax_mhz > 27.0
    dung = kq.tai_nguyen.get("dung") or {}
    assert any(v["tong"] == 20736 for v in dung.values()), (
        "tổng LUT4 của GW2A-18C là 20 736 — con số này đối chiếu được với bảng thông số")


@can_yosys
@can_pnr
def test_fmax_thap_hon_tan_so_chay_thi_KHONG_dat(tmp_path):
    """Ca quan trọng nhất của tệp này.

    Đặt tần số đòi hỏi cao vô lý để ép không đạt định thời. Nếu chặng này vẫn báo đạt thì
    bitstream dựng ra sẽ nạp được và chạy sai theo kiểu lúc được lúc không.
    """
    goc = _du_an(tmp_path)
    assert H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky").dat
    kq = H.dat_di_day(goc=goc, json_mang=goc / ".eide/hdl/blinky.json",
                      cst=goc / "constraints/tangnano20k.cst", tan_so_mhz=5000.0)
    assert not kq.dat, "không đạt định thời mà báo đạt thì phép đo này vô dụng"
    assert "định thời" in kq.vi_sao_khong_dat


@can_yosys
@can_pnr
def test_thieu_tep_rang_buoc_chan_thi_KHONG_chay(tmp_path):
    """Thiếu `.cst` thì nextpnr tự chọn chân — bitstream nối tín hiệu vào chân không ai định."""
    goc = _du_an(tmp_path)
    assert H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky").dat
    kq = H.dat_di_day(goc=goc, json_mang=goc / ".eide/hdl/blinky.json",
                      cst=goc / "constraints/khong-he-co.cst")
    assert not kq.dat and "ràng buộc chân" in kq.vi_sao_khong_dat


@can_yosys
@can_pnr
@can_pack
def test_bitstream_doc_ten_chip_tu_tep_bo_tri(tmp_path):
    """Bảng ghi `GW2AR-18C`, nextpnr ghi `GW2A-18C`. Đọc từ tệp làm chuyện lệch không xảy ra."""
    goc = _du_an(tmp_path)
    assert H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky").dat
    assert H.dat_di_day(goc=goc, json_mang=goc / ".eide/hdl/blinky.json",
                        cst=goc / "constraints/tangnano20k.cst").dat
    kq = H.dong_goi(goc=goc, pnr_json=goc / ".eide/hdl/blinky_pnr.json")
    assert kq.dat, kq.vi_sao_khong_dat
    assert kq.tai_nguyen["chip_doc_tu_tep_bo_tri"] == "GW2A-18C"
    assert kq.so_byte_ra > 1000, "tệp .fs của GW2A-18C phải lớn, rỗng là hỏng"
    assert (goc / kq.tep_ra).suffix == ".fs"


def test_doc_chip_tu_pnr_tra_rong_khi_khong_doc_duoc(tmp_path):
    """Không đọc được thì trả rỗng để bên gọi lùi về bảng — KHÔNG được đoán một tên chip."""
    xau = tmp_path / "hong.json"
    xau.write_text("{khong phai json", "utf-8")
    assert H._doc_chip_tu_pnr(xau) == ""
    assert H._doc_chip_tu_pnr(tmp_path / "khong-he-co.json") == ""


# =============================================================== mô phỏng

@can_iv
def test_sim_doc_PASS_tu_testbench(tmp_path):
    goc = _du_an(tmp_path, tb="")
    (goc / "rtl" / "tb.v").write_text(TB_PASS, "utf-8")
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert kq.dat and kq.pass_fail == "PASS", kq.vi_sao_khong_dat


@can_iv
def test_sim_in_FAIL_thi_KHONG_dat(tmp_path):
    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(TB_FAIL, "utf-8")
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat and kq.pass_fail == "FAIL"


@can_iv
def test_sim_khong_in_gi_thi_KHONG_dat(tmp_path):
    """Chạy xong mà không in gì thì không có phép đo nào ở đây — và phải nói ra là lỗi testbench."""
    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(TB_IM_LANG, "utf-8")
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat and kq.pass_fail == ""
    assert "testbench" in kq.vi_sao_khong_dat.lower()


# =============================================================== thiếu công cụ

def test_thieu_cong_cu_thi_noi_ro_cach_cai(monkeypatch, tmp_path):
    """Thiếu chương trình thì từ chối có chỉ dẫn, KHÔNG giả lập một kết quả."""
    monkeypatch.setattr(H, "_tim_lenh", lambda ten: "")
    goc = _du_an(tmp_path)
    for f, ten in ((lambda: H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky"), "yosys"),
                   (lambda: H.lint(goc=goc, nguon=goc / "rtl"), "verilator")):
        kq = f()
        assert not kq.dat
        assert ten in kq.vi_sao_khong_dat and "G-TOOL" in kq.vi_sao_khong_dat


def test_cong_cu_hdl_da_dang_ky():
    from eide.tools import build_registry

    r = build_registry()
    ten = {t.name for t in r.all()}
    for c in ("hdl.lint", "hdl.sim", "hdl.synth", "hdl.pnr", "hdl.bitstream"):
        assert c in ten, f"thiếu {c}"


def test_target_flash_co_duong_fpga():
    from eide.tools import build_registry

    r = build_registry()
    sp = next(t for t in r.all() if t.name == "target.flash")
    enum = sp.declaration()["parameters"]["properties"]["cach"]["enum"]
    assert "openfpgaloader" in enum


def test_duong_fpga_goi_duoc_khong_chi_co_trong_thuc_don(tmp_path):
    """DEV-330 — ca trên kiểm `"openfpgaloader"` CÓ trong danh sách tuỳ chọn; ca này kiểm nhánh
    ấy GỌI ĐƯỢC.

    Hai câu đó khác nhau, và khoảng cách giữa chúng từng là một `NameError` sống suốt nhiều
    phiên: `nap_qua_openfpgaloader` gọi `_tim_lenh` mà mô-đun không import nó, nên nhánh FPGA
    đổ ngay lệnh đầu — `E5999: NameError: name '_tim_lenh' is not defined`. Chỉ lộ ra ngày
    03/10/2026, lần đầu có kit thật cắm vào máy.

    Ca này không cần kit và không cần `openFPGALoader`: nó chỉ cần hàm **chạy tới được** chỗ
    kiểm tệp. Đó cũng chính là chỗ `NameError` từng chặn, vì `_tim_lenh` được gọi TRƯỚC khi
    kiểm tệp.
    """
    from eide.build.mach_that import nap_qua_openfpgaloader

    kq = nap_qua_openfpgaloader(tmp_path / "chua-dung-bao-gio.fs")

    # Không ném ngoại lệ là điều kiện đầu; phần còn lại canh rằng nó đi tới đúng chỗ.
    assert kq.cach == "openfpgaloader"
    assert kq.dat is False
    assert kq.vi_sao_khong_dat, "phải nói ra vì sao không nạp được"

    # Chốt chặt: lý do phải là về TỆP, không phải về thiếu công cụ hay lỗi nội bộ. Nếu import
    # bị bỏ lại thì hàm đổ trước khi tới được dòng này.
    vi_sao = kq.vi_sao_khong_dat.lower()
    assert "tep" in vi_sao or "tệp" in vi_sao, (
        f"lý do phải nói về tệp, đang là: {kq.vi_sao_khong_dat!r}")

    # Và không được báo đã đối chiếu: openFPGALoader không đọc ngược so từng byte.
    assert not getattr(kq, "da_verify", False)


def test_duong_fpga_di_het_voi_tep_that(tmp_path, monkeypatch):
    """DEV-330 — ca trên dừng ở chỗ kiểm tệp, nên nó KHÔNG đủ.

    Vá `_tim_lenh` xong thì lỗi thứ hai hiện ra ngay: `_bam_tep` — một cái tên chưa bao giờ
    tồn tại, trong khi ba nhánh nạp kia đều dùng `_hash_tep`. Nó nằm SAU chỗ kiểm tệp, nên ca
    trên đi không tới.

    Bài học của ca này: trên một đường dẫn **chưa bao giờ chạy**, vá một lỗi thì lỗi sau hiện
    ra. Phép kiểm phải đi HẾT đường, không dừng ở lỗi đầu tiên mình vừa sửa.

    Không nạp bo thật: thay `subprocess.run` bằng một bản giả. Việc cần đo là hàm đi hết được
    đường tới lúc gọi lệnh, không phải openFPGALoader có nạp nổi hay không.
    """
    import subprocess as sp_that

    from eide.build import mach_that

    fs = tmp_path / "soc_top.fs"
    fs.write_bytes(b"\x00\x01\x02\x03" * 64)   # tệp THẬT, không rỗng

    monkeypatch.setattr(mach_that, "_tim_lenh", lambda ten: "/gia/openFPGALoader")

    da_goi: list[list[str]] = []

    def run_gia(lenh, **kw):
        da_goi.append(list(lenh))
        return sp_that.CompletedProcess(lenh, 0, stdout="Done\n", stderr="")

    monkeypatch.setattr(mach_that.subprocess, "run", run_gia)

    kq = mach_that.nap_qua_openfpgaloader(fs, bo_kit="tangnano20k")

    # Đi tới được chỗ gọi lệnh — đây là điều `_bam_tep` từng chặn.
    assert da_goi, "chưa gọi tới lệnh nạp"
    assert da_goi[0][1:3] == ["-b", "tangnano20k"]
    assert "-f" not in da_goi[0], "mặc định phải nạp SRAM, không ghi flash"

    # Băm đã tính được: 64 ký tự hex của sha256.
    assert len(kq.hash) == 64 and all(c in "0123456789abcdef" for c in kq.hash)
    assert kq.so_byte == fs.stat().st_size

    # openFPGALoader KHÔNG đọc ngược so từng byte, nên không được khai là đã đối chiếu.
    assert kq.da_verify is False


def test_bat_log_mo_cong_truoc_khi_lam_viec():
    """DEV-331 — bắt bản ghi phải MỞ CỔNG TRƯỚC, không phải đọc sau.

    Đo được 03/10/2026 trên Tang Nano 20K: firmware Bài 2 tính xong, in bốn dòng, rồi vào
    `while(1)` — tất cả trong **khoảng 35 ms**. Gọi `target.log` sau `target.flash` thì byte
    đã phát trong lúc không ai mở cổng, và chip cầu không giữ đệm. `target.log` báo *0 byte,
    cổng im lặng*: đúng về cổng, vô dụng về firmware.

    Ca này không cần kit: dùng một cặp giả lập đầu cuối. Phép phân biệt nằm ở chỗ **rác cũ**:
    hàm phải vét sạch những gì có trước khi làm việc, rồi mới giữ phần phát ra TRONG lúc làm
    việc. Nếu đổi thứ tự thành làm-việc-rồi-mới-mở thì rác cũ sẽ lẫn vào bản ghi, và ca này đỏ.
    """
    import os
    import pty

    from eide.build import mach_that

    chu, con = pty.openpty()
    duong_dan = os.ttyname(con)
    try:
        # Rác có TRƯỚC khi gọi — ví dụ byte còn sót của lượt chạy cũ.
        os.write(chu, b"RAC-CU-TU-LUOT-TRUOC\r\n")
        time.sleep(0.1)

        da_goi: list[int] = []

        def viec():
            da_goi.append(1)
            # Firmware "in một lần rồi dừng": phát ngay trong lúc nạp.
            os.write(chu, b"RESULT,n=4,dtype=I8,ver=V0,ok=1\r\n")
            time.sleep(0.1)
            return "xong"

        ra = mach_that.bat_log_quanh_viec(duong_dan, baud=115200, giay=1.0, viec=viec)
    finally:
        os.close(chu)
        os.close(con)

    assert da_goi == [1], "việc phải được gọi đúng một lần"
    assert ra["kq_viec"] == "xong", "kết quả của việc phải trả về kèm bản ghi"

    # Bắt được phần phát TRONG lúc làm việc — đây là điều `target.log` sau khi nạp không làm nổi.
    assert "RESULT,n=4" in ra["chu"], f"mất phần phát trong lúc làm việc: {ra['chu']!r}"
    assert ra["im_lang"] is False
    assert ra["so_byte"] > 0

    # Và KHÔNG lẫn rác cũ: cổng phải được mở rồi vét sạch TRƯỚC khi việc chạy.
    assert "RAC-CU" not in ra["chu"], (
        "bản ghi lẫn rác của lượt trước — cổng mở sau khi làm việc, hoặc thiếu bước vét")


def test_bat_log_cong_khong_co_thi_noi_ra():
    """Cổng không tồn tại thì phải NÓI, đừng trả bản ghi rỗng trông như bo im lặng.

    Hai chuyện khác nhau hẳn: *bo không gửi gì* là một phép đo về firmware; *không có cổng*
    là một phép đo chưa chạy. Gộp hai cái vào một kết quả rỗng là biến chỗ chưa đo thành chỗ
    đã đo.
    """
    from eide.build import mach_that

    ra = mach_that.bat_log_quanh_viec("/dev/cu.khong-he-co-cong-nay", baud=115200,
                                      giay=1.0, viec=lambda: "khong-duoc-goi")
    assert ra.get("loi"), "phải nói ra là không có cổng"
    assert ra["kq_viec"] is None, "không có cổng thì KHÔNG được chạy việc"
    assert ra["so_byte"] == 0


_DETECT_THAT = """Jtag frequency : requested 6.00MHz    -> real 6.00MHz
index 0:
\tidcode 0x81b
\tmanufacturer Gowin
\tfamily GW2A
\tmodel  GW2A(R)-18(C)
\tirlength 8
"""


def test_doc_idcode_jtag_lay_duoc_con_so_tu_silicon(monkeypatch):
    """DEV-332 — định danh FPGA phải đọc từ chuỗi JTAG, không đi qua SWD.

    `doc_id_chip` đọc bằng `st-info` qua SWD: đúng cho ARM, vô nghĩa cho FPGA. Với một kit
    FPGA cắm vào máy nó trả *"Found 0 stlink programmers"*, và `target.flash` biến câu ấy
    thành `E4013 "chưa đối chiếu được ID chip"` — gửi người làm đi tìm một mạch nạp ST-Link
    vốn chưa bao giờ liên quan. Đo được 03/10/2026 trên Tang Nano 20K.
    """
    import subprocess as sp

    from eide.build import mach_that

    monkeypatch.setattr(mach_that, "_tim_lenh", lambda ten: "/gia/openFPGALoader")
    monkeypatch.setattr(mach_that.subprocess, "run",
                        lambda l, **k: sp.CompletedProcess(l, 0, _DETECT_THAT, ""))

    idcode, mo_ta, vi_sao = mach_that.doc_idcode_jtag()

    assert idcode == "0x81b", f"không lấy đúng IDCODE: {idcode!r}"
    assert not vi_sao, "đọc được thì không được kèm lý do thất bại"
    for phan in ("Gowin", "GW2A"):
        assert phan in mo_ta, f"thiếu {phan} trong mô tả: {mo_ta!r}"


def test_khong_doc_duoc_idcode_thi_noi_ly_do_cua_FPGA(monkeypatch):
    """Không đọc được thì lý do phải nói về JTAG, KHÔNG nói về ST-Link.

    Đây là nửa đắt nhất của DEV-332. Một lời khuyên không khớp lý do thì tệ hơn im lặng: nó
    gửi tác tử đi làm một việc vốn không liên quan. Ca này canh đúng chỗ ấy.
    """
    import subprocess as sp

    from eide.build import mach_that

    monkeypatch.setattr(mach_that, "_tim_lenh", lambda ten: "/gia/openFPGALoader")
    monkeypatch.setattr(mach_that.subprocess, "run",
                        lambda l, **k: sp.CompletedProcess(l, 0, "Jtag frequency : 6MHz\n", ""))

    idcode, _, vi_sao = mach_that.doc_idcode_jtag()

    assert idcode == ""
    assert vi_sao, "không đọc được thì phải nói ra vì sao"
    assert "stlink" not in vi_sao.lower() and "st-link" not in vi_sao.lower(), (
        f"lý do của đường FPGA không được nhắc ST-Link: {vi_sao!r}")
    assert "JTAG" in vi_sao, f"lý do phải nói về JTAG: {vi_sao!r}"


def test_khong_so_idcode_bang_so_chip():
    """IDCODE không được so bằng `so_chip` — phép so mờ cho BÁO ĐỘNG GIẢ.

    Thử tay 03/10/2026: hộ chiếu dự án ghi `GW2AR-LV18QN88C8/I7`, JTAG khai `GW2A(R)-18(C)`.
    `so_chip` trả **`lech`**, tức cổng `E4012` sẽ báo *"bo đang cắm là chip khác"* cho ĐÚNG
    con bo đúng. Chính chú thích của `so_chip` đã dặn: một cảnh báo sai dạy người dùng bỏ qua
    cảnh báo.

    Ca này không đòi sửa `so_chip` — nó chốt rằng phép so ấy KHÔNG dùng được cho FPGA, để ai
    định nối IDCODE vào đó sẽ thấy ca đỏ.
    """
    from eide.tools.mach_that import so_chip

    assert so_chip("GW2AR-LV18QN88C8/I7", "GW2A(R)-18(C)") == "lech", (
        "nếu phép so này đã khớp được thì xem lại DEV-332: có thể dùng so_chip cho FPGA")


def test_do_bo_bao_duong_jtag_khi_doc_duoc_idcode(monkeypatch):
    """`do_bo(do_jtag=True)` phải trình đường FPGA ra như một đường nạp, không im lặng.

    Và `do_bo()` **không truyền cờ** thì KHÔNG được dò JTAG. Hai nửa của ca này canh hai
    điều ngược nhau, và nửa sau mới là nửa đắt: thêm nhánh JTAG không điều kiện làm 6 ca kiểm
    cũ đỏ, vì chúng vá ba seam `THU_MUC_O_DIA` · `doc_id_chip` · `_cong_noi_tiep` và một lời
    gọi ngoài thứ tư thì lọt qua cả ba. Một hàm mà kết quả đổi theo thứ đang cắm trên bàn thì
    không kiểm được bằng ca kiểm.
    """
    from eide.build import mach_that

    da_goi: list[int] = []

    def jtag_gia():
        da_goi.append(1)
        return ("0x81b", "Gowin · GW2A · GW2A(R)-18(C)", "")

    monkeypatch.setattr(mach_that, "doc_id_chip", lambda: ("", "không có ST-Link", {}))
    monkeypatch.setattr(mach_that, "doc_idcode_jtag", jtag_gia)
    monkeypatch.setattr(mach_that, "_cong_noi_tiep", lambda: [])

    # Nửa 1 — bật cờ thì dò, và trình ra như một đường nạp.
    d = mach_that.do_bo(do_jtag=True)
    assert d["idcode_doc_duoc"] == "0x81b"
    assert d["nap_duoc"] is True, "đọc được IDCODE thì phải coi là nạp được"
    jtag = [t for t in d["thiet_bi"] if t.get("nap_duoc_bang") == "openfpgaloader"]
    assert jtag, "thiếu thiết bị đường JTAG trong danh sách"
    assert jtag[0]["chi_tiet"]["idcode"] == "0x81b"
    assert da_goi == [1]

    # Nửa 2 — KHÔNG bật cờ thì tuyệt đối không gọi tới JTAG.
    da_goi.clear()
    d2 = mach_that.do_bo()
    assert da_goi == [], "do_bo() mặc định không được dò JTAG"
    assert d2["idcode_doc_duoc"] == ""
    assert not [t for t in d2["thiet_bi"] if t.get("nap_duoc_bang") == "openfpgaloader"]


def test_khong_module_nao_goi_ten_chua_dinh_nghia():
    """Bắt CẢ LỚP lỗi của DEV-330 một lượt, thay vì từng cái một.

    Hai lỗi `_tim_lenh` và `_bam_tep` cùng một hình dạng: một cái tên được gọi mà không ở đâu
    định nghĩa, nằm trên đường dẫn chưa bao giờ chạy, nên không ca kiểm nào và không lần chạy
    nào đụng tới. Trình dịch Python không bắt — nó chỉ nổ lúc dòng ấy thật sự chạy.

    Ca này quét cây cú pháp của mọi mô-đun: tên nào được ĐỌC mà không nằm trong tên sẵn có,
    tên nhập vào, tên gán, tham số hay bắt ngoại lệ thì báo. Nó không thay được một bộ kiểm
    chạy thật, nhưng nó rẻ và bắt được đúng loại lỗi chỉ lộ ra khi có phần cứng cắm vào.
    """
    import ast
    import builtins
    import pathlib

    goc = pathlib.Path(__file__).resolve().parents[1] / "src" / "eide"
    # Tên dunder cấp mô-đun: Python cấp sẵn, bộ quét cú pháp không thấy chỗ gán.
    san_co = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__",
                                   "__spec__", "__loader__", "__builtins__", "__path__"}

    loi: dict[str, list[str]] = {}
    for p in sorted(goc.rglob("*.py")):
        try:
            cay = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        dn = set(san_co)
        for n in ast.walk(cay):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                dn.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                dn.add(n.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    dn.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.arg):
                dn.add(n.arg)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                dn.add(n.name)
            elif isinstance(n, ast.Global):
                dn.update(n.names)

        thieu = sorted({n.id for n in ast.walk(cay)
                        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                        and n.id not in dn})
        if thieu:
            loi[str(p.relative_to(goc))] = thieu

    assert not loi, "tên được gọi mà không ở đâu định nghĩa:\n" + "\n".join(
        f"  {k}: {', '.join(v)}" for k, v in loi.items())


# =============================================================== câu then chốt của mô-đun
#
# Ba ca dưới đây canh đúng câu cả `hdl.py` dựa vào: **tệp ra trên đĩa mới là bằng chứng, không
# phải mã thoát.** Chúng dùng một chương trình giả do chính ca kiểm viết ra — không phải để
# giả lập `yosys`, mà để dựng được đúng hai tình huống mà `yosys` thật không chịu dựng: trả 0
# rồi không sinh tệp, và trả 0 rồi sinh tệp rỗng.
#
# Ba phép phá tương ứng đều LỌT ở bản đầu (đo ngày 01/10/2026), nên đây là chỗ bộ kiểm trước
# đó không đo gì.

def _lenh_gia(tmp_path: Path, than: str) -> str:
    p = tmp_path / "gia.sh"
    p.write_text("#!/bin/sh\n" + than + "\nexit 0\n", "utf-8")
    p.chmod(0o755)
    return str(p)


def test_tra_0_ma_KHONG_sinh_tep_thi_khong_dat(tmp_path, monkeypatch):
    """Một chương trình trả 0 mà không sinh tệp nào là chuyện ĐÃ GẶP (DEV-275, phần ARM)."""
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh", lambda ten: _lenh_gia(tmp_path, "true"))
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert not kq.dat, "không có tệp mạng cổng mà báo đạt thì chặng sau nhận đầu vào rỗng"
    assert "không có tệp" in kq.vi_sao_khong_dat


def test_tra_0_va_sinh_tep_RONG_thi_khong_dat(tmp_path, monkeypatch):
    """Tệp rỗng còn tệ hơn không có tệp: chặng sau mở được nó và cũng báo xong."""
    goc = _du_an(tmp_path)
    ra = goc / ".eide" / "hdl" / "blinky.json"
    ra.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(H, "_tim_lenh",
                        lambda ten: _lenh_gia(tmp_path, f": > '{ra}'"))
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert not kq.dat
    assert "rỗng" in kq.vi_sao_khong_dat
    assert "bo mạch" in kq.vi_sao_khong_dat, "lời từ chối phải nói hậu quả, không chỉ nói hiện tượng"


def test_khong_cong_don_hai_khoi_thong_ke(tmp_path):
    """Yosys in bảng hai lần; cộng cả hai thì mọi con số gấp đôi một cách im lặng.

    Dùng TÊN Ô KHÁC NHAU ở hai khối, vì nếu trùng tên thì phép ghi đè của `dict` che mất lỗi —
    đó đúng là lý do phép phá này lọt ở bản đầu.
    """
    ra = H.doc_tai_nguyen_yosys("""
Printing statistics.
        +----------Local Count, excluding submodules.
       10   LUT1
=== design hierarchy ===
        +----------Count including submodules.
     5000   LUT4
""")
    assert ra["lut"] == 5000, (
        "chỉ được đếm khối tính cả mô-đun con; cộng cả hai khối ra 5010")
    assert "LUT1" not in ra["chi_tiet"], "ô của khối Local Count không được lọt vào bảng"


def test_cong_cu_hdl_goi_duoc_qua_registry(tmp_path):
    """Gọi THẬT qua kho công cụ, không chỉ gọi lớp lõi.

    Bản đầu của `_goc()` đọc `ctx.project_root` thay vì `ctx.config.paths.project_root`. Lớp
    lõi vẫn chạy, mọi ca kiểm cũ vẫn xanh, và cả năm công cụ đổ ngay lời gọi đầu tiên với
    `E5999 AttributeError` — một mã lỗi không nói được gì cho tác tử, và chỉ hiện ra khi tác
    tử dùng thật.

    Ca này đi qua đúng đường tác tử đi: `registry.call`.
    """
    from types import SimpleNamespace

    from eide.tools import build_registry

    goc = _du_an(tmp_path)
    r = build_registry()
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=goc)),
        run_id="test", store=SimpleNamespace(get=lambda _m: None, apply=lambda **_k: None))
    sp = next(t for t in r.all() if t.name == "hdl.lint")
    kq = sp.fn(ctx, explain={"summary": "kiểm", "why": "ca kiểm"}, nguon="rtl")
    # Đạt hay không tuỳ Verilator; điều ca này canh là KHÔNG ném ngoại lệ, và trả về thứ đọc
    # được — chứ không phải `E5999`.
    assert kq is not None
    assert not isinstance(kq, BaseException)


# =============================================================== tệp còn sót từ lần trước
#
# Lỗi nguy hiểm nhất của một dây chuyền nhiều chặng, và nó đã xảy ra thật ngày 01/10/2026:
# `nextpnr` dừng với `ERROR: Failed to open ... No such file` và trả mã 1, nhưng tệp bố trí
# của LẦN CHẠY TRƯỚC vẫn nằm trên đĩa — nên chặng báo **đạt**, `fmax_mhz=None`, và phép canh
# định thời bị bỏ qua hoàn toàn. Chặng sau ăn tệp cũ, mọi thứ xanh, bitstream mang thiết kế
# của lần sửa trước.

def test_tep_con_sot_tu_lan_truoc_KHONG_duoc_tinh_la_dat(tmp_path, monkeypatch):
    """Lệnh trả mã lỗi mà tệp cũ còn đó thì vẫn phải KHÔNG đạt."""
    goc = _du_an(tmp_path)
    ra = goc / ".eide" / "hdl" / "blinky.json"
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text('{"ket qua cu": 1}', "utf-8")        # tệp của "lần chạy trước"
    monkeypatch.setattr(H, "_tim_lenh",
                        lambda ten: _lenh_gia(tmp_path, "echo 'ERROR: hong' >&2; exit 1"))
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert not kq.dat, "tệp cũ còn sót mà báo đạt thì chặng sau ăn thiết kế của lần trước"


def test_tep_ra_bi_xoa_truoc_khi_chay(tmp_path, monkeypatch):
    """"Tệp có mặt" phải nghĩa là "lần chạy NÀY sinh ra nó"."""
    goc = _du_an(tmp_path)
    ra = goc / ".eide" / "hdl" / "blinky.json"
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_text("cu", "utf-8")
    monkeypatch.setattr(H, "_tim_lenh", lambda ten: _lenh_gia(tmp_path, "true"))
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert not kq.dat
    assert not ra.exists(), "tệp cũ phải bị xoá trước khi chạy, không được để lại"


@can_yosys
@can_pnr
def test_khong_doc_duoc_fmax_thi_canh_bao_chu_khong_im(tmp_path, monkeypatch):
    """Đạt mà không đọc được Fmax thì phép canh định thời không đo gì — phải nói ra."""
    goc = _du_an(tmp_path)
    assert H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky").dat
    that = H.doc_ket_qua_pnr
    monkeypatch.setattr(H, "doc_ket_qua_pnr", lambda nv: (None, that(nv)[1], []))
    kq = H.dat_di_day(goc=goc, json_mang=goc / ".eide/hdl/blinky.json",
                      cst=goc / "constraints/tangnano20k.cst", tan_so_mhz=27.0)
    assert kq.dat and kq.fmax_mhz is None
    assert any(c.get("ma") == "FMAX_KHONG_DOC_DUOC" for c in kq.canh_bao), (
        "đạt mà không đo được định thời thì phải có cảnh báo, không được im lặng")


def test_ghi_tep_roi_moi_do_thi_KHONG_dat(tmp_path, monkeypatch):
    """Công cụ ghi được một phần rồi mới đổ — tệp có mặt, không rỗng, mà lệnh vẫn thất bại.

    Đây là ca duy nhất phân biệt được hai lớp canh. Lớp "tệp phải có mặt" không bắt được, vì
    tệp CÓ mặt; chỉ lớp "mã thoát phải bằng 0" mới bắt. Và tình huống này không bịa: một công
    cụ ghi dở rồi gặp lỗi là chuyện bình thường, còn tệp ghi dở thì chặng sau đọc được một
    phần và chạy tiếp với dữ liệu cụt.
    """
    goc = _du_an(tmp_path)
    ra = goc / ".eide" / "hdl" / "blinky.json"
    ra.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        H, "_tim_lenh",
        lambda ten: _lenh_gia(tmp_path, f"echo '{{\"mot nua\":1}}' > '{ra}'; "
                                        "echo 'ERROR: het bo nho' >&2; exit 1"))
    kq = H.tong_hop(goc=goc, nguon=goc / "rtl", dinh="blinky")
    assert ra.exists() and ra.stat().st_size > 0, "ca này cần tệp CÓ mặt và không rỗng"
    assert not kq.dat, "lệnh trả mã lỗi thì không đạt, dù tệp có mặt"


# =============================================================== khối <resume>

def test_resume_khong_bao_tac_tu_lam_lai_viec_cu(tmp_path):
    """Dòng "lượt chưa kết thúc" phải nói rõ ĐỪNG tự làm lại.

    Đo ngày 01/10/2026, phiên FPGA: khối `<resume>` ghi "Lượt run-00N chưa kết thúc", cộng với
    lời dặn "việc dở dang thì nói ra TRƯỚC khi làm" — tác tử hiểu là phải làm nốt, và **bốn
    lượt liền nó lặp lại việc của lượt trước** thay vì việc vừa được giao.

    Dòng ấy còn thường SAI: `turn.end` được ghi đúng lúc khối resume đang dựng, nên một lượt đã
    xong vẫn hiện ở đây. Một cuộc đua ghi/đọc, không phải một lượt hỏng.
    """
    from eide.memory import resume as R

    nguon = (tmp_path / "resume_src.py")
    src = __import__("inspect").getsource(R)
    assert "đừng tự làm lại việc của lượt" in src or "đừng** tự làm lại" in src, (
        "lời nhắc phải nói thẳng là đừng làm lại")
    assert "ledger.query" in src, "phải chỉ cách tra xem lượt cũ đã làm tới đâu"
    assert "hỏi người dùng" in src, "còn dở thật thì hỏi, không tự quyết"
    assert "việc cũ chỉ được làm lại khi người" in src, (
        "lời dặn cuối khối phải nói rõ: nói ra ≠ làm nốt")


# =============================================================== gói Python cho tính toán

def test_lenh_cai_python_dung_moi_truong_ao():
    """KHÔNG được `pip install --user`, và tuyệt đối không `--break-system-packages`.

    Python của Homebrew đánh dấu "externally managed" theo PEP 668 nên `--user` bị chặn. Gợi ý
    `--break-system-packages` trong thông báo lỗi đúng tên của nó — nó phá môi trường hệ thống
    của người dùng, và EIDE không được làm thế để cài một gói cho mình.
    """
    from eide.build.toolchain import CAN_GI

    for c in CAN_GI["python-so-lieu"]:
        l = c["cach_cai"]
        assert "venv" in l, f"{c['ten']}: phải dựng môi trường ảo"
        assert "--break-system-packages" not in l, f"{c['ten']}: không được phá môi trường hệ thống"
        assert "--user" not in l, f"{c['ten']}: --user bị PEP 668 chặn trên máy này"
        assert "sudo" not in l


def test_kiem_goi_python_tra_rong_khi_chua_co(monkeypatch, tmp_path):
    """Chưa có môi trường ảo thì trả rỗng, KHÔNG ném ngoại lệ."""
    import eide.build.toolchain as TC

    monkeypatch.setattr(TC, "_VENV_PY", tmp_path / "khong-he-co")
    assert TC._kiem_goi_python("numpy") == ""


def test_numpy_dung_ham_kiem_rieng_chu_khong_tim_trong_PATH():
    """`numpy` không phải một lệnh — tìm nó trong PATH thì luôn ra 'thiếu'."""
    from eide.build.toolchain import CAN_GI, _KIEM_RIENG

    np = next(c for c in CAN_GI["python-so-lieu"] if c["ten"] == "numpy")
    assert np.get("kiem") == "numpy"
    assert "numpy" in _KIEM_RIENG


# =============================================================== tab Thiết kế cho dự án FPGA

class _KhoGia:
    """Kho giả tối thiểu cho `surfaces.design`.

    Cần cả `list` chứ không chỉ `get`: khối kiến trúc phần mềm (A5.6) duyệt kho để tìm phương
    án đã chốt. Bản đầu chỉ có `get` và năm ca kiểm đổ với `AttributeError` — một lời nhắc
    rằng kho giả phải giả đủ bề mặt mà bên gọi dùng, không chỉ bề mặt mình đang nghĩ tới.
    """

    def __init__(self, **muc):
        self._m = muc

    def get(self, ma):
        return self._m.get(ma)

    def list(self, *a, **k):
        return []


def _pnr_gia(**ghi_de):
    c = {"dat": True, "fmax_mhz": 134.93, "so_byte_ra": 151148,
         "tai_nguyen": {"dung": {"LUT4": {"dung": 2180, "tong": 20736, "ty_le": 0.1051},
                                 "DFF": {"dung": 820, "tong": 15552, "ty_le": 0.0527},
                                 "VCC": {"dung": 1, "tong": 1, "ty_le": 1.0}},
                        "dong_ho": [{"dong_ho": "clk", "fmax_mhz": 134.93,
                                     "ket": "PASS", "dich_mhz": 27.0}]}}
    c.update(ghi_de)
    return {"canonical": c, "stale": False}


def test_tab_thiet_ke_hien_tai_nguyen_fpga():
    """Tab Thiết kế dựng cho dự án bo mạch in; dự án FPGA đi qua thì TRẮNG XOÁ.

    Dữ liệu đã nằm sẵn trong kho (`hdl.pnr` ghi `build:hdl:pnr` sau mỗi lần đặt-đi dây) —
    thiếu đúng một khối đọc nó ra. Anh Công nêu ngày 02/10/2026.
    """
    import eide.surfaces as S

    m = S.design(_KhoGia(**{"build:hdl:pnr": _pnr_gia()}), None)
    k = next(x for x in m["blocks"] if x["code"] == "A5.11")
    assert "134.93" in k["summary"] and "27" in k["summary"]
    assert "ĐẠT" in k["summary"]
    ten = [r[0] for r in k["rows"]]
    assert "LUT4" in ten and "DFF" in ten


def test_bang_tai_nguyen_bo_nguyen_thuy_toan_cuc():
    """VCC/GND/GSR luôn 1/1 = 100 % và luôn đứng đầu khi sắp theo tỷ lệ.

    Để chúng lại thì ba dòng đáng nhìn bị đẩy xuống, và người đọc học rằng cột tỷ lệ không có
    nghĩa — lúc một ô thật sự chạm trần thì họ cũng bỏ qua.
    """
    import eide.surfaces as S

    m = S.design(_KhoGia(**{"build:hdl:pnr": _pnr_gia()}), None)
    k = next(x for x in m["blocks"] if x["code"] == "A5.11")
    assert "VCC" not in [r[0] for r in k["rows"]]


def test_canh_bao_vuot_nguong_chi_gan_cho_o_LOGIC():
    """Ngưỡng 85 % của đề bài là ngưỡng cho LOGIC, không phải cho mọi loại ô."""
    import eide.surfaces as S

    pnr = _pnr_gia()
    pnr["canonical"]["tai_nguyen"]["dung"]["LUT4"] = {"dung": 19000, "tong": 20736,
                                                      "ty_le": 0.916}
    pnr["canonical"]["tai_nguyen"]["dung"]["IOB"] = {"dung": 380, "tong": 384, "ty_le": 0.99}
    m = S.design(_KhoGia(**{"build:hdl:pnr": pnr}), None)
    k = next(x for x in m["blocks"] if x["code"] == "A5.11")
    d = {r[0]: r[3] for r in k["rows"]}
    assert "vượt ngưỡng" in d["LUT4"], "LUT quá 85 % phải có cảnh báo"
    assert "vượt ngưỡng" not in d["IOB"], "chân vào-ra 99 % là bình thường, không phải lỗi"


def test_dat_ma_khong_doc_duoc_fmax_thi_noi_ra():
    """Một bảng tài nguyên đẹp dễ làm người đọc tin rằng định thời cũng đã được kiểm."""
    import eide.surfaces as S

    pnr = _pnr_gia(fmax_mhz=None)
    pnr["canonical"]["tai_nguyen"]["dong_ho"] = []
    m = S.design(_KhoGia(**{"build:hdl:pnr": pnr}), None)
    k = next(x for x in m["blocks"] if x["code"] == "A5.11")
    assert "CHƯA được kiểm" in k["summary"]


def test_chua_dat_di_day_thi_noi_ro_vi_sao_trong():
    """Khối trống phải nói vì sao trống và cần gì — không được chỉ im lặng."""
    import eide.surfaces as S

    m = S.design(_KhoGia(), None)
    k = next(x for x in m["blocks"] if x["code"] == "A5.11")
    assert "hdl.pnr" in json.dumps(k, ensure_ascii=False)


# ================================================ đường dẫn từ kho tới chỗ đối chiếu ISA
#
# Ngày 02/10/2026: một phép đo so hai cấu hình CPU (có bộ nhân / không có) bằng một mã máy
# dịch với `-march=rv32i` — không chứa lệnh nhân nào. Hai lượt ra số BẰNG NHAU, và con số
# bằng nhau ấy bị đọc thành "bộ nhân không giúp gì". Không công cụ nào nói gì: cả hai lượt
# `ok=true`, cả hai in ra số.
#
# `toolchain.kiem_khop_phan_cung` nay nói ra chuyện đó. Nhưng một hàm kiểm đúng mà không ai
# gọi thì bằng không có — nên ca này đi qua ĐÚNG đường tác tử đi, và canh cả hai chặng của
# đường ấy: đọc được dữ kiện từ kho, VÀ mang cảnh báo ra tới kết quả trả về.

def test_hdl_sim_doc_lenh_mo_rong_tu_kho_va_canh_bao(tmp_path):
    from types import SimpleNamespace

    from eide.tools import build_registry

    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(
        "module tb; initial begin $display(\"PASS\"); $finish; end endmodule\n", "utf-8")

    # Kho đã có kết quả biên dịch, và nó nói: mã máy làm phép nhân bằng phần mềm.
    kho = {"build:firmware": SimpleNamespace(
        canonical={"dat": True, "lenh_mo_rong": {"goi_mulsi3": 5, "noi_goi_mulsi3": 1}})}
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=goc)),
        run_id="test",
        store=SimpleNamespace(get=kho.get, apply=lambda **_k: None))

    sim = next(t for t in build_registry().all() if t.name == "hdl.sim")
    kq = sim.fn(ctx, explain={"summary": "đo", "why": "ca kiểm"},
                nguon="rtl", dinh="tb", dinh_nghia={"CFG_MUL": "1"})

    d = kq if isinstance(kq, dict) else getattr(kq, "data", {}) or {}
    canh = d.get("canh_bao") or []
    assert any(c.get("ma") == "ISA_KHONG_KHOP" for c in canh), (
        f"Không thấy cảnh báo ISA_KHONG_KHOP. canh_bao={canh}")


def test_hdl_sim_khong_canh_bao_khi_kho_trong(tmp_path):
    """Kho chưa có kết quả biên dịch thì im — không đoán, không cảnh báo bừa."""
    from types import SimpleNamespace

    from eide.tools import build_registry

    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(
        "module tb; initial begin $display(\"PASS\"); $finish; end endmodule\n", "utf-8")
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=goc)),
        run_id="test",
        store=SimpleNamespace(get=lambda _m: None, apply=lambda **_k: None))
    sim = next(t for t in build_registry().all() if t.name == "hdl.sim")
    kq = sim.fn(ctx, explain={"summary": "đo", "why": "ca kiểm"},
                nguon="rtl", dinh="tb", dinh_nghia={"CFG_MUL": "1"})
    d = kq if isinstance(kq, dict) else getattr(kq, "data", {}) or {}
    assert not any(c.get("ma") == "ISA_KHONG_KHOP" for c in (d.get("canh_bao") or []))


# ========================================= hết hạn phải diệt CẢ NHÓM, không chỉ con trực tiếp
#
# Ngày 02/10/2026: một lượt `hdl.synth` chạm hạn 1 800 giây, báo trượt đúng, và `hdl.pnr` từ
# chối đúng vì không có tệp mạng cổng. Mọi thứ nhìn như đã xử lý xong.
#
# Nhưng `yosys` gọi `sh -c yosys-abc ...`, và `subprocess.run(timeout=...)` chỉ diệt `yosys`.
# `sh` với `yosys-abc` sống sót, và 49 phút sau vẫn đang cày — giành CPU của lượt chạy kế
# tiếp. Lượt sau chậm đi, và một phép đo thời gian bị tiến trình mồ côi làm lệch là một phép
# đo sai mà trông không có gì sai cả.

def test_het_han_diet_ca_chau_khong_chi_con(tmp_path):
    """Tiến trình cháu phải chết theo, không được sống sót sau khi lượt chạy đã bị dừng."""
    import os
    import signal
    import time

    from eide.build.hdl import KetQuaHdl, _chay

    dau = tmp_path / "chau.pid"
    # `sh` đẻ ra một tiến trình cháu sống lâu, ghi pid của nó ra tệp, rồi tự chờ.
    kich = (f"sh -c 'echo $$ > {dau}; exec sleep 300' & sleep 300")
    kq = KetQuaHdl(chang="thu")
    _chay(kq, ["/bin/sh", "-c", kich], cwd=tmp_path, han=2)

    assert kq.ma_thoat is None, "phải báo là hết hạn"
    assert "chạy quá 2 giây" in kq.vi_sao_khong_dat

    assert dau.exists(), "tiến trình cháu chưa kịp ghi pid — ca kiểm không đo được gì"
    pid = int(dau.read_text().strip())

    # Cho hệ điều hành một nhịp để thu dọn.
    for _ in range(30):
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return                                  # cháu đã chết — đúng
        time.sleep(0.1)

    # Còn sống: dọn rồi mới báo trượt, để ca kiểm không để lại rác trên máy.
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
    raise AssertionError(
        f"tiến trình cháu {pid} còn sống sau khi lượt chạy đã bị dừng — đúng cái lỗi "
        "để lại yosys-abc mồ côi cày 49 phút ngày 02/10/2026")


# ========================================= A8.0: kết quả bộ kiểm HDL phải HIỆN RA
#
# Tab Mô phỏng dựng cho `sim.run` của vi điều khiển — nó đọc hiện vật loại `sim_result`.
# `hdl.sim` ghi vào `build:hdl:sim`, một khoá khác hẳn. Nên **kết quả mọi bộ kiểm HDL không
# hiện ở đâu trên giao diện**, kể cả khi vừa chạy 1 000 bộ giá trị ngẫu nhiên và bắt 7/7 phép
# phá mã. Lại đúng cái mẫu: cơ chế có sẵn, đường dẫn tới nó đứt.

def _kho_mot_muc(ma: str, canonical: dict):
    class _Kho:
        def get(self, m):
            return {"id": ma, "canonical": canonical} if m == ma else None
        def list(self, *_a, **_k):
            return []
    return _Kho()


def test_A8_hien_ket_qua_bo_kiem_hdl():
    from eide.surfaces import _khoi_mo_phong_hdl

    k = _khoi_mo_phong_hdl(_kho_mot_muc("build:hdl:sim", {
        "dat": True, "pass_fail": "PASS", "cong_cu": "iverilog", "giay": 0.21,
        "ma_thoat": 0, "do_nhay": {"bat": 7, "tong": 7}}))
    assert k, "có kết quả trong kho mà khối không hiện gì"
    chu = str(k)
    assert "ĐẠT" in chu
    assert "7/7" in chu, "con số độ nhạy phải hiện ra — nó là thứ nói bộ kiểm canh được gì"


def test_A8_noi_RA_khi_do_nhay_CHUA_DO():
    """Một bộ kiểm PASS mà chưa ai phá mã thì chưa biết nó canh được gì.

    Nấc 3a của Bài 3 từng PASS với hai lỗ, và chỉ phép đo độ nhạy mới thấy. Nên khi thiếu con
    số ấy, khối phải NÓI RA là thiếu — không được im lặng hiện một chữ PASS màu xanh.
    """
    from eide.surfaces import _khoi_mo_phong_hdl

    k = _khoi_mo_phong_hdl(_kho_mot_muc("build:hdl:sim", {
        "dat": True, "pass_fail": "PASS", "cong_cu": "iverilog", "giay": 0.2}))
    chu = str(k)
    assert "CHƯA ĐO" in chu, f"im lặng về độ nhạy là nửa sự thật. Khối: {chu[:400]}"
    assert "phá mã" in chu, "phải nói luôn cách đo, không chỉ nói là thiếu"


def test_A8_noi_ro_khi_bo_kiem_khong_in_gi():
    from eide.surfaces import _khoi_mo_phong_hdl

    k = _khoi_mo_phong_hdl(_kho_mot_muc("build:hdl:sim", {
        "dat": False, "pass_fail": "", "cong_cu": "iverilog", "giay": 0.2,
        "vi_sao_khong_dat": "Testbench không in gì."}))
    chu = str(k)
    assert "KHÔNG ĐẠT" in chu
    assert "KHÔNG in PASS/FAIL" in chu, "một testbench im lặng khác một testbench in FAIL"


def test_A8_khong_co_gi_thi_khong_them_khoi_rong():
    from eide.surfaces import _khoi_mo_phong_hdl

    class _Rong:
        def get(self, _m): return None
        def list(self, *_a, **_k): return []
    assert _khoi_mo_phong_hdl(_Rong()) == []


def test_do_nhay_di_theo_hien_vat_khong_chi_tra_cho_mo_hinh(tmp_path):
    """`test.sensitivity` đo được độ nhạy nhưng KHÔNG ghi hiện vật nào — con số chỉ nằm trong
    hội thoại rồi mất. Nên khối A8.0 không có cách nào biết. Ca này canh đường dẫn mới."""
    from types import SimpleNamespace

    from eide.tools import build_registry

    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(
        "module tb; initial begin $display(\"PASS\"); $finish; end endmodule\n", "utf-8")
    ghi: dict = {}
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=goc)),
        run_id="test",
        store=SimpleNamespace(get=lambda _m: None,
                              apply=lambda **k: ghi.update(k)))
    sim = next(t for t in build_registry().all() if t.name == "hdl.sim")
    sim.fn(ctx, explain={"summary": "đo", "why": "ca kiểm"},
           nguon="rtl", dinh="tb", do_nhay={"bat": 6, "tong": 7})

    dn = ghi.get("canonical", {}).get("do_nhay") or {}
    # M3-13 thêm khoá `do_bang` vào cùng dict này, nên ca kiểm không chốt cứng cả dict nữa
    # — điều nó canh là `bat`/`tong` CÓ VÀO KHO, không phải dict ấy gồm đúng mấy khoá.
    assert (dn.get("bat"), dn.get("tong")) == (6, 7), (
        f"độ nhạy không vào kho — lượt sau không ai biết nó từng được đo. Đã ghi: {dn}")


def test_A8_di_qua_BO_DUNG_TAB_that_khong_chi_goi_ham():
    """Ca này đỏ khi khối chưa được NỐI vào tab — ca trên thì không.

    Năm ca `test_A8_*` phía trên gọi `_khoi_mo_phong_hdl` trực tiếp, nên chúng vẫn xanh khi tôi
    thử bỏ dòng `khoi += _khoi_mo_phong_hdl(store)` ra khỏi `simulation()`. Đúng cái bài học
    của `_goc()`: lớp lõi xanh không nói gì về việc lớp trên có nối đúng không, và cả năm công
    cụ `hdl.*` từng đổ vì chính chuyện đó.
    """
    from eide.surfaces import simulation

    kho = _kho_mot_muc("build:hdl:sim", {
        "dat": True, "pass_fail": "PASS", "cong_cu": "iverilog", "giay": 0.21,
        "do_nhay": {"bat": 7, "tong": 7}})

    class _Inv:
        def __getattr__(self, _n):
            return lambda *a, **k: None

    bm = simulation(kho, _Inv())
    ma = [b.get("code") or b.get("id") for b in (bm.get("blocks") or [])]
    assert any(str(m).startswith("A8.0") for m in ma), (
        f"khối A8.0 chưa được nối vào tab Mô phỏng — khối hiện có: {ma}")
    assert "7/7" in str(bm), "con số độ nhạy phải tới được tab, không chỉ tới hàm dựng khối"


# =============================================================== M3-12 đọc PASS/FAIL cho chặt
#
# Bản cũ đọc kết quả mô phỏng bằng đúng ba dòng:
#
#     tren = kq.nguyen_van.upper()
#     co_pass, co_fail = "PASS" in tren, "FAIL" in tren
#     kq.dat = co_pass and not co_fail
#
# Ba lỗ, và cả ba đều cho ra một chữ PASS màu xanh:
#
#   `nguyen_van` là log BIÊN DỊCH **cộng** log chạy. Nên một cảnh báo của iverilog nhắc tên
#   tệp `pass_through.v` làm cả chặng "đạt" — testbench không in gì cũng được.
#   Dò CHUỖI CON, nên "bypass mode on" chứa "PASS".
#   KHÔNG xét `ma_thoat`, nên `$fatal` sau khi đã in PASS thì vẫn đạt.
#
# Đây là ô xanh giả nằm trên **chính đường đo** — loại đắt nhất, vì mọi thứ phía sau đều tin
# vào nó.
def _hai_lenh(tmp_path: Path, than_bien_dich: str, than_chay: str, ma_thoat: int = 0):
    """Trả một `_tim_lenh` giả: `iverilog`/`verilator` một thân, `vvp`/`sim` một thân."""
    bd = tmp_path / "bd.sh"
    bd.write_text("#!/bin/sh\n" + than_bien_dich + "\nexit 0\n", "utf-8")
    bd.chmod(0o755)
    ch = tmp_path / "ch.sh"
    ch.write_text("#!/bin/sh\n" + than_chay + f"\nexit {ma_thoat}\n", "utf-8")
    ch.chmod(0o755)

    def _tim(ten: str) -> str:
        return str(ch) if ten in ("vvp", "sim") else str(bd)
    return _tim


# `iverilog -g2012 -o <anh> ...` — tham số thứ BA là đường dẫn tệp mô phỏng.
#
# Bản đầu tôi viết `$4` và hai ca kiểm xanh VÌ LÝ DO SAI: không có tệp ảnh thì `mo_phong`
# dừng ngay ở "iverilog không sinh ra tệp mô phỏng", `vvp` giả chưa bao giờ chạy, nên cái
# nó định đo (đọc log chạy) không được chạm tới lần nào.
_TAO_ANH = ': > "$3"'


def test_doc_ket_qua_tb_dem_ca():
    """TC-M3-12-06 — đếm được bao nhiêu ca PASS, không chỉ "có chữ PASS"."""
    r = H.doc_ket_qua_tb("TEST a PASS\nTEST b PASS\n", 0)
    assert r["so_pass"] == 2 and r["so_fail"] == 0, r
    assert r["pass_fail"] == "PASS" and r["dat"], r


def test_doc_ket_qua_tb_bypass_khong_phai_pass():
    """"bypass mode on" chứa "PASS" — nhưng nó không phải một dòng kết quả."""
    r = H.doc_ket_qua_tb("bypass mode on\nsimulation finished\n", 0)
    assert r["so_pass"] == 0 and not r["dat"], r
    assert r["pass_fail"] == "", r


def test_doc_ket_qua_tb_fatal_va_assertion():
    for log in ("PASS\nFATAL: assertion failed at t=10\n",
                "PASS\n%Error: tb.v:12: Assertion failed\n",
                "TEST x PASS\nERROR: bus contention\n"):
        r = H.doc_ket_qua_tb(log, 0)
        assert not r["dat"], (log, r)
        assert r["ly_do"], r


def test_doc_ket_qua_tb_ma_thoat_khac_0():
    r = H.doc_ket_qua_tb("PASS\n", 1)
    assert not r["dat"] and "mã thoát" in r["ly_do"], r


def test_sim_BYPASS_khong_phai_PASS(tmp_path, monkeypatch):
    """TC-M3-12-01 — testbench in "bypass mode on" thì KHÔNG đạt."""
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh",
                        _hai_lenh(tmp_path, _TAO_ANH, 'echo "bypass mode on"'))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat, kq.nguyen_van
    assert kq.pass_fail == "", kq.pass_fail


def test_sim_PASS_nhung_ma_thoat_1_thi_khong_dat(tmp_path, monkeypatch):
    """TC-M3-12-02 — in PASS rồi thoát 1: chương trình mô phỏng đã chết, PASS vô nghĩa."""
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh",
                        _hai_lenh(tmp_path, _TAO_ANH, 'echo PASS', ma_thoat=1))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat
    assert "mã thoát" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat


def test_sim_PASS_roi_FATAL_thi_khong_dat(tmp_path, monkeypatch):
    """TC-M3-12-03 — `$fatal` sau khi đã in PASS vẫn là không đạt.

    Dòng FATAL ở đây cố ý **không** chứa chữ "failed": bản đầu của ca này dùng
    `"FATAL: assertion failed"`, và mã cũ bắt được nó **do tình cờ** — `"FAILED"` chứa
    `"FAIL"`. Tức ca kiểm xanh cả trước lẫn sau khi sửa, và nó không canh gì.
    """
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh", _hai_lenh(
        tmp_path, _TAO_ANH, 'printf "PASS\\nFATAL: timeout at t=10000\\n"'))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat, kq.nguyen_van
    assert kq.vi_sao_khong_dat, "không đạt mà không nói vì sao"


def test_sim_ten_tep_pass_trong_log_bien_dich_khong_tinh(tmp_path, monkeypatch):
    """TC-M3-12-04 — chữ PASS trong log BIÊN DỊCH không phải kết quả của testbench.

    Đây là lỗ tệ nhất của bản cũ: `nguyen_van` cộng cả hai log, nên một cảnh báo nhắc tên
    tệp `pass_through.v` làm cả chặng "đạt" trong khi testbench **không in gì**.
    """
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh", _hai_lenh(
        tmp_path, 'echo "warning: pass_through.v:3: unused"\n' + _TAO_ANH, 'true'))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat, kq.nguyen_van
    assert "testbench" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat


def test_sim_PASS_o_DAU_DONG_cua_log_bien_dich_khong_tinh(tmp_path, monkeypatch):
    """Một dòng `PASS` do chặng BIÊN DỊCH in ra cũng không phải kết quả của testbench.

    Ca này tách khỏi ca trên vì hai chỗ sửa khác nhau: ca trên canh **phép neo dòng** (chữ
    `pass` giữa tên tệp), ca này canh **chỉ đọc log CHẠY**. Phép "phá lại thì đỏ" chỉ ra
    rằng ca trên không canh được chỗ thứ hai: chữ `pass` của nó nằm giữa dòng, nên phép neo
    dòng đã chặn sẵn và việc đọc log gộp hay log chạy không đổi kết quả.

    Script bọc công cụ in `PASS: ...` ở đầu dòng là chuyện có thật (wrapper lint, Makefile).
    """
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh", _hai_lenh(
        tmp_path, 'echo "PASS: lint clean"\n' + _TAO_ANH, 'true'))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat, kq.nguyen_van
    assert "testbench" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat


def test_sim_dem_ca_pass_vao_ket_qua(tmp_path, monkeypatch):
    """Số ca PASS/FAIL phải vào `to_dict()` — một con số đọc được hơn một chữ."""
    goc = _du_an(tmp_path)
    monkeypatch.setattr(H, "_tim_lenh", _hai_lenh(
        tmp_path, _TAO_ANH, 'printf "TEST a PASS\\nTEST b PASS\\nTEST c FAIL\\n"'))
    kq = H.mo_phong(goc=goc, nguon=goc / "rtl", dinh="tb")
    assert not kq.dat
    d = kq.to_dict()
    assert d["so_ca_pass"] == 2 and d["so_ca_fail"] == 1, d


def test_doc_ket_qua_tb_theo_dung_quy_uoc_THAT_cua_du_an():
    """Quy ước in kết quả của testbench dự án này: **nhãn đứng trước** từ khoá.

    Lấy từ 846 bản ghi chặng mô phỏng thật trong `du-lieu/`, không tự nghĩ ra:

        KET QUA: PASS                    243 lần
        TB_PCPI_DOT4: PASS               201
        KET QUA MO PHONG BAI 2: PASS      51

    Mẫu chỉ neo đầu dòng — như kế hoạch M3-12 ghi — **từ chối oan 588 trong 846** bản ghi
    ấy. Một bộ đọc chặt tới mức gọi mọi testbench đang chạy đúng là "không in gì" thì nó
    không chặt, nó chỉ sai theo chiều khác.
    """
    for log in ("KET QUA: PASS\n",
                "TB_PCPI_DOT4: PASS\n",
                "KET QUA MO PHONG BAI 2: PASS\n",
                "[TB] PASS\n",
                "PASS: Hoan tat 4 phep do, tat ca deu ok=1!\n"):
        r = H.doc_ket_qua_tb(log, 0)
        assert r["dat"] and r["so_pass"] == 1, (log, r)

    r = H.doc_ket_qua_tb("KET QUA: FAIL\n", 0)
    assert not r["dat"] and r["so_fail"] == 1, r


def test_doc_ket_qua_tb_cau_ke_co_chu_pass_khong_tinh():
    """Một câu KỂ có chữ "pass" không phải một dòng kết quả.

    Cũng lấy từ log thật: `OK: Tat ca cac ca am tinh deu pass (khoi im hoan toan...)` —
    có dấu hai chấm, nhưng sau dấu ấy là chữ khác, nên nó không phải dòng kết quả.
    """
    r = H.doc_ket_qua_tb(
        "OK: Tat ca cac ca am tinh deu pass (khoi im hoan toan, acc khong doi).\n", 0)
    assert r["so_pass"] == 0 and not r["dat"], r

    # Và chuỗi con vẫn không tính, dù có dấu hai chấm ở đâu đó trên dòng.
    assert H.doc_ket_qua_tb("note: bypass mode on\n", 0)["so_pass"] == 0
    assert H.doc_ket_qua_tb("warning: pass_through.v:3: unused\n", 0)["so_pass"] == 0


# =============================================================== M3-13 độ nhạy testbench HDL
#
# `hdl.sim` nhận `do_nhay` do **tác tử tự điền**. Mô tả tham số đã dặn "chỉ điền khi đã thật
# sự làm", nhưng một lời dặn không phải một phép đo — và con số ấy đi thẳng vào kho rồi lên
# khối A8.0 như thể nó đã được đo.
#
# Lỗ hổng cùng hình dạng với DEV-288 (`test.sensitivity` cho C): ô xanh của bộ kiểm chưa nói
# gì tới khi biết **cơ chế nào** làm nó xanh. Ở đây còn thêm một tầng: cả con số NÓI VỀ ô
# xanh ấy cũng chỉ là lời khai.
def test_do_nhay_tu_khai_duoc_danh_dau(tmp_path):
    """TC-M3-13-05 — con số tác tử tự điền phải mang nhãn `do_bang="tu_khai"`.

    Không cấm tự khai — có lúc tác tử thật sự đã phá mã bằng tay. Nhưng kho phải phân biệt
    được "đo bằng mã" với "khai bằng lời", vì hai thứ ấy đáng tin khác nhau, và khối A8.0
    hiện chúng giống hệt nhau.
    """
    from types import SimpleNamespace

    from eide.tools import build_registry

    goc = _du_an(tmp_path)
    (goc / "rtl" / "tb.v").write_text(
        'module tb; initial begin $display("PASS"); $finish; end endmodule\n', "utf-8")
    ghi: dict = {}
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=goc)),
        run_id="test",
        store=SimpleNamespace(get=lambda _m: None, apply=lambda **k: ghi.update(k)))
    sim = next(t for t in build_registry().all() if t.name == "hdl.sim")
    sim.fn(ctx, explain={"summary": "đo", "why": "ca kiểm"},
           nguon="rtl", dinh="tb", do_nhay={"bat": 6, "tong": 7})

    dn = ghi.get("canonical", {}).get("do_nhay") or {}
    assert dn.get("bat") == 6 and dn.get("tong") == 7, dn
    assert dn.get("do_bang") == "tu_khai", dn


def test_A8_noi_ro_do_nhay_la_TU_KHAI():
    """Khối A8.0 phải NÓI RA rằng con số ấy do tác tử khai, không phải do mã đo."""
    from eide import surfaces as S

    class _Kho:
        def get(self, ma):
            if ma != "build:hdl:sim":
                return None
            return {"id": ma, "type": "build", "version": 1, "author": "agent:run-1",
                    "canonical": {"dat": True, "pass_fail": "PASS", "cong_cu": "vvp",
                                  "giay": 1.0,
                                  "do_nhay": {"bat": 6, "tong": 7, "do_bang": "tu_khai"}},
                    "explain": {"summary": ""}, "stale": False, "stale_reason": None}

    kh = S._khoi_a8_0(_Kho()) if hasattr(S, "_khoi_a8_0") else None
    if kh is None:
        import inspect
        ten = [n for n, f in inspect.getmembers(S, inspect.isfunction)
               if "A8.0" in (inspect.getsource(f) if f.__module__ == S.__name__ else "")]
        kh = getattr(S, ten[0])(_Kho())
    chu = str(kh)
    assert "6/7" in chu, chu[:300]
    assert "tự khai" in chu, "không nói ra rằng con số do tác tử khai"


@can_iv
def test_hdl_sensitivity_bo_kiem_that_bat_duoc(tmp_path):
    """TC-M3-13-03 — testbench kiểm giá trị cụ thể thì phá RTL phải làm nó ĐỎ."""
    from eide.build import hdl as H2

    goc = tmp_path
    rtl = goc / "rtl"
    rtl.mkdir()
    (rtl / "dem.v").write_text(
        "module dem(input clk, output reg [3:0] q);\n"
        "  initial q = 0;\n"
        "  always @(posedge clk) q <= q + 1;\n"
        "endmodule\n", "utf-8")
    (rtl / "tb.v").write_text(
        "module tb;\n"
        "  reg clk = 0; wire [3:0] q;\n"
        "  dem u(.clk(clk), .q(q));\n"
        "  integer i;\n"
        "  initial begin\n"
        "    for (i = 0; i < 5; i = i + 1) begin #1 clk = 1; #1 clk = 0; end\n"
        "    if (q == 4'd5) $display(\"KET QUA: PASS\");\n"
        "    else $display(\"KET QUA: FAIL q=%0d\", q);\n"
        "    $finish;\n"
        "  end\n"
        "endmodule\n", "utf-8")

    r = H2.do_do_nhay_hdl(goc=goc, rtl=[rtl / "dem.v"], nguon=rtl, dinh="tb")
    assert r["bo_kiem_xanh_luc_dau"], r.get("vi_sao_khong_do_duoc") or r
    assert r["so_thay"] == 1, r["tep"]


@can_iv
def test_hdl_sensitivity_tb_chi_in_PASS_thi_khong_thay(tmp_path):
    """TC-M3-13-04 — testbench in PASS vô điều kiện: phá gì nó cũng xanh.

    Đây là ca đắt nhất của cả nhiệm vụ. Một testbench như thế cho ra đúng chữ "PASS" mà
    `hdl.sim` đọc được, và không ai phân biệt được nó với một testbench thật — trừ phép đo
    này.
    """
    from eide.build import hdl as H2

    goc = tmp_path
    rtl = goc / "rtl"
    rtl.mkdir()
    (rtl / "dem.v").write_text(
        "module dem(input clk, output reg [3:0] q);\n"
        "  initial q = 0;\n"
        "  always @(posedge clk) q <= q + 1;\n"
        "endmodule\n", "utf-8")
    (rtl / "tb.v").write_text(
        "module tb;\n"
        "  reg clk = 0; wire [3:0] q;\n"
        "  dem u(.clk(clk), .q(q));\n"
        "  initial begin #10 $display(\"KET QUA: PASS\"); $finish; end\n"
        "endmodule\n", "utf-8")

    r = H2.do_do_nhay_hdl(goc=goc, rtl=[rtl / "dem.v"], nguon=rtl, dinh="tb")
    assert r["bo_kiem_xanh_luc_dau"], r
    assert r["so_khong_thay"] == 1, r["tep"]
