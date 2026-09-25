# -*- coding: utf-8 -*-
"""Dựng SurfaceModel cho 10 bề mặt — EIDE-MDD-40 §D, §E2, §E7.

    I3  "Giao diện không quyết: chỉ render SurfaceModel/Card do lõi gửi"

Nghĩa là: mọi thứ người nhìn thấy trên tab đều phải được sinh **ở đây**, bằng mã, từ
kho thật. Giao diện không được tự nghĩ ra một dòng nào — kể cả dòng "chưa có gì".

Mã khối (`code`) dùng đúng mã trong `docs/review-v3/ui/ui_model.py` (A0–A14), để ma
trận ánh xạ hai chiều **yêu cầu ↔ giao diện** trong tệp Excel vẫn còn đúng khi mã chạy.

## Trạng thái rỗng phải trung thực

Đây là chỗ dễ nói dối nhất của một sản phẩm đang làm dở. Một tab "Thiết kế" trống trơn
khiến người dùng tưởng tính năng hỏng; một tab giả vờ có nội dung mẫu thì tệ hơn nhiều.
Quy tắc E3.2 §5 ("không giấu thất bại") ở đây thành: mỗi khối rỗng phải nói **ba** thứ —
hiện chưa có gì, vì sao chưa có, và cần gì để có.
"""

from __future__ import annotations

from typing import Any

from .protocol import uicommand as uic

# Mười bề mặt của §E7, kèm mã vùng trong ui_model.py.
SURFACES: list[tuple[str, str, str]] = [
    ("requirements", "A2", "Yêu cầu & Giải pháp"),
    ("documents", "A3", "Tài liệu & Nguồn"),
    ("knowledge", "A4", "Tri thức mạch"),
    ("design", "A5", "Thiết kế"),
    ("tools", "A6", "Công cụ"),
    ("code", "A7", "Mã nguồn"),
    ("simulation", "A8", "Mô phỏng"),
    ("hardware", "A9", "Mạch thật"),
    ("journal", "A10", "Nhật ký"),
    ("history", "A11", "Lịch sử"),
    ("project", "A14", "Dự án & Bộ nhớ"),
]


# Tên tầng tin cậy cho người đọc — §C1. Đây là bản dịch DUY NHẤT; giao diện tô màu
# theo mã (`VANG`/`BAC`/…), lõi hiện chữ theo bảng này.
_TIER_VI = {"VANG": "VÀNG", "BAC": "BẠC", "NGUOI": "NGƯỜI", "DONG": "ĐỒNG"}


def block(code: str, title: str, type: str, **kw: Any) -> dict[str, Any]:
    b: dict[str, Any] = {"id": code, "code": code, "title": title, "type": type}
    b.update({k: v for k, v in kw.items() if v is not None})
    return b


def khoi_hien_vat(code: str, title: str, type: str, a: dict[str, Any],
                  **kw: Any) -> dict[str, Any]:
    """Khối gắn với MỘT hiện vật — mang theo đủ lớp giải thích (§E2, §E3).

    Ba thứ đi kèm bắt buộc, và mỗi thứ trả lời một câu người thật sự hỏi:

      `explain`   "Vì sao lại thế?" — sáu trường đã lưu sẵn, nút bấm hiện ra **0 token**
      `diff_prev` "Khác bản trước ở đâu?" — §E3.2 §3 đòi hiện ngay dưới tóm tắt
      `tac_gia`   "Ai làm cái này?" — thanh tác giả người/tác tử trên mỗi hiện vật

    Không có ba thứ này thì hiện vật chỉ là dữ liệu; có chúng thì nó là một thứ người
    đọc được và cãi lại được.
    """
    ex = a.get("explain") or {}
    return block(
        code, title, type,
        summary=kw.pop("summary", None) or ex.get("summary"),
        explain=ex,
        phien_ban=a.get("version"),
        tac_gia="nguoi" if a.get("author") == "human" else "tac_tu",
        diff_prev=ex.get("diff_prev") if (a.get("version") or 1) > 1 else None,
        stale_reason=a.get("stale_reason"),
        artefact_id=a.get("id"),
        **kw)


def empty(code: str, title: str, *, chua_co: str, vi_sao: str, can_gi: str,
          buoc: str | None = None) -> dict[str, Any]:
    """Khối rỗng trung thực: hiện chưa có gì · vì sao · cần gì để có."""
    return block(code, title, "empty", chua_co=chua_co, vi_sao=vi_sao, can_gi=can_gi,
                 buoc=buoc)


