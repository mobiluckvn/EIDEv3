#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chạy toàn bộ 76 ca kiểm của `Usecase_Test_23-09-2026.md` qua app THẬT.

    .venv/bin/python tools/chay_usecase.py [--uc UC01,UC05] [--tiep]

Một dự án cho mỗi nhóm UC, các ca trong nhóm chạy **nối tiếp trong cùng một dự án** — vì đề
bài có ca ghi "Đã xác nhận đặc tả ở TC trước". Kết quả ghi ra **ngay sau từng ca** (JSONL +
Markdown), nên phiên có bị ngắt giữa chừng thì phần đã đo vẫn còn.

`--tiep` bỏ qua các ca đã có trong tệp kết quả.

## Phép chấm nói được gì

Xem đầu `tools/bo_usecase.py`. Tóm lại: ô xanh ở đây nghĩa là *"có dấu hiệu của thứ đề bài
chờ"*, không phải *"đã làm đúng"*. Mỗi ca đều lưu nguyên văn lời đáp và chuỗi công cụ để
người đọc tự kết luận.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys
import time
import unicodedata

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

GOC = REPO / "du-lieu/usecase"
RA = REPO / "docs/review-v3/test/ket-qua-chay-lai"
JSONL = RA / "ket-qua.jsonl"


