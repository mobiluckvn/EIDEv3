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
    tat_ca = store.list(limit=2000)
    loai_cua = {a["id"]: a["type"] for a in tat_ca}

    # M2-01 — hiện vật đã NÓI RÕ nó dựng từ những cái nào cùng loại với `goc` thì lời khai
    # của nó thắng chuỗi mặc định. Một tiêu chí khai `do_req: FR-01` mà vẫn lỗi thời khi
    # người ta sửa FR-02 thì lời khai ấy chẳng để làm gì — và băng cảnh báo lúc nào cũng
    # sáng là băng cảnh báo không ai đọc.
    #
    # Chỉ chặn khi khai CÙNG LOẠI: một phương án khai nguồn là REQ thì nó tự quyết lấy
    # chuyện "REQ nào làm tôi lỗi thời", nhưng nó vẫn phải lỗi thời khi ADR đổi — chuyện
    # ấy nó chưa nói gì.
    khai_ro: set[str] = set()

    # Đường khai báo: ai ghi rằng mình phụ thuộc vào goc.
    for a in tat_ca:
        if a["id"] == artefact_id or a["type"] in KHONG_STALE:
            continue
        up = (a.get("deps") or {}).get("upstream") or []
        if artefact_id in up:
            ket.append(a["id"])
        elif any(loai_cua.get(u) == goc["type"] for u in up):
            khai_ro.add(a["id"])

    # Đường mặc định theo loại — cho những hiện vật CHƯA khai gì về loại này.
    for loai in HA_NGUON.get(goc["type"], ()):
        for a in store.list(loai, limit=500):
            if a["id"] != artefact_id and a["id"] not in ket and a["id"] not in khai_ro:
                ket.append(a["id"])

    return ket


# Loại hiện vật → cột trong ma trận truy vết. Năm cột này là thứ tab A2 dựng (M2-02);
# loại không có trong bảng thì không lên ma trận, vì một cột "khác" gộp mọi thứ lại thì
# không trả lời được câu hỏi nào.
_COT_TRUY_VET: dict[str, str] = {
    "option": "option", "adr": "adr", "code": "code",
    "criteria": "criteria", "sim_result": "ket_qua",
}


def ma_tran_truy_vet(store: Any) -> list[dict[str, Any]]:
    """Mỗi REQ một dòng: yêu cầu này đã được phương án / ADR / mã / tiêu chí nào đụng tới.

    Ba nguồn nối, vì dữ liệu nối REQ nằm ở ba chỗ khác nhau và không chỗ nào sai:

      * `deps.upstream` — lời khai chung, dùng được cho mọi loại;
      * `option.canonical.dap_ung_req` — phương án đã khai từ trước M2-01;
      * `criteria.canonical.assert[*].do_req` — tiêu chí khai theo từng assert.

    Dòng rỗng là một câu trả lời, không phải thiếu dữ liệu: REQ không có ai ở hạ nguồn là
    **REQ chưa ai làm**, và đó đúng là thứ cần nhìn thấy.
    """
    tat_ca = store.list(limit=2000)
    ra: list[dict[str, Any]] = []
    for rq in sorted((a for a in tat_ca if a["type"] == "req"), key=lambda a: a["id"]):
        dong: dict[str, Any] = {"req": rq["id"], "option": [], "adr": [], "code": [],
                                "criteria": [], "ket_qua": []}
        for a in tat_ca:
            cot = _COT_TRUY_VET.get(a["type"])
            if cot is None or a["id"] == rq["id"]:
                continue
            can = a.get("canonical") or {}
            noi = rq["id"] in ((a.get("deps") or {}).get("upstream") or [])
            if not noi and a["type"] == "option":
                noi = rq["id"] in (can.get("dap_ung_req") or [])
            if not noi and a["type"] == "criteria":
                noi = any(str(x.get("do_req") or "") == rq["id"]
                          for x in (can.get("assert") or []))
            if noi and a["id"] not in dong[cot]:
                dong[cot].append(a["id"])
        ra.append(dong)
    return ra


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
