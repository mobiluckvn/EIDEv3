# -*- coding: utf-8 -*-
"""Bộ kiểm cho `plan.get` — công cụ do tác tử tự viết.

Các ca kiểm:
Ca 1: Có kế hoạch đang chạy qua ctx.store -> trả về danh sách bước, trạng thái hoàn thành và hiện vật tương ứng.
Ca 2: Không có kế hoạch nào (store rỗng, hoặc ctx None) -> nói rõ ràng không có kế hoạch, KHÔNG trả về cấu trúc rỗng giả như có.
Ca 3: Kiểm tra đăng ký tool vào registry và gọi tool thông qua context.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import pytest

from plan_get import lay_ke_hoach_hien_tai, thuc_thi_plan_get, dang_ky


class MockStore:
    def __init__(self, plan_data: Optional[Dict[str, Any]] = None):
        self._data = {}
        if plan_data is not None:
            self._data["plan:current"] = {"canonical": plan_data}

    def get(self, key: str) -> Any:
        return self._data.get(key)


class MockContext:
    def __init__(self, store: Optional[MockStore] = None):
        self.store = store


def test_ca1_co_ke_hoach():
    mock_plan = {
        "muc_tieu": "Mục tiêu thử nghiệm",
        "trang_thai": "da_duyet",
        "run_id": "run-001",
        "steps": [
            {"viec": "Bước 1", "cong_cu": "fs.write", "cong": "", "hien_vat": "file1.c", "xong": True, "ghi_chu": "", "chi_phi": "1 lời gọi"},
            {"viec": "Bước 2", "cong_cu": "build.compile", "cong": "", "hien_vat": "build", "xong": False, "ghi_chu": "", "chi_phi": "2 lời gọi"}
        ],
        "gia_dinh": ["Giả định A"],
        "ngoai_pham_vi": ["Ngoài phạm vi B"]
    }
    ctx = MockContext(MockStore(mock_plan))
    res = thuc_thi_plan_get(ctx)
    assert res["co_ke_hoach"] is True
    assert res["muc_tieu"] == "Mục tiêu thử nghiệm"
    assert res["tong_buoc"] == 2
    assert res["da_xong"] == 1
    assert len(res["buoc"]) == 2
    assert res["buoc"][0]["viec"] == "Bước 1"
    assert res["buoc"][0]["xong"] is True
    assert res["buoc"][1]["viec"] == "Bước 2"
    assert res["buoc"][1]["xong"] is False
    assert res["gia_dinh"] == ["Giả định A"]


def test_ca2_khong_co_ke_hoach():
    # Ca 2a: ctx là None
    res1 = thuc_thi_plan_get(None)
    assert res1["co_ke_hoach"] is False
    assert "thong_bao" in res1
    assert "buoc" not in res1

    # Ca 2b: store không có plan:current
    ctx_empty = MockContext(MockStore(None))
    res2 = thuc_thi_plan_get(ctx_empty)
    assert res2["co_ke_hoach"] is False
    assert "thong_bao" in res2
    assert "buoc" not in res2


def test_ca3_dang_ky_tool():
    class DummyRegistry:
        def __init__(self):
            self.tools = {}

        def tool(self, name, group, doc, schema, risk="R1", core=False, keywords=None):
            def decorator(fn):
                self.tools[name] = {
                    "fn": fn,
                    "group": group,
                    "doc": doc,
                    "schema": schema,
                    "risk": risk
                }
                return fn
            return decorator

    r = DummyRegistry()
    dang_ky(r)
    assert "plan.get" in r.tools
    assert r.tools["plan.get"]["group"] == "Điều phối"
    fn = r.tools["plan.get"]["fn"]

    # Gọi với context rỗng
    result = fn(None)
    assert isinstance(result, dict)
    assert result["co_ke_hoach"] is False
