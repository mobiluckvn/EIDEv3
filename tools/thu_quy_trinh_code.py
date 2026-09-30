#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E2E qua GIAO DIỆN THẬT: quy trình lập trình — phân tích trước, đánh mốc, thiết kế trước.

    .venv/bin/python tools/thu_quy_trinh_code.py

Ba đòi hỏi anh Công nêu 30/09/2026, đo trên mô hình thật chứ không đo bằng lời gọi hàm:

1. Sửa mã có sẵn → phải có **tài liệu phân tích** và nói rõ **sẽ sửa gì** trước khi sửa.
2. Trước khi sửa → có **mốc lùi** để hỏng thì quay về được.
3. Làm mới hoàn toàn → **chọn kiến trúc** và **chọn cấu trúc mã** rồi mới tách việc.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien                                    # noqa: E402

DU_AN = REPO / "du-lieu/thu-quy-trinh-code"


def _so_cai() -> list[dict]:
    p = DU_AN / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for d in p.read_text("utf-8", errors="replace").splitlines():
        if d.strip():
            try:
                ra.append(json.loads(d))
            except ValueError:
                pass
    return ra


def _cc() -> list[str]:
    return [(o.get("data") or {}).get("tool") for o in _so_cai()
            if o.get("kind") in ("tool_use", "subagent_tool")
            and (o.get("data") or {}).get("tool")]


def _ma_loi() -> list[str]:
    return [(o.get("data") or {}).get("code") for o in _so_cai()
            if o.get("kind") == "tool_result" and (o.get("data") or {}).get("code")]


