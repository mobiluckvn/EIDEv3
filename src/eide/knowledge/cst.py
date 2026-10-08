# -*- coding: utf-8 -*-
"""M3-18 — đọc tệp ràng buộc chân Gowin (`.cst`) và đối chiếu nó với thiết kế.

Vì sao mô-đun này tồn tại:

`dat_di_day` trước đây chỉ hỏi *"tệp `.cst` có tồn tại không"*. Câu ấy không đủ, và chỗ nó
không đủ là chỗ tốn nhất của cả đường FPGA: nếu một cổng của mô-đun đỉnh **không có `IO_LOC`**,
nextpnr không báo lỗi — nó tự chọn một chân còn trống. Tổng hợp đạt, đặt-đi dây đạt, bitstream
dựng xong, Fmax đẹp. Rồi nạp lên bo thì đèn không sáng, và không một dòng nào trên màn hình
nói vì sao. Người ta sẽ đi tìm lỗi trong RTL, vì mọi chặng đều xanh.

Nên phép kiểm này phải đứng **trước** nextpnr. Sau nextpnr thì không còn gì để chặn: chân đã
được chọn, và chọn sai cũng là một lựa chọn hợp lệ với công cụ.

## Chỗ mô-đun này KHÔNG làm, và nói ra

* **Không tự sửa `.cst`.** Chân nào nối vào đâu là một quyết định phần cứng, có bo thật đứng
  sau. Đoán hộ một dòng `IO_LOC` là đoán hộ một đường mạch đã in ra đồng.
* **Không bịa bản đồ chân của kit.** Hai luật `chan_lech_kit` và `io_type_lech_bank` chỉ nói
  được điều gì khi có Fact chân kit. Không có Fact thì chúng **im và khai là đã im** —
  `chua_co_fact_chan_kit` — chứ không suy từ tri thức chung về con chip.
* **Không đọc hiểu `.cst` đầy đủ.** Nó đọc `IO_LOC` và `IO_PORT`, hai chỉ thị chiếm toàn bộ
  bảy tệp `.cst` thật trong repo. Chỉ thị khác (`CLOCK_LOC`, `INS_LOC`, …) đi vào
  `loi_cu_phap` chứ không bị bỏ qua im lặng — im lặng ở đây là nói rằng đã kiểm.
"""

from __future__ import annotations

import re
from typing import Any

# `IO_LOC "ten" so;` — tên luôn trong ngoặc kép, kể cả tên bus dạng `led[0]`. Chân là số
# (chuỗi, không phải int: `.cst` thật có dạng `IO_LOC "x" 10,11;` cho cặp vi sai, và biến nó
# thành int là mất thông tin).
_LOC = re.compile(r'^\s*IO_LOC\s+"([^"]+)"\s+([0-9,]+)\s*;\s*$')
# `IO_PORT "ten" KHOA=GIATRI KHOA=GIATRI;`
_PORT = re.compile(r'^\s*IO_PORT\s+"([^"]+)"\s+(.+?)\s*;\s*$')
_CAP = re.compile(r"([A-Z_][A-Z0-9_]*)\s*=\s*([^\s;]+)")

# Điện áp ngầm của mỗi họ IO_TYPE, đơn vị volt. Dùng để bắt chuyện IO_TYPE đòi một mức điện mà
# bank không cấp — nextpnr nhận, silicon thì không.
#
# Ba mức này tra từ tên chuẩn của họ (LVCMOS**33** = 3,3 V), không phải tự nhớ: mỗi tên mang
# luôn con số trong chính nó, nên bảng này đọc được lại từ tên mà không cần tài liệu thứ hai.
_V_IO_TYPE: dict[str, float] = {
    "LVCMOS33": 3.3, "LVCMOS25": 2.5, "LVCMOS18": 1.8, "LVCMOS15": 1.5, "LVCMOS12": 1.2,
    "LVTTL33": 3.3, "SSTL33": 3.3, "SSTL25": 2.5, "SSTL18": 1.8, "SSTL15": 1.5,
    "HSTL18": 1.8, "HSTL15": 1.5, "LVDS25": 2.5,
}


