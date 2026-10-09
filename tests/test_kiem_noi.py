# -*- coding: utf-8 -*-
"""M4-13 — kiểm "NỐI" tĩnh sau biên dịch: cơ chế viết đúng mà đường dẫn tới nó đứt.

Tài liệu đánh giá của chính dự án ghi **bảy lần** cùng một hình dạng
(`DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md` §3.1), và ba trong bảy nằm đúng ở bước nối firmware:

| lần | cơ chế **viết đúng** | đường dẫn tới nó |
|---|---|---|
| 5 | `rtos_tick()` | ô vector SysTick trỏ `Default_Handler` |
| 6 | `PendSV_Handler` nối đúng ô vector | không ai đặt `PENDSVSET` |
| 7 | `RTOS_IDLE_PRIORITY` | không ai tạo tác vụ rỗi |

> **Không lần nào có lỗi báo ra.**

Và chúng **biên dịch sạch**: một handler viết sai tên một chữ thì linker giữ ô vector trỏ
`Default_Handler`, rồi `--gc-sections` **xoá hẳn** hàm người viết. Ảnh nạp vào chip không có
mã ấy, mà `build.compile` báo đạt.

Mẫu ở `tests/du-lieu-chung/kiem_noi/` là **đầu ra thật** của `arm-none-eabi-gcc`/`nm`/`objdump`
trên một dự án Cortex-M4 tối giản tái hiện đúng ca #5 — không phải chuỗi tự viết.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

MAU = Path(__file__).parent / "du-lieu-chung" / "kiem_noi"
EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}
co_arm = bool(shutil.which("arm-none-eabi-gcc") and shutil.which("arm-none-eabi-objdump"))
can_arm = pytest.mark.skipif(not co_arm, reason="máy này chưa có chuỗi công cụ ARM")


# ===================================================================== đọc bảng vector
def test_doc_vector_tu_objdump_that():
    """Giải mã `.isr_vector` từ đầu ra `objdump -s` THẬT.

    Mỗi ô 4 byte, little-endian, và bit 0 là **bit Thumb** — không gỡ nó thì mọi địa chỉ lệch
    một, và phép so "ô này có trỏ `Default_Handler` không" trượt hết.
    """
    from eide.build.kiem_noi import doc_vector

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    assert len(v) == 16, len(v)
    assert v[0] == (0, 0x20020000), v[0]          # con trỏ ngăn xếp ban đầu
    assert v[1] == (1, 0x08000048), v[1]          # Reset_Handler, đã gỡ bit Thumb
    assert v[14] == (14, 0x08000040), v[14]       # PendSV_Handler
    assert v[15] == (15, 0x08000046), v[15]       # SysTick → Default_Handler


def test_doc_nm():
    """`nm` → `{tên: (địa chỉ, loại)}`. Giữ LOẠI: `W` (weak) và `T` (strong) nói hai chuyện
    khác nhau, và chính chỗ ấy phân biệt một handler đã nối với một handler còn là alias."""
    from eide.build.kiem_noi import doc_nm

    s = doc_nm((MAU / "nm.txt").read_text("utf-8"))
    assert s["Default_Handler"] == (0x08000046, "T"), s.get("Default_Handler")
    assert s["PendSV_Handler"] == (0x08000040, "T")
    assert s["SysTick_Handler"] == (0x08000046, "W"), s.get("SysTick_Handler")


# ===================================================================== ISR bị bỏ quên
def test_isr_tro_default_handler_bi_bat():
    """TC-M4-13-01 — ca #5 của DANH-GIA, tái hiện bằng dữ liệu thật.

    Ô 15 trỏ đúng địa chỉ `Default_Handler`, trong khi mã người dùng có `SysTick_handler`
    (chữ `h` thường). Hai chữ ấy cách nhau một phím, và hậu quả là `rtos_tick()` không bao giờ
    chạy — mà mọi chặng đều báo đạt.
    """
    from eide.build.kiem_noi import doc_nm, doc_vector, isr_bi_bo_quen

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    s = doc_nm((MAU / "nm.txt").read_text("utf-8"))
    nguon = (MAU / "main.c").read_text("utf-8") + (MAU / "startup.c").read_text("utf-8")

    ra = isr_bi_bo_quen(v, s, nguon)
    ten = {x.ten for x in ra}
    assert "SysTick_Handler" in ten, [(x.ten, x.vi_sao) for x in ra]
    # Và nó phải CHỈ RA cái tên gần giống — đó là thứ biến một cảnh báo thành một việc sửa.
    st = next(x for x in ra if x.ten == "SysTick_Handler")
    assert st.gan_giong == "SysTick_handler", st
    assert st.o == 15 and st.dia_chi == 0x08000046


def test_isr_noi_dung_khong_keu():
    """TC-M4-13-02 — ca âm: `PendSV_Handler` nối đúng thì không được kêu."""
    from eide.build.kiem_noi import doc_nm, doc_vector, isr_bi_bo_quen

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    s = doc_nm((MAU / "nm.txt").read_text("utf-8"))
    nguon = (MAU / "main.c").read_text("utf-8")
    assert "PendSV_Handler" not in {x.ten for x in isr_bi_bo_quen(v, s, nguon)}


def test_isr_khong_co_ten_gan_giong_thi_KHONG_keu():
    """Ca âm quan trọng nhất: một handler **cố ý** để trống phải im lặng.

    Hầu hết ô vector của một dự án thật trỏ `Default_Handler` và đó là **đúng** — không ai
    viết `MemManage_Handler`. Kêu ở đó là kêu mười lăm lần mỗi lần dịch, và lúc ấy cảnh báo
    thật nằm lẫn trong đống ấy.
    """
    from eide.build.kiem_noi import doc_nm, doc_vector, isr_bi_bo_quen

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    s = doc_nm((MAU / "nm.txt").read_text("utf-8"))
    ra = isr_bi_bo_quen(v, s, "/* không có handler nào */")
    assert ra == [], [(x.ten, x.o) for x in ra]


def test_isr_bat_ca_dinh_nghia_STATIC():
    """Lối hỏng thứ hai, cùng hậu quả: handler viết đúng tên nhưng khai `static`.

    Linker không thấy nó, nên ô vector giữ `Default_Handler` — và `nm` không có ký hiệu mạnh
    nào. Khác ca typo ở chỗ tên **khớp hoàn toàn**, nên phép dò tên gần giống phải nhận cả
    trường hợp giống hệt.
    """
    from eide.build.kiem_noi import doc_nm, doc_vector, isr_bi_bo_quen

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    s = doc_nm((MAU / "nm.txt").read_text("utf-8"))
    ra = isr_bi_bo_quen(v, s, "static void SysTick_Handler(void) { rtos_tick(); }\n")
    st = [x for x in ra if x.ten == "SysTick_Handler"]
    assert st and st[0].gan_giong == "SysTick_Handler", [(x.ten, x.gan_giong) for x in ra]


# ===================================================================== hàm bị linker loại
def test_doc_log_gc_sections():
    """TC-M4-13-03 — đọc log `--print-gc-sections` THẬT.

    Dòng thật dài và có đường dẫn tệp tạm của trình biên dịch:
    `arm-none-eabi-ld: removing unused section '.text.SysTick_handler' in file '/var/…/ccJ0Xg4M.o'`
    """
    from eide.build.kiem_noi import ham_bi_loai

    ra = ham_bi_loai((MAU / "gc-sections.log").read_text("utf-8"))
    assert ra == ["SysTick_handler"], ra


def test_ham_bi_loai_bo_vendor_va_section_khong_phai_ham():
    """Hai thứ phải bỏ: tệp trong `vendor/` (kế hoạch cấm quét), và section không phải hàm
    (`.rodata`, `.bss` — bỏ một hằng không dùng là chuyện bình thường, không phải lỗi nối)."""
    from eide.build.kiem_noi import ham_bi_loai

    log = (
        "ld: removing unused section '.text.ham_cua_toi' in file 'firmware/rtos.o'\n"
        "ld: removing unused section '.text.vendor_init' in file 'vendor/hal/hal.o'\n"
        "ld: removing unused section '.rodata.bang_tra' in file 'firmware/rtos.o'\n"
        "ld: removing unused section '.bss.dem' in file 'firmware/rtos.o'\n")
    assert ham_bi_loai(log) == ["ham_cua_toi"], ham_bi_loai(log)


# ===================================================================== hàm chỉ trả hằng
def test_ham_chi_tra_HANG():
    """`target.debug` đã có cảnh báo này — nhưng **chỉ khi chạy trên chip**. Một hàm chưa viết
    xong (`return 0;`) thì nhìn thấy được ngay ở bước dịch, không cần cắm bo."""
    from eide.build.kiem_noi import ham_tra_hang

    d = ("08000010 <lay_nguong>:\n"
         " 8000010:\tf44f 70f0 \tmov.w\tr0, #480\t@ 0x1e0\n"
         " 8000014:\t4770      \tbx\tlr\n"
         "\n"
         "08000020 <tinh_that>:\n"
         " 8000020:\teb00 0040 \tadd.w\tr0, r0, r0, lsl #1\n"
         " 8000024:\t3001      \tadds\tr0, #1\n"
         " 8000026:\t4770      \tbx\tlr\n")
    ra = ham_tra_hang(d)
    assert [x.ten for x in ra] == ["lay_nguong"], [x.ten for x in ra]
    assert ra[0].gia_tri == 480, ra[0]


def test_ham_tra_hang_bo_main_va_handler():
    """`main(){return 0;}` và một handler rỗng có đúng hình dạng ấy, mà cả hai là chuyện
    thường. Kêu chúng lên là kêu ở mọi dự án, và cảnh báo mất nghĩa."""
    from eide.build.kiem_noi import ham_tra_hang

    d = ("08000042 <main>:\n 8000042:\t2000  \tmovs\tr0, #0\n 8000044:\t4770 \tbx\tlr\n\n"
         "08000050 <NMI_Handler>:\n 8000050:\t2000  \tmovs\tr0, #0\n 8000052:\t4770 \tbx\tlr\n")
    assert ham_tra_hang(d) == []


# ===================================================================== kiến trúc khác
def test_kien_truc_KHAC_thi_noi_ro_chu_khong_im():
    """AVR và RISC-V không có `.isr_vector` kiểu Cortex-M. Trả rỗng im lặng ở đó sẽ được đọc
    là *"nối đúng hết"* — đúng cái N6 cấm."""
    from eide.build.kiem_noi import kiem_noi_tu_elf

    kq = kiem_noi_tu_elf(Path("/khong/co/that.elf"), isa="avr8")
    assert kq["ho_tro"] is False
    assert "chưa hỗ trợ" in kq["vi_sao"].lower(), kq["vi_sao"]
    assert kq["isr_bo_quen"] == [] and kq["ham_bi_loai"] == []


def test_thieu_cong_cu_thi_noi_ro(tmp_path):
    """Thiếu `arm-none-eabi-objdump` thì nói rõ, `ho_tro=False`, không đạt giả."""
    from eide.build import kiem_noi as KN

    (tmp_path / "x.elf").write_bytes(b"\x7fELF")
    import unittest.mock as M
    with M.patch.object(KN.shutil, "which", lambda _x: None):
        kq = KN.kiem_noi_tu_elf(tmp_path / "x.elf", isa="arm")
    assert kq["ho_tro"] is False and "objdump" in kq["vi_sao"]


# ===================================================================== công cụ build.wiring
@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-thu")
    return ag, ctx


def test_luoc_do_build_wiring(bo):
    """`core=False` và mô tả ≤ 400 ký tự (N-11)."""
    ag, _ctx = bo
    sp = ag.registry.get("build.wiring")
    assert sp is not None and sp.core is False
    assert len(sp.summary_vi) <= 400, len(sp.summary_vi)
    assert sp.risk == "R1"


def test_build_wiring_chua_bien_dich_thi_tu_choi(bo):
    ag, ctx = bo
    r = ag.registry.run("build.wiring", {"explain": EX}, ctx)
    assert not r.ok and r.error.code == "E4001", r
    assert "build.compile" in (r.error.alternatives or [])


@can_arm
def test_build_wiring_tren_ELF_THAT_trong_repo(bo):
    """TC-M4-13-04 (ca âm, hiện vật THẬT) — ELF FreeRTOS trong repo nối ĐÚNG.

    `du-lieu/stm32f469-freertos/.eide/build/mach.elf` là ảnh thật đã nạp lên bo: ô 14 trỏ
    `PendSV_Handler`, ô 15 trỏ `SysTick_Handler`. Một bộ dò kêu ở đây là một bộ dò không dùng
    được.
    """
    from eide.build.kiem_noi import kiem_noi_tu_elf

    elf = Path(__file__).parents[1] / "du-lieu/stm32f469-freertos/.eide/build/mach.elf"
    if not elf.is_file():
        pytest.skip("không có ELF thật trong repo")
    kq = kiem_noi_tu_elf(elf, isa="arm")
    assert kq["ho_tro"] is True, kq.get("vi_sao")
    assert kq["so_o_vector"] == 16, kq["so_o_vector"]
    assert {x["ten"] for x in kq["isr_bo_quen"]} == set(), kq["isr_bo_quen"]


@pytest.mark.nha_that
@can_arm
def test_build_wiring_tren_ELF_HONG_dung_ca_so_5(bo, tmp_path):
    """TC-M4-13-04 (ca dương) — dựng lại ca #5 bằng chuỗi công cụ THẬT rồi soi.

    Dự án Cortex-M4 tối giản: `SysTick_handler` (chữ `h` thường). Linker giữ ô 15 trỏ
    `Default_Handler` và `--gc-sections` xoá hẳn hàm ấy — **biên dịch sạch**.
    """
    import subprocess

    from eide.build.kiem_noi import kiem_noi_tu_elf

    for t in ("main.c", "startup.c", "link.ld"):
        shutil.copy(MAU / t, tmp_path / t)
    elf = tmp_path / "w.elf"
    r = subprocess.run(
        ["arm-none-eabi-gcc", "-mcpu=cortex-m4", "-mthumb", "-ffreestanding", "-nostdlib",
         "-O1", "-ffunction-sections", "-fdata-sections", "-Wl,--gc-sections",
         "-Wl,--print-gc-sections", "-T", "link.ld", "main.c", "startup.c", "-o", str(elf)],
        cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:400]
    assert "removing unused section '.text.SysTick_handler'" in r.stderr, r.stderr[:400]

    nguon = (tmp_path / "main.c").read_text("utf-8")
    kq = kiem_noi_tu_elf(elf, isa="arm", nguon_chu=nguon, log_link=r.stderr)
    ten = {x["ten"] for x in kq["isr_bo_quen"]}
    assert "SysTick_Handler" in ten, kq["isr_bo_quen"]
    assert "PendSV_Handler" not in ten, kq["isr_bo_quen"]
    assert "SysTick_handler" in kq["ham_bi_loai"], kq["ham_bi_loai"]


# ===================================================================== cờ KIEM_NOI
def test_co_kiem_noi_co_ten_va_mac_dinh_TAT():
    from eide.config import Features

    assert "kiem_noi" in Features.ten_co()
    assert Features().bat("kiem_noi") is False


def test_co_tat_note_build_compile_y_cu(bo, monkeypatch):
    """TC-M4-13-05 — cờ TẮT thì `build.compile` không nói một chữ nào về nối."""
    from eide.build import kiem_noi as KN

    ag, _ctx = bo
    goi: list = []
    monkeypatch.setattr(KN, "kiem_noi_tu_elf", lambda *a, **k: goi.append(a) or {})
    from eide.tools.xay_dung import _note_kiem_noi

    assert _note_kiem_noi(ag.config, ag.config.paths.project_root, "arm", "", "") == ""
    assert goi == [], "cờ TẮT mà vẫn chạy phép kiểm nối"


def test_co_BAT_thi_note_co_phan_NOI(bo, monkeypatch):
    """Mặt còn lại: thiếu nửa này thì một cờ không-bao-giờ-chạy cũng qua được ca trên."""
    from eide.build import kiem_noi as KN
    from eide.config import Features

    ag, _ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_KIEM_NOI", "1")
    ag.config.features = Features.load()
    monkeypatch.setattr(KN, "kiem_noi_tu_elf", lambda *a, **k: {
        "ho_tro": True, "vi_sao": "", "so_o_vector": 16,
        "isr_bo_quen": [{"o": 15, "ten": "SysTick_Handler", "gan_giong": "SysTick_handler",
                         "vi_sao": "x"}],
        "ham_bi_loai": ["SysTick_handler"], "ham_tra_hang": []})
    from eide.tools.xay_dung import _note_kiem_noi

    chu = _note_kiem_noi(ag.config, ag.config.paths.project_root, "arm", "", "")
    assert "SysTick_Handler" in chu and "SysTick_handler" in chu, chu
    assert "ô 15" in chu, chu


def test_co_BAT_ma_kien_truc_khac_thi_noi_RO(bo, monkeypatch):
    """Cờ bật trên AVR thì nói rõ *chưa hỗ trợ*, không im lặng — im lặng đọc thành "nối đúng"."""
    from eide.build import kiem_noi as KN
    from eide.config import Features

    ag, _ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_KIEM_NOI", "1")
    ag.config.features = Features.load()
    monkeypatch.setattr(KN, "kiem_noi_tu_elf", lambda *a, **k: {
        "ho_tro": False, "vi_sao": "chưa hỗ trợ kiến trúc avr8", "so_o_vector": 0,
        "isr_bo_quen": [], "ham_bi_loai": [], "ham_tra_hang": []})
    from eide.tools.xay_dung import _note_kiem_noi

    chu = _note_kiem_noi(ag.config, ag.config.paths.project_root, "avr8", "", "")
    assert "chưa hỗ trợ" in chu.lower(), chu
    assert "KHÔNG" in chu, chu


# ============ tiêu chí: tái hiện ≥3/7 ca của DANH-GIA §3.1 ở bước BUILD
@pytest.mark.nha_that
@can_arm
def test_tai_hien_BA_CA_cua_DANH_GIA(tmp_path):
    """Tiêu chí của nhiệm vụ, đo bằng chuỗi công cụ THẬT — không suy luận.

    Một tệp dựng lại ba hình dạng cùng lúc, rồi đếm xem phép kiểm bắt được mấy:

    * **#3** *"bảng tổng kiểm sinh ra · `main.c` không `#include`"* → `tong_kiem_chuan` không
      ai gọi, linker **xoá hẳn** → `ham_bi_loai`;
    * **#5** *"`rtos_tick()` · ô vector SysTick trỏ `Default_Handler`"* → `SysTick_handler`
      sai một chữ → `isr_bi_bo_quen`;
    * **#7** *"`RTOS_IDLE_PRIORITY` · không ai tạo tác vụ rỗi"* → `vTaskIdle` khai `static` và
      không ai tham chiếu. Chỗ này **trình biên dịch bắt trước linker**:
      `warning: 'vTaskIdle' defined but not used [-Wunused-function]` — tức một cảnh báo ĐÃ CÓ
      mà `build.compile` vốn đã in ra. Ghi đúng như thế thay vì nhận công cho mã mới.

    Hai ca KHÔNG bắt được, và nói ra: **#6** (`PendSV_Handler` nối đúng mà không ai đặt
    `PENDSVSET`) cần phân tích phép ghi thanh ghi — `note_vi` của `build.wiring` tự khai điều
    đó. Còn **#1 · #2 · #4** không phải chuyện nối firmware (thực đơn FPGA, tệp ràng buộc chân,
    một công cụ phía Python).
    """
    import subprocess

    from eide.build.kiem_noi import kiem_noi_tu_elf

    for t in ("startup.c", "link.ld"):
        shutil.copy(MAU / t, tmp_path / t)
    shutil.copy(MAU / "ba-ca-danh-gia.c", tmp_path / "main.c")
    co = ["-mcpu=cortex-m4", "-mthumb", "-ffreestanding", "-O1",
          "-ffunction-sections", "-fdata-sections"]

    # #7 — trình biên dịch bắt, trước cả linker.
    rc = subprocess.run(["arm-none-eabi-gcc", *co, "-Wall", "-Wextra", "-c", "main.c",
                         "-o", "main.o"], cwd=str(tmp_path), capture_output=True, text=True)
    assert "vTaskIdle" in rc.stderr and "not used" in rc.stderr, rc.stderr[:300]

    # #3 và #5 — phép kiểm nối bắt.
    rl = subprocess.run(["arm-none-eabi-gcc", *co, "-nostdlib", "-Wl,--gc-sections",
                         "-Wl,--print-gc-sections", "-T", "link.ld", "main.c", "startup.c",
                         "-o", "w.elf"], cwd=str(tmp_path), capture_output=True, text=True)
    assert rl.returncode == 0, rl.stderr[:400]
    kq = kiem_noi_tu_elf(tmp_path / "w.elf", isa="arm",
                         nguon_chu=(tmp_path / "main.c").read_text("utf-8"),
                         log_link=rl.stderr)
    assert [x["ten"] for x in kq["isr_bo_quen"]] == ["SysTick_Handler"], kq["isr_bo_quen"]
    assert "tong_kiem_chuan" in kq["ham_bi_loai"], kq["ham_bi_loai"]
    assert "SysTick_handler" in kq["ham_bi_loai"], kq["ham_bi_loai"]


def test_note_build_wiring_TU_KHAI_hai_ca_KHONG_bat_duoc(bo, monkeypatch):
    """Phạm vi phải tự khai. Hai trong bảy ca của DANH-GIA §3.1 nằm **ngoài** tầm phép kiểm
    này, và một kết quả "không thấy gì" mà không nói phạm vi sẽ được đọc là *"nối đúng hết"*.
    """
    from eide.build import kiem_noi as KN

    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"\x7fELF")
    ag.store.apply(artefact_id="build:firmware", type="build", op="create", author="test",
                   canonical={"nguyen_van": ""}, explain=EX)
    monkeypatch.setattr(KN, "kiem_noi_tu_elf", lambda *a, **k: {
        "ho_tro": True, "vi_sao": "", "so_o_vector": 16,
        "isr_bo_quen": [], "ham_bi_loai": [], "ham_tra_hang": []})
    r = ag.registry.run("build.wiring", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert "PENDSVSET" in r.data["note_vi"], r.data["note_vi"]
    assert "KHÔNG kiểm được" in r.data["note_vi"], r.data["note_vi"]


# ============ sáu chỗ phép phá chỉ ra là ca kiểm CHƯA chạm tới
def test_khong_co_Default_Handler_thi_tra_RONG():
    """Không có ký hiệu `Default_Handler` thì không có mốc nào để so — trả rỗng, đừng lấy 0
    làm mốc. Một ảnh không có `Default_Handler` là một ảnh dùng startup code khác, và đoán
    mốc ở đó là đoán."""
    from eide.build.kiem_noi import doc_vector, isr_bi_bo_quen

    v = doc_vector((MAU / "vector.objdump.txt").read_text("utf-8"))
    nguon = (MAU / "main.c").read_text("utf-8")
    assert isr_bi_bo_quen(v, {"SysTick_Handler": (0x08000046, "W")}, nguon) == []


def test_o_DU_TRU_tro_Default_Handler_cung_khong_keu():
    """Ô 7–10 và 13 của bảng vector Cortex-M là **dự trữ** — chúng không có tên handler nào,
    nên kể cả khi một script liên kết lạ cho chúng trỏ `Default_Handler` thì cũng không có gì
    để nối."""
    from eide.build.kiem_noi import isr_bi_bo_quen

    dh = 0x08000046
    v = [(i, dh if i in (7, 8, 9, 10, 13) else 0) for i in range(16)]
    ra = isr_bi_bo_quen(v, {"Default_Handler": (dh, "T")},
                        "void SysTick_Handler(void){} void Reserved7_Handler(void){}")
    assert ra == [], [(x.o, x.ten) for x in ra]


def test_ham_bi_loai_BO_TRUNG():
    """Cùng một hàm bị loại ở hai đơn vị dịch thì vẫn là **một** phát hiện. Hai dòng cho một
    chỗ làm con số phát hiện phình lên mà không thêm thông tin nào."""
    from eide.build.kiem_noi import ham_bi_loai

    log = ("ld: removing unused section '.text.ham_x' in file 'firmware/a.o'\n"
           "ld: removing unused section '.text.ham_x' in file 'firmware/b.o'\n")
    assert ham_bi_loai(log) == ["ham_x"], ham_bi_loai(log)


def test_ham_tra_hang_KHONG_nhan_ham_co_NHIEU_lenh():
    """`movs r0,#5` rồi còn tính tiếp thì **không** phải "chỉ trả hằng".

    Phép phá chỉ ra rằng ca cũ không đo được chuyện này: hàm đối chứng của nó mở đầu bằng
    `add.w`, nên một phép kiểm "lệnh CUỐI là `bx lr`" cũng loại nó — ca kiểm xanh mà không
    phân biệt được "đúng hai lệnh" với "từ hai lệnh trở lên".
    """
    from eide.build.kiem_noi import ham_tra_hang

    d = ("08000010 <co_tinh_them>:\n"
         " 8000010:\t2005      \tmovs\tr0, #5\n"
         " 8000012:\t3001      \tadds\tr0, #1\n"
         " 8000014:\t4770      \tbx\tlr\n")
    assert ham_tra_hang(d) == [], [(x.ten, x.gia_tri) for x in ham_tra_hang(d)]


def test_ham_tra_hang_DOI_lenh_ve_phai_la_bx_lr():
    """Hai lệnh mà lệnh thứ hai là một phép nhảy thì hàm chưa về — nó rơi vào hàm khác."""
    from eide.build.kiem_noi import ham_tra_hang

    d = ("08000010 <nhay_di>:\n"
         " 8000010:\t2005      \tmovs\tr0, #5\n"
         " 8000012:\te7fd      \tb.n\t8000010 <nhay_di>\n")
    assert ham_tra_hang(d) == []


@can_arm
def test_anh_KHONG_CO_isr_vector_thi_noi_ro(bo):
    """Một ảnh không có section `.isr_vector` — ví dụ ELF của AVR — phải cho `ho_tro=False`.

    Trả `ho_tro=True` với bảng rỗng ở đó sẽ được đọc là *"16 ô, không ô nào sai"*: một ô xanh
    giả dựng từ một bảng không tồn tại.
    """
    from eide.build.kiem_noi import kiem_noi_tu_elf

    elf = Path(__file__).parents[1] / "du-lieu/robot-canbang/.eide/build/firmware.ino.elf"
    if not elf.is_file():
        pytest.skip("không có ELF AVR thật trong repo")
    kq = kiem_noi_tu_elf(elf, isa="arm")
    assert kq["ho_tro"] is False, kq
    assert "isr_vector" in kq["vi_sao"], kq["vi_sao"]


def test_build_wiring_GHI_hien_vat(bo, monkeypatch):
    """Ghi `analysis:wiring` vào kho. Một phép đo không vào kho thì bằng chưa đo (DEV-341):
    lượt sau không ai biết nó từng chạy, và không bề mặt nào hiện được nó."""
    from eide.build import kiem_noi as KN

    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / ".eide" / "build").mkdir(parents=True, exist_ok=True)
    (goc / ".eide" / "build" / "mach.elf").write_bytes(b"\x7fELF")
    ag.store.apply(artefact_id="build:firmware", type="build", op="create", author="test",
                   canonical={"nguyen_van": ""}, explain=EX)
    monkeypatch.setattr(KN, "kiem_noi_tu_elf", lambda *a, **k: {
        "ho_tro": True, "vi_sao": "", "so_o_vector": 16,
        "isr_bo_quen": [{"o": 15, "ten": "SysTick_Handler", "gan_giong": "SysTick_handler",
                         "vi_sao": "x"}],
        "ham_bi_loai": [], "ham_tra_hang": []})
    r = ag.registry.run("build.wiring", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    a = ag.store.get("analysis:wiring")
    assert a is not None and a["type"] == "analysis", a
    assert a["canonical"]["isr_bo_quen"][0]["ten"] == "SysTick_Handler"
