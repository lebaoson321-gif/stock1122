"""
Chọn MarketDataProvider theo config, để đổi/thêm provider chỉ là thêm
1 adapter mới + đổi biến môi trường, không phải sửa router/scheduler.
"""
import logging
from functools import lru_cache

from app.collectors.base import CompanyFundamentals, FundamentalsProvider, MarketDataProvider
from app.collectors.fireant_adapter import FireAntAdapter
from app.collectors.vnstock_adapter import VnstockAdapter
from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_market_data_provider() -> MarketDataProvider:
    settings = get_settings()
    if settings.market_data_provider == "vnstock":
        return VnstockAdapter()
    raise ValueError(f"Không hỗ trợ MARKET_DATA_PROVIDER={settings.market_data_provider!r}")


class _FundamentalsWithFallback:
    """Lùi về vnstock khi nguồn chính lỗi hoặc trả về rỗng — FireAnt là
    API không chính thức (không SLA), thà hiện số cũ/khác nguồn còn hơn
    hiện thẻ trắng chỉ vì FireAnt tạm gãy hoặc đổi schema."""

    def __init__(self, primary: FundamentalsProvider, fallback: FundamentalsProvider):
        self._primary = primary
        self._fallback = fallback

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals:
        try:
            data = self._primary.get_company_fundamentals(symbol)
        except Exception:  # noqa: BLE001 — provider không chính thức, lỗi là chuyện thường
            logger.warning("FireAnt fundamentals lỗi cho %s, lùi về vnstock", symbol, exc_info=True)
            return self._fallback.get_company_fundamentals(symbol)
        if data.pe is None and data.eps is None and data.market_cap is None:
            # 200 OK nhưng rỗng (mã không tồn tại trên FireAnt, hoặc API
            # đổi schema) — coi như lỗi, đừng cache một bản ghi toàn None.
            return self._fallback.get_company_fundamentals(symbol)
        return data


@lru_cache
def get_fundamentals_provider() -> FundamentalsProvider:
    """Nguồn chỉ số tài chính doanh nghiệp — RIÊNG với get_market_data_provider().
    Giá vẫn luôn qua vnstock; đây chỉ chọn nguồn cho P/E, EPS, ROE, ROA..."""
    settings = get_settings()
    if settings.fundamentals_provider == "vnstock":
        return get_market_data_provider()
    if settings.fundamentals_provider == "fireant":
        if not settings.fireant_token:
            logger.warning("FUNDAMENTALS_PROVIDER=fireant nhưng thiếu FIREANT_TOKEN, dùng vnstock")
            return get_market_data_provider()
        return _FundamentalsWithFallback(
            FireAntAdapter(settings.fireant_token), get_market_data_provider()
        )
    raise ValueError(f"Không hỗ trợ FUNDAMENTALS_PROVIDER={settings.fundamentals_provider!r}")
