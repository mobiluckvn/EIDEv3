# -*- coding: utf-8 -*-
"""Nền tri thức — EIDE-MDD-40 Phần C.

Bốn mảnh, mỗi mảnh giữ một nguyên tắc:

    `ingest`    phân loại theo nội dung, lý do lỗi đúng      (TC023–026, TC070)
    `docs`      tài liệu theo trang, Fact đọc BẰNG MÃ         N1
    `passport`  hộ chiếu chỉ ghim khi có tài liệu; kho ISA    DEV-183, TC018
    `compare`   so sánh có bằng chứng, từ chối vế ĐỒNG        N2
"""

from . import compare, docs, ingest, passport

__all__ = ["ingest", "docs", "passport", "compare"]
