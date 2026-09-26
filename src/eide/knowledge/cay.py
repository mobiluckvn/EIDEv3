# -*- coding: utf-8 -*-
"""Cây khối phân cấp — EIDE-HIER-45. Bước HIER-A.

    "Mạch → khối → khối con → linh kiện (lá) · Port ở biên khối · Net theo phạm vi ·
     flatten bằng mã"

Tài liệu này **sửa** mô hình phẳng của §C2 mà bước CKM vừa dựng. Chỗ đổi quan trọng nhất
không phải cái cây — mà là **Port**.

Trước: hai khối "nối nhau" vì chúng cùng viết chuỗi `"3V3"` vào `tin_hieu_ra`/`tin_hieu_vao`.
Đó là một phỏng đoán theo tên, và nó không chịu được ba câu hỏi: khối này *cấp* hay *nhận*
3V3? nó chịu được bao nhiêu dòng? sửa ruột khối có làm hỏng người dùng khối không?

Sau: Port là **hợp đồng** có hướng, có ràng buộc, có Fact chống lưng. Và nó mua được một
tính chất mà mô hình phẳng không có: **đóng gói** — sửa trong khối mà không đổi Port thì
bên ngoài không cần biết, không STALE ra ngoài (§6). Bất biến E9006 là phép kiểm của đúng
câu đó, và nó kiểm bằng cách so `flatten` trước/sau.

Hai điều cố ý làm khác tài liệu, mỗi điều có lý do đo được:

**1. `parent_id` dùng cho mọi loại nút.** §2.3 tách `module.parent_id` và
`net.scope_module_id`. Cả hai là cùng một quan hệ "nút này nằm trong nút nào", nên một cột
— xem ghi chú ở `store/db.py`. Hai cột là hai chỗ để lệch nhau.

**2. Bất biến kiểm trong `chieu()`.** §3 nói "kiểm bằng mã sau mỗi thay đổi" mà không nói
ai gọi. Đặt ở `chieu()` vì đó là **một cửa duy nhất** mọi thay đổi cây phải đi qua. Hệ quả
đúng: một cái cây có chu trình làm việc dựng lại NỔ, thay vì sống âm thầm trong kho.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

# §2.1 — bốn loại nút cây. `leaf` là linh kiện; §2.1 nói rõ "linh kiện là LÁ của cây khối".
KIND = ("board", "block", "subblock", "leaf")
KIND_KHOI = ("board", "block", "subblock")     # có con được

# §2.1 Port. `huong` quyết định ERC sau này đọc net theo chiều nào.
HUONG = ("in", "out", "bidir", "power_in", "power_out", "passive")
LOAI_PORT = ("single", "bus")

# §2.1 mục Net.
LOAI_NET_CAY = ("signal", "power", "gnd", "bus_member")

# §2.1: "độ sâu không giới hạn; depth > 4 → cảnh báo bố cục/UI (không cấm)".
SAU_KHUYEN_NGHI = 4


def duong(parent_path: str | None, ten: str) -> str:
    """Tên đầy đủ (§2.2 mục 4): `/board/mcu/xtal`."""
    t = (ten or "").strip("/")
    if not parent_path:
        return f"/{t}"
    return f"{parent_path.rstrip('/')}/{t}"


def ma_port(module_path: str, ten: str) -> str:
    return f"port:{module_path}.{ten}"


def do_sau(path: str) -> int:
    return len([x for x in (path or "").split("/") if x])


# =========================================================================== hợp nhất net
class HopNhat:
    """Union-Find — §3 dùng nó để hợp nhất net qua Port.

    Viết tay vì nó mười dòng, và vì một phụ thuộc mới phải trả giá bằng một lý do; ở đây
    không có lý do nào.
    """

    def __init__(self) -> None:
        self._cha: dict[str, str] = {}

    def tim(self, x: str) -> str:
        self._cha.setdefault(x, x)
        while self._cha[x] != x:
            self._cha[x] = self._cha[self._cha[x]]
            x = self._cha[x]
        return x

    def hop(self, a: str, b: str) -> None:
        ra, rb = self.tim(a), self.tim(b)
        if ra != rb:
            self._cha[rb] = ra

    def nhom(self) -> dict[str, list[str]]:
        ra: dict[str, list[str]] = {}
        for x in self._cha:
            ra.setdefault(self.tim(x), []).append(x)
        return ra


# =========================================================================== đọc cây
@dataclass(slots=True)
class Cay:
    """Ảnh của cây trong bộ nhớ — đọc MỘT lần rồi tính nhiều lần.

    Vì sao không truy vấn kho từng bước: `flatten` và sáu bất biến đi lại trên cây rất
    nhiều lần, và mỗi lần chạm SQLite là một lần có thể thấy trạng thái khác (kho dùng
    chung giữa các luồng). Một ảnh nhất quán làm mọi phép kiểm nói về **cùng một cây**.
    """

    nut: dict[str, dict[str, Any]] = field(default_factory=dict)      # node_id → nút
    con: dict[str, list[str]] = field(default_factory=dict)           # cha → [con]
    port: dict[str, dict[str, Any]] = field(default_factory=dict)     # port_id → port
    port_cua: dict[str, list[str]] = field(default_factory=dict)      # module_id → [port_id]
    noi: dict[str, list[str]] = field(default_factory=dict)           # net_id → [port_id]
    noi_port: dict[str, list[str]] = field(default_factory=dict)      # port_id → [net_id]
    goc: str | None = None

    @staticmethod
    def doc(store: Any) -> "Cay":
        c = Cay()
        for n in store.ckm_cac_nut(limit=20000):
            c.nut[n["node_id"]] = n
            if n.get("parent_id"):
                c.con.setdefault(n["parent_id"], []).append(n["node_id"])
            if n.get("kind") == "board" and c.goc is None:
                c.goc = n["node_id"]
        for k in c.con:
            c.con[k].sort()
        for p in store.ckm_cac_port():
            c.port[p["port_id"]] = p
            c.port_cua.setdefault(p["module_id"], []).append(p["port_id"])
        for k in c.port_cua:
            c.port_cua[k].sort()
        for x in store.ckm_cac_noi():
            c.noi.setdefault(x["net_id"], []).append(x["port_id"])
            c.noi_port.setdefault(x["port_id"], []).append(x["net_id"])
        return c

    # ------------------------------------------------------------------ đi lại
    def la_khoi(self, nid: str) -> bool:
        return (self.nut.get(nid, {}).get("kind") or "") in KIND_KHOI

    def net_cua(self, module_id: str) -> list[str]:
        """Net thuộc phạm vi một khối."""
        return [x for x in self.con.get(module_id, [])
                if self.nut[x]["loai"] == "net"]

    def con_truc_tiep(self, module_id: str) -> list[str]:
        """Mọi nút con TRỰC TIẾP — khối, khối con, VÀ lá. Đây là tập mà một net trong khối
        này được phép chạm Port của (§2.2 mục 1)."""
        return [x for x in self.con.get(module_id, [])
                if (self.nut[x].get("kind") or "") in KIND]

    def khoi_con(self, module_id: str) -> list[str]:
        """Chỉ KHỐI con, không tính lá.

        Tách khỏi `con_truc_tiep` sau khi một ca đo đếm sai: `len(khoi_con(gốc)) == 2` trong
        khi gốc có hai khối và một lá (U2 — linh kiện chỉ netlist biết, chưa khối nào nhận).
        Một hàm tên "khối con" mà trả về cả lá thì mọi phép đếm dùng nó đều lệch, và lệch
        âm thầm.
        """
        return [x for x in self.con.get(module_id, [])
                if (self.nut[x].get("kind") or "") in KIND_KHOI]

    def cha(self, nid: str) -> str | None:
        return self.nut.get(nid, {}).get("parent_id")

    def sau_nhat(self) -> tuple[int, str]:
        sau, ai = 0, ""
        for nid, n in self.nut.items():
            if not n.get("path") or (n.get("kind") or "") not in KIND:
                continue
            d = do_sau(n["path"])
            if d > sau:
                sau, ai = d, n["path"]
        return sau, ai


# =========================================================================== flatten §3
def flatten(cay: Cay) -> dict[str, list[str]]:
    """`flatten(cây)` → `{tên net: [ref.pin đã sắp]}`. HIER-04.

    Đây là hàm nối mô hình mới với **mọi tool phẳng đã có**: `eda.bom_check`,
    `doi_chieu_bom_netlist`, và sau này ERC/BOM/sim. Netlist phẳng không mất đi, nó chỉ
    thôi làm dữ liệu gốc.

    Thuật toán theo §3: hợp nhất net qua Port, rồi mỗi nhóm lấy tên của net ở **cấp cao
    nhất** — vì đó là tên người ở ngoài gọi nó, và cũng là tên KiCad sẽ ghi.
    """
    hn = HopNhat()
    chan_cua_net: dict[str, set[str]] = {}

    for nid, n in cay.nut.items():
        if n["loai"] != "net":
            continue
        hn.tim(nid)          # net chưa nối gì vẫn phải có mặt, để nó không im lặng biến mất
        for pid in cay.noi.get(nid, []):
            p = cay.port.get(pid)
            if p is None:
                continue
            if cay.nut.get(p["module_id"], {}).get("kind") == "leaf":
                # Port của LÁ: đây là chỗ net gặp đồng — một chân thật.
                la = cay.nut[p["module_id"]]
                ref = la["canonical"].get("ref") or la["ten"]
                chan_cua_net.setdefault(nid, set()).add(f"{ref}.{p.get('chan') or p['ten']}")
                continue
            # Port của khối: §3 tách hai trường hợp — Port "lên cha" của chính khối sở hữu
            # net, và Port của một khối con. Cả hai quy về CÙNG một phép: net này ≡ mọi net
            # khác nối vào cùng Port đó. Viết một nhánh vì hai nhánh giống nhau chỉ tạo ra
            # một chỗ để chúng lệch nhau về sau.
            for khac in cay.noi_port.get(pid, []):
                if khac != nid:
                    hn.hop(nid, khac)

    ra: dict[str, list[str]] = {}
    for nhom in hn.nhom().values():
        ten = _ten_cap_cao_nhat(cay, nhom)
        chan: set[str] = set()
        for nid in nhom:
            chan |= chan_cua_net.get(nid, set())
        if ten in ra:
            # Hai net KHÁC NHAU trùng tên ở hai khối khác nhau (mỗi khối có một "VDD" cục
            # bộ là chuyện thường). Nếu để đè, netlist phẳng mất một net và không ai biết.
            # Tách bằng đường đầy đủ — dài hơn, nhưng đúng.
            for nid in sorted(nhom):
                if cay.nut.get(nid, {}).get("path"):
                    ten = cay.nut[nid]["path"]
                    break
            else:
                ten = f"{ten}#{sorted(nhom)[0]}"
        ra[ten] = sorted(chan, key=_khoa_chan)
    return ra


def _ten_cap_cao_nhat(cay: Cay, nhom: Iterable[str]) -> str:
    """Tên net của nhóm = net nông nhất; bằng nhau thì theo thứ tự chữ (xác định)."""
    tot: tuple[int, str] | None = None
    for nid in nhom:
        n = cay.nut.get(nid)
        if n is None:
            continue
        d = do_sau(n.get("path") or "")
        khoa = (d, n["ten"])
        if tot is None or khoa < tot:
            tot = khoa
    return tot[1] if tot else "?"


def _khoa_chan(s: str) -> tuple[str, int, str]:
    """Sắp `U1.2` trước `U1.10` — so số bằng SỐ. Một bảng netlist sắp theo chữ làm người
    đọc phải quét hai lần."""
    ref, _, so = s.partition(".")
    return (ref, int(so) if so.isdigit() else 10**9, so)


# =========================================================================== bất biến §3
# Mã lỗi: HIER-45 đánh số E8001–E8006, nhưng E8002…E8008 đã chạy trong mã với nghĩa khác
# (xem EIDE-GAP-44 §2c.3 và quyết định 26/09: mở họ mới). Nên bất biến cây là E9001–E9006.
E_CHU_TRINH = "E9001"
E_XUYEN_CAP = "E9002"
E_PORT_LEN_CHA = "E9003"
E_PORT_LA = "E9004"
E_BUS_LECH = "E9005"
E_DONG_GOI = "E9006"


@dataclass(slots=True)
class ViPham:
    ma: str
    vi: str
    o_dau: str = ""
    goi_y: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"ma": self.ma, "vi": self.vi, "o_dau": self.o_dau, "goi_y": self.goi_y}


def kiem_bat_bien(cay: Cay, *, chan_theo_fact: dict[str, set[str]] | None = None
                  ) -> list[ViPham]:
    """Sáu bất biến của §3, trừ E9006 (cần bản trước — xem `kiem_dong_goi`)."""
    ra: list[ViPham] = []
    ra += _kiem_chu_trinh(cay)
    ra += _kiem_pham_vi(cay)
    ra += _kiem_port_len_cha(cay)
    ra += _kiem_port_la(cay, chan_theo_fact or {})
    ra += _kiem_bus(cay)
    return ra


def _kiem_chu_trinh(cay: Cay) -> list[ViPham]:
    """E9001 — cây không có chu trình; mỗi nút đúng một cha (trừ gốc)."""
    ra: list[ViPham] = []
    for nid, n in cay.nut.items():
        if (n.get("kind") or "") not in KIND:
            continue
        thay: set[str] = set()
        cur: str | None = nid
        while cur:
            if cur in thay:
                ra.append(ViPham(
                    E_CHU_TRINH, f"Đường lên cha của {nid} đi vòng lại chính nó.",
                    nid, "Một khối không thể nằm trong chính nó. Đặt lại cha cho đúng."))
                break
            thay.add(cur)
            cur = cay.cha(cur)
    goc = [nid for nid, n in cay.nut.items()
           if (n.get("kind") or "") in KIND and not n.get("parent_id")]
    if len(goc) > 1:
        ra.append(ViPham(
            E_CHU_TRINH, f"Có {len(goc)} nút không cha: {', '.join(sorted(goc))}. "
                         "Một mạch chỉ có một gốc.",
            "", "Đặt các nút kia làm con của gốc (kind=board)."))
    return ra


def _kiem_pham_vi(cay: Cay) -> list[ViPham]:
    """E9002 — net chỉ chạm Port của con TRỰC TIẾP, hoặc Port của chính khối sở hữu nó.

    Đây là bất biến đắt giá nhất của cả mô hình: nó là thứ biến "đóng gói" từ một lời hứa
    thành một luật. Không có nó, một net ở gốc có thể chạm thẳng chân một con chip nằm sâu
    ba tầng, và mọi lời nói về biên khối trở thành trang trí.
    """
    ra: list[ViPham] = []
    for nid, n in cay.nut.items():
        if n["loai"] != "net":
            continue
        chu = cay.cha(nid)
        if chu is None:
            continue
        con_tt = set(cay.con_truc_tiep(chu))
        for pid in cay.noi.get(nid, []):
            p = cay.port.get(pid)
            if p is None:
                ra.append(ViPham(E_XUYEN_CAP, f"Net {n['ten']} nối tới Port {pid} không "
                                              "tồn tại.", nid))
                continue
            m = p["module_id"]
            if m == chu or m in con_tt:
                continue
            duong_m = cay.nut.get(m, {}).get("path") or m
            ra.append(ViPham(
                E_XUYEN_CAP,
                f"Net {n['ten']} (trong {cay.nut.get(chu, {}).get('path') or chu}) nối tới "
                f"Port của {duong_m} — không phải con trực tiếp. Dây không đi xuyên cấp.",
                nid,
                "Khai một Port ở biên khối trung gian rồi nối qua Port đó. Biên khối tồn "
                "tại để người đọc khối biết nó giao tiếp bằng gì."))
    return ra


def _kiem_port_len_cha(cay: Cay) -> list[ViPham]:
    """E9003 — Port "lên cha" của khối X: đúng một net trong X, đúng một net trong cha(X)."""
    ra: list[ViPham] = []
    for pid, p in cay.port.items():
        m = p["module_id"]
        if cay.nut.get(m, {}).get("kind") == "leaf":
            continue
        nets = cay.noi_port.get(pid, [])
        trong, ngoai = [], []
        for nid in nets:
            chu = cay.cha(nid)
            if chu == m:
                trong.append(nid)
            elif chu == cay.cha(m):
                ngoai.append(nid)
            else:
                ra.append(ViPham(
                    E_PORT_LEN_CHA,
                    f"Port {p['ten']} của {cay.nut.get(m, {}).get('path') or m} bị nối bởi "
                    f"net {cay.nut.get(nid, {}).get('ten')} không thuộc khối này cũng không "
                    "thuộc cha nó.", pid))
        for ds, cho in ((trong, "bên trong khối"), (ngoai, "ở khối cha")):
            if len(ds) > 1:
                ra.append(ViPham(
                    E_PORT_LEN_CHA,
                    f"Port {p['ten']} của {cay.nut.get(m, {}).get('path') or m} bị "
                    f"{len(ds)} net {cho} nối vào: "
                    + ", ".join(sorted(cay.nut[x]["ten"] for x in ds))
                    + ". Một Port là một điểm, không phải một bó.",
                    pid, "Gộp các net đó, hoặc khai thêm Port."))
    return ra


def _kiem_port_la(cay: Cay, chan_theo_fact: dict[str, set[str]]) -> list[ViPham]:
    """E9004 — Port của lá = đúng tập chân trong Fact pinout: không thừa, không thiếu.

    "Không thừa" là chiều quan trọng: một Port thừa nghĩa là sơ đồ sẽ vẽ một chân **chip
    không có**. Đó chính là N1 bị vi phạm ở chỗ khó thấy nhất.
    """
    ra: list[ViPham] = []
    for nid, n in cay.nut.items():
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        mong = chan_theo_fact.get(nid) or chan_theo_fact.get(ref)
        if mong is None:
            continue          # không có Fact để so ⇒ không kết luận (N6)
        co = {(cay.port[p].get("chan") or cay.port[p]["ten"])
              for p in cay.port_cua.get(nid, [])}
        thieu, thua = sorted(mong - co, key=_khoa_so), sorted(co - mong, key=_khoa_so)
        if thieu:
            ra.append(ViPham(
                E_PORT_LA, f"Lá {ref} thiếu Port cho chân: {', '.join(thieu)}.", nid,
                "Sinh lại Port của lá từ Fact pinout."))
        if thua:
            ra.append(ViPham(
                E_PORT_LA,
                f"Lá {ref} có Port cho chân {', '.join(thua)} mà bảng chân KHÔNG có. "
                "Sơ đồ sẽ vẽ một chân chip không tồn tại.", nid,
                "Bỏ các Port đó, hoặc nạp bảng chân đúng phiên bản chip."))
    return ra


def _khoa_so(s: str) -> tuple[int, str]:
    return (int(s), "") if str(s).isdigit() else (10**9, str(s))


def _kiem_bus(cay: Cay) -> list[ViPham]:
    """E9005 — hai đầu một bus phải khớp tên và số lượng member."""
    ra: list[ViPham] = []
    for nid, n in cay.nut.items():
        if n["loai"] != "net":
            continue
        bus = [cay.port[p] for p in cay.noi.get(nid, [])
               if p in cay.port and cay.port[p]["loai"] == "bus"]
        if len(bus) < 2:
            continue
        goc = [str(x) for x in (bus[0]["members"] or [])]
        for p in bus[1:]:
            mem = [str(x) for x in (p["members"] or [])]
            if sorted(mem) != sorted(goc):
                ra.append(ViPham(
                    E_BUS_LECH,
                    f"Bus trên net {n['ten']}: Port {bus[0]['ten']} có "
                    f"[{', '.join(goc)}] còn {p['ten']} có [{', '.join(mem)}].",
                    nid, "Sửa members cho khớp, hoặc tách thành từng net thành viên."))
    return ra


def bien_khoi(cay: Cay, module_id: str) -> dict[str, str]:
    """Hợp đồng của một khối như bên ngoài thấy: `{tên Port: tên net ở cha}`.

    Port không nối gì ở ngoài thì giá trị là `""` — một Port bỏ trống vẫn là một phần của
    hợp đồng, và việc nó được nối hay không là thông tin bên ngoài cần.
    """
    cha = cay.cha(module_id)
    ra: dict[str, str] = {}
    for pid in cay.port_cua.get(module_id, []):
        p = cay.port[pid]
        ngoai = [cay.nut[n]["ten"] for n in cay.noi_port.get(pid, [])
                 if cay.cha(n) == cha and n in cay.nut]
        ra[p["ten"]] = sorted(ngoai)[0] if ngoai else ""
    return ra


def kiem_dong_goi(truoc: dict[str, list[str]], sau: dict[str, list[str]], *,
                  trong_khoi: set[str],
                  bien_truoc: dict[str, str] | None = None,
                  bien_sau: dict[str, str] | None = None) -> list[ViPham]:
    """E9006 — thay đổi "nội bộ" một khối không được thấy được từ ngoài khối.

    Phép kiểm chứng của quy tắc đóng gói (§2.2 mục 2, §3 dòng cuối bảng bất biến). Nó có
    **hai vế**, và vế thứ hai là thứ ca đo dạy cho tôi:

    **(a) chân ngoài khối không đổi.** So `flatten` trước/sau, bỏ qua chân của linh kiện
    *bên trong* khối — vì thêm một điện trở nối vào net cục bộ là việc nội bộ hợp lệ, dù
    nó có làm tập chân của net đó dài ra.

    **(b) biên khối không đổi.** Chỉ vế (a) thì phép kiểm mù đúng chỗ nguy hiểm nhất: gỡ
    Port VDD của khối MCU khỏi net 3V3 làm khối **mất nguồn**, nhưng vì `U1.7` là chân bên
    trong nên vế (a) lọc nó đi và kết luận "không có gì đổi". Vế (b) so `{Port: net ở cha}`
    và bắt được ngay: một Port thôi được nối là một hợp đồng bị xé, không phải sửa nội bộ.

    `trong_khoi` là tập ref linh kiện thuộc khối đã sửa, kể cả khối con.
    """
    ra: list[ViPham] = []

    def ngoai(d: dict[str, list[str]]) -> dict[str, set[str]]:
        kq = {}
        for ten, chan in d.items():
            con = {c for c in chan if c.split(".", 1)[0] not in trong_khoi}
            if con:
                kq[ten] = con
        return kq

    a, b = ngoai(truoc), ngoai(sau)
    for ten in sorted(set(a) | set(b)):
        if a.get(ten, set()) != b.get(ten, set()):
            mat = sorted(a.get(ten, set()) - b.get(ten, set()))
            them = sorted(b.get(ten, set()) - a.get(ten, set()))
            ra.append(ViPham(
                E_DONG_GOI,
                f"Sửa nội bộ khối nhưng net {ten} ở ngoài khối đã đổi"
                + (f" — mất {', '.join(mat)}" if mat else "")
                + (f" — thêm {', '.join(them)}" if them else "") + ".",
                ten,
                "Thay đổi này chạm tới biên khối, nên nó KHÔNG phải sửa nội bộ: nó đổi "
                "hợp đồng. Khai lại Port và để STALE lan ra ngoài theo §6."))

    if bien_truoc is not None and bien_sau is not None and bien_truoc != bien_sau:
        for ten in sorted(set(bien_truoc) | set(bien_sau)):
            cu, moi = bien_truoc.get(ten), bien_sau.get(ten)
            if cu == moi:
                continue
            if moi is None:
                vi = f"Port {ten} biến mất khỏi biên khối (trước nối {cu or 'chưa nối'})."
            elif cu is None:
                vi = f"Biên khối có Port MỚI {ten} (nối {moi or 'chưa nối'})."
            else:
                vi = (f"Port {ten} đổi net ở ngoài: {cu or 'chưa nối'} → "
                      f"{moi or 'chưa nối'}.")
            ra.append(ViPham(
                E_DONG_GOI, "Đổi hợp đồng, không phải sửa nội bộ. " + vi, ten,
                "Đổi Port thì STALE phải lan tới cha và các khối anh em nối vào net đó "
                "(§6). Đừng gọi đây là thay đổi nội bộ."))
    return ra


def canh_bao_do_sau(cay: Cay) -> str:
    """§2.1: depth > 4 thì CẢNH BÁO, không cấm. Một giới hạn cứng ở đây sẽ chặn những mạch
    thật sự có năm tầng, và người dùng sẽ học cách dựng cây méo để lách."""
    sau, ai = cay.sau_nhat()
    if sau <= SAU_KHUYEN_NGHI:
        return ""
    return (f"Cây sâu {sau} cấp ({ai}), quá mức khuyến nghị {SAU_KHUYEN_NGHI}. Vẫn hợp lệ, "
            "nhưng bố cục nên chuyển sang sheet phân cấp và giao diện sẽ khó đọc hơn.")


# =========================================================================== dựng cây §2.3
# Đây là phần di cư của §2.3, và nó KHÔNG phải một lệnh chạy một lần: nó chạy mỗi lần
# `chieu()` chạy, vì cây cũng là hình chiếu của hiện vật như phần còn lại của bản đồ.
#
# Hệ quả đáng giá: một dự án làm từ trước HIER-45 mở lên là có cây ngay, không cần ai bấm
# "di cư", và không có trạng thái "đã di cư chưa" để sai. Hệ quả phải trả: hàm này phải
# dựng được cây từ dữ liệu phẳng **mọi lần**, nên nó phải xác định.
#
# Quy tắc di cư (§2.3 phần comment SQL):
#   khối cũ  → kind=block, cha = board
#   linh kiện → kind=leaf, cha = khối nào KHAI ref đó trong `linh_kien`, không thì board
#   net cũ   → phạm vi board
#   Port     → lá: từ chân đã biết · khối: từ `tin_hieu_vao/ra` cũ · và Port "LÊN CHA"
#              tự sinh cho mỗi net board chạm chân một lá nằm trong khối con
GOC = "module:/board"
TEN_GOC = "Bo mạch"


def _ten_sach(s: str) -> str:
    return (s or "").strip().strip("/").replace(" ", "_") or "?"


def dung_cay(store: Any) -> dict[str, int]:
    """Đặt mọi nút vào cây. Trả về vài con số để người gọi ghi nhật ký."""
    goc = _dat_goc(store)
    khoi = _dat_khoi(store, goc)
    la, thuoc = _dat_la(store, goc, khoi)
    _port_cua_la(store, la)
    _port_cua_khoi(store, khoi)
    net = _dat_net(store, goc, khoi)
    _noi_port_khai(store, khoi, net)
    len_cha = _noi_net(store, goc, khoi, la, thuoc, net)
    return {"khoi": len(khoi), "la": len(la), "net": len(net), "port_len_cha": len_cha}


def _dat_goc(store: Any) -> str:
    g = store.ckm_goc()
    if g:
        return g["node_id"]
    store.ckm_dat_nut(node_id=GOC, loai="module", ten=TEN_GOC,
                      canonical={"ma": "board", "ten": TEN_GOC,
                                 "muc_dich": "gốc của cây khối"})
    store.ckm_dat_cay(GOC, parent_id=None, kind="board", path="/board")
    return GOC


def _dat_khoi(store: Any, goc: str) -> dict[str, dict[str, Any]]:
    """Đặt khối vào cây theo `cha` khai trong hiện vật; không khai thì con của gốc.

    Đi theo THỨ TỰ TOPO (cha trước con) vì `path` của con dựng từ `path` của cha. Khối
    khai một cha không tồn tại, hoặc một vòng cha–con, thì rơi về gốc và vi phạm sẽ được
    E9001 nói ra — không im lặng bỏ khối đó khỏi cây.
    """
    tat = [n for n in store.ckm_cac_nut(loai="module") if n["node_id"] != goc]
    theo_ma = {(n["canonical"].get("ma") or n["ten"]): n for n in tat}

    xong: dict[str, dict[str, Any]] = {}
    con_lai = list(tat)
    while con_lai:
        tien = False
        for n in list(con_lai):
            ma = n["canonical"].get("ma") or n["ten"]
            ma_cha = (n["canonical"].get("cha") or "").strip()
            nut_cha = theo_ma.get(ma_cha) if ma_cha else None
            if ma_cha and nut_cha is None:
                cha_id, cha_path = goc, "/board"      # cha lạ → về gốc, E9001 sẽ không nổ
            elif nut_cha is None:
                cha_id, cha_path = goc, "/board"
            elif nut_cha["node_id"] in xong:
                cha_id = nut_cha["node_id"]
                cha_path = xong[cha_id].get("path") or "/board"
            else:
                continue                               # chờ cha được đặt trước
            store.ckm_dat_cay(n["node_id"], parent_id=cha_id,
                              kind=n["canonical"].get("kind") or "block",
                              path=duong(cha_path, _ten_sach(ma)))
            xong[n["node_id"]] = store.ckm_nut(n["node_id"])
            con_lai.remove(n)
            tien = True
        if not tien:
            # Vòng trong khai báo cha: đặt phần còn lại ở gốc để cây vẫn dựng được, rồi
            # E9001 nói ra. Bỏ chúng đi thì người mất luôn đường thấy mình khai sai ở đâu.
            for n in con_lai:
                ma = n["canonical"].get("ma") or n["ten"]
                store.ckm_dat_cay(n["node_id"], parent_id=goc,
                                  kind=n["canonical"].get("kind") or "block",
                                  path=duong("/board", _ten_sach(ma)))
                xong[n["node_id"]] = store.ckm_nut(n["node_id"])
            break
    return xong


def _dat_la(store: Any, goc: str, khoi: dict[str, dict[str, Any]]
            ) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Chip và linh kiện → `kind=leaf`, cha là khối KHAI ref đó.

    Trả `({node_id: nút}, {ref: node_id khối chứa})`. Cái thứ hai là thứ `_noi_net` cần để
    biết một chân nằm sâu trong khối nào — tức để biết có phải sinh Port "lên cha" không.
    """
    # ref → khối, theo `linh_kien` của từng khối. Một ref khai ở hai khối là lỗi người
    # dùng; lấy khối có path nhỏ nhất để kết quả XÁC ĐỊNH, và không im lặng: xem `canh_bao`.
    chu: dict[str, str] = {}
    for nid, n in sorted(khoi.items()):
        for lk in n["canonical"].get("linh_kien") or []:
            chu.setdefault(str(lk).strip(), nid)

    def dat(nid: str, ref: str) -> None:
        cha = chu.get(ref, goc)
        cha_path = (store.ckm_nut(cha) or {}).get("path") or "/board"
        store.ckm_dat_cay(nid, parent_id=cha, kind="leaf",
                          path=duong(cha_path, _ten_sach(ref)))
        la[nid] = store.ckm_nut(nid)

    la: dict[str, dict[str, Any]] = {}
    da_co: set[str] = set()
    for loai in ("chip", "linh_kien"):
        for n in store.ckm_cac_nut(loai=loai):
            ref = n["canonical"].get("ref") or n["ten"]
            da_co.add(ref)
            dat(n["node_id"], ref)

    # Ref chỉ được NETLIST nhắc tới — chưa có datasheet, nên bước CKM không tạo nút linh
    # kiện nào cho nó. Nó vẫn là một linh kiện thật trên bo, và nếu không thành lá thì
    # `_noi_net` bỏ rơi chân của nó và `flatten` trả về một mạch **thiếu chân**: mạch trông
    # như đã nối đủ trong khi thực tế thiếu. Đo trên ca HIER01 — xem DEV log.
    for p in store.ckm_cac_nut(loai="pin"):
        ref = p["canonical"].get("ref") or p["node_id"].removeprefix("pin:").split(".")[0]
        if not ref or ref in da_co:
            continue
        da_co.add(ref)
        nid = f"linh_kien:{ref}"
        if store.ckm_nut(nid) is None:
            store.ckm_dat_nut(node_id=nid, loai="linh_kien", ten=ref,
                              canonical={"ref": ref, "chua_co_bang_chan": True},
                              nguon={"netlist": "chỉ biết qua netlist, chưa có datasheet"})
        dat(nid, ref)
    return la, chu


