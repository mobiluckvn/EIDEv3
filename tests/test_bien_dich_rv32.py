# -*- coding: utf-8 -*-
"""Đường biên dịch RISC-V 32 bit, cho lõi mềm chạy trên FPGA.

Ba thứ bộ kiểm này canh, và cả ba đều đã sai thật một lần trong ngày 01/10/2026:

1. `tim_chuoi_cong_cu` phải mang `march`/`mabi` sang. Quên thì mọi dự án RISC-V rơi xuống nhánh
   AVR và nhận về một câu nói thiếu `avr-gcc` — một lời chỉ dẫn sai hướng.
2. Tệp hex sinh ra phải đúng dạng `$readmemh` của Verilog, **không** phải Intel HEX. Hai định
   dạng cùng đuôi `.hex`; đưa nhầm thì bitstream dựng xong và CPU chạy rác.
3. Lỗi của trình liên kết phải hiện ra kèm tệp và dòng. Trước đó một lỗi cú pháp trong linker
   script hiện thành "trả mã 1 nhưng không in ra lỗi nào có toạ độ".
"""

from __future__ import annotations

import shutil

import pytest

from eide.build.toolchain import (CHUOI_CONG_CU, bien_dich, kiem_khop_phan_cung,
                                  phan_tich_loi, tim_chuoi_cong_cu)

CO_GCC = bool(shutil.which("riscv64-unknown-elf-gcc"))
can_gcc = pytest.mark.skipif(not CO_GCC, reason="máy chưa có riscv64-unknown-elf-gcc")

START_S = """\
    .section .init
    .globl _start
_start:
    la sp, _stack_top
    la a0, _bss_start
    la a1, _bss_end
1:  bge a0, a1, 2f
    sw zero, 0(a0)
    addi a0, a0, 4
    j 1b
2:  call main
3:  j 3b
"""

MAIN_C = """\
#define UART_TX (*(volatile unsigned int *)0x10000000)
static unsigned doc_chu_ky(void) { unsigned c; __asm__ volatile("csrr %0, cycle":"=r"(c)); return c; }
int main(void) { UART_TX = 'A'; return (int)doc_chu_ky(); }
"""

LD_DUNG = """\
ENTRY(_start)
MEMORY { BRAM (rwx) : ORIGIN = 0x00000000, LENGTH = 32K }
SECTIONS {
  .init   : { KEEP(*(.init)) } > BRAM
  .text   : { *(.text*) }      > BRAM
  .rodata : { *(.rodata*) }    > BRAM
  .data   : { *(.data*) }      > BRAM
  .bss    : { _bss_start = .; *(.bss*) *(COMMON) . = ALIGN(4); _bss_end = .; } > BRAM
  _stack_top = ORIGIN(BRAM) + LENGTH(BRAM);
}
"""


def _du_an(tmp_path, ld: str = LD_DUNG):
    sw = tmp_path / "sw"
    sw.mkdir()
    (sw / "start.S").write_text(START_S, "utf-8")
    (sw / "main.c").write_text(MAIN_C, "utf-8")
    (sw / "linker.ld").write_text(ld, "utf-8")
    return tmp_path, sw


# --------------------------------------------------------------- bảng chuỗi công cụ

@pytest.mark.parametrize("isa,march", [("rv32i", "rv32i_zicsr"),
                                       ("rv32im", "rv32im_zicsr"),
                                       ("rv32imac", "rv32imac_zicsr")])
def test_bang_co_rv32(isa, march):
    assert CHUOI_CONG_CU[isa]["march"] == march
    assert CHUOI_CONG_CU[isa]["mabi"] == "ilp32"


