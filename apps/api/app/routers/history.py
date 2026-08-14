from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.indicator import TechnicalIndicator
from app.models.price import PriceHistory
from app.routers.common import get_stock_or_404
from app.schemas.stock import PricePoint
from app.services.pricing import get_intraday_candle

router = APIRouter(prefix="/api/stocks", tags=["history"])


@router.get("/{symbol}/history", response_model=list[PricePoint])
def get_history(symbol: str, db: Session = Depends(get_db)):
    """Toàn bộ lịch sử giá + chỉ báo kỹ thuật, dùng để vẽ chart."""
    stock = get_stock_or_404(db, symbol)

    rows = db.execute(
        select(PriceHistory, TechnicalIndicator)
        .outerjoin(
            TechnicalIndicator,
            (TechnicalIndicator.stock_id == PriceHistory.stock_id)
            & (TechnicalIndicator.trade_date == PriceHistory.trade_date),
        )
        .where(PriceHistory.stock_id == stock.id)
        .order_by(PriceHistory.trade_date)
    ).all()

    points = []
    for price, indicator in rows:
        points.append(
            PricePoint(
                date=price.trade_date,
                open=float(price.open), high=float(price.high), low=float(price.low),
                close=float(price.close), volume=price.volume,
                ma20=_f(indicator, "ma20"), ma50=_f(indicator, "ma50"), ma200=_f(indicator, "ma200"),
                ema12=_f(indicator, "ema12"), ema26=_f(indicator, "ema26"), rsi14=_f(indicator, "rsi14"),
                macd=_f(indicator, "macd"), macd_signal=_f(indicator, "macd_signal"),
                macd_hist=_f(indicator, "macd_hist"), bb_upper=_f(indicator, "bb_upper"),
                bb_middle=_f(indicator, "bb_middle"), bb_lower=_f(indicator, "bb_lower"),
            )
        )

    # Cây nến của phiên đang chạy. price_history chỉ có dòng hôm nay sau
    # khi job đồng bộ chạy cuối ngày, nên trong phiên biểu đồ sẽ thiếu
    # đúng cây nến người dùng quan tâm nhất.
    # Không kèm chỉ báo kỹ thuật: MA/RSI/MACD tính trên chuỗi phiên ĐÃ
    # ĐÓNG, thêm điểm cho phiên chưa chốt sẽ làm đường chỉ báo nhảy loạn
    # rồi lại đổi khi phiên đóng thật.
    candle = get_intraday_candle(db, stock.id)
    if candle is not None:
        points.append(
            PricePoint(
                date=candle.trade_date,
                open=float(candle.open), high=float(candle.high),
                low=float(candle.low), close=float(candle.close),
                volume=candle.volume,
                is_intraday=True,
            )
        )

    return points


def _f(indicator, attr: str) -> float | None:
    if indicator is None:
        return None
    value = getattr(indicator, attr)
    return float(value) if value is not None else None