def doc_cst(chu: str) -> dict[str, Any]:
    """Đọc nội dung `.cst` thành `{"loc": {tên: chân}, "io": {tên: {KHOÁ: giá trị}}, ...}`.

    Tên giữ **nguyên dạng** `led[0]`: đó là cách `.cst` viết từng bit của một bus, và chuẩn
    hoá nó thành `led` sẽ gộp sáu ràng buộc khác nhau thành một.

    Dòng không đọc được vào `loi_cu_phap` kèm số dòng. Một tệp ràng buộc mà bộ đọc bỏ qua
    được vài dòng là một tệp mà kết luận "mọi cổng đều có chân" nói về phần nó đọc được, chứ
    không nói về tệp.
    """
    loc: dict[str, str] = {}
    io: dict[str, dict[str, str]] = {}
    loi: list[dict[str, Any]] = []

    for i, dong_goc in enumerate(chu.splitlines(), 1):
        # `//` là chú thích của `.cst` thật, và trong bảy tệp trong repo có cả `IO_LOC` bị
        # tắt đi bằng nó. Cắt chú thích TRƯỚC khi đọc, không thì một ràng buộc đã tắt vẫn
        # được tính là còn hiệu lực.
        dong = re.sub(r"//.*$", "", dong_goc).strip()
        if not dong:
            continue
        m = _LOC.match(dong)
        if m:
            loc[m.group(1)] = m.group(2)
            continue
        m = _PORT.match(dong)
        if m:
            cap = dict(_CAP.findall(m.group(2)))
            if not cap:
                loi.append({"dong": i, "noi_dung": dong_goc.strip(),
                            "vi_sao": "IO_PORT không có cặp KHOÁ=GIÁ_TRỊ nào"})
                continue
            io.setdefault(m.group(1), {}).update(cap)
            continue
        loi.append({"dong": i, "noi_dung": dong_goc.strip(),
                    "vi_sao": "không phải IO_LOC hay IO_PORT đọc được"})

    return {"loc": loc, "io": io, "loi_cu_phap": loi}


def cong_tu_json(j: dict[str, Any], dinh: str) -> list[str]:
    """Cổng của mô-đun đỉnh, bus đã tách thành `ten[i]` để so được với `.cst`.

    `.cst` khai từng bit (`led[0]` … `led[5]`); JSON của yosys khai một cổng `led` sáu bit.
    Không tách thì mọi bus đều báo "thiếu ràng buộc" và phép kiểm vô dụng ngay lượt đầu.

    Không có mô-đun `dinh` thì **ném `KeyError`**, không trả rỗng: rỗng sẽ được đọc thành
    "mô-đun đỉnh không có cổng nào", và một thiết kế không cổng thì mọi phép kiểm đều xanh.
    """
    mods = j.get("modules") or {}
    if dinh not in mods:
        raise KeyError(
            f"Mạng cổng không có mô-đun đỉnh “{dinh}”. Có: "
            + ", ".join(sorted(t for t in mods if not t.startswith("$"))[:12]))
    ra: list[str] = []
    for ten, v in (mods[dinh].get("ports") or {}).items():
        bits = v.get("bits") or []
        if len(bits) <= 1:
            ra.append(ten)
        else:
            ra.extend(f"{ten}[{i}]" for i in range(len(bits)))
    return ra


def _volt(gt: str) -> float | None:
    try:
        return float(str(gt).rstrip("Vv"))
    except ValueError:
        return None


