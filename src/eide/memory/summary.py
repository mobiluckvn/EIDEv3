# -*- coding: utf-8 -*-
"""Bản tóm tắt phiên và phiếu kiểm sau nén — EIDE-MEM-42 §6.2, §6.6.

Hai thứ ở đây đi liền nhau và chỉ có nghĩa khi đi cùng:

- **Lược đồ 10 mục.** Tóm tắt tự do thì mỗi lần nén mất một thứ khác nhau, và không ai
  biết đã mất gì. Lược đồ buộc mô hình trả lời đúng mười câu hỏi, mục nào không có nội
  dung thì ghi "—" chứ **không bỏ** — một ô "—" là một thông tin ("phiên này chưa quyết
  gì"), một mục biến mất thì không.
- **Phiếu kiểm.** Ba câu hỏi sinh **bằng mã** từ sổ cái, hỏi lại trên ngữ cảnh ĐÃ NÉN,
  so khớp **bằng mã** (id/khoá/giá trị, không so văn phong). Sai một câu là huỷ nén.

Vì sao phần kiểm quan trọng hơn phần tóm tắt: không có nó thì "nén có làm mất gì không"
mãi là câu hỏi cảm tính, và cách duy nhất phát hiện là người dùng phải nhắc lại một
quyết định họ đã nói — tức là ta để người đi phát hiện lỗi của mình (TC074).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

# §6.2.2 — mười mục, mỗi mục một trần token. Trần nằm ở đây chứ không ở prompt, vì một
# con số trong lời dặn là một đề nghị; một con số trong mã là một ràng buộc.
MUC: list[tuple[str, str, int]] = [
    ("muc_tieu", "1–2 câu: dự án làm gì, người muốn gì trong phiên này", 80),
    ("trang_thai_theo_chang", "C1..C7: xong|đang|chưa + một dòng", 150),
    ("quyet_dinh", "[{adr_id|'chưa ghi', noi_dung, ai, ref}]", 300),
    ("gia_dinh_dang_dung", "[{khoa, gia_tri, vi_sao, huy_khi}]", 150),
    ("sua_cua_nguoi", "[{changeset, hien_vat, tom_tat, vi_sao, da_nhac}]", 200),
    ("viec_con_lai", "[...]", 200),
    ("tep_dang_sua", "[{path, version, dang_lam_gi}]", 100),
    ("hien_vat_stale", "[{id, ly_do}]", 100),
    ("cau_hoi_mo", "[...]", 100),
    ("loi_da_gap", "[{mo_ta, cach_sua, ket_qua}]", 200),
]

# Ba mục KHÔNG được bỏ khi bậc thang C3 gộp tóm tắt (§6.4): chúng là ý chí của người và
# nền của mọi việc sau đó. Vượt trần thì tham chiếu "xem ADR-01…09 trong kho", không xoá.
MUC_KHONG_DUOC_BO = ("quyet_dinh", "gia_dinh_dang_dung", "sua_cua_nguoi")

TEN_TOOL_TOM_TAT = "ghi_tom_tat_phien"
TEN_TOOL_TRA_LOI = "tra_loi_phieu_kiem"


def luoc_do_tom_tat() -> dict[str, Any]:
    """Khai báo công cụ ép mô hình trả về đúng cấu trúc.

    Dùng đường công cụ thay vì "trả JSON trong văn bản rồi ta parse": mô hình được ép
    theo lược đồ ở tầng API, và ta không phải viết bộ sửa JSON hỏng — một bộ như thế
    là chỗ nữa để mất dữ liệu trong im lặng.
    """
    props: dict[str, Any] = {}
    for ten, mo_ta, tran in MUC:
        props[ten] = {"type": "string",
                      "description": f"{mo_ta} · tối đa ~{tran} token · không có thì ghi “—”"}
    return {
        "name": TEN_TOOL_TOM_TAT,
        "description": ("Ghi bản tóm tắt phiên theo đúng mười mục. Chỉ dùng thông tin "
                        "có trong đoạn hội thoại và trong kho; KHÔNG suy diễn. Mọi "
                        "quyết định phải kèm mã tham chiếu. Mục không có nội dung thì "
                        "ghi “—”, không được bỏ."),
        "parameters": {"type": "object", "properties": props,
                       "required": [t for t, _, _ in MUC]},
    }


def luoc_do_tra_loi() -> dict[str, Any]:
    return {
        "name": TEN_TOOL_TRA_LOI,
        "description": ("Trả lời từng câu hỏi kiểm, ngắn gọn, chỉ dựa vào ngữ cảnh đang "
                        "có. Không biết thì trả lời đúng chữ “không biết”."),
        "parameters": {
            "type": "object",
            "properties": {"tra_loi": {"type": "array", "items": {"type": "string"},
                                       "description": "Đúng thứ tự câu hỏi"}},
            "required": ["tra_loi"]},
    }


@dataclass(slots=True)
class BanTomTat:
    muc: dict[str, str] = field(default_factory=dict)
    covers: tuple[int, int] = (0, 0)
    prev_hash: str = ""
    created_at: str = ""
    model: str = ""
    tokens: int = 0

    @classmethod
    def tu_args(cls, args: dict[str, Any], **kw: Any) -> "BanTomTat":
        m = {t: str(args.get(t) or "—").strip() or "—" for t, _, _ in MUC}
        return cls(muc=m, **kw)

    def thieu_muc(self) -> list[str]:
        return [t for t, _, _ in MUC if t not in self.muc]

    def rong(self) -> bool:
        """Mọi mục đều "—" — tóm tắt không nói gì. Không phải lỗi, nhưng phải biết."""
        return all(v.strip() in ("—", "-", "") for v in self.muc.values())

    def van_ban(self) -> str:
        """Dạng đưa vào transcript. Có nhãn rõ để mô hình không nhầm là lời người nói."""
        L = ["<session_summary>",
             "Đây là bản tóm tắt phần hội thoại đã được nén khỏi ngữ cảnh. Nó là NGUỒN "
             "DUY NHẤT về giai đoạn đó — cần chi tiết hơn thì gọi ledger.query."]
        for ten, mo_ta, _ in MUC:
            L.append(f"\n## {ten}\n{self.muc.get(ten, '—')}")
        L.append("</session_summary>")
        return "\n".join(L)

    def to_dict(self) -> dict[str, Any]:
        return {"muc": dict(self.muc), "covers": list(self.covers),
                "prev_hash": self.prev_hash, "created_at": self.created_at,
                "model": self.model, "tokens": self.tokens}

    @classmethod
    def tu_dict(cls, d: Any) -> "BanTomTat | None":
        """Đảo `to_dict` — để bản tóm tắt đọc lại được từ SỔ CÁI sau khi tắt app (M5-17).

        Hai chỗ phải cẩn thận, và cả hai là chuyện của dữ liệu đã nằm trên đĩa:

        * `covers` được ghi thành **list** (JSON không có tuple), nên đọc lại phải đưa về
          tuple — không thì một bản nạp lại khác KIỂU bản vừa tạo, và chỗ nào so bằng sẽ im
          lặng sai.
        * Sổ cái của một bản EIDE cũ có thể **thiếu khoá**. Hàm này chạy ở đường khởi động,
          nên một `KeyError` ở đây là đổi một bản tóm tắt mất lấy cả dự án không mở được.
        """
        if not isinstance(d, dict):
            return None
        c = d.get("covers") or (0, 0)
        try:
            cv = (int(c[0]), int(c[1])) if len(c) >= 2 else (0, 0)
        except (TypeError, ValueError, IndexError):
            cv = (0, 0)
        m = d.get("muc")
        return cls(muc=dict(m) if isinstance(m, dict) else {}, covers=cv,
                   prev_hash=str(d.get("prev_hash") or ""),
                   created_at=str(d.get("created_at") or ""),
                   model=str(d.get("model") or ""),
                   tokens=int(d.get("tokens") or 0))

    def chua_noi_dung_da_quen(self, tombstones: list[str]) -> list[str]:
        """P7 — thứ người đã bảo quên không được sống lại qua bản tóm tắt."""
        chu = " ".join(self.muc.values()).lower()
        return [t for t in tombstones if t.strip() and t.strip().lower()[:40] in chu]


# =========================================================================== phiếu kiểm
@dataclass(slots=True)
class CauKiem:
    hoi: str
    dap_an: str                 # chuỗi phải xuất hiện trong câu trả lời
    nguon: str                  # sự kiện nào trong sổ cái sinh ra câu này

    def dung(self, tra_loi: str) -> bool:
        """So bằng mã: id/khoá/giá trị phải trùng. KHÔNG so văn phong."""
        a = _chuan(tra_loi)
        return _chuan(self.dap_an) in a


def _chuan(s: str) -> str:
    return re.sub(r"[^\wÀ-ỹ.+-]+", " ", str(s or "")).lower().strip()


def lam_phieu_kiem(ledger: Any, store: Any = None, *, so_cau: int = 3) -> list[CauKiem]:
    """§6.2.1 bước 3 — ba sự kiện KIỂM ĐƯỢC, chọn bằng mã từ sổ cái.

    Chọn theo thứ tự ưu tiên: quyết định gần nhất · giả định đang dùng · sửa của người
    gần nhất. Đây đúng ba thứ §6.3 nói không bao giờ được nén mất, nên hỏi chúng là hỏi
    đúng chỗ đau.
    """
    ra: list[CauKiem] = []
    su_kien = list(ledger.read())

    # 1. Quyết định gần nhất (ADR hoặc quyết định cổng).
    for ev in reversed(su_kien):
        if ev.kind == "changeset" and str(ev.data.get("touches")).find("ADR") >= 0:
            ma = next((t for t in ev.data.get("touches", []) if "ADR" in str(t)), "")
            if ma:
                ra.append(CauKiem(
                    hoi=f"Quyết định {ma} là quyết định về việc gì? Nêu mã của nó.",
                    dap_an=ma, nguon=f"changeset {ev.data.get('id')}"))
                break
        if ev.kind == "gate" and ev.data.get("state") in ("approved", "rejected"):
            g = ev.data.get("gate") or ev.data.get("gate_id")
            ra.append(CauKiem(
                hoi=f"Cổng {g} gần đây được duyệt hay bị từ chối?",
                dap_an="duyệt" if ev.data["state"] == "approved" else "từ chối",
                nguon=f"gate {ev.data.get('gate_id')}"))
            break

    # 2. Sửa của người gần nhất.
    for ev in reversed(su_kien):
        if ev.kind == "changeset" and ev.data.get("author") == "human":
            ma = (ev.data.get("touches") or [""])[0]
            if ma:
                ra.append(CauKiem(
                    hoi="Người dùng vừa tự tay sửa hiện vật nào? Nêu đúng mã.",
                    dap_an=str(ma), nguon=f"changeset {ev.data.get('id')}"))
                break

    # 3. Một yêu cầu có tiêu chí đo — thứ dễ bị nén thành "đã bàn về hiệu năng".
    if store is not None:
        for a in reversed(store.list("req", limit=50)):
            tc = (a.get("canonical") or {}).get("criteria") or ""
            so = re.search(r"\d+(?:[.,]\d+)?\s*\S{0,6}", tc)
            if so:
                ra.append(CauKiem(
                    hoi=f"Tiêu chí đo của yêu cầu {a['id']} là gì? Nêu con số.",
                    dap_an=so.group(0).strip(), nguon=f"req {a['id']}"))
                break

    # 4. Bù bằng lời người dùng đầu phiên nếu chưa đủ.
    if len(ra) < so_cau:
        for ev in su_kien:
            if ev.kind == "turn.start" and (ev.data.get("text") or "").strip():
                tu = [w for w in re.findall(r"\w{5,}", ev.data["text"]) if w.isalpha()]
                if tu:
                    ra.append(CauKiem(
                        hoi="Người dùng mô tả việc cần làm bằng những từ nào ở đầu phiên?",
                        dap_an=tu[0], nguon=f"turn.start {ev.data.get('run_id')}"))
                    break
    return ra[:so_cau]


def cham_phieu(phieu: list[CauKiem], tra_loi: list[str]) -> dict[str, Any]:
    """Chấm bằng mã. Thiếu câu trả lời tính là SAI, không tính là bỏ qua."""
    ket = []
    for i, c in enumerate(phieu):
        tl = tra_loi[i] if i < len(tra_loi) else ""
        ket.append({"hoi": c.hoi, "dap_an": c.dap_an, "tra_loi": tl,
                    "dat": c.dung(tl), "nguon": c.nguon})
    dat = sum(1 for k in ket if k["dat"])
    return {"dat": dat, "tong": len(phieu), "diem": f"{dat}/{len(phieu)}",
            "qua": dat == len(phieu) and bool(phieu), "chi_tiet": ket}


def prompt_tom_tat(doan: list[dict[str, Any]], cu: BanTomTat | None,
                   inventory_text: str, tombstones: list[str]) -> str:
    """Lời dặn cho lần gọi tóm tắt. Ngắn, và mọi ràng buộc đều kiểm được sau đó."""
    L = ["Bạn đang nén phần cũ của một phiên làm việc thành bản tóm tắt có cấu trúc.",
         "",
         "Quy tắc:",
         "- CHỈ dùng thông tin có trong đoạn dưới đây và trong <inventory>. Không suy diễn.",
         "- Mọi quyết định phải kèm mã tham chiếu (ADR-xx, cs-xxxx, run-xx).",
         "- Mục không có nội dung: ghi “—”. Không bỏ mục nào.",
         "- Tiếng Việt; thuật ngữ kỹ thuật giữ nguyên tiếng Anh.",
         "- Con số phải giữ NGUYÊN VĂN, kèm đơn vị. Đừng làm tròn, đừng diễn đạt lại.",
         ]
    if tombstones:
        L += ["- Những điều sau đã được người dùng YÊU CẦU QUÊN — tuyệt đối không đưa "
              "vào bản tóm tắt:"]
        L += [f"    · {t[:120]}" for t in tombstones[:10]]
    L += ["", inventory_text or "", ""]
    if cu is not None:
        L += ["Bản tóm tắt hiện có (gộp thêm phần mới vào, giữ mọi quyết định cũ):",
              cu.van_ban(), ""]
    L += ["Đoạn cần tóm tắt:", "---"]
    for m in doan:
        vai = m.get("role", "?")
        chu = m.get("text") or json.dumps(m.get("result", ""), ensure_ascii=False,
                                          default=str)
        L.append(f"[{vai}] {str(chu)[:1500]}")
    L += ["---", "",
          f"Gọi công cụ {TEN_TOOL_TOM_TAT} với đúng mười mục."]
    return "\n".join(L)


def prompt_kiem(phieu: list[CauKiem]) -> str:
    L = ["Trả lời ba câu sau CHỈ dựa vào ngữ cảnh bạn đang có. Không đoán; không biết "
         "thì trả lời đúng chữ “không biết”.", ""]
    for i, c in enumerate(phieu, 1):
        L.append(f"{i}. {c.hoi}")
    L += ["", f"Gọi công cụ {TEN_TOOL_TRA_LOI} với danh sách câu trả lời đúng thứ tự."]
    return "\n".join(L)
