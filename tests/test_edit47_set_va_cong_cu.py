# -*- coding: utf-8 -*-
"""Cài đặt dự án qua `set`, gộp thẻ trùng, và hai công cụ chạy — EIDE-EDIT-47 §DEV-371.

Ba chỗ người đang phải làm thay máy:

1. **bật một cờ** = sửa `.env` rồi mở lại app — mười chín cờ, mỗi cờ có một lý do và một
   cái giá nói ra được, nằm sau một thao tác không có trong giao diện;
2. **đóng hàng chục thẻ `tool.install`** cho cùng một gói, vì mỗi lời gọi đẻ một thẻ;
3. **gõ `make` hộ tác tử**, rồi dán kết quả vào ô nhập.

Bộ này không gọi mô hình thật: `ScriptedGateway` dựng đúng lời gọi công cụ cần đo.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from eide import Config, Core
from eide.config import GIAI_THICH_CO, Features
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

EX = {"summary": "chạy đường dựng của dự án", "why": "để có bitstream",
      "sources": [], "diff_prev": "chưa dựng", "next": "—", "confidence": "VANG"}

GOC = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def phien(du_an):
    def _tao(script: list | None = None, **kw):
        cfg = Config.for_project(du_an, **kw)
        a = Agent(cfg, llm=ScriptedGateway(script or []), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _tb(out):
    return " ".join(c.params.get("text", "") for c in out if c.method == "notice")


def _the(out):
    return [c.params["card"] for c in out
            if c.method == "console.post" and (c.params.get("card") or {}).get("gate_id")]


def _dat_co(core, ten, val):
    core.console_act({"kind": "set", "data": {"key": f"feature.{ten}", "value": val},
                      "origin": {"surface": "project", "block": "A14.7", "row": ten}})


# ============================================================ 1 · cài đặt dự án
def test_set_feature_ghi_vao_SETTINGS_CUA_DU_AN(phien, du_an):
    a, core, out = phien()
    assert a.config.features.bat("watcher") is False

    _dat_co(core, "watcher", True)

    p = du_an / ".eide" / "settings.json"
    assert p.exists(), "không có tệp thì cờ chỉ sống tới lúc tắt app"
    assert json.loads(p.read_text("utf-8"))["features"]["watcher"] is True
    assert a.config.features.bat("watcher") is True, "phải áp ngay trong bộ nhớ"
    assert "watcher" in _tb(out)

    # Sổ cái: một cái bấm đổi *thứ tác tử thấy mỗi lượt* phải có mặt trong sổ y như một
    # changeset. Thiếu nó thì sáu tháng sau không ai biết vì sao hai phiên cùng một dự án
    # hành xử khác nhau.
    sk = [e.data for e in a.ledger.read() if e.kind == "setting"]
    assert sk and sk[-1]["key"] == "feature.watcher" and sk[-1]["value"] is True, sk
    assert sk[-1]["boi"] == "human" and sk[-1]["act_id"]

    # Và lần mở app SAU phải thấy cờ ấy — qua đúng cửa mà `__main__` đi.
    assert Config.for_project(du_an).features.bat("watcher") is True


def test_cai_dat_DU_AN_khong_phai_cua_MAY(phien, du_an, tmp_path, monkeypatch):
    """Một cờ đổi *thứ tác tử thấy mỗi lượt*, nên nó thuộc về DỰ ÁN. Ghi vào `~/.eide`
    thì mở dự án thứ hai trong cùng buổi là đã bật cờ cho cả nó."""
    monkeypatch.setenv("HOME", str(tmp_path / "nha"))
    a, core, out = phien()
    _dat_co(core, "pdf_bang", True)

    assert not (tmp_path / "nha" / ".eide" / "settings.json").exists()
    khac = tmp_path / "du-an-khac"
    khac.mkdir()
    assert Features.load(Config.for_project(khac).paths.state_dir).bat("pdf_bang") is False


def test_THU_TU_UU_TIEN_cai_dat_du_an_thang_bien_moi_truong(du_an, monkeypatch):
    """Lệch có ý với đặc tả, và lý do nằm ở chỗ người dùng đứng:

    cài đặt dự án là một cái BẤM vừa xảy ra, ngay trước mắt họ. Nếu biến môi trường thắng
    thì cái công tắc ở tab A14 lặng lẽ không làm gì trong mọi shell có `export
    EIDE_FEATURE_*` — tức giao diện nói dối về trạng thái thật.
    """
    sd = Config.for_project(du_an).paths.state_dir
    Features.ghi_cai_dat(sd, "khoa_nguoi", True)

    monkeypatch.setenv("EIDE_FEATURE_KHOA_NGUOI", "0")
    assert Features.load(sd).bat("khoa_nguoi") is True, "cài đặt dự án đi sau cùng"
    assert Features.load().bat("khoa_nguoi") is False, "không truyền dự án thì env vẫn cai"

    # Và cài đặt Ở NHÀ thì vẫn nhường biến môi trường — nó là mặc định của người, không
    # phải một cái bấm vừa xảy ra.
    monkeypatch.setenv("HOME", str(du_an / "nha"))
    (du_an / "nha" / ".eide").mkdir(parents=True)
    (du_an / "nha" / ".eide" / "settings.json").write_text(
        json.dumps({"features": {"truy_vet": True}}), "utf-8")
    monkeypatch.setenv("EIDE_FEATURE_TRUY_VET", "0")
    assert Features.load().bat("truy_vet") is False


def test_ten_co_la_mot_cai_khong_co_thi_NOI_RA(phien):
    a, core, out = phien()
    _dat_co(core, "khong_co_co_nay", True)
    assert "khong_co_co_nay" in _tb(out) and "Đang có" in _tb(out)


def test_tep_cai_dat_VO_khong_chan_app(du_an):
    """Người sẽ mở app lên để sửa chính cái tệp ấy — và lúc ấy app phải lên được."""
    sd = Config.for_project(du_an).paths.state_dir
    (sd / "settings.json").write_text("{vỡ", "utf-8")
    assert Features.load(sd).bat("watcher") is False


def test_ghi_mot_co_KHONG_XOA_phan_con_lai(du_an):
    sd = Config.for_project(du_an).paths.state_dir
    (sd / "settings.json").write_text(
        json.dumps({"features": {"pdf_bang": True}, "thu_khac": {"x": 1}}), "utf-8")
    Features.ghi_cai_dat(sd, "watcher", True)
    d = json.loads((sd / "settings.json").read_text("utf-8"))
    assert d["features"] == {"pdf_bang": True, "watcher": True}
    assert d["thu_khac"] == {"x": 1}


def test_moi_co_co_mot_cau_giai_thich():
    """Một cái công tắc không có lời giải thích là một cái công tắc không ai dám bật."""
    thieu = [t for t in Features.ten_co() if not GIAI_THICH_CO.get(t, "").strip()]
    assert not thieu, f"thiếu câu giải thích cho: {thieu}"
    du = sorted(set(GIAI_THICH_CO) - set(Features.ten_co()))
    assert not du, f"giải thích cho cờ không còn tồn tại: {du}"


def test_TAB_A14_co_khoi_cai_dat_va_no_GUI_BANG_SET(du_an):
    """Lõi khai, giao diện không suy (I8). Một cờ không phải hiện vật trong kho — không
    phiên bản, không changeset — nên nó gửi `set`, không gửi `edit`."""
    from eide import surfaces

    cfg = Config.for_project(du_an)
    cfg.features.watcher = True
    k = surfaces.cai_dat_du_an(cfg)
    assert k["code"] == "A14.7" and k["type"] == "kv"
    assert k["sua_duoc"]["gui_bang"] == "set"
    assert k["sua_duoc"]["truong"][0]["kieu"] == "bool"
    assert k["sua_duoc"]["truong"][0]["path"] == "feature.{ma}"

    dong = {p[0]: p for p in k["pairs"]}
    assert set(dong) == set(Features.ten_co())
    assert dong["watcher"][1] == "có" and dong["pdf_bang"][1] == "không"
    assert "4,3" in dong["pdf_bang"][2], "cái giá đo được phải nằm ngay trên dòng ấy"

    # Và nó phải tới được tab thật, không chỉ tồn tại trong một hàm không ai gọi.
    from eide.store import EideMd

    mat = surfaces.project(EideMd(cfg.paths.eide_md), _inv(cfg), [], cfg)
    assert any(b["code"] == "A14.7" for b in mat["blocks"])


def test_APP_doc_duoc_khoi_ay(du_an):
    """Lõi gửi mà app không đọc thì cái công tắc không tồn tại với người dùng — lỗi lặp
    lại nhiều nhất của dự án này là *"cơ chế có sẵn, đường dẫn tới nó đứt"*."""
    sv = (GOC / "ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift").read_text("utf-8")
    fe = (GOC / "ui/EIDEApp/Sources/EIDE/Views/FormEditor.swift").read_text("utf-8")
    assert 'raw["gui_bang"]' in fe and "static func actDat" in fe
    assert 'sd.guiBang == "set"' in sv and "struct CongTac" in sv


def _inv(cfg):
    from eide.protocol.ledger import Ledger
    from eide.store import Store, inventory

    return inventory.build(Store(cfg.paths.store_db), ledger=Ledger(cfg.paths.ledger),
                           project_name="du-an-thu")


# ============================================================ 2 · gộp thẻ trùng
def _script_cai(ds: list[str]):
    """Một Response cho MỖI LƯỢT. Thẻ cổng đầu tiên làm lượt DỪNG (I6), nên nhiều lời gọi
    trong cùng một Response thì những lời sau không bao giờ chạy — chỗ thẻ trùng sinh ra
    là **lượt sau**, khi thẻ cũ vẫn còn treo chưa ai trả lời."""
    return [Response(tool_calls=[ToolCall(f"c{i}", "tool.install",
                                          {"cong_cu": g, "isa": "avr8",
                                           "explain": {**EX, "summary": f"lần {i}"}})])
            for i, g in enumerate(ds)] + [Response(text="xong")]


def test_GOI_LAI_cung_mot_goi_khi_the_con_treo_thi_khong_de_the_moi(phien):
    """Đo được trên phiên FPGA: `tool.install` cho `oss-cad-suite` được gọi lại nhiều lượt
    (mỗi lần tải 483 MB nên nó hết hạn lượt giữa đường), và mỗi lần đẻ một thẻ mới trong
    khi thẻ cũ vẫn treo.

    Một chồng thẻ hỏi cùng một câu là cách nhanh nhất dạy người ta bấm Duyệt mà không đọc.
    """
    a, core, out = phien(_script_cai(["avr-gcc"] * 4), autonomy="A1")
    for _ in range(4):
        core.console_act({"kind": "say", "text": "cài avr-gcc giúp tôi"})

    the = _the(out)
    assert len(the) == 1, [t["title"] for t in the]
    assert len(a.pending_gates) == 1
    # Và những lần sau nhận lại ĐÚNG mã thẻ cũ, không nhận một mã mới.
    gid = the[0]["gate_id"]
    ds = [e.data for e in a.ledger.read() if e.kind == "gate"]
    trung = [d for d in ds if d.get("state") == "trung_the_dang_cho"]
    assert len(trung) == 3, ds
    assert all(d["gate_id"] == gid for d in trung)


def test_GOI_KHAC_thi_van_la_the_khac(phien):
    a, core, out = phien(_script_cai(["avr-gcc", "avrdude"]), autonomy="A1")
    core.console_act({"kind": "say", "text": "cài avr-gcc"})
    core.console_act({"kind": "say", "text": "cài avrdude"})
    assert len({t["gate_id"] for t in _the(out)}) == 2


def test_van_tay_viec_BO_QUA_explain(phien):
    """`explain` là lời mô hình tự soạn, khác nhau từng lần kể cả khi việc y hệt. So cả
    `explain` thì phép gộp thẻ không bao giờ khớp — một cơ chế có mà không bao giờ nổ."""
    a, _, _ = phien()
    v1 = a._van_tay_viec("tool.install", {"cong_cu": "x", "explain": {"summary": "a"}})
    v2 = a._van_tay_viec("tool.install", {"cong_cu": "x", "explain": {"summary": "b"}})
    v3 = a._van_tay_viec("tool.install", {"cong_cu": "y", "explain": {"summary": "a"}})
    assert v1 == v2 and v1 != v3


# ============================================================ 3 · build.make
def _mk(du_an, than: str, ten: str = "Makefile", thu_muc: str = "") -> None:
    d = du_an / thu_muc if thu_muc else du_an
    d.mkdir(parents=True, exist_ok=True)
    (d / ten).write_text(than, "utf-8")


def _goi(a, ten, **args):
    """Gọi thẳng một công cụ, không qua mô hình. Cổng thì đo riêng ở phần trên."""
    from eide.loop import TurnContext

    ctx = TurnContext(config=a.config, store=a.store, ledger=a.ledger, eide_md=a.eide_md,
                      ids=a.ids, registry=a.registry, emit=lambda c: None,
                      history=a.history, agent=a, run_id="run-do",
                      project_name="du-an-thu")
    return a.registry.run(ten, {"explain": EX, **args}, ctx)


def test_build_make_chay_DUONG_DUNG_CUA_DU_AN(phien, du_an):
    a, core, out = phien()
    _mk(du_an, "all:\n\t@echo da-dung-xong > ket-qua.txt\n")
    r = _goi(a, "build.make", target="all")
    assert r.ok, r.error
    assert (du_an / "ket-qua.txt").read_text("utf-8").strip() == "da-dung-xong"
    hv = a.store.get(r.data["hien_vat"])
    assert hv and hv["canonical"]["ma_thoat"] == 0, "chạy xong phải ghi sổ (lớp 3)"
    assert hv["canonical"]["lenh"] == "make all"


def test_build_make_MA_THOAT_KHAC_0_la_mot_KET_QUA(phien, du_an):
    """Gói một lần dựng đổ thành `ok=True` là đúng thứ `build.compile` được viết để không
    làm: *"không có bằng chứng thì không có kết luận"*."""
    a, core, out = phien()
    _mk(du_an, "all:\n\t@echo loi-day >&2; exit 3\n")
    r = _goi(a, "build.make", target="all")
    assert not r.ok and r.error.code == "E4002"
    assert "loi-day" in r.error.hint_for_agent
    assert a.store.get("build:make:all")["canonical"]["dat"] is False


def test_build_make_NGOAI_HOP_CAT_bi_chan(phien, du_an):
    a, core, out = phien()
    r = _goi(a, "build.make", cwd="../../..")
    assert not r.ok, r.data
    assert "ngoài vùng làm việc" in r.error.message_vi, r.error.message_vi


def test_build_make_KHONG_CO_MAKEFILE_thi_noi_that(phien, du_an):
    a, core, out = phien()
    r = _goi(a, "build.make")
    assert not r.ok and "Makefile" in r.error.message_vi
    assert "build.compile" in (r.error.alternatives or [])


def test_hai_cong_cu_moi_DI_QUA_CONG(phien, du_an):
    """Không phải vì chúng nguy hiểm hơn `build.compile`, mà vì `make` chạy **bất kỳ thứ
    gì** trong Makefile — và Makefile là một tệp trong dự án mà chính tác tử ghi được."""
    a, core, out = phien()
    for ten in ("build.make", "py.run"):
        spec = a.registry.get(ten)
        assert spec is not None and spec.gate == "G-OPS" and spec.risk == "R3", ten
        assert spec.needs_explain and not spec.core, ten


def test_mot_luot_dung_nhieu_lan_chi_duyet_MOT_LAN(phien, du_an):
    """Mười lần dựng trong một vòng sửa–dựng–sửa không được thành mười lần bấm Duyệt."""
    _mk(du_an, "all:\n\t@true\n")
    a, core, out = phien([
        Response(tool_calls=[ToolCall("c1", "build.make", {"target": "all",
                                                           "explain": EX})]),
        Response(tool_calls=[ToolCall("c2", "build.make", {"target": "all",
                                                           "explain": EX}),
                             ToolCall("c3", "build.make", {"target": "all",
                                                           "explain": EX})]),
        Response(text="xong"),
    ], autonomy="A1")
    core.console_act({"kind": "say", "text": "dựng giúp tôi"})
    gid = _the(out)[0]["gate_id"]
    out.clear()
    core.console_act({"kind": "decide",
                      "data": {"gate_id": gid, "approved": True},
                      "origin": {"surface": "console"}})
    assert not _the(out), "đã duyệt trong lượt này thì không hỏi lại"
    ds = [e.data for e in a.ledger.read() if e.kind == "gate"]
    assert any(d.get("state") == "da_duyet_truoc_do" for d in ds), ds


# ============================================================ 4 · py.run
def test_py_run_tra_dung_MA_THOAT_cho_tac_tu(phien, du_an):
    a, core, out = phien()
    (du_an / "vo.py").write_text("import sys\nprint('tới đây rồi')\nsys.exit(2)\n", "utf-8")
    r = _goi(a, "py.run", path="vo.py")
    assert not r.ok and r.error.details["ma_thoat"] == 2
    assert "tới đây rồi" in r.error.hint_for_agent
    assert a.store.get("build:py:vo.py")["canonical"]["dat"] is False


def test_py_run_chay_duoc_va_ghi_DAU_RA(phien, du_an):
    a, core, out = phien()
    (du_an / "do.py").write_text("print('ket qua: 42')\n", "utf-8")
    r = _goi(a, "py.run", path="do.py")
    assert r.ok, r.error
    assert "ket qua: 42" in a.store.get("build:py:do.py")["canonical"]["nguyen_van"]


def test_py_run_nhan_THAM_SO(phien, du_an):
    a, core, out = phien()
    (du_an / "cong.py").write_text("import sys\nprint(sum(int(x) for x in sys.argv[1:]))\n",
                                   "utf-8")
    r = _goi(a, "py.run", path="cong.py", args=["2", "40"])
    assert r.ok and "42" in r.data["nguyen_van"]


def test_py_run_KHONG_chay_tep_ngoai_goc_du_an(phien, du_an, tmp_path):
    """Hộp cát phải canh cả cửa này. Một đường chạy mã ngoài dự án là một đường chạy mã
    bất kỳ trên máy — và lúc ấy mọi luật khác chỉ còn là trang trí."""
    ngoai = tmp_path / "ngoai.py"
    ngoai.write_text("print('tôi ở ngoài dự án')\n", "utf-8")
    a, core, out = phien()
    r = _goi(a, "py.run", path=str(ngoai))
    assert not r.ok
    assert "ngoài" in r.error.message_vi.lower() or r.error.code == "E4010", \
        r.error.to_dict()


def test_py_run_CHI_CHAY_TEP_PY(phien, du_an):
    a, core, out = phien()
    (du_an / "chay.sh").write_text("echo xin chao\n", "utf-8")
    r = _goi(a, "py.run", path="chay.sh")
    assert not r.ok and r.error.code == "E4007"


def test_py_run_dung_PYTHON_CUA_LOI(phien, du_an):
    """`.venv` của dự án, không phải `python3` trên PATH: "chạy được trên máy tôi" phải
    nói về đúng cái môi trường lõi đang chạy.

    Hỏi hàm chọn trình thông dịch, không đọc đầu ra: khi `.venv/bin` đang nằm trên PATH
    thì `python3` TRÙNG với trình của lõi, nên một phép đo qua đầu ra sẽ xanh cả khi mã
    chọn sai — và nó xanh đúng trên máy của người đang sửa mã.
    """
    import sys

    from eide.tools.xay_dung import _python_cua_may

    assert _python_cua_may() == sys.executable

    a, core, out = phien()
    (du_an / "ai.py").write_text("import sys\nprint(sys.executable)\n", "utf-8")
    r = _goi(a, "py.run", path="ai.py")
    assert r.ok and sys.executable in r.data["nguyen_van"]


def test_QUA_HAN_thi_dung_lai_va_KHONG_bao_xong(phien, du_an, monkeypatch):
    """Một lệnh treo không được giữ cả lượt làm con tin, và càng không được thành "xong".

    Trần thật là 900 giây (một lần tải `oss-cad-suite` mất gần thế). Ở đây hạ xuống để đo
    được — bộ kiểm chờ 900 giây là bộ kiểm không ai chạy lại.
    """
    from eide.tools import xay_dung as xd

    monkeypatch.setattr(xd, "GIAY_CHAY", 0.8)
    a, core, out = phien()
    (du_an / "treo.py").write_text("import time\nprint('bat dau')\ntime.sleep(30)\n",
                                   "utf-8")
    r = _goi(a, "py.run", path="treo.py")
    assert not r.ok
    assert "quá hạn" in r.error.message_vi, r.error.message_vi
    hv = a.store.get("build:py:treo.py")
    assert hv["canonical"]["qua_han"] is True and hv["canonical"]["dat"] is False


def test_DAU_RA_QUA_LON_bi_cat_GIUA(phien, du_an):
    """Đầu ra đi vào ngữ cảnh của lượt sau. Một bản `make` nói 4 MB cảnh báo sẽ đẩy mọi
    khối khác ra khỏi cửa sổ — tức một lần dựng ồn ào xoá sạch thứ tác tử cần để hiểu dự
    án. Cắt ở GIỮA vì dòng lỗi đầu và dòng kết luận cuối là hai thứ luôn đáng đọc.
    """
    from eide.tools.xay_dung import TRAN_DAU_RA

    a, core, out = phien()
    (du_an / "on.py").write_text(
        "print('DONG-DAU')\n"
        f"print('x' * {TRAN_DAU_RA * 2})\n"
        "print('DONG-CUOI')\n", "utf-8")
    r = _goi(a, "py.run", path="on.py")
    assert r.ok, r.error
    nv = r.data["nguyen_van"]
    assert len(nv) <= TRAN_DAU_RA + 200, len(nv)
    assert "DONG-DAU" in nv and "DONG-CUOI" in nv, "cắt mất một trong hai đầu"
    assert r.data["da_cat_dau_ra"] is True, "cắt mà không khai là nói sai về đầu ra"
