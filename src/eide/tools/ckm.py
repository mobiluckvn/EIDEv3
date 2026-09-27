# -*- coding: utf-8 -*-
"""Công cụ dựng Bản đồ tri thức mạch — EIDE-MDD-40 §C2, tiền đề của EIDE-SCH-44 §4.

Bảy công cụ, và trật tự giữa chúng là trật tự tự nhiên của việc thiết kế mạch:

    passport.pin ──► ckm.chip_add ──► ckm.pinout_set ──┐
    ckm.module_set ──────────────────────────────────┬─┴─► ckm.build ──► (sch.compose)
    ckm.net_set / ckm.import_netlist ────────────────┘
    ckm.graph, diagram.render: đọc — gọi lúc nào cũng được

KHÔNG có planner xếp trật tự đó (§B1). Mỗi công cụ tự kiểm tiền đề của mình và khi thiếu
thì trả lỗi NÓI RA gọi gì trước. Đó là toàn bộ cơ chế: mô hình đi sai thứ tự sẽ nhận một
câu chỉ đường, không phải một sự cố.

Mọi công cụ ghi ở đây làm đúng hai việc, theo đúng thứ tự này:
  1. ghi HIỆN VẬT qua `history.ghi_kho` — có changeset, hoàn tác được (N9), có STALE;
  2. gọi `ckm.chieu()` dựng lại đồ thị từ hiện vật.
Không công cụ nào ghi thẳng vào `ckm_nodes/ckm_edges`. Lý do dài hơn ở `knowledge/ckm.py`.

Một điều cố ý KHÔNG làm: không có `ckm.pinout_auto` gán cả loạt chân theo phỏng đoán.
Gán chân là quyết định thiết kế có hậu quả vật lý, và §C2 ghi ĐƯỢC_GÁN là quan hệ *duy
nhất* — tức mỗi lần gán là một lần loại trừ mọi khả năng khác của chân đó. Việc đó đi
từng chân, có Fact, và người thấy được.
"""

from __future__ import annotations

from typing import Any

from ..errors import EideError
from ..knowledge import cay as KC
from ..knowledge import ckm as K
from ..protocol import uicommand as uic
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA


def _ten_chip(chip: str) -> str:
    """Tên chip như người gọi nó. Hộ chiếu là `ns.part@semver`; chân thì theo tên trần."""
    return chip.split("@", 1)[0].split(":")[-1]


def _chan_co_san(ctx: Any, ten: str) -> dict[str, K.ChanCKM]:
    """Bảng chân của chip từ Fact. Mã đọc Fact; mô hình không đưa chân vào đây."""
    return K.chan_tu_fact(ctx.store.query_facts(subject=f"pin:{ten}.", limit=2000), ten)


def _loi(kq: K.KetQuaKiem, *, goi_thay: list[str]) -> ToolResult:
    return ToolResult(False, error=EideError(
        kq.ma_loi or "E8003", kq.vi, hint_for_agent=kq.goi_y,
        alternatives=goi_thay, details=kq.chi_tiet, blame="agent"))


def _ho_chieu_cua(ctx: Any, chip: str) -> str:
    """Mã hộ chiếu của một chip, tra theo TÊN chip.

    Không tra bằng `store.get(chip)`: `passport.pin` ghi hiện vật dưới mã `ns.part@semver`
    (ví dụ `atmel.atmega328p@1.0.0`), nên tra theo id chỉ trúng khi người gọi tình cờ
    truyền đúng mã đó. Ca đo bắt được: ghim hộ chiếu xong, `ckm.build` vẫn báo "thiếu hộ
    chiếu" — một lời từ chối đúng luật nhưng sai sự thật, tức loại tệ nhất.
    """
    if ctx.store.get(chip) is not None:
        return chip
    ten = _ten_chip(chip).strip().lower()
    for a in ctx.store.list(type="passport", limit=200):
        if str(a["canonical"].get("chip", "")).strip().lower() == ten:
            return a["id"]
    return ""


def _nut_la(ctx: Any, ref: str) -> str | None:
    """node_id của lá theo ref. Chip vào bản đồ dưới `chip:<ref>`, linh kiện chỉ netlist
    biết thì dưới `linh_kien:<ref>` — hai tiền tố, một ref."""
    for tt in ("chip:", "linh_kien:"):
        if ctx.store.ckm_nut(tt + ref) is not None:
            return tt + ref
    return None


def _ghi_stale_nut(ctx: Any, *, loai: str, muc_tieu: str, ly_do: str,
                   net_lien_quan: str = "") -> dict[str, Any]:
    """Tính STALE theo cây rồi ghi vào hiện vật sơ đồ khối. Trả phần vừa thêm.

    Ghi vào `MG-1` chứ không gọi `store.mark_stale`: STALE của cây là **theo NÚT**, còn
    `mark_stale` làm việc theo hiện vật — và cả cây nằm trong một hiện vật. Xem ghi chú dài
    ở `knowledge/cay.py` về lý do không tách mỗi khối một hiện vật.

    Ghi bằng `store.apply` chứ không `history.ghi_kho`: đây không phải một thay đổi mới của
    người hay tác tử, nó là **hệ quả** của changeset vừa ghi. Sinh thêm một changeset ở đây
    sẽ làm lịch sử có hai dòng cho một việc.
    """
    a = ctx.store.get(K.MA_DO_THI)
    if a is None:
        return {}
    cay = KC.Cay.doc(ctx.store)
    if KC.tim_nut(cay, muc_tieu) is None:
        # Nút chưa vào cây (ví dụ gán chân cho một ref chưa có trong bản đồ): không có gì
        # để lan. `lan_stale` cố ý NỔ với id lạ, nên phải hỏi trước thay vì bắt ngoại lệ —
        # bắt ngoại lệ ở đây sẽ che luôn những id lạ do lỗi lập trình.
        return {}
    lan = KC.lan_stale(cay, loai=loai, muc_tieu=muc_tieu, ly_do=ly_do,
                       net_lien_quan=net_lien_quan)
    if not lan.stale and not lan.chi_bao_tin:
        return {}
    canon = dict(a["canonical"])
    nut = dict(canon.get("stale_nut") or {})
    nut.update(lan.stale)
    tin = dict(canon.get("con_da_doi") or {})
    tin.update(lan.chi_bao_tin)
    # Nút vừa được cập nhật thì thôi mang cờ "con đã đổi" — nếu không, cờ cũ đọng lại và
    # người thấy một thông tin về một việc đã xong.
    for k in lan.stale:
        tin.pop(k, None)
    canon["stale_nut"], canon["con_da_doi"] = nut, tin
    ctx.store.apply(artefact_id=K.MA_DO_THI, type="block_diagram", op="update",
                    author=f"agent:{ctx.run_id}", canonical=canon,
                    explain=a["explain"], view_hint=a.get("view_hint"))
    return lan.to_dict()


def _bang_gan(ctx: Any, ref: str) -> list[dict[str, Any]]:
    """Bảng gán chân hiện tại của MỘT linh kiện (theo ref), đọc từ hiện vật pinout."""
    a = ctx.store.get(K.ma_pinout(ref))
    return list(a["canonical"].get("gan") or []) if a else []


