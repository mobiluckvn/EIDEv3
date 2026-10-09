# -*- coding: utf-8 -*-
"""M4-11 — STALE theo TỆP, chặn tuyên xong khi còn STALE, và hồi quy nhẹ sau khi sửa mã.

Kế hoạch ghi rằng phải sửa `deps.ha_nguon_cua` cho loại `sim_result`. **Đo trước khi tin:**
ba ca đầu của bộ này XANH SẴN trên mã trước M4-11 — lớp ấy đã đúng từ M2-01 (`deps.upstream`
thắng chuỗi mặc định khi khai cùng loại), và M4-06 đã dùng nó cho
`sim_result:test-sensitivity`. Chỗ hổng thật nằm ở **đường ghi**: `test.run` và `sim.run` —
hai công cụ mọi dự án đi qua — gọi `store.apply` **không có `deps=`**, nên hiện vật của chúng
không khai gì, và chuỗi mặc định `"code" → sim_result` làm mọi lần sửa một tệp mã bất kỳ đánh
STALE mọi kết quả test/sim.

Nên ba ca đầu giữ lại làm **hàng rào cho lớp mà bản sửa dựa vào** (nói rõ chúng xanh sẵn),
còn phép đo thật nằm ở phần sau: chạy công cụ THẬT rồi đọc kho.
"""

from __future__ import annotations

import shutil

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}
MA_TEST = "sim_result:unit-test"
MA_SIM = "sim_result:can-bang"
co_cc = bool(shutil.which("cc") or shutil.which("clang") or shutil.which("gcc"))
can_cc = pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")

# Một tệp test in đúng khuôn JSON, gọi một hàm của tệp sản phẩm.
TEP_TEST = ('#include <stdio.h>\nint nguong(void);\n'
            'int main(void){ printf("{\\"ca\\": [{\\"ten\\": \\"A\\", \\"dat\\": %s,'
            ' \\"vi\\": \\"nguong\\"}]}\\n", nguong()==480?"true":"false"); return 0; }\n')
TEP_SP = "#include <stdint.h>\nint nguong(void){ return 480; }\n"


@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-thu")
    return ag, build_registry(), ctx


def _tep(goc, duong: str, noi_dung: str) -> None:
    p = goc / duong
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(noi_dung, "utf-8")


def _ghi_qua_eide(ag, duong: str, noi_dung: str) -> None:
    """Ghi tệp qua `history.ghi_tep` — đường duy nhất đăng ký hiện vật và đánh dấu STALE."""
    _tep(ag.config.paths.project_root, duong, noi_dung)
    ag.history.ghi_tep(author="agent:run-1", paths=[duong], summary="sửa " + duong,
                       explain=EX, run_id="run-1")


def _ket_qua_test(ag, upstream: list[str] | None) -> None:
    ag.store.apply(artefact_id=MA_TEST, type="sim_result", op="create", author="test",
                   canonical={"dat": True, "so_ca": 3, "so_dat": 3,
                              "tep_nguon": list(upstream or [])},
                   explain=EX,
                   **({"deps": {"upstream": list(upstream)}} if upstream else {}))


# ============================================ lớp deps — XANH SẴN, giữ làm hàng rào (M2-01)
def test_sua_tep_khong_lien_quan_khong_stale(bo):
    """TC-M4-11-01 — kết quả khai dựng từ `firmware/pid.c`; sửa `firmware/ui.c` thì nó KHÔNG
    lỗi thời.

    Ca này **xanh sẵn** trước M4-11: `ha_nguon_cua` đã làm đúng từ M2-01. Giữ nó vì bản sửa
    của M4-11 dựa vào đúng tính chất này — nếu ai siết lại `khai_ro` thì phải thấy ở đây.
    """
    ag, _r, _ctx = bo
    for t in ("firmware/pid.c", "firmware/ui.c"):
        _ghi_qua_eide(ag, t, "int x;\n")
    _ket_qua_test(ag, ["firmware/pid.c"])

    _ghi_qua_eide(ag, "firmware/ui.c", "int x; int y;\n")
    assert not ag.store.get(MA_TEST)["stale"], ag.store.get(MA_TEST)["stale_reason"]


