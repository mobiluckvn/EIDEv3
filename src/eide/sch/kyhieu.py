# -*- coding: utf-8 -*-
"""Bước 3 — ký hiệu (symbol). SCH-44 §3 bước 3, §5.

Hai đường lấy ký hiệu, và §5 nói rõ thứ tự:

  **thư viện chính thức** tải về như DỮ LIỆU (`.kicad_sym`, có hash, qua G-DATA) — không
  cần cài KiCad. Tìm theo MPN/bí danh, **đối chiếu số chân và tên chân với Fact pinout**;
  khớp ≥ 95 % thì dùng và ghi `lib_ref@version`; lệch thì *"không dùng im lặng"*.

  **sinh từ Fact** (`.kicad_sym`): số chân, tên, kiểu suy từ Fact, và mô tả symbol ghi
  *"sinh từ DS rev X p.Y"* — §5 gọi đó là "N1 áp vào ký hiệu".

Máy này chưa có thư viện chính thức nào tải về, nên đường thứ hai là đường thực tế. Điều đó
**không** làm phép đối chiếu vô nghĩa: khi người dùng tải thư viện về sau, cùng hàm này sẽ
so nó với Fact và từ chối cái lệch.

Chip không có Fact pinout ≥ NGƯỜI → **E8002**, không bịa chân (§5 cuối).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# §5 — kiểu chân KiCad. Suy từ hướng Port, và `passive` là câu trả lời trung thực khi chưa
# biết: đoán `input` cho một chân chưa rõ sẽ làm ERC của KiCad báo lỗi sai ở máy người khác.
KIEU_CHAN = {"in": "input", "out": "output", "bidir": "bidirectional",
             "power_in": "power_in", "power_out": "power_out", "passive": "passive"}

NGUONG_KHOP = 0.95          # §5: "khớp ≥ 95 % → dùng"


@dataclass(slots=True)
class KyHieu:
    ref: str
    lib: str = ""                  # thư viện chính thức, hoặc "" nếu sinh
    ten: str = ""
    sinh_tu_fact: bool = False
    chan: list[dict[str, str]] = field(default_factory=list)
    nguon: str = ""                # "DS rev X p.Y" — N1 áp vào ký hiệu
    canh_bao: str = ""
    ty_khop: float | None = None   # khớp bao nhiêu với Fact, None = không có lib để so
    xac_nhan_boi: str = ""         # ai đã xem và xác nhận ký hiệu này
    xac_nhan_luc: str = ""

    @property
    def can_xac_nhan(self) -> bool:
        """§9 — "Symbol sinh từ Fact: xem, xác nhận, sửa kiểu chân" là một widget **edit**.

        Ký hiệu sinh từ Fact là một phép SUY của máy: kiểu chân (`power_in`/`in`/`passive`…)
        suy từ hướng Port, mà hướng Port lại suy từ tên chân. Suy đúng phần lớn thời gian
        không phải là suy đúng, và một kiểu chân sai làm ERC của KiCad báo sai — nên nó cần
        một con người nói "đúng rồi". Ký hiệu lấy từ thư viện chính thức khớp 100 % thì không
        cần: ở đó tác giả thư viện đã là con người đó.
        """
        if self.xac_nhan_boi:
            return False
        return bool(self.sinh_tu_fact) or (self.ty_khop is not None and self.ty_khop < 1.0)

    def to_dict(self) -> dict[str, Any]:
        return {"ref": self.ref, "lib": self.lib, "ten": self.ten,
                "sinh_tu_fact": self.sinh_tu_fact, "so_chan": len(self.chan),
                "nguon": self.nguon, "canh_bao": self.canh_bao,
                "ty_khop": self.ty_khop, "can_xac_nhan": self.can_xac_nhan,
                "xac_nhan_boi": self.xac_nhan_boi, "xac_nhan_luc": self.xac_nhan_luc,
                "chan": [dict(c) for c in self.chan]}


def anh_xa(cay: Any, *, thu_vien: dict[str, dict[str, Any]] | None = None,
           nguon_fact: dict[str, str] | None = None) -> tuple[dict[str, KyHieu], list[str]]:
    """Ánh xạ ref → ký hiệu cho mọi lá trong cây. Trả `(ánh xạ, thiếu pinout)`.

    `thu_vien` là thư viện chính thức đã tải (ref/MPN → {lib, ten, chan}); rỗng thì mọi ký
    hiệu sinh từ Fact. `nguon_fact` là câu "DS rev X p.Y" cho từng ref, do người gọi tra từ
    Fact — module này không đọc kho (giữ `eide/sch/` không phụ thuộc lớp lưu trữ).
    """
    ra: dict[str, KyHieu] = {}
    thieu: list[str] = []
    tv = thu_vien or {}
    ngf = nguon_fact or {}

    for nid, n in sorted(cay.nut.items()):
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        chan = [_chan_tu_port(cay.port[p]) for p in cay.port_cua.get(nid, [])]
        if not chan:
            # §5 cuối: không có pinout thì KHÔNG bịa. Đây là ref sẽ làm `sch.compose` dừng.
            thieu.append(ref)
            continue
        chan.sort(key=_khoa_chan)
        chinh_thuc = tv.get(ref) or tv.get(n["canonical"].get("ten") or "")
        if chinh_thuc:
            ty, lech = _doi_chieu(chan, chinh_thuc.get("chan") or [])
            if ty >= NGUONG_KHOP:
                ra[ref] = KyHieu(ref=ref, lib=chinh_thuc.get("lib", ""),
                                 ten=chinh_thuc.get("ten", ""), chan=chan, ty_khop=ty,
                                 nguon=f"thư viện {chinh_thuc.get('lib')}@"
                                       f"{chinh_thuc.get('version', '?')}",
                                 canh_bao=("" if ty == 1.0 else
                                           f"khớp {ty:.0%} với Fact; lệch: {lech}"))
                continue
            # §5: "lệch → không dùng im lặng". Rơi về ký hiệu sinh, và NÓI RA vì sao.
            ra[ref] = _sinh(ref, n, chan, ngf.get(ref, ""), ty_khop=ty,
                            canh_bao=(f"Ký hiệu thư viện {chinh_thuc.get('lib')} chỉ khớp "
                                      f"{ty:.0%} với Fact pinout ({lech}) — dùng ký hiệu "
                                      "sinh từ Fact thay vì tin thư viện."))
            continue
        ra[ref] = _sinh(ref, n, chan, ngf.get(ref, ""))
    return ra, thieu


def _sinh(ref: str, n: dict[str, Any], chan: list[dict[str, str]], nguon: str,
          canh_bao: str = "", ty_khop: float | None = None) -> KyHieu:
    return KyHieu(ref=ref, lib="", ten=n["canonical"].get("ten") or ref,
                  sinh_tu_fact=True, chan=chan, ty_khop=ty_khop,
                  nguon=nguon or "Fact pinout trong kho (chưa ghi rõ trang tài liệu)",
                  canh_bao=canh_bao)


# =================================================== xác nhận của người §9, SCH-14/SCH-15
# Tập kiểu chân KiCad mà người được phép chọn khi sửa. Đặt tên khác `KIEU_CHAN` (bảng
# hướng-Port → kiểu chân ở đầu tệp) vì hai thứ khác nhau: một cái là phép SUY của máy, một cái
# là danh sách người CHỌN. Bản đầu trùng tên và đè lên bảng suy — `_chan_tu_port` gọi `.get()`
# trên một tuple, tức mọi ký hiệu sinh ra đều nổ.
KIEU_CHAN_CHON_DUOC = ("power_in", "power_out", "input", "output", "bidirectional", "passive",
                       "open_collector", "tri_state", "unspecified", "no_connect")


def ap_xac_nhan(ds: dict[str, KyHieu], da_xac_nhan: dict[str, dict[str, Any]]) -> None:
    """Đắp phần người đã xác nhận lên ánh xạ vừa sinh lại.

    `sch.symbols` chạy lại mỗi khi Fact đổi, và nếu nó quên phần này thì mọi xác nhận của người
    biến mất mỗi lần sinh lại — người dùng sẽ xác nhận lần thứ ba rồi thôi không xác nhận nữa.
    Sửa kiểu chân của người **đè lên** phép suy của máy: đó là cả điểm của việc cho họ sửa.
    """
    for ref, xn in (da_xac_nhan or {}).items():
        k = ds.get(ref)
        if k is None:
            continue
        k.xac_nhan_boi = str(xn.get("boi") or "")
        k.xac_nhan_luc = str(xn.get("luc") or "")
        sua = dict(xn.get("kieu_chan") or {})
        for c in k.chan:
            if c.get("so") in sua:
                c["kieu"] = sua[c["so"]]
                c["kieu_boi_nguoi"] = "có"


def _chan_tu_port(p: dict[str, Any]) -> dict[str, str]:
    return {"so": str(p.get("chan") or p["ten"]), "ten": str(p["ten"]),
            "kieu": KIEU_CHAN.get(p.get("huong", ""), "passive")}


def _khoa_chan(c: dict[str, str]) -> tuple[int, str]:
    s = c["so"]
    return (int(s), "") if s.isdigit() else (10**9, s)


def _doi_chieu(fact: list[dict[str, str]],
               lib: list[dict[str, str]]) -> tuple[float, str]:
    """Tỉ lệ khớp giữa chân trong Fact và chân trong thư viện, kèm câu nói chỗ lệch.

    So theo SỐ chân, không theo tên: tên chân khác nhau giữa các phiên bản thư viện là
    chuyện thường (`VCC` vs `VDD`), còn số chân khác nhau nghĩa là **hai con chip khác nhau**
    — và đó mới là thứ phải chặn.
    """
    f = {c["so"] for c in fact}
    l = {str(c.get("so") or c.get("number") or "") for c in lib}
    if not f:
        return (0.0, "Fact không có chân nào")
    khop = len(f & l)
    thieu, thua = sorted(f - l, key=_so), sorted(l - f, key=_so)
    p: list[str] = []
    if thieu:
        p.append("thư viện thiếu chân " + ", ".join(thieu[:8]))
    if thua:
        p.append("thư viện có thêm chân " + ", ".join(thua[:8]))
    return (khop / len(f | l) if (f | l) else 0.0, "; ".join(p))


def _so(s: str) -> tuple[int, str]:
    return (int(s), "") if str(s).isdigit() else (10**9, str(s))


# =========================================================================== .kicad_sym
def viet_kicad_sym(ds: dict[str, KyHieu]) -> str:
    """Viết `.kicad_sym` cho các ký hiệu sinh từ Fact.

    Viết tay S-expression vì máy không cài KiCad và `kiutils` cũng chưa có. Định dạng này
    KiCad 7→9 đọc được; phần hình vẽ để tối giản (một hình chữ nhật + chân hai bên) — mục
    tiêu là **mở được và đúng chân**, không phải đẹp.
    """
    L = ['(kicad_symbol_lib (version 20231120) (generator "EIDE")']
    for ref in sorted(ds):
        k = ds[ref]
        if not k.sinh_tu_fact:
            continue
        ten = _ten_sym(k)
        L.append(f'  (symbol "{ten}" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)')
        L.append(f'    (property "Reference" "{_tien_to(ref)}" (at 0 2.54 0))')
        L.append(f'    (property "Value" "{_esc(k.ten)}" (at 0 0 0))')
        # N1 áp vào ký hiệu: nguồn gốc đi theo tệp, không chỉ nằm trong báo cáo.
        L.append(f'    (property "Description" "Sinh từ {_esc(k.nguon)} — EIDE" (at 0 0 0))')
        L.append(f'    (symbol "{ten}_1_1"')
        n = max(1, len(k.chan))
        cao = 2.54 * ((n + 1) // 2 + 1)
        L.append(f"      (rectangle (start -5.08 {cao:.2f}) (end 5.08 {-cao:.2f})"
                 " (stroke (width 0.254) (type default)) (fill (type background)))")
        for i, c in enumerate(k.chan):
            ben = -1 if i % 2 == 0 else 1
            y = cao - 2.54 * (i // 2 + 1)
            goc = 0 if ben < 0 else 180
            L.append(f'      (pin {c["kieu"]} line (at {ben * 7.62:.2f} {y:.2f} {goc})'
                     f' (length 2.54) (name "{_esc(c["ten"])}" (effects (font (size 1.27 1.27))))'
                     f' (number "{_esc(c["so"])}" (effects (font (size 1.27 1.27)))))')
        L += ["    )", "  )"]
    L += [")", ""]
    return "\n".join(L)


def _ten_sym(k: KyHieu) -> str:
    return _esc(k.ten or k.ref)


def _tien_to(ref: str) -> str:
    """`U1` → `U`. KiCad dùng tiền tố chữ để tự đánh số ký hiệu mới."""
    t = "".join(c for c in ref if c.isalpha())
    return t or "U"


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"')
