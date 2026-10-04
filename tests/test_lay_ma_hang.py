# -*- coding: utf-8 -*-
"""DEV-335 — lấy mã của hãng về thư mục được biên dịch.

Hai lỗi đo được trên phiên RTOS ngày 04/10/2026, cùng một họ: **một hàm có quyền đổi tên tệp,
và chỗ gọi nó lại tự nhớ tên mình đã xin.**

1. Tệp tải thử nằm lại trong `firmware/`. `lay_sdk` tải một tệp để dò nhánh, xin tên
   `.eide-thu-nhanh`, rồi xoá `.eide-thu-nhanh`. Nhưng `tai_ve` làm sạch tên bằng
   `.strip("-.")` nên dấu chấm đầu bị cắt, tệp ghi ra thành `eide-thu-nhanh` — **không ẩn**,
   nằm giữa mã nguồn của người dùng, và lệnh xoá nhắm vào một cái tên không tồn tại. Trên đĩa
   còn lại ba tệp: `eide-thu-nhanh`, `eide-thu-nhanh-223cd9d0`, `eide-thu-nhanh-f18a6eab`.

2. Cùng tên khác nội dung thì giữ cả hai bản — **đúng cho tài liệu, sai cho mã nguồn.** Chính
   sách ấy có lý do thật: một Fact đã trích dẫn tới bản tài liệu cũ thì bản ấy phải còn kiểm
   lại được. Nhưng với tệp `.c` trong thư mục được biên dịch, giữ cả hai nghĩa là **cả hai vào
   dòng lệnh dịch**. Đo được: trong 45 tệp `.c` của lượt dịch có cả `ft6x06.c` và
   `ft6x06-ac138c52.c`, cả `nt35510.c` và `nt35510-6b3d5f5f.c`, cả `otm8009a.c` và
   `otm8009a-1bf0e24c.c`. Lần ấy link được **chỉ vì hai bản đặt tên hàm khác nhau**; cùng tên
   hàm là lỗi link, mà tệ hơn lỗi link là *link đúng bản sai*.

Chỗ hỏng không nằm ở chính sách. Nó nằm ở việc **chỉ có một chính sách cho hai loại tệp**.
"""

from __future__ import annotations

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from eide.knowledge import sdk_hang as SDK      # noqa: E402
from eide.knowledge import tai_ve as TV         # noqa: E402


class _GiaUrl:
    """Thay `urlopen`. Trả nội dung khác nhau cho cùng một URL theo số lần gọi — đúng tình
    huống thật: hãng cập nhật tệp, hoặc hai nhánh có hai bản."""

    def __init__(self, cac_ban: list[bytes]):
        self.cac_ban = cac_ban
        self.lan = 0

    def __call__(self, *a, **k):
        noi_dung = self.cac_ban[min(self.lan, len(self.cac_ban) - 1)]
        self.lan += 1
        return _GiaPhanHoi(noi_dung)


class _GiaPhanHoi:
    def __init__(self, noi_dung: bytes):
        self._n = noi_dung
        self.headers = {"Content-Type": "text/plain", "Content-Length": str(len(noi_dung))}

    def read(self, n: int = -1) -> bytes:
        ra, self._n = self._n, b""
        return ra

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ------------------------------------------------- 1 · không để lại tệp tải thử
def test_tep_tai_thu_khong_nam_lai_trong_thu_muc_ma(tmp_path, monkeypatch):
    """Nhánh tải thử CHỈ chạy khi `mo_url is None`, nên phải thay `tai_ve` chứ không thay URL.

    Bản đầu của ca này truyền `mo_url` vào `lay_sdk` — và nhánh tải thử không hề chạy, nên ca
    xanh cả khi lệnh dọn vẫn là bản cũ. Một ca kiểm nhìn đúng mà **không chạm vào đường đang
    cần đo**; đúng họ lỗi mà chính bộ kiểm này tồn tại để bắt. Thử lại độ nhạy sau khi sửa:
    trả lại lệnh dọn cũ thì ca đỏ.
    """
    that = TV.tai_ve

    def tai_ve_gia(url, thu_muc, **k):
        # Mô phỏng đúng chỗ hỏng: tên XIN có dấu chấm đầu, tên GHI RA thì không.
        return that(url, thu_muc, **{**k, "mo_url": _GiaUrl([b"/* van ban */\n"])})

    # `lay_sdk` nạp `from . import tai_ve as tv` BÊN TRONG hàm, nên phải vá thuộc tính của
    # chính module `tai_ve` — vá `SDK.tv` không tới được vì tên ấy chưa tồn tại lúc này.
    monkeypatch.setattr(TV, "tai_ve", tai_ve_gia)
    dich = tmp_path / "firmware"
    SDK.lay_sdk("st/abc", ["Src/ft6x06.c"], dich)      # mo_url=None → nhánh tải thử CHẠY

    con_lai = sorted(p.name for p in dich.rglob("*"))
    rac = [t for t in con_lai if "thu-nhanh" in t]
    assert not rac, (
        f"tệp tải thử nằm lại trong thư mục mã nguồn: {rac}. Nó sẽ được trình biên dịch nhặt "
        f"lên, hoặc tệ hơn là nằm im trong repo của người dùng mà không ai biết nó là gì.")
    assert "ft6x06.c" in con_lai, f"tệp cần lấy không có: {con_lai}"


