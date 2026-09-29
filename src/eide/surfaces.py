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

from pathlib import Path
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
from .knowledge.compare import TEN_TANG_VI as _TIER_VI    # một nguồn sự thật (DEV-261)
from .knowledge.compare import ten_tang as _ten_tang


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


# Đuôi tệp của tài liệu TÁC TỬ LÀM RA (`doc.render`), khác với tài liệu người NẠP VÀO.
DUOI_TAO_RA = (".docx", ".pptx", ".xlsx", ".pdf")


def _tac_tu_lam_ra(d: dict[str, Any]) -> bool:
    """Hiện vật `doc` này là tệp tác tử làm ra, hay tài liệu người dùng nạp vào?

    Phân biệt bằng CẤU TRÚC, không bằng đuôi tệp: `doc.render` đăng ký qua `history.ghi_tep`
    nên canonical chỉ có `{path, sha, bytes}`; tài liệu nạp vào thì có `title`, `pages`,
    `publisher`. Một PDF datasheet cũng đuôi `.pdf`, nên dò theo đuôi sẽ nhầm.
    """
    c = d.get("canonical") or {}
    if c.get("title") or c.get("pages") or c.get("publisher"):
        return False
    duong = str(c.get("path") or "")
    return bool(duong) and duong.lower().endswith(DUOI_TAO_RA)


def _goc_du_an(cfg: Any) -> str:
    """Đường dẫn tuyệt đối tới thư mục dự án. Rỗng nếu không lấy được — chứ không đoán."""
    try:
        return str(Path(cfg.paths.project_root).resolve())
    except Exception:                                                  # noqa: BLE001
        return ""


def _co_tep(n: int) -> str:
    """Số byte → chữ người đọc. `48271` không nói được gì; `47 KB` thì nói được."""
    if n >= 1_048_576:
        return f"{n / 1_048_576:.1f} MB".replace(".", ",")
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


def documents(store: Any, inv: Any, goc: str = "") -> dict[str, Any]:
    tat_ca = store.list("doc", limit=100)
    lam_ra = [d for d in tat_ca if _tac_tu_lam_ra(d)]
    docs = [d for d in tat_ca if not _tac_tu_lam_ra(d)]
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
    # Tệp tác tử LÀM RA — khối riêng, và nói rõ NẰM Ở ĐÂU.
    #
    # Trước đây chúng lọt vào bảng "Tài liệu đã nạp" với mọi cột trống (không có phiên bản,
    # số trang, nhà phát hành — vì chúng không phải datasheet). Tệ hơn: **không chỗ nào trên
    # giao diện nói đường dẫn đầy đủ**, nên người dùng làm ra một tệp rồi đi tìm không thấy.
    # Anh Công hỏi đúng câu ấy ngày 29/09/2026: *"thư mục Agent sinh ra tài liệu nằm ở đâu?"*
    #
    # Một tệp làm ra mà người dùng không tìm thấy thì cũng bằng chưa làm.
    if lam_ra:
        khoi.append(block(
            "A3.2", "Tài liệu tác tử đã tạo", "table",
            summary=(f"{len(lam_ra)} tệp, nằm trong thư mục dự án"
                     + (f": {goc}" if goc else "")),
            columns=["Tệp", "Dạng", "Cỡ", "Đường dẫn đầy đủ"],
            rows=[[Path(d["canonical"]["path"]).name,
                   Path(d["canonical"]["path"]).suffix.lstrip(".").upper(),
                   _co_tep(d["canonical"].get("bytes") or 0),
                   str(Path(goc) / d["canonical"]["path"]) if goc
                   else d["canonical"]["path"]] for d in lam_ra],
            row_meta={d["id"]: {"phien_ban": d["version"], "tac_gia": "tac_tu",
                                "explain": d["explain"]} for d in lam_ra},
            note_vi=("Sửa NGUỒN `.md` rồi render lại, đừng sửa trong Word — bản render là "
                     "thứ dựng lại được, nguồn mới là thứ giữ lịch sử.")))

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

    khoi.extend(_khoi_ban_do_mach(store))
    khoi.extend(_khoi_so_do(store))
    return _don_gian("design", "A5", "Thiết kế", khoi)


