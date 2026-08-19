"""
Orchestrate: MarketDataProvider -> normalize -> upsert stocks/price_history
-> recompute_indicators -> recompute_score. Dùng chung bởi router sync
thủ công (routers/sync.py) và scheduler job (scheduler.py) — không viết
lặp 2 nơi.
"""
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.analysis.scoring import recompute_score
from app.collectors.base import MarketDataProvider
from app.models.price import PriceHistory
from app.models.stock import Stock
from app.processing.indicators import recompute_indicators
from app.processing.normalize import clean_price_bars

# Lùi start_date bao nhiêu ngày trước phiên mới nhất đã có khi sync tăng
# dần (xem sync_stock_history) — đệm phòng provider sửa lại số liệu vài
# phiên gần đây sau khi đã sync; upsert theo (stock_id, trade_date) vốn
# chống trùng nên ghi đè lại các phiên đã có là an toàn.
_INCREMENTAL_SYNC_LOOKBACK_DAYS = 10


def upsert_stock(db: Session, symbol: str, company_name: str, sector: str, exchange: str) -> Stock:
    stmt = (
        insert(Stock)
        .values(symbol=symbol, company_name=company_name, sector=sector, exchange=exchange)
        .on_conflict_do_update(
            index_elements=["symbol"],
            set_={"company_name": company_name, "sector": sector, "exchange": exchange},
        )
        .returning(Stock)
    )
    stock = db.execute(stmt).scalar_one()
    db.commit()
    return stock


def sync_stock_history(
    db: Session,
    provider: MarketDataProvider,
    symbol: str,
    years: int = 5,
    refresh_info: bool = False,
) -> int:
    """Đồng bộ lịch sử giá cho 1 mã. Trả về số dòng giá đã ghi.
    Raises bất kỳ exception nào từ provider — caller (router/scheduler)
    chịu trách nhiệm bắt và ghi vào data_sync_log."""
    symbol = symbol.upper()

    existing = db.execute(select(Stock).where(Stock.symbol == symbol)).scalar_one_or_none()
    # Tên công ty/ngành/sàn gần như không đổi — chỉ gọi lại provider (1
    # lượt gọi mạng riêng, tốn ~vài giây) khi thật sự cần: mã mới, lần
    # trước lấy hụt (company_name rơi về symbol, xem VnstockAdapter.
    # get_company_info nhánh except), hoặc bị ép làm mới qua refresh_info.
    if existing is None or existing.company_name == symbol or refresh_info:
        info = provider.get_company_info(symbol)
        stock = upsert_stock(db, symbol, info.company_name, info.sector, info.exchange)
    else:
        stock = existing

    # Mã đã có giá -> chỉ tải phần còn thiếu (lùi vài ngày làm đệm) thay
    # vì tải lại cả `years` năm mỗi ngày. Mã hoàn toàn mới thì vẫn phải
    # tải đủ theo years vì MA200 cần tối thiểu 200 phiên trước đó.
    latest_date = db.execute(
        select(func.max(PriceHistory.trade_date)).where(PriceHistory.stock_id == stock.id)
    ).scalar_one_or_none()

    if latest_date is None:
        bars = provider.get_price_history(symbol, years=years)
    else:
        start_date = latest_date - timedelta(days=_INCREMENTAL_SYNC_LOOKBACK_DAYS)
        bars = provider.get_price_history(symbol, years=years, start_date=start_date)

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
