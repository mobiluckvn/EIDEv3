# -*- coding: utf-8 -*-
"""Trả nợ giao diện của EDIT-47 — EIDE-EDIT-47 §DEV-380.

Bốn món nợ đọng từ các gói trước, mỗi món là một chỗ **lõi đã có mà người không chạm tới
được**:

| Nợ | Từ gói | Vì sao nó là nợ thật |
|---|---|---|
| Cuộn đồng bộ hai cột diff | DEV-366 | mỗi cột một thanh cuộn → đọc diff 200 dòng thành canh hai thanh bằng tay |
| `diff_tom_tat` chưa vẽ | DEV-366 | lõi tính "mỗi hiện vật đổi mấy dòng" và gửi đi; app bỏ qua |
| Thẻ phương án không có nút "Sửa" | DEV-370 | A2.3 sửa được từ DEV-368, nhưng người đọc thẻ không biết chỗ ấy ở đâu |
| Không có nút "quét lại ngay" | DEV-369 | người vừa làm gì ngoài app, quay sang EIDE, và chỉ còn cách chờ |

Phần Swift của chúng đo ở `ui/EIDEApp/Tests/EIDETests/`; bộ này đo phía **lõi khai gì** và
hai ca đọc mã Swift để canh đường dẫn không đứt.
"""

from __future__ import annotations

import pathlib

import pytest

from eide import Config, Core, surfaces
from eide.llm import ScriptedGateway
from eide.llm.gateway import Response, ToolCall
from eide.loop import Agent

GOC = pathlib.Path(__file__).resolve().parents[1]
SW = GOC / "ui/EIDEApp/Sources/EIDE/Views"


def _ma_swift(tep: pathlib.Path) -> str:
    """Mã Swift ĐÃ BỎ dòng chú thích.

    Hai ca dưới đây đếm số lần một tên xuất hiện (định nghĩa + chỗ gọi). Không bỏ chú
    thích thì chúng đếm cả cái tên nằm trong một câu `/// … xem `haiCotCuonCungNhau``, nên
    phép phá "giữ hàm, bỏ chỗ gọi" vẫn xanh. Đúng cùng một bẫy đã sập ở
    `test_edit47_watcher._than_ma` hôm nay: phép đo đọc văn xuôi của mình rồi báo xanh.
    """
    return "\n".join(d for d in tep.read_text("utf-8").splitlines()
                      if not d.lstrip().startswith(("///", "//", "#")))

EX = {"summary": "ghi", "why": "w", "sources": [], "diff_prev": "đầu", "next": "—",
      "confidence": "VANG"}


@pytest.fixture
def phien(du_an):
    def _tao(script: list | None = None, **co):
        cfg = Config.for_project(du_an)
        for k, v in co.items():
            setattr(cfg.features, k, v)
        a = Agent(cfg, llm=ScriptedGateway(script or []), project_name="du-an-thu")
        out: list = []
        core = Core(a.ledger, a.ids, a.turn, on_emit=out.append, on_sync=a.paint,
                    on_query=a.hoi_chi_doc)
        return a, core, out
    return _tao


def _the(out):
    return [c.params["card"] for c in out
            if c.method == "console.post" and (c.params.get("card") or {})]


def _tb(out):
    return " ".join(c.params.get("text", "") for c in out if c.method == "notice")


def _a11(a):
    from eide.store import inventory

    inv = inventory.build(a.store, ledger=a.ledger, project_name="du-an-thu")
    return {b["code"]: b for b in surfaces.history(a.store, inv, a.history)["blocks"]}


