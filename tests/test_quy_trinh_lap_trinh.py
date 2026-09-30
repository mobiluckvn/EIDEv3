# -*- coding: utf-8 -*-
"""Quy trình lập trình: phân tích trước · đánh mốc trước · thiết kế trước khi tách việc.

Ba đòi hỏi anh Công nêu 30/09/2026, và ba lỗ hổng đo được trước khi vá:

1. `fs.write` **đè được một tệp 200 dòng mà tác tử chưa hề đọc** — câu "đọc tệp trước" chỉ là
   một dòng gợi ý trong mô tả công cụ. Changeset có nên hoàn tác được; nhưng hoàn tác là sửa
   hậu quả, không phải ngăn nguyên nhân.
2. **Không mốc lùi nào** được đặt trước khi sửa. Người dùng nói *"bỏ hết đi"* thì phải bấm
   hoàn tác từng changeset và tự nhớ đã tới đâu.
3. `plan.exit` kiểm **hình thức** kế hoạch (đủ bước, công cụ có thật) mà không hỏi câu nào về
   **kiến trúc**. Một kế hoạch "viết 8 tệp firmware" đọc rất xuôi tai và được duyệt.
"""

from __future__ import annotations

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "đầu", "next": "n",
      "confidence": "NGUOI"}


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


# ============================================= 1. không đè mã chưa đọc
def test_khong_de_duoc_tep_chua_doc(bo, du_an):
    """Ghi đè mù hỏng theo kiểu IM LẶNG và TOÀN PHẦN: không xung đột, không cảnh báo, chỉ có
    một tệp ngắn hơn hẳn."""
    ag, r, ctx = bo
    goc = (du_an / "main.c").read_text()

    ra = r.get("fs.write").fn(ctx, path="main.c", content="int main(void){return 1;}\n",
                              explain=EX)
    assert not ra.ok and ra.error.code == "E4020"
    assert "fs.edit" in ra.error.alternatives
    assert (du_an / "main.c").read_text() == goc, "tệp đã bị đụng vào dù lời gọi bị chặn"

    # Đọc rồi thì ghi được.
    r.get("fs.read").fn(ctx, path="main.c")
    ra = r.get("fs.write").fn(ctx, path="main.c", content="int main(void){return 1;}\n",
                              explain=EX)
    assert ra["changeset"].startswith("cs-")


def test_doc_MOT_PHAN_thi_khong_tinh_la_da_doc(bo, du_an):
    """Đọc 20 dòng giữa một tệp 800 dòng rồi ghi đè cả tệp thì vẫn là xoá 780 dòng chưa nhìn."""
    ag, r, ctx = bo
    (du_an / "dai.c").write_text("\n".join(f"// dòng {i}" for i in range(200)))
    r.get("fs.read").fn(ctx, path="dai.c", offset=10, limit=20)
    ra = r.get("fs.write").fn(ctx, path="dai.c", content="// ngắn\n", explain=EX)
    assert not ra.ok and ra.error.code == "E4020"


def test_tep_MOI_thi_ghi_thang_duoc(bo):
    """Luật này chỉ về GHI ĐÈ. Tệp chưa có thì không có gì để mất."""
    ag, r, ctx = bo
    ra = r.get("fs.write").fn(ctx, path="moi.c", content="// mới\n", explain=EX)
    assert ra["tao_moi"] is True


# ============================================= 2. mốc lùi trước khi sửa
def test_dat_MOC_LUI_truoc_lan_sua_dau_tien_cua_luot(bo):
    ag, r, ctx = bo
    assert ag.history.danh_sach_snapshot(gom_checkpoint=True) == []
    ra = r.get("fs.write").fn(ctx, path="a.c", content="// a\n", explain=EX)
    moc = ra["moc_lui"]
    assert moc and moc.startswith("snap-")
    assert ag.history.snapshots.get(moc) is not None
    # Nói ra cho người dùng — một mốc không ai biết là có thì cũng như không có.
    assert moc in ra["note_vi"] and "bỏ cả lượt" in ra["note_vi"]


def test_moi_luot_MOT_moc_chu_khong_phai_moi_lan_ghi(bo):
    ag, r, ctx = bo
    r.get("fs.write").fn(ctx, path="a.c", content="// a\n", explain=EX)
    ra2 = r.get("fs.write").fn(ctx, path="b.c", content="// b\n", explain=EX)
    assert ra2["moc_lui"] is None, "đặt mốc ở mọi lần ghi thì mốc thành tiếng ồn"


