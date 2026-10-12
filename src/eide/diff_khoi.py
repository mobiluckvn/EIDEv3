# -*- coding: utf-8 -*-
"""Khối `diff` — EIDE-EDIT-47 §3.3 và §DEV-366.

Mọi chỗ EIDE đang NÓI "xem diff" đều phải có diff để xem. Rà 12/10/2026 thấy ba chỗ nói mà
không có:

* thẻ xung đột (`loop._the_xung_dot`) cho người ba lựa chọn, trong đó một lựa chọn là
  *"Để tôi xem diff rồi quyết"* — mà không có gì để xem. Hai bản được nhét vào thẻ dưới dạng
  chuỗi **cắt ở 4 000 ký tự**, hiện ra như chữ thường;
* cổng `G-FILE` nói "ghi đè bản của anh" mà không nói ghi đè CÁI GÌ;
* `history.preview_restore` nói "1 req quay về bản cũ" mà không nói quay về thành gì.

Lõi tính `hunks`, giao diện chỉ vẽ (I3). Lý do chia như vậy: `difflib` của Python và bộ dựng
diff của Swift là hai hiện thực khác nhau của cùng một thuật toán, và hai hiện thực thì có
hai hành vi ở ca biên — người sẽ thấy một diff khác với diff mà lõi dùng để quyết.

## Hợp đồng

`noi_dung` của mỗi bên được gửi **nguyên văn một lần**; `hunks` chỉ là KHOẢNG DÒNG. Nhét
từng đoạn chữ vào mỗi hunk thì một tệp 2 000 dòng đổi rải rác sẽ gửi gần hai lần nội dung.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from typing import Any

# Trần nội dung một bên. Trên ngưỡng này thì cắt, và **nói ra là đã cắt** — một diff cắt im
# lặng là thứ tệ nhất ở đây: người đọc tưởng mình đã xem hết rồi mới bấm.
TRAN_KY_TU = 200_000


def bam(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def in_canonical(canonical: dict[str, Any]) -> str:
    """Hiện vật JSON → văn bản so được.

    `sort_keys=True` là phần quan trọng: thứ tự khoá trong một `dict` Python không phải nội
    dung của hiện vật, nên để nó đổi thì diff sẽ hiện những dòng "đổi" mà chẳng có gì đổi.
    """
    return json.dumps(canonical, ensure_ascii=False, indent=2, sort_keys=True)


def dung_diff(*, loai: str, trai: str, phai: str, goc: str | None = None,
              tieu_de: str, diff_id: str,
              nhan_trai: str = "Bản của anh", nhan_phai: str = "Bản hiện tại",
              cho_phep_sua: bool = False,
              gan_voi: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dựng tham số cho lệnh `diff.show`. Thuần tính toán — không chạm đĩa, không chạm git.

    `goc` có ⇒ so BA BÊN: hunk nào mà **cả hai bên cùng đụng vào** so với gốc thì đánh
    `xung_dot`. Đây là định nghĩa của diff3, và nó trả lời đúng câu người hỏi khi nhìn thẻ
    xung đột: *chỗ nào tôi với tác tử giẫm lên nhau, chỗ nào chỉ một bên sửa.*
    """
    t, cat_t = _cat(trai)
    p, cat_p = _cat(phai)
    dt, dp = t.splitlines(), p.splitlines()
    dg = goc.splitlines() if goc is not None else None

    hunks = _hunks(dt, dp)
    if dg is not None:
        _danh_dau_xung_dot(hunks, goc=dg, trai=dt, phai=dp)

    ra: dict[str, Any] = {
        "diff_id": diff_id,
        "tieu_de": tieu_de,
        "loai": loai,
        "trai": {"nhan": nhan_trai, "noi_dung": t, "hash": bam(trai), "cat": cat_t,
                 "so_dong": len(dt)},
        "phai": {"nhan": nhan_phai, "noi_dung": p, "hash": bam(phai), "cat": cat_p,
                 "so_dong": len(dp)},
        "hunks": hunks,
        "cho_phep_sua": bool(cho_phep_sua),
        "gan_voi": gan_voi,
        "tom_tat": tom_tat(hunks),
    }
    if goc is not None:
        g, cat_g = _cat(goc)
        ra["goc"] = {"nhan": "Bản gốc chung", "noi_dung": g, "hash": bam(goc), "cat": cat_g,
                     "so_dong": len(dg or [])}
    return ra


def tom_tat(hunks: list[dict[str, Any]]) -> dict[str, int]:
    """Đếm để hiện một dòng tóm tắt mà không phải đọc cả diff."""
    return {
        "doan": len(hunks),
        "them": sum(h["so_phai"] for h in hunks if h["loai"] == "them"),
        "bot": sum(h["so_trai"] for h in hunks if h["loai"] == "xoa"),
        "doi": sum(1 for h in hunks if h["loai"] == "doi"),
        "xung_dot": sum(1 for h in hunks if h["loai"] == "xung_dot"),
    }


