from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DataSyncLog(Base):
    """
    Ghi lại mỗi lần chạy job thu thập dữ liệu (scheduler hoặc sync thủ
    công qua API). Đây là tín hiệu DUY NHẤT để biết scheduler có "chết
    âm thầm" hay không — mọi job PHẢI ghi 1 dòng ở đây dù thành công
    hay thất bại (xem app/scheduler.py).
    """

    __tablename__ = "data_sync_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int | None] = mapped_column(ForeignKey("stocks.id", ondelete="SET NULL"), index=True)
    sync_type: Mapped[str] = mapped_column(String(32), nullable=False)  # historical | realtime
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # success | provider_error | no_data
    rows_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