# ============================================================ A5.8 — sơ đồ nguyên lý (SCH-44 §9)
def _khoi_so_do(store: Any) -> list[dict[str, Any]]:
    """Khối A5.8: ảnh sơ đồ · băng chất lượng bố cục · ký hiệu chờ xác nhận · mức render.

    Chỉ hiện khi CÓ hiện vật sơ đồ. Không có thì tab Thiết kế giữ nguyên hình dạng cũ — đó là
    điều kiện của cờ tính năng (§2.1 mục 2): cờ bật mà chưa ai sinh sơ đồ thì giao diện phải
    **không đổi một pixel nào**, nên ở đây không có cả ô trống trung thực.
    """
    bc = store.get("layout:mach")
    sym = store.get("symbol_map:mach")
    rp = store.get("report:sch-render")
    if not (bc or sym or rp):
        return []

    khoi: list[dict[str, Any]] = []

    if rp:
        c = rp["canonical"]
        tep = list(c.get("tep") or [])
        khoi.append(khoi_hien_vat(
            "A5.8", "Sơ đồ nguyên lý", "svg", rp,
            summary=(f"{len(tep)} trang · {c.get('so_ky_hieu', 0)} ký hiệu · "
                     f"{c.get('so_sheet', 0)} hộp sheet con"
                     + (" · " + "; ".join(c.get("canh_bao") or [])[:120]
                        if c.get("canh_bao") else "")),
            tep=tep, tep_chinh=(tep[0] if tep else None),
            ref=list(c.get("ref_trong_svg") or []),
            # Bấm ký hiệu → Fact/nguồn; bấm net → tô sáng (SCH-06/07). Giao diện gửi HumanAct,
            # lõi trả lời — không có logic thiết kế nào nằm trong Swift.
            bam_ky_hieu="Cho tôi xem Fact và nguồn của {ref}",
            bam_net="Tô sáng net {net} và cho tôi xem ERC liên quan"))

    if bc:
        c = bc["canonical"]
        tc = c.get("tieu_chi") or {}
        sheet = c.get("sheet") or {}
        hang = [["Cả trang (một tờ)", tc.get("kho", "?"), tc.get("so_ky_hieu", 0),
                 tc.get("cap_chong_nhau", 0), tc.get("day_cat_than", 0),
                 f"{(tc.get('ty_le_net_dung_nhan') or 0):.0%}",
                 "ĐẠT" if tc.get("dat") else "CHƯA: " + "; ".join(tc.get("vi_pham") or [])]]
        for pth, sb in sorted(sheet.items()):
            t = sb.get("tieu_chi") or {}
            hang.append([pth, t.get("kho", "?"), t.get("so_ky_hieu", 0),
                         t.get("cap_chong_nhau", 0), t.get("day_cat_than", 0),
                         f"{(t.get('ty_le_net_dung_nhan') or 0):.0%}",
                         "ĐẠT" if t.get("dat") else
                         "CHƯA: " + "; ".join(t.get("vi_pham") or [])])
        dn = c.get("de_nghi_phan_cap") or {}
        khoi.append(khoi_hien_vat(
            "A5.8b", "Chất lượng bố cục — đo bằng số", "table", bc,
            summary=("Mỗi dòng là một trang. " + (dn.get("vi") or "")),
            columns=["Trang", "Khổ", "Ký hiệu", "Cặp chồng nhau", "Dây cắt thân",
                     "Net dùng nhãn", "Tiêu chí"],
            rows=hang))

    if sym:
        c = sym["canonical"]
        cho = set(c.get("cho_xac_nhan") or [])
        xn = c.get("xac_nhan") or {}
        hang = []
        for k in (c.get("chi_tiet") or []):
            ai = xn.get(k["ref"]) or {}
            hang.append([
                k["ref"], k.get("ten", ""), k.get("lib") or "sinh từ Fact",
                k.get("so_chan", 0),
                ("—" if k.get("ty_khop") is None else f"{k['ty_khop']:.0%}"),
                k.get("nguon", ""),
                ("CHỜ ANH XEM" if k["ref"] in cho else
                 f"anh đã xác nhận: “{ai.get('trich_loi', '')[:60]}”" if ai else "không cần"),
                ", ".join(f"{c2['so']}={c2['kieu']}" for c2 in (k.get("chan") or [])[:6])])
        khoi.append(khoi_hien_vat(
            "A5.8c", "Ký hiệu linh kiện — xem và xác nhận", "table", sym,
            summary=(f"{len(hang)} ký hiệu"
                     + (f" · {len(cho)} CHỜ anh xem: kiểu chân ở đây là phép suy từ hướng "
                        "Port, và ERC trong KiCad dựa vào kiểu chân. Bấm vào ô kiểu chân để "
                        "sửa — lời anh viết ở ô “vì sao” thành Fact tầng NGƯỜI."
                        if cho else " · không còn cái nào chờ anh")),
            columns=["Ref", "Linh kiện", "Thư viện", "Số chân", "Khớp Fact", "Chân lấy từ đâu",
                     "Xác nhận", "Kiểu chân"],
            cot_sua={"Kiểu chân": "chan", "Xác nhận": "xac_nhan"},
            loai_sua="symbol",
            rows=hang))

    khoi.append(block(
        "A5.8d", "Mức render đang dùng", "kv",
        summary="Máy này KHÔNG cài KiCad — quyết định 25/09/2026.",
        pairs=[
            ["Đang dùng", ("R1 — renderer nội bộ của EIDE (SVG tự vẽ)" if rp
                           else "R3 — sơ đồ khối và đồ thị net của bản đồ mạch")],
            ["Muốn xem trong KiCad",
             "Xuất gói (sch.export) rồi mở ở máy có KiCad; sửa xong chép về và Nạp lại "
             "(sch.import)."],
            ["Vì sao không cài",
             "Cả đường ống chạy bằng Python thuần trong sandbox dự án, nên không có bước nào "
             "cần KiCad trên máy này."],
        ]))
    return khoi


