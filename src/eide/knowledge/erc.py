# -*- coding: utf-8 -*-
"""Fact theo cấp và ERC theo cây — EIDE-HIER-45 §4. Bước HIER-B.

Hai việc, và việc thứ hai dựa vào việc thứ nhất:

**§4.1 Fact gắn ở mọi cấp.** Chủ thể Fact theo cấp là `module:/mcu` · `port:/mcu.I2C0` ·
`net:/board.+3V3` · `leaf:U1` · `pin:U1.28`. Fact của lá đến từ datasheet; Fact của khối
thì hoặc người khai ở Port (Iout.max của khối nguồn), hoặc **suy dẫn bằng mã** từ các con
(tổng dòng tiêu thụ). Không có đường thứ ba — mô hình không được tự điền một con số cấp
khối, vì cấp khối là chỗ người đọc tin nhất và kiểm lại khó nhất.

**§4.2 Bốn ràng buộc kiểm bằng MÃ, không LLM.** Tài liệu ghi thẳng "(bằng mã, không LLM)",
và lý do không phải là tiết kiệm token: bốn phép này đều là cộng và so sánh, nên mô hình
không thêm được gì ngoài rủi ro. Việc của mô hình là *đọc datasheet ra Fact*; việc của mã
là *cộng chúng lại*.

Điều khó nhất ở đây không phải phép so sánh — mà là **tìm đúng hai vế trên cây**. Một net
nguồn ở gốc chạm chân lá qua hai tầng Port; muốn biết ai cấp và ai tiêu thụ thì phải đi
xuống tới lá. Đó là lý do file này tồn tại thay vì thêm luật vào `compare.py`: `compare`
biết so hai Fact, còn đây biết **Fact nào với Fact nào**.

Mọi phát hiện mang `path` của khối (HIER-17: "ERC/BOM/truy vết báo theo path khối"). Một
dòng "thiếu pull-up" không nói ở khối nào thì trên một mạch 40 khối là vô dụng.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import cay as C
from . import compare as CP

# --------------------------------------------------------------------------- §4.1 chủ thể
TIEN_TO_CAP = ("module:", "port:", "net:", "leaf:", "pin:")

# Khoá Fact mà ERC đọc. Danh sách đóng và có bí danh, vì cùng một đại lượng được datasheet
# gọi bằng nhiều tên, và bắt người dùng nhớ đúng một tên là bắt sai chỗ.
KHOA = {
    "i_max": ("i_max", "i.max", "icc.max", "idd.max", "supply_current", "dong_tieu_thu"),
    "i_out_max": ("iout_max", "iout.max", "i_out.max", "dong_ra_max"),
    "voh": ("voh", "voh.min", "v_oh"),
    "vih": ("vih", "vih.min", "v_ih"),
    "addr": ("addr", "i2c.addr", "dia_chi", "slave_addr"),
    "v_max": ("v_max", "vdd.max", "vin.max", "ap_toi_da"),
    # M3-01 — mức chịu của riêng miền I/O (nhiều chip có VDD lõi khác VDDIO), và cờ chân
    # chịu được 5 V. Chân 5V-tolerant là chuyện rất thường gặp (STM32, nhiều chân I/O);
    # báo oan ở đó thì bảng ERC mất uy tín đúng vào loại mạch phổ biến nhất.
    "vddio_max": ("vddio.max", "vddio_max"),
    "v_tolerant": ("v_tolerant", "ft", "five_volt_tolerant"),
}


def khoa_chuan(k: str) -> str | None:
    """Tên khoá chuẩn của một khoá Fact, hoặc None nếu ERC không dùng khoá đó."""
    t = (k or "").strip().lower().replace(" ", "")
    for chuan, bd in KHOA.items():
        if t in bd:
            return chuan
    return None


def chu_the_la(nut: dict[str, Any]) -> list[str]:
    """Những chủ thể Fact có thể nói về một lá: `leaf:U1`, tên chip, và ref trần.

    Ba dạng vì ba nguồn khác nhau: `fact.extract` ghi theo tên chip (Fact của *loại* chip),
    người dùng hay gõ ref (`U1`), và §4.1 quy ước `leaf:U1`. Chấp cả ba rồi ưu tiên cái
    CỤ THỂ hơn — xem `fact_cua`.
    """
    ref = nut["canonical"].get("ref") or nut["ten"]
    ten = nut["canonical"].get("ten") or nut["ten"]
    return [f"leaf:{ref}", ref, ten]


@dataclass(slots=True)
class PhatHien:
    """Một phát hiện ERC. `path` là chỗ nó xảy ra — không có nó thì phát hiện vô dụng."""

    luat: str
    ket_luan: str                 # dat | khong_dat | canh_bao | chua_du_du_kien
    muc: str                      # blocker | major | minor | info
    path: str
    vi: str
    bang_chung: list[dict[str, Any]] = field(default_factory=list)
    cach_sua: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"luat": self.luat, "ket_luan": self.ket_luan, "muc": self.muc,
                "path": self.path, "vi": self.vi, "bang_chung": self.bang_chung,
                "cach_sua": self.cach_sua}


# =========================================================================== tra Fact
class TraFact:
    """Tra Fact theo cấp. Đọc MỘT lần, tra nhiều lần.

    Ưu tiên chủ thể cụ thể hơn: `pin:U1.7` trước `leaf:U1` trước `ATmega328P`. Vì một con
    số gắn vào *đúng con chip này* nói nhiều hơn một con số gắn vào *loại chip* — ví dụ
    dòng tiêu thụ thực đo của U1 trên bo này.
    """

    def __init__(self, store: Any) -> None:
        self._theo: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for f in store.query_facts(limit=20000):
            k = khoa_chuan(str(f.get("key", "")))
            if k is None:
                continue
            self._theo.setdefault((str(f.get("subject", "")), k), []).append(f)

    def tra(self, chu_the: list[str], khoa: str) -> dict[str, Any] | None:
        for ct in chu_the:
            ds = self._theo.get((ct, khoa))
            if ds:
                # Nhiều Fact cùng chủ thể+khoá: lấy cái TIN NHẤT. Không tự hoà giải hai số
                # khác nhau — `fact.cross_check` mới là chỗ làm việc đó, và nó hỏi người.
                return min(ds, key=_uu_tien)
        return None

    def tat_ca(self, chu_the: list[str], khoa: str) -> list[dict[str, Any]]:
        ra: list[dict[str, Any]] = []
        for ct in chu_the:
            ra += self._theo.get((ct, khoa), [])
        return ra


def _uu_tien(f: dict[str, Any]) -> int:
    from .ckm import thu_tu_tang
    return thu_tu_tang(str(f.get("tier", "")))


def _gt(f: dict[str, Any]) -> tuple[float, str]:
    return CP._so(f)


def _cite(f: dict[str, Any]) -> dict[str, Any]:
    return CP._cite(f)


# =========================================================================== §4.2 bốn luật
def erc(store: Any) -> list[PhatHien]:
    """Bốn ràng buộc §4.2, chạy trên cây. Trả danh sách phát hiện, mỗi cái có path."""
    cay = C.Cay.doc(store)
    if not cay.goc:
        return []
    tf = TraFact(store)
    phang, thuoc = C.flatten_chi_tiet(cay)
    ra: list[PhatHien] = []
    ra += ngan_sach_dong(cay, tf, phang, thuoc)
    ra += muc_logic_tren_net(cay, tf, phang)
    ra += qua_ap_tren_net(cay, tf, phang, thuoc)
    ra += trung_dia_chi_bus(cay, tf, phang)
    ra += pull_up_bus(cay, tf, phang)
    # M3-03 — ma trận kiểu chân, thay phần ERC của KiCad (máy này không cài KiCad).
    from .erc_kieu_chan import kiem_kieu_chan, _kieu_nguoi_xac_nhan

    ra += kiem_kieu_chan(cay, tf, phang, thuoc, _kieu_nguoi_xac_nhan(store))
    ra += tranh_chap_nguon(cay, tf, thuoc)
    ra += chap_nguon(cay, thuoc)
    return ra


# --------------------------------------------------------------------------- 1b. hai bộ cấp
# Tên net được coi là ĐẤT dù `loai` khai gì. Đặt cạnh `_la_dat` vì cả hai dùng chung danh
# sách này, và một danh sách chép ở hai chỗ sẽ lệch nhau đúng lúc ai đó thêm tên thứ năm.
TEN_DAT = ("GND", "VSS", "AGND", "DGND")


def _nhom_net(cay: C.Cay, thuoc: dict[str, str]) -> dict[str, list[str]]:
    """Nhóm điện → các net phạm vi thuộc nó. Không lọc gì — người gọi tự lọc."""
    ra: dict[str, list[str]] = {}
    for nid, ten in thuoc.items():
        if cay.nut.get(nid, {}).get("loai") == "net":
            ra.setdefault(ten, []).append(nid)
    return {k: sorted(v) for k, v in ra.items()}


def _bo_cap_tren_nhom(cay: C.Cay, tf: TraFact,
                      nets: list[str]) -> list[tuple[str, dict[str, Any] | None]]:
    """Các **LÁ** cấp nguồn cho nhóm net này: `[(ref, Fact iout_max hoặc None)]`.

    Chỉ đếm LÁ. Port của KHỐI là **đường đi qua** cấp, không phải một bộ cấp thứ hai — trên
    mạch mẫu, net 3V3 có hai Port `power_out`: của lá U3 và của khối `/board/pwr`. Đếm cả
    Port khối thì mọi mạch có khối nguồn đều bị báo tranh chấp, tức luật này sẽ nổ trên
    chính cái mạch đúng.

    Nhận ra bằng Fact `iout_max` HOẶC hướng `power_out` — cùng lý lẽ với `_hai_ve_dong`:
    hướng Port của mạch di cư là `passive`, nên gate theo hướng thì một LDO có Fact hẳn hoi
    vẫn không được tính.
    """
    theo_ref: dict[str, dict[str, Any] | None] = {}
    for pid in sorted({p for nid in nets for p in cay.noi.get(nid, [])}):
        p = cay.port.get(pid)
        if p is None:
            continue
        m = cay.nut.get(p["module_id"])
        if m is None or m.get("kind") != "leaf":
            continue
        ref = m["canonical"].get("ref") or m["ten"]
        ct = [f"pin:{ref}.{p.get('chan') or p['ten']}"] + chu_the_la(m)
        f = tf.tra(ct, "i_out_max")
        if f is None and str(p.get("huong")) != "power_out":
            continue
        # Một lá có hai chân VOUT song song vẫn là MỘT bộ cấp — gom theo ref.
        if ref not in theo_ref or (f is not None and theo_ref[ref] is None):
            theo_ref[ref] = f
    return sorted(theo_ref.items())


def tranh_chap_nguon(cay: C.Cay, tf: TraFact, thuoc: dict[str, str]) -> list[PhatHien]:
    """Hai lá trở lên cùng cấp một rail (§4.2 mở rộng, M3-04).

    `_hai_ve_dong` giữ MỘT bộ cấp — cái ở tầng tin nhất — và bỏ các bộ khác **không nói
    gì**. Hai LDO cùng đẩy lên một rail thì con có điện áp ra cao hơn gánh hết tải, con kia
    chạy ngược, và cả hai nóng lên theo cách không đọc ra được từ sơ đồ.

    Cấp song song có chủ ý (OR-ing qua diode, nguồn dự phòng) là thiết kế có thật: khai
    `ckm.net_set(or_ing=true)` thì luật im. Báo oan ở mức blocker thì người ta học được cách
    bỏ qua blocker — mà đó là mức duy nhất không được phép bị bỏ qua.
    """
    ra: list[PhatHien] = []
    for ten, nets in sorted(_nhom_net(cay, thuoc).items()):
        if _la_dat(cay, nets):
            continue
        if any((cay.nut.get(n, {}).get("canonical", {}) or {}).get("or_ing") for n in nets):
            continue
        cap = _bo_cap_tren_nhom(cay, tf, nets)
        if len(cap) < 2:
            continue
        bc = [{"ref": ref, **({"fact": f.get("fact_id") or f.get("key")} if f else
                              {"nguon": "hướng Port power_out"})} for ref, f in cap]
        ra.append(PhatHien(
            "tranh_chap_nguon", "khong_dat", "blocker", _path_nong_nhat(cay, nets),
            f"Net nguồn {ten} có {len(cap)} bộ cấp: "
            + ", ".join(f"`{ref}`" for ref, _ in cap)
            + ". Con có điện áp ra cao hơn sẽ gánh hết tải và đẩy ngược vào con kia; cả hai "
              "nóng lên, và chuyện đó không đọc ra được từ sơ đồ.",
            bc,
            cach_sua="Chỉ một bộ cấp cho mỗi rail. Nếu là cấp song song có chủ ý (OR-ing, "
                     "nguồn dự phòng) thì khai `ckm.net_set(or_ing=true)`."))
    return ra


# --------------------------------------------------------------------------- 1c. chập rail–đất
def chap_nguon(cay: C.Cay, thuoc: dict[str, str]) -> list[PhatHien]:
    """Một nhóm điện có cả net nguồn lẫn net đất — tức rail bị nối vào GND (M3-04).

    Bản cũ **không thể** báo chuyện này: `_nhom_nguon` loại cả nhóm khi chỉ một net thành
    viên là đất, nên một rail +3V3 bị nối nhầm vào GND thì cả nhóm rơi khỏi mọi phép kiểm —
    im lặng tuyệt đối, đúng lúc mạch sẽ chết ngay khi cấp điện.
    """
    ra: list[PhatHien] = []
    for ten, nets in sorted(_nhom_net(cay, thuoc).items()):
        nguon, dat = [], []
        for nid in nets:
            c = cay.nut.get(nid, {}).get("canonical", {}) or {}
            ten_net = str(c.get("ten", "")).strip()
            if (c.get("loai") or "") == "gnd" or ten_net.upper() in TEN_DAT:
                dat.append((nid, ten_net or "GND"))
            elif (c.get("loai") or "") in ("power", "rail"):
                nguon.append((nid, ten_net or ten))
        if not (nguon and dat):
            continue
        cho = ", ".join(f"`{t}` ({cay.nut.get(n, {}).get('path') or n})"
                        for n, t in nguon[:2] + dat[:2])
        ra.append(PhatHien(
            "chap_nguon", "khong_dat", "blocker", _path_nong_nhat(cay, nets),
            f"Nhóm net {ten} gồm cả net nguồn lẫn net ĐẤT — rail đang nối vào GND: {cho}. "
            "Mạch sẽ chết ngay khi cấp điện, và cầu chì (nếu có) là thứ duy nhất đứng giữa.",
            cach_sua="Tách hai net ra. Đây gần như luôn là một Port nối sai hoặc một net "
                     "trùng tên bị hợp nhất ngoài ý muốn."))
    return ra


# --------------------------------------------------------------------------- 1. dòng cấp
def ngan_sach_dong(cay: C.Cay, tf: TraFact, phang: dict[str, list[str]],
                   thuoc: dict[str, str]) -> list[PhatHien]:
    """`Iout.max(khối nguồn) ≥ Σ I.max(khối tiêu thụ nối vào Port đó)`.

    Xét theo **NET ĐIỆN** (nhóm sau khi hợp nhất qua Port), không theo từng net phạm vi.
    Hai lý do, cả hai đo được:

      - một đường nguồn đi qua ba khối gồm bốn net phạm vi; xét từng net thì cùng một ràng
        buộc bị báo **bốn lần**, và người học được cách bỏ qua bảng ERC;
      - hai vế của phép cộng nằm ở hai cấp khác nhau: `iout_max` trên chân LDO nằm sâu
        trong khối nguồn, `i_max` trên chân MCU nằm sâu trong khối MCU. Chỉ net điện mới
        thấy được cả hai.

    Người tiêu thụ có thể là một lá, hoặc một khối có Fact `i_max` khai ở chính khối (một
    khối đã đo cả cụm). Khi khối có Fact riêng thì dùng nó và KHÔNG cộng thêm lá bên trong
    — cộng cả hai là tính hai lần cùng một dòng điện.

    Thiếu một vế thì trả "chưa đủ dữ kiện" kèm tên thứ còn thiếu. §4.2 ghi rõ: *"thiếu →
    chưa đủ dữ kiện, không đoán"*.
    """
    ra: list[PhatHien] = []
    for ten, thanh_vien in sorted(_nhom_nguon(cay, thuoc).items()):
        cap, tieu = _hai_ve_dong(cay, tf, thanh_vien)
        path = _path_nong_nhat(cay, thanh_vien)
        if not cap:
            ra.append(PhatHien(
                "ngan_sach_dong", "chua_du_du_kien", "info", path,
                f"Net nguồn {ten}: chưa biết khối nào cấp nó, hoặc khối cấp chưa có Fact "
                "dòng ra tối đa. Không kết luận được ngân sách dòng.",
                cach_sua="Khai Fact `iout_max` ở Port power_out của khối nguồn (nguồn là "
                         "datasheet của LDO/DC-DC), hoặc nói rõ khối nào cấp net này."))
            continue
        if not tieu:
            ra.append(PhatHien(
                "ngan_sach_dong", "chua_du_du_kien", "info", path,
                f"Net nguồn {ten} có khối cấp ({cap['ten']}) nhưng chưa linh kiện/khối nào "
                "nối vào có Fact dòng tiêu thụ. Chưa đủ dữ kiện để cộng.",
                bang_chung=[_cite(cap["fact"])],
                cach_sua="Nạp Fact `i_max` cho các linh kiện dùng net này."))
            continue

        i_cap, dv = _gt(cap["fact"])
        tong = 0.0
        thieu: list[str] = []
        bc = [_cite(cap["fact"])]
        for t in tieu:
            if t.get("fact") is None:
                thieu.append(t["ten"])
                continue
            v, _ = _gt(t["fact"])
            tong += 0.0 if v != v else v          # NaN thì bỏ, và nó vào `thieu` bên dưới
            if v != v:
                thieu.append(t["ten"])
            else:
                bc.append(_cite(t["fact"]))

        du = f"{_mA(i_cap)} cấp cho {_mA(tong)} tiêu thụ"
        if thieu:
            ra.append(PhatHien(
                "ngan_sach_dong", "chua_du_du_kien", "info", path,
                f"Net {ten}: cộng được {_mA(tong)} từ {len(tieu) - len(thieu)} linh kiện, "
                f"nhưng CHƯA có Fact dòng cho {', '.join(sorted(thieu))}. Tổng thật lớn hơn "
                f"con số này, nên không kết luận được dù {du}.",
                bang_chung=bc,
                cach_sua="Nạp Fact `i_max` cho những linh kiện còn thiếu rồi kiểm lại."))
        elif i_cap >= tong:
            ra.append(PhatHien(
                "ngan_sach_dong", "dat", "info", path,
                f"Net {ten}: {du} — còn dư {_mA(i_cap - tong)}.", bang_chung=bc))
        else:
            ra.append(PhatHien(
                "ngan_sach_dong", "khong_dat", "blocker", path,
                f"Net {ten} THIẾU dòng: khối cấp {_mA(i_cap)} nhưng tải cần {_mA(tong)} — "
                f"thiếu {_mA(tong - i_cap)}. Mạch sẽ chạy được lúc nhẹ tải rồi sụt áp khi "
                "đủ tải, và lỗi đó rất khó truy.",
                bang_chung=bc,
                cach_sua="Chọn nguồn dòng lớn hơn, bỏ tải khỏi rail này, hoặc kiểm lại "
                         "xem con số tiêu thụ có phải dòng đỉnh thay vì dòng trung bình."))
    return ra


def _mA(a: float) -> str:
    """Hiện dòng theo cách người đọc: mA khi nhỏ, A khi lớn. Dấu phẩy thập phân tiếng Việt."""
    if a != a:
        return "?"
    s = f"{a * 1000:.0f} mA" if abs(a) < 1 else f"{a:.3g} A"
    return s.replace(".", ",")


def _nhom_nguon(cay: C.Cay, thuoc: dict[str, str]) -> dict[str, list[str]]:
    """Nhóm net điện nào là nguồn: có ít nhất một net thành viên khai `loai` power/rail."""
    ra: dict[str, list[str]] = {}
    la_nguon: set[str] = set()
    for nid, ten in thuoc.items():
        n = cay.nut.get(nid)
        if n is None or n["loai"] != "net":
            continue
        ra.setdefault(ten, []).append(nid)
        if (n["canonical"].get("loai") or "") in ("power", "rail", "gnd"):
            la_nguon.add(ten)
    return {k: sorted(v) for k, v in ra.items()
            if k in la_nguon and not _la_dat(cay, v)}


def _la_dat(cay: C.Cay, nets: list[str]) -> bool:
    """Net đất không có ngân sách dòng theo nghĩa này — bỏ, đừng báo một dòng vô nghĩa."""
    for nid in nets:
        c = cay.nut.get(nid, {}).get("canonical", {})
        if (c.get("loai") or "") == "gnd":
            return True
        if str(c.get("ten", "")).strip().upper() in ("GND", "VSS", "AGND", "DGND"):
            return True
    return False


def _path_nong_nhat(cay: C.Cay, nets: list[str]) -> str:
    """Path của khối sở hữu net NÔNG nhất trong nhóm — chỗ người sẽ đi tìm để sửa."""
    tot: tuple[int, str] | None = None
    for nid in nets:
        p = cay.nut.get(cay.cha(nid) or "", {}).get("path") or "/board"
        k = (C.do_sau(p), p)
        if tot is None or k < tot:
            tot = k
    return tot[1] if tot else "/board"


def _hai_ve_dong(cay: C.Cay, tf: TraFact, nets: list[str]
                 ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Ai cấp net điện này, và ai tiêu thụ nó — quét MỌI net phạm vi trong nhóm.

    "Ai cấp" = Port `power_out` có Fact `iout_max`, ở bất kỳ cấp nào (thường là chân LDO
    nằm sâu trong khối nguồn). "Ai tiêu thụ" = lá/khối còn lại — trừ lá nằm trong một khối
    đã có Fact `i_max` riêng, khi đó lấy khối để không cộng hai lần.
    """
    cap: dict[str, Any] | None = None
    tieu: list[dict[str, Any]] = []
    khoi_co_fact: set[str] = set()
    da_thay: set[str] = set()

    for pid in sorted({p for nid in nets for p in cay.noi.get(nid, [])}):
        p = cay.port.get(pid)
        if p is None:
            continue
        m = cay.nut.get(p["module_id"])
        if m is None:
            continue
        la_la = m.get("kind") == "leaf"
        ct = ([f"port:{m.get('path')}.{p['ten']}"]
              + (chu_the_la(m) if la_la else [f"module:{m.get('path')}"]))

        # Ai cấp thì nhận ra bằng **FACT**, không gate theo hướng Port. Lý do đo được: Port
        # của lá sinh khi di cư mô hình phẳng có hướng `passive` (không đoán hướng tín hiệu
        # — xem `_huong_theo_ten`), nên gate theo hướng làm một LDO có Fact `iout_max` hẳn
        # hoi vẫn "không phải khối cấp", và cả ràng buộc im lặng biến thành "chưa đủ dữ
        # kiện". Fact là bằng chứng; hướng Port là dữ liệu bổ trợ có thể chưa biết.
        f_cap = tf.tra(ct, "i_out_max")
        if f_cap is not None or p["huong"] == "power_out":
            if f_cap is not None and (cap is None or _uu_tien(f_cap) < _uu_tien(cap["fact"])):
                cap = {"ten": m.get("path") or m["ten"], "fact": f_cap}
            continue
        if p["huong"] not in ("power_in", "passive", "in", "bidir"):
            continue
        if p["module_id"] in da_thay:
            continue                      # một khối/lá nối hai Port vào cùng net điện
        da_thay.add(p["module_id"])
        f = tf.tra(ct, "i_max")
        if not la_la and f is not None:
            khoi_co_fact.add(p["module_id"])
        tieu.append({"ten": m.get("path") or m["ten"], "fact": f,
                     "nut": p["module_id"], "la": la_la})

    if khoi_co_fact:
        tieu = [t for t in tieu
                if t["nut"] in khoi_co_fact
                or not _nam_trong(cay, t["nut"], khoi_co_fact)]
    # Khối KHÔNG có Fact riêng thì bỏ nó đi — lá bên trong nó đã đại diện. Giữ lại sẽ
    # thành một dòng "chưa có Fact dòng cho /board/mcu" trong khi U1 bên trong đã có.
    tieu = [t for t in tieu if t["la"] or t["fact"] is not None]
    return cap, tieu


