# -*- coding: utf-8 -*-
"""Sổ cái và giao thức UAP — bất biến I1–I6, toàn vẹn lịch sử (§F3)."""

import json
from pathlib import Path

import pytest

from eide.errors import EideError
from eide.protocol import HumanAct, Target, UICommand
from eide.protocol.ledger import Ledger
from eide.protocol.rpc import Core, Session
from eide.ids import IdGen


# =========================================================================== sổ cái
def test_chuoi_hash_toan_ven(tmp_path):
    lg = Ledger(tmp_path / "l.jsonl")
    for i in range(10):
        lg.append("note", {"i": i})
    ok, msg = lg.verify()
    assert ok, msg
    assert "10" in msg


def test_sua_mot_dong_o_giua_bi_phat_hien(tmp_path):
    """§F3 'Toàn vẹn lịch sử: append-only; kiểm hash chuỗi khi mở dự án'."""
    p = tmp_path / "l.jsonl"
    lg = Ledger(p)
    for i in range(5):
        lg.append("note", {"i": i})

    rows = [json.loads(l) for l in p.read_text("utf-8").splitlines()]
    rows[2]["data"]["i"] = 999                       # sửa lén một sự kiện
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", "utf-8")

    ok, msg = Ledger(p).verify()
    assert not ok
    assert "3" in msg, f"phải chỉ đúng sự kiện hỏng, nhận: {msg}"


def test_ghi_tiep_sau_khi_mo_lai(tmp_path):
    p = tmp_path / "l.jsonl"
    Ledger(p).append("note", {"a": 1})
    lg2 = Ledger(p)                                   # mở lại: phải nối đúng chuỗi
    lg2.append("note", {"a": 2})
    assert lg2.seq == 2
    assert Ledger(p).verify()[0]


def test_loai_su_kien_la_thi_no(tmp_path):
    with pytest.raises(ValueError):
        Ledger(tmp_path / "l.jsonl").append("khong-co-loai-nay", {})


def test_tra_bang_run_cho_backref(tmp_path):
    lg = Ledger(tmp_path / "l.jsonl")
    lg.append("turn.start", {"run_id": "run-042", "text": "bật tối ưu -O3"})
    lg.append("tool_use", {"tool": "build.compile"})
    lg.append("turn.start", {"run_id": "run-043", "text": "chạy mô phỏng"})
    hits = lg.find_run("-O3")
    assert len(hits) == 1 and hits[0]["run_id"] == "run-042"


# =========================================================================== HumanAct
def test_13_loai():
    from eide.protocol.humanact import HUMAN_ACT_KINDS
    assert len(HUMAN_ACT_KINDS) == 13


def test_16_lenh_ui():
    from eide.protocol.uicommand import UI_COMMANDS
    assert len(UI_COMMANDS) == 16


def test_I6_decide_khong_gate_id_thi_vo_nghia():
    """I6: 'Cổng là thẻ riêng — chỉ HumanAct kind=decide với gate_id đang chờ mới mở cổng'."""
    with pytest.raises(EideError) as e:
        HumanAct(kind="decide", data={"approved": True}).validate()
    assert "gate_id" in str(e.value)


def test_edit_phai_co_base_version():
    """Không có base_version thì không phát hiện được người và tác tử đâm nhau (§E4 bước 3)."""
    with pytest.raises(EideError):
        HumanAct(kind="edit", target=Target("file", "src/main.c"), data={}).validate()
    HumanAct(kind="edit", target=Target("file", "src/main.c"),
             data={"base_version": "v7"}).validate()


def test_I2_moi_humanact_mot_dong_transcript():
    acts = [
        HumanAct("say", text="chào"),
        HumanAct("decide", data={"gate_id": "gate-1", "approved": True, "gate": "G-OPS"}),
        HumanAct("edit", target=Target("spec", "REQ-set", "v2"),
                 data={"base_version": "v1", "summary": "FR-03 ≥ 5 MB/s"}, note="phim 4K"),
        HumanAct("snapshot", data={"name": "v0.3"}),
    ]
    for a in acts:
        line = a.validate().transcript_line()
        assert line.startswith("[Bạn] ") and len(line) > 8


