# -*- coding: utf-8 -*-
"""Chỉ mục tìm kiếm tài liệu — M5-01. BM25 qua FTS5, lưu bền trong kho.

## Vì sao tệp này phải tồn tại

Trước M5-01, cả hệ thống chỉ có **một phép `in`**: `doc.read(tim=…)` lọc
`tk in t.chu.lower()` trên **một** `doc_id`, không xếp hạng. Ba câu hỏi rất thường gặp không
trả lời được bằng nó:

* *"tài liệu nào nói về pull-up I2C"* — phải gọi `doc.read` từng tài liệu một rồi tự so;
* *"tìm VCC"* trên một datasheet viết `Supply voltage` — ra **rỗng**, và rỗng ở đây đọc như
  *"tài liệu không có"*. Đây là loại câu trả lời sai mà N1 không bắt được, vì nó không bịa gì;
* *"đoạn nào liên quan NHẤT"* — không có khái niệm đó.

`grep -i "fts5|bm25|embedd|rerank"` trong `src/` trước M5-01 ra **0 kết quả**. Và có một dấu
vết của việc tính năng này từng được nghĩ tới rồi bỏ dở: `memory/envelope.py` khai chính sách
phong bì cho `"rag.ask"` — **một công cụ không tồn tại**.

## Hai thứ nó giải quyết cùng lúc

`doc_chunks` giữ nội dung từng đơn vị trích dẫn, nên chỉ mục **sống qua lần mở lại dự án**.
Trước đây `_lay_tai_lieu` gọi lại bộ đọc mỗi lần mở lại — tức chạy lại pypdf trên toàn bộ PDF
chỉ để trả lời một phép tìm.

## Chỗ dễ sai nhất: BM25 trả số ÂM

`bm25()` của FTS5 trả một số **âm**, và càng âm thì càng khớp. Trả thẳng nó ra ngoài thì mọi
chỗ sắp xếp "giảm dần theo điểm" sẽ ra **ngược**, im lặng. Nên `tim()` trả `diem = -bm25(...)`:
càng lớn càng khớp, đúng như người đọc một danh sách xếp hạng mong đợi.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from typing import Any

# Bảng ĐỒNG NGHĨA. Mỗi dòng là một nhóm; truy vấn chạm một từ trong nhóm thì được mở rộng ra
# cả nhóm.
#
# Vì sao cần: hai hãng gọi cùng một thông số bằng hai tên (`VCC` ↔ `Supply voltage`), và phép
# tách từ của FTS5 cắt `start-up` thành hai token nên nó không khớp `startup`. Không mở rộng
# thì một phép tìm đúng ý trả về rỗng — và rỗng đọc như *"tài liệu không có"*.
#
# Giữ bảng NHỎ và chỉ cho những cặp đã gặp thật trong datasheet trên máy. Một bảng đồng nghĩa
# rộng tay làm mọi truy vấn khớp mọi thứ, và lúc ấy xếp hạng mất nghĩa.
DONG_NGHIA: tuple[tuple[str, ...], ...] = (
    ("vdd", "vcc", "vddio", "supply voltage", "dien ap cap", "điện áp cấp"),
    ("start-up", "startup", "start up", "startup time", "thoi gian khoi dong"),
    ("tsu", "setup", "setup time", "thoi gian thiet lap"),
    ("pull-up", "pullup", "pull up", "dien tro keo len", "điện trở kéo lên"),
    ("fmax", "max frequency", "operating frequency", "clock frequency", "tan so"),
    ("icc", "supply current", "dong tieu thu", "dòng tiêu thụ"),
    ("ta", "ambient temperature", "operating temperature", "nhiet do"),
    ("flash", "program memory", "bo nho chuong trinh"),
    ("i2c", "twi", "two wire"),
)

# Trần số chunk của một tài liệu. Một datasheet 800 trang là chuyện có thật; chỉ mục hoá hết
# thì kho phình, mà phần cuối gần như không ai tra. Chỗ bị cắt được NÓI RA, không im lặng bỏ.
TRAN_CHUNK = 5000

_RE_TU = re.compile(r"[0-9a-zA-ZÀ-ỹ_\-\.]+")


def _tach(chu: str) -> list[str]:
    return [t.lower() for t in _RE_TU.findall(chu or "")]


def _chu_cua(t: Any) -> str:
    """Nội dung đi vào chỉ mục cho một đơn vị trích dẫn.

    Ô bảng nối bằng `" | "` **vào cùng chuỗi**: một đơn vị dạng hàng bảng mang chữ ở `o`, không
    ở `chu`. Bỏ `o` đi là bỏ chính phần datasheet đặt số vào — bảng đặc tính điện.
    """
    phan = [str(getattr(t, "chu", "") or "")]
    o = list(getattr(t, "o", None) or [])
    if o:
        phan.append(" | ".join(str(x) for x in o))
    cot = list(getattr(t, "cot", None) or [])
    if cot:
        phan.append(" | ".join(str(x) for x in cot))
    nhan = str(getattr(t, "nhan", "") or "")
    if nhan:
        phan.append(nhan)
    return "\n".join(p for p in phan if p.strip())


def ghi_chi_muc(store: Any, tl: Any) -> int:
    """Ghi lại chỉ mục của MỘT tài liệu. Trả số chunk đã ghi.

    **Xoá rồi ghi lại**, không cộng thêm: nạp lại cùng một `doc_id` (tài liệu sửa, phiên bản
    mới) mà cộng dồn thì một trang có hai bản trong chỉ mục, tức hai kết quả cho một chỗ — và
    người đọc không có cách nào biết bản nào là bản hiện tại.
    """
    db = store._db
    ds = list(getattr(tl, "trang", None) or [])[:TRAN_CHUNK]
    with store._lock:
        db.execute("DELETE FROM doc_chunks WHERE doc_id=?", (tl.doc_id,))
        if store.co_fts:
            db.execute("DELETE FROM doc_fts WHERE doc_id=?", (tl.doc_id,))
        for t in ds:
            chu = _chu_cua(t)
            if not chu.strip():
                continue
            h = hashlib.sha1(chu.encode("utf-8")).hexdigest()[:16]
            db.execute(
                "INSERT OR REPLACE INTO doc_chunks(doc_id,so,nhan,loai_bang,chu,hash) "
                "VALUES(?,?,?,?,?,?)",
                (tl.doc_id, int(t.so), str(getattr(t, "nhan", "") or ""),
                 str(getattr(t, "loai_bang", "") or ""), chu, h))
            if store.co_fts:
                db.execute("INSERT INTO doc_fts(chu,doc_id,so) VALUES(?,?,?)",
                           (chu, tl.doc_id, int(t.so)))
        db.commit()
    return len(ds)


def xoa_chi_muc(store: Any, doc_id: str) -> None:
    db = store._db
    with store._lock:
        db.execute("DELETE FROM doc_chunks WHERE doc_id=?", (doc_id,))
        if store.co_fts:
            db.execute("DELETE FROM doc_fts WHERE doc_id=?", (doc_id,))
        db.commit()


def dem_chunk(store: Any, doc_id: str | None = None) -> int:
    q = "SELECT COUNT(*) n FROM doc_chunks"
    a: tuple = ()
    if doc_id:
        q += " WHERE doc_id=?"
        a = (doc_id,)
    return int(store._db.execute(q, a).fetchone()["n"])


def so_tai_lieu(store: Any) -> int:
    return int(store._db.execute(
        "SELECT COUNT(DISTINCT doc_id) n FROM doc_chunks").fetchone()["n"])


# Từ CHỨC NĂNG — bỏ khỏi truy vấn khi còn token khác.
#
# Vì sao cần, bằng một phép đo: truy vấn `"zzzqqq khong co trong tai lieu nao"` — một câu
# không có thứ gì trong tài liệu — vẫn trả về 8 kết quả, vì `khong`/`co`/`trong`/`nao` khớp
# gần như mọi trang. BM25 cho chúng trọng số thấp nên **thứ tự** vẫn tạm đúng, nhưng tập
# **khớp** thì không: `ket_qua` không bao giờ rỗng.
#
# Và đó mới là chỗ đau: *"không khớp đoạn nào"* là tín hiệu duy nhất bảo tác tử **dừng đoán**
# và nói với người dùng rằng tài liệu không có phần đó. Một tín hiệu không bao giờ nổ thì
# bằng không có — tác tử luôn nhận được một thứ trông như câu trả lời.
#
# Tác tử gọi công cụ này bằng **lời của người dùng**, nên câu truy vấn là một câu tiếng Việt
# đầy đủ, không phải vài từ khoá.
_TU_CHUC_NANG = frozenset("""
cua la va hay hoac nao gi the thi ma nhung cac mot hai cho den tu voi theo trong ngoai
khong co duoc bao nhieu nhu nay do kia tai vi nen con se dang da chua cung cho_phep
the_nao bang tren duoi sau truoc khi lam gi
of the and or is are in on at to for with from by a an this that it be been was were
what which how many much do does did not no any some all
""".split())


def _dang_ke(tu: list[str]) -> list[str]:
    """Bỏ từ chức năng và token quá ngắn — nhưng chỉ khi còn lại thứ gì.

    Giữ lại khi lọc xong thành rỗng: một truy vấn `"V"` hay `"ta"` là hợp lệ (ký hiệu thông
    số), và trả rỗng ở đó là chặn một câu hỏi đúng.
    """
    giu = [t for t in tu if len(t) > 2 and t not in _TU_CHUC_NANG]
    return giu or tu


def mo_rong(truy_van: str) -> list[str]:
    """Truy vấn → danh sách token ĐÃ mở rộng theo `DONG_NGHIA`.

    Mở rộng theo **cụm** trước, rồi theo token: `"supply voltage"` là một cụm hai từ, và tra
    từng từ một thì `supply` khớp cả `supply current`.
    """
    chu = (truy_van or "").lower()
    tu = _dang_ke(_tach(chu))
    ra: list[str] = list(tu)
    for nhom in DONG_NGHIA:
        cham = any(k in chu for k in nhom if " " in k or "-" in k) or any(
            t in tu for t in nhom if " " not in t and "-" not in t)
        # `tu` ở đây đã qua `_dang_ke`, nên một từ chức năng không kéo được cả nhóm vào.
        if not cham:
            continue
        for k in nhom:
            ra.extend(_tach(k))
    # Giữ thứ tự, bỏ trùng: thứ tự giúp người đọc `truy_van_da_mo_rong` thấy phần gốc trước.
    thay: list[str] = []
    for t in ra:
        if t not in thay:
            thay.append(t)
    return thay


def _dieu_kien_doc(doc_ids: list[str] | None) -> tuple[str, list[Any]]:
    if not doc_ids:
        return "", []
    cho = ",".join("?" for _ in doc_ids)
    return f" AND doc_id IN ({cho})", list(doc_ids)


def tim(store: Any, truy_van: str, *, doc_ids: list[str] | None = None,
        k: int = 8) -> list[dict[str, Any]]:
    """Như `tim_xep_hang`, chỉ trả phần kết quả."""
    return tim_xep_hang(store, truy_van, doc_ids=doc_ids, k=k)[0]


def tim_xep_hang(store: Any, truy_van: str, *, doc_ids: list[str] | None = None,
                 k: int = 8) -> tuple[list[dict[str, Any]], str]:
    """Tìm đoạn liên quan trên MỌI tài liệu đã nạp, xếp hạng giảm dần theo `diem`.

    `diem = -bm25(...)`: `bm25()` của FTS5 trả số **âm** và càng âm thì càng khớp, nên trả
    thẳng nó ra ngoài sẽ làm mọi phép sắp xếp "giảm dần" ra **ngược**, im lặng.

    Không có FTS5 thì xếp hạng bằng **số token khớp** — thô hơn nhiều, nhưng nó trả lời được
    câu *"tài liệu nào nhắc tới thứ này"*, và đó là câu hỏi hay gặp nhất.
    """
    tu = mo_rong(truy_van)
    if not tu:
        return [], "rong"
    k = max(1, min(int(k or 8), 20))
    loc, tham = _dieu_kien_doc(doc_ids)

    if getattr(store, "co_fts", False):
        # Mỗi token là một vế OR, bọc trong dấu nháy kép để FTS5 không đọc `-` là toán tử
        # NOT: `pull-up` chưa bọc sẽ thành *"pull VÀ KHÔNG up"*, tức ngược hẳn ý.
        mau = " OR ".join('"' + t.replace('"', "") + '"' for t in tu[:40])
        q = ("SELECT doc_id, so, chu, -bm25(doc_fts) AS diem FROM doc_fts "
             "WHERE doc_fts MATCH ?" + loc + " ORDER BY diem DESC LIMIT ?")
        try:
            hang = list(store._db.execute(q, [mau, *tham, k]))
        except sqlite3.OperationalError:
            # Cú pháp MATCH hỏng (ví dụ token mang dấu `-` chưa bọc nháy kép: FTS5 đọc nó là
            # tên cột và nổ `no such column`). Rơi về đường thô được, NHƯNG phải nói ra —
            # bản đầu nuốt im lặng, nên `note_vi` vẫn khai là BM25 trong khi tác tử đang đọc
            # một thứ tự xếp hạng thô. Tìm ra bằng tập phá của chính nhiệm vụ này.
            hang = []
            duong_loi = True
        else:
            duong_loi = False
        if hang:
            return ([_dong(store, r["doc_id"], r["so"], r["chu"], float(r["diem"]))
                     for r in hang], "bm25")
        if duong_loi:
            tho = "loi_cu_phap"

    # Dự phòng — và cũng là đường chạy khi FTS5 có mà truy vấn không khớp token nào.
    tho = locals().get("tho") or ("khong_fts" if not getattr(store, "co_fts", False)
                                  else "khong_khop")
    q = "SELECT doc_id, so, chu FROM doc_chunks WHERE 1=1" + loc
    diem: list[tuple[float, Any]] = []
    for r in store._db.execute(q, tham):
        thap = r["chu"].lower()
        d = sum(1 for t in tu if t in thap)
        if d:
            # Chia theo độ dài để một trang dài không thắng chỉ vì nó dài — cùng ý với BM25.
            diem.append((d + d / (1 + len(thap) / 2000.0), r))
    diem.sort(key=lambda x: (-x[0], x[1]["doc_id"], x[1]["so"]))
    return ([_dong(store, r["doc_id"], r["so"], r["chu"], round(d, 3))
             for d, r in diem[:k]], tho)


def _dong(store: Any, doc_id: str, so: int, chu: str, diem: float) -> dict[str, Any]:
    r = store._db.execute(
        "SELECT nhan, loai_bang FROM doc_chunks WHERE doc_id=? AND so=?",
        (doc_id, int(so))).fetchone()
    nhan = (r["nhan"] if r else "") or ""
    return {"doc_id": doc_id, "so": int(so), "nhan": nhan,
            "trich_dan": nhan or f"trang {so}",
            "loai_bang": (r["loai_bang"] if r else "") or "",
            "diem": diem, "chu": chu}


def cua_so(chu: str, truy_van: str, rong: int = 600) -> str:
    """Đoạn `rong` ký tự **quanh chỗ khớp đầu tiên**, không phải đầu trang.

    Cùng lý do với chính sách phong bì của `doc.read` (M5-13): người gọi tìm vì họ cần đúng
    chỗ ấy, nên trả về phần đầu của một trang 2 000 ký tự là trả về phần họ không hỏi.
    """
    if len(chu) <= rong:
        return chu
    thap = chu.lower()
    i = -1
    for t in mo_rong(truy_van):
        i = thap.find(t)
        if i >= 0:
            break
    if i < 0:
        return chu[:rong] + "…"
    dau = max(0, i - rong // 2)
    return ("…" if dau else "") + chu[dau:dau + rong] + ("…" if dau + rong < len(chu) else "")
