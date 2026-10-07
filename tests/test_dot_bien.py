# -*- coding: utf-8 -*-
"""Phép đo độ nhạy của bộ kiểm — và phép kiểm cho chính phép đo ấy.

Bài kiểm này phải làm được đúng một việc mà cả dự án đang đòi ở mọi chỗ khác: chứng minh
rằng cái ô xanh nó bật lên là **đo được**, chứ không phải mặc định. Nên mỗi trạng thái đều
có một ca dựng cảnh ngược lại: một bộ kiểm thật (phải ra `thay`), một bộ kiểm giả (phải ra
`khong_thay`), một bộ kiểm không liên kết nổi (phải ra `khong_nap_duoc`), và một bộ kiểm đỏ
sẵn (phải KHÔNG ra kết luận nào).
"""

from __future__ import annotations

from pathlib import Path

from eide.build import dot_bien as DB


# ---------------------------------------------------------------- đột biến văn bản

def test_dot_bien_khong_dung_vao_chuoi_va_chu_thich():
    """Đổi chữ trong chuỗi/chú thích thì hành vi không đổi — và một đột biến không đổi hành
    vi mà bộ kiểm "không bắt được" là một cáo buộc sai với bộ kiểm."""
    ma = '#include <stdio.h>\nint f(void){ /* 1234 */ puts("toa do 480"); return 480; }\n'
    moi, _, n = DB.dot_bien_van_ban(ma, 0)
    assert n == 1, "chỉ được đổi đúng hằng số 480 trong mã, không đổi số trong chuỗi/chú thích"
    assert '"toa do 480"' in moi
    assert "/* 1234 */" in moi
    assert "return 99999;" in moi
    assert "#include <stdio.h>" in moi


def test_dot_bien_dao_so_sanh():
    moi, _, n = DB.dot_bien_van_ban("if (a == b) x = 1;", 1)
    assert n == 1 and "!=" in moi


def test_dot_bien_khong_pha_toan_tu_ghep():
    """`<=`, `==` trong `!=`, `++` — đổi vào đấy thì mã không dịch được, và "không dịch được"
    sẽ bị đọc nhầm thành "bộ kiểm bắt được"."""
    for phep, ma in ((1, "if (a != b);"), (2, "if (a <= b);"), (3, "i++;")):
        _, _, n = DB.dot_bien_van_ban(ma, phep)
        assert n == 0, f"phép {phep} không được đụng vào {ma!r}"


# ---------------------------------------------------------------- bốn trạng thái

def _tep(tmp_path: Path, ten: str, noi_dung: str) -> Path:
    p = tmp_path / ten
    p.write_text(noi_dung, "utf-8")
    return p


def test_bo_kiem_that_thi_ra_thay(tmp_path):
    """Bộ kiểm thật: nó đọc hằng số trong tệp sản phẩm, nên phá tệp ấy thì nó đỏ."""
    p = _tep(tmp_path, "sp.c", "int nguong(void){ return 480; }\n")

    def chay(them):
        if them is None:
            return True, ""
        return "480" in them.read_text("utf-8"), ""

    d = DB.do_do_nhay([p], chay)
    assert d["tep"][0]["trang_thai"] == "thay"
    assert d["so_thay"] == 1
    assert "KHÔNG RỖNG" in DB.loi_nguoi_doc(d)


def test_bo_kiem_gia_thi_ra_khong_thay(tmp_path):
    """Bộ kiểm giả: xanh bất kể tệp sản phẩm viết gì. Đây là ca chính — nó tái dựng đúng
    `test_ui.c` mà tác tử đã viết ở phiên FreeRTOS."""
    p = _tep(tmp_path, "ui.c", "int nut_x(void){ return 300; }\n")
    d = DB.do_do_nhay([p], lambda them: (True, ""))
    assert d["tep"][0]["trang_thai"] == "khong_thay"
    loi = DB.loi_nguoi_doc(d)
    assert "không chạm tới 1/1" in loi
    assert "tệ hơn không có bộ kiểm nào" in loi


