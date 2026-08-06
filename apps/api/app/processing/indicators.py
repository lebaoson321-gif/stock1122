"""
Tính chỉ báo kỹ thuật: MA, EMA, RSI, MACD, Bollinger Bands.

MA/RSI/MACD port từ legacy/backend/app/indicators.py (đã test kỹ với dữ
liệu giả lập ở bản MVP trước) — bổ sung EMA12/26 độc lập và Bollinger
Bands theo yêu cầu nền tảng mới.

`recompute_indicators()` tính lại TOÀN BỘ chuỗi từ price_history rồi
upsert vào technical_indicators — không patch tăng dần (xem docstring
model TechnicalIndicator để biết lý do: MA200 cần 200 dòng trước đó).
"""
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.indicator import TechnicalIndicator
from app.models.price import PriceHistory


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma50"] = df["close"].rolling(window=50).mean()
    df["ma200"] = df["close"].rolling(window=200).mean()
    return df


def add_ema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """RSI = 100 - 100 / (1 + RS), RS = avg gain / avg loss trong `period` phiên."""
    df = df.copy()
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    df["rsi14"] = 100 - (100 / (1 + rs))
    df.loc[avg_loss == 0, "rsi14"] = 100.0
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD = EMA(fast) - EMA(slow); Signal = EMA(signal) của MACD."""
    df = df.copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    return df


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands: dải giữa = MA(period), dải trên/dưới = MA ± num_std * độ lệch chuẩn."""
    df = df.copy()
    mid = df["close"].rolling(window=period).mean()
    std = df["close"].rolling(window=period).std()
    df["bb_middle"] = mid
    df["bb_upper"] = mid + num_std * std
    df["bb_lower"] = mid - num_std * std
    return df


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = add_moving_averages(df)
    df = add_ema(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)
    return df


_INDICATOR_COLUMNS = [
    "ma20", "ma50", "ma200", "ema12", "ema26", "rsi14",
    "macd", "macd_signal", "macd_hist", "bb_upper", "bb_middle", "bb_lower",
]


def _safe_float(value) -> float | None:
    if value is None or (isinstance(value, float) and (np.isnan(value) or np.isinf(value))):
        return None
    return float(value)


def recompute_indicators(db: Session, stock_id: int) -> int:
    """Tính lại toàn bộ chỉ báo kỹ thuật cho 1 mã từ price_history, upsert
    vào technical_indicators. Trả về số dòng đã ghi."""
    rows = db.execute(
        select(
            PriceHistory.trade_date, PriceHistory.open, PriceHistory.high,
            PriceHistory.low, PriceHistory.close, PriceHistory.volume,
        )
        .where(PriceHistory.stock_id == stock_id)
        .order_by(PriceHistory.trade_date)
    ).all()

    if not rows:
        return 0

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    df = compute_all_indicators(df)

    records = []
    for _, row in df.iterrows():
        record = {
            "stock_id": stock_id,
            "trade_date": row["date"] if isinstance(row["date"], date) else row["date"].date(),
        }
        for col in _INDICATOR_COLUMNS:
            record[col] = _safe_float(row.get(col))
        records.append(record)

    stmt = insert(TechnicalIndicator).values(records)
    stmt = stmt.on_conflict_do_update(
        index_elements=["stock_id", "trade_date"],
        set_={col: getattr(stmt.excluded, col) for col in _INDICATOR_COLUMNS},
    )
    db.execute(stmt)
    db.commit()
    return len(records)
