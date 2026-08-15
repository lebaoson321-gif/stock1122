from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.collectors.factory import get_market_data_provider
from app.collectors.vnstock_adapter import VALID_EXCHANGES
from app.db import get_db
from app.models.stock import Stock
from app.schemas.stock import StockListResponse, StockSummary, SymbolOut
from app.services.pricing import get_price_snapshots

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("", response_model=StockListResponse)
def list_stocks(
    q: str | None = Query(None, description="Tìm theo mã hoặc tên công ty"),
    exchange: str | None = Query(None, description="Lọc theo sàn: HOSE, HNX, UPCOM"),
    limit: int = Query(50, ge=1, le=100_000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Stock).where(Stock.is_active.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Stock.symbol.ilike(pattern), Stock.company_name.ilike(pattern)))
    if exchange:
        stmt = stmt.where(Stock.exchange == exchange.upper())

    # ~1600 mã sau khi thêm HNX/UPCoM — không render hết, đếm tổng riêng
    # để frontend phân trang (xem components/StockList.tsx).
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    stocks = db.execute(stmt.order_by(Stock.symbol).limit(limit).offset(offset)).scalars().all()

    # Lấy giá hàng loạt (2 truy vấn cho cả danh sách) thay vì từng mã —
    # danh sách có thể tới vài trăm dòng.
    snapshots = get_price_snapshots(db, [s.id for s in stocks])
    items = [
        StockSummary(
            symbol=s.symbol,
            company_name=s.company_name,
            sector=s.sector,
            exchange=s.exchange,
            current_price=float(snap.price) if (snap := snapshots.get(s.id)) else None,
            price_source=snap.source if snap else None,
            change_pct=snap.change_pct if snap else None,
        )
        for s in stocks
    ]
    return StockListResponse(items=items, total=total)


@router.get("/symbols", response_model=list[SymbolOut])
def list_symbols_endpoint(
    exchange: str = Query(
        "HOSE",
        description="Sàn cần lấy: HOSE, HNX, UPCOM (phân cách bởi dấu phẩy để lấy nhiều sàn), hoặc 'all' cho cả 3.",
    ),
):
    """Toàn bộ mã cổ phiếu (type=STOCK) đang niêm yết, lấy trực tiếp từ
    vnstock — KHÔNG đọc từ bảng `stocks` (chỉ chứa mã đã từng được sync
    giá). Dùng để biết cần sync thêm mã nào."""
    exchanges = (
        list(VALID_EXCHANGES)
        if exchange.strip().lower() == "all"
        else [e.strip().upper() for e in exchange.split(",") if e.strip()]
    )
    provider = get_market_data_provider()
    symbols = provider.list_symbols(exchanges)
    return [SymbolOut(symbol=s.symbol, company_name=s.company_name, exchange=s.exchange) for s in symbols]


@router.get("/hose-symbols", response_model=list[SymbolOut], include_in_schema=False)
def list_hose_symbols_legacy():
    """Alias cũ — giữ lại để workflow chưa kịp đổi sang /symbols?exchange=
    không bị gãy giữa lúc deploy. Có thể xoá sau khi daily-sync.yml (đã
    đổi sang endpoint mới) chạy ổn định vài lần."""
    return list_symbols_endpoint(exchange="HOSE")