# =================================================== 1 · cuộn đồng bộ hai cột
def test_hai_cot_diff_cuon_CUNG_NHAU():
    """Một khung cuộn dọc bọc cả hai cột, nên chúng cuộn cùng nhau **vì cấu trúc** — không
    phải vì một phép đồng bộ hai chiều phải tự giữ cho khỏi lệch.

    Đo bằng cách đọc mã: SwiftUI không có chỗ nào để hỏi "hai cột này có cùng offset
    không" từ ngoài, và một ca kiểm giao diện dựng ra để trả lời câu ấy sẽ chỉ đo lại
    chính phép dựng của mình.
    """
    s = _ma_swift(SW / "DiffView.swift")
    # Phải xuất hiện HAI lần TRONG MÃ: một lần định nghĩa, một lần được GỌI trong `body`.
    # Đếm cả chú thích thì phép phá "giữ hàm, bỏ chỗ gọi" lọt — hàm vẫn còn trong tệp mà
    # màn hình thì quay về hai thanh cuộn.
    assert s.count("haiCotCuonCungNhau") == 2, s.count("haiCotCuonCungNhau")
    # Nhãn cột nằm NGOÀI khung cuộn: cuộn 50 dòng mà không biết đang đọc cột nào thì hai
    # cột cạnh nhau cũng chẳng để làm gì.
    i = s.index("private var haiCotCuonCungNhau")
    than = s[i:i + 900]
    assert than.index("nhanCot") < than.index("ScrollView(.vertical)")
    # Và phần vẽ dòng KHÔNG được có khung cuộn dọc riêng nữa.
    j = s.index("private func dongCua")
    assert "ScrollView(.vertical)" not in s[j:j + 500]


def test_mot_ban_ve_dong_diff_KHONG_phai_hai():
    """`cot(...)` cũ (ca cột phải là ô soạn) phải dựng từ cùng hai phần với cột cuộn đồng
    bộ. Hai bản vẽ cùng một dòng sẽ lệch nhau ở màu hoặc ở số dòng, và lệch ở đây nghĩa là
    người đọc hai diff khác nhau tuỳ chỗ nó hiện ra."""
    s = _ma_swift(SW / "DiffView.swift")
    i = s.index("private func cot(nhan:")
    than = s[i:s.index("private var cotSuaDuoc")]
    assert "nhanCot(nhan)" in than and "dongCua(dong, ben: ben)" in than
    assert "ForEach" not in than, "không vẽ lại dòng lần thứ hai"


# =================================================== 2 · diff_tom_tat được vẽ
def test_LOI_tra_diff_tom_tat_va_APP_ve_no(phien, du_an):
    """Lõi tính `diff_tom_tat` từ DEV-366 và gửi đi; app **chưa bao giờ vẽ**. Người đọc
    được câu "sẽ mất gì" nhưng không thấy mất BAO NHIÊU, nên một bản ưng ý cách hiện tại
    hai mươi hiện vật trông y như một bản cách một hiện vật."""
    a, core, out = phien()
    a.store.apply(artefact_id="FR-01", type="req", op="create", author="agent:run-1",
                  canonical={"text": "≥ 1 MB/s"}, explain=EX)
    snap = a.history.tao_snapshot(ten="trước khi sửa", boi="human")
    a.history.ghi_kho(author="human", artefact_id="FR-01", type="req", op="update",
                      canonical={"text": "≥ 5 MB/s"}, explain=EX)

    kq = a.hoi_chi_doc("history.preview_restore", {"snapshot_id": snap.id})
    assert kq["ok"] is True
    dt = kq["diff_tom_tat"]
    assert [x["id"] for x in dt] == ["FR-01"]
    assert dt[0]["viec"] == "quay về bản cũ"
    # Một ô bị SỬA đếm vào `doi`; `them`/`bot` bằng 0. Khung đầu tiên tôi vẽ chỉ hiện
    # `+them −bot`, nên nó in "+0 −0" cho đúng ca thường gặp nhất — tức nói "không đổi gì"
    # về một thay đổi. Ca kiểm này là chỗ bắt được chuyện ấy.
    assert dt[0]["doi"] >= 1, dt[0]
    assert dt[0]["them"] == 0 and dt[0]["bot"] == 0, dt[0]

    s = _ma_swift(GOC / "ui/EIDEApp/Sources/EIDE/Views/RootView.swift")
    assert 'truoc["diff_tom_tat"]' in s
    # Hai lần: định nghĩa + chỗ gọi. Xem lý do ở ca cuộn đồng bộ phía trên.
    assert s.count("bangDiffTomTat") == 2, s.count("bangDiffTomTat")
    assert '"viec"' in s
    # Phần "hiện mấy con số nào" thì đo ở Swift (`SeMatGiView.nhanSo`), không đo bằng cách
    # tìm chữ trong tệp: phép phá "bỏ `doi` đi" vẫn để lại chữ `"doi"` trong mã, nên một ca
    # kiểm đọc chữ sẽ xanh trong khi màn hình in "+0 −0".
    assert "static func nhanSo" in s


