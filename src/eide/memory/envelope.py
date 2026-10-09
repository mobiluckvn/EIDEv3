# -*- coding: utf-8 -*-
"""Bao kết quả công cụ trước khi nó vào ngữ cảnh — EIDE-MEM-42 §5.1, §5.2.

Tài liệu gọi đây là *"biện pháp quan trọng nhất và rẻ nhất"*, và số liệu ủng hộ: một
`fs.read` trên tệp 3 000 dòng, hay một log build dài, đi nguyên văn vào transcript là
gần hết cửa sổ sau vài lời gọi. TC028 (repo > 500 tệp) trượt vì đúng chuyện đó.

Ý tưởng, một câu: **mô hình nhận đúng lượng nó cần, phần còn lại nằm ở blob và đọc lại
được bằng `blob.read`.** Cắt mà không có đường đọc lại thì không phải là cắt — là mất.

Ba điều bộ này cố ý KHÔNG làm:

1. **Không cắt lặng lẽ.** Mỗi lần cắt đều để lại `summary_line` nói rõ đã hiện bao
   nhiêu trên tổng bao nhiêu, và `blob_ref` để lấy phần còn lại. Người và mô hình đều
   đọc được câu đó.
2. **Không cắt cái nhỏ.** Kết quả đã dưới trần thì đi qua nguyên vẹn, không bọc thêm
   một lớp giấy. Bọc mọi thứ chỉ làm tăng token mà không giảm gì.
3. **Không cắt lỗi.** Một `EideError` mang bốn trường để mô hình đổi hướng; cắt nó là
   cắt đúng thứ đang cứu lượt (§B3).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

# Ước token: ~3 ký tự tiếng Việt có dấu. Dùng chung với context.assemble để hai chỗ
# không nói hai con số khác nhau về cùng một đoạn chữ.
KY_TU_MOI_TOKEN = 3.0


def uoc_token(x: Any) -> int:
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    return int(len(s) / KY_TU_MOI_TOKEN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


# =========================================================================== phong bì
@dataclass(slots=True)
class ToolResultEnvelope:
    """§5.2 — thứ thật sự đi vào transcript thay cho kết quả thô."""

    tool: str
    call_id: str
    ts: str = field(default_factory=_now)
    ok: bool = True
    data: Any = None                      # phần đã cắt, đi vào ngữ cảnh
    truncated: bool = False
    shown_tokens: int = 0
    full_tokens: int = 0
    blob_ref: str | None = None           # "blob:sha256:…"
    artefact_ref: dict[str, Any] | None = None
    summary_line: str = ""
    error: dict[str, Any] | None = None

    def to_model(self) -> dict[str, Any]:
        """Dạng mô hình đọc. Lỗi giữ nguyên bốn trường, không bọc."""
        if not self.ok and self.error is not None:
            return self.error
        d: dict[str, Any] = {"ok": True, "data": self.data}
        if self.truncated:
            d["_cat"] = {
                "vi_sao": "kết quả dài hơn trần cho phép vào ngữ cảnh",
                "da_hien": f"{self.shown_tokens} token / khoảng {self.full_tokens}",
                "phan_con_lai": self.blob_ref,
                "doc_tiep_bang": f"blob.read(ref={self.blob_ref!r}, tu=…, den=…)",
            }
        if self.summary_line:
            d["_dong"] = self.summary_line
        if self.artefact_ref:
            d["_hien_vat"] = self.artefact_ref
        return d

    def to_ledger(self) -> dict[str, Any]:
        return {"tool": self.tool, "call_id": self.call_id, "ok": self.ok,
                "truncated": self.truncated, "shown_tokens": self.shown_tokens,
                "full_tokens": self.full_tokens, "blob_ref": self.blob_ref,
                "summary_line": self.summary_line}


# =========================================================================== chính sách
# Bảng §5.1. Mỗi dòng: bao nhiêu đi vào ngữ cảnh, và mô hình đọc thêm bằng gì.
#
# Một chính sách nhận `(data, args)` và trả `(data_hien, dong_tom_tat, con_nua)`.
# `con_nua = False` nghĩa là không cần blob — kết quả đã đủ nhỏ.

TRAN_DONG_MAC_DINH = 80
TRAN_KY_TU_DONG = 200


def _cat_dong(chu: str, so_dong: int) -> tuple[str, int, int]:
    ds = chu.splitlines()
    return "\n".join(ds[:so_dong]), min(len(ds), so_dong), len(ds)


def _cat_dau_cuoi(chu: str, dau: int, cuoi: int) -> tuple[str, int]:
    """Đầu N + cuối N. Với log thì hai đầu là chỗ có tin, khúc giữa hiếm khi."""
    ds = chu.splitlines()
    if len(ds) <= dau + cuoi:
        return chu, len(ds)
    giua = len(ds) - dau - cuoi
    return ("\n".join(ds[:dau]) + f"\n… (đã cắt {giua} dòng ở giữa) …\n"
            + "\n".join(ds[-cuoi:])), len(ds)


def _cs_fs_read(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """≤ 400 dòng; tệp dài hơn thì đầu 60 dòng + đề mục hàm/cấu trúc + gợi ý range."""
    if not isinstance(d, dict) or "content" not in d:
        return d, "", False
    tong = int(d.get("lines_total") or 0)
    chu = str(d.get("content") or "")
    duong = d.get("path", "?")
    if tong <= 400:
        hien, n, _ = _cat_dong(chu, 400)
        moi = {**d, "content": hien}
        return moi, f"fs.read {duong} ({tong} dòng, hiện đủ)", len(chu.splitlines()) > n

    dau, _, _ = _cat_dong(chu, 60)
    de_muc = _de_muc(chu)
    moi = {**d, "content": dau, "truncated": True,
           "de_muc": de_muc,
           "note_vi": (f"Tệp {tong} dòng — ngữ cảnh chỉ nhận 60 dòng đầu và bảng đề mục. "
                       f"Đọc tiếp bằng fs.read(path, offset, limit), hoặc đọc nguyên văn "
                       f"bằng blob.read.")}
    return moi, f"fs.read {duong} ({tong} dòng, hiện 1–60 + {len(de_muc)} đề mục)", True


def _de_muc(chu: str) -> list[str]:
    """Đề mục hàm/cấu trúc — thay cho ctags, đủ dùng cho C/H/Python/Swift.

    Lưu ý `fs.read` trả nội dung **đã đánh số dòng** (`"  123\\tmã"`), nên phải gỡ tiền
    tố đó trước khi khớp. Bản đầu quên chuyện này và bảng đề mục luôn rỗng — tức mô
    hình nhận 60 dòng đầu mà không có gì để biết nên đọc tiếp đoạn nào.
    """
    import re

    so_dong = re.compile(r"^\s*\d+\t")
    mau = re.compile(
        r"^\s*(?:"
        r"(?:static\s+|inline\s+|extern\s+)*[\w\*]+\s+\**(\w+)\s*\([^;]*\)\s*\{"   # hàm C
        r"|def\s+(\w+)"                                                             # Python
        r"|class\s+(\w+)"
        r"|(?:func|struct|enum|protocol)\s+(\w+)"                                   # Swift
        r"|#\s*define\s+(\w+)"
        r"|typedef\s+struct\s*\{?\s*(\w*)"
        r")")
    ra: list[str] = []
    for i, dong in enumerate(chu.splitlines(), 1):
        m = mau.match(so_dong.sub("", dong))
        if m:
            ten = next((g for g in m.groups() if g), "")
            if ten:
                ra.append(f"{i}: {ten}")
        if len(ra) >= 120:
            ra.append("… (còn nữa)")
            break
    return ra


def _cs_tim_kiem(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """fs.grep / fs.glob: ≤ 80 dòng khớp, mỗi dòng ≤ 200 ký tự, và ĐẾM tổng."""
    if not isinstance(d, dict):
        return d, "", False
    khoa = "hits" if "hits" in d else ("files" if "files" in d else None)
    if khoa is None:
        return d, "", False
    ds = d.get(khoa) or []
    tong = int(d.get("count") or len(ds))
    if len(ds) <= TRAN_DONG_MAC_DINH:
        return d, f"{khoa} {tong} kết quả", False
    giu = ds[:TRAN_DONG_MAC_DINH]
    for h in giu:
        if isinstance(h, dict) and isinstance(h.get("text"), str):
            h["text"] = h["text"][:TRAN_KY_TU_DONG]
    moi = {**d, khoa: giu, "truncated": True,
           "note_vi": (f"{tong} kết quả, ngữ cảnh nhận {TRAN_DONG_MAC_DINH} cái đầu. "
                       "Thu hẹp mẫu tìm, hoặc đọc đủ bằng blob.read.")}
    return moi, f"tìm thấy {tong}, hiện {TRAN_DONG_MAC_DINH}", True


def _cs_log(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """bash / target.log: đầu 40 + cuối 40 dòng + mã thoát."""
    if not isinstance(d, dict):
        return d, "", False
    for khoa in ("stdout", "output", "log", "text"):
        if isinstance(d.get(khoa), str):
            chu = d[khoa]
            hien, tong = _cat_dau_cuoi(chu, 40, 40)
            con = hien != chu
            moi = {**d, khoa: hien}
            if con:
                moi["truncated"] = True
            return moi, f"{tong} dòng log", con
    return d, "", False


def _cs_build(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """build.compile: ok/fail + ≤ 20 lỗi đầu (đã gom trùng) + Flash/RAM."""
    if not isinstance(d, dict):
        return d, "", False
    loi = d.get("errors") or d.get("loi") or []
    if not isinstance(loi, list) or len(loi) <= 20:
        return d, "", False
    moi = {**d, "errors": loi[:20], "truncated": True,
           "note_vi": f"{len(loi)} lỗi/cảnh báo, hiện 20 cái đầu. Sửa từ trên xuống."}
    return moi, f"build: {len(loi)} lỗi, hiện 20", True


def _cs_ingest(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """ingest.file: số trang/bảng/Fact + 5 tiêu đề bảng đầu. Cây tệp dài thì cắt."""
    if not isinstance(d, dict):
        return d, "", False
    cay = d.get("cay")
    if isinstance(cay, list) and len(cay) > 25:
        moi = {**d, "cay": cay[:25], "truncated": True,
               "note_vi": (f"Gói có {len(cay)} tệp, ngữ cảnh nhận 25 cái đầu. "
                           "Trình đầy đủ cho người dùng trên tab Tài liệu và hỏi họ chọn.")}
        return moi, f"{d.get('loai', 'tệp')} · {len(cay)} mục, hiện 25", True
    return d, f"{d.get('loai', 'tệp')} · {d.get('mo_ta', '')}", False


def _cs_danh_sach(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """history.list / ledger.query / store.list: ≤ 30 mục, mỗi mục một dòng."""
    if not isinstance(d, dict):
        return d, "", False
    for khoa in ("items", "muc", "changesets", "events", "rows", "ban"):
        ds = d.get(khoa)
        if isinstance(ds, list) and len(ds) > 30:
            moi = {**d, khoa: ds[:30], "truncated": True,
                   "note_vi": f"{len(ds)} mục, hiện 30 cái mới nhất."}
            return moi, f"{len(ds)} mục, hiện 30", True
    return d, "", False


def _cs_web(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """doc.search_web: ≤ 8 ứng viên (tiêu đề, domain, phiên bản, kích thước)."""
    if not isinstance(d, dict):
        return d, "", False
    ds = d.get("ket_qua") or d.get("results")
    if isinstance(ds, list) and len(ds) > 8:
        khoa = "ket_qua" if "ket_qua" in d else "results"
        moi = {**d, khoa: ds[:8], "truncated": True,
               "note_vi": f"{len(ds)} kết quả, hiện 8 cái đầu."}
        return moi, f"{len(ds)} ứng viên, hiện 8", True
    return d, "", False


# M5-13 — ba công cụ ĐỌC TRI THỨC không có chính sách riêng, nên chúng rơi vào trần chung —
# và trần chung bị lách: `_cat_chung` cắt SỐ phần tử của một list (`d[:30]`) mà không cắt từng
# phần tử. Một `doc.read` **mặc định** trả 40 đoạn × 2 000 ký tự ≈ 60 000 ký tự ≈ 20 000 token,
# và 30 phần tử đầu của nó vẫn là 60 000 ký tự.
#
# Đây không phải ca bất thường mà trần chung sinh ra để đỡ: nó là đường đọc tài liệu CHÍNH.
_DOC_SO_DOAN = 8
_DOC_KY_TU = 600
_FACT_SO = 30


def _cs_doc_read(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """`doc.read`: ≤ 8 đoạn, mỗi đoạn 600 ký tự **quanh chỗ khớp từ khoá**.

    Cửa sổ đi theo `tim` chứ không lấy đầu đoạn, và đó là cả nửa giá trị của chính sách này:
    tác tử gọi `doc.read(tim="throttle")` vì nó cần đúng chỗ ấy. Trả 600 ký tự đầu của một
    đoạn 5 000 ký tự là trả về phần nó **không** hỏi — rồi nó gọi lại, hoặc tệ hơn, kết luận
    tài liệu không có phần đó.
    """
    if not isinstance(d, dict) or not isinstance(d.get("doan"), list):
        return d, "", False
    ds = d["doan"]
    tim = str(args.get("tim") or "").strip().lower()

    def _cua_so(chu: str) -> str:
        if len(chu) <= _DOC_KY_TU:
            return chu
        i = chu.lower().find(tim) if tim else -1
        if i < 0:
            return chu[:_DOC_KY_TU] + "…"
        dau = max(0, i - _DOC_KY_TU // 2)
        return ("…" if dau else "") + chu[dau:dau + _DOC_KY_TU] + "…"

    giu = []
    doi = False
    for t in ds[:_DOC_SO_DOAN]:
        if not isinstance(t, dict):
            giu.append(t)
            continue
        chu = str(t.get("chu") or "")
        o = list(t.get("o") or [])
        m = {**t, "chu": _cua_so(chu), "o": o[:10]}
        if m["chu"] != chu or len(o) > 10:
            doi = True
        giu.append(m)
    con = len(ds) - len(giu)
    if not doi and con <= 0:
        return d, "", False

    moi = {**d, "doan": giu, "so_tra_ve": len(giu), "bi_cat": True,
           "note_vi": ((d.get("note_vi") or "") + " ").strip()
           + (f"Phong bì chỉ hiện {len(giu)}/{d.get('so_khop', len(ds))} đoạn"
              + (f", còn {con} đoạn nữa" if con > 0 else "")
              + ". Gọi lại với `tu` = "
              + str((giu[-1].get("so") if isinstance(giu[-1], dict) else len(giu)) or len(giu))
              + " để đọc tiếp, hoặc `blob.read` để lấy nguyên văn phần dư.")}
    return (moi,
            f"doc.read {d.get('doc_id', '?')}: {d.get('so_khop', len(ds))} khớp, "
            f"hiện {len(giu)}", True)


def _cs_fact(d: Any, args: dict[str, Any]) -> tuple[Any, str, bool]:
    """`fact.query` / `fact.extract`: ≤ 30 Fact, bỏ `explain`, gọn `source`.

    `explain` của một Fact là một chuỗi JSON cỡ 1 KB, và mô hình KHÔNG cần nó để dùng con số:
    nó cần `value`, `unit`, `tier`, và **chỗ tra lại**. 100 Fact × 1 KB là hơn 30 000 token
    cho một phép tra.

    `source` thì giữ — nhưng chỉ `doc_id`/`page`/`cite`. Cắt luôn cả `source` là lấy mất đúng
    thứ làm một Fact khác với một con số nhớ được.
    """
    if not isinstance(d, dict):
        return d, "", False
    khoa = "facts" if isinstance(d.get("facts"), list) else (
        "fact" if isinstance(d.get("fact"), list) else "")
    if not khoa:
        return d, "", False
    ds = d[khoa]
    # Kết quả nhỏ đi NGUYÊN qua. Bỏ `explain` của ba Fact tiết kiệm được chút ít, nhưng nó
    # đánh dấu `truncated` lên **mọi** lời gọi — và một dấu "đã cắt" xuất hiện ở mọi nơi thì
    # không còn nói gì. Trần đặt ở mức một phép tra bình thường không chạm tới.
    if uoc_token(d) <= 800:
        return d, "", False

    def _gon(f: Any) -> Any:
        if not isinstance(f, dict):
            return f
        ra = {k: v for k, v in f.items() if k != "explain"}
        src = f.get("source")
        if isinstance(src, str):
            try:
                src = json.loads(src)
            except (ValueError, TypeError):
                src = None
        if isinstance(src, dict):
            ra["source"] = {k: src[k] for k in ("doc_id", "page", "cite") if k in src}
        return ra

    giu = [_gon(f) for f in ds[:_FACT_SO]]
    if giu == ds:
        return d, "", False
    con = len(ds) - len(giu)
    moi = {**d, khoa: giu,
           "note_vi": ((d.get("note_vi") or "") + " ").strip()
           + (f"Phong bì hiện {len(giu)}/{len(ds)} Fact"
              + (f" (còn {con})" if con > 0 else "")
              + ", đã bỏ trường `explain` để giữ cửa sổ. Nguyên văn ở `blob.read`; lý do "
                "từng Fact đọc bằng `fact.review` hoặc `store.get`.")}
    return moi, f"{khoa}: {len(ds)} Fact, hiện {len(giu)} (bỏ explain)", True


CHINH_SACH: dict[str, Callable[[Any, dict[str, Any]], tuple[Any, str, bool]]] = {
    "doc.read": _cs_doc_read,
    "fact.query": _cs_fact,
    "fact.extract": _cs_fact,
    "fs.read": _cs_fs_read,
    "fs.grep": _cs_tim_kiem,
    "fs.glob": _cs_tim_kiem,
    "bash": _cs_log,
    "target.log": _cs_log,
    "sim.run": _cs_log,
    "analyze.capture": _cs_log,
    "build.compile": _cs_build,
    "ingest.file": _cs_ingest,
    # M5-01 — khoá này trước đây là `"rag.ask"`, **một công cụ không tồn tại**: dấu vết
    # của một tính năng đã được nghĩ tới rồi bỏ dở, nằm đúng chỗ dễ làm người đọc mã tin
    # là đã có RAG. Nay nó trỏ về công cụ thật.
    "doc.search": _cs_danh_sach,
    "history.list": _cs_danh_sach,
    "ledger.query": _cs_danh_sach,
    "store.list": _cs_danh_sach,
    "snapshot.list": _cs_danh_sach,
    "doc.search_web": _cs_web,
}

# Trần chung cho công cụ KHÔNG có chính sách riêng. Đặt rộng tay có chủ đích: mục tiêu
# của trần chung không phải tiết kiệm từng token, mà là chặn một kết quả bất thường
# nuốt cả cửa sổ. Công cụ nào thường xuyên chạm trần thì nên có chính sách riêng, và
# việc nó chạm trần sẽ hiện trong sổ cái.
TRAN_CHUNG_TOKEN = 4000


def dong_tom_tat(tool: str, d: Any) -> str:
    if isinstance(d, dict):
        for k in ("path", "id", "doc_id", "snapshot", "changeset"):
            if d.get(k):
                return f"{tool} {d[k]}"
    return tool


def boc_ket_qua(*, tool: str, call_id: str, ket_qua: Any, args: dict[str, Any] | None = None,
                blobs: Any = None) -> ToolResultEnvelope:
    """Bọc một `ToolResult` thành phong bì, cắt theo chính sách và đẩy phần dư vào blob.

    `blobs` là `BlobStore`; thiếu nó thì vẫn cắt nhưng không có đường đọc lại — và khi
    đó phong bì **nói thẳng ra** thay vì im lặng làm mất dữ liệu.
    """
    env = ToolResultEnvelope(tool=tool, call_id=call_id)

    if not getattr(ket_qua, "ok", True):
        # §B3 — lỗi là dữ liệu để mô hình đổi hướng. Không cắt, không bọc.
        env.ok = False
        env.error = ket_qua.to_model()
        env.shown_tokens = env.full_tokens = uoc_token(env.error)
        env.summary_line = f"{tool} → {env.error.get('code', 'lỗi')}"
        return env

    tho = getattr(ket_qua, "data", ket_qua)
    env.full_tokens = uoc_token(tho)
    env.artefact_ref = _hien_vat(ket_qua, tho)

    cs = CHINH_SACH.get(tool)
    if cs is not None:
        hien, dong, con_nua = cs(tho, args or {})
    else:
        hien, dong, con_nua = tho, "", False
        if env.full_tokens > TRAN_CHUNG_TOKEN:
            # Chừa chỗ cho phần vỏ JSON. `_cat_chung` tiêu đúng ngân sách nó được giao, nên
            # giao cả trần thì `shown_tokens` nhảy lên trên trần vì mấy chục token dấu ngoặc
            # và tên khoá — một cái trần bị vượt bởi chính phép cắt dựng ra để giữ nó.
            hien = _cat_chung(tho, TRAN_CHUNG_TOKEN * 3 // 4)
            con_nua = True
            dong = f"{tool}: kết quả {env.full_tokens} token, đã thu gọn"

    env.data = hien
    env.shown_tokens = uoc_token(hien)
    env.truncated = con_nua or env.shown_tokens < env.full_tokens
    env.summary_line = dong or dong_tom_tat(tool, tho)

    if env.truncated:
        if blobs is not None:
            h = blobs.put(json.dumps(tho, ensure_ascii=False, default=str))
            env.blob_ref = f"blob:sha256:{h}"
        else:
            env.summary_line += " · (không có kho blob — phần dư KHÔNG lưu lại được)"
    return env


# Trần cho MỘT phần tử bên trong một kết quả đã phải thu gọn. Không để một phần tử tiêu hết
# ngân sách của cả kết quả — và không hạ xuống quá thấp, vì một mảnh 100 ký tự thì mô hình
# không đọc ra được gì ngoài việc "có thứ gì ở đây".
TRAN_PHAN_TU_TOKEN = 400


def _cat_chung(d: Any, tran: int = TRAN_CHUNG_TOKEN) -> Any:
    """Thu gọn một kết quả không có chính sách riêng, giữ hình dạng để mô hình còn hiểu.

    `tran` là NGÂN SÁCH của nhánh này, và nó phải đi xuống theo. Bản trước chỉ cắt *số* phần
    tử của một list (`d[:30]`) rồi cắt mỗi chuỗi theo trần **của cả kết quả** — nên
    `{"ds": ["y"*20000]*5}` ra 5 × 12 000 ký tự: một cái trần 4 000 token bị lách thành
    20 000 token, bằng chính cái phép cắt đáng ra phải chặn nó.
    """
    if isinstance(d, str):
        n = int(max(tran, 100) * KY_TU_MOI_TOKEN)
        return d if len(d) <= n else d[:n] + "\n… (đã cắt)"
    if isinstance(d, list):
        giu = d[:30]
        # Chia ngân sách cho các phần tử còn giữ. Phần tử nhỏ không tiêu gì, nên chỗ dư
        # không bị mất — chỉ phần tử to bị kẹp.
        moi = max(TRAN_PHAN_TU_TOKEN, tran // max(1, len(giu)))
        ds = [_cat_chung(x, moi) if uoc_token(x) > moi else x for x in giu]
        return ds + ["… (đã cắt)"] if len(d) > 30 else ds
    if isinstance(d, dict):
        ra: dict[str, Any] = {}
        moi = max(TRAN_PHAN_TU_TOKEN, tran // max(1, len(d)))
        for k, v in d.items():
            ra[k] = _cat_chung(v, moi) if uoc_token(v) > moi else v
        ra["truncated"] = True
        return ra
    return d


def _hien_vat(ket_qua: Any, tho: Any) -> dict[str, Any] | None:
    """§5.2 — tham chiếu hiện vật theo id + version, để mô hình biết đang nói bản nào."""
    ma = getattr(ket_qua, "artefact_id", None)
    if not ma and isinstance(tho, dict):
        ma = tho.get("artefact_id") or tho.get("id")
    if not ma:
        return None
    ra: dict[str, Any] = {"id": ma}
    if isinstance(tho, dict):
        for k in ("version", "phien_ban"):
            if tho.get(k):
                ra["version"] = tho[k]
                break
        if tho.get("type"):
            ra["type"] = tho["type"]
    return ra
