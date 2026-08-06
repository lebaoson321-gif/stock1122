"""
Phân tích xu hướng thị trường cho 1 mã, dựa trên technical_indicators đã
có sẵn (ma20/ma50/ma200, macd) — không cần dữ liệu mới, chỉ tổng hợp/
chấm điểm từ dữ liệu đã tính sẵn.

Thang điểm 0-10: 5 = trung tính, >5 = xu hướng tăng, <5 = xu hướng giảm.
Kết hợp 3 tín hiệu (nếu có đủ dữ liệu): MA20 vs MA50, MA50 vs MA200,
MACD vs Signal — mỗi tín hiệu đóng góp bằng nhau, nhiều khung thời gian
đồng thuận thì điểm càng lệch về 0 hoặc 10.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.indicator import TechnicalIndicator


def compute_trend_score(db: Session, stock_id: int) -> float | None:
    latest = db.execute(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.stock_id == stock_id)
        .order_by(TechnicalIndicator.trade_date.desc())
        .limit(1)
    ).scalar_one_or_none()

    if latest is None:
        return None

    signals = []
    if latest.ma20 is not None and latest.ma50 is not None:
        signals.append(1 if latest.ma20 > latest.ma50 else -1)
    if latest.ma50 is not None and latest.ma200 is not None:
        signals.append(1 if latest.ma50 > latest.ma200 else -1)
    if latest.macd is not None and latest.macd_signal is not None:
        signals.append(1 if latest.macd > latest.macd_signal else -1)

    if not signals:
        return 5.0

    avg = sum(signals) / len(signals)  # -1..1
    return round(max(0.0, min(10.0, 5 + avg * 5)), 2)
