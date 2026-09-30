# -*- coding: utf-8 -*-
"""Phần phân tích và thiết kế của tác tử phải HIỆN RA trên tab, không chỉ trôi qua Console.

Anh Công theo dõi phiên dựng RTOS và nói: *"việc phân tích và thiết kế của Agent khá okay
nhưng nội dung đó chưa được show ở tab bên cạnh"*. Đo lại trên chính dự án `rtos-ptit`:

    A2  Yêu cầu & Giải pháp    A2.1∅  A2.3  A2.4
    A5  Thiết kế               A5.4∅  A5.2∅          ← RỖNG HOÀN TOÀN
    A7  Mã nguồn               A7.1  build

Tác tử vừa so ba phương án kiến trúc, chốt một cái qua cổng G-DESIGN, chia việc thành 6 bước
qua 12 phiên bản kế hoạch, viết một tài liệu phân tích mã — mà tab Thiết kế không có gì, kế
hoạch không nằm ở tab nào, tài liệu phân tích không nằm ở tab nào.

*Một phân tích không ai mở ra đọc được thì đúng bằng một phân tích chưa làm.*

Các phép kiểm dưới đây đo trên dữ liệu hình dạng thật của dự án ấy.
"""

from __future__ import annotations

from typing import Any

import pytest

from eide import surfaces as S
from eide.kien_truc import muc_kien_truc, so_do_mo_dun


# --------------------------------------------------------------------------- kho giả
class KhoGia:
    """Kho tối thiểu: chỉ cần `list(type)` và `get(id)` như bề mặt thật dùng."""

    def __init__(self, **theo_loai: list[dict[str, Any]]):
        self._d = theo_loai

    def list(self, loai: str | None = None, limit: int = 100, **kw: Any):
        return list(self._d.get(loai or "", []))[:limit]

    def get(self, aid: str):
        for xs in self._d.values():
            for a in xs:
                if a["id"] == aid:
                    return a
        return None


