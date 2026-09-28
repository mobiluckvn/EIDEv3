# -*- coding: utf-8 -*-
"""Tải một tài liệu từ URL về đĩa — và nói thật nó là tệp gì.

Trước bước này EIDE có `doc.search_web` (tìm ra ứng viên) và `doc.load` (nạp tệp đã nằm trong
dự án), nhưng **không có đường nào đi từ ứng viên tới tệp**. Người dùng phải tự mở trình duyệt,
tự tải, tự chép vào thư mục dự án. Đo trên dự án bo thật ngày 27/09/2026: đó là chỗ đứt đầu
tiên của luồng "bo thật → tài liệu → firmware".

Hai điều mô-đun này cố ý làm khác bản nhanh nhất có thể viết:

1. **Không tin phần mở rộng, không tin `Content-Type`.** Tin *magic byte* của mấy byte đầu.
   Trang tài liệu của nhiều hãng (ST là một) trả về HTML tường đồng ý cookie cho một URL kết
   thúc bằng `.pdf`. Lưu nguyên khối HTML đó thành `datasheet.pdf` rồi báo "đã tải xong" là
   cách chắc chắn nhất để bước trích Fact sau đó hỏng ở chỗ không ai nghĩ tới.
2. **Không tin `Content-Length`.** Nó là lời khai của máy chủ. Trần dung lượng phải được ép
   trong lúc đọc từng khối, nếu không thì một máy chủ khai 1 KB vẫn đẩy được 4 GB vào đĩa.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

# Trần mặc định. Datasheet lớn nhất từng gặp (reference manual STM32F4, ~1 700 trang) khoảng
# 18 MB; 80 MB đủ rộng cho tài liệu thật và vẫn chặn được việc tải nguyên một bản cài đặt.
TRAN_BYTE = 80 * 1024 * 1024
KHOI = 64 * 1024

# Magic byte → loại tệp. Chỉ những loại `doc.load` đọc được, cộng HTML để nhận ra tường chặn.
_MAGIC: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", "pdf"),
    (b"PK\x03\x04", "zip"),          # docx/xlsx/pptx/odt đều là zip — doc.load phân biệt tiếp
    (b"\xd0\xcf\x11\xe0", "office_cu"),   # .doc/.xls/.ppt đời cũ
    (b"{\\rtf", "rtf"),
)

# Ảnh. Tải được nhưng **không phải tài liệu**: không nạp vào kho để trích dẫn, mà để
# `asset.image_to_c` đổi thành mảng điểm ảnh cho firmware vẽ. Thiếu nhánh này thì tác tử tìm
# đúng logo trên Wikimedia rồi bị chính EIDE chặn ở bước tải — đo được ngày 28/09/2026.
_MAGIC_ANH: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"), (b"GIF89a", "gif"),
    (b"BM", "bmp"),
    (b"II*\x00", "tiff"), (b"MM\x00*", "tiff"),
)


class MoUrl(Protocol):
    """Cách mở một URL. Tách ra để test chạy được mà không cần mạng."""

    def __call__(self, url: str, *, timeout: float) -> Any: ...   # pragma: no cover


@dataclass(slots=True)
class KetQuaTai:
    """Tải xong (hoặc không) thì biết được đúng những gì ghi ở đây, không hơn."""

    dat: bool = False
    url: str = ""
    tep: str = ""                     # tệp SẼ NẠP, rỗng nếu không lưu gì
    tep_goc: str = ""                 # bản gốc giữ lại khi `tep` là bản chuyển đổi
    loai: str = ""                    # pdf | zip | office_cu | rtf | html | khong_biet
    so_byte: int = 0
    hash: str = ""
    content_type: str = ""            # lời khai của máy chủ, giữ lại để đối chiếu
    ung_vien_pdf: list[dict[str, str]] = field(default_factory=list)
    vi_sao_khong_dat: str = ""
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "url": self.url, "tep": self.tep,
                "tep_goc": self.tep_goc, "loai": self.loai,
                "so_byte": self.so_byte, "hash": self.hash,
                "content_type": self.content_type, "ung_vien_pdf": self.ung_vien_pdf,
                "vi_sao_khong_dat": self.vi_sao_khong_dat, "canh_bao": self.canh_bao}


def _loai_theo_magic(dau: bytes) -> str:
    for mau, ten in _MAGIC:
        if dau.startswith(mau):
            return ten
    for mau, _ten in _MAGIC_ANH:
        if dau.startswith(mau):
            return "anh"
    if dau[:4] == b"RIFF" and dau[8:12] == b"WEBP":
        return "anh"
    d = dau[:1024].lstrip().lower()
    # SVG là văn bản XML — phải xét TRƯỚC nhánh html, nếu không một tệp logo .svg sẽ bị coi là
    # một trang web và bị từ chối kèm câu "trên trang không có liên kết PDF nào".
    if b"<svg" in d:
        return "anh"
    if d.startswith((b"<!doctype html", b"<html", b"<?xml")) or b"<html" in d:
        return "html"
    return "khong_biet"


def duoi_anh(dau: bytes) -> str:
    """`.png`/`.jpg`/… suy từ magic byte, để tên tệp lưu ra khớp nội dung thật."""
    for mau, ten in _MAGIC_ANH:
        if dau.startswith(mau):
            return {"jpeg": ".jpg"}.get(ten, f".{ten}")
    if dau[:4] == b"RIFF" and dau[8:12] == b"WEBP":
        return ".webp"
    return ".svg" if b"<svg" in dau[:1024].lower() else ""


def _la_van_ban(b: bytes) -> bool:
    """Khối byte này có phải văn bản đọc được không.

    Hai phép kiểm, và phép thứ hai mới là phép quyết định: UTF-8 giải mã được **và** hầu hết
    ký tự in được. Chỉ kiểm giải mã là chưa đủ — một tệp nhị phân vẫn có thể tình cờ hợp lệ
    UTF-8, và khi đó ta lưu nó thành "tài liệu" rồi trích dẫn "dòng 40" của một mớ ký tự
    điều khiển.
    """
    try:
        chu = b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not chu.strip():
        return False
    mau = chu[:8000]
    xau = sum(1 for c in mau if not (c.isprintable() or c in "\n\r\t\f\v"))
    return xau / max(1, len(mau)) < 0.02


def ten_tu_url(url: str) -> str:
    """Tên tệp an toàn suy ra từ URL. Không bao giờ trả về đường dẫn có `/` hay `..`."""
    from urllib.parse import unquote, urlparse

    duoi = unquote(urlparse(url).path).rsplit("/", 1)[-1]
    duoi = re.sub(r"[^A-Za-z0-9._-]", "-", duoi).strip("-.") or "tai-lieu"
    return duoi[:120]


def _lien_ket_pdf(html: str, url_goc: str) -> list[dict[str, str]]:
    """Các liên kết .pdf trên một trang — ỨNG VIÊN, không phải tài liệu.

    Trả về theo thứ tự xuất hiện, không trùng. Lấy cả chữ trong thẻ `<a>` làm tiêu đề vì người
    dùng chọn tài liệu bằng tên ("Reference manual"), không bằng URL.
    """
    from urllib.parse import urljoin

    ra: list[dict[str, str]] = []
    da: set[str] = set()
    for m in re.finditer(r"<a\b[^>]*?href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>",
                         html, re.I | re.S):
        href = m.group(1).strip()
        if ".pdf" not in href.lower():
            continue
        day_du = urljoin(url_goc, href)
        if not day_du.lower().startswith(("http://", "https://")) or day_du in da:
            continue
        da.add(day_du)
        chu = re.sub(r"<[^>]+>", " ", m.group(2))
        chu = re.sub(r"\s+", " ", chu).strip()
        ra.append({"url": day_du, "tieu_de": chu[:160] or ten_tu_url(day_du)})
    return ra


_BO_THE = re.compile(r"<(script|style|noscript|template|svg)\b.*?</\1\s*>", re.I | re.S)
# Cả thẻ MỞ và thẻ ĐÓNG của khối đều là ranh giới dòng: `<br>bốn<div>năm</div>` chỉ có thẻ
# đóng ở cuối, nên nếu chỉ bắt thẻ đóng thì "bốn" và "năm" dính thành một dòng.
_XUONG_DONG = re.compile(
    r"</?(p|div|li|tr|h[1-6]|td|th|section|article|ul|ol|table|blockquote)\b[^>]*>"
    r"|<br\s*/?>", re.I)


def chu_tu_html(html_chu: str) -> str:
    """Bóc chữ đọc được ra khỏi HTML, giữ ranh giới dòng theo thẻ khối.

    Dùng khi một TRANG WEB chính là tài liệu (trang của nhà phân phối, wiki, trang hướng dẫn).
    Bản chữ này được lưu thành tệp RIÊNG, có hash riêng, và bản HTML gốc vẫn giữ nguyên: trích
    dẫn "dòng 42" phải trỏ vào đúng tệp mà người ta mở ra kiểm lại được, nên không thể vừa
    đánh số theo chữ đã bóc vừa nói là đang trích dẫn tệp HTML.
    """
    from html import unescape

    s = _BO_THE.sub(" ", html_chu)
    s = _XUONG_DONG.sub("\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    dong = [re.sub(r"[ \t ]+", " ", d).strip() for d in s.split("\n")]
    ra: list[str] = []
    for d in dong:
        if d or (ra and ra[-1]):        # gộp nhiều dòng trống thành một
            ra.append(d)
    return "\n".join(ra).strip() + "\n"


def tai_ve(url: str, thu_muc: Path, *, ten_tep: str = "", tran_byte: int = TRAN_BYTE,
           timeout: float = 60.0, nhan_html: bool = False,
           mo_url: Callable[..., Any] | None = None) -> KetQuaTai:
    """Tải `url` vào `thu_muc`. Trả về sự thật đo được, không kèm kết luận "dùng được".

    `dat=True` chỉ có nghĩa: đã có một tệp trên đĩa và ta biết nó thuộc loại nào. Nó **không**
    có nghĩa tệp đó là tài liệu của dự án — việc đó do `doc.load` làm, và tầng tin cậy do
    người dùng khai qua `nguon` (N1).
    """
    kq = KetQuaTai(url=url)
    if not url.lower().startswith(("http://", "https://")):
        kq.vi_sao_khong_dat = (
            f"Chỉ tải được qua http/https. “{url[:60]}” không phải địa chỉ mạng — nếu tệp đã "
            "nằm trên máy thì gọi doc.load với đường dẫn tệp, không cần tải.")
        return kq

    import urllib.error
    import urllib.request

    mo = mo_url or _mo_that
    try:
        with mo(url, timeout=timeout) as r:
            kq.content_type = (r.headers.get("Content-Type") or "").split(";")[0].strip()
            khai = r.headers.get("Content-Length")
            if khai and khai.isdigit() and int(khai) > tran_byte:
                kq.vi_sao_khong_dat = (
                    f"Máy chủ khai tệp {int(khai) / 1e6:.1f} MB, vượt trần "
                    f"{tran_byte / 1e6:.0f} MB. Không tải.")
                return kq
            phan: list[bytes] = []
            tong = 0
            while True:
                b = r.read(KHOI)
                if not b:
                    break
                tong += len(b)
                # Trần ép TRONG lúc đọc: Content-Length ở trên là lời khai, cái này là thước.
                if tong > tran_byte:
                    kq.vi_sao_khong_dat = (
                        f"Đã đọc quá trần {tran_byte / 1e6:.0f} MB mà chưa hết tệp "
                        f"(máy chủ khai {khai or 'không khai'}). Dừng, không lưu.")
                    return kq
                phan.append(b)
    except urllib.error.HTTPError as e:
        from ..errors import network_down                     # noqa: F401  (chỉ để rõ ý)
        kq.vi_sao_khong_dat = f"Máy chủ trả HTTP {e.code} {e.reason}."
        return kq
    except Exception as e:                                    # noqa: BLE001
        kq.vi_sao_khong_dat = f"Không tải được: {type(e).__name__}: {str(e)[:150]}"
        return kq

    noi_dung = b"".join(phan)
    kq.so_byte = len(noi_dung)
    kq.hash = hashlib.sha256(noi_dung).hexdigest()
    kq.loai = _loai_theo_magic(noi_dung)

    if kq.so_byte == 0:
        kq.vi_sao_khong_dat = "Máy chủ trả về 0 byte."
        return kq

    if kq.loai == "html":
        # Mặc định KHÔNG lưu HTML thành tài liệu: trang giới thiệu, tường cookie và trang đăng
        # nhập đều trả 200 OK, và lưu chúng thành `datasheet.pdf` là cách chắc chắn nhất để
        # bước trích Fact về sau hỏng ở chỗ không ai nghĩ tới.
        text = noi_dung.decode("utf-8", errors="replace")
        kq.ung_vien_pdf = _lien_ket_pdf(text, url)
        if not nhan_html:
            kq.vi_sao_khong_dat = (
                f"URL này trả về trang HTML ({kq.so_byte / 1024:.0f} KB), không phải tệp tài "
                "liệu"
                + (f". Trên trang có {len(kq.ung_vien_pdf)} liên kết PDF — chọn một rồi tải "
                   "lại." if kq.ung_vien_pdf else
                   ", và trên trang không có liên kết PDF nào. Nếu CHÍNH TRANG này là tài "
                   "liệu (trang nhà phân phối, wiki, trang hướng dẫn) thì gọi lại với "
                   "`nhan_html=true` để lấy phần chữ của nó."))
            if url.lower().rstrip("/").endswith(".pdf"):
                kq.canh_bao.append(
                    "URL kết thúc bằng .pdf nhưng nội dung là HTML — đừng coi phần mở rộng là "
                    "bằng chứng về loại tệp.")
            return kq

        # Người/tác tử đã BIẾT đây là trang web và vẫn muốn dùng nó làm tài liệu. Giữ cả hai
        # tệp: bản HTML gốc (để đối chiếu về sau) và bản chữ đã bóc (để trích dẫn theo dòng).
        chu = chu_tu_html(text)
        if len(chu.strip()) < 200:
            kq.vi_sao_khong_dat = (
                f"Bóc chữ khỏi trang này chỉ được {len(chu.strip())} ký tự — gần như toàn bộ "
                "nội dung do JavaScript dựng ra, nên không có gì để trích dẫn.")
            return kq
        thu_muc.mkdir(parents=True, exist_ok=True)
        goc = (re.sub(r"[^A-Za-z0-9._-]", "-", ten_tep).strip("-.") if ten_tep
               else ten_tu_url(url))
        goc = re.sub(r"\.(html?|txt)$", "", goc, flags=re.I) or "trang-web"
        (thu_muc / f"{goc}.html").write_bytes(noi_dung)
        (thu_muc / f"{goc}.txt").write_text(chu, "utf-8")
        kq.tep_goc = f"{goc}.html"
        kq.tep = f"{goc}.txt"
        kq.dat = True
        kq.canh_bao.append(
            f"Đây là chữ BÓC RA từ một trang web, không phải tài liệu do hãng phát hành. Bản "
            f"HTML gốc giữ ở {kq.tep_goc}. Nạp nó với `nguon=\"ben_thu_ba\"` trừ khi trang "
            "này thuộc tên miền của chính hãng.")
        return kq

    if kq.loai == "khong_biet":
        # Không có magic byte KHÔNG có nghĩa là không đọc được: header BSP, linker script,
        # Markdown, CSV đều là văn bản thuần. `doc.load` nạp được những thứ đó (trích dẫn theo
        # dòng), nên `doc.fetch` mà từ chối chúng là hai công cụ của cùng một hệ thống nói
        # ngược nhau — đo được trên phiên bo thật: tác tử tìm đúng `stm32469i_discovery.h` rồi
        # bị chính EIDE chặn ở bước tải, và nó kết luận "hãng không lưu tài liệu trên GitHub".
        if _la_van_ban(noi_dung):
            kq.loai = "van_ban"
        else:
            kq.vi_sao_khong_dat = (
                f"Tải về {kq.so_byte} byte nhưng không nhận ra định dạng, và nội dung không "
                f"phải văn bản (máy chủ khai “{kq.content_type or 'không khai'}”, byte đầu "
                f"{noi_dung[:8]!r}). Không lưu.")
            return kq

    thu_muc.mkdir(parents=True, exist_ok=True)
    ten = re.sub(r"[^A-Za-z0-9._-]", "-", ten_tep).strip("-.") if ten_tep else ten_tu_url(url)
    duoi_chuan = ({"pdf": ".pdf", "rtf": ".rtf"}.get(kq.loai, "")
                  or (duoi_anh(noi_dung) if kq.loai == "anh" else ""))
    if duoi_chuan and not ten.lower().endswith(duoi_chuan):
        ten += duoi_chuan
    p = thu_muc / ten
    if p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() != kq.hash:
        # Cùng tên, khác nội dung: giữ cả hai. Ghi đè im lặng là cách mất bản tài liệu cũ mà
        # các Fact đã trích dẫn tới — và trích dẫn thì phải còn kiểm lại được.
        goc, sau = (ten.rsplit(".", 1) + [""])[:2]
        p = thu_muc / (f"{goc}-{kq.hash[:8]}" + (f".{sau}" if sau else ""))
        kq.canh_bao.append(f"Đã có tệp cùng tên với nội dung khác — lưu thành {p.name}.")
    p.write_bytes(noi_dung)
    kq.tep = p.name
    kq.dat = True
    return kq


def _mo_that(url: str, *, timeout: float) -> Any:
    """Mở URL thật. Khai một User-Agent thường: nhiều máy chủ của hãng trả 403 cho urllib."""
    import urllib.request

    req = urllib.request.Request(url, headers={
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
        "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
    })
    return urllib.request.urlopen(req, timeout=timeout)       # noqa: S310  (đã ép http/https)