def test_sua_tep_lien_quan_thi_stale(bo):
    """TC-M4-11-02 — mặt còn lại, và nó là mặt NẶNG hơn: hẹp quá thì một kết quả đã lỗi thời
    nằm đó như còn đúng."""
    ag, _r, _ctx = bo
    for t in ("firmware/pid.c", "firmware/ui.c"):
        _ghi_qua_eide(ag, t, "int x;\n")
    _ket_qua_test(ag, ["firmware/pid.c"])

    _ghi_qua_eide(ag, "firmware/pid.c", "int x; int y;\n")
    assert ag.store.get(MA_TEST)["stale"]
    assert "cs-" in ag.store.get(MA_TEST)["stale_reason"]


def test_hien_vat_cu_khong_upstream_van_stale_theo_loai(bo):
    """TC-M4-11-03 — ca âm TƯƠNG THÍCH. Hiện vật cũ trên đĩa không có `deps`, và chúng phải
    tiếp tục STALE theo chuỗi mặc định: hẹp đi cho dữ liệu KHÔNG KHAI là tự nhận biết một
    thứ mình không biết."""
    ag, _r, _ctx = bo
    _ghi_qua_eide(ag, "firmware/pid.c", "int x;\n")
    _ket_qua_test(ag, None)
    assert not (ag.store.get(MA_TEST)["deps"] or {}).get("upstream")

    _ghi_qua_eide(ag, "firmware/ui.c", "int x;\n")
    assert ag.store.get(MA_TEST)["stale"], "hiện vật KHÔNG khai deps phải stale như cũ"


