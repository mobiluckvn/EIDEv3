# -*- coding: utf-8 -*-
"""Chuẩn hoá đơn vị và ký hiệu kỹ thuật — EIDE-ING-43 §5.2. Bằng MÃ, 0 token.

Vì sao việc này không được giao cho mô hình: `4R7` là 4,7 Ω, `3V3` là 3,3 V, `100n`
trong ngữ cảnh tụ là 100 nF. Một mô hình đọc đúng chín lần rồi sai lần thứ mười, và lần
thứ mười đi thẳng vào một con điện trở người ta đi mua. Quy tắc này hữu hạn và viết
được thành mã, nên nó phải là mã.

## Hai thứ luôn được giữ

`raw` — chuỗi **nguyên văn** trong tài liệu. Người rà soát đối chiếu với tệp bằng chuỗi
đó, không bằng con số ta đã diễn dịch. Mất `raw` là mất khả năng cãi lại.

`cờ` — khi tài liệu ghi `—`, `N/A`, `TBD`, giá trị là **null có lý do**, không phải 0.
Biến "chưa có số" thành số 0 là cách nhanh nhất để một mạch chạy sai mà không ai hiểu vì
sao.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Tiền tố SI → hệ số. `M` là mega, `m` là mili — phân biệt HOA/thường là bắt buộc.
TIEN_TO: dict[str, float] = {
    "T": 1e12, "G": 1e9, "M": 1e6, "k": 1e3, "K": 1e3, "h": 1e2, "da": 1e1,
    "d": 1e-1, "c": 1e-2, "m": 1e-3, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
    "n": 1e-9, "p": 1e-12, "f": 1e-15,
}

# Đơn vị cơ bản, viết theo cách người Việt đọc quen.
DON_VI_CO_BAN = {"V", "A", "Ω", "Hz", "s", "F", "H", "W", "°C", "B", "bps", "B/s", "%"}

_BI_DANH_DON_VI = {
    "ohm": "Ω", "ohms": "Ω", "r": "Ω", "Ω": "Ω",
    "v": "V", "volt": "V", "volts": "V",
    "a": "A", "amp": "A", "amps": "A", "ampere": "A",
    "hz": "Hz", "hertz": "Hz",
    "f": "F", "farad": "F",
    "h": "H", "henry": "H",
    "s": "s", "sec": "s", "second": "s", "giây": "s",
    "w": "W", "watt": "W",
    "b": "B", "byte": "B", "bytes": "B",
    "°c": "°C", "c": "°C", "℃": "°C", "degc": "°C",
    "bps": "bps", "b/s": "B/s", "%": "%",
}

# "Không có số" — mỗi cái là một lý do khác nhau, và không cái nào là 0.
_KHONG_CO_SO = {
    "—": "tài liệu để trống",
    "-": "tài liệu để trống",
    "–": "tài liệu để trống",
    "n/a": "tài liệu ghi N/A — không áp dụng cho trường hợp này",
    "na": "tài liệu ghi N/A — không áp dụng cho trường hợp này",
    "tbd": "tài liệu ghi TBD — nhà sản xuất chưa chốt",
    "tba": "tài liệu ghi TBA — chưa công bố",
    "note": "ô trỏ tới chú thích, không phải một giá trị",
}

# Ký hiệu kỹ thuật: chữ đơn vị đứng THAY cho dấu thập phân. 4R7 = 4,7 Ω.
_KY_HIEU_KT = re.compile(r"^(\d+)([RKkMmuµnpVAF])(\d+)$")

# Số kèm đơn vị: "5.5 V", "100nF", "-40°C", "4,7kΩ".
_SO_DON_VI = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*"
    r"([TGMkKhdcmuµμnpf]?)\s*"
    r"(Ω|ohms?|V|volts?|A|amps?|ampere|Hz|hertz|F|farad|H|henry|s|sec|seconds?|giây|"
    r"W|watt|B/s|bps|B|bytes?|°C|℃|degC|%)\s*$",
    re.IGNORECASE)

# Dải: "2.7–5.5 V", "2,7 ~ 5,5V", "-40 to +85 °C", "2.7 .. 5.5 V".
_DAI = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*(?:[-–—~]|\.\.|to|đến|tới)\s*"
    r"([+-]?\d+(?:[.,]\d+)?)\s*(.*)$", re.IGNORECASE)

# Min/typ/max chung một ô: "2.7 / 3.3 / 5.5" hoặc "2.7|3.3|5.5".
_BA_GIA_TRI = re.compile(
    r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*[/|]\s*([+-]?\d+(?:[.,]\d+)?)"
    r"\s*[/|]\s*([+-]?\d+(?:[.,]\d+)?)\s*(.*)$")

# Điều kiện: "@ 100 kHz, VDD = 3.3 V", "(VDD=5V, TA=25°C)".
# Giá trị điều kiện dừng trước dấu đóng ngoặc và dấu phẩy phân tách — nếu không,
# "(VDD=5V)" cho ra "5V)" và mọi phép so điều kiện sau đó lệch một ký tự.
_DIEU_KIEN = re.compile(
    r"([A-Za-z][\w\.]{0,15})\s*=\s*([+-]?\d+(?:[.,]\d+)?\s*[^\s,;)\]]{0,6})")
_DIEU_KIEN_TAN = re.compile(r"@\s*([+-]?\d+(?:[.,]\d+)?\s*[kKMG]?Hz)")


@dataclass(slots=True)
class GiaTri:
    """Một giá trị đã chuẩn hoá. `raw` luôn còn, và `co` nói vì sao thiếu số."""

    raw: str
    gia_tri: float | None = None
    don_vi: str = ""
    vmin: float | None = None
    vtyp: float | None = None
    vmax: float | None = None
    co: str = ""                              # "" nếu có số; ngược lại là LÝ DO
    dieu_kien: dict[str, str] = field(default_factory=dict)

    @property
    def co_so(self) -> bool:
        return any(v is not None for v in (self.gia_tri, self.vmin, self.vtyp, self.vmax))

    @property
    def la_dai(self) -> bool:
        return self.vmin is not None and self.vmax is not None

    def to_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "value": self.gia_tri, "unit": self.don_vi,
                "vmin": self.vmin, "vtyp": self.vtyp, "vmax": self.vmax,
                "co": self.co, "condition": dict(self.dieu_kien)}

    def hien_vi(self) -> str:
        """Dạng hiện cho người Việt: dấu phẩy thập phân, đơn vị chuẩn."""
        def so(x: float | None) -> str:
            if x is None:
                return "—"
            s = f"{x:g}"
            return s.replace(".", ",")

        if self.la_dai:
            giua = f" (điển hình {so(self.vtyp)})" if self.vtyp is not None else ""
            return f"{so(self.vmin)}…{so(self.vmax)} {self.don_vi}{giua}".strip()
        if self.gia_tri is None:
            return f"— ({self.co})" if self.co else "—"
        return f"{so(self.gia_tri)} {self.don_vi}".strip()


def _so(s: str) -> float | None:
    try:
        return float(s.strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


def chuan_don_vi(tien_to: str, don_vi: str) -> tuple[float, str]:
    """`("k", "ohm")` → `(1000.0, "Ω")`. Tiền tố lạ thì hệ số 1, đơn vị giữ nguyên."""
    dv = _BI_DANH_DON_VI.get(don_vi.strip().lower(), don_vi.strip())
    he = TIEN_TO.get(tien_to, 1.0) if tien_to else 1.0
    return he, dv


def tach_dieu_kien(chu: str) -> dict[str, str]:
    """"@ 100 kHz, VDD = 3.3 V" → {"freq": "100 kHz", "vdd": "3.3 V"}.

    Điều kiện có cấu trúc là điều kiện **so sánh được**: VIH ở 3,3 V và VIH ở 5 V là hai
    con số khác nhau, và gộp chúng lại là cách tạo ra một kết luận sai nghe rất hợp lý.
    """
    ra: dict[str, str] = {}
    m = _DIEU_KIEN_TAN.search(chu)
    if m:
        ra["freq"] = m.group(1).strip()
    for k, v in _DIEU_KIEN.findall(chu):
        ra[k.strip().lower()] = v.strip()
    return ra


def chuan_hoa(chu: str, *, don_vi_cot: str = "", ngu_canh: str = "") -> GiaTri:
    """Chuẩn hoá MỘT ô. `don_vi_cot` là đơn vị lấy từ cột Unit của bảng.

    `ngu_canh` giúp đoán đơn vị cho ký hiệu cụt: `100n` cạnh chữ "tụ" là 100 nF. Nếu
    không đoán được thì **để trống**, không bịa — một đơn vị sai còn tệ hơn không có.
    """
    goc = str(chu)
    s = goc.strip()
    g = GiaTri(raw=goc)
    if not s:
        g.co = "ô trống"
        return g

    # Tách phần điều kiện ra trước, rồi chuẩn hoá phần còn lại.
    g.dieu_kien = tach_dieu_kien(s)
    than = re.sub(r"[\(\[]?\s*@[^\)\]]*[\)\]]?", " ", s)
    than = re.sub(r"[\(\[][^\)\]]*=[^\)\]]*[\)\]]", " ", than).strip()

    thap = than.lower().strip(" .*")
    if thap in _KHONG_CO_SO:
        g.co = _KHONG_CO_SO[thap]
        return g
    if re.fullmatch(r"note\s*\d+", thap):
        g.co = _KHONG_CO_SO["note"]
        return g

    # --- min/typ/max chung một ô.
    m = _BA_GIA_TRI.match(than)
    if m:
        g.vmin, g.vtyp, g.vmax = (_so(m.group(1)), _so(m.group(2)), _so(m.group(3)))
        g.don_vi = _don_vi_tu(m.group(4), don_vi_cot)
        return g

    # --- dải min–max.
    m = _DAI.match(than)
    if m:
        g.vmin, g.vmax = _so(m.group(1)), _so(m.group(2))
        g.don_vi = _don_vi_tu(m.group(3), don_vi_cot)
        return g

    # --- ký hiệu kỹ thuật 4R7 / 3V3 / 100n.
    m = _KY_HIEU_KT.match(than)
    if m:
        nguyen, ky, thap_phan = m.groups()
        gt = _so(f"{nguyen}.{thap_phan}")
        if ky in ("R",):
            g.gia_tri, g.don_vi = gt, "Ω"
        elif ky in ("V", "A", "F"):
            g.gia_tri, g.don_vi = gt, ky
        else:
            he, dv = chuan_don_vi(ky, don_vi_cot or _doan_don_vi(ngu_canh))
            g.gia_tri = (gt or 0) * he
            g.don_vi = dv
        return g

    # --- "100n", "4k7" đã bắt ở trên; còn "100n" cụt thì cần ngữ cảnh.
    m = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)\s*([TGMkKhdcmuµμnpf])", than)
    if m:
        dv = don_vi_cot or _doan_don_vi(ngu_canh)
        he, dv = chuan_don_vi(m.group(2), dv)
        gt = _so(m.group(1))
        g.gia_tri = None if gt is None else gt * he
        g.don_vi = dv
        if not dv:
            g.co = (f"“{than}” có tiền tố SI nhưng không rõ đơn vị — cần cột Đơn vị "
                    "hoặc ngữ cảnh")
            g.gia_tri = None
        return g

    # --- số kèm đơn vị.
    m = _SO_DON_VI.match(than)
    if m:
        he, dv = chuan_don_vi(m.group(2), m.group(3))
        gt = _so(m.group(1))
        g.gia_tri = None if gt is None else gt * he
        g.don_vi = dv
        return g

    # --- số trần: lấy đơn vị từ cột.
    m = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)", than)
    if m:
        gt = _so(m.group(1))
        if don_vi_cot:
            he, dv = _tach_don_vi_cot(don_vi_cot)
            g.gia_tri = None if gt is None else gt * he
            g.don_vi = dv
        else:
            g.gia_tri = gt
            g.co = "số không có đơn vị — bảng thiếu cột Đơn vị"
        return g

    g.co = f"không đọc được thành số: “{than[:40]}”"
    return g


def _don_vi_tu(duoi: str, don_vi_cot: str) -> str:
    duoi = (duoi or "").strip()
    if duoi:
        m = re.fullmatch(r"([TGMkKhdcmuµμnpf]?)\s*(\S+)", duoi)
        if m:
            _, dv = chuan_don_vi(m.group(1), m.group(2))
            return dv
    if don_vi_cot:
        return _tach_don_vi_cot(don_vi_cot)[1]
    return ""


def _tach_don_vi_cot(o: str) -> tuple[float, str]:
    """Cột Đơn vị có thể ghi "mV" hay "kΩ" — hệ số nằm luôn trong tiêu đề cột."""
    s = str(o).strip()
    m = re.fullmatch(r"([TGMkKhdcmuµμnpf])\s*(\S+)", s)
    if m:
        return chuan_don_vi(m.group(1), m.group(2))
    return chuan_don_vi("", s)


def _doan_don_vi(ngu_canh: str) -> str:
    """Đoán đơn vị từ ngữ cảnh — chỉ khi chắc chắn, còn lại trả rỗng."""
    c = (ngu_canh or "").lower()
    if any(k in c for k in ("tụ", "capacitor", "cap ", "decoupling")):
        return "F"
    if any(k in c for k in ("điện trở", "resistor", "pull-up", "pullup")):
        return "Ω"
    if any(k in c for k in ("cuộn cảm", "inductor")):
        return "H"
    return ""
