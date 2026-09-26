# -*- coding: utf-8 -*-
"""Công cụ thư viện khối — EIDE-HIER-45 §5. Bước HIER-C.

Bốn công cụ: `khoi.list` · `khoi.place` · `khoi.extract` · `khoi.upgrade`.

Hai chỗ các công cụ này cố ý KHÓ hơn mức cần để chạy:

**`khoi.place` đi qua cổng G-DESIGN.** §5 nói *"người duyệt (G-DESIGN) mới đặt vào cây"*. Đặt
một khối thư viện là một quyết định thiết kế — nó mang theo linh kiện, giá trị và cả một cụm
Fact vào mạch của người dùng. Một công cụ đặt được mà không hỏi sẽ dựng xong nửa mạch trước
khi ai kịp đọc.

**`khoi.extract` từ chối khối không khép kín.** Một khối có net chạm ra ngoài mà không qua Port
thì đem sang dự án khác sẽ **im lặng hở**: vẫn đặt được, vẫn vẽ được, chỉ sai khi hàn.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from ..knowledge import cay as KC
from ..knowledge import ckm as K
from ..knowledge import khoi_thu_vien as KTV
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA


def _goc(ctx: Any):
    from ..config import user_blocks_path
    return ctx.config.paths.blocks, user_blocks_path()


def register(r: Registry) -> Registry:

    @r.tool("khoi.list", "Thiết kế",
            "Xem thư viện khối tái dùng đang có (LDO, pull-up, reset RC, dao động…). Ba tầng: "
            "dự án trước, rồi thư viện người dùng. Gọi cái này TRƯỚC khi vẽ tay một cụm quen.",
            {"type": "object",
             "properties": {"ten": {"type": "string",
                                    "description": "Chỉ tìm khối tên này"}},
             "required": []},
            risk="R1", core=False,
            keywords=["thư viện khối", "khối tái dùng", "block", "ldo", "pull-up",
                      "reset", "dao động"])
    def khoi_list(ctx: Any, ten: str = ""):
        du_an, nguoi = _goc(ctx)
        ds = (KTV.liet_ke(du_an, tang="du_an") + KTV.liet_ke(nguoi, tang="nguoi_dung"))
        if ten:
            ds = [k for k in ds if k.ten == ten]
        return {
            "so_khoi": len(ds),
            "khoi": [{"ma": k.ma, "tang": k.tang, "mo_ta": k.mo_ta,
                      "port": [p.get("ten") for p in k.port],
                      "params": [{"ten": p.get("ten"), "don_vi": p.get("don_vi", ""),
                                  "cong_thuc": p.get("cong_thuc", ""),
                                  "mac_dinh": p.get("mac_dinh")} for p in k.params],
                      "so_linh_kien": len(k.la)} for k in ds],
            "note_vi": (f"{len(ds)} khối trong thư viện."
                        if ds else
                        "Thư viện khối đang rỗng ở cả hai tầng tra được (dự án và người "
                        "dùng). Tầng thứ ba — gói toàn cầu M4 — chưa có trong bản này, nên "
                        "đừng nói với người dùng là 'không có khối nào tồn tại'."),
        }

    @r.tool("khoi.place", "Thiết kế",
            "Đặt một khối thư viện vào cây với tham số cụ thể. Mã tính các giá trị dẫn xuất "
            "(điện trở chia áp, tụ lọc…) từ công thức, và MỌI tham số phải nói được nó ở đâu "
            "ra — thiếu nguồn thì không đặt, chứ không điền số.",
            {"type": "object",
             "properties": {
                 "ma": {"type": "string",
                        "description": "LDO-3V3@1.2.0, hoặc chỉ LDO-3V3 để lấy bản mới nhất"},
                 "khoi": {"type": "string",
                          "description": "Mã khối trong cây để đặt vào (MOD-PWR). Chưa có "
                                         "thì công cụ tạo khối mới với mã này."},
                 "tham_so": {"type": "object",
                             "description": 'Giá trị tham số: {"vout": 3.3}'},
                 "nguon": {"type": "object",
                           "description": 'Mỗi tham số ở ĐÂU ra: {"vout": "anh nói: dùng '
                                          '3,3 V"} hoặc {"vout": "DS-XYZ trang 4"}'},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ma", "khoi", "explain"]},
            risk="R2", gate="G-DESIGN", core=False, writes_artefact=True,
            needs_explain=True, produces=["block_diagram", "netlist"],
            keywords=["đặt khối", "dùng khối", "thư viện", "instantiate"])
    def khoi_place(ctx: Any, ma: str, khoi: str, explain: dict[str, Any],
                   tham_so: dict[str, Any] | None = None,
                   nguon: dict[str, str] | None = None):
        du_an, nguoi = _goc(ctx)
        k, cau = KTV.tra_khoi(ma, du_an=du_an, nguoi_dung=nguoi)
        if k is None:
            return ToolResult(False, error=EideError(
                "E2001", cau,
                hint_for_agent="Xem thư viện bằng khoi.list. Nếu mạch này có cụm đó rồi thì "
                               "trích nó thành khối bằng khoi.extract.",
                alternatives=["khoi.list", "khoi.extract"], blame="agent"))

        kq = KTV.dat_khoi(k, gia_tri=dict(tham_so or {}), nguon=dict(nguon or {}))
        if kq.loi:
            return ToolResult(False, error=EideError(
                "E8002" if kq.thieu_nguon else "E5001",
                f"Chưa đặt được {k.ma}: " + "; ".join(kq.loi[:4]),
                hint_for_agent=(
                    ("Mỗi tham số phải nói được nó ở đâu ra — truyền `nguon` cho: "
                     + ", ".join(kq.thieu_nguon)
                     + ". Người dùng nói con số thì trích nguyên văn lời họ; đọc từ "
                       "datasheet thì ghi mã tài liệu và trang. Một điện trở tính từ con số "
                       "không ai biết ở đâu ra là một điện trở sẽ được hàn lên bo thật.")
                    if kq.thieu_nguon else
                    "Xem params của khối bằng khoi.list rồi truyền đủ tham số."),
                alternatives=["khoi.list", "ask_user", "fact.assert_human"],
                details=kq.to_dict(), blame="agent"))

        # Ref phải DUY NHẤT toàn mạch (HIER-45 §2.2 mục 4). Đặt cùng một khối lần thứ hai —
        # hai con LDO trên một bo là chuyện thường — thì ref trong gói (U9, R8…) đã có người
        # dùng. Cấp ref mới, và NÓI RA ánh xạ: người đọc BOM cần biết R8 của khối thành R12
        # trên bo.
        kq.la, anh_xa = _cap_ref_moi(ctx, kq.la)
        a = ctx.store.get(K.MA_DO_THI)
        ds = [K.Module.from_dict(d) for d in (a["canonical"].get("khoi") if a else [])]
        cu = next((x for x in ds if x.ma == khoi), None)
        m = K.Module(ma=khoi, ten=cu.ten if cu else f"{k.ten}",
                     muc_dich=cu.muc_dich if cu else (k.mo_ta or f"khối từ {k.ma}"),
                     linh_kien=[str(x.get("ref")) for x in kq.la],
                     cha=cu.cha if cu else "", kind=cu.kind if cu else "block",
                     port=[{"ten": p.get("ten"), "huong": p.get("huong"),
                            "loai": p.get("loai") or "single",
                            "members": list(p.get("members") or []),
                            "rang_buoc": dict(p.get("rang_buoc") or {})}
                           for p in kq.port])
        ds = [x for x in ds if x.ma != khoi] + [m]
        canon = dict(a["canonical"]) if a else {}
        canon["khoi"] = [x.to_dict() for x in sorted(ds, key=lambda z: z.ma)]
        canon["so_khoi"] = len(ds)
        # HIER-16 — ghi `block@semver` đã dùng, để snapshot và hộ chiếu truy được.
        dung = dict(canon.get("khoi_thu_vien") or {})
        dung[khoi] = {"ma": k.ma, "tang": k.tang, "tham_so": dict(tham_so or {}),
                      "nguon": dict(nguon or {}), "anh_xa_ref": anh_xa,
                      "dan_xuat": {t: g.to_dict() for t, g in kq.dan_xuat.items()}}
        canon["khoi_thu_vien"] = dung
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_DO_THI, type="block_diagram",
            op="update" if a else "create", canonical=canon, explain=explain,
            run_id=ctx.run_id)

        # Lá của khối vào netlist nội bộ dưới dạng linh kiện; Fact của khối vào kho kèm nguồn.
        _ghi_linh_kien(ctx, kq.la, explain)
        so_fact = _ghi_fact(ctx, k, kq)
        K.chieu(ctx.store)

        return {"khoi": khoi, "block": k.ma, "tang": k.tang,
                "so_linh_kien": len(kq.la), "so_fact": so_fact, "anh_xa_ref": anh_xa,
                "dan_xuat": {t: g.to_dict() for t, g in kq.dan_xuat.items()},
                "changeset": cs.id,
                "note_vi": (f"Đã đặt {k.ma} ({cau}) thành khối {khoi} với "
                            f"{len(kq.la)} linh kiện. "
                            + (f"Ref đổi để không trùng: "
                               + ", ".join(f"{a}→{b}" for a, b in sorted(anh_xa.items()))
                               + ". " if anh_xa else "")
                            + " ".join(f"{t} = {g.cau_vi()}"
                                       for t, g in sorted(kq.dan_xuat.items()))
                            + (f" {so_fact} Fact của khối đã vào kho kèm nguồn."
                               if so_fact else ""))}

    @r.tool("khoi.extract", "Thiết kế",
            "Lưu một khối đang có trong mạch thành khối thư viện dùng lại được. Công cụ kiểm "
            "khối có KHÉP KÍN không (chỉ giao tiếp qua Port) — không kín thì từ chối và nói "
            "rõ chỗ hở.",
            {"type": "object",
             "properties": {
                 "khoi": {"type": "string", "description": "Mã khối trong cây (MOD-PWR)"},
                 "ten": {"type": "string", "description": "Tên khối thư viện: LDO-3V3"},
                 "phien_ban": {"type": "string", "description": "Mặc định 1.0.0"},
                 "mo_ta": {"type": "string"},
                 "dung_chung": {"type": "boolean",
                                "description": "true = lưu vào thư viện NGƯỜI DÙNG (~/.eide) "
                                               "để dự án khác dùng được; false = chỉ dự án này"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["khoi", "ten", "explain"]},
            risk="R2", core=False, writes_artefact=True, needs_explain=True,
            produces=["report"],
            keywords=["trích khối", "lưu khối", "đóng gói", "thư viện", "extract"])
    def khoi_extract(ctx: Any, khoi: str, ten: str, explain: dict[str, Any],
                     phien_ban: str = "1.0.0", mo_ta: str = "",
                     dung_chung: bool = False):
        cay = KC.Cay.doc(ctx.store)
        nid = KC.tim_nut(cay, khoi) or KC.tim_nut(cay, K.ma_module(khoi))
        if nid is None:
            return ToolResult(False, error=EideError(
                "E2001", f"Không có khối nào mã {khoi} trong cây.",
                hint_for_agent="Xem cây bằng ckm.graph.",
                alternatives=["ckm.graph"], blame="agent"))

        kk = KTV.kiem_khep_kin(cay, nid)
        if not kk.kin:
            return ToolResult(False, error=EideError(
                "E9002",
                f"Khối {khoi} chưa KHÉP KÍN nên không đóng gói được: "
                + "; ".join(kk.ho[:3]),
                hint_for_agent=("Một khối không khép kín đem sang dự án khác sẽ im lặng hở — "
                                "vẫn đặt được, vẫn vẽ được, chỉ sai khi hàn. Khai Port ở biên "
                                "khối cho những net đang chạm ra ngoài (ckm.port_set), rồi "
                                "trích lại."),
                alternatives=["ckm.port_set", "ckm.graph"],
                details=kk.to_dict(), blame="agent"))

        trong = {nid} | set(KTV._hau_due(cay, nid))
        fact = _fact_cua_la(ctx, cay, trong)
        k = KTV.goi_tu_khoi(cay, nid, ten=ten, phien_ban=phien_ban, mo_ta=mo_ta, fact=fact)
        loi = KTV.kiem_manifest(k.to_dict())
        if loi:
            return ToolResult(False, error=EideError(
                "E5001", "Gói khối không hợp lệ: " + "; ".join(loi[:3]),
                hint_for_agent="Sửa tên hoặc phiên bản rồi trích lại.", blame="agent"))

        du_an, nguoi = _goc(ctx)
        d = KTV.luu_khoi(k, goc=(nguoi if dung_chung else du_an))
        ctx.store.apply(artefact_id=f"report:khoi:{k.ma}", type="report", op="create",
                        author=f"agent:{ctx.run_id}",
                        canonical={"ma": k.ma, "duong": str(d), "khep_kin": kk.to_dict(),
                                   "so_linh_kien": len(k.la), "so_fact": len(k.fact)},
                        explain=explain)
        return {"ma": k.ma, "duong": str(d),
                "tang": "nguoi_dung" if dung_chung else "du_an",
                "so_linh_kien": len(k.la), "so_port": len(k.port),
                "so_fact": len(k.fact), "khep_kin": kk.to_dict(),
                "note_vi": (f"Đã đóng gói {k.ma}: {len(k.la)} linh kiện, {len(k.port)} Port, "
                            f"{len(k.fact)} Fact kèm nguồn. Lưu ở thư viện "
                            + ("NGƯỜI DÙNG — dự án khác dùng được."
                               if dung_chung else "DỰ ÁN này.")
                            + " Khép kín: chỉ giao tiếp qua "
                            + ", ".join(kk.port) + ".")}

    @r.tool("khoi.upgrade", "Thiết kế",
            "Nâng một khối đang dùng trong mạch lên phiên bản khác của khối thư viện. Nói rõ "
            "Port có đổi không — đổi Port thì STALE lan ra ngoài khối, không đổi thì không.",
            {"type": "object",
             "properties": {
                 "khoi": {"type": "string", "description": "Mã khối trong cây"},
                 "ma": {"type": "string", "description": "Phiên bản đích: LDO-3V3@1.3.0"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["khoi", "ma", "explain"]},
            risk="R2", gate="G-DESIGN", core=False, writes_artefact=True,
            needs_explain=True, produces=["block_diagram"],
            keywords=["nâng phiên bản", "upgrade", "khối thư viện", "semver"])
    def khoi_upgrade(ctx: Any, khoi: str, ma: str, explain: dict[str, Any]):
        a = ctx.store.get(K.MA_DO_THI)
        dung = ((a["canonical"].get("khoi_thu_vien") or {}) if a else {}).get(khoi)
        if not dung:
            return ToolResult(False, error=EideError(
                "E2001", f"Khối {khoi} không phải đặt từ thư viện, nên không có gì để nâng.",
                hint_for_agent="Chỉ khối đặt bằng khoi.place mới nâng phiên bản được.",
                alternatives=["khoi.list", "khoi.place"], blame="agent"))
        du_an, nguoi = _goc(ctx)
        moi, cau = KTV.tra_khoi(ma, du_an=du_an, nguoi_dung=nguoi)
        if moi is None:
            return ToolResult(False, error=EideError(
                "E2001", cau, hint_for_agent="Xem bản có sẵn bằng khoi.list.",
                alternatives=["khoi.list"], blame="agent"))
        cu, _ = KTV.tra_khoi(dung["ma"], du_an=du_an, nguoi_dung=nguoi)

        # §6 dòng cuối: "Nâng phiên bản khối thư viện — như 'đổi Port' nếu manifest Port đổi;
        # như 'nội bộ' nếu chỉ đổi bên trong." Đây là chỗ quyết định STALE lan tới đâu.
        p_cu = _chu_ky_port(cu) if cu else []
        p_moi = _chu_ky_port(moi)
        doi_port = p_cu != p_moi
        return {"khoi": khoi, "tu": dung["ma"], "den": moi.ma, "doi_port": doi_port,
                "port_cu": p_cu, "port_moi": p_moi,
                "note_vi": (f"{cau}. "
                            + ("Port ĐỔI — nâng phiên bản này lan STALE ra cha và các khối "
                               "anh em nối vào (§6). Gọi khoi.place lại với tham số để đặt "
                               "bản mới."
                               if doi_port else
                               "Port KHÔNG đổi — đây là thay đổi nội bộ khối, bên ngoài "
                               "không phải cập nhật gì. Gọi khoi.place lại để đặt bản mới.")),
                "buoc_tiep": "khoi.place"}

    return r


# --------------------------------------------------------------------------- phụ trợ
def _chu_ky_port(k: KTV.Khoi) -> list[str]:
    """Chữ ký Port của một khối — thứ quyết định nâng phiên bản có lan STALE hay không."""
    return sorted(f"{p.get('ten')}:{p.get('huong')}:{p.get('loai') or 'single'}"
                  for p in k.port)


def _cap_ref_moi(ctx: Any, la: list[dict[str, Any]]
                 ) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Đổi ref đã có người dùng sang ref còn trống. Trả `(lá đã đổi, ánh xạ cũ→mới)`.

    Giữ TIỀN TỐ chữ (`R8` → `R12`, không phải `R8_2`): tiền tố là thứ KiCad và người đọc BOM
    dùng để biết linh kiện loại gì, và một ref lạ dạng `R8_2` sẽ làm KiCad tự đánh số lại rồi
    mất liên kết với netlist.
    """
    dang_co = {(n["canonical"].get("ref") or n["ten"])
               for n in ctx.store.ckm_cac_nut(loai="linh_kien")}
    dang_co |= {(n["canonical"].get("ref") or n["ten"])
                for n in ctx.store.ckm_cac_nut(loai="chip")}
    a = ctx.store.get(K.MA_NETLIST)
    if a:
        dang_co |= {str(x.get("ref")) for x in (a["canonical"].get("linh_kien") or [])
                    if x.get("ref")}

    ra: list[dict[str, Any]] = []
    anh_xa: dict[str, str] = {}
    for x in la:
        ref = str(x.get("ref") or "")
        if ref and ref in dang_co:
            moi = _ref_trong(ref, dang_co)
            anh_xa[ref] = moi
            x = {**x, "ref": moi, "ref_trong_khoi": ref}
            ref = moi
        dang_co.add(ref)
        ra.append(x)
    return ra, anh_xa


