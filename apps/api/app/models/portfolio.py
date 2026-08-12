"""
Danh mục đầu tư ảo (paper trading) — tiền ảo, giá thật.

Ba bảng thay vì một: `portfolios` giữ tiền mặt, `portfolio_positions` giữ
số cổ phiếu đang nắm + giá vốn bình quân, `portfolio_transactions` giữ
lịch sử lệnh. Vị thế hoàn toàn có thể suy ra từ lịch sử lệnh, nhưng lưu
riêng để trang danh mục không phải cộng dồn lại toàn bộ lịch sử mỗi lần
mở, và để giá vốn bình quân là một con số được ghi rõ chứ không phải kết
quả tính lại (tránh sai lệch nếu sau này đổi công thức).
"""
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Tiền VND: Numeric(20, 2) — đủ cho hàng nghìn tỷ, vẫn giữ được số lẻ.
# KHÔNG dùng float cho tiền: sai số nhị phân sẽ tích luỹ qua từng lệnh
# mua/bán và làm số dư lệch dần.
_MONEY = Numeric(20, 2)
# Giá cổ phiếu lưu cùng kiểu với price_history.close để so sánh/tính toán
# không phải ép kiểu qua lại.
_PRICE = Numeric(18, 4)


class Portfolio(Base):
    __tablename__ = "portfolios"
    __table_args__ = (
        # Mỗi user đúng 1 danh mục — giữ mô hình đơn giản, nếu sau này cần
        # nhiều danh mục thì bỏ ràng buộc này và thêm cột `name`.
        UniqueConstraint("user_id", name="uq_portfolios_user"),
        CheckConstraint("cash_balance >= 0", name="ck_portfolios_cash_non_negative"),
        CheckConstraint("initial_capital > 0", name="ck_portfolios_capital_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Xem models/watchlist.py: bảng auth.users do Supabase quản lý, chỉ
    # tham chiếu bằng FK string, không map bằng SQLAlchemy model.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    initial_capital: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    cash_balance: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "stock_id", name="uq_portfolio_positions_portfolio_stock"),
        CheckConstraint("quantity > 0", name="ck_portfolio_positions_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(nullable=False)
    # Giá vốn bình quân gia quyền: mua thêm thì bình quân lại, bán thì giữ
    # nguyên (bán không làm đổi giá vốn phần còn lại).
    avg_cost: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"
    __table_args__ = (
        CheckConstraint("side IN ('buy', 'sell')", name="ck_portfolio_transactions_side"),
        CheckConstraint("quantity > 0", name="ck_portfolio_transactions_quantity_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[Decimal] = mapped_column(_PRICE, nullable=False)
    # quantity * price, lưu sẵn để lịch sử vẫn đúng kể cả khi sau này thêm
    # phí giao dịch (lúc đó amount != quantity * price).
    amount: Mapped[Decimal] = mapped_column(_MONEY, nullable=False)
    # "realtime" (khớp theo giá trong phiên) hay "close" (ngoài giờ, khớp
    # theo giá đóng cửa gần nhất) — để người dùng hiểu vì sao khớp ở giá đó.
    price_source: Mapped[str] = mapped_column(String(16), nullable=False, default="close")

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
