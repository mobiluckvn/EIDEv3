# -*- coding: utf-8 -*-
"""Bắt sửa từ BÊN NGOÀI EIDE — EIDE-EDIT-47 §DEV-369.

Luật nền số 3 của README nói *"mọi thay đổi gỡ lại được, **kể cả do người gõ**"*. Rà
12/10/2026: câu ấy đúng với thứ người sửa TRONG app, và sai với cách kỹ sư nhúng làm
thật — mở `main.c` bằng VS Code, sửa, lưu. Lần sửa ấy:

* không có changeset, nên **không hoàn tác được**;
* không đánh dấu hạ nguồn lỗi thời, nên một kết quả mô phỏng dựng trên mã cũ vẫn xanh;
* không phá được soft-lock, nên tác tử tưởng nó vẫn làm chủ tệp ấy;
* và tác tử **không biết gì** cho tới khi nó tình cờ đọc lại tệp.

Tài liệu nói *"changeset `kind="external"` đã có trong `changeset.py` từ bước G5, không ai
tạo nó"*. Mở mã ra thì chữ ấy đã có người dùng với một nghĩa khác hẳn: `forward.kind=
"external"` nghĩa là *tác động ra ngoài máy* (nạp bo, cài công cụ — §E5.3, không hoàn tác
được). Nên nhãn "sửa ngoài app" đi đường khác: `explain.sources[].kind`, và
`history.tom_tat()` kẹp thêm điều kiện để một lần nạp bo không dính nhãn ấy.

## Vì sao quét `mtime` chứ không chỉ dựa `watchdog`

`watchdog` nhanh hơn và không tốn CPU khi im. Nhưng nó là một phụ thuộc ngoài, và một
tính năng *an toàn dữ liệu* mà tắt lặng lẽ khi thiếu thư viện là một tính năng không ai
dám tin. Nên: dùng `watchdog` nếu có, **tự quét `mtime`** nếu không — và nói ra đang chạy
bằng đường nào.
"""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Callable

# Thư mục không bao giờ theo dõi. Đây là HAI luật khác nhau, nên để riêng — một bảng tra
# phủ lên nhau thì tháo mất một luật mà không ai thấy:
#
# 1. Tên trong bảng này: thứ máy sinh ra. Theo dõi `build/` là coi mỗi lần biên dịch là
#    một lần người sửa mã.
BO_QUA_THU_MUC = frozenset({
    "__pycache__", "node_modules", "build", "dist", "target", "out",
})

# 2. Và **mọi thành phần bắt đầu bằng dấu chấm**. Hai lý do khác nhau, cùng quan trọng:
#    * `.eide/` là chỗ chính lõi ghi liên tục — theo dõi nó là tự nghe tiếng của mình rồi
#      gọi đó là người dùng sửa;
#    * `.env` giữ khoá API. Theo dõi nó nghĩa là chép nguyên khoá vào blob của một
#      changeset, tức là khoá rời khỏi `.env` — đúng thứ ràng buộc bảo mật của dự án cấm.
#    Luật này cũng phủ `.git/`, `.venv/`, `.pytest_cache/`, `.DS_Store` mà không cần kể tên.

# Tệp lớn hơn ngần này thì bỏ qua: changeset giữ bản cũ trong blob, và một tệp 5 MB đổi
# mười lần là 50 MB blob cho một thứ không ai định hoàn tác.
TRAN_BYTE = 5 * 1024 * 1024

# Gộp sự kiện trong bấy nhiêu giây. Một lần Cmd-S của trình soạn hiện đại có thể là ba
# sự kiện tệp (ghi tạm · đổi tên · chmod), và ba changeset cho một lần lưu thì tab Lịch
# sử thành thứ không ai đọc.
GIAY_GOM = 1.5

# ===================================================== tiếng của chính EIDE
#
# Bản đầu của gói này lọc tiếng của chính lõi bằng MỘT CỬA SỔ THỜI GIAN ("lõi vừa ghi tệp
# này trong 3 giây thì bỏ qua"). Chạy qua app thật 12/10/2026 thì nó hỏng ngay: lõi còn tự
# ghi `EIDE.md` và `du-an.json` ở cuối mỗi lượt, bằng một đường KHÔNG đi qua chỗ đánh dấu
# — nên watcher ghi "anh sửa EIDE.md bên ngoài EIDE", và bốn phép đo khác của bộ E2E đỏ
# theo vì lịch sử có thêm changeset lạ.
#
# Nên đổi luật: **so NỘI DUNG, không xem đồng hồ**. Nếu nội dung hiện tại đúng bằng thứ
# EIDE ghi nhận lần cuối cho tệp ấy thì không có gì của người trong đó — bất kể bao lâu.
# Đồng hồ còn làm phép lọc phụ thuộc vào máy nhanh hay chậm, thứ không ai muốn trong một
# cơ chế an toàn dữ liệu.
#
# Sổ này nằm ở mức MODULE, khoá theo đường dẫn tuyệt đối, vì những chỗ ghi cần đánh dấu
# (`EideMd.save`, `ThongTinDuAn.ghi`) không giữ tham chiếu tới `Agent` nào.
_EIDE_DA_GHI: dict[str, str] = {}


