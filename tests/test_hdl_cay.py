# -*- coding: utf-8 -*-
"""Cây mô-đun HDL — A5.10.

Ca quan trọng nhất của tệp này là `test_tu_khoa_KHONG_thanh_mo_dun`, và nó có lý do riêng:
**bốn ca trong đó là bốn lỗi đã xảy ra thật**, và chúng chỉ lộ ra khi chạy bộ đọc trên PicoRV32
3 049 dòng. Không ca nào trên chuỗi tự soạn bắt được, vì tôi sẽ không nghĩ ra việc thử `if (`.

Mẫu bắt lời gọi mô-đun lúc đầu viết `[ \\t]*` giữa hai tên — tức cho phép **không có gì**. Nên:

    if (…)       → mô-đun `i`     gọi thực thể `f`
    for (…)      → mô-đun `fo`    gọi thực thể `r`
    case (…)     → mô-đun `cas`   gọi thực thể `e`
    assert (…)   → mô-đun `asser` gọi thực thể `t`

Danh sách từ khoá không đỡ được, vì `i` và `fo` **không phải** từ khoá — chúng là một nửa của
từ khoá. Cây mô-đun ra 65 quan hệ, trong đó 50 là rác, và mỗi nút rác mang nhãn "KHÔNG thấy
khai ở tệp nào" nên trông đúng như một tệp bị thiếu.
"""

from __future__ import annotations

from pathlib import Path

from eide.hdl_cay import (
    bo_chu_thich, cay_van_ban, dinh, doc_mot_tep, doc_quan_he, nhom_cua,
    tap_trong_cay, tu_lenh_tong_hop,
)

GOC = Path(__file__).resolve().parents[1]


# =============================================================== đọc lời gọi mô-đun

def test_doc_loi_goi_mo_dun_co_va_khong_co_tham_so():
    ra = doc_mot_tep("""
module soc_top(input clk);
    bram ram (.clk(clk));
    uart_tx #(.BAUD(115200)) tx (.clk(clk));
    picorv32 #(
        .ENABLE_MUL(1),
        .ENABLE_PCPI(0)
    ) cpu (.clk(clk));
endmodule
""")
    assert ra == {"soc_top": ["bram", "uart_tx", "picorv32"]}


def test_tu_khoa_KHONG_thanh_mo_dun():
    """Bốn ca đã xảy ra thật trên PicoRV32. Xem docstring đầu tệp."""
    ra = doc_mot_tep("""
module m;
    integer i;
    initial begin
        if (REGS_INIT_ZERO) begin
            for (i = 0; i < 32; i = i+1)
                cpuregs[i] = 0;
        end
        case (state)
            0: x <= 1;
        endcase
        assert (a == b);
        restrict property (c != 0);
    end
    always @(posedge clk) y <= z;
    assign w = f(1);
endmodule
""")
    assert ra == {"m": []}, f"khớp sai: {ra['m']}"


def test_mo_dun_khong_goi_gi_van_CO_MAT_voi_danh_sach_rong():
    """Nút lá thật khác một mô-đun không được khai ở đâu cả — hai thứ không được lẫn."""
    ra = doc_mot_tep("module la(input a); assign a = 1; endmodule")
    assert ra == {"la": []}


def test_chu_thich_va_chuoi_khong_sinh_quan_he():
    ra = doc_mot_tep("""
module m;
    // bram ram (.clk(clk));
    /* uart_tx tx (.clk(clk)); */
    initial $display("picorv32 cpu (.clk(clk));");
endmodule
""")
    assert ra == {"m": []}, f"chú thích hoặc chuỗi sinh ra quan hệ: {ra}"


def test_bo_chu_thich_GIU_NGUYEN_so_dong():
    """Ăn mất một `\\n` thì hai dòng dán lại, và mẫu `^[ \\t]*` khớp sai chỗ."""
    vao = "a\n/* hai\ndòng */\nb\n"
    assert bo_chu_thich(vao).count("\n") == vao.count("\n")


# =============================================================== cây

def _vd():
    qh = {"tb": ["soc"], "soc": ["cpu", "ram", "uart"], "cpu": ["mul"],
          "ram": [], "uart": [], "mul": [], "le": []}
    ot = {"tb": "bai1/sim/tb.v", "soc": "rtl/soc.v", "cpu": "third_party/p/cpu.v",
          "ram": "rtl/ram.v", "uart": "rtl/uart.v", "mul": "third_party/p/cpu.v",
          "le": "bai3/rtl/le.v"}
    return qh, ot


def test_dinh_la_mo_dun_khong_ai_goi():
    qh, _ = _vd()
    assert dinh(qh) == ["le", "tb"]


def test_tap_trong_cay_khong_gom_mo_dun_khong_ai_goi():
    """Một mô-đun được khai mà không ai gọi thì Yosys bỏ đi — nó KHÔNG vào chip."""
    qh, _ = _vd()
    assert tap_trong_cay(qh, "soc") == {"soc", "cpu", "ram", "uart", "mul"}
    assert "le" not in tap_trong_cay(qh, "soc")
    assert "tb" not in tap_trong_cay(qh, "soc")


def test_cay_van_ban_co_nhanh_dung_muc():
    qh, ot = _vd()
    d = cay_van_ban(qh, ot, "soc")
    assert d[0].startswith("soc")
    # Nhánh phải hiện ra. Bản đầu mất hết tiền tố nên mọi nút cùng một mức, và cây 20 nút
    # của PicoRV32 trông như một danh sách phẳng.
    assert any(x.startswith("├── ") for x in d), f"mất nhánh: {d}"
    assert any(x.startswith("└── ") for x in d), f"mất nhánh cuối: {d}"
    # Con của `cpu` phải thụt sâu hơn `cpu`, và có thanh dọc vì `cpu` chưa phải nút cuối.
    assert any(x.startswith("│   └── mul") or x.startswith("│   ├── mul") for x in d), \
        f"con của cpu không thụt đúng: {d}"


