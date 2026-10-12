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

Bộ này KHÔNG gọi mô hình một lần nào: `edit`, `undo`, `snapshot`, `branch` đều được lõi
giải quyết bằng mã. Nên nó chạy miễn phí và chạy lại được bao nhiêu lần cũng được.
"""

from __future__ import annotations

import argparse
import json
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
        subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
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

    # ---------------------------------------------------------------- Đ
    b.phan("Đ · ẢNH CHỤP CHO BÁO CÁO")
    g.mo_tab("history")
    time.sleep(0.8)
    anh = g.chup_man_hinh(REPO / "du-lieu" / "ket-qua" / "anh" / "nut-lui-a11.png",
                          nhan="a11")
    b.kiem("App tự chụp được cửa sổ của nó", anh is not None and anh.exists(),
           str(anh))

    return b.tong()


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