def diff_tom_tat(trai: str, phai: str) -> dict[str, int]:
    """Chỉ CON SỐ, không nội dung — cho danh sách nhiều tệp (xem `preview_restore`).

    Gửi toàn văn của hai mươi hiện vật vào một lần xem trước là trả giá cho thứ người chưa
    mở ra xem.
    """
    return tom_tat(_hunks(trai.splitlines(), phai.splitlines()))


# --------------------------------------------------------------------------- trong nhà
def _cat(s: str) -> tuple[str, bool]:
    if len(s) <= TRAN_KY_TU:
        return s, False
    return (s[:TRAN_KY_TU]
            + f"\n⟨CẮT Ở {TRAN_KY_TU} KÝ TỰ — bản đủ dài {len(s)} ký tự⟩\n"), True


def _hunks(dt: list[str], dp: list[str]) -> list[dict[str, Any]]:
    """Khoảng dòng khác nhau giữa hai bên. `autojunk=False` — xem chú thích.

    `SequenceMatcher` mặc định coi dòng xuất hiện trong hơn 1 % của một chuỗi dài là "rác"
    và BỎ QUA nó khi dò. Với mã nguồn thì dòng `}` hay dòng trống rơi đúng vào định nghĩa
    ấy, nên một tệp C 300 dòng sẽ ra một diff lệch hẳn so với `git diff`.
    """
    sm = difflib.SequenceMatcher(None, dt, dp, autojunk=False)
    ra: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        ra.append({
            "loai": {"replace": "doi", "insert": "them", "delete": "xoa"}[tag],
            # Số dòng người đọc đếm từ 1; chỉ số nội bộ đếm từ 0.
            "dong_trai": i1 + 1, "so_trai": i2 - i1,
            "dong_phai": j1 + 1, "so_phai": j2 - j1,
        })
    return ra


def _dong_giu_nguyen(goc: list[str], ben: list[str]) -> set[int]:
    """Chỉ số dòng CỦA BÊN mà bên ấy bê nguyên từ gốc sang — tức bên ấy không đụng vào.

    Đây là cách rẻ và chắc để trả lời "bên này có sửa chỗ đó không", mà không phải dựng
    một phép ánh xạ khoảng-dòng hai chiều. Bản đầu của chỗ này ánh xạ khoảng, và nó sai
    đúng ở ca thường gặp nhất: một đoạn `equal` dài bị trả về nguyên khối, nên MỌI hunk
    nằm trong đó đều bị coi là "đã đụng" và một phép gộp sạch hiện ra toàn màu đỏ.
    """
    giu: set[int] = set()
    for tag, _i1, _i2, j1, j2 in difflib.SequenceMatcher(
            None, goc, ben, autojunk=False).get_opcodes():
        if tag == "equal":
            giu.update(range(j1, j2))
    return giu


def _danh_dau_xung_dot(hunks: list[dict[str, Any]], *, goc: list[str],
                       trai: list[str], phai: list[str]) -> None:
    """Hunk nào CẢ HAI bên cùng đụng vào so với gốc thì là xung đột.

    Chỉ một bên đụng thì không có gì phải hỏi người — lấy bên ấy là phép gộp đúng, và
    `_sua_tep` đã làm vậy từ trước bằng `git merge-file`.

    **Chỗ này không phải là bộ gộp.** Nó chỉ TÔ MÀU. Quyết định "gộp sạch hay không" vẫn do
    `vcs.merge_ba_chieu` (git) đưa ra ở `_sua_tep`; hai hiện thực có thể lệch nhau ở ca
    biên, và khi lệch thì diff vẫn hiện đủ mọi đoạn đã đổi — chỉ thiếu cái nhãn đỏ. Ca kiểm
    `test_hai_bo_may_dong_y_nhau` canh đúng chỗ lệch ấy trên ca thường gặp.

    **Một giới hạn đã biết, nói ra chứ không giấu:** hunk mà một bên XOÁ TRẮNG (không còn
    dòng nào để hỏi "dòng này có mới không") thì không được đánh xung đột, dù diff3 gọi
    "xoá một bên, sửa bên kia" là xung đột. Phép gộp của git vẫn bắt được ca ấy và vẫn
    dựng thẻ — chỉ khối diff là thiếu màu đỏ. Xem `test_xoa_mot_ben_sua_ben_kia`.
    """
    giu_t = _dong_giu_nguyen(goc, trai)
    giu_p = _dong_giu_nguyen(goc, phai)
    for h in hunks:
        a1, a2 = h["dong_trai"] - 1, h["dong_trai"] - 1 + h["so_trai"]
        b1, b2 = h["dong_phai"] - 1, h["dong_phai"] - 1 + h["so_phai"]
        trai_doi = any(i not in giu_t for i in range(a1, a2))
        phai_doi = any(j not in giu_p for j in range(b1, b2))
        if trai_doi and phai_doi:
            h["loai"] = "xung_dot"


__all__ = ["dung_diff", "diff_tom_tat", "in_canonical", "tom_tat", "bam", "TRAN_KY_TU"]