# =========================================================================== từng bề mặt
def requirements(store: Any, inv: Any) -> dict[str, Any]:
    reqs = store.list("req", limit=200)
    opts = store.list("option", limit=20)
    blocks: list[dict[str, Any]] = []

    if reqs:
        blocks.append(block(
            "A2.1", "Đặc tả yêu cầu", "table",
            summary=f"{len(reqs)} yêu cầu, bản mới nhất v{max(r['version'] for r in reqs)}",
            columns=["Mã", "Yêu cầu", "Tiêu chí đo", "Trích lời anh", "Tầng", "Tác giả"],
            rows=[[r["id"], r["canonical"].get("text", ""),
                   r["canonical"].get("criteria", ""),
                   r["canonical"].get("source_quote", ""),
                   (r["explain"] or {}).get("confidence", ""),
                   "Anh" if r["author"] == "human" else "Tác tử"] for r in reqs],
            # §E2 cột "Người sửa được gì": bảng REQ cho sửa mô tả và tiêu chí inline,
            # kèm ô "vì sao". Giao diện đọc đúng danh sách này để biết ô nào cho gõ.
            editable_fields=["text", "criteria"],
            cot_sua={"Yêu cầu": "text", "Tiêu chí đo": "criteria"},
            # Mỗi dòng mang phiên bản và lớp giải thích riêng — nút "Vì sao?" trên
            # từng dòng chứ không phải trên cả bảng.
            row_meta={r["id"]: {"phien_ban": r["version"],
                                "tac_gia": "nguoi" if r["author"] == "human" else "tac_tu",
                                "explain": r["explain"],
                                "stale_reason": r["stale_reason"]} for r in reqs},
            stale=[r["id"] for r in reqs if r["stale"]]))
    else:
        blocks.append(empty(
            "A2.1", "Đặc tả yêu cầu",
            chua_co="Chưa có yêu cầu nào trong kho.",
            vi_sao="Tác tử chỉ ghi yêu cầu khi trích được đúng lời anh nói (N7) — "
                   "nó không tự bịa ra yêu cầu từ một câu mô tả chung.",
            can_gi="Nói cho tác tử biết anh muốn làm gì, rồi trả lời cụm câu hỏi làm rõ.",
            buoc="G3"))

    if opts:
        chon = next((o for o in opts if o["canonical"].get("da_chon")), None)
        blocks.append(block(
            "A2.3", "Phương án so sánh", "table",
            summary=(f"{len(opts)} phương án · "
                     + (f"đã chốt {chon['id']}" if chon else "CHƯA chốt phương án nào")),
            columns=["Mã", "Tên", "Kiến trúc", "Chi phí ước", "Độ khó", "Đáp ứng REQ",
                     "KHÔNG đáp ứng", "Rủi ro", "Chốt"],
            rows=[[o["id"], o["canonical"].get("ten", ""),
                   o["canonical"].get("kien_truc", ""),
                   o["canonical"].get("chi_phi_uoc", ""),
                   o["canonical"].get("do_kho", ""),
                   ", ".join(o["canonical"].get("dap_ung_req", [])),
                   ", ".join(o["canonical"].get("khong_dap_ung", [])),
                   "; ".join(o["canonical"].get("rui_ro", [])),
                   "★" if o["canonical"].get("da_chon") else ""] for o in opts],
            stale=[o["id"] for o in opts if o["stale"]]))
    else:
        blocks.append(empty(
            "A2.3", "Phương án so sánh",
            chua_co="Chưa có phương án nào.",
            vi_sao="Phương án dựng từ đặc tả yêu cầu; chưa có yêu cầu thì chưa có gì để so.",
            can_gi="Chốt đặc tả trước, rồi yêu cầu tác tử đề xuất 2–4 phương án."))

    adrs = store.list("adr", limit=50)
    if adrs:
        blocks.append(block(
            "A2.4", "Quyết định (ADR)", "table",
            summary=f"{len(adrs)} quyết định đã chốt — mỗi cái ghi ai quyết và hệ quả gì",
            columns=["Mã", "Quyết định", "Chọn", "Ai quyết", "Trích lời anh", "Hệ quả"],
            rows=[[a["id"], a["canonical"].get("tieu_de", ""),
                   a["canonical"].get("chon", ""),
                   "Anh" if a["canonical"].get("quyet_boi") == "nguoi" else "Tác tử",
                   a["canonical"].get("trich_loi_nguoi", ""),
                   "; ".join(a["canonical"].get("he_qua", []))] for a in adrs],
            stale=[a["id"] for a in adrs if a["stale"]]))
    else:
        blocks.append(empty(
            "A2.4", "Quyết định (ADR)",
            chua_co="Chưa có quyết định nào được ghi thành hiện vật.",
            vi_sao="Quyết định chốt trong hội thoại mà không ghi lại thì không có phiên "
                   "bản, không có hệ quả, và không đánh dấu được hạ nguồn khi đổi ý.",
            can_gi="Khi anh chốt một lựa chọn, tác tử sẽ ghi bằng store.adr_create."))
    return {"surface": "requirements", "code": "A2", "title": "Yêu cầu & Giải pháp",
            "blocks": blocks}