def test_doc_duoc_ten_that_du_tai_ve_co_doi_ten(tmp_path):
    """Nửa gốc của lỗi: `.strip("-.")` cắt dấu chấm đầu, nên tên xin ≠ tên ghi ra.

    Ca này khoá hành vi ấy lại. Nếu mai `tai_ve` thôi đổi tên thì ca vẫn xanh; nếu nó đổi tên
    theo kiểu khác thì chỗ dọn trong `lay_sdk` vẫn đúng, vì nó hỏi `tai_ve` đã ghi ra tên gì.
    """
    r = TV.tai_ve("https://x/y", tmp_path, ten_tep=".eide-thu-nhanh",
                  mo_url=_GiaUrl([b"noi dung van ban\n"]))
    assert r.dat
    assert not r.tep.startswith("."), (
        "`tai_ve` ghi ra tên KHÁC tên được xin — nên mọi chỗ dọn rác phải dùng `kq.tep`, "
        f"không dùng tên đã xin (xin `.eide-thu-nhanh`, ghi ra `{r.tep}`)")


# --------------------------------- 2 · mã nguồn: cùng tên khác nội dung thì GHI ĐÈ
def test_ma_nguon_trung_ten_thi_ghi_de_chu_khong_giu_hai_ban(tmp_path):
    dich = tmp_path / "firmware"
    ban_a = b"/* ban A */\nint f(void){return 1;}\n"
    ban_b = b"/* ban B */\nint f(void){return 2;}\n"
    SDK.lay_sdk("st/abc", ["Src/ft6x06.c"], dich, mo_url=_GiaUrl([ban_a]))
    SDK.lay_sdk("st/abc", ["Src/ft6x06.c"], dich, mo_url=_GiaUrl([ban_b]))

    cac_c = sorted(p.name for p in dich.rglob("*.c"))
    assert cac_c == ["ft6x06.c"], (
        f"thư mục được biên dịch có nhiều hơn một bản: {cac_c}. Cả hai sẽ vào dòng lệnh dịch; "
        f"cùng tên hàm là lỗi link, khác tên hàm thì link đúng bản sai.")
    assert (dich / "ft6x06.c").read_bytes() == ban_b, "ghi đè mà không lấy bản mới"


def test_tai_lieu_trung_ten_thi_VAN_giu_ca_hai_ban(tmp_path):
    """Nửa đối, và là nửa quan trọng hơn: đừng chữa lỗi này bằng cách bỏ chính sách cũ.

    Một Fact đã trích dẫn tới bản tài liệu cũ thì bản ấy phải còn kiểm lại được. Nếu ca này
    đỏ thì bản vá đã đi quá, và nó sẽ làm mất hiện vật mà trích dẫn trỏ tới.
    """
    r1 = TV.tai_ve("https://x/ds.txt", tmp_path, ten_tep="ds.txt",
                   mo_url=_GiaUrl([b"ban tai lieu thu nhat\n"]))
    r2 = TV.tai_ve("https://x/ds.txt", tmp_path, ten_tep="ds.txt",
                   mo_url=_GiaUrl([b"ban tai lieu thu hai, khac han\n"]))
    assert r1.dat and r2.dat
    assert r1.tep != r2.tep, "tài liệu cùng tên khác nội dung phải giữ CẢ HAI bản"
    assert (tmp_path / r1.tep).exists(), "mất bản tài liệu cũ — trích dẫn tới nó sẽ chết"
    assert any("lưu thành" in c for c in r2.canh_bao), "giữ cả hai mà không nói ra"


def test_ghi_de_thi_phai_NOI_RA(tmp_path):
    """Ghi đè im lặng cũng là một dạng mất dữ liệu. Nói ra thì người đọc kết quả biết."""
    dich = tmp_path / "firmware"
    SDK.lay_sdk("st/abc", ["Src/a.c"], dich, mo_url=_GiaUrl([b"/* A */\n"]))
    kq = SDK.lay_sdk("st/abc", ["Src/a.c"], dich, mo_url=_GiaUrl([b"/* B khac han */\n"]))
    assert kq.so_dat == 1
    # Cảnh báo đi theo `tai_ve`; chỗ này chỉ cần chắc việc ghi đè đã xảy ra và lấy bản mới.
    assert (dich / "a.c").read_bytes() == b"/* B khac han */\n"


def test_cung_noi_dung_thi_khong_canh_bao_gi(tmp_path):
    """Lấy lại đúng bản đang có là việc bình thường — không được kêu.

    Một cảnh báo luôn kêu thì bằng không kêu, và ca này giữ cho bản vá không biến mỗi lần
    lấy lại thành một dòng cảnh báo.
    """
    dich = tmp_path / "firmware"
    giong = b"/* y nguyen */\n"
    SDK.lay_sdk("st/abc", ["Src/a.c"], dich, mo_url=_GiaUrl([giong]))
    SDK.lay_sdk("st/abc", ["Src/a.c"], dich, mo_url=_GiaUrl([giong]))
    assert sorted(p.name for p in dich.rglob("*.c")) == ["a.c"]
    assert (dich / "a.c").read_bytes() == giong
