from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PriceHistory(Base):
    """Giá OHLCV theo ngày (daily bar) — dữ liệu lịch sử đã sync."""

    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_price_history_stock_date"),
        # Tối ưu truy vấn "N ngày gần nhất của 1 mã" (dùng cho /history, chart).
        Index("ix_price_history_stock_date_desc", "stock_id", text("trade_date DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
