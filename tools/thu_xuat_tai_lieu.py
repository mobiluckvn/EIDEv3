#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E qua GIAO DIỆN THẬT: tác tử tự làm ra tệp `.docx` / `.xlsx` / `.pdf`.

    .venv/bin/python tools/thu_xuat_tai_lieu.py

Bộ kiểm đơn vị đã chứng minh `xuat_ban.py` dựng được tệp khi **tôi** gọi hàm. Bộ này hỏi một
câu khác hẳn, và là câu duy nhất đáng tin: **tác tử có tự chọn `doc.render` không**, khi người
dùng chỉ nói bằng tiếng Việt qua ô nhập của app?

Một công cụ đăng ký xong mà mô hình không bao giờ gọi thì đúng bằng không có. Chuyện ấy đã xảy
ra trong chính dự án này: bộ dò độ nhạy chạy 0/402 lượt vì đường dẫn tới nó đứt, trong khi mã
của nó vẫn xanh.

## Ba ca

1. **Word** — "xuất ra file Word cho tôi". Đợi chờ: có `.docx`, mở lại được, có chữ.
2. **Excel từ bảng** — nguồn có bảng. Đợi chờ: có `.xlsx`, sheet có hàng.
3. **Excel từ văn xuôi** — cố tình không có bảng. Đợi chờ: tác tử **nói không làm được và
   nói vì sao**, chứ không đẻ ra một tệp rỗng. Đây là ca quan trọng nhất: một công cụ chỉ
   biết nói "xong" thì chưa dùng được.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien                                    # noqa: E402

DU_AN = REPO / "du-lieu/thu-tai-lieu"


def _mo_lai(p: pathlib.Path) -> dict:
    """Mở tệp bằng chính thư viện đọc, không tin vào số byte."""
    from eide.xuat_ban import doc_lai_docx, doc_lai_pdf, doc_lai_xlsx

    return {".docx": doc_lai_docx, ".xlsx": doc_lai_xlsx,
            ".pdf": doc_lai_pdf}[p.suffix.lower()](p)


def _tep(duoi: str) -> list[pathlib.Path]:
    return sorted(x for x in DU_AN.rglob(f"*{duoi}") if ".eide" not in x.parts)


def _cong_cu_da_goi() -> list[str]:
    """Tên công cụ tác tử đã gọi, đọc từ SỔ CÁI.

    Ảnh chụp giao diện không mang chuỗi công cụ — nó mang thứ trên màn hình. Sổ cái mới là
    nơi ghi tác tử đã gọi gì, và nó là nguồn không sửa được.
    """
    import json

    p = DU_AN / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra: list[str] = []
    for d in p.read_text("utf-8").splitlines():
        if not d.strip():
            continue
        try:
            o = json.loads(d)
        except ValueError:
            continue
        d = o.get("data") or {}
        ten = d.get("tool") or d.get("name")
        if o.get("kind") in ("tool_use", "subagent_tool") and ten:
            ra.append(ten)
    return ra



def _ma_loi_cua(ten: str) -> list[str]:
    """Mã lỗi mà một công cụ đã trả trong cả phiên, đọc từ sổ cái."""
    import json

    p = DU_AN / ".eide" / "ledger.jsonl"
    ra: list[str] = []
    for d in (p.read_text("utf-8").splitlines() if p.exists() else []):
        if not d.strip():
            continue
        try:
            o = json.loads(d)
        except ValueError:
            continue
        x = o.get("data") or {}
        if o.get("kind") == "tool_result" and x.get("tool") == ten and x.get("code"):
            ra.append(x["code"])
    return ra


def _la_bang_that(p: pathlib.Path) -> bool:
    """Bảng thật: từ 2 cột và 3 hàng trở lên, và không ô nào dài như một đoạn văn.

    Ô dài hơn 400 ký tự là dấu hiệu của văn xuôi bị nhét vào ô — đúng thứ `sang_xlsx` từ
    chối làm, nên nếu nó xuất hiện thì có ai đó đã đi vòng qua.
    """
    import openpyxl

    wb = openpyxl.load_workbook(str(p), read_only=True)
    try:
        ws = wb.worksheets[0]
        if ws.max_row < 3 or ws.max_column < 2:
            return False
        for h in ws.iter_rows(values_only=True):
            if any(len(str(o or "")) > 400 for o in h):
                return False
        return True
    finally:
        wb.close()