# ===================================================== đường GHI — chỗ hổng thật của M4-11
def test_test_run_KHAI_deps_upstream(bo):
    """TC-M4-11-06 — `test.run` phải ghi hiện vật KÈM `deps.upstream`.

    Đây là chỗ đứt: hiện vật được ghi ở mọi lượt (kể cả lượt không dịch được), và nó đi vào
    kho **không khai gì**. Mọi ca STALE-theo-tệp ở trên đều nói về một hiện vật do tay dựng;
    ca này hỏi hiện vật do CÔNG CỤ dựng.
    """
    ag, _r, ctx = bo
    goc = ag.config.paths.project_root
    _tep(goc, "firmware/pid.c", TEP_SP)
    _tep(goc, "test/t.c", TEP_TEST)

    ag.registry.run("test.run", {"explain": EX}, ctx)
    up = (ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or []
    assert "test/t.c" in up, up
    assert "firmware/pid.c" in up, "tệp SẢN PHẨM dịch cùng phải có trong upstream"


def test_test_run_roi_sua_tep_KHAC_thi_ket_qua_con_tuoi(bo):
    """TC-M4-11-07 — phép đo đầu-cuối, và là lý do cả nhiệm vụ tồn tại: sau một lượt
    `test.run` THẬT, sửa một tệp firmware không liên quan không được làm kết quả lỗi thời;
    sửa đúng tệp đã dịch cùng thì phải."""
    ag, _r, ctx = bo
    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _ghi_qua_eide(ag, "firmware/pid.c", TEP_SP)
    # `ve.c` kéo header của bo nên nó KHÔNG được dịch cùng — đúng thứ không nên làm stale.
    _ghi_qua_eide(ag, "firmware/ve.c", '#include "stm32469i_discovery.h"\nvoid ve(void){}\n')
    ag.registry.run("test.run", {"explain": EX}, ctx)
    assert not ag.store.get(MA_TEST)["stale"]

    _ghi_qua_eide(ag, "firmware/ve.c", '#include "stm32469i_discovery.h"\nvoid ve(void){;}\n')
    assert not ag.store.get(MA_TEST)["stale"], (
        "sửa tệp KHÔNG được dịch cùng mà kết quả vẫn lỗi thời — băng cảnh báo lúc nào cũng "
        "sáng là băng cảnh báo không ai đọc")

    _ghi_qua_eide(ag, "firmware/pid.c", "#include <stdint.h>\nint nguong(void){return 0;}\n")
    assert ag.store.get(MA_TEST)["stale"], "sửa tệp ĐÃ DỊCH CÙNG mà kết quả không lỗi thời"


def test_nguon_tuong_minh_thi_tep_duoc_INCLUDE_van_vao_upstream(bo):
    """Chỗ hẹp của chính bản sửa này, và nó phải được canh.

    `test.run` nêu `nguon` tường minh thì `ds` CHỈ còn tệp test — đường nhặt tệp logic
    (`_logic_dich_duoc_tren_may`) không chạy. Mà một tệp test `#include "../firmware/pid.c"`
    vẫn phụ thuộc vào `pid.c` thật. Lấy `tep_nguon` làm upstream mà không khép bao đóng
    `#include` thì bản sửa này tự tạo ra một ô "còn tươi" GIẢ — đúng loại sai mà nó đi vá.
    """
    ag, _r, ctx = bo
    goc = ag.config.paths.project_root
    _tep(goc, "firmware/pid.c", TEP_SP)
    _tep(goc, "test/t.c", '#include "../firmware/pid.c"\n' + TEP_TEST)

    ag.registry.run("test.run", {"explain": EX, "nguon": ["test/t.c"]}, ctx)
    up = (ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or []
    assert "test/t.c" in up, up
    assert "firmware/pid.c" in up, (
        "tệp được #include phải vào upstream, không thì sửa nó mà kết quả vẫn báo còn tươi")


def test_bao_dong_DUNG_duoc_khi_hai_tep_include_lan_nhau(bo):
    """Hai tệp `#include` lẫn nhau là chuyện có thật trong firmware (qua header). Bao đóng
    phải DỪNG, và phải ra đủ hai tệp.

    Ca này chạy trong một **luồng riêng có đồng hồ**, và đó là cả nửa giá trị của nó: phép đo
    phải biến cái TREO thành chữ ĐỎ. `_khep_include` có hai lớp phòng độc lập chống vòng vô
    hạn — phép dedupe `xong` và trần đếm **lượt**. Tháo riêng từng lớp thì hành vi không đổi
    (tập phá đã chỉ ra đúng thế), tháo cả hai thì nó lặp mãi; mà pytest không có đồng hồ cho
    từng ca, nên một ca gọi thẳng `_khep_include` sẽ **treo** chứ không đỏ, và một lượt treo
    giết luôn mọi phép phá còn lại. Lần chạy tập phá đầu tiên mất 900 giây đúng vì chuyện này.
    """
    import threading

    from eide.tools.xay_dung import _khep_include

    goc = bo[0].config.paths.project_root
    _tep(goc, "v1.c", '#include "v2.c"\nint v1(void){return 1;}\n')
    _tep(goc, "v2.c", '#include "v1.c"\nint v2(void){return 2;}\n')
    ra: list = []
    t = threading.Thread(target=lambda: ra.append(_khep_include(goc, [goc / "v1.c"])),
                         daemon=True)
    t.start()
    t.join(timeout=5.0)
    assert not t.is_alive(), "_khep_include không dừng trên một vòng #include"
    assert sorted(ra[0]) == ["v1.c", "v2.c"], ra


def test_include_he_thong_va_tep_khong_co_thi_bo_qua(bo):
    """`#include <stdio.h>` không phải phụ thuộc của dự án, và một tệp không tồn tại thì
    không được vào upstream — một id không có hiện vật nào chỉ làm đồ thị rộng ra mà không
    nói thêm gì.

    Và ca này phải canh `<...>` bằng một tệp CÙNG TÊN có thật trong dự án, không thì nó xanh
    vì `stdio.h` không tồn tại, chứ không vì phép lọc chạy. Đây là hình dạng có thật:
    `du-lieu/rtos-sinhvien/firmware/` có một `stdio.h` riêng của bo — chuyện đã làm 11/12 tệp
    bị xếp sai ở M4-19 (DEV-349).
    """
    from eide.tools.xay_dung import _khep_include

    goc = bo[0].config.paths.project_root
    _tep(goc, "stdio.h", "/* stdio giả của bo */\n")
    _tep(goc, "c.c", '#include <stdio.h>\n#include "khong-co.h"\nint c(void){return 0;}\n')
    assert _khep_include(goc, [goc / "c.c"]) == ["c.c"]


def test_tep_mam_KHONG_ton_tai_thi_khong_vao_upstream(bo):
    """Tệp MẦM cũng phải qua phép lọc tồn-tại, không chỉ tệp được `#include`.

    Phá lại thì đỏ chỉ ra chỗ này: `sim.run` dựng `ds = [(goc / x) for x in nguon]` **không**
    lọc `.exists()` (khác `test.run`), nên một `nguon` sai chính tả đi thẳng vào `upstream` —
    một id không có hiện vật nào ứng với nó. Hai lớp phòng ở hai chỗ khác nhau: `ung.is_file()`
    canh tệp được include, `p.is_file()` canh tệp mầm. Tháo một lớp thôi thì không thấy gì.
    """
    from eide.tools.xay_dung import _khep_include

    goc = bo[0].config.paths.project_root
    assert _khep_include(goc, [goc / "khong-co.c"]) == []


def test_bo_dedupe_thi_TRAN_bi_tieu_het_vao_mot_vong(bo):
    """Dedupe không chỉ để chạy nhanh — nó là thứ giữ cho TRẦN còn ý nghĩa.

    Hai tệp `#include` lẫn nhau mà không dedupe thì hàng đợi tự nuôi chính nó, và trần lượt bị
    tiêu hết vào cái vòng ấy **trước khi** tới các tệp ở xa. Lúc đó `upstream` thiếu mắt, và
    thiếu một mắt trong `upstream` không kêu lên — nó chỉ im lặng bảo rằng một con số cũ còn
    đúng. Con số 6 lấy từ phép đo, không từ ước lượng: có dedupe ra 5 tệp, không có ra 4.
    """
    from eide.tools.xay_dung import _khep_include

    goc = bo[0].config.paths.project_root
    _tep(goc, "a.c", '#include "b.c"\n#include "c.c"\nint a;\n')
    _tep(goc, "b.c", '#include "a.c"\nint b;\n')          # vòng a ↔ b
    _tep(goc, "c.c", '#include "d.c"\nint c;\n')
    _tep(goc, "d.c", '#include "e.c"\nint d;\n')
    _tep(goc, "e.c", "int e;\n")
    assert sorted(_khep_include(goc, [goc / "a.c"], tran=6)) == [
        "a.c", "b.c", "c.c", "d.c", "e.c"]




def test_tran_bao_dong_chan_theo_LUOT(bo):
    """Trần phải chặn số LƯỢT, không chặn "số tệp đã xong".

    Tìm ra bằng chính tập phá của nhiệm vụ này: bỏ phép dedupe thì phép đo **treo 900 giây**
    thay vì đỏ — vì hai tệp `#include` lẫn nhau làm hàng đợi dài mãi trong khi `len(xong)`
    dừng ở hai. Một trần đặt trên `len(xong)` không chặn gì cả; nó chỉ trông như có chặn.
    """
    from eide.tools.xay_dung import _khep_include

    goc = bo[0].config.paths.project_root
    _tep(goc, "x.c", '#include "y.c"\nint x(void){return 1;}\n')
    _tep(goc, "y.c", '#include "z.c"\nint y(void){return 2;}\n')
    _tep(goc, "z.c", "int z(void){return 3;}\n")
    assert len(_khep_include(goc, [goc / "x.c"], tran=2)) <= 2
    assert sorted(_khep_include(goc, [goc / "x.c"])) == ["x.c", "y.c", "z.c"]


@can_cc
def test_sim_run_KHAI_deps_upstream(bo):
    """TC-M4-11-08 — cùng chỗ đứt, ở `sim.run`. Khác `test.run` một chỗ: `sim.run` chặn
    bằng E4023 trước khi ghi kho nếu số đo không mang mã assert, nên ca này cần chương
    trình mô phỏng CHẠY THẬT."""
    ag, _r, ctx = bo
    goc = ag.config.paths.project_root
    ag.registry.run("sim.criteria", {
        "ma": "sim-01", "ten": "Cân bằng",
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 15.0,
                    "don_vi": "°", "do_req": "REQ-BAL-01",
                    "nguon_nguong": "§13.4 tài liệu"}],
        "khong_mo_phong_duoc": [{"gi": "WS2812", "vi_sao": "không có mô hình",
                                 "cach_bu": "đo bằng oscilloscope"}],
        "timeout_s": 20, "trich_loi": "đúng rồi, 15 độ", "explain": EX}, ctx)
    _tep(goc, "firmware/control_pid.c", "#include <stdint.h>\ndouble goc(void){return 3.0;}\n")
    _tep(goc, "sim/plant.c",
         '#include <stdio.h>\ndouble goc(void);\n'
         'int main(void){ printf("{\\"do\\": {\\"A1\\": %f}}\\n", goc()); return 0; }\n')

    r = ag.registry.run("sim.run", {"explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "") or getattr(r.error, "hint_for_agent", "")
    up = (ag.store.get(MA_SIM)["deps"] or {}).get("upstream") or []
    assert "sim/plant.c" in up and "firmware/control_pid.c" in up, up


# ======================================================= hook: STALE phải chặn lời tuyên xong
def _hook_stale():
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    fn = next(f for f in register_standard_hooks(HookBus())._stop
              if f.__name__ == "ket_qua_stale")

    class _Mot:
        @staticmethod
        def stop(ctx):
            return fn(ctx)

    return _Mot()


class _Ctx:
    def __init__(self, store, *, noi=True, da_ghi=True, registry=None):
        self.said_anything = noi
        self.da_ghi_gi_do = da_ghi
        self.store = store
        self.registry = registry
        self.da_nhac_stale = False


def test_tuyen_xong_khi_MA_TEST_stale_thi_bat_lai(bo):
    """TC-M4-11-04 — nhãn STALE mà không chặn được lời tuyên xong thì nó là trang trí.

    Đo được ở chính đợt này (DANG-LAM, bài học #9): một con số đúng, đi vào kho đúng, rồi
    không đi tới đâu.
    """
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.mark_stale([MA_TEST], "cs-0007 (tác tử sửa mã)")

    r = _hook_stale().stop(_Ctx(ag.store))
    assert r.another_round is True
    assert "lỗi thời" in r.injection and "cs-0007" in r.injection
    assert "test.run" in r.injection


def test_ket_qua_con_tuoi_thi_hook_IM(bo):
    """Ca âm. Một hook kêu khi không có gì lỗi thời sẽ thành tiếng ồn trong một buổi chiều."""
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    assert _hook_stale().stop(_Ctx(ag.store)).another_round is False


def test_luot_THUAN_DOC_co_ket_qua_stale_thi_hook_IM(bo):
    """Lượt không ghi gì thường là lượt trả lời một câu hỏi. Bắt nó chạy lại test là dựng
    thủ tục quanh một cuộc trò chuyện — cùng lý do với `kiem_viec_chua_ai_kiem`."""
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.mark_stale([MA_TEST], "cs-0007")
    assert _hook_stale().stop(_Ctx(ag.store, da_ghi=False)).another_round is False


def test_chua_tra_luot_ve_thi_hook_IM(bo):
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.mark_stale([MA_TEST], "cs-0007")
    assert _hook_stale().stop(_Ctx(ag.store, noi=False)).another_round is False


def test_chi_nhac_MOT_LAN_moi_luot(bo):
    """Vòng thứ hai là vòng tác tử đang TRẢ LỜI lời nhắc này."""
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.mark_stale([MA_TEST], "cs-0007")
    ctx = _Ctx(ag.store)
    assert _hook_stale().stop(ctx).another_round is True
    assert ctx.da_nhac_stale is True
    assert _hook_stale().stop(ctx).another_round is False


def test_hook_noi_ten_HIEN_VAT_nao_loi_thoi(bo):
    """Hai kết quả lỗi thời thì lời nhắc phải kể cả hai: "chạy lại trước khi báo" mà không
    nói chạy lại cái nào là một việc không làm được."""
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.apply(artefact_id=MA_SIM, type="sim_result", op="create", author="test",
                   canonical={"dat": True}, explain=EX,
                   deps={"upstream": ["sim/plant.c"]})
    ag.store.mark_stale([MA_TEST, MA_SIM], "cs-0009 (anh sửa mã)")
    r = _hook_stale().stop(_Ctx(ag.store))
    assert "unit-test" in r.injection and "can-bang" in r.injection


def test_chi_do_nhay_stale_thi_hook_IM(bo):
    """`sim_result:test-sensitivity` đã có hook riêng (`test_xanh_chua_do_nhay`), và hook ấy
    so `version_test` — chính xác hơn một nhãn stale. Hai hook cùng nhắc một việc thì lời
    nhắc thứ hai chỉ là tiếng ồn, và tiếng ồn thì bị bỏ qua kể cả lần nó đáng đọc."""
    ag, _r, _ctx = bo
    ag.store.apply(artefact_id="sim_result:test-sensitivity", type="sim_result", op="create",
                   author="test", canonical={"diem": 0.0}, explain=EX)
    ag.store.mark_stale(["sim_result:test-sensitivity"], "cs-0007")
    assert _hook_stale().stop(_Ctx(ag.store)).another_round is False


def test_hook_MO_KHOA_cong_cu_truoc_khi_bao_chay(bo):
    """`test.run`/`sim.run` là `core=False` — tác tử chỉ thấy chúng sau `tool.search`.

    Đo được ở M4-06 (DEV-351): hook nổ hai lượt liền, `another_round=True` cả hai, và tác tử
    KHÔNG gọi lần nào, vì công cụ ấy không có trong danh sách nó nhìn thấy. Bảo ai đó dùng
    một thứ họ không nhìn thấy thì không phải là bảo.
    """
    ag, _r, _ctx = bo
    _ket_qua_test(ag, ["firmware/pid.c"])
    ag.store.mark_stale([MA_TEST], "cs-0007")
    assert "test.run" not in ag.registry._unlocked
    _hook_stale().stop(_Ctx(ag.store, registry=ag.registry))
    assert "test.run" in ag.registry._unlocked


# ============================================================ cờ HOI_QUY_NEN — mặc định TẮT
def test_co_hoi_quy_nen_co_ten_va_mac_dinh_TAT():
    """Bài học M4-07: một cờ không có tên trong `ten_co()` thì không bật được, và ca kiểm
    im. Nay `ten_co()` lấy từ dataclass, nên ca này so TẬP, không kiểm một tên."""
    from eide.config import Features

    assert "hoi_quy_nen" in Features.ten_co()
    assert Features().bat("hoi_quy_nen") is False


def test_co_tat_khong_tu_chay_test(bo, monkeypatch):
    """TC-M4-11-05 — cờ TẮT thì hành vi y như cũ: không một lượt chạy test nào tự nổ."""
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, _ctx = bo
    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _tep(goc, "firmware/pid.c", TEP_SP)
    _ket_qua_test(ag, ["test/t.c", "firmware/pid.c"])

    goi: list = []
    import eide.build.mo_phong as MP
    monkeypatch.setattr(MP, "chay_test", lambda **kw: goi.append(kw))

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall(
            "c2", "fs.write", {"path": "firmware/pid.c", "content": TEP_SP + "int z;\n",
                               "explain": EX})]),
        Response(text="đã sửa pid.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "sửa pid.c",
                                "origin": {"surface": "console"}}), lambda c: None)

    assert goi == [], "cờ TẮT mà vẫn tự chạy test"
    assert not any("hồi quy:" in (m.get("text") or "") for m in ag.messages)