# =================================================== 3 · nút Sửa trên thẻ phương án
def _script_hoi():
    return [
        Response(tool_calls=[ToolCall("c1", "ask_user", {
            "intro": "Có ba cách làm, anh chọn cách nào?",
            "questions": [{"key": "cach", "question": "Chọn cách nào?",
                           "why": "quyết định cả kiến trúc",
                           "choices": ["cách A", "cách B"]}]})]),
        Response(text="xong"),
    ]


def test_the_phuong_an_CO_NUT_SUA_khi_kho_co_phuong_an_chua_chot(phien, du_an):
    """§DEV-370 đòi "mỗi cách có nút Sửa". A2.3 sửa được từ DEV-368 nên phương án SỬA ĐƯỢC
    rồi; chỗ thiếu là người đọc thẻ **không biết điều đó** — họ đang nhìn một câu hỏi ba
    lựa chọn, và chỗ sửa thì ở một tab khác."""
    a, core, out = phien(_script_hoi())
    a.store.apply(artefact_id="OPT-01", type="option", op="create", author="agent:run-1",
                  canonical={"ten": "cách A", "kien_truc": "DMA"}, explain=EX)
    core.console_act({"kind": "say", "text": "nêu cho tôi vài cách"})

    t = [x for x in _the(out) if x.get("type") == "clarify"]
    assert t, [x.get("type") for x in _the(out)]
    hd = {h["ma"]: h for h in (t[0].get("hanh_dong") or [])}
    assert "mo_bang_phuong_an" in hd, t[0].get("hanh_dong")
    h = hd["mo_bang_phuong_an"]
    assert h["kind"] == "attend", "mở một tab là SỰ CHÚ Ý — không được tốn lượt mô hình"
    assert h["data"]["di_tab"] == "requirements"
    assert not h.get("ton_token")
    assert "1 cách" in h["nhan"], h["nhan"]


def test_KHONG_co_phuong_an_nao_thi_KHONG_khai_nut(phien, du_an):
    """Một cái nút "Sửa phương án" trên thẻ mà kho không có phương án nào là một cái nút
    mở ra bảng rỗng — nó dạy người ta rằng nút trong app hay dẫn tới chỗ không có gì."""
    a, core, out = phien(_script_hoi())
    core.console_act({"kind": "say", "text": "nêu cho tôi vài cách"})
    t = [x for x in _the(out) if x.get("type") == "clarify"]
    assert t and not t[0].get("hanh_dong")


def test_phuong_an_DA_CHOT_thi_khong_tinh(phien, du_an):
    a, core, out = phien(_script_hoi())
    a.store.apply(artefact_id="OPT-01", type="option", op="create", author="agent:run-1",
                  canonical={"ten": "cách A", "da_chon": True}, explain=EX)
    core.console_act({"kind": "say", "text": "nêu cho tôi vài cách"})
    t = [x for x in _the(out) if x.get("type") == "clarify"]
    assert t and not t[0].get("hanh_dong")


