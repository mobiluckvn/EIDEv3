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

_EX_DN = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—",
          "next": "—", "confidence": "VANG"}


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
    # M4-04 — nay nó GHI hiện vật, nên nó phải đòi `explain`: N8 không có ngoại lệ. Vẫn R1 và
    # vẫn không khoá — "rẻ tới mức gọi được ngay" là chuyện mức rủi ro và cửa duyệt.
    assert t.writes_artefact and t.needs_explain, (t.writes_artefact, t.needs_explain)


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



# ============== M4-05: mutant không dịch được KHÔNG phải "bộ kiểm bắt được" (stillborn)
#
# Vòng đột biến cũ kết luận bằng đúng một câu hỏi: *"phá rồi thì `chay` có trả False không?"*
# Nhưng `False` có hai nghĩa khác hẳn nhau:
#
#   · bộ kiểm chạy và có ca ĐỎ  → đúng là nó canh chỗ ấy;
#   · mã không DỊCH nổi          → chưa có phép kiểm nào chạy, nên chưa biết gì.
#
# Gộp hai nghĩa ấy làm con số độ nhạy đẹp lên một cách giả — và đẹp theo hướng tệ nhất: những
# phép phá THÔ nhất, loại làm hỏng cú pháp, là loại dễ bị tính là "bắt được" nhất, trong khi
# chúng không nói gì về việc bộ kiểm có đọc giá trị nào của tệp hay không.
#
# Chỗ khó: `_DAU_HIEU_KHAC` có `"error:"`, mà `vi_sao_khong_dat` của một ca test hỏng THẬT rất
# dễ chứa chữ ấy ("TC-01: error: mong 1 nhan 0"). Nên dấu hiệu KHÔNG được đọc từ nội dung log,
# mà phải do chính hàm `chay` **khai** ra — bằng tiền tố `[BIEN_DICH] `.

# Tệp có HAI chỗ phá được bằng hai phép khác nhau: hằng `480` (phép 0, đổi thành 99999) và
# `==` (phép 1, đảo thành `!=`). Nhờ thế đo được chuyện "bỏ phép này rồi đi tiếp phép sau".
_HAI_CHO = "int f(int x){ if (x == 1) return 480; return 0; }\n"

# `do_do_nhay` gọi `chay` BA kiểu, và trộn chúng là cách một ca kiểm xanh vì lý do sai:
#   1. `chay(None)`     — mốc, chạy bộ kiểm như tác tử vẫn chạy;
#   2. `chay(p)` với tệp NGUYÊN BẢN — bước nạp, hỏi "bộ kiểm dịch nổi cùng tệp này không";
#   3. `chay(p)` với tệp ĐÃ PHÁ     — vòng đột biến.
# Bản đầu của các ca dưới đây đếm lượt gọi, nên lượt "stillborn" rơi vào bước 2 và ra
# `khong_nap_duoc` — một ca xanh mà chưa chạm tới thứ nó định đo.


def _gia(**theo_noi_dung: tuple[bool, str]):
    """Hàm `chay` giả, phân nhánh theo NỘI DUNG tệp chứ không theo số lượt gọi."""
    def chay(them):
        if them is None:
            return True, ""
        chu = them.read_text("utf-8")
        for dau, kq in theo_noi_dung.items():
            if {"n99999": "99999", "khac": "!=", "loi": "###"}[dau] in chu:
                return kq
        return True, ""                      # tệp nguyên bản: bước nạp phải XANH
    return chay


def test_mutant_khong_dich_duoc_KHONG_tinh_la_thay(tmp_path):
    """TC-M4-05-01 — mutant làm lỗi biên dịch bị bỏ qua, và vòng đo ĐI TIẾP sang phép sau.

    Không `break` ở đó: một phép phá không dịch được chưa trả lời câu hỏi nào, nên câu trả
    lời phải đi tìm ở phép kế tiếp. Dừng lại và gọi nó là "bắt được" là cách con số độ nhạy
    tăng lên mà bộ kiểm không khá hơn một chút nào.
    """
    p = _tep(tmp_path, "sp.c", _HAI_CHO)
    d = DB.do_do_nhay([p], _gia(
        n99999=(False, "[BIEN_DICH] sp.c:1: error: bit-field width not an integer"),
        khac=(False, "TC-01: mong 480 nhan 0")))

    assert d["tep"][0]["trang_thai"] == "thay", d["tep"]
    assert d["so_mutant_khong_hop_le"] == 1, d
    assert "đảo phép so sánh bằng" in d["tep"][0]["vi_sao"], (
        "kết luận phải đến từ phép phá THỨ HAI, không từ phép không dịch được: "
        + d["tep"][0]["vi_sao"])


def test_ca_test_hong_co_chu_error_van_la_thay(tmp_path):
    """TC-M4-05-02 — ca âm: log có chữ "error:" mà KHÔNG có tiền tố thì vẫn là "bắt được".

    Đây là ca đắt nhất của nhiệm vụ. `_DAU_HIEU_KHAC` có `"error:"`, nên một phép dò theo nội
    dung sẽ gọi mọi ca test hỏng có chữ ấy là "mutant không dịch được" — tức biến một phép đo
    *bắt được* thành *chưa đo được*, và con số độ nhạy TỤT xuống vì một lý do sai.
    """
    p = _tep(tmp_path, "sp.c", "int nguong(void){ return 480; }\n")
    d = DB.do_do_nhay([p], _gia(n99999=(False, "TC-01: error: mong 480, nhan duoc 99999")))

    assert d["tep"][0]["trang_thai"] == "thay", d["tep"]
    assert d["so_mutant_khong_hop_le"] == 0, d


def test_moi_phep_deu_stillborn_thi_chua_do_duoc(tmp_path):
    """TC-M4-05-03 — mọi mutant đều không dịch được ⇒ `chua_do_duoc`, nói rõ vì sao.

    Không phải `khong_thay` — đó là một cáo buộc ("bộ kiểm không nhìn tệp này") — và không
    phải `thay`. Cái đúng là "chưa biết", kèm lý do nó chưa biết.
    """
    p = _tep(tmp_path, "sp.c", _HAI_CHO)
    hong = (False, "[BIEN_DICH] error: syntax error")
    d = DB.do_do_nhay([p], _gia(n99999=hong, khac=hong))

    assert d["tep"][0]["trang_thai"] == "chua_do_duoc", d["tep"]
    assert d["so_chua_do"] == 1 and d["so_thay"] == 0, d
    assert d["so_mutant_khong_hop_le"] == 2, d
    assert "biên dịch" in d["tep"][0]["vi_sao"], d["tep"][0]["vi_sao"]


def test_tien_to_BIEN_DICH_khong_doi_phan_loai_o_buoc_NAP(tmp_path):
    """Bước nạp mã gốc giữ nguyên phân loại `khong_nap_duoc` — kế hoạch cấm đổi chỗ này.

    Hai bước nói hai chuyện: *mã sản phẩm có dịch được cùng bộ kiểm không* (bước nạp) và
    *mutant có dịch được không* (vòng đột biến). Gộp chúng lại là mất đúng cái kết luận mạnh
    nhất của phép đo — "bộ kiểm chưa từng chạy một dòng nào của tệp này".
    """
    p = _tep(tmp_path, "sp.c", _HAI_CHO)
    d = DB.do_do_nhay([p], lambda them: (True, "") if them is None
                      else (False, "ld: duplicate symbol _nguong"))

    assert d["tep"][0]["trang_thai"] == "khong_nap_duoc", d["tep"]
    assert d["so_khong_nap"] == 1, d
    assert d["so_mutant_khong_hop_le"] == 0, "chưa vào vòng đột biến mà đã đếm mutant"


def test_so_mutant_khong_hop_le_co_mat_ca_khi_bang_khong(tmp_path):
    """Khoá `so_mutant_khong_hop_le` phải luôn có trong kết quả, kể cả khi bằng 0.

    Một khoá chỉ xuất hiện khi khác 0 thì bên đọc phải `.get(...)` kèm một giá trị mặc định,
    và mặc định ấy sớm muộn sai ở một chỗ nào đó. Đây cũng là thứ `loi_nguoi_doc` đọc.
    """
    p = _tep(tmp_path, "sp.c", "int nguong(void){ return 480; }\n")
    d = DB.do_do_nhay([p], _gia(n99999=(False, "TC-01 do")))

    assert "so_mutant_khong_hop_le" in d, sorted(d)
    assert d["so_mutant_khong_hop_le"] == 0, d


def test_loi_nguoi_doc_NOI_RA_co_mutant_stillborn(tmp_path):
    """Đoạn cho người đọc phải nói ra số mutant bị bỏ — không thì con số kia đọc như đã đo hết.

    "Bắt 1/1" sau khi một phép phá bị bỏ vì không dịch được là một câu đúng về mẫu số của nó
    và sai về điều người đọc hiểu.
    """
    p = _tep(tmp_path, "sp.c", _HAI_CHO)
    chu = DB.loi_nguoi_doc(DB.do_do_nhay([p], _gia(
        n99999=(False, "[BIEN_DICH] error: x"), khac=(False, "TC-01 do"))))

    assert "không dịch được" in chu, chu
    assert "1" in chu, chu



