# -*- coding: utf-8 -*-
"""ERC theo KIỂU CHÂN — ma trận điện, thay phần ERC của KiCad. M3-03.

`tools/sch.py` ghi thẳng ở đầu tệp: **máy này KHÔNG cài KiCad**. Nên bốn lỗi mà KiCad ERC
bắt bằng một ma trận kiểu chân thì hoặc EIDE tự bắt, hoặc không ai bắt:

  `xung_dau_ra`      hai chân đẩy ngược nhau trên cùng net — blocker
  `nguon_khong_cap`  net nguồn chỉ có người tiêu thụ, không ai cấp
  `net_mot_chan`     net nối đúng một chân — gần như chắc là nối thiếu
  `dau_vao_treo`     chân vào không có ai lái

Hai quyết định định hình cả tệp này, và cả hai là để bảng ERC **không bị tắt**:

**`passive` không bao giờ là xung đột.** Mạch di cư từ netlist phẳng có hướng Port mặc định
là `passive` cho gần như mọi chân (`cay._huong_theo_ten` chỉ đoán `power_in` cho VCC/GND).
Coi `passive` là xung đột thì mọi mạch di cư sáng đèn đỏ hàng loạt — và một bảng báo trên
mọi mạch thì bị bỏ qua, kể cả lần nó đúng.

**Không sinh phát hiện `dat`.** Bốn luật này nói về chỗ SAI. Một dòng "net này ổn" cho từng
net trên mạch 200 net là cách nhanh nhất để chôn ba dòng đáng đọc.

Phần `net_mot_chan` đã có từ trước trong `knowledge/ckm.py` (`cho_dut`), nhưng chỉ là một
DÒNG CHỮ trong kết quả `ckm.build` — không `path`, không mức, không vào bảng ERC. Nên không
ai lọc được theo mức, và nó mất ngay khi người dùng nhìn sang chỗ khác.
"""

from __future__ import annotations

from typing import Any

from . import cay as C
from .erc import PhatHien, TraFact, _la_dat, chu_the_la

# Hướng Port "đẩy ra" — hai cái trong số này trên cùng một net là xung đột.
DAY_RA = ("out", "power_out")
# Hướng "lái được net": một chân vào cần ít nhất một trong số này.
LAI_DUOC = ("out", "power_out", "bidir")
# Net nguồn: chỉ nhóm này mới bị hỏi "ai cấp?".
LOAI_NGUON = ("power", "rail")


def _kieu_nguoi_xac_nhan(store: Any) -> dict[str, str]:
    """`{"U1.7": "power_in"}` — kiểu chân người đã xem và xác nhận, từ `symbol_map:mach`.

    Ưu tiên nó hơn `huong` của Port: hướng Port có thể do mã đoán khi di cư, còn bản đồ ký
    hiệu là thứ người đã nhìn. Không có thì trả `{}` và luật dùng `huong`.
    """
    from ..tools.sch import MA_SYMBOL

    try:
        a = store.get(MA_SYMBOL)
    except Exception:                                            # noqa: BLE001
        return {}
    ra: dict[str, str] = {}
    for ky in ((a or {}).get("canonical") or {}).get("ky_hieu") or []:
        ref = str(ky.get("ref") or "")
        if not ref or not ky.get("xac_nhan_boi"):
            continue
        for c in ky.get("chan") or []:
            so, kieu = str(c.get("so") or c.get("chan") or ""), str(c.get("kieu") or "")
            if so and kieu:
                ra[f"{ref}.{so}"] = kieu
    return ra


# Kiểu chân KiCad → hướng Port. Ngược chiều `sch.kyhieu.KIEU_CHAN`, vì ở đây ta đi từ thứ
# người đã xác nhận về lại dạng mà luật này so sánh.
_VE_HUONG = {"input": "in", "output": "out", "bidirectional": "bidir",
             "power_in": "power_in", "power_out": "power_out", "passive": "passive",
             "tri_state": "bidir", "open_collector": "bidir", "unspecified": "passive",
             "free": "passive", "no_connect": "passive"}


