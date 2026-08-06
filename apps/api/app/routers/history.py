from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.indicator import TechnicalIndicator
from app.models.price import PriceHistory
from app.routers.common import get_stock_or_404
from app.schemas.stock import PricePoint

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
    return points


def _f(indicator, attr: str) -> float | None:
    if indicator is None:
        return None
    value = getattr(indicator, attr)
    return float(value) if value is not None else None