@pytest.mark.parametrize("isa", ["rv32i", "rv32im", "rv32imac"])
def test_tim_chuoi_cong_cu_mang_march_sang(isa):
    """Lỗi đã xảy ra thật: thiếu hai khoá này thì dự án RISC-V bị đẩy sang nhánh AVR."""
    cc = tim_chuoi_cong_cu(isa)
    assert cc["march"].startswith("rv32"), "thiếu `march` thì bên gọi không nhận ra RISC-V"
    assert cc["mabi"] == "ilp32"


def test_zicsr_co_trong_moi_march_rv32():
    """`csrr` chung cần `_zicsr`; `rdcycle` thì không. Giữ `_zicsr` để không vỡ ở lượt sau."""
    for isa, cf in CHUOI_CONG_CU.items():
        if isa.startswith("rv32"):
            assert "_zicsr" in cf["march"], f"{isa} thiếu _zicsr"


# --------------------------------------------------------------- đọc lỗi trình liên kết

def test_doc_loi_linker_script_co_toa_do():
    ra = phan_tich_loi(
        "/opt/homebrew/Cellar/riscv-gnu-toolchain/main/bin/ld:"
        "/duong/dan/sw/linker.ld:5: syntax error\n"
        "collect2: error: ld returned 1 exit status\n")
    assert len(ra) >= 1, "lỗi linker script phải hiện ra, không được im lặng"
    l = ra[0]
    assert l.tep.endswith("linker.ld") and l.dong == 5 and l.muc == "error"
    assert "syntax error" in l.thong_diep
    assert l.cot == 0, "không có cột thì ghi 0, đừng ghi 1 như thể đã định vị được"


@pytest.mark.parametrize("dong,mong_tep,mong_dong", [
    ("ld:/a/b/linker.ld:12: non constant expression for ORIGIN", "linker.ld", 12),
    ("/x/ld:/p/sw/start.S:4: undefined reference to `main'", "start.S", 4),
])
def test_doc_cac_dang_loi_linker(dong, mong_tep, mong_dong):
    ra = phan_tich_loi(dong)
    assert ra and ra[0].tep.endswith(mong_tep) and ra[0].dong == mong_dong


def test_khong_nhan_dong_vo_nghia_lam_loi():
    """Dòng không có toạ độ thì KHÔNG được thành một lỗi có toạ độ bịa ra."""
    assert phan_tich_loi("collect2: error: ld returned 1 exit status") == []


# --------------------------------------------------------------- dịch thật

@can_gcc
@pytest.mark.parametrize("isa", ["rv32i", "rv32im"])
def test_dich_that_ra_hex_readmemh(tmp_path, isa):
    goc, sw = _du_an(tmp_path)
    kq = bien_dich(goc=goc, sketch=sw, isa=isa, flash_toi_da=32768)
    assert kq.dat, kq.vi_sao_khong_dat
    assert kq.cong_cu == "riscv64-unknown-elf-gcc"
    assert kq.flash > 0, "kích thước 0 nghĩa là chưa đọc được, không phải chương trình rỗng"

    hexp = goc / kq.tep_hex_readmemh
    assert hexp.exists() and kq.so_tu_readmemh > 0
    dong = hexp.read_text("utf-8").split()
    assert len(dong) == kq.so_tu_readmemh
    # Đúng dạng `$readmemh`: mỗi dòng đúng 8 chữ số hệ 16, không tiền tố, không dấu hai chấm.
    for d in dong:
        assert len(d) == 8 and all(c in "0123456789abcdef" for c in d), d
    assert not any(d.startswith(":") for d in dong), "đây phải là $readmemh, KHÔNG phải Intel HEX"


