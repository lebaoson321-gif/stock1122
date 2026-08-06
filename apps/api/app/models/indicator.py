from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TechnicalIndicator(Base):
    """
    Bảng cache chỉ báo kỹ thuật — tính lại TOÀN BỘ chuỗi mỗi khi
    price_history của một mã có dữ liệu mới (xem
    app/processing/indicators.py::recompute_indicators), không patch
    tăng dần, để tránh drift (MA200 cần 200 dòng trước đó mới đúng).
    """

    __tablename__ = "technical_indicators"
    __table_args__ = (
        UniqueConstraint("stock_id", "trade_date", name="uq_technical_indicators_stock_date"),
        Index("ix_technical_indicators_stock_date_desc", "stock_id", text("trade_date DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    ma20: Mapped[float | None] = mapped_column(Numeric(18, 4))
    ma50: Mapped[float | None] = mapped_column(Numeric(18, 4))
    ma200: Mapped[float | None] = mapped_column(Numeric(18, 4))
    ema12: Mapped[float | None] = mapped_column(Numeric(18, 4))
    ema26: Mapped[float | None] = mapped_column(Numeric(18, 4))
    rsi14: Mapped[float | None] = mapped_column(Numeric(18, 4))
    macd: Mapped[float | None] = mapped_column(Numeric(18, 4))
    macd_signal: Mapped[float | None] = mapped_column(Numeric(18, 4))
    macd_hist: Mapped[float | None] = mapped_column(Numeric(18, 4))
    bb_upper: Mapped[float | None] = mapped_column(Numeric(18, 4))
    bb_middle: Mapped[float | None] = mapped_column(Numeric(18, 4))
    bb_lower: Mapped[float | None] = mapped_column(Numeric(18, 4))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