def documents(store: Any, inv: Any) -> dict[str, Any]:
    docs = store.list("doc", limit=100)
    khoi: list[dict[str, Any]] = []

    if docs:
        khoi.append(block(
            "A3.1", "Tài liệu đã nạp", "table",
            summary=f"{len(docs)} tài liệu · mọi Fact trích ra đều trỏ về số trang ở đây",
            columns=["Mã", "Tên", "Phiên bản", "Trang", "Nhà phát hành", "Hash"],
            rows=[[d["id"], d["canonical"].get("title", ""),
                   d["canonical"].get("version", "") or "—",
                   d["canonical"].get("pages", ""),
                   d["canonical"].get("publisher", "") or "—",
                   (d["canonical"].get("hash", "") or "")[:12]] for d in docs],
            row_meta={d["id"]: {"phien_ban": d["version"],
                                "tac_gia": "tac_tu", "explain": d["explain"]}
                      for d in docs}))

        # §C3 bước 7 — tài liệu có đoạn mang hình dạng mệnh lệnh thì phải hiện đỏ.
        tiem = [(d["id"], d["canonical"].get("prompt_injection") or []) for d in docs]
        tiem = [(i, c) for i, c in tiem if c]
        if tiem:
            khoi.append(block(
                "A3.3", "Cảnh báo tiêm lệnh", "list",
                summary="Tài liệu chứa văn bản giống chỉ dẫn cho tác tử — đọc như DỮ LIỆU",
                items=[f"{i}: {', '.join(c)}" for i, c in tiem]))
    else:
        khoi.append(empty(
            "A3.1", "Tài liệu & nguồn",
            chua_co="Chưa nạp datasheet hay tài liệu nào.",
            vi_sao="Không có tài liệu thì không có Fact, và không có Fact thì tác tử "
                   "không được dùng con số nào để quyết định hay sinh mã (N1).",
            can_gi="Kéo tệp PDF vào đây, hoặc bảo tác tử đi tìm rồi anh duyệt nguồn."))

    # A3.6 — ING-43 §8. Cây tệp sau phân loại: loại · mức hỗ trợ · VÌ SAO · độ tin cậy.
    #
    # Cột "vì sao" là cột đáng giá nhất ở đây. Một bảng chỉ có "tệp → loại" thì khi máy
    # đoán sai, người không có cách nào biết nó sai ở đâu; đọc được "zip có word/ →
    # DOCX" thì họ sửa được ngay bằng cách đưa đúng tệp.
    cls = store.list("classification", limit=100)
    if cls:
        hang = []
        for c in cls:
            k = c["canonical"]
            hang.append([k.get("path", c["id"]), k.get("mo_ta", ""),
                         k.get("muc_ho_tro_vi", ""), k.get("ly_do_phan_loai", ""),
                         f"{k.get('do_tin_cay', 1.0):.0%}",
                         k.get("ma_loi") or ("đọc được" if k.get("doc_duoc") else "—")])
        day_du = sum(1 for c in cls if c["canonical"].get("muc_ho_tro") == "day_du")
        khoi.append(block(
            "A3.6", "Nạp & trích xuất theo định dạng", "table",
            summary=(f"{len(cls)} tệp đã phân loại · {day_du} ở mức ĐẦY ĐỦ (trích Fact "
                     "tự động được) · còn lại phải anh xác nhận từng số"),
            columns=["Tệp", "Định dạng", "Mức hỗ trợ", "Vì sao xếp loại này",
                     "Độ tin cậy", "Trạng thái"],
            rows=hang,
            row_meta={c["id"]: {"phien_ban": c["version"], "tac_gia": "tac_tu",
                                "explain": c["explain"]} for c in cls}))

        # Gói nhiều tệp: người chọn nạp cái nào (ING-04).
        for c in cls:
            k = c["canonical"]
            if not k.get("can_chon"):
                continue
            khoi.append(block(
                f"A3.6.{c['id'][-4:]}", f"Trong gói {k.get('path', '')}", "table",
                summary=(f"{k.get('so_muc', 0)} tệp — quá nhiều để nạp hết. Anh chọn "
                         "tệp nào cần đọc; loại dưới đây là ĐOÁN theo đuôi, chưa mở ra."),
                columns=["Đường dẫn", "Loại đoán", "Mức hỗ trợ", "Kích thước"],
                rows=[[t["duong_dan"], t["loai_doan"], t["muc_ho_tro_vi"],
                       f"{t['kich_thuoc']:,} B" if t["kich_thuoc"] else "—"]
                      for t in (k.get("cay") or [])[:60]]))
    return {"surface": "documents", "code": "A3", "title": "Tài liệu & Nguồn",
            "blocks": khoi}