# ---------------- đường dẫn tới cơ chế: hai CÔNG CỤ THẬT phải đếm được mutant stillborn
#
# `dot_bien` biết đọc tiền tố là một nửa. Nửa còn lại là hai hàm `chay` thật — của
# `test.sensitivity` và của `hdl.sensitivity` — phải KHAI nó ra. Thiếu nửa sau thì cơ chế có
# sẵn mà không lượt đo nào đi qua nó, đúng cái mẫu lặp lại nhiều nhất trong dự án này.
#
# Nên hai ca dưới đây **gọi đúng công cụ**, không chép lại logic của nó. Bản đầu của tôi dựng
# lại một `_chay` giống `_chay` thật rồi kiểm tiền tố trên bản sao ấy — một ca xanh chứng minh
# rằng *đoạn mã trong ca kiểm* làm đúng, không chứng minh gì về sản phẩm.

import shutil                                                            # noqa: E402

import pytest                                                            # noqa: E402

co_cc = bool(shutil.which("cc") or shutil.which("clang") or shutil.which("gcc"))
co_iv = bool(shutil.which("iverilog") and shutil.which("vvp"))


def _ctx_sp(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1",
                       agent=agent)


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_test_sensitivity_dem_duoc_mutant_stillborn(make_agent):
    """Công cụ `test.sensitivity` THẬT phải trả `so_mutant_khong_hop_le` ≥ 1 — đo trên cc.

    Dàn dựng: hằng `16` là **độ rộng bit-field**, nên phép phá 0 của bảng C đổi nó thành
    `99999` và `cc` đổ (*width of bit-field 'b' (99999 bits) exceeds the width of its type*).
    Đây là một phép phá hợp lệ về văn bản — không phải một dàn dựng giả — và đúng hình dạng
    mutant stillborn mà nhiệm vụ này nhắm tới.

    Bản đầu của tôi dùng `: 480`, và tệp GỐC đã không dịch được — nên lượt đo dừng ở bước nạp
    với `khong_nap_duoc`, chưa vào vòng đột biến. Một dàn dựng mà mã gốc đã hỏng thì không đo
    được chuyện gì về mutant.

    Trước M4-05, lượt đo ấy ra `thay`: "bộ kiểm bắt được" cho một mutant mà bộ kiểm chưa bao
    giờ chạy.
    """
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    # Tệp test phải dịch được MỘT MÌNH: `_chay(None)` là mốc, và nó chỉ dịch tệp test. Bản
    # đầu của ca này cho tệp test gọi `nguong()` của sản phẩm, nên mốc đổ ở bước liên kết và
    # cả phép đo dừng ngay với `bo_kiem_xanh_luc_dau = False` — `tep` rỗng, không lượt đột
    # biến nào chạy.
    (goc / "firmware" / "sp.c").write_text(
        "struct S { unsigned b : 16; };\nint khac(void){ return 1; }\n", "utf-8")
    (goc / "test" / "t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"a\\",\\"dat\\":true}]}'
        '\\n"); return 0; }\n', "utf-8")

    r = agent.registry.run("test.sensitivity", {"explain": _EX_DN, "nguon": ["firmware/sp.c"],
                                               "test": ["test/t.c"]}, _ctx_sp(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_mutant_khong_hop_le"] >= 1, (
        "công cụ thật KHÔNG đếm được mutant stillborn — cơ chế có sẵn, đường dẫn tới nó "
        f"đứt: {r.data['tep']}")
    assert r.data["tep"][0]["trang_thai"] != "thay", r.data["tep"]
    assert "không dịch được" in r.data["note_vi"], r.data["note_vi"]


@pytest.mark.skipif(not co_iv, reason="máy chưa có iverilog")
def test_hdl_do_do_nhay_dem_duoc_mutant_stillborn(tmp_path):
    """`do_do_nhay_hdl` THẬT phải đếm được mutant Verilog không dịch được.

    Phép `đổi hằng số thập phân (+1)` của bảng Verilog biến `4'd5` của **độ rộng bus**
    (`[3:0]` không đụng tới) — nên để dựng được một mutant hỏng cú pháp một cách tự nhiên,
    dùng `posedge → negedge` trên một chỗ không hợp lệ thì khó. Thay vào đó dàn dựng một
    mô-đun mà phép `& → |` làm sai kiểu: `q <= a & b;` với `b` chưa khai → iverilog đổ.
    """
    from eide.build import hdl as H

    rtl = tmp_path / "rtl"
    rtl.mkdir()
    # `chot.v`: chỗ duy nhất phá được là `&`, và sau khi đổi thành `|` thì `c` chưa khai làm
    # iverilog đổ — mutant hỏng cú pháp sinh ra từ một phép phá hợp lệ về văn bản.
    (rtl / "chot.v").write_text(
        "module chot(input a, input b, output q);\n"
        "  assign q = a & b;\n"
        "endmodule\n", "utf-8")
    (rtl / "tb.v").write_text(
        "module tb;\n"
        "  reg a = 1, b = 1; wire q;\n"
        "  chot u(.a(a), .b(b), .q(q));\n"
        '  initial begin #1 if (q === 1\'b1) $display("KET QUA: PASS");\n'
        '    else $display("KET QUA: FAIL q=%b", q); $finish; end\n'
        "endmodule\n", "utf-8")

    r = H.do_do_nhay_hdl(goc=tmp_path, rtl=[rtl / "chot.v"], nguon=rtl, dinh="tb")
    assert r["bo_kiem_xanh_luc_dau"], r.get("vi_sao_khong_do_duoc") or r
    assert "so_mutant_khong_hop_le" in r, sorted(r)
    # `&` → `|` dịch được (a|b vẫn là 1), nên nó KHÔNG stillborn và testbench vẫn xanh.
    # Ca này chốt chuyện quan trọng hơn: đường HDL mang theo khoá đếm, và một mutant dịch
    # được thì KHÔNG bị đếm là stillborn.
    assert r["so_mutant_khong_hop_le"] == 0, r["tep"]


@pytest.mark.skipif(not co_iv, reason="máy chưa có iverilog")
def test_hdl_mutant_hong_cu_phap_KHONG_tinh_la_bat_duoc(tmp_path):
    """Đường HDL thật: mutant làm iverilog đổ phải vào `so_mutant_khong_hop_le`, không vào `thay`.

    Dùng một bảng phép đột biến **một phép duy nhất** làm hỏng cú pháp, để đo đúng một chuyện
    và không phụ thuộc thứ tự của `PHEP_VERILOG`.
    """
    from eide.build import hdl as H

    rtl = tmp_path / "rtl"
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

    def chay(_p=None):
        kq = H.mo_phong(goc=tmp_path, nguon=rtl, dinh="tb")
        if not kq.dat and kq.loi:
            return False, DB.TIEN_TO_BIEN_DICH + kq.nguyen_van
        return bool(kq.dat), kq.nguyen_van

    # Bảng một phép: `q + 1` → `q + ;` — hỏng cú pháp, và là phép phá duy nhất áp được.
    bang = ((r"q \+ 1", "q + ", "bỏ toán hạng phải của phép cộng"),)
    d = DB.do_do_nhay([rtl / "dem.v"], chay, toi_da_phep=1, bang=bang)

    assert d["so_mutant_khong_hop_le"] == 1, d["tep"]
    assert d["tep"][0]["trang_thai"] == "chua_do_duoc", d["tep"]
    assert d["so_thay"] == 0, "mutant hỏng cú pháp bị tính là bộ kiểm BẮT ĐƯỢC"
    assert (rtl / "dem.v").read_text("utf-8").count("q + 1") == 1, "tệp RTL không được trả lại"


@pytest.mark.skipif(not co_iv, reason="máy chưa có iverilog")
def test_mo_phong_KHONG_chay_lai_tep_sim_cu_khi_bien_dich_do(tmp_path):
    """Ô xanh giả nằm trên CHÍNH ĐƯỜNG ĐO: biên dịch đổ mà vẫn báo PASS của lượt trước.

    `mo_phong` dựng `sim.vvp` rồi chạy nó, và nó chỉ hỏi `anh.exists()`. Tệp của lượt trước
    còn nằm đó, nên một lượt dịch **đổ** vẫn thấy "có tệp" và `vvp` chạy **bản cũ** — in ra
    `PASS` của một mã khác mã trên đĩa.

    Đo được 08/10/2026: `dem.v` sửa thành `q <= q + ;` (sai cú pháp) cho `dat = True`,
    `pass_fail = "PASS"`, `ma_thoat = 0`. Trên đường đo độ nhạy nó còn tệ hơn một bậc: mutant
    hỏng cú pháp được đọc thành *"testbench vẫn xanh"*, tức **"bộ kiểm không canh chỗ này"* —
    một cáo buộc sai về sản phẩm, sinh ra từ một tệp sót lại.

    `_don_tep_ra` đã có từ 01/10/2026 cho đúng chuyện này ở `nextpnr`; `tong_hop`,
    `dat_di_day`, `dong_goi` đều gọi nó, chỉ `mo_phong` là không.
    """
    from eide.build import hdl as H

    rtl = tmp_path / "rtl"
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

    # Lượt 1: mã đúng → đạt, và để lại `sim.vvp` trên đĩa.
    assert H.mo_phong(goc=tmp_path, nguon=rtl, dinh="tb").dat
    assert (tmp_path / ".eide" / "hdl" / "sim.vvp").exists(), "dàn dựng sai: chưa có tệp cũ"

    # Lượt 2: mã SAI CÚ PHÁP, tệp cũ vẫn còn đó.
    van = (rtl / "dem.v").read_text("utf-8")
    try:
        (rtl / "dem.v").write_text(van.replace("q <= q + 1;", "q <= q + ;"), "utf-8")
        kq = H.mo_phong(goc=tmp_path, nguon=rtl, dinh="tb")
    finally:
        (rtl / "dem.v").write_text(van, "utf-8")

    assert kq.dat is False, "biên dịch ĐỔ mà vẫn báo đạt — đang chạy lại tệp mô phỏng cũ"
    assert kq.pass_fail == "", f"đọc được PASS/FAIL của lượt trước: {kq.pass_fail!r}"
    assert kq.loi, "không giữ lại lỗi biên dịch"


def test_loi_nguoi_doc_khong_khen_khi_chua_do_duoc_tep_nao(tmp_path):
    """0/N tệp mà câu kết lại là "phá tệp nào cũng có ca đỏ" thì nó đang khen một chỗ trống.

    Trước M4-05, nhánh cuối của `loi_nguoi_doc` chạy cho cả trường hợp `so_thay == 0`: người
    đọc nhận một câu nghe như lời bảo đảm, cho một lượt đo chưa kết luận được gì.
    """
    p = _tep(tmp_path, "sp.c", _HAI_CHO)
    hong = (False, "[BIEN_DICH] error: syntax error")
    chu = DB.loi_nguoi_doc(DB.do_do_nhay([p], _gia(n99999=hong, khac=hong)))

    assert "CHƯA ĐO ĐƯỢC" in chu, chu
    assert "phá tệp nào cũng có ca đỏ" not in chu, chu
    assert "“chưa biết”" in chu, chu


def test_ma_cho_giu_di_va_ve_khong_lech():
    """Mã chỗ giữ phải song ánh với số thứ tự — lệch một chỗ là trả lại SAI chuỗi."""
    assert [DB._ma_cho(i) for i in range(5)] == ["A", "B", "C", "D", "E"]
    assert DB._ma_cho(25) == "Z" and DB._ma_cho(26) == "AA"
    assert all(DB._so_cho(DB._ma_cho(i)) == i for i in range(0, 2000))


def test_tep_co_HON_MUOI_chu_thich_van_dot_bien_duoc():
    """Tệp có ≥ 10 chuỗi/chú thích phải đột biến được — bản cũ ném `IndexError`.

    Chỗ giữ cũ là `\\x00{i}\\x00`, và `\\x00` không nằm trong `[\\w.]`, nên phép phá đầu của
    bảng C (`\\d{2,}` → `99999`) đột biến **chính con số của chỗ giữ**. Từ chỗ giữ thứ 11 trở
    đi (`\\x0010\\x00`) thì `giu[99999]` ném `IndexError`.

    Đo được 08/10/2026: `test.sensitivity` ĐỔ trên cả ba dự án firmware thật trong `du-lieu/`
    — mọi tệp firmware thật đều có hơn 10 chú thích. Tức đường đo độ nhạy cho C chưa bao giờ
    chạy nổi trên một tệp thật; các con số cũ đều từ tệp nhỏ do ca kiểm tự dựng.
    """
    ma = "".join(f"// chu thich {i}\n" for i in range(14)) + "int f(void){ return 480; }\n"
    moi, _, n = DB.dot_bien_van_ban(ma, 0)

    assert n == 1, n
    assert "99999" in moi and "480" not in moi, moi[-80:]
    # Mọi chú thích phải về nguyên vẹn, và không còn chỗ giữ nào sót lại.
    for i in range(14):
        assert f"// chu thich {i}\n" in moi, i
    assert "\x00" not in moi, "còn sót chỗ giữ trong mã đã đột biến"


def test_chu_thich_khong_bi_dot_bien_ke_ca_khi_co_so_dai():
    """Ca âm đi kèm: con số NẰM TRONG chú thích vẫn không được đổi.

    Đây là điều `_BO_QUA` tồn tại để bảo đảm, và nó phải còn đúng sau khi đổi cách mã hoá chỗ
    giữ — đổi một hằng trong `printf` thì hành vi không đổi, và một đột biến không đổi hành vi
    mà bộ kiểm "không bắt được" là một cáo buộc sai.
    """
    ma = ("// nguong 480 theo datasheet\n" * 12) + "int f(void){ return 17; }\n"
    moi, _, n = DB.dot_bien_van_ban(ma, 0)

    assert n == 1, n
    assert moi.count("nguong 480 theo datasheet") == 12, moi[:120]
    assert "return 99999;" in moi, moi[-60:]


# ------------- luật "chỉ gắn tiền tố khi có lỗi biên dịch" — MỘT chỗ, và đo được
#
# Lượt phá đầu của M4-05 cho thấy luật này nằm trong hai closure (`_chay` của
# `test.sensitivity`, `chay` của `hdl.sensitivity`) mà không ca kiểm nào gọi tới được: hai
# phép phá nhắm đúng chỗ ấy đều LỌT. Gom về `ket_qua_chay` thì nó đo được, và hai đường không
# còn lệch nhau trong im lặng.

def test_ket_qua_chay_gan_tien_to_khi_co_loi_bien_dich():
    dat, log = DB.ket_qua_chay(dat=False, loi_bien_dich="sp.c:1: error: x", log="bỏ qua")
    assert dat is False
    assert DB._la_loi_bien_dich(log) and "error: x" in log, log


def test_ket_qua_chay_KHONG_gan_tien_to_khi_QUA_HAN():
    """Quá hạn cũng là không đạt — nhưng một mutant làm bộ kiểm TREO không phải stillborn.

    Gọi nó là stillborn là nói sai về nguyên nhân: nó là một mutant mà phép đo không kết luận
    được, không phải một mutant chưa bao giờ dịch. Và hậu quả thực tế ngược hẳn nhau: một cái
    bảo "bỏ qua phép này", cái kia bảo "xem lại vì sao mã treo".
    """
    dat, log = DB.ket_qua_chay(dat=False, log="Test chạy quá 120 s — nhiều khả năng có vòng "
                                              "chờ không bao giờ thoát.")
    assert dat is False
    assert not DB._la_loi_bien_dich(log), log
    assert "quá 120 s" in log


def test_ket_qua_chay_dat_thi_khong_bao_gio_gan_tien_to():
    dat, log = DB.ket_qua_chay(dat=True, loi_bien_dich="error: x", log="")
    assert dat is True and not DB._la_loi_bien_dich(log), log


@pytest.mark.skipif(not co_iv, reason="máy chưa có iverilog")
def test_do_do_nhay_hdl_dem_stillborn_tren_duong_THAT(tmp_path):
    """`do_do_nhay_hdl` THẬT phải đếm mutant Verilog không dịch được.

    Năm phép của `PHEP_VERILOG` cố ý đều **hợp lệ về cú pháp** — mỗi phép đổi hành vi chứ
    không đổi văn bản — nên qua bảng mặc định không dựng nổi một mutant stillborn, và nhánh
    gắn tiền tố của `do_do_nhay_hdl` không ca nào chạm tới được. Đó là chỗ LỌT ở lượt phá đầu.

    Nên ca này bơm một bảng một phép làm hỏng cú pháp vào **đúng đường thật**: cùng hàm, cùng
    `mo_phong`, cùng `chay`. Chỉ cái bảng là của ca kiểm.
    """
    from eide.build import hdl as H

    rtl = tmp_path / "rtl"
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

    r = H.do_do_nhay_hdl(goc=tmp_path, rtl=[rtl / "dem.v"], nguon=rtl, dinh="tb",
                         bang=((r"q \+ 1", "q + ", "bỏ toán hạng phải của phép cộng"),))

    assert r["bo_kiem_xanh_luc_dau"], r.get("vi_sao_khong_do_duoc") or r
    assert r["so_mutant_khong_hop_le"] == 1, r["tep"]
    assert r["so_thay"] == 0, "mutant hỏng cú pháp bị tính là testbench BẮT ĐƯỢC"
    assert (rtl / "dem.v").read_text("utf-8").count("q + 1") == 1, "tệp RTL không được trả lại"


def test_cong_cu_hdl_sensitivity_MANG_THEO_so_mutant_stillborn(tmp_path, monkeypatch):
    """Công cụ `hdl.sensitivity` phải mang con số stillborn ra cả ba chỗ: kết quả, kho, note.

    Đây là tầng **báo lại**, và nó hỏng theo kiểu riêng: phép đo đúng, con số đúng, rồi con số
    không đi tới đâu. Ba phép phá nhắm ba chỗ ấy đều LỌT ở lượt đầu, vì mọi ca kiểm cũ của
    công cụ này đều đi qua một lượt đo có `stillborn == 0`.

    Nên ở đây `do_do_nhay_hdl` được thay bằng một bản trả số sẵn: phần đang đo là tầng báo
    lại, không phải phép đo.
    """
    from types import SimpleNamespace

    from eide.build import hdl as H
    from eide.tools import build_registry

    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "dem.v").write_text("module dem; endmodule\n", "utf-8")
    monkeypatch.setattr(H, "do_do_nhay_hdl", lambda **_k: {
        "bo_kiem_xanh_luc_dau": True, "so_thay": 1, "so_khong_thay": 0,
        "so_khong_nap": 0, "so_chua_do": 0, "so_mutant_khong_hop_le": 2,
        "tep": [{"tep": "dem.v", "trang_thai": "thay", "vi_sao": "x"}]})

    ghi: dict = {}
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=tmp_path)),
        run_id="test",
        store=SimpleNamespace(get=lambda _m: None, apply=lambda **k: ghi.update(k)))
    sp = next(t for t in build_registry().all() if t.name == "hdl.sensitivity")
    kq = sp.fn(ctx, explain=_EX_DN, nguon="rtl", nguon_rtl=["rtl/dem.v"], dinh="tb")

    d = kq if isinstance(kq, dict) else getattr(kq, "data", {}) or {}
    assert d.get("so_mutant_khong_hop_le") == 2, d
    assert (ghi.get("canonical") or {}).get("do_nhay", {}).get(
        "so_mutant_khong_hop_le") == 2, ghi.get("canonical")
    assert "không dịch được" in d["note_vi"], d["note_vi"]