def _nam_trong(cay: C.Cay, nid: str, to: set[str]) -> bool:
    cur = cay.cha(nid)
    while cur:
        if cur in to:
            return True
        cur = cay.cha(cur)
    return False


# --------------------------------------------------------------------------- 2. mức logic
def muc_logic_tren_net(cay: C.Cay, tf: TraFact,
                       phang: dict[str, list[str]]) -> list[PhatHien]:
    """VOH của bên phát ≥ VIH của bên thu, trên cùng một net.

    Dùng lại `compare.muc_logic` — cùng một luật, cùng một câu giải thích, cùng cách xử vế
    ĐỒNG. Việc của file này chỉ là **tìm hai đầu trên cây**: đi từ net phẳng xuống các lá,
    lấy lá nào có `voh` làm bên phát, lá nào có `vih` làm bên thu.
    """
    ra: list[PhatHien] = []
    la_theo_ref = {(n["canonical"].get("ref") or n["ten"]): n
                   for n in cay.nut.values() if n.get("kind") == "leaf"}
    for ten, chan in sorted(phang.items()):
        if len(chan) < 2:
            continue
        phat, thu = [], []
        for c in chan:
            ref, _, so = c.partition(".")
            n = la_theo_ref.get(ref)
            if n is None:
                continue
            ct = [f"pin:{ref}.{so}"] + chu_the_la(n)
            f_ra, f_vao = tf.tra(ct, "voh"), tf.tra(ct, "vih")
            if f_ra is not None:
                phat.append((c, n, f_ra))
            if f_vao is not None:
                thu.append((c, n, f_vao))
        for c_ra, n_ra, f_ra in phat:
            for c_vao, n_vao, f_vao in thu:
                if c_ra == c_vao:
                    continue
                kq = CP.muc_logic(f_ra, f_vao)
                ra.append(PhatHien(
                    "muc_logic",
                    "chua_du_du_kien" if kq.chua_kiem_chung else kq.ket_luan,
                    kq.muc, n_vao.get("path") or "/board",
                    f"Net {ten}, {c_ra} → {c_vao}: {kq.giai_thich}",
                    kq.bang_chung, kq.cach_sua))
    return ra