def test_cay_noi_RA_khi_gap_vong_thay_vi_treo():
    qh = {"a": ["b"], "b": ["a"]}
    d = cay_van_ban(qh, {}, "a")
    assert any("vòng" in x for x in d), d
    assert len(d) <= 6, f"không dừng được, ra {len(d)} dòng"


def test_nhan_nhom_suy_tu_duong_dan():
    assert nhom_cua("rtl/bram.v") == "chung"
    assert nhom_cua("bai3/rtl/pcpi_mac.v") == "bài 3"
    assert nhom_cua("bai1/sim/tb_soc.v") == "bài 1"
    assert nhom_cua("third_party/picorv32/picorv32.v") == "bên thứ ba"
    assert nhom_cua("du-lieu/x/third_party/a.v") == "bên thứ ba"


# =============================================================== lấy từ lệnh tổng hợp

def test_rut_tep_va_dinh_tu_lenh_yosys():
    tep, d = tu_lenh_tong_hop(
        ["/opt/homebrew/bin/yosys", "-p",
         "read_verilog -sv /x/rtl/a.v /x/rtl/b.sv; synth_gowin -top soc_top -json /x/o.json"])
    assert tep == ["/x/rtl/a.v", "/x/rtl/b.sv"]
    assert d == "soc_top"


def test_lenh_khong_co_tep_thi_tra_rong_chu_khong_doan():
    tep, d = tu_lenh_tong_hop(["yosys", "-p", "synth_gowin -top x"])
    assert tep == [] and d == "x"


# =============================================================== trên dự án THẬT

def test_tren_du_an_that_cay_phai_dung():
    """Chạy trên dự án RISC-V thật — nơi cả hai lỗi của bộ đọc lộ ra lần đầu.

    Ca này bỏ qua khi chưa có dự án ấy, và nói rõ là bỏ qua vì sao. Nó không thay các ca trên:
    các ca trên canh từng luật, ca này canh rằng chúng đủ cho một tệp 3 049 dòng thật.
    """
    import pytest

    d = GOC / "du-lieu/riscv-tn20k-b"
    if not (d / "rtl/soc_top.v").exists():
        pytest.skip("chưa có dự án du-lieu/riscv-tn20k-b")

    tep = [str(p) for p in sorted((d / "rtl").rglob("*.v"))]
    tep.append(str(d / "third_party/picorv32/picorv32.v"))
    qh, ot = doc_quan_he(d, tep)

    assert qh.get("soc_top") == ["picorv32", "bram", "uart_tx"], qh.get("soc_top")

    # Không nút nào được gọi mà không thấy khai ở đâu. Chính con số này từng là 5.
    thieu = sorted({x for v in qh.values() for x in v} - set(qh))
    assert not thieu, f"gọi mà không thấy khai: {thieu} — bộ đọc khớp sai"

    cay = tap_trong_cay(qh, "soc_top")
    assert "bram" in cay and "uart_tx" in cay and "picorv32" in cay
    assert "blinky" not in cay, "blinky không nằm trong SoC nào — không được vào cây"


def test_A5_10_di_qua_BO_DUNG_TAB_that(tmp_path):
    """Ca này đỏ khi khối chưa được NỐI vào tab Thiết kế — các ca trên thì không.

    Cùng bài học với A8.0 và với `_goc()`: lớp lõi xanh không nói gì về việc lớp trên có nối
    đúng không. Năm công cụ `hdl.*` từng đổ với `E5999` vì chính chuyện đó, và năm ca
    `test_A8_*` của tôi vẫn xanh khi tôi thử bỏ hẳn dòng nối khối ra khỏi `simulation()`.
    """
    from eide.surfaces import design

    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "soc.v").write_text(
        "module soc; ram r (.a(1)); endmodule\nmodule ram(input a); endmodule\n", "utf-8")

    class _Kho:
        def get(self, m):
            if m != "build:hdl:synth":
                return None
            return {"id": m, "canonical": {"lenh": [
                "yosys", "-p",
                f"read_verilog -sv {tmp_path / 'rtl' / 'soc.v'}; "
                "synth_gowin -top soc -json o.json"]}}

        def list(self, *_a, **_k):
            return []

    class _Inv:
        def __getattr__(self, _n):
            return lambda *a, **k: None

    bm = design(_Kho(), _Inv(), str(tmp_path))
    ma = [b.get("code") or b.get("id") for b in (bm.get("blocks") or [])]
    assert any(str(m).startswith("A5.10") for m in ma), (
        f"khối A5.10 chưa được nối vào tab Thiết kế — khối hiện có: {ma}")
    chu = str(bm)
    assert "└── ram" in chu or "├── ram" in chu, "cây phải tới được tab, không chỉ tới hàm dựng"


def test_loi_goi_sau_dau_cham_phay_tren_cung_dong():
    """`module soc; ram r (…); endmodule` trên một dòng là hợp lệ.

    Bản đầu neo mẫu ở `^` đầu dòng, nên nó bỏ qua hoàn toàn — và ca kiểm qua tab của tôi đỏ
    với `0 quan hệ gọi` trong khi khối đã nối đúng. Hai thứ ấy trông giống nhau trên màn hình:
    một khối chưa nối, và một khối nối rồi mà bộ đọc không đọc ra gì.
    """
    assert doc_mot_tep(
        "module soc; ram r (.a(1)); endmodule\nmodule ram(input a); endmodule\n"
    ) == {"soc": ["ram"], "ram": []}