# ====== M4-19: đột biến trên BẢN SAO, không ghi đè tệp sản phẩm của người dùng
#
# `do_do_nhay` ghi mã đã phá vào **chính tệp của dự án**, rồi trả lại trong `finally`. Nó chỉ
# an toàn với ngoại lệ Python. Một `Ctrl-C`, một lần máy hết pin, một `kill -9` giữa vòng đo —
# và tệp sản phẩm nằm lại ở trạng thái đã bị phá, trong một dự án mà người dùng tưởng là
# nguyên vẹn. Phép đo tự tay làm hỏng thứ nó đi đo: tệ hơn nhiều so với không đo.
#
# Suốt M4-05 tôi phải sao `du-lieu/` ra scratchpad trước mỗi lượt đo thật, chỉ vì chuyện này.

def test_tep_goc_KHONG_bi_ghi_trong_luc_do(tmp_path):
    """TC-M4-19-01 — tệp gốc phải nguyên vẹn ở **mọi** lần `chay` được gọi, không chỉ lúc cuối.

    Kiểm "sau khi xong thì tệp nguyên vẹn" là chưa đủ: `finally` đã bảo đảm điều ấy từ trước.
    Câu cần hỏi là *trong lúc đo* tệp gốc có bị đổi lần nào không — vì đó là khoảng thời gian
    mà một lần ngắt sẽ bắt gặp.
    """
    goc_van = "int f(int x){ if (x == 1) return 480; return 0; }\n"
    p = _tep(tmp_path, "sp.c", goc_van)
    tam = tmp_path / "tam"
    sai: list[str] = []

    def chay(them):
        if p.read_text("utf-8") != goc_van:
            sai.append(f"tệp gốc đã bị đổi khi chay({them})")
        return (True, "") if them is None else (False, "TC-01 do")

    DB.do_do_nhay([p], chay, thu_muc_tam=tam)
    assert not sai, sai
    assert p.read_text("utf-8") == goc_van


