# -*- coding: utf-8 -*-
"""So sánh Fact có bằng chứng — EIDE-MDD-40 §C2, nguyên tắc N2.

    "Bộ so sánh fact.compare(a, b, rule) → {verdict, severity, evidence:[cite_a, cite_b],
     unverified} với 8 luật đã có ca đo: mức logic, quá áp, ngân sách bộ nhớ, trùng AF,
     pull-up, timing bus, thay thế linh kiện, cắm ngược/đoản mạch."

Hai ràng buộc làm nên giá trị của tệp này, và cả hai đều dễ bị bỏ qua khi vội:

**Một — vế ĐỒNG không được dùng để quyết định.** N2 nói so sánh chỉ hợp lệ khi cả hai
vế ∈ {VÀNG, BẠC, NGƯỜI}. Một kết luận "3,3 V không đủ lái mức logic 5 V" dựa trên con
số mô hình nhớ được thì *nghe đúng*, và đó chính là vấn đề: nó sẽ được tin. Nên ở đây
vế ĐỒNG làm phép so sánh **trả về `unverified`**, không trả về kết luận.

**Hai — mọi kết luận mang theo hai trích dẫn.** Người đọc phải mở được cả hai trang tài
liệu mà đối chiếu. Không có bằng chứng thì kết luận chỉ là một lời khẳng định khác.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .docs import ve_si

TANG_DUNG_DUOC = frozenset({"VANG", "BAC", "NGUOI"})

# Tên tầng cho người đọc — MỘT nguồn sự thật, ở ngay cạnh chỗ định nghĩa tầng.
#
# Trước đây bảng này bị sao ra hai chỗ (`store/inventory.py` và `surfaces.py`). Thêm
# tầng CẤU HÌNH, mình sửa một bản và bỏ sót bản kia — và nó vỡ bằng cách tệ nhất có
# thể: `KeyError` trong hàm dựng `<inventory>`, tức **giết cả lượt** trước khi mô hình
# được gọi. Một phép tra TÊN HIỂN THỊ không bao giờ được phép làm chết một lượt.
TEN_TANG_VI = {"VANG": "VÀNG", "BAC": "BẠC", "NGUOI": "NGƯỜI", "DONG": "ĐỒNG",
               "CAUHINH": "CẤU HÌNH"}

# Thứ tự hiện cho người. CAUHINH cuối vì nó không phải một mức tin cậy về giới hạn vật
# lý — nó là một loại nguồn khác hẳn (ING-43 §4.5).
THU_TU_TANG = ("VANG", "BAC", "NGUOI", "DONG", "CAUHINH")


def ten_tang(ma: str) -> str:
    """Tầng lạ thì hiện nguyên mã, KHÔNG nổ."""
    return TEN_TANG_VI.get((ma or "").upper(), ma or "?")

# ING-43 §5.3 — khi cùng một khoá có nhiều nguồn, ai thắng?
#
# Thứ tự này KHÔNG phải để hệ thống tự chọn rồi im lặng. Nó là **đề xuất** kèm lý do,
# và người chọn. Lý do: một errata mới hơn thường đúng hơn, nhưng không phải luôn —
# có khi errata nói về một mã chip khác, có khi bản cũ mới là bản đang chạy trên bo.
# Tự chọn là lấy mất của người đúng cái quyết định họ cần biết là mình đang ra.
UU_TIEN_NGUON = ["errata", "datasheet_moi", "datasheet_cu", "config", "code"]

_UU_TIEN_VI = {
    "errata": "errata — nhà sản xuất sửa lại chính tài liệu của họ",
    "datasheet_moi": "datasheet bản mới hơn",
    "datasheet_cu": "datasheet bản cũ",
    "config": "tệp cấu hình của dự án — nói dự án ĐANG đặt gì, không nói chip chịu được gì",
    "code": "hằng số trong mã — chỉ để đối chiếu, không phải nguồn sự thật",
}


def _hang_nguon(f: dict[str, Any]) -> str:
    """Xếp một Fact vào một hạng nguồn để so."""
    src = f.get("source") or {}
    if isinstance(src, str):
        import json as _j
        try:
            src = _j.loads(src)
        except ValueError:
            src = {}
    if src.get("errata") or "errata" in str(src.get("doc_id", "")).lower():
        return "errata"
    og = f.get("origin", "")
    if og == "config":
        return "config"
    if og == "code":
        return "code"
    return "datasheet_moi" if src.get("version") else "datasheet_cu"


def doi_chieu_cheo(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cùng (thực thể, khoá) mà nhiều nguồn cho số khác nhau → một bảng khác biệt.

    ING-43 §5.3 và ca TC011 (hai phiên bản datasheet). Điều bộ này cố ý KHÔNG làm là
    tự chọn một bên: nó xếp hạng, nói vì sao, và để người quyết. Một hệ thống tự hoà
    giải mâu thuẫn giữa hai tài liệu sẽ đúng phần lớn thời gian — và lần sai thì không
    ai biết là đã có mâu thuẫn.
    """
    from .docs import ve_si

    nhom: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for f in facts:
        nhom.setdefault((f.get("subject", ""), f.get("key", "")), []).append(f)

    ra: list[dict[str, Any]] = []
    for (tt, khoa), ds in sorted(nhom.items()):
        if len(ds) < 2:
            continue
        si = {}
        for f in ds:
            v = f.get("value")
            if v is None:
                continue
            si[f.get("fact_id", "")] = ve_si(float(v), f.get("unit", ""))
        if len({round(x[0], 9) for x in si.values()}) < 2:
            continue                      # cùng giá trị, khác cách viết → không lệch

        xep = sorted(ds, key=lambda f: UU_TIEN_NGUON.index(_hang_nguon(f))
                     if _hang_nguon(f) in UU_TIEN_NGUON else 99)
        de_xuat = xep[0]
        ra.append({
            "thuc_the": tt, "khoa": khoa,
            "so_nguon": len(ds),
            "cac_ban": [{
                "fact_id": f.get("fact_id"), "gia_tri": f.get("value"),
                "don_vi": f.get("unit"), "tang": f.get("tier"),
                "hang_nguon": _hang_nguon(f),
                "nguon": (f.get("source") or {}) if isinstance(f.get("source"), dict)
                         else f.get("source"),
            } for f in xep],
            "de_xuat": de_xuat.get("fact_id"),
            "vi_sao": (f"Ưu tiên {_UU_TIEN_VI.get(_hang_nguon(de_xuat), 'nguồn này')}."),
            "can_nguoi_chon": True,
            "note_vi": ("Hai nguồn nói hai con số khác nhau. ĐỪNG tự chọn — trình cả "
                        "hai cho người dùng kèm nguồn, nêu đề xuất và lý do, rồi để họ "
                        "quyết."),
        })
    return ra


