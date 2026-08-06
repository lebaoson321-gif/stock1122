"""
Module thu thập dữ liệu giá lịch sử cổ phiếu từ HOSE/HNX
sử dụng thư viện vnstock (https://github.com/thinh-vu/vnstock).

Cài đặt: pip install vnstock
"""
from datetime import datetime, timedelta
import pandas as pd


def fetch_price_history(symbol: str, years: int = 5) -> pd.DataFrame:
    """
    Lấy dữ liệu giá lịch sử (OHLCV) cho một mã cổ phiếu.

    Args:
        symbol: mã cổ phiếu, ví dụ "FPT"
        years: số năm dữ liệu muốn lấy về (mặc định 5 năm)

    Returns:
        DataFrame với các cột: date, open, high, low, close, volume
    """
    from vnstock import Vnstock  # import trong hàm để MVP vẫn chạy được
                                   # phần khác nếu chưa cài vnstock

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365 * years)).strftime("%Y-%m-%d")

    stock = Vnstock().stock(symbol=symbol, source="VCI")
    raw = stock.quote.history(start=start_date, end=end_date, interval="1D")

    df = raw.rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    return df[["date", "open", "high", "low", "close", "volume"]]


def fetch_company_info(symbol: str) -> dict:
    """Lấy thông tin cơ bản của doanh nghiệp (tên, ngành)."""
    from vnstock import Vnstock

    # "TCBS" đã bị vnstock 4.x loại khỏi danh sách nguồn hỗ trợ cho
    # component `company` (chỉ còn KBS, VCI, MSN, FMP) -> dùng "VCI",
    # cùng nguồn với fetch_price_history().
    stock = Vnstock().stock(symbol=symbol, source="VCI")
    try:
        overview = stock.company.overview()
        if overview.empty:
            return {"company_name": symbol, "sector": ""}
        row = overview.iloc[0]
        company_name = row.get("organ_short_name") or row.get("organ_name") or symbol
        sector = row.get("sector") or ""
        return {"company_name": str(company_name), "sector": str(sector)}
    except Exception:
        # Nếu API thay đổi hoặc lỗi, không chặn luồng chính
        return {"company_name": symbol, "sector": ""}
