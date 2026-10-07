# -*- coding: utf-8 -*-
"""M2-01 — truy vết KHAI BÁO: hiện vật nói nó dựng từ REQ nào, và STALE chỉ lan tới đó.

`deps.ha_nguon_cua` vốn có hai đường: **theo khai báo** (`deps.upstream`) và **theo loại**
(chuỗi mặc định §E5.4). Đường theo khai báo chính xác hơn — nó nói *hiện vật này* dựng từ
*cái kia*, chứ không phải *loại này* thường dựng từ *loại kia*.

Nhưng không đường nào ghi `deps` cả: `History.ghi_kho` và `History.ghi_tep` không có tham số
ấy, nên `store.apply` luôn nhận `deps=None` và ghi `{}`. Đường khai báo có mã, có ca kiểm, và
**chưa từng chạy một lần nào** — y hệt hình dạng "cơ chế có sẵn, đường dẫn tới nó đứt".

Hệ quả đo được: sửa MỘT yêu cầu thì **mọi** phương án, ADR, tệp mã, tiêu chí trong kho đều
sáng đèn STALE. Một băng cảnh báo lúc nào cũng sáng là một băng cảnh báo không ai đọc.
"""

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}


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


def _req(r, ctx, ma, text):
    return r.get("store.req_create").fn(ctx, id=ma, loai="FR", text=text,
                                        source_quote=f"anh nói: {text}", explain=EX)


# =========================================================================== ghi được deps
def test_ghi_kho_luu_deps_upstream(bo):
    """TC-M2-01-01 — `ghi_kho` nhận `deps` và kho giữ lại được."""
    ag, r, ctx = bo
    ag.history.ghi_kho(author="test", artefact_id="PA-A", type="option", op="create",
                       canonical={"ten": "phương án A"}, explain=EX,
                       deps={"upstream": ["FR-01"]})
    assert ag.store.get("PA-A")["deps"].get("upstream") == ["FR-01"]


def test_ghi_lai_khong_xoa_deps_cu(bo):
    """TC-M2-01-02 — ghi lại mà không nói gì về deps thì deps cũ phải còn.

    `apply` dùng `deps=excluded.deps` trong câu upsert, nên MỖI lần ghi lại sẽ xoá sạch
    liên kết đã khai. Một hiện vật mất đường về nguồn sau lần sửa thứ hai thì đường khai
    báo chỉ sống được đúng một version.
    """
    ag, r, ctx = bo
    ag.history.ghi_kho(author="test", artefact_id="PA-A", type="option", op="create",
                       canonical={"ten": "A"}, explain=EX, deps={"upstream": ["FR-01"]})
    ag.history.ghi_kho(author="test", artefact_id="PA-A", type="option", op="update",
                       canonical={"ten": "A sửa"}, explain=EX)
    assert ag.store.get("PA-A")["deps"].get("upstream") == ["FR-01"]
    # Truyền dict rỗng là CỐ Ý xoá — khác hẳn với không nói gì.
    ag.history.ghi_kho(author="test", artefact_id="PA-A", type="option", op="update",
                       canonical={"ten": "A sửa nữa"}, explain=EX, deps={})
    assert not (ag.store.get("PA-A")["deps"] or {}).get("upstream")


# =========================================================================== STALE đúng chỗ
def test_sua_FR02_khong_stale_tieu_chi_chi_do_FR01(bo):
    """TC-M2-01-03 — tiêu chí khai đo FR-01 thì sửa FR-02 không được làm nó lỗi thời."""
    ag, r, ctx = bo
    _req(r, ctx, "FR-01", "đèn nháy 1 Hz")
    _req(r, ctx, "FR-02", "nút bấm đổi chế độ")
    r.get("sim.criteria").fn(ctx, explain=EX, ma="sim-01", ten="đo nháy", **{
        "assert": [{"ma": "A1", "mo_ta": "chu kỳ 1 s", "phep_so": "<=", "nguong": 1.0,
                    "don_vi": "s", "do_req": "FR-01", "nguon_nguong": "FR-01"}]})
    ma_tc = next(a["id"] for a in ag.store.list("criteria"))

    ra = r.get("store.req_update").fn(ctx, id="FR-02", text="nút bấm giữ 2 giây", explain=EX)
    assert ma_tc not in ra["stale"], \
        f"sửa FR-02 mà tiêu chí chỉ đo FR-01 vẫn lỗi thời. STALE: {ra['stale']}"

    ra = r.get("store.req_update").fn(ctx, id="FR-01", text="đèn nháy 2 Hz", explain=EX)
    assert ma_tc in ra["stale"], f"sửa đúng FR-01 mà tiêu chí KHÔNG lỗi thời: {ra['stale']}"


