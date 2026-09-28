# -*- coding: utf-8 -*-
"""Biên dịch bare-metal cho ARM Cortex-M (STM32F469 là ca thật đầu tiên).

Bộ này canh ba thứ dễ sai mà sai thì KHÔNG lộ ra ở lúc biên dịch:

1. **Kích thước.** Bộ đọc của AVR (`avr-size -C`, tìm "Program:/Data:") khớp 0 dòng trên đầu
   ra của binutils ARM và trả về (0, 0). "Firmware nặng 0 byte" vẫn đi tiếp được vào phép so
   hạn mức và cho ra kết luận "vừa chip" cho mọi firmware.
2. **`-mcpu` và FPU.** Dịch cho M7 rồi nạp vào M4 sinh lệnh chip không hiểu; bật hard-float
   trên chip không có FPU thì hard-fault ở lệnh dấu phẩy động đầu tiên. Cả hai chỉ hiện ra
   trên bo thật.
3. **Linker script.** Nó quyết định địa chỉ Flash/RAM. Đoán một địa chỉ thì firmware dịch
   xong, nạp xong, và không chạy.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from eide.build import toolchain as TC

CO_ARM = shutil.which("arm-none-eabi-gcc") is not None
can_arm = pytest.mark.skipif(not CO_ARM, reason="máy không có arm-none-eabi-gcc")

LD = """MEMORY {
  FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 2048K
  RAM  (rwx) : ORIGIN = 0x20000000, LENGTH = 320K
}
ENTRY(Reset_Handler)
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text   : { *(.text*) *(.rodata*) } > FLASH
  .data   : { *(.data*) } > RAM AT > FLASH
  .bss    : { *(.bss*) *(COMMON) } > RAM
  _estack = ORIGIN(RAM) + LENGTH(RAM);
}
"""

C = """#include <stdint.h>
extern uint32_t _estack;
void Reset_Handler(void);
static volatile uint32_t dem;
__attribute__((section(".isr_vector"), used))
uint32_t const vector[2] = { (uint32_t)&_estack, (uint32_t)Reset_Handler };
void Reset_Handler(void) { for (;;) dem++; }
"""


def _du_an(tmp_path, *, ld: str | None = LD, c: str = C, ten_ld: str = "mach.ld"):
    fw = tmp_path / "firmware"
    fw.mkdir()
    (fw / "mach.c").write_text(c, "utf-8")
    if ld is not None:
        (fw / ten_ld).write_text(ld, "utf-8")
    return tmp_path, fw


# =========================================================== bảng chuỗi công cụ
def test_armv7e_m_dich_cho_cortex_m4_khong_phai_m7():
    """M4 chạy được trên M7; ngược lại thì không. Chọn phía sai-thì-chậm."""
    assert TC.CHUOI_CONG_CU["armv7e-m"]["cpu"] == "cortex-m4"
    assert TC.CHUOI_CONG_CU["armv7e-m"]["float"] == "soft"


def test_moi_isa_arm_deu_co_objcopy():
    """Không có objcopy thì không có .bin, và bo nạp kiểu ổ đĩa không nạp được gì."""
    for isa in ("armv6-m", "armv7-m", "armv7e-m"):
        assert TC.CHUOI_CONG_CU[isa]["objcopy"] == "arm-none-eabi-objcopy"


def test_duong_libc_khong_co_gcc_thi_tra_rong():
    assert TC.duong_libc("", "cortex-m4") == ""
    assert TC.duong_libc("khong-co-lenh-nay-dau", "cortex-m4") == ""


# =========================================================== từ chối khi thiếu dữ kiện
def test_khong_co_linker_script_thi_tu_choi_chu_khong_tu_sinh(tmp_path):
    goc, fw = _du_an(tmp_path, ld=None)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    assert not kq.dat
    assert "linker script" in kq.vi_sao_khong_dat
    assert "không tự sinh" in kq.vi_sao_khong_dat


def test_hai_linker_script_thi_khong_doan_dung_cai_nao(tmp_path):
    goc, fw = _du_an(tmp_path)
    (fw / "khac.ld").write_text(LD, "utf-8")
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    assert not kq.dat and "Không đoán dùng cái nào" in kq.vi_sao_khong_dat


def test_khong_co_tep_nguon_thi_noi_ro(tmp_path):
    fw = tmp_path / "firmware"
    fw.mkdir()
    (fw / "mach.ld").write_text(LD, "utf-8")
    kq = TC.bien_dich(goc=tmp_path, sketch=fw, isa="armv7e-m")
    assert not kq.dat and "Không có tệp .c/.s" in kq.vi_sao_khong_dat


def test_fpu_sai_cho_cpu_thi_tu_choi_truoc_khi_dich(tmp_path):
    """`fpv5-d16` là FPU của M7. Đặt nó cho M4 thì chương trình hard-fault trên bo thật."""
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m", fpu="fpv5-d16")
    assert not kq.dat
    assert "không hợp lệ cho cortex-m4" in kq.vi_sao_khong_dat
    assert "fpv4-sp-d16" in kq.vi_sao_khong_dat          # nói luôn cái đúng là gì


def test_isa_chua_biet_thi_khong_chon_kien_truc_gan_giong(tmp_path):
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="xtensa-lx6")
    assert not kq.dat and "Chưa biết biên dịch cho kiến trúc" in kq.vi_sao_khong_dat


# =========================================================== biên dịch thật
@can_arm
def test_dich_that_ra_elf_bin_hex_va_kich_thuoc_dung(tmp_path):
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m",
                      flash_toi_da=2 * 1024 * 1024, sram_toi_da=324 * 1024)
    assert kq.dat, kq.vi_sao_khong_dat + "\n" + kq.nguyen_van[-800:]
    build = goc / ".eide" / "build"
    assert (build / "mach.elf").exists()
    assert (build / "mach.bin").exists() and (build / "mach.hex").exists()
    assert (build / "mach.map").exists()
    assert kq.tep_bin.endswith("mach.bin")

    # Flash phải bằng ĐÚNG số byte của ảnh nạp, không lẫn section gỡ lỗi.
    assert kq.flash == (build / "mach.bin").stat().st_size
    # Và phải khớp với `size -B` của binutils — một phép đo độc lập.
    r = subprocess.run([shutil.which("arm-none-eabi-size") or "arm-none-eabi-size",
                        "-B", str(build / "mach.elf")], capture_output=True, text=True)
    so = [int(x) for x in r.stdout.splitlines()[1].split()[:3]]
    assert kq.flash == so[0] + so[1]          # text + data
    assert kq.sram == so[1] + so[2]           # data + bss
    assert ".debug_info" not in {k for k in kq.section if k in ("",)}
    assert kq.section[".isr_vector"] == 8


@can_arm
def test_section_go_loi_khong_duoc_tinh_vao_flash(tmp_path):
    """`.debug_*` nặng hơn cả firmware — tính vào Flash là báo tràn cho một firmware 24 byte."""
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    assert kq.dat
    go_loi = sum(v for k, v in kq.section.items() if k.startswith(".debug"))
    assert go_loi > kq.flash          # đúng là chúng to hơn — nên phép loại trừ có ý nghĩa
    assert kq.flash < 1000


@can_arm
def test_bin_bat_dau_bang_stack_pointer_va_reset_vector(tmp_path):
    """Hai từ đầu của ảnh nạp là hợp đồng với phần cứng Cortex-M — kiểm được bằng byte."""
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    assert kq.dat
    b = (goc / ".eide" / "build" / "mach.bin").read_bytes()
    sp = int.from_bytes(b[0:4], "little")
    reset = int.from_bytes(b[4:8], "little")
    assert sp == 0x20000000 + 320 * 1024        # đỉnh RAM như linker script khai
    assert 0x08000000 <= reset < 0x08200000     # trong vùng Flash
    assert reset & 1                            # bit Thumb, nếu thiếu thì chip hard-fault


@can_arm
def test_thieu_libc_thi_khai_ra_chu_khong_im(tmp_path):
    """Máy này không có newlib. Điều đó phải hiện thành một cờ, không phải `cannot find -lc`."""
    goc, fw = _du_an(tmp_path)
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    co_libc = bool(TC.duong_libc(shutil.which("arm-none-eabi-gcc") or "", "cortex-m4"))
    assert kq.thieu_libc is (not co_libc)
    assert ("-nostdlib" in kq.lenh) is (not co_libc)


@can_arm
def test_env_check_khai_newlib_thieu(tmp_path):
    kq = TC.kiem_moi_truong("armv7e-m")
    ten = {c["ten"] for c in kq["cong_cu"]}
    assert "newlib (libc cho ARM)" in ten
    nl = next(c for c in kq["cong_cu"] if c["ten"].startswith("newlib"))
    assert nl["bat_buoc"] is False and nl["cach_cai"]


# ============================== include: mã của hãng mang theo #include tương đối
def test_moi_thu_muc_con_co_header_deu_duoc_I(tmp_path):
    """Ca thật trên bo STM32F469.

        stm32469i_discovery_lcd.c:58: #include "../../../Utilities/Fonts/fonts.h"

    Ba cấp `..` ấy chỉ đúng khi tệp nằm đúng chỗ trong cây của ST. Một `-I` duy nhất vào thư
    mục gốc không đủ, và người đọc lỗi sẽ đi tìm một `fonts.h` bị thiếu — trong khi tệp ấy có
    thật và nằm ngay trong dự án.
    """
    fw = tmp_path / "firmware"
    (fw / "Drivers" / "BSP" / "Bo").mkdir(parents=True)
    (fw / "Utilities" / "Fonts").mkdir(parents=True)
    (fw / "Drivers" / "BSP" / "Bo" / "bsp.h").write_text("#define X 1\n", "utf-8")
    (fw / "Utilities" / "Fonts" / "fonts.h").write_text("#define F 1\n", "utf-8")
    (fw / "mach.c").write_text("int main(void){return 0;}\n", "utf-8")

    duong = TC._duong_include(fw)
    assert f"-I{fw}" in duong
    assert f"-I{fw / 'Drivers' / 'BSP' / 'Bo'}" in duong
    assert f"-I{fw / 'Utilities' / 'Fonts'}" in duong
    # Thư mục KHÔNG có header thì không cần -I.
    assert not any("Drivers'" in d and d.endswith("Drivers") for d in duong)


@can_arm
def test_dich_duoc_khi_header_nam_o_thu_muc_con(tmp_path):
    """Kiểm bằng trình biên dịch thật, không chỉ bằng danh sách cờ."""
    goc, fw = _du_an(tmp_path, c="")
    (fw / "mach.c").unlink()
    (fw / "inc" / "sau").mkdir(parents=True)
    (fw / "inc" / "sau" / "cau_hinh.h").write_text("#define GIA_TRI 7\n", "utf-8")
    (fw / "mach.c").write_text(
        "#include <stdint.h>\n"
        '#include "cau_hinh.h"\n'
        "extern uint32_t _estack;\n"
        "void Reset_Handler(void);\n"
        "static volatile uint32_t d;\n"
        '__attribute__((section(".isr_vector"), used))\n'
        "uint32_t const v[2] = { (uint32_t)&_estack, (uint32_t)Reset_Handler };\n"
        "void Reset_Handler(void) { for(;;) d += GIA_TRI; }\n", "utf-8")
    kq = TC.bien_dich(goc=goc, sketch=fw, isa="armv7e-m")
    assert kq.dat, kq.vi_sao_khong_dat + "\n" + kq.nguyen_van[-600:]


def test_tep_don_le_thi_I_vao_thu_muc_chua_no(tmp_path):
    p = tmp_path / "mach.c"
    p.write_text("int main(void){return 0;}\n", "utf-8")
    assert TC._duong_include(p) == [f"-I{tmp_path}"]


# ============================== lỗi FPU phải CHỈ ĐƯỜNG tới tham số `fpu=`
def test_loi_ve_dau_phay_dong_chi_duong_toi_tham_so_fpu():
    """Đo được trên phiên FreeRTOS: port `ARM_CM4F` dừng ở

        #error This port can only be used when the project options are configured to
        enable hardware floating point support.

    Câu ấy đúng, nhưng nó nói về *project options của FreeRTOS* — trong khi thứ phải đổi nằm
    ở **lời gọi `build.compile`**. Tác tử đọc nó rất dễ đi sửa `FreeRTOSConfig.h`, hoặc tệ
    hơn, đổi sang port không-FPU. Cả hai đều sai: STM32F469 **có** FPU.
    """
    from eide.tools.xay_dung import _goi_y_fpu

    class _L:
        def __init__(self, t):
            self.thong_diep, self.vi = t, t

    loi = [_L("#error This port can only be used when the project options are configured "
              "to enable hardware floating point support.")]
    t = _goi_y_fpu(loi, "")
    assert 'fpu="fpv4-sp-d16"' in t
    assert "ĐỪNG sửa cấu hình thư viện" in t and "ĐỪNG đổi sang port không-FPU" in t
    # Nói cả VÌ SAO mặc định là soft — nếu không, lần sau ai đó sẽ đổi mặc định cho tiện.
    assert "hard-fault ở lệnh dấu phẩy động đầu tiên" in t


def test_da_truyen_fpu_roi_thi_KHONG_chi_nham_duong():
    """Đã truyền `fpu=` mà vẫn lỗi thì nguyên nhân nằm chỗ khác. Chỉ nhầm đường ở đây sẽ làm
    tác tử quay lại sửa một thứ vốn đã đúng."""
    from eide.tools.xay_dung import _goi_y_fpu

    class _L:
        def __init__(self, t):
            self.thong_diep, self.vi = t, t

    assert _goi_y_fpu([_L("hardware floating point support")], "fpv4-sp-d16") == ""


def test_loi_khong_lien_quan_thi_im_lang():
    from eide.tools.xay_dung import _goi_y_fpu

    class _L:
        def __init__(self, t):
            self.thong_diep, self.vi = t, t

    assert _goi_y_fpu([_L("undefined reference to `memset'")], "") == ""
