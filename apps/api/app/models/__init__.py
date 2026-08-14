from app.models import _auth_shadow  # noqa: F401  đăng ký shadow table auth.users
from app.models.indicator import TechnicalIndicator
from app.models.prediction import AIPrediction
from app.models.fundamentals import CompanyFundamentals
from app.models.market_index import MarketIndex
from app.models.portfolio import Portfolio, PortfolioPosition, PortfolioTransaction
from app.models.price import PriceHistory
from app.models.realtime import RealtimeQuote
from app.models.score import StockScore
from app.models.stock import Stock
from app.models.sync_log import DataSyncLog
from app.models.watchlist import Watchlist, WatchlistItem

__all__ = [
    "Stock",
    "PriceHistory",
    "TechnicalIndicator",
    "RealtimeQuote",
    "DataSyncLog",
    "StockScore",
    "AIPrediction",
    "Watchlist",
    "WatchlistItem",
    "Portfolio",
    "PortfolioPosition",
    "PortfolioTransaction",
    "CompanyFundamentals",
    "MarketIndex",
]
