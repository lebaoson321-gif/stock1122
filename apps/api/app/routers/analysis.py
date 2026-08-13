from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.indicator import TechnicalIndicator
from app.models.price import PriceHistory
from app.models.score import StockScore
from app.routers.common import get_stock_or_404
from app.schemas.stock import AnalysisResponse, ScorePlaceholder, ScoreResponse
from app.services.market_session import VN_TZ
from app.services.pricing import get_current_price

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

    # Giá hiển thị phải đi qua CÙNG một nguồn với danh mục và với khớp
    # lệnh ảo (services/pricing.py). Trước đây trang mã đọc thẳng
    # price_history nên cùng một mã hiện 34,90 ở đây mà 35,4 ở danh mục.
    current = get_current_price(db, stock.id)
    current_price = float(current.price) if current else close
    price_source = current.source if current else "close"

    # Mốc tham chiếu để tính % thay đổi là giá đóng cửa của phiên GẦN NHẤT
    # ĐÃ ĐÓNG. Nếu dòng giá mới nhất chính là hôm nay (đã sync trong ngày)
    # thì phiên đã đóng gần nhất là dòng liền trước; nếu chưa sync hôm nay
    # mà đang có giá khớp trong phiên thì chính dòng mới nhất là mốc.
    today_vn = datetime.now(VN_TZ).date()
    if price_source == "realtime" and latest_price.trade_date != today_vn:
        reference_close = close
    else:
        reference_close = float(prev_price.close)

    change_pct = (
        ((current_price - reference_close) / reference_close) * 100 if reference_close else 0.0
    )

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
        symbol=symbol, date=latest_price.trade_date, close=close,
        current_price=current_price, price_source=price_source,
        change_pct=round(change_pct, 2),
        ma20=ma20, ma50=ma50, trend=trend, rsi14=rsi, rsi_status=rsi_status,
        macd=macd, macd_signal_value=macd_signal, macd_signal_status=macd_status,
    )


@router.get("/{symbol}/score", response_model=ScoreResponse | ScorePlaceholder)
def get_score(symbol: str, db: Session = Depends(get_db)):
    """Điểm chấm cổ phiếu (Analysis Engine): xu hướng/thanh khoản/biến
    động, tính lại mỗi lần sync (xem app/analysis/scoring.py). Trả
    placeholder (available=False) thay vì 404 nếu mã tồn tại nhưng chưa
    từng được chấm điểm — để frontend phân biệt "chưa tính" với "lỗi"."""
    stock = get_stock_or_404(db, symbol)
    score = db.execute(
        select(StockScore)
        .where(StockScore.stock_id == stock.id)
        .order_by(StockScore.score_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    if score is None:
        return ScorePlaceholder(symbol=stock.symbol)

    return ScoreResponse(
        symbol=stock.symbol, date=score.score_date,
        trend_score=float(score.trend_score) if score.trend_score is not None else None,
        liquidity_score=float(score.liquidity_score) if score.liquidity_score is not None else None,
        volatility_score=float(score.volatility_score) if score.volatility_score is not None else None,
        total_score=float(score.total_score) if score.total_score is not None else None,
    )
