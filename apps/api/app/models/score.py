from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StockScore(Base):
    """
    Điểm chấm cổ phiếu từ Analysis Engine (trend/liquidity/volatility).

    PHASE 2 — bảng tồn tại để schema sẵn sàng, nhưng chưa có job nào ghi
    dữ liệu vào đây. Xem app/analysis/ cho các hàm stub liên quan.
    """

    __tablename__ = "stock_scores"
    __table_args__ = (UniqueConstraint("stock_id", "score_date", name="uq_stock_scores_stock_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    score_date: Mapped[date] = mapped_column(Date, nullable=False)

    trend_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    liquidity_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    volatility_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    total_score: Mapped[float | None] = mapped_column(Numeric(5, 2))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