@can_cc
def test_co_BAT_thi_chay_hoi_quy_va_TIEM_ket_qua(bo, monkeypatch):
    """Mặt còn lại của TC-M4-11-05: thiếu nửa này thì một cờ không-bao-giờ-chạy cũng qua.

    Và chuyện hồi quy chạy xong KHÔNG xoá nhãn STALE là có chủ ý: §E5.4 nói "không tự chạy
    lại" — lượt này chỉ **mách** con số cho tác tử, hiện vật vẫn đợi một `test.run` thật.
    """
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()
    assert ag.config.features.bat("hoi_quy_nen")

    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _tep(goc, "firmware/pid.c", TEP_SP)
    ag.registry.run("test.run", {"explain": EX}, ctx)
    assert "firmware/pid.c" in ((ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or [])

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c1", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall(
            "c2", "fs.write",
            {"path": "firmware/pid.c",
             "content": "#include <stdint.h>\nint nguong(void){ return 999; }\n",
             "explain": EX})]),
        Response(text="đã sửa pid.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "đổi ngưỡng",
                                "origin": {"surface": "console"}}), lambda c: None)

    hq = [m for m in ag.messages if "hồi quy:" in (m.get("text") or "")]
    assert hq, "cờ BẬT mà không lượt hồi quy nào nổ"
    # Sửa 480 → 999 nên ca test phải ĐỎ, và con số tiêm vào phải nói đúng điều đó.
    assert "0/1" in hq[0]["text"], hq[0]["text"]
    # Và phải nói CA NÀO đỏ. "0/1" một mình là một con số không chỉ ra việc gì phải làm —
    # cùng lý do với `vi_sao_khong_dat` của `test.run`.
    assert "nguong" in hq[0]["text"], hq[0]["text"]
    assert ag.store.get(MA_TEST)["stale"], "hồi quy nhẹ KHÔNG được xoá nhãn STALE"


