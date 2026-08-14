from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class FundamentalsResponse(BaseModel):
    symbol: str
    available: Literal[True] = True
    company_name: str
    # float chứ không Decimal — xem ghi chú ở schemas/portfolio.py.
    # Mọi chỉ số đều optional — provider không chính thức, và mỗi loại
    # hình doanh nghiệp có bộ chỉ số khác nhau. UI phải chịu được thiếu.
    market_cap: float | None = None
    pe: float | None = None
    pb: float | None = None
    eps: float | None = None
    roe: float | None = None
    roa: float | None = None
    dividend_yield: float | None = None
    issue_share: float | None = None
    charter_capital: float | None = None
    company_profile: str | None = None
    industry: str | None = None
    fetched_at: datetime
    # Bắt buộc truyền, không đặt mặc định — quên gán ở router phải vỡ
    # ngay lúc chạy (lỗi validation), không được âm thầm thiếu trên
    # production rồi để UI hiện số mà không rõ nguồn nào.
    source: Literal["fireant", "vnstock"]


class FundamentalsUnavailable(BaseModel):
    symbol: str
    available: Literal[False] = False
    message: str = "Chưa lấy được thông tin tài chính cho mã này."
