# -*- coding: utf-8 -*-
"""M4-01 — unit test do EIDE phán theo tiêu chí nêu trước, thay cho `dat:true` tệp test tự in.

Điều bộ này canh, một câu: **thứ bị kiểm không được là thứ tuyên bố kết quả.**

`sim.run` đã đi qua chỗ này từ lâu: chương trình mô phỏng chỉ in **số đo** (`do`), còn đạt hay
không do EIDE so số đo với ngưỡng trong tiêu chí người dùng đã xác nhận. `test.run` thì chưa —
nó đếm `sum(1 for x in kq.ca if x.get("dat") is True)`, nên **chính tệp test** nói nó đạt. Một
dòng sửa trong `test/test_pid.c` là mọi ca "đạt", và không phép kiểm nào thấy.

Chỗ khác với `sim.run`, và vì sao nó đáng một nhiệm vụ riêng: tệp test là thứ tác tử **tự
viết**. Nên ở đây cái vòng "thứ bị kiểm tự chấm điểm mình" khép kín hơn: tác tử viết mã sản
phẩm, viết tệp test cho nó, rồi đọc kết quả do tệp test ấy tự in ra.
"""

from __future__ import annotations

import shutil

import pytest

from eide.build import mo_phong as MP
from eide.build import tieu_chi as TCM

pytestmark = pytest.mark.nha_that

_EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
       "confidence": "VANG"}

co_cc = bool(shutil.which("cc") or shutil.which("clang") or shutil.which("gcc"))
can_cc = pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


def _tc(**kw) -> TCM.TieuChi:
    """Tiêu chí một assert: T1 — giá trị ra của PID không quá 255 (trần PWM 8 bit)."""
    return TCM.TieuChi.from_dict({
        "ma": "unit-01", "ten": "Logic PID",
        "assert": [{"ma": "T1", "mo_ta": "Giá trị ra của PID khi bão hoà",
                    "phep_so": "<=", "nguong": 255, "don_vi": "đơn vị PWM",
                    "do_req": "REQ-PID-02", "nguon_nguong": "PWM 8 bit của AVR"}],
        **kw})


def _viet_test(goc, than: str, ten: str = "test_pid.c") -> None:
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test" / ten).write_text(
        '#include <stdio.h>\nint main(void){ printf("%s\\n", ' + than + '); return 0; }\n',
        "utf-8")


# Một tệp test in SỐ ĐO, không in kết luận. 300 > 255 nên EIDE phải phán KHÔNG ĐẠT — dù tệp
# test không nói một chữ nào về đạt hay hỏng.
_IN_SO_DO_300 = '"{\\"do\\": {\\"T1\\": 300}}"'
# Cùng một con số, nhưng tệp test TỰ KHAI là đạt. Đây là khuôn cũ.
_IN_TU_KHAI_DAT = '"{\\"ca\\": [{\\"ten\\": \\"pid_bao_hoa\\", \\"dat\\": true}]}"'


@can_cc
def test_chay_test_co_tieu_chi_thi_EIDE_phan(tmp_path):
    """TC-M4-01-01 — có tiêu chí thì số đo của tệp test bị EIDE so với ngưỡng.

    Tệp test in `{"do": {"T1": 300}}` và **không** nói đạt hay hỏng. Ngưỡng là `<= 255`, nên
    kết luận phải là một ca HỎNG, và câu giải thích phải mang con số 300 — không thì người
    đọc không kiểm lại được.
    """
    goc = tmp_path
    _viet_test(goc, _IN_SO_DO_300)
    kq = MP.chay_test(goc=goc, nguon=[goc / "test" / "test_pid.c"], tieu_chi=_tc())

    assert kq.chay_duoc, kq.vi_sao_khong_dat or kq.loi_bien_dich
    assert kq.so_ca == 1 and kq.so_hong == 1 and kq.so_dat == 0, kq.ca
    assert kq.che_do == "eide_phan", kq.che_do
    assert kq.dat is False
    assert "300" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat
    assert kq.ca[0]["ten"] == "T1", kq.ca


