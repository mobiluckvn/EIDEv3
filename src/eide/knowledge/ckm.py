# -*- coding: utf-8 -*-
"""Bản đồ tri thức mạch (CKM) — EIDE-MDD-40 §C2. Bước CKM.

    "Thực thể: Chip (hộ chiếu ns.part@semver), Pin (số, tên, AF[], mức áp, dòng, kéo
     nội), Net (tên, loại, áp danh định), Module, Bus, Nguồn (rail), Ràng buộc, Tài
     liệu, Fact. Quan hệ: CÓ_CHÂN, NỐI, ĐƯỢC_GÁN (duy nhất), GỒM, THỰC_HIỆN, CẤP,
     ÁP_LÊN, SINH, THAY_THẾ."

Vì sao CKM phải có trước khi sinh được sơ đồ: EIDE-SCH-44 §4 mở đầu bước soạn bằng
"từ CKM đã có", và ba thứ nó đòi là module_graph ≥ 1, netlist nội bộ, Fact pinout
≥ NGƯỜI. Trước bước này cả ba chỉ có TÊN trong kho — `ARTEFACT_TYPES` liệt kê
`ckm`/`pinout`/`netlist`/`block_diagram` mà không công cụ nào ghi chúng. Sinh sơ đồ từ
một bản đồ rỗng thì mô hình phải bịa ra linh kiện và chân, tức là đúng thứ N1 cấm.

Ba quyết định của module này, và lý do đo được của từng cái:

**1. Chân không có trong Fact thì không gán được.** Không phải vì lịch sự với tài liệu,
mà vì hậu quả vật lý: gán SDA cho một chân chỉ có chức năng ADC thì mạch hàn xong sẽ
không bao giờ chạy, và không có bước nào sau đó phát hiện ra — biên dịch vẫn sạch, ERC
vẫn sạch. Chỗ duy nhất chặn được là lúc gán. Nên `kiem_chan()` đòi một Fact, và tầng
ĐỒNG (tri thức chung của mô hình) không tính.

**2. ĐƯỢC_GÁN duy nhất nằm trong chỉ mục SQLite, không nằm ở đây.** Xem `SCHEMA_CKM`.
Hàm ở đây chỉ dịch `IntegrityError` thành câu người đọc được.

**3. Mermaid do MÃ sinh, không do mô hình viết.** N3: hình chiếu của trạng thái dự án
phải xác định. Cùng một module_graph phải ra cùng một hình, mọi lần.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# --------------------------------------------------------------------------- từ vựng
# Danh sách đóng. Một loại lạ không được lặng lẽ vào đồ thị: nó sẽ hiện ra ở mọi bản
# kiểm kê, mọi hình vẽ, và không ai biết nó nghĩa là gì.
LOAI_NUT = ("chip", "pin", "net", "module", "bus", "rail", "rang_buoc", "tai_lieu",
            "fact", "chuc_nang", "linh_kien")
LOAI_CANH = ("CO_CHAN", "NOI", "DUOC_GAN", "GOM", "THUC_HIEN", "CAP", "AP_LEN",
             "SINH", "THAY_THE")

# Tầng dùng được để thiết kế. Giống `TANG_DUNG_DUOC` của bộ so sánh và cùng một lý do:
# ĐỒNG là phỏng đoán của mô hình, CẤU HÌNH là dự án đang đặt gì chứ không phải chip
# chịu được gì. Cả hai đều không nói được "chân 27 có I2C".
TANG_THIET_KE = ("VANG", "BAC", "NGUOI")

LOAI_NET = ("power", "ground", "signal", "bus", "clock", "analog")

_CHAN_HOP_LE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def ma_pin(ref: str, chan: str) -> str:
    """Chân định danh theo REF trên sơ đồ (U1.27), không theo tên chip.

    Đo trên ca `test_build_du_tien_de_thi_noi_du`: khi khoá theo tên chip, một chân vào
    bản đồ HAI lần — `pin:ATmega328P.27` do bảng chân, `pin:U1.27` do netlist — và bản đồ
    đếm 5 chân trên một chip có 3. Tệ hơn: hai con ATmega328P trên cùng một bo sẽ đè lên
    nhau, nên gán chân cho con này lại hiện ra ở con kia.

    Netlist nói bằng ref, datasheet nói bằng tên chip. Bo mạch có thể có nhiều con cùng
    loại nhưng không thể có hai U1 — nên REF là khoá, và tên chip là thuộc tính.
    """
    return f"pin:{ref}.{chan}"


def ma_net(ten: str) -> str:
    return f"net:{ten}"


def ma_module(ma: str) -> str:
    return f"module:{ma}"


# =========================================================================== chân & Fact
@dataclass(slots=True)
class ChanCKM:
    """Một chân như CKM biết về nó — luôn kèm chỗ nó đến từ đâu."""

    chan: str
    ten: str = ""
    af: list[str] = field(default_factory=list)
    muc_ap: str = ""
    tier: str = ""
    fact_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"chan": self.chan, "ten": self.ten, "af": list(self.af),
                "muc_ap": self.muc_ap, "tier": self.tier, "fact_id": self.fact_id}


def _tach_af(gt: Any) -> list[str]:
    """AF trong Fact có thể là "USART1_TX, TIM2_CH1" hoặc "AF7/AF1" — tách cả hai."""
    s = "" if gt is None else str(gt)
    return [x.strip() for x in re.split(r"[,;/|]", s) if x.strip()]


def chan_tu_fact(facts: list[dict[str, Any]], chip: str) -> dict[str, ChanCKM]:
    """Dựng danh sách chân từ bảng Fact. Mã đọc, mô hình không tham gia.

    Quy ước chủ thể của Fact chân: `pin:<chip>.<số>` — đã có trong lược đồ kho từ đầu
    (`"pin:U1.28"` trong comment của bảng facts). Khoá nào cũng nhận, nhưng chỉ ba khoá
    có nghĩa với việc gán: `ten`/`name`, `af`/`alt`, `muc_ap`/`voltage`.
    """
    ra: dict[str, ChanCKM] = {}
    tien_to = f"pin:{chip}."
    for f in facts:
        sub = str(f.get("subject", ""))
        if not sub.startswith(tien_to):
            continue
        so = sub[len(tien_to):].strip()
        if not so:
            continue
        c = ra.setdefault(so, ChanCKM(chan=so))
        khoa = str(f.get("key", "")).lower()
        gt = f.get("value")
        if khoa in ("ten", "name", "ten_chan", "pin_name"):
            c.ten = "" if gt is None else str(gt)
        elif khoa in ("af", "alt", "alt_func", "chuc_nang_thay_the", "functions"):
            c.af = _tach_af(gt)
        elif khoa in ("muc_ap", "voltage", "vio"):
            c.muc_ap = "" if gt is None else str(gt)
        # Tầng của chân = tầng ÍT TIN CẬY NHẤT trong các Fact nói về nó, và `fact_id` trỏ
        # vào chính cái Fact yếu đó — vì đó là thứ phải sửa để nâng chân lên.
        #
        # Một chân mà TÊN ở VÀNG còn AF ở ĐỒNG thì không phải chân VÀNG: thứ ta đang gán
        # là AF. Lấy tầng tin nhất ở đây sẽ biến một phỏng đoán của mô hình thành một con
        # số có nền vàng nhạt trên màn hình — đúng thứ N6 gọi là đậu sai.
        t = str(f.get("tier", "")).upper()
        if t and (not c.tier or thu_tu_tang(t) > thu_tu_tang(c.tier)):
            c.tier = t
            c.fact_id = str(f.get("fact_id", ""))
    return ra


def thu_tu_tang(tang: str) -> int:
    """Thứ tự tin cậy: số nhỏ = tin hơn. Tầng lạ xếp cuối, không nổ."""
    bang = {"VANG": 0, "BAC": 1, "NGUOI": 2, "CAUHINH": 8, "DONG": 9}
    return bang.get((tang or "").upper(), 7)


@dataclass(slots=True)
class KetQuaKiem:
    dat: bool
    ma_loi: str = ""
    vi: str = ""
    goi_y: str = ""
    chi_tiet: dict[str, Any] = field(default_factory=dict)


def kiem_chan(chan: str, co_san: dict[str, ChanCKM], *, chip: str) -> KetQuaKiem:
    """Chân này có thật không, và có tin được không (SCH-03 "không bịa chân").

    Ba câu trả lời khác nhau, và chúng KHÔNG được gộp thành một:
      - chưa có Fact chân nào cho chip  → chưa nạp bảng chân (E8002)
      - có bảng chân, chân này không có → chân này không tồn tại (E8003)
      - có nhưng tầng ĐỒNG             → mô hình đoán, không phải tài liệu (E8006)
    Gộp lại thành "không gán được" thì người đọc không biết phải làm gì tiếp.
    """
    if not _CHAN_HOP_LE.match(chan or ""):
        return KetQuaKiem(False, "E8003", f"Số chân {chan!r} không hợp lệ.",
                          "Dùng số hoặc tên chân như trong bảng chân của datasheet.")
    if not co_san:
        return KetQuaKiem(
            False, "E8002",
            f"Chưa có Fact chân nào cho {chip}, nên không kiểm được chân {chan} có thật hay không.",
            "Nạp bảng chân từ datasheet bằng fact.extract rồi fact.review; hoặc nếu "
            "người dùng đọc datasheet và nói cho bạn, ghi bằng fact.assert_human.")
    c = co_san.get(chan)
    if c is None:
        gan = sorted(co_san)[:12]
        return KetQuaKiem(
            False, "E8003",
            f"{chip} không có chân {chan} trong bảng chân đã nạp "
            f"({len(co_san)} chân: {', '.join(gan)}{'…' if len(co_san) > 12 else ''}).",
            "Đừng đoán số chân. Kiểm lại bảng chân bằng fact.query, hoặc hỏi người dùng.",
            {"chan_co": sorted(co_san)})
    if c.tier and c.tier.upper() not in TANG_THIET_KE:
        return KetQuaKiem(
            False, "E8006",
            f"Chân {chan} của {chip} chỉ có ở tầng {c.tier} — đó là phỏng đoán, "
            "không phải tài liệu. Tầng này không được vào bản đồ mạch.",
            "Nạp datasheet để lên VÀNG/BẠC, hoặc xin người dùng xác nhận con số "
            "(fact.assert_human → tầng NGƯỜI).", {"tier": c.tier})
    return KetQuaKiem(True, chi_tiet={"chan": c.to_dict()})


def kiem_af(chuc_nang: str, c: ChanCKM) -> KetQuaKiem:
    """Chức năng gán cho chân phải nằm trong AF của chân đó, KHI danh sách AF có.

    Không có danh sách AF thì không kết luận được gì — và "không kết luận được" phải
    hiện ra như thế, chứ không được lặng lẽ thành "đạt" (N6).
    """
    if not c.af:
        return KetQuaKiem(True, chi_tiet={"kiem_duoc": False,
                                          "vi": f"Chân {c.chan} chưa có danh sách AF "
                                                "trong Fact, nên không kiểm được chức "
                                                "năng có hợp lệ hay không."})
    can = chuc_nang.strip().lower()
    khop = [a for a in c.af if a.strip().lower() == can]
    if not khop:
        gan = [a for a in c.af if can in a.lower() or a.lower() in can]
        return KetQuaKiem(
            False, "E8007",
            f"Chân {c.chan} không làm được {chuc_nang}. AF của nó: {', '.join(c.af)}.",
            ("Có thể anh nhầm với " + ", ".join(gan) + "." if gan else
             "Chọn chân khác, hoặc kiểm lại bảng AF."),
            {"af": list(c.af), "gan_giong": gan})
    return KetQuaKiem(True, chi_tiet={"kiem_duoc": True, "af": khop[0]})


# =========================================================================== module_graph
@dataclass(slots=True)
class Module:
    """Một khối. `cha` và `kind` là phần HIER-45 thêm vào.

    Hai trường đó nằm trong HIỆN VẬT, không chỉ trong đồ thị — vì đồ thị là hình chiếu, và
    một cái cây chỉ tồn tại trong hình chiếu thì hoàn tác sẽ xoá nó mà không ai ghi lại.
    """

    ma: str
    ten: str
    muc_dich: str = ""
    linh_kien: list[str] = field(default_factory=list)
    tin_hieu_vao: list[str] = field(default_factory=list)
    tin_hieu_ra: list[str] = field(default_factory=list)
    rail: str = ""
    dap_ung_req: list[str] = field(default_factory=list)
    cha: str = ""                 # mã khối cha; rỗng = con của gốc
    kind: str = "block"           # block | subblock
    port: list[dict[str, Any]] = field(default_factory=list)   # hợp đồng của khối (§2.1)

    def to_dict(self) -> dict[str, Any]:
        return {"ma": self.ma, "ten": self.ten, "muc_dich": self.muc_dich,
                "linh_kien": list(self.linh_kien), "tin_hieu_vao": list(self.tin_hieu_vao),
                "tin_hieu_ra": list(self.tin_hieu_ra), "rail": self.rail,
                "dap_ung_req": list(self.dap_ung_req), "cha": self.cha, "kind": self.kind,
                "port": [dict(p) for p in self.port]}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Module":
        return Module(ma=d.get("ma", ""), ten=d.get("ten", ""),
                      muc_dich=d.get("muc_dich", ""),
                      linh_kien=list(d.get("linh_kien") or []),
                      tin_hieu_vao=list(d.get("tin_hieu_vao") or []),
                      tin_hieu_ra=list(d.get("tin_hieu_ra") or []),
                      rail=d.get("rail", ""),
                      dap_ung_req=list(d.get("dap_ung_req") or []),
                      cha=d.get("cha", ""), kind=d.get("kind") or "block",
                      port=[dict(x) for x in (d.get("port") or [])])


def canh_giua_module(ms: list[Module]) -> list[dict[str, str]]:
    """Luồng tín hiệu: ra của module A trùng vào của module B thì có cạnh A→B.

    Suy ra bằng MÃ từ tên tín hiệu, không hỏi mô hình vẽ mũi tên. Hệ quả tốt: nếu hai
    module nghĩ khác nhau về tên một tín hiệu, mũi tên biến mất và người thấy ngay —
    một hình vẽ do mô hình nối thì luôn đẹp và không bao giờ phát hiện lỗi đó.
    """
    ra: list[dict[str, str]] = []
    for a in ms:
        cho_ra = {s.strip().upper() for s in a.tin_hieu_ra if s.strip()}
        for b in ms:
            if b.ma == a.ma:
                continue
            chung = sorted(cho_ra & {s.strip().upper() for s in b.tin_hieu_vao if s.strip()})
            for s in chung:
                ra.append({"tu": a.ma, "den": b.ma, "tin_hieu": s})
    return ra


def tin_hieu_treo(ms: list[Module]) -> dict[str, list[str]]:
    """Tín hiệu vào mà không module nào ra (và ngược lại) — chỗ đứt của bản đồ.

    Đây là giá trị thật của sơ đồ khối: nó phải trả lời được câu "chỗ nào chưa nối"
    (§E2, cột "Người đọc thấy gì"). Một hình vẽ không nói được điều đó chỉ là trang trí.
    """
    ra_tat = {s.strip().upper() for m in ms for s in m.tin_hieu_ra if s.strip()}
    vao_tat = {s.strip().upper() for m in ms for s in m.tin_hieu_vao if s.strip()}
    return {"vao_khong_ai_cap": sorted(vao_tat - ra_tat),
            "ra_khong_ai_dung": sorted(ra_tat - vao_tat)}


_MM_XAU = re.compile(r"[^0-9A-Za-z_]")


def _mm_id(s: str) -> str:
    """Mermaid không chịu được dấu và khoảng trắng trong id nút."""
    x = _MM_XAU.sub("_", s or "")
    return x if x and not x[0].isdigit() else f"n_{x}"


def mermaid(ms: list[Module], canh: list[dict[str, str]] | None = None) -> str:
    """Sơ đồ khối dạng người đọc. Do mã sinh ⇒ cùng đầu vào, cùng một chữ (N3)."""
    if not ms:
        return ""
    c = canh if canh is not None else canh_giua_module(ms)
    L = ["graph LR"]
    for m in sorted(ms, key=lambda x: x.ma):
        nhan = m.ten or m.ma
        if m.linh_kien:
            nhan += "<br/>" + ", ".join(m.linh_kien[:4])
        if m.rail:
            nhan += f"<br/>[{m.rail}]"
        L.append(f'  {_mm_id(m.ma)}["{nhan}"]')
    for e in sorted(c, key=lambda x: (x["tu"], x["den"], x["tin_hieu"])):
        L.append(f'  {_mm_id(e["tu"])} -->|{e["tin_hieu"]}| {_mm_id(e["den"])}')
    treo = tin_hieu_treo(ms)
    for s in treo["vao_khong_ai_cap"]:
        L.append(f'  chua_noi_{_mm_id(s)}(("?")) -->|{s}| '
                 + _mm_id(next(m.ma for m in ms
                               if s in [x.strip().upper() for x in m.tin_hieu_vao])))
    return "\n".join(L)


def bang_khoi(ms: list[Module]) -> str:
    """Dạng bảng của cùng dữ liệu — cho người đọc trong Console, nơi không vẽ được hình."""
    if not ms:
        return "Chưa có khối nào."
    L = ["| Khối | Việc | Linh kiện | Vào | Ra | Nguồn | REQ |",
         "|---|---|---|---|---|---|---|"]
    for m in sorted(ms, key=lambda x: x.ma):
        L.append(f"| {m.ma} {m.ten} | {m.muc_dich} | {', '.join(m.linh_kien) or '—'} | "
                 f"{', '.join(m.tin_hieu_vao) or '—'} | {', '.join(m.tin_hieu_ra) or '—'} | "
                 f"{m.rail or '—'} | {', '.join(m.dap_ung_req) or '—'} |")
    return "\n".join(L)


# =========================================================================== gộp CKM
# EIDE-SCH-44 §4 bước 1: "requires: module_graph ≥ 1, netlist_ckm, passport".
# Ba tiền đề đó viết ra ở đây MỘT lần, để `ckm.build` và (sau này) `sch.compose` không
# thể có hai ý kiến khác nhau về "đủ chưa".
TIEN_DE_SO_DO = (
    # Đếm theo `kind:block`/`kind:subblock`, KHÔNG theo số nút loại `module` — vì từ
    # HIER-45 cây luôn có một nút gốc `kind=board` do mã tự tạo, và đếm nó là tự trả lời
    # "đã có khối" cho một bản đồ chưa có khối nào. Một tiền đề tự thoả là một tiền đề bỏ.
    (("kind:block", "kind:subblock"), 1, "sơ đồ khối: ít nhất một khối", "ckm.module_set"),
    (("net",), 1, "netlist nội bộ: ít nhất một net", "ckm.net_set hoặc ckm.import_netlist"),
    # Đếm chip CÓ HỘ CHIẾU, không phải chip có trong bản đồ. SCH-44 §4 đòi `passport`, và
    # một chip chưa ghim hộ chiếu là một chip chưa ai đối chiếu với tài liệu nào — đúng thứ
    # không được làm nền cho một sơ đồ. Ca đo bắt được chỗ này: tiền đề ghi "hộ chiếu đã
    # ghim" nhưng lại tự thoả bởi `ckm.chip_add`.
    (("chip_co_ho_chieu",), 1, "hộ chiếu chip đã ghim", "passport.pin"),
)


def thieu_gi(dem: dict[str, int]) -> list[dict[str, str]]:
    ra = []
    for khoa, toi_thieu, nhan, cong_cu in TIEN_DE_SO_DO:
        if sum(dem.get(k, 0) for k in khoa) < toi_thieu:
            ra.append({"loai": khoa[0].removeprefix("kind:"), "can": nhan, "goi": cong_cu})
    return ra


def _hop_le_loai(loai: str, danh_sach: tuple[str, ...], ten_truong: str) -> None:
    if loai not in danh_sach:
        raise ValueError(f"{ten_truong} lạ: {loai!r}. Chỉ nhận: {', '.join(danh_sach)}")


# =========================================================================== hình chiếu
# Vì sao KG là HÌNH CHIẾU chứ không phải nguồn sự thật:
#
# N9 nói mọi thay đổi là một changeset hoàn tác được. Changeset lùi lại bằng cách đặt
# `canonical` của hiện vật về bản trước (xem `History._ap_mot`). Nếu KG được ghi trực
# tiếp, thì sau một lần hoàn tác, hiện vật lùi mà đồ thị vẫn còn chân đã gán — và người
# dùng nhìn hai chỗ thấy hai câu trả lời khác nhau về cùng một mạch. Đó là cách tệ nhất
# để sai: không ai biết bên nào đúng.
#
# Nên: hiện vật là sự thật, `ckm_nodes/ckm_edges` dựng lại từ hiện vật. Cùng cách kho
# làm với `events` → `artefacts`. Hoàn tác xong gọi `chieu()` là đồ thị khớp lại.
#
# Giá phải trả: mỗi lần ghi phải dựng lại cả đồ thị. Đo trên bản đồ 200 chân: ~12 ms.
# Rẻ hơn nhiều so với một bản đồ nói dối.
MA_DO_THI = "MG-1"
MA_NETLIST = "netlist:CKM"
MA_CKM = "CKM-1"


def ma_chip(ref: str) -> str:
    return f"ckm:chip:{ref}"


def ma_pinout(ref: str) -> str:
    return f"pinout:{ref}"


def chieu(store: Any) -> dict[str, int]:
    """Dựng lại toàn bộ KG từ hiện vật. Gọi sau mỗi lần ghi và sau mỗi lần hoàn tác."""
    store.ckm_xoa_het()

    # 1) chip và chân — từ hiện vật `ckm:chip:<ten>`
    for a in store.list(type="ckm", limit=500):
        if not a["id"].startswith("ckm:chip:"):
            continue
        c = a["canonical"]
        ten, ref = c.get("chip", ""), c.get("ref", "")
        if not ten or not ref:
            continue
        nid = f"chip:{ref}"
        store.ckm_dat_nut(node_id=nid, loai="chip", ten=ten,
                          canonical={"ten": ten, "ref": ref,
                                     "ho_chieu": c.get("ho_chieu", ""),
                                     "so_chan": len(c.get("chan") or [])},
                          tier="VANG" if c.get("ho_chieu") else None,
                          nguon={"passport": c.get("ho_chieu", "")})
        for ch in c.get("chan") or []:
            pid = ma_pin(ref, ch.get("chan", ""))
            store.ckm_dat_nut(node_id=pid, loai="pin", ten=ch.get("ten") or ch.get("chan", ""),
                              canonical=ch, tier=ch.get("tier"),
                              nguon={"fact_id": ch.get("fact_id", "")})
            store.ckm_dat_canh(loai="CO_CHAN", tu=nid, den=pid)

    # 2) net — từ `netlist:CKM`
    nl = store.get(MA_NETLIST)
    if nl:
        for lk in nl["canonical"].get("linh_kien") or []:
            ref = lk.get("ref", "")
            if ref:
                store.ckm_dat_nut(node_id=f"linh_kien:{ref}", loai="linh_kien", ten=ref,
                                  canonical=lk, tier=lk.get("tier"))
        for n in nl["canonical"].get("net") or []:
            ten = n.get("ten", "")
            if not ten:
                continue
            nid = ma_net(ten)
            store.ckm_dat_nut(node_id=nid, loai="net", ten=ten, canonical=n,
                              tier=n.get("tier"))
            for c in n.get("chan") or []:
                pid = f"pin:{c}"
                if store.ckm_nut(pid) is None:
                    s = str(c)
                    store.ckm_dat_nut(node_id=pid, loai="pin", ten=s,
                                      canonical={"chan": s.split(".", 1)[-1],
                                                 "ref": s.split(".", 1)[0]})
                store.ckm_dat_canh(loai="NOI", tu=nid, den=pid)
            if n.get("bus"):
                store.ckm_dat_nut(node_id=f"bus:{n['bus']}", loai="bus", ten=n["bus"],
                                  canonical={"ten": n["bus"]})
                store.ckm_dat_canh(loai="GOM", tu=f"bus:{n['bus']}", den=nid)
            if n.get("loai") in ("power", "ground"):
                store.ckm_dat_nut(node_id=f"rail:{ten}", loai="rail", ten=ten,
                                  canonical={"ten": ten, "ap": n.get("ap_danh_dinh", "")})

    # 3) gán chân — từ `pinout:<ten>`. Chỉ mục UNIQUE của kho là chốt cuối: nếu hiện vật
    #    chứa hai lần gán cùng một chân thì việc dựng lại NỔ, và đó là điều đúng — im
    #    lặng chọn một cái là chọn hộ người dùng một quyết định thiết kế.
    for a in store.list(type="pinout", limit=500):
        ref = a["canonical"].get("ref") or a["canonical"].get("chip", "")
        for g in a["canonical"].get("gan") or []:
            pid = ma_pin(ref, g.get("chan", ""))
            if store.ckm_nut(pid) is None:
                store.ckm_dat_nut(node_id=pid, loai="pin", ten=g.get("chan", ""),
                                  canonical={"chan": g.get("chan", "")}, tier=g.get("tier"))
            fid = f"chuc_nang:{g.get('chuc_nang', '')}"
            store.ckm_dat_nut(node_id=fid, loai="chuc_nang", ten=g.get("chuc_nang", ""),
                              canonical={"ten": g.get("chuc_nang", "")})
            store.ckm_dat_canh(loai="DUOC_GAN", tu=pid, den=fid,
                               canonical={"net": g.get("net", ""),
                                          "vi_sao": g.get("vi_sao", "")})
            if g.get("net"):
                nid = ma_net(g["net"])
                if store.ckm_nut(nid) is None:
                    store.ckm_dat_nut(node_id=nid, loai="net", ten=g["net"],
                                      canonical={"ten": g["net"], "chan": []})
                store.ckm_dat_canh(loai="NOI", tu=nid, den=pid)

    # 4) khối — từ `MG-1`
    mg = store.get(MA_DO_THI)
    if mg:
        for d in mg["canonical"].get("khoi") or []:
            m = Module.from_dict(d)
            store.ckm_dat_nut(node_id=ma_module(m.ma), loai="module", ten=m.ten,
                              canonical=m.to_dict())
            for lk in m.linh_kien:
                store.ckm_dat_canh(loai="GOM", tu=ma_module(m.ma), den=f"linh_kien:{lk}")
            for rq in m.dap_ung_req:
                store.ckm_dat_canh(loai="THUC_HIEN", tu=ma_module(m.ma), den=f"req:{rq}")
            if m.rail:
                store.ckm_dat_nut(node_id=f"rail:{m.rail}", loai="rail", ten=m.rail,
                                  canonical={"ten": m.rail})
                store.ckm_dat_canh(loai="CAP", tu=f"rail:{m.rail}", den=ma_module(m.ma))

    # 5) CÂY — HIER-45. Chạy cuối, vì nó đọc mọi thứ bốn bước trên vừa dựng.
    from . import cay as _cay
    _cay.dung_cay(store)

    # 6) Bất biến cây. §3 nói "kiểm bằng mã sau mỗi thay đổi" mà không nói ai gọi; đặt ở
    #    đây vì `chieu()` là MỘT CỬA duy nhất mọi thay đổi bản đồ phải đi qua.
    #
    #    Vi phạm được TRẢ VỀ, không nổ. Khác với chỉ mục ĐƯỢC_GÁN (nơi kho từ chối ghi),
    #    một cái cây lệch vẫn phải dựng lên được — vì nếu không, người dùng mất luôn đường
    #    nhìn thấy nó lệch ở đâu. Người gọi có trách nhiệm nói ra: `ckm.build` liệt kê,
    #    giao diện tô, và không ai được coi bản đồ có vi phạm là bản đồ dùng được.
    cay = _cay.Cay.doc(store)
    vi_pham = _cay.kiem_bat_bien(cay, chan_theo_fact=_chan_theo_fact(store, cay))
    d = store.ckm_dem()
    if vi_pham:
        d["vi_pham_cay"] = len(vi_pham)
    store._ckm_vi_pham = [v.to_dict() for v in vi_pham]     # noqa: SLF001 — xem ghi chú
    return d


def vi_pham_cay(store: Any) -> list[dict[str, str]]:
    """Vi phạm bất biến của lần `chieu()` gần nhất.

    Cất trên đối tượng kho thay vì trả kèm `chieu()` vì `chieu()` đã có 12 chỗ gọi và
    không chỗ nào cần con số này — đổi chữ ký của nó để phục vụ một chỗ đọc là bắt mười
    một chỗ khác chịu thay đổi. Ai cần thì gọi hàm này.
    """
    return list(getattr(store, "_ckm_vi_pham", []) or [])


def _chan_theo_fact(store: Any, cay: Any) -> dict[str, set[str]]:
    """Tập chân mà Fact nói một lá CÓ — vế "đúng" của bất biến E9004.

    Chỉ trả về ref nào thật sự có Fact. Lá chưa có datasheet không có mặt ở đây, nên E9004
    **không kết luận gì** về nó (N6) thay vì báo thiếu cả 28 chân.
    """
    ra: dict[str, set[str]] = {}
    for nid, n in cay.nut.items():
        if n.get("kind") != "leaf":
            continue
        ref = n["canonical"].get("ref") or n["ten"]
        ten_chip = n["canonical"].get("ten") or n["ten"]
        chan = chan_tu_fact(store.query_facts(subject=f"pin:{ten_chip}.", limit=2000),
                            ten_chip)
        if chan:
            ra[nid] = {c for c, v in chan.items()
                       if not v.tier or v.tier.upper() in TANG_THIET_KE}
    return ra


def cho_dut(nut_pin: list[dict[str, Any]], canh_gan: list[dict[str, Any]],
            nets: list[dict[str, Any]],
            canh_co_chan: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Chỗ bản đồ còn hở. Nói ra bằng con số, không bằng tính từ.

    §E2 đòi tab Tri thức mạch trả lời "chỗ nào chưa có Fact (đứt)". Bốn chỗ hở, và chúng
    KHÔNG gộp được vì việc phải làm khác nhau:

      chân chưa gán       việc chưa làm — chân có bảng chân mà chưa quyết chức năng
      chân không bảng chân chưa có datasheet cho linh kiện đó, nên không kiểm được gì
      net một chân        gần như luôn là lỗi VẼ
      net không chân      một cái tên không nghĩa gì

    Phân biệt hai loại đầu là điều đo trên bộ E2E mới thấy: khi gộp chúng, một bo có
    ATmega328P (5 chân đã nạp, 2 chưa gán) cộng một cảm biến chưa có datasheet báo
    "6 chân chưa gán chức năng" — con số đó thúc người đi gán chân của một linh kiện mà
    họ chưa có tài liệu, tức là thúc đúng vào chỗ N1 cấm.
    """
    da_gan = {e["tu"] for e in canh_gan}
    if canh_co_chan is None:
        co_bang_chan = {n["node_id"] for n in nut_pin}
    else:
        co_bang_chan = {e["den"] for e in canh_co_chan}
    chua_gan, khong_bang = [], []
    for n in nut_pin:
        if n["node_id"] in da_gan:
            continue
        (chua_gan if n["node_id"] in co_bang_chan else khong_bang).append(
            n["node_id"].split(":", 1)[-1])
    mot_chan, rong = [], []
    for n in nets:
        sc = len(n.get("canonical", {}).get("chan") or [])
        if sc == 1:
            mot_chan.append(n["ten"])
        elif sc == 0:
            rong.append(n["ten"])
    return {"chan_chua_gan": sorted(chua_gan), "so_chan_chua_gan": len(chua_gan),
            "chan_khong_co_bang_chan": sorted(khong_bang),
            "so_chan_khong_co_bang_chan": len(khong_bang),
            "net_mot_chan": sorted(mot_chan), "net_khong_chan": sorted(rong)}
