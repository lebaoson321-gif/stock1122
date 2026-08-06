"""Tổng hợp trend/liquidity/volatility score thành total_score, upsert
vào bảng stock_scores — cùng pattern với
app/processing/indicators.py::recompute_indicators()."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.analysis.liquidity import compute_liquidity_score
from app.analysis.trend import compute_trend_score
from app.analysis.volatility import compute_volatility_score
from app.models.price import PriceHistory
from app.models.score import StockScore


def recompute_score(db: Session, stock_id: int) -> StockScore | None:
    latest_date = db.execute(
        select(PriceHistory.trade_date)
        .where(PriceHistory.stock_id == stock_id)
        .order_by(PriceHistory.trade_date.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_date is None:
        return None

    trend = compute_trend_score(db, stock_id)
    liquidity = compute_liquidity_score(db, stock_id)
    volatility = compute_volatility_score(db, stock_id)

    parts = [p for p in (trend, liquidity, volatility) if p is not None]
    total = round(sum(parts) / len(parts), 2) if parts else None

    stmt = (
        insert(StockScore)
        .values(
            stock_id=stock_id, score_date=latest_date,
            trend_score=trend, liquidity_score=liquidity,
            volatility_score=volatility, total_score=total,
        )
        .on_conflict_do_update(
            index_elements=["stock_id", "score_date"],
            set_={
                "trend_score": trend, "liquidity_score": liquidity,
                "volatility_score": volatility, "total_score": total,
            },
        )
        .returning(StockScore)
    )
    score = db.execute(stmt).scalar_one()
    db.commit()
    return score
