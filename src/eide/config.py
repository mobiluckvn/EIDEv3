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


@dataclass(slots=True)
class ContextBudget:
    """Ngan sach token tung khoi ngu canh — MDD-40 §B2 (bang)."""

    constitution: int = 2000
    eide_md: int = 3000
    inventory: int = 800
    facts: int = 2000
    human_edits: int = 1000
    pending: int = 300
    skills_hint: int = 300


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

    def ensure(self) -> "Paths":
        for d in (self.state_dir, self.blobs, self.transcripts):
            d.mkdir(parents=True, exist_ok=True)
        return self


def user_memory_path() -> Path:
    """`~/.eide/memory.md` — bo nho NGUOI DUNG, dung chung moi du an (§B6)."""
    return Path.home() / ".eide" / "memory.md"


@dataclass(slots=True)
class Config:
    paths: Paths
    budget: Budget = field(default_factory=Budget)
    context_budget: ContextBudget = field(default_factory=ContextBudget)
    latency: LatencyTargets = field(default_factory=LatencyTargets)
    model: ModelConfig = field(default_factory=ModelConfig)
    autonomy: str = "A3"
    language: str = "vi"
    # Che do do: khong goi mo hinh that, dung ban ghi lai. Dung cho 76 TC chay lap 5 lan.
    offline: bool = False

    @classmethod
    def for_project(cls, root: str | Path, **kw) -> "Config":
        return cls(paths=Paths(Path(root).expanduser().resolve()).ensure(), **kw)
