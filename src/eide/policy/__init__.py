# -*- coding: utf-8 -*-
"""Lớp cấp quyền: allow | ask (thẻ cổng) | deny — EIDE-MDD-40 §B4."""

from .engine import DEFAULT_POLICY, Decision, PolicyEngine

__all__ = ["PolicyEngine", "Decision", "DEFAULT_POLICY"]
