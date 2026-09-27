# -*- coding: utf-8 -*-
"""Tiêu chí mô phỏng — nêu TRƯỚC khi chạy, và là thứ PHÁN XỬ kết quả.

Đây là chỗ N6 sống hoặc chết. Ba quyết định của tệp này, và lý do từng cái:

1. **Chương trình mô phỏng ĐO, EIDE PHÁN.** Chương trình in ra số đo (`do: {ma: giá trị}`),
   còn đạt hay không do so số đo với ngưỡng trong tiêu chí. Bản trước để chương trình tự in
   `dat: true` — nghĩa là thứ được kiểm cũng chính là thứ tuyên bố kết quả, và một dòng sửa
   trong `sim/plant.c` đủ để mọi phép thử "đạt".

2. **Thiếu số đo là CHƯA ĐỦ DỮ KIỆN, không phải đạt.** Một assert không có số đo tương ứng
   thì kết luận là "chưa đo được", và cả lần chạy không được gọi là đạt. Log rỗng ≠ đạt.

3. **Phần không mô phỏng được luôn đi kèm kết quả.** TC019 đòi *"nói rõ phần nào không mô
   phỏng được… không tuyên bố 'đạt' cho phần chưa mô phỏng"*. Nếu danh sách đó chỉ nằm trong
   tiêu chí mà không xuất hiện cùng kết luận, người đọc sẽ hiểu "5/5 đạt" là "mọi thứ đạt".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Phép so của một assert. Giữ đóng: mô hình chọn trong danh sách này, không viết biểu thức.
PHEP_SO = ("<=", ">=", "<", ">", "==", "trong_khoang")

TEN_PHEP = {"<=": "không quá", ">=": "ít nhất", "<": "nhỏ hơn", ">": "lớn hơn",
            "==": "đúng bằng", "trong_khoang": "nằm trong khoảng"}


@dataclass(slots=True)
class Assert:
    """Một điều kiện đo được. Mỗi trường ở đây trả lời một câu người rà soát sẽ hỏi."""

    ma: str                       # "A1" — mã để số đo trỏ tới
    mo_ta: str                    # "Góc nghiêng lớn nhất trong 5 s"
    phep_so: str = "<="
    nguong: float = 0.0
    nguong_tren: float = 0.0      # chỉ dùng với `trong_khoang`
    don_vi: str = ""
    do_req: str = ""              # assert này đo YÊU CẦU nào (REQ-…)
    nguon_nguong: str = ""        # ngưỡng lấy từ đâu: Fact, tài liệu, hay lời người dùng

    def to_dict(self) -> dict[str, Any]:
        return {"ma": self.ma, "mo_ta": self.mo_ta, "phep_so": self.phep_so,
                "nguong": self.nguong, "nguong_tren": self.nguong_tren,
                "don_vi": self.don_vi, "do_req": self.do_req,
                "nguon_nguong": self.nguon_nguong}

    @property
    def vi(self) -> str:
        if self.phep_so == "trong_khoang":
            return (f"{self.ma}: {self.mo_ta} nằm trong khoảng "
                    f"{self.nguong}–{self.nguong_tren} {self.don_vi}".strip())
        return (f"{self.ma}: {self.mo_ta} {TEN_PHEP.get(self.phep_so, self.phep_so)} "
                f"{self.nguong} {self.don_vi}".strip())

    def xet(self, gia_tri: Any) -> tuple[str, str]:
        """Trả `(ket_luan, vi)` — `ket_luan` ∈ {đạt, không_đạt, chưa_đo_được}."""
        if gia_tri is None:
            return ("chua_do_duoc",
                    f"{self.ma}: chương trình mô phỏng KHÔNG in ra số đo cho assert này — "
                    "chưa đủ dữ kiện để kết luận, không phải đạt.")
        try:
            v = float(gia_tri)
        except (TypeError, ValueError):
            return ("chua_do_duoc",
                    f"{self.ma}: số đo “{gia_tri}” không phải một số — chưa xét được.")
        ok = {
            "<=": v <= self.nguong, ">=": v >= self.nguong,
            "<": v < self.nguong, ">": v > self.nguong,
            "==": abs(v - self.nguong) < 1e-9,
            "trong_khoang": self.nguong <= v <= self.nguong_tren,
        }.get(self.phep_so)
        if ok is None:
            return ("chua_do_duoc", f"{self.ma}: phép so “{self.phep_so}” không hợp lệ.")
        return (("dat" if ok else "khong_dat"),
                f"{self.ma}: đo được {v} {self.don_vi}".strip()
                + f" · yêu cầu {TEN_PHEP.get(self.phep_so, self.phep_so)} {self.nguong}"
                + (f"–{self.nguong_tren}" if self.phep_so == "trong_khoang" else "")
                + (f" {self.don_vi}" if self.don_vi else ""))


@dataclass(slots=True)
class TieuChi:
    ma: str = "sim-01"
    ten: str = ""
    asserts: list[Assert] = field(default_factory=list)
    khong_mo_phong_duoc: list[dict[str, str]] = field(default_factory=list)
    timeout_s: float = 60.0
    xac_nhan_boi: str = ""
    xac_nhan_luc: str = ""
    trich_loi: str = ""

    @property
    def da_xac_nhan(self) -> bool:
        return bool(self.xac_nhan_boi)

    def to_dict(self) -> dict[str, Any]:
        return {"ma": self.ma, "ten": self.ten,
                "assert": [a.to_dict() for a in self.asserts],
                "so_assert": len(self.asserts),
                "khong_mo_phong_duoc": [dict(x) for x in self.khong_mo_phong_duoc],
                "timeout_s": self.timeout_s, "xac_nhan_boi": self.xac_nhan_boi,
                "xac_nhan_luc": self.xac_nhan_luc, "trich_loi": self.trich_loi,
                "da_xac_nhan": self.da_xac_nhan}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TieuChi":
        return cls(
            ma=str(d.get("ma") or "sim-01"), ten=str(d.get("ten") or ""),
            asserts=[Assert(
                ma=str(a.get("ma") or ""), mo_ta=str(a.get("mo_ta") or ""),
                phep_so=str(a.get("phep_so") or "<="),
                nguong=float(a.get("nguong") or 0), nguong_tren=float(a.get("nguong_tren") or 0),
                don_vi=str(a.get("don_vi") or ""), do_req=str(a.get("do_req") or ""),
                nguon_nguong=str(a.get("nguon_nguong") or ""))
                for a in (d.get("assert") or [])],
            khong_mo_phong_duoc=[dict(x) for x in (d.get("khong_mo_phong_duoc") or [])],
            timeout_s=float(d.get("timeout_s") or 60.0),
            xac_nhan_boi=str(d.get("xac_nhan_boi") or ""),
            xac_nhan_luc=str(d.get("xac_nhan_luc") or ""),
            trich_loi=str(d.get("trich_loi") or ""))


def xet_ket_qua(tc: TieuChi, do: dict[str, Any]) -> dict[str, Any]:
    """So số đo với tiêu chí. **Đây** là chỗ ra kết luận, không phải chương trình mô phỏng."""
    dong: list[dict[str, str]] = []
    for a in tc.asserts:
        kl, vi = a.xet(do.get(a.ma))
        dong.append({"ma": a.ma, "ket_luan": kl, "vi": vi, "mo_ta": a.mo_ta,
                     "do_req": a.do_req, "nguon_nguong": a.nguon_nguong})
    dem = {k: sum(1 for d in dong if d["ket_luan"] == k)
           for k in ("dat", "khong_dat", "chua_do_duoc")}
    # Thừa số đo cũng đáng nói: nó nghĩa là chương trình đo một thứ không ai đặt tiêu chí,
    # hoặc mã assert bị gõ sai ở một trong hai bên.
    thua = sorted(set(do) - {a.ma for a in tc.asserts})
    return {
        "dong": dong, "dem": dem, "so_do_thua": thua,
        "dat": bool(tc.asserts) and dem["khong_dat"] == 0 and dem["chua_do_duoc"] == 0,
        "vi_sao_khong_dat": (
            "" if (tc.asserts and dem["khong_dat"] == 0 and dem["chua_do_duoc"] == 0) else
            ("tiêu chí chưa có assert nào" if not tc.asserts else
             "; ".join(d["vi"] for d in dong
                       if d["ket_luan"] in ("khong_dat", "chua_do_duoc"))[:600])),
    }
