"""
Chọn MarketDataProvider theo config, để đổi/thêm provider chỉ là thêm
1 adapter mới + đổi biến môi trường, không phải sửa router/scheduler.
"""
from functools import lru_cache

from app.collectors.base import MarketDataProvider
from app.collectors.vnstock_adapter import VnstockAdapter
from app.config import get_settings


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider == "vnstock":
        return VnstockAdapter()
    raise ValueError(f"Không hỗ trợ MARKET_DATA_PROVIDER={settings.market_data_provider!r}")