@can_cc
def test_khong_neu_tieu_chi_thi_hanh_vi_y_cu(tmp_path):
    """TC-M4-01-04 — ca "không kêu nhầm": không tiêu chí thì y như cũ, chỉ dán nhãn tự khai.

    Sáu ca trong `test_xay_dung.py` và mọi dự án đang có đều đi đường này. Nếu nhiệm vụ này
    làm chúng đổi hành vi thì nó không phải một năng lực thêm vào, mà là một lần phá tương
    thích ngược.
    """
    goc = tmp_path
    _viet_test(goc, _IN_TU_KHAI_DAT)
    kq = MP.chay_test(goc=goc, nguon=[goc / "test" / "test_pid.c"])

    assert kq.chay_duoc and kq.dat is True, kq.vi_sao_khong_dat
    assert kq.so_ca == 1 and kq.so_dat == 1, kq.ca
    assert kq.che_do == "tu_khai", kq.che_do


@can_cc
def test_tieu_chi_KHONG_CO_ASSERT_nao_thi_noi_ra_chu_khong_bao_0_ca(tmp_path):
    """Tiêu chí rỗng assert → nói ra là **không có gì để phán**, không báo "0 ca".

    "Chạy xong, 0 ca" đọc như một kết quả rỗng vô hại. Nhưng ở đây nó nghĩa là bảng tiêu chí
    người dùng vừa duyệt không chứa điều kiện nào — và mọi lượt chạy sau đó sẽ "không đạt" vì
    một lý do nằm ở tiêu chí, không ở sản phẩm.
    """
    goc = tmp_path
    _viet_test(goc, _IN_SO_DO_300)
    rong = TCM.TieuChi.from_dict({"ma": "unit-01", "assert": []})
    kq = MP.chay_test(goc=goc, nguon=[goc / "test" / "test_pid.c"], tieu_chi=rong)

    assert kq.chay_duoc and kq.dat is False
    assert kq.so_ca == 0, kq.ca
    assert "chưa có assert nào" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat
    assert "unit-01" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat


@can_cc
def test_co_tieu_chi_ma_test_khong_in_so_do_thi_CHUA_DO_DUOC(tmp_path):
    """Có tiêu chí mà không có số đo nào → **chưa đủ dữ kiện**, không phải đạt.

    Đây là quyết định số 2 của `build/tieu_chi.py`, và nó phải đúng cả ở đường unit test:
    log rỗng ≠ đạt. Nếu thiếu số đo mà lùi về đếm `ca` tự khai thì cả nhiệm vụ này vô nghĩa —
    chỉ cần bỏ khoá `do` đi là về lại chế độ tự chấm điểm.
    """
    goc = tmp_path
    _viet_test(goc, '"{\\"do\\": {}}"')
    kq = MP.chay_test(goc=goc, nguon=[goc / "test" / "test_pid.c"], tieu_chi=_tc())

    assert kq.chay_duoc and kq.dat is False
    assert kq.che_do == "eide_phan", kq.che_do
    assert kq.so_hong == 1, kq.ca
    assert "KHÔNG in ra số đo" in kq.vi_sao_khong_dat, kq.vi_sao_khong_dat


# ======================================================================= qua công cụ thật

def _ghi_tieu_chi(agent, ctx, *, trich_loi: str = "Tôi đồng ý với tiêu chí này.") -> None:
    kw = {"ma": "unit-01", "ten": "Logic PID",
          "assert": [{"ma": "T1", "mo_ta": "Giá trị ra của PID khi bão hoà",
                      "phep_so": "<=", "nguong": 255, "don_vi": "đơn vị PWM",
                      "do_req": "REQ-PID-02", "nguon_nguong": "PWM 8 bit của AVR"}],
          "explain": _EX}
    if trich_loi:
        kw["trich_loi"] = trich_loi
    r = agent.registry.run("test.criteria", kw, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")


@can_cc
def test_tu_khai_dat_nhung_co_tieu_chi_thi_tu_choi(make_agent):
    """TC-M4-01-02 — đã có tiêu chí mà tệp test vẫn in `ca` tự khai → E4024.

    Không im lặng bỏ qua phần tự khai, và cũng không im lặng nhận nó. Nếu nhận, tiêu chí trở
    thành một tờ giấy dán tường: nó có, đã được xác nhận, và không phán gì cả.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx)
    _viet_test(goc, _IN_TU_KHAI_DAT)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert not r.ok, r.data
    assert r.error.code == "E4024", r.error.code
    assert '"do"' in r.error.hint_for_agent, "phải chỉ đúng khuôn số đo cần in"


@can_cc
def test_test_criteria_chua_xac_nhan_thi_test_run_tu_choi(make_agent):
    """TC-M4-01-03 — tiêu chí chưa ai xác nhận thì `test.run` từ chối bằng E4009.

    Tiêu chí là **của người dùng**. Tự xác nhận hộ rồi chạy là cách đặt ngưỡng vừa khít với
    thứ vừa đo được — TC022 cấm đúng việc ấy.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx, trich_loi="")
    _viet_test(goc, _IN_SO_DO_300)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert not r.ok and r.error.code == "E4009", getattr(r.error, "code", r.data)