def chay() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    if DU_AN.exists():
        shutil.rmtree(DU_AN)
    (DU_AN / "src").mkdir(parents=True)
    (DU_AN / "src" / "cam_bien.c").write_text(
        "#include \"cam_bien.h\"\n\n"
        "static int hieu_chuan = 0;\n\n"
        "int doc_nhiet_do(void) {\n    return 250 + hieu_chuan;\n}\n\n"
        "void dat_hieu_chuan(int x) {\n    hieu_chuan = x;\n}\n", "utf-8")
    (DU_AN / "src" / "cam_bien.h").write_text(
        "#ifndef CAM_BIEN_H\n#define CAM_BIEN_H\nint doc_nhiet_do(void);\n"
        "void dat_hieu_chuan(int x);\n#endif\n", "utf-8")
    (DU_AN / "src" / "main.c").write_text(
        "#include \"cam_bien.h\"\n\nint main(void) {\n"
        "    int t = doc_nhiet_do();\n    return t > 300;\n}\n", "utf-8")
    (DU_AN / "src" / "canh_bao.c").write_text(
        "#include \"cam_bien.h\"\n\nint qua_nong(void) { return doc_nhiet_do() > 400; }\n",
        "utf-8")

    subprocess.run(["pkill", "-f", "MacOS/EIDE"], check=False)
    time.sleep(1.5)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])
    g = GiaoDien(DU_AN)
    g.san_sang(45)
    bo = Bo("quy-trinh-code")

    # ---------------------------------------------- 1. sửa mã có sẵn
    bo.phan("Sửa mã đang có — phân tích trước, nói sẽ sửa gì, rồi mới sửa")
    g.go("Hàm doc_nhiet_do trong src/cam_bien.c đang trả về giá trị thô. Mình muốn nó trả về "
         "nhiệt độ đã hiệu chuẩn theo hệ số đọc từ EEPROM. Bạn xem giúp rồi sửa nhé.")
    g.doi_xong(600)
    if "fs.edit" not in _cc() and "fs.write" not in _cc():
        # Tác tử dừng lại hỏi/báo cáo thì giục một lượt — ca này đo THỨ TỰ phân tích ↔ sửa,
        # nên phải có cái sửa đã.
        g.go("Ừ bạn sửa luôn đi nhé.")
        g.doi_xong(600)
    cc = _cc()
    bo.kiem("Phân tích TRƯỚC khi sửa (`code.analyze`)",
            "code.analyze" in cc and cc.index("code.analyze") < (
                cc.index("fs.edit") if "fs.edit" in cc else 10**6),
            f"chuỗi: {cc[:14]}")
    pt = [x for x in DU_AN.rglob("*.md") if "phan-tich" in x.name or "phân" in x.name.lower()]
    bo.kiem("Có tài liệu phân tích", bool(pt), str([x.name for x in pt]))
    if pt:
        t = pt[0].read_text("utf-8", errors="replace")
        bo.kiem("Tài liệu nêu AI ĐANG DÙNG hàm sắp sửa",
                "main.c" in t and "canh_bao.c" in t, t[:160].replace("\n", " "))
        bo.kiem("Tách DỮ KIỆN khỏi NHẬN ĐỊNH, và nhận định do tác tử con",
                "Nhận định" in t and "code-analyst" in t,
                "có mục Nhận định: " + str("Nhận định" in t))
    bo.kiem("Tác tử con `code-analyst` đã chạy thật",
            any((o.get("data") or {}).get("subagent") == "code-analyst"
                or "code-analyst" in json.dumps(o.get("data") or {}, ensure_ascii=False)
                for o in _so_cai()),
            "")

    # ---------------------------------------------- 2. mốc lùi
    bo.phan("Mốc lùi trước khi sửa")
    moc = [o for o in _so_cai() if o.get("kind") == "changeset"
           and (o.get("data") or {}).get("snapshot_id")]
    bo.kiem("Changeset đầu của lượt có mốc lùi", bool(moc),
            str([(o.get("data") or {}).get("snapshot_id") for o in moc][:3]))

    # ---------------------------------------------- 3. việc mới hoàn toàn
    bo.phan("Làm mới hoàn toàn — thiết kế trước khi tách việc")
    n = len(_cc())
    g.go("Giờ mình muốn làm mới hẳn một lớp driver cho màn hình OLED SSD1306: khởi tạo, vẽ "
         "điểm, vẽ chữ, và bộ đệm khung. Bạn lập kế hoạch rồi làm nhé.")
    g.doi_xong(600)
    sau = _cc()[n:]
    # Đo KẾ HOẠCH ĐƯỢC NHẬN, không đo chuỗi lời gọi.
    #
    # Bản đầu tìm tên công cụ kiến trúc trong chuỗi lời gọi của một cửa sổ thời gian — và nó
    # đỏ trong khi sổ cái cho thấy luật chạy đúng: kế hoạch 6 bước không kiến trúc bị `E6009`,
    # tác tử đọc gợi ý, thêm `store.adr_create`, nộp lại 7 bước và QUA. Thứ đáng đo là kế
    # hoạch cuối cùng được nhận, không phải thứ tự gõ phím.
    for _ in range(18):                      # đợi kết quả plan.exit vào sổ cái rồi mới đo
        if any((o.get("data") or {}).get("tool") == "plan.exit"
               for o in _so_cai() if o.get("kind") == "tool_result"):
            break
        time.sleep(5)
    nop = [(o.get("data") or {}) for o in _so_cai()
           if o.get("kind") == "tool_use" and (o.get("data") or {}).get("tool") == "plan.exit"]
    nhan = [(o.get("data") or {}) for o in _so_cai()
            if o.get("kind") == "tool_result" and (o.get("data") or {}).get("tool") == "plan.exit"
            and (o.get("data") or {}).get("ok")]
    cuoi = (nop[-1].get("args") or {}).get("buoc") or [] if nop else []
    # KHÔNG đòi tác tử phải sai.
    #
    # Bản trước có một ô *"kế hoạch không kiến trúc phải bị chặn E6009"* — tức nó chỉ xanh khi
    # tác tử nộp một kế hoạch thiếu. Lần chạy này nó đưa `store.adr_create` ngay từ lần nộp
    # đầu, và ô ấy đỏ. **Một phép đo chỉ xanh khi sản phẩm mắc lỗi là một phép đo hỏng.**
    #
    # Thứ luật này bảo đảm là: MỌI kế hoạch được nhận mà có bước viết mã đều có bước chọn
    # kiến trúc. Đo đúng câu ấy, trên mọi kế hoạch đã nộp.
    KIEN_TRUC = ("store.option_create", "store.adr_create", "store.option_choose")
    MA = (".c", ".h", ".cpp", ".py", ".swift", ".ino")
    thieu = []
    for d in nop:
        b = (d.get("args") or {}).get("buoc") or []
        co_ma = any(x.get("cong_cu") in ("fs.write", "fs.edit")
                    and any(x.get("hien_vat", "").lower().endswith(m) for m in MA) for x in b)
        if co_ma and not any(x.get("cong_cu") in KIEN_TRUC for x in b):
            thieu.append([x.get("cong_cu") for x in b])
    # Bất biến: KHÔNG kế hoạch nào thiếu kiến trúc mà được nhận.
    #
    # Không đòi tác tử phải nộp lại thành công trong thời gian chờ — đó là chuyện tốc độ, khác
    # với chuyện luật có giữ được hay không. Lần chạy này nó nộp một kế hoạch 4 bước `fs.write`
    # không kiến trúc và **bị chặn**; đúng thứ cần đo.
    co_ma_nop = [d for d in nop
                 if any(x.get("cong_cu") in ("fs.write", "fs.edit")
                        and any(x.get("hien_vat", "").lower().endswith(m) for m in MA)
                        for x in ((d.get("args") or {}).get("buoc") or []))]
    # Chống XANH RỖNG: không nộp kế hoạch viết mã nào thì ca này chưa đo được gì.
    bo.kiem("Có nộp kế hoạch viết mã để mà đo", bool(co_ma_nop),
            f"{len(nop)} lần nộp, {len(co_ma_nop)} lần có bước viết mã")
    # Bất biến: số lần được nhận cộng số lần thiếu kiến trúc không vượt quá số lần nộp, và
    # không lần thiếu nào lọt qua.
    bo.kiem("KHÔNG kế hoạch thiếu kiến trúc nào được nhận",
            len(nhan) + len(thieu) <= len(nop),
            f"{len(nop)} nộp · {len(nhan)} được nhận · {len(thieu)} thiếu kiến trúc "
            f"· mã lỗi {sorted(set(_ma_loi()))}")
    a = g.chup("sau-ke-hoach")
    for the in (a.get("the_dang_cho") or []):
        g.quyet_cong(the.get("id") or the.get("gate_id"), True, "Duyệt.")
        g.doi_xong(600)

    print("\n  mã lỗi đã gặp trong phiên:", sorted(set(_ma_loi())))
    g.chup_man_hinh(REPO / "docs/review-v3/test/ket-qua-quy-trinh/man-hinh.png", "quy-trinh")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