def test_APP_doc_duoc_nut_tren_THE(phien):
    """Lõi khai trên THẺ, không chỉ trên khối — app phải đọc cả hai chỗ."""
    uap = _ma_swift(GOC / "ui/EIDEApp/Sources/EIDE/Protocol/UAP.swift")
    cv = _ma_swift(SW / "CardViews.swift")
    hd = _ma_swift(SW / "HanhDong.swift")
    assert 'raw["hanh_dong"]' in uap and "var hanhDong" in uap
    assert "card.hanhDong" in cv and "NutHanhDong(" in cv
    # Và `di_tab` phải ĐỔI TAB thật, không chỉ ghi sổ: thiếu nó thì `attend` nói "tôi đang
    # xem tab Yêu cầu" trong khi người vẫn ngồi ở Console.
    assert 'di_tab' in hd and "state.selectedSurface = tab" in hd


# =================================================== 4 · nút "quét lại ngay"
def test_A11_khai_nut_QUET_LAI_va_no_chay_bang_MA(phien, du_an):
    """Nhịp 2 giây đủ nhanh cho tay người, trừ một lúc: người vừa làm gì đó ngoài app rồi
    quay sang EIDE để xem nó bắt được chưa. Chờ hai giây trong khi nhìn một bảng không đổi
    là chờ mà không biết mình đang chờ cái gì."""
    a, core, out = phien(watcher=True)
    a.store.apply(artefact_id="FR-01", type="req", op="create", author="agent:run-1",
                  canonical={"text": "x"}, explain=EX)
    a.history.ghi_kho(author="human", artefact_id="FR-01", type="req", op="update",
                      canonical={"text": "y"}, explain=EX)

    hd = {h["ma"]: h for h in (_a11(a)["A11.1"].get("hanh_dong") or [])}
    assert "quet_lai" in hd, _a11(a)["A11.1"].get("hanh_dong")
    assert hd["quet_lai"]["kind"] == "set" and not hd["quet_lai"].get("ton_token")
    assert hd["quet_lai"]["data"] == {"key": "watcher.quet_lai", "value": True}

    # Bấm nó: lõi quét MỘT nhịp bằng mã, và bắt được tệp vừa đổi ngoài app.
    a.bat_dau_theo_doi(out.append)
    a.dung_theo_doi()                       # không cần thread; quét thẳng cho tất định
    a._watcher = type("W", (), {"quet_mot_lan": lambda s: ["main.c"]})()
    (du_an / "main.c").write_text("int main(void){return 42;}\n", "utf-8")
    goi_truoc = a.llm._i

    core.console_act({"kind": "set", "data": {"key": "watcher.quet_lai", "value": True},
                      "origin": {"surface": "history", "block": "A11.1"}})

    assert a.llm._i == goi_truoc, "quét lại là việc của mã — 0 token"
    cs = [c for c in a.history.log.all()
          if a.history.tom_tat(c)["ngoai_eide"]]
    assert len(cs) == 1, [c.explain["summary"] for c in a.history.log.all()]


def test_quet_lai_khi_CHUA_THEO_DOI_thi_noi_that(phien, du_an):
    """Cờ `watcher` tắt thì không có gì để quét lại — nói ra, đừng im lặng làm như đã quét."""
    a, core, out = phien()
    core.console_act({"kind": "set", "data": {"key": "watcher.quet_lai", "value": True},
                      "origin": {"surface": "history", "block": "A11.1"}})
    assert "Chưa theo dõi" in _tb(out) and "A14.7" in _tb(out)


def test_quet_lai_KHONG_CO_GI_DOI_thi_cung_noi(phien, du_an):
    """Im lặng sau một cú bấm là thứ tệ nhất: người không biết nút có ăn hay không."""
    a, core, out = phien(watcher=True)
    a._watcher = type("W", (), {"quet_mot_lan": lambda s: []})()
    core.console_act({"kind": "set", "data": {"key": "watcher.quet_lai", "value": True},
                      "origin": {"surface": "history", "block": "A11.1"}})
    assert "không tệp nào đổi" in _tb(out)