def test_target_parse():
    t = Target.parse("file:src/main.c@v7")
    assert (t.type, t.id, t.version) == ("file", "src/main.c", "v7")
    assert str(t) == "file:src/main.c@v7"
    assert Target.parse("fact:12").version is None


# =========================================================================== phiên/RPC
def test_I5_seq_va_chong_trung(tmp_path):
    s = Session()
    for _ in range(3):
        s.stamp(UICommand("notice", {"text": "x"}))
    assert s.seq_out == 3
    s.accept_in("h-0001", 1)
    with pytest.raises(EideError):
        s.accept_in("h-0001", 2)             # cùng id → E_PROTO_DUP


def test_resume_phat_lai(tmp_path):
    s = Session()
    for i in range(5):
        s.stamp(UICommand("notice", {"text": str(i)}))
    assert len(s.replay(2)) == 3
    assert s.replay(5) == []


def test_resume_qua_xa_thi_doi_dung_lai_toan_bo(tmp_path):
    s = Session()
    for i in range(600):
        s.stamp(UICommand("notice", {"text": str(i)}))
    assert s.replay(0) is None                # > 500 → surface.set toàn bộ (§D2)


def test_I1_khong_co_cua_thu_hai(tmp_path):
    lg = Ledger(tmp_path / "l.jsonl")
    core = Core(lg, IdGen(tmp_path), lambda act, emit: None)
    with pytest.raises(EideError) as e:
        core.dispatch("tools.run", {"tool": "fs.read"})
    assert "console.act" in str(e.value)


def test_write_ahead_truoc_khi_lam(tmp_path):
    """I5: HumanAct được ghi sổ TRƯỚC khi xử lý — mất điện giữa lượt vẫn biết người bảo gì."""
    lg = Ledger(tmp_path / "l.jsonl")

    def no_ra_giua_chung(act, emit):
        raise RuntimeError("sập nguồn")

    core = Core(lg, IdGen(tmp_path), no_ra_giua_chung)
    with pytest.raises(RuntimeError):
        core.console_act({"kind": "say", "text": "làm cái mạch đo nhiệt"})

    kinds = [e.kind for e in lg.read()]
    assert "human_act" in kinds
    assert "incident" in kinds
    ha = next(e for e in lg.read() if e.kind == "human_act")
    assert ha.data["text"] == "làm cái mạch đo nhiệt"


# ============================== nhiều TIẾN TRÌNH cùng ghi một sổ cái
# Đo được trong chính dự án này ngày 28/09/2026: app EIDE đang mở dự án STM32F469, bộ kịch bản
# phiên mở **cùng** dự án đó, và cả hai cùng ghi. Sổ cái có hai bản ghi cùng mang `seq 9156`.
# Chính tác tử phát hiện — nó đọc sổ cái và báo "lệch thứ tự ở dòng 9174". Đó là hỏng đúng cái
# thuộc tính mà sổ cái tồn tại để có (§F3), nên bộ này canh nó.

_KICH_BAN_TIEN_TRINH = """
import sys, json
sys.path.insert(0, {src!r})
from eide.protocol.ledger import Ledger
l = Ledger({duong!r})
for i in range({so!r}):
    l.append("ui_command", {{"ai": {ten!r}, "i": i, "chu": "có dấu tiếng Việt — ăn uống"}})
"""


def test_hai_tien_trinh_cung_ghi_thi_so_cai_van_toan_ven(tmp_path):
    """`threading.Lock` chỉ khoá trong MỘT tiến trình. Hai tiến trình thì mỗi bên giữ
    `_seq`/`_head` đọc lúc khởi tạo rồi tự đếm tiếp — và sổ cái thành hai dãy số chồng nhau.
    """
    import subprocess
    import sys

    p = tmp_path / "ledger.jsonl"
    src = str(Path(__file__).resolve().parents[1] / "src")
    chay = [subprocess.Popen(
        [sys.executable, "-c", _KICH_BAN_TIEN_TRINH.format(
            src=src, duong=str(p), so=40, ten=ten)])
        for ten in ("a", "b", "c")]
    for c in chay:
        assert c.wait(timeout=120) == 0

    ds = [json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip()]
    assert len(ds) == 120
    # Điều kiện thật sự cần: `seq` là một thứ tự tổng, không trùng, không tụt.
    assert [d["seq"] for d in ds] == list(range(1, 121))
    dat, mo_ta = Ledger(p).verify()
    assert dat, mo_ta


