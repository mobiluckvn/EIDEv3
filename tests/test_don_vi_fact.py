# -*- coding: utf-8 -*-
"""M5-05 — một con số đúng độ lớn mà SAI THỨ NGUYÊN vẫn vào kho được.

Ba chỗ đứt, đo lại trong mã trước khi sửa:

1. **`hop_ly` không kiểm đơn vị.** Nó quy về đơn vị cơ bản rồi chỉ so ĐỘ LỚN, nên
   `hop_ly("vdd.max", 25, "°C")` trả `True`: 25 nằm trong khoảng điện áp hợp lý (0,5–60), và
   chẳng ai hỏi "25 cái gì". Một Fact `vdd.max = 25 °C` ở tầng BẠC là vế giới hạn của luật ERC
   quá áp — tức một ô xanh giả đúng chỗ đắt nhất.
2. **Hai khoá không bao giờ được kiểm khoảng.** Bộ trích sinh ra `"fmax"` và `"ta.max"`, còn
   `PHAM_VI_HOP_LY` khai `"f.max"`, `"temp.min"`, `"temp.max"`. Hai bên không gặp nhau, nên
   `fmax = 20 GHz` của một MCU đi qua không ai cản.
3. **Đường HÀNG BẢNG không gọi `hop_ly` lần nào.** Mà bảng là đường chính của datasheet —
   `_tu_hang_bang` tồn tại chính vì đơn vị nằm ở cột riêng.

Cùng một hình dạng đã gặp bảy lần trong đợt này: cơ chế có sẵn (`PHAM_VI_HOP_LY`, `ve_si`),
đường dẫn tới nó đứt.
"""

from __future__ import annotations

import pytest

from eide.knowledge import docs as D


# ===================================================================== thứ nguyên
@pytest.mark.parametrize("khoa,gt,dv", [
    ("vdd.max", 25, "°C"),            # ca thật: 25 lọt khoảng điện áp 0,5–60
    ("vdd.min", 1.8, "mA"),
    ("icc.typ", 3.3, "V"),
    ("ta.max", 85, "V"),
    ("fmax", 16, "V"),
    ("i2c.pullup.typ", 4.7, "V"),
    ("flash.size", 2, "V"),
])
def test_sai_thu_nguyen_bi_loai(khoa, gt, dv):
    """TC-M5-05-01 — khoá có thứ nguyên khai báo thì đơn vị phải khớp.

    `vdd` đo volt. Một con số kèm `°C` không phải điện áp dù độ lớn của nó hợp lý — và chính
    *"độ lớn hợp lý"* là thứ làm nó đi qua được phép kiểm cũ.
    """
    assert D.hop_ly(khoa, gt, dv) is False, f"{khoa} = {gt} {dv} vẫn vào được kho"


@pytest.mark.parametrize("khoa,gt,dv", [
    ("vdd.max", 5.5, "V"),
    ("vdd.min", 1800, "mV"),          # cùng thứ nguyên, khác tiền tố
    ("icc.typ", 250, "mA"),
    ("ta.max", 85, "°C"),
    ("fmax", 20, "MHz"),
    ("i2c.pullup.typ", 4.7, "kΩ"),
    ("flash.size", 512, "KB"),
    ("flash.size", 32768, ""),        # datasheet hay ghi dung lượng KHÔNG kèm đơn vị
])
def test_gia_tri_dung_khong_bi_loai(khoa, gt, dv):
    """TC-M5-05-05 — ca âm. Một phép kiểm chặn quá tay sẽ bỏ mất Fact thật, và lúc ấy tác tử
    phải hỏi người dùng những con số đang nằm sẵn trong datasheet."""
    assert D.hop_ly(khoa, gt, dv) is True, f"{khoa} = {gt} {dv} bị loại oan"


def test_khoa_khong_khai_thu_nguyen_thi_KHONG_chan():
    """Khoá lạ không có trong bảng thì không chặn — giữ đúng tính chất cũ của `hop_ly`.

    `i2c.addr` là ca thật của chuyện này: giá trị của nó là chuỗi `"0x48"`, không có đơn vị để
    quy đổi. Áp một thứ nguyên lên nó là loại bỏ vế duy nhất của luật trùng địa chỉ bus.
    """
    assert D.hop_ly("khoa.la", 12345, "") is True
    assert D.hop_ly("i2c.addr", "0x48", "") is True
    assert D.hop_ly("throughput.max", 480, "Mbps") is True