@can_gcc
def test_thu_tu_byte_la_little_endian(tmp_path):
    """Từng từ trong tệp hex phải là 4 byte của ảnh nhị phân đọc theo little-endian.

    Đây là ca bộ kiểm **thiếu** ở bản đầu, và nó là ca tốn kém nhất nếu lọt: đảo thứ tự byte
    thì tệp hex vẫn đúng hình dạng (28 dòng, mỗi dòng 8 chữ số hệ 16), tổng hợp vẫn xong,
    bitstream vẫn dựng được — và CPU nạp mã lộn byte rồi chạy rác. Không phép đo nào trước lúc
    cắm bo nhìn ra.

    So trực tiếp với `mach.bin` chứ không so với một hằng số chép tay: hằng số chép tay sẽ
    phải sửa mỗi lần đổi cờ biên dịch, và lúc đó người sửa có thể chép luôn giá trị sai.
    """
    goc, sw = _du_an(tmp_path)
    kq = bien_dich(goc=goc, sketch=sw, isa="rv32i")
    assert kq.dat, kq.vi_sao_khong_dat

    raw = (goc / ".eide" / "build" / "mach.bin").read_bytes()
    if len(raw) % 4:
        raw += b"\x00" * (4 - len(raw) % 4)
    tu_hex = (goc / kq.tep_hex_readmemh).read_text("utf-8").split()
    assert len(tu_hex) == len(raw) // 4

    for i, chu in enumerate(tu_hex):
        mong = int.from_bytes(raw[4 * i:4 * i + 4], "little")
        assert int(chu, 16) == mong, (
            f"từ thứ {i}: tệp hex ghi {chu}, mà ảnh nhị phân đọc little-endian là {mong:08x}")

    # Thêm một vế độc lập, không dựa vào `mach.bin`: RV32 không nén thì MỌI từ lệnh có hai bit
    # thấp bằng 0b11. Đảo byte làm byte thấp lên chỗ cao, nên vế này cũng đổ.
    assert int(tu_hex[0], 16) & 0b11 == 0b11, (
        f"từ lệnh đầu tiên {tu_hex[0]} có hai bit thấp khác 0b11 — không phải lệnh RV32 hợp lệ")


@can_gcc
def test_march_that_su_di_vao_lenh(tmp_path):
    """Cờ `-march`/`-mabi` phải có mặt trong lệnh thật, không chỉ trong bảng."""
    goc, sw = _du_an(tmp_path)
    kq = bien_dich(goc=goc, sketch=sw, isa="rv32im")
    assert "-march=rv32im_zicsr" in kq.lenh
    assert "-mabi=ilp32" in kq.lenh
    assert "-nostdlib" in kq.lenh and "-lgcc" in kq.lenh, (
        "RV32I không có lệnh nhân: `a*b` thành lời gọi __mulsi3 trong libgcc")


@can_gcc
def test_thieu_entry_thi_KHONG_bao_dat(tmp_path):
    """`--gc-sections` dọn sạch chương trình mà trình liên kết vẫn trả 0.

    Đây là ca quan trọng nhất của tệp này: thiếu `ENTRY`/`KEEP` thì liên kết "thành công" và
    sinh ra một tệp ảnh rỗng. Nếu EIDE tin mã trả về thì nó báo biên dịch xong cho một
    chương trình không có một lệnh nào.
    """
    ld_thieu = LD_DUNG.replace("ENTRY(_start)\n", "").replace("KEEP(*(.init))", "*(.init)")
    goc, sw = _du_an(tmp_path, ld=ld_thieu)
    kq = bien_dich(goc=goc, sketch=sw, isa="rv32i")
    assert not kq.dat, "tệp ảnh rỗng mà báo đạt thì phép đo này vô dụng"
    assert "ENTRY(_start)" in kq.vi_sao_khong_dat, "lời từ chối phải nói cách sửa"
    assert "KEEP" in kq.vi_sao_khong_dat


@can_gcc
def test_thieu_linker_script_thi_noi_ra(tmp_path):
    sw = tmp_path / "sw"
    sw.mkdir()
    (sw / "main.c").write_text("int main(void){return 0;}", "utf-8")
    kq = bien_dich(goc=tmp_path, sketch=sw, isa="rv32i")
    assert not kq.dat
    assert ".ld" in kq.vi_sao_khong_dat and "BRAM" in kq.vi_sao_khong_dat


