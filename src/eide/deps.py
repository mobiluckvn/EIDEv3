# -*- coding: utf-8 -*-
"""Đồ thị phụ thuộc và STALE — EIDE-MDD-40 §E5.4.

    "Chuỗi phụ thuộc mặc định: REQ → phương án → module → pinout/netlist → BOM/ERC →
     mã → build → tiêu chí → sim → flash. Fact → mọi hiện vật dùng Fact đó (qua sources).
     Khi hiện vật thượng nguồn đổi (bởi ai), hạ nguồn được đánh dấu STALE với lý do —
     **không tự xoá, không tự chạy lại**."

Câu cuối là cả thiết kế. Có ba cách xử lý một hiện vật lỗi thời, và tài liệu chọn cách
thứ ba:

  1. Xoá nó đi — người mất việc đã làm, không hỏi.
  2. Tự chạy lại — tốn tiền, và có thể chạy lại thứ người đang muốn giữ.
  3. **Đánh dấu và nói lý do** — người nhìn thấy, người quyết.

Cách thứ ba đắt hơn về mã (phải có đồ thị, phải có lý do đọc được, phải có nút "chấp
nhận STALE") nhưng nó là cách duy nhất không lấy mất quyền quyết của người.
"""

from __future__ import annotations

from typing import Any, Iterable

# §E5.4 — chuỗi mặc định. Khoá là loại hiện vật, giá trị là các loại phụ thuộc vào nó.
HA_NGUON: dict[str, tuple[str, ...]] = {
    "req":           ("option", "adr", "block_diagram", "code", "criteria", "findings",
                      "note"),
    "option":        ("adr", "block_diagram", "netlist", "bom", "code"),
    "adr":           ("block_diagram", "netlist", "code"),
    "passport":      ("pinout", "netlist", "ckm", "code", "build", "sim_result", "target"),
    "block_diagram": ("netlist", "pinout", "ckm", "code"),
    "pinout":        ("netlist", "ckm", "code", "build"),
    "netlist":       ("bom", "findings", "pinout", "ckm", "code"),
    "bom":           ("findings", "ckm"),
    # CKM là thứ sinh sơ đồ nguyên lý và sinh mã dùng chân. Đổi bản đồ thì cả hai lỗi thời.
    "ckm":           ("netlist", "pinout", "code", "findings"),
    "code":          ("build", "sim_result", "target"),
    "config":        ("build",),
    "build":         ("sim_result", "target"),
    "criteria":      ("sim_result",),
    "sim_result":    ("target",),
    # Fact đi theo đường riêng: qua `sources`, không theo loại (xem `fact_ha_nguon`).
}

# Loại hiện vật KHÔNG bao giờ bị đánh STALE: chúng là bằng chứng của một thời điểm,
# không phải kết luận cần cập nhật.
KHONG_STALE = frozenset({"changeset", "snapshot", "report", "analysis"})


def ha_nguon_cua(store: Any, artefact_id: str) -> list[str]:
    """Hiện vật nào phụ thuộc vào cái này.

    Hai đường, cộng lại:
      - **theo loại** (chuỗi mặc định §E5.4): REQ đổi thì phương án/module/mã lỗi thời;
      - **theo khai báo** (`deps.upstream` của chính hiện vật): chính xác hơn chuỗi
        mặc định, vì nó nói *hiện vật này* dựng từ *cái kia*, chứ không phải *loại này*
        thường dựng từ *loại kia*.
    """
    goc = store.get(artefact_id)
    if goc is None:
        return []

    ket: list[str] = []

    # Đường khai báo: ai ghi rằng mình phụ thuộc vào goc.
    for a in store.list(limit=2000):
        if a["id"] == artefact_id or a["type"] in KHONG_STALE:
            continue
        up = (a.get("deps") or {}).get("upstream") or []
        if artefact_id in up:
            ket.append(a["id"])

    # Đường mặc định theo loại.
    for loai in HA_NGUON.get(goc["type"], ()):
        for a in store.list(loai, limit=500):
            if a["id"] != artefact_id and a["id"] not in ket:
                ket.append(a["id"])

    return ket


def fact_ha_nguon(store: Any, fact_id: str) -> list[str]:
    """Mọi hiện vật dùng Fact này — tra qua `explain.sources` (§E5.4).

    §C1 buộc mỗi con số trong `summary`/`why` phải có nguồn trong `sources`. Nhờ ràng
    buộc đó, câu hỏi "Fact này đổi thì cái gì lỗi thời?" trả lời được bằng tra bảng,
    không cần đoán.
    """
    ket = []
    for a in store.list(limit=2000):
        if a["type"] in KHONG_STALE:
            continue
        for s in (a.get("explain") or {}).get("sources", []) or []:
            ref = s.get("ref") if isinstance(s, dict) else str(s)
            if ref and fact_id in str(ref):
                ket.append(a["id"])
                break
    return ket


def danh_dau_stale(store: Any, *, thuong_nguon: Iterable[str], ly_do_cs: str,
                   mo_ta: str = "") -> list[str]:
    """Đánh dấu hạ nguồn của các hiện vật vừa đổi. Trả danh sách đã đánh dấu.

    Lý do luôn mang **mã changeset**, để băng cảnh báo trên tab nói được câu đầy đủ:
    "cần cập nhật vì cs-0103 (anh sửa REQ v2)" — chứ không phải "cần cập nhật" cụt lủn.
    """
    can: list[str] = []
    for aid in thuong_nguon:
        for ha in ha_nguon_cua(store, aid):
            if ha not in can:
                can.append(ha)
        if aid.startswith("fact:") or (store.get(aid) or {}).get("type") == "fact":
            for ha in fact_ha_nguon(store, aid):
                if ha not in can:
                    can.append(ha)

    if not can:
        return []
    ly_do = f"{ly_do_cs}" + (f" ({mo_ta})" if mo_ta else "")
    store.mark_stale(can, ly_do)
    return can


def chuoi_giai_thich(store: Any, artefact_id: str) -> str:
    """Câu giải thích cho người: cái này lỗi thời vì cái kia đổi."""
    a = store.get(artefact_id)
    if a is None or not a.get("stale"):
        return ""
    return f"{artefact_id} cần cập nhật vì {a.get('stale_reason') or 'thượng nguồn đã đổi'}"