def knowledge(store: Any, inv: Any) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    if inv.passport:
        blocks.append(block("A4.1", "Hộ chiếu chip", "kv",
                            pairs=[["Chip", inv.passport], ["ISA", inv.isa or "chưa rõ"]]))
    else:
        blocks.append(empty(
            "A4.1", "Hộ chiếu chip",
            chua_co="Chưa ghim hộ chiếu chip nào.",
            vi_sao="Tác tử không ghim một cái tên chip trần khi chưa có tài liệu — "
                   "một câu trả lời sai tệ hơn một ô trống.",
            can_gi="Nạp datasheet của chip, hoặc cho tác tử tìm rồi anh duyệt nguồn.",
            buoc="G4"))

    facts = store.query_facts(limit=300)
    if facts:
        blocks.append(block(
            "A4.2", "Bảng Fact", "table",
            summary=" · ".join(f"{_TIER_VI.get(k, k)} {v}"
                               for k, v in inv.fact_tiers.items()),
            columns=["Thực thể", "Khoá", "Giá trị", "Đơn vị", "Tầng", "Nguồn"],
            rows=[[f["subject"], f["key"], f["value"] or "", f["unit"] or "",
                   f["tier"], _cite(f)] for f in facts]))

        # §C3 bước 5 — hàng đợi rà soát: BẠC là "nguồn đã duyệt, dòng chưa xác nhận".
        bac = [f for f in facts if f["tier"] == "BAC"]
        if bac:
            blocks.append(block(
                "A4.2b", "Hàng đợi rà soát Fact", "table",
                summary=(f"{len(bac)} Fact ở tầng BẠC chờ anh xác nhận từng dòng. "
                         "Xác nhận rồi mới lên VÀNG và dùng được để quyết định tự động."),
                columns=["Mã", "Khoá", "Giá trị", "Trang", "Trích đoạn nguyên văn"],
                rows=[[f["fact_id"], f["key"],
                       f"{f['value']} {f['unit'] or ''}".strip(),
                       _trang(f), _trich(f)] for f in bac[:40]]))

        nguoi = [f for f in facts if f["tier"] == "NGUOI"]
        if nguoi:
            blocks.append(block(
                "A4.2c", "Fact tầng NGƯỜI — anh cho, chưa có tài liệu", "table",
                summary=("Dùng được như VÀNG để so sánh và sinh mã, nhưng mọi nơi dùng "
                         "đều ghi rõ nguồn là lời anh. Nên tìm tài liệu để nâng lên VÀNG."),
                columns=["Khoá", "Giá trị", "Trích lời anh"],
                rows=[[f["key"], f"{f['value']} {f['unit'] or ''}".strip(), _trich(f)]
                      for f in nguoi]))
    else:
        blocks.append(empty(
            "A4.2", "Bảng Fact",
            chua_co="0 Fact. Chưa con số nào của dự án này truy vết được tới tài liệu.",
            vi_sao="Fact được trích từ datasheet anh duyệt, hoặc do chính anh khai "
                   "(khi đó nó mang tầng NGƯỜI và luôn hiện kèm 'chưa có tài liệu').",
            can_gi="Nạp tài liệu rồi rà soát bảng Fact ứng viên.",
            buoc="G4"))
    return {"surface": "knowledge", "code": "A4", "title": "Tri thức mạch", "blocks": blocks}


def _don_gian(surface: str, code: str, title: str, khoi: list[dict[str, Any]]):
    return {"surface": surface, "code": code, "title": title, "blocks": khoi}