def test_neu_ma_tieu_chi_chua_he_co_thi_tu_choi_E4008(make_agent):
    """Nêu một mã tiêu chí chưa tồn tại → E4008, kèm đường đi tới `test.criteria`."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _viet_test(goc, _IN_SO_DO_300)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-09"}, ctx)
    assert not r.ok and r.error.code == "E4008", getattr(r.error, "code", r.data)
    assert "test.criteria" in (r.error.alternatives or []), r.error.alternatives


@can_cc
def test_test_run_co_tieu_chi_thi_EIDE_phan_va_note_noi_ro_che_do(make_agent):
    """Đường đầy-đủ qua công cụ: tiêu chí đã xác nhận + tệp test in số đo → EIDE phán.

    Và `note_vi` phải NÓI RA chế độ. Hai lượt chạy khác chế độ mà đọc giống nhau thì con số
    "3/3 ca đạt" của một lượt tự khai được đọc ngang với một lượt đã phán — đúng cái lỗi
    DEV-344 vừa sửa ở khối A8.0.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx)
    _viet_test(goc, _IN_SO_DO_300)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["che_do"] == "eide_phan", r.data["che_do"]
    assert r.data["dat"] is False and r.data["so_hong"] == 1
    assert "EIDE phán" in r.data["note_vi"], r.data["note_vi"]
    assert "unit-01" in r.data["note_vi"], r.data["note_vi"]


@can_cc
def test_hien_vat_mang_theo_MA_TIEU_CHI_da_phan(make_agent):
    """Hiện vật phải mang `ma_tieu_chi`, không chỉ mang chữ "đã phán".

    Người đọc sở cứ sáu tháng sau cần tra lại **ngưỡng nào** đã phán con số này. Thiếu mã
    tiêu chí thì hiện vật nói "EIDE phán" mà không ai kiểm lại được nó phán theo cái gì —
    đúng hình dạng một con số không có nguồn.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx)
    _viet_test(goc, _IN_SO_DO_300)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    c = (agent.store.get("sim_result:unit-test") or {}).get("canonical") or {}
    assert c.get("ma_tieu_chi") == "unit-01", c.get("ma_tieu_chi")
    assert c.get("che_do") == "eide_phan", c.get("che_do")
    assert c.get("so_do") == {"T1": 300}, c.get("so_do")


@can_cc
def test_E4024_tu_choi_TRUOC_khi_ghi_kho(make_agent):
    """Từ chối rồi thì KHÔNG được để lại hiện vật — nhất là một hiện vật nói "đã phán".

    Nếu ghi kho trước rồi mới từ chối, kho giữ một mục `che_do="eide_phan"` cho một lượt mà
    thật ra là tệp test tự khai. Lời từ chối đi tới tác tử và tắt theo lượt; hiện vật thì ở
    lại và là thứ người đọc sở cứ sau này tin.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx)
    _viet_test(goc, _IN_TU_KHAI_DAT)

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert not r.ok and r.error.code == "E4024"
    assert agent.store.get("sim_result:unit-test") is None, (
        "đã từ chối mà vẫn để lại hiện vật kết quả test")


