# -*- coding: utf-8 -*-
"""Bước 4 — bố cục theo khối. EIDE-SCH-44 §4, ca SCH05–08, SCH17.

Câu quyết định toàn bộ tệp này nằm ở §4 dòng cuối:

    "Mô hình không tự 'vẽ' toạ độ; nó chỉ chọn style, nhóm module, và gợi ý luồng — toạ độ
     do mã tính (xác định, lặp lại được với cùng đầu vào)."

Nên ở đây không có chỗ nào gọi mô hình. Và "xác định" không phải một lời hứa mà là một phép
kiểm: SCH17 đòi *chạy 5 lần cùng toạ độ*, nên mọi vòng lặp phải đi trên danh sách đã **sắp**,
không đi trên `dict` hay `set`.

**Tiêu chí nghiệm thu đo bằng số, không chấm cảm tính** (§4): 0 ký hiệu chồng nhau · 0 dây
cắt qua thân ký hiệu · 0 dây chéo · tỉ lệ net dùng nhãn ≤ 70 % · trang ≤ A3 · mọi ký hiệu
có ref/value hiển thị không đè. Vi phạm thì **nới vùng 20 % và lặp** (≤ 5 lần).

Một điều cố ý làm đơn giản hơn tài liệu, và nói rõ ở đây: §4 đề nghị đi dây bằng A* trên
lưới có phạt gấp. Bản này **không** đi dây giữa các khối — mọi net liên khối dùng nhãn, và
dây chỉ nối trong vùng khi hai chân thẳng hàng. Lý do: một mạch có dây vẽ sai tệ hơn một mạch
dùng nhãn, vì nhãn thì người đọc vẫn truy được net còn dây sai thì họ tin mắt mình. Tỉ lệ
nhãn vì thế sẽ cao, và tiêu chí ≤ 70 % sẽ **cảnh báo** — đó là một cảnh báo đúng, không phải
một con số cần lách. Đi dây thật là việc của SCH-C.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# §4 — lưới KiCad. Mọi toạ độ là bội của con số này; KiCad bắt chân ký hiệu vào lưới, và
# một ký hiệu lệch lưới thì dây nối vào nó không bao giờ khớp.
LUOI = 1.27

# Khổ giấy (mm). §4: "trang ≤ A3".
KHO_GIAY = {"A4": (297.0, 210.0), "A3": (420.0, 297.0)}
LE = 12.7                     # lề, chừa cho khung tên KiCad

# Kích thước ký hiệu — ước lượng theo số chân, vì bản này chưa đọc hình vẽ thật từ .kicad_sym.
# Ước RỘNG TAY: một ký hiệu bị coi nhỏ hơn thực tế sẽ chồng lên cái bên cạnh, và phép kiểm
# "0 chồng nhau" sẽ nói đạt trong khi hình vẽ thì không.
RONG_IC = 25.4
CAO_MOI_CHAN = 2.54
CAO_TOI_THIEU = 10.16
CACH_NHAU = 7.62              # khoảng trống tối thiểu giữa hai ký hiệu

# Chiều cao chữ THẬT khi vẽ, tính bằng mm. Bố cục sở hữu con số này (nó làm việc bằng mm),
# còn bộ vẽ đổi nó sang px — nếu hai bên tự đoán riêng thì phép kiểm "chữ không đè" nói về
# một hình khác với hình người thấy, và nó sẽ luôn đạt. Đo lần đầu đúng lỗi đó: hộp bao cao
# 1,27 mm trong khi chữ vẽ ra cao 2,8 mm.
CAO_CHU_MM = CHU_CAO_CO_SO = 1.27 * 2.2
CACH_NHAN = 3 * LUOI          # khoảng cách hai nhãn kề nhau — phải ≥ chiều cao chữ

NGUONG_NHAN = 0.70            # §4: tỉ lệ net dùng nhãn ≤ 70 %
SO_LAN_NOI = 5                # §4: "nới vùng 20 % và lặp (≤ 5 lần)"


def tron(x: float) -> float:
    """Bắt vào lưới 1,27 mm. Làm tròn tới bội gần nhất, không cắt xuống."""
    return round(x / LUOI) * LUOI


@dataclass(slots=True)
class O:
    """Một ký hiệu đã đặt."""

    ref: str
    x: float
    y: float
    rong: float
    cao: float
    khoi: str = ""
    nhan: list[str] = field(default_factory=list)      # nhãn net gắn vào ký hiệu này

    @property
    def hop(self) -> tuple[float, float, float, float]:
        return (self.x, self.y, self.x + self.rong, self.y + self.cao)

    def to_dict(self) -> dict[str, Any]:
        return {"ref": self.ref, "x": round(self.x, 2), "y": round(self.y, 2),
                "rong": round(self.rong, 2), "cao": round(self.cao, 2),
                "khoi": self.khoi, "nhan": list(self.nhan)}


@dataclass(slots=True)
class Vung:
    """Vùng của một khối (§4: "mỗi module là một vùng chữ nhật trên lưới")."""

    khoi: str
    ten: str
    x: float
    y: float
    rong: float
    cao: float

    def to_dict(self) -> dict[str, Any]:
        return {"khoi": self.khoi, "ten": self.ten, "x": round(self.x, 2),
                "y": round(self.y, 2), "rong": round(self.rong, 2),
                "cao": round(self.cao, 2)}


@dataclass(slots=True)
class BoCuc:
    kho: str = "A4"
    vung: list[Vung] = field(default_factory=list)
    o: list[O] = field(default_factory=list)
    day: list[dict[str, Any]] = field(default_factory=list)
    nhan: list[dict[str, Any]] = field(default_factory=list)
    tieu_chi: dict[str, Any] = field(default_factory=dict)
    canh_bao: list[str] = field(default_factory=list)
    so_lan_noi: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"kho": self.kho, "vung": [v.to_dict() for v in self.vung],
                "o": [x.to_dict() for x in self.o], "day": self.day, "nhan": self.nhan,
                "tieu_chi": self.tieu_chi, "canh_bao": list(self.canh_bao),
                "so_lan_noi": self.so_lan_noi}


# =========================================================================== xếp vùng
def _luong(cay: Any) -> list[tuple[str, str]]:
    """Thứ tự khối trái → phải theo luồng tín hiệu (§4: nguồn vào, MCU giữa, ngoại vi phải).

    Suy từ **hướng Port**, không từ tên khối: khối chỉ có `power_out` là nguồn, khối có nhiều
    Port nhất là trung tâm. Suy từ tên ("PWR", "MCU") sẽ đúng trên mạch mẫu và sai trên mạch
    thật, vì tên khối là do người đặt.
    """
    diem: list[tuple[int, int, str, str]] = []
    for nid, n in sorted(cay.nut.items()):
        if (n.get("kind") or "") not in ("block", "subblock"):
            continue
        ports = [cay.port[p] for p in cay.port_cua.get(nid, [])]
        huong = [p["huong"] for p in ports]
        chi_cap = bool(huong) and all(h in ("power_out", "out") for h in huong)
        chi_nhan = bool(huong) and all(h in ("power_in", "in") for h in huong)
        if chi_cap:
            cot = 0                       # nguồn vào bên trái
        elif chi_nhan:
            cot = 2                       # chỉ nhận ⇒ ngoại vi bên phải
        else:
            cot = 1                       # vừa nhận vừa phát ⇒ trung tâm
        # Khoá phụ: NHIỀU Port hơn thì đứng trước trong cùng cột (khối trung tâm to nằm trên),
        # rồi tới path để kết quả xác định.
        diem.append((cot, -len(ports), n.get("path") or nid, nid))
    diem.sort()
    return [(nid, path) for _, _, path, nid in diem]


def _o_trong_vung(cay: Any, nid: str) -> list[O]:
    """Ký hiệu trong một khối: lá trực tiếp của khối đó. IC trước, thụ động sau (§4)."""
    ra: list[O] = []
    for x in sorted(cay.con_truc_tiep(nid)):
        n = cay.nut[x]
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        so_chan = max(1, len(cay.port_cua.get(x, [])))
        thu_dong = _la_thu_dong(ref)
        rong = 7.62 if thu_dong else RONG_IC
        cao = max(CAO_TOI_THIEU, CAO_MOI_CHAN * ((so_chan + 1) // 2 + 1))
        ra.append(O(ref=ref, x=0, y=0, rong=rong, cao=cao, khoi=nid))
    # IC (nhiều chân) trước, rồi thụ động — §4: "IC/MCU ở giữa; linh kiện thụ động gắn với
    # chân nào thì đặt sát chân đó". Bản này đặt thụ động NGAY SAU IC trong cùng vùng.
    ra.sort(key=lambda z: (_la_thu_dong(z.ref), -z.cao, z.ref))
    return ra


_TIEN_TO_THU_DONG = ("R", "C", "L", "D", "Y", "SW", "FB", "TP")


def _la_thu_dong(ref: str) -> bool:
    t = "".join(c for c in ref if c.isalpha()).upper()
    return t in _TIEN_TO_THU_DONG


# =========================================================================== bố cục
def tinh_bo_cuc(cay: Any, phang: dict[str, list[str]], *,
               kho: str = "A4") -> BoCuc:
    """Tính bố cục. Xác định: cùng cây + cùng netlist ⇒ cùng toạ độ, mọi lần."""
    for lan in range(SO_LAN_NOI + 1):
        bc = _mot_lan(cay, phang, kho=kho, no=1.0 + 0.2 * lan)
        bc.so_lan_noi = lan
        bc.tieu_chi = kiem_tieu_chi(bc, phang)
        if bc.tieu_chi["dat"]:
            return bc
        if lan == SO_LAN_NOI and kho == "A4":
            # Hết cách trên A4 thì thử A3 — §4 cho phép tới A3, và một trang chật là lý do
            # thật để đổi khổ, không phải lý do để bỏ tiêu chí.
            return tinh_bo_cuc(cay, phang, kho="A3")
    bc.canh_bao.append(
        f"Đã nới vùng {SO_LAN_NOI} lần trên khổ {bc.kho} mà vẫn chưa đạt tiêu chí bố cục: "
        + "; ".join(bc.tieu_chi["vi_pham"])
        + ". Bố cục vẫn dùng được nhưng khó đọc — nên chuyển sang sheet phân cấp.")
    return bc


def _mot_lan(cay: Any, phang: dict[str, list[str]], *, kho: str, no: float) -> BoCuc:
    bc = BoCuc(kho=kho)
    rong_giay, cao_giay = KHO_GIAY.get(kho, KHO_GIAY["A4"])
    x = LE
    cot_truoc = -1

    cao_dung_duoc = cao_giay - 2 * LE
    for nid, path in _luong(cay):
        o = _o_trong_vung(cay, nid)
        if not o:
            continue
        # Xếp trong vùng theo CỘT, và cuộn sang cột mới khi hết chiều cao trang.
        #
        # Bản đầu xếp mọi ký hiệu thành một cột duy nhất; ca đo với 40 điện trở trong một
        # khối cho thấy nó tràn cả khổ A3. Một vùng cao hơn trang không phải "bố cục chật"
        # mà là bố cục KHÔNG DÙNG ĐƯỢC, và nới vùng 20 % năm lần chỉ làm nó tràn xa hơn.
        cao_tb = max(z.cao for z in o) + CACH_NHAU
        moi_cot = max(1, int((cao_dung_duoc - 2 * CACH_NHAU) // cao_tb))
        so_cot = (len(o) + moi_cot - 1) // moi_cot
        rong_cot = max(z.rong for z in o) + CACH_NHAU
        cao_noi_dung = min(len(o), moi_cot) * cao_tb
        vung = Vung(khoi=nid, ten=cay.nut[nid]["ten"],
                    x=tron(x), y=tron(LE),
                    rong=tron(so_cot * rong_cot + CACH_NHAU),
                    cao=tron(min(cao_dung_duoc, (cao_noi_dung + CACH_NHAU) * no)))
        for i, z in enumerate(o):
            cot, hang = divmod(i, moi_cot)
            z.x = tron(vung.x + CACH_NHAU / 2 + cot * rong_cot)
            z.y = tron(vung.y + CACH_NHAU + hang * cao_tb)
            bc.o.append(z)
        bc.vung.append(vung)
        x = vung.x + vung.rong + CACH_NHAU
        cot_truoc += 1

    # Nhãn net: mọi net chạm ≥ 2 vùng khác nhau, hoặc net nguồn/đất. Dây chỉ dùng cho net
    # nằm TRỌN trong một vùng và hai chân thẳng hàng — xem ghi chú đầu tệp.
    theo_ref = {z.ref: z for z in bc.o}
    for ten in sorted(phang):
        chan = sorted(set(phang[ten]))
        vung_cua = {theo_ref[c.split(".", 1)[0]].khoi for c in chan
                    if c.split(".", 1)[0] in theo_ref}
        trong_mot_vung = len(vung_cua) == 1 and len(chan) == 2
        if trong_mot_vung and _thang_hang(chan, theo_ref):
            a, b = chan
            za, zb = theo_ref[a.split(".", 1)[0]], theo_ref[b.split(".", 1)[0]]
            bc.day.append({"net": ten,
                           "refs": sorted({za.ref, zb.ref}),
                           "tu": [round(za.x + za.rong, 2), round(za.y + za.cao / 2, 2)],
                           "den": [round(zb.x, 2), round(zb.y + zb.cao / 2, 2)],
                           "so_gap": 0})
            continue
        for c in chan:
            ref = c.split(".", 1)[0]
            z = theo_ref.get(ref)
            if z is None:
                continue
            z.nhan.append(ten)
            bc.nhan.append({"net": ten, "ref": ref, "chan": c.split(".", 1)[-1],
                            "x": round(z.x + z.rong + LUOI, 2),
                            "y": round(z.y + CACH_NHAN * len(z.nhan), 2)})
    return bc


def _thang_hang(chan: list[str], theo_ref: dict[str, O]) -> bool:
    a, b = chan
    za, zb = theo_ref.get(a.split(".", 1)[0]), theo_ref.get(b.split(".", 1)[0])
    if za is None or zb is None or za.ref == zb.ref:
        return False
    return abs((za.y + za.cao / 2) - (zb.y + zb.cao / 2)) < LUOI


# =========================================================================== tiêu chí §4
def kiem_tieu_chi(bc: BoCuc, phang: dict[str, list[str]]) -> dict[str, Any]:
    """Sáu tiêu chí của §4, đo bằng SỐ. Trả `{dat, vi_pham, so_liệu}`.

    Không có tiêu chí nào ở đây là "đẹp". Mỗi cái đo một thứ làm người đọc sai: hai ký hiệu
    chồng nhau thì mất một cái; dây cắt thân ký hiệu thì trông như nối vào chân; dây chéo thì
    người lần theo sai đường; quá nhiều nhãn thì phải tra từng cái.
    """
    vi_pham: list[str] = []

    chong = _dem_chong(bc.o)
    if chong:
        vi_pham.append(f"{len(chong)} cặp ký hiệu chồng nhau: "
                       + "; ".join(f"{a}–{b}" for a, b in chong[:4]))

    cat = _dem_day_cat_than(bc)
    if cat:
        vi_pham.append(f"{len(cat)} dây cắt qua thân ký hiệu: " + ", ".join(cat[:4]))

    cheo = [d for d in bc.day if d.get("so_gap", 0) > 3]
    if cheo:
        vi_pham.append(f"{len(cheo)} dây gấp quá 3 đoạn")

    tong_net = len(phang) or 1
    net_dung_nhan = len({n["net"] for n in bc.nhan})
    ty = net_dung_nhan / tong_net
    if ty > NGUONG_NHAN:
        vi_pham.append(f"{ty:.0%} net dùng nhãn (> {NGUONG_NHAN:.0%}) — mạch khó đọc, nên "
                       "chuyển sang sheet phân cấp")

    rong_giay, cao_giay = KHO_GIAY.get(bc.kho, KHO_GIAY["A4"])
    trong_giay = all(z.x + z.rong <= rong_giay - LE and z.y + z.cao <= cao_giay - LE
                     for z in bc.o)
    if not trong_giay:
        ra = [z.ref for z in bc.o
              if z.x + z.rong > rong_giay - LE or z.y + z.cao > cao_giay - LE]
        vi_pham.append(f"{len(ra)} ký hiệu tràn khỏi khổ {bc.kho}: " + ", ".join(ra[:4]))

    lech_luoi = [z.ref for z in bc.o
                 if abs(z.x / LUOI - round(z.x / LUOI)) > 1e-6
                 or abs(z.y / LUOI - round(z.y / LUOI)) > 1e-6]
    if lech_luoi:
        vi_pham.append(f"{len(lech_luoi)} ký hiệu lệch lưới {LUOI} mm: "
                       + ", ".join(lech_luoi[:4]))

    return {"dat": not vi_pham, "vi_pham": vi_pham,
            "so_ky_hieu": len(bc.o), "so_vung": len(bc.vung),
            "so_day": len(bc.day), "so_nhan": len(bc.nhan),
            "ty_le_net_dung_nhan": round(ty, 3),
            "cap_chong_nhau": len(chong), "day_cat_than": len(cat),
            "trong_kho_giay": trong_giay, "kho": bc.kho}


def _dem_chong(o: list[O]) -> list[tuple[str, str]]:
    ra: list[tuple[str, str]] = []
    for i in range(len(o)):
        for j in range(i + 1, len(o)):
            a, b = o[i], o[j]
            if (a.x < b.x + b.rong and b.x < a.x + a.rong
                    and a.y < b.y + b.cao and b.y < a.y + a.cao):
                ra.append((a.ref, b.ref))
    return ra


def _dem_day_cat_than(bc: BoCuc) -> list[str]:
    """Dây đi qua thân một ký hiệu KHÔNG phải hai đầu của nó.

    Chỉ xét đoạn ngang/dọc, vì bố cục này chỉ sinh dây trực giao. Một dây chéo lọt vào đây
    sẽ không bị xét — nên nếu về sau có đi dây chéo thì phép kiểm này phải mở rộng, và ghi
    chú này là chỗ để nhớ.
    """
    ra: list[str] = []
    for d in bc.day:
        x1, y1 = d["tu"]
        x2, y2 = d["den"]
        for z in bc.o:
            if z.ref in (d.get("refs") or []):
                continue          # hai đầu dây thì không tính là "cắt qua thân"
            x3, y3, x4, y4 = z.hop
            if abs(y1 - y2) < 1e-9:                       # đoạn ngang
                if y3 < y1 < y4 and min(x1, x2) < x4 and x3 < max(x1, x2):
                    if not (abs(x1 - x4) < 1e-9 or abs(x2 - x3) < 1e-9):
                        ra.append(f"{d['net']} qua {z.ref}")
            elif abs(x1 - x2) < 1e-9:                     # đoạn dọc
                if x3 < x1 < x4 and min(y1, y2) < y4 and y3 < max(y1, y2):
                    ra.append(f"{d['net']} qua {z.ref}")
    return ra
