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
    trách nhiệm bắt và ghi vào data_sync_log.

    CẠM BẪY cho caller nào định bọc pg_try_advisory_xact_lock() quanh
    NHIỀU lần gọi hàm này (vd. lặp theo lô/theo sàn): db.commit() bên
    dưới KẾT THÚC transaction hiện tại, mà pg_try_advisory_xact_lock là
    khoá THEO TRANSACTION — nên khoá tự nhả ngay sau lần gọi đầu tiên,
    không giữ được cho các lần gọi sau trong cùng 1 lượt poll. Đã xảy ra
    thật: scheduler.py và routers/sync.py._poll_realtime_background đều
    có kiểu này — bằng chứng trong data_sync_log (2026-08-20, id 4452
    chạy 08:01:11, NẰM TRONG cửa sổ chạy 08:00:49-08:01:21 của id 4453,
    mà KHÔNG bị skipped_locked như lẽ ra phải vậy). Hiện chấp nhận được
    vì chỉ còn 1 bộ lập lịch gọi poll (cron-job.org) nên 2 lượt không tự
    chồng nhau (~32s/lượt, cách nhau 10 phút) — nhưng nếu có bộ lập lịch
    thứ 2 cùng gọi, khoá KHÔNG chặn được va chạm giữa lô 2 trở đi. Sửa
    triệt để (gộp 1 transaction, chỉ commit cuối) cần thiết kế lại cách
    1 lô lỗi không kéo sập cả lượt — xem ghi chú ở nơi gọi."""
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
                "open_price": q.open_price,
                "high_price": q.high_price,
                "low_price": q.low_price,
                "accumulated_volume": q.accumulated_volume,
                "trading_date": q.trading_date,
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
            "open_price": stmt.excluded.open_price,
            "high_price": stmt.excluded.high_price,
            "low_price": stmt.excluded.low_price,
            "accumulated_volume": stmt.excluded.accumulated_volume,
            "trading_date": stmt.excluded.trading_date,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(records)
