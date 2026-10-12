#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Năm tầng lùi và khối diff, đo QUA APP THẬT — EIDE-EDIT-47 §DEV-365, §DEV-366.

    python tools/thu_nut_lui.py

Vì sao phải có bộ này bên cạnh `tests/test_edit47_nut_lui.py` và `LuiTests.swift`:

* bộ Python đi qua `console.act` — nó chứng minh **lõi làm đúng** khi nhận ý chí của người;
* bộ Swift gọi thẳng các hàm của `AppState` — nó chứng minh **nút gửi đúng thứ**;
* còn câu *"người bấm vào app thì có lùi được không"* thì không bộ nào trong hai bộ ấy trả
  lời. Cả gói DEV-365 sinh ra vì đúng một loại hỏng: **cơ chế có sẵn, đường lên giao diện
  đứt**. Một phép đo không đi hết đường ấy sẽ xanh y như cũ trong khi đường vẫn đứt.

Mặc định bộ này KHÔNG gọi mô hình một lần nào: `edit`, `undo`, `snapshot`, `branch`,
`confirm` đều được lõi giải quyết bằng mã. Nên nó chạy miễn phí và chạy lại được bao nhiêu
lần cũng được.

Ngoại lệ DUY NHẤT là phần H (duyệt có sửa, DEV-370): một thẻ cổng chỉ sinh ra từ một lời
gọi công cụ THẬT của tác tử, nên phần ấy phải tốn một lượt mô hình. Nó nằm sau một cờ
riêng và mặc định bị bỏ qua:

    EIDE_FEATURE_CONG_CO_DIFF=1 EIDE_FEATURE_DUYET_CO_SUA=1 EIDE_E2E_MO_HINH=1 \
        python tools/thu_nut_lui.py
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien, PathsThu           # noqa: E402

EX = {"summary": "dựng dữ liệu cho bộ đo", "why": "để người có cái mà sửa, mà lùi",
      "sources": [], "diff_prev": "bản đầu", "next": "—", "confidence": "VANG"}


def _kho(du_an: pathlib.Path):
    """Kho hiện vật DÙNG CHUNG với app (xem `PathsThu`). Sổ cái thì không — một dự án một
    tiến trình là ranh giới thiết kế."""
    from eide.store import Store

    return Store(PathsThu(du_an).store_db)


def _ghi_req(du_an: pathlib.Path, ma: str, text: str) -> None:
    k = _kho(du_an)
    k.apply(artefact_id=ma, type="req", op="update" if k.get(ma) else "create",
            author="agent:bo-do", canonical={"text": text}, explain=EX)


def _ghi_build(du_an: pathlib.Path, thuong_nguon: list[str]) -> None:
    """Một hiện vật `build` dựng TỪ các hiện vật kia — để sửa thượng nguồn thì nó lỗi thời."""
    _kho(du_an).apply(artefact_id="build:firmware", type="build", op="create",
                      author="agent:bo-do", explain=EX,
                      canonical={"dat": True, "flash": 1234},
                      deps={"upstream": thuong_nguon})


def _stale(du_an: pathlib.Path, ma: str) -> bool | None:
    a = _kho(du_an).get(ma)
    return None if a is None else bool(a["stale"])


def _canon(du_an: pathlib.Path, ma: str) -> dict:
    a = _kho(du_an).get(ma)
    return {} if a is None else dict(a["canonical"])


def _doc_req(du_an: pathlib.Path, ma: str) -> str:
    a = _kho(du_an).get(ma)
    return "" if a is None else str(a["canonical"].get("text", ""))


def _ver(du_an: pathlib.Path, ma: str) -> str:
    a = _kho(du_an).get(ma)
    return f"v{a['version']}" if a else "v1"


