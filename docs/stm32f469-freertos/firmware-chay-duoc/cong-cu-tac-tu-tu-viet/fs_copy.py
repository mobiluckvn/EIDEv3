# -*- coding: utf-8 -*-
"""`fs.copy` và `fs.remove` — công cụ do TÁC TỬ tự viết.

Sao chép và dọn dẹp tệp hoặc thư mục trong vùng làm việc.
"""

from __future__ import annotations

import shutil
import os
from pathlib import Path
from typing import Any, Dict


def fs_copy_impl(ctx: Any, nguon: str, dich: str) -> Dict[str, Any]:
    project_root = Path(ctx.config.paths.project_root).resolve()

    src = Path(nguon)
    if not src.is_absolute():
        src = (project_root / src).resolve()

    if not src.exists():
        raise FileNotFoundError(f"Đường dẫn nguồn không tồn tại: {nguon}")

    dst = Path(dich)
    if not dst.is_absolute():
        dst = (project_root / dst).resolve()

    try:
        dst.relative_to(project_root)
    except ValueError:
        if not str(dst).startswith(str(project_root.parent)):
            raise PermissionError(f"Đường dẫn đích nằm ngoài vùng làm việc: {dich}")

    total_files = 0
    total_bytes = 0

    if src.is_file():
        if dst.is_dir():
            target_file = dst / src.name
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            target_file = dst
        shutil.copy2(src, target_file)
        total_files = 1
        total_bytes = target_file.stat().st_size
    elif src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.rglob("*"):
            rel = item.relative_to(src)
            dest_item = dst / rel
            if item.is_dir():
                dest_item.mkdir(parents=True, exist_ok=True)
            elif item.is_file():
                dest_item.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_item)
                total_files += 1
                total_bytes += dest_item.stat().st_size
    else:
        raise ValueError(f"Loại tệp không được hỗ trợ: {src}")

    return {
        "ok": True,
        "count": total_files,
        "bytes": total_bytes,
        "nguon": str(src),
        "dich": str(dst)
    }


def fs_remove_impl(ctx: Any, duong_dan: str) -> Dict[str, Any]:
    project_root = Path(ctx.config.paths.project_root).resolve()
    target = Path(duong_dan)
    if not target.is_absolute():
        target = (project_root / target).resolve()

    if not target.exists():
        return {"ok": True, "note": "Tệp không tồn tại"}

    try:
        target.relative_to(project_root)
    except ValueError:
        raise PermissionError(f"Đường dẫn xoá nằm ngoài dự án: {duong_dan}")

    if target.is_file() or target.is_symlink():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)

    return {"ok": True, "xoa": str(target)}


def dang_ky(r) -> None:
    @r.tool("fs.copy", "Tệp & lệnh",
            "Sao chép một tệp hoặc toàn bộ thư mục từ đường dẫn nguồn sang đường dẫn đích trong vùng làm việc",
            {
                "type": "object",
                "properties": {
                    "nguon": {"type": "string", "description": "Đường dẫn tệp hoặc thư mục nguồn"},
                    "dich": {"type": "string", "description": "Đường dẫn tệp hoặc thư mục đích"}
                },
                "required": ["nguon", "dich"]
            },
            risk="R1", core=False, keywords=["copy", "sao chép", "tệp"])
    def fs_copy(ctx: Any, nguon: str, dich: str) -> Dict[str, Any]:
        return fs_copy_impl(ctx, nguon, dich)

    @r.tool("fs.remove", "Tệp & lệnh",
            "Xoá một tệp hoặc thư mục thừa trong vùng làm việc của dự án",
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
