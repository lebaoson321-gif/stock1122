"""
Schemas (Pydantic) định nghĩa cấu trúc dữ liệu trả về qua API.
Giữ đồng bộ với dữ liệu FE đang mock, để khi nối thật không lệch field.
"""
from datetime import date as date_type
from typing import Optional
from pydantic import BaseModel


class StockSummary(BaseModel):
    symbol: str
    company_name: str
    sector: str
    last_updated: Optional[str] = None


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
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None


class AnalysisResponse(BaseModel):
    symbol: str
    date: date_type
    close: float
    change_pct: float
    ma20: Optional[float]
    ma50: Optional[float]
    trend: str            # "bullish" | "bearish"
    rsi: Optional[float]
    rsi_status: str        # "overbought" | "oversold" | "neutral"
    macd: Optional[float]
    macd_signal_value: Optional[float]
    macd_signal_status: str  # "buy" | "sell"


class SyncResult(BaseModel):
    symbol: str
    rows_synced: int
    message: str