def chay() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    if DU_AN.exists():
        shutil.rmtree(DU_AN)
    DU_AN.mkdir(parents=True)
    (DU_AN / "so-lieu.md").write_text(
        "# Kết quả đo dòng tiêu thụ\n\n"
        "Đo trên bo STM32F469I-DISCO, ba chế độ.\n\n"
        "| Chế độ | Dòng (mA) | Ghi chú |\n|---|---|---|\n"
        "| Chạy đủ tốc | 92 | LCD bật |\n"
        "| Ngủ nhẹ | 21 | LCD tắt |\n"
        "| Ngủ sâu | 3 | chỉ RTC |\n", "utf-8")
    (DU_AN / "y-tuong.md").write_text(
        "# Ý tưởng\n\nMột thiết bị đo nhiệt độ phòng, gửi số liệu qua Wi-Fi.\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])

    g = GiaoDien(DU_AN)
    g.san_sang(40)
    bo = Bo("xuat-tai-lieu")

    # ------------------------------------------------------------------ ca 1: Word
    bo.phan("Ca 1 — xin một tệp Word")
    g.go("Bạn viết giúp tôi một tài liệu ngắn giới thiệu ý tưởng trong y-tuong.md, "
         "rồi xuất ra file Word để tôi gửi cho thầy nhé.")
    g.doi_xong(300)
    cc = _cong_cu_da_goi()
    bo.kiem("Tác tử tự gọi `doc.render`", "doc.render" in cc, f"chuỗi công cụ: {cc}")
    docx = _tep(".docx")
    bo.kiem("Có tệp .docx trong dự án", bool(docx), str([str(x.name) for x in docx]))
    if docx:
        do = _mo_lai(docx[0])
        bo.kiem("Mở lại được và CÓ CHỮ", do.get("so_ky_tu", 0) > 50, str(do))

    # ------------------------------------------------------------------ ca 2: Excel có bảng
    bo.phan("Ca 2 — xin Excel từ nguồn CÓ bảng")
    truoc_cc = len(_cong_cu_da_goi())
    g.go("Bảng số liệu trong so-lieu.md, bạn xuất ra file Excel giúp tôi.")
    g.doi_xong(300)
    cc = _cong_cu_da_goi()[truoc_cc:]
    bo.kiem("Gọi `doc.render` với xlsx", "doc.render" in cc, f"chuỗi công cụ: {cc}")
    xlsx = _tep(".xlsx")
    bo.kiem("Có tệp .xlsx", bool(xlsx), str([str(x.name) for x in xlsx]))
    if xlsx:
        do = _mo_lai(xlsx[0])
        bo.kiem("Sheet có hàng dữ liệu", do.get("tong_hang", 0) >= 4, str(do))

    # ------------------------------------------------------------- ca 3: Excel từ văn xuôi
    #
    # Ca quan trọng nhất, và ca đã dạy tôi một lần nữa: **số đo đúng, câu hỏi sai**.
    #
    # Bản đầu của ca này hỏi "tác tử có từ chối không" và chấm bằng việc chữ `bảng` có mặt
    # trong lời đáp. Nó XANH — nhưng cái thật sự xảy ra khác hẳn: `doc.render` từ chối
    # (`E2013`), tác tử **đọc gợi ý trong lỗi, tự thêm một bảng thật vào tệp nguồn**, rồi
    # xuất lại. Kết quả là một bảng 7 hàng dùng được, không phải một tệp rỗng.
    #
    # Hành vi ấy đúng hơn cái tôi định đo (hiến pháp §4: hỏi không phải là dừng). Nên ca này
    # đổi câu hỏi cho khớp với thứ đáng quan tâm — ba câu, không một:
    #
    #   1. hàng rào có NỔ không (E2013 phải có mặt trong sổ cái);
    #   2. tệp ra có thật sự là BẢNG không, hay chỉ là văn xuôi nhét vào ô;
    #   3. tác tử có NÓI RA rằng nó đã sửa tệp nguồn không — người dùng không được phát
    #      hiện tệp của mình đổi bằng cách tự tình cờ mở ra xem.
    bo.phan("Ca 3 — xin Excel từ nguồn KHÔNG có bảng")
    truoc = set(_tep(".xlsx"))
    g.go("File y-tuong.md ấy, bạn xuất thẳng ra Excel cho tôi.")
    a = g.doi_xong(300)
    loi = (a.get("loi_tac_tu_cuoi") or "").lower()
    moi_ra = sorted(set(_tep(".xlsx")) - truoc)

    bo.kiem("Hàng rào NỔ: `doc.render` trả E2013 ít nhất một lần",
            "E2013" in _ma_loi_cua("doc.render"), str(_ma_loi_cua("doc.render")))
    bo.kiem("Tệp ra là BẢNG THẬT, không phải văn xuôi nhét vào ô",
            not moi_ra or all(_la_bang_that(x) for x in moi_ra),
            "; ".join(f"{x.name}: {_mo_lai(x)}" for x in moi_ra) or "không tạo thêm tệp nào")
    bo.kiem("NÓI RA là đã sửa tệp nguồn", (not moi_ra) or ("y-tuong.md" in loi), loi[:300])

    # ------------------------------------------------------- ca 4: sơ đồ vào bản trình chiếu
    #
    # Ca này đo cả hai chiều một lúc: tác tử có TỰ VẼ khi cần cho thấy một trình tự không, và
    # sơ đồ ấy có vào tệp thành HÌNH không. Trước 29/09/2026 nó vào thành khối mã — một trang
    # slide đầy cú pháp `A->>B:` là thứ không ai trình bày được.
    bo.phan("Ca 4 — sơ đồ tuần tự vào bản trình chiếu")
    g.go("Bạn mô tả giúp tôi trình tự lúc người dùng chạm vào màn hình cảm ứng rồi giao diện "
         "đổi trang, vẽ sơ đồ cho dễ hiểu. Xong xuất ra file PowerPoint để tôi trình bày nhé.")
    a = g.doi_xong(600)
    loi = a.get("loi_tac_tu_cuoi") or ""
    bo.kiem("Tác tử tự vẽ bằng ```mermaid", "```mermaid" in loi, loi[:200])
    bo.kiem("Khối sơ đồ trên màn hình là `sơ-đồ`, không phải `khối-mã`",
            "sơ-đồ" in (a.get("khoi_markdown") or []),
            str(a.get("khoi_markdown"))[:200])
    pptx = [x for x in DU_AN.rglob("*.pptx") if ".eide" not in x.parts]
    bo.kiem("Có tệp .pptx", bool(pptx), str([x.name for x in pptx]))
    if pptx:
        from eide.xuat_ban import doc_lai_pptx

        do = doc_lai_pptx(pptx[0])
        bo.kiem("Slide có HÌNH, không phải mã mermaid", do.get("so_hinh", 0) >= 1, str(do))

    g.chup_man_hinh(REPO / "docs/review-v3/test/ket-qua-tai-lieu/man-hinh.png", "xuat-tai-lieu")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
