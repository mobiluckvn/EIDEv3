# -*- coding: utf-8 -*-
"""M3-18 — kiểm ràng buộc chân FPGA (`.cst`) với cổng mô-đun đỉnh và chân của kit.

Vì sao năng lực này tồn tại, đo được trên dữ liệu thật trong `du-lieu/`:

`dat_di_day` trước đây chỉ hỏi *"tệp `.cst` có tồn tại không"*. Nếu một cổng của mô-đun đỉnh
không có `IO_LOC`, nextpnr **không đổ** — nó tự chọn một chân còn trống. Bitstream dựng xong,
mọi chặng báo đạt, và mạch thì nối sai chân. Đó là ô xanh giả tốn nhất của cả đường FPGA: nó
chỉ hiện ra khi cắm bo lên và thấy đèn không sáng, hoặc không hiện ra bao giờ.

Phép kiểm này đứng TRƯỚC nextpnr, vì sau nextpnr thì không còn gì để chặn.
"""

import json

import pytest

from eide.knowledge import cst as C

# Lấy nguyên hằng `CST` mà tests/test_hdl.py đang dùng: cùng một tệp ràng buộc thì hai bộ ca
# kiểm nói về cùng một hiện vật, và không ai phải sửa hai chỗ khi nó đổi.
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

CONG_KHOP = ["clk"] + [f"led[{i}]" for i in range(6)]


def test_doc_cst_mau():
    """TC-M3-18-01 — đọc được `IO_LOC` và `IO_PORT`, giữ nguyên tên dạng `led[5]`."""
    d = C.doc_cst(CST)
    assert d["loc"]["led[5]"] == "20", d["loc"]
    assert d["loc"]["clk"] == "4", d["loc"]
    assert d["io"]["clk"]["IO_TYPE"] == "LVCMOS33", d["io"]
    assert d["io"]["clk"]["PULL_MODE"] == "UP", d["io"]
    assert not d["loi_cu_phap"], d["loi_cu_phap"]


def test_cong_thieu_rang_buoc_bi_chan():
    """TC-M3-18-02 — cổng không có `IO_LOC` là **blocker**, không phải cảnh báo.

    Đây là chính cái lỗi nextpnr im lặng cho qua: thiếu ràng buộc thì nó tự chọn chân.
    """
    pt = C.kiem(C.doc_cst(CST), CONG_KHOP + ["uart_tx"], {})
    thieu = [p for p in pt if p["loai"] == "thieu_rang_buoc"]
    assert len(thieu) == 1, pt
    assert thieu[0]["ten"] == "uart_tx", thieu[0]
    assert thieu[0]["muc"] == "blocker", thieu[0]


def test_trung_chan_bi_chan():
    """TC-M3-18-03 — hai cổng cùng một chân là blocker: phần cứng không làm được thế."""
    pt = C.kiem(C.doc_cst(CST + 'IO_LOC "x" 15;\n'), CONG_KHOP + ["x"], {})
    trung = [p for p in pt if p["loai"] == "trung_chan"]
    assert len(trung) == 1, pt
    assert trung[0]["muc"] == "blocker", trung[0]
    assert set(trung[0]["ten_cac_cong"]) == {"led[0]", "x"}, trung[0]
    assert trung[0]["chan"] == "15", trung[0]


def test_cst_khop_khong_bao():
    """TC-M3-18-04 — ca âm: cổng khớp đúng CST, không có Fact kit → **không** blocker.

    Thiếu Fact chân kit thì bỏ phần đối chiếu kit, KHÔNG đoán bản đồ chân. Một phép kiểm
    bịa ra bản đồ chân rồi chặn đường dựng còn tệ hơn không có phép kiểm nào.
    """
    pt = C.kiem(C.doc_cst(CST), CONG_KHOP, {})
    assert not [p for p in pt if p["muc"] == "blocker"], pt
    assert any(p["loai"] == "chua_co_fact_chan_kit" for p in pt), (
        "không nói ra rằng phần đối chiếu kit đã bị bỏ — im lặng ở đây là nói rằng đã kiểm")


