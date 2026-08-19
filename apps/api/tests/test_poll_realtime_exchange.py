"""
/api/stocks/poll-realtime phải gom mã theo `stocks.exchange` và xét
trạng thái phiên RIÊNG cho từng sàn — HOSE và HNX đóng khớp liên tục lúc
14:45 như nhau, CHỈ UPCOM khớp liên tục thẳng tới 15:00 (xem
market_session.py). Trước bản sửa này, poll-realtime dùng một cổng
HOSE chung cho mọi mã — hôm nay chưa lộ lỗi vì DB chỉ toàn mã HOSE, sẽ
sai ngay khi backfill HNX/UPCOM xong.

DB thật (SQLite in-memory, có vài dòng `stocks` trên cả 3 sàn) — không
mock kết quả list_active_symbols_by_exchange(), để test này thật sự
chứng minh được việc GOM NHÓM đọc đúng cột exchange, không chỉ chứng
minh logic gate tách rời khỏi DB. Ghim `now` cho get_market_status()
THẬT thay vì mock is_open giả — cùng lý do với test_indices_poll.py.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.routers.sync as sync_router
from app.models.stock import Stock
from app.models.sync_log import DataSyncLog
from app.services.market_session import get_market_status as real_get_market_status

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

_ANCHOR = date(2024, 1, 1)  # bất kỳ ngày nào — chỉ dùng để tính ra 1 thứ 3
_TUESDAY = _ANCHOR + timedelta(days=(7 - _ANCHOR.weekday()) % 7 + 1)

_STOCKS = [("VNM", "HOSE"), ("VCB", "HOSE"), ("SHS", "HNX"), ("BSR", "UPCOM")]
_EXCHANGE_BY_SYMBOL = dict(_STOCKS)


def _at(t: time) -> datetime:
    return datetime.combine(_TUESDAY, t, tzinfo=_VN_TZ)


class _StubProvider:
    """get_price_board trả rỗng — đủ để poll_and_store_price_board() trả
    về sớm (records rỗng) mà không chạm câu insert riêng của Postgres,
    nên chạy được trên SQLite. Test này chỉ quan tâm SÀN nào bị gọi."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def get_price_board(self, symbols: list[str]):
        self.calls.append(sorted(symbols))
        return []


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Stock.__table__.create(engine)
    DataSyncLog.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    for symbol, exchange in _STOCKS:
        session.add(Stock(symbol=symbol, company_name=symbol, sector="", exchange=exchange, is_active=True))
    session.commit()
    yield session
    session.close()


def _polled_exchanges(monkeypatch, db_session, now: datetime) -> set[str]:
    stub_provider = _StubProvider()

    def pinned(exchange: str):
        return real_get_market_status(now, exchange)

    monkeypatch.setattr(sync_router, "get_market_status", pinned)
    monkeypatch.setattr(sync_router, "get_market_data_provider", lambda: stub_provider)

    sync_router.poll_realtime(batch_size=50, force=False, db=db_session)

    return {_EXCHANGE_BY_SYMBOL[symbol] for batch in stub_provider.calls for symbol in batch}


def test_poll_realtime_at_1450_only_upcom_group(monkeypatch, db_session):
    """14:50 thứ Ba: HOSE và HNX đã đóng, chỉ nhóm UPCOM còn được poll."""
    assert _polled_exchanges(monkeypatch, db_session, _at(time(14, 50))) == {"UPCOM"}


def test_poll_realtime_at_1000_all_three_groups(monkeypatch, db_session):
    """10:00 thứ Ba: cả 3 nhóm sàn đều đang khớp liên tục."""
    assert _polled_exchanges(monkeypatch, db_session, _at(time(10, 0))) == {"HOSE", "HNX", "UPCOM"}


def test_poll_realtime_at_lunch_no_groups(monkeypatch, db_session):
    """12:00 thứ Ba (nghỉ trưa): cả 3 sàn đều đóng, không nhóm nào được poll."""
    assert _polled_exchanges(monkeypatch, db_session, _at(time(12, 0))) == set()
