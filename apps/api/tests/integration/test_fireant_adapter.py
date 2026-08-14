"""
Contract test cho FireAntAdapter — gọi restv2.fireant.vn THẬT, cần mạng
VÀ biến môi trường FIREANT_TOKEN (token của tài khoản fireant.vn đã đăng
nhập — xem apps/api/.env.example). KHÔNG chạy trong CI mặc định (đánh dấu
@pytest.mark.integration), chạy tay để xác nhận FireAnt chưa đổi schema
response theo cách phá vỡ adapter — cùng lý do với test_vnstock_adapter.py.

Chạy: FIREANT_TOKEN=... pytest tests/ -m integration
"""
import os

import pytest

from app.collectors.fireant_adapter import FireAntAdapter

pytestmark = pytest.mark.integration

_TOKEN = os.environ.get("FIREANT_TOKEN", "")


@pytest.fixture
def adapter():
    if not _TOKEN:
        pytest.skip("Cần biến môi trường FIREANT_TOKEN để chạy test này")
    return FireAntAdapter(token=_TOKEN)


@pytest.mark.parametrize("symbol", ["DHC", "VCB", "HPG"])
def test_get_company_fundamentals_shape(adapter, symbol):
    data = adapter.get_company_fundamentals(symbol)

    assert data.symbol == symbol
    assert data.pe is not None and data.pe > 0
    assert data.eps is not None and data.eps > 0
    assert data.market_cap is not None and data.market_cap > 0
    assert data.issue_share is not None and data.issue_share > 0
    # ROE/ROA của doanh nghiệp niêm yết bình thường không âm và không
    # vượt ngưỡng vô lý (xem services/fundamentals_math.MAX_PLAUSIBLE_PERCENT).
    assert data.roe is None or 0 <= data.roe <= 200
    assert data.roa is None or 0 <= data.roa <= 200
    assert data.raw["_source"] == "fireant"
