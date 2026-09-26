# -*- coding: utf-8 -*-
"""Bước 7 — nạp lại sơ đồ người đã sửa. EIDE-SCH-44 §3 bước 7 và §7. Ca SCH10, SCH12, SCH13.

    "3. So với CKM: (a) chỉ đổi vị trí/nhãn → changeset human 'bố cục', không STALE; (b) đổi
     giá trị linh kiện → cập nhật BOM/Fact NGƯỜI, STALE ERC; (c) thêm/bớt linh kiện hoặc net →
     thẻ hỏi 'cập nhật module_graph theo sơ đồ, hay giữ CKM và đánh dấu sơ đồ lệch?' — không
     tự chọn."

Ba loại, và **việc phải làm khác nhau ở cả ba** — nên gộp chúng là làm mất thông tin quan
trọng nhất của bước này:

  **bố cục**    người kéo ký hiệu cho dễ đọc. Không có gì lỗi thời. Nếu ta đánh STALE ở đây
                thì mỗi lần người dùng sắp lại trang là một lần cả chuỗi hạ nguồn sáng đèn,
                và họ học được rằng băng cảnh báo vô nghĩa.

  **giá trị**   người đổi 4,7 kΩ thành 10 kΩ. Đây là một quyết định kỹ thuật của HỌ: giá trị
                vào BOM và thành Fact tầng NGƯỜI (có trích lời), ERC phải chạy lại.

  **cấu trúc**  người thêm một net hay một linh kiện. EIDE **không biết** họ muốn gì: sửa bản
                đồ theo sơ đồ, hay giữ bản đồ và coi sơ đồ là lệch? Hai lựa chọn dẫn tới hai
                mạch khác nhau, nên đây là chỗ phải HỎI. Tự chọn ở đây là tự quyết một phần
                thiết kế thay người.

Điều tệp này cố ý không làm: không ghi gì vào kho. Nó chỉ **phân loại** và trả về việc cần
làm; ghi là việc của công cụ, và thẻ hỏi là việc của vòng lặp.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LOAI = ("bo_cuc", "gia_tri", "cau_truc")


@dataclass(slots=True)
class ThayDoi:
    loai: str                   # bo_cuc | gia_tri | cau_truc
    vi: str
    chi_tiet: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"loai": self.loai, "vi": self.vi, "chi_tiet": self.chi_tiet}


@dataclass(slots=True)
class KetQuaNap:
    thay_doi: list[ThayDoi] = field(default_factory=list)
    canh_bao: list[str] = field(default_factory=list)

    @property
    def theo_loai(self) -> dict[str, list[ThayDoi]]:
        ra: dict[str, list[ThayDoi]] = {k: [] for k in LOAI}
        for t in self.thay_doi:
            ra.setdefault(t.loai, []).append(t)
        return ra

    @property
    def can_hoi(self) -> bool:
        """Có thay đổi CẤU TRÚC thì phải hỏi người — §7 mục 3(c)."""
        return bool(self.theo_loai["cau_truc"])

    def to_dict(self) -> dict[str, Any]:
        return {"so_thay_doi": len(self.thay_doi),
                "theo_loai": {k: [t.to_dict() for t in v]
                              for k, v in self.theo_loai.items()},
                "can_hoi": self.can_hoi, "canh_bao": list(self.canh_bao)}

    def cau_vi(self) -> str:
        t = self.theo_loai
        p: list[str] = []
        if t["cau_truc"]:
            p.append(f"{len(t['cau_truc'])} thay đổi CẤU TRÚC — phải hỏi người dùng muốn "
                     "cập nhật bản đồ theo sơ đồ hay giữ bản đồ và đánh dấu sơ đồ lệch: "
                     + "; ".join(x.vi for x in t["cau_truc"][:4]))
        if t["gia_tri"]:
            p.append(f"{len(t['gia_tri'])} giá trị linh kiện đổi — vào BOM và thành Fact tầng "
                     "NGƯỜI, ERC phải chạy lại: " + "; ".join(x.vi for x in t["gia_tri"][:4]))
        if t["bo_cuc"]:
            p.append(f"{len(t['bo_cuc'])} thay đổi chỉ về bố cục — ghi lại, KHÔNG làm gì lỗi "
                     "thời")
        return ". ".join(p) if p else "Sơ đồ khớp bản đồ mạch, không có gì đổi."


# =========================================================================== phân loại
def phan_loai(*, doc: Any, cay: Any, so: dict[str, Any],
              gia_tri_kho: dict[str, str]) -> KetQuaNap:
    """So sơ đồ người sửa với bản đồ trong kho rồi phân loại từng thay đổi.

    `doc` là `CayDocDuoc` từ `phan_cap.doc_phan_cap`; `so` là kết quả `phan_cap.so_cay`.

    `gia_tri_kho` **bắt buộc**, và phải là `phan_cap.gia_tri_mong_doi(cay, symbol)` — tức thứ
    bên GHI đã viết vào trường Value, không phải giá trị thô trong kho. Nó không có giá trị mặc
    định là có lý do đo được: bản trước để mặc định `None` rồi tự lùi về giá trị thô trong kho,
    và vì bên ghi điền tên chip khi lá chưa có `gia_tri`, mọi lần nạp lại đều báo một "thay đổi
    giá trị" không ai gây ra. Một mặc định âm thầm so với cơ sở khác thì tệ hơn là không có
    mặc định.
    """
    kq = KetQuaNap()
    kq.canh_bao += list(getattr(doc, "canh_bao", []) or [])

    # (c) cấu trúc — khối thêm/bớt, Port lệch, linh kiện thêm/bớt
    for p in so.get("khoi_chi_co_o_tep") or []:
        kq.thay_doi.append(ThayDoi(
            "cau_truc", f"sơ đồ có khối {p} mà bản đồ không có",
            {"khoi": p, "o": "tep"}))
    for p in so.get("khoi_chi_co_o_kho") or []:
        kq.thay_doi.append(ThayDoi(
            "cau_truc", f"bản đồ có khối {p} mà sơ đồ không còn",
            {"khoi": p, "o": "kho"}))
    for p, d in sorted((so.get("port_lech") or {}).items()):
        kq.thay_doi.append(ThayDoi(
            "cau_truc",
            f"khối {p} lệch tập Port — sơ đồ: [{', '.join(d['o_tep'])}], "
            f"bản đồ: [{', '.join(d['o_kho'])}]",
            {"khoi": p, **d}))

    ref_kho = {(n["canonical"].get("ref") or n["ten"]): n
               for n in cay.nut.values() if n.get("kind") == "leaf"}
    for ref in sorted(set(doc.la) - set(ref_kho)):
        kq.thay_doi.append(ThayDoi(
            "cau_truc", f"sơ đồ có linh kiện {ref} mà bản đồ không có",
            {"ref": ref, "o": "tep", "ten": doc.la[ref].get("ten", "")}))
    for ref in sorted(set(ref_kho) - set(doc.la)):
        kq.thay_doi.append(ThayDoi(
            "cau_truc", f"bản đồ có linh kiện {ref} mà sơ đồ không còn",
            {"ref": ref, "o": "kho"}))

    # (b) giá trị linh kiện
    for ref in sorted(set(doc.la) & set(ref_kho)):
        moi = str(doc.la[ref].get("gia_tri") or "").strip()
        cu = str(gia_tri_kho.get(ref, "")).strip()
        # So với giá trị bên GHI đã viết (`phan_cap.gia_tri_mong_doi`), không với giá trị
        # rỗng trong kho — xem docstring hàm đó.
        if moi != cu and (moi or cu):
            kq.thay_doi.append(ThayDoi(
                "gia_tri", f"{ref}: {cu} → {moi}",
                {"ref": ref, "cu": cu, "moi": moi}))
        # Lá chuyển sang sheet khác là thay đổi CẤU TRÚC, không phải bố cục: nó đổi khối chứa
        # linh kiện, tức đổi cả biên khối mà linh kiện đó nằm trong.
        p_tep = doc.la[ref].get("path", "")
        p_kho = cay.nut.get(ref_kho[ref].get("parent_id") or "", {}).get("path", "")
        if p_tep and p_kho and p_tep != p_kho:
            kq.thay_doi.append(ThayDoi(
                "cau_truc", f"{ref} chuyển từ khối {p_kho} sang {p_tep}",
                {"ref": ref, "tu": p_kho, "den": p_tep}))

    # (a) bố cục — chỉ khi KHÔNG có thay đổi nào ở hai loại trên cho cùng đối tượng đó.
    # Bản này không so từng toạ độ: KiCad ghi lại toạ độ theo cách riêng, và một so sánh toạ
    # độ quá nhạy sẽ báo "đổi bố cục" ở mọi lần mở tệp. Nói ra giới hạn đó thay vì giả vờ đã đo.
    if not kq.thay_doi:
        kq.canh_bao.append(
            "Không thấy thay đổi nào về cấu trúc hay giá trị. Bản này KHÔNG so từng toạ độ ký "
            "hiệu, nên nếu người dùng chỉ kéo ký hiệu cho dễ đọc thì thay đổi đó không hiện ra "
            "ở đây — và cũng không cần, vì nó không làm gì lỗi thời.")
    return kq


def the_hoi(kq: KetQuaNap) -> dict[str, Any] | None:
    """Nội dung thẻ hỏi cho thay đổi cấu trúc — §7 mục 3(c). `None` nếu không cần hỏi.

    Hai lựa chọn được viết ra bằng **hậu quả**, không bằng tên kỹ thuật: người đọc cần biết
    chọn cái nào thì mạch của họ thành cái gì.
    """
    ct = kq.theo_loai["cau_truc"]
    if not ct:
        return None
    return {
        "tieu_de": "Sơ đồ anh sửa có thay đổi CẤU TRÚC — cập nhật bản đồ, hay giữ bản đồ?",
        "viec": [x.vi for x in ct],
        "lua_chon": [
            {"ma": "theo_so_do",
             "nhan": "Cập nhật bản đồ mạch theo sơ đồ",
             "hau_qua": "Cây khối, Port và netlist trong EIDE đổi theo tệp anh vừa sửa. "
                        "ERC và mã dùng chân sẽ thành lỗi thời và cần chạy lại."},
            {"ma": "giu_ban_do",
             "nhan": "Giữ bản đồ, đánh dấu sơ đồ đang lệch",
             "hau_qua": "EIDE giữ nguyên cây khối; tệp sơ đồ được ghi là lệch với bản đồ, và "
                        "lần sinh lại sẽ ghi đè phần lệch đó."},
        ],
        "khong_tu_chon": ("Hai lựa chọn dẫn tới hai mạch khác nhau, nên EIDE không chọn hộ. "
                          "Không trả lời thì không có gì thay đổi."),
    }