# --------------------------------------------------------------------------- 2b. quá áp
def _ap_cap_cua_net(cay: C.Cay, nets: list[str]) -> dict[str, Any] | None:
    """Điện áp mà net này ĐANG MANG, dựng thành một Fact để `compare` so được.

    Lấy từ `canonical.ap_danh_dinh` — trường mà `ckm.net_set(ap_danh_dinh=…)` ghi, tức
    **người khai**, nên tầng là `NGUOI`. Không suy từ tên net: một net tên "3V3" mà người
    ta cấp 5 V vào thì cái tên là thứ sai, và đó đúng là lỗi cần bắt.
    """
    from .chuan_hoa import chuan_hoa

    for nid in nets:
        n = cay.nut.get(nid)
        if n is None:
            continue
        raw = str(n["canonical"].get("ap_danh_dinh") or "").strip()
        if not raw:
            continue
        g = chuan_hoa(raw, ngu_canh="điện áp")
        if g.gia_tri is None:
            continue
        return {"key": "ap_danh_dinh", "value": g.gia_tri, "unit": g.don_vi or "V",
                "tier": "NGUOI", "subject": f"net:{n.get('path') or n['ten']}",
                "source": {"human_act_id": "ckm.net_set"},
                "explain": {"summary": f"net khai {raw}"}}
    return None