def test_trung_ky_hieu_thi_ra_khong_nap_duoc(tmp_path):
    """Tệp test tự định nghĩa lại hàm của sản phẩm ⇒ trình liên kết báo trùng. Đây là bằng
    chứng MẠNH HƠN `khong_thay`, nên nó phải có trạng thái riêng chứ không gộp vào."""
    p = _tep(tmp_path, "ui.c", "int nut_x(void){ return 300; }\n")
    d = DB.do_do_nhay([p], lambda them: (True, "") if them is None
                      else (False, "ld: duplicate symbol '_nut_x'"))
    assert d["tep"][0]["trang_thai"] == "khong_nap_duoc"
    assert "TRÙNG ký hiệu" in d["tep"][0]["vi_sao"]
    assert "bản sao" in d["tep"][0]["vi_sao"]


def test_thieu_header_bo_thi_noi_dung_ly_do(tmp_path):
    """Đúng chuyện đo được trên `firmware/ui.c`: logic dính header của bo nên bộ kiểm chưa
    từng chạy được dòng nào của nó."""
    p = _tep(tmp_path, "ui.c", "int nut_x(void){ return 300; }\n")
    d = DB.do_do_nhay([p], lambda them: (True, "") if them is None
                      else (False, "ui.c:6:10: fatal error: 'stm32469i_discovery.h' "
                                   "file not found"))
    assert d["tep"][0]["trang_thai"] == "khong_nap_duoc"
    assert "thiếu header của bo" in d["tep"][0]["vi_sao"]
    assert "dính chặt vào phần cứng" in DB.loi_nguoi_doc(d)


def test_bo_kiem_do_san_thi_khong_ket_luan_gi(tmp_path):
    """Đỏ từ trước thì không phân biệt được "đỏ vì đột biến" với "đỏ từ trước" — phải nói
    chưa đo được, không được nói bộ kiểm tốt mà cũng không được nói nó giả."""
    p = _tep(tmp_path, "sp.c", "int f(void){ return 480; }\n")
    d = DB.do_do_nhay([p], lambda them: (False, "1 ca hỏng"))
    assert d["tep"] == []
    assert "vi_sao_khong_do_duoc" in d
    assert "Chưa đo được" in DB.loi_nguoi_doc(d)


def test_tep_khong_co_cho_pha_thi_la_chua_do_duoc(tmp_path):
    """Không có hằng số, không có phép so sánh ⇒ không đột biến được. Cái đó là "chưa biết",
    không phải "bộ kiểm không thấy"."""
    p = _tep(tmp_path, "rong.c", "void f(void){}\n")
    d = DB.do_do_nhay([p], lambda them: (True, ""))
    assert d["tep"][0]["trang_thai"] == "chua_do_duoc"
    assert d["so_khong_thay"] == 0


def test_tra_tep_ve_nguyen_ven_ke_ca_khi_chay_no(tmp_path):
    """Phép đo này sửa mã nguồn của người dùng. Nó văng giữa chừng mà không trả lại thì nó
    tự tay làm hỏng dự án — tệ hơn nhiều so với việc không đo."""
    goc = "int f(void){ return 480; }\n"
    p = _tep(tmp_path, "sp.c", goc)

    def no(them):
        if them is None:
            return True, ""
        if them.read_text("utf-8") != goc:
            raise RuntimeError("trình biên dịch chết")
        return True, ""

    try:
        DB.do_do_nhay([p], no)
    except RuntimeError:
        pass
    assert p.read_text("utf-8") == goc


# ---------------------------------------------------------------- tầng công cụ

def test_cong_cu_test_sensitivity_co_mat_va_khong_khoa():
    """Nó phải là R1 và không khoá: một phép đo tự vạch mặt mình thì phải rẻ tới mức tác tử
    gọi được ngay, không phải xin duyệt."""
    from eide.tools import build_registry
    t = build_registry().get("test.sensitivity")
    assert t is not None and t.risk == "R1"
    assert "test.run" in t.summary_vi, "phải chỉ rõ gọi nó SAU test.run, nếu không nó vô nghĩa"
    from eide.ke_hoach import cong_cu_bi_khoa
    assert not cong_cu_bi_khoa(t)


