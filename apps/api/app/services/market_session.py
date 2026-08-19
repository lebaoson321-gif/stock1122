"""
Trạng thái phiên giao dịch — HOSE, HNX, UPCoM.

Một chỗ duy nhất định nghĩa "thị trường đang mở hay đóng" — dùng chung
cho endpoint trạng thái (web hiển thị + quyết định có tự làm mới hay
không) và cho job poll giá (không gọi provider ngoài giờ). Trước đây
khung giờ nằm rải rác trong cron của scheduler và trong workflow, mỗi
nơi một kiểu.

Hàm chính nhận `now` làm tham số thay vì tự gọi datetime.now() để test
được mọi mốc giờ mà không phải giả lập đồng hồ hệ thống.

Khác biệt giữa 3 sàn (giờ khớp lệnh liên tục giống nhau, khác ở ATO/ATC):
  HOSE : 9:00-11:30, 13:00-14:45 — có ATO (9:00-9:15) và ATC (14:30-14:45)
  HNX  : 9:00-11:30, 13:00-14:45 — có ATC, KHÔNG có ATO (vào thẳng khớp
         lệnh liên tục lúc 9:00)
  UPCoM: 9:00-11:30, 13:00-15:00 — KHÔNG có ATO/ATC, chỉ khớp lệnh liên
         tục suốt phiên chiều tới 15:00
Giai đoạn "post" (giao dịch thoả thuận sau ATC, 14:45-15:00) áp dụng cho
HOSE và HNX vì cả 2 đều đóng khớp lệnh lúc 14:45; UPCoM không có giai
đoạn này vì khớp liên tục đã kéo dài tới đúng 15:00.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

_ATO_START = time(9, 0)
_MORNING_START = time(9, 15)
_MORNING_END = time(11, 30)
_AFTERNOON_START = time(13, 0)
_ATC_START = time(14, 30)
_ATC_END = time(14, 45)
_POST_END = time(15, 0)

# Lịch từng sàn: danh sách (mốc giờ, trạng thái BẮT ĐẦU tại mốc đó).
# Khớp lệnh liên tục buổi sáng luôn bắt đầu lúc 9:00 — chỉ khác là HOSE
# gọi giai đoạn 9:00-9:15 là "ato" còn HNX/UPCoM vào thẳng "morning".
_SCHEDULES: dict[str, list[tuple[time, str]]] = {
    "HOSE": [
        (_ATO_START, "ato"),
        (_MORNING_START, "morning"),
        (_MORNING_END, "lunch"),
        (_AFTERNOON_START, "afternoon"),
        (_ATC_START, "atc"),
        (_ATC_END, "post"),
        (_POST_END, "closed"),
    ],
    "HNX": [
        (_ATO_START, "morning"),
        (_MORNING_END, "lunch"),
        (_AFTERNOON_START, "afternoon"),
        (_ATC_START, "atc"),
        (_ATC_END, "post"),
        (_POST_END, "closed"),
    ],
    "UPCOM": [
        (_ATO_START, "morning"),
        (_MORNING_END, "lunch"),
        (_AFTERNOON_START, "afternoon"),
        (_POST_END, "closed"),
    ],
}

# Alias sàn — cùng bộ mã với app.collectors.vnstock_adapter.VALID_EXCHANGES,
# không import trực tiếp từ đó để services/ không phụ thuộc ngược vào
# collectors/ (chỉ là danh sách mã sàn, không phải dữ liệu từ provider).
_EXCHANGE_ALIASES = {"HOSE": "HOSE", "HSX": "HOSE", "HNX": "HNX", "UPCOM": "UPCOM"}

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


def _normalize_exchange(exchange: str) -> str:
    normalized = _EXCHANGE_ALIASES.get(exchange.upper())
    if normalized is None:
        valid = ", ".join(sorted(set(_EXCHANGE_ALIASES.values())))
        raise ValueError(f"Sàn không hợp lệ: {exchange}. Chỉ hỗ trợ: {valid}")
    return normalized


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


def get_market_status(now: datetime | None = None, exchange: str = "HOSE") -> MarketStatus:
    schedule = _SCHEDULES[_normalize_exchange(exchange)]

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
            next_change=at(_next_weekday(today), schedule[0][0]),
        )

    current = now.time()
    state = "pre_open"
    next_change: datetime | None = at(today, schedule[0][0])
    for start, name in schedule:
        if current >= start:
            state = name
        else:
            next_change = at(today, start)
            break
    else:
        # Đã qua mốc cuối trong ngày -> mở cửa lại vào ngày làm việc kế tiếp.
        next_change = at(_next_weekday(today), schedule[0][0])

    return MarketStatus(
        state=state,
        label=LABELS[state],
        is_open=state in _LIVE_STATES,
        is_trading_day=True,
        server_time=now,
        next_change=next_change,
    )


def is_market_open(now: datetime | None = None, exchange: str = "HOSE") -> bool:
    return get_market_status(now, exchange).is_open
