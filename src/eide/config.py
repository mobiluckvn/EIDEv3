# -*- coding: utf-8 -*-
"""Cau hinh lõi: duong dan, ngan sach, muc tu chu, mo hinh.

Moi con so o day deu co nguon trong EIDE-MDD-40 — ghi chu §... ben canh. Khong tu
dat mot nguong nao ma tai lieu khong noi; can mot nguong moi thi ghi DEV-2xx.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> int:
    """Nap `.env` vao os.environ. Khong de len bien da co san trong moi truong.

    Viet tay thay vi them phu thuoc: doc mot tep KEY=VALUE la viec cua mot vong for,
    va moi phu thuoc them vao lõi la mot thu nua phai giai trinh khi bao ve de an.
    """
    p = Path(path)
    if not p.exists():
        return 0
    n = 0
    for line in p.read_text("utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and v and k not in os.environ:
            os.environ[k] = v
            n += 1
    return n

# --------------------------------------------------------------------------- mo hinh
# Quyet dinh cua chu san pham 25/09/2026: chi dung gemini-3.8-flash.
# Danh sach nay la mot RANG BUOC, khong phai goi y. Moi lop goi mo hinh deu di qua
# `ModelConfig.assert_allowed`, ke ca khi ai do truyen ten model thang vao `llm.stream`.
ALLOWED_MODELS = frozenset({"gemini-3.8-flash"})


# --------------------------------------------------------------------------- muc tu chu
# MDD-40 §B4: "muc tu chu mac dinh A3". B6: bo nho nguoi dung giu muc tu chu.
#   A0 hoi moi thu · A1 doc tu do, ghi phai hoi · A2 ghi trong du an tu do
#   A3 (mac dinh) ghi tu do, chi cac cong rui ro moi hoi · A4 tu chu cao, chi G-OPS/G-SAFE
AUTONOMY_LEVELS = ("A0", "A1", "A2", "A3", "A4")


@dataclass(slots=True)
class Budget:
    """Ngan sach mot luot — MDD-40 §B1 va §F3."""

    max_tool_calls: int = 40          # §B1 "ngan sach 40 tool/luot"
    max_seconds: float = 300.0        # §B1 "300 s"; UC19 "qua han luot (300s) tha nguoi dung ra"
    compact_at: float = 0.70          # §B1 "if ctx.tokens > 0.7 * window"
    max_ask_rounds: int = 2           # N4 "hoi mot cum, toi da 2 lan/luot"

    def __post_init__(self) -> None:
        """Noi han muc bang bien moi truong. Mac dinh van la so cua MDD-40 §B1.

        Vi sao can noi — do duoc ngay 01/10/2026, viec FPGA:

        Han 300 s/luot duoc chon cho viec vi dieu khien, noi moi buoc dai vai giay. Viec FPGA co
        nhung buoc **dai hon han mot luot ngay tu ban chat cong viec**, khong phai vi cham:

          - tai goi `oss-cad-suite`: 483 MB
          - tong hop mot loi RISC-V bang Yosys roi dat-di day bang nextpnr: vai phut

        Voi han 300 s, tac tu khong bao gio cham duoc cau goi `tool.install` den luc xong — no
        het luot giua duong, va lan sau vao lai thi bat dau lai tu dau. Do la mot vong lap khong
        bao gio ket thuc, khong phai mot buoc cham.

        Ghi lech trong EIDE-DEV-LOG. Mac dinh KHONG doi: chi du an nao can thi dat bien.
        """
        import os as _os

        def _so(ten: str, cu: float) -> float:
            v = (_os.environ.get(ten) or "").strip()
            if not v:
                return cu
            try:
                x = float(v)
            except ValueError:
                return cu
            # Tran tren co that: mot han muc vo han bien "tac tu dang lam" thanh "tac tu dang
            # treo" ma khong ai biet khi nao nen dung cho.
            return max(cu, min(x, 7200.0))

        self.max_seconds = _so("EIDE_TRAN_GIAY_LUOT", self.max_seconds)
        self.max_tool_calls = int(_so("EIDE_TRAN_LOI_GOI_LUOT", float(self.max_tool_calls)))


@dataclass(slots=True)
class ContextBudget:
    """Ngan sach token tung khoi ngu canh — EIDE-MEM-42 §4.1 (10 khoi).

    Ban truoc co 7 khoi theo MDD-40 §B2. MEM-42 them ba khoi va mot dieu quan trong
    hon ca ba: **du tru 20 %**. Khong co du tru thi ngu canh co the day den muc khong
    con cho cho chinh cau tra loi cua luot nay — va luc do loi khong phai "dai qua",
    ma la mot loi 400 giua chung.

    Nguyen tac P8: moi khoi co tran RIENG; vuot thi nen khoi do, khong "muon" cua khoi
    khac. Muon la cach mot khoi it quan trong an mat cho cua khoi quan trong.
    """

    # MEM-42 §4.1 ghi 2 000 va ghi chu "khong xay ra (co dinh)". Do that tren ban dang
    # chay: 3 503. Con so 2 000 duoc uoc TRUOC khi chin nguyen tac va bang §10 duoc viet
    # ra kem ly do; moi nguyen tac nay ~200 token va da rut het co the rut.
    #
    # Chon cach nao: cat hien phap cho vua con so, hay sua con so? Bang §10 la thu da
    # DO DUOC la doi hanh vi (tac tu ghi hien vat thay vi ke trong van xuoi, G3/G5), va
    # khoi nay duoc cache nen chi phi moi luot gan nhu bang khong. Cat no de dat mot muc
    # tieu ngan sach la doi mot hanh vi da do lay mot dong trong bang.
    #
    # Nen: dat tran theo so THAT + mot khoang tho, va them mot ca do chan no phinh tiep
    # (`test_hien_phap_khong_duoc_phinh_qua_tran`). Mot cai tran khong ai canh thi khong
    # phai la tran — xem DEV-254.
    # 3600 → 3700 ngày 29/09/2026, có chủ ý và có lý do.
    #
    # Ca `test_hien_phap_khong_duoc_phinh_qua_tran` đỏ khi hiến pháp thêm luật "hỏi không
    # phải là dừng" (§4). Chính ca ấy nói nó là một ĐIỂM QUYẾT ĐỊNH chứ không phải lệnh cấm:
    # *"đỏ nghĩa là ai đó vừa thêm vào hiến pháp — hãy quyết định có đáng không, đừng lặng lẽ
    # nâng trần."*
    #
    # Quyết định: đáng. Luật ấy làm ba ca Happy đang trượt của bộ usecase chuyển sang đạt
    # (TC006 · TC008 · TC052) — ba ca DUY NHẤT mà 76 ca nói là sai với sản phẩm. Trước khi
    # nâng đã tìm chỗ cắt: §10 dài nhất (721 token) nhưng cả bảng đều chịu lực.
    #
    # Nâng đúng 100, không nâng nhiều hơn. Hiến pháp nay 3676 token, nên lần thêm sau vẫn
    # chạm trần và vẫn phải mở lại đúng cuộc trò chuyện này. Nâng dư ra là tắt cái phanh.
    #
    # Chỗ này KHÁC với "sửa tiêu chí cho vừa kết quả" mà N6 cấm: N6 cấm hạ ngưỡng ĐẠT để một
    # phép thử hỏng thành đạt. Đây là một ngân sách token, và nó vừa mua được một hành vi đo
    # được — không phải một ô xanh.
    constitution: int = 3700
    tool_schema: int = 4000          # khoi 2 — luoc do tool hien thi
    eide_md: int = 3000
    inventory: int = 800
    facts: int = 2000
    human_edits: int = 1000
    pending: int = 300
    skills: int = 6000               # khoi 7 — skill da nap
    skills_hint: int = 300
    session_summary: int = 3000      # khoi 8 — ban tom tat phien (C2/C3)
    du_tru_ty_le: float = 0.20       # khoi 10 — bat kha xam pham

    # Bon nguong cua §4.2. Vuot tung muc thi lam gi, xem `muc_nen`.
    nguong_c1: float = 0.60
    nguong_c2: float = 0.70
    nguong_c3: float = 0.85
    nguong_c4: float = 0.95

    def du_tru(self, cua_so: int) -> int:
        return int(cua_so * self.du_tru_ty_le)

    def kha_dung(self, cua_so: int) -> int:
        """Phan thuc su dung duoc — cua so tru du tru."""
        return max(0, cua_so - self.du_tru(cua_so))

    def muc_nen(self, ty_le: float) -> str:
        """§4.2 — tra ve C0..C4 theo muc su dung."""
        if ty_le >= self.nguong_c4:
            return "C4"
        if ty_le >= self.nguong_c3:
            return "C3"
        if ty_le >= self.nguong_c2:
            return "C2"
        if ty_le >= self.nguong_c1:
            return "C1"
        return "C0"


@dataclass(slots=True)
class LatencyTargets:
    """MDD-40 §F3 — do tre. Dung trong test, khong chi de trang tri."""

    s0_hook_ms: float = 300.0
    inventory_ms: float = 50.0
    human_save_to_changeset_ms: float = 500.0
    undo_level1_ms: float = 1000.0
    snapshot_ms: float = 5000.0


@dataclass(slots=True)
class ModelConfig:
    """Gemini. Nhiet do 0 cho moi viec can lap lai duoc (§F3 "tat dinh").

    Chu san pham chot 25/09/2026: CHI dung `gemini-3.8-flash`, khong dung mo hinh khac.
    Vi vay ca ba vai tro (chinh, subagent, tom tat) deu tro ve mot ten — va `assert_allowed`
    canh chuyen do bang ma, de mot lan sua ba cau o dau do khong lam lot mot mo hinh la.
    """

    provider: str = "gemini"
    main: str = "gemini-3.8-flash"
    subagent: str = "gemini-3.8-flash"
    summarize: str = "gemini-3.8-flash"
    temperature: float = 0.0
    max_output_tokens: int = 8192
    context_window: int = 1_000_000
    api_key_env: str = "GEMINI_API_KEY"
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.main = os.environ.get("EIDE_MODEL_MAIN", self.main)
        self.subagent = os.environ.get("EIDE_MODEL_SUBAGENT", self.subagent)
        self.summarize = os.environ.get("EIDE_MODEL_SUMMARIZE", self.summarize)
        for m in (self.main, self.subagent, self.summarize):
            self.assert_allowed(m)

    @staticmethod
    def assert_allowed(model: str) -> str:
        if model not in ALLOWED_MODELS:
            raise ValueError(
                f"Mô hình {model!r} không nằm trong danh sách được phép: "
                f"{', '.join(sorted(ALLOWED_MODELS))}. "
                "Chủ sản phẩm chốt 25/09/2026 chỉ dùng gemini-3.8-flash."
            )
        return model

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) or os.environ.get("GOOGLE_API_KEY")


@dataclass(slots=True)
class Paths:
    """Duong dan cua MOT du an. Sandbox = project_root (MDD-40 §B3 "Sandbox")."""

    project_root: Path

    @property
    def state_dir(self) -> Path:
        """`.eide/` — so cai, changeset, blob, bo dem id."""
        return self.project_root / ".eide"

    @property
    def ledger(self) -> Path:
        return self.state_dir / "ledger.jsonl"

    @property
    def changesets(self) -> Path:
        return self.state_dir / "changesets.jsonl"  # §E5.1 "chi muc chung hai ben"

    @property
    def store_db(self) -> Path:
        return self.state_dir / "store.sqlite"      # §E5.1 event-sourcing

    @property
    def blobs(self) -> Path:
        return self.state_dir / "blobs"             # §E5.1 content-addressed

    @property
    def transcripts(self) -> Path:
        return self.state_dir / "transcripts"       # §B6 messages JSONL cua phien

    @property
    def eide_md(self) -> Path:
        return self.project_root / "EIDE.md"        # §B2/§B6 goc du an

    @property
    def blocks(self) -> Path:
        """`.eide/blocks/` — thu vien khoi cua DU AN (HIER-45 §5, tang 1)."""
        return self.state_dir / "blocks"

    def ensure(self) -> "Paths":
        # Đường dẫn dự án có thể do người GÕ TAY vào ô văn bản, không chỉ do bộ chọn sinh ra,
        # nên chặn ở giao diện là chưa đủ. Không kiểm ở đây thì `mkdir` ném
        # `NotADirectoryError: …/main.c/.eide` — đúng chỗ, nhưng người đọc không hiểu chuyện
        # gì và cũng không biết sửa thế nào.
        if self.project_root.exists() and not self.project_root.is_dir():
            raise NotADirectoryError(
                f"{self.project_root} là một TỆP, không phải thư mục. Dự án EIDE cần một "
                "thư mục: tác tử đọc/ghi bên trong nó và `.eide/` nằm ở đó. Chọn thư mục "
                "chứa tệp ấy, hoặc tạo một thư mục mới.")
        for d in (self.state_dir, self.blobs, self.transcripts):
            d.mkdir(parents=True, exist_ok=True)
        return self


def user_memory_path() -> Path:
    """`~/.eide/memory.md` — bo nho NGUOI DUNG, dung chung moi du an (§B6)."""
    return Path.home() / ".eide" / "memory.md"


def user_blocks_path() -> Path:
    """`~/.eide/blocks/` — thu vien khoi cua NGUOI DUNG (HIER-45 §5, tang 2).

    Tang 3 (goi toan cau M4, da phat hanh) chua co: no doi mot kenh phat hanh va mot chuoi
    hash, ma ca hai deu chua ton tai. Cho nen `tra_khoi` chi doc hai tang va NOI RO dieu do
    — mot tang rong khong duoc im lang thanh "khong co khoi nao".
    """
    return Path.home() / ".eide" / "blocks"


@dataclass(slots=True)
class Features:
    """Co tinh nang — EIDE-SCH-44 §2.1 lop bao ve so 1.

    Khac biet voi `ToolSpec.core` (nap tre): `core=False` VAN dang ky cong cu, chi giau
    no khoi luoc do cho toi khi `tool.search` mo ra. Co tinh nang thi manh hon — tat la
    **khong dang ky**, nen khong co nhanh ma nao cua tinh nang do chay duoc, va luoc do
    tool khong tang mot token nao.

    Doc theo thu tu: mac dinh trong ma → `~/.eide/settings.json` → bien moi truong.
    Bien moi truong dung sau cung de chay hoi quy HAI CHE DO ma khong sua tep cua nguoi:

        EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/thu_g5.py
    """

    schematic: bool = False        # SCH-44: sinh so do KiCad. Mac dinh TAT.
    # M1-02 — thu hep danh sach cong cu hien thi con CORE_GON, cat mo ta tham so, va go
    # cong cu mo tam sau 3 luot khong dung. Doi DANH SACH cong cu mo hinh nhin thay, tuc
    # la doi hanh vi tac tu (N-4) — nen mac dinh TAT, cho toi khi bo eval noi nguoc lai.
    gon_cong_cu: bool = False
    # M2-01 — mo truong `hien_thuc_req` tren luoc do `fs.write`/`fs.edit`, de tac tu KHAI
    # tep nay hien thuc REQ nao. Doi luoc do cong cu la doi hanh vi tac tu (N-4) — phan
    # nen (ghi va doc `deps.upstream`) chay ca khi co TAT.
    truy_vet: bool = False
    # M2-02 — hook Stop nhac khi con YEU CAU chua co phep do nao. Chen loi nhac vao
    # transcript la doi thu mo hinh doc moi luot (N-4). Khoi A2.2 tren tab A2 thi KHONG
    # phu thuoc co: no chi trinh bay thu da co trong kho.
    req_phu: bool = False
    # M2-03 — tra canh bao chat luong yeu cau (tieu chi khong do duoc, tu mo ho, trung
    # lap) trong ket qua cua store.req_create/req_update. Doi thu mo hinh doc sau moi lan
    # ghi yeu cau, nen sau co (N-4). Module `yeu_cau.py` thi luon co va luon kiem duoc.
    req_chat_luong: bool = False
    # M2-06 — buoc ke hoach phai khai KIEM BANG GI, va plan.step_done doi chieu so cai xem
    # phep kiem ay da chay thanh cong SAU lan ghi cua buoc chua. Them truong vao luoc do
    # plan.exit va them mot cua chan o step_done — doi hanh vi tac tu (N-4).
    ke_hoach_cong_kiem: bool = False
    # M3-10 — chay ERC ngay sau moi lan sua ban do mach, va khong de luot ket thuc khi con
    # loi chan MOI chua ai nhac toi. Doi `result.data` va chen loi nhac vao transcript, tuc
    # doi thu mo hinh doc moi luot (N-4).
    erc_tu_dong: bool = False
    # M4-02 — sim-runner la tac tu con NEU TIEU CHI va CHAY DO. Cho no `fs.write` ra ngoai
    # `sim/` la cho dung cai tac tu dang bi do quyen sua thuoc do cua minh: no viet lai
    # `test/*.c` roi chay lai, va bao cao cua no van hop le. Co bat thi `fs.write` cua
    # rieng sim-runner bi gioi han trong `sim/`.
    #
    # Sau co vi no DOI TAP VIEC mot tac tu con lam duoc (N-4): mot sim-runner khong ghi noi
    # tep test co the be tac o nhung viec truoc day no lam xong. Mac dinh TAT cho toi khi bo
    # eval noi nguoc lai. Hang rao chinh (POL-N6-sua-test) thi KHONG sau co — no chan ca
    # tac tu chinh lan tac tu con, bang mot phep do dem duoc.
    sim_runner_gioi_han: bool = False
    # M4-06 — EIDE tu DO do nhay sau khi test xanh, va tu NANG bo kiem.
    #
    # Hai thu sau co, va deu la N-4: mot Stop hook chen loi nhac vao transcript moi luot (doi
    # thu mo hinh doc), va cong cu `test.harden` goi mot tac tu con viet them ca kiem (doi
    # viec tac tu lam duoc, va tieu tien mo hinh).
    #
    # Phan KHONG sau co: `test.sensitivity` ghi hien vat kem `deps.upstream`. Do la sua loi
    # thuan — mot phep do khong vao kho thi bang chua do, va mot con so da loi thoi ma khong
    # ai danh dau thi te hon khong co con so.
    test_harden: bool = False

    @classmethod
    def load(cls) -> "Features":
        import json

        f = cls()
        p = Path.home() / ".eide" / "settings.json"
        if p.exists():
            try:
                d = (json.loads(p.read_text("utf-8")) or {}).get("features") or {}
            except (ValueError, OSError):
                d = {}
            for ten in cls.ten_co():
                if ten in d:
                    setattr(f, ten, bool(d[ten]))
        for ten in cls.ten_co():
            v = os.environ.get(f"EIDE_FEATURE_{ten.upper()}")
            if v is not None:
                setattr(f, ten, v.strip().lower() in ("1", "true", "yes", "on", "co"))
        return f

    @staticmethod
    def ten_co() -> tuple[str, ...]:
        return ("schematic", "gon_cong_cu", "truy_vet", "req_phu", "req_chat_luong",
                "ke_hoach_cong_kiem", "erc_tu_dong", "sim_runner_gioi_han",
                "test_harden")

    def bat(self, ten: str) -> bool:
        return bool(getattr(self, ten, False))

    def dang_bat(self) -> list[str]:
        return [t for t in self.ten_co() if self.bat(t)]

    def to_dict(self) -> dict[str, bool]:
        return {t: self.bat(t) for t in self.ten_co()}


@dataclass(slots=True)
class Config:
    paths: Paths
    budget: Budget = field(default_factory=Budget)
    context_budget: ContextBudget = field(default_factory=ContextBudget)
    latency: LatencyTargets = field(default_factory=LatencyTargets)
    model: ModelConfig = field(default_factory=ModelConfig)
    features: Features = field(default_factory=Features.load)
    autonomy: str = "A3"
    language: str = "vi"
    # Che do do: khong goi mo hinh that, dung ban ghi lai. Dung cho 76 TC chay lap 5 lan.
    offline: bool = False

    @classmethod
    def for_project(cls, root: str | Path, **kw) -> "Config":
        return cls(paths=Paths(Path(root).expanduser().resolve()).ensure(), **kw)
