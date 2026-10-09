# -*- coding: utf-8 -*-
"""Bộ đọc SVD — register map của nhà sản xuất, đọc bằng MÃ chứ không bằng mô hình.

## Vì sao tệp này phải tồn tại

`ingest.phan_loai` nhìn một tệp SVD và khai `loai="svd"`, mức hỗ trợ **ĐẦY ĐỦ**,
`doc_duoc=True`. Rồi `doc.load` gọi `_nap_theo_loai`, mà `"svd"` không có nhánh nào ở đó, nên
nó rơi xuống `E1001 "chưa có bộ đọc nạp nó vào kho"`. Một comment trong `tools/knowledge.py`
nói *"bốn loại đó có công cụ riêng đọc đúng cấu trúc của chúng"* — và `grep -rni svd src/`
trước M5-03 ra đúng hai chỗ: phép phân loại, và chính câu comment ấy.

Hệ thống trả **hai câu trả lời trái nhau** cho cùng một tệp, và tác tử không có cách nào biết
câu nào đúng. Đó tệ hơn một tính năng thiếu: thiếu thì nó đi đường khác, còn mâu thuẫn thì nó
thử lại y nguyên.

## Vì sao đọc bằng mã, không nhờ mô hình đọc

Một địa chỉ thanh ghi là `base + offset`, và `0x40011000 + 0x08` nhớ sai một chữ số thì firmware
ghi vào **một thanh ghi khác** — không lỗi biên dịch, không lỗi chạy, chỉ là một ngoại vi không
làm gì. Đúng loại con số mà §C1 đòi phải có nguồn tra lại được. Nên phép cộng ấy do mã làm, và
mỗi Fact mang theo trích dẫn `<Ngoại vi>.<Thanh ghi>[.<Trường>]` để người mở tệp ra đối chiếu.

## Cấu trúc dữ liệu: dùng lại `Trang`, không đẻ kiểu mới

Mỗi thanh ghi và mỗi trường bit là **một `Trang`** — tức một đơn vị trích dẫn — và dữ liệu nằm
ở `o`/`cot` như một hàng bảng. Lý do thực dụng: `_lay_tai_lieu` dựng lại `TaiLieu` từ tệp sau
khi app khởi động lại, nên mọi thứ `fact_tu_svd` cần phải nằm **trong** `TaiLieu`. Một cấu trúc
song song sẽ sống đúng một tiến trình.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .docs import TaiLieu, Trang

# Trần số đơn vị đọc ra từ một SVD. SVD thật của một MCU họ F4 có cỡ 1 500–3 000 thanh ghi và
# hơn 10 000 trường bit; nạp hết thì kho phình và không ai dùng tới phần lớn. Trần đặt ở mức
# đủ cho cả một chip lớn, và chỗ bị cắt được NÓI RA, không im lặng bỏ.
TRAN_DON_VI = 40_000

_COT_REG = ("ngoai_vi", "thanh_ghi", "dia_chi", "reset", "size", "access")
_COT_FIELD = ("ngoai_vi", "thanh_ghi", "truong", "bit_offset", "bit_width")
_RE_BITRANGE = re.compile(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]")


def _so(chu: str | None) -> int | None:
    """`0x40011000` · `32` · `0X20` → số. Không đọc được thì `None`, không đoán 0.

    Trả 0 cho một giá trị không đọc được là tệ nhất: `base = 0` làm mọi địa chỉ của ngoại vi
    ấy thành offset trần, và chúng trông vẫn như địa chỉ.
    """
    if chu is None:
        return None
    t = chu.strip()
    if not t:
        return None
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t, 0)
    except ValueError:
        return None


def _chu(e: Any, ten: str) -> str:
    c = e.find(ten)
    return (c.text or "").strip() if c is not None and c.text else ""


def _bit(f: Any) -> tuple[int | None, int | None]:
    """`(offset, width)` từ MỘT trong hai lối khai của ARM.

    SVD thật trộn cả hai trong cùng một tệp, nên đọc một lối thôi là mất trường — và một
    trường bit thiếu không kêu lên, nó chỉ làm tác tử phải tự nhớ vị trí bit.
    """
    o, w = _so(_chu(f, "bitOffset")), _so(_chu(f, "bitWidth"))
    if o is not None and w is not None:
        return o, w
    m = _RE_BITRANGE.search(_chu(f, "bitRange"))
    if m:
        msb, lsb = int(m.group(1)), int(m.group(2))
        return lsb, msb - lsb + 1
    # `lsb`/`msb` là lối khai thứ ba, có trong một số SVD của Nordic và SiLabs.
    lsb, msb = _so(_chu(f, "lsb")), _so(_chu(f, "msb"))
    if lsb is not None and msb is not None:
        return lsb, msb - lsb + 1
    return None, None


def _thanh_ghi_cua(per: Any) -> list[tuple[Any, int]]:
    """Mọi `<register>` của một ngoại vi, kèm offset CỘNG DỒN của cluster bọc ngoài.

    `<cluster>` gói một nhóm thanh ghi lặp lại và cộng offset của riêng nó. Bỏ qua cluster thì
    mất thanh ghi; cộng thiếu offset cluster thì ra địa chỉ **SAI** — và một địa chỉ sai tệ hơn
    một thanh ghi thiếu, vì nó trông như đã có.
    """
    ra: list[tuple[Any, int]] = []
    regs = per.find("registers")
    if regs is None:
        return ra

    def _di(node: Any, cong: int, tien_to: str) -> None:
        for con in node:
            if con.tag == "register":
                ra.append((con, cong))
                if tien_to:
                    con.set("_eide_tien_to", tien_to)
            elif con.tag == "cluster":
                ten = _chu(con, "name")
                _di(con, cong + (_so(_chu(con, "addressOffset")) or 0),
                    f"{tien_to}{ten}." if ten else tien_to)

    _di(regs, 0, "")
    return ra


def doc_svd(path: Path, *, doc_id: str, phien_ban: str = "",
            nha_phat_hanh: str = "") -> TaiLieu:
    """Tệp SVD → `TaiLieu`, mỗi thanh ghi và mỗi trường bit là một đơn vị trích dẫn.

    Ném `ValueError` khi XML hỏng. KHÔNG trả về một tài liệu rỗng trong trường hợp ấy: ghi
    một nửa register map rồi báo lỗi là trạng thái tệ nhất — kho có số, và không ai biết nó
    thiếu phần nào.
    """
    byte = path.read_bytes()
    try:
        goc = ET.fromstring(byte.decode("utf-8", errors="replace"))
    except ET.ParseError as e:
        raise ValueError(f"XML hỏng ở dòng {e.position[0]}: {e}") from e
    if goc.tag != "device":
        raise ValueError(f"thẻ gốc là <{goc.tag}>, không phải <device>")

    pers = goc.find("peripherals")
    ds_per = list(pers) if pers is not None else []
    # Bảng tra để `derivedFrom` lấy được thanh ghi của ngoại vi gốc. Phần lớn ngoại vi cùng họ
    # của một SVD thật khai bằng MỘT dòng `derivedFrom` và không có `<registers>` — không xử
    # lý nó thì mất gần hết register map của chip.
    theo_ten = {_chu(p, "name"): p for p in ds_per if p.tag == "peripheral"}

    trang: list[Trang] = []
    so = 0
    for per in ds_per:
        if per.tag != "peripheral":
            continue
        ten_p = _chu(per, "name")
        base = _so(_chu(per, "baseAddress"))
        if not ten_p or base is None:
            continue
        nguon_reg = per
        goc_ten = (per.get("derivedFrom") or "").strip()
        if goc_ten and not _thanh_ghi_cua(per):
            nguon_reg = theo_ten.get(goc_ten, per)
        for reg, cong in _thanh_ghi_cua(nguon_reg):
            if so >= TRAN_DON_VI:
                break
            off = _so(_chu(reg, "addressOffset"))
            if off is None:
                continue
            ten_r = (reg.get("_eide_tien_to") or "") + _chu(reg, "name")
            if not ten_r:
                continue
            dia_chi = f"0x{base + cong + off:08X}"
            reset = _chu(reg, "resetValue")
            kich = _so(_chu(reg, "size"))
            truy = _chu(reg, "access")
            so += 1
            trang.append(Trang(
                so=so, nhan=f"{ten_p}.{ten_r}", loai_bang="thanh_ghi",
                cot=list(_COT_REG),
                o=[ten_p, ten_r, dia_chi, reset, "" if kich is None else str(kich), truy],
                chu=(f"{ten_p}.{ten_r} @{dia_chi}"
                     + (f" reset={reset}" if reset else "")
                     + (f" size={kich}" if kich is not None else "")
                     + (f" access={truy}" if truy else ""))))
            fields = reg.find("fields")
            for f in (list(fields) if fields is not None else []):
                if so >= TRAN_DON_VI:
                    break
                ten_f = _chu(f, "name")
                o_bit, w_bit = _bit(f)
                if not ten_f or o_bit is None or w_bit is None:
                    continue
                so += 1
                trang.append(Trang(
                    so=so, nhan=f"{ten_p}.{ten_r}.{ten_f}", loai_bang="truong_bit",
                    cot=list(_COT_FIELD),
                    o=[ten_p, ten_r, ten_f, str(o_bit), str(w_bit)],
                    chu=(f"{ten_p}.{ten_r}.{ten_f} bit {o_bit}"
                         + (f"..{o_bit + w_bit - 1}" if w_bit > 1 else "")
                         + f" (rộng {w_bit})")))

    return TaiLieu(
        doc_id=doc_id, ten=path.name, duong_dan=str(path),
        hash=hashlib.sha256(byte).hexdigest(), so_trang=len(trang), trang=trang,
        phien_ban=phien_ban or _chu(goc, "version"),
        nha_phat_hanh=nha_phat_hanh or _chu(goc, "name"),
        loai="svd", don_vi_trich_dan="thanh ghi")


def dem(tl: TaiLieu) -> tuple[int, int]:
    """`(số thanh ghi, số trường bit)` — hai con số khác nhau, không gộp."""
    r = sum(1 for t in tl.trang if t.loai_bang == "thanh_ghi")
    return r, sum(1 for t in tl.trang if t.loai_bang == "truong_bit")


def da_cat(tl: TaiLieu) -> bool:
    """Tài liệu này có bị trần `TRAN_DON_VI` cắt không.

    Một trần cắt **im lặng** là chỗ tệ nhất của cả tệp này: kho có 40 000 đơn vị, tác tử tra
    một thanh ghi ở cuối tệp và nhận "không có", rồi kết luận *chip không có thanh ghi ấy*.
    Hai câu khác nhau — *không có* và *chưa nạp tới* — dẫn tới hai việc ngược nhau.
    """
    return tl.so_trang >= TRAN_DON_VI


def _fact(*, fid_nguon: str, chu_the: str, khoa: str, gia_tri: Any, tl: TaiLieu,
          t: Trang, tier: str) -> dict[str, Any]:
    fid = "f-" + hashlib.sha1(
        f"{chu_the}|{khoa}|{gia_tri}|{fid_nguon[:8]}".encode()).hexdigest()[:10]
    return {
        "fact_id": fid, "subject": chu_the, "key": khoa, "value": gia_tri,
        "unit": "", "condition": "", "tier": tier, "origin": "extract",
        "source": {"doc_id": tl.doc_id, "version": tl.phien_ban, "page": t.so,
                   "cite": t.nhan, "quote": t.chu[:160]},
        "explain": {
            "summary": f"{chu_the} · {khoa} = {gia_tri}",
            "why": f"Đọc bằng mã từ SVD {tl.ten}, {t.nhan}.",
            "sources": [{"kind": "doc", "ref": f"{tl.doc_id} · {t.nhan}", "tier": tier}],
            "diff_prev": "bản đầu tiên",
            "next": ("Người xác nhận đúng dòng này để lên tầng VÀNG." if tier == "BAC"
                     else "Tìm tài liệu chuẩn chứng thực để nâng lên VÀNG."),
            "confidence": tier,
        },
    }


def fact_tu_svd(tl: TaiLieu, *, thuc_the: str = "", tier: str = "BAC") -> list[dict[str, Any]]:
    """`TaiLieu` SVD → danh sách Fact `reg:<P>.<R>` và `field:<P>.<R>.<F>`.

    `thuc_the` chỉ đi vào phần giải thích, KHÔNG vào `subject`: một thanh ghi được tra bằng
    tên ngoại vi (`USART1.BRR`), không bằng tên chip — và đó cũng là cách người đọc datasheet
    gọi nó. Gắn tên chip vào subject thì `reg.lookup("USART1.BRR")` không tìm thấy gì.

    `size`/`access` chỉ ghi khi SVD **khai** chúng. Điền mặc định 32 bit cho một thanh ghi
    không khai là bịa một dữ kiện và dán tầng BẠC lên nó.
    """
    ra: list[dict[str, Any]] = []
    for t in tl.trang:
        d = dict(zip(t.cot, t.o))
        if t.loai_bang == "thanh_ghi":
            chu_the = f"reg:{d['ngoai_vi']}.{d['thanh_ghi']}"
            for khoa in ("dia_chi", "reset", "size", "access"):
                if d.get(khoa):
                    ra.append(_fact(fid_nguon=tl.hash, chu_the=chu_the, khoa=khoa,
                                    gia_tri=d[khoa], tl=tl, t=t, tier=tier))
        elif t.loai_bang == "truong_bit":
            chu_the = f"field:{d['ngoai_vi']}.{d['thanh_ghi']}.{d['truong']}"
            for khoa in ("bit_offset", "bit_width"):
                ra.append(_fact(fid_nguon=tl.hash, chu_the=chu_the, khoa=khoa,
                                gia_tri=int(d[khoa]), tl=tl, t=t, tier=tier))
    return ra