def _khoi_ban_do_mach(store: Any) -> list[dict[str, Any]]:
    """Sơ đồ khối · Pinout · Netlist · CKM — dạng NGƯỜI của bản đồ tri thức mạch (§C2, E1).

    Mỗi bảng ở đây trả lời một câu §E2 ghi trong cột "Người đọc thấy gì", và cột tầng đi
    kèm từng dòng là chỗ quan trọng nhất: một chân gán theo lời người dùng và một chân gán
    theo datasheet KHÔNG được trông giống nhau trên màn hình.
    """
    from .knowledge import cay as _C
    from .knowledge import ckm as K

    ra: list[dict[str, Any]] = []

    # A5.9 — Cây khối phân cấp (HIER-45 §8). Đặt TRƯỚC sơ đồ khối vì từ HIER-45 cây là
    # hình dáng thật của mạch; bảng khối là một cách nhìn phẳng của cùng dữ liệu.
    ckm_a = store.get(K.MA_CKM)
    cay_chu = (ckm_a["canonical"].get("cay") or []) if ckm_a else []
    mg0 = store.get(K.MA_DO_THI)
    stale_nut = ((mg0["canonical"].get("stale_nut") or {}) if mg0 else {})
    con_da_doi = ((mg0["canonical"].get("con_da_doi") or {}) if mg0 else {})
    if cay_chu:
        vp = (ckm_a["canonical"].get("vi_pham_bat_bien") or [])
        sau = max((len([x for x in d.split("/") if x.strip()])
                   for d in cay_chu if d.strip().startswith("/")), default=0)
        ra.append(khoi_hien_vat(
            # Loại `cay`: giao diện có khối riêng vẽ cây gập/mở (A5.9.1). Vẫn gửi kèm
            # `columns`/`rows` để chỗ nào chỉ biết vẽ bảng thì vẫn đọc được — một khối mới
            # không được làm màn hình trống.
            "A5.9", "Cây khối phân cấp", "cay", ckm_a,
            summary=(f"{len(cay_chu)} nút · sâu {sau} cấp"
                     + (f" · {len(vp)} VI PHẠM bất biến cây" if vp else "")
                     + (f" · {len(stale_nut)} nút CẦN CẬP NHẬT" if stale_nut else "")
                     + (f" · quá mức khuyến nghị {_C.SAU_KHUYEN_NGHI} cấp, bố cục nên "
                        "chuyển sang sheet phân cấp" if sau > _C.SAU_KHUYEN_NGHI else "")),
            columns=["Nút", "Loại", "Port", "Net", "Tình trạng"],
            rows=[_hang_cay(d, stale_nut, con_da_doi) for d in cay_chu],
            # §6 — giao diện tô màu theo NÚT. Danh sách đường dẫn, không phải mã hiện vật.
            stale_nut=dict(stale_nut), con_da_doi=dict(con_da_doi),
            **_du_lieu_cay(store, cay_chu, ckm_a, stale_nut, con_da_doi),
            stale=[ckm_a["id"]] if ckm_a["stale"] else []))
        erc = (ckm_a["canonical"].get("erc") or [])
        if erc:
            nang = [x for x in erc if x.get("ket_luan") == "khong_dat"]
            cb = [x for x in erc if x.get("ket_luan") == "canh_bao"]
            thieu = [x for x in erc if x.get("ket_luan") == "chua_du_du_kien"]
            ra.append(block(
                "A5.9c", "Kiểm mạch theo cây (ERC)", "table",
                summary=(f"{len(nang)} lỗi chặn · {len(cb)} cảnh báo · "
                         f"{len(thieu)} chỗ CHƯA ĐỦ DỮ KIỆN · "
                         f"{len(erc) - len(nang) - len(cb) - len(thieu)} đạt"
                         + (" — 'chưa đủ dữ kiện' KHÔNG phải đạt" if thieu else "")),
                columns=["Khối", "Luật", "Kết luận", "Điều gì", "Cách sửa"],
                rows=[[x.get("path", ""), x.get("luat", ""),
                       _ket_luan_vi(x.get("ket_luan", "")), x.get("vi", ""),
                       x.get("cach_sua", "") or "—"]
                      for x in sorted(erc, key=_uu_tien_erc)]))
        if vp:
            ra.append(block(
                "A5.9b", "Vi phạm bất biến cây", "table",
                summary="Bản đồ chưa dùng được để sinh sơ đồ cho tới khi những chỗ này sạch.",
                columns=["Mã", "Chỗ", "Vấn đề", "Cách sửa"],
                rows=[[v.get("ma", ""), v.get("o_dau", ""), v.get("vi", ""),
                       v.get("goi_y", "")] for v in vp]))

    # A5.9d — khối lấy từ thư viện (HIER-45 §5). Hiện cả SỐ DẪN XUẤT và nguồn của nó: một
    # điện trở 609,76 Ω trên bảng mà không nói ra nó tính từ đâu thì người đọc chỉ có cách tin.
    if mg0 and (mg0["canonical"].get("khoi_thu_vien") or {}):
        dung = mg0["canonical"]["khoi_thu_vien"]
        hang: list[list[Any]] = []
        for khoi_ma, d in sorted(dung.items()):
            dx = d.get("dan_xuat") or {}
            hang.append([
                khoi_ma, d.get("ma", ""),
                {"du_an": "dự án", "nguoi_dung": "người dùng"}.get(d.get("tang", ""),
                                                                  d.get("tang", "")),
                "; ".join(f"{k}={v}" for k, v in sorted((d.get("tham_so") or {}).items()))
                or "—",
                "; ".join(f"{t} = {_so_dx(g)}" for t, g in sorted(dx.items())) or "—",
                "; ".join(f"{k}: {v}" for k, v in sorted((d.get("nguon") or {}).items()))
                or "CHƯA ghi nguồn",
                "; ".join(f"{a}→{b}" for a, b in
                          sorted((d.get("anh_xa_ref") or {}).items())) or "—",
            ])
        ra.append(khoi_hien_vat(
            "A5.9d", "Khối lấy từ thư viện", "table", mg0,
            summary=(f"{len(dung)} khối đặt từ thư viện — snapshot ghi lại "
                     "block@semver để bản ưng ý khôi phục được đúng phiên bản"),
            columns=["Khối trong mạch", "block@semver", "Tầng", "Tham số",
                     "Số dẫn xuất", "Nguồn tham số", "Ref đổi"],
            rows=hang))

    mg = store.get(K.MA_DO_THI)
    if mg:
        c = mg["canonical"]
        treo = c.get("tin_hieu_treo") or {}
        chua = treo.get("vao_khong_ai_cap") or []
        ra.append(khoi_hien_vat(
            # Loại `table`, KHÔNG phải `diagram`: giao diện chỉ vẽ những loại khối nó biết,
            # và một loại lạ hiện ra thành dòng "chưa biết vẽ khối loại…". Bảng là dạng
            # người đọc được NGAY; hình vẽ thuộc tính năng sinh sơ đồ (SCH-44, cờ riêng).
            "A5.1", "Sơ đồ khối", "table", mg,
            summary=(f"{c.get('so_khoi', 0)} khối · {len(c.get('canh') or [])} liên kết"
                     + (f" · {len(chua)} tín hiệu CHƯA ai cấp: " + ", ".join(chua[:6])
                        + " — hoặc còn thiếu khối, hoặc tên tín hiệu lệch nhau"
                        if chua else "")),
            columns=["Khối", "Việc", "Linh kiện", "Vào", "Ra", "Nguồn", "REQ"],
            rows=[[f"{m.get('ma')} {m.get('ten')}", m.get("muc_dich", ""),
                   ", ".join(m.get("linh_kien") or []) or "—",
                   ", ".join(m.get("tin_hieu_vao") or []) or "—",
                   ", ".join(m.get("tin_hieu_ra") or []) or "—",
                   m.get("rail") or "—", ", ".join(m.get("dap_ung_req") or []) or "—"]
                  for m in c.get("khoi") or []],
            stale=[mg["id"]] if mg["stale"] else []))
        mm = (mg.get("view_hint") or {}).get("text", "")
        if mm:
            ra.append(block(
                "A5.1b", "Sơ đồ khối — mã mermaid", "code", text=mm,
                summary="Dán được sang tài liệu hay trình xem mermaid. Do mã sinh từ bản "
                        "đồ, nên nó luôn khớp bảng trên."))

    pinouts = [p for p in store.list("pinout", limit=200) if p["canonical"].get("gan")]
    for p in pinouts:
        gan = p["canonical"].get("gan") or []
        nguoi = [g for g in gan if str(g.get("tier", "")).upper() == "NGUOI"]
        chua_kiem = [g for g in gan if not g.get("af_kiem_duoc")]
        ra.append(khoi_hien_vat(
            "A5.2", f"Pinout — {p['canonical'].get('chip', p['id'])}", "table", p,
            summary=(f"{len(gan)} chân đã gán"
                     + (f" · {len(nguoi)} theo lời anh, chưa có tài liệu" if nguoi else "")
                     + (f" · {len(chua_kiem)} chân KHÔNG kiểm được AF" if chua_kiem else "")),
            columns=["Chân", "Chức năng", "Net", "Tầng", "AF kiểm được", "Fact"],
            rows=[[g.get("chan", ""), g.get("chuc_nang", ""), g.get("net") or "—",
                   _tang_vi(g.get("tier", "")),
                   "có" if g.get("af_kiem_duoc") else "KHÔNG",
                   g.get("fact_id") or "—"] for g in gan],
            stale=[p["id"]] if p["stale"] else []))

    nl = store.get(K.MA_NETLIST)
    if nl:
        nets = nl["canonical"].get("net") or []
        mot = [n.get("ten") for n in nets if len(n.get("chan") or []) == 1]
        doan = [n.get("ten") for n in nets if n.get("loai_do_doan")]
        ra.append(khoi_hien_vat(
            "A5.3", "Netlist (bản đồ mạch)", "table", nl,
            summary=(f"{len(nets)} net"
                     + (f" · {len(mot)} net chỉ nối MỘT chân ({', '.join(mot[:6])}) — gần "
                        "như luôn là lỗi vẽ" if mot else "")
                     + (f" · {len(doan)} net loại do đoán theo tên" if doan else "")),
            columns=["Net", "Loại", "Áp", "Bus", "Số chân", "Chân"],
            rows=[[n.get("ten", ""),
                   n.get("loai", "") + (" (đoán)" if n.get("loai_do_doan") else ""),
                   n.get("ap_danh_dinh") or "—", n.get("bus") or "—",
                   len(n.get("chan") or []), ", ".join(n.get("chan") or [])[:120]]
                  for n in nets],
            stale=[nl["id"]] if nl["stale"] else []))

    ckm = store.get(K.MA_CKM)
    if ckm:
        c = ckm["canonical"]
        thieu = c.get("thieu") or []
        dut = c.get("cho_dut") or {}
        ra.append(khoi_hien_vat(
            "A5.5", "Bản đồ tri thức mạch — đủ chưa?", "table", ckm,
            summary=("Đủ tiền đề để sinh sơ đồ nguyên lý" if not thieu else
                     "CHƯA đủ để sinh sơ đồ: " + "; ".join(t["can"] for t in thieu)),
            columns=["Hạng mục", "Tình trạng"],
            rows=([["Thiếu: " + t["can"], "gọi " + t["goi"]] for t in thieu]
                  + [["Chân chưa gán chức năng", dut.get("so_chan_chua_gan", 0)],
                     ["Chân của linh kiện chưa có bảng chân",
                      dut.get("so_chan_khong_co_bang_chan", 0)],
                     ["Net nối một chân", ", ".join(dut.get("net_mot_chan") or []) or "—"],
                     ["Net chưa nối gì", ", ".join(dut.get("net_khong_chan") or []) or "—"],
                     ["Chip trong bản đồ",
                      ", ".join(x.get("ten", "") for x in c.get("chip") or []) or "—"]]),
            stale=[ckm["id"]] if ckm["stale"] else []))

    if not ra:
        ra.append(empty(
            "A5.2", "Sơ đồ khối · Pinout · Netlist",
            chua_co="Chưa có sơ đồ hay bảng phân chân nào.",
            vi_sao="Tác tử từ chối vẽ sơ đồ từ phỏng đoán — sơ đồ phải dựng từ danh sách "
                   "khối có thật, và pinout chỉ nhận chức năng chân có trong Fact.",
            can_gi="Nạp datasheet chip, rồi bảo tác tử chia khối và gán chân.", buoc="G4"))
    return ra


