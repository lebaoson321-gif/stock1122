"""
/api/market/indices/poll phải xét trạng thái phiên RIÊNG cho từng chỉ số
qua INDEX_EXCHANGE (routers/market.py), KHÔNG dùng một cổng chung — lỗi
thật đã xảy ra hồi 14:45-15:00 mỗi ngày: cổng chung mặc định HOSE khiến
UPCOM-Index (sàn DUY NHẤT khớp liên tục thẳng tới 15:00, không có
ATO/ATC) bị bỏ sót 15 phút cuối phiên.

Dùng thẳng get_market_status() THẬT (không mock is_open giả) và chỉ ghim
`now` — nếu mock is_open trực tiếp thì test không còn chứng minh được gì
về lịch giao dịch thật của từng sàn, đúng lỗi đã gặp khi tưởng nhầm HNX
cũng khớp liên tục tới 15:00 như UPCOM (thực ra HNX đóng lúc 14:45 giống
HOSE — xem market_session.py).
"""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import app.routers.market as market_router
from app.services.market_session import get_market_status as real_get_market_status

_VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

_ANCHOR = date(2024, 1, 1)  # bất kỳ ngày nào — chỉ dùng để tính ra 1 thứ 3
_TUESDAY = _ANCHOR + timedelta(days=(7 - _ANCHOR.weekday()) % 7 + 1)  # thứ 2 kế tiếp rồi +1 ngày


def _at(t: time) -> datetime:
    return datetime.combine(_TUESDAY, t, tzinfo=_VN_TZ)


class _StubProvider:
    def __init__(self):
        self.calls: list[str] = []

    def get_index_intraday(self, code: str):
        self.calls.append(code)
        return None  # test này chỉ quan tâm CODE nào bị gọi, không quan tâm OHLC


def _pin_now(monkeypatch, now: datetime) -> _StubProvider:
    """Ghim `now` cho get_market_status() THẬT (không thay is_open giả),
    và thay get_market_data_provider() bằng stub để không gọi mạng."""

    def pinned(exchange: str):
        return real_get_market_status(now, exchange)

    stub_provider = _StubProvider()
    monkeypatch.setattr(market_router, "get_market_status", pinned)
    monkeypatch.setattr(market_router, "get_market_data_provider", lambda: stub_provider)
    return stub_provider


def test_poll_indices_at_1450_only_upcom_processed(monkeypatch):
    """14:50 thứ Ba: HOSE và HNX đã đóng khớp liên tục (cùng lúc 14:45),
    chỉ UPCOM còn khớp liên tục tới 15:00."""
    stub_provider = _pin_now(monkeypatch, _at(time(14, 50)))

    result = market_router.poll_indices(force=False, db=None)

    by_code = {item.code: item for item in result.results}
    assert by_code["VNINDEX"].message.startswith("Bỏ qua")
    assert by_code["VN30"].message.startswith("Bỏ qua")
    assert by_code["HNX"].message.startswith("Bỏ qua")
    assert not by_code["UPCOM"].message.startswith("Bỏ qua")

    # CHỈ UPCOM thật sự gọi provider — 3 mã còn lại bị chặn TRƯỚC khi tới
    # bước gọi get_index_intraday (không lãng phí lượt gọi mạng).
    assert stub_provider.calls == ["UPCOM"]


def test_poll_indices_at_1000_all_four_processed(monkeypatch):
    """10:00 thứ Ba: cả 3 sàn đều đang khớp liên tục."""
    stub_provider = _pin_now(monkeypatch, _at(time(10, 0)))

    result = market_router.poll_indices(force=False, db=None)

    for item in result.results:
        assert not item.message.startswith("Bỏ qua"), item
    assert set(stub_provider.calls) == {"VNINDEX", "VN30", "HNX", "UPCOM"}


def test_poll_indices_at_lunch_none_processed(monkeypatch):
    """12:00 thứ Ba (nghỉ trưa): cả 3 sàn đều đóng, không mã nào được poll."""
    stub_provider = _pin_now(monkeypatch, _at(time(12, 0)))

    result = market_router.poll_indices(force=False, db=None)

    for item in result.results:
        assert item.message.startswith("Bỏ qua"), item
    assert stub_provider.calls == []