@can_cc
def test_hoi_quy_KHONG_dem_duoc_ca_nao_thi_noi_CHUA_CHAY_DUOC(bo, monkeypatch):
    """`0/0 ca đạt` là một câu không có ô đỏ nào — đúng cái bẫy `test.run` đã vá bằng E4014.

    Một bộ kiểm in ra thứ không đếm được thì lượt hồi quy phải nói **CHƯA chạy được** kèm lý
    do, không được hiện một phân số trông như đã đo.
    """
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()

    goc = ag.config.paths.project_root
    _tep(goc, "firmware/pid.c", TEP_SP)
    # Tệp test KHÔNG in khuôn JSON nào — `test.run` sẽ trả E4014, nhưng hiện vật vẫn được ghi
    # kèm `deps.upstream`, nên đường hồi quy vẫn nổ được ở lượt sau.
    _tep(goc, "test/t.c",
         '#include <stdio.h>\nint nguong(void);\n'
         'int main(void){ printf("Tất cả test OK, nguong=%d\\n", nguong()); return 0; }\n')
    ag.registry.run("test.run", {"explain": EX}, ctx)
    assert "firmware/pid.c" in ((ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or [])

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "firmware/pid.c", "content": TEP_SP + "int z;\n", "explain": EX})]),
        Response(text="sửa pid.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "sửa pid.c",
                                "origin": {"surface": "console"}}), lambda c: None)

    hq = [m for m in ag.messages if "hồi quy:" in (m.get("text") or "")]
    assert hq, "không lượt hồi quy nào nổ"
    assert "CHƯA chạy được" in hq[0]["text"], hq[0]["text"]
    assert "0/0" not in hq[0]["text"], "một phân số rỗng đọc như đã đo mà không có ô đỏ nào"