def test_ba_khoa_cung_tien_to_i2c_khong_lan_nhau():
    """`i2c.pullup.typ` đo ohm, `i2c.fmax` đo hertz, `i2c.addr` không có thứ nguyên — ba khoá
    cùng bắt đầu bằng `i2c`, và không cái nào được lây thứ nguyên của cái khác."""
    assert D.hop_ly("i2c.pullup.typ", 4.7, "kΩ") is True
    assert D.hop_ly("i2c.fmax", 400, "kHz") is True
    assert D.hop_ly("i2c.fmax", 400, "kΩ") is False
    assert D.hop_ly("i2c.addr", "0x48", "") is True


def test_thu_nguyen_cua_lay_tien_to_DAI_NHAT(monkeypatch):
    """Phép tra phải lấy tiền tố DÀI NHẤT khớp, không phải cái đầu tiên tìm thấy.

    Tập phá chỉ ra rằng ca `i2c` ở trên KHÔNG đo được tính chất này: bảng hiện không có khoá
    `"i2c"`, nên đi từ ngắn hay từ dài cũng cùng rơi vào `"i2c.pullup"`. Ca này dựng đúng
    tình huống phân biệt được — một khoá ngắn VÀ một khoá dài cùng khớp — bằng cách thêm một
    dòng vào bảng trong phạm vi ca kiểm.

    Tính chất ấy sẽ cần thật khi bảng có thêm một nhóm như `adc` (đo volt) cạnh `adc.fmax`
    (đo hertz).
    """
    monkeypatch.setitem(D.THU_NGUYEN_KHOA, "adc", "V")
    monkeypatch.setitem(D.THU_NGUYEN_KHOA, "adc.fmax", "Hz")
    assert D.thu_nguyen_cua("adc.vref.max") == "V"
    assert D.thu_nguyen_cua("adc.fmax") == "Hz", "tiền tố NGẮN đã thắng tiền tố dài"
    assert D.hop_ly("adc.fmax", 1, "MHz") is True
    assert D.hop_ly("adc.fmax", 1, "V") is False


def test_hop_ly_KHONG_NO_voi_gia_tri_khong_phai_so():
    """Tập phá tìm ra một lỗi tiềm ẩn ở đây, không phải ở phần M5-05 thêm vào.

    `pv[0] <= co_ban` ném `TypeError` khi giá trị là chuỗi, và `i2c.addr` — khoá giá trị-chuỗi
    duy nhất hiện có — chỉ sống sót vì nó KHÔNG có khoảng trong `PHAM_VI_HOP_LY`. Cái lỗi nằm
    đó im lặng, chờ người đầu tiên thêm một khoảng cho một khoá như thế.
    """
    assert D.hop_ly("vdd.max", "3.3", "V") is True        # không nổ, và không chặn oan
    assert D.hop_ly("i2c.addr", "1001000", "") is True
    assert D.hop_ly("flash.size", "khong-phai-so", "") is True


def test_don_vi_RONG_voi_khoa_co_thu_nguyen_thi_loai():
    """Một con số không đơn vị cho một khoá đo volt là một con số không ai kiểm lại được.

    Ngoại lệ duy nhất là nhóm byte: datasheet ghi `Flash: 32768` không kèm đơn vị thật, và
    `ve_don_vi_co_ban` đã có ngữ nghĩa KB=1024 cho nhóm ấy.
    """
    assert D.hop_ly("vdd.max", 3.3, "") is False
    assert D.hop_ly("fmax", 16_000_000, "") is False
    assert D.hop_ly("flash.size", 32768, "") is True
    assert D.hop_ly("ram.size", 2048, "") is True


# ===================================================================== khoảng hợp lý
def test_khoa_fmax_ta_co_khoang():
    """TC-M5-05-02 — hai khoá mà bộ trích SINH RA phải là hai khoá được kiểm.

    `PHAM_VI_HOP_LY` khai `f.max` và `temp.*`; `_MAU_THONG_SO` sinh `fmax` và `ta.*`. Hai bảng
    không gặp nhau, nên phép kiểm khoảng của hai thông số này chưa nổ lần nào.
    """
    assert D.hop_ly("fmax", 20, "GHz") is False
    assert D.hop_ly("fmax", 0.5, "Hz") is False
    assert D.hop_ly("ta.max", 900, "°C") is False
    assert D.hop_ly("ta.min", -300, "°C") is False
    assert D.hop_ly("fmax", 180, "MHz") is True
    assert D.hop_ly("ta.min", -40, "°C") is True


def test_khoa_CU_van_con_khoang():
    """`f.max` và `temp.*` phải GIỮ: `tools/xay_dung.py` đọc `PHAM_VI_HOP_LY` theo khoá
    `flash.size`/`ram.size`, và bộ ca kiểm cũ dùng `temp.max`. Đổi tên thay vì thêm là làm
    hỏng Fact đã nằm trong kho của người dùng."""
    assert "f.max" in D.PHAM_VI_HOP_LY
    assert "temp.min" in D.PHAM_VI_HOP_LY and "temp.max" in D.PHAM_VI_HOP_LY
    assert "flash.size" in D.PHAM_VI_HOP_LY and "ram.size" in D.PHAM_VI_HOP_LY
    assert D.hop_ly("temp.max", 85, "°C") is True