def _tim_linh_kien(ctx: Any, chip: str) -> tuple[str, str, ToolResult | None]:
    """`chip` người gọi đưa có thể là REF (U1) hay TÊN CHIP (ATmega328P). Trả (ten, ref).

    Bo mạch có thể có hai con cùng loại. Khi đó tên chip KHÔNG đủ để biết đang nói con
    nào, và đoán hộ là gán chân cho con sai — một lỗi không hiện ra ở đâu cho tới lúc
    hàn. Nên chỗ mơ hồ thì HỎI, và nói rõ có những con nào.
    """
    nuts = ctx.store.ckm_cac_nut(loai="chip")
    theo_ref = {n["canonical"].get("ref"): n for n in nuts if n["canonical"].get("ref")}
    if chip in theo_ref:
        n = theo_ref[chip]
        return n["ten"], chip, None
    cung_loai = [n for n in nuts if n["ten"] == chip]
    if len(cung_loai) == 1:
        return chip, cung_loai[0]["canonical"].get("ref") or chip, None
    if len(cung_loai) > 1:
        refs = sorted(n["canonical"].get("ref", "") for n in cung_loai)
        return chip, "", ToolResult(False, error=EideError(
            "E8008",
            f"Bo mạch có {len(cung_loai)} con {chip}: {', '.join(refs)}. Chân của con nào?",
            hint_for_agent=("Truyền ref (U1, U2…) vào tham số chip thay vì tên chip. Nếu "
                            "bạn không biết người dùng muốn con nào thì hỏi họ — gán chân "
                            "cho con sai là lỗi chỉ lộ ra lúc hàn."),
            alternatives=["ckm.graph", "ask_user"], details={"ref": refs}, blame="agent"))
    # Chưa có trong bản đồ: coi tên là cả tên lẫn ref (một con duy nhất).
    return chip, chip, None