# ============================================= 3. thiết kế trước khi tách việc
def _ke_hoach(r, ctx, buoc):
    r.get("plan.enter").fn(ctx, viec="x")
    return r.get("plan.exit").fn(ctx, buoc=buoc, gia_dinh=[], ngoai_pham_vi=[])


def test_ke_hoach_viet_ma_MOI_ma_thieu_kien_truc_thi_bi_chan(bo):
    """Sai kiến trúc thì tám bước sau đều sai theo, và phát hiện ở bước tám đắt gấp bội phát
    hiện ở bước không."""
    ag, r, ctx = bo
    ra = _ke_hoach(r, ctx, [
        {"viec": "Viết driver I2C", "cong_cu": "fs.write", "hien_vat": "src/i2c.c"},
        {"viec": "Viết driver SPI", "cong_cu": "fs.write", "hien_vat": "src/spi.c"},
        {"viec": "Biên dịch", "cong_cu": "build.compile", "hien_vat": "firmware.bin"}])
    assert not ra.ok and ra.error.code == "E6009"
    t = " ".join(ra.error.details["thieu"])
    assert "KIẾN TRÚC" in t and "CẤU TRÚC MÃ" in t


def test_ke_hoach_co_chon_huong_va_noi_cau_truc_thi_qua(bo):
    ag, r, ctx = bo
    ra = _ke_hoach(r, ctx, [
        {"viec": "So ba hướng chia mô-đun cho firmware", "cong_cu": "store.option_create",
         "hien_vat": "OPT-01..03"},
        {"viec": "Chốt hướng và ghi ADR", "cong_cu": "store.option_choose", "hien_vat": "ADR-01"},
        {"viec": "Viết driver I2C theo cấu trúc đã chốt: src/hal/i2c.c + src/hal/i2c.h",
         "cong_cu": "fs.write", "hien_vat": "src/hal/i2c.c"}])
    assert ra["so_buoc"] == 3, getattr(ra, "error", None)


def test_ke_hoach_SUA_ma_co_san_phai_co_buoc_phan_tich(bo):
    ag, r, ctx = bo
    ra = _ke_hoach(r, ctx, [
        {"viec": "Sửa hàm đọc cảm biến trong main.c", "cong_cu": "fs.edit",
         "hien_vat": "main.c"},
        {"viec": "Biên dịch lại", "cong_cu": "build.compile", "hien_vat": "firmware.bin"}])
    assert not ra.ok and ra.error.code == "E6009"
    assert "code.analyze" in " ".join(ra.error.details["thieu"])


def test_ke_hoach_KHONG_dong_toi_ma_thi_khong_hoi_gi(bo):
    """Cảnh báo kêu quá tay sẽ thành báo động giả, mà báo động giả dạy người ta bỏ qua."""
    ag, r, ctx = bo
    ra = _ke_hoach(r, ctx, [
        {"viec": "Nạp datasheet", "cong_cu": "doc.load", "hien_vat": "DOC-01"},
        {"viec": "Trích Fact", "cong_cu": "fact.extract", "hien_vat": "FACT-01..09"}])
    assert ra["so_buoc"] == 2


# ============================================= tài liệu phân tích mã
def test_code_analyze_tra_loi_cau_AI_DANG_DUNG(bo, du_an):
    """`fs.read` cho thấy MỘT tệp. Câu đắt nhất trước khi sửa là câu khác: ai đang dùng nó?"""
    ag, r, ctx = bo
    (du_an / "hal.c").write_text(
        "int doc_cam_bien(void){ return 42; }\nvoid khoi_tao(void){}\n")
    (du_an / "app.c").write_text("extern int doc_cam_bien(void);\nint x(void){"
                                 " return doc_cam_bien(); }\n")
    ra = r.get("code.analyze").fn(
        ctx, tep=["hal.c"], doi_gi="đổi doc_cam_bien trả về số đo đã hiệu chuẩn",
        vi_sao="số thô lệch 2 độ", explain=EX)
    assert "app.c" in ra["cho_phai_xem_lai"]
    t = (du_an / ra["tai_lieu"]).read_text("utf-8")
    assert "doc_cam_bien" in t and "app.c" in t
    # Giới hạn phải nằm TRONG tài liệu, không giấu trong mã.
    assert "Giới hạn" in t and "con trỏ hàm" in t


