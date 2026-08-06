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


class MarketDataProvider(Protocol):
    """Interface chuẩn hoá — implementation không được để lộ kiểu dữ liệu
    thô (DataFrame, tên cột) của provider cụ thể ra ngoài."""

    def get_price_history(self, symbol: str, years: int) -> list[PriceBar]: ...

    def get_company_info(self, symbol: str) -> CompanyInfo: ...

    def get_price_board(self, symbols: list[str]) -> list[PriceBoardQuote]: ...