def register(r: Registry) -> Registry:

    # ====================================================================== chip & chân
    @r.tool("ckm.chip_add", "Thiết kế",
            "Đưa một chip và bảng chân của nó vào Bản đồ tri thức mạch. Chân lấy từ Fact "
            "đã có trong kho — công cụ này KHÔNG tạo chân, nên nếu chưa nạp bảng chân thì "
            "nó nói thẳng là chưa có gì để đưa vào.",
            {"type": "object",
             "properties": {
                 "chip": {"type": "string", "description": "Tên chip, hoặc mã hộ chiếu"},
                 "ref": {"type": "string",
                         "description": "Ký hiệu trên sơ đồ (U1, U2…) nếu đã biết"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["chip", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["ckm"],
            keywords=["chip", "chân", "pin", "ckm", "bản đồ mạch", "thêm chip"])
    def chip_add(ctx: Any, chip: str, explain: dict[str, Any], ref: str = ""):
        ten = _ten_chip(chip)
        ref = ref or ten
        chan = _chan_co_san(ctx, ten)
        if not chan:
            return ToolResult(False, error=EideError(
                "E8002",
                f"Chưa có Fact chân nào cho {ten}. Đưa chip vào bản đồ mà không có chân "
                "thì bản đồ chỉ có một cái tên và không tra được gì.",
                hint_for_agent=(
                    "Chân đến từ bảng chân của datasheet: doc.load → fact.extract → "
                    f"fact.review. Nếu người dùng đọc datasheet và nói cho bạn từng chân, "
                    f"ghi bằng fact.assert_human với subject 'pin:{ten}.<số>' và key 'ten' "
                    "hoặc 'af'."),
                alternatives=["doc.load", "fact.extract", "fact.assert_human", "ask_user"],
                details={"chu_de_can": f"pin:{ten}.<số chân>"}, blame="agent"))

        # Chân chỉ có ở tầng ĐỒNG/CẤU HÌNH không vào bản đồ — nhưng phải NÓI RA là đã bỏ,
        # chứ không im lặng để bản đồ thiếu chân mà trông như đủ.
        nhan, bo_qua = [], []
        for so, c in sorted(chan.items()):
            if c.tier and c.tier.upper() not in K.TANG_THIET_KE:
                bo_qua.append(f"{so} (tầng {c.tier})")
            else:
                nhan.append(c.to_dict())

        hc = _ho_chieu_cua(ctx, chip)
        ma = K.ma_chip(ref)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=ma, type="ckm",
            op="update" if ctx.store.get(ma) else "create",
            canonical={"chip": ten, "ref": ref, "ho_chieu": hc,
                       "chan": nhan, "chan_bo_qua": bo_qua},
            explain=explain, run_id=ctx.run_id)
        K.chieu(ctx.store)
        return {
            "chip": ten, "ref": ref, "so_chan_vao_ban_do": len(nhan), "chan_bo_qua": bo_qua,
            "co_ho_chieu": bool(hc), "ho_chieu": hc, "changeset": cs.id,
            "note_vi": (f"Đã đưa {ten} ({ref}) vào bản đồ với {len(nhan)} chân."
                        + (f" BỎ QUA {len(bo_qua)} chân vì chỉ có ở tầng phỏng đoán: "
                           + ", ".join(bo_qua[:6]) + ". Nói cho người dùng biết."
                           if bo_qua else "")
                        + ("" if hc else " Chip này CHƯA có hộ chiếu — gọi passport.pin "
                                         "để ghim, nếu không thì sinh sơ đồ sẽ thiếu tiền đề.")),
        }

    # ====================================================================== sơ đồ khối
    @r.tool("ckm.module_set", "Thiết kế",
            "Ghi một KHỐI của mạch: nó làm gì, gồm linh kiện nào, nhận tín hiệu gì và ra "
            "tín hiệu gì. Gọi nhiều lần, mỗi khối một lần. Mã tự nối các khối theo tên "
            "tín hiệu và tự vẽ sơ đồ — bạn không cần vẽ mũi tên.",
            {"type": "object",
             "properties": {
                 "ma": {"type": "string", "description": "MOD-PWR, MOD-I2C…"},
                 "ten": {"type": "string"},
                 "muc_dich": {"type": "string", "description": "Khối này để làm gì, một câu"},
                 "linh_kien": {"type": "array", "items": {"type": "string"},
                               "description": "Ref hoặc tên linh kiện trong khối"},
                 "tin_hieu_vao": {"type": "array", "items": {"type": "string"},
                                  "description": "Tên tín hiệu/net đi VÀO khối"},
                 "tin_hieu_ra": {"type": "array", "items": {"type": "string"}},
                 "rail": {"type": "string", "description": "Nguồn cấp cho khối: 3V3, 5V…"},
                 "dap_ung_req": {"type": "array", "items": {"type": "string"},
                                 "description": "Mã REQ mà khối này thực hiện"},
                 "cha": {"type": "string",
                         "description": "Mã khối CHA nếu đây là khối con (để rỗng = khối "
                                        "cấp một của mạch). Mạch là một CÂY: khối trong khối."},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ma", "ten", "muc_dich", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            produces=["block_diagram"],
            keywords=["khối", "module", "sơ đồ khối", "kiến trúc mạch", "phân rã",
                      "block", "decompose"])
    def module_set(ctx: Any, ma: str, ten: str, muc_dich: str, explain: dict[str, Any],
                   linh_kien: list[str] | None = None,
                   tin_hieu_vao: list[str] | None = None,
                   tin_hieu_ra: list[str] | None = None, rail: str = "",
                   dap_ung_req: list[str] | None = None, cha: str = ""):
        cu = ctx.store.get(K.MA_DO_THI)
        ds_cu = [K.Module.from_dict(d) for d in (cu["canonical"].get("khoi") if cu else [])]
        if cha:
            if cha == ma:
                return ToolResult(False, error=EideError(
                    "E9001", f"Khối {ma} không thể là cha của chính nó.",
                    hint_for_agent="Bỏ tham số cha, hoặc chỉ đúng khối cha.", blame="agent"))
            if not any(x.ma == cha for x in ds_cu):
                return ToolResult(False, error=EideError(
                    "E2001", f"Chưa có khối nào mã {cha} để làm cha.",
                    hint_for_agent=("Ghi khối cha trước rồi mới ghi khối con — cây dựng từ "
                                    "trên xuống. Khối đang có: "
                                    + (", ".join(x.ma for x in ds_cu) or "chưa có khối nào")),
                    alternatives=["ckm.module_set", "ckm.graph"], blame="agent"))
        m = K.Module(ma=ma, ten=ten, muc_dich=muc_dich, linh_kien=linh_kien or [],
                     tin_hieu_vao=tin_hieu_vao or [], tin_hieu_ra=tin_hieu_ra or [],
                     rail=rail, dap_ung_req=dap_ung_req or [], cha=cha,
                     kind="subblock" if cha else "block")
        ds = list(ds_cu)
        ds = [x for x in ds if x.ma != ma] + [m]
        canh = K.canh_giua_module(ds)
        treo = K.tin_hieu_treo(ds)
        canon = {"so_khoi": len(ds), "khoi": [x.to_dict() for x in sorted(ds, key=lambda z: z.ma)],
                 "canh": canh, "tin_hieu_treo": treo}

        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_DO_THI, type="block_diagram",
            op="update" if cu else "create", canonical=canon, explain=explain,
            run_id=ctx.run_id)
        # Dạng người của cùng dữ liệu, do MÃ sinh (N8, E1). Không vào changeset vì nó
        # không phải thông tin mới — dựng lại được từ canonical bất cứ lúc nào.
        ctx.store.apply(artefact_id=K.MA_DO_THI, type="block_diagram", op="update",
                        author=f"agent:{ctx.run_id}", canonical=canon, explain=explain,
                        view_hint={"kind": "mermaid", "text": K.mermaid(ds, canh),
                                   "bang": K.bang_khoi(ds)})
        K.chieu(ctx.store)

        req_la = [rq for rq in m.dap_ung_req if ctx.store.get(rq) is None]
        nut = ctx.store.ckm_nut(K.ma_module(ma)) or {}
        return {
            "khoi": ma, "so_khoi": len(ds), "changeset": cs.id, "canh_suy_ra": canh,
            "duong": nut.get("path", ""), "kind": nut.get("kind", ""),
            "tin_hieu_treo": treo, "req_khong_co_trong_kho": req_la,
            "note_vi": (f"Khối ở {nut.get('path', '?')}. Bản đồ có {len(ds)} khối, "
                        f"{len(canh)} liên kết suy ra từ tên tín hiệu."
                        + (f" Tín hiệu {', '.join(treo['vao_khong_ai_cap'][:5])} chưa khối "
                           "nào cấp — hoặc còn thiếu khối, hoặc tên tín hiệu lệch nhau."
                           if treo["vao_khong_ai_cap"] else "")
                        + (f" REQ {', '.join(req_la)} không có trong kho — đừng tự tạo, "
                           "hỏi người dùng hoặc gọi store.req_create." if req_la else "")),
        }

    @r.tool("diagram.render", "Thiết kế",
            "Lấy sơ đồ khối để cho người xem: hình mermaid và bảng khối. Mã vẽ, không "
            "phải bạn vẽ — nên hình luôn khớp bản đồ hiện tại.",
            {"type": "object",
             "properties": {"dang": {"type": "string",
                                     "enum": ["mermaid", "bang", "ca_hai"]}},
             "required": []},
            risk="R1", keywords=["vẽ", "sơ đồ", "hình", "render", "diagram", "khối"])
    def diagram_render(ctx: Any, dang: str = "ca_hai"):
        a = ctx.store.get(K.MA_DO_THI)
        ms = [K.Module.from_dict(d) for d in (a["canonical"].get("khoi") if a else [])]
        if not ms:
            # §137 của MDD-40: "render từ chối khi thiếu module_graph và nói gọi gì trước".
            return ToolResult(False, error=EideError(
                "E2001", "Chưa có khối nào trong bản đồ mạch nên không có gì để vẽ.",
                hint_for_agent="Ghi các khối bằng ckm.module_set trước — mỗi khối một lần.",
                alternatives=["ckm.module_set"], blame="agent"))
        canh = K.canh_giua_module(ms)
        ra: dict[str, Any] = {"so_khoi": len(ms), "tin_hieu_treo": K.tin_hieu_treo(ms)}
        if dang in ("mermaid", "ca_hai"):
            ra["mermaid"] = K.mermaid(ms, canh)
        if dang in ("bang", "ca_hai"):
            ra["bang"] = K.bang_khoi(ms)
        # Không tự vẽ lên tab: tab Thiết kế dựng từ kho ở cuối mỗi lượt (`surfaces.design`).
        # Một công cụ đọc mà cũng đẩy hình lên tab thì sẽ có hai đường vẽ cùng một thứ, và
        # sớm muộn hai đường đó lệch nhau.
        return ra

    @r.tool("ckm.port_set", "Thiết kế",
            "Khai một PORT ở biên một khối — tức hợp đồng của khối với bên ngoài: tên, "
            "hướng (vào/ra/hai chiều/nguồn), và ràng buộc. Chỉ khối mới cần khai Port; "
            "Port của linh kiện là chân của nó, sinh sẵn từ Fact.",
            {"type": "object",
             "properties": {
                 "khoi": {"type": "string", "description": "Mã khối (MOD-MCU…)"},
                 "ten": {"type": "string", "description": "Tên Port: VDD, I2C0, ALERT…"},
                 "huong": {"type": "string", "enum": list(KC.HUONG),
                           "description": "power_in = khối NHẬN nguồn; power_out = khối CẤP"},
                 "loai": {"type": "string", "enum": list(KC.LOAI_PORT)},
                 "members": {"type": "array", "items": {"type": "string"},
                             "description": "Với bus: tên các tín hiệu thành viên (SDA, SCL)"},
                 "rang_buoc": {"type": "object",
                               "description": "v_min/v_max/i_max/level — số nào cũng phải "
                                              "có nguồn, đừng đoán"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["khoi", "ten", "huong", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["block_diagram"],
            keywords=["port", "biên khối", "hợp đồng", "chân khối", "giao tiếp"])
    def port_set(ctx: Any, khoi: str, ten: str, huong: str, explain: dict[str, Any],
                 loai: str = "single", members: list[str] | None = None,
                 rang_buoc: dict[str, Any] | None = None):
        a = ctx.store.get(K.MA_DO_THI)
        ds = [K.Module.from_dict(d) for d in (a["canonical"].get("khoi") if a else [])]
        m = next((x for x in ds if x.ma == khoi), None)
        if m is None:
            return ToolResult(False, error=EideError(
                "E2001", f"Chưa có khối nào mã {khoi}.",
                hint_for_agent="Ghi khối bằng ckm.module_set trước khi khai biên của nó. "
                               "Khối đang có: " + (", ".join(x.ma for x in ds) or "chưa có"),
                alternatives=["ckm.module_set", "ckm.graph"], blame="agent"))
        if loai == "bus" and not (members or []):
            return ToolResult(False, error=EideError(
                "E9005", f"Port bus {ten} phải nói rõ gồm những tín hiệu nào.",
                hint_for_agent="Truyền members, ví dụ [\"SDA\", \"SCL\"]. Một bus không "
                               "kể thành viên thì hai đầu không kiểm khớp được.",
                blame="agent"))

        # Port nằm trong HIỆN VẬT sơ đồ khối, không ghi thẳng vào bảng `ckm_port` — bảng đó
        # là hình chiếu. Cùng lý do với mọi thứ khác của bản đồ: hoàn tác phải lùi được.
        canon = dict(a["canonical"]) if a else {"so_khoi": len(ds), "khoi": []}
        khoi_moi = []
        for x in ds:
            d = x.to_dict()
            if x.ma == khoi:
                ps = [p for p in (d.get("port") or []) if p.get("ten") != ten]
                ps.append({"ten": ten, "huong": huong, "loai": loai,
                           "members": list(members or []),
                           "rang_buoc": dict(rang_buoc or {})})
                d["port"] = sorted(ps, key=lambda z: str(z.get("ten")))
            khoi_moi.append(d)
        canon["khoi"], canon["so_khoi"] = khoi_moi, len(khoi_moi)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_DO_THI, type="block_diagram",
            op="update", canonical=canon, explain=explain, run_id=ctx.run_id)
        K.chieu(ctx.store)

        lan = _ghi_stale_nut(ctx, loai="port", muc_tieu=K.ma_module(khoi),
                             ly_do=f"{cs.id} (Port {ten} của khối {khoi} đổi)")
        nut = ctx.store.ckm_nut(K.ma_module(khoi)) or {}
        sv = ctx.store.ckm_cac_port(module_id=K.ma_module(khoi))
        return {"khoi": khoi, "port": ten, "huong": huong, "so_port": len(sv),
                "changeset": cs.id, "duong": nut.get("path", ""),
                "stale_theo_nut": lan.get("stale", {}),
                "note_vi": (f"Khối {khoi} giờ có {len(sv)} Port: "
                            + ", ".join(f"{p['ten']}({p['huong']})" for p in sv)
                            + ". Port là hợp đồng — sửa ruột khối mà không đổi Port thì "
                              "bên ngoài không phải cập nhật gì."
                            + (" Đổi Port thì CÓ lan: "
                               + ", ".join(sorted(lan.get("stale", {})))
                               + " cần xem lại (§6)." if lan.get("stale") else ""))}

    # ====================================================================== pinout
    @r.tool("ckm.pinout_set", "Thiết kế",
            "Gán MỘT chân của chip cho MỘT chức năng. Chân phải có trong Fact đã nạp — "
            "công cụ từ chối chân không có trong bảng chân, và từ chối gán lại một chân "
            "đã gán. Mỗi lần gán là một quyết định thiết kế, nên đi từng chân.",
            {"type": "object",
             "properties": {
                 "chip": {"type": "string"},
                 "chan": {"type": "string",
                          "description": "Số hoặc tên chân, đúng như datasheet"},
                 "chuc_nang": {"type": "string",
                               "description": "I2C1_SDA, ADC1_IN3, GPIO_OUT…"},
                 "net": {"type": "string", "description": "Net nối vào chân này, nếu đã biết"},
                 "thay_the": {"type": "boolean",
                              "description": "true = cố ý gán lại chân đã gán. Phải kèm vi_sao."},
                 "vi_sao": {"type": "string", "description": "Vì sao gán lại"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["chip", "chan", "chuc_nang", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["pinout"],
            keywords=["pinout", "gán chân", "chân", "pin", "af", "chức năng chân"])
    def pinout_set(ctx: Any, chip: str, chan: str, chuc_nang: str, explain: dict[str, Any],
                   net: str = "", thay_the: bool = False, vi_sao: str = ""):
        ten, ref, loi = _tim_linh_kien(ctx, _ten_chip(chip))
        if loi is not None:
            return loi
        co_san = _chan_co_san(ctx, ten)
        kq = K.kiem_chan(chan, co_san, chip=ten)
        if not kq.dat:
            return _loi(kq, goi_thay=["fact.query", "fact.extract", "fact.assert_human",
                                      "ask_user"])
        c = co_san[chan]
        kq_af = K.kiem_af(chuc_nang, c)
        if not kq_af.dat:
            return _loi(kq_af, goi_thay=["fact.query", "ask_user"])

        gan = _bang_gan(ctx, ref)
        cu = next((g for g in gan if g.get("chan") == chan), None)
        if cu and not thay_the:
            return ToolResult(False, error=EideError(
                "E8004",
                f"Chân {chan} của {ten} đã được gán cho {cu.get('chuc_nang')}. Một chân "
                "làm được đúng một chức năng.",
                hint_for_agent=(
                    f"Nếu {chuc_nang} phải nằm ở đây thì {cu.get('chuc_nang')} phải đi chỗ "
                    "khác — đó là một đánh đổi, hỏi người dùng. Khi họ đã quyết, gọi lại "
                    "với thay_the=true và vi_sao."),
                alternatives=["ask_user", "ckm.graph"],
                details={"gan_truoc": cu.get("chuc_nang"), "chan": chan,
                         "af_con_lai": [a for a in c.af
                                        if a.strip().lower()
                                        != str(cu.get("chuc_nang", "")).strip().lower()]},
                blame="agent"))
        if cu and not vi_sao.strip():
            return ToolResult(False, error=EideError(
                "E8004", f"Gán lại chân {chan} thì phải nói vì sao.",
                hint_for_agent="Người đọc lịch sử sau này cần biết vì sao chân đổi chức "
                               "năng. Truyền vi_sao.", blame="agent"))

        moi = {"chan": chan, "chuc_nang": chuc_nang, "net": net, "tier": c.tier,
               "fact_id": c.fact_id, "vi_sao": vi_sao,
               "af_kiem_duoc": bool(kq_af.chi_tiet.get("kiem_duoc", False))}
        gan = [g for g in gan if g.get("chan") != chan] + [moi]
        gan.sort(key=lambda g: str(g.get("chan")))

        ma = K.ma_pinout(ref)
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=ma, type="pinout",
            op="update" if ctx.store.get(ma) else "create",
            canonical={"chip": ten, "ref": ref, "so_gan": len(gan), "gan": gan},
            explain=explain, run_id=ctx.run_id)
        K.chieu(ctx.store)
        nid_la = _nut_la(ctx, ref)
        lan = (_ghi_stale_nut(ctx, loai="fact_la", muc_tieu=nid_la,
                              ly_do=f"{cs.id} (gán chân {chan} của {ref})")
               if nid_la else {})

        canh_bao = []
        if not moi["af_kiem_duoc"]:
            canh_bao.append(kq_af.chi_tiet.get("vi", ""))
        if c.tier == "NGUOI":
            canh_bao.append(f"Chân {chan} dựa trên lời người dùng, chưa có tài liệu.")
        for cb in canh_bao:
            ctx.emit(uic.notice(cb, level="warn", code="CKM-02"))
        return {"chip": ten, "ref": ref, "chan": chan, "chuc_nang": chuc_nang,
                "tier_chan": c.tier, "stale_theo_nut": lan.get("stale", {}),
                "so_chan_da_gan": len(gan), "changeset": cs.id, "canh_bao": canh_bao,
                "note_vi": (f"Đã gán {ref}.{chan} ({ten}) → {chuc_nang}"
                            + (f" (thay cho {cu.get('chuc_nang')}: {vi_sao})" if cu else "")
                            + ". " + " ".join(canh_bao)).strip()}

    # ====================================================================== net
    @r.tool("ckm.net_set", "Thiết kế",
            "Ghi một NET của mạch: tên, loại, điện áp danh định, và những chân nó nối. "
            "Nếu chân thuộc một chip đã có trong bản đồ thì chân đó phải tồn tại thật.",
            {"type": "object",
             "properties": {
                 "ten": {"type": "string", "description": "SDA, VDD_3V3, GND…"},
                 "loai": {"type": "string", "enum": list(K.LOAI_NET)},
                 "ap_danh_dinh": {"type": "string",
                                  "description": "3.3 V, 5 V… nếu là nguồn"},
                 "chan": {"type": "array",
                          "items": {"type": "array", "items": {"type": "string"}},
                          "description": 'Cặp [ref, chân]: [["U1","27"],["U2","5"]]'},
                 "bus": {"type": "string", "description": "Thuộc bus nào: I2C1, SPI2…"},
                 "trong_khoi": {"type": "string",
                                "description": "Mã khối SỞ HỮU net này (để rỗng = net của "
                                               "cả mạch). Net chỉ nối được Port của khối "
                                               "con TRỰC TIẾP — dây không đi xuyên cấp."},
                 "noi_port": {"type": "array", "items": {"type": "array",
                                                        "items": {"type": "string"}},
                              "description": 'Cặp [mã khối, tên Port]: [["MOD-MCU","VDD"]]'},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ten", "loai", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["netlist"],
            keywords=["net", "nối", "dây", "netlist", "bus", "nguồn", "rail"])
    def net_set(ctx: Any, ten: str, loai: str, explain: dict[str, Any],
                ap_danh_dinh: str = "", chan: list[list[str]] | None = None,
                bus: str = "", trong_khoi: str = "",
                noi_port: list[list[str]] | None = None):
        cap = [(str(x[0]), str(x[1])) for x in (chan or []) if len(x) >= 2]

        # Chân của chip đã có trong bản đồ thì phải tồn tại thật. Chân của linh kiện thụ
        # động (R, C) không có bảng chân nào — không chặn, nhưng nói rõ là KHÔNG kiểm
        # được, chứ không để người đọc hiểu là đã kiểm và đạt (N6).
        theo_ref: dict[str, str] = {}
        for n in ctx.store.ckm_cac_nut(loai="chip"):
            theo_ref[n["canonical"].get("ref") or n["ten"]] = n["ten"]
        khong_kiem_duoc: list[str] = []
        for ref, so in cap:
            ten_chip = theo_ref.get(ref)
            if ten_chip is None:
                khong_kiem_duoc.append(f"{ref}.{so}")
                continue
            kq = K.kiem_chan(so, _chan_co_san(ctx, ten_chip), chip=ten_chip)
            if not kq.dat:
                return _loi(kq, goi_thay=["ckm.graph", "fact.query", "ask_user"])

        a = ctx.store.get(K.MA_NETLIST)
        canon = dict(a["canonical"]) if a else {"nguon": "CKM", "net": [], "linh_kien": []}
        nets = [n for n in (canon.get("net") or []) if n.get("ten") != ten]
        nets.append({"ten": ten, "loai": loai, "ap_danh_dinh": ap_danh_dinh, "bus": bus,
                     "chan": [f"{r}.{p}" for r, p in cap], "tier": "NGUOI",
                     "trong_khoi": trong_khoi,
                     "noi_port": [[str(x[0]), str(x[1])] for x in (noi_port or [])
                                  if len(x) >= 2]})
        nets.sort(key=lambda n: str(n.get("ten")))
        canon["net"], canon["so_net"], canon["nguon"] = nets, len(nets), "CKM"

        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_NETLIST, type="netlist",
            op="update" if a else "create", canonical=canon, explain=explain,
            run_id=ctx.run_id)
        K.chieu(ctx.store)

        canh_bao = []
        if not cap:
            canh_bao.append(f"Net {ten} chưa nối chân nào.")
        elif len(cap) == 1:
            canh_bao.append(f"Net {ten} chỉ nối MỘT chân — gần như luôn là lỗi vẽ.")
        if khong_kiem_duoc:
            canh_bao.append("KHÔNG kiểm được chân " + ", ".join(khong_kiem_duoc[:6])
                            + " vì linh kiện đó chưa có bảng chân trong bản đồ.")
        for cb in canh_bao:
            ctx.emit(uic.notice(cb, level="warn", code="CKM-01"))
        return {"net": ten, "so_chan": len(cap), "so_net": len(nets),
                "changeset": cs.id, "canh_bao": canh_bao,
                "note_vi": " ".join(canh_bao) or f"Đã ghi net {ten} với {len(cap)} chân."}

    @r.tool("ckm.from_pinout", "Thiết kế",
            "Dựng bản đồ mạch TỪ Fact chân đã trích: mỗi giá trị `net` thành một net, mỗi "
            "`khoi` thành một khối, chân vi điều khiển thành đầu nối. MÃ dựng, không phải bạn "
            "chép tay — bạn chỉ rà lại kết quả.",
            {"type": "object",
             "properties": {
                 "chip": {"type": "string", "description": "ATmega328P"},
                 "ref": {"type": "string", "description": "U1 — mã linh kiện trên bo"},
                 "xem_truoc": {"type": "boolean",
                               "description": "true = chỉ xem sẽ dựng gì, chưa ghi"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["chip", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            produces=["netlist", "block_diagram"],
            keywords=["dựng bản đồ", "từ bản đồ chân", "net từ fact", "khối", "ckm"])
    def from_pinout(ctx: Any, chip: str, explain: dict[str, Any], ref: str = "",
                    xem_truoc: bool = False):
        """Vì sao việc này phải do MÃ làm, bằng hai lần chạy thật của cùng một câu hỏi.

        Bảng bản đồ chân đã nằm trong kho dưới dạng Fact: `pin:ATmega328P.D4` có `net=DIR1`,
        `khoi=A4988 #1`, `huong=ra`. Dựng bản đồ mạch từ đó là một phép biến đổi xác định.
        Nhưng khi giao cho mô hình chép 14 net bằng 14 lời gọi `ckm.net_set`, hai lần chạy
        cùng một câu cho ra **14/14 đúng** và **0/14 đúng** — lần thứ hai nó bỏ dở giữa
        chừng. Một bước xác định mà kết quả phụ thuộc vào lượt chạy là một bước đặt sai chỗ.

        Mô hình vẫn còn việc ở đây, và là việc chỉ nó làm được: đọc kết quả, thấy khối nào
        đặt tên vô lý, chân nào tài liệu ghi thiếu, rồi sửa bằng `ckm.module_set`/`net_set`.
        """
        ten_chip = _ten_chip(chip)
        ref = ref or "U1"
        fs = ctx.store.query_facts(subject=f"pin:{ten_chip}.", limit=500)
        theo_chan: dict[str, dict[str, str]] = {}
        for f in fs:
            sub = str(f.get("subject", ""))
            so = sub.split(".", 1)[-1].strip()
            if so:
                theo_chan.setdefault(so, {})[str(f.get("key"))] = str(f.get("value") or "")
        co_net = {so: d for so, d in theo_chan.items() if d.get("net")
                  and not d["net"].startswith(("—", "-"))}
        if not co_net:
            return ToolResult(False, error=EideError(
                "E8002",
                f"Không có Fact chân nào của {ten_chip} mang khoá `net`.",
                hint_for_agent=("Trích bản đồ chân trước: doc.load → fact.extract_pinout. "
                                "Nếu tài liệu không có bảng net thì nói với người dùng và "
                                "hỏi họ nối gì vào đâu — đừng tự đặt net."),
                alternatives=["fact.extract_pinout", "doc.read", "ask_user"], blame="agent"))

        # Gom theo net: mỗi net biết chân MCU của nó và khối ở đầu kia.
        net_khoi: dict[str, str] = {}
        net_chan: dict[str, list[str]] = {}
        for so, d in sorted(co_net.items()):
            ten_net = d["net"].strip().replace(" ", "_")
            net_chan.setdefault(ten_net, []).append(so)
            if d.get("khoi") and not net_khoi.get(ten_net):
                net_khoi[ten_net] = d["khoi"].strip()

        def _ma_khoi(ten: str) -> str:
            t = "".join(c if c.isalnum() else "-" for c in ten.upper())
            return "MOD-" + "-".join(x for x in t.split("-") if x)[:24]

        khoi_moi = {}
        for ten_net, k in net_khoi.items():
            if k:
                khoi_moi.setdefault(_ma_khoi(k), {"ten": k, "net": []})["net"].append(ten_net)

        loai_net = {}
        for ten_net in net_chan:
            t = ten_net.upper()
            loai_net[ten_net] = ("power" if any(x in t for x in ("3V3", "5V", "VCC", "VDD"))
                                 else "ground" if "GND" in t
                                 else "clock" if any(x in t for x in ("SCL", "XTAL", "CLK"))
                                 else "signal")

        xem = {"chip": ten_chip, "ref": ref, "so_net": len(net_chan),
               "so_khoi": len(khoi_moi),
               "net": [{"ten": n, "loai": loai_net[n], "chan_mcu": sorted(c),
                        "khoi": net_khoi.get(n, "")} for n, c in sorted(net_chan.items())],
               "khoi": [{"ma": m, "ten": v["ten"], "net": sorted(v["net"])}
                        for m, v in sorted(khoi_moi.items())]}
        if xem_truoc:
            return {**xem, "da_ghi": False,
                    "note_vi": (f"Xem trước: sẽ dựng {len(net_chan)} net và {len(khoi_moi)} "
                                "khối từ bản đồ chân. Chưa ghi gì. Gọi lại với "
                                "xem_truoc=false để ghi.")}

        # Ghi: khối trước (net cần khối tồn tại), rồi net.
        a_mg = ctx.store.get(K.MA_DO_THI)
        mg = dict(a_mg["canonical"]) if a_mg else {"khoi": [], "lien_ket": []}
        da_co = {k.get("ma") for k in (mg.get("khoi") or [])}
        for m, v in sorted(khoi_moi.items()):
            if m in da_co:
                continue
            mg.setdefault("khoi", []).append(
                {"ma": m, "ten": v["ten"],
                 "muc_dich": f"Khối {v['ten']} — dựng từ cột “Net · khối” của bảng bản đồ "
                             "chân trong tài liệu",
                 "linh_kien": [], "tier": "BAC"})
        ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_DO_THI, type="block_diagram",
            op="update" if a_mg else "create", canonical=mg, explain=explain,
            run_id=ctx.run_id)

        a_net = ctx.store.get(K.MA_NETLIST)
        canon = dict(a_net["canonical"]) if a_net else {"nguon": "CKM", "net": [],
                                                        "linh_kien": []}
        cu = {n.get("ten"): n for n in (canon.get("net") or [])}
        for ten_net, chan_mcu in sorted(net_chan.items()):
            cu[ten_net] = {"ten": ten_net, "loai": loai_net[ten_net], "ap_danh_dinh": "",
                           "bus": "", "chan": [f"{ref}.{c}" for c in sorted(chan_mcu)],
                           "tier": "BAC", "trong_khoi": "", "noi_port": [],
                           "khoi_dau_kia": net_khoi.get(ten_net, "")}
        canon["net"] = sorted(cu.values(), key=lambda n: str(n.get("ten")))
        canon["so_net"], canon["nguon"] = len(canon["net"]), "CKM"
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_NETLIST, type="netlist",
            op="update" if a_net else "create", canonical=canon, explain=explain,
            run_id=ctx.run_id)
        K.chieu(ctx.store)

        return {**xem, "da_ghi": True, "changeset": cs.id,
                "note_vi": (
                    f"Đã dựng {len(net_chan)} net và {len(khoi_moi)} khối từ bản đồ chân của "
                    f"{ten_chip} — bằng mã, nên nó khớp bảng trong tài liệu từng dòng. "
                    "CÒN THIẾU và cần bạn làm: mỗi net mới có MỘT đầu là chân vi điều khiển; "
                    "đầu kia là linh kiện trong khối (A4988, MPU6050…) mà tài liệu mô tả ở "
                    "chương riêng. Đọc chương đó rồi thêm linh kiện và Port bằng "
                    "ckm.chip_add/ckm.port_set/ckm.net_set. Tầng của những net này là BẠC: "
                    "trích từ tài liệu nội bộ, chưa ai rà từng dòng.")}

    @r.tool("ckm.import_netlist", "Thiết kế",
            "Đưa một netlist đã đọc (bằng eda.netlist) vào Bản đồ tri thức mạch. Dùng khi "
            "người dùng đã có sơ đồ trong KiCad — khỏi phải khai lại từng net.",
            {"type": "object",
             "properties": {
                 "netlist_id": {"type": "string",
                                "description": "Mã hiện vật netlist trong kho"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["netlist_id", "explain"]},
            risk="R2", writes_artefact=True, needs_explain=True,
            produces=["ckm", "netlist"],
            keywords=["nhập", "import", "netlist", "kicad", "ckm"])
    def import_netlist(ctx: Any, netlist_id: str, explain: dict[str, Any]):
        if netlist_id == K.MA_NETLIST:
            return ToolResult(False, error=EideError(
                "E5001", f"{K.MA_NETLIST} chính là netlist của bản đồ — không nhập vào "
                         "chính nó.",
                hint_for_agent="Truyền mã netlist đọc từ tệp (eda.netlist), ví dụ "
                               "netlist:hw/board.net.",
                alternatives=["store.list", "eda.netlist"], blame="agent"))
        a = ctx.store.get(netlist_id)
        if a is None or a["type"] != "netlist":
            return ToolResult(False, error=EideError(
                "E2001", f"Không có hiện vật netlist nào mã {netlist_id}.",
                hint_for_agent="Đọc netlist bằng eda.netlist trước; hoặc "
                               "store.list(type='netlist') để xem có gì.",
                alternatives=["eda.netlist", "store.list"], blame="agent"))

        nguon = a["canonical"]
        b = ctx.store.get(K.MA_NETLIST)
        canon = dict(b["canonical"]) if b else {"nguon": "CKM", "net": [], "linh_kien": []}
        theo_ten = {n.get("ten"): n for n in (canon.get("net") or [])}
        ghi_de: list[str] = []
        for n in nguon.get("net") or []:
            ten = n.get("ten", "")
            if not ten:
                continue
            if ten in theo_ten:
                ghi_de.append(ten)
            theo_ten[ten] = {"ten": ten, "loai": _doan_loai_net(ten),
                             "loai_do_doan": True,
                             "chan": list(n.get("chan") or []), "tier": "NGUOI",
                             "nguon": netlist_id}
        lk = {l.get("ref"): l for l in (canon.get("linh_kien") or []) if l.get("ref")}
        for l in nguon.get("linh_kien") or []:
            if l.get("ref"):
                lk[l["ref"]] = {**l, "tier": "NGUOI", "nguon": netlist_id}
        canon["net"] = sorted(theo_ten.values(), key=lambda n: str(n.get("ten")))
        canon["so_net"] = len(canon["net"])
        canon["linh_kien"] = sorted(lk.values(), key=lambda l: str(l.get("ref")))

        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_NETLIST, type="netlist",
            op="update" if b else "create", canonical=canon, explain=explain,
            run_id=ctx.run_id)
        K.chieu(ctx.store)
        return {"so_net": len(canon["net"]), "so_linh_kien": len(canon["linh_kien"]),
                "nguon": netlist_id, "net_bi_ghi_de": ghi_de, "changeset": cs.id,
                "note_vi": (f"Đã đưa {len(nguon.get('net') or [])} net và "
                            f"{len(nguon.get('linh_kien') or [])} linh kiện từ {netlist_id} "
                            "vào bản đồ. Loại net (nguồn/đất/tín hiệu) ĐOÁN theo tên net — "
                            "netlist không nói loại, nên chỗ nào quan trọng thì xác nhận "
                            "lại bằng ckm.net_set."
                            + (f" Ghi đè {len(ghi_de)} net đã khai tay: "
                               + ", ".join(ghi_de[:5]) + "." if ghi_de else ""))}

    @r.tool("board.check", "Thiết kế",
            "Kiểm mạch bằng bốn ràng buộc tính được từ Fact: ngân sách dòng theo cây, mức "
            "logic hai đầu net, trùng địa chỉ I2C, pull-up của bus. Mỗi phát hiện nói rõ Ở "
            "KHỐI NÀO. Thiếu Fact thì trả 'chưa đủ dữ kiện' — không đoán.",
            {"type": "object",
             "properties": {
                 "khoi": {"type": "string",
                          "description": "Chỉ xem phát hiện trong một khối (đường dẫn như "
                                         "/board/mcu). Để rỗng = cả mạch."}},
             "required": []},
            risk="R1",
            keywords=["erc", "kiểm mạch", "ngân sách dòng", "pull-up", "địa chỉ i2c",
                      "mức logic", "board.check"])
    def board_check(ctx: Any, khoi: str = ""):
        from ..knowledge import erc as ERC

        ds = ERC.erc(ctx.store)
        if khoi:
            ds = [x for x in ds if x.path == khoi or x.path.startswith(khoi.rstrip("/") + "/")]
        theo = {"khong_dat": [], "canh_bao": [], "chua_du_du_kien": [], "dat": []}
        for x in ds:
            theo.setdefault(x.ket_luan, []).append(x.to_dict())

        if not ds:
            return {"so_phat_hien": 0, "ket_qua": theo,
                    "note_vi": ("Chưa kiểm được gì: bản đồ chưa có net nguồn hay bus nào để "
                                "xét. Dựng cây và net trước (ckm.net_set / ckm.port_set).")}
        # Thứ tự câu nói theo mức độ hậu quả, không theo thứ tự luật chạy.
        phan = []
        if theo["khong_dat"]:
            phan.append(f"{len(theo['khong_dat'])} lỗi CHẶN: "
                        + "; ".join(f"[{x['path']}] {x['vi']}" for x in theo["khong_dat"][:3]))
        if theo["canh_bao"]:
            phan.append(f"{len(theo['canh_bao'])} cảnh báo: "
                        + "; ".join(f"[{x['path']}] {x['vi']}" for x in theo["canh_bao"][:2]))
        if theo["chua_du_du_kien"]:
            phan.append(f"{len(theo['chua_du_du_kien'])} chỗ CHƯA ĐỦ DỮ KIỆN — đây không "
                        "phải 'đạt', và nói với người dùng cần nạp Fact gì: "
                        + "; ".join(f"[{x['path']}] {x['vi']}"
                                    for x in theo["chua_du_du_kien"][:2]))
        if theo["dat"] and not (theo["khong_dat"] or theo["canh_bao"]):
            phan.append(f"{len(theo['dat'])} ràng buộc kiểm được và ĐẠT")
        return {"so_phat_hien": len(ds), "ket_qua": theo,
                "theo_khoi": sorted({x.path for x in ds}),
                "note_vi": ". ".join(phan) + "."}

    # ====================================================================== đọc & gộp
    @r.tool("ckm.graph", "Thiết kế",
            "Tra Bản đồ tri thức mạch: có bao nhiêu chip/chân/net/khối, chân nào gán gì, "
            "chỗ nào còn hở. Gọi cái này trước khi gán chân hoặc trước khi hỏi người dùng "
            "— đừng đoán bản đồ đang có gì.",
            {"type": "object",
             "properties": {
                 "loai": {"type": "string", "enum": list(K.LOAI_NUT),
                          "description": "Chỉ xem một loại thực thể"},
                 "chip": {"type": "string", "description": "Chỉ xem chân/gán của chip này"}},
             "required": []},
            risk="R1", keywords=["bản đồ", "ckm", "tra", "đồ thị", "graph", "xem mạch"])
    def graph(ctx: Any, loai: str = "", chip: str = ""):
        dem = _dem_day_du(ctx)
        ra: dict[str, Any] = {"dem": dem}
        if chip:
            ten, ref, loi = _tim_linh_kien(ctx, _ten_chip(chip))
            if loi is not None:
                return loi
            gan = _bang_gan(ctx, ref)
            chan = ctx.store.ckm_cac_nut(loai="pin", tien_to=f"pin:{ref}.")
            da = {g.get("chan") for g in gan}
            ra.update({"chip": ten, "ref": ref, "gan": gan, "so_chan": len(chan),
                       "chan_chua_gan": sorted(n["node_id"].split(".", 1)[-1]
                                               for n in chan
                                               if n["node_id"].split(".", 1)[-1] not in da)})
        if loai:
            ra["nut"] = [{"id": n["node_id"], "ten": n["ten"], "tier": n["tier"],
                          **n["canonical"]}
                         for n in ctx.store.ckm_cac_nut(loai=loai, limit=300)]
        if not loai and not chip:
            a = ctx.store.get(K.MA_DO_THI)
            ms = [K.Module.from_dict(d) for d in (a["canonical"].get("khoi") if a else [])]
            cay = KC.Cay.doc(ctx.store)
            ra["khoi"] = [m.ma for m in ms]
            ra["cay"] = _cay_chu(cay)
            ra["tin_hieu_treo"] = K.tin_hieu_treo(ms) if ms else {}
            ra["thieu_de_sinh_so_do"] = K.thieu_gi(dem)
            ra["vi_pham_bat_bien"] = K.vi_pham_cay(ctx.store)
            sau = KC.canh_bao_do_sau(cay)
            if sau:
                ra["canh_bao_do_sau"] = sau
        return ra

    @r.tool("ckm.build", "Thiết kế",
            "Gộp bản đồ thành MỘT hiện vật CKM: khối, net, pinout, BOM, hộ chiếu. Nói rõ "
            "còn thiếu gì và chỗ nào hở. Đây là thứ mà việc sinh sơ đồ nguyên lý cần.",
            {"type": "object",
             "properties": {"explain": EXPLAIN_SCHEMA},
             "required": ["explain"]},
            risk="R2", writes_artefact=True, needs_explain=True, produces=["ckm"],
            keywords=["gộp", "ckm", "bản đồ mạch", "build", "chốt bản đồ"])
    def build(ctx: Any, explain: dict[str, Any]):
        # Dựng lại đồ thị trước khi đọc nó: nếu hiện vật bị đổi bằng đường khác (hoàn
        # tác, sửa tay, phát lại sự kiện) thì đây là chỗ đồ thị khớp lại.
        K.chieu(ctx.store)
        dem = _dem_day_du(ctx)
        thieu = K.thieu_gi(dem)
        nut_pin = ctx.store.ckm_cac_nut(loai="pin")
        nets = ctx.store.ckm_cac_nut(loai="net")
        dut = K.cho_dut(nut_pin, ctx.store.ckm_cac_canh(loai="DUOC_GAN"), nets,
                        ctx.store.ckm_cac_canh(loai="CO_CHAN"))
        a = ctx.store.get(K.MA_DO_THI)
        ms = [K.Module.from_dict(d) for d in (a["canonical"].get("khoi") if a else [])]
        chips = ctx.store.ckm_cac_nut(loai="chip")
        bom = ctx.store.list(type="bom", limit=5)

        cay = KC.Cay.doc(ctx.store)
        phang = KC.flatten(cay)
        vi_pham = K.vi_pham_cay(ctx.store)
        canh_sau = KC.canh_bao_do_sau(cay)
        from ..knowledge import erc as ERC
        canon = {
            "cay": _cay_chu(cay),
            "erc": [x.to_dict() for x in ERC.erc(ctx.store)],
            "flatten": {k: list(v) for k, v in phang.items()},
            "vi_pham_bat_bien": vi_pham,
            "chip": [{"ten": c["ten"], "ho_chieu": c["canonical"].get("ho_chieu", ""),
                      "ref": c["canonical"].get("ref", "")} for c in chips],
            "so_chan": len(nut_pin),
            "khoi": [m.to_dict() for m in ms],
            "canh_khoi": K.canh_giua_module(ms),
            "net": [{"ten": n["ten"], **n["canonical"]} for n in nets],
            "pinout": {c["canonical"].get("ref", c["ten"]):
                       _bang_gan(ctx, c["canonical"].get("ref", c["ten"])) for c in chips},
            "bom": [b["id"] for b in bom],
            "cho_dut": dut, "thieu": thieu, "du_de_sinh_so_do": not thieu,
        }
        cs = ctx.history.ghi_kho(
            author=f"agent:{ctx.run_id}", artefact_id=K.MA_CKM, type="ckm",
            op="update" if ctx.store.get(K.MA_CKM) else "create", canonical=canon,
            explain=explain, run_id=ctx.run_id)

        # KHÔNG trả lỗi khi thiếu: gộp một bản đồ chưa đủ vẫn có ích — nó cho người thấy
        # còn thiếu gì. Chỉ việc SINH SƠ ĐỒ mới cần đủ, và chỗ đó mới là chỗ chặn.
        nd = ("Bản đồ đủ tiền đề để sinh sơ đồ nguyên lý." if not thieu else
              "Bản đồ CHƯA đủ để sinh sơ đồ nguyên lý. Thiếu: "
              + "; ".join(f"{t['can']} (gọi {t['goi']})" for t in thieu) + ".")
        ho = []
        if dut["so_chan_chua_gan"]:
            ho.append(f"{dut['so_chan_chua_gan']} chân chưa gán chức năng")
        if dut["so_chan_khong_co_bang_chan"]:
            ho.append(f"{dut['so_chan_khong_co_bang_chan']} chân của linh kiện CHƯA CÓ "
                      "bảng chân (chưa nạp datasheet), nên không kiểm được gì về chúng")
        if dut["net_mot_chan"]:
            ho.append(f"net nối một chân: {', '.join(dut['net_mot_chan'][:5])}")
        if dut["net_khong_chan"]:
            ho.append(f"net chưa nối gì: {', '.join(dut['net_khong_chan'][:5])}")
        if not bom:
            ho.append("chưa có BOM (store.bom_set)")
        # Vi phạm bất biến làm bản đồ KHÔNG dùng được để sinh sơ đồ, dù đủ tiền đề. Một
        # cái cây có chu trình hay một net đi xuyên cấp thì `flatten` ra một mạch khác với
        # mạch người vẽ — và mọi thứ hạ nguồn đọc cái sai đó mà không biết.
        du = (not thieu) and not vi_pham
        if vi_pham:
            nd = ("Bản đồ VI PHẠM bất biến cây, chưa dùng được để sinh sơ đồ: "
                  + "; ".join(f"{v['ma']} {v['vi']}" for v in vi_pham[:3])
                  + (f" (và {len(vi_pham) - 3} chỗ nữa)" if len(vi_pham) > 3 else ""))
        return {"ckm": K.MA_CKM, "changeset": cs.id, "dem": dem, "thieu": thieu,
                "cho_dut": dut, "du_de_sinh_so_do": du,
                "vi_pham_bat_bien": vi_pham, "so_net_phang": len(phang),
                "canh_bao_do_sau": canh_sau,
                "note_vi": (nd + (" Chỗ hở: " + "; ".join(ho) + "." if ho else "")
                            + (" " + canh_sau if canh_sau else ""))}

    return r


def _dem_day_du(ctx: Any) -> dict[str, int]:
    """Bảng đếm của kho, cộng thêm thứ kho không biết: chip nào đã có hộ chiếu.

    Kho đếm nút; "đã ghim hộ chiếu" là một tính chất của hiện vật, nên nó được cộng ở đây
    thay vì bắt lớp kho biết về hộ chiếu.
    """
    dem = dict(ctx.store.ckm_dem())
    dem["chip_co_ho_chieu"] = sum(
        1 for c in ctx.store.ckm_cac_nut(loai="chip") if c["canonical"].get("ho_chieu"))
    return dem


def _cay_chu(cay: Any) -> list[str]:
    """Cây dạng chữ, thụt đầu dòng — dạng người đọc được trong Console.

    Giao diện có khối cây riêng (A5.9, bước HIER-B); dạng này để tác tử và người đọc thấy
    hình dáng mạch ngay trong kết quả công cụ, không phải gọi thêm gì.
    """
    if not cay.goc:
        return []
    ra: list[str] = []

    def di(nid: str, sau: int) -> None:
        n = cay.nut[nid]
        so_port = len(cay.port_cua.get(nid, []))
        nhan = f"{'  ' * sau}{n.get('path') or n['ten']}"
        if n.get("kind") == "leaf":
            nhan += f" [lá · {so_port} chân]"
        else:
            net = [x for x in cay.con.get(nid, []) if cay.nut[x]["loai"] == "net"]
            nhan += f" [{n.get('kind')} · {so_port} Port · {len(net)} net]"
        ra.append(nhan)
        for con in cay.con_truc_tiep(nid):
            di(con, sau + 1)

    di(cay.goc, 0)
    return ra


def _doan_loai_net(ten: str) -> str:
    """Loại net đoán theo tên — netlist KiCad không nói loại.

    Đoán, và gọi nó là đoán (`loai_do_doan: True` trong hiện vật, và note_vi nói ra). Sai
    ở đây không hỏng mạch ngay, nhưng nếu im lặng thì một net nguồn bị coi là tín hiệu và
    các luật so sánh sau này áp sai lên nó.
    """
    t = ten.strip().upper()
    if t in ("GND", "GROUND", "VSS", "AGND", "DGND", "GNDA"):
        return "ground"
    if t.startswith(("VDD", "VCC", "VBAT", "VIN", "3V3", "5V", "1V8", "VDDA",
                     "+3V3", "+5V", "AVDD")):
        return "power"
    if t.startswith(("SCK", "SCLK", "CLK", "XTAL", "OSC", "MCLK")):
        return "clock"
    if t.startswith(("SDA", "SCL", "MOSI", "MISO", "TX", "RX", "CAN", "USB", "UART")):
        return "bus"
    return "signal"
