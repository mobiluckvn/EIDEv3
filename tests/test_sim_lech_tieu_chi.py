# -*- coding: utf-8 -*-
"""DEV-336 — `sim.run` đem số đo của một chương trình so với tiêu chí của chương trình khác.

Đo được trên phiên robot ngày 04/10/2026. Hiện vật `sim_result:can-bang` bản 8 ghi
`ma_tieu_chi = "sim-01"` (bộ tiêu chí đòi mười mã `A1`–`A10`) với số đo `{"C1": 0, "C2": 0}`
(của bộ `sim-ntc`, hai mã), và `dat = False`.

Hai thứ mặc định gặp nhau là ra chuyện:

- `ma_tieu_chi` mặc định `"sim-01"` — nên lượt chạy cho bộ tiêu chí thứ hai mà không nêu rõ
  thì lặng lẽ dùng bộ thứ nhất;
- `nguon` bỏ trống thì lấy **mọi** tệp `sim/*.c` — nên chỉ cần thêm một chương trình mô phỏng
  thứ hai là lượt sau đo thứ khác;
- và kết quả ghi vào **một mã hiện vật duy nhất**, nên bản sau đè bản trước.

Hậu quả không phải một lỗi kêu lên, mà là **sở cứ nói ngược báo cáo**: tác tử báo 10/10 đạt —
và nó báo đúng, nó đã chạy thật — còn hiện vật lưu lại nói không đạt. Người đọc sở cứ về sau
thấy `dat: False` mà không có cách nào biết đó là *sai cặp tiêu chí/nguồn* chứ không phải *sản
phẩm sai*.

Hai chuyện ấy dẫn tới hai việc ngược nhau: một cái bảo đi sửa mã, cái kia bảo gọi lại cho
đúng. Nên chỗ này phải **chặn**, không được trả về `dat: False`.
"""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from eide.build import tieu_chi as TCM      # noqa: E402


def _tc(ma: str, cac_ma: list[str]) -> TCM.TieuChi:
    return TCM.TieuChi.from_dict({
        "ma": ma, "ten": f"tiêu chí {ma}", "da_xac_nhan": True, "timeout_s": 5,
        "assert": [{"ma": m, "mo_ta": f"ô {m}", "phep_so": "==", "nguong": 1.0,
                    "nguon_nguong": "bảng của người"} for m in cac_ma],
    })


def test_khong_khoa_nao_trung_thi_moi_assert_la_CHUA_DO_DUOC_khong_phai_KHONG_DAT():
    """Phân biệt *chưa đo được* với *đo rồi mà sai* — hai cái dẫn tới hai việc khác nhau.

    Nếu `xet_ket_qua` xếp chúng vào `khong_dat` thì không ai phân biệt được nữa, và chốt ở
    `sim.run` cũng không dựng được.
    """
    xet = TCM.xet_ket_qua(_tc("sim-01", ["A1", "A2", "A3"]), {"C1": 0, "C2": 0})
    assert xet["dem"]["chua_do_duoc"] == 3, (
        f"ba assert không có số đo phải là 'chưa đo được', nhận {xet['dem']}")
    assert xet["dem"]["khong_dat"] == 0, (
        "không được xếp 'thiếu số đo' thành 'đo rồi mà sai'")
    assert not xet["dat"]


def test_so_do_thua_duoc_ke_ra():
    """Số đo mà không ai đặt tiêu chí cũng là một dấu hiệu — nó nói hai bên đang nói hai thứ."""
    xet = TCM.xet_ket_qua(_tc("sim-01", ["A1"]), {"C1": 0, "C2": 0})
    assert xet["so_do_thua"] == ["C1", "C2"], (
        f"phải kê số đo thừa để người đọc thấy hai bên lệch nhau, nhận {xet['so_do_thua']}")


def test_khoa_trung_mot_phan_thi_KHONG_bi_chan():
    """Nửa đối — chốt chỉ nhắm vào ca **không một khoá nào** trùng.

    Trùng một phần là chuyện bình thường: chương trình đo được vài ô, vài ô còn lại chưa đo.
    Nếu chốt nổ ở đây thì nó chặn cả việc làm từng phần, và người ta sẽ tắt chốt.
    """
    tc = _tc("sim-01", ["A1", "A2", "A3"])
    do = {"A1": 1.0}
    assert set(do) & {a.ma for a in tc.asserts}, (
        "ca này PHẢI có khoá trùng, không thì nó không còn là nửa đối")
    xet = TCM.xet_ket_qua(tc, do)
    assert xet["dem"]["dat"] == 1 and xet["dem"]["chua_do_duoc"] == 2


def test_dieu_kien_chan_dung_dung_cho_ca_lech_hoan_toan():
    """Chính điều kiện mà `sim.run` dùng để chặn, kiểm riêng ở đây.

    Viết thành ca riêng vì `sim.run` cần dịch và chạy một chương trình C thật nên không gọi
    được trong bộ kiểm này; điều kiện thì kiểm được, và nó là phần quyết định.
    """
    def phai_chan(cac_ma_assert: list[str], so_do: dict) -> bool:
        tc = _tc("sim-01", cac_ma_assert)
        return bool(tc.asserts) and not (set(so_do) & {a.ma for a in tc.asserts})

    assert phai_chan(["A1", "A2"], {"C1": 0, "C2": 0}), "lệch hoàn toàn thì phải chặn"
    assert not phai_chan(["A1", "A2"], {"A1": 1.0}), "trùng một phần thì không chặn"
    assert not phai_chan(["A1"], {"A1": 0.0}), "trùng đủ thì không chặn, kể cả khi sai giá trị"
    assert not phai_chan([], {"C1": 0}), "tiêu chí rỗng đã có lỗi riêng, đừng chặn ở đây"


def test_loi_chan_noi_ro_hai_ben_doi_gi():
    """Thông báo phải kê **cả hai phía**, vì người đọc cần biết lệch ở đâu.

    Đọc thẳng mã nguồn `sim.run`: ca này canh nội dung thông báo, mà gọi hàm thì phải dịch
    một chương trình C — nên soi mã là phép đo rẻ nhất còn đúng chỗ.
    """
    nguon = (REPO / "src/eide/tools/xay_dung.py").read_text("utf-8")
    i = nguon.find("Số đo không chứa MỘT mã assert nào")
    assert i > 0, "mất chốt DEV-336 trong sim.run"
    doan = nguon[i - 400:i + 1600]
    assert '"E4023"' in doan, "chốt phải có mã lỗi riêng để tra được"
    assert "assert_doi" in doan and "so_do_nhan_duoc" in doan, (
        "thông báo phải kê cả hai phía: tiêu chí đòi gì và chương trình in ra gì")
    assert "KHÔNG phải sản phẩm sai" in doan, (
        "phải nói thẳng đây không phải lỗi sản phẩm, không thì tác tử sẽ đi sửa mã")
    assert "tep_nguon" in doan, "phải nêu tệp nguồn nào đã chạy, vì `nguon` bỏ trống lấy mọi tệp"