def _du_lieu_cay(store: Any, cay_chu: list[str], ckm_a: dict[str, Any],
                 stale_nut: dict[str, str], con_da_doi: dict[str, str]) -> dict[str, Any]:
    """Dữ liệu cho khối cây gập/mở: mỗi nút một bản ghi, kèm Port/net/ERC của CHÍNH nút đó.

    Gửi sẵn cả ba thứ thay vì để giao diện gọi lại: §E2 nói nút "Vì sao?" và các panel phụ
    phải hiện ra **0 token**. Người bấm vào một khối là muốn xem ngay, không phải chờ một
    lượt mô hình.
    """
    from .knowledge import cay as KC

    c = KC.Cay.doc(store)
    nut: list[dict[str, Any]] = []
    port_theo: dict[str, list[dict[str, Any]]] = {}
    net_theo: dict[str, list[str]] = {}
    for nid, n in c.nut.items():
        d = n.get("path")
        if not d or (n.get("kind") or "") not in KC.KIND:
            continue
        ports = [c.port[p] for p in c.port_cua.get(nid, [])]
        nets = [c.nut[x]["ten"] for x in c.con.get(nid, []) if c.nut[x]["loai"] == "net"]
        nut.append({
            "duong": d, "ten": n["ten"], "kind": n.get("kind") or "",
            "muc": KC.do_sau(d), "cha": (c.nut.get(n.get("parent_id") or "", {}) or {}).get("path", ""),
            "so_port": len(ports), "so_net": len(nets),
            "tier": n.get("tier") or "",
            "tinh_trang": ("stale" if d in stale_nut else
                           "con_da_doi" if d in con_da_doi else ""),
            "ly_do": stale_nut.get(d) or con_da_doi.get(d) or "",
        })
        port_theo[d] = [{"ten": p["ten"], "huong": p["huong"], "loai": p["loai"],
                         "chan": p.get("chan") or "",
                         "rang_buoc": "; ".join(f"{k}={v}" for k, v in
                                                sorted((p.get("rang_buoc") or {}).items()))}
                        for p in ports]
        if nets:
            net_theo[d] = sorted(nets)
    erc_theo: dict[str, list[dict[str, Any]]] = {}
    for x in (ckm_a["canonical"].get("erc") or []):
        erc_theo.setdefault(x.get("path", ""), []).append(x)
    return {"cay_nut": sorted(nut, key=lambda z: z["duong"]),
            "port_theo_nut": port_theo, "net_theo_nut": net_theo,
            "erc_theo_nut": erc_theo,
            "sau_khuyen_nghi": KC.SAU_KHUYEN_NGHI}


_KET_LUAN_VI = {"khong_dat": "LỖI CHẶN", "canh_bao": "cảnh báo",
                "chua_du_du_kien": "chưa đủ dữ kiện", "dat": "đạt"}


def _ket_luan_vi(ma: str) -> str:
    """"chưa đủ dữ kiện" phải đọc ra đúng là chưa kiểm được, không phải một mức độ nhẹ hơn
    của "đạt" (N6)."""
    return _KET_LUAN_VI.get(ma, ma or "?")


def _uu_tien_erc(x: dict[str, Any]) -> tuple[int, str, str]:
    """Xếp theo HẬU QUẢ, không theo thứ tự luật chạy: lỗi chặn lên trước."""
    thu = {"khong_dat": 0, "canh_bao": 1, "chua_du_du_kien": 2, "dat": 3}
    return (thu.get(x.get("ket_luan", ""), 9), x.get("path", ""), x.get("luat", ""))


def _so_dx(g: dict[str, Any]) -> str:
    """Số dẫn xuất kèm công thức — §5 "mọi số từ công thức có nguồn"."""
    v = g.get("gia_tri")
    s = f"{v:.6g}".replace(".", ",") if isinstance(v, (int, float)) else str(v)
    return f"{s} {g.get('don_vi', '')} ({g.get('cong_thuc', '')})".strip()


