from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.indicator import TechnicalIndicator
from app.models.price import PriceHistory
from app.routers.common import get_stock_or_404
from app.schemas.stock import AnalysisResponse, ScorePlaceholder

router = APIRouter(prefix="/api/stocks", tags=["analysis"])


@router.get("/{symbol}/analysis", response_model=AnalysisResponse)
def get_analysis(symbol: str, db: Session = Depends(get_db)):
    """Trạng thái phân tích kỹ thuật mới nhất — dùng cho card tổng quan."""
    stock = get_stock_or_404(db, symbol)
    symbol = stock.symbol

    rows = db.execute(
        select(PriceHistory, TechnicalIndicator)
        .outerjoin(
            TechnicalIndicator,
            (TechnicalIndicator.stock_id == PriceHistory.stock_id)
            & (TechnicalIndicator.trade_date == PriceHistory.trade_date),
        )
        .where(PriceHistory.stock_id == stock.id)
        .order_by(PriceHistory.trade_date.desc())
        .limit(2)
    ).all()

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chưa có dữ liệu giá cho mã {symbol}")

    latest_price, latest_ind = rows[0]
    prev_price = rows[1][0] if len(rows) > 1 else latest_price

    close = float(latest_price.close)
    prev_close = float(prev_price.close)
    change_pct = ((close - prev_close) / prev_close) * 100 if prev_close else 0.0

    ma20 = float(latest_ind.ma20) if latest_ind and latest_ind.ma20 is not None else None
    ma50 = float(latest_ind.ma50) if latest_ind and latest_ind.ma50 is not None else None
    trend = "bullish" if (ma20 or 0) > (ma50 or 0) else "bearish"

    rsi = float(latest_ind.rsi14) if latest_ind and latest_ind.rsi14 is not None else None
    if rsi is None:
        rsi_status = "neutral"
    elif rsi > 70:
        rsi_status = "overbought"
    elif rsi < 30:
        rsi_status = "oversold"
    else:
        rsi_status = "neutral"

    macd = float(latest_ind.macd) if latest_ind and latest_ind.macd is not None else None
    macd_signal = float(latest_ind.macd_signal) if latest_ind and latest_ind.macd_signal is not None else None
    macd_status = "buy" if (macd or 0) > (macd_signal or 0) else "sell"

    return AnalysisResponse(
        symbol=symbol, date=latest_price.trade_date, close=close, change_pct=round(change_pct, 2),
        ma20=ma20, ma50=ma50, trend=trend, rsi14=rsi, rsi_status=rsi_status,
        macd=macd, macd_signal_value=macd_signal, macd_signal_status=macd_status,
    )


@router.get("/{symbol}/score", response_model=ScorePlaceholder)
def get_score(symbol: str, db: Session = Depends(get_db)):
    """Analysis Engine (trend/liquidity/volatility scoring) — PHASE 2,
    chưa triển khai. Trả placeholder thay vì 404 để frontend phân biệt
    được "chưa có module" với "mã không tồn tại"."""
    stock = get_stock_or_404(db, symbol)
    return ScorePlaceholder(symbol=stock.symbol)
