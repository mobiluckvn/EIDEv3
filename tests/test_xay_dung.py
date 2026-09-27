# -*- coding: utf-8 -*-
"""build.compile và sim.run — G6 tối thiểu.

Điều bộ này canh, một câu: **hai công cụ dễ nói dối nhất phải không nói dối được.**

Một công cụ biên dịch có thể "đạt" mà không sinh ra tệp nào; một công cụ mô phỏng có thể in
ra một bản báo cáo đẹp mà chẳng chạy gì. Cả hai kiểu đậu giả đều trông hợp lý trên màn hình
và chỉ vỡ ra khi người dùng nạp firmware vào bo thật. Nên mọi ca ở đây hỏi cùng một câu:
*bằng chứng đâu?*
"""

from __future__ import annotations

import shutil

import pytest

from eide.build import mo_phong as MP
from eide.build import toolchain as TC

_EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
       "confidence": "VANG"}

co_avr = bool(TC.tim_chuoi_cong_cu("avr8").get("arduino-cli")
              or TC.tim_chuoi_cong_cu("avr8").get("avr-gcc"))
can_avr = pytest.mark.skipif(not co_avr, reason="máy này chưa có chuỗi công cụ AVR")
co_cc = bool(shutil.which("cc") or shutil.which("clang") or shutil.which("gcc"))


def _ctx(agent):
    from eide.loop import TurnContext

    return TurnContext(config=agent.config, store=agent.store, ledger=agent.ledger,
                       eide_md=agent.eide_md, ids=agent.ids, registry=agent.registry,
                       emit=lambda c: None, history=agent.history, run_id="run-1")


# ===================================================================== phân tích lỗi
def test_loi_trinh_bien_dich_thanh_TEP_DONG_COT():
    """Trả nguyên một khối chữ thì tác tử phải đoán chỗ sửa; trả toạ độ thì nó sửa đúng chỗ."""
    ds = TC.phan_tich_loi(
        "firmware/main.c:42:13: error: 'TCCR2A' undeclared (first use in this function)\n"
        "firmware/main.c:50:5: warning: unused variable 'x' [-Wunused-variable]\n"
        "chữ không phải lỗi\n")
    assert [x.muc for x in ds] == ["error", "warning"]
    assert ds[0].tep == "firmware/main.c" and ds[0].dong == 42 and ds[0].cot == 13
    assert "TCCR2A" in ds[0].thong_diep


def test_kien_truc_la_thi_NOI_RA_chu_khong_im_lang_bo_qua(tmp_path):
    kq = TC.bien_dich(goc=tmp_path, sketch=tmp_path, isa="risc-v-bia")
    assert not kq.dat and "Chưa biết biên dịch" in kq.vi_sao_khong_dat


# ===================================================================== biên dịch thật
@can_avr
def test_bien_dich_that_va_doc_duoc_kich_thuoc(tmp_path):
    (tmp_path / "firmware").mkdir()
    (tmp_path / "firmware/firmware.ino").write_text(
        "#include <avr/io.h>\n"
        "int main(void){ DDRB |= (1<<PB5); for(;;){ PORTB ^= (1<<PB5);} }\n", "utf-8")
    kq = TC.bien_dich(goc=tmp_path, sketch=tmp_path / "firmware", isa="avr8",
                      flash_toi_da=32768, sram_toi_da=2048)
    assert kq.dat, kq.vi_sao_khong_dat + "\n" + kq.nguyen_van[-800:]
    assert kq.tep_ra.endswith((".hex", ".elf"))
    assert 0 < kq.flash < 32768


@can_avr
def test_loi_bien_dich_tra_ve_TUNG_DONG_de_sua(tmp_path):
    (tmp_path / "firmware").mkdir()
    (tmp_path / "firmware/firmware.ino").write_text(
        "#include <avr/io.h>\nint main(void){ ham_khong_ton_tai(); }\n", "utf-8")
    kq = TC.bien_dich(goc=tmp_path, sketch=tmp_path / "firmware", isa="avr8")
    assert not kq.dat and kq.loi
    assert kq.loi[0].dong == 2 and "ham_khong_ton_tai" in kq.loi[0].thong_diep