def _port_cua_la(store: Any, la: dict[str, dict[str, Any]]) -> None:
    """§2.1: "Port của lá = pin theo Fact pinout". Một Port cho mỗi chân đã biết.

    Chân của lá là các nút `pin:<ref>.<so>` mà bước CKM đã dựng từ Fact — nên Port của lá
    **thừa hưởng nguyên** kỷ luật "không bịa chân": không có Fact thì không có nút chân,
    không có nút chân thì không có Port, và E9004 sẽ nói ra nếu hai bên lệch.
    """
    for nid, n in la.items():
        ref = n["canonical"].get("ref") or n["ten"]
        for p in store.ckm_cac_nut(loai="pin", tien_to=f"pin:{ref}."):
            so = p["node_id"].split(".", 1)[-1]
            store.ckm_dat_port(port_id=ma_port(n.get("path") or ref, so),
                               module_id=nid, ten=so,
                               huong=_huong_theo_ten(p["canonical"].get("ten") or so),
                               fact_refs=[(p.get("nguon") or {}).get("fact_id", "")],
                               chan=so)


_TEN_NGUON = ("VCC", "VDD", "VIN", "VBAT", "AVCC", "VDDA")
_TEN_DAT = ("GND", "VSS", "AGND", "DGND")


def _huong_theo_ten(ten: str) -> str:
    """Hướng suy từ tên chân — chỉ cho chân NGUỒN/ĐẤT, chỗ tên là quy ước chắc chắn.

    Không đoán hướng tín hiệu: một chân `PC4` có thể vào, ra, hay hai chiều tuỳ chức năng
    được gán, và đoán sai hướng làm ERC sau này nói một câu sai có vẻ chắc chắn. `passive`
    là câu trả lời trung thực khi chưa biết.
    """
    t = (ten or "").strip().upper()
    if t.startswith(_TEN_NGUON):
        return "power_in"
    if t.startswith(_TEN_DAT):
        return "power_in"
    return "passive"


