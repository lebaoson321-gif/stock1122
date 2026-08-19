"""
Ranh giới (boundary) giữa app và nhà cung cấp dữ liệu thị trường.

Không có API chính thức của HOSE cho nhà phát triển cá nhân — `vnstock`
(adapter mặc định) là thư viện cộng đồng scrape dữ liệu từ VCI, không có
SLA. Thư viện này đã đổi API giữa chừng một lần trong dự án này
(`source="TCBS"` bị loại bỏ). Vì vậy MỌI nơi khác trong codebase chỉ được
gọi qua interface `MarketDataProvider` này — không import `vnstock` trực
tiếp ở đâu khác ngoài `vnstock_adapter.py`. Khi provider đổi/hỏng, chỉ
cần sửa một adapter, không phải sửa router/scheduler/processing.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass
class PriceBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class CompanyInfo:
    symbol: str
    company_name: str
    sector: str
    exchange: str  # "HOSE" | "HNX" | "UPCOM"


@dataclass
class PriceBoardQuote:
    symbol: str
    captured_at: datetime
    match_price: float | None
    match_volume: int | None
    ref_price: float | None
    ceiling_price: float | None
    floor_price: float | None
    raw: dict
    # OHLC + khối lượng luỹ kế của CHÍNH phiên hôm nay, do bảng giá trả
    # sẵn — dùng để vẽ cây nến đang chạy trên biểu đồ (price_history chỉ
    # có dòng của hôm nay sau khi job sync chạy, tức sau giờ đóng cửa).
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    accumulated_volume: int | None = None
    # Ngày giao dịch do provider khai báo — đáng tin hơn captured_at (là
    # thời điểm MÌNH gọi), nhất là khi job poll chạy trễ qua nửa đêm.
    trading_date: date | None = None


@dataclass
class ListedSymbol:
    symbol: str
    company_name: str
    exchange: str  # "HOSE" | "HNX" | "UPCOM"


@dataclass
class IndexBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class CompanyFundamentals:
    """Chỉ số cơ bản của doanh nghiệp. MỌI trường đều optional: provider
    là API không chính thức, tên trường có thể đổi hoặc thiếu tuỳ mã (mã
    mới niêm yết thường chưa có P/E, ngân hàng không có cùng bộ chỉ số
    với doanh nghiệp sản xuất). UI phải hiển thị được khi thiếu trường."""

    symbol: str
    market_cap: float | None = None  # VND
    pe: float | None = None
    pb: float | None = None
    eps: float | None = None  # VND/cp
    roe: float | None = None  # %
    roa: float | None = None  # %
    dividend_yield: float | None = None  # %
    issue_share: float | None = None  # số cp đang lưu hành
    charter_capital: float | None = None  # VND
    company_profile: str | None = None
    industry: str | None = None
    # Toàn bộ dữ liệu thô đã lấy được — giữ lại để chẩn đoán khi provider
    # đổi tên trường (cùng lý do với RealtimeQuote.raw).
    raw: dict | None = None


class MarketDataProvider(Protocol):
    """Interface chuẩn hoá — implementation không được để lộ kiểu dữ liệu
    thô (DataFrame, tên cột) của provider cụ thể ra ngoài."""

    def get_price_history(self, symbol: str, years: int) -> list[PriceBar]: ...

    def get_company_info(self, symbol: str) -> CompanyInfo: ...

    def get_price_board(self, symbols: list[str]) -> list[PriceBoardQuote]: ...

    def list_symbols(self, exchanges: list[str]) -> list[ListedSymbol]: ...

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals: ...

    def get_index_history(self, code: str, years: int) -> list[IndexBar]: ...


class FundamentalsProvider(Protocol):
    """Interface hẹp hơn MarketDataProvider — chỉ chỉ số tài chính. Nguồn
    chỉ số tài chính có thể khác nguồn giá (xem factory.get_fundamentals_provider),
    nên adapter kiểu FireAntAdapter không cần (và không nên) implement
    toàn bộ MarketDataProvider."""

    def get_company_fundamentals(self, symbol: str) -> CompanyFundamentals: ...
