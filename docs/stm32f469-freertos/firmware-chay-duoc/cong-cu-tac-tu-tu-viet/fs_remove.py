# -*- coding: utf-8 -*-
"""`fs.remove` — công cụ do TÁC TỬ tự viết.

Xoá một tệp hoặc thư mục trong vùng làm việc của dự án.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict


def fs_remove_impl(ctx: Any, duong_dan: str) -> Dict[str, Any]:
    project_root = Path(ctx.config.paths.project_root).resolve()
    target = Path(duong_dan)
    if not target.is_absolute():
        target = (project_root / target).resolve()

    try:
        target.relative_to(project_root)
    except ValueError:
        raise PermissionError(f"Đường dẫn xoá nằm ngoài dự án: {duong_dan}")

    if not target.exists():
        return {"ok": True, "note": "Đường dẫn không tồn tại", "xoa": str(target)}

    if target.is_file() or target.is_symlink():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)

    return {"ok": True, "xoa": str(target)}


def dang_ky(r) -> None:
    @r.tool("fs.remove", "Tệp & lệnh",
            "Xoá một tệp hoặc thư mục trong vùng làm việc của dự án",
            {
                "type": "object",
                "properties": {
                    "duong_dan": {"type": "string", "description": "Đường dẫn tương đối tới tệp hoặc thư mục cần xoá"}
                },
                "required": ["duong_dan"]
            },
            risk="R1", core=False, keywords=["xóa", "remove", "dọn"])
    def fs_remove(ctx: Any, duong_dan: str) -> Dict[str, Any]:
        return fs_remove_impl(ctx, duong_dan)
