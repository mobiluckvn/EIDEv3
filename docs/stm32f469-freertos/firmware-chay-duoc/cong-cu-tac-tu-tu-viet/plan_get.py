# -*- coding: utf-8 -*-
"""`plan.get` — công cụ do TÁC TỬ tự viết.

Xem toàn văn chi tiết kế hoạch đang chạy: mục tiêu, các bước, công cụ, cổng, hiện vật và trạng thái.
Sử dụng ctx.store để truy xuất hiện vật plan:current an toàn và đồng nhất.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def lay_ke_hoach_hien_tai(ctx: Any = None) -> Optional[Dict[str, Any]]:
    if ctx is None:
        return None
    store = getattr(ctx, "store", None)
    if store is None and isinstance(ctx, dict):
        store = ctx.get("store")
    if store is None:
        return None

    try:
        art = store.get("plan:current")
        if not art:
            return None
        if hasattr(art, "canonical") and isinstance(art.canonical, dict):
            return art.canonical
        if isinstance(art, dict):
            canon = art.get("canonical")
            if isinstance(canon, dict):
                return canon
            return art
        if hasattr(art, "data") and isinstance(art.data, dict):
            return art.data
        return None
    except Exception:
        return None


def thuc_thi_plan_get(ctx: Any = None) -> Dict[str, Any]:
    plan = lay_ke_hoach_hien_tai(ctx)
    if not plan or not plan.get("steps"):
        return {
            "co_ke_hoach": False,
            "thong_bao": "Hiện không có kế hoạch nào đang chạy hoặc chưa có kế hoạch được duyệt."
        }

    steps = plan.get("steps", [])
    da_xong = sum(1 for s in steps if s.get("xong") is True)
    return {
        "co_ke_hoach": True,
        "muc_tieu": plan.get("muc_tieu", ""),
        "trang_thai": plan.get("trang_thai", ""),
        "run_id": plan.get("run_id", ""),
        "tong_buoc": len(steps),
        "da_xong": da_xong,
        "buoc": [
            {
                "so": idx + 1,
                "viec": s.get("viec", ""),
                "cong_cu": s.get("cong_cu", ""),
                "cong": s.get("cong", ""),
                "hien_vat": s.get("hien_vat", ""),
                "xong": s.get("xong", False),
                "ghi_chu": s.get("ghi_chu", ""),
                "chi_phi": s.get("chi_phi", "")
            }
            for idx, s in enumerate(steps)
        ],
        "gia_dinh": plan.get("gia_dinh", []),
        "ngoai_pham_vi": plan.get("ngoai_pham_vi", [])
    }


def dang_ky(r) -> None:
    @r.tool("plan.get", "Điều phối",
            "Xem toàn văn chi tiết kế hoạch đang chạy: mục tiêu, các bước, công cụ, cổng, hiện vật và trạng thái",
            {"type": "object", "properties": {}, "required": []},
            risk="R1", core=False, keywords=["plan", "kế hoạch", "tiến độ"])
    def plan_get(ctx: Any = None) -> Dict[str, Any]:
        return thuc_thi_plan_get(ctx)