def test_hoi_quy_truyen_dung_TRAN_thoi_gian(bo, monkeypatch):
    """Trần 20 s phải thật sự tới `chay_test`.

    Không phải một ca soi câu lệnh của chính mình: trần này là **hợp đồng** của đường hồi quy
    nhẹ — nó chạy giữa lượt, trong thời gian người dùng đang chờ. Bỏ nó đi thì về mặc định
    120 s, và lúc ấy "nhẹ" chỉ còn là một chữ trong tên hàm.
    """
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, _ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()

    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _tep(goc, "firmware/pid.c", TEP_SP)
    _ket_qua_test(ag, ["test/t.c", "firmware/pid.c"])

    goi: list = []
    import eide.build.mo_phong as MP

    class _Gia:
        chay_duoc = True
        so_ca = so_dat = 1
        so_hong = 0
        vi_sao_khong_dat = ""
        loi_bien_dich = ""

    monkeypatch.setattr(MP, "chay_test", lambda **kw: (goi.append(kw), _Gia())[1])

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "firmware/pid.c", "content": TEP_SP + "int z;\n", "explain": EX})]),
        Response(text="sửa pid.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "sửa pid.c",
                                "origin": {"surface": "console"}}), lambda c: None)

    assert goi, "không lượt hồi quy nào nổ"
    assert goi[0]["giay_toi_da"] == 20.0, goi[0]
    assert goi[0]["do_phu"] is False, "hồi quy nhẹ không cần đo độ phủ"


