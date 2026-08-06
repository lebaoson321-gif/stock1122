from datetime import date, timedelta

from app.collectors.base import PriceBar
from app.processing.normalize import clean_price_bars


def _bar(d: date, close: float = 100.0, volume: int = 1000) -> PriceBar:
    return PriceBar(trade_date=d, open=close * 0.99, high=close * 1.02, low=close * 0.98, close=close, volume=volume)


def test_drops_non_positive_prices():
    d = date.today()
    bars = [_bar(d, close=100.0), PriceBar(trade_date=d + timedelta(days=1), open=-1, high=-1, low=-1, close=-1, volume=10)]
    result = clean_price_bars(bars)
    assert len(result) == 1
    assert result[0].close == 100.0


def test_drops_negative_volume():
    d = date.today()
    bars = [_bar(d, volume=-5)]
    assert clean_price_bars(bars) == []


def test_drops_high_less_than_low():
    d = date.today()
    bad = PriceBar(trade_date=d, open=100, high=90, low=95, close=100, volume=10)
    assert clean_price_bars([bad]) == []


def test_dedupes_by_date_keeping_last():
    d = date.today()
    bars = [_bar(d, close=100.0), _bar(d, close=200.0)]
    result = clean_price_bars(bars)
    assert len(result) == 1
    assert result[0].close == 200.0


def test_sorts_by_date():
    d = date.today()
    bars = [_bar(d + timedelta(days=2)), _bar(d), _bar(d + timedelta(days=1))]
    result = clean_price_bars(bars)
    assert [b.trade_date for b in result] == sorted(b.trade_date for b in bars)