@dataclass(slots=True)
class KetQuaSoSanh:
    luat: str
    ket_luan: str                      # dat | khong_dat | canh_bao | chua_kiem_chung
    muc: str                           # blocker | major | minor | info
    giai_thich: str
    bang_chung: list[dict[str, Any]] = field(default_factory=list)
    chua_kiem_chung: bool = False
    cach_sua: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"luat": self.luat, "ket_luan": self.ket_luan, "muc": self.muc,
                "giai_thich": self.giai_thich, "bang_chung": self.bang_chung,
                "chua_kiem_chung": self.chua_kiem_chung, "cach_sua": self.cach_sua}


def _cite(f: dict[str, Any]) -> dict[str, Any]:
    import json
    s = f.get("source")
    if isinstance(s, str):
        try:
            s = json.loads(s)
        except ValueError:
            s = {}
    s = s or {}
    if s.get("page"):
        nguon = f"{s.get('doc_id', 'tài liệu')} tr.{s['page']}"
    elif s.get("human_act_id"):
        nguon = f"anh nói ({s['human_act_id']}), chưa có tài liệu"
    else:
        nguon = "không rõ nguồn"
    return {"khoa": f.get("key"), "thuc_the": f.get("subject"),
            "gia_tri": f.get("value"), "don_vi": f.get("unit"),
            "tang": f.get("tier"), "nguon": nguon,
            "trich_doan": (s.get("quote") or "")[:160]}