def _hang_cay(dong: str, stale_nut: dict[str, str] | None = None,
              con_da_doi: dict[str, str] | None = None) -> list[str]:
    """Một dòng cây dạng chữ → năm cột. Thụt đầu dòng giữ nguyên để người thấy phân cấp.

    Cột "Tình trạng" phân biệt hai thứ §6 cố ý tách: **cần cập nhật** (việc phải làm) và
    **con đã đổi** (chỉ thông tin). Gộp chúng là biến mười thông tin thành mười việc không
    có thật, và người sẽ học cách bỏ qua cả hai."""
    thut = len(dong) - len(dong.lstrip())
    than = dong.strip()
    if "[" in than and than.endswith("]"):
        duong, _, mo = than.partition("[")
        phan = [x.strip() for x in mo.rstrip("]").split("·")]
    else:
        duong, phan = than, []
    loai = phan[0] if phan else ""
    port = next((x for x in phan if "Port" in x or "chân" in x), "")
    net = next((x for x in phan if "net" in x), "")
    d = duong.strip()
    tt = ""
    if (stale_nut or {}).get(d):
        tt = "CẦN CẬP NHẬT — " + stale_nut[d]
    elif (con_da_doi or {}).get(d):
        tt = "con đã đổi (thông tin)"
    return [" " * thut + d, loai, port, net, tt]


def _tang_vi(ma: str) -> str:
    """Một nguồn sự thật cho tên tầng — xem DEV-261. Tầng lạ hiện nguyên mã, không nổ."""
    from .knowledge.compare import ten_tang
    return ten_tang(ma) if ma else "—"


def tools_surface(store: Any, inv: Any) -> dict[str, Any]:
    return _don_gian("tools", "A6", "Công cụ", [empty(
        "A6.1", "Kiểm kê toolchain",
        chua_co="Chưa kiểm kê toolchain.",
        vi_sao="Việc dò toolchain, trình mô phỏng và bộ nạp thuộc bước G6.",
        can_gi="—", buoc="G6")])


def _thanh(ty: float | None, rong: int = 12) -> str:
    """Thanh đặc/rỗng cho một tỉ lệ. §E2 đòi "thanh Flash/RAM so với Fact budget".

    Một con số phần trăm đọc được, nhưng "84 %" và "8 %" trông giống nhau khi lướt qua; một
    thanh thì không. Không biết ngân sách thì KHÔNG vẽ thanh — vẽ một thanh rỗng cho thứ
    chưa đo được là nói dối bằng hình.
    """
    if not ty or ty <= 0:
        return ""
    n = max(1, min(rong, int(round(ty * rong))))
    return "▰" * n + "▱" * (rong - n)


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

    # Kết quả biên dịch — `build.compile` ghi vào kho, và tab Mã nguồn là chỗ người đọc
    # tìm nó. Không hiện ở đây thì kích thước Flash/SRAM chỉ tồn tại trong một câu trả lời
    # đã trôi khỏi màn hình.
    for a in store.list("build", limit=5):
        c = a.get("canonical") or {}
        dat = bool(c.get("dat"))
        ty_f = c.get("ty_le_flash")
        ty_s = c.get("ty_le_sram")
        khoi.append(khoi_hien_vat(
            a["id"], "Kết quả biên dịch", "kv", a,
            summary=("ĐẠT" if dat else "KHÔNG ĐẠT") + " · " + str(c.get("cong_cu") or "?")
                    + (f" · {c.get('so_loi', 0)} lỗi, {c.get('so_canh_bao', 0)} cảnh báo"),
            pairs=[["Trạng thái", ("Biên dịch xong, có tệp ảnh trên đĩa" if dat else
                                  f"KHÔNG xong — {c.get('vi_sao_khong_dat', '')}")],
                   ["Chuỗi công cụ", str(c.get("cong_cu") or "—")],
                   ["Tệp ra", str(c.get("tep_ra") or "—")],
                   ["Flash", (f"{_thanh(ty_f)} {c.get('flash', 0)} B"
                              + (f" / {c.get('flash_toi_da')} B ({ty_f:.0%})" if ty_f
                                 else " (chưa biết hạn mức — chưa có Fact flash.size)"))],
                   ["SRAM", (f"{_thanh(ty_s)} {c.get('sram', 0)} B"
                             + (f" / {c.get('sram_toi_da')} B ({ty_s:.0%})" if ty_s
                                else " (chưa biết hạn mức — chưa có Fact ram.size)"))],
                   *([["Lỗi đầu tiên",
                       f"{x['tep']}:{x['dong']}:{x['cot']} {x['thong_diep']}"]
                      for x in (c.get("loi") or [])[:3]]),
                   *([["Cảnh báo", f"{x['tep']}:{x['dong']} {x['thong_diep']}"]
                      for x in (c.get("canh_bao") or [])[:3]])]))

    # Bản đồ bộ nhớ: symbol nào chiếm chỗ. Chỉ có ích khi firmware chật, nhưng lúc đó nó là
    # thứ duy nhất trả lời được "bỏ cái gì".
    for a in store.list("analysis", limit=3):
        c = a.get("canonical") or {}
        if not c.get("symbol"):
            continue
        khoi.append(khoi_hien_vat(
            a["id"], "Bản đồ bộ nhớ — cái gì chiếm chỗ", "table", a,
            summary=(f"Flash {c.get('flash', 0)} B · SRAM {c.get('sram', 0)} B · "
                     + ("; ".join(c.get("de_xuat") or []) or "còn trong ngân sách")),
            columns=["Symbol", "Byte", "Loại"],
            rows=[[x.get("ten", ""), x.get("byte", 0), x.get("loai", "")]
                  for x in (c.get("symbol") or [])[:12]]))

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
    """Tab Mô phỏng: kết quả `sim.run`, và **con số do chương trình mô phỏng in ra**.

    Bản trước luôn hiện ô trống "chưa chạy mô phỏng lần nào" — kể cả sau khi `sim.run` đã
    chạy thật và ghi hiện vật `sim_result` vào kho. Một công cụ ghi vào kho mà bề mặt không
    đọc là một nửa tính năng: người dùng chạy xong rồi nhìn vào chỗ đáng lẽ thấy kết quả và
    thấy chữ "chưa chạy lần nào".
    """
    khoi: list[dict[str, Any]] = []

    # Tiêu chí trước, kết quả sau — đúng thứ tự mà §C5 đòi ("tiêu chí nêu trước"). Đặt kết
    # quả lên trên thì người đọc thấy con số trước khi thấy thước đo nó.
    for a in store.list("criteria", limit=5):
        c = a.get("canonical") or {}
        ds_as = c.get("assert") or []
        xn = bool(c.get("xac_nhan_boi"))
        khoi.append(khoi_hien_vat(
            a["id"], f"Tiêu chí mô phỏng — {c.get('ma', '')}", "table", a,
            summary=(f"{len(ds_as)} tiêu chí · "
                     + ("anh đã xác nhận: “" + str(c.get("trich_loi", ""))[:70] + "”"
                        if xn else
                        "CHƯA xác nhận — mô phỏng sẽ không chạy tới khi anh duyệt bảng này")
                     + (f" · {len(c.get('khong_mo_phong_duoc') or [])} phần KHÔNG mô phỏng "
                        "được" if c.get("khong_mo_phong_duoc") else "")),
            columns=["Mã", "Đo gì", "Phép so", "Ngưỡng", "Đơn vị", "Đo yêu cầu nào",
                     "Ngưỡng lấy từ đâu"],
            cot_sua={"Ngưỡng": "nguong"},
            loai_sua="criteria",
            rows=[[x.get("ma", ""), x.get("mo_ta", ""), x.get("phep_so", ""),
                   (f"{x.get('nguong')}–{x.get('nguong_tren')}"
                    if x.get("phep_so") == "trong_khoang" else str(x.get("nguong", ""))),
                   x.get("don_vi", ""), x.get("do_req", "") or "— chưa gắn REQ —",
                   x.get("nguon_nguong", "") or "— CHƯA NÓI NGUỒN —"]
                  for x in ds_as]))
        if c.get("khong_mo_phong_duoc"):
            khoi.append(block(
                a["id"] + ":khong-mo-phong", "Phần KHÔNG mô phỏng được", "table",
                summary=("Những phần dưới đây nằm NGOÀI mọi kết luận “đạt” của mô phỏng — "
                         "chúng phải được đo trên bo thật."),
                columns=["Cái gì", "Vì sao không mô phỏng được", "Bù bằng cách nào"],
                rows=[[x.get("gi", ""), x.get("vi_sao", ""), x.get("cach_bu", "")]
                      for x in c["khong_mo_phong_duoc"]]))

    ds = store.list("sim_result", limit=10)
    if not ds:
        khoi.append(empty(
            "A8.1", "Kết quả mô phỏng",
            chua_co="Chưa chạy mô phỏng lần nào.",
            vi_sao="Tác tử nêu tiêu chí TRƯỚC khi chạy, và không bao giờ tuyên bố 'đạt' từ "
                   "một log rỗng (N6).",
            can_gi="Bảo tác tử mô phỏng vòng điều khiển (sim.run) sau khi đã có mã.",
            buoc="G6"))
        return _don_gian("simulation", "A8", "Mô phỏng", khoi)

    for a in ds:
        c = a.get("canonical") or {}
        kq = c.get("ket_qua") or {}
        dat = bool(c.get("dat"))
        # Từng tiêu chí một, kèm kết luận của nó — không gộp thành một con số.
        if (c.get("xet") or {}).get("dong"):
            khoi.append(block(
                a["id"] + ":xet", f"Từng tiêu chí — {a['id'].split(':')[-1]}", "table",
                summary=("Kết luận của mỗi dòng do SO SỐ ĐO với ngưỡng, không do chương "
                         "trình mô phỏng tự tuyên bố."),
                columns=["Mã", "Đo gì", "Kết luận", "Số đo so với ngưỡng", "Đo REQ nào"],
                rows=[[d.get("ma", ""), d.get("mo_ta", ""),
                       {"dat": "ĐẠT", "khong_dat": "KHÔNG ĐẠT",
                        "chua_do_duoc": "CHƯA ĐO ĐƯỢC"}.get(d.get("ket_luan"),
                                                            str(d.get("ket_luan"))),
                       d.get("vi", ""), d.get("do_req", "")]
                      for d in c["xet"]["dong"]]))
        khoi.append(khoi_hien_vat(
            a["id"], f"Kết quả mô phỏng — {a['id'].split(':')[-1]}", "kv", a,
            summary=(("ĐẠT" if dat else "CHƯA ĐẠT") + " · "
                     + (str(c.get("vi_sao_khong_dat")) if not dat else "")
                     + f" · chạy trên {len(c.get('tep_nguon') or [])} tệp nguồn"),
            pairs=[["Kết luận", ("ĐẠT — theo đúng tiêu chí mà chương trình mô phỏng tự kiểm"
                                if dat else
                                f"CHƯA ĐẠT — {c.get('vi_sao_khong_dat', '')}")],
                   *[[str(k), _loi_nguoi(v)] for k, v in sorted(kq.items()) if k != "dat"],
                   ["Chạy trên mã nào", ", ".join(c.get("tep_nguon") or []) or "—"],
                   ["Giới hạn",
                    "Đây là kết quả trên MÔ HÌNH: nó nói mã điều khiển tự nhất quán và ổn "
                    "định được với mô hình đó, KHÔNG nói mạch thật sẽ chạy. Tham số cơ khí "
                    "thật phải đo trên bo."]]))
    return _don_gian("simulation", "A8", "Mô phỏng", khoi)



