# -*- coding: utf-8 -*-
"""MEM-A — phong bì kết quả, blob, đồng hồ ngữ cảnh, C1. EIDE-MEM-42 §4, §5, §6.1.

Ca đo: MEM01 (fs.read tệp 3 000 dòng), MEM02 (40 tool/lượt log lớn), MEM05 (C1).

Điều cả bộ này canh: **cắt không được thành mất.** Mỗi lần thu gọn đều phải để lại một
đường đọc lại và một câu nói rõ đã cắt bao nhiêu — nếu không thì ta đổi "ngữ cảnh đầy"
lấy "tác tử nhớ sai", và cái sau khó phát hiện hơn nhiều.
"""

from __future__ import annotations

import json

import pytest

from eide.config import ContextBudget
from eide.memory import LUOT_GIU_NGUYEN_VAN, boc_ket_qua, c1, chi_so_ghim, uoc_token
from eide.memory.envelope import TRAN_CHUNG_TOKEN
from eide.tools.registry import ToolResult


class KhoBlob:
    """BlobStore tối giản để đo phần "đọc lại được"."""

    def __init__(self):
        self.d: dict[str, bytes] = {}

    def put(self, data):
        import hashlib
        b = data.encode("utf-8") if isinstance(data, str) else data
        h = hashlib.sha256(b).hexdigest()
        self.d[h] = b
        return h

    def get(self, h):
        return self.d.get(h)


def _ok(data):
    return ToolResult(True, data=data)


# =========================================================================== MEM01
def _tep(n: int) -> dict:
    noi = "\n".join(f"{i:5d}\tdòng thứ {i} của một tệp rất dài" for i in range(1, n + 1))
    return {"path": "src/drv_i2c.c", "bytes": len(noi), "lines_total": n,
            "lines_shown": [1, n], "truncated": False, "content": noi, "note_vi": ""}


def test_MEM01_tep_3000_dong_chi_vao_ngu_canh_60_dong_dau(tmp_path):
    kho = KhoBlob()
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(_tep(3000)),
                      args={"path": "src/drv_i2c.c"}, blobs=kho)

    assert env.truncated
    assert len(env.data["content"].splitlines()) == 60
    assert env.shown_tokens < env.full_tokens / 10, "phải giảm ít nhất một bậc độ lớn"
    assert "3000" in env.summary_line and "60" in env.summary_line


def test_MEM01_phan_con_lai_van_doc_lai_duoc(tmp_path):
    kho = KhoBlob()
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(_tep(3000)),
                      args={}, blobs=kho)
    assert env.blob_ref and env.blob_ref.startswith("blob:sha256:")
    tho = json.loads(kho.get(env.blob_ref.split(":")[-1]).decode("utf-8"))
    assert tho["lines_total"] == 3000
    assert len(tho["content"].splitlines()) == 3000, "blob phải giữ NGUYÊN VĂN"


def test_MEM01_bao_cho_mo_hinh_biet_cach_doc_tiep(tmp_path):
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(_tep(3000)),
                      args={}, blobs=KhoBlob())
    m = env.to_model()
    assert "_cat" in m
    assert "blob.read" in m["_cat"]["doc_tiep_bang"]
    assert m["_cat"]["phan_con_lai"] == env.blob_ref


def test_MEM01_co_bang_de_muc_de_mo_hinh_biet_doc_doan_nao(tmp_path):
    noi = "\n".join([
        "#include <stdio.h>",
        "#define I2C_TIMEOUT_MS 50",
        "static int i2c_init(void) {",
        "    return 0;",
        "}",
        "void i2c_write(uint8_t a) {",
    ] + [f"    // đệm {i}" for i in range(3000)])
    d = {"path": "a.c", "lines_total": 3006, "content": noi, "bytes": len(noi)}
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(d), args={},
                      blobs=KhoBlob())
    ten = " ".join(env.data["de_muc"])
    assert "i2c_init" in ten and "i2c_write" in ten and "I2C_TIMEOUT_MS" in ten