def test_rang_buoc_thua_bi_bao_major():
    """Ràng buộc cho một tên không phải cổng: `major`, không chặn.

    Không chặn vì một tệp `.cst` của cả kit, dùng cho nhiều thiết kế, thì **đương nhiên** có
    chân mà thiết kế này không dùng. Nhưng cũng không im: một tên thừa cũng có thể là một
    cổng viết sai chính tả, và lúc ấy nó đi cặp với một `thieu_rang_buoc`.
    """
    pt = C.kiem(C.doc_cst(CST), [c for c in CONG_KHOP if c != "led[5]"], {})
    thua = [p for p in pt if p["loai"] == "rang_buoc_thua"]
    assert [p["ten"] for p in thua] == ["led[5]"], pt
    assert thua[0]["muc"] == "major", thua[0]
    assert not [p for p in pt if p["muc"] == "blocker"], pt


def test_cong_tu_json_tach_bus():
    """`cong_tu_json` tách bus thành `ten[i]`, bus 1 bit giữ tên trần.

    `.cst` khai từng bit (`led[0]` … `led[5]`), còn JSON yosys khai một cổng `led` 6 bit. Nếu
    không tách, mọi bus đều báo "thiếu ràng buộc" và phép kiểm thành vô dụng ngay lượt đầu.
    """
    j = {"modules": {"dinh": {"ports": {
        "clk": {"direction": "input", "bits": [2]},
        "led": {"direction": "output", "bits": [3, 4, 5, 6, 7, 8]}}}}}
    assert C.cong_tu_json(j, "dinh") == ["clk", "led[0]", "led[1]", "led[2]", "led[3]",
                                         "led[4]", "led[5]"]


def test_cong_tu_json_khong_co_mo_dun_dinh():
    """Không có mô-đun đỉnh trong JSON thì nói ra, không trả danh sách rỗng.

    Rỗng sẽ được đọc thành "mô-đun đỉnh không có cổng nào", và một thiết kế không cổng thì
    mọi phép kiểm đều xanh — ô xanh giả ngay trong công cụ đi tìm ô xanh giả.
    """
    with pytest.raises(KeyError):
        C.cong_tu_json({"modules": {"khac": {"ports": {}}}}, "dinh")


def test_doc_cst_noi_ra_dong_khong_doc_duoc():
    """Dòng sai cú pháp phải vào `loi_cu_phap`, không bị bỏ qua im lặng."""
    d = C.doc_cst('IO_LOC "clk" 4;\nIO_LOC clk_khong_ngoac 9;\nIO_LOC "a";\n')
    assert d["loc"] == {"clk": "4"}, d["loc"]
    assert len(d["loi_cu_phap"]) == 2, d["loi_cu_phap"]


def test_doc_cst_bo_qua_chu_thich():
    """`//` là chú thích của `.cst` thật — trong đó có cả `IO_LOC` bị tắt đi."""
    d = C.doc_cst('// IO_LOC "cu" 1;\nIO_LOC "clk" 4;   // chân 27 MHz\n')
    assert d["loc"] == {"clk": "4"}, d["loc"]
    assert not d["loi_cu_phap"], d["loi_cu_phap"]


# =========================================================== đối chiếu với Fact chân của kit

FACT_KIT = {
    "4": {"chuc_nang": "CLK_27MHZ"},
    "15": {"chuc_nang": "LED0"},
    "16": {"chuc_nang": "LED1"},
}


def test_chan_lech_kit_bao_major_kem_trich_dan():
    """Fact nói chân 15 là LED0, mà thiết kế gán `clk` vào đó → `chan_lech_kit`."""
    xau = CST.replace('IO_LOC "clk" 4;', 'IO_LOC "clk" 15;').replace(
        'IO_LOC "led[0]" 15;', 'IO_LOC "led[0]" 4;')
    pt = C.kiem(C.doc_cst(xau), CONG_KHOP, FACT_KIT)
    lech = [p for p in pt if p["loai"] == "chan_lech_kit"]
    assert {p["ten"] for p in lech} == {"clk", "led[0]"}, pt
    assert all(p["muc"] == "major" for p in lech), lech
    assert all(p.get("fact") for p in lech), "không mang theo Fact để người kiểm lại được"


def test_chan_khop_fact_kit_thi_im():
    """Ca âm của phép trên: gán đúng theo Fact thì không báo gì."""
    pt = C.kiem(C.doc_cst(CST), CONG_KHOP, FACT_KIT)
    assert not [p for p in pt if p["loai"] == "chan_lech_kit"], pt
    assert not [p for p in pt if p["loai"] == "chua_co_fact_chan_kit"], pt