# ===================================================================== mô phỏng
@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_mo_phong_chay_ma_THAT_va_doc_ket_qua_bang_JSON(tmp_path):
    (tmp_path / "sim").mkdir()
    (tmp_path / "sim/main.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"dat\\": true, \\"goc_max_do\\": 1.5}\\n"); return 0; }\n',
        "utf-8")
    kq = MP.chay_mo_phong(goc=tmp_path, nguon=[tmp_path / "sim/main.c"])
    assert kq.chay_duoc and kq.dat, kq.vi_sao_khong_dat + kq.loi_bien_dich[-500:]
    assert kq.ket_qua["goc_max_do"] == 1.5


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_mo_phong_KHONG_in_JSON_thi_khong_ket_luan_gi(tmp_path):
    """Một chương trình in ra "mọi thứ ổn" rồi thoát 0 không phải là một kết quả mô phỏng."""
    (tmp_path / "sim").mkdir()
    (tmp_path / "sim/main.c").write_text(
        '#include <stdio.h>\nint main(void){ printf("robot đứng vững!\\n"); return 0; }\n',
        "utf-8")
    kq = MP.chay_mo_phong(goc=tmp_path, nguon=[tmp_path / "sim/main.c"])
    assert kq.chay_duoc and not kq.dat
    assert "không in ra dòng JSON" in kq.vi_sao_khong_dat


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_mo_phong_thoat_khac_0_thi_khong_coi_la_chay_tron_ven(tmp_path):
    """`dat` ở tầng này CHỈ nói "chạy trọn vẹn và in được kết quả" — đạt hay không là việc
    của TIÊU CHÍ, không phải của chương trình mô phỏng tự tuyên bố."""
    (tmp_path / "sim").mkdir()
    (tmp_path / "sim/main.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"do\\": {\\"A1\\": 12.0}}\\n"); return 1; }\n',
        "utf-8")
    kq = MP.chay_mo_phong(goc=tmp_path, nguon=[tmp_path / "sim/main.c"])
    assert kq.chay_duoc and not kq.dat and "mã 1" in kq.vi_sao_khong_dat
    assert kq.ket_qua["do"]["A1"] == 12.0


# ===================================================================== qua công cụ
def test_build_compile_khong_co_ma_nguon_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("build.compile", {"sketch": "khong-co", "explain": _EX},
                           _ctx(agent))
    assert not r.ok and r.error.code == "E4001"


def test_sim_run_DOI_TIEU_CHI_truoc_tien(make_agent):
    """Chạy trước rồi đặt tiêu chí sau là cách đặt tiêu chí vừa khít với kết quả — nên tiêu
    chí là thứ `sim.run` hỏi ĐẦU TIÊN, trước cả việc có mã mô phỏng hay chưa."""
    agent = make_agent([])
    r = agent.registry.run("sim.run", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4008"
    assert "vừa khít với kết quả" in r.error.hint_for_agent


def test_sim_run_chua_tach_logic_thi_CHI_DUONG_chu_khong_bia(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx)
    r = agent.registry.run("sim.run", {"explain": _EX}, ctx)
    assert not r.ok and r.error.code == "E4003"
    assert "ĐÚNG mã sẽ nạp vào chip" in r.error.hint_for_agent


def _ghi_tieu_chi(agent, ctx, *, xac_nhan=True, nguong=15.0):
    return agent.registry.run("sim.criteria", {
        "ma": "sim-01", "ten": "Cân bằng",
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=",
                    "nguong": nguong, "don_vi": "°", "do_req": "REQ-BAL-01",
                    "nguon_nguong": "§13.4 tài liệu"}],
        "khong_mo_phong_duoc": [{"gi": "WS2812", "vi_sao": "không có mô hình 800 kHz",
                                 "cach_bu": "đo bằng oscilloscope"}],
        "timeout_s": 20,
        **({"trich_loi": "đúng rồi, 15 độ"} if xac_nhan else {}),
        "explain": _EX}, ctx)


