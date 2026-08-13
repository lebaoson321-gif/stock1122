from datetime import date as date_type
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StockSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    company_name: str
    sector: str


class HoseSymbol(BaseModel):
    symbol: str
    company_name: str


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
    # Giá dùng để hiển thị và giao dịch — cùng nguồn với danh mục ảo
    # (services/pricing.py). Khác `close` khi đang có giá khớp trong phiên.
    current_price: float
    price_source: str
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


class PollResult(BaseModel):
    symbols_requested: int
    rows_synced: int
    failed_batches: int
    message: str


class ScoreResponse(BaseModel):
    symbol: str
    available: bool = True
    date: date_type
    trend_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    volatility_score: Optional[float] = None
    total_score: Optional[float] = None


class ScorePlaceholder(BaseModel):
    """Mã đã có dữ liệu giá nhưng chưa từng được chấm điểm (VD: sync lần
    cuối trước khi tính năng này ra mắt) — gọi lại POST /sync để tính
    điểm, hoặc đợi lần sync định kỳ tiếp theo."""

    symbol: str
    available: bool = False
    message: str = "Chưa có điểm chấm cho mã này — gọi POST /sync để tính lại."


class PredictionResponse(BaseModel):
    symbol: str
    available: bool = True
    date: date_type
    model_name: str
    model_version: str
    prob_up: Optional[float] = None
    predicted_label: Optional[str] = None  # "up" | "down"


class PredictionPlaceholder(BaseModel):
    """Chưa có dự đoán cho mã này — services/ai/predict.py chưa chạy
    cho mã này (chạy thủ công hoặc theo lịch, xem services/ai/README.md)."""

    symbol: str
    available: bool = False
    message: str = "Chưa có dự đoán AI cho mã này."
