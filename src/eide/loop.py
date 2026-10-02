# -*- coding: utf-8 -*-
"""Vòng lặp tác tử — EIDE-MDD-40 §B1.

Đây là bản hiện thực của đoạn giả mã trong tài liệu:

    def turn(human_act):
        ev = hooks.user_prompt_submit(human_act)      # S0, 0 token
        if ev.block: return ev.reply
        msgs.append(user(human_act, ev.annotations))
        for step in range(40):
            ctx = assemble(constitution, EIDE_md, reminders=[...], skills)
            rsp = llm.stream(ctx, msgs, tools=tools.visible())
            if not rsp.tool_calls: break
            for call in rsp.tool_calls:
                pre  = hooks.pre_tool_use(call)
                perm = policy.decide(call, pre)
                res  = tools.run(call) if perm.allow else error(perm.reason)
                hooks.post_tool_use(call, res)
                msgs.append(tool_result(call.id, res))
            if ctx.tokens > 0.7 * window: msgs = compact(msgs)
        hooks.stop(msgs)

Điều quan trọng nhất về kiến trúc này, và là lý do v3 bỏ máy trạng thái S0–S6: **không
có đường nào đi vòng qua ba lớp xác định**. Mô hình muốn làm gì cũng phải qua
`pre_tool_use → policy.decide → post_tool_use`. Trong kiến trúc cũ, một nút hỏng giữa
chuỗi làm cả lượt chết tại chỗ; ở đây lỗi quay về mô hình như dữ liệu, kèm hướng dẫn,
và nó đổi hướng.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .du_an import ThongTinDuAn
from .config import Config
from .context import assemble
from .errors import EideError, budget_exhausted, gate_pending
from .hooks import HookBus, S0Engine
from .hooks.standard import register_standard_hooks
from .ids import IdGen
from . import memory as mem
from .memory import boc_ket_qua
from .memory.transcript import KhoPhien, phuc_hoi as _phuc_hoi
from .policy import PolicyEngine
from .protocol import HumanAct
from .protocol import uicommand as uic
from .protocol.ledger import Ledger
from .store import EideMd, Store, inventory
from .tools import Registry, build_registry


# =========================================================================== ngữ cảnh lượt
@dataclass
class TurnContext:
    """Mọi thứ một công cụ hoặc một hook cần biết về lượt đang chạy."""

    config: Config
    store: Store
    ledger: Ledger
    eide_md: EideMd
    ids: IdGen
    registry: Registry
    emit: Callable[[Any], None]

    history: Any = None
    agent: Any = None          # để `memory.compact` gọi ngược vào vòng lặp
    run_id: str = ""
    started_at: float = 0.0
    tool_calls_used: int = 0
    ask_rounds: int = 0
    awaiting_human: bool = False
    said_anything: bool = False

    pending_cards: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    assumptions_stated: list[str] = field(default_factory=list)
    human_edits: list[dict[str, Any]] = field(default_factory=list)
    project_name: str = ""
    # Tệp tác tử đang sửa trong lượt này — soft-lock (§E4 bước 1, ca CX09).
    locks: set[str] = field(default_factory=set)
    thoi_diem_ket_thuc: dict[str, float] = field(default_factory=dict)
    # Mọi câu tác tử đã NÓI RA trong lượt. Hook Stop và phép đánh dấu "đã nhắc" đọc
    # cái này, chứ không hỏi mô hình xem nó có nghĩ là đã nói hay chưa.
    loi_da_noi: list[str] = field(default_factory=list)
    # Tên công cụ đã gọi trong lượt, theo thứ tự — để nói được "tôi đã làm gì" khi phải
    # dừng giữa chừng vì hết ngân sách.
    cong_cu_da_goi: list[str] = field(default_factory=list)
    # Lượt này đã GHI được gì chưa (tệp hoặc hiện vật). Dùng để phân biệt "đang tìm hiểu"
    # với "đang quay vòng".
    da_ghi_gi_do: bool = False
    da_nhac_quay_vong: set[str] = field(default_factory=set)
    # Công cụ đã bị nhắc "ok mà kết quả rỗng" trong lượt này. Nhắc lại mỗi lần gọi sẽ thành
    # tiếng ồn, và tiếng ồn thì bị bỏ qua — kể cả lần nó đáng đọc.
    da_nhac_rong: set[str] = field(default_factory=set)
    # Lượt này đã bị bắt tự kiểm chứng chưa. Vòng thứ hai là vòng tác tử đang TRẢ LỜI lời
    # nhắc ấy; bắt nó kiểm lại lần nữa sẽ thành vòng lặp.
    da_tu_kiem: bool = False
    # Tệp tác tử đã ĐỌC trong lượt này — `fs.write` đòi đọc trước khi đè (§E4, N9).
    da_doc: set[str] = field(default_factory=set)
    # Lời NGƯỜI đã nói trong phiên — constant-guard coi con số họ tự nói là có nguồn.
    loi_nguoi_trong_phien: list[str] = field(default_factory=list)
    usage_luot: Any = None                       # chi phí CỦA LƯỢT NÀY, không phải phiên
    phan_loai_sua: Any = None                    # §E4.1 — loại sửa của người trong lượt
    fact_nguoi_moi: list[dict[str, Any]] = field(default_factory=list)
    # Tài liệu đã nạp trong phiên — giữ nguyên văn theo trang để trích Fact và trả lời
    # có trích trang. Không nằm trong kho vì nội dung PDF lớn và không cần phiên bản.
    tai_lieu: dict[str, Any] = field(default_factory=dict)

    def mark_agent_read(self, path: str) -> None:
        """Ghi nhận tác tử đã ĐỌC một tệp trong lượt này.

        Dùng cho một luật chứ không để thống kê: `fs.write` không được đè một tệp đang có mà
        tác tử chưa đọc. Xem `fs_write`.
        """
        self.da_doc.add(path)

    def mark_agent_wrote(self, path: str) -> None:
        """Soft-lock: cảnh báo người, nhưng VẪN cho họ sửa (§E4 bước 1).

        Khoá cứng sẽ biến tác tử thành cái chắn đường. Ca CX09 đo đúng chuyện người phá
        khoá, nên phá khoá phải là một đường đi hợp lệ chứ không phải một lỗi.
        """
        if path not in self.locks:
            self.locks.add(path)
            self.emit(uic.surface_lock("code", block=path, by=self.run_id,
                                       why="Tác tử đang sửa tệp này"))

    def build_inventory(self):
        return inventory.build(self.store, ledger=self.ledger,
                               project_name=self.project_name,
                               pending_cards=self.pending_cards)

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self.started_at

    def budget_left(self) -> tuple[int, float]:
        b = self.config.budget
        return b.max_tool_calls - self.tool_calls_used, b.max_seconds - self.elapsed


class DanhSachGhiDia(list):
    """`list` các message, nhưng mỗi lần thêm đều xuống đĩa trước.

    Vì sao là một lớp chứ không phải "nhớ gọi thêm một dòng ở mười chỗ append": bất
    biến write-ahead chỉ có giá trị khi nó đúng ở **mọi** đường. Một chỗ quên là một
    lượt mất sau sự cố, và chỗ quên đó sẽ là chỗ thêm vào sau này chứ không phải chỗ
    đang có hôm nay.
    """

    def __init__(self, ts: Any):
        super().__init__()
        self._ts = ts

    def append(self, m: dict[str, Any]) -> None:     # type: ignore[override]
        self._ts.ghi(m)
        super().append(m)


# =========================================================================== tác tử
def _tach_kieu_chan(o: str) -> dict[str, str]:
    """`"7=power_in, 27=bidirectional"` → `{"7": "power_in", "27": "bidirectional"}`.

    Đây là dạng mà ô bảng A5.8c hiện ra, nên nó cũng là dạng người sửa. Cặp nào không có dấu
    `=` thì bỏ qua — người gõ thiếu không được làm mất phần họ gõ đúng.
    """
    ra: dict[str, str] = {}
    for phan in o.replace(";", ",").split(","):
        so, sep, kieu = phan.partition("=")
        if sep and so.strip() and kieu.strip():
            ra[so.strip()] = kieu.strip()
    return ra


class Agent:
    """Một phiên làm việc: giữ transcript, thẻ chờ và cổng chờ qua nhiều lượt."""

    def __init__(self, config: Config, *, llm: Any, registry: Registry | None = None,
                 policy: PolicyEngine | None = None, s0: S0Engine | None = None,
                 project_name: str = ""):
        self.config = config
        self.llm = llm
        self.registry = registry or build_registry(self.config.features)
        # Công cụ tác tử đã tự viết cho dự án NÀY — nạp lại khi mở, nếu không thì một năng
        # lực nó đã xây (và người dùng đã duyệt) chỉ sống được đúng một phiên.
        from .nang_luc import nap_cong_cu_tu_viet

        self.cong_cu_tu_viet = nap_cong_cu_tu_viet(
            self.registry, self.config.paths.project_root)
        self.policy = policy or PolicyEngine(autonomy=config.autonomy)
        self.s0 = s0 or S0Engine()
        self.hooks = register_standard_hooks(HookBus())

        p = config.paths
        self.ledger = Ledger(p.ledger)
        self.store = Store(p.store_db)
        self.ids = IdGen(p.state_dir)
        self.eide_md = EideMd.load(p.eide_md, create_name=project_name or p.project_root.name)
        self.project_name = project_name or p.project_root.name

        # Lịch sử phải dựng SAU kho và sổ cái (nó dùng cả hai) và TRƯỚC lượt đầu tiên
        # (nó khởi tạo kho git của dự án).
        from .history import History
        self.history = History(paths=p, store=self.store, ledger=self.ledger,
                               ids=self.ids, eide_md=self.eide_md)

        # M1 trên đĩa (MEM-42 §7.2). Trước bước MEM-B, `messages` chỉ sống trong RAM:
        # lõi chết giữa lượt là mất sạch ngữ cảnh mô hình.
        self.phien = KhoPhien(p.state_dir / "sessions")
        self.session_id = self.ids.next("ses")
        self.transcript = self.phien.transcript(self.session_id)
        self.phuc_hoi = self._doc_phien_do()
        # Tấm thẻ căn cước của dự án, ghi ngay khi mở — xem `du_an.py`.
        #
        # Ghi ở ĐÂY chứ không chỉ ở cuối lượt: một dự án vừa mở rồi đóng ngay cũng phải có
        # tệp ấy, nếu không thì thư mục nhìn từ ngoài vẫn là một mớ không tên.
        self.thong_tin = ThongTinDuAn(p.project_root)
        self._ghi_thong_tin()
        self.bo_nen = mem.BoNen(llm=llm, ledger=self.ledger, store=self.store,
                                eide_md=self.eide_md, transcript=self.transcript)
        self.nhat_ky_nen: list[dict[str, Any]] = []
        self.bo_nho_nguoi = mem.BoNhoNguoiDung()
        # Khối <resume> chỉ tiêm MỘT LẦN, ở lượt đầu của phiên (§7.5).
        self.can_resume = True

        self.messages: list[dict[str, Any]] = DanhSachGhiDia(self.transcript)
        self.dang_nhin: str = "project"          # bề mặt người đang mở (HumanAct attend)
        self.pending_cards: list[dict[str, Any]] = []
        # Có việc đã GHI mà chưa ai kiểm chứng độc lập chưa? Cờ này sống qua nhiều lượt, và
        # đó là điểm chính.
        #
        # Bản đầu của hook `tu_kiem_khi_tuyen_dat` chỉ nổ khi LƯỢT NÀY có ghi. Đo trên phiên
        # FreeRTOS: nó không nổ lần nào — vì lời tuyên "xong" gần như luôn nằm ở một lượt
        # BÁO CÁO, còn việc thì đã ghi ở các lượt trước. Điều kiện ấy giết đúng cái ca nó
        # sinh ra để bắt.
        self.ghi_chua_kiem = False
        self.pending_gates: dict[str, dict[str, Any]] = {}
        # (công cụ, cổng) đã được người duyệt trong LƯỢT VIỆC hiện tại. Xoá ở đầu mỗi câu mới.
        self._cong_cu_da_duyet: set[tuple[str, str]] = set()
        self.assumptions: list[str] = []
        self.last_report: dict[str, Any] = {}
        self.locks: set[str] = set()             # tệp tác tử đang giữ soft-lock
        self.thoi_diem_ket_thuc: dict[str, float] = {}
        self.loi_nguoi: list[str] = []           # mọi câu người đã gõ trong phiên
        self.usage_phien: Any = None             # chi phí cộng dồn cả phiên
        self.tai_lieu: dict[str, Any] = {}       # tài liệu đã nạp, theo doc_id

    def _doc_phien_do(self) -> Any:
        """Phiên trước có kết thúc sạch không? Nếu không, đọc lại và soi việc dở dang.

        Không tự nạp lại transcript cũ vào ngữ cảnh — đó là resume đầy đủ (§7.5), việc
        của MEM-C. Ở đây chỉ trả lời đúng một câu mà MEM14 hỏi: **công cụ nào đã bắt
        đầu mà không có kết quả**, và trong đó cái nào đổi thứ bên ngoài.
        """
        truoc = self.phien.gan_nhat(tru=self.session_id)
        if not truoc or self.phien.ket_thuc_sach(truoc):
            return None
        bc = _phuc_hoi(self.phien.transcript(truoc), truoc)
        if bc.goi_dang_do or bc.dong_hong:
            self.ledger.append("incident", {
                "code": "E_PHIEN_DO", "session": truoc,
                "message_vi": (f"Phiên {truoc} dừng giữa chừng: {len(bc.goi_dang_do)} "
                               f"lời gọi công cụ không có kết quả, {bc.dong_hong} dòng hỏng."),
                "goi_dang_do": bc.goi_dang_do})
        return bc

    def _ghi_thong_tin(self) -> None:
        """Cập nhật `du-an.json`. Không được làm hỏng lượt chạy — xem `ThongTinDuAn.ghi`."""
        try:
            self.thong_tin.ghi(ten=self.project_name, store=self.store,
                               ledger=self.ledger, eide_md=self.eide_md)
        except Exception:                                              # noqa: BLE001
            pass

    def dong_phien(self) -> None:
        """Đánh dấu phiên kết thúc sạch — để lần mở sau biết không cần phục hồi."""
        self.phien.danh_dau_ket_thuc(self.session_id)

    # ------------------------------------------------------------------ một lượt
    def turn(self, act: HumanAct, emit: Callable[[Any], None]) -> None:
        run_id = self.ids.next("run")
        ctx = TurnContext(config=self.config, store=self.store, ledger=self.ledger,
                          eide_md=self.eide_md, ids=self.ids, registry=self.registry,
                          emit=emit, history=self.history, agent=self, run_id=run_id,
                          started_at=time.perf_counter(),
                          pending_cards=self.pending_cards, assumptions=self.assumptions,
                          project_name=self.project_name, locks=self.locks,
                          thoi_diem_ket_thuc=self.thoi_diem_ket_thuc,
                          # N9 — sửa của người mà tác tử chưa nhắc tới. Hook Stop đọc
                          # đúng danh sách này để bắt thêm một vòng (CX07).
                          human_edits=[cs.to_dict() for cs in
                                       self.history.log.human_unacknowledged()],
                          loi_nguoi_trong_phien=self.loi_nguoi,
                          tai_lieu=self.tai_lieu)
        # Mọi lời tác tử nói ra đều đi qua đây, nên "đã nói gì chưa" là một sự thật đo
        # được chứ không phải một phỏng đoán.
        def ghi_lai(cmd):
            if cmd.method == "console.post" and cmd.params.get("role") == "agent":
                ctx.loi_da_noi.append(cmd.params.get("text", ""))
                ctx.said_anything = True
            emit(cmd)
        ctx.emit = ghi_lai

        if act.text:
            self.loi_nguoi.append(act.text)
        if act.note:
            self.loi_nguoi.append(act.note)
        # Chữ người gõ vào thẻ cũng là LỜI NGƯỜI — cùng hạng với câu họ gõ vào ô nhập.
        # Không tính nó thì mọi chốt chặn kiểu "thứ này phải do người nói ra" sẽ chặn
        # nhầm đúng lúc người vừa nói ra.
        for v in (act.data.get("answers") or {}).values():
            if str(v).strip():
                self.loi_nguoi.append(str(v))

        self.ledger.append("turn.start", {"run_id": run_id, "act_id": act.id,
                                          "kind": act.kind, "text": act.text})

        # Chuyển tab không phải một "lượt chạy": không hiện thẻ Run, không vẽ lại bề
        # mặt, không gọi mô hình. Chỉ ghi sổ để phát lại được (DEV-226).
        im_lang = act.kind == "attend"
        if not im_lang:
            emit(uic.run_update(run_id, status="running", steps=[]))

        try:
            self._run(act, ctx)
            # Lượt kết thúc mà tác tử KHÔNG nói câu nào là một lượt người dùng không đọc
            # được. Đã gặp thật: mô hình gọi mười công cụ để đọc mã rồi trả về một câu trả
            # lời rỗng; trên màn hình, EIDE đứng im và người dùng đợi một tệp không bao giờ
            # tới. Im lặng không phải một câu trả lời, kể cả khi không có gì để nói.
            if not im_lang and not ctx.said_anything and act.kind not in ("attend", "set"):
                ctx.emit(uic.console_post(
                    self._cau_im_lang(ctx), role="agent"))
        finally:
            self._ghi_nhan_da_nhac(ctx)
            self._tha_khoa(ctx)
            self.thoi_diem_ket_thuc[run_id] = time.time()
            report = self._report(ctx)
            self.last_report = report
            self.ledger.append("turn.end", {"run_id": run_id, **report})
            self._ghi_thong_tin()
            if not im_lang:
                emit(uic.run_update(
                    run_id, status="waiting" if ctx.awaiting_human else "done",
                    cost=report["cost"], assumptions=self.assumptions,
                    buttons=["Hoàn tác lượt", "Ghi bản ưng ý"]))
                # I3 — giao diện chỉ render thứ lõi gửi. Vẽ lại bề mặt SAU khi sổ cái
                # đã chốt lượt, để tab Nhật ký thấy được cả dòng kết thúc lượt.
                self.paint(emit, run=report)

    # ------------------------------------------------------------------ vẽ bề mặt
    def paint(self, emit: Callable[[Any], None], *, run: dict[str, Any] | None = None,
              only: list[str] | None = None) -> None:
        """Dựng và gửi SurfaceModel cho các tab (§D, §E2, §E7).

        `run` bỏ trống thì lấy **báo cáo lượt gần nhất**, không lấy rỗng. `emit_all` luôn gửi
        kèm thanh trạng thái, nên một lần vẽ lại cục bộ — `paint(only=["history"])` sau khi
        người ghi bản ưng ý hay rẽ nhánh — sẽ đẩy `da_dung_tool = 0` lên màn hình và **bộ đếm
        chạy ngược về không** ngay giữa một lượt còn đang chạy.

        Một con số đi lùi thì tệ hơn một con số đứng yên: đứng yên chỉ là chưa biết, còn đi lùi
        là nói sai.
        """
        run = run if run is not None else (self.last_report or None)
        from . import surfaces
        inv = inventory.build(self.store, ledger=self.ledger,
                              project_name=self.project_name,
                              pending_cards=self.pending_cards)
        surfaces.emit_all(emit, store=self.store, ledger=self.ledger, eide_md=self.eide_md,
                          inv=inv, cfg=self.config, assumptions=self.assumptions,
                          run=run, only=only, hist=self.history,
                          ngu_canh=self.ngu_canh_hien_tai(),
                          bo_nho_kw=self._mat_bang_bo_nho())

    def _mat_bang_bo_nho(self) -> dict[str, Any]:
        """Dữ liệu cho khối A14.6 — thứ người nhìn để biết tác tử đang nhớ gì (P6)."""
        ghim = []
        for i in mem.chi_so_ghim(self.messages):
            m = self.messages[i]
            ghim.append({"vi_sao": ("người ghim" if m.get("_ghim") else
                                    f"ý chí: {m.get('_kind', '?')}"),
                         "chu": str(m.get("text") or "")[:200]})
        return {
            "ngu_canh": self.ngu_canh_hien_tai(),
            "tom_tat": self.bo_nen.tom_tat_hien_tai,
            "ghim": ghim,
            "nhat_ky_nen": self.nhat_ky_nen,
            "bo_nho_nguoi": self.bo_nho_nguoi,
            "da_quen": [e.data for e in self.ledger.read() if e.kind == "tombstone"],
        }

    def ngu_canh_hien_tai(self) -> dict[str, Any]:
        """Đồng hồ ngữ cảnh cho thanh trạng thái (MEM-02).

        Dựng lại phần cố định bằng `_assemble` thay vì nhớ lần lắp gần nhất: con số
        người nhìn phải là con số của LÚC NÀY, không phải của lượt trước.
        """
        from . import surfaces
        inv = inventory.build(self.store, ledger=self.ledger,
                              project_name=self.project_name,
                              pending_cards=self.pending_cards)
        recent = [m.get("text", "") for m in self.messages[-6:] if m.get("role") == "user"]
        asm = assemble(
            eide_md=self.eide_md, inventory_text=inv.render(), store=self.store,
            recent_texts=recent or [""],
            human_edit_changesets=[cs.to_dict() for cs
                                   in self.history.log.human_unacknowledged()],
            pending_cards=self.pending_cards,
            stopped_run=inv.unfinished_run,
            assumptions=self.assumptions,
            plan=self._plan_cho_ngu_canh(),
            budget=self.config.context_budget)
        return surfaces.dong_ho_ngu_canh(asm, self.messages, self.config)

    # ------------------------------------------------------------------ thân
    def _run(self, act: HumanAct, ctx: TurnContext) -> None:
        # --- Thao tác không cần mô hình: giải quyết bằng mã rồi về.
        if act.kind == "decide":
            return self._resolve_gate(act, ctx)
        if act.kind == "stop":
            ctx.emit(uic.console_post("Đã dừng.", role="agent"))
            ctx.said_anything = True
            return
        if act.kind in ("attend", "set"):
            return self._dieu_huong(act, ctx)
        if act.kind == "edit":
            return self._nguoi_sua(act, ctx)
        if act.kind == "undo":
            return self._nguoi_hoan_tac(act, ctx)
        if act.kind == "snapshot":
            return self._nguoi_ghi_ban(act, ctx)
        if act.kind == "branch":
            return self._nguoi_re_nhanh(act, ctx)
        if act.kind == "choose":
            # Thẻ đã được trả lời thì phải rời khỏi `<pending>`. Nếu không, khối nhắc
            # vẫn bảo mô hình "còn thẻ đang chờ người trả lời" ở mọi lượt sau, và nó sẽ
            # hỏi lại đúng câu người vừa trả lời.
            ma = act.data.get("card_id")
            the = next((c for c in self.pending_cards if c.get("card_id") == ma), None)
            self.pending_cards[:] = [c for c in self.pending_cards
                                     if c.get("card_id") != ma]
            tl = act.data.get("answers") or {}
            self.ledger.append("card", {"run_id": ctx.run_id, "card_id": ma,
                                        "state": "answered", "keys": sorted(tl)})
            # I3 — giao diện chỉ đóng thẻ khi LÕI bảo đóng. Thiếu lệnh này thì thẻ đã
            # trả lời vẫn nằm trên Console và băng "còn thẻ đang chờ anh" vẫn sáng.
            ctx.emit(uic.card_resolve(str(ma), by="human", choice=tl or None))
            # Thẻ do snapshot.propose dựng: câu trả lời CHÍNH LÀ việc phải làm. Không
            # đẩy sang mô hình — tên đã có, nội dung do kho quyết định, 0 token.
            if the and the.get("tra_loi_thanh") == "nho_nguoi_dung":
                # §8 — chỉ ghi vào M3 khi người bấm đồng ý, không sớm hơn một giây nào.
                dl = the.get("du_lieu") or {}
                if "đồng ý" in str(tl.get("dong_y", "")).lower():
                    k = self.bo_nho_nguoi.ghi(dl.get("chu_de", ""), dl.get("noi_dung", ""))
                    ctx.emit(uic.console_post(
                        f"Đã nhớ: {dl.get('noi_dung')}" if k.ok
                        else f"Không ghi được: {k.ly_do}", role="agent"))
                else:
                    ctx.emit(uic.console_post(
                        "Không nhớ gì cả — tôi chỉ dùng trong phiên này.",
                        role="agent"))
                ctx.said_anything = True
                return

            if the and the.get("tra_loi_thanh") == "snapshot" and tl.get("ten"):
                return self._nguoi_ghi_ban(HumanAct.from_dict(
                    {"kind": "snapshot",
                     "data": {"name": tl["ten"], "note": tl.get("ghi_chu", "")},
                     "origin": {"surface": "console"}}), ctx)

        # Một câu mới của người dùng mở một LƯỢT VIỆC mới — quên mọi lần duyệt cổng của lượt
        # trước. Giữ lại qua lượt sẽ biến "duyệt một lần" thành "duyệt mãi mãi".
        self._cong_cu_da_duyet.clear()

        # --- S0: hook UserPromptSubmit, 0 token, đứng trước mọi phép đoán (N5).
        s0 = self.s0.run(act.text, attachments_text=act.data.get("_attachment_text", ""),
                         ledger=self.ledger, gate_id_factory=lambda: self.ids.next("gate"))
        self.ledger.append("hook", {"run_id": ctx.run_id, **s0.to_ledger()})

        if s0.reply_vi:
            ctx.emit(uic.console_post(f"{s0.reply_vi}", role="agent"))
            ctx.said_anything = True
        for n in s0.notices:
            ctx.emit(uic.notice(n["text"], level=n["level"], code=n["code"]))
        for card in s0.cards:
            ctx.emit(uic.console_post(_render_gate(card), role="agent", card=card))
            self.pending_cards.append(card)
            self.pending_gates[card["gate_id"]] = {"card": card, "call": None,
                                                   "run_id": ctx.run_id}
            self.ledger.append("gate", {"run_id": ctx.run_id, "gate_id": card["gate_id"],
                                        "gate": card["gate"], "rule": card["rule"],
                                        "state": "open"})
        if s0.block:
            ctx.awaiting_human = bool(s0.cards)
            return

        # --- Mở lại dự án: dựng khối <resume> bằng MÃ, không bằng trí nhớ (§7.5).
        if self.can_resume:
            self.can_resume = False
            khoi = mem.dung_khoi_resume(
                ledger=self.ledger, store=self.store, history=self.history,
                tom_tat_truoc=self.bo_nen.tom_tat_hien_tai, phuc_hoi=self.phuc_hoi)
            if khoi:
                self.messages.append({"role": "user", "_he_thong": True,
                                      "_ghim": True, "text": khoi})

        # --- Phiên trước dừng giữa chừng: nói ra TRƯỚC khi mô hình làm gì tiếp (MEM14).
        if self.phuc_hoi is not None and self.phuc_hoi.goi_dang_do:
            self.messages.append({"role": "user", "_he_thong": True,
                                  "text": self.phuc_hoi.nhac_vi()})
            if self.phuc_hoi.can_hoi_nguoi:
                ctx.emit(uic.notice(
                    "Phiên trước dừng giữa chừng khi đang chạy "
                    + ", ".join(g["tool"] for g in self.phuc_hoi.goi_dang_do
                                if g["co_tac_dung_phu"])
                    + ". Không rõ nó đã xong chưa — tôi sẽ không chạy lại, anh kiểm giúp.",
                    level="warn", code="E_PHIEN_DO"))
                ctx.said_anything = True
            self.phuc_hoi = None            # nhắc đúng một lần, không lặp mỗi lượt

        # --- Lượt của người vào transcript, kèm khối nhắc.
        #
        # `_kind` là thứ quyết định message này có bị nén không (§5.4): quyết định, xác
        # nhận, sửa, ghi bản ưng ý, đổi thiết lập — đều là Ý CHÍ của người, và nén mất
        # ý chí của người là làm ngược ý họ.
        self.messages.append({"role": "user", "_kind": act.kind,
                              "text": self._user_block(act, ctx, s0.annotations)})

        # --- Vòng lặp công cụ.
        extra_round_used = False
        while True:
            self._tool_loop(ctx, s0)
            stop = self.hooks.stop(ctx)
            self.ledger.append("hook", {"run_id": ctx.run_id, "hook": "Stop",
                                        "another_round": stop.another_round,
                                        "reason": stop.reason_vi, "checks": stop.fired})
            if not stop.another_round or extra_round_used or ctx.awaiting_human:
                break
            # Chỉ cho đúng MỘT vòng thêm: hook Stop nhắc là để sửa sót, không phải để
            # kéo dài lượt vô hạn khi mô hình cứ lờ đi.
            extra_round_used = True
            self.messages.append({"role": "user", "text": stop.injection})

    # Bao nhiêu lần gọi cùng một công cụ ĐỌC mà chưa ghi gì thì coi là đang quay vòng.
    # 6 là con số đo được: trên một lượt thật, tác tử gọi `ledger.query` 21 lần liên tiếp để
    # tìm một tệp nó sắp phải tự viết, rồi hết ngân sách mà chưa viết dòng nào.
    NGUONG_QUAY_VONG = 6          # cùng MỘT công cụ gọi bấy nhiêu lần
    NGUONG_TONG_DOC = 10          # tổng lời gọi CHỈ-ĐỌC, rải trên bao nhiêu công cụ cũng tính
    _CONG_CU_DOC = ("fs.read", "fs.glob", "fs.grep", "fs.stat", "fact.query", "store.get",
                    "store.list", "ledger.query", "doc.read", "tool.search", "ckm.graph",
                    "inventory.get", "memory.read", "blob.read",
                    # Ba công cụ tự-soi-mình này vắng mặt trong bản trước, nên một lượt trôi
                    # hết vào việc đọc lại lịch sử của chính nó không bị tính là quay vòng.
                    "history.list", "history.diff", "snapshot.list")

    def _nhac_neu_dang_quay_vong(self, ctx: TurnContext) -> str:
        """Nhắc khi tác tử TÌM mãi mà không LÀM. Nhắc một lần cho mỗi công cụ, không càm ràm.

        Vì sao lõi phải nói câu này thay vì để mô hình tự nhận ra: mô hình không thấy được
        lượt của chính nó từ bên ngoài. Nó thấy từng lời gọi một, mỗi lời gọi đều hợp lý, và
        không có chỗ nào để nhận ra rằng hai mươi lời gọi vừa rồi không đưa việc tiến lên
        được một bước. Ngân sách 40 lời gọi cạn trong im lặng là kết quả tự nhiên của chỗ mù
        đó — và người dùng là người trả giá.
        """
        from collections import Counter

        goi = getattr(ctx, "cong_cu_da_goi", []) or []
        if getattr(ctx, "da_ghi_gi_do", False) or len(goi) < self.NGUONG_QUAY_VONG:
            return ""
        da_nhac = getattr(ctx, "da_nhac_quay_vong", None)
        if da_nhac is None:
            da_nhac = set()
            ctx.da_nhac_quay_vong = da_nhac
        chi_doc = [t for t in goi if t in self._CONG_CU_DOC]
        dem = Counter(chi_doc)
        ten, n = dem.most_common(1)[0] if dem else ("", 0)

        # HAI cách nhận ra "tìm mãi mà không làm", vì một cách bỏ sót ca thật sau:
        #
        #   ledger.query → fs.glob ×5 → store.list → store.get → ledger.query
        #                → history.list → ledger.query ×4
        #
        # Mười bốn lời gọi chỉ-đọc, không ghi gì, rõ ràng là đang quay vòng — nhưng phép đếm
        # THEO TỪNG TÊN không chạm ngưỡng nào cho tới lời gọi thứ mười bốn, và tới lúc đó lượt
        # đã hết. Trải việc tìm ra nhiều công cụ khác nhau không làm nó bớt là quay vòng.
        if n >= self.NGUONG_QUAY_VONG and ten and ten not in da_nhac:
            da_nhac.add(ten)
            vi_sao = f"đã gọi `{ten}` {n} lần"
        elif len(chi_doc) >= self.NGUONG_TONG_DOC and "_tong" not in da_nhac:
            da_nhac.add("_tong")
            vi_sao = (f"đã gọi {len(chi_doc)} lời gọi CHỈ-ĐỌC "
                      f"({', '.join(f'{k}×{v}' for k, v in dem.most_common(4))})")
        else:
            return ""
        return (
            f"[EIDE] Lượt này bạn {vi_sao} và chưa ghi được gì — "
            f"{len(goi)}/{self.config.budget.max_tool_calls} lời gọi đã dùng. Dừng tìm lại. "
            "Chọn một trong BỐN: (1) làm việc chính bằng dữ kiện đang có; (2) nói thẳng với "
            "người dùng là bạn chưa tìm ra thứ gì và hỏi họ; (3) nếu việc quá lớn cho một "
            "lượt thì làm phần đầu rồi báo lại; "
            # Lựa chọn thứ tư, và nó là lựa chọn duy nhất đổi được tình hình cho LẦN SAU.
            #
            # Đo được trên phiên bo STM32F469: tác tử có `pc = 0x08000db0`, cần biết hàm nào
            # ở đó, và gọi `fs.read` 28 lần rồi hết hạn mức mà vẫn chưa chắc. `addr2line`
            # trả lời trong 40 ms. Nó không thiếu thông minh — nó thiếu CÁI MIỆNG để nói
            # "tôi cần một công cụ", nên ba lựa chọn trên đều dẫn nó quay lại cày tay.
            "(4) **cày tay nhiều thế này thường là dấu hiệu THIẾU CÔNG CỤ, không phải thiếu "
            "cố gắng** — nếu có một công cụ trả lời được câu hỏi này trong một lời gọi, xin "
            "tự viết nó bằng `tool.propose` (kèm chính số đo vừa rồi làm lý do). "
            "Đừng tìm tiếp bằng một truy vấn khác cho cùng một câu hỏi.")

    def _cau_im_lang(self, ctx: TurnContext) -> str:
        """Câu thay cho sự im lặng: nói đã làm gì và mời người dùng đẩy tiếp."""
        from collections import Counter

        dem = Counter(getattr(ctx, "cong_cu_da_goi", []) or [])
        if not dem:
            return ("Tôi kết thúc lượt mà không làm gì và cũng không nói gì — đó là lỗi của "
                    "tôi, không phải ý anh. Anh nhắc lại yêu cầu giúp tôi, hoặc nói rõ bước "
                    "đầu tiên anh muốn tôi làm.")
        hay = ", ".join(f"{t} ×{n}" for t, n in dem.most_common(3))
        return (f"Tôi đã gọi {sum(dem.values())} công cụ ({hay}) rồi dừng mà chưa nói gì — "
                "nghĩa là tôi chưa hoàn thành việc anh giao và cũng chưa báo lại. Những gì "
                "đã ghi thì vẫn còn. Anh bảo “làm tiếp” để tôi chạy tiếp, hoặc chia nhỏ yêu "
                "cầu ra nếu nó quá dài cho một lượt.")

    def _cau_het_ngan_sach(self, ctx: TurnContext, kind: str, lim: Any) -> str:
        """Nói rõ: đã làm gì, dừng ở đâu, và người dùng cần gõ gì để đi tiếp."""
        from collections import Counter

        dem = Counter(t for t in getattr(ctx, "cong_cu_da_goi", []) or [])
        hay = ", ".join(f"{t} ×{n}" for t, n in dem.most_common(3))
        return ("Tôi hết " + kind + f" của lượt này ({lim}) nên phải dừng giữa chừng — "
                "chưa xong việc anh giao."
                + (f" Lượt này tôi đã gọi {sum(dem.values())} công cụ, nhiều nhất là {hay}."
                   if dem else "")
                + " Những gì đã ghi vào kho và vào tệp thì vẫn còn nguyên. Anh bảo “làm tiếp”"
                  " là tôi chạy tiếp từ chỗ này; nếu muốn nhanh hơn thì nói rõ phần nào làm"
                  " trước, để tôi khỏi đọc lại những thứ đã đọc.")

    def _tool_loop(self, ctx: TurnContext, s0: Any) -> None:
        while True:
            left_calls, left_secs = ctx.budget_left()
            if left_calls <= 0 or left_secs <= 0:
                kind = "số lời gọi công cụ" if left_calls <= 0 else "thời gian"
                lim = (self.config.budget.max_tool_calls if left_calls <= 0
                       else f"{self.config.budget.max_seconds:.0f} s")
                err = budget_exhausted(kind, lim)
                ctx.emit(uic.notice(err.message_vi, level="warn", code=err.code))
                # Và NÓI RA trong hội thoại, không chỉ treo một băng cảnh báo.
                #
                # Đo được trên một phiên thật: tác tử dùng hết 40 lời gọi để đọc tài liệu rồi
                # lượt kết thúc — trên màn hình, nó im lặng. Người dùng đợi một tệp mã nguồn
                # không bao giờ tới và không có cách nào biết vì sao. Một băng cảnh báo ở góc
                # không phải một câu trả lời cho câu hỏi "nó đang làm gì vậy".
                ctx.emit(uic.console_post(
                    self._cau_het_ngan_sach(ctx, kind, lim), role="agent"))
                ctx.said_anything = True
                return

            asm = self._assemble(ctx, s0)
            stream_id = f"{ctx.run_id}-s{ctx.tool_calls_used}"
            try:
                rsp = self.llm.stream(
                    system=asm.system_instruction, messages=self.messages,
                    tools=self.registry.declarations(),
                    on_text=lambda d: ctx.emit(uic.console_stream(d, stream_id=stream_id)))
            except EideError as e:
                # UC19: hỏng thì dừng an toàn, nói thật, không mất việc đã làm.
                self.ledger.append("incident", {"run_id": ctx.run_id, **e.to_tool_result()})
                ctx.emit(uic.console_stream("", stream_id=stream_id, done=True))
                ctx.emit(uic.console_post(f"{e.message_vi}", role="agent"))
                ctx.said_anything = True
                return

            ctx.emit(uic.console_stream("", stream_id=stream_id, done=True))
            self.ledger.append("llm_call", {"run_id": ctx.run_id, "model": rsp.model,
                                            "usage": rsp.usage.to_dict(),
                                            "tool_calls": [c.tool for c in rsp.tool_calls],
                                            "elapsed_ms": round(rsp.elapsed_ms, 1)})
            self._usage_add(rsp.usage, ctx)

            if rsp.text.strip():
                ctx.emit(uic.console_post(f"{rsp.text.strip()}", role="agent"))
                ctx.said_anything = True
                self._note_stated_assumptions(ctx, rsp.text)

            self.messages.append(rsp.to_message())
            if not rsp.tool_calls:
                return

            self._nhip(ctx)          # token vừa tiêu — nói ngay, đừng đợi hết lượt

            for call in rsp.tool_calls:
                self._one_tool(call, ctx)
                self._nhip(ctx)      # bộ đếm công cụ và giây, sau MỖI lời gọi
                if ctx.awaiting_human:
                    return
            nhac = self._nhac_neu_dang_quay_vong(ctx)
            if nhac:
                self.messages.append({"role": "user", "_he_thong": True, "text": nhac})

            muc = self.config.context_budget.muc_nen(self._context_pressure(asm))
            if muc != "C0":
                self._compact(ctx, muc)

    # ------------------------------------------------------------------ plan mode
    def _ke_hoach(self) -> Any:
        """Kế hoạch hiện tại trong kho, bất kể trạng thái. `None` nếu chưa có."""
        from .ke_hoach import MA_KE_HOACH, KeHoach

        a = self.store.get(MA_KE_HOACH)
        return KeHoach.from_dict(a.get("canonical") or {}) if a else None

    # Công cụ chỉ dùng được KHI ĐANG CÓ kế hoạch đã duyệt. Chúng là `core=False` để không
    # tốn lược đồ ở mọi phiên; nhưng lúc đang giữa một kế hoạch thì chúng phải NHÌN THẤY ĐƯỢC.
    _CONG_CU_KHI_CO_KE_HOACH = ("plan.step_done", "plan.merge", "plan.cancel")

    def _mo_khoa_theo_ngu_canh(self) -> None:
        """Mở khoá những công cụ chỉ dùng được TRONG MỘT TÌNH HUỐNG, đúng lúc tình huống ấy tới.

        Chúng để `core=False` cho khỏi tốn lược đồ ở mọi lượt. Nhưng `core=False` nghĩa là tác
        tử **không nhìn thấy** cho tới khi nó `tool.search` — và nó chỉ tìm khi nó biết có thứ
        để tìm. Đây là hình dạng lỗi lặp lại nhiều nhất trong dự án này (xem DEV-302, DEV-305).

        Đo được 30/09/2026: **31 trên 120 công cụ chưa nổ lần nào** trong mọi lượt chạy thật,
        và 25 trong số đó là `core=False`.
        """
        mo = getattr(self.registry, "_unlocked", None)
        if mo is None:
            return

        # `skill.load` — 8 skill hiện tên trong `<skills-hint>` MỖI LƯỢT, mà công cụ để nạp
        # chúng thì tác tử không nhìn thấy. Đo được: **0 lần nạp** trong toàn bộ lịch sử chạy.
        # Gợi ý một danh mục rồi giấu cái nút mở nó đi thì danh mục ấy chỉ tốn token.
        mo.add("skill.load")

        # `history.undo_30s` — cửa sổ hoàn tác KHÔNG cần thẻ cổng. Menu ⌥⌘Z của giao diện gửi
        # câu "Hoàn tác việc bạn vừa làm giúp mình", và tác tử lúc ấy chỉ thấy `history.undo`
        # (R2, cổng G-HIST) — nên nó dựng thẻ cổng cho một việc lẽ ra lùi được ngay. Đúng thứ
        # cửa sổ 30 giây sinh ra để tránh.
        #
        # Chỉ mở khi CÒN trong cửa sổ: hết 30 giây thì công cụ ấy chỉ trả lỗi, và một công cụ
        # luôn hiện mà luôn hỏng là một công cụ dạy người ta bỏ qua nó.
        import time as _t

        if any(_t.time() - x <= 30 for x in (self.thoi_diem_ket_thuc or {}).values()):
            mo.add("history.undo_30s")

        # `memory.undo_compact` — mở khoá sau khi ĐÃ nén lần nào đó trong phiên. Cửa sổ của nó
        # là 24 giờ, nên không hẹp như cửa sổ 30 giây; nhưng trước khi có lần nén đầu tiên thì
        # nó chỉ là một công cụ luôn trả lỗi.
        if getattr(self, "da_nen_lan_nao", False):
            mo.add("memory.undo_compact")

        self._mo_khoa_cong_cu_ke_hoach()

    def _mo_khoa_cong_cu_ke_hoach(self) -> None:
        """Có kế hoạch đã duyệt thì mở khoá `plan.step_done` / `plan.merge` / `plan.cancel`.

        Đo được 30/09/2026 qua giao diện thật: tác tử có kế hoạch ba bước ngay trong
        `<pending>`, được bảo *"làm tiếp"*, nó sửa tệp rồi dừng — **không gọi `plan.step_done`
        lần nào**. Kế hoạch đứng yên 0/3, không có gì để gộp, và không lỗi nào được ném ra.

        Lý do không phải nó lười: hai công cụ ấy là `core=False`, tức chỉ hiện ra sau một lần
        `tool.search`. Cùng hình dạng lỗi với hook kiểm chứng từng bảo tác tử gọi `task.run`
        mà không mở khoá — *bảo ai đó dùng một thứ họ không nhìn thấy thì không phải là bảo.*
        """
        if self._plan_cho_ngu_canh() is None:
            return
        mo = getattr(self.registry, "_unlocked", None)
        if mo is None:
            return
        for t in self._CONG_CU_KHI_CO_KE_HOACH:
            mo.add(t)

    def _plan_cho_ngu_canh(self) -> dict[str, Any] | None:
        """Kế hoạch ĐÃ DUYỆT, để `<pending>` nhắc lại mỗi lượt.

        Chỉ kế hoạch đã duyệt mới vào ngữ cảnh. Kế hoạch đang soạn không vào: nhắc lại bản
        nháp của chính mình mỗi lượt là cách nhanh nhất để tác tử chốt vào ý đầu tiên nó
        nghĩ ra, đúng lúc nó đang cần nghĩ rộng.
        """
        kh = self._ke_hoach()
        return kh.to_dict() if kh is not None and kh.trang_thai == "da_duyet" else None

    def _khoa_khi_soan_ke_hoach(self, call: Any, spec: Any) -> EideError | None:
        """Đang soạn (hoặc chờ duyệt) kế hoạch → khoá công cụ ghi. `None` = cho qua."""
        from .ke_hoach import cong_cu_bi_khoa

        kh = self._ke_hoach()
        if kh is None or kh.trang_thai not in ("dang_soan", "cho_duyet"):
            return None
        if not cong_cu_bi_khoa(spec):
            return None
        cho = ("đang chờ người dùng duyệt" if kh.trang_thai == "cho_duyet"
               else "đang soạn")
        return EideError(
            "E6005",
            f"`{call.tool}` là công cụ GHI, mà kế hoạch {cho} nên công cụ ghi đang bị khoá.",
            hint_for_agent=(
                "Đây là chế độ kế hoạch (§B5): trình cách làm trước khi tiêu lời gọi. Bạn "
                "vẫn đọc, tìm, đo và hỏi người dùng được — dùng chúng để soạn cho đủ bước. "
                + ("Kế hoạch đã nộp, đừng lách thẻ bằng cách làm tay; đợi người duyệt."
                   if kh.trang_thai == "cho_duyet" else
                   "Soạn xong thì gọi `plan.exit`; thấy việc không lớn như tưởng thì "
                   "`plan.cancel`.")),
            details={"trang_thai": kh.trang_thai, "muc_tieu": kh.muc_tieu},
            alternatives=["plan.exit", "plan.cancel"], blame="agent")

    # ------------------------------------------------------------------ một công cụ
    def _one_tool(self, call: Any, ctx: TurnContext) -> None:
        c = {"tool": call.tool, "args": call.args, "id": call.id}
        ctx.tool_calls_used += 1
        ctx.cong_cu_da_goi.append(call.tool)
        self.ledger.append("tool_use", {"run_id": ctx.run_id, "tool": call.tool,
                                        "args": call.args, "call_id": call.id})
        spec = self.registry.get(call.tool)

        # Plan mode: đang soạn kế hoạch thì mọi công cụ GHI bị khoá (§B5). Chặn ở ĐÂY, trước
        # cả hook và policy, vì đây là câu hỏi về *chế độ đang ở*, không phải về *quyền với
        # thao tác này*. Trộn hai thứ vào policy.yaml thì mỗi công cụ mới phải nhớ thêm một
        # dòng luật — và cái quên thêm sẽ đúng là cái lọt qua.
        chan = self._khoa_khi_soan_ke_hoach(call, spec)
        if chan is not None:
            return self._tool_error(call, chan, ctx, as_incident=False)

        pre = self.hooks.pre_tool_use(c, ctx)
        if not pre.ok and pre.error is not None:
            return self._tool_error(call, pre.error, ctx)

        perm = self.policy.decide(c, pre.facts, spec)
        self.ledger.append("hook", {"run_id": ctx.run_id, "hook": "policy",
                                    "tool": call.tool, **perm.to_ledger()})

        if perm.action == "deny":
            return self._tool_error(call, self.policy.deny_error(c, perm, pre.facts), ctx)

        if perm.action == "ask" and self._da_duyet_roi(call.tool, perm):
            # Đã duyệt công cụ này trong chính lượt việc này rồi thì không hỏi lại.
            #
            # Đo được trên phiên bo thật: một lượt "tự tìm tài liệu" dựng **16 thẻ cổng
            # G-DATA**, tất cả cho cùng một công cụ `doc.search_web`. Hỏi lại mỗi lần không làm
            # người dùng an toàn hơn — nó dạy người ta bấm Duyệt theo phản xạ, và khi một thẻ
            # ĐÁNG đọc hiện ra thì họ cũng bấm nốt. Cùng lý lẽ với chú thích ở `build.compile`
            # về việc không xếp nó R3.
            #
            # Cố ý KHÔNG nhớ cho: thao tác không hoàn tác được, thao tác `never_auto`, và mọi
            # thứ từ R4 trở lên — ba loại đó phải hỏi lại từng lần, kể cả lần thứ mười.
            import dataclasses as _dc

            self.ledger.append("gate", {"run_id": ctx.run_id, "gate": perm.gate,
                                        "tool": call.tool, "state": "da_duyet_truoc_do"})
            perm = _dc.replace(perm, action="allow",
                               reason_vi=(perm.reason_vi
                                          + " (đã duyệt cho công cụ này trong lượt này)"))

        if perm.action == "ask":
            gid = self.ids.next("gate")
            card = {"type": "gate", "card_id": gid, "gate_id": gid, "gate": perm.gate,
                    "rule": perm.rule_id, "title": perm.summary_vi or f"Duyệt {call.tool}",
                    "risk": getattr(spec, "risk", "R3"), "never_auto": perm.never_auto,
                    "irreversible": perm.irreversible,
                    "require_fields": perm.require_fields,
                    "tool": call.tool, "args": call.args,
                    "consequences_vi": _hau_qua(c, ctx, perm, spec),
                    "options": ["Duyệt", "Từ chối"]}
            ctx.emit(uic.console_post(_render_gate(card), role="agent", card=card))
            self.pending_cards.append(card)
            self.pending_gates[gid] = {"card": card, "call": c, "run_id": ctx.run_id}
            self.ledger.append("gate", {"run_id": ctx.run_id, "gate_id": gid,
                                        "gate": perm.gate, "tool": call.tool, "state": "open"})
            ctx.said_anything = True
            ctx.awaiting_human = True
            # I6: mô hình phải DỪNG, không được hỏi lại bằng lời để lách thẻ.
            return self._tool_error(
                call, gate_pending(perm.gate or "?", gid, perm.summary_vi), ctx, as_incident=False)

        res = self.registry.run(call.tool, call.args, ctx)
        self.hooks.post_tool_use(c, res, ctx)
        # "Đã ghi được gì chưa" — dùng để phân biệt một lượt đang tìm hiểu với một lượt đang
        # quay vòng. Lấy từ HỢP ĐỒNG công cụ, không từ tên nó: một công cụ mới thêm vào mà
        # có `writes_artefact` thì tự động tính, không phải nhớ cập nhật một danh sách.
        if res.ok and (getattr(spec, "writes_artefact", False)
                       or call.tool in ("fs.write", "fs.edit")):
            ctx.da_ghi_gi_do = True
            self.ghi_chua_kiem = True
        # Verifier vừa chạy → việc đã ghi coi như đã có người kiểm. Đọc `subagent` từ tham
        # số chứ không từ tên công cụ: `task.run` còn chạy năm loại tác tử con khác.
        if (res.ok and call.tool == "task.run"
                and (call.args or {}).get("subagent") == "verifier"):
            self.ghi_chua_kiem = False

        # `ok` nói về LỜI GỌI, không nói về KẾT QUẢ. Xem `eide/ket_qua.py` cho năm lần bài
        # học này xuất hiện trong một phiên duy nhất. Nhắc MỘT LẦN cho mỗi công cụ trong một
        # lượt: nhắc lại mỗi lần gọi sẽ thành tiếng ồn, và tiếng ồn thì bị bỏ qua.
        if res.ok:
            from .ket_qua import khong_noi_gi, nhac_nho

            rong, ly_do = khong_noi_gi(call.args or {}, res.data)
            if rong and call.tool not in ctx.da_nhac_rong:
                ctx.da_nhac_rong.add(call.tool)
                self.ledger.append("hook", {"run_id": ctx.run_id, "hook": "ket_qua_rong",
                                            "tool": call.tool, "ly_do": ly_do})
                self.messages.append({"role": "user", "_he_thong": True,
                                      "text": nhac_nho(call.tool, ly_do)})

        # MEM-42 §5.1 — kết quả KHÔNG đi nguyên văn vào transcript. Phần vượt trần nằm
        # ở blob và mô hình đọc lại bằng `blob.read`. Đây là chỗ rẻ nhất để giữ cửa sổ.
        env = boc_ket_qua(tool=call.tool, call_id=call.id, ket_qua=res,
                          args=call.args, blobs=self.history.blobs)
        if env.truncated:
            self.ledger.append("note", {"run_id": ctx.run_id, "cat_ket_qua": env.to_ledger()})
        self.messages.append({"role": "tool", "tool_call_id": call.id,
                              "tool": call.tool, "result": env.to_model(),
                              "envelope": env.to_ledger()})

    def _tool_error(self, call: Any, err: EideError, ctx: TurnContext,
                    *, as_incident: bool = True) -> None:
        if as_incident:
            self.ledger.append("tool_result", {"run_id": ctx.run_id, "tool": call.tool,
                                               "ok": False, "code": err.code})
        self.messages.append({"role": "tool", "tool_call_id": call.id,
                              "tool": call.tool, "result": err.to_tool_result()})

    # ------------------------------------------------------------------ điều hướng
    def _dieu_huong(self, act: HumanAct, ctx: TurnContext) -> None:
        """`attend` và `set`: ghi nhận bằng mã, KHÔNG gọi mô hình.

        Đây là chỗ dễ đốt tiền nhất của cả kiến trúc, và nó đã đốt thật: ở lần chạy app
        đầu tiên, mỗi cái bấm chuyển tab sinh ra một `attend`, lõi coi nó như một lượt
        bình thường và gọi mô hình — bảy cú bấm thành bảy lượt, mỗi lượt vài nghìn token,
        để trả lời một câu người dùng chưa từng hỏi.

        Chuyển tab là **sự chú ý**, không phải **yêu cầu**. Tác tử cần biết người đang
        nhìn gì (§D1 I4 — lõi chỉ thấy HumanAct kèm xuất xứ), nhưng biết không có nghĩa
        là phải nói gì đó về nó.
        """
        if act.kind == "attend":
            self.dang_nhin = act.origin.surface
            return

        key = str(act.data.get("key"))
        val = act.data.get("value")
        if key == "autonomy" and val in ("A0", "A1", "A2", "A3", "A4"):
            self.policy.autonomy = str(val)
            self.config.autonomy = str(val)
            ctx.emit(uic.notice(f"Mức tự chủ đổi sang {val}.", level="info"))
        elif key == "trust" and isinstance(val, str):
            self.policy.trusted.add(val)
            ctx.emit(uic.notice(f"Đã ghi nhớ: tin {val} cho lần sau.", level="info"))
        else:
            ctx.emit(uic.notice(f"Thiết lập “{key}” chưa được hiện thực ở bước này.",
                                level="warn"))
        ctx.said_anything = True

    # ------------------------------------------------------------------ người sửa (§E4)
    def _nguoi_sua(self, act: HumanAct, ctx: TurnContext) -> None:
        """Sáu bước của §E4, từ lúc người bấm Lưu tới lúc tác tử biết.

        Điểm cốt lõi, và là chỗ dễ làm sai nhất: **lưu của người luôn được** (§E4 bước 4:
        "code.human_save luôn tự duyệt — đây là hành động R0 của người"). Không có cổng
        nào chắn đường người sửa hiện vật của chính họ. Cái đi qua cổng là chiều ngược
        lại: tác tử ghi đè lên bản người vừa sửa (G-FILE).
        """
        t = act.target
        assert t is not None                       # đã kiểm ở HumanAct.validate()
        if t.type == "criteria":
            # §E2: "Sửa ngưỡng (→ G-QUAL nếu đã có kết quả)… Kết quả sim → STALE".
            # Người sửa tiêu chí của chính họ thì KHÔNG phải hỏi — cổng G-QUAL là để chặn
            # TÁC TỬ tự nới ngưỡng. Nhưng kết quả cũ phải thành lỗi thời ngay, vì nó được đo
            # bằng một thước đã khác.
            return self._nguoi_sua_tieu_chi(act, ctx)
        if t.type == "symbol":
            # SCH-14/15 — người xác nhận hoặc sửa kiểu chân một ký hiệu. Đi nhánh RIÊNG, không
            # qua `_sua_hien_vat`: kiểu chân nằm sâu trong `anh_xa[ref].chan[i].kieu`, mà đường
            # sửa hiện vật chung chỉ thay được trường ở cấp một. Nới nó ra để chạm tới đây là
            # nới một đường mà mọi tab khác đang dùng.
            return self._nguoi_xac_nhan_ky_hieu(act, ctx)
        la_tep = t.type in ("file", "code")
        pha_khoa = la_tep and t.id in self.locks

        try:
            cs = (self._sua_tep(act, ctx, pha_khoa) if la_tep
                  else self._sua_hien_vat(act, ctx))
        except _XungDot as e:
            return self._the_xung_dot(e, act, ctx)

        if cs is None:
            return

        # Bước 5(a) — EIDE.md §"Người vừa sửa": tác tử đọc mục này mỗi lượt.
        self.eide_md.note_human_edit(
            artefact=str(t), summary=cs.explain.get("summary", "sửa"), why=act.note)
        self.eide_md.save()

        pl = getattr(ctx, "phan_loai_sua", None)
        loi = [f"Đã ghi thay đổi của anh vào {t} ({cs.id})."]

        if cs.stale_marked:
            loi.append("Những thứ dựng trên nó giờ cần xem lại: "
                       + ", ".join(cs.stale_marked)
                       + ". Tôi chưa chạy lại gì cả — anh muốn tôi lập kế hoạch cập nhật không?")
        elif pl is not None and not pl.gay_stale:
            # CX08 — nói rõ VÌ SAO không có gì phải cập nhật, để im lặng không bị
            # hiểu thành bỏ sót.
            loi.append(f"Đây là {pl.mo_ta_vi}, không đụng tới nội dung kỹ thuật — "
                       "nên không có gì dựng trên nó phải làm lại.")

        from . import human_edit as he
        nhac = he.loi_nhac_fact_nguoi(getattr(ctx, "fact_nguoi_moi", []) or [])
        if nhac:
            loi.append(nhac)
        if pha_khoa:
            # §E4.1 dòng lock_broken: tác tử DỪNG sửa tệp đó, không tự lưu đè.
            self.locks.discard(t.id)
            ctx.emit(uic.surface_unlock("code", block=t.id))
            loi.append("Tôi đang sửa dở tệp này nên đã dừng lại và giữ bản của anh. "
                       "Phần sửa của tôi sẽ được gộp lên bản mới và trình diff để anh "
                       "duyệt, chứ không tự ghi đè.")
        ctx.emit(uic.console_post("\n\n".join(loi), role="agent"))
        ctx.emit(uic.history_update(changesets=[self.history.tom_tat(cs)],
                                    stale=[{"id": i} for i in cs.stale_marked]))
        ctx.said_anything = True

    def _nguoi_sua_tieu_chi(self, act: HumanAct, ctx: TurnContext) -> None:
        """Người sửa ngưỡng của một assert ngay trên bảng tiêu chí."""
        ma_assert = act.target.id
        ma_tc = (act.origin.block or "criteria:sim-01").split(":", 1)[-1]
        a = self.store.get(f"criteria:{ma_tc}")
        if a is None:
            ctx.emit(uic.notice(f"Không có tiêu chí {ma_tc} trong kho.", level="error"))
            ctx.said_anything = True
            return

        truong = dict(act.data.get("fields") or {})
        moi = str(truong.get("nguong", "")).strip()
        try:
            gt = float(moi.replace(",", "."))
        except ValueError:
            ctx.emit(uic.notice(f"“{moi}” không phải một con số — chưa đổi ngưỡng nào.",
                                level="warn"))
            ctx.said_anything = True
            return

        canon = dict(a["canonical"])
        ds = [dict(x) for x in (canon.get("assert") or [])]
        cu = None
        for x in ds:
            if str(x.get("ma")) == ma_assert:
                cu = x.get("nguong")
                x["nguong"] = gt
                # Ngưỡng do người sửa thì nguồn của nó là chính họ — ghi đè "§13.4 tài liệu"
                # bằng một câu nói thật, thay vì để một nguồn cũ đứng tên một con số mới.
                x["nguon_nguong"] = ("anh sửa trực tiếp trên bảng"
                                     + (f": {act.note}" if act.note else ""))
        if cu is None:
            ctx.emit(uic.notice(f"Tiêu chí {ma_tc} không có assert {ma_assert}.",
                                level="error"))
            ctx.said_anything = True
            return
        canon["assert"] = ds

        cs = self.history.ghi_kho(
            author="human", artefact_id=f"criteria:{ma_tc}", type="criteria", op="update",
            canonical=canon,
            explain={"summary": f"anh đổi ngưỡng {ma_assert}: {cu} → {gt}",
                     "why": act.note or "anh sửa trực tiếp trên bảng tiêu chí",
                     "sources": [{"kind": "human", "ref": act.id or "gui"}],
                     "diff_prev": f"{ma_assert}.nguong: {cu} → {gt}",
                     "next": "Chạy lại sim.run — kết quả cũ đo bằng thước đã khác.",
                     "confidence": "NGUOI"},
            run_id=ctx.run_id)

        # Kết quả cũ thành lỗi thời NGAY. Để nó xanh cạnh một tiêu chí đã đổi là mời người
        # đọc kết luận về mạch bằng một phép đo không còn hiệu lực.
        het_han = []
        for r in self.store.list("sim_result", limit=10):
            if (r.get("canonical") or {}).get("ma_tieu_chi") in (ma_tc, None, ""):
                self.store.mark_stale([r["id"]], f"tiêu chí {ma_assert} đổi {cu} → {gt}")
                het_han.append(r["id"])

        self.eide_md.note_human_edit(artefact=f"criteria:{ma_tc}",
                                     summary=f"đổi ngưỡng {ma_assert} thành {gt}",
                                     why=act.note)
        self.eide_md.save()
        ctx.emit(uic.console_post(
            f"Đã ghi: ngưỡng {ma_assert} đổi từ {cu} sang {gt} ({cs.id}). "
            + (f"Kết quả mô phỏng cũ ({', '.join(het_han)}) nay là LỖI THỜI — nó được đo "
               "bằng một thước đã khác, nên tôi không dùng nó để kết luận nữa. Chạy lại "
               "sim.run khi anh muốn."
               if het_han else "Chưa có kết quả mô phỏng nào để đánh dấu lỗi thời."),
            role="agent"))
        ctx.emit(uic.history_update(changesets=[self.history.tom_tat(cs)],
                                    stale=[{"id": i} for i in het_han]))
        ctx.said_anything = True

    def _nguoi_xac_nhan_ky_hieu(self, act: HumanAct, ctx: TurnContext) -> None:
        """Người bấm xác nhận / sửa kiểu chân trên tab Thiết kế (§9 widget edit).

        Dùng ĐÚNG công cụ mà tác tử dùng (`sch.symbol_confirm`), nên luật "phải có lời của
        người" và "kiểu chân sửa thành Fact tầng NGƯỜI" chỉ tồn tại ở một chỗ. Lời của người ở
        đây là ô "vì sao anh đổi?" ngay cạnh ô sửa — nên nó luôn có thật.
        """
        t = act.target
        ref = t.id
        truong = dict(act.data.get("fields") or {})
        # Hai dạng, vì có hai người gọi: giao diện gửi cả Ô ("7=power_in, 27=bidirectional" —
        # đúng thứ người đọc thấy trong bảng và sửa tại chỗ), còn một lời gọi trong mã gửi
        # từng chân (`chan.7`). Nhận cả hai ở một chỗ, chứ không để mỗi bên có một đường ghi.
        kieu = {k.split(".", 1)[1]: v for k, v in truong.items() if k.startswith("chan.")}
        kieu.update(_tach_kieu_chan(str(truong.get("chan") or "")))
        loi = (act.note or "").strip() or str(truong.get("xac_nhan") or "").strip()
        if not loi:
            ctx.emit(uic.notice(
                f"Chưa ghi xác nhận cho {ref}: cần một câu của anh về ký hiệu này (ô “vì sao” "
                "ngay cạnh ô sửa). Một xác nhận không có lời của người là một xác nhận của "
                "máy đội tên người.", level="warn", code="E8009"))
            ctx.said_anything = True
            return

        cong_cu = self.registry.get("sch.symbol_confirm") if self.registry else None
        if cong_cu is None:
            ctx.emit(uic.notice(
                "Tính năng sơ đồ đang tắt, nên không ghi được xác nhận ký hiệu. Bật "
                "features.schematic trong Thiết lập rồi thử lại.", level="warn"))
            ctx.said_anything = True
            return

        kq = self.registry.run("sch.symbol_confirm", {
            "ref": ref, "trich_loi": loi, "kieu_chan": kieu,
            "explain": {"summary": f"anh xác nhận ký hiệu {ref}",
                        "why": loi, "sources": [{"kind": "human", "ref": act.id or "gui"}],
                        "diff_prev": ("sửa kiểu chân " + ", ".join(sorted(kieu))
                                      if kieu else "xác nhận, không sửa gì"),
                        "next": "Sinh lại ký hiệu và ghi tệp để KiCad thấy kiểu chân này.",
                        "confidence": "NGUOI"}}, ctx)
        if not kq.ok:
            ctx.emit(uic.notice(getattr(kq.error, "message_vi", "Không ghi được xác nhận."),
                                level="error",
                                code=getattr(kq.error, "code", None)))
            ctx.said_anything = True
            return
        ctx.emit(uic.console_post(f"{kq.data['note_vi']}", role="agent"))
        ctx.said_anything = True

    def _sua_tep(self, act: HumanAct, ctx: TurnContext, pha_khoa: bool):
        from .errors import path_not_found
        path = act.target.id
        p = (self.config.paths.project_root / path).resolve()
        if not p.exists():
            raise path_not_found(path)

        cu = p.read_text("utf-8", errors="replace")
        moi = act.data.get("content")
        if moi is None:
            ctx.emit(uic.notice("Thiếu nội dung mới trong thao tác sửa.", level="error"))
            return None

        base_ver = str(act.data.get("base_version", ""))
        if _bam(cu) != base_ver and base_ver:
            # Bước 3 — base_version khác bản hiện tại: tác tử đã sửa trong lúc người gõ.
            goc = self._tim_ban_goc(path, base_ver)
            if goc is None:
                raise _XungDot(path, cua_nguoi=moi, cua_tac_tu=cu, goc=None,
                               vi_sao="không tìm lại được bản gốc mà anh đã mở")
            kq = self.history.vcs.merge_ba_chieu(base=goc, cua_nguoi=moi, cua_tac_tu=cu)
            if not kq.sach:
                raise _XungDot(path, cua_nguoi=moi, cua_tac_tu=cu, goc=goc,
                               vi_sao=f"{kq.doan_xung_dot} đoạn đụng nhau")
            moi = kq.noi_dung

        p.write_text(moi, "utf-8")
        return self.history.ghi_tep(
            author="human", paths=[path],
            summary=act.data.get("summary") or f"anh sửa {path}",
            explain=self._explain_cua_nguoi(act, f"anh sửa {path}"),
            noi_dung_truoc={path: cu}, human_act_id=act.id, note=act.note,
            run_id=ctx.run_id)

    def _sua_hien_vat(self, act: HumanAct, ctx: TurnContext):
        from . import human_edit as he

        aid = act.target.id
        cu = self.store.get(aid)
        if cu is None:
            ctx.emit(uic.notice(
                f"Không có hiện vật {aid} trong kho, nên không sửa được. "
                "Mở tab tương ứng để xem kho đang có gì.", level="error"))
            return None

        base = str(act.data.get("base_version", "")).lstrip("v")
        if base and base.isdigit() and int(base) != cu["version"]:
            # Cùng hiện vật, hai người sửa. Trộn theo TRƯỜNG: khác trường thì gộp được,
            # cùng trường khác giá trị thì để người chọn (§E4 bước 3).
            fields = act.data.get("fields") or {}
            dung = [k for k, v in fields.items() if cu["canonical"].get(k) != v]
            if dung:
                raise _XungDot(
                    aid,
                    cua_nguoi="; ".join(f"{k} = {fields[k]}" for k in dung),
                    cua_tac_tu="; ".join(f"{k} = {cu['canonical'].get(k)}" for k in dung),
                    goc=None,
                    vi_sao=f"anh mở bản v{base}, nhưng kho đã ở v{cu['version']} — "
                           f"trường {', '.join(dung)} đã đổi từ lúc đó")

        truoc = dict(cu["canonical"])
        can = dict(truoc)
        can.update(act.data.get("fields") or {})

        # §E4.1 — không phải sửa nào cũng như nhau. Đổi tên một khối không được làm
        # cả chuỗi hạ nguồn sáng đèn cảnh báo (CX08).
        pl = he.phan_loai(truoc=truoc, sau=can,
                          lock_broken=bool(act.data.get("lock_broken")),
                          bac_bo=bool(act.data.get("bac_bo")))
        ctx.phan_loai_sua = pl

        cs = self.history.ghi_kho(
            author="human", artefact_id=aid, type=cu["type"], op="update",
            canonical=can, explain=self._explain_cua_nguoi(act, f"anh sửa {aid}"),
            human_act_id=act.id, note=act.note, run_id=ctx.run_id,
            gay_stale=pl.gay_stale)

        # §E4 bước 3 / CX05 — số mới người vừa nhập mà chưa truy vết được thì thành
        # Fact tầng NGƯỜI, chứ không biến mất vào một ô trong bảng.
        from .hooks.standard import _van_ban_co_nguon
        nguon = _van_ban_co_nguon(ctx, {})
        ctx.fact_nguoi_moi = [
            he.tao_fact_nguoi(self.store, hien_vat=aid, so=s,
                              trich_loi=act.note or act.data.get("summary") or
                                        f"anh sửa {aid}: {s.nguyen_van}",
                              human_act_id=act.id)
            for s in he.so_moi_khong_nguon(truoc=truoc, sau=can, nguon_da_co=nguon)
        ]
        return cs

    def _explain_cua_nguoi(self, act: HumanAct, mac_dinh: str) -> dict[str, Any]:
        """Changeset của người cũng có lớp giải thích (§E5.1) — dựng từ lời họ."""
        return {
            "summary": act.data.get("summary") or mac_dinh,
            "why": act.note or "Anh không ghi lý do.",
            "sources": [{"kind": "human_act", "ref": act.id, "tier": "NGUOI"}],
            "diff_prev": act.data.get("summary") or "xem diff của changeset",
            "next": "Tác tử xem lại hạ nguồn và đề nghị cập nhật.",
            "confidence": "NGUOI",
        }

    def _tim_ban_goc(self, path: str, bam: str) -> str | None:
        """Tìm lại nội dung tệp mà người đã mở, theo hash nội dung."""
        b = self.history.blobs.get(bam)
        if b is not None:
            return b.decode("utf-8", "replace")
        if not self.history.git_san:
            return None
        for r in self.history.vcs.lich_su_tep(path, n=40):
            noi_dung = self.history.vcs.noi_dung_tai(r["sha"], path)
            if noi_dung is not None and _bam(noi_dung) == bam:
                return noi_dung
        return None

    def _the_xung_dot(self, e: "_XungDot", act: HumanAct, ctx: TurnContext) -> None:
        """§E4 bước 3 — "xung đột → thẻ clarify với hai bản cạnh nhau, người chọn"."""
        card_id = self.ids.next("card")
        card = {
            "type": "clarify", "card_id": card_id,
            "intro": f"Bản của anh và bản hiện tại của {e.hien_vat} đụng nhau "
                     f"({e.vi_sao}). Tôi không tự chọn hộ.",
            "questions": [{
                "key": "chon",
                "question": f"Giữ bản nào cho {e.hien_vat}?",
                "why": "Tôi không ghi đè sửa của anh, và cũng không vứt phần tôi vừa làm "
                       "mà không hỏi.",
                "choices": ["Giữ bản của tôi (anh)", "Giữ bản của tác tử",
                            "Để tôi xem diff rồi quyết"],
                "required": True}],
            "hai_ban": {"cua_nguoi": e.cua_nguoi[:4000], "cua_tac_tu": e.cua_tac_tu[:4000]},
        }
        ctx.emit(uic.console_post(
            f"Bản của anh và bản hiện tại của **{e.hien_vat}** đụng nhau: "
            f"{e.vi_sao}. Anh chọn giữ bản nào?", role="agent", card=card))
        self.pending_cards.append(card)
        ctx.awaiting_human = True
        ctx.said_anything = True
        self.ledger.append("incident", {"run_id": ctx.run_id, "code": "E_VERSION_CONFLICT",
                                        "artefact": e.hien_vat, "why": e.vi_sao})

    # ------------------------------------------------------------------ người hoàn tác
    def _nguoi_hoan_tac(self, act: HumanAct, ctx: TurnContext) -> None:
        """§E5.2 — "hoàn tác của người luôn được (R0)". Không cổng nào chắn."""
        t = act.target
        if t is None:
            ctx.emit(uic.notice("Hoàn tác cái gì? Thiếu target.", level="error"))
            return
        kq = (self.history.hoan_tac_luot(t.id, by="human") if t.type == "run"
              else self.history.hoan_tac_changeset(t.id, by="human"))

        ctx.emit(uic.console_post(f"{kq.message_vi}", role="agent"))
        for c in kq.canh_bao:
            ctx.emit(uic.notice(c, level="warn"))
        ctx.said_anything = True
        if kq.ok:
            ctx.emit(uic.history_update(
                changesets=self.history.danh_sach(limit=30),
                stale=[{"id": i} for i in kq.stale_moi]))
            self.messages.append({"role": "user", "text":
                f"<system-reminder>\nNgười dùng vừa hoàn tác: {kq.message_vi}\n"
                + ("Phần KHÔNG hoàn tác được: "
                   + "; ".join(f"{g['id']} ({g['ly_do']})" for g in kq.giu_nguyen)
                   + "\n" if kq.giu_nguyen else "")
                + "Đừng làm lại thứ vừa bị hoàn tác trừ khi họ bảo.\n</system-reminder>"})

    # ------------------------------------------------------------- bản ưng ý / nhánh
    def _nguoi_ghi_ban(self, act: HumanAct, ctx: TurnContext) -> None:
        """§E6.2 — người đặt tên thì MÃ ghi, không đi vòng qua mô hình.

        Đây là một trong số ít thao tác mà mô hình không có việc gì để làm: tên đã có,
        nội dung do kho quyết định. Cho mô hình đi qua đây chỉ thêm một chỗ để tên bị
        viết lại thành thứ khác.
        """
        ten = str(act.data.get("name") or act.text or "").strip()
        if not ten:
            ctx.emit(uic.notice("Bản ưng ý cần một cái tên.", level="error"))
            ctx.said_anything = True
            return
        try:
            s = self.history.tao_snapshot(
                ten=ten, ghi_chu=str(act.data.get("note") or act.note or ""), boi="human")
        except ValueError as e:
            ctx.emit(uic.console_post(f"{e}", role="agent"))
            ctx.said_anything = True
            return
        ctx.emit(uic.console_post(
            f"Đã ghi bản ưng ý **{s.name}** (`{s.id}`) — {s.tom_tat()}.\n\n"
            "Quay về bản này bất cứ lúc nào; nội dung của nó không đổi nữa.",
            role="agent"))
        ctx.said_anything = True
        self.paint(ctx.emit, only=["history"])
        self.messages.append({"role": "user", "text":
                              f"<system-reminder>\nNgười dùng vừa ghi bản ưng ý "
                              f"“{s.name}” ({s.id}).\n</system-reminder>"})

    def _nguoi_re_nhanh(self, act: HumanAct, ctx: TurnContext) -> None:
        viec = str(act.data.get("action") or "create")
        ten = str(act.data.get("name") or act.text or "").strip()
        if viec in ("create", "tao"):
            kq = self.history.tao_nhanh(ten)
        elif viec in ("switch", "chuyen"):
            kq = self.history.chuyen_nhanh(ten)
        else:
            kq = {"ok": True, "message_vi": "Các nhánh: "
                  + ", ".join(self.history.danh_sach_nhanh())}
        ctx.emit(uic.console_post(f"{kq['message_vi']}", role="agent"))
        ctx.said_anything = True
        if kq.get("ok"):
            self.paint(ctx.emit, only=["history"])

    # ------------------------------------------------------------------ cổng
    def _da_duyet_roi(self, tool: str, perm: Any) -> bool:
        """Công cụ này đã được duyệt trong lượt việc hiện tại chưa.

        "Lượt việc" tính từ câu người dùng gõ cho tới khi tác tử dừng — `self._cong_cu_da_duyet`
        được xoá ở đầu mỗi `console_act`. Nhớ qua lượt sẽ thành "duyệt một lần, dùng mãi mãi",
        đúng thứ thẻ cổng tồn tại để ngăn.
        """
        if perm.irreversible or perm.never_auto:
            return False
        return (tool, perm.gate or "") in self._cong_cu_da_duyet

    def _nho_da_duyet(self, tool: str, card: dict[str, Any]) -> None:
        if card.get("irreversible") or card.get("never_auto"):
            return
        self._cong_cu_da_duyet.add((tool, card.get("gate") or ""))

    def _resolve_gate(self, act: HumanAct, ctx: TurnContext) -> None:
        gid = act.data["gate_id"]
        pend = self.pending_gates.pop(gid, None)
        if pend is None:
            ctx.emit(uic.notice(f"Thẻ {gid} không còn chờ nữa (đã trả lời hoặc hết hạn).",
                                level="warn", code="E_GATE_STALE"))
            ctx.said_anything = True
            return
        approved = bool(act.data.get("approved"))
        self.pending_cards[:] = [c for c in self.pending_cards if c.get("card_id") != gid]
        ctx.emit(uic.card_resolve(gid, by="human", choice=act.data.get("choice")))
        self.ledger.append("gate", {"run_id": ctx.run_id, "gate_id": gid,
                                    "state": "approved" if approved else "rejected",
                                    "act_id": act.id, "note": act.note})

        if not approved:
            ctx.emit(uic.console_post("Đã huỷ, tôi không làm thao tác đó.", role="agent"))
            ctx.said_anything = True
            self.messages.append({"role": "user",
                                  "text": f"<system-reminder>Người dùng TỪ CHỐI cổng {gid}"
                                          f"{' — lý do: ' + act.note if act.note else ''}. "
                                          "Đừng tìm đường khác để làm việc đó. Hỏi họ muốn "
                                          "làm gì tiếp.</system-reminder>"})
            return

        call = pend.get("call")
        if call is not None:
            self._nho_da_duyet(str(call.get("tool") or ""), pend["card"])
        if call is None:
            # Cổng do S0 phát (chưa có lời gọi công cụ nào) — để mô hình tiếp tục.
            self.messages.append({"role": "user",
                                  "text": f"<system-reminder>Người dùng ĐÃ DUYỆT cổng {gid} "
                                          f"({pend['card'].get('title')}). Tiến hành."
                                          "</system-reminder>"})
            return self._tool_loop(ctx, None)

        # Nói ra rằng cổng đã được duyệt, TRƯỚC khi kết quả công cụ xuất hiện.
        #
        # Thiếu dòng này thì mô hình thấy đúng hai thứ mâu thuẫn, liền nhau: lời từ chối
        # E4003 — *"DỪNG LẠI, đừng gọi lại tool này, kết thúc lượt và chờ quyết định"* — rồi
        # ngay sau là một kết quả CỦA CHÍNH công cụ ấy, không ai giải thích vì sao.
        #
        # Ngày 02/10/2026 chuyện ấy xảy ra hai lượt liền trong phiên FPGA. Tác tử dung hoà hai
        # thứ ấy bằng cách kết luận **lời giao việc đã bị cắt mất**, rồi xin người dùng gửi
        # lại đề bài. Lời giao việc không hề bị cắt — tôi đã kiểm trong sổ, còn nguyên 770 ký
        # tự cả đầu lẫn đuôi. Tức là một lời kể sai sinh ra từ một khoảng trống trong ngữ
        # cảnh, và nó tốn hai lượt cùng một mục việc-chờ-làm ghi sai nguyên nhân.
        #
        # Nhánh TỪ CHỐI và nhánh cổng do S0 phát đều đã có lời nhắc. Chỉ nhánh thường gặp
        # nhất là không.
        self.messages.append({"role": "user", "_he_thong": True, "text": (
            f"<system-reminder>\nNgười dùng ĐÃ DUYỆT cổng {gid} "
            f"({pend['card'].get('title')}). Lời gọi `{call['tool']}` bị chặn trước đó nay "
            "đã được chạy thay bạn — kết quả của nó là tin nhắn ngay sau đây.\n\n"
            "Lời từ chối `E4003` trước đó đã hết hiệu lực. **Tiếp tục đúng việc đang làm**: "
            "đề bài vẫn là lời người dùng giao ở đầu lượt, nó không bị mất và không cần hỏi "
            "lại.\n</system-reminder>")})

        spec = self.registry.get(call["tool"])
        res = self.registry.run(call["tool"], call["args"], ctx)
        self.hooks.post_tool_use(call, res, ctx)
        # Cổng G-SCOPE vừa được duyệt cho `plan.exit`: đóng dấu kế hoạch là ĐÃ DUYỆT.
        #
        # Phải làm ở đây chứ không trong chính công cụ, vì `plan.exit` chạy lại y hệt lần
        # trước — nó không có cách nào biết lần này nó chạy SAU một cái gật đầu. Thiếu dấu
        # này thì kế hoạch kẹt mãi ở `cho_duyet`, công cụ ghi khoá mãi, và người dùng bấm
        # Duyệt xong lại thấy tác tử nói nó vẫn đang chờ duyệt.
        if approved and call["tool"] == "plan.exit" and res.ok:
            self._duyet_ke_hoach(ctx, gid)
        self.messages.append({"role": "tool", "tool_call_id": call.get("id", gid),
                              "tool": call["tool"], "result": res.to_model()})
        self._tool_loop(ctx, None)

    def _duyet_ke_hoach(self, ctx: TurnContext, gid: str) -> None:
        """Đóng dấu `da_duyet` lên kế hoạch và mở lại công cụ ghi."""
        from .ke_hoach import MA_KE_HOACH

        kh = self._ke_hoach()
        if kh is None:
            return
        kh.trang_thai = "da_duyet"
        self.store.apply(
            artefact_id=MA_KE_HOACH, type="plan", op="update",
            author=f"human:{gid}", canonical=kh.to_dict(),
            explain={"summary": f"người dùng duyệt kế hoạch {len(kh.buoc)} bước",
                     "why": "cổng G-SCOPE được duyệt", "sources": [gid],
                     "diff_prev": "cho_duyet → da_duyet", "next": "chạy theo kế hoạch",
                     "confidence": "NGUOI"},
            view_hint={"kind": "plan", "path": "kế hoạch"})
        self.messages.append({"role": "user", "_he_thong": True, "text": (
            "<system-reminder>\nKế hoạch đã được duyệt. Công cụ ghi mở lại.\n\n"
            "Từ giờ mỗi lượt bạn sẽ thấy kế hoạch này trong `<pending>`. Làm theo thứ tự, và "
            "gọi `plan.step_done` kèm HIỆN VẬT mỗi khi xong một bước — không phải để báo "
            "cáo, mà để lượt sau bạn (và người dùng) biết đang ở đâu mà không phải đọc lại "
            "sổ cái.\n\nThấy kế hoạch sai khi bắt tay vào làm thì NÓI RA ngay, đừng im lặng "
            "đi chệch: `plan.cancel` rồi soạn lại rẻ hơn nhiều so với làm xong một việc sai."
            "\n</system-reminder>")})

    # ------------------------------------------------------------------ ngữ cảnh
    def _assemble(self, ctx: TurnContext, s0: Any):
        # Mở khoá công cụ theo ngữ cảnh TRƯỚC khi dựng danh sách công cụ cho mô hình.
        self._mo_khoa_theo_ngu_canh()
        inv = ctx.build_inventory()
        recent = [m.get("text", "") for m in self.messages[-6:] if m.get("role") == "user"]
        from .skills import goi_y_cho_ngu_canh

        return assemble(
            eide_md=self.eide_md, inventory_text=inv.render(), store=self.store,
            recent_texts=recent or [""],
            # §B5 "skill nạp theo ngữ cảnh": gợi ý theo từ khoá của câu vừa gõ, nội dung đầy
            # đủ để mô hình tự nạp bằng `skill.load` khi nó thấy cần.
            skills=goi_y_cho_ngu_canh(),
            human_edit_changesets=ctx.human_edits,
            pending_cards=self.pending_cards,
            stopped_run=inv.unfinished_run,
            assumptions=self.assumptions,
            plan=self._plan_cho_ngu_canh(),
            s0_annotations=([self.bo_nho_nguoi.khoi_ngu_canh()]
                            if self.bo_nho_nguoi.khoi_ngu_canh() else [])
                           + (getattr(s0, "annotations", None) or []),
            budget=self.config.context_budget)

    def _user_block(self, act: HumanAct, ctx: TurnContext, annotations: list[str]) -> str:
        asm = self._assemble(ctx, type("S", (), {"annotations": annotations})())
        body = act.text or act.transcript_line()
        return (asm.reminder + "\n\n" + body) if asm.reminder else body

    def _context_pressure(self, asm: Any) -> float:
        used = asm.total_tokens + sum(len(str(m)) // 3 for m in self.messages)
        return used / max(1, self.config.model.context_window)

    def _compact(self, ctx: TurnContext, muc: str = "C1") -> None:
        """Bậc thang nén §6. C1 luôn chạy trước; C2 chỉ khi C1 không đủ.

        Thứ tự này không phải để tiết kiệm mà để **giảm rủi ro**: C1 là mã thuần, không
        có phép đoán nào nằm giữa đường. C2 đưa mô hình vào giữa transcript và sự thật,
        nên chỉ tới đó khi cần, và khi tới thì phải kiểm ngược (§6.6).
        """
        bc = mem.c1(self.messages,
                    ghim=mem.chi_so_ghim(self.messages),
                    tep_da_sua=set(self.locks))
        self.ledger.append("note", {"run_id": ctx.run_id, "compact": "C1", **bc})
        self.da_nen_lan_nao = True
        # §12 "nén là giao dịch": ghi tệp mới rồi đổi tên. Không có khoảnh khắc nào
        # transcript ở trạng thái "đã cắt nhưng chưa có bản thay thế".
        self.transcript.thay_toan_bo(list(self.messages))
        if bc["giam_phan_tram"] >= 5:
            ctx.emit(uic.notice(
                f"[Hệ thống] Đã thu gọn ngữ cảnh {bc['giam_phan_tram']:.0f} % "
                f"({bc['stub_qua_han']} kết quả cũ, {bc['dedup']} lần đọc trùng). "
                "Không mất gì — đọc lại được bằng blob.read.",
                level="info", code="C1"))
        if muc in ("C0", "C1"):
            return

        if muc == "C4":
            # §6.5 — mức 95 %: bỏ mọi kết quả công cụ thô, KHÔNG gọi mô hình. Ở mức này
            # mỗi lời gọi thêm vào là một rủi ro hỏng giữa chừng.
            bc4 = mem.c4(self.messages, ghim=mem.chi_so_ghim(self.messages))
            self.ledger.append("compact", {"run_id": ctx.run_id, "buoc": "c4", **bc4})
            self.transcript.thay_toan_bo(list(self.messages))
            self.nhat_ky_nen.append({"muc": "C4", "ok": True, **bc4,
                                     "kiem": "không kiểm (khẩn cấp)"})
            ctx.emit(uic.notice(
                f"[Hệ thống] Ngữ cảnh gần đầy — đã bỏ {bc4['stub']} kết quả công cụ khỏi "
                f"ngữ cảnh (giảm {bc4['giam_phan_tram']:.0f} %). Không mất gì: đọc lại "
                "bằng blob.read. Nên mở một lượt mới cho việc tiếp theo.",
                level="warn", code="C4"))
            ctx.said_anything = True
            return

        # --- C2/C3: tóm tắt có cấu trúc, có kiểm ngược.
        k = mem.K_LUOT if muc == "C2" else 6      # §6.4 — C3 hạ K xuống 6
        inv = ctx.build_inventory().render()
        kq = self.bo_nen.nen(self.messages, run_id=ctx.run_id, inventory_text=inv,
                             k_luot=k)
        kq.muc = muc
        self.nhat_ky_nen.append({"ts": kq.tom_tat.created_at if kq.tom_tat else "",
                                 **kq.to_dict()})
        ctx.emit(uic.notice(kq.dong_he_thong(),
                            level="info" if kq.ok else "warn", code=muc))
        ctx.said_anything = True

    # ------------------------------------------------------------------ báo cáo
    def _note_stated_assumptions(self, ctx: TurnContext, text: str) -> None:
        low = text.lower()
        for a in self.assumptions:
            if a not in ctx.assumptions_stated and a.lower()[:30] in low:
                ctx.assumptions_stated.append(a)

    def _ghi_nhan_da_nhac(self, ctx: TurnContext) -> None:
        """N9 / CX07 — đánh dấu changeset của người là "tác tử đã nhắc tới".

        Nhận biết bằng cách tìm mã changeset hoặc mã hiện vật trong lời tác tử đã nói
        trong lượt. Máy móc, nhưng đó là ưu điểm: nó không tin vào việc mô hình *nghĩ*
        rằng nó đã nhắc — nó kiểm chữ thật sự đã hiện ra cho người đọc.
        """
        if not ctx.human_edits or not ctx.loi_da_noi:
            return
        loi = "\n".join(ctx.loi_da_noi).lower()
        for cs in ctx.human_edits:
            moc = [cs["id"].lower()] + [t["artefact_id"].lower() for t in cs.get("touches", [])]
            if any(m in loi for m in moc):
                self.history.log.mark(cs["id"], acknowledged_by_agent=ctx.run_id)

    def _tha_khoa(self, ctx: TurnContext) -> None:
        for path in list(self.locks):
            ctx.emit(uic.surface_unlock("code", block=path))
        self.locks.clear()

    def _usage_add(self, u: Any, ctx: TurnContext) -> None:
        """Cộng dồn chi phí — của LƯỢT và của PHIÊN, tách bạch.

        Bản đầu chỉ có một biến tích luỹ, nên báo cáo lượt in ra tổng cả phiên: một
        lượt gọi bốn lần mô hình bị báo là tốn 487 nghìn token (DEV-232). Người đọc
        con số đó không cách nào biết lượt vừa rồi thật sự đắt hay rẻ.
        """
        ctx.usage_luot = u if ctx.usage_luot is None else ctx.usage_luot.add(u)
        self.usage_phien = u if self.usage_phien is None else self.usage_phien.add(u)

    def _nhip(self, ctx: TurnContext) -> None:
        """Báo số đo của lượt ĐANG CHẠY: công cụ đã gọi, giây đã trôi, token đã tiêu.

        Trước đây cả một lượt chỉ có hai mốc tin: `run.update` lúc bắt đầu (chi phí rỗng) và
        `run.update` lúc kết thúc. Giữa hai mốc ấy — chỗ tác tử gọi mười công cụ và tiêu vài
        chục nghìn token — thanh trạng thái đứng nguyên ở `0/40 tool · 0/300 s`.

        Người nhìn vào đó không phân biệt được *đang chạy* với *đã treo*. Mà đây đúng là lúc
        họ cần biết nhất: một lượt dài là lúc duy nhất người ta muốn bấm Dừng.

        Dùng `run.update` chứ không vẽ lại cả thanh trạng thái: dựng thanh trạng thái phải
        `inventory.build()` — quét kho, quét sổ cái — và làm thế sau mỗi lời gọi công cụ là
        trả một cái giá lớn cho một con số nhỏ.
        """
        if ctx.run_id:
            ctx.emit(uic.run_update(ctx.run_id, status="running",
                                    cost=self._chi_phi(ctx)))

    def _chi_phi(self, ctx: TurnContext) -> dict[str, Any]:
        """Chi phí tới thời điểm này — một nguồn sự thật cho cả nhịp giữa lượt lẫn báo cáo."""
        return {"tokens": ctx.usage_luot.to_dict() if ctx.usage_luot else {},
                "tools": ctx.tool_calls_used,
                "seconds": round(ctx.elapsed, 2),
                "phien": self.usage_phien.to_dict() if self.usage_phien else {}}

    def _report(self, ctx: TurnContext) -> dict[str, Any]:
        """Báo cáo lượt, 5 dòng — §E2 dòng "Báo cáo lượt"."""
        return {
            "run_id": ctx.run_id,
            "tool_calls": ctx.tool_calls_used,
            "seconds": round(ctx.elapsed, 2),
            "awaiting_human": ctx.awaiting_human,
            "assumptions": list(self.assumptions),
            "cost": self._chi_phi(ctx),
        }


class _XungDot(Exception):
    """Hai bản đụng nhau. Không giải bằng mã được — phải để người chọn (§E4 bước 3)."""

    def __init__(self, hien_vat: str, *, cua_nguoi: str, cua_tac_tu: str,
                 goc: str | None, vi_sao: str):
        super().__init__(vi_sao)
        self.hien_vat = hien_vat
        self.cua_nguoi = cua_nguoi
        self.cua_tac_tu = cua_tac_tu
        self.goc = goc
        self.vi_sao = vi_sao


def _bam(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _hau_qua(call: dict[str, Any], ctx: Any, perm: Any, spec: Any) -> list[str]:
    """Hậu quả cụ thể của một lời gọi, bằng tiếng người — §E7 quy tắc 1.

    Chỗ này từng trả về danh sách rỗng cho **mọi** cổng. Hậu quả là thẻ cổng chỉ còn
    hai cái nút và một câu tóm tắt: người bấm mà không biết mình đổi cái gì lấy cái gì,
    tức là cái cổng chỉ còn tác dụng làm chậm, không còn tác dụng bảo vệ (DEV-248).
    Nguyên tắc ở đây: chỉ nói thứ **tính được từ trạng thái thật**, không nói chung chung.
    """
    tool = call.get("tool", "")
    args = call.get("args") or {}
    ra: list[str] = []
    try:
        if tool == "snapshot.restore" and ctx.history is not None:
            bc = ctx.history.se_mat_gi_khi_khoi_phuc(str(args.get("snapshot", "")))
            if bc.get("ok"):
                ra += bc.get("se_mat_vi", [])
                if bc.get("co_sua_cua_nguoi"):
                    ra.append(f"Trong đó có {len(bc['cua_nguoi'])} thay đổi do CHÍNH ANH "
                              "sửa — chúng sẽ bị thay bằng bản cũ.")
                for g in bc.get("khong_hoan_tac_duoc", []):
                    ra.append(f"{g['id']} không lùi lại được: {g['ly_do']}")
                if not args.get("giu_ban_hien_tai"):
                    ra.append("Bản hiện tại chưa được ghi thành bản ưng ý nào — "
                              "đặt tên cho nó trước thì sau này còn quay lại được.")
            else:
                ra.append(bc.get("message_vi", ""))
        elif tool == "history.undo" and ctx.history is not None:
            muc = str(args.get("scope", "run"))
            ma = str(args.get("id", "")) or "lượt gần nhất"
            ra.append(f"Hoàn tác {muc} {ma} — các hiện vật nó đã ghi quay về bản trước đó.")
        elif tool.startswith("target."):
            viec = args.get("what") or args.get("op") or tool.split(".", 1)[1]
            ra.append(f"Tác động lên phần cứng thật: {viec}.")
            if tool == "target.dangerous":
                ra.append("Sau thao tác này chip không trở lại trạng thái cũ được.")
        elif tool in ("fs.write", "fs.edit"):
            ra.append(f"Ghi đè {args.get('path', 'tệp')} — bản hiện tại của tệp bị thay.")
        elif tool == "tool.install":
            ra.append(f"Cài {args.get('pkg', 'gói')} vào máy anh, ngoài thư mục dự án.")
    except Exception as e:                       # thẻ cổng không được chết vì phần phụ
        ra.append(f"(không dựng được danh sách hậu quả: {e})")

    if not ra and perm.summary_vi:
        ra.append(perm.summary_vi)
    # "Nếu việc này hỏng thì lùi về đâu" là câu người cần TRƯỚC khi bấm. Điều kiện bám
    # vào bản chất việc (đụng phần cứng, hoặc R2/R3, hoặc không đảo ngược) chứ không
    # bám vào `spec`: cổng vẫn nổ cho cả công cụ chưa đăng ký, và khi đó `spec` là None.
    nang = (tool.startswith("target.") or perm.irreversible
            or getattr(spec, "risk", "") in ("R2", "R3"))
    if nang and ctx.history is not None:
        try:
            gan = ctx.history.snapshots.gan_nhat()
            ra.append(f"Bản ưng ý gần nhất để quay về: “{gan.name}”." if gan
                      else "Chưa có bản ưng ý nào để quay về nếu việc này hỏng.")
        except Exception:
            pass
    return [c for c in ra if c]


def _render_gate(card: dict[str, Any]) -> str:
    """Thẻ cổng dạng chữ, cho transcript và cho lõi chạy headless.

    §E7: "Thẻ cổng ... đúng 1 mục; không default" — nên ở đây không có lựa chọn nào
    được đánh dấu sẵn, và hậu quả luôn đứng trước lựa chọn.
    """
    L = [f"**[{card.get('gate', 'CỔNG')}] {card.get('title', '')}**"]
    for c in card.get("consequences_vi", []):
        L.append(f"- {c}")
    if card.get("irreversible"):
        L.append("- **Thao tác này KHÔNG hoàn tác được.**")
    if card.get("require_vi"):
        L.append("")
        L.append(card["require_vi"])
    if card.get("require_fields"):
        L.append(f"_Phải nêu: {', '.join(card['require_fields'])}._")
    L.append("")
    L.append("→ " + "  ·  ".join(card.get("options", ["Duyệt", "Từ chối"])))
    return "\n".join(L)
