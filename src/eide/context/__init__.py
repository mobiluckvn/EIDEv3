# -*- coding: utf-8 -*-
"""Ngữ cảnh mỗi lượt: hiến pháp + sáu khối nhắc — EIDE-MDD-40 §B2."""

from .assemble import (
    CONSTITUTION_PATH, Assembled, approx_tokens, assemble, mentioned_entities,
)

__all__ = ["assemble", "Assembled", "approx_tokens", "mentioned_entities", "CONSTITUTION_PATH"]
