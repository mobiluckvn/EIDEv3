# -*- coding: utf-8 -*-
"""Công cụ để tác tử TỰ BÙ NĂNG LỰC: `tool.propose` và `tool.reload`.

    tool.propose → kiểm đề xuất bằng mã → thẻ G-TOOL (hiện KHUNG MÃ sẽ ghi)
    (người duyệt)
    → tác tử viết `.eide/cong-cu/<ten>.py` và `.eide/cong-cu/test_<ten>.py` bằng fs.write
    tool.reload  → CHẠY bộ kiểm; xanh thì nạp và đăng ký, đỏ thì từ chối

Xem `eide/nang_luc.py` cho bốn hàng rào và lý do của từng cái.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from ..errors import EideError
from ..nang_luc import (MA_DE_XUAT, NHOM_HOP_LE, duong_ma, duong_test, khuon_ma,
                        khuon_test, kiem_de_xuat)
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA

# Bộ kiểm của một công cụ mới không được chạy lâu hơn thế. Dài hơn nghĩa là nó đang làm việc
# khác chứ không phải kiểm một công cụ.
TRAN_GIAY_TEST = 120.0


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:
    @r.tool("tool.propose", "Điều phối",
            "XIN TỰ VIẾT một công cụ mới cho chính mình, khi bạn thấy EIDE thiếu một năng "
            "lực và việc cày tay đang quá tốn. Nói rõ: công cụ trả lời câu hỏi nào, số đo "
            "chứng minh cày tay không đủ, và sẽ kiểm bằng ca nào. Người dùng duyệt thì bạn "
            "viết mã + bộ kiểm, rồi `tool.reload`.",
            {"type": "object",
             "properties": {
                 "ten": {"type": "string",
                         "description": "dạng `nhom.viec`, ví dụ `code.symbolize`"},
                 "nhom": {"type": "string", "enum": list(NHOM_HOP_LE)},
                 "viec": {"type": "string",
                          "description": "công cụ này trả lời câu hỏi nào, một câu"},
                 "vi_sao": {"type": "string",
                            "description": ("vì sao cày tay không đủ — PHẢI có số đo: bao "
                                            "nhiêu lời gọi đã tốn, bao lâu, thử mấy lần")},
                 "test": {"type": "string",
                          "description": "sẽ kiểm những ca nào, kể cả ca nó phải IM LẶNG"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["ten", "nhom", "viec", "vi_sao", "test", "explain"]},
            risk="R3", gate="G-TOOL", core=True, needs_explain=True,
            keywords=["thiếu công cụ", "tự viết công cụ", "bù năng lực", "propose",
                      "cày tay", "không có công cụ nào"])
    def tool_propose(ctx: Any, explain: dict[str, Any], ten: str, nhom: str,
                     viec: str, vi_sao: str, test: str):
        loi = kiem_de_xuat(ten, viec, vi_sao, test,
                           lambda t: ctx.registry.get(t) is not None)
        if loi:
            return ToolResult(False, error=EideError(
                "E7001", "Đề xuất chưa trình được: " + " · ".join(loi),
                hint_for_agent=("Sửa rồi gọi lại. Phần `vi_sao` là phần người dùng đọc để "
                                "quyết — số đo của chính bạn ở đó có trọng lượng hơn mọi "
                                "lập luận."),
                details={"loi": loi}, blame="agent"))

        ma, tst = duong_ma(ten), duong_test(ten)
        ctx.store.apply(
            artefact_id=MA_DE_XUAT + ten, type="tool_propose",
            op="update" if ctx.store.get(MA_DE_XUAT + ten) else "create",
            author=f"agent:{ctx.run_id}",
            canonical={"ten": ten, "nhom": nhom, "viec": viec, "vi_sao": vi_sao,
                       "test": test, "duong_ma": ma, "duong_test": tst,
                       "trang_thai": "da_duyet"},
            explain=explain, view_hint={"kind": "kv", "path": ma})
        return {
            "ten": ten, "duong_ma": ma, "duong_test": tst,
            "khuon_ma": khuon_ma(ten, nhom, viec), "khuon_test": khuon_test(ten, test),
            "note_vi": (
                f"Được duyệt. Giờ viết hai tệp:\n\n"
                f"1. `{ma}` — công cụ. `khuon_ma` trong kết quả này là khung, bạn điền phần "
                "thân.\n"
                f"2. `{tst}` — bộ kiểm. **Bộ này phải XANH thì công cụ mới được đăng ký.**\n\n"
                "Viết test trước khi viết thân thì rẻ hơn, và nhớ ca **nó phải im lặng**: "
                "một bộ dò kêu quá tay sẽ thành máy báo động giả, mà báo động giả dạy người "
                "ta bỏ qua cảnh báo — đắt hơn hẳn việc không có nó.\n\n"
                f"Xong hai tệp thì gọi `tool.reload` với `ten=\"{ten}\"`.")}

    @r.tool("tool.reload", "Điều phối",
            "NẠP công cụ bạn vừa tự viết. Nó CHẠY bộ kiểm của công cụ ấy trước: xanh thì "
            "đăng ký và dùng được ngay, đỏ thì từ chối và trả lại đúng chỗ hỏng.",
            {"type": "object",
             "properties": {"ten": {"type": "string"}},
             "required": ["ten"]},
            risk="R2", core=False,
            keywords=["nạp công cụ", "reload", "đăng ký công cụ"])
    def tool_reload(ctx: Any, ten: str):
        a = ctx.store.get(MA_DE_XUAT + ten)
        if not a:
            return ToolResult(False, error=EideError(
                "E7002", f"Chưa có đề xuất nào được duyệt cho `{ten}`.",
                hint_for_agent="Gọi `tool.propose` trước — người dùng phải duyệt đã.",
                alternatives=["tool.propose"], blame="agent"))
        goc = Path(ctx.config.paths.project_root)
        ma, tst = goc / duong_ma(ten), goc / duong_test(ten)
        thieu = [str(p.relative_to(goc)) for p in (ma, tst) if not p.exists()]
        if thieu:
            return ToolResult(False, error=EideError(
                "E7003", "Chưa viết xong: thiếu " + ", ".join(thieu),
                hint_for_agent=("Cả hai tệp đều bắt buộc. Công cụ không có bộ kiểm thì nó "
                                "là một lời hứa, không phải một năng lực."),
                details={"thieu": thieu}, blame="agent"))

        # Hàng rào chính: bộ kiểm phải XANH. Chạy trong tiến trình riêng — một bộ kiểm hỏng
        # không được phép kéo theo cả EIDE.
        try:
            r2 = subprocess.run([sys.executable, "-m", "pytest", "-q", str(tst)],
                                cwd=str(goc), capture_output=True, text=True,
                                timeout=TRAN_GIAY_TEST)
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=EideError(
                "E7004", f"Bộ kiểm của `{ten}` chạy quá {TRAN_GIAY_TEST:.0f} giây.",
                hint_for_agent=("Dài hơn thế nghĩa là nó đang làm việc khác chứ không phải "
                                "kiểm một công cụ. Cắt bớt, hoặc giả lập phần chậm."),
                blame="agent"))
        ra = ((r2.stdout or "") + (r2.stderr or ""))[-1500:]
        if r2.returncode != 0:
            return ToolResult(False, error=EideError(
                "E7005", f"Bộ kiểm của `{ten}` ĐỎ — công cụ không được đăng ký.",
                hint_for_agent=("Đọc phần đuôi dưới đây, sửa, rồi gọi lại `tool.reload`. "
                                "Đừng sửa test cho vừa mã: N6 — không đổi tiêu chí để đạt."),
                details={"pytest": ra}, blame="agent"))

        # Nạp và đăng ký. Tới đây mã đã có bộ kiểm xanh đứng sau.
        #
        # Nạp THEO ĐƯỜNG DẪN, không theo tên gói: tệp nằm trong dự án của người dùng, không
        # trong cây mã của EIDE — vì `fs.write` bị chặn ngoài thư mục dự án, nên tác tử
        # không ghi vào `src/eide/` được, và điều đó là đúng.
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                f"eide_cong_cu_{ten.replace('.', '_')}", ma)
            if spec is None or spec.loader is None:
                raise ImportError(f"không nạp được {ma}")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if not hasattr(mod, "dang_ky"):
                raise AttributeError("tệp không có hàm `dang_ky(r)`")
            truoc = {t.name for t in ctx.registry.all()}
            mod.dang_ky(ctx.registry)
            moi = sorted({t.name for t in ctx.registry.all()} - truoc)
        except Exception as e:                                   # noqa: BLE001
            return ToolResult(False, error=EideError(
                "E7006", f"Nạp `{ten}` hỏng: {type(e).__name__}: {e}",
                hint_for_agent=("Tệp phải có `def dang_ky(r): ...` và đăng ký đúng tên đã "
                                "đề xuất. Bộ kiểm xanh mà nạp hỏng nghĩa là bộ kiểm chưa "
                                "chạm tới phần đăng ký — thêm một ca cho nó."),
                blame="agent"))
        if ten not in moi:
            return ToolResult(False, error=EideError(
                "E7007", f"Nạp xong nhưng KHÔNG có công cụ tên `{ten}`. "
                         f"Đăng ký được: {', '.join(moi) or 'không cái nào'}.",
                hint_for_agent=("Tên trong `r.tool(...)` phải khớp đúng tên đã đề xuất và "
                                "được duyệt — người dùng duyệt một cái tên cụ thể."),
                details={"da_dang_ky": moi}, blame="agent"))

        ctx.registry.unlock(ten) if hasattr(ctx.registry, "unlock") else None
        return {
            "ten": ten, "da_dang_ky": moi, "pytest": ra[-400:],
            "note_vi": (
                f"`{ten}` đã đăng ký và dùng được ngay trong lượt này. Bộ kiểm xanh.\n\n"
                "Nó là mã do BẠN viết, nằm ở `src/eide/tools/them/` để nguồn gốc luôn nhìn "
                "thấy được, và là một changeset bình thường nên hoàn tác được.\n\n"
                "Lần tới gặp một việc phải cày tay nhiều lượt, nhớ rằng bạn làm được điều "
                "này — đó thường là dấu hiệu thiếu công cụ, không phải thiếu cố gắng.")}
