# -*- coding: utf-8 -*-
"""Màn hình tương tác: đổi dự án phải sạch, và số đo phải sống khi lượt đang chạy.

Anh Công báo ba việc:

1. *"khi tạo mới dự án thì màn hình này vẫn lưu thông tin chat của dự án khác"*
2. *"chưa cập nhật các thông tin như token, số lần gọi tool ở thanh trạng thái"*
3. *"review kỹ các label status xem cái nào chưa tích hợp"*

Đo lại thì cả ba đều đúng, và chỗ hỏng lớn hơn phần nhìn thấy:

* `AppState.mo()` khởi động lõi mới nhưng **không xoá gì**. Chat của dự án cũ ở lại — và cùng
  với nó là `cards`, tức các **thẻ cổng đang chờ duyệt** của một dự án khác.
* Một lượt chỉ có hai mốc tin: `run.update` lúc bắt đầu (chi phí rỗng) và lúc kết thúc. Ở giữa
  — nơi tác tử gọi mười công cụ — thanh trạng thái đứng nguyên `0/40 tool · 0/300 s`.
* `paint(only=["history"])` vẫn gửi kèm thanh trạng thái với `run=None`, nên bộ đếm **chạy
  ngược về 0** giữa một lượt đang chạy. *Một con số đi lùi tệ hơn một con số đứng yên: đứng
  yên là chưa biết, đi lùi là nói sai.*
* `isa` lõi gửi từ đầu mà **không nhãn nào vẽ**; token đã tiêu thì không có trong mô hình.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

import pytest

from eide import surfaces as S

GOC = pathlib.Path(__file__).resolve().parents[1]
UI = GOC / "ui/EIDEApp/Sources/EIDE"


# ====================================================== thanh trạng thái: token và ngân sách
class InvGia:
    project_name = "du-an"
    branch = "main"
    passport = "st.stm32f469@1.0.0"
    isa = "armv7e-m"
    fact_tiers: dict[str, int] = {}
    last_snapshot = None
    changesets_since_snapshot = 0
    stale: list[Any] = []

    def _stage(self) -> str:
        return "C1"


class CfgGia:
    class budget:
        max_tool_calls = 40
        max_seconds = 300

    autonomy = "A3"

    class model:
        main = "gemini-3.8-flash"


def _thanh(run: dict[str, Any] | None = None) -> dict[str, Any]:
    return S.status_bar(InvGia(), CfgGia(), run=run)


def test_thanh_trang_thai_CO_token():
    """Trước đây token chỉ tồn tại trong thẻ Run — mà thẻ ấy biến mất khi lượt xong."""
    t = _thanh({"cost": {"tokens": {"in": 1200, "out": 300, "cached": 900},
                         "phien": {"in": 40000, "out": 5000, "cached": 30000}}})["token"]
    assert t["luot"] == 1500 and t["phien"] == 45000
    assert t["luot_cache"] == 900 and t["phien_cache"] == 30000


def test_token_cache_KHONG_gop_vao_tong():
    """`cached` rẻ hơn token thường nhiều lần — gộp vào là làm người đọc tưởng đắt hơn thực."""
    t = _thanh({"cost": {"tokens": {"in": 100, "out": 50, "cached": 10_000}}})["token"]
    assert t["luot"] == 150


def test_khong_co_run_thi_token_bang_khong_chu_khong_no():
    for run in (None, {}, {"cost": {}}):
        assert _thanh(run)["token"] == {
            "luot": 0, "phien": 0, "luot_vao": 0, "luot_ra": 0, "luot_cache": 0,
            "phien_vao": 0, "phien_ra": 0, "phien_cache": 0}


def test_ngan_sach_van_doc_duoc_tu_bao_cao_luot():
    b = _thanh({"tool_calls": 7, "seconds": 12.5})["ngan_sach"]
    assert b["da_dung_tool"] == 7 and b["da_dung_giay"] == 12.5


# =============================================== bộ đếm KHÔNG được chạy ngược giữa lượt
class EmitGia:
    def __init__(self) -> None:
        self.lenh: list[Any] = []

    def __call__(self, c: Any) -> None:
        self.lenh.append(c)

    def thanh_trang_thai(self) -> dict[str, Any] | None:
        for c in reversed(self.lenh):
            p = getattr(c, "params", {}) or {}
            if getattr(c, "method", "") == "ui.set" and p.get("key") == "status_bar":
                return p.get("value")
        return None


def test_ve_lai_CUC_BO_khong_lam_bo_dem_chay_nguoc(tmp_path, monkeypatch):
    """`paint(only=["history"])` không được đẩy `0/40 tool` đè lên con số đang chạy.

    Xảy ra thật mỗi khi người ghi bản ưng ý hoặc rẽ nhánh giữa lượt.
    """
    from eide import loop as L

    class KhoGia:
        def list(self, *a: Any, **k: Any) -> list[Any]:
            return []

        def get(self, *a: Any, **k: Any) -> None:
            return None

    class AgentGia:
        last_report = {"tool_calls": 9, "seconds": 31.0,
                       "cost": {"tokens": {"in": 100, "out": 20}, "tools": 9, "seconds": 31.0}}
        paint = L.Agent.paint
        store = KhoGia()
        ledger = eide_md = history = None
        config = CfgGia()
        project_name = "du-an"
        pending_cards: list[Any] = []
        assumptions: list[str] = []

        def ngu_canh_hien_tai(self):
            return {}

        def _mat_bang_bo_nho(self):
            return {}

    a = AgentGia()
    monkeypatch.setattr(L.inventory, "build", lambda *x, **k: InvGia())
    e = EmitGia()
    a.paint(e, only=["history"])                      # KHÔNG truyền run
    tt = e.thanh_trang_thai()
    assert tt is not None
    assert tt["ngan_sach"]["da_dung_tool"] == 9, "bộ đếm bị đẩy về 0 khi vẽ lại cục bộ"
    assert tt["token"]["luot"] == 120


# ======================================================= nhịp giữa lượt: lõi có phát không
def test_lõi_phat_NHIP_sau_moi_loi_goi_cong_cu():
    """Đọc chính mã vòng lặp: `_nhip` phải nằm ngay sau `_one_tool`, trong vòng lặp công cụ.

    Bản đầu của ca này **vô nghĩa**: nó dò `for call in rsp.tool_calls:` trên cả tệp, mà chuỗi
    ấy cũng nằm trong docstring đầu `loop.py` — nên nó bắt trọn hơn sáu trăm dòng và luôn
    thấy `_nhip` ở đâu đó. Gỡ hẳn lời gọi ra, ca vẫn xanh.

    Nay dò **thân vòng lặp thật**: đúng thụt lề, và chỉ những dòng cùng cấp với `_one_tool`.
    """
    src = (GOC / "src/eide/loop.py").read_text("utf-8").split("\n")
    # Neo vào dòng NGAY SAU vòng lặp, không neo vào dòng `for`: docstring đầu tệp cũng có
    # `for call in rsp.tool_calls:` với đúng thụt lề ấy, và đó chính là chỗ bản đầu bắt nhầm.
    #
    # M1-01 đổi dòng `for` thành `for k, call in enumerate(...)` (cần chỉ số k để trả
    # E4031 cho các lời gọi sau cổng). Neo nhận cả hai cách viết: thứ ca này đo là
    # "`_nhip` nằm ngay sau `_one_tool` trong thân vòng lặp", không phải cách gõ dòng `for`.
    _FOR = ("for call in rsp.tool_calls:", "for k, call in enumerate(rsp.tool_calls):")
    i = next((k for k, l in enumerate(src)
              if l.strip() in _FOR
              and src[k + 1].strip().startswith("self._one_tool(")), None)
    assert i is not None, "không tìm thấy vòng lặp gọi công cụ trong thân hàm"
    than = []
    for l in src[i + 1:]:
        if l.strip() and not l.startswith("                "):
            break
        than.append(l)
    than = "\n".join(than)
    assert "self._one_tool(call, ctx)" in than
    assert "self._nhip(ctx)" in than, "không báo số đo sau mỗi lời gọi công cụ"
    # Chống vô nghĩa: thân vòng lặp là vài dòng, không phải nửa tệp.
    assert len(than.split("\n")) < 12, f"bắt nhầm quá nhiều dòng ({len(than.splitlines())})"


def test_nhip_mang_du_ba_con_so():
    from eide import loop as L

    class CtxGia:
        run_id = "run-001"
        tool_calls_used = 5
        elapsed = 7.25
        usage_luot = None

        def __init__(self) -> None:
            self.da_gui: list[Any] = []

        def emit(self, c: Any) -> None:
            self.da_gui.append(c)

    class U:
        def to_dict(self):
            return {"in": 10, "out": 4, "cached": 0, "thoughts": 0}

    class AgentGia:
        usage_phien = U()
        _nhip = L.Agent._nhip
        _chi_phi = L.Agent._chi_phi

    ctx = CtxGia()
    ctx.usage_luot = U()
    AgentGia()._nhip(ctx)
    assert len(ctx.da_gui) == 1
    p = ctx.da_gui[0].params
    assert p["status"] == "running"
    assert p["cost"]["tools"] == 5 and p["cost"]["seconds"] == 7.25
    assert p["cost"]["tokens"]["in"] == 10


def test_nhip_IM_khi_chua_co_luot():
    from eide import loop as L

    class CtxGia:
        run_id = ""
        tool_calls_used = 0
        elapsed = 0.0
        usage_luot = None
        da_gui: list[Any] = []

        def emit(self, c):
            self.da_gui.append(c)

    class AgentGia:
        usage_phien = None
        _nhip = L.Agent._nhip
        _chi_phi = L.Agent._chi_phi

    ctx = CtxGia()
    AgentGia()._nhip(ctx)
    assert ctx.da_gui == []


# ================================================== giao diện: đổi dự án phải xoá sạch
# Ba ca dưới đọc chính tệp Swift. Không chạy được Swift trong pytest, nhưng câu hỏi ở đây là
# *"danh sách có đủ không"* — và đó là câu đọc mã trả lời được, rẻ hơn dựng cả app.

def _appstate() -> str:
    return (UI / "State/AppState.swift").read_text("utf-8")


# `draft` và `selectedSurface` cố ý KHÔNG xoá — xem chú thích ở `doiDuAn`.
GIU_LAI = {"draft", "selectedSurface", "consoleWidth", "connection", "duAnDir"}


def test_doi_du_an_xoa_MOI_truong_thuoc_ve_du_an():
    """Thêm một `@Published` mới mà quên thêm vào `doiDuAn` thì nó rò từ dự án này sang kia."""
    s = _appstate()
    khai = set(re.findall(r"@Published var (\w+)", s))
    than = s.split("func doiDuAn(")[1].split("\n    }")[0]
    quen = {t for t in khai - GIU_LAI if t not in than}
    assert not quen, f"`doiDuAn` chưa dọn: {sorted(quen)}"


def test_transcript_va_cards_nam_trong_danh_sach_don():
    """Hai cái quan trọng nhất, ghim riêng để không ai lỡ tay bỏ.

    `transcript` là phần anh Công nhìn thấy; `cards` là phần nguy hơn — một thẻ cổng còn chờ
    duyệt của dự án cũ mà bấm *Duyệt* thì là gửi quyết định cho một lõi đã chết.
    """
    than = _appstate().split("func doiDuAn(")[1].split("\n    }")[0]
    for t in ("transcript.removeAll()", "cards.removeAll()", "run = nil"):
        assert t in than, f"thiếu `{t}`"


def test_mo_du_an_GOI_doiDuAn_truoc_khi_khoi_dong_loi():
    s = _appstate()
    than = s.split("func mo(")[1].split("\n    }")[0]
    i_don, i_chay = than.find("doiDuAn("), than.find("client.start(")
    assert i_don >= 0, "`mo()` không dọn trạng thái dự án cũ"
    assert i_don < i_chay, "phải dọn TRƯỚC khi lõi mới bắt đầu gửi lệnh"


def test_draft_cua_nguoi_KHONG_bi_xoa():
    """Chữ người tự gõ mà chưa gửi là việc của người — không xoá để cho gọn màn hình của máy."""
    than = _appstate().split("func doiDuAn(")[1].split("\n    }")[0]
    assert "draft" not in than


# ================================================ giao diện: nhãn nào lõi gửi mà chưa vẽ
def _views() -> str:
    return "\n".join(p.read_text("utf-8") for p in (UI / "Views").glob("*.swift"))


@pytest.mark.parametrize("truong", sorted(_thanh().keys()))
def test_moi_truong_thanh_trang_thai_deu_co_nguoi_doc(truong):
    """Lõi gửi một trường mà không nhãn nào vẽ thì nó chỉ tồn tại trong JSON.

    Đúng chuyện đã xảy ra với `isa`: tập lệnh quyết định mọi cờ biên dịch, gửi lên từ đầu,
    và chưa bao giờ hiện ra màn hình.
    """
    assert f"status.{truong}" in _views(), f"`{truong}` lõi gửi mà giao diện không đọc"


@pytest.mark.parametrize("truong", ["luot", "phien", "luot_vao", "luot_ra", "luot_cache",
                                    "phien_vao", "phien_ra", "phien_cache"])
def test_moi_truong_token_deu_hien_ra_dau_do(truong):
    assert f".{truong}" in _views(), f"`token.{truong}` gửi mà không ai đọc"


def test_ngan_sach_doc_bo_dem_SONG_truoc_roi_moi_toi_thanh_trang_thai():
    """`state.run` cập nhật sau mỗi lời gọi công cụ; `state.status` chỉ ở cuối lượt.

    Đọc ngược thứ tự thì suốt một lượt dài con số đứng nguyên ở `0/40`.
    """
    v = (UI / "Views/RootView.swift").read_text("utf-8")
    than = v.split("struct NganSachView")[1].split("\nstruct ")[0]
    assert "state.run?.tools" in than and "b.da_dung_tool" in than
    assert than.find("dangChay ?") < than.find("b.da_dung_tool")