# ---------------------------------------------------------------- M3-13: phép cho Verilog
#
# Phép đột biến kiểu C không dùng được cho Verilog: `==` → `!=` thì còn khớp, nhưng `posedge`
# sườn lên, toán tử `&` trên bus, và hằng `4'd10` thì không có phép nào chạm tới. Mà đó đúng
# là những chỗ một testbench nông sẽ không canh.
def test_phep_verilog_dao_if_khong_dung_display():
    """TC-M3-13-01 — đảo điều kiện `if`, nhưng KHÔNG đụng chuỗi trong `$display`.

    `$display("if (x)")` có đúng hình dạng một điều kiện. Đổi chữ trong đó thì hành vi không
    đổi, và một đột biến không đổi hành vi mà bộ kiểm "không bắt được" là một cáo buộc sai.
    """
    ma = 'always @(posedge clk) begin\n  if (a) $display("if (x)");\nend\n'
    moi, mo_ta, n = DB.dot_bien_van_ban(ma, 0, bang=DB.PHEP_VERILOG)
    assert n == 1, (n, moi)
    assert "if (!(a))" in moi, moi
    assert '$display("if (x)")' in moi, "đã đụng vào chuỗi trong $display"


def test_phep_verilog_du_nam_phep():
    """Năm phép, mỗi phép chạm một loại lỗi khác nhau của mã RTL."""
    cap = [
        ('if (a) b <= 1;', "if (!(a))"),
        ('assign y = a & b;', " | "),
        ("localparam N = 4'd10;", "4'd11"),
        ('always @(posedge clk) x <= 1;', "negedge"),
        ('if (dem == 5) y <= 1;', "!="),
    ]
    for ma, dau in cap:
        thay = False
        for i in range(len(DB.PHEP_VERILOG)):
            moi, _, n = DB.dot_bien_van_ban(ma, i, bang=DB.PHEP_VERILOG)
            if n and dau in moi:
                thay = True
                break
        assert thay, f"không phép nào đổi được {ma!r} thành có {dau!r}"


def test_bang_mac_dinh_y_nhu_cu():
    """TC-M3-13-02 — ca âm: không truyền bảng thì kết quả y hệt trước khi sửa.

    `test.sensitivity` cho firmware C đang dùng bảng mặc định, và nó không được đổi một ly.
    """
    ma = "int f(void){ int i=0; if (i == 480) i = i + 1; return i; }\n"
    for i in range(4):
        a_moi, a_mo_ta, a_n = DB.dot_bien_van_ban(ma, i)
        b_moi, b_mo_ta, b_n = DB.dot_bien_van_ban(ma, i, bang=DB._PHEP)
        assert (a_moi, a_mo_ta, a_n) == (b_moi, b_mo_ta, b_n)


def test_do_do_nhay_nhan_bang_phep_rieng(tmp_path):
    """`do_do_nhay` phải truyền bảng xuống, không chỉ nhận cho có."""
    v = tmp_path / "dem.v"
    v.write_text("module dem; always @(posedge clk) x <= 1; endmodule\n", "utf-8")
    thay: list[str] = []

    def chay(p):
        thay.append(v.read_text("utf-8"))
        return (True, "KET QUA: PASS") if p is None else (True, "KET QUA: PASS")

    DB.do_do_nhay([v], chay, toi_da_phep=len(DB.PHEP_VERILOG),
                  bang=DB.PHEP_VERILOG)
    assert any("negedge" in t for t in thay), "không phép Verilog nào được áp"


def test_tra_tep_ve_nguyen_ven_khi_chay_nem_loi(tmp_path):
    """TC-M3-13-06 — `chay` ném lỗi thì tệp `.v` vẫn phải nguyên như ban đầu.

    Để lại một tệp RTL ở trạng thái đột biến là hỏng theo kiểu tệ nhất: lần dựng sau dùng
    nó, mọi phép đo sau đó nói về một mạch không ai cố ý viết.
    """
    v = tmp_path / "dem.v"
    goc = "module dem; always @(posedge clk) x <= 1; endmodule\n"
    v.write_text(goc, "utf-8")
    lan = {"n": 0}

    def chay(p):
        lan["n"] += 1
        if lan["n"] > 2:                      # lần đầu: chạy gốc; lần hai: nạp tệp
            raise RuntimeError("iverilog chết")
        return True, "KET QUA: PASS"

    try:
        DB.do_do_nhay([v], chay, toi_da_phep=len(DB.PHEP_VERILOG),
                      bang=DB.PHEP_VERILOG)
    except RuntimeError:
        pass
    assert v.read_text("utf-8") == goc, "tệp RTL bị bỏ lại ở trạng thái đột biến"