def _loi_nguoi(v: Any) -> str:
    """Một giá trị bất kỳ → một dòng NGƯỜI đọc được. Không bao giờ trả `str(dict)`.

    Đo được ngày 29/09/2026 bằng bộ quét giao diện: khối `sim_result:can-bang` hiện nguyên
    một danh sách dict Python lên màn — `[{'ten': 'A1 khoi tao…', 'dat': True, …}]`. Chỗ hỏng
    là một dòng dựng bảng gọi `str(v)` cho MỌI giá trị, nên giá trị vô hướng thì đẹp còn giá
    trị có cấu trúc thì lộ nguyên ruột.

    Đây đúng thứ N8 cấm: mọi thứ tác tử làm ra phải có **dạng người hiểu được**. Một dòng
    `{'do_duoc': False, 'vi_sao': '…'}` không phải một dạng người hiểu được — nó là dạng máy
    bị bỏ quên trên đường ra màn hình.

    Quy ước: danh sách ca kiểm thì nói **bao nhiêu đạt trên bao nhiêu**, vì đó là câu người
    đọc muốn biết; danh sách khác thì đếm; dict thì trải các trường vô hướng.
    """
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "có" if v else "không"
    if isinstance(v, (int, float, str)):
        return str(v)
    if isinstance(v, (list, tuple)):
        if not v:
            return "—"
        if all(isinstance(x, (str, int, float)) for x in v):
            return ", ".join(str(x) for x in v)
        if all(isinstance(x, dict) for x in v) and any("dat" in x for x in v):
            n = sum(1 for x in v if x.get("dat") is True)
            return f"{n}/{len(v)} đạt"
        return f"{len(v)} mục"
    if isinstance(v, dict):
        if not v:
            return "—"
        vo_huong = [f"{k}: {v[k]}" for k in sorted(v)
                    if isinstance(v[k], (str, int, float, bool)) and str(v[k]).strip()]
        return " · ".join(vo_huong) if vo_huong else f"{len(v)} trường"
    return str(v)

