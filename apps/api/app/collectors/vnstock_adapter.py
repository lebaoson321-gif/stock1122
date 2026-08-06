"""
Adapter DUY NHẤT chứa mọi xử lý đặc thù của `vnstock`. Không nơi nào
khác trong codebase được `import vnstock` — mọi thứ đi qua
`MarketDataProvider` (app/collectors/base.py).

Lịch sử: ban đầu dùng source="TCBS" cho company info, bị vnstock 4.x
loại bỏ (chỉ còn KBS/VCI/MSN/FMP) khiến /sync luôn lỗi 502 — đã đổi
sang "VCI" (xem legacy/README.md). Version vnstock đã pin cứng trong
requirements.txt (không dùng >=) chính vì lỗi âm thầm này.
"""
import math
from datetime import datetime, timedelta, timezone

import pandas as pd

from app.collectors.base import CompanyInfo, MarketDataProvider, PriceBar, PriceBoardQuote


def _json_safe(value):
    """Chuyển kiểu numpy/pandas (int64, float64, Timestamp...) về kiểu
    Python thuần để lưu được vào cột JSONB."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):  # numpy scalar (int64, float64, bool_...)
        return _json_safe(value.item())
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def _first_present(row: dict, candidates: list[str]):
    """Trả về giá trị đầu tiên có mặt trong `row` theo danh sách tên cột
    ưu tiên. vnstock đôi khi đổi tên cột giữa các phiên bản nên tra theo
    nhiều khả năng thay vì cố định một tên duy nhất (đã gặp thật với
    fetch_company_info — xem docstring module)."""
    for key in candidates:
        value = row.get(key)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            return value
    return None


class VnstockAdapter(MarketDataProvider):
    def get_price_history(self, symbol: str, years: int) -> list[PriceBar]:
        from vnstock import Vnstock  # import trong hàm: chỉ tải vnstock khi thực sự cần

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

        stock = Vnstock().stock(symbol=symbol, source="VCI")
        raw = stock.quote.history(start=start_date, end=end_date, interval="1D")
        if raw is None or raw.empty:
            return []

        df = raw.rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        bars = []
        for _, row in df.iterrows():
            bars.append(
                PriceBar(
                    trade_date=row["date"].date(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                )
            )
        return bars

    def get_company_info(self, symbol: str) -> CompanyInfo:
        from vnstock import Vnstock

        stock = Vnstock().stock(symbol=symbol, source="VCI")
        try:
            overview = stock.company.overview()
            if overview is None or overview.empty:
                return CompanyInfo(symbol=symbol, company_name=symbol, sector="")
            row = overview.iloc[0]
            company_name = row.get("organ_short_name") or row.get("organ_name") or symbol
            sector = row.get("sector") or ""
            return CompanyInfo(symbol=symbol, company_name=str(company_name), sector=str(sector))
        except Exception:
            # Nếu API thay đổi hoặc lỗi, không chặn luồng chính (sync giá
            # vẫn nên tiếp tục dù không lấy được tên công ty/ngành).
            return CompanyInfo(symbol=symbol, company_name=symbol, sector="")

    def get_price_board(self, symbols: list[str]) -> list[PriceBoardQuote]:
        from vnstock.api.trading import Trading  # nhẹ hơn Vnstock().stock() — không

        # kích hoạt lookup company/finance nặng nề, đã kiểm chứng khi debug
        # realtime-poller ở bản MVP trước.
        trading = Trading(source="vci", show_log=False)
        board = trading.price_board(symbols_list=symbols, flatten_columns=True)
        captured_at = datetime.now(timezone.utc)

        if board is None or board.empty:
            return []

        quotes = []
        for _, row in board.iterrows():
            row_dict = row.to_dict()
            symbol = _first_present(row_dict, ["listing_symbol", "symbol"])
            if not symbol:
                continue
            quotes.append(
                PriceBoardQuote(
                    symbol=str(symbol),
                    captured_at=captured_at,
                    match_price=_json_safe(
                        _first_present(row_dict, ["match_match_price", "match_price", "match_avg_price"])
                    ),
                    match_volume=_json_safe(
                        _first_present(row_dict, ["match_match_vol", "match_vol", "match_total_volume"])
                    ),
                    ref_price=_json_safe(_first_present(row_dict, ["listing_ref_price", "ref_price"])),
                    ceiling_price=_json_safe(
                        _first_present(row_dict, ["listing_ceiling", "ceiling", "ceiling_price"])
                    ),
                    floor_price=_json_safe(_first_present(row_dict, ["listing_floor", "floor", "floor_price"])),
                    raw={k: _json_safe(v) for k, v in row_dict.items()},
                )
            )
        return quotes