def _port_cua_khoi(store: Any, khoi: dict[str, dict[str, Any]]) -> None:
    """Port của khối: KHAI BÁO trước, di cư sau.

    Khối đã khai Port bằng `ckm.port_set` thì dùng đúng thứ đã khai — đó là hợp đồng thật,
    có hướng người chọn và ràng buộc có nguồn.

    Khối chưa khai gì thì suy tạm từ `tin_hieu_vao/ra` của mô hình phẳng. Đây là chỗ duy
    nhất hai trường đó còn giá trị sau HIER-45: một **phỏng đoán** đủ tốt để không phải
    khai lại tay cả dự án cũ. Nó được đánh dấu `rang_buoc.di_cu` để không ai nhầm nó với
    một hợp đồng người đã đọc và gật.
    """
    for nid, n in khoi.items():
        c = n["canonical"]
        path = n.get("path") or nid
        khai = c.get("port") or []
        if khai:
            for p in khai:
                t = _ten_sach(p.get("ten", ""))
                if not t or t == "?":
                    continue
                store.ckm_dat_port(port_id=ma_port(path, t), module_id=nid, ten=t,
                                   huong=p.get("huong") or "passive",
                                   loai=p.get("loai") or "single",
                                   members=list(p.get("members") or []),
                                   rang_buoc=dict(p.get("rang_buoc") or {}))
            continue
        for ten in c.get("tin_hieu_vao") or []:
            _port_di_cu(store, nid, path, ten, "in")
        for ten in c.get("tin_hieu_ra") or []:
            _port_di_cu(store, nid, path, ten, "out")
        if c.get("rail"):
            _port_di_cu(store, nid, path, c["rail"], "power_in")