# ===================================================================== đường dòng chữ
def _tl(chu: str) -> D.TaiLieu:
    return D.TaiLieu(doc_id="D1", ten="t.pdf", duong_dan="/t.pdf", hash="h" * 16,
                     so_trang=1, trang=[D.Trang(so=1, chu=chu)])


def test_dong_co_dieu_kien_nhiet_do():
    """TC-M5-05-03 — dòng chữ có HAI con số kèm đơn vị, và chỉ một là giá trị của thông số.

    `"VDD (max) 3.6 V at TA = 25 °C"`: `25 °C` là **điều kiện đo**, không phải `vdd.max`. Phép
    kiểm thứ nguyên là thứ phân biệt được hai cái.
    """
    uv = D.trich_fact_ung_vien(_tl("VDD (max) 3.6 V at TA = 25 °C"), thuc_the="chip:X")
    vdd = [u for u in uv if u.khoa == "vdd.max"]
    assert len(vdd) == 1, [(u.khoa, u.gia_tri, u.don_vi) for u in uv]
    assert vdd[0].gia_tri == 3.6 and vdd[0].don_vi == "V"


def test_dong_chi_co_nhiet_do_thi_KHONG_sinh_fact_dien_ap():
    """Chặt hơn ca trên: dòng CHỈ có nhiệt độ thì không được sinh một `vdd.max` nào."""
    uv = D.trich_fact_ung_vien(_tl("VDD (max) measured at 25 °C"), thuc_the="chip:X")
    assert [u for u in uv if u.khoa == "vdd.max"] == []


# ===================================================================== đường hàng bảng
def _hang(o: list[str], cot: list[str]) -> D.Trang:
    return D.Trang(so=1, chu=" | ".join(o), o=o, cot=cot, loai_bang="thong_so")


def test_TEN_HANG_phai_khop_mau_truoc_da():
    """Chỗ này bắt được một ca kiểm **xanh vì lý do khác**, và nó đáng ghi lại.

    Bảng TC của kế hoạch nêu hàng `o=["VDD","25","°C"]` và mong `_tu_hang_bang` trả rỗng. Nó
    trả rỗng **trên mã chưa sửa** — nhưng không phải vì phép kiểm đơn vị nào: `"VDD"` trơn
    KHÔNG khớp mẫu nào trong `_MAU_THONG_SO` (mẫu đòi `VDD (max)` / `VDD (min)` hoặc
    `supply voltage`), nên hàng bị bỏ ngay ở bước tìm khoá.

    Một ca kiểm như thế xanh trước và sau khi sửa, và nó không đo thứ nó nói nó đo. Nên ca
    này ghim lại chính tính chất ấy, còn các ca kiểm đơn vị ở dưới dùng tên hàng **khớp mẫu**.
    """
    assert D._tu_hang_bang(_hang(["VDD", "25", "°C"], ["Parameter", "Max", "Unit"]),
                           "chip:X") == []
    assert D._tu_hang_bang(_hang(["VDD (max)", "3.6", "V"], ["Parameter", "Max", "Unit"]),
                           "chip:X") != []


def test_hang_bang_cung_bi_kiem():
    """TC-M5-05-04 — bảng là đường CHÍNH của datasheet, và nó không gọi `hop_ly` lần nào.

    `_tu_hang_bang` tồn tại chính vì đơn vị nằm ở cột riêng — nên nó có đủ dữ kiện để kiểm
    thứ nguyên, và nó là đường duy nhất không kiểm. Tên hàng ở đây **khớp mẫu**, nên nếu kết
    quả rỗng thì chỉ có thể vì phép kiểm đơn vị.
    """
    ra = D._tu_hang_bang(_hang(["VDD (max)", "25", "°C"], ["Parameter", "Max", "Unit"]),
                         "chip:X")
    assert ra == [], [(u.khoa, u.gia_tri, u.don_vi) for u in ra]
    ra = D._tu_hang_bang(_hang(["Supply voltage", "25", "°C"],
                               ["Parameter", "Typ", "Unit"]), "chip:X")
    assert ra == [], [(u.khoa, u.gia_tri, u.don_vi) for u in ra]