@can_cc
def test_so_do_khong_khop_MOT_ma_assert_nao_thi_tu_choi_E4023(make_agent):
    """Số đo không chứa mã assert nào → E4023: sai CẶP tiêu chí/tệp test, không sai sản phẩm.

    Hai chuyện ấy dẫn tới hai việc ngược nhau — một cái bảo đi sửa mã, cái kia bảo gọi lại
    cho đúng. Cùng cái bẫy DEV-336 bắt được ở `sim.run`, và ở đường unit test nó dễ trúng
    hơn: `nguon` bỏ trống thì lấy MỌI tệp `test/*.c`.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _ghi_tieu_chi(agent, ctx)
    # Tiêu chí đòi T1; tệp test đo X9. Không giao nhau một mã nào.
    _viet_test(goc, '"{\\"do\\": {\\"X9\\": 1}}"')

    r = agent.registry.run("test.run", {"explain": _EX, "ma_tieu_chi": "unit-01"}, ctx)
    assert not r.ok, r.data
    assert r.error.code == "E4023", r.error.code
    assert "KHÔNG phải sản phẩm sai" in r.error.hint_for_agent
    assert r.error.details["so_do_nhan_duoc"] == ["X9"], r.error.details


def test_assert_thieu_mo_ta_thi_tu_choi_E4007(make_agent):
    """Phép kiểm assert dùng CHUNG với `sim.criteria` — nới nó là nới cả hai cửa.

    `ma` không có thì số đo không trỏ vào đâu; `mo_ta` không có thì kết quả sau này không ai
    đọc được. Ca này canh cả hai, và nó canh hộ `sim.criteria` nữa.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    for xau in ({"ma": "T1"}, {"mo_ta": "chỉ có mô tả"}):
        r = agent.registry.run("test.criteria", {"assert": [xau], "explain": _EX}, ctx)
        assert not r.ok and r.error.code == "E4007", (xau, getattr(r.error, "code", r.data))
    r = agent.registry.run("sim.criteria", {"assert": [{"ma": "A1"}], "explain": _EX}, ctx)
    assert not r.ok and r.error.code == "E4007", getattr(r.error, "code", r.data)


