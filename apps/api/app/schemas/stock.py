from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    company_name: str
    sector: str


class PricePoint(BaseModel):
    date: date_type
    open: float
    high: float
    low: float
    close: float
    volume: int
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    ma200: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None


class AnalysisResponse(BaseModel):
    symbol: str
    date: date_type
    close: float
    change_pct: float
    ma20: Optional[float] = None
    ma50: Optional[float] = None
    trend: str  # "bullish" | "bearish"
    rsi14: Optional[float] = None
    rsi_status: str  # "overbought" | "oversold" | "neutral"
    macd: Optional[float] = None
    macd_signal_value: Optional[float] = None
    macd_signal_status: str  # "buy" | "sell"


class SyncResult(BaseModel):
    symbol: str
    rows_synced: int
    message: str


class ScorePlaceholder(BaseModel):
    """Analysis Engine chưa triển khai — endpoint trả placeholder này
    thay vì 404, để frontend phân biệt được "chưa có module" với "lỗi"."""

    symbol: str
    available: bool = False
    message: str = "Analysis Engine chưa được triển khai (phase 2)."


class PredictionPlaceholder(BaseModel):
    """AI Module chưa triển khai — xem services/ai/."""

    symbol: str
    available: bool = False
    message: str = "AI Module chưa được triển khai (phase 2)."
