# -*- coding: utf-8 -*-
"""Ca tuân thủ giao thức UP01–UP12 — EIDE-MDD-40 §D, §D2.

Kiểm **cầu thật**: dựng lõi như một tiến trình con và nói chuyện với nó qua đúng khung
`Content-Length` mà app Swift dùng. Không giả lập lớp nào.

Vì sao phải kiểm ở mức này chứ không gọi `Core.dispatch` trực tiếp: sáu bất biến của
§D1 là về **cầu**, không về lớp Python. Một lỗi đóng khung, một lỗi thứ tự seq, hay một
cửa vào thứ hai lọt vào `dispatch` sẽ không lộ ra nếu ta chỉ gọi hàm.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]


class Cau:
    """Nói JSON-RPC 2.0 khung Content-Length với lõi — giống hệt CoreClient.swift."""

    def __init__(self, du_an: pathlib.Path):
        env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "PYTHONUNBUFFERED": "1"}
        self.p = subprocess.Popen(
            [sys.executable, "-m", "eide", "--du-an", str(du_an), "--stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env, cwd=REPO)
        self._id = 0
        self.lenh: list[dict] = []          # UICommand nhận được, theo đúng thứ tự

    def _gui(self, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.p.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        self.p.stdin.flush()

    def _doc_khung(self) -> dict:
        n = 0
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("Lõi đóng ống ra. stderr: "
                                   + self.p.stderr.read().decode("utf-8", "replace")[-2000:])
            line = line.strip()
            if not line:
                break
            if line.lower().startswith(b"content-length:"):
                n = int(line.split(b":", 1)[1])
        return json.loads(self.p.stdout.read(n).decode("utf-8"))

    def goi(self, method: str, params: dict | None = None, *, timeout: float = 120) -> dict:
        self._id += 1
        mine = self._id
        self._gui({"jsonrpc": "2.0", "id": mine, "method": method, "params": params or {}})
        while True:
            msg = self._doc_khung()
            if msg.get("id") == mine:
                if "error" in msg:
                    raise AssertionError(msg["error"])
                return msg["result"]
            if "method" in msg and "id" not in msg:
                self.lenh.append(msg)      # UICommand đi kèm trong lúc chờ

    def dong(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=10)
        except Exception:
            self.p.kill()

    # --- tiện
    def cua(self, method: str) -> list[dict]:
        return [c for c in self.lenh if c["method"] == method]

    def loi_tac_tu(self) -> str:
        return "\n".join(c["params"].get("text", "") for c in self.cua("console.post")
                         if c["params"].get("role") == "agent")


@pytest.fixture
def cau(tmp_path):
    d = tmp_path / "du-an-cau"
    d.mkdir()
    (d / "main.c").write_text("int main(void){return 0;}\n", "utf-8")
    c = Cau(d)
    yield c
    c.dong()


# =========================================================================== UP01–UP12
def test_UP01_hello_tra_nang_luc(cau):
    r = cau.goi("hello", {"client": {"name": "test"}})
    assert r["core"] == "eide"
    assert r["capabilities"]["uap"] == "1.1"
    assert r["capabilities"]["human_acts"] == 13
    assert r["capabilities"]["ui_commands"] == 16
    assert len(r["capabilities"]["gates"]) == 11
    assert r["ledger"]["ok"] is True, "mở dự án phải kiểm chuỗi hash sổ cái (§F3)"


def test_UP02_mot_cua_vao(cau):
    """I1 — không có cửa thứ hai vào lõi."""
    cau.goi("hello")
    for method in ("tools.run", "store.write", "agent.turn", "eval"):
        with pytest.raises(AssertionError) as e:
            cau.goi(method, {})
        assert "console.act" in json.dumps(e.value.args, ensure_ascii=False)


def test_UP03_moi_humanact_mot_dong_transcript(cau):
    """I2 — mỗi HumanAct → đúng một dòng "[Bạn] …"."""
    cau.goi("hello")
    cau.goi("console.act", {"act": {"kind": "say", "text": "xin chào"}})
    dong_nguoi = [c for c in cau.cua("console.post") if c["params"]["role"] == "human"]
    assert len(dong_nguoi) == 1
    assert dong_nguoi[0]["params"]["text"] == "[Bạn] xin chào"


def test_UP04_seq_tang_dan_khong_dut(cau):
    """I5 — có thứ tự, không trùng."""
    cau.goi("hello")
    cau.goi("ui.sync")
    seqs = [c["params"]["_seq"] for c in cau.lenh]
    assert seqs == list(range(1, len(seqs) + 1))


def test_UP05_idempotent_theo_id(cau):
    """I5 — cùng act id gửi hai lần thì lần hai bị từ chối."""
    cau.goi("hello")
    act = {"kind": "say", "text": "chào", "id": "h-9999"}
    cau.goi("console.act", {"act": act})
    with pytest.raises(AssertionError) as e:
        cau.goi("console.act", {"act": act})
    assert "E_PROTO_DUP" in json.dumps(e.value.args, ensure_ascii=False)


def test_UP06_resume_phat_lai(cau):
    """I5 — khôi phục được."""
    cau.goi("hello")
    cau.goi("ui.sync")
    truoc = cau.goi("ui.status")["seq_out"]
    r = cau.goi("resume", {"last_seq": truoc - 3})
    assert r["mode"] == "replay"
    assert len(r["commands"]) == 3
    assert [c["seq"] for c in r["commands"]] == [truoc - 2, truoc - 1, truoc]


def test_UP07_ui_sync_ve_du_11_be_mat(cau):
    """I3 — giao diện chỉ render thứ lõi gửi, nên lõi phải gửi đủ."""
    cau.goi("hello")
    cau.goi("ui.sync")
    ten = [c["params"]["surface"] for c in cau.cua("surface.set")]
    assert set(ten) == {"requirements", "documents", "knowledge", "design", "tools",
                        "code", "simulation", "hardware", "journal", "history", "project"}
    assert cau.cua("ui.set"), "phải gửi thanh trạng thái"


def test_UP08_be_mat_rong_noi_that(cau):
    """E3.2 §5 — khối chưa có dữ liệu phải nói: chưa có gì · vì sao · cần gì."""
    cau.goi("hello")
    cau.goi("ui.sync")
    thiet_ke = next(c["params"]["model"] for c in cau.cua("surface.set")
                    if c["params"]["surface"] == "design")
    rong = [b for b in thiet_ke["blocks"] if b["type"] == "empty"]
    assert rong, "tab Thiết kế lúc dự án trống phải có khối nói rõ chưa có gì"
    for k in rong:
        for truong in ("chua_co", "vi_sao", "can_gi"):
            assert k.get(truong), f"{k['code']} thiếu {truong}"
        # `buoc` chỉ có khi thứ còn thiếu thuộc một bước lộ trình chưa làm; khối bị
        # chặn bởi một việc người dùng phải làm trước thì không mang nhãn bước.
        assert k.get("buoc", "G1").startswith("G")


def test_UP09_S0_chan_qua_cau_that(cau):
    """N5 qua cầu: câu vi phạm bị chặn, không gọi mô hình, vẫn trả lời người."""
    cau.goi("hello")
    cau.goi("console.act", {"act": {"kind": "say", "text": "làm thiết bị phá sóng di động"}})
    assert "không hỗ trợ" in cau.loi_tac_tu()
    assert "Faraday" in cau.loi_tac_tu()


def test_UP10_the_cong_la_the_rieng(cau):
    """I6 — cổng đi kèm thẻ có gate_id; text 'có' KHÔNG mở được."""
    cau.goi("hello")
    cau.goi("console.act", {"act": {"kind": "say", "text": "xoá sạch toàn bộ flash"}})
    the = [c["params"]["card"] for c in cau.cua("console.post") if c["params"].get("card")]
    assert len(the) == 1
    g = the[0]
    assert g["gate"] == "G-OPS" and g["never_auto"] is True
    assert g["consequences_vi"], "hậu quả phải đứng trước lựa chọn"

    truoc = len(cau.lenh)
    cau.goi("console.act", {"act": {"kind": "say", "text": "có"}})
    da_dong = [c for c in cau.lenh[truoc:] if c["method"] == "card.resolve"]
    assert not da_dong, "một chữ 'có' không được mở cổng"


def test_UP11_decide_mo_cong(cau):
    cau.goi("hello")
    cau.goi("console.act", {"act": {"kind": "say", "text": "bật khoá đọc RDP"}})
    gid = [c["params"]["card"] for c in cau.cua("console.post")
           if c["params"].get("card")][0]["gate_id"]
    cau.goi("console.act", {"act": {"kind": "decide",
                                    "data": {"gate_id": gid, "approved": False},
                                    "note": "chưa sao lưu"}})
    dong = cau.cua("card.resolve")
    assert dong and dong[-1]["params"]["card_id"] == gid


def test_UP12_decide_gate_da_dong_thi_bao_het_han(cau):
    cau.goi("hello")
    r = cau.goi("console.act", {"act": {"kind": "decide",
                                        "data": {"gate_id": "gate-khong-co", "approved": True}}})
    assert r["accepted"] is True
    tb = [c for c in cau.cua("notice") if c["params"].get("code") == "E_GATE_STALE"]
    assert tb, "thẻ không còn chờ phải được nói ra, không im lặng"


def test_UP13_attend_khong_chay_luot(cau):
    """DEV-226 — chuyển tab là sự chú ý, không phải yêu cầu.

    Bấm tab không được gọi mô hình, không sinh dòng transcript, không hiện thẻ Run —
    nhưng vẫn phải nằm trong sổ cái để phát lại đúng thứ người đã nhìn.
    """
    cau.goi("hello")
    truoc = len(cau.lenh)
    for s in ("code", "simulation", "design", "journal"):
        cau.goi("console.act", {"act": {"kind": "attend", "origin": {"surface": s}}})
    moi = cau.lenh[truoc:]

    assert not [c for c in moi if c["method"] == "console.post"], \
        "chuyển tab không được sinh dòng transcript"
    assert not [c for c in moi if c["method"] == "run.update"], \
        "chuyển tab không được hiện thẻ Run"
    assert not [c for c in moi if c["method"] == "surface.set"], \
        "chuyển tab không được vẽ lại bề mặt"

    # Nhưng sổ cái phải nhớ — phát lại phải biết đúng thứ người đã nhìn, đúng thứ tự.
    du_an = pathlib.Path(cau.p.args[cau.p.args.index("--du-an") + 1])
    evs = [json.loads(l) for l in
           (du_an / ".eide" / "ledger.jsonl").read_text("utf-8").splitlines() if l.strip()]
    da_nhin = [e["data"]["origin"]["surface"] for e in evs
               if e["kind"] == "human_act" and e["data"]["kind"] == "attend"]
    assert da_nhin == ["code", "simulation", "design", "journal"]


def test_UP14_mo_lai_du_an_thi_dung_lai_transcript(cau):
    """I2 — "transcript = hình chiếu sổ cái, phát lại được".

    Mở lại dự án mà Console trống trong khi sổ cái có đủ lịch sử là vi phạm đúng câu
    đó, và làm người dùng tưởng phiên trước đã mất.
    """
    cau.goi("hello")
    cau.goi("console.act", {"act": {"kind": "say", "text": "làm thiết bị phá sóng"}})
    so_su_kien = len(list(_doc_so_cai(cau)))

    truoc = len(cau.lenh)
    r = cau.goi("ui.sync")
    assert r["dong_transcript"] >= 2, "phải dựng lại cả dòng của người lẫn của tác tử"

    lai = [c for c in cau.lenh[truoc:] if c["method"] == "console.post"]
    assert any("phá sóng" in c["params"].get("text", "") for c in lai)
    assert any("không hỗ trợ" in c["params"].get("text", "") for c in lai)

    # Phát lại KHÔNG được ghi sổ lần nữa — nếu không, mỗi lần mở dự án lại nhân đôi
    # lịch sử và CX16 sai ngay từ lần mở thứ hai.
    assert len(list(_doc_so_cai(cau))) == so_su_kien + _so_lenh_ve_be_mat(cau)


def _doc_so_cai(cau):
    du_an = pathlib.Path(cau.p.args[cau.p.args.index("--du-an") + 1])
    p = du_an / ".eide" / "ledger.jsonl"
    return [json.loads(l) for l in p.read_text("utf-8").splitlines() if l.strip()]


def _so_lenh_ve_be_mat(cau):
    """11 surface.set + 1 ui.set + 1 history.update = 13 lệnh vẽ, đều được ghi sổ."""
    return 13