def test_tep_ngan_di_qua_nguyen_ven_khong_boc_giay(tmp_path):
    """Bọc mọi thứ chỉ tăng token mà không giảm gì."""
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(_tep(20)), args={},
                      blobs=KhoBlob())
    assert not env.truncated and env.blob_ref is None
    assert len(env.data["content"].splitlines()) == 20
    assert "_cat" not in env.to_model()


def test_loi_KHONG_bi_cat(tmp_path):
    """§B3 — lỗi là dữ liệu để mô hình đổi hướng. Cắt nó là cắt thứ đang cứu lượt."""
    from eide.errors import path_not_found

    r = ToolResult(False, error=path_not_found("khong/co/dau.c"))
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=r, args={}, blobs=KhoBlob())
    m = env.to_model()
    assert not env.truncated and env.blob_ref is None
    assert m["code"] == "E1003" and m["hint_for_agent"] and m["alternatives"]


def test_thieu_kho_blob_thi_NOI_RA_chu_khong_im_lang_lam_mat(tmp_path):
    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=_ok(_tep(3000)),
                      args={}, blobs=None)
    assert env.truncated and env.blob_ref is None
    assert "KHÔNG lưu lại được" in env.summary_line


# =========================================================================== các chính sách
def test_tim_kiem_cat_80_dong_nhung_van_dem_du(tmp_path):
    d = {"pattern": "i2c", "count": 900,
         "hits": [{"path": f"f{i}.c", "line": i, "text": "x" * 500} for i in range(900)]}
    env = boc_ket_qua(tool="fs.grep", call_id="c", ket_qua=_ok(d), args={},
                      blobs=KhoBlob())
    assert len(env.data["hits"]) == 80
    assert env.data["count"] == 900, "đếm tổng phải giữ — người cần biết còn bao nhiêu"
    assert all(len(h["text"]) <= 200 for h in env.data["hits"])


def test_log_giu_dau_va_CUOI(tmp_path):
    """Với log, hai đầu là chỗ có tin; khúc giữa hiếm khi."""
    d = {"exit_code": 1, "stdout": "\n".join(f"dòng {i}" for i in range(500))}
    env = boc_ket_qua(tool="bash", call_id="c", ket_qua=_ok(d), args={}, blobs=KhoBlob())
    out = env.data["stdout"]
    assert "dòng 0" in out and "dòng 499" in out and "dòng 250" not in out
    assert "đã cắt" in out


def test_cong_cu_khong_co_chinh_sach_van_co_tran_chung(tmp_path):
    d = {"x": "y" * (TRAN_CHUNG_TOKEN * 4)}
    env = boc_ket_qua(tool="cong.cu.la", call_id="c", ket_qua=_ok(d), args={},
                      blobs=KhoBlob())
    assert env.truncated and env.blob_ref
    assert env.shown_tokens < env.full_tokens


def test_tham_chieu_hien_vat_co_id_va_phien_ban(tmp_path):
    r = ToolResult(True, data={"id": "FR-01", "version": 3, "type": "req"},
                   artefact_id="FR-01")
    env = boc_ket_qua(tool="store.req_update", call_id="c", ket_qua=r, args={},
                      blobs=KhoBlob())
    assert env.to_model()["_hien_vat"] == {"id": "FR-01", "version": 3, "type": "req"}


# =========================================================================== MEM02 đồng hồ
def test_MEM02_bon_nguong_dung_bien():
    cb = ContextBudget()
    assert cb.muc_nen(0.10) == "C0"
    assert cb.muc_nen(0.62) == "C1"
    assert cb.muc_nen(0.71) == "C2"
    assert cb.muc_nen(0.88) == "C3"
    assert cb.muc_nen(0.97) == "C4"


def test_MEM02_du_tru_20_phan_tram_bat_kha_xam_pham():
    cb = ContextBudget()
    assert cb.du_tru(1_000_000) == 200_000
    assert cb.kha_dung(1_000_000) == 800_000