# --------------------------------------------------------------- bảng công cụ FPGA

def test_bang_fpga_co_du_bon_chang():
    """Bốn chặng của luồng FPGA phải đủ: thiếu một chặng thì ba chặng kia vô dụng."""
    from eide.build.toolchain import CAN_GI
    ten = {c["ten"] for c in CAN_GI["fpga-gowin"]}
    for can in ("yosys", "nextpnr-himbaechel", "gowin_pack", "openFPGALoader"):
        assert can in ten, f"thiếu chặng {can}"
    bb = {c["ten"] for c in CAN_GI["fpga-gowin"] if c["bat_buoc"]}
    assert {"yosys", "nextpnr-himbaechel", "gowin_pack", "openFPGALoader"} <= bb


def test_lenh_cai_khong_con_lenh_khong_ton_tai():
    """`brew install oss-cad-suite` KHÔNG tồn tại — đã tra ngày 01/10/2026.

    Ca này canh một lỗi mình tự gây ra: bản đầu viết lệnh ấy cho ba công cụ, nghe hợp lý mà
    sai. Một lệnh cài không tồn tại nằm trong bảng còn tệ hơn không có dòng nào: người dùng
    duyệt nó ở cổng G-TOOL, nó chạy, nó thất bại, và lời từ chối nói về Homebrew chứ không nói
    rằng chính EIDE ghi sai.
    """
    from eide.build.toolchain import CAN_GI
    for c in CAN_GI["fpga-gowin"]:
        assert "oss-cad-suite" not in c["cach_cai"] or "github.com" in c["cach_cai"], (
            f"{c['ten']}: `brew install oss-cad-suite` không có thật")


def test_lenh_cai_nextpnr_khong_ghim_cung_mot_ngay():
    """Phải tự tra bản phát hành, không ghim ngày — ghim thì hết hạn rồi báo 404."""
    from eide.build.toolchain import CAN_GI
    c = next(x for x in CAN_GI["fpga-gowin"] if x["ten"] == "nextpnr-himbaechel")
    lenh = c["cach_cai"]
    assert "api.github.com" in lenh, "phải tra bản phát hành qua API"
    assert "uname -m" in lenh, "phải chọn tệp theo kiến trúc máy"
    assert "darwin-arm64" in lenh and "darwin-x64" in lenh
    assert "releases/latest" not in lenh, (
        "KHÔNG được lấy mù bản `latest`: ngày 01/10/2026 bản latest chỉ có tệp x64, nên trên "
        "máy Apple Silicon nó cho ra URL 404")
    assert "sudo" not in lenh, "không được cần quyền quản trị"
    assert "$HOME/.local" not in lenh, (
        "KHÔNG cài vào ~/.local: trên máy này thư mục đó do root sở hữu (755, từ 2023), nên "
        "tar báo Permission denied. Sửa quyền cần sudo — một điểm dừng phải hỏi người dùng, "
        "cái giá quá đắt để cài một công cụ.")
    assert "$HOME/.eide" in lenh, "cài vào thư mục người dùng sở hữu, KHÔNG có dấu cách"
    assert "Application Support" not in lenh, (
        "KHÔNG cài vào ~/Library/Application Support: tên có DẤU CÁCH, mà script bọc của gói "
        "oss-cad-suite không bọc nháy biến đường dẫn, nên gowin_pack báo "
        "'/Users/.../Library/Application: No such file or directory'")


def test_tim_lenh_tim_ca_trong_oss_cad_suite(tmp_path, monkeypatch):
    """Lệnh trong `~/.local/oss-cad-suite/bin` không tự vào PATH — phải tìm thêm ở đó."""
    import eide.build.toolchain as TC
    gia = tmp_path / "oss-cad-suite" / "bin"
    gia.mkdir(parents=True)
    (gia / "nextpnr-himbaechel").write_text("#!/bin/sh\n", "utf-8")
    monkeypatch.setattr(TC, "_OSS_CAD", tmp_path / "oss-cad-suite")
    assert TC._tim_lenh("nextpnr-himbaechel").endswith("oss-cad-suite/bin/nextpnr-himbaechel")
    assert TC._tim_lenh("khong-he-co-lenh-nay") == ""


