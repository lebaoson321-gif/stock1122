"""
PHASE 2 — chưa triển khai. Phân tích biến động: độ rộng Bollinger Band
(bb_upper - bb_lower, đã có trong technical_indicators), biên độ dao
động trong ngày (high-low) so với lịch sử.
"""
from sqlalchemy.orm import Session


def compute_volatility_score(db: Session, stock_id: int) -> float:
    raise NotImplementedError("Xem app/analysis/volatility.py — Analysis Engine PHASE 2")
