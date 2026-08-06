"""
Contract test cho VnstockAdapter — gọi vnstock THẬT, cần mạng.
KHÔNG chạy trong CI mặc định (đánh dấu @pytest.mark.integration), chạy
tay để xác nhận vnstock chưa đổi schema response theo cách phá vỡ
adapter (đây chính là loại lỗi đã gặp thật với source="TCBS" — biến nó
từ 502 production thành test fail bắt được sớm).

Chạy: pytest tests/ -m integration
"""
import pytest

from app.collectors.vnstock_adapter import VnstockAdapter

pytestmark = pytest.mark.integration


@pytest.fixture
def adapter():
    return VnstockAdapter()


def test_get_price_history_shape(adapter):
    bars = adapter.get_price_history("FPT", years=1)
    assert len(bars) > 0
    bar = bars[0]
    assert bar.trade_date is not None
    assert bar.high >= bar.low
    assert bar.open > 0 and bar.close > 0
    assert bar.volume >= 0


def test_get_company_info_shape(adapter):
    info = adapter.get_company_info("FPT")
    assert info.symbol == "FPT"
    assert info.company_name  # không rỗng


def test_get_price_board_shape(adapter):
    quotes = adapter.get_price_board(["FPT", "VNM"])
    assert len(quotes) > 0
    for q in quotes:
        assert q.symbol in ("FPT", "VNM")
        assert q.captured_at is not None