def design(store: Any, inv: Any) -> dict[str, Any]:
    khoi: list[dict[str, Any]] = []

    bom = store.get("BOM")
    if bom:
        dong = bom["canonical"].get("dong", [])
        thieu = [d.get("ten") for d in dong if not d.get("datasheet")]
        khoi.append(block(
            "A5.4", "BOM — linh kiện đã chốt", "table",
            summary=(f"{len(dong)} dòng"
                     + (f" · {len(thieu)} linh kiện CHƯA có datasheet" if thieu else "")),
            columns=["Mã", "Linh kiện", "SL", "Lý do chọn", "Giá ước", "Datasheet"],
            rows=[[d.get("ma", ""), d.get("ten", ""), d.get("so_luong", 1),
                   d.get("ly_do", ""), d.get("gia_uoc", ""),
                   d.get("datasheet") or "CHƯA CÓ"] for d in dong],
            stale=["BOM"] if bom["stale"] else []))
    else:
        khoi.append(empty(
            "A5.4", "BOM — linh kiện đã chốt",
            chua_co="Chưa chốt linh kiện nào.",
            vi_sao="BOM là thứ anh cầm đi mua. Nó chỉ nên có khi phương án đã chốt, để "
                   "không mua nhầm theo một hướng sau đó bị bỏ.",
            can_gi="Chốt phương án, rồi bảo tác tử ghi danh sách linh kiện."))

    pinouts = store.list("pinout", limit=200)
    if pinouts:
        khoi.append(block(
            "A5.2", "Pinout", "table", columns=["Chân", "Chức năng", "Net"],
            rows=[[p["id"], p["canonical"].get("func", ""), p["canonical"].get("net", "")]
                  for p in pinouts]))
    else:
        khoi.append(empty(
            "A5.2", "Sơ đồ khối · Pinout · Netlist",
            chua_co="Chưa có sơ đồ hay bảng phân chân nào.",
            vi_sao="Tác tử từ chối vẽ sơ đồ từ phỏng đoán — sơ đồ phải dựng từ danh sách "
                   "module có thật, và pinout chỉ nhận chức năng chân có trong Fact.",
            can_gi="Nạp datasheet chip trước.", buoc="G4"))
    return _don_gian("design", "A5", "Thiết kế", khoi)


def tools_surface(store: Any, inv: Any) -> dict[str, Any]:
    return _don_gian("tools", "A6", "Công cụ", [empty(
        "A6.1", "Kiểm kê toolchain",
        chua_co="Chưa kiểm kê toolchain.",
        vi_sao="Việc dò toolchain, trình mô phỏng và bộ nạp thuộc bước G6.",
        can_gi="—", buoc="G6")])


def code_surface(store: Any, inv: Any) -> dict[str, Any]:
    """Tab Mã nguồn: tệp mã, script, và QUY TRÌNH gọi chúng.

    Vì sao quy trình nằm chung tab với script: một bước "chạy `scripts/setup.sh`" và
    chính tệp `setup.sh` là hai mặt của một việc. Tách chúng ra hai tab sẽ khiến người
    đọc quy trình phải nhớ đường dẫn rồi đi tìm — đúng kiểu ma sát mà E3.2 §4 nhắm tới
    khi đòi "chỉ ra chỗ cần người".
    """
    khoi: list[dict[str, Any]] = []
    files = store.list("code", limit=200) + store.list("config", limit=100)
    if files:
        khoi.append(block(
            "A7.1", "Tệp mã & script", "table",
            summary=f"{len(files)} tệp do tác tử hoặc anh ghi",
            columns=["Tệp", "Phiên bản", "Tác giả", "Tóm tắt", "Cần cập nhật"],
            rows=[[f["id"], f"v{f['version']}",
                   "Anh" if f["author"] == "human" else "Tác tử",
                   (f["explain"] or {}).get("summary", ""),
                   f["stale_reason"] or ""] for f in files],
            stale=[f["id"] for f in files if f["stale"]]))
    else:
        khoi.append(empty(
            "A7.1", "Tệp mã & script",
            chua_co="Chưa có tệp mã nào trong dự án.",
            vi_sao="Tác tử chỉ ghi tệp khi anh yêu cầu một việc cụ thể, và mọi hằng số "
                   "kỹ thuật trong đó phải truy vết được tới một nguồn có tên (N1).",
            can_gi="Bảo tác tử viết phần anh cần."))

    qt = store.list("procedure", limit=50)
    if qt:
        for a in qt:
            can = a["canonical"]
            td = can.get("tien_do") or {}
            xong = sum(1 for v in td.values() if v.get("trang_thai") == "xong")
            khoi.append(khoi_hien_vat(
                f"A7.5.{a['id']}", f"Quy trình: {can.get('tieu_de', a['id'])}",
                "procedure", a,
                summary=(f"{xong}/{len(can.get('buoc', []))} bước xong"
                         + (f" · chạy ở {can['chay_o_dau']}" if can.get("chay_o_dau") else "")),
                muc_dich=can.get("muc_dich", ""),
                can_truoc=can.get("can_truoc", []),
                buoc=[{**b, "trang_thai": (td.get(str(b.get("so"))) or {}).get("trang_thai", "")}
                      for b in can.get("buoc", [])],
                stale=[a["id"]] if a["stale"] else []))
    else:
        khoi.append(empty(
            "A7.5", "Quy trình từng bước",
            chua_co="Chưa có quy trình nào.",
            vi_sao="Khi tác tử hướng dẫn anh cài đặt hay triển khai, nó ghi thành một "
                   "quy trình có cấu trúc — mỗi bước có lệnh, kết quả mong đợi và cách "
                   "kiểm — chứ không phải một tệp văn bản để anh tự dò.",
            can_gi="Hỏi tác tử cách triển khai thứ anh vừa chốt."))
    return _don_gian("code", "A7", "Mã nguồn", khoi)


