# -*- coding: utf-8 -*-
"""Ràng buộc mô hình — quyết định của chủ sản phẩm 25/09/2026: chỉ `gemini-3.8-flash`.

Một quyết định như thế này rất dễ rò: ai đó thêm một subagent, tiện tay đặt một model
"nhanh hơn" cho nó, và sáu tháng sau không ai biết hệ thống đang chạy bằng gì. Vì vậy
nó được canh bằng MÃ ở đúng điểm gọi cuối cùng, không phải bằng một dòng ghi chú.
"""

import os

import pytest

from eide.config import ALLOWED_MODELS, Config, ModelConfig, load_dotenv


def test_ba_vai_tro_deu_dung_mot_mo_hinh():
    m = ModelConfig()
    assert m.main == m.subagent == m.summarize == "gemini-3.8-flash"


def test_danh_sach_cho_phep_chi_co_mot():
    assert ALLOWED_MODELS == frozenset({"gemini-3.8-flash"})


@pytest.mark.parametrize("ten", ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-3.5-flash",
                                "gemini-flash-latest", "gpt-4o", ""])
def test_mo_hinh_khac_bi_tu_choi(ten):
    with pytest.raises(ValueError) as e:
        ModelConfig.assert_allowed(ten)
    assert "gemini-3.8-flash" in str(e.value)


def test_bien_moi_truong_cung_bi_canh(monkeypatch):
    """Đặt EIDE_MODEL_MAIN thành model khác phải nổ ngay khi khởi động, không âm thầm chạy."""
    monkeypatch.setenv("EIDE_MODEL_MAIN", "gemini-2.5-pro")
    with pytest.raises(ValueError):
        ModelConfig()


def test_chan_o_diem_goi_cuoi_cung(monkeypatch, tmp_path):
    """Truyền thẳng `model=` vào gateway vẫn bị chặn — không có cửa sau."""
    load_dotenv()
    if not ModelConfig().api_key:
        pytest.skip("chưa cấu hình GEMINI_API_KEY")
    from eide.llm.gemini import GeminiGateway
    gw = GeminiGateway(ModelConfig())
    with pytest.raises(ValueError):
        gw.stream(system="x", messages=[{"role": "user", "text": "y"}], tools=[],
                  model="gemini-2.5-pro")


def test_config_mac_dinh_dung_mo_hinh_cho_phep(tmp_path):
    cfg = Config.for_project(tmp_path / "du-an")
    ModelConfig.assert_allowed(cfg.model.main)
