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


CHINH_SACH: dict[str, Callable[[Any, dict[str, Any]], tuple[Any, str, bool]]] = {
    "fs.read": _cs_fs_read,
    "fs.grep": _cs_tim_kiem,
    "fs.glob": _cs_tim_kiem,
    "bash": _cs_log,
    "target.log": _cs_log,
    "sim.run": _cs_log,
    "analyze.capture": _cs_log,
    "build.compile": _cs_build,
    "ingest.file": _cs_ingest,
    "rag.ask": _cs_danh_sach,
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
            hien = _cat_chung(tho)
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


def _cat_chung(d: Any) -> Any:
    """Thu gọn một kết quả không có chính sách riêng, giữ hình dạng để mô hình còn hiểu."""
    if isinstance(d, str):
        return d[: int(TRAN_CHUNG_TOKEN * KY_TU_MOI_TOKEN)] + "\n… (đã cắt)"
    if isinstance(d, list):
        return d[:30] + ["… (đã cắt)"] if len(d) > 30 else d
    if isinstance(d, dict):
        ra: dict[str, Any] = {}
        for k, v in d.items():
            ra[k] = _cat_chung(v) if uoc_token(v) > 500 else v
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
