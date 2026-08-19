"""
Kiểm tra khung giờ giao dịch của cả 3 sàn. Không hardcode giả định về
thứ trong tuần của 1 ngày cụ thể — tự tính ngày giao dịch (thứ 2) và
ngày cuối tuần (thứ 7) từ một mốc neo, tránh sai lệch nếu lịch thay đổi.
"""
from datetime import date, datetime, time, timedelta

import pytest

from app.services.market_session import VN_TZ, get_market_status, is_market_open

_ANCHOR = date(2024, 1, 1)  # bất kỳ ngày nào — chỉ dùng để tính ra 1 thứ 2 và 1 thứ 7
_WEEKDAY = _ANCHOR + timedelta(days=(7 - _ANCHOR.weekday()) % 7)  # thứ 2 kế tiếp (hoặc chính nó)
_WEEKEND = _WEEKDAY + timedelta(days=(5 - _WEEKDAY.weekday()))  # thứ 7 cùng tuần


def _at(t: time, d: date = _WEEKDAY) -> datetime:
    return datetime.combine(d, t, tzinfo=VN_TZ)


# (giờ, trạng thái kỳ vọng) — bao phủ mọi mốc chuyển trạng thái + điểm giữa.
HOSE_CASES = [
    (time(8, 59), "pre_open"),
    (time(9, 0), "ato"),
    (time(9, 7), "ato"),
    (time(9, 14), "ato"),
    (time(9, 15), "morning"),
    (time(10, 0), "morning"),
    (time(11, 29), "morning"),
    (time(11, 30), "lunch"),
    (time(12, 0), "lunch"),
    (time(12, 59), "lunch"),
    (time(13, 0), "afternoon"),
    (time(14, 0), "afternoon"),
    (time(14, 29), "afternoon"),
    (time(14, 30), "atc"),
    (time(14, 37), "atc"),
    (time(14, 44), "atc"),
    (time(14, 45), "post"),
    (time(14, 52), "post"),
    (time(14, 59), "post"),
    (time(15, 0), "closed"),
    (time(20, 0), "closed"),
    (time(23, 59), "closed"),
]

# HNX: giống HOSE hệt trừ việc không có ATO — 9:00 vào thẳng "morning".
HNX_CASES = [
    (time(8, 59), "pre_open"),
    (time(9, 0), "morning"),
    (time(9, 14), "morning"),
    (time(10, 0), "morning"),
    (time(11, 29), "morning"),
    (time(11, 30), "lunch"),
    (time(12, 59), "lunch"),
    (time(13, 0), "afternoon"),
    (time(14, 29), "afternoon"),
    (time(14, 30), "atc"),
    (time(14, 44), "atc"),
    (time(14, 45), "post"),
    (time(14, 59), "post"),
    (time(15, 0), "closed"),
]

# UPCoM: không ATO/ATC/post — khớp liên tục (afternoon) kéo dài tới 15:00.
UPCOM_CASES = [
    (time(8, 59), "pre_open"),
    (time(9, 0), "morning"),
    (time(11, 29), "morning"),
    (time(11, 30), "lunch"),
    (time(12, 59), "lunch"),
    (time(13, 0), "afternoon"),
    (time(14, 29), "afternoon"),
    (time(14, 30), "afternoon"),  # KHÔNG chuyển sang atc — UPCoM không có ATC
    (time(14, 44), "afternoon"),
    (time(14, 45), "afternoon"),  # KHÔNG chuyển sang post — UPCoM không có post
    (time(14, 59), "afternoon"),
    (time(15, 0), "closed"),
]


@pytest.mark.parametrize("t,expected", HOSE_CASES)
def test_hose_schedule(t, expected):
    assert get_market_status(_at(t), "HOSE").state == expected


@pytest.mark.parametrize("t,expected", HNX_CASES)
def test_hnx_schedule(t, expected):
    assert get_market_status(_at(t), "HNX").state == expected


@pytest.mark.parametrize("t,expected", UPCOM_CASES)
def test_upcom_schedule(t, expected):
    assert get_market_status(_at(t), "UPCOM").state == expected


@pytest.mark.parametrize("exchange", ["HOSE", "HNX", "UPCOM"])
def test_weekend_all_exchanges(exchange):
    status = get_market_status(_at(time(10, 0), _WEEKEND), exchange)
    assert status.state == "weekend"
    assert status.is_open is False
    assert status.is_trading_day is False


@pytest.mark.parametrize(
    "exchange,live_states,closed_states",
    [
        ("HOSE", ["ato", "morning", "afternoon", "atc"], ["pre_open", "lunch", "post", "closed"]),
        ("HNX", ["morning", "afternoon", "atc"], ["pre_open", "lunch", "post", "closed"]),
        ("UPCOM", ["morning", "afternoon"], ["pre_open", "lunch", "closed"]),
    ],
)
def test_is_open_matches_live_states(exchange, live_states, closed_states):
    cases = {"HOSE": HOSE_CASES, "HNX": HNX_CASES, "UPCOM": UPCOM_CASES}[exchange]
    for t, expected_state in cases:
        status = get_market_status(_at(t), exchange)
        if expected_state in live_states:
            assert status.is_open, f"{exchange} {t} ({expected_state}) phải đang mở"
        elif expected_state in closed_states:
            assert not status.is_open, f"{exchange} {t} ({expected_state}) phải đang đóng"


def test_hsx_is_alias_for_hose():
    assert get_market_status(_at(time(10, 0)), "HSX").state == get_market_status(_at(time(10, 0)), "HOSE").state


def test_invalid_exchange_raises():
    with pytest.raises(ValueError):
        get_market_status(_at(time(10, 0)), "NASDAQ")


def test_default_exchange_is_hose():
    assert get_market_status(_at(time(9, 5))).state == "ato"


def test_is_market_open_helper():
    assert is_market_open(_at(time(10, 0)), "HOSE") is True
    assert is_market_open(_at(time(12, 0)), "HOSE") is False
    assert is_market_open(_at(time(14, 50)), "UPCOM") is True