def test_MEM02_du_muoi_khoi():
    cb = ContextBudget()
    tran = [cb.constitution, cb.tool_schema, cb.eide_md, cb.inventory, cb.facts,
            cb.human_edits + cb.pending, cb.skills, cb.session_summary]
    assert all(t > 0 for t in tran)
    assert cb.du_tru_ty_le == 0.20


def test_MEM02_dong_ho_bao_dung_khoi_nao_vuot(chay, make_agent):
    agent = make_agent([])
    nc = agent.ngu_canh_hien_tai()
    assert nc["cua_so"] > 0 and nc["muc"] == "C0"
    ten = {k["ten"] for k in nc["khoi"]}
    assert {"constitution", "inventory", "transcript"} <= ten
    assert any("dự trữ" in k["ten"] for k in nc["khoi"])

    # Nhồi cho EIDE.md vượt trần rồi xem đồng hồ có chỉ đúng khối đó không.
    agent.eide_md.set("Mục tiêu", "x" * 40_000)
    nc2 = agent.ngu_canh_hien_tai()
    md = next(k for k in nc2["khoi"] if k["ten"] == "eide_md")
    assert md["vuot"] is False, "render đã cắt theo trần — khối không được vượt"
    assert md["token"] <= md["tran"]


# =========================================================================== MEM05 C1
def _tin_nhan(n_luot: int) -> list[dict]:
    ms: list[dict] = []
    for l in range(n_luot):
        ms.append({"role": "user", "text": f"việc thứ {l}"})
        ms.append({"role": "model", "parts": []})
        ms.append({"role": "tool", "tool_call_id": f"c{l}", "tool": "fs.read",
                   "result": {"ok": True, "data": {"path": f"f{l}.c", "bytes": 100,
                                                   "content": "nội dung " * 200}},
                   "envelope": {"summary_line": f"fs.read f{l}.c",
                                "blob_ref": f"blob:sha256:{l:064d}"}})
    return ms


def test_MEM05_C1_stub_ket_qua_qua_8_luot(tmp_path):
    ms = _tin_nhan(12)
    truoc = sum(len(str(m)) for m in ms)
    bc = c1(ms)
    assert bc["stub_qua_han"] >= 3
    assert bc["sau"] < truoc
    # Kết quả của lượt gần nhất KHÔNG được đụng tới.
    assert ms[-1].get("_stub") is not True


def test_MEM05_stub_van_giu_duong_doc_lai(tmp_path):
    ms = _tin_nhan(12)
    c1(ms)
    stub = next(m for m in ms if m.get("_stub"))
    chu = stub["result"]["_da_thu_gon"]
    assert "blob:sha256:" in chu and "blob.read" in chu, "cắt mà không có đường lùi = mất"


def test_MEM05_C1_khong_goi_mo_hinh(chay, make_agent):
    """0 token — đó là toàn bộ lý do C1 đứng trước C2."""
    agent = make_agent([])
    agent.messages = _tin_nhan(12)
    c1(agent.messages)
    assert len(agent.llm.calls) == 0


def test_MEM05_dedup_lan_doc_trung(tmp_path):
    ms = [
        {"role": "user", "text": "đọc đi"},
        {"role": "tool", "tool": "fs.read", "tool_call_id": "a",
         "result": {"ok": True, "data": {"path": "a.c", "bytes": 10, "content": "x"}},
         "envelope": {"summary_line": "fs.read a.c"}},
        {"role": "user", "text": "đọc lại"},
        {"role": "tool", "tool": "fs.read", "tool_call_id": "b",
         "result": {"ok": True, "data": {"path": "a.c", "bytes": 10, "content": "x"}},
         "envelope": {"summary_line": "fs.read a.c"}},
    ]
    bc = c1(ms)
    assert bc["dedup"] == 1
    assert ms[1].get("_stub") and "đã đọc lại" in ms[1]["result"]["_da_thu_gon"]
    assert not ms[3].get("_stub"), "lần MỚI phải được giữ nguyên"