def _port_di_cu(store: Any, module_id: str, path: str, ten: str, huong: str) -> None:
    t = _ten_sach(ten)
    if not t or t == "?":
        return
    co = {p["ten"] for p in store.ckm_cac_port(module_id=module_id)}
    if t in co:
        return          # đã có (ví dụ vừa là rail vừa là tín hiệu vào) — giữ cái đầu
    store.ckm_dat_port(port_id=ma_port(path, t), module_id=module_id, ten=t,
                       huong=huong,
                       rang_buoc={"di_cu": "hướng suy từ tin_hieu_vao/ra của mô hình "
                                           "phẳng — phỏng đoán, hãy xác nhận"})


def _dat_net(store: Any, goc: str, khoi: dict[str, dict[str, Any]]
             ) -> dict[str, dict[str, Any]]:
    """Net vào phạm vi khối đã khai; không khai thì phạm vi gốc (§2.3 "net cũ: scope = board")."""
    theo_ma = {(n["canonical"].get("ma") or n["ten"]): nid for nid, n in khoi.items()}
    ra: dict[str, dict[str, Any]] = {}
    for n in store.ckm_cac_nut(loai="net"):
        if n.get("parent_id"):
            ra[n["node_id"]] = n
            continue
        ma_khoi = (n["canonical"].get("trong_khoi") or "").strip()
        chu = theo_ma.get(ma_khoi, goc) if ma_khoi else goc
        chu_path = (store.ckm_nut(chu) or {}).get("path") or "/board"
        store.ckm_dat_cay(n["node_id"], parent_id=chu, kind=None,
                          path=f"{chu_path}.{_ten_sach(n['ten'])}")
        ra[n["node_id"]] = store.ckm_nut(n["node_id"])
    return ra


