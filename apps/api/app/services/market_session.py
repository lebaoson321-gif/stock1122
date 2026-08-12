"""
Trạng thái phiên giao dịch HOSE.

Một chỗ duy nhất định nghĩa "thị trường đang mở hay đóng" — dùng chung
cho endpoint trạng thái (web hiển thị + quyết định có tự làm mới hay
không) và cho job poll giá (không gọi provider ngoài giờ). Trước đây
khung giờ nằm rải rác trong cron của scheduler và trong workflow, mỗi
nơi một kiểu.

Hàm chính nhận `now` làm tham số thay vì tự gọi datetime.now() để test
được mọi mốc giờ mà không phải giả lập đồng hồ hệ thống.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Khung giờ HOSE. ATO/ATC là các phiên khớp lệnh định kỳ (mở/đóng cửa),
# giữa chúng là khớp lệnh liên tục.
_ATO_START = time(9, 0)
_MORNING_START = time(9, 15)
_MORNING_END = time(11, 30)
_AFTERNOON_START = time(13, 0)
_ATC_START = time(14, 30)
_ATC_END = time(14, 45)
_POST_END = time(15, 0)

# Thứ tự các mốc trong ngày kèm trạng thái BẮT ĐẦU tại mốc đó.
_SCHEDULE: list[tuple[time, str]] = [
    (_ATO_START, "ato"),
    (_MORNING_START, "morning"),
    (_MORNING_END, "lunch"),
    (_AFTERNOON_START, "afternoon"),
    (_ATC_START, "atc"),
    (_ATC_END, "post"),
    (_POST_END, "closed"),
]

LABELS = {
    "pre_open": "Chưa mở cửa",
    "ato": "Phiên mở cửa (ATO)",
    "morning": "Đang giao dịch (phiên sáng)",
    "lunch": "Nghỉ trưa",
    "afternoon": "Đang giao dịch (phiên chiều)",
    "atc": "Phiên đóng cửa (ATC)",
    "post": "Giao dịch thoả thuận",
    "closed": "Đã đóng cửa",
    "weekend": "Cuối tuần — thị trường nghỉ",
}

# Trạng thái có khớp lệnh thật -> giá đang chạy, web nên tự làm mới.
# "lunch" KHÔNG nằm ở đây: giá đứng yên suốt 1 tiếng rưỡi, làm mới chỉ
# tốn request. "post" cũng không: thoả thuận không đổi giá khớp.
_LIVE_STATES = {"ato", "morning", "afternoon", "atc"}


@dataclass
class MarketStatus:
    state: str
    label: str
    is_open: bool
    """True khi giá đang có thể thay đổi (không tính nghỉ trưa)."""
    is_trading_day: bool
    server_time: datetime
    next_change: datetime | None
    """Thời điểm trạng thái đổi tiếp theo — web dùng để đếm ngược."""


def _next_weekday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def get_market_status(now: datetime | None = None) -> MarketStatus:
    now = (now or datetime.now(VN_TZ)).astimezone(VN_TZ)
    today = now.date()
    is_trading_day = today.weekday() < 5

    def at(d: date, t: time) -> datetime:
        return datetime.combine(d, t, tzinfo=VN_TZ)

    if not is_trading_day:
        return MarketStatus(
            state="weekend",
            label=LABELS["weekend"],
            is_open=False,
            is_trading_day=False,
            server_time=now,
            next_change=at(_next_weekday(today), _ATO_START),
        )

    current = now.time()
    state = "pre_open"
    next_change: datetime | None = at(today, _ATO_START)
    for start, name in _SCHEDULE:
        if current >= start:
            state = name
        else:
            next_change = at(today, start)
            break
    else:
        # Đã qua mốc cuối trong ngày -> mở cửa lại vào ngày làm việc kế tiếp.
        next_change = at(_next_weekday(today), _ATO_START)

    return MarketStatus(
        state=state,
        label=LABELS[state],
        is_open=state in _LIVE_STATES,
        is_trading_day=True,
        server_time=now,
        next_change=next_change,
    )


def is_market_open(now: datetime | None = None) -> bool:
    return get_market_status(now).is_open