def test_hang_bang_DUNG_van_qua():
    """Ca âm của đường bảng. Chặn quá tay ở đây là bỏ mất gần hết Fact của một datasheet."""
    ra = D._tu_hang_bang(_hang(["VDD (max)", "2.7", "5.5", "V"],
                               ["Parameter", "Min", "Max", "Unit"]), "chip:X")
    d = {u.khoa: u.gia_tri for u in ra}
    assert d.get("vdd.min") == 2.7 and d.get("vdd.max") == 5.5, d


def test_hang_bang_sai_thu_nguyen_chi_bo_O_SAI():
    """Một hàng có ô đúng và ô sai thì chỉ bỏ ô sai — bỏ cả hàng là mất dữ kiện thật.

    Hàng này là hình dạng có thật trong datasheet: bộ đọc bảng cắt lệch một cột nên giá trị
    nhiệt độ của cột `Conditions` rơi vào một cột giá trị.
    """
    # Ô sai nằm GIỮA, không ở cuối: nếu nó ở cuối thì một phép `break` thay cho `continue`
    # cũng xanh, và ca kiểm không phân biệt được "bỏ ô sai" với "bỏ nốt phần còn lại".
    ra = D._tu_hang_bang(
        D.Trang(so=1, chu="VDD (max) | 2.7 V | 25 °C | 5.5 V",
                o=["VDD (max)", "2.7 V", "25 °C", "5.5 V"],
                cot=["Parameter", "Min", "Typ", "Max"], loai_bang="thong_so"),
        "chip:X")
    khoa = {u.khoa for u in ra}
    assert "vdd.min" in khoa and "vdd.max" in khoa, khoa
    assert "vdd.typ" not in khoa, "ô 25 °C vẫn thành điện áp danh định"


def test_hang_bang_cung_bi_kiem_KHOANG_chu_khong_chi_thu_nguyen():
    """Hàng bảng phải qua CẢ HAI phép kiểm, nên nó phải được tra bằng khoá **có hậu tố**.

    Tập phá chỉ ra chỗ này: gọi `hop_ly("vdd", …)` thay vì `hop_ly("vdd.max", …)` vẫn xanh,
    vì thứ nguyên tra theo tiền tố nên `"vdd"` cũng ra `"V"` — nhưng `PHAM_VI_HOP_LY` không có
    khoá `"vdd"`, nên phép kiểm **khoảng** im lặng mất. Một `600 V` đúng thứ nguyên mà không
    phải chip này sẽ đi qua.
    """
    ra = D._tu_hang_bang(_hang(["VDD (max)", "600", "V"], ["Parameter", "Max", "Unit"]),
                         "chip:X")
    assert ra == [], [(u.khoa, u.gia_tri, u.don_vi) for u in ra]
    ra = D._tu_hang_bang(_hang(["Max operating frequency", "20", "GHz"],
                               ["Parameter", "Max", "Unit"]), "chip:X")
    assert ra == [], [(u.khoa, u.gia_tri, u.don_vi) for u in ra]


def test_duong_BANG_va_duong_DONG_CHU_sinh_CUNG_MOT_khoa():
    """Lỗ tìm ra bằng tập phá, ngoài phạm vi kế hoạch nêu — và nó im lặng.

    `_tu_hang_bang` cắt mù hậu tố (`k.rsplit(".", 1)[0]`), nên:

    * `flash.size` → `flash` + hậu tố cột → **`flash.max`**;
    * `fmax` (một đoạn, không có hậu tố nào để cắt) → **`fmax.max`**.

    Hai khoá ấy không có trong `KHOA_CHUAN`, không có trong `PHAM_VI_HOP_LY`, và
    `tools/xay_dung._han_muc` không đọc `flash.max` — nên một dung lượng Flash đọc từ BẢNG
    chưa bao giờ thành hạn mức, mà Fact vẫn trông hợp lệ. Cùng hình dạng với chính lỗi M5-05
    đi vá: hai khoá cho một thông số, và hai bên không gặp nhau.
    """
    d = D._tu_hang_bang(_hang(["Flash memory", "512", "KB"],
                              ["Parameter", "Value", "Unit"]), "chip:X")
    assert [u.khoa for u in d] == ["flash.size"], [u.khoa for u in d]

    f = D._tu_hang_bang(_hang(["Max operating frequency", "180", "MHz"],
                              ["Parameter", "Max", "Unit"]), "chip:X")
    assert [u.khoa for u in f] == ["fmax"], [u.khoa for u in f]

    # Và khoá CÓ hậu tố min/typ/max thì vẫn lấy hậu tố từ CỘT, như trước.
    v = D._tu_hang_bang(_hang(["VDD (max)", "2.7", "5.5", "V"],
                              ["Parameter", "Min", "Max", "Unit"]), "chip:X")
    assert sorted(u.khoa for u in v) == ["vdd.max", "vdd.min"], [u.khoa for u in v]
