# -*- coding: utf-8 -*-
"""PreToolUse · PostToolUse · Stop — ba lớp xác định bao quanh mỗi lời gọi công cụ.

EIDE-MDD-40 §B1/§B4. Ở G1 mới có phần không phụ thuộc changeset (G2) và hiện vật hai
dạng (G3); những chỗ đó được đánh dấu rõ để G2/G3 nối vào, không phải viết lại.

Nguyên tắc khi thêm việc cho hook: hook phải XÁC ĐỊNH và NHANH. Một hook gọi mô hình
là một hook có thể hỏng đúng lúc mô hình hỏng — và khi đó nguyên tắc nó canh biến mất
mà không ai biết.
"""

from __future__ import annotations

import re
from typing import Any

from ..errors import missing_explain, outside_sandbox
from .s0 import normalize_vi as _bo_dau
from .base import HookBus, PreToolResult, StopResult

# Sáu trường bắt buộc của lớp giải thích — §E1, §E3.1, nguyên tắc N8.
EXPLAIN_FIELDS = ("summary", "why", "sources", "diff_prev", "next", "confidence")

# Hằng số "trần" đi vào mã — N1.
#
# Phạm vi được thu hẹp có chủ đích sau khi đo trên phiên thật: bản đầu bắt MỌI số ≥ 3
# chữ số trong MỌI tệp, và vì kho Fact rỗng nên nó chặn cả một tài liệu hướng dẫn tiếng
# Việt. Kết quả: tác tử không ghi nổi tệp nào trong 33 lượt (xem DEV-231).
#
# Thứ N1 thật sự canh là **con số kỹ thuật quyết định hành vi mạch**: điện áp, dòng,
# thời gian, tần số, địa chỉ thanh ghi, ngưỡng. Không phải `chmod 755`, không phải số
# thứ tự bước trong tài liệu.
#
# Thứ tự trong nhóm đơn vị QUAN TRỌNG: biến thể dài phải đứng trước biến thể ngắn,
# nếu không `MB/s` sẽ khớp thành `MB` và bỏ rơi phần `/s`.
_CONST = re.compile(
    r"(?<![\w.])("
    r"\d+(?:[.,]\d+)?\s*(?:"
    r"GB/s|MB/s|KB/s|B/s|Gbps|Mbps|kbps|bps|"       # thông lượng
    r"TB|GB|MB|KB|"                                  # dung lượng
    r"GHz|MHz|kHz|Hz|"                               # tần số
    r"mAh|Ah|mA|uA|µA|"                              # dòng
    r"mV|kV|"                                        # áp
    r"ms|µs|us|ns|"                                  # thời gian
    r"kΩ|MΩ|Ω|ohm|uF|µF|nF|pF|mH|uH|dBm|dB|°C|℃"    # linh kiện, nhiệt
    r")"
    r"|0x[0-9A-Fa-f]{3,}"
    r"|\d+(?:[.,]\d+)?\s*V(?![a-zA-Z])"
    r"|\d+(?:[.,]\d+)?\s*A(?![a-zA-Z])"
    r")(?![\w.])", re.IGNORECASE)

# Định nghĩa hằng trong C — `#define X 1234` là đúng hình dạng mà N1 nhắm tới.
_DEFINE = re.compile(r"#\s*define\s+(\w+)\s+\(?\s*(-?\d+(?:\.\d+)?|0x[0-9A-Fa-f]+)")

_CONST_ALLOW = {"0", "1", "0x00", "0xFF", "0xFFFF", "0xFFFFFFFF"}

# Chỉ tệp mã và cấu hình mới bị soi. Tài liệu hướng dẫn là văn xuôi cho người đọc —
# con số trong đó là lời thuật lại một quyết định đã ghi ở nơi khác.
_DUOI_LA_MA = {".c", ".h", ".cpp", ".cc", ".hpp", ".s", ".asm", ".ino", ".py", ".rs",
               ".go", ".sh", ".bash", ".ld", ".mk", ".cmake", ".yaml", ".yml", ".json",
               ".toml", ".dts", ".dtsi", ".conf"}


