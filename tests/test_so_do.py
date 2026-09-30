# -*- coding: utf-8 -*-
"""Sơ đồ mermaid phải thành HÌNH trong tài liệu xuất ra, không thành khối mã.

Bộ này đo phía Python (`so_do.py` + `xuat_ban.py`). Phía giao diện đo bằng
`tools/thu_so_do.py` qua app thật.

## Ca quan trọng nhất nằm ở cuối: hai bộ đọc phải đọc RA CÙNG MỘT THỨ

`Views/SoDo.swift` và `src/eide/so_do.py` đọc cùng một tập con mermaid bằng hai ngôn ngữ —
một cái giá có thật của việc lõi không gọi ngược lên app được. Ràng buộc giữ hai bên khớp
nhau là **cùng một tập sơ đồ thật** trong `docs/` và `du-lieu/`: cả hai phải ra cùng số vai,
cùng số khối, cùng nhãn. Ca `test_hai_bo_doc_ra_cung_mot_thu` là chỗ ràng buộc ấy nổ nếu ai
sửa một bên mà quên bên kia.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from eide.so_do import bo_emoji, doc, kieu, tom_tat, ve_png
from eide.xuat_ban import cong_thuc_nguoi_doc, doc_markdown, render

GOC = Path(__file__).resolve().parents[1]
pytest.importorskip("PIL")


def _mermaid(tep: str, bat_dau: str) -> str:
    t = (GOC / tep).read_text("utf-8")
    for m in re.finditer(r"```mermaid\s*\n(.*?)```", t, re.S):
        if m.group(1).strip().startswith(bat_dau):
            return m.group(1).strip()
    pytest.skip(f"không còn sơ đồ {bat_dau} trong {tep}")


TUAN_TU = "du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md"
KHOI = "docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md"


# ======================================================== đọc
def test_doc_so_do_tuan_tu_that_cua_tac_tu():
    t = doc(_mermaid(TUAN_TU, "sequenceDiagram"))
    assert [v.nhan for v in t.vai][0] == "Người dùng"
    assert len(t.vai) == 7
    assert t.danh_so is True
    assert sum(1 for x in t.dong if x[0] == "tin") == 12
    assert any(x[0] == "mo" and x[1] == "loop" for x in t.dong)
    assert any(x[0] == "ghi_chu" for x in t.dong)


def test_the_br_thanh_xuong_dong_khong_con_the():
    t = doc(_mermaid(TUAN_TU, "sequenceDiagram"))
    chu = [x[3] for x in t.dong if x[0] == "ghi_chu"]
    assert chu and "\n" in chu[0] and "<br" not in chu[0]


def test_doc_so_do_khoi_that_co_subgraph():
    l = doc(_mermaid(KHOI, "graph"))
    assert len(l.nut) == 8 and len(l.canh) == 8
    assert l.ngang is False                       # `graph TB`
    assert any("Kỹ sư nhúng" in n.nhan for n in l.nut)
    assert any(c.nhan == "tìm datasheet" for c in l.canh)


def test_mui_ten_dai_doc_truoc_mui_ten_ngan():
    """`->>` là tiền tố của `-->>`. Dò ngắn trước thì MỌI lời đáp thành lời gọi."""
    t = doc("sequenceDiagram\n  A->>B: gọi\n  B-->>A: đáp\n")
    net = [x[4] for x in t.dong if x[0] == "tin"]
    assert net == ["lien", "dut"]


def test_kieu_chua_ve_duoc_tra_None_va_noi_dung_ten():
    assert doc("gantt\n  title X\n") is None
    assert kieu("gantt\n  title X\n") == "gantt"
    assert doc("classDiagram\n  A <|-- B\n") is None


def test_bo_emoji_vi_phong_khong_ve_duoc():
    """Phông có dấu tiếng Việt trên macOS không có emoji — vẽ ra là một Ô VUÔNG RỖNG, và ô
    vuông rỗng trông như lỗi phông."""
    assert bo_emoji("👤 Kỹ sư nhúng") == "Kỹ sư nhúng"
    assert bo_emoji("Bo mạch thật") == "Bo mạch thật"


# ======================================================== vẽ
def test_ve_ra_PNG_that_va_co_kich_thuoc_doc_duoc(tmp_path):
    from PIL import Image

    for tep, bd in ((TUAN_TU, "sequenceDiagram"), (KHOI, "graph")):
        ra, vi = ve_png(_mermaid(tep, bd), tmp_path / f"{bd}.png")
        assert ra is not None, vi
        with Image.open(ra) as im:
            assert im.width > 300 and im.height > 100


def test_so_do_qua_be_thi_xoay_huong_cho_vua_trang_giay(tmp_path):
    """Trang A4 rộng 6,5 inch. Tỉ lệ 6:1 thu cho vừa trang thì chữ không đọc được."""
    from PIL import Image

    md = ("graph LR\n" + "\n".join(f'  N{i}["Khối số {i}"]' for i in range(10))
          + "\n" + "\n".join(f"  N{i} --> N{i+1}" for i in range(9)))
    ra, vi = ve_png(md, tmp_path / "be.png")
    assert ra is not None, vi
    with Image.open(ra) as im:
        assert im.width / im.height < 2.5, f"vẫn bè: {im.width}×{im.height}"


def test_khong_ve_duoc_thi_noi_ro_chu_khong_im_lang(tmp_path):
    ra, vi = ve_png("erDiagram\n  A ||--o{ B : co\n", tmp_path / "x.png")
    assert ra is None and "erDiagram" in vi


# ======================================================== vào tài liệu
def test_khoi_mermaid_tach_thanh_khoi_so_do_chu_khong_phai_ma():
    k = doc_markdown("```mermaid\ngraph LR\n A-->B\n```\n")
    assert [x.loai for x in k] == ["so_do"]
    assert doc_markdown("```bash\ngraph LR\n```\n")[0].loai == "ma"


def test_docx_chua_ANH_chu_khong_chua_ma_mermaid(tmp_path):
    docx = pytest.importorskip("docx")
    md = "# Kiến trúc\n\n```mermaid\n" + _mermaid(KHOI, "graph") + "\n```\n"
    p = tmp_path / "a.docx"
    assert render(md, p, "docx").dat
    tl = docx.Document(str(p))
    chu = "\n".join(x.text for x in tl.paragraphs)
    assert "graph TB" not in chu and "-->" not in chu, "mã mermaid lọt vào tài liệu"
    assert "Sơ đồ khối" in chu                      # chú thích dưới hình
    assert len(tl.inline_shapes) >= 1, "không có hình nào trong tệp"


def test_pptx_moi_tieu_de_mot_slide_va_so_do_thanh_hinh(tmp_path):
    pptx = pytest.importorskip("pptx")
    md = ("# Báo cáo\n\n## Phần 1\n\nNội dung một.\n\n## Phần 2\n\n```mermaid\n"
          + _mermaid(KHOI, "graph") + "\n```\n")
    p = tmp_path / "b.pptx"
    kq = render(md, p, "pptx")
    assert kq.dat, kq.vi_sao_khong_dat
    assert kq.do_lai["so_slide"] >= 4               # bìa + 2 phần + slide sơ đồ
    assert kq.do_lai["so_hinh"] >= 1
    tr = pptx.Presentation(str(p))
    chu = "\n".join(sh.text_frame.text for s in tr.slides for sh in s.shapes
                    if sh.has_text_frame)
    assert "graph TB" not in chu


def test_cong_thuc_tex_khong_in_nguyen_cu_phap():
    ra = cong_thuc_nguoi_doc(
        r"$$\text{PLLM} = 8 \implies f_{\text{SYSCLK}} = \frac{8\text{ MHz}}{8} "
        r"\times \frac{360}{2} = 180\text{ MHz}$$")
    assert "\\frac" not in ra and "\\text" not in ra and "$$" not in ra
    assert "⇒" in ra and "×" in ra and "180 MHz" in ra


# ======================================================== hai bộ đọc phải khớp
def test_hai_bo_doc_ra_cung_mot_thu():
    """Bộ đọc Swift và bộ đọc Python phải ra cùng số vai / khối / nhãn.

    Hai bản dịch cùng một cú pháp là cái giá của việc lõi không gọi ngược lên app được. Ca
    này là chỗ cái giá ấy được TRẢ: sửa một bên mà quên bên kia thì đỏ ở đây.

    Nguồn đối chiếu là tệp kết quả của `tools/thu_so_do.py` — chạy qua app THẬT. Chưa chạy
    lần nào thì bỏ qua, và nói rõ là bỏ qua vì sao.
    """
    kq = GOC / "du-lieu/ket-qua/so-do.jsonl"
    if not kq.exists():
        pytest.skip("chưa chạy tools/thu_so_do.py — không có số của phía Swift để đối chiếu")
    dong = [json.loads(l) for l in kq.read_text("utf-8").splitlines() if l.strip()]
    swift = {d.get("ten"): d for d in dong if isinstance(d, dict)}
    # Bộ Swift ghi "7 vai" trong tóm tắt; bên Python phải ra đúng thế.
    t = doc(_mermaid(TUAN_TU, "sequenceDiagram"))
    assert f"{len(t.vai)} vai" in tom_tat(_mermaid(TUAN_TU, "sequenceDiagram"))
    assert any("7 vai" in json.dumps(d, ensure_ascii=False) for d in dong), \
        f"phía Swift không còn báo 7 vai — hai bộ đọc đã lệch. {list(swift)[:3]}"


def test_mui_ten_hai_chieu_khong_de_ra_khoi_ma():
    """`A <--> B` từng đẻ ra một khối tên `A <`.

    `<-->` chứa `-->`, nên dò `-->` trước sẽ cắt ở giữa; phần trái còn `"A <"` — có dấu cách
    nên không khớp mẫu khai nút, rơi xuống nhánh mặc định và thành một khối có thật với cái
    tên vô nghĩa. Nhìn thấy trong app trên sơ đồ tác tử vừa vẽ; không con số nào kêu.
    """
    l = doc('graph LR\n  MOD_MCU["MCU"] <--> MOD_SENSOR["Cảm biến"]\n')
    assert sorted(n.ma for n in l.nut) == ["MOD_MCU", "MOD_SENSOR"]
    assert len(l.canh) == 1
    for bien in ("<-.->", "<==>"):
        l2 = doc(f'graph LR\n  A["a"] {bien} B["b"]\n')
        assert sorted(n.ma for n in l2.nut) == ["A", "B"], bien


# ==================================================== khung cụm `subgraph` không được chồng
#
# Lỗi thấy ngày 30/09/2026 trên chính sơ đồ mô-đun RTOS ở tab Thiết kế: khung `firmware` và
# `firmware/rtos` chồng một nửa lên nhau, nên `main.c` nhìn ra như nằm trong thư mục `rtos`.
#
# Không con số nào của bộ quét bắt được — `ve_png` trả về PNG hợp lệ, số khối và số nối đều
# đúng. **Một hình sai vẫn là một hình vẽ được.** Nên `xep_cho` được tách ra khỏi phép vẽ, để
# hình học đo được bằng số thay vì bằng mắt.

_HAI_CUM = """graph TB
    subgraph g0["firmware"]
        n0["main.c"]
        n1["stm32f4xx_hal.h"]
    end
    subgraph g1["firmware/rtos"]
        n3["rtos_core.c"]
        n4["rtos_port.c"]
        n2["rtos_queue.c"]
        n5["rtos_types.h"]
    end
    n0 --> n5
    n0 --> n1
    n3 --> n5
    n4 --> n5
    n2 --> n5"""


def _hop_cum(so, khung):
    """Hộp bao của từng cụm — đúng phép hợp mà `_ve_luong` dùng để vẽ khung."""
    ra = {}
    for i, n in enumerate(so.nut):
        if n.cum is None or not khung[i]:
            continue
        x, y, w, h = khung[i]
        cu = ra.get(n.cum)
        ra[n.cum] = (x, y, x + w, y + h) if cu is None else (
            min(cu[0], x), min(cu[1], y), max(cu[2], x + w), max(cu[3], y + h))
    return ra


def _chong(a, b) -> bool:
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _xep(nguon):
    from eide.so_do import _luong, xep_cho
    so = _luong(nguon)
    kt = [(max(len(n.nhan) * 8 + 30, 90), 44) for n in so.nut]
    cho = [(0, 0)] * len(so.nut)
    tang = [0] * len(so.nut)
    for _ in range(len(so.nut)):
        for c in so.canh:
            tang[c.den] = max(tang[c.den], tang[c.tu] + 1)
    return so, xep_cho(so, kt, cho, tang)[0]


def test_hai_khung_subgraph_KHONG_chong_len_nhau():
    so, khung = _xep(_HAI_CUM)
    hop = _hop_cum(so, khung)
    assert len(hop) == 2
    a, b = hop[0], hop[1]
    assert not _chong(a, b), f"khung cụm chồng nhau: {a} ∩ {b}"


def test_moi_nut_nam_TRONG_khung_cum_cua_chinh_no():
    """Phép kiểm thật sự người đọc quan tâm: tệp có hiện đúng trong thư mục của nó không."""
    so, khung = _xep(_HAI_CUM)
    hop = _hop_cum(so, khung)
    for i, n in enumerate(so.nut):
        if n.cum is None:
            continue
        x, y, w, h = khung[i]
        k = hop[n.cum]
        assert k[0] <= x and k[1] <= y and x + w <= k[2] and y + h <= k[3]
        for ci, kc in hop.items():
            if ci != n.cum:
                assert not _chong((x, y, x + w, y + h), kc), \
                    f"{n.nhan} (cụm {n.cum}) nằm lọt vào khung cụm {ci}"


def test_chua_cho_cho_NHAN_cum_o_mep_tren():
    """Khung cụm vươn lên trên nút cao nhất 24 px để nhét nhãn — thiếu chỗ thì nhãn bị cắt."""
    so, khung = _xep(_HAI_CUM)
    assert min(k[1] for k in khung if k) >= 24


def test_so_do_KHONG_cum_giu_nguyen_bo_cuc():
    """Chống hồi quy: phép chia dải chỉ được chạy khi có cụm."""
    from eide.so_do import _luong, xep_cho
    nguon = "graph TB\n    A[\"một\"] --> B[\"hai\"]\n    B --> C[\"ba\"]"
    so = _luong(nguon)
    assert not so.cum
    kt = [(90, 44)] * len(so.nut)
    khung, w, h = xep_cho(so, kt, [(0, 0)] * len(so.nut), [0, 1, 2])
    assert min(k[1] for k in khung if k) < 24, "không có cụm thì không được chừa lề nhãn"