def simulation(store: Any, inv: Any) -> dict[str, Any]:
    return _don_gian("simulation", "A8", "Mô phỏng", [empty(
        "A8.1", "Tiêu chí & kết quả mô phỏng",
        chua_co="Chưa có tiêu chí và chưa chạy mô phỏng lần nào.",
        vi_sao="Nền biên dịch – mô phỏng thuộc bước G6. Tác tử sẽ nêu tiêu chí TRƯỚC khi "
               "chạy, và không bao giờ tuyên bố 'đạt' từ một log rỗng (N6).",
        can_gi="—", buoc="G6")])


def hardware(store: Any, inv: Any) -> dict[str, Any]:
    return _don_gian("hardware", "A9", "Mạch thật", [empty(
        "A9.1", "Dò board · Nạp · Gỡ lỗi",
        chua_co="Chưa kết nối bo mạch nào.",
        vi_sao="Năng lực chạm phần cứng thuộc bước G7. Mọi thao tác không đảo ngược "
               "(xoá Flash, option bytes, RDP, eFuse) đã có cổng chặn sẵn từ bây giờ.",
        can_gi="—", buoc="G7")])


def journal(ledger: Any, limit: int = 300) -> dict[str, Any]:
    """Nhật ký = hình chiếu sổ cái. Đây là bề mặt G1 điền được ĐẦY ĐỦ."""
    items = []
    for ev in ledger.read():
        items.append({"seq": ev.seq, "ts": ev.ts, "kind": ev.kind,
                      "tom_tat": _tom_tat_su_kien(ev)})
    ok, msg = ledger.verify()
    return _don_gian("journal", "A10", "Nhật ký", [
        block("A10.1", "Sổ cái", "timeline",
              summary=f"{len(items)} sự kiện · {msg}",
              integrity_ok=ok, items=items[-limit:]),
        block("A10.2", "Sự cố", "list",
              summary="Mạng, mô hình, quá hạn, sandbox",
              items=[f"{e.ts[:19]} · {e.data.get('code', e.data.get('kind', '?'))}: "
                     f"{e.data.get('message_vi', e.data.get('why', ''))[:160]}"
                     for e in ledger.read() if e.kind == "incident"] or
                    ["Chưa có sự cố nào."]),
    ])


def history(store: Any, inv: Any, hist: Any = None) -> dict[str, Any]:
    """Tab Lịch sử — §E2 dòng "Changeset", §E7 "Tab 10 Lịch sử"."""
    stale = store.list(stale_only=True, limit=100)
    khoi: list[dict[str, Any]] = []

    ds = hist.danh_sach(limit=80) if hist else []
    hien = [c for c in ds if not c["la_checkpoint"]]
    if hien:
        khoi.append(block(
            "A11.1", "Dòng thời gian changeset", "changesets",
            summary=(f"{len(hien)} thay đổi · "
                     f"{sum(1 for c in hien if c['cua_nguoi'])} của anh · "
                     f"{sum(1 for c in hien if not c['hoan_tac_duoc'])} không hoàn tác được"),
            items=hien,
            checkpoints=[c for c in ds if c["la_checkpoint"]]))
    else:
        khoi.append(empty(
            "A11.1", "Dòng thời gian changeset",
            chua_co="Chưa có thay đổi nào.",
            vi_sao="Tác tử chưa ghi gì và anh cũng chưa sửa gì. Mọi thay đổi — của ai "
                   "cũng vậy — sẽ hiện ở đây và hoàn tác được.",
            can_gi="Bảo tác tử làm một việc có ghi hiện vật, hoặc tự sửa một hiện vật."))

    snaps = hist.danh_sach_snapshot() if hist else []
    if snaps:
        khoi.append(block(
            "A11.2", "Bản ưng ý (snapshot)", "snapshots",
            summary=(f"{len(snaps)} bản · "
                     + (f"{sum(1 for s in snaps if s['kind'] == 'release')} release"
                        if any(s["kind"] == "release" for s in snaps)
                        else "chưa có bản release nào")),
            items=snaps,
            co_release=bool(hist and hist.snapshots.co_release())))
    else:
        khoi.append(empty(
            "A11.2", "Bản ưng ý (snapshot)",
            chua_co="Chưa ghi bản ưng ý nào.",
            vi_sao="Bản ưng ý là trạng thái anh đặt tên và quay về được bất cứ lúc nào. "
                   "Tác tử sẽ đề xuất ghi sau mỗi mốc đáng nhớ — nhưng anh đặt tên, vì "
                   "tên là thứ anh sẽ đọc lại sau này.",
            can_gi="Bảo tác tử ghi một bản, hoặc chờ nó tự đề xuất sau một mốc."))

    if hist:
        nhanh = hist.danh_sach_nhanh()
        if len(nhanh) > 1:
            khoi.append(block(
                "A11.3", "Nhánh", "list",
                summary=f"Đang ở nhánh “{hist.nhanh_hien_tai()}”",
                items=[f"{'▸ ' if n == hist.nhanh_hien_tai() else '  '}{n}"
                       for n in nhanh]))

    khoi.append(block(
        "A11.4", "Hiện vật STALE", "list",
        summary=f"{len(stale)} hiện vật cần cập nhật vì thượng nguồn đã đổi",
        items=[f"{a['id']} ({a['type']}): {a['stale_reason']}" for a in stale]
              or ["Không có hiện vật nào cần cập nhật."]))
    return _don_gian("history", "A11", "Lịch sử", khoi)


