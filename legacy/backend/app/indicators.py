"""
Module tính toán chỉ báo kỹ thuật (Technical Indicators):
Moving Average, RSI, MACD.
"""
import pandas as pd


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["close"].rolling(window=20).mean()
    df["MA50"] = df["close"].rolling(window=50).mean()
    df["MA200"] = df["close"].rolling(window=200).mean()
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
    df["RSI"] = 100 - (100 / (1 + rs))
    # Xử lý trường hợp avg_loss = 0 (RSI -> 100)
    df.loc[avg_loss == 0, "RSI"] = 100.0
    return df


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD = EMA(fast) - EMA(slow); Signal = EMA(signal) của MACD."""
    df = df.copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]
    return df


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_macd(df)
    return df
