# -*- coding: utf-8 -*-
"""Lấy MÃ NGUỒN của hãng về dự án — nhiều tệp một lượt.

Khác `doc.fetch` ở chỗ dùng để làm gì: `doc.fetch` mang về **tài liệu để đọc và trích dẫn**;
tệp ở đây là **mã sẽ được biên dịch vào firmware**. Hai thứ đi hai đường khác nhau trong dự
án, và gộp chúng lại sẽ khiến một tệp `.c` của hãng nằm trong kho tài liệu như thể nó là một
nguồn để trích Fact.

Vì sao phải có công cụ riêng thay vì gọi `doc.fetch` nhiều lần: đo trên bo STM32F469, để vẽ
được lên màn DSI cần **khoảng 60–70 tệp** (HAL + CMSIS + BSP + driver panel). Sáu mươi lượt
gọi công cụ vượt ngân sách một lượt làm việc, và người dùng sẽ phải duyệt cổng cho từng tệp
một — đúng kiểu ma sát dạy người ta bấm duyệt theo phản xạ.

Ba điều cố ý:

1. **Chỉ nhận văn bản.** Mã nguồn là văn bản; một tệp nhị phân lọt vào thư mục firmware sẽ
   được trình biên dịch nhặt lên và báo một lỗi không liên quan gì tới nguyên nhân thật.
2. **Không bao giờ ghi ra ngoài thư mục đích**, kể cả khi đường dẫn trong repo có `..`.
3. **Nói rõ từng tệp hỏng vì sao.** Tải 70 tệp mà 3 tệp hỏng rồi báo "xong" là cách để lỗi
   liên kết xuất hiện sau đó ở một chỗ không liên quan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

TRAN_SO_TEP = 120
TRAN_TONG_BYTE = 16 * 1024 * 1024
TRAN_MOT_TEP = 2 * 1024 * 1024

# Đuôi được coi là mã nguồn biên dịch được hoặc tệp cấu hình đi kèm.
DUOI_MA = (".c", ".h", ".s", ".S", ".ld", ".cc", ".cpp", ".hpp", ".inc", ".txt", ".md")


@dataclass(slots=True)
class MotTep:
    duong_repo: str
    ten: str = ""
    so_byte: int = 0
    hash: str = ""
    dat: bool = False
    vi_sao: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"duong_repo": self.duong_repo, "ten": self.ten, "so_byte": self.so_byte,
                "hash": self.hash[:16], "dat": self.dat, "vi_sao": self.vi_sao}


@dataclass(slots=True)
class KetQuaSdk:
    repo: str = ""
    nhanh: str = ""
    dich: str = ""
    tep: list[MotTep] = field(default_factory=list)
    tong_byte: int = 0
    vi_sao_khong_dat: str = ""

    @property
    def so_dat(self) -> int:
        return sum(1 for t in self.tep if t.dat)

    def to_dict(self) -> dict[str, Any]:
        return {"repo": self.repo, "nhanh": self.nhanh, "dich": self.dich,
                "so_yeu_cau": len(self.tep), "so_dat": self.so_dat,
                "so_hong": len(self.tep) - self.so_dat,
                "tong_byte": self.tong_byte,
                "tep": [t.to_dict() for t in self.tep],
                "hong": [t.to_dict() for t in self.tep if not t.dat],
                "vi_sao_khong_dat": self.vi_sao_khong_dat}


def _ten_an_toan(duong: str, *, phang: bool) -> str:
    """Tên tệp sẽ ghi ra. Không bao giờ chứa `..` hay đường dẫn tuyệt đối."""
    if phang:
        return re.sub(r"[^A-Za-z0-9._-]", "-", duong.rsplit("/", 1)[-1]).strip("-.")
    phan = [re.sub(r"[^A-Za-z0-9._-]", "-", x).strip("-.")
            for x in duong.split("/") if x not in ("", ".", "..")]
    return "/".join(p for p in phan if p)


def lay_sdk(repo: str, tep: list[str], dich: Path, *, nhanh: str = "main",
            phang: bool = True, doi_ten: dict[str, str] | None = None,
            timeout: float = 60.0,
            mo_url: Callable[..., Any] | None = None) -> KetQuaSdk:
    """Tải `tep` từ `repo` (dạng `owner/name`) vào `dich`. Trả về từng tệp đạt hay không.

    `doi_ten` có mặt vì một số tệp của hãng **bắt buộc phải đổi tên mới dùng được**:
    `stm32f4xx_hal_conf_template.h` phải thành `stm32f4xx_hal_conf.h`, nếu không thì mọi
    `#include "stm32f4xx_hal_conf.h"` trong HAL đều hỏng. Không có tham số này thì tác tử
    phải đọc cả tệp 15 KB rồi ghi lại chỉ để đổi cái tên.
    """
    from . import tai_ve as tv

    kq = KetQuaSdk(repo=repo, nhanh=nhanh, dich=str(dich))
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", repo or ""):
        kq.vi_sao_khong_dat = (
            f"“{repo}” không phải dạng `owner/name`. Ví dụ: "
            "`STMicroelectronics/stm32f4xx-hal-driver`.")
        return kq
    if not tep:
        kq.vi_sao_khong_dat = "Chưa nêu tệp nào cần lấy."
        return kq
    if len(tep) > TRAN_SO_TEP:
        kq.vi_sao_khong_dat = (
            f"Xin {len(tep)} tệp, vượt trần {TRAN_SO_TEP} tệp một lượt. Chia thành nhiều lượt "
            "và nói cho người dùng biết bạn đang lấy những gì.")
        return kq

    import urllib.parse

    dich.mkdir(parents=True, exist_ok=True)
    for duong in tep:
        t = MotTep(duong_repo=duong)
        kq.tep.append(t)
        if not duong.lower().endswith(DUOI_MA):
            t.vi_sao = (f"đuôi không nằm trong danh sách mã nguồn ({', '.join(DUOI_MA)}) — "
                        "không lấy, vì tệp nhị phân lọt vào thư mục firmware sẽ làm trình "
                        "biên dịch báo một lỗi không liên quan tới nguyên nhân thật.")
            continue
        moi = (doi_ten or {}).get(duong)
        ten = (_ten_an_toan(moi, phang=True) if moi
               else _ten_an_toan(duong, phang=phang))
        if not ten:
            t.vi_sao = "không suy ra được tên tệp an toàn từ đường dẫn này."
            continue
        if kq.tong_byte >= TRAN_TONG_BYTE:
            t.vi_sao = f"đã vượt trần {TRAN_TONG_BYTE / 1e6:.0f} MB cho cả lượt."
            continue

        url = (f"https://raw.githubusercontent.com/{repo}/{nhanh}/"
               + "/".join(urllib.parse.quote(x) for x in duong.split("/")))
        ra = (dich / ten)
        ra.parent.mkdir(parents=True, exist_ok=True)
        r = tv.tai_ve(url, ra.parent, ten_tep=ra.name, tran_byte=TRAN_MOT_TEP,
                      timeout=timeout, mo_url=mo_url)
        if not r.dat:
            t.vi_sao = r.vi_sao_khong_dat[:200]
            continue
        if r.loai not in ("van_ban", "rtf"):
            # Đã tải về nhưng không phải văn bản → bỏ đi, đừng để lại trong firmware.
            (ra.parent / r.tep).unlink(missing_ok=True)
            t.vi_sao = f"nội dung không phải văn bản (nhận ra là “{r.loai}”) — đã bỏ."
            continue
        t.ten, t.so_byte, t.hash, t.dat = r.tep, r.so_byte, r.hash, True
        kq.tong_byte += r.so_byte
    return kq
