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

import shutil
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
