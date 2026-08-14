"""
Giá đóng cửa/OHLCV theo ngày của các chỉ số thị trường (VN-Index, HNX,
UPCoM, VN30) — dữ liệu công khai, không thuộc về một user cụ thể nên
không cần RLS (khác với portfolios/watchlists).
"""
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MarketIndex(Base):
    __tablename__ = "market_indices"
    __table_args__ = (
        UniqueConstraint("code", "trade_date", name="uq_market_indices_code_date"),
        Index("ix_market_indices_code_date_desc", "code", text("trade_date DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
