from datetime import date as dt_date
from datetime import datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RealtimeQuote(Base):
    """
    Tick giá khớp lệnh realtime (price board). Chỉ giữ dữ liệu gần đây —
    dọn dữ liệu >retention_days bằng Supabase pg_cron (xem
    supabase/sql/retention.sql), KHÔNG lưu vô hạn.
    """

    __tablename__ = "realtime_quotes"
    __table_args__ = (
        UniqueConstraint("stock_id", "captured_at", name="uq_realtime_quotes_stock_time"),
        Index("ix_realtime_quotes_stock_captured_desc", "stock_id", text("captured_at DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    match_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    match_volume: Mapped[int | None] = mapped_column(BigInteger)
    ref_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    ceiling_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    floor_price: Mapped[float | None] = mapped_column(Numeric(18, 4))

    # OHLC + KL luỹ kế của phiên hôm nay, do bảng giá trả sẵn. Dùng để vẽ
    # cây nến đang chạy (xem services/pricing.py::get_intraday_candle) —
    # price_history chỉ có dòng hôm nay sau khi job sync chạy cuối ngày.
    open_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    high_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    low_price: Mapped[float | None] = mapped_column(Numeric(18, 4))
    accumulated_volume: Mapped[int | None] = mapped_column(BigInteger)
    # Ngày giao dịch provider khai báo, đáng tin hơn captured_at khi job
    # poll chạy trễ qua nửa đêm.
    trading_date: Mapped[dt_date | None] = mapped_column(Date, index=True)
    # Toàn bộ row gốc từ provider (đã flatten) — phòng khi cần field chưa
    # có cột riêng, và để debug khi provider đổi schema (xem collectors/).
    raw: Mapped[dict | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
