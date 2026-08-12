from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PortfolioCreate(BaseModel):
    # Vốn ảo tính bằng ĐỒNG (không phải nghìn đồng) — khớp với cách người
    # dùng nhập "100000000" cho 100 triệu. Xem services/trading.py về quy
    # đổi sang đơn vị giá.
    initial_capital: Decimal = Field(gt=0, le=Decimal("1e15"))


# Đầu RA dùng float, KHÔNG dùng Decimal: Pydantic serialize Decimal thành
# CHUỖI JSON ("18.4200"), khiến frontend gọi toLocaleString() lên chuỗi và
# in ra số thô chưa định dạng (đã gặp thật). Độ chính xác Decimal vẫn được
# giữ ở DB và ở services/trading.py — đây chỉ là bề mặt hiển thị, và số
# tiền VND còn xa giới hạn an toàn của số thực JS (2^53).
class PositionOut(BaseModel):
    stock_id: int
    symbol: str
    company_name: str
    quantity: int
    avg_cost: float  # nghìn VND/cp, cùng đơn vị giá hiển thị trên biểu đồ
    current_price: float | None
    price_source: str | None
    market_value: float | None  # VND
    cost_value: float  # VND
    pnl: float | None  # VND
    pnl_pct: float | None


class PortfolioOut(BaseModel):
    id: int
    initial_capital: float
    cash_balance: float
    positions: list[PositionOut] = []
    holdings_value: float  # tổng giá trị thị trường số cổ đang nắm (VND)
    total_value: float  # tiền mặt + holdings_value (VND)
    total_pnl: float  # total_value - initial_capital (VND)
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
    price: float
    amount: float
    price_source: str
    executed_at: datetime


class OrderResult(BaseModel):
    transaction: TransactionOut
    portfolio: PortfolioOut
