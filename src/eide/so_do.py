# -*- coding: utf-8 -*-
"""Vẽ sơ đồ mermaid thành PNG — cho tài liệu tác tử xuất ra (Word · PowerPoint · PDF · Excel).

## Vì sao có tệp này, khi giao diện đã vẽ được

Giao diện vẽ bằng SwiftUI, trong app. Lõi Python chạy **không có app** — nó là tiến trình con,
và `doc.render` phải làm ra tệp ngay cả khi chạy từ dòng lệnh. Nên chỗ này cần một bộ vẽ riêng.

Trước tệp này, một tài liệu xuất ra có sơ đồ sẽ in **nguyên mã mermaid** vào giữa trang Word —
đúng thứ người nhận không đọc được, và đúng chỗ người ta chờ một hình.

## Cái giá: hai bộ đọc cho một cú pháp

`Views/SoDo.swift` và tệp này đọc cùng một tập con mermaid bằng hai ngôn ngữ. Đó là một cái
giá thật, nói ra chứ không giấu — sửa cú pháp thì phải sửa hai nơi.

Đổi lại thì tránh được ba thứ đắt hơn: lõi phải gọi ngược lên app (lõi là tiến trình con,
chiều gọi chỉ có một), hoặc nhúng một trình duyệt vào lõi, hoặc bắt người dùng cài Node.
Và ràng buộc được giữ bằng **bộ kiểm dùng chung một tập sơ đồ thật**: cùng những tệp trong
`docs/` và `du-lieu/`, cả hai bên phải đọc ra cùng số vai, cùng số khối, cùng nhãn.

## Chỗ nó KHÔNG làm

Không vẽ kiểu nào ngoài `sequenceDiagram` và `graph`/`flowchart`. Gặp kiểu khác thì trả `None`,
và `xuat_ban.py` in khối mã **kèm một câu nói rõ là chưa vẽ được** — chứ không lặng lẽ bỏ hình.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Phông có dấu tiếng Việt. Thứ tự là thứ tự ưu tiên; thiếu hết thì trả về `None` và nơi gọi
# in mã thay vì vẽ một hình đầy ô vuông.
PHONG = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
)

MAU_NEN = (255, 255, 255, 255)
MAU_HOP = (219, 234, 254, 255)          # xanh nhạt
MAU_VIEN = (59, 130, 246, 255)
MAU_CHU = (17, 24, 39, 255)
MAU_MO = (107, 114, 128, 255)
MAU_GHI_CHU = (254, 249, 195, 255)
MAU_VIEN_GHI_CHU = (202, 138, 4, 255)


# ============================================================================ mô hình
@dataclass(slots=True)
class Khoi:
    ma: str
    nhan: str
    hinh: str = "hop"                    # hop | bau | tron | thoi
    cum: int | None = None


@dataclass(slots=True)
class Canh:
    tu: int
    den: int
    nhan: str = ""
    net: str = "lien"                    # lien | dut | dam


@dataclass(slots=True)
class Luong:
    ngang: bool
    nut: list[Khoi] = field(default_factory=list)
    canh: list[Canh] = field(default_factory=list)
    cum: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Vai:
    ma: str
    nhan: str
    la_nguoi: bool = False


@dataclass(slots=True)
class TuanTu:
    vai: list[Vai] = field(default_factory=list)
    dong: list[tuple] = field(default_factory=list)   # (loai, ...) — xem `_tuan_tu`
    danh_so: bool = False


# ============================================================================ đọc
def kieu(nguon: str) -> str:
    for d in nguon.splitlines():
        t = d.strip()
        if not t or t.startswith("%%"):
            continue
        return t.split()[0]
    return ""


def doc(nguon: str) -> TuanTu | Luong | None:
    k = kieu(nguon)
    if k == "sequenceDiagram":
        return _tuan_tu(nguon)
    if k in ("graph", "flowchart"):
        return _luong(nguon)
    return None


def _go_the(s: str) -> str:
    t = s.strip()
    if len(t) >= 2 and t[0] == t[-1] == '"':
        t = t[1:-1]
    for the in ("<br/>", "<br>", "<br />"):
        t = t.replace(the, "\n")
    return t.replace("&nbsp;", " ").strip()


# Mũi tên xếp DÀI TRƯỚC NGẮN: `->>` là tiền tố của `-->>` khi dò từ trái, nên dò ngắn trước
# sẽ cắt mọi lời đáp thành lời gọi.
_MUI = (("-->>", "dut"), ("--x", "dut"), ("--)", "dut"), ("-->", "dut"),
        ("->>", "lien"), ("-x", "lien"), ("-)", "lien"), ("->", "lien"))
_KHOI_TU = ("loop", "alt", "opt", "par", "critical", "break", "rect")


def _tuan_tu(nguon: str) -> TuanTu | None:
    t = TuanTu()
    chi_so: dict[str, int] = {}

    def vi_tri(ma: str, *, nguoi: bool = False, nhan: str | None = None) -> int:
        m = ma.strip()
        if m in chi_so:
            i = chi_so[m]
            if nhan and t.vai[i].nhan == t.vai[i].ma:
                t.vai[i].nhan = nhan
            t.vai[i].la_nguoi = t.vai[i].la_nguoi or nguoi
            return i
        t.vai.append(Vai(m, nhan or m, nguoi))
        chi_so[m] = len(t.vai) - 1
        return len(t.vai) - 1

    mo = 0
    for raw in nguon.splitlines():
        d = raw.strip()
        if not d or d.startswith("%%") or d == "sequenceDiagram":
            continue
        if d == "autonumber":
            t.danh_so = True
            continue
        if d.startswith(("activate ", "deactivate ")):
            continue
        if d.startswith(("participant ", "actor ")):
            nguoi = d.startswith("actor ")
            than = d[6:] if nguoi else d[12:]
            if " as " in than:
                a, b = than.split(" as ", 1)
                vi_tri(a, nguoi=nguoi, nhan=_go_the(b))
            else:
                vi_tri(than, nguoi=nguoi)
            continue
        if d == "end":
            if mo > 0:
                mo -= 1
                t.dong.append(("dong",))
            continue
        kt = next((k for k in _KHOI_TU if d == k or d.startswith(k + " ")), None)
        if kt:
            mo += 1
            t.dong.append(("mo", kt, _go_the(d[len(kt):])))
            continue
        if d == "else" or d.startswith("else "):
            t.dong.append(("khac", _go_the(d[4:])))
            continue
        if d.lower().startswith("note "):
            g = _ghi_chu(d[5:], vi_tri)
            if g:
                t.dong.append(g)
            continue
        tn = _tin(d, vi_tri)
        if tn:
            t.dong.append(tn)

    if not t.vai or not any(x[0] == "tin" for x in t.dong):
        return None
    t.dong.extend([("dong",)] * mo)
    return t


def _ghi_chu(than: str, vi_tri) -> tuple | None:
    if ":" not in than:
        return None
    dau, chu = than.split(":", 1)
    dau = dau.strip()
    for tien in ("over ", "left of ", "right of "):
        if dau.startswith(tien):
            dau = dau[len(tien):]
            break
    cot = [vi_tri(x.strip()) for x in dau.split(",") if x.strip()]
    if not cot:
        return None
    return ("ghi_chu", cot[0], cot[-1], _go_the(chu))


def _tin(d: str, vi_tri) -> tuple | None:
    if ":" not in d:
        return None
    dau, chu = d.split(":", 1)
    for m, net in _MUI:
        if m in dau:
            a, b = dau.split(m, 1)
            if not a.strip() or not b.strip():
                return None
            return ("tin", vi_tri(a.strip()), vi_tri(b.strip()), _go_the(chu), net)
    return None


# Mũi tên HAI CHIỀU đứng trước mũi tên một chiều, vì `<-->` chứa `-->`.
#
# Thiếu chúng thì `A <--> B` bị cắt ở `-->`, phần trái còn lại là `"A <"` — và vì nó có dấu
# cách nên không khớp mẫu khai nút, rơi xuống nhánh mặc định và **đẻ ra một khối tên
# `MOD_MCU <`**. Nhìn thấy trong app ngày 29/09/2026 trên sơ đồ tác tử vừa vẽ: một khối thừa,
# tên vô nghĩa, và không con số nào kêu.
_NOI = (("<-.->", "dut"), ("<-->", "lien"), ("<==>", "dam"),
        ("-.->", "dut"), ("-.-", "dut"), ("==>", "dam"), ("===", "dam"),
        ("-->", "lien"), ("---", "lien"), ("->", "lien"))
_BOC = (("((", "))", "tron"), ("{{", "}}", "thoi"), ("[", "]", "hop"),
        ("(", ")", "bau"), ("{", "}", "thoi"))


def _khai_nut(d: str) -> tuple[str, str | None, str | None] | None:
    for mo, dong, hinh in _BOC:
        i = d.find(mo)
        if i <= 0 or not d.endswith(dong):
            continue
        ma = d[:i].strip()
        if not ma or " " in ma:
            continue
        return ma, _go_the(d[i + len(mo):-len(dong)]), hinh
    ma = d.strip()
    if not ma or " " in ma:
        return None
    return ma, None, None


def _luong(nguon: str) -> Luong | None:
    ra = Luong(ngang=True)
    chi_so: dict[str, int] = {}
    cum_nay: int | None = None

    def ghi(ma: str, nhan: str | None, hinh: str | None) -> int:
        m = ma.strip()
        if m in chi_so:
            i = chi_so[m]
            if nhan:
                ra.nut[i].nhan = nhan
                if hinh:
                    ra.nut[i].hinh = hinh
            return i
        ra.nut.append(Khoi(m, nhan or m, hinh or "hop", cum_nay))
        chi_so[m] = len(ra.nut) - 1
        return len(ra.nut) - 1

    for raw in nguon.splitlines():
        d = raw.split("%%")[0].strip()
        if not d:
            continue
        if d.startswith(("graph ", "flowchart ")):
            h = d.split()[-1]
            ra.ngang = h.startswith(("L", "R"))
            continue
        if d.startswith(("classDef ", "class ", "style ", "click ", "linkStyle ")):
            continue
        if d.startswith("subgraph"):
            than = d[8:].strip()
            m = re.match(r'^\S*\[(.*)\]$', than)
            ra.cum.append(_go_the(m.group(1) if m else than))
            cum_nay = len(ra.cum) - 1
            continue
        if d == "end":
            cum_nay = None
            continue
        c = _doc_canh(d, ghi)
        if c:
            ra.canh.extend(c)
            continue
        kn = _khai_nut(d)
        if kn:
            ghi(*kn)

    return ra if ra.nut else None


def _doc_canh(d: str, ghi) -> list[Canh] | None:
    doan: list[str] = []
    net: list[str] = []
    con = d
    while True:
        som = None
        for m, n in _NOI:
            i = con.find(m)
            if i >= 0 and (som is None or i < som[0]):
                som = (i, m, n)
        if som is None:
            break
        i, m, n = som
        doan.append(con[:i])
        net.append(n)
        con = con[i + len(m):]
    if not doan:
        return None
    doan.append(con)

    ra: list[Canh] = []
    truoc: int | None = None
    for i, phan in enumerate(doan):
        t = phan.strip()
        nhan = ""
        if t.startswith("|") and "|" in t[1:]:
            j = t.index("|", 1)
            nhan = _go_the(t[1:j])
            t = t[j + 1:].strip()
        if not t:
            truoc = None
            continue
        kn = _khai_nut(t) or (t, None, None)
        vt = ghi(*kn)
        if truoc is not None and i > 0:
            ra.append(Canh(truoc, vt, nhan, net[i - 1]))
        truoc = vt
    return ra or None


# ============================================================================ vẽ
def _phong(co: int):
    from PIL import ImageFont

    for p in PHONG:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, co)
            except OSError:
                continue
    return None


def _do(ve, s: str, f) -> tuple[int, int]:
    """Bề rộng/cao một khối chữ nhiều dòng."""
    s = bo_emoji(s)
    if not s:
        return 0, 0
    w = h = 0
    for d in s.split("\n"):
        a = ve.textbbox((0, 0), d, font=f)
        w = max(w, a[2] - a[0])
        h += (a[3] - a[1]) + 4
    return w, h


# Emoji và ký hiệu hình. Phông có dấu tiếng Việt trên macOS (`Arial Unicode`) không có
# chúng, nên Pillow vẽ ra một Ô VUÔNG RỖNG — và một ô vuông rỗng trông như lỗi phông, người
# đọc sẽ nghĩ tài liệu hỏng. Bỏ hẳn thì nhãn sạch và không ai mất gì: emoji trong nhãn sơ đồ
# là trang trí, nghĩa nằm ở chữ bên cạnh.
_EMOJI = re.compile("[" + "".join((
    "\U0001F300-\U0001FAFF", "\U00002600-\U000027BF",
    "\U0001F000-\U0001F0FF", "\U0000FE00-\U0000FE0F",
    "\U00002190-\U000021FF", "\U00002B00-\U00002BFF")) + "]+")


def bo_emoji(s: str) -> str:
    return _EMOJI.sub("", s).replace("  ", " ").strip()


def _chu(ve, s: str, x: int, y: int, f, mau, giua: bool = True, nen=None) -> None:
    """Vẽ chữ nhiều dòng, `(x, y)` là TÂM khối chữ (hoặc mép trái nếu `giua=False`)."""
    s = bo_emoji(s)
    if not s:
        return
    dong = s.split("\n")
    w, h = _do(ve, s, f)
    if nen is not None:
        x0 = x - w // 2 - 3 if giua else x - 3
        ve.rectangle([x0, y - h // 2 - 2, x0 + w + 6, y - h // 2 + h + 2], fill=nen)
    cy = y - h // 2
    for d in dong:
        a = ve.textbbox((0, 0), d, font=f)
        dw, dh = a[2] - a[0], a[3] - a[1]
        ve.text((x - dw // 2 if giua else x, cy - a[1]), d, font=f, fill=mau)
        cy += dh + 4


def _mui_ten(ve, x1, y1, x2, y2, mau, dai=8) -> None:
    import math

    goc = math.atan2(y2 - y1, x2 - x1)
    p = [(x2, y2),
         (x2 - dai * math.cos(goc - 0.42), y2 - dai * math.sin(goc - 0.42)),
         (x2 - dai * math.cos(goc + 0.42), y2 - dai * math.sin(goc + 0.42))]
    ve.polygon(p, fill=mau)


def _net(ve, x1, y1, x2, y2, mau, net: str) -> None:
    """Vẽ đoạn thẳng; `dut` thì vẽ từng nhịp."""
    rong = 3 if net == "dam" else 2
    if net != "dut":
        ve.line([(x1, y1), (x2, y2)], fill=mau, width=rong)
        return
    import math

    d = math.hypot(x2 - x1, y2 - y1) or 1
    n = int(d // 10)
    for i in range(n + 1):
        a, b = i * 10 / d, min((i * 10 + 6) / d, 1.0)
        ve.line([(x1 + (x2 - x1) * a, y1 + (y2 - y1) * a),
                 (x1 + (x2 - x1) * b, y1 + (y2 - y1) * b)], fill=mau, width=rong)


def ve_png(nguon: str, ra: Path, *, rong_toi_da: int = 1700) -> tuple[Path | None, str]:
    """Vẽ một khối mermaid ra PNG. Trả `(đường dẫn, lý do nếu không vẽ được)`."""
    try:
        from PIL import Image, ImageDraw
    except ImportError as e:                                           # pragma: no cover
        return None, f"thiếu Pillow: {e}"

    mo_hinh = doc(nguon)
    if mo_hinh is None:
        return None, f"chưa vẽ được kiểu sơ đồ {kieu(nguon)!r}"
    f = _phong(15)
    if f is None:
        # Vẽ bằng phông mặc định của Pillow sẽ ra một hình đầy ô vuông ở mọi chữ có dấu — tệ
        # hơn hẳn việc in mã ra cho người đọc.
        return None, "máy không có phông chữ nào đọc được dấu tiếng Việt"

    if isinstance(mo_hinh, TuanTu):
        anh = _ve_tuan_tu(mo_hinh, Image, ImageDraw, f)
    else:
        anh = _ve_luong(mo_hinh, Image, ImageDraw, f)
        # Sơ đồ quá bè thì XOAY HƯỚNG CHẢY rồi chọn bản vuông vắn hơn.
        #
        # Trang A4 rộng 6,5 inch. Một `graph LR` 12 khối ra tấm ảnh tỉ lệ 6:1, thu cho vừa
        # trang thì cao còn hơn một inch — chữ trong khối nhỏ tới mức không đọc được. Đo
        # được trên tài liệu kiến trúc C4 thật: hình vào đúng chỗ, kèm chú thích đầy đủ, mà
        # không ai đọc nổi chữ trong đó. Một hình không đọc được thì cũng bằng không có.
        #
        # Hướng chảy là chuyện TRÌNH BÀY, không phải chuyện nội dung: `A --> B` vẫn là `A`
        # trỏ tới `B` dù vẽ ngang hay vẽ dọc. Nên đổi hướng cho vừa giấy là hợp lệ.
        if anh is not None and anh.width > anh.height * 2.2:
            khac = _ve_luong(Luong(not mo_hinh.ngang, mo_hinh.nut, mo_hinh.canh,
                                   mo_hinh.cum), Image, ImageDraw, f)
            if khac is not None:
                def _lech(a):
                    t = a.width / max(a.height, 1)
                    return abs(t - 1.35)
                if _lech(khac) < _lech(anh):
                    anh = khac
    if anh is None:
        return None, "sơ đồ rỗng"
    if anh.width > rong_toi_da:
        # Thu nhỏ cho vừa khổ giấy. Thu chứ không cắt: cắt là mất nội dung mà không báo.
        t = rong_toi_da / anh.width
        anh = anh.resize((rong_toi_da, max(int(anh.height * t), 1)), Image.LANCZOS)
    ra.parent.mkdir(parents=True, exist_ok=True)
    anh.save(ra, "PNG")
    return ra, ""


def _ve_tuan_tu(so: TuanTu, Image, ImageDraw, f):
    do = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    f_nho = _phong(13) or f

    rong = []
    for i, v in enumerate(so.vai):
        rong.append(max(_do(do, v.nhan, f)[0] + 26, 90))
    for x in so.dong:
        if x[0] == "tin":
            w = _do(do, x[3], f_nho)[0] // 2 + 20
            rong[x[1]] = max(rong[x[1]], w)
            rong[x[2]] = max(rong[x[2]], w)

    le, dem = 16, 40
    tam, x = [], le
    for w in rong:
        tam.append(x + w // 2)
        x += w + dem
    tong_rong = x - dem + le

    cao_dau = 56
    y = cao_dau + 18
    vi_tri = []
    for x_ in so.dong:
        if x_[0] == "tin":
            y += 44
            vi_tri.append(y)
        elif x_[0] == "ghi_chu":
            h = _do(do, x_[3], f_nho)[1] + 20
            y += h // 2 + 10
            vi_tri.append(y)
            y += h // 2 + 10
        elif x_[0] in ("mo", "khac"):
            y += 30
            vi_tri.append(y)
        else:
            y += 14
            vi_tri.append(y)
    tong_cao = y + 26

    anh = Image.new("RGB", (tong_rong, tong_cao), MAU_NEN[:3])
    ve = ImageDraw.Draw(anh)

    for t in tam:                                                       # đường đời
        for yy in range(cao_dau, tong_cao - 10, 9):
            ve.line([(t, yy), (t, min(yy + 5, tong_cao - 10))], fill=(190, 195, 205), width=1)

    ngan: list[tuple[int, int, str, str]] = []
    for i, x_ in enumerate(so.dong):
        if x_[0] == "mo":
            ngan.append((i, vi_tri[i], x_[1], x_[2]))
        elif x_[0] == "dong" and ngan:
            _, y0, loai, nhan = ngan.pop()
            ve.rounded_rectangle([le // 2, y0 - 18, tong_rong - le // 2, vi_tri[i] + 8],
                                 radius=6, outline=MAU_VIEN, width=2)
            # Căn TRÁI, không căn giữa: căn giữa ở `le//2 + 60` làm nhãn dài tràn ra khỏi
            # mép trái tấm ảnh và chữ `loop` bị cắt cụt thành `p`.
            _chu(ve, f"{loai} {nhan}".strip(), le // 2 + 8, y0 - 10, f_nho, MAU_VIEN[:3],
                 giua=False, nen=MAU_NEN[:3])

    stt = 0
    for i, x_ in enumerate(so.dong):
        y = vi_tri[i]
        if x_[0] == "tin":
            stt += 1
            _, a, b, chu, net = x_
            nhan = f"{stt}. {chu}" if so.danh_so else chu
            if a == b:
                ve.line([(tam[a], y - 9), (tam[a] + 26, y - 9), (tam[a] + 26, y + 6),
                         (tam[a], y + 6)], fill=MAU_CHU[:3], width=2)
                _mui_ten(ve, tam[a] + 26, y + 6, tam[a], y + 6, MAU_CHU[:3])
                _chu(ve, nhan, tam[a] + 34, y - 2, f_nho, MAU_CHU[:3], giua=False,
                     nen=MAU_NEN[:3])
            else:
                _net(ve, tam[a], y, tam[b], y, MAU_CHU[:3] if net != "dut" else MAU_MO[:3], net)
                _mui_ten(ve, tam[a], y, tam[b], y,
                         MAU_CHU[:3] if net != "dut" else MAU_MO[:3])
                _chu(ve, nhan, (tam[a] + tam[b]) // 2, y - 14, f_nho, MAU_CHU[:3],
                     nen=MAU_NEN[:3])
        elif x_[0] == "ghi_chu":
            _, a, b, chu = x_
            w, h = _do(do, chu, f_nho)
            g = (tam[a] + tam[b]) // 2
            ve.rounded_rectangle([g - w // 2 - 12, y - h // 2 - 9,
                                  g + w // 2 + 12, y + h // 2 + 9],
                                 radius=4, fill=MAU_GHI_CHU[:3], outline=MAU_VIEN_GHI_CHU[:3])
            _chu(ve, chu, g, y, f_nho, MAU_CHU[:3])
        elif x_[0] == "khac":
            for xx in range(le, tong_rong - le, 9):
                ve.line([(xx, y - 10), (min(xx + 5, tong_rong - le), y - 10)],
                        fill=MAU_VIEN[:3], width=1)
            _chu(ve, x_[1] or "khác", le + 8, y, f_nho, MAU_VIEN[:3], giua=False,
                 nen=MAU_NEN[:3])

    for i, v in enumerate(so.vai):                                      # hộp tên vai
        w = rong[i]
        r = [tam[i] - w // 2, 8, tam[i] + w // 2, cao_dau - 8]
        ve.rounded_rectangle(r, radius=18 if v.la_nguoi else 6,
                             fill=MAU_HOP[:3], outline=MAU_VIEN[:3], width=2)
        _chu(ve, v.nhan, tam[i], (8 + cao_dau - 8) // 2, f, MAU_CHU[:3])
    return anh


def _ve_luong(so: Luong, Image, ImageDraw, f):
    do = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    f_nho = _phong(12) or f

    # --- cắt cạnh lùi rồi xếp tầng (xem `SoDoView.swift` về vì sao phải cắt trước) -----
    ke: list[list[int]] = [[] for _ in so.nut]
    for i, c in enumerate(so.canh):
        if c.tu < len(so.nut) and c.den < len(so.nut):
            ke[c.tu].append(i)
    trang = [0] * len(so.nut)
    lui: set[int] = set()

    def sau(v: int) -> None:
        trang[v] = 1
        for i in ke[v]:
            d = so.canh[i].den
            if trang[d] == 1:
                lui.add(i)
            elif trang[d] == 0:
                sau(d)
        trang[v] = 2

    for v in range(len(so.nut)):
        if trang[v] == 0:
            sau(v)

    tang = [0] * len(so.nut)
    for _ in range(len(so.nut)):
        doi = False
        for i, c in enumerate(so.canh):
            if i in lui or c.tu >= len(tang) or c.den >= len(tang):
                continue
            if tang[c.den] < tang[c.tu] + 1:
                tang[c.den] = tang[c.tu] + 1
                doi = True
        if not doi:
            break

    kt = []
    for n in so.nut:
        w, h = _do(do, n.nhan, f)
        w, h = max(w + 30, 90), max(h + 22, 44)
        if n.hinh == "tron":
            w = h = max(w, h)
        kt.append((w, h))

    cho = [(0, 0)] * len(so.nut)
    for c in so.canh:
        if not c.nhan:
            continue
        w, h = _do(do, c.nhan, f_nho)
        for i in (c.tu, c.den):
            if i < len(cho):
                cho[i] = (max(cho[i][0], w), max(cho[i][1], h))

    theo_tang: list[list[int]] = [[] for _ in range(max(tang) + 1)]
    for i, t in enumerate(tang):
        theo_tang[t].append(i)

    le, dem_ngang = 20, (26 if so.ngang else 44)

    def o_ngang(i: int) -> int:
        return max(kt[i][1], cho[i][1]) if so.ngang else max(kt[i][0], cho[i][0])

    giua = [0] * len(so.nut)
    if theo_tang:
        x = le
        for i in theo_tang[-1]:
            giua[i] = x + o_ngang(i) // 2
            x += o_ngang(i) + dem_ngang

    con: list[list[int]] = [[] for _ in so.nut]
    for i, c in enumerate(so.canh):
        if i not in lui and c.tu < len(so.nut) and c.den < len(so.nut):
            con[c.tu].append(c.den)

    for li in range(len(theo_tang) - 2, -1, -1):
        muon = []
        for i in theo_tang[li]:
            ds = [d for d in con[i] if tang[d] > li]
            muon.append((i, sum(giua[d] for d in ds) / len(ds) if ds else float("inf")))
        muon.sort(key=lambda p: (p[1], p[0]))
        x = le
        for i, m in muon:
            nua = o_ngang(i) // 2
            tam = int(max(x + nua, m if m != float("inf") else x + nua))
            giua[i] = tam
            x = tam + nua + dem_ngang

    doi = min((giua[i] - o_ngang(i) // 2 for i in range(len(so.nut))), default=le) - le
    khung = [None] * len(so.nut)
    chay, toi_da_ngang = le, 0
    for hang in theo_tang:
        day = max((kt[i][0] if so.ngang else kt[i][1]) for i in hang)
        dem_tang = max((cho[i][0] if so.ngang else cho[i][1]) for i in hang)
        dem_tang = int(dem_tang * (2.4 if any(con[i] for i in hang) else 1))
        for i in hang:
            t = giua[i] - doi
            if so.ngang:
                khung[i] = (chay + (day - kt[i][0]) // 2, t - kt[i][1] // 2, *kt[i])
            else:
                khung[i] = (t - kt[i][0] // 2, chay + (day - kt[i][1]) // 2, *kt[i])
            toi_da_ngang = max(toi_da_ngang, t + o_ngang(i) // 2 + le)
        chay += day + dem_ngang + dem_tang

    w = (chay if so.ngang else toi_da_ngang) + le
    h = (toi_da_ngang if so.ngang else chay) + le
    anh = Image.new("RGB", (max(w, 240), max(h, 120)), MAU_NEN[:3])
    ve = ImageDraw.Draw(anh)

    for ci in range(len(so.cum)):                                       # khung cụm
        trong = [khung[i] for i, n in enumerate(so.nut) if n.cum == ci and khung[i]]
        if not trong:
            continue
        x0 = min(k[0] for k in trong) - 12
        y0 = min(k[1] for k in trong) - 24
        x1 = max(k[0] + k[2] for k in trong) + 12
        y1 = max(k[1] + k[3] for k in trong) + 12
        ve.rounded_rectangle([x0, y0, x1, y1], radius=8, outline=MAU_VIEN[:3], width=1)
        _chu(ve, so.cum[ci], x0 + 8, y0 + 10, f_nho, MAU_VIEN[:3], giua=False,
             nen=MAU_NEN[:3])

    # Gieo sẵn khung các NÚT: nhãn phải tránh cả hộp khối, không chỉ tránh nhãn khác. Nhìn
    # trong app thấy `VCC / GND` nằm đè lên chữ `Khối vi điều khiển`.
    da_dat: list[tuple[int, int, int, int]] = [
        (k[0], k[1], k[0] + k[2], k[1] + k[3]) for k in khung if k]
    for c in so.canh:
        if c.tu >= len(khung) or c.den >= len(khung):
            continue
        a, b = khung[c.tu], khung[c.den]
        if so.ngang:
            p1 = (a[0] + a[2], a[1] + a[3] // 2)
            p2 = (b[0], b[1] + b[3] // 2)
        else:
            p1 = (a[0] + a[2] // 2, a[1] + a[3])
            p2 = (b[0] + b[2] // 2, b[1])
        mau = MAU_MO[:3] if c.net == "dut" else (75, 85, 99)
        _net(ve, *p1, *p2, mau, c.net)
        _mui_ten(ve, *p1, *p2, mau)
        if c.nhan:
            # Thử vài chỗ dọc đường, lấy chỗ đầu tiên không chạm nhãn đã đặt. Không chỗ nào
            # trống thì vẫn vẽ ở chỗ cuối — một nhãn hơi chồng còn đọc mò được, một nhãn biến
            # mất thì người đọc không biết là đã mất.
            lw, lh = _do(do, c.nhan, f_nho)
            o = None
            for t in (0.5, 0.66, 0.36, 0.8, 0.22):
                cx = int(p1[0] + (p2[0] - p1[0]) * t)
                cy = int(p1[1] + (p2[1] - p1[1]) * t)
                o = (cx - lw // 2 - 3, cy - lh // 2 - 2, cx + lw // 2 + 3, cy + lh // 2 + 2)
                if not any(not (o[2] < q[0] or q[2] < o[0] or o[3] < q[1] or q[3] < o[1])
                           for q in da_dat):
                    break
            da_dat.append(o)
            ve.rectangle(o, fill=MAU_NEN[:3])
            _chu(ve, c.nhan, (o[0] + o[2]) // 2, (o[1] + o[3]) // 2, f_nho, MAU_MO[:3])

    for i, n in enumerate(so.nut):                                      # nút
        x0, y0, w0, h0 = khung[i]
        r = [x0, y0, x0 + w0, y0 + h0]
        if n.hinh == "tron":
            ve.ellipse(r, fill=MAU_HOP[:3], outline=MAU_VIEN[:3], width=2)
        elif n.hinh == "bau":
            ve.rounded_rectangle(r, radius=h0 // 2, fill=MAU_HOP[:3],
                                 outline=MAU_VIEN[:3], width=2)
        elif n.hinh == "thoi":
            ve.polygon([(x0 + w0 // 2, y0), (x0 + w0, y0 + h0 // 2),
                        (x0 + w0 // 2, y0 + h0), (x0, y0 + h0 // 2)],
                       fill=MAU_HOP[:3], outline=MAU_VIEN[:3])
        else:
            ve.rounded_rectangle(r, radius=8, fill=MAU_HOP[:3], outline=MAU_VIEN[:3], width=2)
        _chu(ve, n.nhan, x0 + w0 // 2, y0 + h0 // 2, f, MAU_CHU[:3])
    return anh


# ============================================================================ tóm tắt
def tom_tat(nguon: str) -> str:
    """Câu mô tả sơ đồ — dùng làm chú thích hình và lời thay ảnh."""
    m = doc(nguon)
    if isinstance(m, TuanTu):
        return (f"Sơ đồ tuần tự · {len(m.vai)} vai · "
                f"{sum(1 for x in m.dong if x[0] == 'tin')} bước")
    if isinstance(m, Luong):
        return f"Sơ đồ khối · {len(m.nut)} khối · {len(m.canh)} nối"
    return f"mermaid · {kieu(nguon)}"
