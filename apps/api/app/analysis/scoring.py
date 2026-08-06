"""
PHASE 2 — chưa triển khai. Tổng hợp trend/liquidity/volatility score
thành total_score, ghi vào bảng stock_scores (model đã có sẵn ở
app/models/score.py, chỉ chưa có job nào ghi dữ liệu).

Khi implement xong 3 hàm compute_*_score ở trend.py/liquidity.py/
volatility.py, hàm dưới đây chỉ cần gọi cả 3, tổng hợp, upsert — tương
tự cách app/processing/indicators.py::recompute_indicators() đã làm
cho technical_indicators.
"""
from sqlalchemy.orm import Session


def recompute_score(db: Session, stock_id: int) -> None:
    raise NotImplementedError("Xem app/analysis/scoring.py — Analysis Engine PHASE 2")
