"""
Phân tích thanh khoản: so sánh khối lượng giao dịch trung bình gần đây
(20 phiên) với giai đoạn trước đó (20 phiên kế trước) — thanh khoản đang
tăng lên thì điểm cao, đang giảm thì điểm thấp. Đây là điểm "động lượng
thanh khoản" tương đối của chính mã đó theo thời gian, không so sánh
tuyệt đối giữa các mã (khối lượng "thấp" của mã vốn hoá lớn có thể vẫn
cao hơn khối lượng "cao" của mã vốn hoá nhỏ, nên so sánh tuyệt đối giữa
các mã không có ý nghĩa nếu không chuẩn hoá theo free-float).

Thang điểm 0-10: 5 = trung tính (thanh khoản không đổi).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.price import PriceHistory

_RECENT_WINDOW = 20
_PRIOR_WINDOW = 20


def compute_liquidity_score(db: Session, stock_id: int) -> float | None:
    rows = db.execute(
        select(PriceHistory.volume)
        .where(PriceHistory.stock_id == stock_id)
        .order_by(PriceHistory.trade_date.desc())
        .limit(_RECENT_WINDOW + _PRIOR_WINDOW)
    ).scalars().all()

    if len(rows) < 10:
        return None

    recent = rows[:_RECENT_WINDOW]
    prior = rows[_RECENT_WINDOW:] or recent

    avg_recent = sum(recent) / len(recent)
    avg_prior = sum(prior) / len(prior)

    if avg_prior == 0:
        return 5.0

    ratio = avg_recent / avg_prior  # 1.0 = không đổi
    # Đổi (ratio - 1) thành điểm lệch khỏi 5, giới hạn ±5 (ratio >=2x hoặc <=0x)
    score = 5 + max(-5.0, min(5.0, (ratio - 1) * 5))
    return round(score, 2)