def test_MEM05_supersede_khi_tep_da_bi_sua(tmp_path):
    ms = [
        {"role": "user", "text": "đọc"},
        {"role": "tool", "tool": "fs.read", "tool_call_id": "a",
         "result": {"ok": True, "data": {"path": "a.c", "bytes": 10, "content": "cũ"}},
         "envelope": {"summary_line": "fs.read a.c"}},
    ]
    bc = c1(ms, tep_da_sua={"a.c"})
    assert bc["supersede"] == 1
    assert "đã được sửa" in ms[1]["result"]["_da_thu_gon"]


def test_MEM05_dem_theo_LUOT_khong_theo_message(tmp_path):
    """Bản trước giữ 10 *message* ≈ chưa tới hai lượt — lý do tác tử quên giữa chừng."""
    ms = _tin_nhan(3)          # 3 lượt, 9 message
    bc = c1(ms)
    assert bc["stub_qua_han"] == 0, "3 lượt chưa tới ngưỡng 8, không được stub gì"
    assert len(ms) == 9, "C1 không được vứt message nào — nó thu gọn, không cắt bỏ"


def test_MEM05_ghim_thi_khong_bi_dung_toi(tmp_path):
    ms = _tin_nhan(12)
    ghim = {i for i, m in enumerate(ms) if m.get("role") == "tool"}
    bc = c1(ms, ghim=ghim)
    assert bc["stub_qua_han"] == 0


def test_ghim_tu_dong_theo_Y_CHI_cua_nguoi(tmp_path):
    ms = [
        {"role": "user", "text": "duyệt", "_kind": "decide"},
        {"role": "user", "text": "câu thường"},
        {"role": "user", "text": "sửa", "_kind": "edit"},
    ]
    assert chi_so_ghim(ms) == {0, 2}


def test_C1_chay_lai_nhieu_lan_khong_hong(tmp_path):
    ms = _tin_nhan(12)
    c1(ms)
    n = len(ms)
    bc2 = c1(ms)
    assert len(ms) == n
    assert bc2["stub_qua_han"] == 0, "đã stub rồi thì không stub lại"


def test_hang_so_nguong_dung_nhu_tai_lieu():
    assert LUOT_GIU_NGUYEN_VAN == 8


def test_de_muc_doc_duoc_noi_dung_DA_DANH_SO_DONG():
    """`fs.read` trả "  123\\tmã" — quên gỡ tiền tố thì bảng đề mục luôn rỗng."""
    from eide.memory.envelope import _de_muc

    chu = "\n".join([
        "    1\t#include <stdint.h>",
        "    2\t#define I2C_TIMEOUT_MS 50",
        "    3\tstatic int i2c_init(void) {",
        "    4\t    return 0;",
        "    5\t}",
    ])
    ten = " ".join(_de_muc(chu))
    assert "i2c_init" in ten and "I2C_TIMEOUT_MS" in ten


def test_hien_phap_khong_duoc_phinh_qua_tran():
    """MEM-42 P8 — mỗi khối có trần riêng, và trần phải có người canh.

    Hiến pháp là khối duy nhất KHÔNG tự co lại được: nó không có bước cắt như EIDE.md
    hay `<facts>`. Nên chỗ canh nó phải là một ca đo, không phải một dòng trong bảng.
    Ca này đỏ nghĩa là: ai đó vừa thêm vào hiến pháp — hãy quyết định có đáng không,
    đừng lặng lẽ nâng trần.
    """
    from eide.context.assemble import CONSTITUTION_PATH, approx_tokens

    n = approx_tokens(CONSTITUTION_PATH.read_text("utf-8"))
    assert n <= ContextBudget().constitution, (
        f"hiến pháp {n} token, vượt trần {ContextBudget().constitution}")