def _hv(aid: str, loai: str, canonical: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return {"id": aid, "type": loai, "version": kw.pop("version", 1),
            "author": kw.pop("author", "agent:run-001"), "canonical": canonical,
            "explain": kw.pop("explain", {"summary": ""}), "stale": False,
            "stale_reason": None, **kw}


PA_A = _hv("PA-A", "option", {
    "ten": "Nhân tiền định ưu tiên dựa trên PendSV",
    "kien_truc": "Nhân tiền định đa mức ưu tiên với PendSV, Bitmap O(1) và TCB tĩnh.",
    "linh_kien_chinh": ["PendSV context switcher", "Bitmap priority scheduler O(1)"],
    "rui_ro": ["Cần kiểm soát lưu ngữ cảnh FPU (s16-s31) để tránh tràn stack"],
    "do_kho": "trung bình", "chi_phi_uoc": "RAM ~1,5 KB", "da_chon": True})
PA_B = _hv("PA-B", "option", {
    "ten": "Nhân hợp tác không chiếm quyền",
    "kien_truc": "Nhân đa nhiệm hợp tác dựa trên nhường quyền tự nguyện.",
    "rui_ro": ["Một tác vụ không nhường thì cả hệ đứng"],
    "do_kho": "thấp", "chi_phi_uoc": "RAM ~0,5 KB", "da_chon": False})
ADR = _hv("ADR-01", "adr", {
    "tieu_de": "Chọn nhân tiền định ưu tiên", "chon": "PA-A",
    "boi_canh": "Nhân tiền định đa mức ưu tiên.",
    "he_qua": ["Triển khai PendSV và SysTick cho Cortex-M4F"],
    "quyet_boi": "tac_tu", "trich_loi_nguoi": ""})


# ===================================================================== A5.6 kiến trúc
def test_tab_thiet_ke_HIEN_kien_truc_phan_mem_khi_KHONG_co_mach():
    """Phép kiểm chính: dự án phần mềm thuần, không CKM, tab Thiết kế vẫn có nội dung."""
    kho = KhoGia(option=[PA_A, PA_B], adr=[ADR], code=[])
    r = S.design(kho, None)
    ma = {b["code"]: b for b in r["blocks"]}
    assert "A5.6" in ma, "tab Thiết kế không có khối kiến trúc phần mềm"
    assert ma["A5.6"]["type"] == "sections"
    ten = " ".join(s["ten"] for s in ma["A5.6"]["sections"])
    assert "Kiến trúc đã chọn" in ten
    assert "Rủi ro" in ten, "rủi ro nêu lúc chọn là thứ dễ mất nhất — phải có mục riêng"


def test_khoi_kien_truc_RONG_khi_chua_co_phuong_an():
    """Chống rỗng giả: không có phương án thì khối phải RỖNG, không bịa ra mục nào."""
    r = S.design(KhoGia(), None)
    ma = {b["code"]: b for b in r["blocks"]}
    assert ma["A5.6"]["type"] == "empty"
    assert ma["A5.6"]["chua_co"] and ma["A5.6"]["vi_sao"] and ma["A5.6"]["can_gi"]


def test_phuong_an_BI_LOAI_van_hien_kem_ly_do():
    """Phương án đã loại là bối cảnh của quyết định — mất nó thì ADR thành một mệnh lệnh."""
    muc = muc_kien_truc(KhoGia(option=[PA_A, PA_B], adr=[ADR]))
    than = "\n".join(m["than"] for m in muc)
    assert "PA-B" in than
    assert "Một tác vụ không nhường thì cả hệ đứng" in than, "rủi ro của phương án loại bị mất"


def test_he_qua_cua_ADR_hien_ra():
    muc = muc_kien_truc(KhoGia(option=[PA_A], adr=[ADR]))
    assert any("PendSV và SysTick" in m["than"] for m in muc)


# ===================================================== sơ đồ mô-đun — cạnh phải CÓ THẬT
def test_so_do_dung_canh_tu_include_THAT(tmp_path):
    (tmp_path / "rtos").mkdir()
    (tmp_path / "rtos" / "rtos_core.c").write_text(
        '#include "rtos_types.h"\nvoid f(void){}\n', "utf-8")
    (tmp_path / "rtos" / "rtos_types.h").write_text("#define N 8\n", "utf-8")
    (tmp_path / "main.c").write_text('#include "rtos_types.h"\nint main(void){}\n', "utf-8")

    ma, doc, canh = so_do_mo_dun(str(tmp_path),
                                 ["main.c", "rtos/rtos_core.c", "rtos/rtos_types.h"])
    assert doc == 3 and canh == 2
    assert ma.startswith("graph TB")
    assert ma.count("-->") == 2
    assert 'subgraph' in ma and 'rtos' in ma, "mô-đun phải nhóm theo thư mục"


def test_KHONG_ve_so_do_khi_khong_co_quan_he_nao(tmp_path):
    """Chống trang trí: ba ô rời không nối gì trông như bản vẽ kiến trúc mà không nói gì.

    Vẽ ra thì người đọc tưởng đã có thiết kế mô-đun. Không vẽ, và nói vì sao không vẽ, thì
    người đọc biết đúng thứ mình đang có.
    """
    for t in ("a.c", "b.c", "c.c"):
        (tmp_path / t).write_text("int x;\n", "utf-8")
    ma, doc, canh = so_do_mo_dun(str(tmp_path), ["a.c", "b.c", "c.c"])
    assert ma == "" and doc == 3 and canh == 0


def test_khong_doc_duoc_tep_thi_NOI_RA_chu_khong_im(tmp_path):
    kho = KhoGia(option=[PA_A], adr=[ADR],
                 code=[_hv("firmware/khong-co.c", "code", {"path": "firmware/khong-co.c"})])
    than = "\n".join(m["than"] for m in muc_kien_truc(kho, str(tmp_path)))
    assert "Chưa vẽ được sơ đồ" in than


# ============================================================== A2.5 kế hoạch chia việc
KE_HOACH = _hv("plan:current", "plan", {
    "muc_tieu": "Triển khai nhân RTOS tiền định trong firmware/rtos/",
    "trang_thai": "hoan_thanh",
    "gia_dinh": ["Chuỗi công cụ arm-none-eabi-gcc có hỗ trợ FPU Cortex-M4F"],
    "ngoai_pham_vi": ["Chưa triển khai cấp phát bộ nhớ động", "Chưa bật MPU"],
    "steps": [{"viec": "Tạo tệp định nghĩa kiểu dữ liệu", "cong_cu": "fs.write",
               "hien_vat": "firmware/rtos/rtos_types.h", "chi_phi": "1 lời gọi",
               "ghi_chu": "Định nghĩa TCB", "xong": True},
              {"viec": "Biên dịch firmware", "cong_cu": "build.compile",
               "hien_vat": "build", "chi_phi": "1 lời gọi", "ghi_chu": "", "xong": False}]},
    version=12)


def test_ke_hoach_HIEN_tren_tab_A2():
    r = S.requirements(KhoGia(plan=[KE_HOACH]), None)
    ma = {b["code"]: b for b in r["blocks"]}
    assert "A2.5" in ma and ma["A2.5"]["type"] == "ke_hoach"
    assert ma["A2.5"]["summary"].startswith("1/2 bước xong")


def test_ke_hoach_giu_GIA_DINH_va_NGOAI_PHAM_VI():
    """Hai danh sách này là thứ người cần nhất lúc nghiệm thu, và trôi nhanh nhất ở Console."""
    b = {x["code"]: x for x in S.requirements(KhoGia(plan=[KE_HOACH]), None)["blocks"]}["A2.5"]
    assert b["gia_dinh"] == ["Chuỗi công cụ arm-none-eabi-gcc có hỗ trợ FPU Cortex-M4F"]
    assert "Chưa bật MPU" in b["ngoai_pham_vi"]


def test_moi_buoc_mang_theo_HIEN_VAT():
    """Hiện vật phân biệt một bước ĐÃ LÀM với một bước được kể là đã làm (`plan.step_done`)."""
    b = {x["code"]: x for x in S.requirements(KhoGia(plan=[KE_HOACH]), None)["blocks"]}["A2.5"]
    assert [x["hien_vat"] for x in b["buoc"]] == ["firmware/rtos/rtos_types.h", "build"]
    assert [x["so"] for x in b["buoc"]] == [1, 2]


def test_khoi_ke_hoach_KHONG_co_nut_bam():
    """Bước chỉ đóng được bằng `plan.step_done`, mà công cụ ấy đòi hiện vật mở ra xem được.

    Một nút "Xong" trên tab là đường vòng qua đúng cái đòi hỏi làm nên giá trị của kế hoạch.
    """
    b = {x["code"]: x for x in S.requirements(KhoGia(plan=[KE_HOACH]), None)["blocks"]}["A2.5"]
    assert "buttons" not in b and "actions" not in b
    for x in b["buoc"]:
        assert "trang_thai" not in x, "trường này là thứ KhoiQuyTrinh dùng để vẽ ba nút"


def test_moi_trang_thai_ke_hoach_deu_co_chu_tieng_viet():
    """Chú thích cũ ở `KeHoach.trang_thai` chỉ kể BỐN trạng thái, mã ghi SÁU.

    Một danh sách kể thiếu tệ hơn không kể, vì nó trông như đã đủ.
    """
    from eide.ke_hoach import TEN_TRANG_THAI_VI
    for tt in ("dang_soan", "cho_duyet", "da_duyet", "hoan_thanh", "huy", "da_cat"):
        assert tt in TEN_TRANG_THAI_VI, f"trạng thái {tt} chưa có chữ cho người đọc"


def test_khoi_ke_hoach_RONG_khi_chua_lap_ke_hoach():
    ma = {b["code"]: b for b in S.requirements(KhoGia(), None)["blocks"]}
    assert ma["A2.5"]["type"] == "empty"


# ======================================================== A2.4 "Ai quyết" — ba trạng thái
class SoCaiGia:
    def __init__(self, su_kien): self._e = su_kien

    def read(self): return self._e


class SuKien:
    def __init__(self, kind, data): self.kind, self.data = kind, data


def _so_cai_co_duyet(cong="G-DESIGN"):
    return SoCaiGia([
        SuKien("gate", {"gate_id": "gate-0001", "gate": cong, "state": "open"}),
        SuKien("human_act", {"kind": "decide",
                             "data": {"approved": True, "gate_id": "gate-0001"}})])


def test_ai_quyet_noi_ro_NGUOI_DA_DUYET_QUA_CONG():
    """Đo được trên `rtos-ptit`: tác tử đề xuất, anh bấm duyệt `gate-0001` lúc 09:06:37.

    Tab chỉ hiện "Tác tử" — đọc ra thành "tác tử tự quyết, không ai xem". Nói thiếu về phía
    người là một cách nói sai.
    """
    r = S.requirements(KhoGia(adr=[ADR]), None, _so_cai_co_duyet())
    o = {b["code"]: b for b in r["blocks"]}["A2.4"]["rows"][0][3]
    assert "duyệt" in o and "G-DESIGN" in o


def test_ai_quyet_phan_biet_TAC_TU_TU_QUYET_khi_khong_ai_duyet():
    r = S.requirements(KhoGia(adr=[ADR]), None, SoCaiGia([]))
    assert "chưa ai duyệt" in {b["code"]: b for b in r["blocks"]}["A2.4"]["rows"][0][3]


def test_ai_quyet_noi_ANH_QUYET_khi_nguoi_that_su_chon():
    adr = _hv("ADR-02", "adr", {**ADR["canonical"], "quyet_boi": "nguoi",
                                "trich_loi_nguoi": "Mình chọn phương án 2 nhé"})
    r = S.requirements(KhoGia(adr=[adr]), None, SoCaiGia([]))
    assert {b["code"]: b for b in r["blocks"]}["A2.4"]["rows"][0][3] == "Anh quyết"


def test_ba_trang_thai_ai_quyet_KHAC_NHAU_tung_doi_mot():
    """Chống vô nghĩa: ba nhánh phải ra ba chữ khác nhau, không phải ba tên gọi của một thứ."""
    nguoi = _hv("A", "adr", {**ADR["canonical"], "quyet_boi": "nguoi"})
    ra = {S._ai_quyet(nguoi, set()),
          S._ai_quyet(ADR, {"G-DESIGN"}),
          S._ai_quyet(ADR, set())}
    assert len(ra) == 3


def test_so_cai_hong_khong_lam_SAP_tab():
    """Sổ cái đọc lỗi thì cột "Ai quyết" phải thận trọng, chứ không ném ngoại lệ ra giao diện."""
    class Hong:
        def read(self): raise OSError("sổ cái hỏng")
    r = S.requirements(KhoGia(adr=[ADR]), None, Hong())
    assert "chưa ai duyệt" in {b["code"]: b for b in r["blocks"]}["A2.4"]["rows"][0][3]


# ================================================= A7.2 tài liệu phân tích mã trước khi sửa
def test_tai_lieu_phan_tich_HIEN_noi_dung_that(tmp_path):
    (tmp_path / "tai-lieu").mkdir()
    (tmp_path / "tai-lieu" / "phan-tich-ma.md").write_text(
        "# Phân tích\n\n`rtos_delay_ms` đang được `HAL_Delay` gọi.\n", "utf-8")
    kho = KhoGia(note=[_hv("tai-lieu/phan-tich-ma.md", "note",
                           {"path": "tai-lieu/phan-tich-ma.md"}, version=2)],
                 code=[], config=[], build=[], analysis=[], procedure=[])
    ma = {b["code"]: b for b in S.code_surface(kho, None, str(tmp_path))["blocks"]}
    assert "A7.2" in ma
    assert "HAL_Delay" in ma["A7.2"]["sections"][0]["than"], "chỉ liệt kê tên tệp là chưa đủ"


def test_tai_lieu_phan_tich_khong_doc_duoc_thi_NOI_RA(tmp_path):
    kho = KhoGia(note=[_hv("tai-lieu/mat-roi.md", "note", {"path": "tai-lieu/mat-roi.md"})],
                 code=[], config=[], build=[], analysis=[], procedure=[])
    ma = {b["code"]: b for b in S.code_surface(kho, None, str(tmp_path))["blocks"]}
    than = ma["A7.2"]["sections"][0]["than"]
    assert "Chưa đọc được" in than and "vẫn còn trong kho" in than


def test_tai_lieu_qua_dai_bi_CAT_va_noi_la_da_cat(tmp_path):
    (tmp_path / "d.md").write_text("x" * (S.TRAN_CHU_PHAN_TICH + 500), "utf-8")
    kho = KhoGia(note=[_hv("d.md", "note", {"path": "d.md"})],
                 code=[], config=[], build=[], analysis=[], procedure=[])
    than = {b["code"]: b for b in
            S.code_surface(kho, None, str(tmp_path))["blocks"]}["A7.2"]["sections"][0]["than"]
    assert "cắt bớt" in than and "500 ký tự" in than


def test_KHONG_co_khoi_A7_2_khi_chua_phan_tich_gi():
    kho = KhoGia(code=[], config=[], build=[], analysis=[], procedure=[], note=[])
    assert "A7.2" not in {b["code"] for b in S.code_surface(kho, None, "")["blocks"]}


# ============================================================ giao diện vẽ được kiểu khối
@pytest.mark.parametrize("kieu", ["ke_hoach", "sections"])
def test_giao_dien_biet_ve_kieu_khoi_moi(kieu):
    """Lõi sinh ra một `type` mà Swift không có nhánh `case` thì tab hiện ô vàng "chưa biết vẽ".

    Đây là phép kiểm rẻ nhất bắt được chuyện ấy, vì nó đọc chính tệp Swift.
    """
    import pathlib
    sw = pathlib.Path(__file__).resolve().parents[1] / (
        "ui/EIDEApp/Sources/EIDE/Views/SurfaceView.swift")
    assert f'case "{kieu}"' in sw.read_text("utf-8"), f"Swift chưa dựng được khối {kieu}"
