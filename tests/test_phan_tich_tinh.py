# -*- coding: utf-8 -*-
"""M2-09 — phân tích tĩnh chiều sâu: đồ thị gọi hàm, ngăn xếp, luật ngữ cảnh ngắt.

`phan_tich_ma.py` nói thẳng trong docstring của chính nó: *"Không phân tích ngữ nghĩa, không
dựng đồ thị gọi hàm đúng nghĩa"*. Và chuỗi biên dịch có `-Wall -Wextra` mà **không** có
`-fstack-usage`, `-fcallgraph-info`, `-fanalyzer`. Nên ba câu hỏi mà một người làm nhúng hỏi
đầu tiên đều không có ai trả lời:

* *"ngăn xếp sâu nhất bao nhiêu byte"* — RAM của ATmega328P là 2 048 byte, và một chuỗi gọi
  sâu làm tràn ngăn xếp **không có lỗi nào kêu lên**: nó ghi lên biến toàn cục rồi chương
  trình chạy sai ở một chỗ khác;
* *"hàm nào gọi hàm nào"*;
* *"trong hàm ngắt có phép chia, `printf`, hay `_delay_ms` không"* — ba thứ làm một ISR 50 kHz
  trượt deadline, và cả ba đều biên dịch sạch.

Bộ này đo trên **mẫu thật** ở `tests/du-lieu-chung/phan_tich_tinh/`: `.su` và `.ci` sinh bằng
`arm-none-eabi-gcc 16.2.0` và `.su` của Apple clang, không phải chuỗi tự viết.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

MAU = Path(__file__).parent / "du-lieu-chung" / "phan_tich_tinh"
EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}


# ===================================================================== đọc .su
def test_doc_su():
    """TC-M2-09-01 — và nó đo được **hai** định dạng, vì hai trình biên dịch khác nhau.

    `arm-none-eabi-gcc` ghi `tep.c:DÒNG:CỘT:ham`, Apple clang ghi `tep.c:DÒNG:ham` — **thiếu
    cột**. Kế hoạch chỉ nêu dạng GCC; đọc một dạng thôi thì `code.static` không chạy nổi trên
    máy chủ, mà máy chủ là nơi `test.run` dịch mọi thứ.
    """
    from eide.build.phan_tich_tinh import doc_su

    gcc = doc_su((MAU / "arm-gcc.su").read_text("utf-8"))
    assert gcc["tinh"][0] == 144 and gcc["tinh"][1] == "static", gcc
    assert gcc["loc"][0] == 80 and gcc["bo_dem_phu"][0] == 48
    assert gcc["main"][0] == 8
    assert set(gcc) == {"bo_dem_phu", "loc", "tinh", "main"}, set(gcc)

    cl = doc_su((MAU / "clang.su").read_text("utf-8"))
    assert set(cl) == set(gcc), (set(cl), set(gcc))
    assert cl["tinh"][0] == 320, cl          # clang cấp phát rộng tay hơn, đúng như đo được


def test_doc_su_bo_dong_rac():
    """Dòng không đúng khuôn thì bỏ, không đoán. Một con số ngăn xếp đoán ra còn tệ hơn không
    có — nó đi vào phép so ngân sách RAM."""
    from eide.build.phan_tich_tinh import doc_su

    ra = doc_su("rac\nt.c:1:f\tKHONG-PHAI-SO\tstatic\n\nt.c:2:g\t16\tstatic\n")
    assert ra == {"g": (16, "static")}, ra


def test_doc_su_kieu_dynamic_giu_lai():
    """`dynamic` và `bounded` là ba kiểu GCC khai, và chúng nói ba chuyện khác nhau: một hàm
    `dynamic` thì con số kia **không phải trần**. Giữ kiểu lại để lớp trên nói đúng."""
    from eide.build.phan_tich_tinh import doc_su

    ra = doc_su("t.c:1:5:f\t16\tdynamic\nt.c:2:5:g\t32\tdynamic,bounded\n")
    assert ra["f"] == (16, "dynamic") and ra["g"][1] == "dynamic,bounded", ra


# ===================================================================== đọc .ci
def test_doc_ci():
    """TC-M2-09-01 (phần đồ thị) — tên nút trong VCG **không nhất quán**.

    Đo được trên đầu ra thật: hàm `static` thành `"m2.c:loc"` (có tiền tố tệp), hàm `extern`
    thành `"tinh"` (trần). Không chuẩn hoá thì `tinh → loc` thành một cung giữa hai cái tên
    không khớp bất kỳ khoá nào của `.su`, và đồ thị rời ra từng mảnh — im lặng.
    """
    from eide.build.phan_tich_tinh import doc_ci

    cg = doc_ci((MAU / "arm-gcc.ci").read_text("utf-8"))
    assert cg["main"] == {"tinh"}, cg
    assert cg["tinh"] == {"loc"}, cg
    assert cg["loc"] == {"bo_dem_phu"}, cg
    # Hàm của thư viện (`__aeabi_idiv`) vẫn là một cung thật — phép chia 32 bit trên Cortex-M0
    # gọi hàm, và hàm ấy TIÊU NGĂN XẾP.
    assert "__aeabi_idiv" in cg["bo_dem_phu"], cg


def test_doc_ci_rong_thi_rong_chu_khong_no():
    from eide.build.phan_tich_tinh import doc_ci

    assert doc_ci("") == {}
    assert doc_ci("graph: { title: \"x\"\n}\n") == {}


# ===================================================================== ngăn xếp
def test_ngan_xep_theo_chuoi_goi():
    """TC-M2-09-02 — cộng dồn theo chuỗi gọi, và trả CẢ chuỗi.

    Một con số 96 mà không nói đi qua đâu thì không sửa được. Chuỗi là thứ chỉ ra chỗ cắt.
    """
    from eide.build.phan_tich_tinh import ngan_xep_toi_da

    su = {"main": (16, "static"), "a": (32, "static"), "b": (48, "static")}
    cg = {"main": {"a"}, "a": {"b"}}
    kq = ngan_xep_toi_da(su, cg, "main")
    assert kq.byte == 96, kq
    assert kq.chuoi == ["main", "a", "b"], kq
    assert kq.de_quy is False and kq.thieu == []


def test_ngan_xep_chon_nhanh_SAU_NHAT():
    """Hai nhánh thì lấy nhánh tốn nhất — trần là trần, không phải trung bình."""
    from eide.build.phan_tich_tinh import ngan_xep_toi_da

    # Nhánh SÂU phải đứng SAU theo thứ tự chữ (`z` > `a`): nếu nó đứng trước thì một phép
    # "lấy nhánh đầu tiên" cũng ra đúng, và ca kiểm không phân biệt được hai cái.
    su = {"main": (8, "static"), "a": (10, "static"), "z": (100, "static"),
          "c": (10, "static")}
    kq = ngan_xep_toi_da(su, {"main": {"a", "z"}, "a": {"c"}}, "main")
    assert kq.byte == 108 and kq.chuoi == ["main", "z"], kq


def test_de_quy_thi_noi_khong_chan_duoc():
    """TC-M2-09-03 — đệ quy thì **không có trần**, và phải nói ra thế.

    Trả một con số cho một chuỗi gọi đệ quy là trả một lời nói dối có đơn vị byte: nó trông
    như một trần, và người đọc sẽ đem nó so với RAM.
    """
    from eide.build.phan_tich_tinh import ngan_xep_toi_da

    kq = ngan_xep_toi_da({"a": (32, "static")}, {"a": {"a"}}, "a")
    assert kq.de_quy is True
    assert "a" in kq.vong, kq.vong
    kq2 = ngan_xep_toi_da({"x": (8, "static"), "y": (8, "static")},
                          {"x": {"y"}, "y": {"x"}}, "x")
    assert kq2.de_quy is True


def test_ham_KHONG_CO_trong_su_thi_khai_THIEU():
    """Hàm thư viện (`__aeabi_idiv`, `memcpy`) không có trong `.su` của ta — ngăn xếp của nó
    **không đo được**, và con số tổng vì thế là một **chặn dưới**, không phải trần.

    Im lặng coi nó bằng 0 là biến một chặn dưới thành một trần. Đó đúng là kiểu ô xanh giả mà
    cả dự án này đi vá: một con số hợp lý, sai, và không có gì kêu lên.
    """
    from eide.build.phan_tich_tinh import ngan_xep_toi_da

    kq = ngan_xep_toi_da({"f": (48, "static")}, {"f": {"__aeabi_idiv"}}, "f")
    assert kq.byte == 48
    assert kq.thieu == ["__aeabi_idiv"], kq.thieu
    assert kq.la_chan_duoi is True, "có hàm không đo được thì đây là chặn DƯỚI"


def test_goc_khong_co_thi_noi_ro():
    from eide.build.phan_tich_tinh import ngan_xep_toi_da

    kq = ngan_xep_toi_da({"f": (8, "static")}, {}, "khong_co_ham_nay")
    assert kq.byte == 0 and kq.thieu == ["khong_co_ham_nay"]
    assert kq.la_chan_duoi is True


# ===================================================================== luật ISR
ISR_XAU = """
#include <avr/interrupt.h>
unsigned long dem;
static long chia(long a, long b){ return a / b; }
static void cham(void){ _delay_ms(1); }
ISR(TIMER2_COMPA_vect) {
    float g = 1.5f;
    dem = dem + (unsigned long)chia(7, 3);
    cham();
    printf("dem=%lu\\n", dem);
}
int main(void){ dem = 0; for(;;){} }
"""

ISR_SACH = """
#include <avr/interrupt.h>
volatile unsigned short dem;
ISR(TIMER2_COMPA_vect) {
    dem++;
    unsigned short x = dem;
    x = x >> 2;
    (void)x;
}
int main(void){ dem = 0; for(;;){} }
"""


def test_luat_isr_bat_phep_chia_va_delay():
    """TC-M2-09-04 — ba thứ làm một ISR 50 kHz trượt deadline, và cả ba biên dịch sạch.

    Phép chia số nguyên 32 bit trên Cortex-M0 gọi `__aeabi_idiv` (hàng chục chu kỳ và tiêu
    ngăn xếp); `_delay_ms` chặn hẳn; `printf` kéo cả bộ định dạng vào ngữ cảnh ngắt.
    """
    from eide.build.phan_tich_tinh import luat_isr

    cg = {"TIMER2_COMPA_vect": {"chia", "cham"}, "cham": set(), "chia": set()}
    vp = luat_isr(ISR_XAU, cg, "TIMER2_COMPA_vect")
    loai = {v.loai for v in vp}
    assert "so_thuc" in loai and "phep_chia" in loai and "ham_chan" in loai, loai
    assert all(v.dong > 0 for v in vp), [(v.loai, v.dong) for v in vp]
    # Mỗi vi phạm phải chỉ ĐÚNG dòng — một cảnh báo không có số dòng là một cảnh báo phải đi
    # tìm, và trên một tệp 400 dòng thì nó không được đọc.
    chia = next(v for v in vp if v.loai == "phep_chia")
    assert "a / b" in ISR_XAU.splitlines()[chia.dong - 1], ISR_XAU.splitlines()[chia.dong - 1]


def test_luat_isr_bat_bien_toan_cuc_khong_volatile():
    """`dem` ghi ở cả ISR lẫn `main` mà **không** `volatile`: trình biên dịch được phép giữ
    nó trong thanh ghi, và vòng `for(;;)` của `main` sẽ không bao giờ thấy ISR đổi nó.

    Đây là lỗi kinh điển nhất của lập trình nhúng, và nó **biên dịch sạch**.
    """
    from eide.build.phan_tich_tinh import luat_isr

    vp = luat_isr(ISR_XAU, {"TIMER2_COMPA_vect": set()}, "TIMER2_COMPA_vect")
    v = [x for x in vp if x.loai == "thieu_volatile"]
    assert v and v[0].ten == "dem", vp
    assert v[0].dong > 0


def test_isr_sach_khong_keu():
    """TC-M2-09-05 — ca âm. Một bộ dò kêu quá tay sẽ thành máy báo động giả trong một buổi
    chiều, và lúc ấy nó bị bỏ qua kể cả lần nó đúng."""
    from eide.build.phan_tich_tinh import luat_isr

    vp = luat_isr(ISR_SACH, {"TIMER2_COMPA_vect": set()}, "TIMER2_COMPA_vect")
    assert vp == [], [(v.loai, v.dong, v.ten) for v in vp]


def test_phep_chia_cho_HANG_khong_tinh_la_vi_pham():
    """Chia cho một **hằng** là phép dịch bit mà trình biên dịch tự làm — không gọi hàm, không
    tốn gì. Kêu ở đó là kêu oan, và kêu oan làm người đọc bỏ qua cả danh sách."""
    from eide.build.phan_tich_tinh import luat_isr

    chu = ("volatile int dem;\nISR(X_vect){ int y = dem / 4; dem = y % 8; (void)y; }\n")
    assert [v for v in luat_isr(chu, {"X_vect": set()}, "X_vect")
            if v.loai == "phep_chia"] == []


def test_luat_isr_chi_soi_ham_REACHABLE_tu_ISR():
    """Chỉ soi các hàm ISR **gọi tới được**. Một `printf` trong một hàm chỉ `main` gọi thì
    không phải lỗi của ngữ cảnh ngắt — và báo nó lên là trộn hai chuyện."""
    from eide.build.phan_tich_tinh import luat_isr

    chu = ("volatile int dem;\n"
           "static void chi_main_goi(void){ printf(\"x\"); }\n"
           "ISR(X_vect){ dem++; }\n"
           "int main(void){ chi_main_goi(); for(;;){} }\n")
    vp = luat_isr(chu, {"X_vect": set(), "chi_main_goi": set()}, "X_vect")
    assert vp == [], [(v.loai, v.dong) for v in vp]

    # Còn khi ISR GỌI nó thì phải báo, và báo kèm tên hàm trung gian.
    vp2 = luat_isr(chu, {"X_vect": {"chi_main_goi"}, "chi_main_goi": set()}, "X_vect")
    assert any(v.loai == "ham_chan" for v in vp2), vp2
    assert any(v.ham == "chi_main_goi" for v in vp2), [(v.loai, v.ham) for v in vp2]


# ===================================================================== chạy thật
co_cc = bool(shutil.which("cc") or shutil.which("gcc") or shutil.which("clang"))


def test_thieu_trinh_bien_dich_thi_noi_ro(du_an, monkeypatch):
    """TC-M2-09-06 — thiếu công cụ thì NÓI RÕ, `ok` vẫn True, và không đạt giả.

    Một phép phân tích trả `{}` vì thiếu trình biên dịch mà không nói gì sẽ được đọc là
    *"không có vi phạm nào"* — đúng cái N6 cấm.
    """
    from eide.build import phan_tich_tinh as PT

    (du_an / "firmware").mkdir(exist_ok=True)
    (du_an / "firmware" / "a.c").write_text("int f(void){return 1;}\n", "utf-8")
    monkeypatch.setattr(PT.shutil, "which", lambda _x: None)
    kq = PT.chay_phan_tich(du_an, [du_an / "firmware" / "a.c"])
    assert kq["chay_duoc"] is False
    assert "không chạy được" in kq["vi_sao"].lower(), kq["vi_sao"]
    assert kq["ham"] == {} and kq["vi_pham"] == []


@pytest.mark.skipif(not co_cc, reason="máy này không có trình biên dịch C")
def test_chay_that_tren_may_chu(du_an):
    """Chạy `-fstack-usage` thật. Clang KHÔNG có `-fcallgraph-info`, nên đồ thị gọi hàm
    không dựng được — và phải NÓI RA điều đó, không trả một đồ thị rỗng.

    Đo được 09/10/2026: `clang: error: unknown argument: '-fcallgraph-info=su'`.
    """
    from eide.build import phan_tich_tinh as PT

    (du_an / "firmware").mkdir(exist_ok=True)
    shutil.copy(MAU / "mau.c", du_an / "firmware" / "mau.c")
    kq = PT.chay_phan_tich(du_an, [du_an / "firmware" / "mau.c"])
    assert kq["chay_duoc"] is True, kq.get("vi_sao")
    assert set(kq["ham"]) >= {"tinh", "loc", "bo_dem_phu", "main"}, kq["ham"]
    assert kq["ham"]["tinh"][0] > 0
    if not kq["co_do_thi"]:
        assert "callgraph" in kq["vi_sao"].lower() or "đồ thị" in kq["vi_sao"].lower(), kq


@pytest.mark.nha_that
@pytest.mark.skipif(not shutil.which("arm-none-eabi-gcc"),
                    reason="máy này chưa có arm-none-eabi-gcc")
def test_chay_that_co_DO_THI_voi_gcc(du_an):
    """GCC thật thì có cả `.su` lẫn `.ci`, nên ngăn xếp theo chuỗi gọi đo được."""
    from eide.build import phan_tich_tinh as PT

    (du_an / "firmware").mkdir(exist_ok=True)
    shutil.copy(MAU / "mau.c", du_an / "firmware" / "mau.c")
    kq = PT.chay_phan_tich(du_an, [du_an / "firmware" / "mau.c"],
                           cc="arm-none-eabi-gcc", them_co=["-ffreestanding"])
    assert kq["chay_duoc"] and kq["co_do_thi"], kq.get("vi_sao")
    assert kq["do_thi"]["main"] == {"tinh"}, kq["do_thi"]
    nx = kq["ngan_xep"]["main"]
    assert nx["byte"] >= 144 + 80 + 48, nx


# ===================================================================== công cụ code.static
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


def test_luoc_do_code_static(bo):
    """`core=False` (chỉ hiện sau `tool.search`) và mô tả ≤ 400 ký tự (N-11)."""
    ag, _ctx = bo
    sp = ag.registry.get("code.static")
    assert sp is not None and sp.core is False
    assert len(sp.summary_vi) <= 400, len(sp.summary_vi)
    assert sp.risk == "R1", sp.risk


def test_code_static_khong_co_nguon_thi_tu_choi(bo):
    ag, ctx = bo
    r = ag.registry.run("code.static", {"explain": EX}, ctx)
    assert not r.ok and r.error.code == "E4011", r


@pytest.mark.skipif(not co_cc, reason="máy này không có trình biên dịch C")
def test_code_static_ghi_hien_vat_va_gon(bo):
    """Ghi artefact `analysis:static`, và kết quả vào ngữ cảnh phải GỌN: tối đa 20 phát hiện,
    mỗi cái có `tep:dong`."""
    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / "firmware").mkdir(exist_ok=True)
    shutil.copy(MAU / "mau.c", goc / "firmware" / "mau.c")
    r = ag.registry.run("code.static", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    a = ag.store.get("analysis:static")
    assert a is not None and a["type"] == "analysis"
    assert len(r.data["vi_pham"]) <= 20
    assert r.data["so_ham"] >= 4, r.data
    assert "note_vi" in r.data


@pytest.mark.skipif(not co_cc, reason="máy này không có trình biên dịch C")
def test_code_static_KHONG_lam_hong_anh_nap_chip(bo):
    """Phân tích dịch vào `.eide/build/tinh/`, KHÔNG chạm ảnh nạp chip.

    Kế hoạch cấm đúng chỗ này: đổi cờ biên dịch của `build.compile` là đổi chính cái ảnh sẽ
    nạp vào chip — và một phép phân tích không được phép làm thế.
    """
    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / "firmware").mkdir(exist_ok=True)
    shutil.copy(MAU / "mau.c", goc / "firmware" / "mau.c")
    truoc = {p: p.read_bytes() for p in (goc / "firmware").rglob("*") if p.is_file()}
    ag.registry.run("code.static", {"explain": EX}, ctx)
    sau = {p: p.read_bytes() for p in (goc / "firmware").rglob("*") if p.is_file()}
    assert truoc == sau, "phép phân tích đã chạm tệp nguồn"
    assert (goc / ".eide" / "build" / "tinh").exists()


# ===================================================== đính vào code.analyze
def _hien_vat_tinh(ag, *, tep: list[str], stale: bool = False, de_quy: bool = False,
                   co_do_thi: bool = True):
    ag.store.apply(
        artefact_id="analysis:static", type="analysis", op="create", author="test",
        canonical={"chay_duoc": True, "co_do_thi": co_do_thi, "bi_quan": True,
                   "ham": {"main": [8, "static"], "tinh": [144, "static"]},
                   "ngan_xep": {"main": {"byte": 272, "chuoi": ["main", "tinh", "loc"],
                                         "de_quy": de_quy, "vong": ["loc"] if de_quy else [],
                                         "thieu": [], "la_chan_duoi": False}},
                   "vi_pham": [{"loai": "phep_chia", "dong": 12, "ham": "ISR_X"}],
                   "isr": ["TIMER2_COMPA_vect"]},
        explain=EX, deps={"upstream": list(tep)})
    if stale:
        ag.store.mark_stale(["analysis:static"], "cs-0009 (tác tử sửa mã)")


def test_tom_tat_tinh_dinh_vao_ban_phan_tich(bo):
    """Bước 4 của kế hoạch: `code.analyze` đính tóm tắt phân tích tĩnh vào phần DỮ KIỆN.

    Không có nó thì hai phép đo nằm ở hai chỗ, và người đọc bản phân tích trước khi sửa mã
    không thấy con số ngăn xếp — đúng lúc nó đáng đọc nhất.
    """
    from eide.tools.xay_dung import _tom_tat_tinh

    ag, _ctx = bo
    _hien_vat_tinh(ag, tep=["firmware/pid.c"])
    chu = _tom_tat_tinh(ag, ["firmware/pid.c"])
    assert "272 byte" in chu, chu
    assert "main → tinh → loc" in chu, chu
    assert "BI QUAN" in chu
    assert "phep_chia dòng 12" in chu, chu


def test_tom_tat_tinh_NOI_RA_khi_so_da_LOI_THOI(bo):
    """Hiện vật STALE thì nói rõ là số cũ, và chỉ đường chạy lại.

    So **cờ STALE**, không so đồng hồ: `updated_at` của kho có độ phân giải thô nên phép so
    "mới hơn" im lặng sai (DEV-351), còn `deps.upstream` đã khai đúng các tệp nó đo.
    """
    from eide.tools.xay_dung import _tom_tat_tinh

    ag, _ctx = bo
    _hien_vat_tinh(ag, tep=["firmware/pid.c"], stale=True)
    chu = _tom_tat_tinh(ag, ["firmware/pid.c"])
    assert "LỖI THỜI" in chu and "code.static" in chu, chu
    assert "cs-0009" in chu, chu


def test_tom_tat_tinh_IM_khi_chua_do_hoac_do_ma_KHAC(bo):
    """Hai cửa im lặng, và cả hai đúng.

    *"Chưa đo"* khác *"không có vấn đề"*: im lặng ở đây để phần nhận định phía dưới không khai
    gì về ngăn xếp. Và một hiện vật đo **mã khác** thì nói về chuyện khác.
    """
    from eide.tools.xay_dung import _tom_tat_tinh

    ag, _ctx = bo
    assert _tom_tat_tinh(ag, ["firmware/pid.c"]) == ""
    _hien_vat_tinh(ag, tep=["firmware/ui.c"])
    assert _tom_tat_tinh(ag, ["firmware/pid.c"]) == ""


def test_tom_tat_tinh_noi_ra_DE_QUY_va_THIEU_DO_THI(bo):
    """Đệ quy thì không có trần; thiếu đồ thị thì con số chưa cộng dồn. Hai điều kiện ấy đổi
    hẳn nghĩa của con số, nên chúng phải đi cùng nó."""
    from eide.tools.xay_dung import _tom_tat_tinh

    ag, _ctx = bo
    _hien_vat_tinh(ag, tep=["firmware/pid.c"], de_quy=True, co_do_thi=False)
    chu = _tom_tat_tinh(ag, ["firmware/pid.c"])
    assert "đệ quy" in chu.lower() and "KHÔNG chặn trên được" in chu, chu
    assert "chưa cộng dồn" in chu, chu


# ===== hai lỗ nữa, tìm ra khi chạy trên FIRMWARE THẬT trong repo
def test_nhan_dang_ISR_kieu_ARM():
    """Firmware trong repo dùng CẢ HAI lối khai hàm ngắt.

    AVR: macro `ISR(TIMER2_COMPA_vect)` (`du-lieu/robot-sinhvien2/firmware/timer.c`).
    ARM/CMSIS: một hàm thường tên `*_Handler` / `*_IRQHandler`
    (`docs/rtos-tu-viet/firmware-chay-duoc/startup.c`).

    Bắt một lối thôi thì công cụ **mù hẳn** trên một nửa firmware của repo — đo được
    09/10/2026: chạy trên dự án RTOS ARM ra `isr: []` dù nó có hàng chục handler.
    """
    from eide.build.phan_tich_tinh import tim_isr

    chu = ("void SysTick_Handler(void) { dem++; }\n"
           "void TIM2_IRQHandler(void) { x(); }\n"
           "ISR(TIMER2_COMPA_vect) { y(); }\n"
           "void NMI_Handler(void);\n"                                   # chỉ khai báo
           "void HardFault_Handler(void) __attribute__((weak, alias(\"D\")));\n")
    assert tim_isr(chu) == ["SysTick_Handler", "TIM2_IRQHandler", "TIMER2_COMPA_vect"], \
        tim_isr(chu)


def test_do_thi_tu_VAN_BAN_khi_khong_co_ci():
    """Không có `.ci` thì phải dò đồ thị bằng VĂN BẢN.

    Thiếu bước này thì `luat_isr` chỉ soi **thân ISR**, không soi hàm ISR gọi tới — và trên
    máy chủ (clang, không có `-fcallgraph-info`) đó là *mọi lúc*. Đo được trên
    `robot-sinhvien2`: ISR gọi `motor_step_isr()`, và phép soi dừng ngay ở dòng gọi.
    """
    from eide.build.phan_tich_tinh import do_thi_tu_VAN_BAN, luat_isr

    chu = ("volatile int dem;\n"
           "static void cham(void) { _delay_ms(1); }\n"
           "static void sau(void) { cham(); }\n"
           "ISR(T_vect) { dem++; sau(); }\n"
           "int main(void) { for(;;){} }\n")
    cg = do_thi_tu_VAN_BAN(chu)
    assert cg["T_vect"] == {"sau"}, cg
    assert cg["sau"] == {"cham"}, cg
    assert "_delay_ms" in cg["cham"], cg
    # Và luật ISR nay thấy xuyên qua hai lớp hàm.
    vp = luat_isr(chu, cg, "T_vect")
    assert any(v.loai == "ham_chan" and v.ham == "cham" for v in vp), vp


def test_do_thi_VAN_BAN_khong_nham_ten_trong_CHUOI():
    """Tên hàm nằm trong một chuỗi ký tự không phải một lời gọi."""
    from eide.build.phan_tich_tinh import do_thi_tu_VAN_BAN

    chu = ("static void cham(void) { x(); }\n"
           "ISR(T_vect) { log(\"cham(\"); }\n")
    assert "cham" not in do_thi_tu_VAN_BAN(chu).get("T_vect", set())


def test_chay_phan_tich_KHAI_do_thi_la_VAN_BAN(du_an):
    """Đồ thị văn bản phải tự khai là văn bản. Nó mù với lời gọi qua con trỏ hàm và có thể
    kêu thừa — đọc nó như một đồ thị đầy đủ là tin quá một phép dò chuỗi."""
    from eide.build import phan_tich_tinh as PT

    (du_an / "firmware").mkdir(exist_ok=True)
    (du_an / "firmware" / "a.c").write_text(
        "volatile int dem;\n"
        "static void cham(void){ _delay_ms(1); }\n"
        "ISR(T_vect){ dem++; cham(); }\n"
        "int main(void){ for(;;){} }\n", "utf-8")
    kq = PT.chay_phan_tich(du_an, [du_an / "firmware" / "a.c"])
    if not kq["co_do_thi"]:
        assert kq["do_thi_van_ban"] is True, kq
        assert "VĂN BẢN" in kq["vi_sao"], kq["vi_sao"]
        assert any(v["loai"] == "ham_chan" for v in kq["vi_pham"]), kq["vi_pham"]


def test_chu_thich_khong_sinh_canh_bao_OAN():
    """Chú thích phải được bỏ TRƯỚC khi soi toán tử.

    Luật "chia/mod trên biến" khớp `/` rồi một tên biến — mà `/* ghi chú */ x = 1;` có đúng
    hình dạng ấy. Mã firmware của `robot-sinhvien2` chú thích **rất dày** bằng tiếng Việt, nên
    không bỏ chú thích thì phép đo trên nó toàn cảnh báo oan, và một danh sách toàn cảnh báo
    oan thì không ai đọc — kể cả dòng đúng.
    """
    from eide.build.phan_tich_tinh import luat_isr

    chu = ("volatile int dem;\n"
           "ISR(T_vect) {\n"
           "    /* Bang 3.3: tron goc va toc do goc theo tai lieu */ dem++;\n"
           "    // ghi chu noi ve float va phep chia / bien\n"
           "    int x = dem;        /* khong co phep chia nao o day */ (void)x;\n"
           "}\n")
    assert luat_isr(chu, {"T_vect": set()}, "T_vect") == [], \
        [(v.loai, v.dong, v.chu) for v in luat_isr(chu, {"T_vect": set()}, "T_vect")]


def test_chu_thich_bi_bo_ma_SO_DONG_van_dung():
    """Bỏ chú thích mà giữ nguyên độ dài: một cảnh báo sai số dòng là một cảnh báo phải đi
    tìm, và trên một tệp 400 dòng thì nó không được đọc.

    Chú thích phải trải **nhiều dòng** để ca này phân biệt được hai phép: xoá hẳn (`sub("")`)
    và thay bằng khoảng trắng. Với một chú thích MỘT dòng thì `sub("")` vẫn để lại ký tự
    xuống dòng, nên số dòng không lệch và phép phá báo LỌT oan — tập phá chỉ ra đúng thế.
    """
    from eide.build.phan_tich_tinh import luat_isr

    chu = ("volatile int dem;\n"
           "ISR(T_vect) {\n"
           "    /* chu thich khoi\n"
           "       trai ba dong\n"
           "       khong lien quan */\n"
           "    int y = dem / dem;\n"
           "}\n")
    vp = [v for v in luat_isr(chu, {"T_vect": set()}, "T_vect") if v.loai == "phep_chia"]
    assert vp and vp[0].dong == 6, [(v.loai, v.dong) for v in vp]


def test_chu_thich_KHOI_nhieu_dong_cung_bi_bo():
    """Chú thích khối trải NHIỀU dòng — cách firmware trong repo viết mọi mục tài liệu.

    Phép phá chỉ ra rằng bỏ chú thích theo *từng dòng* không đủ: `/* … */` trải nhiều dòng
    không khớp, nên các dòng **giữa** nó bị soi như mã. Và chúng là văn xuôi tiếng Việt, đầy
    dấu `/` và chữ `float`.
    """
    from eide.build.phan_tich_tinh import luat_isr

    chu = ("volatile int dem;\n"
           "ISR(T_vect) {\n"
           "    /* Bang 3.3 — cach tron goc:\n"
           "       dung float hay phep chia / bien deu khong duoc trong ISR,\n"
           "       xem muc 3.3 doan 142 */\n"
           "    dem++;\n"
           "}\n")
    assert luat_isr(chu, {"T_vect": set()}, "T_vect") == [], \
        [(v.loai, v.dong, v.chu) for v in luat_isr(chu, {"T_vect": set()}, "T_vect")]


@pytest.mark.skipif(not co_cc, reason="máy này không có trình biên dịch C")
def test_code_static_co_TRAN_20_phat_hien(bo):
    """Trần 20 chỉ đo được khi có **hơn 20** phát hiện.

    Phép phá chỉ ra rằng ca cũ xanh vì dàn dựng chỉ sinh 0–1 vi phạm — bỏ trần đi cũng không
    đổi gì. Một ISR 30 dòng mỗi dòng một phép chia là dàn dựng, nhưng một ISR thật dài 200
    dòng thì con số phát hiện lên hàng chục rất nhanh.

    Và ca này lộ ra một lỗ thật: macro `ISR(T_vect)` của AVR **không dịch được** trên máy chủ,
    nên bản đầu của `code.static` trả về sớm và bỏ luôn danh sách vi phạm — mà luật ngữ cảnh
    ngắt đọc MÃ NGUỒN, nó không cần trình biên dịch. Trên máy chủ thì mọi firmware AVR đi
    đúng đường ấy, tức phần đáng giá nhất của công cụ không bao giờ tới tay tác tử.
    """
    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / "firmware").mkdir(exist_ok=True)
    than = "\n".join(f"    z = dem / dem; (void)z;   /* dong {i} */" for i in range(30))
    (goc / "firmware" / "isr.c").write_text(
        "volatile int dem;\nint z;\nISR(T_vect) {\n" + than + "\n}\n"
        "int main(void){ dem = 0; for(;;){} }\n", "utf-8")
    r = ag.registry.run("code.static", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_vi_pham"] >= 30, r.data["so_vi_pham"]
    assert len(r.data["vi_pham"]) == 20, len(r.data["vi_pham"])
    assert r.data["bi_cat"] is True
    assert "hiện 20" in r.data["note_vi"], r.data["note_vi"]
    # Dịch đổ thì phải nói rõ NGĂN XẾP chưa đo được, nhưng vẫn giao danh sách vi phạm.
    if not r.data["chay_duoc"]:
        assert "NGĂN XẾP chưa đo được" in r.data["note_vi"], r.data["note_vi"]


def test_code_static_CHUA_DO_DUOC_thi_noi_thang(bo, monkeypatch):
    """Qua CÔNG CỤ, không chỉ qua hàm: chưa đo được thì `note_vi` phải nói thẳng, và phải nói
    rõ *"đây KHÔNG phải không có vi phạm"*.

    Một kết quả rỗng vì thiếu trình biên dịch sẽ được đọc là *"không có vi phạm nào"* — đúng
    cái N6 cấm, và nó là đường dễ nhất để một ô xanh giả đi qua.
    """
    from eide.build import phan_tich_tinh as PT

    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / "firmware").mkdir(exist_ok=True)
    (goc / "firmware" / "a.c").write_text("int f(void){return 1;}\n", "utf-8")
    monkeypatch.setattr(PT.shutil, "which", lambda _x: None)
    r = ag.registry.run("code.static", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["chay_duoc"] is False
    assert "CHƯA phân tích được" in r.data["note_vi"], r.data["note_vi"]
    assert "KHÔNG phải" in r.data["note_vi"], r.data["note_vi"]
    assert ag.store.get("analysis:static") is None, "chưa đo mà vẫn ghi hiện vật"


def test_code_analyze_DINH_tom_tat_tinh(bo):
    """Bước 4 qua CÔNG CỤ: `code.analyze` phải đính tóm tắt vào tệp tài liệu nó ghi ra.

    Phép phá chỉ ra rằng các ca trước gọi `_tom_tat_tinh` **trực tiếp**, nên bỏ hẳn chỗ nối
    trong `code.analyze` mà bộ kiểm vẫn xanh — một hàm đúng với một đường dẫn tới nó bị đứt,
    đúng hình dạng cả đợt này đi vá.
    """
    ag, ctx = bo
    goc = ag.config.paths.project_root
    (goc / "firmware").mkdir(exist_ok=True)
    (goc / "firmware" / "pid.c").write_text("int pid(void){return 1;}\n", "utf-8")
    _hien_vat_tinh(ag, tep=["firmware/pid.c"])

    r = ag.registry.run("code.analyze", {
        "tep": ["firmware/pid.c"], "doi_gi": "đổi hệ số Kp của vòng PID từ 12 xuống 9",
        "vi_sao": "robot dao động quanh điểm cân bằng", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    chu = (goc / r.data["tai_lieu"]).read_text("utf-8")
    assert "Phân tích tĩnh" in chu, chu[-400:]
    assert "272 byte" in chu, chu[-400:]
