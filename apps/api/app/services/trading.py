"""
Khớp lệnh mua/bán ảo.

Luật mô phỏng ở mức ĐƠN GIẢN (theo lựa chọn khi thiết kế): mua bán số
lượng bất kỳ (không bắt lô chẵn 100), không phí giao dịch, không thuế,
không T+2, giao dịch được cả ngoài giờ. Muốn siết lại cho giống HOSE
thật thì thêm ở chính module này — router chỉ gọi `execute_order()` nên
không phải sửa chỗ khác.

Đơn vị: giá (`price`, `avg_cost`) tính bằng NGHÌN VND — cùng đơn vị với
`price_history.close` và với số hiển thị trên biểu đồ (FPT ~70.70).
Tiền (`cash_balance`, `amount`) tính bằng VND. Mọi quy đổi giữa hai đơn
vị đi qua `PRICE_UNIT_VND` bên dưới, không nhân/chia 1000 rải rác.
"""
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio, PortfolioPosition, PortfolioTransaction
from app.models.stock import Stock
from app.services.pricing import get_current_price

PRICE_UNIT_VND = Decimal(1000)
_VND = Decimal("0.01")
_PRICE_Q = Decimal("0.0001")


class TradeError(Exception):
    """Lệnh không hợp lệ theo trạng thái danh mục (hết tiền, bán quá số
    đang nắm...). Router đổi thành HTTP 400 — phân biệt với lỗi hệ thống."""


def order_amount_vnd(quantity: int, price: Decimal) -> Decimal:
    """Thành tiền của lệnh, tính bằng VND."""
    return (Decimal(quantity) * price * PRICE_UNIT_VND).quantize(_VND, rounding=ROUND_HALF_UP)


def _get_position(db: Session, portfolio_id: int, stock_id: int) -> PortfolioPosition | None:
    return db.execute(
        select(PortfolioPosition).where(
            PortfolioPosition.portfolio_id == portfolio_id,
            PortfolioPosition.stock_id == stock_id,
        )
    ).scalar_one_or_none()


def execute_order(
    db: Session, portfolio: Portfolio, stock: Stock, side: str, quantity: int
) -> PortfolioTransaction:
    """Khớp 1 lệnh theo giá hiện tại. Raises TradeError nếu không hợp lệ.
    Commit khi thành công; caller không cần commit lại."""
    if quantity <= 0:
        raise TradeError("Số lượng phải lớn hơn 0.")

    current = get_current_price(db, stock.id)
    if current is None:
        raise TradeError(
            f"Chưa có giá cho mã {stock.symbol}. Đồng bộ dữ liệu cho mã này trước khi giao dịch."
        )

    price = Decimal(current.price).quantize(_PRICE_Q, rounding=ROUND_HALF_UP)
    amount = order_amount_vnd(quantity, price)
    position = _get_position(db, portfolio.id, stock.id)

    if side == "buy":
        if amount > portfolio.cash_balance:
            raise TradeError(
                f"Không đủ tiền: cần {amount:,.0f}đ nhưng chỉ còn {portfolio.cash_balance:,.0f}đ."
            )
        portfolio.cash_balance = portfolio.cash_balance - amount
        if position is None:
            position = PortfolioPosition(
                portfolio_id=portfolio.id, stock_id=stock.id, quantity=quantity, avg_cost=price
            )
            db.add(position)
        else:
            # Giá vốn bình quân gia quyền theo số lượng.
            total_cost = position.avg_cost * position.quantity + price * quantity
            position.quantity = position.quantity + quantity
            position.avg_cost = (total_cost / position.quantity).quantize(
                _PRICE_Q, rounding=ROUND_HALF_UP
            )

    elif side == "sell":
        held = position.quantity if position else 0
        if quantity > held:
            raise TradeError(f"Chỉ đang nắm {held} cp {stock.symbol}, không bán được {quantity} cp.")
        portfolio.cash_balance = portfolio.cash_balance + amount
        # Bán KHÔNG đổi giá vốn phần còn lại — lãi/lỗ đã hiện thực hoá
        # nằm ở tiền mặt, phần còn nắm vẫn giữ nguyên giá vốn cũ.
        if quantity == held:
            db.delete(position)
        else:
            position.quantity = held - quantity

    else:
        raise TradeError(f"Loại lệnh không hợp lệ: {side!r}")

    transaction = PortfolioTransaction(
        portfolio_id=portfolio.id,
        stock_id=stock.id,
        side=side,
        quantity=quantity,
        price=price,
        amount=amount,
        price_source=current.source,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def reset_portfolio(db: Session, portfolio: Portfolio, initial_capital: Decimal | None = None) -> Portfolio:
    """Xoá sạch vị thế + lịch sử, đưa tiền mặt về vốn ban đầu (hoặc mức
    vốn mới nếu truyền vào)."""
    db.query(PortfolioTransaction).filter(PortfolioTransaction.portfolio_id == portfolio.id).delete()
    db.query(PortfolioPosition).filter(PortfolioPosition.portfolio_id == portfolio.id).delete()
    if initial_capital is not None:
        portfolio.initial_capital = initial_capital
    portfolio.cash_balance = portfolio.initial_capital
    db.commit()
    db.refresh(portfolio)
    return portfolio