def _chiu_cua_chan(tf: TraFact, ct: list[str]) -> dict[str, Any] | None:
    """Mức chịu tối đa của một chân: `v_max` trước, rồi `vddio_max`."""
    return tf.tra(ct, "v_max") or tf.tra(ct, "vddio_max")


def qua_ap_tren_net(cay: C.Cay, tf: TraFact, phang: dict[str, list[str]],
                    thuoc: dict[str, str]) -> list[PhatHien]:
    """Net mang điện áp vượt mức chịu của một chân nối vào nó (§4.2, TC038).

    Luật này khác ba luật kia ở một điểm: chúng bắt mạch **chạy sai**, nó bắt mạch **hỏng**.
    5 V vào một chân chịu 3,6 V không làm lệch số đo — nó phá con chip, và không có cách
    nào "chạy lại để xem". Nên đây là luật duy nhất mà phát hiện muộn một lần đã quá muộn.

    `compare.qua_ap` đã có sẵn từ trước: câu chữ, mức `blocker`, cách chặn vế ĐỒNG — đủ cả.
    Nhưng `erc()` chỉ gọi bốn luật và không luật nào gọi nó, nên tác tử phải **tự nhớ** gọi
    `fact.compare` mới thấy. Một phép kiểm phụ thuộc vào việc ai đó nhớ gọi nó thì không
    phải một phép kiểm.

    Hai đường vào của cùng một lỗi, nên hai vế cấp:

      * **rail** — `ap_danh_dinh` của net (cấp sai nguồn);
      * **tín hiệu** — `voh` lớn nhất của một chân trên net (nối chân ra 5 V vào chân vào
        3,3 V; đây là đường thường gặp hơn, vì hai con chip đều "đúng" khi đọc riêng).

    Không có vế nào thì **im lặng** — không sinh dòng "đạt" cho mọi chân chưa ai đo. Một
    bảng ERC đầy dòng "đạt" cho thứ chưa đo là cách nhanh nhất để người đọc học được rằng
    bảng ấy không đáng đọc.
    """
    ra: list[PhatHien] = []
    la_theo_ref = {(n["canonical"].get("ref") or n["ten"]): n
                   for n in cay.nut.values() if n.get("kind") == "leaf"}
    net_cua_nhom: dict[str, list[str]] = {}
    for nid, ten in thuoc.items():
        if cay.nut.get(nid, {}).get("loai") == "net":
            net_cua_nhom.setdefault(ten, []).append(nid)

    for ten, chan in sorted(phang.items()):
        nets = sorted(net_cua_nhom.get(ten, []))
        if nets and _la_dat(cay, nets):
            continue

        # Thu thập từng chân trên net: nó chịu tối đa bao nhiêu, và nó có đẩy ra mức nào.
        chiu: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        voh: list[tuple[str, dict[str, Any]]] = []
        for c in chan:
            ref, _, so = c.partition(".")
            n = la_theo_ref.get(ref)
            if n is None:
                continue
            ct = [f"pin:{ref}.{so}"] + chu_the_la(n)
            if _co_bat(tf.tra(ct, "v_tolerant")):
                continue          # chân khai chịu được 5 V — không phải chỗ hỏng
            f_chiu = _chiu_cua_chan(tf, ct)
            if f_chiu is not None:
                chiu.append((c, n, f_chiu))
            f_ra = tf.tra(ct, "voh")
            if f_ra is not None:
                voh.append((c, f_ra))
        if not chiu:
            continue

        cap = _ap_cap_cua_net(cay, nets)
        nguon_vi = f"rail {ten}"
        if cap is None and voh:
            c_ra, cap = max(voh, key=lambda x: _gt(x[1])[0])
            nguon_vi = f"{c_ra} đẩy ra"
        if cap is None:
            continue

        for c, n, f_chiu in chiu:
            if cap.get("subject") == f_chiu.get("subject"):
                continue
            if nguon_vi.startswith(c + " "):
                continue          # chính chân ấy đẩy ra — không tự so với mình
            kq = CP.qua_ap(cap, f_chiu)
            if kq.ket_luan == "dat":
                continue          # trong giới hạn: đừng thêm một dòng vào bảng
            ra.append(PhatHien(
                "qua_ap",
                "chua_du_du_kien" if kq.chua_kiem_chung else kq.ket_luan,
                kq.muc, n.get("path") or _path_cua_ref(cay, c.partition(".")[0]),
                f"Net {ten} ({nguon_vi}) → {c}: {kq.giai_thich}",
                kq.bang_chung, kq.cach_sua))
    return ra