def _so(f: dict[str, Any]) -> tuple[float, str]:
    try:
        return ve_si(float(str(f.get("value")).replace(",", ".")), f.get("unit") or "")
    except (TypeError, ValueError):
        return (float("nan"), f.get("unit") or "")


def _chan_dong(a: dict[str, Any], b: dict[str, Any], luat: str) -> KetQuaSoSanh | None:
    """N2 — có vế ĐỒNG thì KHÔNG kết luận."""
    dong = [f for f in (a, b) if (f.get("tier") or "").upper() not in TANG_DUNG_DUOC]
    if not dong:
        return None
    ten = ", ".join(f"{f.get('subject')}·{f.get('key')}" for f in dong)
    return KetQuaSoSanh(
        luat=luat, ket_luan="chua_kiem_chung", muc="info", chua_kiem_chung=True,
        giai_thich=(f"Không kết luận được: {ten} ở tầng ĐỒNG (tri thức chung của mô "
                    "hình, chưa có tài liệu). Một phép so sánh có vế ĐỒNG nghe thì "
                    "đúng, và đó mới là chỗ nguy hiểm — nó sẽ được tin."),
        bang_chung=[_cite(a), _cite(b)],
        cach_sua="Nạp datasheet cho vế thiếu, hoặc hỏi người dùng để có Fact tầng NGƯỜI.")


# =========================================================================== 8 luật
def muc_logic(ra: dict[str, Any], vao: dict[str, Any]) -> KetQuaSoSanh:
    """Đầu ra của chip A có lái nổi mức logic đầu vào của chip B không? (TC013)"""
    chan = _chan_dong(ra, vao, "muc_logic")
    if chan:
        return chan
    voh, _ = _so(ra)
    vih, _ = _so(vao)
    bc = [_cite(ra), _cite(vao)]
    if voh >= vih:
        return KetQuaSoSanh("muc_logic", "dat", "info",
                            f"VOH {voh:g} V ≥ VIH {vih:g} V — mức logic tương thích.", bc)
    return KetQuaSoSanh(
        "muc_logic", "khong_dat", "blocker",
        f"VOH của bên phát là {voh:g} V, nhưng bên thu cần VIH tối thiểu {vih:g} V. "
        f"Thiếu {vih - voh:g} V — bên thu sẽ đọc mức cao thành mức thấp, không ổn định.",
        bc, cach_sua="Thêm mạch chuyển mức (level shifter) hai chiều, hoặc chọn linh "
                     "kiện cùng dải điện áp.")


def qua_ap(ap_cap: dict[str, Any], chiu_toi_da: dict[str, Any]) -> KetQuaSoSanh:
    """Điện áp cấp có vượt mức chịu đựng của chân không? (TC038)"""
    chan = _chan_dong(ap_cap, chiu_toi_da, "qua_ap")
    if chan:
        return chan
    v, _ = _so(ap_cap)
    vmax, _ = _so(chiu_toi_da)
    bc = [_cite(ap_cap), _cite(chiu_toi_da)]
    if v <= vmax:
        return KetQuaSoSanh("qua_ap", "dat", "info",
                            f"{v:g} V ≤ {vmax:g} V — trong giới hạn.", bc)
    return KetQuaSoSanh(
        "qua_ap", "khong_dat", "blocker",
        f"Cấp {v:g} V vào chân chịu tối đa {vmax:g} V — vượt {v - vmax:g} V. "
        "Đây là hỏng vĩnh viễn, không phải hoạt động sai.",
        bc, cach_sua=f"Cấp từ rail ≤ {vmax:g} V, hoặc thêm mạch hạ/chuyển mức.")