def register_standard_hooks(bus: HookBus) -> HookBus:

    # ================================================================== PreToolUse
    @bus.on_pre_tool
    def check_sandbox(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """Đường dẫn ra ngoài vùng làm việc bị chặn VÌ THIẾT KẾ (TC070).

        Công cụ fs.* tự kiểm nữa, nhưng lớp này bắt được cả công cụ mới ai đó thêm sau
        mà quên kiểm — đó là lý do một hook chung tồn tại song song với kiểm trong tool.
        """
        from pathlib import Path
        root = Path(ctx.config.paths.project_root).resolve()
        for key in ("path", "file", "dir", "target_path", "out"):
            raw = (call.get("args") or {}).get(key)
            if not isinstance(raw, str) or not raw:
                continue
            p = Path(raw).expanduser()
            p = (root / p).resolve() if not p.is_absolute() else p.resolve()
            if p != root and root not in p.parents:
                return PreToolResult(ok=False, error=outside_sandbox(str(p), [str(root)]),
                                     fired=["sandbox"])
        return PreToolResult(fired=["sandbox"])

    @bus.on_pre_tool
    def check_explain(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """N8 — công cụ ghi hiện vật phải mang đủ sáu trường explain. Ca CX02.

        Một ngoại lệ có chủ đích cho `sources`: danh sách rỗng là **hợp lệ khi không có
        con số nào để dẫn nguồn**. §E3.1 viết "mỗi số trong summary/why phải có nguồn
        trong danh sách" — nó ràng buộc *số*, không ràng buộc *sự tồn tại của danh sách*.

        Nếu bắt `sources` luôn phải khác rỗng thì mọi hiện vật thuần mô tả ("đổi tên
        khối", "ghi chú quy ước") đều bị chặn, và mô hình sẽ học cách nhét một nguồn
        giả vào cho qua cửa — tức là ta đổi một quy tắc đúng lấy một thói quen sai.
        """
        spec = ctx.registry.get(call.get("tool", ""))
        if spec is None or not spec.needs_explain:
            return PreToolResult(facts={"explain.complete": True})
        ex = (call.get("args") or {}).get("explain") or {}

        missing = [f for f in EXPLAIN_FIELDS if f != "sources" and not ex.get(f)]
        if "sources" not in ex:
            missing.append("sources")
        elif not ex.get("sources"):
            # Rỗng thì chỉ chấp nhận khi summary + why không chứa con số kỹ thuật nào.
            chu = f"{ex.get('summary', '')} {ex.get('why', '')}"
            if _CONST.search(chu):
                missing.append("sources")

        if missing:
            return PreToolResult(ok=False, error=missing_explain(spec.name, missing),
                                 facts={"explain.complete": False,
                                        "explain.missing": missing},
                                 fired=["explain"])
        return PreToolResult(facts={"explain.complete": True}, fired=["explain"])

    @bus.on_pre_tool
    def constant_guard(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """N1 — hằng số không truy vết được thì không đi vào mã.

        Một con số được coi là CÓ NGUỒN khi nó xuất hiện ở ít nhất một trong bốn nơi:

          1. một **Fact** trong kho (tầng VÀNG/BẠC/NGƯỜI);
          2. **EIDE.md** — quyết định, quy ước, giả định đã ghi thành bộ nhớ dự án;
          3. **`explain.sources`** của chính lời gọi này — tác tử đang khai nguồn;
          4. **lời người dùng trong phiên** — họ vừa nói con số đó ra.

        Bốn đường này đều là "truy vết được tới một nguồn có tên", đúng tinh thần N1.
        Bản đầu chỉ có đường (1), và vì kho Fact rỗng lúc bắt đầu dự án nên nó chặn
        sạch — biến một cái cổng thành bức tường (DEV-231).
        """
        from pathlib import Path as _P

        tool = call.get("tool", "")
        if tool not in ("fs.write", "fs.edit"):
            return PreToolResult(facts={"constant_guard.unsourced": 0})

        args = call.get("args") or {}
        duoi = _P(str(args.get("path", ""))).suffix.lower()
        if duoi not in _DUOI_LA_MA:
            # Văn xuôi cho người đọc: số trong đó thuật lại quyết định đã ghi nơi khác.
            return PreToolResult(facts={"constant_guard.unsourced": 0},
                                 fired=["constant_guard:bo-qua-van-xuoi"])

        content = " ".join(str(v) for k, v in args.items()
                           if k in ("content", "new_string", "patch"))
        ung_vien = {m.group(1).strip() for m in _CONST.finditer(content)}
        ung_vien |= {m.group(2) for m in _DEFINE.finditer(content)}
        ung_vien -= _CONST_ALLOW
        if not ung_vien:
            return PreToolResult(facts={"constant_guard.unsourced": 0},
                                 fired=["constant_guard"])

        nguon = _van_ban_co_nguon(ctx, args)
        khong_nguon = [c for c in sorted(ung_vien) if not _co_trong(c, nguon, ctx)]
        return PreToolResult(facts={"constant_guard.unsourced": len(khong_nguon),
                                    "constant_guard.list": khong_nguon},
                             fired=["constant_guard"])

    @bus.on_pre_tool
    def doi_tieu_chi(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """N6 — đổi TIÊU CHÍ khi đã có kết quả là đường ngắn nhất tới một "đạt" vô nghĩa.

        Hook này không chặn; nó nói cho lớp cấp quyền biết ba việc để `policy.yaml` quyết:
        tiêu chí đã tồn tại chưa, có kết quả mô phỏng nào rồi chưa, và ngưỡng nào đang đổi.
        Chính `từ bao nhiêu sang bao nhiêu` mới là thứ thẻ cổng cần hiện — một thẻ hỏi "đổi
        tiêu chí?" mà không nói đổi từ đâu sang đâu thì người dùng bấm duyệt theo phản xạ.
        """
        if call.get("tool") != "sim.criteria":
            return PreToolResult(facts={"criteria.exists": False, "criteria.changed": False})

        args = call.get("args") or {}
        ma = str(args.get("ma") or "sim-01")
        cu = ctx.store.get(f"criteria:{ma}")
        if cu is None:
            return PreToolResult(facts={"criteria.exists": False, "criteria.changed": False},
                                 fired=["doi_tieu_chi:moi"])

        cu_theo_ma = {str(a.get("ma")): a
                      for a in ((cu.get("canonical") or {}).get("assert") or [])}
        doi: list[str] = []
        for a in (args.get("assert") or []):
            c = cu_theo_ma.get(str(a.get("ma")))
            if c is None:
                doi.append(f"{a.get('ma')}: thêm mới")
                continue
            for truong in ("nguong", "nguong_tren", "phep_so"):
                if str(c.get(truong, "")) != str(a.get(truong, "")):
                    doi.append(f"{a.get('ma')}.{truong}: {c.get(truong)} → {a.get(truong)}")
        bo = sorted(set(cu_theo_ma) - {str(a.get("ma")) for a in (args.get("assert") or [])})
        doi += [f"{x}: BỎ ĐI" for x in bo]

        co_kq = ctx.store.get("sim_result:can-bang") is not None
        return PreToolResult(
            facts={"criteria.exists": True, "criteria.changed": bool(doi),
                   "criteria.has_result": co_kq,
                   "criteria.doi_gi": "; ".join(doi[:6])},
            fired=["doi_tieu_chi:" + ("doi" if doi else "khong-doi")])

    @bus.on_pre_tool
    def kiem_release(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """Cấp `snapshot.has_release` cho lớp cấp quyền (CX15)."""
        if not str(call.get("tool", "")).startswith("target."):
            return PreToolResult(facts={"snapshot.has_release": True})
        return PreToolResult(facts={"snapshot.has_release": _co_release(ctx)},
                             fired=["release"])

    @bus.on_pre_tool
    def la_eide_md(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """MEM-42 §7.1 — EIDE.md chỉ vào bằng `memory.*`, không bằng `fs.write`.

        So theo đường dẫn ĐÃ GIẢI, không theo chuỗi: `./EIDE.md`, `EIDE.md` và đường
        tuyệt đối là cùng một tệp, và một luật khoá trên chuỗi thì chỉ cần viết khác
        một chút là lách được.
        """
        if call.get("tool") not in ("fs.write", "fs.edit"):
            return PreToolResult(facts={"target.la_eide_md": False})
        from pathlib import Path
        raw = (call.get("args") or {}).get("path") or ""
        if not raw:
            return PreToolResult(facts={"target.la_eide_md": False})
        goc = Path(ctx.config.paths.project_root).resolve()
        p = Path(raw).expanduser()
        p = (goc / p).resolve() if not p.is_absolute() else p.resolve()
        return PreToolResult(
            facts={"target.la_eide_md": p == Path(ctx.config.paths.eide_md).resolve()},
            fired=["eide_md"])

    @bus.on_pre_tool
    def ten_ban_ung_y(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """§E6.2 — tên bản ưng ý phải do NGƯỜI đặt, và câu đó phải có thật.

        Cấm bằng lời trong mô tả công cụ là chưa đủ: mô hình rất dễ "giúp" bằng cách
        nghĩ ra `sau-khi-sua-driver`. Nên chỗ này đo được: tên phải xuất hiện trong thứ
        người đã gõ ở phiên này — câu trong ô nhập, hoặc chữ họ điền vào thẻ.
        """
        if call.get("tool") != "snapshot.create":
            return PreToolResult(facts={"snapshot.ten_tu_nguoi": True})
        ten = str((call.get("args") or {}).get("ten", "")).strip()
        loi = " ".join(str(c) for c in
                       (getattr(ctx, "loi_nguoi_trong_phien", []) or [])).lower()
        # So khớp nới tay: người gõ "v0.2 thêm nhiệt", tác tử chuẩn hoá thành
        # "v0.2-them-nhiet" — vẫn là tên của người, không phải tên nó nghĩ ra.
        goc = re.sub(r"[^a-z0-9]+", " ", _bo_dau(ten.lower())).split()
        loi_g = re.sub(r"[^a-z0-9]+", " ", _bo_dau(loi))
        tu = bool(goc) and all(t in loi_g.split() for t in goc)
        return PreToolResult(facts={"snapshot.ten_tu_nguoi": tu,
                                    "snapshot.ten": ten},
                             fired=["ten_ban_ung_y"])

    @bus.on_pre_tool
    def ghi_de_ban_cua_nguoi(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """N9 / §E4 bước 6 — "fs.write vào tệp người vừa sửa → G-FILE".

        Luật: nếu thay đổi GẦN NHẤT trên hiện vật này là của người, thì tác tử ghi đè
        lên đó phải hỏi. Không phải vì tác tử hay sai, mà vì người vừa bỏ công vào đó
        và có quyền biết trước khi công ấy bị thay.

        `target.merged` để dành cho luồng §E4.1 lock_broken: khi bản của tác tử đã được
        gộp LÊN bản của người (chứ không thay nó), cổng không cần nổ lần nữa.
        """
        if call.get("tool") not in ("fs.write", "fs.edit"):
            return PreToolResult(facts={"target.human_edited": False})
        path = (call.get("args") or {}).get("path")
        hist = getattr(ctx, "history", None)
        if not path or hist is None:
            return PreToolResult(facts={"target.human_edited": False})

        cham = [cs for cs in hist.log.touching(path) if not cs.undone_by]
        cua_nguoi = bool(cham) and cham[-1].by_human
        return PreToolResult(
            facts={"target.human_edited": cua_nguoi,
                   "target.merged": bool(call.get("args", {}).get("_merged")),
                   "target.last_human_cs": cham[-1].id if cua_nguoi else None},
            fired=["human_edited"])

    # ================================================================== PostToolUse
    @bus.on_post_tool
    def ledger_and_lint(call: dict[str, Any], result: Any, ctx: Any) -> None:
        """Ghi sổ cái + bắt "log rỗng" (N6).

        G2 nối changeset + đồng bộ Surface + đánh dấu STALE vào đúng chỗ này.
        """
        ctx.ledger.append("tool_result", {
            "run_id": ctx.run_id, "tool": call.get("tool"),
            "ok": bool(getattr(result, "ok", False)),
            "elapsed_ms": round(getattr(result, "elapsed_ms", 0.0), 1),
            "code": getattr(getattr(result, "error", None), "code", None),
        })
        data = getattr(result, "data", None)
        if getattr(result, "ok", False) and _looks_empty(data):
            # N6: "log rỗng ≠ đạt". Gắn cờ vào chính kết quả để mô hình đọc được.
            if isinstance(data, dict):
                data.setdefault(
                    "note_vi",
                    "Công cụ chạy xong nhưng không trả về dữ liệu nào. Đây KHÔNG phải "
                    "'đạt' — đây là 'không kết luận được'. Nói rõ điều đó với người dùng.")

    # ================================================================== Stop
    @bus.on_stop
    def assumptions_stated(ctx: Any) -> StopResult:
        """N4 — giả định đang dùng phải được nói ra, không nằm ngầm trong hiện vật."""
        unsaid = [a for a in ctx.assumptions if a not in ctx.assumptions_stated]
        if not unsaid:
            return StopResult()
        return StopResult(
            another_round=True, reason_vi="còn giả định chưa nói ra",
            fired=["assumptions"],
            injection=("<system-reminder>\nBạn kết thúc lượt mà chưa nói ra các giả định "
                       "đang dùng:\n- " + "\n- ".join(unsaid) +
                       "\nNói chúng ra cho người dùng, kèm việc cần gì để xoá giả định đó."
                       "\n</system-reminder>"))

    @bus.on_stop
    def human_edits_acknowledged(ctx: Any) -> StopResult:
        """N9 / CX07 — sửa của người phải được tác tử nhắc tới ở lượt này.

        G2 cấp `ctx.human_edits` từ changeset author=human chưa acknowledged.
        """
        pending = [cs for cs in ctx.human_edits if not cs.get("acknowledged_by_agent")]
        if not pending:
            return StopResult()
        ids = ", ".join(cs.get("id", "?") for cs in pending)
        return StopResult(
            another_round=True, reason_vi="chưa nhắc tới thay đổi của người",
            fired=["human_edits"],
            injection=("<system-reminder>\nBạn chưa nhắc tới thay đổi mà người dùng vừa tự "
                       f"tay sửa ({ids}). Trước khi kết thúc lượt, hãy: (1) nói rõ bạn đã "
                       "thấy thay đổi gì; (2) nêu hệ quả — cái gì thành STALE, cái gì phải "
                       "chạy lại; (3) nếu nó mâu thuẫn với một Fact hay REQ khác, nêu cả "
                       "hai nguồn và hỏi họ.\n</system-reminder>"))

    @bus.on_stop
    def said_something(ctx: Any) -> StopResult:
        """Một lượt kết thúc mà không nói gì với người là một lượt hỏng.

        Không nằm trong bảng §B4, nhưng suy ra từ E3.2 quy tắc 4 ("chỉ ra chỗ cần
        người") và từ ca TC057, nơi cột kết quả TRỐNG HOÀN TOÀN vì lượt bị từ chối
        trong im lặng. Ghi DEV-201.
        """
        if ctx.said_anything or ctx.awaiting_human:
            return StopResult()
        return StopResult(
            another_round=True, reason_vi="chưa nói gì với người dùng", fired=["said_something"],
            injection=("<system-reminder>\nLượt này kết thúc mà bạn chưa nói câu nào với "
                       "người dùng. Hãy trả lời họ: bạn đã làm gì, thấy gì, và đề nghị việc "
                       "tiếp theo. Nếu không làm được việc họ nhờ, nói thẳng là không làm "
                       "được và vì sao.\n</system-reminder>"))

    # SCH-44 SCH-09 — "không đề nghị cài KiCad ở BẤT KỲ thông điệp nào".
    #
    # Đây là một ràng buộc về *thứ không được xuất hiện*, và loại ràng buộc đó không tự giữ
    # được. Mô hình rất dễ "giúp" bằng câu "anh cài KiCad rồi mở tệp này" — đúng lúc nó
    # tưởng đang hữu ích nhất. Cấm bằng một dòng trong hiến pháp là cấm KHÔNG ĐO ĐƯỢC: lời
    # nhắc trôi đi sau vài lần nén, và không ai biết nó đã trôi.
    #
    # Nên luật nằm ở đây, đọc `ctx.loi_da_noi` — mọi câu tác tử nói ra đều đi qua đó.
    _CAM_KICAD = (
        "cài kicad", "cai kicad", "install kicad", "tải kicad", "tai kicad",
        "download kicad", "kicad-cli", "brew install kicad", "apt install kicad",
    )

    @bus.on_stop
    def khong_de_nghi_cai_kicad(ctx: Any) -> StopResult:
        """Quyết định 25/09/2026: máy này KHÔNG cài KiCad, và tác tử không được đề nghị."""
        thay: list[str] = []
        for cau in getattr(ctx, "loi_da_noi", []) or []:
            t = (cau or "").lower()
            for m in _CAM_KICAD:
                if m in t:
                    thay.append(m)
        if not thay:
            return StopResult()
        return StopResult(
            another_round=True, reason_vi="đề nghị cài KiCad — quyết định 25/09 cấm",
            fired=["khong_cai_kicad"],
            injection=("<system-reminder>\nBạn vừa đề nghị cài hoặc gọi KiCad ("
                       + ", ".join(sorted(set(thay)))
                       + "). Quyết định của chủ sản phẩm ngày 25/09/2026: **máy này không "
                         "cài KiCad**, và không đề nghị người dùng cài.\n\nNói lại không có "
                         "câu đó. EIDE tự đọc/ghi tệp KiCad bằng thư viện Python và tự render "
                         "SVG; muốn mở trong KiCad thì dùng sch.export để xuất gói rồi mở ở "
                         "máy KHÁC đã có sẵn KiCad.\n</system-reminder>"))

    # ================================================================== plan mode (§B5)
    @bus.on_pre_tool
    def plan_lon_hay_nho(call: dict[str, Any], ctx: Any) -> PreToolResult:
        """Cấp `plan.big` cho luật `POL-SCOPE-plan`.

        Tính bằng MÃ từ chính nội dung kế hoạch — số bước, và công cụ nào trong đó chạm cổng
        hay từ R3 trở lên. Cố ý **không** hỏi mô hình "việc này có lớn không": nó sẽ khai
        "nhỏ" đúng vào lúc nó đang định làm việc lớn, không phải vì gian mà vì lúc ấy nó
        đang tập trung vào việc chứ không vào việc phân loại việc.
        """
        if call.get("tool") != "plan.exit":
            return PreToolResult()
        from ..ke_hoach import Buoc, KeHoach, la_viec_lon

        b = (call.get("args") or {}).get("buoc") or []
        kh = KeHoach(muc_tieu="x",
                     buoc=[Buoc(**{k: v for k, v in x.items() if k in Buoc.__slots__})
                           for x in b if isinstance(x, dict)])
        lon, vi_sao = la_viec_lon(kh, ctx.registry.get)
        return PreToolResult(facts={"plan.big": lon, "plan.steps": len(kh.buoc),
                                    "plan.why_big": vi_sao},
                             fired=["plan_lon_hay_nho"] if lon else [])

    @bus.on_stop
    def doi_chieu_ke_hoach(ctx: Any) -> StopResult:
        """Stop hook §B5: tác tử có đi đúng kế hoạch đã duyệt không.

        **Không** bắt chạy thêm vòng và **không** coi độ lệch là lỗi. Đi thêm việc ngoài kế
        hoạch thường là dấu hiệu kế hoạch thiếu chứ không phải tác tử sai; việc của hook này
        là làm độ lệch NHÌN THẤY ĐƯỢC để người dùng quyết, chứ không phải để phạt. Một hook
        phạt sẽ dạy tác tử viết kế hoạch thật rộng cho an toàn — tức là phá đúng thứ mà plan
        mode sinh ra để có.
        """
        from ..ke_hoach import MA_KE_HOACH, KeHoach, doi_chieu

        kho = getattr(ctx, "store", None)
        a = kho.get(MA_KE_HOACH) if kho is not None else None
        if not a:
            return StopResult()
        kh = KeHoach.from_dict(a.get("canonical") or {})
        if kh.trang_thai != "da_duyet":
            return StopResult()
        d = doi_chieu(kh, list(getattr(ctx, "cong_cu_da_goi", []) or []))
        if not d["lech"]:
            return StopResult(fired=["doi_chieu_ke_hoach"])
        return StopResult(
            fired=["doi_chieu_ke_hoach_lech"],
            injection=("<system-reminder>\nĐối chiếu với kế hoạch đã duyệt: "
                       f"{d['xong']}/{d['tong']} bước xong"
                       + (" · công cụ dùng NGOÀI kế hoạch: "
                          + ", ".join(d["ngoai_ke_hoach"][:6]) if d["ngoai_ke_hoach"] else "")
                       + (" · bước chưa đụng tới: "
                          + ", ".join(d["chua_lam"][:6]) if d["chua_lam"] else "")
                       + ".\n\nLệch khỏi kế hoạch KHÔNG phải lỗi — thường là dấu hiệu kế "
                         "hoạch thiếu. Khi báo cáo lượt, NÓI RA chỗ lệch và vì sao, để người "
                         "dùng quyết: sửa kế hoạch, hay quay lại đúng nó.\n</system-reminder>"))

    # ============================================= tự kiểm chứng lời tuyên "đạt" (N6, §B5)
    #
    # Đo được trên phiên bo STM32F469: `verifier` — tác tử con kiểm chứng độc lập, thiết kế
    # rất tốt (chỉ công cụ ĐỌC, và **cố ý không cho biết đề bài** để nó không suy ra kết luận
    # mong đợi rồi đi biện minh) — chạy **0 lần trong 402 lượt**.
    #
    # Không phải vì nó hỏng. Vì `CAN_KIEM_CHUNG` chỉ nổ khi một **subagent** tuyên đạt, mà
    # tác tử chính làm hết mọi việc trong lượt của nó và **không sinh subagent lần nào**. Cái
    # van tồn tại, nhưng ống dẫn không đi qua nó. Lời tuyên "xong" của chính tác tử chính —
    # thứ người dùng thật sự đọc — chưa bao giờ bị ai kiểm.
    _TUYEN_DAT = ("đã xong", "da xong", "hoàn thành", "hoan thanh", "chạy được",
                  "chay duoc", "đã chạy", "đạt yêu cầu", "thành công", "thanh cong",
                  "đã sửa xong", "khớp hoàn toàn", "mọi thứ đều ổn", "tất cả đều xanh")

    @bus.on_stop
    def tu_kiem_khi_tuyen_dat(ctx: Any) -> StopResult:
        """Tuyên "đạt" + có GHI hiện vật trong lượt → bắt chạy verifier trước khi kết lượt.

        Hai điều kiện, và điều kiện thứ hai quan trọng ngang điều kiện thứ nhất: chỉ nổ khi
        lượt này **đã ghi được gì đó**. Một câu "xong rồi" sau một lượt thuần đọc thường là
        trả lời một câu hỏi, không phải tuyên bố một việc đã làm — bắt nó kiểm chứng là dựng
        thủ tục quanh một cuộc trò chuyện.

        Chỉ nổ MỘT LẦN mỗi lượt (`ctx.da_tu_kiem`): vòng thứ hai là vòng tác tử đang trả lời
        chính lời nhắc này, và bắt nó kiểm lại lần nữa sẽ thành vòng lặp.
        """
        if getattr(ctx, "da_tu_kiem", False):
            return StopResult()
        if not getattr(ctx, "da_ghi_gi_do", False):
            return StopResult()
        if "task.run" in (getattr(ctx, "cong_cu_da_goi", []) or []):
            return StopResult(fired=["tu_kiem_da_chay"])
        thay = [m for cau in (getattr(ctx, "loi_da_noi", []) or [])
                for m in _TUYEN_DAT if m in (cau or "").lower()]
        if not thay:
            return StopResult()
        ctx.da_tu_kiem = True
        return StopResult(
            another_round=True, reason_vi="tuyên đạt sau khi ghi hiện vật — cần kiểm chứng",
            fired=["tu_kiem_khi_tuyen_dat"],
            injection=("<system-reminder>\nBạn vừa nói việc đã xong (“"
                       + thay[0] + "”) sau khi lượt này có ghi hiện vật.\n\n"
                       "**N6 — không báo đạt giả.** Trước khi kết lượt, gọi "
                       "`task.run(subagent=\"verifier\", …)` và đưa cho nó **bằng chứng**, "
                       "không đưa kết luận: tệp nào, hiện vật nào, con số nào, đọc ở đâu ra. "
                       "Verifier cố ý KHÔNG biết đề bài — nó chỉ mở từng bằng chứng ra xem "
                       "chúng có nói đúng thứ bạn bảo chúng nói không.\n\n"
                       "Đo được trên một phiên bo thật: “dịch sạch + nạp đúng từng byte + "
                       "verify khớp hoàn toàn” đều ĐÚNG, trong khi chương trình đang chạy "
                       "vẫn là bản nháy đèn cũ. Mọi phép đo đều xanh, và cái sai nằm đúng ở "
                       "chỗ không ai đo.\n\n"
                       "Verifier bảo `khong_dat` hay `chua_du_du_kien` thì NÓI RA điều đó "
                       "với người dùng, đừng giữ lại kết luận cũ.\n</system-reminder>"))

    return bus


def _van_ban_co_nguon(ctx: Any, args: dict[str, Any]) -> str:
    """Gom mọi nơi một con số có thể đã được khai nguồn, thành một khối chữ để dò.

    Cách này thô nhưng đúng chỗ: câu hỏi cần trả lời không phải "con số này bằng bao
    nhiêu" mà "nó đã từng xuất hiện kèm một nguồn có tên chưa". Chuỗi ký tự trả lời
    được câu đó, và nó không bao giờ từ chối oan vì một khác biệt định dạng nhỏ.
    """
    phan: list[str] = []

    # 1. Fact trong kho.
    try:
        for f in ctx.store.query_facts(limit=500):
            phan.append(f"{f.get('value')} {f.get('vmin')} {f.get('vtyp')} "
                        f"{f.get('vmax')} {f.get('unit')} {f.get('key')}")
    except Exception:                                        # noqa: BLE001
        pass

    # 2. EIDE.md — quyết định, quy ước, giả định người và tác tử đã chốt.
    md = getattr(ctx, "eide_md", None)
    if md is not None:
        try:
            phan.append(md.path.read_text("utf-8") if md.path.exists() else "")
        except OSError:
            pass

    # 3. Nguồn tác tử tự khai trong chính lời gọi này.
    ex = args.get("explain") or {}
    phan.append(str(ex.get("sources", "")))
    phan.append(str(ex.get("why", "")))
    phan.append(str(ex.get("summary", "")))

    # 4. Lời người dùng trong phiên — họ vừa nói con số đó ra.
    for c in getattr(ctx, "loi_nguoi_trong_phien", []) or []:
        phan.append(str(c))

    return " ".join(phan).lower()


def _co_trong(hang_so: str, nguon: str, ctx: Any) -> bool:
    """Con số này có mặt trong khối nguồn không (bỏ qua khác biệt đơn vị/định dạng)."""
    so = re.sub(r"[^\d.,]", "", hang_so).replace(",", ".").strip(".")
    if not so:
        return True
    dang = {so, so.rstrip("0").rstrip("."), so.replace(".", ",")}
    if hang_so.lower().startswith("0x"):
        dang.add(hang_so.lower())
        try:
            dang.add(str(int(hang_so, 16)))
        except ValueError:
            pass
    return any(d and d in nguon for d in dang)


def _looks_empty(data: Any) -> bool:
    if data is None:
        return True
    if isinstance(data, dict):
        meaningful = {k: v for k, v in data.items() if not k.startswith(("note", "_"))}
        if not meaningful:
            return True
        # {"count": 0, "items": []} là rỗng; {"exists": False} thì không — đó là câu trả lời.
        if "count" in meaningful and meaningful["count"] == 0 and len(meaningful) <= 3:
            return True
    return isinstance(data, (list, str)) and len(data) == 0


def _co_release(ctx: Any) -> bool:
    """CX15 — `target.dangerous` chỉ được phép khi đã có một bản phát hành.

    Sau khi bật RDP hay đốt eFuse thì không còn đường lùi trên con chip đó. Điều kiện
    "phải có một bản đã biết là chạy được" không phải thủ tục hành chính — nó là thứ
    duy nhất còn lại để đối chiếu khi chip đã khoá.
    """
    h = getattr(ctx, "history", None)
    try:
        return bool(h and h.snapshots.co_release())
    except Exception:                                        # noqa: BLE001
        return False