def _co_bat(f: dict[str, Any] | None) -> bool:
    """Fact cờ: có mặt và mang giá trị thật sự là "có"."""
    if f is None:
        return False
    v = f.get("value")
    if isinstance(v, str):
        return v.strip().lower() not in ("", "0", "false", "no", "khong", "không")
    return bool(v)


# --------------------------------------------------------------------------- 3. địa chỉ bus
def trung_dia_chi_bus(cay: C.Cay, tf: TraFact,
                      phang: dict[str, list[str]]) -> list[PhatHien]:
    """Hai linh kiện trên cùng bus I2C không được cùng địa chỉ (§4.2, ca HIER08).

    Phát hiện này rẻ nhưng cứu một buổi chiều: hai TMP102 cùng 0x48 thì bus vẫn có ACK, mã
    vẫn đọc ra số, và số đó là của con nào thì không ai biết.
    """
    ra: list[PhatHien] = []
    for ten, chan in sorted(phang.items()):
        theo_addr: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for c in chan:
            ref, _, so = c.partition(".")
            n = next((x for x in cay.nut.values()
                      if x.get("kind") == "leaf"
                      and (x["canonical"].get("ref") or x["ten"]) == ref), None)
            if n is None:
                continue
            f = tf.tra(chu_the_la(n), "addr")
            if f is None:
                continue
            theo_addr.setdefault(_chuan_addr(f.get("value")), []).append((ref, f))
        for addr, ds in sorted(theo_addr.items()):
            refs = sorted({r for r, _ in ds})
            if len(refs) > 1:
                ra.append(PhatHien(
                    "trung_dia_chi", "khong_dat", "blocker",
                    _path_cua_ref(cay, refs[0]),
                    f"Trên bus {ten}, {', '.join(refs)} cùng địa chỉ {addr}. Bus vẫn có "
                    "ACK và mã vẫn đọc ra số — nhưng số đó của con nào thì không ai biết.",
                    bang_chung=[_cite(f) for _, f in ds],
                    cach_sua="Đổi địa chỉ bằng chân ADDR/A0 của một con, hoặc tách sang "
                             "bus khác."))
    return ra