def test_duoi_tep_doc_dung_dong_cuoi_khi_co_tieng_viet(tmp_path):
    """Nhảy tới một vị trí byte bất kỳ rồi đọc ở chế độ văn bản sẽ cắt đôi một ký tự UTF-8
    nhiều byte. Sổ cái này đầy tiếng Việt có dấu, nên lỗi đó không phải giả thuyết — nó đã
    nổ ngay lần chạy bộ kiểm đầu tiên."""
    from eide.protocol.ledger import _duoi_tep

    p = tmp_path / "l.jsonl"
    l = Ledger(p)
    for i in range(300):
        l.append("ui_command", {"chu": "ăn uống đầy đủ, ngủ nghỉ điều độ " * 20, "i": i})
    with p.open("rb") as f:
        seq, h = _duoi_tep(f)
    assert seq == 300 and len(h) == 64


def test_duoi_tep_tep_rong_va_tep_chi_mot_dong(tmp_path):
    from eide.protocol.ledger import GENESIS, _duoi_tep

    p = tmp_path / "l.jsonl"
    p.write_bytes(b"")
    with p.open("rb") as f:
        assert _duoi_tep(f) == (0, GENESIS)
    l = Ledger(p)
    l.append("ui_command", {"x": 1})
    with p.open("rb") as f:
        assert _duoi_tep(f)[0] == 1


def test_duoi_tep_dong_cuoi_vo_thi_lui_lai_dong_truoc(tmp_path):
    """Mất điện giữa lúc ghi để lại một dòng cụt. Trả `(0, GENESIS)` thì bản ghi kế tiếp sẽ
    giả vờ là dòng đầu tiên — im lặng làm hỏng cả chuỗi. Lùi lại một dòng mới đúng."""
    from eide.protocol.ledger import _duoi_tep

    p = tmp_path / "l.jsonl"
    l = Ledger(p)
    for i in range(3):
        l.append("ui_command", {"i": i})
    with p.open("ab") as f:
        f.write(b'{"seq": 4, "ts": "x", "ki')       # dòng cụt
    with p.open("rb") as f:
        assert _duoi_tep(f)[0] == 3


def test_verify_KHONG_cao_buoc_bi_sua_khi_chi_la_hai_tien_trinh(tmp_path):
    """Một cáo buộc sai ở đúng chỗ người ta phải tin tuyệt đối thì đắt hơn nhiều so với im
    lặng. `seq` lặp mà từng bản ghi vẫn tự khớp hash = tai nạn vận hành, không phải ai sửa."""
    p = tmp_path / "l.jsonl"
    l1 = Ledger(p)
    l1.append("ui_command", {"i": 1})
    l1.append("ui_command", {"i": 2})
    # Mô phỏng tiến trình thứ hai với bộ đếm cũ: ghi tay một bản ghi seq lặp, hash tự khớp.
    ds = [json.loads(x) for x in p.read_text("utf-8").splitlines()]
    from eide.protocol.ledger import _digest

    body = {"seq": 2, "ts": "2026-09-28T00:00:00+00:00", "kind": "ui_command", "data": {"i": 9}}
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    rec = {**body, "prev": ds[0]["hash"], "hash": _digest(payload, ds[0]["hash"])}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")

    dat, mo_ta = Ledger(p).verify()
    assert not dat
    assert "KHÔNG phải ai sửa" in mo_ta and "hai tiến trình" in mo_ta
    assert "bị sửa" not in mo_ta


def test_verify_VAN_cao_buoc_bi_sua_khi_noi_dung_that_su_lech(tmp_path):
    """Nhẹ tay với tai nạn vận hành không được phép làm nhẹ tay với sửa nội dung thật."""
    p = tmp_path / "l.jsonl"
    l = Ledger(p)
    l.append("ui_command", {"i": 1})
    l.append("ui_command", {"i": 2})
    ds = [json.loads(x) for x in p.read_text("utf-8").splitlines()]
    ds[1]["data"] = {"i": 999}                     # sửa nội dung, giữ nguyên hash
    p.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in ds) + "\n", "utf-8")
    dat, mo_ta = Ledger(p).verify()
    assert not dat and "bị sửa" in mo_ta
