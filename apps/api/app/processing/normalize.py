"""Chuẩn hoá / làm sạch dữ liệu giá trước khi lưu DB."""
from app.collectors.base import PriceBar


def clean_price_bars(bars: list[PriceBar]) -> list[PriceBar]:
    """Bỏ các dòng dữ liệu lỗi: giá <= 0, high < low, hoặc thiếu field,
    và loại trùng ngày (giữ dòng xuất hiện sau cùng — thường là bản mới
    nhất nếu provider trả về dữ liệu đã sửa)."""
    by_date: dict = {}
    for bar in bars:
        if bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            continue
        if bar.high < bar.low:
            continue
        if bar.volume < 0:
            continue
        by_date[bar.trade_date] = bar
    return sorted(by_date.values(), key=lambda b: b.trade_date)