def _chuan_addr(v: Any) -> str:
    s = str(v).strip().lower().replace(" ", "")
    if s.startswith("0x"):
        try:
            return f"0x{int(s, 16):02x}"
        except ValueError:
            return s
    if s.isdigit():
        return f"0x{int(s):02x}"
    return s


def _path_cua_ref(cay: C.Cay, ref: str) -> str:
    for n in cay.nut.values():
        if n.get("kind") == "leaf" and (n["canonical"].get("ref") or n["ten"]) == ref:
            return cay.nut.get(n.get("parent_id") or "", {}).get("path") or "/board"
    return "/board"


# --------------------------------------------------------------------------- 4. pull-up bus
def pull_up_bus(cay: C.Cay, tf: TraFact, phang: dict[str, list[str]]) -> list[PhatHien]:
    """Mỗi bus I2C có ĐÚNG MỘT cụm pull-up, trong phạm vi khối sở hữu bus (§4.2).

    Hai chiều đều sai, và sai theo hai kiểu khác nhau:
      - không có  → bus không bao giờ lên mức cao; mạch không chạy, dễ thấy
      - hai cụm   → điện trở song song, dòng kéo gấp đôi; bus CHẠY nhưng sai sườn ở tốc độ
                    cao, và đó là loại lỗi tìm cả tuần

    Đếm bằng cách nhìn net phẳng: điện trở (ref bắt đầu bằng R) nối vào net bus. Chỉ đếm,
    không đoán giá trị — giá trị pull-up là việc của `compare.pull_up`.
    """
    ra: list[PhatHien] = []
    for ten, chan in sorted(phang.items()):
        if not _la_bus_i2c(cay, ten):
            continue
        r = sorted({c.partition(".")[0] for c in chan
                    if c.partition(".")[0].upper().startswith("R")})
        path = _path_so_huu_bus(cay, ten)
        # Khối SỞ HỮU bus là chỗ luật áp dụng, nhưng thứ người cần để đi sửa là điện trở
        # NẰM Ở ĐÂU. Hai thông tin khác nhau, nên nói cả hai.
        o_dau = {x: _path_cua_ref(cay, x) for x in r}
        if not r:
            ra.append(PhatHien(
                "pull_up", "khong_dat", "major", path,
                f"Bus {ten} không có điện trở kéo lên nào. I2C là open-drain — không có "
                "pull-up thì đường này không bao giờ lên mức cao.",
                cach_sua="Thêm một cụm pull-up (thường 4,7 kΩ ở 3,3 V) trong khối sở hữu "
                         "bus; giá trị đúng thì đối chiếu bằng fact.compare luật pull_up."))
        elif len(r) > 1:
            ra.append(PhatHien(
                "pull_up", "canh_bao", "major", path,
                f"Bus {ten} có {len(r)} điện trở kéo lên: "
                + ", ".join(f"{x} ở {o_dau[x]}" for x in r)
                + ". Song song nhau thì dòng kéo gấp đôi: bus vẫn CHẠY nhưng sườn sai ở "
                  "tốc độ cao — loại lỗi tìm cả tuần.",
                cach_sua="Giữ một cụm, bỏ cụm kia — thường cụm trên module cảm biến mua "
                         "sẵn là cụm cần bỏ."))
        else:
            ra.append(PhatHien("pull_up", "dat", "info", path,
                               f"Bus {ten} có đúng một cụm kéo lên: {r[0]} ở {o_dau[r[0]]}."))
    return ra