def _noi_port_khai(store: Any, khoi: dict[str, dict[str, Any]],
                   net: dict[str, dict[str, Any]]) -> None:
    """Nối net tới Port khối theo `noi_port` người/tác tử khai.

    Chạy TRƯỚC `_noi_net`: nối tay là ý chí, di cư chỉ là suy đoán, và `_noi_net` bỏ qua
    net nào đã có kết nối.
    """
    theo_ma = {(n["canonical"].get("ma") or n["ten"]): nid for nid, n in khoi.items()}
    for nid, n in net.items():
        for ma_khoi, ten_port in (n["canonical"].get("noi_port") or []):
            m = theo_ma.get(str(ma_khoi).strip())
            if m is None:
                continue
            path = (store.ckm_nut(m) or {}).get("path") or m
            pid = ma_port(path, _ten_sach(str(ten_port)))
            if store.ckm_cac_port(port_id=pid):
                store.ckm_noi(net_id=nid, port_id=pid)


def _noi_net(store: Any, goc: str, khoi: dict[str, dict[str, Any]],
             la: dict[str, dict[str, Any]], thuoc: dict[str, str],
             net: dict[str, dict[str, Any]]) -> int:
    """Kết nối cũ (`net ↔ ref.pin`) → `connection(net, port)`, sinh Port "lên cha" khi cần.

    Đây là phần khó nhất của di cư, và nó tồn tại vì một lý do vật lý: net cũ nằm ở gốc,
    còn chân nằm trong lá **bên trong** một khối. Nối thẳng là vi phạm E9002 — chính bất
    biến ta vừa dựng. Nên phải sinh đúng thứ tài liệu nói: một Port ở biên khối, cộng một
    net cục bộ bên trong khối, và `flatten` hợp nhất chúng lại thành một net điện.

    Nhờ vậy `flatten(cây sau di cư)` bằng netlist cũ — HIER01 đòi 100 %.
    """
    la_theo_ref = {(n["canonical"].get("ref") or n["ten"]): nid for nid, n in la.items()}
    so_len_cha = 0

    for nid, n in net.items():
        if store.ckm_cac_noi(net_id=nid):
            continue          # net này đã nối bằng Port rồi (cây dựng thật, không di cư)
        ten_net = _ten_sach(n["ten"])
        for canh in store.ckm_cac_canh(loai="NOI", tu=nid):
            ref, _, so = canh["den"].removeprefix("pin:").partition(".")
            nid_la = la_theo_ref.get(ref)
            if nid_la is None or not so:
                continue
            port_la = _tim_port(store, nid_la, so)
            if port_la is None:
                continue
            khoi_chua = store.ckm_nut(nid_la).get("parent_id")
            if khoi_chua == goc or khoi_chua is None:
                # Lá nằm ngay ở gốc: net gốc chạm Port lá là hợp lệ (con trực tiếp).
                store.ckm_noi(net_id=nid, port_id=port_la)
                continue
            # Lá nằm trong một khối → phải đi qua biên khối đó.
            kpath = store.ckm_nut(khoi_chua).get("path") or khoi_chua
            pid = ma_port(kpath, ten_net)
            if not store.ckm_cac_port(port_id=pid):
                store.ckm_dat_port(
                    port_id=pid, module_id=khoi_chua, ten=ten_net, huong="passive",
                    rang_buoc={"di_cu": "Port sinh khi di cư mô hình phẳng: net ở gốc "
                                        "chạm chân một lá bên trong khối này"})
                so_len_cha += 1
            trong = f"net:{kpath}.{ten_net}"
            if store.ckm_nut(trong) is None:
                store.ckm_dat_nut(node_id=trong, loai="net", ten=n["ten"],
                                  canonical={"ten": n["ten"], "di_cu": True},
                                  tier=n.get("tier"))
                store.ckm_dat_cay(trong, parent_id=khoi_chua, kind=None,
                                  path=f"{kpath}.{ten_net}")
            store.ckm_noi(net_id=nid, port_id=pid)
            store.ckm_noi(net_id=trong, port_id=pid)
            store.ckm_noi(net_id=trong, port_id=port_la)
    return so_len_cha


def _tim_port(store: Any, module_id: str, chan: str) -> str | None:
    for p in store.ckm_cac_port(module_id=module_id):
        if (p.get("chan") or p["ten"]) == chan:
            return p["port_id"]
    return None
