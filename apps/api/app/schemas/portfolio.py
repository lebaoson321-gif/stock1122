from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioCreate(BaseModel):
    # Vốn ảo tính bằng ĐỒNG (không phải nghìn đồng) — khớp với cách người
    # dùng nhập "100000000" cho 100 triệu. Xem services/trading.py về quy
    # đổi sang đơn vị giá.
    initial_capital: Decimal = Field(gt=0, le=Decimal("1e15"))


class PositionOut(BaseModel):
    stock_id: int
    symbol: str
    company_name: str
    quantity: int
    avg_cost: Decimal  # nghìn VND/cp, cùng đơn vị giá hiển thị trên biểu đồ
    current_price: Decimal | None
    price_source: str | None
    market_value: Decimal | None  # VND
    cost_value: Decimal  # VND
    pnl: Decimal | None  # VND
    pnl_pct: float | None


class PortfolioOut(BaseModel):
    id: int
    initial_capital: Decimal
    cash_balance: Decimal
    positions: list[PositionOut] = []
    holdings_value: Decimal  # tổng giá trị thị trường số cổ đang nắm (VND)
    total_value: Decimal  # tiền mặt + holdings_value (VND)
    total_pnl: Decimal  # total_value - initial_capital (VND)
    total_pnl_pct: float


class PortfolioMissing(BaseModel):
    """Trả về khi user chưa tạo danh mục — frontend hiện form đặt vốn ban
    đầu thay vì báo lỗi."""

    available: Literal[False] = False
    message: str = "Chưa có danh mục. Tạo danh mục và đặt vốn ảo ban đầu để bắt đầu."


class OrderCreate(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    quantity: int = Field(gt=0)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: str
    quantity: int
    price: Decimal
    amount: Decimal
    price_source: str
    executed_at: datetime


class OrderResult(BaseModel):
    transaction: TransactionOut
    portfolio: PortfolioOut