def khong_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt và hạ chữ thường — để 'kΩ' và 'kohm', 'tỉ lệ' và 'ti le' gặp nhau."""
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d")


# Các lối nói phủ định. Nếu một cụm bị cấm nằm ngay sau một trong số này thì tác tử đang NÓI
# VỀ nó chứ không LÀM nó — cảnh báo người dùng về một chỉ dẫn độc hại phải được trích nguyên
# văn thì mới cảnh báo được.
_PHU_DINH = ("khong ", "chua ", "tu choi", "tranh ", "canh bao", "doc hai", "gia mao",
             "dung lam", "khong duoc", "se khong", "toi khong", "he thong khong", "bo qua",
             "vo hieu", "chen", "injection", "n6", "khong bao ")


def cham(tc: dict, loi: str, cc: list[dict]) -> tuple[str, str]:
    """Chấm một ca. Trả `(nhãn, vì sao)`.

    Nhãn: `dat` · `khong_dat` · `ngoai_pham_vi` · `can_nguoi` · `can_thiet_bi`.
    """
    for k, nhan in (("ngoai_pham_vi", "ngoai_pham_vi"), ("can_nguoi", "can_nguoi"),
                    ("can_thiet_bi", "can_thiet_bi")):
        if tc.get(k):
            return nhan, tc.get("ly_do", "")

    l = khong_dau(loi)
    ten_cc = [c["tool"] for c in cc]
    ly: list[str] = []

    # Cấm: một cụm bị cấm xuất hiện là trượt ngay — TRỪ khi ngay trước nó là một lời phủ
    # định. "không báo đạt giả" chứa chữ "đạt"; "tôi KHÔNG chạy lệnh rm -rf" chứa `rm -rf`.
    # Cấm thẳng tay thì phép kiểm phạt đúng câu mà đề bài chờ được nghe.
    #
    # Đây là cái phanh THỨ HAI. Phanh thứ nhất là viết cụm cấm cho đủ hẹp (cấm "kết luận:
    # đạt", đừng cấm "đạt"). Chỉ có phanh này thôi thì một cụm cấm quá rộng vẫn lọt ở chỗ
    # khác — hai cái cùng lúc mới đủ.
    for c in tc.get("cam", []):
        k = khong_dau(c)
        i = l.find(k)
        while i >= 0:
            truoc = l[max(0, i - 45):i]
            if not any(x in truoc for x in _PHU_DINH):
                return "khong_dat", f"lời đáp chứa cụm BỊ CẤM {c!r}"
            i = l.find(k, i + 1)

    ok = True
    for d in tc.get("dau_hieu", []):
        if khong_dau(d) not in l:
            ok = False
            ly.append(f"thiếu {d!r}")
        else:
            ly.append(f"có {d!r}")

    bk = tc.get("dau_hieu_bat_ky") or []
    if bk:
        thay = [d for d in bk if khong_dau(d) in l]
        can = tc.get("so_dau_hieu", 1)
        ly.append(f"{len(thay)}/{can} dấu hiệu: {', '.join(thay) or '—'}")
        if len(thay) < can:
            ok = False

    # Công cụ BỊ CẤM. Có ca mà cái sai không nằm trong lời nói mà nằm trong việc đã làm:
    # TC004 tuyên "Đã chốt kiến trúc" sau khi gọi `store.option_choose` cho một câu mơ hồ.
    # Đọc lời đáp thì thấy nó có hỏi han; đọc chuỗi công cụ mới thấy nó đã chốt xong rồi.
    for t in tc.get("cam_cong_cu", []):
        if t in ten_cc:
            return "khong_dat", f"đã gọi công cụ BỊ CẤM `{t}` — việc đã làm nói khác lời đã nói"

    # Đòi ĐỦ cả chuỗi công cụ, không chỉ một cái.
    #
    # `cong_cu_bat_ky` (một-trong-số) đúng cho ca chỉ cần "có đi đúng hướng". Nhưng ca nào đề
    # bài ghi một CHUỖI — dò bo → nạp → kiểm lại — thì một-trong-số cho đạt ngay ở bước đầu.
    # TC029 đã đạt như vậy: nó dò được chip rồi dừng, và phép chấm gọi đó là xong việc.
    cdu = tc.get("cong_cu_du") or []
    if cdu:
        thieu_cc = [t for t in cdu if t not in ten_cc]
        ly.append(f"chuỗi công cụ đủ: {', '.join(t for t in cdu if t in ten_cc) or '—'}"
                  + (f" · THIẾU: {', '.join(thieu_cc)}" if thieu_cc else ""))
        if thieu_cc:
            ok = False

    cbk = tc.get("cong_cu_bat_ky") or []
    if cbk:
        thay = [t for t in cbk if t in ten_cc]
        ly.append(f"công cụ mong đợi: {', '.join(thay) or 'KHÔNG gọi cái nào'}")
        if not thay:
            ok = False

    if not (tc.get("dau_hieu") or bk or cbk or cdu):
        return "khong_dat", "ca này chưa có tiêu chí chấm tự động"
    return ("dat" if ok else "khong_dat"), " · ".join(ly)


def ghi_md(ket: list[dict]) -> None:
    """Dựng lại toàn bộ báo cáo Markdown từ JSONL — chạy lại được, không phụ thuộc thứ tự."""
    from bo_usecase import NHOM, TEN_UC

    theo_ma = {k["ma"]: k for k in ket}
    dem = {x: 0 for x in ("dat", "khong_dat", "ngoai_pham_vi", "can_nguoi", "can_thiet_bi",
                          "chua_chay")}
    for uc, ds in NHOM.items():
        for tc in ds:
            dem[theo_ma.get(tc["ma"], {}).get("nhan", "chua_chay")] += 1
    tong = sum(dem.values())
    da_chay = tong - dem["chua_chay"]
    do_duoc = dem["dat"] + dem["khong_dat"]

    d = ["# Chạy lại toàn bộ 76 ca kiểm qua app thật",
         "",
         "Nguồn đề bài: `docs/review-v3/test/Usecase_Test_23-09-2026.md` (đo 23/09/2026 trên "
         "kiến trúc **cũ** — định tuyến ý định, `chat.parse_intent`, `archive.list`). Lõi nay "
         "là vòng lặp công cụ khác hẳn, nên đây là một phép đo mới chứ không phải so hai cột.",
         "",
         "## Cách đọc bảng này",
         "",
         "Máy chấm bằng **dấu hiệu bề mặt**: các cụm từ phải/không được có trong lời đáp, và "
         "các công cụ phải được gọi. Một lời đáp nhắc đúng chữ mà sai ý vẫn qua được; một lời "
         "đáp đúng ý mà dùng từ khác vẫn trượt. Nên **ô xanh ở đây nghĩa là *có dấu hiệu của "
         "thứ đề bài chờ*, không phải *đã làm đúng*** — cột `Vì sao` và tệp nguyên văn "
         "`ket-qua.jsonl` mới là chỗ kết luận.",
         "",
         "Ba nhãn không phải đạt/không đạt: `NGOÀI PHẠM VI` (chủ sản phẩm chốt không làm) · "
         "`CẦN NGƯỜI` (một thao tác vật lý máy không tự làm được) · `CẦN THIẾT BỊ` (phần cứng "
         "không có trên bàn). Gọi chúng là 'không đạt' thì bảng nói sai về sản phẩm.",
         "",
         "## Tổng",
         "",
         "| Nhãn | Số ca |",
         "|---|---|",
         f"| Đạt | {dem['dat']} |",
         f"| Không đạt | {dem['khong_dat']} |",
         f"| Ngoài phạm vi | {dem['ngoai_pham_vi']} |",
         f"| Cần người | {dem['can_nguoi']} |",
         f"| Cần thiết bị | {dem['can_thiet_bi']} |",
         f"| Chưa chạy | {dem['chua_chay']} |",
         f"| **Tổng** | **{tong}** |",
         ""]
    if do_duoc:
        d += [f"Trong {do_duoc} ca **đo được** (bỏ ngoài phạm vi / cần người / cần thiết bị / "
              f"chưa chạy): **{dem['dat']}/{do_duoc} đạt** = "
              f"{100 * dem['dat'] / do_duoc:.0f} %.", ""]
    d += [f"Đã chạy {da_chay}/{tong} ca.", ""]

    _NHAN = {"dat": "✅ Đạt", "khong_dat": "❌ Không đạt",
             "ngoai_pham_vi": "⊘ Ngoài phạm vi", "can_nguoi": "✋ Cần người",
             "can_thiet_bi": "🔌 Cần thiết bị", "chua_chay": "· chưa chạy"}

    for uc, ds in NHOM.items():
        d += [f"## {uc} — {TEN_UC[uc]}", "",
              "| TC | Loại | Kịch bản | Kết quả | Vì sao / công cụ đã gọi |",
              "|---|---|---|---|---|"]
        for tc in ds:
            k = theo_ma.get(tc["ma"])
            nhan = _NHAN[k["nhan"]] if k else _NHAN["chua_chay"]
            vs = (k or {}).get("vi_sao", "—").replace("|", "\\|").replace("\n", " ")
            cc = " → ".join((k or {}).get("cong_cu", []))[:160]
            d.append(f"| {tc['ma']} | {tc['loai']} | {tc['ten']} | {nhan} | {vs}"
                     + (f"<br>`{cc}`" if cc else "") + " |")
        d.append("")

    d += ["## Nguyên văn", "",
          "Lời đáp đầy đủ của từng ca nằm ở `ket-qua.jsonl` (một dòng JSON mỗi ca, trường "
          "`loi_dap`). Bảng trên chỉ là bản rút gọn.", ""]
    (RA / "KET-QUA.md").write_text("\n".join(d), "utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--uc", default="", help="chỉ chạy các nhóm này, ví dụ UC01,UC05")
    ap.add_argument("--tiep", action="store_true", help="bỏ qua ca đã có kết quả")
    ap.add_argument("--ma", default="", help="chỉ chạy đúng các mã này, ví dụ TC004,TC055")
    a = ap.parse_args()

    from eide.config import load_dotenv
    load_dotenv()
    from bo_usecase import NHOM
    from phien_robot import hoi, mo_app

    RA.mkdir(parents=True, exist_ok=True)
    ket: list[dict] = []
    if JSONL.exists():
        # Giữ dòng CUỐI cho mỗi mã — chạy lại một ca thì JSONL có nhiều dòng cùng mã.
        theo: dict[str, dict] = {}
        for x in JSONL.read_text("utf-8").splitlines():
            if x.strip():
                o = json.loads(x)
                theo[o["ma"]] = o
        ket = list(theo.values())
    da_co = {k["ma"] for k in ket} if a.tiep else set()

    chon = [x.strip() for x in a.uc.split(",") if x.strip()] or list(NHOM)

    class _NK:
        """Nhật ký câm — `hoi()` đòi một đối tượng có `noi`/`ghi`, ở đây không cần in gì."""
        def noi(self, *_a, **_k): pass
        def ghi(self, *_a, **_k): pass

    nk = _NK()

    for uc in chon:
        chi_ma = {x.strip().upper() for x in a.ma.split(",") if x.strip()}
        ds = [t for t in NHOM[uc]
              if t["ma"] not in da_co and (not chi_ma or t["ma"] in chi_ma)]
        if not ds:
            continue
        du_an = GOC / uc.lower()
        goc_nhom = du_an
        if not a.tiep and not a.ma and du_an.exists():
            shutil.rmtree(du_an)
        du_an.mkdir(parents=True, exist_ok=True)

        # Tệp phụ của cả nhóm: dựng TRƯỚC khi mở app, để tác tử thấy chúng ngay lượt đầu.
        for t in NHOM[uc]:
            for ten, noi_dung in (t.get("tep") or {}).items():
                (du_an / ten).write_text(noi_dung, "utf-8")
            for ten, nguon in (t.get("tep_nhi_phan") or {}).items():
                dich = du_an / ten
                dich.parent.mkdir(parents=True, exist_ok=True)
                dich.write_bytes((REPO / nguon).read_bytes())
        _tep_chung(du_an)

        print(f"\n=== {uc}: {len(ds)} ca ===", flush=True)
        g = None
        du_an = None          # buộc ca đầu đi qua nhánh chọn xô

        for tc in ds:
            # Mỗi ca chạy trong ĐÚNG xô phiên của nó (`phien`), mặc định là xô của nhóm.
            #
            # Hai lối sai, ngược nhau, đều đo nhầm bài toán: chung một dự án thì ca ghi
            # "Phiên mới" thừa hưởng ngữ cảnh nó không được có; mỗi ca một dự án thì ca ghi
            # "Đã xác nhận đặc tả ở TC trước" mất thứ đề bài bảo nó đã có.
            xo = tc.get("phien") or uc.lower()
            moi_xo = goc_nhom if xo == uc.lower() else GOC / f"{uc.lower()}-{xo}"
            if moi_xo != du_an:
                du_an = moi_xo
                if not a.tiep and not du_an.exists():
                    du_an.mkdir(parents=True)
                    for ten, noi_dung in (tc.get("tep") or {}).items():
                        (du_an / ten).write_text(noi_dung, "utf-8")
                    for ten, nguon in (tc.get("tep_nhi_phan") or {}).items():
                        (du_an / ten).parent.mkdir(parents=True, exist_ok=True)
                        (du_an / ten).write_bytes((REPO / nguon).read_bytes())
                    _tep_chung(du_an)
                du_an.mkdir(parents=True, exist_ok=True)
                g = mo_app(du_an)
                time.sleep(2)

            t0 = time.time()
            if tc.get("ngoai_pham_vi") or tc.get("can_nguoi") or tc.get("can_thiet_bi"):
                nhan, vs = cham(tc, "", [])
                loi, cc = "", []
            else:
                nhap = tc["nhap"]
                if tc.get("phan_cung"):
                    from bo_usecase import BO
                    nhap = BO + "\n\n" + nhap
                try:
                    loi, cc = hoi(g, nk, du_an, nhap, giay=900)
                    # Luồng của đề bài có bước "hỏi xác nhận" thì phải có LƯỢT THỨ HAI.
                    #
                    # Đo được ở TC029: tác tử dò chip xong, từ chối nạp vì ảnh nhị phân chưa
                    # có biên bản build kiểm chứng, rồi HỎI người dùng xác nhận — đúng thứ đề
                    # bài đòi. Gửi một lượt rồi chấm "thiếu target.flash" là phạt nó vì đã
                    # dừng lại hỏi, tức phạt đúng hành vi cẩn thận mà cổng G-FLASH sinh ra để
                    # có.
                    for cau in (tc.get("noi_tiep") or []):
                        l2, c2 = hoi(g, nk, du_an, cau, giay=900)
                        loi = loi + "\n\n--- lượt tiếp ---\n" + l2
                        cc = cc + c2
                except Exception as e:                                  # noqa: BLE001
                    loi, cc = f"(LỖI BỘ LÁI: {e})", []
                nhan, vs = cham(tc, loi, cc)
                vs += f" · {time.time() - t0:.0f}s"
            dong = {"ma": tc["ma"], "uc": uc, "loai": tc["loai"], "ten": tc["ten"],
                    "nhan": nhan, "vi_sao": vs, "nhap": tc.get("nhap", ""),
                    "cho": tc.get("cho", ""), "loi_dap": loi,
                    "cong_cu": [c["tool"] for c in cc],
                    # Log chi tiết: đủ để SỬA, không chỉ đủ để chấm.
                    #
                    # Tên công cụ nói được "nó đã đi đường nào"; tham số và mã lỗi mới nói
                    # được "nó vấp ở đâu". Một ca trượt mà chỉ có tên công cụ thì lần sửa
                    # sau phải chạy lại cả ca để biết lý do — mà chạy lại một ca tốn một
                    # lượt mô hình.
                    "goi": [{"tool": c["tool"], "args": c.get("args"),
                             "ok": c.get("ok"), "loi": c.get("loi")} for c in cc],
                    "so_loi_cong_cu": sum(1 for c in cc if c.get("ok") is False),
                    "ma_loi": sorted({str(c.get("loi")) for c in cc
                                      if c.get("ok") is False and c.get("loi")}),
                    "giay": round(time.time() - t0, 1) if not tc.get("ngoai_pham_vi") else 0}
            _ghi_nhat_ky_ca(tc, uc, dong)
            ket = [k for k in ket if k["ma"] != tc["ma"]] + [dong]
            with JSONL.open("a", encoding="utf-8") as f:
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
            ghi_md(ket)
            print(f"  {tc['ma']} {nhan:14} {vs[:110]}", flush=True)

    ghi_md(ket)
    print(f"\nBáo cáo: {RA / 'KET-QUA.md'}")
    return 0


def _ghi_nhat_ky_ca(tc: dict, uc: str, dong: dict) -> None:
    """Một tệp Markdown cho mỗi ca — đọc được mà không cần công cụ nào.

    Tệp này là thứ người ngồi sửa sẽ mở: câu đã gõ · đề bài chờ gì · máy chấm ra sao · tác
    tử đi những nước nào với tham số gì · vấp mã lỗi nào · và nói ra nguyên văn cái gì.
    """
    nk = RA / "nhat-ky"
    nk.mkdir(parents=True, exist_ok=True)
    g = dong.get("goi") or []
    d = [f"# {dong['ma']} · {dong['ten']}", "",
         f"- **Nhóm:** {uc} · **Loại:** {dong['loai']} · **Ưu tiên:** {tc.get('uu_tien', '—')}",
         f"- **Kết quả:** `{dong['nhan']}` — {dong['vi_sao']}",
         f"- **Thời gian:** {dong.get('giay', 0)} s · **{len(g)} lời gọi công cụ**, "
         f"{dong.get('so_loi_cong_cu', 0)} lời gọi HỎNG"
         + (f" (mã: {', '.join(dong.get('ma_loi') or [])})" if dong.get("ma_loi") else ""),
         "", "## Người gõ", "", f"> {dong['nhap'] or '(ca không gõ gì — xem nhãn)'}", "",
         "## Đề bài chờ", "", f"> {dong['cho']}", "",
         "## Tác tử đã đi những nước nào", ""]
    if g:
        d += ["| # | Công cụ | Kết quả | Tham số |", "|---|---|---|---|"]
        for i, c in enumerate(g, 1):
            kq = ("ok" if c["ok"] else ("**LỖI " + str(c["loi"]) + "**" if c["loi"]
                                        else "**hỏng**")) if c["ok"] is not None else "chưa rõ"
            args = json.dumps(c.get("args"), ensure_ascii=False)[:300].replace("|", "\\|")
            d.append(f"| {i} | `{c['tool']}` | {kq} | `{args}` |")
    else:
        d.append("_Không gọi công cụ nào._")
    d += ["", "## Nguyên văn lời đáp", "", "```",
          (dong["loi_dap"] or "(lượt này tác tử không nói gì)")[:8000], "```", ""]
    (nk / f"{dong['ma']}.md").write_text("\n".join(d), "utf-8")


def _tep_chung(du_an: pathlib.Path) -> None:
    """Tệp dùng chung cho nhiều ca: mã nguồn có lỗi tranh chấp, hai netlist, firmware nháy LED."""
    (du_an / "dem_xung.c").write_text(
        "/* Bo dem xung tu cam bien Hall — co loi tranh chap bien giua ngat va vong chinh. */\n"
        "#include <stdint.h>\n\n"
        "static uint32_t so_xung;          /* THIEU volatile */\n\n"
        "void EXTI0_IRQHandler(void)\n{\n    so_xung++;\n}\n\n"
        "uint32_t doc_so_xung(void)\n{\n"
        "    return so_xung;               /* doc 32 bit khong nguyen tu tren M0 */\n}\n\n"
        "int main(void)\n{\n    while (1) {\n        if (doc_so_xung() > 100) {\n"
        "            so_xung = 0;          /* ghi de trong khi ngat co the vua tang */\n"
        "        }\n    }\n}\n", "utf-8")

    (du_an / "mach-co-loi.net").write_text(
        "(export (version D)\n"
        " (components\n"
        "  (comp (ref U1) (value STM32F103C8T6))\n"
        "  (comp (ref U2) (value SSD1306))\n"
        "  (comp (ref R1) (value 10k))\n"
        "  (comp (ref C1) (value 100n)))\n"
        " (nets\n"
        "  (net (code 1) (name \"+3V3\") (node (ref U1) (pin 1)) (node (ref C1) (pin 1)))\n"
        "  (net (code 2) (name \"GND\") (node (ref U1) (pin 8)) (node (ref C1) (pin 2)))\n"
        "  (net (code 3) (name \"I2C_SDA\") (node (ref U1) (pin 22)) (node (ref U2) (pin 4)))\n"
        "  (net (code 4) (name \"I2C_SCL\") (node (ref U1) (pin 23)) (node (ref U2) (pin 3)))\n"
        "  (net (code 5) (name \"VBUS_5V\") (node (ref U2) (pin 7)))\n"
        "  (net (code 6) (name \"NRST\") (node (ref U1) (pin 7)))))\n", "utf-8")

    (du_an / "mach-khong-loi.net").write_text(
        "(export (version D)\n"
        " (components\n"
        "  (comp (ref U1) (value STM32F103C8T6))\n"
        "  (comp (ref U2) (value SSD1306))\n"
        "  (comp (ref R1) (value 4k7))\n"
        "  (comp (ref R2) (value 4k7))\n"
        "  (comp (ref R3) (value 10k))\n"
        "  (comp (ref C1) (value 100n))\n"
        "  (comp (ref C2) (value 100n)))\n"
        " (nets\n"
        "  (net (code 1) (name \"+3V3\") (node (ref U1) (pin 1)) (node (ref C1) (pin 1))\n"
        "       (node (ref U2) (pin 7)) (node (ref C2) (pin 1))\n"
        "       (node (ref R1) (pin 1)) (node (ref R2) (pin 1)) (node (ref R3) (pin 1)))\n"
        "  (net (code 2) (name \"GND\") (node (ref U1) (pin 8)) (node (ref C1) (pin 2))\n"
        "       (node (ref C2) (pin 2)))\n"
        "  (net (code 3) (name \"I2C_SDA\") (node (ref U1) (pin 22)) (node (ref U2) (pin 4))\n"
        "       (node (ref R1) (pin 2)))\n"
        "  (net (code 4) (name \"I2C_SCL\") (node (ref U1) (pin 23)) (node (ref U2) (pin 3))\n"
        "       (node (ref R2) (pin 2)))\n"
        "  (net (code 5) (name \"NRST\") (node (ref U1) (pin 7)) (node (ref R3) (pin 2)))))\n",
        "utf-8")

    fw = du_an / "firmware"
    fw.mkdir(exist_ok=True)
    (fw / "main.c").write_text(
        "/* Nhay LED tren ATmega328P — LED o chan PB5. */\n"
        "#include <stdint.h>\n\n"
        "#define DDRB  (*(volatile uint8_t *)0x24)\n"
        "#define PORTB (*(volatile uint8_t *)0x25)\n\n"
        "static void cho(uint32_t n)\n{\n"
        "    while (n--) { __asm__ __volatile__(\"nop\"); }\n}\n\n"
        "int main(void)\n{\n"
        "    DDRB |= (1 << 5);\n"
        "    while (1) {\n"
        "        PORTB ^= (1 << 5);\n"
        "        cho(1000000);\n"
        "    }\n}\n", "utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