@can_cc
def test_test_run_khong_neu_tieu_chi_thi_note_noi_la_TU_KHAI(make_agent):
    """Lượt tự khai phải tự nói ra là tự khai, và nói ra độ tin của nó."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    _viet_test(goc, _IN_TU_KHAI_DAT)

    r = agent.registry.run("test.run", {"explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["che_do"] == "tu_khai", r.data["che_do"]
    assert "TỰ KHAI" in r.data["note_vi"], r.data["note_vi"]


# ============================== nơi NGƯỜI đọc con số: tab A8, không phải `note_vi`
#
# `note_vi` đi tới tác tử. Người dùng thì đọc tab. Nếu chế độ chỉ nói ở `note_vi` thì đúng
# cái lỗi DEV-344 vừa sửa ở khối A8.0: con số tự khai và con số đã phán hiện ra giống nhau ở
# chỗ nó được đọc.

def _kho_test(canonical: dict) -> object:
    class _Kho:
        def list(self, loai, limit=10):
            return ([{"id": "sim_result:unit-test", "type": "sim_result", "version": 1,
                      "author": "agent:run-1", "canonical": canonical,
                      "explain": {"summary": ""}, "stale": False, "stale_reason": None}]
                    if loai == "sim_result" else [])

        def get(self, _ma):
            return None

    return _Kho()


def _cap(kh: list, nhan: str) -> str:
    """Giá trị của đúng một dòng trong khối "kv" — không soi cả khối bằng `in str(kh)`.

    Soi cả khối là cách một ca kiểm xanh nhờ **một dòng khác**: bản đầu của hai ca dưới đây
    kiểm `"TỰ KHAI" in str(kh)`, và chúng vẫn xanh khi tôi phá chữ ấy ở dòng *Kết luận* —
    vì `summary` của khối cũng chứa nó. Phép phá bắt được, ca kiểm thì không.
    """
    for k in kh:
        for c, v in (k.get("pairs") or []):
            if c == nhan:
                return str(v)
    return ""


def test_tab_A8_dong_KET_LUAN_noi_ra_con_so_la_TU_KHAI():
    """Tab phải nói ra rằng con số "đạt" này do chính tệp test tự in."""
    from eide import surfaces as S

    kh = S.simulation(_kho_test({
        "dat": True, "chay_duoc": True, "so_ca": 3, "so_dat": 3, "so_hong": 0,
        "che_do": "tu_khai", "ca": [], "tep_nguon": ["test/test_pid.c"]}), None)["blocks"]
    ket = _cap(kh, "Kết luận")
    assert "TỰ KHAI" in ket, ket
    assert "tự kiểm" not in ket, (
        "dòng Kết luận vẫn là câu của sim.run cho một lượt unit test tự khai")
    tin = _cap(kh, "Độ tin của con số này")
    assert "ĐỎ" in tin, f"không nói ra độ tin của một con số tự khai: {tin!r}"
    assert "test.criteria" in tin, tin


def test_tab_A8_dong_KET_LUAN_noi_ra_con_so_do_EIDE_phan():
    """Và lượt đã phán thì nói ra là đã phán, kèm mã tiêu chí để tra lại."""
    from eide import surfaces as S

    kh = S.simulation(_kho_test({
        "dat": True, "chay_duoc": True, "so_ca": 1, "so_dat": 1, "so_hong": 0,
        "che_do": "eide_phan", "ma_tieu_chi": "unit-01", "ca": [],
        "tep_nguon": ["test/test_pid.c"]}), None)["blocks"]
    ket = _cap(kh, "Kết luận")
    assert "EIDE phán" in ket, ket
    assert "unit-01" in ket, ket
    assert "TỰ KHAI" not in ket, "gọi một lượt đã phán là tự khai"
    assert not _cap(kh, "Độ tin của con số này"), (
        "dán cảnh báo độ tin ĐỎ lên một lượt đã được phán")


def test_tab_A8_tieu_chi_unit_khong_bi_goi_la_tieu_chi_mo_phong():
    """Bảng tiêu chí unit test không được hứa hẹn thay cho `sim.run`."""
    from eide import surfaces as S

    class _Kho:
        def list(self, loai, limit=10):
            return ([{"id": "criteria:unit-01", "type": "criteria", "version": 1,
                      "author": "agent:run-1",
                      "canonical": {"ma": "unit-01", "assert": [
                          {"ma": "T1", "mo_ta": "x", "phep_so": "<=", "nguong": 255}]},
                      "explain": {"summary": ""}, "stale": False, "stale_reason": None}]
                    if loai == "criteria" else [])

        def get(self, _ma):
            return None

    chu = str(S.simulation(_Kho(), None))
    assert "Tiêu chí unit test — unit-01" in chu, chu[:900]
    assert "mô phỏng sẽ không chạy" not in chu, (
        "bảng tiêu chí unit test lại nói nó chặn mô phỏng")


def test_test_criteria_dang_ky_core_false_mo_ta_ngan(make_agent):
    """TC-M4-01-05 — công cụ mới không được chiếm chỗ trong ngân sách lược đồ mỗi lượt."""
    agent = make_agent([])
    sp = next((t for t in agent.registry.all() if t.name == "test.criteria"), None)
    assert sp is not None, "chưa đăng ký test.criteria"
    assert sp.core is False, "core=True là nạp lược đồ này vào MỌI lượt"
    assert sp.risk == "R2", sp.risk
    assert len(sp.summary_vi) <= 400, len(sp.summary_vi)
    assert "criteria" in (sp.produces or []), sp.produces


def test_test_criteria_khong_the_de_len_tieu_chi_cua_sim(make_agent):
    """`test.criteria` KHÔNG được ghi đè `criteria:sim-01`.

    Hai loại tiêu chí dùng chung một không gian khoá hiện vật. Nếu `ma` đi thẳng vào khoá thì
    một lần gọi `test.criteria(ma="sim-01")` xoá sổ tiêu chí mô phỏng mà người dùng đã xác
    nhận — và `sim.run` sau đó phán theo ngưỡng của unit test.
    """
    agent = make_agent([])
    ctx = _ctx(agent)
    r = agent.registry.run("test.criteria", {
        "ma": "sim-01",
        "assert": [{"ma": "T1", "mo_ta": "x", "phep_so": "<=", "nguong": 1,
                    "nguon_nguong": "ca kiểm"}],
        "explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert agent.store.get("criteria:sim-01") is None, "đã đè lên tiêu chí của sim.run"
    assert agent.store.get("criteria:unit-sim-01") is not None, r.data