def _ref_trong(ref: str, dang_co: set[str]) -> str:
    tien_to = "".join(c for c in ref if c.isalpha()) or "U"
    i = 1
    while f"{tien_to}{i}" in dang_co:
        i += 1
    return f"{tien_to}{i}"


def _fact_cua_la(ctx: Any, cay: Any, trong: set[str]) -> list[dict[str, Any]]:
    """Fact của các lá trong khối, KÈM nguồn — §5: "Fact kèm nguồn (datasheet của lá)".

    Không có phần này thì khối đem sang dự án khác mất hết chỗ dựa: người nhận thấy một điện
    trở 4,7 kΩ mà không biết vì sao là 4,7 chứ không phải 10.

    Tra theo **cả ref và TÊN CHIP**. Fact chân do `fact.extract` ghi dưới tên chip
    (`pin:AMS1117.1` — Fact của một *loại* chip), còn lá trong cây mang ref (`U3`). Tra chỉ
    theo ref thì khối đóng gói xong có **0 Fact** mà vẫn báo thành công — và đây là lần thứ
    ba cùng một chỗ lẫn ref với tên chip gây lỗi (xem DEV-267, DEV-269).
    """
    from ..knowledge import erc as ERC

    ra: list[dict[str, Any]] = []
    da: set[str] = set()
    for nid in sorted(trong):
        n = cay.nut.get(nid) or {}
        if n.get("kind") != "leaf":
            continue
        ten_chip = n["canonical"].get("ten") or n["ten"]
        for ct in ERC.chu_the_la(n) + [ten_chip]:
            for f in (ctx.store.query_facts(subject=f"pin:{ct}.", limit=200)
                      + ctx.store.query_facts(subject=ct, limit=50)):
                if f["fact_id"] in da:
                    continue
                da.add(f["fact_id"])
                ra.append(dict(f))
    return ra


