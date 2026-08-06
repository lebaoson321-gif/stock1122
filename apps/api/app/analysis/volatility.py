"""
Phân tích biến động: biên độ dao động trong ngày trung bình (high-low so
với close) qua 20 phiên gần nhất — dùng làm proxy độ "ổn định" giá.

Quy ước điểm: 10 = ổn định (biến động thấp), 0 = biến động mạnh/rủi ro
cao. Biên độ trung bình <=0% -> 10 điểm, >=5% -> 0 điểm, tuyến tính ở
giữa (5%/ngày là mức dao động khá lớn với cổ phiếu HOSE thông thường).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price import PriceHistory

_WINDOW = 20
_MAX_RANGE_PCT = 5.0  # biên độ (%) tương ứng điểm 0


def compute_volatility_score(db: Session, stock_id: int) -> float | None:
    rows = db.execute(
        select(PriceHistory.high, PriceHistory.low, PriceHistory.close)
        .where(PriceHistory.stock_id == stock_id)
        .order_by(PriceHistory.trade_date.desc())
        .limit(_WINDOW)
    ).all()

    if len(rows) < 5:
        return None

    ranges_pct = [
        float(high - low) / float(close) * 100
        for high, low, close in rows
        if close and close > 0
    ]
    if not ranges_pct:
        return None

    avg_range_pct = sum(ranges_pct) / len(ranges_pct)
    score = 10 - min(avg_range_pct / _MAX_RANGE_PCT, 1.0) * 10
    return round(max(0.0, score), 2)
