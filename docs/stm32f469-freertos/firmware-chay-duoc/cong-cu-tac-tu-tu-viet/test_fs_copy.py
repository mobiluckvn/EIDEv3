# -*- coding: utf-8 -*-
"""Bộ kiểm cho fs.copy và fs.remove."""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from fs_copy import fs_copy_impl, fs_remove_impl


def test_fs_copy_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        src = root / "hello.txt"
        src.write_text("xin chao")
        dst = root / "sub" / "hello_copy.txt"

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        res = fs_copy_impl(mock_ctx, "hello.txt", "sub/hello_copy.txt")
        assert res["ok"] is True
        assert res["count"] == 1
        assert dst.exists()
        assert dst.read_text() == "xin chao"


def test_fs_copy_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        src_dir = root / "src_folder"
        src_dir.mkdir()
        (src_dir / "f1.txt").write_text("file 1")
        (src_dir / "f2.txt").write_text("file 2")
        sub = src_dir / "child"
        sub.mkdir()
        (sub / "f3.txt").write_text("file 3")

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        res = fs_copy_impl(mock_ctx, "src_folder", "dst_folder")
        assert res["ok"] is True
        assert res["count"] == 3
        assert (root / "dst_folder" / "f1.txt").read_text() == "file 1"
        assert (root / "dst_folder" / "child" / "f3.txt").read_text() == "file 3"


def test_fs_copy_nonexistent():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        with pytest.raises(FileNotFoundError):
            fs_copy_impl(mock_ctx, "khong_ton_tai.txt", "dich.txt")


def test_fs_remove():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "temp.txt"
        target.write_text("tam thoi")

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        res = fs_remove_impl(mock_ctx, "temp.txt")
        assert res["ok"] is True
        assert not target.exists()