@can_avr
def test_build_compile_ghi_hien_vat_build_va_noi_ty_le_bo_nho(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "firmware/firmware.ino").write_text(
        "#include <avr/io.h>\nint main(void){ DDRB |= (1<<PB5); for(;;){} }\n", "utf-8")
    for fid, k, v, dv in (("f1", "flash.size", 32768, "B"), ("f2", "ram.size", 2048, "B")):
        agent.store.put_fact({"fact_id": fid, "subject": "chip:ATmega328P", "key": k,
                              "value": v, "unit": dv, "tier": "BAC", "origin": "extract",
                              "source": {}, "explain": {}})
    r = agent.registry.run("build.compile", {"explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["vua_chip"] is True and r.data["flash_toi_da"] == 32768
    a = agent.store.get("build:firmware")
    assert a and a["canonical"]["dat"] is True


def test_han_muc_bo_nho_lay_tu_FACT_khong_tu_tri_nho(make_agent):
    """Không có Fact thì hạn mức là 0 và công cụ phải nói "chưa biết có vừa chip không" —
    thà không kết luận còn hơn kết luận bằng một con số nhớ được."""
    from eide.tools.xay_dung import _han_muc

    agent = make_agent([])
    assert _han_muc(_ctx(agent), None) == (0, 0)


# ===================================================================== hiện lên bề mặt
def _inv_gia():
    class Inv:
        def __getattr__(self, k):
            return 0
    return Inv()


def test_ket_qua_mo_phong_HIEN_LEN_tab_Mo_phong(make_agent):
    """Một công cụ ghi vào kho mà bề mặt không đọc là một nửa tính năng: người dùng chạy
    xong rồi nhìn vào chỗ đáng lẽ thấy kết quả và thấy chữ "chưa chạy lần nào"."""
    from eide import surfaces as S

    agent = make_agent([])
    truoc = S.simulation(agent.store, _inv_gia())
    assert truoc["blocks"][0]["type"] == "empty"

    agent.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "chay_duoc": True,
                                 "ket_qua": {"dat": True, "goc_max_do": 3.0,
                                             "goc_cuoi_do": 1.07, "thoi_gian_s": 5.0},
                                 "tep_nguon": ["sim/plant.c", "firmware/control.c"]})
    sau = S.simulation(agent.store, _inv_gia())
    b = sau["blocks"][0]
    # Hợp đồng của khối `kv` là `pairs`, không phải `items` — gửi sai khoá thì giao diện vẽ
    # ra một ô trắng và không ai biết.
    assert b["type"] == "kv" and "ĐẠT" in b["summary"] and b.get("pairs")
    chu = " ".join(f"{a} {b2}" for a, b2 in b["pairs"])
    assert "goc_max_do" in chu and "sim/plant.c" in chu
    # Và phải nói ra giới hạn: mô hình không phải bo thật.
    assert "KHÔNG nói mạch thật sẽ chạy" in chu


def test_ket_qua_bien_dich_HIEN_LEN_tab_Ma_nguon(make_agent):
    from eide import surfaces as S

    agent = make_agent([])
    agent.store.apply(artefact_id="build:firmware", type="build", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "cong_cu": "arduino-cli",
                                 "tep_ra": ".eide/build/firmware.ino.hex",
                                 "flash": 2500, "sram": 72,
                                 "flash_toi_da": 30720, "sram_toi_da": 2048,
                                 "ty_le_flash": 0.081, "ty_le_sram": 0.035,
                                 "so_loi": 0, "so_canh_bao": 0})
    m = S.code_surface(agent.store, _inv_gia())
    b = next(x for x in m["blocks"] if x["id"] == "build:firmware")
    chu = " ".join(f"{a} {b2}" for a, b2 in b["pairs"])
    assert "arduino-cli" in chu and "2500 B / 30720 B" in chu


