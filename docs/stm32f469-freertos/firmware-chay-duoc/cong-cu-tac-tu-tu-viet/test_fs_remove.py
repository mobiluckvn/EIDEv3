# -*- coding: utf-8 -*-
"""Bộ kiểm cho fs.remove."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from fs_remove import fs_remove_impl


def test_fs_remove_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "temp.txt"
        target.write_text("noi dung tam")

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        res = fs_remove_impl(mock_ctx, "temp.txt")
        assert res["ok"] is True
        assert not target.exists()


def test_fs_remove_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target_dir = root / "sub_dir"
        target_dir.mkdir()
        (target_dir / "f1.txt").write_text("1")

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        res = fs_remove_impl(mock_ctx, "sub_dir")
        assert res["ok"] is True
        assert not target_dir.exists()


def test_fs_remove_outside_rejected():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir) / "project"
        root.mkdir()
        outside = Path(tmpdir) / "outside.txt"
        outside.write_text("ngoai")

        mock_ctx = MagicMock()
        mock_ctx.config.paths.project_root = root

        with pytest.raises(PermissionError):
            fs_remove_impl(mock_ctx, "../outside.txt")