def project(eide_md: Any, inv: Any, assumptions: list[str]) -> dict[str, Any]:
    """Dự án & Bộ nhớ tác tử — bề mặt G1 điền được đầy đủ (ui_model A14).

    §A3 N3: bảng kiểm kê phải hiện cho NGƯỜI thấy đúng như tác tử thấy. Nếu người và
    mô hình nhìn hai bảng khác nhau thì không ai gỡ được lỗi khi tác tử hiểu sai dự án.
    """
    c = inv.counts
    return _don_gian("project", "A14", "Dự án & Bộ nhớ", [
        block("A14.2", "EIDE.md — bộ nhớ dài hạn", "sections",
              summary="Anh và tác tử cùng sửa tệp này; tác tử đọc nó mỗi lượt.",
              path=str(eide_md.path),
              sections=[{"ten": s, "than": eide_md.get(s)}
                        for s in eide_md.sections if eide_md.get(s)]),
        block("A14.3", "Kiểm kê — đúng bảng tác tử nhìn thấy", "kv",
              summary=f"Chặng {inv._stage()} · dựng bằng mã, 0 token, {inv.elapsed_ms:.1f} ms",
              pairs=[
                  ["Yêu cầu (REQ)", c.get("req", 0)],
                  ["Phương án", c.get("option", 0)],
                  ["ADR", c.get("adr", 0)],
                  ["Hộ chiếu chip", inv.passport or "CHƯA GHIM"],
                  ["Fact", f"{sum(inv.fact_tiers.values())} "
                           f"({' · '.join(f'{k} {v}' for k, v in inv.fact_tiers.items()) or '—'})"],
                  ["Tài liệu", len(inv.docs)],
                  ["Module · Netlist · Pinout · BOM",
                   f"{c.get('block_diagram', 0)} · {c.get('netlist', 0)} · "
                   f"{c.get('pinout', 0)} · {c.get('bom', 0)}"],
                  ["Mã · Build · Tiêu chí · Mô phỏng",
                   f"{c.get('code', 0)} · {c.get('build', 0)} · "
                   f"{c.get('criteria', 0)} · {c.get('sim_result', 0)}"],
                  ["Hiện vật STALE", len(inv.stale)],
                  ["Snapshot gần nhất", (inv.last_snapshot or {}).get("name", "chưa có")],
              ]),
        block("A14.3b", "Giả định đang dùng", "list",
              summary="Giả định phải được nói ra, không nằm ngầm trong hiện vật (N4)",
              items=assumptions or ["Không có giả định nào đang dùng."]),
    ])


# =========================================================================== thanh trạng thái
def status_bar(inv: Any, cfg: Any, *, run: dict[str, Any] | None = None) -> dict[str, Any]:
    """§E7 thanh trạng thái + ui_model A0."""
    b = cfg.budget
    return {
        "du_an": inv.project_name or "(chưa đặt tên)",
        "nhanh": inv.branch,
        "chip": inv.passport or "chưa ghim",
        "isa": inv.isa,
        "fact": dict(inv.fact_tiers),
        "chang": inv._stage(),
        "snapshot": (inv.last_snapshot or {}).get("name"),
        "khoang_cach_snapshot": inv.changesets_since_snapshot,
        "stale": len(inv.stale),
        "tu_chu": cfg.autonomy,
        "mo_hinh": cfg.model.main,
        "ngan_sach": {"tool": b.max_tool_calls, "giay": b.max_seconds,
                      "da_dung_tool": (run or {}).get("tool_calls", 0),
                      "da_dung_giay": (run or {}).get("seconds", 0)},
    }