def kiem(cst: dict[str, Any], cong: list[str],
         fact_chan_kit: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    """Đối chiếu ràng buộc với cổng thiết kế và với Fact chân của kit.

    `fact_chan_kit` khoá theo **số chân** (`"15"`), giá trị là các khoá Fact của chân ấy:
    `chuc_nang` (hoặc `ten`/`net` — xem ghi chú dưới), `bank`, `vccio`.

    Trả một danh sách phát hiện, mỗi cái có `loai` · `muc` (`blocker`/`major`/`info`) ·
    `thong_diep`. `blocker` nghĩa là **không đi tiếp**; `major` là phải đọc nhưng không chặn.
    """
    loc: dict[str, str] = cst.get("loc") or {}
    io: dict[str, dict[str, str]] = cst.get("io") or {}
    pt: list[dict[str, Any]] = []
    tap_cong = set(cong)

    # 1. Cổng không có IO_LOC — blocker. Đây là chính cái lỗi nextpnr im lặng cho qua.
    for c in cong:
        if c not in loc:
            pt.append({
                "loai": "thieu_rang_buoc", "muc": "blocker", "ten": c,
                "thong_diep": (
                    f"Cổng `{c}` của mô-đun đỉnh không có `IO_LOC`. nextpnr sẽ **tự chọn** một "
                    "chân còn trống, bitstream dựng xong và nối tín hiệu vào chân không ai "
                    "định — nạp lên bo thì không chạy, mà mọi chặng đều báo đạt.")})

    # 2. Ràng buộc cho tên không phải cổng — major, không chặn.
    #
    # Không chặn vì một `.cst` của cả kit, dùng cho nhiều thiết kế, thì đương nhiên có chân
    # thiết kế này không dùng (đo trên `du-lieu/riscv-tn20k-b`: `btn_s2` và `uart_rx`). Nhưng
    # cũng không im: một tên thừa cũng có thể là một cổng viết sai chính tả, và lúc ấy nó đi
    # cặp với một `thieu_rang_buoc` — hai phát hiện cạnh nhau đọc ra ngay nguyên nhân.
    for ten in sorted(set(loc) - tap_cong):
        pt.append({
            "loai": "rang_buoc_thua", "muc": "major", "ten": ten, "chan": loc[ten],
            "thong_diep": (
                f"`IO_LOC \"{ten}\" {loc[ten]}` ràng buộc một tên **không phải cổng** của mô-đun "
                "đỉnh. Thường là chân của kit mà thiết kế này không dùng — nhưng cũng có thể là "
                "tên cổng viết sai, và lúc ấy sẽ có một cổng khác báo thiếu ràng buộc.")})

    # 3. Hai tên cùng một chân — blocker. Phần cứng không làm được thế.
    theo_chan: dict[str, list[str]] = {}
    for ten, chan in loc.items():
        if ten in tap_cong:            # chỉ xét chân đang thật sự được thiết kế dùng
            theo_chan.setdefault(chan, []).append(ten)
    for chan, tens in sorted(theo_chan.items()):
        if len(tens) > 1:
            pt.append({
                "loai": "trung_chan", "muc": "blocker", "chan": chan,
                "ten_cac_cong": sorted(tens),
                "thong_diep": (
                    f"Chân {chan} được gán cho {len(tens)} cổng cùng lúc: "
                    + ", ".join(f"`{t}`" for t in sorted(tens))
                    + ". Một chân vật lý mang được một tín hiệu.")})

    # 4 và 5 cần Fact chân của kit. Không có thì KHAI là đã bỏ, không im.
    if not fact_chan_kit:
        pt.append({
            "loai": "chua_co_fact_chan_kit", "muc": "info",
            "thong_diep": (
                "Chưa có Fact chân của kit, nên **đã bỏ** phần đối chiếu chân và phần kiểm mức "
                "điện của bank. Kết luận ở trên chỉ nói về quan hệ `.cst` ↔ cổng thiết kế: nó "
                "không nói chân 15 có thật là LED0 trên bo hay không. Nạp Fact bằng "
                "`doc.pinout` rồi chạy lại để có phần ấy.")})
        return pt

    for ten in sorted(tap_cong & set(loc)):
        chan = loc[ten]
        f = fact_chan_kit.get(chan)
        if not f:
            continue

        # 4. Chân lệch chức năng kit — major kèm Fact để người đọc kiểm lại được.
        #
        # So bằng cách rút chữ–số của hai bên (`led[0]` ↔ `LED0`), vì tên cổng do người viết
        # RTL đặt và tên chức năng do tài liệu kit đặt; đòi chúng giống hệt nhau là đòi một
        # quy ước chưa ai thoả thuận. Không khớp thì NÓI RA chứ không kết luận là sai.
        kit = f.get("chuc_nang") or f.get("ten") or f.get("net") or ""
        if kit and not _cung_mot_ten(ten, kit):
            pt.append({
                "loai": "chan_lech_kit", "muc": "major", "ten": ten, "chan": chan,
                "chuc_nang_kit": kit, "fact": dict(f),
                "thong_diep": (
                    f"Cổng `{ten}` gán vào chân {chan}, mà Fact của kit nói chân {chan} là "
                    f"**{kit}**. Hai tên không khớp: hoặc gán sai chân, hoặc tên cổng đặt theo "
                    "quy ước khác. Mở Fact ra đối chiếu trước khi nạp.")})

        # 5. IO_TYPE đòi mức điện mà bank không cấp — blocker.
        kieu = (io.get(ten) or {}).get("IO_TYPE") or ""
        v_can = _V_IO_TYPE.get(kieu.upper())
        v_co = _volt(f.get("vccio") or "")
        if v_can is not None and v_co is not None and abs(v_can - v_co) > 0.05:
            pt.append({
                "loai": "io_type_lech_bank", "muc": "blocker", "ten": ten, "chan": chan,
                "io_type": kieu, "vccio": f.get("vccio"), "bank": f.get("bank"),
                "thong_diep": (
                    f"`{ten}` khai `IO_TYPE={kieu}` (cần {v_can} V) trên chân {chan} thuộc bank "
                    f"{f.get('bank') or '?'} đang cấp {v_co} V. Công cụ nhận ràng buộc này; "
                    "silicon thì không — mức logic sai, và sai theo kiểu lúc đọc được lúc "
                    "không.")})

    return pt


def _cung_mot_ten(cong: str, kit: str) -> bool:
    """`led[0]` và `LED0` là một; `clk` và `LED0` thì không.

    Rút về chữ thường + chữ số, bỏ dấu ngoặc và gạch dưới. Phép so này cố ý **lỏng**: nó đi
    tìm chuyện lệch hẳn, không đi chấm quy ước đặt tên. Một phép so chặt sẽ báo lệch cho mọi
    thiết kế và không ai đọc nó nữa.
    """
    def rut(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    a, b = rut(cong), rut(kit)
    if not a or not b:
        return True
    return a == b or a in b or b in a