def _ghi_linh_kien(ctx: Any, la: list[dict[str, Any]], explain: dict[str, Any]) -> None:
    """Lá của khối vào `netlist:CKM` dưới dạng linh kiện, để `flatten` và BOM thấy chúng."""
    a = ctx.store.get(K.MA_NETLIST)
    canon = dict(a["canonical"]) if a else {"nguon": "CKM", "net": [], "linh_kien": []}
    theo = {x.get("ref"): x for x in (canon.get("linh_kien") or []) if x.get("ref")}
    for x in la:
        theo[x["ref"]] = {"ref": x["ref"], "ten": x.get("ten", ""),
                          "gia_tri": x.get("gia_tri", ""), "tier": "VANG",
                          "nguon": "khối thư viện"}
    canon["linh_kien"] = sorted(theo.values(), key=lambda z: str(z.get("ref")))
    ctx.store.apply(artefact_id=K.MA_NETLIST, type="netlist",
                    op="update" if a else "create", author=f"agent:{ctx.run_id}",
                    canonical=canon, explain=explain)


def _ghi_fact(ctx: Any, k: KTV.Khoi, kq: KTV.KetQuaDat) -> int:
    """Fact của khối vào kho, KÈM NGUỒN. Giá trị dẫn xuất ghi cả công thức."""
    n = 0
    for f in k.fact:
        if not f.get("subject") or not f.get("key"):
            continue
        ctx.store.put_fact({**f, "fact_id": f.get("fact_id")
                            or f"f-khoi-{k.ten}-{f['subject']}-{f['key']}"})
        n += 1
    for ten, g in kq.dan_xuat.items():
        ctx.store.put_fact({
            "fact_id": f"f-khoi-{k.ten}-{ten}", "subject": f"khoi:{k.ma}", "key": ten,
            "value": g.gia_tri, "unit": g.don_vi, "tier": g.tier, "origin": "extract",
            "source": {"cong_thuc": g.cong_thuc, "tham_so": g.tham_so, "nguon": g.nguon},
            "explain": {"summary": g.cau_vi(),
                        "why": f"tham số dẫn xuất của khối {k.ma}",
                        "sources": [{"kind": "cong_thuc", "ref": g.cong_thuc,
                                     "tier": g.tier}],
                        "diff_prev": "bản đầu tiên",
                        "next": "—", "confidence": g.tier}})
        n += 1
    return n
