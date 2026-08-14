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

from app.collectors.base import (
    CompanyFundamentals,
    CompanyInfo,
    IndexBar,
    ListedSymbol,
    MarketDataProvider,
    PriceBar,
    PriceBoardQuote,
)

# vnstock trả cột "exchange" (đổi tên từ "board" của VCI) với các giá trị
# đã gặp thực tế là "HOSE" hoặc "HSX" tuỳ phiên bản API — chấp nhận cả 2.
_HOSE_EXCHANGE_ALIASES = {"HOSE", "HSX"}

# Mã chỉ số công khai dùng trong app (lưu DB, endpoint, UI).
VALID_INDEX_CODES = ("VNINDEX", "HNX", "UPCOM", "VN30")

# vnstock nhận diện asset_type="index" qua is_valid_index() (module
# vnstock.common.indices), tập hợp này CHỈ chứa {"VNINDEX", "HNXINDEX",
# "UPCOMINDEX", "HNX30"} + các mã trong INDICES_INFO (có "VN30") — KHÔNG
# chứa "HNX"/"UPCOM" trơn như _VCI_INDEX_MAPPING gợi ý (mapping đó chỉ
# được tra SAU KHI đã xác định asset_type == "index"). Đã kiểm chứng bằng
# lời gọi thật: "HNX" bị nhận nhầm thành asset_type="stock", "UPCOM" bị
# từ chối ngay ở bước validate symbol. Vì vậy map sang mã đầy đủ ở đây.
_INDEX_CODE_TO_VNSTOCK_SYMBOL = {
    "VNINDEX": "VNINDEX",
    "HNX": "HNXINDEX",
    "UPCOM": "UPCOMINDEX",
    "VN30": "VN30",
}


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

    def get_index_history(self, code: str, years: int) -> list[IndexBar]:
        from vnstock import Vnstock

        code = code.upper()
        vnstock_symbol = _INDEX_CODE_TO_VNSTOCK_SYMBOL.get(code)
        if vnstock_symbol is None:
            raise ValueError(
                f"Mã chỉ số không hợp lệ: {code}. Chỉ hỗ trợ: {', '.join(VALID_INDEX_CODES)}"
            )

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

        stock = Vnstock().stock(symbol=vnstock_symbol, source="VCI")
        raw = stock.quote.history(start=start_date, end=end_date, interval="1D")
        if raw is None or raw.empty:
            return []

        df = raw.rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        bars = []
        for _, row in df.iterrows():
            bars.append(
                IndexBar(
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

    def list_hose_symbols(self) -> list[ListedSymbol]:
        from vnstock import Listing

        df = Listing(source="VCI").symbols_by_exchange()
        if df is None or df.empty:
            return []

        df = df[df["type"] == "STOCK"]
        exchange = df["exchange"].astype(str).str.upper()
        df = df[exchange.isin(_HOSE_EXCHANGE_ALIASES)]

        symbols = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            symbol = _first_present(row_dict, ["symbol"])
            if not symbol:
                continue
            name = _first_present(row_dict, ["organ_name", "organ_short_name"]) or symbol
            symbols.append(ListedSymbol(symbol=str(symbol), company_name=str(name)))
        return sorted(symbols, key=lambda s: s.symbol)

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals:
        from vnstock import Vnstock

        symbol = symbol.upper()
        company = Vnstock().stock(symbol=symbol, source="VCI").company
        merged: dict = {}

        # Gộp 2 nguồn: overview (hồ sơ doanh nghiệp) + ratio_summary (chỉ
        # số tài chính). Mỗi nguồn hỏng độc lập — thiếu một nguồn vẫn trả
        # về phần lấy được, vì với người dùng "thiếu vài chỉ số" tốt hơn
        # hẳn "không có gì".
        for fetch in (lambda: company.overview(), lambda: company.ratio_summary()):
            try:
                df = fetch()
            except Exception:  # noqa: BLE001
                continue
            if df is None or df.empty:
                continue
            merged.update({k: _json_safe(v) for k, v in df.iloc[0].to_dict().items()})

        if not merged:
            return CompanyFundamentals(symbol=symbol)

        def num(candidates: list[str]) -> float | None:
            value = _first_present(merged, candidates)
            if value is None:
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        # Tên trường của VCI chưa kiểm chứng được bằng dữ liệu thật (API
        # chỉ lộ tên cột lúc gọi thật). Dò theo nhiều tên khả dĩ thay vì
        # cố định một tên — cùng lý do với _first_present ở price board,
        # nơi cách này đã cứu được một lần vnstock đổi schema.
        profile = _first_present(merged, ["company_profile", "profile", "business_strategies"])
        industry = _first_present(merged, ["industry", "icb_name3", "icb_name2", "sector"])

        pe_value = num(["pe", "price_to_earning", "p_e"])
        eps_value = num(["eps", "earning_per_share", "basic_eps"])
        if eps_value is None and pe_value:
            # overview()/ratio_summary() của VCI không có cột EPS trực
            # tiếp (đã kiểm chứng bằng dữ liệu thật, không phải do đoán
            # sai tên cột) — suy ra từ PE = current_price / EPS.
            price_value = num(["current_price", "price", "close_price"])
            if price_value is not None:
                eps_value = price_value / pe_value

        return CompanyFundamentals(
            symbol=symbol,
            market_cap=num(["market_cap", "marketcap", "market_capital"]),
            pe=pe_value,
            pb=num(["pb", "price_to_book", "p_b"]),
            eps=eps_value,
            # Giữ NGUYÊN số thô của provider, không tự quy đổi đơn vị ở
            # đây: đơn vị chỉ xác định được khi đối chiếu với P/E và P/B,
            # việc đó làm ở services/fundamentals_math.py.
            roe=num(["roe", "return_on_equity"]),
            roa=num(["roa", "return_on_asset"]),
            dividend_yield=num(["dividend_yield", "dividend"]),
            issue_share=num(["issue_share", "number_of_shares_mkt_cap", "outstanding_share"]),
            charter_capital=num(["charter_capital", "chartercapital"]),
            company_profile=str(profile) if profile else None,
            industry=str(industry) if industry else None,
            # "_source" đánh dấu nguồn để router (fundamentals.py) biết
            # ROE/ROA thô này còn cần suy đơn vị qua fundamentals_math.py
            # hay không — vnstock (VCI) có, fireant_adapter.py thì không.
            raw={"_source": "vnstock", **merged},
        )
