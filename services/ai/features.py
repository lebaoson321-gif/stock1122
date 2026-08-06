"""
Xây dựng feature matrix cho AI Module từ dữ liệu đã có trong Postgres
(bảng price_history, technical_indicators — do apps/api ghi).

Nhãn (label): 1 nếu close(t+1) > close(t), ngược lại 0 — dự đoán chiều
giá phiên KẾ TIẾP dựa trên đặc trưng tính đến hết phiên hiện tại.
"""
import pandas as pd
from sqlalchemy import text

from db import get_engine

FEATURE_COLUMNS = [
    "return_1d", "return_5d", "return_10d", "volume_ratio",
    "rsi14", "macd", "macd_hist", "dist_ma20", "dist_ma50", "bb_position",
]

_QUERY = text(
    """
    SELECT p.trade_date, p.close, p.volume,
           t.ma20, t.ma50, t.rsi14, t.macd, t.macd_hist, t.bb_upper, t.bb_lower
    FROM price_history p
    JOIN stocks s ON s.id = p.stock_id
    LEFT JOIN technical_indicators t
        ON t.stock_id = p.stock_id AND t.trade_date = p.trade_date
    WHERE s.symbol = :symbol
    ORDER BY p.trade_date
    """
)


def _build_raw_features(symbol: str) -> pd.DataFrame:
    """Trả về DataFrame có cột trade_date, close, và toàn bộ
    FEATURE_COLUMNS — dòng nào thiếu dữ liệu warmup (VD: chưa đủ 20
    phiên để tính MA20) sẽ có NaN ở feature tương ứng, chưa lọc bỏ."""
    engine = get_engine()
    df = pd.read_sql(_QUERY, engine, params={"symbol": symbol.upper()})
    if df.empty:
        return df

    df["return_1d"] = df["close"].pct_change(1)
    df["return_5d"] = df["close"].pct_change(5)
    df["return_10d"] = df["close"].pct_change(10)
    df["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
    df["dist_ma20"] = (df["close"] - df["ma20"]) / df["ma20"]
    df["dist_ma50"] = (df["close"] - df["ma50"]) / df["ma50"]
    bb_width = df["bb_upper"] - df["bb_lower"]
    df["bb_position"] = ((df["close"] - df["bb_lower"]) / bb_width).where(bb_width != 0)

    return df[["trade_date", "close", *FEATURE_COLUMNS]]


def build_training_data(symbol: str) -> pd.DataFrame:
    """DataFrame sẵn sàng train: trade_date + FEATURE_COLUMNS + label.
    Dòng cuối cùng bị bỏ (chưa biết label — cần giá phiên kế tiếp)."""
    df = _build_raw_features(symbol)
    if df.empty:
        return df
    df["label"] = (df["close"].shift(-1) > df["close"]).astype("Int64")
    df = df.dropna(subset=[*FEATURE_COLUMNS, "label"])
    return df[["trade_date", *FEATURE_COLUMNS, "label"]].reset_index(drop=True)


def get_latest_features(symbol: str) -> pd.Series | None:
    """Đặc trưng của phiên gần nhất — dùng để dự đoán phiên KẾ TIẾP
    (chưa xảy ra nên không có label)."""
    df = _build_raw_features(symbol)
    if df.empty:
        return None
    df = df.dropna(subset=FEATURE_COLUMNS)
    if df.empty:
        return None
    return df.iloc[-1]
