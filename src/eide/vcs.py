# -*- coding: utf-8 -*-
"""Git cho phần tệp của dự án — EIDE-MDD-40 §E5.1, §E4 bước 3.

    "Lưu trữ: tệp (mã, netlist, EIDE.md, criteria) trong git của dự án — mỗi changeset
     một commit với message có cấu trúc `cs-0109 | agent:run-43 | code ×2 | <summary>`"

Vì sao dùng git chứ không tự viết lớp phiên bản: ba thứ ta cần đều khó làm đúng và git
đã làm đúng từ lâu — diff tin cậy, revert đúng ngữ nghĩa, và **3-way merge** cho đường
ống "người sửa trong lúc tác tử cũng sửa" (§E4 bước 3, ca CX09). Tự viết merge cho mã C
là tự chuốc lấy một lớp bug mà không ai kiểm được.

Đường lui: mọi thao tác ở đây đều có thể thất bại (máy không có git, thư mục chỉ đọc).
Khi đó changeset **vẫn được ghi** — chỉ là phần tệp mất khả năng hoàn tác bằng git, và
điều đó phải được NÓI RA chứ không nuốt vào trong.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitKhongSan(RuntimeError):
    """Không dùng được git ở thư mục này. Gọi tới phải xử lý, không được lờ đi."""


@dataclass(slots=True)
class KetQuaMerge:
    sach: bool
    noi_dung: str
    doan_xung_dot: int = 0


class Vcs:
    """Kho git của MỘT dự án."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    # ------------------------------------------------------------------ chạy lệnh
    def _git(self, *args: str, dau_vao: str | None = None, check: bool = True) -> str:
        try:
            r = subprocess.run(
                ["git", "-C", str(self.root), *args],
                input=dau_vao, capture_output=True, text=True, timeout=60)
        except FileNotFoundError:
            raise GitKhongSan("Máy chưa cài git.")
        except subprocess.TimeoutExpired:
            raise GitKhongSan("Lệnh git quá hạn 60 giây.")
        if check and r.returncode != 0:
            raise GitKhongSan(f"git {' '.join(args)} → {r.returncode}: {r.stderr.strip()[:300]}")
        return r.stdout

    @property
    def san_sang(self) -> bool:
        """Dự án này có kho git CỦA CHÍNH NÓ chưa.

        Phải so `--show-toplevel` với gốc dự án, không được chỉ hỏi `--git-dir`: lệnh
        đó **đi ngược lên cây thư mục**. Một dự án nằm trong thư mục con của một kho
        git khác sẽ bị coi là "đã có git", và EIDE sẽ commit tệp của người dùng vào
        kho của người khác. Đây là lỗi đã xảy ra thật, không phải giả định.
        """
        try:
            top = self._git("rev-parse", "--show-toplevel").strip()
        except GitKhongSan:
            return False
        try:
            return top and Path(top).resolve() == self.root.resolve()
        except OSError:
            return False

    def khoi_tao(self) -> bool:
        """Dựng kho git nếu chưa có. Trả về True nếu vừa tạo mới."""
        if self.san_sang:
            self._dam_bao_danh_tinh()
            return False
        self._git("init", "-q", "-b", "main")
        self._dam_bao_danh_tinh()
        # `.eide/` là trạng thái nội bộ (sổ cái, kho, blob) — nó có lịch sử riêng và
        # không được trộn vào lịch sử mã của người dùng.
        gi = self.root / ".gitignore"
        if not gi.exists():
            gi.write_text(".eide/\n", "utf-8")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "cs-0000 | eide | khởi tạo | trạng thái ban đầu",
                  "--allow-empty")
        return True

    def _dam_bao_danh_tinh(self) -> None:
        """Máy chưa cấu hình user.name/email thì commit sẽ hỏng. Đặt cục bộ cho kho này."""
        for khoa, gia in (("user.name", "EIDE"), ("user.email", "eide@localhost")):
            if not self._git("config", "--get", khoa, check=False).strip():
                self._git("config", khoa, gia)

    # ------------------------------------------------------------------ ghi
    def commit(self, *, cs_id: str, author: str, summary: str,
               paths: list[str] | None = None) -> str | None:
        """Một changeset một commit. Trả sha, hoặc None nếu không có gì để commit."""
        if paths:
            for p in paths:
                self._git("add", "--", p, check=False)
        else:
            self._git("add", "-A")
        if not self._git("diff", "--cached", "--name-only").strip():
            return None
        n = len(paths or self.thay_doi_dang_cho())
        msg = f"{cs_id} | {author} | tệp ×{n} | {summary[:120]}"
        self._git("commit", "-q", "-m", msg)
        return self._git("rev-parse", "HEAD").strip()

    def thay_doi_dang_cho(self) -> list[str]:
        out = self._git("status", "--porcelain", check=False)
        return [l[3:].strip() for l in out.splitlines() if l.strip()]

    # ------------------------------------------------------------------ hoàn tác
    def revert(self, sha: str, *, cs_id: str) -> str | None:
        """Hoàn tác một commit bằng cách tạo commit MỚI — §E5.2 "không xoá lịch sử"."""
        self._git("revert", "--no-commit", "--no-edit", sha)
        if not self._git("diff", "--cached", "--name-only").strip():
            self._git("revert", "--quit", check=False)
            return None
        self._git("commit", "-q", "-m", f"{cs_id} | hoàn tác | revert {sha[:8]}")
        return self._git("rev-parse", "HEAD").strip()

    def khoi_phuc_tep(self, path: str, noi_dung: str, *, cs_id: str, author: str,
                      summary: str) -> str | None:
        """Đặt lại nội dung một tệp rồi commit — đường lui khi revert không áp được."""
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(noi_dung, "utf-8")
        return self.commit(cs_id=cs_id, author=author, summary=summary, paths=[path])

    # ------------------------------------------------------------------ đọc
    def noi_dung_tai(self, sha: str, path: str) -> str | None:
        try:
            return self._git("show", f"{sha}:{path}")
        except GitKhongSan:
            return None

    def diff(self, sha: str, *, gon: bool = False) -> str:
        args = ["show", "--format=%s", "--stat" if gon else "--patch", sha]
        return self._git(*args, check=False)

    def diff_lam_viec(self, path: str | None = None) -> str:
        args = ["diff", "HEAD"]
        if path:
            args += ["--", path]
        return self._git(*args, check=False)

    def sha_hien_tai(self) -> str | None:
        s = self._git("rev-parse", "HEAD", check=False).strip()
        return s or None

    def lich_su_tep(self, path: str, n: int = 20) -> list[dict[str, str]]:
        out = self._git("log", f"-{n}", "--format=%H%x1f%s%x1f%aI", "--", path, check=False)
        rows = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 3:
                rows.append({"sha": parts[0], "message": parts[1], "ts": parts[2]})
        return rows

    # ------------------------------------------------------------------ merge 3 chiều
    def merge_ba_chieu(self, *, base: str, cua_nguoi: str, cua_tac_tu: str,
                       nhan_nguoi: str = "bản của anh",
                       nhan_tac_tu: str = "bản của tác tử") -> KetQuaMerge:
        """§E4 bước 3 — "3-way merge (base, người, tác tử)".

        Ý nghĩa của thứ tự tham số: bản của NGƯỜI là "ours". Khi git không tự quyết
        được, đoạn của người nằm trên và được giữ nguyên trong tệp kết quả. §E4 bước 6
        nói thẳng: "KHÔNG ghi đè sửa của người nếu không được đồng ý".
        """
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = Path(d)
            (t / "base").write_text(base, "utf-8")
            (t / "ours").write_text(cua_nguoi, "utf-8")
            (t / "theirs").write_text(cua_tac_tu, "utf-8")
            r = subprocess.run(
                ["git", "merge-file", "-p",
                 "-L", nhan_nguoi, "-L", "bản gốc", "-L", nhan_tac_tu,
                 str(t / "ours"), str(t / "base"), str(t / "theirs")],
                capture_output=True, text=True)
            if r.returncode < 0:
                raise GitKhongSan(f"merge-file hỏng: {r.stderr[:200]}")
            return KetQuaMerge(sach=r.returncode == 0, noi_dung=r.stdout,
                               doan_xung_dot=max(0, r.returncode))