def test_chay_nhan_ban_sao_khong_phai_tep_goc(tmp_path):
    """TC-M4-19-02 — mọi đường dẫn đưa cho `chay` phải nằm DƯỚI `thu_muc_tam`.

    Kể cả lượt "nạp mã gốc": nếu lượt ấy đưa tệp thật mà vòng đột biến đưa bản sao, thì hai
    lượt chạy khác nhau ở một chỗ không ai khai ra — và chênh lệch giữa chúng bị đọc thành
    kết luận về bộ kiểm.
    """
    goc_van = "int f(void){ return 480; }\n"
    p = _tep(tmp_path, "sp.c", goc_van)
    tam = tmp_path / "tam"
    thay: list = []

    def chay(them):
        thay.append(them)
        if them is None:
            return True, ""
        return (True, "") if them.read_text("utf-8") == goc_van else (False, "TC-01 do")

    DB.do_do_nhay([p], chay, thu_muc_tam=tam)
    duong = [x for x in thay if x is not None]
    assert duong, "không lần nào `chay` nhận tệp sản phẩm"
    assert all(tam in x.parents for x in duong), [str(x) for x in duong]
    assert all(x.name == "sp.c" for x in duong), [str(x) for x in duong]


def test_khong_co_thu_muc_tam_thi_duong_cu_giu_nguyen(tmp_path):
    """Ca âm tương thích: không nêu `thu_muc_tam` thì vẫn đột biến tại chỗ như trước.

    Ca `test_tra_tep_ve_nguyen_ven_ke_ca_khi_chay_no` và mọi ca cũ đi đường ấy. Đổi hành vi
    mặc định là phá tương thích ngược, và một hàm đổi ngầm thì bên gọi không biết để sửa.
    """
    goc_van = "int f(void){ return 480; }\n"
    p = _tep(tmp_path, "sp.c", goc_van)
    thay: list = []

    def chay(them):
        thay.append(them)
        if them is None:
            return True, ""
        # Bước NẠP đưa tệp nguyên bản — phải xanh, không thì vòng đo dừng ở đó và ca này
        # xanh mà chưa chạm tới vòng đột biến.
        return (True, "") if them.read_text("utf-8") == goc_van else (False, "TC-01 do")

    DB.do_do_nhay([p], chay)
    assert [x for x in thay if x is not None] == [p, p], [str(x) for x in thay]