# --------------------------------------------------------------- hạn thời gian một lượt

def test_han_luot_mac_dinh_khong_doi(monkeypatch):
    """Mặc định phải đúng con số của MDD-40 §B1 — nới là việc của từng dự án."""
    from eide.config import Budget
    monkeypatch.delenv("EIDE_TRAN_GIAY_LUOT", raising=False)
    monkeypatch.delenv("EIDE_TRAN_LOI_GOI_LUOT", raising=False)
    b = Budget()
    assert b.max_seconds == 300.0 and b.max_tool_calls == 40


def test_han_luot_noi_duoc_bang_bien_moi_truong(monkeypatch):
    from eide.config import Budget
    monkeypatch.setenv("EIDE_TRAN_GIAY_LUOT", "1800")
    monkeypatch.setenv("EIDE_TRAN_LOI_GOI_LUOT", "120")
    b = Budget()
    assert b.max_seconds == 1800.0 and b.max_tool_calls == 120


def test_han_luot_khong_sieT_duoc_xuong_duoi_mac_dinh(monkeypatch):
    """Siết hạn mức là cách làm tác tử bỏ việc giữa đường mà vẫn báo xong."""
    from eide.config import Budget
    monkeypatch.setenv("EIDE_TRAN_GIAY_LUOT", "10")
    assert Budget().max_seconds == 300.0


def test_han_luot_co_tran_tren(monkeypatch):
    """Hạn vô hạn biến 'đang làm' thành 'đang treo' mà không ai biết khi nào nên dừng chờ."""
    from eide.config import Budget
    monkeypatch.setenv("EIDE_TRAN_GIAY_LUOT", "999999")
    assert Budget().max_seconds == 7200.0


def test_han_luot_chuoi_vo_nghia_thi_giu_mac_dinh(monkeypatch):
    """Một biến gõ sai không nên làm cả phiên không chạy được."""
    from eide.config import Budget
    monkeypatch.setenv("EIDE_TRAN_GIAY_LUOT", "ba muoi")
    assert Budget().max_seconds == 300.0


def test_khong_cong_cu_nao_cai_vao_thu_muc_root_so_huu():
    """Không lệnh cài nào được trỏ vào `~/.local` — root sở hữu, đo ngày 01/10/2026."""
    from eide.build.toolchain import CAN_GI, CAN_GI_CHUNG
    moi = CAN_GI_CHUNG + [c for ds in CAN_GI.values() for c in ds]
    for c in moi:
        assert "$HOME/.local" not in c["cach_cai"], f"{c['ten']} cài vào ~/.local"


def test_tim_lenh_tim_ca_trong_thu_muc_cong_cu(tmp_path, monkeypatch):
    """`gowin_pack` của pip nằm ở `cong-cu/bin`, không nằm trong PATH."""
    import eide.build.toolchain as TC
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "gowin_pack").write_text("#!/bin/sh\n", "utf-8")
    monkeypatch.setattr(TC, "_THU_MUC_CONG_CU", tmp_path)
    monkeypatch.setattr(TC, "_OSS_CAD", tmp_path / "oss-cad-suite")
    assert TC._tim_lenh("gowin_pack").endswith("bin/gowin_pack")