def kiem_kieu_chan(cay: C.Cay, tf: TraFact, phang: dict[str, list[str]],
                   thuoc: dict[str, str],
                   kieu_nguoi: dict[str, str] | None = None) -> list[PhatHien]:
    """Bốn luật ma trận kiểu chân, xét theo NET ĐIỆN (nhóm bằng `thuoc`).

    Xét theo net điện chứ không theo net phạm vi, cùng lý lẽ với `ngan_sach_dong`: một
    đường đi qua ba khối gồm bốn net phạm vi, và xét từng net thì cùng một ràng buộc bị
    báo bốn lần.
    """
    kieu_nguoi = kieu_nguoi or {}
    ra: list[PhatHien] = []
    net_cua_nhom: dict[str, list[str]] = {}
    for nid, ten in thuoc.items():
        if cay.nut.get(nid, {}).get("loai") == "net":
            net_cua_nhom.setdefault(ten, []).append(nid)

    for ten, nets in sorted(net_cua_nhom.items()):
        chan = _chan_la(cay, nets, kieu_nguoi)
        path = _path_cua_net(cay, nets)
        la_dat = _la_dat(cay, nets)
        la_nguon = any((cay.nut.get(n, {}).get("canonical", {}).get("loai") or "")
                       in LOAI_NGUON for n in nets)

        # 1. hai chân đẩy ngược nhau
        day = [c for c in chan if c[2] in DAY_RA]
        if len(day) >= 2:
            ds = ", ".join(f"`{c[0]}` ({c[2]})" for c in day)
            ra.append(PhatHien(
                "xung_dau_ra", "khong_dat", "blocker", path,
                f"Net {ten} có {len(day)} chân cùng đẩy ra: {ds}. Hai đầu ra đẩy ngược nhau "
                "thì dòng chạy từ con này sang con kia — mạch có thể vẫn chạy một lúc, rồi "
                "một trong hai con chết, và cái chết ấy không nói nó đến từ đâu.",
                cach_sua="Chỉ một chân được lái net này; các chân khác đổi sang `in` hoặc "
                         "`bidir`, hoặc tách net."))

        # 2. net nguồn không ai cấp
        if la_nguon and not la_dat and not _co_pwr_flag(cay, nets):
            co_cap = any(c[2] == "power_out" for c in chan) or _co_iout(cay, tf, chan)
            if chan and not co_cap:
                ra.append(PhatHien(
                    "nguon_khong_cap", "canh_bao", "major", path,
                    f"Net nguồn {ten} chỉ có chân tiêu thụ, không chân nào cấp "
                    f"({', '.join(c[0] for c in chan)}).",
                    cach_sua="Nối nó tới chân `power_out` của khối nguồn; nếu nguồn đến từ "
                             "ngoài bo thì khai `ckm.net_set(pwr_flag=true)` để nói rõ."))

        # 3. net chỉ có một chân lá
        #
        # KHÔNG miễn cho net đất. Phép phá lại chỉ ra chỗ này: bản đầu tôi miễn net đất cho
        # cả ba luật, nhưng một net GND chỉ nối ĐÚNG MỘT chân nghĩa là chân đất của con ấy
        # không nối về đâu — đó là lỗi thật, và là loại lỗi làm mạch chạy chập chờn chứ
        # không chết hẳn. Chỉ `nguon_khong_cap` mới cần miễn: đất không được "cấp".
        if len(chan) == 1:
            ra.append(PhatHien(
                "net_mot_chan", "canh_bao", "minor", path,
                f"Net {ten} nối đúng một chân: `{chan[0][0]}`. Một net một đầu thường là "
                "nối thiếu — nó không dẫn đi đâu cả.",
                cach_sua="Nối thêm đầu còn lại, hoặc nếu cố ý để trống thì đánh dấu "
                         "`no_connect` cho chân ấy."))

        # 4. chân vào không ai lái
        if not la_nguon and not la_dat and len(chan) > 1:   # đất thì không có chuyện treo
            vao = [c for c in chan if c[2] == "in"]
            if vao and not any(c[2] in LAI_DUOC for c in chan):
                ra.append(PhatHien(
                    "dau_vao_treo", "canh_bao", "minor", path,
                    f"Net {ten} có chân vào ({', '.join(c[0] for c in vao)}) mà không chân "
                    "nào lái nó. Chân vào treo đọc ra giá trị ngẫu nhiên và đổi theo nhiễu.",
                    cach_sua="Nối tới một chân ra, hoặc kéo lên/kéo xuống bằng điện trở."))
    return ra


def _chan_la(cay: C.Cay, nets: list[str],
             kieu_nguoi: dict[str, str]) -> list[tuple[str, dict[str, Any], str]]:
    """`[(\"U1.7\", nút lá, hướng)]` cho mọi Port LÁ nối vào nhóm net này."""
    ra: list[tuple[str, dict[str, Any], str]] = []
    for nid in nets:
        for pid in cay.noi.get(nid, []):
            p = cay.port.get(pid)
            if p is None:
                continue
            la = cay.nut.get(p["module_id"])
            if la is None or la.get("kind") != "leaf":
                continue
            ref = la["canonical"].get("ref") or la["ten"]
            ten_chan = f"{ref}.{p.get('chan') or p['ten']}"
            huong = str(p.get("huong") or "passive")
            # Kiểu người đã xác nhận THẮNG hướng Port — xem `_kieu_nguoi_xac_nhan`.
            if ten_chan in kieu_nguoi:
                huong = _VE_HUONG.get(kieu_nguoi[ten_chan], huong)
            if not any(x[0] == ten_chan for x in ra):
                ra.append((ten_chan, la, huong))
    return sorted(ra, key=lambda x: x[0])


def _co_pwr_flag(cay: C.Cay, nets: list[str]) -> bool:
    return any((cay.nut.get(n, {}).get("canonical", {}) or {}).get("pwr_flag")
               for n in nets)


def _co_iout(cay: C.Cay, tf: TraFact, chan: list[tuple[str, dict[str, Any], str]]) -> bool:
    """Có lá nào trên net khai `iout_max` không — nó cấp được, dù hướng Port chưa khai."""
    for ten_chan, la, _ in chan:
        so = ten_chan.partition(".")[2]
        ref = ten_chan.partition(".")[0]
        if tf.tra([f"pin:{ref}.{so}"] + chu_the_la(la), "i_out_max") is not None:
            return True
    return False


def _path_cua_net(cay: C.Cay, nets: list[str]) -> str:
    """Path của khối sở hữu net NÔNG nhất — chỗ người sẽ đi tìm để sửa (HIER-17)."""
    tot: tuple[int, str] | None = None
    for nid in nets:
        p = cay.nut.get(cay.cha(nid) or "", {}).get("path") or "/board"
        k = (C.do_sau(p), p)
        if tot is None or k < tot:
            tot = k
    return tot[1] if tot else "/board"
