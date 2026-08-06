"""
PHASE 2 — chưa triển khai. Phân tích xu hướng thị trường cho 1 mã, dựa
trên technical_indicators đã có (ma20/ma50/ma200, macd) — không cần dữ
liệu mới, chỉ cần tổng hợp/chấm điểm từ dữ liệu đã tính sẵn.

Gợi ý: kết hợp MA20 vs MA50 vs MA200 (nhiều khung thời gian nhất quán
= tin cậy hơn 1 khung), độ dốc MA gần đây, và trạng thái MACD, thành 1
điểm 0-10 (trend_score trong bảng stock_scores).
"""
from sqlalchemy.orm import Session


def compute_trend_score(db: Session, stock_id: int) -> float:
    raise NotImplementedError("Xem app/analysis/trend.py — Analysis Engine PHASE 2")