def test_code_analyze_doi_noi_ro_SE_DOI_GI(bo):
    """Một bản phân tích không nói sẽ đổi gì thì chỉ là một bản liệt kê."""
    ag, r, ctx = bo
    ra = r.get("code.analyze").fn(ctx, tep=["main.c"], doi_gi="cải thiện",
                                  vi_sao="cho tốt hơn", explain=EX)
    assert not ra.ok and ra.error.code == "E4022"


def test_code_analyze_noi_ro_tep_KHONG_CO(bo):
    ag, r, ctx = bo
    ra = r.get("code.analyze").fn(
        ctx, tep=["khong-co.c"], doi_gi="đổi hàm khởi tạo cho nhận tham số",
        vi_sao="cần cấu hình lúc chạy", explain=EX)
    assert ra["thieu_tep"] == ["khong-co.c"]
    assert "Kiểm lại đường dẫn" in ra["note_vi"] or "kiểm lại đường dẫn" in ra["note_vi"]


def test_tai_lieu_TACH_du_kien_khoi_nhan_dinh(bo, du_an):
    """Một con số quét ra và một câu suy đoán không đứng cùng một hàng.

    Tài liệu phải nói rõ phần nào do MÃ quét, phần nào do một tác tử ĐỌC HIỂU — người duyệt
    cần phân biệt được để biết tin tới đâu.
    """
    ag, r, ctx = bo
    (du_an / "hal.c").write_text("int doc(void){ return 1; }\n")
    ra = r.get("code.analyze").fn(ctx, tep=["hal.c"], doi_gi="đổi doc() trả giá trị hiệu chuẩn",
                                  vi_sao="số thô lệch", explain=EX)
    t = (du_an / ra["tai_lieu"]).read_text("utf-8")
    assert "## Nhận định" in t
    # ScriptedGateway hết kịch bản → phải NÓI RA là thiếu, không im lặng bỏ qua.
    assert ("Chưa có" in t or "Không lấy được" in t or "code-analyst" in t)


def test_co_tac_tu_con_code_analyst_chi_doc():
    """Phân tích là việc đọc hiểu, nhưng nó KHÔNG được sửa gì trong lúc phân tích."""
    from eide.subagent import SUBAGENT

    d = SUBAGENT["code-analyst"]
    assert d.doc_duoc_viec is True          # khác verifier: nó CẦN biết sẽ đổi gì
    ghi = [t for t in d.cong_cu if t.startswith(("fs.write", "fs.edit", "store.", "history."))
           and not t.startswith(("store.get", "store.list"))]
    assert ghi == [], f"tác tử phân tích mà có công cụ ghi: {ghi}"
    assert "gián tiếp" in d.system, "không nhắc câu hỏi đắt nhất: chỗ gọi gián tiếp"


def test_moc_lui_TOI_DUOC_so_cai(bo):
    """Một mốc không ghi lại được thì không ai tìm ra nó sau khi tắt app.

    Đo được 30/09/2026: năm changeset liên tiếp báo `snapshot_id=None` trong sổ cái, trong khi
    mốc đã thật sự được đặt — `Changeset.to_dict()` không mang trường ấy theo.
    """
    ag, r, ctx = bo
    ra = r.get("fs.write").fn(ctx, path="a.c", content="// a\n", explain=EX)
    cs = ag.history.log.get(ra["changeset"])
    assert cs.to_dict()["snapshot_id"] == ra["moc_lui"]
    # và tới được sổ cái
    import json

    dong = [json.loads(x) for x in
            (ag.config.paths.ledger).read_text("utf-8").splitlines() if x.strip()]
    cs_su_kien = [o for o in dong if o.get("kind") == "changeset"]
    assert any((o.get("data") or {}).get("snapshot_id") for o in cs_su_kien), \
        "sổ cái không thấy mốc lùi nào"


def test_code_analyze_GHI_SO_khi_goi_tac_tu_con(bo, du_an):
    """Một việc không có dấu trong sổ cái là một việc không truy vết được — và ở đây nó còn
    là một việc TỐN TIỀN không ai đếm được."""
    import inspect

    from eide.tools import xay_dung

    src = inspect.getsource(xay_dung._nhan_dinh_cua_tac_tu_con)
    assert "ghi_so=ghi" in src, "gọi subagent mà không truyền ghi_so"
