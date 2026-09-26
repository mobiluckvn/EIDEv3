# -*- coding: utf-8 -*-
"""Thư viện khối tái dùng `block@semver` — EIDE-HIER-45 §5. Bước HIER-C.

Vấn đề §1 lỗ hổng 6 nêu: *"Mỗi dự án vẽ lại LDO, pull-up, reset…"*. Một khối thư viện là cách
đóng gói việc đã làm đúng một lần.

Điều khó ở đây **không** phải việc đóng gói — mà là hai chỗ dễ nói dối:

**1. Số dẫn xuất.** §5 nói *"đặt vào cây là `instantiate(block, params)` → sinh lá cụ thể (R
theo Vout…), mọi số từ công thức có nguồn — không bịa"*. Một khối LDO đặt với `Vout=3,3 V`
phải sinh ra hai điện trở chia áp với giá trị **tính được**, và mỗi giá trị phải nói được nó
ra từ công thức nào, tham số nào, và tham số đó lấy ở đâu. Không có nguồn thì **không điền
số** — đó là N1 áp vào một chỗ rất dễ lách, vì con số tính ra trông luôn có vẻ đúng.

**2. Tính khép kín.** §5 cuối: trích một khối thành thư viện phải *"kiểm tính khép kín (chỉ
giao tiếp qua Port)"*. Một khối có net chạm ra ngoài mà không qua Port thì đem sang dự án khác
sẽ **im lặng hở** — nó vẫn đặt được, vẫn vẽ được, và chỉ sai khi hàn.

Ba tầng lưu (§5): dự án `.eide/blocks/` → người dùng `~/.eide/blocks/` → gói toàn cầu M4. Tầng
ba chưa có (đòi một kênh phát hành và một chuỗi hash, cả hai chưa tồn tại), nên `tra_khoi` đọc
hai tầng và **nói rõ** điều đó.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import cay as C

MANIFEST = "manifest.json"
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_TEN_HOP_LE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,40}$")


def ma_khoi(ten: str, phien_ban: str) -> str:
    """`LDO-3V3@1.2.0` — cùng dạng `ns.part@semver` của hộ chiếu chip (§5)."""
    return f"{ten}@{phien_ban}"


def tach_ma(ma: str) -> tuple[str, str]:
    ten, _, pb = (ma or "").partition("@")
    return ten, pb


# =========================================================================== công thức §5
# Phép tính cho tham số dẫn xuất. Danh sách ĐÓNG, mỗi phép một hàm — không `eval`.
#
# Vì sao không `eval` dù nó ngắn hơn mười lần: manifest khối đến từ một tệp trên đĩa, và tệp
# đó có thể do người khác viết (§5 nói khối được chia sẻ giữa các dự án). `eval` trên nội dung
# tệp là thực thi mã của người lạ. Danh sách đóng thì một công thức lạ bị **từ chối kèm tên**,
# và đó là thông tin cho người viết khối chứ không phải một lỗi khó hiểu.
def _chia_ap_r2(vout: float, vref: float, r1: float) -> float:
    """R2 của mạch chia áp hồi tiếp: `R2 = R1 / (Vout/Vref − 1)`."""
    k = vout / vref - 1.0
    if k <= 0:
        raise ValueError(f"Vout ({vout}) phải lớn hơn Vref ({vref}) mới chia áp được")
    return r1 / k


def _tu_loc(i_max: float, dv: float, f: float) -> float:
    """Tụ lọc tối thiểu: `C = I / (ΔV · f)`."""
    if dv <= 0 or f <= 0:
        raise ValueError("ΔV và tần số phải dương")
    return i_max / (dv * f)


def _pull_up(vdd: float, i_keo: float) -> float:
    """Điện trở kéo lên tối đa theo dòng kéo: `R = Vdd / I`."""
    if i_keo <= 0:
        raise ValueError("dòng kéo phải dương")
    return vdd / i_keo


CONG_THUC: dict[str, tuple[Any, tuple[str, ...], str]] = {
    "chia_ap_r2": (_chia_ap_r2, ("vout", "vref", "r1"), "R2 = R1 / (Vout/Vref − 1)"),
    "tu_loc": (_tu_loc, ("i_max", "dv", "f"), "C = I / (ΔV · f)"),
    "pull_up": (_pull_up, ("vdd", "i_keo"), "R = Vdd / I"),
}


@dataclass(slots=True)
class GiaTriDanXuat:
    """Một con số TÍNH RA, luôn mang theo đường đi của nó.

    Không có dạng nào khác để trả về một số dẫn xuất trong module này. Một `float` trần đi
    vào hiện vật là một con số không ai kiểm lại được — và nó trông y như một con số đọc từ
    datasheet.
    """

    gia_tri: float
    don_vi: str
    cong_thuc: str
    tham_so: dict[str, Any] = field(default_factory=dict)
    nguon: dict[str, str] = field(default_factory=dict)      # tham số → nguồn của nó
    tier: str = "VANG"

    def to_dict(self) -> dict[str, Any]:
        return {"gia_tri": self.gia_tri, "don_vi": self.don_vi,
                "cong_thuc": self.cong_thuc, "tham_so": dict(self.tham_so),
                "nguon": dict(self.nguon), "tier": self.tier}

    def cau_vi(self) -> str:
        return (f"{_so_vi(self.gia_tri)} {self.don_vi} — tính bằng {self.cong_thuc}, với "
                + ", ".join(f"{k}={_so_vi(v) if isinstance(v, (int, float)) else v}"
                            for k, v in sorted(self.tham_so.items()))
                + (" (nguồn: " + "; ".join(f"{k} từ {v}" for k, v in sorted(self.nguon.items()))
                   + ")" if self.nguon else ""))


def _so_vi(x: Any) -> str:
    if not isinstance(x, (int, float)):
        return str(x)
    s = f"{x:.6g}"
    return s.replace(".", ",")


# =========================================================================== manifest
@dataclass(slots=True)
class Khoi:
    """Một gói khối. `cay_con` là cấu trúc bên trong; `port` là hợp đồng."""

    ten: str
    phien_ban: str
    mo_ta: str = ""
    port: list[dict[str, Any]] = field(default_factory=list)
    params: list[dict[str, Any]] = field(default_factory=list)
    la: list[dict[str, Any]] = field(default_factory=list)       # linh kiện bên trong
    net: list[dict[str, Any]] = field(default_factory=list)      # net cục bộ
    fact: list[dict[str, Any]] = field(default_factory=list)
    bom: list[dict[str, Any]] = field(default_factory=list)
    explain: dict[str, Any] = field(default_factory=dict)
    ca_kiem: list[dict[str, Any]] = field(default_factory=list)
    tang: str = ""              # tầng đã lấy khối này ra: "du_an" | "nguoi_dung" | "M4"

    @property
    def ma(self) -> str:
        return ma_khoi(self.ten, self.phien_ban)

    def to_dict(self) -> dict[str, Any]:
        return {"ten": self.ten, "phien_ban": self.phien_ban, "mo_ta": self.mo_ta,
                "port": self.port, "params": self.params, "la": self.la, "net": self.net,
                "fact": self.fact, "bom": self.bom, "explain": self.explain,
                "ca_kiem": self.ca_kiem}

    @staticmethod
    def from_dict(d: dict[str, Any], *, tang: str = "") -> "Khoi":
        return Khoi(ten=d.get("ten", ""), phien_ban=d.get("phien_ban", ""),
                    mo_ta=d.get("mo_ta", ""), port=list(d.get("port") or []),
                    params=list(d.get("params") or []), la=list(d.get("la") or []),
                    net=list(d.get("net") or []), fact=list(d.get("fact") or []),
                    bom=list(d.get("bom") or []), explain=dict(d.get("explain") or {}),
                    ca_kiem=list(d.get("ca_kiem") or []), tang=tang)


def kiem_manifest(d: dict[str, Any]) -> list[str]:
    """Manifest có đủ và hợp lệ không. Trả danh sách câu sai (rỗng = được)."""
    loi: list[str] = []
    ten, pb = d.get("ten", ""), d.get("phien_ban", "")
    if not _TEN_HOP_LE.match(str(ten)):
        loi.append(f"tên khối {ten!r} không hợp lệ (chữ, số, gạch; 2–41 ký tự)")
    if not SEMVER.match(str(pb)):
        loi.append(f"phiên bản {pb!r} không theo semver (ví dụ 1.0.0)")
    if not (d.get("port") or []):
        loi.append("khối không có Port nào — không ai nối được vào nó")
    for p in d.get("port") or []:
        if not p.get("ten"):
            loi.append("có Port thiếu tên")
        if p.get("huong") not in C.HUONG:
            loi.append(f"Port {p.get('ten')!r} có hướng lạ: {p.get('huong')!r}")
    for x in d.get("params") or []:
        if not x.get("ten"):
            loi.append("có tham số thiếu tên")
        ct = x.get("cong_thuc")
        if ct and ct not in CONG_THUC:
            loi.append(f"tham số {x.get('ten')!r} dùng công thức lạ {ct!r}; có: "
                       + ", ".join(sorted(CONG_THUC)))
    return loi


# =========================================================================== ba tầng §5
def _thu_muc(goc: Path, ten: str, pb: str) -> Path:
    return goc / f"{ten}@{pb}"


def luu_khoi(k: Khoi, *, goc: Path) -> Path:
    d = _thu_muc(goc, k.ten, k.phien_ban)
    d.mkdir(parents=True, exist_ok=True)
    (d / MANIFEST).write_text(json.dumps(k.to_dict(), ensure_ascii=False, indent=2) + "\n",
                              "utf-8")
    return d


def liet_ke(goc: Path, *, tang: str) -> list[Khoi]:
    if not goc.exists():
        return []
    ra: list[Khoi] = []
    for d in sorted(goc.iterdir()):
        p = d / MANIFEST
        if not p.is_file():
            continue
        try:
            ra.append(Khoi.from_dict(json.loads(p.read_text("utf-8")), tang=tang))
        except (ValueError, OSError):
            continue          # manifest hỏng: bỏ qua ở đây, `tra_khoi` nói ra khi được hỏi
    return ra


def tra_khoi(ma_hoac_ten: str, *, du_an: Path, nguoi_dung: Path
             ) -> tuple[Khoi | None, str]:
    """Tìm một khối theo thứ tự ba tầng (§5). Trả `(khối, câu giải thích)`.

    Thứ tự **dự án → người dùng → M4** không phải tuỳ tiện: khối trong dự án là khối người
    dùng đã sửa cho mạch này, nên nó phải thắng bản chung. Ngược lại thì một lần sửa cục bộ
    sẽ bị một bản thư viện mới lặng lẽ ghi đè.

    Không có phiên bản trong `ma_hoac_ten` thì lấy **bản mới nhất** theo semver, và nói ra là
    đã chọn bản nào — im lặng chọn hộ một phiên bản là chỗ dễ sai nhất của mọi hệ quản gói.
    """
    ten, pb = tach_ma(ma_hoac_ten)
    for goc, tang in ((du_an, "du_an"), (nguoi_dung, "nguoi_dung")):
        ds = [k for k in liet_ke(goc, tang=tang) if k.ten == ten]
        if pb:
            ds = [k for k in ds if k.phien_ban == pb]
        if not ds:
            continue
        ds.sort(key=lambda k: _khoa_semver(k.phien_ban), reverse=True)
        k = ds[0]
        cau = f"lấy {k.ma} từ thư viện {'dự án' if tang == 'du_an' else 'người dùng'}"
        if not pb and len(ds) > 1:
            cau += (f" — bản mới nhất trong {len(ds)} bản có sẵn ("
                    + ", ".join(x.phien_ban for x in ds) + ")")
        return k, cau
    co = {k.ma for goc, tang in ((du_an, "du_an"), (nguoi_dung, "nguoi_dung"))
          for k in liet_ke(goc, tang=tang)}
    return None, (f"không có khối nào tên {ten!r} trong thư viện dự án hay người dùng. "
                  + (f"Đang có: {', '.join(sorted(co))}. " if co else "")
                  + "Tầng thứ ba (gói toàn cầu M4) chưa có trong bản này, nên đừng nói là "
                    "'không tồn tại' — chỉ là chưa có ở hai tầng tra được.")


def _khoa_semver(pb: str) -> tuple[int, int, int]:
    m = SEMVER.match(pb or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (-1, -1, -1)


# =========================================================================== instantiate §5
@dataclass(slots=True)
class KetQuaDat:
    la: list[dict[str, Any]] = field(default_factory=list)
    port: list[dict[str, Any]] = field(default_factory=list)
    net: list[dict[str, Any]] = field(default_factory=list)
    dan_xuat: dict[str, GiaTriDanXuat] = field(default_factory=dict)
    thieu_nguon: list[str] = field(default_factory=list)
    loi: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"la": self.la, "port": self.port, "net": self.net,
                "dan_xuat": {k: v.to_dict() for k, v in self.dan_xuat.items()},
                "thieu_nguon": list(self.thieu_nguon), "loi": list(self.loi)}


def dat_khoi(k: Khoi, *, gia_tri: dict[str, Any],
             nguon: dict[str, str] | None = None) -> KetQuaDat:
    """`instantiate(block, params)` của §5. Tính tham số dẫn xuất rồi sinh lá cụ thể.

    **Mọi tham số phải có nguồn.** `nguon[ten]` nói con số đó ở đâu ra: `"anh nói: dùng 3,3 V"`,
    `"DS-AMS1117 trang 4"`, `"mặc định của khối"`. Thiếu nguồn thì tham số vào `thieu_nguon` và
    KHÔNG có lá nào được sinh từ nó — vì một điện trở tính từ một con số không ai biết ở đâu ra
    là một điện trở sẽ được hàn lên bo thật.
    """
    kq = KetQuaDat()
    ng = dict(nguon or {})
    val: dict[str, Any] = {}

    # 1) tham số người đưa, và tham số có mặc định trong manifest
    for p in k.params:
        ten = p.get("ten", "")
        if not ten:
            continue
        if ten in gia_tri:
            val[ten] = gia_tri[ten]
            if ten not in ng:
                kq.thieu_nguon.append(ten)
        elif "mac_dinh" in p:
            val[ten] = p["mac_dinh"]
            ng.setdefault(ten, f"mặc định của khối {k.ma}")
        elif not p.get("cong_thuc"):
            kq.loi.append(f"thiếu tham số {ten} (khối không có mặc định cho nó)")

    # 2) tham số dẫn xuất — theo công thức, và chỉ khi đủ đầu vào CÓ NGUỒN
    for p in k.params:
        ct = p.get("cong_thuc")
        ten = p.get("ten", "")
        if not ct or not ten:
            continue
        ham, can, mo_ta = CONG_THUC[ct]
        thieu = [c for c in can if c not in val]
        if thieu:
            kq.loi.append(f"không tính được {ten}: thiếu {', '.join(thieu)}")
            continue
        khong_nguon = [c for c in can if c not in ng]
        if khong_nguon:
            # Đây là chốt chặn N1 của bước này: một con số tính ra từ một đầu vào không nguồn
            # vẫn là một con số không nguồn, chỉ khó thấy hơn.
            kq.thieu_nguon += [c for c in khong_nguon if c not in kq.thieu_nguon]
            kq.loi.append(f"không tính {ten}: {', '.join(khong_nguon)} chưa có nguồn")
            continue
        try:
            x = float(ham(*[float(val[c]) for c in can]))
        except (TypeError, ValueError) as e:
            kq.loi.append(f"không tính được {ten}: {e}")
            continue
        gd = GiaTriDanXuat(gia_tri=x, don_vi=p.get("don_vi", ""), cong_thuc=mo_ta,
                           tham_so={c: val[c] for c in can},
                           nguon={c: ng[c] for c in can})
        kq.dan_xuat[ten] = gd
        val[ten] = x
        ng[ten] = f"tính bằng {mo_ta}"

    if kq.loi:
        return kq          # có lỗi thì KHÔNG sinh lá — thà không đặt còn hơn đặt số bịa

    # 3) sinh lá: giá trị của lá có thể trỏ tới một tham số bằng "{ten}"
    for la in k.la:
        d = dict(la)
        gt = str(d.get("gia_tri", ""))
        m = re.fullmatch(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", gt.strip())
        if m:
            ten = m.group(1)
            if ten in kq.dan_xuat:
                d["gia_tri"] = _hien(kq.dan_xuat[ten])
                d["dan_xuat"] = kq.dan_xuat[ten].to_dict()
            elif ten in val:
                d["gia_tri"] = f"{_so_vi(val[ten])}"
                d["nguon"] = ng.get(ten, "")
            else:
                kq.loi.append(f"lá {d.get('ref')} trỏ tới tham số {ten} không có")
                continue
        kq.la.append(d)
    kq.port = [dict(p) for p in k.port]
    kq.net = [dict(n) for n in k.net]
    return kq


def _hien(g: GiaTriDanXuat) -> str:
    return f"{_so_vi(g.gia_tri)} {g.don_vi}".strip()


# =========================================================================== khép kín §5
@dataclass(slots=True)
class KetQuaKhepKin:
    kin: bool
    ho: list[str] = field(default_factory=list)
    port: list[str] = field(default_factory=list)
    la: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"kin": self.kin, "ho": list(self.ho), "port": list(self.port),
                "la": list(self.la)}


def kiem_khep_kin(cay: C.Cay, module_id: str) -> KetQuaKhepKin:
    """Khối này chỉ giao tiếp qua Port chứ? §5 cuối — điều kiện để trích thành thư viện.

    Một khối **không** khép kín đem sang dự án khác sẽ im lặng hở: nó vẫn đặt được, vẫn vẽ
    được, và chỉ sai khi hàn. Nên phép kiểm này là cửa duy nhất của `khoi.extract`.

    Hở nghĩa là: một net **bên trong** khối (hoặc trong khối con của nó) được nối bởi một Port
    thuộc nút **ngoài** khối, mà không đi qua Port của chính khối.
    """
    ra = KetQuaKhepKin(kin=True)
    trong = {module_id} | set(_hau_due(cay, module_id))
    port_cua_khoi = set(cay.port_cua.get(module_id, []))
    ra.port = sorted(cay.port[p]["ten"] for p in port_cua_khoi)
    ra.la = sorted((cay.nut[x]["canonical"].get("ref") or cay.nut[x]["ten"])
                   for x in trong if cay.nut[x].get("kind") == "leaf")

    for nid in sorted(trong):
        for net in sorted(x for x in cay.con.get(nid, [])
                          if cay.nut[x]["loai"] == "net"):
            for pid in sorted(cay.noi.get(net, [])):
                p = cay.port.get(pid)
                if p is None:
                    continue
                if p["module_id"] in trong or pid in port_cua_khoi:
                    continue
                ngoai = cay.nut.get(p["module_id"], {}).get("path") or p["module_id"]
                ra.ho.append(f"net {cay.nut[net]['ten']} trong khối nối tới Port "
                             f"{p['ten']} của {ngoai} — ngoài khối, không qua Port của khối")
    if not ra.la:
        ra.ho.append("khối không có linh kiện nào bên trong — không có gì để đóng gói")
    if not ra.port:
        ra.ho.append("khối chưa khai Port nào — đem sang dự án khác thì không ai nối vào được")
    ra.kin = not ra.ho
    return ra


def _hau_due(cay: C.Cay, nid: str) -> list[str]:
    ra: list[str] = []
    ds = list(cay.con_truc_tiep(nid))
    while ds:
        x = ds.pop()
        ra.append(x)
        ds += cay.con_truc_tiep(x)
    return ra


def goi_tu_khoi(cay: C.Cay, module_id: str, *, ten: str, phien_ban: str = "1.0.0",
                mo_ta: str = "", fact: list[dict[str, Any]] | None = None) -> Khoi:
    """Đóng gói một khối trong cây thành `Khoi`. Gọi SAU khi `kiem_khep_kin` đạt."""
    trong = {module_id} | set(_hau_due(cay, module_id))
    la = [{"ref": cay.nut[x]["canonical"].get("ref") or cay.nut[x]["ten"],
           "ten": cay.nut[x]["canonical"].get("ten") or cay.nut[x]["ten"],
           "gia_tri": cay.nut[x]["canonical"].get("gia_tri", ""),
           "chan": sorted((cay.port[p].get("chan") or cay.port[p]["ten"])
                          for p in cay.port_cua.get(x, []))}
          for x in sorted(trong) if cay.nut[x].get("kind") == "leaf"]
    net = [{"ten": cay.nut[n]["ten"],
            "loai": cay.nut[n]["canonical"].get("loai", ""),
            "chan": list(cay.nut[n]["canonical"].get("chan") or [])}
           for nid in sorted(trong)
           for n in sorted(x for x in cay.con.get(nid, []) if cay.nut[x]["loai"] == "net")]
    port = [{"ten": cay.port[p]["ten"], "huong": cay.port[p]["huong"],
             "loai": cay.port[p]["loai"], "members": list(cay.port[p]["members"]),
             "rang_buoc": dict(cay.port[p]["rang_buoc"])}
            for p in sorted(cay.port_cua.get(module_id, []))]
    return Khoi(ten=ten, phien_ban=phien_ban,
                mo_ta=mo_ta or cay.nut[module_id]["canonical"].get("muc_dich", ""),
                port=port, la=la, net=net, fact=list(fact or []),
                bom=[{"ref": x["ref"], "ten": x["ten"], "gia_tri": x["gia_tri"]}
                     for x in la])
