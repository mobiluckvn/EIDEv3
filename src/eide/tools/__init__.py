# -*- coding: utf-8 -*-
"""Công cụ — mọi năng lực của tác tử là một công cụ có hợp đồng (§B3)."""

from .builtin import build_registry
from .registry import Registry, Requirement, ToolResult, ToolSpec

__all__ = ["build_registry", "Registry", "ToolSpec", "ToolResult", "Requirement"]
