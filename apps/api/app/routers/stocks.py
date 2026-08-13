from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.collectors.factory import get_market_data_provider
from app.db import get_db
from app.models.stock import Stock
from app.schemas.stock import HoseSymbol, StockSummary
from app.services.pricing import get_price_snapshots

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
    stocks = db.execute(stmt).scalars().all()

    # Lấy giá hàng loạt (2 truy vấn cho cả danh sách) thay vì từng mã —
    # danh sách có thể tới vài trăm dòng.
    snapshots = get_price_snapshots(db, [s.id for s in stocks])
    return [
        StockSummary(
            symbol=s.symbol,
            company_name=s.company_name,
            sector=s.sector,
            current_price=float(snap.price) if (snap := snapshots.get(s.id)) else None,
            price_source=snap.source if snap else None,
            change_pct=snap.change_pct if snap else None,
        )
        for s in stocks
    ]


@router.get("/hose-symbols", response_model=list[HoseSymbol])
def list_hose_symbols():
    """Toàn bộ mã cổ phiếu (type=STOCK) đang niêm yết trên sàn HOSE, lấy
    trực tiếp từ vnstock — KHÔNG đọc từ bảng `stocks` (chỉ chứa mã đã
    từng được sync giá). Dùng để biết cần sync thêm mã nào."""
    provider = get_market_data_provider()
    symbols = provider.list_hose_symbols()
    return [HoseSymbol(symbol=s.symbol, company_name=s.company_name) for s in symbols]