def test_duong_dan_cai_khong_co_dau_cach():
    """Script bọc của oss-cad-suite không bọc nháy đường dẫn — dấu cách làm nó cắt làm hai.

    Đo ngày 01/10/2026: `bin/gowin_pack` dòng 7 là `exec $release_bindir_abs/tabbypy3 ...`, biến
    không bọc nháy. Cài vào `~/Library/Application Support/...` thì lệnh báo
    `/Users/congvt/Library/Application: No such file or directory`. `nextpnr` và
    `openFPGALoader` là tệp nhị phân nên không vướng; chỉ lệnh nào là script bọc mới vướng — tức
    một lỗi chỉ hiện ở MỘT trong bốn công cụ.
    """
    from eide.build.toolchain import _OSS_CAD, _THU_MUC_CONG_CU
    for d in (_OSS_CAD, _THU_MUC_CONG_CU):
        assert " " not in str(d), f"đường dẫn có dấu cách: {d}"


# ===================================================== khớp ISA với cấu hình phần cứng
#
# Ngày 02/10/2026: một phép đo so hai cấu hình CPU — có bộ nhân và không có — bằng một mã máy
# dịch với `-march=rv32i`, tức không chứa lệnh nhân nào. Hai lượt ra số GIỐNG HỆT NHAU, và
# con số giống nhau ấy bị đọc thành "bộ nhân không giúp gì". Không công cụ nào nói gì cả:
# cả hai lượt `ok=true`, cả hai in ra số. Đây là loại sai không hiện ra thành lỗi.

def test_khop_phan_cung_bat_bo_nhan_ma_khong_co_lenh_nhan():
    canh = kiem_khop_phan_cung(
        {"goi_mulsi3": 5, "noi_goi_mulsi3": 1}, {"CFG_MUL": "1"})
    assert len(canh) == 1
    # Lời cảnh báo phải nói ra HỆ QUẢ, không chỉ nói là lệch nhau: hệ quả mới là chỗ người
    # đọc hiểu vì sao hai con số bằng nhau không phải một kết luận.
    assert "BẰNG NHAU" in canh[0]
    assert "rv32im" in canh[0]


def test_khop_phan_cung_co_lenh_nhan_ma_cpu_khong_co_bo_nhan():
    canh = kiem_khop_phan_cung({"lenh_m": 4}, {"CFG_MUL": "0"})
    assert len(canh) == 1
    assert "lệnh lạ" in canh[0]
    assert "rv32i" in canh[0]


def test_khop_phan_cung_hai_cap_dung_thi_im():
    assert kiem_khop_phan_cung({"lenh_m": 4}, {"CFG_MUL": "1"}) == []
    assert kiem_khop_phan_cung({"goi_mulsi3": 5}, {"CFG_MUL": "0"}) == []


def test_khop_phan_cung_nhan_ca_ten_ENABLE():
    """Tên tham số mô-đun Verilog, không chỉ tên macro của testbench."""
    canh = kiem_khop_phan_cung({"lenh_m": 4}, {"ENABLE_MUL": "0"})
    assert len(canh) == 1


def test_khop_phan_cung_khong_biet_thi_khong_doan():
    """Không tháo mã được thì im, không được cảnh báo bừa."""
    assert kiem_khop_phan_cung({}, {"CFG_MUL": "1"}) == []
    # Và không có khoá nào về bộ nhân trong cấu hình thì cũng không có gì để đối chiếu.
    assert kiem_khop_phan_cung({"lenh_m": 4}, {"CFG_PCPI": "1"}) == []


def test_mo_phong_mang_canh_bao_isa_ra_ngoai(tmp_path):
    """Cảnh báo phải tới được chỗ người đọc, không chỉ tồn tại trong hàm kiểm."""
    from eide.build import hdl
    (tmp_path / "tb.v").write_text(
        "module tb; initial begin $display(\"PASS\"); $finish; end endmodule\n")
    kq = hdl.mo_phong(goc=tmp_path, nguon=tmp_path, dinh="tb",
                      dinh_nghia={"CFG_MUL": "1"},
                      lenh_mo_rong={"goi_mulsi3": 5})
    ma = [c.get("ma") for c in kq.canh_bao]
    assert "ISA_KHONG_KHOP" in ma