def _bam(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def danh_dau_eide_ghi(p: Path, noi_dung: str | None = None) -> None:
    """CHÍNH EIDE vừa ghi tệp này. Gọi ngay sau khi ghi."""
    try:
        if noi_dung is None:
            noi_dung = Path(p).read_text("utf-8", errors="replace")
        _EIDE_DA_GHI[str(Path(p).resolve())] = _bam(noi_dung)
    except OSError:
        return


def la_tieng_cua_eide(p: Path, noi_dung: str) -> bool:
    """Nội dung này đúng bằng thứ EIDE ghi nhận lần cuối cho tệp ấy?"""
    return _EIDE_DA_GHI.get(str(Path(p).resolve())) == _bam(noi_dung)


def quen_tep(p: Path) -> None:
    """Tệp này KHÔNG CÒN — bỏ dấu "EIDE vừa ghi" của nó (§DEV-375).

    Giữ dấu cũ lại thì sau một lần xoá, người tạo lại tệp với ĐÚNG nội dung cũ sẽ bị coi
    là "tiếng của chính EIDE" và lần tạo lại ấy không vào sổ.
    """
    _EIDE_DA_GHI.pop(str(Path(p).resolve()), None)


def la_nhi_phan(p: Path) -> bool:
    """Dò bằng mấy byte đầu, cùng cách `ING-43` làm — không đoán theo đuôi tệp."""
    try:
        with p.open("rb") as f:
            dau = f.read(4096)
    except OSError:
        return True
    if b"\x00" in dau:
        return True
    try:
        dau.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def dang_theo_doi(rel: Path) -> bool:
    if any(ph in BO_QUA_THU_MUC for ph in rel.parts):
        return False
    return not any(ph.startswith(".") for ph in rel.parts)


class Watcher:
    """Theo dõi thư mục dự án và báo tệp nào vừa đổi TỪ BÊN NGOÀI.

    Chạy trong **tiến trình lõi** (một thread), không mở cổng nào, không thêm tiến trình
    nào — §8 của tài liệu: *"không mở cổng mạng, không thêm tiến trình ngoài"*.

    Lớp này chỉ phát hiện và gọi lại; việc ghi changeset là của `loop`. Tách ra để phần
    phát hiện kiểm được mà không cần dựng cả một `Agent`.
    """

    def __init__(self, goc: Path, *, khi_doi: Callable[[list[str]], None],
                 nhip: float = 2.0):
        self.goc = Path(goc).resolve()
        self.khi_doi = khi_doi
        self.nhip = nhip
        self._dung = threading.Event()
        self._thread: threading.Thread | None = None
        self._dau: dict[str, tuple[float, int]] = {}
        self._cho: dict[str, float] = {}
        self.cach = "chưa chạy"

    # ------------------------------------------------------------------ vòng đời
    def bat_dau(self) -> None:
        if self._thread is not None:
            return
        self._dau = self._chup()
        self.cach = "quét mtime"
        self._thread = threading.Thread(target=self._vong, name="eide-watcher",
                                        daemon=True)
        self._thread.start()

    def dung(self) -> None:
        self._dung.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ------------------------------------------------------------------ quét
    def _chup(self) -> dict[str, tuple[float, int]]:
        ra: dict[str, tuple[float, int]] = {}
        for p in self.goc.rglob("*"):
            try:
                if not p.is_file():
                    continue
                rel = p.relative_to(self.goc)
                if not dang_theo_doi(rel):
                    continue
                st = p.stat()
                if st.st_size > TRAN_BYTE:
                    continue
                ra[str(rel)] = (st.st_mtime, st.st_size)
            except OSError:
                continue
        return ra

    def quet_mot_lan(self) -> list[str]:
        """Một vòng quét. Trả danh sách tệp ĐÃ CHÍN (đổi xong và đã qua thời gian gộp).

        Tách ra khỏi vòng lặp để ca kiểm gọi thẳng được — một bộ đo phải ngủ 1,5 giây mỗi
        phép kiểm là một bộ đo không ai chạy.
        """
        moi = self._chup()
        bay = time.time()
        for path, dau in moi.items():
            if self._dau.get(path) != dau:
                self._cho[path] = bay
        # Tệp BIẾN MẤT cũng là một thay đổi (§DEV-375). Bản đầu bỏ qua nó, nên người xoá
        # `main.c` bằng Finder thì EIDE không có đường nào trả nó về — một lỗ trong luật
        # nền số 3, ở đúng chỗ đắt nhất.
        #
        # Vẫn xếp vào hàng chờ như mọi thay đổi khác, và **không** đánh dấu "đã xoá": một
        # lần lưu kiểu ghi-tạm-rồi-đổi-tên làm tệp biến mất trong vài chục milli giây, nên
        # "xoá hay sửa" chỉ trả lời được LÚC CHÍN. Người gọi kiểm lại sự tồn tại ở đó.
        for path in list(self._dau):
            if path not in moi:
                self._cho[path] = bay
        self._dau = moi

        chin = [p for p, luc in self._cho.items() if bay - luc >= GIAY_GOM]
        for p in chin:
            self._cho.pop(p, None)
        return sorted(chin)

    def _vong(self) -> None:
        while not self._dung.wait(self.nhip):
            try:
                doi = self.quet_mot_lan()
            except Exception:                                      # noqa: BLE001
                continue
            if doi:
                try:
                    self.khi_doi(doi)
                except Exception:                                  # noqa: BLE001
                    # Một lỗi trong tay người gọi KHÔNG được giết thread theo dõi: lần
                    # sửa sau vẫn phải bắt được.
                    continue


def noi_dung_doc_duoc(p: Path) -> str | None:
    """Nội dung tệp nếu nó đáng theo dõi, `None` nếu không (nhị phân, quá lớn, mất tệp)."""
    try:
        if not p.is_file() or p.stat().st_size > TRAN_BYTE or la_nhi_phan(p):
            return None
        return p.read_text("utf-8", errors="replace")
    except OSError:
        return None


__all__ = ["Watcher", "la_nhi_phan", "dang_theo_doi", "noi_dung_doc_duoc",
           "danh_dau_eide_ghi", "la_tieng_cua_eide", "quen_tep",
           "BO_QUA_THU_MUC", "TRAN_BYTE", "GIAY_GOM"]
