from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock


def get_stock_or_404(db: Session, symbol: str) -> Stock:
    symbol = symbol.upper()
    stock = db.execute(select(Stock).where(Stock.symbol == symbol)).scalar_one_or_none()
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chưa có dữ liệu cho mã {symbol}. Gọi POST /api/stocks/{symbol}/sync trước.",
        )
    return stock
