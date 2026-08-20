"""
Poll giá phải gom mã theo `stocks.exchange` và xét trạng thái phiên
RIÊNG cho từng sàn — HOSE và HNX đóng khớp liên tục lúc 14:45 như nhau,
CHỈ UPCOM khớp liên tục thẳng tới 15:00 (xem market_session.py). Trước
bản sửa này, poll-realtime dùng một cổng HOSE chung cho mọi mã — hôm
nay chưa lộ lỗi vì DB chỉ toàn mã HOSE, sẽ sai ngay khi backfill
HNX/UPCoM xong.

Test thẳng vào _poll_realtime_core() (vòng lặp gom-sàn-rồi-gọi-provider
thuần), KHÔNG qua endpoint poll_realtime() hay _poll_realtime_background():
2 hàm đó mở SessionLocal() thật và gọi pg_try_advisory_xact_lock — hàm
Postgres-only, không chạy được trên SQLite in-memory dùng cho test này.
_poll_realtime_core() nhận db/provider qua tham số nên test được độc lập
với session thật và advisory lock (xem sync.py để biết vì sao tách 2 lớp).

DB thật (SQLite in-memory, có vài dòng `stocks` trên cả 3 sàn) — không
mock kết quả list_active_symbols_by_exchange(), để test này thật sự
chứng minh được việc GOM NHÓM đọc đúng cột exchange, không chỉ chứng
minh logic gate tách rời khỏi DB. Ghim `now` cho get_market_status()
THẬT thay vì mock is_open giả — cùng lý do với test_indices_poll.py.
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi import BackgroundTasks, Response, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.routers.sync as sync_router
from app.collectors.historical import list_active_symbols_by_exchange
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

    by_exchange = list_active_symbols_by_exchange(db_session)
    sync_router._poll_realtime_core(db_session, stub_provider, by_exchange, batch_size=50, force=False)

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


# --- Endpoint poll_realtime(): 200 đồng bộ khi đóng cửa, 202 + chạy nền khi mở ---
#
# Bù cho việc trả 202 luôn "thành công" với caller kể cả khi poll hỏng
# thật: các test dưới đây chứng minh (1) endpoint không âm thầm nuốt lỗi
# — nó chỉ ĐẨY việc vào nền và trả 202 khi thật sự có việc để làm, và
# (2) _poll_realtime_background() ghi được data_sync_log dù lỗi xảy ra ở
# bất kỳ đâu trong try (cạm bẫy #2 — phải CHỨNG MINH bằng test, không
# phải tin theo code đọc bằng mắt).


def test_poll_realtime_endpoint_closed_market_returns_200_no_background_task(monkeypatch, db_session):
    """Ngoài giờ khớp lệnh của MỌI sàn, không force: trả 200 ngay, đồng
    bộ, KHÔNG có việc nào bị đẩy vào nền (không tốn quota provider)."""

    def pinned(exchange: str):
        return real_get_market_status(_at(time(12, 0)), exchange)

    monkeypatch.setattr(sync_router, "get_market_status", pinned)

    background_tasks = BackgroundTasks()
    response = Response()
    result = sync_router.poll_realtime(
        background_tasks=background_tasks, response=response, batch_size=50, force=False, db=db_session
    )

    assert response.status_code != status.HTTP_202_ACCEPTED
    assert result.message.startswith("Bỏ qua")
    assert background_tasks.tasks == []


def test_poll_realtime_endpoint_open_market_returns_202_and_queues_background_task(monkeypatch, db_session):
    """Trong giờ khớp lệnh của ít nhất 1 sàn: trả 202 NGAY (không đợi
    poll xong) và đẩy đúng 1 việc vào nền."""

    def pinned(exchange: str):
        return real_get_market_status(_at(time(10, 0)), exchange)

    monkeypatch.setattr(sync_router, "get_market_status", pinned)

    background_tasks = BackgroundTasks()
    response = Response()
    result = sync_router.poll_realtime(
        background_tasks=background_tasks, response=response, batch_size=50, force=False, db=db_session
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert "nền" in result.message
    assert len(background_tasks.tasks) == 1


def test_poll_realtime_background_logs_even_on_unexpected_error(monkeypatch, db_session):
    """_poll_realtime_background PHẢI ghi được 1 dòng data_sync_log dù
    lỗi xảy ra ở đâu trong try — kể cả lỗi hoàn toàn ngoài dự kiến, không
    phải lỗi provider thường gặp đã có sẵn try/except riêng.

    Lỗi ở đây tự nhiên xảy ra vì pg_try_advisory_xact_lock là hàm
    Postgres-only, SQLite (dùng cho test) không có — mô phỏng đúng tinh
    thần cạm bẫy #2: response 202 đã gửi cho caller trước đó, chỉ
    data_sync_log mới cho biết sự thật là có lỗi."""
    monkeypatch.setattr(sync_router, "SessionLocal", lambda: db_session)

    sync_router._poll_realtime_background(batch_size=50, force=False)

    logs = db_session.query(DataSyncLog).filter_by(sync_type="realtime").all()
    assert len(logs) == 1
    assert logs[0].status == "provider_error"
    assert logs[0].error_message is not None