def test_io_type_lech_bank_bi_chan():
    """`IO_TYPE=LVCMOS18` trên bank cấp 3,3 V là blocker — mức điện không khớp."""
    pt = C.kiem(C.doc_cst(CST.replace("LVCMOS33", "LVCMOS18")), CONG_KHOP,
                {"4": {"chuc_nang": "CLK_27MHZ", "bank": "1", "vccio": "3.3"}})
    lech = [p for p in pt if p["loai"] == "io_type_lech_bank"]
    assert len(lech) == 1, pt
    assert lech[0]["muc"] == "blocker", lech[0]
    assert lech[0]["ten"] == "clk", lech[0]


def test_io_type_khop_bank_thi_im():
    pt = C.kiem(C.doc_cst(CST), CONG_KHOP,
                {"4": {"chuc_nang": "CLK_27MHZ", "bank": "1", "vccio": "3.3"}})
    assert not [p for p in pt if p["loai"] == "io_type_lech_bank"], pt


# ============================================================== chạy trên tệp `.cst` THẬT
#
# Bảy tệp `.cst` trong `du-lieu/` và `docs/` là hiện vật của những lượt dựng đã chạy trên bo
# thật. Một phép kiểm chỉ chạy trên tệp do chính ca kiểm dựng ra thì chưa chứng minh được nó
# đọc nổi tệp người ta viết.

def _cac_cst_that():
    """MỌI tệp `.cst` trong repo, không chỉ những tệp nằm ở `*/constraints/`.

    Bản đầu của hàm này chỉ quét `du-lieu/*/constraints/` và `docs/*/constraints/` — và thu
    **4 trong 7** tệp. Ba tệp bị bỏ nằm sâu hơn một bậc (`docs/fpga/phien-sinhvien-*/`) hoặc
    nằm cạnh RTL (`phien-bo-that-03-10/rtl/`). Một phép quét bỏ sót gần một nửa hiện vật mà
    vẫn xanh thì câu "mọi tệp `.cst` thật đều đọc được" nói về phần nó quét, không về repo.
    """
    from pathlib import Path
    goc = Path(__file__).resolve().parents[1]
    return sorted(p for p in goc.glob("**/*.cst") if ".venv" not in p.parts)


@pytest.mark.parametrize("duong", _cac_cst_that(),
                         ids=lambda p: str(p).rsplit("EIDE_v3/", 1)[-1])
def test_doc_duoc_moi_cst_that_trong_repo(duong):
    """Mọi tệp `.cst` thật trong repo phải đọc được, 0 dòng sai cú pháp."""
    d = C.doc_cst(duong.read_text("utf-8"))
    assert d["loc"], f"{duong}: không đọc ra ràng buộc nào"
    assert not d["loi_cu_phap"], f"{duong}: {d['loi_cu_phap']}"
    # Mỗi tên có IO_LOC thì thường có IO_PORT kèm; không bắt buộc, nhưng tên trong IO_PORT mà
    # không có IO_LOC thì chắc chắn là lỗi chính tả — ràng buộc điện không có chân để gắn.
    mo_coi = sorted(set(d["io"]) - set(d["loc"]))
    assert not mo_coi, f"{duong}: IO_PORT không có IO_LOC: {mo_coi}"


def test_cst_that_khop_cong_cua_soc_top_that():
    """`soc_top` thật + `.cst` thật: không blocker, và nói ra đúng hai ràng buộc thừa.

    `btn_s2` và `uart_rx` có trong `.cst` của kit mà `soc_top` không dùng — đúng hình dạng
    "tệp ràng buộc của cả kit, dùng cho nhiều thiết kế". Đó là `major`, không chặn.
    """
    from pathlib import Path
    goc = Path(__file__).resolve().parents[1]
    du_an = goc / "du-lieu" / "riscv-tn20k-b"
    tep_cst = du_an / "constraints" / "tangnano20k.cst"
    tep_json = du_an / ".eide" / "hdl" / "soc_top.json"
    if not (tep_cst.is_file() and tep_json.is_file()):
        pytest.skip("không có hiện vật thật của riscv-tn20k-b")

    cong = C.cong_tu_json(json.loads(tep_json.read_text("utf-8")), "soc_top")
    pt = C.kiem(C.doc_cst(tep_cst.read_text("utf-8")), cong, {})
    assert not [p for p in pt if p["muc"] == "blocker"], pt
    thua = sorted(p["ten"] for p in pt if p["loai"] == "rang_buoc_thua")
    assert thua == ["btn_s2", "uart_rx"], pt
