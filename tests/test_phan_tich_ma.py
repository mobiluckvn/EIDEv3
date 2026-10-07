# -*- coding: utf-8 -*-
"""M2-08 — `code.analyze` phải thấy NGẮT, và không được nuốt hàm kế tiếp.

Tài liệu phân tích mã sinh ra để người đọc **trước khi duyệt cho sửa**. Nó nói "tệp này có
những hàm nào" — nên một hàm nó không thấy là một hàm không ai nhìn trước khi sửa.

Hai lỗi, đo trên mã thật của dự án robot (`du-lieu/robot-tu-can-bang/firmware/`):

* `ISR(TIMER0_COMPA_vect)` — cú pháp ngắt của AVR — **không khớp mẫu nào**, vì mẫu đòi có
  kiểu trả về trước tên hàm. timer.c có hai ngắt, cả hai vắng mặt trong tài liệu.
* `[^;]*` trong mẫu là **tham lam**: nó vượt qua cả những hàm thân rỗng (không có dấu `;`)
  và nuốt luôn các hàm phía sau. Ba hàm liền nhau mà thân rỗng thì chỉ hàm đầu được thấy.

Ngắt là đúng chỗ đắt nhất để bỏ sót: nó chạy ngoài luồng chính, nó chạm biến chia sẻ, và
nó là nơi một lỗi đồng bộ không bao giờ tái hiện được bằng cách đọc luồng chính.
"""

from __future__ import annotations

import pathlib

import pytest

from eide.phan_tich_ma import _ky_hieu

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}

_BA_HAM = """static void phu(void) { }
void __attribute__((interrupt)) TIM2_IRQHandler(void) { }
void SysTick_Handler(void)
{
}
"""


def _c(chu: str) -> list[str]:
    return _ky_hieu(pathlib.Path("t.c"), chu)


# =========================================================================== ngắt
def test_ISR_macro_AVR_duoc_nhan():
    """TC-M2-08-01 — `ISR(vector)` là một hàm, dù không có kiểu trả về."""
    assert "TIMER0_COMPA_vect" in _c("ISR(TIMER0_COMPA_vect) {\n x++;\n}\n")


def test_ISR_tren_ma_THAT_cua_robot():
    """Tiêu chí xong của nhiệm vụ: đúng 3 ngắt trong firmware robot (timer.c ×2, uart.c ×1).

    Đo trên tệp thật chứ không trên mẫu tự viết: mẫu tự viết thì tôi vô tình viết nó khớp
    với mẫu regex của mình, còn mã thật thì không nhân nhượng. Và tên vector thì TRA, không
    nhớ — bản đầu của ca này tôi ghi `USART_RX_vect` cho uart.c, mã thật là
    `USART_UDRE_vect`.
    """
    from eide.phan_tich_ma import phan_loai

    goc = pathlib.Path(__file__).resolve().parents[1] / "du-lieu/robot-tu-can-bang/firmware"
    if not goc.exists():
        pytest.skip("không có firmware robot trên máy này")
    isr = {}
    for t in sorted(goc.glob("*.c")):
        pl = phan_loai(t, t.read_text("utf-8", errors="replace"))
        ten = [k for k, v in pl.items() if v == "isr"]
        if ten:
            isr[t.name] = sorted(ten)
    assert isr == {"timer.c": ["TIMER0_COMPA_vect", "TIMER2_COMPA_vect"],
                   "uart.c": ["USART_UDRE_vect"]}, isr


def test_khong_nuot_ham_ke_tiep():
    """TC-M2-08-02 — ba hàm liền nhau, thân rỗng: phải thấy đủ ba."""
    assert _c(_BA_HAM) == ["phu", "TIM2_IRQHandler", "SysTick_Handler"], _c(_BA_HAM)


def test_phan_loai_isr():
    """TC-M2-08-03 — ba loại, ba chữ: hàm thường, ngắt, và hàm `static` chỉ dùng nội bộ."""
    from eide.phan_tich_ma import phan_loai

    pl = phan_loai(pathlib.Path("t.c"), _BA_HAM)
    assert pl["SysTick_Handler"] == "isr", pl
    assert pl["TIM2_IRQHandler"] == "isr", pl
    assert pl["phu"] == "static", pl

    pl2 = phan_loai(pathlib.Path("t.c"), "void chay(void) { }\nISR(ADC_vect) { }\n")
    assert pl2 == {"chay": "ham", "ADC_vect": "isr"}, pl2


def test_loi_goi_ham_trong_than_khong_thanh_dinh_nghia():
    """TC-M2-08-05 — ca âm: `foo(1);` trong thân `main` không phải một định nghĩa hàm."""
    assert _c("int main(void){ foo(1); return 0; }") == ["main"]


def test_khai_bao_co_dau_phay_cham_khong_tinh_la_dinh_nghia():
    """Ca âm thứ hai: nguyên mẫu trong `.c` là khai báo, không phải định nghĩa."""
    assert _c("void chi_khai_bao(void);\nvoid co_than(void) { }\n") == ["co_than"]


def test_ham_nhieu_dong_tham_so_van_nhan_duoc():
    """Danh sách tham số trải nhiều dòng là chuyện thường trong mã nhúng."""
    chu = "int tinh(int a,\n        int b,\n        int c)\n{\n  return a;\n}\n"
    assert _c(chu) == ["tinh"], _c(chu)


# =========================================================================== qua công cụ
def test_code_analyze_tai_lieu_co_muc_ISR(make_agent, du_an):
    """TC-M2-08-04 — tài liệu người đọc phải NÓI RA là tệp có ngắt."""
    agent = make_agent([])
    from eide.loop import TurnContext

    ctx = TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                      eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                      emit=lambda c: None, history=agent.history, agent=agent,
                      run_id="run-1", project_name="du-an-thu")
    (du_an / "timer.c").write_text(
        "#include <avr/interrupt.h>\n"
        "static volatile unsigned ms;\n"
        "ISR(TIMER0_COMPA_vect) {\n  ms++;\n}\n"
        "unsigned timer_get_ms(void) { return ms; }\n", "utf-8")

    ra = agent.registry.get("code.analyze").fn(
        ctx, tep=["timer.c"], doi_gi="thêm bộ đếm thứ hai",
        vi_sao="cần đo chu kỳ vòng điều khiển", explain=EX)
    assert not hasattr(ra, "ok") or ra.ok, getattr(ra, "error", None)

    md = (du_an / ra["tai_lieu"]).read_text("utf-8")
    assert "Ngắt (ISR)" in md, md[:500]
    assert "TIMER0_COMPA_vect" in md, md[:500]
    # Và nói ra HỆ QUẢ, không chỉ liệt kê tên: đây là thứ đổi cách đọc cả phần còn lại.
    assert "volatile" in md, md[:500]
