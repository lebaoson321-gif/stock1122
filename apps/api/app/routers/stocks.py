from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.stock import Stock
from app.schemas.stock import StockSummary

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("", response_model=list[StockSummary])
def list_stocks(
    q: str | None = Query(None, description="Tìm theo mã hoặc tên công ty"),
    db: Session = Depends(get_db),
):
    stmt = select(Stock).where(Stock.is_active.is_(True)).order_by(Stock.symbol)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Stock.symbol.ilike(pattern), Stock.company_name.ilike(pattern)))
    return db.execute(stmt).scalars().all()
