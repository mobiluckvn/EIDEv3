#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gộp hai phép đo thành một báo cáo, và TỰ KIỂM xem có sót ca nào không.

    .venv/bin/python tools/bao_cao_tong.py

Hai nguồn:

* `docs/review-v3/test/ket-qua-chay-lai/ket-qua.jsonl` — 76 ca kiểm chạy qua app thật.
* `docs/review-v3/test/ket-qua-giao-dien/ket-qua.json` — bộ quét giao diện.

Việc chính của tệp này không phải cộng số, mà là **đối chiếu với danh sách gốc**: mọi mã TC
trong `bo_usecase.py` phải có mặt trong kết quả, mọi bề mặt trong danh sách 11 phải có mặt
trong bộ quét. Thiếu một mã là một dòng ĐỎ ngay đầu báo cáo, không phải một khoảng lặng.

Vì sao đáng một tệp riêng: một bảng 76 dòng mà sót ba dòng vẫn trông đầy đủ. Người đọc không
đếm, và cái không được đếm thì không ai thấy.
"""

from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

UC = REPO / "docs/review-v3/test/ket-qua-chay-lai"
GD = REPO / "docs/review-v3/test/ket-qua-giao-dien"
RA = REPO / "docs/review-v3/test/BAO-CAO-TONG.md"

NHAN = {"dat": "Đạt", "khong_dat": "Không đạt", "ngoai_pham_vi": "Ngoài phạm vi",
        "can_nguoi": "Cần người", "can_thiet_bi": "Cần thiết bị"}


def _gop(dong: list[dict]) -> list[dict]:
    """Một mã TC chạy lại nhiều lần thì JSONL có nhiều dòng — giữ dòng CUỐI.

    Không gộp thì mọi con số đều sai theo kiểu khó thấy: "Đạt 75/76" nghe hợp lý, còn "Chưa
    chạy: -22" thì chỉ lộ ra vì nó âm. Một bảng cộng nhầm mà không có ô nào âm sẽ trôi qua.
    """
    theo: dict[str, dict] = {}
    for d in dong:
        theo[d["ma"]] = d
    return list(theo.values())


def main() -> int:
    from bo_usecase import NHOM, TEN_UC
    from quet_giao_dien import BE_MAT

    ket = []
    if (UC / "ket-qua.jsonl").exists():
        ket = _gop([json.loads(x)
                    for x in (UC / "ket-qua.jsonl").read_text("utf-8").splitlines()
                    if x.strip()])
    theo_ma = {k["ma"]: k for k in ket}

    gd = []
    if (GD / "ket-qua.json").exists():
        gd = json.loads((GD / "ket-qua.json").read_text("utf-8"))

    # Lượt ĐỌC TAY. Máy chấm bằng từ khoá trên tiếng Việt tự do đẻ ra cả ô xanh giả lẫn ô đỏ
    # giả (xem LOI-TIM-DUOC.md, L3–L6), nên nó là lượt sàng chứ không phải phán quyết. Tệp
    # này là kết luận sau khi đọc nguyên văn: mỗi mã TC → {"nhan": …, "loai": …, "ghi_chu": …}
    # với `loai` là "san_pham" (lỗi thật) hay "phep_cham" (bộ đo sai).
    tay = {}
    if (UC / "doc-tay.json").exists():
        tay = json.loads((UC / "doc-tay.json").read_text("utf-8"))

    # ---- tự kiểm: có sót không ----------------------------------------------------
    can = [t["ma"] for ds in NHOM.values() for t in ds]
    thieu = [m for m in can if m not in theo_ma]
    thua = [m for m in theo_ma if m not in can]
    phan_gd = {m["phan"] for m in gd}
    be_mat_thieu = [ma for ma, ten in BE_MAT
                    if not any(f"Bề mặt {ma} " in p for p in phan_gd)]

    # Nhãn cuối = đọc tay nếu có, không thì lấy của máy.
    for k in ket:
        t = tay.get(k["ma"])
        k["nhan_cuoi"] = (t or {}).get("nhan", k["nhan"])
        k["loai_loi"] = (t or {}).get("loai", "")
        k["ghi_chu_tay"] = (t or {}).get("ghi_chu", "")

    dem: dict[str, int] = {}
    for k in ket:
        dem[k["nhan_cuoi"]] = dem.get(k["nhan_cuoi"], 0) + 1
    dem_may: dict[str, int] = {}
    for k in ket:
        dem_may[k["nhan"]] = dem_may.get(k["nhan"], 0) + 1
    doi_nhan = [k for k in ket if k["nhan_cuoi"] != k["nhan"]]
    do_duoc = dem.get("dat", 0) + dem.get("khong_dat", 0)
    gd_dat = sum(1 for m in gd if m["dat"])

    d = ["# Báo cáo tổng — chạy toàn bộ usecase và quét toàn bộ giao diện", "",
         "Hai phép đo, một bảng. Nguồn đề bài: "
         "`docs/review-v3/test/Usecase_Test_23-09-2026.md` (19 usecase · 76 ca kiểm).", "",
         "## Tự kiểm: có sót gì không", "",
         "| Câu hỏi | Trả lời |", "|---|---|",
         f"| Đủ 76 mã TC trong kết quả? | "
         + (f"**THIẾU {len(thieu)}**: {', '.join(thieu)}" if thieu
            else f"đủ {len(can)}/{len(can)}") + " |",
         f"| Có mã lạ không nằm trong đề bài? | "
         + (f"**{len(thua)}**: {', '.join(thua)}" if thua else "không") + " |",
         f"| Đủ 11 bề mặt trong bộ quét giao diện? | "
         + (f"**THIẾU**: {', '.join(be_mat_thieu)}" if be_mat_thieu
            else f"đủ {len(BE_MAT)}/{len(BE_MAT)}") + " |",
         f"| Số ô kiểm giao diện | {gd_dat}/{len(gd)} đạt |",
         "",
         "## Tổng ca kiểm", "",
         "Hai cột: **máy chấm** (từ khoá + chuỗi công cụ) và **sau khi đọc tay** (đọc nguyên "
         "văn từng lời đáp). Máy chấm là lượt sàng, không phải phán quyết — nó đã cho cả ô "
         "xanh giả lẫn ô đỏ giả trong chính đợt này, xem `LOI-TIM-DUOC.md`.", "",
         "| Nhãn | Máy chấm | Sau khi đọc tay |", "|---|---|---|"]
    for k in ("dat", "khong_dat", "ngoai_pham_vi", "can_nguoi", "can_thiet_bi"):
        d.append(f"| {NHAN[k]} | {dem_may.get(k, 0)} | {dem.get(k, 0)} |")
    chua = len(can) - len(ket)
    d += [f"| Chưa chạy | {chua} | {chua} |",
          f"| **Tổng** | **{len(can)}** | **{len(can)}** |", ""]
    if doi_nhan:
        d += [f"**{len(doi_nhan)} ca đổi nhãn sau khi đọc tay:**", "",
              "| TC | Máy chấm | Đọc tay | Loại | Vì sao |", "|---|---|---|---|---|"]
        for k in doi_nhan:
            d.append(f"| {k['ma']} | {NHAN.get(k['nhan'], k['nhan'])} | "
                     f"{NHAN.get(k['nhan_cuoi'], k['nhan_cuoi'])} | "
                     f"{'lỗi SẢN PHẨM' if k['loai_loi'] == 'san_pham' else 'lỗi PHÉP CHẤM'} | "
                     f"{k['ghi_chu_tay']} |")
        d.append("")
    if do_duoc:
        d += [f"Trong **{do_duoc} ca đo được**: **{dem.get('dat', 0)} đạt** "
              f"({100 * dem.get('dat', 0) / do_duoc:.0f} %). "
              f"{len(can) - do_duoc} ca còn lại mang nhãn riêng — gọi chúng là *không đạt* "
              f"thì bảng nói sai về sản phẩm.", ""]

    # ---- theo nhóm ---------------------------------------------------------------
    d += ["## Theo usecase", "",
          "| UC | Tên | Đạt / đo được | Ca không đạt |", "|---|---|---|---|"]
    for uc, ds in NHOM.items():
        ms = [theo_ma.get(t["ma"]) for t in ds]
        dd = [m for m in ms if m and m["nhan_cuoi"] in ("dat", "khong_dat")]
        hong = [m["ma"] for m in ms if m and m["nhan_cuoi"] == "khong_dat"]
        d.append(f"| {uc} | {TEN_UC[uc]} | "
                 f"{sum(1 for m in dd if m['nhan_cuoi'] == 'dat')}/{len(dd)} | "
                 f"{', '.join(hong) or '—'} |")
    d.append("")

    # ---- ca không đạt, đủ chi tiết để sửa ------------------------------------------
    hong = [k for k in ket if k["nhan_cuoi"] == "khong_dat"]
    d += [f"## {len(hong)} ca không đạt — chi tiết", ""]
    for k in hong:
        d += [f"### {k['ma']} · {k['ten']}", "",
              f"- **Người gõ:** {k['nhap']}",
              f"- **Đề bài chờ:** {k['cho']}",
              f"- **Máy chấm:** {k['vi_sao']}",
              f"- **Công cụ đã gọi:** `{' → '.join(k['cong_cu']) or '—'}`",
              "", "<details><summary>Nguyên văn lời đáp</summary>", "",
              "```", (k["loi_dap"] or "(không nói gì)")[:2500], "```", "", "</details>", ""]

    # ---- ca mang nhãn riêng -------------------------------------------------------
    rieng = [k for k in ket
             if k["nhan_cuoi"] in ("ngoai_pham_vi", "can_nguoi", "can_thiet_bi")]
    if rieng:
        d += ["## Ca không đo bằng máy được — và vì sao", "",
              "| TC | Nhãn | Lý do |", "|---|---|---|"]
        for k in rieng:
            d.append(f"| {k['ma']} | {NHAN[k['nhan_cuoi']]} | {k['vi_sao']} |")
        d.append("")

    # ---- giao diện ----------------------------------------------------------------
    d += ["## Giao diện", ""]
    if not gd:
        d += ["_Chưa chạy bộ quét giao diện._", ""]
    else:
        hong_gd = [m for m in gd if not m["dat"]]
        d += [f"{gd_dat}/{len(gd)} ô đạt qua {len(phan_gd)} phần "
              f"(11 bề mặt · khung chung · thanh trạng thái · widget sửa tay · bảng Giới "
              f"thiệu · khổ cửa sổ nhỏ nhất). Ảnh từng bề mặt do chính app tự vẽ, ở "
              "`ket-qua-giao-dien/anh/`.", ""]
        if hong_gd:
            d += ["| Phần | Điều không đạt | Bằng chứng |", "|---|---|---|"]
            for m in hong_gd:
                bc = m["bang_chung"].replace("|", "\\|").replace("\n", " ")
                d.append(f"| {m['phan']} | {m['cau']} | {bc} |")
        else:
            d.append("Không ô nào đỏ.")
        d.append("")

    d += ["## Đọc bảng này thế nào", "",
          "Máy chấm ca kiểm bằng **dấu hiệu bề mặt** — cụm từ phải/không được có trong lời "
          "đáp, và công cụ phải được gọi. Một lời đáp nhắc đúng chữ mà sai ý vẫn qua được; "
          "một lời đáp đúng ý mà dùng từ khác vẫn trượt. Nên ô xanh nghĩa là *có dấu hiệu của "
          "thứ đề bài chờ*, không phải *đã làm đúng*. Nguyên văn nằm ở "
          "`ket-qua-chay-lai/ket-qua.jsonl` — đó mới là chỗ kết luận.", "",
          "Bộ quét giao diện thì đo trực tiếp thứ app đang hiện (số khối, nhãn rỗng, khối "
          "tràn khung, thẻ còn nút bấm được), nên nó chắc hơn. Nhưng nó cũng đã từng xanh "
          "trong khi màn hình sai hai lần — xem DEV-289 và DEV-290 — nên ảnh chụp là một "
          "phần của kết quả, không phải minh hoạ.", ""]

    RA.write_text("\n".join(d), "utf-8")
    print(f"Báo cáo tổng: {RA}")
    if thieu:
        print(f"CẢNH BÁO: thiếu {len(thieu)} mã TC: {', '.join(thieu)}")
    if be_mat_thieu:
        print(f"CẢNH BÁO: thiếu bề mặt: {', '.join(be_mat_thieu)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
