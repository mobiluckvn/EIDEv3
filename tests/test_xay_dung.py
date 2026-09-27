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
def test_mo_phong_bao_KHONG_DAT_thi_cong_cu_khong_doi_thanh_dat(tmp_path):
    (tmp_path / "sim").mkdir()
    (tmp_path / "sim/main.c").write_text(
        '#include <stdio.h>\n'
        'int main(void){ printf("{\\"dat\\": false, \\"vi_sao\\": \\"ngã ở giây 2\\"}\\n");'
        ' return 1; }\n', "utf-8")
    kq = MP.chay_mo_phong(goc=tmp_path, nguon=[tmp_path / "sim/main.c"])
    assert kq.chay_duoc and not kq.dat and "ngã ở giây 2" in kq.vi_sao_khong_dat


# ===================================================================== qua công cụ
def test_build_compile_khong_co_ma_nguon_thi_tu_choi(make_agent):
    agent = make_agent([])
    r = agent.registry.run("build.compile", {"sketch": "khong-co", "explain": _EX},
                           _ctx(agent))
    assert not r.ok and r.error.code == "E4001"


def test_sim_run_chua_tach_logic_thi_CHI_DUONG_chu_khong_bia(make_agent):
    agent = make_agent([])
    r = agent.registry.run("sim.run", {"explain": _EX}, _ctx(agent))
    assert not r.ok and r.error.code == "E4003"
    assert "ĐÚNG mã sẽ nạp vào chip" in r.error.hint_for_agent


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