@can_cc
def test_hoi_quy_chay_DUNG_MOT_LAN_moi_luot(bo, monkeypatch):
    """Trần một lần mỗi lượt: một lượt sửa bảy tệp thì bảy lượt biên dịch là tiền và là
    thời gian người dùng đang chờ."""
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()

    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _tep(goc, "firmware/pid.c", TEP_SP)
    _tep(goc, "firmware/loc.c", "#include <stdint.h>\nint loc(void){ return 1; }\n")
    ag.registry.run("test.run", {"explain": EX}, ctx)

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "firmware/pid.c", "content": TEP_SP + "int z;\n", "explain": EX})]),
        Response(tool_calls=[ToolCall("c2", "fs.read", {"path": "firmware/loc.c"})]),
        Response(tool_calls=[ToolCall("c3", "fs.write", {
            "path": "firmware/loc.c",
            "content": "#include <stdint.h>\nint loc(void){ return 2; }\n",
            "explain": EX})]),
        Response(text="sửa hai tệp"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "sửa hai tệp",
                                "origin": {"surface": "console"}}), lambda c: None)

    hq = [m for m in ag.messages if "hồi quy:" in (m.get("text") or "")]
    assert len(hq) == 1, f"{len(hq)} lượt hồi quy trong một lượt"


@can_cc
def test_header_trong_upstream_khong_lam_hoi_quy_do(bo, monkeypatch):
    """Bao đóng `#include` kéo cả HEADER vào upstream — đúng cho STALE (sửa `config.h` thì
    kết quả lỗi thời thật), nhưng đưa một `.h` cho trình biên dịch là một lượt dịch đổ.

    Đo được trên kho thật: `robot-sinhvien2` khai `firmware/config.h` trong upstream. Nên
    phép chọn tệp để dịch phải lọc theo đuôi — không lọc thì hồi quy báo "CHƯA chạy được"
    cho một bộ kiểm vẫn chạy tốt, và đó là một cáo buộc sai về sản phẩm.
    """
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()

    goc = ag.config.paths.project_root
    _tep(goc, "firmware/cau_hinh.h", "#define NGUONG 480\n")
    _tep(goc, "firmware/pid.c", '#include "cau_hinh.h"\nint nguong(void){ return NGUONG; }\n')
    _tep(goc, "test/t.c", TEP_TEST)
    ag.registry.run("test.run", {"explain": EX}, ctx)
    up = (ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or []
    assert "firmware/cau_hinh.h" in up, up

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "firmware/pid.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "firmware/pid.c",
            "content": '#include "cau_hinh.h"\nint nguong(void){ return NGUONG + 1; }\n',
            "explain": EX})]),
        Response(text="sửa pid.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "đổi ngưỡng",
                                "origin": {"surface": "console"}}), lambda c: None)

    hq = [m for m in ag.messages if "hồi quy:" in (m.get("text") or "")]
    assert hq, "không lượt hồi quy nào nổ"
    assert "CHƯA chạy được" not in hq[0]["text"], hq[0]["text"]
    assert "0/1" in hq[0]["text"], hq[0]["text"]