_TEN_BUS_I2C = ("SDA", "SCL", "I2C")


def _la_bus_i2c(cay: C.Cay, ten_net: str) -> bool:
    t = ten_net.strip().upper().split("/")[-1].split(".")[-1]
    if t.startswith(_TEN_BUS_I2C):
        return True
    for n in cay.nut.values():
        if n["loai"] == "net" and n["ten"] == ten_net:
            c = n["canonical"]
            if str(c.get("bus", "")).upper().startswith("I2C"):
                return True
    return False


def _path_so_huu_bus(cay: C.Cay, ten_net: str) -> str:
    for n in cay.nut.values():
        if n["loai"] == "net" and n["ten"] == ten_net:
            return cay.nut.get(n.get("parent_id") or "", {}).get("path") or "/board"
    return "/board"


# =========================================================================== §4.1 kiểm chủ thể
def kiem_chu_the(store: Any, chu_the: str) -> str:
    """Chủ thể Fact theo cấp có trỏ tới một nút CÓ THẬT không? Trả câu cảnh báo, hoặc "".

    Chỉ soi chủ thể **trông như** chủ thể theo cấp (`module:/…`, `port:/…`, `net:/…`,
    `leaf:…`). Chủ thể tự do như `he-thong` hay `chip:RPi-Zero-2W` không bị chạm — chúng
    hợp lệ và đã dùng từ trước.

    Vì sao cảnh báo mà không chặn: một Fact gắn sai chủ thể vẫn là một con số thật người
    vừa đọc từ datasheet; mất nó tệ hơn giữ nó ở chỗ hơi lệch. Nhưng im lặng thì nó sẽ
    không bao giờ được ERC nhìn thấy, và người sẽ tưởng đã khai rồi.
    """
    ct = (chu_the or "").strip()
    if not ct.startswith(("module:/", "port:/", "net:/", "leaf:")):
        return ""
    cay = C.Cay.doc(store)
    if ct.startswith("leaf:"):
        ref = ct.removeprefix("leaf:")
        co = any(n.get("kind") == "leaf"
                 and (n["canonical"].get("ref") or n["ten"]) == ref
                 for n in cay.nut.values())
        return "" if co else (
            f"Chưa có linh kiện nào ref {ref} trong cây khối, nên Fact này sẽ không được "
            "ERC nhìn thấy. Đưa linh kiện vào bản đồ (ckm.chip_add) hoặc kiểm lại ref.")
    if ct.startswith("port:/"):
        than = ct.removeprefix("port:")
        duong, _, ten = than.rpartition(".")
        co = any(p["ten"] == ten
                 and (cay.nut.get(p["module_id"], {}).get("path") or "") == duong
                 for p in cay.port.values())
        return "" if co else (
            f"Chưa có Port {ten} ở {duong}. Khai Port bằng ckm.port_set trước, nếu không "
            "Fact này sẽ nằm ngoài mọi phép kiểm.")
    duong = ct.split(":", 1)[1]
    co = any((n.get("path") or "") == duong for n in cay.nut.values())
    return "" if co else (
        f"Chưa có nút nào ở đường {duong} trong cây khối. Kiểm lại đường, hoặc dựng khối "
        "trước bằng ckm.module_set.")


