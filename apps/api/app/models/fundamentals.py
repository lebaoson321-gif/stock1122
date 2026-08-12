"""
Cache chỉ số cơ bản của doanh nghiệp.

Vì sao cache trong DB thay vì gọi vnstock mỗi lần xem trang: một lần gọi
mất vài giây, và gọi dồn dập dễ bị VCI chặn IP (đã gặp thật khi đồng bộ
hàng loạt). Chỉ số cơ bản cũng chỉ đổi theo quý, không cần tươi từng phút
như giá.

Nạp theo kiểu lazy: endpoint đọc cache, thấy thiếu hoặc quá cũ thì mới
gọi provider rồi ghi lại — không cần thêm job nền riêng.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CompanyFundamentals(Base):
    __tablename__ = "company_fundamentals"
    __table_args__ = (UniqueConstraint("stock_id", name="uq_company_fundamentals_stock"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Tất cả nullable: provider không chính thức, mã mới niêm yết chưa có
    # P/E, ngân hàng không dùng cùng bộ chỉ số với doanh nghiệp sản xuất.
    market_cap: Mapped[float | None] = mapped_column(Numeric(24, 2))
    pe: Mapped[float | None] = mapped_column(Numeric(14, 4))
    pb: Mapped[float | None] = mapped_column(Numeric(14, 4))
    eps: Mapped[float | None] = mapped_column(Numeric(18, 4))
    roe: Mapped[float | None] = mapped_column(Numeric(14, 4))
    roa: Mapped[float | None] = mapped_column(Numeric(14, 4))
    dividend_yield: Mapped[float | None] = mapped_column(Numeric(14, 4))
    issue_share: Mapped[float | None] = mapped_column(Numeric(24, 2))
    charter_capital: Mapped[float | None] = mapped_column(Numeric(24, 2))
    company_profile: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(255))

    # Dữ liệu thô từ provider — để chẩn đoán khi tên trường đổi và cột
    # bên trên bỗng toàn NULL (xem collectors/vnstock_adapter.py).
    raw: Mapped[dict | None] = mapped_column(JSONB)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
