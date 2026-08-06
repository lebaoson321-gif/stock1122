"""
Orchestrate: MarketDataProvider -> normalize -> upsert stocks/price_history
-> recompute_indicators -> recompute_score. Dùng chung bởi router sync
thủ công (routers/sync.py) và scheduler job (scheduler.py) — không viết
lặp 2 nơi.
"""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.analysis.scoring import recompute_score
from app.collectors.base import MarketDataProvider
from app.models.price import PriceHistory
from app.models.stock import Stock
from app.processing.indicators import recompute_indicators
from app.processing.normalize import clean_price_bars


def upsert_stock(db: Session, symbol: str, company_name: str, sector: str) -> Stock:
    stmt = (
        insert(Stock)
        .values(symbol=symbol, company_name=company_name, sector=sector)
        .on_conflict_do_update(
            index_elements=["symbol"],
            set_={"company_name": company_name, "sector": sector},
        )
        .returning(Stock)
    )
    stock = db.execute(stmt).scalar_one()
    db.commit()
    return stock


def sync_stock_history(db: Session, provider: MarketDataProvider, symbol: str, years: int = 5) -> int:
    """Đồng bộ lịch sử giá cho 1 mã. Trả về số dòng giá đã ghi.
    Raises bất kỳ exception nào từ provider — caller (router/scheduler)
    chịu trách nhiệm bắt và ghi vào data_sync_log."""
    symbol = symbol.upper()

    info = provider.get_company_info(symbol)
    stock = upsert_stock(db, symbol, info.company_name, info.sector)

    bars = provider.get_price_history(symbol, years=years)
    bars = clean_price_bars(bars)
    if not bars:
        return 0

    records = [
        {
            "stock_id": stock.id,
            "trade_date": bar.trade_date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in bars
    ]
    stmt = insert(PriceHistory).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["stock_id", "trade_date"],
        set_={
            "open": stmt.excluded.open, "high": stmt.excluded.high, "low": stmt.excluded.low,
            "close": stmt.excluded.close, "volume": stmt.excluded.volume,
        },
    )
    db.execute(stmt)
    db.commit()

    recompute_indicators(db, stock.id)
    recompute_score(db, stock.id)
    return len(records)


def list_active_symbols(db: Session) -> list[str]:
    rows = db.execute(select(Stock.symbol).where(Stock.is_active.is_(True)).order_by(Stock.symbol)).all()
    return [r[0] for r in rows]