def test_ban_sao_bi_DON_sau_khi_do(tmp_path):
    """Bản sao là rác của phép đo — để lại thì lần dựng sau có thể ăn phải nó.

    Cùng hình dạng với lỗi `sim.vvp` cũ ở DEV-348: một tệp sót lại từ lượt trước làm lượt
    sau nói về một mã khác mã trên đĩa.
    """
    goc_van = "int f(void){ return 480; }\n"
    p = _tep(tmp_path, "sp.c", goc_van)
    tam = tmp_path / "tam"
    DB.do_do_nhay([p], lambda them: (True, "") if them is None
                  else ((True, "") if them.read_text("utf-8") == goc_van else (False, "do")),
                  thu_muc_tam=tam)
    assert not tam.exists(), (
        "thư mục tạm còn nằm lại sau khi đo xong: "
        + str(sorted(str(x.relative_to(tam)) for x in tam.rglob("*"))))


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_sensitivity_include_tuong_doi_van_dich_duoc(make_agent):
    """TC-M4-19-03 — `#include "pid.h"` tương đối vẫn tìm thấy khi mã đã sang bản sao.

    Đây là cái bẫy mà kế hoạch nêu sẵn, và nó biến một tiến bộ thành một lùi bước: sao tệp ra
    thư mục tạm thì `#include "pid.h"` cạnh tệp gốc không còn cạnh bản sao, `cc` đổ, và phép
    đo xếp tệp ấy là `khong_nap_duoc` — *"bộ kiểm chưa từng chạy một dòng nào của nó"*. Một
    cáo buộc sai về sản phẩm, sinh ra từ chỗ đặt bản sao.

    Tệp test ở đây **tự dịch được một mình**, vì `chay(None)` là mốc và nó chỉ dịch tệp test:
    một tệp test gọi hàm sản phẩm sẽ làm mốc ĐỎ ở bước liên kết, và cả phép đo dừng trước khi
    vào vòng đột biến. Đo được hai lần trong hai nhiệm vụ liền (M4-01, M4-19) — và nó cũng là
    một việc còn mở đáng ghi, xem DEV-349.
    """
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "firmware" / "pid.h").write_text("#define NGUONG 480\n", "utf-8")
    (goc / "firmware" / "pid.c").write_text(
        '#include "pid.h"\nint pid(void){ return NGUONG + 12; }\n', "utf-8")
    (goc / "test" / "t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"a\\",\\"dat\\":true}]}'
        '\\n"); return 0; }\n', "utf-8")

    r = agent.registry.run("test.sensitivity", {"explain": _EX_DN, "nguon": ["firmware/pid.c"],
                                               "test": ["test/t.c"]}, _ctx_sp(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["tep"], f"mốc ĐỎ, chưa vào vòng đột biến: {r.data.get('note_vi', '')[:200]}"
    tep = r.data["tep"][0]
    assert tep["trang_thai"] != "khong_nap_duoc", (
        "include tương đối đứt sau khi sang bản sao — phép đo cáo buộc sai: " + str(tep))


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_mtime_tep_goc_khong_doi(make_agent):
    """TC-M4-19-04 — `test.sensitivity` không được CHẠM vào tệp sản phẩm, kể cả mtime.

    mtime là thứ `make` và mọi hệ dựng khác đọc. Một phép đo ghi rồi ghi lại y nguyên nội
    dung vẫn làm `make` dựng lại cả cây — và tệ hơn, nó làm mọi phép so "tệp có đổi không"
    của chính EIDE nói sai.
    """
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    sp = goc / "firmware" / "pid.c"
    sp.write_text("int pid(void){ return 480; }\n", "utf-8")
    (goc / "test" / "t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"a\\",\\"dat\\":true}]}'
        '\\n"); return 0; }\n', "utf-8")

    truoc = (sp.stat().st_mtime_ns, sp.read_bytes())
    r = agent.registry.run("test.sensitivity", {"explain": _EX_DN, "nguon": ["firmware/pid.c"],
                                               "test": ["test/t.c"]}, _ctx_sp(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["tep"], f"mốc ĐỎ, chưa vào vòng đột biến: {r.data.get('note_vi', '')[:200]}"
    # Có đi qua vòng đột biến thật: phép phá 0 áp được vào `480`, nên trạng thái không thể là
    # "không có chỗ nào để đột biến".
    assert "không có chỗ nào" not in r.data["tep"][0]["vi_sao"], r.data["tep"]
    assert (sp.stat().st_mtime_ns, sp.read_bytes()) == truoc, (
        "tệp sản phẩm bị ghi lại — mtime hoặc nội dung đã đổi")
    # Và không để lại vỏ rỗng: `.eide/mutate` tích thêm một thư mục mỗi `run_id` thì sau một
    # trăm lượt đo nó là một trăm thư mục rác trong dự án của người dùng.
    assert not (goc / ".eide" / "mutate").exists(), sorted(
        str(x) for x in (goc / ".eide" / "mutate").rglob("*"))


def test_buoc_NAP_dich_dung_noi_dung_tep_goc_tren_ban_sao(tmp_path):
    """Bản sao phải mang ĐÚNG nội dung tệp gốc — không thì bước nạp hỏi một câu khác.

    Bước nạp hỏi *"bộ kiểm có dịch nổi cùng tệp này không"*, và kết luận mạnh nhất của cả
    phép đo nằm ở đó: `khong_nap_duoc` nghĩa là **bộ kiểm chưa từng chạy một dòng nào** của
    tệp. Nếu bản sao rỗng thì lượt ấy dịch một tệp rỗng, luôn trót lọt, và kết luận ấy biến
    mất — thay bằng một ô xanh.
    """
    goc_van = "int nguong(void){ return 480; }\n"
    p = _tep(tmp_path, "sp.c", goc_van)
    tam = tmp_path / "tam"

    def chay(them):
        if them is None:
            return True, ""
        # Bộ kiểm trùng ký hiệu — nhưng chỉ khi tệp sản phẩm THẬT SỰ định nghĩa `nguong`.
        chu = them.read_text("utf-8")
        if "nguong" in chu:
            return False, "ld: duplicate symbol _nguong"
        return True, ""

    d = DB.do_do_nhay([p], chay, thu_muc_tam=tam)
    assert d["tep"][0]["trang_thai"] == "khong_nap_duoc", d["tep"]
    assert d["so_khong_nap"] == 1, d


def test_hai_tep_CUNG_TEN_khac_thu_muc_khong_pha_ban_sao_cua_nhau(tmp_path):
    """`bai1/dem.c` và `bai2/dem.c` phải có hai bản sao riêng.

    Gộp chúng vào một chỗ thì lượt đo của tệp sau ghi lên bản sao của tệp trước — và vì vòng
    đo trả tệp về trong `finally`, cái hỏng hiện ra thành một kết luận SAI về một trong hai
    tệp, không thành một lỗi ai thấy.
    """
    (tmp_path / "bai1").mkdir()
    (tmp_path / "bai2").mkdir()
    a = tmp_path / "bai1" / "dem.c"
    b = tmp_path / "bai2" / "dem.c"
    a.write_text("int a(void){ return 480; }\n", "utf-8")
    b.write_text("int b(void){ return 17; }\n", "utf-8")
    tam = tmp_path / "tam"
    thay: list = []

    def chay(them):
        if them is None:
            return True, ""
        chu = them.read_text("utf-8")
        thay.append((them.parent.name, chu.strip()))
        # Xanh khi nội dung còn nguyên; đỏ khi đã bị phá.
        return ("99999" not in chu), ""

    d = DB.do_do_nhay([a, b], chay, thu_muc_tam=tam)
    assert [x["trang_thai"] for x in d["tep"]] == ["thay", "thay"], d["tep"]
    # Mỗi tệp phải được dịch đúng NỘI DUNG của nó, không phải nội dung của tệp kia.
    cua_a = [c for _, c in thay if "int a(" in c]
    cua_b = [c for _, c in thay if "int b(" in c]
    assert cua_a and cua_b, thay
    assert len({t for t, _ in thay}) == 2, (
        "hai tệp cùng tên dùng CHUNG một thư mục bản sao: " + str(thay))


def test_ban_sao_cua_tep_TRUOC_da_bi_don_khi_do_tep_SAU(tmp_path):
    """Dọn từng tệp, không chỉ dọn một lần ở cuối.

    Một lượt đo 12 tệp firmware mà giữ cả 12 bản sao tới cuối là 12 lần dung lượng nằm trong
    `.eide/` của người dùng — và nếu lượt đo bị ngắt, chúng nằm lại hết. Phép dọn ở cuối
    không thay được phép dọn từng bước: cái ở cuối chỉ chạy khi có cái cuối.
    """
    (tmp_path / "d1").mkdir()
    (tmp_path / "d2").mkdir()
    a = tmp_path / "d1" / "a.c"
    b = tmp_path / "d2" / "b.c"
    a.write_text("int a(void){ return 480; }\n", "utf-8")
    b.write_text("int b(void){ return 17; }\n", "utf-8")
    tam = tmp_path / "tam"
    con_lai: list[list[str]] = []

    def chay(them):
        if them is None:
            return True, ""
        con_lai.append(sorted(x.name for x in tam.rglob("*.c")))
        return ("99999" not in them.read_text("utf-8")), ""

    DB.do_do_nhay([a, b], chay, thu_muc_tam=tam)
    assert con_lai, "không lần nào `chay` nhận tệp sản phẩm"
    # Ở lượt đo tệp thứ hai, bản sao của tệp thứ nhất phải đã biến mất.
    assert all("a.c" not in x for x in con_lai[2:]), con_lai
    assert con_lai[-1] == ["b.c"], con_lai


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_duong_tim_header_khong_che_header_HE_THONG(make_agent):
    """`-iquote`, không `-I`: thư mục firmware có `stdio.h` giả không được che bản hệ thống.

    Đo được ngày 08/10/2026 trên `du-lieu/rtos-sinhvien`: `firmware/` của nó có `stdio.h`
    riêng (chuyện thường của mã bare-metal), và `-I firmware` làm `#include <stdio.h>` của
    tệp test khớp vào bản giả — `FILE` thành *"use of undeclared identifier"*, và **11 trong
    12** tệp bị xếp là `khong_nap_duoc` (*"thiếu header của bo"*). Một cáo buộc sai với từng
    tệp, do đúng cái cờ tôi thêm vào để tránh một cáo buộc sai khác.

    `-iquote` chỉ đổi đường cho `#include "..."` — đúng và chỉ đúng phần mà bản sao làm đứt.
    """
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    # `stdio.h` giả của bo: có hàm in riêng, KHÔNG có FILE/fopen.
    (goc / "firmware" / "stdio.h").write_text("void bo_print(const char *s);\n", "utf-8")
    (goc / "firmware" / "pid.c").write_text(
        '#include "nguong.h"\nint pid(void){ return NGUONG + 12; }\n', "utf-8")
    (goc / "firmware" / "nguong.h").write_text("#define NGUONG 480\n", "utf-8")
    (goc / "test" / "t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ FILE *f = stdout; fprintf(f, "{\\"ca\\": '
        '[{\\"ten\\":\\"a\\",\\"dat\\":true}]}\\n"); return 0; }\n', "utf-8")

    r = agent.registry.run("test.sensitivity", {"explain": _EX_DN, "nguon": ["firmware/pid.c"],
                                               "test": ["test/t.c"]}, _ctx_sp(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["tep"], f"mốc ĐỎ: {r.data.get('note_vi', '')[:200]}"
    tep = r.data["tep"][0]
    assert tep["trang_thai"] != "khong_nap_duoc", (
        "đường tìm header che mất header hệ thống — cáo buộc sai: " + str(tep))


def test_thu_muc_tam_LONG_theo_run_id(tmp_path, monkeypatch):
    """Thư mục bản sao phải lồng theo `run_id`.

    Hai lượt đo chạy song song trên cùng dự án mà dùng chung `.eide/mutate/` sẽ ghi lên bản
    sao của nhau ở `mutate/0/<tên>`. Vòng đo trả tệp về trong `finally`, nên cái hỏng không
    hiện ra thành một lỗi — nó hiện ra thành một kết luận sai về một trong hai lượt.
    """
    from types import SimpleNamespace

    from eide.build import dot_bien as DBm
    from eide.tools import build_registry

    (tmp_path / "firmware").mkdir()
    (tmp_path / "test").mkdir()
    (tmp_path / "firmware" / "sp.c").write_text("int f(void){ return 480; }\n", "utf-8")
    (tmp_path / "test" / "t.c").write_text("int main(void){ return 0; }\n", "utf-8")

    bat: dict = {}
    monkeypatch.setattr(DBm, "do_do_nhay",
                        lambda *a, **k: bat.update(k) or {
                            "tep": [], "so_thay": 0, "so_khong_thay": 0, "so_khong_nap": 0,
                            "so_chua_do": 0, "so_mutant_khong_hop_le": 0})
    ctx = SimpleNamespace(
        config=SimpleNamespace(paths=SimpleNamespace(project_root=tmp_path)),
        run_id="run-abc",
        store=SimpleNamespace(get=lambda _m: None, apply=lambda **_k: None))
    sp = next(t for t in build_registry().all() if t.name == "test.sensitivity")
    sp.fn(ctx, explain=_EX_DN, nguon=["firmware/sp.c"], test=["test/t.c"])

    tam = bat.get("thu_muc_tam")
    assert tam is not None, bat
    assert tam.name == "run-abc", str(tam)
    assert tam.parent.name == "mutate", str(tam)


# ========== M4-04: đột biến TỪNG VỊ TRÍ, và một con số thay cho một câu nhị phân
#
# Chế độ cũ trả đúng một câu cho mỗi tệp: *"bộ kiểm có thấy tệp này không?"*. Câu ấy đủ để lật
# tẩy một ô xanh giả, và không đủ để làm gì tiếp: một tệp 400 dòng mà bộ kiểm chỉ canh một
# hằng số vẫn ra `thay` — "bộ kiểm BẮT ĐƯỢC" — y như một tệp được canh từng dòng.
#
# Hai chỗ chế độ cũ không nói được, và cả hai đã có người hỏi:
#   · `re.subn` đổi MỌI chỗ khớp cùng lúc, nên "đảo mọi phép `==` trong tệp" là một đột biến
#     duy nhất. Một bộ kiểm canh được **một** trong mười chỗ ấy là đủ để tệp thành `thay`.
#   · ca DANH-GIA §2.2: đổi `0xFFFFFFFD` thành `0` thì cả 4 ca vẫn xanh — mà hằng hex thì
#     `(?<![\w.])(\d{2,})` không chạm tới, nên phép đo cũ **không có** phép phá nào cho nó.

def test_liet_ke_moi_vi_tri_rieng():
    """TC-M4-04-01 — hai chỗ `==` là HAI đột biến, và `ap_mot` chỉ đổi một chỗ.

    `re.subn` của chế độ cũ gộp chúng thành một: bộ kiểm canh được một chỗ là cả tệp thành
    "bắt được", và chín chỗ kia không ai hỏi tới.
    """
    ma = "int f(int a,int b,int c,int d){ return (a==b) + (c==d); }\n"
    ds = [x for x in DB.liet_ke_dot_bien(ma) if "so sánh bằng" in x.mo_ta]
    assert len(ds) == 2, [(x.dong, x.truoc, x.sau) for x in DB.liet_ke_dot_bien(ma)]

    moi = DB.ap_mot(ma, ds[0])
    assert moi.count("!=") == 1 and moi.count("==") == 1, moi
    moi2 = DB.ap_mot(ma, ds[1])
    assert moi2 != moi, "hai đột biến khác vị trí mà cho ra cùng một mã"


def test_dot_bien_hang_hex():
    """TC-M4-04-02 — hằng hex phải có phép phá. Đây là ca DANH-GIA §2.2.

    `*(--sp) = 0xFFFFFFFDU;` là `EXC_RETURN` của ARM: sai giá trị này thì bo nổ `IBUSERR`
    ngay chu kỳ đầu. Bảng cũ không có phép nào chạm tới nó — `(?<![\\w.])(\\d{2,})(?![\\w.])`
    bị chặn bởi chữ `x` đứng trước, nên `0xFFFFFFFD` **không** phải "hằng số từ hai chữ số".
    """
    ma = "unsigned f(void){ return 0xFFFFFFFDU; }\n"
    ds = [x for x in DB.liet_ke_dot_bien(ma) if "hex" in x.mo_ta.lower()]
    assert ds, [x.mo_ta for x in DB.liet_ke_dot_bien(ma)]
    moi = DB.ap_mot(ma, ds[0])
    assert "0x0" in moi and "0xFFFFFFFD" not in moi, moi


def test_phep_moi_khong_doi_chi_so_cua_bon_phep_cu():
    """Bốn phép cũ phải giữ đúng chỉ số 0..3 — ca kiểm cũ gọi theo số.

    Và chế độ "tep" phải không đổi: `toi_da_phep` mặc định là 3, nên nó chỉ dùng phép 0..2.
    Thêm phép vào CUỐI bảng là cách duy nhất không chạm vào chuyện ấy.
    """
    assert len(DB._PHEP) >= 9, len(DB._PHEP)
    assert DB._PHEP[0][2] == "đổi mọi hằng số từ hai chữ số"
    assert DB._PHEP[1][2] == "đảo phép so sánh bằng"
    assert DB._PHEP[2][2] == "đảo phép so sánh nhỏ hơn"
    assert DB._PHEP[3][2] == "đổi cộng thành trừ"
    mo_ta_moi = [x[2] for x in DB._PHEP[4:]]
    assert any("hex" in x.lower() for x in mo_ta_moi), mo_ta_moi
    assert any("&&" in x or "logic" in x.lower() for x in mo_ta_moi), mo_ta_moi
    assert any("trả về" in x.lower() for x in mo_ta_moi), mo_ta_moi


def test_chi_tiet_tinh_diem_va_liet_ke_dot_bien_song(tmp_path):
    """TC-M4-04-03 — bộ kiểm chỉ canh hằng `480` thì điểm phải < 1, và dòng `==` phải SỐNG.

    Đây là câu mà chế độ cũ không nói được: tệp này ra `thay` — "bộ kiểm bắt được" — trong
    khi nó chỉ canh đúng một trong nhiều chỗ.
    """
    ma = "int f(int x,int y){ if (x==y) return 480; return 0; }\n"
    p = _tep(tmp_path, "sp.c", ma)

    def chay(them):
        if them is None:
            return True, ""
        chu = them.read_text("utf-8")
        # Bộ kiểm chỉ đọc hằng 480 — mọi đột biến khác nó không thấy.
        return ("480" in chu), ""

    d = DB.do_do_nhay([p], chay, muc="chi_tiet", thu_muc_tam=tmp_path / "tam")
    assert 0 < d["diem"] < 1, d
    assert d["so_mutant"] > d["so_bat"], d
    dong_song = [x for x in d["song"] if "==" in x["truoc"] or "!=" in x["sau"]]
    assert dong_song, d["song"]
    assert all({"tep", "dong", "phep", "truoc", "sau"} <= set(x) for x in d["song"]), d["song"]


def test_che_do_tep_giu_nguyen_ket_qua(tmp_path):
    """TC-M4-04-04 — không nêu `muc` thì khoá trả về y như cũ, KHÔNG có `diem`.

    Mọi ca cũ của tệp này và mọi lượt `test.sensitivity` đang chạy đi đường ấy. Thêm một khoá
    vào chế độ mặc định là đổi thứ bên gọi đọc — và `loi_nguoi_doc` đọc theo khoá.
    """
    p = _tep(tmp_path, "sp.c", "int nguong(void){ return 480; }\n")
    d = DB.do_do_nhay([p], lambda them: (True, "") if them is None
                      else ("480" in them.read_text("utf-8"), ""))
    assert "diem" not in d, sorted(d)
    assert "song" not in d, sorted(d)
    assert d["tep"][0]["trang_thai"] == "thay", d["tep"]
    assert set(d) == {"tep", "so_thay", "so_khong_thay", "so_khong_nap", "so_chua_do",
                      "so_mutant_khong_hop_le", "bo_kiem_xanh_luc_dau"}, sorted(d)


def test_lay_mau_tat_dinh_theo_seed(tmp_path):
    """TC-M4-04-05 — nhiều vị trí hơn trần thì lấy mẫu, và lấy mẫu phải TẤT ĐỊNH.

    Một phép đo cho hai con số khác nhau trên cùng mã nguồn thì không ai đối chiếu được lượt
    này với lượt trước — và "điểm đột biến tụt" sẽ bị đọc thành "bộ kiểm tệ đi".
    """
    ma = "int f(void){ int s=0;\n" + "".join(f"  s += {10 + i};\n" for i in range(60)) \
         + "  return s; }\n"
    p = _tep(tmp_path, "sp.c", ma)

    def _chay_het(seed):
        thay: list[int] = []

        def chay(them):
            if them is None:
                return True, ""
            chu = them.read_text("utf-8")
            thay.append(chu.count("99999"))
            return True, ""                     # bộ kiểm không canh gì — mọi mutant SỐNG

        DB.do_do_nhay([p], chay, muc="chi_tiet", toi_da_moi_tep=10, seed=seed,
                      thu_muc_tam=tmp_path / f"tam{seed}")
        return thay

    a, b = _chay_het(0), _chay_het(0)
    assert a == b, (a, b)
    # Trần được tôn trọng: 1 lượt nạp + 10 lượt đột biến.
    assert len(a) == 11, len(a)


def test_chi_tiet_KHONG_tinh_stillborn_vao_mau_so(tmp_path):
    """Điểm đột biến = bắt / (đã thử − stillborn). Mutant không dịch được nằm NGOÀI mẫu số.

    Để nó trong mẫu số là kéo điểm xuống vì một lý do không nói gì về bộ kiểm — và đó đúng
    cái lỗi M4-05 vừa sửa ở chế độ theo tệp, chỉ khác là lần này nó hiện ra thành một con số.
    """
    ma = "int f(int x){ if (x==1) return 480; return 0; }\n"
    p = _tep(tmp_path, "sp.c", ma)

    def chay(them):
        if them is None:
            return True, ""
        chu = them.read_text("utf-8")
        if "99999" in chu:
            return False, DB.TIEN_TO_BIEN_DICH + "error: hằng quá lớn"
        return ("480" in chu), ""

    d = DB.do_do_nhay([p], chay, muc="chi_tiet", thu_muc_tam=tmp_path / "tam")
    assert d["so_stillborn"] >= 1, d
    assert d["diem"] == d["so_bat"] / (d["so_mutant"] - d["so_stillborn"]), d
    assert not any("99999" in x["sau"] for x in d["song"]), (
        "mutant không dịch được bị xếp là SỐNG — nó chưa bao giờ chạy")


def test_chi_tiet_khong_co_mutant_nao_thi_diem_la_None(tmp_path):
    """Không phá được chỗ nào thì điểm là `None`, không phải `0.0`.

    `0.0` đọc thành "bộ kiểm không bắt được gì" — một cáo buộc. Cái đúng là "chưa biết", và
    đó là cùng một nguyên tắc với bốn trạng thái của chế độ theo tệp.
    """
    p = _tep(tmp_path, "rong.c", "void f(void){}\n")
    d = DB.do_do_nhay([p], lambda them: (True, ""), muc="chi_tiet",
                      thu_muc_tam=tmp_path / "tam")
    assert d["diem"] is None, d
    assert d["so_mutant"] == 0, d


def test_mien_khoa_plan_mode_la_CO_CHU_Y_va_co_ly_do():
    """`test.sensitivity` được miễn khoá plan mode — và chỗ miễn phải là danh sách CÓ CHỦ Ý.

    `cong_cu_bi_khoa` lấy từ **hợp đồng** của công cụ (`writes_artefact`, `risk`), không từ
    một danh sách tên — nên khi M4-04 cho nó ghi hiện vật thì nó tự động bị khoá. Luật ấy
    đúng, và nó cũng là lý do `KHONG_KHOA` tồn tại: `memory.note` vào đó vì khoá nó trong lúc
    soạn kế hoạch là cấm tác tử ghi lại thứ nó vừa học để soạn kế hoạch ấy.

    `test.sensitivity` cùng hình dạng: nó là một phép ĐO, không phải một thay đổi thiết kế.
    Khoá nó là cấm tác tử biết bộ kiểm hiện tại canh được những gì — đúng thứ nó cần để soạn
    một kế hoạch sửa.

    Ca này canh chuyện miễn ấy nằm trong danh sách CÓ CHỦ Ý, không nằm trong một `if` nào đó
    nới luật chung cho mọi công cụ R1.
    """
    from eide.ke_hoach import KHONG_KHOA, cong_cu_bi_khoa
    from eide.tools import build_registry

    reg = build_registry()
    assert "test.sensitivity" in KHONG_KHOA
    assert not cong_cu_bi_khoa(reg.get("test.sensitivity"))
    # Luật chung KHÔNG được nới: một công cụ R1 khác có `writes_artefact` vẫn phải bị khoá.
    khac = [t for t in reg.all()
            if t.writes_artefact and t.name not in KHONG_KHOA and str(t.risk) < "R3"]
    assert khac, "không còn công cụ nào để đối chiếu — ca này mất tác dụng"
    assert all(cong_cu_bi_khoa(t) for t in khac), [t.name for t in khac[:5]]


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_tai_hien_DANH_GIA_2_2_mutant_EXC_RETURN_phai_SONG(tmp_path):
    """Tiêu chí xong của M4-04, đo trên hiện vật THẬT: `0xFFFFFFFD` → `0` thì bộ kiểm vẫn xanh.

    Ca DANH-GIA §2.2: sau khi bộ kiểm xanh 4/4, Agent **tự khai** *"2 trong 4 ca bộ kiểm không
    bắt được"*, kèm dự đoán *"lỗi này nạp lên bo thật sẽ nổ HardFault ngay chu kỳ đầu"*. Người
    kiểm lại bằng tay — đổi `0xFFFFFFFD` thành `0`, dịch lại, cả 4 ca vẫn xanh. Rồi bo nổ đúng
    `IBUSERR` ở đúng chỗ ấy.

    Ba điều ca này chốt:

    * **bảng phép CŨ không có đột biến nào cho hằng hex** — `(?<![\\w.])(\\d{2,})(?![\\w.])` bị
      chặn bởi chữ `x`, nên phép đo cũ về mặt cấu trúc *không thể* thấy chỗ này;
    * bảng mới thấy nó, ở đúng dòng 147 của `control_rtos.c` thật;
    * áp vào rồi chạy bộ kiểm thật thì mutant **SỐNG** — tức điểm mù mà Agent tự khai hôm ấy
      nay đo được bằng máy, không cần một người ngồi sửa tay rồi dịch lại.

    Chạy trên bản sao trong `tmp_path`; `du-lieu/` không bị chạm.
    """
    import shutil
    import subprocess

    goc_du_an = Path(__file__).resolve().parents[1] / "du-lieu" / "rtos-sinhvien"
    if not (goc_du_an / "firmware" / "control_rtos.c").is_file():
        pytest.skip("không có hiện vật rtos-sinhvien")

    du_an = tmp_path / "du-an"
    shutil.copytree(goc_du_an, du_an, symlinks=True)
    sp = du_an / "firmware" / "control_rtos.c"
    tt = du_an / "test" / "test_rtos.c"
    goc_van = sp.read_text("utf-8")
    assert "0xFFFFFFFDU" in goc_van, "hiện vật đã đổi — đọc lại ca này trước khi sửa"

    # (1) bảng CŨ mù hẳn với hằng hex.
    assert not [x for x in DB.liet_ke_dot_bien(goc_van, bang=DB._PHEP[:4])
                if "0xFFFFFFFD" in x.truoc]

    # (2) bảng MỚI thấy, và nói đúng dòng.
    ds = [x for x in DB.liet_ke_dot_bien(goc_van) if "0xFFFFFFFD" in x.truoc]
    assert ds, "bảng mới vẫn không có phép nào cho hằng hex"
    assert any(x.dong == 147 for x in ds), [(x.dong, x.mo_ta) for x in ds]
    assert any("0x0" in x.sau for x in ds), [x.sau for x in ds]

    cc = shutil.which("cc") or shutil.which("clang") or shutil.which("gcc")

    def chay() -> bool:
        ra = du_an / "chay"
        r = subprocess.run([cc, "-O0", "-std=c11", "-DEIDE_TEST=1", "-o", str(ra), str(tt)],
                           capture_output=True, text=True, cwd=str(du_an))
        if r.returncode != 0:
            return False
        return subprocess.run([str(ra)], capture_output=True, text=True,
                              cwd=str(du_an)).returncode == 0

    assert chay(), "mốc đã ĐỎ — chưa đo được gì"
    db = next(x for x in ds if x.dong == 147)
    try:
        sp.write_text(DB.ap_mot(goc_van, db), "utf-8")
        van_xanh = chay()
    finally:
        sp.write_text(goc_van, "utf-8")

    assert van_xanh, (
        "mutant BỊ BẮT — khác claim của DANH-GIA §2.2. Đọc lại trước khi sửa ca này: hoặc bộ "
        "kiểm đã được siết, hoặc claim cũ sai.")
    assert sp.read_text("utf-8") == goc_van


def test_liet_ke_khong_dung_ca_tep_cho_moi_cho_khop(tmp_path):
    """Liệt kê phải RẺ: một tệp bitmap thật có hàng vạn chỗ khớp.

    Đo được 09/10/2026: `du-lieu/rtos-sinhvien/firmware/logo_ptit.c` là **720 KB** với
    **57 600** chỗ khớp phép hằng hex. Bản đầu của `liet_ke_dot_bien` dựng một bản 720 KB rồi
    chạy một lượt regex bỏ che cho **từng** chỗ — khoảng 41 GB việc chuỗi. Phép đo **treo**,
    không đổ, nên nó trông như một lượt chạy lâu chứ không như một lỗi: `test.sensitivity` mức
    chi tiết chạy quá 10 phút trên một tệp và bị tôi giết.

    Tệp dựng ở đây phải giống tệp thật ở một chỗ: **chú thích trên mỗi dòng**. Bản đầu của ca
    này dùng hằng hex trần, và nó KHÔNG bắt được bản chậm — vì `_bo_che` trả về ngay khi
    không có chỗ giữ nào. Chính các chú thích mới làm mỗi lượt bỏ che thành một lượt regex
    thật. Đo 09/10/2026 trên tệp 150 KB với 8 000 chú thích: bản nhanh **0,04 s**, bản chậm
    **≈ 21 s**. Trần 5 s nằm giữa, rộng cả hai phía.
    """
    import time

    ma = ("const unsigned d[] = {\n"
          + "".join(f"  0x{i & 0xFF:02X}, //  ##{i}\n" for i in range(8000)) + "};\n")
    t0 = time.monotonic()
    ds = DB.liet_ke_dot_bien(ma, toi_da=30, seed=0)
    giay = time.monotonic() - t0

    assert len(ds) == 30, len(ds)
    assert giay < 5.0, f"liệt kê mất {giay:.1f} s — đang dựng cả tệp cho mỗi chỗ khớp"
    # Và lấy mẫu vẫn phải tất định.
    assert [(x.dong, x.truoc) for x in ds] == [
        (x.dong, x.truoc) for x in DB.liet_ke_dot_bien(ma, toi_da=30, seed=0)]
    # Danh sách trả về theo THỨ TỰ TRONG TỆP. Lấy mẫu xong mà không sắp lại thì người đọc
    # "những dòng bộ kiểm không canh" phải nhảy ngược nhảy xuôi trong tệp — một bản báo cáo
    # đúng về dữ liệu và khó đọc.
    assert [x.dong for x in ds] == sorted(x.dong for x in ds), [x.dong for x in ds]


def test_so_dong_dung_khi_co_CHU_THICH_NHIEU_DONG():
    """Số dòng phải là số dòng người mở tệp ra sẽ thấy.

    Toạ độ trong bản đã che KHÔNG trùng toạ độ mã gốc: một chú thích `/* … */` ba dòng co lại
    thành một chỗ giữ không có dòng mới nào. Thiếu bản đồ đoạn thì số dòng báo ra lệch đúng ở
    những tệp có nhiều chú thích — tức là mọi tệp thật.
    """
    ma = ("int a(void){ return 1; }\n"
          "/* chú thích\n"
          "   dài ba\n"
          "   dòng */\n"
          "int f(int x,int y){ if (x==y) return 7; return 0; }\n")
    ds = [x for x in DB.liet_ke_dot_bien(ma) if "so sánh bằng" in x.mo_ta]
    assert len(ds) == 1, [(x.dong, x.mo_ta) for x in DB.liet_ke_dot_bien(ma)]
    assert ds[0].dong == 5, (ds[0].dong, ds[0].truoc)
    assert "if (x==y)" in ds[0].truoc, ds[0].truoc
    assert "if (x!=y)" in ds[0].sau, ds[0].sau


def test_phep_doi_gia_tri_tra_ve():
    """`return <biểu thức>;` → `return 0;` — và KHÔNG chạm `return 0;` sẵn có.

    Phép này bắt được chuyện bộ kiểm chỉ xem *hàm có chạy không* mà không xem *nó trả về gì*.
    Và nó phải bỏ qua `return 0;`: một đột biến không đổi gì mà bộ kiểm "không bắt được" là
    một cáo buộc sai.
    """
    ds = DB.liet_ke_dot_bien("int f(int x){ return x * 3; }\n")
    tra = [x for x in ds if "trả về" in x.mo_ta]
    assert len(tra) == 1, [(x.mo_ta, x.truoc) for x in ds]
    assert "return 0;" in DB.ap_mot("int f(int x){ return x * 3; }\n", tra[0])

    # `return 0;` sẵn có: không sinh đột biến nào của phép này.
    assert not [x for x in DB.liet_ke_dot_bien("int f(void){ return 0; }\n")
                if "trả về" in x.mo_ta]


def test_bo_muc_dot_bien_KHONG_doi_gi():
    """`0x0` gặp phép hằng hex thì ra `0x0` — không đổi gì, phải bị bỏ.

    Giữ nó lại là đưa vào mẫu số một phép phá không đổi hành vi: điểm đột biến tụt xuống vì
    một mutant mà **không bộ kiểm nào** bắt được, kể cả một bộ kiểm hoàn hảo.
    """
    ds = DB.liet_ke_dot_bien("int f(void){ return 0x0; }\n")
    assert not [x for x in ds if "hex" in x.mo_ta], [(x.truoc, x.sau) for x in ds]
    # Ca âm: một hằng hex KHÁC 0 thì vẫn sinh đột biến.
    assert [x for x in DB.liet_ke_dot_bien("int f(void){ return 0x1F; }\n")
            if "hex" in x.mo_ta]


def test_muc_la_thi_NEM_LOI_chu_khong_im_lang_chay_nhu_tep(tmp_path):
    """`muc` lạ phải ném `ValueError`, không được im lặng chạy chế độ mặc định.

    Im lặng ở đây là tệ nhất trong ba cách: tác tử gõ `muc="chitiet"` rồi đọc một kết quả
    **không có** `diem`, và kết luận "phép đo này không tính được điểm" — một kết luận sai về
    công cụ, sinh ra từ một lỗi chính tả.
    """
    p = _tep(tmp_path, "sp.c", "int f(void){ return 480; }\n")
    with pytest.raises(ValueError, match="chi_tiet"):
        DB.do_do_nhay([p], lambda them: (True, ""), muc="chitiet")


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_cong_cu_truyen_muc_xuong_VA_ghi_hien_vat(make_agent):
    """Công cụ phải truyền `muc` xuống, và phải GHI hiện vật.

    Hai chỗ hỏng khác nhau mà cùng vô hình: một tham số không được truyền thì tác tử gọi
    `muc="chi_tiet"` và nhận lại kết quả chế độ tệp; một phép đo không vào kho thì con số nó
    tìm ra tắt theo lượt, nên lượt sau không ai biết nó từng xảy ra (xem DEV-341 cho cùng mẫu).
    """
    agent = make_agent([])
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "firmware" / "sp.c").write_text(
        "int nguong(void){ return 480; }\nint khac(int x){ return x == 1; }\n", "utf-8")
    (goc / "test" / "t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": [{\\"ten\\":\\"a\\",\\"dat\\":true}]}\\n");'
        ' return 0; }\n', "utf-8")

    r = agent.registry.run("test.sensitivity", {
        "explain": _EX_DN, "muc": "chi_tiet",
        "nguon": ["firmware/sp.c"], "test": ["test/t.c"]}, _ctx_sp(agent))
    assert r.ok, getattr(r.error, "message_vi", "")
    assert "diem" in r.data, sorted(r.data)
    assert r.data["so_mutant"] > 0, r.data

    a = agent.store.get("sim_result:test-sensitivity")
    assert a is not None, "phép đo không vào kho — lượt sau không ai biết nó từng xảy ra"
    c = a["canonical"]
    assert c["muc"] == "chi_tiet" and "diem" in c, sorted(c)
