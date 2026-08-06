"""Orchestrate: MarketDataProvider.get_price_board() -> upsert realtime_quotes."""
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.collectors.base import MarketDataProvider
from app.models.realtime import RealtimeQuote
from app.models.stock import Stock


def poll_and_store_price_board(db: Session, provider: MarketDataProvider, symbols: list[str]) -> int:
    """Poll giá khớp lệnh cho danh sách mã, upsert vào realtime_quotes.
    Trả về số dòng đã ghi. Raises exception từ provider — caller chịu
    trách nhiệm bắt và ghi vào data_sync_log."""
    if not symbols:
        return 0

    symbol_to_id = dict(
        db.execute(select(Stock.symbol, Stock.id).where(Stock.symbol.in_(symbols))).all()
    )

    quotes = provider.get_price_board(symbols)
    records = []
    for q in quotes:
        stock_id = symbol_to_id.get(q.symbol)
        if stock_id is None:
            continue
        records.append(
            {
                "stock_id": stock_id,
                "captured_at": q.captured_at,
                "match_price": q.match_price,
                "match_volume": q.match_volume,
                "ref_price": q.ref_price,
                "ceiling_price": q.ceiling_price,
                "floor_price": q.floor_price,
                "raw": q.raw,
            }
        )

    if not records:
        return 0

    stmt = insert(RealtimeQuote).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["stock_id", "captured_at"],
        set_={
            "match_price": stmt.excluded.match_price,
            "match_volume": stmt.excluded.match_volume,
            "ref_price": stmt.excluded.ref_price,
            "ceiling_price": stmt.excluded.ceiling_price,
            "floor_price": stmt.excluded.floor_price,
            "raw": stmt.excluded.raw,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(records)