def test_tep_ma_khong_khai_REQ_van_stale_theo_loai(bo, du_an):
    """TC-M2-01-04 — ca âm: không khai gì thì vẫn lan theo loại như cũ (giữ CX06).

    Đây là chỗ dễ làm hỏng nhất của nhiệm vụ này: siết đường khai báo mà quên rằng phần lớn
    hiện vật trong kho **không khai gì cả**. Chúng phải tiếp tục sáng đèn như trước.
    """
    ag, r, ctx = bo
    _req(r, ctx, "FR-01", "đèn nháy 1 Hz")
    (du_an / "drv.c").write_text("int x;\n", "utf-8")
    ag.history.ghi_tep(author="agent:run-1", paths=["drv.c"], summary="thêm drv.c", explain=EX)

    ra = r.get("store.req_update").fn(ctx, id="FR-01", text="đèn nháy 2 Hz", explain=EX)
    assert "drv.c" in ra["stale"], f"tệp không khai REQ phải vẫn STALE theo loại: {ra['stale']}"


# =========================================================================== ma trận
def test_ma_tran_truy_vet_tung_REQ(bo):
    """TC-M2-01-05 — mỗi REQ một dòng: nó đã được phương án/tiêu chí/mã nào đụng tới."""
    from eide import deps

    ag, r, ctx = bo
    _req(r, ctx, "FR-01", "đèn nháy 1 Hz")
    _req(r, ctx, "FR-02", "nút bấm đổi chế độ")
    r.get("store.option_create").fn(ctx, id="PA-A", ten="dùng timer", kien_truc="timer",
                                    dap_ung_req=["FR-01"], explain=EX)

    mt = {d["req"]: d for d in deps.ma_tran_truy_vet(ag.store)}
    assert set(mt) == {"FR-01", "FR-02"}, sorted(mt)
    assert mt["FR-01"]["option"] == ["PA-A"]
    assert mt["FR-02"]["option"] == [], mt["FR-02"]


def test_ma_tran_truy_vet_lay_ca_tieu_chi(bo):
    """Tiêu chí nối với REQ qua `assert[*].do_req`, không qua `deps` — ma trận phải đọc cả hai."""
    from eide import deps

    ag, r, ctx = bo
    _req(r, ctx, "FR-01", "đèn nháy 1 Hz")
    r.get("sim.criteria").fn(ctx, explain=EX, ma="sim-01", ten="đo nháy", **{
        "assert": [{"ma": "A1", "mo_ta": "chu kỳ 1 s", "phep_so": "<=", "nguong": 1.0,
                    "do_req": "FR-01", "nguon_nguong": "FR-01"}]})

    mt = {d["req"]: d for d in deps.ma_tran_truy_vet(ag.store)}
    assert mt["FR-01"]["criteria"], mt["FR-01"]


# =========================================================================== cờ
def test_co_tat_luoc_do_fs_write_khong_co_hien_thuc_req():
    """TC-M2-01-06 — cờ TẮT: lược đồ `fs.write` không mọc thêm trường nào."""
    from eide.config import Features
    from eide.tools import build_registry

    r = build_registry(Features())
    for ten in ("fs.write", "fs.edit"):
        assert "hien_thuc_req" not in r.get(ten).params["properties"], ten


def test_co_bat_thi_fs_write_nhan_hien_thuc_req(monkeypatch, du_an):
    """Cờ BẬT: trường có mặt, và giá trị đi được tới `deps.upstream` của tệp."""
    from eide import Config
    from eide.config import Features
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext
    from eide.tools import build_registry

    monkeypatch.setenv("EIDE_FEATURE_TRUY_VET", "1")
    co = Features.load()
    cfg = Config.for_project(du_an)
    cfg.features = co
    ag = Agent(cfg, llm=ScriptedGateway([]), project_name="du-an-thu")
    r = build_registry(co)
    ctx = TurnContext(config=cfg, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=r, emit=lambda c: None, history=ag.history,
                      agent=ag, run_id="run-1", project_name="du-an-thu")

    assert "hien_thuc_req" in r.get("fs.write").params["properties"]
    r.get("store.req_create").fn(ctx, id="FR-01", loai="FR", text="đèn nháy",
                                 source_quote="anh nói: đèn nháy", explain=EX)
    r.get("fs.write").fn(ctx, path="blink.c", content="int main(void){return 0;}\n",
                         explain=EX, hien_thuc_req=["FR-01"])
    assert ag.store.get("blink.c")["deps"].get("upstream") == ["FR-01"]


# =========================================================================== phép đo của §
def test_do_so_hien_vat_STALE_giam_khi_khai_dung(bo, du_an):
    """Tiêu chí xong của nhiệm vụ: 3 REQ + 3 hiện vật khai đúng → sửa 1 REQ chỉ lan 1 chỗ.

    Con số này là lý do của cả nhiệm vụ. Trước: sửa một yêu cầu làm **tất cả** hiện vật hạ
    nguồn sáng đèn. Sau: chỉ đúng phần khai mình dựng từ nó.
    """
    ag, r, ctx = bo
    for i in (1, 2, 3):
        _req(r, ctx, f"FR-0{i}", f"yêu cầu {i}")
        r.get("store.option_create").fn(ctx, id=f"PA-{i}", ten=f"phương án {i}",
                                        kien_truc="x", dap_ung_req=[f"FR-0{i}"], explain=EX)

    ra = r.get("store.req_update").fn(ctx, id="FR-01", text="yêu cầu 1 sửa", explain=EX)
    pa = sorted(x for x in ra["stale"] if x.startswith("PA-"))
    assert pa == ["PA-1"], f"sửa FR-01 mà lan tới: {pa}"
