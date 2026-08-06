"""
PHASE 2 — chưa triển khai. Phân tích thanh khoản: khối lượng giao dịch
trung bình gần đây so với lịch sử dài hạn, tần suất phiên có khối lượng
bất thường. Dữ liệu nguồn: price_history.volume.
"""
from sqlalchemy.orm import Session


def compute_liquidity_score(db: Session, stock_id: int) -> float:
    raise NotImplementedError("Xem app/analysis/liquidity.py — Analysis Engine PHASE 2")