# =========================================================================== phát tất cả
def emit_all(emit, *, store: Any, ledger: Any, eide_md: Any, inv: Any, cfg: Any,
             assumptions: list[str] | None = None, run: dict[str, Any] | None = None,
             only: list[str] | None = None, hist: Any = None) -> int:
    """Vẽ lại các bề mặt. Gọi cuối mỗi lượt và khi giao diện xin dựng lại toàn bộ."""
    models = {
        "requirements": lambda: requirements(store, inv),
        "documents": lambda: documents(store, inv),
        "knowledge": lambda: knowledge(store, inv),
        "design": lambda: design(store, inv),
        "tools": lambda: tools_surface(store, inv),
        "code": lambda: code_surface(store, inv),
        "simulation": lambda: simulation(store, inv),
        "hardware": lambda: hardware(store, inv),
        "journal": lambda: journal(ledger),
        "history": lambda: history(store, inv, hist),
        "project": lambda: project(eide_md, inv, assumptions or []),
    }
    n = 0
    for ten, dung in models.items():
        if only and ten not in only:
            continue
        emit(uic.surface_set(ten, dung()))
        n += 1
    emit(uic.ui_set("status_bar", status_bar(inv, cfg, run=run)))
    emit(uic.history_update(
        changesets=hist.danh_sach(limit=40) if hist else [],
        snapshots=hist.danh_sach_snapshot() if hist else [],
        stale=[{"id": a["id"], "type": a["type"], "ly_do": a["stale_reason"]}
               for a in store.list(stale_only=True, limit=50)]))
    return n


# =========================================================================== phụ
def _nguon(f: dict[str, Any]) -> dict[str, Any]:
    import json
    s = f.get("source")
    if isinstance(s, str):
        try:
            return json.loads(s)
        except ValueError:
            return {}
    return s or {}


def _trang(f: dict[str, Any]) -> str:
    s = _nguon(f)
    return str(s.get("page", "—"))


def _trich(f: dict[str, Any]) -> str:
    return (_nguon(f).get("quote") or "")[:120]


def _cite(f: dict[str, Any]) -> str:
    import json
    src = f.get("source")
    if isinstance(src, str):
        try:
            src = json.loads(src)
        except ValueError:
            return src
    src = src or {}
    if src.get("page"):
        return f"{src.get('doc_id', 'tài liệu')} tr.{src['page']}"
    if src.get("human_act_id"):
        return f"anh cho ({src['human_act_id']}), chưa có tài liệu"
    return "không rõ nguồn"


def _tom_tat_su_kien(ev: Any) -> str:
    d = ev.data
    return {
        "turn.start": lambda: f"Bắt đầu lượt {d.get('run_id')}: {(d.get('text') or '')[:70]}",
        "turn.end": lambda: (f"Kết thúc {d.get('run_id')} · {d.get('tool_calls', 0)} công cụ · "
                             f"{d.get('seconds', 0)} s"),
        "human_act": lambda: f"[{d.get('kind')}] {(d.get('text') or '')[:70]}",
        "ui_command": lambda: d.get("method", ""),
        "hook": lambda: (f"{d.get('hook', 'S0')}"
                         + (f" → {d.get('decision')}" if d.get("decision") else "")
                         + (f" ({', '.join(r['rule'] for r in d.get('rules', []))})"
                            if d.get("rules") else "")
                         + (f" · {d.get('tool')} → {d.get('action')}" if d.get("action") else "")),
        "llm_call": lambda: (f"{d.get('model')} · {d.get('usage', {}).get('in', 0)}→"
                             f"{d.get('usage', {}).get('out', 0)} token"
                             + (f" · gọi {', '.join(d.get('tool_calls', []))}"
                                if d.get("tool_calls") else "")),
        "tool_use": lambda: f"{d.get('tool')}({_args_ngan(d.get('args'))})",
        "tool_result": lambda: (f"{d.get('tool')} → "
                                + ("ok" if d.get("ok") else f"LỖI {d.get('code')}")),
        "gate": lambda: f"Cổng {d.get('gate')} [{d.get('gate_id')}] · {d.get('state')}",
        "incident": lambda: f"SỰ CỐ {d.get('code', d.get('kind', ''))}",
        "changeset": lambda: f"changeset {d.get('id')}",
        "note": lambda: str(d)[:70],
    }.get(ev.kind, lambda: str(d)[:70])()


def _args_ngan(args: Any, n: int = 60) -> str:
    if not isinstance(args, dict):
        return ""
    s = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return s if len(s) <= n else s[:n] + "…"