def test_khong_co_han_muc_thi_NOI_RA_chua_biet(make_agent):
    """Thiếu Fact flash.size mà vẫn in một tỉ lệ thì đó là một con số bịa."""
    from eide import surfaces as S

    agent = make_agent([])
    agent.store.apply(artefact_id="build:firmware", type="build", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "cong_cu": "avr-gcc", "tep_ra": "a.elf",
                                 "flash": 2500, "sram": 72, "flash_toi_da": 0,
                                 "sram_toi_da": 0, "ty_le_flash": None,
                                 "ty_le_sram": None, "so_loi": 0, "so_canh_bao": 0})
    m = S.code_surface(agent.store, _inv_gia())
    b = next(x for x in m["blocks"] if x["id"] == "build:firmware")
    chu = " ".join(f"{a} {b2}" for a, b2 in b["pairs"])
    assert "chưa biết hạn mức" in chu


# ===================================================================== G6-A · môi trường
def test_env_check_liet_ke_CO_va_THIEU_khong_tu_tuyen_bo_san_sang(make_agent):
    """TC018 — cách chắc chắn nhất để không báo biên dịch thành công giả là không bao giờ tự
    tuyên bố sẵn sàng: chỉ liệt kê cái có, cái thiếu, và thiếu thì hỏng việc gì."""
    agent = make_agent([])
    r = agent.registry.run("env.check", {"isa": "avr8"}, _ctx(agent))
    assert r.ok
    ten = {c["ten"] for c in r.data["cong_cu"]}
    assert {"cc", "arduino-cli", "avr-gcc"} <= ten
    assert all("de_lam_gi" in c for c in r.data["cong_cu"])
    # Không có câu nào tuyên bố "sẵn sàng biên dịch".
    assert "sẵn sàng" not in r.data["note_vi"].lower()


def test_env_check_kien_truc_LA_thi_noi_thang_chu_khong_chon_gan_giong(make_agent):
    """TC018 ghi nhận: chọn `armv7e-m` cho một chip Cortex-M3 sẽ sinh mã mang lệnh chip
    không chạy được."""
    agent = make_agent([])
    r = agent.registry.run("env.check", {"isa": "armv7-m"}, _ctx(agent))
    assert r.ok and r.data["isa_chua_biet"] is True
    assert "chưa biên dịch được cho chip này" in r.data["note_vi"]
    assert "gần giống" in r.data["note_vi"]


def test_tool_install_KHONG_nhan_lenh_do_mo_hinh_soan(make_agent):
    """Nếu mô hình tự soạn lệnh shell thì "duyệt cài đặt" thành "duyệt chạy một lệnh bất kỳ"."""
    agent = make_agent([])
    r = agent.registry.run("tool.install",
                           {"cong_cu": "rm -rf /", "isa": "avr8", "explain": _EX},
                           _ctx(agent))
    assert not r.ok and r.error.code == "E4005"
    assert "đừng soạn lệnh shell" in r.error.hint_for_agent


def test_tool_install_da_co_thi_khong_cai_lai(make_agent):
    agent = make_agent([])
    r = agent.registry.run("tool.install", {"cong_cu": "cc", "explain": _EX}, _ctx(agent))
    assert r.ok and r.data["da_co"] is True


def test_tool_install_di_qua_cong_G_TOOL(make_agent):
    """Cài phần mềm vào máy người dùng là R3 và phải hỏi — không có đường tắt."""
    agent = make_agent([])
    spec = agent.registry.get("tool.install")
    assert spec.risk == "R3" and spec.gate == "G-TOOL"