def hardware(store: Any, inv: Any) -> dict[str, Any]:
    """Tab Mạch thật — §E7 dòng "Dò board / nạp / verify".

    Cột bắt buộc của dòng đó: *"Nạp gì (hash, kích thước) vào đâu; verify thế nào; nếu không
    khớp thì vì sao dừng"*. Nên khối nạp ở đây không được rút gọn thành "đã nạp xong": nó phải
    mang theo hash, số byte, đích, và **verify hay không verify** — vì "đã nạp" mà không verify
    là một câu đúng chữ nhưng dẫn tới một kết luận sai về việc chip đang chạy bản nào.
    """
    khoi: list[dict[str, Any]] = []

    for a in store.list("target", limit=10):
        c = a.get("canonical") or {}
        if "cach" in c:                                        # bản ghi NẠP
            dat = bool(c.get("dat"))
            khoi.append(khoi_hien_vat(
                a["id"], "Nạp firmware vào bo", "kv", a,
                summary=("ĐÃ NẠP" if dat else "KHÔNG NẠP ĐƯỢC")
                        + f" · {c.get('cach') or '?'}"
                        + (" · đã verify" if c.get("da_verify") else " · CHƯA verify"),
                pairs=[
                    ["Nạp gì", f"{c.get('tep') or '?'} · {c.get('so_byte') or 0} B"],
                    ["sha256", str(c.get("hash") or "")[:16] or "—"],
                    ["Vào đâu", str(c.get("dich") or "—")],
                    ["Chip dự án ghim", str(c.get("chip_du_an") or "—")],
                    ["Chip đã đối chiếu",
                     str(c.get("chip_da_doi_chieu")
                         or "CHƯA đối chiếu bằng ID đọc từ silicon")],
                    ["Nhãn ổ của bộ nạp", str(c.get("chip_theo_nhan_o") or "—")],
                    ["Verify", "Trình nạp đã đọc lại và so khớp"
                     if c.get("da_verify") else
                     "KHÔNG verify — chưa có bằng chứng nội dung trên chip đúng bản này"],
                    ["Thời gian", f"{c.get('giay') or 0} s"],
                    ["Hoàn tác được", "KHÔNG — " + str(c.get("vi_sao_khong_hoan_tac") or "")],
                ] + ([["Vì sao dừng", str(c.get("vi_sao_khong_dat"))]] if not dat else [])
                  + [["Cảnh báo", x] for x in (c.get("canh_bao") or [])]))
        elif "cong" in c:                                      # bản ghi ĐỌC LOG
            im = bool(c.get("im_lang"))
            khoi.append(khoi_hien_vat(
                a["id"], "Log từ bo", "log", a,
                summary=(f"{c.get('so_byte') or 0} B từ {c.get('cong')} "
                         f"ở {c.get('baud')} baud"
                         + (" · IM LẶNG" if im else "")),
                # Nguyên văn, không tóm tắt: log là bằng chứng, và một bản tóm tắt log là
                # lời của người tóm tắt, không phải của bo.
                noi_dung=str(c.get("chu") or ""),
                canh_bao=list(c.get("canh_bao") or [])))

    if not khoi:
        khoi.append(empty(
            "A9.1", "Dò board · Nạp · Gỡ lỗi",
            chua_co="Chưa nạp gì lên bo trong dự án này.",
            vi_sao="Nạp là thao tác KHÔNG hoàn tác được — bản firmware đang chạy trên chip bị "
                   "ghi đè — nên nó chỉ xảy ra khi anh duyệt thẻ cổng G-FLASH.",
            can_gi="Cắm bo rồi bảo tác tử dò (target.detect) và nạp (target.flash)."))
    return _don_gian("hardware", "A9", "Mạch thật", khoi)


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


def bo_nho(eide_md: Any, *, ngu_canh: dict[str, Any] | None = None,
           tom_tat: Any = None, ghim: list[dict[str, Any]] | None = None,
           nhat_ky_nen: list[dict[str, Any]] | None = None,
           bo_nho_nguoi: Any = None, da_quen: list[dict[str, Any]] | None = None
           ) -> list[dict[str, Any]]:
    """Khối A14.6 — Bộ nhớ tác tử. EIDE-MEM-42 §11.

    Nguyên tắc P6: **người thấy và sửa được bộ nhớ tác tử.** Không có mặt bằng này thì
    "tác tử nhớ gì" là một hộp đen, và khi nó quên một thứ thì người chỉ có thể đoán là
    do ngữ cảnh đầy hay do mô hình kém.
    """
    khoi: list[dict[str, Any]] = []

    # --- Đồng hồ ngữ cảnh theo khối.
    nc = ngu_canh or {}
    if nc.get("cua_so"):
        khoi.append(block(
            "A14.6.1", "Ngữ cảnh đang dùng", "table",
            summary=(f"{nc['tong']:,} / {nc['cua_so']:,} token "
                     f"({nc['ty_le'] * 100:.0f} %) · mức {nc['muc']} · "
                     f"dùng được {nc['kha_dung']:,} sau khi trừ 20 % dự trữ"),
            columns=["Khối", "Token", "Trần", "Vượt?"],
            rows=[[k["ten"], f"{k['token']:,}",
                   f"{k['tran']:,}" if k.get("tran") else "—",
                   "VƯỢT" if k.get("vuot") else ""] for k in nc.get("khoi", [])]))

    # --- Bản tóm tắt phiên: xem và SỬA được (MEM-11).
    if tom_tat is not None:
        from .memory.summary import MUC
        khoi.append(block(
            "A14.6.2", "Bản tóm tắt phiên", "sections",
            summary="Đây là thứ thay cho phần hội thoại đã nén. Anh sửa được — sửa xong "
                    "lượt sau tác tử dùng bản của anh.",
            sections=[{"ten": t, "than": tom_tat.muc.get(t, "—")} for t, _, _ in MUC],
            cot_sua={t: t for t, _, _ in MUC}))
    else:
        khoi.append(empty(
            "A14.6.2", "Bản tóm tắt phiên",
            chua_co="Chưa nén lần nào nên chưa có bản tóm tắt.",
            vi_sao="Ngữ cảnh chưa chạm ngưỡng 70 %. Tới đó tác tử sẽ tóm tắt phần cũ "
                   "theo mười mục cố định, rồi tự kiểm lại xem có mất gì không.",
            can_gi="Không cần làm gì — đây là trạng thái bình thường."))

    # --- Nhật ký nén: trước/sau, kiểm mấy trên mấy.
    nk = nhat_ky_nen or []
    if nk:
        khoi.append(block(
            "A14.6.3", "Nhật ký nén", "table",
            summary=(f"{len(nk)} lần nén · "
                     f"{sum(1 for n in nk if n.get('ok'))} lần qua kiểm"),
            columns=["Mức", "Trước", "Sau", "Kiểm", "Số lần thử", "Kết quả"],
            rows=[[n.get("muc", ""), f"{n.get('truoc', 0):,}", f"{n.get('sau', 0):,}",
                   n.get("kiem", ""), n.get("so_lan_thu", 1),
                   "đạt" if n.get("ok") else f"HUỶ — {n.get('ly_do', '')[:60]}"]
                  for n in nk[-10:]]))

    # --- Message được ghim: không bao giờ bị nén.
    g = ghim or []
    if g:
        khoi.append(block(
            "A14.6.4", "Đang ghim (không bao giờ bị nén)", "list",
            summary=f"{len(g)} thông điệp · ghim theo Ý CHÍ của anh, không theo độ mới",
            items=[f"[{x.get('vi_sao', '?')}] {x.get('chu', '')[:120]}" for x in g]))

    # --- Bộ nhớ người dùng (M3).
    if bo_nho_nguoi is not None:
        ds = bo_nho_nguoi.doc()
        if ds:
            khoi.append(block(
                "A14.6.5", "Bộ nhớ về anh (dùng chung mọi dự án)", "table",
                summary=f"{len(ds)} dòng · {bo_nho_nguoi.path}",
                columns=["Chủ đề", "Nội dung"],
                rows=[[m["chu_de"], m["dong"]] for m in ds]))
        else:
            khoi.append(empty(
                "A14.6.5", "Bộ nhớ về anh (dùng chung mọi dự án)",
                chua_co="Chưa nhớ gì về anh.",
                vi_sao="Tác tử chỉ ĐỀ XUẤT nhớ khi anh lặp lại một sở thích từ hai lần "
                       "trở lên, và chỉ ghi khi anh bấm đồng ý. Nó không bao giờ nhớ "
                       "khoá, mật khẩu, hay nhận xét về anh.",
                can_gi="Không cần làm gì."))

    # --- Đã quên có chủ đích.
    dq = da_quen or []
    if dq:
        khoi.append(block(
            "A14.6.6", "Đã quên theo yêu cầu của anh", "list",
            summary=f"{len(dq)} điều · tác tử không được nhắc lại, kể cả từ hội thoại cũ",
            items=[f"{t.get('section', '')}: {t.get('noi_dung', '')}" for t in dq]))

    # --- Cảnh báo EIDE.md vượt trần + đề xuất lược.
    if eide_md is not None and getattr(eide_md, "qua_tran", False):
        de = eide_md.de_xuat_luoc()
        khoi.append(block(
            "A14.6.7", "EIDE.md vượt trần", "table",
            summary=(f"{eide_md.so_token:,} token / trần 3 000. Tác tử KHÔNG tự xoá — "
                     "anh duyệt thì nó lược."),
            columns=["Mục", "Số dòng lược được", "Vì sao"],
            rows=[[d["muc"], d["so_dong"], d["vi_sao"]] for d in de]))
    return khoi