def _mo_app(g, lan: int = 3, giay: float = 60) -> None:
    """Mở app và đợi kênh kiểm thử bật. Đóng hẳn rồi mở lại nếu nó không bật.

    **Đo được 12/10/2026, và nó là một cái bẫy của bộ đo chứ không phải của sản phẩm:**
    lần chạy ĐẦU TIÊN sau `./dong-goi.sh` thường treo ở đây, lần thứ hai thì kênh mở sau
    5 giây. `dong-goi.sh` làm `rm -rf EIDE.app` rồi dựng lại **trong lúc bản cũ đang
    chạy** — LaunchServices còn giữ gói cũ, nên `open` rơi vào một trạng thái nửa vời.

    Nên: đóng hẳn và đợi LaunchServices quên bản cũ TRƯỚC khi mở, rồi mới đếm giờ. Đợi lâu
    hơn không chữa được — đã thử 90 giây, vẫn treo; mở lại thì xong ngay.

    Và đừng báo *"app có đang chạy không?"* sau một phút im lặng: app chạy bình thường,
    chỉ bộ đo hết kiên nhẫn trước sản phẩm. Một bộ đo như thế nói sai về sản phẩm.
    """
    for i in range(lan):
        subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
        time.sleep(3)
        # Chạy THẲNG tệp thực thi, không qua `open`.
        #
        # `open` đưa việc mở cho LaunchServices, và LaunchServices **không mang theo biến
        # môi trường** của tiến trình gọi nó. Bộ đo này cần bật một cờ tính năng rồi mở
        # lại app để đo cả hai chế độ — qua `open` thì cờ không tới được lõi, và phép đo
        # "cờ bật thì sao" lặng lẽ đo lại đúng chế độ cờ tắt.
        subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                         env=dict(os.environ),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            g.san_sang(giay)
            return
        except TimeoutError:
            if i == lan - 1:
                raise
            print(f"  (kênh chưa bật sau {giay:.0f}s — đóng hẳn rồi mở lại, lần {i + 2})")


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)

    _mo_app(g)
    print("Kênh kiểm thử giao diện đã mở")

    # ---------------------------------------------------------------- A
    b.phan("A · NGƯỜI SỬA MỘT Ô, VÀ CÓ MỘT ĐƯỜNG LÙI NGAY TẠI ĐÓ")

    _ghi_req(du_an, "FR-01", "≥ 1 MB/s")
    g.ve_lai()
    g.mo_tab("requirements")
    a = g.chup("truoc-khi-sua")
    b.kiem("Tab Yêu cầu hiện hiện vật để sửa",
           any(k["code"].startswith("A2") for k in a["khoi_tren_tab"]),
           " · ".join(k["code"] for k in a["khoi_tren_tab"]))

    # Đúng thông điệp mà ô sửa trong bảng gửi (`OSuaDuoc.actLuu`), kèm mã phiên sửa.
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
            "data": {"base_version": _ver(du_an, "FR-01"),
                     "fields": {"text": "≥ 5 MB/s"},
                     "summary": "sửa text của FR-01", "session_id": "es-do-1"},
            "note": "phim 4K nên cần hơn",
            "origin": {"surface": "requirements", "block": "A2.1", "row": "FR-01"}})
    a = g.doi_xong()
    lui = a.get("lui") or {}

    b.kiem("Kho nhận bản của người", _doc_req(du_an, "FR-01") == "≥ 5 MB/s",
           _doc_req(du_an, "FR-01"))
    toast = lui.get("toast") or {}
    b.kiem("Thanh “Đã ghi … · Hoàn tác” hiện ra sau khi lưu", bool(toast),
           json.dumps(toast, ensure_ascii=False))
    b.kiem("Thanh ấy còn hiệu lực (trong 30 giây)", toast.get("con_hieu_luc") is True,
           str(toast.get("con_hieu_luc")))
    b.kiem("Nút Hoàn tác trỏ vào CẢ LƯỢT SỬA, không riêng changeset cuối",
           toast.get("target") == "session:es-do-1", str(toast.get("target")))
    b.kiem("Lõi đếm được lượt này có thay đổi", (lui.get("luot_so_thay_doi") or 0) >= 1,
           f"{lui.get('luot_so_thay_doi')} thay đổi")
    b.kiem("Nút “Lùi cả lượt” sáng vì lượt có thay đổi",
           "Lùi cả lượt" in (lui.get("luot_nut") or []),
           " · ".join(lui.get("luot_nut") or []) or "không nút nào")

    g.mo_tab("history")
    a = g.chup("a11-sau-khi-sua")
    cs = [k for k in a["khoi_tren_tab"] if k["code"] == "A11.1"]
    b.kiem("Tab Lịch sử hiện changeset của người", bool(cs) and cs[0]["so_muc"] >= 1,
           cs[0]["summary"] if cs else "không có khối A11.1")

    b.buoc("Bấm Hoàn tác trên thanh ấy")
    g._gui({"ui": "lui", "viec": "toast"})
    r = g._doi("da_lui", 20)
    b.kiem("Cái bấm đi vào lõi", r.get("da_gui") is True, json.dumps(r, ensure_ascii=False))
    g.doi_xong()
    b.kiem("Kho QUAY VỀ bản trước khi người sửa", _doc_req(du_an, "FR-01") == "≥ 1 MB/s",
           _doc_req(du_an, "FR-01"))

    # ---------------------------------------------------------------- B
    b.phan("B · GHI BẢN ƯNG Ý TỪ THANH TRẠNG THÁI")

    b.buoc("Tên rỗng — không được gửi gì cả")
    g._gui({"ui": "lui", "viec": "ghi_ban", "ten": "   "})
    r = g._doi("da_lui", 20)
    b.kiem("Tên rỗng thì giao diện KHÔNG gửi HumanAct nào", r.get("da_gui") is False,
           json.dumps(r, ensure_ascii=False))

    b.buoc("Tên thật")
    g._gui({"ui": "lui", "viec": "ghi_ban", "ten": "mốc đo nút lùi",
            "ghi_chu": "do bộ thu_nut_lui ghi"})
    g._doi("da_lui", 20)
    a = g.doi_xong()
    ds = ((a.get("lui") or {}).get("ban_ung_y")) or []
    b.kiem("Bản ưng ý mới có trong danh sách giao diện nhận được",
           "mốc đo nút lùi" in ds, " · ".join(ds) or "danh sách rỗng")
    # Ô trên THANH TRẠNG THÁI, không phải danh sách trong menu: nó đọc một đường khác
    # (`status_bar`), và đường ấy từng đọc nhầm kho hiện vật nên ô trống suốt.
    b.kiem("Ô “Bản ưng ý” trên thanh trạng thái nói đúng tên bản vừa ghi",
           a["trang_thai"].get("ban_ung_y") == "mốc đo nút lùi",
           repr(a["trang_thai"].get("ban_ung_y")))

    # ---------------------------------------------------------------- C
    b.phan("C · VỀ BẢN ƯNG Ý, CÓ XEM TRƯỚC SẼ MẤT GÌ")

    _ghi_req(du_an, "FR-02", "sinh ra SAU bản ưng ý")
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-01"},
            "data": {"base_version": _ver(du_an, "FR-01"),
                     "fields": {"text": "≥ 9 MB/s"},
                     "summary": "sửa text của FR-01", "session_id": "es-do-2"},
            "note": "thử một hướng khác",
            "origin": {"surface": "requirements", "block": "A2.1", "row": "FR-01"}})
    g.doi_xong()

    ds_snap = _ban_ung_y(du_an)
    snap = next((s["id"] for s in ds_snap if s["name"] == "mốc đo nút lùi"), None)
    b.kiem("Tìm được mã bản ưng ý vừa ghi", snap is not None,
           json.dumps(ds_snap, ensure_ascii=False))
    assert snap

    g._gui({"ui": "lui", "viec": "xem_truoc", "snapshot": snap})
    r = g._doi("xem_truoc_khoi_phuc", 25)
    b.kiem("Phép xem trước trả lời được (máy–máy, 0 token)", r.get("ok") is True,
           json.dumps(r, ensure_ascii=False)[:200])
    b.kiem("Nó NÓI RA sẽ mất gì trước khi hỏi", bool(r.get("se_mat_vi")),
           " · ".join(r.get("se_mat_vi") or []))
    b.kiem("Nó biết có sửa của người chưa nằm trong bản ưng ý nào",
           r.get("co_sua_cua_nguoi") is True, str(r.get("co_sua_cua_nguoi")))

    b.buoc("Về bản ấy, giữ bản hiện tại lại thành một bản có tên")
    g._gui({"ui": "lui", "viec": "ve_ban", "snapshot": snap, "giu": "hướng đã thử"})
    g._doi("da_lui", 20)
    a = g.doi_xong()
    b.kiem("Kho về đúng trạng thái lúc ghi bản ưng ý",
           _doc_req(du_an, "FR-01") == "≥ 1 MB/s", _doc_req(du_an, "FR-01"))
    b.kiem("Hiện vật sinh SAU bản ưng ý bị gỡ", _doc_req(du_an, "FR-02") == "",
           _doc_req(du_an, "FR-02") or "(đã gỡ)")
    ds = ((a.get("lui") or {}).get("ban_ung_y")) or []
    b.kiem("Bản đang bỏ lại được giữ, không mất", "hướng đã thử" in ds,
           " · ".join(ds))
    b.kiem("Bản ưng ý vừa khôi phục vẫn còn trong danh sách", "mốc đo nút lùi" in ds,
           " · ".join(ds))

    # ---------------------------------------------------------------- D
    b.phan("D · NHÁNH")

    g._gui({"ui": "lui", "viec": "nhanh", "action": "create", "ten": "thu-nut-lui"})
    g._doi("da_lui", 20)
    a = g.doi_xong()
    lui = a.get("lui") or {}
    b.kiem("Giao diện biết đang đứng ở nhánh mới",
           lui.get("nhanh_hien_tai") == "thu-nut-lui", str(lui.get("nhanh_hien_tai")))
    b.kiem("Danh sách nhánh do LÕI cấp (giao diện không chạy git)",
           "thu-nut-lui" in (lui.get("nhanh") or []) and len(lui.get("nhanh") or []) >= 2,
           " · ".join(lui.get("nhanh") or []))

    g._gui({"ui": "lui", "viec": "nhanh", "action": "switch", "ten": "main"})
    g._doi("da_lui", 20)
    a = g.doi_xong()
    b.kiem("Chuyển về nhánh cũ được",
           ((a.get("lui") or {}).get("nhanh_hien_tai")) == "main",
           str((a.get("lui") or {}).get("nhanh_hien_tai")))

    # ---------------------------------------------------------------- E
    b.phan("E · HAI BẢN ĐỤNG NHAU: NGƯỜI THẤY DIFF, SỬA CỘT PHẢI, RỒI CHỌN (DEV-366)")

    tep = du_an / "main.c"
    tep.write_text("int main(void){return 0;}\n", "utf-8")
    g.mo_tab("code")
    # Người mở tệp ở một bản cũ rồi lưu — đúng tình huống tác tử đã sửa trong lúc họ gõ.
    g._gui({"kind": "edit", "target": {"type": "file", "id": "main.c"},
            "data": {"base_version": "ban-cu-khong-con-nua",
                     "content": "int main(void){return 42;}\n"},
            "note": "tôi sửa trong lúc tác tử cũng sửa",
            "origin": {"surface": "code"}})
    a = g.doi_xong()

    the = [t for t in a["the_dang_cho"] if t["loai"] == "clarify"]
    b.kiem("Giao diện hiện thẻ xung đột", bool(the),
           the[0]["tieu_de"] if the else "không thẻ nào")
    ds = a.get("diff") or []
    b.kiem("Khối diff tới được giao diện (lệnh thứ 17)", len(ds) == 1,
           json.dumps(ds, ensure_ascii=False)[:200])
    assert ds and the
    b.kiem("Diff gắn đúng vào thẻ xung đột ấy", ds[0]["gan_voi"] == the[0]["card_id"],
           f"{ds[0]['gan_voi']} ↔ {the[0]['card_id']}")
    b.kiem("Diff có nội dung thật, không phải một cái khung rỗng",
           ds[0]["so_hunk"] >= 1 and ds[0]["so_dong_trai"] >= 1,
           f"{ds[0]['so_hunk']} đoạn · trái {ds[0]['so_dong_trai']} dòng "
           f"· phải {ds[0]['so_dong_phai']} dòng")
    b.kiem("Cột phải sửa được — lựa chọn thứ ba của thẻ cần một chỗ để sửa",
           ds[0]["cho_phep_sua"] is True, str(ds[0]["cho_phep_sua"]))

    # Ảnh chụp LÚC THẺ CÒN MỞ: phần duy nhất của khối diff mà bản chụp trạng thái không
    # thấy là **nó vẽ ra trông thế nào**. Hai cột có thẳng hàng không, màu có đúng chỗ
    # không, chữ có bị cắt không — mấy câu ấy chỉ có mắt người trả lời được.
    g.chup_man_hinh(REPO / "du-lieu" / "ket-qua" / "anh" / "the-xung-dot.png",
                    nhan="the-xung-dot")

    b.buoc("Sửa cột phải rồi bấm “Dùng bản tôi vừa sửa trong diff”")
    da_sua = "int main(void){return 7;}\n"
    g._gui({"ui": "giai_xung_dot", "card_id": the[0]["card_id"],
            "chon": "Dùng bản tôi vừa sửa trong diff", "ban_da_sua": da_sua})
    r = g._doi("da_giai_xung_dot", 25)
    b.kiem("Cái bấm đi vào lõi", r.get("card_id") == the[0]["card_id"],
           json.dumps(r, ensure_ascii=False))
    g.doi_xong()
    b.kiem("Đúng nội dung người gõ nằm trên đĩa", tep.read_text("utf-8") == da_sua,
           repr(tep.read_text("utf-8")))

    a = g.chup("sau-giai-xung-dot")
    b.kiem("Thẻ xung đột đã đóng, không còn nút bấm được",
           not [t for t in a["the_dang_cho"] if t["card_id"] == the[0]["card_id"]],
           f"{len(a['the_dang_cho'])} thẻ còn chờ")
    toast = (a.get("lui") or {}).get("toast") or {}
    b.kiem("Lần ghi ấy hoàn tác được như mọi thay đổi khác",
           bool(toast) and toast.get("con_hieu_luc") is True,
           json.dumps(toast, ensure_ascii=False))

    # ---------------------------------------------------------------- G
    b.phan("G · SỬA SÂU TRONG HIỆN VẬT, BÁC BỎ, XÁC NHẬN FACT (DEV-368)")

    _ghi_tieu_chi(du_an)
    g.ve_lai()
    g.mo_tab("simulation")
    a = g.chup("a8-tieu-chi")
    kh = [k for k in a["khoi_tren_tab"] if k.get("sua_duoc_loai")]
    b.kiem("Khối tiêu chí KHAI ra ô nào sửa được (I8)",
           any(k["sua_duoc_loai"] == "criteria" for k in kh),
           " · ".join(f"{k['code']}→{k['sua_duoc_loai']}" for k in kh) or "không khối nào")
    b.kiem("Lõi khai đủ đường dẫn LỒNG, không phải tên trường cấp một",
           any("assert/{row}/nguong" in (k.get("sua_duoc_duong") or []) for k in kh),
           str([k.get("sua_duoc_duong") for k in kh]))

    # HAI CHẾ ĐỘ, vì `EIDE_FEATURE_SUA_LONG` là một cờ và một cờ chỉ có nghĩa khi đo
    # được cả hai phía. Chạy bộ này HAI LẦN, đúng cách dự án đo cờ:
    #
    #   python tools/thu_nut_lui.py                        # cờ tắt
    #   EIDE_FEATURE_SUA_LONG=1 python tools/thu_nut_lui.py  # cờ bật
    #
    # Cố ý KHÔNG bật cờ rồi mở lại app giữa chừng: đã thử và nó làm kho hiện vật của dự
    # án đo về trạng thái bản ưng ý — một hiệu ứng phụ của bộ đo, không phải của sản
    # phẩm, nhưng nó làm mọi con số sau đó nói về một cái kho khác.
    bat_co = (os.environ.get("EIDE_FEATURE_SUA_LONG") or "").strip() in ("1", "true")
    b.buoc(f"Sửa ngưỡng của assert thứ HAI — cờ đang {'BẬT' if bat_co else 'TẮT'}")
    _patch_a2(g)
    a = g.doi_xong()
    assertx = _tieu_chi(du_an)
    if bat_co:
        b.kiem("Cờ bật: phần tử thứ hai nhận giá trị mới", assertx[1]["nguong"] == 42,
               str(assertx[1]))
        b.kiem("Cờ bật: phần tử thứ nhất KHÔNG bị đụng tới", assertx[0]["nguong"] == 3.3,
               str(assertx[0]))
    else:
        b.kiem("Cờ tắt: kho KHÔNG đổi", assertx[1]["nguong"] == 10, str(assertx[1]))
        b.kiem("Cờ tắt: lõi nói ra TÊN CỜ, không im lặng bỏ qua",
               any("SUA_LONG" in (t.get("chu") or "") for t in a.get("thong_bao") or []),
               json.dumps(a.get("thong_bao") or [], ensure_ascii=False)[:150])

    b.buoc("Xác nhận một Fact tầng BẠC — đường BẠC→VÀNG chỉ người đi được")
    _ghi_fact(du_an)
    g.ve_lai()
    g._gui({"kind": "confirm", "target": {"type": "fact", "id": "f-do-1"},
            "data": {"verdict": "dung"},
            "note": "tôi tra datasheet trang 12, đúng là 3,6 V",
            "origin": {"surface": "knowledge", "block": "A4.2", "row": "f-do-1"}})
    g.doi_xong()
    b.kiem("Fact lên tầng VÀNG", _tang_fact(du_an, "f-do-1") == "VANG",
           _tang_fact(du_an, "f-do-1"))

    b.buoc("Bác bỏ một phát hiện — ghi vào EIDE.md §Đừng")
    _ghi_phat_hien(du_an)
    g.ve_lai()
    g._gui({"kind": "edit", "target": {"type": "analysis", "id": "PT-do-1"},
            "data": {"base_version": "", "bac_bo": True, "summary": "bác bỏ PT-do-1"},
            "note": "đây là ISR, trình liên kết gọi qua bảng vector",
            "origin": {"surface": "code"}})
    g.doi_xong()
    md = (du_an / "EIDE.md").read_text("utf-8")
    muc_dung = md.split("## Đừng", 1)[-1].split("\n## ", 1)[0]
    b.kiem("Lý do nằm trong MỤC §Đừng của EIDE.md", "bảng vector" in muc_dung,
           muc_dung.strip()[:120])

    # ---------------------------------------------------------------- H
    b.phan("H · DUYỆT VỚI BẢN ĐÃ SỬA (DEV-370)")

    # Cần cờ `CONG_CO_DIFF` để cổng có diff, và `DUYET_CO_SUA` để cột phải sửa được.
    # Chạy phần này khi cả hai bật; không thì nói rõ là đã bỏ qua, đừng im lặng.
    #
    # Phần H là phần DUY NHẤT của bộ này gọi mô hình, và nó phải gọi: một thẻ cổng chỉ
    # sinh ra từ một lời gọi công cụ THẬT của tác tử. Dựng một thẻ giả để bấm là đo cái
    # nút trên một thứ không phải thẻ cổng.
    #
    # Nên nó nằm sau một cờ riêng: `EIDE_E2E_MO_HINH=1`. Mặc định cả bộ vẫn chạy miễn phí.
    if not (os.environ.get("EIDE_FEATURE_CONG_CO_DIFF")
            and os.environ.get("EIDE_FEATURE_DUYET_CO_SUA")
            and os.environ.get("EIDE_E2E_MO_HINH")):
        print("  (bỏ qua phần H — cần EIDE_FEATURE_CONG_CO_DIFF=1 "
              "EIDE_FEATURE_DUYET_CO_SUA=1 EIDE_E2E_MO_HINH=1; phần này TỐN TIỀN mô hình)")
    else:
        # Mức tự chủ A3 không dựng cổng cho `fs.write`. Hạ xuống A1 bằng đúng đường người
        # đi (`HumanAct kind=set`), không sửa cấu hình sau lưng app.
        g._gui({"kind": "set", "data": {"key": "autonomy", "value": "A1"},
                "origin": {"surface": "settings"}})
        time.sleep(2)
        b.buoc("Tác tử xin ghi Makefile; người sửa một cờ dịch rồi duyệt")
        g.go("viết cho tôi một Makefile tối giản dịch main.c, dùng -O2")
        a = g.doi_xong()
        cong = [t for t in a["the_dang_cho"] if t["loai"] == "gate"]
        b.kiem("Thẻ cổng G-FILE hiện ra", bool(cong),
               cong[0]["tieu_de"] if cong else "không thẻ nào")
        ds = [d for d in (a.get("diff") or []) if d["gan_voi"] == (cong[0]["gate_id"]
                                                                  if cong else "")]
        b.kiem("Thẻ cổng kèm khối diff: ghi đè CÁI GÌ lên cái gì", bool(ds),
               json.dumps(a.get("diff") or [], ensure_ascii=False)[:160])
        b.kiem("Cột phải SỬA ĐƯỢC vì cờ duyệt-có-sửa đang bật",
               bool(ds) and ds[0]["cho_phep_sua"] is True,
               str(ds[0]["cho_phep_sua"]) if ds else "—")
        assert cong and ds

        ban_toi = "CFLAGS = -Og -g -Wall\nall:\n\t$(CC) $(CFLAGS) -o main main.c\n"
        g._gui({"kind": "decide",
                "data": {"gate_id": cong[0]["gate_id"], "approved": True,
                         "choice": "Duyệt với bản đã sửa",
                         "amended": {"content": ban_toi}},
                "note": "cờ -O2 làm mất thông tin gỡ lỗi", "origin": {"surface": "console"}})
        g.doi_xong()

        tep = du_an / "Makefile"
        b.kiem("Trên đĩa là BẢN CỦA NGƯỜI, không phải bản tác tử",
               tep.exists() and tep.read_text("utf-8") == ban_toi,
               repr(tep.read_text("utf-8")[:60]) if tep.exists() else "chưa có tệp")
        cs = _changeset_cham(du_an, "Makefile")
        b.kiem("Hai changeset riêng, tác tử trước rồi tới anh",
               [c["author"].split(":")[0] for c in cs] == ["agent", "human"],
               " → ".join(c["author"] for c in cs) or "không có changeset nào")

    # ---------------------------------------------------------------- I
    b.phan("I · TRÌNH SOẠN TỆP TRONG APP, VÀ KHOÁ MỀM HAI CHIỀU (DEV-367)")

    tep = du_an / "sua-trong-app.c"
    tep.write_text("int f(void){return 0;}\n", "utf-8")
    g.mo_tab("code")
    g._gui({"ui": "tep", "viec": "mo", "tep": "sua-trong-app.c"})
    r = g._doi("da_mo_tep", 25)
    b.kiem("Mở được tệp trong app (nội dung tới từ LÕI, qua hộp cát)",
           r.get("ok") is True and r.get("so_ky_tu", 0) > 0,
           json.dumps(r, ensure_ascii=False)[:140])
    b.kiem("Lõi cho hash để lưu còn gộp ba chiều được", bool(r.get("hash")),
           str(r.get("hash"))[:16])

    # (Khoá mềm chiều người → tác tử đo ở `tests/test_edit47_sua_tep.py`: nó cần một lời
    # gọi công cụ thật của tác tử, tức một lượt mô hình. Không dựng một phép kiểm luôn
    # xanh ở đây để lấp chỗ — một ô xanh không thể đỏ thì không nói gì cả.)

    g._gui({"ui": "tep", "viec": "luu", "tep": "sua-trong-app.c",
            "hash": r.get("hash", ""), "noi_dung": "int f(void){return 42;}\n",
            "vi_sao": "tôi sửa thẳng trong EIDE"})
    g._doi("da_luu_tep", 20)
    g.doi_xong()
    b.kiem("Nội dung người gõ nằm trên đĩa",
           tep.read_text("utf-8") == "int f(void){return 42;}\n",
           repr(tep.read_text("utf-8")))
    cs = _changeset_cham(du_an, "sua-trong-app.c")
    b.kiem("Lần lưu ấy là một changeset của NGƯỜI, hoàn tác được",
           bool(cs) and cs[-1]["author"] == "human" and cs[-1]["reversible"],
           " → ".join(c["author"] for c in cs) or "không có changeset nào")

    g._gui({"ui": "tep", "viec": "dong", "tep": "sua-trong-app.c"})
    g._doi("da_dong_tep", 20)

    b.buoc("Mở EIDE.md — nó sửa được, nhưng lưu đi một đường khác")
    g._gui({"ui": "tep", "viec": "mo", "tep": "EIDE.md"})
    r = g._doi("da_mo_tep", 25)
    b.kiem("App biết đây là EIDE.md (lưu phải đi qua cửa bộ nhớ)",
           r.get("la_eide_md") is True, str(r.get("la_eide_md")))
    g._gui({"ui": "tep", "viec": "dong", "tep": "EIDE.md"})
    g._doi("da_dong_tep", 20)

    # ---------------------------------------------------------------- K
    b.phan("K · SỬA TỆP BÊN NGOÀI APP, NHƯ KỸ SƯ NHÚNG LÀM THẬT (DEV-369)")

    # Đây là phần duy nhất của bộ này KHÔNG đi qua kênh kiểm thử để gây ra thay đổi: nó
    # ghi thẳng vào đĩa, đúng như VS Code làm. Thứ phải đo là *app có tự biết hay không*.
    #
    # Cũng là cờ, nên cũng phải đo được cả hai phía:
    #   python tools/thu_nut_lui.py                           # cờ tắt
    #   EIDE_FEATURE_WATCHER=1 python tools/thu_nut_lui.py    # cờ bật
    bat_wt = (os.environ.get("EIDE_FEATURE_WATCHER") or "").strip() in ("1", "true")
    ngoai = du_an / "sua-bang-vscode.c"
    V1, V2 = "int g(void){return 1;}\n", "int g(void){return 42;}\n"

    b.buoc(f"Tạo tệp mới bằng tay, không qua app — cờ đang {'BẬT' if bat_wt else 'TẮT'}")
    ngoai.write_text(V1, "utf-8")
    # Cờ tắt thì không có gì để đợi — nhưng vẫn phải đợi QUÁ một nhịp quét cộng thời gian
    # gộp, không thì "không thấy gì" chỉ nghĩa là đo quá sớm.
    cs = _doi_changeset(du_an, "sua-bang-vscode.c", 1, giay=25 if bat_wt else 8)

    if not bat_wt:
        b.kiem("Cờ tắt: app KHÔNG theo dõi thư mục (không changeset nào)", not cs,
               f"{len(cs)} changeset")
        b.kiem("Cờ tắt: tệp vẫn y nguyên trên đĩa (không ai đụng vào)",
               ngoai.read_text("utf-8") == V1, repr(ngoai.read_text("utf-8")))
    else:
        b.kiem("App tự bắt được tệp mới, thành changeset của NGƯỜI",
               bool(cs) and cs[-1]["author"] == "human", f"{len(cs)} changeset")

        # Lần sửa THỨ HAI mới là lần đo được đường hoàn tác về nội dung: lần đầu là tệp
        # mới, hoàn tác nó nghĩa là xoá tệp đi, không phải trả về bản cũ.
        b.buoc("Sửa lại tệp ấy lần nữa, vẫn bằng tay")
        ngoai.write_text(V2, "utf-8")
        cs = _doi_changeset(du_an, "sua-bang-vscode.c", 2)
        b.kiem("Hai lần sửa là HAI changeset, không gộp vào nhau", len(cs) >= 2,
               f"{len(cs)} changeset")
        b.kiem("Changeset ấy hoàn tác được",
               bool(cs) and cs[-1]["reversible"] is True,
               str(cs[-1].get("reversible")) if cs else "—")
        md = (du_an / "EIDE.md").read_text("utf-8")
        b.kiem("Tác tử BIẾT: EIDE.md §Người vừa sửa có tên tệp",
               "sua-bang-vscode.c" in md,
               md.split("## Người vừa sửa", 1)[-1].strip()[:110])

        b.buoc("Bấm Hoàn tác trên chính changeset ấy, trong app")
        g.ve_lai()
        g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs[-1]["id"]},
                "data": {"mode": "revert"}, "origin": {"surface": "history"}})
        g.doi_xong()
        b.kiem("Nội dung cũ trở lại trên ĐĨA — luật nền số 3 đúng cả với tệp người gõ "
               "bên ngoài app",
               ngoai.read_text("utf-8") == V1, repr(ngoai.read_text("utf-8")))

        b.buoc("XOÁ hẳn tệp ấy bằng tay (như xoá trong Finder) — DEV-375")
        # Đếm MỐC NGAY TRƯỚC khi xoá, không dùng số đếm từ trước lần hoàn tác: chính lần
        # hoàn tác vừa rồi cũng sinh một changeset chạm tệp này, nên `len(cs) + 1` đã
        # thoả ngay lập tức và phép đo trả về trước khi watcher kịp quét. Một lần chờ
        # thoả sai thì nó không chờ gì cả.
        truoc_xoa = len(_changeset_cham(du_an, "sua-bang-vscode.c"))
        ngoai.unlink()
        cs = _doi_changeset(du_an, "sua-bang-vscode.c", truoc_xoa + 1)
        b.kiem("App bắt được cả lần XOÁ, thành changeset hoàn tác được",
               bool(cs) and cs[-1]["author"] == "human" and cs[-1]["reversible"]
               and any(f.get("op") == "delete" for f in cs[-1].get("forward") or []),
               f"{len(cs)} changeset · " + " → ".join(
                   f"{c['author']}/{'xoá' if any(f.get('op') == 'delete' for f in c.get('forward') or []) else 'sửa'}"
                   for c in cs))
        md = (du_an / "EIDE.md").read_text("utf-8")
        b.kiem("Tác tử biết đây là XOÁ, không phải sửa", "XOÁ bên ngoài EIDE" in md,
               md.split("## Người vừa sửa", 1)[-1].strip()[:110])

        b.buoc("Bấm Hoàn tác — tệp phải trở lại trên đĩa")
        g.ve_lai()
        g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs[-1]["id"]},
                "data": {"mode": "revert"}, "origin": {"surface": "history"}})
        g.doi_xong()
        b.kiem("Tệp đã xoá TRỞ LẠI, đúng nội dung cũ",
               ngoai.exists() and ngoai.read_text("utf-8") == V1,
               repr(ngoai.read_text("utf-8")) if ngoai.exists() else "tệp vẫn mất")

        b.buoc("Xoá CẢ MỘT THƯ MỤC ba tệp — một cú bấm, phải là một changeset (DEV-376)")
        tm = du_an / "firmware"
        tm.mkdir(exist_ok=True)
        ba = {f"firmware/{t}": f"// {t}\n" for t in ("main.c", "uart.c", "led.c")}
        for t, n in ba.items():
            (du_an / t).write_text(n, "utf-8")
        _doi_changeset(du_an, "firmware/main.c", 1)
        truoc_xoa = len(_changeset_cham(du_an, "firmware/main.c"))
        shutil.rmtree(tm)
        cs = _doi_changeset(du_an, "firmware/main.c", truoc_xoa + 1)
        b.kiem("Ba tệp mất đi là MỘT changeset, không phải ba",
               bool(cs) and len(cs) == truoc_xoa + 1
               and len([t for t in cs[-1].get("touches") or []]) == 3,
               f"{len(cs)} changeset · chạm {len(cs[-1].get('touches') or []) if cs else 0} tệp")

        b.buoc("Một lần Hoàn tác phải trả CẢ BA về")
        g.ve_lai()
        g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs[-1]["id"]},
                "data": {"mode": "revert"}, "origin": {"surface": "history"}})
        g.doi_xong()
        thieu = [t for t, n in ba.items()
                 if not (du_an / t).exists() or (du_an / t).read_text("utf-8") != n]
        b.kiem("Cả ba tệp trở lại sau MỘT cú bấm", not thieu,
               "thiếu: " + ", ".join(thieu) if thieu else "đủ ba")

    # ---------------------------------------------------------------- L
    b.phan("L · BẬT MỘT CỜ TÍNH NĂNG TỪ TRONG APP (DEV-371)")

    g.mo_tab("project")
    g.ve_lai()
    a = g.chup("a14-cai-dat")
    kh = {k["code"]: k for k in a["khoi_tren_tab"]}
    b.kiem("Tab A14 có khối Cài đặt dự án", "A14.7" in kh,
           " · ".join(sorted(kh)) or "không khối nào")
    cd = kh.get("A14.7", {})
    b.kiem("Khối ấy khai gửi bằng `set`, không phải `edit` (một cờ không là hiện vật)",
           cd.get("sua_duoc_gui_bang") == "set", str(cd.get("sua_duoc_gui_bang")))
    b.kiem("App VẼ ĐƯỢC khối ấy (không rơi vào nhánh “chưa biết vẽ”)",
           cd.get("ve_duoc") is True and "kv" not in (a.get("khoi_chua_biet_ve") or []),
           f"ve_duoc={cd.get('ve_duoc')} · chưa biết vẽ: {a.get('khoi_chua_biet_ve')}")
    cap = {c[0]: (c[1] if len(c) > 1 else "") for c in cd.get("cap_kv") or []}
    b.kiem("Mười chín cờ đều có mặt, và `pdf_bang` đang TẮT",
           len(cap) >= 19 and cap.get("pdf_bang") == "không",
           f"{len(cap)} cờ · pdf_bang={cap.get('pdf_bang')}")

    b.buoc("Bấm công tắc `pdf_bang` — đúng thông điệp mà `CongTac` gửi")
    g._gui({"kind": "set", "data": {"key": "feature.pdf_bang", "value": True},
            "origin": {"surface": "project", "block": "A14.7", "row": "pdf_bang"}})
    g.doi_xong()
    tep = du_an / ".eide" / "settings.json"
    d = json.loads(tep.read_text("utf-8")) if tep.exists() else {}
    b.kiem("Cờ nằm trong `.eide/settings.json` của DỰ ÁN (sống qua lần tắt app)",
           (d.get("features") or {}).get("pdf_bang") is True,
           json.dumps(d, ensure_ascii=False)[:120] if d else "không có tệp")
    g.ve_lai()
    a = g.chup("a14-sau-khi-bat")
    b.kiem("Lõi nói lại BẬT cái gì và cái giá của nó",
           any("pdf_bang" in (t.get("chu") or "") and "4,3" in (t.get("chu") or "")
               for t in a.get("thong_bao") or []),
           json.dumps(a.get("thong_bao") or [], ensure_ascii=False)[:170])
    cd = {k["code"]: k for k in a["khoi_tren_tab"]}.get("A14.7", {})
    cap = {c[0]: (c[1] if len(c) > 1 else "") for c in cd.get("cap_kv") or []}
    b.kiem("Bảng vẽ lại nói đúng trạng thái mới", cap.get("pdf_bang") == "có",
           f"pdf_bang={cap.get('pdf_bang')}")

    # ---------------------------------------------------------------- M
    b.phan("M · TẦNG THỨ TƯ: LÙI CẢ MỘT LƯỢT, VÀ SỔ CÁI GHI LẠI KẾT QUẢ (DEV-372)")

    # Ba tầng kia (changeset · phiên sửa · bản ưng ý) đã đi ở phần A và C. Tầng `run` thì
    # chưa phần nào chạm tới, nên chỉ số thứ tư của §7 không có số cho nó — và "chưa có số"
    # trông y hệt "có số mà xấu" trong một bảng tổng.
    _ghi_req(du_an, "FR-09", "≤ 200 ms")
    g.ve_lai()
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-09"},
            "data": {"base_version": _ver(du_an, "FR-09"), "fields": {"text": "≤ 50 ms"}},
            "origin": {"surface": "requirements"}})
    g.doi_xong()
    cs = _changeset_cham(du_an, "FR-09")
    run = cs[-1]["run_id"] if cs else ""
    b.kiem("Changeset của lần sửa ấy khai đúng mã lượt", bool(run), run or "không có")

    # Tầng MỘT trước (một changeset), rồi sửa lại để có cái mà lùi cả lượt. Làm cả hai ở
    # đây chứ không dựa vào phần K: phần ấy chỉ chạy khi cờ `WATCHER` bật, nên phép kiểm
    # "bốn tầng đều có bản ghi" sẽ đỏ ở chế độ cờ tắt — một phép đo chỉ đúng một nửa thời
    # gian thì nó nói về cấu hình, không nói về sản phẩm.
    g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs[-1]["id"]},
            "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    g.doi_xong()
    b.kiem("Lùi MỘT changeset đưa hiện vật về bản trước",
           _doc_req(du_an, "FR-09") == "≤ 200 ms", _doc_req(du_an, "FR-09"))

    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-09"},
            "data": {"base_version": _ver(du_an, "FR-09"), "fields": {"text": "≤ 20 ms"}},
            "origin": {"surface": "requirements"}})
    g.doi_xong()
    cs = _changeset_cham(du_an, "FR-09")
    run = cs[-1]["run_id"] if cs else run

    g._gui({"kind": "undo", "target": {"type": "run", "id": run},
            "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    g.doi_xong()
    b.kiem("Lùi CẢ LƯỢT đưa hiện vật về bản trước", _doc_req(du_an, "FR-09") == "≤ 200 ms",
           _doc_req(du_an, "FR-09"))

    ds = _su_kien(du_an, "undo")
    b.kiem("Sổ cái ghi KẾT QUẢ hoàn tác, kèm TẦNG — §7 chỉ số 4 đo đúng chỗ này",
           any(d.get("tang") == "run" and d.get("ok") for d in ds),
           " · ".join(f"{d.get('tang')}:{'ok' if d.get('ok') else 'hỏng'}" for d in ds)
           or "không bản ghi nào")
    b.kiem("Bốn tầng đều có bản ghi trong một phiên",
           {"changeset", "session", "snapshot", "run"} <= {d.get("tang") for d in ds},
           " · ".join(sorted({str(d.get("tang")) for d in ds})))

    # ---------------------------------------------------------------- N
    b.phan("N · HAI CÚ BẤM CHO MỘT HIỆN VẬT LỖI THỜI (DEV-373)")

    # Đo được 12/10/2026 trên sổ cái 39 dự án: 7 lần hạ nguồn bị đánh STALE rồi KHÔNG AI
    # cập nhật. Phần này đo đường đi của người tới hai việc ấy.
    _ghi_req(du_an, "FR-20", "≥ 1 MB/s")
    _ghi_build(du_an, ["FR-20"])
    g.ve_lai()
    g._gui({"kind": "edit", "target": {"type": "req", "id": "FR-20"},
            "data": {"base_version": _ver(du_an, "FR-20"), "fields": {"text": "≥ 9 MB/s"}},
            "origin": {"surface": "requirements"}})
    g.doi_xong()

    g.mo_tab("history")
    a = g.chup("a11-stale")
    k = {x["code"]: x for x in a["khoi_tren_tab"]}.get("A11.4", {})
    b.kiem("Khối STALE là một BẢNG (danh sách chuỗi thì không có chỗ đặt nút)",
           k.get("type") == "table", str(k.get("type")))
    b.kiem("App vẽ được nó và thấy hiện vật lỗi thời",
           k.get("ve_duoc") is True and k.get("so_hang", 0) >= 1,
           f"ve_duoc={k.get('ve_duoc')} · {k.get('so_hang')} dòng")
    hd = {h.get("ma"): h for h in k.get("hanh_dong") or []}
    b.kiem("Lõi KHAI hai cú bấm, và khai cái nào tốn tiền",
           set(hd) >= {"cap_nhat_tat_ca", "chap_nhan"}
           and hd["cap_nhat_tat_ca"].get("ton_token") is True
           and not hd["chap_nhan"].get("ton_token"),
           " · ".join(f"{m}{'(tốn token)' if h.get('ton_token') else ''}"
                      for m, h in hd.items()) or "không khai nút nào")
    b.kiem("Nút chấp nhận ĐÒI lý do trước khi gửi",
           hd.get("chap_nhan", {}).get("can_ly_do") is True,
           str(hd.get("chap_nhan", {}).get("can_ly_do")))

    b.buoc("Bấm “Chấp nhận STALE” — đúng thông điệp mà `NutHanhDong` gửi")
    g._gui({"kind": "edit", "target": {"type": "build", "id": "build:firmware"},
            "data": {"chap_nhan_stale": True},
            "note": "bản dựng này chỉ để đo kích thước, ngưỡng mới không đụng tới",
            "origin": {"surface": "history", "block": "A11.4", "row": "build:firmware"}})
    g.doi_xong()
    b.kiem("Băng cảnh báo tắt, nội dung hiện vật KHÔNG đổi",
           _stale(du_an, "build:firmware") is False
           and _canon(du_an, "build:firmware").get("flash") == 1234,
           f"stale={_stale(du_an, 'build:firmware')} · "
           f"{_canon(du_an, 'build:firmware')}")
    cs = _changeset_cham(du_an, "build:firmware")
    b.kiem("Là một changeset của NGƯỜI, hoàn tác được",
           bool(cs) and cs[-1]["author"] == "human" and cs[-1]["reversible"],
           " → ".join(c["author"] for c in cs) or "không changeset nào")

    b.buoc("Hoàn tác nó — cờ lỗi thời phải bật lại")
    g._gui({"kind": "undo", "target": {"type": "changeset", "id": cs[-1]["id"]},
            "data": {"mode": "revert"}, "origin": {"surface": "history"}})
    g.doi_xong()
    b.kiem("Cờ lỗi thời bật lại sau khi hoàn tác",
           _stale(du_an, "build:firmware") is True,
           f"stale={_stale(du_an, 'build:firmware')}")

    # ---------------------------------------------------------------- Đ
    b.phan("Đ · ẢNH CHỤP CHO BÁO CÁO")
    g.mo_tab("history")
    time.sleep(0.8)
    anh = g.chup_man_hinh(REPO / "du-lieu" / "ket-qua" / "anh" / "nut-lui-a11.png",
                          nhan="a11")
    b.kiem("App tự chụp được cửa sổ của nó", anh is not None and anh.exists(),
           str(anh))

    return b.tong()


def _patch_a2(g) -> None:
    """Đúng thông điệp mà `FormEditor` gửi khi người sửa ô Ngưỡng của dòng thứ hai."""
    g._gui({"kind": "edit", "target": {"type": "criteria", "id": "criteria:sim-01"},
            "data": {"base_version": "v1",
                     "patch": [{"path": "assert/1/nguong", "op": "set", "value": 42}],
                     "summary": "sửa 1 ô của A2", "session_id": "es-do-3"},
            "note": "tôi đo lại trên bo", "origin": {"surface": "simulation"}})


def _ghi_tieu_chi(du_an: pathlib.Path) -> None:
    k = _kho(du_an)
    k.apply(artefact_id="criteria:sim-01", type="criteria", op="create",
            author="agent:bo-do", explain=EX,
            canonical={"ma": "sim-01",
                       "assert": [{"ma": "A1", "mo_ta": "dòng nghỉ", "phep_so": "<=",
                                   "nguong": 3.3, "don_vi": "mA"},
                                  {"ma": "A2", "mo_ta": "thời gian khởi động",
                                   "phep_so": "<=", "nguong": 10, "don_vi": "ms"}]})


def _tieu_chi(du_an: pathlib.Path) -> list:
    return (_kho(du_an).get("criteria:sim-01") or {}).get("canonical", {}).get("assert", [])


def _ghi_fact(du_an: pathlib.Path) -> None:
    _kho(du_an).put_fact({"fact_id": "f-do-1", "subject": "chip:X", "key": "vdd.max",
                          "value": "3.6", "unit": "V", "tier": "BAC", "origin": "extract",
                          "source": {"doc": "ds.pdf", "page": 12}, "explain": EX})


def _tang_fact(du_an: pathlib.Path, fid: str) -> str:
    return next((f["tier"] for f in _kho(du_an).query_facts(limit=99)
                 if f["fact_id"] == fid), "—")


def _ghi_phat_hien(du_an: pathlib.Path) -> None:
    _kho(du_an).apply(artefact_id="PT-do-1", type="analysis", op="create",
                      author="agent:bo-do", explain=EX,
                      canonical={"vi_sao": "hàm ISR_TIM2 không ai gọi"})


def _changeset_cham(du_an: pathlib.Path, path: str) -> list[dict]:
    """Changeset chạm một tệp, theo thứ tự ghi. Đọc thẳng sổ — không dựng `History`
    (nó sẽ khởi tạo git và cấp mã, tức một tiến trình thứ hai ghi vào dự án)."""
    p = du_an / ".eide" / "changesets.jsonl"
    if not p.exists():
        return []
    ra = []
    for l in p.read_text("utf-8").splitlines():
        if not l.strip():
            continue
        d = json.loads(l)
        if any(t.get("artefact_id") == path for t in d.get("touches") or []):
            ra.append(d)
    return ra


def _doi_changeset(du_an: pathlib.Path, path: str, du: int,
                   giay: float = 25) -> list[dict]:
    """Đợi tới khi có `du` changeset chạm `path`, hoặc hết giờ.

    Watcher trong app quét mỗi 2 s và gộp sự kiện trong 1,5 s. Đợi theo ĐIỀU KIỆN chứ
    không ngủ một con số cố định: một bộ đo ngủ 6 giây rồi báo đỏ vì máy chậm 200 ms là
    một bộ đo nói sai về sản phẩm.
    """
    han = time.time() + giay
    cs: list[dict] = []
    while time.time() < han:
        cs = _changeset_cham(du_an, path)
        if len(cs) >= du:
            return cs
        time.sleep(1.0)
    return cs


def _su_kien(du_an: pathlib.Path, kind: str) -> list[dict]:
    """Phần `data` của mọi sự kiện sổ cái loại ấy. Đọc thẳng tệp, không dựng `Ledger`."""
    p = du_an / ".eide" / "ledger.jsonl"
    if not p.exists():
        return []
    ra = []
    for l in p.read_text("utf-8", errors="replace").splitlines():
        if not l.strip():
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if d.get("kind") == kind:
            ra.append(d.get("data") or {})
    return ra


def _ban_ung_y(du_an: pathlib.Path) -> list[dict]:
    """Danh sách bản ưng ý, đọc từ tệp của app. Chỉ ĐỌC — không dựng `History` (nó sẽ
    khởi tạo git và cấp mã, tức một tiến trình thứ hai ghi vào dự án)."""
    p = du_an / ".eide" / "snapshots.jsonl"
    if not p.exists():
        return []
    ra = []
    for l in p.read_text("utf-8").splitlines():
        if l.strip():
            d = json.loads(l)
            if d.get("kind") in ("named", "release"):
                ra.append({"id": d["id"], "name": d.get("name", "")})
    return ra


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Đo năm tầng lùi qua app thật")
    ap.add_argument("--du-an", default="du-lieu/thu-nut-lui")
    ap.add_argument("--giu", action="store_true")
    a = ap.parse_args(argv)

    from eide.config import load_dotenv
    load_dotenv()

    d = pathlib.Path(a.du_an).resolve()
    if d.exists() and not a.giu:
        shutil.rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    (d / "main.c").write_text("int main(void){return 0;}\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