# ===================================================================== G6-A · bản đồ bộ nhớ
@can_avr
def test_build_map_doc_SECTION_va_SYMBOL_va_de_xuat_khi_tran(make_agent):
    """TC021 — một con số tổng nói firmware có vừa chip không; nó không nói phải bỏ gì."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "firmware").mkdir(parents=True, exist_ok=True)
    (goc / "firmware/firmware.ino").write_text(
        "#include <avr/io.h>\n"
        "const char bang[600] = {0};\n"
        "int main(void){ DDRB = bang[0]; for(;;){} }\n", "utf-8")
    for fid, k, v in (("f1", "flash.size", 32768), ("f2", "ram.size", 2048)):
        agent.store.put_fact({"fact_id": fid, "subject": "chip:ATmega328P", "key": k,
                              "value": v, "unit": "B", "tier": "BAC", "origin": "extract",
                              "source": {}, "explain": {}})
    assert agent.registry.run("build.compile", {"explain": _EX}, ctx).ok

    r = agent.registry.run("build.map", {"explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert any(s["ten"] == ".text" for s in r.data["section"])
    assert r.data["symbol"] and r.data["symbol"][0]["byte"] > 0
    assert r.data["vua_flash"] is True
    a = agent.store.get("analysis:build-map")
    assert a and a["canonical"]["flash"] > 0


def test_build_map_chua_bien_dich_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("build.map", {"explain": _EX}, _ctx(agent))
    assert not r.ok and "Chưa biên dịch lần nào" in r.error.message_vi


def test_map_canh_bao_SRAM_gan_day_vi_ngan_xep_khong_nam_trong_so_do(tmp_path):
    """Trên AVR, tràn ngăn xếp không sinh ngoại lệ mà lặng lẽ hỏng — nên 75 % đã là lúc phải
    nói, không đợi tới 100 %."""
    from eide.build.toolchain import doc_map

    m = doc_map(elf=tmp_path / "khong-co.elf", flash_toi_da=32768, sram_toi_da=2048)
    assert "Không có" in m["canh_bao"][0]


# ================================================== G6-B · tiêu chí PHÁN XỬ, không phải sim
def _tc_mau():
    from eide.build.tieu_chi import Assert, TieuChi

    return TieuChi(
        ma="sim-01", ten="Cân bằng 5 giây",
        asserts=[Assert(ma="A1", mo_ta="Góc nghiêng lớn nhất", phep_so="<=", nguong=15.0,
                        don_vi="°", do_req="REQ-BAL-01", nguon_nguong="§13.4 tài liệu"),
                 Assert(ma="A2", mo_ta="Góc ở giây thứ 5", phep_so="<=", nguong=2.0,
                        don_vi="°", do_req="REQ-BAL-01", nguon_nguong="anh Công nói")],
        khong_mo_phong_duoc=[{"gi": "WS2812", "vi_sao": "không có mô hình định thời 800 kHz",
                              "cach_bu": "đo trên bo bằng oscilloscope"}],
        xac_nhan_boi="human", trich_loi="đúng rồi, 15 độ và 2 độ")


def test_tieu_chi_PHAN_XU_ket_qua_chu_khong_phai_chuong_trinh_mo_phong():
    """Bản trước để chương trình mô phỏng tự in `dat: true` — thứ được kiểm cũng là thứ
    tuyên bố kết quả, và một dòng sửa trong sim/plant.c đủ để mọi phép thử "đạt"."""
    from eide.build.tieu_chi import xet_ket_qua

    tc = _tc_mau()
    assert xet_ket_qua(tc, {"A1": 3.0, "A2": 1.1})["dat"] is True
    xau = xet_ket_qua(tc, {"A1": 20.0, "A2": 1.1})
    assert xau["dat"] is False and "đo được 20.0" in xau["vi_sao_khong_dat"]


def test_thieu_so_do_la_CHUA_DU_DU_KIEN_khong_phai_dat():
    """Log rỗng ≠ đạt (N6). Một assert không có số đo thì cả lần chạy không được gọi là đạt."""
    from eide.build.tieu_chi import xet_ket_qua

    kq = xet_ket_qua(_tc_mau(), {"A1": 3.0})
    assert kq["dat"] is False and kq["dem"]["chua_do_duoc"] == 1
    assert "KHÔNG in ra số đo" in kq["dong"][1]["vi"]


def test_so_do_THUA_cung_duoc_noi_ra():
    """Số đo không có assert nào nhận nghĩa là một trong hai bên gõ sai mã assert."""
    from eide.build.tieu_chi import xet_ket_qua

    kq = xet_ket_qua(_tc_mau(), {"A1": 3.0, "A2": 1.0, "A9": 7})
    assert kq["so_do_thua"] == ["A9"]


def test_moi_assert_noi_duoc_no_do_REQ_nao_va_nguong_tu_dau():
    """§E2: "Mỗi assert đo REQ nào; ngưỡng lấy từ đâu" — không có hai thứ này thì người rà
    soát không có cách nào cãi lại một con số."""
    from eide.build.tieu_chi import xet_ket_qua

    kq = xet_ket_qua(_tc_mau(), {"A1": 3.0, "A2": 1.0})
    assert all(d["do_req"] and d["nguon_nguong"] for d in kq["dong"])


def test_tieu_chi_CHUA_xac_nhan_thi_sim_run_tu_choi(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    r = _ghi_tieu_chi(agent, ctx, xac_nhan=False)
    assert r.ok and r.data["da_xac_nhan"] is False
    assert "CHƯA có xác nhận" in r.data["note_vi"]
    kq = agent.registry.run("sim.run", {"explain": _EX}, ctx)
    assert not kq.ok and kq.error.code == "E4009"
    assert "Đừng tự xác nhận hộ" in kq.error.hint_for_agent


def test_tieu_chi_KHONG_khai_phan_chua_mo_phong_thi_NHAC(make_agent):
    """TC019 — tuyên bố đạt cho phần chưa mô phỏng là đậu giả."""
    agent = make_agent([])
    ctx = _ctx(agent)
    r = agent.registry.run("sim.criteria", {
        "assert": [{"ma": "A1", "mo_ta": "Góc", "phep_so": "<=", "nguong": 5,
                    "nguon_nguong": "tài liệu"}],
        "explain": _EX}, ctx)
    assert r.ok and "CHƯA khai phần nào không mô phỏng được" in r.data["note_vi"]


def test_tieu_chi_thieu_NGUON_NGUONG_thi_noi_ra(make_agent):
    agent = make_agent([])
    r = agent.registry.run("sim.criteria", {
        "assert": [{"ma": "A1", "mo_ta": "Góc", "phep_so": "<=", "nguong": 5}],
        "explain": _EX}, _ctx(agent))
    assert r.ok and r.data["thieu_nguon_nguong"] == ["A1"]
    assert "con số đó ở đâu ra" in r.data["note_vi"]


def test_doi_NGUONG_khi_da_co_ket_qua_thi_hook_bao_cho_cong_G_QUAL(make_agent):
    """TC022 — ca tệ nhất của cả bộ: tác tử từng ghi hẳn "khi mô phỏng thất bại thì điều
    chỉnh tiêu chí" thành LUẬT CỦA DỰ ÁN."""
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx, nguong=15.0)
    agent.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX, canonical={"dat": False})

    bus = register_standard_hooks(HookBus())
    # `explain` phải có: hook kiểm explain chạy TRƯỚC và dừng cả chuỗi nếu thiếu — nên một
    # ca đo quên nó sẽ đo nhầm hook khác.
    r = bus.pre_tool_use({"tool": "sim.criteria", "args": {
        "ma": "sim-01", "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 45.0}]}},
        ctx)
    assert r.facts["criteria.exists"] and r.facts["criteria.changed"]
    assert r.facts["criteria.has_result"] is True
    assert "A1.nguong: 15.0 → 45.0" in r.facts["criteria.doi_gi"]


def test_them_assert_MOI_cung_tinh_la_doi(make_agent):
    from eide.hooks.base import HookBus
    from eide.hooks.standard import register_standard_hooks

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx)
    bus = register_standard_hooks(HookBus())
    r = bus.pre_tool_use({"tool": "sim.criteria", "args": {
        "ma": "sim-01", "explain": _EX,
        "assert": [{"ma": "A1", "mo_ta": "Góc lớn nhất", "phep_so": "<=", "nguong": 15.0},
                   {"ma": "A2", "mo_ta": "Thêm", "phep_so": "<=", "nguong": 1}]}}, ctx)
    assert r.facts["criteria.changed"] and "A2: thêm mới" in r.facts["criteria.doi_gi"]
    # Chưa có kết quả mô phỏng thì KHÔNG phải hỏi — thêm tiêu chí lúc chưa chạy là việc bình
    # thường, và hỏi ở đó chỉ dạy người dùng bấm duyệt theo phản xạ.
    assert r.facts["criteria.has_result"] is False


# ===================================================================== G6-C · test.run
@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_test_run_dem_duoc_CA_DAT_va_CA_HONG(make_agent):
    """TC052 — một bản báo cáo bằng lời thì không đếm được, nên test phải in JSON."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test/test_pid.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": ['
        '{\\"ten\\": \\"pid_zero\\", \\"dat\\": true},'
        '{\\"ten\\": \\"pid_bao_hoa\\", \\"dat\\": false, \\"vi\\": \\"ra 300 > 255\\"}'
        ']}\\n"); return 0; }\n', "utf-8")
    r = agent.registry.run("test.run", {"explain": _EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_ca"] == 2 and r.data["so_dat"] == 1 and r.data["so_hong"] == 1
    assert r.data["dat"] is False and "ra 300 > 255" in r.data["vi_sao_khong_dat"]
    assert "1/2 ca đạt" in r.data["note_vi"]


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_test_run_KHONG_in_JSON_thi_khong_ket_luan(make_agent):
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test/t.c").write_text(
        '#include <stdio.h>\nint main(void){ printf("Tất cả test đã chạy OK\\n"); return 0; }\n',
        "utf-8")
    r = agent.registry.run("test.run", {"explain": _EX}, ctx)
    assert r.ok and r.data["dat"] is False
    assert "không đếm được" in r.data["vi_sao_khong_dat"]


def test_chua_co_test_thi_NOI_THANG_chu_khong_coi_la_dat(make_agent):
    agent = make_agent([])
    r = agent.registry.run("test.run", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4011"
    assert "đừng coi im lặng là đạt" in r.error.hint_for_agent


@pytest.mark.skipif(not co_cc, reason="không có trình biên dịch C trên máy")
def test_do_phu_khong_do_duoc_thi_NOI_RA_chu_khong_bo_cot(make_agent):
    """Im lặng bỏ cột độ phủ thì người đọc hiểu là không có gì để nói."""
    agent = make_agent([])
    ctx = _ctx(agent)
    goc = agent.config.paths.project_root
    (goc / "test").mkdir(parents=True, exist_ok=True)
    (goc / "test/t.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"ca\\": [{\\"ten\\": \\"a\\", \\"dat\\": true}]}\\n");'
        ' return 0; }\n', "utf-8")
    r = agent.registry.run("test.run", {"explain": _EX}, ctx)
    assert r.ok and "do_phu" in r.data
    assert r.data["do_phu"].get("do_duoc") in (True, False)
    if not r.data["do_phu"]["do_duoc"]:
        assert r.data["do_phu"]["vi_sao"] and "CHƯA đo được độ phủ" in r.data["note_vi"]


# ===================================================================== G6-E · bề mặt
def test_tab_Mo_phong_hien_TIEU_CHI_truoc_KET_QUA_sau(make_agent):
    """§C5 "tiêu chí nêu trước". Đặt kết quả lên trên thì người đọc thấy con số trước khi
    thấy thước đo nó."""
    from eide import surfaces as S

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx)
    agent.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "chay_duoc": True, "ma_tieu_chi": "sim-01",
                                 "xet": {"dong": [{"ma": "A1", "mo_ta": "Góc lớn nhất",
                                                   "ket_luan": "dat",
                                                   "vi": "đo được 3.0 ° · yêu cầu không quá 15.0",
                                                   "do_req": "REQ-BAL-01"}],
                                         "dem": {"dat": 1, "khong_dat": 0,
                                                 "chua_do_duoc": 0}},
                                 "ket_qua": {"do": {"A1": 3.0}}})
    m = S.simulation(agent.store, _inv_gia())
    ma = [b["id"] for b in m["blocks"]]
    assert ma.index("criteria:sim-01") < ma.index("sim_result:can-bang")

    tc = next(b for b in m["blocks"] if b["id"] == "criteria:sim-01")
    assert "Đo yêu cầu nào" in tc["columns"] and "Ngưỡng lấy từ đâu" in tc["columns"]
    assert tc["cot_sua"] == {"Ngưỡng": "nguong"} and tc["loai_sua"] == "criteria"


def test_phan_KHONG_mo_phong_duoc_co_khoi_RIENG(make_agent):
    """TC019 — nếu nó chỉ nằm trong tiêu chí thì người đọc hiểu "5/5 đạt" là "mọi thứ đạt"."""
    from eide import surfaces as S

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx)
    m = S.simulation(agent.store, _inv_gia())
    b = next(b for b in m["blocks"] if b["id"].endswith(":khong-mo-phong"))
    assert "NGOÀI mọi kết luận" in b["summary"]
    assert b["rows"][0][0] == "WS2812"


def test_tieu_chi_CHUA_xac_nhan_thi_be_mat_noi_thang(make_agent):
    from eide import surfaces as S

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx, xac_nhan=False)
    b = S.simulation(agent.store, _inv_gia())["blocks"][0]
    assert "CHƯA xác nhận" in b["summary"] and "sẽ không chạy" in b["summary"]


def test_thanh_Flash_RAM_chi_ve_khi_BIET_ngan_sach(make_agent):
    """Vẽ một thanh rỗng cho thứ chưa đo được là nói dối bằng hình."""
    from eide.surfaces import _thanh

    assert _thanh(0.08).startswith("▰") and "▱" in _thanh(0.08)
    assert _thanh(None) == "" and _thanh(0) == ""
    assert _thanh(0.99).count("▰") >= 11


def test_nguoi_sua_NGUONG_tren_bang_thi_ket_qua_cu_thanh_LOI_THOI(make_agent):
    """Để một kết quả xanh đứng cạnh một tiêu chí đã đổi là mời người đọc kết luận về mạch
    bằng một phép đo không còn hiệu lực."""
    from eide.protocol.humanact import HumanAct

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx, nguong=15.0)
    agent.store.apply(artefact_id="sim_result:can-bang", type="sim_result", op="create",
                      author="agent:run-1", explain=_EX,
                      canonical={"dat": True, "ma_tieu_chi": "sim-01"})

    seen: list = []
    agent.turn(HumanAct.from_dict({
        "kind": "edit", "target": "criteria:A1",
        "data": {"base_version": "v1", "fields": {"nguong": "8"}},
        "origin": {"surface": "simulation", "block": "criteria:sim-01", "row": "A1"},
        "note": "15 độ là quá rộng, robot đổ trước khi tới đó"}), seen.append)

    tc = agent.store.get("criteria:sim-01")["canonical"]
    a1 = next(x for x in tc["assert"] if x["ma"] == "A1")
    assert a1["nguong"] == 8.0
    # Nguồn ngưỡng đổi theo: để "§13.4 tài liệu" đứng tên một con số người vừa tự đặt là sai.
    assert "anh sửa trực tiếp" in a1["nguon_nguong"] and "robot đổ" in a1["nguon_nguong"]

    kq = agent.store.get("sim_result:can-bang")
    assert kq["stale"], "kết quả cũ phải thành lỗi thời"
    assert "15.0 → 8.0" in kq["stale_reason"]
    loi = [c for c in seen if c.method == "console.post"]
    assert loi and "LỖI THỜI" in loi[-1].params["text"]


def test_sua_nguong_bang_mot_thu_khong_phai_so_thi_KHONG_doi_gi(make_agent):
    from eide.protocol.humanact import HumanAct

    agent = make_agent([])
    ctx = _ctx(agent)
    _ghi_tieu_chi(agent, ctx, nguong=15.0)
    seen: list = []
    agent.turn(HumanAct.from_dict({
        "kind": "edit", "target": "criteria:A1",
        "data": {"base_version": "v1", "fields": {"nguong": "thấp thôi"}},
        "origin": {"surface": "simulation", "block": "criteria:sim-01"}}), seen.append)
    tc = agent.store.get("criteria:sim-01")["canonical"]
    assert next(x for x in tc["assert"] if x["ma"] == "A1")["nguong"] == 15.0