# =========================================================================== §8 explain khối
def explain_khoi(cay: C.Cay, module_id: str, *, ex_cu: dict[str, Any] | None = None,
                 req: list[str] | None = None) -> dict[str, Any]:
    """Bảy câu của §8 cho một khối. Hai câu MỚI do mã dựng từ cây, không do mô hình viết.

    §8 đòi lớp giải thích của khối trả lời: làm gì (REQ nào) · **giao tiếp gì (Port)** ·
    **gồm gì (con)** · dựa vào đâu · khác bản trước · việc tiếp theo · tin được đến đâu.

    Hai câu in đậm là dữ liệu, không phải văn: chúng đọc được từ cây một cách xác định.
    Bắt mô hình viết chúng là mời nó mô tả một khối theo trí nhớ — và nó sẽ viết đúng
    trong chín lần, rồi lần thứ mười viết một Port không tồn tại.
    """
    module_id = C.tim_nut(cay, module_id) or module_id
    n = cay.nut.get(module_id, {})
    ports = [cay.port[p] for p in cay.port_cua.get(module_id, [])]
    con_khoi = [cay.nut[x].get("path") or x for x in cay.khoi_con(module_id)]
    con_la = [(cay.nut[x]["canonical"].get("ref") or cay.nut[x]["ten"])
              for x in cay.con_truc_tiep(module_id)
              if cay.nut[x].get("kind") == "leaf"]
    ex = dict(ex_cu or {})
    ex["giao_tiep"] = (", ".join(f"{p['ten']} ({p['huong']})" for p in ports)
                       or "chưa khai Port nào — bên ngoài chưa biết khối này giao tiếp bằng gì")
    ex["gom"] = ("; ".join(filter(None, [
        ", ".join(con_khoi) if con_khoi else "",
        ("linh kiện: " + ", ".join(con_la)) if con_la else ""])) or "chưa có gì bên trong")
    if req:
        ex["thuc_hien_req"] = ", ".join(req)
    # `confidence` = tầng THẤP NHẤT trong khối (§8 "tin được đến đâu"), tính từ các lá.
    tang = [cay.nut[x].get("tier") for x in _moi_con(cay, module_id)
            if cay.nut[x].get("tier")]
    if tang:
        from .ckm import thu_tu_tang
        ex["confidence"] = max(tang, key=thu_tu_tang)
    return ex


def _moi_con(cay: C.Cay, nid: str) -> list[str]:
    ra: list[str] = []
    ds = list(cay.con_truc_tiep(nid))
    while ds:
        x = ds.pop()
        ra.append(x)
        ds += cay.con_truc_tiep(x)
    return ra