def ngan_sach_bo_nho(can: dict[str, Any], co: dict[str, Any]) -> KetQuaSoSanh:
    """Chương trình có vừa bộ nhớ không? (TC021)"""
    chan = _chan_dong(can, co, "ngan_sach_bo_nho")
    if chan:
        return chan
    c, dv = _so(can)
    t, _ = _so(co)
    bc = [_cite(can), _cite(co)]
    if c <= t:
        return KetQuaSoSanh("ngan_sach_bo_nho", "dat", "info",
                            f"Cần {c:g} {dv}, có {t:g} {dv} — còn {t - c:g} {dv} "
                            f"({(1 - c / t) * 100:.0f}%).", bc)
    return KetQuaSoSanh(
        "ngan_sach_bo_nho", "khong_dat", "blocker",
        f"Cần {c:g} {dv} nhưng chip chỉ có {t:g} {dv} — thiếu {c - t:g} {dv}. "
        "Trình biên dịch sẽ báo lỗi linker; phát hiện được từ mức yêu cầu là sớm hơn.",
        bc, cach_sua="Giảm dữ liệu tĩnh, bật tối ưu kích thước, hoặc đổi sang chip có "
                     "bộ nhớ lớn hơn.")


def trung_af(a: dict[str, Any], b: dict[str, Any]) -> KetQuaSoSanh:
    """Hai chức năng cùng gán vào một chân (§C2 quan hệ ĐƯỢC_GÁN là duy nhất)."""
    chan = _chan_dong(a, b, "trung_af")
    if chan:
        return chan
    bc = [_cite(a), _cite(b)]
    if a.get("subject") != b.get("subject"):
        return KetQuaSoSanh("trung_af", "dat", "info", "Hai chân khác nhau.", bc)
    return KetQuaSoSanh(
        "trung_af", "khong_dat", "blocker",
        f"Chân {a.get('subject')} đang được gán cho cả “{a.get('value')}” và "
        f"“{b.get('value')}”. Một chân chỉ giữ được một chức năng tại một thời điểm.",
        bc, cach_sua="Chuyển một trong hai sang chân khác có cùng chức năng thay thế.")


def pull_up(co: dict[str, Any] | None, can: dict[str, Any]) -> KetQuaSoSanh:
    """Bus hở cực máng (I2C) có điện trở kéo lên chưa? (TC038)"""
    if co is None:
        return KetQuaSoSanh(
            "pull_up", "khong_dat", "major",
            "Bus I2C không có điện trở kéo lên. SDA/SCL là hở cực máng — không kéo lên "
            "thì đường tín hiệu không bao giờ lên mức cao và bus đứng im.",
            [_cite(can)],
            cach_sua=f"Thêm điện trở kéo lên (thường {can.get('value')} "
                     f"{can.get('unit')}) lên rail nguồn của bus.")
    chan = _chan_dong(co, can, "pull_up")
    if chan:
        return chan
    r, _ = _so(co)
    rmax, _ = _so(can)
    bc = [_cite(co), _cite(can)]
    if r <= rmax * 2:
        return KetQuaSoSanh("pull_up", "dat", "info",
                            f"Kéo lên {co.get('value')} {co.get('unit')} — hợp lý.", bc)
    return KetQuaSoSanh(
        "pull_up", "canh_bao", "minor",
        f"Điện trở kéo lên {co.get('value')} {co.get('unit')} lớn hơn nhiều so với mức "
        f"khuyến nghị {can.get('value')} {can.get('unit')} — sườn tín hiệu sẽ chậm, "
        "tốc độ cao dễ lỗi.", bc, cach_sua="Giảm giá trị điện trở kéo lên.")


def timing_bus(toc_do: dict[str, Any], toi_da: dict[str, Any]) -> KetQuaSoSanh:
    """Tốc độ bus có vượt khả năng linh kiện chậm nhất không?"""
    chan = _chan_dong(toc_do, toi_da, "timing_bus")
    if chan:
        return chan
    f, dv = _so(toc_do)
    fmax, _ = _so(toi_da)
    bc = [_cite(toc_do), _cite(toi_da)]
    if f <= fmax:
        return KetQuaSoSanh("timing_bus", "dat", "info",
                            f"{f:g} {dv} ≤ {fmax:g} {dv}.", bc)
    return KetQuaSoSanh(
        "timing_bus", "khong_dat", "major",
        f"Chạy bus ở {f:g} {dv} nhưng linh kiện chậm nhất chỉ chịu {fmax:g} {dv}.",
        bc, cach_sua=f"Hạ tốc độ bus xuống ≤ {fmax:g} {dv}.")