def project(eide_md: Any, inv: Any, assumptions: list[str], **kw: Any) -> dict[str, Any]:
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
    ] + bo_nho(eide_md, **kw))


# =========================================================================== thanh trạng thái
def status_bar(inv: Any, cfg: Any, *, run: dict[str, Any] | None = None,
               ngu_canh: dict[str, Any] | None = None) -> dict[str, Any]:
    """§E7 thanh trạng thái + ui_model A0 + đồng hồ ngữ cảnh A14.6 (MEM-02)."""
    b = cfg.budget
    return {
        "ngu_canh": ngu_canh or {},
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
def dong_ho_ngu_canh(asm: Any, messages: list[Any], cfg: Any) -> dict[str, Any]:
    """MEM-42 §4.1–4.2 — đồng hồ token theo khối, bốn ngưỡng, dự trữ 20 %.

    Người nhìn thanh này để biết vì sao tác tử "quên": không phải nó kém trí nhớ, mà là
    một khối cụ thể đã chạm trần. Không có bảng này thì "ngữ cảnh đầy" là một lời giải
    thích không kiểm được.
    """
    cb = cfg.context_budget
    cua_so = cfg.model.context_window
    tran = {"constitution": cb.constitution, "eide_md": cb.eide_md,
            "inventory": cb.inventory, "facts": cb.facts,
            "human_edits": cb.human_edits, "pending": cb.pending,
            "skills_hint": cb.skills_hint}
    khoi = []
    for ten, cap in tran.items():
        dung = int((getattr(asm, "tokens", {}) or {}).get(ten, 0))
        khoi.append({"ten": ten, "token": dung, "tran": cap,
                     "vuot": dung > cap})
    transcript = sum(len(str(m)) // 3 for m in messages)
    khoi.append({"ten": "transcript", "token": transcript, "tran": None, "vuot": False})
    du_tru = cb.du_tru(cua_so)
    khoi.append({"ten": "dự trữ (bất khả xâm phạm)", "token": du_tru,
                 "tran": du_tru, "vuot": False})

    tong = sum(k["token"] for k in khoi)
    ty_le = tong / max(1, cua_so)
    return {"khoi": khoi, "tong": tong, "cua_so": cua_so,
            "ty_le": round(ty_le, 3), "muc": cb.muc_nen(ty_le),
            "nguong": {"C1": cb.nguong_c1, "C2": cb.nguong_c2,
                       "C3": cb.nguong_c3, "C4": cb.nguong_c4},
            "kha_dung": cb.kha_dung(cua_so)}


def emit_all(emit, *, store: Any, ledger: Any, eide_md: Any, inv: Any, cfg: Any,
             assumptions: list[str] | None = None, run: dict[str, Any] | None = None,
             only: list[str] | None = None, hist: Any = None,
             ngu_canh: dict[str, Any] | None = None,
             bo_nho_kw: dict[str, Any] | None = None) -> int:
    """Vẽ lại các bề mặt. Gọi cuối mỗi lượt và khi giao diện xin dựng lại toàn bộ."""
    models = {
        "requirements": lambda: requirements(store, inv),
        "documents": lambda: documents(store, inv, _goc_du_an(cfg)),
        "knowledge": lambda: knowledge(store, inv),
        "design": lambda: design(store, inv),
        "tools": lambda: tools_surface(store, inv),
        "code": lambda: code_surface(store, inv),
        "simulation": lambda: simulation(store, inv),
        "hardware": lambda: hardware(store, inv),
        "journal": lambda: journal(ledger),
        "history": lambda: history(store, inv, hist),
        "project": lambda: project(eide_md, inv, assumptions or [], **(bo_nho_kw or {})),
    }
    n = 0
    for ten, dung in models.items():
        if only and ten not in only:
            continue
        emit(uic.surface_set(ten, dung()))
        n += 1
    emit(uic.ui_set("status_bar", status_bar(inv, cfg, run=run, ngu_canh=ngu_canh)))
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