@can_cc
def test_sua_tep_KHONG_trong_upstream_thi_khong_chay_hoi_quy(bo, monkeypatch):
    """Hồi quy chỉ nổ cho tệp mà bộ kiểm THẬT SỰ dịch cùng — cùng một phép đọc `upstream`
    mà STALE dùng, không phải một phép so tên thư mục."""
    from eide.llm import Response, ToolCall
    from eide.protocol.humanact import HumanAct

    ag, _r, ctx = bo
    monkeypatch.setenv("EIDE_FEATURE_HOI_QUY_NEN", "1")
    from eide.config import Features
    ag.config.features = Features.load()

    goc = ag.config.paths.project_root
    _tep(goc, "test/t.c", TEP_TEST)
    _tep(goc, "firmware/pid.c", TEP_SP)
    _tep(goc, "firmware/ve.c", '#include "stm32469i_discovery.h"\nvoid ve(void){}\n')
    ag.registry.run("test.run", {"explain": EX}, ctx)
    up = (ag.store.get(MA_TEST)["deps"] or {}).get("upstream") or []
    assert "firmware/ve.c" not in up, up

    ag.llm.script = [
        Response(tool_calls=[ToolCall("c0", "fs.read", {"path": "firmware/ve.c"})]),
        Response(tool_calls=[ToolCall("c1", "fs.write", {
            "path": "firmware/ve.c",
            "content": '#include "stm32469i_discovery.h"\nvoid ve(void){;}\n',
            "explain": EX})]),
        Response(text="sửa ve.c"), Response(text="nói thêm"), Response(text="nói thêm")]
    ag.llm._i = 0
    ag.turn(HumanAct.from_dict({"kind": "say", "text": "sửa ve.c",
                                "origin": {"surface": "console"}}), lambda c: None)

    assert not any("hồi quy:" in (m.get("text") or "") for m in ag.messages)