def thay_the_linh_kien(cu: dict[str, Any], moi: dict[str, Any]) -> KetQuaSoSanh:
    """Linh kiện thay thế có giữ được thông số không? (TC045)"""
    chan = _chan_dong(cu, moi, "thay_the")
    if chan:
        return chan
    a, dv = _so(cu)
    b, _ = _so(moi)
    bc = [_cite(cu), _cite(moi)]
    if a == b:
        return KetQuaSoSanh("thay_the", "dat", "info",
                            f"{cu.get('key')} giống nhau: {a:g} {dv}.", bc)
    lech = abs(b - a) / a * 100 if a else float("inf")
    muc = "info" if lech < 5 else "minor" if lech < 20 else "major"
    return KetQuaSoSanh(
        "thay_the", "canh_bao" if muc != "major" else "khong_dat", muc,
        f"{cu.get('key')} đổi từ {a:g} sang {b:g} {dv} ({lech:.0f}%). "
        "Kiểm phần mạch phụ thuộc thông số này trước khi thay.", bc)


def cam_nguoc(dong_do: dict[str, Any], dong_binh_thuong: dict[str, Any]) -> KetQuaSoSanh:
    """Dòng tiêu thụ bất thường — dấu hiệu chập hoặc cắm ngược (TC036)."""
    chan = _chan_dong(dong_do, dong_binh_thuong, "cam_nguoc")
    if chan:
        return chan
    i, dv = _so(dong_do)
    binh, _ = _so(dong_binh_thuong)
    bc = [_cite(dong_do), _cite(dong_binh_thuong)]
    if i <= binh * 2:
        return KetQuaSoSanh("cam_nguoc", "dat", "info",
                            f"Dòng {i:g} {dv} trong khoảng bình thường.", bc)
    return KetQuaSoSanh(
        "cam_nguoc", "khong_dat", "blocker",
        f"NGẮT NGUỒN. Dòng đo được {i:g} {dv}, gấp {i / binh:.1f} lần mức bình thường "
        f"{binh:g} {dv} — gần như chắc chắn có chập hoặc cắm ngược nguồn.",
        bc, cach_sua="Ngắt điện, đo trở kháng VCC–GND khi chưa cấp, tìm linh kiện nóng.")


LUAT = {
    "muc_logic": muc_logic,
    "qua_ap": qua_ap,
    "ngan_sach_bo_nho": ngan_sach_bo_nho,
    "trung_af": trung_af,
    "pull_up": pull_up,
    "timing_bus": timing_bus,
    "thay_the": thay_the_linh_kien,
    "cam_nguoc": cam_nguoc,
}

MO_TA_LUAT = {
    "muc_logic": "Đầu ra của bên phát có lái nổi mức logic của bên thu không",
    "qua_ap": "Điện áp cấp có vượt mức chịu đựng của chân không",
    "ngan_sach_bo_nho": "Chương trình có vừa Flash/RAM không",
    "trung_af": "Một chân có bị gán hai chức năng không",
    "pull_up": "Bus hở cực máng đã có điện trở kéo lên chưa",
    "timing_bus": "Tốc độ bus có vượt khả năng linh kiện chậm nhất không",
    "thay_the": "Linh kiện thay thế có giữ được thông số không",
    "cam_nguoc": "Dòng tiêu thụ có bất thường không (chập / cắm ngược)",
}


def so_sanh(ten_luat: str, a: dict[str, Any], b: dict[str, Any] | None) -> KetQuaSoSanh:
    ham = LUAT.get(ten_luat)
    if ham is None:
        return KetQuaSoSanh(ten_luat, "chua_kiem_chung", "info",
                            f"Không có luật tên “{ten_luat}”. Các luật có: "
                            + ", ".join(LUAT), chua_kiem_chung=True)
    if ten_luat == "pull_up":
        return ham(a if b is not None else None, b if b is not None else a)
    if b is None:
        return KetQuaSoSanh(ten_luat, "chua_kiem_chung", "info",
                            "Luật này cần hai vế.", chua_kiem_chung=True)
    return ham(a, b)
